#!/usr/bin/env python3
"""
REZoning Land Use Processor - Global Scale

OVERVIEW:
=========
This module provides global processing of REZoning solar and wind data with 
conservative land use overlap adjustments across ALL ISOs. It addresses the 
critical issue of double-counting in renewable energy resource assessments.

PROCESSING SCOPE:
================
- Processes ALL ISOs globally (190+ countries)
- Applies identical LCOE share allocation logic to each grid cell
- Returns 4 complete DataFrames: original + adjusted for solar & wind
- Caches results for fast downstream access

METHODOLOGY:
============
Identical to single-ISO processing but scaled globally:
1. Load complete REZoning solar and wind datasets
2. For each grid_cell within each ISO, apply overlap adjustment
3. Use LCOE share allocation: cheaper tech gets larger share in overlap
4. Preserve all non-overlapping capacity at full potential
5. Cache all results with metadata

Author: VerveStacks Team
Version: 1.0
"""

import pandas as pd
import os
import pickle
from datetime import datetime
import time
from shared_data_loader import get_project_root, get_cache_path

def process_all_rezoning_data(force_refresh=False):
    """
    Process REZoning data for ALL ISOs with land use overlap adjustments.
    
    This function scales the single-ISO LCOE share allocation methodology
    to process all countries globally. The core logic remains identical -
    only the scope changes from single ISO to all ISOs.
    
    Parameters:
    -----------
    force_refresh : bool
        If True, bypass cache and reprocess all data
    
    Returns:
    --------
    dict: Global REZoning data with keys:
        - 'df_rez_solar_original': Raw solar data (all ISOs)
        - 'df_rez_solar': Land-use adjusted solar data (all ISOs)
        - 'df_rez_wind_original': Raw wind data (all ISOs)  
        - 'df_rez_wind': Land-use adjusted wind data (all ISOs)
        - 'df_rez_windoff': Offshore wind data (same as original - no land-use conflicts)
        - 'processing_metadata': Timestamp, statistics, etc.
    """
    
    cache_file = get_cache_path('rezoning_landuse_global_cache.pkl')
    
    # Check cache first (unless force refresh)
    if not force_refresh and os.path.exists(cache_file):
        print("Loading REZoning data from cache...")
        try:
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
            print(f"Cache loaded successfully. Processed: {cached_data['processing_metadata']['timestamp']}")
            return cached_data
        except Exception as e:
            print(f"Cache loading failed: {e}. Reprocessing...")
    
    print("Processing REZoning data for ALL ISOs globally...")
    start_time = time.time()
    
    # 1. Load complete REZoning datasets
    print("Loading global REZoning datasets...")
    project_root = get_project_root()
    solar_path = project_root / 'data' / 'REZoning' / 'REZoning_Solar_atlite_cf.csv'
    wind_path = project_root / 'data' / 'REZoning' / 'REZoning_WindOnshore_atlite_cf.csv'
    windoff_path = project_root / 'data' / 'REZoning' / 'REZoning_WindOffshore_atlite_cf.csv'
    
    if not os.path.exists(solar_path):
        raise FileNotFoundError(f"Solar REZoning file not found: {solar_path}")
    if not os.path.exists(wind_path):
        raise FileNotFoundError(f"Wind REZoning file not found: {wind_path}")
    
    df_rez_solar_original = pd.read_csv(solar_path)
    df_rez_wind_original = pd.read_csv(wind_path)
    
    # Load offshore wind data (optional - some countries may not have offshore potential)
    df_rez_windoff_original = pd.DataFrame()
    if os.path.exists(windoff_path):
        df_rez_windoff_original = pd.read_csv(windoff_path)
        print(f"Loaded {len(df_rez_windoff_original):,} offshore wind grid cells across {df_rez_windoff_original['ISO'].nunique() if not df_rez_windoff_original.empty else 0} ISOs")
    else:
        print(f"⚠️  Offshore wind file not found: {windoff_path} - continuing without offshore wind data")
    
    print(f"Loaded {len(df_rez_solar_original):,} solar grid cells across {df_rez_solar_original['ISO'].nunique()} ISOs")
    print(f"Loaded {len(df_rez_wind_original):,} wind grid cells across {df_rez_wind_original['ISO'].nunique()} ISOs")
    
    # 2. Apply land use overlap adjustments globally
    print("Applying land use overlap adjustments globally...")
    df_rez_solar_adjusted, df_rez_wind_adjusted = _apply_global_overlap_adjustment(
        df_rez_solar_original, df_rez_wind_original
    )
    
    # 3. Calculate summary statistics
    processing_time = time.time() - start_time
    
    # Calculate before/after totals
    solar_gen_before = df_rez_solar_original['Generation Potential (GWh)'].sum() / 1000
    wind_gen_before = df_rez_wind_original['Generation Potential (GWh)'].sum() / 1000
    solar_gen_after = df_rez_solar_adjusted['Generation Potential (GWh)'].sum() / 1000
    wind_gen_after = df_rez_wind_adjusted['Generation Potential (GWh)'].sum() / 1000
    
    solar_cap_before = df_rez_solar_original['Installed Capacity Potential (MW)'].sum()
    wind_cap_before = df_rez_wind_original['Installed Capacity Potential (MW)'].sum()
    solar_cap_after = df_rez_solar_adjusted['Installed Capacity Potential (MW)'].sum()
    wind_cap_after = df_rez_wind_adjusted['Installed Capacity Potential (MW)'].sum()
    
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'processing_time_seconds': processing_time,
        'total_isos_processed': df_rez_solar_original['ISO'].nunique(),
        'solar_cells_processed': len(df_rez_solar_original),
        'wind_cells_processed': len(df_rez_wind_original),
        'global_impact_summary': {
            'solar_gen_before_twh': solar_gen_before,
            'solar_gen_after_twh': solar_gen_after,
            'solar_gen_change_pct': (solar_gen_after/solar_gen_before - 1) * 100,
            'wind_gen_before_twh': wind_gen_before,
            'wind_gen_after_twh': wind_gen_after,
            'wind_gen_change_pct': (wind_gen_after/wind_gen_before - 1) * 100,
            'total_gen_before_twh': solar_gen_before + wind_gen_before,
            'total_gen_after_twh': solar_gen_after + wind_gen_after,
            'total_gen_change_pct': ((solar_gen_after + wind_gen_after)/(solar_gen_before + wind_gen_before) - 1) * 100,
            'solar_cap_before_gw': solar_cap_before / 1000,
            'solar_cap_after_gw': solar_cap_after / 1000,
            'wind_cap_before_gw': wind_cap_before / 1000,
            'wind_cap_after_gw': wind_cap_after / 1000
        }
    }
    
    # Print global summary
    print(f"\nGLOBAL LAND USE ADJUSTMENT COMPLETED:")
    print(f"Processing time: {processing_time:.1f} seconds")
    print(f"ISOs processed: {metadata['total_isos_processed']}")
    print(f"Solar Generation: {solar_gen_before:.0f} → {solar_gen_after:.0f} TWh ({metadata['global_impact_summary']['solar_gen_change_pct']:+.1f}%)")
    print(f"Wind Generation:  {wind_gen_before:.0f} → {wind_gen_after:.0f} TWh ({metadata['global_impact_summary']['wind_gen_change_pct']:+.1f}%)")
    print(f"Total Generation: {solar_gen_before + wind_gen_before:.0f} → {solar_gen_after + wind_gen_after:.0f} TWh ({metadata['global_impact_summary']['total_gen_change_pct']:+.1f}%)")
    
    # 4. Prepare output data
    result_data = {
        'df_rez_solar_original': df_rez_solar_original,
        'df_rez_solar': df_rez_solar_adjusted,
        'df_rez_wind_original': df_rez_wind_original,
        'df_rez_wind': df_rez_wind_adjusted,
        'df_rez_windoff': df_rez_windoff_original,
        'processing_metadata': metadata
    }
    
    # 5. Cache results
    print("Caching results to disk...")
    os.makedirs('cache', exist_ok=True)
    with open(cache_file, 'wb') as f:
        pickle.dump(result_data, f)
    print(f"Results cached to {cache_file}")
    
    return result_data

