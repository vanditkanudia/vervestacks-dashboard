-- Import worldcities data into VerveStacks database
-- This script handles the complete import process for countries and cities

DROP TABLE IF EXISTS temp_worldcities;
CREATE TEMP TABLE temp_worldcities(
    city text,
    city_ascii text,
    lat numeric,
    lng numeric,
    country text,
    iso2 text,
    iso3 text,
    admin_name text,
    capital text,
    population bigint,
    id bigint
);

-- Import CSV data using PROGRAM mode for robust file access
\copy temp_worldcities FROM PROGRAM 'cmd /c type "data\worldcities.csv"' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');

-- Insert countries with deduplication
INSERT INTO vervestacks.countries (iso_code, iso2_code, name, region, latitude, longitude, population, capital, has_model)
SELECT 
    iso_code,
    iso2_code,
    name,
    region,
    latitude,
    longitude,
    population,
    capital,
    has_model
FROM (
    SELECT DISTINCT ON (iso3)
        iso3 as iso_code,
        iso2 as iso2_code,
        country as name,
        'Unknown' as region,
        AVG(lat) as latitude,
        AVG(lng) as longitude,
        SUM(population) as population,
        MAX(CASE WHEN capital = 'primary' THEN city ELSE NULL END) as capital,
        true as has_model
    FROM temp_worldcities 
    WHERE iso3 IS NOT NULL AND country IS NOT NULL
    GROUP BY iso3, iso2, country
) deduped
ON CONFLICT (iso_code) DO UPDATE SET
    iso2_code = EXCLUDED.iso2_code,
    name = EXCLUDED.name,
    region = EXCLUDED.region,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    population = EXCLUDED.population,
    capital = EXCLUDED.capital,
    has_model = EXCLUDED.has_model,
    model_last_updated = CURRENT_TIMESTAMP;

-- Insert cities
INSERT INTO vervestacks.cities (city_name, city_ascii, latitude, longitude, country_id, iso2_code, iso3_code, admin_name, capital_type, population, worldcities_id)
SELECT 
    t.city,
    t.city_ascii,
    t.lat,
    t.lng,
    c.id as country_id,
    t.iso2,
    t.iso3,
    t.admin_name,
    t.capital,
    t.population,
    t.id
FROM temp_worldcities t
JOIN vervestacks.countries c ON t.iso3 = c.iso_code
ON CONFLICT DO NOTHING;
