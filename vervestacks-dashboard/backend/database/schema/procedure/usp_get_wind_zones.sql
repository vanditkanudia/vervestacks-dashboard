-- Procedure: Get Wind Renewable Zones for Dashboard (Onshore or Offshore)
-- Returns wind zone data matching the Python service response format
-- Replicates the logic from dashboard_data_analyzer.py get_wind_renewable_zones()

DROP FUNCTION IF EXISTS vervestacks.usp_get_wind_zones(VARCHAR(3), VARCHAR(10));

CREATE OR REPLACE FUNCTION vervestacks.usp_get_wind_zones(
    p_iso_code VARCHAR(3),
    p_wind_type VARCHAR(10) DEFAULT 'onshore'
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
    v_wind_table TEXT;
    v_cost_tech TEXT;
BEGIN
    -- Validate ISO code
    IF p_iso_code IS NULL OR LENGTH(p_iso_code) != 3 THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', 'Invalid ISO code. Must be 3 characters.'
        );
    END IF;

    -- Validate wind_type
    IF p_wind_type NOT IN ('onshore', 'offshore') THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', 'Invalid wind_type. Must be "onshore" or "offshore".'
        );
    END IF;

    -- Set table and tech based on wind_type
    IF p_wind_type = 'offshore' THEN
        v_wind_table := 'renewable_zones_wind_offshore';
        v_cost_tech := 'windoff';
    ELSE
        v_wind_table := 'renewable_zones_wind_onshore';
        v_cost_tech := 'windon';
    END IF;

    -- Check if data exists for this ISO (using dynamic SQL for table name)
    EXECUTE format('
        SELECT COUNT(*) 
        FROM vervestacks.%I 
        WHERE UPPER(iso) = $1',
        v_wind_table
    ) USING UPPER(p_iso_code) INTO v_total_cells;

    IF v_total_cells = 0 THEN
        v_statistics := jsonb_build_object(
            'iso', UPPER(p_iso_code),
            'wind_type', p_wind_type,
            'total_cells', 0,
            'total_capacity_mw', 0,
            'total_generation_gwh', 0,
            'avg_capacity_factor', 0,
            'avg_lcoe', 0,
            'total_suitable_area_km2', 0,
            'cost_data_available', false,
            'investment_cost_usd_kw', NULL,
            'fixed_om_usd_kw', NULL,
            'data_source', format('Atlite %s Wind (High-resolution ERA5 weather data)', INITCAP(p_wind_type)),
            'capacity_factor_quality', 'High-resolution, technology-specific modeling'
        );

        RETURN jsonb_build_object(
            'success', true,
            'data', jsonb_build_object(
                'grid_data', '[]'::jsonb,
                'statistics', v_statistics,
                'costs', '[]'::jsonb
            )
        );
    END IF;

    -- Calculate statistics (using dynamic SQL)
    EXECUTE format('
        SELECT 
            COUNT(*)::INTEGER,
            COALESCE(SUM(installed_capacity_potential_mw), 0),
            COALESCE(SUM(generation_potential_gwh), 0),
            COALESCE(AVG(capacity_factor), 0),
            COALESCE(AVG(lcoe_usd_mwh), 0),
            COALESCE(SUM(suitable_area_km2), 0)
        FROM vervestacks.%I
        WHERE UPPER(iso) = $1
          AND installed_capacity_potential_mw >= 1.0',
        v_wind_table
    ) USING UPPER(p_iso_code)
    INTO v_total_cells, v_total_capacity_mw, v_total_generation_gwh, 
         v_avg_capacity_factor, v_avg_lcoe, v_total_suitable_area_km2;

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
      AND tech = v_cost_tech;

    -- Build grid_data array with geometry as GeoJSON (using dynamic SQL)
    -- Handle NULL case when no rows found
    EXECUTE format('
        SELECT COALESCE(
            jsonb_agg(
                jsonb_build_object(
                    ''id'', id,
                    ''grid_cell'', grid_cell,
                    ''lat'', lat,
                    ''lng'', lng,
                    ''Capacity Factor'', capacity_factor,
                    ''Installed Capacity Potential (MW)'', installed_capacity_potential_mw,
                    ''LCOE (USD/MWh)'', lcoe_usd_mwh,
                    ''Suitable Area (km²)'', suitable_area_km2,
                    ''Zone Score'', zone_score,
                    ''Total_Generation_GWh'', generation_potential_gwh,
                    ''geometry'', CASE 
                        WHEN geometry_json IS NOT NULL AND geometry_json != '''' 
                        THEN geometry_json::jsonb 
                        ELSE NULL 
                    END
                )
            ),
            ''[]''::jsonb
        )
        FROM (
            SELECT id, grid_cell, lat, lng, capacity_factor, 
                   installed_capacity_potential_mw, lcoe_usd_mwh, 
                   suitable_area_km2, zone_score, generation_potential_gwh, 
                   geometry_json
            FROM vervestacks.%I
            WHERE UPPER(iso) = $1
              AND installed_capacity_potential_mw >= 1.0
              AND geometry_json IS NOT NULL
              AND geometry_json != ''''
            ORDER BY capacity_factor DESC NULLS LAST
        ) subq',
        v_wind_table
    ) USING UPPER(p_iso_code) INTO v_grid_data;

    -- Ensure v_grid_data is not NULL
    v_grid_data := COALESCE(v_grid_data, '[]'::jsonb);

    -- Build statistics object (handle empty cost data safely)
    v_statistics := jsonb_build_object(
        'iso', UPPER(p_iso_code),
        'wind_type', p_wind_type,
        'total_cells', COALESCE(v_total_cells, 0),
        'total_capacity_mw', ROUND(COALESCE(v_total_capacity_mw, 0)::numeric, 2),
        'total_generation_gwh', ROUND(COALESCE(v_total_generation_gwh, 0)::numeric, 2),
        'avg_capacity_factor', ROUND(COALESCE(v_avg_capacity_factor, 0)::numeric, 4),
        'avg_lcoe', ROUND(COALESCE(v_avg_lcoe, 0)::numeric, 2),
        'total_suitable_area_km2', ROUND(COALESCE(v_total_suitable_area_km2, 0)::numeric, 2),
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
        'data_source', format('Atlite %s Wind (High-resolution ERA5 weather data)', INITCAP(p_wind_type)),
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
            'error', format('Failed to get wind renewable zones: %s', SQLERRM)
        );
END;
$$ LANGUAGE plpgsql;

