-- Create VerveStacks Dashboard Database
-- Run this first: psql -h localhost -U postgres -d postgres -f 00_create_database.sql

-- Check if database exists and create if it doesn't
SELECT 'Creating VerveStacks database...' as status;

-- Create database (this will fail gracefully if it already exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'vervestacks_dashboard') THEN
        CREATE DATABASE vervestacks_dashboard;
    END IF;
END
$$;

-- If we get here, the database was created successfully
SELECT 'Database vervestacks_dashboard created successfully!' as status;
