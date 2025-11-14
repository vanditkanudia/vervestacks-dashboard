import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
import os
import sys


def get_solar_renewable_zones( iso_code: str) -> Dict[str, Any]:
    """
    Get solar renewable energy zones data for a country.
    
    This method processes Atlite solar rezoning data to analyze solar energy potential,
    capacity factors, and economic metrics for renewable energy planning.
    
    Args:
        iso_code (str): 3-letter ISO country code (e.g., "IND", "DEU", "USA")
    
    Returns:
        Dict[str, Any]: Dictionary with the following structure:
            - success (bool): True if processing succeeded, False otherwise
            - data (dict): Solar zones data if successful, None otherwise, containing:
                - grid_data (list): List of solar zone data for map visualization
                - statistics (dict): Summary statistics and metrics
                - costs (list): Cost data for the country
            - error (str): Error message if processing failed, None otherwise
    
    Example:
        result = analyzer.get_solar_renewable_zones("DEU")
        if result["success"]:
            solar_data = result["data"]
            print(f"Total Zones: {solar_data['statistics']['total_cells']}")
        else:
            print(f"Error: {result['error']}")
    """
    try:
        import pandas as pd
        from pathlib import Path
        # Add the 1_grids directory to Python path
        scripts_path = Path(__file__).parent / '1_grids' 
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))
        
        # Import the energy colors
        from extract_country_pypsa_network_clustered import load_zones_for_country
        
        # Set up paths for REZoning data using project root
        project_root = Path(__file__).parent
        data_path = project_root / 'data' / 'REZoning'
        solar_file = data_path / 'REZoning_Solar_atlite_cf.csv'
        costs_file = data_path / 'REZoning_costs_per_kw.csv'
        
        # Check if files exist
        if not solar_file.exists():
            return {
                "success": False,
                "data": None,
                "error": f"Solar rezoning data file not found: {solar_file}"
            }
        
        if not costs_file.exists():
            return {
                "success": False,
                "data": None,
                "error": f"Solar costs data file not found: {costs_file}"
            }
        
        # Load data
        solar_data = pd.read_csv(solar_file)
        costs_data = pd.read_csv(costs_file)
        zones_gdf = load_zones_for_country(iso_code, 'onshore')[['grid_cell','geometry']]
        
        # Filter data for the specific ISO
        iso_solar = solar_data[solar_data['ISO'] == iso_code].copy()
        
        if iso_solar.empty:
            return {
                "success": False,
                "data": None,
                "error": f"No solar data found for ISO: {iso_code}"
            }
        
        # Get cost data for this ISO
        iso_costs = costs_data[costs_data['iso'] == iso_code]
        
        # Clean and process the data
        iso_solar = iso_solar.dropna(subset=['lat', 'lng', 'Capacity Factor'])
        
        # Filter by minimum capacity (1MW)
        min_capacity_mw = 1.0
        iso_solar = iso_solar[iso_solar['Installed Capacity Potential (MW)'] >= min_capacity_mw]
        
        # Calculate additional metrics
        iso_solar['Total_Generation_GWh'] = (
            iso_solar['Installed Capacity Potential (MW)'] * 
            iso_solar['Capacity Factor'] * 8760 / 1000
        )
        
        # Create grid statistics
        grid_stats = {
            'iso': iso_code,
            'total\_cells': len(iso_solar),
            'total_capacity_mw': float(iso_solar['Installed Capacity Potential (MW)'].sum()),
            'total_generation_gwh': float(iso_solar['Total_Generation_GWh'].sum()),
            'avg_capacity_factor': float(iso_solar['Capacity Factor'].mean()),
            'avg_lcoe': float(iso_solar['LCOE (USD/MWh)'].mean()),
            'total_suitable_area_km2': float(iso_solar['Suitable Area (km²)'].sum()),
            'cost_data_available': not iso_costs.empty,
            'investment_cost_usd_kw': float(iso_costs['invcost'].iloc[0]) if not iso_costs.empty else None,
            'fixed_om_usd_kw': float(iso_costs['fixom'].iloc[0]) if not iso_costs.empty else None,
            'data_source': 'Atlite (High-resolution ERA5 weather data)',
            'capacity_factor_quality': 'High-resolution, technology-specific modeling'
        }
        
        # Prepare grid data for frontend (limit to essential columns and convert to dict)
        grid_data_columns = [
            'id', 'grid_cell', 'lat', 'lng', 'Capacity Factor', 
            'Installed Capacity Potential (MW)', 'LCOE (USD/MWh)',
            'Suitable Area (km²)', 'Zone Score', 'Total_Generation_GWh', 'geometry'
        ]
        iso_solar = zones_gdf.merge(iso_solar, on='grid_cell', how='inner')
        grid_data = iso_solar[grid_data_columns].copy()
        
        # Convert to dict format for JSON serialization
        grid_data_dict = grid_data.to_dict('records')
        
        # Prepare costs data
        costs_dict = iso_costs.to_dict('records') if not iso_costs.empty else []
        
        return {
            "success": True,
            "data": {
                "grid_data": grid_data_dict,
                "statistics": grid_stats,
                "costs": costs_dict
            }
        }
        
    except Exception as e:
        print(f"Error getting solar renewable zones for {iso_code}: {e}")
        return {
            "success": False,
            "data": None,
            "error": f"Failed to get solar renewable zones: {str(e)}"
        }

