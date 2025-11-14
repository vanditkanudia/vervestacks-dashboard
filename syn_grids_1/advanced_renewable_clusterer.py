#!/usr/bin/env python3
"""
Advanced Renewable Energy Clustering for Synthetic Grids
======================================================

Integrates the sophisticated renewable clustering logic from 1_grids/re_clustering
into the synthetic grid pipeline. Creates technology-specific clusters for solar,
wind onshore, and wind offshore with temporal profile analysis.

Author: VerveStacks Team
"""

import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

from syn_grids_1.clustered_buses_utils import get_iso2_from_iso3

# Add 1_grids to path for importing re_clustering functions
sys.path.append(str(Path(__file__).parent.parent / '1_grids'))
sys.path.append(str(Path(__file__).parent.parent / '1_grids' / 're_clustering'))

try:
    from re_clustering.re_clustering_1 import (
        extract_cell_profiles,
        smart_clustering_pipeline,
        visualize_and_export,
        load_and_reshape_atlite,
        prepare_profiles,
        process_grid_infrastructure as re_process_grid_infrastructure
    )
    from extract_country_pypsa_network_clustered import (
        load_atlite_data_for_country,
        load_zones_for_country
    )
    from re_clustering.identify_disconnected_regions import (
        identify_disconnected_regions
    )
    RE_CLUSTERING_AVAILABLE = True
    print("✅ Advanced RE clustering functions imported successfully")
except ImportError as e:
    RE_CLUSTERING_AVAILABLE = False
    print(f"⚠️ Advanced RE clustering not available: {e}")
    print("Falling back to simple renewable clustering")

