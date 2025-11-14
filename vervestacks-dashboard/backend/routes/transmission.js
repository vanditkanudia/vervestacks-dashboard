const express = require('express');
const router = express.Router();
const PythonExecutor = require('../utils/pythonExecutor');

const pythonExecutor = new PythonExecutor();

/**
 * GET /api/transmission/data/:isoCode
 * Get transmission line data for a specific country
 */
router.get('/data/:isoCode', async (req, res) => {
  try {
    const { isoCode } = req.params;
    const { clusters } = req.query;
    
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

    // Call Python service for transmission data
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const pythonUrl = `${pythonServiceUrl}/transmission/data/${isoCode}${clusters ? `?clusters=${clusters}` : ''}`;
    const pythonResponse = await fetch(pythonUrl);
    
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
        error: data.error || 'No transmission data found for this country'
      });
    }

    res.json({
      success: true,
      data: data.data,
      meta: {
        isoCode: isoCode.toUpperCase(),
        clusters: clusters || 'auto',
        timestamp: new Date().toISOString(),
        dataSource: 'VerveStacks Regional Clustering Algorithm'
      }
    });

  } catch (error) {
    console.error('Error fetching transmission data:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error while fetching transmission data'
    });
  }
});

/**
 * GET /api/transmission/network/:isoCode
 * Get transmission network data (real infrastructure) for a specific country
 */
router.get('/network/:isoCode', async (req, res) => {
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

    // Call Python service for transmission network data
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const pythonUrl = `${pythonServiceUrl}/transmission/network/${isoCode}`;
    const pythonResponse = await fetch(pythonUrl);
    
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
        error: data.error || 'No transmission network data found for this country'
      });
    }

    res.json({
      success: true,
      data: data.data,
      meta: {
        isoCode: isoCode.toUpperCase(),
        timestamp: new Date().toISOString(),
        dataType: 'Real Transmission Infrastructure (OSM Data)'
      }
    });

  } catch (error) {
    console.error('Error fetching transmission network data:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error while fetching transmission network data'
    });
  }
});

/**
 * GET /api/transmission/generation/:isoCode
 * Get transmission generation data (power plants) for a specific country
 */
router.get('/generation/:isoCode', async (req, res) => {
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

    // Call Python service for transmission generation data
    const pythonServiceUrl = process.env.PYTHON_SERVICE_URL;
    const pythonUrl = `${pythonServiceUrl}/transmission/generation/${isoCode}`;
    const pythonResponse = await fetch(pythonUrl);
    
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
        error: data.error || 'No generation data found for this country'
      });
    }

    res.json({
      success: true,
      data: data.data,
      meta: {
        isoCode: isoCode.toUpperCase(),
        timestamp: new Date().toISOString(),
        dataType: 'Power Generation Plants (CSV Data)'
      }
    });

  } catch (error) {
    console.error('Error fetching transmission generation data:', error);
    res.status(500).json({
      success: false,
      error: 'Internal server error while fetching transmission generation data'
    });
  }
});

/**
 * Health check for transmission endpoints
 */
router.get('/health', async (req, res) => {
  try {
    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    
    res.json({
      success: true,
      pythonService: pythonAvailable,
      timestamp: new Date().toISOString(),
      endpoints: [
        'GET /api/transmission/data/:isoCode',
        'GET /api/transmission/network/:isoCode',
        'GET /api/transmission/generation/:isoCode'
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
