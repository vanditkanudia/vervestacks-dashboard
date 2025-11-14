import React, { useState, useMemo, useEffect, useCallback } from 'react';
import Highcharts from 'highcharts/highstock';
import HighchartsReact from 'highcharts-react-official';

import { 
  Wind, 
  Sun,
  RefreshCw
} from 'lucide-react';
import { capacityAPI, generationProfileAPI, renewablePotentialAPI } from '../services/api';
import L from 'leaflet';
import api from '../services/api';
import toast from 'react-hot-toast';

// Import Highcharts modules for better functionality
import HighchartsMore from 'highcharts/highcharts-more';
import HighchartsExporting from 'highcharts/modules/exporting';
import HighchartsAccessibility from 'highcharts/modules/accessibility';
import HighchartsData from 'highcharts/modules/data';

// Initialize Highcharts modules
if (typeof Highcharts === 'object') {
  HighchartsMore(Highcharts);
  HighchartsExporting(Highcharts);
  HighchartsAccessibility(Highcharts);
  HighchartsData(Highcharts);
}

const GenerationProfileChart = ({ countryIso }) => {
  const [formData, setFormData] = useState({
    year: 2022
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [chartRef, setChartRef] = useState(null);
  const [capacityLoading, setCapacityLoading] = useState(false);
  const [capacityError, setCapacityError] = useState(null);
  const [solarProfile, setSolarProfile] = useState(null);
  const [solarLoading, setSolarLoading] = useState(false);
  const [solarError, setSolarError] = useState(null);
  const [solarCapacityGW, setSolarCapacityGW] = useState(null);
  const [solarSelectedCells, setSolarSelectedCells] = useState(null);
  const [windProfile, setWindProfile] = useState(null);
  const [windLoading, setWindLoading] = useState(false);
  const [windError, setWindError] = useState(null);
  const [windCapacityGW, setWindCapacityGW] = useState(null);
  const [solarInputGW, setSolarInputGW] = useState('');
  const [windInputGW, setWindInputGW] = useState('');
  const [solarZonesGeoJSON, setSolarZonesGeoJSON] = useState(null);
  const [windZonesGeoJSON, setWindZonesGeoJSON] = useState(null);
  const simulatorMapRef = React.useRef(null);
  const simulatorLayerRef = React.useRef(null);
  const simulatorWindMapRef = React.useRef(null);
  const simulatorWindLayerRef = React.useRef(null);
  const [windSelectedCells, setWindSelectedCells] = useState(null);

  // Sidebar generation summaries (GW)
  const solarAvgGW = useMemo(() => {
    if (!Array.isArray(solarProfile) || solarProfile.length === 0) return null;
    const sumMW = solarProfile.reduce((s, v) => s + (typeof v === 'number' ? v : 0), 0);
    return (sumMW / solarProfile.length) / 1000;
  }, [solarProfile]);
  const solarPeakGW = useMemo(() => {
    if (!Array.isArray(solarProfile) || solarProfile.length === 0) return null;
    return Math.max(...solarProfile) / 1000;
  }, [solarProfile]);
  const windAvgGW = useMemo(() => {
    if (!Array.isArray(windProfile) || windProfile.length === 0) return null;
    const sumMW = windProfile.reduce((s, v) => s + (typeof v === 'number' ? v : 0), 0);
    return (sumMW / windProfile.length) / 1000;
  }, [windProfile]);
  const windPeakGW = useMemo(() => {
    if (!Array.isArray(windProfile) || windProfile.length === 0) return null;
    return Math.max(...windProfile) / 1000;
  }, [windProfile]);

  // Utilization color scale (0 → red, 0.5 → amber, 1 → green)
  const getUtilizationColor = useCallback((u) => {
    if (typeof u !== 'number' || isNaN(u)) return '#f3f4f6';
    const clamped = Math.max(0, Math.min(1, u));
    // Simple gradient: red (#ef4444) -> amber (#f59e0b) -> green (#10b981)
    if (clamped < 0.5) {
      // interpolate red to amber
      const t = clamped / 0.5; // 0..1
      const r = Math.round(239 + (245 - 239) * t);
      const g = Math.round(68 + (158 - 68) * t);
      const b = Math.round(68 + (11 - 68) * t);
      return `rgb(${r},${g},${b})`;
    } else {
      // amber to green
      const t = (clamped - 0.5) / 0.5; // 0..1
      const r = Math.round(245 + (16 - 245) * t);
      const g = Math.round(158 + (185 - 158) * t);
      const b = Math.round(11 + (129 - 11) * t);
      return `rgb(${r},${g},${b})`;
    }
  }, []);

  // Accessor for map coloring (unmatched => light gray)
  const getSolarCellColor = useCallback((cellId) => {
    if (!solarSelectedCells || !cellId) return '#f3f4f6';
    const info = solarSelectedCells[cellId];
    if (!info) return '#f3f4f6';
    const u = info.utilization_ratio ?? info.utilization_factor ?? info.capacity_factor;
    return getUtilizationColor(u);
  }, [solarSelectedCells, getUtilizationColor]);

  const getWindCellColor = useCallback((cellId) => {
    if (!windSelectedCells || !cellId) return '#f3f4f6';
    const info = windSelectedCells[cellId];
    if (!info) return '#f3f4f6';
    const u = info.utilization_ratio ?? info.utilization_factor ?? info.capacity_factor;
    return getUtilizationColor(u);
  }, [windSelectedCells, getUtilizationColor]);

  // Fetch solar zones (shapes) for current ISO once per ISO
  useEffect(() => {
    let cancelled = false;
    const fetchZones = async () => {
      try {
        if (!countryIso) return;
        const resp = await renewablePotentialAPI.getSolarZones(countryIso);
        if (!resp?.success || !resp.data?.grid_data) return;
        const features = resp.data.grid_data
          .filter(r => r?.geometry)
          .map(r => ({
            type: 'Feature',
            properties: { grid_cell: r.grid_cell },
            geometry: r.geometry
          }));
        if (!cancelled) setSolarZonesGeoJSON({ type: 'FeatureCollection', features });
      } catch (e) {
        if (!cancelled) setSolarZonesGeoJSON(null);
      }
    };
    fetchZones();
    return () => { cancelled = true; };
  }, [countryIso]);

  // Fetch wind zones (onshore) for current ISO
  useEffect(() => {
    let cancelled = false;
    const fetchZones = async () => {
      try {
        if (!countryIso) return;
        const resp = await renewablePotentialAPI.getWindZones(countryIso, 'onshore');
        if (!resp?.success || !resp.data?.grid_data) return;
        const features = resp.data.grid_data
          .filter(r => r?.geometry)
          .map(r => ({
            type: 'Feature',
            properties: { grid_cell: r.grid_cell },
            geometry: r.geometry
          }));
        if (!cancelled) setWindZonesGeoJSON({ type: 'FeatureCollection', features });
      } catch (e) {
        if (!cancelled) setWindZonesGeoJSON(null);
      }
    };
    fetchZones();
    return () => { cancelled = true; };
  }, [countryIso]);

  // Initialize simulator map once
  useEffect(() => {
    if (!simulatorMapRef.current && typeof window !== 'undefined') {
      const el = document.getElementById('simulator-map');
      if (el) {
        const map = L.map(el, { zoomControl: true });
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
          attribution: '© OpenStreetMap contributors © CARTO',
          maxZoom: 18
        }).addTo(map);
        // Set default view; will fit to data when layer added
        map.setView([20, 0], 2);
        simulatorMapRef.current = map;
      }
    }
  }, []);

  // Initialize wind simulator map once
  useEffect(() => {
    if (!simulatorWindMapRef.current && typeof window !== 'undefined') {
      const el = document.getElementById('simulator-map-wind');
      if (el) {
        const map = L.map(el, { zoomControl: true });
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
          attribution: '© OpenStreetMap contributors © CARTO',
          maxZoom: 18
        }).addTo(map);
        map.setView([20, 0], 2);
        simulatorWindMapRef.current = map;
      }
    }
  }, []);

  // Add/update polygons layer when zones or selected cells change
  useEffect(() => {
    const map = simulatorMapRef.current;
    if (!map || !solarZonesGeoJSON) return;
    // Remove existing layer
    if (simulatorLayerRef.current) {
      map.removeLayer(simulatorLayerRef.current);
      simulatorLayerRef.current = null;
    }
    const layer = L.geoJSON(solarZonesGeoJSON, {
      style: (feature) => ({
        color: '#ffffff',
        weight: 0.4,
        fillColor: getSolarCellColor(feature?.properties?.grid_cell),
        fillOpacity: 0.7
      }),
      onEachFeature: (feature, l) => {
        const id = feature?.properties?.grid_cell;
        const info = solarSelectedCells?.[id];
        const u = info?.utilization_ratio ?? info?.utilization_factor ?? info?.capacity_factor;
        const cap = info?.capacity_mw;
        const tooltip = `Cell: ${id || 'N/A'}\nUtilization: ${typeof u==='number'?u.toFixed(2):'—'}\nCapacity: ${typeof cap==='number'?cap.toFixed(0):'—'} MW`;
        l.bindTooltip(tooltip, { sticky: true });
      }
    }).addTo(map);
    simulatorLayerRef.current = layer;
    try { map.fitBounds(layer.getBounds(), { padding: [10, 10] }); } catch {}
  }, [solarZonesGeoJSON, solarSelectedCells, getSolarCellColor]);

  // Add/update wind polygons layer
  useEffect(() => {
    const map = simulatorWindMapRef.current;
    if (!map || !windZonesGeoJSON) return;
    if (simulatorWindLayerRef.current) {
      map.removeLayer(simulatorWindLayerRef.current);
      simulatorWindLayerRef.current = null;
    }
    const layer = L.geoJSON(windZonesGeoJSON, {
      style: (feature) => ({
        color: '#ffffff',
        weight: 0.4,
        fillColor: getWindCellColor(feature?.properties?.grid_cell),
        fillOpacity: 0.7
      }),
      onEachFeature: (feature, l) => {
        const id = feature?.properties?.grid_cell;
        const info = windSelectedCells?.[id];
        const u = info?.utilization_ratio ?? info?.utilization_factor ?? info?.capacity_factor;
        const cap = info?.capacity_mw;
        const tooltip = `Cell: ${id || 'N/A'}\nUtilization: ${typeof u==='number'?u.toFixed(2):'—'}\nCapacity: ${typeof cap==='number'?cap.toFixed(0):'—'} MW`;
        l.bindTooltip(tooltip, { sticky: true });
      }
    }).addTo(map);
    simulatorWindLayerRef.current = layer;
    try { map.fitBounds(layer.getBounds(), { padding: [10, 10] }); } catch {}
  }, [windZonesGeoJSON, windSelectedCells, getWindCellColor]);
  
  // Reload handlers
  const handleReloadTimeline = async () => {
    if (!countryIso || !formData.year) return;
    await handleSubmit();
  };

  const handleReloadSolar = async () => {
    if (!countryIso || !formData.year || typeof solarCapacityGW !== 'number' || solarCapacityGW <= 0) return;
    setSolarLoading(true);
    setSolarError(null);
    // Clear current selection so the map visually resets while fetching
    setSolarSelectedCells(null);
    try {
      const solarResp = await generationProfileAPI.getSolarHourly(countryIso, formData.year, solarCapacityGW);
      if (solarResp?.success && Array.isArray(solarResp.profile)) {
        console.log('[Solar] API profile received', solarResp);
        setSolarProfile(solarResp.profile);
        setSolarSelectedCells(solarResp.selected_cells || null);
      } else {
        setSolarError('Solar profile endpoint returned no data');
        setSolarProfile(null);
        setSolarSelectedCells(null);
      }
    } catch (e) {
      setSolarError(e?.response?.data?.message || e.message || 'Failed to fetch solar profile');
      setSolarProfile(null);
    } finally {
      setSolarLoading(false);
    }
  };

  const handleReloadWind = async () => {
    if (!countryIso || !formData.year || typeof windCapacityGW !== 'number' || windCapacityGW <= 0) return;
    setWindLoading(true);
    setWindError(null);
    // Clear current selection so the map visually resets while fetching
    setWindSelectedCells(null);
    try {
      const windResp = await generationProfileAPI.getWindHourly(countryIso, formData.year, windCapacityGW);
      if (windResp?.success && Array.isArray(windResp.profile)) {
        setWindProfile(windResp.profile);
        setWindSelectedCells(windResp.selected_cells || null);
      } else {
        setWindError('Wind profile endpoint returned no data');
        setWindProfile(null);
        setWindSelectedCells(null);
      }
    } catch (e) {
      setWindError(e?.response?.data?.message || e.message || 'Failed to fetch wind profile');
      setWindProfile(null);
    } finally {
      setWindLoading(false);
    }
  };

  // Stable fetch function for capacity
  const fetchCapacityData = useCallback(async () => {
    if (!countryIso || !formData.year) return;
    
    
    setCapacityLoading(true);
    setCapacityError(null);
    
    try {
      const response = await capacityAPI.getCapacityByFuel(countryIso, formData.year);
      
      
      if (response.success) {
        
        
        // profiles from capacity API no longer used directly

        // Extract Solar capacity_gw strictly (no inference beyond key casing)
        const solarCap = response?.capacity?.Solar?.capacity_gw ?? response?.capacity?.solar?.capacity_gw;
        if (typeof solarCap === 'number' && solarCap > 0) {
          setSolarCapacityGW(solarCap);
          setSolarInputGW(solarCap.toString());
          setSolarLoading(true);
          setSolarError(null);
          try {
            const solarResp = await generationProfileAPI.getSolarHourly(countryIso, formData.year, solarCap);
            if (solarResp?.success && Array.isArray(solarResp.profile)) {
              console.log('[Solar] API profile received', {
                iso: countryIso,
                year: formData.year,
                capacityGW: solarCap,
                points: solarResp.profile.length,
                sample: solarResp.profile.slice(0, 24)
              });
              setSolarProfile(solarResp.profile);
              setSolarSelectedCells(solarResp.selected_cells || null);
            } else {
              setSolarError('Solar profile endpoint returned no data');
              setSolarProfile(null);
              setSolarSelectedCells(null);
            }
          } catch (e) {
            console.error('❌ Error fetching solar hourly profile:', e);
            setSolarError(e?.response?.data?.message || e.message || 'Failed to fetch solar profile');
            setSolarProfile(null);
          } finally {
            setSolarLoading(false);
          }
        } else {
          setSolarProfile(null);
          setSolarError('Solar capacity unavailable for selected ISO/year');
          setSolarCapacityGW(null);
          setSolarLoading(false);
        }

        // Extract Wind (onshore) capacity and fetch hourly profile
        const windCap = response?.capacity?.Windon?.capacity_gw ?? response?.capacity?.wind?.capacity_gw;
        if (typeof windCap === 'number' && windCap > 0) {
          setWindCapacityGW(windCap);
          setWindInputGW(windCap.toString());
          setWindLoading(true);
          setWindError(null);
          try {
            const windResp = await generationProfileAPI.getWindHourly(countryIso, formData.year, windCap);
            if (windResp?.success && Array.isArray(windResp.profile)) {
              setWindProfile(windResp.profile);
              setWindSelectedCells(windResp.selected_cells || null);
            } else {
              setWindError('Wind profile endpoint returned no data');
              setWindProfile(null);
              setWindSelectedCells(null);
            }
          } catch (e) {
            console.error('❌ Error fetching wind hourly profile:', e);
            setWindError(e?.response?.data?.message || e.message || 'Failed to fetch wind profile');
            setWindProfile(null);
          } finally {
            setWindLoading(false);
          }
        } else {
          setWindProfile(null);
          setWindError('Wind capacity unavailable for selected ISO/year');
          setWindCapacityGW(null);
          setWindLoading(false);
        }

        // Offshore wind temporarily disabled
      } else {
        throw new Error(response.message || 'Failed to fetch capacity data');
      }
    } catch (error) {
      console.error('❌ Error fetching capacity data:', error);
      setCapacityError(error.message);
      // Don't show toast for capacity errors as they're not critical
      
      // Stop wind/solar loaders and surface clear messages in cards
      setSolarLoading(false);
      setWindLoading(false);
      setSolarProfile(null);
      setWindProfile(null);
      setSolarError('Capacity data unavailable for selected ISO/year');
      setWindError('Capacity data unavailable for selected ISO/year');
    } finally {
      setCapacityLoading(false);
    }
  }, [countryIso, formData.year]);

  // Fetch capacity data when component mounts or country/year changes
  useEffect(() => {
    if (countryIso && formData.year) {
      fetchCapacityData();
    }
  }, [fetchCapacityData, countryIso, formData.year]);

  // Auto-generate timeline chart on initial load and when ISO/year changes
  useEffect(() => {
    if (countryIso && formData.year && !loading) {
      handleSubmit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countryIso, formData.year]);

  // Reset charts and show waiting indicators when country changes
  useEffect(() => {
    if (!countryIso) return;
    // Reset main timeline
    setChartData(null);
    setError(null);
    setLoading(true);
    // Reset capacity and profiles
    
    setCapacityError(null);
    setCapacityLoading(true);
    
    // Solar
    setSolarProfile(null);
    setSolarError(null);
    setSolarLoading(true);
    setSolarInputGW('');
    // Wind
    setWindProfile(null);
    setWindError(null);
    setWindLoading(true);
    setWindInputGW('');
  }, [countryIso]);

  

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const validateForm = () => {
    if (!countryIso) {
      toast.error('Country ISO code is required');
      return false;
    }
    
    if (formData.year < 2000 || formData.year > 2022) {
      toast.error('Year must be between 2000 and 2022');
      return false;
    }
    
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError(null);
    setChartData(null);

    try {
      const requestData = {
        isoCode: countryIso,
        year: parseInt(formData.year),
        totalGenerationTwh: null
      };

      const response = await api.post('/generation-profile', requestData);
      
      if (response.data.success) {
        setChartData(response.data.data);
        toast.success(`Profile generated successfully for ${countryIso} in ${formData.year}!`);
      } else {
        throw new Error(response.data.message || 'Failed to generate profile');
      }
    } catch (error) {
      const errorMessage = error.response?.data?.message || error.message || 'An error occurred';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Reset no longer needed; chart auto-loads on ISO/year change


  // Prepare chart data and options
  const chartOptions = useMemo(() => {
    if (!chartData || !chartData.hourlyProfile) {
      return null;
    }

    const timeData = chartData.hourlyProfile.map((value, index) => {
      const date = new Date(chartData.year, 0, 1, index % 24, 0, 0);
      date.setDate(date.getDate() + Math.floor(index / 24));
      // Convert MW to GW for display
      return [date.getTime(), value / 1000];
    });

    return {
      chart: {
        type: 'line',
        backgroundColor: 'transparent',
        style: { fontFamily: 'Inter, system-ui, sans-serif' },
        zoomType: 'xy',
        panning: { enabled: true, type: 'xy' },
        panKey: 'shift',
        // Reduce extra padding beneath plot area
        marginBottom: 20,
        marginTop: 50,
        spacingBottom: 0,
        spacingTop: 10
      },
      navigator: {
        enabled: true,
        // Make navigator more compact to avoid pushing the plot upward
        height: 28,
        margin: 6,
        outlineColor: '#CBD5E1',
        maskFill: 'rgba(99, 102, 241, 0.1)',
        series: {
          color: '#A5B4FC',
          lineWidth: 1
        }
      },
      scrollbar: {
        enabled: true,
        barBackgroundColor: '#CBD5E1',
        barBorderRadius: 4,
        buttonBackgroundColor: '#E2E8F0',
        trackBackgroundColor: '#F1F5F9'
      },
      title: { text: '' },
      xAxis: {
        type: 'datetime',
        title: { text: 'Time' },
        labels: { 
          style: { color: '#64748B' },
          rotation: -45,
          align: 'right',
          y: 20,
          formatter: function() {
            // Format the full date for tooltip
            const fullDate = Highcharts.dateFormat('%B %d, %Y %H:%M', this.value);
            // Format the display label (remove year if present)
            let displayLabel = Highcharts.dateFormat(this.dateTimeLabelFormat, this.value);
            // Remove year from display (e.g., "Jan 2022" becomes "Jan")
            displayLabel = displayLabel.replace(/\s*\d{4}$/, '');
            
            // Return HTML with title attribute for tooltip
            return `<span title="${fullDate}" style="cursor: help;">${displayLabel}</span>`;
          },
          useHTML: true
        },
        gridLineColor: '#E2E8F0',
        dateTimeLabelFormats: {
          day: '%b %d',
          week: '%b %d', 
          month: '%b',
          year: '%Y'
        }
      },
      yAxis: {
        title: { text: 'Generation (GW)' },
        labels: { style: { color: '#64748B' } },
        gridLineColor: '#E2E8F0'
      },
      rangeSelector: {
        enabled: true,
        allButtonsEnabled: true,
        selected: 5, // Default to "All" option (index 5)
        buttons: [
          {
            type: 'month',
            count: 1,
            text: '1M',
            title: 'View 1 month'
          },
          {
            type: 'month',
            count: 3,
            text: '3M',
            title: 'View 3 months'
          },
          {
            type: 'month',
            count: 6,
            text: '6M',
            title: 'View 6 months'
          },
          {
            type: 'year',
            count: 1,
            text: '1Y',
            title: 'View 1 year'
          },
          {
            type: 'all',
            text: 'All',
            title: 'View all data'
          }
        ],
        buttonTheme: {
          style: {
            fontSize: '11px',
            fontWeight: '500',
            color: '#6B7280',
            border: '1px solid #D1D5DB',
            borderRadius: '6px',
            padding: '6px 12px'
          },
          states: {
            select: {
              color: '#ffffff',
              backgroundColor: '#6366F1',
              borderColor: '#6366F1',
              fontWeight: '600'
            },
            hover: {
              color: '#1F2937',
              backgroundColor: '#F3F4F6',
              borderColor: '#9CA3AF'
            }
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        borderColor: '#E2E8F0',
        borderRadius: 8,
        shadow: true,
        formatter: function() {
          return `
            <div style="padding: 8px;">
              <div style="font-weight: 600; color: #1E293B; margin-bottom: 8px;">
                ${Highcharts.dateFormat('%B %d, %Y', this.x)}
              </div>
              <div style="font-weight: 600; color: #6366F1; font-size: 16px;">
                Generation: ${Highcharts.numberFormat(this.y, 2)} GW
              </div>
            </div>
          `;
        }
      },
      exporting: { enabled: false },
      plotOptions: {
        line: {
          color: '#6366F1',
          lineWidth: 2,
          marker: { enabled: false }
        }
      },
      series: [{
        name: 'Generation (GW)',
        data: timeData,
        type: 'line'
      }],
      legend: { enabled: false },
      credits: { enabled: false }
    };
  }, [chartData]);

  // Function to create chart options for profile charts (generation only)
  const getProfileChartOptions = (profileType, profileName, profileData) => {
    if (!profileData || !Array.isArray(profileData)) {
      return null;
    }

    // Convert hourly data (MW) to time series in GW
    const timeData = profileData.map((value, index) => {
      const year = formData.year || new Date().getFullYear();
      const date = new Date(year, 0, 1, index % 24, 0, 0);
      date.setDate(date.getDate() + Math.floor(index / 24));
      return [date.getTime(), value / 1000];
    });

    // Define colors for each profile type
    const colors = {
      solar: '#FCD34D',
      hydro: '#3B82F6',
      nuclear: '#FB923C',
      wind: '#10B981'
    };

    return {
      chart: {
        type: 'line',
        backgroundColor: 'transparent',
        style: { fontFamily: 'Inter, system-ui, sans-serif' },
        height: 250
      },
      title: { text: '' },
      xAxis: {
        type: 'datetime',
        labels: {
          style: { color: '#64748B', fontSize: '10px' },
          rotation: -45,
          formatter: function() {
            return Highcharts.dateFormat('%b', this.value); // Month name only
          }
        },
        dateTimeLabelFormats: {
          day: '%b',
          week: '%b',
          month: '%b',
          year: '%b'
        },
        gridLineColor: '#E2E8F0'
      },
      yAxis: {
        title: { text: 'GW' },
        labels: { style: { color: '#64748B', fontSize: '10px' } },
        gridLineColor: '#E2E8F0'
      },
      tooltip: {
        backgroundColor: 'rgba(255, 255, 255, 0.98)',
        borderColor: '#E2E8F0',
        borderRadius: 6,
        shadow: false,
        formatter: function() {
          const date = Highcharts.dateFormat('%b %d, %Y %H:%M', this.x);
          return `<div style="padding: 6px;"><b>${date}</b><br/>${Highcharts.numberFormat(this.y, 2)} GW</div>`;
        }
      },
      plotOptions: {
        line: {
          color: colors[profileType],
          lineWidth: 2,
          marker: { enabled: false }
        }
      },
      series: [{
        name: `${profileName} Generation (GW)`,
        data: timeData,
        type: 'line'
      }],
      legend: { enabled: false },
      credits: { enabled: false },
      rangeSelector: { enabled: false },
      navigator: { enabled: false },
      scrollbar: { enabled: false }
    };
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6">


      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6">
        {/* Left Sidebar (restored) */}
        <div className="lg:col-span-3 space-y-4 sm:space-y-6">
          {/* Parameters */}
          <div className="card p-4">
            <h3 className="font-semibold text-gray-900 mb-4">Parameters</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Year</label>
                <select
                  name="year"
                  value={formData.year}
                  onChange={handleInputChange}
                  className="input-field w-full"
                  disabled
                  aria-disabled="true"
                  title="Year selection is temporarily disabled"
                >
                  {Array.from({ length: 23 }, (_, i) => 2000 + i).map(y => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Capacity Summary */}
          <div className="card p-4">
            <h3 className="font-semibold text-gray-900 mb-4">Capacities</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Solar</span>
                <span className="font-mono text-gray-700">{typeof solarCapacityGW === 'number' ? `${solarCapacityGW.toFixed(2)} GW` : '—'}</span>
              </div>
              <div className="flex justify-between">
                <span>Wind</span>
                <span className="font-mono text-gray-700">{typeof windCapacityGW === 'number' ? `${windCapacityGW.toFixed(2)} GW` : '—'}</span>
              </div>
            </div>
          </div>

        {/* Generation Summary */}
        <div className="card p-4">
          <h3 className="font-semibold text-gray-900 mb-4">Generation (GW)</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Solar Avg</span>
              <span className="font-mono text-gray-700">{solarAvgGW !== null ? solarAvgGW.toFixed(2) : '—'}</span>
            </div>
            <div className="flex justify-between">
              <span>Solar Peak</span>
              <span className="font-mono text-gray-700">{solarPeakGW !== null ? solarPeakGW.toFixed(2) : '—'}</span>
            </div>
            <div className="flex justify-between">
              <span>Wind Avg</span>
              <span className="font-mono text-gray-700">{windAvgGW !== null ? windAvgGW.toFixed(2) : '—'}</span>
            </div>
            <div className="flex justify-between">
              <span>Wind Peak</span>
              <span className="font-mono text-gray-700">{windPeakGW !== null ? windPeakGW.toFixed(2) : '—'}</span>
            </div>
          </div>
        </div>

        </div>

        {/* Main Content Area */}
        <div className="lg:col-span-9 space-y-4 sm:space-y-6">
          {/* Top Row - Timeline Chart */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Timeline</h3>
              <button
                onClick={handleReloadTimeline}
                disabled={loading}
                className="btn-outline text-sm px-2 py-1 disabled:opacity-50"
                title="Reload timeline"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
            
            <div className="h-[420px] bg-white border border-gray-200 rounded overflow-visible">
              {loading ? (
                <div className="h-full flex items-center justify-center text-gray-400">
                  Generating chart...
                </div>
              ) : error ? (
                <div className="h-full flex items-center justify-center text-amber-600 text-sm">
                  {error}
                </div>
              ) : chartData ? (
                <HighchartsReact
                  highcharts={Highcharts}
                  options={chartOptions}
                  constructorType="stockChart"
                  containerProps={{ style: { height: '100%' } }}
                  ref={setChartRef}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-gray-400">
                  Chart will appear here
                </div>
              )}
            </div>
          </div>

          {/* Bottom Row - Profile Charts (50/50 layout) */}
          <div className="grid grid-cols-2 gap-6">
            {/* Solar Profile Chart */}
            <div className="card p-4">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900 flex items-center">
                  <Sun className="h-5 w-5 mr-2 text-yellow-500" />
                  Solar Generation{typeof solarCapacityGW === 'number' ? ` — ${solarCapacityGW.toFixed(2)} GW` : ''}
                </h3>
                <button
                  onClick={handleReloadSolar}
                  disabled={solarLoading || !(typeof solarCapacityGW === 'number' && solarCapacityGW > 0)}
                  className="btn-outline text-sm px-2 py-1 disabled:opacity-50"
                  title="Reload solar profile"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
              </div>
              <div className="mb-4 flex items-center space-x-2">
                <input
                  type="number"
                  placeholder="Enter capacity (GW)"
                  value={solarInputGW}
                  onChange={(e) => setSolarInputGW(e.target.value)}
                  min="0.1"
                  step="0.1"
                  className="input-field flex-1 text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                />
                <button
                  onClick={async () => {
                    const cap = parseFloat(solarInputGW);
                    if (!isNaN(cap) && cap > 0) {
                      setSolarLoading(true);
                      setSolarError(null);
                      try {
                        const solarResp = await generationProfileAPI.getSolarHourly(countryIso, formData.year, cap);
                        if (solarResp?.success && Array.isArray(solarResp.profile)) {
                          console.log('[Solar] API profile received', {
                            iso: countryIso,
                            year: formData.year,
                            capacityGW: cap,
                            points: solarResp.profile.length,
                            sample: solarResp.profile.slice(0, 24)
                          });
                          setSolarProfile(solarResp.profile);
                          setSolarCapacityGW(cap);
                          setSolarSelectedCells(solarResp.selected_cells || null);
                        } else {
                          setSolarError('Solar profile endpoint returned no data');
                          setSolarProfile(null);
                          setSolarSelectedCells(null);
                        }
                      } catch (e) {
                        console.error('❌ Error fetching solar hourly profile:', e);
                        setSolarError(e?.response?.data?.message || e.message || 'Failed to fetch solar profile');
                        setSolarProfile(null);
                      } finally {
                        setSolarLoading(false);
                      }
                    }
                  }}
                  disabled={!solarInputGW || parseFloat(solarInputGW) <= 0 || solarLoading}
                  className="btn-primary text-sm px-4 py-2"
                >
                  Go
                </button>
              </div>
              <div className="h-64 bg-white border border-gray-200 rounded">
                {solarLoading ? (
                  <div className="h-full flex items-center justify-center text-gray-400 text-sm">Loading solar profile...</div>
                ) : solarError ? (
                  <div className="h-full flex items-center justify-center text-amber-600 text-sm">{solarError}</div>
                ) : Array.isArray(solarProfile) ? (
                  <HighchartsReact
                    highcharts={Highcharts}
                    options={getProfileChartOptions('solar', 'Solar', solarProfile)}
                    constructorType="stockChart"
                    containerProps={{ style: { height: '100%' } }}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                    No data available
                  </div>
                )}
              </div>
            </div>

            {/* Wind (Onshore) Profile Chart */}
            <div className="card p-4">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900 flex items-center">
                  <Wind className="h-5 w-5 mr-2 text-emerald-500" />
                  Wind Generation{typeof windCapacityGW === 'number' ? ` — ${windCapacityGW.toFixed(2)} GW` : ''}
                </h3>
                <button
                  onClick={handleReloadWind}
                  disabled={windLoading || !(typeof windCapacityGW === 'number' && windCapacityGW > 0)}
                  className="btn-outline text-sm px-2 py-1 disabled:opacity-50"
                  title="Reload wind profile"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
              </div>
              <div className="mb-4 flex items-center space-x-2">
                <input
                  type="number"
                  placeholder="Enter capacity (GW)"
                  value={windInputGW}
                  onChange={(e) => setWindInputGW(e.target.value)}
                  min="0.1"
                  step="0.1"
                  className="input-field flex-1 text-sm [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                />
                <button
                  onClick={async () => {
                    const cap = parseFloat(windInputGW);
                    if (!isNaN(cap) && cap > 0) {
                      setWindLoading(true);
                      setWindError(null);
                      try {
                        const windResp = await generationProfileAPI.getWindHourly(countryIso, formData.year, cap);
                        if (windResp?.success && Array.isArray(windResp.profile)) {
                          setWindProfile(windResp.profile);
                          setWindCapacityGW(cap);
                          setWindSelectedCells(windResp.selected_cells || null);
                        } else {
                          setWindError('Wind profile endpoint returned no data');
                          setWindProfile(null);
                          setWindSelectedCells(null);
                        }
                      } catch (e) {
                        console.error('❌ Error fetching wind hourly profile:', e);
                        setWindError(e?.response?.data?.message || e.message || 'Failed to fetch wind profile');
                        setWindProfile(null);
                      } finally {
                        setWindLoading(false);
                      }
                    }
                  }}
                  disabled={!windInputGW || parseFloat(windInputGW) <= 0 || windLoading}
                  className="btn-primary text-sm px-4 py-2"
                >
                  Go
                </button>
              </div>
              <div className="h-64 bg-white border border-gray-200 rounded">
                {windLoading ? (
                  <div className="h-full flex items-center justify-center text-gray-400 text-sm">Loading wind profile...</div>
                ) : windError ? (
                  <div className="h-full flex items-center justify-center text-amber-600 text-sm">{windError}</div>
                ) : Array.isArray(windProfile) ? (
                  <HighchartsReact
                    highcharts={Highcharts}
                    options={getProfileChartOptions('wind', 'Wind', windProfile)}
                    constructorType="stockChart"
                    containerProps={{ style: { height: '100%' } }}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                    No data available
                  </div>
                )}
              </div>
            </div>

            {/* Offshore wind chart removed for now */}
          </div>

          {/* Simulator Maps (side by side) */}
            <div className="grid grid-cols-2 gap-6">
            <div className="card p-4 relative">
              <h3 className="font-semibold text-gray-900 mb-4">Simulator Map — Solar Utilization</h3>
              <div id="simulator-map" className="w-full h-[420px] rounded border border-gray-200" />
              {solarLoading && (
                <div className="absolute inset-0 bg-white/60 flex items-center justify-center rounded">
                  <div className="text-gray-600 text-sm">Loading solar map…</div>
                </div>
              )}
            </div>
            <div className="card p-4 relative">
              <h3 className="font-semibold text-gray-900 mb-4">Simulator Map — Wind Utilization</h3>
              <div id="simulator-map-wind" className="w-full h-[420px] rounded border border-gray-200" />
              {windLoading && (
                <div className="absolute inset-0 bg-white/60 flex items-center justify-center rounded">
                  <div className="text-gray-600 text-sm">Loading wind map…</div>
                </div>
              )}
            </div>
          </div>

          {/* Capacity Data Status */}
          {capacityLoading && (
            <div className="text-center text-gray-500 text-sm">
              Loading capacity data...
            </div>
          )}
          
          {capacityError && (
            <div className="text-center text-amber-600 text-sm bg-amber-50 p-2 rounded">
              ⚠️ Capacity data unavailable: {capacityError}
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-100 border border-red-300 text-red-700 px-4 py-2 rounded">
          {error}
        </div>
      )}
    </div>
  );
};

export default GenerationProfileChart;
