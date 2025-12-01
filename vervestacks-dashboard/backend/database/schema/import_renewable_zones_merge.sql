-- Merge geometry staging tables with capacity factor staging tables
-- Produces final renewable zone tables consumed by the dashboard

\echo '--- Renewable zones merge: start ---'
SET search_path TO vervestacks, public;

-- ============================================================================
-- Final tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS renewable_zones_solar (
    id BIGSERIAL PRIMARY KEY,
    grid_cell TEXT UNIQUE NOT NULL,
    iso TEXT NOT NULL,
    lat NUMERIC,
    lng NUMERIC,
    centroid_lat NUMERIC,
    centroid_lon NUMERIC,
    zone_score NUMERIC,
    suitable_area_km2 NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    capacity_factor NUMERIC,
    zone_output_density_gwh_km2 NUMERIC,
    area_km2 NUMERIC,
    perimeter_km NUMERIC,
    source_type TEXT DEFAULT 'solar',
    file_source TEXT,
    geometry_json TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS renewable_zones_wind_onshore (
    id BIGSERIAL PRIMARY KEY,
    grid_cell TEXT UNIQUE NOT NULL,
    iso TEXT NOT NULL,
    wind_type TEXT DEFAULT 'onshore',
    lat NUMERIC,
    lng NUMERIC,
    centroid_lat NUMERIC,
    centroid_lon NUMERIC,
    zone_score NUMERIC,
    suitable_area_km2 NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    capacity_factor NUMERIC,
    zone_output_density_gwh_km2 NUMERIC,
    area_km2 NUMERIC,
    perimeter_km NUMERIC,
    file_source TEXT,
    geometry_json TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS renewable_zones_wind_offshore (
    id BIGSERIAL PRIMARY KEY,
    grid_cell TEXT UNIQUE NOT NULL,
    iso TEXT NOT NULL,
    wind_type TEXT DEFAULT 'offshore',
    lat NUMERIC,
    lng NUMERIC,
    centroid_lat NUMERIC,
    centroid_lon NUMERIC,
    zone_score NUMERIC,
    suitable_area_km2 NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    capacity_factor NUMERIC,
    cf_atlite_offshore_wind NUMERIC,
    zone_output_density_gwh_km2 NUMERIC,
    area_km2 NUMERIC,
    perimeter_km NUMERIC,
    file_source TEXT,
    geometry_json TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

TRUNCATE renewable_zones_solar;
TRUNCATE renewable_zones_wind_onshore;
TRUNCATE renewable_zones_wind_offshore;

-- ============================================================================
-- Solar merge
-- ============================================================================
\echo 'Merging solar zones'
WITH solar_cf AS (
    SELECT *
    FROM (
        SELECT
            cf.*,
            ROW_NUMBER() OVER (PARTITION BY TRIM(cf.grid_cell) ORDER BY cf.capacity_factor DESC NULLS LAST, cf.id) AS rn
        FROM staging_renewable_capacity_factors_solar cf
    ) ranked
    WHERE rn = 1
),
solar_joined AS (
    SELECT
        TRIM(cf.grid_cell) AS grid_cell_trimmed,
        cf.id AS cf_id,
        cf.iso AS cf_iso,
        cf.lat AS cf_lat,
        cf.lng AS cf_lng,
        cf.zone_score AS cf_zone_score,
        cf.suitable_area_km2 AS cf_suitable_area_km2,
        cf.lcoe_usd_mwh AS cf_lcoe_usd_mwh,
        cf.generation_potential_gwh AS cf_generation_potential_gwh,
        cf.installed_capacity_potential_mw AS cf_installed_capacity_potential_mw,
        cf.capacity_factor AS cf_capacity_factor,
        cf.zone_output_density_gwh_km2,
        geom.*
    FROM solar_cf cf
    JOIN staging_renewable_zones_onshore geom
      ON TRIM(cf.grid_cell) = TRIM(geom.grid_cell)
),
solar_ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY grid_cell_trimmed
               ORDER BY cf_capacity_factor DESC NULLS LAST, cf_id
           ) AS rn
    FROM solar_joined
)
INSERT INTO renewable_zones_solar (
    grid_cell,
    iso,
    lat,
    lng,
    centroid_lat,
    centroid_lon,
    zone_score,
    suitable_area_km2,
    lcoe_usd_mwh,
    generation_potential_gwh,
    installed_capacity_potential_mw,
    capacity_factor,
    zone_output_density_gwh_km2,
    area_km2,
    perimeter_km,
    file_source,
    geometry_json
)
SELECT
    grid_cell_trimmed,
    cf_iso,
    COALESCE(cf_lat, centroid_lat),
    COALESCE(cf_lng, centroid_lon),
    centroid_lat,
    centroid_lon,
    COALESCE(cf_zone_score, zone_score),
    COALESCE(cf_suitable_area_km2, suitable_area_km2),
    COALESCE(cf_lcoe_usd_mwh, lcoe_usd_mwh),
    COALESCE(cf_generation_potential_gwh, generation_potential_gwh),
    COALESCE(cf_installed_capacity_potential_mw, installed_capacity_potential_mw),
    cf_capacity_factor AS capacity_factor,
    zone_output_density_gwh_km2,
    area_km2,
    perimeter_km,
    file_source,
    geometry_json
FROM solar_ranked
WHERE rn = 1
ON CONFLICT (grid_cell) DO NOTHING;

\echo 'Solar zones inserted:'
SELECT COUNT(*) AS solar_rows FROM renewable_zones_solar;

-- ============================================================================
-- Wind onshore merge
-- ============================================================================
\echo 'Merging wind onshore zones'
WITH wind_on_cf AS (
    SELECT *
    FROM (
        SELECT
            cf.*,
            ROW_NUMBER() OVER (PARTITION BY TRIM(cf.grid_cell) ORDER BY cf.capacity_factor DESC NULLS LAST, cf.id) AS rn
        FROM staging_renewable_capacity_factors_wind_onshore cf
    ) ranked
    WHERE rn = 1
),
wind_on_joined AS (
    SELECT
        TRIM(cf.grid_cell) AS grid_cell_trimmed,
        cf.id AS cf_id,
        cf.iso AS cf_iso,
        cf.lat AS cf_lat,
        cf.lng AS cf_lng,
        cf.zone_score AS cf_zone_score,
        cf.suitable_area_km2 AS cf_suitable_area_km2,
        cf.lcoe_usd_mwh AS cf_lcoe_usd_mwh,
        cf.generation_potential_gwh AS cf_generation_potential_gwh,
        cf.installed_capacity_potential_mw AS cf_installed_capacity_potential_mw,
        cf.capacity_factor AS cf_capacity_factor,
        cf.zone_output_density_gwh_km2,
        geom.*
    FROM wind_on_cf cf
    JOIN staging_renewable_zones_onshore geom
      ON TRIM(cf.grid_cell) = TRIM(geom.grid_cell)
),
wind_on_ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY grid_cell_trimmed
               ORDER BY cf_capacity_factor DESC NULLS LAST, cf_id
           ) AS rn
    FROM wind_on_joined
)
INSERT INTO renewable_zones_wind_onshore (
    grid_cell,
    iso,
    lat,
    lng,
    centroid_lat,
    centroid_lon,
    zone_score,
    suitable_area_km2,
    lcoe_usd_mwh,
    generation_potential_gwh,
    installed_capacity_potential_mw,
    capacity_factor,
    zone_output_density_gwh_km2,
    area_km2,
    perimeter_km,
    file_source,
    geometry_json
)
SELECT
    grid_cell_trimmed,
    cf_iso,
    COALESCE(cf_lat, centroid_lat),
    COALESCE(cf_lng, centroid_lon),
    centroid_lat,
    centroid_lon,
    COALESCE(cf_zone_score, zone_score),
    COALESCE(cf_suitable_area_km2, suitable_area_km2),
    COALESCE(cf_lcoe_usd_mwh, lcoe_usd_mwh),
    COALESCE(cf_generation_potential_gwh, generation_potential_gwh),
    COALESCE(cf_installed_capacity_potential_mw, installed_capacity_potential_mw),
    cf_capacity_factor AS capacity_factor,
    zone_output_density_gwh_km2,
    area_km2,
    perimeter_km,
    file_source,
    geometry_json
