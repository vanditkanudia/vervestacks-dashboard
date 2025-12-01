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
  className = "w-full h-full" 
}, ref) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [mapReady, setMapReady] = useState(false);

  // Expose map instance to parent component
  useImperativeHandle(ref, () => ({
    getMap: () => mapInstanceRef.current
  }), []);

  // Create GeoJSON layer helper
  const createGeoJSONLayer = useCallback((geoJsonData, styleFunction, onEachFeature) => {
    const layer = L.geoJSON(geoJsonData, {
      style: styleFunction,
      onEachFeature: onEachFeature
    });
    
    return layer;
  }, []);

  // Render wind zone shapes - thresholds passed as parameters, not in dependencies
  const renderWindZoneShapes = useCallback((map, onshoreData, offshoreData, onshoreThresholds, offshoreThresholds) => {
    if (!map) {
      return;
    }
    
    // Handle empty data
    if ((!onshoreData || !onshoreData.grid_data || onshoreData.grid_data.length === 0) && 
        (!offshoreData || !offshoreData.grid_data || offshoreData.grid_data.length === 0)) {
      // Clear existing layers if no data
      map.eachLayer((layer) => {
        if (layer instanceof L.CircleMarker || layer instanceof L.GeoJSON) {
          map.removeLayer(layer);
        }
      });
      return;
    }

    // Remove existing layers before creating new ones
    let existingOnshoreLayer = null;
    let existingOffshoreLayer = null;
    map.eachLayer((layer) => {
      if (layer instanceof L.GeoJSON) {
        if (layer.options.onshoreWindLayer) existingOnshoreLayer = layer;
        if (layer.options.offshoreWindLayer) existingOffshoreLayer = layer;
      }
    });
    
    if (existingOnshoreLayer) map.removeLayer(existingOnshoreLayer);
    if (existingOffshoreLayer) map.removeLayer(existingOffshoreLayer);

    // Get current map bounds and zoom level for performance optimization
    const mapBounds = map.getBounds();
    const zoomLevel = map.getZoom();

    // Render onshore wind shapes
    if (onshoreData && onshoreData.grid_data && onshoreData.grid_data.length > 0 && onshoreThresholds) {
      const onshoreZones = onshoreData.grid_data;
      
      // Optimize GeoJSON data based on current view
      const onshoreGeoJsonData = optimizeGeoJSONData(onshoreZones, mapBounds, zoomLevel);
      
      // Only render if we have features to display
      if (onshoreGeoJsonData.features.length > 0) {
        const onshoreLayer = createGeoJSONLayer(
          onshoreGeoJsonData,
          (feature) => getZoneStyle(feature, 'onshore_wind', onshoreThresholds, zoomLevel),
          (feature, layer) => {
            const zone = feature.properties;
            
            // Store original feature reference for color updates
            layer.feature = feature;
            
            // Add tooltip on hover
            layer.bindTooltip(createZonePopup(zone, 'onshore_wind'), {
              permanent: false,
              direction: 'auto',
              className: 'renewable-zone-tooltip',
              offset: [15, -15] // Move tooltip further from hover point
            });
            
            // Add enhanced hover effects with smooth transitions
            layer.on('mouseover', (e) => {
              e.target.setStyle(getHoverStyle(zoomLevel));
              e.target.bringToFront();
            });
            
            layer.on('mouseout', (e) => {
              // Restore original style based on thresholds
              const originalStyle = getZoneStyle(feature, 'onshore_wind', onshoreThresholds, zoomLevel);
              e.target.setStyle({
                ...originalStyle,
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
        onshoreLayer.options.thresholds = onshoreThresholds;
        onshoreLayer.addTo(map);
      }
    }

    // Render offshore wind shapes
    if (offshoreData && offshoreData.grid_data && offshoreData.grid_data.length > 0 && offshoreThresholds) {
      const offshoreZones = offshoreData.grid_data;
      
      // Optimize GeoJSON data based on current view
      const offshoreGeoJsonData = optimizeGeoJSONData(offshoreZones, mapBounds, zoomLevel);
      
      // Only render if we have features to display
      if (offshoreGeoJsonData.features.length > 0) {
        const offshoreLayer = createGeoJSONLayer(
          offshoreGeoJsonData,
          (feature) => getZoneStyle(feature, 'offshore_wind', offshoreThresholds, zoomLevel),
          (feature, layer) => {
            const zone = feature.properties;
            
            // Store original feature reference for color updates
            layer.feature = feature;
            
            // Add tooltip on hover
            layer.bindTooltip(createZonePopup(zone, 'offshore_wind'), {
              permanent: false,
              direction: 'auto',
              className: 'renewable-zone-tooltip',
              offset: [15, -15] // Move tooltip further from hover point
            });
            
            // Add enhanced hover effects with smooth transitions
            layer.on('mouseover', (e) => {
              e.target.setStyle(getHoverStyle(zoomLevel));
              e.target.bringToFront();
            });
            
            layer.on('mouseout', (e) => {
              // Restore original style based on thresholds
              const originalStyle = getZoneStyle(feature, 'offshore_wind', offshoreThresholds, zoomLevel);
              e.target.setStyle({
                ...originalStyle,
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
        offshoreLayer.options.thresholds = offshoreThresholds;
        offshoreLayer.addTo(map);
      }
    }
  }, [createGeoJSONLayer]); // Removed onZoneSelect and thresholds from dependencies

  // Initialize map immediately when component mounts (no dependencies)
  useEffect(() => {
    // Check if map already exists (from previous mount or external source)
    if (mapInstanceRef.current) {
      setMapReady(true);
      return;
    }
    
    if (!mapRef.current) {
      return;
    }
    
    // Wait for container to be ready and have dimensions
    let retryCount = 0;
    const maxRetries = 20; // Increased retries
    
    const initMap = () => {
      // Check if map was already created (by another effect run)
      if (mapInstanceRef.current) {
        setMapReady(true);
        return;
      }
      
      if (!mapRef.current) return;
      const container = mapRef.current;
      
      // Check if container has dimensions
      const hasDimensions = container.offsetWidth > 0 && container.offsetHeight > 0;
      if (!hasDimensions && retryCount < maxRetries) {
        retryCount++;
        // Retry on next frame if container doesn't have dimensions yet
        requestAnimationFrame(initMap);
        return;
      }
      
      // Create map even if dimensions check failed (after max retries)
      try {
        const map = createMap(container, {
          defaultStyle: 'CLEAN_MINIMAL'
        });
        
        // Set initial view immediately (required before map can be used)
        map.setView([0, 0], 2, { animate: false });
        mapInstanceRef.current = map;
        setMapReady(true); // Signal that map is ready
      } catch (error) {
        console.error('Error creating wind map:', error);
      }
    };
    
    // Use requestAnimationFrame to ensure DOM is ready
    requestAnimationFrame(initMap);
    
    // Cleanup only on unmount - actually remove the map
    return () => {
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.stop();
          mapInstanceRef.current.remove();
        } catch (err) {
          console.warn('Error removing wind map:', err);
        }
        mapInstanceRef.current = null;
        setMapReady(false);
      }
    };
  }, []); // Empty deps - runs once on mount

  // Render layers only when BOTH data AND thresholds are ready (for each wind type)
  useEffect(() => {
    // Wait for map to be ready
    if (!mapReady || !mapInstanceRef.current) {
      return;
    }
    
    // Check if we have at least one wind type with both data and thresholds ready
    const onshoreReady = onshoreWindData?.grid_data?.length > 0 && onshoreWindThresholds;
    const offshoreReady = offshoreWindData?.grid_data?.length > 0 && offshoreWindThresholds;
    
    if (!onshoreReady && !offshoreReady) {
      return; // Wait for at least one to be ready
    }
    
    // Wait for map to be loaded before rendering
    const renderLayers = () => {
      if (!mapInstanceRef.current) {
        return;
      }
      
      const map = mapInstanceRef.current;
      
      // Check if map is ready - try to get center, if it fails, wait
      let mapReady = false;
      try {
        const center = map.getCenter();
        mapReady = center && typeof center.lat === 'number' && typeof center.lng === 'number';
      } catch (error) {
        mapReady = false;
      }
      
      if (!mapReady) {
        // Map not ready yet, wait for it
        if (map.whenReady) {
          map.whenReady(() => {
            setTimeout(() => {
              renderLayers();
            }, 50);
          });
        } else {
          // Retry after a short delay
          setTimeout(() => {
            renderLayers();
          }, 100);
        }
        return;
      }
      
      // Render layers first (so they're visible)
      renderWindZoneShapes(
        map, 
        onshoreReady ? onshoreWindData : null,
        offshoreReady ? offshoreWindData : null,
        onshoreWindThresholds,
        offshoreWindThresholds
      );
      
      // Fit bounds AFTER rendering (so layers are visible)
      if (!map.options.boundsSet) {
        // Calculate bounds from ALL available data for initial view
        let coordinates = [];
        const extractCoordinates = (zone) => {
          if (zone.lat && zone.lng) {
            coordinates.push([zone.lat, zone.lng]);
          } else if (zone.geometry && zone.geometry.type === 'Polygon') {
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
        
        // Fit bounds if we have coordinates
        if (coordinates.length > 0) {
          try {
            const bounds = calculateMapBounds(coordinates, 0.1);
            // Use a small delay to ensure layers are rendered first
            setTimeout(() => {
              map.fitBounds(bounds, { padding: [20, 20], animate: false });
              map.options.boundsSet = true;
            }, 100);
          } catch (error) {
            console.warn('Error fitting bounds:', error);
          }
        }
      }
    };
    
    // Use a small delay to ensure map is initialized
    const timer = setTimeout(() => {
      renderLayers();
    }, 100);
    
    return () => clearTimeout(timer);
  }, [onshoreWindData, offshoreWindData, onshoreWindThresholds, offshoreWindThresholds, renderWindZoneShapes, mapReady]);

  // Update layer colors when thresholds change (don't recreate layers)
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    
    const zoomLevel = mapInstanceRef.current.getZoom();
    
    // Update onshore layer colors
    if (onshoreWindThresholds) {
      let onshoreLayer = null;
      mapInstanceRef.current.eachLayer((layer) => {
        if (layer instanceof L.GeoJSON && layer.options.onshoreWindLayer) {
          onshoreLayer = layer;
        }
      });
      
      if (onshoreLayer) {
        onshoreLayer.eachLayer((featureLayer) => {
          if (featureLayer.feature) {
            const newStyle = getZoneStyle(featureLayer.feature, 'onshore_wind', onshoreWindThresholds, zoomLevel);
            featureLayer.setStyle(newStyle);
          }
        });
        onshoreLayer.options.thresholds = onshoreWindThresholds;
      }
    }
    
    // Update offshore layer colors
    if (offshoreWindThresholds) {
      let offshoreLayer = null;
      mapInstanceRef.current.eachLayer((layer) => {
        if (layer instanceof L.GeoJSON && layer.options.offshoreWindLayer) {
          offshoreLayer = layer;
        }
      });
      
      if (offshoreLayer) {
        offshoreLayer.eachLayer((featureLayer) => {
          if (featureLayer.feature) {
            const newStyle = getZoneStyle(featureLayer.feature, 'offshore_wind', offshoreWindThresholds, zoomLevel);
            featureLayer.setStyle(newStyle);
          }
        });
        offshoreLayer.options.thresholds = offshoreWindThresholds;
      }
    }
  }, [onshoreWindThresholds, offshoreWindThresholds]); // Only when thresholds change

  return (
    <div className={className}>
      <div 
        ref={mapRef}
        className="w-full h-full min-h-96"
      />
      
      {/* Loading and error overlays are handled by parent component */}
    </div>
  );
});

export default WindMap;
