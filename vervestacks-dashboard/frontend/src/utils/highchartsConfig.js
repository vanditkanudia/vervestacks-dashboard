/**
 * Centralized Highcharts Configuration Utility
 * 
 * This utility provides consistent Highcharts configuration across all charts
 * in the VerveStacks dashboard, ensuring uniform styling, behavior, and maintainability.
 */

import Highcharts from 'highcharts';
import HighchartsSeriesLabel from 'highcharts/modules/series-label';
import { smartFormatNumber } from './numberFormatting';

// Initialize Highcharts modules once for all charts
if (typeof Highcharts !== 'undefined') {
  HighchartsSeriesLabel(Highcharts);
}

/**
 * Common chart styling configuration
 */
export const CHART_STYLES = {
  fontFamily: "Inter, system-ui, sans-serif",
  titleFontSize: "18px",
  titleFontWeight: "600",
  titleColor: "#1f2937",
  subtitleFontSize: "14px",
  subtitleColor: "#6b7280",
  axisTitleFontSize: "11px",
  axisTitleFontWeight: "500",
  axisTitleColor: "#374151",
  axisLabelFontSize: "12px",
  axisLabelColor: "#6b7280",
  legendFontSize: "12px",
  legendColor: "#374151",
  legendHoverColor: "#1f2937",
  gridLineColor: "#e5e7eb",
  gridLineWidth: 1,
  tooltipFontSize: "12px",
  backgroundColor: "transparent",
  oceanBackground: "#D2DFFF",
  countryColor: "#C5D0EF",
  borderColor: "#D2DFFF",
  hoverColor: "#8B5CF6",
  selectedColor: "#A855F7"
};

/**
 * Common chart dimensions
 */
export const CHART_DIMENSIONS = {
  height: 400,
  legendPadding: 20,
  tooltipPadding: 8
};

/**
 * Common animation settings
 */
export const ANIMATION_CONFIG = {
  duration: 1000,
  easing: 'easeOutQuart'
};

/**
 * Create base chart configuration with common styling and structure
 * Provides standardized title, subtitle, font, and background styling
 * 
 * @param {Object} options - Chart-specific configuration options
 * @param {string} [options.type='line'] - Chart type: 'line', 'column', 'area', etc.
 * @param {string} [options.title=''] - Chart title text
 * @param {string} [options.subtitle=''] - Chart subtitle text
 * @param {number} [options.height=400] - Chart height in pixels
 * @param {string} [options.backgroundColor='transparent'] - Chart background color
 * @param {Object} [options...customOptions] - Additional Highcharts options to merge
 * 
 * @returns {Object} Base Highcharts chart configuration object
 * 
 * @example
 * createBaseChartConfig({ type: 'line', title: 'Sales Data', subtitle: 'Monthly report' });
 */
export const createBaseChartConfig = (options = {}) => {
  const {
    type = 'line',
    title = '',
    subtitle = '',
    height = CHART_DIMENSIONS.height,
    backgroundColor = CHART_STYLES.backgroundColor,
    ...customOptions
  } = options;

  return {
    chart: {
      type,
      height,
      backgroundColor,
      borderWidth: 0,
      style: {
        fontFamily: CHART_STYLES.fontFamily,
      },
    },
    title: {
      text: title,
      style: {
        fontSize: CHART_STYLES.titleFontSize,
        fontWeight: CHART_STYLES.titleFontWeight,
        color: CHART_STYLES.titleColor,
      },
    },
    subtitle: {
      text: subtitle,
      style: {
        fontSize: CHART_STYLES.subtitleFontSize,
        color: CHART_STYLES.subtitleColor,
      },
    },
    credits: {
      enabled: false,
    },
    ...customOptions
  };
};

/**
 * Create common x-axis configuration with standardized styling
 * Configures title, labels, grid lines, and categories for horizontal axis
 * 
 * @param {Object} options - X-axis specific configuration options
 * @param {string} [options.title=''] - Axis title text
 * @param {Array<string>} [options.categories=null] - Array of category labels
 * @param {string} [options.type='linear'] - Axis type: 'linear', 'datetime', 'category', etc.
 * @param {Object} [options...customOptions] - Additional Highcharts x-axis options to merge
 * 
 * @returns {Object} Highcharts x-axis configuration object
 * 
 * @example
 * createXAxisConfig({ title: 'Year', categories: ['2020', '2021', '2022'] });
 */
