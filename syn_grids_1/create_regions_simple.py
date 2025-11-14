#!/usr/bin/env python3
"""
Simple Population-Only Demand Region Clustering
===============================================

Simplified wrapper that creates demand regions using only population data,
    bypassing OSM industrial facilities to avoid data quality issues.

Usage:
    python create_regions_simple.py --country IND --clusters 12
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
from sklearn.cluster import DBSCAN, KMeans
import argparse
import os
import sys
from pathlib import Path

# Add 1_grids to path for importing re_clustering functions
sys.path.append(str(Path(__file__).parent.parent / '1_grids'))
sys.path.append(str(Path(__file__).parent.parent / '1_grids' / 're_clustering'))

from re_clustering.identify_disconnected_regions import (
    identify_disconnected_regions_demand
)

class PopulationDemandRegionMapper:
    """
    Simple population-only demand region clustering
    """
    
    def __init__(self, country_code):
        self.country = country_code
        self.cities = None
        self.demand_points = None
        self.cluster_centers = None
        
    def load_city_data(self, cities_file='data/country_data/worldcities.csv'):
        """Load city population data"""
        df = pd.read_csv(cities_file)
        
        # Filter for country and significant cities
        country_filter = (df['iso3'] == self.country) & (df['population'] > 10000)
        
        if country_filter.sum() == 0:
            print(f"No cities found for {self.country}, trying with smaller threshold...")
            country_filter = (df['iso3'] == self.country) & (df['population'] > 10000)
        
        if country_filter.sum() == 0:
            print(f"Still no cities found for {self.country}, using all cities...")
            country_filter = df['iso3'] == self.country
        
        self.cities = df[country_filter].copy()
        
        # Add coordinate validation for known countries
        country_bounds = {
            'JPN': {'lat': (24, 46), 'lng': (123, 146)},  # Japan (including Okinawa)
            'USA': {'lat': (18, 72), 'lng': (-180, -65)}, # USA (including Alaska/Hawaii)
            'CHN': {'lat': (18, 54), 'lng': (73, 135)},   # China
            'IND': {'lat': (6, 37), 'lng': (68, 97)},     # India
            'DEU': {'lat': (47, 55), 'lng': (5, 16)},     # Germany
            'FRA': {'lat': (41, 51), 'lng': (-5, 10)},    # France
            'ITA': {'lat': (36, 47), 'lng': (6, 19)},     # Italy
            'CHE': {'lat': (45, 48), 'lng': (5, 11)},     # Switzerland
            'AUS': {'lat': (-44, -10), 'lng': (112, 154)}, # Australia
            'BRA': {'lat': (-34, 6), 'lng': (-74, -32)},  # Brazil
            'ZAF': {'lat': (-35, -22), 'lng': (16, 33)},  # South Africa
            'NZL': {'lat': (-47, -34), 'lng': (166, 179)}, # New Zealand
        }
        
        if self.country in country_bounds:
            bounds = country_bounds[self.country]
            lat_min, lat_max = bounds['lat']
            lng_min, lng_max = bounds['lng']
            
            # Filter out cities with invalid coordinates
            valid_coords = (
                (self.cities['lat'] >= lat_min) & (self.cities['lat'] <= lat_max) &
                (self.cities['lng'] >= lng_min) & (self.cities['lng'] <= lng_max)
            )
            
            invalid_cities = self.cities[~valid_coords]
            if len(invalid_cities) > 0:
                print(f"Filtering out {len(invalid_cities)} cities with invalid coordinates:")
                for _, city in invalid_cities.iterrows():
                    print(f"  {city['city']}: ({city['lat']:.2f}, {city['lng']:.2f}) - outside bounds")
            
            self.cities = self.cities[valid_coords].copy()
        
        print(f"Loaded {len(self.cities)} cities for {self.country}")
        return self.cities
    
    def create_demand_points(self):
        """Create demand points from population data only"""
        if self.cities is None:
            print("No city data loaded")
            return None
        
        demand_points = []
        
        # Add population centers
        for _, city in self.cities.iterrows():
            demand_points.append({
                'name': city['city'],
                'lat': city['lat'],
                'lng': city['lng'],
                'type': 'population',
                'raw_weight': city['population'] / 1000,  # Convert to thousands
                'scaled_weight': city['population'] / 1000,  # Same as raw for population-only
                'subtype': 'city'
            })
        
        self.demand_points = pd.DataFrame(demand_points)
        print(f"Created {len(self.demand_points)} population-based demand points")
        return self.demand_points

    def filter_demand_points_for_disconnected_regions(self):
        """Filter demand points for disconnected regions"""
        if self.demand_points is None:
            print("No demand points to filter")
            return None
        
        result = identify_disconnected_regions_demand(self.demand_points, self.country, plot=False)
        self.demand_points = self.demand_points[self.demand_points['name'].isin(result['main_continental_nodes'])]
        
        return self.demand_points
    
    def cluster_demand_points(self, method='voronoi', n_clusters=None, eps_km=100):
        """Cluster demand points using Voronoi diagrams for non-overlapping regions"""
        if self.demand_points is None or len(self.demand_points) == 0:
            print("No demand points to cluster")
            return None
        
        print(f"Creating {n_clusters or 'auto'} Voronoi demand regions from {len(self.demand_points)} cities...")
        
        if method == 'voronoi' and n_clusters:
            # Use Voronoi clustering for non-overlapping regions
            self._cluster_voronoi(n_clusters)
        else:
            # Fallback to original DBSCAN method
            print("Using fallback DBSCAN clustering...")
            coords = np.radians(self.demand_points[['lat', 'lng']].values)
            eps_radians = eps_km / 6371  # Earth radius in km
            
            clustering = DBSCAN(eps=eps_radians, min_samples=2, metric='haversine').fit(coords)
            self.demand_points['cluster'] = clustering.labels_
        
        # Handle noise points
        noise_mask = self.demand_points['cluster'] == -1
        if noise_mask.sum() > 0:
            print(f"Assigning {noise_mask.sum()} noise points to nearest clusters...")
            for idx in self.demand_points[noise_mask].index:
                point = self.demand_points.loc[idx]
                non_noise = self.demand_points[~noise_mask]
                if len(non_noise) > 0:
                    distances = non_noise.apply(
                        lambda row: self._haversine_distance(
                            point['lat'], point['lng'],
                            row['lat'], row['lng']
                        ), axis=1
                    )
                    nearest_idx = distances.idxmin()
                    self.demand_points.loc[idx, 'cluster'] = non_noise.loc[nearest_idx, 'cluster']
        
        # Adjust to target number of clusters if specified
        if n_clusters:
            self._adjust_clusters_to_target(n_clusters)
        
        n_final_clusters = self.demand_points['cluster'].nunique()
        print(f"Final clustering: {n_final_clusters} regions")
        
        return self.demand_points
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate haversine distance between two points in km"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Earth radius in km
        
        return c * r
    
    def _cluster_voronoi(self, n_clusters):
        """Create Voronoi-based non-overlapping clusters"""
        from scipy.spatial import Voronoi
        from scipy.spatial.distance import cdist
        from sklearn.cluster import KMeans
        
        print(f"Creating {n_clusters} Voronoi clusters...")
        
        # Step 1: Use K-means to find optimal cluster centers
        coords = self.demand_points[['lng', 'lat']].values
        weights = self.demand_points['scaled_weight'].values
        
        # Create weighted coordinates by repeating points based on weight
        weighted_coords = []
        for i, (coord, weight) in enumerate(zip(coords, weights)):
            # Repeat each point proportional to its weight (capped for performance)
            repeat_count = max(1, min(int(weight / weights.mean()), 10))
            for _ in range(repeat_count):
                weighted_coords.append(coord)
        
        weighted_coords = np.array(weighted_coords)
        
        # Fit K-means on weighted coordinates
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(weighted_coords)
        cluster_centers = kmeans.cluster_centers_
        
        # Step 2: Create Voronoi diagram from cluster centers
        voronoi = Voronoi(cluster_centers)
        
        # Step 3: Assign each data point to nearest Voronoi center
        distances = cdist(coords, cluster_centers)
        cluster_assignments = np.argmin(distances, axis=1)
        
        self.demand_points['cluster'] = cluster_assignments
        
        print(f"Assigned {len(self.demand_points)} cities to {n_clusters} Voronoi regions")
    
    def _adjust_clusters_to_target(self, target_clusters):
        """Adjust number of clusters to target"""
        current_n = self.demand_points['cluster'].nunique()
        
        while current_n != target_clusters:
            cluster_sizes = self.demand_points.groupby('cluster')['scaled_weight'].sum()
            
            if current_n > target_clusters:
                # Merge smallest cluster
                smallest = cluster_sizes.idxmin()
                smallest_points = self.demand_points[self.demand_points['cluster'] == smallest]
                
                # Find nearest cluster by centroid distance
                smallest_center_lat = smallest_points['lat'].mean()
                smallest_center_lng = smallest_points['lng'].mean()
                
                min_dist = float('inf')
                nearest_cluster = None
                
                for cluster_id in cluster_sizes.index:
                    if cluster_id == smallest:
                        continue
                    cluster_points = self.demand_points[self.demand_points['cluster'] == cluster_id]
                    cluster_center_lat = cluster_points['lat'].mean()
                    cluster_center_lng = cluster_points['lng'].mean()
                    
                    dist = self._haversine_distance(
                        smallest_center_lat, smallest_center_lng,
                        cluster_center_lat, cluster_center_lng
                    )
                    
                    if dist < min_dist:
                        min_dist = dist
                        nearest_cluster = cluster_id
                
                # Merge
                self.demand_points.loc[self.demand_points['cluster'] == smallest, 'cluster'] = nearest_cluster
                
            else:  # current_n < target_clusters
                # Split largest cluster
                largest = cluster_sizes.idxmax()
                largest_points = self.demand_points[self.demand_points['cluster'] == largest]
                
                if len(largest_points) >= 2:
                    coords = largest_points[['lat', 'lng']].values
                    kmeans = KMeans(n_clusters=2, random_state=42)
                    sub_labels = kmeans.fit_predict(coords)
                    
                    new_cluster_id = self.demand_points['cluster'].max() + 1
                    indices_to_change = largest_points.index[sub_labels == 1]
                    self.demand_points.loc[indices_to_change, 'cluster'] = new_cluster_id
                else:
                    break
            
            current_n = self.demand_points['cluster'].nunique()
    
    def calculate_cluster_centers(self):
        """Calculate population-weighted cluster centers with geographic validation"""
        clusters = []
        
        for cluster_id in self.demand_points['cluster'].unique():
            cluster_points = self.demand_points[self.demand_points['cluster'] == cluster_id]
            
            # Check for geographic coherence - cities shouldn't be more than 1000km apart in same cluster
            if len(cluster_points) > 1:
                coords = cluster_points[['lat', 'lng']].values
                max_distance = 0
                for i in range(len(coords)):
                    for j in range(i+1, len(coords)):
                        dist = self._haversine_distance(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
                        max_distance = max(max_distance, dist)
                
                if max_distance > 1000:  # More than 1000km apart
                    # Use simple geometric centroid for geographically dispersed clusters
                    weighted_lat = cluster_points['lat'].mean()
                    weighted_lng = cluster_points['lng'].mean()
                    total_weight = cluster_points['scaled_weight'].sum()
                else:
                    # Population-weighted centroid for geographically coherent clusters
                    total_weight = cluster_points['scaled_weight'].sum()
                    weighted_lat = (cluster_points['lat'] * cluster_points['scaled_weight']).sum() / total_weight
                    weighted_lng = (cluster_points['lng'] * cluster_points['scaled_weight']).sum() / total_weight
            else:
                # Single city cluster
                weighted_lat = cluster_points['lat'].iloc[0]
                weighted_lng = cluster_points['lng'].iloc[0]
                total_weight = cluster_points['scaled_weight'].sum()
            
            # Find largest city in cluster
            largest_city_idx = cluster_points['raw_weight'].idxmax()
            largest_city_raw = cluster_points.loc[largest_city_idx, 'name']
            # Handle Unicode in city names safely
            largest_city = str(largest_city_raw).encode('ascii', 'replace').decode('ascii')
            
            clusters.append({
                'cluster_id': int(cluster_id),
                'name': f"{largest_city}_region",
                'center_lat': weighted_lat,
                'center_lng': weighted_lng,
                'total_demand': total_weight,
                'population_demand': total_weight,
                'industrial_demand': 0.0,  # No industrial in population-only mode
                'demand_share': 0,  # Will calculate after
                'n_cities': len(cluster_points),
                'n_industrial': 0,  # No industrial facilities
                'major_city': largest_city,
                'major_industries': 'None (population-only mode)'
            })
        
        self.cluster_centers = pd.DataFrame(clusters)
        self.cluster_centers['demand_share'] = (
            self.cluster_centers['total_demand'] / 
            self.cluster_centers['total_demand'].sum()
        )
        
        return self.cluster_centers
    
    def estimate_ntc_between_regions(self):
        """Estimate NTC between demand regions (simplified)"""
        if self.cluster_centers is None:
            print("No cluster centers available for NTC estimation")
            return None
        
        print("Estimating NTC between demand regions...")
        
        ntc_connections = []
        regions = self.cluster_centers
        
        for i, region_a in regions.iterrows():
            for j, region_b in regions.iterrows():
                if i >= j:  # Avoid duplicates and self-connections
                    continue
                
                # Calculate distance
                distance_km = self._haversine_distance(
                    region_a['center_lat'], region_a['center_lng'],
                    region_b['center_lat'], region_b['center_lng']
                )
                
                # Simple NTC estimation based on demand and distance
                demand_a = region_a['total_demand']
                demand_b = region_b['total_demand']
                
                # Base transmission need
                transmission_need = min(demand_a, demand_b) * 0.3  # 30% of smaller demand
                
                # Distance penalty
                distance_factor = max(0.2, 1 / (1 + distance_km / 300))  # 300km reference
                
                # Country-specific factors
                country_factors = {
                    'CHE': 1.2, 'DEU': 1.1, 'ITA': 1.0, 'USA': 0.8, 'IND': 0.6,
                    'CHN': 0.7, 'JPN': 1.1, 'AUS': 0.5, 'ZAF': 0.7, 'NZL': 0.9, 'BRA': 0.6
                }
                country_factor = country_factors.get(self.country, 1.0)
                
                # Calculate estimated NTC
                estimated_ntc = transmission_need * distance_factor * country_factor
                
                # Practical limits
                estimated_ntc = max(100, min(5000, estimated_ntc))  # 100 MW to 5 GW
                
                ntc_connections.append({
                    'from_region': region_a['name'],
                    'to_region': region_b['name'],
                    'from_id': int(region_a['cluster_id']),
                    'to_id': int(region_b['cluster_id']),
                    'distance_km': round(distance_km, 1),
                    'estimated_ntc_mw': round(estimated_ntc, 0),
                    'from_demand': round(demand_a, 1),
                    'to_demand': round(demand_b, 1)
                })
        
        self.ntc_connections = pd.DataFrame(ntc_connections)
        print(f"Estimated NTC for {len(self.ntc_connections)} region pairs")
        return self.ntc_connections
    
    def get_results_data(self, return_format='dataframe'):
        """
        Get results data as DataFrames or arrays instead of exporting to CSV
        
        Parameters:
        -----------
        return_format : str, optional
            Format to return data in. Options:
            - 'dataframe': Return pandas DataFrames (default)
            - 'array': Return numpy arrays
            - 'dict': Return dictionary with DataFrames
            
        Returns:
        --------
        dict or tuple
            Dictionary containing:
            - 'demand_points': DataFrame/array of demand points
            - 'cluster_centers': DataFrame/array of region centers  
            - 'ntc_connections': DataFrame/array of NTC connections
            - 'summary': Dictionary with summary statistics
        """
        results = {}
        
        # Get demand points
        if self.demand_points is not None:
            if return_format == 'array':
                results['demand_points'] = self.demand_points.values
            else:
                results['demand_points'] = self.demand_points.copy()
        else:
            results['demand_points'] = None
        
        # Get cluster centers
        if self.cluster_centers is not None:
            if return_format == 'array':
                results['cluster_centers'] = self.cluster_centers.values
            else:
                results['cluster_centers'] = self.cluster_centers.copy()
        else:
            results['cluster_centers'] = None
        
        # Get NTC connections
        if hasattr(self, 'ntc_connections') and self.ntc_connections is not None:
            if return_format == 'array':
                results['ntc_connections'] = self.ntc_connections.values
            else:
                results['ntc_connections'] = self.ntc_connections.copy()
        else:
            results['ntc_connections'] = None
        
        # Calculate summary statistics
        summary = {}
        if self.cluster_centers is not None:
            summary = {
                'country': self.country,
                'total_regions': len(self.cluster_centers),
                'total_population_demand': float(self.cluster_centers['total_demand'].sum()),
                'average_region_size': float(self.cluster_centers['total_demand'].mean()),
                'total_demand_points': len(self.demand_points) if self.demand_points is not None else 0,
                'total_ntc_connections': len(self.ntc_connections) if hasattr(self, 'ntc_connections') and self.ntc_connections is not None else 0
            }
            
            # Top 5 regions by population
            top_regions = self.cluster_centers.nlargest(5, 'total_demand')
            summary['top_regions'] = []
            for _, region in top_regions.iterrows():
                city_name = str(region['major_city']).encode('ascii', 'replace').decode('ascii')
                summary['top_regions'].append({
                    'name': city_name,
                    'total_demand': float(region['total_demand']),
                    'demand_share': float(region['demand_share']),
                    'n_cities': int(region['n_cities'])
                })
        
        results['summary'] = summary
        
        return results

    def export_results(self, output_dir='output'):
        """Export results to CSV files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Export demand points
        if self.demand_points is not None:
            points_file = os.path.join(output_dir, f'{self.country}_demand_points.csv')
            self.demand_points.to_csv(points_file, index=False)
            print(f"Exported demand points to {points_file}")
        
        # Export cluster centers
        if self.cluster_centers is not None:
            centers_file = os.path.join(output_dir, f'{self.country}_region_centers.csv')
            self.cluster_centers.to_csv(centers_file, index=False)
            print(f"Exported region centers to {centers_file}")
        
        # Export NTC connections
        if hasattr(self, 'ntc_connections') and self.ntc_connections is not None:
            ntc_file = os.path.join(output_dir, f'{self.country}_ntc_connections.csv')
            self.ntc_connections.to_csv(ntc_file, index=False)
            print(f"Exported NTC connections to {ntc_file}")
        
        # Print summary
        if self.cluster_centers is not None:
            print(f"\n=== {self.country} POPULATION-ONLY DEMAND REGIONS SUMMARY ===")
            print(f"Total regions: {len(self.cluster_centers)}")
            print(f"Total population demand: {self.cluster_centers['total_demand'].sum():,.0f}")
            print(f"Average region size: {self.cluster_centers['total_demand'].mean():,.0f}")
            
            print("\nTop 5 regions by population:")
            top_regions = self.cluster_centers.nlargest(5, 'total_demand')
            for _, region in top_regions.iterrows():
                # Handle Unicode city names safely
                city_name = str(region['major_city']).encode('ascii', 'replace').decode('ascii')
                print(f"  {city_name}: {region['total_demand']:,.0f} "
                      f"({region['demand_share']:.1%}, {region['n_cities']} cities)")


