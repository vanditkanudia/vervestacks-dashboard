const jwt = require('jsonwebtoken');
const config = require('../config');
const db = require('../database/connection');

const authenticateToken = async (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ message: 'Access token required' });
  }

  try {
    const decoded = jwt.verify(token, config.development.jwt.secret);
    
    // Verify user still exists and is active
    const userQuery = 'SELECT id, email, role, is_active FROM users WHERE id = $1 AND is_active = true';
    const result = await db.query(userQuery, [decoded.userId]);
    
    if (result.rows.length === 0) {
      return res.status(403).json({ message: 'Invalid or expired token' });
    }
    
    req.user = result.rows[0];
    next();
  } catch (error) {
    return res.status(403).json({ message: 'Invalid or expired token' });
  }
};

const optionalAuth = async (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    req.user = null;
    return next();
  }

  try {
    const decoded = jwt.verify(token, config.development.jwt.secret);
    const userQuery = 'SELECT id, email, role, is_active FROM users WHERE id = $1 AND is_active = true';
    const result = await db.query(userQuery, [decoded.userId]);
    
    req.user = result.rows.length > 0 ? result.rows[0] : null;
  } catch (error) {
    req.user = null;
  }
  
  next();
};

module.exports = { authenticateToken, optionalAuth };
