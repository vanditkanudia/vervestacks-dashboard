const express = require('express');
const { body, validationResult } = require('express-validator');
const PythonExecutor = require('../utils/pythonExecutor');

const router = express.Router();
const pythonExecutor = new PythonExecutor();

// Input validation middleware
const validateGenerationProfileInput = [
  body('isoCode')
    .isLength({ min: 3, max: 3 })
    .withMessage('ISO code must be exactly 3 characters')
    .isAlpha()
    .withMessage('ISO code must contain only letters')
    .toUpperCase(),
  body('year')
    .isInt({ min: 2000, max: 2022 })
    .withMessage('Year must be between 2000 and 2022'),
  body('totalGenerationTwh')
    .optional({ nullable: true, checkFalsy: false })
    .custom((value) => {
      // If value is null/undefined/empty string, it's valid (optional)
      if (value === null || value === undefined || value === '') {
        return true;
      }
      // If value is provided, validate it's a number between 0.1 and 10000
      const num = parseFloat(value);
      if (isNaN(num) || num < 0.1 || num > 10000) {
        throw new Error('Total annual generation must be between 0.1 and 10,000 TWh');
      }
      return true;
    })
    .withMessage('Total annual generation must be between 0.1 and 10,000 TWh')
];

/**
 * POST /api/generation-profile
 * Generate hourly electricity generation profile for a country and year
 */
