# VerveStacks Database Setup - Final Version

This directory contains the complete database setup for the VerveStacks dashboard application.

## Prerequisites

- PostgreSQL 12+
- Python 3.6+ (for GeoJSON conversion)
- Access to PostgreSQL server (localhost:5432 by default)

## Quick Start

### Complete Setup (Recommended)
```bash
# 1. Convert GeoJSON files to CSV (if needed)
python convert_geojson.py

# 2. Consolidate transmission generation plants CSV files (if needed)
python consolidate_generation_plants.py

# 3. Run complete database setup
setup_database.bat
```

That's it! The database will be fully populated and ready for use.

## Data Sources

- **worldcities.csv**: Global cities database (48K+ cities)
- **consolidated_onshore_zones.geojson**: Onshore renewable energy zones (60K+ zones)
- **consolidated_offshore_zones.geojson**: Offshore renewable energy zones (42K+ zones)
- **processed_gem_plants_data.csv**: Global Energy Monitor (GEM) power plant data (100K+ plants)
- **data/OSM-kan-prebuilt/**: Consolidated OSM transmission buses & lines (BR, CA, DE, ES, IT, JP, NZ, PT)

## File Structure

```
database/
├── setup_database.bat             # Complete database setup script
├── convert_geojson.py             # GeoJSON to CSV converter
├── consolidate_generation_plants.py  # Consolidate transmission generation CSV files
├── schema/                        # All SQL schema files
│   ├── 00_create_database.sql     # Database creation
│   ├── 01_create_schema.sql        # Schema setup
│   ├── 02_create_tables.sql        # Table definitions
│   ├── 03_create_indexes.sql       # Performance indexes
│   ├── 04_create_functions.sql     # Stored procedures
│   ├── 05_create_triggers.sql      # Triggers and validation
│   ├── 06_grant_permissions.sql    # User permissions
│   ├── 07_geojson_to_staging.sql   # GeoJSON processing
│   ├── setup_schema.sql            # Main schema orchestrator
│   ├── import_worldcities.sql      # Worldcities data import
│   ├── import_renewable_zones.sql  # Renewable zones data import
│   ├── import_gem_plants.sql       # GEM plants data import (SQL)
│   ├── import_transmission_generation_plants.sql  # Transmission generation plants import
│   ├── import_transmission_network.sql  # Transmission network (buses + lines) import
│   └── procedure/                  # Stored procedures
│       ├── usp_get_capacity_evolution_data.sql
│       ├── usp_get_co2_intensity_data.sql
│       ├── usp_get_fuel_colors.sql
│       ├── usp_get_generation_trends_data.sql
│       ├── usp_get_utilization_factor_data.sql
│       ├── usp_get_existing_stock_metrics.sql  # GEM existing stock
│       ├── usp_get_transmission_generation_plants.sql  # Transmission generation plants
│       └── usp_get_transmission_network_data.sql       # Transmission network (buses + lines)
└── data/                          # Data files
    ├── worldcities.csv
    ├── consolidated_onshore_zones.geojson
    ├── consolidated_offshore_zones.geojson
    ├── onshore_zones.csv          # Generated from GeoJSON
    ├── offshore_zones.csv         # Generated from GeoJSON
    ├── transmission_generation_plants_consolidated.csv  # Generated from consolidation script
    └── OSM-kan-prebuilt/           # Prebuilt OSM buses & lines (copied to project root)
```

## Execution Flow

1. **GeoJSON Conversion** (`convert_geojson.py`)
   - Converts GeoJSON files to CSV format
   - Handles both onshore and offshore zones
   - Preserves geometry as JSON text
   - Extracts ISO codes and other properties

2. **Database Setup** (`setup_database.bat`)
   - Creates `vervestacks_dashboard` database
   - Creates `vervestacks` schema
   - Creates all tables, indexes, triggers, and permissions
   - Creates GEM plants tables and stored procedures
   - Imports worldcities data (241 countries, 48K+ cities)
   - Imports renewable zones data (60K+ onshore, 42K+ offshore)

3. **GEM Plants Data Import** (Optional, separate step)
   - Run SQL import: `psql -d vervestacks_dashboard -f schema/import_gem_plants.sql`
   - Requires `processed_gem_plants_data.csv` in `data/` directory
   - Imports GEM power plant data (100K+ plants) for existing stock analysis

4. **Transmission Generation Plants Data Import** (Optional, separate step)
   - First run: `python consolidate_generation_plants.py` to merge all country CSV files
   - Then run SQL import: `psql -d vervestacks_dashboard -f schema/import_transmission_generation_plants.sql`
   - Requires `transmission_generation_plants_consolidated.csv` in `data/` directory
   - Imports transmission generation plants data (80+ countries) for transmission analysis

5. **Transmission Network Infrastructure Import**
   - Source files: `data/OSM-kan-prebuilt/buses.csv` and `lines.csv` (already consolidated)
   - Run SQL import: `psql -d vervestacks_dashboard -f schema/import_transmission_network.sql`
   - Loads staging tables, converts to numeric types, and populates:
     - `vervestacks.transmission_buses`
     - `vervestacks.transmission_lines`
   - Replaces the old Python OSM loader for Transmission Lines tab

## Verification

After setup, verify the data:

```sql
-- Check data counts
SELECT 'Countries: ' || COUNT(*) FROM vervestacks.countries;
SELECT 'Cities: ' || COUNT(*) FROM vervestacks.cities;
SELECT 'Onshore zones: ' || COUNT(*) FROM vervestacks.staging_renewable_zones_onshore;
SELECT 'Offshore zones: ' || COUNT(*) FROM vervestacks.staging_renewable_zones_offshore;
SELECT 'GEM plants: ' || COUNT(*) FROM vervestacks.gem_plants;
SELECT 'GEM countries: ' || COUNT(DISTINCT iso_code) FROM vervestacks.gem_plants;

-- Sample data
SELECT name, iso_code FROM vervestacks.countries ORDER BY name LIMIT 5;
SELECT iso, country_name, capacity_factor FROM vervestacks.staging_renewable_zones_onshore LIMIT 3;
SELECT iso_code, COUNT(*) as plants, SUM(capacity_mw)/1000.0 as total_capacity_gw 
FROM vervestacks.gem_plants 
WHERE LOWER(status) IN ('operating', 'construction')
GROUP BY iso_code 
ORDER BY total_capacity_gw DESC 
LIMIT 5;

-- Test GEM stored procedure
SELECT vervestacks.usp_get_existing_stock_metrics('DEU');

-- Test transmission generation plants stored procedure
SELECT vervestacks.usp_get_transmission_generation_plants('BRA');

-- Transmission network counts
SELECT 'Transmission buses: ' || COUNT(*) FROM vervestacks.transmission_buses;
SELECT 'Transmission lines: ' || COUNT(*) FROM vervestacks.transmission_lines;

-- Test transmission network stored procedure
SELECT jsonb_pretty(vervestacks.usp_get_transmission_network_data('BRA'));
```

Expected results:
- Countries: 241
- Cities: 48,059
- Onshore zones: 60,342
- Offshore zones: 42,640
- GEM plants: ~100,000+ (after import)
- GEM countries: ~200+ (after import)

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Issues**
   - Ensure PostgreSQL server is running on localhost:5432
   - Check that postgres user has necessary permissions

2. **File Not Found Errors**
   - Run scripts from `backend/database` directory
   - Ensure all data files are in `data/` subdirectory
   - Check that GeoJSON files exist before conversion
   - All SQL files are now organized in `schema/` folder

3. **Python Script Issues**
   - Ensure Python 3.6+ is installed
   - Check that JSON files are valid GeoJSON format
   - Verify file permissions for reading/writing

4. **GEM Data Import Issues**
   - Ensure `processed_gem_plants_data.csv` exists and is accessible
   - Check PostgreSQL connection settings (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)
   - Verify `gem_techmap` table exists (optional, fallback logic will be used if missing)
   - Check that stored procedure `usp_get_existing_stock_metrics` exists

### Error Messages

- `relation "temp_worldcities" does not exist`: Normal - temp tables are session-scoped
- `No such file or directory`: Check file paths and working directory
- `permission denied`: Ensure PostgreSQL user has necessary permissions
- `function vervestacks.usp_get_existing_stock_metrics does not exist`: Run stored procedure creation script
- `relation "vervestacks.gem_plants" does not exist`: Run `02_create_tables.sql` to create all tables (GEM tables are included)

## Production Notes

- Uses `timestamp` without timezone (as requested)
- Permissions are set for development (not tightened for production)
- Geometry data is stored as JSON TEXT (PostGIS not required)
- All scripts are idempotent (can be run multiple times safely)
- Uses client-side `\copy` with PROGRAM mode for robust file access
- All SQL files organized in `schema/` folder for better maintainability
- Streamlined setup process with no verification steps (as requested)
- GEM plants data is queried via stored procedures (no Python service dependency)
- Existing stock endpoint calls PostgreSQL directly from Node.js backend

## GEM Plants Data

The GEM (Global Energy Monitor) plants data provides existing stock analysis for the dashboard:

### Tables
- **`vervestacks.gem_techmap`**: Technology mapping reference (Type_mod + Technology → model_fuel)
- **`vervestacks.staging_gem_plants`**: Staging table for CSV imports
- **`vervestacks.gem_plants`**: Main processed plants table with model_fuel calculated

### Stored Procedure
- **`vervestacks.usp_get_existing_stock_metrics(iso_code)`**: Returns JSONB with existing stock metrics
  - Metadata (capacity, plant counts, coverage)
  - Plants data (for map visualization)
  - Capacity by technology
  - Status distribution
  - Fuel histograms (age and size distributions)

### Import Method

**SQL Import** (follows same pattern as other imports)
```bash
# Ensure CSV file is in data/ directory
# Then run the import script
psql -d vervestacks_dashboard -f schema/import_gem_plants.sql
```

The import script will:
- Load CSV from `data/processed_gem_plants_data.csv`
- Apply model_fuel logic (techmap merge + fallback)
- Process and load into `gem_plants` table

### Usage

The existing stock endpoint (`/api/overview/existing-stock/:iso_code`) calls the stored procedure directly from Node.js backend, matching the Overview tab pattern. No Python service is required.

## Transmission Generation Plants Data

The transmission generation plants data provides power plant visualization for the transmission analysis tab:

### Tables
- **`vervestacks.staging_transmission_generation_plants`**: Staging table for CSV imports
- **`vervestacks.transmission_generation_plants`**: Main processed plants table with coordinates and fuel types

### Stored Procedure
- **`vervestacks.usp_get_transmission_generation_plants(iso_code)`**: Returns JSONB with generation plants data
  - Plants data (for map visualization)
  - Statistics (total plants, capacity, fuel type counts)

### Import Method

**Step 1: Consolidate CSV Files**
```bash
# Run from backend/database/ directory
python consolidate_generation_plants.py
```

This script:
- Merges all `data/transmission_line_generation/*.csv` files
- Adds `iso_code` column (extracted from filename)
- Filters invalid coordinates
- Saves to `data/transmission_generation_plants_consolidated.csv`

**Step 2: SQL Import** (follows same pattern as other imports)
```bash
# Ensure consolidated CSV file is in data/ directory
# Then run the import script
psql -d vervestacks_dashboard -f schema/import_transmission_generation_plants.sql
```

### Usage

The transmission generation endpoint (`/api/transmission/generation/:isoCode`) calls the stored procedure directly from Node.js backend, matching the Overview tab pattern. No Python service is required.

## Transmission Network Data

The transmission network data (buses + lines) powers the infrastructure maps used in the Transmission Lines tab.

### Tables
- **`vervestacks.transmission_buses`**: Clean bus/substation data filtered by country
- **`vervestacks.transmission_lines`**: Transmission lines with both endpoints inside the country
- **Staging tables** mirror the OSM CSV columns for safe imports

### Stored Procedure
- **`vervestacks.usp_get_transmission_network_data(iso_code)`**: Returns JSONB with buses, lines, and statistics (same shape as the legacy Python service)

### Import Method

```bash
# Ensure OSM files exist at project root: data/OSM-kan-prebuilt/buses.csv + lines.csv
psql -d vervestacks_dashboard -f schema/import_transmission_network.sql
```

The import script:
- Loads CSV data into temp tables (all TEXT)
- Copies into staging tables
- Converts types and populates main tables
- Filters lines to cases where both buses belong to the same country

### Usage

- Backend route `/api/transmission/network/:isoCode` now calls the stored procedure directly (no Python dependency)
- Frontend Transmission Lines tab reads from the new PostgreSQL-backed endpoint

## Support

For issues or questions, check the troubleshooting section above or refer to the PostgreSQL documentation.

## Note on Geometry Data

Geometry data is stored as JSON TEXT in the database (geometry_json columns). The `07_geojson_to_staging.sql` script uses PostGIS functions for processing temporary geometry tables created by ogr2ogr, but the main database schema does not require PostGIS. The standard import process uses CSV files with pre-converted geometry JSON.