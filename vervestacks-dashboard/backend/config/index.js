const ConfigManager = require('../../config/ConfigManager');

// Create global config instance
const config = new ConfigManager();

// Validate configuration
try {
  config.validate();
  config.printSummary();
} catch (error) {
  console.error('❌ Configuration validation failed:', error.message);
  process.exit(1);
}

module.exports = config;
