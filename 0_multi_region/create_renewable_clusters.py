#!/usr/bin/env python3
"""
Clean, simple renewable clustering algorithm
Clusters grid cells based on total generation potential (solar + wind)
No technology dominance, no complex metrics - just pure clustering
"""

import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN, KMeans
import argparse
import os
import sys

class SimpleRenewableClusterer:
    """Simple renewable clustering based on total generation potential"""
    
    def __init__(self, country):
        self.country = country
        self.combined_data = None
        self.cluster_centers = None
        self.demand_centers = None
        
    def load_renewable_data(self, use_adjusted=True):
        """Load and combine renewable data - simple approach"""
        # Import the REZoning data function
        sys.path.append('..')
        from iso_processing_functions import get_rezoning_data
        
        print(f"Loading renewable data for {self.country}...")
        rez_data = get_rezoning_data(self.country, use_adjusted=use_adjusted, technology='both')
        
        solar_data = rez_data['solar']
        wind_data = rez_data['wind']
        
        print(f"Loaded {len(solar_data)} solar cells, {len(wind_data)} wind cells")
        
        if len(solar_data) == 0 and len(wind_data) == 0:
            print(f"No renewable data found for {self.country}")
            return None
        
        # Simple combination: add generation at each grid cell
        combined = []
        all_grid_cells = set(solar_data['grid_cell'].unique()) | set(wind_data['grid_cell'].unique())
        
        for grid_cell in all_grid_cells:
            solar_row = solar_data[solar_data['grid_cell'] == grid_cell]
            wind_row = wind_data[wind_data['grid_cell'] == grid_cell]
            
            # Get coordinates (prefer solar, fallback to wind)
            if len(solar_row) > 0:
                lat, lng = solar_row.iloc[0]['lat'], solar_row.iloc[0]['lng']
            else:
                lat, lng = wind_row.iloc[0]['lat'], wind_row.iloc[0]['lng']
            
            # Get generation and LCOE
            solar_gen = solar_row.iloc[0]['Generation Potential (GWh)'] if len(solar_row) > 0 else 0
            wind_gen = wind_row.iloc[0]['Generation Potential (GWh)'] if len(wind_row) > 0 else 0
            solar_lcoe = solar_row.iloc[0]['LCOE (USD/MWh)'] if len(solar_row) > 0 else 0
            wind_lcoe = wind_row.iloc[0]['LCOE (USD/MWh)'] if len(wind_row) > 0 else 0
            total_gen = solar_gen + wind_gen
            
            if total_gen > 0:
                combined.append({
                    'grid_cell': grid_cell,
                    'lat': lat,
                    'lng': lng,
                    'solar_generation_gwh': solar_gen,
                    'wind_generation_gwh': wind_gen,
                    'total_generation_gwh': total_gen,
                    'solar_lcoe_usd_mwh': solar_lcoe,
                    'wind_lcoe_usd_mwh': wind_lcoe
                })
        
        self.combined_data = pd.DataFrame(combined)
        
        print(f"Combined {len(self.combined_data)} renewable grid cells")
        print(f"Total: {self.combined_data['total_generation_gwh'].sum():.0f} GWh")
        print(f"Solar: {self.combined_data['solar_generation_gwh'].sum():.0f} GWh")
        print(f"Wind: {self.combined_data['wind_generation_gwh'].sum():.0f} GWh")
        
        return self.combined_data
    
    def load_demand_centers(self, output_dir='output'):
        """Load demand cluster centers for distance calculations"""
        demand_file = f'{output_dir}/{self.country}_region_centers.csv'
        
        if not os.path.exists(demand_file):
            print(f"Warning: Demand centers file not found: {demand_file}")
            print("Using fallback approach without demand-based clustering")
            return None
            
        try:
            self.demand_centers = pd.read_csv(demand_file)
            initial_count = len(self.demand_centers)
            
            # Validate coordinates and filter out invalid ones
            # Remove rows with NaN coordinates
            self.demand_centers = self.demand_centers.dropna(subset=['center_lat', 'center_lng'])
            
            # Define reasonable bounds for the country (generous to include territories)
            if self.country == 'USA':
                lat_min, lat_max = 15, 75  # Includes Hawaii, Alaska, territories
                lng_min, lng_max = -180, -60  # Includes Alaska crossing dateline
            elif self.country == 'CHN':
                lat_min, lat_max = 15, 55
                lng_min, lng_max = 70, 140
            elif self.country == 'IND':
                lat_min, lat_max = 5, 40
                lng_min, lng_max = 65, 100
            else:
                # Very generous global bounds - just remove extreme outliers
                lat_min, lat_max = -90, 90
                lng_min, lng_max = -180, 180
            
            # Filter out coordinates outside reasonable bounds
            valid_coords = (
                (self.demand_centers['center_lat'] >= lat_min) & 
                (self.demand_centers['center_lat'] <= lat_max) &
                (self.demand_centers['center_lng'] >= lng_min) & 
                (self.demand_centers['center_lng'] <= lng_max)
            )
            
            invalid_centers = self.demand_centers[~valid_coords]
            if len(invalid_centers) > 0:
                print(f"Warning: Filtering out {len(invalid_centers)} demand centers with invalid coordinates")
            
            self.demand_centers = self.demand_centers[valid_coords]
            
            if len(self.demand_centers) == 0:
                print("Error: No valid demand centers remaining after filtering")
                self.demand_centers = None
                return None
                
            print(f"Loaded {len(self.demand_centers)} valid demand centers ({initial_count - len(self.demand_centers)} filtered out)")
            return self.demand_centers
            
        except Exception as e:
            print(f"Error loading demand centers: {e}")
            self.demand_centers = None
            return None
    
    def _haversine_distance(self, lat1, lng1, lat2, lng2):
        """Calculate haversine distance between two points in kilometers"""
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(np.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        # Earth radius in kilometers
        r = 6371
        return c * r
    
    def _calculate_distance_to_nearest_demand(self):
        """Calculate distance from each renewable cell to nearest demand center"""
        if self.demand_centers is None:
            print("No demand centers available - using geographic clustering only")
            return None
            
        distances = []
        
        for _, renewable_cell in self.combined_data.iterrows():
            min_distance = float('inf')
            
            for _, demand_center in self.demand_centers.iterrows():
                # Calculate haversine distance in kilometers
                distance = self._haversine_distance(
                    renewable_cell['lat'], renewable_cell['lng'],
                    demand_center['center_lat'], demand_center['center_lng']
                )
                min_distance = min(min_distance, distance)
            
            distances.append(min_distance)
        
        self.combined_data['distance_to_demand_km'] = distances
        
        print(f"Distance to demand range: {min(distances):.1f} - {max(distances):.1f} km")
        return distances
    
    def cluster_renewable_zones(self, n_clusters=5, eps_km=50, output_dir='output'):
        """Distance-based clustering: group by proximity to demand centers"""
        if self.combined_data is None or len(self.combined_data) == 0:
            print("No renewable data available for clustering")
            return None
        
        print(f"Clustering into {n_clusters} renewable zones based on distance to demand...")
        
        # Load demand centers and calculate distances
        self.load_demand_centers(output_dir)
        self._calculate_distance_to_nearest_demand()
        
        if 'distance_to_demand_km' not in self.combined_data.columns:
            print("Falling back to geographic clustering...")
            return self._fallback_geographic_clustering(n_clusters, eps_km)
        
        # Create features for clustering: [lat, lng, distance_to_demand, generation_weight]
        features = []
        
        # Check for valid distance data
        max_dist = self.combined_data['distance_to_demand_km'].max()
        min_dist = self.combined_data['distance_to_demand_km'].min()
        max_gen = self.combined_data['total_generation_gwh'].max()
        

        
        # Handle edge cases
        if max_dist == 0 or np.isnan(max_dist) or np.isinf(max_dist):
            print("Warning: Invalid distance data - using geographic clustering only")
            return self._fallback_geographic_clustering(n_clusters, eps_km)
            
        if max_gen == 0 or np.isnan(max_gen) or np.isinf(max_gen):
            print("Warning: Invalid generation data - using equal weights")
            max_gen = 1
        
        for _, row in self.combined_data.iterrows():
            # Skip rows with invalid coordinates or distances
            if (np.isnan(row['lat']) or np.isnan(row['lng']) or 
                np.isnan(row['distance_to_demand_km']) or np.isinf(row['distance_to_demand_km'])):
                continue
                
            # Normalize distance (0-1 scale) - closer to demand = lower value
            norm_distance = row['distance_to_demand_km'] / max_dist
            
            # Add generation weight (higher generation = more important)
            norm_generation = row['total_generation_gwh'] / max_gen
            
            features.append([
                row['lat'], 
                row['lng'], 
                norm_distance * 2,  # Weight distance heavily
                norm_generation * 0.5  # Secondary weight for generation
            ])
        
        features = np.array(features)
        
        # Check if we have enough valid features
        if len(features) == 0:
            print("Error: No valid renewable grid cells found")
            return None
            

        
        # Use K-means clustering on the multi-dimensional features
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        
        # Create cluster labels for valid rows only
        valid_indices = []
        cluster_labels = []
        
        for i, (_, row) in enumerate(self.combined_data.iterrows()):
            if (not np.isnan(row['lat']) and not np.isnan(row['lng']) and 
                not np.isnan(row['distance_to_demand_km']) and not np.isinf(row['distance_to_demand_km'])):
                valid_indices.append(i)
        

            
        # Fit clustering
        cluster_predictions = kmeans.fit_predict(features)
        
        # Assign cluster labels back to dataframe
        self.combined_data['cluster'] = -1  # Default for invalid rows
        for i, cluster_id in enumerate(cluster_predictions):
            if i < len(valid_indices):
                self.combined_data.iloc[valid_indices[i], self.combined_data.columns.get_loc('cluster')] = cluster_id
        
        print(f"Created {n_clusters} renewable zones based on demand proximity and generation")
        
        # Calculate cluster centers
        self._calculate_cluster_centers()
        
        return self.cluster_centers
    
    def _fallback_geographic_clustering(self, n_clusters, eps_km):
        """Fallback to simple geographic clustering if demand centers not available"""
        print("Using geographic clustering fallback...")
        
        # Filter out invalid coordinates
        valid_mask = (
            ~np.isnan(self.combined_data['lat']) & 
            ~np.isnan(self.combined_data['lng']) &
            ~np.isinf(self.combined_data['lat']) & 
            ~np.isinf(self.combined_data['lng'])
        )
        
        valid_data = self.combined_data[valid_mask].copy()
        
        if len(valid_data) == 0:
            print("Error: No valid coordinates found")
            return None
            

        
        # Use K-means on lat/lng coordinates
        coords = valid_data[['lat', 'lng']].values
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(coords)
        
        # Assign clusters back to original dataframe
        self.combined_data['cluster'] = -1  # Default for invalid rows
        self.combined_data.loc[valid_mask, 'cluster'] = cluster_labels
        
        self._calculate_cluster_centers()
        return self.cluster_centers
    
    def _adjust_to_target_clusters(self, target_clusters):
        """Simple cluster adjustment"""
        current_n = self.combined_data['cluster'].nunique()
        
        while current_n != target_clusters:
            cluster_generations = self.combined_data.groupby('cluster')['total_generation_gwh'].sum()
            
            if current_n > target_clusters:
                # Merge smallest cluster into largest
                smallest = cluster_generations.idxmin()
                largest = cluster_generations.idxmax()
                self.combined_data.loc[self.combined_data['cluster'] == smallest, 'cluster'] = largest
                print(f"Merged cluster {smallest} into {largest}")
                
            else:  # current_n < target_clusters
                # Split largest cluster (simple approach: assign half to new cluster)
                largest = cluster_generations.idxmax()
                largest_points = self.combined_data[self.combined_data['cluster'] == largest]
                
                if len(largest_points) >= 2:
                    # Split in half
                    half_size = len(largest_points) // 2
                    new_cluster_id = self.combined_data['cluster'].max() + 1
                    
                    # Assign first half to new cluster
                    indices_to_reassign = largest_points.index[:half_size]
                    self.combined_data.loc[indices_to_reassign, 'cluster'] = new_cluster_id
                    print(f"Split cluster {largest} into {largest} and {new_cluster_id}")
                else:
                    break
            
            current_n = self.combined_data['cluster'].nunique()
    
    def _calculate_cluster_centers(self):
        """Calculate simple cluster centers"""
        clusters = []
        
        for cluster_id in sorted(self.combined_data['cluster'].unique()):
            # Skip invalid cluster ID -1 (noise/invalid points)
            if cluster_id == -1:
                print(f"Skipping cluster -1 (contains {len(self.combined_data[self.combined_data['cluster'] == cluster_id])} invalid grid cells)")
                continue
                
            cluster_points = self.combined_data[self.combined_data['cluster'] == cluster_id]
            
            # Filter out any remaining NaN coordinates within valid clusters
            valid_coords = cluster_points.dropna(subset=['lat', 'lng'])
            if len(valid_coords) == 0:
                print(f"Skipping cluster {cluster_id} (no valid coordinates)")
                continue
            
            # Generation-weighted centroid
            total_generation = valid_coords['total_generation_gwh'].sum()
            if total_generation == 0:
                print(f"Skipping cluster {cluster_id} (zero generation)")
                continue
                
            weighted_lat = (valid_coords['lat'] * valid_coords['total_generation_gwh']).sum() / total_generation
            weighted_lng = (valid_coords['lng'] * valid_coords['total_generation_gwh']).sum() / total_generation
            
            # Aggregate statistics
            solar_generation = cluster_points['solar_generation_gwh'].sum()
            wind_generation = cluster_points['wind_generation_gwh'].sum()
            
            # Calculate generation-weighted average LCOE and ranges for solar and wind separately
            solar_weighted_lcoe = 0
            wind_weighted_lcoe = 0
            solar_lcoe_min = 0
            solar_lcoe_max = 0
            wind_lcoe_min = 0
            wind_lcoe_max = 0
            
            if solar_generation > 0:
                # Only include grid cells with solar generation for solar LCOE
                solar_cells = cluster_points[cluster_points['solar_generation_gwh'] > 0]
                if len(solar_cells) > 0:
                    solar_weighted_lcoe = (solar_cells['solar_lcoe_usd_mwh'] * solar_cells['solar_generation_gwh']).sum() / solar_generation
                    solar_lcoe_min = solar_cells['solar_lcoe_usd_mwh'].min()
                    solar_lcoe_max = solar_cells['solar_lcoe_usd_mwh'].max()
            
            if wind_generation > 0:
                # Only include grid cells with wind generation for wind LCOE
                wind_cells = cluster_points[cluster_points['wind_generation_gwh'] > 0]
                if len(wind_cells) > 0:
                    wind_weighted_lcoe = (wind_cells['wind_lcoe_usd_mwh'] * wind_cells['wind_generation_gwh']).sum() / wind_generation
                    wind_lcoe_min = wind_cells['wind_lcoe_usd_mwh'].min()
                    wind_lcoe_max = wind_cells['wind_lcoe_usd_mwh'].max()
            
            clusters.append({
                'cluster_id': cluster_id,
                'name': f'RE_{self.country}_{cluster_id}',
                'center_lat': weighted_lat,
                'center_lng': weighted_lng,
                'total_generation_gwh': total_generation,
                'solar_generation_gwh': solar_generation,
                'wind_generation_gwh': wind_generation,
                'solar_weighted_lcoe_usd_mwh': solar_weighted_lcoe,
                'wind_weighted_lcoe_usd_mwh': wind_weighted_lcoe,
                'solar_lcoe_min_usd_mwh': solar_lcoe_min,
                'solar_lcoe_max_usd_mwh': solar_lcoe_max,
                'wind_lcoe_min_usd_mwh': wind_lcoe_min,
                'wind_lcoe_max_usd_mwh': wind_lcoe_max,
                'n_grid_cells': len(cluster_points),
                'generation_share': 0  # Will calculate after
            })
        
        self.cluster_centers = pd.DataFrame(clusters)
        
        # Calculate generation shares
        total_gen = self.cluster_centers['total_generation_gwh'].sum()
        self.cluster_centers['generation_share'] = self.cluster_centers['total_generation_gwh'] / total_gen
        
        return self.cluster_centers
    
    def export_results(self, output_dir='output'):
        """Export cluster results"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Export cluster centers
        centers_file = f'{output_dir}/{self.country}_renewable_cluster_centers.csv'
        self.cluster_centers.to_csv(centers_file, index=False)
        print(f"Exported cluster centers to {centers_file}")
        
        # Export cluster mapping (rename cluster to cluster_id for compatibility)
        # Filter out invalid clusters (-1) and rows with NaN coordinates
        mapping_data = self.combined_data.copy()
        mapping_data = mapping_data.rename(columns={'cluster': 'cluster_id'})
        
        # Remove invalid clusters and NaN coordinates
        initial_count = len(mapping_data)
        mapping_data = mapping_data[mapping_data['cluster_id'] != -1]  # Remove noise cluster
        mapping_data = mapping_data.dropna(subset=['lat', 'lng'])  # Remove NaN coordinates
        final_count = len(mapping_data)
        
        if final_count < initial_count:
            print(f"Filtered out {initial_count - final_count} invalid grid cells from mapping")
        
        mapping_file = f'{output_dir}/{self.country}_renewable_cluster_mapping.csv'
        mapping_data.to_csv(mapping_file, index=False)
        print(f"Exported cluster mapping to {mapping_file}")
        
        # Print summary
        print(f"\n=== {self.country} RENEWABLE ZONES SUMMARY ===")
        print(f"Total zones: {len(self.cluster_centers)}")
        print(f"Total generation: {self.cluster_centers['total_generation_gwh'].sum():.0f} GWh")
        print(f"Solar: {self.cluster_centers['solar_generation_gwh'].sum():.0f} GWh")
        print(f"Wind: {self.cluster_centers['wind_generation_gwh'].sum():.0f} GWh")
        print(f"Total grid cells: {len(self.combined_data)}")
        
        print(f"\nTop zones by generation:")
        top_zones = self.cluster_centers.nlargest(5, 'total_generation_gwh')
        for _, zone in top_zones.iterrows():
            print(f"  {zone['name']}: {zone['total_generation_gwh']:.0f} GWh "
                  f"({zone['generation_share']:.1%}, {zone['n_grid_cells']} cells)")


def main():
    parser = argparse.ArgumentParser(description='Simple renewable clustering')
    parser.add_argument('--country', required=True, help='Country ISO code')
    parser.add_argument('--clusters', type=int, default=5, help='Number of clusters')
    parser.add_argument('--eps-km', type=float, default=50, help='DBSCAN epsilon in km')

    parser.add_argument('--output-dir', default='output', help='Output directory')
    
    args = parser.parse_args()
    
    print(f"Starting simple renewable clustering for {args.country}")
    
    # Create clusterer
    clusterer = SimpleRenewableClusterer(args.country)
    
    # Load data
    if clusterer.load_renewable_data() is None:
        print("No renewable data available")
        return
    
    # Cluster
    clusterer.cluster_renewable_zones(n_clusters=args.clusters, eps_km=args.eps_km, output_dir=args.output_dir)
    
    # Export
    clusterer.export_results(args.output_dir)
    
    print("Clustering complete!")


if __name__ == '__main__':
    main()