class AdvancedRenewableClusterer:
    """
    Advanced renewable energy clusterer using 1_grids logic
    
    Creates technology-specific clusters for solar, wind onshore, and wind offshore
    using temporal profile analysis and hierarchical clustering.
    """
    
    def __init__(self, country_code: str, output_dir: str = "syn_grids_1/output"):
        """
        Initialize the advanced renewable clusterer
        
        Args:
            country_code: ISO3 country code (e.g., 'USA', 'IND', 'DEU')
            output_dir: Base directory for output files
        """
        self.country = country_code.upper()
        # Don't add country subdirectory - it's already included in output_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Technology-specific results
        self.solar_results = None
        self.wind_onshore_results = None
        self.wind_offshore_results = None
        
        # Combined results for synthetic grid compatibility
        self.combined_results = None
        
        # Data storage
        self.atlite_data = None
        self.zones_data = None
        self.grid_data = None
        
        # Clustering results from other stages
        self.demand_results = None
        self.generation_results = None
    
    def set_clustering_results(self, demand_results=None, generation_results=None):
        """
        Set demand and generation clustering results for use in renewable clustering
        
        Args:
            demand_results: Demand clustering results
            generation_results: Generation clustering results
        """
        self.demand_results = demand_results
        self.generation_results = generation_results
        
    def load_renewable_data(self, use_adjusted: bool = True) -> bool:
        """
        Load renewable data using 1_grids logic
        
        Args:
            use_adjusted: Whether to use adjusted REZoning data
            
        Returns:
            bool: True if data loaded successfully
        """
        if not RE_CLUSTERING_AVAILABLE:
            print("❌ Advanced RE clustering not available")
            return False
            
        try:
            print(f"\n🌞 LOADING ADVANCED RENEWABLE DATA FOR {self.country}")
            print("-" * 60)
            
            # Get ISO2 code for data loading
            iso2_code = get_iso2_from_iso3(self.country)
            print(f"Using ISO2 code: {iso2_code}")
            
            # Load zones (onshore and offshore)
            print("Loading zone geometries...")
            onshore_zones_gdf = load_zones_for_country(iso2_code, 'onshore')
            mainland_result = identify_disconnected_regions(onshore_zones_gdf, self.country, plot=False)
            mainland_grid_cells = mainland_result['main_continental_grid_cells']
            mainland_bounds = mainland_result['main_bounds']
            if len(mainland_grid_cells) > 0:
                onshore_zones_gdf = onshore_zones_gdf[onshore_zones_gdf['grid_cell'].isin(mainland_grid_cells)]
            
            offshore_zones_gdf = load_zones_for_country(iso2_code, 'offshore')
            
            if onshore_zones_gdf.empty and offshore_zones_gdf.empty:
                print("❌ No zones found for the specified country")
                return False
                
            print(f"  - Loaded {len(onshore_zones_gdf)} onshore zones")
            print(f"  - Loaded {len(offshore_zones_gdf)} offshore zones")
            
            # Combine zones
            self.zones_data = pd.concat([onshore_zones_gdf, offshore_zones_gdf], ignore_index=True)
            print("Preparing zones data for renewable clustering...")
            
            # Add required columns to zones_gdf if they don't exist
            if 'lat' not in self.zones_data.columns or 'lon' not in self.zones_data.columns:
                if 'centroid_lat' in self.zones_data.columns and 'centroid_lon' in self.zones_data.columns:
                    # Use existing centroid coordinates
                    self.zones_data['lat'] = self.zones_data['centroid_lat']
                    self.zones_data['lon'] = self.zones_data['centroid_lon']
                elif hasattr(self.zones_data, 'geometry') and not self.zones_data.geometry.empty:
                    # Calculate centroids from geometry
                    self.zones_data['centroid'] = self.zones_data.geometry.centroid
                    self.zones_data['lon'] = self.zones_data.centroid.x
                    self.zones_data['lat'] = self.zones_data.centroid.y
                else:
                    print("  - Warning: No geometry or coordinate columns found in zones data")
                    # Create dummy coordinates (this shouldn't happen in practice)
                    self.zones_data['lat'] = 0
                    self.zones_data['lon'] = 0
            
            # Load atlite data
            print("Loading atlite renewable data...")
            self.atlite_data = load_atlite_data_for_country(iso2_code, self.country)
            
            if self.atlite_data.empty:
                print("❌ No atlite data found for the specified country")
                return False
                
            print(f"  - Loaded {len(self.atlite_data)} atlite records")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading renewable data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_technology_clusters(self, 
                                 n_solar_clusters: int = None,
                                 n_wind_clusters: int = None, 
                                 n_offshore_clusters: int = None,
                                 data_source: str = 'kan') -> Dict[str, Any]:
        """
        Create technology-specific renewable clusters using 1_grids logic
        
        Args:
            n_solar_clusters: Number of solar clusters (auto-calculated if None)
            n_wind_clusters: Number of wind onshore clusters (auto-calculated if None)
            n_offshore_clusters: Number of wind offshore clusters (auto-calculated if None)
            data_source: Data source for grid infrastructure
            
        Returns:
            Dict containing clustering results for each technology
        """
        if not RE_CLUSTERING_AVAILABLE:
            print("❌ Advanced RE clustering not available")
            return None
            
        try:
            print(f"\n🌞 CREATING TECHNOLOGY-SPECIFIC RENEWABLE CLUSTERS")
            print("=" * 60)
            
            # Get ISO2 code
            iso2_code = get_iso2_from_iso3(self.country)
            
            # Step 1: Reshape atlite data
            print("Step 1: Reshaping atlite data...")
            atlite_reshaped, unique_cells = load_and_reshape_atlite(self.atlite_data, year=2013)
            print(f"  - Reshaped data for {len(unique_cells)} unique cells")
            
            # Step 2: Extract cell profiles for each technology
            print("Step 2: Extracting technology-specific profiles...")
            
            # Create ISO processor for data access
            iso_processor = self._create_iso_processor()
            
            profiles = extract_cell_profiles(atlite_reshaped, self.zones_data, iso_processor)
            
            print(f"  - Solar profiles: {len(profiles['profiles_solar']['cells'])} cells")
            print(f"  - Wind onshore profiles: {len(profiles['profiles_won']['cells'])} cells")
            print(f"  - Wind offshore profiles: {len(profiles['profiles_offwind']['cells'])} cells")
            
            # Step 3: Load grid infrastructure from clustered buses
            print("Step 3: Loading grid infrastructure from clustered buses...")
            components = load_network_components_from_clustered_buses(
                demand_results=self.demand_results,
                generation_results=self.generation_results,
                country_code=self.country
            )
            country_buses = components['buses']
            lines_df = components.get('lines', pd.DataFrame())
            
            buses_processed, transmission_buses = re_process_grid_infrastructure(country_buses, lines_df)
            print(f"  - Processed {len(transmission_buses)} transmission buses")
            
            # Step 4: Create technology-specific clusters
            results = {}
            
            # Solar clustering
            if len(profiles['profiles_solar']['cells']) > 0:
                print(f"\n🌞 SOLAR CLUSTERING")
                print("-" * 30)
                
                solar_clusters, solar_stats, solar_linkage, solar_info, solar_cell_mapping = smart_clustering_pipeline(
                    profiles['profiles_solar'], transmission_buses,
                    iso3_code=self.country,
                    technology='solar',
                    output_dir=str(self.output_dir)
                )
                
                # Create solar visualization
                visualize_and_export(
                    solar_clusters, profiles['profiles_solar'], solar_stats, transmission_buses,
                    self.zones_data, self.country, solar_info, str(self.output_dir), technology='solar'
                )
                
                # Calculate weighted profiles
                solar_weighted_profiles = self._calculate_weighted_profiles(
                    solar_clusters, profiles['profiles_solar'], 'solar'
                )
                
                # Export timeseries
                self._export_technology_timeseries(solar_weighted_profiles, 'solar')
                
                results['solar'] = {
                    'clusters': solar_clusters,
                    'stats': solar_stats,
                    'linkage': solar_linkage,
                    'info': solar_info,
                    'profiles': solar_weighted_profiles,
                    'n_clusters': len(np.unique(solar_clusters)),
                    'cell_mapping': solar_cell_mapping
                }
                
                self.solar_results = results['solar']
                print(f"✅ Solar clustering complete: {results['solar']['n_clusters']} clusters")
            
            # Wind onshore clustering
            if len(profiles['profiles_won']['cells']) > 0:
                print(f"\n💨 WIND ONSHORE CLUSTERING")
                print("-" * 30)
                
                wind_clusters, wind_stats, wind_linkage, wind_info, wind_cell_mapping = smart_clustering_pipeline(
                    profiles['profiles_won'], transmission_buses,
                    iso3_code=self.country,
                    technology='wind_onshore',
                    output_dir=str(self.output_dir)
                )
                
                # Create wind visualization
                visualize_and_export(
                    wind_clusters, profiles['profiles_won'], wind_stats, transmission_buses,
                    self.zones_data, self.country, wind_info, str(self.output_dir), technology='wind_onshore'
                )
                
                # Calculate weighted profiles
                wind_weighted_profiles = self._calculate_weighted_profiles(
                    wind_clusters, profiles['profiles_won'], 'wind_onshore'
                )
                
                # Export timeseries
                self._export_technology_timeseries(wind_weighted_profiles, 'wind_onshore')
                
                results['wind_onshore'] = {
                    'clusters': wind_clusters,
                    'stats': wind_stats,
                    'linkage': wind_linkage,
                    'info': wind_info,
                    'profiles': wind_weighted_profiles,
                    'n_clusters': len(np.unique(wind_clusters)),
                    'cell_mapping': wind_cell_mapping
                }
                
                self.wind_onshore_results = results['wind_onshore']
                print(f"✅ Wind onshore clustering complete: {results['wind_onshore']['n_clusters']} clusters")
            
            # Wind offshore clustering
            if len(profiles['profiles_offwind']['cells']) > 0:
                print(f"\n🌊 WIND OFFSHORE CLUSTERING")
                print("-" * 30)
                
                offshore_clusters, offshore_stats, offshore_linkage, offshore_info, offshore_cell_mapping = smart_clustering_pipeline(
                    profiles['profiles_offwind'], transmission_buses,
                    iso3_code=self.country,
                    technology='wind_offshore',
                    output_dir=str(self.output_dir)
                )
                
                # Create offshore visualization
                visualize_and_export(
                    offshore_clusters, profiles['profiles_offwind'], offshore_stats, transmission_buses,
                    self.zones_data, self.country, offshore_info, str(self.output_dir), technology='wind_offshore'
                )
                
                # Calculate weighted profiles
                offshore_weighted_profiles = self._calculate_weighted_profiles(
                    offshore_clusters, profiles['profiles_offwind'], 'wind_offshore'
                )
                
                # Export timeseries
                self._export_technology_timeseries(offshore_weighted_profiles, 'wind_offshore')
                
                results['wind_offshore'] = {
                    'clusters': offshore_clusters,
                    'stats': offshore_stats,
                    'linkage': offshore_linkage,
                    'info': offshore_info,
                    'profiles': offshore_weighted_profiles,
                    'n_clusters': len(np.unique(offshore_clusters)),
                    'cell_mapping': offshore_cell_mapping
                }
                
                self.wind_offshore_results = results['wind_offshore']
                print(f"✅ Wind offshore clustering complete: {results['wind_offshore']['n_clusters']} clusters")
            
            # Step 5: Create combined results for synthetic grid compatibility
            self.combined_results = self._create_combined_results(results)
            
            # Summary
            total_clusters = sum(r['n_clusters'] for r in results.values())
            print(f"\n🎉 TECHNOLOGY-SPECIFIC CLUSTERING COMPLETE!")
            print("=" * 60)
            for tech, result in results.items():
                print(f"🌞 {tech.replace('_', ' ').title()}: {result['n_clusters']} clusters")
            print(f"📊 Total renewable clusters: {total_clusters}")
            print(f"📂 Output directory: {self.output_dir}")
            
            return self.combined_results
            
        except Exception as e:
            print(f"❌ Technology clustering failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_iso_processor(self):
        """Create a minimal ISO processor for data access"""
        class MinimalISOProcessor:
            def __init__(self, country_code):
                self.country_code = country_code
                # Load REZoning data
                try:
                    from iso_processing_functions import get_rezoning_data
                    rez_data = get_rezoning_data(country_code, use_adjusted=True, technology='all')
                    self.df_solar_rezoning = rez_data['solar']
                    self.df_windon_rezoning = rez_data['wind']
                    self.df_windoff_rezoning = rez_data.get('windoff', pd.DataFrame())
                except Exception as e:
                    print(f"Warning: Could not load REZoning data: {e}")
                    self.df_solar_rezoning = pd.DataFrame()
                    self.df_windon_rezoning = pd.DataFrame()
                    self.df_windoff_rezoning = pd.DataFrame()
        
        return MinimalISOProcessor(self.country)
    
    def _calculate_weighted_profiles(self, clusters, profiles, technology):
        """Calculate weighted cluster profiles"""
        try:
            from extract_country_pypsa_network_clustered import calculate_weighted_cluster_profiles_2
            return calculate_weighted_cluster_profiles_2(clusters, profiles, technology)
        except Exception as e:
            print(f"Warning: Could not calculate weighted profiles: {e}")
            return None
    
    def _export_technology_timeseries(self, weighted_profiles, technology):
        """Export technology timeseries"""
        try:
            from extract_country_pypsa_network_clustered import export_cluster_timeseries
            export_cluster_timeseries(weighted_profiles, technology, self.output_dir)
        except Exception as e:
            print(f"Warning: Could not export timeseries: {e}")
    
    def _create_combined_results(self, results):
        """Create combined results for synthetic grid compatibility"""
        combined = {
            'centers': [],
            'mapping': [],
            'n_clusters': 0,
            'technologies': {}
        }
        
        cluster_id_offset = 0
        
        for tech, result in results.items():
            # Add technology-specific results
            combined['technologies'][tech] = result
            
            # Create centers for synthetic grid
            if 'stats' in result and result['stats'] is not None:
                for _, cluster_stat in result['stats'].iterrows():
                    combined['centers'].append({
                        'cluster_id': int(cluster_stat['cluster_id'] + cluster_id_offset),
                        'cluster_type': 'renewable',
                        'technology': tech,
                        'center_lat': cluster_stat['centroid_lat'],
                        'center_lng': cluster_stat['centroid_lon'],
                        'n_cells': cluster_stat['n_cells'],
                        'total_capacity_mw': cluster_stat.get('total_re_capacity_mw', 0),
                        'avg_distance_to_grid_km': cluster_stat.get('avg_distance_to_grid_km', 0)
                    })
            
            # Update cluster ID offset for next technology
            cluster_id_offset += result['n_clusters']
            combined['n_clusters'] += result['n_clusters']
        
        return combined
    
    
    def export_results(self):
        """Export results in synthetic grid format"""
        if self.combined_results is None:
            print("❌ No results to export")
            return False
        
        try:
            print(f"\n💾 EXPORTING ADVANCED RENEWABLE RESULTS")
            print("-" * 50)
            
            # Export centers
            centers_df = pd.DataFrame(self.combined_results['centers'])
            centers_file = self.output_dir / f"{self.country}_renewable_centers.csv"
            centers_df.to_csv(centers_file, index=False)
            print(f"✅ Exported renewable centers: {centers_file}")
            
            # Export technology-specific summaries
            for tech, result in self.combined_results['technologies'].items():
                if 'stats' in result and result['stats'] is not None:
                    stats_file = self.output_dir / f"{self.country}_{tech}_cluster_stats.csv"
                    result['stats'].to_csv(stats_file, index=False)
                    print(f"✅ Exported {tech} cluster stats: {stats_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error exporting results: {e}")
            return False

    
def load_network_components_from_clustered_buses(demand_results: Optional[Dict] = None,
                                               generation_results: Optional[Dict] = None,
                                               country_code: str = 'synthetic') -> Dict:
    """
    Load network components from clustered buses data instead of OSM data
    
    Args:
        demand_results: Demand clustering results with 'centers' key
        generation_results: Generation clustering results with 'centers' key
        country_code: Country code for identification
        
    Returns:
        Dict with 'buses' and 'lines' DataFrames
    """
    from syn_grids_1.clustered_buses_utils import prepare_clustered_buses_data
    
    print(f"Loading network components from clustered buses for {country_code}")
    
    # Prepare buses DataFrame from clustered data (demand + generation only)
    country_buses = prepare_clustered_buses_data(demand_results, generation_results)
    
    if country_buses.empty:
        print(f"⚠️ No clustered buses found for {country_code}")
        return {'buses': pd.DataFrame(), 'lines': pd.DataFrame()}
    
    print(f"  - Loaded {len(country_buses)} clustered buses")
    
    # For lines, we'll create an empty DataFrame since we don't have line data from clusters
    # The renewable clustering process will handle connectivity differently
    components = {
        'buses': country_buses,
        'lines': pd.DataFrame()  # Empty lines DataFrame
    }
    
    return components


def load_network_components(country_code: str, data_source: str = 'kan', mainland_bounds: dict = None):
    """Load and filter network components for the specified country from the specified data source"""
    print(f"Loading network components for country: {country_code} from {data_source} dataset")
    
    input_files = {}
    input_files['buses'] = f'data/OSM-kan-prebuilt/buses.csv'
    input_files['lines'] = f'data/OSM-kan-prebuilt/lines.csv'
    # Essential columns for lines (used for connectivity analysis and clustering)
    lines_essential_columns = ['bus0', 'bus1', 'length', 'r', 'x', 'g', 'b', 's_nom', 'type','voltage', 'geometry']
    
    components = {}
    
    # Load buses
    try:
        df = pd.read_csv(input_files['buses'])
        if 'country' in df.columns:
            country_buses = df[df['country'] == country_code]
        else:
            country_buses = df[df['bus_id'].astype(str).str.contains(country_code, case=False, na=False)]

        if country_buses.empty:
            # Attempt to hint available countries
            try:
                df = pd.read_csv(input_files['buses'])
                available_countries = df['country'].unique() if 'country' in df.columns else df['bus_id'].astype(str).str[:2].unique()
            except Exception:
                available_countries = []
            raise ValueError(f"No buses found for country '{country_code}' in {data_source} dataset. Available countries: {available_countries}")

        components['buses'] = country_buses
        print(f"  - Loaded {len(country_buses)} buses from {data_source} dataset")

    except Exception as e:
        print(f"  - Error loading buses from {data_source} dataset: {e}")
        components['buses'] = pd.DataFrame()
    
    # Load lines (used for connectivity analysis and later network topology updates)
    try:
        file_path = input_files['lines']
        if Path(file_path).exists():
            # First, check what columns are available
            df_sample = pd.read_csv(file_path, nrows=1)
            available_columns = df_sample.columns.tolist()
            
            # Filter essential columns to only those that exist
            existing_columns = [col for col in lines_essential_columns if col in available_columns]
            
            if len(existing_columns) >= 2:  # Need at least bus0 and bus1
                # Load only existing essential columns
                df_lines = pd.read_csv(file_path, usecols=existing_columns)
                
                # Filter for country-specific lines
                if 'bus0' in df_lines.columns and 'bus1' in df_lines.columns:
                    # Get all bus IDs for this country
                    country_bus_ids = set(country_buses['bus_id'].astype(str))
                    
                    # Filter lines where both buses are in the country
                    df_filtered = df_lines[
                        df_lines['bus0'].astype(str).isin(country_bus_ids) & 
                        df_lines['bus1'].astype(str).isin(country_bus_ids)
                    ]
                    
                    components['lines'] = df_filtered
                    print(f"  - Loaded {len(df_filtered)} lines from {data_source} dataset")
                else:
                    print(f"  - Skipping lines (no bus connection columns)")
                    components['lines'] = pd.DataFrame()
            else:
                print(f"  - Skipping lines (insufficient columns: {existing_columns})")
                components['lines'] = pd.DataFrame()
        else:
            print(f"  - lines.csv not found in {data_source} dataset")
            components['lines'] = pd.DataFrame()
    except Exception as e:
        print(f"  - Error loading lines from {data_source} dataset: {e}")
        components['lines'] = pd.DataFrame()
    
    return components

def main():
    """Example usage of the AdvancedRenewableClusterer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced renewable clustering for synthetic grids')
    parser.add_argument('--country', required=True, help='ISO3 country code')
    parser.add_argument('--output-dir', default='syn_grids_1/output', help='Output directory')
    
    args = parser.parse_args()
    
    # Create clusterer
    clusterer = AdvancedRenewableClusterer(
        country_code=args.country,
        output_dir=args.output_dir
    )
    
    # Load data
    if not clusterer.load_renewable_data():
        print("❌ Failed to load renewable data")
        return
    
    # Create clusters
    results = clusterer.create_technology_clusters()
    
    if results:
        # Export results
        clusterer.export_results()
        print("🎉 Advanced renewable clustering complete!")
    else:
        print("❌ Clustering failed")


if __name__ == "__main__":
    main()
