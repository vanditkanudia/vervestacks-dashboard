"""
Portal Dashboard Data Generator - Complete Energy Data
=======================================================

Compiles generation (TWh), capacity (GW), and emissions (mtCO2) data grouped by model_fuel 
for all ISOs and all years from both Ember and IRENA sources.

Output columns:
- iso_code, year, model_fuel, r10 (AR6 R10 region)
- generation_twh, capacity_gw, emissions_mtco2 (from Ember)
- irena_capacity_gw, irena_generation_twh (from IRENA)
"""

import pandas as pd
import duckdb
from pathlib import Path
import sys

# Add parent directory to path to import shared_data_loader
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_data_loader import SharedDataLoader

def compile_generation_and_capacity_data():
    """
    Compile generation (TWh), capacity (GW), and emissions (mtCO2) data grouped by iso_code, model_fuel, and year.
    Includes data from both Ember and IRENA sources, with AR6 R10 region mapping.
    
    Returns:
        pd.DataFrame: Table with columns [iso_code, year, model_fuel, generation_twh, capacity_gw, 
                      emissions_mtco2, irena_capacity_gw, irena_generation_twh, r10]
    """
    print("Loading data...")
    
    # Initialize shared data loader
    loader = SharedDataLoader(data_dir="data")
    
    # Load Ember data
    df_ember = loader.get_ember_data()
    print(f"  Ember data loaded: {len(df_ember):,} records")
    
    # Load typemap for model_fuel mapping
    df_irena_ember_map = loader.get_vs_mappings_sheet("irena_ember_typemap")
    print(f"  Type mapping loaded: {len(df_irena_ember_map)} mappings")
    
    # Rename columns to match processing pattern
    df_ember = df_ember.rename(columns={'Variable': 'Type', 'Country code': 'iso_code'})
    
    # Filter to only include fuel data (no aggregations)
    df_ember = df_ember[df_ember['Subcategory'] == 'Fuel']
    print(f"  Filtered to fuel data: {len(df_ember):,} records")
    
    # Register with DuckDB for joining
    duckdb.register('df_ember', df_ember)
    duckdb.register('df_irena_ember_map', df_irena_ember_map)
    
    # Add model_fuel to ember using SQL join (following verve_stacks_processor pattern)
    df_ember = duckdb.sql("""
        SELECT T2.model_fuel, T1.* 
        FROM df_ember T1 
        INNER JOIN df_irena_ember_map T2 ON T1.Type=T2.Type AND T2.Source='EMBER'
    """).df()
    print(f"  After model_fuel mapping: {len(df_ember):,} records")
    
    # === GENERATION DATA (TWh) ===
    df_generation = df_ember[df_ember['Unit'] == 'TWh'].copy()
    print(f"  Filtered to TWh: {len(df_generation):,} records")
    
    df_generation_grouped = (
        df_generation
        .groupby(['iso_code', 'Year', 'model_fuel'], as_index=False)['Value']
        .sum()
    )
    df_generation_grouped = df_generation_grouped.rename(columns={
        'Value': 'generation_twh',
        'Year': 'year'
    })
    
    print(f"\nGeneration data compiled:")
    print(f"   Total records: {len(df_generation_grouped):,}")
    
    # === CAPACITY DATA (GW) ===
    df_capacity = df_ember[df_ember['Unit'] == 'GW'].copy()
    print(f"\nCapacity data processing:")
    print(f"  Filtered to GW: {len(df_capacity):,} records")
    
    df_capacity_grouped = (
        df_capacity
        .groupby(['iso_code', 'Year', 'model_fuel'], as_index=False)['Value']
        .sum()
    )
    df_capacity_grouped = df_capacity_grouped.rename(columns={
        'Value': 'capacity_gw',
        'Year': 'year'
    })
    
    print(f"  Capacity data compiled: {len(df_capacity_grouped):,} records")
    
    # === EMISSIONS DATA (mtCO2) ===
    df_emissions = df_ember[df_ember['Unit'] == 'mtCO2'].copy()
    print(f"\nEmissions data processing:")
    print(f"  Filtered to mtCO2: {len(df_emissions):,} records")
    
    df_emissions_grouped = (
        df_emissions
        .groupby(['iso_code', 'Year', 'model_fuel'], as_index=False)['Value']
        .sum()
    )
    df_emissions_grouped = df_emissions_grouped.rename(columns={
        'Value': 'emissions_mtco2',
        'Year': 'year'
    })
    
    print(f"  Emissions data compiled: {len(df_emissions_grouped):,} records")
    
    # === IRENA DATA ===
    print(f"\nIRENA data processing:")
    
    # Load IRENA data
    df_irena_c = loader.get_irena_capacity_data()
    df_irena_g = loader.get_irena_generation_data()
    print(f"  IRENA capacity loaded: {len(df_irena_c):,} records")
    print(f"  IRENA generation loaded: {len(df_irena_g):,} records")
    
    # Add ISO codes to IRENA data (following verve_stacks_processor pattern)
    import pycountry
    import re
    
    def clean_country_name(country_name):
        if isinstance(country_name, str):
            return re.sub(r'\s*\(.*\)\s*$', '', country_name).strip()
        return country_name
    
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
    
    df_irena_c['Country/area'] = df_irena_c['Country/area'].apply(clean_country_name)
    df_irena_g['Country/area'] = df_irena_g['Country/area'].apply(clean_country_name)
    df_irena_c['iso_code'] = df_irena_c['Country/area'].apply(get_iso_code)
    df_irena_g['iso_code'] = df_irena_g['Country/area'].apply(get_iso_code)
    
    # Rename Technology to Type for mapping
    df_irena_c = df_irena_c.rename(columns={'Technology': 'Type'})
    df_irena_g = df_irena_g.rename(columns={'Technology': 'Type'})
    
    # Add model_fuel to IRENA using pandas merge (preserve all columns including years)
    df_irena_c = df_irena_c.merge(
        df_irena_ember_map[df_irena_ember_map['Source'] == 'IRENA'][['Type', 'model_fuel']],
        on='Type',
        how='inner'
    )
    
    df_irena_g = df_irena_g.merge(
        df_irena_ember_map[df_irena_ember_map['Source'] == 'IRENA'][['Type', 'model_fuel']],
        on='Type',
        how='inner'
    )
    
    print(f"  After model_fuel mapping - Capacity: {len(df_irena_c):,} records")
    print(f"  After model_fuel mapping - Generation: {len(df_irena_g):,} records")
    
    # IRENA data is already in long format with 'Year' and 'Electricity statistics (MW/GWh)' columns
    # Just need to group and rename
    
    # IRENA Capacity - filter and group
    df_irena_c = df_irena_c[df_irena_c['iso_code'].notna()].copy()
    df_irena_c['year'] = df_irena_c['Year']
    df_irena_c['irena_capacity_gw'] = pd.to_numeric(df_irena_c['Electricity statistics (MW/GWh)'], errors='coerce') / 1000  # MW to GW
    df_irena_c = df_irena_c.dropna(subset=['irena_capacity_gw'])
    
    df_irena_c_grouped = (
        df_irena_c
        .groupby(['iso_code', 'year', 'model_fuel'], as_index=False)['irena_capacity_gw']
        .sum()
    )
    
    # IRENA Generation - filter and group
    df_irena_g = df_irena_g[df_irena_g['iso_code'].notna()].copy()
    df_irena_g['year'] = df_irena_g['Year']
    df_irena_g['irena_generation_twh'] = pd.to_numeric(df_irena_g['Electricity statistics (MW/GWh)'], errors='coerce') / 1000  # GWh to TWh
    df_irena_g = df_irena_g.dropna(subset=['irena_generation_twh'])
    
    df_irena_g_grouped = (
        df_irena_g
        .groupby(['iso_code', 'year', 'model_fuel'], as_index=False)['irena_generation_twh']
        .sum()
    )
    
    print(f"  IRENA capacity grouped: {len(df_irena_c_grouped):,} records")
    print(f"  IRENA generation grouped: {len(df_irena_g_grouped):,} records")
    print(f"  IRENA technologies: {sorted(df_irena_c_grouped['model_fuel'].unique())}")
    
    # === AR6 R10 REGION MAPPING ===
    print(f"\nAR6 R10 region mapping:")
    df_ar6r10_map = loader.get_vs_mappings_sheet("ar6r10_iso_mapping")
    print(f"  AR6 R10 mapping loaded: {len(df_ar6r10_map)} mappings")
    print(f"  Columns: {list(df_ar6r10_map.columns)}")
    
    # The column might be named differently - check for r10, R10, region, etc.
    r10_col = None
    for col in df_ar6r10_map.columns:
        if 'r10' in str(col).lower():
            r10_col = col
            break
    
    if r10_col:
        print(f"  Using column: {r10_col}")
        print(f"  R10 regions: {sorted(df_ar6r10_map[r10_col].unique())}")
    else:
        print(f"  Warning: No R10 column found in mapping")
    
    # === MERGE ALL DATA ===
    df_merged = df_generation_grouped.merge(
        df_capacity_grouped,
        on=['iso_code', 'year', 'model_fuel'],
        how='outer'  # Keep all records from both datasets
    )
    
    df_merged = df_merged.merge(
        df_emissions_grouped,
        on=['iso_code', 'year', 'model_fuel'],
        how='outer'
    )
    
    # Merge IRENA data
    df_merged = df_merged.merge(
        df_irena_c_grouped,
        on=['iso_code', 'year', 'model_fuel'],
        how='outer'
    )
    
    df_merged = df_merged.merge(
        df_irena_g_grouped,
        on=['iso_code', 'year', 'model_fuel'],
        how='outer'
    )
    
    # Fill NaN values with 0 (for cases where data is missing)
    df_merged['generation_twh'] = df_merged['generation_twh'].fillna(0)
    df_merged['capacity_gw'] = df_merged['capacity_gw'].fillna(0)
    df_merged['emissions_mtco2'] = df_merged['emissions_mtco2'].fillna(0)
    df_merged['irena_capacity_gw'] = df_merged['irena_capacity_gw'].fillna(0)
    df_merged['irena_generation_twh'] = df_merged['irena_generation_twh'].fillna(0)
    
    # Add AR6 R10 region mapping
    if r10_col:
        # Rename to standard 'r10' for consistency (iso3 -> iso_code, r10_region -> r10)
        df_ar6r10_map_clean = df_ar6r10_map[['iso3', r10_col]].rename(columns={
            'iso3': 'iso_code',
            r10_col: 'r10'
        })
        df_merged = df_merged.merge(
            df_ar6r10_map_clean,
            on='iso_code',
            how='left'
        )
    else:
        # If no R10 column found, add empty column
        df_merged['r10'] = None
    
    print(f"\nMerged data:")
    print(f"   Total records: {len(df_merged):,}")
    print(f"   Countries: {df_merged['iso_code'].nunique()}")
    print(f"   Years: {df_merged['year'].min()}-{df_merged['year'].max()}")
    print(f"   Technologies: {sorted(df_merged['model_fuel'].unique())}")
    print(f"   R10 regions: {sorted(df_merged['r10'].dropna().unique())}")
    print(f"   ISOs without R10 mapping: {df_merged[df_merged['r10'].isna()]['iso_code'].nunique()}")
    
    return df_merged


if __name__ == "__main__":
    # Test the function
    df_data = compile_generation_and_capacity_data()
    
    # Save to CSV
    output_file = Path(__file__).parent / "data_overview_tab.csv"
    df_data.to_csv(output_file, index=False)
    print(f"\nData saved to: {output_file}")
    
    # Show sample
    print("\nSample data:")
    print(df_data.head(20))
    
    # Show summary statistics
    print("\nSummary by technology:")
    summary = df_data.groupby('model_fuel').agg({
        'generation_twh': ['count', 'sum', 'mean'],
        'capacity_gw': ['sum', 'mean'],
        'emissions_mtco2': ['sum', 'mean'],
        'irena_capacity_gw': ['sum', 'mean'],
        'irena_generation_twh': ['sum', 'mean']
    })
    print(summary)

