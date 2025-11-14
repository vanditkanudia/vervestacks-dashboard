const { Pool } = require('pg');
const config = require('../config');

let pool = null;

// Initialize database connection pool
const initializePool = () => {
  if (!pool) {
    pool = new Pool({
      host: config.get('database.host'),
      port: config.get('database.port'),
      database: config.get('database.name'),
      user: config.get('database.user'),
      password: config.get('database.password'),
      ssl: config.get('database.ssl'),
      max: config.get('database.pool.max'),
      idleTimeoutMillis: config.get('database.pool.idleTimeoutMillis'),
      connectionTimeoutMillis: config.get('database.pool.connectionTimeoutMillis'),
    });

    // Handle pool errors
    pool.on('error', (err) => {
      console.error('Unexpected error on idle client', err);
      process.exit(-1);
    });

    console.log('✅ PostgreSQL connection pool initialized');
  }
  return pool;
};

// Get database connection
const getConnection = () => {
  if (!pool) {
    initializePool();
  }
  return pool;
};

// Execute a query
const query = async (text, params = []) => {
  const client = await getConnection().connect();
  try {
    // Set the search path to use our schema
    await client.query('SET search_path TO vervestacks, public');
    const result = await client.query(text, params);
    return result;
  } finally {
    client.release();
  }
};

// Test database connection
const testConnection = async () => {
  try {
    const result = await query('SELECT NOW()');
    console.log('✅ Database connection successful:', result.rows[0]);
    return true;
  } catch (error) {
    console.error('❌ Database connection failed:', error.message);
    return false;
  }
};

// Initialize database tables
const initializeDatabase = async () => {
  try {
    // Read and execute schema.sql
    const fs = require('fs');
    const path = require('path');
    const schemaPath = path.join(__dirname, 'setup_database.sql');
    const schema = fs.readFileSync(schemaPath, 'utf8');
    
    // Split schema into individual statements
    const statements = schema
      .split(';')
      .map(stmt => stmt.trim())
      .filter(stmt => stmt.length > 0 && !stmt.startsWith('--'));
    
    for (const statement of statements) {
      if (statement.trim()) {
        await query(statement);
      }
    }
    
    console.log('✅ Database schema initialized successfully');
    return true;
  } catch (error) {
    console.error('❌ Database schema initialization failed:', error.message);
    return false;
  }
};

// Close database connection pool
const closePool = async () => {
  if (pool) {
    await pool.end();
    pool = null;
    console.log('✅ Database connection pool closed');
  }
};

module.exports = {
  query,
  getConnection,
  testConnection,
  initializeDatabase,
  closePool,
  pool: null // Will be set by initializePool
};