def get_wind_renewable_zones( iso_code: str, wind_type: str = 'onshore') -> Dict[str, Any]:
    """
    Get wind renewable energy zones data for a country (offshore or onshore).
    
    This method processes Atlite wind rezoning data to analyze wind energy potential,
    capacity factors, and economic metrics for renewable energy planning.
    
    Args:
        iso_code (str): 3-letter ISO country code (e.g., "IND", "DEU", "USA")
        wind_type (str): Wind type - 'onshore' or 'offshore' (default: 'onshore')
    
    Returns:
        Dict[str, Any]: Dictionary with the following structure:
            - success (bool): True if processing succeeded, False otherwise
            - data (dict): Wind zones data if successful, None otherwise, containing:
                - grid_data (list): List of wind zone data for map visualization
                - statistics (dict): Summary statistics and metrics
                - costs (list): Cost data for the country
            - error (str): Error message if processing failed, None otherwise
    
    Example:
        result = analyzer.get_wind_renewable_zones("DEU", "offshore")
        if result["success"]:
            wind_data = result["data"]
            print(f"Total Zones: {wind_data['statistics']['total_cells']}")
        else:
            print(f"Error: {result['error']}")
    """
    try:
        import pandas as pd
        from pathlib import Path
        # Add the 1_grids directory to Python path
        scripts_path = Path(__file__).parent / '1_grids' 
        if str(scripts_path) not in sys.path:
            sys.path.insert(0, str(scripts_path))
        
        # Import the energy colors
        from extract_country_pypsa_network_clustered import load_zones_for_country
        
        # Set up paths for REZoning data using project root
        project_root = Path(__file__).parent
        data_path = project_root / 'data' / 'REZoning'
        
        # Choose the appropriate wind data file
        if wind_type == 'offshore':
            wind_file = data_path / 'REZoning_WindOffshore_atlite_cf.csv'
            zones_gdf = load_zones_for_country(iso_code, 'offshore')[['grid_cell','geometry']]
        else:
            wind_file = data_path / 'REZoning_WindOnshore_atlite_cf.csv'
            zones_gdf = load_zones_for_country(iso_code, 'onshore')[['grid_cell','geometry']]
        
        costs_file = data_path / 'REZoning_costs_per_kw.csv'
        
        # Check if files exist
        if not wind_file.exists():
            return {
                "success": False,
                "data": None,
                "error": f"Wind {wind_type} data file not found: {wind_file}"
            }
        
        if not costs_file.exists():
            return {
                "success": False,
                "data": None,
                "error": f"Costs data file not found: {costs_file}"
            }
        
        # Load wind data
        wind_data = pd.read_csv(wind_file)
        costs_data = pd.read_csv(costs_file)
        
        # Filter data for the specific ISO
        iso_wind = wind_data[wind_data['ISO'] == iso_code].copy()
        
        if iso_wind.empty:
            return {
                "success": False,
                "data": None,
                "error": f"No {wind_type} wind data found for ISO: {iso_code}"
            }
        
        # Get cost data for this ISO
        iso_costs = costs_data[costs_data['iso'] == iso_code]
        
        # Clean and process the data - wind data uses 'lng' instead of 'long'
        iso_wind = iso_wind.dropna(subset=['lat', 'lng', 'Capacity Factor'])
        iso_wind = iso_wind[iso_wind['Installed Capacity Potential (MW)'] >= 1.0]
        
        # Calculate additional metrics
        iso_wind['Total_Generation_GWh'] = (
            iso_wind['Installed Capacity Potential (MW)'] * 
            iso_wind['Capacity Factor'] * 8760 / 1000
        )
        # Create grid statistics
        grid_stats = {
            'iso': iso_code,
            'wind_type': wind_type,
            'total_cells': len(iso_wind),
            'total_capacity_mw': float(iso_wind['Installed Capacity Potential (MW)'].sum()),
            'total_generation_gwh': float(iso_wind['Total_Generation_GWh'].sum()),
            'avg_capacity_factor': float(iso_wind['Capacity Factor'].mean()),
            'avg_lcoe': float(iso_wind['LCOE (USD/MWh)'].mean()),
            'total_suitable_area_km2': float(iso_wind['Suitable Area (km²)'].sum()),
            'cost_data_available': not iso_costs.empty,
            'investment_cost_usd_kw': float(iso_costs['invcost'].iloc[0]) if not iso_costs.empty else None,
            'fixed_om_usd_kw': float(iso_costs['fixom'].iloc[0]) if not iso_costs.empty else None,
            'data_source': f'Atlite {wind_type.title()} Wind (High-resolution ERA5 weather data)',
            'capacity_factor_quality': 'High-resolution, technology-specific modeling'
        }
        
        # Prepare grid data for frontend (limit to essential columns and convert to dict)
        grid_data_columns = [
            'id', 'grid_cell', 'lat', 'lng', 'Capacity Factor', 
            'Installed Capacity Potential (MW)', 'LCOE (USD/MWh)',
            'Suitable Area (km²)', 'Zone Score', 'Total_Generation_GWh', 'geometry'
        ]
        iso_wind = zones_gdf.merge(iso_wind, on='grid_cell', how='inner')
        grid_data = iso_wind[grid_data_columns].copy()
        
        # Convert to dict format for JSON serialization
        grid_data_dict = grid_data.to_dict('records')
        costs_dict = iso_costs.to_dict('records') if not iso_costs.empty else []
        
        return {
            "success": True,
            "data": {
                "grid_data": grid_data_dict,
                "statistics": grid_stats,
                "costs": costs_dict
            }
        }
        
    except Exception as e:
        print(f"Error getting wind renewable zones for {iso_code}: {e}")
        return {
            "success": False,
            "data": None,
            "error": f"Failed to get wind renewable zones: {str(e)}"
        }

