#!/usr/bin/env python3
"""
Cluster Overlap Checker
======================

Checks if cluster convex hulls overlap within each cluster type
(demand, GEM, renewable) and reports any overlapping pairs.

Usage:
    python check_cluster_overlaps.py --country USA --output-dir output/USA_d10g10r10
"""

import pandas as pd
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon
import argparse
import os
from pathlib import Path

class ClusterOverlapChecker:
    """Check for overlapping cluster shapes"""
    
    def __init__(self, country_code, output_dir='output'):
        self.country = country_code
        self.output_dir = output_dir
        
        # Visualization thresholds (same as in create_summary_map_visual.py)
        self.min_generation_gwh = 1000
        self.min_capacity_mw = 50
        self.min_population = 100000
        
    def apply_visualization_thresholds(self, data, data_type):
        """Apply the same thresholds used in visualization"""
        if data is None or len(data) == 0:
            return data
            
        filtered_data = data.copy()
        
        if data_type == 'demand':
            if 'scaled_weight' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['scaled_weight'] >= self.min_population/1000]
        elif data_type == 'gem':
            if 'total_capacity_mw' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['total_capacity_mw'] >= self.min_capacity_mw]
        elif data_type == 'renewable':
            if 'total_generation_gwh' in filtered_data.columns:
                filtered_data = filtered_data[filtered_data['total_generation_gwh'] >= self.min_generation_gwh]
        
        return filtered_data
    
    def create_cluster_polygon(self, cluster_points, cluster_id, cluster_id_col='cluster_id'):
        """Create convex hull polygon for a cluster"""
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
    
    def check_overlaps_within_type(self, cluster_points, cluster_type, cluster_id_col='cluster_id'):
        """Check for overlaps within a single cluster type"""
        if cluster_points is None or len(cluster_points) == 0:
            return []
        
        print(f"\n=== Checking {cluster_type} Cluster Overlaps ===")
        
        # Apply thresholds
        filtered_points = self.apply_visualization_thresholds(cluster_points, cluster_type.lower())
        
        # Get unique cluster IDs
        cluster_ids = sorted(filtered_points[cluster_id_col].unique())
        print(f"Checking {len(cluster_ids)} {cluster_type} clusters...")
        
        # Create polygons for all clusters
        polygons = {}
        for cluster_id in cluster_ids:
            polygon = self.create_cluster_polygon(filtered_points, cluster_id, cluster_id_col)
            if polygon is not None:
                polygons[cluster_id] = polygon
        
        print(f"Created {len(polygons)} valid polygons")
        
        # Check all pairs for overlaps
        overlaps = []
        for i, cluster_a in enumerate(cluster_ids):
            for cluster_b in cluster_ids[i+1:]:
                if cluster_a in polygons and cluster_b in polygons:
                    poly_a = polygons[cluster_a]
                    poly_b = polygons[cluster_b]
                    
                    try:
                        intersection = poly_a.intersection(poly_b)
                        if not intersection.is_empty:
                            # Calculate overlap area
                            overlap_area = intersection.area * (111 ** 2)  # Convert to km²
                            
                            overlaps.append({
                                'type': cluster_type,
                                'cluster_a': cluster_a,
                                'cluster_b': cluster_b,
                                'overlap_area_km2': overlap_area,
                                'area_a_km2': poly_a.area * (111 ** 2),
                                'area_b_km2': poly_b.area * (111 ** 2)
                            })
                            
                    except Exception as e:
                        print(f"Error checking overlap between {cluster_a} and {cluster_b}: {e}")
        
        if len(overlaps) > 0:
            print(f"⚠️  Found {len(overlaps)} overlapping pairs:")
            for overlap in overlaps:
                print(f"  Clusters {overlap['cluster_a']} ↔ {overlap['cluster_b']}: "
                      f"{overlap['overlap_area_km2']:.0f} km² overlap")
        else:
            print(f"✅ No overlaps found in {cluster_type} clusters")
        
        return overlaps
    
    def check_all_overlaps(self):
        """Check overlaps for all cluster types"""
        print(f"\n=== CHECKING CLUSTER OVERLAPS FOR {self.country} ===")
        
        base_path = Path(self.output_dir)
        all_overlaps = []
        
        # Check demand clusters
        demand_points_file = base_path / f'{self.country}_demand_points.csv'
        if demand_points_file.exists():
            demand_points = pd.read_csv(demand_points_file)
            demand_overlaps = self.check_overlaps_within_type(demand_points, 'Demand', 'cluster')
            all_overlaps.extend(demand_overlaps)
        else:
            print(f"⚠️  Demand points file not found: {demand_points_file}")
        
        # Check GEM clusters
        gem_mapping_file = base_path / f'{self.country}_gem_cluster_mapping.csv'
        if gem_mapping_file.exists():
            gem_mapping = pd.read_csv(gem_mapping_file)
            gem_overlaps = self.check_overlaps_within_type(gem_mapping, 'GEM', 'cluster_id')
            all_overlaps.extend(gem_overlaps)
        else:
            print(f"⚠️  GEM mapping file not found: {gem_mapping_file}")
        
        # Check renewable clusters
        renewable_mapping_file = base_path / f'{self.country}_renewable_cluster_mapping.csv'
        if renewable_mapping_file.exists():
            renewable_mapping = pd.read_csv(renewable_mapping_file)
            renewable_overlaps = self.check_overlaps_within_type(renewable_mapping, 'Renewable', 'cluster_id')
            all_overlaps.extend(renewable_overlaps)
        else:
            print(f"⚠️  Renewable mapping file not found: {renewable_mapping_file}")
        
        # Summary
        print(f"\n=== OVERLAP SUMMARY ===")
        if len(all_overlaps) > 0:
            print(f"⚠️  Total overlapping pairs found: {len(all_overlaps)}")
            
            # Group by type
            overlap_by_type = {}
            for overlap in all_overlaps:
                cluster_type = overlap['type']
                if cluster_type not in overlap_by_type:
                    overlap_by_type[cluster_type] = []
                overlap_by_type[cluster_type].append(overlap)
            
            for cluster_type, overlaps in overlap_by_type.items():
                print(f"  {cluster_type}: {len(overlaps)} overlapping pairs")
                total_overlap_area = sum(o['overlap_area_km2'] for o in overlaps)
                print(f"    Total overlap area: {total_overlap_area:.0f} km²")
        else:
            print("✅ No overlaps found in any cluster type!")
        
        return all_overlaps

def main():
    parser = argparse.ArgumentParser(description='Check for overlapping cluster shapes')
    parser.add_argument('--country', required=True, help='Country code (e.g., USA, IND)')
    parser.add_argument('--output-dir', required=True, help='Output directory with cluster files')
    
    args = parser.parse_args()
    
    checker = ClusterOverlapChecker(args.country, args.output_dir)
    overlaps = checker.check_all_overlaps()
    
    if len(overlaps) > 0:
        print(f"\n⚠️  Recommendation: Consider adjusting clustering parameters to reduce overlaps")
    else:
        print(f"\n✅ All cluster shapes are non-overlapping!")

if __name__ == '__main__':
    main()
