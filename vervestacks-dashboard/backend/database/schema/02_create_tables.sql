-- VerveStacks Dashboard Database Tables (Minimal Core + Staging)
-- This file creates minimal core tables and staging tables for CSV imports

-- Set search path
SET search_path TO vervestacks, public;

-- ============================================================================
-- CORE TABLES (Countries, Cities, Users, Sessions)
-- ============================================================================

-- Countries table (from worldcities.csv)
CREATE TABLE IF NOT EXISTS vervestacks.countries (
    id SERIAL PRIMARY KEY,
    iso_code VARCHAR(3) UNIQUE NOT NULL,
    iso2_code VARCHAR(2),
    name VARCHAR(255) NOT NULL,
    region VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    population BIGINT,
    capital VARCHAR(255),
    has_model BOOLEAN DEFAULT true,
    model_last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cities table (from worldcities.csv)
CREATE TABLE IF NOT EXISTS vervestacks.cities (
    id SERIAL PRIMARY KEY,
    city_name VARCHAR(255) NOT NULL,
    city_ascii VARCHAR(255),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    country_id INTEGER REFERENCES vervestacks.countries(id) ON DELETE CASCADE,
    iso2_code VARCHAR(2),
    iso3_code VARCHAR(3),
    admin_name VARCHAR(255),
    capital_type VARCHAR(50),
    population BIGINT,
    worldcities_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table (for authentication)
CREATE TABLE IF NOT EXISTS vervestacks.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dashboard sessions table (for user sessions)
CREATE TABLE IF NOT EXISTS vervestacks.dashboard_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES vervestacks.users(id) ON DELETE CASCADE,
    country_id INTEGER REFERENCES vervestacks.countries(id) ON DELETE CASCADE,
    session_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fuel reference table (static reference data)
CREATE TABLE IF NOT EXISTS vervestacks.fuels (
    id SERIAL PRIMARY KEY,
    fuel_name VARCHAR(50) UNIQUE NOT NULL,
    fuel_type VARCHAR(20) NOT NULL CHECK (fuel_type IN ('renewable', 'nonrenewable')),
    fuel_group VARCHAR(20) NOT NULL,
    data_category VARCHAR(20) NOT NULL CHECK (data_category IN ('IRENA', 'EMBER')),
    color VARCHAR(7) NOT NULL, -- Hex color code
    display_name VARCHAR(100) NOT NULL,
    alias_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert static fuel reference data
INSERT INTO vervestacks.fuels (fuel_name, fuel_type, fuel_group, data_category, color, display_name, alias_name) VALUES
-- Renewable fuels (IRENA category: Hydro, Solar, Wind)
('hydro', 'renewable', 'hydro', 'IRENA', '#1E90FF', 'Hydro', 'Hydropower'),
('solar', 'renewable', 'solar', 'IRENA', '#FFA500', 'Solar', 'Photovoltaic'),
('windon', 'renewable', 'wind', 'IRENA', '#87CEEB', 'Windon', 'Onshore Wind'),
('windoff', 'renewable', 'wind', 'IRENA', '#005B96', 'Windoff', 'Offshore Wind'),

-- Renewable fuels (EMBER category: Bioenergy, Geothermal)
('bioenergy', 'renewable', 'bioenergy', 'EMBER', '#228B22', 'Bioenergy', 'Biomass'),
('biomass', 'renewable', 'bioenergy', 'EMBER', '#228B22', 'Biomass', 'Bioenergy'),
('geothermal', 'renewable', 'geothermal', 'EMBER', '#8B4513', 'Geothermal', 'Geothermal Energy'),

-- Non-renewable fuels (EMBER category: Coal, Gas, Oil, Nuclear)
('coal', 'nonrenewable', 'fossil', 'EMBER', '#2F4F4F', 'Coal', 'Coal Power'),
('gas', 'nonrenewable', 'fossil', 'EMBER', '#B39DDB', 'Gas', 'Gas Power'),
('oil', 'nonrenewable', 'fossil', 'EMBER', '#FF0000', 'Oil', 'Oil Power'),
('nuclear', 'nonrenewable', 'nuclear', 'EMBER', '#FFD700', 'Nuclear', 'Nuclear Power');

-- ============================================================================
-- STAGING TABLES (CSV-first imports; structure mirrors input files)
-- ============================================================================

-- Raw import for onshore zones (from preprocessed CSV of GeoJSON)
CREATE TABLE IF NOT EXISTS vervestacks.staging_renewable_zones_onshore (
    iso TEXT,
    country_name TEXT,
    grid_cell TEXT,
    centroid_lat NUMERIC,
    centroid_lon NUMERIC,
    zone_score NUMERIC,
    capacity_factor NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    suitable_area_km2 NUMERIC,
    area_km2 NUMERIC,
    perimeter_km NUMERIC,
    file_source TEXT,
    geometry_json TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw import for offshore zones (from preprocessed CSV of GeoJSON)
CREATE TABLE IF NOT EXISTS vervestacks.staging_renewable_zones_offshore (
    iso TEXT,
    grid_cell TEXT,
    centroid_lat NUMERIC,
    centroid_lon NUMERIC,
    zone_score NUMERIC,
    capacity_factor NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    suitable_area_km2 NUMERIC,
    area_km2 NUMERIC,
    perimeter_km NUMERIC,
    file_source TEXT,
    geometry_json TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw import for energy data overview (from data_overview_tab.csv)
CREATE TABLE IF NOT EXISTS vervestacks.staging_data_overview (
    iso_code TEXT,
    year INTEGER,
    model_fuel TEXT,
    generation_twh NUMERIC,
    capacity_gw NUMERIC,
    emissions_mtco2 NUMERIC,
    irena_capacity_gw NUMERIC,
    irena_generation_twh NUMERIC,
    r10 TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Raw import for GEM plants data (from processed_gem_plants_data.csv)
CREATE TABLE IF NOT EXISTS vervestacks.staging_gem_plants (
    plant_name TEXT,
    country_area TEXT,
    iso_code VARCHAR(3),
    city TEXT,
    subnational_unit TEXT,
    type TEXT,
    technology TEXT,
    fuel TEXT,
    status TEXT,
    capacity_mw NUMERIC,
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    start_year INTEGER,
    year INTEGER,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- GEM PLANTS TABLES (Reference + Processed Data)
-- ============================================================================

-- Technology mapping table for model_fuel creation
-- This table maps Type_mod + Technology to model_fuel and model_name
CREATE TABLE IF NOT EXISTS vervestacks.gem_techmap (
    id SERIAL PRIMARY KEY,
    type_mod VARCHAR(50) NOT NULL,
    technology VARCHAR(255) NOT NULL,
    model_fuel VARCHAR(50) NOT NULL,
    model_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(type_mod, technology)
);

-- Main table for processed GEM plants data
-- This table contains the processed data with model_fuel already calculated
CREATE TABLE IF NOT EXISTS vervestacks.gem_plants (
    id SERIAL PRIMARY KEY,
    
    -- Plant identification
    plant_name TEXT NOT NULL,
    country_area TEXT,
    iso_code VARCHAR(3) NOT NULL,
    city TEXT,
    subnational_unit TEXT,
    
    -- Plant characteristics
    type TEXT,
    technology TEXT,
    fuel TEXT,
    status TEXT NOT NULL,
    capacity_mw NUMERIC,
    
    -- Processed fields
    type_mod TEXT,  -- Type after oil/gas splitting
    model_fuel TEXT,  -- Final model fuel after techmap merge
    model_name TEXT,
    
    -- Location
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    has_coordinates BOOLEAN DEFAULT FALSE,
    
    -- Dates
    start_year INTEGER,
    year INTEGER,
    age INTEGER,  -- Calculated: current_year - start_year
    
    -- Additional metadata
    additional_data JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TRANSMISSION GENERATION PLANTS TABLES
-- ============================================================================

-- Staging table for transmission generation plants CSV import
-- Matches CSV column structure exactly
CREATE TABLE IF NOT EXISTS vervestacks.staging_transmission_generation_plants (
    "comm-out" TEXT,
    "model_name" TEXT,
    "Capacity (MW)" NUMERIC,
    "model_fuel" TEXT,
    "model_description" TEXT,
    "comm_id" TEXT,
    "bus_id" TEXT,
    "Latitude" NUMERIC,
    "Longitude" NUMERIC,
    "is_new_tech" TEXT,
    "iso_code" VARCHAR(3),
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main table for transmission generation plants
CREATE TABLE IF NOT EXISTS vervestacks.transmission_generation_plants (
    id SERIAL PRIMARY KEY,
    
    -- Country identification
    iso_code VARCHAR(3) NOT NULL,
    
    -- Plant identification
    plant_name TEXT,  -- From model_name
    comm_out TEXT,  -- From comm-out
    comm_id TEXT,
    bus_id TEXT,
    
    -- Plant characteristics
    capacity_mw NUMERIC,  -- From Capacity (MW)
    fuel_type TEXT,  -- From model_fuel
    description TEXT,  -- From model_description
    is_new_tech BOOLEAN,  -- From is_new_tech
    
    -- Location
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    has_coordinates BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TRANSMISSION NETWORK TABLES (Buses + Lines)
-- ============================================================================

-- Staging table for transmission buses CSV import (matches OSM columns)
CREATE TABLE IF NOT EXISTS vervestacks.staging_transmission_buses (
    bus_id TEXT,
    station_id TEXT,
    voltage TEXT,
    dc TEXT,
    symbol TEXT,
    under_construction TEXT,
    tags TEXT,
    x TEXT,
    y TEXT,
    country TEXT,
    geometry TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main table for transmission buses
CREATE TABLE IF NOT EXISTS vervestacks.transmission_buses (
    id SERIAL PRIMARY KEY,
    bus_id TEXT NOT NULL,
    station_id TEXT,
    country VARCHAR(2) NOT NULL,
    iso3_code VARCHAR(3),  -- ISO3 code from countries table lookup
    voltage NUMERIC,
    is_dc BOOLEAN DEFAULT FALSE,
    symbol TEXT,
    under_construction BOOLEAN DEFAULT FALSE,
    tags TEXT,
    longitude NUMERIC(11, 8),
    latitude NUMERIC(10, 8),
    geometry TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Staging table for transmission lines CSV import (matches OSM columns)
CREATE TABLE IF NOT EXISTS vervestacks.staging_transmission_lines (
    line_id TEXT,
    bus0 TEXT,
    bus1 TEXT,
    voltage TEXT,
    s_nom TEXT,
    circuits TEXT,
    length TEXT,
    underground TEXT,
    under_construction TEXT,
    tags TEXT,
    type TEXT,
    geometry TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main table for transmission lines
CREATE TABLE IF NOT EXISTS vervestacks.transmission_lines (
    id SERIAL PRIMARY KEY,
    line_id TEXT NOT NULL,
    bus0_id TEXT NOT NULL,
    bus1_id TEXT NOT NULL,
    country VARCHAR(2) NOT NULL,
    iso3_code VARCHAR(3),  -- ISO3 code from countries table lookup (inherited from bus)
    voltage NUMERIC,
    s_nom NUMERIC,
    circuits INTEGER,
    length_km NUMERIC,
    underground BOOLEAN DEFAULT FALSE,
    under_construction BOOLEAN DEFAULT FALSE,
    tags TEXT,
    line_type TEXT,
    geometry TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- DEMAND PROFILES TABLE (ERA5 Combined Data)
-- ============================================================================

-- ERA5 combined demand profiles (from era5_combined_data_2030.csv)
-- This table contains hourly demand data with both demand_year (scenario) and weather_year (historical weather)
CREATE TABLE IF NOT EXISTS vervestacks.era5_combined_data_2030 (
    id SERIAL PRIMARY KEY,
    
    -- Country identification
    country VARCHAR(3) NOT NULL,
    region_name TEXT,
    agg_region TEXT,
    
    -- Temporal information
    time TIMESTAMP,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    mm_dd_hh VARCHAR(15),
    
    -- Scenario and weather year
    demand_year INTEGER NOT NULL,
    weather_year INTEGER NOT NULL,
    
    -- Demand value (NULL allowed for missing data - prevents holes in profiles)
    mw NUMERIC,
    
    -- Unique constraint on time series key
    UNIQUE(country, demand_year, weather_year, month, day, hour)
);

COMMENT ON TABLE vervestacks.era5_combined_data_2030 IS 
    'Hourly electricity demand profiles by country with scenario year (demand_year) and weather year (weather_year)';
COMMENT ON COLUMN vervestacks.era5_combined_data_2030.country IS 
    '3-letter ISO country code';
COMMENT ON COLUMN vervestacks.era5_combined_data_2030.mw IS 
    'Electricity demand in megawatts for the hour. NULL values indicate missing data and are converted to 0 in stored procedures to maintain 8760-hour profile integrity.';
COMMENT ON COLUMN vervestacks.era5_combined_data_2030.demand_year IS 
    'Scenario year for demand projection (e.g., 2030)';
COMMENT ON COLUMN vervestacks.era5_combined_data_2030.weather_year IS 
    'Historical weather year used for profile (e.g., 2011)';

-- Show table creation status
SELECT 'Minimal core + staging tables created successfully!' as status;