iso_code = 'DEU'
# wind_type = 'onshore'


df_solar = get_solar_renewable_zones(iso_code)
# print(df_solar)
df_wind = get_wind_renewable_zones( iso_code, 'onshore')
# print(df_wind)
df_wind_offshore = get_wind_renewable_zones( iso_code, 'offshore')
print(df_wind_offshore)


# """
# Debug Script for Renewable Zones Functions

# This script contains exact copies of get_solar_renewable_zones and get_wind_renewable_zones
# functions from dashboard_data_analyzer.py for individual testing and debugging.

# Usage:
#     python debug_renewable_zones.py
# """

# import pandas as pd
# import numpy as np
# from typing import Dict, Any
# import logging
# import os
# import sys
# from pathlib import Path

# # Set up logging for debugging
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)

# class RenewableZonesDebugger:
#     """
#     Debug class containing exact copies of renewable zones functions
#     """
    
#     def __init__(self):
#         """Initialize the debugger"""
#         self.logger = logging.getLogger(__name__)
#         print("=== Renewable Zones Debugger Initialized ===")
#         print(f"Current working directory: {os.getcwd()}")
#         print(f"Script location: {Path(__file__).parent}")
    
#     def get_solar_renewable_zones(self, iso_code: str) -> Dict[str, Any]:
#         """
#         Get solar renewable energy zones data for a country.
        
#         This method processes Atlite solar rezoning data to analyze solar energy potential,
#         capacity factors, and economic metrics for renewable energy planning.
        
#         Args:
#             iso_code (str): 3-letter ISO country code (e.g., "IND", "DEU", "USA")
        
#         Returns:
#             Dict[str, Any]: Dictionary with the following structure:
#                 - success (bool): True if processing succeeded, False otherwise
#                 - data (dict): Solar zones data if successful, None otherwise, containing:
#                     - grid_data (list): List of solar zone data for map visualization
#                     - statistics (dict): Summary statistics and metrics
#                     - costs (list): Cost data for the country
#                 - error (str): Error message if processing failed, None otherwise
        
#         Example:
#             result = analyzer.get_solar_renewable_zones("DEU")
#             if result["success"]:
#                 solar_data = result["data"]
#                 print(f"Total Zones: {solar_data['statistics']['total_cells']}")
#             else:
#                 print(f"Error: {result['error']}")
#         """
#         print(f"\n=== DEBUG: Starting get_solar_renewable_zones for {iso_code} ===")
        
#         try:
#             import pandas as pd
#             from pathlib import Path
#             print(f"DEBUG: Imported pandas and pathlib successfully")
            