FROM wind_on_ranked
WHERE rn = 1
ON CONFLICT (grid_cell) DO NOTHING;

\echo 'Wind onshore zones inserted:'
SELECT COUNT(*) AS wind_onshore_rows FROM renewable_zones_wind_onshore;

-- ============================================================================
-- Wind offshore merge
-- ============================================================================
\echo 'Merging wind offshore zones'
WITH wind_off_cf AS (
    SELECT *
    FROM (
        SELECT
            cf.*,
            ROW_NUMBER() OVER (PARTITION BY TRIM(cf.grid_cell) ORDER BY cf.capacity_factor DESC NULLS LAST, cf.id) AS rn
        FROM staging_renewable_capacity_factors_wind_offshore cf
    ) ranked
    WHERE rn = 1
),
wind_off_joined AS (
    SELECT
        TRIM(cf.grid_cell) AS grid_cell_trimmed,
        cf.id AS cf_id,
        cf.iso AS cf_iso,
        cf.lat AS cf_lat,
        cf.lng AS cf_lng,
        cf.zone_score AS cf_zone_score,
        cf.suitable_area_km2 AS cf_suitable_area_km2,
        cf.lcoe_usd_mwh AS cf_lcoe_usd_mwh,
        cf.generation_potential_gwh AS cf_generation_potential_gwh,
        cf.installed_capacity_potential_mw AS cf_installed_capacity_potential_mw,
        cf.capacity_factor AS cf_capacity_factor,
        cf.cf_atlite_offshore_wind,
        cf.zone_output_density_gwh_km2,
        geom.*
    FROM wind_off_cf cf
    JOIN staging_renewable_zones_offshore geom
      ON 'wof-' ||TRIM(cf.grid_cell) =  TRIM(geom.grid_cell)
),
wind_off_ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY grid_cell_trimmed
               ORDER BY cf_capacity_factor DESC NULLS LAST, cf_id
           ) AS rn
    FROM wind_off_joined
)
INSERT INTO renewable_zones_wind_offshore (
    grid_cell,
    iso,
    lat,
    lng,
    centroid_lat,
    centroid_lon,
    zone_score,
    suitable_area_km2,
    lcoe_usd_mwh,
    generation_potential_gwh,
    installed_capacity_potential_mw,
    capacity_factor,
    cf_atlite_offshore_wind,
    zone_output_density_gwh_km2,
    area_km2,
    perimeter_km,
    file_source,
    geometry_json
)
SELECT
    grid_cell_trimmed,
    cf_iso,
    COALESCE(cf_lat, centroid_lat),
    COALESCE(cf_lng, centroid_lon),
    centroid_lat,
    centroid_lon,
    COALESCE(cf_zone_score, zone_score),
    COALESCE(cf_suitable_area_km2, suitable_area_km2),
    COALESCE(cf_lcoe_usd_mwh, lcoe_usd_mwh),
    COALESCE(cf_generation_potential_gwh, generation_potential_gwh),
    COALESCE(cf_installed_capacity_potential_mw, installed_capacity_potential_mw),
    cf_capacity_factor AS capacity_factor,
    cf_atlite_offshore_wind,
    zone_output_density_gwh_km2,
    area_km2,
    perimeter_km,
    file_source,
    geometry_json
FROM wind_off_ranked
WHERE rn = 1
ON CONFLICT (grid_cell) DO NOTHING;

\echo 'Wind offshore zones inserted:'
SELECT COUNT(*) AS wind_offshore_rows FROM renewable_zones_wind_offshore;

\echo '--- Renewable zones merge complete ---'

