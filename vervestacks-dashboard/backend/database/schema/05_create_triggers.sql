-- VerveStacks Dashboard Database Triggers (Minimal)
-- Keep only generic update triggers and ISO validation

-- Set search path
SET search_path TO vervestacks, public;

-- ============================================================================
-- UPDATE TRIGGERS
-- ============================================================================

-- Make trigger creation idempotent for re-runs
DROP TRIGGER IF EXISTS update_users_updated_at ON vervestacks.users;
DROP TRIGGER IF EXISTS update_dashboard_sessions_updated_at ON vervestacks.dashboard_sessions;

-- Trigger for users table updated_at
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON vervestacks.users 
    FOR EACH ROW EXECUTE FUNCTION vervestacks.update_updated_at_column();

-- Trigger for dashboard_sessions table updated_at
CREATE TRIGGER update_dashboard_sessions_updated_at 
    BEFORE UPDATE ON vervestacks.dashboard_sessions 
    FOR EACH ROW EXECUTE FUNCTION vervestacks.update_updated_at_column();

-- ============================================================================
-- DATA VALIDATION TRIGGERS
-- ============================================================================

-- Function to validate country ISO codes
CREATE OR REPLACE FUNCTION vervestacks.validate_country_iso()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate ISO code format (3 characters)
    IF LENGTH(NEW.iso_code) != 3 THEN
        RAISE EXCEPTION 'ISO code must be exactly 3 characters long';
    END IF;
    
    -- Validate ISO2 code format (2 characters) if provided
    IF NEW.iso2_code IS NOT NULL AND LENGTH(NEW.iso2_code) != 2 THEN
        RAISE EXCEPTION 'ISO2 code must be exactly 2 characters long';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for countries table ISO validation
DROP TRIGGER IF EXISTS validate_countries_iso ON vervestacks.countries;
CREATE TRIGGER validate_countries_iso
    BEFORE INSERT OR UPDATE ON vervestacks.countries
    FOR EACH ROW EXECUTE FUNCTION vervestacks.validate_country_iso();
-- Show trigger creation status
SELECT 'Minimal triggers created successfully!' as status;
