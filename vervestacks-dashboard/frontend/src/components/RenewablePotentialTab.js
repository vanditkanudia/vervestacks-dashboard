/**
 * RenewablePotentialTab Component
 * 
 * Main container component for renewable energy potential analysis.
 * Now refactored to use dedicated map components and custom hooks.
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  MapPin, 
  Zap, 
  TrendingUp, 
  DollarSign, 
  BarChart3,
  AlertCircle,
  Loader2
} from 'lucide-react';
import SolarMap from './SolarMap';
import WindMap from './WindMap';
import useRenewableData from '../hooks/useRenewableData';
import useMapSynchronization from '../hooks/useMapSynchronization';
import { formatNumber } from '../utils/renewableUtils';

const RenewablePotentialTab = ({ countryIso }) => {
  const [selectedZone, setSelectedZone] = useState(null);
  
  // Use custom hooks for data management and map synchronization
  const {
    solarData,
    onshoreWindData,
    offshoreWindData,
    loading,
    loadingStates,
    error,
    windErrors,
    solarThresholds,
    onshoreWindThresholds,
    offshoreWindThresholds
  } = useRenewableData(countryIso);

  const { synchronizeMaps, cleanup } = useMapSynchronization();

  // Refs for map instances
  const solarMapRef = useRef(null);
  const windMapRef = useRef(null);

  // Handle zone selection
  const handleZoneSelect = (zone) => {
    setSelectedZone(zone);
  };

  // Synchronize maps when both are ready
  useEffect(() => {
    const timer = setTimeout(() => {
      if (solarMapRef.current?.getMap && windMapRef.current?.getMap) {
        const solarMap = solarMapRef.current.getMap();
        const windMap = windMapRef.current.getMap();
        if (solarMap && windMap) {
          synchronizeMaps(solarMap, windMap);
        }
      }
    }, 2000);

    return () => {
      clearTimeout(timer);
      cleanup();
    };
  }, [synchronizeMaps, cleanup, solarData, onshoreWindData, offshoreWindData]);

  // Loading state
  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Loader2 className="h-12 w-12 animate-spin text-indigo-500 mx-auto mb-4" />
            <p className="text-gray-600">Loading solar renewable zones data...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center">
            <AlertCircle className="h-6 w-6 text-red-500 mr-3" />
            <div>
              <h3 className="text-lg font-semibold text-red-800">Unable to Load Solar Data</h3>
              <p className="text-red-600 mt-1">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // No data state
  if (!solarData || !solarData.statistics) {
    return (
      <div className="p-8">
        <div className="text-center text-gray-600">
          <MapPin className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-semibold mb-2">No Solar Data Available</h3>
          <p>No solar renewable zones data found for {countryIso}.</p>
        </div>
      </div>
    );
  }

  const { statistics } = solarData;

  // ChartCard wrapper component (matching Overview tab style)
  const ChartCard = ({ title, subtitle, children, icon, showHeader = true }) => (
    <div className="bg-white rounded-lg hover:shadow-sm transition-shadow">
      {showHeader && (
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="text-base font-semibold text-gray-900 mb-1">{title}</h3>
            <p className="text-xs text-gray-600">{subtitle}</p>
          </div>
          {icon && (
            <div className="text-gray-400 hover:text-gray-600 cursor-pointer">
              {icon}
            </div>
          )}
        </div>
      )}
      <div className="chart-container">
        {children}
      </div>
    </div>
  );

  return (
    <div className="px-4 sm:px-6 py-4 sm:py-6">
      {/* Main Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4 mb-3 sm:mb-4">
        {/* Solar Card */}
        <ChartCard 
          title="Solar Energy Potential"
          subtitle=""
          icon={<Zap className="h-5 w-5" />}
          showHeader={true}
        >
          <div className="h-96 relative bg-gray-100">
            <SolarMap
              ref={solarMapRef}
              solarData={solarData}
              solarThresholds={solarThresholds}
              selectedZone={selectedZone}
              onZoneSelect={handleZoneSelect}
              countryIso={countryIso}
              className="w-full h-full"
            />
            

            {/* Legend Overlay */}
            <div className="absolute bottom-4 right-4 bg-white border border-gray-200 rounded-lg p-3 shadow-lg max-w-xs" style={{ zIndex: 1000 }}>
              {solarThresholds && (
                <div className="space-y-1">
                  <div className="text-xs font-semibold text-gray-700 mb-2 border-b border-gray-200 pb-1">
                    ☀️ Solar Capacity Factor
                  </div>
                  <div className="flex items-center text-xs">
                    <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: solarThresholds.excellent.color }}></div>
                    <span>Excellent: {(solarThresholds.excellent.threshold * 100).toFixed(1)}%+</span>
                  </div>
                  <div className="flex items-center text-xs">
                    <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: solarThresholds.high.color }}></div>
                    <span>High: {(solarThresholds.high.threshold * 100).toFixed(1)}-{(solarThresholds.excellent.threshold * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex items-center text-xs">
                    <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: solarThresholds.good.color }}></div>
                    <span>Good: {(solarThresholds.good.threshold * 100).toFixed(1)}-{(solarThresholds.high.threshold * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex items-center text-xs">
                    <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: solarThresholds.fair.color }}></div>
                    <span>Fair: {(solarThresholds.fair.threshold * 100).toFixed(1)}-{(solarThresholds.good.threshold * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex items-center text-xs">
                    <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: solarThresholds.poor.color }}></div>
                    <span>Poor: &lt;{(solarThresholds.fair.threshold * 100).toFixed(1)}%</span>
                  </div>
                </div>
              )}
              {!solarThresholds && (
                <div className="text-xs text-gray-600">
                  <span>Calculating thresholds...</span>
                </div>
              )}
            </div>
          </div>

          {/* Solar Statistics */}
          <div className="mt-3 sm:mt-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
              <div className="bg-gray-50 rounded p-2">
                <div className="flex items-center">
                  <MapPin className="h-4 w-4 text-gray-600 mr-2" />
                  <div>
                    <p className="text-xs text-gray-600">Zones</p>
                    <p className="text-sm font-bold">{statistics.total_cells.toLocaleString()}</p>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 rounded p-2">
                <div className="flex items-center">
                  <Zap className="h-4 w-4 text-gray-600 mr-2" />
                  <div>
                    <p className="text-xs text-gray-600">Capacity</p>
                    <p className="text-sm font-bold">{formatNumber(statistics.total_capacity_mw)} MW</p>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 rounded p-2">
                <div className="flex items-center">
                  <TrendingUp className="h-4 w-4 text-gray-600 mr-2" />
                  <div>
                    <p className="text-xs text-gray-600">Avg CF</p>
                    <p className="text-sm font-bold">{(statistics.avg_capacity_factor * 100).toFixed(1)}%</p>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 rounded p-2">
                <div className="flex items-center">
                  <DollarSign className="h-4 w-4 text-gray-600 mr-2" />
                  <div>
                    <p className="text-xs text-gray-600">Avg LCOE</p>
                    <p className="text-sm font-bold">${statistics.avg_lcoe.toFixed(0)}/MWh</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="text-xs text-gray-600 flex justify-between">
              <span>Area: {statistics.total_suitable_area_km2.toLocaleString()} km² ({solarData.grid_data.length.toLocaleString()} zones)</span>
              <span>Generation: {formatNumber(statistics.total_generation_gwh)} GWh</span>
              {statistics.cost_data_available && (
                <span>Cost: ${statistics.investment_cost_usd_kw}/kW</span>
              )}
            </div>
          </div>
        </ChartCard>

        {/* Wind Card */}
        <ChartCard 
          title="Wind Energy Potential"
          subtitle=""
          icon={<Zap className="h-5 w-5" />}
          showHeader={true}
        >
          <div className="h-96 relative bg-gray-100">
            <WindMap
              ref={windMapRef}
              onshoreWindData={onshoreWindData}
              offshoreWindData={offshoreWindData}
              onshoreWindThresholds={onshoreWindThresholds}
              offshoreWindThresholds={offshoreWindThresholds}
              selectedZone={selectedZone}
              onZoneSelect={handleZoneSelect}
              countryIso={countryIso}
              className="w-full h-full"
            />
            
            {/* Loading Overlay */}
            {(loadingStates.onshore || loadingStates.offshore) && (
              <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center" style={{ zIndex: 1000 }}>
                <div className="text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mx-auto mb-2" />
                  <div className="text-sm text-gray-600">
                    {loadingStates.onshore && <div>Loading onshore wind data...</div>}
                    {loadingStates.offshore && <div>Loading offshore wind data...</div>}
                  </div>
                </div>
              </div>
            )}

            {/* Error Messages */}
            {(windErrors.onshore || windErrors.offshore) && (
              <div className="absolute top-4 left-4 bg-yellow-50 border border-yellow-200 rounded-lg p-2 shadow-lg max-w-xs" style={{ zIndex: 1000 }}>
                <div className="text-xs text-yellow-800">
                  {windErrors.onshore && <div>⚠️ Onshore wind: {windErrors.onshore}</div>}
                  {windErrors.offshore && <div>⚠️ Offshore wind: {windErrors.offshore}</div>}
                </div>
              </div>
            )}

            {/* Dual Legend Overlay */}
            {(onshoreWindData || offshoreWindData) && (
              <div className="absolute bottom-4 right-4 bg-white border border-gray-200 rounded-lg p-3 shadow-lg max-w-xs" style={{ zIndex: 1000 }}>
                <div className="space-y-2">
                  {/* Onshore Wind Legend */}
                  {onshoreWindData && onshoreWindThresholds && (
                    <div>
                      <div className="text-xs font-semibold text-gray-700 mb-1 border-b border-gray-200 pb-1">
                        🌬️ Onshore Wind
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: onshoreWindThresholds.excellent.color }}></div>
                          <span>Excellent: {(onshoreWindThresholds.excellent.threshold * 100).toFixed(1)}%+</span>
                        </div>
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: onshoreWindThresholds.high.color }}></div>
                          <span>High: {(onshoreWindThresholds.high.threshold * 100).toFixed(1)}-{(onshoreWindThresholds.excellent.threshold * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: onshoreWindThresholds.good.color }}></div>
                          <span>Good: {(onshoreWindThresholds.good.threshold * 100).toFixed(1)}-{(onshoreWindThresholds.high.threshold * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: onshoreWindThresholds.fair.color }}></div>
                          <span>Fair: {(onshoreWindThresholds.fair.threshold * 100).toFixed(1)}-{(onshoreWindThresholds.good.threshold * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: onshoreWindThresholds.poor.color }}></div>
                          <span>Poor: &lt;{(onshoreWindThresholds.fair.threshold * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* Offshore Wind Legend */}
                  {offshoreWindData && offshoreWindThresholds && (
                    <div>
                      <div className="text-xs font-semibold text-gray-700 mb-1 border-b border-gray-200 pb-1">
                        🌊 Offshore Wind
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: offshoreWindThresholds.excellent.color }}></div>
                          <span>Excellent: {(offshoreWindThresholds.excellent.threshold * 100).toFixed(1)}%+</span>
                        </div>
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: offshoreWindThresholds.high.color }}></div>
                          <span>High: {(offshoreWindThresholds.high.threshold * 100).toFixed(1)}-{(offshoreWindThresholds.excellent.threshold * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: offshoreWindThresholds.good.color }}></div>
                          <span>Good: {(offshoreWindThresholds.good.threshold * 100).toFixed(1)}-{(offshoreWindThresholds.high.threshold * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: offshoreWindThresholds.fair.color }}></div>
                          <span>Fair: {(offshoreWindThresholds.fair.threshold * 100).toFixed(1)}-{(offshoreWindThresholds.good.threshold * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex items-center text-xs">
                          <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: offshoreWindThresholds.poor.color }}></div>
                          <span>Poor: &lt;{(offshoreWindThresholds.fair.threshold * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* Loading state for wind legends */}
                  {((onshoreWindData && !onshoreWindThresholds) || (offshoreWindData && !offshoreWindThresholds)) && (
                    <div className="text-xs text-gray-600">
                      <span>Calculating wind thresholds...</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Wind Statistics */}
          {(onshoreWindData || offshoreWindData) && (
            <div className="mt-3 sm:mt-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
                <div className="bg-gray-50 rounded p-2">
                  <div className="flex items-center">
                    <MapPin className="h-4 w-4 text-gray-600 mr-2" />
                    <div>
                      <p className="text-xs text-gray-600">Zones</p>
                      <p className="text-sm font-bold">
                        {(() => {
                          const onshoreZones = onshoreWindData?.statistics?.total_cells || 0;
                          const offshoreZones = offshoreWindData?.statistics?.total_cells || 0;
                          const totalZones = onshoreZones + offshoreZones;
                          
                          if (onshoreZones > 0 && offshoreZones > 0) {
                            return (
                              <span>
                                <span className="text-green-600">{onshoreZones.toLocaleString()}</span> + 
                                <span className="text-blue-600"> {offshoreZones.toLocaleString()}</span> = {totalZones.toLocaleString()}
                              </span>
                            );
                          } else if (onshoreZones > 0) {
                            return <span className="text-green-600">{onshoreZones.toLocaleString()}</span>;
                          } else if (offshoreZones > 0) {
                            return <span className="text-blue-600">{offshoreZones.toLocaleString()}</span>;
                          } else {
                            return '0';
                          }
                        })()}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 rounded p-2">
                  <div className="flex items-center">
                    <Zap className="h-4 w-4 text-gray-600 mr-2" />
                    <div>
                      <p className="text-xs text-gray-600">Capacity</p>
                      <p className="text-sm font-bold">
                        {(() => {
                          const onshoreCapacity = onshoreWindData?.statistics?.total_capacity_mw || 0;
                          const offshoreCapacity = offshoreWindData?.statistics?.total_capacity_mw || 0;
                          const totalCapacity = onshoreCapacity + offshoreCapacity;
                          
                          if (onshoreCapacity > 0 && offshoreCapacity > 0) {
                            return (
                              <span>
                                <span className="text-green-600">{formatNumber(onshoreCapacity)}</span> + 
                                <span className="text-blue-600"> {formatNumber(offshoreCapacity)}</span> = {formatNumber(totalCapacity)} MW
                              </span>
                            );
                          } else if (onshoreCapacity > 0) {
                            return <span className="text-green-600">{formatNumber(onshoreCapacity)} MW</span>;
                          } else if (offshoreCapacity > 0) {
                            return <span className="text-blue-600">{formatNumber(offshoreCapacity)} MW</span>;
                          } else {
                            return '0 MW';
                          }
                        })()}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 rounded p-2">
                  <div className="flex items-center">
                    <TrendingUp className="h-4 w-4 text-gray-600 mr-2" />
                    <div>
                      <p className="text-xs text-gray-600">Avg CF</p>
                      <p className="text-sm font-bold">
                        {(() => {
                          const onshoreCF = onshoreWindData?.statistics?.avg_capacity_factor || 0;
                          const offshoreCF = offshoreWindData?.statistics?.avg_capacity_factor || 0;
                          const onshoreWeight = onshoreWindData?.statistics?.total_cells || 0;
                          const offshoreWeight = offshoreWindData?.statistics?.total_cells || 0;
                          const totalWeight = onshoreWeight + offshoreWeight;
                          
                          if (onshoreCF > 0 && offshoreCF > 0) {
                            const weightedAvg = ((onshoreCF * onshoreWeight) + (offshoreCF * offshoreWeight)) / totalWeight;
                            return (
                              <span>
                                <span className="text-green-600">{(onshoreCF * 100).toFixed(1)}%</span> + 
                                <span className="text-blue-600"> {(offshoreCF * 100).toFixed(1)}%</span> = {(weightedAvg * 100).toFixed(1)}%
                              </span>
                            );
                          } else if (onshoreCF > 0) {
                            return <span className="text-green-600">{(onshoreCF * 100).toFixed(1)}%</span>;
                          } else if (offshoreCF > 0) {
                            return <span className="text-blue-600">{(offshoreCF * 100).toFixed(1)}%</span>;
                          } else {
                            return '0.0%';
                          }
                        })()}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 rounded p-2">
                  <div className="flex items-center">
                    <DollarSign className="h-4 w-4 text-gray-600 mr-2" />
                    <div>
                      <p className="text-xs text-gray-600">Avg LCOE</p>
                      <p className="text-sm font-bold">
                        {(() => {
                          const onshoreLCOE = onshoreWindData?.statistics?.avg_lcoe || 0;
                          const offshoreLCOE = offshoreWindData?.statistics?.avg_lcoe || 0;
                          const onshoreWeight = onshoreWindData?.statistics?.total_cells || 0;
                          const offshoreWeight = offshoreWindData?.statistics?.total_cells || 0;
                          const totalWeight = onshoreWeight + offshoreWeight;
                          
                          if (onshoreLCOE > 0 && offshoreLCOE > 0) {
                            const weightedAvg = ((onshoreLCOE * onshoreWeight) + (offshoreLCOE * offshoreWeight)) / totalWeight;
                            return (
                              <span>
                                <span className="text-green-600">${onshoreLCOE.toFixed(0)}</span> + 
                                <span className="text-blue-600"> ${offshoreLCOE.toFixed(0)}</span> = ${weightedAvg.toFixed(0)}/MWh
                              </span>
                            );
                          } else if (onshoreLCOE > 0) {
                            return <span className="text-green-600">${onshoreLCOE.toFixed(0)}/MWh</span>;
                          } else if (offshoreLCOE > 0) {
                            return <span className="text-blue-600">${offshoreLCOE.toFixed(0)}/MWh</span>;
                          } else {
                            return '$0/MWh';
                          }
                        })()}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="text-xs text-gray-600 flex justify-between">
                <span>
                  Area: {((onshoreWindData?.statistics?.total_suitable_area_km2 || 0) + (offshoreWindData?.statistics?.total_suitable_area_km2 || 0)).toLocaleString()} km² 
                  ({((onshoreWindData?.grid_data?.length || 0) + (offshoreWindData?.grid_data?.length || 0)).toLocaleString()} zones)
                </span>
                <span>
                  Generation: {formatNumber((onshoreWindData?.statistics?.total_generation_gwh || 0) + (offshoreWindData?.statistics?.total_generation_gwh || 0))} GWh
                </span>
                {((onshoreWindData?.statistics?.cost_data_available) || (offshoreWindData?.statistics?.cost_data_available)) && (
                  <span>
                    Cost: ${(() => {
                      const onshoreCost = onshoreWindData?.statistics?.investment_cost_usd_kw || 0;
                      const offshoreCost = offshoreWindData?.statistics?.investment_cost_usd_kw || 0;
                      const onshoreWeight = onshoreWindData?.statistics?.total_cells || 0;
                      const offshoreWeight = offshoreWindData?.statistics?.total_cells || 0;
                      const totalWeight = onshoreWeight + offshoreWeight;
                      if (totalWeight === 0) return '0';
                      const weightedAvg = ((onshoreCost * onshoreWeight) + (offshoreCost * offshoreWeight)) / totalWeight;
                      return weightedAvg.toFixed(0);
                    })()}/kW
                  </span>
                )}
              </div>
            </div>
          )}
        </ChartCard>
      </div>
    </div>
  );
};

export default RenewablePotentialTab;