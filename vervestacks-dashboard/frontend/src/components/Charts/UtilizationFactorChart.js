import React, { useState, useEffect, useCallback } from "react";
import Highcharts from "highcharts";
import HighchartsReact from "highcharts-react-official";
import { energyMetricsAPI } from "../../services/api";
import { createLineChartConfig, getLevelColor } from "../../utils/highchartsConfig";
import { smartFormatNumber } from "../../utils/numberFormatting";
import toast from "react-hot-toast";

const UtilizationFactorChart = ({ countryIso, countryName, height }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadUtilizationData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await energyMetricsAPI.getEnergyMetrics(countryIso);

      if (response && response.success && response.data) {
        setChartData(response.data);
      } else {
        throw new Error("Failed to load utilization factor data");
      }
    } catch (error) {
      console.error("Error loading utilization factor data:", error);
      setError(error.message);
      toast.error("Failed to load utilization factor data");
    } finally {
      setLoading(false);
    }
  }, [countryIso]);

  useEffect(() => {
    loadUtilizationData();
  }, [loadUtilizationData]);

  const getChartOptions = () => {
    if (!chartData || !chartData.utilization_data) {
      return createLineChartConfig({
        title: "No Utilization Factor Data Available",
        xAxis: { type: 'linear', title: '' },
        yAxis: { title: "%", formatter: function() { return smartFormatNumber(this.value); }},
        series: []
      });
    }

    // Process utilization data
    const utilizationData = chartData.utilization_data;
    
    // Group data by level and extract region name dynamically
    const regionData = utilizationData.find(item => item.Level && item.Level.startsWith('R10'));
    const regionName = regionData ? regionData.Level : "Region";
    
    const levelConfig = [
      { dataKey: "ISO", displayName: countryName },
      { dataKey: "R10", displayName: regionName },
      { dataKey: "World", displayName: "World" }
    ];
    const series = levelConfig.map(({ dataKey, displayName }) => {
      const levelData = utilizationData.filter(item => 
        item.Level && item.Level.includes(dataKey)
      );
      
      return {
        name: displayName,
        data: levelData.map(item => {
          const utilizationFactorRaw = parseFloat(item.Utilization_Factor) || 0;
          const utilizationFactorPercent = utilizationFactorRaw * 100; // Convert to percentage
          return {
            x: parseInt(item.Year) || 0,
            y: utilizationFactorPercent,
            name: `${item.Year}: ${utilizationFactorPercent.toFixed(1)}%`
          };
        }).sort((a, b) => a.x - b.x),
        color: getLevelColor(displayName, countryName)
      };
    });

    return createLineChartConfig({
      title: "Fossil Fuel Utilization Factor",
      subtitle: "Annual fossil fuel power plant utilization across geographic levels",
      height: height || 400,
      xAxis: { type: 'linear', title: '' },
      yAxis: { 
        title: "%",
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
                  Utilization Factor: ${formattedValue}%`;
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
            onClick={loadUtilizationData}
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

export default UtilizationFactorChart;