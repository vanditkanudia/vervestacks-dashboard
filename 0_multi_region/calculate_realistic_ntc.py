#!/usr/bin/env python3
"""
Realistic NTC (Net Transfer Capacity) Calculator
===============================================

Calculates transmission capacity only between geographically overlapping clusters
using convex hull intersection with visualization thresholds to filter noise.

Usage:
    python calculate_realistic_ntc.py --country USA --output-dir output/USA_d10g10r10
"""

import pandas as pd
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import argparse
import os
from pathlib import Path

class RealisticNTCCalculator:
    """Calculate NTC only between overlapping clusters"""
    
    def __init__(self, country_code, output_dir='output'):
        self.country = country_code
        self.output_dir = output_dir
        
        # Visualization thresholds (same as in create_summary_map_visual.py)
        self.min_generation_gwh = 100   # For renewable grid cells (lowered from 1000)
        self.min_capacity_mw = 10       # For power plants (lowered from 50)
        self.min_population = 10000     # For cities (lowered from 100000)
        
        # Load cluster data
        self.demand_centers = None
        self.demand_points = None
        self.gem_centers = None
        self.gem_mapping = None
        self.renewable_centers = None
        self.renewable_mapping = None
        
    def load_cluster_data(self):
        """Load all cluster data files"""
        base_path = Path(self.output_dir)
        
        # Load demand data
        demand_centers_file = base_path / f'{self.country}_region_centers.csv'
        demand_points_file = base_path / f'{self.country}_demand_points.csv'
        
        if demand_centers_file.exists():
            self.demand_centers = pd.read_csv(demand_centers_file)
            print(f"Loaded {len(self.demand_centers)} demand centers")
        
        if demand_points_file.exists():
            self.demand_points = pd.read_csv(demand_points_file)
            print(f"Loaded {len(self.demand_points)} demand points")
        
        # Load GEM data
        gem_centers_file = base_path / f'{self.country}_gem_cluster_centers.csv'
        gem_mapping_file = base_path / f'{self.country}_gem_cluster_mapping.csv'
        
        if gem_centers_file.exists():
            self.gem_centers = pd.read_csv(gem_centers_file)
            print(f"Loaded {len(self.gem_centers)} GEM centers")
        
        if gem_mapping_file.exists():
            self.gem_mapping = pd.read_csv(gem_mapping_file)
            print(f"Loaded {len(self.gem_mapping)} GEM facilities")
        
        # Load renewable data
        renewable_centers_file = base_path / f'{self.country}_renewable_cluster_centers.csv'
        renewable_mapping_file = base_path / f'{self.country}_renewable_cluster_mapping.csv'
        
        if renewable_centers_file.exists():
            self.renewable_centers = pd.read_csv(renewable_centers_file)
            print(f"Loaded {len(self.renewable_centers)} renewable centers")
        
        if renewable_mapping_file.exists():
            self.renewable_mapping = pd.read_csv(renewable_mapping_file)
            print(f"Loaded {len(self.renewable_mapping)} renewable grid cells")
    
    def apply_visualization_thresholds(self, data, data_type):
        """Apply the same thresholds used in visualization to filter noise"""
        if data is None or len(data) == 0:
            return data
            
        filtered_data = data.copy()
        
        if data_type == 'demand':
            # Filter by population (scaled_weight is in thousands)
            if 'scaled_weight' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['scaled_weight'] >= self.min_population/1000]
        
        elif data_type == 'gem':
            # Filter by capacity
            if 'total_capacity_mw' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['total_capacity_mw'] >= self.min_capacity_mw]
        
        elif data_type == 'renewable':
            # Filter by generation
            if 'total_generation_gwh' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['total_generation_gwh'] >= self.min_generation_gwh]
        
        return filtered_data
    
    def create_cluster_polygon(self, cluster_points, cluster_id, cluster_id_col='cluster_id'):
        """Create convex hull polygon for a cluster with threshold filtering"""
        if cluster_points is None or len(cluster_points) == 0:
            return None
            
        # Get points for this cluster
        points = cluster_points[cluster_points[cluster_id_col] == cluster_id]
        
        if len(points) < 3:
            return None
            
        try:
            # Get coordinates
            coords = points[['lng', 'lat']].values
            
            # Create convex hull
            hull = ConvexHull(coords)
            hull_points = coords[hull.vertices]
            
            # Create Shapely polygon
            polygon = Polygon(hull_points)
            return polygon
            
        except Exception as e:
            print(f"Error creating polygon for cluster {cluster_id}: {e}")
            return None
    
    def calculate_overlap_area(self, poly1, poly2):
        """Calculate intersection area between two polygons in km²"""
        if poly1 is None or poly2 is None:
            return 0
            
        try:
            intersection = poly1.intersection(poly2)
            if intersection.is_empty:
                return 0
                
            # Rough conversion to km² (1 degree ≈ 111 km at equator)
            area_deg2 = intersection.area
            area_km2 = area_deg2 * (111 ** 2)
            return area_km2
            
        except Exception as e:
            print(f"Error calculating overlap: {e}")
            return 0
    
    def calculate_distance_km(self, lat1, lng1, lat2, lng2):
        """Calculate haversine distance between two points"""
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(np.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        # Earth radius in km
        r = 6371
        return c * r
    
    def calculate_ntc_capacity(self, overlap_area_km2, distance_km, capacity_mw_or_gwh, capacity_type='MW'):
        """Calculate NTC capacity based on overlap and distance"""
        if overlap_area_km2 <= 0:
            return 0
            
        # Base transmission capacity per km² of overlap
        base_capacity_per_km2 = 10  # MW per km² of overlap
        
        # Distance penalty (transmission gets expensive over long distances)
        if distance_km <= 100:
            distance_factor = 1.0
        elif distance_km <= 500:
            distance_factor = 0.8
        elif distance_km <= 1000:
            distance_factor = 0.5
        else:
            distance_factor = 0.2
        
        # Overlap-based capacity
        overlap_capacity = overlap_area_km2 * base_capacity_per_km2
        
        # Scale by available capacity (don't exceed what's actually there)
        if capacity_type == 'GWh':
            # Convert GWh to MW assuming 50% capacity factor
            available_mw = capacity_mw_or_gwh * 1000 / (365 * 24 * 0.5)
        else:
            available_mw = capacity_mw_or_gwh
            
        # Final NTC is minimum of overlap-based and availability-based capacity
        ntc_mw = min(overlap_capacity, available_mw * 0.3) * distance_factor
        
        return max(0, ntc_mw)
    
    def calculate_gem_to_demand_ntc(self):
        """Calculate NTC between GEM clusters and overlapping demand regions"""
        if self.gem_centers is None or self.demand_centers is None:
            print("Missing GEM or demand data")
            return pd.DataFrame()
            
        if self.gem_mapping is None or self.demand_points is None:
            print("Missing GEM mapping or demand points data")
            return pd.DataFrame()
        
        print("Calculating GEM -> Demand NTC...")
        
        # Apply thresholds
        filtered_gem_mapping = self.apply_visualization_thresholds(self.gem_mapping, 'gem')
        filtered_demand_points = self.apply_visualization_thresholds(self.demand_points, 'demand')
        
        ntc_results = []
        
        for _, gem_center in self.gem_centers.iterrows():
            gem_id = gem_center['cluster_id']
            
            # Create GEM cluster polygon
            gem_polygon = self.create_cluster_polygon(filtered_gem_mapping, gem_id, 'cluster_id')
            if gem_polygon is None:
                continue
                
            for _, demand_center in self.demand_centers.iterrows():
                demand_id = demand_center['cluster_id']
                
                # Create demand cluster polygon
                demand_polygon = self.create_cluster_polygon(filtered_demand_points, demand_id, 'cluster')
                if demand_polygon is None:
                    continue
                
                # Calculate overlap
                overlap_area = self.calculate_overlap_area(gem_polygon, demand_polygon)
                
                if overlap_area > 0:  # Only create NTC if there's overlap
                    # Calculate distance between centers
                    distance = self.calculate_distance_km(
                        gem_center['center_lat'], gem_center['center_lng'],
                        demand_center['center_lat'], demand_center['center_lng']
                    )
                    
                    # Calculate NTC capacity
                    ntc_capacity = self.calculate_ntc_capacity(
                        overlap_area, distance, gem_center.get('total_capacity_mw', 0), 'MW'
                    )
                    
                    if ntc_capacity > 0:
                        ntc_results.append({
                            'from_cluster': gem_center['name'],
                            'from_type': 'GEM',
                            'from_id': gem_id,
                            'to_cluster': demand_center['name'],
                            'to_type': 'DEMAND',
                            'to_id': demand_id,
                            'ntc_mw': ntc_capacity,
                            'distance_km': distance,
                            'overlap_area_km2': overlap_area
                        })
        
        return pd.DataFrame(ntc_results)
    
    def calculate_renewable_to_demand_ntc(self):
        """Calculate NTC between renewable zones and overlapping demand regions"""
        if self.renewable_centers is None or self.demand_centers is None:
            print("Missing renewable or demand data")
            return pd.DataFrame()
            
        if self.renewable_mapping is None or self.demand_points is None:
            print("Missing renewable mapping or demand points data")
            return pd.DataFrame()
        
        print("Calculating Renewable -> Demand NTC...")
        
        # Apply thresholds
        filtered_renewable_mapping = self.apply_visualization_thresholds(self.renewable_mapping, 'renewable')
        filtered_demand_points = self.apply_visualization_thresholds(self.demand_points, 'demand')
        
        ntc_results = []
        
        for _, renewable_center in self.renewable_centers.iterrows():
            renewable_id = renewable_center['cluster_id']
            
            # Create renewable cluster polygon
            renewable_polygon = self.create_cluster_polygon(filtered_renewable_mapping, renewable_id, 'cluster_id')
            if renewable_polygon is None:
                continue
                
            for _, demand_center in self.demand_centers.iterrows():
                demand_id = demand_center['cluster_id']
                
                # Create demand cluster polygon
                demand_polygon = self.create_cluster_polygon(filtered_demand_points, demand_id, 'cluster')
                if demand_polygon is None:
                    continue
                
                # Calculate overlap
                overlap_area = self.calculate_overlap_area(renewable_polygon, demand_polygon)
                
                if overlap_area > 0:  # Only create NTC if there's overlap
                    # Calculate distance between centers
                    distance = self.calculate_distance_km(
                        renewable_center['center_lat'], renewable_center['center_lng'],
                        demand_center['center_lat'], demand_center['center_lng']
                    )
                    
                    # Calculate NTC capacity
                    ntc_capacity = self.calculate_ntc_capacity(
                        overlap_area, distance, renewable_center.get('total_generation_gwh', 0), 'GWh'
                    )
                    
                    if ntc_capacity > 0:
                        ntc_results.append({
                            'from_cluster': renewable_center['name'],
                            'from_type': 'RENEWABLE',
                            'from_id': renewable_id,
                            'to_cluster': demand_center['name'],
                            'to_type': 'DEMAND',
                            'to_id': demand_id,
                            'ntc_mw': ntc_capacity,
                            'distance_km': distance,
                            'overlap_area_km2': overlap_area
                        })
        
        return pd.DataFrame(ntc_results)
    
    def calculate_renewable_to_gem_ntc(self):
        """Calculate NTC between renewable zones and overlapping GEM clusters"""
        if self.renewable_centers is None or self.gem_centers is None:
            print("Missing renewable or GEM data")
            return pd.DataFrame()
            
        if self.renewable_mapping is None or self.gem_mapping is None:
            print("Missing renewable or GEM mapping data")
            return pd.DataFrame()
        
        print("Calculating Renewable -> GEM NTC...")
        
        # Apply thresholds
        filtered_renewable_mapping = self.apply_visualization_thresholds(self.renewable_mapping, 'renewable')
        filtered_gem_mapping = self.apply_visualization_thresholds(self.gem_mapping, 'gem')
        
        ntc_results = []
        
        for _, renewable_center in self.renewable_centers.iterrows():
            renewable_id = renewable_center['cluster_id']
            
            # Create renewable cluster polygon
            renewable_polygon = self.create_cluster_polygon(filtered_renewable_mapping, renewable_id, 'cluster_id')
            if renewable_polygon is None:
                continue
                
            for _, gem_center in self.gem_centers.iterrows():
                gem_id = gem_center['cluster_id']
                
                # Create GEM cluster polygon
                gem_polygon = self.create_cluster_polygon(filtered_gem_mapping, gem_id, 'cluster_id')
                if gem_polygon is None:
                    continue
                
                # Calculate overlap
                overlap_area = self.calculate_overlap_area(renewable_polygon, gem_polygon)
                
                if overlap_area > 0:  # Only create NTC if there's overlap
                    # Calculate distance between centers
                    distance = self.calculate_distance_km(
                        renewable_center['center_lat'], renewable_center['center_lng'],
                        gem_center['center_lat'], gem_center['center_lng']
                    )
                    
                    # Calculate NTC capacity (use smaller of renewable and GEM capacity)
                    renewable_capacity_mw = renewable_center.get('total_generation_gwh', 0) * 1000 / (365 * 24 * 0.5)
                    gem_capacity_mw = gem_center.get('total_capacity_mw', 0)
                    
                    ntc_capacity = self.calculate_ntc_capacity(
                        overlap_area, distance, min(renewable_capacity_mw, gem_capacity_mw), 'MW'
                    )
                    
                    if ntc_capacity > 0:
                        ntc_results.append({
                            'from_cluster': renewable_center['name'],
                            'from_type': 'RENEWABLE',
                            'from_id': renewable_id,
                            'to_cluster': gem_center['name'],
                            'to_type': 'GEM',
                            'to_id': gem_id,
                            'ntc_mw': ntc_capacity,
                            'distance_km': distance,
                            'overlap_area_km2': overlap_area
                        })
        
        return pd.DataFrame(ntc_results)
    
    def calculate_all_ntc(self):
        """Calculate all NTC connections and save results"""
        print(f"\n=== CALCULATING REALISTIC NTC FOR {self.country} ===")
        
        # Load data
        self.load_cluster_data()
        
        # Calculate all NTC types
        gem_to_demand = self.calculate_gem_to_demand_ntc()
        renewable_to_demand = self.calculate_renewable_to_demand_ntc()
        renewable_to_gem = self.calculate_renewable_to_gem_ntc()
        
        # Combine all results and add connection_type column
        connection_dfs = []
        
        if len(gem_to_demand) > 0:
            gem_to_demand['connection_type'] = 'GEM_TO_DEMAND'
            connection_dfs.append(gem_to_demand)
            
        if len(renewable_to_demand) > 0:
            renewable_to_demand['connection_type'] = 'RENEWABLE_TO_DEMAND'
            connection_dfs.append(renewable_to_demand)
            
        if len(renewable_to_gem) > 0:
            renewable_to_gem['connection_type'] = 'RENEWABLE_TO_GEM'
            connection_dfs.append(renewable_to_gem)
        
        if len(connection_dfs) == 0:
            print("No overlapping clusters found - no NTC connections created")
            return
            
        all_ntc = pd.concat(connection_dfs, ignore_index=True)
        
        # Rename columns for visualization compatibility
        all_ntc = all_ntc.rename(columns={
            'from_cluster': 'from_name',
            'to_cluster': 'to_name'
        })
        
        # Save results
        output_file = Path(self.output_dir) / f'{self.country}_realistic_ntc_connections.csv'
        all_ntc.to_csv(output_file, index=False)
        
        # Print summary
        print(f"\n=== NTC CALCULATION COMPLETE ===")
        print(f"Total connections: {len(all_ntc)}")
        print(f"GEM -> Demand: {len(gem_to_demand)}")
        print(f"Renewable -> Demand: {len(renewable_to_demand)}")
        print(f"Renewable -> GEM: {len(renewable_to_gem)}")
        print(f"Total NTC capacity: {all_ntc['ntc_mw'].sum():.0f} MW")
        print(f"Average distance: {all_ntc['distance_km'].mean():.0f} km")
        print(f"Results saved: {output_file}")
        
        return all_ntc

def main():
    parser = argparse.ArgumentParser(description='Calculate realistic NTC between overlapping clusters')
    parser.add_argument('--country', required=True, help='Country code (e.g., USA, IND)')
    parser.add_argument('--output-dir', required=True, help='Output directory with cluster files')
    
    args = parser.parse_args()
    
    calculator = RealisticNTCCalculator(args.country, args.output_dir)
    calculator.calculate_all_ntc()

if __name__ == '__main__':
    main()
