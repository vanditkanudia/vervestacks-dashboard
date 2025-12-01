-- Procedure: Get Transmission Generation Plants Data for Dashboard
-- Returns generation plants data for a specific ISO code
-- Matches the structure from dashboard_data_analyzer.py get_transmission_generation_data()

DROP FUNCTION IF EXISTS vervestacks.usp_get_transmission_generation_plants(VARCHAR(3));

CREATE OR REPLACE FUNCTION vervestacks.usp_get_transmission_generation_plants(
    p_iso_code VARCHAR(3)
)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
    v_plants_data JSONB;
    v_statistics JSONB;
    v_fuel_type_counts JSONB;
    v_total_capacity NUMERIC;
    v_total_plants INTEGER;
BEGIN
    -- Validate ISO code
    IF p_iso_code IS NULL OR LENGTH(p_iso_code) != 3 THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', 'Invalid ISO code. Must be 3 characters.'
        );
    END IF;

    -- Check if data exists for this ISO
    IF NOT EXISTS (
        SELECT 1 
        FROM vervestacks.transmission_generation_plants 
        WHERE iso_code = UPPER(p_iso_code)
    ) THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', format('Generation data file not found for %s', UPPER(p_iso_code))
        );
    END IF;

    -- Get plants data (for map visualization)
    -- Match the structure from Python service
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'id', COALESCE(comm_out, 'plant_' || id::TEXT),
            'name', COALESCE(plant_name, 'Unknown Plant'),
            'capacity_mw', capacity_mw,
            'fuel_type', COALESCE(fuel_type, 'unknown'),
            'lat', latitude,
            'lng', longitude,
            'bus_id', COALESCE(bus_id, ''),
            'description', COALESCE(description, ''),
            'comm_id', COALESCE(comm_id, ''),
            'type', 'power_plant'
        )
        ORDER BY capacity_mw DESC NULLS LAST
    ), '[]'::jsonb) INTO v_plants_data
    FROM vervestacks.transmission_generation_plants
    WHERE iso_code = UPPER(p_iso_code)
      AND has_coordinates = TRUE;

    -- Calculate fuel type counts
    SELECT COALESCE(jsonb_object_agg(
        fuel_type, 
        plant_count
    ), '{}'::jsonb) INTO v_fuel_type_counts
    FROM (
        SELECT 
            COALESCE(fuel_type, 'unknown') as fuel_type,
            COUNT(*) as plant_count
        FROM vervestacks.transmission_generation_plants
        WHERE iso_code = UPPER(p_iso_code)
          AND has_coordinates = TRUE
        GROUP BY fuel_type
    ) fuel_counts;

    -- Calculate total capacity and plant count
    SELECT 
        COALESCE(SUM(capacity_mw), 0) as total_capacity,
        COUNT(*) as total_plants
    INTO v_total_capacity, v_total_plants
    FROM vervestacks.transmission_generation_plants
    WHERE iso_code = UPPER(p_iso_code)
      AND has_coordinates = TRUE;

    -- Build statistics object
    v_statistics := jsonb_build_object(
        'total_plants', v_total_plants,
        'total_capacity_mw', v_total_capacity,
        'fuel_types', v_fuel_type_counts,
        'iso_code', UPPER(p_iso_code)
    );

    -- Build generation data object (matches Python service structure)
    v_result := jsonb_build_object(
        'iso_code', UPPER(p_iso_code),
        'plants', COALESCE(v_plants_data, '[]'::jsonb),
        'statistics', v_statistics
    );

    -- Return success response (matches Python service structure)
    RETURN jsonb_build_object(
        'success', true,
        'data', v_result,
        'error', NULL
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', format('Database error: %s', SQLERRM)
        );
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION vervestacks.usp_get_transmission_generation_plants(VARCHAR(3)) TO PUBLIC;

