/**
 * Custom Hook for Renewable Energy Data Management
 * 
 * This hook handles fetching, processing, and state management for
 * renewable energy data including solar, onshore wind, and offshore wind.
 */

import { useState, useEffect, useCallback } from 'react';
import { renewablePotentialAPI } from '../services/api';
import { calculatePercentileThresholds } from '../utils/renewableUtils';
import toast from 'react-hot-toast';

export const useRenewableData = (countryIso) => {
  const [solarData, setSolarData] = useState(null);
  const [onshoreWindData, setOnshoreWindData] = useState(null);
  const [offshoreWindData, setOffshoreWindData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [loadingStates, setLoadingStates] = useState({
    onshore: false,
    offshore: false
  });
  const [windErrors, setWindErrors] = useState({
    onshore: null,
    offshore: null
  });

  // Thresholds for different renewable types
  const [solarThresholds, setSolarThresholds] = useState(null);
  const [onshoreWindThresholds, setOnshoreWindThresholds] = useState(null);
  const [offshoreWindThresholds, setOffshoreWindThresholds] = useState(null);
  
  // Separate loading states for data vs thresholds
  const [solarDataLoading, setSolarDataLoading] = useState(true);
  const [solarThresholdsLoading, setSolarThresholdsLoading] = useState(false);
  const [windDataLoading, setWindDataLoading] = useState(true);
  const [windThresholdsLoading, setWindThresholdsLoading] = useState(false);

  const loadSolarData = useCallback(async () => {
    try {
      setLoading(true);
      setSolarDataLoading(true);
      setError(null);
      
      const response = await renewablePotentialAPI.getSolarZones(countryIso);
      
      if (response.success) {
        setSolarData(response.data);
      } else {
        console.error('Solar data loading failed:', response.error);
        setError(response.error || 'Failed to load solar renewable zones data');
      }
    } catch (err) {
      console.error('Error loading solar data:', err);
      setError('Failed to load solar renewable zones data');
      toast.error('Failed to load solar renewable zones data');
    } finally {
      setLoading(false);
      setSolarDataLoading(false);
    }
  }, [countryIso]);

  const loadOnshoreWindData = useCallback(async () => {
    try {
      setLoadingStates(prev => ({ ...prev, onshore: true }));
      setWindErrors(prev => ({ ...prev, onshore: null }));
      
      const response = await renewablePotentialAPI.getWindZones(countryIso, 'onshore');
      
      if (response.success) {
        setOnshoreWindData(response.data);
      } else {
        console.warn('Failed to load onshore wind data:', response.error);
        setWindErrors(prev => ({ ...prev, onshore: response.error }));
        setOnshoreWindData(null);
      }
    } catch (err) {
      console.warn('Error loading onshore wind data:', err);
      setWindErrors(prev => ({ ...prev, onshore: 'Failed to load onshore wind data' }));
      setOnshoreWindData(null);
    } finally {
      setLoadingStates(prev => ({ ...prev, onshore: false }));
    }
  }, [countryIso]);

  const loadOffshoreWindData = useCallback(async () => {
    try {
      setLoadingStates(prev => ({ ...prev, offshore: true }));
      setWindErrors(prev => ({ ...prev, offshore: null }));
      
      const response = await renewablePotentialAPI.getWindZones(countryIso, 'offshore');
      
      if (response.success) {
        setOffshoreWindData(response.data);
      } else {
        console.warn('Failed to load offshore wind data:', response.error);
        setWindErrors(prev => ({ ...prev, offshore: response.error }));
        setOffshoreWindData(null);
      }
    } catch (err) {
      console.warn('Error loading offshore wind data:', err);
      setWindErrors(prev => ({ ...prev, offshore: 'Failed to load offshore wind data' }));
      setOffshoreWindData(null);
    } finally {
      setLoadingStates(prev => ({ ...prev, offshore: false }));
    }
  }, [countryIso]);
  
  // Track wind data loading - set to false when both onshore and offshore are done
  useEffect(() => {
    if (!loadingStates.onshore && !loadingStates.offshore) {
      setWindDataLoading(false);
    } else {
      setWindDataLoading(true);
    }
  }, [loadingStates.onshore, loadingStates.offshore]);

  // Load solar data on mount
  useEffect(() => {
    loadSolarData();
  }, [loadSolarData]);

  // Load wind data on mount
  useEffect(() => {
    loadOnshoreWindData();
    loadOffshoreWindData();
  }, [loadOnshoreWindData, loadOffshoreWindData]);

  // Calculate thresholds when data loads
  useEffect(() => {
    if (solarData?.grid_data?.length > 0) {
      setSolarThresholdsLoading(true);
      try {
        const capacityFactors = solarData.grid_data.map(zone => zone['Capacity Factor']);
        const thresholds = calculatePercentileThresholds(capacityFactors, 'solar');
        setSolarThresholds(thresholds);
      } catch (err) {
        console.error('Error calculating solar thresholds:', err);
        setError('Failed to calculate solar thresholds');
      } finally {
        setSolarThresholdsLoading(false);
      }
    } else {
      setSolarThresholds(null);
      setSolarThresholdsLoading(false);
    }
  }, [solarData]);

  useEffect(() => {
    if (onshoreWindData?.grid_data?.length > 0) {
      try {
        const capacityFactors = onshoreWindData.grid_data.map(zone => zone['Capacity Factor']);
        const thresholds = calculatePercentileThresholds(capacityFactors, 'onshore_wind');
        setOnshoreWindThresholds(thresholds);
      } catch (err) {
        console.error('Error calculating onshore wind thresholds:', err);
        setWindErrors(prev => ({ ...prev, onshore: 'Failed to calculate onshore wind thresholds' }));
        setOnshoreWindThresholds(null);
      }
    } else {
      setOnshoreWindThresholds(null);
    }
  }, [onshoreWindData]);

  useEffect(() => {
    if (offshoreWindData?.grid_data?.length > 0) {
      try {
        const capacityFactors = offshoreWindData.grid_data.map(zone => zone['Capacity Factor']);
        const thresholds = calculatePercentileThresholds(capacityFactors, 'offshore_wind');
        setOffshoreWindThresholds(thresholds);
      } catch (err) {
        console.error('Error calculating offshore wind thresholds:', err);
        setWindErrors(prev => ({ ...prev, offshore: 'Failed to calculate offshore wind thresholds' }));
        setOffshoreWindThresholds(null);
      }
    } else {
      setOffshoreWindThresholds(null);
    }
  }, [offshoreWindData]);
  
  // Track wind thresholds loading - set to false when both are calculated (or determined to not exist)
  useEffect(() => {
    const onshoreReady = onshoreWindData ? (onshoreWindData.grid_data?.length > 0 ? onshoreWindThresholds !== null : true) : true;
    const offshoreReady = offshoreWindData ? (offshoreWindData.grid_data?.length > 0 ? offshoreWindThresholds !== null : true) : true;
    
    if (onshoreReady && offshoreReady) {
      setWindThresholdsLoading(false);
    } else {
      setWindThresholdsLoading(true);
    }
  }, [onshoreWindData, offshoreWindData, onshoreWindThresholds, offshoreWindThresholds]);

  // Calculate ready states
  const solarLayerReady = solarData && solarThresholds;
  const windLayerReady = (onshoreWindData && onshoreWindThresholds) || 
                         (offshoreWindData && offshoreWindThresholds);
  const isSolarLoading = solarDataLoading || solarThresholdsLoading;
  const isWindLoading = windDataLoading || windThresholdsLoading;

  return {
    // Data
    solarData,
    onshoreWindData,
    offshoreWindData,
    
    // Loading states
    loading,
    loadingStates,
    solarDataLoading,
    solarThresholdsLoading,
    windDataLoading,
    windThresholdsLoading,
    isSolarLoading,
    isWindLoading,
    solarLayerReady,
    windLayerReady,
    
    // Error states
    error,
    windErrors,
    
    // Thresholds
    solarThresholds,
    onshoreWindThresholds,
    offshoreWindThresholds,
    
    // Actions
    loadSolarData,
    loadOnshoreWindData,
    loadOffshoreWindData
  };
};

export default useRenewableData;
