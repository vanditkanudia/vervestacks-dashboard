"""
Data Processing Utilities

Utility functions for data manipulation and analysis operations.
"""

import pandas as pd
import pickle
from pathlib import Path
import logging


def smart_format_number(value):
    """
    Smart number formatting for chart labels based on magnitude
    - Larger numbers get less precision (rounded)
    - Smaller numbers get more precision (meaningful decimals)
    - Never shows unnecessary .0
    
    Args:
        value: Number to format
    
    Returns:
        Clean formatted string for labels
    
    Examples:
        smart_format_number(18391)  # "18391"
        smart_format_number(18.4)   # "18.4"
        smart_format_number(18.0)   # "18"
        smart_format_number(0.34)   # "0.34"
        smart_format_number(0.0)    # "0"
    """
    if value == 0:
        return "0"
    
    abs_val = abs(value)
    
    if abs_val >= 1000:
        # Very large: no decimals
        return f"{value:.0f}"
    elif abs_val >= 50:
        # Large: no decimals, no .0
        return f"{int(round(value))}"
    elif abs_val >= 10:
        # Medium: 1 decimal if meaningful
        rounded = round(value, 1)
        if rounded == int(rounded):
            return f"{int(rounded)}"
        else:
            return f"{rounded:.1f}"
    elif abs_val >= 1:
        # Small: up to 2 decimals if meaningful
        rounded = round(value, 2)
        if rounded == int(rounded):
            return f"{int(rounded)}"
        elif rounded == round(rounded, 1):
            return f"{rounded:.1f}"
        else:
            return f"{rounded:.2f}"
    else:
        # Very small: up to 3 decimals if meaningful
        rounded = round(value, 3)
        if rounded == 0:
            return "0"
        # Remove trailing zeros
        formatted = f"{rounded:.3f}".rstrip('0').rstrip('.')
        return formatted


def calculate_median_across_columns(df, value_cols, median_across=['Model']):
    """
    Calculate median values by aggregating across specified columns.
    
    Args:
        df: Input dataframe
        value_cols: List of columns to calculate median for (e.g., year columns)
        median_across: Columns to aggregate across (default: ['Model'])
    
    Returns:
        DataFrame with median values, 'Median' replacing median_across values
    
    Example:
        # Calculate median across models for each scenario and variable
        median_df = calculate_median_across_columns(
            ngfs_df, 
            value_cols=['2025', '2030', '2035', '2040', '2045', '2050'],
            median_across=['Model']
        )
    """
    # Identify group-by columns (all columns except value_cols and median_across)
    all_cols = set(df.columns)
    exclude_cols = set(value_cols) | set(median_across)
    potential_group_cols = list(all_cols - exclude_cols)
    
    # Automatically exclude columns with any null values from grouping
    group_by_cols = []
    for col in potential_group_cols:
        if not df[col].isnull().any():
            group_by_cols.append(col)
    
    # Check group sizes to determine which groups have multiple records
    group_sizes = df.groupby(group_by_cols).size()
    
    # Groups with only one record - return original data
    single_record_groups = group_sizes[group_sizes == 1].index
    single_record_df = df.set_index(group_by_cols).loc[single_record_groups].reset_index()
    
    # Groups with multiple records - calculate median
    multi_record_groups = group_sizes[group_sizes > 1].index
    if len(multi_record_groups) > 0:
        multi_record_df = df.set_index(group_by_cols).loc[multi_record_groups].reset_index()
        median_df = multi_record_df.groupby(group_by_cols)[value_cols].median().reset_index()
        
        # Add the median_across columns with 'Median' values for median calculations
        for col in median_across:
            median_df[col] = 'Median'
        
        # Add other non-grouping, non-value columns from the first record of each group
        other_cols = [col for col in df.columns if col not in group_by_cols + value_cols + median_across]
        if other_cols:
            first_records = multi_record_df.groupby(group_by_cols)[other_cols].first().reset_index()
            median_df = median_df.merge(first_records, on=group_by_cols, how='left')
    else:
        median_df = pd.DataFrame()
    
    # Combine single record and median results
    if not single_record_df.empty and not median_df.empty:
        result_df = pd.concat([single_record_df, median_df], ignore_index=True)
    elif not single_record_df.empty:
        result_df = single_record_df
    elif not median_df.empty:
        result_df = median_df
    else:
        result_df = pd.DataFrame()
    
    # Reorder columns to match original structure
    if not result_df.empty:
        original_col_order = [col for col in df.columns if col in result_df.columns]
        result_df = result_df[original_col_order]
    
    return result_df


# =============================================================================
# CACHE ACCESS UTILITIES
# =============================================================================

