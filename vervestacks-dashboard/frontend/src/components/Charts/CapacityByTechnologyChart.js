import React, { useState, useEffect, useCallback } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official';
import { energyMetricsAPI } from '../../services/api';
import { smartFormatNumber } from '../../utils/numberFormatting';
import toast from 'react-hot-toast';

const CapacityByTechnologyChart = ({ countryIso }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadCapacityData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await energyMetricsAPI.getExistingStockMetrics(countryIso);

      if (response && response.success && response.data) {
        setChartData(response.data);
      } else {
        throw new Error('Failed to load capacity by technology data');
      }
    } catch (error) {
      console.error('Error loading capacity by technology data:', error);
      setError(error.message);
      toast.error('Failed to load capacity by technology data');
    } finally {
      setLoading(false);
    }
  }, [countryIso]);

  useEffect(() => {
    loadCapacityData();
  }, [loadCapacityData]);

  const getChartOptions = () => {
    if (!chartData || !chartData.capacity_by_technology) {
      return {
        chart: { type: 'pie', height: 400 },
        title: { text: 'No Capacity Data Available' },
        series: []
      };
    }

    const capacityData = chartData.capacity_by_technology;
    
    // Convert to Highcharts format
    const seriesData = Object.entries(capacityData).map(([technology, capacity]) => ({
      name: technology.charAt(0).toUpperCase() + technology.slice(1),
      y: capacity,
      color: getTechnologyColor(technology)
    }));

    return {
      chart: {
        type: 'pie',
        height: 400,
        backgroundColor: 'transparent',
        style: {
          fontFamily: 'Inter, system-ui, sans-serif',
        },
      },
      title: {
        text: 'Capacity by Technology',
        style: {
          fontSize: '18px',
          fontWeight: '600',
          color: '#1f2937',
        },
      },
      subtitle: {
        text: `Total Operating Capacity: ${smartFormatNumber(chartData.metadata?.total_operating_capacity_gw || 0)} GW`,
        style: {
          fontSize: '14px',
          color: '#6b7280',
        },
      },
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderWidth: 0,
        borderRadius: 8,
        shadow: true,
        style: {
          fontSize: '12px',
        },
        formatter: function() {
          const percentage = ((this.y / chartData.metadata.total_operating_capacity_gw) * 100);
          const formattedPercentage = smartFormatNumber(percentage);
          const formattedCapacity = smartFormatNumber(this.y);
          return `<b>${this.point.name}</b><br/>
                  Capacity: <b>${formattedCapacity} GW</b><br/>
                  Share: <b>${formattedPercentage}%</b>`;
        },
      },
      plotOptions: {
        pie: {
          allowPointSelect: true,
          cursor: 'pointer',
          dataLabels: {
            enabled: true,
            format: '<b>{point.name}</b>: {point.percentage:.1f}%',
            style: {
              fontSize: '11px',
              fontWeight: '500',
            },
          },
          showInLegend: true,
        },
        series: {
          animation: {
            duration: 1000,
          },
        },
      },
      legend: {
        enabled: true,
        align: 'right',
        verticalAlign: 'middle',
        layout: 'vertical',
        itemStyle: {
          fontSize: '12px',
          color: '#374151',
        },
      },
      credits: {
        enabled: false,
      },
      series: [{
        name: 'Capacity (GW)',
        data: seriesData,
        size: '80%',
        innerSize: '60%',
      }],
    };
  };

  const getTechnologyColor = (technology) => {
    const colors = {
      coal: '#1f2937',      // Dark slate
      gas: '#06b6d4',       // Cyan
      nuclear: '#f59e0b',   // Amber
      hydro: '#3b82f6',     // Blue
      wind: '#10b981',      // Emerald
      solar: '#fbbf24',     // Yellow
      biomass: '#8b5cf6',    // Purple
      geothermal: '#ef4444', // Red
      waste: '#6b7280',     // Gray
      oil: '#dc2626',       // Red
    };
    return colors[technology] || '#6b7280';
  };

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
          <div className="text-red-500 text-lg font-medium mb-2">Error Loading Data</div>
          <div className="text-gray-600 text-sm mb-4">{error}</div>
          <button
            onClick={loadCapacityData}
            className="btn-primary"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <HighchartsReact highcharts={Highcharts} options={getChartOptions()} />
    </div>
  );
};

export default CapacityByTechnologyChart;
