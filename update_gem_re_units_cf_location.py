#!/usr/bin/env python3
"""
Update GEM Renewable Energy Units - Capacity Factor and Location

This script updates existing renewable energy units in the GEM database with 
capacity factors and grid cell locations from REZoning data enhanced with Atlite weather data.

the date stamped from the output folder will be copied to the GEM folder as re_units_cf_grid_cell_mapping.csv

Author: VerveStacks Team
Date: 2025-08-30
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import sys
from math import radians, cos, sin, asin, sqrt
import warnings

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared_data_loader import get_shared_loader
from excel_manager import ExcelManager

# Load the gem_techmap
shared_loader = get_shared_loader("data/")
df_gem_map = shared_loader.get_vs_mappings_sheet("gem_techmap")


warnings.filterwarnings('ignore')

class GEMUnitsUpdater:
    """
    Updates existing renewable energy units in GEM database with realistic capacity factors
    and grid cell locations from REZoning data enhanced with Atlite weather data.
    """
    
    def __init__(self, data_path="data/", output_path="output/"):
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Data containers
        self.gem_units = None
        self.solar_rezoning = None
        self.onshore_rezoning = None
        self.offshore_rezoning = None
        self.kinesys_mapping = None
        
        # Initialize shared data loader
        self.shared_loader = get_shared_loader(str(self.data_path))
        
        self.logger.info("🔧 GEM Units Updater initialized")
    
    def load_gem_units(self):
        """Load and filter GEM renewable energy units."""
        print("\\n" + "="*60)
        print("STEP 1: LOADING GEM RENEWABLE ENERGY UNITS")
        print("="*60)
        
        # Load GEM data
        gem_path = self.data_path / "existing_stock/Global-Integrated-Power-April-2025.xlsx"
        print(f"📊 Loading GEM data: {gem_path}")
        
        self.gem_units = pd.read_excel(gem_path, sheet_name="Power facilities")
        print(f"   Loaded {len(self.gem_units):,} total GEM units")
        
        # Apply SAME GEM filtering as main processing (verve_stacks_processor.py lines 172, 175-179)
        print("   Applying GEM status filtering (same as main processing)...")
        
        # Step 1: Remove retired units (all types)
        retired_mask = self.gem_units['Status'].str.lower().str.startswith('retired')
        self.gem_units = self.gem_units[~retired_mask]
        
        # Step 2: Remove cancelled/shelved units EXCEPT hydropower
        cancelled_shelved_mask = (
            self.gem_units['Status'].str.lower().str.startswith(('cancelled', 'shelved')) &
            (self.gem_units['Type'].str.lower() != 'hydropower')
        )
        self.gem_units = self.gem_units[~cancelled_shelved_mask]
        
        # Step 3: Filter for renewable units with valid coordinates
        renewable_mask = self.gem_units['Type'].isin(['solar', 'wind'])
        coord_mask = (
            self.gem_units['Latitude'].notna() & 
            self.gem_units['Longitude'].notna() &
            (self.gem_units['Latitude'] != 0) &
            (self.gem_units['Longitude'] != 0)
        )
        
        self.gem_units = self.gem_units[renewable_mask & coord_mask].copy()
        
        print(f"   Filtered to {len(self.gem_units):,} active renewable units with coordinates")
        print(f"   Solar units: {(self.gem_units['Type'] == 'solar').sum():,}")
        print(f"   Wind units: {(self.gem_units['Type'] == 'wind').sum():,}")
        
        # Add ISO codes using existing VerveStacks logic
        self.gem_units['iso_code'] = self.gem_units['Country/area'].apply(self._get_iso_code)
        
        # Count units with successful ISO mapping
        mapped_units = self.gem_units['iso_code'].notna().sum()
        unmapped_units = len(self.gem_units) - mapped_units
        
        print(f"   Successfully mapped {mapped_units:,} units to ISO codes ({mapped_units/len(self.gem_units):.1%})")
        if unmapped_units > 0:
            print(f"   ⚠️  {unmapped_units:,} units could not be mapped to ISO codes")
        
        # Filter out units without ISO mapping for processing
        self.gem_units = self.gem_units[self.gem_units['iso_code'].notna()].copy()
        
        print(f"   Final dataset: {len(self.gem_units):,} units across {self.gem_units['iso_code'].nunique()} countries")
        print(f"   Solar units: {(self.gem_units['Type'] == 'solar').sum():,}")
        print(f"   Wind units: {(self.gem_units['Type'] == 'wind').sum():,}")
        
        print("✅ GEM units loaded and filtered successfully")
    
    def _get_iso_code(self, country_name):
        """Get ISO code for country name using existing VerveStacks logic."""
        if not isinstance(country_name, str):
            return None
        
        # First try kinesys region mapping with aliases
        if self.kinesys_mapping is not None:
            # Check direct country name match
            direct_match = self.kinesys_mapping[
                self.kinesys_mapping['country'].str.lower() == country_name.lower()
            ]
            if not direct_match.empty:
                return direct_match.iloc[0]['iso']
            
            # Check aliases (multiple country name variations)
            for _, row in self.kinesys_mapping.iterrows():
                if pd.notna(row['Alias']):
                    aliases = [alias.strip() for alias in row['Alias'].split('~') if alias.strip()]
                    if country_name.lower() in [alias.lower() for alias in aliases]:
                        return row['iso']
        
        # Fallback to existing VerveStacks logic
        name = country_name.strip().lower()
        special_cases = {
            'kosovo': 'XKX', 'chinese taipei': 'TWN', 'republic of korea': 'KOR',
            'china, hong kong special administrative region': 'HKG',
            'democratic republic of the congo': 'COD', 'russia': 'RUS', 'dr congo': 'COD',
        }
        
        if name in special_cases:
            return special_cases[name]
        
        try:
            import pycountry
            return pycountry.countries.lookup(country_name).alpha_3
        except (LookupError, AttributeError, ImportError):
            return None
    
    def load_rezoning_data(self):
        """Load REZoning data for all renewable technologies."""
        print("\\n" + "="*60)
        print("STEP 2: LOADING REZONING DATA WITH ATLITE CAPACITY FACTORS")
        print("="*60)
        
        # Load kinesys region mapping for country matching
        print("🗺️  Loading kinesys region mapping...")
        self.kinesys_mapping = self.shared_loader.get_vs_mappings_sheet('kinesys_region_map')
        print(f"   Loaded mapping for {len(self.kinesys_mapping)} countries")
        
        # Load solar REZoning data
        solar_path = self.data_path / "REZoning/REZoning_Solar_atlite_cf.csv"
        print(f"☀️  Loading solar REZoning data: {solar_path}")
        solar_raw = pd.read_csv(solar_path)
        print(f"   Loaded {len(solar_raw):,} solar grid cells across {solar_raw['ISO'].nunique()} ISOs")
        
        # Load onshore wind REZoning data
        onshore_path = self.data_path / "REZoning/REZoning_WindOnshore_atlite_cf.csv"
        print(f"🌬️  Loading onshore wind REZoning data: {onshore_path}")
        onshore_raw = pd.read_csv(onshore_path)
        print(f"   Loaded {len(onshore_raw):,} onshore wind grid cells across {onshore_raw['ISO'].nunique()} ISOs")
        
        # Load offshore wind REZoning data
        offshore_path = self.data_path / "REZoning/REZoning_WindOffshore_atlite_cf.csv"
        print(f"🌊 Loading offshore wind REZoning data: {offshore_path}")
        offshore_raw = pd.read_csv(offshore_path)
        print(f"   Loaded {len(offshore_raw):,} offshore wind grid cells across {offshore_raw['ISO'].nunique()} ISOs")
        
        # APPLY SAME FILTERING AS MAIN PROCESSING (re_clustering_1.py lines 235-239, 255, 258, 261)
        print(f"\n📊 Applying capacity factor and capacity quality filtering...")
        
        # Solar: CF ≥ 5% AND capacity > 1 MW (same as re_clustering_1.py lines 235 & 255)
        solar_original = len(solar_raw)
        solar_cf_filtered = solar_raw[solar_raw['Capacity Factor'] >= 0.05]
        self.solar_rezoning = solar_cf_filtered[solar_cf_filtered['Installed Capacity Potential (MW)'] > 1]
        solar_filtered = len(self.solar_rezoning)
        print(f"   ☀️  Solar: {solar_original:,} → {solar_filtered:,} grid cells ({solar_filtered/solar_original:.1%} kept, CF ≥ 5% & capacity > 1 MW)")
        
        # Onshore Wind: CF ≥ 8% AND capacity > 1 MW (same as re_clustering_1.py lines 237 & 258)
        onshore_original = len(onshore_raw)
        onshore_cf_filtered = onshore_raw[onshore_raw['Capacity Factor'] >= 0.08]
        self.onshore_rezoning = onshore_cf_filtered[onshore_cf_filtered['Installed Capacity Potential (MW)'] > 1]
        onshore_filtered = len(self.onshore_rezoning)
        print(f"   🌬️  Onshore Wind: {onshore_original:,} → {onshore_filtered:,} grid cells ({onshore_filtered/onshore_original:.1%} kept, CF ≥ 8% & capacity > 1 MW)")
        
        # Offshore Wind: CF ≥ 20% AND capacity > 1 MW (same as re_clustering_1.py lines 239 & 261)
        offshore_original = len(offshore_raw)
        offshore_cf_filtered = offshore_raw[offshore_raw['Capacity Factor'] >= 0.2]
        self.offshore_rezoning = offshore_cf_filtered[offshore_cf_filtered['Installed Capacity Potential (MW)'] > 1]
        offshore_filtered = len(self.offshore_rezoning)
        print(f"   🌊 Offshore Wind: {offshore_original:,} → {offshore_filtered:,} grid cells ({offshore_filtered/offshore_original:.1%} kept, CF ≥ 20% & capacity > 1 MW)")
        
        print("✅ All REZoning data loaded and filtered for quality")
    
    def calculate_fast_distance(self, lat1, lon1, lat2, lon2):
        """Fast approximate distance calculation (much faster than Haversine)."""
        # Simple Euclidean distance approximation
        # Good enough for finding nearest neighbors, ~10x faster than Haversine
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Rough conversion: 1 degree ≈ 111 km
        # Adjust longitude by latitude to account for Earth's curvature
        lat_avg = radians((lat1 + lat2) / 2)
        dlat_km = dlat * 111.0
        dlon_km = dlon * 111.0 * cos(lat_avg)
        
        # Euclidean distance (faster than sqrt for comparison purposes)
        return sqrt(dlat_km**2 + dlon_km**2)
    
    def find_nearest_grid_cell(self, gem_unit, rezoning_data, grid_prefix="", max_distance_km=1000, accept_threshold_km=1000):
        """
        Find the nearest grid cell for a GEM unit with optimized search and early exit.
        
        Args:
            gem_unit: GEM unit data with coordinates and metadata
            rezoning_data: Pre-filtered REZoning data for the technology
            grid_prefix: Prefix to add to grid cell IDs (e.g., "wof-" for offshore wind)
            max_distance_km: Maximum search distance (default 5000km)
            accept_threshold_km: Distance threshold for accepting matches (default 100km)
        
        Note: rezoning_data is already pre-filtered for quality in load_rezoning_data():
        - Solar: CF ≥ 5% AND capacity > 1 MW (same as re_clustering_1.py lines 235 & 255)
        - Onshore Wind: CF ≥ 8% AND capacity > 1 MW (same as re_clustering_1.py lines 237 & 258)  
        - Offshore Wind: CF ≥ 20% AND capacity > 1 MW (same as re_clustering_1.py lines 239 & 261)
        """
        # Filter by ISO first for performance
        iso_filtered = rezoning_data[rezoning_data['ISO'] == gem_unit['iso_code']].copy()
        
        if len(iso_filtered) == 0:
            # No high-quality grid cells available for this ISO after CF filtering
            return None, None, None
        
        # Detect longitude column name (different datasets use 'lng' or 'long')
        lon_col = 'lng' if 'lng' in iso_filtered.columns else 'long'
        
        # OPTIMIZATION 1: Pre-filter by rough bounding box (±2 degrees ≈ ±220km)
        # This eliminates ~90% of grid cells before distance calculation
        lat_margin = 2.0  # degrees
        lon_margin = 2.0  # degrees
        
        bbox_filtered = iso_filtered[
            (iso_filtered['lat'] >= gem_unit['Latitude'] - lat_margin) &
            (iso_filtered['lat'] <= gem_unit['Latitude'] + lat_margin) &
            (iso_filtered[lon_col] >= gem_unit['Longitude'] - lon_margin) &
            (iso_filtered[lon_col] <= gem_unit['Longitude'] + lon_margin)
        ].copy()
        
        if len(bbox_filtered) == 0:
            # Fallback to full ISO search if bounding box is too restrictive
            bbox_filtered = iso_filtered
        
        # OPTIMIZATION 2: Vectorized distance calculation (much faster than apply)
        gem_lat = gem_unit['Latitude']
        gem_lon = gem_unit['Longitude']
        
        # Vectorized fast distance calculation
        dlat = bbox_filtered['lat'] - gem_lat
        dlon = bbox_filtered[lon_col] - gem_lon
        
        # Rough conversion with latitude adjustment
        lat_avg_rad = np.radians((bbox_filtered['lat'] + gem_lat) / 2)
        dlat_km = dlat * 111.0
        dlon_km = dlon * 111.0 * np.cos(lat_avg_rad)
        
        bbox_filtered['distance_km'] = np.sqrt(dlat_km**2 + dlon_km**2)
        
        # OPTIMIZATION 3: Early exit for very close matches (< 50km)
        very_close = bbox_filtered[bbox_filtered['distance_km'] < 50.0]
        if len(very_close) > 0:
            # Found very close match, use it immediately
            best_close = very_close.loc[very_close['Capacity Factor'].idxmax()] if 'Capacity Factor' in very_close.columns else very_close.iloc[0]
            grid_cell_id = f"{grid_prefix}{best_close['grid_cell']}" if grid_prefix else best_close['grid_cell']
            return grid_cell_id, best_close.get('Capacity Factor', np.nan), best_close['distance_km']
        
        # OPTIMIZATION 4: Filter by maximum reasonable distance
        valid_distances = bbox_filtered[
            (bbox_filtered['distance_km'].notna()) & 
            (bbox_filtered['distance_km'] <= max_distance_km)
        ]
        
        if len(valid_distances) == 0:
            return None, None, None
            
        # Find minimum distance
        min_distance = valid_distances['distance_km'].min()
        
        # OPTIMIZATION 5: Early exit if minimum distance is acceptable
        if min_distance < accept_threshold_km:
            closest_cells = valid_distances[valid_distances['distance_km'] == min_distance]
            
            # Tie-breaking: select cell with highest capacity factor
            if 'Capacity Factor' in closest_cells.columns:
                valid_cf_cells = closest_cells[closest_cells['Capacity Factor'].notna()]
                if len(valid_cf_cells) > 0:
                    best_cell = valid_cf_cells.loc[valid_cf_cells['Capacity Factor'].idxmax()]
                else:
                    best_cell = closest_cells.iloc[0]
            else:
                best_cell = closest_cells.iloc[0]
            
            # Format grid cell ID with prefix if needed
            grid_cell_id = f"{grid_prefix}{best_cell['grid_cell']}" if grid_prefix else best_cell['grid_cell']
            return grid_cell_id, best_cell.get('Capacity Factor', np.nan), min_distance
        
        # If distance is within max_distance_km but beyond accept_threshold_km, 
        # we could optionally return the best available match
        # For now, stick to the acceptance threshold for consistency
        return None, None, None
    
    def run_full_update(self):
        """Execute the complete GEM units update workflow."""
        start_time = datetime.now()
        
        print("🔧" * 20)
        print("GEM RENEWABLE ENERGY UNITS UPDATE - FULL WORKFLOW")
        print("🔧" * 20)
        
        try:
            # Step 1: Load GEM units
            self.load_gem_units()
            
            # Step 2: Load REZoning data
            self.load_rezoning_data()
            
            # Step 3: Process units (spatial matching)
            print("\\n" + "="*60)
            print("STEP 3: PROCESSING GEM UNITS - SPATIAL MATCHING")
            print("="*60)
            
            results = []
            
            # Process each GEM unit
            total_units = len(self.gem_units)
            processed_count = 0
            
            for idx, unit in self.gem_units.iterrows():
                if 'iso_code' not in unit or pd.isna(unit.get('iso_code')):
                    continue  # Skip units without ISO mapping
                
                # Determine technology and REZoning source
                if unit['Type'].lower() == 'solar':
                    rezoning_data = self.solar_rezoning
                    grid_prefix = ""
                    tech_desc = "solar"
                elif pd.notna(unit['Technology']) and 'offshore' in unit['Technology'].lower():
                    rezoning_data = self.offshore_rezoning
                    grid_prefix = "wof-"
                    tech_desc = "offshore wind"
                else:  # Onshore wind (default for wind units)
                    rezoning_data = self.onshore_rezoning
                    grid_prefix = ""
                    tech_desc = "onshore wind"
                
                # Find nearest grid cell
                grid_cell, capacity_factor, distance = self.find_nearest_grid_cell(
                    unit, rezoning_data, grid_prefix
                )
                
                if grid_cell is not None:
                    results.append({
                        'GEM_unit/phase_ID': unit['GEM unit/phase ID'],
                        'capacity_factor': capacity_factor,
                        'grid_cell': grid_cell,
                        'capacity_gw': unit['Capacity (MW)'] / 1000,  # Convert MW to GW
                        'technology': unit['Technology'] if pd.notna(unit['Technology']) else tech_desc
                    })
                
                processed_count += 1
                
                # Progress reporting
                if processed_count % 5000 == 0:
                    progress_pct = (processed_count / total_units) * 100
                    print(f"   Processed {processed_count:,}/{total_units:,} units ({progress_pct:.1f}%) - {len(results):,} matched")
            
            # Save results
            results_df = pd.DataFrame(results)
            
            if len(results_df) > 0:
                # Merge the results with the gem_techmap
                results_df = results_df.merge(
                    df_gem_map[['Technology', 'model_fuel']], 
                    left_on='technology', 
                    right_on='Technology', 
                    how='left'
                )
                results_df = results_df.drop(columns=['Technology'])
            else:
                print(f"\n⚠️  No units were successfully mapped - results DataFrame is empty")
            
            # Create output directory
            self.output_path.mkdir(parents=True, exist_ok=True)
            
            # Save CSV file with timestamp to avoid file locks
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = self.output_path / f"gem_units_cf_location_{timestamp}.csv"
            print(f"\\n💾 Saving results: {csv_path}")
            results_df.to_csv(csv_path, index=False)
            
            # Summary
            duration = datetime.now() - start_time
            print(f"\\n🎉 GEM UNITS UPDATE COMPLETED SUCCESSFULLY")
            print(f"   Successfully matched: {len(results_df):,} units")
            print(f"   Total processing time: {duration}")
            print(f"   Output file: {csv_path}")
            
        except Exception as e:
            print(f"\\n❌ ERROR in GEM units update: {e}")
            raise

def main():
    """Main execution function."""
    print("Starting GEM Renewable Energy Units Update...")
    
    # Initialize updater
    updater = GEMUnitsUpdater()
    
    # Run full update
    updater.run_full_update()

if __name__ == "__main__":
    main()
