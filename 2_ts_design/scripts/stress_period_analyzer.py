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
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime, timedelta
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib not available - plots will be skipped")

# Import branding manager for professional styling
try:
    from branding_manager import VerveStacksBrandingManager
    branding_manager = VerveStacksBrandingManager()
    BRANDING_AVAILABLE = True
except ImportError:
    BRANDING_AVAILABLE = False
    print("⚠️  branding_manager not available - plots will not have branding")

# Using robust centralized branding system

try:
    from enhanced_lcoe_calculator import EnhancedLCOECalculator
    ENHANCED_LCOE_AVAILABLE = True
except ImportError:
    ENHANCED_LCOE_AVAILABLE = False

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
    
    def __init__(self, max_timeslices=500, data_path="./data/", use_enhanced_lcoe=True, config_path="./config/", force_reload=False):
        # Load configuration files
        self.config_path = config_path
        self.config = self._load_configuration()
        
        # Apply configuration with parameter overrides
        self.max_timeslices = max_timeslices or self.config.get('max_timeslices', 500)
        self.base_aggregates = 12  # 4 seasons x 3 daily periods
        self.data_path = data_path
        self.force_reload = force_reload
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
        # self.load_all_data()  # Disabled - using 8760 constructor data instead
    
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
    
    def process_iso(self, iso_code, save_outputs=False, output_dir=None):
        """
        Process a single ISO and generate all timeslice scenarios using improved 8760 constructor
        
        This is where the magic happens - transforming our improved renewable profiles into 
        intelligent temporal structures for each ISO's unique characteristics
        """
        print(f"\n🎯 Processing {iso_code} - Building adaptive timeslices...")
        
        # Set default output directory if not provided
        if output_dir is None:
            current_script_dir = Path(__file__).parent.absolute()
            output_dir = current_script_dir.parent / "outputs" / iso_code
        else:
            output_dir = Path(output_dir)
        
        # Step 1: Get comprehensive profiles from our improved 8760 constructor
        # Import the 8760 constructor (handle numeric module name)
        import importlib.util
        script_dir = Path(__file__).parent.absolute()
        supply_constructor_path = script_dir / "8760_supply_demand_constructor.py"
        
        spec = importlib.util.spec_from_file_location("supply_constructor", supply_constructor_path)
        supply_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(supply_module)
        Supply8760Constructor = supply_module.Supply8760Constructor
        
        # Use the same data path - it's auto-detected now
        constructor = Supply8760Constructor(self.data_path, force_reload=self.force_reload)
        profiles = constructor.construct_8760_profiles(iso_code)
        
        # Create charts and save to output directory
        if save_outputs:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create supply curve chart
            supply_curve_chart_path = output_dir / f"supply_curves_{iso_code}.svg"
            supply_curve_path = constructor.create_supply_curve_chart(iso_code, output_path=str(supply_curve_chart_path), use_estimated_lcoe=True)
            print(f"   ✅ Supply curve chart saved")
            
            # Create quarterly charts - TEMPORARILY DISABLED
            # quarterly_chart_path = output_dir / f"quarterly_charts_{iso_code}.png"
            # quarterly_path = constructor.create_quarterly_charts(profiles, iso_code, output_path=str(quarterly_chart_path), show_chart=False)
            # print(f"   ✅ Quarterly charts saved")
            
        print(f"   📁 Charts saved to: {output_dir}")
        
        if not profiles:
            print(f"❌ Failed to construct profiles for {iso_code}")
            return None
        
        # Step 2: Extract coverage for scenario generation (the key bridge metric)
        coverage = profiles['coverage']  # This includes nuclear now - perfect for stress analysis
        print(f"   📊 Coverage range: {coverage.min():.1f}% to {coverage.max():.1f}%")
        
        # Step 3: Calculate net load from our profiles
        net_load = profiles['net_load']
        print(f"   ⚡ Net load range: {net_load.min():.0f} to {net_load.max():.0f} MW")
        
        # Step 4: Generate critical periods using statistical approaches with our coverage
        print(f"   📊 Generating critical periods using statistical methods...")
        
        # Generate all stress configurations from VS_mappings (replaces hardcoded calls)
        scenarios, scenario_configs = self._generate_all_stress_configurations(coverage)
        
        # Also generate the old method for comparison (optional)
        # scenarios_old = self._generate_three_span_scenarios(iso_data, renewable_supply, target_hours=400)
        # scenarios.update(scenarios_old)
        
        # Step 5 & 6: Create scenario-specific base aggregations and mappings
        scenario_mappings = {}
        scenario_base_schemes = {}
        
        print(f"   🎯 Creating dynamic base aggregations for {len(scenarios)} scenarios...")
        
        for scenario_name, periods in scenarios.items():
            print(f"   📊 Processing {scenario_name}...")
            
            # Get configuration for this scenario
            config = scenario_configs.get(scenario_name, {})
            
            # Convert original's period format to segments format for mapping
            segments = []
            for period in periods:
                # Convert month/day to day index
                start_day_index = self._month_day_to_day_index(period['start_month'], period['start_day'])
                end_day_index = self._month_day_to_day_index(period['end_month'], period['end_day'])
                segments.append((start_day_index, end_day_index))
            
            # Create scenario-specific base aggregation
            base_scheme = self._create_scenario_base_aggregation(net_load, scenario_name, periods, segments, config)
            scenario_base_schemes[scenario_name] = base_scheme
            
            # Generate mapping using scenario-specific base scheme
            mapping = self._generate_mapping(base_scheme, segments, scenario_name)
            scenario_mappings[scenario_name] = mapping
            
            timeslice_count = self._count_timeslices(mapping)
            total_hours = sum(period['duration_hours'] for period in periods)
            print(f"      ✅ {scenario_name}: {len(periods)} periods, {total_hours} hours, {timeslice_count} timeslices")
        
        # Step 7: Save outputs if requested (NO DUPLICATION)
        if save_outputs:
            print(f"   💾 Saving outputs for {iso_code}...")
            
            # Save individual timeslice mappings
            for scenario_name, mapping_df in scenario_mappings.items():
                filename = output_dir / f"timeslices_{iso_code}_{scenario_name}.csv"
                mapping_df.to_csv(filename, index=False)
                print(f"     ✅ {filename}")
            
            # Create consolidated tsdesign file
            consolidated_filename = self._create_consolidated_tsdesign(iso_code, scenario_mappings, scenario_base_schemes, output_dir)
            print(f"     🎯 {consolidated_filename}")
            
            # Create and save segment summary
            segment_summary = self._create_segment_summary(iso_code, scenarios, output_dir)
            
            
            # Prepare data structures for plotting (match original RSA format)
            renewable_supply = {
                'hourly_total': profiles['renewable_total'],
                'hourly_solar': profiles['solar'],
                'hourly_wind': profiles['wind'],
                'hourly_hydro': profiles['hydro'],
                'hourly_nuclear': profiles['nuclear']
            }
            iso_data = {
                'demand': profiles['demand']
            }
            
             # Save daily coverage data for enhanced calendar visualization
            self._save_daily_coverage_json(iso_code, renewable_supply, iso_data, output_dir)
            
            # Generate calendar charts
            self._generate_calendar_charts(iso_code, output_dir)
            
            # Create all plots in one organized call with scenario-specific base schemes
            self._create_all_plots(iso_code, net_load, renewable_supply, iso_data, 
                                 scenarios, scenario_base_schemes, output_dir)
        
        return scenario_mappings, {
            'iso_data': iso_data,
            'renewable_supply': renewable_supply, 
            'net_load': net_load,
            'scenarios': scenarios,
            'scenario_base_schemes': scenario_base_schemes
        }
    
    def _create_all_plots(self, iso_code, net_load, renewable_supply, iso_data, 
                         scenarios, scenario_base_schemes, output_dir):
        """Create all plots for an ISO in one organized function with scenario-specific base schemes"""
        if not MATPLOTLIB_AVAILABLE:
            print("⚠️  matplotlib not available - skipping plots")
            return
        
        print(f"   📊 Creating comprehensive visualization suite for {iso_code}...")
        
        try:
            # 1. Annual summary analysis
            try:
                self._create_re_analysis_summary(iso_code, renewable_supply, iso_data, output_dir)
                print(f"   📊 Annual summary analysis completed for {iso_code}")
            except Exception as e:
                print(f"   ❌ Error creating summary analysis for {iso_code}: {e}")
            
            # 2. Statistical scenario analysis plots
            self._plot_statistical_scenarios(iso_code, iso_data, renewable_supply, 
                                           scenarios, output_dir)
            
            # 3. Scenario-specific aggregation justification plots
            self._plot_scenario_aggregation_justifications(iso_code, net_load, scenario_base_schemes, output_dir)
            
            # 4. Individual scenario plots (disabled - has known error and creates empty folders)
            # try:
            #     self._plot_individual_scenarios(iso_code, net_load, renewable_supply, 
            #                                   scenarios, output_dir)
            # except Exception as e:
            #     print(f"   ⚠️ Individual scenario plots skipped for {iso_code}: {e}")
            print(f"   ⚠️ Individual scenario plots disabled (creates empty folders)")
            
            print(f"   ✅ All plots completed for {iso_code}")
            
        except Exception as e:
            print(f"   ❌ Error creating plots for {iso_code}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _plot_statistical_scenarios(self, iso_code, iso_data, renewable_supply, scenarios, output_dir):
        """Plot statistical scenario analysis based on configuration settings"""
        
        print(f"   📊 Creating statistical scenario plots...")
        
        # Load configuration to check which scenarios should have plots
        config_df = self._load_stress_configurations()
        
        # Plot each scenario that has create_plot=True
        import pandas as pd
        for _, config in config_df.iterrows():
            config_name = config['name']
            should_plot = config.get('create_plot', False) if pd.notna(config.get('create_plot', False)) else False
            
            if should_plot and config_name in scenarios:
                print(f"   🎨 Creating plot for {config_name}...")
                
                # Check if configuration has daily and/or weekly parameters
                has_daily = self._has_daily_stress_params(config)
                has_weekly = self._has_weekly_stress_params(config)
                
                if has_daily and has_weekly:
                    # MIXED configuration: create a combined plot
                    print(f"   🎨 Creating mixed plot for {config_name} (daily + weekly)")
                    self._plot_mixed_stress_scenario(iso_code, iso_data, renewable_supply, scenarios[config_name], output_dir, config_name)
                elif has_daily:
                    # DAILY-only configuration
                    self._plot_daily_stress_scenario(iso_code, iso_data, renewable_supply, scenarios[config_name], output_dir, config_name)
                elif has_weekly:
                    # WEEKLY-only configuration
                    self._plot_weekly_stress_scenario(iso_code, iso_data, renewable_supply, scenarios[config_name], output_dir, config_name)
        
        print(f"   ✅ Statistical scenario plots completed for {iso_code}")

    def _plot_daily_stress_scenario(self, iso_code, iso_data, renewable_supply, periods, output_dir, config_name):
        """
        Plot daily stress scenario using EXACT same logic as existing plotting functions.
        Works for any daily configuration (triple_1, triple_5, custom combinations).
        """
        # Use existing triple_5 plotting logic for any daily stress configuration
        # (The plotting logic is the same regardless of how many days are selected)
        self._plot_plan2_triple_5(iso_code, iso_data, renewable_supply, periods, output_dir, config_name)

    def _plot_weekly_stress_scenario(self, iso_code, iso_data, renewable_supply, periods, output_dir, config_name):
        """
        Plot weekly stress scenario using EXACT same logic as existing plotting functions.
        Works for any weekly configuration (weekly_stress, custom combinations).
        """
        # Use existing weekly_stress plotting logic for any weekly stress configuration
        # (The plotting logic is the same regardless of how many weeks are selected)
        self._plot_plan3_weekly_stress(iso_code, iso_data, renewable_supply, periods, output_dir, config_name)

    def _plot_mixed_stress_scenario(self, iso_code, iso_data, renewable_supply, periods, output_dir, config_name):
        """
        Plot mixed stress scenario (combination of daily and weekly periods).
        Separates periods by category and uses appropriate plotting logic for each.
        """
        # Separate daily and weekly periods
        daily_periods = [p for p in periods if p.get('duration_days', 1) == 1]
        weekly_periods = [p for p in periods if p.get('duration_days', 1) > 1]
        
        # Plot daily periods if any exist
        if daily_periods:
            print(f"   📊 Plotting {len(daily_periods)} daily components of {config_name}...")
            self._plot_plan2_triple_5(iso_code, iso_data, renewable_supply, daily_periods, output_dir, f"{config_name}_daily")
        
        # Plot weekly periods if any exist  
        if weekly_periods:
            print(f"   📊 Plotting {len(weekly_periods)} weekly components of {config_name}...")
            self._plot_plan3_weekly_stress(iso_code, iso_data, renewable_supply, weekly_periods, output_dir, f"{config_name}_weekly")

    def _plot_plan2_triple_5(self, iso_code, iso_data, renewable_supply, periods, output_dir, config_name=None):
        """Plot Plan #2: Triple-5 scenario analysis with three category panels"""
        
        demand = iso_data['demand']
        re_supply = renewable_supply['hourly_total']
        hydro_supply = renewable_supply['hourly_hydro']
        solar_supply = renewable_supply['hourly_solar']
        wind_supply = renewable_supply['hourly_wind']
        nuclear_supply = renewable_supply['hourly_nuclear']
        
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
        
        # Apply branding to all subplots
        if BRANDING_AVAILABLE:
            for ax in axes:
                branding_manager.apply_chart_style(ax, "scenario_analysis")
            
            # Apply figure-level styling
            branding_manager.apply_figure_style(fig)
        
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
                period_nuclear = [nuclear_supply[h] / 1000 for h in hours]
                period_hydro = [hydro_supply[h] / 1000 for h in hours]
                period_wind = [wind_supply[h] / 1000 for h in hours]
                period_solar = [solar_supply[h] / 1000 for h in hours]
                
                # Create x-axis (hours within day)
                x_hours = list(range(24))
                x_offset = i * 25  # Offset each day by 25 hours for spacing
                x_plot = [x + x_offset for x in x_hours]
                
                # Import standard energy sector colors
                from energy_colors import ENERGY_COLORS
                
                # Plot stacked areas (nuclear at bottom as baseload)
                ax.fill_between(x_plot, 0, period_nuclear, alpha=0.8, color=ENERGY_COLORS['nuclear'], label='Nuclear' if i == 0 else "")
                ax.fill_between(x_plot, period_nuclear, 
                               [period_nuclear[j] + period_hydro[j] for j in range(24)], 
                               alpha=0.8, color=ENERGY_COLORS['hydro'], label='Hydro' if i == 0 else "")
                ax.fill_between(x_plot, [period_nuclear[j] + period_hydro[j] for j in range(24)], 
                               [period_nuclear[j] + period_hydro[j] + period_wind[j] for j in range(24)], 
                               alpha=0.8, color=ENERGY_COLORS['wind'], label='Wind' if i == 0 else "")
                ax.fill_between(x_plot, [period_nuclear[j] + period_hydro[j] + period_wind[j] for j in range(24)],
                               [period_nuclear[j] + period_hydro[j] + period_wind[j] + period_solar[j] for j in range(24)], 
                               alpha=0.8, color=ENERGY_COLORS['solar'], label='Solar' if i == 0 else "")
                
                # Plot demand line
                ax.plot(x_plot, period_demand, color='black', linewidth=2, 
                       label='Demand' if i == 0 else "", linestyle='--')
                
                # Add coverage percentage label (keep the metric on chart as requested)
                max_y = max(max(period_demand), 
                           max([period_nuclear[j] + period_hydro[j] + period_wind[j] + period_solar[j] for j in range(24)]))
                ax.text(x_offset + 12, max_y * 1.05,
                       f"Avg: {period['avg_coverage']:.0f}%",
                       ha='center', va='bottom', fontsize=7, alpha=0.6,
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.6))
            
            ax.set_title(titles[category], color=colors[category])
            ax.set_ylabel('Power (GW)')
            ax.grid(True, alpha=0.3)
            
            # Set x-axis labels with actual dates
            if cat_periods:
                max_hours = len(cat_periods) * 25
                ax.set_xlim(0, max_hours)
                ax.set_xticks([i * 25 + 12 for i in range(len(cat_periods))])
                # Use actual dates on x-axis in Mar30 format
                date_labels = [self._format_date_mmmdd(period['start_month'], period['start_day']) for period in cat_periods]
                ax.set_xticklabels(date_labels, rotation=45)
        
        # Finalize chart styling after all elements are set
        if BRANDING_AVAILABLE:
            for ax in axes:
                branding_manager.finalize_chart_style(ax)
        
        # Create common legend for all subplots
        handles = [
            plt.Rectangle((0,0),1,1, color=ENERGY_COLORS['nuclear'], alpha=0.8, label='Nuclear'),
            plt.Rectangle((0,0),1,1, color=ENERGY_COLORS['hydro'], alpha=0.8, label='Hydro'),
            plt.Rectangle((0,0),1,1, color=ENERGY_COLORS['wind'], alpha=0.8, label='Wind'),
            plt.Rectangle((0,0),1,1, color=ENERGY_COLORS['solar'], alpha=0.8, label='Solar'),
            plt.Line2D([0], [0], color='black', linewidth=2, linestyle='--', label='Demand')
        ]
        
        # Position legend at the bottom center of the figure
        fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, 0.02), 
                  ncol=5, frameon=True, fancybox=True)
        
        plt.tight_layout()
        
        # Adjust subplot layout to prevent legend from cropping x-axis labels
        plt.subplots_adjust(bottom=0.15)
        
        # Add branding logos and main title
        if BRANDING_AVAILABLE:
            branding_manager.add_logos_to_chart(fig, "small", f"Critical Days Analysis - {self._get_country_name(iso_code)}")
        
        # Save plot
        plot_name = config_name if config_name else "triple_5"
        filename = f"stress_periods_{plot_name}_{iso_code}.svg"
        filepath = Path(output_dir) / filename
        plt.savefig(filepath, format='svg', bbox_inches='tight', pad_inches=0.2)
        plt.close()
        
        print(f"      ✅ Plan #2 plot saved: {filename}")
    
    def _plot_plan3_weekly_stress(self, iso_code, iso_data, renewable_supply, periods, output_dir, config_name=None):
        """Plot Plan #3: Weekly Stress scenario analysis"""
        
        # Import standard energy sector colors
        from energy_colors import ENERGY_COLORS
        
        demand = iso_data['demand']
        re_supply = renewable_supply['hourly_total']
        hydro_supply = renewable_supply['hourly_hydro']
        solar_supply = renewable_supply['hourly_solar']  
        wind_supply = renewable_supply['hourly_wind']
        nuclear_supply = renewable_supply['hourly_nuclear']
        
        # Create figure with standardized size but adaptive to content
        # Use standard height for up to 2 periods, then scale moderately
        if len(periods) <= 2:
            fig_height = 7  # Standard height
        else:
            fig_height = min(7 + 2 * (len(periods) - 2), 15)  # Scale but cap at 15
        
        fig, axes = plt.subplots(len(periods), 1, figsize=(11, fig_height))
        if len(periods) == 1:
            axes = [axes]
            
        fig.suptitle(f'Plan #3: Weekly Sustained Stress Analysis - {iso_code}')
        
        # Apply branding to all subplots
        if BRANDING_AVAILABLE:
            for ax in axes:
                branding_manager.apply_chart_style(ax, "scenario_analysis")
            
            # Apply figure-level styling
            branding_manager.apply_figure_style(fig)
        
        for idx, period in enumerate(periods):
            ax = axes[idx]
            
            # Get week start/end day indices
            start_day = self._month_day_to_day_index(period['start_month'], period['start_day'])
            end_day = self._month_day_to_day_index(period['end_month'], period['end_day'])
            
            # Get all hours in this week
            hours = range(start_day * 24, (end_day + 1) * 24)
            
            # Convert to GW for plotting
            week_demand = [demand[h] / 1000 for h in hours]
            week_nuclear = [nuclear_supply[h] / 1000 for h in hours]
            week_hydro = [hydro_supply[h] / 1000 for h in hours]  
            week_wind = [wind_supply[h] / 1000 for h in hours]
            week_solar = [solar_supply[h] / 1000 for h in hours]
            
            # Create x-axis (hours in week)
            x_hours = list(range(len(hours)))
            
            # Plot stacked areas (nuclear at bottom as baseload)
            ax.fill_between(x_hours, 0, week_nuclear, alpha=0.8, color=ENERGY_COLORS['nuclear'], label='Nuclear')
            ax.fill_between(x_hours, week_nuclear, 
                           [week_nuclear[i] + week_hydro[i] for i in range(len(hours))], 
                           alpha=0.8, color=ENERGY_COLORS['hydro'], label='Hydro')
            ax.fill_between(x_hours, [week_nuclear[i] + week_hydro[i] for i in range(len(hours))], 
                           [week_nuclear[i] + week_hydro[i] + week_wind[i] for i in range(len(hours))], 
                           alpha=0.8, color=ENERGY_COLORS['wind'], label='Wind')
            ax.fill_between(x_hours, [week_nuclear[i] + week_hydro[i] + week_wind[i] for i in range(len(hours))],
                           [week_nuclear[i] + week_hydro[i] + week_wind[i] + week_solar[i] for i in range(len(hours))], 
                           alpha=0.8, color=ENERGY_COLORS['solar'], label='Solar')
            
            # Plot demand line
            ax.plot(x_hours, week_demand, color='black', linewidth=2, label='Demand', linestyle='--')
            
            # Add day separators
            for day in range(1, period['duration_days']):
                ax.axvline(x=day * 24, color='gray', linestyle=':', alpha=0.5)
            
            start_date = self._format_date_mmmdd(period['start_month'], period['start_day'])
            end_date = self._format_date_mmmdd(period['end_month'], period['end_day'])
            ax.set_title(f"Week {idx+1}: {start_date} - {end_date} "
                        f"(Avg Coverage: {period['avg_coverage']:.1f}%)", 
                        color='#d73027')
            ax.set_ylabel('Power (GW)')
            ax.grid(True, alpha=0.3)
            
            # Set x-axis to show actual dates within the week
            ax.set_xticks([i * 24 + 12 for i in range(period['duration_days'])])
            
            # Calculate actual dates for each day in the week in Mar30 format
            start_day_idx = self._month_day_to_day_index(period['start_month'], period['start_day'])
            week_dates = []
            for day_offset in range(period['duration_days']):
                day_idx = start_day_idx + day_offset
                month, day = self._day_index_to_month_day(day_idx)
                week_dates.append(self._format_date_mmmdd(month, day))
            
            ax.set_xticklabels(week_dates, rotation=45)
        
        # Finalize chart styling after all elements are set
        try:
            if BRANDING_AVAILABLE:
                for ax in axes:
                    branding_manager.finalize_chart_style(ax)
        except Exception:
            pass
        
        # Create common legend for all subplots
        handles = [
            plt.Rectangle((0,0),1,1, color=ENERGY_COLORS['nuclear'], alpha=0.8, label='Nuclear'),
            plt.Rectangle((0,0),1,1, color=ENERGY_COLORS['hydro'], alpha=0.8, label='Hydro'),
            plt.Rectangle((0,0),1,1, color=ENERGY_COLORS['wind'], alpha=0.8, label='Wind'),
            plt.Rectangle((0,0),1,1, color=ENERGY_COLORS['solar'], alpha=0.8, label='Solar'),
            plt.Line2D([0], [0], color='black', linewidth=2, linestyle='--', label='Demand')
        ]
        
        # Position legend at the bottom center of the figure
        fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, 0.02), 
                  ncol=5, frameon=True, fancybox=True)
        
        plt.tight_layout()
        
        # Adjust subplot layout to prevent legend from cropping x-axis labels
        plt.subplots_adjust(bottom=0.15)
        
        # Save plot
        plot_name = config_name if config_name else "weekly_stress"
        filename = f"stress_periods_{plot_name}_{iso_code}.svg"
        filepath = Path(output_dir) / filename
        # Add branding logos and main title
        try:
            if BRANDING_AVAILABLE:
                branding_manager.add_logos_to_chart(fig, "small", f"Weekly Stress Analysis - {self._get_country_name(iso_code)}")
        except Exception:
            pass
        plt.savefig(filepath, format='svg', bbox_inches='tight', pad_inches=0.2)
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
        
        # Apply branding to all subplots
        if BRANDING_AVAILABLE:
            for ax in axes:
                branding_manager.apply_chart_style(ax, "scenario_analysis")
            
            # Apply figure-level styling
            branding_manager.apply_figure_style(fig)
        
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
                    ax.set_xlabel('Date')
                    
                    # Set x-axis to show MM-DD dates at reasonable intervals
                    n_ticks = min(12, len(date_labels))
                    if n_ticks > 0:
                        tick_indices = np.linspace(0, len(date_labels)-1, n_ticks, dtype=int)
                        tick_labels = [self._format_date_mmmdd(date_labels[i].month, date_labels[i].day) for i in tick_indices]
                        
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
        # Add branding logos
        try:
            if BRANDING_AVAILABLE:
                branding_manager.add_logos_to_chart(fig, "small")
        except Exception:
            pass
        
        plot_filename = f"{output_dir}RE_scenarios_hourly_{iso_code}.png"
        plt.savefig(plot_filename, format='svg', bbox_inches='tight', pad_inches=0.2)
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
        
        # Apply branding
        try:
            if BRANDING_AVAILABLE:
                for ax in axes.flatten():
                    branding_manager.apply_chart_style(ax, "scenario_analysis")
                
                # Apply figure-level styling
                branding_manager.apply_figure_style(fig)
        except Exception:
            pass
        
        # 1. Average RE Coverage by Month (top-left)
        monthly_coverage = hourly_df.groupby('month')['coverage_pct'].mean()
        bars = axes[0,0].bar(monthly_coverage.index, monthly_coverage.values, 
                            color='skyblue', alpha=0.8)
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
                                   s=30)
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
                             label='Solar', color='gold', alpha=0.8)
        bars2 = axes[1,1].bar([i + width/2 for i in x], monthly_wind.values, width,
                             label='Wind', color='skyblue', alpha=0.8)
        
        axes[1,1].set_title(f'Average RE Generation by Month - {iso_code}')
        axes[1,1].set_xlabel('Month')
        axes[1,1].set_ylabel('Average Generation (GW)')
        axes[1,1].grid(True, alpha=0.3)
        axes[1,1].legend()
        
        # Add capacity information as text (guard for missing key)
        total_capacity = renewable_supply.get('total_capacity')
        if total_capacity is None:
            # Fallback: compute from available components if present
            solar_cap = renewable_supply.get('solar_capacity_gw', 0)
            wind_cap = renewable_supply.get('wind_capacity_gw', 0)
            hydro_cap = renewable_supply.get('hydro_capacity_gw', 0)
            total_capacity = (solar_cap or 0) + (wind_cap or 0) + (hydro_cap or 0)
        peak_demand = demand.max() / 1000  # Convert to GW
        ratio = (total_capacity/peak_demand) if peak_demand > 0 else 0
        axes[1,1].text(0.02, 0.98, f'Total RE Capacity: {total_capacity:.1f} GW\nPeak Demand: {peak_demand:.1f} GW\nCapacity Ratio: {ratio:.1f}x',
                      transform=axes[1,1].transAxes, verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Finalize chart styling after all elements are set
        try:
            if BRANDING_AVAILABLE:
                for ax in axes.flatten():
                    branding_manager.finalize_chart_style(ax)
        except Exception:
            pass
        
        plt.tight_layout()
        
        # Save the summary
        output_path = f"{output_dir}/re_analysis_summary_{iso_code}.svg"
        # Add branding logos and main title
        try:
            if BRANDING_AVAILABLE:
                branding_manager.add_logos_to_chart(fig, "small", f"Renewable Energy Analysis Summary - {self._get_country_name(iso_code)}")
        except Exception:
            pass
        
        plt.savefig(output_path, format='svg', bbox_inches='tight', pad_inches=0.2)
        plt.close()
        
        print(f"     📊 ./outputs/re_analysis_summary_{iso_code}.svg")
        
        # Also create a quick text summary
        # Safely fetch total capacity
        total_capacity_safe = renewable_supply.get('total_capacity', 0) or 0
        summary_stats = {
            'Annual Average Coverage': f"{hourly_df['coverage_pct'].mean():.1f}%",
            'Peak Coverage': f"{hourly_df['coverage_pct'].max():.1f}%",
            'Surplus Hours': f"{hourly_df['is_surplus'].sum():,} hours ({hourly_df['is_surplus'].sum()/8760*100:.1f}% of year)",
            'Scarcity Hours': f"{hourly_df['is_scarcity'].sum():,} hours ({hourly_df['is_scarcity'].sum()/8760*100:.1f}% of year)",
            'Solar Capacity Factor': f"{(hourly_df['solar_gw'].mean() * 8760) / (total_capacity_safe * 8760) * 100:.1f}%" if total_capacity_safe > 0 else "N/A",
            'Best Month (Avg Coverage)': f"Month {monthly_coverage.idxmax()} ({monthly_coverage.max():.1f}%)",
            'Worst Month (Avg Coverage)': f"Month {monthly_coverage.idxmin()} ({monthly_coverage.min():.1f}%)"
        }
        
        print(f"     📈 Key Annual Statistics for {iso_code}:")
        for key, value in summary_stats.items():
            print(f"         • {key}: {value}")
    
    def _plot_individual_scenarios(self, iso_code, net_load, renewable_supply, scenarios, output_dir):
        """Create individual detailed plots for each scenario"""
        # Create subdirectory for individual scenario plots
        scenario_dir = output_dir / "individual_scenarios"
        scenario_dir.mkdir(parents=True, exist_ok=True)
        
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
            
            ax.set_title(f'{self._get_country_name(iso_code)} - {scenario_name.replace("_", " ").title()} - Detailed Analysis')
            ax.set_xlabel('Month')
            ax.set_ylabel('RE Coverage (%)')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            
            # Format x-axis
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            
            plt.tight_layout()
            
            # Save individual scenario plot
            plot_filename = scenario_dir / f"{iso_code}_{scenario_name}_detailed.png"
            # Add branding logos
            try:
                if BRANDING_AVAILABLE:
                    branding_manager.add_logos_to_chart(fig, "small")
            except Exception:
                pass
            
            plt.savefig(plot_filename, format='svg', bbox_inches='tight', pad_inches=0.2)
            print(f"     📊 {plot_filename}")
            plt.close()
    
    def _plot_aggregation_justification(self, iso_code, net_load, base_scheme, output_dir):
        """Create plots to justify the aggregated segment decisions"""
        # Reshape data for analysis
        daily_net_load = net_load.reshape(365, 24)
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 3, figsize=(11, 7),
                                gridspec_kw={'height_ratios': [0.45, 0.55]})
        fig.suptitle(f'Timeslice Aggregation Justification - {self._get_country_name(iso_code)}', 
                    fontsize=branding_manager.get_font_size('title'), y=0.98)
        try:
            if BRANDING_AVAILABLE:
                for ax in axes.flatten():
                    branding_manager.apply_chart_style(ax, "scenario_analysis")
                
                # Apply figure-level styling
                branding_manager.apply_figure_style(fig)
        except Exception:
            pass
        
        # Get unique seasons and periods for all plots
        unique_seasons = sorted(set(base_scheme['months'].values()))
        unique_periods = sorted(set(base_scheme['hours'].values()))
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_seasons)))
        season_colors = {season: colors[i] for i, season in enumerate(unique_seasons)}
        period_colors = {period: colors[i % len(colors)] for i, period in enumerate(unique_periods)}
        
        # Plot 1: Monthly variability patterns (TOP LEFT)
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
        
        # Plot monthly variability with season colors
        month_stds = [s['std'] for s in monthly_stats]
        month_colors = [season_colors[base_scheme['months'][i+1]] for i in range(12)]
        
        bars = ax1.bar(month_names, month_stds, color=month_colors, alpha=0.7)
        ax1.set_title('Monthly Variability by Season Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax1.set_ylabel('Net Load Std Dev (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax1.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Plot 2: Monthly patterns with season clusters (TOP CENTER)
        ax2 = axes[0, 1]
        month_means = [s['mean'] for s in monthly_stats]
        bars = ax2.bar(month_names, month_means, color=month_colors, alpha=0.7)
        ax2.set_title('Monthly Net Load by Season Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax2.set_ylabel('Average Net Load (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax2.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Plot 3: Monthly peak patterns (TOP RIGHT)
        ax3 = axes[0, 2]
        month_peaks = [s['max'] for s in monthly_stats]
        ax3.bar(month_names, month_peaks, color=month_colors, alpha=0.7)
        ax3.set_title('Monthly Peak Net Load by Season Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax3.set_ylabel('Peak Net Load (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax3.grid(True, alpha=0.3)
        ax3.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax3.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Create unified legend for all three top charts (positioned below the top row)
        handles = [plt.Rectangle((0,0),1,1, color=season_colors[season], alpha=0.7)
                  for season in unique_seasons]
        legend_labels = [f'Season {s}' for s in unique_seasons]

        # Position legend below the top row, centered
        fig.legend(handles, legend_labels, loc='upper center', bbox_to_anchor=(0.5, 0.54),
                  ncol=len(unique_seasons), frameon=True, fancybox=True,
                  fontsize=branding_manager.get_font_size('axis'))
        
        # Plot 4: 2D heatmap showing season-period combinations (BOTTOM LEFT - LEFTMOST)
        ax4 = axes[1, 0]
        
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
        
        im = ax4.imshow(season_period_matrix, cmap='RdYlBu_r', aspect='auto')
        ax4.set_title('Season-Period Net Load Matrix', fontsize=branding_manager.get_font_size('subtitle'))
        ax4.set_xlabel('Daily Period', fontsize=branding_manager.get_font_size('labels'))
        ax4.set_ylabel('Season', fontsize=branding_manager.get_font_size('labels'))
        ax4.set_xticks(range(len(unique_periods)))
        ax4.set_xticklabels([f'Period {p}' for p in unique_periods], fontsize=branding_manager.get_font_size('axis'), rotation=45, ha='right')
        ax4.set_yticks(range(len(unique_seasons)))
        ax4.set_yticklabels([f'S{s}' for s in unique_seasons], fontsize=branding_manager.get_font_size('axis'))
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax4)
        cbar.set_label('Average Net Load (MW)', fontsize=branding_manager.get_font_size('labels'))
        cbar.ax.tick_params(labelsize=branding_manager.get_font_size('axis'))
        
        # Add text annotations to show values
        for i in range(len(unique_seasons)):
            for j in range(len(unique_periods)):
                text = ax4.text(j, i, f'{season_period_matrix[i, j]:.0f}',
                               ha="center", va="center", color="black", 
                               fontsize=branding_manager.get_font_size('heatmap'))  # Use config-based heatmap font size
        
        # Plot 5: Hourly patterns with period clusters (BOTTOM CENTER)
        ax5 = axes[1, 1]
        
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
        
        # Plot hourly means with period colors
        hour_means = [s['mean'] for s in hourly_stats]
        hour_colors = [period_colors[base_scheme['hours'][i+1]] for i in range(24)]
        
        hours = list(range(24))
        bars = ax5.bar(hours, hour_means, color=hour_colors, alpha=0.7)
        ax5.set_title('Hourly Net Load by Period Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax5.set_xlabel('Hour of Day', fontsize=branding_manager.get_font_size('labels'))
        ax5.set_ylabel('Average Net Load (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax5.grid(True, alpha=0.3)
        ax5.set_xticks(range(0, 24, 3))
        ax5.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax5.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Plot 6: Hourly variability patterns (BOTTOM RIGHT)
        ax6 = axes[1, 2]
        hour_stds = [s['std'] for s in hourly_stats]
        ax6.bar(hours, hour_stds, color=hour_colors, alpha=0.7)
        ax6.set_title('Hourly Variability by Period Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax6.set_xlabel('Hour of Day', fontsize=branding_manager.get_font_size('labels'))
        ax6.set_ylabel('Net Load Std Dev (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax6.grid(True, alpha=0.3)
        ax6.set_xticks(range(0, 24, 3))
        ax6.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax6.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Create unified legend for period clusters (positioned below the bottom row)
        period_handles = [plt.Rectangle((0,0),1,1, color=period_colors[period], alpha=0.7)
                          for period in unique_periods]
        period_legend_labels = [f'Period {p}' for p in unique_periods]

        # Position legend below the bottom row, centered
        fig.legend(period_handles, period_legend_labels, loc='lower center', bbox_to_anchor=(0.5, 0.01),
                  ncol=len(unique_periods), frameon=True, fancybox=True,
                  fontsize=branding_manager.get_font_size('axis'))
        
        # Finalize chart styling after all elements are set
        try:
            if BRANDING_AVAILABLE:
                for ax in axes.flatten():
                    branding_manager.finalize_chart_style(ax)
        except Exception:
            pass
        
        plt.tight_layout(pad=2.0)
        
        # Add branding logos and main title
        try:
            if BRANDING_AVAILABLE:
                branding_manager.add_logos_to_chart(fig, "small", f"Timeslice Aggregation Justification - {self._get_country_name(iso_code)}")
        except Exception:
            pass
        
        # Save plot
        plot_filename = output_dir / f"aggregation_justification_{iso_code}.svg"
        plt.savefig(plot_filename, format='svg', bbox_inches='tight', pad_inches=0.2)
        print(f"     📊 {plot_filename}")
        plt.close()
        
        # Create summary statistics tables
        self._create_aggregation_summary(iso_code, base_scheme, monthly_stats, hourly_stats, output_dir)
    
    def _plot_scenario_aggregation_justifications(self, iso_code, net_load, scenario_base_schemes, output_dir):
        """Create aggregation justification plots for each scenario"""
        
        # Load configuration to check which scenarios should have clustering plots
        config_df = self._load_stress_configurations()
        
        # Filter scenarios that should have clustering plots
        scenarios_to_plot = []
        import pandas as pd
        for scenario_name in scenario_base_schemes.keys():
            # Find config for this scenario
            config_row = config_df[config_df['name'] == scenario_name]
            if not config_row.empty:
                config = config_row.iloc[0]
                should_plot_clu = config.get('create_plot_clu', False) if pd.notna(config.get('create_plot_clu', False)) else False
                if should_plot_clu:
                    scenarios_to_plot.append(scenario_name)
        
        if not scenarios_to_plot:
            print(f"   📊 No scenarios configured for clustering plots (create_plot_clu=True)")
            return
            
        print(f"   📊 Creating {len(scenarios_to_plot)} scenario-specific aggregation justification plots...")
        
        for scenario_name in scenarios_to_plot:
            base_scheme = scenario_base_schemes[scenario_name]
            print(f"      🎨 Creating justification plot for {scenario_name}...")
            
            # Create scenario-specific plot
            self._plot_single_aggregation_justification(iso_code, net_load, base_scheme, 
                                                      output_dir, scenario_name)
        
        print(f"   ✅ All aggregation justification plots completed for {iso_code}")
    
    def _plot_single_aggregation_justification(self, iso_code, net_load, base_scheme, output_dir, scenario_name):
        """Create a single aggregation justification plot for a specific scenario"""
        # Reshape data for analysis
        daily_net_load = net_load.reshape(365, 24)
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 3, figsize=(11, 7),
                                gridspec_kw={'height_ratios': [0.45, 0.55]})
        
        # Scenario-specific title
        scenario_display = scenario_name.replace('_', ' ').title()
        fig.suptitle(f'Timeslice Aggregation Justification - {self._get_country_name(iso_code)} ({scenario_display})', 
                    fontsize=branding_manager.get_font_size('title'), y=0.98)
        
        # Apply branding to all subplots
        try:
            if BRANDING_AVAILABLE:
                for ax in axes.flatten():
                    branding_manager.apply_chart_style(ax, "scenario_analysis")
                
                # Apply figure-level styling
                branding_manager.apply_figure_style(fig)
        except Exception:
            pass
        
        # Get unique seasons and periods for all plots
        unique_seasons = sorted(set(base_scheme['months'].values()))
        unique_periods = sorted(set(base_scheme['hours'].values()))
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_seasons)))
        season_colors = {season: colors[i] for i, season in enumerate(unique_seasons)}
        period_colors = {period: colors[i % len(colors)] for i, period in enumerate(unique_periods)}
        
        # Plot 1: Monthly variability patterns (TOP LEFT)
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
                'std': month_data.std(),
                'max': month_data.max(),
                'min': month_data.min()
            })
            day_start += month_days
        
        # Plot monthly variability with season colors
        month_stds = [s['std'] for s in monthly_stats]
        month_colors = [season_colors[base_scheme['months'][i+1]] for i in range(12)]
        
        bars = ax1.bar(month_names, month_stds, color=month_colors, alpha=0.7)
        ax1.set_title('Monthly Variability by Season Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax1.set_ylabel('Net Load Std Dev (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax1.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Plot 2: Monthly patterns with season clusters (TOP CENTER)
        ax2 = axes[0, 1]
        month_means = [s['mean'] for s in monthly_stats]
        bars = ax2.bar(month_names, month_means, color=month_colors, alpha=0.7)
        ax2.set_title('Monthly Net Load by Season Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax2.set_ylabel('Average Net Load (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax2.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Plot 3: Monthly peak patterns (TOP RIGHT)
        ax3 = axes[0, 2]
        month_peaks = [s['max'] for s in monthly_stats]
        ax3.bar(month_names, month_peaks, color=month_colors, alpha=0.7)
        ax3.set_title('Monthly Peak Net Load by Season Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax3.set_ylabel('Peak Net Load (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax3.grid(True, alpha=0.3)
        ax3.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax3.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Create unified legend for all three top charts (positioned below the top row)
        unique_seasons_sorted = sorted(unique_seasons)
        legend_labels = [f'Season {season}' for season in unique_seasons_sorted]
        handles = [plt.Rectangle((0,0),1,1, color=season_colors[season], alpha=0.7) for season in unique_seasons_sorted]
        
        fig.legend(handles, legend_labels, loc='upper center', bbox_to_anchor=(0.5, 0.54),
                  ncol=len(unique_seasons), frameon=True, fancybox=True,
                  fontsize=branding_manager.get_font_size('axis'))
        
        # Plot 4: 2D heatmap showing season-period combinations (BOTTOM LEFT - LEFTMOST)
        ax4 = axes[1, 0]
        
        # Create matrix for season-period combinations
        season_to_idx = {season: i for i, season in enumerate(unique_seasons_sorted)}
        period_to_idx = {period: i for i, period in enumerate(sorted(unique_periods))}
        
        season_period_matrix = np.zeros((len(unique_seasons), len(unique_periods)))
        
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
        
        im = ax4.imshow(season_period_matrix, cmap='RdYlBu_r', aspect='auto')
        ax4.set_title('Season-Period Net Load Matrix', fontsize=branding_manager.get_font_size('subtitle'))
        ax4.set_xlabel('Daily Period', fontsize=branding_manager.get_font_size('labels'))
        ax4.set_ylabel('Season', fontsize=branding_manager.get_font_size('labels'))
        ax4.set_xticks(range(len(unique_periods)))
        ax4.set_xticklabels([f'Period {p}' for p in sorted(unique_periods)], fontsize=branding_manager.get_font_size('axis'), rotation=45, ha='right')
        ax4.set_yticks(range(len(unique_seasons)))
        ax4.set_yticklabels([f'S{s}' for s in unique_seasons_sorted], fontsize=branding_manager.get_font_size('axis'))
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax4)
        cbar.set_label('Average Net Load (MW)', fontsize=branding_manager.get_font_size('labels'))
        cbar.ax.tick_params(labelsize=branding_manager.get_font_size('axis'))
        
        # Add text annotations to show values
        for i in range(len(unique_seasons)):
            for j in range(len(unique_periods)):
                text = ax4.text(j, i, f'{season_period_matrix[i, j]:.0f}',
                               ha="center", va="center", color="black", 
                               fontsize=branding_manager.get_font_size('heatmap'))  # Use config-based heatmap font size
        
        # Plot 5: Hourly patterns with period clusters (BOTTOM CENTER)
        ax5 = axes[1, 1]
        
        # Calculate hourly statistics
        hourly_stats = []
        for hour in range(24):
            hour_data = daily_net_load[:, hour]
            hourly_stats.append({
                'mean': hour_data.mean(),
                'std': hour_data.std(),
                'max': hour_data.max(),
                'min': hour_data.min()
            })
        
        # Plot hourly means with period colors
        hour_means = [s['mean'] for s in hourly_stats]
        hour_colors = [period_colors[base_scheme['hours'][i+1]] for i in range(24)]
        
        hours = list(range(24))
        bars = ax5.bar(hours, hour_means, color=hour_colors, alpha=0.7)
        ax5.set_title('Hourly Net Load by Period Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax5.set_xlabel('Hour of Day', fontsize=branding_manager.get_font_size('labels'))
        ax5.set_ylabel('Average Net Load (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax5.grid(True, alpha=0.3)
        ax5.set_xticks(range(0, 24, 3))
        ax5.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax5.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Plot 6: Hourly variability with period clusters (BOTTOM RIGHT)
        ax6 = axes[1, 2]
        hour_stds = [s['std'] for s in hourly_stats]
        ax6.bar(hours, hour_stds, color=hour_colors, alpha=0.7)
        ax6.set_title('Hourly Variability by Period Cluster', fontsize=branding_manager.get_font_size('subtitle'))
        ax6.set_xlabel('Hour of Day', fontsize=branding_manager.get_font_size('labels'))
        ax6.set_ylabel('Net Load Std Dev (MW)', fontsize=branding_manager.get_font_size('labels'))
        ax6.grid(True, alpha=0.3)
        ax6.set_xticks(range(0, 24, 3))
        ax6.tick_params(axis='x', rotation=45, labelsize=branding_manager.get_font_size('axis'))
        ax6.tick_params(axis='y', labelsize=branding_manager.get_font_size('axis'))
        
        # Finalize chart styling after all elements are set
        try:
            if BRANDING_AVAILABLE:
                for ax in axes.flatten():
                    branding_manager.finalize_chart_style(ax)
        except Exception:
            pass
        
        plt.tight_layout()
        
        # Add branding logos and main title
        try:
            if BRANDING_AVAILABLE:
                branding_manager.add_logos_to_chart(fig, "small", f"Aggregation Justification - {self._get_country_name(iso_code)} ({scenario_display})")
        except Exception:
            pass
        
        # Save with scenario-specific filename
        plot_filename = output_dir / f"aggregation_justification_{iso_code}_{scenario_name}.svg"
        plt.savefig(plot_filename, format='svg', bbox_inches='tight', pad_inches=0.2)
        print(f"         ✅ {plot_filename}")
        plt.close()
        
        # Create scenario-specific summary statistics tables
        self._create_scenario_aggregation_summary(iso_code, base_scheme, monthly_stats, hourly_stats, output_dir, scenario_name)
    
    def _create_scenario_aggregation_summary(self, iso_code, base_scheme, monthly_stats, hourly_stats, output_dir, scenario_name):
        """Create scenario-specific summary tables explaining the aggregation decisions"""
        
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
        season_filename = output_dir / f"season_clusters_{iso_code}_{scenario_name}.csv"
        season_df.to_csv(season_filename, index=False)
        print(f"         📋 {season_filename}")
        
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
        period_filename = output_dir / f"period_clusters_{iso_code}_{scenario_name}.csv"
        period_df.to_csv(period_filename, index=False)
        print(f"         📋 {period_filename}")
    
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
        season_filename = output_dir / f"season_clusters_{iso_code}.csv"
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
        period_filename = output_dir / f"period_clusters_{iso_code}.csv"
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
            summary_filename = output_dir / f"segment_summary_{iso_code}.csv"
            summary_df.to_csv(summary_filename, index=False)
            print(f"     📋 {summary_filename}")
            return summary_df
        else:
            print(f"     ⚠️  No segments found for {iso_code}")
            return pd.DataFrame()
    
    def _save_daily_coverage_json(self, iso_code, renewable_supply, iso_data, output_dir):
        """Save daily coverage data as JSON for enhanced calendar visualization"""
        import json
        
        demand = iso_data['demand']
        re_total = renewable_supply['hourly_total']
        
        # Calculate daily average coverage (365 days)
        daily_coverage = []
        for day in range(365):
            start_hour = day * 24
            end_hour = min((day + 1) * 24, 8760)
            
            day_demand = demand[start_hour:end_hour]
            day_re = re_total[start_hour:end_hour]
            
            if np.sum(day_demand) > 0:
                day_coverage_pct = (np.sum(day_re) / np.sum(day_demand)) * 100
            else:
                day_coverage_pct = 0.0
                
            daily_coverage.append(round(day_coverage_pct, 1))
        
        # Create JSON structure
        coverage_data = {
            "iso": iso_code,
            "weather_year": 2013,  # Default weather year used in analysis
            "daily_coverage": daily_coverage,
            "metadata": {
                "units": "percentage",
                "description": "Daily average renewable energy coverage (renewables/demand * 100)",
                "calculation": "Daily sum of renewables / Daily sum of demand * 100",
                "generated_by": "VerveStacks Stress Period Analyzer"
            }
        }
        
        # Save JSON file
        json_filename = output_dir / f"daily_coverage_{iso_code}.json"
        with open(json_filename, 'w') as f:
            json.dump(coverage_data, f, indent=2)
        
        print(f"     📅 {json_filename}")
        
        # Print summary statistics
        avg_coverage = np.mean(daily_coverage)
        min_coverage = np.min(daily_coverage)
        max_coverage = np.max(daily_coverage)
        print(f"        Daily coverage: {min_coverage:.1f}% to {max_coverage:.1f}% (avg: {avg_coverage:.1f}%)")
        
        return json_filename
    
    def run_full_pipeline(self, target_isos=None, save_results=True, output_dir=None):
        """
        Run the complete VerveStacks timeslice processing pipeline
        
        This is the main entry point - processes all ISOs and generates
        the adaptive timeslice structures that will revolutionize TIMES modeling
        """
        print("🚀 Starting VerveStacks Timeslice Processing Pipeline")
        print("=" * 60)
        
        # Set default output directory relative to script location if not provided
        if output_dir is None:
            script_dir = Path(__file__).parent.absolute()
            output_dir = script_dir.parent / "outputs"  # 2_ts_design/outputs/
            
        # Ensure output_dir is a Path object
        output_dir = Path(output_dir)
        
        # Create output directory structure if saving
        if save_results:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get list of ISOs to process
        if target_isos is None:
            # Default to common ISOs for demo since we no longer need to load all data upfront
            target_isos = ['DEU', 'ITA', 'CHE', 'DNK', 'FRA'][:5]  # Process first 5 for demo
        
        print(f"\n🎯 Processing {len(target_isos)} ISOs: {', '.join(target_isos)}")
        
        # Process each ISO
        all_results = {}
        for iso_code in target_isos:
            # Create ISO-specific output directory
            if save_results:
                iso_output_dir = output_dir / iso_code
                iso_output_dir.mkdir(parents=True, exist_ok=True)
                (iso_output_dir / "individual_scenarios").mkdir(parents=True, exist_ok=True)
            else:
                iso_output_dir = output_dir
            
            result = self.process_iso(iso_code, save_outputs=save_results, output_dir=iso_output_dir)
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
    # CONFIGURATION-DRIVEN SCENARIO GENERATION
    # ==========================================
    
    def _generate_all_stress_configurations(self, coverage):
        """
        Generate all stress configurations from VS_mappings stress_periods_config.
        Replaces hardcoded triple_1, triple_5, weekly_stress calls with dynamic execution.
        """
        # Load configuration table
        config_df = self._load_stress_configurations()
        
        # Process each configuration row
        all_scenarios = {}
        all_configs = {}  # Store configurations for later use
        for _, config in config_df.iterrows():
            config_name = config['name']
            
            # Check if configuration has daily and/or weekly parameters
            has_daily = self._has_daily_stress_params(config)
            has_weekly = self._has_weekly_stress_params(config)
            has_clustering = self._has_clustering_params(config)
            

            
            if has_daily and has_weekly:
                # MIXED configuration: combine daily and weekly periods
                print(f"   🔄 Processing mixed configuration: {config_name} (daily + weekly)")
                daily_result = self._process_daily_stress_periods(coverage, config)
                weekly_result = self._process_weekly_stress_periods(coverage, config)
                
                # Combine the periods from both processors
                combined_periods = daily_result[config_name] + weekly_result[config_name]
                all_scenarios[config_name] = combined_periods
                all_configs[config_name] = config
                
            elif has_daily:
                # DAILY-only configuration
                scenario_result = self._process_daily_stress_periods(coverage, config)
                all_scenarios.update(scenario_result)
                all_configs[config_name] = config
                
            elif has_weekly:
                # WEEKLY-only configuration  
                scenario_result = self._process_weekly_stress_periods(coverage, config)
                all_scenarios.update(scenario_result)
                all_configs[config_name] = config
                
            elif has_clustering:
                # CLUSTERING-only configuration (traditional approach - no stress periods!)
                print(f"   📊 {config_name}: Pure Clustering Configuration (Traditional Approach)")
                print(f"   🎯 Target: {config.get('target_timeslices', 'auto')} total timeslices (aggregated only)")
                scenario_result = self._process_clustering_only_periods(config)
                all_scenarios.update(scenario_result)
                all_configs[config_name] = config
                
            else:
                print(f"   ⚠️  No valid parameters found for configuration: {config_name}")
        
        return all_scenarios, all_configs
    
    def _load_stress_configurations(self):
        """Load stress period configurations from VS_mappings."""
        try:
            from shared_data_loader import get_shared_loader
            shared_loader = get_shared_loader("data/")
            config_df = shared_loader.get_vs_mappings_sheet("stress_periods_config")
            
            if config_df is None or config_df.empty:
                print("   ⚠️  No stress_periods_config found in VS_mappings, using default configurations")
                # Fallback to hardcoded configurations for backward compatibility
                return self._get_default_stress_configurations()
            
            return config_df
            
        except Exception as e:
            print(f"   ⚠️  Error loading stress configurations: {e}")
            print("   📋 Using default configurations")
            return self._get_default_stress_configurations()
    
    def _get_default_stress_configurations(self):
        """Fallback default configurations matching current hardcoded behavior."""
        import pandas as pd
        
        default_configs = [
            # Traditional clustering-only configurations (30 years of energy modeling!)
            {'name': 'ts12_clu', 'days_scarcity': None, 'days_surplus': None, 'days_volatility': None, 'weeks_scarcity': None, 'weeks_surplus': None, 'weeks_volatility': None, 'num_aggregated_ts': 12, 'create_plot': False, 'create_plot_clu': False},
            {'name': 'ts24_clu', 'days_scarcity': None, 'days_surplus': None, 'days_volatility': None, 'weeks_scarcity': None, 'weeks_surplus': None, 'weeks_volatility': None, 'num_aggregated_ts': 24, 'create_plot': False, 'create_plot_clu': False},
            {'name': 'ts48_clu', 'days_scarcity': None, 'days_surplus': None, 'days_volatility': None, 'weeks_scarcity': None, 'weeks_surplus': None, 'weeks_volatility': None, 'num_aggregated_ts': 48, 'create_plot': False, 'create_plot_clu': True}
        ]
        
        return pd.DataFrame(default_configs)
    
    def _has_daily_stress_params(self, config):
        """Check if configuration has daily stress parameters."""
        daily_params = ['days_scarcity', 'days_surplus', 'days_volatility']
        return any(pd.notna(config.get(param)) and config.get(param, 0) > 0 for param in daily_params)
    
    def _has_weekly_stress_params(self, config):
        """Check if configuration has weekly stress parameters."""
        weekly_params = ['weeks_scarcity', 'weeks_surplus', 'weeks_volatility']
        return any(pd.notna(config.get(param)) and config.get(param, 0) > 0 for param in weekly_params)
    
    def _has_clustering_params(self, config):
        """Check if configuration is clustering-only (no stress periods)."""
        # Look for clustering parameters in both fallback defaults and VS_mappings
        clustering_params = ['num_aggregated_months', 'num_aggregated_hours']
        return any(pd.notna(config.get(param)) and config.get(param, 0) > 0 for param in clustering_params)

    def _process_daily_stress_periods(self, coverage, config):
        """
        Process daily stress periods using existing logic with configurable parameters.
        Replaces hardcoded triple_1 (1,1,1) and triple_5 (5,5,5) with any combination.
        EXACT same logic as _generate_plan1_triple_1 and _generate_plan2_triple_5.
        """
        config_name = config['name']
        
        # Extract parameters, handling NaN values from Excel
        import pandas as pd
        num_scarcity = int(config.get('days_scarcity', 0) if pd.notna(config.get('days_scarcity', 0)) else 0)
        num_surplus = int(config.get('days_surplus', 0) if pd.notna(config.get('days_surplus', 0)) else 0)
        num_volatility = int(config.get('days_volatility', 0) if pd.notna(config.get('days_volatility', 0)) else 0)
        
        print(f"   📊 {config_name}: Configurable Daily Selection")
        print(f"   🎯 Target: {num_scarcity} scarcity + {num_surplus} surplus + {num_volatility} volatile days")
        
        # EXACT same daily statistics calculation as current implementations
        daily_stats = self._calculate_daily_statistics_from_coverage(coverage)
        
        # Select stress periods using EXACT same ranking logic, different counts
        selected_periods = self._select_daily_stress_periods(daily_stats, num_scarcity, num_surplus, num_volatility)
        
        # Return in EXACT same format as current implementations
        return {config_name: selected_periods}
    
    def _process_weekly_stress_periods(self, coverage, config):
        """
        Process weekly stress periods using existing logic with configurable parameters.
        Replaces hardcoded weekly_stress (2 weeks) with any number of weeks.
        EXACT same logic as _generate_plan3_weekly_stress.
        """
        config_name = config['name']
        
        # Extract parameters, handling NaN values from Excel
        import pandas as pd
        num_scarcity_weeks = int(config.get('weeks_scarcity', 0) if pd.notna(config.get('weeks_scarcity', 0)) else 0)
        num_surplus_weeks = int(config.get('weeks_surplus', 0) if pd.notna(config.get('weeks_surplus', 0)) else 0)
        num_volatility_weeks = int(config.get('weeks_volatility', 0) if pd.notna(config.get('weeks_volatility', 0)) else 0)
        
        print(f"   📊 {config_name}: Configurable Weekly Selection")
        print(f"   🎯 Target: {num_scarcity_weeks} scarcity weeks + {num_surplus_weeks} surplus weeks + {num_volatility_weeks} volatile weeks")
        
        # EXACT same weekly statistics calculation as current _generate_plan3_weekly_stress
        weekly_stats = self._calculate_weekly_statistics_from_coverage(coverage)
        
        # Select weekly stress periods using EXACT same ranking logic, different counts
        selected_periods = self._select_weekly_stress_periods(weekly_stats, num_scarcity_weeks, num_surplus_weeks, num_volatility_weeks)
        
        # Return in EXACT same format as current implementations
        return {config_name: selected_periods}
    
    def _process_clustering_only_periods(self, config):
        """
        Process clustering-only configurations (traditional approach).
        These configurations have NO stress periods - just pure aggregated timeslices.
        This is the classic energy modeling approach used for 30 years!
        """
        config_name = config['name']
        
        # Extract target timeslices from various possible column names
        import pandas as pd
        
        # Try different column names (fallback defaults vs VS_mappings)
        target_timeslices = None
        
        # First try explicit month/hour specification
        if (pd.notna(config.get('num_aggregated_months')) and 
            pd.notna(config.get('num_aggregated_hours'))):
            months = int(config.get('num_aggregated_months'))
            hours = int(config.get('num_aggregated_hours'))
            target_timeslices = months * hours
        else:
            # Fallback to num_aggregated_ts
            for param in ['num_aggregated_ts']:
                if pd.notna(config.get(param)) and config.get(param, 0) > 0:
                    target_timeslices = int(config.get(param))
                    break
        
        
        print(f"   🎯 Pure clustering: {target_timeslices} total timeslices (no stress periods)")
        
        # For clustering-only, we return an EMPTY list of periods
        # The base aggregation will provide ALL the timeslices
        return {config_name: []}

    def _calculate_daily_statistics_from_coverage(self, coverage):
        """
        Calculate daily statistics using EXACT same logic as _generate_plan1_triple_1 and _generate_plan2_triple_5.
        No changes to calculations, thresholds, or methodology.
        """
        # EXACT same calculation as current implementations
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        daily_stats = []
        
        for day in range(365):
            day_coverage = np.array(coverage[day*24:(day+1)*24])
            
            # Determine month and day-of-month (EXACT same logic)
            cum_days = np.cumsum([0] + days_in_month)
            month = np.where(day < cum_days[1:])[0][0] + 1
            day_in_month = day - cum_days[month-1] + 1
            
            # Core statistical metrics (EXACT same calculations)
            avg_coverage = np.mean(day_coverage)
            coverage_variance = np.var(day_coverage)
            coverage_std = np.std(day_coverage)
            min_coverage = np.min(day_coverage)
            max_coverage = np.max(day_coverage)
            
            stats = {
                'day_index': day,
                'month': month,
                'day_in_month': day_in_month,
                'date_string': self._format_date_mmmdd(month, day_in_month),
                'avg_coverage': avg_coverage,
                'coverage_variance': coverage_variance,
                'coverage_std': coverage_std,
                'min_coverage': min_coverage,
                'max_coverage': max_coverage
            }
            daily_stats.append(stats)
        
        return daily_stats

    def _select_daily_stress_periods(self, daily_stats, num_scarcity, num_surplus, num_volatility):
        """
        Select daily stress periods using EXACT same logic as current triple_1/triple_5.
        Only difference: configurable counts instead of hardcoded 1 or 5.
        """
        import pandas as pd
        df = pd.DataFrame(daily_stats)
        used_day_indices = set()
        selected_periods = []
        
        # SCARCITY SELECTION (EXACT same logic as current)
        if num_scarcity > 0:
            scarcity_ranking = df.sort_values('avg_coverage', ascending=True)  # Same ranking
            scarcity_days = scarcity_ranking.head(num_scarcity)  # Only change: configurable count
            used_day_indices.update(scarcity_days['day_index'])
            
            print(f"\n   🔥 SCARCITY DAYS (Renewable Shortage Crisis):")
            for i, (_, row) in enumerate(scarcity_days.iterrows(), 1):
                print(f"      {i}. {row['date_string']}: Avg={row['avg_coverage']:.1f}% "
                      f"(Min={row['min_coverage']:.1f}%, Max={row['max_coverage']:.1f}%)")
            
            # Add to selected periods (same format as current)
            for i, (_, row) in enumerate(scarcity_days.iterrows(), 1):
                selected_periods.append({
                    'category': 'scarcity',
                    'start_month': int(row['month']),
                    'start_day': int(row['day_in_month']),
                    'end_month': int(row['month']),
                    'end_day': int(row['day_in_month']),
                    'duration_days': 1,
                    'duration_hours': 24,
                    'avg_coverage': row['avg_coverage'],
                    'coverage_variance': row['coverage_variance'],
                    'period_id': f"S{i:02d}",
                    'description': f"Scarcity day: {row['date_string']}"
                })
        
        # SURPLUS SELECTION (EXACT same logic as current)
        if num_surplus > 0:
            surplus_ranking = df[~df['day_index'].isin(used_day_indices)].sort_values('avg_coverage', ascending=False)  # Same ranking
            surplus_days = surplus_ranking.head(num_surplus)  # Only change: configurable count
            used_day_indices.update(surplus_days['day_index'])
            
            print(f"\n   ⚡ SURPLUS DAYS (Renewable Excess Management):")
            for i, (_, row) in enumerate(surplus_days.iterrows(), 1):
                print(f"      {i}. {row['date_string']}: Avg={row['avg_coverage']:.1f}% "
                      f"(Min={row['min_coverage']:.1f}%, Max={row['max_coverage']:.1f}%)")
            
            # Add to selected periods (same format as current)
            for i, (_, row) in enumerate(surplus_days.iterrows(), 1):
                selected_periods.append({
                    'category': 'surplus',
                    'start_month': int(row['month']),
                    'start_day': int(row['day_in_month']),
                    'end_month': int(row['month']),
                    'end_day': int(row['day_in_month']),
                    'duration_days': 1,
                    'duration_hours': 24,
                    'avg_coverage': row['avg_coverage'],
                    'coverage_variance': row['coverage_variance'],
                    'period_id': f"P{i:02d}",
                    'description': f"Surplus day: {row['date_string']}"
                })
        
        # VOLATILITY SELECTION (EXACT same logic as current)
        if num_volatility > 0:
            available_volatile = df[
                (~df['day_index'].isin(used_day_indices)) & 
                (df['avg_coverage'] <= 100)  # Same constraint as current
            ].sort_values('coverage_variance', ascending=False)  # Same ranking
            volatile_days = available_volatile.head(num_volatility)  # Only change: configurable count
            
            print(f"\n   🌪️ VOLATILE DAYS (Operational Challenges):")
            for i, (_, row) in enumerate(volatile_days.iterrows(), 1):
                print(f"      {i}. {row['date_string']}: Avg={row['avg_coverage']:.1f}%, "
                      f"Var={row['coverage_variance']:.1f}, Std={row['coverage_std']:.1f}")
            
            # Add to selected periods (same format as current)
            for i, (_, row) in enumerate(volatile_days.iterrows(), 1):
                selected_periods.append({
                    'category': 'volatile',
                    'start_month': int(row['month']),
                    'start_day': int(row['day_in_month']),
                    'end_month': int(row['month']),
                    'end_day': int(row['day_in_month']),
                    'duration_days': 1,
                    'duration_hours': 24,
                    'avg_coverage': row['avg_coverage'],
                    'coverage_variance': row['coverage_variance'],
                    'period_id': f"V{i:02d}",
                    'description': f"Volatile day: {row['date_string']}"
                })
        
        return selected_periods

    def _calculate_weekly_statistics_from_coverage(self, coverage):
        """
        Calculate weekly statistics using EXACT same logic as _generate_plan3_weekly_stress.
        No changes to calculations, thresholds, or methodology.
        """
        # EXACT same calculation as current _generate_plan3_weekly_stress
        weekly_stats = []
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        for week in range(52):  # 52 weeks in year
            week_start_day = week * 7
            week_end_day = min((week + 1) * 7, 365)
            
            # Get all hours in this week (EXACT same logic)
            week_hours = []
            for day in range(week_start_day, week_end_day):
                if day < 365:  # Safety check
                    day_coverage = coverage[day*24:(day+1)*24]
                    week_hours.extend(day_coverage)
            
            if week_hours:  # Ensure we have data
                # Calculate week statistics (EXACT same calculations)
                week_avg_coverage = np.mean(week_hours)
                week_min_coverage = np.min(week_hours)
                week_max_coverage = np.max(week_hours)
                week_std_coverage = np.std(week_hours)
                
                # Get week start/end dates (EXACT same logic)
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
                    'week_span': f"{self._format_date_mmmdd(start_month, start_day_in_month)}-{self._format_date_mmmdd(end_month, end_day_in_month)}",
                    'days_in_week': week_end_day - week_start_day
                })
        
        return weekly_stats

    def _select_weekly_stress_periods(self, weekly_stats, num_scarcity_weeks, num_surplus_weeks, num_volatility_weeks):
        """
        Select weekly stress periods using EXACT same logic as current weekly_stress.
        Only difference: configurable counts instead of hardcoded 2.
        """
        import pandas as pd
        df_weeks = pd.DataFrame(weekly_stats)
        selected_periods = []
        used_week_indices = set()
        
        # SCARCITY WEEKS SELECTION (EXACT same logic as current, just configurable count)
        if num_scarcity_weeks > 0:
            worst_weeks = df_weeks.sort_values('week_avg_coverage', ascending=True).head(num_scarcity_weeks)
            used_week_indices.update(worst_weeks['week_index'])
            
            print(f"\n   🌨️ SUSTAINED STRESS WEEKS:")
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
                selected_periods.append(period_info)
        
        # TODO: Add surplus and volatility weeks selection if needed in future
        # (Current implementation only has scarcity weeks)
        
        return selected_periods

    # ==========================================
    # STRESS SCENARIO GENERATION METHODS
    # ==========================================
    

    
      
    
    # ==========================================
    # BASE AGGREGATION AND MAPPING METHODS
    # ==========================================
    
    def _create_scenario_base_aggregation(self, net_load, scenario_name, periods, segments, config, max_base_timeslices=48):
        """Create scenario-specific base aggregation using num_aggregated_ts from configuration"""
        
        # Extract num_aggregated_ts from configuration
        import pandas as pd
        num_aggregated_ts = None
        
        # Try different possible column names for the target timeslices
        for param in ['num_aggregated_ts', 'target_timeslices']:
            if param in config and pd.notna(config.get(param)) and config.get(param, 0) > 0:
                num_aggregated_ts = int(config.get(param))
                break
        
        # If no explicit target found in config, use fallback logic
        if num_aggregated_ts is None:
            num_periods = len(periods)
            
            if num_periods == 0:
                # CLUSTERING-ONLY scenario: Extract from scenario name as fallback
                if 'ts12_clu' in scenario_name:
                    num_aggregated_ts = 12
                elif 'ts24_clu' in scenario_name:
                    num_aggregated_ts = 24
                elif 'ts48_clu' in scenario_name:
                    num_aggregated_ts = 48
                else:
                    num_aggregated_ts = 48  # Default for unknown clustering configs
                
                print(f"      🎯 Clustering-only: Using {num_aggregated_ts} total timeslices (fallback from scenario name)")
            else:
                # STRESS-BASED scenario: Use inverse logic as fallback
                if num_periods >= 15:  # Very complex scenario (like s5p5v5_d with 15 periods)
                    num_aggregated_ts = 12  # Exactly 12 base slices
                elif num_periods >= 9:   # Complex scenario (like s3p3v3_d with 9 periods)
                    num_aggregated_ts = 24  # 24 base slices
                elif num_periods >= 4:   # Medium scenario (like s2_w_p2_d with 4 periods)
                    num_aggregated_ts = 36  # 36 base slices
                else:  # Simple scenario (like s1p1v1_d with 3 periods)
                    num_aggregated_ts = 48  # Full 48 base slices
                
                print(f"      🎯 Stress-based: Using {num_aggregated_ts} base timeslices (fallback logic)")
        else:
            print(f"      🎯 Using num_aggregated_ts from configuration: {num_aggregated_ts}")
        
        # Create base aggregation with the determined target
        base_scheme = self._create_base_aggregation(net_load, num_aggregated_ts, 
                                                   stress_segments=segments, scenario_name=scenario_name, config=config)
        
        return base_scheme
    
    def _create_base_aggregation(self, net_load, max_base_timeslices=48, stress_segments=None, scenario_name=None, config=None): 
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
        # Load from stress_periods_config table or use defaults
        if config is not None:
            n_seasons = config.get('num_aggregated_months', 4)
            n_daily_periods = config.get('num_aggregated_hours', 6)
        else:
            # Fallback to defaults if no config provided
            n_seasons = 4
            n_daily_periods = 6
            
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
        
        # Use configured daily periods
        daily_labels = self._contiguous_cluster(hourly_patterns, n_daily_periods, is_circular=True)
        
        # Create hour segment names as H01, H02, H03, etc.
        daily_names = [f'H{i+1:02d}' for i in range(n_daily_periods)]  # H01, H02, H03, H04, etc.
        hours = {i+1: daily_names[daily_labels[i]] for i in range(24)}
        
        total_combinations = n_seasons * n_daily_periods
        
        # Add scenario-specific information to the output
        scenario_info = f" for {scenario_name}" if scenario_name else ""
        print(f"      🎯 Base aggregation{scenario_info}: {n_seasons} seasons (S01-S{n_seasons:02d}) × {n_daily_periods} hour periods (H01-H{n_daily_periods:02d}) = {total_combinations} base timeslices")
        
        return {'months': months, 'hours': hours, 'scenario_name': scenario_name, 'n_seasons': n_seasons, 'n_daily_periods': n_daily_periods}
    
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
    
    def _create_consolidated_tsdesign(self, iso_code, scenario_mappings, scenario_base_schemes, output_dir):
        """Create consolidated tsdesign file with all scenarios in one table using scenario-specific base schemes"""
        
        # Use actual scenarios from configuration (dynamic, not hardcoded)
        expected_scenarios = list(scenario_mappings.keys())
        
        consolidated_rows = []
        
        # Step 1: Add scenario-specific month mappings (now different across scenarios!)
        for month in range(1, 13):
            new_row = {'description': 'month', 'sourcevalue': month}
            for scenario_name in expected_scenarios:
                base_scheme = scenario_base_schemes[scenario_name]
                new_row[scenario_name] = base_scheme['months'][month]  # Scenario-specific season
            consolidated_rows.append(new_row)
        
        # Step 2: Add scenario-specific hour mappings (now different across scenarios!)
        for hour in range(1, 25):
            new_row = {'description': 'hour', 'sourcevalue': hour}
            for scenario_name in expected_scenarios:
                base_scheme = scenario_base_schemes[scenario_name]
                new_row[scenario_name] = base_scheme['hours'][hour]  # Scenario-specific period
            consolidated_rows.append(new_row)
        
        # Step 3: Handle advanced periods - collect all periods from all scenarios
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

        # Step 4: Add hydro_af scenario P10/P50/P90
        from shared_data_loader import get_shared_loader
        shared_loader = get_shared_loader("data/")
        config_df = shared_loader.get_vs_mappings_sheet("stress_periods_config")

        hydro_af_row = {'description': 'hydro_af', 'sourcevalue': 'hydro_af'}
        for scenario_name in expected_scenarios:
            # Get hydro_af value from stress_periods_config for this scenario
            hydro_scenario = config_df[config_df['name'] == scenario_name]['hydro_af'].iloc[0]
            hydro_af_row[scenario_name] = hydro_scenario

        consolidated_rows.append(hydro_af_row)
        
        # Convert to DataFrame
        consolidated_df = pd.DataFrame(consolidated_rows)
        
        # Reorder columns
        column_order = ['description', 'sourcevalue'] + expected_scenarios
        consolidated_df = consolidated_df[column_order]
        
        # Save consolidated file
        filename = output_dir / f"tsdesign_{iso_code}.csv"
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
    
    def _format_date_mmmdd(self, month, day):
        """Convert month number and day to '30Mar' format"""
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return f"{day:02d}{month_names[month-1]}"
    
    def _get_country_name(self, iso_code):
        """Convert ISO code to readable country name using centralized function"""
        try:
            import sys
            from pathlib import Path
            parent_dir = Path(__file__).parent.parent.parent
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))
            
            from data_utils import get_country_name_from_iso
            return get_country_name_from_iso(iso_code)
                
        except Exception as e:
            return iso_code  # Fallback to ISO code
    
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
    
    def _generate_calendar_year_visualization(self, iso_code, output_dir):
        """Generate calendar year visualization using the calendar heatmap visualizer"""
        try:
            # Import the calendar visualizer
            import sys
            from pathlib import Path
            
            # Add the scripts directory to the path
            scripts_dir = Path(__file__).parent
            sys.path.insert(0, str(scripts_dir))
            
            from calendar_heatmap_visualizer import EnhancedCalendarHeatmapVisualizer
            
            print(f"   📅 Generating calendar year visualization for {iso_code}...")
            
            # Check if daily coverage JSON exists
            daily_coverage_file = output_dir / f"daily_coverage_{iso_code}.json"
            if not daily_coverage_file.exists():
                print(f"   ⚠️  Daily coverage file not found: {daily_coverage_file}")
                return
            
            # Create visualizer and generate charts
            visualizer = EnhancedCalendarHeatmapVisualizer()
            
            # Load data and create charts
            with open(daily_coverage_file, 'r') as f:
                import json
                coverage_data = json.load(f)
            
            # Generate calendar heatmap
            calendar_output = output_dir / f"calendar_year_{iso_code}.png"
            visualizer.create_calendar_heatmap(coverage_data, str(calendar_output))
            
            # Generate monthly summary
            monthly_output = output_dir / f"monthly_summary_{iso_code}.png"
            visualizer.create_monthly_summary_heatmap(coverage_data, str(monthly_output))
            
            print(f"   ✅ Calendar year visualization completed for {iso_code}")
            
        except Exception as e:
            print(f"   ❌ Error generating calendar year visualization for {iso_code}: {e}")
            import traceback
            traceback.print_exc()

    def _generate_calendar_charts(self, iso_code, output_dir):
        """Generate calendar year and monthly summary charts"""
        try:
            print(f"   📅 Generating calendar charts for {iso_code}...")
            
            # Check if daily coverage JSON exists
            daily_coverage_file = output_dir / f"daily_coverage_{iso_code}.json"
            if not daily_coverage_file.exists():
                print(f"   ⚠️  Daily coverage file not found: {daily_coverage_file}")
                return

            # Load daily coverage data
            with open(daily_coverage_file, 'r') as f:
                import json
                coverage_data = json.load(f)

            # Extract daily coverage values
            daily_values = coverage_data.get('daily_coverage', [])
            if not daily_values:
                print(f"   ⚠️  No daily coverage data found in {daily_coverage_file}")
                return

            # Create calendar year heatmap
            self._create_calendar_year_heatmap(iso_code, daily_values, output_dir)
            
            print(f"   ✅ Calendar charts completed for {iso_code}")

        except Exception as e:
            print(f"   ❌ Error generating calendar charts for {iso_code}: {e}")
            import traceback
            traceback.print_exc()

    def _create_calendar_year_heatmap(self, iso_code, daily_values, output_dir):
        """Create calendar year heatmap visualization"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime, timedelta
            import numpy as np
            import calendar
            
            # Create figure with branding-compliant size
            fig, ax = plt.subplots(figsize=(11, 7))  # Standard branding size
            
            # Apply branding styling
            if BRANDING_AVAILABLE:
                branding_manager.apply_chart_style(ax, "calendar_heatmap")
            
            # Get country name
            country_name = self._get_country_name(iso_code)
            
            # Create date range for the year (assuming 2013 as per the data)
            year = 2013
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31)
            
            # Create calendar grid - 7 days x 53 weeks (maximum weeks in a year)
            calendar_data = np.full((7, 53), np.nan)
            
            # Populate calendar with daily values
            day_idx = 0
            for day_of_year in range(365):  # Full year
                if day_idx < len(daily_values):
                    current_date = start_date + timedelta(days=day_of_year)
                    # Use simple week number (0-52) based on day of year
                    week_num = day_of_year // 7
                    weekday = current_date.weekday()  # Monday=0, Sunday=6
                    
                    if 0 <= week_num < 53 and 0 <= weekday < 7:
                        # Use capped values for visualization (scale buster)
                        calendar_data[weekday, week_num] = min(daily_values[day_idx], 125.0)
                    day_idx += 1
            
            # Use branding manager's coverage colormap for consistency
            if BRANDING_AVAILABLE:
                cmap = branding_manager.create_coverage_colormap("calendar_heatmap")
            else:
                # Fallback colormap if branding not available
                from matplotlib.colors import ListedColormap
                colors_list = [
                    '#f8f9fa',      # No data (light gray)
                    '#ffebee',      # Very light red (shortage)
                    '#ffcdd2',      # Light red (moderate shortage)
                    '#ef9a9a',      # Red (low coverage)
                    '#ffb74d',      # Orange (balanced)
                    '#81c784',      # Green (good coverage)
                    '#4caf50',      # Dark green (surplus)
                    '#2e7d32'       # Very dark green (high surplus)
                ]
                cmap = ListedColormap(colors_list)
            
            # Scale buster: Cap all values > 125% to 125% for better visualization
            capped_values = [min(val, 125.0) for val in daily_values]
            
            # Normalize values to color indices with intuitive scale
            # Green (balanced) should be in the middle around 100%
            min_val = min(capped_values)
            max_val = 125.0  # Fixed maximum for scale consistency
            
            # Create a more intuitive scale where:
            # 0-50%: Red (shortage)
            # 50-100%: Orange (balanced) 
            # 100-125%: Green (surplus)
            norm = plt.Normalize(0, 125)
            
            # Create heatmap with capped values
            im = ax.imshow(calendar_data, cmap=cmap, aspect='auto', norm=norm)
            
            # Set ticks and labels for weeks (every 4 weeks) with better spacing
            week_ticks = list(range(0, 53, 4))
            week_labels = [f'W{i+1}' for i in week_ticks]
            ax.set_xticks(week_ticks)
            ax.set_xticklabels(week_labels, rotation=45)
            
            # Add minor week labels for better readability (every 2 weeks to reduce overlap)
            minor_week_ticks = list(range(0, 53, 2))
            ax.set_xticks(minor_week_ticks, minor=True)
            ax.set_xticklabels([f'{i+1}' for i in minor_week_ticks], minor=True)
            
            # Set ticks and labels for days
            ax.set_yticks(range(7))
            ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
            
            # Add month labels at the top with visual separators
            month_positions = []
            month_names = []
            month_week_positions = []  # Store week positions for separators
            
            for month in range(1, 13):
                month_start = datetime(year, month, 1)
                # Calculate week number based on day of year
                day_of_year = (month_start - start_date).days
                week_num = day_of_year // 7
                if 0 <= week_num < 53:
                    month_positions.append(week_num)
                    month_names.append(calendar.month_abbr[month])
                    month_week_positions.append(week_num)
            
            # Add month labels with branding colors
            neutral_colors = branding_manager.branding_config.get('colors', {}).get('neutral', {}) if BRANDING_AVAILABLE else {}
            month_bg_color = neutral_colors.get('light_gray', '#f8f9fa')
            month_edge_color = neutral_colors.get('gray', '#dee2e6')
            
            for pos, name in zip(month_positions, month_names):
                ax.text(pos, -1.2, name, ha='center', va='top',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor=month_bg_color, edgecolor=month_edge_color))
            
            # Add visual separators between months (vertical lines) with branding colors
            for i, week_pos in enumerate(month_week_positions[1:], 1):  # Skip first month
                if week_pos > 0:  # Don't draw line at week 0
                    # Draw vertical line spanning the full height of the chart
                    ax.axvline(x=week_pos - 0.5, color=month_edge_color, linewidth=2, alpha=0.7, linestyle='--')
                    # Add subtle horizontal line at the top for month separation
                    ax.axhline(y=-0.8, xmin=0, xmax=1, color=month_edge_color, linewidth=1, alpha=0.5)
            
            # Add colorbar with small size (branding compliant)
            cbar = plt.colorbar(im, ax=ax, shrink=0.6, aspect=20)
            cbar.set_label('Daily Coverage (%)', fontsize=7)  # Use branding axis size
            
            # Create intuitive legend with branding colors
            if BRANDING_AVAILABLE:
                coverage_colors = branding_manager.branding_config.get('colors', {}).get('gradients', {}).get('coverage', {})
                legend_elements = [
                    plt.Rectangle((0, 0), 1, 1, facecolor=coverage_colors.get('shortage', '#ffcdd2'), label='Shortage (<50%)'),
                    plt.Rectangle((0, 0), 1, 1, facecolor=coverage_colors.get('moderate', '#ffb74d'), label='Balanced (50-100%)'),
                    plt.Rectangle((0, 0), 1, 1, facecolor=coverage_colors.get('surplus', '#4caf50'), label='Surplus (100-125%)')
                ]
            else:
                # Fallback legend colors
                legend_elements = [
                    plt.Rectangle((0, 0), 1, 1, facecolor='#ffcdd2', label='Shortage (<50%)'),
                    plt.Rectangle((0, 0), 1, 1, facecolor='#ffb74d', label='Balanced (50-100%)'),
                    plt.Rectangle((0, 0), 1, 1, facecolor='#4caf50', label='Surplus (100-125%)')
                ]
            
            # Position legend according to branding config (right side) with branding colors
            ax.legend(handles=legend_elements, loc='center right', bbox_to_anchor=(1.15, 0.5),
                     ncol=1, frameon=True, fancybox=True, shadow=True,
                     facecolor=month_bg_color, edgecolor=month_edge_color)
            
            # Enhanced coverage statistics box with scale-busted values
            total_days = len(daily_values)
            original_max = max(daily_values)
            capped_max = max(capped_values)
            
            shortage_days = sum(1 for val in daily_values if val < 50)  # Less than 50% coverage
            balanced_days = sum(1 for val in daily_values if 50 <= val <= 100)  # 50-100% coverage
            surplus_days = sum(1 for val in daily_values if val > 100)  # More than 100% coverage
            scale_busted_days = sum(1 for val in daily_values if val > 125)  # Days capped at 125%
            
            coverage_stats = f"""Coverage Statistics
📊 Total Days: {total_days}
🔴 Shortage (<50%): {shortage_days} days
🟠 Balanced (50-100%): {balanced_days} days
🟢 Surplus (100-125%): {surplus_days} days
⚠️ Scale Busted (>125%): {scale_busted_days} days
📈 Min: {min_val:.1f}%
📈 Max: {capped_max:.1f}% (capped from {original_max:.1f}%)
📈 Mean: {np.mean(capped_values):.1f}%"""
            
            # Position statistics box according to branding config (below legend) with branding colors
            ax.text(1.08, 0.3, coverage_stats, transform=ax.transAxes,
                   verticalalignment='top', horizontalalignment='left',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor=month_bg_color, edgecolor=month_edge_color))
            
            # Set title and labels (no hardcoded font sizes)
            ax.set_title(f'Daily Renewable Energy Coverage - {country_name} ({year})')
            ax.set_xlabel('Week of Year')
            ax.set_ylabel('Day of Week')
            
            # CRITICAL: Finalize styling after all chart elements are set
            if BRANDING_AVAILABLE:
                branding_manager.apply_figure_style(fig)
                branding_manager.finalize_chart_style(ax)
            
            # Add logos and main title in header band
            if BRANDING_AVAILABLE:
                branding_manager.add_logos_to_chart(fig, "small", f"Daily Renewable Energy Coverage - {country_name} ({year})")
            
            # Adjust layout with branding-compliant padding
            plt.tight_layout(pad=1.0)
            
            # Save chart with branding-compliant parameters
            output_file = output_dir / f"calendar_year_{iso_code}.png"
            plt.savefig(output_file, dpi=300, bbox_inches=None, pad_inches=0.2)
            plt.close()  # Prevent auto-opening
            
            print(f"   ✅ Calendar year heatmap saved: {output_file}")
            
        except Exception as e:
            print(f"   ❌ Error creating calendar year heatmap: {e}")
            import traceback
            traceback.print_exc()

    def _create_monthly_summary_heatmap(self, iso_code, daily_values, output_dir):
        """Create monthly summary heatmap visualization"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            import calendar
            from datetime import datetime
            
            # Create figure with branding-compliant size
            fig, ax = plt.subplots(figsize=(11, 7))  # Standard branding size
            if BRANDING_AVAILABLE:
                branding_manager.apply_chart_style(ax, "monthly_summary")
            
            # Get country name
            country_name = self._get_country_name(iso_code)
            
            # Organize data by month
            year = 2013
            monthly_data = []
            month_names = []
            
            day_idx = 0
            for month in range(1, 13):
                month_name = calendar.month_abbr[month]
                month_names.append(month_name)
                
                days_in_month = calendar.monthrange(year, month)[1]
                month_values = []
                
                for day in range(days_in_month):
                    if day_idx < len(daily_values):
                        month_values.append(daily_values[day_idx])
                        day_idx += 1
                
                monthly_data.append(month_values)
            
            # Create heatmap data
            max_days = max(len(month) for month in monthly_data)
            heatmap_data = np.full((12, max_days), np.nan)
            
            for i, month_values in enumerate(monthly_data):
                for j, value in enumerate(month_values):
                    heatmap_data[i, j] = value
            
            # Create color mapping (same as calendar year)
            colors_list = [
                '#f8f9fa',      # No data (very light gray)
                '#ffebee',      # Extreme shortage (very light red)
                '#ffcdd2',      # Shortage (light red)
                '#ef9a9a',      # Moderate shortage (red)
                '#e57373',      # Low coverage (medium red)
                '#ffb74d',      # Moderate coverage (orange)
                '#81c784',      # Adequate coverage (green)
                '#4db6ac',      # Good coverage (teal)
                '#64b5f6',      # High coverage (blue)
                '#9575cd',      # Surplus (purple)
                '#5d4037'       # Extreme surplus (dark brown)
            ]
            
            from matplotlib.colors import ListedColormap
            cmap = ListedColormap(colors_list)
            
            # Normalize values
            min_val = min(daily_values)
            max_val = max(daily_values)
            norm = plt.Normalize(min_val, max_val)
            
            # Create heatmap
            im = ax.imshow(heatmap_data, cmap=cmap, aspect='auto', norm=norm)
            
            # Set ticks and labels
            ax.set_xticks(range(0, max_days, 5))
            ax.set_xticklabels([f'Day {i+1}' for i in range(0, max_days, 5)])
            ax.set_yticks(range(12))
            ax.set_yticklabels(month_names)
            
            # Add day labels with smaller font
            for i in range(0, max_days, 5):
                ax.text(i, -0.5, f'Day {i+1}', ha='center', va='top', fontsize=8,
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='#f8f9fa', edgecolor='#dee2e6'))
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label('Daily Coverage (%)')
            
            # Create legend
            legend_elements = [
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[0], label='No Data'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[1], label='Extreme Shortage'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[2], label='Shortage'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[3], label='Moderate Shortage'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[4], label='Low Coverage'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[5], label='Moderate Coverage'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[6], label='Adequate Coverage'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[7], label='Good Coverage'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[8], label='High Coverage'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[9], label='Surplus'),
                plt.Rectangle((0, 0), 1, 1, facecolor=colors_list[10], label='Extreme Surplus')
            ]
            
            # Position legend
            ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.3),
                     ncol=3, frameon=True, fancybox=True, shadow=True,
                     facecolor='#f8f9fa', edgecolor='#dee2e6')
            
            # Add statistics box
            coverage_stats = f"Coverage Statistics\nMin: {min_val:.1f}%\nMax: {max_val:.1f}%\nMean: {np.mean(daily_values):.1f}%"
            ax.text(1.02, 0.98, coverage_stats, transform=ax.transAxes, fontsize=10,
                   verticalalignment='top', horizontalalignment='left',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='#f8f9fa', edgecolor='#dee2e6'))
            
            # Set title and labels
            ax.set_title(f'Monthly Daily Coverage Summary - {country_name} ({year})')
            ax.set_xlabel('Day of Month')
            ax.set_ylabel('Month')
            
            # Apply branding and finalize
            if BRANDING_AVAILABLE:
                branding_manager.apply_figure_style(fig)
                branding_manager.finalize_chart_style(ax)
            
            # Save chart
            output_file = output_dir / f"monthly_summary_{iso_code}.png"
            plt.savefig(output_file, dpi=300, bbox_inches=None, pad_inches=0.2)
            plt.close()
            
            print(f"   ✅ Monthly summary heatmap saved: {output_file}")
            
        except Exception as e:
            print(f"   ❌ Error creating monthly summary heatmap: {e}")
            import traceback
            traceback.print_exc()

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
    target_isos = ['IND']  # Default demo ISO
    
    # Handle both --iso format and direct ISO format
    if len(sys.argv) > 1:
        if sys.argv[1].startswith('--iso') and len(sys.argv) > 2:
            # Format: --iso CHE
            target_isos = [sys.argv[2]]
        elif not sys.argv[1].startswith('--'):
            # Format: CHE or CHE,USA,DEU
            target_isos = sys.argv[1].split(',')
        else:
            print(f"⚠️  Unrecognized argument format: {sys.argv[1]}")
            print("💡 Usage: python stress_period_analyzer.py --iso CHE")
            print("💡 Or: python stress_period_analyzer.py CHE")
            print(f"📋 Using default demo ISO: {target_isos}")
    else:
        print(f"📋 Using default demo ISO: {target_isos}")
        print("💡 Usage: python stress_period_analyzer.py --iso CHE")
        print("💡 Or: python stress_period_analyzer.py CHE")
    
    # Initialize processor with configuration support
    # Auto-detect correct data path for our 8760 constructor integration
    import os
    if os.path.exists("data/"):
        data_path = "data/"  # Running from project root
    else:
        data_path = "../data/"  # Running from scripts directory
        
    processor = VerveStacksTimesliceProcessor(
        max_timeslices=None,  # Will use config file value
        data_path=data_path,  # Auto-detected path
        config_path="./config/"
    )
    
    # Run with enhanced hybrid approach
    print("🚀 Running hybrid approach with original's period selection logic...")
    results = processor.run_full_pipeline(
        target_isos=target_isos, 
        save_results=True
        # output_dir will default to script_dir/../outputs (2_ts_design/outputs/)
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