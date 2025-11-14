import { capacityAPI } from '../services/api';

// Simple session cache for fuel colors (no expiry)
let colorCache = null;

/**
 * Initialize fuel colors once per session by fetching from backend API.
 * If already initialized, this is a no-op.
 */
export const initializeFuelColors = async () => {
  if (colorCache) return;
  try {
    const response = await capacityAPI.getFuelColors();
    if (response && typeof response === 'object') {
      colorCache = response;
    } else {
      throw new Error('Invalid response structure');
    }
  } catch (error) {
    console.error('❌ Failed to fetch fuel colors:', error);
    // Leave colorCache as null; callers will fallback to default color
  }
};

/**
 * Get fuel color synchronously (uses cached colors)
 * @param {string} fuelType - The fuel type (e.g., 'nuclear', 'solar')
 * @returns {string} - Hex color code
 */
export const getFuelColor = (fuelType) => {
  const key = fuelType ? String(fuelType).toLowerCase() : '';
  if (colorCache && key && colorCache[key]) {
    return colorCache[key];
  }
  return '#7F8C8D'; // Default gray color when not available
};

/**
 * Get all fuel colors synchronously (uses cached colors)
 * @returns {Object} - Object with fuel types as keys and colors as values
 */
export const getAllFuelColors = () => {
  if (!colorCache) {
    throw new Error('Fuel colors not initialized. Call initializeFuelColors() first.');
  }
  return colorCache;
};

/**
 * Clear the color cache (useful for testing or forcing refresh)
 */
export const clearColorCache = () => {
  colorCache = null;
};
