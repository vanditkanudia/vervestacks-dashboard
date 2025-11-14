import React, { useState, useEffect } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official';
import { getFuelColor } from '../../utils/fuelColors';
import { smartFormatNumber } from '../../utils/numberFormatting';
import { 
  createStackedColumnChartConfig
} from '../../utils/highchartsConfig';

const PlantSizeHistogram = ({ data }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (data && data.fuel_histograms && data.dominant_fuels) {
      try {
        const dominantFuels = data.dominant_fuels;
        const fuelHistograms = data.fuel_histograms;
        
        if (dominantFuels.length === 0) {
          setError('No coal, gas, oil, or nuclear plants found');
          setLoading(false);
          return;
        }

        // Define correct size category order (without 'MW' suffix)
        const correctSizeOrder = ['<10', '10-50', '50-100', '100-500', '500-1000', '1000+'];
        
        // Get all size categories from all fuels to ensure consistent x-axis
        const allSizeCategories = new Set();
        dominantFuels.forEach(fuel => {
          const fuelData = fuelHistograms[fuel];
          if (fuelData && fuelData.size_histogram) {
            Object.keys(fuelData.size_histogram).forEach(category => {
              allSizeCategories.add(category);
            });
          }
        });

        // Use correct order, filtering to only include categories that exist in data
        const categories = correctSizeOrder.filter(category => allSizeCategories.has(category));

        // Create series data for stacked chart
        const series = dominantFuels.map(fuel => {
          const fuelData = fuelHistograms[fuel];
          if (!fuelData || !fuelData.size_histogram) return null;

          const seriesData = categories.map(category => 
            fuelData.size_histogram[category] || 0
          );

          return {
            name: fuel.toUpperCase(),
            data: seriesData,
            color: getFuelColor(fuel),
            visible: true,  // Ensure series is visible
            showInLegend: true  // Ensure series shows in legend
          };
        }).filter(Boolean);

        // Calculate total capacity and plants for subtitle
        const totalCapacity = dominantFuels.reduce((sum, fuel) => {
          const fuelData = fuelHistograms[fuel];
          return sum + (fuelData?.total_capacity_gw || 0);
        }, 0);

        const totalPlants = dominantFuels.reduce((sum, fuel) => {
          const fuelData = fuelHistograms[fuel];
          return sum + (fuelData?.unit_count || 0);
        }, 0);

        setChartData({
          categories,
          series,
          title: 'Size Distribution by Fuel Type',
          subtitle: `${smartFormatNumber(totalCapacity)} GW, ${totalPlants} plants total`
        });
        setLoading(false);
        setError(null);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    } else if (data) {
      setError('No fuel histogram data available');
      setLoading(false);
    }
  }, [data]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="text-center">
          <div className="text-red-500 text-lg font-medium mb-2">Error Loading Size Histogram</div>
          <div className="text-gray-600 text-sm">{error}</div>
        </div>
      </div>
    );
  }

  if (!chartData) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="text-center">
          <div className="text-gray-500 text-lg font-medium mb-2">No Size Data Available</div>
          <div className="text-gray-600 text-sm">No plant size data found for this country.</div>
        </div>
      </div>
    );
  }

  const chartOptions = createStackedColumnChartConfig({
    title: chartData.title,
    subtitle: chartData.subtitle,
    xAxis: {
      title: 'MW',
      categories: chartData.categories
    },
    yAxis: {
      title: 'GW'
    },
    series: chartData.series,
    stacking: 'normal',
    showLegend: true,
    tooltip: {
      formatter: function() {
        const formattedValue = smartFormatNumber(this.y);
        const formattedTotal = smartFormatNumber(this.point.stackTotal);
        return `<b>${this.x}</b><br/>${this.series.name}: ${formattedValue} GW<br/>Total: ${formattedTotal} GW`;
      }
    }
  });

  // Override stackLabels to enable them with formatter
  chartOptions.yAxis.stackLabels = {
    enabled: true,
    style: { fontSize: '10px' },
    formatter: function() {
      return smartFormatNumber(this.total);
    }
  };

  return (
    <div className="">
      <HighchartsReact 
        highcharts={Highcharts} 
        options={chartOptions} 
      />
    </div>
  );
};

export default PlantSizeHistogram;
