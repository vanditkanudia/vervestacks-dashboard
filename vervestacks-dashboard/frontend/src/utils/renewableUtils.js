/**
 * Renewable Energy Utility Functions
 * 
 * This utility provides calculations and formatting functions specific to
 * renewable energy data visualization and analysis.
 */

import { smartFormatNumber } from './numberFormatting';

/**
 * Calculate percentile thresholds for renewable energy capacity factors
 * @param {Array} capacityFactors - Array of capacity factor values
 * @param {string} type - Type of renewable energy ('solar', 'onshore_wind', 'offshore_wind')
 * @returns {Object} Threshold object with percentile values
 */
export const calculatePercentileThresholds = (capacityFactors, type = 'solar') => {
  if (!capacityFactors || capacityFactors.length === 0) {
    return {
      poor: { threshold: 0, color: '#440154' },
      fair: { threshold: 0, color: '#31688e' },
      good: { threshold: 0, color: '#35b779' },
      high: { threshold: 0, color: '#fde725' },
      excellent: { threshold: 0, color: '#fde725' }
    };
  }

  // Sort capacity factors in descending order (original logic)
  const sortedCFs = [...capacityFactors].sort((a, b) => b - a);
  const total = sortedCFs.length;
  
  // Calculate percentile thresholds (top 20%, 60th, 40th, 20th percentiles) - original logic
  const p80 = sortedCFs[Math.floor(total * 0.2)]; // Top 20%
  const p60 = sortedCFs[Math.floor(total * 0.4)]; // 60th percentile
  const p40 = sortedCFs[Math.floor(total * 0.6)]; // 40th percentile
  const p20 = sortedCFs[Math.floor(total * 0.8)]; // 20th percentile

  const thresholds = {
    excellent: { threshold: p80, color: '#FDE725' }, // Top 20%
    high: { threshold: p60, color: '#6DCD59' },     // 60th percentile
    good: { threshold: p40, color: '#35B779' },     // 40th percentile
    fair: { threshold: p20, color: '#31688E' },      // 20th percentile
    poor: { threshold: 0, color: '#440154' }         // Bottom
  };

  return thresholds;
};

/**
 * Format number with appropriate units
 * @param {number} num - Number to format
 * @returns {string} Formatted number string
 */
export const formatNumber = (num) => {
  // Handle null, undefined, or non-numeric values
  if (num == null || isNaN(num)) {
    return 'N/A';
  }
  
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`;
  } else if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`;
  }
  return num.toFixed(1);
};

/**
 * Get capacity factor label based on thresholds
 * @param {number} cf - Capacity factor value
 * @param {Object} thresholds - Threshold object
 * @returns {string} Label ('Poor', 'Fair', 'Good', 'High', 'Excellent')
 */
export const getCapacityFactorLabel = (cf, thresholds) => {
  if (!thresholds) return 'Unknown';
  
  if (cf >= thresholds.excellent.threshold) return 'Excellent';
  if (cf >= thresholds.high.threshold) return 'High';
  if (cf >= thresholds.good.threshold) return 'Good';
  if (cf >= thresholds.fair.threshold) return 'Fair';
  return 'Poor';
};

/**
 * Optimize GeoJSON data based on current map view for performance
 * @param {Array} gridData - Array of grid data objects
 * @param {Object} mapBounds - Leaflet map bounds
 * @param {number} zoomLevel - Current zoom level
 * @returns {Object} Optimized GeoJSON data
 */