export const createXAxisConfig = (options = {}) => {
  const {
    title = '',
    categories = null,
    type = 'linear',
    ...customOptions
  } = options;

  return {
    type,
    title: {
      text: title,
      style: {
        fontSize: CHART_STYLES.axisTitleFontSize,
        fontWeight: CHART_STYLES.axisTitleFontWeight,
        color: CHART_STYLES.axisTitleColor,
      },
    },
    labels: {
      style: {
        fontSize: CHART_STYLES.axisLabelFontSize,
        color: CHART_STYLES.axisLabelColor,
      },
    },
    gridLineWidth: CHART_STYLES.gridLineWidth,
    gridLineColor: CHART_STYLES.gridLineColor,
    ...(categories && { categories }),
    ...customOptions
  };
};

/**
 * Create common y-axis configuration with standardized styling
 * Configures title, labels, grid lines, and value formatting for vertical axis
 * 
 * @param {Object} options - Y-axis specific configuration options
 * @param {string} [options.title=''] - Axis title text (e.g., 'TWh', 'GW', 'USD')
 * @param {Function} [options.formatter=null] - Custom formatter function for axis labels
 * @param {Object} [options...customOptions] - Additional Highcharts y-axis options to merge
 * 
 * @returns {Object} Highcharts y-axis configuration object
 * 
 * @example
 * createYAxisConfig({ title: 'Temperature (°C)' });
 * 
 * @example
 * createYAxisConfig({ 
 *   title: 'Value', 
 *   formatter: function() { return smartFormatNumber(this.value); } 
 * });
 */
export const createYAxisConfig = (options = {}) => {
  const {
    title = '',
    formatter = null,
    ...customOptions
  } = options;

  return {
    title: {
      text: title,
      style: {
        fontSize: CHART_STYLES.axisTitleFontSize,
        fontWeight: CHART_STYLES.axisTitleFontWeight,
        color: CHART_STYLES.axisTitleColor,
      },
    },
    labels: {
      style: {
        fontSize: CHART_STYLES.axisLabelFontSize,
        color: CHART_STYLES.axisLabelColor,
      },
      ...(formatter && { formatter }),
    },
    gridLineWidth: CHART_STYLES.gridLineWidth,
    gridLineColor: CHART_STYLES.gridLineColor,
    ...customOptions
  };
};

/**
 * Create common legend configuration with standardized styling
 * Supports floating or fixed legends with customizable positioning and layout
 * 
 * @param {Object} options - Legend-specific configuration options
 * @param {string} [options.align='right'] - Horizontal alignment: 'left', 'center', 'right'
 * @param {string} [options.verticalAlign='top'] - Vertical alignment: 'top', 'middle', 'bottom'
 * @param {string} [options.layout='vertical'] - Legend layout: 'horizontal' or 'vertical'
 * @param {boolean} [options.floating=true] - Whether legend floats over the chart
 * @param {number} [options.x=-20] - Horizontal offset from alignment position
 * @param {number} [options.y=40] - Vertical offset from alignment position
 * @param {string} [options.backgroundColor='rgba(255, 255, 255, 0.9)'] - Legend background color
 * @param {number} [options.borderRadius=3] - Legend border radius in pixels
 * @param {Object} [options...customOptions] - Additional Highcharts legend options to merge
 * 
 * @returns {Object} Highcharts legend configuration object
 * 
 * @example
 * // Floating legend (default)
 * createLegendConfig({ align: 'right', verticalAlign: 'top' });
 * 
 * @example
 * // Fixed bottom legend
 * createLegendConfig({ 
 *   verticalAlign: 'bottom', 
 *   layout: 'horizontal', 
 *   floating: false 
 * });
 */
