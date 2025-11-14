/**
 * Common Map Utilities for VerveStacks Dashboard
 * 
 * This utility provides consistent map styling and configuration across all maps
 * in the dashboard, ensuring a clean, professional appearance that highlights
 * renewable energy data without visual clutter.
 */

import L from 'leaflet';

/**
 * Map Style Presets
 * Different styles optimized for different types of data visualization
 */
export const MAP_STYLES = {
  // Clean minimal style for renewable energy zones
  CLEAN_MINIMAL: {
    name: 'Clean Minimal',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution: '© OpenStreetMap contributors © CARTO',
    description: 'Clean style with clear country boundaries, perfect for renewable energy zones'
  },
  
  // Light style with subtle features
  LIGHT_SUBTLE: {
    name: 'Light Subtle',
    url: 'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
    attribution: '© OpenStreetMap contributors © CARTO',
    description: 'Light background with minimal labels, ideal for data visualization'
  },
  
  // Dark theme for contrast
  DARK_THEME: {
    name: 'Dark Theme',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '© OpenStreetMap contributors © CARTO',
    description: 'Dark theme for high contrast with bright renewable energy markers'
  },
  
  // High contrast for accessibility
  HIGH_CONTRAST: {
    name: 'High Contrast',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '© OpenStreetMap contributors © CARTO',
    description: 'High contrast style for better accessibility and marker visibility'
  },
  
  // Terrain style for geographical context
  TERRAIN: {
    name: 'Terrain',
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    attribution: '© OpenStreetMap contributors © CARTO',
    description: 'Terrain style showing geographical features relevant to renewable energy'
  }
};

/**
 * Default map configuration optimized for renewable energy visualization
 */
export const DEFAULT_MAP_CONFIG = {
  // Map options
  zoomControl: true,
  attributionControl: true,
  scrollWheelZoom: true,
  doubleClickZoom: true,
  dragging: true,
  boxZoom: true,
  keyboard: true,
  touchZoom: true,
  
  // Zoom limits
  minZoom: 2,
  maxZoom: 18,
  
  // Default style
  defaultStyle: MAP_STYLES.CLEAN_MINIMAL,
  
  // Marker defaults
  markerDefaults: {
    opacity: 0.7,
    fillOpacity: 0.6,
    weight: 1,
    color: 'white'
  }
};

/**
 * Create a standardized tile layer with consistent styling
 * @param {string} style - Style preset name from MAP_STYLES
 * @param {Object} options - Additional Leaflet tile layer options
 * @returns {L.TileLayer} Configured tile layer
 */
export const createTileLayer = (style = 'CLEAN_MINIMAL', options = {}) => {
  const styleConfig = MAP_STYLES[style] || MAP_STYLES.CLEAN_MINIMAL;
  
  const defaultOptions = {
    attribution: styleConfig.attribution,
    maxZoom: 18,
    detectRetina: true,
    ...options
  };
  
  return L.tileLayer(styleConfig.url, defaultOptions);
};

/**
 * Create a map with standardized configuration
 * @param {HTMLElement} container - Map container element
 * @param {Object} options - Map initialization options
 * @returns {L.Map} Configured map instance
 */
export const createMap = (container, options = {}) => {
  const config = {
    ...DEFAULT_MAP_CONFIG,
    ...options
  };
  
  const map = L.map(container, {
    zoomControl: config.zoomControl,
    attributionControl: config.attributionControl,
    scrollWheelZoom: config.scrollWheelZoom,
    doubleClickZoom: config.doubleClickZoom,
    dragging: config.dragging,
    boxZoom: config.boxZoom,
    keyboard: config.keyboard,
    touchZoom: config.touchZoom,
    minZoom: config.minZoom,
    maxZoom: config.maxZoom
  });
  
  // Add default tile layer
  const tileLayer = createTileLayer(config.defaultStyle);
  tileLayer.addTo(map);
  
  return map;
};

/**
 * Create a standardized circle marker
 * @param {Array} position - [lat, lng] coordinates
 * @param {Object} options - Marker options
 * @returns {L.CircleMarker} Configured circle marker
 */
export const createCircleMarker = (position, options = {}) => {
  const defaultOptions = {
    ...DEFAULT_MAP_CONFIG.markerDefaults,
    ...options
  };
  
  return L.circleMarker(position, defaultOptions);
};

/**
 * Create a custom control for any map
 * @param {Object} options - Control configuration
 * @returns {L.Control} Custom control
 */
export const createCustomControl = (options = {}) => {
  const CustomControl = L.Control.extend({
    onAdd: function(map) {
      const div = L.DomUtil.create('div', 'leaflet-custom-control');
      div.style.cssText = `
        background: white;
        border: 1px solid #ccc;
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        font-family: Arial, sans-serif;
        font-size: 12px;
        ${options.customStyles || ''}
      `;
      
      if (options.content) {
        div.innerHTML = options.content;
      }
      
      return div;
    }
  });
  
  return new CustomControl({ 
    position: options.position || 'bottomright',
    ...options
  });
};

/**
 * Calculate optimal map bounds for a set of coordinates
 * @param {Array} coordinates - Array of [lat, lng] coordinates
 * @param {number} padding - Padding factor (0-1)
 * @returns {L.LatLngBounds} Calculated bounds
 */
export const calculateMapBounds = (coordinates, padding = 0.1) => {
  if (!coordinates || coordinates.length === 0) {
    return L.latLngBounds([[0, 0], [0, 0]]);
  }
  
  const lats = coordinates.map(coord => coord[0]);
  const lngs = coordinates.map(coord => coord[1]);
  
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  
  const latPadding = (maxLat - minLat) * padding;
  const lngPadding = (maxLng - minLng) * padding;
  
  return L.latLngBounds(
    [minLat - latPadding, minLng - lngPadding],
    [maxLat + latPadding, maxLng + lngPadding]
  );
};

const mapUtils = {
  MAP_STYLES,
  DEFAULT_MAP_CONFIG,
  createTileLayer,
  createMap,
  createCircleMarker,
  createCustomControl,
  calculateMapBounds
};

export default mapUtils;
