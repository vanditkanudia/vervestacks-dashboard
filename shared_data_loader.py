"""
Shared Data Loader for VerveStacks
==================================

Eliminates data loading duplications by providing a centralized, cached data loading service.
All shared data files are loaded once and cached for reuse across modules.

Author: VerveStacks Team
"""

import pandas as pd
from pathlib import Path
import logging
import numpy as np
from collections import OrderedDict
from datetime import datetime
import duckdb
import time


def get_project_root():
    """
    Find VerveStacks project root from any subdirectory.
    Looks for characteristic files that exist only at project root.
    """
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "main.py").exists() and (parent / "verve_stacks_processor.py").exists():
            return parent
    return Path(__file__).parent.resolve()  # fallback to shared_data_loader directory


def get_cache_path(filename):
    """
    Get absolute cache path that works from any directory.
    
    Args:
        filename: Cache filename (e.g., 'global_data_cache.pkl')
        
    Returns:
        Path: Absolute path to cache file
    """
    return get_project_root() / 'cache' / filename


class SharedDataLoader:
    """
    Centralized data loader that eliminates duplications by caching commonly used datasets.
    
    Benefits:
    - Load large files once, reuse everywhere
    - Consistent data versions across modules  
    - Reduced memory usage
    - Faster processing after initial load
    """
    
    def __init__(self, data_dir="data/", cache_enabled=True):
        """
        Initialize the shared data loader.
        
        Args:
            data_dir: Root directory for data files
            cache_enabled: Whether to cache loaded data (recommended: True)
        """
        self.data_dir = Path(data_dir)
        self.cache_enabled = cache_enabled
        self._cache = {}
        self.logger = logging.getLogger(__name__)
        
        # Validate data directory exists
        if not self.data_dir.exists():
            self.logger.warning(f"Data directory not found: {self.data_dir}")
    
    def _get_cached_or_load(self, cache_key, load_function):
        """Generic caching wrapper for data loading functions."""
        if not self.cache_enabled:
            return load_function()
            
        if cache_key not in self._cache:
            self.logger.info(f"Loading and caching: {cache_key}")
            self._cache[cache_key] = load_function()
        else:
            self.logger.debug(f"Using cached data: {cache_key}")
            
        return self._cache[cache_key]
    
    # === VS_mappings.xlsx consolidation ===
    def get_vs_mappings_sheet(self, sheet_name):
        """
        Load any sheet from VS_mappings.xlsx with caching.
        
        Available sheets:
        - gem_techmap, irena_ember_typemap, unsd_region_map, unsd_product_map, 
          unsd_flow_map, weo_pg_techs, kinesys_region_map, loadshape_roadtransport, 
          iamc_variables
        """
        cache_key = f"vs_mappings_{sheet_name}"
        
        def load_sheet():
            # Try multiple possible locations for VS_mappings.xlsx
            possible_paths = [
                self.data_dir / "../assumptions/VS_mappings.xlsx",  # From 2_ts_design/scripts with data_path="../data/"
                self.data_dir / "assumptions/VS_mappings.xlsx",     # From root with data_path="data/"
                Path("assumptions/VS_mappings.xlsx"),               # Current directory
                Path("../assumptions/VS_mappings.xlsx"),            # Up one level
                Path("../../assumptions/VS_mappings.xlsx")          # Up two levels (for nested scripts)
            ]
            
            for file_path in possible_paths:
                try:
                    if file_path.exists():
                        self.logger.info(f"Loading VS_mappings.xlsx from: {file_path}")
                        return pd.read_excel(file_path, sheet_name=sheet_name)
                except Exception as e:
                    self.logger.debug(f"Failed to load from {file_path}: {e}")
                    continue
            
            # If all paths fail, provide helpful error message
            tried_paths = [str(p) for p in possible_paths]
            error_msg = f"Failed to load VS_mappings.xlsx sheet '{sheet_name}' from any of: {tried_paths}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
                
        return self._get_cached_or_load(cache_key, load_sheet)
    
    # === IRENA data consolidation ===
    def get_irena_capacity_data(self):
        """Load IRENASTAT-C.xlsx with caching."""
        cache_key = "irena_capacity"
        
        def load_irena_c():
            file_path = self.data_dir / "irena/IRENASTAT-C.xlsx"
            try:
                return pd.read_excel(file_path)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_irena_c)
    
    def get_irena_generation_data(self):
        """Load IRENASTAT-G.xlsx with caching."""
        cache_key = "irena_generation"
        
        def load_irena_g():
            file_path = self.data_dir / "irena/IRENASTAT-G.xlsx"
            try:
                return pd.read_excel(file_path)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_irena_g)
    
    # === Weather data consolidation (standardized to 2013) ===
    def get_sarah_iso_weather_data(self):
        """Load sarah_era5_iso_2013.csv with caching (standardized year)."""
        cache_key = "sarah_iso_weather_2013"
        
        def load_sarah():
            file_path = self.data_dir / "hourly_profiles/sarah_era5_iso_2013.csv"
            try:
                return pd.read_csv(file_path)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_sarah)
    
    def get_sarah_grid_weather_data(self):
        """Load sarah_era5_iso_grid_cell_2013.csv with caching (grid modeling)."""
        cache_key = "sarah_grid_weather_2013"
        
        def load_sarah_grid():
            file_path = self.data_dir / "hourly_profiles/sarah_era5_iso_grid_cell_2013.csv"
            try:
                return pd.read_csv(file_path)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_sarah_grid)
    
    def get_atlite_iso_weather_data(self):
        """Load and atlite ISO weather data with disk + memory caching (standardized year)."""
        cache_key = "atlite_iso_weather_2013"
        
        def load_atlite_iso():
            # Check for disk cache first (following project pattern) - but only if caching is enabled
            cache_file = get_cache_path("atlite_iso_weather.pkl")
            
            if self.cache_enabled and cache_file.exists():
                self.logger.info(f"Loading ISO data from disk cache: {cache_file}")
                try:
                    return pd.read_pickle(cache_file)
                except Exception as e:
                    self.logger.warning(f"Failed to load ISO disk cache: {e}, rebuilding...")
            elif not self.cache_enabled and cache_file.exists():
                self.logger.info(f"🔄 Force reload: Skipping disk cache {cache_file}")
            
            # Cache miss or failed - load and merge from source files
            atlite_path = self.data_dir / "hourly_profiles/atlite_iso_2013.csv"
            self.logger.info(f"Loading ISO file: {atlite_path}")
            
            try:
                df_atlite_iso = pd.read_csv(atlite_path)
                self.logger.info(f"ISO data loaded: {len(df_atlite_iso):,} rows")
            except Exception as e:
                self.logger.error(f"Failed to load ISO file {atlite_path}: {e}")
                raise
                            
            # Save merged result to disk cache (only if caching is enabled)
            if self.cache_enabled:
                try:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    df_atlite_iso.to_pickle(cache_file)
                    self.logger.info(f"Saved merged ISO data to disk cache: {cache_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to save ISO disk cache: {e}")
            else:
                self.logger.info("🔄 Force reload: Skipping disk cache save")
            
            return df_atlite_iso
                                
        return self._get_cached_or_load(cache_key, load_atlite_iso)
    
    def get_atlite_grid_weather_data(self):
        """Load atlite grid weather data with disk + memory caching (grid modeling)."""
        cache_key = "atlite_grid_weather_2013"
        
        def load_atlite_grid():
            # Check for disk cache first (following project pattern) - but only if caching is enabled
            cache_file = get_cache_path("atlite_grid_weather.pkl")
            
            if self.cache_enabled and cache_file.exists():
                self.logger.info(f"Loading merged data from disk cache: {cache_file}")
                try:
                    return pd.read_pickle(cache_file)
                except Exception as e:
                    self.logger.warning(f"Failed to load disk cache: {e}, rebuilding...")
            elif not self.cache_enabled and cache_file.exists():
                self.logger.info(f"🔄 Force reload: Skipping disk cache {cache_file}")
            
            # Cache miss or failed - load and merge from source files
            atlite_path = self.data_dir / "hourly_profiles/atlite_grid_cell_2013.parquet"
            self.logger.info(f"Loading large grid cell file: {atlite_path}")
            
            try:
                df_atlite_grid = pd.read_parquet(atlite_path)
                self.logger.info(f"Grid cell data loaded: {len(df_atlite_grid):,} rows")
            except Exception as e:
                self.logger.error(f"Failed to load grid cell file {atlite_path}: {e}")
                raise
            
            # Save merged result to disk cache (only if caching is enabled)
            if self.cache_enabled:
                try:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    df_atlite_grid.to_pickle(cache_file)
                    self.logger.info(f"Saved grid cell data to disk cache: {cache_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to save disk cache: {e}")
            else:
                self.logger.info("🔄 Force reload: Skipping disk cache save")
            
            return df_atlite_grid
                                
        return self._get_cached_or_load(cache_key, load_atlite_grid)
    
    def clear_atlite_disk_cache(self):
        """Clear disk cache for atlite weather data (useful for force reload)."""
        cache_files = [
            get_cache_path("atlite_grid_weather.pkl"),
            get_cache_path("atlite_iso_weather.pkl")
        ]
        
        for cache_file in cache_files:
            if cache_file.exists():
                try:
                    cache_file.unlink()
                    self.logger.info(f"Cleared disk cache: {cache_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clear disk cache {cache_file}: {e}")
    
    def get_era5_demand_data(self):
        """Load era5_combined_data_2030.csv with caching."""
        cache_key = "era5_demand_2030"
        
        def load_era5():
            file_path = self.data_dir / "hourly_profiles/era5_combined_data_2030.csv"
            try:
                return pd.read_csv(file_path)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_era5)
    
    # === RE potentials consolidation ===
    def get_re_potentials_sheet(self, sheet_name):
        """
        Load any sheet from re_potentials.xlsx with caching.
        
        Available sheets: commodities, process, fi_t
        """
        cache_key = f"re_potentials_{sheet_name}"
        
        def load_re_sheet():
            file_path = self.data_dir / "technologies/re_potentials.xlsx"
            try:
                return pd.read_excel(file_path, sheet_name=sheet_name)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path} sheet '{sheet_name}': {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_re_sheet)
    
    # === Technoeconomic data consolidation ===
    def get_technoeconomic_sheet(self, sheet_name):
        """
        Load any sheet from ep_technoeconomic_assumptions.xlsx with caching.
        
        Available sheets: costs, costs_size_multipliers, regional_multipliers, 
                         ep_regionmap, thermal_eff, life
        """
        cache_key = f"technoeconomic_{sheet_name}"
        
        def load_tech_sheet():
            file_path = self.data_dir / "technologies/ep_technoeconomic_assumptions.xlsx"
            try:
                return pd.read_excel(file_path, sheet_name=sheet_name)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path} sheet '{sheet_name}': {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_tech_sheet)
    
    # === Other commonly used data ===
    def get_ember_data(self):
        """Load Ember yearly data with caching."""
        cache_key = "ember_yearly"
        
        def load_ember():
            file_path = self.data_dir / "ember/yearly_full_release_long_format.csv"
            try:
                return pd.read_csv(file_path)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_ember)
    
    def get_monthly_hydro_data(self):
        """Load monthly hydro data with caching."""
        cache_key = "monthly_hydro"
        
        def load_hydro():
            file_path = self.data_dir / "timeslices/monthly_full_release_long_format.csv"
            try:
                return pd.read_csv(file_path)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_hydro)
    
    def get_region_map(self):
        """Load region mapping data with caching."""
        cache_key = "region_map"
        
        def load_region_map():
            file_path = self.data_dir / "timeslices/region_map.xlsx"
            try:
                return pd.read_excel(file_path)
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                raise
                
        return self._get_cached_or_load(cache_key, load_region_map)
    
    def get_rezoning_data(self, force_reload=False):
        """
        Load REZoning data with landuse adjustments.
        
        This method integrates REZoning data loading into the shared data loader
        to ensure consistent caching behavior and proper force-reload support.
        
        Args:
            force_reload: If True, bypass cache and reload from source
            
        Returns:
            dict: REZoning data with keys:
                - 'df_rez_solar': Land-use adjusted solar data
                - 'df_rez_wind': Land-use adjusted wind data  
                - 'df_rez_windoff': Offshore wind data (no land-use conflicts)
                - 'df_rez_solar_original': Original solar data
                - 'df_rez_wind_original': Original wind data
                - 'df_rez_windoff_original': Original offshore wind data
                - 'processing_metadata': Processing information
        """
        cache_key = "rezoning_landuse_global"
        
        def load_rezoning_data():
            """Load and process REZoning data."""
            self.logger.info("Loading REZoning data with landuse adjustments...")
            
            # Import the global processor
            from rezoning_landuse_processor import process_all_rezoning_data
            
            # Process REZoning data (this handles the actual data loading and processing)
            global_data = process_all_rezoning_data(force_refresh=force_reload)
            
            self.logger.info(f"REZoning data loaded: {len(global_data.get('df_rez_solar', []))} solar, {len(global_data.get('df_rez_wind', []))} wind, {len(global_data.get('df_rez_windoff', []))} offshore wind records")
            return global_data
        
        # If force_reload is True, bypass cache entirely
        if force_reload:
            self.logger.info("Force reload requested for REZoning data - bypassing cache")
            return load_rezoning_data()
        
        # Otherwise use normal caching behavior
        return self._get_cached_or_load(cache_key, load_rezoning_data)
    
    # === Cache management ===
    def clear_cache(self):
        """Clear all cached data to free memory."""
        self._cache.clear()
        self.logger.info("Data cache cleared")
    
    def get_cache_info(self):
        """Return information about cached datasets."""
        return {
            "cached_datasets": list(self._cache.keys()),
            "cache_size": len(self._cache),
            "cache_enabled": self.cache_enabled
        }