#             # Add the 1_grids directory to Python path
#             scripts_path = Path(__file__).parent / '1_grids' 
#             print(f"DEBUG: Scripts path: {scripts_path}")
#             print(f"DEBUG: Scripts path exists: {scripts_path.exists()}")
            
#             if str(scripts_path) not in sys.path:
#                 sys.path.insert(0, str(scripts_path))
#                 print(f"DEBUG: Added {scripts_path} to sys.path")
            
#             # Import the energy colors
#             print("DEBUG: Attempting to import load_zones_for_country...")
#             try:
#                 from extract_country_pypsa_network_clustered import load_zones_for_country
#                 print("DEBUG: Successfully imported load_zones_for_country")
#             except ImportError as e:
#                 print(f"DEBUG: Failed to import load_zones_for_country: {e}")
#                 return {
#                     "success": False,
#                     "data": None,
#                     "error": f"Import error: {str(e)}"
#                 }
            
#             # Set up paths for REZoning data using project root
#             project_root = Path(__file__).parent
#             data_path = project_root / 'data' / 'REZoning'
#             solar_file = data_path / 'REZoning_Solar_atlite_cf.csv'
#             costs_file = data_path / 'REZoning_costs_per_kw.csv'
            
#             print(f"DEBUG: Project root: {project_root}")
#             print(f"DEBUG: Data path: {data_path}")
#             print(f"DEBUG: Solar file: {solar_file}")
#             print(f"DEBUG: Costs file: {costs_file}")
            
#             # Check if files exist
#             if not solar_file.exists():
#                 print(f"DEBUG: Solar file does not exist: {solar_file}")
#                 return {
#                     "success": False,
#                     "data": None,
#                     "error": f"Solar rezoning data file not found: {solar_file}"
#                 }
#             else:
#                 print(f"DEBUG: Solar file exists: {solar_file}")
            
#             if not costs_file.exists():
#                 print(f"DEBUG: Costs file does not exist: {costs_file}")
#                 return {
#                     "success": False,
#                     "data": None,
#                     "error": f"Solar costs data file not found: {costs_file}"
#                 }
#             else:
#                 print(f"DEBUG: Costs file exists: {costs_file}")
            
#             # Load data
#             print("DEBUG: Loading solar data...")
#             solar_data = pd.read_csv(solar_file)
#             print(f"DEBUG: Solar data shape: {solar_data.shape}")
#             print(f"DEBUG: Solar data columns: {list(solar_data.columns)}")
            
#             print("DEBUG: Loading costs data...")
#             costs_data = pd.read_csv(costs_file)
#             print(f"DEBUG: Costs data shape: {costs_data.shape}")
#             print(f"DEBUG: Costs data columns: {list(costs_data.columns)}")
            
#             print("DEBUG: Loading zones GeoDataFrame...")
#             zones_gdf = load_zones_for_country(iso_code, 'onshore')[['grid_cell','geometry']]
#             print(f"DEBUG: Zones GDF shape: {zones_gdf.shape}")
#             print(f"DEBUG: Zones GDF columns: {list(zones_gdf.columns)}")
            
#             # Filter data for the specific ISO
#             print(f"DEBUG: Filtering solar data for ISO: {iso_code}")
#             iso_solar = solar_data[solar_data['ISO'] == iso_code].copy()
#             print(f"DEBUG: ISO solar data shape after filtering: {iso_solar.shape}")
            
#             if iso_solar.empty:
#                 available_isos = solar_data['ISO'].unique()
#                 print(f"DEBUG: Available ISOs in solar data: {available_isos}")
#                 return {
#                     "success": False,
#                     "data": None,
#                     "error": f"No solar data found for ISO: {iso_code}. Available ISOs: {available_isos}"
#                 }
            
#             # Get cost data for this ISO
#             print(f"DEBUG: Filtering costs data for ISO: {iso_code}")
#             iso_costs = costs_data[costs_data['iso'] == iso_code]
#             print(f"DEBUG: ISO costs data shape: {iso_costs.shape}")
            
#             # Clean and process the data
#             print("DEBUG: Cleaning and processing data...")
#             print(f"DEBUG: Data before dropna: {len(iso_solar)} rows")
#             iso_solar = iso_solar.dropna(subset=['lat', 'lng', 'Capacity Factor'])
#             print(f"DEBUG: Data after dropna: {len(iso_solar)} rows")
            