export const createLegendConfig = (options = {}) => {
  const {
    align = 'right',
    verticalAlign = 'top',
    layout = 'vertical',
    floating = true,
    x = -20,
    y = 40,
    backgroundColor = 'rgba(255, 255, 255, 0.9)',
    borderRadius = 3,
    ...customOptions
  } = options;

  return {
    enabled: true,
    align,
    verticalAlign,
    layout,
    floating,
    x,
    y,
    backgroundColor,
    borderWidth: 0,
    borderRadius,
    shadow: false,
    itemStyle: {
      fontSize: CHART_STYLES.legendFontSize,
      color: CHART_STYLES.legendColor,
    },
    itemHoverStyle: {
      color: CHART_STYLES.legendHoverColor,
    },
    ...customOptions
  };
};

/**
 * Create common tooltip configuration with standardized styling
 * Configures tooltip appearance, background, and content formatting
 * 
 * @param {Object} options - Tooltip-specific configuration options
 * @param {string} [options.backgroundColor='rgba(255, 255, 255, 0.95)'] - Tooltip background color
 * @param {number} [options.borderWidth=0] - Tooltip border width in pixels
 * @param {number} [options.borderRadius=8] - Tooltip border radius in pixels
 * @param {boolean} [options.shadow=true] - Whether to show tooltip shadow
 * @param {boolean} [options.shared=false] - Shared tooltip for multiple series
 * @param {Function} [options.formatter=null] - Custom formatter function for tooltip content
 * @param {Object} [options...customOptions] - Additional Highcharts tooltip options to merge
 * 
 * @returns {Object} Highcharts tooltip configuration object
 * 
 * @example
 * createTooltipConfig({ backgroundColor: 'rgba(0,0,0,0.8)', borderRadius: 4 });
 * 
 * @example
 * createTooltipConfig({ 
 *   shared: true, 
 *   formatter: function() { return `<b>${this.x}</b><br/>Value: ${this.y}`; } 
 * });
 */
export const createTooltipConfig = (options = {}) => {
  const {
    backgroundColor = "rgba(255, 255, 255, 0.95)",
    borderWidth = 0,
    borderRadius = 8,
    shadow = true,
    shared = false,
    formatter = null,
    ...customOptions
  } = options;

  return {
    backgroundColor,
    borderWidth,
    borderRadius,
    shadow,
    shared,
    style: {
      fontSize: CHART_STYLES.tooltipFontSize,
    },
    ...(formatter && { formatter }),
    ...customOptions
  };
};

/**
 * Create plot options configuration for different chart types
 * Configures markers, line width, fill opacity, stacking, and data labels
 * 
 * @param {Object} options - Plot options configuration
 * @param {string} [options.chartType='line'] - Chart type: 'line', 'area', 'column'
 * @param {Object} [options.marker={ enabled: true, radius: 4 }] - Marker configuration for line charts
 * @param {number} [options.lineWidth=3] - Line width in pixels
 * @param {number} [options.fillOpacity=0.6] - Fill opacity for area charts (0-1)
 * @param {string} [options.stacking=null] - Stacking type: 'normal', 'percent', or null
 * @param {Object} [options.dataLabels=null] - Data labels configuration
 * @param {Object} [options...customOptions] - Additional plot options to merge
 * @returns {Object} Plot options configuration object
 */
export const createPlotOptionsConfig = (options = {}) => {
  const {
    chartType = 'line',
    marker = { enabled: true, radius: 4 },
    lineWidth = 3,
    fillOpacity = 0.6,
    stacking = null,
    dataLabels = null,
    ...customOptions
  } = options;

  const plotConfig = {
    series: {
      animation: {
        duration: ANIMATION_CONFIG.duration,
      },
    },
  };

  // Add chart-type specific options
  if (chartType === 'line') {
    const lineConfig = {
      marker: {
        enabled: marker.enabled,
        radius: marker.radius,
        lineWidth: 2,
        lineColor: "#ffffff",
      },
      lineWidth,
    };

    // Add custom data labels if provided
    if (dataLabels) {
      lineConfig.dataLabels = dataLabels;
    }

    plotConfig.line = lineConfig;
  } else if (chartType === 'area') {
    plotConfig.area = {
      fillOpacity,
      lineWidth: 1,
      marker: {
        enabled: false,
      },
      ...(stacking && { stacking }),
      ...customOptions
    };
  } else if (chartType === 'column') {
    plotConfig.column = {
      ...(stacking && { stacking }),
      ...(dataLabels && { dataLabels }),
      ...customOptions
    };
  }

  return plotConfig;
};

