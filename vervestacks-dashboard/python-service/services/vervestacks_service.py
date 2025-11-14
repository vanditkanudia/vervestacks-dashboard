import pandas as pd
from typing import Dict, List, Optional
import logging
import sys
import os

# Add project paths for module imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # Navigate: services -> python-service -> vervestacks-dashboard -> VerveStacks
scripts_dir = os.path.join(project_root, '2_ts_design', 'scripts')

sys.path.insert(0, project_root)
sys.path.insert(0, scripts_dir)

# Change working directory to project root so VerveStacks functions can find their files
os.chdir(project_root)

class VerveStacksService:
    """
    Service layer for VerveStacks data operations.
    Acts as an intermediary between API endpoints and VerveStacks processing logic.
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.processor = None
        self.logger = logging.getLogger(__name__)
        self._initialize_processor()
        self._initialize_energy_analyzer()
    
    def _initialize_processor(self):
        """Initialize the VerveStacks processor once."""
        try:
            # Import here to avoid import errors during module loading
            from verve_stacks_processor import VerveStacksProcessor
            
            # Use absolute path for data directory to avoid path resolution issues
            data_dir = os.path.join(project_root, "data")
            self.processor = VerveStacksProcessor(data_dir=data_dir, cache_dir=self.cache_dir)
            self.logger.info("VerveStacks processor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize VerveStacks processor: {e}")
            self.processor = None
    
    def _initialize_energy_analyzer(self):
        """Initialize the dashboard data analyzer."""
        try:
            # Import here to avoid import errors during module loading
            from dashboard_data_analyzer import DashboardDataAnalyzer
            
            self.energy_analyzer = DashboardDataAnalyzer()
            self.logger.info("Dashboard data analyzer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize dashboard data analyzer: {e}")
            self.energy_analyzer = None
     
    
    def get_energy_analysis(self, iso_code: str, year: int = 2022) -> Dict:
        """
        Get comprehensive energy analysis data for a specific ISO code.
        
        Args:
            iso_code: 3-letter ISO country code
            year: Analysis year
            
        Returns:
            Dictionary containing all energy analysis data
        """
        if not self.processor:
            raise Exception("VerveStacks processor not available")
        
        try:
            # Import here to avoid import errors
            from existing_stock_processor import process_existing_stock
            from iso_processing_functions import calibration_data
            # Processing energy analysis data
            # Create ISO processor (this loads all the data)
            iso_processor = self.processor.get_ISOProcessor(
                iso_code, 
                add_documentation=False,
                auto_commit=False,
                skip_timeslices=True  # Skip time-slice processing for faster API response
            )
            
            # Get the core data using existing functions
            df_irena_util, df_ember_util, df_grouped_gem = process_existing_stock(
                iso_processor, add_documentation=False
            )
             
            # Get comprehensive calibration data
            calibration_data(iso_processor, df_irena_util, df_ember_util, df_grouped_gem)
            
            # Format data for charts
            return self._format_chart_data(
                iso_code, year, df_irena_util, df_ember_util, df_grouped_gem
            )
            
        except Exception as e:
            self.logger.error(f"Error processing {iso_code}: {e}")
            raise Exception(f"Failed to process {iso_code}: {str(e)}")
   
    def get_technology_mix(self, iso_code: str, year: int = 2022) -> Dict:
        """Get technology mix and capacity data."""
        if not self.processor:
            raise Exception("VerveStacks processor not available")
        
        try:
            # Import here to avoid import errors
            from existing_stock_processor import process_existing_stock
            
            iso_processor = self.processor.process_iso(
                iso_code, 
                add_documentation=False,
                skip_timeslices=True
            )
            
            _, _, df_grouped_gem = process_existing_stock(
                iso_processor, add_documentation=False
            )
            
            # Calculate technology mix
            tech_mix = df_grouped_gem.groupby('model_fuel').agg({
                'capacity_gw': 'sum',
                'efficiency': 'mean'
            }).round(3).to_dict('index')
            
            return {
                "iso_code": iso_code,
                "year": year,
                "technology_mix": tech_mix,
                "total_capacity_gw": df_grouped_gem['capacity_gw'].sum()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting technology mix for {iso_code}: {e}")
            raise Exception(f"Failed to get technology mix: {str(e)}")
    
    def get_co2_intensity(self, iso_code: str, year: int = 2022) -> Dict:
        """Get CO2 intensity and fuel consumption data."""
        if not self.processor:
            raise Exception("VerveStacks processor not available")
        
        try:
            # Import here to avoid import errors
            from existing_stock_processor import process_existing_stock
            from iso_processing_functions import calibration_data
            
            iso_processor = self.processor.process_iso(
                iso_code, 
                add_documentation=False,
                skip_timeslices=True
            )
            
            df_irena_util, df_ember_util, df_grouped_gem = process_existing_stock(
                iso_processor, add_documentation=False
            )
            
            # Get calibration data for fuel consumption
            calibration_data(iso_processor, df_irena_util, df_ember_util, df_grouped_gem)
            
            # Calculate CO2 intensity metrics
            co2_data = self._calculate_co2_metrics(df_grouped_gem, df_irena_util, df_ember_util)
            
            return {
                "iso_code": iso_code,
                "year": year,
                "co2_intensity": co2_data
            }
            
        except Exception as e:
            self.logger.error(f"Error getting CO2 intensity for {iso_code}: {e}")
            raise Exception(f"Failed to get CO2 intensity: {str(e)}")
    
    def _format_chart_data(self, iso_code: str, year: int, 
                          df_irena_util: pd.DataFrame, 
                          df_ember_util: pd.DataFrame, 
                          df_grouped_gem: pd.DataFrame) -> Dict:
        """Format data for dashboard charts."""
        
        # Utilization data for charts
        utilization_data = {
            "irena": df_irena_util.to_dict('records'),
            "ember": df_ember_util.to_dict('records')
        }
        
        # Technology mix
        tech_mix = df_grouped_gem.groupby('model_fuel').agg({
            'capacity_gw': 'sum',
            'efficiency': 'mean'
        }).round(3).to_dict('index')
        
        # Capacity comparison
        capacity_comparison = df_grouped_gem.groupby('model_fuel').agg({
            'capacity_gw': 'sum'
        }).round(3).to_dict('index')
        
        return {
            "iso_code": iso_code,
            "year": year,
            "utilization_data": utilization_data,
            "technology_mix": tech_mix,
            "capacity_comparison": capacity_comparison,
            "total_capacity_gw": df_grouped_gem['capacity_gw'].sum(),
            "data_sources": ["GEM", "IRENA", "EMBER", "UNSD"]
        }
    
    def _calculate_co2_metrics(self, df_grouped_gem: pd.DataFrame, 
                              df_irena_util: pd.DataFrame, 
                              df_ember_util: pd.DataFrame) -> Dict:
        """Calculate CO2 intensity metrics from the data."""
        
        # Basic CO2 intensity calculation (simplified)
        # In a real implementation, you'd use actual emission factors
        co2_factors = {
            'coal': 0.8,      # kg CO2/kWh
            'gas': 0.4,       # kg CO2/kWh
            'oil': 0.7,       # kg CO2/kWh
            'nuclear': 0.0,   # kg CO2/kWh
            'hydro': 0.0,     # kg CO2/kWh
            'solar': 0.0,     # kg CO2/kWh
            'wind': 0.0,      # kg CO2/kWh
            'bioenergy': 0.1  # kg CO2/kWh
        }
        
        co2_data = {}
        for tech, factor in co2_factors.items():
            if tech in df_grouped_gem['model_fuel'].values:
                tech_data = df_grouped_gem[df_grouped_gem['model_fuel'] == tech]
                total_capacity = tech_data['capacity_gw'].sum()
                avg_efficiency = tech_data['efficiency'].mean()
                
                co2_data[tech] = {
                    "capacity_gw": round(total_capacity, 3),
                    "efficiency": round(avg_efficiency, 3),
                    "co2_factor_kg_kwh": factor,
                    "estimated_annual_co2_kt": round(total_capacity * 8.76 * factor * avg_efficiency / 1000, 1)
                }
        
        return co2_data

    def get_existing_stock_metrics(self, iso_code: str) -> Dict:
        """Get existing stock metrics from GEM data for dashboard charts."""
        if not self.energy_analyzer:
            raise Exception("Energy metrics analyzer not available")
        
        try:
            result = self.energy_analyzer.get_existing_stock_metrics(iso_code)
            return result
        except Exception as e:
            self.logger.error(f"Error getting existing stock metrics for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get existing stock metrics: {str(e)}"
            }


    def get_solar_renewable_zones(self, iso_code: str) -> Dict:
        """Get solar renewable energy zones data for a country."""
        if not self.energy_analyzer:
            raise Exception("Energy metrics analyzer not available")
        
        try:
            result = self.energy_analyzer.get_solar_renewable_zones(iso_code)
            return result
        except Exception as e:
            self.logger.error(f"Error getting solar renewable zones for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get solar renewable zones: {str(e)}"
            }

    def get_wind_renewable_zones(self, iso_code: str, wind_type: str = 'onshore') -> Dict:
        """Get wind renewable energy zones data for a country (offshore or onshore)."""
        if not self.energy_analyzer:
            raise Exception("Energy metrics analyzer not available")
        
        try:
            result = self.energy_analyzer.get_wind_renewable_zones(iso_code, wind_type)
            return result
        except Exception as e:
            self.logger.error(f"Error getting wind renewable zones for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get wind renewable zones: {str(e)}"
            }
    
    def get_transmission_data(self, iso_code: str, target_clusters: int = None) -> Dict:
        """Get transmission line data from create_regions_simple.py for dashboard visualization."""
        if not self.energy_analyzer:
            raise Exception("Energy metrics analyzer not available")
        
        try:
            result = self.energy_analyzer.get_transmission_data(iso_code, target_clusters)
            return result
        except Exception as e:
            self.logger.error(f"Error getting transmission data for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get transmission data: {str(e)}"
            }

    def get_transmission_network_data(self, iso_code: str) -> Dict:
        """Get transmission network data from load_network_components for dashboard visualization."""
        if not self.energy_analyzer:
            raise Exception("Energy metrics analyzer not available")
        
        try:
            result = self.energy_analyzer.get_transmission_network_data(iso_code)
            return result
        except Exception as e:
            self.logger.error(f"Error getting transmission network data for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get transmission network data: {str(e)}"
            }

    def get_transmission_generation_data(self, iso_code: str) -> Dict:
        """Get transmission generation data from power plants CSV files for dashboard visualization."""
        if not self.energy_analyzer:
            raise Exception("Energy metrics analyzer not available")
        
        try:
            result = self.energy_analyzer.get_transmission_generation_data(iso_code)
            return result
        except Exception as e:
            self.logger.error(f"Error getting transmission generation data for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get transmission generation data: {str(e)}"
            }

    def get_fuel_colors(self) -> Dict:
        """Get fuel colors from Python energy_colors.py file via dashboard data analyzer."""
        if not self.energy_analyzer:
            raise Exception("Energy metrics analyzer not available")
        
        try:
            result = self.energy_analyzer.get_fuel_colors()
            return result
        except Exception as e:
            self.logger.error(f"Error getting fuel colors: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get fuel colors: {str(e)}"
            }
    
    def get_ar6_scenario_drivers(self, iso_code: str) -> Dict:
        """Get AR6 scenario drivers for demand and fuel price evolution."""
        if not self.energy_analyzer:
            raise Exception("Energy metrics analyzer not available")
        
        try:
            result = self.energy_analyzer.get_ar6_scenario_drivers(iso_code)
            return result
        except Exception as e:
            self.logger.error(f"Error getting AR6 scenario drivers for {iso_code}: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get AR6 scenario drivers: {str(e)}"
            }