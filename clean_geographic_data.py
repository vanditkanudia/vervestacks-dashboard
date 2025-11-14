#!/usr/bin/env python3
"""
Universal Geographic Data Cleaner
=================================

Cleans coordinate outliers from any dataset (CSV/Excel) using statistical detection + web lookup.
Creates corrected file with _geocorrected suffix in the same folder as input.

Usage:
    python clean_geographic_data.py --input worldcities.csv --lat-col lat --lng-col lng --country-col iso3 --name-col city
    python clean_geographic_data.py --input gem_data.xlsx --sheet "Global Power Plants" --lat-col Latitude --lng-col Longitude --country-col Country --name-col "Plant Name"

Features:e
- Statistical outlier detection (3-sigma from country mean coordinates)
- Web-based coordinate lookup for corrections
- Supports CSV and Excel files (with sheet specification)
- Generates correction file with _geocorrected suffix
- Preserves all original columns + adds correction metadata
"""

import pandas as pd
import numpy as np
import requests
import time
from geopy.geocoders import Nominatim
import argparse
from pathlib import Path
import sys

class UniversalGeoDataCleaner:
    def __init__(self, lat_col, lng_col, country_col, name_col, 
                 region_col=None, weight_col=None, sigma_threshold=4.0, rate_limit_delay=1.0):
        self.lat_col = lat_col
        self.lng_col = lng_col  
        self.country_col = country_col
        self.name_col = name_col
        self.region_col = region_col
        self.weight_col = weight_col
        self.sigma_threshold = sigma_threshold
        
        # Initialize geocoder
        self.geocoder = Nominatim(user_agent="universal_geo_cleaner_v1.0")
        self.rate_limit_delay = rate_limit_delay
        self.lookup_cache = {}
        
    def load_data(self, file_path, sheet_name=None):
        """Load data from CSV or Excel"""
        path = Path(file_path)
        
        if path.suffix.lower() == '.csv':
            if sheet_name:
                print(f"Warning: Sheet name '{sheet_name}' ignored for CSV file")
            return pd.read_csv(file_path)
        elif path.suffix.lower() in ['.xlsx', '.xls']:
            if sheet_name:
                return pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
    
    def validate_columns(self, df):
        """Validate that required columns exist in the dataset and auto-detect weight column"""
        required_cols = [self.lat_col, self.lng_col, self.country_col, self.name_col]
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            print(f"Error: Missing required columns: {missing_cols}")
            print(f"Available columns: {list(df.columns)}")
            return False
        
        if self.region_col and self.region_col not in df.columns:
            print(f"Warning: Region column '{self.region_col}' not found, will skip in geocoding")
            self.region_col = None
        
        # Auto-detect weight column if not specified
        if not self.weight_col:
            weight_candidates = [
                'population', 'pop', 'capacity', 'capacity_mw', 'mw', 'gw', 
                'generation', 'generation_gwh', 'gwh', 'twh', 'area', 'size'
            ]
            
            available_cols = [col.lower() for col in df.columns]
            for candidate in weight_candidates:
                if candidate in available_cols:
                    # Find the actual column name (preserving case)
                    actual_col = next(col for col in df.columns if col.lower() == candidate)
                    self.weight_col = actual_col
                    print(f"Auto-detected weight column: '{actual_col}'")
                    break
            
            if not self.weight_col:
                print("Warning: No weight column detected, will use equal weights for share calculation")
        
        elif self.weight_col not in df.columns:
            print(f"Warning: Weight column '{self.weight_col}' not found, will use equal weights")
            self.weight_col = None
            
        return True
    
    def detect_outliers_by_country(self, df):
        """Detect coordinate outliers using mean lat/lng as reference"""
        print(f"\nDetecting outliers using {self.sigma_threshold}-sigma threshold...")
        
        # Basic coordinate validation first
        valid_lat = (df[self.lat_col] >= -90) & (df[self.lat_col] <= 90)
        valid_lng = (df[self.lng_col] >= -180) & (df[self.lng_col] <= 180)
        basic_invalid = ~(valid_lat & valid_lng)
        
        if basic_invalid.sum() > 0:
            print(f"Found {basic_invalid.sum()} records with invalid coordinate ranges (lat: ±90°, lng: ±180°)")
        
        all_outliers = []
        countries_processed = 0
        
        for country in df[self.country_col].unique():
            if pd.isna(country):
                continue
                
            country_data = df[df[self.country_col] == country].copy()
            
            # Need minimum data points for statistics
            if len(country_data) < 5:
                continue
            
            countries_processed += 1
            
            # Use mean coordinates as reference (robust since outliers are rare)
            ref_lat = country_data[self.lat_col].mean()
            ref_lng = country_data[self.lng_col].mean()
            
            # Calculate absolute deviations from mean
            country_data['lat_dev'] = abs(country_data[self.lat_col] - ref_lat)
            country_data['lng_dev'] = abs(country_data[self.lng_col] - ref_lng)
            
            # Calculate 3-sigma thresholds
            lat_mean_dev = country_data['lat_dev'].mean()
            lat_std_dev = country_data['lat_dev'].std()
            lng_mean_dev = country_data['lng_dev'].mean() 
            lng_std_dev = country_data['lng_dev'].std()
            
            # Handle edge case where std is 0 (all points identical)
            if lat_std_dev == 0:
                lat_threshold = lat_mean_dev + 0.1  # Small threshold
            else:
                lat_threshold = lat_mean_dev + self.sigma_threshold * lat_std_dev
                
            if lng_std_dev == 0:
                lng_threshold = lng_mean_dev + 0.1  # Small threshold  
            else:
                lng_threshold = lng_mean_dev + self.sigma_threshold * lng_std_dev
            
            # Identify outliers
            lat_outliers = country_data['lat_dev'] > lat_threshold
            lng_outliers = country_data['lng_dev'] > lng_threshold
            outliers_mask = lat_outliers | lng_outliers
            
            if outliers_mask.sum() > 0:
                outliers = country_data[outliers_mask].copy()
                outliers['ref_lat'] = ref_lat
                outliers['ref_lng'] = ref_lng
                outliers['lat_threshold'] = lat_threshold
                outliers['lng_threshold'] = lng_threshold
                outliers['detection_method'] = f'{self.sigma_threshold}sigma_from_mean'
                
                print(f"  {country}: {len(outliers)}/{len(country_data)} outliers "
                      f"(ref: {ref_lat:.3f}, {ref_lng:.3f}, thresholds: ±{lat_threshold:.3f}°, ±{lng_threshold:.3f}°)")
                
                all_outliers.append(outliers)
        
        print(f"Processed {countries_processed} countries")
        return pd.concat(all_outliers, ignore_index=True) if all_outliers else pd.DataFrame()
    
    def lookup_coordinates(self, name, country, region=None):
        """Look up correct coordinates using web geocoding"""
        
        # Build search queries in order of preference
        search_queries = []
        if region and pd.notna(region):
            search_queries.append(f"{name}, {region}, {country}")
        search_queries.extend([
            f"{name}, {country}",
            f"{name}"  # Fallback
        ])
        
        for query in search_queries:
            if query in self.lookup_cache:
                return self.lookup_cache[query]
            
            try:
                time.sleep(self.rate_limit_delay)  # Rate limiting
                location = self.geocoder.geocode(query, timeout=10)
                
                if location:
                    result = {
                        'corrected_lat': location.latitude,
                        'corrected_lng': location.longitude,
                        'lookup_query': query,
                        'lookup_confidence': 'found',
                        'lookup_address': location.address
                    }
                    self.lookup_cache[query] = result
                    return result
                    
            except Exception as e:
                print(f"    Lookup failed for '{query}': {e}")
                continue
        
        # No results found
        return {
            'corrected_lat': None,
            'corrected_lng': None,
            'lookup_query': search_queries[0],
            'lookup_confidence': 'not_found',
            'lookup_address': None
        }
    
    def process_outliers(self, outliers_df, original_df):
        """Process outliers by looking up correct coordinates with validation"""
        if len(outliers_df) == 0:
            return pd.DataFrame()
        
        print(f"\nLooking up corrections for {len(outliers_df)} outliers...")
        print("This may take a while due to rate limiting...")
        
        corrections = []
        
        for i, (_, row) in enumerate(outliers_df.iterrows()):
            print(f"  [{i+1}/{len(outliers_df)}] {row[self.name_col]} ({row[self.country_col]}): "
                  f"({row[self.lat_col]:.3f}, {row[self.lng_col]:.3f})", end=" -> ")
            
            # Look up correction
            region_value = row[self.region_col] if self.region_col else None
            correction_data = self.lookup_coordinates(
                row[self.name_col], 
                row[self.country_col], 
                region_value
            )
            
            # Validate correction
            if correction_data['corrected_lat'] is not None:
                corrected_lat = correction_data['corrected_lat']
                corrected_lng = correction_data['corrected_lng']
                original_lat = row[self.lat_col]
                original_lng = row[self.lng_col]
                
                # Check if correction is significant (different when rounded to 3 decimals)
                if (round(corrected_lat, 3) == round(original_lat, 3) and 
                    round(corrected_lng, 3) == round(original_lng, 3)):
                    print("MINOR CHANGE (skipped) ≈")
                    continue
                
                # Validate that correction is not itself an outlier
                country_data = original_df[original_df[self.country_col] == row[self.country_col]]
                if len(country_data) >= 5:  # Need minimum data for validation
                    ref_lat = country_data[self.lat_col].mean()
                    ref_lng = country_data[self.lng_col].mean()
                    
                    # Calculate deviation of corrected coordinates
                    corrected_lat_dev = abs(corrected_lat - ref_lat)
                    corrected_lng_dev = abs(corrected_lng - ref_lng)
                    
                    # Calculate thresholds for this country
                    lat_mean_dev = country_data[self.lat_col].apply(lambda x: abs(x - ref_lat)).mean()
                    lat_std_dev = country_data[self.lat_col].apply(lambda x: abs(x - ref_lat)).std()
                    lng_mean_dev = country_data[self.lng_col].apply(lambda x: abs(x - ref_lng)).mean()
                    lng_std_dev = country_data[self.lng_col].apply(lambda x: abs(x - ref_lng)).std()
                    
                    lat_threshold = lat_mean_dev + self.sigma_threshold * lat_std_dev if lat_std_dev > 0 else lat_mean_dev + 0.1
                    lng_threshold = lng_mean_dev + self.sigma_threshold * lng_std_dev if lng_std_dev > 0 else lng_mean_dev + 0.1
                    
                    # Check if correction is also an outlier (but don't reject, just flag)
                    is_correction_outlier = corrected_lat_dev > lat_threshold or corrected_lng_dev > lng_threshold
            
            # Create corrected row with clean format
            if correction_data['corrected_lat'] is not None:
                corrected_row = row.to_dict()
                # Replace original coordinates with corrected ones
                corrected_row[self.lat_col] = correction_data['corrected_lat']
                corrected_row[self.lng_col] = correction_data['corrected_lng']
                # Add old coordinates as new columns
                corrected_row['lat_old'] = row[self.lat_col]
                corrected_row['lng_old'] = row[self.lng_col]
                # Add correction quality flag
                corrected_row['correction_outlier'] = is_correction_outlier if 'is_correction_outlier' in locals() else False
                
                corrections.append(corrected_row)
                
                if 'is_correction_outlier' in locals() and is_correction_outlier:
                    print(f"({correction_data['corrected_lat']:.3f}, {correction_data['corrected_lng']:.3f}) ⚠️")
                else:
                    print(f"({correction_data['corrected_lat']:.3f}, {correction_data['corrected_lng']:.3f}) ✓")
            else:
                print("NOT FOUND ✗")
        
        return pd.DataFrame(corrections)
    
    def calculate_country_shares(self, corrections_df, original_df):
        """Calculate share of corrected records by country"""
        if len(corrections_df) == 0:
            return corrections_df
        
        print(f"\nCalculating country shares...")
        
        for i, row in corrections_df.iterrows():
            country = row[self.country_col]
            country_data = original_df[original_df[self.country_col] == country]
            
            if self.weight_col and self.weight_col in country_data.columns:
                # Calculate weighted share
                total_weight = country_data[self.weight_col].sum()
                record_weight = row[self.weight_col] if self.weight_col in row else 0
                share_pct = (record_weight / total_weight * 100) if total_weight > 0 else 0
                share_type = f"{self.weight_col}_share"
            else:
                # Calculate count share
                total_count = len(country_data)
                share_pct = (1 / total_count * 100) if total_count > 0 else 0
                share_type = "count_share"
            
            corrections_df.at[i, 'country_share_pct'] = share_pct
            corrections_df.at[i, 'share_type'] = share_type
        
        return corrections_df
    
    def save_corrections(self, corrections_df, input_file_path, sheet_name=None):
        """Save corrections to file with _geocorrected suffix"""
        if len(corrections_df) == 0:
            print("No corrections to save.")
            return None
        
        input_path = Path(input_file_path)
        
        # Create output filename with _geocorrected suffix
        if input_path.suffix.lower() == '.csv':
            output_path = input_path.with_name(f"{input_path.stem}_geocorrected{input_path.suffix}")
            corrections_df.to_csv(output_path, index=False)
        else:
            output_path = input_path.with_name(f"{input_path.stem}_geocorrected{input_path.suffix}")
            sheet_name_out = sheet_name if sheet_name else "corrections"
            corrections_df.to_excel(output_path, sheet_name=sheet_name_out, index=False)
        
        print(f"\nSaved {len(corrections_df)} corrections to: {output_path}")
        return output_path

