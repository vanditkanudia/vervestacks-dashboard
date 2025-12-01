-- Import Renewable Capacity Factor CSV data into staging tables
-- Mirrors the pattern used for GEM data imports

\echo '--- Renewable capacity factors import: start ---'
SET search_path TO vervestacks, public;

-- ============================================================================
-- Recreate staging tables (schema may evolve)
-- ============================================================================

DROP TABLE IF EXISTS staging_renewable_capacity_factors_solar;
CREATE TABLE staging_renewable_capacity_factors_solar (
    id BIGSERIAL PRIMARY KEY,
    grid_cell TEXT NOT NULL,
    iso TEXT NOT NULL,
    lat NUMERIC,
    lng NUMERIC,
    zone_score NUMERIC,
    suitable_area_km2 NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    zone_output_density_gwh_km2 NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    capacity_factor NUMERIC,
    source_file TEXT DEFAULT 'REZoning_Solar_atlite_cf.csv',
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging_renewable_capacity_factors_wind_onshore;
CREATE TABLE staging_renewable_capacity_factors_wind_onshore (
    id BIGSERIAL PRIMARY KEY,
    grid_cell TEXT NOT NULL,
    iso TEXT NOT NULL,
    lat NUMERIC,
    lng NUMERIC,
    zone_score NUMERIC,
    suitable_area_km2 NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    zone_output_density_gwh_km2 NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    capacity_factor NUMERIC,
    source_file TEXT DEFAULT 'REZoning_WindOnshore_atlite_cf.csv',
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS staging_renewable_capacity_factors_wind_offshore;
CREATE TABLE staging_renewable_capacity_factors_wind_offshore (
    id BIGSERIAL PRIMARY KEY,
    grid_cell TEXT NOT NULL,
    iso TEXT NOT NULL,
    lat NUMERIC,
    lng NUMERIC,
    zone_score NUMERIC,
    suitable_area_km2 NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    zone_output_density_gwh_km2 NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    capacity_factor NUMERIC,
    cf_atlite_offshore_wind NUMERIC,
    source_file TEXT DEFAULT 'REZoning_WindOffshore_atlite_cf.csv',
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS renewable_zone_costs;
CREATE TABLE renewable_zone_costs (
    iso TEXT NOT NULL,
    tech TEXT NOT NULL,
    invcost NUMERIC,
    fixom NUMERIC,
    varom NUMERIC,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (iso, tech)
);

-- Clear existing data
TRUNCATE staging_renewable_capacity_factors_solar;
TRUNCATE staging_renewable_capacity_factors_wind_onshore;
TRUNCATE staging_renewable_capacity_factors_wind_offshore;
TRUNCATE renewable_zone_costs;

-- ============================================================================
-- Solar capacity factors
-- ============================================================================
\echo 'Loading solar capacity factor CSV'
DROP TABLE IF EXISTS temp_rezoning_solar_raw;
CREATE TEMP TABLE temp_rezoning_solar_raw (
    id INTEGER,
    zone_score NUMERIC,
    suitable_area_km2 NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    zone_output_density_gwh_km2 NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    capacity_factor NUMERIC,
    grid_cell TEXT,
    iso TEXT,
    lat NUMERIC,
    lng NUMERIC,
    cf_old NUMERIC
);

\copy temp_rezoning_solar_raw FROM PROGRAM 'cmd /c type "..\..\..\data\REZoning\REZoning_Solar_atlite_cf.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

INSERT INTO staging_renewable_capacity_factors_solar (
    grid_cell,
    iso,
    lat,
    lng,
    zone_score,
    suitable_area_km2,
    lcoe_usd_mwh,
    generation_potential_gwh,
    zone_output_density_gwh_km2,
    installed_capacity_potential_mw,
    capacity_factor
)
SELECT
    TRIM(grid_cell),
    TRIM(iso),
    lat,
    lng,
    zone_score,
    suitable_area_km2,
    lcoe_usd_mwh,
    generation_potential_gwh,
    zone_output_density_gwh_km2,
    installed_capacity_potential_mw,
    capacity_factor
FROM temp_rezoning_solar_raw
WHERE grid_cell IS NOT NULL
  AND grid_cell <> '';

-- ============================================================================
-- Wind onshore capacity factors
-- ============================================================================
\echo 'Loading wind onshore capacity factor CSV'
DROP TABLE IF EXISTS temp_rezoning_wind_onshore_raw;
CREATE TEMP TABLE temp_rezoning_wind_onshore_raw (
    id INTEGER,
    zone_score NUMERIC,
    suitable_area_km2 NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    zone_output_density_gwh_km2 NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    capacity_factor NUMERIC,
    grid_cell TEXT,
    iso TEXT,
    lat NUMERIC,
    lng NUMERIC,
    cf_old NUMERIC
);

\copy temp_rezoning_wind_onshore_raw FROM PROGRAM 'cmd /c type "..\..\..\data\REZoning\REZoning_WindOnshore_atlite_cf.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

INSERT INTO staging_renewable_capacity_factors_wind_onshore (
    grid_cell,
    iso,
    lat,
    lng,
    zone_score,
    suitable_area_km2,
    lcoe_usd_mwh,
    generation_potential_gwh,
    zone_output_density_gwh_km2,
    installed_capacity_potential_mw,
    capacity_factor
)
SELECT
    TRIM(grid_cell),
    TRIM(iso),
    lat,
    lng,
    zone_score,
    suitable_area_km2,
    lcoe_usd_mwh,
    generation_potential_gwh,
    zone_output_density_gwh_km2,
    installed_capacity_potential_mw,
    capacity_factor
FROM temp_rezoning_wind_onshore_raw
WHERE grid_cell IS NOT NULL
  AND grid_cell <> '';

-- ============================================================================
-- Wind offshore capacity factors
-- ============================================================================
\echo 'Loading wind offshore capacity factor CSV'
DROP TABLE IF EXISTS temp_rezoning_wind_offshore_raw;
CREATE TEMP TABLE temp_rezoning_wind_offshore_raw (
    id INTEGER,
    zone_score NUMERIC,
    suitable_area_km2 NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    zone_output_density_gwh_km2 NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    capacity_factor NUMERIC,
    grid_cell TEXT,
    iso TEXT,
    lat NUMERIC,
    lng NUMERIC,
    cf_old NUMERIC
);

\copy temp_rezoning_wind_offshore_raw FROM PROGRAM 'cmd /c type "..\..\..\data\REZoning\REZoning_WindOffshore_atlite_cf.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

INSERT INTO staging_renewable_capacity_factors_wind_offshore (
    grid_cell,
    iso,
    lat,
    lng,
    zone_score,
    suitable_area_km2,
    lcoe_usd_mwh,
    generation_potential_gwh,
    zone_output_density_gwh_km2,
    installed_capacity_potential_mw,
    capacity_factor,
    cf_atlite_offshore_wind
)
SELECT
    TRIM(grid_cell),
    TRIM(iso),
    lat,
    lng,
    zone_score,
    suitable_area_km2,
    lcoe_usd_mwh,
    generation_potential_gwh,
    zone_output_density_gwh_km2,
    installed_capacity_potential_mw,
    capacity_factor,
    cf_old AS cf_atlite_offshore_wind
FROM temp_rezoning_wind_offshore_raw
WHERE grid_cell IS NOT NULL
  AND grid_cell <> '';

-- ============================================================================
-- Costs
-- ============================================================================
\echo 'Loading renewable cost CSV'
DROP TABLE IF EXISTS temp_rezoning_costs_raw;
CREATE TEMP TABLE temp_rezoning_costs_raw (
    iso TEXT,
    tech TEXT,
    invcost NUMERIC,
    fixom NUMERIC
);

\copy temp_rezoning_costs_raw FROM PROGRAM 'cmd /c type "..\..\..\data\REZoning\REZoning_costs_per_kw.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

WITH ranked_costs AS (
    SELECT
        TRIM(iso) AS iso,
        LOWER(TRIM(tech)) AS tech,
        invcost,
        fixom,
        ROW_NUMBER() OVER (
            PARTITION BY TRIM(iso), LOWER(TRIM(tech))
            ORDER BY invcost NULLS LAST, fixom NULLS LAST
        ) AS rn
    FROM temp_rezoning_costs_raw
    WHERE iso IS NOT NULL
      AND iso <> ''
      AND tech IS NOT NULL
      AND tech <> ''
)
INSERT INTO renewable_zone_costs (
    iso,
    tech,
    invcost,
    fixom,
    varom
)
SELECT
    iso,
    tech,
    invcost,
    fixom,
    NULL::NUMERIC
FROM ranked_costs
WHERE rn = 1;

\echo '--- Renewable capacity factors import complete ---'

