const fs = require('fs');
const path = require('path');
// Portable relative path from config/ to env/env.{environment}
const resolvedEnv = (process.env.NODE_ENV || 'development').trim();
const envPath = path.resolve(__dirname, '..', 'env', `env.${resolvedEnv}`);

// Lightweight env loader (no external dependencies)
if (fs.existsSync(envPath)) {
  const content = fs.readFileSync(envPath, 'utf8');
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith('\'') && value.endsWith('\''))) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
} else {
  // Fail fast if env file is missing
  console.error(`❌ Environment file not found: ${envPath}`);
}

class ConfigManager {
  constructor() {
    this.environment = process.env.NODE_ENV || 'development';
    this.config = this.loadConfig();
  }

  /**
   * Load configuration from environment variables
   */
  loadConfig() {
    try {
      const config = {
        environment: this.environment,
        server: {
          port: parseInt(process.env.BACKEND_PORT),
          host: process.env.BACKEND_HOST,
          protocol: process.env.BACKEND_PROTOCOL
        },
        database: {
          host: process.env.DB_HOST,
          port: parseInt(process.env.DB_PORT),
          name: process.env.DB_NAME,
          user: process.env.DB_USER,
          password: process.env.DB_PASSWORD,
          ssl: this.environment === 'production',
          pool: {
            max: this.environment === 'production' ? 50 : 20,
            idleTimeoutMillis: 30000,
            connectionTimeoutMillis: 2000
          }
        },
        jwt: {
          secret: process.env.JWT_SECRET,
          expiresIn: process.env.JWT_EXPIRES_IN,
          algorithm: 'HS256'
        },
        cors: {
          origin: process.env.CORS_ORIGINS
            ? process.env.CORS_ORIGINS.split(',').map(v => v.trim()).filter(Boolean)
            : (process.env.CORS_ORIGIN ? process.env.CORS_ORIGIN : undefined),
          credentials: process.env.CORS_CREDENTIALS === 'true',
          methods: process.env.CORS_METHODS ? process.env.CORS_METHODS.split(',') : ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
          allowedHeaders: process.env.CORS_ALLOWED_HEADERS ? process.env.CORS_ALLOWED_HEADERS.split(',') : ['Content-Type', 'Authorization']
        },
        python: {
          serviceUrl: process.env.PYTHON_SERVICE_URL,
          apiUrl: process.env.PYTHON_API_URL,
          timeout: 30000,
          retries: 3
        },
        logging: {
          level: process.env.LOG_LEVEL,
          console: process.env.LOG_CONSOLE === 'true',
          file: process.env.LOG_FILE === 'true',
          filePath: process.env.LOG_FILE_PATH
        },
        rateLimit: {
          windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS),
          max: parseInt(process.env.RATE_LIMIT_MAX),
          skipSuccessfulRequests: process.env.RATE_LIMIT_SKIP_SUCCESSFUL_REQUESTS === 'true'
        },
        security: {
          helmet: process.env.SECURITY_HELMET === 'true',
          compression: process.env.SECURITY_COMPRESSION === 'true',
          trustProxy: process.env.SECURITY_TRUST_PROXY === 'true'
        }
      };
      
      console.log(`✅ Loaded ${this.environment} configuration from environment variables`);
      return config;
      
    } catch (error) {
      console.error(`❌ Error loading config: ${error.message}`);
      throw error;
    }
  }

  /**
   * Get configuration value by path
   * @param {string} path - Dot notation path (e.g., 'database.host')
   * @param {any} defaultValue - Default value if path not found
   */
  get(path, defaultValue = null) {
    return path.split('.').reduce((obj, key) => {
      return (obj && obj[key] !== undefined) ? obj[key] : defaultValue;
    }, this.config);
  }

  /**
   * Get entire configuration object
   */
  getAll() {
    return this.config;
  }

  /**
   * Get current environment
   */
  getEnvironment() {
    return this.environment;
  }

  /**
   * Check if current environment is production
   */
  isProduction() {
    return this.environment === 'production';
  }

  /**
   * Check if current environment is development
   */
  isDevelopment() {
    return this.environment === 'development';
  }


  /**
   * Validate configuration
   */
  validate() {
    const required = [
      'server.port',
      'database.host',
      'database.name',
      'jwt.secret',
      'python.serviceUrl'
    ];

    const missing = required.filter(path => {
      const value = this.get(path);
      return value === null || value === undefined || value === '';
    });
    
    if (missing.length > 0) {
      throw new Error(`Missing required configuration: ${missing.join(', ')}`);
    }

    return true;
  }

  /**
   * Print configuration summary (without sensitive data)
   */
  printSummary() {
    console.log('\n📋 Configuration Summary');
    console.log('========================');
    console.log(`Environment: ${this.environment}`);
    console.log(`Server: ${this.get('server.protocol')}://${this.get('server.host')}:${this.get('server.port')}`);
    console.log(`Database: ${this.get('database.host')}:${this.get('database.port')}/${this.get('database.name')}`);
    console.log(`Python Service: ${this.get('python.serviceUrl')}`);
    console.log(`CORS Origin: ${this.get('cors.origin')}`);
    console.log(`Logging Level: ${this.get('logging.level')}`);
    console.log('========================\n');
  }
}

module.exports = ConfigManager;
