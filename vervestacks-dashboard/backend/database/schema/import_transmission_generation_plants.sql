-- Import Transmission Generation Plants Data into VerveStacks Database
-- This script handles the complete import process for transmission generation plants data
-- Follows the same structure as import_gem_plants.sql

-- Clear existing staging data
DELETE FROM vervestacks.staging_transmission_generation_plants;

-- Import transmission generation plants data
-- Use all TEXT columns in temp table to avoid COPY parsing errors
-- IMPORTANT: Column order must match CSV file order exactly
DROP TABLE IF EXISTS temp_transmission_gen_plants;
CREATE TEMP TABLE temp_transmission_gen_plants (
    iso_code TEXT,  -- First column in CSV
    "comm-out" TEXT,
    "model_name" TEXT,
    "Capacity (MW)" TEXT,  -- TEXT first, convert to NUMERIC later
    "model_fuel" TEXT,
    "model_description" TEXT,
    "comm_id" TEXT,
    "bus_id" TEXT,
    "Latitude" TEXT,  -- TEXT first, convert to NUMERIC later
    "Longitude" TEXT,  -- TEXT first, convert to NUMERIC later
    "is_new_tech" TEXT
);

-- Import CSV data using PROGRAM mode for robust file access
-- CSV file should be in backend/database/data/ directory
\copy temp_transmission_gen_plants FROM PROGRAM 'cmd /c type "data\transmission_generation_plants_consolidated.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8', QUOTE '"', ESCAPE '"');

-- Insert into staging table with validation and type conversion
-- Use CTE to safely convert types before filtering
WITH converted_data AS (
    SELECT 
        "comm-out",
        "model_name",
        -- Convert Capacity to NUMERIC, filter out invalid values
        CASE 
            WHEN TRIM("Capacity (MW)") ~ '^[0-9]+(\.[0-9]+)?$' THEN TRIM("Capacity (MW)")::NUMERIC
            ELSE NULL
        END as capacity_mw,
        "model_fuel",
        "model_description",
        "comm_id",
        "bus_id",
        -- Convert Latitude to NUMERIC, filter out invalid values
        CASE 
            WHEN TRIM("Latitude") ~ '^-?[0-9]+(\.[0-9]+)?$' THEN TRIM("Latitude")::NUMERIC
            ELSE NULL
        END as latitude,
        -- Convert Longitude to NUMERIC, filter out invalid values
        CASE 
            WHEN TRIM("Longitude") ~ '^-?[0-9]+(\.[0-9]+)?$' THEN TRIM("Longitude")::NUMERIC
            ELSE NULL
        END as longitude,
        "is_new_tech",
        UPPER(TRIM(iso_code)) as iso_code
    FROM temp_transmission_gen_plants
    WHERE iso_code IS NOT NULL 
      AND TRIM(iso_code) <> ''
      AND LENGTH(TRIM(iso_code)) = 3
      -- Validate that Latitude and Longitude are valid numeric strings before conversion
      -- Handle negative numbers, decimals, and optional leading/trailing spaces
      AND TRIM("Latitude") ~ '^-?[0-9]+(\.[0-9]+)?$'
      AND TRIM("Longitude") ~ '^-?[0-9]+(\.[0-9]+)?$'
)
INSERT INTO vervestacks.staging_transmission_generation_plants (
    "comm-out",
    "model_name",
    "Capacity (MW)",
    "model_fuel",
    "model_description",
    "comm_id",
    "bus_id",
    "Latitude",
    "Longitude",
    "is_new_tech",
    iso_code
)
SELECT 
    "comm-out",
    "model_name",
    capacity_mw as "Capacity (MW)",
    "model_fuel",
    "model_description",
    "comm_id",
    "bus_id",
    latitude as "Latitude",
    longitude as "Longitude",
    "is_new_tech",
    iso_code
FROM converted_data
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
  AND latitude != 0
  AND longitude != 0;

-- Clear existing main table data (optional - comment out if you want to keep existing data)
-- DELETE FROM vervestacks.transmission_generation_plants;

-- Insert into main table with data transformation
INSERT INTO vervestacks.transmission_generation_plants (
    iso_code,
    plant_name,
    comm_out,
    comm_id,
    bus_id,
    capacity_mw,
    fuel_type,
    description,
    is_new_tech,
    latitude,
    longitude,
    has_coordinates
)
SELECT 
    UPPER(TRIM(iso_code)) as iso_code,
    "model_name" as plant_name,
    "comm-out" as comm_out,
    "comm_id",
    "bus_id",
    "Capacity (MW)" as capacity_mw,
    LOWER(TRIM("model_fuel")) as fuel_type,
    "model_description" as description,
    CASE 
        WHEN LOWER(TRIM("is_new_tech")) IN ('true', '1', 'yes', 't') THEN TRUE
        WHEN LOWER(TRIM("is_new_tech")) IN ('false', '0', 'no', 'f', '') THEN FALSE
        ELSE NULL
    END as is_new_tech,
    "Latitude" as latitude,
    "Longitude" as longitude,
    CASE 
        WHEN "Latitude" IS NOT NULL 
         AND "Longitude" IS NOT NULL 
         AND "Latitude" != 0 
         AND "Longitude" != 0 
        THEN TRUE
        ELSE FALSE
    END as has_coordinates
FROM vervestacks.staging_transmission_generation_plants
WHERE iso_code IS NOT NULL
  AND iso_code <> '';

-- Show import statistics
SELECT 
    'Transmission Generation Plants Import Complete!' as status,
    COUNT(*) as total_plants_imported,
    COUNT(DISTINCT iso_code) as countries_imported
FROM vervestacks.transmission_generation_plants;

