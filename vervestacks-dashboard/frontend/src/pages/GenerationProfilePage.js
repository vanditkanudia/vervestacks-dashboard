import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, Globe, Info } from 'lucide-react';
import GenerationProfileChart from '../components/GenerationProfileChart';
import api from '../services/api';
import toast from 'react-hot-toast';

const GenerationProfilePage = () => {
  const [formData, setFormData] = useState({
    isoCode: '',
    year: new Date().getFullYear(),
    totalGenerationTwh: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chartData, setChartData] = useState(null);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const validateForm = () => {
    if (!formData.isoCode || formData.isoCode.length !== 3) {
      toast.error('ISO code must be exactly 3 characters');
      return false;
    }
    
    if (formData.year < 2000 || formData.year > 2022) {
      toast.error('Year must be between 2000 and 2022');
      return false;
    }
    
    if (formData.totalGenerationTwh && (formData.totalGenerationTwh < 0.1 || formData.totalGenerationTwh > 10000)) {
      toast.error('Total annual generation must be between 0.1 and 10,000 TWh');
      return false;
    }
    
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError(null);
    setChartData(null);

    try {
      // Prepare request data (convert empty string to null for optional parameter)
      const requestData = {
        isoCode: formData.isoCode,
        year: parseInt(formData.year),
        totalGenerationTwh: formData.totalGenerationTwh ? parseFloat(formData.totalGenerationTwh) : null
      };

      const response = await api.post('/generation-profile', requestData);
      
      if (response.data.success) {
        setChartData(response.data.data);
        const sourceText = requestData.totalGenerationTwh ? `${requestData.totalGenerationTwh} TWh` : 'EMBER data';
        toast.success(`Profile generated successfully for ${formData.isoCode} in ${formData.year} using ${sourceText}!`);
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

  const handleReset = () => {
    setFormData({
      isoCode: '',
      year: 2022,
      totalGenerationTwh: ''
    });
    setChartData(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-vervestacks-primary rounded-lg flex items-center justify-center">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Hourly Generation Profile Generator
                </h1>
                <p className="text-gray-600">
                  Generate 8760-hour electricity generation profiles for any country and year
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Input Form */}
          <div className="lg:col-span-1">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 sticky top-24"
            >
              <h2 className="text-lg font-semibold text-gray-900 mb-6 flex items-center">
                <Globe className="h-5 w-5 mr-2 text-vervestacks-primary" />
                Generation Parameters
              </h2>

              <form onSubmit={handleSubmit} className="space-y-6">
                {/* ISO Code */}
                <div>
                  <label htmlFor="isoCode" className="block text-sm font-medium text-gray-700 mb-2">
                    Country ISO Code
                  </label>
                  <input
                    type="text"
                    id="isoCode"
                    name="isoCode"
                    value={formData.isoCode}
                    onChange={handleInputChange}
                    placeholder="e.g., ITA, JPN, BRA"
                    maxLength={3}
                    className="input-field w-full uppercase"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Enter 3-letter ISO country code (e.g., ITA for Italy)
                  </p>
                </div>

                {/* Year */}
                <div>
                  <label htmlFor="year" className="block text-sm font-medium text-gray-700 mb-2">
                    Year
                  </label>
                  <input
                    type="number"
                    id="year"
                    name="year"
                    value={formData.year}
                    onChange={handleInputChange}
                    min="2000"
                    max="2022"
                    className="input-field w-full"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Year range: 2000 - 2022
                  </p>
                </div>

                {/* Total Annual Generation */}
                <div>
                  <label htmlFor="totalGenerationTwh" className="block text-sm font-medium text-gray-700 mb-2">
                    Total Annual Generation (TWh)
                  </label>
                  <input
                    type="number"
                    id="totalGenerationTwh"
                    name="totalGenerationTwh"
                    value={formData.totalGenerationTwh}
                    onChange={handleInputChange}
                    min="0.1"
                    max="10000"
                    step="0.1"
                    className="input-field w-full"
                    placeholder="Leave empty for default"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Total annual generation in Terawatt-hours. Leave empty for default.
                  </p>
                </div>

                {/* Action Buttons */}
                <div className="space-y-3 pt-4">
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full btn-primary flex items-center justify-center space-x-2 py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    ) : (
                      <>
                        <Zap className="h-4 w-4" />
                        <span>Generate Profile</span>
                      </>
                    )}
                  </button>
                  
                  <button
                    type="button"
                    onClick={handleReset}
                    className="w-full btn-outline py-3"
                  >
                    Reset Form
                  </button>
                </div>
              </form>

              {/* Info Box */}
              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-start space-x-3">
                  <Info className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-blue-800">
                    <p className="font-medium mb-1">How it works</p>
                    <p>
                      This tool calls your Python function to generate 8760 hourly generation values using 
                      demand-shaped profiles from EMBER data. If you specify a total generation target, 
                      it will scale the profile accordingly. The process may take a few moments.
                    </p>
                    <p className="mt-2 text-orange-600 font-medium">
                      ⚠️ Currently using test data while Python integration is being resolved.
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Chart Display */}
          <div className="lg:col-span-2">
            <GenerationProfileChart
              data={chartData}
              loading={loading}
              error={error}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default GenerationProfilePage;