def analyze_country_population_demand(country_code, target_clusters=None, eps_km=100):
    """Complete population-only demand analysis pipeline"""
    print(f"\nStarting population-only demand region analysis for {country_code}")
    
    # Initialize mapper
    mapper = PopulationDemandRegionMapper(country_code)
    
    # Load data
    print("\nLoading city data...")
    mapper.load_city_data()
    
    # Create demand points (population only)
    print("\nCreating population-based demand points...")
    mapper.create_demand_points()
    
    # Cluster demand points
    print(f"\nClustering into regions (target: {target_clusters or 'auto'})...")
    mapper.cluster_demand_points(method='voronoi', n_clusters=target_clusters, eps_km=eps_km)
    
    # Calculate cluster centers
    print("\nCalculating cluster centers...")
    mapper.calculate_cluster_centers()
    
    # Estimate NTC between regions
    mapper.estimate_ntc_between_regions()
    
    return mapper


if __name__ == "__main__":
    # Default cluster suggestions for known countries (optional)
    default_clusters = {
        'CHE': 4, 'ITA': 7, 'DEU': 10, 'USA': 15, 'AUS': 8, 'CHN': 20,
        'IND': 12, 'JPN': 10, 'ZAF': 6, 'NZL': 4, 'BRA': 12, 'FRA': 8,
        'GBR': 8, 'ESP': 6, 'CAN': 12, 'MEX': 8, 'ARG': 6, 'RUS': 15,
        'TUR': 6, 'IRN': 8, 'SAU': 4, 'EGY': 6, 'NGA': 8, 'KEN': 4,
        'ETH': 6, 'GHA': 4, 'THA': 6, 'VNM': 6, 'IDN': 10, 'MYS': 4,
        'PHL': 8, 'KOR': 6, 'TWN': 4, 'SGP': 1, 'HKG': 1, 'ARE': 2
    }
    
    parser = argparse.ArgumentParser(description='Population-only demand region analysis')
    parser.add_argument('--country', required=True,
                       help='ISO3 country code for analysis (e.g., USA, DEU, IND)')
    parser.add_argument('--clusters', type=int,
                       help='Target number of regions (default: auto-suggested based on country)')
    parser.add_argument('--eps-km', type=float, default=100,
                       help='DBSCAN epsilon parameter in km (default: 100)')
    parser.add_argument('--output-dir', default='output',
                       help='Output directory for results (default: output)')
    
    args = parser.parse_args()
    
    # Use suggested clusters if available, otherwise default to 6
    target_clusters = args.clusters or default_clusters.get(args.country.upper(), 6)
    
    print(f"Selected: {args.country.upper()}")
    print(f"Target regions: {target_clusters}")
    print("Mode: Population-only (no OSM industrial data)")
    
    # Run analysis
    result = analyze_country_population_demand(args.country.upper(), target_clusters=target_clusters, eps_km=args.eps_km)
    
    # Export to custom directory
    if result:
        result.export_results(args.output_dir)
    
    print(f"\nAnalysis complete for {args.country.upper()}!")
    print(f"Check the '{args.output_dir}' folder for CSV files with detailed results.")
