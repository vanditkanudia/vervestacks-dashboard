const axios = require('axios');

class PythonExecutor {
  constructor() {
    // Python API server configuration
    // Use environment variable for production deployment
    this.pythonApiUrl = process.env.PYTHON_API_URL;
    this.apiTimeout = 120000; // 120 seconds for heavy hourly profile generation
  }

  /**
   * Execute Python function via REST API
   */
  async executeGenerationProfile(isoCode, year, totalGenerationTwh = null) {
    try {
      console.log(`🔄 Calling Python API for ${isoCode} in ${year}${totalGenerationTwh ? ` (${totalGenerationTwh} TWh)` : ' (from EMBER data)'}`);
      
      const response = await axios.post(`${this.pythonApiUrl}/generate-profile`, {
        iso_code: isoCode,
        year: year,
        total_generation_twh: totalGenerationTwh
      }, {
        timeout: this.apiTimeout
      });
      
      console.log(`✅ Python API response received for ${isoCode}`);
      return response.data.profile;
      
    } catch (error) {
      if (error.code === 'ECONNREFUSED') {
        throw new Error('Python API server not running. Start it with: cd python-service && python api_server.py');
      }
      throw new Error(`Python API error: ${error.response?.data?.detail || error.message}`);
    }
  }

  /**
   * Check if Python API is available
   */
  async checkPythonAvailability() {
    try {
      await axios.get(`${this.pythonApiUrl}/health`, { timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Execute Python function to get capacity data via REST API
   */
  async executeCapacityByFuel(isoCode, year) {
    try {
      console.log(`🔄 Calling Python API for capacity data: ${isoCode} in ${year}`);
      
      const response = await axios.get(`${this.pythonApiUrl}/capacity-by-fuel/${isoCode}/${year}`, {
        timeout: this.apiTimeout
      });
      
      console.log(`✅ Python API capacity response received for ${isoCode}`);
      return response.data;
      
    } catch (error) {
      if (error.code === 'ECONNREFUSED') {
        throw new Error('Python API server not running. Start it with: cd python-service && python api_server.py');
      }
      throw new Error(`Python API error: ${error.response?.data?.detail || error.message}`);
    }
  }

  /**
   * Get fuel colors from Python energy_colors.py file
   */
  async executeFuelColors() {
    try {
      console.log('🔄 Calling Python API for fuel colors');
      
      const response = await axios.get(`${this.pythonApiUrl}/fuel-colors`, {
        timeout: this.apiTimeout
      });
      
      console.log('✅ Python API fuel colors response received');
      return response.data;
      
    } catch (error) {
      if (error.code === 'ECONNREFUSED') {
        throw new Error('Python API server not running. Start it with: cd python-service && python api_server.py');
      }
      throw new Error(`Python API error: ${error.response?.data?.detail || error.message}`);
    }
  }

  /**
   * Execute Python hourly solar profile with explicit capacity (GW)
   */
  async executeSolarHourly(isoCode, year, capacityGw) {
    try {
      if (!isoCode || !year || !capacityGw || isNaN(capacityGw) || capacityGw <= 0) {
        throw new Error('Invalid parameters for solar hourly profile');
      }
      const url = `${this.pythonApiUrl}/generation-profile/solar-hourly/${isoCode}`;
      const response = await axios.get(url, {
        params: { year: Number(year), capacity_gw: Number(capacityGw) },
        timeout: this.apiTimeout
      });
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNREFUSED') {
        throw new Error('Python API server not running. Start it with: cd python-service && python api_server.py');
      }
      throw new Error(`Python API error: ${error.response?.data?.detail || error.message}`);
    }
  }

  /**
   * Execute Python hourly wind (onshore) profile with explicit capacity (GW)
   */
  async executeWindHourly(isoCode, year, capacityGw) {
    try {
      if (!isoCode || !year || !capacityGw || isNaN(capacityGw) || capacityGw <= 0) {
        throw new Error('Invalid parameters for wind hourly profile');
      }
      const url = `${this.pythonApiUrl}/generation-profile/wind-hourly/${isoCode}`;
      const response = await axios.get(url, {
        params: { year: Number(year), capacity_gw: Number(capacityGw) },
        timeout: this.apiTimeout
      });
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNREFUSED') {
        throw new Error('Python API server not running. Start it with: cd python-service && python api_server.py');
      }
      throw new Error(`Python API error: ${error.response?.data?.detail || error.message}`);
    }
  }

  /**
   * Execute Python hourly wind (offshore) profile with explicit capacity (GW)
   */
  async executeWindOffHourly(isoCode, year, capacityGw) {
    try {
      if (!isoCode || !year || !capacityGw || isNaN(capacityGw) || capacityGw <= 0) {
        throw new Error('Invalid parameters for offshore wind hourly profile');
      }
      const url = `${this.pythonApiUrl}/generation-profile/windoff-hourly/${isoCode}`;
      const response = await axios.get(url, {
        params: { year: Number(year), capacity_gw: Number(capacityGw) },
        timeout: this.apiTimeout
      });
      return response.data;
    } catch (error) {
      if (error.code === 'ECONNREFUSED') {
        throw new Error('Python API server not running. Start it with: cd python-service && python api_server.py');
      }
      throw new Error(`Python API error: ${error.response?.data?.detail || error.message}`);
    }
  }
}

module.exports = PythonExecutor;