class GridCellShapeCache:
    """
    LRU cache for grid-cell level hourly capacity factor profiles.
    
    Loads all grid cells for an ISO once from parquet, caches in memory.
    Uses Least Recently Used (LRU) eviction when cache limit reached.
    
    Memory-safe for production:
    - Bounded cache size (default: 10 ISOs)
    - Shared across all API users
    - Popular ISOs stay cached, rare ISOs evicted
    
    Performance:
    - First load: 2-3 seconds (from parquet)
    - Cached load: 0.01 seconds (50x faster)
    - Typical cache hit rate: 80-90%
    """
    
    def __init__(self, data_dir="data/", max_isos=10, max_memory_gb=3, weather_year=2013):
        """
        Initialize grid cell shape cache.
        
        Parameters:
        -----------
        data_dir : str
            Path to data directory
        max_isos : int
            Maximum number of ISO+technology combinations to cache
        max_memory_gb : float
            Soft memory limit in GB (for monitoring, not enforced)
        weather_year : int
            Weather year to use for data (default: 2013)
        """
        self.data_dir = Path(data_dir)
        self.max_isos = max_isos
        self.max_memory_gb = max_memory_gb
        self.weather_year = weather_year
        
        # LRU cache using OrderedDict
        self._cache = OrderedDict()  # {f"{iso}_{tech}": {cell_id: np.array(8760)}}
        self._access_times = {}  # {cache_key: timestamp}
        self._cache_stats = {
            'hits': 0,              # Full cache hits (all cells found)
            'partial_hits': 0,      # Partial hits (some cells found, loaded rest)
            'misses': 0,            # Complete misses (no cache entry)
            'evictions': 0,         # Cache evictions (LRU)
            'loads': 0,             # Parquet load operations
            'split_file_hits': 0    # Split ISO files loaded
        }
        
        # Parquet directory paths
        self.split_files_dir = self.data_dir / 'hourly_profiles' / 'Atlite_data'
        
        if not self.split_files_dir.exists():
            raise FileNotFoundError(
                f"Split files directory not found: {self.split_files_dir}\n"
                f"Expected structure: data/hourly_profiles/Atlite_data/{{ISO}}_{{year}}.parquet"
            )
        
        logging.info(f"✅ GridCellShapeCache initialized with SPLIT FILES (year={weather_year}, max_isos={max_isos}, max_memory={max_memory_gb}GB)")
        logging.info(f"   📂 Split files directory: {self.split_files_dir}")
    
    def get_cell_shapes(self, iso_code, technology, cell_ids):
        """
        Get hourly CF shapes for specific grid cells.
        
        Uses incremental cache building: only loads missing cells from parquet,
        merges with existing cache. Memory-efficient and fast!
        
        Parameters:
        -----------
        iso_code : str
            ISO country code (e.g., 'DEU', 'USA')
        technology : str
            Technology type ('solar', 'wind', 'windoff')
        cell_ids : list
            List of cell IDs to retrieve
            
        Returns:
        --------
        dict : {cell_id: np.array(8760)}
            Dictionary mapping cell IDs to 8760-hour CF arrays
            
        Raises:
        -------
        ValueError: If requested cells cannot be found in parquet data
        """
        cache_key = f"{iso_code}_{technology}"
        
        # Check if ISO has any cached data
        if cache_key in self._cache:
            # Mark as recently used (LRU)
            self._cache.move_to_end(cache_key)
            self._access_times[cache_key] = datetime.now()
            
            cached_shapes = self._cache[cache_key]
            
            # Identify missing cells
            missing_cells = [cell_id for cell_id in cell_ids if cell_id not in cached_shapes]
            
            if missing_cells:
                # Partial cache hit - load only missing cells
                self._cache_stats['partial_hits'] = self._cache_stats.get('partial_hits', 0) + 1
                logging.info(f"📊 Partial cache hit for {cache_key}: {len(cached_shapes)} cached, loading {len(missing_cells)} more cells...")
                
                # Load only missing cells from parquet
                new_shapes = self._load_iso_shapes_from_parquet(iso_code, technology, missing_cells)
                
                if not new_shapes:
                    # Could not load any missing cells
                    missing_str = ', '.join(missing_cells[:5]) + ('...' if len(missing_cells) > 5 else '')
                    raise ValueError(f"Could not load shapes for {len(missing_cells)} cells from parquet: {missing_str}")
                
                # Merge new shapes with existing cache
                cached_shapes.update(new_shapes)
                self._cache[cache_key] = cached_shapes
                
                logging.info(f"✅ Merged {len(new_shapes)} new cells. Cache now has {len(cached_shapes)} cells for {cache_key}")
            else:
                # Full cache hit - all requested cells already cached
                self._cache_stats['hits'] += 1
                logging.info(f"✅ Full cache hit for {cache_key}: All {len(cell_ids)} cells found in cache")
            
            # Return requested cells (all should be available now)
            result = {}
            still_missing = []
            for cell_id in cell_ids:
                if cell_id in cached_shapes:
                    result[cell_id] = cached_shapes[cell_id]
                else:
                    still_missing.append(cell_id)
            
            if still_missing:
                missing_str = ', '.join(still_missing[:5]) + ('...' if len(still_missing) > 5 else '')
                raise ValueError(f"Missing shape data for {len(still_missing)} cells even after loading: {missing_str}")
            
            return result
        
        # Complete cache miss - load requested cells and initialize cache
        self._cache_stats['misses'] += 1
        logging.info(f"📥 Cache miss for {cache_key}. Loading {len(cell_ids)} cells from parquet...")
        
        iso_shapes = self._load_iso_shapes_from_parquet(iso_code, technology, cell_ids)
        
        if not iso_shapes:
            raise ValueError(f"Could not load any shapes for {iso_code} {technology} from parquet")
        
        # Add to cache with LRU eviction
        self._add_to_cache(cache_key, iso_shapes)
        
        # Verify all requested cells were loaded
        missing = [cell_id for cell_id in cell_ids if cell_id not in iso_shapes]
        if missing:
            missing_str = ', '.join(missing[:5]) + ('...' if len(missing) > 5 else '')
            logging.warning(f"⚠️  Could not load {len(missing)} cells: {missing_str}")
        
        # Return what we have
        return {cell_id: iso_shapes[cell_id] for cell_id in cell_ids if cell_id in iso_shapes}
    
    def _load_iso_shapes_from_parquet(self, iso_code, technology, cell_ids):
        """
        Load grid cell shapes from ISO-specific parquet file using DuckDB.
        
        Returns:
        --------
        dict : {cell_id: np.array(8760)}
        """
        start_time = time.time()
        
        if not cell_ids:
            logging.warning(f"⚠️  No cell IDs provided")
            return {}
        
        # Map technology to parquet column name
        tech_column_map = {
            'solar': 'solar_capacity_factor',
            'wind': 'wind_capacity_factor',
            'windoff': 'windoff_capacity_factor'
        }
        
        cf_column = tech_column_map.get(technology)
        if cf_column is None:
            logging.error(f"❌ Unknown technology: {technology}")
            return {}
        
        # Get ISO-specific file path
        split_file_path = self.split_files_dir / f"{iso_code}_{self.weather_year}.parquet"
        
        if not split_file_path.exists():
            raise FileNotFoundError(
                f"Split parquet file not found: {split_file_path}\n"
                f"Expected: {iso_code}_{self.weather_year}.parquet in {self.split_files_dir}"
            )
        
        try:
            logging.info(f"📂 Loading from split file: {split_file_path.name}")
            
            # Choose strategy based on cell list size
            if len(cell_ids) < 100:
                # Small list: Use SQL IN clause (simple and fast)
                cell_list = ','.join([f"'{cell_id}'" for cell_id in cell_ids])
                
                query = f"""
                    SELECT grid_cell, month, day, hour, {cf_column}
                    FROM read_parquet('{split_file_path}')
                    WHERE grid_cell IN ({cell_list})
                """
                
                atlite_data = duckdb.query(query).df()
                
            else:
                # Large list: Use temp table join (more efficient)
                conn = duckdb.connect(':memory:')
                
                # Create temp table with target cells
                conn.execute("CREATE TEMP TABLE target_cells (cell_id VARCHAR)")
                conn.executemany("INSERT INTO target_cells VALUES (?)", [(str(c),) for c in cell_ids])
                
                # Join with parquet data
                query = f"""
                    SELECT p.grid_cell, p.month, p.day, p.hour, p.{cf_column}
                    FROM read_parquet('{split_file_path}') p
                    INNER JOIN target_cells t ON p.grid_cell = t.cell_id
                """
                
                atlite_data = conn.execute(query).df()
                conn.close()
            
            load_time = time.time() - start_time
            
            # Convert to dict of arrays
            shapes = self._convert_df_to_shapes(atlite_data, cf_column, iso_code, technology)
            
            self._cache_stats['loads'] += 1
            self._cache_stats['split_file_hits'] += 1
            logging.info(f"✅ Loaded {len(shapes)} cells for {iso_code} {technology} in {load_time:.2f}s")
            
            return shapes
            
        except Exception as e:
            logging.error(f"❌ Error loading shapes from parquet with DuckDB: {e}")
            raise
    
    def _convert_df_to_shapes(self, atlite_data, cf_column, iso_code, technology):
        """
        Convert DataFrame to dict of shapes.
        
        Parameters:
        -----------
        atlite_data : pd.DataFrame
            DataFrame with columns: grid_cell, month, day, hour, {cf_column}
        cf_column : str
            Name of capacity factor column
        iso_code : str
            ISO country code (for logging)
        technology : str
            Technology type (for logging)
            
        Returns:
        --------
        dict : {cell_id: np.array(8760)}
        """
        if atlite_data.empty:
            logging.warning(f"⚠️  No data found for {iso_code} {technology} cells")
            return {}
        
        # Check if CF column exists
        if cf_column not in atlite_data.columns:
            logging.warning(f"⚠️  Column {cf_column} not found in parquet")
            return {}
        
        # Convert to dict of arrays
        shapes = {}
        for cell_id in atlite_data['grid_cell'].unique():
            cell_data = atlite_data[atlite_data['grid_cell'] == cell_id].sort_values(['month', 'day', 'hour'])
            cf_values = cell_data[cf_column].values
            
            # Ensure exactly 8760 hours
            if len(cf_values) == 8760:
                shapes[cell_id] = cf_values
            else:
                logging.warning(f"⚠️  Cell {cell_id} has {len(cf_values)} hours (expected 8760), skipping")
        
        return shapes
    
    def _add_to_cache(self, cache_key, shapes):
        """Add shapes to cache with LRU eviction if needed."""
        # Evict if cache is full
        if len(self._cache) >= self.max_isos:
            # Remove least recently used (first item in OrderedDict)
            evicted_key = next(iter(self._cache))
            del self._cache[evicted_key]
            if evicted_key in self._access_times:
                del self._access_times[evicted_key]
            self._cache_stats['evictions'] += 1
            logging.info(f"♻️  Evicted {evicted_key} from cache (LRU)")
        
        # Add new entry
        self._cache[cache_key] = shapes
        self._access_times[cache_key] = datetime.now()
        logging.info(f"💾 Cached {cache_key} ({len(shapes)} cells)")
    
    def get_cache_info(self):
        """Get information about current cache state."""
        cache_info = {}
        for key, shapes in self._cache.items():
            # Estimate memory size (rough)
            num_cells = len(shapes)
            memory_mb = num_cells * 8760 * 8 / 1024 / 1024  # 8 bytes per float64
            cache_info[key] = {
                'num_cells': num_cells,
                'memory_mb': round(memory_mb, 2),
                'last_accessed': self._access_times.get(key, 'Unknown')
            }
        
        return {
            'cached_isos': cache_info,
            'stats': self._cache_stats,
            'cache_size': len(self._cache),
            'max_size': self.max_isos
        }
    
    def get_cache_stats(self):
        """Get cache performance statistics."""
        hits = self._cache_stats['hits']
        partial_hits = self._cache_stats.get('partial_hits', 0)
        misses = self._cache_stats['misses']
        
        total_requests = hits + partial_hits + misses
        
        # Full hits are best, partial hits are good, misses are expensive
        effective_hits = hits + partial_hits
        hit_rate = (effective_hits / total_requests * 100) if total_requests > 0 else 0
        full_hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self._cache_stats,
            'total_requests': total_requests,
            'effective_hit_rate_percent': round(hit_rate, 2),  # Full + partial hits
            'full_hit_rate_percent': round(full_hit_rate, 2)   # Only full hits
        }
    
    def clear_iso(self, iso_code, technology=None):
        """Clear specific ISO from cache."""
        if technology:
            cache_key = f"{iso_code}_{technology}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                logging.info(f"🗑️  Cleared {cache_key} from cache")
        else:
            # Clear all technologies for this ISO
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{iso_code}_")]
            for key in keys_to_remove:
                del self._cache[key]
            logging.info(f"🗑️  Cleared all {iso_code} entries from cache")
    
    def clear_all(self):
        """Clear entire cache."""
        self._cache.clear()
        self._access_times.clear()
        logging.info("🗑️  Cleared entire cache")


