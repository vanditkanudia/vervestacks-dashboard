const express = require('express');
const db = require('../database/connection');
const { optionalAuth } = require('../middleware/auth');

const router = express.Router();

// Get all countries
router.get('/', optionalAuth, async (req, res) => {
  try {
    const query = `
      SELECT 
        id,
        iso_code,
        iso2_code,
        name,
        region,
        latitude,
        longitude,
        population,
        capital
      FROM countries 
      ORDER BY name ASC
    `;
    const result = await db.query(query);
    
    res.json({
      countries: result.rows,
      total: result.rows.length
    });
  } catch (error) {
    console.error('Error fetching countries:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Get single country by ISO code
router.get('/:isoCode', optionalAuth, async (req, res) => {
  try {
    const { isoCode } = req.params;
    
    const query = `
      SELECT 
        id,
        iso_code,
        iso2_code,
        name,
        region,
        latitude,
        longitude,
        population,
        capital
      FROM countries 
      WHERE UPPER(iso_code) = UPPER($1)
    `;
    const result = await db.query(query, [isoCode]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ message: 'Country not found' });
    }
    
    const country = result.rows[0];
    
    res.json({ country });
  } catch (error) {
    console.error('Error fetching country:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Get countries by region
router.get('/region/:region', optionalAuth, async (req, res) => {
  try {
    const { region } = req.params;
    
    const query = `
      SELECT 
        id,
        iso_code,
        iso2_code,
        name,
        region,
        latitude,
        longitude,
        population,
        capital
      FROM countries 
      WHERE LOWER(region) = LOWER($1)
      ORDER BY name ASC
    `;
    const result = await db.query(query, [region]);
    
    res.json({
      countries: result.rows,
      region: region,
      total: result.rows.length
    });
  } catch (error) {
    console.error('Error fetching countries by region:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

module.exports = router;
