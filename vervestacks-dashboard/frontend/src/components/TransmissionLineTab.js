import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  MapPin, 
  Zap, 
  TrendingUp, 
  BarChart3,
  AlertCircle,
  Loader2,
  Settings,
  Layers,
  Eye,
  EyeOff,
  Power
} from 'lucide-react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import toast from 'react-hot-toast';
import { createMap, createTileLayer, calculateMapBounds, MAP_STYLES } from '../utils/mapUtils';
import { transmissionAPI } from '../services/api';

// Configuration constants
const CONFIG = {
  colors: {
    region: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'],
    voltage: {
      high: '#d62728',    // Red for 380kV+
      medium: '#ff7f0e',  // Orange for 220kV
      low: '#2ca02c',     // Green for 110kV
      default: '#7f7f7f'  // Gray for lower voltages
    },
    fuel: {
      gas: '#3B82F6',
      bioenergy: '#10B981',
      coal: '#6B7280',
      hydro: '#06B6D4',
      nuclear: '#8B5CF6',
      solar: '#F59E0B',
      wind: '#84CC16',
      oil: '#EF4444',
      unknown: '#9CA3AF'
    },
    transmission: {
      bus: '#fbbf24',
      busStroke: '#f59e0b',
      ntc: '#666'
    }
  },
  markers: {
    population: { radius: 4, weight: 1, opacity: 0.8, fillOpacity: 0.6 },
    cluster: { radius: 6, weight: 2, opacity: 1, fillOpacity: 0.8 },
    transmission: { radius: 6, weight: 0, opacity: 1, fillOpacity: 0.8 },
    powerPlant: { weight: 2, opacity: 1, fillOpacity: 0.8 }
  },
  lines: {
    transmission: { weight: 1, opacity: 0.8 },
    ntc: { weight: 2, opacity: 0.6, dashArray: '5, 5' }
  },
  powerPlantSizes: {
    large: 12,    // >= 1000 MW
    medium: 10,   // >= 500 MW
    small: 8,     // >= 100 MW
    tiny: 6       // < 100 MW
  }
};