/**
 * Create complete line chart configuration with all common settings
 * Combines base chart, axes, legend, tooltip, and plot options for line charts
 * 
 * @param {Object} options - Complete line chart configuration options
 * @param {string} options.title - Chart title text
 * @param {string} options.subtitle - Chart subtitle text
 * @param {number} [options.height=400] - Chart height in pixels
 * @param {Object} [options.xAxis={}] - X-axis configuration (passed to createXAxisConfig)
 * @param {Object} [options.yAxis={}] - Y-axis configuration (passed to createYAxisConfig)
 * @param {Array<Object>} options.series - Chart series data array
 * @param {Object} [options.tooltip={}] - Tooltip configuration (passed to createTooltipConfig)
 * @param {Object} [options.legend={}] - Legend configuration (passed to createLegendConfig)
 * @param {Object} [options.plotOptions={}] - Plot options (passed to createPlotOptionsConfig)
 * @param {boolean} [options.showLegend=false] - Whether to show legend (defaults to false for line charts)
 * @param {boolean} [options.enableSeriesLabels=false] - Enable series-label module labels
 * @param {Object} [options.chart={}] - Chart-specific overrides
 * @param {Object} [options...customOptions] - Additional Highcharts options to merge
 * 
 * @returns {Object} Complete Highcharts line chart configuration object
 * 
 * @example
 * createLineChartConfig({
 *   title: 'Temperature Over Time',
 *   subtitle: 'Daily measurements',
 *   xAxis: { title: 'Date' },
 *   yAxis: { title: 'Temperature (°C)' },
 *   series: [{ name: 'Temp', data: [20, 22, 24] }]
 * });
 */
export const createLineChartConfig = (options = {}) => {
  const {
    title,
    subtitle,
    height,
    xAxis = {},
    yAxis = {},
    series = [],
    tooltip = {},
    legend = {},
    plotOptions = {},
    showLegend = false, // Default to hidden legend for line charts
    enableSeriesLabels = false, // Enable series-label module labels
    chart: chartOverrides = {},
    ...customOptions
  } = options;

  // Configure legend based on showLegend parameter
  const legendConfig = showLegend 
    ? createLegendConfig(legend) 
    : { enabled: false };

  // Automatically add label configuration to all series if enabled
  const seriesWithLabels = enableSeriesLabels
    ? series.map(s => ({
        ...s,
        label: {
          enabled: true,
          minFontSize: 10,
          maxFontSize: 12,
          style: {
            fontWeight: '600',
            textOutline: '2px white',
            color: '#1f2937'
          }
        }
      }))
    : series;

  const baseConfig = createBaseChartConfig({ type: 'line', title, subtitle, height });

  return {
    ...baseConfig,
    chart: {
      ...baseConfig.chart,
      ...chartOverrides
    },
    xAxis: createXAxisConfig(xAxis),
    yAxis: createYAxisConfig(yAxis),
    legend: legendConfig,
    tooltip: createTooltipConfig(tooltip),
    plotOptions: createPlotOptionsConfig({ chartType: 'line', ...plotOptions }),
    series: seriesWithLabels,
    ...customOptions
  };
};

/**
 * Create complete area chart configuration with all common settings
 * Combines base chart, axes, legend, tooltip, and plot options for area charts
 * Uses bottom-aligned horizontal legend by default
 * 
 * @param {Object} options - Complete area chart configuration options
 * @param {string} options.title - Chart title text
 * @param {string} options.subtitle - Chart subtitle text
 * @param {number} [options.height=400] - Chart height in pixels
 * @param {Object} [options.xAxis={}] - X-axis configuration (passed to createXAxisConfig)
 * @param {Object} [options.yAxis={}] - Y-axis configuration (passed to createYAxisConfig)
 * @param {Array<Object>} options.series - Chart series data array
 * @param {Object} [options.tooltip={}] - Tooltip configuration (defaults to shared=true)
 * @param {Object} [options.legend={}] - Legend configuration (defaults to bottom horizontal)
 * @param {Object} [options.plotOptions={}] - Plot options (passed to createPlotOptionsConfig)
 * @param {boolean} [options.showLegend=true] - Whether to show legend (defaults to true for area charts)
 * @param {boolean} [options.enableSeriesLabels=false] - Enable series-label module labels
 * @param {Object} [options...customOptions] - Additional Highcharts options to merge
 * 
 * @returns {Object} Complete Highcharts area chart configuration object
 * 
 * @example
 * createAreaChartConfig({
 *   title: 'Energy Production',
 *   subtitle: 'By fuel type',
 *   xAxis: { categories: ['2020', '2021', '2022'] },
 *   yAxis: { title: 'TWh' },
 *   series: [{ name: 'Solar', data: [10, 15, 20] }]
 * });
 */
