-- Import GEM Plants Data into VerveStacks Database
-- This script handles the complete import process for GEM power plant data
-- Follows the same structure as import_data_overview.sql

-- Clear existing staging data
DELETE FROM vervestacks.staging_gem_plants;

-- Import GEM plants data
DROP TABLE IF EXISTS temp_gem_plants;
CREATE TEMP TABLE temp_gem_plants (
    "Type" TEXT,
    "Country/area" TEXT,
    "Subregion" TEXT,
    "Region" TEXT,
    "Plant / Project name" TEXT,
    "Unit / Phase name" TEXT,
    "Plant / Project name (local)" TEXT,
    "Plant / Project name (other)" TEXT,
    "Capacity (MW)" NUMERIC,
    "Status" TEXT,
    "Start year" TEXT,
    "Retired year" TEXT,
    "Technology" TEXT,
    "Fuel" TEXT,
    "Hydrogen production" TEXT,
    "Hydrogen capable" TEXT,
    "Country/area 1 (hydropower only)" TEXT,
    "Country/area 2 (hydropower only)" TEXT,
    "Country/area 1 Capacity (MW) (hydropower only)" NUMERIC,
    "Country/area 2 Capacity (MW) (hydropower only)" NUMERIC,
    "Owner" TEXT,
    "Parent" TEXT,
    "CHP" TEXT,
    "CCS" TEXT,
    "Conversion/replacement" TEXT,
    "Unit conversion year" TEXT,
    "Conversion from/replacement of (fuel)" TEXT,
    "Conversion from/replacement of (GEM unit ID)" TEXT,
    "Captive Industry Type" TEXT,
    "Captive Industry Use" TEXT,
    "Captive Non Industry Use" TEXT,
    "Latitude" NUMERIC,
    "Longitude" NUMERIC,
    "Location accuracy" TEXT,
    "City" TEXT,
    "Local area (taluk, county)" TEXT,
    "Major area (prefecture, district)" TEXT,
    "Subnational unit (state, province)" TEXT,
    "GEM location ID" TEXT,
    "GEM unit/phase ID" TEXT,
    "GEM.Wiki URL" TEXT,
    "Type_mod" TEXT,
    "model_fuel" TEXT,
    "model_name" TEXT,
    iso_code TEXT
);

-- Import CSV data using PROGRAM mode for robust file access
-- Note: CSV file path - adjust as needed. Default looks in portal/ directory (project root)
\copy temp_gem_plants FROM PROGRAM 'cmd /c type "..\..\..\portal\processed_gem_plants_data.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

-- Insert into staging table with validation
INSERT INTO vervestacks.staging_gem_plants (
    plant_name,
    country_area,
    iso_code,
    city,
    subnational_unit,
    type,
    technology,
    fuel,
    status,
    capacity_mw,
    latitude,
    longitude,
    start_year,
    year
)
SELECT 
    "Plant / Project name",
    "Country/area",
    iso_code,
    "City",
    "Subnational unit (state, province)",
    "Type",
    "Technology",
    "Fuel",
    "Status",
    "Capacity (MW)",
    "Latitude",
    "Longitude",
    CASE 
        WHEN "Start year" IS NULL OR "Start year" = '' OR LOWER(TRIM("Start year")) = 'not found' THEN 2015
        WHEN "Start year" ~ '^[0-9]+\.?[0-9]*$' THEN FLOOR("Start year"::NUMERIC)::INTEGER
        ELSE NULL
    END as start_year,
    NULL as year
FROM temp_gem_plants
WHERE iso_code IS NOT NULL 
  AND iso_code <> '' 
  AND "Status" IS NOT NULL 
  AND "Status" <> '';

-- Clear existing main table data
TRUNCATE TABLE vervestacks.gem_plants;

