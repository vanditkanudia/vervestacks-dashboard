"""
Compile GEM Plants Data - Standalone Script
==========================================

Processes Global Energy Monitor (GEM) power plant data and exports enriched CSV.
Extracts the df_gem processing logic from verve_stacks_processor.py for standalone use.

Author: VerveStacks Team
"""

import pandas as pd
import pycountry
import re
from pathlib import Path
import sys

# Add parent directory to path to import shared_data_loader
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_data_loader import SharedDataLoader


def get_data_paths():
    """Get the correct data paths based on current working directory."""
    current_dir = Path.cwd()
    
    # Check if we're in the portal directory
    if current_dir.name == "portal":
        data_dir = Path("../data")
        assumptions_dir = Path("../assumptions")
    else:
        # Assume we're in the project root
        data_dir = Path("data")
        assumptions_dir = Path("assumptions")
    
    return data_dir, assumptions_dir


def load_gem_data():
    """Load GEM data from Excel file."""
    print("Loading GEM data...")
    
    data_dir, _ = get_data_paths()
    gem_file = data_dir / "existing_stock/Global-Integrated-Power-April-2025.xlsx"
    
    if not gem_file.exists():
        raise FileNotFoundError(f"GEM data file not found: {gem_file}")
    
    df_gem = pd.read_excel(gem_file, sheet_name="Power facilities")
    print(f"  Loaded {len(df_gem):,} power plant records from {gem_file}")
    
    return df_gem


def load_mapping_data():
    """Load mapping tables from VS_mappings.xlsx."""
    print("Loading mapping data...")
    
    data_dir, _ = get_data_paths()
    loader = SharedDataLoader(data_dir=str(data_dir))
    
    # Load mapping tables
    df_gem_map = loader.get_vs_mappings_sheet("gem_techmap")
    df_gem_status_map = loader.get_vs_mappings_sheet("gem_statusmap")
    
    print(f"  Loaded {len(df_gem_map)} technology mappings")
    print(f"  Loaded {len(df_gem_status_map)} status mappings")
    
    return df_gem_map, df_gem_status_map


def clean_country_name(country_name):
    """Clean country names by removing parenthetical information."""
    if isinstance(country_name, str):
        return re.sub(r'\s*\(.*\)\s*$', '', country_name).strip()
    return country_name


def get_iso_code(country_name):
    """Get ISO 3-letter country code from country name."""
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


