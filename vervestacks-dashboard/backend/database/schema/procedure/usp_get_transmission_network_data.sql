-- Procedure: Get Transmission Network Data (Buses + Lines)
-- Returns JSON structure matching legacy Python service response

DROP FUNCTION IF EXISTS vervestacks.usp_get_transmission_network_data(VARCHAR(3));

CREATE OR REPLACE FUNCTION vervestacks.usp_get_transmission_network_data(
    p_iso_code VARCHAR(3)
)
RETURNS JSONB AS $$
DECLARE
    v_iso3 VARCHAR(3);
    v_buses JSONB;
    v_lines JSONB;
    v_statistics JSONB;
    v_total_buses INTEGER := 0;
    v_total_lines INTEGER := 0;
    v_bus_voltage_levels JSONB := '{}'::jsonb;
    v_line_voltage_levels JSONB := '{}'::jsonb;
BEGIN
    -- Validate ISO code
    IF p_iso_code IS NULL OR LENGTH(TRIM(p_iso_code)) <> 3 THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', 'Invalid ISO code. Must be 3 characters.'
        );
    END IF;

    v_iso3 := UPPER(TRIM(p_iso_code));

    -- Retrieve buses for the country using ISO3 code directly
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'id', bus_id,
            'name', bus_id,
            'lat', latitude,
            'lng', longitude,
            'voltage', voltage,
            'type', 'transmission_bus'
        )
        ORDER BY COALESCE(voltage, 0) DESC, bus_id
    ), '[]'::jsonb),
    COUNT(*) AS total_buses
    INTO v_buses, v_total_buses
    FROM vervestacks.transmission_buses
    WHERE iso3_code = v_iso3;

    IF v_total_buses = 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', format('No transmission buses found for %s', v_iso3)
        );
    END IF;

    -- Retrieve lines (only when both buses exist and share the same country)
    WITH line_data AS (
        SELECT
            l.line_id,
            l.bus0_id,
            l.bus1_id,
            l.voltage,
            l.s_nom,
            l.length_km,
            l.geometry,
            b0.latitude AS bus0_lat,
            b0.longitude AS bus0_lng,
            b1.latitude AS bus1_lat,
            b1.longitude AS bus1_lng
        FROM vervestacks.transmission_lines l
        JOIN vervestacks.transmission_buses b0 ON b0.bus_id = l.bus0_id
        JOIN vervestacks.transmission_buses b1 ON b1.bus_id = l.bus1_id
        WHERE l.iso3_code = v_iso3
    )
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'id', line_id,
            'bus0_id', bus0_id,
            'bus1_id', bus1_id,
            'bus0_lat', bus0_lat,
            'bus0_lng', bus0_lng,
            'bus1_lat', bus1_lat,
            'bus1_lng', bus1_lng,
            'voltage', voltage,
            'capacity', s_nom,
            'length', length_km,
            'geometry', geometry,
            'type', 'transmission_line'
        )
        ORDER BY COALESCE(voltage, 0) DESC, line_id
    ), '[]'::jsonb),
    COUNT(*) AS total_lines
    INTO v_lines, v_total_lines
    FROM line_data;

    -- Voltage distribution for buses
    SELECT COALESCE(jsonb_object_agg(voltage_label, cnt), '{}'::jsonb)
    INTO v_bus_voltage_levels
    FROM (
        SELECT
            format('%skV', TRIM(TO_CHAR(voltage::NUMERIC, 'FM999999999'))) AS voltage_label,
            COUNT(*) AS cnt
        FROM vervestacks.transmission_buses
        WHERE iso3_code = v_iso3
          AND voltage IS NOT NULL
          AND voltage > 0
        GROUP BY voltage_label
    ) t;

    -- Voltage distribution for lines
    SELECT COALESCE(jsonb_object_agg(voltage_label, cnt), '{}'::jsonb)
    INTO v_line_voltage_levels
    FROM (
        SELECT
            format('%skV', TRIM(TO_CHAR(voltage::NUMERIC, 'FM999999999'))) AS voltage_label,
            COUNT(*) AS cnt
        FROM vervestacks.transmission_lines
        WHERE iso3_code = v_iso3
          AND voltage IS NOT NULL
          AND voltage > 0
        GROUP BY voltage_label
    ) t;

    -- Build statistics
    v_statistics := jsonb_build_object(
        'total_buses', v_total_buses,
        'total_lines', v_total_lines,
        'voltage_levels', v_bus_voltage_levels,
        'line_voltage_levels', v_line_voltage_levels,
        'iso_code', v_iso3
    );

    -- Build success payload
    RETURN jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'iso_code', v_iso3,
            'buses', v_buses,
            'lines', v_lines,
            'statistics', v_statistics
        ),
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

GRANT EXECUTE ON FUNCTION vervestacks.usp_get_transmission_network_data(VARCHAR(3)) TO PUBLIC;

