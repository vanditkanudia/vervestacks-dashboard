-- Procedure: Get Existing Stock Metrics for Dashboard
-- Returns processed existing stock data for a specific ISO code
-- Replicates the logic from dashboard_data_analyzer.py get_existing_stock_metrics()

DROP FUNCTION IF EXISTS vervestacks.usp_get_existing_stock_metrics(VARCHAR(3));

CREATE OR REPLACE FUNCTION vervestacks.usp_get_existing_stock_metrics(
    p_iso_code VARCHAR(3)
)
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
    v_metadata JSONB;
    v_plants_data JSONB;
    v_capacity_by_tech JSONB;
    v_status_dist JSONB;
    v_histograms JSONB;
    v_current_year INTEGER := 2025;
    v_statuses_to_keep TEXT[] := ARRAY['operating', 'construction'];
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
    IF NOT EXISTS (SELECT 1 FROM vervestacks.gem_plants WHERE iso_code = p_iso_code) THEN
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', format('No GEM data found for ISO code: %s', p_iso_code)
        );
    END IF;

    -- Create temp table with filtered data for this ISO code (performance optimization)
    -- Drop if exists (in case of previous error)
    DROP TABLE IF EXISTS temp_gem_iso;
    
    CREATE TEMP TABLE temp_gem_iso AS
    SELECT *
    FROM vervestacks.gem_plants
    WHERE iso_code = p_iso_code;

    -- Create index on temp table for better performance
    CREATE INDEX idx_temp_gem_iso_status ON temp_gem_iso(status);
    CREATE INDEX idx_temp_gem_iso_model_fuel ON temp_gem_iso(model_fuel);
    CREATE INDEX idx_temp_gem_iso_coords ON temp_gem_iso(has_coordinates);

    -- Calculate metadata
    WITH operating_plants AS (
        SELECT 
            COUNT(*) as plant_count,
            COALESCE(SUM(capacity_mw), 0) / 1000.0 as total_capacity_gw,
            COUNT(*) FILTER (WHERE has_coordinates = TRUE) as mapped_count
        FROM temp_gem_iso
        WHERE LOWER(status) = ANY(v_statuses_to_keep)
    ),
    total_plants AS (
        SELECT COUNT(*) as total_count
        FROM temp_gem_iso
    )
    SELECT jsonb_build_object(
        'total_operating_capacity_gw', op.total_capacity_gw,
        'operating_plants', op.plant_count,
        'mapped_plants', op.mapped_count,
        'total_plants', tp.total_count,
        'coverage_percentage', CASE 
            WHEN tp.total_count > 0 THEN (op.mapped_count::NUMERIC / tp.total_count * 100)
            ELSE 0 
        END
    ) INTO v_metadata
    FROM operating_plants op, total_plants tp;

    -- Get plants data (for map visualization)
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'id', format('%s_%s', p_iso_code, id),
            'name', COALESCE(plant_name, 'Unknown'),
            'technology', COALESCE(model_fuel, 'Unknown'),
            'capacity_mw', COALESCE(capacity_mw, 0),
            'status', COALESCE(status, 'Unknown'),
            'latitude', COALESCE(latitude, 0),
            'longitude', COALESCE(longitude, 0),
            'start_year', start_year,
            'age', age,
            'city', COALESCE(city, ''),
            'state', COALESCE(subnational_unit, ''),
            'country', COALESCE(country_area, 'Unknown')
        ) ORDER BY id
    ), '[]'::jsonb) INTO v_plants_data
    FROM temp_gem_iso
    WHERE LOWER(status) = ANY(v_statuses_to_keep)
      AND has_coordinates = TRUE;

    -- Calculate capacity by technology
    WITH capacity_by_tech_data AS (
        SELECT 
            model_fuel,
            ROUND(SUM(capacity_mw) / 1000.0, 3) as capacity_gw
        FROM temp_gem_iso
        WHERE model_fuel IS NOT NULL
          AND capacity_mw IS NOT NULL
        GROUP BY model_fuel
    )
    SELECT COALESCE(jsonb_object_agg(
        model_fuel,
        capacity_gw
    ), '{}'::jsonb) INTO v_capacity_by_tech
    FROM capacity_by_tech_data;

    -- Calculate status distribution
    WITH status_counts AS (
        SELECT status, COUNT(*)::INTEGER as count
        FROM temp_gem_iso
        GROUP BY status
    )
    SELECT COALESCE(jsonb_object_agg(
        status,
        count
    ), '{}'::jsonb) INTO v_status_dist
    FROM status_counts;

    -- Calculate fuel histograms (age and size distributions)
    WITH target_fuels AS (
        SELECT DISTINCT model_fuel
        FROM temp_gem_iso
        WHERE LOWER(status) = ANY(v_statuses_to_keep)
          AND model_fuel IN ('coal', 'gas', 'oil', 'nuclear', 'hydro')
          AND model_fuel IS NOT NULL
          AND capacity_mw > 0
    ),
    operating_plants AS (
        SELECT 
            model_fuel,
            capacity_mw,
            -- Use age from table (already calculated correctly during import)
            age,
            -- Age binning matching Python pd.cut with include_lowest=True
            -- Bins: [0, 5], (5, 10], (10, 20], (20, 30], (30, 50], (50, 100]
            CASE
                WHEN age >= 0 AND age <= 5 THEN '0-5'  -- [0, 5] inclusive
                WHEN age > 5 AND age <= 10 THEN '5-10'  -- (5, 10] exclusive left, inclusive right
                WHEN age > 10 AND age <= 20 THEN '10-20'  -- (10, 20]
                WHEN age > 20 AND age <= 30 THEN '20-30'  -- (20, 30]
                WHEN age > 30 AND age <= 50 THEN '30-50'  -- (30, 50]
                WHEN age > 50 THEN '50+'  -- (50, 100]
                ELSE NULL
            END as age_bin,
            -- Size binning matching Python pd.cut with include_lowest=True
            -- Bins: [0, 10], (10, 50], (50, 100], (100, 500], (500, 1000], (1000, 5000]
            CASE
                WHEN capacity_mw IS NULL OR capacity_mw <= 0 THEN NULL
                WHEN capacity_mw >= 0 AND capacity_mw <= 10 THEN '<10'  -- [0, 10] inclusive
                WHEN capacity_mw > 10 AND capacity_mw <= 50 THEN '10-50'  -- (10, 50] exclusive left, inclusive right
                WHEN capacity_mw > 50 AND capacity_mw <= 100 THEN '50-100'  -- (50, 100]
                WHEN capacity_mw > 100 AND capacity_mw <= 500 THEN '100-500'  -- (100, 500]
                WHEN capacity_mw > 500 AND capacity_mw <= 1000 THEN '500-1000'  -- (500, 1000]
                WHEN capacity_mw > 1000 THEN '1000+'  -- (1000, 5000]
                ELSE NULL
            END as size_bin
        FROM temp_gem_iso
        WHERE LOWER(status) = ANY(v_statuses_to_keep)
          AND capacity_mw IS NOT NULL
          AND capacity_mw > 0
          AND age IS NOT NULL
    ),
    fuel_histogram_data AS (
        SELECT 
            tf.model_fuel,
            -- Calculate age histogram values
            -- SUM will return NULL if no matching rows, COALESCE converts to 0
            COALESCE(SUM(CASE WHEN op.age_bin = '0-5' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as age_0_5,
            COALESCE(SUM(CASE WHEN op.age_bin = '5-10' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as age_5_10,
            COALESCE(SUM(CASE WHEN op.age_bin = '10-20' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as age_10_20,
            COALESCE(SUM(CASE WHEN op.age_bin = '20-30' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as age_20_30,
            COALESCE(SUM(CASE WHEN op.age_bin = '30-50' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as age_30_50,
            COALESCE(SUM(CASE WHEN op.age_bin = '50+' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as age_50_plus,
            -- Calculate size histogram values
            COALESCE(SUM(CASE WHEN op.size_bin = '<10' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as size_lt_10,
            COALESCE(SUM(CASE WHEN op.size_bin = '10-50' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as size_10_50,
            COALESCE(SUM(CASE WHEN op.size_bin = '50-100' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as size_50_100,
            COALESCE(SUM(CASE WHEN op.size_bin = '100-500' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as size_100_500,
            COALESCE(SUM(CASE WHEN op.size_bin = '500-1000' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as size_500_1000,
            COALESCE(SUM(CASE WHEN op.size_bin = '1000+' THEN op.capacity_mw ELSE 0 END), 0) / 1000.0 as size_1000_plus,
            -- Calculate totals
            ROUND(COALESCE(SUM(op.capacity_mw), 0) / 1000.0, 3) as total_capacity_gw,
            COUNT(op.model_fuel) as unit_count
        FROM target_fuels tf
        LEFT JOIN operating_plants op ON op.model_fuel = tf.model_fuel
        GROUP BY tf.model_fuel
    ),
    fuel_histogram_json AS (
        SELECT 
            model_fuel,
            jsonb_build_object(
                'age_histogram', jsonb_build_object(
                    '0-5', COALESCE(age_0_5, 0),
                    '5-10', COALESCE(age_5_10, 0),
                    '10-20', COALESCE(age_10_20, 0),
                    '20-30', COALESCE(age_20_30, 0),
                    '30-50', COALESCE(age_30_50, 0),
                    '50+', COALESCE(age_50_plus, 0)
                ),
                'size_histogram', jsonb_build_object(
                    '<10', COALESCE(size_lt_10, 0),
                    '10-50', COALESCE(size_10_50, 0),
                    '50-100', COALESCE(size_50_100, 0),
                    '100-500', COALESCE(size_100_500, 0),
                    '500-1000', COALESCE(size_500_1000, 0),
                    '1000+', COALESCE(size_1000_plus, 0)
                ),
                'total_capacity_gw', total_capacity_gw,
                'unit_count', unit_count
            ) as histogram
        FROM fuel_histogram_data
    )
    SELECT jsonb_build_object(
        'dominant_fuels', COALESCE(jsonb_agg(model_fuel ORDER BY model_fuel), '[]'::jsonb),
        'fuel_histograms', COALESCE(jsonb_object_agg(model_fuel, histogram), '{}'::jsonb)
    ) INTO v_histograms
    FROM fuel_histogram_json;

    -- Build final result
    v_result := jsonb_build_object(
        'success', true,
        'data', jsonb_build_object(
            'iso_code', p_iso_code,
            'metadata', v_metadata,
            'plants_data', v_plants_data,
            'capacity_by_technology', v_capacity_by_tech,
            'status_distribution', v_status_dist,
            'technologies_available', (
                SELECT jsonb_agg(DISTINCT model_fuel)
                FROM temp_gem_iso
                WHERE model_fuel IS NOT NULL
            ),
            'statuses_available', (
                SELECT jsonb_agg(DISTINCT status)
                FROM temp_gem_iso
            ),
            'dominant_fuels', COALESCE(v_histograms->'dominant_fuels', '[]'::jsonb),
            'fuel_histograms', COALESCE(v_histograms->'fuel_histograms', '{}'::jsonb)
        ),
        'error', NULL
    );

    -- Clean up temp table
    DROP TABLE IF EXISTS temp_gem_iso;

    RETURN v_result;

EXCEPTION
    WHEN OTHERS THEN
        -- Clean up temp table on error
        DROP TABLE IF EXISTS temp_gem_iso;
        RETURN jsonb_build_object(
            'success', false,
            'data', NULL,
            'error', format('Failed to process existing stock data: %s', SQLERRM)
        );
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION vervestacks.usp_get_existing_stock_metrics(VARCHAR(3)) TO postgres;

-- Add comment
COMMENT ON FUNCTION vervestacks.usp_get_existing_stock_metrics(VARCHAR(3)) IS 
'Returns existing stock metrics for dashboard charts. Processes GEM plants data to generate metadata, plant lists, capacity breakdowns, status distributions, and fuel histograms.';