#             # Filter by minimum capacity (1MW)
#             min_capacity_mw = 1.0
#             print(f"DEBUG: Filtering by minimum capacity: {min_capacity_mw} MW")
#             print(f"DEBUG: Data before capacity filter: {len(iso_solar)} rows")
#             iso_solar = iso_solar[iso_solar['Installed Capacity Potential (MW)'] >= min_capacity_mw]
#             print(f"DEBUG: Data after capacity filter: {len(iso_solar)} rows")
            
#             # Calculate additional metrics
#             print("DEBUG: Calculating additional metrics...")
#             iso_solar['Total_Generation_GWh'] = (
#                 iso_solar['Installed Capacity Potential (MW)'] * 
#                 iso_solar['Capacity Factor'] * 8760 / 1000
#             )
#             print("DEBUG: Total_Generation_GWh calculated")
            
#             # Create grid statistics
#             print("DEBUG: Creating grid statistics...")
#             grid_stats = {
#                 'iso': iso_code,
#                 'total_cells': len(iso_solar),
#                 'total_capacity_mw': float(iso_solar['Installed Capacity Potential (MW)'].sum()),
#                 'total_generation_gwh': float(iso_solar['Total_Generation_GWh'].sum()),
#                 'avg_capacity_factor': float(iso_solar['Capacity Factor'].mean()),
#                 'avg_lcoe': float(iso_solar['LCOE (USD/MWh)'].mean()),
#                 'total_suitable_area_km2': float(iso_solar['Suitable Area (km²)'].sum()),
#                 'cost_data_available': not iso_costs.empty,
#                 'investment_cost_usd_kw': float(iso_costs['invcost'].iloc[0]) if not iso_costs.empty else None,
#                 'fixed_om_usd_kw': float(iso_costs['fixom'].iloc[0]) if not iso_costs.empty else None,
#                 'data_source': 'Atlite (High-resolution ERA5 weather data)',
#                 'capacity_factor_quality': 'High-resolution, technology-specific modeling'
#             }
#             print(f"DEBUG: Grid statistics: {grid_stats}")
            
#             # Prepare grid data for frontend (limit to essential columns and convert to dict)
#             print("DEBUG: Preparing grid data...")
#             grid_data_columns = [
#                 'id', 'grid_cell', 'lat', 'lng', 'Capacity Factor', 
#                 'Installed Capacity Potential (MW)', 'LCOE (USD/MWh)',
#                 'Suitable Area (km²)', 'Zone Score', 'Total_Generation_GWh', 'geometry'
#             ]
            
#             print("DEBUG: Merging zones_gdf with iso_solar...")
#             print(f"DEBUG: zones_gdf columns: {list(zones_gdf.columns)}")
#             print(f"DEBUG: iso_solar columns: {list(iso_solar.columns)}")
            
#             iso_solar = zones_gdf.merge(iso_solar, on='grid_cell', how='inner')
#             print(f"DEBUG: Data after merge: {iso_solar.shape}")
            
#             # Check which columns are actually available
#             available_columns = [col for col in grid_data_columns if col in iso_solar.columns]
#             missing_columns = [col for col in grid_data_columns if col not in iso_solar.columns]
#             print(f"DEBUG: Available columns: {available_columns}")
#             print(f"DEBUG: Missing columns: {missing_columns}")
            
#             grid_data = iso_solar[available_columns].copy()
#             print(f"DEBUG: Grid data shape: {grid_data.shape}")
            
#             # Convert to dict format for JSON serialization
#             print("DEBUG: Converting to dict format...")
#             grid_data_dict = grid_data.to_dict('records')
#             print(f"DEBUG: Grid data dict length: {len(grid_data_dict)}")
            
#             # Prepare costs data
#             costs_dict = iso_costs.to_dict('records') if not iso_costs.empty else []
#             print(f"DEBUG: Costs dict length: {len(costs_dict)}")
            
#             result = {
#                 "success": True,
#                 "data": {
#                     "grid_data": grid_data_dict,
#                     "statistics": grid_stats,
#                     "costs": costs_dict
#                 }
#             }
#             print("DEBUG: Successfully completed get_solar_renewable_zones")
#             return result
            
#         except Exception as e:
#             self.logger.error(f"Error getting solar renewable zones for {iso_code}: {e}")
#             print(f"DEBUG: Exception occurred: {str(e)}")
#             import traceback
#             print(f"DEBUG: Traceback:\n{traceback.format_exc()}")
#             return {
#                 "success": False,
#                 "data": None,
#                 "error": f"Failed to get solar renewable zones: {str(e)}"
#             }

#     def get_wind_renewable_zones(self, iso_code: str, wind_type: str = 'onshore') -> Dict[str, Any]:
#         """
#         Get wind renewable energy zones data for a country (offshore or onshore).
        
