import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
from sklearn.cluster import DBSCAN, KMeans
from collections import defaultdict
import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path to import shared_data_loader
sys.path.append(str(Path(__file__).parent.parent))
from shared_data_loader import get_cache_path
# Add 1_grids to path for importing re_clustering functions
sys.path.append(str(Path(__file__).parent.parent / '1_grids'))
sys.path.append(str(Path(__file__).parent.parent / '1_grids' / 're_clustering'))

from re_clustering.identify_disconnected_regions import (
    identify_disconnected_regions_generation
)

def filter_gem_data_by_status(df_gem, include_announced=True, include_preconstruction=True):
    """
    Centralized GEM data status filtering (same logic as 1_grids pipeline).
    
    Parameters:
    ----------
    df_gem : pd.DataFrame
        GEM data DataFrame with 'Status' and 'Type' columns
    include_announced : bool, default True
        Whether to include plants with 'announced' status
    include_preconstruction : bool, default True
        Whether to include plants with 'pre-construction' status
        
    Returns:
    -------
    pd.DataFrame
        Filtered DataFrame with active/operational plants
    """
    if df_gem.empty or 'Status' not in df_gem.columns:
        return df_gem
    
    # Start with all data
    mask = pd.Series(True, index=df_gem.index)
    
    # Always exclude retired units (all types)
    retired_mask = df_gem['Status'].str.lower().str.startswith('retired')
    mask = mask & ~retired_mask

    # Remove cancelled/shelved units EXCEPT hydropower  
    if 'Type' in df_gem.columns:
        cancelled_shelved_mask = (
            df_gem['Status'].str.lower().str.startswith(('cancelled', 'shelved')) &
            (df_gem['Type'].str.lower() != 'hydropower')
        )
        mask = mask & ~cancelled_shelved_mask
    else:
        # Fallback: exclude all cancelled/shelved if no Type column
        cancelled_shelved_mask = df_gem['Status'].str.lower().str.startswith(('cancelled', 'shelved'))
        mask = mask & ~cancelled_shelved_mask

    # Conditional exclusions based on parameters
    if not include_announced:
        announced_mask = df_gem['Status'].str.lower().str.startswith('announced')
        mask = mask & ~announced_mask
        
    if not include_preconstruction:
        preconstruction_mask = df_gem['Status'].str.lower().str.startswith('pre-construction')
        mask = mask & ~preconstruction_mask
    
    # Apply the combined filter
    filtered_df = df_gem[mask]
    
    return filtered_df