def load_gem_data_from_cache(cache_dir="cache", relative_to_script=True):
    """
    Load GEM power plants data directly from global cache.
    
    Args:
        cache_dir: Directory containing cache files (default: "cache")
        relative_to_script: If True, resolve cache_dir relative to calling script's directory
    
    Returns:
        pd.DataFrame or None: GEM dataframe if cache exists, None otherwise
    
    Example:
        # From any module
        from data_utils import load_gem_data_from_cache
        df_gem = load_gem_data_from_cache()
        if df_gem is not None:
            # Use GEM data...
    """
    logger = logging.getLogger(__name__)
    
    if relative_to_script:
        # Get the directory of the calling script
        import inspect
        caller_frame = inspect.currentframe().f_back
        caller_file = caller_frame.f_code.co_filename
        caller_dir = Path(caller_file).parent
        cache_path = caller_dir / cache_dir
    else:
        cache_path = Path(cache_dir)
    
    cache_file = cache_path / "global_data_cache.pkl"
    
    if not cache_file.exists():
        logger.debug(f"Cache file not found: {cache_file}")
        return None
    
    try:
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
        
        if 'df_gem' in cache_data and cache_data['df_gem'] is not None:
            df_gem = cache_data['df_gem']
            logger.info(f"Loaded GEM data from cache: {len(df_gem)} power plants")
            return df_gem
        else:
            logger.warning("No GEM data found in cache")
            return None
            
    except Exception as e:
        logger.error(f"Error loading GEM data from cache: {e}")
        return None


def load_cached_dataset(dataset_name, cache_dir="cache", relative_to_script=True):
    """
    Load any dataset from global cache by name.
    
    Args:
        dataset_name: Name of dataset in cache (e.g., 'df_gem', 'df_irena_c', 'df_ember')
        cache_dir: Directory containing cache files (default: "cache")
        relative_to_script: If True, resolve cache_dir relative to calling script's directory
    
    Returns:
        pd.DataFrame or None: Dataset if found in cache, None otherwise
    
    Available datasets:
        - df_gem: GEM power plants data
        - df_irena_c: IRENA capacity data  
        - df_irena_g: IRENA generation data
        - df_ember: EMBER electricity data
        - ngfs_df: NGFS scenarios data
        - df_unsd: UNSD energy statistics
        - df_unsd_regmap: UNSD regional mapping
        - df_unsd_prodmap: UNSD production mapping
        - df_unsd_flowmap: UNSD flow mapping
        - df_unsd_trade: UNSD trade data
        - df_electricity_trade: Electricity trade data
        - df_ember_trade: EMBER trade data
        - df_gem_map: GEM technology mapping
        - df_irena_ember_map: IRENA-EMBER mapping
        
    Note: REZoning data (df_solar_rezoning, df_windon_rezoning, df_windoff_rezoning) 
    is now handled by shared_data_loader.get_rezoning_data() for proper force_reload support.
    
    Example:
        # Load EMBER data
        df_ember = load_cached_dataset('df_ember')
        
        # Load IRENA capacity data
        df_irena_c = load_cached_dataset('df_irena_c')
    """
    logger = logging.getLogger(__name__)
    
    # Check if this is a REZoning dataset that should use shared_data_loader instead
    rezoning_datasets = ['df_solar_rezoning', 'df_windon_rezoning', 'df_windoff_rezoning']
    if dataset_name in rezoning_datasets:
        logger.warning(f"Dataset '{dataset_name}' is now handled by shared_data_loader.get_rezoning_data() for proper force_reload support")
        logger.warning("Please use: from shared_data_loader import get_rezoning_data; rezoning_data = get_rezoning_data(force_reload=force_reload)")
        return None
    
    if relative_to_script:
        # Get the directory of the calling script
        import inspect
        caller_frame = inspect.currentframe().f_back
        caller_file = caller_frame.f_code.co_filename
        caller_dir = Path(caller_file).parent
        cache_path = caller_dir / cache_dir
    else:
        cache_path = Path(cache_dir)
    
    cache_file = cache_path / "global_data_cache.pkl"
    
    if not cache_file.exists():
        logger.debug(f"Cache file not found: {cache_file}")
        return None
    
    try:
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
        
        if dataset_name in cache_data and cache_data[dataset_name] is not None:
            dataset = cache_data[dataset_name]
            logger.info(f"Loaded {dataset_name} from cache: {len(dataset)} records")
            return dataset
        else:
            logger.warning(f"Dataset '{dataset_name}' not found in cache")
            return None
            
    except Exception as e:
        logger.error(f"Error loading {dataset_name} from cache: {e}")
        return None


