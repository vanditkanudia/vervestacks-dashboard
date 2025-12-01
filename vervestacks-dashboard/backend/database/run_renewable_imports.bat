@echo off
REM ================================================================
REM VerveStacks Renewable Data Import Script
REM Runs the new capacity-factor and merge SQL scripts
REM Usage: run from vervestacks-dashboard/backend/database/
REM ================================================================

setlocal enabledelayedexpansion

REM Default connection settings (override via environment variables if needed)
set PG_HOST=%PG_HOST%
if "%PG_HOST%"=="" set PG_HOST=localhost

set PG_PORT=%PG_PORT%
if "%PG_PORT%"=="" set PG_PORT=5432

set PG_USER=%PG_USER%
if "%PG_USER%"=="" set PG_USER=postgres

set DB_NAME=%DB_NAME%
if "%DB_NAME%"=="" set DB_NAME=vervestacks_dashboard

echo.
echo ================================================
echo VerveStacks Renewable Data Import
echo ================================================
echo Current directory: %CD%
echo Host: %PG_HOST%:%PG_PORT%
echo User: %PG_USER%
echo Database: %DB_NAME%
echo ================================================
echo.

REM psql reads this env var automatically
REM In CI we rely on DB_PASSWORD from environment; no interactive prompt.
set "PGPASSWORD=%DB_PASSWORD%"

IF "%PGPASSWORD%"=="" (
    echo ERROR: DB_PASSWORD environment variable is not set.
    echo Make sure GitHub Actions workflow passes DB_PASSWORD in env.
    exit /b 1
)

REM Verify SQL files exist
if not exist "schema\import_renewable_capacity_factors.sql" (
    echo ERROR: schema\import_renewable_capacity_factors.sql not found
    goto :cleanup
)

if not exist "schema\import_renewable_zones_merge.sql" (
    echo ERROR: schema\import_renewable_zones_merge.sql not found
    goto :cleanup
)

echo Step 1: Importing renewable capacity factors (CSV data)...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema/import_renewable_capacity_factors.sql
if errorlevel 1 (
    echo ERROR: Capacity factor import failed.
    goto :cleanup
)
echo ✔ Capacity factors imported successfully.
echo.

echo Step 2: Merging capacity data with geometry staging tables...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema/import_renewable_zones_merge.sql
if errorlevel 1 (
    echo ERROR: Merge script failed.
    goto :cleanup
)
echo ✔ Renewable zone merge completed successfully.
echo.

echo ================================================
echo Renewable data import: SUCCESS
echo ================================================

:cleanup
REM Clear password for security
set PGPASSWORD=
echo Done.
endlocal

@REM pause