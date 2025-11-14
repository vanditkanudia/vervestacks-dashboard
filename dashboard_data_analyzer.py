"""
Dashboard Data Analyzer Module

This module provides data analysis for dashboard visualization.
Currently handles energy metrics from Ember dataset and existing stock from GEM data,
designed to expand for comprehensive dashboard data needs.

Classes:
    DashboardDataAnalyzer: Main analyzer class for dashboard data processing

Example:
    analyzer = DashboardDataAnalyzer()
    result = analyzer.get_energy_metrics("IND")
    if result["success"]:
        chart_data = result["data"]
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
import os
import sys
from pathlib import Path

class DashboardDataAnalyzer:
    """
    Analyzer for dashboard data processing.
    Currently provides energy metrics analysis from Ember dataset,
    designed to expand for comprehensive dashboard data needs.
    """
    
    def __init__(self, ember_data_path: str = "data/ember/yearly_full_release_long_format.csv"):
        """
        Initialize the DashboardDataAnalyzer.
        
        Args:
            ember_data_path (str): Path to the Ember yearly data CSV file.
                                  Default: "data/ember/yearly_full_release_long_format.csv"
        
        Example:
            analyzer = DashboardDataAnalyzer()
            analyzer = DashboardDataAnalyzer("custom/path/to/ember_data.csv")
        """
        self.ember_data_path = ember_data_path
        self._ember_data = None
        
        # GEM setup for existing stock analysis
        self._gem_processor = None
        self._gem_data = None
        
        self.logger = logging.getLogger(__name__)
    
    def load_ember_data(self) -> Dict[str, Any]:
        """
        Load and cache Ember data from CSV file.
        
        This method loads the Ember dataset once and caches it in memory
        for subsequent calls to avoid repeated file I/O operations.
        
        Returns:
            Dict[str, Any]: Dictionary with the following structure:
                - success (bool): True if data loaded successfully, False otherwise
                - data (pd.DataFrame): Loaded Ember dataset if successful, None otherwise
                - error (str): Error message if loading failed, None otherwise
        
        Example:
            result = analyzer.load_ember_data()
            if result["success"]:
                df_ember = result["data"]
            else:
                print(f"Error: {result['error']}")
        """
        try:
            if self._ember_data is None:
                if not os.path.exists(self.ember_data_path):
                    return {
                        "success": False,
                        "data": None,
                        "error": f"Ember data file not found at {self.ember_data_path}"
                    }
                
                self._ember_data = pd.read_csv(self.ember_data_path)
                self.logger.info(f"Ember data loaded successfully: {len(self._ember_data)} records")
            
            return {
                "success": True,
                "data": self._ember_data,
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"Error loading Ember data: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to load Ember data: {str(e)}"
            }
    
    def get_energy_metrics(self, iso_code: str) -> Dict[str, Any]:
        """
        Get energy metrics data for charts (utilization factor and CO2 intensity).
        
        This method processes Ember data to calculate utilization factors and CO2 intensity
        across three geographic levels: ISO (country), Region (Ember region), and World.
        
        Args:
            iso_code (str): 3-letter ISO country code (e.g., "IND", "DEU", "USA")
        
        Returns:
            Dict[str, Any]: Dictionary with the following structure:
                - success (bool): True if processing succeeded, False otherwise
                - data (dict): Chart data if successful, None otherwise, containing:
                    - iso_code (str): The input ISO code
                    - iso_region (str): The Ember region for this ISO
                    - utilization_data (list): List of dicts with Year, Level, Utilization_Factor
                    - co2_intensity_data (list): List of dicts with Year, Level, CO2_Intensity
                    - years_available (list): List of available years [2000, 2001, ..., 2023]
                    - levels (list): List of geographic levels ["ISO", "Region", "World"]
                - error (str): Error message if processing failed, None otherwise
        
        Example:
            result = analyzer.get_energy_metrics("IND")
            if result["success"]:
                chart_data = result["data"]
                print(f"ISO Region: {chart_data['iso_region']}")
                print(f"Years: {chart_data['years_available']}")
            else:
                print(f"Error: {result['error']}")
        
        Raises:
            Exception: If data processing fails internally
        """
        try:
            # Load data
            load_result = self.load_ember_data()
            if not load_result["success"]:
                return load_result
            
            df_ember = load_result["data"]
            
            # Get ISO region
            iso_data = df_ember[df_ember['Country code'] == iso_code]
            if len(iso_data) == 0:
                return {
                    "success": False,
                    "data": None,
                    "error": f"No data found for ISO code: {iso_code}"
                }
            
            iso_region = iso_data['Ember region'].iloc[0]
            
            # Process metrics for all levels
            iso_metrics = self._get_metrics_by_year(df_ember, df_ember['Country code'] == iso_code, f"ISO ({iso_code})")
            region_metrics = self._get_metrics_by_year(df_ember, df_ember['Ember region'] == iso_region, f"Region ({iso_region})")
            world_metrics = self._get_metrics_by_year(df_ember, 
                (df_ember['Country code'].notna()) & (df_ember['Country code'] != '') & (df_ember['Area type'] == 'Country'), 
                "World")
            
            # Combine all metrics
            all_metrics = pd.concat([iso_metrics, region_metrics, world_metrics], ignore_index=True)
            
            # Prepare chart data
            utilization_data = all_metrics[['Year', 'Level', 'Utilization_Factor']].dropna(subset=['Utilization_Factor']).copy()
            co2_intensity_data = all_metrics[['Year', 'Level', 'CO2_Intensity']].dropna(subset=['CO2_Intensity']).copy()
            
            # Sort for proper plotting
            utilization_data = utilization_data.sort_values(['Level', 'Year'])
            co2_intensity_data = co2_intensity_data.sort_values(['Level', 'Year'])
            
            # Convert to dict format for API response
            chart_data = {
                "iso_code": iso_code,
                "iso_region": iso_region,
                "utilization_data": utilization_data.to_dict('records'),
                "co2_intensity_data": co2_intensity_data.to_dict('records'),
                "years_available": sorted(all_metrics['Year'].unique().tolist()),
                "levels": ["ISO", "Region", "World"]
            }
            
            return {
                "success": True,
                "data": chart_data,
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"Error processing energy metrics for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to process energy metrics: {str(e)}"
            }

    def _get_metrics_by_year(self, df: pd.DataFrame, filter_condition: pd.Series, level_name: str) -> pd.DataFrame:
        """
        Extract generation, emissions, and capacity data by year for given filter condition.
        
        Args:
            df: Ember DataFrame
            filter_condition: Boolean filter condition
            level_name: Name for the level (ISO, Region, World)
            
        Returns:
            DataFrame with calculated metrics
        """
        # Filter data based on condition
        df_filtered = df[filter_condition].copy()
        
        # Define fossil fuel types
        fossil_fuels = ['Coal', 'Gas', 'Other Fossil']
        
        # Get fossil generation data by year (only TWh units)
        fossil_generation_data = df_filtered[
            (df_filtered['Subcategory'] == "Fuel") & 
            (df_filtered['Variable'].isin(fossil_fuels)) &
            (df_filtered['Unit'] == "TWh")
        ].groupby('Year')['Value'].sum().reset_index()
        fossil_generation_data.columns = ['Year', 'Fossil_Generation']
        
        # Get total generation data by year (for CO2 intensity)
        total_generation_data = df_filtered[
            df_filtered['Variable'] == "Total Generation"
        ].groupby('Year')['Value'].sum().reset_index()
        total_generation_data.columns = ['Year', 'Total_Generation']
        
        # Get emissions data by year
        emissions_data = df_filtered[
            df_filtered['Variable'] == "Total emissions"
        ].groupby('Year')['Value'].sum().reset_index()
        emissions_data.columns = ['Year', 'Emissions']
        
        # Get fossil capacity data by year
        fossil_capacity_data = df_filtered[
            (df_filtered['Subcategory'] == "Fuel") & 
            (df_filtered['Variable'].isin(fossil_fuels)) &
            (df_filtered['Unit'] == "GW")
        ].groupby('Year')['Value'].sum().reset_index()
        fossil_capacity_data.columns = ['Year', 'Fossil_Capacity']
        
        # Merge all data
        metrics_df = fossil_generation_data.merge(total_generation_data, on='Year', how='outer')
        metrics_df = metrics_df.merge(emissions_data, on='Year', how='outer')
        metrics_df = metrics_df.merge(fossil_capacity_data, on='Year', how='outer')
        
        # Calculate metrics
        metrics_df['Utilization_Factor'] = metrics_df['Fossil_Generation'] / metrics_df['Fossil_Capacity'] / 8.76
        metrics_df['CO2_Intensity'] = metrics_df['Emissions'] / metrics_df['Total_Generation']
        
        # Add level identifier
        metrics_df['Level'] = level_name
        
        return metrics_df


    def _initialize_gem_processor(self):
        """
        Initialize VerveStacksProcessor for GEM data access.
        
        This method initializes the VerveStacksProcessor once and caches it
        for subsequent calls to avoid repeated initialization.
        """
        try:
            if self._gem_processor is None:
                from verve_stacks_processor import VerveStacksProcessor
                self._gem_processor = VerveStacksProcessor(data_dir="data", cache_dir="cache")
                self.logger.info("GEM processor initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing GEM processor: {e}")
            raise

    def _load_zones_from_geojson(self, iso_code: str, zone_type: str = 'onshore') -> pd.DataFrame:
        """
        Load renewable energy zones from GeoJSON files.
        
        This method loads geometry data directly from GeoJSON files, filtering by ISO code
        and returning a DataFrame with grid_cell and geometry columns.
        
        Args:
            iso_code (str): 3-letter ISO country code (e.g., "IND", "DEU", "USA")
            zone_type (str): Zone type - 'onshore' or 'offshore' (default: 'onshore')
        
        Returns:
            pd.DataFrame: DataFrame with columns ['grid_cell', 'geometry']
        """
        try:
            import json
            from shapely.geometry import shape
            from pathlib import Path
            
            # Set up paths for GeoJSON files
            project_root = Path(__file__).parent
            data_path = project_root / 'data' / 'REZoning'
            
            # Choose the appropriate GeoJSON file
            if zone_type == 'offshore':
                geojson_file = data_path / 'consolidated_offshore_zones.geojson'
            else:
                geojson_file = data_path / 'consolidated_onshore_zones.geojson'
            
            if not geojson_file.exists():
                self.logger.error(f"GeoJSON file not found: {geojson_file}")
                return pd.DataFrame()
            
            # Load and parse GeoJSON
            with open(geojson_file, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            # Extract features and filter by ISO
            zones_data = []
            for feature in geojson_data.get('features', []):
                properties = feature.get('properties', {})
                geometry = feature.get('geometry')
                
                # Get ISO from properties or infer from grid_cell
                feature_iso = properties.get('ISO')
                if not feature_iso:
                    # Try to infer ISO from grid_cell prefix (e.g., "DEU_12345")
                    grid_cell = properties.get('grid_cell', '')
                    if '_' in grid_cell:
                        feature_iso = grid_cell.split('_')[0]
                
                # Filter by ISO code
                if feature_iso == iso_code:
                    try:
                        # Validate and convert geometry
                        geom_shape = shape(geometry)
                        if geom_shape.is_valid and not geom_shape.is_empty:
                            zones_data.append({
                                'grid_cell': properties.get('grid_cell', ''),
                                'geometry': geom_shape
                            })
                    except Exception as e:
                        self.logger.warning(f"Invalid geometry for grid_cell {properties.get('grid_cell', '')}: {e}")
                        continue
            
            if not zones_data:
                self.logger.warning(f"No valid zones found for ISO {iso_code} in {zone_type} GeoJSON")
                return pd.DataFrame()
            
            # Create DataFrame
            zones_df = pd.DataFrame(zones_data)
            self.logger.info(f"Loaded {len(zones_df)} {zone_type} zones for {iso_code}")
            
            return zones_df
            
        except Exception as e:
            self.logger.error(f"Error loading zones from GeoJSON for {iso_code}: {e}")
            return pd.DataFrame()

    def get_solar_renewable_zones(self, iso_code: str) -> Dict[str, Any]:
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
            
            # Load zones from GeoJSON (replacing load_zones_for_country)
            zones_df = self._load_zones_from_geojson(iso_code, 'onshore')
            
            # Filter data for the specific ISO
            iso_solar = solar_data[solar_data['ISO'] == iso_code].copy()
            
            if zones_df.empty:
                return {
                    "success": False,
                    "data": None,
                    "error": f"No onshore zones found for ISO: {iso_code}"
                }
            
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
                'total_cells': len(iso_solar),
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
            iso_solar = zones_df.merge(iso_solar, on='grid_cell', how='inner')
            grid_data = iso_solar[grid_data_columns].copy()
            
            # Convert geometry to GeoJSON format for JSON serialization
            import json
            from shapely.geometry import mapping
            grid_data['geometry'] = grid_data['geometry'].apply(lambda geom: mapping(geom) if geom is not None else None)
            
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
            self.logger.error(f"Error getting solar renewable zones for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get solar renewable zones: {str(e)}"
            }

    def get_wind_renewable_zones(self, iso_code: str, wind_type: str = 'onshore') -> Dict[str, Any]:
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
            
            # Set up paths for REZoning data using project root
            project_root = Path(__file__).parent
            data_path = project_root / 'data' / 'REZoning'
            
            # Choose the appropriate wind data file
            if wind_type == 'offshore':
                wind_file = data_path / 'REZoning_WindOffshore_atlite_cf.csv'
            else:
                wind_file = data_path / 'REZoning_WindOnshore_atlite_cf.csv'
            
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
            
            # Load zones from GeoJSON (replacing load_zones_for_country)
            zones_df = self._load_zones_from_geojson(iso_code, wind_type)
            
            # Filter data for the specific ISO
            iso_wind = wind_data[wind_data['ISO'] == iso_code].copy()
            
            if wind_type == 'offshore' and not iso_wind['grid_cell'].iloc[0].startswith('wof-'):
                iso_wind['grid_cell'] = 'wof-' + iso_wind['grid_cell']
            
            if zones_df.empty:
                return {
                    "success": False,
                    "data": None,
                    "error": f"No {wind_type} zones found for ISO: {iso_code}"
                }
            
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
            iso_wind = zones_df.merge(iso_wind, on='grid_cell', how='inner')
            grid_data = iso_wind[grid_data_columns].copy()
            
            # Convert geometry to GeoJSON format for JSON serialization
            import json
            from shapely.geometry import mapping
            grid_data['geometry'] = grid_data['geometry'].apply(lambda geom: mapping(geom) if geom is not None else None)
            
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
            self.logger.error(f"Error getting wind renewable zones for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get wind renewable zones: {str(e)}"
            }

    def get_existing_stock_metrics(self, iso_code: str) -> Dict[str, Any]:
        """
        Get existing stock metrics from GEM data for dashboard charts.
        
        This method processes GEM data to analyze existing power plant infrastructure
        and capacity across different technologies and statuses.
        
        Args:
            iso_code (str): 3-letter ISO country code (e.g., "IND", "DEU", "USA")
        
        Returns:
            Dict[str, Any]: Dictionary with the following structure:
                - success (bool): True if processing succeeded, False otherwise
                - data (dict): Chart data if successful, None otherwise, containing:
                    - metadata (dict): Summary statistics and counts
                    - plants (list): List of plant data for visualization
                    - capacity_by_technology (dict): Capacity breakdown by technology
                    - status_distribution (dict): Distribution by plant status
                - error (str): Error message if processing failed, None otherwise
        
        Example:
            result = analyzer.get_existing_stock_metrics("IND")
            if result["success"]:
                stock_data = result["data"]
                print(f"Total Capacity: {stock_data['metadata']['total_operating_capacity_gw']} GW")
            else:
                print(f"Error: {result['error']}")
        """
        try:
            
            # Set up path for generation data using project root
            project_root = Path(__file__).parent
            gem_iso_file = project_root / 'portal' / 'processed_gem_plants_data.csv'
            
            if gem_iso_file.exists():
                df_gem_iso = pd.read_csv(gem_iso_file)
            else:
                return {
                    "success": False,
                    "data": None,
                    "error": f"GEM ISO data file not found: {gem_iso_file}"
                }
            # Get GEM data for the specific ISO
            df_gem_iso = df_gem_iso[df_gem_iso['iso_code'] == iso_code].copy()
            
            # GEM data loaded successfully
            
            if len(df_gem_iso) == 0:
                # Check if there are any records with similar ISO codes
                all_iso_codes = df_gem_iso['iso_code'].unique()
                self.logger.info(f"Available ISO codes in GEM data: {sorted(all_iso_codes)}")
                
                return {
                    "success": False,
                    "data": None,
                    "error": f"No GEM data found for ISO code: {iso_code}. Available codes: {sorted(all_iso_codes)[:10]}"
                }
            
            # Check for required columns
            required_columns = ['Status', 'Capacity (MW)', 'Latitude', 'Longitude', 'Fuel']
            missing_columns = [col for col in required_columns if col not in df_gem_iso.columns]
            if missing_columns:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Missing required columns in GEM data: {missing_columns}"
                }
            
           
            # Status filtering completed
            if len(df_gem_iso) == 0:
                self.logger.warning(f"No valid status records found for {iso_code}")
                # Return empty data structure instead of error
                return {
                    "success": True,
                    "data": {
                        "iso_code": iso_code,
                        "metadata": {
                            "total_operating_capacity_gw": 0.0,
                            "operating_plants": 0,
                            "mapped_plants": 0,
                            "total_plants": 0,
                            "coverage_percentage": 0.0
                        },
                        "plants": [],
                        "capacity_by_technology": {},
                        "status_distribution": {},
                        "technologies_available": [],
                        "statuses_available": []
                    },
                    "error": None
                }
            
            # Helper functions converted from notebook
            def is_valid_year(val):
                try:
                    year = int(val)
                    return 1900 <= year <= 2030
                except:
                    return False
            
            def get_start_year(row):
                for col in ['Start year', 'Year', 'start_year']:
                    if col in row and is_valid_year(row[col]):
                        return int(row[col])
                return None
            
            # Process the data
            df_gem_iso['Start year'] = df_gem_iso.apply(get_start_year, axis=1)
            
            # Calculate metadata
            statuses_to_keep = ['operating', 'construction']
            operating_plants = df_gem_iso[df_gem_iso['Status'].str.lower().isin(statuses_to_keep)]
            total_operating_capacity_gw = operating_plants['Capacity (MW)'].sum() / 1000 if len(operating_plants) > 0 else 0
            operating_count = len(operating_plants)
            mapped_plants = len(df_gem_iso[df_gem_iso['Latitude'].notna() & df_gem_iso['Longitude'].notna()])
            
           
            # Debug: Check specific plants like EcoElectrica
            ecoelectrica = df_gem_iso[df_gem_iso['Plant / Project name'].str.contains('EcoElectrica', case=False, na=False)]
            if len(ecoelectrica) > 0:
                plant = ecoelectrica.iloc[0]
                # Debug info available if needed
            
            # NOW create plant data AFTER model_fuel processing (matching notebook order)
            plants_data = []
            operating_plants_for_map = df_gem_iso[df_gem_iso['Status'].str.lower().isin(statuses_to_keep)].copy()
            
            for idx, (_, plant) in enumerate(operating_plants_for_map.iterrows()):
                if pd.notna(plant['Latitude']) and pd.notna(plant['Longitude']):
                    # Calculate age (matching notebook)
                    current_year = 2025
                    age = current_year - plant.get('Start year', 2015) if pd.notna(plant.get('Start year')) else None
                    
                    plants_data.append({
                        'id': f"{iso_code}_{idx}",  # Unique ID: ISO_code + index
                        'name': str(plant.get('Plant / Project name', 'Unknown')),
                        'technology': str(plant.get('model_fuel', 'Unknown')),
                        'capacity_mw': float(plant.get('Capacity (MW)', 0)) if pd.notna(plant.get('Capacity (MW)', 0)) else 0.0,
                        'status': str(plant.get('Status', 'Unknown')),
                        'latitude': float(plant['Latitude']) if pd.notna(plant['Latitude']) else 0.0,
                        'longitude': float(plant['Longitude']) if pd.notna(plant['Longitude']) else 0.0,
                        'start_year': int(plant.get('Start year')) if pd.notna(plant.get('Start year')) else None,
                        'age': int(age) if age is not None else None,
                        'city': str(plant.get('City', '')),
                        'state': str(plant.get('Subnational unit (state, province)', '')),
                        'country': str(plant.get('Country/area', 'Unknown'))
                    })
            
            # Calculate capacity by technology
            capacity_by_technology = df_gem_iso.groupby('model_fuel')['Capacity (MW)'].sum().to_dict()
            capacity_by_technology = {tech: float(cap) / 1000 for tech, cap in capacity_by_technology.items() if pd.notna(cap)}
            
            # Use specific fuel types: coal, gas, oil, nuclear (operating plants only)

            target_fuels = ['coal', 'gas', 'oil', 'nuclear', 'hydro']
            operating_capacity = df_gem_iso[df_gem_iso['Status'].str.lower().isin(statuses_to_keep)].groupby('model_fuel')['Capacity (MW)'].sum()
            
            # Filter to only include fuels that exist in the data and are in our target list
            dominant_fuels = [fuel for fuel in target_fuels if fuel in operating_capacity.index and operating_capacity[fuel] > 0]
            
            # Calculate status distribution
            status_distribution = df_gem_iso.groupby('Status').size().to_dict()
            status_distribution = {str(status): int(count) for status, count in status_distribution.items()}
            
            # Create fuel-specific histogram data for 4 specific fuels (coal, gas, oil, nuclear, hydro)
            def create_fuel_specific_histograms(df_gem_iso, dominant_fuels):
                """Create histogram data for age and size distributions (matching notebook logic exactly)."""
                
                # Filter for operating plants with valid data (matching notebook)
                operating_plants = df_gem_iso[
                    (df_gem_iso['Status'].str.lower().isin(statuses_to_keep)) &
                    (df_gem_iso['Start year'].notna()) &
                    (df_gem_iso['Capacity (MW)'].notna())
                ].copy()
                
                if len(operating_plants) == 0:
                    return {
                        'dominant_fuels': [],
                        'fuel_histograms': {}
                    }
                
                # Calculate plant age (matching notebook exactly)
                current_year = 2025  # Match notebook
                operating_plants['Age'] = current_year - operating_plants['Start year'].fillna(2015)
                operating_plants['Age'] = operating_plants['Age'].clip(0, 100)  # Reasonable age bounds
                
                # Create histograms for each target fuel (matching notebook bins exactly)
                fuel_histograms = {}
                
                for fuel_type in dominant_fuels:
                    fuel_data = operating_plants[operating_plants['model_fuel'] == fuel_type].copy()
                    
                    if len(fuel_data) == 0:
                        # Create empty histogram for missing fuels
                        fuel_histograms[fuel_type] = {
                            'age_histogram': {'0-5': 0.0, '5-10': 0.0, '10-20': 0.0, '20-30': 0.0, '30-50': 0.0, '50+': 0.0},
                            'size_histogram': {'<10': 0.0, '10-50': 0.0, '50-100': 0.0, '100-500': 0.0, '500-1000': 0.0, '1000+': 0.0},
                            'total_capacity_gw': 0.0,
                            'unit_count': 0
                        }
                        continue
                    
                    # Age histogram (using notebook bins exactly)
                    age_bins_fuel = [0, 5, 10, 20, 30, 50, 100]
                    age_labels_fuel = ['0-5', '5-10', '10-20', '20-30', '30-50', '50+']
                    fuel_data['Age_Bin'] = pd.cut(fuel_data['Age'], bins=age_bins_fuel, labels=age_labels_fuel, include_lowest=True)
                    age_dist = fuel_data.groupby('Age_Bin', observed=True)['Capacity (MW)'].sum()
                    
                    # Ensure age histogram is in correct order and convert to GW
                    age_histogram_ordered = {}
                    for label in age_labels_fuel:
                        age_histogram_ordered[label] = float(age_dist.get(label, 0) / 1000)  # Convert MW to GW
                    
                    # Size histogram (using notebook bins exactly)
                    size_bins_fuel = [0, 10, 50, 100, 500, 1000, 5000]
                    size_labels_fuel = ['<10', '10-50', '50-100', '100-500', '500-1000', '1000+']
                    fuel_data['Size_Bin'] = pd.cut(fuel_data['Capacity (MW)'], bins=size_bins_fuel, labels=size_labels_fuel, include_lowest=True)
                    size_dist = fuel_data.groupby('Size_Bin', observed=True)['Capacity (MW)'].sum()
                    
                    # Ensure size histogram is in correct order and convert to GW
                    size_histogram_ordered = {}
                    for label in size_labels_fuel:
                        size_histogram_ordered[label] = float(size_dist.get(label, 0) / 1000)  # Convert MW to GW
                    
                    fuel_histograms[fuel_type] = {
                        'age_histogram': {str(k): float(v) for k, v in age_histogram_ordered.items()},
                        'size_histogram': {str(k): float(v) for k, v in size_histogram_ordered.items()},
                        'total_capacity_gw': float(fuel_data['Capacity (MW)'].sum() / 1000),
                        'unit_count': len(fuel_data)
                    }
                
                return {
                    'dominant_fuels': dominant_fuels,
                    'fuel_histograms': fuel_histograms
                }
            
            # Add fuel-specific histogram data to dashboard data
            histogram_data = create_fuel_specific_histograms(df_gem_iso, dominant_fuels)
            
            # Prepare dashboard data structure
            dashboard_data = {
                "iso_code": iso_code,
                "metadata": {
                    "total_operating_capacity_gw": float(total_operating_capacity_gw),
                    "operating_plants": int(operating_count),
                    "mapped_plants": int(mapped_plants),
                    "total_plants": len(df_gem_iso),
                    "coverage_percentage": float((mapped_plants / len(df_gem_iso) * 100) if len(df_gem_iso) > 0 else 0)
                },
                "plants": plants_data,
                "capacity_by_technology": capacity_by_technology,
                "status_distribution": status_distribution,
                "technologies_available": list(capacity_by_technology.keys()),
                "statuses_available": list(status_distribution.keys()),
                "dominant_fuels": histogram_data.get('dominant_fuels', []),
                "fuel_histograms": histogram_data.get('fuel_histograms', {})
            }
            
            return {
                "success": True,
                "data": dashboard_data,
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"Error processing existing stock data for {iso_code}: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to process existing stock data: {str(e)}"
            }

    def get_transmission_data(self, iso_code: str, target_clusters: int = None) -> Dict[str, Any]:
        """
        Get transmission line data from create_regions_simple.py for dashboard visualization.
        
        This method processes population-based demand regions and transmission network data
        using the VerveStacks regional clustering algorithm.
        
        Args:
            iso_code (str): 3-letter ISO country code (e.g., "IND", "DEU", "USA")
            target_clusters (int): Target number of regions (optional, auto-suggested if not provided)
        
        Returns:
            Dict[str, Any]: Dictionary with the following structure:
                - success (bool): True if processing succeeded, False otherwise
                - data (dict): Transmission data if successful, None otherwise, containing:
                    - demand_points (list): List of demand points with coordinates and population data
                    - cluster_centers (list): List of region centers with coordinates and metadata
                    - ntc_connections (list): List of NTC connections between regions
                    - summary (dict): Summary statistics and metadata
                - error (str): Error message if processing failed, None otherwise
        
        Example:
            result = analyzer.get_transmission_data("IND", target_clusters=12)
            if result["success"]:
                transmission_data = result["data"]
                print(f"Total Regions: {transmission_data['summary']['total_regions']}")
            else:
                print(f"Error: {result['error']}")
        """
        try:
            import sys
            import os
            from pathlib import Path
            
            # Add the 0_multi_region directory to Python path
            multi_region_path = Path(__file__).parent / '0_multi_region'
            if str(multi_region_path) not in sys.path:
                sys.path.insert(0, str(multi_region_path))
            
            # Change to the correct working directory for the script
            original_cwd = os.getcwd()
            os.chdir(multi_region_path)
            
            # Import the create_regions_simple module
            from create_regions_simple import analyze_country_population_demand
            
            # Default cluster suggestions for known countries
            default_clusters = {
                'CHE': 4, 'ITA': 7, 'DEU': 10, 'USA': 15, 'AUS': 8, 'CHN': 20,
                'IND': 12, 'JPN': 10, 'ZAF': 6, 'NZL': 4, 'BRA': 12, 'FRA': 8,
                'GBR': 8, 'ESP': 6, 'CAN': 12, 'MEX': 8, 'ARG': 6, 'RUS': 15,
                'TUR': 6, 'IRN': 8, 'SAU': 4, 'EGY': 6, 'NGA': 8, 'KEN': 4,
                'ETH': 6, 'GHA': 4, 'THA': 6, 'VNM': 6, 'IDN': 10, 'MYS': 4,
                'PHL': 8, 'KOR': 6, 'TWN': 4, 'SGP': 1, 'HKG': 1, 'ARE': 2
            }
            
            # Use provided clusters or default suggestion
            clusters_to_use = target_clusters or default_clusters.get(iso_code.upper(), 6)
            
            # Run the analysis
            mapper = analyze_country_population_demand(
                country_code=iso_code.upper(), 
                target_clusters=clusters_to_use, 
                eps_km=100
            )
            
            # Get results data
            results = mapper.get_results_data(return_format='dataframe')
            
            # Convert DataFrames to dictionaries for JSON serialization
            transmission_data = {
                "iso_code": iso_code.upper(),
                "demand_points": results['demand_points'].to_dict('records') if results['demand_points'] is not None else [],
                "cluster_centers": results['cluster_centers'].to_dict('records') if results['cluster_centers'] is not None else [],
                "ntc_connections": results['ntc_connections'].to_dict('records') if results['ntc_connections'] is not None else [],
                "summary": results['summary']
            }
            
            return {
                "success": True,
                "data": transmission_data,
                "error": None
            }
            
        except ImportError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to import create_regions_simple module: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Error getting transmission data for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get transmission data: {str(e)}"
            }
        finally:
            # Restore original working directory
            if 'original_cwd' in locals():
                os.chdir(original_cwd)

    def get_fuel_colors(self) -> Dict[str, Any]:
        """
        Get fuel colors from Python energy_colors.py file for dashboard visualization.
        
        This method retrieves the centralized fuel color palette from the energy_colors.py
        file to ensure consistent colors across all dashboard charts and visualizations.
        
        Returns:
            Dict[str, Any]: Dictionary with the following structure:
                - success (bool): True if processing succeeded, False otherwise
                - data (dict): Direct dictionary mapping fuel types to hex color codes
                - error (str): Error message if processing failed, None otherwise
        
        Example:
            result = analyzer.get_fuel_colors()
            if result["success"]:
                colors = result["data"]
                print(f"Coal color: {colors['coal']}")
            else:
                print(f"Error: {result['error']}")
        """
        try:
            # Import energy colors from the 2_ts_design/scripts directory
            import sys
            import os
            from pathlib import Path
            
            # Add the 2_ts_design/scripts directory to Python path
            scripts_path = Path(__file__).parent / '2_ts_design' / 'scripts'
            if str(scripts_path) not in sys.path:
                sys.path.insert(0, str(scripts_path))
            
            # Import the energy colors
            from energy_colors import ENERGY_COLORS, ENERGY_COLORS_ALT
            
            # Combine both color dictionaries
            all_colors = {**ENERGY_COLORS, **ENERGY_COLORS_ALT}
            
            return {
                "success": True,
                "data": all_colors,
                "error": None
            }
            
        except ImportError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to import energy_colors module: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get fuel colors: {str(e)}"
            }

    def get_transmission_network_data(self, iso_code: str) -> Dict[str, Any]:
        """
        Get transmission network data from load_network_components for dashboard visualization.
        
        This method loads real transmission infrastructure data including buses (substations)
        and lines (transmission corridors) from OSM datasets.
        
        Args:
            iso_code (str): 3-letter ISO country code (e.g., "DEU", "FRA", "CHE")
        
        Returns:
            Dict[str, Any]: Dictionary with the following structure:
                - success (bool): True if processing succeeded, False otherwise
                - data (dict): Transmission network data if successful, None otherwise, containing:
                    - buses (list): List of transmission buses/substations for map visualization
                    - lines (list): List of transmission lines for map visualization
                    - statistics (dict): Summary statistics and metrics
                - error (str): Error message if processing failed, None otherwise
        
        Example:
            result = analyzer.get_transmission_network_data("DEU")
            if result["success"]:
                network_data = result["data"]
                print(f"Total Buses: {network_data['statistics']['total_buses']}")
                print(f"Total Lines: {network_data['statistics']['total_lines']}")
            else:
                print(f"Error: {result['error']}")
        """
        try:
            import sys
            import os
            from pathlib import Path
            
            # Add the 1_grids directory to Python path
            grids_path = Path(__file__).parent / '1_grids'
            if str(grids_path) not in sys.path:
                sys.path.insert(0, str(grids_path))
            
            # Import the load_network_components function
            from extract_country_pypsa_network_clustered import load_network_components,get_iso2_from_iso3 
            
            # Convert ISO3 to ISO2 for the function
            iso2_code = get_iso2_from_iso3(iso_code.upper())
            
            # Temporarily change working directory to 1_grids for the function to work
            original_cwd = os.getcwd()
            try:
                os.chdir(grids_path)
                # Load network components
                components = load_network_components(iso2_code, 'kan')
            finally:
                os.chdir(original_cwd)
            
            buses_df = components.get('buses', pd.DataFrame())
            lines_df = components.get('lines', pd.DataFrame())
            
            
            if buses_df.empty:
                return {
                    "success": False,
                    "data": None,
                    "error": f"No transmission buses found for {iso_code}"
                }
            
            # Process buses data for visualization
            buses_data = []
            if not buses_df.empty:
                for _, bus in buses_df.iterrows():
                    bus_data = {
                        "id": bus.get('bus_id', ''),
                        "name": bus.get('bus_id', ''),
                        "lat": bus.get('y', 0),
                        "lng": bus.get('x', 0),
                        "voltage": bus.get('voltage', 0),
                        "type": "transmission_bus"
                    }
                    buses_data.append(bus_data)
            
            # Process lines data for visualization
            lines_data = []
            if not lines_df.empty:
                # Get bus coordinates for line endpoints
                bus_coords = buses_df.set_index('bus_id')[['x', 'y']].to_dict('index')
                
                for _, line in lines_df.iterrows():
                    bus0_id = line.get('bus0', '')
                    bus1_id = line.get('bus1', '')
                    
                    if bus0_id in bus_coords and bus1_id in bus_coords:
                        line_data = {
                            "id": f"{bus0_id}-{bus1_id}",
                            "bus0_id": bus0_id,
                            "bus1_id": bus1_id,
                            "bus0_lat": bus_coords[bus0_id]['y'],
                            "bus0_lng": bus_coords[bus0_id]['x'],
                            "bus1_lat": bus_coords[bus1_id]['y'],
                            "bus1_lng": bus_coords[bus1_id]['x'],
                            "voltage": line.get('voltage', 0),
                            "capacity": line.get('s_nom', 0),
                            "length": line.get('length', 0),
                            "geometry": line.get('geometry', ''),  # Include geometry data
                            "type": "transmission_line"
                        }
                        lines_data.append(line_data)
            
            # Calculate statistics
            voltage_levels = {}
            if buses_data:
                voltages = [bus['voltage'] for bus in buses_data if bus['voltage'] > 0]
                for voltage in voltages:
                    voltage_levels[f"{voltage}kV"] = voltage_levels.get(f"{voltage}kV", 0) + 1
            
            line_voltage_levels = {}
            if lines_data:
                # Get all unique voltage levels from the data
                voltages = [line.get('voltage', 0) for line in lines_data if line.get('voltage', 0) > 0]
                unique_voltages = sorted(set(voltages), reverse=True)  # Sort descending
                
                # Count lines for each voltage level
                for voltage in unique_voltages:
                    count = sum(1 for line in lines_data if line.get('voltage', 0) == voltage)
                    line_voltage_levels[f"{int(voltage)}kV"] = count
                
                # Debug: Log voltage distribution
                self.logger.info(f"Voltage levels found for {iso_code}: {unique_voltages}")
                self.logger.info(f"Voltage distribution: {line_voltage_levels}")
            
            statistics = {
                "total_buses": len(buses_data),
                "total_lines": len(lines_data),
                "voltage_levels": voltage_levels,
                "line_voltage_levels": line_voltage_levels,
                "iso_code": iso_code.upper()
            }
            
            transmission_data = {
                "iso_code": iso_code.upper(),
                "buses": buses_data,
                "lines": lines_data,
                "statistics": statistics
            }
            
            return {
                "success": True,
                "data": transmission_data,
                "error": None
            }
            
        except ImportError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to import load_network_components: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Error getting transmission network data for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get transmission network data: {str(e)}"
            }

    def get_transmission_generation_data(self, iso_code: str) -> Dict[str, Any]:
        """
        Get power generation data for transmission analysis.
        
        This method loads power plant data from country-specific CSV files
        to visualize generation capacity and fuel types on the transmission map.
        
        Args:
            iso_code (str): 3-letter ISO country code (e.g., "BRA", "USA", "DEU")
        
        Returns:
            Dict[str, Any]: Dictionary with the following structure:
                - success (bool): True if processing succeeded, False otherwise
                - data (dict): Generation data if successful, None otherwise, containing:
                    - plants (list): List of power plant data for map visualization
                    - statistics (dict): Summary statistics and metrics
                - error (str): Error message if processing failed, None otherwise
        
        Example:
            result = analyzer.get_transmission_generation_data("BRA")
            if result["success"]:
                generation_data = result["data"]
                print(f"Total Plants: {generation_data['statistics']['total_plants']}")
            else:
                print(f"Error: {result['error']}")
        """
        try:
            import pandas as pd
            from pathlib import Path
            
            # Set up path for generation data using project root
            project_root = Path(__file__).parent
            generation_file = project_root / 'data' / 'transmission_line_generation' / f'{iso_code.upper()}.csv'
            
            # Check if file exists
            if not generation_file.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"Generation data file not found for {iso_code.upper()}"
                }
            
            # Read CSV file
            df = pd.read_csv(generation_file)
            
            # Validate required columns
            required_columns = ['Capacity (MW)', 'model_fuel', 'Latitude', 'Longitude', 'model_name']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Missing required columns: {missing_columns}"
                }
            
            # Process plants data for visualization
            plants_data = []
            fuel_type_counts = {}
            total_capacity = 0
            
            for _, plant in df.iterrows():
                # Validate coordinates
                lat = plant.get('Latitude')
                lng = plant.get('Longitude')
                
                if pd.isna(lat) or pd.isna(lng) or lat == 0 or lng == 0:
                    continue
                
                capacity = plant.get('Capacity (MW)', 0)
                fuel_type = plant.get('model_fuel', 'unknown')
                plant_name = plant.get('model_name', 'Unknown Plant')
                
                # Count fuel types
                fuel_type_counts[fuel_type] = fuel_type_counts.get(fuel_type, 0) + 1
                total_capacity += capacity
                
                plant_data = {
                    "id": plant.get('comm-out', f"plant_{len(plants_data)}"),
                    "name": plant_name,
                    "capacity_mw": capacity,
                    "fuel_type": fuel_type,
                    "lat": lat,
                    "lng": lng,
                    "bus_id": plant.get('bus_id', ''),
                    "description": plant.get('model_description', ''),
                    "comm_id": plant.get('comm_id', ''),
                    "type": "power_plant"
                }
                plants_data.append(plant_data)
            
            # Calculate statistics
            statistics = {
                "total_plants": len(plants_data),
                "total_capacity_mw": total_capacity,
                "fuel_types": fuel_type_counts,
                "iso_code": iso_code.upper()
            }
            
            generation_data = {
                "iso_code": iso_code.upper(),
                "plants": plants_data,
                "statistics": statistics
            }
            
            return {
                "success": True,
                "data": generation_data,
                "error": None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting transmission generation data for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get transmission generation data: {str(e)}"
            }


    def get_ar6_scenario_drivers(self, iso_code: str) -> Dict[str, Any]:
        """
        Get AR6 scenario drivers for the specified ISO code.
        
        Args:
            iso_code (str): 3-letter ISO country code (e.g., "BRA", "USA", "DEU")
        
        Returns:
            Dict[str, Any]: Dictionary with the following structure:
        
        """
        try:
            from create_ar6_r10_scenario import load_ar6_scenario_drivers, map_iso_to_r10

            fuel_attributes_mapping = {'Gas Price': 'gas', 'Oil Price': 'oil', 'Coal Price': 'coal', 'Biomass Price': 'bioenergy'}

            r10_region, fuel_prices_df = map_iso_to_r10(iso_code)
            ar6_data = load_ar6_scenario_drivers(r10_region)
            iea_baseline_twh, iea_years, iea_values = self.get_iea_historical_data(iso_code)
            fuel_average_price = self.get_fuel_average_price(fuel_prices_df, fuel_attributes_mapping)

            # Years for plotting
            years = [2020, 2025, 2030, 2035, 2040, 2045, 2050]
            # Define climate categories and colors
            categories = ['C1', 'C2', 'C3', 'C4', 'C7']
            colors = {
                'C1': '#2E8B57',  # Sea Green (ambitious)
                'C2': '#4682B4',  # Steel Blue
                'C3': '#DAA520',  # Goldenrod
                'C4': '#CD853F',  # Peru
                'C7': '#B22222'   # Fire Brick (limited action)
            }
            elec_share_attributes = ['Transportation electricity share', 'Industry electricity share', 'Residential and commercial electricity share']

            # Prepare data for all three charts
            co2_data = ar6_data[ar6_data['attribute'] == 'CO2 price']
            elec_data = ar6_data[ar6_data['attribute'] == 'Electricity growth relative to 2020']
            hydrogen_data = ar6_data[ar6_data['attribute'] == 'Hydrogen as a share of electricity']
            
            

            category_co2_medians = {category: {} for category in categories} # Chart 1: CO2 Price Trajectories
            absolute_electricity_demand = {category: {} for category in categories} # Chart 2: Electricity Demand Growth (absolute TWh)
            hydrogen_demand = {category: {} for category in categories} # Chart 3: Hydrogen Demand (absolute TWh)
            fuel_price_data = {attribute: {} for attribute in fuel_attributes_mapping.values()} # Chart 4: Fuel prices projection
            c1_elec_share_data = {attribute: {} for attribute in elec_share_attributes} # Chart 5: Electricity shares projection (C1)
            c7_elec_share_data = {attribute: {} for attribute in elec_share_attributes} # Chart 6: Electricity shares projection (C7)
            for category in categories:
                category_co2_data = co2_data[co2_data['Category'] == category]
                category_elec_data = elec_data[elec_data['Category'] == category]
                category_hydrogen_data = hydrogen_data[hydrogen_data['Category'] == category]
                if not category_co2_data.empty:

                    for year in years:
                        year_co2_data = category_co2_data[category_co2_data['Year'] == year]
                        year_elec_data = category_elec_data[category_elec_data['Year'] == year]
                        year_hydrogen_data = category_hydrogen_data[category_hydrogen_data['Year'] == year]

                        if not year_co2_data.empty:
                            category_co2_medians[category][year] = year_co2_data['median'].iloc[0]
                        else:
                            category_co2_medians[category][year] = np.nan
                        if not year_elec_data.empty:
                            growth_index = year_elec_data['median'].iloc[0]
                            absolute_twh = iea_baseline_twh * growth_index
                            absolute_electricity_demand[category][year] = absolute_twh
                        else:
                            absolute_electricity_demand[category][year] = np.nan
                        if not year_hydrogen_data.empty and not year_elec_data.empty:
                            growth_index = year_elec_data['median'].iloc[0]
                            h2_share = year_hydrogen_data['median'].iloc[0]
                            absolute_elec_twh = iea_baseline_twh * growth_index
                            hydrogen_twh = absolute_elec_twh * h2_share
                            hydrogen_demand[category][year] = hydrogen_twh
                        else:
                            hydrogen_demand[category][year] = np.nan
                        if category == 'C1':
                            for attribute in elec_share_attributes:
                                share_elec_data = ar6_data[(ar6_data['attribute'].str.lower() == attribute.lower()) & (ar6_data['Category'] == category) & (ar6_data['Year'] == year)]
                                if not share_elec_data.empty:
                                    elec_share = share_elec_data['median'].iloc[0]
                                    c1_elec_share_data[attribute][year] = elec_share
                                else:
                                    c1_elec_share_data[attribute][year] = np.nan
                        if category == 'C7':
                            # for fuel price data
                            for attribute, fuel_name in fuel_attributes_mapping.items():
                                fuel_data = ar6_data[(ar6_data['attribute'].str.lower() == attribute.lower()) & (ar6_data['Category'] == category) & (ar6_data['Year'] == year)]
                                fuel_price = fuel_average_price[attribute] if attribute in fuel_average_price else np.nan
                                if not fuel_data.empty and not pd.isna(fuel_price):
                                    fuel_price_data[fuel_name][year] = fuel_data['median'].iloc[0]*fuel_price
                                else:
                                    fuel_price_data[fuel_name][year] = np.nan

                            for attribute in elec_share_attributes:
                                share_elec_data = ar6_data[(ar6_data['attribute'].str.lower() == attribute.lower()) & (ar6_data['Category'] == category) & (ar6_data['Year'] == year)]
                                if not share_elec_data.empty:
                                    elec_share = share_elec_data['median'].iloc[0]
                                    c7_elec_share_data[attribute][year] = elec_share
                                else:
                                    c7_elec_share_data[attribute][year] = np.nan
                            



            return {
                "success": True,
                "data": {
                    "co2_chart_data": category_co2_medians,
                    "elec_chart_data": absolute_electricity_demand,
                    "hydrogen_chart_data": hydrogen_demand,
                    "fuel_price_chart_data": fuel_price_data,
                    "c1_elec_share_chart_data": c1_elec_share_data,
                    "c7_elec_share_chart_data": c7_elec_share_data,
                    "iea_years": iea_years,
                    "iea_values": iea_values,
                    "categories": categories,
                    "colors": colors,
                    "years": years,
                    "fuel_attributes_mapping": fuel_attributes_mapping,
                    "r10_region": r10_region
                },
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get AR6 scenario drivers: {str(e)}"
            }
    

    def get_iea_historical_data(self, iso_code: str) -> Dict[str, Any]:

            # Load IEA baseline data for absolute calculations and historical plotting
        try:
            iea_file = Path("scenario_drivers/iea_electricity_summary_2018_2022.csv")
            if iea_file.exists():
                iea_df = pd.read_csv(iea_file)
                iso_iea = iea_df[iea_df['iso'] == iso_code.upper()]
                if not iso_iea.empty:
                    # Use total electricity production as baseline (most recent year)
                    iea_baseline_twh = iso_iea['total_production_twh'].iloc[-1]
                    
                    # Prepare historical data for plotting
                    iea_historical = iso_iea.sort_values('year')
                    iea_years = iea_historical['year'].tolist()
                    iea_values = iea_historical['total_production_twh'].tolist()
                    # print(f"   📊 IEA historical data: {len(iea_years)} years ({min(iea_years)}-{max(iea_years)})")
                    
                else:
                    iea_baseline_twh = 100  # Fallback for missing data
                    iea_years = []
                    iea_values = []
            else:
                iea_baseline_twh = 100  # Fallback
                iea_years = []
                iea_values = []
            return iea_baseline_twh, iea_years, iea_values
        except Exception as e:
            print(f"   ⚠️  Could not load IEA baseline: {e}")
            iea_baseline_twh = 100
            iea_years = []
            iea_values = []
            return iea_baseline_twh, iea_years, iea_values


    def get_fuel_average_price(self, iso_fuel_prices_df: pd.DataFrame, fuel_attributes_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Get average fuel price for the specified ISO code.
        
        Args:
            iso_fuel_prices_df (pd.DataFrame): DataFrame containing fuel prices for the specified ISO code
        
        Returns:
            Dict[str, Any]: Dictionary with the following structure:
        """
        fuel_average_price = {}
        try:

            if iso_fuel_prices_df.empty:
                return {}

            for fuel, fuel_attribute in fuel_attributes_mapping.items():
                fuel_high_price_column = f'{fuel_attribute}_high'
                fuel_low_price_column = f'{fuel_attribute}_low'
                if fuel_high_price_column in iso_fuel_prices_df.columns and fuel_low_price_column in iso_fuel_prices_df.columns:
                    fuel_high_price = iso_fuel_prices_df[fuel_high_price_column].iloc[0]
                    fuel_low_price = iso_fuel_prices_df[fuel_low_price_column].iloc[0]
                    fuel_average_price[fuel] = (fuel_high_price + fuel_low_price) / 2
                else:
                    fuel_average_price[fuel] = np.nan
            return fuel_average_price
        except Exception as e:
            print(f"❌ Error: {e}")
            return fuel_average_price

# Example usage for testing
if __name__ == "__main__":
    analyzer = DashboardDataAnalyzer()
    
    result = analyzer.get_ar6_scenario_drivers("IND")
    print(result)

    # if result["success"]:
    #     print("✅ Solar renewable zones retrieved successfully")
    #     print(f"Total Zones: {result['data']['statistics']['total_cells']}")
    # else:
    #     print(f"❌ Error: {result['error']}")
    
    # Test with India
    # result = analyzer.get_energy_metrics("IND")
    # if result["success"]:
    #     print("✅ Energy metrics retrieved successfully")
    #     print(f"ISO Region: {result['data']['iso_region']}")
    #     print(f"Years available: {result['data']['years_available']}")
    # else:
    #     print(f"❌ Error: {result['error']}")