import React, { useState, useMemo, useCallback } from 'react';
import { Search, Globe } from 'lucide-react';
import * as Flags from 'country-flag-icons/react/3x2';
import PropTypes from 'prop-types';

const CountryList = ({ countries = [], selectedCountry = null, onCountrySelect }) => {
  const [searchTerm, setSearchTerm] = useState('');

  // Optimized flag component with useCallback
  const getCountryFlag = useCallback((country) => {
    if (!country?.iso2_code) {
      return (
        <div className="w-6 h-4 bg-gray-200 rounded-sm flex items-center justify-center">
          <span className="text-xs text-gray-500 font-mono">{country?.iso_code || '??'}</span>
        </div>
      );
    }
    
    const FlagComponent = Flags[country.iso2_code];
    if (FlagComponent) {
      return <FlagComponent className="w-6 h-4 rounded-sm shadow-md" />;
    }
    
    // Fallback for missing flag - show ISO 3 code
    return (
      <div className="w-6 h-4 bg-gray-200 rounded-sm flex items-center justify-center">
        <span className="text-xs text-gray-500 font-mono">{country.iso_code}</span>
      </div>
    );
  }, []);

  // Filter countries based on search
  const filteredCountries = useMemo(() => {
    if (!countries || !Array.isArray(countries)) return [];
    
    return countries.filter(country => {
      const matchesSearch = country.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           country.iso_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           country.iso2_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           country.capital?.toLowerCase().includes(searchTerm.toLowerCase());
      
      return matchesSearch;
    });
  }, [countries, searchTerm]);

  const handleCountryClick = useCallback((country) => {
    onCountrySelect?.(country);
  }, [onCountrySelect]);

  const CountryCard = ({ country, index }) => (
    <div
      key={country.iso_code || index}
      className={`country-card-simple group ${selectedCountry?.iso_code === country.iso_code ? 'country-card-active-simple' : ''} hover:bg-gray-100 transition-all duration-200`}
      onClick={() => handleCountryClick(country)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {getCountryFlag(country)}
          <h3 className="text-sm font-medium text-gray-900">{country.name}</h3>
        </div>
        <span className="text-xs text-gray-500 font-mono">{country.iso_code}</span>
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col border-2 border-blue-200 rounded-lg bg-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center space-x-2 mb-4">
          <Globe className="h-4 w-4 text-blue-500" />
          <h2 className="text-base font-semibold text-gray-900">Countries</h2>
          <span className="text-xs text-gray-500">({countries?.length || 0})</span>
        </div>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-4 pr-10 py-3 border border-gray-200 rounded-full bg-white shadow-inner focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
          <Search className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        </div>
      </div>

      {/* Country List */}
      <div className="flex-1 overflow-y-auto">
        {filteredCountries.length > 0 ? (
          <div className="p-2 space-y-1">
            {filteredCountries.map((country, index) => (
              <CountryCard key={country.iso_code || index} country={country} index={index} />
            ))}
          </div>
        ) : (
          <div className="p-4 text-center text-gray-500">
            <p className="text-sm">No countries found</p>
            {searchTerm && (
              <p className="text-xs mt-1">Try a different search term</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

CountryList.propTypes = {
  countries: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number,
    iso_code: PropTypes.string.isRequired,
    iso2_code: PropTypes.string,
    name: PropTypes.string.isRequired,
    region: PropTypes.string,
    latitude: PropTypes.string,
    longitude: PropTypes.string,
    population: PropTypes.string,
    capital: PropTypes.string,
  })),
  selectedCountry: PropTypes.shape({
    iso_code: PropTypes.string,
    name: PropTypes.string,
  }),
  onCountrySelect: PropTypes.func.isRequired,
};

export default CountryList;