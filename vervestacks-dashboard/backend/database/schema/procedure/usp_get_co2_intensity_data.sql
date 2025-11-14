-- Procedure: Get CO2 Intensity Data for Overview Tab
DROP FUNCTION IF EXISTS vervestacks.usp_get_co2_intensity_data(VARCHAR(3));
-- Returns CO2 intensity data for country, region, and world levels
-- CO2 Intensity = (Total Fossil Emissions * 1000) / Total Generation (ALL fuels)
-- Units: kg CO2/MWh

CREATE OR REPLACE FUNCTION vervestacks.usp_get_co2_intensity_data(
    p_iso_code VARCHAR(3)
)
RETURNS TABLE (
    "Level" TEXT,
    "Year" INTEGER,
    "CO2Intensity" NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH emissions_data AS (
        -- Get total emissions from fossil fuels using consolidated table
        SELECT 
            iso_code,
            year,
            r10,
            SUM(emissions_mtco2) as total_emissions
        FROM vervestacks.energy_metrics_consolidated
        WHERE fuel_group = 'fossil'
          AND emissions_mtco2 > 0
          and year < 2023
        GROUP BY iso_code, year, r10
    ),
    generation_data AS (
        -- Get TOTAL generation from ALL fuels using consolidated table
        SELECT 
            iso_code,
            year,
            r10,
            SUM(generation_twh) as total_generation
        FROM vervestacks.energy_metrics_consolidated
        WHERE generation_twh > 0
        GROUP BY iso_code, year, r10
    ),
    combined_data AS (
        -- Combine emissions and generation data
        SELECT 
            e.iso_code,
            e.year,
            e.r10,
            e.total_emissions,
            g.total_generation
        FROM emissions_data e
        INNER JOIN generation_data g 
            ON e.iso_code = g.iso_code 
            AND e.year = g.year
    ),
    country_data AS (
        -- Country-level data
        SELECT 
            'ISO' as level,
            year,
            CASE 
                WHEN total_generation > 0 THEN (total_emissions * 1000) / total_generation
                ELSE 0
            END as co2_intensity
        FROM combined_data
        WHERE iso_code = p_iso_code
    ),
    region_data AS (
        -- Region-level data (average of all countries in the same region)
        SELECT 
            cd1.r10 as level,
            year,
            CASE 
                WHEN SUM(total_generation) > 0 THEN (SUM(total_emissions) * 1000) / SUM(total_generation)
                ELSE 0
            END as co2_intensity
        FROM combined_data cd1
        WHERE cd1.r10 = (SELECT r10 FROM combined_data WHERE iso_code = p_iso_code LIMIT 1)
        GROUP BY cd1.r10, year
    ),
    world_data AS (
        -- World-level data (average of all countries)
        SELECT 
            'World' as level,
            year,
            CASE 
                WHEN SUM(total_generation) > 0 THEN (SUM(total_emissions) * 1000) / SUM(total_generation)
                ELSE 0
            END as co2_intensity
        FROM combined_data
        GROUP BY year
    )
    -- Union all levels
    SELECT level, year, co2_intensity FROM country_data
    UNION ALL
    SELECT level, year, co2_intensity FROM region_data
    UNION ALL
    SELECT level, year, co2_intensity FROM world_data
    ORDER BY level, year;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION vervestacks.usp_get_co2_intensity_data(VARCHAR(3)) TO postgres;

-- Add comment
COMMENT ON FUNCTION vervestacks.usp_get_co2_intensity_data(VARCHAR(3)) IS 
'Returns CO2 intensity data for Overview Tab charts. Shows country, region, and world levels for comparison.';
