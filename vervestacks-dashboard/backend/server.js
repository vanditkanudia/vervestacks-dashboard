const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const compression = require('compression');
const morgan = require('morgan');
const config = require('./config');
const db = require('./database/connection');

// Import routes
const authRoutes = require('./routes/auth');
const countryRoutes = require('./routes/countries');
const generationProfileRoutes = require('./routes/generationProfile');
const capacityRoutes = require('./routes/capacity');
const vervestacksRoutes = require('./routes/vervestacks');
const renewablePotentialRoutes = require('./routes/renewablePotential');
const transmissionRoutes = require('./routes/transmission');

const app = express();

// Trust proxy for rate limiting (fixes X-Forwarded-For header issue)
app.set('trust proxy', config.get('security.trustProxy'));

// Security middleware
if (config.get('security.helmet')) {
  app.use(helmet());
}
if (config.get('security.compression')) {
  app.use(compression());
}

// Rate limiting with proper configuration
const limiter = rateLimit({
  windowMs: config.get('rateLimit.windowMs'),
  max: config.get('rateLimit.max'),
  standardHeaders: true,
  legacyHeaders: false,
  skipSuccessfulRequests: config.get('rateLimit.skipSuccessfulRequests'),
  skip: (req) => req.path === '/health' || config.isDevelopment()
});
app.use(limiter);

// CORS configuration
app.use(cors({
  origin: config.get('cors.origin'),
  credentials: config.get('cors.credentials'),
  methods: config.get('cors.methods'),
  allowedHeaders: config.get('cors.allowedHeaders'),
  optionsSuccessStatus: 200
}));

// Logging
app.use(morgan('combined'));

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    service: 'VerveStacks Dashboard API'
  });
});

// API routes
app.use('/api/auth', authRoutes);
app.use('/api/countries', countryRoutes);
app.use('/api/generation-profile', generationProfileRoutes);
app.use('/api/capacity', capacityRoutes);
app.use('/api/overview', vervestacksRoutes);
app.use('/api/renewable-potential', renewablePotentialRoutes);
app.use('/api/transmission', transmissionRoutes);

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    message: 'VerveStacks Dashboard API',
    version: '1.0.0',
    documentation: '/api/docs',
    health: '/health'
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    message: 'Route not found',
    path: req.originalUrl
  });
});

// Global error handler
app.use((error, req, res, next) => {
  console.error('Global error handler:', error);
  res.status(500).json({
    message: 'Internal server error',
    ...(process.env.NODE_ENV === 'development' && { error: error.message })
  });
});

const PORT = config.get('server.port');

// Initialize database and start server
const startServer = async () => {
  try {
    // Test database connection
    const dbConnected = await db.testConnection();
    if (!dbConnected) {
      console.error('❌ Failed to connect to database. Server will not start.');
      process.exit(1);
    }

    // Initialize database schema
    // await db.initializeDatabase();

    // Start the server
    const host = config.get('server.host');
    const protocol = config.get('server.protocol');
    
    app.listen(PORT, host, () => {
      console.log('🚀 VerveStacks Dashboard API');
      console.log('================================');
      console.log(`🌍 Server running on ${protocol}://${host}:${PORT}`);
      console.log(`📋 Health check: ${protocol}://${host}:${PORT}/health`);
      console.log(`🔗 API base: ${protocol}://${host}:${PORT}/api`);
      console.log(`🔧 Environment: ${config.getEnvironment()}`);
      console.log('✅ Database connected and schema initialized');
      console.log('================================');
    });

  } catch (error) {
    console.error('❌ Server startup failed:', error);
    process.exit(1);
  }
};

// Handle graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 Shutting down server gracefully...');
  await db.closePool();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n🛑 Shutting down server gracefully...');
  await db.closePool();
  process.exit(0);
});

startServer();

module.exports = app;
