-- Procedure: Get Solar Renewable Zones for Dashboard
-- Returns solar zone data matching the Python service response format
-- Replicates the logic from dashboard_data_analyzer.py get_solar_renewable_zones()

DROP FUNCTION IF EXISTS vervestacks.usp_get_solar_zones(VARCHAR(3));

CREATE OR REPLACE FUNCTION vervestacks.usp_get_solar_zones(
    p_iso_code VARCHAR(3)
)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
    v_grid_data JSONB;
    v_statistics JSONB;
    v_costs JSONB;
    v_total_cells INTEGER;
    v_total_capacity_mw NUMERIC;
    v_total_generation_gwh NUMERIC;
    v_avg_capacity_factor NUMERIC;
    v_avg_lcoe NUMERIC;
    v_total_suitable_area_km2 NUMERIC;
    v_cost_data JSONB;
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
    SELECT COUNT(*) INTO v_total_cells
    FROM vervestacks.renewable_zones_solar
    WHERE UPPER(iso) = UPPER(p_iso_code);

    IF v_total_cells = 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', format('No solar zones found for ISO code: %s', p_iso_code)
        );
    END IF;

    -- Calculate statistics
    SELECT 
        COUNT(*)::INTEGER,
        COALESCE(SUM(installed_capacity_potential_mw), 0),
        COALESCE(SUM(generation_potential_gwh), 0),
        COALESCE(AVG(capacity_factor), 0),
        COALESCE(AVG(lcoe_usd_mwh), 0),
        COALESCE(SUM(suitable_area_km2), 0)
    INTO 
        v_total_cells,
        v_total_capacity_mw,
        v_total_generation_gwh,
        v_avg_capacity_factor,
        v_avg_lcoe,
        v_total_suitable_area_km2
    FROM vervestacks.renewable_zones_solar
    WHERE UPPER(iso) = UPPER(p_iso_code)
      AND installed_capacity_potential_mw >= 1.0;  -- Filter by minimum capacity (1MW)

    -- Get cost data (handle NULL case when no rows found)
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'iso', iso,
                'tech', tech,
                'invcost', invcost,
                'fixom', fixom
            )
        ),
        '[]'::jsonb
    )
    INTO v_cost_data
    FROM vervestacks.renewable_zone_costs
    WHERE UPPER(iso) = UPPER(p_iso_code)
      AND tech = 'solarpv';

    -- Build grid_data array with geometry as GeoJSON (handle NULL case)
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'id', id,
                'grid_cell', grid_cell,
                'lat', lat,
                'lng', lng,
                'Capacity Factor', capacity_factor,
                'Installed Capacity Potential (MW)', installed_capacity_potential_mw,
                'LCOE (USD/MWh)', lcoe_usd_mwh,
                'Suitable Area (km²)', suitable_area_km2,
                'Zone Score', zone_score,
                'Total_Generation_GWh', generation_potential_gwh,
                'geometry', CASE 
                    WHEN geometry_json IS NOT NULL AND geometry_json != '' 
                    THEN geometry_json::jsonb 
                    ELSE NULL 
                END
            )
            ORDER BY capacity_factor DESC NULLS LAST
        ),
        '[]'::jsonb
    )
    INTO v_grid_data
    FROM vervestacks.renewable_zones_solar
    WHERE UPPER(iso) = UPPER(p_iso_code)
      AND installed_capacity_potential_mw >= 1.0
      AND geometry_json IS NOT NULL
      AND geometry_json != '';

    -- Ensure v_grid_data is not NULL
    v_grid_data := COALESCE(v_grid_data, '[]'::jsonb);

    -- Build statistics object
    v_statistics := jsonb_build_object(
        'iso', UPPER(p_iso_code),
        'total_cells', v_total_cells,
        'total_capacity_mw', ROUND(v_total_capacity_mw::numeric, 2),
        'total_generation_gwh', ROUND(v_total_generation_gwh::numeric, 2),
        'avg_capacity_factor', ROUND(v_avg_capacity_factor::numeric, 4),
        'avg_lcoe', ROUND(v_avg_lcoe::numeric, 2),
        'total_suitable_area_km2', ROUND(v_total_suitable_area_km2::numeric, 2),
        'cost_data_available', (v_cost_data IS NOT NULL AND jsonb_typeof(v_cost_data) = 'array' AND jsonb_array_length(v_cost_data) > 0),
        'investment_cost_usd_kw', CASE 
            WHEN v_cost_data IS NOT NULL 
                 AND jsonb_typeof(v_cost_data) = 'array' 
                 AND jsonb_array_length(v_cost_data) > 0 
            THEN (v_cost_data->0->>'invcost')::numeric 
            ELSE NULL 
        END,
        'fixed_om_usd_kw', CASE 
            WHEN v_cost_data IS NOT NULL 
                 AND jsonb_typeof(v_cost_data) = 'array' 
                 AND jsonb_array_length(v_cost_data) > 0 
            THEN (v_cost_data->0->>'fixom')::numeric 
            ELSE NULL 
        END,
        'data_source', 'Atlite (High-resolution ERA5 weather data)',
        'capacity_factor_quality', 'High-resolution, technology-specific modeling'
    );

    -- Build costs array (use empty array if no data)
    v_costs := COALESCE(v_cost_data, '[]'::jsonb);

    -- Build final result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'grid_data', COALESCE(v_grid_data, '[]'::jsonb),
            'statistics', v_statistics,
            'costs', v_costs
        )
    );

    RETURN v_result;

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', format('Failed to get solar renewable zones: %s', SQLERRM)
        );
END;
$$ LANGUAGE plpgsql;

