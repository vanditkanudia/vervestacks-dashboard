#!/usr/bin/env python3
"""
Voronoi-Based Clustering
========================

Creates non-overlapping clusters using Voronoi diagrams for demand and GEM data.
Guarantees that cluster regions never overlap by construction.

Usage:
    python voronoi_clustering.py --country USA --type demand --clusters 10 --output-dir output/USA_d10g10r10
"""

import pandas as pd
import numpy as np
from scipy.spatial import Voronoi, voronoi_plot_2d
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import argparse
import os
from pathlib import Path

class VoronoiClusterer:
    """Create non-overlapping clusters using Voronoi diagrams"""
    
    def __init__(self, country_code):
        self.country = country_code
        self.data_points = None
        self.cluster_centers = None
        self.voronoi = None
        
    def load_data(self, data_type, output_dir):
        """Load demand or GEM data"""
        base_path = Path(output_dir)
        
        if data_type == 'demand':
            # Load city/demand data
            cities_file = '../data/country_data/worldcities.csv'
            if os.path.exists(cities_file):
                df = pd.read_csv(cities_file)
                
                # Filter for country and significant cities
                country_filter = (df['iso3'] == self.country) & (df['population'] > 50000)
                
                if country_filter.sum() == 0:
                    print(f"No large cities found for {self.country}, trying smaller threshold...")
                    country_filter = (df['iso3'] == self.country) & (df['population'] > 10000)
                
                if country_filter.sum() == 0:
                    print(f"Still no cities found for {self.country}, using all cities...")
                    country_filter = df['iso3'] == self.country
                
                self.data_points = df[country_filter].copy()
                self.data_points['weight'] = self.data_points['population'] / 1000  # Convert to thousands
                
                print(f"Loaded {len(self.data_points)} cities for {self.country}")
                
        elif data_type == 'gem':
            # Load GEM data from existing cluster mapping
            gem_mapping_file = Path(output_dir) / f'{self.country}_gem_cluster_mapping.csv'
            
            if gem_mapping_file.exists():
                gem_data = pd.read_csv(gem_mapping_file)
                
                # Filter for significant facilities (>= 50 MW)
                if 'total_capacity_mw' in gem_data.columns:
                    gem_data = gem_data[gem_data['total_capacity_mw'] >= 50]
                    capacity_col = 'total_capacity_mw'
                elif 'capacity_mw' in gem_data.columns:
                    gem_data = gem_data[gem_data['capacity_mw'] >= 50]
                    capacity_col = 'capacity_mw'
                else:
                    print("No capacity column found in GEM data")
                    return False
                
                self.data_points = gem_data[['lat', 'lng', capacity_col]].copy()
                self.data_points['weight'] = gem_data[capacity_col]
                
                print(f"Loaded {len(self.data_points)} GEM facilities for {self.country}")
            else:
                print(f"GEM mapping file not found: {gem_mapping_file}")
                return False
        
        return True
    
    def create_voronoi_clusters(self, n_clusters):
        """Create Voronoi-based clusters"""
        if self.data_points is None or len(self.data_points) == 0:
            print("No data points available for clustering")
            return None
        
        print(f"Creating {n_clusters} Voronoi clusters from {len(self.data_points)} points...")
        
        # Step 1: Use K-means to find optimal cluster centers
        coords = self.data_points[['lng', 'lat']].values
        
        # Weight the clustering by importance (population or capacity)
        weights = self.data_points['weight'].values
        
        # Use weighted K-means approach
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        
        # Create weighted coordinates by repeating points based on weight
        weighted_coords = []
        for i, (coord, weight) in enumerate(zip(coords, weights)):
            # Repeat each point proportional to its weight (capped for performance)
            repeat_count = max(1, min(int(weight / weights.mean()), 10))
            for _ in range(repeat_count):
                weighted_coords.append(coord)
        
        weighted_coords = np.array(weighted_coords)
        
        # Fit K-means on weighted coordinates
        kmeans.fit(weighted_coords)
        self.cluster_centers = kmeans.cluster_centers_
        
        print(f"Found {len(self.cluster_centers)} cluster centers")
        
        # Step 2: Create Voronoi diagram from cluster centers
        self.voronoi = Voronoi(self.cluster_centers)
        
        # Step 3: Assign each data point to nearest Voronoi center
        distances = cdist(coords, self.cluster_centers)
        cluster_assignments = np.argmin(distances, axis=1)
        
        self.data_points['cluster'] = cluster_assignments
        
        print(f"Assigned points to Voronoi clusters")
        
        return self.data_points
    
    def calculate_cluster_statistics(self, data_type):
        """Calculate statistics for each Voronoi cluster"""
        if self.data_points is None:
            return None
        
        cluster_stats = []
        
        for cluster_id in range(len(self.cluster_centers)):
            cluster_points = self.data_points[self.data_points['cluster'] == cluster_id]
            
            if len(cluster_points) == 0:
                continue
            
            # Calculate weighted centroid (should be close to Voronoi center)
            total_weight = cluster_points['weight'].sum()
            
            if data_type == 'demand':
                # Population-weighted centroid
                weighted_lat = (cluster_points['lat'] * cluster_points['weight']).sum() / total_weight
                weighted_lng = (cluster_points['lng'] * cluster_points['weight']).sum() / total_weight
                
                # Find largest city in cluster
                largest_city_idx = cluster_points['weight'].idxmax()
                largest_city = cluster_points.loc[largest_city_idx, 'city']
                
                cluster_stats.append({
                    'cluster_id': int(cluster_id),
                    'name': f"{largest_city}_region",
                    'center_lat': weighted_lat,
                    'center_lng': weighted_lng,
                    'voronoi_center_lat': self.cluster_centers[cluster_id][1],
                    'voronoi_center_lng': self.cluster_centers[cluster_id][0],
                    'total_demand': total_weight,
                    'population_demand': total_weight,
                    'industrial_demand': 0.0,
                    'demand_share': 0,  # Will calculate after
                    'n_cities': len(cluster_points),
                    'n_industrial': 0,
                    'major_city': largest_city,
                    'major_industries': 'None (population-only mode)'
                })
                
            elif data_type == 'gem':
                # Capacity-weighted centroid
                weighted_lat = (cluster_points['lat'] * cluster_points['weight']).sum() / total_weight
                weighted_lng = (cluster_points['lng'] * cluster_points['weight']).sum() / total_weight
                
                cluster_stats.append({
                    'cluster_id': int(cluster_id),
                    'name': f"GEN_Voronoi_{cluster_id}",
                    'center_lat': weighted_lat,
                    'center_lng': weighted_lng,
                    'voronoi_center_lat': self.cluster_centers[cluster_id][1],
                    'voronoi_center_lng': self.cluster_centers[cluster_id][0],
                    'total_capacity_mw': total_weight,
                    'capacity_share': 0,  # Will calculate after
                    'n_plants': len(cluster_points),
                    'avg_plant_size_mw': total_weight / len(cluster_points),
                    'largest_plant_mw': cluster_points['weight'].max()
                })
        
        cluster_df = pd.DataFrame(cluster_stats)
        
        # Calculate shares
        if data_type == 'demand':
            total_demand = cluster_df['total_demand'].sum()
            cluster_df['demand_share'] = cluster_df['total_demand'] / total_demand
        elif data_type == 'gem':
            total_capacity = cluster_df['total_capacity_mw'].sum()
            cluster_df['capacity_share'] = cluster_df['total_capacity_mw'] / total_capacity
        
        return cluster_df
    
    def export_results(self, data_type, output_dir):
        """Export Voronoi clustering results"""
        if self.data_points is None:
            return
        
        base_path = Path(output_dir)
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Export cluster centers
        cluster_stats = self.calculate_cluster_statistics(data_type)
        if cluster_stats is not None:
            if data_type == 'demand':
                centers_file = base_path / f'{self.country}_region_centers.csv'
                points_file = base_path / f'{self.country}_demand_points.csv'
                
                # Prepare demand points export
                export_points = self.data_points.copy()
                export_points = export_points.rename(columns={
                    'city': 'name',
                    'weight': 'scaled_weight'
                })
                export_points['type'] = 'population'
                export_points['raw_weight'] = export_points['scaled_weight']
                export_points['subtype'] = 'city'
                
            elif data_type == 'gem':
                centers_file = base_path / f'{self.country}_gem_cluster_centers.csv'
                points_file = base_path / f'{self.country}_gem_cluster_mapping.csv'
                
                # Prepare GEM points export
                export_points = self.data_points.copy()
                export_points = export_points.rename(columns={
                    'weight': 'total_capacity_mw'
                })
                export_points['cluster_id'] = export_points['cluster']
            
            # Save files
            cluster_stats.to_csv(centers_file, index=False)
            export_points.to_csv(points_file, index=False)
            
            print(f"Exported {data_type} Voronoi clusters:")
            print(f"  Centers: {centers_file}")
            print(f"  Points: {points_file}")
            
            # Print summary
            print(f"\n=== {data_type.upper()} VORONOI CLUSTERS SUMMARY ===")
            print(f"Total clusters: {len(cluster_stats)}")
            if data_type == 'demand':
                print(f"Total demand: {cluster_stats['total_demand'].sum():.0f}")
                print(f"Total cities: {cluster_stats['n_cities'].sum()}")
            elif data_type == 'gem':
                print(f"Total capacity: {cluster_stats['total_capacity_mw'].sum():.0f} MW")
                print(f"Total plants: {cluster_stats['n_plants'].sum()}")
            
            print(f"Clusters by size:")
            if data_type == 'demand':
                top_clusters = cluster_stats.nlargest(5, 'total_demand')
                for _, cluster in top_clusters.iterrows():
                    print(f"  {cluster['name']}: {cluster['total_demand']:.0f} demand ({cluster['n_cities']} cities)")
            elif data_type == 'gem':
                top_clusters = cluster_stats.nlargest(5, 'total_capacity_mw')
                for _, cluster in top_clusters.iterrows():
                    print(f"  {cluster['name']}: {cluster['total_capacity_mw']:.0f} MW ({cluster['n_plants']} plants)")
    
    def visualize_voronoi_clusters(self, data_type, output_dir):
        """Create visualization of Voronoi clusters"""
        if self.voronoi is None or self.data_points is None:
            return
        
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        
        # Plot Voronoi diagram
        voronoi_plot_2d(self.voronoi, ax=ax, show_vertices=False, line_colors='blue', line_width=2, point_size=0)
        
        # Plot data points colored by cluster
        colors = plt.cm.Set3(np.linspace(0, 1, len(self.cluster_centers)))
        
        for cluster_id in range(len(self.cluster_centers)):
            cluster_points = self.data_points[self.data_points['cluster'] == cluster_id]
            if len(cluster_points) > 0:
                ax.scatter(cluster_points['lng'], cluster_points['lat'], 
                          c=[colors[cluster_id]], s=50, alpha=0.7, 
                          label=f'Cluster {cluster_id}')
        
        # Plot cluster centers
        ax.scatter(self.cluster_centers[:, 0], self.cluster_centers[:, 1], 
                  c='red', s=200, marker='*', edgecolors='black', linewidth=2,
                  label='Voronoi Centers')
        
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title(f'{self.country} - Voronoi {data_type.title()} Clusters\n'
                    f'Non-Overlapping Regions by Construction')
        ax.grid(True, alpha=0.3)
        
        # Add legend (limit to avoid clutter)
        if len(self.cluster_centers) <= 15:
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        
        # Save visualization
        output_file = Path(output_dir) / f'{self.country}_voronoi_{data_type}_clusters.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Voronoi visualization saved: {output_file}")
        
        plt.show()

def main():
    parser = argparse.ArgumentParser(description='Create Voronoi-based non-overlapping clusters')
    parser.add_argument('--country', required=True, help='Country code (e.g., USA, IND)')
    parser.add_argument('--type', required=True, choices=['demand', 'gem'], 
                       help='Type of clustering: demand or gem')
    parser.add_argument('--clusters', type=int, required=True, help='Number of clusters')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--visualize', action='store_true', help='Create visualization')
    
    args = parser.parse_args()
    
    print(f"Creating Voronoi {args.type} clusters for {args.country}...")
    
    clusterer = VoronoiClusterer(args.country)
    
    # Load data
    if not clusterer.load_data(args.type, args.output_dir):
        print("Failed to load data")
        return
    
    # Create clusters
    result = clusterer.create_voronoi_clusters(args.clusters)
    if result is None:
        print("Clustering failed")
        return
    
    # Export results
    clusterer.export_results(args.type, args.output_dir)
    
    # Create visualization if requested
    if args.visualize:
        clusterer.visualize_voronoi_clusters(args.type, args.output_dir)
    
    print(f"Voronoi {args.type} clustering complete!")

if __name__ == '__main__':
    main()
