-- ============================================================================
-- Migration Script: Allow NULL in mw column
-- ============================================================================
-- This script updates the era5_combined_data_2030 table to allow NULL values
-- in the mw column. This prevents holes in profiles when importing data with
-- missing demand values.
--
-- Run this if you have an existing database with the NOT NULL constraint:
-- psql -U postgres -d vervestacks_dashboard -f schema/migrate_allow_null_mw.sql
-- ============================================================================

SET search_path TO vervestacks, public;

-- Check if table exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'vervestacks' 
        AND table_name = 'era5_combined_data_2030'
    ) THEN
        RAISE NOTICE 'Table era5_combined_data_2030 does not exist. Skipping migration.';
        RETURN;
    END IF;
END $$;

-- Drop NOT NULL constraint on mw column
DO $$
BEGIN
    -- Check if constraint exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'vervestacks'
        AND table_name = 'era5_combined_data_2030'
        AND column_name = 'mw'
        AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE vervestacks.era5_combined_data_2030 
        ALTER COLUMN mw DROP NOT NULL;
        
        RAISE NOTICE '✅ Successfully removed NOT NULL constraint from mw column';
    ELSE
        RAISE NOTICE 'ℹ️  mw column already allows NULL values. No changes needed.';
    END IF;
END $$;

-- Update stored procedure to handle NULLs
\echo 'Updating stored procedure to handle NULL values...'
\i schema/procedure/usp_get_demand_profile.sql

\echo ''
\echo '========================================'
\echo '✅ Migration complete!'
\echo '========================================'
\echo 'The mw column now allows NULL values.'
\echo 'NULL values will be converted to 0 in stored procedures.'
\echo ''

