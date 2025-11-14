-- VerveStacks Dashboard Database Functions (Minimal)
-- Keep only generic utilities; domain-specific functions deferred

-- Set search path
SET search_path TO vervestacks, public;

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION vervestacks.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to clean cache entries
-- (Deprecated for now; analysis_cache table removed)
-- CREATE OR REPLACE FUNCTION vervestacks.clean_expired_cache() ...

-- No domain-specific validation until final tables are defined

-- Show function creation status
SELECT 'Utility functions created successfully!' as status;