#         This method processes Atlite wind rezoning data to analyze wind energy potential,
#         capacity factors, and economic metrics for renewable energy planning.
        
#         Args:
#             iso_code (str): 3-letter ISO country code (e.g., "IND", "DEU", "USA")
#             wind_type (str): Wind type - 'onshore' or 'offshore' (default: 'onshore')
        
#         Returns:
#             Dict[str, Any]: Dictionary with the following structure:
#                 - success (bool): True if processing succeeded, False otherwise
#                 - data (dict): Wind zones data if successful, None otherwise, containing:
#                     - grid_data (list): List of wind zone data for map visualization
#                     - statistics (dict): Summary statistics and metrics
#                     - costs (list): Cost data for the country
#                 - error (str): Error message if processing failed, None otherwise
        
#         Example:
#             result = analyzer.get_wind_renewable_zones("DEU", "offshore")
#             if result["success"]:
#                 wind_data = result["data"]
#                 print(f"Total Zones: {wind_data['statistics']['total_cells']}")
#             else:
#                 print(f"Error: {result['error']}")
#         """
#         print(f"\n=== DEBUG: Starting get_wind_renewable_zones for {iso_code}, type: {wind_type} ===")
        
#         try:
#             import pandas as pd
#             from pathlib import Path
#             print(f"DEBUG: Imported pandas and pathlib successfully")
            
#             # Add the 1_grids directory to Python path
#             scripts_path = Path(__file__).parent / '1_grids' 
#             print(f"DEBUG: Scripts path: {scripts_path}")
#             print(f"DEBUG: Scripts path exists: {scripts_path.exists()}")
            
#             if str(scripts_path) not in sys.path:
#                 sys.path.insert(0, str(scripts_path))
#                 print(f"DEBUG: Added {scripts_path} to sys.path")
            
#             # Import the energy colors
#             print("DEBUG: Attempting to import load_zones_for_country...")
#             try:
#                 from extract_country_pypsa_network_clustered import load_zones_for_country
#                 print("DEBUG: Successfully imported load_zones_for_country")
#             except ImportError as e:
#                 print(f"DEBUG: Failed to import load_zones_for_country: {e}")
#                 return {
#                     "success": False,
#                     "data": None,
#                     "error": f"Import error: {str(e)}"
#                 }
            
#             # Set up paths for REZoning data using project root
#             project_root = Path(__file__).parent
#             data_path = project_root / 'data' / 'REZoning'
            
#             # Choose the appropriate wind data file
#             if wind_type == 'offshore':
#                 wind_file = data_path / 'REZoning_WindOffshore_atlite_cf.csv'
#                 zones_gdf = load_zones_for_country(iso_code, 'offshore')[['grid_cell','geometry']]
#             else:
#                 wind_file = data_path / 'REZoning_WindOnshore_atlite_cf.csv'
#                 zones_gdf = load_zones_for_country(iso_code, 'onshore')[['grid_cell','geometry']]
            
#             costs_file = data_path / 'REZoning_costs_per_kw.csv'
            
#             print(f"DEBUG: Project root: {project_root}")
#             print(f"DEBUG: Data path: {data_path}")
#             print(f"DEBUG: Wind file: {wind_file}")
#             print(f"DEBUG: Costs file: {costs_file}")
            
#             # Check if files exist
#             if not wind_file.exists():
#                 print(f"DEBUG: Wind file does not exist: {wind_file}")
#                 return {
#                     "success": False,
#                     "data": None,
#                     "error": f"Wind {wind_type} data file not found: {wind_file}"
#                 }
#             else:
#                 print(f"DEBUG: Wind file exists: {wind_file}")
            
#             if not costs_file.exists():
#                 print(f"DEBUG: Costs file does not exist: {costs_file}")
#                 return {
#                     "success": False,
#                     "data": None,
#                     "error": f"Costs data file not found: {costs_file}"
#                 }
#             else:
#                 print(f"DEBUG: Costs file exists: {costs_file}")
            
#             # Load wind data
#             print("DEBUG: Loading wind data...")
#             wind_data = pd.read_csv(wind_file)
#             print(f"DEBUG: Wind data shape: {wind_data.shape}")
#             print(f"DEBUG: Wind data columns: {list(wind_data.columns)}")
            
#             print("DEBUG: Loading costs data...")
#             costs_data = pd.read_csv(costs_file)
#             print(f"DEBUG: Costs data shape: {costs_data.shape}")
            
#             print("DEBUG: Loading zones GeoDataFrame...")
#             zones_gdf = load_zones_for_country(iso_code, 'onshore')[['grid_cell','geometry']]
#             print(f"DEBUG: Zones GDF shape: {zones_gdf.shape}")
            
