const express = require('express');
const router = express.Router();
const PythonExecutor = require('../utils/pythonExecutor');

const pythonExecutor = new PythonExecutor();

/**
 * GET /api/renewable-potential/solar-zones/:isoCode
 * Get solar renewable energy zones for a specific country
 */
router.get('/solar-zones/:isoCode', async (req, res) => {
  try {
    const { isoCode } = req.params;
    
    if (!isoCode || isoCode.length !== 3) {
      return res.status(400).json({
        success: false,
        error: 'Invalid ISO code. Must be 3 characters.'
      });
    }

    // Check Python service availability
    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    if (!pythonAvailable) {
      return res.status(503).json({
        success: false,
        error: 'Python service is not available. Please try again later.'
      });
    }

    // Call Python service for solar zones data
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const pythonResponse = await fetch(`${pythonServiceUrl}/renewable-potential/solar-zones/${isoCode}`);
    
    if (!pythonResponse.ok) {
      const errorData = await pythonResponse.json().catch(() => ({}));
      return res.status(pythonResponse.status).json({
        success: false,
        error: errorData.detail || `Python service error: ${pythonResponse.statusText}`
      });
    }

    const data = await pythonResponse.json();
    
    if (!data.success) {
      return res.status(404).json({
        success: false,
        error: data.error || 'No solar renewable zones data found for this country'
      });
    }

    res.json({
      success: true,
      data: data.data,
      meta: {
        isoCode: isoCode.toUpperCase(),
        timestamp: new Date().toISOString(),
        dataSource: 'Atlite ERA5 Weather Data'
      }
    });

  } catch (error) {
    console.error('Error fetching solar zones:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error while fetching solar renewable zones data'
    });
  }
});

/**
 * GET /api/renewable-potential/wind-zones/:isoCode
 * Get wind renewable energy zones for a specific country (offshore or onshore)
 */
router.get('/wind-zones/:isoCode', async (req, res) => {
  try {
    const { isoCode } = req.params;
    const { wind_type = 'onshore' } = req.query;
    
    if (!isoCode || isoCode.length !== 3) {
      return res.status(400).json({
        success: false,
        error: 'Invalid ISO code. Must be 3 characters.'
      });
    }

    if (!['offshore', 'onshore'].includes(wind_type)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid wind_type. Must be "offshore" or "onshore".'
      });
    }

    // Check Python service availability
    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    if (!pythonAvailable) {
      return res.status(503).json({
        success: false,
        error: 'Python service is not available. Please try again later.'
      });
    }

    // Call Python service for wind zones data
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const pythonResponse = await fetch(`${pythonServiceUrl}/renewable-potential/wind-zones/${isoCode}?wind_type=${wind_type}`);
    
    if (!pythonResponse.ok) {
      const errorData = await pythonResponse.json().catch(() => ({}));
      return res.status(pythonResponse.status).json({
        success: false,
        error: errorData.detail || `Python service error: ${pythonResponse.statusText}`
      });
    }

    const data = await pythonResponse.json();
    
    if (!data.success) {
      return res.status(404).json({
        success: false,
        error: data.error || `No ${wind_type} wind renewable zones data found for this country`
      });
    }

    res.json({
      success: true,
      data: data.data,
      meta: {
        isoCode: isoCode.toUpperCase(),
        windType: wind_type,
        timestamp: new Date().toISOString(),
        dataSource: 'Atlite ERA5 Weather Data'
      }
    });

  } catch (error) {
    console.error('Error fetching wind zones:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error while fetching wind renewable zones data'
    });
  }
});

/**
 * GET /api/renewable-potential/health
 * Health check for renewable potential endpoints
 */
router.get('/health', async (req, res) => {
  try {
    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    
    res.json({
      success: true,
      pythonService: pythonAvailable,
      timestamp: new Date().toISOString(),
      endpoints: [
        'GET /api/renewable-potential/solar-zones/:isoCode',
        'GET /api/renewable-potential/wind-zones/:isoCode'
      ]
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Health check failed'
    });
  }
});

module.exports = router;
