-- VerveStacks Dashboard Database Schema Setup
-- This file creates the schema and sets up the basic database structure
-- NOTE: This assumes you're already connected to the vervestacks_dashboard database

-- Switch to vervestacks_dashboard database if not already connected
\connect vervestacks_dashboard

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS vervestacks;

-- Set search path to use our schema
SET search_path TO vervestacks, public;

-- PostGIS extension removed - using TEXT columns for geometry JSON instead

-- Show schema creation status
SELECT 'VerveStacks schema created successfully!' as status;