class GEMUnitsClusterer:
    """
    Cluster GEM (Global Energy Monitor) power plant units by technology, capacity and geography
    """
    
    def __init__(self, country_code):
        self.country = country_code
        self.gem_data = None
        self.clusters = None
        self.cluster_centers = None
        self.cluster_mapping = None
        self.rezoning_grid_cells = None
    
    def load_gem_data(self, gem_file='data/existing_stock/Global-Integrated-Power-April-2025.xlsx'):
        """
        Load GEM power plant data for the specified country
        """
        print(f"Loading GEM power plant data...")
        
        try:
            # First try to load from cached pickle file (much faster)
            cache_file = get_cache_path('global_data_cache.pkl')
            if os.path.exists(cache_file):
                try:
                    print("Loading GEM data from cache...")
                    import pickle
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                        if 'df_gem' in cached_data:
                            df = cached_data['df_gem']
                            print(f"Loaded {len(df)} power plant records from cache")
                        else:
                            raise KeyError("df_gem not found in cache")
                except Exception as e:
                    print(f"Cache loading failed ({e}), falling back to Excel file...")
                    df = pd.read_excel(gem_file, sheet_name='Power facilities')
                    print(f"Loaded {len(df)} power plant records from Excel file")
            else:
                # Fallback to Excel file
                print(f"Loading from Excel file: {gem_file}")
                df = pd.read_excel(gem_file, sheet_name='Power facilities')
                print(f"Loaded {len(df)} power plant records from Excel file")
                
        except Exception as e:
            print(f"Error loading GEM file: {e}")
            print("Please ensure the GEM Excel file exists and is accessible")
            return None
        
        # Use the correct country column name from GEM data
        country_col = 'Country/area'
        
        if country_col not in df.columns:
            print(f"Could not find country column '{country_col}' in GEM data. Available columns: {list(df.columns)}")
            return None
        
        # Load country name mapping from VS_mappings
        try:
            mappings_file = os.path.join( 'assumptions', 'VS_mappings.xlsx')
            region_map = pd.read_excel(mappings_file, sheet_name='kinesys_region_map')
            
            # Create country name mapping from the region map
            country_names = {}
            for _, row in region_map.iterrows():
                iso_code = row['iso']
                country_name = row['country']
                aliases = str(row['Alias']) if pd.notna(row['Alias']) else ''
                
                # Create list of possible names for this country
                possible_names = [country_name]
                
                # Add aliases if available
                if aliases and aliases != 'nan':
                    alias_list = [alias.strip() for alias in aliases.split('~') if alias.strip()]
                    possible_names.extend(alias_list)
                
                country_names[iso_code] = possible_names
                
        except Exception as e:
            print(f"Warning: Could not load country mappings from VS_mappings.xlsx: {e}")
            print("Falling back to basic country name mapping")
            # Fallback to basic mapping
            country_names = {
                'IND': ['India'], 'CHN': ['China'], 'USA': ['United States'],
                'DEU': ['Germany'], 'ITA': ['Italy'], 'CHE': ['Switzerland'],
                'AUS': ['Australia'], 'JPN': ['Japan'], 'ZAF': ['South Africa'],
                'NZL': ['New Zealand'], 'BRA': ['Brazil'], 'FRA': ['France'],
                'GBR': ['United Kingdom'], 'ESP': ['Spain'], 'CAN': ['Canada'],
                'MEX': ['Mexico'], 'ARG': ['Argentina'], 'RUS': ['Russia']
            }
        
        if self.country in country_names:
            country_filter = df[country_col].isin(country_names[self.country])
        else:
            print(f"No country name mapping for {self.country}")
            return None
        
        # Apply country filter first
        country_data = df[country_filter].copy()
        
        # Filter using the same logic as 1_grids pipeline
        # This includes: operating, under construction, pre-construction, announced
        # Excludes: retired, cancelled/shelved (except hydropower)
        if 'Status' in country_data.columns:
            initial_count = len(country_data)
            country_data = filter_gem_data_by_status(country_data, include_announced=True, include_preconstruction=True)
            filtered_count = len(country_data)
            print(f"Filtered to active plants (same as 1_grids): {filtered_count}/{initial_count} plants")
        
        self.gem_data = country_data
        
        if len(self.gem_data) == 0:
            print(f"No GEM power plant data found for {self.country}")
            return None
        
        # Clean and prepare data - try common column names
        self._clean_gem_data()
        
        print(f"Loaded {len(self.gem_data)} power plants for {self.country}")
        if 'capacity_mw' in self.gem_data.columns:
            print(f"Total capacity: {self.gem_data['capacity_mw'].sum():.0f} MW")
        
        # Show technology breakdown
        if 'technology' in self.gem_data.columns:
            tech_summary = self.gem_data.groupby('technology').agg({
                'capacity_mw': ['count', 'sum']
            }).round(0)
            tech_summary.columns = ['count', 'capacity_mw']
            print("\nTechnology breakdown:")
            print(tech_summary)
        
        return self.gem_data

    def filter_gem_data_for_disconnected_regions(self):
        """
        Filter GEM data for disconnected regions
        """
        result = identify_disconnected_regions_generation(self.gem_data, self.country, plot=False)
        self.gem_data = self.gem_data[self.gem_data['gem_unit_id'].isin(result['main_continental_units'])]
        return self.gem_data
    
    def load_rezoning_data(self, rezoning_file='../data/REZoning/REZoning_Solar.csv'):
        """
        Load REZoning grid cell data for coordinate mapping
        (Solar and wind share the same grid_cell coordinates)
        """
        print("Loading REZoning grid cell data for coordinate mapping...")
        
        try:
            # Load REZoning data (solar file has all grid cells with coordinates)
            df = pd.read_csv(rezoning_file)
            print(f"Loaded {len(df)} REZoning grid cells")
            
            # Filter for country
            if 'ISO' in df.columns:
                df = df[df['ISO'] == self.country]
                print(f"Filtered to {len(df)} grid cells for {self.country}")
            
            # Keep only unique grid cells with coordinates
            if 'grid_cell' in df.columns and 'lat' in df.columns and 'lng' in df.columns:
                self.rezoning_grid_cells = df[['grid_cell', 'lat', 'lng']].drop_duplicates(subset=['grid_cell'])
                print(f"Using {len(self.rezoning_grid_cells)} unique grid cells for mapping")
            else:
                print("Required columns (grid_cell, lat, long) not found in REZoning data")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error loading REZoning data: {e}")
            print("Grid cell mapping will not be available")
            return False
    
    def _clean_gem_data(self):
        """
        Clean and standardize GEM data columns
        """
        # Map GEM column names to standard names
        column_mappings = {
            'capacity_mw': ['Capacity (MW)'],
            'technology': ['Technology', 'Fuel'],
            'status': ['Status'],
            'lat': ['Latitude'],
            'lng': ['Longitude'],
            'plant_name': ['Plant / Project name', 'Unit / Phase name'],
            'owner': ['Owner'],
            'year_online': ['Start year'],
            'gem_unit_id': ['GEM unit/phase ID']
        }
        
        # Map columns to standard names
        for standard_name, possible_names in column_mappings.items():
            for col_name in possible_names:
                if col_name in self.gem_data.columns:
                    if standard_name not in self.gem_data.columns:
                        self.gem_data[standard_name] = self.gem_data[col_name]
                    break
        
        # Clean capacity data
        if 'capacity_mw' in self.gem_data.columns:
            self.gem_data['capacity_mw'] = pd.to_numeric(self.gem_data['capacity_mw'], errors='coerce')
            self.gem_data = self.gem_data.dropna(subset=['capacity_mw'])
            self.gem_data = self.gem_data[self.gem_data['capacity_mw'] > 0]
        
        # Clean coordinates
        if 'lat' in self.gem_data.columns and 'lng' in self.gem_data.columns:
            initial_count = len(self.gem_data)
            
            self.gem_data['lat'] = pd.to_numeric(self.gem_data['lat'], errors='coerce')
            self.gem_data['lng'] = pd.to_numeric(self.gem_data['lng'], errors='coerce')
            
            # Remove plants without coordinates
            coord_mask = self.gem_data['lat'].notna() & self.gem_data['lng'].notna()
            missing_coords = self.gem_data[~coord_mask]
            if len(missing_coords) > 0:
                print(f"Removed {len(missing_coords)} plants with missing coordinates")
            
            self.gem_data = self.gem_data[coord_mask]
            
            # Validate coordinate ranges and log invalid ones
            valid_lat = (self.gem_data['lat'] >= -90) & (self.gem_data['lat'] <= 90)
            valid_lng = (self.gem_data['lng'] >= -180) & (self.gem_data['lng'] <= 180)
            
            invalid_coords = self.gem_data[~(valid_lat & valid_lng)]
            if len(invalid_coords) > 0:
                print(f"Found {len(invalid_coords)} plants with invalid coordinates:")
                for _, plant in invalid_coords.iterrows():
                    name = plant.get('plant_name', plant.get('Plant / Project name', 'Unknown'))
                    lat, lng = plant['lat'], plant['lng']
                    print(f"  - {name}: ({lat}, {lng})")
                
                # Remove plants with invalid coordinates
                self.gem_data = self.gem_data[valid_lat & valid_lng]
                print(f"Removed {len(invalid_coords)} plants with invalid coordinates")
            
            final_count = len(self.gem_data)
            if final_count < initial_count:
                print(f"Coordinate cleaning: {final_count}/{initial_count} plants retained")
        
        # Standardize technology names
        if 'technology' in self.gem_data.columns:
            self.gem_data['technology'] = self.gem_data['technology'].fillna('Unknown')
            
            # Group similar technologies
            tech_mapping = {
                'coal': ['Coal', 'Hard Coal', 'Lignite', 'Sub-bituminous', 'Bituminous'],
                'gas': ['Natural Gas', 'Gas', 'CCGT', 'OCGT', 'Combined Cycle', 'Gas Turbine', 
                       'gas turbine', 'combined cycle'],
                'nuclear': ['Nuclear', 'Uranium', 'pressurized water reactor', 'boiling water reactor'],
                'hydro': ['Hydro', 'Hydroelectric', 'Pumped Storage', 'Run-of-River', 
                         'run-of-river', 'pumped storage', 'conventional storage', 
                         'conventional and run-of-river'],
                'wind': ['Wind', 'Onshore Wind', 'Offshore Wind', 'Onshore'],
                'solar': ['Solar', 'Solar PV', 'Solar Thermal', 'Photovoltaic', 'PV', 'Assumed PV'],
                'oil': ['Oil', 'Diesel', 'Heavy Fuel Oil', 'Residual Fuel Oil'],
                'biomass': ['Biomass', 'Wood', 'Bagasse', 'Biogas'],
                'geothermal': ['Geothermal'],
                'other': ['Other', 'Unknown', 'Waste', 'Tidal', 'Wave', 'unknown', 'unknown type']
            }
            
            # Apply technology grouping
            tech_groups = {}
            for group, techs in tech_mapping.items():
                for tech in techs:
                    tech_groups[tech] = group
            
            self.gem_data['tech_group'] = self.gem_data['technology'].map(tech_groups).fillna('other')
        
        # Status filtering is now done earlier in load_gem_data()
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate haversine distance between two points in km
        """
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
    
    def _find_nearest_grid_cell(self, lat, lng):
        """
        Find the nearest REZoning grid_cell for a given lat/lng coordinate
        Uses vectorized operations for speed
        """
        if self.rezoning_grid_cells is None or len(self.rezoning_grid_cells) == 0:
            return None
        
        # Vectorized distance calculation using numpy
        import numpy as np
        
        # Convert to radians
        lat_rad = np.radians(lat)
        lng_rad = np.radians(lng)
        grid_lats_rad = np.radians(self.rezoning_grid_cells['lat'].values)
        grid_lngs_rad = np.radians(self.rezoning_grid_cells['lng'].values)
        
        # Haversine formula vectorized
        dlat = grid_lats_rad - lat_rad
        dlng = grid_lngs_rad - lng_rad
        
        a = np.sin(dlat/2)**2 + np.cos(lat_rad) * np.cos(grid_lats_rad) * np.sin(dlng/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        distances = 6371 * c  # Earth radius in km
        
        # Find minimum distance index
        min_idx = np.argmin(distances)
        return self.rezoning_grid_cells.iloc[min_idx]['grid_cell']
    
    def cluster_gem_units(self, method='voronoi', n_clusters=None, eps_km=30, by_technology=False):
        """
        Cluster GEM power plant units using Voronoi diagrams for non-overlapping regions
        """
        if self.gem_data is None or len(self.gem_data) == 0:
            print("No GEM data available for clustering")
            return None
        
        print(f"\nClustering GEM power plants (target: {n_clusters or 'auto'}, method: {method})")
        
        if method == 'voronoi' and n_clusters:
            # Use Voronoi clustering for non-overlapping regions
            self._cluster_voronoi_all_plants(n_clusters)
        elif by_technology:
            # Cluster separately by technology group
            self._cluster_by_technology(method, n_clusters, eps_km)
        else:
            # Cluster all plants together
            self._cluster_all_plants(method, n_clusters, eps_km)
        
        # Calculate cluster centers and statistics
        self._calculate_cluster_centers()
        
        # Create cluster mapping
        self._create_cluster_mapping()
        
        return self.clusters
    
    def _cluster_by_technology(self, method, n_clusters, eps_km):
        """
        Cluster plants separately by technology group
        """
        if 'tech_group' not in self.gem_data.columns:
            print("No technology grouping available, clustering all plants together")
            self._cluster_all_plants(method, n_clusters, eps_km)
            return
        
        # Initialize cluster column
        self.gem_data['cluster'] = -1
        cluster_id_counter = 0
        
        # Cluster each technology separately
        for tech_group in self.gem_data['tech_group'].unique():
            tech_plants = self.gem_data[self.gem_data['tech_group'] == tech_group].copy()
            
            if len(tech_plants) < 2:
                # Single plant gets its own cluster
                self.gem_data.loc[tech_plants.index, 'cluster'] = cluster_id_counter
                cluster_id_counter += 1
                continue
            
            print(f"  Clustering {len(tech_plants)} {tech_group} plants...")
            
            # Determine target clusters for this technology
            if n_clusters:
                tech_target = max(1, int(n_clusters * len(tech_plants) / len(self.gem_data)))
            else:
                tech_target = None
            
            # Apply clustering
            if method == 'hybrid':
                tech_clusters = self._cluster_hybrid_tech(tech_plants, eps_km, tech_target)
            else:
                tech_clusters = self._cluster_kmeans_tech(tech_plants, tech_target or 3)
            
            # Assign cluster IDs with offset
            tech_clusters = tech_clusters + cluster_id_counter
            self.gem_data.loc[tech_plants.index, 'cluster'] = tech_clusters
            
            cluster_id_counter = tech_clusters.max() + 1
    
    def _cluster_voronoi_all_plants(self, n_clusters):
        """
        Create Voronoi-based non-overlapping clusters for all plants
        """
        from scipy.spatial import Voronoi
        from scipy.spatial.distance import cdist
        from sklearn.cluster import KMeans
        
        print(f"Creating {n_clusters} Voronoi clusters for all plants...")
        
        # Step 1: Use K-means to find optimal cluster centers
        coords = self.gem_data[['lng', 'lat']].values
        weights = self.gem_data['capacity_mw'].values
        
        # Create weighted coordinates by repeating points based on capacity
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
        
        self.gem_data['cluster'] = cluster_assignments
        
        # Mark that Voronoi clustering was used (to skip minimum size enforcement)
        self._used_voronoi = True
        
        print(f"Assigned {len(self.gem_data)} plants to {n_clusters} Voronoi regions")
    
    def _cluster_all_plants(self, method, n_clusters, eps_km):
        """
        Cluster all plants together regardless of technology
        """
        if method == 'hybrid':
            self._cluster_hybrid_all(eps_km, n_clusters)
        else:
            self._cluster_kmeans_all(n_clusters or 5)
    
    def _cluster_hybrid_tech(self, tech_plants, eps_km, target_clusters):
        """
        DBSCAN clustering for a specific technology
        """
        coords = np.radians(tech_plants[['lat', 'lng']].values)
        
        # Use DBSCAN with haversine metric
        eps_radians = eps_km / 6371  # Earth radius in km
        clustering = DBSCAN(eps=eps_radians, min_samples=1, metric='haversine').fit(coords)
        
        clusters = clustering.labels_
        
        # Handle noise points - assign to nearest cluster
        noise_mask = clusters == -1
        if noise_mask.sum() > 0:
            for i, is_noise in enumerate(noise_mask):
                if is_noise:
                    # Find nearest non-noise point
                    non_noise_indices = np.where(~noise_mask)[0]
                    if len(non_noise_indices) > 0:
                        distances = []
                        for j in non_noise_indices:
                            dist = self._haversine_distance(
                                tech_plants.iloc[i]['lat'], tech_plants.iloc[i]['lng'],
                                tech_plants.iloc[j]['lat'], tech_plants.iloc[j]['lng']
                            )
                            distances.append(dist)
                        nearest_idx = non_noise_indices[np.argmin(distances)]
                        clusters[i] = clusters[nearest_idx]
        
        # Adjust to target clusters if specified
        if target_clusters and len(np.unique(clusters)) != target_clusters:
            clusters = self._adjust_tech_clusters(tech_plants, clusters, target_clusters)
        
        return clusters
    
    def _cluster_hybrid_all(self, eps_km, target_clusters):
        """
        DBSCAN clustering for all plants
        """
        coords = np.radians(self.gem_data[['lat', 'lng']].values)
        
        # Use DBSCAN with haversine metric
        eps_radians = eps_km / 6371
        clustering = DBSCAN(eps=eps_radians, min_samples=2, metric='haversine').fit(coords)
        
        self.gem_data['cluster'] = clustering.labels_
        
        # Handle noise points
        noise_mask = self.gem_data['cluster'] == -1
        if noise_mask.sum() > 0:
            for idx in self.gem_data[noise_mask].index:
                point = self.gem_data.loc[idx]
                non_noise = self.gem_data[~noise_mask]
                if len(non_noise) > 0:
                    distances = non_noise.apply(
                        lambda row: self._haversine_distance(
                            point['lat'], point['lng'],
                            row['lat'], row['lng']
                        ), axis=1
                    )
                    nearest_idx = distances.idxmin()
                    self.gem_data.loc[idx, 'cluster'] = non_noise.loc[nearest_idx, 'cluster']
        
        # Adjust to target clusters if specified
        if target_clusters:
            self._adjust_all_clusters(target_clusters)
    
    def _cluster_kmeans_tech(self, tech_plants, n_clusters):
        """
        K-means clustering for a specific technology
        """
        coords = tech_plants[['lat', 'lng']].values
        weights = tech_plants['capacity_mw'].values
        
        # Weighted K-means
        weighted_coords = []
        for coord, weight in zip(coords, weights):
            n_repeats = max(1, int(weight / weights.mean()))
            weighted_coords.extend([coord] * n_repeats)
        
        weighted_coords = np.array(weighted_coords)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(weighted_coords)
        
        # Assign clusters to original points
        clusters = []
        for coord in coords:
            distances = np.sum((kmeans.cluster_centers_ - coord)**2, axis=1)
            clusters.append(np.argmin(distances))
        
        return np.array(clusters)
    
    def _cluster_kmeans_all(self, n_clusters):
        """
        K-means clustering for all plants
        """
        coords = self.gem_data[['lat', 'lng']].values
        weights = self.gem_data['capacity_mw'].values
        
        # Weighted K-means
        weighted_coords = []
        for coord, weight in zip(coords, weights):
            n_repeats = max(1, int(weight / weights.mean()))
            weighted_coords.extend([coord] * n_repeats)
        
        weighted_coords = np.array(weighted_coords)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(weighted_coords)
        
        # Map back to original points
        self.gem_data['cluster'] = 0
        for i, coord in enumerate(coords):
            distances = np.sum((kmeans.cluster_centers_ - coord)**2, axis=1)
            self.gem_data.iloc[i, self.gem_data.columns.get_loc('cluster')] = np.argmin(distances)
    
    def _adjust_tech_clusters(self, tech_plants, clusters, target_clusters):
        """
        Adjust number of clusters for a technology to target
        """
        current_n = len(np.unique(clusters))
        
        if current_n == target_clusters:
            return clusters
        
        # Simple approach: use K-means to get exact number
        coords = tech_plants[['lat', 'lng']].values
        kmeans = KMeans(n_clusters=target_clusters, random_state=42)
        new_clusters = kmeans.fit_predict(coords)
        
        return new_clusters
    
    def _adjust_all_clusters(self, target_clusters):
        """
        Adjust total number of clusters to target
        """
        current_n = self.gem_data['cluster'].nunique()
        
        while current_n != target_clusters:
            cluster_capacities = self.gem_data.groupby('cluster')['capacity_mw'].sum()
            
            if current_n > target_clusters:
                # Merge smallest cluster
                smallest = cluster_capacities.idxmin()
                smallest_plants = self.gem_data[self.gem_data['cluster'] == smallest]
                
                # Find nearest cluster by centroid distance
                smallest_center_lat = smallest_plants['lat'].mean()
                smallest_center_lng = smallest_plants['lng'].mean()
                
                min_dist = float('inf')
                nearest_cluster = None
                
                for cluster_id in cluster_capacities.index:
                    if cluster_id == smallest:
                        continue
                    cluster_plants = self.gem_data[self.gem_data['cluster'] == cluster_id]
                    cluster_center_lat = cluster_plants['lat'].mean()
                    cluster_center_lng = cluster_plants['lng'].mean()
                    
                    dist = self._haversine_distance(
                        smallest_center_lat, smallest_center_lng,
                        cluster_center_lat, cluster_center_lng
                    )
                    
                    if dist < min_dist:
                        min_dist = dist
                        nearest_cluster = cluster_id
                
                # Merge
                self.gem_data.loc[self.gem_data['cluster'] == smallest, 'cluster'] = nearest_cluster
                
            else:  # current_n < target_clusters
                # Split largest cluster
                largest = cluster_capacities.idxmax()
                largest_plants = self.gem_data[self.gem_data['cluster'] == largest]
                
                if len(largest_plants) >= 2:
                    coords = largest_plants[['lat', 'lng']].values
                    kmeans = KMeans(n_clusters=2, random_state=42)
                    sub_labels = kmeans.fit_predict(coords)
                    
                    new_cluster_id = self.gem_data['cluster'].max() + 1
                    indices_to_change = largest_plants.index[sub_labels == 1]
                    self.gem_data.loc[indices_to_change, 'cluster'] = new_cluster_id
                else:
                    break
            
            current_n = self.gem_data['cluster'].nunique()
    
    def _calculate_cluster_centers(self):
        """
        Calculate capacity-weighted cluster centers and statistics
        """
        clusters = []
        
        for cluster_id in sorted(self.gem_data['cluster'].unique()):
            cluster_plants = self.gem_data[self.gem_data['cluster'] == cluster_id]
            
            # Capacity-weighted centroid
            total_capacity = cluster_plants['capacity_mw'].sum()
            weighted_lat = (cluster_plants['lat'] * cluster_plants['capacity_mw']).sum() / total_capacity
            weighted_lng = (cluster_plants['lng'] * cluster_plants['capacity_mw']).sum() / total_capacity
            
            # Technology breakdown
            tech_breakdown = cluster_plants.groupby('tech_group')['capacity_mw'].sum()
            dominant_tech = tech_breakdown.idxmax()
            tech_diversity = len(tech_breakdown)
            
            # Plant statistics
            avg_plant_size = cluster_plants['capacity_mw'].mean()
            largest_plant = cluster_plants['capacity_mw'].max()
            
            # Age statistics if available
            avg_age = None
            if 'year_online' in cluster_plants.columns:
                current_year = 2025
                ages = current_year - pd.to_numeric(cluster_plants['year_online'], errors='coerce')
                avg_age = ages.mean()
            
            # Get geographic name for the cluster
            geographic_name = self._get_geographic_name(weighted_lat, weighted_lng)
            
            clusters.append({
                'cluster_id': int(cluster_id),
                'name': f"GEN_{geographic_name}_{dominant_tech}_{cluster_id}",
                'center_lat': weighted_lat,
                'center_lng': weighted_lng,
                'total_capacity_mw': total_capacity,
                'n_plants': len(cluster_plants),
                'dominant_tech': dominant_tech,
                'tech_diversity': tech_diversity,
                'avg_plant_size_mw': avg_plant_size,
                'largest_plant_mw': largest_plant,
                'avg_age_years': avg_age,
                'capacity_share': 0,  # Will calculate after
                'tech_breakdown': tech_breakdown.to_dict()
            })
        
        self.cluster_centers = pd.DataFrame(clusters)
        self.cluster_centers['capacity_share'] = (
            self.cluster_centers['total_capacity_mw'] / 
            self.cluster_centers['total_capacity_mw'].sum()
        )
        
        # Enforce minimum cluster size (configurable, default 1% of total capacity)
        # Skip for Voronoi clustering to preserve non-overlapping property
        if not getattr(self, '_used_voronoi', False):
            min_share = getattr(self, 'min_share', 0.01)
            self._enforce_minimum_cluster_size(min_share=min_share)
        else:
            print("Skipping minimum cluster size enforcement for Voronoi clustering (preserves non-overlapping property)")
        
        return self.cluster_centers
    
    def _get_geographic_name(self, lat, lng):
        """
        Get geographic name (state/region) for cluster center coordinates
        Uses the same geographic regions as renewable clustering
        """
        # Same geographic regions as in renewable clustering
        country_regions = {
            'IND': {
                'regions': [
                    {'name': 'Rajasthan', 'lat_range': (24, 30), 'lng_range': (69, 78)},
                    {'name': 'Gujarat', 'lat_range': (20, 25), 'lng_range': (68, 75)},
                    {'name': 'Maharashtra', 'lat_range': (15, 22), 'lng_range': (72, 81)},
                    {'name': 'Karnataka', 'lat_range': (11, 19), 'lng_range': (74, 78)},
                    {'name': 'Tamil_Nadu', 'lat_range': (8, 14), 'lng_range': (76, 81)},
                    {'name': 'Andhra_Pradesh', 'lat_range': (12, 20), 'lng_range': (77, 85)},
                    {'name': 'Madhya_Pradesh', 'lat_range': (21, 27), 'lng_range': (74, 83)},
                    {'name': 'Uttar_Pradesh', 'lat_range': (24, 31), 'lng_range': (77, 85)},
                    {'name': 'Haryana', 'lat_range': (27, 31), 'lng_range': (74, 78)},
                    {'name': 'Punjab', 'lat_range': (29, 33), 'lng_range': (73, 77)}
                ]
            },
            'USA': {
                'regions': [
                    {'name': 'California', 'lat_range': (32, 42), 'lng_range': (-125, -114)},
                    {'name': 'Texas', 'lat_range': (25, 37), 'lng_range': (-107, -93)},
                    {'name': 'Arizona', 'lat_range': (31, 37), 'lng_range': (-115, -109)},
                    {'name': 'Nevada', 'lat_range': (35, 42), 'lng_range': (-120, -114)},
                    {'name': 'New_Mexico', 'lat_range': (31, 37), 'lng_range': (-109, -103)},
                    {'name': 'Colorado', 'lat_range': (37, 41), 'lng_range': (-109, -102)},
                    {'name': 'Utah', 'lat_range': (37, 42), 'lng_range': (-114, -109)},
                    {'name': 'Florida', 'lat_range': (24, 31), 'lng_range': (-88, -80)}
                ]
            }
        }
        
        # Get regions for this country
        if self.country in country_regions:
            for region in country_regions[self.country]['regions']:
                lat_min, lat_max = region['lat_range']
                lng_min, lng_max = region['lng_range']
                
                if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
                    return region['name']
        
        # Fallback to generic geographic naming
        if lat > 0:
            ns = 'North' if lat > 30 else 'Central' if lat > 15 else 'South'
        else:
            ns = 'North' if lat > -15 else 'Central' if lat > -30 else 'South'
        
        if lng > 0:
            ew = 'East' if lng > 90 else 'Central' if lng > 45 else 'West'
        else:
            ew = 'East' if lng > -45 else 'Central' if lng > -90 else 'West'
        
        return f"{ns}_{ew}"
    
    def _enforce_minimum_cluster_size(self, min_share=0.01):
        """
        Merge clusters smaller than min_share (1%) into nearest clusters
        """
        if self.cluster_centers is None or len(self.cluster_centers) == 0:
            return
        
        print(f"\nEnforcing minimum cluster size ({min_share*100:.1f}% of total capacity)...")
        
        total_capacity = self.cluster_centers['total_capacity_mw'].sum()
        min_capacity = total_capacity * min_share
        
        # Find clusters below minimum size
        small_clusters = self.cluster_centers[self.cluster_centers['total_capacity_mw'] < min_capacity]
        
        if len(small_clusters) == 0:
            print("All clusters meet minimum size requirement")
            return
        
        print(f"Found {len(small_clusters)} clusters below minimum size ({min_capacity:.0f} MW)")
        
        # Merge small clusters into nearest larger clusters
        for _, small_cluster in small_clusters.iterrows():
            small_id = small_cluster['cluster_id']
            
            # Find nearest cluster that meets minimum size
            large_clusters = self.cluster_centers[
                (self.cluster_centers['total_capacity_mw'] >= min_capacity) & 
                (self.cluster_centers['cluster_id'] != small_id)
            ]
            
            if len(large_clusters) == 0:
                continue  # No large clusters to merge into
            
            # Calculate distances to all large clusters
            distances = []
            for _, large_cluster in large_clusters.iterrows():
                dist = self._haversine_distance(
                    small_cluster['center_lat'], small_cluster['center_lng'],
                    large_cluster['center_lat'], large_cluster['center_lng']
                )
                distances.append((dist, large_cluster['cluster_id']))
            
            # Merge into nearest large cluster
            nearest_dist, nearest_id = min(distances)
            
            # Update the gem_data cluster assignments
            self.gem_data.loc[self.gem_data['cluster'] == small_id, 'cluster'] = nearest_id
            
            print(f"  Merged cluster {small_id} ({small_cluster['total_capacity_mw']:.0f} MW) "
                  f"into cluster {nearest_id} (distance: {nearest_dist:.0f} km)")
        
        # Recalculate cluster centers after merging
        self._calculate_cluster_centers()
    
    def _create_cluster_mapping(self):
        """
        Create detailed cluster to plant mapping
        """
        mapping = []
        total_plants = len(self.gem_data)
        
        print(f"\nCreating cluster mapping with grid_cell assignment for {total_plants} plants...")
        
        for i, (_, row) in enumerate(self.gem_data.iterrows()):
            # Progress indicator
            if i % 500 == 0 or i == total_plants - 1:
                progress = (i + 1) / total_plants * 100
                print(f"  Progress: {i+1}/{total_plants} plants ({progress:.1f}%)")
            
            # Find nearest REZoning grid_cell for this power plant
            nearest_grid_cell = self._find_nearest_grid_cell(row['lat'], row['lng'])
            
            mapping.append({
                'bus_id': 'gen' + str(int(row['cluster'])),
                'cluster_id': int(row['cluster']),
                'GEM location ID': row.get('GEM location ID', 'Unknown'),
                'gem_unit_id': row.get('gem_unit_id', 'Unknown'),
                'plant_name': row.get('plant_name', 'Unknown'),
                'lat': row['lat'],
                'lng': row['lng'],
                'capacity_mw': row['capacity_mw'],
                'technology': row.get('technology', 'Unknown'),
                'tech_group': row.get('tech_group', 'other'),
                'status': row.get('status', 'Unknown'),
                'owner': row.get('owner', 'Unknown'),
                'year_online': row.get('year_online', None),
                'nearest_grid_cell': nearest_grid_cell
            })
        
        self.cluster_mapping = pd.DataFrame(mapping)
        return self.cluster_mapping
    
    def estimate_generation_to_demand_ntc(self, demand_regions_file=None, use_osm_grid=True):
        """
        Estimate NTC between generation clusters and demand regions
        Enhanced with OSM grid infrastructure data when available
        """
        if self.cluster_centers is None:
            print("No generation cluster centers available for NTC estimation")
            return None
        
        # Load demand regions data
        if demand_regions_file is None:
            demand_regions_file = f'output/{self.country}_region_centers.csv'
        
        try:
            if not os.path.exists(demand_regions_file):
                print(f"Demand regions file not found: {demand_regions_file}")
                print("Please run create_regions.py first to generate demand regions")
                return None
            
            demand_regions = pd.read_csv(demand_regions_file)
            print(f"Loaded {len(demand_regions)} demand regions from {demand_regions_file}")
        except Exception as e:
            print(f"Error loading demand regions: {e}")
            return None
        
        # Load OSM grid infrastructure if requested
        grid_infrastructure = None
        if use_osm_grid:
            grid_file = f'cache/industrial/{self.country.lower()}_grid_infrastructure.csv'
            try:
                if os.path.exists(grid_file):
                    grid_infrastructure = pd.read_csv(grid_file)
                    substations = grid_infrastructure[grid_infrastructure['type'] == 'substation']
                    print(f"Loaded {len(substations)} substations from OSM data for NTC enhancement")
                else:
                    print(f"OSM grid file not found: {grid_file}")
                    print("Using distance-based NTC estimation")
            except Exception as e:
                print(f"Error loading OSM grid data: {e}")
                print("Falling back to distance-based NTC estimation")
        
        print("\nEstimating NTC between generation clusters and demand regions...")
        if grid_infrastructure is not None:
            print("Using OSM grid infrastructure data for enhanced NTC estimation")
        
        ntc_connections = []
        
        for _, gen_cluster in self.cluster_centers.iterrows():
            for _, demand_region in demand_regions.iterrows():
                
                # Calculate distance between generation cluster and demand region
                distance_km = self._haversine_distance(
                    gen_cluster['center_lat'], gen_cluster['center_lng'],
                    demand_region['center_lat'], demand_region['center_lng']
                )
                
                # Base NTC estimation based on generation capacity and demand
                gen_capacity = gen_cluster['total_capacity_mw']
                demand_load = demand_region['total_demand']
                
                # Estimate transmission need as fraction of generation capacity
                transmission_need = min(gen_capacity * 0.8, demand_load * 100)  # 80% of generation or scaled demand
                
                # Enhanced NTC calculation using OSM grid infrastructure
                if grid_infrastructure is not None:
                    # Count substations in transmission corridor (within 50km of line)
                    corridor_substations = self._count_corridor_substations(
                        grid_infrastructure, 
                        gen_cluster['center_lat'], gen_cluster['center_lng'],
                        demand_region['center_lat'], demand_region['center_lng'],
                        corridor_width_km=50
                    )
                    
                    # Grid infrastructure factor based on substation density
                    substation_density = corridor_substations / max(1, distance_km / 100)
                    grid_factor = min(2.0, 0.5 + substation_density * 0.1)
                    
                    # Distance penalty with grid infrastructure consideration
                    distance_factor = max(0.1, grid_factor / (1 + distance_km / 200))
                    
                    substation_info = {
                        'corridor_substations': corridor_substations,
                        'substation_density': round(substation_density, 2),
                        'grid_factor': round(grid_factor, 2)
                    }
                    
                else:
                    # Fallback to simple distance penalty
                    distance_factor = max(0.1, 1 / (1 + distance_km / 200))
                
                # Country-specific grid strength factors
                country_factors = {
                    'CHE': 1.2, 'DEU': 1.1, 'ITA': 1.0, 'USA': 0.8, 'IND': 0.6,
                    'CHN': 0.7, 'JPN': 1.1, 'AUS': 0.5, 'ZAF': 0.7, 'NZL': 0.9, 'BRA': 0.6
                }
                
                country_factor = country_factors.get(self.country, 1.0)
                
                # Calculate estimated NTC
                estimated_ntc = transmission_need * distance_factor * country_factor
                
                # Practical limits: 50 MW minimum, 5000 MW maximum for conventional generation
                estimated_ntc = max(50, min(5000, estimated_ntc))
                
                connection_data = {
                    'from_generation_cluster': gen_cluster['name'],
                    'to_demand_region': demand_region['name'],
                    'from_gen_id': int(gen_cluster['cluster_id']),
                    'to_demand_id': int(demand_region['cluster_id']),
                    'distance_km': round(distance_km, 1),
                    'estimated_ntc_mw': round(estimated_ntc, 0),
                    'gen_capacity_mw': round(gen_capacity, 0),
                    'demand_load': round(demand_load, 1),
                    'capacity_utilization': round(estimated_ntc / gen_capacity * 100, 1) if gen_capacity > 0 else 0,
                    'dominant_tech': gen_cluster['dominant_tech'],
                    'n_plants': gen_cluster['n_plants'],
                    'from_lat': gen_cluster['center_lat'],
                    'from_lng': gen_cluster['center_lng'],
                    'to_lat': demand_region['center_lat'],
                    'to_lng': demand_region['center_lng']
                }
                
                # Add OSM grid infrastructure data if available
                if grid_infrastructure is not None and 'substation_info' in locals():
                    connection_data.update(substation_info)
                else:
                    connection_data.update({
                        'corridor_substations': 0,
                        'substation_density': 0.0,
                        'grid_factor': 1.0
                    })
                
                ntc_connections.append(connection_data)
        
        self.generation_to_demand_ntc = pd.DataFrame(ntc_connections)
        
        # Sort by estimated capacity (highest first)
        self.generation_to_demand_ntc = self.generation_to_demand_ntc.sort_values('estimated_ntc_mw', ascending=False)
        
        print(f"Estimated NTC for {len(self.generation_to_demand_ntc)} generation-to-demand connections")
        
        # Print top connections
        print("\nTop 10 generation-to-demand transmission connections:")
        for _, conn in self.generation_to_demand_ntc.head(10).iterrows():
            print(f"  {conn['from_generation_cluster']} -> {conn['to_demand_region']}: "
                  f"{conn['estimated_ntc_mw']:.0f} MW ({conn['distance_km']:.0f} km, "
                  f"{conn['capacity_utilization']:.1f}% utilization, {conn['dominant_tech']})")
        
        return self.generation_to_demand_ntc
    
    def _count_corridor_substations(self, grid_infrastructure, lat1, lng1, lat2, lng2, corridor_width_km=50):
        """
        Count substations within a corridor between two points
        """
        substations = grid_infrastructure[grid_infrastructure['type'] == 'substation']
        
        if len(substations) == 0:
            return 0
        
        corridor_count = 0
        
        for _, substation in substations.iterrows():
            sub_lat = substation['lat']
            sub_lng = substation['lng']
            
            # Calculate distance from substation to transmission line
            line_distance = self._point_to_line_distance(
                sub_lat, sub_lng, lat1, lng1, lat2, lng2
            )
            
            # Count if within corridor width
            if line_distance <= corridor_width_km:
                corridor_count += 1
        
        return corridor_count
    
    def _point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """
        Calculate shortest distance from point to line segment (in km)
        """
        # Vector from line start to point
        dx_p = px - x1
        dy_p = py - y1
        
        # Vector of the line
        dx_l = x2 - x1
        dy_l = y2 - y1
        
        # Length squared of line
        line_length_sq = dx_l * dx_l + dy_l * dy_l
        
        if line_length_sq == 0:
            return self._haversine_distance(px, py, x1, y1)
        
        # Parameter t for projection of point onto line
        t = max(0, min(1, (dx_p * dx_l + dy_p * dy_l) / line_length_sq))
        
        # Closest point on line
        closest_x = x1 + t * dx_l
        closest_y = y1 + t * dy_l
        
        return self._haversine_distance(px, py, closest_x, closest_y)
    
    def visualize_clusters(self, figsize=(15, 10)):
        """
        Visualize GEM power plant clusters on a map
        """
        if self.gem_data is None:
            print("No data to visualize")
            return None
        
        # Load country boundaries
        boundaries_file = '../data/country_data/naturalearth/ne_10m_admin_0_countries_lakes.shp'
        
        try:
            world = gpd.read_file(boundaries_file)
            country_boundary = world[world['ISO_A3'] == self.country]
        except Exception as e:
            print(f"Could not load country boundaries: {e}")
            country_boundary = None
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=figsize)
        
        # Top left: Plants by technology
        ax1.set_title(f'{self.country} - Power Plants by Technology')
        tech_colors = {'coal': 'brown', 'gas': 'orange', 'nuclear': 'red', 
                      'hydro': 'blue', 'wind': 'green', 'solar': 'yellow', 'other': 'gray'}
        
        for tech in self.gem_data['tech_group'].unique():
            tech_plants = self.gem_data[self.gem_data['tech_group'] == tech]
            color = tech_colors.get(tech, 'gray')
            ax1.scatter(tech_plants['lng'], tech_plants['lat'],
                       s=tech_plants['capacity_mw']/20, c=color, alpha=0.6, label=tech)
        
        ax1.legend()
        
        # Top right: Plants by capacity
        ax2.set_title(f'{self.country} - Power Plants by Capacity')
        scatter2 = ax2.scatter(self.gem_data['lng'], self.gem_data['lat'],
                             c=self.gem_data['capacity_mw'], s=30, alpha=0.6, cmap='Reds')
        plt.colorbar(scatter2, ax=ax2, label='Capacity (MW)')
        
        # Bottom left: Plants by age (if available)
        if 'year_online' in self.gem_data.columns:
            ax3.set_title(f'{self.country} - Power Plants by Age')
            years = pd.to_numeric(self.gem_data['year_online'], errors='coerce')
            ages = 2025 - years
            scatter3 = ax3.scatter(self.gem_data['lng'], self.gem_data['lat'],
                                 c=ages, s=30, alpha=0.6, cmap='viridis')
            plt.colorbar(scatter3, ax=ax3, label='Age (years)')
        else:
            ax3.set_title('Age data not available')
        
        # Bottom right: Clustered generation zones
        ax4.set_title(f'{self.country} - Generation Clusters')
        
        n_clusters = self.gem_data['cluster'].nunique()
        colors = plt.cm.Set3(np.linspace(0, 1, n_clusters))
        
        for i, cluster_id in enumerate(sorted(self.gem_data['cluster'].unique())):
            cluster_plants = self.gem_data[self.gem_data['cluster'] == cluster_id]
            ax4.scatter(cluster_plants['lng'], cluster_plants['lat'],
                       c=[colors[i]], s=cluster_plants['capacity_mw']/20,
                       alpha=0.7, label=f'Cluster {cluster_id}')
        
        # Plot cluster centers
        if self.cluster_centers is not None:
            ax4.scatter(self.cluster_centers['center_lng'], self.cluster_centers['center_lat'],
                       s=200, c='red', marker='*', edgecolors='black', linewidth=2,
                       label='Cluster Centers', zorder=5)
        
        # Add country boundaries if available
        if country_boundary is not None and len(country_boundary) > 0:
            for ax in [ax1, ax2, ax3, ax4]:
                country_boundary.boundary.plot(ax=ax, color='black', linewidth=1)
        
        for ax in [ax1, ax2, ax3, ax4]:
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
        
        # Limit legend items for readability
        handles, labels = ax4.get_legend_handles_labels()
        if len(handles) > 10:
            ax4.legend(handles[:10], labels[:10], bbox_to_anchor=(1.05, 1), loc='upper left')
        else:
            ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        plt.show()
        
        return fig
    
    def export_results(self, output_dir='output'):
        """
        Export clustering results to CSV files
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Export cluster centers
        if self.cluster_centers is not None:
            centers_file = os.path.join(output_dir, f'{self.country}_gem_cluster_centers.csv')
            self.cluster_centers.to_csv(centers_file, index=False)
            print(f"Exported GEM cluster centers to {centers_file}")
        
        # Export cluster mapping (plant to cluster mapping)
        if self.cluster_mapping is not None:
            mapping_file = os.path.join(output_dir, f'{self.country}_gem_cluster_mapping.csv')
            mapping_file2 = os.path.join(output_dir, f'{self.country}_power_plants_assigned_to_buses.csv')
            self.cluster_mapping.to_csv(mapping_file, index=False)
            powerplants_map_df = self.cluster_mapping[['GEM location ID', 'bus_id']]
            powerplants_map_df = powerplants_map_df.drop_duplicates(subset=['GEM location ID', 'bus_id'])
            powerplants_map_df.to_csv(mapping_file2, index=False)
            print(f"Exported GEM cluster mapping to {mapping_file}")
        
        # Export generation-to-demand NTC connections if available
        if hasattr(self, 'generation_to_demand_ntc') and self.generation_to_demand_ntc is not None:
            ntc_file = os.path.join(output_dir, f'{self.country}_generation_to_demand_ntc.csv')
            self.generation_to_demand_ntc.to_csv(ntc_file, index=False)
            print(f"Exported generation-to-demand NTC connections to {ntc_file}")
        
        # Print summary
        if self.cluster_centers is not None:
            print(f"\n=== {self.country} GENERATION CLUSTERS SUMMARY ===")
            print(f"Total clusters: {len(self.cluster_centers)}")
            print(f"Total capacity: {self.cluster_centers['total_capacity_mw'].sum():.0f} MW")
            print(f"Total plants: {self.cluster_centers['n_plants'].sum()}")
            
            # Technology breakdown
            tech_summary = {}
            for _, cluster in self.cluster_centers.iterrows():
                for tech, capacity in cluster['tech_breakdown'].items():
                    tech_summary[tech] = tech_summary.get(tech, 0) + capacity
            
            print("\nTechnology breakdown:")
            for tech, capacity in sorted(tech_summary.items(), key=lambda x: x[1], reverse=True):
                share = capacity / sum(tech_summary.values()) * 100
                print(f"  {tech}: {capacity:.0f} MW ({share:.1f}%)")
            
            print("\nTop 5 clusters by capacity:")
            top_clusters = self.cluster_centers.nlargest(5, 'total_capacity_mw')
            for _, cluster in top_clusters.iterrows():
                print(f"  {cluster['name']}: {cluster['total_capacity_mw']:.0f} MW "
                      f"({cluster['capacity_share']:.1%}, {cluster['n_plants']} plants, "
                      f"{cluster['dominant_tech']})")


