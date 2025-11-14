-- Procedure: Get Generation Trends Data for Overview Tab
DROP FUNCTION IF EXISTS vervestacks.usp_get_generation_trends_data(VARCHAR(3));
-- Returns electricity generation data by fuel type for stacked area chart
-- Shows annual generation trends from 2000-2022

CREATE OR REPLACE FUNCTION vervestacks.usp_get_generation_trends_data(
    p_iso_code VARCHAR(3)
)
RETURNS TABLE (
    "FuelType" TEXT,
    "Year" INTEGER,
    "GenerationTWh" NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        display_name::TEXT as fuel_type,
        year,
        COALESCE(generation_twh, 0) as generation_twh
    FROM vervestacks.energy_metrics_consolidated
    WHERE iso_code = p_iso_code
      AND year BETWEEN 2000 AND 2022
      AND fuel_name IN ('coal', 'gas', 'hydro', 'nuclear', 'oil', 'solar', 'windon', 'windoff', 'bioenergy')
    ORDER BY fuel_type, year;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION vervestacks.usp_get_generation_trends_data(VARCHAR(3)) TO postgres;

-- Add comment
COMMENT ON FUNCTION vervestacks.usp_get_generation_trends_data(VARCHAR(3)) IS 
'Returns electricity generation trends data for Overview Tab stacked area chart. Shows generation by fuel type from 2000-2022.';
