-- Procedure: Get Utilization Factor Data for Overview Tab
DROP FUNCTION IF EXISTS vervestacks.usp_get_utilization_factor_data(VARCHAR(3));
-- Returns fossil fuel utilization factor data for country, region, and world levels
-- Utilization Factor = Total Fossil Generation / Total Fossil Capacity / 8.76

CREATE OR REPLACE FUNCTION vervestacks.usp_get_utilization_factor_data(
    p_iso_code VARCHAR(3)
)
RETURNS TABLE (
    "Level" TEXT,
    "Year" INTEGER,
    "UtilizationFactor" NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH fossil_data AS (
        -- Filter for fossil fuels only using consolidated table
        SELECT 
            iso_code,
            year,
            r10,
            SUM(generation_twh) as total_generation,
            SUM(capacity_gw) as total_capacity
        FROM vervestacks.energy_metrics_consolidated
        WHERE fuel_group = 'fossil'
          AND generation_twh > 0 
          AND capacity_gw > 0
        GROUP BY iso_code, year, r10
    ),
    country_data AS (
        -- Country-level data
        SELECT 
            'ISO' as level,
            year,
            CASE 
                WHEN total_capacity > 0 THEN total_generation / total_capacity / 8.76
                ELSE 0
            END as utilization_factor
        FROM fossil_data
        WHERE iso_code = p_iso_code
    ),
    region_data AS (
        -- Region-level data (average of all countries in the same region)
        SELECT 
            fd1.r10 as level,
            year,
            CASE 
                WHEN SUM(total_capacity) > 0 THEN SUM(total_generation) / SUM(total_capacity) / 8.76
                ELSE 0
            END as utilization_factor
        FROM fossil_data fd1
        WHERE fd1.r10 = (SELECT r10 FROM fossil_data WHERE iso_code = p_iso_code LIMIT 1)
        GROUP BY fd1.r10, year
    ),
    world_data AS (
        -- World-level data (average of all countries)
        SELECT 
            'World' as level,
            year,
            CASE 
                WHEN SUM(total_capacity) > 0 THEN SUM(total_generation) / SUM(total_capacity) / 8.76
                ELSE 0
            END as utilization_factor
        FROM fossil_data
        GROUP BY year
    )
    -- Union all levels
    SELECT level, year, utilization_factor FROM country_data
    UNION ALL
    SELECT level, year, utilization_factor FROM region_data
    UNION ALL
    SELECT level, year, utilization_factor FROM world_data
    ORDER BY level, year;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION vervestacks.usp_get_utilization_factor_data(VARCHAR(3)) TO postgres;

-- Add comment
COMMENT ON FUNCTION vervestacks.usp_get_utilization_factor_data(VARCHAR(3)) IS 
'Returns fossil fuel utilization factor data for Overview Tab charts. Shows country, region, and world levels for comparison.';
