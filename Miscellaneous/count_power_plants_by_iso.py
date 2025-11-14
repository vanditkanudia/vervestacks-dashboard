#!/usr/bin/env python3
"""
Simple script to count operational power plants > 100MW by ISO code.
Uses the same GEM data loading logic as the map generation script.
"""

import pandas as pd
import pickle
from pathlib import Path
import sys
import os
import yaml
from datetime import datetime
import argparse

# Add the parent directory to Python path to import VerveStacksProcessor
sys.path.append(str(Path(__file__).parent.parent))

from verve_stacks_processor import VerveStacksProcessor

def load_gem_data():
    """Load GEM data efficiently from cache or Excel file."""
    cache_file = Path("../cache/global_data_cache.pkl")
    
    if cache_file.exists():
        print("Loading GEM data from cache...")
        try:
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
            return cached_data.get('df_gem')
        except Exception as e:
            print(f"Error loading from cache: {e}")
    
    # Fallback to loading via VerveStacksProcessor
    print("Loading GEM data via VerveStacksProcessor...")
    try:
        processor = VerveStacksProcessor()
        processor.load_all_data()
        return processor.df_gem
    except Exception as e:
        print(f"Error loading via processor: {e}")
        return None

def count_plants_by_iso(max_fossil_units=200):
    """Count operational power plants > 100MW by ISO code.
    
    Args:
        max_fossil_units (int): Maximum number of fossil fuel units per ISO for threshold calculation
    """
    
    # Load GEM data
    df_gem = load_gem_data()
    if df_gem is None:
        print("Failed to load GEM data")
        return
    
    print(f"Loaded {len(df_gem):,} total power plant records")
    
    # Filter for operational plants > 10MW (lower bound for better resolution in small countries)
    operational_plants = df_gem[
        (df_gem['Status'] == 'operating') & 
        (df_gem['Capacity (MW)'] >= 10.0)
    ].copy()
    
    print(f"Found {len(operational_plants):,} operational plants >= 10MW")
    print(f"Target: ≤{max_fossil_units} fossil units per ISO")
    
    # Find the correct country/ISO column
    iso_column = None
    for col in ['iso_code', 'ISO', 'Country code', 'Country', 'country']:
        if col in operational_plants.columns:
            iso_column = col
            break
    
    if iso_column is None:
        print("Could not find ISO/country column in data")
        print("Available columns:", list(operational_plants.columns))
        return
    
    print(f"Using column '{iso_column}' for country grouping")
    
    # Define capacity thresholds (starting from 10MW for better small country resolution)
    thresholds = [10, 50, 100, 250, 500, 1000]
    
    # Define fossil fuel categories (these bring retrofit options)
    fossil_fuels = ['coal', 'gas', 'oil']
    
    # Count plants by ISO and capacity threshold
    results_list = []
    
    # Filter out null/None ISO values
    valid_isos = operational_plants[iso_column].dropna().unique()
    
    for iso in valid_isos:
        iso_plants = operational_plants[operational_plants[iso_column] == iso]
        
        row_data = {'ISO': iso}
        
        # Separate fossil and non-fossil plants
        fossil_plants = iso_plants[iso_plants['model_fuel'].isin(fossil_fuels)]
        non_fossil_plants = iso_plants[~iso_plants['model_fuel'].isin(fossil_fuels)]
        
        # Count plants at each threshold - separate fossil vs non-fossil
        for threshold in thresholds:
            # Fossil fuel plants (with retrofit options)
            fossil_at_threshold = len(fossil_plants[fossil_plants['Capacity (MW)'] >= threshold])
            row_data[f'Fossil_{threshold}MW+'] = fossil_at_threshold
            
            # Non-fossil plants (no retrofit complexity)
            non_fossil_at_threshold = len(non_fossil_plants[non_fossil_plants['Capacity (MW)'] >= threshold])
            row_data[f'NonFossil_{threshold}MW+'] = non_fossil_at_threshold
        
        # Calculate dynamic threshold for max_fossil_units
        if len(fossil_plants) > 0:
            # Sort fossil plants by capacity (descending) and find threshold for target count
            fossil_sorted = fossil_plants.sort_values('Capacity (MW)', ascending=False)
            if len(fossil_sorted) <= max_fossil_units:
                # If we have fewer fossil plants than target, use 10MW threshold
                dynamic_threshold = 10
            else:
                # Find the capacity of the Nth largest plant (where N = max_fossil_units)
                dynamic_threshold = fossil_sorted.iloc[max_fossil_units - 1]['Capacity (MW)']
                # Round up to nearest 10MW for cleaner thresholds (better resolution for small countries)
                dynamic_threshold = int(((dynamic_threshold + 9) // 10) * 10)
            
            fossil_at_dynamic = len(fossil_plants[fossil_plants['Capacity (MW)'] >= dynamic_threshold])
        else:
            dynamic_threshold = 10
            fossil_at_dynamic = 0
        
        row_data[f'{max_fossil_units}_fossil_units_threshold'] = dynamic_threshold
        row_data[f'Fossil_at_{max_fossil_units}_threshold'] = fossil_at_dynamic
        
        # Capacity breakdown - keep only one total MW column
        fossil_capacity = fossil_plants['Capacity (MW)'].sum()
        non_fossil_capacity = non_fossil_plants['Capacity (MW)'].sum()
        total_capacity = fossil_capacity + non_fossil_capacity
        
        row_data['Total_Capacity_MW'] = total_capacity
        
        # Average sizes
        total_plants = len(iso_plants)
        avg_capacity = total_capacity / total_plants if total_plants > 0 else 0
        row_data['Avg_MW'] = avg_capacity
        
        results_list.append(row_data)
    
    # Create DataFrame and sort by fossil plants (10MW+)
    results = pd.DataFrame(results_list)
    results = results.sort_values('Fossil_10MW+', ascending=False)
    
    print("\n" + "="*130)
    print("OPERATIONAL POWER PLANTS BY CAPACITY THRESHOLD AND FUEL TYPE (ISO CODE)")
    print("="*130)
    print("Fossil fuels (coal/gas/oil) bring retrofit options → higher model complexity")
    print(f"Dynamic threshold targets ≤{max_fossil_units} fossil units per ISO")
    print("="*130)
    print(f"{'ISO':<5} {'F≥10':<6} {'NF≥10':<7} {'F≥50':<6} {'NF≥50':<7} {'F≥100':<6} {'NF≥100':<7} {'F≥250':<6} {'NF≥250':<7} {f'{max_fossil_units}F_Thr':<8} {f'F@{max_fossil_units}':<6} {'Total MW':<10}")
    print("-" * 110)
    
    for _, row in results.iterrows():
        iso = row['ISO']
        
        # Fossil plants at each threshold
        f_10 = int(row['Fossil_10MW+'])
        f_50 = int(row['Fossil_50MW+'])
        f_100 = int(row['Fossil_100MW+'])
        f_250 = int(row['Fossil_250MW+'])
        
        # Non-fossil plants at each threshold
        nf_10 = int(row['NonFossil_10MW+'])
        nf_50 = int(row['NonFossil_50MW+'])
        nf_100 = int(row['NonFossil_100MW+'])
        nf_250 = int(row['NonFossil_250MW+'])
        
        # Dynamic threshold data
        dynamic_threshold = int(row[f'{max_fossil_units}_fossil_units_threshold'])
        fossil_at_dynamic = int(row[f'Fossil_at_{max_fossil_units}_threshold'])
        
        # Total capacity
        total_mw = int(row['Total_Capacity_MW'])
        
        print(f"{iso:<5} {f_10:<6,} {nf_10:<7,} {f_50:<6,} {nf_50:<7,} {f_100:<6,} {nf_100:<7,} {f_250:<6,} {nf_250:<7,} {dynamic_threshold:<8,} {fossil_at_dynamic:<6,} {total_mw:<10,}")
    
    # Summary statistics
    total_fossil_10 = results['Fossil_10MW+'].sum()
    total_non_fossil_10 = results['NonFossil_10MW+'].sum()
    total_fossil_50 = results['Fossil_50MW+'].sum()
    total_non_fossil_50 = results['NonFossil_50MW+'].sum()
    total_fossil_100 = results['Fossil_100MW+'].sum()
    total_non_fossil_100 = results['NonFossil_100MW+'].sum()
    total_fossil_250 = results['Fossil_250MW+'].sum()
    total_non_fossil_250 = results['NonFossil_250MW+'].sum()
    
    total_fossil_at_dynamic = results[f'Fossil_at_{max_fossil_units}_threshold'].sum()
    total_capacity = results['Total_Capacity_MW'].sum()
    num_countries = len(results)
    
    print("-" * 110)
    print(f"TOTALS:")
    print(f"  ≥10MW: {int(total_fossil_10):,} fossil, {int(total_non_fossil_10):,} non-fossil")
    print(f"  ≥50MW: {int(total_fossil_50):,} fossil, {int(total_non_fossil_50):,} non-fossil")
    print(f"  ≥100MW: {int(total_fossil_100):,} fossil, {int(total_non_fossil_100):,} non-fossil")
    print(f"  ≥250MW: {int(total_fossil_250):,} fossil, {int(total_non_fossil_250):,} non-fossil") 
    print(f"  @{max_fossil_units}_FOSSIL_THRESHOLD: {int(total_fossil_at_dynamic):,} fossil plants globally")
    print(f"  TOTAL CAPACITY: {int(total_capacity):,} MW")
    print(f"  COUNTRIES: {num_countries}")
    
    # Analysis for model variable thresholds with fossil/non-fossil breakdown
    print("\n" + "="*120)
    print("THRESHOLD ANALYSIS FOR MODEL VARIABLES (FOSSIL vs NON-FOSSIL)")
    print("="*120)
    print("Model complexity = Fossil plants × (1 + retrofit options) + Non-fossil plants × 1")
    print("Fossil plants typically have 2-3x more variables due to CCS retrofit options")
    print("="*120)
    
    # Analyze countries with high complexity
    print("RECOMMENDED THRESHOLDS BY COUNTRY (targeting ~100-300 total model variables):")
    print(f"{'ISO':<5} {'Fossil Rec.':<12} {'NonFossil Rec.':<15} {'Model Variables':<15} {'Total MW':<10} {f'{max_fossil_units}F_Thr':<10}")
    print("-" * 80)
    
    for _, row in results.head(25).iterrows():  # Top 25 countries
        iso = row['ISO']
        
        # Get counts at each threshold
        f_10 = int(row['Fossil_10MW+'])
        f_50 = int(row['Fossil_50MW+'])
        f_100 = int(row['Fossil_100MW+'])
        f_250 = int(row['Fossil_250MW+'])
        f_500 = int(row['Fossil_500MW+'])
        f_1000 = int(row['Fossil_1000MW+'])
        
        nf_10 = int(row['NonFossil_10MW+'])
        nf_50 = int(row['NonFossil_50MW+'])
        nf_100 = int(row['NonFossil_100MW+'])
        nf_250 = int(row['NonFossil_250MW+'])
        nf_500 = int(row['NonFossil_500MW+'])
        nf_1000 = int(row['NonFossil_1000MW+'])
        
        # Determine optimal thresholds (fossil plants count 3x due to retrofit complexity)
        fossil_options = [
            (f_1000, "1000MW+", f_1000 * 3),
            (f_500, "500MW+", f_500 * 3),
            (f_250, "250MW+", f_250 * 3),
            (f_100, "100MW+", f_100 * 3),
            (f_50, "50MW+", f_50 * 3),
            (f_10, "10MW+", f_10 * 3)
        ]
        
        non_fossil_options = [
            (nf_1000, "1000MW+", nf_1000),
            (nf_500, "500MW+", nf_500),
            (nf_250, "250MW+", nf_250),
            (nf_100, "100MW+", nf_100),
            (nf_50, "50MW+", nf_50),
            (nf_10, "10MW+", nf_10)
        ]
        
        # Find best fossil threshold (target <150 variables from fossil)
        fossil_rec = "10MW+"
        fossil_vars = f_10 * 3
        for count, threshold, variables in fossil_options:
            if variables <= 150:
                fossil_rec = threshold
                fossil_vars = variables
                break
        
        # Find best non-fossil threshold (target <150 variables from non-fossil)
        non_fossil_rec = "10MW+"
        non_fossil_vars = nf_10
        for count, threshold, variables in non_fossil_options:
            if variables <= 150:
                non_fossil_rec = threshold
                non_fossil_vars = variables
                break
        
        total_model_vars = fossil_vars + non_fossil_vars
        
        total_mw = int(row['Total_Capacity_MW'])
        dynamic_threshold = int(row[f'{max_fossil_units}_fossil_units_threshold'])
        
        print(f"{iso:<5} {fossil_rec:<12} {non_fossil_rec:<15} {total_model_vars:<15,} {total_mw:<10,} {dynamic_threshold:<10,}")
    
    # Summary insights
    print("\n" + "="*120)
    print("KEY INSIGHTS FOR MODEL DESIGN:")
    print("="*120)
    
    # Countries with high fossil complexity
    high_fossil_countries = results[results['Fossil_10MW+'] > 200]
    if len(high_fossil_countries) > 0:
        print(f"\n🔥 HIGH FOSSIL COMPLEXITY COUNTRIES ({len(high_fossil_countries)} countries):")
        print("   These need higher fossil thresholds due to retrofit options:")
        for _, row in high_fossil_countries.head(10).iterrows():
            iso = row['ISO']
            f_10 = int(row['Fossil_10MW+'])
            f_100 = int(row['Fossil_100MW+'])
            f_250 = int(row['Fossil_250MW+'])
            dynamic_thr = int(row[f'{max_fossil_units}_fossil_units_threshold'])
            print(f"   {iso}: {f_10:,} fossil plants (≥10MW) → Dynamic threshold: {dynamic_thr}MW ({f_100:,} at 100MW, {f_250:,} at 250MW)")
    
    # Countries with high renewable complexity  
    high_renewable_countries = results[results['NonFossil_10MW+'] > 300]
    if len(high_renewable_countries) > 0:
        print(f"\n🌱 HIGH RENEWABLE COMPLEXITY COUNTRIES ({len(high_renewable_countries)} countries):")
        print("   These have many renewable/nuclear plants:")
        for _, row in high_renewable_countries.head(5).iterrows():
            iso = row['ISO']
            nf_10 = int(row['NonFossil_10MW+'])
            nf_50 = int(row['NonFossil_50MW+'])
            nf_100 = int(row['NonFossil_100MW+'])
            print(f"   {iso}: {nf_10:,} non-fossil plants (≥10MW) → {nf_50:,} at ≥50MW, {nf_100:,} at ≥100MW")
    
    print(f"\n💡 DYNAMIC THRESHOLD EFFECTIVENESS:")
    print(f"   Total fossil plants at {max_fossil_units}-unit thresholds: {int(total_fossil_at_dynamic):,}")
    print(f"   Average reduction from 10MW baseline: {((total_fossil_10 - total_fossil_at_dynamic) / total_fossil_10 * 100):.1f}%")
    print(f"   Small country resolution: Now includes plants ≥10MW (vs previous ≥100MW)")
    print(f"   Model complexity ratio: Fossil plants create ~3x more variables than renewables")
    
    # Save detailed results to CSV
    output_file = Path(f"Miscellaneous/output/power_plants_fossil_breakdown_{max_fossil_units}units_iso.csv")
    output_file.parent.mkdir(exist_ok=True)
    results.to_csv(output_file, index=False)
    print(f"\nDetailed fossil/non-fossil breakdown with {max_fossil_units}-unit thresholds saved to: {output_file}")
    
    return results

def generate_fuel_threshold_csv(results_df, max_fossil_units=200, target_hydro_geo=100, target_solar_wind=100, min_solar_wind_mw=200):
    """Generate CSV file with ISO-fuel specific capacity thresholds.
    
    Args:
        results_df: DataFrame from count_plants_by_iso analysis
        max_fossil_units: Target max fossil units per ISO
        target_hydro_geo: Target max hydro+geothermal units per ISO
        target_solar_wind: Target max solar/wind units per ISO each
        min_solar_wind_mw: Minimum MW for solar/wind individual tracking
    """
    
    print(f"\n🎯 Generating fuel-specific capacity thresholds CSV...")
    print(f"   Target: ≤{max_fossil_units} fossil, ≤{target_hydro_geo} hydro+geo, ≤{target_solar_wind} solar/wind each")
    
    # Load GEM data for detailed fuel-specific analysis
    df_gem = load_gem_data()
    if df_gem is None:
        print("❌ Failed to load GEM data for detailed analysis")
        return
    
    # Filter operational plants ≥10MW
    operational_plants = df_gem[
        (df_gem['Status'] == 'operating') & 
        (df_gem['Capacity (MW)'] >= 10.0)
    ].copy()
    
    # Find ISO column
    iso_column = None
    for col in ['iso_code', 'ISO', 'Country code', 'Country', 'country']:
        if col in operational_plants.columns:
            iso_column = col
            break
    
    if iso_column is None:
        print("❌ Could not find ISO column in GEM data")
        return
    
    # Define fuel categories (using exact model_fuel values from GEM data)
    fossil_fuels = ['coal', 'gas', 'oil']
    hydro_geo_fuels = ['hydro', 'geothermal']
    solar_wind_fuels = ['solar', 'windon', 'windoff']  # Separate onshore/offshore wind
    other_fuels = ['nuclear', 'bioenergy']
    
    # All actual model_fuel values for CSV columns
    all_model_fuels = ['bioenergy', 'coal', 'gas', 'geothermal', 'hydro', 'nuclear', 'oil', 'solar', 'windoff', 'windon']
    
    csv_data = []
    
    # Process each ISO
    valid_isos = operational_plants[iso_column].dropna().unique()
    
    for iso in valid_isos:
        iso_plants = operational_plants[operational_plants[iso_column] == iso]
        
        if len(iso_plants) == 0:
            continue
            
        thresholds = {'iso_code': iso}
        
        # 1. FOSSIL FUELS: Combined threshold for ≤max_fossil_units total
        fossil_plants = iso_plants[iso_plants['model_fuel'].isin(fossil_fuels)]
        if len(fossil_plants) > max_fossil_units:
            fossil_threshold = fossil_plants.nlargest(max_fossil_units, 'Capacity (MW)')['Capacity (MW)'].min()
            # Round to nearest 10MW
            fossil_threshold = round(fossil_threshold / 10) * 10
        else:
            fossil_threshold = 10.0  # Include all fossil plants
        
        thresholds['coal'] = fossil_threshold
        thresholds['gas'] = fossil_threshold
        thresholds['oil'] = fossil_threshold
        
        # 2. NUCLEAR: Always include all (threshold = 0)
        thresholds['nuclear'] = 0.0
        
        # 3. HYDRO + GEOTHERMAL: Combined threshold for ≤target_hydro_geo total
        hydro_geo_plants = iso_plants[iso_plants['model_fuel'].isin(hydro_geo_fuels)]
        if len(hydro_geo_plants) > target_hydro_geo:
            hydro_geo_threshold = hydro_geo_plants.nlargest(target_hydro_geo, 'Capacity (MW)')['Capacity (MW)'].min()
            hydro_geo_threshold = round(hydro_geo_threshold / 10) * 10
        else:
            hydro_geo_threshold = 10.0
        
        thresholds['hydro'] = hydro_geo_threshold
        thresholds['geothermal'] = hydro_geo_threshold
        
        # 4. SOLAR/WIND: Individual thresholds, >min_solar_wind_mw but max target_solar_wind each
        for fuel in solar_wind_fuels:
            fuel_plants = iso_plants[iso_plants['model_fuel'] == fuel]
            large_plants = fuel_plants[fuel_plants['Capacity (MW)'] >= min_solar_wind_mw]
            
            if len(large_plants) > target_solar_wind:
                threshold = large_plants.nlargest(target_solar_wind, 'Capacity (MW)')['Capacity (MW)'].min()
                threshold = max(threshold, min_solar_wind_mw)  # Ensure >= minimum
                threshold = round(threshold / 10) * 10
            else:
                threshold = min_solar_wind_mw  # Fixed minimum
            
            thresholds[fuel] = threshold
        
        # 5. OTHER FUELS: Default threshold
        for fuel in other_fuels:
            if fuel == 'nuclear':
                continue  # Already handled
            thresholds[fuel] = 50.0  # Use actual model_fuel names
        
        # Add notes
        fossil_count = len(fossil_plants[fossil_plants['Capacity (MW)'] >= fossil_threshold])
        hydro_geo_count = len(hydro_geo_plants[hydro_geo_plants['Capacity (MW)'] >= hydro_geo_threshold])
        
        if fossil_count <= max_fossil_units and hydro_geo_count <= target_hydro_geo:
            thresholds['notes'] = 'auto_generated'
        else:
            thresholds['notes'] = f'auto_generated_F{fossil_count}_HG{hydro_geo_count}'
        
        csv_data.append(thresholds)
    
    # Create DataFrame
    df_thresholds = pd.DataFrame(csv_data)
    
    # Ensure all model_fuel columns exist (using exact GEM model_fuel names)
    fuel_columns = all_model_fuels  # Use actual model_fuel values
    for col in fuel_columns:
        if col not in df_thresholds.columns:
            df_thresholds[col] = 50.0  # Default threshold
    
    # Reorder columns
    column_order = ['iso_code'] + fuel_columns + ['notes']
    df_thresholds = df_thresholds[column_order]
    
    # Sort by ISO code
    df_thresholds = df_thresholds.sort_values('iso_code')
    
    # Save to CSV
    output_file = Path("assumptions/iso_fuel_capacity_thresholds.csv")
    output_file.parent.mkdir(exist_ok=True)
    df_thresholds.to_csv(output_file, index=False, float_format='%.1f')
    
    print(f"✅ Fuel-specific thresholds saved to: {output_file}")
    print(f"   📊 Generated thresholds for {len(df_thresholds)} ISOs")
    
    # Generate metadata file
    metadata = {
        'generation_info': {
            'generated_date': datetime.utcnow().isoformat() + 'Z',
            'source_data': 'GEM Global Integrated Power Database',
            'target_fossil_units': max_fossil_units,
            'target_hydro_geo_units': target_hydro_geo,
            'target_solar_wind_units': target_solar_wind,
            'min_solar_wind_mw': min_solar_wind_mw
        },
        'methodology': {
            'fossil_fuels': 'Combined threshold for coal+gas+oil to achieve target count',
            'nuclear': 'Always 0.0 - track all nuclear units individually',
            'hydro_geothermal': 'Combined threshold for hydro+geothermal',
            'solar_wind': 'Individual thresholds with minimum MW requirement',
            'other_fuels': 'Default 50MW threshold for biomass, waste, other'
        },
        'fuel_definitions': {
            'coal': 'All coal-fired thermal plants',
            'gas': 'Natural gas and LNG plants',
            'oil': 'Oil and diesel plants',
            'nuclear': 'Nuclear power plants',
            'hydro': 'Hydroelectric plants (all types)',
            'geothermal': 'Geothermal power plants',
            'solar': 'Solar PV and CSP plants',
            'wind': 'Onshore and offshore wind',
            'biomass': 'Biomass and biogas plants',
            'waste': 'Waste-to-energy plants',
            'other': 'Other renewable and alternative fuels'
        }
    }
    
    metadata_file = Path("assumptions/iso_fuel_capacity_thresholds_metadata.yaml")
    with open(metadata_file, 'w') as f:
        yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
    
    print(f"📋 Metadata saved to: {metadata_file}")
    
    # Show sample of results
    print(f"\n📋 Sample thresholds (first 10 ISOs):")
    print(df_thresholds.head(10).to_string(index=False))
    
    return df_thresholds

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze power plant capacity thresholds by ISO and fuel type')
    parser.add_argument('--max-fossil-units', type=int, default=200, 
                       help='Target maximum fossil fuel units per ISO (default: 200)')
    parser.add_argument('--generate-csv', action='store_true',
                       help='Generate CSV file with fuel-specific capacity thresholds')
    parser.add_argument('--target-hydro-geo', type=int, default=100,
                       help='Target maximum hydro+geothermal units per ISO (default: 100)')
    parser.add_argument('--target-solar-wind', type=int, default=100,
                       help='Target maximum solar/wind units per ISO each (default: 100)')
    parser.add_argument('--min-solar-wind-mw', type=int, default=200,
                       help='Minimum MW for solar/wind individual tracking (default: 200)')
    
    args = parser.parse_args()
    
    # Run the main analysis
    results = count_plants_by_iso(max_fossil_units=args.max_fossil_units)
    
    # Generate CSV if requested
    if args.generate_csv:
        generate_fuel_threshold_csv(
            results, 
            max_fossil_units=args.max_fossil_units,
            target_hydro_geo=args.target_hydro_geo,
            target_solar_wind=args.target_solar_wind,
            min_solar_wind_mw=args.min_solar_wind_mw
        )
