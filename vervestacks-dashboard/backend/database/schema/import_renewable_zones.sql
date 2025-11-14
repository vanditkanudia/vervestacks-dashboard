-- Import renewable zones data into VerveStacks database
-- This script handles both onshore and offshore renewable energy zones

-- Clear existing staging data
DELETE FROM vervestacks.staging_renewable_zones_onshore;
DELETE FROM vervestacks.staging_renewable_zones_offshore;

-- Import onshore zones
DROP TABLE IF EXISTS temp_onshore_zones;
CREATE TEMP TABLE temp_onshore_zones (
    iso TEXT,
    country_name TEXT,
    grid_cell TEXT,
    centroid_lat NUMERIC,
    centroid_lon NUMERIC,
    zone_score NUMERIC,
    capacity_factor NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    suitable_area_km2 NUMERIC,
    area_km2 NUMERIC,
    perimeter_km NUMERIC,
    file_source TEXT,
    geometry_json TEXT
);

-- Import onshore CSV data
\copy temp_onshore_zones FROM PROGRAM 'cmd /c type ".\data\onshore_zones.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

-- Insert onshore zones
INSERT INTO vervestacks.staging_renewable_zones_onshore (
    iso, country_name, grid_cell, centroid_lat, centroid_lon,
    zone_score, capacity_factor, lcoe_usd_mwh, generation_potential_gwh,
    installed_capacity_potential_mw, suitable_area_km2, area_km2, perimeter_km,
    file_source, geometry_json
)
SELECT 
    iso, country_name, grid_cell, centroid_lat, centroid_lon,
    zone_score, capacity_factor, lcoe_usd_mwh, generation_potential_gwh,
    installed_capacity_potential_mw, suitable_area_km2, area_km2, perimeter_km,
    file_source, geometry_json
FROM temp_onshore_zones
WHERE iso IS NOT NULL AND iso <> '' AND capacity_factor IS NOT NULL;

-- Import offshore zones
DROP TABLE IF EXISTS temp_offshore_zones;
CREATE TEMP TABLE temp_offshore_zones (
    iso TEXT,
    grid_cell TEXT,
    centroid_lat NUMERIC,
    centroid_lon NUMERIC,
    zone_score NUMERIC,
    capacity_factor NUMERIC,
    lcoe_usd_mwh NUMERIC,
    generation_potential_gwh NUMERIC,
    installed_capacity_potential_mw NUMERIC,
    suitable_area_km2 NUMERIC,
    area_km2 NUMERIC,
    perimeter_km NUMERIC,
    file_source TEXT,
    geometry_json TEXT
);

-- Import offshore CSV data
\copy temp_offshore_zones FROM PROGRAM 'cmd /c type ".\data\offshore_zones.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

-- Insert offshore zones
INSERT INTO vervestacks.staging_renewable_zones_offshore (
    iso, grid_cell, centroid_lat, centroid_lon, zone_score,
    capacity_factor, lcoe_usd_mwh, generation_potential_gwh,
    installed_capacity_potential_mw, suitable_area_km2, area_km2, perimeter_km,
    file_source, geometry_json
)
SELECT 
    iso, grid_cell, centroid_lat, centroid_lon, zone_score,
    capacity_factor, lcoe_usd_mwh, generation_potential_gwh,
    installed_capacity_potential_mw, suitable_area_km2, area_km2, perimeter_km,
    file_source, geometry_json
FROM temp_offshore_zones
WHERE iso IS NOT NULL AND iso <> '' AND capacity_factor IS NOT NULL;
