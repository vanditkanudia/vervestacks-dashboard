@echo off
REM ========================================
REM VerveStacks Database Setup - CI + Interactive
REM ========================================

setlocal ENABLEDELAYEDEXPANSION

REM ----------------------------------------
REM 1) Database configuration
REM ----------------------------------------
set "DB_NAME=vervestacks_dashboard"
set "PG_HOST=localhost"
set "PG_PORT=5432"
set "PG_USER=postgres"

REM ----------------------------------------
REM 2) Detect CI / non-interactive mode
REM    (GitHub Actions step sets DB_SETUP_NONINTERACTIVE=true)
REM ----------------------------------------
if /I "%DB_SETUP_NONINTERACTIVE%"=="true" (
    set "NONINTERACTIVE=1"
) else (
    set "NONINTERACTIVE=0"
)

echo ========================================
echo VerveStacks Database Setup
echo ========================================
echo Current directory: %CD%
echo.

REM ----------------------------------------
REM 3) Check CSV data files
REM ----------------------------------------
echo Checking data files...

if not exist "data\regions.csv" (
    echo ERROR: data\regions.csv not found
    goto :ERROR_END
)

if not exist "data\resources.csv" (
    echo ERROR: data\resources.csv not found
    goto :ERROR_END
)

if not exist "data\renewable_zones.csv" (
    echo ERROR: data\renewable_zones.csv not found
    goto :ERROR_END
)

if not exist "data\data_overview.csv" (
    echo ERROR: data\data_overview.csv not found
    goto :ERROR_END
)

echo All data files found
echo.

REM ----------------------------------------
REM 4) Check SQL schema files
REM ----------------------------------------
echo Checking SQL files...

if not exist "schema\create_database.sql" (
    echo ERROR: schema\create_database.sql not found
    goto :ERROR_END
)

if not exist "schema\create_tables.sql" (
    echo ERROR: schema\create_tables.sql not found
    goto :ERROR_END
)

if not exist "schema\import_regions.sql" (
    echo ERROR: schema\import_regions.sql not found
    goto :ERROR_END
)

if not exist "schema\import_resources.sql" (
    echo ERROR: schema\import_resources.sql not found
    goto :ERROR_END
)

if not exist "schema\import_renewable_zones.sql" (
    echo ERROR: schema\import_renewable_zones.sql not found
    goto :ERROR_END
)

if not exist "schema\import_data_overview.sql" (
    echo ERROR: schema\import_data_overview.sql not found
    goto :ERROR_END
)

echo All SQL files found
echo.

REM ----------------------------------------
REM 5) Show config and handle password
REM ----------------------------------------
echo ========================================
echo Ready to setup database
echo ========================================
echo Database: %DB_NAME%
echo Host    : %PG_HOST%:%PG_PORT%
echo User    : %PG_USER%
echo.

REM Password handling:
REM - In CI: DB_SETUP_NONINTERACTIVE=true and PGPASSWORD is set by workflow.
REM - Local/manual: prompt if PGPASSWORD is empty.
if "%NONINTERACTIVE%"=="1" (
    if "%PGPASSWORD%"=="" (
        echo ERROR: DB_SETUP_NONINTERACTIVE is true but PGPASSWORD is not set.
        goto :ERROR_END
    ) else (
        echo Using PGPASSWORD from environment (non-interactive mode)...
        echo.
    )
) else (
    echo Enter PostgreSQL password for user '%PG_USER%':
    set /p "PGPASSWORD=Password: "
    echo.
)

REM ----------------------------------------
REM 6) Test connection
REM ----------------------------------------
echo Testing connection...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -c "SELECT 1;" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Unable to connect to PostgreSQL with the provided credentials.
    goto :ERROR_END
)

echo Connection successful.
echo.

REM ----------------------------------------
REM 7) Create database and schema
REM ----------------------------------------
echo ========================================
echo Step 1: Creating database and schema...
echo ========================================
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -f schema\create_database.sql
if errorlevel 1 (
    echo ERROR: Failed to create database
    goto :ERROR_END
)
echo.

REM ----------------------------------------
REM 8) Create tables
REM ----------------------------------------
echo Step 2: Creating tables...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema\create_tables.sql
if errorlevel 1 (
    echo ERROR: Failed to create tables
    goto :ERROR_END
)
echo.

REM ----------------------------------------
REM 9) Import regions data
REM ----------------------------------------
echo Step 3: Importing regions data...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema\import_regions.sql
if errorlevel 1 (
    echo ERROR: Failed to import regions data
    goto :ERROR_END
)
echo.

REM ----------------------------------------
REM 10) Import resources data
REM ----------------------------------------
echo Step 4: Importing resources data...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema\import_resources.sql
if errorlevel 1 (
    echo ERROR: Failed to import resources data
    goto :ERROR_END
)
echo.

REM ----------------------------------------
REM 11) Import renewable zones data
REM ----------------------------------------
echo Step 5: Importing renewable zones data...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema\import_renewable_zones.sql
if errorlevel 1 (
    echo ERROR: Failed to import renewable zones data
    goto :ERROR_END
)
echo.

REM ----------------------------------------
REM 12) Import data overview data
REM ----------------------------------------
echo Step 6: Importing data overview data...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f schema\import_data_overview.sql
if errorlevel 1 (
    echo ERROR: Failed to import data overview data
    goto :ERROR_END
)
echo.

REM ----------------------------------------
REM 13) Success
REM ----------------------------------------
echo ========================================
echo Setup Complete - SUCCESS!
echo ========================================
echo Database: %DB_NAME%
echo Schema  : vervestacks
echo All data imported successfully.
echo.
echo Your VerveStacks dashboard database is ready!
echo.

REM Clear password from environment
set PGPASSWORD=

if not "%NONINTERACTIVE%"=="1" (
    echo.
    pause
)

endlocal
exit /b 0

REM ----------------------------------------
REM ERROR HANDLER
REM ----------------------------------------
:ERROR_END
echo.
echo ========================================
echo Setup FAILED
echo ========================================
REM Clear password
set PGPASSWORD=
if not "%NONINTERACTIVE%"=="1" (
    echo.
    pause
)
endlocal
exit /b 1