"""
8760-Hour Supply and Demand Constructor

Creates complete hourly supply and demand profiles for any ISO using:
- Fixed baseline: Hydro (demand-shaped) + Nuclear (flat) from 2022 actual generation  
- Variable renewables: Solar and wind from REZoning grid cells, LCOE-optimized with hourly shapes

Output: Stacked area chart showing supply components + demand line
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent  # Go up from scripts -> 2_ts_design -> root
sys.path.insert(0, str(project_root))

from branding_manager import VerveStacksBrandingManager
from energy_colors import ENERGY_COLORS
from shared_data_loader import get_shared_loader
from verve_stacks_processor import VerveStacksProcessor

# Using robust centralized branding system


class Supply8760Constructor:
    """
    Constructs complete 8760-hour supply and demand profiles for ISO analysis
    """
    
    def __init__(self, data_path="../data/", force_reload=False):
        self.data_path = data_path
        self.force_reload = force_reload
        self.shared_loader = get_shared_loader(data_path)
        
        # Initialize branding manager
        self.branding = VerveStacksBrandingManager()
        
        # Using robust centralized branding system
        
        # Country name mapping
        self.country_names = {
            'CHE': 'Switzerland',
            'JPN': 'Japan',
            'DEU': 'Germany',
            'USA': 'United States',
            'GBR': 'United Kingdom',
            'FRA': 'France',
            'ITA': 'Italy',
            'ESP': 'Spain',
            'NLD': 'Netherlands',
            'BEL': 'Belgium',
            'AUT': 'Austria',
            'DNK': 'Denmark',
            'SWE': 'Sweden',
            'NOR': 'Norway',
            'FIN': 'Finland',
            'POL': 'Poland',
            'CZE': 'Czech Republic',
            'HUN': 'Hungary',
            'ROU': 'Romania',
            'BGR': 'Bulgaria',
            'HRV': 'Croatia',
            'SVN': 'Slovenia',
            'SVK': 'Slovakia',
            'EST': 'Estonia',
            'LVA': 'Latvia',
            'LTU': 'Lithuania',
            'IRL': 'Ireland',
            'PRT': 'Portugal',
            'GRC': 'Greece',
            'MLT': 'Malta',
            'CYP': 'Cyprus',
            'LUX': 'Luxembourg'
        }
        
    def load_demand_profile(self, iso_code):
        """Load 8760-hour demand profile for ISO"""
        # Load cached demand data
        demand_df = self.shared_loader.get_era5_demand_data()
        
        # Load region mapping
        region_map_df = self.shared_loader.get_vs_mappings_sheet('kinesys_region_map')
        region_map = dict(zip(region_map_df['2-alpha code'], region_map_df['iso']))
        
        # Pivot demand data by country
        demand_pivot = demand_df.pivot_table(
            index=['Hour', 'Day', 'Month', 'mm_dd_hh'], 
            columns='Country', 
            values='MW', 
            aggfunc='first'
        ).reset_index().sort_values('mm_dd_hh')
        
        # Map country codes to ISOs and find our target ISO
        iso_demand_column = None
        for country_code in demand_pivot.columns:
            if country_code in ['Hour', 'Day', 'Month', 'mm_dd_hh']:
                continue
            mapped_iso = region_map.get(country_code)
            if mapped_iso == iso_code:
                iso_demand_column = country_code
                break
        
        if iso_demand_column is None:
            raise ValueError(f"No demand data found for ISO: {iso_code}")
        
        # Extract 8760-hour demand profile
        iso_demand_profile = demand_pivot[iso_demand_column].values
        annual_demand_mwh = iso_demand_profile.sum()
        
        return iso_demand_profile
    
    def build_baseline_profiles(self, iso_code, demand_profile):
        """Build nuclear and hydro baseline generation profiles"""
        # Try to get baseline data from best available source
        nuclear_hourly, hydro_hourly = self._get_baseline_data(iso_code, demand_profile)
        
        # If still no data, set to zero
        if nuclear_hourly is None:
            nuclear_hourly = np.zeros(8760)
        if hydro_hourly is None:
            hydro_hourly = np.zeros(8760)
            
        return nuclear_hourly, hydro_hourly
    
    def _get_baseline_data(self, iso_code, demand_profile):
        """Get baseline generation data from best available source"""
        # Try monthly data first (most detailed)
        monthly_df = self.shared_loader.get_monthly_hydro_data()
        
        nuclear_hourly, hydro_hourly = self._extract_monthly_baseline(iso_code, monthly_df, demand_profile)
        
        # If monthly data missing, try yearly data
        if nuclear_hourly is None or hydro_hourly is None:
            yearly_df = self.shared_loader.get_ember_data()
            
            nuclear_yearly, hydro_yearly = self._extract_yearly_baseline(iso_code, yearly_df, demand_profile)
            
            # Use yearly data for missing components
            if nuclear_hourly is None:
                nuclear_hourly = nuclear_yearly
            if hydro_hourly is None:
                hydro_hourly = hydro_yearly
        
        return nuclear_hourly, hydro_hourly
    
    def _get_country_name(self, iso_code):
        """Convert ISO code to readable country name"""
        return self.country_names.get(iso_code, iso_code)
    
    def _extract_monthly_baseline(self, iso_code, monthly_df, demand_profile):
        """Try to build baseline from monthly data"""
        # Filter for this ISO's generation data
        iso_monthly = monthly_df[
            (monthly_df['Country code'] == iso_code) & 
            (monthly_df['Category'] == 'Electricity generation') &
            (monthly_df['Unit'] == 'TWh')
        ].copy()
        
        if iso_monthly.empty:
            return None, None
            
        # Extract month from date if Date column exists, otherwise try Month column
        if 'Date' in iso_monthly.columns:
            iso_monthly['month'] = pd.to_datetime(iso_monthly['Date']).dt.month
        elif 'Month' in iso_monthly.columns:
            iso_monthly['month'] = iso_monthly['Month']
        else:
            # No date/month column found, assume data is already monthly
            iso_monthly['month'] = range(1, len(iso_monthly) + 1)
        
        # Get nuclear data
        nuclear_monthly = iso_monthly[iso_monthly['Variable'] == 'Nuclear'].groupby('month')['Value'].mean()
        nuclear_hourly = self._create_flat_profile(nuclear_monthly) if not nuclear_monthly.empty else None
        
        # Get hydro data  
        hydro_monthly = iso_monthly[iso_monthly['Variable'] == 'Hydro'].groupby('month')['Value'].mean()
        hydro_hourly = self._create_demand_shaped_profile(hydro_monthly, demand_profile) if not hydro_monthly.empty else None
        
        return nuclear_hourly, hydro_hourly
    
    def _extract_yearly_baseline(self, iso_code, yearly_df, demand_profile):
        """Try to build baseline from yearly data with regional fallback"""
        # Check what columns are available in the EMBER data
        if 'Date' in yearly_df.columns:
            # Filter for this ISO's recent generation data using Date column
            iso_yearly = yearly_df[
                (yearly_df['Country code'] == iso_code) &
                (yearly_df['Category'] == 'Electricity generation') &
                (yearly_df['Unit'] == 'TWh') &
                (yearly_df['Date'] >= '2020-01-01')  # Recent years only
            ].copy()
        elif 'Year' in yearly_df.columns:
            # Filter for this ISO's recent generation data using Year column
            iso_yearly = yearly_df[
                (yearly_df['Country code'] == iso_code) &
                (yearly_df['Category'] == 'Electricity generation') &
                (yearly_df['Unit'] == 'TWh') &
                (yearly_df['Year'] >= 2020)  # Recent years only
            ].copy()
        else:
            # No date/year column found, use all data
            iso_yearly = yearly_df[
                (yearly_df['Country code'] == iso_code) &
                (yearly_df['Category'] == 'Electricity generation') &
                (yearly_df['Unit'] == 'TWh')
            ].copy()
        
        if iso_yearly.empty:
            return None, None
            
        # Get average annual values
        nuclear_annual = iso_yearly[iso_yearly['Variable'] == 'Nuclear']['Value'].mean()
        hydro_annual = iso_yearly[iso_yearly['Variable'] == 'Hydro']['Value'].mean()
        
        # Create flat nuclear profile
        nuclear_hourly = np.full(8760, nuclear_annual * 1_000_000 / 8760) if not pd.isna(nuclear_annual) else None
        
        # Create hydro profile with demand-shaped pattern
        hydro_hourly = None
        if not pd.isna(hydro_annual):
            hydro_hourly = self._create_demand_shaped_annual(hydro_annual, demand_profile)
        
        return nuclear_hourly, hydro_hourly
    
    def _create_flat_profile(self, monthly_data):
        """Create flat hourly profile from monthly TWh data"""
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        hourly_profile = np.zeros(8760)
        
        hour_start = 0
        for month in range(1, 13):
            hours_in_month = days_in_month[month-1] * 24
            hour_end = hour_start + hours_in_month
            
            monthly_twh = monthly_data.get(month, 0)
            monthly_mw = monthly_twh * 1_000_000 / hours_in_month  # TWh to MW
            
            hourly_profile[hour_start:hour_end] = monthly_mw
            hour_start = hour_end
            
        return hourly_profile
    
    def _create_demand_shaped_profile(self, monthly_data, demand_profile):
        """Create demand-shaped hourly profile from monthly TWh data"""
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        hourly_profile = np.zeros(8760)
        
        hour_start = 0
        for month in range(1, 13):
            hours_in_month = days_in_month[month-1] * 24
            hour_end = hour_start + hours_in_month
            
            monthly_twh = monthly_data.get(month, 0)
            monthly_mwh = monthly_twh * 1_000_000  # TWh to MWh
            
            # Get demand shape for this month
            month_demand = demand_profile[hour_start:hour_end]
            
            if len(month_demand) > 0 and month_demand.sum() > 0:
                # Normalize demand to fractions
                demand_shape = month_demand / month_demand.sum()
                # Distribute monthly MWh according to demand shape
                month_hydro = demand_shape * monthly_mwh
                hourly_profile[hour_start:hour_end] = month_hydro
            
            hour_start = hour_end
            
        return hourly_profile
    
    def get_total_electricity_generation(self, iso_code, year):
        """
        Get total electricity generation for a specific ISO and year from EMBER data.
        
        Parameters:
        -----------
        iso_code : str
            3-letter ISO country code (e.g., 'USA', 'DEU', 'CHE')
        year : int
            Year for which to get generation data
            
        Returns:
        --------
        float or None
            Total electricity generation in TWh, or None if not found
        """
        # Load EMBER yearly data
        yearly_df = self.shared_loader.get_ember_data()
        
        # Filter for total generation data
        generation_data = yearly_df[
            (yearly_df['Country code'] == iso_code) &
            (yearly_df['Year'] == year) &
            (yearly_df['Category'] == 'Electricity generation') &
            (yearly_df['Subcategory'] == 'Total') &
            (yearly_df['Variable'] == 'Total Generation') &
            (yearly_df['Unit'] == 'TWh')
        ]
        
        if generation_data.empty:
            return None
        
        total_generation = generation_data['Value'].iloc[0]
        return total_generation
    
    
    def get_generation_by_fuel(self, iso_code, year):
        """
        Get electricity generation breakdown by fuel type for a specific ISO and year.
        
        Parameters:
        -----------
        iso_code : str
            3-letter ISO country code (e.g., 'USA', 'DEU', 'CHE')
        year : int
            Year for which to get generation data
            
        Returns:
        --------
        pandas.DataFrame
            DataFrame with fuel types and their generation values in TWh
        """
        # Load EMBER yearly data
        yearly_df = self.shared_loader.get_ember_data()
        
        # Filter for fuel-specific generation data
        fuel_data = yearly_df[
            (yearly_df['Country code'] == iso_code) &
            (yearly_df['Year'] == year) &
            (yearly_df['Category'] == 'Electricity generation') &
            (yearly_df['Subcategory'] == 'Fuel') &
            (yearly_df['Unit'] == 'TWh')
        ].copy()
        
        if fuel_data.empty:
            return pd.DataFrame()
        
        # Clean and sort the data
        fuel_breakdown = fuel_data[['Variable', 'Value']].copy()
        fuel_breakdown = fuel_breakdown.dropna(subset=['Value'])
        fuel_breakdown = fuel_breakdown.sort_values('Value', ascending=False)
        
        return fuel_breakdown

    def _standardize_fuel_name(self, fuel_name):
        """
        Standardize fuel names to match EMBER variable names.
        
        Parameters:
        -----------
        fuel_name : str
            Raw fuel name from IRENA or EMBER data
            
        Returns:
        --------
        str
            Standardized fuel name
        """
        fuel_mapping = {
            'solar': 'Solar',
            'wind': 'Wind',
            'hydro': 'Hydro',
            'nuclear': 'Nuclear',
            'coal': 'Coal',
            'gas': 'Natural gas',
            'bioenergy': 'Bioenergy',
            'oil': 'Oil'
        }
        
        # Convert to lowercase for matching
        fuel_lower = str(fuel_name).lower()
        
        # Return mapped name or original if no mapping found
        return fuel_mapping.get(fuel_lower, fuel_name)

    def create_demand_shaped_generation_from_ember(self, iso_code, year, total_generation_twh=None):
        """
        Create hourly generation profile shaped by demand pattern using EMBER annual total.
        
        Parameters:
        -----------
        iso_code : str
             3-letter ISO country code (e.g., 'DEU', 'USA')
        year : int
             Year for EMBER generation data (e.g., 2022)
        total_generation_twh : float, optional
             Total annual generation in TWh. If provided, uses this value.
             If None, gets from EMBER data for iso_code and year.
             
        Returns:
        --------
        numpy.ndarray
             8760-hour generation profile in GW
        """
        # Load demand profile for the ISO
        demand_profile = self.load_demand_profile(iso_code)
        
        # Calculate hourly shares (normalize demand profile)
        hourly_shares = demand_profile / demand_profile.sum()
        
        # Get total annual generation
        if total_generation_twh is not None:
            pass
        else:
            total_generation_twh = self.get_total_electricity_generation(iso_code, year)
            if total_generation_twh is None:
                raise ValueError(f"No EMBER generation data found for {iso_code} in {year}")
        
        # Convert TWh to GWh, then distribute according to demand shape
        total_generation_gwh = total_generation_twh * 1000  # TWh to GWh
        
        # Create hourly generation profile in GW
        generation_profile_gw = hourly_shares * total_generation_gwh
        
        return generation_profile_gw

    def create_demand_shaped_generation_by_fuel(self, iso_code, year, fuel_generation_twh=None):
        """
        Create hourly generation profiles shaped by demand pattern for each fuel type.
        
        Parameters:
        -----------
        iso_code : str
             3-letter ISO country code (e.g., 'DEU', 'USA')
        year : int
             Year for EMBER generation data (e.g., 2022)
        fuel_generation_twh : dict, optional
             Dictionary with fuel types as keys and generation in TWh as values.
             If provided, uses these values. If None, gets from EMBER data.
             Example: {'Coal': 123.45, 'Natural gas': 89.32, 'Nuclear': 67.89}
             
        Returns:
        --------
        dict
             Dictionary with fuel types as keys and 8760-hour generation profiles in GW as values
        """
        # Load demand profile for the ISO
        demand_profile = self.load_demand_profile(iso_code)
        
        # Calculate hourly shares (normalize demand profile)
        hourly_shares = demand_profile / demand_profile.sum()
        
        # Get fuel-specific generation data
        if fuel_generation_twh is not None:
            fuel_data = fuel_generation_twh
        else:
            fuel_breakdown_df = self.get_generation_by_fuel(iso_code, year)
            if fuel_breakdown_df.empty:
                raise ValueError(f"No fuel generation data found for {iso_code} in {year}")
            
            # Convert DataFrame to dictionary
            fuel_data = dict(zip(fuel_breakdown_df['Variable'], fuel_breakdown_df['Value']))
        
        # Create hourly profiles for each fuel type
        fuel_profiles = {}
        
        for fuel_type, annual_twh in fuel_data.items():
            if annual_twh > 0:  # Only process fuels with positive generation
                # Convert TWh to GWh, then distribute according to demand shape
                annual_gwh = annual_twh * 1000  # TWh to GWh
                
                # Create hourly generation profile in GW
                fuel_profile_gw = hourly_shares * annual_gwh
                fuel_profiles[fuel_type] = fuel_profile_gw
        
        return fuel_profiles

    def _create_demand_shaped_annual(self, annual_twh, demand_profile):
        """Create demand-shaped profile from annual TWh (uniform monthly distribution)"""
        monthly_twh = annual_twh / 12  # Distribute evenly across months
        monthly_data = pd.Series({month: monthly_twh for month in range(1, 13)})
        return self._create_demand_shaped_profile(monthly_data, demand_profile)
    
    def get_capacity_by_fuel(self, iso_code, year):
        """
        Get generation capacity breakdown by fuel type for a specific ISO and year.
        
        Uses utilization functions from existing_stock_processor.py:
        - IRENA: Hydro, Solar, Wind capacity data (from calculate_irena_utilization)
        - EMBER: Gas, Coal, Nuclear capacity data (from calculate_ember_utilization)
        
        Parameters:
        -----------
        iso_code : str
            3-letter ISO country code (e.g., 'USA', 'DEU', 'CHE')
        year : int
            Year for which to get capacity data
            
        Returns:
        --------
        dict
            Dictionary with fuel types as keys and capacity data as values:
            {
                'Hydro': {'capacity_gw': float, 'source': str, 'data_type': str},
                'Solar': {'capacity_gw': float, 'source': str, 'data_type': str},
                'Wind': {'capacity_gw': float, 'source': str, 'data_type': str},
                'Coal': {'capacity_gw': float, 'source': str, 'data_type': str},
                'Gas': {'capacity_gw': float, 'source': str, 'data_type': str},
                'Nuclear': {'capacity_gw': float, 'source': str, 'data_type': str}
            }
        """
        # Initialize result dictionary
        fuel_capacity = {}
        
        try:
            # Create proper VerveStacksProcessor for consistent data preprocessing
            try:
                verve_processor = VerveStacksProcessor(data_dir=self.data_path)
            except Exception as e:
                print(f"   ⚠️ Warning: Could not initialize VerveStacksProcessor: {e}")
                # Fallback to shared_loader if VerveStacksProcessor fails
                verve_processor = self.shared_loader
            
            # Create a minimal ISO processor structure that the utilization functions expect
            class MinimalISOProcessor:
                def __init__(self, iso_code, verve_processor):
                    self.input_iso = iso_code
                    self.main = verve_processor  # VerveStacksProcessor has the preprocessed data attributes
            
            # Create the minimal processor
            minimal_processor = MinimalISOProcessor(iso_code, verve_processor)
            
            # Import and use the utilization functions
            import sys
            from pathlib import Path
            
            # Add existing_stock_processor to path
            existing_stock_path = Path(__file__).parent.parent.parent / "existing_stock_processor.py"
            if not existing_stock_path.exists():
                raise FileNotFoundError(f"existing_stock_processor.py not found at {existing_stock_path}")
            
            sys.path.insert(0, str(existing_stock_path.parent))
            
            from existing_stock_processor import calculate_irena_utilization, calculate_ember_utilization
            
            # === IRENA DATA: Hydro, Solar, Wind (from utilization function) ===
            irena_util = calculate_irena_utilization(minimal_processor)
            
            if not irena_util.empty:
                # Process IRENA renewable fuels
                irena_renewables = ['hydro', 'solar', 'windon']
                
                for _, row in irena_util.iterrows():
                    if row['year'] == year and row['model_fuel'] in irena_renewables:
                        fuel_key = self._standardize_fuel_name(row['model_fuel']).title()
                        capacity_gw = row['Capacity_GW']
                        generation_twh = row['Generation_TWh']
                        utilization = row['utilization_factor']
                        
                        # Handle NaN utilization factors (can occur when capacity is 0)
                        if pd.isna(utilization):
                            utilization = 0.0
                        elif pd.isna(capacity_gw) or capacity_gw == 0:
                            # Skip fuels with zero or missing capacity
                            continue
                        
                        fuel_capacity[fuel_key] = {
                            'capacity_gw': float(capacity_gw),  # Ensure it's a valid float
                            'source': 'IRENA (utilization)',
                            'data_type': 'direct',
                            'data_year': year,
                            'generation_twh': float(generation_twh),  # Ensure it's a valid float
                            'utilization_factor': float(utilization)  # Ensure it's a valid float
                        }
            
            # === EMBER DATA: Gas, Coal, Nuclear (from utilization function) ===
            ember_util = calculate_ember_utilization(minimal_processor)
            
            if not ember_util.empty:
                # Process EMBER conventional fuels
                ember_fuels = ['coal', 'gas', 'nuclear']
                
                for _, row in ember_util.iterrows():
                    if row['year'] == year and row['model_fuel'] in ember_fuels:
                        fuel_key = self._standardize_fuel_name(row['model_fuel']).title()
                        capacity_gw = row['Capacity_GW']
                        generation_twh = row['Generation_TWh']
                        utilization = row['utilization_factor']
                        
                        # Handle NaN utilization factors (can occur when capacity is 0)
                        if pd.isna(utilization):
                            utilization = 0.0
                        elif pd.isna(capacity_gw) or capacity_gw == 0:
                            # Skip fuels with zero or missing capacity
                            continue
                        
                        fuel_capacity[fuel_key] = {
                            'capacity_gw': float(capacity_gw),  # Ensure it's a valid float
                            'source': 'EMBER (utilization)',
                            'data_type': 'direct',
                            'data_year': year,
                            'generation_twh': float(generation_twh),  # Ensure it's a valid float
                            'utilization_factor': float(utilization)  # Ensure it's a valid float
                        }
            
            # === Summary ===
            if fuel_capacity:
                # Ensure all values are JSON-serializable
                for fuel_type, data in fuel_capacity.items():
                    for key, value in data.items():
                        if pd.isna(value):
                            data[key] = None
                        elif isinstance(value, (np.integer, np.floating)):
                            data[key] = float(value)
                        elif isinstance(value, np.ndarray):
                            data[key] = value.tolist()
                
                total_capacity_gw = sum(fuel['capacity_gw'] for fuel in fuel_capacity.values())
                
                # Summary information available in fuel_capacity dict
                
                # Final validation: ensure all values are JSON-serializable
                try:
                    import json
                    json.dumps(fuel_capacity)  # Test JSON serialization
                    return fuel_capacity
                except (ValueError, TypeError) as e:
                    # Clean up any remaining problematic values
                    for fuel_type, data in fuel_capacity.items():
                        for key, value in data.items():
                            if pd.isna(value) or value is None:
                                data[key] = 0.0
                            elif isinstance(value, (np.integer, np.floating)):
                                data[key] = float(value)
                            elif isinstance(value, np.ndarray):
                                data[key] = value.tolist()
                    return fuel_capacity
            else:
                return {}
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {}
    
    def get_relevant_cells_by_technology(self, tech_cells, residual_mwh):
        """Get only the relevant grid cells (cheapest up to residual load)"""
        
        # Sort by LCOE (cheapest first)
        sorted_cells = tech_cells.sort_values('LCOE (USD/MWh)').reset_index(drop=True)
        
        relevant_cells = []
        cumulative_mwh = 0
        
        for _, cell in sorted_cells.iterrows():
            relevant_cells.append(cell)
            if 'Generation (MWh)' in cell:
                cumulative_mwh += cell['Generation (MWh)']
            else:
                # Fallback calculation
                gen_mwh = cell['Installed Capacity Potential (MW)'] * cell['Capacity Factor'] * 8760
                cumulative_mwh += gen_mwh
            
            # Stop when we have enough to meet full residual load
            if cumulative_mwh >= residual_mwh:
                break
        
        return pd.DataFrame(relevant_cells)
    
    def calculate_relevant_resource_targets(self, solar_cells, wind_cells, residual_mwh):
        """Weight by cost and scale of only relevant (economically competitive) cells"""
        
        # Get only relevant cells for each technology
        relevant_solar = self.get_relevant_cells_by_technology(solar_cells, residual_mwh)
        relevant_wind = self.get_relevant_cells_by_technology(wind_cells, residual_mwh)
        
        if relevant_solar.empty and relevant_wind.empty:
            return 0, 0
        elif relevant_solar.empty:
            print(f"   ⚠️ No relevant solar cells, allocating all to wind")
            return 0, residual_mwh
        elif relevant_wind.empty:
            print(f"   ⚠️ No relevant wind cells, allocating all to solar")
            return residual_mwh, 0
        
        # Calculate metrics for relevant cells only
        solar_relevant_potential = relevant_solar['Generation (MWh)'].sum() if 'Generation (MWh)' in relevant_solar.columns else (
            relevant_solar['Installed Capacity Potential (MW)'] * relevant_solar['Capacity Factor'] * 8760
        ).sum()
        
        wind_relevant_potential = relevant_wind['Generation (MWh)'].sum() if 'Generation (MWh)' in relevant_wind.columns else (
            relevant_wind['Installed Capacity Potential (MW)'] * relevant_wind['Capacity Factor'] * 8760
        ).sum()
        
        # Use weighted average LCOE of relevant cells (weighted by generation)
        solar_avg_lcoe = (relevant_solar['LCOE (USD/MWh)'] * relevant_solar.get('Generation (MWh)', 
                         relevant_solar['Installed Capacity Potential (MW)'] * relevant_solar['Capacity Factor'] * 8760)).sum() / solar_relevant_potential
        wind_avg_lcoe = (relevant_wind['LCOE (USD/MWh)'] * relevant_wind.get('Generation (MWh)',
                        relevant_wind['Installed Capacity Potential (MW)'] * relevant_wind['Capacity Factor'] * 8760)).sum() / wind_relevant_potential
        
        # Score = relevant potential (TWh) per unit cost ($/MWh)
        solar_score = (solar_relevant_potential / 1e6) / solar_avg_lcoe  # TWh per $/MWh
        wind_score = (wind_relevant_potential / 1e6) / wind_avg_lcoe
        
        total_score = solar_score + wind_score
        
        # Allocate residual demand proportionally
        solar_target = residual_mwh * (solar_score / total_score)
        wind_target = residual_mwh * (wind_score / total_score)
        
        return solar_target, wind_target
    
    def select_cells_by_technology(self, tech_cells, target_mwh, tech_name):
        """Select cheapest grid cells within a technology to meet target"""
        
        # Sort by LCOE within technology
        sorted_cells = tech_cells.sort_values('LCOE (USD/MWh)').reset_index(drop=True)
        
        selected_cells = []
        cumulative_mwh = 0
        
        for _, cell in sorted_cells.iterrows():
            # Calculate this cell's full generation potential
            if 'Generation (MWh)' in cell:
                cell_full_gen_mwh = cell['Generation (MWh)']
            else:
                # Fallback calculation
                cell_full_gen_mwh = cell['Installed Capacity Potential (MW)'] * cell['Capacity Factor'] * 8760
            
            # Check if we already have enough capacity
            if cumulative_mwh >= target_mwh:
                break
            
            # Calculate remaining capacity needed
            remaining_needed_mwh = target_mwh - cumulative_mwh
            
            # Use minimum of remaining needed and cell's full capacity
            cell_used_gen_mwh = min(remaining_needed_mwh, cell_full_gen_mwh)
            
            # Add this cell to selection with potentially reduced capacity
            cell_dict = cell.to_dict()
            cell_dict['Technology'] = tech_name.lower()
            # Use existing grid_cell_normalized if available, otherwise create normalized version
            if 'grid_cell_normalized' not in cell_dict:
                # Create normalized grid_cell using ISO + id format
                iso_code = cell_dict.get('ISO', '')
                cell_id = cell_dict.get('id', '')
                if iso_code and cell_id:
                    cell_dict['grid_cell_normalized'] = f"{iso_code}_{cell_id}"
                else:
                    cell_dict['grid_cell_normalized'] = cell_dict['grid_cell']
            
            # Override the generation with the capped amount
            cell_dict['Generation (MWh)'] = cell_used_gen_mwh
            
            selected_cells.append(cell_dict)
            cumulative_mwh += cell_used_gen_mwh
            
            # If we've met the target exactly, we're done
            if cumulative_mwh >= target_mwh:
                break
        
        return selected_cells
    
    def select_renewable_grid_cells(self, iso_code, residual_mwh):
        """Select renewable grid cells with balanced solar/wind allocation based on relevant resources"""
        # Load renewable data using unified method
        solar_cells, wind_cells, windoff_cells, original_solar_cells, original_wind_cells = self._load_renewable_data(iso_code, self.force_reload)
        
        if solar_cells.empty and wind_cells.empty:
            return []
        
        # Calculate balanced targets based on relevant resources only
        solar_target_mwh, wind_target_mwh = self.calculate_relevant_resource_targets(
            solar_cells, wind_cells, residual_mwh
        )
        
        selected_cells = []
        
        # Select solar cells to meet solar target
        if solar_target_mwh > 0 and not solar_cells.empty:
            solar_selected = self.select_cells_by_technology(solar_cells, solar_target_mwh, 'solar')
            selected_cells.extend(solar_selected)
        
        # Select wind cells to meet wind target  
        if wind_target_mwh > 0 and not wind_cells.empty:
            wind_selected = self.select_cells_by_technology(wind_cells, wind_target_mwh, 'wind')
            selected_cells.extend(wind_selected)
        
        return selected_cells
    
    def _estimate_lcoe_from_capacity_factor(self, capacity_mw, capacity_factor, technology, discount_rate=0.1):
        """
        Estimate LCOE from capacity factor using technology-specific parameters
        
        Parameters:
        -----------
        capacity_mw : float
            Installed capacity in MW
        capacity_factor : float
            Capacity factor (0-1)
        technology : str
            Technology type ('Solar', 'Wind Onshore', 'Wind Offshore')
        discount_rate : float, default=0.05
            Discount rate for present value calculations
            
        Returns:
        --------
        float: LCOE in $/MWh
        """
        # Technology-specific parameters
        tech_params = {
            'Solar': {
                'capex_per_kw': 1000,  # $/kW
                'om_per_kw_year': 20,   # $/kW/year
                'lifetime_years': 25,
                'decommissioning_rate': 0.05  # 5% of CAPEX
            },
            'Wind Onshore': {
                'capex_per_kw': 1500,
                'om_per_kw_year': 30,
                'lifetime_years': 22,
                'decommissioning_rate': 0.05
            },
            'Wind Offshore': {
                'capex_per_kw': 3500,
                'om_per_kw_year': 80,
                'lifetime_years': 22,
                'decommissioning_rate': 0.05
            }
        }
        
        params = tech_params.get(technology, tech_params['Solar'])
        
        # Calculate costs
        capex = capacity_mw * 1000 * params['capex_per_kw']  # Convert MW to kW
        om_annual = capacity_mw * 1000 * params['om_per_kw_year']
        decommissioning = capex * params['decommissioning_rate']
        
        # Calculate total generation over lifetime
        annual_generation_mwh = capacity_mw * capacity_factor * 8760
        total_generation_mwh = annual_generation_mwh * params['lifetime_years']
        
        # Calculate present value of O&M costs
        om_pv = om_annual * ((1 - (1 + discount_rate)**(-params['lifetime_years'])) / discount_rate)
        
        # Present value of decommissioning cost
        decommissioning_pv = decommissioning / (1 + discount_rate)**params['lifetime_years']
        
        # Total cost
        total_cost = capex + om_pv + decommissioning_pv
        
        # LCOE in $/MWh
        lcoe = total_cost / total_generation_mwh
        
        return lcoe

    def _load_renewable_data(self, iso_code, force_reload=False):
        """Load and combine renewable data - direct approach"""
        # Import the REZoning data function
        sys.path.append('..')
        from iso_processing_functions import get_rezoning_data
        
        print(f"Loading renewable data for {iso_code}...")
        rez_data = get_rezoning_data(iso_code, True, 'all', force_reload=force_reload)
        rez_data_original = get_rezoning_data(iso_code, False, 'all', force_reload=force_reload)
        
        solar_data = rez_data['solar']
        wind_data = rez_data['wind']
        windoff_data = rez_data.get('windoff', pd.DataFrame())

        solar_cells = solar_data[solar_data['ISO'] == iso_code]
        wind_cells = wind_data[wind_data['ISO'] == iso_code]
        windoff_cells = windoff_data[windoff_data['ISO'] == iso_code] if not windoff_data.empty else pd.DataFrame()

        original_solar_cells = rez_data_original['solar']
        original_wind_cells = rez_data_original['wind']

        original_solar_cells = original_solar_cells[original_solar_cells['ISO'] == iso_code]
        original_wind_cells = original_wind_cells[original_wind_cells['ISO'] == iso_code]
                
        return solar_cells, wind_cells, windoff_cells, original_solar_cells, original_wind_cells
    
    def select_cells_by_capacity(self, cells_df, target_capacity_gw, technology='solar'):
        """
        Select grid cells to meet target capacity using merit order (best CF first).
        
        Parameters:
        -----------
        cells_df : pd.DataFrame
            DataFrame with renewable grid cells
        target_capacity_gw : float
            Target capacity in GW
        technology : str
            Technology type ('solar', 'wind', 'windoff')
            
        Returns:
        --------
        dict
            Dictionary with cell_id as keys and cell info (capacity_mw, capacity_factor, utilization_ratio) as values
        """
        if cells_df.empty:
            return {}
        
        # Ensure we have required columns
        required_cols = ['Capacity Factor', 'Installed Capacity Potential (MW)']
        for col in required_cols:
            if col not in cells_df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Filter out cells with very low or zero capacity factors
        cells_filtered = cells_df[cells_df['Capacity Factor'] > 0.001].copy()
        
        if cells_filtered.empty:
            return {}
        
        # Sort by capacity factor (descending - best first)
        cells_sorted = cells_filtered.sort_values('Capacity Factor', ascending=False).copy()
        
        # Convert target to MW
        target_capacity_mw = target_capacity_gw * 1000
        
        # Select cells using merit order
        selected_cells = {}
        cumulative_capacity_mw = 0.0
        
        for idx, row in cells_sorted.iterrows():
            cell_capacity_mw = row['Installed Capacity Potential (MW)']
            cell_cf = row['Capacity Factor']
            
            # Determine cell ID
            if 'grid_cell' in row.index and pd.notna(row['grid_cell']):
                cell_id = str(row['grid_cell'])
            elif 'grid_cell_normalized' in row.index and pd.notna(row['grid_cell_normalized']):
                cell_id = str(row['grid_cell_normalized'])
            elif 'id' in row.index and pd.notna(row['id']):
                cell_id = f"{row.get('ISO', 'UNK')}_{row['id']}"
            else:
                # Fallback: use index
                cell_id = f"{technology}_{idx}"
            
            # Check if we need full cell or partial
            remaining_capacity_mw = target_capacity_mw - cumulative_capacity_mw
            
            if remaining_capacity_mw <= 0:
                # Target already met
                break
            
            if cell_capacity_mw <= remaining_capacity_mw:
                # Use entire cell
                utilization_ratio = 1.0
                cumulative_capacity_mw += cell_capacity_mw
            else:
                # Partial utilization of this cell to exactly meet target
                utilization_ratio = remaining_capacity_mw / cell_capacity_mw
                cumulative_capacity_mw = target_capacity_mw
            
            # Add to selected cells
            selected_cells[cell_id] = {
                'capacity_mw': float(cell_capacity_mw),
                'capacity_factor': float(cell_cf),
                'utilization_ratio': float(utilization_ratio)
            }
            
            # Stop if target is met
            if cumulative_capacity_mw >= target_capacity_mw:
                break
        
        return selected_cells
    
    def generate_hourly_profile_from_cells(self, selected_cells, iso_code, technology):
        """
        Generate 8760-hour generation profile from selected grid cells.
        
        Parameters:
        -----------
        selected_cells : dict
            Output from select_cells_by_capacity()
            Format: {cell_id: {'capacity_mw': float, 'capacity_factor': float, 'utilization_ratio': float}}
        iso_code : str
            ISO country code (e.g., 'DEU', 'USA')
        technology : str
            Technology type ('solar', 'wind', 'windoff')
            
        Returns:
        --------
        list
            8760 generation values in MW (hour 1 to 8760), JSON-safe Python list
            
        Raises:
        -------
        ValueError: If shape data cannot be loaded for requested cells
        """
        if not selected_cells:
            return [0.0] * 8760
        
        # Get shape cache
        from shared_data_loader import get_shape_cache
        shape_cache = get_shape_cache(data_dir=self.data_path)
        
        # Get list of cell IDs
        cell_ids = list(selected_cells.keys())
        
        # Get shapes from cache (incremental loading, raises ValueError if can't load)
        try:
            cell_shapes = shape_cache.get_cell_shapes(iso_code, technology, cell_ids)
        except ValueError as e:
            print(f"❌ Error loading cell shapes: {e}")
            raise ValueError(f"Could not load shape data for {iso_code} {technology}: {e}")
        
        # Initialize total profile
        total_profile = np.zeros(8760)
        cells_processed = 0
        cells_with_invalid_shapes = []
        
        # Aggregate each cell's contribution
        for cell_id, cell_info in selected_cells.items():
            cell_shape = cell_shapes.get(cell_id)
            
            if cell_shape is not None and len(cell_shape) == 8760:
                # Calculate generation: capacity × utilization × hourly_cf
                utilized_capacity_mw = cell_info['capacity_mw'] * cell_info['utilization_ratio']
                cell_generation = utilized_capacity_mw * cell_shape
                total_profile += cell_generation
                cells_processed += 1
            else:
                cells_with_invalid_shapes.append(cell_id)
        
        # Check if we're missing significant number of cells
        if cells_with_invalid_shapes:
            if len(cells_with_invalid_shapes) > len(selected_cells) * 0.1:  # More than 10% missing
                missing_str = ', '.join(cells_with_invalid_shapes[:5]) + ('...' if len(cells_with_invalid_shapes) > 5 else '')
                raise ValueError(f"Invalid or missing shape data for {len(cells_with_invalid_shapes)} cells: {missing_str}")
            else:
                # Minor data quality issue, just warn
                print(f"⚠️  Warning: {len(cells_with_invalid_shapes)} cells have invalid shapes (ignored)")
        
        print(f"✅ Generated profile from {cells_processed}/{len(selected_cells)} cells")
        
        # Verify we got meaningful data
        if cells_processed == 0:
            raise ValueError(f"No valid cell shapes found for {iso_code} {technology}")
        
        # Convert to Python list for JSON safety
        return total_profile.tolist()

    
    def build_renewable_profiles(self, selected_cells):
        """Build hourly renewable generation profiles from selected grid cells"""
        if not selected_cells:
            return np.zeros(8760), np.zeros(8760)
        
        # Use ISO-level shapes for all countries (better data quality and consistency)
        return self._build_profiles_iso_level(selected_cells)
    
    def _build_profiles_iso_level(self, selected_cells):
        """New approach: Use ISO-level shapes for all grid cells (better data quality)"""
        # Load ISO-level shapes data with Atlite fallback (better quality than grid cell level)
        try:
            shapes_df = self.shared_loader.get_atlite_iso_weather_data()
            
            # Check if we actually have data for this ISO
            iso_code = selected_cells[0].get('ISO') if selected_cells else None
            if iso_code and not shapes_df[shapes_df['iso'] == iso_code].empty:
                print("   Using Atlite ISO-level weather data")
            else:
                print(f"   Atlite data loaded but no data for {iso_code}, falling back to Sarah-ERA5")
                shapes_df = self.shared_loader.get_sarah_iso_weather_data()
        except Exception as e:
            print(f"   Failed to load Atlite data ({e}), falling back to Sarah-ERA5")
            shapes_df = self.shared_loader.get_sarah_iso_weather_data()
        
        # Get ISO code from first cell (all cells should be from same ISO)
        iso_code = selected_cells[0].get('ISO') if selected_cells else None
        if not iso_code:
            return np.zeros(8760), np.zeros(8760)
        
        # Get ISO-level shapes (same shape for all cells in this ISO)
        iso_shapes = shapes_df[shapes_df['iso'] == iso_code]
        
        if iso_shapes.empty:
            return np.zeros(8760), np.zeros(8760)
        
        # Sort by month, day, hour to ensure proper 8760 sequence
        iso_shapes = iso_shapes.sort_values(['month', 'day', 'hour']).reset_index(drop=True)
        
        # Handle missing hours by taking first 8760 records
        if len(iso_shapes) < 8760:
            return np.zeros(8760), np.zeros(8760)
        elif len(iso_shapes) > 8760:
            # Take first 8760 records
            iso_shapes = iso_shapes.iloc[:8760].reset_index(drop=True)
        
        # Initialize hourly arrays
        solar_hourly = np.zeros(8760)
        wind_hourly = np.zeros(8760)
        
        # Process each selected grid cell using the SAME ISO-level shape
        successful_matches = 0
        
        for cell in selected_cells:
            # Get annual generation for this cell
            if 'Generation (MWh)' in cell:
                annual_generation_mwh = cell['Generation (MWh)']
            else:
                # Fallback calculation
                annual_generation_mwh = (
                    cell['Installed Capacity Potential (MW)'] * 
                    cell['Capacity Factor'] * 8760
                )
            
            # Apply ISO-level hourly shapes (same shape for all cells)
            technology = cell['Technology']
            
            if technology == 'solar' and 'com_fr_solar' in iso_shapes.columns:
                # Use ISO-level solar shape for this cell
                cell_hourly = annual_generation_mwh * iso_shapes['com_fr_solar'].values
                solar_hourly += cell_hourly
                successful_matches += 1
                
            elif technology == 'wind' and 'com_fr_wind' in iso_shapes.columns:
                # Use ISO-level wind shape for this cell
                cell_hourly = annual_generation_mwh * iso_shapes['com_fr_wind'].values
                wind_hourly += cell_hourly
                successful_matches += 1
                
            else:
                pass
        
        return solar_hourly, wind_hourly
    
    def construct_8760_profiles(self, iso_code, output_dir=None):
        """Main method: construct complete 8760-hour supply and demand profiles"""
        # Step 1: Load demand profile
        demand_hourly = self.load_demand_profile(iso_code)
        annual_demand_mwh = demand_hourly.sum()
        
        # Step 2: Build baseline generation profiles  
        nuclear_hourly, hydro_hourly = self.build_baseline_profiles(iso_code, demand_hourly)
        baseline_mwh = nuclear_hourly.sum() + hydro_hourly.sum()
        
        # Step 3: Calculate residual demand
        residual_mwh = annual_demand_mwh - baseline_mwh
        
        # Step 4: Select renewable grid cells
        selected_cells = self.select_renewable_grid_cells(iso_code, residual_mwh)
        
        # Step 5: Build renewable profiles
        solar_hourly, wind_hourly = self.build_renewable_profiles(selected_cells)
        
        # Step 6: Combine all profiles
        total_supply_hourly = nuclear_hourly + hydro_hourly + solar_hourly + wind_hourly
        net_load_hourly = demand_hourly - total_supply_hourly
        
        # Step 7: Calculate hourly coverage (renewable/demand ratio)
        renewable_hourly = hydro_hourly + solar_hourly + wind_hourly + nuclear_hourly
        coverage_hourly = np.array([
            (renewable_hourly[h] / demand_hourly[h] * 100) if demand_hourly[h] > 0 else 0 
            for h in range(8760)
        ])
        
        return {
            'demand': demand_hourly,
            'nuclear': nuclear_hourly,
            'hydro': hydro_hourly, 
            'solar': solar_hourly,
            'wind': wind_hourly,
            'renewable_total': renewable_hourly,
            'total_supply': total_supply_hourly,
            'net_load': net_load_hourly,
            'coverage': coverage_hourly,
            'selected_cells': selected_cells
        }
    
    def create_quarterly_charts(self, profiles, iso_code, output_path=None, show_chart=True):
        """Create quarterly stacked area charts with supply components + demand line"""
        # Create hourly datetime index
        start_date = datetime(2030, 1, 1)
        hours = [start_date + timedelta(hours=h) for h in range(8760)]
        
        # Define quarters (hour ranges)
        quarters = [
            ("Q1", 0, 2160, "Jan-Mar"),      # Jan 1 - Mar 31 (31+29+31)*24 = 2184 hrs (using 2160 for simplicity)
            ("Q2", 2160, 4344, "Apr-Jun"),   # Apr 1 - Jun 30 (30+31+30)*24 = 2184 hrs
            ("Q3", 4344, 6552, "Jul-Sep"),   # Jul 1 - Sep 30 (31+31+30)*24 = 2208 hrs
            ("Q4", 6552, 8760, "Oct-Dec")    # Oct 1 - Dec 31 (31+30+31)*24 = 2208 hrs
        ]
        
        # Import standard energy sector colors
        from energy_colors import ENERGY_COLORS
        colors = ENERGY_COLORS
        
        supply_components = ['nuclear', 'hydro', 'solar', 'wind']
        
        # Create 2x2 subplot layout
        fig, axes = plt.subplots(2, 2, figsize=(11, 7))
        axes = axes.flatten()
        
        chart_paths = []
        
        for i, (quarter, start_hour, end_hour, months) in enumerate(quarters):
            ax = axes[i]
            
            # Apply branding to this subplot
            self.branding.apply_chart_style(ax, "quarterly_chart")
            
            # Extract quarterly data
            quarter_hours = hours[start_hour:end_hour]
            quarter_length = len(quarter_hours)
            
            # Stack supply components for this quarter
            bottom = np.zeros(quarter_length)
            
            # Plot stacked areas for non-zero components
            for component in supply_components:
                component_data = profiles[component][start_hour:end_hour]
                if component_data.sum() > 0:
                    ax.fill_between(quarter_hours, bottom, bottom + component_data,
                                  alpha=0.8, color=colors[component],
                                  label=f'{component.title()}: {component_data.sum()/1e6:.1f} TWh')
                    bottom += component_data
            
            # Plot demand line (always on top)
            quarter_demand = profiles['demand'][start_hour:end_hour]
            ax.plot(quarter_hours, quarter_demand, color='black', linewidth=1.5,
                   label=f'Demand: {quarter_demand.sum()/1e6:.1f} TWh', zorder=10)
            
            # Calculate quarterly metrics
            quarter_supply = profiles['total_supply'][start_hour:end_hour]
            quarter_net_load = profiles['net_load'][start_hour:end_hour]
            quarter_coverage = (quarter_supply.sum() / quarter_demand.sum() * 100) if quarter_demand.sum() > 0 else 0
            quarter_surplus_hours = (quarter_net_load < 0).sum()
            
            # Formatting for each quarter (branding handles typography)
            ax.set_title(f'{iso_code} {quarter} ({months})', 
                        pad=15)
            ax.set_ylabel('Power (MW)')
            
            # Legend for first quarter only (to avoid clutter)
            if i == 0:
                ax.legend(loc='upper left', framealpha=0.9)
            
            # Grid styling handled by branding
            
            # Format x-axis for readability
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=14))  # Every 2 weeks
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            ax.tick_params(axis='x', rotation=45, labelsize=7)
            
            # Set clean y-axis
            ax.set_ylim(bottom=0)
            max_y = max(quarter_demand.max(), quarter_supply.max()) * 1.05
            ax.set_ylim(top=max_y)
            
            # Add compact info box for each quarter
            info_text = f"""Coverage: {quarter_coverage:.1f}%
