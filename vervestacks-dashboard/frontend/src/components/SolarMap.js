/**
 * SolarMap Component
 * 
 * A dedicated component for rendering solar renewable energy potential data
 * on an interactive Leaflet map with optimized performance.
 */

import React, { useRef, useEffect, useCallback, useState, forwardRef, useImperativeHandle } from 'react';
import L from 'leaflet';
import { createMap, calculateMapBounds } from '../utils/mapUtils';
import { 
  optimizeGeoJSONData, 
  createZonePopup, 
  getZoneStyle, 
  getHoverStyle
} from '../utils/renewableUtils';

const SolarMap = forwardRef(({ 
  solarData, 
  solarThresholds, 
  selectedZone, 
  onZoneSelect,
  countryIso,
  className = "w-full h-full" 
}, ref) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [geometryLoading, setGeometryLoading] = useState(false);

  // Expose map instance to parent component
  useImperativeHandle(ref, () => ({
    getMap: () => mapInstanceRef.current
  }), []);

  // Create GeoJSON layer helper
  const createGeoJSONLayer = useCallback((geoJsonData, styleFunction, onEachFeature) => {
    console.log('🌞 SolarMap: Creating GeoJSON layer with', geoJsonData.features.length, 'features');
    
    const layer = L.geoJSON(geoJsonData, {
      style: styleFunction,
      onEachFeature: onEachFeature
    });
    
    return layer;
  }, []);

  // Render solar zone shapes
  const renderSolarZoneShapes = useCallback((map, gridData) => {
    if (!map || !gridData || gridData.length === 0) {
      setGeometryLoading(false);
      return;
    }

    // Set geometry loading state
    setGeometryLoading(true);
    
    // Smart layer management - only re-render if data has changed significantly
    let existingSolarLayer = null;
    map.eachLayer((layer) => {
      if (layer instanceof L.GeoJSON && layer.options.solarLayer) {
        existingSolarLayer = layer;
      }
    });

    // Only re-render if we don't have a layer or if the data has changed significantly
    if (existingSolarLayer) {
      // Check if we need to update based on zoom level or view changes
      const currentZoom = map.getZoom();
      const lastZoom = existingSolarLayer.options.lastZoom || 0;
      
      // Only re-render if zoom level changed significantly (more than 2 levels)
      if (Math.abs(currentZoom - lastZoom) < 2) {
        setGeometryLoading(false);
        return;
      }
      
      // Clear existing layer for re-render
      map.removeLayer(existingSolarLayer);
    }

    // Get current map bounds and zoom level for performance optimization
    const mapBounds = map.getBounds();
    const zoomLevel = map.getZoom();

    // Optimize GeoJSON data based on current view
    const geoJsonData = optimizeGeoJSONData(gridData, mapBounds, zoomLevel);

    // Only render if we have features to display
    if (geoJsonData.features.length === 0) {
      setGeometryLoading(false);
      return;
    }

    // Create GeoJSON layer with styling and interactions
    const geoJsonLayer = createGeoJSONLayer(
      geoJsonData,
      (feature) => getZoneStyle(feature, 'solar', solarThresholds, zoomLevel),
      (feature, layer) => {
        const zone = feature.properties;
        
        // Add popup
        layer.bindPopup(createZonePopup(zone, 'solar'));
        
        // Add click handler
        layer.on('click', () => onZoneSelect(zone));
        
        // Add enhanced hover effects with smooth transitions
        layer.on('mouseover', (e) => {
          e.target.setStyle(getHoverStyle(zoomLevel));
          e.target.bringToFront();
        });
        
        layer.on('mouseout', (e) => {
          e.target.setStyle({
            weight: zoomLevel <= 4 ? 0.5 : zoomLevel <= 6 ? 0.8 : zoomLevel <= 8 ? 1 : 1.2,
            opacity: 0.8,
            fillOpacity: 0.6,
            color: 'white',
            dashArray: '3'
          });
        });
      }
    );

    // Mark this layer as solar layer for future identification
    geoJsonLayer.options.solarLayer = true;
    geoJsonLayer.options.lastZoom = map.getZoom();

    // Add layer to map
    geoJsonLayer.addTo(map);
    
    // Clear geometry loading state
    setGeometryLoading(false);
  }, [createGeoJSONLayer, solarThresholds, onZoneSelect]);

  // Initialize map
  const initializeMap = useCallback(() => {
    if (!mapRef.current || !solarData?.grid_data) {
      return;
    }

    const gridData = solarData.grid_data;
    if (!gridData || gridData.length === 0) {
      return;
    }

    // Only initialize if map doesn't exist
    if (!mapInstanceRef.current) {
      // Calculate bounds from ALL data - use lat/lng if available, otherwise use geometry
      let coordinates = [];
      gridData.forEach(zone => {
        if (zone.lat && zone.lng) {
          coordinates.push([zone.lat, zone.lng]);
        } else if (zone.geometry && zone.geometry.type === 'Polygon') {
          // Extract coordinates from polygon geometry
          const coords = zone.geometry.coordinates[0];
          coords.forEach(coord => {
            coordinates.push([coord[1], coord[0]]); // lat, lng
          });
        }
      });

      // Initialize map with clean styling
      const map = createMap(mapRef.current, {
        defaultStyle: 'CLEAN_MINIMAL'
      });
      mapInstanceRef.current = map;

      // Always fit bounds to data if we have coordinates
      if (coordinates.length > 0) {
        const bounds = calculateMapBounds(coordinates, 0.1);
        map.fitBounds(bounds, { padding: [20, 20] });
      } else {
        // Fallback to world view if no coordinates
        map.setView([0, 0], 2);
      }
    }

    // Always update shapes (for view changes)
    renderSolarZoneShapes(mapInstanceRef.current, gridData);
  }, [solarData, renderSolarZoneShapes]);

  // Initialize map when data is available or when component mounts
  useEffect(() => {
    if (mapRef.current) {
      // Always initialize map, even without data
      if (!mapInstanceRef.current) {
        // Initialize map with default view if no data
        const map = createMap(mapRef.current, {
          defaultStyle: 'CLEAN_MINIMAL'
        });
        mapInstanceRef.current = map;
        
        // Set default view based on data bounds or country
        if (solarData && solarData.grid_data && solarData.grid_data.length > 0) {
          // Calculate bounds from ALL data
          let coordinates = [];
          solarData.grid_data.forEach(zone => {
            if (zone.lat && zone.lng) {
              coordinates.push([zone.lat, zone.lng]);
            } else if (zone.geometry && zone.geometry.type === 'Polygon') {
              const coords = zone.geometry.coordinates[0];
              coords.forEach(coord => {
                coordinates.push([coord[1], coord[0]]); // lat, lng
              });
            }
          });
          
          if (coordinates.length > 0) {
            const bounds = calculateMapBounds(coordinates, 0.1);
            map.fitBounds(bounds, { padding: [20, 20] });
          } else {
            map.setView([0, 0], 2);
          }
        } else {
          map.setView([0, 0], 2);
        }
      }
      
      // If we have data, initialize with data
      if (solarData && solarData.grid_data) {
        initializeMap();
      }
    }
    
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [initializeMap, solarData]);

  return (
    <div className={className}>
      <div 
        ref={mapRef}
        className="w-full h-full min-h-96"
      />
      
      {/* Loading Overlay */}
      {geometryLoading && (
        <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center" style={{ zIndex: 1000 }}>
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto mb-2"></div>
            <div className="text-sm text-gray-600">Loading solar zones...</div>
          </div>
        </div>
      )}
      
      {/* No Data Overlay */}
      {!geometryLoading && (!solarData || !solarData.grid_data || solarData.grid_data.length === 0) && (
        <div className="absolute inset-0 bg-gray-50 flex items-center justify-center" style={{ zIndex: 1000 }}>
          <div className="text-center text-gray-500">
            <div className="text-sm">No solar data available</div>
            <div className="text-xs mt-1">Map view centered on region</div>
          </div>
        </div>
      )}
    </div>
  );
});

export default SolarMap;
