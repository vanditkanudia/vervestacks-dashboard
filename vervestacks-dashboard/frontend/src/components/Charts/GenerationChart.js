import React, { useState, useEffect, useCallback } from "react";
import Highcharts from "highcharts";
import HighchartsReact from "highcharts-react-official";
import { capacityAPI } from "../../services/api";
import { getFuelColor } from "../../utils/fuelColors";
import { createAreaChartConfig } from "../../utils/highchartsConfig";
import { smartFormatNumber } from "../../utils/numberFormatting";
import toast from "react-hot-toast";

const GenerationChart = ({ countryIso, year = 2022, height }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadGenerationData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await capacityAPI.getCapacityUtilization(
        countryIso,
        year
      );

      // Data is now returned directly from backend (PostgreSQL structure)
      if (
        response &&
        response.success &&
        response.data
      ) {
        setChartData(response.data);
      } else {
        throw new Error("Invalid API response structure");
      }
    } catch (error) {
      console.error("Error loading generation data:", error);
      setError(error.message);
      toast.error("Failed to load generation data");
    } finally {
      setLoading(false);
    }
  }, [countryIso, year]);

  useEffect(() => {
    loadGenerationData();
  }, [loadGenerationData]);

  const getChartOptions = () => {
    if (!chartData || !chartData.generation_chart) {
      console.warn("GenerationChart: Missing required data properties");
      // Return a basic chart structure even with no data
      return createAreaChartConfig({
        title: "No Generation Data Available",
        subtitle: "Annual electricity generation by fuel type (2000-2022)",
        xAxis: { categories: [], title: '' },
        yAxis: { title: "TWh" },
        series: [],
        tooltip: { shared: true },
        plotOptions: { stacking: 'normal' }
      });
    }

    // Check if generation_chart has actual data (not empty object)
    const hasGenerationData =
      chartData.generation_chart &&
      Object.keys(chartData.generation_chart).length > 0 &&
      Object.values(chartData.generation_chart).some(
        (arr) => arr && arr.length > 0
      );

    if (!hasGenerationData) {
      console.warn(
        "GenerationChart: No generation data available for this country"
      );
      // Return a basic chart structure with no data message
      return createAreaChartConfig({
        title: "No Generation Data Available",
        subtitle: "Annual electricity generation by fuel type (2000-2022)",
        xAxis: { categories: [], title: '' },
        yAxis: { title: "TWh" },
        series: [],
        tooltip: { shared: true },
        plotOptions: { stacking: 'normal' }
      });
    }

    const { generation_chart, fuel_types, years } = chartData;

    // Use fuel_types and years from backend, fallback to extracting from generation_chart
    const fuelTypes = fuel_types || Object.keys(generation_chart);
    const chartYears = years || Array.from({ length: generation_chart[fuelTypes[0]]?.length || 0 }, (_, i) => 2000 + i);

    // Create series data for each fuel type
    const series = fuelTypes.map((fuelType) => {
      const fuelData = generation_chart[fuelType] || [];
      // Convert string values to numbers for Highcharts
      const numericData = fuelData.map(val => {
        const num = parseFloat(val);
        return isNaN(num) ? 0 : num;
      });
      return {
        name: fuelType.charAt(0).toUpperCase() + fuelType.slice(1),
        data: numericData,
        type: "area",
        stacking: "normal",
        color: getFuelColor(fuelType), // Use synchronous fuel color function
      };
    });

    return createAreaChartConfig({
      title: "Generation Trends",
      subtitle: "Annual electricity generation by fuel type (2000-2022)",
      height: height || 400,
      xAxis: { categories: chartYears, title: '' },
      yAxis: { title: "TWh" },
      series,
      tooltip: {
        shared: true,
        formatter: function () {
          let tooltip = `<b>${this.x}</b><br/>`;
          this.points.forEach((point) => {
            if (point.y > 0) {
              const formattedValue = smartFormatNumber(point.y);
              tooltip += `<span style="color:${point.color}">●</span> ${
                point.series.name
              }: <b>${formattedValue} TWh</b><br/>`;
            }
          });
          return tooltip;
        }
      },
      plotOptions: {
        stacking: 'normal'
      },
      showLegend: false, // Hide legend since labels are on areas
      enableSeriesLabels: true // Enable series-label module
    });
  };

  if (loading) {
    return (
      <div className="p-3">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <p className="text-gray-900 font-medium mb-2">Failed to load data</p>
          <p className="text-gray-600 text-sm mb-4">{error}</p>
          <button onClick={loadGenerationData} className="btn-primary">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!chartData) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-50 rounded-lg">
        <div className="text-center">
          <p className="text-gray-600">No generation data available</p>
        </div>
      </div>
    );
  }

  // Always render the chart container, let Highcharts handle empty data
  return (
    <div className="p-3">
      <HighchartsReact highcharts={Highcharts} options={getChartOptions()} />
    </div>
  );
};

export default GenerationChart;