def get_cache_info(cache_dir="cache", relative_to_script=True):
    """
    Get information about available datasets in cache.
    
    Args:
        cache_dir: Directory containing cache files (default: "cache")
        relative_to_script: If True, resolve cache_dir relative to calling script's directory
    
    Returns:
        dict: Information about cache contents
    """
    logger = logging.getLogger(__name__)
    
    if relative_to_script:
        # Get the directory of the calling script
        import inspect
        caller_frame = inspect.currentframe().f_back
        caller_file = caller_frame.f_code.co_filename
        caller_dir = Path(caller_file).parent
        cache_path = caller_dir / cache_dir
    else:
        cache_path = Path(cache_dir)
    
    cache_file = cache_path / "global_data_cache.pkl"
    
    if not cache_file.exists():
        return {"cache_exists": False, "cache_file": str(cache_file)}
    
    try:
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
        
        info = {
            "cache_exists": True,
            "cache_file": str(cache_file),
            "datasets": {}
        }
        
        for key, value in cache_data.items():
            if value is not None and hasattr(value, '__len__'):
                info["datasets"][key] = {
                    "type": type(value).__name__,
                    "length": len(value),
                    "columns": list(value.columns) if hasattr(value, 'columns') else None
                }
            else:
                info["datasets"][key] = {
                    "type": type(value).__name__,
                    "value": str(value)[:100] if value is not None else None
                }
        
        return info
        
    except Exception as e:
        logger.error(f"Error reading cache info: {e}")
        return {"cache_exists": True, "cache_file": str(cache_file), "error": str(e)}


def get_country_name_from_iso(iso_code):
    """
    Get country name from ISO code using kinesys_region_map from VS_mappings.
    
    Args:
        iso_code (str): 3-letter ISO country code (e.g., 'CHE', 'USA', 'IND')
        
    Returns:
        str: Country name if found, otherwise returns the ISO code
        
    Examples:
        get_country_name_from_iso('CHE')  # Returns 'Switzerland'
        get_country_name_from_iso('USA')  # Returns 'United States'
        get_country_name_from_iso('IND')  # Returns 'India'
    """
    try:
        from shared_data_loader import get_vs_mappings_sheet
        
        # Get kinesys_region_map sheet
        try:
            region_map = get_vs_mappings_sheet('kinesys_region_map')
        except Exception:
            region_map = None
        
        if region_map is not None and not region_map.empty:
            
            # Look for the ISO code in the mapping
            # The mapping typically has columns like 'iso3', 'country_name', etc.
            iso_upper = iso_code.upper()
            
            # Try different possible column names for ISO codes
            iso_columns = ['iso3', 'iso_code', 'ISO', 'iso']
            name_columns = ['country_name', 'Country', 'country', 'name', 'Country Name']
            
            iso_col = None
            name_col = None
            
            # Find the ISO column
            for col in iso_columns:
                if col in region_map.columns:
                    iso_col = col
                    break
            
            # Find the country name column
            for col in name_columns:
                if col in region_map.columns:
                    name_col = col
                    break
            
            if iso_col and name_col:
                # Look up the country name
                match = region_map[region_map[iso_col] == iso_upper]
                if not match.empty:
                    country_name = match[name_col].iloc[0]
                    if pd.notna(country_name) and country_name.strip():
                        return country_name.strip()
            
            # If no match found, try a fallback approach
            # Look for the ISO code in any string column
            for col in region_map.columns:
                if region_map[col].dtype == 'object':  # String column
                    match = region_map[region_map[col].str.upper() == iso_upper]
                    if not match.empty:
                        # Try to find a country name in other columns
                        for name_col in name_columns:
                            if name_col in region_map.columns:
                                country_name = match[name_col].iloc[0]
                                if pd.notna(country_name) and country_name.strip():
                                    return country_name.strip()
        
        # If not found in kinesys_region_map, try other common sheet names
        for sheet_name in ['country_mapping', 'countries', 'iso_mapping']:
            try:
                sheet_data = get_vs_mappings_sheet(sheet_name)
                if sheet_data is not None and not sheet_data.empty:
                    # Similar lookup logic for other sheets
                    for iso_col in ['iso3', 'iso_code', 'ISO', 'iso']:
                        if iso_col in sheet_data.columns:
                            match = sheet_data[sheet_data[iso_col].str.upper() == iso_upper]
                            if not match.empty:
                                for name_col in ['country_name', 'Country', 'country', 'name']:
                                    if name_col in sheet_data.columns:
                                        country_name = match[name_col].iloc[0]
                                        if pd.notna(country_name) and country_name.strip():
                                            return country_name.strip()
            except Exception:
                continue  # Sheet doesn't exist, try next one
        
        # If still not found, return a hardcoded fallback for common countries
        fallback_names = {
            'CHE': 'Switzerland', 'USA': 'United States', 'DEU': 'Germany', 
            'FRA': 'France', 'GBR': 'United Kingdom', 'JPN': 'Japan',
            'ITA': 'Italy', 'ESP': 'Spain', 'CAN': 'Canada', 'AUS': 'Australia',
            'IND': 'India', 'CHN': 'China', 'BRA': 'Brazil', 'RUS': 'Russia',
            'MEX': 'Mexico', 'KOR': 'South Korea', 'TUR': 'Turkey', 'IDN': 'Indonesia',
            'SAU': 'Saudi Arabia', 'ARG': 'Argentina', 'ZAF': 'South Africa', 'EGY': 'Egypt'
        }
        
        return fallback_names.get(iso_code.upper(), iso_code.upper())
        
    except Exception as e:
        logging.warning(f"Could not get country name for {iso_code}: {e}")
        # Return the ISO code as fallback
        return iso_code.upper()