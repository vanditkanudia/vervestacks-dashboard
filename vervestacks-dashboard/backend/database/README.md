# VerveStacks Database Setup - Final Version

This directory contains the complete database setup for the VerveStacks dashboard application.

## Prerequisites

- PostgreSQL 12+ with PostGIS extension
- Python 3.6+ (for GeoJSON conversion)
- Access to PostgreSQL server (localhost:5432 by default)

## Quick Start

### Complete Setup (Recommended)
```bash
# 1. Convert GeoJSON files to CSV (if needed)
python convert_geojson.py

# 2. Run complete database setup
setup_database.bat
```

That's it! The database will be fully populated and ready for use.

## Data Sources

- **worldcities.csv**: Global cities database (48K+ cities)
- **consolidated_onshore_zones.geojson**: Onshore renewable energy zones (60K+ zones)
- **consolidated_offshore_zones.geojson**: Offshore renewable energy zones (42K+ zones)

## File Structure

```
database/
├── setup_database.bat             # Complete database setup script
├── convert_geojson.py             # GeoJSON to CSV converter
├── schema/                        # All SQL schema files
│   ├── 00_create_database.sql     # Database creation
│   ├── 01_create_schema.sql        # Schema and PostGIS setup
│   ├── 02_create_tables.sql        # Table definitions
│   ├── 03_create_indexes.sql       # Performance indexes
│   ├── 04_create_functions.sql     # Stored procedures
│   ├── 05_create_triggers.sql      # Triggers and validation
│   ├── 06_grant_permissions.sql    # User permissions
│   ├── 07_geojson_to_staging.sql   # GeoJSON processing
│   ├── setup_schema.sql            # Main schema orchestrator
│   ├── import_worldcities.sql      # Worldcities data import
│   └── import_renewable_zones.sql  # Renewable zones data import
└── data/                          # Data files
    ├── worldcities.csv
    ├── consolidated_onshore_zones.geojson
    ├── consolidated_offshore_zones.geojson
    ├── onshore_zones.csv          # Generated from GeoJSON
    └── offshore_zones.csv         # Generated from GeoJSON
```

## Execution Flow

1. **GeoJSON Conversion** (`convert_geojson.py`)
   - Converts GeoJSON files to CSV format
   - Handles both onshore and offshore zones
   - Preserves geometry as JSON text
   - Extracts ISO codes and other properties

2. **Database Setup** (`setup_database.bat`)
   - Creates `vervestacks_dashboard` database
   - Creates `vervestacks` schema with PostGIS
   - Creates all tables, indexes, triggers, and permissions
   - Imports worldcities data (241 countries, 48K+ cities)
   - Imports renewable zones data (60K+ onshore, 42K+ offshore)

## Verification

After setup, verify the data:

```sql
-- Check data counts
SELECT 'Countries: ' || COUNT(*) FROM vervestacks.countries;
SELECT 'Cities: ' || COUNT(*) FROM vervestacks.cities;
SELECT 'Onshore zones: ' || COUNT(*) FROM vervestacks.staging_renewable_zones_onshore;
SELECT 'Offshore zones: ' || COUNT(*) FROM vervestacks.staging_renewable_zones_offshore;

-- Sample data
SELECT name, iso_code FROM vervestacks.countries ORDER BY name LIMIT 5;
SELECT iso, country_name, capacity_factor FROM vervestacks.staging_renewable_zones_onshore LIMIT 3;
```

Expected results:
- Countries: 241
- Cities: 48,059
- Onshore zones: 60,342
- Offshore zones: 42,640

## Troubleshooting

### Common Issues

1. **PostgreSQL Connection Issues**
   - Ensure PostgreSQL server is running on localhost:5432
   - Check that postgres user has necessary permissions
   - Verify PostGIS extension is installed

2. **File Not Found Errors**
   - Run scripts from `backend/database` directory
   - Ensure all data files are in `data/` subdirectory
   - Check that GeoJSON files exist before conversion
   - All SQL files are now organized in `schema/` folder

3. **PostGIS Extension Missing**
   - Install PostGIS extension for PostgreSQL
   - Enable in target database: `CREATE EXTENSION postgis;`

4. **Python Script Issues**
   - Ensure Python 3.6+ is installed
   - Check that JSON files are valid GeoJSON format
   - Verify file permissions for reading/writing

### Error Messages

- `relation "temp_worldcities" does not exist`: Normal - temp tables are session-scoped
- `No such file or directory`: Check file paths and working directory
- `permission denied`: Ensure PostgreSQL user has necessary permissions
- `extension "postgis" does not exist`: Install PostGIS extension

## Production Notes

- Uses `timestamp` without timezone (as requested)
- Permissions are set for development (not tightened for production)
- PostGIS extension is required for spatial operations
- All scripts are idempotent (can be run multiple times safely)
- Uses client-side `\copy` with PROGRAM mode for robust file access
- All SQL files organized in `schema/` folder for better maintainability
- Streamlined setup process with no verification steps (as requested)

## Support

For issues or questions, check the troubleshooting section above or refer to the PostgreSQL and PostGIS documentation.