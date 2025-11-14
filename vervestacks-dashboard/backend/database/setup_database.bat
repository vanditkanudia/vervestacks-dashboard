@echo off
REM ========================================
REM VerveStacks Database Setup - Password Prompt Version
REM ========================================
REM This script sets up the complete VerveStacks database with all data
REM Run from: vervestacks-dashboard/backend/database/

setlocal enabledelayedexpansion

REM Database configuration
set PG_HOST=localhost
set PG_PORT=5432
set PG_USER=postgres
set DB_NAME=vervestacks_dashboard

echo.
echo ========================================
echo VerveStacks Database Setup
echo ========================================
echo Current directory: %CD%
echo.

REM Check if required data files exist
echo Checking data files...
if not exist "data\worldcities.csv" (
    echo ERROR: data\worldcities.csv not found
    pause
    exit /b 1
)

if not exist "data\onshore_zones.csv" (
    echo ERROR: data\onshore_zones.csv not found
    echo Please run: python convert_geojson.py
    pause
    exit /b 1
)

if not exist "data\offshore_zones.csv" (
    echo ERROR: data\offshore_zones.csv not found
    echo Please run: python convert_geojson.py
    pause
    exit /b 1
)

if not exist "data\data_overview_tab.csv" (
    echo ERROR: data\data_overview_tab.csv not found
    pause
    exit /b 1
)

echo All data files found!
echo.

REM Check if SQL files exist
echo Checking SQL files...
if not exist "schema\setup_schema.sql" (
    echo ERROR: schema\setup_schema.sql not found
    pause
    exit /b 1
)

if not exist "schema\import_worldcities.sql" (
    echo ERROR: schema\import_worldcities.sql not found
    pause
    exit /b 1
)

if not exist "schema\import_renewable_zones.sql" (
    echo ERROR: schema\import_renewable_zones.sql not found
    pause
    exit /b 1
)

if not exist "schema\import_data_overview.sql" (
    echo ERROR: schema\import_data_overview.sql not found
    pause
    exit /b 1
)

echo All SQL files found!
echo.

echo ========================================
echo Ready to setup database
echo ========================================
echo Database: %DB_NAME%
echo Host: %PG_HOST%:%PG_PORT%
echo User: %PG_USER%
echo.

REM Prompt for password
set /p PG_PASSWORD="Enter PostgreSQL password for user '%PG_USER%': "

REM Set password environment variable
set PGPASSWORD=%PG_PASSWORD%

echo.
echo Testing connection...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d postgres -c "SELECT 'Connection successful' as status;" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PostgreSQL connection failed
    echo Please check your password and ensure PostgreSQL is running
    pause
    exit /b 1
)

echo Connection successful!
echo.

REM Step 1: Create database schema
echo Step 1: Creating database schema...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d postgres -f schema/setup_schema.sql
if errorlevel 1 (
    echo ERROR: Schema creation failed
    pause
    exit /b 1
)

REM Step 2: Import worldcities data
echo.
echo Step 2: Importing worldcities data...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema/import_worldcities.sql
if errorlevel 1 (
    echo ERROR: Failed to import worldcities data
    pause
    exit /b 1
)

REM Step 3: Import renewable zones data
echo.
echo Step 3: Importing renewable zones data...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema/import_renewable_zones.sql
if errorlevel 1 (
    echo ERROR: Failed to import renewable zones data
    pause
    exit /b 1
)

REM Step 4: Import data overview data
echo.
echo Step 4: Importing data overview data...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema/import_data_overview.sql
if errorlevel 1 (
    echo ERROR: Failed to import data overview data
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup Complete - SUCCESS!
echo ========================================
echo Database: %DB_NAME%
echo Schema: vervestacks
echo All data imported successfully
echo.
echo Your VerveStacks dashboard database is ready!
echo.

REM Clear password from environment
set PGPASSWORD=

pause