import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { RotateCcw } from 'lucide-react';
import WorldMap from '../components/WorldMap';
import CountryList from '../components/CountryList';
import CountryInfoPanel from '../components/CountryInfoPanel';
import { countriesAPI } from '../services/api';
import toast from 'react-hot-toast';

const HomePage = () => {
  const navigate = useNavigate();
  const [countries, setCountries] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [heroVisible, setHeroVisible] = useState(true);
  const controllerRef = useRef(null);

  useEffect(() => {
    loadCountries();
    
    // Check if user has already explored in this session
    const hasExplored = sessionStorage.getItem('vervestacks-explored');
    if (hasExplored === 'true') {
      setHeroVisible(false);
    }
  }, []);

  const loadCountries = async () => {
    try {
      const data = await countriesAPI.getAll();
      setCountries(data.countries);
    } catch (error) {
      toast.error('Failed to load countries');
      console.error('Error loading countries:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCountrySelect = (country) => {
    setSelectedCountry(country);
    // No navigation - just center and zoom on the map
  };

  const handleExploreClick = () => {
    setHeroVisible(false);
    sessionStorage.setItem('vervestacks-explored', 'true');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-vervestacks-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-vervestacks-primary mx-auto mb-4"></div>
          <p className="text-vervestacks-dark-blue">Loading VerveStacks...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-vervestacks-background relative">
      {/* Top-left brand label - show only after Explore (when hero is hidden) */}
      {!heroVisible && (
        <div className="absolute top-4 left-4 z-30 select-none pointer-events-none">
          <span className="text-2xl sm:text-3xl font-extrabold tracking-wide text-gray-800/80">VERVESTACKS</span>
        </div>
      )}
      {/* Hero Section with Map Background */}
      <div className="relative h-screen flex items-center justify-center overflow-hidden">
        {/* Interactive D3.js World Map - Always visible */}
        <div className="absolute inset-0">
          <WorldMap
            countries={countries}
            selectedCountry={selectedCountry}
            onCountrySelect={handleCountrySelect}
            controllerRef={controllerRef}
          />
        </div>

        {/* Country Info Panel - Only visible when country is selected */}
        {!heroVisible && (
          <CountryInfoPanel
            country={selectedCountry}
            isVisible={!!selectedCountry}
            onClose={() => setSelectedCountry(null)}
            onDashboardClick={() => navigate(`/country/${selectedCountry?.iso_code}`)}
          />
        )}

        {/* Country List Sidebar - Only visible when hero is not visible */}
        {!heroVisible && (
          <div className="absolute inset-0 flex items-center justify-end pr-4 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, x: 400 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="w-80 h-3/4 bg-white rounded-2xl shadow-2xl z-30 hidden lg:block transition-all duration-200 pointer-events-auto border border-gray-200"
            >
              <CountryList
                countries={countries}
                selectedCountry={selectedCountry}
                onCountrySelect={handleCountrySelect}
              />
            </motion.div>
          </div>
        )}

        {/* Landing Panel Overlay */}
        <AnimatePresence>
          {heroVisible && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.6, ease: 'easeInOut' }}
              className="absolute inset-0 z-20 flex items-center justify-center"
            >
              {/* Semi-transparent overlay */}
              <div className="absolute inset-0 bg-black bg-opacity-20"></div>
              
              {/* Landing Panel */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -30 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="relative z-10 text-center px-8 py-12 max-w-2xl mx-4"
              >
                {/* Kanors Logo */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2, duration: 0.6 }}
                  className="mb-8 flex justify-center"
                >
                  <img 
                    src="/images/Kanors_logo.png" 
                    alt="KANORS Logo" 
                    className="h-16 w-auto"
                  />
                </motion.div>

                {/* Main Title */}
                <div className="mb-8">
                  <h1 className="text-5xl md:text-6xl font-bold text-blue-800 mb-6 tracking-tight font-integral">
                    VERVESTACKS
                  </h1>
                </div>
                
                {/* Description */}
                <p className="text-lg text-gray-700 mb-10 leading-relaxed max-w-xl mx-auto">
                  A comprehensive Python project for processing global energy data, creating country-specific 
                  Veda/TIMES energy system models, and managing them with GitHub version control.
                </p>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                  <button
                    onClick={handleExploreClick}
                    className="relative bg-gradient-to-r from-orange-400 via-pink-400 to-red-400 text-white text-lg px-10 py-4 rounded-xl font-bold flex items-center space-x-3 shadow-lg min-w-[180px] group hover:shadow-xl transition-shadow duration-300"
                  >
                    {/* Compass Icon - Only this rotates on button hover */}
                    <div className="relative">
                      <motion.img 
                        src="/images/compass.png" 
                        alt="Compass" 
                        className="h-7 w-7 filter brightness-0 invert"
                        whileHover={{ 
                          rotate: 360
                        }}
                        transition={{ 
                          rotate: { duration: 0.8, ease: "easeInOut" }
                        }}
                      />
                    </div>
                    
                    {/* Button Text */}
                    <span className="tracking-wide">Explore</span>
                    
                    {/* Arrow indicator */}
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                  
                  <motion.button
                    onClick={() => navigate('/docs')}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="text-blue-800 text-lg px-8 py-3 bg-white border border-gray-300 hover:bg-blue-50 rounded-lg font-bold transition-all duration-200 min-w-[160px]"
                  >
                    Learn More
                  </motion.button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Map Controls - Left Side */}
        {!heroVisible && (
          <div className="absolute bottom-4 left-4 z-30 space-y-2">
            <button
              onClick={() => {
                setSelectedCountry(null);
                // Reset map view to original zoom and position
                if (controllerRef.current) {
                  controllerRef.current.resetView();
                }
              }}
              className="map-control-btn px-4 py-2 text-sm font-medium flex items-center space-x-2"
              aria-label="Reset map to default view"
              title="Reset map to default view"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Reset</span>
            </button>
          </div>
        )}

      </div>

      {/* Mobile Country List - Only visible when hero is not visible */}
      {!heroVisible && (
        <section className="lg:hidden bg-white py-12">
          <div className="max-w-lg mx-auto px-4">
            <h2 className="text-2xl font-bold text-vervestacks-dark-blue mb-6 text-center">
              Explore Countries
            </h2>
            <div className="bg-white rounded-xl shadow-sm">
              <CountryList
                countries={countries}
                selectedCountry={selectedCountry}
                onCountrySelect={handleCountrySelect}
              />
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default HomePage;