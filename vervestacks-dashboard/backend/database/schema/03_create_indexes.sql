-- VerveStacks Dashboard Database Indexes (Core + Staging)
-- This file creates performance indexes for minimal core and staging tables

-- Set search path
SET search_path TO vervestacks, public;

-- ============================================================================
-- CORE TABLES INDEXES
-- ============================================================================

-- Countries table indexes
CREATE INDEX IF NOT EXISTS idx_countries_iso_code ON vervestacks.countries(iso_code);
CREATE INDEX IF NOT EXISTS idx_countries_iso2_code ON vervestacks.countries(iso2_code);
CREATE INDEX IF NOT EXISTS idx_countries_name ON vervestacks.countries(name);
CREATE INDEX IF NOT EXISTS idx_countries_region ON vervestacks.countries(region);
CREATE INDEX IF NOT EXISTS idx_countries_has_model ON vervestacks.countries(has_model);

-- Cities table indexes
CREATE INDEX IF NOT EXISTS idx_cities_country_id ON vervestacks.cities(country_id);
CREATE INDEX IF NOT EXISTS idx_cities_name ON vervestacks.cities(city_name);
CREATE INDEX IF NOT EXISTS idx_cities_population ON vervestacks.cities(population);
CREATE INDEX IF NOT EXISTS idx_cities_capital_type ON vervestacks.cities(capital_type);
CREATE INDEX IF NOT EXISTS idx_cities_iso3_code ON vervestacks.cities(iso3_code);

-- Users table indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON vervestacks.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON vervestacks.users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON vervestacks.users(is_active);

-- Dashboard sessions indexes
CREATE INDEX IF NOT EXISTS idx_dashboard_sessions_user_id ON vervestacks.dashboard_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_sessions_country_id ON vervestacks.dashboard_sessions(country_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_sessions_created_at ON vervestacks.dashboard_sessions(created_at);

-- ============================================================================
-- STAGING TABLES INDEXES
-- ============================================================================



-- renewable zones staging (onshore)
CREATE INDEX IF NOT EXISTS idx_staging_onshore_iso ON vervestacks.staging_renewable_zones_onshore(iso);
CREATE INDEX IF NOT EXISTS idx_staging_onshore_grid ON vervestacks.staging_renewable_zones_onshore(grid_cell);

-- renewable zones staging (offshore)
CREATE INDEX IF NOT EXISTS idx_staging_offshore_iso ON vervestacks.staging_renewable_zones_offshore(iso);
CREATE INDEX IF NOT EXISTS idx_staging_offshore_grid ON vervestacks.staging_renewable_zones_offshore(grid_cell);

-- Show index creation status
SELECT 'Core + staging indexes created successfully!' as status;
