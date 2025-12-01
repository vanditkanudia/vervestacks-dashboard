-- Import ERA5 Combined Demand Profiles Data
-- This script imports hourly electricity demand profiles from era5_combined_data_2030.csv
-- Source: data/hourly_profiles/era5_combined_data_2030.csv
-- Expected columns: Country, time, region_name, MW, agg_region, demand_year, weather_year, Hour, Day, Month, mm_dd_hh

-- Set search path
SET search_path TO vervestacks, public;

-- ============================================================================
-- STEP 1: Create Temporary Staging Table
-- ============================================================================

DROP TABLE IF EXISTS temp_era5_import;

CREATE TEMP TABLE temp_era5_import (
    country VARCHAR(3),
    time TEXT,
    region_name TEXT,
    mw NUMERIC,
    agg_region TEXT,
    demand_year INTEGER,
    weather_year INTEGER,
    hour INTEGER,
    day INTEGER,
    month INTEGER,
    mm_dd_hh VARCHAR(15)
);

-- ============================================================================
-- STEP 2: Import CSV Data
-- ============================================================================

-- Note: Using PROGRAM 'type ...' for Windows compatibility (client-side \copy)
-- Path is relative to the backend/database directory
-- Full path: E:\py_projects\GitHub\VerveStacks\data\hourly_profiles\era5_combined_data_2030.csv
\COPY temp_era5_import FROM PROGRAM 'type ..\..\..\data\hourly_profiles\era5_combined_data_2030.csv' WITH (FORMAT CSV, HEADER TRUE, DELIMITER ',', NULL '');

-- Check import success
DO $$
DECLARE
    row_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO row_count FROM temp_era5_import;
    RAISE NOTICE '✓ CSV imported: % rows loaded into temp table', row_count;
END $$;

-- ============================================================================
-- STEP 3: Data Validation
-- ============================================================================

-- Check for NULL values in critical columns
DO $$
DECLARE
    null_country INTEGER;
    null_mw INTEGER;
    null_demand_year INTEGER;
    null_weather_year INTEGER;
    null_month INTEGER;
    null_day INTEGER;
    null_hour INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_country FROM temp_era5_import WHERE country IS NULL;
    SELECT COUNT(*) INTO null_mw FROM temp_era5_import WHERE mw IS NULL;
    SELECT COUNT(*) INTO null_demand_year FROM temp_era5_import WHERE demand_year IS NULL;
    SELECT COUNT(*) INTO null_weather_year FROM temp_era5_import WHERE weather_year IS NULL;
    SELECT COUNT(*) INTO null_month FROM temp_era5_import WHERE month IS NULL;
    SELECT COUNT(*) INTO null_day FROM temp_era5_import WHERE day IS NULL;
    SELECT COUNT(*) INTO null_hour FROM temp_era5_import WHERE hour IS NULL;
    
    RAISE NOTICE '✓ Validation - NULL checks:';
    RAISE NOTICE '  - Country NULL: % rows', null_country;
    RAISE NOTICE '  - MW NULL: % rows', null_mw;
    RAISE NOTICE '  - Demand Year NULL: % rows', null_demand_year;
    RAISE NOTICE '  - Weather Year NULL: % rows', null_weather_year;
    RAISE NOTICE '  - Month NULL: % rows', null_month;
    RAISE NOTICE '  - Day NULL: % rows', null_day;
    RAISE NOTICE '  - Hour NULL: % rows', null_hour;
END $$;

-- Check data ranges
DO $$
DECLARE
    invalid_month INTEGER;
    invalid_day INTEGER;
    invalid_hour INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_month FROM temp_era5_import WHERE month < 1 OR month > 12;
    SELECT COUNT(*) INTO invalid_day FROM temp_era5_import WHERE day < 1 OR day > 31;
    SELECT COUNT(*) INTO invalid_hour FROM temp_era5_import WHERE hour < 0 OR hour > 23;
    
    RAISE NOTICE '✓ Validation - Range checks:';
    RAISE NOTICE '  - Invalid Month (not 1-12): % rows', invalid_month;
    RAISE NOTICE '  - Invalid Day (not 1-31): % rows', invalid_day;
    RAISE NOTICE '  - Invalid Hour (not 0-23): % rows', invalid_hour;
