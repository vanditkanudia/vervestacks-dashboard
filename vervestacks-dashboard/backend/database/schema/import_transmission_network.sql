-- Import Transmission Network (Buses + Lines) Data into VerveStacks Database
-- Source: data/OSM-kan-prebuilt/

-- ============================================================================
-- STAGING CLEANUP
-- ============================================================================
DELETE FROM vervestacks.staging_transmission_buses;
DELETE FROM vervestacks.staging_transmission_lines;

-- ============================================================================
-- IMPORT BUSES (OSM-kan-prebuilt)
-- ============================================================================
-- Use temp table first (all TEXT columns) to avoid COPY parsing errors
DROP TABLE IF EXISTS temp_transmission_buses;
CREATE TEMP TABLE temp_transmission_buses (
    bus_id TEXT,
    station_id TEXT,
    voltage TEXT,
    dc TEXT,
    symbol TEXT,
    under_construction TEXT,
    tags TEXT,
    x TEXT,
    y TEXT,
    country TEXT,
    geometry TEXT
);

-- File path: Go up 3 levels from backend/database/ to project root, then into data/OSM-kan-prebuilt/
\copy temp_transmission_buses FROM PROGRAM 'cmd /c type "..\..\..\data\OSM-kan-prebuilt\buses.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8', QUOTE '"', ESCAPE '"');

-- Insert into staging table
INSERT INTO vervestacks.staging_transmission_buses (
    bus_id, station_id, voltage, dc, symbol, under_construction, tags, x, y, country, geometry
)
SELECT 
    bus_id, station_id, voltage, dc, symbol, under_construction, tags, x, y, country, geometry
FROM temp_transmission_buses;

-- Clear existing main table data (buses + lines) to ensure full refresh
DELETE FROM vervestacks.transmission_lines;
DELETE FROM vervestacks.transmission_buses;

INSERT INTO vervestacks.transmission_buses (
    bus_id,
    station_id,
    country,
    iso3_code,
    voltage,
    is_dc,
    symbol,
    under_construction,
    tags,
    longitude,
    latitude,
    geometry
)
SELECT DISTINCT ON (normalized_bus_id)
    normalized_bus_id AS bus_id,
    station_id,
    country,
    iso3_code,
    voltage,
    is_dc,
    symbol,
    under_construction,
    tags,
    longitude,
    latitude,
    geometry
FROM (
    SELECT
        TRIM(sb.bus_id) AS normalized_bus_id,
        NULLIF(TRIM(sb.station_id), '') AS station_id,
        UPPER(TRIM(sb.country)) AS country,
        c.iso_code AS iso3_code,
        NULLIF(TRIM(sb.voltage), '')::NUMERIC AS voltage,
        CASE WHEN LOWER(TRIM(sb.dc)) = 't' THEN TRUE ELSE FALSE END AS is_dc,
        NULLIF(TRIM(sb.symbol), '') AS symbol,
        CASE WHEN LOWER(TRIM(sb.under_construction)) = 't' THEN TRUE ELSE FALSE END AS under_construction,
        NULLIF(sb.tags, '') AS tags,
        NULLIF(TRIM(sb.x), '')::NUMERIC AS longitude,
        NULLIF(TRIM(sb.y), '')::NUMERIC AS latitude,
        NULLIF(TRIM(sb.geometry), '') AS geometry
    FROM vervestacks.staging_transmission_buses sb
    LEFT JOIN vervestacks.countries c ON UPPER(TRIM(sb.country)) = UPPER(TRIM(c.iso2_code))
    WHERE TRIM(sb.bus_id) IS NOT NULL
      AND TRIM(sb.country) <> ''
) deduped
ORDER BY normalized_bus_id, station_id NULLS LAST
ON CONFLICT (bus_id) DO NOTHING;

