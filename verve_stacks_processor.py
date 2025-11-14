import pandas as pd
import duckdb
import os
import pycountry
import re
import pickle
from pathlib import Path
import logging
from shared_data_loader import get_shared_loader

class VerveStacksProcessor:
    """
    Main processor for VerveStacks energy data compilation.
    Loads global datasets once and processes multiple ISOs efficiently.
    """
    
    def __init__(self, data_dir="data", cache_dir="cache", force_reload=False):
        """
        Initialize the processor with global datasets.
        
        Args:
            data_dir: Directory containing input data files
            cache_dir: Directory for caching processed data
            force_reload: If True, reload data even if cache exists
        """
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Global datasets - loaded once
        self.df_irena_c = None
        self.df_irena_g = None
        self.df_ember = None
        self.df_gem = None
        self.df_gem_map = None
        self.df_gem_status_map = None
        self.df_irena_ember_map = None
        self.ngfs_df = None
        self.df_unsd = None
        self.df_unsd_regmap = None
        self.df_unsd_prodmap = None
        self.df_unsd_flowmap = None
        self.df_unsd_trade = None
        self.df_electricity_trade = None
        self.df_ember_trade = None
        
        # REZoning data for grid modeling
        self.df_solar_rezoning = None
        self.df_windon_rezoning = None
        self.df_windoff_rezoning = None
        
        # Store force_reload flag for shared loader
        self.force_reload = force_reload
        
        # Load or cache data
        self._load_global_data(force_reload)
    
    def _load_global_data(self, force_reload=False):
        """Load global datasets, using cache if available."""
        cache_file = self.cache_dir / "global_data_cache.pkl"
        
        if not force_reload and cache_file.exists():
            self.logger.info("Loading data from cache...")
            self._load_from_cache(cache_file)
        else:
            self.logger.info("Loading fresh data from files...")
            self._load_fresh_data()
            self._save_to_cache(cache_file)
    
    def _load_fresh_data(self):
        """Load all global datasets from source files using shared data loader."""
        # Initialize shared data loader
        self.shared_loader = get_shared_loader(self.data_dir, cache_enabled=not self.force_reload)
        
        self.logger.info("Loading IRENA data...")
        self.df_irena_c = self.shared_loader.get_irena_capacity_data()
        self.df_irena_g = self.shared_loader.get_irena_generation_data()
        
        self.logger.info("Loading EMBER data...")
        self.df_ember = self.shared_loader.get_ember_data()
        
        self.logger.info("Loading GEM data...")
        self.df_gem = pd.read_excel(self.data_dir / "existing_stock/Global-Integrated-Power-April-2025.xlsx", 
                                   sheet_name="Power facilities")
        
        self.logger.info("Loading mapping files...")
        self.df_gem_map = self.shared_loader.get_vs_mappings_sheet("gem_techmap")
        self.df_gem_status_map = self.shared_loader.get_vs_mappings_sheet("gem_statusmap")
        self.df_irena_ember_map = self.shared_loader.get_vs_mappings_sheet("irena_ember_typemap")
        
        self.logger.info("Loading NGFS data...")
        # Initialize empty dataframe
        self.ngfs_df = pd.DataFrame()
        
        # Load MESSAGEix-GLOBIOM data
        downscaled_file_path_1 = self.data_dir / "ipcc_iamc/NGFS4.2/Downscaled_MESSAGEix-GLOBIOM 1.1-M-R12_data.xlsx"
        if downscaled_file_path_1.exists():
            df1 = pd.read_excel(downscaled_file_path_1)
            self.ngfs_df = pd.concat([self.ngfs_df, df1], ignore_index=True)
            self.logger.info(f"Loaded MESSAGEix-GLOBIOM data: {len(df1)} rows")
        else:
            self.logger.warning(f"NGFS file not found: {downscaled_file_path_1}")
            
        # Load REMIND-MAgPIE data
        downscaled_file_path_2 = self.data_dir / "ipcc_iamc/NGFS4.2/Downscaled_REMIND-MAgPIE 3.2-4.6_data.xlsx"
        if downscaled_file_path_2.exists():
            df2 = pd.read_excel(downscaled_file_path_2)
            self.ngfs_df = pd.concat([self.ngfs_df, df2], ignore_index=True)
            self.logger.info(f"Loaded REMIND-MAgPIE data: {len(df2)} rows")
        else:
            self.logger.warning(f"NGFS file not found: {downscaled_file_path_2}")
        
        self.logger.info(f"Total NGFS data loaded: {len(self.ngfs_df)} rows")
        
        self.logger.info("Loading UNSD data...")
        self.df_unsd = pd.read_csv(self.data_dir / "unsd/unsd_july_2025.csv")
        self.df_unsd_regmap = self.shared_loader.get_vs_mappings_sheet("unsd_region_map")
        self.df_unsd_prodmap = self.shared_loader.get_vs_mappings_sheet("unsd_product_map")
        self.df_unsd_flowmap = self.shared_loader.get_vs_mappings_sheet("unsd_flow_map")
        
        # Register UNSD DataFrames with DuckDB for SQL operations
        duckdb.register('df_unsd', self.df_unsd)
        duckdb.register('df_unsd_prodmap', self.df_unsd_prodmap)
        duckdb.register('df_unsd_flowmap', self.df_unsd_flowmap)
        duckdb.register('df_unsd_regmap', self.df_unsd_regmap)
        
        # Create electricity trade data
        self.logger.info("Processing UNSD electricity trade data...")
        self.df_unsd_trade = duckdb.sql("""
            SELECT T1.TIME_PERIOD AS year,round(SUM(cast(T1.OBS_VALUE as float) * T1.CONVERSION_FACTOR / 1000 / 3.6),1) as twh_UNSD
            ,T3.attribute,T4.ISO
            from 
            df_unsd T1
            inner join df_unsd_prodmap T2 ON cast(T2.Code as varchar) = cast(T1.COMMODITY as varchar)
            inner join df_unsd_flowmap T3 ON cast(T3.Code as varchar) = cast(T1.TRANSACTION as varchar)
            inner join df_unsd_regmap T4 ON cast(T4.Code as varchar) = cast(T1.REF_AREA as varchar)
            where 
            commodity = 7000 AND
             T3.attribute.lower() IN ('import','export') AND
             T1.TIME_PERIOD >= 2000
            group by T1.TIME_PERIOD,T3.attribute,T4.ISO
        """).df()
        
        # Create electricity trade pivot table
        self.df_electricity_trade = self.df_unsd_trade.pivot(index=["ISO", "attribute"], columns="year", values="twh_UNSD")
        
        # Process EMBER electricity trade data as backup
        self.logger.info("Processing EMBER electricity trade data...")
        ember_trade = self.df_ember[self.df_ember['Variable'] == 'Net Imports'].copy()
        ember_trade = ember_trade.rename(columns={'Country code': 'ISO', 'Value': 'net_imports_twh'})
        
        # Create pivot table for EMBER net imports
        self.df_ember_trade = ember_trade.pivot_table(
            index='ISO', 
            columns='Year', 
            values='net_imports_twh',
            aggfunc='first'
        ).reset_index()
        
        # Apply all the preprocessing that was in Cell 0
        self._preprocess_data()
    
    def _preprocess_data(self):
        """Apply all preprocessing that was in the original Cell 0."""
        # Remove cancelled/shelved/retired from GEM
        # self.df_gem = self.df_gem[~self.df_gem['Status'].str.lower().str.startswith(('cancelled', 'shelved', 'retired','announced','pre-construction'))]
        # 21-09-25: Only excludes retired. other statuses will be offered as potential new techs
        self.df_gem = self.df_gem[~self.df_gem['Status'].str.lower().str.startswith(('retired'))]

        # Remove cancelled/shelved plants unless Type is hydropower
        mask_cancelled_shelved = (
            self.df_gem['Status'].str.lower().str.startswith(('cancelled', 'shelved'))
            & (self.df_gem['Type'].str.lower() != 'hydropower')
        )
        self.df_gem = self.df_gem[~mask_cancelled_shelved]

        cancelled_coal_remaining = self.df_gem[
        (self.df_gem['Status'].str.lower().str.startswith(('cancelled', 'shelved'))) &
        (self.df_gem['Type'].str.lower() == 'coal')
        ]
        print(f"🐛 DEBUG: {len(cancelled_coal_remaining)} cancelled coal plants remaining after filtering")
        if len(cancelled_coal_remaining) > 0:
            print("Sample cancelled coal plants still in data:")
            print(cancelled_coal_remaining[['Plant / Project name', 'Status', 'Type', 'Country/area']].head())
        
        # Technology = Type for if missing
        self.df_gem['Technology'] = self.df_gem.apply(
            lambda row: row['Type'] if pd.isna(row['Technology']) else row['Technology'], axis=1
        )
        
        def custom_type(row):
            if row['Type'] == 'oil/gas':
                if pd.notna(row['Fuel']):
                    fuel_val = str(row['Fuel'])
                else:
                    fuel_val = ''
                if fuel_val.lower().startswith('fossil liquids:'):
                    return 'oil'
                else:
                    return 'gas'
            else:
                return row['Type']

        self.df_gem['Type_mod'] = self.df_gem.apply(custom_type, axis=1)

        # Add model_fuel and model_name to GEM using mapping table
        self.df_gem = self.df_gem.merge(
            self.df_gem_map[['Type_mod', 'Technology', 'model_fuel', 'model_name']], 
            on=['Type_mod', 'Technology'], 
            how='left'
        )

        # 21-09-25: Add status detail to model_name
        self.df_gem = self.df_gem.merge(
            self.df_gem_status_map[['status', 'model_name']], 
            left_on='Status', 
            right_on='status',
            how='left',
            suffixes=('', '_status')
        )
        
        # Prefix model_name with status model_name
        self.df_gem['model_name'] = self.df_gem['model_name_status'].fillna('') + self.df_gem['model_name'].fillna('')
        
        # Clean up temporary columns
        self.df_gem = self.df_gem.drop(['model_name_status', 'status'], axis=1)


        # Handle unmapped combinations with fallback logic
        def fallback_fuel_and_name(row):
            if pd.isna(row['model_fuel']):
                # Debug: Print unmapped combinations
                print(f"🔧 UNMAPPED: Type='{row['Type']}', Technology='{row['Technology']}', Country='{row.get('Country', 'N/A')}'")
                
                if row['Type'] == 'oil/gas':
                    if pd.notna(row['Fuel']):
                        fuel_val = str(row['Fuel'])
                        if fuel_val.lower().startswith('fossil liquids:'):
                            fallback_value = 'oil'
                        else:
                            fallback_value = 'gas'
                    else:
                        fallback_value = 'gas'
                elif row['Type'] == 'hydropower':
                    fallback_value = 'hydro'
                else:
                    fallback_value = row['Type']
                
                print(f"   → FALLBACK: model_fuel='{fallback_value}'")
                return fallback_value
            else:
                return row['model_fuel']
        
        # Count unmapped records before applying fallback
        unmapped_count = self.df_gem['model_fuel'].isna().sum()
        if unmapped_count > 0:
            print(f"\n🚨 Found {unmapped_count} unmapped (Type, Technology) combinations:")
        
        self.df_gem['model_fuel'] = self.df_gem.apply(fallback_fuel_and_name, axis=1)
        
        # Verify no NaN values remain
        remaining_nan = self.df_gem['model_fuel'].isna().sum()
        if remaining_nan > 0:
            print(f"⚠️  WARNING: {remaining_nan} model_fuel values are still NaN after fallback!")
        else:
            print(f"✅ All model_fuel values resolved (no NaN remaining)")
        
        # Fill missing model_names with ep_ prefix pattern
        self.df_gem['model_name'] = self.df_gem['model_name'].fillna(
            self.df_gem['model_fuel'].apply(lambda x: f'ep_{x}')
        )
        
        # Clean country names in IRENA dataframes
        def clean_country_name(country_name):
            if isinstance(country_name, str):
                return re.sub(r'\s*\(.*\)\s*$', '', country_name).strip()
            return country_name
        
        self.df_irena_c['Country/area'] = self.df_irena_c['Country/area'].apply(clean_country_name)
        self.df_irena_g['Country/area'] = self.df_irena_g['Country/area'].apply(clean_country_name)
        
        # Rename columns
        self.df_ember = self.df_ember.rename(columns={'Variable': 'Type', 'Country code': 'iso_code'})

        # Filter EMBER data to only include fuel data (no aggregations - including the total row)
        self.df_ember = self.df_ember[self.df_ember['Subcategory'] == 'Fuel']
        
        # Register DataFrames with DuckDB before using them in SQL
        duckdb.register('df_ember', self.df_ember)
        duckdb.register('df_irena_ember_map', self.df_irena_ember_map)
        
        # Add model_fuel to ember
        self.df_ember = duckdb.sql("""
            SELECT T2.model_fuel, T1.* 
            FROM df_ember T1 
            INNER JOIN df_irena_ember_map T2 ON T1.Type=T2.Type AND T2.Source='EMBER'
        """).df()
        
        # Rename Technology column to Type in IRENA dataframes
        self.df_irena_c = self.df_irena_c.rename(columns={'Technology': 'Type'})
        self.df_irena_g = self.df_irena_g.rename(columns={'Technology': 'Type'})
        
        # Add ISO codes
        def get_iso_code(country_name):
            if not isinstance(country_name, str):
                return None
            name = country_name.strip().lower()
            special_cases = {
                'kosovo': 'XKX',
                'kosovo (under unscr 1244/99)': 'XKX',
                'chinese taipei': 'TWN',
                'republic of korea': 'KOR',
                'china, hong kong special administrative region': 'HKG',
                'democratic republic of the congo': 'COD',
                'russia': 'RUS',
                'dr congo': 'COD',
            }
            if name in special_cases:
                return special_cases[name]
            try:
                return pycountry.countries.lookup(country_name).alpha_3
            except (LookupError, AttributeError, ImportError):
                return None
        
        self.df_irena_c['iso_code'] = self.df_irena_c['Country/area'].apply(get_iso_code)
        self.df_irena_g['iso_code'] = self.df_irena_g['Country/area'].apply(get_iso_code)
        self.df_gem['iso_code'] = self.df_gem['Country/area'].apply(get_iso_code)
        
        # Register IRENA DataFrames with DuckDB before using them in SQL
        duckdb.register('df_irena_c', self.df_irena_c)
        duckdb.register('df_irena_g', self.df_irena_g)
        
        # Add model_fuel to IRENA
        self.df_irena_c = duckdb.sql("""
            SELECT T2.model_fuel, T1.* 
            FROM df_irena_c T1 
            INNER JOIN df_irena_ember_map T2 ON T1.Type=T2.Type AND T2.Source='IRENA'
        """).df()
        
        self.df_irena_g = duckdb.sql("""
            SELECT T2.model_fuel, T1.* 
            FROM df_irena_g T1 
            INNER JOIN df_irena_ember_map T2 ON T1.Type=T2.Type AND T2.Source='IRENA'
        """).df()
        
        # Load REZoning data for grid modeling using shared_data_loader
        self.logger.info("Loading REZoning data...")
        rezoning_data = self.shared_loader.get_rezoning_data(force_reload=self.force_reload)
        self.df_solar_rezoning = rezoning_data.get('df_rez_solar')
        self.df_windon_rezoning = rezoning_data.get('df_rez_wind')
        self.df_windoff_rezoning = rezoning_data.get('df_rez_windoff', pd.DataFrame())
    
    def _save_to_cache(self, cache_file):
        """Save processed data to cache."""
        cache_data = {
            'df_irena_c': self.df_irena_c,
            'df_irena_g': self.df_irena_g,
            'df_ember': self.df_ember,
            'df_gem': self.df_gem,
            'df_gem_map': self.df_gem_map,
            'df_gem_status_map': self.df_gem_status_map,
            'df_irena_ember_map': self.df_irena_ember_map,
            'ngfs_df': self.ngfs_df,
            'df_unsd': self.df_unsd,
            'df_unsd_regmap': self.df_unsd_regmap,
            'df_unsd_prodmap': self.df_unsd_prodmap,
            'df_unsd_flowmap': self.df_unsd_flowmap,
            'df_unsd_trade': self.df_unsd_trade,
            'df_electricity_trade': self.df_electricity_trade,
            'df_ember_trade': self.df_ember_trade,
            # Note: REZoning data (df_solar_rezoning, df_windon_rezoning, df_windoff_rezoning) 
            # is now handled by shared_data_loader for proper force_reload support
        }
        
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        self.logger.info(f"Data cached to {cache_file}")
    
    def _load_from_cache(self, cache_file):
        """Load processed data from cache."""
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
        
        for key, value in cache_data.items():
            setattr(self, key, value)
        
        self.logger.info("Data loaded from cache.")
    
    def get_ISOProcessor(self, input_iso, capacity_threshold=100, 
                   efficiency_adjustment_gas=1.0, efficiency_adjustment_coal=1.0,
                   output_dir="output", tsopt='ts12_clu', skip_timeslices=False, process_all_tsopts=False, grid_modeling=False, auto_commit=True, add_documentation=True, grids_override=None):
        """
        Process data for a specific ISO country code.
        
        Args:
            input_iso: 3-letter ISO country code (e.g., 'JPN', 'USA')
            capacity_threshold: MW threshold for individual plant tracking
            efficiency_adjustment_gas: Efficiency adjustment factor for gas plants
            efficiency_adjustment_coal: Efficiency adjustment factor for coal plants
            output_dir: Output directory for results
            tsopt: Time slice option (default: 'ts12_clu') - used when process_all_tsopts=False
            skip_timeslices: Whether to skip time-slice processing
            process_all_tsopts: If True, process all available ts_* options (ignores tsopt parameter)
            auto_commit: Whether to perform git operations (branch creation, commits, pushes)
            grid_modeling: Whether to enable grid modeling features
        """
        self.logger.info(f"Processing ISO: {input_iso}")
        
        # Create ISO-specific processor
        return ISOProcessor(
            self, input_iso, capacity_threshold,
            efficiency_adjustment_gas, efficiency_adjustment_coal,
            output_dir, tsopt, skip_timeslices, process_all_tsopts, auto_commit, grid_modeling, add_documentation, grids_override
        )
        
        
    
    
    def process_iso(self, input_iso, capacity_threshold=100, 
                   efficiency_adjustment_gas=1.0, efficiency_adjustment_coal=1.0,
                   output_dir="output", tsopt='ts12_clu', skip_timeslices=False, process_all_tsopts=False, grid_modeling=False, auto_commit=True, add_documentation=True, grids_override=None):
        """
        Process data for a specific ISO country code.
        
        Args:
            input_iso: 3-letter ISO country code (e.g., 'JPN', 'USA')
            capacity_threshold: MW threshold for individual plant tracking
            efficiency_adjustment_gas: Efficiency adjustment factor for gas plants
            efficiency_adjustment_coal: Efficiency adjustment factor for coal plants
            output_dir: Output directory for results
            tsopt: Time slice option (default: 'ts12_clu') - used when process_all_tsopts=False
            skip_timeslices: Whether to skip time-slice processing
            process_all_tsopts: If True, process all available ts_* options (ignores tsopt parameter)
            auto_commit: Whether to perform git operations (branch creation, commits, pushes)
            grid_modeling: Whether to enable grid modeling features
        """
        self.logger.info(f"Processing ISO: {input_iso}")
        
        # Create ISO-specific processor
        iso_processor = ISOProcessor(
            self, input_iso, capacity_threshold,
            efficiency_adjustment_gas, efficiency_adjustment_coal,
            output_dir, tsopt, skip_timeslices, process_all_tsopts, auto_commit, grid_modeling, add_documentation, grids_override
        )
        
        # Run the full processing pipeline
        iso_processor.run_full_pipeline()
        
        self.logger.info(f"Completed processing for {input_iso}")
    
    def get_available_isos(self):
        """Get list of available ISO codes in the data."""
        gem_isos = set(self.df_gem['iso_code'].dropna().unique())
        irena_isos = set(self.df_irena_c['iso_code'].dropna().unique())
        ember_isos = set(self.df_ember['iso_code'].dropna().unique())
        
        return sorted(gem_isos.intersection(irena_isos).intersection(ember_isos))