def _apply_global_overlap_adjustment(solar_data, wind_data):
    """
    Apply land use overlap adjustment globally using LCOE share allocation.
    
    IDENTICAL LOGIC to single-ISO processing, but operates on:
    - (ISO, grid_cell) pairs instead of just grid_cell
    - All ISOs simultaneously for efficiency
    
    The core LCOE share allocation methodology remains unchanged.
    """
    
    # Create copies to avoid modifying originals
    solar_adj = solar_data.copy()
    wind_adj = wind_data.copy()
    
    # Get all unique (ISO, grid_cell) combinations
    solar_cells = set(zip(solar_data['ISO'], solar_data['grid_cell']))
    wind_cells = set(zip(wind_data['ISO'], wind_data['grid_cell']))
    all_cells = solar_cells.union(wind_cells)
    
    print(f"Processing {len(all_cells):,} unique (ISO, grid_cell) combinations...")
    
    adjustments_made = 0
    processed_count = 0
    
    for iso_code, grid_cell in all_cells:
        processed_count += 1
        
        # Progress reporting every 1000 cells
        if processed_count % 1000 == 0:
            print(f"  Processed {processed_count:,}/{len(all_cells):,} cells ({processed_count/len(all_cells)*100:.1f}%)")
        
        # Get solar and wind data for this (ISO, grid_cell) pair
        solar_row = solar_data[(solar_data['ISO'] == iso_code) & (solar_data['grid_cell'] == grid_cell)]
        wind_row = wind_data[(wind_data['ISO'] == iso_code) & (wind_data['grid_cell'] == grid_cell)]
        
        # Skip if only one technology present
        if len(solar_row) == 0 or len(wind_row) == 0:
            continue
            
        # Extract data (IDENTICAL to single-ISO logic)
        solar_area = solar_row.iloc[0]['Suitable Area (km²)']
        wind_area = wind_row.iloc[0]['Suitable Area (km²)']
        solar_cap = solar_row.iloc[0]['Installed Capacity Potential (MW)']
        wind_cap = wind_row.iloc[0]['Installed Capacity Potential (MW)']
        solar_gen = solar_row.iloc[0]['Generation Potential (GWh)']
        wind_gen = wind_row.iloc[0]['Generation Potential (GWh)']
        solar_lcoe = solar_row.iloc[0]['LCOE (USD/MWh)']
        wind_lcoe = wind_row.iloc[0]['LCOE (USD/MWh)']
        
        # Skip if any area is zero or NaN (avoid division by zero)
        if pd.isna(solar_area) or pd.isna(wind_area) or solar_area <= 0 or wind_area <= 0:
            continue
        
        # Calculate overlap (IDENTICAL logic)
        overlap_area = min(solar_area, wind_area)
        
        # Calculate competing capacities/generation in overlap zone (IDENTICAL logic)
        if solar_area <= wind_area:
            # All solar competes with portion of wind
            solar_competing_cap = solar_cap
            solar_competing_gen = solar_gen
            wind_competing_cap = (overlap_area / wind_area) * wind_cap
            wind_competing_gen = (overlap_area / wind_area) * wind_gen
            wind_untouched_cap = wind_cap - wind_competing_cap
            wind_untouched_gen = wind_gen - wind_competing_gen
            solar_untouched_cap = 0
            solar_untouched_gen = 0
        else:
            # All wind competes with portion of solar
            wind_competing_cap = wind_cap
            wind_competing_gen = wind_gen
            solar_competing_cap = (overlap_area / solar_area) * solar_cap
            solar_competing_gen = (overlap_area / solar_area) * solar_gen
            solar_untouched_cap = solar_cap - solar_competing_cap
            solar_untouched_gen = solar_gen - solar_competing_gen
            wind_untouched_cap = 0
            wind_untouched_gen = 0
        
        # Calculate LCOE shares for overlap allocation (IDENTICAL logic)
        lcoe_sum = solar_lcoe + wind_lcoe
        solar_multiplier = wind_lcoe / lcoe_sum  # Higher wind LCOE = more solar share
        wind_multiplier = solar_lcoe / lcoe_sum   # Higher solar LCOE = more wind share
        
        # Allocate competing capacity/generation based on LCOE shares (IDENTICAL logic)
        solar_allocated_cap = solar_competing_cap * solar_multiplier
        solar_allocated_gen = solar_competing_gen * solar_multiplier
        wind_allocated_cap = wind_competing_cap * wind_multiplier
        wind_allocated_gen = wind_competing_gen * wind_multiplier
        
        # Calculate final adjusted values (IDENTICAL logic)
        solar_final_cap = solar_allocated_cap + solar_untouched_cap
        solar_final_gen = solar_allocated_gen + solar_untouched_gen
        wind_final_cap = wind_allocated_cap + wind_untouched_cap
        wind_final_gen = wind_allocated_gen + wind_untouched_gen
        
        # Update the DataFrames (now using ISO + grid_cell for indexing)
        solar_mask = (solar_adj['ISO'] == iso_code) & (solar_adj['grid_cell'] == grid_cell)
        wind_mask = (wind_adj['ISO'] == iso_code) & (wind_adj['grid_cell'] == grid_cell)
        
        solar_adj.loc[solar_mask, 'Installed Capacity Potential (MW)'] = solar_final_cap
        solar_adj.loc[solar_mask, 'Generation Potential (GWh)'] = solar_final_gen
        wind_adj.loc[wind_mask, 'Installed Capacity Potential (MW)'] = wind_final_cap
        wind_adj.loc[wind_mask, 'Generation Potential (GWh)'] = wind_final_gen
        
        adjustments_made += 1
    
    print(f"Applied overlap adjustments to {adjustments_made:,} (ISO, grid_cell) pairs with both technologies")
    
    return solar_adj, wind_adj

def main():
    """Test the global processing function"""
    try:
        print("Testing global REZoning land use processor...")
        result = process_all_rezoning_data(force_refresh=False)
        
        print("\n" + "="*60)
        print("GLOBAL PROCESSING COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"DataFrames available:")
        print(f"  - df_rez_solar_original: {len(result['df_rez_solar_original']):,} rows")
        print(f"  - df_rez_solar: {len(result['df_rez_solar']):,} rows") 
        print(f"  - df_rez_wind_original: {len(result['df_rez_wind_original']):,} rows")
        print(f"  - df_rez_wind: {len(result['df_rez_wind']):,} rows")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()