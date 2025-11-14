#!/usr/bin/env python3
"""
Complete Synthetic Grid Generation Pipeline Demo
===============================================

This script demonstrates the complete unified pipeline for synthetic grid generation:

1. 🔸 CLUSTERING: Creates demand, generation, and renewable clusters
2. 🔸 GRID MAPPING: Maps substations to clusters and calculates NTC
3. 🔸 VALIDATION VIZ: Shows cluster shapes and substation assignments  
4. 🔸 SYNTHETIC VIZ: Final simplified network visualization

Usage:
    python run_synthetic_grid_pipeline.py IND
    python run_synthetic_grid_pipeline.py DEU --nc 10
"""

import sys
import argparse
from pathlib import Path

# Add syn_grids_1 to path
# sys.path.append(str(Path(__file__).parent / 'syn_grids_1'))

from syn_grids_1.synthetic_grid_clusterer import SyntheticGridClusterer

def main():
    """Run complete synthetic grid generation for demonstration"""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Synthetic Grid Generation Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s IND              # Generate synthetic grid for India with 5 clusters (default)
  %(prog)s DEU --nc 10      # Generate synthetic grid for Germany with 10 clusters
  %(prog)s USA --nc 15      # Generate synthetic grid for USA with 15 clusters
        """
    )
    
    parser.add_argument('iso', type=str,
                       help='ISO3 country code (e.g., IND, DEU, USA)')
    parser.add_argument('--nc', type=int, default=5,
                       help='Number of clusters for demand and generation (default: 5)')
    
    args = parser.parse_args()
    
    # Validate and format ISO code
    country = args.iso.upper()
    n_clusters = args.nc
    
    if len(country) != 3:
        print(f"❌ Error: ISO code must be 3 letters (e.g., IND, DEU, USA), got '{country}'")
        sys.exit(1)
    
    if n_clusters < 1:
        print(f"❌ Error: Number of clusters must be at least 1, got {n_clusters}")
        sys.exit(1)
    
    print("🚀 SYNTHETIC GRID GENERATION DEMO")
    print("=" * 50)
    print("This demo will:")
    print("1. Create energy system clusters")
    print("2. Map real substations to clusters")  
    print("3. Calculate inter-cluster NTC")
    print("4. Generate validation visualizations")
    print("5. Create simplified synthetic network")
    print()
    
    # Configuration
    output_dir = f"1_grids/output_syn_{n_clusters}"  # Output directory includes cluster count
    print(f"🎯 Target country: {country}")
    print(f"🔢 Number of clusters: {n_clusters}")
    print(f"🔍 OSM data source: Auto-detected (Eur-prebuilt → Kanors in-house dataset)")
    print(f"📊 Expected outputs: {output_dir}/{country}/")
    print()
    
    # Create synthetic grid generator
    generator = SyntheticGridClusterer(
        country_code=country,
        output_dir=output_dir,
        # grid_data_dir=grid_data_dir
    )
    
    # Run complete pipeline with user-specified number of clusters
    results = generator.create_complete_synthetic_grid(
        demand_clusters=n_clusters,        # User-specified demand regions
        generation_clusters=n_clusters,    # User-specified generation clusters  
        renewable_clusters=10,             # Renewable zones (ignored for advanced clustering)
        eps_demand=100,                    # 100km DBSCAN radius for demand
        eps_generation=30,                 # 30km DBSCAN radius for generation
        eps_renewable=50,                  # 50km DBSCAN radius for renewables (ignored for advanced clustering)
        grid_data_dir=None,                # Auto-detect OSM data source
        use_advanced_renewable=True        # Use advanced technology-specific clustering
    )
    
    # Check results
    if results.get('success', True):
        print(f"\n🎉 DEMO COMPLETED SUCCESSFULLY!")
        print(f"📂 Check outputs in: {output_dir}/")
        print(f"\n📊 Generated files:")
        
        # List key output files
        output_path = Path(output_dir)
        if output_path.exists():
            csv_files = list(output_path.glob("*.csv"))
            png_files = list(output_path.glob("*.png"))
            json_files = list(output_path.glob("*.json"))
            
            print(f"   📄 CSV files: {len(csv_files)} (cluster data, mappings, NTC)")
            print(f"   🎨 PNG files: {len(png_files)} (visualizations)")
            print(f"   📋 JSON files: {len(json_files)} (summaries)")
            
            print(f"\n🔍 Key files to review:")
            for file in output_path.glob("*validation*.png"):
                print(f"   🎨 {file.name} - Validation visualization")
            for file in output_path.glob("*network*.png"):
                print(f"   🌐 {file.name} - Synthetic grid network")
            for file in output_path.glob("*ntc*.csv"):
                print(f"   ⚡ {file.name} - NTC matrix for modeling")
        
        print(f"\n✨ The synthetic grid is ready for power system modeling!")
        
    else:
        print(f"\n❌ DEMO FAILED")
        print(f"Error: {results.get('error', 'Unknown error')}")
        print(f"\nTroubleshooting:")
        print(f"- Check that OSM data exists for {country} in either:")
        print(f"  * data/OSM-Eur-prebuilt/ (European dataset)")
        print(f"  * data/OSM-kan-prebuilt/ (Kanors in-house dataset)")
        print(f"- Verify country code matches your data")
        print(f"- Check console output for detailed error messages")

if __name__ == "__main__":
    main()
