-- VerveStacks Dashboard Database Permissions
-- This file grants appropriate permissions to database users

-- Set search path
SET search_path TO vervestacks, public;

-- ============================================================================
-- SCHEMA PERMISSIONS
-- ============================================================================

-- Grant all privileges on schema to postgres user
GRANT ALL PRIVILEGES ON SCHEMA vervestacks TO postgres;

-- Grant usage on schema to postgres user
GRANT USAGE ON SCHEMA vervestacks TO postgres;

-- ============================================================================
-- TABLE PERMISSIONS
-- ============================================================================

-- Grant all privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA vervestacks TO postgres;

-- Grant all privileges on all existing sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA vervestacks TO postgres;

-- Grant all privileges on all existing functions
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA vervestacks TO postgres;

-- ============================================================================
-- DEFAULT PRIVILEGES FOR FUTURE OBJECTS
-- ============================================================================

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA vervestacks 
    GRANT ALL ON TABLES TO postgres;

-- Set default privileges for future sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA vervestacks 
    GRANT ALL ON SEQUENCES TO postgres;

-- Set default privileges for future functions
ALTER DEFAULT PRIVILEGES IN SCHEMA vervestacks 
    GRANT ALL ON FUNCTIONS TO postgres;

-- ============================================================================
-- APPLICATION USER PERMISSIONS (Optional)
-- ============================================================================

-- Create application user if it doesn't exist
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'vervestacks_app') THEN
--         CREATE ROLE vervestacks_app WITH LOGIN PASSWORD 'your_secure_password';
--     END IF;
-- END
-- $$;

-- Grant necessary permissions to application user
-- GRANT USAGE ON SCHEMA vervestacks TO vervestacks_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA vervestacks TO vervestacks_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA vervestacks TO vervestacks_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA vervestacks TO vervestacks_app;

-- Set default privileges for application user
-- ALTER DEFAULT PRIVILEGES IN SCHEMA vervestacks 
--     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vervestacks_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA vervestacks 
--     GRANT USAGE, SELECT ON SEQUENCES TO vervestacks_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA vervestacks 
--     GRANT EXECUTE ON FUNCTIONS TO vervestacks_app;

-- ============================================================================
-- READ-ONLY USER PERMISSIONS (Optional)
-- ============================================================================

-- Create read-only user if it doesn't exist
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'vervestacks_readonly') THEN
--         CREATE ROLE vervestacks_readonly WITH LOGIN PASSWORD 'readonly_password';
--     END IF;
-- END
-- $$;

-- Grant read-only permissions
-- GRANT USAGE ON SCHEMA vervestacks TO vervestacks_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA vervestacks TO vervestacks_readonly;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA vervestacks TO vervestacks_readonly;

-- Set default read-only privileges
-- ALTER DEFAULT PRIVILEGES IN SCHEMA vervestacks 
--     GRANT SELECT ON TABLES TO vervestacks_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA vervestacks 
--     GRANT EXECUTE ON FUNCTIONS TO vervestacks_readonly;

-- ============================================================================
-- SECURITY POLICIES (Optional - for Row Level Security)
-- ============================================================================

-- Enable Row Level Security on sensitive tables (if needed)
-- ALTER TABLE vervestacks.users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE vervestacks.dashboard_sessions ENABLE ROW LEVEL SECURITY;

-- Create policy for users table (users can only see their own data)
-- CREATE POLICY user_isolation ON vervestacks.users
--     FOR ALL TO vervestacks_app
--     USING (id = current_setting('app.current_user_id')::INTEGER);

-- Create policy for dashboard sessions (users can only see their own sessions)
-- CREATE POLICY session_isolation ON vervestacks.dashboard_sessions
--     FOR ALL TO vervestacks_app
--     USING (user_id = current_setting('app.current_user_id')::INTEGER);

-- ============================================================================
-- PERFORMANCE OPTIMIZATION PERMISSIONS
-- ============================================================================

-- Grant permissions for creating indexes (if needed for application user)
-- GRANT CREATE ON SCHEMA vervestacks TO vervestacks_app;

-- ============================================================================
-- MONITORING PERMISSIONS (Optional)
-- ============================================================================

-- Grant permissions for monitoring queries
-- GRANT SELECT ON pg_stat_activity TO vervestacks_app;
-- GRANT SELECT ON pg_stat_user_tables TO vervestacks_app;
-- GRANT SELECT ON pg_stat_user_indexes TO vervestacks_app;

-- Show permissions status
SELECT 'All permissions granted successfully!' as status;
