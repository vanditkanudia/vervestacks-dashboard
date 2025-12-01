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

-- GEM plants staging indexes
CREATE INDEX IF NOT EXISTS idx_staging_gem_iso ON vervestacks.staging_gem_plants(iso_code);
CREATE INDEX IF NOT EXISTS idx_staging_gem_status ON vervestacks.staging_gem_plants(status);
CREATE INDEX IF NOT EXISTS idx_staging_gem_type ON vervestacks.staging_gem_plants(type);

-- ============================================================================
-- GEM PLANTS INDEXES
-- ============================================================================

-- GEM techmap lookup index
CREATE INDEX IF NOT EXISTS idx_gem_techmap_lookup 
    ON vervestacks.gem_techmap(type_mod, technology);

-- GEM plants main table indexes
CREATE INDEX IF NOT EXISTS idx_gem_plants_iso ON vervestacks.gem_plants(iso_code);
CREATE INDEX IF NOT EXISTS idx_gem_plants_status ON vervestacks.gem_plants(status);
CREATE INDEX IF NOT EXISTS idx_gem_plants_model_fuel ON vervestacks.gem_plants(model_fuel);
CREATE INDEX IF NOT EXISTS idx_gem_plants_coordinates ON vervestacks.gem_plants(has_coordinates) WHERE has_coordinates = TRUE;
CREATE INDEX IF NOT EXISTS idx_gem_plants_operating ON vervestacks.gem_plants(iso_code, status) WHERE LOWER(status) IN ('operating', 'construction');

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_gem_plants_iso_status_fuel 
    ON vervestacks.gem_plants(iso_code, status, model_fuel);

-- ============================================================================
-- TRANSMISSION GENERATION PLANTS INDEXES
-- ============================================================================

-- Staging table indexes
CREATE INDEX IF NOT EXISTS idx_staging_transmission_gen_iso 
    ON vervestacks.staging_transmission_generation_plants(iso_code);

-- Main table indexes
CREATE INDEX IF NOT EXISTS idx_transmission_gen_plants_iso 
    ON vervestacks.transmission_generation_plants(iso_code);

CREATE INDEX IF NOT EXISTS idx_transmission_gen_plants_fuel 
    ON vervestacks.transmission_generation_plants(fuel_type);

CREATE INDEX IF NOT EXISTS idx_transmission_gen_plants_coordinates 
    ON vervestacks.transmission_generation_plants(latitude, longitude) 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_transmission_gen_plants_has_coords 
    ON vervestacks.transmission_generation_plants(has_coordinates) 
    WHERE has_coordinates = TRUE;

-- Composite index for common queries (iso_code + fuel_type)
CREATE INDEX IF NOT EXISTS idx_transmission_gen_plants_iso_fuel 
    ON vervestacks.transmission_generation_plants(iso_code, fuel_type);

-- ============================================================================
-- TRANSMISSION NETWORK INDEXES
-- ============================================================================

-- Staging table indexes
CREATE INDEX IF NOT EXISTS idx_staging_transmission_buses_country 
    ON vervestacks.staging_transmission_buses(country);

CREATE INDEX IF NOT EXISTS idx_staging_transmission_lines_bus0 
    ON vervestacks.staging_transmission_lines(bus0);

CREATE INDEX IF NOT EXISTS idx_staging_transmission_lines_bus1 
    ON vervestacks.staging_transmission_lines(bus1);

-- Transmission buses indexes
CREATE UNIQUE INDEX IF NOT EXISTS idx_transmission_buses_bus_id 
    ON vervestacks.transmission_buses(bus_id);

CREATE INDEX IF NOT EXISTS idx_transmission_buses_country 
    ON vervestacks.transmission_buses(country);

CREATE INDEX IF NOT EXISTS idx_transmission_buses_iso3 
    ON vervestacks.transmission_buses(iso3_code);

CREATE INDEX IF NOT EXISTS idx_transmission_buses_voltage 
    ON vervestacks.transmission_buses(voltage);

CREATE INDEX IF NOT EXISTS idx_transmission_buses_coordinates 
    ON vervestacks.transmission_buses(latitude, longitude) 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Transmission lines indexes
CREATE INDEX IF NOT EXISTS idx_transmission_lines_country 
    ON vervestacks.transmission_lines(country);

CREATE INDEX IF NOT EXISTS idx_transmission_lines_iso3 
    ON vervestacks.transmission_lines(iso3_code);

CREATE INDEX IF NOT EXISTS idx_transmission_lines_bus0 
    ON vervestacks.transmission_lines(bus0_id);

CREATE INDEX IF NOT EXISTS idx_transmission_lines_bus1 
    ON vervestacks.transmission_lines(bus1_id);

CREATE INDEX IF NOT EXISTS idx_transmission_lines_voltage 
    ON vervestacks.transmission_lines(voltage);

CREATE INDEX IF NOT EXISTS idx_transmission_lines_bus_pair 
    ON vervestacks.transmission_lines(bus0_id, bus1_id);
-- DEMAND PROFILES INDEXES (ERA5 Combined Data)
-- ============================================================================

-- Primary query pattern: filter by country, demand_year, weather_year
CREATE INDEX IF NOT EXISTS idx_era5_country_demand_weather 
    ON vervestacks.era5_combined_data_2030(country, demand_year, weather_year);

-- Composite index for time series queries (most common pattern)
CREATE INDEX IF NOT EXISTS idx_era5_country_demand_weather_time 
    ON vervestacks.era5_combined_data_2030(country, demand_year, weather_year, month, day, hour);

-- Index for country-level filtering
CREATE INDEX IF NOT EXISTS idx_era5_country 
    ON vervestacks.era5_combined_data_2030(country);

-- Index for demand year queries (scenario filtering)
CREATE INDEX IF NOT EXISTS idx_era5_demand_year 
    ON vervestacks.era5_combined_data_2030(demand_year);

-- Index for weather year queries (weather pattern analysis)
CREATE INDEX IF NOT EXISTS idx_era5_weather_year 
    ON vervestacks.era5_combined_data_2030(weather_year);

-- Show index creation status
SELECT 'Core + staging indexes created successfully!' as status;
