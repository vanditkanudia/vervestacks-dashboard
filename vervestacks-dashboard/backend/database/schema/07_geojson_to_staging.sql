-- GeoJSON → staging loader (no Python). Assumes ogr2ogr loaded:
--   temp_onshore_geom(geom geometry(MultiPolygon,4326), <attributes...>)
--   temp_offshore_geom(geom geometry(MultiPolygon,4326), <attributes...>)
-- Adjust attribute column names below to match your GeoJSON fields.

\echo '--- GeoJSON to staging: start ---'
SET search_path TO vervestacks, public;

-- Debug: presence and basic stats of temp geometry tables
\echo 'Checking temp_onshore_geom presence and count'
SELECT to_regclass('public.temp_onshore_geom') AS onshore_table,
       COALESCE((SELECT COUNT(*) FROM public.temp_onshore_geom), 0) AS onshore_rows
WHERE TRUE;

\echo 'Checking temp_offshore_geom presence and count'
SELECT to_regclass('public.temp_offshore_geom') AS offshore_table,
       COALESCE((SELECT COUNT(*) FROM public.temp_offshore_geom), 0) AS offshore_rows
WHERE TRUE;

-- Ensure geometry SRID
-- (If your geom is unknown SRID, uncomment to force 4326)
-- UPDATE temp_onshore_geom  SET geom = ST_SetSRID(geom, 4326) WHERE ST_SRID(geom) = 0;
-- UPDATE temp_offshore_geom SET geom = ST_SetSRID(geom, 4326) WHERE ST_SRID(geom) = 0;

-- Clear current staging
\echo 'Clearing existing staging tables'
DELETE FROM staging_renewable_zones_onshore;
DELETE FROM staging_renewable_zones_offshore;

-- Onshore
INSERT INTO staging_renewable_zones_onshore (
    iso,
    country_name,
    grid_cell,
    centroid_lat,
    centroid_lon,
    zone_score,
    capacity_factor,
    lcoe_usd_mwh,
    generation_potential_gwh,
    installed_capacity_potential_mw,
    suitable_area_km2,
    area_km2,
    perimeter_km,
    file_source,
    geometry_json
)
SELECT
    COALESCE(t.iso, '') AS iso,
    COALESCE(t.country_name, '') AS country_name,
    t.grid_cell,
    ST_Y(ST_Centroid(t.geom)::geometry) AS centroid_lat,
    ST_X(ST_Centroid(t.geom)::geometry) AS centroid_lon,
    t.zone_score,
    t.capacity_factor,
    t.lcoe_usd_mwh,
    t.generation_potential_gwh,
    t.installed_capacity_potential_mw,
    t.suitable_area_km2,
    ST_Area(t.geom::geography) / 1000000.0 AS area_km2,
    ST_Perimeter(t.geom::geography) / 1000.0 AS perimeter_km,
    'data/consolidated_onshore_zones.geojson' AS file_source,
    ST_AsGeoJSON(t.geom) AS geometry_json
FROM temp_onshore_geom t
WHERE t.geom IS NOT NULL;

\echo 'Onshore staging row count after load'
SELECT COUNT(*) AS onshore_staging_rows FROM staging_renewable_zones_onshore;

-- Offshore
INSERT INTO staging_renewable_zones_offshore (
    iso,
    grid_cell,
    centroid_lat,
    centroid_lon,
    zone_score,
    capacity_factor,
    lcoe_usd_mwh,
    generation_potential_gwh,
    installed_capacity_potential_mw,
    suitable_area_km2,
    area_km2,
    perimeter_km,
    file_source,
    geometry_json
)
SELECT
    COALESCE(t.iso, '') AS iso,
    t.grid_cell,
    ST_Y(ST_Centroid(t.geom)::geometry) AS centroid_lat,
    ST_X(ST_Centroid(t.geom)::geometry) AS centroid_lon,
    t.zone_score,
    t.capacity_factor,
    t.lcoe_usd_mwh,
    t.generation_potential_gwh,
    t.installed_capacity_potential_mw,
    t.suitable_area_km2,
    ST_Area(t.geom::geography) / 1000000.0 AS area_km2,
    ST_Perimeter(t.geom::geography) / 1000.0 AS perimeter_km,
    'data/consolidated_offshore_zones.geojson' AS file_source,
    ST_AsGeoJSON(t.geom) AS geometry_json
FROM temp_offshore_geom t
WHERE t.geom IS NOT NULL;

\echo 'Offshore staging row count after load'
SELECT COUNT(*) AS offshore_staging_rows FROM staging_renewable_zones_offshore;

SELECT 'GeoJSON to staging load complete.' AS status;
\echo '--- GeoJSON to staging: end ---'


