-- ============================================================================
-- Stored Procedure: usp_get_demand_profile
-- ============================================================================
-- Returns hourly demand profile (8760 hours) for a country
-- Input: 2-letter country code, demand_year, weather_year
-- Output: Array of 8760 MW values in chronological order (month, day, hour)
-- Note: NULL values in mw column are converted to 0 to maintain profile integrity
-- ============================================================================

SET search_path TO vervestacks, public;

CREATE OR REPLACE FUNCTION vervestacks.usp_get_demand_profile(
    p_country_code VARCHAR(3),
    p_demand_year INTEGER DEFAULT 2030,
    p_weather_year INTEGER DEFAULT 2013
)
RETURNS NUMERIC[]
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    profile NUMERIC[];
    row_count INTEGER;
BEGIN
    -- Extract demand profile as array, ordered by month, day, hour
    -- This guarantees chronological ordering: Jan 1 00:00 -> Dec 31 23:00
    -- COALESCE converts NULL values to 0 to maintain 8760-hour profile integrity
    SELECT 
        array_agg(COALESCE(mw, 0) ORDER BY month, day, hour)
    INTO profile
    FROM vervestacks.era5_combined_data_2030
    WHERE country = p_country_code
      AND weather_year = 2013;
    --   AND demand_year = p_demand_year
    
    -- Validate result
    IF profile IS NULL THEN
        RAISE EXCEPTION 'No demand data found for country: %, demand_year: %, weather_year: %', 
            p_country_code, p_demand_year, 2013;
    END IF;
    
    -- Verify we have exactly 8760 hours
    row_count := array_length(profile, 1);
    IF row_count != 8760 THEN
        RAISE WARNING 'Expected 8760 hours, got % hours for country: %', row_count, p_country_code;
    END IF;
    
    RETURN profile;
END;
$$;

COMMENT ON FUNCTION vervestacks.usp_get_demand_profile IS 
    'Returns 8760-hour demand profile array (MW) for a country, ordered chronologically by month, day, hour. NULL values are automatically converted to 0 to maintain profile integrity.';

-- Show completion
SELECT 'Stored procedure usp_get_demand_profile created successfully!' as status;

