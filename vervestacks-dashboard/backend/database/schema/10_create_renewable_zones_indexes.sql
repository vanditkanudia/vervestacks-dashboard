-- Create indexes for renewable zones tables
-- Improves query performance for ISO-based lookups and spatial operations

SET search_path TO vervestacks, public;

-- ============================================================================
-- Solar zones indexes
-- ============================================================================

-- ISO code index (most common filter)
CREATE INDEX IF NOT EXISTS idx_renewable_zones_solar_iso 
    ON vervestacks.renewable_zones_solar(UPPER(iso));

-- Grid cell index (for joins and lookups)
CREATE INDEX IF NOT EXISTS idx_renewable_zones_solar_grid_cell 
    ON vervestacks.renewable_zones_solar(grid_cell);

-- Spatial index removed (PostGIS not used - geometry stored as JSON TEXT)

-- Capacity filter index (for minimum capacity filtering)
CREATE INDEX IF NOT EXISTS idx_renewable_zones_solar_capacity 
    ON vervestacks.renewable_zones_solar(installed_capacity_potential_mw) 
    WHERE installed_capacity_potential_mw >= 1.0;

-- ============================================================================
-- Wind onshore zones indexes
-- ============================================================================

-- ISO code index
CREATE INDEX IF NOT EXISTS idx_renewable_zones_wind_onshore_iso 
    ON vervestacks.renewable_zones_wind_onshore(UPPER(iso));

-- Grid cell index
CREATE INDEX IF NOT EXISTS idx_renewable_zones_wind_onshore_grid_cell 
    ON vervestacks.renewable_zones_wind_onshore(grid_cell);

-- Spatial index removed (PostGIS not used - geometry stored as JSON TEXT)

-- Capacity filter index
CREATE INDEX IF NOT EXISTS idx_renewable_zones_wind_onshore_capacity 
    ON vervestacks.renewable_zones_wind_onshore(installed_capacity_potential_mw) 
    WHERE installed_capacity_potential_mw >= 1.0;

-- ============================================================================
-- Wind offshore zones indexes
-- ============================================================================

-- ISO code index
CREATE INDEX IF NOT EXISTS idx_renewable_zones_wind_offshore_iso 
    ON vervestacks.renewable_zones_wind_offshore(UPPER(iso));

-- Grid cell index
CREATE INDEX IF NOT EXISTS idx_renewable_zones_wind_offshore_grid_cell 
    ON vervestacks.renewable_zones_wind_offshore(grid_cell);

-- Spatial index removed (PostGIS not used - geometry stored as JSON TEXT)

-- Capacity filter index
CREATE INDEX IF NOT EXISTS idx_renewable_zones_wind_offshore_capacity 
    ON vervestacks.renewable_zones_wind_offshore(installed_capacity_potential_mw) 
    WHERE installed_capacity_potential_mw >= 1.0;

-- ============================================================================
-- Costs table indexes
-- ============================================================================

-- ISO code index
CREATE INDEX IF NOT EXISTS idx_renewable_zone_costs_iso 
    ON vervestacks.renewable_zone_costs(UPPER(iso));

-- Tech index (for filtering by technology)
CREATE INDEX IF NOT EXISTS idx_renewable_zone_costs_tech 
    ON vervestacks.renewable_zone_costs(tech);

-- Composite index for common lookups
CREATE INDEX IF NOT EXISTS idx_renewable_zone_costs_iso_tech 
    ON vervestacks.renewable_zone_costs(UPPER(iso), tech);

\echo 'Renewable zones indexes created successfully'