def analyze_country_gem_units(country_code, target_clusters=None, eps_km=30, min_share=0.01, by_technology=True, enable_osm_grid=False, output_dir='output'):
    """
    Complete GEM power plant clustering analysis pipeline for a country
    """
    print(f"\nStarting GEM power plant cluster analysis for {country_code}")
    
    # Initialize clusterer
    clusterer = GEMUnitsClusterer(country_code)
    clusterer.min_share = min_share  # Set minimum cluster size
    
    # Load data
    print("\nLoading GEM power plant data...")
    if clusterer.load_gem_data() is None:
        return None
    
    # Load REZoning grid cell data for coordinate mapping
    print("\nLoading REZoning grid cell data...")
    clusterer.load_rezoning_data()
    
    # Cluster power plants
    print(f"\nClustering into generation zones (target: {target_clusters or 'auto'})...")
    clusterer.cluster_gem_units(method='voronoi', n_clusters=target_clusters, 
                               eps_km=eps_km, by_technology=by_technology)
    
    # Estimate NTC to demand regions
    clusterer.estimate_generation_to_demand_ntc(use_osm_grid=enable_osm_grid)
    
    # Export results
    print("\nExporting results...")
    clusterer.export_results(output_dir)
    
    return clusterer


if __name__ == "__main__":
    # Default cluster suggestions for known countries (optional)
    default_clusters = {
        'CHE': 3, 'ITA': 5, 'DEU': 8, 'USA': 15, 'AUS': 6, 'CHN': 12,
        'IND': 10, 'JPN': 8, 'ZAF': 4, 'NZL': 3, 'BRA': 8, 'FRA': 6,
        'GBR': 6, 'ESP': 5, 'CAN': 10, 'MEX': 6, 'ARG': 4, 'RUS': 12,
        'TUR': 5, 'IRN': 6, 'SAU': 3, 'EGY': 4, 'NGA': 6, 'KEN': 3,
        'ETH': 4, 'GHA': 3, 'THA': 4, 'VNM': 4, 'IDN': 8, 'MYS': 3,
        'PHL': 6, 'KOR': 4, 'TWN': 3, 'SGP': 1, 'HKG': 1, 'ARE': 2
    }
    
    parser = argparse.ArgumentParser(description='GEM power plant cluster analysis')
    parser.add_argument('--country', required=True,
                       help='ISO3 country code for analysis (e.g., USA, DEU, IND)')
    parser.add_argument('--clusters', type=int,
                       help='Target number of generation clusters (default: auto-suggested based on country)')
    parser.add_argument('--eps-km', type=float, default=30,
                       help='DBSCAN epsilon parameter in km (default: 30)')
    parser.add_argument('--min-share', type=float, default=0.01,
                       help='Minimum cluster size as share of total capacity (default: 0.01 = 1%)')
    parser.add_argument('--by-technology', action='store_true', default=False,
                       help='Cluster separately by technology (default: False)')
    parser.add_argument('--mixed-tech', action='store_true',
                       help='Cluster all technologies together (overrides --by-technology)')
    parser.add_argument('--enable-osm-grid', action='store_true',
                       help='Enable OSM grid infrastructure for NTC enhancement (disabled by default)')
    parser.add_argument('--output-dir', default='output',
                       help='Output directory for results (default: output)')
    
    args = parser.parse_args()
    
    # Handle technology clustering option
    by_technology = args.by_technology and not args.mixed_tech
    
    # Use suggested clusters if available, otherwise default to 5
    target_clusters = args.clusters or default_clusters.get(args.country.upper(), 5)
    
    print(f"Selected: {args.country.upper()}")
    print(f"Target generation clusters: {target_clusters}")
    print(f"Clustering mode: {'By technology' if by_technology else 'Mixed technologies'}")
    
    if args.enable_osm_grid:
        print("OSM grid infrastructure: ENABLED")
    else:
        print("OSM grid infrastructure: DISABLED (distance-based NTC only)")
    
    # Run analysis
    result = analyze_country_gem_units(args.country.upper(), target_clusters=target_clusters, 
                                     eps_km=args.eps_km, min_share=args.min_share,
                                     by_technology=by_technology, enable_osm_grid=args.enable_osm_grid,
                                     output_dir=args.output_dir)
    
    if result:
        print(f"\nGEM clustering complete for {args.country.upper()}!")
        print(f"Check the '{args.output_dir}' folder for CSV files with detailed results.")
    else:
        print(f"\nNo GEM power plant data found for {args.country.upper()}")
