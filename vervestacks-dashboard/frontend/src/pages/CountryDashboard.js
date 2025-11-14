import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  MapPin,
  Database,
  Zap,
  Activity,
  DollarSign,
  ChevronDown,
  Maximize2,
  ArrowLeft,
  Search
} from 'lucide-react';
import * as Flags from 'country-flag-icons/react/3x2';
import { countriesAPI, energyMetricsAPI } from '../services/api';
import toast from 'react-hot-toast';
import GenerationChart from '../components/Charts/GenerationChart';
import CapacityChart from '../components/Charts/CapacityChart';
import UtilizationFactorChart from '../components/Charts/UtilizationFactorChart';
import CO2IntensityChart from '../components/Charts/CO2IntensityChart';
import PlantAgeHistogram from '../components/Charts/PlantAgeHistogram';
import PlantSizeHistogram from '../components/Charts/PlantSizeHistogram';
import GenerationProfileChart from '../components/GenerationProfileChart';
import RenewablePotentialTab from '../components/RenewablePotentialTab';
import TransmissionLineTab from '../components/TransmissionLineTab';
import AR6ScenarioChart from '../components/Charts/AR6ScenarioChart';

const CountryDashboard = () => {
  const { isoCode } = useParams();
  const navigate = useNavigate();
  const [country, setCountry] = useState(null);
  const [countries, setCountries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [existingStockData, setExistingStockData] = useState(null);
  const [existingStockLoading, setExistingStockLoading] = useState(false);
  const [existingStockError, setExistingStockError] = useState(null);
  const [showHourlySimulator, setShowHourlySimulator] = useState(false);
  const [showCountryDropdown, setShowCountryDropdown] = useState(false);
  const [countrySearchTerm, setCountrySearchTerm] = useState('');
  const [githubLinks, setGithubLinks] = useState({ type: 'single', url: 'https://github.com/akanudia/vervestacks_models/tree/main' });
  const [showGithubDropdown, setShowGithubDropdown] = useState(false);
  const dropdownRef = useRef(null);
  const githubDropdownRef = useRef(null);
  const globalHeaderRef = useRef(null);
  const countryHeaderRef = useRef(null);
  const tabNavigationRef = useRef(null);
  const [chartHeight, setChartHeight] = useState(400); // Default height

  const loadCountryData = useCallback(async () => {
    try {
      const data = await countriesAPI.getByIso(isoCode);
      setCountry(data.country);
    } catch (error) {
      toast.error(`Failed to load data for ${isoCode}`);
      console.error('Error loading country:', error);
    } finally {
      setLoading(false);
    }
  }, [isoCode]);

  const loadCountriesList = useCallback(async () => {
    try {
      const data = await countriesAPI.getAll();
      setCountries(data.countries || []);
    } catch (error) {
      console.error('Error loading countries list:', error);
    }
  }, []);

  const loadExistingStockData = useCallback(async (countryIso) => {
    if (!countryIso) return;
    
    try {
      setExistingStockLoading(true);
      setExistingStockError(null);
      const response = await energyMetricsAPI.getExistingStockMetrics(countryIso);
      
      if (response && response.success && response.data) {
        setExistingStockData(response.data);
      } else {
        throw new Error('Failed to load existing stock data');
      }
    } catch (error) {
      setExistingStockError(error.message);
      toast.error('Failed to load existing stock data');
      console.error('Error loading existing stock data:', error);
    } finally {
      setExistingStockLoading(false);
    }
  }, []);

  // Load country data when isoCode changes
  useEffect(() => {
    loadCountryData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isoCode]);

  // Load countries list only once on mount
  useEffect(() => {
    if (countries.length === 0) {
      loadCountriesList();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load existing stock data when the existing-stock tab is active or country changes
  useEffect(() => {
    if (activeTab === 'existing-stock' && country && country.iso_code) {
      loadExistingStockData(country.iso_code);
    }
  }, [activeTab, country, loadExistingStockData]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowCountryDropdown(false);
        setCountrySearchTerm('');
      }
    };

    if (showCountryDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showCountryDropdown]);

  // Close GitHub dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (githubDropdownRef.current && !githubDropdownRef.current.contains(event.target)) {
        setShowGithubDropdown(false);
      }
    };

    if (showGithubDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showGithubDropdown]);

  // Determine GitHub links based on available branches
  useEffect(() => {
    const resolveGithubLinks = async () => {
      const iso = (country?.iso_code || isoCode || '').toUpperCase();
      if (!iso) {
        setGithubLinks({ type: 'single', url: 'https://github.com/akanudia/vervestacks_models/tree/main' });
        return;
      }

      const branches = [iso, `${iso}_grids`, `${iso}_grids_syn_5`];
      const checkBranch = async (branch) => {
        try {
          const resp = await fetch(`https://api.github.com/repos/akanudia/vervestacks_models/branches/${branch}`);
          return resp.ok;
        } catch (e) {
          return false;
        }
      };

      try {
        const results = await Promise.all(branches.map(b => checkBranch(b)));
        const available = branches.filter((b, i) => results[i]);
        if (available.length >= 2) {
          setGithubLinks({
            type: 'multiple',
            items: available.map(b => ({ name: b, url: `https://github.com/akanudia/vervestacks_models/tree/${b}` }))
          });
        } else if (available.length === 1) {
          setGithubLinks({ type: 'single', url: `https://github.com/akanudia/vervestacks_models/tree/${available[0]}` });
        } else {
          setGithubLinks({ type: 'single', url: 'https://github.com/akanudia/vervestacks_models/tree/main' });
        }
      } catch (e) {
        setGithubLinks({ type: 'single', url: 'https://github.com/akanudia/vervestacks_models/tree/main' });
      }
    };

    resolveGithubLinks();
  }, [country?.iso_code, isoCode]);

  // Calculate chart height for Overview tab (desktop only)
  useEffect(() => {
    const calculateChartHeight = () => {
      // Only apply on desktop (lg breakpoint: 1024px)
      if (window.innerWidth < 1024) {
        setChartHeight(400); // Default height for mobile
        return;
      }

      // Only calculate when Overview tab is active
      if (activeTab !== 'overview' || showHourlySimulator) {
        return;
      }

      const globalHeader = globalHeaderRef.current;
      const countryHeader = countryHeaderRef.current;
      const tabNavigation = tabNavigationRef.current;

      if (!globalHeader || !countryHeader || !tabNavigation) {
        return;
      }

      const viewportHeight = window.innerHeight;
      const globalHeaderHeight = globalHeader.offsetHeight;
      const countryHeaderHeight = countryHeader.offsetHeight;
      const tabNavHeight = tabNavigation.offsetHeight;
      
      // Account for all spacing more precisely:
      // - Overview tab container padding: py-6 = 24px top + 24px bottom = 48px
      // - Gap between grid rows: gap-4 = 16px
      // - ChartCard padding per chart: p-6 = 24px top + 24px bottom = 48px
      //   We have 2 rows, so 2 * 48px = 96px for chart padding
      // - Minimal buffer for safety: 5px (minimal for smaller screens)
      const paddingAndGaps = 48 + 16 + 96 + 5; // 165px total
      
      const availableHeight = viewportHeight - globalHeaderHeight - countryHeaderHeight - tabNavHeight - paddingAndGaps;
      
      // Divide by 2 for 2 rows
      // For smaller screens (height < 1080), use lower minimum (200px)
      // For larger screens, use 250px minimum
      const minHeight = viewportHeight < 1080 ? 200 : 250;
      const calculatedHeight = Math.max(minHeight, Math.floor(availableHeight / 2));
      
      setChartHeight(calculatedHeight);
    };

    // Calculate on mount and when dependencies change
    calculateChartHeight();

    // Recalculate on window resize
    window.addEventListener('resize', calculateChartHeight);
    return () => window.removeEventListener('resize', calculateChartHeight);
  }, [activeTab, showHourlySimulator, country]);


    // Helper function to get country flag (memoized)
  const getCountryFlag = useCallback((countryData) => {
    if (!countryData?.iso2_code) {
      return (
        <div className="w-6 h-4 bg-gray-200 rounded-sm flex items-center justify-center">
          <span className="text-xs text-gray-500 font-mono">{countryData?.iso_code || '??'}</span>
        </div>
      );
    }
    
    const FlagComponent = Flags[countryData.iso2_code];
    if (FlagComponent) {
      return <FlagComponent className="w-6 h-4 rounded-sm shadow-sm" />;
    }
    
    return (
      <div className="w-6 h-4 bg-gray-200 rounded-sm flex items-center justify-center">
        <span className="text-xs text-gray-500 font-mono">{countryData.iso_code}</span>
      </div>
    );
  }, []);

  // Handle country selection from dropdown
  const handleCountrySelect = useCallback((selectedCountry) => {
    setShowCountryDropdown(false);
    setCountrySearchTerm('');
    navigate(`/country/${selectedCountry.iso_code}`);
  }, [navigate]);

  // Handle search input change
  const handleSearchChange = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setCountrySearchTerm(e.target.value);
  }, []);

  // Filter countries based on search term (memoized to prevent re-renders)
  const filteredCountries = useMemo(() => {
    return countries.filter(c => 
      c.name?.toLowerCase().includes(countrySearchTerm.toLowerCase()) ||
      c.iso_code?.toLowerCase().includes(countrySearchTerm.toLowerCase()) ||
      c.iso2_code?.toLowerCase().includes(countrySearchTerm.toLowerCase())
    );
  }, [countries, countrySearchTerm]);

  const tabs = useMemo(() => [
    { id: 'overview', name: 'Overview', icon: <MapPin className="h-4 w-4" /> },
    { id: 'existing-stock', name: 'Existing Stock', icon: <Database className="h-4 w-4" /> },
    { id: 'renewable-potential', name: 'Renewable Potential', icon: <Zap className="h-4 w-4" /> },
    { id: 'transmission-line', name: 'Transmission Lines', icon: <Activity className="h-4 w-4" /> },
    { id: 'demand-fuel-price', name: 'Demand and Fuel Price Evolution', icon: <DollarSign className="h-4 w-4" /> },
    { id: 'results', name: 'Results', icon: <Database className="h-4 w-4" /> },
    { id: 'what-vervestacks', name: `What VERVESTACKS can do for ${country?.name || 'Japan'}`, icon: <Zap className="h-4 w-4" /> },
  ], [country?.name]);

  // ChartCard wrapper component
  const ChartCard = useCallback(({ title, subtitle, children, icon, showHeader = true }) => (
    <div className="bg-white rounded-lg sm:rounded-xl shadow-card p-4 sm:p-6 hover:shadow-card-hover transition-shadow">
      {showHeader && (
        <div className="flex justify-between items-start mb-3 sm:mb-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-1 truncate">{title}</h3>
            <p className="text-xs sm:text-sm text-gray-600 line-clamp-2">{subtitle}</p>
          </div>
          {icon && (
            <div className="text-gray-400 hover:text-gray-600 cursor-pointer ml-2 flex-shrink-0">
              {icon}
        </div>
          )}
      </div>
      )}
      <div className="chart-container">
        {children}
        </div>
      </div>
  ), []);

  // Memoize tab content to prevent unnecessary re-renders
  const OverviewTab = useMemo(() => {
    if (!country) return null;
    return (
      <div className="px-4 sm:px-6 py-4 sm:py-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4" style={{ 
          gridTemplateRows: chartHeight > 400 ? `repeat(2, ${chartHeight + 48}px)` : 'auto'
        }}>
          <ChartCard 
            title="Fossil Fuel Utilization Factor"
            subtitle="Annual fossil fuel power plant utilization across geographic levels"
            icon={<Maximize2 className="h-5 w-5" />}
            showHeader={false}
          >
        <UtilizationFactorChart countryIso={country.iso_code} countryName={country.name} height={chartHeight} />
          </ChartCard>
          
          <ChartCard 
            title="CO2 Intensity"
            subtitle="Annual CO2 emissions per unit of electricity generated"
            icon={<Maximize2 className="h-5 w-5" />}
            showHeader={false}
          >
        <CO2IntensityChart countryIso={country.iso_code} countryName={country.name} height={chartHeight} />
          </ChartCard>
          
          <ChartCard 
            title="Generation Trends"
            subtitle="Annual electricity generation by fuel type (2000-2022)"
            icon={<Maximize2 className="h-5 w-5" />}
            showHeader={false}
          >
        <GenerationChart countryIso={country.iso_code} year={2022} height={chartHeight} />
          </ChartCard>
          
          <ChartCard 
            title="Map"
            subtitle="Installed electricity generation capacity by fuel showing infrastructure development over time"
            icon={<Maximize2 className="h-5 w-5" />}
            showHeader={false}
          >
        <CapacityChart countryIso={country.iso_code} year={2022} height={chartHeight} />
          </ChartCard>
      </div>
    </div>
  );
  }, [country, chartHeight]);

  const ExistingStockTab = useMemo(() => {
    if (!country) {
      return (
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading country data...</p>
          </div>
        </div>
      );
    }

    if (existingStockLoading) {
      return (
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading existing stock data...</p>
          </div>
        </div>
      );
    }

    if (existingStockError) {
      return (
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="text-red-500 text-lg font-medium mb-2">Error Loading Data</div>
            <div className="text-gray-600 text-sm">{existingStockError}</div>
            <button 
              onClick={() => loadExistingStockData(country.iso_code)}
              className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              Retry
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="px-4 sm:px-6 py-4 sm:py-6">
        {/* Stacked Histograms Side-by-Side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 sm:gap-4 mb-3 sm:mb-4">
          <ChartCard 
            title="Plant Age Distribution"
            subtitle="Distribution of power plants by age and fuel type"
            icon={<Maximize2 className="h-5 w-5" />}
            showHeader={false}
          >
          <PlantAgeHistogram data={existingStockData} />
          </ChartCard>
          
          <ChartCard 
            title="Plant Size Distribution"
            subtitle="Distribution of power plants by capacity and fuel type"
            icon={<Maximize2 className="h-5 w-5" />}
            showHeader={false}
          >
          <PlantSizeHistogram data={existingStockData} />
          </ChartCard>
        </div>

        </div>
    );
  }, [country, existingStockLoading, existingStockError, existingStockData, loadExistingStockData]);

  const GenerationProfileTab = useMemo(() => {
    if (!country) return null;
    return (
      <div className="px-4 sm:px-6 py-4 sm:py-6">
        <ChartCard 
          showHeader={false}
        >
          <GenerationProfileChart countryIso={country.iso_code} />
        </ChartCard>
      </div>
    );
  }, [country]);

  const RenewablePotentialTabComponent = useMemo(() => {
    if (!country) return null;
    return <RenewablePotentialTab countryIso={country.iso_code} />;
  }, [country]);

  const TransmissionLineTabComponent = useMemo(() => {
    if (!country) return null;
    return <TransmissionLineTab countryIso={country.iso_code} />;
  }, [country]);

  const DemandFuelPriceTab = useMemo(() => {
    if (!country) return null;
    return (
      <div className="px-4 sm:px-6 py-4 sm:py-6">
          
          
       
        <AR6ScenarioChart countryIso={country.iso_code?.toUpperCase()} countryName={country.name} />
      </div>
    );
  }, [country]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-center text-gray-700">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mx-auto mb-4"></div>
          <p>Loading {isoCode} dashboard...</p>
        </div>
      </div>
    );
  }

  if (!country) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-center text-gray-700">
          <h1 className="text-2xl font-bold mb-4">Country Not Found</h1>
          <p className="mb-6">
            The country with ISO code "{isoCode}" could not be found.
          </p>
          <Link to="/" className="btn-primary">
            Return Home
          </Link>
      </div>
    </div>
  );
  }


  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return OverviewTab;
      case 'existing-stock':
        return ExistingStockTab;
      case 'renewable-potential':
        return RenewablePotentialTabComponent;
      case 'transmission-line':
        return TransmissionLineTabComponent;
      case 'demand-fuel-price':
        return DemandFuelPriceTab;
      case 'results':
        return (
          <div className="px-4 sm:px-6 py-4 sm:py-6">
            <div className="flex items-center justify-center h-96">
              <div className="text-center text-gray-500">
                <Database className="h-12 w-12 sm:h-16 sm:w-16 mx-auto mb-4 text-gray-400" />
                <div className="text-xl sm:text-2xl font-semibold mb-2">Results</div>
                <div className="text-base sm:text-lg">Coming Soon</div>
                <div className="text-xs sm:text-sm mt-2 px-4">Analysis results and model outputs will be available here.</div>
              </div>
            </div>
          </div>
        );
      case 'what-vervestacks':
        return (
          <div className="px-4 sm:px-6 py-4 sm:py-6">
            <div className="flex items-center justify-center h-96">
              <div className="text-center text-gray-500">
                <Zap className="h-12 w-12 sm:h-16 sm:w-16 mx-auto mb-4 text-gray-400" />
                <div className="text-xl sm:text-2xl font-semibold mb-2 px-4">What VERVESTACKS can do for {country?.name || 'Japan'}</div>
                <div className="text-base sm:text-lg">Coming Soon</div>
                <div className="text-xs sm:text-sm mt-2 px-4">Customized recommendations and capabilities will be displayed here.</div>
              </div>
            </div>
          </div>
        );
      default:
        return <OverviewTab />;
    }
  };

  return (
    <div className="min-h-screen bg-vervestacks-secondary">
      {/* Section 1: Global Header */}
      <div ref={globalHeaderRef} className="bg-vervestacks-secondary px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-3 sm:gap-4">
          <div className="text-vervestacks-primary font-bold text-lg sm:text-xl">
            VERVESTACKS
          </div>
          <nav className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 lg:space-x-6">
            <a href={`https://vedaonline.cloud?b=${country?.iso_code || isoCode}`}
               target="_blank"
               rel="noopener noreferrer"
               className="text-vervestacks-primary hover:underline text-sm">Veda Online</a>
            <a href="https://vervestacks.readthedocs.io/en/latest/index.html" target="_blank" rel="noopener noreferrer" className="text-vervestacks-primary hover:underline text-sm">Documentation</a>
            {githubLinks.type === 'multiple' ? (
              <div className="relative" ref={githubDropdownRef}>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setShowGithubDropdown(!showGithubDropdown);
                  }}
                  className="text-vervestacks-primary hover:underline text-sm inline-flex items-center"
                >
                  GitHub <ChevronDown className={`h-4 w-4 ml-1 text-vervestacks-primary transition-transform ${showGithubDropdown ? 'rotate-180' : ''}`} />
                </button>
                {showGithubDropdown && (
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-xl border border-gray-200 z-50">
                    <div className="py-2">
                      {githubLinks.items.map(item => (
                        <a
                          key={item.url}
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                        >
                          {item.name}
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <a
                href={githubLinks.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-vervestacks-primary hover:underline text-sm"
              >GitHub</a>
            )}
          </nav>
        </div>
      </div>

      {/* Section 2: Single Card containing Country Header, Tabs, and Content */}
      <div className="bg-vervestacks-secondary px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
        <div className="rounded-xl shadow-card" style={{ backgroundColor: '#F0F5FF' }}>
          {/* Country Header */}
          <div ref={countryHeaderRef} className="px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-4">
              <div className="flex items-center space-x-3 sm:space-x-4 w-full sm:w-auto">
                {/* Back Button */}
                <Link to="/" className="text-vervestacks-primary hover:text-vervestacks-primary/80 transition-colors flex-shrink-0">
                  <ArrowLeft className="h-5 w-5 sm:h-6 sm:w-6" />
                </Link>
                <h1 className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-900 truncate">
                  {country.name}'s Energy Analysis
                    </h1>
                  </div>
              <div className="flex items-center gap-2 sm:gap-3 w-full sm:w-auto justify-end">
                {/* Country Selector with Dropdown */}
                <div className="relative" ref={dropdownRef}>
                  <div 
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setShowCountryDropdown(!showCountryDropdown);
                    }}
                    className="bg-white border border-gray-200 rounded-md px-3 sm:px-4 py-2 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer"
                  >
                    <div className="flex items-center space-x-2">
                      {getCountryFlag(country)}
                      <span className="text-gray-900 font-medium text-xs sm:text-sm hidden sm:inline">{country.name}</span>
                      <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${showCountryDropdown ? 'rotate-180' : ''}`} />
                </div>
              </div>
              
                  {/* Dropdown Menu */}
                  {showCountryDropdown && (
                    <div 
                      className="absolute top-full mt-2 right-0 w-72 sm:w-80 bg-white rounded-lg shadow-xl border border-gray-200 max-h-96 flex flex-col"
                      style={{ zIndex: 9999 }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {/* Search Box */}
                      <div className="p-3 border-b border-gray-200">
                        <div className="relative">
                          <input
                            type="text"
                            placeholder="Search countries..."
                            value={countrySearchTerm}
                            onChange={handleSearchChange}
                            onClick={(e) => {
                              e.stopPropagation();
                            }}
                            onKeyDown={(e) => {
                              e.stopPropagation();
                            }}
                            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-md text-sm focus:ring-2 focus:ring-vervestacks-primary focus:border-transparent"
                            autoFocus
                          />
                          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        </div>
                      </div>

                      {/* Country List */}
                      <div className="overflow-y-auto max-h-80">
                        {filteredCountries.length > 0 ? (
                          filteredCountries.map((c) => (
                            <div
                              key={c.iso_code}
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                handleCountrySelect(c);
                              }}
                              className={`flex items-center justify-between px-4 py-2 hover:bg-gray-50 cursor-pointer transition-colors ${
                                c.iso_code === country.iso_code ? 'bg-blue-50' : ''
                              }`}
                            >
                              <div className="flex items-center space-x-3">
                                {getCountryFlag(c)}
                                <span className="text-sm font-medium text-gray-900">{c.name}</span>
                              </div>
                              <span className="text-xs text-gray-500 font-mono">{c.iso_code}</span>
                            </div>
                          ))
                        ) : (
                          <div className="p-4 text-center text-gray-500">
                            <p className="text-sm">No countries found</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Simulator Toggle */}
                <button
                  type="button"
                  role="switch"
                  aria-checked={showHourlySimulator}
                  onClick={() => setShowHourlySimulator(prev => !prev)}
                  className={`${showHourlySimulator ? 'btn-primary' : 'btn-outline'} px-3 sm:px-5 py-2 rounded-md font-medium text-xs sm:text-sm transition-all duration-200 whitespace-nowrap`}
                  title={showHourlySimulator ? 'Turn off simulator' : "Let's Simulate Energy"}
                >
                  <span className="hidden sm:inline">{showHourlySimulator ? 'Simulator On' : "Let's Simulate Energy"}</span>
                  <span className="sm:hidden">{showHourlySimulator ? 'Simulator' : 'Simulate'}</span>
                </button>
          </div>
        </div>
      </div>

          {/* Tab Navigation */}
      {!showHourlySimulator && (
            <div ref={tabNavigationRef} className="px-4 sm:px-6 py-2 sm:py-3 border-b border-gray-200">
              <div className="flex space-x-2 overflow-x-auto scrollbar-hide -mx-4 px-4 sm:mx-0 sm:px-0" style={{ WebkitOverflowScrolling: 'touch' }}>
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                    className={`px-3 sm:px-4 py-2 rounded-md font-medium text-xs sm:text-sm transition-all duration-200 whitespace-nowrap flex-shrink-0 ${
                    activeTab === tab.id
                        ? 'bg-vervestacks-primary text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                  }`}
                >
                    {tab.name}
                </button>
              ))}
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1">
        <motion.div
          key={showHourlySimulator ? 'hourly-simulator' : activeTab}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
              {showHourlySimulator ? GenerationProfileTab : renderTabContent()}
        </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CountryDashboard;
