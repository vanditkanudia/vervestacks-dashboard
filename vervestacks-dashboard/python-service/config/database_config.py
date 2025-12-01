"""
Database Configuration Module
Loads database connection settings from environment files
Matches Node.js ConfigManager pattern for consistency
"""

import os
from pathlib import Path


class DatabaseConfig:
    """Database configuration loader (environment-aware)"""
    
    def __init__(self):
        # Read environment (matches Node.js NODE_ENV pattern)
        self.environment = os.getenv('PYTHON_ENV', 'development')
        
        # Load env file
        self._load_env_file()
        
        # Build config
        self.config = self._build_config()
        
        # Log which environment is loaded
        print(f"✅ Database config loaded for environment: {self.environment}")
        self._print_config_summary()
    
    def _load_env_file(self):
        """
        Load environment file (matches Node.js ConfigManager pattern)
        Reads from: vervestacks-dashboard/env/env.{environment}
        """
        # Path from python-service/config/ to env/
        env_file = Path(__file__).parent.parent.parent / 'env' / f'env.{self.environment}'
        
        if not env_file.exists():
            raise FileNotFoundError(
                f"❌ Environment file not found: {env_file}\n"
                f"Expected: env/env.{self.environment}\n"
                f"Available environments: development, production"
            )
        
        # Load env file (same logic as Node.js ConfigManager)
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value
                if '=' not in line:
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                # Don't override existing env vars (allow system overrides)
                if key not in os.environ:
                    os.environ[key] = value
        
        print(f"✅ Loaded environment file: env/env.{self.environment}")
    
    def _build_config(self):
        """
        Build database configuration from environment variables
        Returns asyncpg connection pool configuration
        """
        # Validate required variables
        required = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing = [var for var in required if not os.getenv(var)]
        
        if missing:
            raise ValueError(
                f"❌ Missing required database environment variables: {', '.join(missing)}"
            )
        
        # Pool size based on environment (matches Node.js logic)
        max_size = 50 if self.environment == 'production' else 20
        
        return {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'server_settings': {
                'search_path': 'vervestacks, public'
            },
            'min_size': 10,
            'max_size': max_size,
            'max_inactive_connection_lifetime': 30.0,
            'timeout': 2.0,
            'command_timeout': 60.0
        }
    
    def _print_config_summary(self):
        """Print configuration summary (without sensitive data)"""
        print("\n📋 Database Configuration Summary")
        print("=" * 50)
        print(f"Environment:     {self.environment}")
        print(f"Database Host:   {self.config['host']}:{self.config['port']}")
        print(f"Database Name:   {self.config['database']}")
        print(f"Database User:   {self.config['user']}")
        print(f"Schema Path:     {self.config['server_settings']['search_path']}")
        print(f"Pool Min Size:   {self.config['min_size']}")
        print(f"Pool Max Size:   {self.config['max_size']}")
        print(f"Connection Timeout: {self.config['timeout']}s")
        print("=" * 50 + "\n")
    
    def get(self):
        """Get database configuration dictionary"""
        return self.config
    
    def get_environment(self):
        """Get current environment"""
        return self.environment
    
    def is_production(self):
        """Check if running in production"""
        return self.environment == 'production'
    
    def is_development(self):
        """Check if running in development"""
        return self.environment == 'development'


# Singleton instance
_db_config_instance = None


def get_database_config():
    """
    Get database configuration (singleton pattern)
    
    Returns:
        dict: Database configuration for asyncpg.create_pool()
    
    Example:
        config = get_database_config()
        pool = await asyncpg.create_pool(**config)
    """
    global _db_config_instance
    if _db_config_instance is None:
        _db_config_instance = DatabaseConfig()
    return _db_config_instance.get()


def get_config_instance():
    """
    Get DatabaseConfig instance (for accessing methods like is_production())
    
    Returns:
        DatabaseConfig: Configuration instance
    
    Example:
        config = get_config_instance()
        if config.is_production():
            # Production-specific logic
    """
    global _db_config_instance
    if _db_config_instance is None:
        _db_config_instance = DatabaseConfig()
    return _db_config_instance

