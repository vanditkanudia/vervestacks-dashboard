-- VerveStacks Dashboard Complete Schema Setup
-- PROD-SAFE: This script only creates schema/objects and does not require superuser privileges
-- Run with: psql -h <host> -U <user> -d <db> -f setup_schema.sql
-- Ensure the current working directory is this folder so relative \i paths resolve

-- Set search path
\set ON_ERROR_STOP on
SET search_path TO vervestacks, public;
SET lock_timeout = '5s';
SET statement_timeout = '5min';

-- Show start message
SELECT 'Starting VerveStacks database schema setup...' as status;

-- ============================================================================
-- DATABASE CREATION
-- ============================================================================

\echo 'Creating database...'
\i schema/00_create_database.sql

-- ============================================================================
-- CONNECT TO NEW DATABASE
-- ============================================================================

\echo 'Connecting to vervestacks_dashboard database...'
\connect vervestacks_dashboard

-- ============================================================================
-- SCHEMA CREATION
-- ============================================================================

\echo 'Creating schema and extensions...'
BEGIN;
\i schema/01_create_schema.sql

-- ============================================================================
-- TABLE CREATION
-- ============================================================================

\echo 'Creating all tables...'
\i schema/02_create_tables.sql

-- One-time cleanup for legacy/unused objects (suppress NOTICE if missing)
DO $$
BEGIN
    IF to_regclass('vervestacks.staging_worldcities') IS NOT NULL THEN
        EXECUTE 'DROP TABLE vervestacks.staging_worldcities';
    END IF;
END$$;

-- ============================================================================
-- INDEX CREATION
-- ============================================================================

\echo 'Creating performance indexes...'
\i schema/03_create_indexes.sql

-- ============================================================================
-- FUNCTION CREATION
-- ============================================================================

\echo 'Creating stored procedures and functions (minimal)...'
\i schema/04_create_functions.sql

-- ============================================================================
-- TRIGGER CREATION
-- ============================================================================

\echo 'Creating triggers and validation (minimal)...'
\i schema/05_create_triggers.sql

-- ============================================================================
-- PERMISSIONS
-- ============================================================================

\echo 'Setting up permissions...'
\i schema/06_grant_permissions.sql



-- Show completion message
SELECT 'VerveStacks database schema setup completed successfully!' as status;
SELECT 'Ready for data import and application startup.' as next_step;
