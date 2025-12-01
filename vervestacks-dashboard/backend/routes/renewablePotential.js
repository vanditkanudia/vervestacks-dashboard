const express = require('express');
const router = express.Router();
const db = require('../database/connection');

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

    // Call PostgreSQL stored procedure
    const result = await db.query(
      'SELECT * FROM vervestacks.usp_get_solar_zones($1)',
      [isoCode.toUpperCase()]
    );

    // Check if result exists and has data
    if (!result.rows || result.rows.length === 0) {
      return res.status(500).json({
        success: false,
        error: 'Database query returned no results'
      });
    }

    const data = result.rows[0].usp_get_solar_zones;
    
    if (!data || !data.success) {
      return res.status(404).json({
        success: false,
        error: data?.error || 'No solar renewable zones data found for this country'
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

    // Call PostgreSQL stored procedure
    const result = await db.query(
      'SELECT * FROM vervestacks.usp_get_wind_zones($1, $2)',
      [isoCode.toUpperCase(), wind_type]
    );

    // Check if result exists and has data
    if (!result.rows || result.rows.length === 0) {
      return res.status(500).json({
        success: false,
        error: 'Database query returned no results'
      });
    }

    const data = result.rows[0].usp_get_wind_zones;
    
    if (!data || !data.success) {
      return res.status(404).json({
        success: false,
        error: data?.error || `No ${wind_type} wind renewable zones data found for this country`
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
    // Check PostgreSQL connection
    const dbCheck = await db.query('SELECT 1 as health');
    const dbHealthy = dbCheck.rows.length > 0;
    
    res.json({
      success: true,
      database: dbHealthy,
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