export const createAreaChartConfig = (options = {}) => {
  const {
    title,
    subtitle,
    height,
    xAxis = {},
    yAxis = {},
    series = [],
    tooltip = {},
    legend = {},
    plotOptions = {},
    showLegend = true, // Default to showing legend
    enableSeriesLabels = false, // Enable series-label module labels
    ...customOptions
  } = options;

  // Configure legend based on showLegend parameter
  const legendConfig = showLegend 
    ? createLegendConfig({ 
        align: 'center', 
        verticalAlign: 'bottom', 
        layout: 'horizontal',
        floating: false,
        x: 0,
        y: 0,
        ...legend 
      })
    : { enabled: false };

  // Automatically add label configuration to all series if enabled
  const seriesWithLabels = enableSeriesLabels
    ? series.map(s => ({
        ...s,
        label: {
          enabled: true,
          minFontSize: 10,
          maxFontSize: 12,
          style: {
            fontWeight: '600',
            textOutline: '2px white',
            color: '#1f2937'
          }
        }
      }))
    : series;

  return {
    ...createBaseChartConfig({ type: 'area', title, subtitle, height }),
    xAxis: createXAxisConfig(xAxis),
    yAxis: createYAxisConfig(yAxis),
    legend: legendConfig,
    tooltip: createTooltipConfig({ shared: true, ...tooltip }),
    plotOptions: createPlotOptionsConfig({ chartType: 'area', ...plotOptions }),
    series: seriesWithLabels,
    ...customOptions
  };
};

/**
 * Create complete stacked column chart configuration with all common settings
 * Configures stacked column chart for displaying percentage shares or distributions
 * Uses bottom-aligned horizontal legend by default with shared tooltips
 * 
 * @param {Object} options - Complete stacked column chart configuration options
 * @param {string} options.title - Chart title text
 * @param {string} options.subtitle - Chart subtitle text
 * @param {number} [options.height=400] - Chart height in pixels
 * @param {Object} [options.xAxis={}] - X-axis configuration (passed to createXAxisConfig)
 * @param {Object} [options.yAxis={}] - Y-axis configuration (passed to createYAxisConfig)
 * @param {Array<Object>} options.series - Chart series data array
 * @param {Object} [options.tooltip={}] - Tooltip configuration (defaults to shared=true)
 * @param {Object} [options.legend={}] - Legend configuration (defaults to bottom horizontal)
 * @param {string} [options.stacking='percent'] - Stacking type: 'percent' or 'normal'
 * @param {boolean} [options.showDataLabels=false] - Whether to show data labels on last point
 * @param {boolean} [options.showLegend=false] - Whether to show legend (defaults to false)
 * @param {Object} [options.chart={}] - Chart-specific overrides (e.g., spacingBottom)
 * @param {Object} [options...customOptions] - Additional Highcharts options to merge
 * 
 * @returns {Object} Complete Highcharts stacked column chart configuration object
 * 
 * @example
 * createStackedColumnChartConfig({
 *   title: 'Electricity Share',
 *   subtitle: 'By sector',
 *   xAxis: { categories: ['2020', '2025', '2030'] },
 *   yAxis: { title: '%', max: 100 },
 *   series: [{ name: 'Industry', data: [40, 45, 50], stack: 'share' }]
 * });
 */