class ISOProcessor:
    """Handles processing for a specific ISO country."""
    
    def __init__(self, main_processor, input_iso, capacity_threshold,
                 efficiency_adjustment_gas, efficiency_adjustment_coal, output_dir,
                 tsopt='ts12_clu', skip_timeslices=False, process_all_tsopts=False, auto_commit=True, grid_modeling=False, add_documentation=True, grids_override=None):
        self.main = main_processor
        self.input_iso = input_iso
        self.capacity_threshold = capacity_threshold
        self.efficiency_adjustment_gas = efficiency_adjustment_gas
        self.efficiency_adjustment_coal = efficiency_adjustment_coal
        self.add_documentation = add_documentation
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.tsopt = tsopt
        self.skip_timeslices = skip_timeslices
        self.process_all_tsopts = process_all_tsopts
        self.auto_commit = auto_commit
        self.grid_modeling = grid_modeling
        
        # Store data_source as derived property for consistent global access
        if grids_override:
            self.data_source = grids_override
        else:
            self.data_source = "kan" if grid_modeling else "cit"
        
        self.logger = main_processor.logger
    
    def run_full_pipeline(self):
        """Run the complete processing pipeline for this ISO."""
        from existing_stock_processor import process_existing_stock
        import iso_processing_functions
        import importlib
        importlib.reload(iso_processing_functions)
        from iso_processing_functions import (
            calibration_data, get_ngfs_data, get_weo_data, 
            create_ccs_retrofits_table, re_targets_ember
        )
        from veda_model_creator import create_veda_model
        
        
        self.logger.info(f"Starting full pipeline for {self.input_iso}")
        
        # Step 1: Process existing stock data (and write to vervestacks_ISO.xlsx)
        self.logger.info("Processing existing stock data...")
        df_irena_util, df_ember_util, df_grouped_gem = process_existing_stock(self, self.add_documentation)
        
        # Step 2: Run all analysis functions
        self.logger.info("Running calibration analysis...")
        calibration_data(self, df_irena_util, df_ember_util, df_grouped_gem)
        
        self.logger.info("Processing CCS retrofits...")
        # writes to vervestacks_ISO.xlsx
        ccs_retrofits_df = create_ccs_retrofits_table(self, df_grouped_gem)
        
        self.logger.info("Extracting renewable energy targets...")
        re_targets_ember_df = re_targets_ember(self)
        
        self.logger.info("Processing WEO technology data...")
        get_weo_data(self)
        
        self.logger.info("skipping NGFS scenario data...")
        # self.logger.info("Processing IAMC scenario data...")
        # get_ngfs_data(self)
        
        # Step 3: Create Veda model files (including time-slice processing and git commit)
        self.logger.info("Creating Veda model files...")
        create_veda_model(self, df_grouped_gem, df_irena_util, df_ember_util, self.tsopt, self.process_all_tsopts, self.skip_timeslices, self.auto_commit, ccs_retrofits_df, re_targets_ember_df)
        
        # Step 4: Update model library table with calibration metrics
        self.logger.info("Updating model library table...")
        self._update_model_library_table()
        
        self.logger.info(f"Pipeline completed for {self.input_iso}")
    
    def register_unsd_data(self):
        """Register UNSD data with DuckDB for processing functions."""
        duckdb.register('df_unsd', self.main.df_unsd)
        duckdb.register('df_unsd_regmap', self.main.df_unsd_regmap)
        duckdb.register('df_unsd_prodmap', self.main.df_unsd_prodmap)
        duckdb.register('df_unsd_flowmap', self.main.df_unsd_flowmap)
    
    def _update_model_library_table(self):
        """Update the model library table with calibration metrics for this ISO."""
        try:
            # Check if we have summary metrics from calibration_data
            if not hasattr(self, 'summary_metrics'):
                self.logger.warning(f"No summary metrics found for {self.input_iso}, skipping model library table update")
                return
            
            metrics = self.summary_metrics
            
            # Extract numeric values from formatted strings (handle various formats)
            import re
            
            def extract_number(value_str):
                """Extract numeric value from formatted string."""
                if not value_str:
                    return 0
                # Remove common units and formatting
                clean_str = str(value_str).replace(',', '').replace(' ', '')
                # Extract first number found
                match = re.search(r'[\d.]+', clean_str)
                return float(match.group(0)) if match else 0
            
            total_gw = extract_number(metrics.get('total_capacity_gw', '0'))
            total_twh = extract_number(metrics.get('total_generation_twh', '0'))
            co2_mt = extract_number(metrics.get('model_co2_mt', '0'))
            calibration_pct = extract_number(metrics.get('calibration_pct', '0'))
            
            # Import and call the updater directly
            from update_model_library_table import ModelLibraryTableUpdater
            
            # Use correct model identifier (add _grids suffix for grid models)
            model_id = f"{self.input_iso}_grids" if self.grid_modeling else self.input_iso
            
            updater = ModelLibraryTableUpdater()
            success = updater.update_model_entry(
                model_id,
                total_gw,
                total_twh,
                co2_mt,
                calibration_pct
            )
            
            if success:
                self.logger.info(f"Model library table updated for {model_id}")
            else:
                self.logger.warning(f"Model library table update failed for {model_id}")
                
        except Exception as e:
            # Use model_id if available, otherwise fall back to input_iso
            identifier = f"{self.input_iso}_grids" if self.grid_modeling else self.input_iso
            self.logger.error(f"Error updating model library table for {identifier}: {e}")


if __name__ == "__main__":
    # Example usage
    processor = VerveStacksProcessor()
    
    # Process Japan
    processor.process_iso('JPN')
    
    # Process another country without reloading data
    processor.process_iso('USA')
    
    # See available countries
    print("Available ISO codes:", processor.get_available_isos()[:10]) 