-- ============================================================================
-- IMPORT LINES (OSM-kan-prebuilt)
-- ============================================================================
-- Use temp table first (all TEXT columns) to avoid COPY parsing errors
DROP TABLE IF EXISTS temp_transmission_lines;
CREATE TEMP TABLE temp_transmission_lines (
    line_id TEXT,
    bus0 TEXT,
    bus1 TEXT,
    voltage TEXT,
    s_nom TEXT,
    circuits TEXT,
    length TEXT,
    underground TEXT,
    under_construction TEXT,
    tags TEXT,
    type TEXT,
    geometry TEXT
);

-- File path: Go up 3 levels from backend/database/ to project root, then into data/OSM-kan-prebuilt/
\copy temp_transmission_lines FROM PROGRAM 'cmd /c type "..\..\..\data\OSM-kan-prebuilt\lines.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8', QUOTE '"', ESCAPE '"');

-- Insert into staging table
INSERT INTO vervestacks.staging_transmission_lines (
    line_id, bus0, bus1, voltage, s_nom, circuits, length, underground, under_construction, tags, type, geometry
)
SELECT 
    line_id, bus0, bus1, voltage, s_nom, circuits, length, underground, under_construction, tags, type, geometry
FROM temp_transmission_lines;

-- Insert lines with joins to determine country and ISO3 code (only when both buses exist and share the same country)
WITH cleaned_lines AS (
    SELECT
        TRIM(line_id) AS line_id,
        TRIM(bus0) AS bus0_id,
        TRIM(bus1) AS bus1_id,
        NULLIF(TRIM(voltage), '')::NUMERIC AS voltage,
        NULLIF(TRIM(s_nom), '')::NUMERIC AS s_nom,
        NULLIF(TRIM(circuits), '')::INTEGER AS circuits,
        NULLIF(TRIM(length), '')::NUMERIC AS length_m,
        CASE WHEN LOWER(TRIM(underground)) = 't' THEN TRUE ELSE FALSE END AS underground,
        CASE WHEN LOWER(TRIM(under_construction)) = 't' THEN TRUE ELSE FALSE END AS under_construction,
        NULLIF(tags, '') AS tags,
        NULLIF(type, '') AS line_type,
        NULLIF(TRIM(geometry), '') AS geometry
    FROM vervestacks.staging_transmission_lines
    WHERE TRIM(line_id) IS NOT NULL
      AND TRIM(bus0) IS NOT NULL
      AND TRIM(bus1) IS NOT NULL
)
INSERT INTO vervestacks.transmission_lines (
    line_id,
    bus0_id,
    bus1_id,
    country,
    iso3_code,
    voltage,
    s_nom,
    circuits,
    length_km,
    underground,
    under_construction,
    tags,
    line_type,
    geometry
)
SELECT
    cl.line_id,
    cl.bus0_id,
    cl.bus1_id,
    b0.country,
    b0.iso3_code,  -- Use ISO3 from bus (both buses have same country, so same ISO3)
    cl.voltage,
    cl.s_nom,
    cl.circuits,
    CASE WHEN cl.length_m IS NOT NULL THEN cl.length_m / 1000.0 ELSE NULL END AS length_km,
    cl.underground,
    cl.under_construction,
    cl.tags,
    cl.line_type,
    cl.geometry
FROM cleaned_lines cl
JOIN vervestacks.transmission_buses b0 ON b0.bus_id = cl.bus0_id
JOIN vervestacks.transmission_buses b1 ON b1.bus_id = cl.bus1_id
WHERE b0.country = b1.country;

-- Show import statistics
SELECT 
    'Transmission Buses Import Complete!' AS status,
    COUNT(*) AS total_buses,
    COUNT(DISTINCT country) AS countries_imported
FROM vervestacks.transmission_buses;

SELECT 
    'Transmission Lines Import Complete!' AS status,
    COUNT(*) AS total_lines,
    COUNT(DISTINCT country) AS countries_imported
FROM vervestacks.transmission_lines;