-- Process and load from staging to main table
-- This applies the model_fuel logic similar to Python processing
INSERT INTO vervestacks.gem_plants (
    plant_name,
    country_area,
    iso_code,
    city,
    subnational_unit,
    type,
    technology,
    fuel,
    status,
    capacity_mw,
    latitude,
    longitude,
    has_coordinates,
    start_year,
    year,
    age,
    type_mod,
    model_fuel,
    model_name
)
SELECT 
    sg.plant_name,
    sg.country_area,
    sg.iso_code,
    sg.city,
    sg.subnational_unit,
    sg.type,
    sg.technology,
    sg.fuel,
    sg.status,
    sg.capacity_mw,
    sg.latitude,
    sg.longitude,
    (sg.latitude IS NOT NULL AND sg.longitude IS NOT NULL) as has_coordinates,
    sg.start_year,
    sg.year,
    -- Calculate age with default start_year = 2015 if NULL/invalid, and clip to [0, 100]
    -- Matching Python: current_year - start_year.fillna(2015).clip(0, 100)
    LEAST(
        GREATEST(
            2025 - CASE 
                WHEN sg.start_year IS NULL OR sg.start_year NOT BETWEEN 1900 AND 2030 THEN 2015
                ELSE sg.start_year
            END,
            0
        ),
        100
    ) as age,
    -- Calculate type_mod (oil/gas splitting logic)
    CASE
        WHEN LOWER(sg.type) = 'oil/gas' THEN
            CASE
                WHEN sg.fuel IS NOT NULL AND LOWER(sg.fuel) LIKE 'fossil liquids:%' THEN 'oil'
                ELSE 'gas'
            END
        WHEN LOWER(sg.type) = 'hydropower' THEN 'hydro'
        ELSE sg.type
    END as type_mod,
    -- Get model_fuel from techmap or use fallback
    COALESCE(
        gtm.model_fuel,
        CASE
            WHEN LOWER(sg.type) = 'oil/gas' THEN
                CASE
                    WHEN sg.fuel IS NOT NULL AND LOWER(sg.fuel) LIKE 'fossil liquids:%' THEN 'oil'
                    ELSE 'gas'
                END
            WHEN LOWER(sg.type) = 'hydropower' THEN 'hydro'
            ELSE sg.type
        END
    ) as model_fuel,
    gtm.model_name
FROM vervestacks.staging_gem_plants sg
LEFT JOIN vervestacks.gem_techmap gtm ON 
    gtm.type_mod = CASE
        WHEN LOWER(sg.type) = 'oil/gas' THEN
            CASE
                WHEN sg.fuel IS NOT NULL AND LOWER(sg.fuel) LIKE 'fossil liquids:%' THEN 'oil'
                ELSE 'gas'
            END
        WHEN LOWER(sg.type) = 'hydropower' THEN 'hydro'
        ELSE sg.type
    END
    AND gtm.technology = COALESCE(sg.technology, sg.type)
WHERE sg.iso_code IS NOT NULL
  AND sg.status IS NOT NULL;

-- Update statistics
ANALYZE vervestacks.gem_plants;

-- Show import results
SELECT 
    'GEM Plants Import Complete!' as status,
    COUNT(*) as total_records,
    COUNT(DISTINCT iso_code) as countries,
    COUNT(DISTINCT status) as status_types,
    COUNT(DISTINCT model_fuel) as fuel_types,
    COUNT(*) FILTER (WHERE has_coordinates = TRUE) as mapped_plants,
    ROUND(SUM(capacity_mw) / 1000.0, 2) as total_capacity_gw
FROM vervestacks.gem_plants;

-- Show operating plants summary
SELECT 
    'Operating Plants Summary' as status,
    COUNT(*) as operating_plants,
    COUNT(DISTINCT iso_code) as countries,
    ROUND(SUM(capacity_mw) / 1000.0, 2) as total_capacity_gw,
    COUNT(*) FILTER (WHERE has_coordinates = TRUE) as mapped_plants
FROM vervestacks.gem_plants
WHERE LOWER(status) IN ('operating', 'construction');