Surplus: {quarter_surplus_hours}/{quarter_length} hrs
Peak: {quarter_demand.max():,.0f} MW"""
            
            ax.text(0.98, 0.98, info_text, transform=ax.transAxes,
                   verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))
        
        # Overall title
        total_coverage = (profiles['total_supply'].sum() / profiles['demand'].sum() * 100) if profiles['demand'].sum() > 0 else 0
        fig.suptitle(f'{iso_code} Zero-Emission Profile by Quarter (Annual Coverage: {total_coverage:.1f}%)', 
                    y=0.98)
        
        # Apply figure-level styling
        self.branding.apply_figure_style(fig)
        
        # Finalize chart styling after all elements are set
        for ax in axes.flatten():
            self.branding.finalize_chart_style(ax)
        
        # Add branding logos
        self.branding.add_logos_to_chart(fig, "small", f"Quarterly Supply and Demand Analysis - {self._get_country_name(iso_code)}")
        
        plt.tight_layout()
        plt.savefig(output_path, format='svg', bbox_inches='tight', pad_inches=0.2)
        chart_paths.append(output_path)
        
        if show_chart:
            plt.show()
        else:
            plt.close()
            
        return chart_paths
    

    
    def create_supply_curve_chart(self, iso_code, output_path=None, use_estimated_lcoe=False):
        """Create renewable energy supply curve chart showing both original and landuse-adjusted data
        
        Parameters:
        -----------
        iso_code : str
            ISO country code
        output_path : str, optional
            Path to save the chart
        use_estimated_lcoe : bool, default=False
            If True, estimate LCOE from capacity factor instead of using REZoning LCOE values
        """
        # Load renewable data using unified method
        solar_cells, wind_cells, windoff_cells, original_solar_cells, original_wind_cells = self._load_renewable_data(iso_code, self.force_reload)
        
        # Prepare supply curve data for both original and adjusted versions
        supply_curves = {}
        
        # Process adjusted data
        technologies_adjusted = {}
        if not solar_cells.empty:
            solar_cells['Technology'] = 'Solar'
            solar_cells['Version'] = 'Landuse Adjusted'
            technologies_adjusted['Solar_Adjusted'] = solar_cells
        if not wind_cells.empty:
            wind_cells['Technology'] = 'Wind Onshore'
            wind_cells['Version'] = 'Landuse Adjusted'
            technologies_adjusted['Wind Onshore_Adjusted'] = wind_cells
        if not windoff_cells.empty:
            windoff_cells['Technology'] = 'Wind Offshore'
            windoff_cells['Version'] = 'Adjusted'
            technologies_adjusted['Wind Offshore_Adjusted'] = windoff_cells
        
        # Process original data
        technologies_original = {}
        if not original_solar_cells.empty:
            original_solar_cells['Technology'] = 'Solar'
            original_solar_cells['Version'] = 'Original'
            technologies_original['Solar_Original'] = original_solar_cells
        if not original_wind_cells.empty:
            original_wind_cells['Technology'] = 'Wind Onshore'
            original_wind_cells['Version'] = 'Original'
            technologies_original['Wind Onshore_Original'] = original_wind_cells
        
        # Combine all technologies
        all_technologies = {**technologies_adjusted, **technologies_original}
        
        if not all_technologies:
            return None
        
        # Prepare supply curve data
        for tech_name, df in all_technologies.items():
            if df.empty:
                continue
                
            # Ensure we have the required columns
            required_cols = ['LCOE (USD/MWh)', 'Installed Capacity Potential (MW)']
            if not all(col in df.columns for col in required_cols):
                continue
            
            # Clean and sort by LCOE
            df_clean = df.dropna(subset=required_cols).copy()
            
            # Filter wind technologies to keep top 95% of capacity by CF (for chart readability)
            tech_name = df_clean['Technology'].iloc[0] if not df_clean.empty else ''
            if tech_name in ['Wind Onshore', 'Wind Offshore']:
                # Sort by capacity factor (descending - best first)
                df_sorted = df_clean.sort_values('Capacity Factor', ascending=False).copy()
                
                # Calculate cumulative capacity
                df_sorted['Cumulative_Capacity'] = df_sorted['Installed Capacity Potential (MW)'].cumsum()
                total_capacity = df_sorted['Installed Capacity Potential (MW)'].sum()
                
                # Keep top 95% of capacity (removes bottom 5% of poorest CF cells)
                capacity_95th = total_capacity * 0.95
                df_clean = df_sorted[df_sorted['Cumulative_Capacity'] <= capacity_95th].copy()
                
                # Drop the temporary cumulative column
                df_clean = df_clean.drop('Cumulative_Capacity', axis=1)
            
            # Optionally estimate LCOE from capacity factor
            if use_estimated_lcoe and 'Capacity Factor' in df_clean.columns:
                # Filter out cells with zero or very low capacity factors (can't generate electricity)
                df_clean = df_clean[df_clean['Capacity Factor'] > 0.001].copy()  # Minimum 0.1% capacity factor
                
                if not df_clean.empty:
                    tech_name = df_clean['Technology'].iloc[0]
                    df_clean['LCOE (USD/MWh)'] = df_clean.apply(
                        lambda row: self._estimate_lcoe_from_capacity_factor(
                            row['Installed Capacity Potential (MW)'],
                            row['Capacity Factor'],
                            tech_name
                        ), axis=1
                    )
            
            df_clean = df_clean.sort_values('LCOE (USD/MWh)').reset_index(drop=True)
            
            if df_clean.empty:
                continue
            
            # Calculate cumulative capacity in GW and generation in TWh
            df_clean['Capacity_GW'] = df_clean['Installed Capacity Potential (MW)'] / 1000
            df_clean['Cumulative_GW'] = df_clean['Capacity_GW'].cumsum()
            
            # Calculate generation potential from MW and Atlite capacity factors
            if 'Capacity Factor' in df_clean.columns:
                df_clean['Annual_Generation_TWh'] = df_clean['Installed Capacity Potential (MW)'] * df_clean['Capacity Factor'] * 8760 / 1e6
                df_clean['Cumulative_TWh'] = df_clean['Annual_Generation_TWh'].cumsum()
            else:
                print(f"Warning: No Capacity Factor column found for {tech_name}, skipping generation calculation")
                continue
            
            # Create unique key for each technology-version combination
            version = df_clean['Version'].iloc[0].replace(' ', '_')
            key = f"{tech_name}_{version}"
            supply_curves[key] = df_clean
        
        if not supply_curves:
            return None
        
        # Create stepped line chart with proper spacing from header
        fig = plt.figure(figsize=(11, 7))
        
        # Use GridSpec to control exact positioning and prevent header overlap
        from matplotlib import gridspec
        gs = gridspec.GridSpec(1, 2, figure=fig, 
                              top=0.85, bottom=0.15, left=0.08, right=0.95, 
                              wspace=0.25)
        
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        
        # Apply branding to both subplots
        self.branding.apply_chart_style(ax1, "supply_curve")
        self.branding.apply_chart_style(ax2, "supply_curve")
        
        # Apply figure-level styling
        self.branding.apply_figure_style(fig)
        
        # Import standard energy sector colors
        from energy_colors import ENERGY_COLORS_ALT
        colors = ENERGY_COLORS_ALT
        
        # Define line styles for original vs adjusted
        line_styles = {
            'Original': '--',  # Dashed line
            'Landuse Adjusted': '-'  # Solid line
        }
        
        # Chart 1: LCOE vs Cumulative Capacity (GW)
        for key, df in supply_curves.items():
            if df.empty:
                continue
            
            tech_name = df['Technology'].iloc[0]
            version = df['Version'].iloc[0]
            
            # Create stepped line
            x_capacity = [0] + df['Cumulative_GW'].tolist()
            y_lcoe = [df['LCOE (USD/MWh)'].iloc[0]] + df['LCOE (USD/MWh)'].tolist()
            
            # Use different line styles and colors
            base_color = colors.get(tech_name, '#7F8C8D')
            line_style = line_styles.get(version, '-')
            
            # Adjust alpha for original vs adjusted
            alpha = 0.6 if version == 'Original' else 0.8
            
            # Create compact legend labels
            if version == 'Original':
                label = f'{tech_name} Orig'
            elif version == 'Landuse Adjusted':
                label = f'{tech_name} Adj'
            else:  # Wind Offshore (Adjusted)
                label = f'{tech_name}'  # No "Adj" for offshore wind
            
            ax1.step(x_capacity, y_lcoe, where='post', linewidth=2.5, 
                    color=base_color, linestyle=line_style,
                    label=label, alpha=alpha)
        
        ax1.set_xlabel('Cumulative Capacity (GW)')
        ax1.set_ylabel('LCOE ($/MWh)')
        ax1.set_title(f'{self._get_country_name(iso_code)} Renewable Supply Curve - Capacity')
        ax1.legend(loc='upper right', fontsize=8, framealpha=0.9, ncol=1)
        # Grid styling handled by branding
        
        # Chart 2: LCOE vs Cumulative Generation (TWh)
        for key, df in supply_curves.items():
            if df.empty:
                continue
            
            tech_name = df['Technology'].iloc[0]
            version = df['Version'].iloc[0]
            
            # Create stepped line
            x_generation = [0] + df['Cumulative_TWh'].tolist()
            y_lcoe = [df['LCOE (USD/MWh)'].iloc[0]] + df['LCOE (USD/MWh)'].tolist()
            
            # Use different line styles and colors
            base_color = colors.get(tech_name, '#7F8C8D')
            line_style = line_styles.get(version, '-')
            
            # Adjust alpha for original vs adjusted
            alpha = 0.6 if version == 'Original' else 0.8
            
            # Create compact legend labels (same as above)
            if version == 'Original':
                label = f'{tech_name} Orig'
            elif version == 'Landuse Adjusted':
                label = f'{tech_name} Adj'
            else:  # Wind Offshore (Adjusted)
                label = f'{tech_name}'  # No "Adj" for offshore wind
            
            ax2.step(x_generation, y_lcoe, where='post', linewidth=2.5, 
                    color=base_color, linestyle=line_style,
                    label=label, alpha=alpha)
        
        ax2.set_xlabel('Cumulative Generation Potential (TWh/year)')
        ax2.set_ylabel('LCOE ($/MWh)')
        ax2.set_title(f'{self._get_country_name(iso_code)} Renewable Supply Curve - Generation')
        ax2.legend(loc='upper right', fontsize=8, framealpha=0.9, ncol=1)
        # Grid styling handled by branding
        
        # Finalize chart styling after all elements are set
        self.branding.finalize_chart_style(ax1)
        self.branding.finalize_chart_style(ax2)
        
        # Add branding logos
        self.branding.add_logos_to_chart(fig, "small", f"Supply Curve Analysis - {self._get_country_name(iso_code)}")
        
        plt.tight_layout()
        plt.savefig(output_path, format='svg', bbox_inches='tight', pad_inches=0.2)
        plt.close()
        
        return output_path
    

    
    def generate_profile_and_chart(self, iso_code, show_chart=True):
        """
        One-shot method: ISO input → Chart output
        
        Args:
            iso_code: ISO code (e.g., 'DEU', 'ITA', 'USA')
            show_chart: Whether to display chart (default True)
            
        Returns:
            tuple: (profiles_dict, chart_path)
        """
        # Generate profiles
        profiles = self.construct_8760_profiles(iso_code)
        
        # Create quarterly charts - TEMPORARILY DISABLED
        # chart_paths = self.create_quarterly_charts(profiles, iso_code, show_chart=show_chart)
        chart_paths = []  # Empty list since quarterly charts are disabled
        
        # Create supply curve chart
        supply_curve_path = self.create_supply_curve_chart(iso_code, use_estimated_lcoe=True)
        if supply_curve_path:
            chart_paths.append(supply_curve_path)
        
        return profiles, chart_paths


# Convenience function for direct use
def create_iso_profile_chart(iso_code, data_path="data/", show_chart=True):
    """
    Simple function: ISO → Chart
    
    Usage:
        create_iso_profile_chart("DEU")  # Germany
        create_iso_profile_chart("ITA")  # Italy  
        create_iso_profile_chart("USA")  # United States
    """
    constructor = Supply8760Constructor(data_path)
    return constructor.generate_profile_and_chart(iso_code, show_chart)


def main():
    """Simple usage: ISO → Chart"""
    if len(sys.argv) > 1:
        iso_code = sys.argv[1].upper()
    else:
        iso_code = "DEU"  # Default
    
    # One-shot: ISO → Charts (don't show interactive window)
    profiles, chart_paths = create_iso_profile_chart(iso_code, show_chart=False)


if __name__ == "__main__":
    main()