#             # Filter data for the specific ISO
#             print(f"DEBUG: Filtering wind data for ISO: {iso_code}")
#             iso_wind = wind_data[wind_data['ISO'] == iso_code].copy()
#             print(f"DEBUG: ISO wind data shape after filtering: {iso_wind.shape}")
            
#             if iso_wind.empty:
#                 available_isos = wind_data['ISO'].unique()
#                 print(f"DEBUG: Available ISOs in wind data: {available_isos}")
#                 return {
#                     "success": False,
#                     "data": None,
#                     "error": f"No {wind_type} wind data found for ISO: {iso_code}. Available ISOs: {available_isos}"
#                 }
            
#             # Get cost data for this ISO
#             print(f"DEBUG: Filtering costs data for ISO: {iso_code}")
#             iso_costs = costs_data[costs_data['iso'] == iso_code]
#             print(f"DEBUG: ISO costs data shape: {iso_costs.shape}")
            
#             # Clean and process the data - wind data uses 'lng' instead of 'long'
#             print("DEBUG: Cleaning and processing data...")
#             print(f"DEBUG: Data before dropna: {len(iso_wind)} rows")
#             iso_wind = iso_wind.dropna(subset=['lat', 'lng', 'Capacity Factor'])
#             print(f"DEBUG: Data after dropna: {len(iso_wind)} rows")
            
#             print(f"DEBUG: Data before capacity filter: {len(iso_wind)} rows")
#             iso_wind = iso_wind[iso_wind['Installed Capacity Potential (MW)'] >= 1.0]
#             print(f"DEBUG: Data after capacity filter: {len(iso_wind)} rows")
            
#             # Calculate additional metrics
#             print("DEBUG: Calculating additional metrics...")
#             iso_wind['Total_Generation_GWh'] = (
#                 iso_wind['Installed Capacity Potential (MW)'] * 
#                 iso_wind['Capacity Factor'] * 8760 / 1000
#             )
#             print("DEBUG: Total_Generation_GWh calculated")
            
#             # Create grid statistics
#             print("DEBUG: Creating grid statistics...")
#             grid_stats = {
#                 'iso': iso_code,
#                 'wind_type': wind_type,
#                 'total_cells': len(iso_wind),
#                 'total_capacity_mw': float(iso_wind['Installed Capacity Potential (MW)'].sum()),
#                 'total_generation_gwh': float(iso_wind['Total_Generation_GWh'].sum()),
#                 'avg_capacity_factor': float(iso_wind['Capacity Factor'].mean()),
#                 'avg_lcoe': float(iso_wind['LCOE (USD/MWh)'].mean()),
#                 'total_suitable_area_km2': float(iso_wind['Suitable Area (km²)'].sum()),
#                 'cost_data_available': not iso_costs.empty,
#                 'investment_cost_usd_kw': float(iso_costs['invcost'].iloc[0]) if not iso_costs.empty else None,
#                 'fixed_om_usd_kw': float(iso_costs['fixom'].iloc[0]) if not iso_costs.empty else None,
#                 'data_source': f'Atlite {wind_type.title()} Wind (High-resolution ERA5 weather data)',
#                 'capacity_factor_quality': 'High-resolution, technology-specific modeling'
#             }
#             print(f"DEBUG: Grid statistics: {grid_stats}")
            
#             # Prepare grid data for frontend (limit to essential columns and convert to dict)
#             print("DEBUG: Preparing grid data...")
#             grid_data_columns = [
#                 'id', 'grid_cell', 'lat', 'lng', 'Capacity Factor', 
#                 'Installed Capacity Potential (MW)', 'LCOE (USD/MWh)',
#                 'Suitable Area (km²)', 'Zone Score', 'Total_Generation_GWh', 'geometry'
#             ]
            
#             print("DEBUG: Merging zones_gdf with iso_wind...")
#             print(f"DEBUG: zones_gdf columns: {list(zones_gdf.columns)}")
#             print(f"DEBUG: iso_wind columns: {list(iso_wind.columns)}")
            
#             iso_wind = zones_gdf.merge(iso_wind, on='grid_cell', how='inner')
#             print(f"DEBUG: Data after merge: {iso_wind.shape}")
            
#             # Check which columns are actually available
#             available_columns = [col for col in grid_data_columns if col in iso_wind.columns]
#             missing_columns = [col for col in grid_data_columns if col not in iso_wind.columns]
#             print(f"DEBUG: Available columns: {available_columns}")
#             print(f"DEBUG: Missing columns: {missing_columns}")
            
