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

  // Render solar zone shapes - thresholds passed as parameter, not in dependencies
  const renderSolarZoneShapes = useCallback((map, gridData, thresholds) => {
    if (!map || !gridData || gridData.length === 0) {
      return;
    }
    
    // Check for existing layer - if exists, remove it before creating new one
    let existingSolarLayer = null;
    map.eachLayer((layer) => {
      if (layer instanceof L.GeoJSON && layer.options.solarLayer) {
        existingSolarLayer = layer;
      }
    });

    if (existingSolarLayer) {
      map.removeLayer(existingSolarLayer);
    }

    // Get current map bounds and zoom level for performance optimization
    let mapBounds, zoomLevel;
    try {
      mapBounds = map.getBounds();
      zoomLevel = map.getZoom();
    } catch (error) {
      console.warn('Could not get map bounds/zoom:', error);
      // Use defaults if bounds unavailable
      mapBounds = null;
      zoomLevel = 2;
    }

    // Optimize GeoJSON data based on current view
    const geoJsonData = optimizeGeoJSONData(gridData, mapBounds, zoomLevel);

    // Only render if we have features to display
    if (geoJsonData.features.length === 0) {
      return;
    }

    // Create GeoJSON layer with styling and interactions
    const geoJsonLayer = createGeoJSONLayer(
      geoJsonData,
      (feature) => getZoneStyle(feature, 'solar', thresholds, zoomLevel),
      (feature, layer) => {
        const zone = feature.properties;
        
        // Store original feature reference for color updates
        layer.feature = feature;
        
        // Add tooltip on hover
        layer.bindTooltip(createZonePopup(zone, 'solar'), {
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
          const originalStyle = getZoneStyle(feature, 'solar', thresholds, zoomLevel);
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

    // Mark this layer as solar layer for future identification
    geoJsonLayer.options.solarLayer = true;
    geoJsonLayer.options.lastZoom = map.getZoom();
    geoJsonLayer.options.thresholds = thresholds; // Store thresholds for reference

    // Add layer to map
    geoJsonLayer.addTo(map);
  }, [createGeoJSONLayer]); // Removed onZoneSelect and solarThresholds from dependencies

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
        console.error('Error creating solar map:', error);
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
          console.warn('Error removing solar map:', err);
        }
        mapInstanceRef.current = null;
        setMapReady(false);
      }
    };
  }, []); // Empty deps - runs once on mount

  // Render layers only when BOTH data AND thresholds are ready
  useEffect(() => {
    // Wait for map to be ready
    if (!mapReady || !mapInstanceRef.current) {
      return;
    }
    if (!solarData?.grid_data?.length) {
      return;
    }
    if (!solarThresholds) {
      return; // Wait for thresholds
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
      
      // Both ready - render layer first, then fit bounds
      const gridData = solarData.grid_data;
      
      // Render layer with both data and thresholds (render first)
      renderSolarZoneShapes(map, gridData, solarThresholds);
      
      // Fit bounds AFTER rendering (so layers are visible)
      if (!map.options.boundsSet) {
        // Calculate bounds from ALL data for initial view
        let coordinates = [];
        gridData.forEach(zone => {
          if (zone.lat && zone.lng) {
            coordinates.push([zone.lat, zone.lng]);
          } else if (zone.geometry && zone.geometry.type === 'Polygon') {
            const coords = zone.geometry.coordinates[0];
            coords.forEach(coord => {
              coordinates.push([coord[1], coord[0]]); // lat, lng
            });
          }
        });
        
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
  }, [solarData, solarThresholds, renderSolarZoneShapes, mapReady]);

  // Update layer colors when thresholds change (don't recreate layer)
  useEffect(() => {
    if (!mapInstanceRef.current || !solarThresholds) return;
    
    // Find existing solar layer
    let existingLayer = null;
    mapInstanceRef.current.eachLayer((layer) => {
      if (layer instanceof L.GeoJSON && layer.options.solarLayer) {
        existingLayer = layer;
      }
    });
    
    if (existingLayer) {
      // Update colors of each feature individually
      const zoomLevel = mapInstanceRef.current.getZoom();
      existingLayer.eachLayer((featureLayer) => {
        if (featureLayer.feature) {
          const newStyle = getZoneStyle(featureLayer.feature, 'solar', solarThresholds, zoomLevel);
          featureLayer.setStyle(newStyle);
        }
      });
      
      // Update stored thresholds
      existingLayer.options.thresholds = solarThresholds;
    }
  }, [solarThresholds]); // Only when thresholds change (not data)

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

export default SolarMap;
