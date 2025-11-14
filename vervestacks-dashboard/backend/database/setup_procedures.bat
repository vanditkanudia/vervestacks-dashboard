@echo off
REM ========================================
REM VerveStacks Procedures Setup
REM ========================================
REM This script runs all PostgreSQL procedures in the procedure folder
REM Run from: vervestacks-dashboard/backend/database/

setlocal enabledelayedexpansion

REM Database configuration
set PG_HOST=localhost
set PG_PORT=5432
set PG_USER=postgres
set DB_NAME=vervestacks_dashboard

echo.
echo ========================================
echo VerveStacks Procedures Setup
echo ========================================
echo Current directory: %CD%
echo.

REM Check if procedure folder exists
if not exist "schema\procedure" (
    echo ERROR: schema\procedure folder not found
    pause
    exit /b 1
)

REM Count procedure files
set /a procedure_count=0
for %%f in (schema\procedure\*.sql) do (
    set /a procedure_count+=1
)

if %procedure_count%==0 (
    echo ERROR: No .sql files found in schema\procedure folder
    pause
    exit /b 1
)

echo Found %procedure_count% procedure files in schema\procedure folder
echo.

REM Prompt for password
set /p PG_PASSWORD="Enter PostgreSQL password for user '%PG_USER%': "

REM Set password environment variable
set PGPASSWORD=%PG_PASSWORD%

echo.
echo Testing connection...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -c "SELECT 'Connection successful' as status;" >nul 2>&1
if errorlevel 1 (
    echo ERROR: PostgreSQL connection failed
    echo Please check your password and ensure PostgreSQL is running
    pause
    exit /b 1
)

echo Connection successful!
echo.

echo ========================================
echo Running Procedures
echo ========================================
echo Database: %DB_NAME%
echo Host: %PG_HOST%:%PG_PORT%
echo User: %PG_USER%
echo.

REM Run each procedure file
set /a success_count=0
set /a failed_count=0

for %%f in (schema\procedure\*.sql) do (
    echo Running procedure: %%~nxf
    psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d %DB_NAME% -f "%%f"
    if errorlevel 1 (
        echo ERROR: Failed to run procedure %%~nxf
        set /a failed_count+=1
    ) else (
        echo SUCCESS: Procedure %%~nxf completed
        set /a success_count+=1
    )
    echo.
)

echo ========================================
echo Procedures Setup Complete
echo ========================================
echo Total procedures: %procedure_count%
echo Successful: %success_count%
echo Failed: %failed_count%
echo.

if %failed_count%==0 (
    echo All procedures executed successfully!
    echo Your VerveStacks procedures are ready!
) else (
    echo WARNING: %failed_count% procedures failed
    echo Please check the error messages above
)

echo.

REM Clear password from environment
set PGPASSWORD=

pause
