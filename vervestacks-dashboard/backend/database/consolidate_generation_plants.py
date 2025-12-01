"""
Consolidate Transmission Generation Plants CSV Files

This script merges all country-specific CSV files from data/transmission_line_generation/
into a single consolidated CSV file with iso_code column added.

Usage:
    python consolidate_generation_plants.py
"""

import pandas as pd
from pathlib import Path
import sys

def consolidate_generation_plants():
    """
    Consolidate all transmission_line_generation CSV files into one file.
    
    Returns:
        tuple: (success: bool, output_path: str, total_rows: int, countries: int)
    """
    # Set up paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent  # Go up to VerveStacks root
    source_dir = project_root / 'data' / 'transmission_line_generation'
    output_file = script_dir / 'data' / 'transmission_generation_plants_consolidated.csv'
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if source directory exists
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        return False, None, 0, 0
    
    # Get all CSV files
    csv_files = list(source_dir.glob('*.csv'))
    
    if not csv_files:
        print(f"Error: No CSV files found in {source_dir}")
        return False, None, 0, 0
    
    print(f"Found {len(csv_files)} CSV files to consolidate...")
    
    # Required columns (from dashboard_data_analyzer.py)
    required_columns = ['Capacity (MW)', 'model_fuel', 'Latitude', 'Longitude', 'model_name']
    
    all_dataframes = []
    countries_processed = 0
    total_rows = 0
    errors = []
    
    for csv_file in sorted(csv_files):
        # Extract ISO code from filename (e.g., "BRA.csv" -> "BRA")
        iso_code = csv_file.stem.upper()
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_file)
            
            # Validate required columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                errors.append(f"{iso_code}: Missing columns {missing_columns}")
                continue
            
            # Add iso_code column
            df['iso_code'] = iso_code
            
            # Filter out rows with invalid coordinates (matching Python service logic)
            initial_count = len(df)
            df = df[
                df['Latitude'].notna() & 
                df['Longitude'].notna() & 
                (df['Latitude'] != 0) & 
                (df['Longitude'] != 0)
            ]
            filtered_count = initial_count - len(df)
            
            if filtered_count > 0:
                print(f"  {iso_code}: Filtered out {filtered_count} rows with invalid coordinates")
            
            if len(df) == 0:
                print(f"  {iso_code}: No valid rows after filtering")
                continue
            
            all_dataframes.append(df)
            countries_processed += 1
            total_rows += len(df)
            
            print(f"  {iso_code}: {len(df)} plants")
            
        except Exception as e:
            errors.append(f"{iso_code}: Error reading file - {str(e)}")
            continue
    
    if not all_dataframes:
        print("Error: No valid data to consolidate")
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(f"  - {error}")
        return False, None, 0, 0
    
    # Concatenate all dataframes
    print(f"\nConsolidating {len(all_dataframes)} dataframes...")
    consolidated_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Reorder columns: put iso_code first, then others
    columns = ['iso_code'] + [col for col in consolidated_df.columns if col != 'iso_code']
    consolidated_df = consolidated_df[columns]
    
    # Save to CSV
    print(f"Saving consolidated data to {output_file}...")
    consolidated_df.to_csv(output_file, index=False)
    
    print(f"\n✓ Consolidation complete!")
    print(f"  Total countries: {countries_processed}")
    print(f"  Total plants: {total_rows:,}")
    print(f"  Output file: {output_file}")
    
    if errors:
        print(f"\n⚠ Warnings ({len(errors)} files had issues):")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    
    return True, str(output_file), total_rows, countries_processed


if __name__ == '__main__':
    success, output_path, total_rows, countries = consolidate_generation_plants()
    
    if success:
        print(f"\n✓ Successfully consolidated {countries} countries with {total_rows:,} plants")
        sys.exit(0)
    else:
        print("\n✗ Consolidation failed")
        sys.exit(1)