#             grid_data = iso_wind[available_columns].copy()
#             print(f"DEBUG: Grid data shape: {grid_data.shape}")
            
#             # Convert to dict format for JSON serialization
#             print("DEBUG: Converting to dict format...")
#             grid_data_dict = grid_data.to_dict('records')
#             print(f"DEBUG: Grid data dict length: {len(grid_data_dict)}")
            
#             costs_dict = iso_costs.to_dict('records') if not iso_costs.empty else []
#             print(f"DEBUG: Costs dict length: {len(costs_dict)}")
            
#             result = {
#                 "success": True,
#                 "data": {
#                     "grid_data": grid_data_dict,
#                     "statistics": grid_stats,
#                     "costs": costs_dict
#                 }
#             }
#             print("DEBUG: Successfully completed get_wind_renewable_zones")
#             return result
            
#         except Exception as e:
#             self.logger.error(f"Error getting wind renewable zones for {iso_code}: {e}")
#             print(f"DEBUG: Exception occurred: {str(e)}")
#             import traceback
#             print(f"DEBUG: Traceback:\n{traceback.format_exc()}")
#             return {
#                 "success": False,
#                 "data": None,
#                 "error": f"Failed to get wind renewable zones: {str(e)}"
#             }


# def test_solar_zones(debugger, iso_code="DEU"):
#     """Test the solar zones function"""
#     print(f"\n{'='*60}")
#     print(f"TESTING SOLAR ZONES FOR {iso_code}")
#     print(f"{'='*60}")
    
#     result = debugger.get_solar_renewable_zones(iso_code)
    
#     if result["success"]:
#         print("✅ SUCCESS: Solar zones function completed successfully!")
#         stats = result["data"]["statistics"]
#         print(f"📊 Statistics:")
#         for key, value in stats.items():
#             print(f"   {key}: {value}")
#         print(f"📍 Grid data points: {len(result['data']['grid_data'])}")
#         print(f"💰 Cost data entries: {len(result['data']['costs'])}")
#     else:
#         print("❌ FAILED: Solar zones function failed")
#         print(f"Error: {result['error']}")
    
#     return result


# def test_wind_zones(debugger, iso_code="DEU", wind_type="onshore"):
#     """Test the wind zones function"""
#     print(f"\n{'='*60}")
#     print(f"TESTING WIND ZONES FOR {iso_code} ({wind_type.upper()})")
#     print(f"{'='*60}")
    
#     result = debugger.get_wind_renewable_zones(iso_code, wind_type)
    
#     if result["success"]:
#         print("✅ SUCCESS: Wind zones function completed successfully!")
#         stats = result["data"]["statistics"]
#         print(f"📊 Statistics:")
#         for key, value in stats.items():
#             print(f"   {key}: {value}")
#         print(f"📍 Grid data points: {len(result['data']['grid_data'])}")
#         print(f"💰 Cost data entries: {len(result['data']['costs'])}")
#     else:
#         print("❌ FAILED: Wind zones function failed")
#         print(f"Error: {result['error']}")
    
#     return result


# def main():
#     """Main function to run tests"""
#     print("🚀 Starting Renewable Zones Debugger")
#     print("=" * 80)
    
#     # Initialize debugger
#     debugger = RenewableZonesDebugger()
    
#     # Test cases - you can modify these
#     test_cases = [
#         {"iso": "DEU", "test_solar": True, "test_wind": True, "wind_type": "onshore"},
#         {"iso": "IND", "test_solar": True, "test_wind": True, "wind_type": "onshore"},
#         {"iso": "USA", "test_solar": True, "test_wind": False, "wind_type": "onshore"},
#     ]
    
#     results = {}
    
#     for case in test_cases:
#         iso = case["iso"]
#         results[iso] = {}
        
#         if case["test_solar"]:
#             results[iso]["solar"] = test_solar_zones(debugger, iso)
        
#         if case["test_wind"]:
#             results[iso]["wind"] = test_wind_zones(debugger, iso, case["wind_type"])
    
#     # Summary
#     print(f"\n{'='*80}")
#     print("🎯 SUMMARY")
#     print(f"{'='*80}")
    
#     for iso, tests in results.items():
#         print(f"\n{iso}:")
#         if "solar" in tests:
#             status = "✅ PASS" if tests["solar"]["success"] else "❌ FAIL"
#             print(f"  Solar: {status}")
#         if "wind" in tests:
#             status = "✅ PASS" if tests["wind"]["success"] else "❌ FAIL"
#             print(f"  Wind:  {status}")


# if __name__ == "__main__":
#     main()
