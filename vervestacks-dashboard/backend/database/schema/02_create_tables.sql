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

-- Show table creation status
SELECT 'Minimal core + staging tables created successfully!' as status;