router.post('/', validateGenerationProfileInput, async (req, res) => {
  try {
    // Debug logging
    console.log('📥 Received generation profile request:', {
      body: req.body,
      headers: req.headers,
      url: req.url
    });

    // Check for validation errors
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      console.log('❌ Validation errors:', errors.array());
      console.log('📊 Received values:', {
        isoCode: req.body.isoCode,
        year: req.body.year,
        totalGenerationTwh: req.body.totalGenerationTwh,
        totalGenerationTwhType: typeof req.body.totalGenerationTwh
      });
      return res.status(400).json({
        message: 'Validation failed',
        errors: errors.array()
      });
    }

    const { isoCode, year, totalGenerationTwh } = req.body;

    // Additional validation
    if (!isoCode || isoCode.length !== 3) {
      return res.status(400).json({
        message: 'ISO code must be exactly 3 characters',
        received: isoCode
      });
    }

    if (!year || year < 2000 || year > 2022) {
      return res.status(400).json({
        message: 'Year must be between 2000 and 2022',
        received: year
      });
    }

    console.log(`✅ Validation passed for ${isoCode} in ${year}${totalGenerationTwh ? ` (${totalGenerationTwh} TWh)` : ' (from EMBER data)'}`);

    // Check if Python is available
    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    if (!pythonAvailable) {
      return res.status(500).json({
        message: 'Python is not available on the system',
        error: 'Python execution environment not found'
      });
    }

    console.log(`🔄 Generating profile for ${isoCode} in ${year}${totalGenerationTwh ? ` (${totalGenerationTwh} TWh)` : ' (from EMBER data)'}`);

    // Execute Python script to generate profile
    const hourlyProfile = await pythonExecutor.executeGenerationProfile(
      isoCode,
      year,
      totalGenerationTwh
    );

    // Convert GW to MW for display (1 GW = 1000 MW)
    const hourlyProfileMW = hourlyProfile.map(gw => gw * 1000);

    // Calculate summary statistics (in MW for display)
    const totalMWh = hourlyProfileMW.reduce((sum, value) => sum + value, 0);
    const peakMW = Math.max(...hourlyProfileMW);
    const averageMW = totalMWh / 8760;
    const minMW = Math.min(...hourlyProfileMW);

    // Prepare response data
    const response = {
      success: true,
      data: {
        isoCode,
        year,
        totalGenerationTwh: totalGenerationTwh || 'From EMBER data',
        hourlyProfile: hourlyProfileMW, // Store in MW for frontend
        hourlyProfileGW: hourlyProfile, // Also store original GW values
        summary: {
          totalMWh: Math.round(totalMWh),
          peakMW: Math.round(peakMW),
          averageMW: Math.round(averageMW),
          minMW: Math.round(minMW),
          dataPoints: hourlyProfileMW.length,
          totalGW: Math.round(hourlyProfile.reduce((sum, gw) => sum + gw, 0) / 8760 * 100) / 100
        },
        generatedAt: new Date().toISOString()
      }
    };

    console.log(`✅ Profile generated successfully for ${isoCode}`);
    console.log(`   📊 Total: ${Math.round(totalMWh)} MWh, Peak: ${Math.round(peakMW)} MW`);

    res.json(response);

  } catch (error) {
    console.error('❌ Error generating profile:', error);
    
    res.status(500).json({
      success: false,
      message: 'Failed to generate generation profile',
      error: error.message,
      details: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  }
});

/**
 * GET /api/generation-profile/health
 * Check if the generation profile service is healthy
 */
router.get('/health', async (req, res) => {
  try {
    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    
    res.json({
      status: 'OK',
      service: 'Generation Profile Service',
      python: pythonAvailable ? 'Available' : 'Not Available',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({
      status: 'ERROR',
      service: 'Generation Profile Service',
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

/**
 * GET /api/generation-profile/solar-hourly
 * Generate 8760-hour solar profile using explicit capacity (GW)
 */
router.get('/solar-hourly', async (req, res) => {
  try {
    const { isoCode, year, capacityGw } = req.query;

    // Validation (no fallbacks)
    if (!isoCode || typeof isoCode !== 'string' || isoCode.length !== 3 || !/^[A-Za-z]{3}$/.test(isoCode)) {
      return res.status(400).json({ success: false, message: 'isoCode must be a 3-letter code (e.g., ITA)' });
    }
    const yearNum = Number(year);
    if (!yearNum || yearNum < 2000 || yearNum > 2022) {
      return res.status(400).json({ success: false, message: 'year must be between 2000 and 2022' });
    }
    const cap = Number(capacityGw);
    if (!cap || isNaN(cap) || cap <= 0) {
      return res.status(400).json({ success: false, message: 'capacityGw must be a number > 0 (GW)' });
    }

    // Python availability
    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    if (!pythonAvailable) {
      return res.status(503).json({ success: false, message: 'Python service not available. Please start the Python service.' });
    }

    const data = await pythonExecutor.executeSolarHourly(isoCode.toUpperCase(), yearNum, cap);
    return res.json(data);
  } catch (error) {
    console.error('❌ Solar hourly error:', error);
    return res.status(500).json({ success: false, message: 'Failed to generate solar profile', error: error.message });
  }
});

/**
 * GET /api/generation-profile/wind-hourly
 * Generate 8760-hour onshore wind profile using explicit capacity (GW)
 */
router.get('/wind-hourly', async (req, res) => {
  try {
    const { isoCode, year, capacityGw } = req.query;
    if (!isoCode || typeof isoCode !== 'string' || isoCode.length !== 3 || !/^[A-Za-z]{3}$/.test(isoCode)) {
      return res.status(400).json({ success: false, message: 'isoCode must be a 3-letter code (e.g., ITA)' });
    }
    const yearNum = Number(year);
    if (!yearNum || yearNum < 2000 || yearNum > 2022) {
      return res.status(400).json({ success: false, message: 'year must be between 2000 and 2022' });
    }
    const cap = Number(capacityGw);
    if (!cap || isNaN(cap) || cap <= 0) {
      return res.status(400).json({ success: false, message: 'capacityGw must be a number > 0 (GW)' });
    }

    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    if (!pythonAvailable) {
      return res.status(503).json({ success: false, message: 'Python service not available. Please start the Python service.' });
    }

    const data = await pythonExecutor.executeWindHourly(isoCode.toUpperCase(), yearNum, cap);
    return res.json(data);
  } catch (error) {
    console.error('❌ Wind hourly error:', error);
    return res.status(500).json({ success: false, message: 'Failed to generate wind profile', error: error.message });
  }
});

/**
 * GET /api/generation-profile/windoff-hourly
 * Generate 8760-hour offshore wind profile using explicit capacity (GW)
 */
router.get('/windoff-hourly', async (req, res) => {
  try {
    const { isoCode, year, capacityGw } = req.query;
    if (!isoCode || typeof isoCode !== 'string' || isoCode.length !== 3 || !/^[A-Za-z]{3}$/.test(isoCode)) {
      return res.status(400).json({ success: false, message: 'isoCode must be a 3-letter code (e.g., ITA)' });
    }
    const yearNum = Number(year);
    if (!yearNum || yearNum < 2000 || yearNum > 2022) {
      return res.status(400).json({ success: false, message: 'year must be between 2000 and 2022' });
    }
    const cap = Number(capacityGw);
    if (!cap || isNaN(cap) || cap <= 0) {
      return res.status(400).json({ success: false, message: 'capacityGw must be a number > 0 (GW)' });
    }

    const pythonAvailable = await pythonExecutor.checkPythonAvailability();
    if (!pythonAvailable) {
      return res.status(503).json({ success: false, message: 'Python service not available. Please start the Python service.' });
    }

    const data = await pythonExecutor.executeWindOffHourly(isoCode.toUpperCase(), yearNum, cap);
    return res.json(data);
  } catch (error) {
    console.error('❌ Offshore wind hourly error:', error);
    return res.status(500).json({ success: false, message: 'Failed to generate offshore wind profile', error: error.message });
  }
});

module.exports = router;
