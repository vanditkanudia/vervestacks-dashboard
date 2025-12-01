from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import sys
import os
import numpy as np
import asyncpg
from contextlib import asynccontextmanager
import asyncio

# Add project paths for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '2_ts_design', 'scripts'))

# Import and initialize the constructor using importlib (required for files with numbers)
import importlib.util
script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '2_ts_design', 'scripts', '8760_supply_demand_constructor.py')
spec = importlib.util.spec_from_file_location("supply_module", script_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Import VerveStacks service
from services.vervestacks_service import VerveStacksService

# Import database configuration
from config.database_config import get_database_config, get_config_instance

# Initialize services
data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', '')
constructor = module.Supply8760Constructor(data_path)
vervestacks_service = VerveStacksService(cache_dir="cache")

print(f"✅ Constructor initialized successfully with data path: {data_path}")
print(f"✅ VerveStacks service initialized successfully")

# Global database pool
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI
    Handles startup and shutdown events
    """
    global db_pool
    
    # Startup: Initialize database connection pool
    print("\n🚀 Starting FastAPI application...")
    try:
        db_config = get_database_config()
        db_pool = await asyncpg.create_pool(**db_config)
        print(f"✅ Database connection pool created successfully")
        print(f"   Pool size: {db_config['min_size']}-{db_config['max_size']} connections")
    except Exception as e:
        print(f"❌ Failed to create database pool: {e}")
        print("⚠️  Application will start but database queries will fail")
        db_pool = None
    
    yield  # Application runs here
    
    # Shutdown: Close database connection pool
    print("\n🛑 Shutting down FastAPI application...")
    if db_pool:
        await db_pool.close()
        print("✅ Database connection pool closed")

app = FastAPI(title="VerveStacks Python API", lifespan=lifespan)

# Dependency injection for services
def get_vervestacks_service():
    return vervestacks_service

def get_supply_constructor():
    return constructor

def get_db_pool():
    """Get database connection pool"""
    if db_pool is None:
        raise HTTPException(
            status_code=503, 
            detail="Database connection pool not available"
        )
    return db_pool

class GenerationRequest(BaseModel):
    iso_code: str
    year: int
    total_generation_twh: Optional[float] = None
    demand_year: Optional[int] = 2030
    weather_year: Optional[int] = 2011

@app.get("/health")
async def health_check():
    """Health check endpoint with database connectivity test"""
    db_status = "disconnected"
    db_details = None
    
    # Test database connection
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    db_status = "connected"
                    pool_size = db_pool.get_size()
                    db_details = {
                        "pool_size": pool_size,
                        "pool_free": db_pool.get_idle_size(),
                        "pool_max": db_pool.get_max_size()
                    }
        except Exception as e:
            db_status = f"error: {str(e)}"
    
    return {
        "status": "OK", 
        "python_module": constructor is not None,
        "vervestacks_service": vervestacks_service is not None,
        "database": {
            "status": db_status,
            "details": db_details
        }
    }

# Existing endpoints...
@app.post("/generate-profile")
async def generate_profile(
    request: GenerationRequest, 
    constructor = Depends(get_supply_constructor),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Generate demand-shaped generation profile using PostgreSQL demand data.
    
    This endpoint uses the database-backed method for 10-600x faster performance
    compared to the previous CSV-based approach.
    
    Request Body:
        iso_code: 3-letter ISO code (e.g., 'USA', 'DEU')
        year: Year for EMBER generation data (e.g., 2022)
        total_generation_twh: Optional - User can provide or will use EMBER data
        demand_year: Optional - Scenario year for demand (default: 2030)
        weather_year: Optional - Weather pattern year (default: 2011)
    
    Returns:
        8760-hour generation profile shaped by demand pattern
    """
    if not constructor:
        raise HTTPException(status_code=500, detail="Python module not available")
    
    try:
        profile = await constructor.create_demand_shaped_generation_from_ember_db(
            iso_code=request.iso_code,
            year=request.year,
            db_pool=pool,
            total_generation_twh=request.total_generation_twh,
            demand_year=request.demand_year,
            weather_year=request.weather_year
        )
        
        return {
            "success": True,
            "profile": profile.tolist() if hasattr(profile, 'tolist') else list(profile)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capacity-by-fuel/{iso_code}/{year}")
def get_capacity_by_fuel(iso_code: str, year: int, 
                              constructor = Depends(get_supply_constructor)):

# def get_capacity_by_fuel(iso_code: str, year: int):
    """Get generation capacity breakdown by fuel type."""
    if not constructor:
        raise HTTPException(status_code=500, detail="Python module not available")
    
    try:
        capacity_data = constructor.get_capacity_by_fuel(iso_code, year)
        
        if not capacity_data:
            raise HTTPException(status_code=404, detail=f"No capacity data found for {iso_code} in {year}")
        
       
        
        return {
            "success": True,
            "iso_code": iso_code,
            "year": year,
            "capacity": capacity_data,
            
            "total_capacity_gw": sum(fuel['capacity_gw'] for fuel in capacity_data.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_eligible_solar_cells(iso_code: str, year: int = 2022, capacity_gw: float = None):
    """
    Get selected solar grid cells based on capacity target using merit order (best CF first).
    
    Parameters:
    - iso_code: ISO country code (e.g., 'DEU', 'USA')
    - year: Year for capacity data (default: 2022)
    - capacity_gw: Target capacity in GW. If None, uses actual installed capacity from IRENA/EMBER
    
    Returns:
    Dictionary with cell_id as keys and cell info (capacity_mw, capacity_factor, utilization_ratio) as values
    """
    try:
        # Load renewable data for this ISO
        solar_cells, wind_cells, windoff_cells, original_solar_cells, original_wind_cells = constructor._load_renewable_data(iso_code, force_reload=False)
        
        # Get target capacity
        if capacity_gw is None:
            capacity_data = constructor.get_capacity_by_fuel(iso_code, year)
            capacity_gw = capacity_data.get('Solar', {}).get('capacity_gw', 0)
            
            if capacity_gw == 0:
                # Fallback to different key formats
                capacity_gw = capacity_data.get('solar', {}).get('capacity_gw', 0)
        
        if capacity_gw <= 0:
            return {
                "error": f"No solar capacity data available for {iso_code} in {year}",
                "cells": {}
            }
        
        # Select cells using merit order
        selected_cells = constructor.select_cells_by_capacity(
            solar_cells, 
            target_capacity_gw=capacity_gw,
            technology='solar'
        )
        
        return selected_cells
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_eligible_wind_cells(iso_code: str, year: int = 2022, capacity_gw: float = None):
    """
    Get selected wind grid cells based on capacity target using merit order (best CF first).
    
    Parameters:
    - iso_code: ISO country code (e.g., 'DEU', 'USA')
    - year: Year for capacity data (default: 2022)
    - capacity_gw: Target capacity in GW. If None, uses actual installed capacity from IRENA/EMBER
    
    Returns:
    Dictionary with cell_id as keys and cell info (capacity_mw, capacity_factor, utilization_ratio) as values
    """
    try:
        # Load renewable data for this ISO
        solar_cells, wind_cells, windoff_cells, original_solar_cells, original_wind_cells = constructor._load_renewable_data(iso_code, force_reload=False)
        
        # Get target capacity
        if capacity_gw is None:
            capacity_data = constructor.get_capacity_by_fuel(iso_code, year)
            capacity_gw = capacity_data.get('Windon', {}).get('capacity_gw', 0)
            
            if capacity_gw == 0:
                # Fallback to different key formats
                capacity_gw = capacity_data.get('wind', {}).get('capacity_gw', 0)
        
        if capacity_gw <= 0:
            return {
                "error": f"No wind capacity data available for {iso_code} in {year}",
                "cells": {}
            }
        
        # Select cells using merit order
        selected_cells = constructor.select_cells_by_capacity(
            wind_cells, 
            target_capacity_gw=capacity_gw,
            technology='wind'
        )
        
        return selected_cells
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_eligible_windoff_cells(iso_code: str, year: int = 2022, capacity_gw: float = None):
    """
    Get selected offshore wind grid cells based on capacity target using merit order (best CF first).
    
    Parameters:
    - iso_code: ISO country code (e.g., 'DEU', 'USA')
    - year: Year for capacity data (default: 2022)
    - capacity_gw: Target capacity in GW. If None, uses actual installed capacity from IRENA/EMBER
    
    Returns:
    Dictionary with cell_id as keys and cell info (capacity_mw, capacity_factor, utilization_ratio) as values
    """
    try:
        # Load renewable data for this ISO
        solar_cells, wind_cells, windoff_cells, original_solar_cells, original_wind_cells = constructor._load_renewable_data(iso_code, force_reload=False)
        
        # Get target capacity
        if capacity_gw is None:
            capacity_data = constructor.get_capacity_by_fuel(iso_code, year)
            capacity_gw = capacity_data.get('windoff', {}).get('capacity_gw', 0)
            
            if capacity_gw == 0:
                # Fallback to different key formats
                capacity_gw = capacity_data.get('windoff', {}).get('capacity_gw', 0)
        
        if capacity_gw <= 0:
            return {
                "error": f"No offshore wind capacity data available for {iso_code} in {year}",
                "cells": {}
            }
        
        # Select cells using merit order
        selected_cells = constructor.select_cells_by_capacity(
            windoff_cells, 
            target_capacity_gw=capacity_gw,
            technology='windoff'
        )
        
        return selected_cells
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generation-profile/solar-hourly/{iso_code}")
def get_solar_hourly_profile(iso_code: str, year: int = 2022, capacity_gw: float = None, constructor = Depends(get_supply_constructor)):
# def get_solar_hourly_profile(iso_code: str, year: int = 2022, capacity_gw: float = None):
    """
    Generate 8760-hour solar generation profile.
    
    Parameters:
    - iso_code: ISO country code (e.g., 'DEU', 'USA')
    - year: Year for capacity data (default: 2022)
    - capacity_gw: Target capacity in GW. If None, uses actual installed capacity
    
    Returns:
    List of 8760 generation values in MW (hour 1 to 8760)
    """
    try:
        # Step 1: Select optimal cells
        selected_cells = get_eligible_solar_cells(iso_code, year, capacity_gw)
        
        if not selected_cells or 'error' in selected_cells:
            return {"success": False, "message": f"Could not select cells for {iso_code}",
             "profile": [0.0] * 8760,
              "selected_cells": {}}
        
        # Step 2: Generate hourly profile
        hourly_profile = constructor.generate_hourly_profile_from_cells(
            selected_cells, iso_code, 'solar'
        )
        
        return {"success": True, "profile": hourly_profile, "selected_cells": selected_cells}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generation-profile/wind-hourly/{iso_code}")
def get_wind_hourly_profile(iso_code: str, year: int = 2022, capacity_gw: float = None, constructor = Depends(get_supply_constructor)):
# async def get_wind_hourly_profile(iso_code: str, year: int = 2022, capacity_gw: float = None):
    """
    Generate 8760-hour wind generation profile.
    
    Parameters:
    - iso_code: ISO country code (e.g., 'DEU', 'USA')
    - year: Year for capacity data (default: 2022)
    - capacity_gw: Target capacity in GW. If None, uses actual installed capacity
    
    Returns:
    List of 8760 generation values in MW (hour 1 to 8760)
    """
    try:
        # Step 1: Select optimal cells
        selected_cells = get_eligible_wind_cells(iso_code, year, capacity_gw)
        
        if not selected_cells or 'error' in selected_cells:
            return {"success": False, "message": f"Could not select cells for {iso_code}",
             "profile": [0.0] * 8760,
              "selected_cells": {}}
        
        # Step 2: Generate hourly profile
        hourly_profile = constructor.generate_hourly_profile_from_cells(
            selected_cells, iso_code, 'wind'
        )
        
        return {"success": True, "profile": hourly_profile, "selected_cells": selected_cells}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generation-profile/windoff-hourly/{iso_code}")
def get_windoff_hourly_profile(iso_code: str, year: int = 2022, capacity_gw: float = None, constructor = Depends(get_supply_constructor)):
# async def get_windoff_hourly_profile(iso_code: str, year: int = 2022, capacity_gw: float = None):
    """
    Generate 8760-hour offshore wind generation profile.
    
    Parameters:
    - iso_code: ISO country code (e.g., 'DEU', 'USA')
    - year: Year for capacity data (default: 2022)
    - capacity_gw: Target capacity in GW. If None, uses actual installed capacity
    
    Returns:
    List of 8760 generation values in MW (hour 1 to 8760)
    """
    try:
        # Step 1: Select optimal cells
        selected_cells = get_eligible_windoff_cells(iso_code, year, capacity_gw)
        
        if not selected_cells or 'error' in selected_cells:
            return {"success": False, "message": f"Could not select cells for {iso_code}",
             "profile": [0.0] * 8760,
              "selected_cells": {}}
        
        # Step 2: Generate hourly profile
        hourly_profile = constructor.generate_hourly_profile_from_cells(
            selected_cells, iso_code, 'windoff'
        )
        
        return {"success": True, "profile": hourly_profile, "selected_cells": selected_cells}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Cache monitoring endpoint
@app.get("/cache/shape-cache-stats")
def get_shape_cache_stats():
    """Get performance statistics for the grid cell shape cache."""
    try:
        from shared_data_loader import get_shape_cache
        cache = get_shape_cache()
        return {
            "stats": cache.get_cache_stats(),
            "info": cache.get_cache_info()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NEW VERVESTACKS ENDPOINTS
@app.get("/overview/energy-analysis/{iso_code}")
def get_energy_analysis(iso_code: str, year: int = 2022,
                             service: VerveStacksService = Depends(get_vervestacks_service)):
    """Get comprehensive energy analysis data for dashboard charts."""
    try:
        data = service.get_energy_analysis(iso_code, year)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/overview/technology-mix/{iso_code}")
def get_technology_mix(iso_code: str, year: int = 2022,
                            service: VerveStacksService = Depends(get_vervestacks_service)):
    """Get technology mix and capacity data."""
    try:
        data = service.get_technology_mix(iso_code, year)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/overview/co2-intensity/{iso_code}")
def get_co2_intensity(iso_code: str, year: int = 2022,
                           service: VerveStacksService = Depends(get_vervestacks_service)):
    """Get CO2 intensity and fuel consumption data."""
    try:
        data = service.get_co2_intensity(iso_code, year)
        return {
            "success": True,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/overview/existing-stock/{iso_code}")
def get_existing_stock(iso_code: str,
                            service: VerveStacksService = Depends(get_vervestacks_service)):
    """Get existing stock data for infrastructure analysis."""
    try:
        result = service.get_existing_stock_metrics(iso_code)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "success": True,
            "data": result["data"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/renewable-potential/solar-zones/{iso_code}")
def get_solar_zones(iso_code: str,
                          service: VerveStacksService = Depends(get_vervestacks_service)):
    """Get solar renewable energy zones for a country."""
    try:
        result = service.get_solar_renewable_zones(iso_code)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "success": True,
            "data": result["data"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/renewable-potential/wind-zones/{iso_code}")
def get_wind_zones(iso_code: str,
                         wind_type: str = 'onshore',
                         service: VerveStacksService = Depends(get_vervestacks_service)):
    """Get wind renewable energy zones for a country (offshore or onshore)."""
    try:
        if wind_type not in ['offshore', 'onshore']:
            raise HTTPException(status_code=400, detail="wind_type must be 'offshore' or 'onshore'")
        
        result = service.get_wind_renewable_zones(iso_code, wind_type)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "success": True,
            "data": result["data"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transmission/data/{iso_code}")
def get_transmission_data(iso_code: str,
                               clusters: Optional[int] = None,
                               service: VerveStacksService = Depends(get_vervestacks_service)):
    """Get transmission line data from create_regions_simple.py for dashboard visualization."""
    try:
        result = service.get_transmission_data(iso_code, clusters)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "success": True,
            "data": result["data"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# DEPRECATED: Transmission network data now comes from PostgreSQL
# via tables vervestacks.transmission_buses and vervestacks.transmission_lines
# using stored procedure usp_get_transmission_network_data().
# Backend route: /api/transmission/network/:isoCode (Node.js -> PostgreSQL)
# @app.get("/transmission/network/{iso_code}")
# def get_transmission_network_data(iso_code: str,
#                                        service: VerveStacksService = Depends(get_vervestacks_service)):
#     """Legacy endpoint that loaded OSM data via load_network_components."""
#     try:
#         result = service.get_transmission_network_data(iso_code)
#         if not result["success"]:
#             raise HTTPException(status_code=404, detail=result["error"])
#         
#         return {
#             "success": True,
#             "data": result["data"]
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# DEPRECATED: This endpoint has been migrated to PostgreSQL
# Generation plants data is now served from vervestacks.transmission_generation_plants table
# via stored procedure usp_get_transmission_generation_plants()
# Backend route: /api/transmission/generation/:isoCode (Node.js -> PostgreSQL)
# @app.get("/transmission/generation/{iso_code}")
# def get_transmission_generation_data(iso_code: str,
#                                          service: VerveStacksService = Depends(get_vervestacks_service)):
#     """Get transmission generation data from power plants CSV files for dashboard visualization."""
#     try:
#         result = service.get_transmission_generation_data(iso_code)
#         if not result["success"]:
#             raise HTTPException(status_code=404, detail=result["error"])
#         
#         return {
#             "success": True,
#             "data": result["data"]
#         }
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.get("/fuel-colors")
async def get_fuel_colors(service: VerveStacksService = Depends(get_vervestacks_service)):
    """Get fuel colors from Python energy_colors.py file."""
    try:
        result = service.get_fuel_colors()
        if result["success"]:
            return result["data"]
        else:
            raise HTTPException(status_code=500, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ar6-scenario/{iso_code}")
async def get_ar6_scenario(iso_code: str,
                          service: VerveStacksService = Depends(get_vervestacks_service)):
    """Get AR6 scenario drivers for demand and fuel price evolution."""
    try:
        result = service.get_ar6_scenario_drivers(iso_code)
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return {
            "success": True,
            "data": result["data"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# DATABASE TEST ENDPOINTS
# ============================================================================

@app.get("/test/demand-profile/{country_code}")
async def test_demand_profile(
    country_code: str,
    demand_year: int = 2030,
    weather_year: int = 2011,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Test endpoint for demand profile stored procedure (direct database call)
    
    Args:
        country_code: 2-letter country code (e.g., 'AO', 'US')
        demand_year: Scenario year (default: 2030)
        weather_year: Weather pattern year (default: 2011)
    
    Returns:
        JSON with profile statistics and sample values
    """
    try:
        # Call stored procedure
        profile = await pool.fetchval(
            'SELECT vervestacks.usp_get_demand_profile($1, $2, $3)',
            country_code, demand_year, weather_year
        )
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"No demand data found for country: {country_code}, "
                       f"demand_year: {demand_year}, weather_year: {weather_year}"
            )
        
        # Convert to numpy for statistics
        profile_array = np.array(profile, dtype=float)
        
        return {
            "success": True,
            "country_code": country_code,
            "demand_year": demand_year,
            "weather_year": weather_year,
            "statistics": {
                "total_hours": len(profile_array),
                "min_demand_mw": float(np.min(profile_array)),
                "max_demand_mw": float(np.max(profile_array)),
                "avg_demand_mw": float(np.mean(profile_array)),
                "annual_demand_mwh": float(np.sum(profile_array))
            },
            "sample_values": {
                "first_10_hours": profile_array[:10].tolist(),
                "last_10_hours": profile_array[-10:].tolist()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/demand-profile/{iso_code}")
async def get_demand_profile(
    iso_code: str,
    demand_year: int = 2030,
    weather_year: int = 2011,
    constructor = Depends(get_supply_constructor),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get 8760-hour demand profile for an ISO code using database
    
    This endpoint uses the new load_demand_profile_from_db() method which
    queries PostgreSQL instead of loading the 350MB CSV file.
    
    Args:
        iso_code: 3-letter ISO code (e.g., 'USA', 'AUS', 'IND')
        demand_year: Scenario year for demand projection (default: 2030)
        weather_year: Historical weather year (default: 2011)
    
    Returns:
        JSON with profile data and statistics
        
    Example:
        GET /demand-profile/AUS?demand_year=2030&weather_year=2011
    """
    try:
        # Load demand profile from database (NEW METHOD!)
        demand_profile = await constructor.load_demand_profile_from_db(
            iso_code=iso_code,
            db_pool=pool,
            demand_year=demand_year,
            weather_year=weather_year
        )
        
        return {
            "success": True,
            "iso_code": iso_code,
            "demand_year": demand_year,
            "weather_year": weather_year,
            "statistics": {
                "total_hours": len(demand_profile),
                "min_demand_mw": float(np.min(demand_profile)),
                "max_demand_mw": float(np.max(demand_profile)),
                "avg_demand_mw": float(np.mean(demand_profile)),
                "annual_demand_mwh": float(np.sum(demand_profile))
            },
            "profile": demand_profile.tolist(),  # Full 8760-hour profile
            "sample_values": {
                "first_24_hours": demand_profile[:24].tolist(),
                "last_24_hours": demand_profile[-24:].tolist()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading demand profile: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
   
    # result = asyncio.run(test_demand_profile(country_code="AO"))
    # print(result)
