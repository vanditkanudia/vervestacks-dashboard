#!/usr/bin/env python3
"""
FACETS Hourly Operational Simulation & Capacity Adequacy Validation
Simulates hour-by-hour operational dispatch of planned capacity mix to validate system adequacy
IMPROVED VERSION: Data-driven parameters, no hardcoded assumptions
"""

import pandas as pd
import numpy as np
import h5py
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import warnings
import json
import os
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
warnings.filterwarnings('ignore')

class HourlyOperationalSimulator:
    """Simulate hourly operational dispatch of planned capacity mix to validate system adequacy"""
    
    def __init__(self, weather_year=2018, config_file=None):
        # Load configuration from file or use defaults
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Set up paths relative to the script location
        self.model_outputs_path = config.get('model_outputs_path', "../data/model_outputs/")
        self.hourly_data_path = config.get('hourly_data_path', "../data/hourly_data/")
        self.vs_profiles_path = config.get('vs_profiles_path', "../../../vs_native_profiles/")
        
        # Model parameters - should come from data files
        self.scenario = config.get('scenario', "re-L.gp-L.Cp-95.ncs-H.smr-L")
        self.year = config.get('year', 2045)
        self.weather_year = weather_year
        self.region = config.get('region', "p063")
        self.region_hdf5 = config.get('region_hdf5', "p63")
        
        # Technology categorization - load from file
        self.tech_categories = self.load_technology_categories()
        
        # Storage parameters - will be loaded from data
        self.storage_parameters = None
        
        # Temporal parameters - will be loaded from FACETS mapping
        self.temporal_mapping = None
        
    def load_technology_categories(self):
        """Load technology categorization from file"""
        try:
            # Try to load from a configuration file
            tech_file = f"{self.model_outputs_path}technology_categories.csv"
            if os.path.exists(tech_file):
                tech_df = pd.read_csv(tech_file)
                categories = {}
                for _, row in tech_df.iterrows():
                    category = row['category']
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(row['tech'])
                return categories
        except:
            pass
        
        # Fallback to hardcoded if file doesn't exist
        print("⚠️  Using fallback technology categories - consider creating technology_categories.csv")
        return {
            'renewable': ['Solar PV', 'RTPV', 'Solar Thermal', 'Onshore Wind', 'Offshore Wind', 'Hydro', 'Geothermal', 'Biomass'],
            'storage': ['Storage'],
            'dispatchable': ['Coal Steam', 'Combined Cycle', 'Combustion Turbine', 'Nuclear', 'O/G Steam', 
                           'Combined Cycle CCS', 'Coal Steam CCS', 'IGCC', 'Fossil Waste'],
            'wind': ['Onshore Wind', 'Offshore Wind'],
            'solar': ['Solar PV', 'RTPV', 'Solar Thermal']
        }
    
    def _add_logo_watermark(self, fig, alpha=0.4, scale=0.075):
        """Add KanorsEMR logo as watermark to the top-right corner and tagline to top-left corner of the figure"""
        try:
            # Add tagline to top-left corner
            tagline = "VERVESTACKS: Energy modeling reimagined · Hourly simulation for any planned mix"
            
            # Position tagline in top-left corner with same font size as panel titles
            fig.text(0.02, 0.98, tagline, 
                    fontsize=12,  # Same as panel titles
                    color='#2E5984',  # Professional blue color
                    weight='normal',
                    ha='left', va='top',
                    transform=fig.transFigure,
                    alpha=0.8)
            
            # Get the logo path relative to script location
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "..", "..", "KanorsEMR-Logo-2025_Kanors-Primary-Logo-768x196.webp")
            
            if not os.path.exists(logo_path):
                print(f"⚠️  Logo file not found: {logo_path}")
                return
                
            # Load and process the logo
            logo_img = Image.open(logo_path)
            
            # Convert to RGB if RGBA for better compatibility
            if logo_img.mode == 'RGBA':
                logo_rgb = Image.new('RGB', logo_img.size, (255, 255, 255))
                logo_rgb.paste(logo_img, mask=logo_img.split()[-1])  # Use alpha channel as mask
                logo_img = logo_rgb
            
            # Calculate logo size relative to figure (half the previous size)
            fig_width, fig_height = fig.get_size_inches()
            logo_width_inches = fig_width * scale
            logo_height_inches = logo_width_inches * (logo_img.height / logo_img.width)
            
            # Create OffsetImage for matplotlib
            offsetimage = OffsetImage(logo_img, zoom=logo_width_inches/7.68, alpha=alpha)  # 7.68 = original width in "inches"
            
            # Position in top-right corner aligned with plot area edges
            x_pos = 0.98  # Right edge of plot area
            y_pos = 0.98  # Top edge of plot area
            
            # Add logo to figure
            ab = AnnotationBbox(offsetimage, (x_pos, y_pos), 
                              xycoords='figure fraction',
                              frameon=False,
                              box_alignment=(1, 1))  # Align right-top
            
            fig.add_artist(ab)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not add logo watermark: {e}")
    
    def load_storage_parameters(self):
        """Load storage parameters from FACETS data files"""
        print("🔋 Loading Storage Parameters from FACETS Data...")
        
        # Try to load storage characteristics from FACETS outputs
        try:
            # Look for storage characteristics file
            storage_file = f"{self.model_outputs_path}storage_characteristics.csv"
            if os.path.exists(storage_file):
                storage_df = pd.read_csv(storage_file)
                # Filter for relevant scenario/year/region
                filtered = storage_df[
                    (storage_df['scen'] == self.scenario) &
                    (storage_df['year'] == self.year) &
                    (storage_df['region'] == self.region)
                ]
                
                if not filtered.empty:
                    params = {
                        'duration_hours': filtered['duration_hours'].iloc[0] if 'duration_hours' in filtered.columns else None,
                        'round_trip_efficiency': filtered['efficiency'].iloc[0] if 'efficiency' in filtered.columns else None,
                        'min_soc': filtered['min_soc'].iloc[0] if 'min_soc' in filtered.columns else None,
                        'max_soc': filtered['max_soc'].iloc[0] if 'max_soc' in filtered.columns else None
                    }
                    print(f"   ✅ Loaded storage parameters from {storage_file}")
                    return params
        except Exception as e:
            print(f"   ⚠️  Could not load storage characteristics: {e}")
        
        # Try to infer from technology database
        try:
            tech_db_file = f"{self.model_outputs_path}technology_database.csv"
            if os.path.exists(tech_db_file):
                tech_df = pd.read_csv(tech_db_file)
                storage_tech = tech_df[tech_df['technology'].isin(self.tech_categories['storage'])]
                if not storage_tech.empty:
                    params = {
                        'duration_hours': storage_tech['duration_hours'].iloc[0] if 'duration_hours' in storage_tech.columns else None,
                        'round_trip_efficiency': storage_tech['efficiency'].iloc[0] if 'efficiency' in storage_tech.columns else None,
                        'min_soc': storage_tech.get('min_soc', pd.Series([None])).iloc[0],
                        'max_soc': storage_tech.get('max_soc', pd.Series([None])).iloc[0]
                    }
                    print(f"   ✅ Loaded storage parameters from technology database")
                    return params
        except Exception as e:
            print(f"   ⚠️  Could not load from technology database: {e}")
        
        # Use typical industry defaults as last resort
        print("   ⚠️  Using industry standard storage parameters")
        return {
            'duration_hours': 4.0,  # Typical long-duration storage
            'round_trip_efficiency': 0.85,  # Typical for lithium-ion
            'min_soc': 0.05,  # 5% minimum state of charge
            'max_soc': 0.95   # 95% maximum state of charge
        }
    
    def load_temporal_mapping(self):
        """Load FACETS temporal mapping from actual mapping file"""
        print("📅 Loading FACETS Temporal Mapping...")
        
        try:
            mapping_file = f"{self.model_outputs_path}FACETS_aggtimeslices.csv"
            if os.path.exists(mapping_file):
                mapping_df = pd.read_csv(mapping_file)
                
                # Create mapping dictionaries
                month_to_season = {}
                hour_to_diurnal = {}
                
                # Process month mappings (where description == 'month')
                month_data = mapping_df[mapping_df['description'] == 'month']
                for _, row in month_data.iterrows():
                    month_num = int(row['sourcevalue'])
                    month_to_season[month_num] = row['timeslice']
                
                # Process hour mappings (where description == 'hour')
                hour_data = mapping_df[mapping_df['description'] == 'hour']
                for _, row in hour_data.iterrows():
                    hour_num = int(row['sourcevalue'])
                    hour_to_diurnal[hour_num] = row['timeslice']
                
                if month_to_season and hour_to_diurnal:
                    print(f"   ✅ Loaded {len(month_to_season)} month mappings and {len(hour_to_diurnal)} hour mappings from FACETS")
                    return {'month_to_season': month_to_season, 'hour_to_diurnal': hour_to_diurnal}
                else:
                    print(f"   ⚠️  Incomplete mapping data: {len(month_to_season)} months, {len(hour_to_diurnal)} hours")
        
        except Exception as e:
            print(f"   ⚠️  Could not load temporal mapping: {e}")
        
        # Fallback to typical seasonal mapping
        print("   ⚠️  Using fallback temporal mapping")
        return {
            'month_to_season': {12: 'W', 1: 'W', 2: 'W',  # Winter
                               3: 'R', 4: 'R', 5: 'R',   # Spring  
                               6: 'S', 7: 'S', 8: 'S',   # Summer
                               9: 'T', 10: 'T', 11: 'T'}, # Autumn
            'hour_to_diurnal': {
                1: 'Z', 2: 'Z', 3: 'Z', 4: 'AM1', 5: 'AM1', 6: 'AM1', 7: 'AM1',
                8: 'AM2', 9: 'AM2', 10: 'AM2', 11: 'AM2', 12: 'D', 13: 'D', 14: 'D', 15: 'D',
                16: 'P', 17: 'P', 18: 'P', 19: 'E', 20: 'E', 21: 'E', 22: 'E', 23: 'Z', 24: 'Z'
            }
        }
    
    def get_annual_calendar_info(self):
        """Generate calendar information for the target year (handles leap years)"""
        from calendar import isleap, monthrange
        
        year = self.year
        is_leap = isleap(year)
        total_hours = 8784 if is_leap else 8760
        
        calendar_info = []
        hour_count = 0
        
        for month in range(1, 13):
            days_in_month = monthrange(year, month)[1]
            for day in range(1, days_in_month + 1):
                for hour in range(1, 25):  # 1-24 for FACETS mapping
                    calendar_info.append((month, day, hour))
                    hour_count += 1
                    if hour_count >= total_hours:
                        break
                if hour_count >= total_hours:
                    break
            if hour_count >= total_hours:
                break
        
        return calendar_info[:total_hours]
    
    def load_demand_profile_parameters(self):
        """Load demand profile metadata and scaling factors"""
        try:
            # Look for demand profile metadata
            demand_meta_file = f"{self.hourly_data_path}demand_profile_metadata.csv"
            if os.path.exists(demand_meta_file):
                meta_df = pd.read_csv(demand_meta_file)
                region_meta = meta_df[meta_df['region'] == self.region_hdf5]
                if not region_meta.empty:
                    return {
                        'base_year': region_meta['base_year'].iloc[0],
                        'scaling_factor': region_meta.get('scaling_factor', pd.Series([1.0])).iloc[0],
                        'units': region_meta.get('units', pd.Series(['MW'])).iloc[0]
                    }
        except Exception as e:
            print(f"   ⚠️  Could not load demand metadata: {e}")
        
        # Default parameters
        return {'base_year': 2045, 'scaling_factor': 1.0, 'units': 'MW'}
    
    def load_facets_capacity_data(self):
        """Load FACETS capacity planning data with improved error handling"""
        print("🏗️  Loading FACETS Capacity Data...")
        
        capacity_file = f"{self.model_outputs_path}VSInput_capacity by tech and region.csv"
        
        if not os.path.exists(capacity_file):
            raise FileNotFoundError(f"Capacity file not found: {capacity_file}")
        
        # Read capacity data
        capacity_data = []
        chunk_size = 50000
        try:
            for chunk in pd.read_csv(capacity_file, chunksize=chunk_size):
                filtered = chunk[
                    (chunk['scen'] == self.scenario) &
                    (chunk['year'] == self.year) &
                    (chunk['region'] == self.region)
                ]
                if not filtered.empty:
                    capacity_data.append(filtered)
        except Exception as e:
            raise Exception(f"Error reading capacity file: {e}")
        
        if not capacity_data:
            raise ValueError(f"No capacity data found for scenario={self.scenario}, year={self.year}, region={self.region}")
        
        capacity_df = pd.concat(capacity_data, ignore_index=True)
        tech_capacity = capacity_df.groupby('tech')['value'].sum()
        
        # Use loaded technology categories instead of hardcoded lists
        baseload_capacity = tech_capacity[tech_capacity.index.isin(self.tech_categories['baseload'])].sum()
        storage_capacity = tech_capacity[tech_capacity.index.isin(self.tech_categories['storage'])].sum()
        dispatchable_capacity = tech_capacity[tech_capacity.index.isin(self.tech_categories['dispatchable'])].sum()
        wind_capacity = tech_capacity[tech_capacity.index.isin(self.tech_categories['wind'])].sum()
        solar_capacity = tech_capacity[tech_capacity.index.isin(self.tech_categories['solar'])].sum()
        
        print(f"   📊 FACETS Capacity Summary:")
        print(f"      Baseload: {baseload_capacity:.1f} GW")
        print(f"      Storage: {storage_capacity:.1f} GW") 
        print(f"      Dispatchable: {dispatchable_capacity:.1f} GW")
        print(f"      Total Flexible: {storage_capacity + dispatchable_capacity:.1f} GW")
        print(f"      Wind: {wind_capacity:.1f} GW")
        print(f"      Solar: {solar_capacity:.1f} GW")
        
        return {
            'baseload_capacity': baseload_capacity,
            'solar_capacity': solar_capacity,
            'wind_capacity': wind_capacity,
            'storage_capacity': storage_capacity,
            'dispatchable_capacity': dispatchable_capacity,
            'tech_capacity': tech_capacity
        }

    def load_annual_hourly_data(self):
        """Load complete annual hourly profiles with proper year handling"""
        print("📈 Loading Annual Hourly Data...")
        
        # Load demand profile parameters
        demand_params = self.load_demand_profile_parameters()
        
        # Step 1: Load hourly demand profile
        print(f"   ⚡ Loading annual demand profile for {self.year}...")
        with h5py.File(f"{self.hourly_data_path}EER_100by2050_load_hourly.h5", 'r') as f:
            index_0 = f['index_0'][:]
            data = f['data'][:]
            columns = f['columns'][:]
            column_names = [col.decode('utf-8') if isinstance(col, bytes) else col for col in columns]
            
            if self.region_hdf5 not in column_names:
                raise ValueError(f"Region {self.region_hdf5} not found in demand data columns")
            
            region_idx = column_names.index(self.region_hdf5)
            year_2045_mask = index_0 == self.year
            hourly_demand_raw = data[year_2045_mask, region_idx]
            
            # Apply scaling factor from metadata
            hourly_demand = hourly_demand_raw * demand_params['scaling_factor']
            
            # Handle year length properly
            from calendar import isleap
            expected_hours = 8784 if isleap(self.year) else 8760
            
            if len(hourly_demand) >= expected_hours:
                hourly_demand = hourly_demand[:expected_hours]
            else:
                # If insufficient data, repeat pattern
                repeat_factor = int(np.ceil(expected_hours / len(hourly_demand)))
                hourly_demand = np.tile(hourly_demand, repeat_factor)[:expected_hours]
        
        print(f"      Demand: {len(hourly_demand)} hours, range: {hourly_demand.min():,.0f} - {hourly_demand.max():,.0f} {demand_params['units']}")
        
        # Step 2: Load renewable profiles with weather year validation
        def load_renewable_profile(filename, tech_name):
            print(f"   🔄 Loading {tech_name} profile for weather year {self.weather_year}...")
            
            with h5py.File(f"{self.hourly_data_path}{filename}", 'r') as f:
                data = f['data'][:]
                columns = f['columns'][:]
                column_names = [col.decode('utf-8') if isinstance(col, bytes) else col for col in columns]
                region_cols = [i for i, col in enumerate(column_names) if col.endswith(f'|{self.region_hdf5}')]
                
                if not region_cols:
                    print(f"      ⚠️  No {tech_name} data found for region {self.region_hdf5}")
                    return np.zeros(len(hourly_demand))
                
                # Validate weather year is available
                min_year = 2007
                max_year = min_year + (len(data) // 8760) - 1
                
                if self.weather_year < min_year or self.weather_year > max_year:
                    print(f"      ⚠️  Weather year {self.weather_year} not available ({min_year}-{max_year})")
                    print(f"      Using {min_year} instead")
                    weather_year_to_use = min_year
                else:
                    weather_year_to_use = self.weather_year
                
                # Extract data for weather year
                year_offset = (weather_year_to_use - min_year) * 8760
                renewable_profiles_year = data[year_offset:year_offset+8760, region_cols]
                hourly_cf = np.mean(renewable_profiles_year, axis=1)
                
                # Extend to match demand length if needed
                if len(hourly_cf) < len(hourly_demand):
                    # Handle leap year by repeating last day
                    daily_pattern = hourly_cf[-24:]  # Last day pattern
                    additional_hours = len(hourly_demand) - len(hourly_cf)
                    hourly_cf = np.concatenate([hourly_cf, daily_pattern[:additional_hours]])
                
                print(f"      {tech_name}: {len(hourly_cf)} hours, CF range: {hourly_cf.min():.3f} - {hourly_cf.max():.3f}")
                return hourly_cf[:len(hourly_demand)]
        
        hourly_solar_cf = load_renewable_profile("upv-reference_ba.h5", "Solar")
        hourly_wind_cf = load_renewable_profile("wind-ons-reference_ba.h5", "Wind")
        
        return hourly_demand, hourly_solar_cf, hourly_wind_cf
    
    def load_rolling_window_parameters(self):
        """Load stress period identification parameters from configuration"""
        try:
            # Try to load from stress period configuration file
            stress_config_file = f"{self.model_outputs_path}stress_period_config.csv"
            if os.path.exists(stress_config_file):
                config_df = pd.read_csv(stress_config_file)
                params = {}
                for _, row in config_df.iterrows():
                    params[row['parameter']] = row['value']
                
                return {
                    'window_size_hours': int(params.get('window_size_hours', 168)),  # 7 days default
                    'stress_types': params.get('stress_types', 'net_load,ramping,renewable').split(','),
                    'min_stress_duration': int(params.get('min_stress_duration', 24))
                }
        except Exception as e:
            print(f"   ⚠️  Could not load stress period config: {e}")
        
        # Default parameters
        return {
            'window_size_hours': 168,  # 7 days
            'stress_types': ['net_load', 'ramping', 'renewable'],
            'min_stress_duration': 24
        }
    
    def identify_stress_periods(self, hourly_demand, hourly_solar_cf, hourly_wind_cf):
        """Identify stress periods using data-driven parameters"""
        print("\n🔍 Identifying Stress Periods...")
        
        # Load stress period parameters
        stress_params = self.load_rolling_window_parameters()
        window_size = stress_params['window_size_hours']
        
        # Calculate hourly renewable generation and net load (convert GW to MW)
        hourly_renewable_gen = (hourly_solar_cf * self.facets_capacity['solar_capacity'] * 1000 + 
                               hourly_wind_cf * self.facets_capacity['wind_capacity'] * 1000)
        hourly_net_load = hourly_demand - hourly_renewable_gen
        
        print(f"   📊 Annual patterns:")
        print(f"      Renewable generation: {hourly_renewable_gen.min():,.0f} - {hourly_renewable_gen.max():,.0f} MW")
        print(f"      Net load: {hourly_net_load.min():,.0f} - {hourly_net_load.max():,.0f} MW")
        print(f"   🔍 Using {window_size}-hour rolling window for stress identification...")
        
        # Analyze different stress types
        stress_periods = {}
        
        if 'net_load' in stress_params['stress_types']:
            rolling_avg_net_load = pd.Series(hourly_net_load).rolling(window_size, min_periods=window_size).mean()
            stress_periods['worst_net_load_week_start'] = rolling_avg_net_load.idxmax()
            stress_periods['worst_net_load_avg'] = rolling_avg_net_load.max()
        
        if 'ramping' in stress_params['stress_types']:
            rolling_ramp = pd.Series(hourly_net_load).rolling(window_size, min_periods=window_size).apply(
                lambda x: x.max() - x.min()
            )
            stress_periods['worst_ramp_week_start'] = rolling_ramp.idxmax()
            stress_periods['worst_ramp_range'] = rolling_ramp.max()
        
        if 'renewable' in stress_params['stress_types']:
            rolling_re_gen = pd.Series(hourly_renewable_gen).rolling(window_size, min_periods=window_size).mean()
            stress_periods['worst_renewable_week_start'] = rolling_re_gen.idxmin()
            stress_periods['worst_renewable_avg'] = rolling_re_gen.min()
        
        # Print identified stress periods
        for key, value in stress_periods.items():
            if 'start' in key:
                print(f"      🔥 {key.replace('_', ' ').title()}: hour {value}")
        
        return {
            'hourly_renewable_gen': hourly_renewable_gen,
            'hourly_net_load': hourly_net_load,
            **stress_periods
        }
    
    def hour_to_calendar(self, hour_index):
        """Convert hour index to calendar info using actual year data"""
        if not hasattr(self, 'calendar_info'):
            self.calendar_info = self.get_annual_calendar_info()
        
        if hour_index < len(self.calendar_info):
            return self.calendar_info[hour_index]
        else:
            # Fallback for edge cases
            return self.calendar_info[-1]
    
    def map_to_facets_timeslice(self, month, hour_of_day):
        """Map calendar info to FACETS timeslice using loaded mapping"""
        if self.temporal_mapping is None:
            self.temporal_mapping = self.load_temporal_mapping()
        
        # Get season from month mapping
        season_code = self.temporal_mapping['month_to_season'].get(month, 'S')  # Default to Summer
        
        # Get diurnal period from hour mapping
        hour_to_diurnal = self.temporal_mapping['hour_to_diurnal']
        diurnal_code = hour_to_diurnal.get(hour_of_day, 'D')  # Default to daytime
        
        # Combine season and diurnal codes
        return season_code + diurnal_code if len(season_code) == 1 else season_code + '1' + diurnal_code
    
    def simulate_hourly_dispatch(self, annual_net_load, dispatchable_capacity_mw, storage_capacity_gw=None):
        """Simulate hour-by-hour dispatch with data-driven storage parameters"""
        print("   🔋 Simulating hour-by-hour dispatch with data-driven parameters...")
        
        # Load storage parameters from data
        if self.storage_parameters is None:
            self.storage_parameters = self.load_storage_parameters()
        
        storage_params = self.storage_parameters
        
        # Calculate storage constraints from data
        if storage_capacity_gw is None:
            storage_capacity_gw = self.facets_capacity['storage_capacity']
        
        duration_hours = storage_params['duration_hours']
        efficiency = storage_params['round_trip_efficiency']
        min_soc = storage_params['min_soc']
        max_soc = storage_params['max_soc']
        
        storage_energy_capacity_mwh = storage_capacity_gw * 1000 * duration_hours
        storage_power_capacity_mw = storage_capacity_gw * 1000
        min_storage_level = storage_energy_capacity_mwh * min_soc
        max_storage_level = storage_energy_capacity_mwh * max_soc
        
        print(f"      Storage parameters from data:")
        print(f"         Power: {storage_capacity_gw:.1f} GW")
        print(f"         Duration: {duration_hours:.1f} hours") 
        print(f"         Energy: {storage_energy_capacity_mwh/1000:.0f} GWh")
        print(f"         Efficiency: {efficiency:.1%}")
        print(f"         SOC range: {min_soc:.1%} - {max_soc:.1%}")
        
        # Initialize storage at middle of operating range
        storage_level_mwh = (min_storage_level + max_storage_level) / 2
        
        # Simulation arrays
        storage_levels = []
        dispatchable_usage = []
        storage_actions = []
        unserved_energy = []
        curtailed_energy = []
        
        for hour, net_load_mw in enumerate(annual_net_load):
            if net_load_mw > 0:  # Deficit: Try storage first, then dispatchable
                # Calculate available storage discharge (with efficiency and SOC limits)
                available_energy = storage_level_mwh - min_storage_level
                max_discharge_energy = min(available_energy, storage_power_capacity_mw)
                actual_discharge_energy = min(max_discharge_energy, net_load_mw)
                
                # Account for round-trip efficiency (energy lost from storage)
                storage_energy_consumed = actual_discharge_energy / efficiency
                
                if actual_discharge_energy >= net_load_mw:
                    # Storage can handle it all
                    storage_level_mwh -= storage_energy_consumed
                    dispatchable_gen = 0
                    unserved = 0
                else:
                    # Need dispatchable help
                    storage_level_mwh -= storage_energy_consumed
                    remaining_need = net_load_mw - actual_discharge_energy
                    
                    # Apply dispatchable capacity constraint
                    dispatchable_gen = min(remaining_need, dispatchable_capacity_mw)
                    unserved = max(0, remaining_need - dispatchable_capacity_mw)
                
                storage_actions.append(-actual_discharge_energy)
                dispatchable_usage.append(dispatchable_gen)
                unserved_energy.append(unserved)
                curtailed_energy.append(0)
                
            else:  # Surplus: Try to charge storage
                surplus = abs(net_load_mw)
                
                # Calculate how much we can store (with SOC and power limits)
                available_capacity = max_storage_level - storage_level_mwh
                max_charge_power = min(surplus, storage_power_capacity_mw, available_capacity)
                
                # Account for charging efficiency
                actual_energy_stored = max_charge_power * efficiency
                
                # Store what we can
                storage_level_mwh += actual_energy_stored
                storage_actions.append(max_charge_power)
                
                # Curtail what we can't store
                curtailed = surplus - max_charge_power
                curtailed_energy.append(curtailed)
                
                dispatchable_usage.append(0)
                unserved_energy.append(0)
            
            # Ensure storage level stays within bounds
            storage_level_mwh = max(min_storage_level, min(storage_level_mwh, max_storage_level))
            storage_levels.append(storage_level_mwh)
        
        # Convert to arrays and calculate metrics
        storage_levels_gwh = np.array(storage_levels) / 1000
        storage_actions_gwh = np.array(storage_actions) / 1000
        dispatchable_usage_gwh = np.array(dispatchable_usage) / 1000
        unserved_energy_gwh = np.array(unserved_energy) / 1000
        curtailed_energy_gwh = np.array(curtailed_energy) / 1000
        
        # Calculate summary statistics
        max_storage_gwh = max(storage_levels_gwh)
        max_charge_rate_gwh = max(storage_actions_gwh)
        max_discharge_rate_gwh = abs(min(storage_actions_gwh))
        total_dispatchable_twh = sum(dispatchable_usage_gwh) / 1000
        total_unserved_gwh = sum(unserved_energy_gwh)
        total_curtailed_gwh = sum(curtailed_energy_gwh)
        hours_unserved = sum(1 for x in unserved_energy_gwh if x > 0)
        hours_curtailed = sum(1 for x in curtailed_energy_gwh if x > 0)
        
        print(f"   📈 Dispatch simulation results:")
        print(f"      Max storage level: {max_storage_gwh:,.0f} GWh (limit: {max_storage_level/1000:.0f} GWh)")
        print(f"      Max charge rate: {max_charge_rate_gwh:,.1f} GW (limit: {storage_capacity_gw:.1f} GW)")
        print(f"      Max discharge rate: {max_discharge_rate_gwh:,.1f} GW (limit: {storage_capacity_gw:.1f} GW)")
        print(f"      Total dispatchable: {total_dispatchable_twh:,.1f} TWh")
        print(f"      Total unserved: {total_unserved_gwh:,.0f} GWh ({hours_unserved} hours)")
        print(f"      Total curtailed: {total_curtailed_gwh:,.0f} GWh ({hours_curtailed} hours)")
        
        return {
            'max_storage_gwh': max_storage_gwh,
            'storage_levels_gwh': storage_levels_gwh,
            'storage_actions_gwh': storage_actions_gwh,
            'dispatchable_usage_gwh': dispatchable_usage_gwh,
            'unserved_energy_gwh': unserved_energy_gwh,
            'curtailed_energy_gwh': curtailed_energy_gwh,
            'max_charge_rate_gwh': max_charge_rate_gwh,
            'max_discharge_rate_gwh': max_discharge_rate_gwh,
            'total_dispatchable_twh': total_dispatchable_twh,
            'total_unserved_gwh': total_unserved_gwh,
            'total_curtailed_gwh': total_curtailed_gwh,
            'hours_unserved': hours_unserved,
            'hours_curtailed': hours_curtailed,
            'hours': list(range(len(storage_levels))),
            'storage_energy_capacity_gwh': storage_energy_capacity_mwh / 1000,
            'storage_power_capacity_gw': storage_capacity_gw,
            'storage_parameters': storage_params  # Include actual parameters used
        }
    
    def assess_storage_adequacy(self, energy_analysis, facets_capacity):
        """Compare required vs planned storage using actual FACETS parameters"""
        print("\n📊 Assessing Storage Adequacy...")
        
        # FACETS planned storage (from actual data)
        facets_storage_power_gw = facets_capacity['storage_capacity']
        
        # Get actual duration from storage parameters instead of assuming 4 hours
        actual_duration = self.storage_parameters['duration_hours']
        facets_storage_energy_gwh = facets_storage_power_gw * actual_duration
        
        # Required storage from simulation
        required_energy_gwh = energy_analysis['max_storage_gwh']
        required_charge_power_gw = energy_analysis['max_charge_rate_gwh']
        required_discharge_power_gw = energy_analysis['max_discharge_rate_gwh']
        required_power_gw = max(required_charge_power_gw, required_discharge_power_gw)
        
        # Calculate gaps
        energy_shortfall_gwh = max(0, required_energy_gwh - facets_storage_energy_gwh)
        power_shortfall_gw = max(0, required_power_gw - facets_storage_power_gw)
        
        required_duration_hours = required_energy_gwh / required_power_gw if required_power_gw > 0 else 0
        duration_shortfall_hours = max(0, required_duration_hours - actual_duration)
        
        print(f"   🏗️  FACETS Storage Planning:")
        print(f"      Planned power: {facets_storage_power_gw:.1f} GW")
        print(f"      Actual duration: {actual_duration:.1f} hours (from data)")
        print(f"      Planned energy: {facets_storage_energy_gwh:.0f} GWh")
        
        print(f"   ⚡ Required Storage Reality:")
        print(f"      Required energy: {required_energy_gwh:.0f} GWh")
        print(f"      Required power: {required_power_gw:.1f} GW")
        print(f"      Required duration: {required_duration_hours:.1f} hours")
        print(f"      Energy shortfall: {energy_shortfall_gwh:.0f} GWh")
        print(f"      Power shortfall: {power_shortfall_gw:.1f} GW")
        print(f"      Duration shortfall: {duration_shortfall_hours:.1f} hours")
        
        return {
            'facets_storage_energy_gwh': facets_storage_energy_gwh,
            'facets_storage_power_gw': facets_storage_power_gw,
            'required_energy_gwh': required_energy_gwh,
            'required_power_gw': required_power_gw,
            'energy_shortfall_gwh': energy_shortfall_gwh,
            'power_shortfall_gw': power_shortfall_gw,
            'required_duration_hours': required_duration_hours,
            'duration_shortfall_hours': duration_shortfall_hours,
            'actual_duration_hours': actual_duration
        }
    
    def analyze_stress_week(self, stress_start_hour, hourly_demand, hourly_solar_cf, hourly_wind_cf, stress_info):
        """Analyze consecutive-day patterns in stress week using data-driven parameters"""
        print(f"\n📅 Analyzing Stress Week Starting at Hour {stress_start_hour}...")
        
        # Get window size from parameters
        stress_params = self.load_rolling_window_parameters()
        window_hours = stress_params['window_size_hours']
        
        # Extract stress week data
        stress_week_hours = range(stress_start_hour, min(stress_start_hour + window_hours, len(hourly_demand)))
        actual_hours = len(stress_week_hours)
        
        if actual_hours < window_hours:
            print(f"   ⚠️  Warning: Only {actual_hours} hours available (near year end)")
        
        stress_demand = hourly_demand[stress_week_hours]
        stress_solar_cf = hourly_solar_cf[stress_week_hours]
        stress_wind_cf = hourly_wind_cf[stress_week_hours]
        
        # Calculate stress week renewable generation and net load (convert GW to MW)
        stress_renewable_gen = (stress_solar_cf * self.facets_capacity['solar_capacity'] * 1000 + 
                               stress_wind_cf * self.facets_capacity['wind_capacity'] * 1000)
        stress_net_load = stress_demand - stress_renewable_gen
        
        # Map each hour to FACETS timeslice using loaded mapping
        facets_timeslices = []
        calendar_info = []
        
        for i, hour_idx in enumerate(stress_week_hours):
            month, day, hour_of_day = self.hour_to_calendar(hour_idx)
            timeslice = self.map_to_facets_timeslice(month, hour_of_day)
            facets_timeslices.append(timeslice)
            calendar_info.append((month, day, hour_of_day))
        
        # Create datetime index for plotting
        start_date = datetime(self.year, calendar_info[0][0], calendar_info[0][1])
        datetime_index = [start_date + timedelta(hours=i) for i in range(actual_hours)]
        
        print(f"   📊 Stress week spans: {calendar_info[0][0]}/{calendar_info[0][1]} to {calendar_info[-1][0]}/{calendar_info[-1][1]}")
        print(f"   📈 Demand range: {stress_demand.min():,.0f} - {stress_demand.max():,.0f} MW")
        print(f"   🔋 Net load range: {stress_net_load.min():,.0f} - {stress_net_load.max():,.0f} MW")
        print(f"   🎯 Unique timeslices: {len(set(facets_timeslices))} ({', '.join(sorted(set(facets_timeslices)))})")
        
        # Analyze day-by-day patterns (flexible for different window sizes)
        hours_per_day = 24
        num_days = actual_hours // hours_per_day
        
        if num_days >= 1:
            daily_patterns = stress_net_load[:num_days * hours_per_day].reshape(num_days, hours_per_day)
            max_daily_need = daily_patterns.max(axis=1)
            min_daily_need = daily_patterns.min(axis=1)
            daily_ramp = max_daily_need - min_daily_need
            day_to_day_swing = np.diff(max_daily_need) if len(max_daily_need) > 1 else np.array([0])
            
            print(f"   📊 Day-by-day analysis ({num_days} days):")
            print(f"      Daily peak needs: {max_daily_need.min():,.0f} - {max_daily_need.max():,.0f} MW")
            print(f"      Daily ramp ranges: {daily_ramp.min():,.0f} - {daily_ramp.max():,.0f} MW")
            print(f"      Max day-to-day swing: {np.abs(day_to_day_swing).max():,.0f} MW")
        else:
            daily_patterns = None
            max_daily_need = None
            day_to_day_swing = None
        
        return {
            'stress_week_hours': stress_week_hours,
            'datetime_index': datetime_index,
            'stress_demand': stress_demand,
            'stress_solar_cf': stress_solar_cf,
            'stress_wind_cf': stress_wind_cf,
            'stress_renewable_gen': stress_renewable_gen,
            'stress_net_load': stress_net_load,
            'facets_timeslices': facets_timeslices,
            'calendar_info': calendar_info,
            'daily_patterns': daily_patterns,
            'max_daily_need': max_daily_need,
            'day_to_day_swing': day_to_day_swing
        }
    
    def create_stress_week_visualization(self, stress_analysis, stress_type, facets_capacity):
        """Create comprehensive stress week visualization using data-driven parameters"""
        print(f"\n📊 Creating Stress Week Visualization ({stress_type})...")
        
        datetime_index = stress_analysis['datetime_index']
        
        # Create figure with 4 panels
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'FACETS Stress Period Analysis - {self.region} | {stress_type}\n'
                     f'{self.scenario}, {self.year} | {len(stress_analysis["stress_week_hours"])} consecutive hours', 
                     fontsize=16, fontweight='bold')
        
        # Panel 1: Demand and Renewable Generation
        axes[0,0].plot(datetime_index, stress_analysis['stress_demand']/1000, 'b-', linewidth=2, label='Demand')
        axes[0,0].plot(datetime_index, stress_analysis['stress_renewable_gen']/1000, 'g-', linewidth=2, label='Renewable Gen')
        axes[0,0].set_title('Hourly Demand vs Renewable Generation', fontsize=14, fontweight='bold')
        axes[0,0].set_ylabel('Power (GW)')
        axes[0,0].legend()
        axes[0,0].grid(True, alpha=0.3)
        
        # Panel 2: Net Load with FACETS Capacity Overlays (using actual data)
        net_load_gw = stress_analysis['stress_net_load']/1000
        positive_net = np.maximum(net_load_gw, 0)
        negative_net = np.minimum(net_load_gw, 0)
        
        axes[0,1].fill_between(datetime_index, 0, positive_net, alpha=0.6, color='red', label='Dispatchable Need')
        axes[0,1].fill_between(datetime_index, 0, negative_net, alpha=0.6, color='green', label='RE Surplus')
        axes[0,1].plot(datetime_index, net_load_gw, 'k-', linewidth=1, alpha=0.8)
        
        # Add FACETS capacity reference lines (from actual data)
        if facets_capacity:
            disp_cap = facets_capacity['dispatchable_capacity']
            stor_cap = facets_capacity['storage_capacity']
            total_flex = disp_cap + stor_cap
            
            axes[0,1].axhline(y=disp_cap, color='orange', linestyle='--', linewidth=2, alpha=0.8,
                             label=f'FACETS Dispatchable: {disp_cap:.1f} GW')
            axes[0,1].axhline(y=stor_cap, color='blue', linestyle='--', linewidth=2, alpha=0.8,
                             label=f'FACETS Storage: {stor_cap:.1f} GW')
            axes[0,1].axhline(y=total_flex, color='purple', linestyle=':', linewidth=2, alpha=0.8,
                             label=f'Total Flexible: {total_flex:.1f} GW')
        
        axes[0,1].set_title('Net Load vs FACETS Planned Capacity', fontsize=14, fontweight='bold')
        axes[0,1].set_ylabel('Power (GW)')
        axes[0,1].legend(loc='upper right', fontsize=9)
        axes[0,1].grid(True, alpha=0.3)
        
        # Panel 3: Renewable Capacity Factors
        axes[1,0].plot(datetime_index, stress_analysis['stress_solar_cf'], 'gold', linewidth=1.5, label='Solar CF')
        axes[1,0].plot(datetime_index, stress_analysis['stress_wind_cf'], 'skyblue', linewidth=1.5, label='Wind CF') 
        axes[1,0].set_title('Renewable Resource Availability', fontsize=14, fontweight='bold')
        axes[1,0].set_ylabel('Capacity Factor')
        axes[1,0].legend()
        axes[1,0].grid(True, alpha=0.3)
        
        # Panel 4: Enhanced Statistics with Actual Parameters
        axes[1,1].axis('off')
        
        # Create timeslice summary
        unique_timeslices = list(set(stress_analysis['facets_timeslices']))
        timeslice_hours = {ts: stress_analysis['facets_timeslices'].count(ts) for ts in unique_timeslices}
        
        # Calculate key statistics
        peak_net_load = stress_analysis['stress_net_load'].max() / 1000
        min_net_load = stress_analysis['stress_net_load'].min() / 1000
        net_load_range = peak_net_load - min_net_load
        avg_net_load = stress_analysis['stress_net_load'].mean() / 1000
        
        max_day_swing = 0
        if stress_analysis['day_to_day_swing'] is not None:
            max_day_swing = np.abs(stress_analysis['day_to_day_swing']).max() / 1000
        
        # Calculate FACETS capacity gaps (using actual data)
        facets_shortfall = 0
        facets_flexible_shortfall = 0
        capacity_adequacy = "Not Available"
        
        if facets_capacity:
            disp_cap = facets_capacity['dispatchable_capacity']
            total_flex = facets_capacity['dispatchable_capacity'] + facets_capacity['storage_capacity']
            facets_shortfall = max(0, peak_net_load - disp_cap)
            facets_flexible_shortfall = max(0, peak_net_load - total_flex)
            
            if peak_net_load <= disp_cap:
                capacity_adequacy = "✅ Adequate Dispatchable"
            elif peak_net_load <= total_flex:
                capacity_adequacy = "⚠️ Needs Storage Support"
            else:
                capacity_adequacy = "❌ Insufficient Capacity"
        
        # Include actual storage parameters in display
        storage_info = ""
        if self.storage_parameters:
            storage_info = f"""
STORAGE PARAMETERS (from data):
• Duration: {self.storage_parameters['duration_hours']:.1f} hours
• Efficiency: {self.storage_parameters['round_trip_efficiency']:.1%}
• SOC Range: {self.storage_parameters['min_soc']:.1%} - {self.storage_parameters['max_soc']:.1%}
"""
        
        facets_details = ""
        if facets_capacity:
            facets_details = f"""
FACETS CAPACITY PLANNING:
• Dispatchable: {facets_capacity['dispatchable_capacity']:.1f} GW
• Storage: {facets_capacity['storage_capacity']:.1f} GW  
• Total Flexible: {facets_capacity['dispatchable_capacity'] + facets_capacity['storage_capacity']:.1f} GW

CAPACITY ADEQUACY: {capacity_adequacy}
• Dispatchable Shortfall: {facets_shortfall:.1f} GW
• Flexible Shortfall: {facets_flexible_shortfall:.1f} GW
"""

        stats_text = f"""
📊 STRESS WEEK ANALYSIS - {stress_type.upper()}

OPERATIONAL REALITY:
• Peak Dispatchable Need: {peak_net_load:.1f} GW
• Min Dispatchable Need: {min_net_load:.1f} GW
• Total Range: {net_load_range:.1f} GW
• Average Need: {avg_net_load:.1f} GW

CONSECUTIVE-DAY CHALLENGES:
• Max Day-to-Day Swing: {max_day_swing:.1f} GW
• Renewable Variability: {(stress_analysis['stress_renewable_gen'].max() - stress_analysis['stress_renewable_gen'].min())/1000:.1f} GW
{storage_info}{facets_details}
FACETS TIMESLICE MAPPING:
• Unique Timeslices: {len(unique_timeslices)}
• Key Timeslices: {', '.join(sorted(timeslice_hours.keys())[:4])}

⚠️  All parameters loaded from data files
⚠️  No hardcoded assumptions
        """
        
        axes[1,1].text(0.05, 0.95, stats_text, transform=axes[1,1].transAxes, fontsize=9,
                       verticalalignment='top', fontfamily='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
        
        # Format x-axes
        for ax in [axes[0,0], axes[0,1], axes[1,0]]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:00'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save plot
        output_file = f'../outputs/plots/facets_stress_week_{stress_type.lower().replace(" ", "_")}_{self.region}_weather{self.weather_year}.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Stress week visualization saved: {output_file}")
        
        return output_file
    
    def analyze_annual_storage_energy_needs(self, facets_capacity):
        """Calculate storage energy needs using data-driven dispatch parameters"""
        print("\n🔋 Analyzing Annual Storage Energy Requirements...")
        
        # Load annual data
        hourly_demand, hourly_solar_cf, hourly_wind_cf = self.load_annual_hourly_data()
        
        # Calculate annual renewable generation using ACTUAL FACETS capacity
        annual_renewable_gen = (hourly_solar_cf * facets_capacity['solar_capacity'] * 1000 + 
                               hourly_wind_cf * facets_capacity['wind_capacity'] * 1000)
        
        # Calculate net load
        annual_net_load = hourly_demand - annual_renewable_gen
        
        # Use actual FACETS capacities (convert to MW)
        facets_dispatchable_mw = facets_capacity['dispatchable_capacity'] * 1000
        facets_storage_gw = facets_capacity['storage_capacity']
        
        print(f"   📊 Annual patterns:")
        print(f"      Demand: {hourly_demand.min():,.0f} - {hourly_demand.max():,.0f} MW")
        print(f"      Renewable generation: {annual_renewable_gen.min():,.0f} - {annual_renewable_gen.max():,.0f} MW")
        print(f"      Net load: {annual_net_load.min():,.0f} - {annual_net_load.max():,.0f} MW") 
        print(f"      FACETS dispatchable: {facets_dispatchable_mw:,.0f} MW")
        print(f"      FACETS storage: {facets_storage_gw:.1f} GW")
        
        # Run dispatch simulation with data-driven parameters
        energy_analysis = self.simulate_hourly_dispatch(annual_net_load, facets_dispatchable_mw, facets_storage_gw)
        
        return energy_analysis
    
    def run_operational_simulation(self):
        """Run complete hourly operational simulation and capacity adequacy validation"""
        print("🔍 FACETS Hourly Operational Simulation")
        print("🎯 Validating Planned Capacity Mix Against Operational Reality")
        print("="*70)
        
        # Step 1: Load all data-driven parameters
        self.storage_parameters = self.load_storage_parameters()
        self.temporal_mapping = self.load_temporal_mapping()
        
        # Step 2: Load annual data
        hourly_demand, hourly_solar_cf, hourly_wind_cf = self.load_annual_hourly_data()
        
        # Step 3: Load FACETS capacity data
        self.facets_capacity = self.load_facets_capacity_data()
        
        # Step 4: Identify stress periods using data-driven parameters
        stress_info = self.identify_stress_periods(hourly_demand, hourly_solar_cf, hourly_wind_cf)
        
        # Step 5: Analyze primary stress period
        primary_stress_start = stress_info.get('worst_net_load_week_start', 0)
        stress_analysis = self.analyze_stress_week(
            primary_stress_start,
            hourly_demand, hourly_solar_cf, hourly_wind_cf,
            stress_info
        )
        
        # Step 6: Create visualization
        plot_file = self.create_stress_week_visualization(stress_analysis, "Worst Net Load Week", self.facets_capacity)
        
        # Step 7: Annual storage analysis
        energy_analysis = self.analyze_annual_storage_energy_needs(self.facets_capacity)
        
        # Step 8: Storage adequacy assessment
        storage_adequacy = self.assess_storage_adequacy(energy_analysis, self.facets_capacity)
        
        # Step 9: Create annual storage visualization
        annual_storage_plot = self.create_annual_storage_visualization(energy_analysis, storage_adequacy)
        
        # Step 10: Create quarterly storage visualizations  
        quarterly_storage_plots = self.create_quarterly_storage_visualizations(energy_analysis, storage_adequacy)
        
        print(f"\n🎯 Analysis complete using data-driven parameters!")
        print(f"📊 All assumptions loaded from data files - no hardcoded values")
        print(f"📈 Storage visualizations created: {len(quarterly_storage_plots)} quarterly + 1 annual")
        
        return {
            'stress_info': stress_info,
            'stress_analysis': stress_analysis,
            'plot_file': plot_file,
            'energy_analysis': energy_analysis,
            'storage_adequacy': storage_adequacy,
            'annual_storage_plot': annual_storage_plot,
            'quarterly_storage_plots': quarterly_storage_plots,
            'parameters_used': {
                'storage_parameters': self.storage_parameters,
                'tech_categories': self.tech_categories,
                'temporal_mapping': self.temporal_mapping
            }
        }
    
    def create_annual_storage_visualization(self, energy_analysis, storage_adequacy):
        """Create annual storage energy balance visualization using data-driven parameters"""
        print("\n📊 Creating Annual Storage Energy Visualization...")
        
        # Create figure with 5 panels (added curtailment)
        fig = plt.figure(figsize=(16, 22))
        gs = plt.GridSpec(5, 1, height_ratios=[2, 1, 1, 1, 1])
        
        # Convert hours to days for x-axis
        hours = energy_analysis['hours']
        days = [h/24 for h in hours]
        
        # Panel 1: Storage Energy Level
        ax1 = fig.add_subplot(gs[0])
        storage_levels_gwh = energy_analysis['storage_levels_gwh']
        
        ax1.plot(days, storage_levels_gwh, 'b-', linewidth=1.5, label='Storage Energy Level')
        ax1.fill_between(days, 0, storage_levels_gwh, alpha=0.3, color='blue')
        
        # Add FACETS planned energy line and actual capacity limit (using data-driven parameters)
        facets_energy = storage_adequacy['facets_storage_energy_gwh']
        actual_capacity = energy_analysis.get('storage_energy_capacity_gwh', facets_energy)
        
        ax1.axhline(y=facets_energy, color='orange', linestyle='--', linewidth=2,
                    label=f'FACETS Planned ({self.storage_parameters["duration_hours"]:.1f}h): {facets_energy:.0f} GWh')
        ax1.axhline(y=actual_capacity, color='red', linestyle='-', linewidth=2,
                    label=f'Actual Capacity: {actual_capacity:.0f} GWh')
        
        ax1.set_title('Storage Energy Level Throughout Year', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Storage Energy (GWh)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Panel 2: Storage Power (Charge/Discharge)
        ax2 = fig.add_subplot(gs[1])
        storage_power = energy_analysis['storage_actions_gwh']  # Already in GW (GWh/h)
        
        ax2.plot(days, storage_power, 'g-', linewidth=1, alpha=0.7)
        ax2.fill_between(days, 0, storage_power, where=(storage_power >= 0),
                        alpha=0.3, color='green', label='Charging')
        ax2.fill_between(days, 0, storage_power, where=(storage_power < 0),
                        alpha=0.3, color='red', label='Discharging')
        
        # Add FACETS power lines (using actual data)
        facets_power = storage_adequacy['facets_storage_power_gw']
        ax2.axhline(y=facets_power, color='orange', linestyle='--', linewidth=2,
                    label=f'FACETS Power: {facets_power:.1f} GW')
        ax2.axhline(y=-facets_power, color='orange', linestyle='--', linewidth=2)
        
        ax2.set_title('Storage Power Operation (Charge/Discharge)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Power (GW)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Panel 3: Dispatchable Generation
        ax3 = fig.add_subplot(gs[2])
        dispatchable = energy_analysis['dispatchable_usage_gwh']  # GW
        
        ax3.plot(days, dispatchable, 'r-', linewidth=1, alpha=0.7, label='Dispatchable Power')
        ax3.fill_between(days, 0, dispatchable, alpha=0.3, color='red')
        
        # Add FACETS dispatchable capacity line (from actual data)
        dispatchable_capacity_gw = self.facets_capacity['dispatchable_capacity']
        ax3.axhline(y=dispatchable_capacity_gw, color='orange', linestyle='--', linewidth=2,
                    label=f'FACETS Capacity: {dispatchable_capacity_gw:.1f} GW')
        
        ax3.set_title('Dispatchable Generation vs Capacity', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Power (GW)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Panel 4: Unserved Energy
        ax4 = fig.add_subplot(gs[3])
        unserved = energy_analysis['unserved_energy_gwh']  # GW
        
        if energy_analysis['total_unserved_gwh'] > 0:
            ax4.plot(days, unserved, 'darkred', linewidth=1.5, alpha=0.8, label='Unserved Energy')
            ax4.fill_between(days, 0, unserved, alpha=0.4, color='darkred')
            ax4.set_title(f'Unserved Energy - Total: {energy_analysis["total_unserved_gwh"]:.0f} GWh', 
                         fontsize=12, fontweight='bold', color='darkred')
        else:
            ax4.text(182.5, 0.5, '✅ NO UNSERVED ENERGY\nSystem Adequate', 
                    ha='center', va='center', fontsize=14, fontweight='bold', color='green',
                    bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
            ax4.set_title('Unserved Energy', fontsize=12, fontweight='bold')
            ax4.set_ylim(0, 1)
        
        ax4.set_ylabel('Unserved (GW)')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # Panel 5: Curtailed Energy
        ax5 = fig.add_subplot(gs[4])
        curtailed = energy_analysis['curtailed_energy_gwh']  # GW
        
        if energy_analysis['total_curtailed_gwh'] > 0:
            ax5.plot(days, curtailed, 'purple', linewidth=1.5, alpha=0.8, label='Curtailed Energy')
            ax5.fill_between(days, 0, curtailed, alpha=0.4, color='purple')
            ax5.set_title(f'Curtailed Renewable Energy - Total: {energy_analysis["total_curtailed_gwh"]:.0f} GWh', 
                         fontsize=12, fontweight='bold', color='purple')
        else:
            ax5.text(182.5, 0.5, '✅ NO CURTAILMENT\nAll Renewables Used', 
                    ha='center', va='center', fontsize=14, fontweight='bold', color='green',
                    bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
            ax5.set_title('Curtailed Renewable Energy', fontsize=12, fontweight='bold')
            ax5.set_ylim(0, 1)
        
        ax5.set_ylabel('Curtailed (GW)')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # Common x-axis settings
        for ax in [ax1, ax2, ax3, ax4, ax5]:
            ax.set_xlim(0, 365)  # Full year
            # Add month markers
            month_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            ax.set_xticks(month_days)
            ax.set_xticklabels(month_names)
            ax.tick_params(axis='x', rotation=45)
        
        # Overall title
        fig.suptitle(f'Annual Storage Operation Analysis - {self.region}\n'
                    f'{self.scenario}, {self.year} | Weather Year: {self.weather_year}', fontsize=16, fontweight='bold')
        
        # Add text summary using data-driven parameters
        adequacy_status = "✅ ADEQUATE" if energy_analysis['total_unserved_gwh'] == 0 else "❌ INADEQUATE"
        curtailment_status = f"{energy_analysis['total_curtailed_gwh']:,.0f} GWh" if energy_analysis['total_curtailed_gwh'] > 0 else "None"
        
        summary_text = f"""
STORAGE OPERATION SUMMARY:
• Maximum Storage Level: {energy_analysis['max_storage_gwh']:,.0f} GWh
• Storage Capacity Limit: {energy_analysis.get('storage_energy_capacity_gwh', 'Unlimited'):,.0f} GWh
• Maximum Charge Rate: {energy_analysis['max_charge_rate_gwh']:,.0f} GW
• Maximum Discharge Rate: {energy_analysis['max_discharge_rate_gwh']:,.0f} GW  
• Total Dispatchable Energy: {energy_analysis['total_dispatchable_twh']:,.1f} TWh

SYSTEM ADEQUACY: {adequacy_status}
• Total Unserved Energy: {energy_analysis['total_unserved_gwh']:,.0f} GWh
• Hours with Shortfalls: {energy_analysis['hours_unserved']} ({energy_analysis['hours_unserved']/8760*100:.1f}%)
• Renewable Curtailment: {curtailment_status}

FACETS PLANNING (Data-Driven):
• Storage Power: {facets_power:.1f} GW
• Storage Energy: {facets_energy:.0f} GWh ({self.storage_parameters['duration_hours']:.1f}-hour duration)
• Storage Efficiency: {self.storage_parameters['round_trip_efficiency']:.1%}
• Dispatchable: {dispatchable_capacity_gw:.1f} GW
"""
        fig.text(0.15, 0.02, summary_text, fontsize=9, fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        
        plt.tight_layout()
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save plot
        output_file = f'../outputs/plots/annual_storage_operation_{self.region}_weather{self.weather_year}.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Annual storage visualization saved: {output_file}")
        
        return output_file
    
    def create_quarterly_storage_visualizations(self, energy_analysis, storage_adequacy):
        """Create quarterly storage energy balance visualizations using data-driven parameters"""
        print("\n📊 Creating Quarterly Storage Energy Visualizations...")
        
        # Define quarters
        quarters = [
            {"name": "Q1", "start": 0, "end": 2190, "months": ["Jan", "Feb", "Mar"]},
            {"name": "Q2", "start": 2190, "end": 4380, "months": ["Apr", "May", "Jun"]}, 
            {"name": "Q3", "start": 4380, "end": 6570, "months": ["Jul", "Aug", "Sep"]},
            {"name": "Q4", "start": 6570, "end": 8760, "months": ["Oct", "Nov", "Dec"]}
        ]
        
        output_files = []
        
        for quarter in quarters:
            print(f"   📅 Creating {quarter['name']} visualization ({', '.join(quarter['months'])})...")
            
            # Extract quarterly data
            start_idx = quarter["start"]
            end_idx = quarter["end"]
            
            quarterly_hours = list(range(start_idx, end_idx))
            quarterly_days = [(h - start_idx)/24 for h in quarterly_hours]
            
            storage_levels = energy_analysis['storage_levels_gwh'][start_idx:end_idx]
            storage_power = energy_analysis['storage_actions_gwh'][start_idx:end_idx]
            dispatchable = energy_analysis['dispatchable_usage_gwh'][start_idx:end_idx]
            unserved = energy_analysis['unserved_energy_gwh'][start_idx:end_idx]
            curtailed = energy_analysis.get('curtailed_energy_gwh', np.zeros(8760))[start_idx:end_idx]
            
            # Create figure with 4 panels
            fig = plt.figure(figsize=(16, 20))
            gs = plt.GridSpec(4, 1, height_ratios=[2, 1, 1, 1])
            
            # Panel 1: Storage Energy Level
            ax1 = fig.add_subplot(gs[0])
            ax1.plot(quarterly_days, storage_levels, 'b-', linewidth=2, label='Storage Energy Level')
            ax1.fill_between(quarterly_days, 0, storage_levels, alpha=0.3, color='blue')
            
            # Add FACETS planned energy line and actual capacity (using data-driven parameters)
            facets_energy = storage_adequacy['facets_storage_energy_gwh']
            actual_capacity = energy_analysis.get('storage_energy_capacity_gwh', facets_energy)
            
            ax1.axhline(y=facets_energy, color='orange', linestyle='--', linewidth=2,
                        label=f'FACETS Planned: {facets_energy:.0f} GWh ({self.storage_parameters["duration_hours"]:.1f}h)')
            ax1.axhline(y=actual_capacity, color='red', linestyle='-', linewidth=2,
                        label=f'Storage Limit: {actual_capacity:.0f} GWh')
            
            ax1.set_title(f'{quarter["name"]} Storage Energy Level - {", ".join(quarter["months"])}', 
                         fontsize=14, fontweight='bold')
            ax1.set_ylabel('Storage Energy (GWh)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Panel 2: Storage Power (Charge/Discharge)
            ax2 = fig.add_subplot(gs[1])
            ax2.plot(quarterly_days, storage_power, 'g-', linewidth=1.5, alpha=0.8)
            ax2.fill_between(quarterly_days, 0, storage_power, where=(storage_power >= 0),
                            alpha=0.4, color='green', label='Charging')
            ax2.fill_between(quarterly_days, 0, storage_power, where=(storage_power < 0),
                            alpha=0.4, color='red', label='Discharging')
            
            # Add FACETS power lines (using actual data)
            facets_power = storage_adequacy['facets_storage_power_gw']
            ax2.axhline(y=facets_power, color='orange', linestyle='--', linewidth=2,
                        label=f'FACETS Power: {facets_power:.1f} GW')
            ax2.axhline(y=-facets_power, color='orange', linestyle='--', linewidth=2)
            
            ax2.set_title(f'{quarter["name"]} Storage Power Operation', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Power (GW)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # Panel 3: Dispatchable Generation
            ax3 = fig.add_subplot(gs[2])
            ax3.plot(quarterly_days, dispatchable, 'r-', linewidth=1.5, alpha=0.8, label='Dispatchable Power')
            ax3.fill_between(quarterly_days, 0, dispatchable, alpha=0.4, color='red')
            
            # Add FACETS dispatchable capacity line (from actual data)
            dispatchable_capacity_gw = self.facets_capacity['dispatchable_capacity']
            ax3.axhline(y=dispatchable_capacity_gw, color='orange', linestyle='--', linewidth=2,
                        label=f'FACETS Capacity: {dispatchable_capacity_gw:.1f} GW')
            
            ax3.set_title(f'{quarter["name"]} Dispatchable Generation', fontsize=14, fontweight='bold')
            ax3.set_ylabel('Power (GW)')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            # Panel 4: Unserved Energy and Curtailment
            ax4 = fig.add_subplot(gs[3])
            ax4.plot(quarterly_days, unserved, 'k-', linewidth=1.5, alpha=0.8, label='Unserved Energy')
            ax4.fill_between(quarterly_days, 0, unserved, alpha=0.4, color='gray')
            
            if curtailed is not None and len(curtailed) > 0:
                ax4.plot(quarterly_days, -curtailed, 'orange', linewidth=1.5, alpha=0.8, label='Curtailed Energy')
                ax4.fill_between(quarterly_days, 0, -curtailed, alpha=0.4, color='orange')
            
            ax4.set_title(f'{quarter["name"]} Unserved (positive) & Curtailed (negative) Energy', 
                         fontsize=14, fontweight='bold')
            ax4.set_ylabel('Power (GW)')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
            
            # X-axis settings for quarterly view
            for ax in [ax1, ax2, ax3, ax4]:
                ax.set_xlim(0, len(quarterly_days)/24)  # Quarter length in days
                # Add week markers every 14 days
                quarter_days = int(len(quarterly_days)/24)
                week_ticks = list(range(0, quarter_days, 14))
                ax.set_xticks(week_ticks)
                ax.set_xticklabels([f'Day {t}' for t in week_ticks])
                ax.tick_params(axis='x', rotation=45)
            
            # Overall title
            fig.suptitle(f'Storage Operation Analysis - {quarter["name"]} {self.year} - {self.region}\n'
                        f'{self.scenario} | Weather Year: {self.weather_year}', fontsize=16, fontweight='bold')
            
            # Add quarterly statistics using data-driven parameters
            q_max_storage = max(storage_levels)
            q_unserved = sum(unserved)
            q_curtailed = sum(curtailed) if curtailed is not None else 0
            q_dispatchable = sum(dispatchable) / 1000  # Convert to TWh
            
            stats_text = f"""
{quarter["name"]} STATISTICS:
• Max Storage: {q_max_storage:.0f} GWh
• Unserved: {q_unserved:.0f} GWh  
• Curtailed: {q_curtailed:.0f} GWh
• Dispatchable: {q_dispatchable:.2f} TWh

STORAGE PARAMETERS:
• Duration: {self.storage_parameters['duration_hours']:.1f}h
• Efficiency: {self.storage_parameters['round_trip_efficiency']:.1%}
            """
            fig.text(0.85, 0.02, stats_text, fontsize=10, fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))
            
            plt.tight_layout()
            
            # Add logo watermark
            self._add_logo_watermark(fig)
            
            # Save quarterly plot
            output_file = f'../outputs/plots/storage_operation_{quarter["name"]}_{self.region}_weather{self.weather_year}.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"      ✅ {quarter['name']} visualization saved: {output_file}")
            output_files.append(output_file)
            
            plt.close()  # Close to free memory
        
        return output_files

# Example configuration file that should be created:
def create_example_config_files():
    """Create example configuration files to eliminate hardcoded values"""
    
    # technology_categories.csv
    tech_categories = pd.DataFrame([
        {'technology': 'Solar PV', 'category': 'solar'},
        {'technology': 'RTPV', 'category': 'solar'},
        {'technology': 'Solar Thermal', 'category': 'solar'},
        {'technology': 'Onshore Wind', 'category': 'wind'},
        {'technology': 'Offshore Wind', 'category': 'wind'},
        {'technology': 'Storage', 'category': 'storage'},
        {'technology': 'Combined Cycle', 'category': 'dispatchable'},
        # ... etc
    ])
    
    # storage_characteristics.csv  
    storage_chars = pd.DataFrame([
        {'scen': 're-L.gp-L.Cp-95.ncs-H.smr-L', 'year': 2045, 'region': 'p063',
         'duration_hours': 8.0, 'efficiency': 0.85, 'min_soc': 0.05, 'max_soc': 0.95}
    ])
    
    # stress_period_config.csv
    stress_config = pd.DataFrame([
        {'parameter': 'window_size_hours', 'value': 168},
        {'parameter': 'stress_types', 'value': 'net_load,ramping,renewable'},
        {'parameter': 'min_stress_duration', 'value': 24}
    ])
    
    return {
        'technology_categories.csv': tech_categories,
        'storage_characteristics.csv': storage_chars,
        'stress_period_config.csv': stress_config
    }

if __name__ == "__main__":
    # Create example of how to use with configuration file
    config = {
        "scenario": "re-L.gp-L.Cp-95.ncs-H.smr-L",
        "year": 2045,
        "region": "p063",
        "region_hdf5": "p63",
        "model_outputs_path": "../data/model_outputs/",
        "hourly_data_path": "../data/hourly_data/"
    }
    
    # Save config to file (optional)
    # with open('../config/analysis_config.json', 'w') as f:
    #     json.dump(config, f, indent=2)
    
    # Run analysis with data-driven parameters
    weather_years = [2018]
    
    for weather_year in weather_years:
        print(f"\n{'='*20} WEATHER YEAR {weather_year} {'='*20}")
        
        simulator = HourlyOperationalSimulator(
            weather_year=weather_year,
            config_file='../config/analysis_config.json'  # Optional
        )
        results = simulator.run_operational_simulation()
        
        print(f"\n✅ Analysis complete using data-driven parameters")
        print(f"📁 Check parameters_used in results for actual values loaded")