const TransmissionLineTab = ({ countryIso }) => {
  const [transmissionData, setTransmissionData] = useState(null);
  const [networkData, setNetworkData] = useState(null);
  const [generationData, setGenerationData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [clusters, setClusters] = useState(12);
  const [mapStyle, setMapStyle] = useState(MAP_STYLES.CLEAN_MINIMAL);
  
  // Layer visibility controls - will be updated when network data loads
  const [layerVisibility, setLayerVisibility] = useState({
    populationPoints: true,
    clusterCenters: false, // Hidden by default
    ntcConnections: false, // Hidden by default
    transmissionBuses: true, // Visible by default
    powerPlants: true // Visible by default
  });

  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layerGroupsRef = useRef({});
  
  // Second map references
  const mapRef2 = useRef(null);
  const mapInstanceRef2 = useRef(null);
  const layerGroupsRef2 = useRef({});

  // Utility functions for colors and styling
  const getRegionColor = useCallback((clusterId) => {
    return CONFIG.colors.region[clusterId % CONFIG.colors.region.length];
  }, []);

  const getVoltageColor = useCallback((voltage) => {
    if (voltage >= 380) return CONFIG.colors.voltage.high;
    if (voltage >= 220) return CONFIG.colors.voltage.medium;
    if (voltage >= 110) return CONFIG.colors.voltage.low;
    return CONFIG.colors.voltage.default;
  }, []);

  const getFuelColor = useCallback((fuelType) => {
    return CONFIG.colors.fuel[fuelType] || CONFIG.colors.fuel.unknown;
  }, []);

  const getMarkerSize = useCallback((capacity) => {
    if (capacity >= 1000) return CONFIG.powerPlantSizes.large;
    if (capacity >= 500) return CONFIG.powerPlantSizes.medium;
    if (capacity >= 100) return CONFIG.powerPlantSizes.small;
    return CONFIG.powerPlantSizes.tiny;
  }, []);

  const parseLinestringGeometry = useCallback((geometry) => {
    // Parse LINESTRING WKT format: "LINESTRING (lng1 lat1, lng2 lat2, ...)"
    if (!geometry || !geometry.startsWith('LINESTRING')) {
      return null;
    }
    
    try {
      // Extract coordinates from LINESTRING (lng1 lat1, lng2 lat2, ...)
      const coordsMatch = geometry.match(/LINESTRING \((.+)\)/);
      if (!coordsMatch) return null;
      
      const coordsString = coordsMatch[1];
      const coordPairs = coordsString.split(',');
      
      return coordPairs.map(coord => {
        const [lng, lat] = coord.trim().split(' ').map(Number);
        return [lat, lng]; // Leaflet expects [lat, lng] format
      });
    } catch (error) {
      console.warn('Error parsing geometry:', error);
      return null;
    }
  }, []);


  // Marker creation utilities
  const createMarker = useCallback((lat, lng, config, popupContent) => {
    const marker = L.circleMarker([lat, lng], config);
    if (popupContent) {
      marker.bindPopup(popupContent);
    }
    return marker;
  }, []);

  const createTransmissionBusMarker = useCallback((bus) => {
    const config = {
      radius: CONFIG.markers.transmission.radius,
      fillColor: CONFIG.colors.transmission.bus,
      color: CONFIG.colors.transmission.busStroke,
      weight: CONFIG.markers.transmission.weight,
      opacity: CONFIG.markers.transmission.opacity,
      fillOpacity: CONFIG.markers.transmission.fillOpacity
    };
    
    const popupContent = `
      <div class="p-2">
        <h3 class="font-semibold text-sm">${bus.name}</h3>
        <p class="text-xs text-gray-600">Type: Transmission Bus</p>
        <p class="text-xs text-gray-600">Voltage: ${bus.voltage} kV</p>
      </div>
    `;
    
    return createMarker(bus.lat, bus.lng, config, popupContent);
  }, [createMarker]);

  const createPopulationMarker = useCallback((point) => {
    const color = getRegionColor(point.cluster);
    const config = {
      radius: CONFIG.markers.population.radius,
      fillColor: color,
      color: color,
      weight: CONFIG.markers.population.weight,
      opacity: CONFIG.markers.population.opacity,
      fillOpacity: CONFIG.markers.population.fillOpacity
    };
    
    const popupContent = `
      <div class="p-2">
        <h3 class="font-semibold text-sm">${point.name}</h3>
        <p class="text-xs text-gray-600">Population: ${point.raw_weight?.toLocaleString() || 'N/A'}</p>
        <p class="text-xs text-gray-600">Region: ${point.cluster}</p>
      </div>
    `;
    
    return createMarker(point.lat, point.lng, config, popupContent);
  }, [createMarker, getRegionColor]);

  const createPowerPlantMarker = useCallback((plant) => {
    const config = {
      radius: getMarkerSize(plant.capacity_mw),
      fillColor: getFuelColor(plant.fuel_type),
      color: '#FFFFFF',
      weight: CONFIG.markers.powerPlant.weight,
      opacity: CONFIG.markers.powerPlant.opacity,
      fillOpacity: CONFIG.markers.powerPlant.fillOpacity
    };
    
    const popupContent = `
      <div class="p-2">
        <h3 class="font-semibold text-sm">${plant.name}</h3>
        <p class="text-xs text-gray-600">Capacity: ${plant.capacity_mw.toLocaleString()} MW</p>
        <p class="text-xs text-gray-600">Fuel Type: ${plant.fuel_type}</p>
        <p class="text-xs text-gray-600">Bus ID: ${plant.bus_id || 'N/A'}</p>
        ${plant.description ? `<p class="text-xs text-gray-500 mt-1">${plant.description}</p>` : ''}
      </div>
    `;
    
    return createMarker(plant.lat, plant.lng, config, popupContent);
  }, [createMarker, getMarkerSize, getFuelColor]);

  // Helper function to load transmission infrastructure (buses and lines)
  const loadTransmissionInfrastructure = useCallback((mapInstance, layerGroups, data) => {
    if (!data) return;

    // Add transmission buses
    if (data.buses) {
      data.buses.forEach(bus => {
        if (bus.lat && bus.lng) {
          const marker = createTransmissionBusMarker(bus);
          layerGroups.transmissionBuses.addLayer(marker);
        }
      });
    }

    // Add transmission lines
    if (data.lines) {
      data.lines.forEach(line => {
        if (line.bus0_lat && line.bus0_lng && line.bus1_lat && line.bus1_lng) {
          const voltage = line.voltage || 0;
          const color = getVoltageColor(voltage);
          
          // Try to use geometry data first, fallback to straight line
          let coordinates;
          if (line.geometry) {
            const geometryCoords = parseLinestringGeometry(line.geometry);
            if (geometryCoords && geometryCoords.length > 1) {
              coordinates = geometryCoords;
            } else {
              // Fallback to straight line between buses
              coordinates = [
                [line.bus0_lat, line.bus0_lng],
                [line.bus1_lat, line.bus1_lng]
              ];
            }
          } else {
            // Fallback to straight line between buses
            coordinates = [
              [line.bus0_lat, line.bus0_lng],
              [line.bus1_lat, line.bus1_lng]
            ];
          }
          
          const polyline = L.polyline(coordinates, {
            color: color,
            weight: CONFIG.lines.transmission.weight,
            opacity: CONFIG.lines.transmission.opacity
          });

          polyline.bindPopup(`
            <div class="p-2">
              <h3 class="font-semibold text-sm">Transmission Line</h3>
              <p class="text-xs text-gray-600">From: ${line.bus0_id}</p>
              <p class="text-xs text-gray-600">To: ${line.bus1_id}</p>
              <p class="text-xs text-gray-600">Voltage: ${voltage} kV</p>
              <p class="text-xs text-gray-600">Capacity: ${line.capacity} MVA</p>
              <p class="text-xs text-gray-600">Length: ${line.length} km</p>
            </div>
          `);

          // Add to voltage-specific groups only (no general transmissionLines layer)
          const voltageKey = `${voltage}kV`;
          if (layerGroups[voltageKey]) {
            layerGroups[voltageKey].addLayer(polyline);
          }
        }
      });
    }
  }, [getVoltageColor, parseLinestringGeometry, createTransmissionBusMarker]);

  // Load demand cluster data (population, clusters, NTC + transmission)
  const loadDemandClusterData = useCallback((mapInstance, layerGroups) => {
    if (!mapInstance || !transmissionData) return;

    // Clear existing data
    Object.values(layerGroups).forEach(group => {
      group.clearLayers();
    });

    // Add population points
    if (transmissionData.demand_points) {
      transmissionData.demand_points.forEach((point, index) => {
        if (point.lat && point.lng && point.cluster !== undefined) {
          const marker = createPopulationMarker(point);
          layerGroups.populationPoints.addLayer(marker);
        }
      });
    }

    // Add cluster centers
    if (transmissionData.cluster_centers) {
      transmissionData.cluster_centers.forEach((center, index) => {
        if (center.center_lat && center.center_lng) {
          const color = getRegionColor(center.cluster_id);
          
          const houseIcon = L.divIcon({
            className: 'custom-house-icon',
            html: `
              <div style="
                width: 12px; 
                height: 12px; 
                background-color: ${color}; 
                border: 2px solid white; 
                border-radius: 2px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 8px;
                color: white;
                font-weight: bold;
              ">
                ${center.cluster_id}
              </div>
            `,
            iconSize: [12, 12],
            iconAnchor: [6, 6]
          });

          const marker = L.marker([center.center_lat, center.center_lng], { icon: houseIcon });
          
          marker.bindPopup(`
            <div class="p-2">
              <h3 class="font-semibold text-sm">${center.name}</h3>
              <p class="text-xs text-gray-600">Region ID: ${center.cluster_id}</p>
              <p class="text-xs text-gray-600">Total Demand: ${center.total_demand?.toLocaleString() || 'N/A'}</p>
              <p class="text-xs text-gray-600">Cities: ${center.n_cities || 'N/A'}</p>
              <p class="text-xs text-gray-600">Major City: ${center.major_city || 'N/A'}</p>
            </div>
          `);

          layerGroups.clusterCenters.addLayer(marker);
        }
      });
    }

    // Add NTC connections
    if (transmissionData.ntc_connections) {
      transmissionData.ntc_connections.forEach(connection => {
        const fromCenter = transmissionData.cluster_centers?.find(c => c.cluster_id === connection.from_id);
        const toCenter = transmissionData.cluster_centers?.find(c => c.cluster_id === connection.to_id);
        
        if (fromCenter && toCenter && fromCenter.center_lat && fromCenter.center_lng && 
            toCenter.center_lat && toCenter.center_lng) {
          
          const line = L.polyline([
            [fromCenter.center_lat, fromCenter.center_lng],
            [toCenter.center_lat, toCenter.center_lng]
          ], {
            color: CONFIG.colors.transmission.ntc,
            weight: CONFIG.lines.ntc.weight,
            opacity: CONFIG.lines.ntc.opacity,
            dashArray: CONFIG.lines.ntc.dashArray
          });

          line.bindPopup(`
            <div class="p-2">
              <h3 class="font-semibold text-sm">NTC Connection</h3>
              <p class="text-xs text-gray-600">From: ${connection.from_region}</p>
              <p class="text-xs text-gray-600">To: ${connection.to_region}</p>
              <p class="text-xs text-gray-600">Distance: ${connection.distance_km} km</p>
              <p class="text-xs text-gray-600">NTC: ${connection.estimated_ntc_mw} MW</p>
            </div>
          `);

          layerGroups.ntcConnections.addLayer(line);
        }
      });
    }

    // Add transmission infrastructure to demand cluster
    loadTransmissionInfrastructure(mapInstance, layerGroups, networkData);
  }, [transmissionData, networkData, createPopulationMarker, loadTransmissionInfrastructure, getRegionColor]);

  // Load generation cluster data (transmission + power plants)
  const loadGenerationClusterData = useCallback((mapInstance, layerGroups) => {
    if (!mapInstance) return;

    // Clear existing data
    Object.values(layerGroups).forEach(group => {
      group.clearLayers();
    });

    // Add transmission infrastructure to generation cluster
    loadTransmissionInfrastructure(mapInstance, layerGroups, networkData);

    // Add power plants from generation data
    if (generationData && generationData.plants) {
      generationData.plants.forEach(plant => {
        if (plant.lat && plant.lng) {
          const marker = createPowerPlantMarker(plant);
          layerGroups.powerPlants.addLayer(marker);
        }
      });
    }
  }, [networkData, generationData, loadTransmissionInfrastructure, createPowerPlantMarker]);

  const initializeMap = useCallback((mapRef, mapInstanceRef, layerGroupsRef, mapType = 'demand') => {
    if (!transmissionData || !transmissionData.demand_points || transmissionData.demand_points.length === 0) {
      return;
    }

    // Calculate map bounds from demand points
    const coordinates = transmissionData.demand_points.map(point => [point.lat, point.lng]);
    const bounds = calculateMapBounds(coordinates, 0.1);

    // Create map with clean styling
    const map = createMap(mapRef.current, {
      defaultStyle: 'CLEAN_MINIMAL'
    });
    mapInstanceRef.current = map;

    // Fit bounds to data
    map.fitBounds(bounds, { padding: [20, 20] });

    // Initialize base layer groups
    layerGroupsRef.current = {
      populationPoints: L.layerGroup(),
      clusterCenters: L.layerGroup(),
      ntcConnections: L.layerGroup(),
      transmissionBuses: L.layerGroup(),
      powerPlants: L.layerGroup()
    };

    // Add dynamic voltage layer groups based on network data
    if (networkData && networkData.statistics && networkData.statistics.line_voltage_levels) {
      Object.keys(networkData.statistics.line_voltage_levels).forEach(voltageKey => {
        const layerKey = voltageKey.toLowerCase().replace('kv', 'kV');
        layerGroupsRef.current[layerKey] = L.layerGroup();
      });
    }

    // Add layer groups to map
    Object.values(layerGroupsRef.current).forEach(group => {
      group.addTo(map);
    });

    // Load data based on map type
    if (mapType === 'demand') {
      loadDemandClusterData(map, layerGroupsRef.current);
    } else if (mapType === 'generation') {
      loadGenerationClusterData(map, layerGroupsRef.current);
    }
  }, [transmissionData, loadDemandClusterData, loadGenerationClusterData, networkData]);

  const initializeBothMaps = useCallback(() => {
    if (!transmissionData || !transmissionData.demand_points || transmissionData.demand_points.length === 0) {
      return;
    }

    // Initialize first map (Demand Cluster)
    initializeMap(mapRef, mapInstanceRef, layerGroupsRef, 'demand');
    
    // Initialize second map (Generation Cluster)
    initializeMap(mapRef2, mapInstanceRef2, layerGroupsRef2, 'generation');
  }, [transmissionData, initializeMap]);

  const updateLayerVisibility = useCallback(() => {
    // Layer configuration: which maps each layer should appear on
    const layerConfig = {
      populationPoints: ['demand'],
      clusterCenters: ['demand'],
      ntcConnections: ['demand'],
      transmissionBuses: ['demand', 'generation'],
      powerPlants: ['generation']
    };

    const updateMapLayers = (mapInstance, layerGroups, mapType) => {
      if (!mapInstance) return;

      Object.keys(layerVisibility).forEach(layerKey => {
        const group = layerGroups[layerKey];
        if (group) {
          const shouldShow = layerVisibility[layerKey] && 
                            (layerConfig[layerKey]?.includes(mapType) || 
                             layerKey.includes('kV')); // Voltage layers show on both maps
          
          if (shouldShow) {
            group.addTo(mapInstance);
          } else {
            group.remove();
          }
        }
      });
    };

    // Update both maps with appropriate data
    if (mapInstanceRef.current && layerGroupsRef.current) {
      updateMapLayers(mapInstanceRef.current, layerGroupsRef.current, 'demand');
    }
    if (mapInstanceRef2.current && layerGroupsRef2.current) {
      updateMapLayers(mapInstanceRef2.current, layerGroupsRef2.current, 'generation');
    }
  }, [layerVisibility]);

  // Handle map style changes
  const handleMapStyleChange = useCallback((newStyle) => {
    setMapStyle(newStyle);
    
    // Find the style key for the selected style
    const styleKey = Object.keys(MAP_STYLES).find(key => MAP_STYLES[key].name === newStyle.name);
    
    // Update both maps if they exist
    const updateMapStyle = (mapInstance) => {
      if (mapInstance) {
        mapInstance.eachLayer((layer) => {
          if (layer instanceof L.TileLayer) {
            mapInstance.removeLayer(layer);
          }
        });
        const newTileLayer = createTileLayer(styleKey);
        newTileLayer.addTo(mapInstance);
      }
    };

    updateMapStyle(mapInstanceRef.current);
    updateMapStyle(mapInstanceRef2.current);
  }, []);

  // Simple data loading flow: 3 calls for 2 maps
  useEffect(() => {
    if (!countryIso) return;
    
    const loadAllData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // 1. Load Population Data (for Demand Cluster map)
        const populationResponse = await transmissionAPI.getTransmissionData(countryIso, clusters);
        if (!populationResponse.success) {
          throw new Error(populationResponse.error || 'Failed to load population data');
        }
        setTransmissionData(populationResponse.data);
        
        // 2. Load Generation Data (for Generation Cluster map)
        const generationResponse = await transmissionAPI.getTransmissionGenerationData(countryIso);
        if (!generationResponse.success) {
          throw new Error(generationResponse.error || 'Failed to load generation data');
        }
        setGenerationData(generationResponse.data);
        
        // 3. Load Transmission Data (for both maps)
        const transmissionResponse = await transmissionAPI.getTransmissionNetworkData(countryIso);
        if (!transmissionResponse.success) {
          throw new Error(transmissionResponse.error || 'Failed to load transmission data');
        }
        setNetworkData(transmissionResponse.data);
        
        toast.success('All data loaded successfully');
      } catch (err) {
        setError(err.message);
        toast.error(`Failed to load data: ${err.message}`);
        console.error('Error loading data:', err);
      } finally {
        setLoading(false);
      }
    };
    
    loadAllData();
  }, [countryIso, clusters]);

  // Update layer visibility when network data loads (only once when data changes)
  useEffect(() => {
    if (networkData && networkData.statistics && networkData.statistics.line_voltage_levels) {
      setLayerVisibility(prevVisibility => {
        const newLayerVisibility = { ...prevVisibility };
        
        // Add voltage layers with default visibility (only if they don't exist)
        Object.keys(networkData.statistics.line_voltage_levels).forEach(voltageKey => {
          const layerKey = voltageKey.toLowerCase().replace('kv', 'kV');
          if (!(layerKey in newLayerVisibility)) {
            newLayerVisibility[layerKey] = true; // Default to visible only for new layers
          }
        });
        
        return newLayerVisibility;
      });
    }
  }, [networkData]);

  useEffect(() => {
    if (transmissionData && mapRef.current && mapRef2.current && !mapInstanceRef.current && !mapInstanceRef2.current) {
      initializeBothMaps();
    }
    
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
      if (mapInstanceRef2.current) {
        mapInstanceRef2.current.remove();
        mapInstanceRef2.current = null;
      }
    };
  }, [transmissionData, initializeBothMaps]);

  useEffect(() => {
    if (mapInstanceRef.current || mapInstanceRef2.current) {
      updateLayerVisibility();
    }
  }, [updateLayerVisibility, transmissionData, networkData]);

  const toggleLayer = (layerKey) => {
    setLayerVisibility(prev => ({
      ...prev,
      [layerKey]: !prev[layerKey]
    }));
  };

  const handleClustersChange = (newClusters) => {
    setClusters(newClusters);
  };


  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading transmission data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-4" />
          <div className="text-red-500 text-lg font-medium mb-2">Error Loading Data</div>
          <div className="text-gray-600 text-sm mb-4">{error}</div>
          <button 
            onClick={async () => {
              if (!countryIso) return;
              
              try {
                setLoading(true);
                setError(null);
                
                // Retry loading all data
                const populationResponse = await transmissionAPI.getTransmissionData(countryIso, clusters);
                if (!populationResponse.success) {
                  throw new Error(populationResponse.error || 'Failed to load population data');
                }
                setTransmissionData(populationResponse.data);
                
                const generationResponse = await transmissionAPI.getTransmissionGenerationData(countryIso);
                if (!generationResponse.success) {
                  throw new Error(generationResponse.error || 'Failed to load generation data');
                }
                setGenerationData(generationResponse.data);
                
                const transmissionResponse = await transmissionAPI.getTransmissionNetworkData(countryIso);
                if (!transmissionResponse.success) {
                  throw new Error(transmissionResponse.error || 'Failed to load transmission data');
                }
                setNetworkData(transmissionResponse.data);
                
                toast.success('All data loaded successfully');
              } catch (err) {
                setError(err.message);
                toast.error(`Failed to load data: ${err.message}`);
                console.error('Error loading data:', err);
              } finally {
                setLoading(false);
              }
            }}
            className="btn-primary"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!transmissionData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center text-gray-500">
          <MapPin className="h-8 w-8 mx-auto mb-4" />
          <div className="text-lg font-medium mb-2">No Transmission Data</div>
          <div className="text-sm">No transmission data available for this country.</div>
        </div>
      </div>
    );
  }

  const { summary } = transmissionData;
  const networkStats = networkData?.statistics || {};
  const generationStats = generationData?.statistics || {};

  return (
    <div className="h-screen flex flex-col">
    

      {/* Statistics Cards */}
      <div className="p-3 sm:p-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 sm:gap-4">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4">
            <div className="flex items-center">
              <MapPin className="h-4 w-4 sm:h-5 sm:w-5 text-indigo-600 mr-2" />
              <div>
                <p className="text-xs sm:text-sm text-gray-600">Total Regions</p>
                <p className="text-base sm:text-lg font-semibold text-gray-900">{summary?.total_regions || 0}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4">
            <div className="flex items-center">
              <BarChart3 className="h-4 w-4 sm:h-5 sm:w-5 text-green-600 mr-2" />
              <div>
                <p className="text-xs sm:text-sm text-gray-600">Demand Points</p>
                <p className="text-base sm:text-lg font-semibold text-gray-900">{summary?.total_demand_points || 0}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4">
            <div className="flex items-center">
              <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-600 mr-2" />
              <div>
                <p className="text-xs sm:text-sm text-gray-600">NTC Connections</p>
                <p className="text-base sm:text-lg font-semibold text-gray-900">{summary?.total_ntc_connections || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4">
            <div className="flex items-center">
              <Power className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600 mr-2" />
              <div>
                <p className="text-xs sm:text-sm text-gray-600">Demand Buses</p>
                <p className="text-base sm:text-lg font-semibold text-gray-900">{networkStats.total_buses || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4">
            <div className="flex items-center">
              <Zap className="h-4 w-4 sm:h-5 sm:w-5 text-red-600 mr-2" />
              <div>
                <p className="text-xs sm:text-sm text-gray-600">Generation Buses</p>
                <p className="text-base sm:text-lg font-semibold text-gray-900">{generationStats.total_buses || 0}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 sm:p-4">
            <div className="flex items-center">
              <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-purple-600 mr-2" />
              <div>
                <p className="text-xs sm:text-sm text-gray-600">Avg Region Size</p>
                <p className="text-base sm:text-lg font-semibold text-gray-900">
                  {summary?.average_region_size ? Math.round(summary.average_region_size).toLocaleString() : 0}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="px-4 sm:px-6 py-4 sm:py-6">
        {/* Maps - Clean Card Structure */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4 mb-3 sm:mb-4">
          
          
          {/* Demand Cluster Map Card */}
          <div className="bg-white rounded-lg hover:shadow-sm transition-shadow" description="Demand Cluster Map - Shows population-based demand regions with NTC connections, transmission buses, and voltage-specific transmission lines">
            <div className="flex justify-between items-start p-3">
              <div className="flex items-center space-x-4">
                <div>
                  <h3 className="text-base font-semibold text-gray-900 mb-1">Demand Cluster</h3>
                </div>
                <div className="flex items-center space-x-2">
                  
                  <label className="text-xs text-gray-600">Clusters:</label>
                  <select
                    value={clusters}
                    onChange={(e) => handleClustersChange(parseInt(e.target.value))}
                    className="px-2 py-1 border border-gray-300 rounded text-xs"
                  >
                    <option value={6}>6</option>
                    <option value={8}>8</option>
                    <option value={10}>10</option>
                    <option value={12}>12</option>
                    <option value={15}>15</option>
                    <option value={20}>20</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="chart-container">
              <div className="relative" style={{ height: '500px' }}>
                <div 
                  ref={mapRef}
                  className="w-full h-full"
                />
              </div>
            </div>
          </div>
          
          {/* Generation Cluster Map Card */}
          <div className="bg-white rounded-lg hover:shadow-sm transition-shadow" description="Generation Cluster Map - Shows power plants, transmission infrastructure, buses, and voltage-specific transmission lines">
            <div className="flex justify-between items-start p-3">
              <div>
                <h3 className="text-base font-semibold text-gray-900 mb-1">Generation</h3>
                
              </div>
            </div>
            <div className="chart-container">
              <div className="relative" style={{ height: '500px' }}>
                <div 
                  ref={mapRef2}
                  className="w-full h-full"
                />
              </div>
            </div>
          </div>
          
        </div>
      </div>

      {/* Map Layers Control Section */}
      <div className="bg-white rounded-lg hover:shadow-sm transition-shadow p-4">
        <div className="flex items-center mb-3">
          <Layers className="h-5 w-5 text-gray-600 mr-2" />
          <h3 className="text-base font-semibold text-gray-900">Map Layers Control</h3>
        </div>
        
        {/* Map Style Selector */}
        <div className="mb-4 pb-3 border-b border-gray-100">
          <div className="flex items-center space-x-2">
            <Settings className="h-4 w-4 text-gray-600" />
            <label className="text-sm text-gray-600">Map Style:</label>
            <select
              value={mapStyle.name}
              onChange={(e) => {
                const selectedStyle = Object.values(MAP_STYLES).find(style => style.name === e.target.value);
                if (selectedStyle) {
                  handleMapStyleChange(selectedStyle);
                }
              }}
              className="text-sm border border-gray-300 rounded px-3 py-1 bg-white"
            >
              {Object.values(MAP_STYLES).map(style => (
                <option key={style.name} value={style.name}>
                  {style.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          {/* Demand Cluster Layers */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 mb-2">Demand Cluster Only</p>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-gray-400 rounded-full mr-2"></div>
                <span>Demand Points ({summary?.total_demand_points || 0})</span>
              </div>
              <button
                onClick={() => toggleLayer('populationPoints')}
                className="text-gray-500 hover:text-gray-700"
              >
                {layerVisibility.populationPoints ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              </button>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-gray-600 mr-2" style={{ borderRadius: '2px' }}></div>
                <span>Cluster Centers ({summary?.total_regions || 0})</span>
              </div>
              <button
                onClick={() => toggleLayer('clusterCenters')}
                className="text-gray-500 hover:text-gray-700"
              >
                {layerVisibility.clusterCenters ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              </button>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-4 h-0.5 bg-gray-500 mr-2" style={{ borderTop: '2px dashed #666' }}></div>
                <span>NTC Connections ({summary?.total_ntc_connections || 0})</span>
              </div>
              <button
                onClick={() => toggleLayer('ntcConnections')}
                className="text-gray-500 hover:text-gray-700"
              >
                {layerVisibility.ntcConnections ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Transmission Infrastructure Layers */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 mb-2">Both Maps</p>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div>
                <span>Transmission Buses ({networkStats.total_buses || 0})</span>
              </div>
              <button
                onClick={() => toggleLayer('transmissionBuses')}
                className="text-gray-500 hover:text-gray-700"
              >
                {layerVisibility.transmissionBuses ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              </button>
            </div>
            
            {/* Dynamic voltage layers */}
            {networkStats.line_voltage_levels && Object.entries(networkStats.line_voltage_levels)
              .sort(([a], [b]) => parseInt(b.replace('kV', '')) - parseInt(a.replace('kV', '')))
              .map(([voltageKey, count]) => {
                const layerKey = voltageKey.toLowerCase().replace('kv', 'kV');
                const voltage = parseInt(voltageKey.replace('kV', ''));
                
                // Get color based on voltage level
                const getVoltageColor = (voltage) => {
                  if (voltage >= 500) return 'bg-red-600';
                  if (voltage >= 400) return 'bg-red-500';
                  if (voltage >= 300) return 'bg-orange-500';
                  if (voltage >= 200) return 'bg-yellow-500';
                  if (voltage >= 100) return 'bg-green-500';
                  return 'bg-gray-500';
                };
                
                return (
                  <div key={voltageKey} className="flex items-center justify-between">
                    <div className="flex items-center">
                      <div className={`w-4 h-0.5 ${getVoltageColor(voltage)} mr-2`}></div>
                      <span>{voltageKey} Lines ({count})</span>
                    </div>
                    <button
                      onClick={() => toggleLayer(layerKey)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      {layerVisibility[layerKey] ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                    </button>
                  </div>
                );
              })}
          </div>

          {/* Generation Cluster Layers */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 mb-2">Generation Cluster Only</p>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                <span>Power Plants ({generationStats.total_plants || 0})</span>
              </div>
              <button
                onClick={() => toggleLayer('powerPlants')}
                className="text-gray-500 hover:text-gray-700"
              >
                {layerVisibility.powerPlants ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TransmissionLineTab;