def process_gem_data(df_gem, df_gem_map, df_gem_status_map):
    """Process GEM data with filtering, mapping, and enrichment."""
    print("Processing GEM data...")
    
    # Step 1: Filter to only keep specific statuses
    print("  Filtering plant statuses...")
    statuses_to_keep = ['operating', 'construction', 'mothballed']
    initial_count = len(df_gem)
    
    # Convert status to lowercase for comparison
    df_gem['Status_lower'] = df_gem['Status'].str.lower()
    df_gem = df_gem[df_gem['Status_lower'].isin(statuses_to_keep)]
    df_gem = df_gem.drop('Status_lower', axis=1)  # Clean up temporary column
    
    filtered_count = len(df_gem)
    print(f"    Kept {filtered_count:,} plants with statuses: {statuses_to_keep}")
    print(f"    Removed {initial_count - filtered_count:,} plants with other statuses")
    
    # Step 2: Technology field - use Type as fallback if missing
    print("  Adding Technology field...")
    df_gem['Technology'] = df_gem.apply(
        lambda row: row['Type'] if pd.isna(row['Technology']) else row['Technology'], axis=1
    )
    
    # Step 3: Create Type_mod field for oil/gas splitting
    print("  Creating Type_mod field...")
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
    
    df_gem['Type_mod'] = df_gem.apply(custom_type, axis=1)
    
    # Step 4: Add model_fuel and model_name using technology mapping
    print("  Applying technology mapping...")
    df_gem = df_gem.merge(
        df_gem_map[['Type_mod', 'Technology', 'model_fuel', 'model_name']], 
        on=['Type_mod', 'Technology'], 
        how='left'
    )
    
    # Step 5: Add status detail to model_name
    print("  Applying status mapping...")
    df_gem = df_gem.merge(
        df_gem_status_map[['status', 'model_name']], 
        left_on='Status', 
        right_on='status',
        how='left',
        suffixes=('', '_status')
    )
    
    # Prefix model_name with status model_name
    df_gem['model_name'] = df_gem['model_name_status'].fillna('') + df_gem['model_name'].fillna('')
    
    # Clean up temporary columns
    df_gem = df_gem.drop(['model_name_status', 'status'], axis=1)
    
    # Step 6: Handle unmapped combinations with fallback logic
    print("  Handling unmapped combinations...")
    def fallback_fuel_and_name(row):
        if pd.isna(row['model_fuel']):
            print(f"    UNMAPPED: Type='{row['Type']}', Technology='{row['Technology']}', Country='{row.get('Country/area', 'N/A')}'")
            
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
            
            print(f"      → FALLBACK: model_fuel='{fallback_value}'")
            return fallback_value
        else:
            return row['model_fuel']
    
    # Count unmapped records before applying fallback
    unmapped_count = df_gem['model_fuel'].isna().sum()
    if unmapped_count > 0:
        print(f"    Found {unmapped_count} unmapped (Type, Technology) combinations")
    
    df_gem['model_fuel'] = df_gem.apply(fallback_fuel_and_name, axis=1)
    
    # Verify no NaN values remain
    remaining_nan = df_gem['model_fuel'].isna().sum()
    if remaining_nan > 0:
        print(f"    WARNING: {remaining_nan} model_fuel values are still NaN after fallback!")
    else:
        print(f"    All model_fuel values resolved (no NaN remaining)")
    
    # Step 7: Fill missing model_names with ep_ prefix pattern
    print("  Filling missing model names...")
    df_gem['model_name'] = df_gem['model_name'].fillna(
        df_gem['model_fuel'].apply(lambda x: f'ep_{x}')
    )
    
    # Step 8: Add ISO codes
    print("  Adding ISO codes...")
    df_gem['iso_code'] = df_gem['Country/area'].apply(get_iso_code)
    
    # Count records with and without ISO codes
    iso_count = df_gem['iso_code'].notna().sum()
    no_iso_count = df_gem['iso_code'].isna().sum()
    print(f"    Added ISO codes: {iso_count:,} records")
    if no_iso_count > 0:
        print(f"    Records without ISO codes: {no_iso_count:,}")
    
    print(f"  Final processed records: {len(df_gem):,}")
    
    return df_gem


def export_to_csv(df_gem, output_file):
    """Export processed GEM data to CSV."""
    print(f"Exporting to CSV: {output_file}")
    
    # Create output directory if it doesn't exist
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export to CSV
    df_gem.to_csv(output_file, index=False)
    
    print(f"  Exported {len(df_gem):,} records to {output_file}")
    
    # Show summary statistics
    print("\nSummary Statistics:")
    print(f"  Total plants: {len(df_gem):,}")
    print(f"  Countries: {df_gem['iso_code'].nunique()}")
    print(f"  Technologies: {df_gem['model_fuel'].nunique()}")
    print(f"  Total capacity: {df_gem['Capacity (MW)'].sum():,.0f} MW")
    
    print("\nTechnology breakdown:")
    tech_summary = df_gem.groupby('model_fuel').agg({
        'Capacity (MW)': ['count', 'sum'],
        'Plant / Project name': 'count'
    }).round(0)
    tech_summary.columns = ['Plant Count', 'Total Capacity (MW)', 'Plant Count (alt)']
    print(tech_summary)
    
    print("\nTop 10 countries by capacity:")
    country_summary = df_gem.groupby(['iso_code', 'Country/area']).agg({
        'Capacity (MW)': 'sum',
        'Plant / Project name': 'count'
    }).sort_values('Capacity (MW)', ascending=False).head(10)
    country_summary.columns = ['Total Capacity (MW)', 'Plant Count']
    print(country_summary)


def main():
    """Main function to process GEM data."""
    print("=" * 60)
    print("GEM Plants Data Compilation")
    print("=" * 60)
    
    try:
        # Load data
        df_gem = load_gem_data()
        df_gem_map, df_gem_status_map = load_mapping_data()
        
        # Process data
        df_processed = process_gem_data(df_gem, df_gem_map, df_gem_status_map)
        
        # Export to CSV - always save in portal root
        script_dir = Path(__file__).parent  # portal directory
        output_file = script_dir / "processed_gem_plants_data.csv"
        export_to_csv(df_processed, str(output_file))
        
        print("\n" + "=" * 60)
        print("Processing completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
