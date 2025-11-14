const express = require('express');
const PythonExecutor = require('../utils/pythonExecutor');
const db = require('../database/connection');

const router = express.Router();
const pythonExecutor = new PythonExecutor();

/**
 * @route GET /api/capacity/capacity-by-fuel/:iso_code/:year
 * @desc Get generation capacity breakdown by fuel type for a specific country and year
 * @access Public
 */
router.get('/capacity-by-fuel/:iso_code/:year', async (req, res) => {
  try {
    const { iso_code, year } = req.params;

    // Validate parameters
    if (!iso_code || !year) {
      return res.status(400).json({
        success: false,
        message: 'ISO code and year are required'
      });
    }

    // Validate year range
    const yearNum = parseInt(year);
    if (yearNum < 2000 || yearNum > 2022) {
      return res.status(400).json({
        success: false,
        message: 'Year must be between 2000 and 2022',
        received: year
      });
    }

    // Check if Python is available
    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    if (!pythonAvailable) {
      return res.status(500).json({
        success: false,
        message: 'Python service is not available. Please ensure the Python service is running.',
        error: 'Service unavailable'
      });
    }

    // Execute Python script to get capacity data
    const capacityData = await pythonExecutor.executeCapacityByFuel(iso_code, year);
    
    // Return the capacity data
    res.json(capacityData);

  } catch (error) {
    console.error('Capacity endpoint error:', error);

    // Handle specific error cases
    if (error.message.includes('Python API server not running')) {
      return res.status(503).json({
        success: false,
        message: 'Python service not available. Please ensure the Python service is running.',
        error: 'Service unavailable'
      });
    }

    // Other errors
    res.status(500).json({
      success: false,
      message: 'Failed to retrieve capacity data',
      error: error.message
    });
  }
});

/**
 * @route GET /api/capacity/fuel-colors
 * @desc Get fuel colors from Python energy_colors.py file
 * @access Public
 */
router.get('/fuel-colors', async (req, res) => {
  try {
    // Fetch from PostgreSQL fuels table via procedure
    const result = await db.query('SELECT * FROM vervestacks.usp_get_fuel_colors()');

    // Transform rows to key-value map { fuel_name: color }
    const colors = {};
    for (const row of result.rows) {
      if (row.fuel_name && row.color) {
        colors[String(row.fuel_name).toLowerCase()] = String(row.color);
      }
    }

    return res.json(colors);

  } catch (error) {
    console.error('Error fetching fuel colors from database:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch fuel colors from database',
      message: error.message
    });
  }
});

module.exports = router;
