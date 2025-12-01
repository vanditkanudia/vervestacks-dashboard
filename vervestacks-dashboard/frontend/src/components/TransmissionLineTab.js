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
import { initializeFuelColors, getFuelColor as getFuelColorFromCache } from '../utils/fuelColors';
import { transmissionAPI } from '../services/api';

// Configuration constants
const CONFIG = {
  colors: {
    region: [
      '#E7A396', '#EACE84', '#BAB9E1', '#D9A1C0', '#F7A978', '#F0ACB7', '#F8E5EB', '#EBCFB2',
      '#DDE4BE', '#B0E3CD', '#BDD4F6', '#CCCBF2', '#CAD892', '#969A60', '#758D46', '#98D0F5',
      '#5E9DBE', '#3C8782', '#EB5A6D', '#F3C9E4', '#EEADA7', '#BDBDBD', '#F9F4BC', '#FAF5AF',
      '#AD9281', '#F2C6C7', '#EB7757', '#ED6C84', '#83A061', '#A0BA46'
    ],
    voltage: {
      high: '#d62728',    // Red for 380kV+
      medium: '#ff7f0e',  // Orange for 220kV
      low: '#2ca02c',     // Green for 110kV
      default: '#7f7f7f'  // Gray for lower voltages
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
    transmission: { weight: 1, opacity: 1, smoothFactor: 0, lineCap: 'round' },
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

  useEffect(() => {
    initializeFuelColors().catch(error => {
      console.error('Failed to initialize fuel colors:', error);
    });
  }, []);

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
    const serviceColor = getFuelColorFromCache(fuelType);
    if (serviceColor && serviceColor !== '#7F8C8D') {
      return serviceColor;
    }
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

  const transmissionBusMarkersRef = useRef([]);
  const transmissionBusMarkersRef2 = useRef([]);

  const createTransmissionBusMarker = useCallback((bus) => {
    const config = {
      radius: 4,
      fillColor: '#dc2626',
      color: '#dc2626',
      weight: 1,
      opacity: 1,
      fillOpacity: 0  // Transparent fill, only border visible
    };
    
    const popupContent = `
      <div class="p-2">
        <h3 class="font-semibold text-sm">${bus.name}</h3>
        <p class="text-xs text-gray-600">Type: Transmission Bus</p>
        <p class="text-xs text-gray-600">Voltage: ${bus.voltage} kV</p>
      </div>
    `;
    
    const marker = createMarker(bus.lat, bus.lng, config, popupContent);
    if (marker) {
      marker.options.baseRadius = config.radius;
    }
    return marker;
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
      color: "transparent",
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
    
    const marker = createMarker(plant.lat, plant.lng, config, popupContent);
    if (marker) {
      marker.options.baseRadius = config.radius;
    }
    return marker;
  }, [createMarker, getMarkerSize, getFuelColor]);

  // Helper function to load transmission infrastructure (buses and lines)
  // Order: Lines first (will be bottom), then buses (will be on top of lines)
  // But we want lines on top, so we'll add buses first, then lines
  const loadTransmissionInfrastructure = useCallback((mapInstance, layerGroups, data, busMarkersRef = null) => {
    if (!data) return;

    // Add transmission buses first (middle layer)
    if (busMarkersRef) {
      busMarkersRef.current = [];
    }

    if (data.buses) {
      data.buses.forEach(bus => {
        if (bus.lat && bus.lng) {
          const marker = createTransmissionBusMarker(bus);
          if (marker) {
            layerGroups.transmissionBuses.addLayer(marker);
            if (busMarkersRef) {
              busMarkersRef.current.push(marker);
            }
          }
        }
      });
    }

    // Add transmission lines last (top layer - appears on top of buses)
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

  const updateTransmissionBusMarkerSizes = useCallback((mapInstance, busMarkersRef) => {
    if (!mapInstance || !busMarkersRef?.current?.length) return;

    const zoom = mapInstance.getZoom();
    const baseZoom = 7;
    const zoomDiff = zoom - baseZoom;
    const scale = Math.max(0.2, Math.min(2.2, Math.pow(1.3, zoomDiff)));

    busMarkersRef.current.forEach(marker => {
      if (marker && marker.options?.baseRadius) {
        marker.setRadius(marker.options.baseRadius * scale);
      }
    });
  }, []);

  // Load demand cluster data (population, clusters + transmission)
  // Layer order (bottom to top): Demand points -> Transmission buses -> Transmission lines
  const loadDemandClusterData = useCallback((mapInstance, layerGroups) => {
    if (!mapInstance || !transmissionData) return;

    // Clear existing data
    Object.values(layerGroups).forEach(group => {
      group.clearLayers();
    });

    // Step 1: Add demand points first (bottom layer)
    if (transmissionData.demand_points) {
      transmissionData.demand_points.forEach((point, index) => {
        if (point.lat && point.lng && point.cluster !== undefined) {
          const marker = createPopulationMarker(point);
          layerGroups.populationPoints.addLayer(marker);
        }
      });
    }

    // Step 2: Add cluster centers (also bottom layer, same level as demand points)
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

    // Step 3: Add transmission infrastructure (buses then lines)
    // This ensures buses are added before lines, so lines appear on top
    loadTransmissionInfrastructure(mapInstance, layerGroups, networkData, transmissionBusMarkersRef);
    updateTransmissionBusMarkerSizes(mapInstance, transmissionBusMarkersRef);
  }, [transmissionData, networkData, createPopulationMarker, loadTransmissionInfrastructure, getRegionColor, updateTransmissionBusMarkerSizes]);

  // Load generation cluster data (transmission + power plants)
  const powerPlantMarkersRef = useRef([]);

  const updatePowerPlantMarkerSizes = useCallback((mapInstance) => {
    if (!mapInstance || !powerPlantMarkersRef.current?.length) return;

    const zoom = mapInstance.getZoom();
    const baseZoom = 7;
    const zoomDiff = zoom - baseZoom;
    const scale = Math.max(0.15, Math.min(3, Math.pow(1.35, zoomDiff)));

    powerPlantMarkersRef.current.forEach(marker => {
      if (marker && marker.options?.baseRadius) {
        marker.setRadius(marker.options.baseRadius * scale);
      }
    });
  }, []);

  const loadGenerationClusterData = useCallback((mapInstance, layerGroups) => {
    if (!mapInstance) return;

    // Clear existing data
    Object.values(layerGroups).forEach(group => {
      group.clearLayers();
    });
    powerPlantMarkersRef.current = [];

    // Layer order (bottom to top): Power plants -> Transmission buses -> Transmission lines
    
    // Step 1: Add power plants first (middle layer, same level as buses)
    if (generationData && generationData.plants) {
      generationData.plants.forEach(plant => {
        if (plant.lat && plant.lng) {
          const marker = createPowerPlantMarker(plant);
          if (marker) {
            layerGroups.powerPlants.addLayer(marker);
            powerPlantMarkersRef.current.push(marker);
          }
        }
      });
    }

    // Step 2: Add transmission infrastructure (buses then lines)
    // This ensures buses are added before lines, so lines appear on top
    loadTransmissionInfrastructure(mapInstance, layerGroups, networkData, transmissionBusMarkersRef2);
    
    updatePowerPlantMarkerSizes(mapInstance);
    updateTransmissionBusMarkerSizes(mapInstance, transmissionBusMarkersRef2);
  }, [networkData, generationData, loadTransmissionInfrastructure, createPowerPlantMarker, updatePowerPlantMarkerSizes, updateTransmissionBusMarkerSizes]);

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

    // Add layer groups to map in correct z-index order (bottom to top):
    // 1. Demand points (bottom)
    // 2. Cluster centers (same level as demand points)
    // 3. Transmission buses (middle)
    // 4. Power plants (for generation map)
    // 5. Transmission lines (top) - voltage layers added last
    
    // Add base layers first (bottom)
    if (layerGroupsRef.current.populationPoints) {
      layerGroupsRef.current.populationPoints.addTo(map);
    }
    if (layerGroupsRef.current.clusterCenters) {
      layerGroupsRef.current.clusterCenters.addTo(map);
    }
    if (layerGroupsRef.current.transmissionBuses) {
      layerGroupsRef.current.transmissionBuses.addTo(map);
    }
    if (layerGroupsRef.current.powerPlants) {
      layerGroupsRef.current.powerPlants.addTo(map);
    }
    
    // Add voltage layers last (top layer - transmission lines)
    if (networkData && networkData.statistics && networkData.statistics.line_voltage_levels) {
      Object.keys(networkData.statistics.line_voltage_levels).forEach(voltageKey => {
        const layerKey = voltageKey.toLowerCase().replace('kv', 'kV');
        if (layerGroupsRef.current[layerKey]) {
          layerGroupsRef.current[layerKey].addTo(map);
        }
      });
    }

    // Load data based on map type
    if (mapType === 'demand') {
      loadDemandClusterData(map, layerGroupsRef.current);
      map.on('zoomend', () => updateTransmissionBusMarkerSizes(map, transmissionBusMarkersRef));
    } else if (mapType === 'generation') {
      loadGenerationClusterData(map, layerGroupsRef.current);
      map.on('zoomend', () => {
        updatePowerPlantMarkerSizes(map);
        updateTransmissionBusMarkerSizes(map, transmissionBusMarkersRef2);
      });
    }
  }, [transmissionData, loadDemandClusterData, loadGenerationClusterData, networkData, updatePowerPlantMarkerSizes, updateTransmissionBusMarkerSizes]);

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
      transmissionBuses: ['demand', 'generation'],
      powerPlants: ['generation']
    };

    const updateMapLayers = (mapInstance, layerGroups, mapType) => {
      if (!mapInstance) return;

      // Define z-index order (bottom to top)
      const zIndexOrder = [
        'populationPoints',    // Bottom
        'clusterCenters',      // Bottom (same level)
        'transmissionBuses',   // Middle
        'powerPlants'          // Middle (for generation map)
      ];

      // First, remove all layers
      Object.keys(layerVisibility).forEach(layerKey => {
        const group = layerGroups[layerKey];
        if (group) {
          const shouldShow = layerVisibility[layerKey] && 
                            (layerConfig[layerKey]?.includes(mapType) || 
                             layerKey.includes('kV')); // Voltage layers show on both maps
          
          if (!shouldShow) {
            group.remove();
          }
        }
      });

      // Then add layers back in correct z-index order (bottom to top)
      zIndexOrder.forEach(layerKey => {
        const group = layerGroups[layerKey];
        if (group) {
          const shouldShow = layerVisibility[layerKey] && 
                            (layerConfig[layerKey]?.includes(mapType) || 
                             layerKey.includes('kV'));
          
          if (shouldShow) {
            group.addTo(mapInstance);
          }
        }
      });

      // Add voltage layers last (top layer - transmission lines)
      Object.keys(layerVisibility).forEach(layerKey => {
        if (layerKey.includes('kV')) {
          const group = layerGroups[layerKey];
          if (group && layerVisibility[layerKey]) {
            group.addTo(mapInstance);
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
          // Check if this is a "no data" case vs technical error
          if (transmissionResponse.noData) {
            // For "no data" cases, set networkData to null but don't throw error
            // The component will handle this gracefully
            setNetworkData(null);
          } else {
            throw new Error(transmissionResponse.error || 'Failed to load transmission data');
          }
        } else {
          setNetworkData(transmissionResponse.data);
        }
        
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

  const { summary } = transmissionData || {};
  const networkStats = networkData?.statistics || {};
  const generationStats = generationData?.statistics || {};

  return (
    <div className="h-screen flex flex-col">
      <div className="px-4 sm:px-6 py-4 sm:py-6">
        {/* Maps - Clean Card Structure */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4 mb-3 sm:mb-4">
          
          
          {/* Demand Cluster Map Card */}
          <div className="bg-white rounded-lg hover:shadow-sm transition-shadow" description="Demand Cluster Map - Shows population-based demand regions with transmission buses and voltage-specific transmission lines">
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

