import pandas as pd
import numpy as np
import warnings
import os
import sys
from pathlib import Path

# Add root directory to Python path (robust approach)
script_dir = Path(__file__).parent.absolute()
root_dir = script_dir.parent.parent  # Go up two levels: scripts -> 2_ts_design -> root
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from shared_data_loader import get_shared_loader
from logo_manager import logo_manager
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime, timedelta
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib not available - plots will be skipped")

try:
    from enhanced_lcoe_calculator import EnhancedLCOECalculator
    ENHANCED_LCOE_AVAILABLE = True
except ImportError:
    ENHANCED_LCOE_AVAILABLE = False

# Using robust centralized branding system

warnings.filterwarnings('ignore')

class VerveStacksTimesliceProcessor:
    """
    VerveStacks Timeslice Processor - The heart of adaptive temporal modeling
    
    Transforms the 8760-hour modeling problem into intelligent, stress-based 
    timeslice structures that capture what matters most for each ISO.
    
    New Features:
    - Enhanced LCOE calculations with financing, asset life, and O&M costs
    - Historical deployment ratios for realistic solar/wind technology mix
    - Uses IRENASTAT-G.xlsx data to determine country-specific ratios
    """
    
    def __init__(self, max_timeslices=500, data_path="./data/", use_enhanced_lcoe=True, config_path="./config/"):
        # Load configuration files
        self.config_path = config_path
        self.config = self._load_configuration()
        
        # Apply configuration with parameter overrides
        self.max_timeslices = max_timeslices or self.config.get('max_timeslices', 500)
        self.base_aggregates = 12  # 4 seasons x 3 daily periods
        self.data_path = data_path
        self.use_enhanced_lcoe = use_enhanced_lcoe and ENHANCED_LCOE_AVAILABLE
        
        # Initialize enhanced LCOE calculator if available
        if self.use_enhanced_lcoe:
            self.lcoe_calculator = EnhancedLCOECalculator()
        else:
            # Fallback to simple technology costs for LCOE calculation
            self.tech_costs = {
                'wind': 1500,  # $/kW
                'solar': 700   # $/kW
            }
        
        # Region mapping will be loaded from file
        self.region_map = {}
        
        # Using robust centralized branding system
        
        # Load and prepare all data
        self.load_all_data()
    
    def _get_country_name(self, iso_code):
        """Get country name from ISO code"""
        country_names = {
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
        return country_names.get(iso_code, iso_code)
    
    def _load_configuration(self):
        """Load configuration files with fallback defaults"""
        import json
        config = {}
        
        try:
            # Load default configuration
            default_config_file = os.path.join(self.config_path, 'default_settings.json')
            if os.path.exists(default_config_file):
                with open(default_config_file, 'r') as f:
                    config = json.load(f)
                print(f"✅ Loaded default configuration from {default_config_file}")
            
            # Load ISO-specific overrides
            iso_config_file = os.path.join(self.config_path, 'iso_settings.json')
            if os.path.exists(iso_config_file):
                with open(iso_config_file, 'r') as f:
                    iso_config = json.load(f)
                    config['iso_overrides'] = iso_config
                print(f"✅ Loaded ISO-specific configuration from {iso_config_file}")
                
        except Exception as e:
            print(f"⚠️  Could not load configuration files: {e}")
            print("   Using built-in defaults")
        
        # Ensure basic defaults exist
        config.setdefault('max_timeslices', 500)
        config.setdefault('base_aggregates', 12)
        config.setdefault('use_enhanced_lcoe', True)
        
        return config
    
    def get_iso_config(self, iso_code, parameter, default_value):
        """Get ISO-specific configuration parameter with fallback to default"""
        iso_overrides = self.config.get('iso_overrides', {})
        iso_specific = iso_overrides.get(iso_code, {})
        return iso_specific.get(parameter, self.config.get(parameter, default_value))
    
    def _calculate_lcoe(self, technology, capacity_factor, capacity_mw, iso_code='USA'):
        """
        Calculate LCOE using enhanced financial modeling if available,
        otherwise fall back to simple calculation
        """
        if self.use_enhanced_lcoe:
            try:
                # Use enhanced LCOE calculator
                result = self.lcoe_calculator.calculate_enhanced_lcoe(
                    technology=technology,
                    capacity_factor=capacity_factor,
                    capacity_kw=capacity_mw * 1000,  # Convert MW to kW
                    iso_code=iso_code
                )
                return result['lcoe_enhanced']
            except Exception as e:
                # Fall back to simple calculation
                return self._simple_lcoe(technology, capacity_factor)
        else:
            return self._simple_lcoe(technology, capacity_factor)
    
    def _simple_lcoe(self, technology, capacity_factor):
        """Simple LCOE calculation (fallback method)"""
        if capacity_factor <= 0:
            return 999
        return self.tech_costs.get(technology, 1000) / (capacity_factor * 8760)
        
    def _load_region_mapping(self):
        """Load region mapping from region_map.xlsx"""
        try:
            region_df = pd.read_excel(f"{self.data_path}timeslices/region_map.xlsx")
            
            # Map 2-letter country codes to 3-letter ISO codes
            region_map = {}
            for _, row in region_df.iterrows():
                country_code = row.get('2-alpha code', '')  # 2-letter code
                iso_code = row.get('iso', '')               # 3-letter ISO code
                
                if country_code and iso_code:
                    region_map[country_code] = iso_code
            
            print(f"   Loaded region mapping for {len(region_map)} countries")
            return region_map
            
        except FileNotFoundError:
            print("⚠️  timeslices/region_map.xlsx not found - using basic country mapping")
            # Fallback to basic 2-letter to 3-letter mapping
            return {
                'DE': 'DEU', 'US': 'USA', 'CN': 'CHN', 'IN': 'IND', 
                'BR': 'BRA', 'AR': 'ARG', 'AU': 'AUS', 'CA': 'CAN',
                'MX': 'MEX', 'ZA': 'ZAF', 'JP': 'JPN', 'KR': 'KOR',
                'GB': 'GBR', 'FR': 'FRA', 'IT': 'ITA', 'ES': 'ESP',
                'NL': 'NLD', 'PL': 'POL', 'TR': 'TUR', 'SA': 'SAU',
                'AE': 'ARE', 'ID': 'IDN', 'TH': 'THA', 'VN': 'VNM'
            }
    
    def load_all_data(self):
        """Load and preprocess all data files"""
        print("🔄 Loading VerveStacks data pipeline...")
        
        # Load region mapping first (needed for other files)
        self.region_map = self._load_region_mapping()
        
        # Load demand data
        demand_data = self._load_demand_data()
        print(f"✅ Loaded demand data for {len(demand_data.columns)} ISOs")
        
        # Load existing generation (IRENA)
        existing_gen = self._load_existing_generation()
        print(f"✅ Loaded existing generation for {len(existing_gen)} countries/ISOs")
        
        # Load renewable potential
        renewable_potential = self._load_renewable_potential()
        print(f"✅ Loaded renewable potential for {len(renewable_potential)} ISOs")
        
        # Load renewable shapes
        renewable_shapes = self._load_renewable_shapes()
        print(f"✅ Loaded renewable shapes for {len(renewable_shapes['iso'].unique())} ISOs")
        
        # Load hydro seasonality (monthly patterns)
        hydro_patterns = self._load_hydro_patterns()
        print(f"✅ Loaded hydro patterns for {len(hydro_patterns)} countries")
        
        # Load hydro generation data (5-year averages by month)
        hydro_monthly = self._load_hydro_data()
        print(f"✅ Loaded hydro monthly data for {len(hydro_monthly)} ISOs/countries")
        
        # Calculate historical solar/wind ratios from actual deployment data
        print("🔄 Calculating historical solar/wind deployment ratios...")
        solar_wind_ratios = self._calculate_historical_solar_wind_ratios()
        
        return {
            'demand': demand_data,
            'existing_gen': existing_gen,
            'renewable_potential': renewable_potential,
            'renewable_shapes': renewable_shapes,
            'hydro_patterns': hydro_patterns,
            'hydro_monthly': hydro_monthly,
            'solar_wind_ratios': solar_wind_ratios
        }
    
    def _load_demand_data(self):
        """Load hourly demand data by country, then map to ISOs"""
        try:
            shared_loader = get_shared_loader(self.data_path)
            demand_df = shared_loader.get_era5_demand_data()
            print(f"   Found {len(demand_df)} hourly records for {len(demand_df['Country'].unique())} countries")
            
            # Use already loaded region mapping (no duplicate call)
            region_map = self.region_map
            
            # Pivot demand data by country
            demand_pivot = demand_df.pivot_table(
                index=['Hour', 'Day', 'Month'], 
                columns='Country', 
                values='MW', 
                aggfunc='first'
            ).reset_index()
            
            # Map country codes to ISOs and rename columns
            iso_demand = pd.DataFrame()
            for country_code in demand_pivot.columns:
                if country_code in ['Hour', 'Day', 'Month']:
                    continue
                    
                # Find ISO for this country
                iso_code = region_map.get(country_code)
                if iso_code:
                    iso_demand[iso_code] = demand_pivot[country_code]
            
            print(f"   Mapped to {len(iso_demand.columns)} ISOs")
            return iso_demand
            
        except FileNotFoundError:
            print("⚠️  hourly_profiles/era5_combined_data_2030.csv not found - using synthetic data")
            return self._create_synthetic_demand()
    
    def _load_existing_generation(self):
        """Load existing generation from IRENA files"""
        existing_gen = {}
        
        try:
            # Load capacity file
            # Use shared loader for IRENA data
            shared_loader = get_shared_loader(self.data_path)
            capacity_df = shared_loader.get_irena_capacity_data()
            print(f"   IRENA capacity: {len(capacity_df)} records")
            
            # Load generation file  
            generation_df = shared_loader.get_irena_generation_data()
            print(f"   IRENA generation: {len(generation_df)} records")
            
            # Process existing generation by technology
            # This assumes standard IRENA file structure - may need adjustment
            for _, row in generation_df.iterrows():
                country = row.get('Country/area', '')
                technology = row.get('Technology', '')
                
                # Map country to ISO using region_map
                iso_code = None
                if pd.notna(country) and isinstance(country, str):
                    for country_code, iso in self.region_map.items():
                        if (isinstance(country_code, str) and 
                            (country_code in country or country in country_code)):
                            iso_code = iso
                            break
                
                if iso_code and technology in ['Solar photovoltaic', 'Wind', 'Hydro']:
                    if iso_code not in existing_gen:
                        existing_gen[iso_code] = {}
                    
                    # Get most recent year's data
                    year_columns = [col for col in row.index if str(col).isdigit()]
                    if year_columns:
                        latest_year = max(year_columns)
                        value = row[latest_year]
                        if pd.notna(value):
                            tech_key = 'solar' if 'Solar' in technology else technology.lower()
                            existing_gen[iso_code][tech_key] = float(value)
            
        except FileNotFoundError:
            print("⚠️  IRENA files not found - using synthetic existing generation")
            existing_gen = self._create_synthetic_existing_gen()
            
        return existing_gen
    
    def _calculate_historical_solar_wind_ratios(self):
        """
        Calculate historical solar/(solar+wind) ratios by country using last 5 years of IRENA data
        This provides realistic technology mix ratios based on actual deployment patterns
        """
        ratios = {}
        
        try:
            # Load generation file  
            # Use shared loader for consistent data access
            shared_loader = get_shared_loader(self.data_path)
            generation_df = shared_loader.get_irena_generation_data()
            
            # Filter for solar and wind technologies, last 5 years
            solar_wind_df = generation_df[
                (generation_df['Technology'].isin(['Solar photovoltaic', 'Onshore wind energy', 'Offshore wind energy'])) &
                (generation_df['Year'] >= 2018) &  # Last 5 years (2018-2022)
                (generation_df['Electricity statistics (MW/GWh)'].notna()) &
                (generation_df['Electricity statistics (MW/GWh)'] > 0)
            ].copy()
            
            # Aggregate wind technologies
            solar_wind_df['tech_group'] = solar_wind_df['Technology'].apply(
                lambda x: 'solar' if 'Solar' in x else 'wind'
            )
            
            # Sum generation by country and technology group over the 5-year period
            country_totals = solar_wind_df.groupby(['Country/area', 'tech_group'])['Electricity statistics (MW/GWh)'].sum().reset_index()
            
            # Calculate solar/(solar+wind) ratios
            for country in country_totals['Country/area'].unique():
                country_data = country_totals[country_totals['Country/area'] == country]
                
                solar_gen = country_data[country_data['tech_group'] == 'solar']['Electricity statistics (MW/GWh)'].sum()
                wind_gen = country_data[country_data['tech_group'] == 'wind']['Electricity statistics (MW/GWh)'].sum()
                total_gen = solar_gen + wind_gen
                
                if total_gen > 0:
                    solar_ratio = solar_gen / total_gen
                    
                    # Map country to ISO code
                    iso_code = None
                    if isinstance(country, str):
                        # Clean country name for better matching
                        clean_country = country.replace(' (the)', '').replace(' (', ' ').replace(')', '')
                        
                        # Map to ISO using region_map or simple mappings
                        country_mappings = {
                            'United States of America': 'USA',
                            'Germany': 'DEU', 
                            'China': 'CHN',
                            'Brazil': 'BRA',
                            'India': 'IND',
                            'Japan': 'JPN',
                            'Italy': 'ITA',
                            'Spain': 'ESP',
                            'France': 'FRA',
                            'United Kingdom of Great Britain and Northern Ireland': 'GBR',
                            'Australia': 'AUS',
                            'Canada': 'CAN',
                            'Republic of Korea': 'KOR',
                            'Netherlands': 'NLD',
                            'Norway': 'NOR',
                            'Sweden': 'SWE'
                        }
                        
                        iso_code = country_mappings.get(clean_country)
                        if not iso_code:
                            # Try partial matching
                            for country_key, iso_val in country_mappings.items():
                                if country_key.lower() in clean_country.lower() or clean_country.lower() in country_key.lower():
                                    iso_code = iso_val
                                    break
                    
                    if iso_code:
                        ratios[iso_code] = {
                            'solar_ratio': solar_ratio,
                            'wind_ratio': 1 - solar_ratio,
                            'total_generation_gwh': total_gen,
                            'solar_generation_gwh': solar_gen,
                            'wind_generation_gwh': wind_gen
                        }
                        print(f"   {iso_code}: {solar_ratio:.1%} solar, {1-solar_ratio:.1%} wind (total: {total_gen:,.0f} GWh)")
            
            print(f"   ✅ Historical solar/wind ratios calculated for {len(ratios)} countries")
            return ratios
            
        except Exception as e:
            print(f"⚠️  Error calculating historical ratios: {e}")
            # Fallback to global defaults based on typical deployment patterns
            print("   Using fallback default ratios based on typical deployment patterns")
            return {
                'USA': {'solar_ratio': 0.45, 'wind_ratio': 0.55, 'total_generation_gwh': 500000, 'solar_generation_gwh': 225000, 'wind_generation_gwh': 275000},
                'DEU': {'solar_ratio': 0.55, 'wind_ratio': 0.45, 'total_generation_gwh': 120000, 'solar_generation_gwh': 66000, 'wind_generation_gwh': 54000},
                'CHN': {'solar_ratio': 0.40, 'wind_ratio': 0.60, 'total_generation_gwh': 800000, 'solar_generation_gwh': 320000, 'wind_generation_gwh': 480000},
                'IND': {'solar_ratio': 0.60, 'wind_ratio': 0.40, 'total_generation_gwh': 200000, 'solar_generation_gwh': 120000, 'wind_generation_gwh': 80000},
                'BRA': {'solar_ratio': 0.15, 'wind_ratio': 0.85, 'total_generation_gwh': 150000, 'solar_generation_gwh': 22500, 'wind_generation_gwh': 127500},
                'ITA': {'solar_ratio': 0.70, 'wind_ratio': 0.30, 'total_generation_gwh': 80000, 'solar_generation_gwh': 56000, 'wind_generation_gwh': 24000},
                'NOR': {'solar_ratio': 0.05, 'wind_ratio': 0.95, 'total_generation_gwh': 20000, 'solar_generation_gwh': 1000, 'wind_generation_gwh': 19000},
            }
    
    def _load_renewable_potential(self):
        """Load renewable potential from re_potentials.xlsx"""
        try:
            # Use shared loader for RE potentials
            shared_loader = get_shared_loader(self.data_path)
            potential_df = shared_loader.get_re_potentials_sheet('fi_t')
            
            # Extract ISO from process names (last 3 characters)
            potential_df['iso'] = potential_df['process'].str[-3:]
            
            # Calculate MWh potential
            potential_df['mwh_potential'] = potential_df['CAP_BND'] * potential_df['AF~FX'] * 8760
            
            # Calculate LCOE for ranking using enhanced method
            potential_df['tech_type'] = potential_df['Comm-IN'].map({'solar': 'solar', 'wind': 'wind'})
            potential_df['lcoe'] = potential_df.apply(
                lambda x: self._calculate_lcoe(
                    technology=x['tech_type'],
                    capacity_factor=x['AF~FX'],
                    capacity_mw=x['CAP_BND'],
                    iso_code=x['iso']
                ) if x['tech_type'] and x['AF~FX'] > 0 else 999,
                axis=1
            )
            
            print(f"   Renewable potential: {len(potential_df)} technology-ISO combinations")
            return potential_df
            
        except FileNotFoundError:
            print("⚠️  timeslices/re_potentials.xlsx not found - using synthetic renewable potential")
            return self._create_synthetic_renewable_potential()
    
    def _load_renewable_shapes(self):
        """Load hourly renewable generation shapes"""
        try:
            # Use shared loader for weather data (standardized to 2013)
            shared_loader = get_shared_loader(self.data_path)
            shapes_df = shared_loader.get_sarah_iso_weather_data()
            print(f"   Renewable shapes: {len(shapes_df)} hourly records")
            return shapes_df
        except FileNotFoundError:
            print("⚠️  hourly_profiles/sarah_era5_iso_2013.csv not found - using synthetic shapes")
            return self._create_synthetic_renewable_shapes()
    
    def _load_hydro_patterns(self):
        """Load monthly hydro generation patterns"""
        try:
            # Use shared loader for monthly hydro data
            shared_loader = get_shared_loader(self.data_path)
            hydro_df = shared_loader.get_monthly_hydro_data()
            
            # Filter for hydro generation
            hydro_only = hydro_df[
                (hydro_df['Category'] == 'Electricity generation') & 
                (hydro_df['Variable'] == 'Hydro')
            ].copy()
            
            # Extract month from date and average across years
            hydro_only['month'] = pd.to_datetime(hydro_only['Date']).dt.month
            
            # Group by country and month, average across years
            hydro_patterns = hydro_only.groupby(['Country code', 'month'])['Value'].mean().reset_index()
            
            print(f"   Hydro patterns: {len(hydro_patterns)} country-month combinations")
            return hydro_patterns
            
        except FileNotFoundError:
            print("⚠️  timeslices/monthly_full_release_long_format.csv not found - using synthetic hydro")
            return self._create_synthetic_hydro_patterns()
    
    def _load_hydro_data(self):
        """Load historical hydro generation data and calculate monthly averages by ISO"""
        try:
            print("📊 Loading hydro generation data...")
            # Use shared loader for monthly hydro data
            shared_loader = get_shared_loader(self.data_path)
            hydro_df = shared_loader.get_monthly_hydro_data()
            
            # Filter for hydro generation in TWh
            hydro_gen = hydro_df[
                (hydro_df['Category'] == 'Electricity generation') & 
                (hydro_df['Variable'] == 'Hydro') & 
                (hydro_df['Unit'] == 'TWh')
            ].copy()
            
            print(f"   Found {len(hydro_gen)} hydro generation records")
            
            # Convert Date to datetime and extract year/month
            hydro_gen['Date'] = pd.to_datetime(hydro_gen['Date'])
            hydro_gen['Year'] = hydro_gen['Date'].dt.year
            hydro_gen['Month'] = hydro_gen['Date'].dt.month
            
            # Get last 5 years (assume current data goes to 2023 or later)
            max_year = hydro_gen['Year'].max()
            recent_years = range(max_year - 4, max_year + 1)  # Last 5 years
            recent_hydro = hydro_gen[hydro_gen['Year'].isin(recent_years)]
            
            print(f"   Using data from {min(recent_years)} to {max(recent_years)}")
            
            # Calculate 5-year average monthly generation by country
            monthly_avg = recent_hydro.groupby(['Country code', 'Month'])['Value'].mean().reset_index()
            
            # Map country codes to ISO codes
            iso_hydro = {}
            for _, row in monthly_avg.iterrows():
                country_code = row['Country code']
                iso_code = self.region_map.get(country_code, country_code)  # Use ISO if mapped, else use country code
                month = row['Month']
                twh_generation = row['Value']
                
                if iso_code not in iso_hydro:
                    iso_hydro[iso_code] = {}
                iso_hydro[iso_code][month] = twh_generation
            
            print(f"   Loaded hydro data for {len(iso_hydro)} ISOs/countries")
            return iso_hydro
            
        except FileNotFoundError:
            print("⚠️  timeslices/monthly_full_release_long_format.csv not found - no hydro data")
            return {}
        except Exception as e:
            print(f"❌ Error loading hydro data: {e}")
            return {}
    
    def get_hydro_profile(self, iso_code, demand_profile, hydro_monthly):
        """Generate hourly hydro profile for an ISO based on monthly averages and demand shape"""
        if iso_code not in hydro_monthly:
            return np.zeros(8760)
        
        # Create hourly hydro profile
        hydro_hourly = np.zeros(8760)
        
        # Days in each month (non-leap year)
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        hour_start = 0
        for month in range(1, 13):
            # Get monthly generation in TWh
            monthly_twh = hydro_monthly[iso_code].get(month, 0)
            monthly_mwh = monthly_twh * 1_000_000  # TWh to MWh
            
            # Hours in this month
            hours_in_month = days_in_month[month-1] * 24
            hour_end = hour_start + hours_in_month
            
            # Get demand shape for this month
            month_demand = demand_profile[hour_start:hour_end]
            
            if len(month_demand) > 0 and month_demand.sum() > 0:
                # Distribute monthly energy based on demand shape
                demand_shape = month_demand / month_demand.sum()  # Normalize to sum=1
                month_hydro = demand_shape * monthly_mwh  # Distribute MWh across hours
                hydro_hourly[hour_start:hour_end] = month_hydro
            
            hour_start = hour_end
        
        return hydro_hourly
    
    def process_iso(self, iso_code, data_bundle, save_outputs=False, output_dir="./outputs/"):
        """
        Process a single ISO and generate all timeslice scenarios
        
        This is where the magic happens - transforming raw data into 
        intelligent temporal structures for each ISO's unique characteristics
        """
        print(f"\n🎯 Processing {iso_code} - Building adaptive timeslices...")
        
        # Step 1: Extract ISO-specific data
        iso_data = self._extract_iso_data(iso_code, data_bundle)
        if not iso_data:
            print(f"❌ Insufficient data for {iso_code}")
            return None
        
        # Step 2: Build renewable supply profile
        renewable_supply = self._build_renewable_supply(iso_code, iso_data)
        print(f"   🌞 Renewable capacity: {renewable_supply['total_capacity']:.1f} GW")
        
        # Step 3: Calculate net load
        net_load = self._calculate_net_load(iso_data, renewable_supply)
        print(f"   ⚡ Net load range: {net_load.min():.0f} to {net_load.max():.0f} MW")
        
        # Step 4: Generate critical periods using new statistical approaches
        print(f"   📊 Generating critical periods using statistical methods...")
        
        # Generate all three statistical approaches
        scenarios_plan1 = self._generate_statistical_scenarios(iso_data, renewable_supply, method="triple_1")
        scenarios_plan2 = self._generate_statistical_scenarios(iso_data, renewable_supply, method="triple_5")
        scenarios_plan3 = self._generate_statistical_scenarios(iso_data, renewable_supply, method="weekly_stress")
        
        # Combine all approaches into scenarios dict
        scenarios = {**scenarios_plan1, **scenarios_plan2, **scenarios_plan3}
        
        # Also generate the old method for comparison (optional)
        # scenarios_old = self._generate_three_span_scenarios(iso_data, renewable_supply, target_hours=400)
        # scenarios.update(scenarios_old)
        
        # Step 5: Create base aggregation scheme
        base_scheme = self._create_base_aggregation(net_load)
        
        # Step 6: Create timeslice mappings for all scenarios  
        scenario_mappings = {}
        for scenario_name, periods in scenarios.items():
            # Convert original's period format to segments format for mapping
            segments = []
            for period in periods:
                # Convert month/day to day index
                start_day_index = self._month_day_to_day_index(period['start_month'], period['start_day'])
                end_day_index = self._month_day_to_day_index(period['end_month'], period['end_day'])
                segments.append((start_day_index, end_day_index))
            
            mapping = self._generate_mapping(base_scheme, segments, scenario_name)
            scenario_mappings[scenario_name] = mapping
            
            timeslice_count = self._count_timeslices(mapping)
            total_hours = sum(period['duration_hours'] for period in periods)
            print(f"   📊 {scenario_name}: {len(periods)} periods, {total_hours} hours, {timeslice_count} timeslices")
        
        # Step 7: Save outputs if requested (NO DUPLICATION)
        if save_outputs:
            print(f"   💾 Saving outputs for {iso_code}...")
            
            # Save individual timeslice mappings
            for scenario_name, mapping_df in scenario_mappings.items():
                filename = f"{output_dir}timeslices_{iso_code}_{scenario_name}.csv"
                mapping_df.to_csv(filename, index=False)
                print(f"     ✅ {filename}")
            
            # Create consolidated tsdesign file
            consolidated_filename = self._create_consolidated_tsdesign(iso_code, scenario_mappings, output_dir)
            print(f"     🎯 {consolidated_filename}")
            
            # Create and save segment summary
            segment_summary = self._create_segment_summary(iso_code, scenarios, output_dir)
            
            # Create all plots in one organized call
            self._create_all_plots(iso_code, net_load, renewable_supply, iso_data, 
                                 scenarios, base_scheme, output_dir)
        
        return scenario_mappings, {
            'iso_data': iso_data,
            'renewable_supply': renewable_supply, 
            'net_load': net_load,
            'scenarios': scenarios,
            'base_scheme': base_scheme
        }
    
    def _create_all_plots(self, iso_code, net_load, renewable_supply, iso_data, 
                         scenarios, base_scheme, output_dir):
        """Create all plots for an ISO in one organized function - NO DUPLICATION"""
        if not MATPLOTLIB_AVAILABLE:
            print("⚠️  matplotlib not available - skipping plots")
            return
        
        print(f"   📊 Creating comprehensive visualization suite for {iso_code}...")
        
        try:
            # 1. Annual summary analysis (from original version) - run early in case later plots fail
            try:
                self._create_re_analysis_summary(iso_code, renewable_supply, iso_data, output_dir)
                print(f"   📊 Annual summary analysis completed for {iso_code}")
            except Exception as e:
                print(f"   ❌ Error creating summary analysis for {iso_code}: {e}")
            
            # 2. Statistical scenario analysis plots (updated to new approaches)
            self._plot_statistical_scenarios(iso_code, iso_data, renewable_supply, 
                                           scenarios, output_dir)
            
            # 3. Aggregation justification plots
            self._plot_aggregation_justification(iso_code, net_load, base_scheme, output_dir)
            
            # 4. Individual scenario plots (new) - has known error, run last
            try:
                self._plot_individual_scenarios(iso_code, net_load, renewable_supply, 
                                              scenarios, output_dir)
            except Exception as e:
                print(f"   ⚠️ Individual scenario plots skipped for {iso_code}: {e}")
            
            print(f"   ✅ All plots completed for {iso_code}")
            
        except Exception as e:
            print(f"   ❌ Error creating plots for {iso_code}: {str(e)}")
            import traceback
            traceback.print_exc()
    

    
    def _plot_statistical_scenarios(self, iso_code, iso_data, renewable_supply, scenarios, output_dir):
        """Plot statistical scenario analysis for Plan #2 (Triple-5) and Plan #3 (Weekly Stress)"""
        
        print(f"   📊 Creating statistical scenario plots...")
        
        # Skip Plan #1 (Triple-1) plotting since those days are already covered in Plan #2
        
        # Plot Plan #2: Triple-5 if available
        if 'triple_5' in scenarios:
            self._plot_plan2_triple_5(iso_code, iso_data, renewable_supply, scenarios['triple_5'], output_dir)
        
        # Plot Plan #3: Weekly Stress if available  
        if 'weekly_stress' in scenarios:
            self._plot_plan3_weekly_stress(iso_code, iso_data, renewable_supply, scenarios['weekly_stress'], output_dir)
        
        print(f"   ✅ Statistical scenario plots completed for {iso_code}")
    



    
    def _plot_plan2_triple_5(self, iso_code, iso_data, renewable_supply, periods, output_dir):
        """Plot Plan #2: Triple-5 scenario analysis with three category panels"""
        
        demand = iso_data['demand']
        re_supply = renewable_supply['hourly_total']
        hydro_supply = renewable_supply['hourly_hydro']
        solar_supply = renewable_supply['hourly_solar']
        wind_supply = renewable_supply['hourly_wind']
        
        # Calculate coverage for all hours
        coverage = [(re_supply[h] / demand[h] * 100) if demand[h] > 0 else 0 for h in range(8760)]
        
        # Group periods by category
        categories = {'scarcity': [], 'surplus': [], 'volatile': []}
        for period in periods:
            if period['category'] in categories:
                categories[period['category']].append(period)
        
        # Create figure with 3 subplots (one for each category)
        fig, axes = plt.subplots(3, 1, figsize=(11, 7))
        fig.suptitle(f'Plan #2: Triple-5 Critical Days Analysis - {iso_code}')
        
        # Add VerveStacks logo watermark
        logo_manager.add_matplotlib_watermark(fig)
        
        colors = {'scarcity': '#d73027', 'surplus': '#1a9850', 'volatile': '#f46d43'}
        titles = {
            'scarcity': '🔥 SCARCITY DAYS - Renewable Shortage Crisis', 
            'surplus': '⚡ SURPLUS DAYS - Renewable Excess Management',
            'volatile': '🌪️ VOLATILE DAYS - Operational Challenges'
        }
        
        for idx, (category, cat_periods) in enumerate(categories.items()):
            ax = axes[idx]
            
            # Plot all selected days for this category
            for i, period in enumerate(cat_periods):
                # Get the day index and hours
                day_start = self._month_day_to_day_index(period['start_month'], period['start_day'])
                hours = range(day_start * 24, (day_start + 1) * 24)
                
                # Convert to GW for plotting
                period_demand = [demand[h] / 1000 for h in hours]
                period_hydro = [hydro_supply[h] / 1000 for h in hours]
                period_wind = [wind_supply[h] / 1000 for h in hours]
                period_solar = [solar_supply[h] / 1000 for h in hours]
                
                # Create x-axis (hours within day)
                x_hours = list(range(24))
                x_offset = i * 25  # Offset each day by 25 hours for spacing
                x_plot = [x + x_offset for x in x_hours]
                
                # Plot stacked areas
                # Import standard energy sector colors
                from energy_colors import ENERGY_COLORS
                
                ax.fill_between(x_plot, 0, period_hydro, alpha=0.8, color=ENERGY_COLORS['hydro'], label='Hydro' if i == 0 else "")
                ax.fill_between(x_plot, period_hydro, 
                               [period_hydro[j] + period_wind[j] for j in range(24)], 
                               alpha=0.8, color=ENERGY_COLORS['wind'], label='Wind' if i == 0 else "")
                ax.fill_between(x_plot, [period_hydro[j] + period_wind[j] for j in range(24)],
                               [period_hydro[j] + period_wind[j] + period_solar[j] for j in range(24)], 
                               alpha=0.8, color=ENERGY_COLORS['solar'], label='Solar' if i == 0 else "")
                
                # Plot demand line
                ax.plot(x_plot, period_demand, color='black', linewidth=2, 
                       label='Demand' if i == 0 else "", linestyle='--')
                
                # Add coverage percentage label (keep the metric on chart as requested)
                max_y = max(max(period_demand), 
                           max([period_hydro[j] + period_wind[j] + period_solar[j] for j in range(24)]))
                ax.text(x_offset + 12, max_y * 1.05,
                       f"Avg: {period['avg_coverage']:.0f}%",
                       ha='center', va='bottom', fontsize=7, alpha=0.6,
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.6))
            
            ax.set_title(titles[category], color=colors[category])
            ax.set_ylabel('Power (GW)')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            
            # Set x-axis labels with actual dates
            if cat_periods:
                max_hours = len(cat_periods) * 25
                ax.set_xlim(0, max_hours)
                ax.set_xticks([i * 25 + 12 for i in range(len(cat_periods))])
                # Use actual dates on x-axis as requested
                date_labels = [f"{period['start_month']:02d}/{period['start_day']:02d}" for period in cat_periods]
                ax.set_xticklabels(date_labels, rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        filename = f"plan2_triple5_critical_days_{iso_code}.svg"
        filepath = Path(output_dir) / filename
        plt.savefig(filepath, format='svg', bbox_inches='tight')
        plt.close()
        
        print(f"      ✅ Plan #2 plot saved: {filename}")
    
    def _plot_plan3_weekly_stress(self, iso_code, iso_data, renewable_supply, periods, output_dir):
        """Plot Plan #3: Weekly Stress scenario analysis"""
        
        demand = iso_data['demand']
        re_supply = renewable_supply['hourly_total']
        hydro_supply = renewable_supply['hourly_hydro']
        solar_supply = renewable_supply['hourly_solar']  
        wind_supply = renewable_supply['hourly_wind']
        
        # Create figure with adaptive height
        max_height = min(6 * len(periods), 20)  # Cap at 20 inches for very long periods
        fig, axes = plt.subplots(len(periods), 1, figsize=(11, max_height))
        if len(periods) == 1:
            axes = [axes]
        
        # Add VerveStacks logo watermark
        logo_manager.add_matplotlib_watermark(fig)
            
        fig.suptitle(f'Plan #3: Weekly Sustained Stress Analysis - {iso_code}')
        
        for idx, period in enumerate(periods):
            ax = axes[idx]
            
            # Get week start/end day indices
            start_day = self._month_day_to_day_index(period['start_month'], period['start_day'])
            end_day = self._month_day_to_day_index(period['end_month'], period['end_day'])
            
            # Get all hours in this week
            hours = range(start_day * 24, (end_day + 1) * 24)
            
            # Convert to GW for plotting
            week_demand = [demand[h] / 1000 for h in hours]
            week_hydro = [hydro_supply[h] / 1000 for h in hours]  
            week_wind = [wind_supply[h] / 1000 for h in hours]
            week_solar = [solar_supply[h] / 1000 for h in hours]
            
            # Create x-axis (hours in week)
            x_hours = list(range(len(hours)))
            
            # Plot stacked areas
            ax.fill_between(x_hours, 0, week_hydro, alpha=0.8, color=ENERGY_COLORS['hydro'], label='Hydro')
            ax.fill_between(x_hours, week_hydro, 
                           [week_hydro[i] + week_wind[i] for i in range(len(hours))], 
                           alpha=0.8, color=ENERGY_COLORS['wind'], label='Wind')
            ax.fill_between(x_hours, [week_hydro[i] + week_wind[i] for i in range(len(hours))],
                           [week_hydro[i] + week_wind[i] + week_solar[i] for i in range(len(hours))], 
                           alpha=0.8, color=ENERGY_COLORS['solar'], label='Solar')
            
            # Plot demand line
            ax.plot(x_hours, week_demand, color='black', linewidth=2, label='Demand', linestyle='--')
            
            # Add day separators
            for day in range(1, period['duration_days']):
                ax.axvline(x=day * 24, color='gray', linestyle=':', alpha=0.5)
            
            ax.set_title(f"Week {idx+1}: {period['start_month']:02d}/{period['start_day']:02d} - "
                        f"{period['end_month']:02d}/{period['end_day']:02d} "
                        f"(Avg Coverage: {period['avg_coverage']:.1f}%)", 
                        color='#d73027')
            ax.set_ylabel('Power (GW)')
            ax.set_xlabel('Hours in Week')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            
            # Set x-axis to show actual dates within the week
            ax.set_xticks([i * 24 + 12 for i in range(period['duration_days'])])
            
            # Calculate actual dates for each day in the week
            start_day_idx = self._month_day_to_day_index(period['start_month'], period['start_day'])
            week_dates = []
            for day_offset in range(period['duration_days']):
                day_idx = start_day_idx + day_offset
                month, day = self._day_index_to_month_day(day_idx)
                week_dates.append(f"{month:02d}/{day:02d}")
            
            ax.set_xticklabels(week_dates, rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        filename = f"plan3_weekly_stress_{iso_code}.svg"
        filepath = Path(output_dir) / filename
        plt.savefig(filepath, format='svg', bbox_inches='tight')
        plt.close()
        
        print(f"      ✅ Plan #3 plot saved: {filename}")

    def _plot_three_span_scenarios(self, iso_code, iso_data, renewable_supply, scenarios, output_dir):
        """Plot three span scenarios using original's clean style - showing only selected period hours"""
        demand = iso_data['demand']
        re_supply = renewable_supply['hourly_total']
        
        # Calculate RE coverage percentage (original's key metric)
        coverage = [(re_supply[h] / demand[h] * 100) if demand[h] > 0 else 0 for h in range(8760)]
        
        # Create figure with vertical subplot layout (original's clean style)
        fig, axes = plt.subplots(3, 1, figsize=(11, 7))
        fig.suptitle(f'Hourly Power Profiles for Optimal Modeling Periods - {iso_code}')
        
        # Add VerveStacks logo watermark
        logo_manager.add_matplotlib_watermark(fig)
        
        scenario_names = ['short_spans', 'medium_spans', 'long_spans']
        titles = ['Short Spans (1-3 days): Maximum Event Granularity', 
                 'Medium Spans (1-7 days): Balanced Approach', 
                 'Long Spans (7-15 days): Extended Phenomena']
        colors = {'short_spans': 'red', 'medium_spans': 'blue', 'long_spans': 'green'}
        
        for idx, (scenario_name, title) in enumerate(zip(scenario_names, titles)):
            ax = axes[idx]
            
            if scenario_name in scenarios and scenarios[scenario_name]:
                periods = scenarios[scenario_name]
                
                # Collect all hours from all periods for this scenario
                all_period_data = []
                all_period_demand = []
                all_period_re = []
                period_boundaries = []
                
                for i, period in enumerate(periods):
                    # Convert month/day to day index and then to hours
                    start_day_index = self._month_day_to_day_index(period['start_month'], period['start_day'])
                    end_day_index = self._month_day_to_day_index(period['end_month'], period['end_day'])
                    
                    start_hour = start_day_index * 24
                    end_hour = min((end_day_index + 1) * 24, 8760)
                    
                    # Extract data for this period
                    period_hours = list(range(start_hour, end_hour))
                    period_coverage = [coverage[h] for h in period_hours]
                    period_demand = [demand[h] for h in period_hours]
                    period_re_supply = [re_supply[h] for h in period_hours]
                    
                    all_period_data.extend(period_coverage)
                    all_period_demand.extend(period_demand)
                    all_period_re.extend(period_re_supply)
                    
                    # Mark period boundaries
                    if i > 0:
                        period_boundaries.append(len(all_period_data) - len(period_coverage))
                
                if all_period_data:
                    hour_indices = range(len(all_period_data))
                    
                    # Convert MW to GW for cleaner visualization
                    all_period_demand_gw = [d / 1000 for d in all_period_demand]
                    all_period_re_gw = [r / 1000 for r in all_period_re]
                    
                    # Extract solar, wind, and hydro components separately
                    all_period_solar = []
                    all_period_wind = []
                    all_period_hydro = []
                    
                    for period in periods:
                        start_day_index = self._month_day_to_day_index(period['start_month'], period['start_day'])
                        end_day_index = self._month_day_to_day_index(period['end_month'], period['end_day'])
                        
                        for day_index in range(start_day_index, end_day_index + 1):
                            for hour in range(24):
                                hour_of_year = (day_index * 24 + hour) % 8760
                                all_period_solar.append(renewable_supply['hourly_solar'][hour_of_year] / 1000)  # MW to GW
                                all_period_wind.append(renewable_supply['hourly_wind'][hour_of_year] / 1000)    # MW to GW
                                all_period_hydro.append(renewable_supply.get('hourly_hydro', np.zeros(8760))[hour_of_year] / 1000)  # MW to GW
                    
                    # Create actual date labels for x-axis
                    start_date = datetime(2030, 1, 1)
                    date_labels = []
                    period_segment_info = []
                    current_pos = 0
                    
                    for i, period in enumerate(periods):
                        start_day_index = self._month_day_to_day_index(period['start_month'], period['start_day'])
                        end_day_index = self._month_day_to_day_index(period['end_month'], period['end_day'])
                        
                        period_start_date = start_date + timedelta(days=start_day_index)
                        period_end_date = start_date + timedelta(days=end_day_index)
                        period_hours = (end_day_index - start_day_index + 1) * 24
                        
                        # Create date labels for this period
                        for hour_offset in range(period_hours):
                            current_date = period_start_date + timedelta(hours=hour_offset)
                            date_labels.append(current_date)
                        
                        # Store segment info for labeling
                        period_segment_info.append({
                            'start_pos': current_pos,
                            'end_pos': current_pos + period_hours - 1,
                            'mid_pos': current_pos + period_hours // 2,
                            'period_id': period.get('period_id', f'P{i+1:02d}'),
                            'start_date': f"{period['start_month']:02d}/{period['start_day']:02d}",
                            'end_date': f"{period['end_month']:02d}/{period['end_day']:02d}",
                            'duration': period['duration_days']
                        })
                        current_pos += period_hours
                    
                    # Plot demand line
                    demand_line = ax.plot(hour_indices, all_period_demand_gw, 
                                        color='black', linewidth=2, alpha=0.8, linestyle='-',
                                        label='Demand (GW)')
                    
                    # Plot stacked renewable energy (hydro + solar + wind)
                    # Hydro (bottom layer) - steel blue color
                    ax.fill_between(hour_indices, 0, all_period_hydro,
                                   color='steelblue', alpha=0.8, label='Hydro (GW)')
                    
                    # Solar (on top of hydro) - yellow/gold color
                    hydro_plus_solar = [h + s for h, s in zip(all_period_hydro, all_period_solar)]
                    ax.fill_between(hour_indices, all_period_hydro, hydro_plus_solar,
                                   color='gold', alpha=0.7, label='Solar (GW)')
                    
                    # Wind (stacked on top of hydro + solar) - blue color  
                    ax.fill_between(hour_indices, hydro_plus_solar, all_period_re_gw,
                                   color='skyblue', alpha=0.7, label='Wind (GW)')
                    
                    # Calculate surplus and scarcity masks based on absolute values
                    surplus_mask = np.array(all_period_re_gw) > np.array(all_period_demand_gw)
                    scarcity_mask = np.array(all_period_re_gw) < (0.25 * np.array(all_period_demand_gw))  # <25% of demand
                    
                    # Fill areas for surplus and scarcity with proper bounds
                    max_value = max(max(all_period_demand_gw), max(all_period_re_gw))
                    
                    # Surplus: RE supply above demand
                    ax.fill_between(hour_indices, all_period_re_gw, all_period_demand_gw, 
                                   where=surplus_mask, alpha=0.3, color='green', 
                                   label='RE Surplus', interpolate=True)
                    
                    # Scarcity: RE supply below 25% of demand  
                    scarcity_threshold = [0.25 * d for d in all_period_demand_gw]
                    ax.fill_between(hour_indices, all_period_re_gw, scarcity_threshold,
                                   where=scarcity_mask, alpha=0.3, color='red',
                                   label='RE Scarcity (<25% demand)', interpolate=True)
                    
                    # Add 25% demand reference line
                    ax.plot(hour_indices, scarcity_threshold, 
                           color='red', linestyle=':', alpha=0.6, linewidth=1,
                           label='25% Demand Threshold')
                    
                    # Add period separators and labels
                    for i, segment in enumerate(period_segment_info):
                        # Add vertical separator line (except for first period)
                        if i > 0:
                            ax.axvline(x=segment['start_pos'], color='gray', linestyle='-', alpha=0.7, linewidth=2)
                        
                        # Add period label at the top of each segment
                        ax.annotate(f"{segment['period_id']}\n{segment['start_date']} to {segment['end_date']}\n({segment['duration']}d)", 
                                   xy=(segment['mid_pos'], max_value * 0.95), 
                                   ha='center', va='top',
                                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.8),
                                   rotation=0)
                    
                    # Clean formatting with MM-DD x-axis labels
                    ax.set_ylabel('Power (GW)')
                    ax.set_xlabel('Date (MM/DD)')
                    
                    # Set x-axis to show MM-DD dates at reasonable intervals
                    n_ticks = min(12, len(date_labels))
                    if n_ticks > 0:
                        tick_indices = np.linspace(0, len(date_labels)-1, n_ticks, dtype=int)
                        tick_labels = [date_labels[i].strftime('%m/%d') for i in tick_indices]
                        
                        ax.set_xticks(tick_indices)
                        ax.set_xticklabels(tick_labels, rotation=45, ha='right')
                    
                    total_hours = sum(p['duration_hours'] for p in periods)
                    ax.set_title(f'{title}: {len(periods)} Periods, {total_hours} Hours '
                               f'({total_hours/8760*100:.1f}% of year)')
                    
                    # Clean grid and limits
                    ax.grid(True, alpha=0.3)
                    ax.set_ylim(0, max_value * 1.1)
                    
                    # Combine legends cleanly
                    if idx == 0:  # Only show legend on first plot
                        ax.legend(loc='upper right')
                    
                else:
                    ax.text(0.5, 0.5, f'No data for {scenario_name}', 
                           ha='center', va='center', transform=ax.transAxes)
            
            else:
                ax.text(0.5, 0.5, f'No data for {scenario_name}', 
                       ha='center', va='center', transform=ax.transAxes)
        
        plt.tight_layout()
        
        # Save plot
        plot_filename = f"{output_dir}RE_scenarios_hourly_{iso_code}.svg"
        plt.savefig(plot_filename, format='svg', bbox_inches='tight')
        print(f"     📊 {plot_filename}")
        plt.close()
    
    def _create_re_analysis_summary(self, iso_code, renewable_supply, iso_data, output_dir):
        """Create annual RE analysis summary with key statistics (from original version)"""
        
        # Prepare annual data for analysis
        demand = iso_data['demand']
        re_total = renewable_supply['hourly_total']
        re_solar = renewable_supply['hourly_solar'] 
        re_wind = renewable_supply['hourly_wind']
        
        # Calculate coverage and statistics for each hour
        hourly_data = []
        for h in range(8760):
            if demand[h] > 0:
                coverage_pct = (re_total[h] / demand[h]) * 100
                is_surplus = re_total[h] > demand[h]
                is_scarcity = re_total[h] < (0.25 * demand[h])  # <25% threshold
            else:
                coverage_pct = 0
                is_surplus = False
                is_scarcity = True
            
            # Calculate month for this hour (approximate)
            day_of_year = h // 24
            month = min(12, ((day_of_year * 12) // 365) + 1)
            
            hourly_data.append({
                'hour': h,
                'month': month,
                'coverage_pct': coverage_pct,
                'is_surplus': is_surplus,
                'is_scarcity': is_scarcity,
                'demand_gw': demand[h] / 1000,
                'solar_gw': re_solar[h] / 1000,
                'wind_gw': re_wind[h] / 1000,
                'total_re_gw': re_total[h] / 1000
            })
        
        hourly_df = pd.DataFrame(hourly_data)
        
        # Calculate daily statistics (365 days)
        daily_stats = []
        for day in range(365):
            start_hour = day * 24
            end_hour = min(start_hour + 24, 8760)
            day_data = hourly_df.iloc[start_hour:end_hour]
            
            if len(day_data) > 0:
                daily_stats.append({
                    'day': day,
                    'month': day_data.iloc[12]['month'],  # Use noon hour for month
                    'avg_coverage': day_data['coverage_pct'].mean(),
                    'coverage_range': day_data['coverage_pct'].max() - day_data['coverage_pct'].min(),
                    'surplus_hours': day_data['is_surplus'].sum(),
                    'scarcity_hours': day_data['is_scarcity'].sum(),
                    'peak_demand_gw': day_data['demand_gw'].max(),
                    'peak_re_gw': day_data['total_re_gw'].max()
                })
        
        daily_df = pd.DataFrame(daily_stats)
        
        # Create 2x2 summary visualization (original's layout)
        fig, axes = plt.subplots(2, 2, figsize=(11, 7))
        
        # Add VerveStacks logo watermark
        logo_manager.add_matplotlib_watermark(fig)
        
        # 1. Average RE Coverage by Month (top-left)
        monthly_coverage = hourly_df.groupby('month')['coverage_pct'].mean()
        bars = axes[0,0].bar(monthly_coverage.index, monthly_coverage.values, 
                            color='skyblue', alpha=0.8, edgecolor='darkblue')
        axes[0,0].set_title(f'Average RE Coverage by Month - {iso_code}')
        axes[0,0].set_xlabel('Month')
        axes[0,0].set_ylabel('Coverage (%)')
        axes[0,0].grid(True, alpha=0.3)
        axes[0,0].axhline(y=100, color='red', linestyle='--', alpha=0.7, label='100% Coverage')
        axes[0,0].legend()
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            axes[0,0].text(bar.get_x() + bar.get_width()/2., height + 2,
                          f'{height:.0f}%', ha='center', va='bottom')
        
        # 2. Daily Coverage Variability (top-right)
        scatter = axes[0,1].scatter(daily_df['avg_coverage'], daily_df['coverage_range'], 
                                   alpha=0.6, c=daily_df['surplus_hours'], cmap='viridis',
                                   s=30, edgecolors='black', linewidth=0.5)
        axes[0,1].set_xlabel('Average Daily Coverage (%)')
        axes[0,1].set_ylabel('Daily Coverage Range (%)')
        axes[0,1].set_title(f'Daily Coverage: Average vs Variability - {iso_code}')
        axes[0,1].grid(True, alpha=0.3)
        cbar = plt.colorbar(scatter, ax=axes[0,1])
        cbar.set_label('Surplus Hours per Day')
        
        # 3. Hourly Coverage Distribution (bottom-left) 
        axes[1,0].hist(hourly_df['coverage_pct'], bins=50, alpha=0.7,
                      color='lightgreen', density=True)
        axes[1,0].set_xlabel('Coverage (%)')
        axes[1,0].set_ylabel('Density')
        axes[1,0].set_title(f'Distribution of Hourly RE Coverage - {iso_code}')
        axes[1,0].grid(True, alpha=0.3)
        
        # Add statistics lines
        mean_cov = hourly_df['coverage_pct'].mean()
        median_cov = hourly_df['coverage_pct'].median()
        axes[1,0].axvline(mean_cov, color='red', linestyle='--', linewidth=2, 
                         label=f'Mean: {mean_cov:.1f}%')
        axes[1,0].axvline(median_cov, color='blue', linestyle='--', linewidth=2,
                         label=f'Median: {median_cov:.1f}%')
        axes[1,0].axvline(100, color='orange', linestyle=':', linewidth=2,
                         label='100% Coverage')
        axes[1,0].legend()
        
        # 4. Technology Contribution by Month (bottom-right)
        monthly_solar = hourly_df.groupby('month')['solar_gw'].mean()
        monthly_wind = hourly_df.groupby('month')['wind_gw'].mean()
        
        x = monthly_solar.index
        width = 0.35
        
        bars1 = axes[1,1].bar([i - width/2 for i in x], monthly_solar.values, width,
                             label='Solar', color='gold', alpha=0.8, edgecolor='darkorange')
        bars2 = axes[1,1].bar([i + width/2 for i in x], monthly_wind.values, width,
                             label='Wind', color='skyblue', alpha=0.8, edgecolor='darkblue')
        
        axes[1,1].set_title(f'Average RE Generation by Month - {iso_code}')
        axes[1,1].set_xlabel('Month')
        axes[1,1].set_ylabel('Average Generation (GW)')
        axes[1,1].grid(True, alpha=0.3)
        axes[1,1].legend()
        
        # Add capacity information as text
        total_capacity = renewable_supply['total_capacity']
        peak_demand = demand.max() / 1000  # Convert to GW
        axes[1,1].text(0.02, 0.98, f'Total RE Capacity: {total_capacity:.1f} GW\nPeak Demand: {peak_demand:.1f} GW\nCapacity Ratio: {total_capacity/peak_demand:.1f}x',
                      transform=axes[1,1].transAxes, verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        # Save the summary
        output_path = f"{output_dir}/re_analysis_summary_{iso_code}.svg"
        plt.savefig(output_path, format='svg', bbox_inches='tight')
        plt.close()
        
        print(f"     📊 ./outputs/re_analysis_summary_{iso_code}.svg")
        
        # Also create a quick text summary
        summary_stats = {
            'Annual Average Coverage': f"{hourly_df['coverage_pct'].mean():.1f}%",
            'Peak Coverage': f"{hourly_df['coverage_pct'].max():.1f}%",
            'Surplus Hours': f"{hourly_df['is_surplus'].sum():,} hours ({hourly_df['is_surplus'].sum()/8760*100:.1f}% of year)",
            'Scarcity Hours': f"{hourly_df['is_scarcity'].sum():,} hours ({hourly_df['is_scarcity'].sum()/8760*100:.1f}% of year)",
            'Solar Capacity Factor': f"{(hourly_df['solar_gw'].mean() * 8760) / (renewable_supply['total_capacity'] * 8760) * 100:.1f}%" if renewable_supply['total_capacity'] > 0 else "N/A",
            'Best Month (Avg Coverage)': f"Month {monthly_coverage.idxmax()} ({monthly_coverage.max():.1f}%)",
            'Worst Month (Avg Coverage)': f"Month {monthly_coverage.idxmin()} ({monthly_coverage.min():.1f}%)"
        }
        
        print(f"     📈 Key Annual Statistics for {iso_code}:")
        for key, value in summary_stats.items():
            print(f"         • {key}: {value}")
    
    def _plot_individual_scenarios(self, iso_code, net_load, renewable_supply, scenarios, output_dir):
        """Create individual detailed plots for each scenario"""
        # Create subdirectory for individual scenario plots
        scenario_dir = f"{output_dir}individual_scenarios/"
        os.makedirs(scenario_dir, exist_ok=True)
        
        start_date = datetime(2030, 1, 1)
        time_axis = [start_date + timedelta(hours=h) for h in range(8760)]
        
        for scenario_name, segments in scenarios.items():
            fig, ax = plt.subplots(1, 1, figsize=(11, 7))
            
            # Plot full year data as background
            coverage = [(renewable_supply['hourly_total'][h] / max(1, net_load[h] + renewable_supply['hourly_total'][h]) * 100) 
                       for h in range(8760)]
            
            ax.plot(time_axis, coverage, color='lightgray', alpha=0.5, linewidth=0.5, label='Full Year Coverage')
            ax.axhline(y=100, color='gray', linestyle='--', alpha=0.7)
            
            # Highlight and detail each segment
            colors = plt.cm.tab10(np.linspace(0, 1, len(segments)))
            
            for i, (start_day, end_day) in enumerate(segments):
                start_hour = start_day * 24
                end_hour = min((end_day + 1) * 24, 8760)
                
                period_time = time_axis[start_hour:end_hour]
                period_coverage = coverage[start_hour:end_hour]
                
                segment_letter = chr(ord('a') + i)
                ax.plot(period_time, period_coverage, color=colors[i], linewidth=2, 
                       alpha=0.9, label=f'Segment {segment_letter} ({end_day-start_day+1}d)')
                
                # Add detailed annotations
                if period_time:
                    avg_coverage = np.mean(period_coverage)
                    min_coverage = min(period_coverage)
                    max_coverage = max(period_coverage)
                    
                    mid_time = period_time[len(period_time)//2]
                    ax.annotate(f'{segment_letter}\nAvg: {avg_coverage:.0f}%\nRange: {min_coverage:.0f}%-{max_coverage:.0f}%', 
                               xy=(mid_time, max_coverage), xytext=(10, 10), 
                               textcoords='offset points', fontsize=7, alpha=0.6,
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.6))
            
            ax.set_title(f'{iso_code} - {scenario_name.replace("_", " ").title()} - Detailed Analysis')
            ax.set_xlabel('Month')
            ax.set_ylabel('RE Coverage (%)')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            
            # Format x-axis
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            
            plt.tight_layout()
            
            # Save individual scenario plot
            plot_filename = f"{scenario_dir}{iso_code}_{scenario_name}_detailed.svg"
            plt.savefig(plot_filename, format='svg', bbox_inches='tight')
            print(f"     📊 {plot_filename}")
            plt.close()
    

    
    def _plot_aggregation_justification(self, iso_code, net_load, base_scheme, output_dir):
        """Create plots to justify the aggregated segment decisions"""
        # Reshape data for analysis
        daily_net_load = net_load.reshape(365, 24)
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Create comprehensive justification plots
        fig, axes = plt.subplots(2, 3, figsize=(11, 7))
        fig.suptitle(f'Aggregation Justification - {iso_code}')
        
        # Plot 1: Monthly patterns with season clusters
        ax1 = axes[0, 0]
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Calculate monthly statistics
        monthly_stats = []
        day_start = 0
        for month in range(12):
            month_days = days_in_month[month]
            month_data = daily_net_load[day_start:day_start + month_days]
            monthly_stats.append({
                'mean': month_data.mean(),
                'max': month_data.max(), 
                'min': month_data.min(),
                'std': month_data.std()
            })
            day_start += month_days
        
        # Get unique seasons and assign colors
        unique_seasons = sorted(set(base_scheme['months'].values()))
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_seasons)))
        season_colors = {season: colors[i] for i, season in enumerate(unique_seasons)}
        
        # Plot monthly means with season colors
        month_means = [s['mean'] for s in monthly_stats]
        month_colors = [season_colors[base_scheme['months'][i+1]] for i in range(12)]
        
        bars = ax1.bar(month_names, month_means, color=month_colors, alpha=0.7)
        ax1.set_title('Monthly Net Load by Season Cluster')
        ax1.set_ylabel('Average Net Load (MW)')
        ax1.grid(True, alpha=0.3)
        
        # Add season labels to legend
        handles = [plt.Rectangle((0,0),1,1, color=season_colors[season], alpha=0.7) 
                  for season in unique_seasons]
        ax1.legend(handles, [f'Season {s}' for s in unique_seasons], loc='upper right')
        
        # Plot 2: Monthly variability patterns
        ax2 = axes[0, 1]
        month_stds = [s['std'] for s in monthly_stats]
        ax2.bar(month_names, month_stds, color=month_colors, alpha=0.7)
        ax2.set_title('Monthly Variability by Season Cluster')
        ax2.set_ylabel('Net Load Std Dev (MW)')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Monthly peak patterns
        ax3 = axes[0, 2]
        month_peaks = [s['max'] for s in monthly_stats]
        ax3.bar(month_names, month_peaks, color=month_colors, alpha=0.7)
        ax3.set_title('Monthly Peak Net Load by Season Cluster')
        ax3.set_ylabel('Peak Net Load (MW)')
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Hourly patterns with period clusters
        ax4 = axes[1, 0]
        
        # Calculate hourly statistics
        hourly_stats = []
        for hour in range(24):
            hour_data = daily_net_load[:, hour]
            hourly_stats.append({
                'mean': hour_data.mean(),
                'max': hour_data.max(),
                'min': hour_data.min(), 
                'std': hour_data.std()
            })
        
        # Get unique daily periods and assign colors
        unique_periods = sorted(set(base_scheme['hours'].values()))
        period_colors = {period: colors[i % len(colors)] for i, period in enumerate(unique_periods)}
        
        # Plot hourly means with period colors
        hour_means = [s['mean'] for s in hourly_stats]
        hour_colors = [period_colors[base_scheme['hours'][i+1]] for i in range(24)]
        
        hours = list(range(24))
        bars = ax4.bar(hours, hour_means, color=hour_colors, alpha=0.7)
        ax4.set_title('Hourly Net Load by Period Cluster')
        ax4.set_xlabel('Hour of Day')
        ax4.set_ylabel('Average Net Load (MW)')
        ax4.grid(True, alpha=0.3)
        ax4.set_xticks(range(0, 24, 3))
        
        # Add period labels to legend
        handles = [plt.Rectangle((0,0),1,1, color=period_colors[period], alpha=0.7) 
                  for period in unique_periods]
        ax4.legend(handles, [f'Period {p}' for p in unique_periods], loc='upper right')
        
        # Plot 5: Hourly variability patterns
        ax5 = axes[1, 1]
        hour_stds = [s['std'] for s in hourly_stats]
        ax5.bar(hours, hour_stds, color=hour_colors, alpha=0.7)
        ax5.set_title('Hourly Variability by Period Cluster')
        ax5.set_xlabel('Hour of Day')
        ax5.set_ylabel('Net Load Std Dev (MW)')
        ax5.grid(True, alpha=0.3)
        ax5.set_xticks(range(0, 24, 3))
        
        # Plot 6: 2D heatmap showing season-period combinations
        ax6 = axes[1, 2]
        
        # Create matrix of season-period combinations
        season_period_matrix = np.zeros((len(unique_seasons), len(unique_periods)))
        season_to_idx = {season: i for i, season in enumerate(unique_seasons)}
        period_to_idx = {period: i for i, period in enumerate(unique_periods)}
        
        # Fill matrix with average net load for each combination
        for month in range(1, 13):
            season = base_scheme['months'][month]
            season_idx = season_to_idx[season]
            
            # Get month data
            month_days = days_in_month[month-1]
            day_start = sum(days_in_month[:month-1])
            month_data = daily_net_load[day_start:day_start + month_days]
            
            for hour in range(1, 25):
                period = base_scheme['hours'][hour]
                period_idx = period_to_idx[period]
                
                # Average net load for this season-period combination
                hour_data = month_data[:, hour-1]
                if len(hour_data) > 0:
                    season_period_matrix[season_idx, period_idx] += hour_data.mean() / 12  # Average across months
        
        im = ax6.imshow(season_period_matrix, cmap='RdYlBu_r', aspect='auto')
        ax6.set_title('Season-Period Net Load Matrix')
        ax6.set_xlabel('Daily Period')
        ax6.set_ylabel('Season')
        ax6.set_xticks(range(len(unique_periods)))
        ax6.set_xticklabels([f'Period {p}' for p in unique_periods])
        ax6.set_yticks(range(len(unique_seasons)))
        ax6.set_yticklabels([f'Season {s}' for s in unique_seasons])
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax6)
        cbar.set_label('Average Net Load (MW)')
        
        # Add text annotations to show values
        for i in range(len(unique_seasons)):
            for j in range(len(unique_periods)):
                text = ax6.text(j, i, f'{season_period_matrix[i, j]:.0f}',
                               ha="center", va="center", color="black")
        
        plt.tight_layout()
        
        # Save plot
        plot_filename = f"{output_dir}aggregation_justification_{iso_code}.svg"
        plt.savefig(plot_filename, format='svg', bbox_inches='tight')
        print(f"     📊 {plot_filename}")
        plt.close()
        
        # Create summary statistics tables
        self._create_aggregation_summary(iso_code, base_scheme, monthly_stats, hourly_stats, output_dir)
    
    def _create_aggregation_summary(self, iso_code, base_scheme, monthly_stats, hourly_stats, output_dir):
        """Create summary tables explaining the aggregation decisions"""
        
        # Seasonal summary
        season_summary = []
        for month in range(1, 13):
            season = base_scheme['months'][month]
            stats = monthly_stats[month-1]
            season_summary.append({
                'month': month,
                'month_name': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month-1],
                'season_cluster': season,
                'avg_net_load': stats['mean'],
                'peak_net_load': stats['max'],
                'min_net_load': stats['min'],
                'variability': stats['std']
            })
        
        season_df = pd.DataFrame(season_summary)
        season_filename = f"{output_dir}season_clusters_{iso_code}.csv"
        season_df.to_csv(season_filename, index=False)
        print(f"     📋 {season_filename}")
        
        # Daily period summary
        period_summary = []
        for hour in range(1, 25):
            period = base_scheme['hours'][hour]
            stats = hourly_stats[hour-1]
            period_summary.append({
                'hour': hour,
                'period_cluster': period,
                'avg_net_load': stats['mean'],
                'peak_net_load': stats['max'], 
                'min_net_load': stats['min'],
                'variability': stats['std']
            })
        
        period_df = pd.DataFrame(period_summary)
        period_filename = f"{output_dir}period_clusters_{iso_code}.csv"
        period_df.to_csv(period_filename, index=False)
        print(f"     📋 {period_filename}")
        
        return season_df, period_df
    
    def _create_segment_summary(self, iso_code, scenarios, output_dir):
        """Create a summary table of all periods for this ISO"""
        summary_data = []
        
        for scenario_name, periods in scenarios.items():
            for i, period in enumerate(periods):
                period_letter = chr(ord('a') + i)
                
                summary_data.append({
                    'scenario': scenario_name,
                    'period': period_letter,
                    'period_id': period.get('period_id', f'P{i+1:02d}'),
                    'start_date': f"{period['start_month']:02d}-{period['start_day']:02d}",
                    'end_date': f"{period['end_month']:02d}-{period['end_day']:02d}",
                    'duration_days': period['duration_days'],
                    'duration_hours': period['duration_hours'],
                    'avg_score': period.get('avg_score', 0),
                    'avg_coverage_range': period.get('avg_coverage_range', 0)
                })
        
        if summary_data:  # Only create file if we have data
            summary_df = pd.DataFrame(summary_data)
            summary_filename = f"{output_dir}segment_summary_{iso_code}.csv"
            summary_df.to_csv(summary_filename, index=False)
            print(f"     📋 {summary_filename}")
            return summary_df
        else:
            print(f"     ⚠️  No segments found for {iso_code}")
            return pd.DataFrame()
    
    def run_full_pipeline(self, target_isos=None, save_results=True, output_dir="./outputs/"):
        """
        Run the complete VerveStacks timeslice processing pipeline
        
        This is the main entry point - processes all ISOs and generates
        the adaptive timeslice structures that will revolutionize TIMES modeling
        """
        print("🚀 Starting VerveStacks Timeslice Processing Pipeline")
        print("=" * 60)
        
        # Create output directory structure if saving
        if save_results:
            os.makedirs(output_dir, exist_ok=True)
        
        # Load all data
        data_bundle = self.load_all_data()
        
        # Get list of ISOs to process
        if target_isos is None:
            available_isos = list(data_bundle['demand'].columns)
            target_isos = available_isos[:5]  # Process first 5 for demo
        
        print(f"\n🎯 Processing {len(target_isos)} ISOs: {', '.join(target_isos)}")
        
        # Process each ISO
        all_results = {}
        for iso_code in target_isos:
            # Create ISO-specific output directory
            if save_results:
                iso_output_dir = f"{output_dir}{iso_code}/"
                os.makedirs(iso_output_dir, exist_ok=True)
                os.makedirs(f"{iso_output_dir}individual_scenarios/", exist_ok=True)
            else:
                iso_output_dir = output_dir
            
            result = self.process_iso(iso_code, data_bundle, save_outputs=save_results, output_dir=iso_output_dir)
            if result:
                scenario_mappings, processing_data = result
                all_results[iso_code] = scenario_mappings
        
        print(f"\n✅ Successfully processed {len(all_results)} ISOs")
        if save_results:
            print(f"📁 All results saved to: {output_dir}")
            for iso_code in all_results.keys():
                print(f"   📊 {iso_code}: {output_dir}{iso_code}/")
            print(f"   📈 Individual scenario plots in each ISO's subfolder")
        print("🎉 VerveStacks timeslice structures ready for TIMES modeling!")
        
        return all_results
    
    # =========================================
    # DATA EXTRACTION AND PROCESSING METHODS
    # =========================================
    
    def _extract_iso_data(self, iso_code, data_bundle):
        """Extract and validate data for specific ISO"""
        iso_data = {}
        
        # Get demand data
        if iso_code in data_bundle['demand'].columns:
            iso_data['demand'] = data_bundle['demand'][iso_code].values
        else:
            print(f"   ⚠️  No demand data for {iso_code}")
            return None
        
        # Get renewable shapes
        shapes = data_bundle['renewable_shapes']
        iso_shapes = shapes[shapes['iso'] == iso_code]
        if not iso_shapes.empty:
            iso_data['renewable_shapes'] = iso_shapes
        else:
            print(f"   ⚠️  No renewable shapes for {iso_code}")
            return None
        
        # Get renewable potential
        potential = data_bundle['renewable_potential']
        iso_potential = potential[potential['iso'] == iso_code]
        iso_data['renewable_potential'] = iso_potential
        
        # Get hydro patterns (try ISO code, then country mapping)
        hydro = data_bundle['hydro_patterns']
        iso_hydro = hydro[hydro['Country code'] == iso_code]
        if iso_hydro.empty:
            # Try reverse mapping
            country_name = next((k for k, v in self.region_map.items() if v == iso_code), None)
            if country_name:
                iso_hydro = hydro[hydro['Country code'] == country_name]
        
        iso_data['hydro_patterns'] = iso_hydro
        
        # Get hydro monthly data
        hydro_monthly = data_bundle.get('hydro_monthly', {})
        iso_data['hydro_monthly'] = hydro_monthly
        
        return iso_data
    
    def _build_renewable_supply(self, iso_code, iso_data):
        """Build optimal renewable supply mix for ISO - ENERGY-BASED sizing for realistic analysis"""
        
        # Calculate annual energy demand (TWh)
        annual_demand_mwh = iso_data['demand'].sum()  # Sum all hourly demand
        annual_demand_twh = annual_demand_mwh / 1_000_000  # Convert MWh to TWh
        
        peak_demand_mw = iso_data['demand'].max()
        
        # Calculate hydro contribution first
        hydro_monthly = iso_data.get('hydro_monthly', {})
        demand_profile = iso_data['demand']
        hourly_hydro = self.get_hydro_profile(iso_code, demand_profile, hydro_monthly)
        annual_hydro_mwh = hourly_hydro.sum()
        annual_hydro_twh = annual_hydro_mwh / 1_000_000
        
        # Calculate RESIDUAL demand that wind+solar must meet
        residual_demand_mwh = annual_demand_mwh - annual_hydro_mwh
        residual_demand_twh = residual_demand_mwh / 1_000_000
        
        print(f"       🎯 Total demand: {annual_demand_twh:.1f} TWh (peak: {peak_demand_mw:.0f} MW)")
        print(f"       💧 Hydro supply: {annual_hydro_twh:.1f} TWh")
        print(f"       ⚡ Residual for wind+solar: {residual_demand_twh:.1f} TWh")
        print(f"       📊 Load factor: {(annual_demand_mwh / (peak_demand_mw * 8760)) * 100:.1f}%")
        
        # Get renewable potential 
        potential = iso_data['renewable_potential'].copy()
        if potential.empty:
            print(f"       ⚠️ No renewable potential data for {iso_code}")
            return {
                'total_capacity': 0,
                'selected_resources': [],
                'hourly_solar': np.zeros(8760),
                'hourly_wind': np.zeros(8760),
                'hourly_total': np.zeros(8760)
            }
        
        # Calculate annual energy potential for each resource
        potential['annual_energy_mwh'] = potential['CAP_BND'] * potential['AF~FX'] * 8760 * 1000  # GW * CF * hours * 1000 = MWh
        
        # Get historical solar/wind ratios for this country
        solar_wind_ratios = iso_data.get('solar_wind_ratios', {})
        country_ratios = solar_wind_ratios.get(iso_code, {'solar_ratio': 0.5, 'wind_ratio': 0.5})  # Default 50/50
        
        print(f"       📊 Available potential: {len(potential)} technology options")
        print(f"       🏛️ Using historical ratios: {country_ratios['solar_ratio']:.1%} solar, {country_ratios['wind_ratio']:.1%} wind")
        
        # Check if hydro already meets all demand
        if residual_demand_mwh <= 0:
            print(f"       🌊 Hydro surplus! Hydro generates {annual_hydro_twh:.1f} TWh vs {annual_demand_twh:.1f} TWh demand")
            print(f"       ⚡ No additional wind+solar needed - hydro covers everything!")
            # Still need to set up the structure but with zero wind+solar
        
        # Build renewable mix using historical deployment ratios
        total_energy_mwh = 0
        total_capacity_gw = 0
        selected_resources = []
        
        # Only build wind+solar if there's residual demand after hydro
        if residual_demand_mwh > 0:
            # Allocate residual demand between solar and wind based on historical ratios
            solar_target_mwh = residual_demand_mwh * country_ratios['solar_ratio']
            wind_target_mwh = residual_demand_mwh * country_ratios['wind_ratio']
            
            print(f"       📈 Target allocation: {solar_target_mwh/1_000_000:.1f} TWh solar, {wind_target_mwh/1_000_000:.1f} TWh wind")
            
            # Build solar capacity first
            solar_potential = potential[potential['tech_type'] == 'solar'].sort_values('lcoe')
            solar_energy_built = 0
            solar_capacity_built = 0
            
            for _, resource in solar_potential.iterrows():
                if solar_energy_built >= solar_target_mwh:
                    break
                    
                remaining_solar_mwh = solar_target_mwh - solar_energy_built
                available_energy_mwh = resource['annual_energy_mwh']
                
                if available_energy_mwh <= remaining_solar_mwh:
                    # Take the full resource
                    energy_to_add_mwh = available_energy_mwh
                    capacity_to_add_gw = resource['CAP_BND']
                else:
                    # Take partial resource
                    energy_to_add_mwh = remaining_solar_mwh
                    capacity_to_add_gw = remaining_solar_mwh / (resource['AF~FX'] * 8760 * 1000)
                
                if energy_to_add_mwh > 0:
                    selected_resources.append({
                        'technology': 'solar',
                        'capacity_gw': capacity_to_add_gw,
                        'capacity_mw': capacity_to_add_gw * 1000,
                        'capacity_factor': resource['AF~FX'],
                        'annual_mwh': energy_to_add_mwh,
                        'annual_twh': energy_to_add_mwh / 1_000_000,
                        'lcoe': resource['lcoe']
                    })
                    solar_capacity_built += capacity_to_add_gw
                    solar_energy_built += energy_to_add_mwh
            
            # Build wind capacity second
            wind_potential = potential[potential['tech_type'] == 'wind'].sort_values('lcoe')
            wind_energy_built = 0
            wind_capacity_built = 0
            
            for _, resource in wind_potential.iterrows():
                if wind_energy_built >= wind_target_mwh:
                    break
                    
                remaining_wind_mwh = wind_target_mwh - wind_energy_built
                available_energy_mwh = resource['annual_energy_mwh']
                
                if available_energy_mwh <= remaining_wind_mwh:
                    # Take the full resource
                    energy_to_add_mwh = available_energy_mwh
                    capacity_to_add_gw = resource['CAP_BND']
                else:
                    # Take partial resource
                    energy_to_add_mwh = remaining_wind_mwh
                    capacity_to_add_gw = remaining_wind_mwh / (resource['AF~FX'] * 8760 * 1000)
                
                if energy_to_add_mwh > 0:
                    selected_resources.append({
                        'technology': 'wind',
                        'capacity_gw': capacity_to_add_gw,
                        'capacity_mw': capacity_to_add_gw * 1000,
                        'capacity_factor': resource['AF~FX'],
                        'annual_mwh': energy_to_add_mwh,
                        'annual_twh': energy_to_add_mwh / 1_000_000,
                        'lcoe': resource['lcoe']
                    })
                    wind_capacity_built += capacity_to_add_gw
                    wind_energy_built += energy_to_add_mwh
            
            total_capacity_gw = solar_capacity_built + wind_capacity_built
            total_energy_mwh = solar_energy_built + wind_energy_built
            
            print(f"       ☀️ Solar built: {solar_capacity_built:.1f} GW, {solar_energy_built/1_000_000:.1f} TWh")
            print(f"       💨 Wind built: {wind_capacity_built:.1f} GW, {wind_energy_built/1_000_000:.1f} TWh")
                

        
        capacity_vs_peak = (total_capacity_gw * 1000) / peak_demand_mw * 100  # Convert GW to MW for comparison
        wind_solar_energy_twh = total_energy_mwh / 1_000_000  # Convert MWh to TWh for display
        total_system_energy_twh = wind_solar_energy_twh + annual_hydro_twh  # Total energy including hydro
        
        print(f"       🏗️ Wind+Solar built: {total_capacity_gw:.1f} GW generating {wind_solar_energy_twh:.1f} TWh ({capacity_vs_peak:.1f}% of peak demand)")
        print(f"       ⚡ Total system energy: {total_system_energy_twh:.1f} TWh (target: {annual_demand_twh:.1f} TWh)")
        
        # Hydro profile already calculated above
        
        # Calculate hydro capacity
        if hourly_hydro.max() > 0:
            hydro_capacity_gw = hourly_hydro.max() / 1000  # Peak MW to GW
        else:
            hydro_capacity_gw = 0
            print(f"       💧 No hydro data for {iso_code}")
        
        # Build hourly generation profiles using shapes
        shapes = iso_data['renewable_shapes']
        
        # Initialize hourly arrays
        hourly_solar = np.zeros(8760)
        hourly_wind = np.zeros(8760)
        
        if not shapes.empty and len(shapes) >= 8760:
            # Sort shapes data chronologically to ensure proper hour ordering
            shapes_sorted = shapes.sort_values(['month', 'day', 'hour']).reset_index(drop=True)
            
            # Calculate total annual generation by technology, then distribute using shapes
            
            # Calculate total annual generation for each technology
            total_solar_annual_mwh = 0
            total_wind_annual_mwh = 0
            
            for resource in selected_resources:
                if resource['technology'] == 'solar':
                    # Annual generation = CAP_BND * AF~FX * 8760 * 1000 MWh
                    annual_gen = resource['capacity_gw'] * resource['capacity_factor'] * 8760 * 1000
                    total_solar_annual_mwh += annual_gen
                elif resource['technology'] == 'wind':
                    # Annual generation = CAP_BND * AF~FX * 8760 * 1000 MWh  
                    annual_gen = resource['capacity_gw'] * resource['capacity_factor'] * 8760 * 1000
                    total_wind_annual_mwh += annual_gen
            
            # Distribute total annual generation across hours using chronologically sorted fractions
            if total_solar_annual_mwh > 0:
                hourly_solar = shapes_sorted['com_fr_solar'].iloc[:8760].values * total_solar_annual_mwh
            
            if total_wind_annual_mwh > 0:
                hourly_wind = shapes_sorted['com_fr_wind'].iloc[:8760].values * total_wind_annual_mwh
        else:
            print(f"       ⚠️ Insufficient renewable shapes data ({len(shapes)} records)")
        
        return {
            'total_capacity': total_capacity_gw,  # In GW (wind + solar only)
            'total_capacity_mw': total_capacity_gw * 1000,  # Also provide in MW
            'hydro_capacity_gw': hydro_capacity_gw,  # Hydro capacity in GW
            'total_system_capacity': total_capacity_gw + hydro_capacity_gw,  # Total including hydro
            'selected_resources': selected_resources,
            'hourly_hydro': hourly_hydro,  # In MW
            'hourly_solar': hourly_solar,  # In MW
            'hourly_wind': hourly_wind,    # In MW  
            'hourly_total': hourly_solar + hourly_wind + hourly_hydro  # In MW (includes hydro)
        }
    
    def _calculate_net_load(self, iso_data, renewable_supply):
        """Calculate net load = demand - renewables (which now includes hydro)"""
        
        demand = iso_data['demand']
        # renewable_supply['hourly_total'] now includes hydro + wind + solar
        renewables_total = renewable_supply['hourly_total']
        
        # Net load = what needs to be served by dispatchable generation
        # (renewables_total already includes hydro, so no double-counting)
        net_load = demand - renewables_total
        
        return net_load
    
    # ==========================================
    # STRESS SCENARIO GENERATION METHODS
    # ==========================================
    
    def _generate_statistical_scenarios(self, iso_data, renewable_supply, method="triple_5"):
        """Generate critical periods using clean statistical approaches"""
        
        if method == "triple_1":
            return self._generate_plan1_triple_1(iso_data, renewable_supply)
        elif method == "triple_5":
            return self._generate_plan2_triple_5(iso_data, renewable_supply)
        elif method == "weekly_stress":
            return self._generate_plan3_weekly_stress(iso_data, renewable_supply)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _generate_plan1_triple_1(self, iso_data, renewable_supply):
        """Plan #1: Triple-1 - 1 scarcity + 1 surplus + 1 volatile day (3 days = 72h)"""
        
        demand = iso_data['demand']
        re_supply = renewable_supply['hourly_total']
        
        print(f"   📊 Plan #1: Statistical Triple-1 Selection")
        print(f"   🎯 Target: 1 scarcity + 1 surplus + 1 volatile day = 3 days (72 hours)")
        
        # Calculate RE coverage percentage for all hours
        coverage = [(re_supply[h] / demand[h] * 100) if demand[h] > 0 else 0 for h in range(8760)]
        
        # Calculate daily statistics for all 365 days
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        daily_stats = []
        
        for day in range(365):
            day_coverage = np.array(coverage[day*24:(day+1)*24])
            
            # Determine month and day-of-month
            cum_days = np.cumsum([0] + days_in_month)
            month = np.where(day < cum_days[1:])[0][0] + 1
            day_in_month = day - cum_days[month-1] + 1
            
            # Core statistical metrics
            avg_coverage = np.mean(day_coverage)
            coverage_variance = np.var(day_coverage)
            coverage_std = np.std(day_coverage)
            min_coverage = np.min(day_coverage)
            max_coverage = np.max(day_coverage)
            
            stats = {
                'day_index': day,
                'month': month,
                'day_in_month': day_in_month,
                'date_string': f"{month:02d}/{day_in_month:02d}",
                'avg_coverage': avg_coverage,
                'coverage_variance': coverage_variance,
                'coverage_std': coverage_std,
                'min_coverage': min_coverage,
                'max_coverage': max_coverage
            }
            daily_stats.append(stats)
        
        df = pd.DataFrame(daily_stats)
        
        # Step 1: Select 1 worst scarcity day (lowest average coverage)
        scarcity_ranking = df.sort_values('avg_coverage', ascending=True)
        scarcity_days = scarcity_ranking.head(1)
        used_day_indices = set(scarcity_days['day_index'])
        
        print(f"\n   🔥 SCARCITY DAY (Renewable Shortage Crisis):")
        for i, (_, row) in enumerate(scarcity_days.iterrows(), 1):
            print(f"      {i}. {row['date_string']}: Avg={row['avg_coverage']:.1f}% "
                  f"(Min={row['min_coverage']:.1f}%, Max={row['max_coverage']:.1f}%)")
        
        # Step 2: Select 1 best surplus day (highest average coverage, excluding used days)
        surplus_ranking = df[~df['day_index'].isin(used_day_indices)].sort_values('avg_coverage', ascending=False)
        surplus_days = surplus_ranking.head(1)
        used_day_indices.update(surplus_days['day_index'])
        
        print(f"\n   ⚡ SURPLUS DAY (Renewable Excess Management):")
        for i, (_, row) in enumerate(surplus_days.iterrows(), 1):
            print(f"      {i}. {row['date_string']}: Avg={row['avg_coverage']:.1f}% "
                  f"(Min={row['min_coverage']:.1f}%, Max={row['max_coverage']:.1f}%)")
        
        # Step 3: Select 1 most volatile day (highest variance, excluding used days, avg coverage <= 100%)
        available_volatile = df[
            (~df['day_index'].isin(used_day_indices)) & 
            (df['avg_coverage'] <= 100)
        ].sort_values('coverage_variance', ascending=False)
        volatile_days = available_volatile.head(1)
        
        print(f"\n   🌪️ VOLATILE DAY (Operational Challenges):")
        for i, (_, row) in enumerate(volatile_days.iterrows(), 1):
            print(f"      {i}. {row['date_string']}: Avg={row['avg_coverage']:.1f}%, "
                  f"Var={row['coverage_variance']:.1f}, Std={row['coverage_std']:.1f}")
        
        # Create periods structure for compatibility
        all_selected_days = pd.concat([scarcity_days, surplus_days, volatile_days])
        periods = []
        
        for category, days_df in [('scarcity', scarcity_days), ('surplus', surplus_days), ('volatile', volatile_days)]:
            for i, (_, row) in enumerate(days_df.iterrows(), 1):
                period_info = {
                    'category': category,
                    'start_month': int(row['month']),
                    'start_day': int(row['day_in_month']),
                    'end_month': int(row['month']),
                    'end_day': int(row['day_in_month']),
                    'duration_days': 1,
                    'duration_hours': 24,
                    'avg_coverage': row['avg_coverage'],
                    'coverage_variance': row['coverage_variance'],
                    'period_id': f"{category[0].upper()}{i:02d}",
                    'description': f"{category.title()} day: {row['date_string']}"
                }
                periods.append(period_info)
        
        total_hours = len(periods) * 24
        print(f"\n   📊 Selected {len(periods)} days totaling {total_hours} hours")
        print(f"   📈 Coverage range: {all_selected_days['avg_coverage'].min():.1f}% to {all_selected_days['avg_coverage'].max():.1f}%")
        
        return {'triple_1': periods}
    
    def _generate_plan2_triple_5(self, iso_data, renewable_supply):
        """Plan #2: No-Overlap Triple-5 - 5 scarcity + 5 surplus + 5 volatile days (15 days = 360h)"""
        
        demand = iso_data['demand']
        re_supply = renewable_supply['hourly_total']
        
        print(f"   📊 Plan #2: Statistical Triple-5 Selection")
        print(f"   🎯 Target: 5 scarcity + 5 surplus + 5 volatile days = 15 days (360 hours)")
        
        # Calculate RE coverage percentage for all hours
        coverage = [(re_supply[h] / demand[h] * 100) if demand[h] > 0 else 0 for h in range(8760)]
        
        # Calculate daily statistics for all 365 days
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        daily_stats = []
        
        for day in range(365):
            day_coverage = np.array(coverage[day*24:(day+1)*24])
            
            # Determine month and day-of-month
            cum_days = np.cumsum([0] + days_in_month)
            month = np.where(day < cum_days[1:])[0][0] + 1
            day_in_month = day - cum_days[month-1] + 1
            
            # Core statistical metrics
            avg_coverage = np.mean(day_coverage)
            coverage_variance = np.var(day_coverage)
            coverage_std = np.std(day_coverage)
            min_coverage = np.min(day_coverage)
            max_coverage = np.max(day_coverage)
            
            stats = {
                'day_index': day,
                'month': month,
                'day_in_month': day_in_month,
                'date_string': f"{month:02d}/{day_in_month:02d}",
                'avg_coverage': avg_coverage,
                'coverage_variance': coverage_variance,
                'coverage_std': coverage_std,
                'min_coverage': min_coverage,
                'max_coverage': max_coverage
            }
            daily_stats.append(stats)
        
        df = pd.DataFrame(daily_stats)
        
        # Step 1: Select 5 worst scarcity days (lowest average coverage)
        scarcity_ranking = df.sort_values('avg_coverage', ascending=True)
        scarcity_days = scarcity_ranking.head(5)
        used_day_indices = set(scarcity_days['day_index'])
        
        print(f"\n   🔥 SCARCITY DAYS (Renewable Shortage Crisis):")
        for i, (_, row) in enumerate(scarcity_days.iterrows(), 1):
            print(f"      {i}. {row['date_string']}: Avg={row['avg_coverage']:.1f}% "
                  f"(Min={row['min_coverage']:.1f}%, Max={row['max_coverage']:.1f}%)")
        
        # Step 2: Select 5 best surplus days (highest average coverage, excluding used days)
        surplus_ranking = df[~df['day_index'].isin(used_day_indices)].sort_values('avg_coverage', ascending=False)
        surplus_days = surplus_ranking.head(5)
        used_day_indices.update(surplus_days['day_index'])
        
        print(f"\n   ⚡ SURPLUS DAYS (Renewable Excess Management):")
        for i, (_, row) in enumerate(surplus_days.iterrows(), 1):
            print(f"      {i}. {row['date_string']}: Avg={row['avg_coverage']:.1f}% "
                  f"(Min={row['min_coverage']:.1f}%, Max={row['max_coverage']:.1f}%)")
        
        # Step 3: Select 5 most volatile days (highest variance, excluding used days, avg coverage <= 100%)
        available_volatile = df[
            (~df['day_index'].isin(used_day_indices)) & 
            (df['avg_coverage'] <= 100)
        ].sort_values('coverage_variance', ascending=False)
        volatile_days = available_volatile.head(5)
        
        print(f"\n   🌪️ VOLATILE DAYS (Operational Challenges):")
        for i, (_, row) in enumerate(volatile_days.iterrows(), 1):
            print(f"      {i}. {row['date_string']}: Avg={row['avg_coverage']:.1f}%, "
                  f"Var={row['coverage_variance']:.1f}, Std={row['coverage_std']:.1f}")
        
        # Create periods structure for compatibility
        all_selected_days = pd.concat([scarcity_days, surplus_days, volatile_days])
        periods = []
        
        for category, days_df in [('scarcity', scarcity_days), ('surplus', surplus_days), ('volatile', volatile_days)]:
            for i, (_, row) in enumerate(days_df.iterrows(), 1):
                period_info = {
                    'category': category,
                    'start_month': int(row['month']),
                    'start_day': int(row['day_in_month']),
                    'end_month': int(row['month']),
                    'end_day': int(row['day_in_month']),
                    'duration_days': 1,
                    'duration_hours': 24,
                    'avg_coverage': row['avg_coverage'],
                    'coverage_variance': row['coverage_variance'],
                    'period_id': f"{category[0].upper()}{i:02d}",
                    'description': f"{category.title()} day: {row['date_string']}"
                }
                periods.append(period_info)
        
        total_hours = len(periods) * 24
        print(f"\n   📊 Selected {len(periods)} days totaling {total_hours} hours")
        print(f"   📈 Coverage range: {all_selected_days['avg_coverage'].min():.1f}% to {all_selected_days['avg_coverage'].max():.1f}%")
        
        return {'triple_5': periods}
    
    def _generate_plan3_weekly_stress(self, iso_data, renewable_supply):
        """Plan #3: Weekly Sustained Stress - 2 worst weeks by average coverage (2 weeks = 336h)"""
        
        demand = iso_data['demand']
        re_supply = renewable_supply['hourly_total']
        
        print(f"   📊 Plan #3: Weekly Sustained Stress Selection")
        print(f"   🎯 Target: 2 worst weeks = 14 days (336 hours)")
        
        # Calculate RE coverage percentage for all hours
        coverage = [(re_supply[h] / demand[h] * 100) if demand[h] > 0 else 0 for h in range(8760)]
        
        # Calculate weekly statistics
        weekly_stats = []
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        for week in range(52):  # 52 weeks in year
            week_start_day = week * 7
            week_end_day = min((week + 1) * 7, 365)
            
            # Get all hours in this week
            week_hours = []
            for day in range(week_start_day, week_end_day):
                if day < 365:  # Safety check
                    day_coverage = coverage[day*24:(day+1)*24]
                    week_hours.extend(day_coverage)
            
            if week_hours:  # Ensure we have data
                # Calculate week statistics
                week_avg_coverage = np.mean(week_hours)
                week_min_coverage = np.min(week_hours)
                week_max_coverage = np.max(week_hours)
                week_std_coverage = np.std(week_hours)
                
                # Get week start/end dates
                start_cum_days = np.cumsum([0] + days_in_month)
                start_month = np.where(week_start_day < start_cum_days[1:])[0][0] + 1
                start_day_in_month = week_start_day - start_cum_days[start_month-1] + 1
                
                end_day_idx = min(week_end_day - 1, 364)
                end_month = np.where(end_day_idx < start_cum_days[1:])[0][0] + 1
                end_day_in_month = end_day_idx - start_cum_days[end_month-1] + 1
                
                weekly_stats.append({
                    'week_index': week,
                    'week_avg_coverage': week_avg_coverage,
                    'week_min_coverage': week_min_coverage,
                    'week_max_coverage': week_max_coverage,
                    'week_std_coverage': week_std_coverage,
                    'start_month': start_month,
                    'start_day': start_day_in_month,
                    'end_month': end_month,
                    'end_day': end_day_in_month,
                    'week_span': f"{start_month:02d}/{start_day_in_month:02d}-{end_month:02d}/{end_day_in_month:02d}",
                    'days_in_week': week_end_day - week_start_day
                })
        
        df_weeks = pd.DataFrame(weekly_stats)
        
        # Select 2 worst weeks by average coverage
        worst_weeks = df_weeks.sort_values('week_avg_coverage', ascending=True).head(2)
        
        print(f"\n   🌨️ SUSTAINED STRESS WEEKS:")
        periods = []
        for i, (_, row) in enumerate(worst_weeks.iterrows(), 1):
            print(f"      {i}. Week {row['week_span']}: Avg={row['week_avg_coverage']:.1f}% "
                  f"(Min={row['week_min_coverage']:.1f}%, Max={row['week_max_coverage']:.1f}%)")
            
            period_info = {
                'category': 'sustained_stress',
                'start_month': int(row['start_month']),
                'start_day': int(row['start_day']),
                'end_month': int(row['end_month']),
                'end_day': int(row['end_day']),
                'duration_days': row['days_in_week'],
                'duration_hours': row['days_in_week'] * 24,
                'avg_coverage': row['week_avg_coverage'],
                'min_coverage': row['week_min_coverage'],
                'max_coverage': row['week_max_coverage'],
                'period_id': f"W{i:02d}",
                'description': f"Sustained stress week: {row['week_span']}"
            }
            periods.append(period_info)
        
        total_hours = sum(p['duration_hours'] for p in periods)
        print(f"\n   📊 Selected {len(periods)} weeks totaling {total_hours} hours")
        print(f"   📈 Coverage range: {worst_weeks['week_avg_coverage'].min():.1f}% to {worst_weeks['week_avg_coverage'].max():.1f}%")
        
        return {'weekly_stress': periods}
    
    def _generate_three_span_scenarios(self, iso_data, renewable_supply, target_hours=400):
        """Generate three span scenarios using original's superior RE coverage-based method"""
        
        demand = iso_data['demand']
        re_supply = renewable_supply['hourly_total']
        
        # Calculate RE coverage percentage (the key metric from original)
        coverage = [(re_supply[h] / demand[h] * 100) if demand[h] > 0 else 0 for h in range(8760)]
        daily_coverage = np.array(coverage).reshape(365, 24)
        
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Calculate comprehensive daily statistics using RE coverage (original approach)
        daily_stats = []
        for day in range(365):
            day_coverage = daily_coverage[day]
            day_demand = demand[day*24:(day+1)*24]
            
            # Determine month and day-of-month
            cum_days = np.cumsum([0] + days_in_month)
            month = np.where(day < cum_days[1:])[0][0] + 1
            day_in_month = day - cum_days[month-1] + 1
            
            # Calculate coverage statistics (original's approach)
            min_coverage = day_coverage.min()
            max_coverage = day_coverage.max()
            coverage_range = max_coverage - min_coverage
            avg_coverage = day_coverage.mean()
            
            # Count special hours (original's logic)
            surplus_hours = np.sum(day_coverage > 100)  # Hours with RE surplus
            extreme_scarcity_hours = np.sum(day_coverage < 25)  # Hours with severe scarcity
            scarcity_hours = np.sum(day_coverage < 50)  # Hours with moderate scarcity
            peak_demand = day_demand.max()
            
            stats = {
                'day_index': day,
                'month': month,
                'day_in_month': day_in_month,
                'date_key': f"{month}-{day_in_month}",
                'min_coverage': min_coverage,
                'max_coverage': max_coverage,
                'avg_coverage': avg_coverage,
                'coverage_range': coverage_range,
                'surplus_hours': surplus_hours,
                'extreme_scarcity_hours': extreme_scarcity_hours,
                'scarcity_hours': scarcity_hours,
                'peak_demand': peak_demand,
                'balance_range': coverage_range  # For compatibility
            }
            daily_stats.append(stats)
        
        daily_stats_df = pd.DataFrame(daily_stats)
        
        # Apply original's 6-factor composite scoring
        daily_stats_df = self._calculate_original_composite_scores(daily_stats_df)
        
        print(f"   📊 RE Coverage Analysis Complete - Top 10 representative days:")
        top_days = daily_stats_df.nlargest(10, 'composite_score')
        for i, (_, row) in enumerate(top_days.iterrows(), 1):
            print(f"      {i:2d}. {row['month']:2d}/{row['day_in_month']:2d} - Score: {row['composite_score']:.3f} "
                  f"(Coverage: {row['min_coverage']:4.1f}%-{row['max_coverage']:4.1f}%, "
                  f"Surplus: {row['surplus_hours']:2.0f}h)")
        
        scenarios = {}
        
        # Scenario 1: Short spans (1-3 days) - Maximum event granularity  
        print(f"\n   📋 SHORT SPANS (1-3 days) - Maximum Event Granularity")
        max_periods_short = target_hours // (3 * 24)  # Assume avg 3 days per period
        short_periods = self._find_diverse_contiguous_periods(
            daily_stats_df, max_periods=max_periods_short, min_days=1, max_days=3, 
            target_hours=target_hours, scenario_type="short"
        )
        scenarios['short_spans'] = short_periods
        
        # Scenario 2: Medium spans (1-7 days) - Balanced approach (avoid short period dates)
        print(f"\n   📋 MEDIUM SPANS (1-7 days) - Balanced Approach")
        max_periods_medium = target_hours // (5 * 24)  # Assume avg 5 days per period
        medium_periods = self._find_diverse_contiguous_periods(
            daily_stats_df, max_periods=max_periods_medium, min_days=1, max_days=7, 
            target_hours=target_hours, scenario_type="medium", excluded_periods=short_periods
        )
        scenarios['medium_spans'] = medium_periods
        
        # Scenario 3: Long spans (7-15 days) - Extended phenomena (avoid all previous dates)
        print(f"\n   📋 LONG SPANS (7-15 days) - Extended Phenomena")
        max_periods_long = target_hours // (12 * 24)  # Assume avg 12 days per period
        long_periods = self._find_diverse_contiguous_periods(
            daily_stats_df, max_periods=max_periods_long, min_days=7, max_days=15, 
            target_hours=target_hours, scenario_type="long", 
            excluded_periods=short_periods + medium_periods
        )
        scenarios['long_spans'] = long_periods
        
        return scenarios
    
    def _calculate_original_composite_scores(self, daily_stats_df):
        """Calculate composite scores using original's superior 6-factor method"""
        
        # Normalize metrics for scoring (original approach)
        max_coverage_range = daily_stats_df['coverage_range'].max()
        max_balance_range = daily_stats_df['balance_range'].max()  
        max_surplus_hours = daily_stats_df['surplus_hours'].max()
        max_scarcity_hours = daily_stats_df['extreme_scarcity_hours'].max()
        max_peak_demand = daily_stats_df['peak_demand'].max()
        min_min_coverage = daily_stats_df['min_coverage'].min()
        max_max_coverage = daily_stats_df['max_coverage'].max()
        
        def calculate_score(row):
            # Score components (0-1 scale, higher = more representative) - ORIGINAL'S 6-FACTOR METHOD
            variability_score = row['coverage_range'] / max_coverage_range if max_coverage_range > 0 else 0
            extreme_high_score = row['max_coverage'] / max_max_coverage if max_max_coverage > 0 else 0
            extreme_low_score = (min_min_coverage / row['min_coverage']) if row['min_coverage'] > 0 else 1
            surplus_score = row['surplus_hours'] / max_surplus_hours if max_surplus_hours > 0 else 0
            scarcity_score = row['extreme_scarcity_hours'] / max_scarcity_hours if max_scarcity_hours > 0 else 0
            demand_score = row['peak_demand'] / max_peak_demand if max_peak_demand > 0 else 0
            
            # Original's weighted composite score - PROVEN APPROACH
            composite_score = (
                variability_score * 0.25 +    # Intraday variability
                extreme_high_score * 0.20 +   # Peak generation events
                extreme_low_score * 0.20 +    # Scarcity events
                surplus_score * 0.15 +        # Surplus events
                scarcity_score * 0.10 +       # Extended scarcity
                demand_score * 0.10           # High demand events
            )
            
            return composite_score
            
        daily_stats_df['composite_score'] = daily_stats_df.apply(calculate_score, axis=1)
        daily_stats_df = daily_stats_df.sort_values('composite_score', ascending=False)
        
        return daily_stats_df
    
    def _find_diverse_contiguous_periods(self, daily_stats_df, max_periods, min_days, max_days, target_hours, 
                                        scenario_type="short", excluded_periods=None):
        """Find optimal contiguous periods with temporal diversity across scenarios"""
        
        # Handle excluded periods to ensure no overlap between scenarios
        excluded_dates = set()
        if excluded_periods:
            for period in excluded_periods:
                # Mark a buffer around excluded periods to ensure separation
                start_month, start_day = period['start_month'], period['start_day']
                end_month, end_day = period['end_month'], period['end_day']
                
                # Add buffer days before and after each excluded period
                buffer_days = 7  # 1 week separation minimum
                start_day_index = self._month_day_to_day_index(start_month, start_day)
                end_day_index = self._month_day_to_day_index(end_month, end_day)
                
                for day_idx in range(max(0, start_day_index - buffer_days), 
                                   min(365, end_day_index + buffer_days + 1)):
                    month, day = self._day_index_to_month_day(day_idx)
                    excluded_dates.add(f"{month}-{day}")
        
        # Scenario-specific filtering for diversity
        filtered_df = daily_stats_df.copy()
        
        if scenario_type == "short":
            # SHORT: Focus on extreme variability and peak events across all seasons
            print("      Target: 5 periods, 1-3 days each, ~400 hours total")
            # Prefer days with high variability and extreme events
            filtered_df['scenario_score'] = (
                filtered_df['composite_score'] * 0.6 +
                (filtered_df['coverage_range'] / filtered_df['coverage_range'].max()) * 0.4
            )
            
        elif scenario_type == "medium":
            # MEDIUM: Focus on shoulder seasons and transitional periods
            print("      Target: 3 periods, 1-7 days each, ~400 hours total")
            # Prefer spring/fall months and moderate variability
            season_preference = filtered_df['month'].apply(lambda m: 
                1.5 if m in [3, 4, 5, 9, 10, 11] else 1.0)  # Spring/Fall preference
            filtered_df['scenario_score'] = (
                filtered_df['composite_score'] * 0.5 +
                season_preference * 0.3 +
                (1 - abs(filtered_df['coverage_range'] - filtered_df['coverage_range'].median()) / 
                 filtered_df['coverage_range'].max()) * 0.2
            )
            
        elif scenario_type == "long":
            # LONG: Focus on winter/summer extremes and extended stress periods
            print("      Target: 1 periods, 7-15 days each, ~400 hours total")
            # Prefer winter/summer months with sustained patterns
            season_preference = filtered_df['month'].apply(lambda m: 
                1.5 if m in [12, 1, 2, 6, 7, 8] else 0.8)  # Winter/Summer preference
            filtered_df['scenario_score'] = (
                filtered_df['composite_score'] * 0.4 +
                season_preference * 0.4 +
                (filtered_df['extreme_scarcity_hours'] / filtered_df['extreme_scarcity_hours'].max()) * 0.2
            )
        
        # Remove excluded dates from consideration
        if excluded_dates:
            mask = ~filtered_df.apply(lambda row: f"{int(row['month'])}-{int(row['day_in_month'])}" in excluded_dates, axis=1)
            filtered_df = filtered_df[mask]
        
        # Now use the enhanced selection logic
        return self._find_original_contiguous_periods(filtered_df, max_periods, min_days, max_days, target_hours)
    
    def _find_original_contiguous_periods(self, daily_stats_df, max_periods, min_days, max_days, target_hours):
        """Find optimal contiguous periods using original's proven algorithm"""
        
        periods = []
        used_days = set()
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        def get_next_day(month, day):
            """Get next day, handling month/year boundaries - ORIGINAL'S APPROACH"""
            if day < days_in_month[month - 1]:
                return month, day + 1
            elif month < 12:
                return month + 1, 1
            else:
                return 1, 1  # Wrap to next year
        
        def get_date_key(month, day):
            return f"{month}-{day}"
        
        # Sort by scenario-specific score if available, otherwise composite score
        sort_column = 'scenario_score' if 'scenario_score' in daily_stats_df.columns else 'composite_score'
        sorted_days = daily_stats_df.sort_values(sort_column, ascending=False)
        
        total_hours = 0
        period_count = 0
        
        # ORIGINAL'S ALGORITHM: Try to build periods starting from highest-scored days
        for _, start_day_row in sorted_days.iterrows():
            if period_count >= max_periods or total_hours >= target_hours:
                break
                
            start_month = int(start_day_row['month'])
            start_day = int(start_day_row['day_in_month'])
            start_date_key = get_date_key(start_month, start_day)
            
            if start_date_key in used_days:
                continue
            
            # Try different period lengths (prefer longer periods for sustainability)
            for period_length in range(max_days, min_days - 1, -1):
                if total_hours + (period_length * 24) > target_hours:
                    continue
                
                # Check if we can build a period of this length
                current_month, current_day = start_month, start_day
                period_days = []
                valid_period = True
                
                for day_offset in range(period_length):
                    current_date_key = get_date_key(current_month, current_day)
                    
                    if current_date_key in used_days:
                        valid_period = False
                        break
                    
                    period_days.append((current_month, current_day, current_date_key))
                    current_month, current_day = get_next_day(current_month, current_day)
                
                if valid_period:
                    # Mark all days as used
                    for month, day, date_key in period_days:
                        used_days.add(date_key)
                    
                    # Calculate period statistics
                    period_scores = []
                    period_coverage_ranges = []
                    
                    for month, day, date_key in period_days:
                        day_row = daily_stats_df[
                            (daily_stats_df['month'] == month) & 
                            (daily_stats_df['day_in_month'] == day)
                        ]
                        if not day_row.empty:
                            period_scores.append(day_row.iloc[0]['composite_score'])
                            period_coverage_ranges.append(day_row.iloc[0]['coverage_range'])
                    
                    period_info = {
                        'start_month': start_month,
                        'start_day': start_day,
                        'end_month': period_days[-1][0],
                        'end_day': period_days[-1][1],
                        'duration_days': period_length,
                        'duration_hours': period_length * 24,
                        'avg_score': np.mean(period_scores) if period_scores else 0,
                        'avg_coverage_range': np.mean(period_coverage_ranges) if period_coverage_ranges else 0,
                        'period_id': f"P{period_count + 1:02d}"
                    }
                    
                    periods.append(period_info)
                    total_hours += period_length * 24
                    period_count += 1
                    
                    print(f"      ✅ {period_info['period_id']}: {start_month:2d}/{start_day:2d} to "
                          f"{period_info['end_month']:2d}/{period_info['end_day']:2d} "
                          f"({period_length:2d} days, {period_length * 24:3d}h) - "
                          f"Score: {period_info['avg_score']:.3f}")
                    break  # Found a valid period, move to next starting day
        
        print(f"      📊 Selected {len(periods)} periods totaling {total_hours} hours")
        return periods
    
    # ==========================================
    # BASE AGGREGATION AND MAPPING METHODS
    # ==========================================
    
    def _create_base_aggregation(self, net_load, max_base_timeslices=48): 
        """Create intelligent base seasonal/daily aggregation using actual data patterns"""
        
        # Reshape to analyze patterns (8760 = 365 days × 24 hours)
        daily_net_load = net_load.reshape(365, 24)
        
        # SMART SEASONAL CLUSTERING - group by actual months with proper day counts
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # 2030 is not a leap year
        
        monthly_patterns = []
        day_start = 0
        
        for month in range(12):
            month_days = days_in_month[month]
            month_data = daily_net_load[day_start:day_start + month_days]
            
            monthly_patterns.append([
                month_data.mean(),           # Average net load
                month_data.max(),            # Peak net load  
                month_data.min(),            # Minimum net load
                month_data.std(),            # Variability
                month_data[:, 6:18].mean(),  # Daytime average
                month_data[:, 18:22].mean()  # Evening peak average
            ])
            
            day_start += month_days
        
        monthly_patterns = np.array(monthly_patterns)
        
        # Use clustering for seasons but ensure contiguous months
        # Use default values (this file doesn't have stress_periods_config integration)
        n_seasons = 4
        season_labels = self._contiguous_cluster(monthly_patterns, n_seasons, is_circular=True)
        
        # Create season names as S01, S02, S03, etc.
        season_names = [f'S{i+1:02d}' for i in range(n_seasons)]  # S01, S02, S03, S04, S05, S06
        months = {i+1: season_names[season_labels[i]] for i in range(12)}
        
        # SMART DAILY PERIOD CLUSTERING with contiguous hours
        hourly_patterns = []
        for hour in range(24):
            hour_data = daily_net_load[:, hour]
            hourly_patterns.append([
                hour_data.mean(),     # Average net load this hour
                hour_data.max(),      # Peak net load this hour
                hour_data.std(),      # Variability this hour
                np.percentile(hour_data, 95)  # 95th percentile
            ])
        
        hourly_patterns = np.array(hourly_patterns)
        
        # Use default daily periods
        n_daily_periods = 6
        daily_labels = self._contiguous_cluster(hourly_patterns, n_daily_periods, is_circular=True)
        
        # Create hour segment names as H01, H02, H03, etc.
        daily_names = [f'H{i+1:02d}' for i in range(n_daily_periods)]  # H01, H02, H03, H04, etc.
        hours = {i+1: daily_names[daily_labels[i]] for i in range(24)}
        
        total_combinations = n_seasons * n_daily_periods
        print(f"   🎯 Smart aggregation: {n_seasons} seasons (S01-S{n_seasons:02d}) × {n_daily_periods} hour periods (H01-H{n_daily_periods:02d}) = {total_combinations} base timeslices")
        
        return {'months': months, 'hours': hours}
    
    def _contiguous_cluster(self, data, n_clusters, is_circular=False):
        """Create contiguous clusters (adjacent months/hours stay together)"""
        if n_clusters >= len(data):
            return list(range(len(data)))
        
        n_items = len(data)
        
        # Calculate similarity between adjacent items
        similarities = []
        for i in range(n_items):
            next_i = (i + 1) % n_items if is_circular else min(i + 1, n_items - 1)
            if next_i != i:
                # Calculate distance between adjacent items
                dist = np.sqrt(np.sum((data[i] - data[next_i]) ** 2))
                similarities.append((i, next_i, dist))
        
        # Sort by similarity (smallest distance = most similar)
        similarities.sort(key=lambda x: x[2])
        
        # Create clusters by finding the best breakpoints
        break_points = set()
        n_breaks_needed = n_clusters - 1
        
        # Take the largest distances as break points
        for i in range(len(similarities) - n_breaks_needed, len(similarities)):
            if i >= 0:
                break_points.add(similarities[i][1])  # Add the start of next segment
        
        # Assign cluster labels ensuring contiguity
        labels = []
        current_cluster = 0
        
        for i in range(n_items):
            labels.append(current_cluster)
            if i + 1 in break_points:
                current_cluster += 1
        
        return labels
    
    def _generate_mapping(self, base_scheme, segments, scenario_name): 
        """Generate final timeslice mapping table"""
        mapping = []
        
        # Add month mappings
        for month, season in base_scheme['months'].items():
            mapping.append({
                'description': 'month',
                'sourcevalue': f'{month:02d}',
                'timeslice': season
            })
        
        # Add hour mappings  
        for hour, period in base_scheme['hours'].items():
            mapping.append({
                'description': 'hour',
                'sourcevalue': f'{hour:02d}',
                'timeslice': period
            })
        
        # Sort segments by start date to ensure chronological order
        sorted_segments = sorted(segments, key=lambda x: x[0])  # Sort by start_day
        
        # Add advanced segments - ONLY start and end dates for each segment
        # Start from 'b' since 'a' is reserved for aggregated slices
        for i, (start_day, end_day) in enumerate(sorted_segments):
            segment_letter = chr(ord('b') + i)  # This will be chronological: b, c, d, e...
            
            # Convert day numbers to mm-dd format with proper year wrapping
            start_month, start_day_in_month = self._day_index_to_month_day(start_day)
            end_month, end_day_in_month = self._day_index_to_month_day(end_day)
            
            # Add start date
            mapping.append({
                'description': 'adv',
                'sourcevalue': segment_letter,
                'timeslice': f"{start_month:02d}-{start_day_in_month:02d}"
            })
            
            # Add end date
            mapping.append({
                'description': 'adv',
                'sourcevalue': segment_letter,
                'timeslice': f"{end_month:02d}-{end_day_in_month:02d}"
            })
        
        return pd.DataFrame(mapping)
    
    def _create_consolidated_tsdesign(self, iso_code, scenario_mappings, output_dir):
        """Create consolidated tsdesign file with all scenarios in one table"""
        
        # Expected scenario order for the main VerveStacks script
        expected_scenarios = ['triple_1', 'triple_5', 'weekly_stress']
        
        consolidated_rows = []
        
        # Step 1: Add common month and hour mappings (these are identical across scenarios)
        first_scenario = list(scenario_mappings.values())[0]
        
        # Add months (identical across all scenarios)
        for _, row in first_scenario.iterrows():
            if row['description'] == 'month':
                new_row = {'description': 'month', 'sourcevalue': row['sourcevalue']}
                for scenario_name in expected_scenarios:
                    new_row[scenario_name] = row['timeslice']  # Same for all scenarios
                consolidated_rows.append(new_row)
        
        # Add hours (identical across all scenarios)  
        for _, row in first_scenario.iterrows():
            if row['description'] == 'hour':
                new_row = {'description': 'hour', 'sourcevalue': row['sourcevalue']}
                for scenario_name in expected_scenarios:
                    new_row[scenario_name] = row['timeslice']  # Same for all scenarios
                consolidated_rows.append(new_row)
        
        # Step 2: Handle advanced periods - collect all periods from all scenarios
        all_adv_periods = {}  # {scenario: [(segment_letter, [start_date, end_date])]}
        
        for scenario_name, mapping_df in scenario_mappings.items():
            if scenario_name not in expected_scenarios:
                continue
                
            adv_rows = mapping_df[mapping_df['description'] == 'adv']
            periods = {}
            
            for _, row in adv_rows.iterrows():
                segment = row['sourcevalue']
                date = row['timeslice']
                
                if segment not in periods:
                    periods[segment] = []
                periods[segment].append(date)
            
            all_adv_periods[scenario_name] = periods
        
        # Step 3: Create unified advanced period structure
        # Get all unique segment letters across all scenarios
        all_segments = set()
        for scenario_periods in all_adv_periods.values():
            all_segments.update(scenario_periods.keys())
        
        # Sort segments alphabetically  
        sorted_segments = sorted(all_segments)
        
        # Add advanced period rows (two rows per segment: start and end)
        for segment in sorted_segments:
            # Each segment gets exactly 2 rows
            for row_idx in [0, 1]:  # 0=start date, 1=end date
                new_row = {'description': 'adv', 'sourcevalue': segment}
                
                for scenario_name in expected_scenarios:
                    if (scenario_name in all_adv_periods and 
                        segment in all_adv_periods[scenario_name] and
                        len(all_adv_periods[scenario_name][segment]) > row_idx):
                        new_row[scenario_name] = all_adv_periods[scenario_name][segment][row_idx]
                    else:
                        new_row[scenario_name] = ''  # Empty if scenario doesn't have this segment/row
                
                consolidated_rows.append(new_row)
        
        # Convert to DataFrame
        consolidated_df = pd.DataFrame(consolidated_rows)
        
        # Reorder columns
        column_order = ['description', 'sourcevalue'] + expected_scenarios
        consolidated_df = consolidated_df[column_order]
        
        # Save consolidated file
        filename = f"{output_dir}tsdesign_{iso_code}.csv"
        consolidated_df.to_csv(filename, index=False)
        
        # Print summary
        month_rows = len(consolidated_df[consolidated_df['description'] == 'month'])
        hour_rows = len(consolidated_df[consolidated_df['description'] == 'hour'])
        adv_rows = len(consolidated_df[consolidated_df['description'] == 'adv'])
        adv_segments = adv_rows // 2  # 2 rows per segment
        
        print(f"       📋 Consolidated tsdesign: {month_rows} months + {hour_rows} hours + {adv_segments} advanced segments ({adv_rows} rows)")
        
        return filename
    
    def _day_index_to_month_day(self, day_index):
        """Convert day index (0-364) to proper month and day with year wrapping"""
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Handle year wrapping - if day_index >= 365, wrap to next year
        day_index = day_index % 365
        
        cumulative_days = 0
        for month, days in enumerate(days_in_month, 1):
            if day_index < cumulative_days + days:
                day_in_month = day_index - cumulative_days + 1
                return month, day_in_month
            cumulative_days += days
        
        # Fallback (shouldn't happen with proper modulo)
        return 12, 31
    
    def _month_day_to_day_index(self, month, day):
        """Convert month and day to day index (0-364)"""
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        day_index = 0
        for m in range(month - 1):
            day_index += days_in_month[m]
        day_index += day - 1
        
        return min(day_index, 364)  # Ensure we don't exceed 364
    
    def _count_timeslices(self, mapping):
        """Count total timeslices"""
        # Count unique season-hour combinations
        month_timeslices = set(mapping[mapping['description'] == 'month']['timeslice'])
        hour_timeslices = set(mapping[mapping['description'] == 'hour']['timeslice'])
        base_combinations = len(month_timeslices) * len(hour_timeslices)
        
        # Count advanced segment hours
        adv_rows = len(mapping[mapping['description'] == 'adv'])
        adv_segments = adv_rows // 2  # 2 rows per segment (start/end dates)
        
        # Estimate total hours (this is approximate since we don't parse actual dates)
        estimated_hours_per_segment = 48  # Assume average 2-day segments
        total_adv_hours = adv_segments * estimated_hours_per_segment
        
        return base_combinations + total_adv_hours
    
    # ==========================================
    # SYNTHETIC DATA GENERATORS FOR TESTING
    # ==========================================
    
    def _create_synthetic_demand(self): 
        """Create synthetic demand data for testing"""
        np.random.seed(42)  # For reproducibility
        
        # Create realistic demand patterns
        hours = np.arange(8760)
        
        # Base seasonal pattern
        seasonal = 50000 + 10000 * np.sin(2 * np.pi * hours / (365 * 24) - np.pi/2)
        
        # Daily pattern 
        daily = 15000 * np.sin(2 * np.pi * (hours % 24) / 24 - np.pi/3)
        
        # Random variation
        noise = np.random.normal(0, 5000, 8760)
        
        # Combine patterns
        demand_deu = np.maximum(seasonal + daily + noise, 10000)  # Minimum 10 GW
        demand_usa = demand_deu * 8 + np.random.normal(0, 20000, 8760)  # Larger, more variable
        
        return pd.DataFrame({
            'DEU': demand_deu,
            'USA': np.maximum(demand_usa, 50000)  # Minimum 50 GW
        })
    
    def _create_synthetic_existing_gen(self): 
        """Create synthetic existing generation data"""
        return {
            'DEU': {'solar': 45.0, 'wind': 55.0, 'hydro': 25.0},
            'USA': {'solar': 75.0, 'wind': 125.0, 'hydro': 80.0}
        }
    
    def _create_synthetic_renewable_potential(self): 
        """Create synthetic renewable potential data"""
        np.random.seed(42)
        
        # Create variety of renewable resources with different capacity factors
        data = []
        
        for iso in ['DEU', 'USA']:
            # Solar resources (lower CF, lower cost)
            for i in range(10):
                cf = 0.10 + i * 0.02  # 10% to 28% CF
                capacity = 50 + np.random.uniform(0, 100)  # 50-150 GW
                lcoe = self._calculate_lcoe('solar', cf, capacity, iso)
                
                data.append({
                    'process': f'EN_SPV_{i:02d}_{iso}',
                    'iso': iso,
                    'CAP_BND': capacity,
                    'AF~FX': cf,
                    'Comm-IN': 'solar',
                    'tech_type': 'solar',
                    'mwh_potential': capacity * cf * 8760,
                    'lcoe': lcoe
                })
            
            # Wind resources (higher CF, higher cost)
            for i in range(10):
                cf = 0.25 + i * 0.05  # 25% to 70% CF
                capacity = 30 + np.random.uniform(0, 80)  # 30-110 GW
                lcoe = self._calculate_lcoe('wind', cf, capacity, iso)
                
                data.append({
                    'process': f'EN_WON_{i:02d}_{iso}',
                    'iso': iso,
                    'CAP_BND': capacity,
                    'AF~FX': cf,
                    'Comm-IN': 'wind',
                    'tech_type': 'wind',
                    'mwh_potential': capacity * cf * 8760,
                    'lcoe': lcoe
                })
        
        return pd.DataFrame(data)
    
    
    def _create_synthetic_renewable_shapes(self): 
        """Create synthetic renewable generation shapes"""
        np.random.seed(42)
        
        data = []
        
        for iso in ['DEU', 'USA']:
            for hour in range(8760):
                # Solar pattern - peaks around midday, zero at night
                hour_of_day = hour % 24
                day_of_year = hour // 24
                
                # Solar: sine wave peaking at noon, scaled by season
                solar_daily = np.maximum(0, np.sin(np.pi * (hour_of_day - 6) / 12))
                solar_seasonal = 0.7 + 0.3 * np.sin(2 * np.pi * day_of_year / 365 - np.pi/2)
                solar_fraction = solar_daily * solar_seasonal / 8760
                
                # Wind: more variable, some seasonal pattern
                wind_base = 0.3 + 0.2 * np.sin(2 * np.pi * day_of_year / 365)
                wind_variation = np.random.uniform(0.5, 1.5)
                wind_fraction = wind_base * wind_variation / 8760
                
                data.append({
                    'iso': iso,
                    'month': (day_of_year // 30) + 1,
                    'day': (day_of_year % 30) + 1,
                    'hour': hour_of_day,
                    'com_fr_solar': solar_fraction,
                    'com_fr_wind': wind_fraction
                })
        
        return pd.DataFrame(data)
    
    def _create_synthetic_hydro_patterns(self): 
        """Create synthetic hydro seasonality patterns"""
        # Typical hydro pattern: high in spring (snowmelt), low in late summer/fall
        monthly_patterns = {
            'DEU': [2.0, 1.8, 2.5, 3.2, 3.8, 2.8, 1.9, 1.5, 1.3, 1.7, 2.1, 2.3],
            'USA': [8.5, 7.2, 9.8, 12.1, 14.5, 10.2, 6.8, 5.1, 4.2, 5.9, 7.8, 8.9]
        }
        
        data = []
        for country, pattern in monthly_patterns.items():
            for month, value in enumerate(pattern, 1):
                data.append({
                    'Country code': country,
                    'month': month,
                    'Value': value
                })
        
        return pd.DataFrame(data)


# ==================================================
# MAIN EXECUTION AND USAGE EXAMPLE
# ==================================================

if __name__ == "__main__":
    import sys
    
    print("🌟 VerveStacks Timeslice Processor - HYBRID EDITION")
    print("🔄 Combining v5's data-driven capacity with original's superior period selection")
    print("✅ Features: Country-specific RE capacity")
    print()
    
    # Parse command line arguments for ISO codes
    if len(sys.argv) > 1:
        target_isos = sys.argv[1].split(',')
        print(f"📋 Using command line ISOs: {target_isos}")
    else:
        target_isos = ['IND']  # Default demo ISO
        print(f"📋 Using default demo ISO: {target_isos}")
        print("💡 Usage: python RE_Shapes_Analysis_v5.py USA,DEU,CHN")
    
    # Initialize processor with configuration support
    processor = VerveStacksTimesliceProcessor(
        max_timeslices=None,  # Will use config file value
        data_path="../data/",  # Relative to 2_ts_design folder
        config_path="./config/"
    )
    
    # Run with enhanced hybrid approach
    print("🚀 Running hybrid approach with original's period selection logic...")
    results = processor.run_full_pipeline(
        target_isos=target_isos, 
        save_results=True,
        output_dir="./outputs/"
    )
    
    print("\n" + "="*60)
    print("🎯 HYBRID OUTPUT STRUCTURE:")
    print("./outputs/")
    print("├── timeslices_ISO_short_spans.csv")  
    print("├── timeslices_ISO_medium_spans.csv")  
    print("├── timeslices_ISO_long_spans.csv")  
    print("├── segment_summary_ISO.csv")
    print("├── RE_scenarios_hourly_ISO.png (Clean original style)")
    print("├── aggregation_justification_ISO.svg")
    print("├── season_clusters_ISO.csv")
    print("├── period_clusters_ISO.csv")
    print("└── individual_scenarios/")
    print("    └── ISO_scenario_detailed.png (3 per ISO)")
    print("\n🎉 Hybrid VerveStacks processor ready!")
    print("🔥 Best of both worlds: v5's data pipeline + original's period selection!")
    print("📊 RE coverage-based analysis with country-specific renewable capacity building")
    print("📈 Historical deployment ratios ensure realistic solar/wind technology mix")
    print("🏔️ Now with integrated hydro generation in all plots and analysis! ⚡")
    print("💰 Enhanced LCOE calculations with financing, asset life, and O&M costs! 📊")
    print("🏛️ Realistic solar/wind mix based on historical deployment patterns (IRENASTAT-G)! 📈")