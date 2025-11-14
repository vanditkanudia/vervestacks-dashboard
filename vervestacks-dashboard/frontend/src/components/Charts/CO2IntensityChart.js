import React, { useState, useEffect, useCallback } from "react";
import Highcharts from "highcharts";
import HighchartsReact from "highcharts-react-official";
import { energyMetricsAPI } from "../../services/api";
import { createLineChartConfig, getLevelColor } from "../../utils/highchartsConfig";
import { smartFormatNumber } from "../../utils/numberFormatting";
import toast from "react-hot-toast";

const CO2IntensityChart = ({ countryIso, countryName, height }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadCO2Data = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await energyMetricsAPI.getEnergyMetrics(countryIso);

      if (response && response.success && response.data) {
        setChartData(response.data);
      } else {
        throw new Error("Failed to load CO2 intensity data");
      }
    } catch (error) {
      console.error("Error loading CO2 intensity data:", error);
      setError(error.message);
      toast.error("Failed to load CO2 intensity data");
    } finally {
      setLoading(false);
    }
  }, [countryIso]);

  useEffect(() => {
    loadCO2Data();
  }, [loadCO2Data]);

  const getChartOptions = () => {
    if (!chartData || !chartData.co2_intensity_data) {
      return createLineChartConfig({
        title: "No CO2 Intensity Data Available",
        xAxis: { type: 'linear', title: '' },
        yAxis: { title: "kg CO2/MWh", formatter: function() { return smartFormatNumber(this.value); }},
        series: []
      });
    }

    // Process CO2 intensity data
    const co2Data = chartData.co2_intensity_data;
    
    // Group data by level and extract region name dynamically
    const regionData = co2Data.find(item => item.Level && item.Level.startsWith('R10'));
    const regionName = regionData ? regionData.Level : "Region";
    
    const levelConfig = [
      { dataKey: "ISO", displayName: countryName },
      { dataKey: "R10", displayName: regionName },
      { dataKey: "World", displayName: "World" }
    ];
    const series = levelConfig.map(({ dataKey, displayName }) => {
      const levelData = co2Data.filter(item => 
        item.Level && item.Level.includes(dataKey)
      );
      
      return {
        name: displayName,
        data: levelData.map(item => {
          const co2IntensityMWh = parseFloat(item.CO2_Intensity) || 0; // already kg CO2/MWh from backend
          return {
            x: parseInt(item.Year) || 0,
            y: co2IntensityMWh,
            name: `${item.Year}: ${co2IntensityMWh.toFixed(1)} kg CO2/MWh`
          };
        }).sort((a, b) => a.x - b.x),
        color: getLevelColor(displayName, countryName)
      };
    });

    return createLineChartConfig({
      title: "CO2 Intensity",
      subtitle: "Annual CO2 emissions per unit of electricity generated",
      height: height || 400,
      xAxis: { type: 'linear', title: '' },
      yAxis: { 
        title: "kg CO2/MWh",
        formatter: function() {
          return smartFormatNumber(this.value);
        }
      },
      series,
      tooltip: {
        formatter: function() {
          const formattedValue = this.y !== null && this.y !== undefined ? smartFormatNumber(this.y) : 'N/A';
          return `<b>${this.series.name}</b><br/>
                  Year: ${this.x}<br/>
                  CO2 Intensity: ${formattedValue} kg CO2/MWh`;
        }
      }
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
      <div className="p-3">
        <div className="text-center">
          <div className="text-red-500 text-lg font-medium mb-2">Error Loading Data</div>
          <div className="text-gray-600 text-sm mb-4">{error}</div>
          <button
            onClick={loadCO2Data}
            className="btn-primary"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-3">
      <HighchartsReact highcharts={Highcharts} options={getChartOptions()} />
    </div>
  );
};

export default CO2IntensityChart;