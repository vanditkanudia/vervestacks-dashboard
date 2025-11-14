import React, { useState, useEffect } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official';
import { energyMetricsAPI } from '../../services/api';
import toast from 'react-hot-toast';
import { smartFormatNumber } from '../../utils/numberFormatting';
import { createLineChartConfig, createStackedColumnChartConfig } from '../../utils/highchartsConfig';
import { getFuelColor } from '../../utils/fuelColors';
import { initializeFuelColors } from '../../utils/fuelColors';

const AR6ScenarioChart = ({ countryIso, countryName }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Initialize fuel colors first
        await initializeFuelColors();

        // Country ISO used to fetch scenario data

        const response = await energyMetricsAPI.getAr6ScenarioDrivers(countryIso);

        if (response && response.success && response.data) {
          setChartData(response.data);
        } else {
          throw new Error(response?.error || 'Failed to load AR6 scenario data');
        }
      } catch (err) {
        console.error('Error loading AR6 scenario data:', err);
        setError(err.message);
        toast.error(`Failed to load AR6 scenario data: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [countryIso]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading AR6 scenario data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="text-red-500 text-lg font-medium mb-2">Error</div>
          <div className="text-gray-600 text-sm">{error}</div>
        </div>
      </div>
    );
  }

  if (!chartData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center text-gray-600">No AR6 scenario data available</div>
      </div>
    );
  }

  // Prepare data for CO2 prices chart
  const prepareCO2Data = () => {
    const { co2_chart_data, categories, colors, years } = chartData;
    
    return categories.map(category => ({
      name: category,
      data: years.map(year => {
        const value = co2_chart_data[category]?.[year];
        return [year, value !== undefined && !isNaN(value) ? value : null];
      }),
      color: colors[category],
      lineWidth: 3,
      marker: {
        enabled: true,
        radius: 4
      }
    }));
  };

  // Prepare data for electricity demand chart
  const prepareElectricityData = () => {
    const { elec_chart_data, iea_years, iea_values, categories, colors, years } = chartData;
    
    // Historical data (from IEA)
    const historicalSeries = [{
      name: 'IEA Historical',
      data: iea_years.map((year, idx) => [year, iea_values[idx]]),
      type: 'line',
      dashStyle: 'Dash',
      color: '#666',
      lineWidth: 2,
      marker: {
        enabled: true,
        radius: 3
      },
      legendIndex: 0
    }];

    // Projected data for each category
    const categorySeries = categories.map(category => ({
      name: category,
      data: years.map(year => {
        const value = elec_chart_data[category]?.[year];
        return [year, value !== undefined && !isNaN(value) ? value : null];
      }),
      type: 'line',
      color: colors[category],
      lineWidth: 2.5,
      marker: {
        enabled: true,
        radius: 4
      }
    }));

    return [...historicalSeries, ...categorySeries];
  };

  // Prepare data for hydrogen demand chart
  const prepareHydrogenData = () => {
    const { hydrogen_chart_data, categories, colors, years } = chartData;
    
    return categories.map(category => ({
      name: category,
      data: years.map(year => {
        const value = hydrogen_chart_data[category]?.[year];
        return [year, value !== undefined && !isNaN(value) ? value : null];
      }),
      color: colors[category],
      lineWidth: 3,
      marker: {
        enabled: true,
        radius: 4
      }
    }));
  };

  // Prepare data for fuel price chart
  const prepareFuelPriceData = () => {
    const { fuel_price_chart_data, years } = chartData;
    
    if (!fuel_price_chart_data) {
      return [];
    }
    
    // Map fuel keys from data to readable names and fuel types for colors
    const fuelDisplayNames = {
      'gas': 'Gas',
      'oil': 'Oil',
      'coal': 'Coal',
      'bioenergy': 'Biomass'
    };
    
    return Object.keys(fuel_price_chart_data).map(fuelKey => {
      const fuelType = fuelKey.toLowerCase(); // Use the key as fuel type for getFuelColor
      return {
        name: fuelDisplayNames[fuelKey] || fuelKey.charAt(0).toUpperCase() + fuelKey.slice(1),
        data: years.map(year => {
          const value = fuel_price_chart_data[fuelKey]?.[year];
          return [year, value !== undefined && !isNaN(value) ? value : null];
        }),
        color: getFuelColor(fuelType),
        lineWidth: 3,
        marker: {
          enabled: true,
          radius: 4
        }
      };
    });
  };

  // Prepare data for C1 electricity share stacked bar chart
  const prepareC1ElectricityShareData = () => {
    const { years, c1_elec_share_chart_data } = chartData;
    
    if (!c1_elec_share_chart_data) {
      return [];
    }
    
    // Map API keys to display names
    const seriesNameMapping = {
      'Transportation electricity share': 'Transportation',
      'Industry electricity share': 'Industry',
      'Residential and commercial electricity share': 'Residential and commercial'
    };
    
    // Get all unique fuel types from the data
    const fuelTypes = new Set();
    Object.keys(c1_elec_share_chart_data).forEach(fuel => fuelTypes.add(fuel));
    
    // Prepare series for each source
    return Array.from(fuelTypes).map(fuel => ({
      name: seriesNameMapping[fuel] || fuel.charAt(0).toUpperCase() + fuel.slice(1),
      data: years.map(year => {
        const value = c1_elec_share_chart_data[fuel]?.[year];
        return value !== undefined && !isNaN(value) ? value : 0;
      }),
      stack: 'share'
    }));
  };

  // Prepare data for C7 electricity share stacked bar chart
  const prepareC7ElectricityShareData = () => {
    const { years, c7_elec_share_chart_data } = chartData;
    
    if (!c7_elec_share_chart_data) {
      return [];
    }
    
    // Map API keys to display names
    const seriesNameMapping = {
      'Transportation electricity share': 'Transportation',
      'Industry electricity share': 'Industry',
      'Residential and commercial electricity share': 'Residential and commercial'
    };
    
    // Get all unique fuel types from the data
    const fuelTypes = new Set();
    Object.keys(c7_elec_share_chart_data).forEach(fuel => fuelTypes.add(fuel));
    
    // Prepare series for each source
    return Array.from(fuelTypes).map(fuel => ({
      name: seriesNameMapping[fuel] || fuel.charAt(0).toUpperCase() + fuel.slice(1),
      data: years.map(year => {
        const value = c7_elec_share_chart_data[fuel]?.[year];
        return value !== undefined && !isNaN(value) ? value : 0;
      }),
      stack: 'share'
    }));
  };

  // Chart configurations using common utilities
  const co2ChartOptions = createLineChartConfig({
    title: 'CO₂ Price Trajectories',
    subtitle: 'Projected carbon prices across different AR6 climate scenarios',
    height: 350,

    xAxis: { 
      title: '', 
      categories: chartData.years 
    },
    yAxis: { 
      title: '$/tCO₂'
    },
    tooltip: {
      formatter: function() {
        const formattedValue = this.y !== null && this.y !== undefined ? smartFormatNumber(this.y) : 'N/A';
        return `<b>${this.series.name}</b><br/>${this.x}: ${formattedValue}`;
      }
    },
    enableSeriesLabels: true,
    series: prepareCO2Data()
  });

  const elecChartOptions = createLineChartConfig({
    title: 'Electricity Demand Projections',
    subtitle: 'Historical demand and future projections under different AR6 scenarios',
    height: 350,
   
    xAxis: { title: '' },
    yAxis: { title: 'TWh' },
    tooltip: {
      formatter: function() {
        const formattedValue = this.y !== null && this.y !== undefined ? smartFormatNumber(this.y) : 'N/A';
        return `<b>${this.series.name}</b><br/>${this.x}: ${formattedValue}`;
      }
    },
    enableSeriesLabels: true,
    series: prepareElectricityData()
  });

  const hydrogenChartOptions = createLineChartConfig({
    title: 'Hydrogen Demand Projections',
    subtitle: 'Projected hydrogen production demand under different AR6 scenarios',
    height: 350,
    
    xAxis: { 
      title: '', 
      categories: chartData.years 
    },
    yAxis: { title: 'TWh' },
    tooltip: {
      formatter: function() {
        const formattedValue = this.y !== null && this.y !== undefined ? smartFormatNumber(this.y) : 'N/A';
        return `<b>${this.series.name}</b><br/>${this.x}: ${formattedValue}`;
      }
    },
    enableSeriesLabels: true,
    series: prepareHydrogenData()
  });

  const fuelPriceChartOptions = createLineChartConfig({
    title: 'Fuel Price Projections',
    subtitle: 'Projected fuel prices under C7 scenario',
    height: 350,
    
    xAxis: { 
      title: '', 
      categories: chartData.years 
    },
    yAxis: { title: 'USD/MWh' },
    tooltip: {
      formatter: function() {
        const formattedValue = this.y !== null && this.y !== undefined ? smartFormatNumber(this.y) : 'N/A';
        return `<b>${this.series.name}</b><br/>${this.x}: ${formattedValue}`;
      }
    },
    enableSeriesLabels: true,
    series: prepareFuelPriceData()
  });

  const c1ElecShareChartOptions = createStackedColumnChartConfig({
    title: 'C1 Electricity Share',
    subtitle: 'Ambitious scenario: Electricity generation by fuel type',
    height: 350,
    xAxis: { 
      title: '', 
      categories: chartData.years 
    },
    yAxis: { 
      title: '%',
      max: 100
    },
    stacking: 'percent',
    showDataLabels: true,
    series: prepareC1ElectricityShareData()
  });

  const c7ElecShareChartOptions = createStackedColumnChartConfig({
    title: 'C7 Electricity Share',
    subtitle: 'Limited action scenario: Electricity generation by fuel type',
    height: 350,
    xAxis: { 
      title: '', 
      categories: chartData.years 
    },
    yAxis: { 
      title: '%',
      max: 100
    },
    stacking: 'percent',
    showDataLabels: true,
    series: prepareC7ElectricityShareData()
  });

  return (
    <div className="space-y-4">
      {/* R10 Region Info Card */}
      {chartData.r10_region && (
        <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg px-4 py-3 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-700">AR6 R10 Region:</span>
              <span className="text-sm font-mono bg-white px-2 py-1 rounded border border-purple-200 text-purple-700">
                {chartData.r10_region}
              </span>
            </div>
            <span className="text-xs text-gray-600 italic">IPCC AR6 climate scenario projections</span>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg p-6 shadow-sm">
          <HighchartsReact highcharts={Highcharts} options={co2ChartOptions} />
        </div>

        <div className="bg-white rounded-lg p-6 shadow-sm">
          <HighchartsReact highcharts={Highcharts} options={elecChartOptions} />
        </div>

        <div className="bg-white rounded-lg p-6 shadow-sm">
          <HighchartsReact highcharts={Highcharts} options={hydrogenChartOptions} />
        </div>

        {chartData.fuel_price_chart_data && Object.keys(chartData.fuel_price_chart_data).length > 0 && (
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <HighchartsReact highcharts={Highcharts} options={fuelPriceChartOptions} />
          </div>
        )}

        {chartData.c1_elec_share_chart_data && Object.keys(chartData.c1_elec_share_chart_data).length > 0 && (
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <HighchartsReact highcharts={Highcharts} options={c1ElecShareChartOptions} />
          </div>
        )}

        {chartData.c7_elec_share_chart_data && Object.keys(chartData.c7_elec_share_chart_data).length > 0 && (
          <div className="bg-white rounded-lg p-6 shadow-sm">
            <HighchartsReact highcharts={Highcharts} options={c7ElecShareChartOptions} />
          </div>
        )}
      </div>
    </div>
  );
};

export default AR6ScenarioChart;

