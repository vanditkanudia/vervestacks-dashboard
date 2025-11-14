-- Wind and Solar Production Fractions using PVGIS Data - Simple Normalization
-- Wind: Based on Vestas V117-3.3MW turbine specifications
-- Solar: Using PVGIS calculated power output (P column)
-- No capping - preserves natural generation patterns

WITH WindAndSolarProcessing AS (
    -- Step 1: Process wind speed and use PVGIS solar power directly
    SELECT 
        Country,
        Country_Code_ISO3,
        State,
        City,
        Lat,
        Lng,
        [time],
        Year,
        Month,
        Day,
        Hour,
        WS10m,
        try_convert(float,P) AS solar_power_pvgis,  -- PVGIS calculated solar power
        T2m AS temperature_c,
        -- Convert 10m wind to 91.5m hub height using power law (alpha = 0.143)
        WS10m * POWER(91.5 / 10.0, 0.143) AS WS_hub
    FROM [SARAH-ERA5].[dbo].[PVGIS_ISO]
),

PowerCalculations AS (
    -- Step 2: Apply wind power curve and normalize solar power
    SELECT *,
        -- Wind Power Curve (Vestas V117-3.3MW)
        CASE 
            -- Below cut-in (3 m/s): No power
            WHEN WS_hub < 3.0 THEN 0.0
            
            -- Linear ramp from 3 m/s to 12 m/s (rated)
            WHEN WS_hub >= 3.0 AND WS_hub < 4.0 THEN 0.02 * (WS_hub - 3.0) / 1.0
            WHEN WS_hub >= 4.0 AND WS_hub < 5.0 THEN 0.02 + (0.09 - 0.02) * (WS_hub - 4.0) / 1.0
            WHEN WS_hub >= 5.0 AND WS_hub < 6.0 THEN 0.09 + (0.21 - 0.09) * (WS_hub - 5.0) / 1.0
            WHEN WS_hub >= 6.0 AND WS_hub < 7.0 THEN 0.21 + (0.39 - 0.21) * (WS_hub - 6.0) / 1.0
            WHEN WS_hub >= 7.0 AND WS_hub < 8.0 THEN 0.39 + (0.64 - 0.39) * (WS_hub - 7.0) / 1.0
            WHEN WS_hub >= 8.0 AND WS_hub < 9.0 THEN 0.64 + (0.97 - 0.64) * (WS_hub - 8.0) / 1.0
            WHEN WS_hub >= 9.0 AND WS_hub < 10.0 THEN 0.97 + (1.39 - 0.97) * (WS_hub - 9.0) / 1.0
            WHEN WS_hub >= 10.0 AND WS_hub < 11.0 THEN 1.39 + (1.89 - 1.39) * (WS_hub - 10.0) / 1.0
            WHEN WS_hub >= 11.0 AND WS_hub < 12.0 THEN 1.89 + (2.47 - 1.89) * (WS_hub - 11.0) / 1.0
            
            -- Rated power region (12-25 m/s): Full capacity factor
            WHEN WS_hub >= 12.0 AND WS_hub < 25.0 THEN 1.0
            
            -- Above cut-out (25 m/s): No power (safety shutdown)
            ELSE 0.0
        END AS wind_capacity_factor,
        
        -- Solar: Use PVGIS power output directly (assuming it's normalized 0-1 or convert if needed)
        CASE 
            WHEN solar_power_pvgis < 0 THEN 0.0
            ELSE solar_power_pvgis / 1000.0  -- Convert from W/m² to capacity factor (adjust if P units differ)
        END AS solar_capacity_factor
    FROM WindAndSolarProcessing
),

AnnualSums AS (
    -- Step 3: Calculate annual sums for each location
    SELECT 
        Country_Code_ISO3,
        City,
        Year,
        SUM(wind_capacity_factor) AS annual_wind_cf_sum,
        SUM(solar_capacity_factor) AS annual_solar_cf_sum
    FROM PowerCalculations
    GROUP BY Country_Code_ISO3, City, Year
),

FinalFractions AS (
    -- Step 4: Simple normalization - no capping, just divide by annual sum
    SELECT 
        pc.*,
        asums.annual_wind_cf_sum,
        asums.annual_solar_cf_sum,
        
        -- Wind fractions: Simple normalization
        CASE 
            WHEN asums.annual_wind_cf_sum > 0 
            THEN pc.wind_capacity_factor / asums.annual_wind_cf_sum
            ELSE 0.0 
        END AS wind_fraction,
        
        -- Solar fractions: Simple normalization  
        CASE 
            WHEN asums.annual_solar_cf_sum > 0 
            THEN pc.solar_capacity_factor / asums.annual_solar_cf_sum
            ELSE 0.0 
        END AS solar_fraction
        
    FROM PowerCalculations pc
    INNER JOIN AnnualSums asums ON 
        pc.Country_Code_ISO3 = asums.Country_Code_ISO3 
        AND pc.City = asums.City 
        AND pc.Year = asums.Year
)

-- Final output with both wind and solar fractions
SELECT 
    Country_Code_ISO3 as iso,
    Month as month,
    Day as day,
    Hour as hour,
    ROUND(solar_fraction, 8) AS com_fr_solar,
	ROUND(wind_fraction, 8) AS com_fr_wind
FROM FinalFractions
WHERE Year = 2013 
ORDER BY Country_Code_ISO3, City, Year, Month, Day, Hour;

-- Validation queries to check results:

-- 1. Check that fractions sum to 1.0 per location-year
/*
SELECT 
    Country_Code_ISO3,
    City,
    Year,
    ROUND(SUM(wind_fraction), 6) AS wind_fraction_sum,
    ROUND(SUM(solar_fraction), 6) AS solar_fraction_sum,
    ROUND(AVG(wind_capacity_factor), 4) AS avg_wind_cf,
    ROUND(AVG(solar_capacity_factor), 4) AS avg_solar_cf,
    ROUND(MAX(wind_fraction), 8) AS max_wind_fraction,
    ROUND(MAX(solar_fraction), 8) AS max_solar_fraction,
    COUNT(*) AS total_hours
FROM FinalFractions
WHERE Year = 2013
GROUP BY Country_Code_ISO3, City, Year
ORDER BY max_wind_fraction DESC, max_solar_fraction DESC;
*/

-- 2. Summary by country
/*
SELECT 
    Country,
    COUNT(DISTINCT City) AS cities_count,
    ROUND(AVG(wind_capacity_factor), 4) AS avg_wind_cf,
    ROUND(AVG(solar_capacity_factor), 4) AS avg_solar_cf,
    ROUND(MAX(wind_fraction), 8) AS max_wind_fraction,
    ROUND(MAX(solar_fraction), 8) AS max_solar_fraction,
    COUNT(*) AS total_records
FROM FinalFractions
WHERE Year = 2013
GROUP BY Country
ORDER BY avg_wind_cf DESC;
*/

-- 3. Check for locations with extreme fractions (transmission stress indicators)
/*
SELECT 
    Country_Code_ISO3,
    City,
    COUNT(CASE WHEN wind_fraction > 0.001 THEN 1 END) AS high_wind_hours,
    COUNT(CASE WHEN solar_fraction > 0.001 THEN 1 END) AS high_solar_hours,
    MAX(wind_fraction) AS peak_wind_fraction,
    MAX(solar_fraction) AS peak_solar_fraction
FROM FinalFractions
WHERE Year = 2013
GROUP BY Country_Code_ISO3, City
HAVING MAX(wind_fraction) > 0.001 OR MAX(solar_fraction) > 0.001
ORDER BY peak_wind_fraction DESC, peak_solar_fraction DESC;
*/