def main():
    parser = argparse.ArgumentParser(
        description='Clean coordinate outliers from geographic datasets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # WorldCities CSV
  python clean_geographic_data.py --input worldcities.csv --lat-col lat --lng-col lng --country-col iso3 --name-col city
  
  # GEM Excel with sheet
  python clean_geographic_data.py --input gem_data.xlsx --sheet "Global Power Plants" --lat-col Latitude --lng-col Longitude --country-col Country --name-col "Plant Name" --region-col "State/Province"
        """
    )
    
    # Required arguments
    parser.add_argument('--input', required=True, help='Input file path (CSV or Excel)')
    parser.add_argument('--lat-col', required=True, help='Latitude column name')
    parser.add_argument('--lng-col', required=True, help='Longitude column name')
    parser.add_argument('--country-col', required=True, help='Country column name')
    parser.add_argument('--name-col', required=True, help='Location name column')
    
    # Optional arguments
    parser.add_argument('--sheet', help='Excel sheet name (if Excel file)')
    parser.add_argument('--region-col', help='Region/state column name (optional)')
    parser.add_argument('--weight-col', help='Weight column for share calculation (auto-detected if not provided)')
    parser.add_argument('--sigma', type=float, default=4.0, help='Sigma threshold for outlier detection (default: 4.0)')
    parser.add_argument('--rate-limit', type=float, default=1.0, help='Seconds between web lookups (default: 1.0)')
    parser.add_argument('--dry-run', action='store_true', help='Only detect outliers, do not lookup corrections')
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not Path(args.input).exists():
        print(f"Error: Input file '{args.input}' not found")
        sys.exit(1)
    
    # Initialize cleaner
    cleaner = UniversalGeoDataCleaner(
        lat_col=args.lat_col,
        lng_col=args.lng_col,
        country_col=args.country_col,
        name_col=args.name_col,
        region_col=args.region_col,
        weight_col=args.weight_col,
        sigma_threshold=args.sigma,
        rate_limit_delay=args.rate_limit
    )
    
    try:
        # Load data
        print(f"Loading data from {args.input}...")
        if args.sheet:
            print(f"Using sheet: {args.sheet}")
        df = cleaner.load_data(args.input, args.sheet)
        print(f"Loaded {len(df)} records")
        
        # Validate columns
        if not cleaner.validate_columns(df):
            sys.exit(1)
        
        # Detect outliers
        outliers = cleaner.detect_outliers_by_country(df)
        
        if len(outliers) == 0:
            print("\n🎉 No coordinate outliers detected! Dataset appears clean.")
            return
        
        print(f"\n📍 Summary: Found {len(outliers)} coordinate outliers across {outliers[args.country_col].nunique()} countries")
        
        if args.dry_run:
            print("\n--dry-run mode: Skipping coordinate lookup")
            print("\nOutliers found:")
            for _, row in outliers.iterrows():
                print(f"  {row[args.name_col]} ({row[args.country_col]}): "
                      f"({row[args.lat_col]:.3f}, {row[args.lng_col]:.3f}) - "
                      f"dev: lat={row['lat_dev']:.3f}°, lng={row['lng_dev']:.3f}°")
            return
        
        # Process outliers (lookup corrections)
        corrections = cleaner.process_outliers(outliers, df)
        
        # Calculate country shares
        corrections = cleaner.calculate_country_shares(corrections, df)
        
        # Save results
        output_path = cleaner.save_corrections(corrections, args.input, args.sheet)
        
        # Summary
        print(f"\n📊 Results:")
        print(f"  Total corrections: {len(corrections)}")
        
        if len(corrections) > 0:
            # Count by correction quality
            outlier_corrections = corrections[corrections.get('correction_outlier', False) == True]
            good_corrections = corrections[corrections.get('correction_outlier', False) == False]
            
            print(f"  Good corrections: {len(good_corrections)}")
            print(f"  Outlier corrections (⚠️): {len(outlier_corrections)}")
            
            # Share analysis
            if 'country_share_pct' in corrections.columns:
                share_col = corrections['country_share_pct']
                print(f"\n📈 Share Analysis:")
                print(f"  Mean share per record: {share_col.mean():.2f}%")
                print(f"  Median share per record: {share_col.median():.2f}%")
                print(f"  Max share (single record): {share_col.max():.2f}%")
                
                # Flag tiny shares
                tiny_shares = corrections[share_col < 1.0]  # Less than 1%
                if len(tiny_shares) > 0:
                    print(f"  Records with <1% share: {len(tiny_shares)} (consider ignoring)")
                    
                large_shares = corrections[share_col >= 5.0]  # 5% or more
                if len(large_shares) > 0:
                    print(f"  Records with ≥5% share: {len(large_shares)} (high impact)")
            
            print(f"\n✅ Corrected coordinates saved to: {output_path}")
            print("Review the corrections and apply them to your dataset as needed.")
        else:
            print("  No corrections found.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
