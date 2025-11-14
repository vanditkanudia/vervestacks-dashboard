DROP FUNCTION IF EXISTS vervestacks.usp_get_fuel_colors();

-- Returns fuel colors from fuels table
-- Columns: fuel_name, display_name, color
CREATE OR REPLACE FUNCTION vervestacks.usp_get_fuel_colors()
RETURNS TABLE (
    "fuel_name" TEXT,
    "display_name" TEXT,
    "color" TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        f.fuel_name::TEXT,
        f.display_name::TEXT,
        f.color::TEXT
    FROM vervestacks.fuels f
    WHERE f.fuel_name IS NOT NULL AND f.color IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- Optional: privileges
GRANT EXECUTE ON FUNCTION vervestacks.usp_get_fuel_colors() TO postgres;

