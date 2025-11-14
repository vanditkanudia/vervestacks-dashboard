#!/usr/bin/env python3
"""
Synthetic Grid Clustering Engine
===============================

Creates demand, generation, and renewable clusters for synthetic grid generation.
Reuses existing VerveStacks clustering logic while providing a unified interface.

Author: VerveStacks Team
"""

import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

# Import existing clustering components
from syn_grids_1.create_regions_simple import PopulationDemandRegionMapper
from syn_grids_1.create_gem_units_clusters import GEMUnitsClusterer
from syn_grids_1.create_renewable_clusters import SimpleRenewableClusterer
from syn_grids_1.advanced_renewable_clusterer import AdvancedRenewableClusterer
from syn_grids_1.voronoi_clustering import VoronoiClusterer
from syn_grids_1.cluster_shapes_validator_4panel import ClusterShapesValidator4Panel

class SyntheticGridClusterer:
    """
    Unified clustering engine for synthetic grid generation.
    
    Orchestrates demand, generation, and renewable clustering while
    preserving the existing clustering algorithms and logic.
    """
    
    def __init__(self, country_code: str, output_dir: str = "syn_grids_1/output"):
        """
        Initialize the synthetic grid clusterer.
        
        Args:
            country_code: ISO3 country code (e.g., 'USA', 'IND', 'DEU')
            output_dir: Base directory for output files (default: syn_grids_1/output)
        """
        self.country = country_code.upper()
        # Create country-specific output directory
        self.output_dir = Path(output_dir) / self.country
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clustering components
        self.demand_mapper = None
        self.gem_clusterer = None
        self.renewable_clusterer = None
        
        # Results storage
        self.demand_results = None
        self.generation_results = None
        self.renewable_results = None
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"🌍 Initializing Synthetic Grid Clusterer for {self.country}")
        print(f"📂 Output directory: {self.output_dir}")
    
    def create_demand_clusters(self, 
                             n_clusters: int = None, 
                             eps_km: float = 100,
                             method: str = 'voronoi') -> Dict[str, Any]:
        """
        Create demand region clusters using existing population clustering logic.
        
        Args:
            n_clusters: Number of demand regions to create
            eps_km: DBSCAN epsilon parameter in kilometers
            method: Clustering method ('voronoi' or 'dbscan')
            
        Returns:
            Dict containing demand clustering results
        """
        print(f"\n🏘️  CREATING DEMAND CLUSTERS")
        print("-" * 50)
        
        # Initialize demand mapper (reusing existing class)
        self.demand_mapper = PopulationDemandRegionMapper(self.country)
        
        try:
            # Load city data using existing method with corrected path
            cities_data = self.demand_mapper.load_city_data('data/country_data/worldcities.csv')
            if cities_data is None or len(cities_data) == 0:
                raise ValueError(f"No city data found for {self.country}")
            
            # Create demand points using existing method
            demand_points = self.demand_mapper.create_demand_points()
            if demand_points is None or len(demand_points) == 0:
                raise ValueError("No demand points created")

            demand_points = self.demand_mapper.filter_demand_points_for_disconnected_regions()
            if demand_points is None or len(demand_points) == 0:
                raise ValueError("No demand points created")
                
            # Apply clustering using existing method
            clusters = self.demand_mapper.cluster_demand_points(
                method=method, 
                n_clusters=n_clusters, 
                eps_km=eps_km
            )
            
            # Calculate cluster centers using existing method
            cluster_centers = self.demand_mapper.calculate_cluster_centers()
            
            # Store results
            self.demand_results = {
                'centers': cluster_centers,
                'points': demand_points,
                'n_clusters': len(cluster_centers) if cluster_centers is not None else 0,
                'method': method,
                'eps_km': eps_km
            }
            
            print(f"✅ Created {self.demand_results['n_clusters']} demand clusters")
            
            # Save results (reusing existing save methods)
            try:
                self._save_demand_results()
            except Exception as e:
                print(f"   ⚠️  Warning: Could not save demand results: {e}")
            
            return self.demand_results
            
        except Exception as e:
            print(f"❌ Demand clustering failed: {e}")
            raise
    
    def create_generation_clusters(self, 
                                 n_clusters: int = None, 
                                 eps_km: float = 30,
                                 method: str = 'voronoi',
                                 min_share: float = 0.01) -> Dict[str, Any]:
        """
        Create generation clusters using existing GEM clustering logic.
        
        Args:
            n_clusters: Number of generation clusters to create
            eps_km: DBSCAN epsilon parameter in kilometers
            method: Clustering method ('voronoi' or 'dbscan')
            min_share: Minimum capacity share threshold
            
        Returns:
            Dict containing generation clustering results
        """
        print(f"\n🏭 CREATING GENERATION CLUSTERS")
        print("-" * 50)
        
        # Initialize GEM clusterer (reusing existing class)
        self.gem_clusterer = GEMUnitsClusterer(self.country)
        
        try:
            # Load GEM data using existing method (with corrected paths)
            gem_data = self.gem_clusterer.load_gem_data('data/existing_stock/Global-Integrated-Power-April-2025.xlsx')
            if gem_data is None or len(gem_data) == 0:
                raise ValueError(f"No GEM power plant data found for {self.country}")
            gem_data = self.gem_clusterer.filter_gem_data_for_disconnected_regions()
            # Filter by minimum share (manual implementation)
            total_capacity = gem_data['capacity_mw'].sum() if 'capacity_mw' in gem_data.columns else 1
            filtered_data = gem_data[gem_data['capacity_mw'] >= (total_capacity * min_share)] if 'capacity_mw' in gem_data.columns else gem_data
            if len(filtered_data) == 0:
                print(f"   ⚠️ No power plants meet minimum share threshold of {min_share}, using all plants")
                filtered_data = gem_data
            
            # Apply clustering using existing method
            clusters = self.gem_clusterer.cluster_gem_units(
                method=method,
                n_clusters=n_clusters,
                eps_km=eps_km
            )
            
            # Store results
            self.generation_results = {
                'centers': self.gem_clusterer.cluster_centers,
                'mapping': self.gem_clusterer.cluster_mapping,
                'n_clusters': len(self.gem_clusterer.cluster_centers) if self.gem_clusterer.cluster_centers is not None else 0,
                'method': method,
                'eps_km': eps_km,
                'min_share': min_share,
                'total_plants': len(filtered_data),
                'total_capacity_mw': filtered_data['capacity_mw'].sum() if 'capacity_mw' in filtered_data.columns else 0
            }
            
            print(f"✅ Created {self.generation_results['n_clusters']} generation clusters")
            print(f"📊 Total plants: {self.generation_results['total_plants']}")
            print(f"⚡ Total capacity: {self.generation_results['total_capacity_mw']:,.0f} MW")
            
            # Save results (reusing existing save methods)
            try:
                self._save_generation_results()
            except Exception as e:
                print(f"   ⚠️  Warning: Could not save generation results: {e}")
            
            return self.generation_results
            
        except Exception as e:
            print(f"❌ Generation clustering failed: {e}")
            raise
    
    def create_renewable_clusters(self, 
                                n_clusters: int = None, 
                                eps_km: float = 50,
                                use_adjusted: bool = True,
                                use_advanced: bool = True) -> Dict[str, Any]:
        """
        Create renewable energy clusters using advanced 1_grids logic or simple clustering.
        
        Args:
            n_clusters: Number of renewable zones to create (ignored for advanced clustering)
            eps_km: DBSCAN epsilon parameter in kilometers (ignored for advanced clustering)
            use_adjusted: Whether to use adjusted REZoning data
            use_advanced: Whether to use advanced technology-specific clustering
            
        Returns:
            Dict containing renewable clustering results
        """
        print(f"\n🌞 CREATING RENEWABLE CLUSTERS")
        print("-" * 50)
        
        try:
            if use_advanced:
                print("🚀 Using ADVANCED technology-specific clustering (1_grids logic)")
                
                # Initialize advanced renewable clusterer
                renewable_clusterer = AdvancedRenewableClusterer(
                    country_code=self.country,
                    output_dir=self.output_dir
                )
                
                # Set demand and generation results for use in renewable clustering
                renewable_clusterer.set_clustering_results(
                    demand_results=self.demand_results,
                    generation_results=self.generation_results
                )
                
                # Load renewable data
                if not renewable_clusterer.load_renewable_data(use_adjusted=use_adjusted):
                    print("❌ Failed to load renewable data")
                    return None
                
                # Create technology-specific clusters
                renewable_results = renewable_clusterer.create_technology_clusters()
                
                if renewable_results:
                    # Export results
                    renewable_clusterer.export_results()
                    
                    # Convert to synthetic grid format
                    synthetic_format = self._convert_advanced_to_synthetic_format(renewable_results)
                    
                    # Store results
                    self.renewable_results = synthetic_format
                    
                    total_clusters = renewable_results['n_clusters']
                    technologies = list(renewable_results['technologies'].keys())
                    print(f"✅ Created {total_clusters} renewable clusters across {len(technologies)} technologies")
                    print(f"   Technologies: {', '.join(technologies)}")
                    
                    # Save results (reusing existing save methods)
                    try:
                        self._save_renewable_results()
                    except Exception as e:
                        print(f"   ⚠️  Warning: Could not save renewable results: {e}")
                    
                    return self.renewable_results
                else:
                    print("❌ Advanced renewable clustering failed")
                    return None
            else:
                print("📊 Using SIMPLE renewable clustering (legacy)")
                
                # Initialize renewable clusterer (reusing existing class)
                self.renewable_clusterer = SimpleRenewableClusterer(self.country)
                
                # Load renewable data using existing method
                renewable_data = self.renewable_clusterer.load_renewable_data(use_adjusted=use_adjusted)
                if renewable_data is None or len(renewable_data) == 0:
                    raise ValueError(f"No renewable data found for {self.country}")
                
                # Apply clustering using existing method
                clusters = self.renewable_clusterer.cluster_renewable_zones(
                    n_clusters=n_clusters,
                    eps_km=eps_km,
                    output_dir=self.output_dir
                )
                
                # Store results
                self.renewable_results = {
                    'centers': self.renewable_clusterer.cluster_centers,
                    'mapping': self.renewable_clusterer.combined_data,
                    'n_clusters': len(self.renewable_clusterer.cluster_centers) if self.renewable_clusterer.cluster_centers is not None else 0,
                    'eps_km': eps_km,
                    'use_adjusted': use_adjusted,
                    'total_grid_cells': len(renewable_data),
                    'total_generation_gwh': renewable_data['total_generation_gwh'].sum(),
                    'solar_generation_gwh': renewable_data['solar_generation_gwh'].sum(),
                    'wind_generation_gwh': renewable_data['wind_generation_gwh'].sum()
                }
                
                print(f"✅ Created {self.renewable_results['n_clusters']} renewable clusters")
                print(f"📊 Total grid cells: {self.renewable_results['total_grid_cells']}")
                print(f"🌞 Total generation: {self.renewable_results['total_generation_gwh']:,.0f} GWh")
                print(f"   ├── Solar: {self.renewable_results['solar_generation_gwh']:,.0f} GWh")
                print(f"   └── Wind: {self.renewable_results['wind_generation_gwh']:,.0f} GWh")
                
                # Save results (reusing existing save methods)
                try:
                    self._save_renewable_results()
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not save renewable results: {e}")
                
                return self.renewable_results
            
        except Exception as e:
            print(f"❌ Renewable clustering failed: {e}")
            raise
    
    def _convert_advanced_to_synthetic_format(self, advanced_results):
        """
        Convert advanced renewable clustering results to synthetic grid format
        
        Args:
            advanced_results: Results from AdvancedRenewableClusterer
            
        Returns:
            Dict in synthetic grid format
        """
        import pandas as pd
        
        try:
            # Create synthetic format structure
            synthetic_format = {
                'centers': [],
                'mapping': [],
                'n_clusters': advanced_results['n_clusters'],
                'technologies': advanced_results['technologies'],
                'use_advanced': True
            }
            
            # Convert centers to synthetic format (centers already have correct offset IDs from _create_combined_results)
            for center in advanced_results['centers']:
                synthetic_format['centers'].append({
                    'cluster_id': center['cluster_id'],
                    'cluster_type': 'renewable',
                    'technology': center['technology'],
                    'center_lat': center['center_lat'],
                    'center_lng': center['center_lng'],
                    'n_cells': center['n_cells'],
                    'total_capacity_mw': center['total_capacity_mw'],
                    'avg_distance_to_grid_km': center['avg_distance_to_grid_km']
                })
            
            # Create mapping data from cell_mapping DataFrames for each technology
            mapping_data = []
            cluster_id_offset = 0
            
            for tech, tech_result in advanced_results['technologies'].items():
                if 'cell_mapping' in tech_result and tech_result['cell_mapping'] is not None:
                    cell_mapping_df = tech_result['cell_mapping']
                    
                    # Add offset to cluster_id to ensure uniqueness across technologies
                    cell_mapping_df = cell_mapping_df.copy()
                    cell_mapping_df['cluster_id'] = (cell_mapping_df['cluster_id'] + cluster_id_offset).astype(int)
                    cell_mapping_df['cluster'] = cell_mapping_df['cluster_id']  # Add 'cluster' column for compatibility
                    cell_mapping_df['cluster_type'] = 'renewable'
                    cell_mapping_df['technology'] = tech
                    
                    # Ensure required columns exist and standardize column names
                    if 'lat' not in cell_mapping_df.columns and 'centroid_lat' in cell_mapping_df.columns:
                        cell_mapping_df['lat'] = cell_mapping_df['centroid_lat']
                    elif 'lat' not in cell_mapping_df.columns:
                        print(f"  - Warning: No 'lat' column found in {tech} cell_mapping. Available columns: {list(cell_mapping_df.columns)}")
                    
                    if 'lng' not in cell_mapping_df.columns:
                        if 'lon' in cell_mapping_df.columns:
                            cell_mapping_df['lng'] = cell_mapping_df['lon']
                        elif 'centroid_lon' in cell_mapping_df.columns:
                            cell_mapping_df['lng'] = cell_mapping_df['centroid_lon']
                        else:
                            print(f"  - Warning: No 'lng' or 'lon' column found in {tech} cell_mapping. Available columns: {list(cell_mapping_df.columns)}")
                    
                    # Convert to list of dictionaries
                    tech_mapping_data = cell_mapping_df.to_dict('records')
                    mapping_data.extend(tech_mapping_data)
                    
                    # Update offset for next technology
                    cluster_id_offset += tech_result['n_clusters']
                    
                    print(f"  - Added {len(tech_mapping_data)} cells for {tech} technology")
                else:
                    print(f"  - Warning: No cell_mapping found for {tech} technology")
            
            # Convert to DataFrame for consistency with synthetic grid format
            synthetic_format['mapping'] = pd.DataFrame(mapping_data) if mapping_data else pd.DataFrame()
            
            print(f"✅ Created renewable mapping with {len(mapping_data)} total cells across all technologies")
            
            return synthetic_format
            
        except Exception as e:
            print(f"❌ Error converting advanced results: {e}")
            return None
    
    def create_all_clusters(self, 
                          demand_clusters: int = None,
                          generation_clusters: int = None, 
                          renewable_clusters: int = None,
                          eps_demand: float = 100,
                          eps_generation: float = 30,
                          eps_renewable: float = 50,
                          use_advanced_renewable: bool = True) -> Dict[str, Any]:
        """
        Create all three types of clusters in sequence.
        
        Args:
            demand_clusters: Number of demand regions
            generation_clusters: Number of generation clusters
            renewable_clusters: Number of renewable zones (ignored for advanced clustering)
            eps_demand: DBSCAN epsilon for demand clustering
            eps_generation: DBSCAN epsilon for generation clustering
            eps_renewable: DBSCAN epsilon for renewable clustering (ignored for advanced clustering)
            use_advanced_renewable: Whether to use advanced technology-specific renewable clustering
            
        Returns:
            Dict containing all clustering results
        """
        print(f"\n🌍 CREATING ALL CLUSTERS FOR {self.country}")
        print("=" * 60)
        
        results = {}
        
        try:
            # Create demand clusters
            results['demand'] = self.create_demand_clusters(
                n_clusters=demand_clusters,
                eps_km=eps_demand
            )
            
            # Create generation clusters
            results['generation'] = self.create_generation_clusters(
                n_clusters=generation_clusters,
                eps_km=eps_generation
            )
            
            # Create renewable clusters
            results['renewable'] = self.create_renewable_clusters(
                n_clusters=renewable_clusters,
                eps_km=eps_renewable,
                use_advanced=use_advanced_renewable
            )
            
            # Summary
            print(f"\n🎉 ALL CLUSTERS CREATED SUCCESSFULLY!")
            print("=" * 60)
            print(f"🏘️  Demand regions: {results['demand']['n_clusters']}")
            print(f"🏭 Generation clusters: {results['generation']['n_clusters']}")
            print(f"🌞 Renewable zones: {results['renewable']['n_clusters']}")
            print(f"📂 Output directory: {self.output_dir}")
            
            return results
            
        except Exception as e:
            print(f"❌ Cluster creation failed: {e}")
            raise
    
    def _save_demand_results(self):
        """Save demand clustering results using existing methods"""
        if self.demand_mapper and self.demand_results:
            # Manual save since PopulationDemandRegionMapper doesn't have save_results method
            if self.demand_results['centers'] is not None:
                centers_df = pd.DataFrame(self.demand_results['centers'])
                centers_file = f"{self.output_dir}/{self.country}_region_centers.csv"
                centers_df.to_csv(centers_file, index=False)
                print(f"   💾 Saved: {centers_file}")
            
            if self.demand_results['points'] is not None:
                points_df = pd.DataFrame(self.demand_results['points'])
                load_share_df = points_df[['cluster', 'scaled_weight']]
                load_share_df = load_share_df.groupby('cluster').sum().reset_index()
                load_share_df['bus_id'] = 'dem' + load_share_df['cluster'].astype(str)
                load_share_df['load_share'] = load_share_df['scaled_weight'] / load_share_df['scaled_weight'].sum()
                load_share_file = f"{self.output_dir}/{self.country}_bus_load_share.csv"
                load_share_df.to_csv(load_share_file, index=False)
                print(f"   💾 Saved: {load_share_file}")
                points_file = f"{self.output_dir}/{self.country}_demand_points.csv"
                points_df.to_csv(points_file, index=False)
                print(f"   💾 Saved: {points_file}")
    
    def _save_generation_results(self):
        """Save generation clustering results using existing methods"""
        if self.gem_clusterer and self.generation_results:
            # Manual save since we need to be sure about the method
            if self.generation_results['centers'] is not None:
                centers_df = pd.DataFrame(self.generation_results['centers'])
                centers_file = f"{self.output_dir}/{self.country}_gem_cluster_centers.csv"
                centers_df.to_csv(centers_file, index=False)
                print(f"   💾 Saved: {centers_file}")
            
            if self.generation_results['mapping'] is not None:
                mapping_df = pd.DataFrame(self.generation_results['mapping'])
                mapping_file = f"{self.output_dir}/{self.country}_gem_cluster_mapping.csv"
                mapping_file2 = os.path.join(self.output_dir, f'{self.country}_power_plants_assigned_to_buses.csv')
                powerplants_map_df = mapping_df[['GEM location ID', 'bus_id']]
                powerplants_map_df = powerplants_map_df.drop_duplicates(subset=['GEM location ID', 'bus_id'])
                powerplants_map_df.to_csv(mapping_file2, index=False)
                mapping_df.to_csv(mapping_file, index=False)
                print(f"   💾 Saved: {mapping_file}")
    
    def _save_renewable_results(self):
        """Save renewable clustering results using existing methods"""
        if self.renewable_clusterer and self.renewable_results:
            # Manual save since we need to be sure about the method
            if self.renewable_results['centers'] is not None:
                centers_df = pd.DataFrame(self.renewable_results['centers'])
                centers_file = f"{self.output_dir}/{self.country}_renewable_cluster_centers.csv"
                centers_df.to_csv(centers_file, index=False)
                print(f"   💾 Saved: {centers_file}")
            
            if self.renewable_results['mapping'] is not None:
                mapping_df = pd.DataFrame(self.renewable_results['mapping'])
                mapping_file = f"{self.output_dir}/{self.country}_renewable_cluster_mapping.csv"
                mapping_df.to_csv(mapping_file, index=False)
                print(f"   💾 Saved: {mapping_file}")
    
    def get_cluster_summary(self) -> Dict[str, Any]:
        """
        Get summary of all created clusters.
        
        Returns:
            Dict containing cluster summary information
        """
        summary = {
            'country': self.country,
            'output_dir': self.output_dir,
            'clusters_created': {}
        }
        
        if self.demand_results:
            summary['clusters_created']['demand'] = {
                'count': self.demand_results['n_clusters'],
                'method': self.demand_results['method']
            }
        
        if self.generation_results:
            summary['clusters_created']['generation'] = {
                'count': self.generation_results['n_clusters'],
                'total_plants': self.generation_results['total_plants'],
                'total_capacity_mw': self.generation_results['total_capacity_mw']
            }
        
        if self.renewable_results:
            summary['clusters_created']['renewable'] = {
                'count': self.renewable_results['n_clusters'],
                'total_generation_gwh': self.renewable_results['total_generation_gwh']
            }
        
        return summary
    
    def create_complete_synthetic_grid(self, 
                                     demand_clusters: int = None,
                                     generation_clusters: int = None, 
                                     renewable_clusters: int = None,
                                     eps_demand: float = 100,
                                     eps_generation: float = 30,
                                     eps_renewable: float = 50,
                                     grid_data_dir: str = None,
                                     use_advanced_renewable: bool = True) -> Dict[str, Any]:
        """
        Create complete synthetic grid pipeline with all steps:
        1. Create clusters (demand, generation, renewable)
        2. Map substations and calculate NTC
        3. Generate validation visualizations
        4. Create synthetic network visualization
        """
        print(f"\n🚀 COMPLETE SYNTHETIC GRID GENERATION")
        print("=" * 60)
        
        try:
            # Step 1: Create all clusters
            print(f"\n📊 STEP 1: Creating Energy System Clusters")
            cluster_results = self.create_all_clusters(
                demand_clusters=demand_clusters,
                generation_clusters=generation_clusters,
                renewable_clusters=renewable_clusters,
                eps_demand=eps_demand,
                eps_generation=eps_generation,
                eps_renewable=eps_renewable,
                use_advanced_renewable=use_advanced_renewable
            )
            
            # Step 2: Initialize substation mapper and calculate NTC
            print(f"\n⚡ STEP 2: Calculating Inter-Cluster NTC")
            from syn_grids_1.substation_grid_mapper import SubstationGridMapper
            
            self.substation_mapper = SubstationGridMapper(
                country_code=self.country,
                output_dir=self.output_dir.parent,  # Pass base directory, SubstationGridMapper will add country subdir
                grid_data_dir=grid_data_dir
            )
            
            # Pass cluster results to the mapper
            self.substation_mapper.demand_results = self.demand_results
            self.substation_mapper.generation_results = self.generation_results
            self.substation_mapper.renewable_results = self.renewable_results
            
            # Load grid infrastructure and calculate NTC
            success = self.substation_mapper.load_grid_infrastructure()
            if not success:
                raise Exception("Failed to load grid infrastructure")
            
            ntc_results = self.substation_mapper.calculate_inter_cluster_ntc()
            
            # Step 2.5: Connect disconnected buses
            print(f"\n🔌 STEP 2.5: Connecting Disconnected Buses")
            self.substation_mapper.connect_disconnected_buses(max_distance_km=1000)
            
            # Step 2.6: Add water crossing detection to new connections
            print(f"\n🌊 STEP 2.6: Adding Water Crossing Detection")
            self.substation_mapper.add_water_detection_to_ntc()
            
            # Step 3: Generate visualizations
            print(f"\n🎨 STEP 3: Generating Visualizations")
            
            # Create 4-panel cluster shapes validator
            validator_4panel = ClusterShapesValidator4Panel(
                country_code=self.country,
                output_dir=self.output_dir.parent,  # Pass base directory, validator will add country subdir
                demand_results=self.demand_results,
                generation_results=self.generation_results,
                renewable_results=self.renewable_results
            )
            
            # Pass NTC matrix to validator for network visualization
            if hasattr(self.substation_mapper, 'ntc_matrix') and self.substation_mapper.ntc_matrix is not None:
                validator_4panel.ntc_matrix = self.substation_mapper.ntc_matrix
            
            # Create 4-panel cluster shapes validation visualization
            shapes_file_4panel = self.output_dir / f"{self.country}_cluster_shapes_4panel.png"
            validator_4panel.visualize_cluster_shapes(shapes_file_4panel)
            
            # Create synthetic grid network visualization
            if hasattr(self.substation_mapper, 'ntc_matrix') and self.substation_mapper.ntc_matrix is not None:
                network_file = self.output_dir / f"{self.country}_synthetic_network.png"
                self._create_synthetic_grid_network_visualization(str(network_file))
            
            # Step 4: Save results
            print(f"\n💾 STEP 4: Saving Results")
            if hasattr(self.substation_mapper, 'save_results'):
                self.substation_mapper.save_results()
            
            # Summary
            print(f"\n🎉 SYNTHETIC GRID GENERATION COMPLETED!")
            print("=" * 60)
            print(f"🏘️  Demand regions: {cluster_results['demand']['n_clusters']}")
            print(f"🏭 Generation clusters: {cluster_results['generation']['n_clusters']}")
            print(f"🌞 Renewable zones: {cluster_results['renewable']['n_clusters']}")
            
            if hasattr(self.substation_mapper, 'ntc_matrix') and self.substation_mapper.ntc_matrix is not None:
                print(f"⚡ Inter-cluster connections: {len(self.substation_mapper.ntc_matrix)}")
                print(f"📊 Total NTC capacity: {self.substation_mapper.ntc_matrix['s_nom'].sum():,.0f} MVA")
            
            print(f"📂 Output directory: {self.output_dir}")
            
            return {
                'success': True,
                'clusters': cluster_results,
                'ntc_matrix': ntc_results,
                'output_dir': self.output_dir
            }
            
        except Exception as e:
            print(f"❌ Synthetic grid generation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_synthetic_grid_network_visualization(self, save_file):
        """Create synthetic grid network visualization showing NTC connections"""
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        from matplotlib.patches import Circle, Polygon
        import numpy as np
        import pandas as pd
        
        if not hasattr(self.substation_mapper, 'ntc_matrix') or self.substation_mapper.ntc_matrix is None:
            print("❌ No NTC matrix available for visualization")
            return
        
        print(f"📊 Creating synthetic grid network visualization...")
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(15, 12))
        
        # Get cluster centers for positioning
        all_clusters = self.substation_mapper._get_all_cluster_centers()
        cluster_positions = {}
        
        for cluster in all_clusters:
            cluster_key = f"{cluster['cluster_type']}{int(cluster['cluster_id'])}"
            cluster_positions[cluster_key] = (cluster['lng'], cluster['lat'])
        
        # Plot cluster centers
        colors = {'demand': 'red', 'generation': 'blue', 'renewable': 'green'}
        sizes = {'demand': 100, 'generation': 150, 'renewable': 120}
        
        for cluster_type, color in colors.items():
            type_clusters = [c for c in all_clusters if c['cluster_type'] == cluster_type]
            if type_clusters:
                lngs = [c['lng'] for c in type_clusters]
                lats = [c['lat'] for c in type_clusters]
                ax.scatter(lngs, lats, c=color, s=sizes[cluster_type], 
                          alpha=0.7, label=f'{cluster_type.capitalize()} Clusters', 
                          edgecolors='black', linewidth=1)
        
        # Plot NTC connections
        ntc_matrix = self.substation_mapper.ntc_matrix
        max_capacity = ntc_matrix['s_nom'].max()
        
        # Count water crossings for legend
        water_crossings = 0
        regular_connections = 0
        
        for _, connection in ntc_matrix.iterrows():
            # Convert cluster IDs to int to avoid float formatting issues (1.0 vs 1)
            # Handle both string and numeric types
            try:
                from_id = int(float(connection['from_cluster_id'])) if pd.notna(connection['from_cluster_id']) else 0
                to_id = int(float(connection['to_cluster_id'])) if pd.notna(connection['to_cluster_id']) else 0
            except (ValueError, TypeError):
                print(f"Warning: Could not convert cluster IDs: {connection['from_cluster_id']}, {connection['to_cluster_id']}")
                continue
            
            from_key = f"{connection['from_cluster_type']}{from_id}"
            to_key = f"{connection['to_cluster_type']}{to_id}"
            
            if from_key in cluster_positions and to_key in cluster_positions:
                from_pos = cluster_positions[from_key]
                to_pos = cluster_positions[to_key]
                
                # Line width based on capacity
                line_width = max(1, (connection['s_nom'] / max_capacity) * 10)
                
                # Check if this connection crosses water
                crosses_water = connection.get('crosses_water', False)
                
                # Color based on connection type
                if connection['from_cluster_type'] == 'renewable':
                    line_color = 'green'
                elif connection['from_cluster_type'] == 'generation':
                    line_color = 'blue'
                else:
                    line_color = 'red'
                
                # Style based on water crossing
                if crosses_water:
                    # Water crossing: dotted line with darker color
                    line_style = '--'
                    line_alpha = 0.8
                    water_crossings += 1
                else:
                    # Regular connection: solid line
                    line_style = '-'
                    line_alpha = 0.6
                    regular_connections += 1
                
                ax.plot([from_pos[0], to_pos[0]], [from_pos[1], to_pos[1]], 
                       color=line_color, linewidth=line_width, alpha=line_alpha,
                       linestyle=line_style)
        
        # Formatting
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_title(f'Synthetic Grid Network - {self.country}\n'
                    f'{len(ntc_matrix)} Inter-Cluster Connections, '
                    f'{ntc_matrix["s_nom"].sum():,.0f} MVA Total\n'
                    f'🌊 {water_crossings} Water Crossings (dotted), '
                    f'🏗️ {regular_connections} Regular Connections (solid)', 
                    fontsize=14, fontweight='bold')
        
        # Create custom legend for line styles
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='red', lw=2, label='Demand Connections'),
            Line2D([0], [0], color='blue', lw=2, label='Generation Connections'),
            Line2D([0], [0], color='green', lw=2, label='Renewable Connections'),
            Line2D([0], [0], color='black', lw=2, linestyle='-', label='Regular Lines'),
            Line2D([0], [0], color='black', lw=2, linestyle='--', label='Water Crossings')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"💾 Synthetic grid network visualization saved: {save_file}")


def main():
    """Example usage of the SyntheticGridClusterer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create clusters for synthetic grid generation')
    parser.add_argument('--country', required=True, help='ISO3 country code')
    parser.add_argument('--demand-clusters', type=int, help='Number of demand clusters')
    parser.add_argument('--generation-clusters', type=int, help='Number of generation clusters')
    parser.add_argument('--renewable-clusters', type=int, help='Number of renewable clusters')
    parser.add_argument('--output-dir', default='output', help='Output directory')
    
    args = parser.parse_args()
    
    # Create clusterer
    clusterer = SyntheticGridClusterer(
        country_code=args.country,
        output_dir=args.output_dir
    )
    
    # Create all clusters
    results = clusterer.create_all_clusters(
        demand_clusters=args.demand_clusters,
        generation_clusters=args.generation_clusters,
        renewable_clusters=args.renewable_clusters
    )
    
    # Print summary
    summary = clusterer.get_cluster_summary()
    print(f"\n📋 CLUSTER SUMMARY:")
    print(f"Country: {summary['country']}")
    for cluster_type, info in summary['clusters_created'].items():
        print(f"{cluster_type.capitalize()}: {info}")


if __name__ == "__main__":
    main()
