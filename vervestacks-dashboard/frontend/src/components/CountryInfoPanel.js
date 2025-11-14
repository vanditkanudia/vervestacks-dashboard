import React, { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';

const CountryInfoPanel = ({ country = null, isVisible, onClose, onDashboardClick = null }) => {
  const navigate = useNavigate();
  const [countryData, setCountryData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [countdown, setCountdown] = useState(null);
  const timerRef = useRef(null);

  // Fetch country data from REST Countries API
  useEffect(() => {
    if (!country) return;

    const fetchCountryData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Use country name to fetch data
        const response = await fetch(`https://restcountries.com/v3.1/name/${country.name}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch data: ${response.status}`);
        }
        
        const data = await response.json();
        setCountryData(data[0]); // REST Countries returns an array
      } catch (err) {
        console.error('Error fetching country data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchCountryData();
  }, [country]);

  // Start countdown when country is selected
  useEffect(() => {
    if (!country || !countryData || loading) return;

    setCountdown(3);

    // Start a tick timer; navigation will be handled in a separate effect
    timerRef.current = setInterval(() => {
      setCountdown(prev => (prev == null ? null : prev - 1));
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [country, countryData, loading]);

  // Navigate when countdown hits 0 (avoid updating Router during render/state updater)
  useEffect(() => {
    if (countdown === 0) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (onDashboardClick) {
        onDashboardClick();
      } else if (country?.iso_code) {
        navigate(`/country/${country.iso_code}`);
      }
      setCountdown(null);
    }
  }, [countdown, onDashboardClick, navigate, country]);

  // Clear timer when panel is closed
  useEffect(() => {
    if (!isVisible) {
      setCountdown(null);
    }
  }, [isVisible]);

  const handleDashboardClick = () => {
    setCountdown(null); // Clear timer on manual click
    if (onDashboardClick) {
      onDashboardClick();
    } else {
      navigate(`/country/${country.iso_code}`);
    }
  };

  const formatPopulation = (population) => {
    if (!population) return 'N/A';
    if (population >= 1000000) {
      return `${(population / 1000000).toFixed(1)} Mil`;
    }
    return population.toLocaleString();
  };

  const formatGDP = (gdp) => {
    if (!gdp) return 'N/A';
    // GDP is typically in USD
    if (gdp >= 1000000000000) {
      return `$${(gdp / 1000000000000).toFixed(2)} T`;
    } else if (gdp >= 1000000000) {
      return `$${(gdp / 1000000000).toFixed(2)} B`;
    }
    return `$${gdp.toLocaleString()}`;
  };

  if (!isVisible || !country) return null;

  return (
    <div className="absolute top-4 left-4 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-40">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center">
            <span className="text-xs font-bold text-gray-600">
              {country.iso_code?.substring(0, 2) || '??'}
            </span>
          </div>
          <h2 className="text-lg font-semibold text-gray-900">{country.name}</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 rounded-full transition-colors"
        >
          <X className="h-4 w-4 text-gray-500" />
        </button>
      </div>

      {/* Current Year Badge */}

      {/* Content */}
      <div className="p-4">
        {loading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mx-auto mb-2"></div>
            <p className="text-sm text-gray-600">Loading country data...</p>
          </div>
        )}

        {error && (
          <div className="text-center py-8">
            <p className="text-sm text-red-600 mb-2">Failed to load data</p>
            <p className="text-xs text-gray-500">{error}</p>
          </div>
        )}

        {countryData && !loading && (
          <div className="space-y-4">
            {/* Population */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-600">Population</span>
                <span className="text-xs text-gray-500">2024</span>
              </div>
              <div className="text-lg font-bold text-gray-900">
                {formatPopulation(countryData.population)}
              </div>
              {countryData.capital && (
                <div className="mt-1 text-xs text-gray-500">
                  Capital: {Array.isArray(countryData.capital) ? countryData.capital[0] : countryData.capital}
                </div>
              )}
            </div>

            {/* GDP */}
            {countryData.gdp && (
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-gray-600">GDP</span>
                  <span className="text-xs text-gray-500">2024</span>
                </div>
                <div className="text-lg font-bold text-gray-900">
                  {formatGDP(countryData.gdp)}
                </div>
                {countryData.gini && (
                  <div className="mt-1 text-xs text-gray-500">
                    Gini Index: {Object.values(countryData.gini)[0]}
                  </div>
                )}
              </div>
            )}

            {/* Region */}
            {countryData.region && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Region:</span>
                <span className="font-medium text-gray-900">{countryData.region}</span>
              </div>
            )}
          </div>
        )}

        {/* Dashboard Button */}
        <div className="mt-6">
          <button
            onClick={handleDashboardClick}
            className={`w-full py-3 px-4 font-medium rounded-lg transition-all duration-300 shadow-md hover:shadow-lg ${
              countdown 
                ? 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700' 
                : 'bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600'
            } text-white`}
          >
            {countdown ? `Dashboard (${countdown})` : 'Dashboard'}
          </button>
        </div>
      </div>
    </div>
  );
};

CountryInfoPanel.propTypes = {
  country: PropTypes.shape({
    iso_code: PropTypes.string,
    name: PropTypes.string.isRequired,
  }),
  isVisible: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onDashboardClick: PropTypes.func,
};

// defaultProps removed in favor of default parameters

export default CountryInfoPanel;
