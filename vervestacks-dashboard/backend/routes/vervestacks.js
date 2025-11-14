const express = require('express');
const router = express.Router();
const db = require('../database/connection');

// VerveStacks energy analysis endpoints
// These now call PostgreSQL procedures directly

/**
 * @route GET /api/overview/energy-analysis/:iso_code
 * @desc Get comprehensive energy analysis data for dashboard charts
 * @access Public
 */
router.get('/energy-analysis/:iso_code', async (req, res) => {
  try {
    const { iso_code } = req.params;
    const { year = 2022 } = req.query;

    // Validate ISO code
    if (!iso_code || iso_code.length !== 3) {
      return res.status(400).json({
        success: false,
        message: 'Invalid ISO code. Must be 3 characters.'
      });
    }

    // Call Python FastAPI service
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const response = await fetch(`${pythonServiceUrl}/overview/energy-analysis/${iso_code}?year=${year}`);
    
    if (!response.ok) {
      throw new Error(`Python service responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    // Return the data directly from Python service without extra wrapping
    res.json(data);

  } catch (error) {
    console.error('Error fetching energy analysis:', error);
    
    if (error.message.includes('fetch')) {
      return res.status(503).json({
        success: false,
        message: 'Python service not available. Please ensure the Python service is running on port 5000.',
        error: 'Service unavailable'
      });
    }

    res.status(500).json({
      success: false,
      message: 'Failed to retrieve energy analysis data',
      error: error.message
    });
  }
});

/**
 * @route GET /api/overview/capacity-utilization/:iso_code
 * @desc Get capacity utilization data for generation trends and capacity evolution charts
 * @access Public
 */
router.get('/capacity-utilization/:iso_code', async (req, res) => {
  try {
    const { iso_code } = req.params;
    const { year = 2022 } = req.query;

    // Validate ISO code
    if (!iso_code || iso_code.length !== 3) {
      return res.status(400).json({
        success: false,
        message: 'Invalid ISO code. Must be 3 characters.'
      });
    }

    // Call PostgreSQL procedures for generation trends and capacity evolution data
    const [generationResult, capacityResult] = await Promise.all([
      db.query('SELECT * FROM vervestacks.usp_get_generation_trends_data($1)', [iso_code]),
      db.query('SELECT * FROM vervestacks.usp_get_capacity_evolution_data($1)', [iso_code])
    ]);


    // Transform generation data to match frontend expectations
    const generation_chart = {};
    const fuel_types = [...new Set(generationResult.rows.map(row => row.FuelType).filter(fuel => fuel != null))];
    const years = [...new Set(generationResult.rows.map(row => row.Year).filter(year => year != null))].sort();

    fuel_types.forEach(fuelType => {
      if (fuelType && typeof fuelType === 'string') {
        generation_chart[fuelType.toLowerCase()] = years.map(year => {
          const row = generationResult.rows.find(r => r.FuelType === fuelType && r.Year === year);
          return row ? row.GenerationTWh : 0;
        });
      }
    });

    // Transform capacity data to match frontend expectations
    const capacity_chart = {};
    const capacity_fuel_types = [...new Set(capacityResult.rows.map(row => row.FuelType).filter(fuel => fuel != null))];
    const capacity_years = [...new Set(capacityResult.rows.map(row => row.Year).filter(year => year != null))].sort();

    capacity_fuel_types.forEach(fuelType => {
      if (fuelType && typeof fuelType === 'string') {
        capacity_chart[fuelType.toLowerCase()] = capacity_years.map(year => {
          const row = capacityResult.rows.find(r => r.FuelType === fuelType && r.Year === year);
          return row ? row.CapacityGW : 0;
        });
      }
    });

    // Return data in the expected format
    res.json({
      success: true,
      data: {
        generation_chart,
        capacity_chart,
        fuel_types: fuel_types.map(f => f.toLowerCase()),
        years: years
      }
    });

  } catch (error) {
    console.error('Error fetching capacity utilization:', error);
    
    res.status(500).json({
      success: false,
      message: 'Failed to retrieve capacity utilization data',
      error: error.message
    });
  }
});

/**
 * @route GET /api/overview/technology-mix/:iso_code
 * @desc Get technology mix and capacity data
 * @access Public
 */
router.get('/technology-mix/:iso_code', async (req, res) => {
  try {
    const { iso_code } = req.params;
    const { year = 2022 } = req.query;

    // Validate ISO code
    if (!iso_code || iso_code.length !== 3) {
      return res.status(400).json({
        success: false,
        message: 'Invalid ISO code. Must be 3 characters.'
      });
    }

    // Call Python FastAPI service
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const response = await fetch(`${pythonServiceUrl}/overview/technology-mix/${iso_code}?year=${year}`);
    
    if (!response.ok) {
      throw new Error(`Python service responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    // Return the data directly from Python service without extra wrapping
    res.json(data);

  } catch (error) {
    console.error('Error fetching technology mix:', error);
    
    if (error.message.includes('fetch')) {
      return res.status(503).json({
        success: false,
        message: 'Python service not available. Please ensure the Python service is running on port 5000.',
        error: 'Service unavailable'
      });
    }

    res.status(500).json({
      success: false,
      message: 'Failed to retrieve technology mix data',
      error: error.message
    });
  }
});

/**
 * @route GET /api/overview/co2-intensity/:iso_code
 * @desc Get CO2 intensity and fuel consumption data
 * @access Public
 */
router.get('/co2-intensity/:iso_code', async (req, res) => {
  try {
    const { iso_code } = req.params;
    const { year = 2022 } = req.query;

    // Validate ISO code
    if (!iso_code || iso_code.length !== 3) {
      return res.status(400).json({
        success: false,
        message: 'Invalid ISO code. Must be 3 characters.'
      });
    }

    // Call Python FastAPI service
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const response = await fetch(`${pythonServiceUrl}/overview/co2-intensity/${iso_code}?year=${year}`);
    
    if (!response.ok) {
      throw new Error(`Python service responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    // Return the data directly from Python service without extra wrapping
    res.json(data);

  } catch (error) {
    console.error('Error fetching CO2 intensity:', error);
    
    if (error.message.includes('fetch')) {
      return res.status(503).json({
        success: false,
        message: 'Python service not available. Please ensure the Python service is running on port 5000.',
        error: 'Service unavailable'
      });
    }

    res.status(500).json({
      success: false,
      message: 'Failed to retrieve CO2 intensity data',
      error: error.message
    });
  }
});

/**
 * @route GET /api/overview/energy-metrics/:iso_code
 * @desc Get energy metrics data for utilization factor and CO2 intensity charts
 * @access Public
 */
router.get('/energy-metrics/:iso_code', async (req, res) => {
  try {
    const { iso_code } = req.params;

    // Validate ISO code
    if (!iso_code || iso_code.length !== 3) {
      return res.status(400).json({
        success: false,
        message: 'Invalid ISO code. Must be 3 characters.'
      });
    }

    // Call PostgreSQL procedures for utilization factor and CO2 intensity data
    const [utilizationResult, co2IntensityResult] = await Promise.all([
      db.query('SELECT * FROM vervestacks.usp_get_utilization_factor_data($1)', [iso_code]),
      db.query('SELECT * FROM vervestacks.usp_get_co2_intensity_data($1)', [iso_code])
    ]);


    // Transform data to match frontend expectations
    const utilization_data = utilizationResult.rows.map(row => ({
      Level: row.Level,
      Year: row.Year,
      Utilization_Factor: row.UtilizationFactor
    }));

    const co2_intensity_data = co2IntensityResult.rows.map(row => ({
      Level: row.Level,
      Year: row.Year,
      CO2_Intensity: row.CO2Intensity
    }));

    // Return data in the expected format
    res.json({
      success: true,
      data: {
        utilization_data,
        co2_intensity_data
      }
    });

  } catch (error) {
    console.error('Error fetching energy metrics:', error);
    
    res.status(500).json({
      success: false,
      message: 'Failed to retrieve energy metrics data',
      error: error.message
    });
  }
});

/**
 * @route GET /api/overview/existing-stock/:iso_code
 * @desc Get existing stock data for infrastructure analysis
 * @access Public
 */
router.get('/existing-stock/:iso_code', async (req, res) => {
  try {
    const { iso_code } = req.params;

    // Validate ISO code
    if (!iso_code || iso_code.length !== 3) {
      return res.status(400).json({
        success: false,
        message: 'Invalid ISO code. Must be 3 characters.'
      });
    }

    // Call Python FastAPI service
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const response = await fetch(`${pythonServiceUrl}/overview/existing-stock/${iso_code}`);
    
    if (!response.ok) {
      throw new Error(`Python service responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    // Return the data directly from Python service without extra wrapping
    res.json(data);

  } catch (error) {
    console.error('Error fetching existing stock data:', error);
    
    if (error.message.includes('fetch')) {
      return res.status(503).json({
        success: false,
        message: 'Python service not available. Please ensure the Python service is running on port 5000.',
        error: 'Service unavailable'
      });
    }

    res.status(500).json({
      success: false,
      message: 'Failed to retrieve existing stock data',
      error: error.message
    });
  }
});

/**
 * @route GET /api/overview/ar6-scenario/:iso_code
 * @desc Get AR6 scenario drivers for demand and fuel price evolution
 * @access Public
 */
router.get('/ar6-scenario/:iso_code', async (req, res) => {
  try {
    const { iso_code } = req.params;

    // Validate ISO code
    if (!iso_code || iso_code.length !== 3) {
      return res.status(400).json({
        success: false,
        message: 'Invalid ISO code. Must be 3 characters.'
      });
    }

    // Call Python FastAPI service
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const response = await fetch(`${pythonServiceUrl}/ar6-scenario/${iso_code}`);
    
    if (!response.ok) {
      throw new Error(`Python service responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    // Return the data directly from Python service without extra wrapping
    res.json(data);

  } catch (error) {
    console.error('Error fetching AR6 scenario data:', error);
    
    if (error.message.includes('fetch')) {
      return res.status(503).json({
        success: false,
        message: 'Python service not available. Please ensure the Python service is running on port 5000.',
        error: 'Service unavailable'
      });
    }

    res.status(500).json({
      success: false,
      message: 'Failed to retrieve AR6 scenario data',
      error: error.message
    });
  }
});

module.exports = router;