# Global singleton instances for easy access
_global_loader = None
_global_shape_cache = None

def get_shared_loader(data_dir="data/", cache_enabled=True):
    """
    Get the global SharedDataLoader instance.
    
    This creates a singleton so all modules use the same cached data.
    If cache_enabled differs from existing instance, updates the setting.
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = SharedDataLoader(data_dir, cache_enabled)
    else:
        # Update cache setting if different
        if _global_loader.cache_enabled != cache_enabled:
            _global_loader.cache_enabled = cache_enabled
            print(f"🔄 SharedDataLoader: Updated cache_enabled to {cache_enabled}")
    return _global_loader


def get_shape_cache(data_dir="data/", max_isos=10, max_memory_gb=3, weather_year=2013):
    """
    Get the global GridCellShapeCache instance.
    
    This creates a singleton so all modules use the same cache.
    Shared across all API users for memory efficiency.
    
    Parameters:
    -----------
    data_dir : str
        Path to data directory
    max_isos : int
        Maximum number of ISO+technology combinations to cache
    max_memory_gb : float
        Soft memory limit in GB
    weather_year : int
        Weather year to use for data (default: 2013)
    """
    global _global_shape_cache
    if _global_shape_cache is None:
        _global_shape_cache = GridCellShapeCache(data_dir, max_isos, max_memory_gb, weather_year)
    return _global_shape_cache


# Convenience functions for common data access
def get_vs_mappings_sheet(sheet_name):
    """Convenience function to get VS_mappings.xlsx sheets."""
    return get_shared_loader().get_vs_mappings_sheet(sheet_name)

def get_irena_capacity_data():
    """Convenience function to get IRENA capacity data."""
    return get_shared_loader().get_irena_capacity_data()

def get_irena_generation_data():
    """Convenience function to get IRENA generation data."""
    return get_shared_loader().get_irena_generation_data()

def get_sarah_iso_weather_data():
    """Convenience function to get SARAH ISO weather data (2013)."""
    return get_shared_loader().get_sarah_iso_weather_data()

def get_sarah_grid_weather_data():
    """Convenience function to get SARAH grid weather data (2013)."""
    return get_shared_loader().get_sarah_grid_weather_data()

def get_era5_demand_data():
    """Convenience function to get ERA5 demand data."""
    return get_shared_loader().get_era5_demand_data()

def get_rezoning_data(force_reload=False):
    """Convenience function to get REZoning data with landuse adjustments."""
    return get_shared_loader().get_rezoning_data(force_reload=force_reload)