export const createStackedColumnChartConfig = (options = {}) => {
  const {
    title,
    subtitle,
    height,
    xAxis = {},
    yAxis = {},
    series = [],
    tooltip = {},
    legend = {},
    stacking = 'percent',
    showDataLabels = false,
    showLegend = false,
    chart: chartOverrides = {},
    ...customOptions
  } = options;

  // Configure legend - disabled by default
  const legendConfig = showLegend
    ? createLegendConfig({
        align: 'center',
        verticalAlign: 'bottom',
        layout: 'horizontal',
        floating: false,
        x: 0,
        y: 0,
        ...legend
      })
    : { enabled: false };

  // Default tooltip with shared mode for stacked charts
  const defaultTooltip = {
    shared: true,
    formatter: function() {
      let tooltip = `<b>${this.x}</b><br/>`;
      this.points.forEach((point) => {
        if (point.y > 0) {
          tooltip += `<span style="color:${point.color}">●</span> ${point.series.name}: <b>${smartFormatNumber(point.y)}${stacking === 'percent' ? '%' : ''}</b><br/>`;
        }
      });
      return tooltip;
    },
    ...tooltip
  };

  // Default plot options for stacked columns
  const defaultPlotOptions = {
    column: {
      stacking,
      borderWidth: 0,
      dataLabels: showDataLabels ? {
        enabled: true,
        formatter: function() {
          // Show series name only on the last point (last year)
          const lastIndex = this.series.data.length - 1;
          if (this.point.index === lastIndex) {
            return this.series.name;
          }
          return '';
        },
        style: {
          fontSize: '11px',
          fontWeight: '600',
          textOutline: '2px white',
          color: '#1f2937'
        },
        align: 'right',
        verticalAlign: 'middle',
        x: 10,
        allowOverlap: true
      } : {
        enabled: false
      }
    }
  };

  const baseConfig = createBaseChartConfig({ type: 'column', title, subtitle, height });

  return {
    ...baseConfig,
    chart: {
      ...baseConfig.chart,
      ...chartOverrides
    },
    xAxis: createXAxisConfig(xAxis),
    yAxis: {
      ...createYAxisConfig(yAxis),
      stackLabels: {
        enabled: false
      }
    },
    legend: legendConfig,
    tooltip: createTooltipConfig(defaultTooltip),
    plotOptions: defaultPlotOptions,
    series,
    ...customOptions
  };
};

/**
 * Default color palette for charts
 * Provides semantic color names and descriptive aliases for consistency
 */
export const CHART_COLORS = {
  // Semantic colors
  primary: "#8B5CF6",
  secondary: "#06B6D4", 
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  info: "#3B82F6",
  // Descriptive aliases (same values as semantic colors for clarity)
  purple: "#8B5CF6",    // Alias for primary
  cyan: "#06B6D4",      // Alias for secondary
  emerald: "#10B981",   // Alias for success
  amber: "#F59E0B",     // Alias for warning
  red: "#EF4444",       // Alias for danger
  blue: "#3B82F6",     // Alias for info
  gray: "#6B7280"
};

/**
 * Get level colors for geographic comparison charts
 * @param {string} level - Level name (country, region, world)
 * @param {string} countryName - Country name for dynamic coloring
 * @returns {string} Hex color code
 */
export const getLevelColor = (level, countryName = '') => {
  const colors = {
    [countryName]: CHART_COLORS.purple,
    "World": CHART_COLORS.emerald
  };
  
  // Handle dynamic region names (R10LATIN_AM, R10EUROPE, etc.)
  if (level && level.startsWith('R10')) {
    return CHART_COLORS.cyan;
  }
  
  return colors[level] || CHART_COLORS.gray;
};

// Export all configurations
// Note: createBaseChartConfig, createPlotOptionsConfig, createXAxisConfig, 
// createYAxisConfig, createLegendConfig, createTooltipConfig are internal utilities
// used by the chart config functions above, not exported
const highchartsConfig = {
  CHART_STYLES,
  CHART_DIMENSIONS,
  ANIMATION_CONFIG,
  CHART_COLORS,
  createLineChartConfig,
  createAreaChartConfig,
  createStackedColumnChartConfig,
  getLevelColor
};

export default highchartsConfig;
