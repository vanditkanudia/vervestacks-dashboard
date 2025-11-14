-- Procedure: Get Capacity Evolution Data for Overview Tab
DROP FUNCTION IF EXISTS vervestacks.usp_get_capacity_evolution_data(VARCHAR(3));
-- Returns installed capacity data by fuel type for stacked area chart
-- Shows annual capacity evolution from 2000-2022

CREATE OR REPLACE FUNCTION vervestacks.usp_get_capacity_evolution_data(
    p_iso_code VARCHAR(3)
)
RETURNS TABLE (
    "FuelType" TEXT,
    "Year" INTEGER,
    "CapacityGW" NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        display_name::TEXT as fuel_type,
        year,
        COALESCE(capacity_gw, 0) as capacity_gw
    FROM vervestacks.energy_metrics_consolidated
    WHERE iso_code = p_iso_code
      AND year BETWEEN 2000 AND 2022
      AND fuel_name IN ('coal', 'gas', 'hydro', 'nuclear', 'oil', 'solar', 'windon', 'windoff', 'bioenergy')
    ORDER BY fuel_type, year;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION vervestacks.usp_get_capacity_evolution_data(VARCHAR(3)) TO postgres;

-- Add comment
COMMENT ON FUNCTION vervestacks.usp_get_capacity_evolution_data(VARCHAR(3)) IS 
'Returns installed capacity evolution data for Overview Tab stacked area chart. Shows capacity by fuel type from 2000-2022.';