END $$;

-- Show sample data
SELECT 
    '✓ Sample data (first 5 rows):' as info,
    country,
    demand_year,
    weather_year,
    month,
    day,
    hour,
    mw
FROM temp_era5_import 
LIMIT 5;

-- ============================================================================
-- STEP 4: Insert into Final Table
-- ============================================================================

-- Insert with ON CONFLICT to handle duplicates (update if exists)
INSERT INTO vervestacks.era5_combined_data_2030 
    (country, time, region_name, mw, agg_region, demand_year, weather_year, hour, day, month, mm_dd_hh)
SELECT 
    country,
    -- Parse time as timestamp (format: YYYY-MM-DD HH:MM:SS)
    CASE 
        WHEN time IS NOT NULL AND time != '' THEN 
            TO_TIMESTAMP(time, 'YYYY-MM-DD HH24:MI:SS')
        ELSE NULL
    END as time,
    region_name,
    mw,
    agg_region,
    demand_year,
    weather_year,
    hour,
    day,
    month,
    mm_dd_hh
FROM temp_era5_import
WHERE country IS NOT NULL 
  -- Note: mw IS NOT NULL is intentionally omitted to allow NULL values
  -- This prevents holes in profiles (missing hours). NULLs are converted to 0 in stored procedures.
  AND demand_year IS NOT NULL
  AND weather_year IS NOT NULL
  AND month IS NOT NULL
  AND day IS NOT NULL
  AND hour IS NOT NULL
ON CONFLICT (country, demand_year, weather_year, month, day, hour) 
DO UPDATE SET 
    mw = EXCLUDED.mw,
    time = EXCLUDED.time,
    region_name = EXCLUDED.region_name,
    agg_region = EXCLUDED.agg_region,
    mm_dd_hh = EXCLUDED.mm_dd_hh;

-- ============================================================================
-- STEP 5: Report Results
-- ============================================================================

-- Count final records
DO $$
DECLARE
    total_records INTEGER;
    unique_countries INTEGER;
    unique_demand_years INTEGER;
    unique_weather_years INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_records FROM vervestacks.era5_combined_data_2030;
    SELECT COUNT(DISTINCT country) INTO unique_countries FROM vervestacks.era5_combined_data_2030;
    SELECT COUNT(DISTINCT demand_year) INTO unique_demand_years FROM vervestacks.era5_combined_data_2030;
    SELECT COUNT(DISTINCT weather_year) INTO unique_weather_years FROM vervestacks.era5_combined_data_2030;
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE '✓ ERA5 Demand Profiles Import Complete';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total records: %', total_records;
    RAISE NOTICE 'Unique countries: %', unique_countries;
    RAISE NOTICE 'Unique demand years: %', unique_demand_years;
    RAISE NOTICE 'Unique weather years: %', unique_weather_years;
    RAISE NOTICE '';
END $$;

-- Show sample statistics by country
SELECT 
    '✓ Sample statistics by country (top 5):' as info,
    country,
    COUNT(*) as total_hours,
    MIN(mw) as min_demand_mw,
    MAX(mw) as max_demand_mw,
    AVG(mw)::NUMERIC(10,2) as avg_demand_mw
FROM vervestacks.era5_combined_data_2030
GROUP BY country
ORDER BY total_hours DESC
LIMIT 5;

-- ============================================================================
-- STEP 6: Cleanup
-- ============================================================================

DROP TABLE IF EXISTS temp_era5_import;

SELECT '✓ Import script completed successfully!' as status;

