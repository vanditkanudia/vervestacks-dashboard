#!/usr/bin/env python3
"""
Atlite Offshore Wind Integration Script
=====================================

PURPOSE:
This script integrates Atlite weather-based offshore wind capacity factors with REZoning 
economic data to create realistic ISO-level offshore wind shapes and enhanced supply curves.

DEDICATED FOCUS:
This script handles ONLY offshore wind processing, applying the proven demand-constrained 
selection methodology from the main atlite integration script.

METHODOLOGY:
Derives ISO-level offshore wind shapes from grid-cell level shapes using demand-constrained
selection to ensure realistic deployment patterns rather than theoretical maximums.

INPUT FILES:
1. atlite_wof_grid_cell_2013.csv - Offshore wind capacity factors by grid cell
2. REZoning_WindOffshore.csv - Economic potential for offshore wind sites
3. EMBER yearly data - For demand anchoring

OUTPUT FILES:
1. REZoning_WindOffshore_atlite_cf.csv - Enhanced offshore REZoning with Atlite CFs
2. atlite_wof_iso_2013.csv - ISO-level offshore wind shapes (8760 hours)

AUTHOR: VerveStacks Team
DATE: 30 August 2025

METHODOLOGICAL INNOVATION SUMMARY:
=====================================

PROBLEM ADDRESSED:
- Offshore wind sites often have different capacity factor patterns than onshore
- Need for realistic offshore wind deployment considering economic constraints
- Integration of weather-based capacity factors with economic potential data

SOLUTION APPROACH:
1. DEMAND-CONSTRAINED SELECTION: Use actual electricity generation targets
2. ECONOMIC RATIONALITY: Sort offshore sites by LCOE (cheapest first)
3. WEATHER REALISM: Apply Atlite-derived capacity factors to economic data
4. SPATIAL AGGREGATION: Create ISO-level profiles from grid-cell data

INNOVATION:
Rather than using theoretical maximum offshore potential, this approach selects
the most economically attractive offshore sites up to realistic deployment targets,
ensuring the resulting ISO-level profiles reflect actual deployment economics.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import sys
import warnings

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

warnings.filterwarnings('ignore')

class AtliteOffshoreWindIntegrator:
    """
    Integrates Atlite offshore wind capacity factors with REZoning economic data
    to create realistic ISO-level offshore wind energy shapes.
    
    This class applies the demand-constrained selection methodology specifically
    to offshore wind resources, ensuring economic rationality in deployment patterns.
    """
    
    def __init__(self, data_path="../../data/", output_path="../../data/"):
        """
        Initialize the offshore wind integrator.
        
        Args:
            data_path (str): Path to input data directory
            output_path (str): Path to output data directory
        """
        self.data_path = Path(data_path)
        self.output_path = Path(output_path)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Data containers
        self.atlite_offshore_data = None
        self.rezoning_offshore = None
        self.ember_generation = None
        
        self.logger.info("🌊 Atlite Offshore Wind Integrator initialized")
    
    def validate_input_files(self):
        """Validate that all required input files exist."""
        required_files = [
            "hourly_profiles/atlite_wof_grid_cell_2013.csv",
            "REZoning/REZoning_WindOffshore.csv",
            "ember/yearly_full_release_long_format.csv"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.data_path / file_path
            if not full_path.exists():
                missing_files.append(str(full_path))
        
        if missing_files:
            raise FileNotFoundError(f"Missing required data files:\n" + "\n".join(missing_files))
        
        print("✅ All required offshore wind data files found")
    
    def load_offshore_data(self):
        """
        STEP 0: Load all offshore wind source data files
        
        This step loads the three critical datasets:
        - Atlite: Weather-based hourly offshore wind capacity factors by grid cell
        - EMBER: Actual 2022 electricity generation by country (for demand anchoring)
        - REZoning Offshore: Economic potential and costs by offshore grid cell
        """
        print("\n" + "="*60)
        print("STEP 0: LOADING OFFSHORE WIND SOURCE DATA")
        print("="*60)
        
        # Load Atlite offshore wind hourly capacity factors
        atlite_path = self.data_path / "hourly_profiles/atlite_wof_grid_cell_2013.csv"
        print(f"🌊 Loading Atlite offshore wind data: {atlite_path}")
        self.atlite_offshore_data = pd.read_csv(atlite_path)
        print(f"   Loaded {len(self.atlite_offshore_data):,} rows covering {self.atlite_offshore_data['grid_cell'].nunique()} offshore grid cells")

        # remove wof- from the grid_cell column
        # self.atlite_offshore_data['grid_cell'] = self.atlite_offshore_data['grid_cell'].str.replace('wof-', '')
        # print(f"   Available ISOs: {sorted(self.atlite_offshore_data['grid_cell'].str[:3].unique())}")
        

        # Load EMBER generation data for demand anchoring
        ember_path = self.data_path / "ember/yearly_full_release_long_format.csv"
        print(f"📊 Loading EMBER generation data: {ember_path}")
        ember_raw = pd.read_csv(ember_path)
        
        # Filter for 2022 total generation only
        self.ember_generation = ember_raw[
            (ember_raw['Year'] == 2022) & 
            (ember_raw['Variable'] == 'Total Generation')
        ][['Country code', 'Value']].copy()
        self.ember_generation.columns = ['iso', 'total_generation_twh']
        print(f"   Loaded 2022 generation data for {len(self.ember_generation)} countries")
        
        # Load REZoning offshore wind potential
        offshore_path = self.data_path / "REZoning/REZoning_WindOffshore.csv"
        print(f"🌊 Loading REZoning offshore wind data: {offshore_path}")
        self.rezoning_offshore = pd.read_csv(offshore_path)
        print(f"   Loaded {len(self.rezoning_offshore):,} offshore wind grid cells across {self.rezoning_offshore['ISO'].nunique()} ISOs")
        
        print("✅ All offshore wind source data loaded successfully")
    
    def enhance_offshore_with_atlite(self):
        """
        STEP 1: Add Atlite offshore wind capacity factors to REZoning data
        
        This step performs a LEFT JOIN to add weather-realistic capacity factors
        to the REZoning offshore economic data, creating enhanced supply curves.
        
        CRITICAL: Uses LEFT JOIN to preserve all REZoning offshore grid cells, 
        falling back to original capacity factors where Atlite data is not available.
        """
        print("\n" + "="*60)
        print("STEP 1: ENHANCING OFFSHORE REZONING DATA WITH ATLITE CAPACITY FACTORS")
        print("="*60)
        
        # Get average offshore wind capacity factors by grid cell from Atlite
        print("🌊 Calculating average offshore wind capacity factors by grid cell from Atlite data...")
        atlite_avg_cf = self.atlite_offshore_data.groupby('grid_cell').agg({
            'wind_capacity_factor': 'mean'
        }).reset_index()
        atlite_avg_cf.columns = ['grid_cell', 'cf_atlite_offshore_wind']
        
        print(f"   Calculated averages for {len(atlite_avg_cf)} offshore grid cells")
        
        # Enhance offshore wind REZoning data
        print("🌊 Enhancing REZoning offshore wind data...")
        original_offshore_count = len(self.rezoning_offshore)
        
        # LEFT JOIN to preserve all REZoning offshore data
        self.rezoning_offshore = self.rezoning_offshore.merge(
            atlite_avg_cf, 
            left_on='grid_cell', 
            right_on='grid_cell', 
            how='left'
        )
        
        # Check join results
        enhanced_count = self.rezoning_offshore['cf_atlite_offshore_wind'].notna().sum()
        print(f"   Enhanced {enhanced_count:,} of {original_offshore_count:,} offshore grid cells ({enhanced_count/original_offshore_count:.1%})")
        
        # Store original Capacity Factor values before updating
        self.rezoning_offshore['cf_old'] = self.rezoning_offshore['Capacity Factor'].copy()
        
        # Update Capacity Factor with Atlite data (fallback to original if Atlite not available)
        self.rezoning_offshore['Capacity Factor'] = self.rezoning_offshore['cf_atlite_offshore_wind'].fillna(
            self.rezoning_offshore['Capacity Factor']
        )
        
        print("✅ REZoning offshore wind data enhancement completed")
    
    def calculate_offshore_iso_shapes(self):
        """
        STEPS 2-4: Calculate realistic ISO-level offshore wind energy shapes
        
        This is the core innovation: rather than using theoretical maximum offshore potential,
        we select the most economically attractive offshore sites up to realistic targets,
        ensuring the resulting ISO-level profiles reflect actual deployment economics.
        """
        print("\n" + "="*60)
        print("STEP 2-4: CALCULATING ISO-LEVEL OFFSHORE WIND SHAPES")
        print("="*60)
        
        # Get list of ISOs with both offshore potential and generation data
        offshore_isos = set(self.atlite_offshore_data['grid_cell'].str[4:7].unique())
        generation_isos = set(self.ember_generation['iso'].unique())
        target_isos = offshore_isos.intersection(generation_isos)
        
        print(f"🎯 Processing {len(target_isos)} ISOs with both offshore potential and generation data")
        print(f"   Target ISOs: {sorted(target_isos)}")
        
        # Container for all ISO shapes
        all_iso_shapes = []
        
        for iso in sorted(target_isos):
            print(f"\n🌊 Processing offshore wind shapes for {iso}...")
            
            # Get ISO generation target
            iso_generation = self.ember_generation[self.ember_generation['iso'] == iso]['total_generation_twh'].iloc[0]
            offshore_target_twh = iso_generation
            offshore_target_gwh = offshore_target_twh * 1000
            
            print(f"   Total generation: {iso_generation:.1f} TWh")
            print(f"   Offshore wind target: {offshore_target_gwh:.1f} GWh ({offshore_target_twh:.2f} TWh)")
            
            # Process offshore wind shapes
            offshore_shape = self._calculate_offshore_technology_shape(
                iso, 'offshore_wind', offshore_target_gwh, 
                self.rezoning_offshore, 'Capacity Factor'
            )
            
            if offshore_shape is not None:
                all_iso_shapes.append(offshore_shape)
                print(f"   ✅ Generated offshore wind shape for {iso}")
            else:
                print(f"   ⚠️  No offshore wind shape generated for {iso}")
        
        # Combine all ISO shapes
        if all_iso_shapes:
            self.iso_shapes = pd.concat(all_iso_shapes, ignore_index=True)
            print(f"\n✅ Generated offshore wind shapes for {len(all_iso_shapes)} ISOs")
            print(f"   Total records: {len(self.iso_shapes):,}")
        else:
            print("\n⚠️  No offshore wind shapes generated")
            self.iso_shapes = pd.DataFrame()
    
    def _calculate_offshore_technology_shape(self, iso, tech_type, target_generation_gwh, rezoning_data, cf_column):
        """
        Calculate technology-specific shape using demand-constrained selection.
        
        This method implements the core innovation: selecting grid cells based on
        economic attractiveness (LCOE) up to the target generation level.
        """
        # Filter data for this ISO
        iso_data = rezoning_data[rezoning_data['ISO'] == iso].copy()
        
        if len(iso_data) == 0:
            print(f"     No {tech_type} data for {iso}")
            return None
        
        # Calculate generation potential for each grid cell (GWh/year)
        iso_data['generation_potential_gwh'] = (
            iso_data['Installed Capacity Potential (MW)'] * iso_data[cf_column] * 8760 * 1e-3
        )
        
        # Sort by LCOE (cheapest first) for economic rationality
        iso_data = iso_data.sort_values('LCOE (USD/MWh)')
        
        # Select grid cells up to target generation (demand-constrained selection)
        cumulative_generation = iso_data['generation_potential_gwh'].cumsum()
        selected_cells = iso_data[cumulative_generation <= target_generation_gwh]
        
        if len(selected_cells) == 0:
            print(f"     No economically viable {tech_type} cells for {iso}")
            return None
        
        selected_generation = selected_cells['generation_potential_gwh'].sum()
        print(f"     Selected {len(selected_cells)} {tech_type} cells: {selected_generation:.1f} GWh")
        
        # Get hourly shapes for selected cells
        selected_grid_cells = selected_cells['grid_cell'].tolist()
        
        # Filter Atlite data for selected cells
        cell_shapes = self.atlite_offshore_data[
            self.atlite_offshore_data['grid_cell'].isin(selected_grid_cells)
        ].copy()
        
        if len(cell_shapes) == 0:
            print(f"     No Atlite shape data for selected {tech_type} cells in {iso}")
            return None
        
        # Weight by generation potential for aggregation
        cell_shapes = cell_shapes.merge(
            selected_cells[['grid_cell', 'generation_potential_gwh']], 
            left_on='grid_cell', 
            right_on='grid_cell'
        )
        
        # Calculate weighted average hourly capacity factors
        cell_shapes['weighted_cf'] = (
            cell_shapes['wind_capacity_factor'] * cell_shapes['generation_potential_gwh']
        )
        
        # Group by hour and calculate weighted average
        hourly_shape = cell_shapes.groupby(['month', 'day', 'hour']).agg({
            'weighted_cf': 'sum',
            'generation_potential_gwh': 'sum'
        }).reset_index()
        
        hourly_shape['wind_capacity_factor'] = (
            hourly_shape['weighted_cf'] / hourly_shape['generation_potential_gwh']
        )
        
        # Calculate com_fr_wind as hourly fraction of the year (normalized to sum to 1.0)
        total_cf = hourly_shape['wind_capacity_factor'].sum()
        hourly_shape['com_fr_wind'] = hourly_shape['wind_capacity_factor'] / total_cf

        # Add ISO identifier
        hourly_shape['iso'] = iso
        
        return hourly_shape[['iso', 'month', 'day', 'hour', 'com_fr_wind', 'wind_capacity_factor']]
    
    def generate_offshore_outputs(self):
        """
        STEP 5: Generate final output files
        
        Creates the two key output files:
        1. REZoning_WindOffshore_atlite_cf.csv - Enhanced offshore REZoning data
        2. atlite_wof_iso_2013.csv - ISO-level offshore wind shapes
        """
        print("\n" + "="*60)
        print("STEP 5: GENERATING OFFSHORE WIND OUTPUT FILES")
        print("="*60)
        
        # Create output directories
        rezoning_output_dir = self.output_path / "REZoning"
        profiles_output_dir = self.output_path / "hourly_profiles"
        
        rezoning_output_dir.mkdir(parents=True, exist_ok=True)
        profiles_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Save enhanced REZoning offshore data
        rezoning_output_path = rezoning_output_dir / "REZoning_WindOffshore_atlite_cf.csv"
        print(f"💾 Saving enhanced REZoning offshore data: {rezoning_output_path}")
        self.rezoning_offshore.to_csv(rezoning_output_path, index=False)
        print(f"   Saved {len(self.rezoning_offshore):,} offshore grid cells")
        
        # 2. Save ISO-level offshore wind shapes
        if not self.iso_shapes.empty:
            shapes_output_path = profiles_output_dir / "atlite_wof_iso_2013.csv"
            print(f"💾 Saving ISO-level offshore wind shapes: {shapes_output_path}")
            self.iso_shapes.to_csv(shapes_output_path, index=False)
            print(f"   Saved {len(self.iso_shapes):,} hourly records for {self.iso_shapes['iso'].nunique()} ISOs")
        else:
            print("⚠️  No ISO shapes to save")
        
        # Summary statistics
        print(f"\n📊 OFFSHORE WIND INTEGRATION SUMMARY:")
        print(f"   Enhanced offshore grid cells: {len(self.rezoning_offshore):,}")
        if hasattr(self, 'iso_shapes') and not self.iso_shapes.empty:
            print(f"   Generated shapes for ISOs: {self.iso_shapes['iso'].nunique()}")
            print(f"   Total hourly records: {len(self.iso_shapes):,}")
        
        # REZoning enhancement summary - compare updated Capacity Factor with original cf_old
        offshore_enhanced = (self.rezoning_offshore['Capacity Factor'] != self.rezoning_offshore['cf_old']).sum()
        print(f"   Offshore cells with Atlite enhancement: {offshore_enhanced:,}")
        
        print("✅ All offshore wind output files generated successfully")
    
    def run_full_offshore_integration(self):
        """
        Execute the complete offshore wind integration workflow.
        
        This method orchestrates all steps of the offshore wind integration process,
        from data loading through final output generation.
        """
        start_time = datetime.now()
        
        print("🌊" * 20)
        print("ATLITE OFFSHORE WIND INTEGRATION - FULL WORKFLOW")
        print("🌊" * 20)
        
        try:
            # Step 0: Validate and load data
            self.validate_input_files()
            self.load_offshore_data()
            
            # Step 1: Enhance REZoning with Atlite
            self.enhance_offshore_with_atlite()
            
            # Steps 2-4: Calculate ISO shapes
            self.calculate_offshore_iso_shapes()
            
            # Step 5: Generate outputs
            self.generate_offshore_outputs()
            
            # Final summary
            duration = datetime.now() - start_time
            print(f"\n🎉 OFFSHORE WIND INTEGRATION COMPLETED SUCCESSFULLY")
            print(f"   Total processing time: {duration}")
            print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"\n❌ ERROR in offshore wind integration: {e}")
            raise

def main():
    """Main execution function."""
    print("Starting Atlite Offshore Wind Integration...")
    
    # Initialize integrator
    integrator = AtliteOffshoreWindIntegrator()
    
    # Run full integration
    integrator.run_full_offshore_integration()

if __name__ == "__main__":
    main()
