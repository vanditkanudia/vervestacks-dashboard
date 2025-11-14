-- Import data overview tab data into VerveStacks database
-- This script handles the complete import process for energy data overview

-- Clear existing staging data
DELETE FROM vervestacks.staging_data_overview;

-- Import data overview
DROP TABLE IF EXISTS temp_data_overview;
CREATE TEMP TABLE temp_data_overview (
    iso_code TEXT,
    year INTEGER,
    model_fuel TEXT,
    generation_twh NUMERIC,
    capacity_gw NUMERIC,
    emissions_mtco2 NUMERIC,
    irena_capacity_gw NUMERIC,
    irena_generation_twh NUMERIC,
    r10 TEXT
);

-- Import CSV data using PROGRAM mode for robust file access
\copy temp_data_overview FROM PROGRAM 'cmd /c type ".\data\data_overview_tab.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

-- Insert data overview with validation
INSERT INTO vervestacks.staging_data_overview (
    iso_code, year, model_fuel, generation_twh, capacity_gw, 
    emissions_mtco2, irena_capacity_gw, irena_generation_twh, r10
)
SELECT 
    iso_code, year, model_fuel, generation_twh, capacity_gw,
    emissions_mtco2, irena_capacity_gw, irena_generation_twh, r10
FROM temp_data_overview
WHERE iso_code IS NOT NULL 
  AND iso_code <> '' 
  AND year IS NOT NULL 
  AND model_fuel IS NOT NULL 
  AND model_fuel <> '';

-- Create consolidated energy metrics table using fuel table for data source selection
DROP TABLE IF EXISTS vervestacks.energy_metrics_consolidated;
CREATE TABLE vervestacks.energy_metrics_consolidated AS
SELECT 
    s.iso_code,
    s.year,
    f.fuel_name,
    f.data_category,
    f.fuel_type,
    f.fuel_group,
    f.color,
    f.display_name,
    s.r10,
    -- Conditional selection based on data_category from fuel table
    CASE 
        WHEN f.data_category = 'EMBER' THEN s.generation_twh
        WHEN f.data_category = 'IRENA' THEN s.irena_generation_twh
        ELSE 0
    END as generation_twh,
    
    CASE 
        WHEN f.data_category = 'EMBER' THEN s.capacity_gw
        WHEN f.data_category = 'IRENA' THEN s.irena_capacity_gw
        ELSE 0
    END as capacity_gw,
    
    s.emissions_mtco2
FROM vervestacks.staging_data_overview s
INNER JOIN vervestacks.fuels f ON s.model_fuel = f.fuel_name
WHERE s.iso_code IS NOT NULL 
  AND s.iso_code <> '' 
  AND s.year IS NOT NULL 
  AND s.model_fuel IS NOT NULL 
  AND s.model_fuel <> '';

-- Add indexes for performance
CREATE INDEX idx_energy_metrics_consolidated_iso_year_fuel 
ON vervestacks.energy_metrics_consolidated (iso_code, year, fuel_name);

CREATE INDEX idx_energy_metrics_consolidated_data_category 
ON vervestacks.energy_metrics_consolidated (data_category);

CREATE INDEX idx_energy_metrics_consolidated_fuel_type 
ON vervestacks.energy_metrics_consolidated (fuel_type);

CREATE INDEX idx_energy_metrics_consolidated_r10 
ON vervestacks.energy_metrics_consolidated (r10);

-- Add primary key constraint
ALTER TABLE vervestacks.energy_metrics_consolidated 
ADD CONSTRAINT pk_energy_metrics_consolidated 
PRIMARY KEY (iso_code, year, fuel_name);

-- Show import results
SELECT 
    'Data Overview Import Complete!' as status,
    COUNT(*) as total_records,
    COUNT(DISTINCT iso_code) as countries,
    COUNT(DISTINCT year) as years,
    COUNT(DISTINCT model_fuel) as fuel_types
FROM vervestacks.staging_data_overview;

-- Show consolidated table results
SELECT 
    'Energy Metrics Consolidated Table Created!' as status,
    COUNT(*) as total_records,
    COUNT(DISTINCT iso_code) as countries,
    COUNT(DISTINCT year) as years,
    COUNT(DISTINCT fuel_name) as fuel_types,
    COUNT(DISTINCT data_category) as data_sources
FROM vervestacks.energy_metrics_consolidated;
