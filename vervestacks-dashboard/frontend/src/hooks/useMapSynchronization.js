/**
 * Custom Hook for Map Synchronization
 * 
 * This hook handles synchronization between two Leaflet maps,
 * ensuring they stay in sync for pan and zoom operations.
 */

import { useCallback, useRef, useEffect } from 'react';

export const useMapSynchronization = () => {
  const syncCleanupRef = useRef(null);

  const synchronizeMaps = useCallback((map1, map2) => {
    // Clean up any existing sync
    if (syncCleanupRef.current) {
      syncCleanupRef.current();
      syncCleanupRef.current = null;
    }

    if (!map1 || !map2) {
      console.warn('Cannot synchronize maps: one or both maps are null');
      return;
    }

    // Validate maps are properly initialized
    if (!map1._container || !map2._container || 
        !map1._loaded || !map2._loaded ||
        !map1._panes || !map2._panes) {
      console.warn('Maps not properly initialized for synchronization');
      return;
    }
    
    // Prevent infinite loops and zoom conflicts
    let isSyncing = false;
    let isZooming = false;
    
    // Track zoom states to prevent sync during zoom operations
    const handleZoomStart = () => { isZooming = true; };
    const handleZoomEnd = () => { 
      // Allow sync after zoom completes with a small delay
      setTimeout(() => { isZooming = false; }, 100);
    };
    
    // Add zoom event listeners to both maps
    map1.on('zoomstart', handleZoomStart);
    map1.on('zoomend', handleZoomEnd);
    map2.on('zoomstart', handleZoomStart);
    map2.on('zoomend', handleZoomEnd);
    
    // Create named functions for easier cleanup
    const syncMap1ToMap2 = () => {
      if (!isSyncing && map2 && map2._container && map2._loaded && map2._panes) {
        isSyncing = true;
        try {
          // Additional validation before sync - allow sync even during zoom if maps are stable
          if (map1._loaded && map1._panes && map1.getCenter) {
            map2.setView(map1.getCenter(), map1.getZoom(), { animate: false });
          }
        } catch (error) {
          console.warn('Error syncing map1 to map2:', error);
        }
        setTimeout(() => { isSyncing = false; }, 150);
      }
    };
    
    const syncMap2ToMap1 = () => {
      if (!isSyncing && map1 && map1._container && map1._loaded && map1._panes) {
        isSyncing = true;
        try {
          // Additional validation before sync - allow sync even during zoom if maps are stable
          if (map2._loaded && map2._panes && map2.getCenter) {
            map1.setView(map2.getCenter(), map2.getZoom(), { animate: false });
          }
        } catch (error) {
          console.warn('Error syncing map2 to map1:', error);
        }
        setTimeout(() => { isSyncing = false; }, 150);
      }
    };
    
    // Add new listeners with debouncing for both move and zoom
    map1.on('moveend zoomend', syncMap1ToMap2);
    map2.on('moveend zoomend', syncMap2ToMap1);
    
    // Store cleanup function
    syncCleanupRef.current = () => {
      map1.off('moveend zoomend', syncMap1ToMap2);
      map2.off('moveend zoomend', syncMap2ToMap1);
      map1.off('zoomstart', handleZoomStart);
      map1.off('zoomend', handleZoomEnd);
      map2.off('zoomstart', handleZoomStart);
      map2.off('zoomend', handleZoomEnd);
    };

    return syncCleanupRef.current;
  }, []);

  const cleanup = useCallback(() => {
    if (syncCleanupRef.current) {
      syncCleanupRef.current();
      syncCleanupRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    synchronizeMaps,
    cleanup
  };
};

export default useMapSynchronization;
