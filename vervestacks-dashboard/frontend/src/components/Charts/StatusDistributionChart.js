import React, { useState, useEffect, useCallback } from 'react';
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official';
import { energyMetricsAPI } from '../../services/api';
import { smartFormatNumber } from '../../utils/numberFormatting';
import toast from 'react-hot-toast';

const StatusDistributionChart = ({ countryIso }) => {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadStatusData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await energyMetricsAPI.getExistingStockMetrics(countryIso);

      if (response && response.success && response.data) {
        setChartData(response.data);
      } else {
        throw new Error('Failed to load status distribution data');
      }
    } catch (error) {
      console.error('Error loading status distribution data:', error);
      setError(error.message);
      toast.error('Failed to load status distribution data');
    } finally {
      setLoading(false);
    }
  }, [countryIso]);

  useEffect(() => {
    loadStatusData();
  }, [loadStatusData]);

  const getChartOptions = () => {
    if (!chartData || !chartData.status_distribution) {
      return {
        chart: { type: 'column', height: 400 },
        title: { text: 'No Status Data Available' },
        series: []
      };
    }

    const statusData = chartData.status_distribution;
    
    // Convert to Highcharts format
    const seriesData = Object.entries(statusData).map(([status, count]) => ({
      name: status.charAt(0).toUpperCase() + status.slice(1),
      y: count,
      color: getStatusColor(status)
    }));

    return {
      chart: {
        type: 'column',
        height: 400,
        backgroundColor: 'transparent',
        style: {
          fontFamily: 'Inter, system-ui, sans-serif',
        },
      },
      title: {
        text: 'Plant Status Distribution',
        style: {
          fontSize: '18px',
          fontWeight: '600',
          color: '#1f2937',
        },
      },
      subtitle: {
        text: `Total Plants: ${chartData.metadata?.total_plants || 0}`,
        style: {
          fontSize: '14px',
          color: '#6b7280',
        },
      },
      xAxis: {
        type: 'category',
        labels: {
          style: {
            fontSize: '12px',
            color: '#374151',
          },
        },
      },
      yAxis: {
        title: {
          text: 'Number of Plants',
          style: {
            fontSize: '12px',
            color: '#374151',
          },
        },
        labels: {
          style: {
            fontSize: '11px',
            color: '#6b7280',
          },
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
          const percentage = ((this.y / chartData.metadata.total_plants) * 100);
          const formattedPercentage = smartFormatNumber(percentage);
          return `<b>${this.point.name}</b><br/>
                  Plants: <b>${smartFormatNumber(this.y)}</b><br/>
                  Share: <b>${formattedPercentage}%</b>`;
        },
      },
      plotOptions: {
        column: {
          borderRadius: 4,
          dataLabels: {
            enabled: true,
            format: '{y}',
            style: {
              fontSize: '11px',
              fontWeight: '500',
              color: '#374151',
            },
          },
        },
        series: {
          animation: {
            duration: 1000,
          },
        },
      },
      legend: {
        enabled: false,
      },
      credits: {
        enabled: false,
      },
      series: [{
        name: 'Plants',
        data: seriesData,
      }],
    };
  };

  const getStatusColor = (status) => {
    const colors = {
      operating: '#10b981',      // Green
      construction: '#f59e0b',   // Amber
      permitted: '#3b82f6',     // Blue
      'pre-permit': '#8b5cf6',   // Purple
      announced: '#ef4444',      // Red
      shelved: '#6b7280',        // Gray
      cancelled: '#dc2626',      // Red
      mothballed: '#f97316',     // Orange
    };
    return colors[status.toLowerCase()] || '#6b7280';
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
            onClick={loadStatusData}
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

export default StatusDistributionChart;
