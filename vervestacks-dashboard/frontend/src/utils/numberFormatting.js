/**
 * Smart Number Formatting Utility
 * 
 * Formats numbers for chart labels and tooltips based on magnitude:
 * - Larger numbers get less precision (rounded)
 * - Smaller numbers get more precision (meaningful decimals)
 * - Never shows unnecessary .0
 * 
 * This function is a JavaScript port of the Python smart_format_number function
 * from data_utils.py, ensuring consistent number formatting across the dashboard.
 * 
 * @param {number} value - Number to format
 * @returns {string} Clean formatted string for labels
 * 
 * @example
 * smartFormatNumber(18391)  // "18391"
 * smartFormatNumber(18.4)   // "18.4"
 * smartFormatNumber(18.0)   // "18"
 * smartFormatNumber(0.34)   // "0.34"
 * smartFormatNumber(0.0)    // "0"
 * 
 * @example
 * // Usage in Highcharts tooltips
 * tooltip: {
 *     formatter: function() {
 *         const formattedValue = smartFormatNumber(this.y);
 *         return `${this.series.name}: ${formattedValue} GW`;
 *     }
 * }
 * 
 * @example
 * // Usage in map popups
 * const createPopup = (data) => {
 *     const formattedCapacity = smartFormatNumber(data.capacity);
 *     return `<p>Capacity: ${formattedCapacity} MW</p>`;
 * };
 */
export function smartFormatNumber(value) {
    // Handle null, undefined, or non-numeric values
    if (value === null || value === undefined || isNaN(value)) {
        return "0";
    }
    
    // Convert to number if it's a string
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    
    // Handle invalid numbers
    if (isNaN(numValue)) {
        return "0";
    }
    
    // Handle zero
    if (numValue === 0) {
        return "0";
    }
    
    const absVal = Math.abs(numValue);
    
    if (absVal >= 1000) {
        // Very large: no decimals
        return Math.round(numValue).toString();
    } else if (absVal >= 50) {
        // Large: no decimals, no .0
        return Math.round(numValue).toString();
    } else if (absVal >= 10) {
        // Medium: 1 decimal if meaningful
        const rounded = Math.round(numValue * 10) / 10;
        return rounded === Math.floor(rounded) ? 
            Math.floor(rounded).toString() : 
            rounded.toFixed(1);
    } else if (absVal >= 1) {
        // Small: up to 2 decimals if meaningful
        const rounded = Math.round(numValue * 100) / 100;
        if (rounded === Math.floor(rounded)) {
            return Math.floor(rounded).toString();
        } else if (Math.round(rounded * 10) / 10 === rounded) {
            return rounded.toFixed(1);
        } else {
            return rounded.toFixed(2);
        }
    } else {
        // Very small: up to 3 decimals if meaningful
        const rounded = Math.round(numValue * 1000) / 1000;
        if (rounded === 0) return "0";
        // Remove trailing zeros
        return rounded.toFixed(3).replace(/\.?0+$/, '');
    }
}

/**
 * Format number with unit for display in tooltips and labels
 * 
 * @param {number} value - Number to format
 * @param {string} unit - Unit to append (e.g., 'GW', 'TWh', 'MW', '%')
 * @returns {string} Formatted string with unit
 * 
 * @example
 * formatNumberWithUnit(18.4, 'GW')  // "18.4 GW"
 * formatNumberWithUnit(18391, 'MW') // "18391 MW"
 * formatNumberWithUnit(0.34, '%')   // "0.34%"
 */
export function formatNumberWithUnit(value, unit) {
    const formattedNumber = smartFormatNumber(value);
    return `${formattedNumber} ${unit}`;
}

/**
 * Format percentage values for display
 * 
 * @param {number} value - Percentage value (0-100)
 * @returns {string} Formatted percentage string
 * 
 * @example
 * formatPercentage(18.4)  // "18.4%"
 * formatPercentage(0.34)  // "0.34%"
 * formatPercentage(100)   // "100%"
 */
export function formatPercentage(value) {
    return formatNumberWithUnit(value, '%');
}

/**
 * Format currency values for display
 * 
 * @param {number} value - Currency value
 * @param {string} symbol - Currency symbol (default: '$')
 * @returns {string} Formatted currency string
 * 
 * @example
 * formatCurrency(18.4)     // "$18.4"
 * formatCurrency(18391)    // "$18391"
 * formatCurrency(0.34, '€') // "€0.34"
 */
export function formatCurrency(value, symbol = '$') {
    const formattedNumber = smartFormatNumber(value);
    return `${symbol}${formattedNumber}`;
}

