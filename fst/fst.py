import pandas as pd
import os
import pycountry
import numpy as np


def get_iso_code(country_name):
    """Convert country name to ISO 3-letter code"""
    try:
        return pycountry.countries.lookup(country_name).alpha_3
    except LookupError:
        return None


def create_gem_ember_mapping():
    """Create mapping between GEM and EMBER fuel/technology types"""
    mapping = {
        # GEM types -> EMBER categories
        'Coal': 'Coal',
        'Lignite': 'Coal', 
        'Natural Gas': 'Gas',
        'Oil': 'Oil',
        'Nuclear': 'Nuclear',
        'Hydro': 'Hydro',
        'Wind': 'Wind',
        'Solar': 'Solar',
        'Biomass': 'Bioenergy',
        'Waste': 'Bioenergy',
        'Geothermal': 'Geothermal',
        'Ocean': 'Ocean',
        'Pumped Storage': 'Hydro',
        'Battery Storage': 'Storage',
        'Other': 'Other',
        'Unknown': 'Other'
    }
    return mapping


def aggregate_gem_data(df, mapping):
    """Aggregate GEM data by country, fuel type, and year"""
    # Apply mapping to standardize fuel types
    df['EMBER_Fuel'] = df['Type'].map(mapping).fillna('Other')
    
    # Group by country, fuel type, and year (if available)
    agg_columns = ['Country/area', 'EMBER_Fuel']
    if 'Year' in df.columns:
        agg_columns.append('Year')
    
    aggregated = df.groupby(agg_columns, as_index=False).agg({
        'Capacity (MW)': 'sum',
        'Status': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'Unknown'
    })
    
    # Convert to GW
    aggregated['Capacity (GW)'] = aggregated['Capacity (MW)'] / 1000
    
    # Add ISO codes
    aggregated['ISO_Code'] = aggregated['Country/area'].apply(get_iso_code)
    
    return aggregated


def load_and_process_gem_data():
    """Load and process GEM data from Excel file"""
    excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx') or f.endswith('.xls')]
    
    if not excel_files:
        print("No Excel file found in the folder.")
        return None
    
    # Load GEM data
    df = pd.read_excel('Global-Integrated-Power-April-2025.xlsx', sheet_name='Power facilities', nrows=4000)
    
    print("GEM Data Structure:")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print("\nFirst few rows:")
    print(df.head())
    
    print("\nUnique fuel types in GEM data:")
    print(df['Type'].value_counts())
    
    return df


def create_comparison_framework():
    """Create framework for comparing GEM and EMBER data"""
    # Define EMBER fuel categories
    ember_categories = [
        'Coal', 'Gas', 'Oil', 'Nuclear', 'Hydro', 'Wind', 'Solar', 
        'Bioenergy', 'Geothermal', 'Ocean', 'Storage', 'Other'
    ]
    
    # Create comparison template
    comparison_template = pd.DataFrame({
        'Fuel_Type': ember_categories,
        'GEM_Capacity_GW': 0,
        'EMBER_Capacity_GW': 0,
        'Difference_GW': 0,
        'Difference_Percent': 0
    })
    
    return comparison_template


def main():
    """Main function to process GEM data and prepare for EMBER comparison"""
    print("=== GEM Data Processing and EMBER Mapping ===")
    
    # Load GEM data
    gem_df = load_and_process_gem_data()
    if gem_df is None:
        return
    
    # Create mapping
    mapping = create_gem_ember_mapping()
    print(f"\nGEM to EMBER mapping created with {len(mapping)} fuel types")
    
    # Aggregate GEM data
    aggregated_gem = aggregate_gem_data(gem_df, mapping)
    
    print("\nAggregated GEM Data by EMBER fuel categories:")
    ember_summary = aggregated_gem.groupby('EMBER_Fuel')['Capacity (GW)'].sum()
    print(ember_summary)
    
    print("\nSample aggregated data:")
    print(aggregated_gem.head(10))
    
    # Create comparison framework
    comparison_template = create_comparison_framework()
    print("\nComparison template created for EMBER data integration")
    
    # Save processed data
    aggregated_gem.to_csv('gem_aggregated_by_ember_categories.csv', index=False)
    comparison_template.to_csv('comparison_template.csv', index=False)
    
    print("\nFiles saved:")
    print("- gem_aggregated_by_ember_categories.csv: GEM data aggregated by EMBER categories")
    print("- comparison_template.csv: Template for EMBER comparison")
    
    return aggregated_gem, comparison_template


if __name__ == "__main__":
    result = main()
    if result:
        aggregated_gem, comparison_template = result
