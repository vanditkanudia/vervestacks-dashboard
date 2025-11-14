/**
 * WindMap Component
 * 
 * A dedicated component for rendering wind renewable energy potential data
 * (both onshore and offshore) on an interactive Leaflet map.
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

const WindMap = forwardRef(({ 
  onshoreWindData, 
  offshoreWindData,
  onshoreWindThresholds, 
  offshoreWindThresholds,
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
    console.log('💨 WindMap: Creating GeoJSON layer with', geoJsonData.features.length, 'features');
    
    const layer = L.geoJSON(geoJsonData, {
      style: styleFunction,
      onEachFeature: onEachFeature
    });
    
    return layer;
  }, []);

  // Render wind zone shapes
  const renderWindZoneShapes = useCallback((map, onshoreData, offshoreData) => {
    if (!map) {
      setGeometryLoading(false);
      return;
    }
    
    // Set geometry loading state
    setGeometryLoading(true);
    
    // Handle empty data
    if ((!onshoreData || !onshoreData.grid_data || onshoreData.grid_data.length === 0) && 
        (!offshoreData || !offshoreData.grid_data || offshoreData.grid_data.length === 0)) {
      // Clear existing layers if no data
      map.eachLayer((layer) => {
        if (layer instanceof L.CircleMarker || layer instanceof L.GeoJSON) {
          map.removeLayer(layer);
        }
      });
      setGeometryLoading(false);
      return;
    }

    // Smart layer management - check for existing layers
    let existingOnshoreLayer = null;
    let existingOffshoreLayer = null;
    map.eachLayer((layer) => {
      if (layer instanceof L.GeoJSON) {
        if (layer.options.onshoreWindLayer) existingOnshoreLayer = layer;
        if (layer.options.offshoreWindLayer) existingOffshoreLayer = layer;
      }
    });

    // Only re-render if we don't have existing layers or zoom changed significantly
    if (existingOnshoreLayer && existingOffshoreLayer) {
      const currentZoom = map.getZoom();
      const lastOnshoreZoom = existingOnshoreLayer.options.lastZoom || 0;
      const lastOffshoreZoom = existingOffshoreLayer.options.lastZoom || 0;
      
      // Only re-render if zoom level changed significantly (more than 2 levels)
      if (Math.abs(currentZoom - lastOnshoreZoom) < 2 && Math.abs(currentZoom - lastOffshoreZoom) < 2) {
        setGeometryLoading(false);
        return;
      }
      
      // Clear existing layers for re-render
      if (existingOnshoreLayer) map.removeLayer(existingOnshoreLayer);
      if (existingOffshoreLayer) map.removeLayer(existingOffshoreLayer);
    }

    // Get current map bounds and zoom level for performance optimization
    const mapBounds = map.getBounds();
    const zoomLevel = map.getZoom();

    // Render onshore wind shapes
    if (onshoreData && onshoreData.grid_data && onshoreData.grid_data.length > 0) {
      const onshoreZones = onshoreData.grid_data;
      
      // Optimize GeoJSON data based on current view
      const onshoreGeoJsonData = optimizeGeoJSONData(onshoreZones, mapBounds, zoomLevel);
      
      // Only render if we have features to display
      if (onshoreGeoJsonData.features.length > 0) {
        const onshoreLayer = createGeoJSONLayer(
          onshoreGeoJsonData,
          (feature) => getZoneStyle(feature, 'onshore_wind', onshoreWindThresholds, zoomLevel),
          (feature, layer) => {
            const zone = feature.properties;
            
            layer.bindPopup(createZonePopup(zone, 'onshore_wind'));
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

        // Mark this layer as onshore wind layer for future identification
        onshoreLayer.options.onshoreWindLayer = true;
        onshoreLayer.options.lastZoom = map.getZoom();
        onshoreLayer.addTo(map);
      }
    }

    // Render offshore wind shapes
    if (offshoreData && offshoreData.grid_data && offshoreData.grid_data.length > 0) {
      const offshoreZones = offshoreData.grid_data;
      
      // Optimize GeoJSON data based on current view
      const offshoreGeoJsonData = optimizeGeoJSONData(offshoreZones, mapBounds, zoomLevel);
      
      // Only render if we have features to display
      if (offshoreGeoJsonData.features.length > 0) {
        const offshoreLayer = createGeoJSONLayer(
          offshoreGeoJsonData,
          (feature) => getZoneStyle(feature, 'offshore_wind', offshoreWindThresholds, zoomLevel),
          (feature, layer) => {
            const zone = feature.properties;
            
            layer.bindPopup(createZonePopup(zone, 'offshore_wind'));
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

        // Mark this layer as offshore wind layer for future identification
        offshoreLayer.options.offshoreWindLayer = true;
        offshoreLayer.options.lastZoom = map.getZoom();
        offshoreLayer.addTo(map);
      }
    }
    
    // Clear geometry loading state
    setGeometryLoading(false);
  }, [createGeoJSONLayer, onshoreWindThresholds, offshoreWindThresholds, onZoneSelect]);

  // Initialize map
  const initializeWindMap = useCallback(() => {
    if (!mapRef.current) return;

    try {
      // Only initialize if map doesn't exist
      if (!mapInstanceRef.current) {
        // Calculate bounds from ALL available data
        let coordinates = [];
        
        // Helper function to extract coordinates from zone
        const extractCoordinates = (zone) => {
          if (zone.lat && zone.lng) {
            coordinates.push([zone.lat, zone.lng]);
          } else if (zone.geometry && zone.geometry.type === 'Polygon') {
            // Extract coordinates from polygon geometry
            const coords = zone.geometry.coordinates[0];
            coords.forEach(coord => {
              coordinates.push([coord[1], coord[0]]); // lat, lng
            });
          }
        };
        
        if (onshoreWindData?.grid_data?.length > 0) {
          onshoreWindData.grid_data.forEach(extractCoordinates);
        }
        if (offshoreWindData?.grid_data?.length > 0) {
          offshoreWindData.grid_data.forEach(extractCoordinates);
        }

        // Initialize map with clean styling
        const map = createMap(mapRef.current, {
          defaultStyle: 'CLEAN_MINIMAL'
        });
        mapInstanceRef.current = map;

        // Always fit bounds to data if available
        if (coordinates.length > 0) {
          const bounds = calculateMapBounds(coordinates, 0.1);
          map.fitBounds(bounds, { padding: [20, 20] });
        } else {
          // Fallback to world view if no coordinates
          map.setView([0, 0], 2);
        }
      }

      // Always update shapes with both data types
      if (mapInstanceRef.current) {
        renderWindZoneShapes(mapInstanceRef.current, onshoreWindData, offshoreWindData);
      }
    } catch (error) {
      console.error('Error initializing wind map:', error);
      // Reset map reference on error
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch (removeError) {
          console.warn('Error removing wind map:', removeError);
        }
        mapInstanceRef.current = null;
      }
    }
  }, [onshoreWindData, offshoreWindData, renderWindZoneShapes]);

  // Initialize map when data is available or when component mounts
  useEffect(() => {
    if (mapRef.current) {
      // Always initialize map, even without data
      if (!mapInstanceRef.current) {
        try {
          // Initialize map with default view if no data
          const map = createMap(mapRef.current, {
            defaultStyle: 'CLEAN_MINIMAL'
          });
          mapInstanceRef.current = map;
          
           // Set default view based on data bounds or country
           const allData = [];
           if (onshoreWindData?.grid_data?.length > 0) allData.push(...onshoreWindData.grid_data);
           if (offshoreWindData?.grid_data?.length > 0) allData.push(...offshoreWindData.grid_data);
           
           if (allData.length > 0) {
             // Calculate bounds from ALL data
             let coordinates = [];
             allData.forEach(zone => {
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
        } catch (error) {
          console.error('Error initializing wind map:', error);
        }
      }
      
      // If we have data, initialize with data
      if ((onshoreWindData || offshoreWindData) && mapRef.current) {
        initializeWindMap();
      }
    }
    
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [initializeWindMap, onshoreWindData, offshoreWindData]);

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
            <div className="text-sm text-gray-600">Loading wind zones...</div>
          </div>
        </div>
      )}
      
      {/* No Data Overlay */}
      {!geometryLoading && 
       (!onshoreWindData || !onshoreWindData.grid_data || onshoreWindData.grid_data.length === 0) &&
       (!offshoreWindData || !offshoreWindData.grid_data || offshoreWindData.grid_data.length === 0) && (
        <div className="absolute inset-0 bg-gray-50 flex items-center justify-center" style={{ zIndex: 1000 }}>
          <div className="text-center text-gray-500">
            <div className="text-sm">No wind data available</div>
            <div className="text-xs mt-1">Map view centered on region</div>
          </div>
        </div>
      )}
    </div>
  );
});

export default WindMap;