export const optimizeGeoJSONData = (gridData, mapBounds, zoomLevel) => {
  if (!gridData || gridData.length === 0) {
    return { type: 'FeatureCollection', features: [] };
  }


  // Performance optimization - temporarily disabled to show all data
  // const maxFeatures = zoomLevel <= 4 ? 5000 : zoomLevel <= 6 ? 10000 : zoomLevel <= 8 ? 20000 : 50000;
  
  let polygonCount = 0;
  let pointCount = 0;
  let errorCount = 0;
  
  const features = gridData.map(zone => {
    // Use geometry if available (already parsed GeoJSON object)
    if (zone.geometry) {
      try {
        polygonCount++;
        return {
          type: 'Feature',
          properties: zone,
          geometry: zone.geometry
        };
      } catch (error) {
        console.warn('Failed to use geometry:', error);
        errorCount++;
        return null;
      }
    }
    
    // Fallback to point geometry if no geometry
    if (zone.lat && zone.lng) {
      pointCount++;
      return {
        type: 'Feature',
        properties: zone,
        geometry: {
          type: 'Point',
          coordinates: [zone.lng, zone.lat]
        }
      };
    }
    
    return null;
  }).filter(feature => feature !== null);

  

  return {
    type: 'FeatureCollection',
    features
  };
};

/**
 * Create zone popup content
 * @param {Object} zone - Zone data object
 * @param {string} zoneType - Type of zone ('solar', 'onshore_wind', 'offshore_wind')
 * @returns {string} HTML popup content
 */
export const createZonePopup = (zone, zoneType) => {
  const typeLabels = {
    solar: 'Solar',
    onshore_wind: 'Onshore Wind',
    offshore_wind: 'Offshore Wind'
  };

  return `
    <div class="p-2">
      <h4 class="font-semibold text-sm mb-2">${typeLabels[zoneType]} Zone</h4>
      <div class="space-y-1 text-xs">
        <div><strong>Capacity Factor:</strong> ${smartFormatNumber(zone['Capacity Factor'] * 100)}%</div>
        <div><strong>Capacity:</strong> ${smartFormatNumber(zone['Installed Capacity Potential (MW)'])} MW</div>
        <div><strong>LCOE:</strong> $${smartFormatNumber(zone['LCOE (USD/MWh)'] || 0)}/MWh</div>
        <div><strong>Area:</strong> ${smartFormatNumber(zone['Suitable Area (km²)'])} km²</div>
      </div>
    </div>
  `;
};

/**
 * Get hover style for map features
 * @param {number} zoomLevel - Current zoom level
 * @returns {Object} Leaflet style object
 */
export const getHoverStyle = (zoomLevel) => ({
  weight: zoomLevel <= 4 ? 1 : zoomLevel <= 6 ? 1.5 : zoomLevel <= 8 ? 2 : 2.5,
  opacity: 1,
  fillOpacity: 0.8,
  color: 'white',
  dashArray: '5'
});

/**
 * Get zone style based on capacity factor and thresholds
 * @param {Object} feature - GeoJSON feature
 * @param {string} zoneType - Type of zone
 * @param {Object} thresholds - Threshold object
 * @param {number} zoomLevel - Current zoom level
 * @returns {Object} Leaflet style object
 */
export const getZoneStyle = (feature, zoneType, thresholds, zoomLevel) => {
  const zone = feature.properties;
  const cf = zone['Capacity Factor'];
  
  let color = '#440154'; // Default poor color
  
  if (thresholds) {
    if (cf >= thresholds.excellent.threshold) color = thresholds.excellent.color;
    else if (cf >= thresholds.high.threshold) color = thresholds.high.color;
    else if (cf >= thresholds.good.threshold) color = thresholds.good.color;
    else if (cf >= thresholds.fair.threshold) color = thresholds.fair.color;
    else color = thresholds.poor.color;
  }

  // Return polygon style for GeoJSON layers
  return {
    fillColor: color,
    color: 'white',
    weight: zoomLevel <= 4 ? 0.5 : zoomLevel <= 6 ? 0.8 : zoomLevel <= 8 ? 1 : 1.2,
    opacity: 0.8,
    fillOpacity: 0.6
  };
};

const renewableUtils = {
  calculatePercentileThresholds,
  formatNumber,
  getCapacityFactorLabel,
  optimizeGeoJSONData,
  createZonePopup,
  getHoverStyle,
  getZoneStyle
};

export default renewableUtils;
