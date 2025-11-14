#!/usr/bin/env python3
"""
Substation Grid Mapper for Synthetic Grid Generation
===================================================

Maps actual substations and transmission lines to synthetic grid clusters,
then calculates realistic NTC between clusters based on actual line capacities.

Usage:
    python substation_grid_mapper.py --country KAN --output-dir test_output_kan
"""

import pandas as pd
import numpy as np
from shapely.geometry import Point, Polygon, LineString
from scipy.spatial import ConvexHull
import argparse
import os
from pathlib import Path
import matplotlib.pyplot as plt
try:
    import geopandas as gpd
    from rtree import index
    WATER_DETECTION_AVAILABLE = True
except ImportError:
    WATER_DETECTION_AVAILABLE = False
    print("⚠️ Water detection dependencies not available (geopandas, rtree)")

class SubstationGridMapper:
    """
    Maps actual substations to synthetic clusters and calculates inter-cluster NTC
    """
    
    def __init__(self, country_code, output_dir, grid_data_dir=None):
        self.country = country_code.upper()
        # Ensure output_dir is a Path object and create country-specific subdirectory
        self.output_dir = Path(output_dir) / self.country
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-detect grid data source if not provided
        if grid_data_dir is None:
            from syn_grids_1.clustered_buses_utils import get_osm_data_source
            data_source = get_osm_data_source(self.country)
            if data_source is None:
                raise ValueError(f"No OSM data available for country: {self.country}")
            self.grid_data_dir = f'data/OSM-{data_source}-prebuilt'
            print(f"Auto-detected grid data source: {self.grid_data_dir}")
        else:
            self.grid_data_dir = grid_data_dir
            print(f"Using specified grid data source: {self.grid_data_dir}")
        
        # Load cluster data
        self.demand_centers = None
        self.demand_points = None
        self.generation_centers = None
        self.generation_mapping = None
        self.renewable_centers = None
        self.renewable_mapping = None
        
        # Load grid infrastructure data
        self.substations = None
        self.transmission_lines = None
        
        # Results
        self.substation_cluster_mapping = None
        self.cluster_shapes = None
        self.ntc_matrix = None
        
        # Water detection
        self.water_data = None
        self.water_index = None
        self.water_threshold = 0.1  # Flag if >10% of line is over water
        
        # Flow direction rules (from our discussion)
        self.allowed_flows = {
            ('generation', 'demand'): True,     # G→D: Power plants supply load
            ('renewable', 'demand'): True,      # R→D: Clean power to load  
            ('renewable', 'generation'): True,  # R→G: Storage/grid services
            ('demand', 'demand'): True,         # D→D: Inter-regional load balancing
            # Blocked flows: D→G, D→R, G→R, G→G, R→R
        }
    
    def load_cluster_data(self):
        """Load cluster data from previous clustering step"""
        base_path = Path(self.output_dir)
        
        # Load demand data
        demand_centers_file = base_path / f'{self.country}_region_centers.csv'
        demand_points_file = base_path / f'{self.country}_demand_points.csv'
        
        if demand_centers_file.exists():
            self.demand_centers = pd.read_csv(demand_centers_file)
            print(f"📍 Loaded {len(self.demand_centers)} demand centers")
        
        if demand_points_file.exists():
            self.demand_points = pd.read_csv(demand_points_file)
            print(f"🏘️ Loaded {len(self.demand_points)} demand points")
        
        # Load generation data
        generation_centers_file = base_path / f'{self.country}_gem_cluster_centers.csv'
        generation_mapping_file = base_path / f'{self.country}_gem_cluster_mapping.csv'
        
        if generation_centers_file.exists():
            self.generation_centers = pd.read_csv(generation_centers_file)
            print(f"🏭 Loaded {len(self.generation_centers)} generation centers")
        
        if generation_mapping_file.exists():
            self.generation_mapping = pd.read_csv(generation_mapping_file)
            print(f"⚡ Loaded {len(self.generation_mapping)} generation facilities")
        
        # Load renewable data
        renewable_centers_file = base_path / f'{self.country}_renewable_cluster_centers.csv'
        renewable_mapping_file = base_path / f'{self.country}_renewable_cluster_mapping.csv'
        
        if renewable_centers_file.exists():
            self.renewable_centers = pd.read_csv(renewable_centers_file)
            print(f"🌞 Loaded {len(self.renewable_centers)} renewable centers")
        
        if renewable_mapping_file.exists():
            self.renewable_mapping = pd.read_csv(renewable_mapping_file)
            print(f"🌱 Loaded {len(self.renewable_mapping)} renewable grid cells")
    
    def load_grid_infrastructure(self):
        """Load substation and transmission line data, filtered by country"""
        # Convert ISO3 to ISO2 for substation filtering
        from syn_grids_1.clustered_buses_utils import get_iso2_from_iso3
        iso2_country = get_iso2_from_iso3(self.country)
        print(f"Filtering grid data for {self.country} (ISO2: {iso2_country})")
        
        # Load substations (buses)
        buses_file = Path(self.grid_data_dir) / 'buses.csv'
        if buses_file.exists():
            all_substations = pd.read_csv(buses_file)
            
            # Filter by country using ISO2 code
            if 'country' in all_substations.columns:
                self.substations = all_substations[all_substations['country'] == iso2_country].copy()
            else:
                # Fallback: try to filter by bus_id pattern
                self.substations = all_substations[
                    all_substations['bus_id'].astype(str).str.contains(iso2_country, case=False, na=False)
                ].copy()
            
            if self.substations.empty:
                available_countries = all_substations['country'].unique() if 'country' in all_substations.columns else []
                raise ValueError(f"No substations found for country '{self.country}' (ISO2: {iso2_country}). "
                               f"Available countries: {available_countries[:10]}")
            
            # Extract lat/lng from x,y columns (assuming they are lng,lat)
            self.substations['lat'] = self.substations['y']
            self.substations['lng'] = self.substations['x']
            print(f"Loaded {len(self.substations)} substations for {self.country}")
        else:
            raise FileNotFoundError(f"Substations file not found: {buses_file}")
        
        # Load transmission lines
        lines_file = Path(self.grid_data_dir) / 'lines.csv'
        if lines_file.exists():
            all_lines = pd.read_csv(lines_file)
            
            # Filter lines where both buses are in the country
            country_bus_ids = set(self.substations['bus_id'].astype(str))
            
            if 'bus0' in all_lines.columns and 'bus1' in all_lines.columns:
                self.transmission_lines = all_lines[
                    all_lines['bus0'].astype(str).isin(country_bus_ids) & 
                    all_lines['bus1'].astype(str).isin(country_bus_ids)
                ].copy()
                
                print(f"Loaded {len(self.transmission_lines)} transmission lines for {self.country}")
                if len(self.transmission_lines) > 0:
                    print(f"   Total capacity: {self.transmission_lines['s_nom'].sum():,.0f} MVA")
            else:
                print("No bus0/bus1 columns found in lines data")
                self.transmission_lines = pd.DataFrame()
        else:
            raise FileNotFoundError(f"Transmission lines file not found: {lines_file}")
        
        return True  # Successfully loaded grid infrastructure
    
    def _get_all_cluster_centers(self):
        """Get all cluster centers from all cluster types"""
        all_clusters = []
        
        # Add demand centers
        if self.demand_results and self.demand_results['centers'] is not None:
            centers_df = pd.DataFrame(self.demand_results['centers'])
            for _, center in centers_df.iterrows():
                all_clusters.append({
                    'cluster_id': int(center.get('cluster_id', center.name)),
                    'cluster_type': 'demand',
                    'lat': center['center_lat'],
                    'lng': center['center_lng']
                })
        
        # Add generation centers
        if self.generation_results and self.generation_results['centers'] is not None:
            centers_df = pd.DataFrame(self.generation_results['centers'])
            for _, center in centers_df.iterrows():
                all_clusters.append({
                    'cluster_id': int(center.get('cluster_id', center.name)),
                    'cluster_type': 'generation',
                    'lat': center['center_lat'],
                    'lng': center['center_lng']
                })
        
        # Add renewable centers
        if self.renewable_results and self.renewable_results['centers'] is not None:
            centers_df = pd.DataFrame(self.renewable_results['centers'])
            for _, center in centers_df.iterrows():
                all_clusters.append({
                    'cluster_id': int(center.get('cluster_id', center.name)),
                    'cluster_type': 'renewable',
                    'lat': center['center_lat'],
                    'lng': center['center_lng']
                })
        return all_clusters
    
    def _get_bus_location(self, bus_id):
        """Get lat/lng coordinates for a bus_id"""
        if self.substations is None:
            return None
        
        bus_data = self.substations[self.substations['bus_id'] == bus_id]
        if len(bus_data) == 0:
            return None
        
        return {
            'lat': bus_data.iloc[0]['lat'],
            'lng': bus_data.iloc[0]['lng']
        }
    
    def _haversine_distance(self, lat1, lng1, lat2, lng2):
        """Calculate haversine distance between two points in kilometers"""
        import math
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r
    
    def _find_nearest_cluster(self, bus_location, all_clusters):
        """Find nearest cluster to bus location, with priority tie-breaking"""
        if not all_clusters:
            return None
        
        min_distance = float('inf')
        nearest_cluster = None
        
        # Priority order for tie-breaking
        priority_order = {'renewable': 1, 'generation': 2, 'demand': 3}
        
        for cluster in all_clusters:
            distance = self._haversine_distance(
                bus_location['lat'], bus_location['lng'],
                cluster['lat'], cluster['lng']
            )
            
            # Check if this is the closest cluster
            if distance < min_distance:
                min_distance = distance
                nearest_cluster = cluster
            elif distance == min_distance:
                # Tie-breaking: use priority order (renewable > generation > demand)
                current_priority = priority_order.get(cluster['cluster_type'], 999)
                nearest_priority = priority_order.get(nearest_cluster['cluster_type'], 999)
                
                if current_priority < nearest_priority:
                    nearest_cluster = cluster
        
        return nearest_cluster
    
    def _is_valid_connection(self, from_type, to_type):
        """Check if connection between cluster types is physically valid"""
        # Your connection rules:
        # 1. Generation to Demand
        # 2. Renewable to Demand  
        # 3. Renewable to Generation
        # 4. Demand to Demand
        
        valid_connections = {
            ('generation', 'demand'): True,
            ('renewable', 'demand'): True,
            ('renewable', 'generation'): True,
            ('demand', 'demand'): True,
        }
        
        return valid_connections.get((from_type, to_type), False)
    
    def _find_clusters_containing_bus(self, bus_location):
        """Find all cluster hulls that contain the bus location"""
        containing_clusters = []
        
        # Check demand clusters
        if self.demand_results and self.demand_results['points'] is not None:
            demand_clusters = self._get_cluster_hulls_from_points(
                self.demand_results['points'], 'demand'
            )
            for cluster_id, hull in demand_clusters.items():
                if self._point_in_polygon(bus_location, hull):
                    containing_clusters.append({
                        'cluster_id': cluster_id,
                        'cluster_type': 'demand',
                        'hull': hull
                    })
        
        # Check generation clusters
        if self.generation_results and self.generation_results['mapping'] is not None:
            generation_clusters = self._get_cluster_hulls_from_points(
                self.generation_results['mapping'], 'generation'
            )
            for cluster_id, hull in generation_clusters.items():
                if self._point_in_polygon(bus_location, hull):
                    containing_clusters.append({
                        'cluster_id': cluster_id,
                        'cluster_type': 'generation',
                        'hull': hull
                    })
        
        # Check renewable clusters
        if self.renewable_results and self.renewable_results['mapping'] is not None:
            renewable_clusters = self._get_cluster_hulls_from_points(
                self.renewable_results['mapping'], 'renewable'
            )
            for cluster_id, hull in renewable_clusters.items():
                if self._point_in_polygon(bus_location, hull):
                    containing_clusters.append({
                        'cluster_id': cluster_id,
                        'cluster_type': 'renewable',
                        'hull': hull
                    })
        
        return containing_clusters
    
    def _get_cluster_hulls_from_points(self, points_data, cluster_type):
        """Create cluster hulls from clustered points data"""
        from scipy.spatial import ConvexHull
        import numpy as np
        
        hulls = {}
        
        if points_data is None:
            return hulls
        
        # Determine the correct cluster column name based on cluster type
        if cluster_type == 'generation':
            cluster_col = 'cluster_id'
        else:  # demand and renewable use 'cluster'
            cluster_col = 'cluster'
        
        # Group points by the correct cluster column
        cluster_groups = points_data.groupby(cluster_col)
        
        for cluster_id, group in cluster_groups:
            if len(group) < 3:  # Need at least 3 points for a hull
                # Create a small circle around the centroid
                centroid_lat = group['lat'].mean()
                centroid_lng = group['lng'].mean()
                hulls[cluster_id] = {
                    'type': 'circle',
                    'center': (centroid_lat, centroid_lng),
                    'radius': 0.1  # 0.1 degree radius
                }
                continue
            
            # Create convex hull
            try:
                points = np.column_stack((group['lng'].values, group['lat'].values))
                hull = ConvexHull(points)
                hull_coords = points[hull.vertices]
                
                hulls[cluster_id] = {
                    'type': 'polygon',
                    'coordinates': hull_coords
                }
            except Exception:
                # Fallback to circle if hull creation fails
                centroid_lat = group['lat'].mean()
                centroid_lng = group['lng'].mean()
                hulls[cluster_id] = {
                    'type': 'circle',
                    'center': (centroid_lat, centroid_lng),
                    'radius': 0.1
                }
        
        return hulls
    
    def _point_in_polygon(self, point, hull):
        """Check if point is inside polygon or circle hull"""
        if hull['type'] == 'circle':
            # Check if point is within circle
            center_lat, center_lng = hull['center']
            distance = self._haversine_distance(
                point['lat'], point['lng'],
                center_lat, center_lng
            )
            # Convert radius from degrees to km (rough approximation)
            radius_km = hull['radius'] * 111  # 1 degree ≈ 111 km
            return distance <= radius_km
        
        elif hull['type'] == 'polygon':
            # Check if point is inside polygon using ray casting algorithm
            x, y = point['lng'], point['lat']
            polygon = hull['coordinates']
            
            n = len(polygon)
            inside = False
            
            p1x, p1y = polygon[0]
            for i in range(1, n + 1):
                p2x, p2y = polygon[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y
            
            return inside
        
        return False
    
    def _find_valid_bus1_assignment(self, bus0_type, candidate_clusters):
        """Find valid bus1 assignment from candidate clusters with bus0-dependent priority"""
        if not candidate_clusters:
            return None
        
        # Priority depends on bus0 type
        if bus0_type == 'renewable':
            # Renewable can connect to Demand (priority 1) or Generation (priority 2)
            priority_order = {'demand': 1, 'generation': 2}
        elif bus0_type == 'generation':
            # Generation can only connect to Demand (priority 1)
            priority_order = {'demand': 1}
        elif bus0_type == 'demand':
            # Demand can only connect to Demand (priority 1)
            priority_order = {'demand': 1}
        else:
            return None
        
        # Try to find a valid connection
        valid_candidates = []
        for cluster in candidate_clusters:
            if self._is_valid_connection(bus0_type, cluster['cluster_type']):
                valid_candidates.append(cluster)
        
        if not valid_candidates:
            return None
        
        # Return the highest priority valid candidate
        best_candidate = min(valid_candidates, 
                           key=lambda x: priority_order.get(x['cluster_type'], 999))
        
        return best_candidate
    
    def _assign_bus0_to_closest_hull_centroid(self, bus_location):
        """
        Assign bus0 to the hull with the closest centroid (determines type)
        
        Strategy:
        1. Find all hulls that contain bus0
        2. Calculate distance to each hull's centroid
        3. Assign to hull with closest centroid
        4. This determines bus0's type for bus1 assignment
        """
        # Find all hulls that contain bus0
        containing_clusters = self._find_clusters_containing_bus(bus_location)
        
        if not containing_clusters:
            # If bus0 is not in any hull, assign to nearest cluster center
            all_clusters = self._get_all_cluster_centers()
            return self._find_nearest_cluster(bus_location, all_clusters)
        
        # Calculate distance to each hull's centroid
        min_distance = float('inf')
        closest_cluster = None
        
        for cluster in containing_clusters:
            # Get cluster centroid
            centroid = self._get_cluster_centroid(cluster['cluster_id'], cluster['cluster_type'])
            if centroid is None:
                continue
            
            # Calculate distance to centroid
            distance = self._haversine_distance(
                bus_location['lat'], bus_location['lng'],
                centroid['lat'], centroid['lng']
            )
            
            # Keep track of closest centroid
            if distance < min_distance:
                min_distance = distance
                closest_cluster = cluster
        
        return closest_cluster
    
    def _get_cluster_centroid(self, cluster_id, cluster_type):
        """Get the centroid coordinates for a specific cluster"""
        if cluster_type == 'demand' and self.demand_results and self.demand_results['centers'] is not None:
            centers_df = pd.DataFrame(self.demand_results['centers'])
            cluster_data = centers_df[centers_df.index == cluster_id]
            if len(cluster_data) > 0:
                return {
                    'lat': cluster_data.iloc[0]['center_lat'],
                    'lng': cluster_data.iloc[0]['center_lng']
                }
        
        elif cluster_type == 'generation' and self.generation_results and self.generation_results['centers'] is not None:
            centers_df = pd.DataFrame(self.generation_results['centers'])
            cluster_data = centers_df[centers_df.index == cluster_id]
            if len(cluster_data) > 0:
                return {
                    'lat': cluster_data.iloc[0]['center_lat'],
                    'lng': cluster_data.iloc[0]['center_lng']
                }
        
        elif cluster_type == 'renewable' and self.renewable_results and self.renewable_results['centers'] is not None:
            centers_df = pd.DataFrame(self.renewable_results['centers'])
            cluster_data = centers_df[centers_df.index == cluster_id]
            if len(cluster_data) > 0:
                return {
                    'lat': cluster_data.iloc[0]['center_lat'],
                    'lng': cluster_data.iloc[0]['center_lng']
                }
        
        return None
    
    
    def create_cluster_shapes(self):
        """Create cluster boundary shapes from clustered points"""
        self.cluster_shapes = {}
        
        # Create demand cluster shapes
        if self.demand_centers is not None and self.demand_points is not None:
            self.cluster_shapes['demand'] = self._create_shapes_from_points(
                self.demand_centers, self.demand_points, 'demand'
            )
        
        # Create generation cluster shapes  
        if self.generation_centers is not None and self.generation_mapping is not None:
            self.cluster_shapes['generation'] = self._create_shapes_from_points(
                self.generation_centers, self.generation_mapping, 'generation'
            )
        
        # Create renewable cluster shapes
        if self.renewable_centers is not None and self.renewable_mapping is not None:
            self.cluster_shapes['renewable'] = self._create_shapes_from_points(
                self.renewable_centers, self.renewable_mapping, 'renewable'
            )
        
        print(f"📐 Created cluster shapes:")
        for cluster_type, shapes in self.cluster_shapes.items():
            print(f"   {cluster_type}: {len(shapes)} shapes")
    
    def _create_shapes_from_points(self, centers_df, points_df, cluster_type):
        """Create ConvexHull shapes from clustered points"""
        shapes = {}
        
        for _, center in centers_df.iterrows():
            cluster_id = center.get('cluster_id', center.name)
            
            # Get points for this cluster
            if 'cluster' in points_df.columns:
                cluster_data = points_df[points_df['cluster'] == cluster_id]
            elif 'cluster_id' in points_df.columns:
                cluster_data = points_df[points_df['cluster_id'] == cluster_id]
            else:
                continue
            
            if len(cluster_data) >= 3:  # Need at least 3 points for ConvexHull
                try:
                    coords = cluster_data[['lng', 'lat']].values
                    hull = ConvexHull(coords)
                    hull_coords = coords[hull.vertices]
                    shapes[cluster_id] = Polygon(hull_coords)
                except Exception as e:
                    print(f"⚠️ Could not create shape for {cluster_type} cluster {cluster_id}: {e}")
                    # Fallback to circle around center
                    center_point = Point(center['center_lng'], center['center_lat'])
                    shapes[cluster_id] = center_point.buffer(0.5)  # 0.5 degree buffer
            else:
                # Fallback for clusters with few points
                center_point = Point(center['center_lng'], center['center_lat'])
                shapes[cluster_id] = center_point.buffer(0.5)
        
        return shapes
    
    def assign_substations_to_clusters(self):
        """
        Assign each substation to exactly one cluster using hierarchical priority:
        1. Renewable cluster (if within boundary)
        2. Generation cluster (if within boundary)  
        3. Demand cluster (fallback)
        """
        if self.substations is None:
            print("❌ No substations loaded")
            return
        
        print(f"\n🎯 ASSIGNING SUBSTATIONS TO CLUSTERS")
        print("-" * 50)
        
        substation_assignments = []
        
        for _, substation in self.substations.iterrows():
            bus_id = substation['bus_id']
            point = Point(substation['lng'], substation['lat'])
            
            assigned_cluster = None
            assigned_type = None
            
            # Priority 1: Check renewable clusters
            if 'renewable' in self.cluster_shapes:
                for cluster_id, shape in self.cluster_shapes['renewable'].items():
                    if shape.contains(point):
                        assigned_cluster = cluster_id
                        assigned_type = 'renewable'
                        break
            
            # Priority 2: Check generation clusters (if not already assigned)
            if assigned_cluster is None and 'generation' in self.cluster_shapes:
                for cluster_id, shape in self.cluster_shapes['generation'].items():
                    if shape.contains(point):
                        assigned_cluster = cluster_id
                        assigned_type = 'generation'
                        break
            
            # Priority 3: Assign to nearest demand cluster (fallback)
            if assigned_cluster is None and 'demand' in self.cluster_shapes:
                min_distance = float('inf')
                nearest_cluster = None
                
                for cluster_id, shape in self.cluster_shapes['demand'].items():
                    if shape.contains(point):
                        assigned_cluster = cluster_id
                        assigned_type = 'demand'
                        break
                    else:
                        # Find nearest cluster center if not within any boundary
                        distance = point.distance(shape.centroid)
                        if distance < min_distance:
                            min_distance = distance
                            nearest_cluster = cluster_id
                
                # Assign to nearest if not within any boundary
                if assigned_cluster is None:
                    assigned_cluster = nearest_cluster
                    assigned_type = 'demand'
            
            substation_assignments.append({
                'bus_id': bus_id,
                'lat': substation['lat'],
                'lng': substation['lng'],
                'voltage': substation.get('voltage', 0),
                'cluster_id': assigned_cluster,
                'cluster_type': assigned_type
            })
        
        self.substation_cluster_mapping = pd.DataFrame(substation_assignments)
        
        # Print assignment summary
        assignment_summary = self.substation_cluster_mapping.groupby('cluster_type').size()
        print(f"📊 Substation assignment summary:")
        for cluster_type, count in assignment_summary.items():
            print(f"   {cluster_type}: {count} substations")
        
        return self.substation_cluster_mapping
    
    def calculate_inter_cluster_ntc(self):
        """
        Calculate NTC between clusters using hull-based assignment and connection validation
        
        Logic:
        1. bus0 → nearest cluster (any type)
        2. bus1 → check which cluster hulls it falls within
        3. bus1 → try to assign valid type from those hulls (with priority)
        4. Skip if no valid connection possible
        """
        if self.transmission_lines is None:
            print("❌ Missing transmission line data")
            return
        
        print(f"\n⚡ CALCULATING INTER-CLUSTER NTC (Hull-Based Assignment)")
        print("-" * 50)
        
        # Debug: Check cluster results
        print(f"🔍 Debug - demand_results: {self.demand_results is not None}")
        print(f"🔍 Debug - generation_results: {self.generation_results is not None}")
        print(f"🔍 Debug - renewable_results: {self.renewable_results is not None}")
        
        # Debug: Check data structure
        if self.demand_results and self.demand_results['points'] is not None:
            print(f"🔍 Debug - demand_points columns: {list(self.demand_results['points'].columns)}")
        if self.generation_results and self.generation_results['mapping'] is not None:
            print(f"🔍 Debug - generation_mapping columns: {list(self.generation_results['mapping'].columns)}")
        if self.renewable_results and self.renewable_results['mapping'] is not None:
            print(f"🔍 Debug - renewable_mapping columns: {list(self.renewable_results['mapping'].columns)}")
        
        # Get all cluster centers and hulls for assignment
        all_clusters = self._get_all_cluster_centers()
        if not all_clusters:
            print("❌ No cluster centers found")
            return
        
        print(f"📍 Found {len(all_clusters)} cluster centers for assignment")
        
        # Initialize NTC matrix
        ntc_connections = []
        skipped_lines = 0
        valid_lines = 0
        
        # Process each transmission line
        for _, line in self.transmission_lines.iterrows():
            bus0 = line['bus0']
            bus1 = line['bus1']
            capacity_mva = line['s_nom']
            
            # Get bus locations
            bus0_location = self._get_bus_location(bus0)
            bus1_location = self._get_bus_location(bus1)
            
            if bus0_location is None or bus1_location is None:
                continue  # Skip if bus location not found
            
            # Step 1: Assign bus0 to hull with closest centroid (determines type)
            bus0_cluster = self._assign_bus0_to_closest_hull_centroid(bus0_location)
            if bus0_cluster is None:
                continue
            
            # Step 2: Check which cluster hulls bus1 falls within
            bus1_candidate_clusters = self._find_clusters_containing_bus(bus1_location)
            if not bus1_candidate_clusters:
                # If bus1 doesn't fall in any hull, assign to nearest cluster
                bus1_cluster = self._find_nearest_cluster(bus1_location, all_clusters)
                if bus1_cluster is None:
                    continue
            else:
                # Step 3: Assign bus1 based on bus0's type and priority rules
                bus1_cluster = self._find_valid_bus1_assignment(bus0_cluster['cluster_type'], bus1_candidate_clusters)
                if bus1_cluster is None:
                    skipped_lines += 1
                    continue
            
            # Skip if bus0 and bus1 are in the same hull (no inter-cluster connection)
            if (bus0_cluster['cluster_id'] == bus1_cluster['cluster_id'] and 
                bus0_cluster['cluster_type'] == bus1_cluster['cluster_type']):
                continue
            
            # Step 4: Check if connection is physically valid
            if self._is_valid_connection(bus0_cluster['cluster_type'], bus1_cluster['cluster_type']):
                # Apply offset to renewable cluster IDs to match centers
                from_cluster_id = self._apply_renewable_offset(bus0_cluster['cluster_id'], bus0_cluster['cluster_type'])
                to_cluster_id = self._apply_renewable_offset(bus1_cluster['cluster_id'], bus1_cluster['cluster_type'])
                
                # Get original cluster IDs (without offset) for readable format
                # Use the original cluster IDs (before offset is applied)
                bus0_original = self._get_original_cluster_id(bus0_cluster['cluster_type'], bus0_cluster['cluster_id'])
                bus1_original = self._get_original_cluster_id(bus1_cluster['cluster_type'], bus1_cluster['cluster_id'])
                
                # Create descriptive type comment
                type_description = f"{bus0_cluster['cluster_type'].capitalize()} cluster {bus0_cluster['cluster_id']} to {bus1_cluster['cluster_type'].capitalize()} cluster {bus1_cluster['cluster_id']}"
                
                # Get cluster center coordinates for distance calculation
                bus0_center = self._get_cluster_by_id(bus0_cluster['cluster_id'], bus0_cluster['cluster_type'])
                bus1_center = self._get_cluster_by_id(bus1_cluster['cluster_id'], bus1_cluster['cluster_type'])
                
                if bus0_center is None or bus1_center is None:
                    print(f"⚠️ Warning: Could not find cluster centers for distance calculation")
                    cluster_distance = 0
                else:
                    # Calculate distance between cluster centers for aggregation
                    cluster_distance = self._haversine_distance(
                        bus0_center['lat'], bus0_center['lng'],
                        bus1_center['lat'], bus1_center['lng']
                    )
                
                
                # Add valid connection
                ntc_connections.append({
                    'from_cluster_id': from_cluster_id,
                    'from_cluster_type': bus0_cluster['cluster_type'],
                    'to_cluster_id': to_cluster_id,
                    'to_cluster_type': bus1_cluster['cluster_type'],
                    'bus0': bus0_original,  # Original cluster ID (e.g., dem0, gen1, sol2)
                    'bus1': bus1_original,  # Original cluster ID (e.g., dem0, gen1, won3)
                    'type': type_description,  # Descriptive comment
                    'line_id': line.get('line_id', f"{bus0}-{bus1}"),
                    's_nom': capacity_mva,
                    'voltage': line.get('voltage', 0),
                    'length': cluster_distance,  # Distance between cluster centers
                    'from_bus': bus0,
                    'to_bus': bus1
                })
                valid_lines += 1
            else:
                # Skip invalid connections
                skipped_lines += 1
        
        print(f"📊 Line processing summary:")
        print(f"   Valid connections: {valid_lines}")
        print(f"   Skipped (invalid): {skipped_lines}")
        print(f"   Total processed: {valid_lines + skipped_lines}")
        
        # Convert to DataFrame and aggregate by cluster pairs
        if len(ntc_connections) > 0:
            ntc_df = pd.DataFrame(ntc_connections)
            
            # Aggregate capacity by cluster pairs
            self.ntc_matrix = ntc_df.groupby([
                'from_cluster_id', 'from_cluster_type', 
                'to_cluster_id', 'to_cluster_type'
            ]).agg({
                's_nom': 'sum',
                'line_id': 'count',  # Number of lines
                'voltage': 'mean',  # Average voltage
                'length': 'mean',  # Average distance between clusters
                'bus0': 'first',  # Take first bus0 (should be same for all)
                'bus1': 'first',  # Take first bus1 (should be same for all)
                'type': 'first'   # Take first type description (should be same for all)
            }).reset_index()
            
            self.ntc_matrix.rename(columns={'line_id': 'num_lines'}, inplace=True)
            
            print(f"\n✅ NTC Matrix Results:")
            print(f"   Total inter-cluster connections: {len(self.ntc_matrix)}")
            print(f"   Total NTC capacity: {self.ntc_matrix['s_nom'].sum():,.0f} MVA")
            
            # Show top connections
            print(f"\n🔝 Top 5 NTC connections:")
            top_connections = self.ntc_matrix.nlargest(5, 's_nom')
            for _, conn in top_connections.iterrows():
                print(f"   {conn['from_cluster_type']}{conn['from_cluster_id']} → "
                      f"{conn['to_cluster_type']}{conn['to_cluster_id']}: "
                      f"{conn['s_nom']:,.0f} MVA ({conn['num_lines']} lines)")
        
        else:
            print("⚠️ No valid inter-cluster connections found")
            self.ntc_matrix = pd.DataFrame()
        
        return self.ntc_matrix
    
    def _get_original_cluster_id(self, cluster_type, offset_cluster_id):
        """
        Get original cluster ID (without offset) for readable format
        
        Args:
            cluster_type: Type of cluster (demand, generation, renewable)
            offset_cluster_id: Cluster ID with offset applied
            
        Returns:
            String in format like 'dem0', 'gen1', 'ren2'
        """
        if cluster_type == 'demand':
            # Demand clusters don't have offset, so original ID is the same
            return f"dem{int(float(offset_cluster_id))}"
        elif cluster_type == 'generation':
            # Generation clusters don't have offset, so original ID is the same
            return f"gen{int(float(offset_cluster_id))}"
        elif cluster_type == 'renewable':
            # Need to reverse the offset to get original cluster ID
            if (hasattr(self, 'renewable_results') and 
                self.renewable_results and 
                'technologies' in self.renewable_results and 
                self.renewable_results['technologies']):
                
                technologies = self.renewable_results['technologies']
                
                # Find which technology this cluster belongs to
                solar_count = technologies.get('solar', {}).get('n_clusters', 0)
                onshore_count = technologies.get('wind_onshore', {}).get('n_clusters', 0)
                
                # Convert to int for comparison
                offset_id = int(float(offset_cluster_id))
                
                if offset_id < solar_count:
                    # Solar cluster
                    original_id = offset_id
                    return f"sol{original_id}"
                elif offset_id < solar_count + onshore_count:
                    # Wind onshore cluster
                    original_id = offset_id - solar_count
                    return f"won{original_id}"
                else:
                    # Wind offshore cluster
                    original_id = offset_id - solar_count - onshore_count
                    return f"wof{original_id}"
            
            # Fallback if we can't determine the technology
            return f"ren{int(float(offset_cluster_id))}"
        else:
            return f"{cluster_type[:3]}{int(float(offset_cluster_id))}"

    def _apply_renewable_offset(self, cluster_id, cluster_type):
        """
        Apply the same offset to renewable cluster IDs that's used in centers creation
        
        This ensures NTC matrix cluster IDs match the centers cluster IDs:
        - Solar clusters: 0-23 (offset 0)
        - Wind onshore clusters: 24-42 (offset 24) 
        - Wind offshore clusters: 43-61 (offset 43)
        """
        if cluster_type != 'renewable':
            return cluster_id
        
        # Check if we have renewable results with technology information
        if (self.renewable_results and 
            'technologies' in self.renewable_results and 
            self.renewable_results['technologies']):
            
            technologies = self.renewable_results['technologies']
            
            # Determine which technology this cluster belongs to
            # We need to find the original cluster_id in the technology-specific data
            for tech, tech_result in technologies.items():
                if ('stats' in tech_result and 
                    tech_result['stats'] is not None and
                    cluster_id in tech_result['stats']['cluster_id'].values):
                    
                    # Apply the same offset logic as in _create_combined_results
                    if tech == 'solar':
                        offset = 0
                    elif tech == 'wind_onshore':
                        offset = technologies.get('solar', {}).get('n_clusters', 0)
                    elif tech == 'wind_offshore':
                        solar_count = technologies.get('solar', {}).get('n_clusters', 0)
                        onshore_count = technologies.get('wind_onshore', {}).get('n_clusters', 0)
                        offset = solar_count + onshore_count
                    else:
                        offset = 0
                    
                    return cluster_id + offset
        
        # Fallback: return original cluster_id if we can't determine offset
        return cluster_id
    
    def connect_disconnected_buses(self, max_distance_km=200):
        """
        Connect all disconnected buses to the main network using nearest neighbor approach
        
        Args:
            max_distance_km: Maximum distance for new connections
            
        Returns:
            Updated NTC matrix with new connections
        """
        print(f"\n🔌 CONNECTING DISCONNECTED BUSES")
        print("-" * 50)
        
        if self.ntc_matrix is None or len(self.ntc_matrix) == 0:
            print("❌ No NTC matrix available")
            return self.ntc_matrix
        
        try:
            import networkx as nx
        except ImportError:
            print("❌ NetworkX not available. Please install: pip install networkx")
            return self.ntc_matrix
        
        # Create graph from existing NTC connections
        G = nx.Graph()
        for _, row in self.ntc_matrix.iterrows():
            from_bus = f"{row['from_cluster_type']}{row['from_cluster_id']}"
            to_bus = f"{row['to_cluster_type']}{row['to_cluster_id']}"
            G.add_edge(from_bus, to_bus)
        
        # Find connected components
        connected_components = list(nx.connected_components(G))
        if not connected_components:
            print("❌ No connected components found")
            return self.ntc_matrix
        
        # Get main network (largest component)
        main_network = max(connected_components, key=len)
        print(f"📍 Main network: {len(main_network)} buses")
        
        # Find all buses (from cluster centers)
        all_clusters = self._get_all_cluster_centers()
        all_bus_ids = {f"{c['cluster_type']}{c['cluster_id']}" for c in all_clusters}
        
        # Find disconnected buses (sorted for deterministic results)
        disconnected_buses = sorted(list(all_bus_ids - main_network))
        print(f"🔌 Disconnected buses: {len(disconnected_buses)}")
        
        if not disconnected_buses:
            print("✅ All buses already connected")
            return self.ntc_matrix
        
        # Connect each disconnected bus (with dynamic main network updates)
        new_connections = []
        connected_count = 0
        current_connected_network = main_network.copy()  # Dynamic connected network
        
        for disconnected_bus in disconnected_buses:
            # Parse bus type and ID
            bus_type = None
            bus_id = None
            for cluster_type in ['demand', 'generation', 'renewable']:
                if disconnected_bus.startswith(cluster_type):
                    bus_type = cluster_type
                    bus_id = disconnected_bus[len(cluster_type):]
                    break
            
            if bus_type is None:
                print(f"⚠️ Could not parse bus type for {disconnected_bus}")
                continue
            
            # Find bus location
            bus_location = self._find_bus_location_by_id(bus_type, bus_id)
            if bus_location is None:
                print(f"⚠️ Could not find location for {disconnected_bus}")
                continue
            
            # Find nearest connected bus from current connected network (with relaxed rules)
            nearest_connection = self._find_nearest_connected_bus_relaxed(
                bus_location, bus_type, current_connected_network, max_distance_km
            )
            
            if nearest_connection is None:
                print(f"⚠️ No valid connection found for {disconnected_bus}")
                continue
            
            # Get original cluster IDs for readable format
            bus0_original = self._get_original_cluster_id(bus_type, bus_id)
            bus1_original = self._get_original_cluster_id(nearest_connection['cluster_type'], nearest_connection['cluster_id'])
            
            # Create descriptive type comment for disconnected bus connection
            type_description = f"Potential connection: {bus_type.capitalize()} cluster {bus_id} to {nearest_connection['cluster_type'].capitalize()} cluster {nearest_connection['cluster_id']}"
            
            # Get cluster center coordinates for both buses
            disconnected_bus_center = self._get_cluster_by_id(bus_id, bus_type)
            nearest_connection_center = self._get_cluster_by_id(nearest_connection['cluster_id'], nearest_connection['cluster_type'])
            
            if disconnected_bus_center is None or nearest_connection_center is None:
                print(f"⚠️ Warning: Could not find cluster centers for disconnected bus distance calculation")
                cluster_distance = 0
            else:
                # Calculate distance between cluster centers for disconnected bus
                cluster_distance = self._haversine_distance(
                    disconnected_bus_center['lat'], disconnected_bus_center['lng'],
                    nearest_connection_center['lat'], nearest_connection_center['lng']
                )
            
            # Add new connection
            new_connection = {
                'from_cluster_id': bus_id,
                'from_cluster_type': bus_type,
                'to_cluster_id': nearest_connection['cluster_id'],
                'to_cluster_type': nearest_connection['cluster_type'],
                'bus0': bus0_original,  # Original cluster ID (e.g., dem0, gen1, sol2)
                'bus1': bus1_original,  # Original cluster ID (e.g., dem0, gen1, won3)
                'type': type_description,  # Descriptive comment
                'line_id': f"potential_{disconnected_bus}-{nearest_connection['bus_id']}",
                's_nom': 0.0,  # Potential line with zero capacity
                'voltage': 0,  # Unknown voltage for potential line
                'length': cluster_distance,  # Distance between cluster centers
                'from_bus': disconnected_bus,
                'to_bus': nearest_connection['bus_id'],
                'connection_type': 'potential'  # Flag as potential line
            }
            
            new_connections.append(new_connection)
            connected_count += 1
            
            # Update current connected network to include this bus
            current_connected_network.add(disconnected_bus)
            
            print(f"   ✅ Connected {disconnected_bus} → {nearest_connection['bus_id']}")
        
        # Add new connections to NTC matrix
        if new_connections:
            new_connections_df = pd.DataFrame(new_connections)
            self.ntc_matrix = pd.concat([self.ntc_matrix, new_connections_df], ignore_index=True)
            
            print(f"\n✅ Connected {connected_count} disconnected buses")
            print(f"📊 Total connections: {len(self.ntc_matrix)}")
            print(f"   Existing lines: {len(self.ntc_matrix[self.ntc_matrix.get('connection_type', 'existing') == 'existing'])}")
            print(f"   Potential lines: {len(self.ntc_matrix[self.ntc_matrix.get('connection_type', 'existing') == 'potential'])}")
        else:
            print("⚠️ No new connections could be established")
        
        return self.ntc_matrix
    
    def _find_bus_location_by_id(self, bus_type, bus_id):
        """Find location of a specific bus by type and ID"""
        all_clusters = self._get_all_cluster_centers()
        
        for cluster in all_clusters:
            if (cluster['cluster_type'] == bus_type and 
                str(cluster['cluster_id']) == str(bus_id)):
                return {
                    'lat': cluster['lat'],
                    'lng': cluster['lng']
                }
        
        return None
    
    def _find_nearest_connected_bus(self, bus_location, bus_type, main_network, max_distance_km):
        """Find nearest connected bus that allows valid connection"""
        all_clusters = self._get_all_cluster_centers()
        
        # Get all connected buses with their locations
        connected_candidates = []
        for cluster in all_clusters:
            bus_id = f"{cluster['cluster_type']}{cluster['cluster_id']}"
            if bus_id in main_network:
                connected_candidates.append({
                    'cluster_id': cluster['cluster_id'],
                    'cluster_type': cluster['cluster_type'],
                    'bus_id': bus_id,
                    'lat': cluster['lat'],
                    'lng': cluster['lng']
                })
        
        if not connected_candidates:
            return None
        
        # Find nearest valid connection
        min_distance = float('inf')
        best_connection = None
        
        for candidate in connected_candidates:
            # Check if connection is valid
            if not self._is_valid_connection(bus_type, candidate['cluster_type']):
                continue
            
            # Calculate distance
            distance = self._haversine_distance(
                bus_location['lat'], bus_location['lng'],
                candidate['lat'], candidate['lng']
            )
            
            # Check distance limit
            if distance > max_distance_km:
                continue
            
            # Check if this is the closest valid connection
            if distance < min_distance:
                min_distance = distance
                best_connection = candidate
        
        return best_connection
    
    def _find_nearest_connected_bus_relaxed(self, bus_location, bus_type, connected_network, max_distance_km):
        """
        Find nearest connected bus with relaxed priority rules for disconnected buses
        
        For disconnected buses, we prioritize distance over strict connection rules.
        This allows bidirectional connections (e.g., demand can connect to generation)
        to find the shortest possible connection.
        """
        all_clusters = self._get_all_cluster_centers()
        
        # Get all connected buses with their locations
        connected_candidates = []
        for cluster in all_clusters:
            bus_id = f"{cluster['cluster_type']}{cluster['cluster_id']}"
            if bus_id in connected_network:
                connected_candidates.append({
                    'cluster_id': cluster['cluster_id'],
                    'cluster_type': cluster['cluster_type'],
                    'bus_id': bus_id,
                    'lat': cluster['lat'],
                    'lng': cluster['lng']
                })
        
        if not connected_candidates:
            return None
        
        # Find nearest valid connection (with relaxed rules)
        min_distance = float('inf')
        best_connection = None
        
        for candidate in connected_candidates:
            # Check if connection is valid in either direction
            valid_forward = self._is_valid_connection(bus_type, candidate['cluster_type'])
            valid_reverse = self._is_valid_connection(candidate['cluster_type'], bus_type)
            
            if not (valid_forward or valid_reverse):
                continue  # Skip if neither direction is valid
            
            # Calculate distance
            distance = self._haversine_distance(
                bus_location['lat'], bus_location['lng'],
                candidate['lat'], candidate['lng']
            )
            
            # Check distance limit
            if distance > max_distance_km:
                continue
            
            # Check if this is the closest valid connection
            if distance < min_distance:
                min_distance = distance
                best_connection = candidate
        
        return best_connection
    
    def save_results(self):
        """Save all mapping and NTC results to CSV files"""
        output_path = Path(self.output_dir)
        
        # Save substation cluster mapping
        if self.substation_cluster_mapping is not None:
            mapping_file = output_path / f'{self.country}_substation_cluster_mapping.csv'
            self.substation_cluster_mapping.to_csv(mapping_file, index=False)
            print(f"💾 Saved substation mapping: {mapping_file}")
        
        # Save NTC matrix
        if self.ntc_matrix is not None and len(self.ntc_matrix) > 0:
            ntc_file = output_path / f'{self.country}_clustered_lines.csv'
            self.ntc_matrix.to_csv(ntc_file, index=False)
            print(f"💾 Saved NTC matrix: {ntc_file}")
        
        # Save clustered buses data
        self._save_clustered_buses_data(output_path)
        
        # Save synthetic grid summary
        self._save_synthetic_grid_summary()
    
    def _save_clustered_buses_data(self, output_path):
        """Create and save clustered buses data using utility function"""
        try:
            from syn_grids_1.clustered_buses_utils import prepare_clustered_buses_data, save_clustered_buses_csv
            
            # Prepare clustered buses data
            clustered_buses_df = prepare_clustered_buses_data(
                demand_results=self.demand_results,
                generation_results=self.generation_results,
                renewable_results=self.renewable_results
            )
            
            # Save to CSV
            save_clustered_buses_csv(clustered_buses_df, output_path, self.country)
                
        except Exception as e:
            print(f"❌ Error saving clustered buses data: {e}")
    
    def _save_synthetic_grid_summary(self):
        """Create and save synthetic grid summary"""
        summary = {
            'country': self.country,
            'grid_data_source': self.grid_data_dir,
            'total_substations': int(len(self.substations) if self.substations is not None else 0),
            'total_lines': int(len(self.transmission_lines) if self.transmission_lines is not None else 0),
            'total_capacity_mva': float(self.transmission_lines['s_nom'].sum() if self.transmission_lines is not None else 0),
        }
        
        # Add cluster summary
        if self.substation_cluster_mapping is not None:
            cluster_summary = self.substation_cluster_mapping.groupby('cluster_type').agg({
                'bus_id': 'count',
                'cluster_id': 'nunique'
            })
            # Convert to JSON-serializable format
            summary['clusters'] = {
                cluster_type: {
                    'num_substations': int(data['bus_id']),
                    'num_clusters': int(data['cluster_id'])
                }
                for cluster_type, data in cluster_summary.iterrows()
            }
        
        # Add NTC summary
        if self.ntc_matrix is not None and len(self.ntc_matrix) > 0:
            summary['ntc_summary'] = {
                'total_connections': int(len(self.ntc_matrix)),
                'total_ntc_capacity_mva': float(self.ntc_matrix['s_nom'].sum()),
                'total_lines': int(self.ntc_matrix['num_lines'].sum())
            }
        
        # Save summary
        summary_file = Path(self.output_dir) / f'{self.country}_synthetic_grid_summary.json'
        import json
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"💾 Saved synthetic grid summary: {summary_file}")
    
    def create_full_pipeline(self):
        """Run the complete substation mapping and NTC calculation pipeline"""
        print(f"🏗️ SYNTHETIC GRID PIPELINE FOR {self.country}")
        print("=" * 60)
        
        try:
            # Step 1: Load cluster data
            self.load_cluster_data()
            
            # Step 2: Load grid infrastructure 
            self.load_grid_infrastructure()
            
            # Step 3: Create cluster shapes
            self.create_cluster_shapes()
            
            # Step 4: Assign substations to clusters
            self.assign_substations_to_clusters()
            
            # Step 5: Calculate inter-cluster NTC
            self.calculate_inter_cluster_ntc()
            
            # Step 6: Add water crossing detection
            self.add_water_detection_to_ntc()
            
            # Step 7: Save results
            self.save_results()
            
            print(f"\n🎉 SYNTHETIC GRID PIPELINE COMPLETED!")
            print("=" * 60)
            print(f"✅ Substations mapped to clusters")
            print(f"✅ Inter-cluster NTC calculated")
            print(f"✅ Water crossing detection added")
            print(f"✅ Results saved to {self.output_dir}")
            
            return True
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_water_data(self, water_data_dir='data/country_data/naturalearth'):
        """
        Load Natural Earth water data and create spatial index
        
        Args:
            water_data_dir: Directory containing Natural Earth shapefiles
        """
        try:
            print("🌊 Loading water data for crossing detection...")
            
            water_dir = Path(water_data_dir)
            ocean_file = water_dir / 'ne_50m_ocean' / 'ne_50m_ocean.shp'
            lakes_file = water_dir / 'ne_50m_lakes' / 'ne_50m_lakes.shp'
            
            water_polygons = []
            
            # Load ocean data
            if ocean_file.exists():
                ocean_gdf = gpd.read_file(ocean_file)
                print(f"🌊 Loaded {len(ocean_gdf)} ocean polygons")
                water_polygons.extend(ocean_gdf.geometry.tolist())
            else:
                print(f"⚠️ Ocean file not found: {ocean_file}")
            
            # Load lakes data
            if lakes_file.exists():
                lakes_gdf = gpd.read_file(lakes_file)
                print(f"🏞️ Loaded {len(lakes_gdf)} lake polygons")
                water_polygons.extend(lakes_gdf.geometry.tolist())
            else:
                print(f"⚠️ Lakes file not found: {lakes_file}")
            
            if not water_polygons:
                print("❌ No water data loaded")
                return False
            
            # Create spatial index for fast queries
            self.water_index = index.Index()
            self.water_data = []
            
            for i, polygon in enumerate(water_polygons):
                if polygon is not None and not polygon.is_empty:
                    # Get bounding box for spatial index
                    bounds = polygon.bounds
                    self.water_index.insert(i, bounds)
                    self.water_data.append(polygon)
            
            print(f"✅ Water data loaded: {len(self.water_data)} polygons indexed")
            
            # Debug: Show bounds of loaded water data
            if self.water_data:
                all_bounds = [polygon.bounds for polygon in self.water_data if polygon is not None]
                if all_bounds:
                    min_lng = min(bounds[0] for bounds in all_bounds)
                    max_lng = max(bounds[2] for bounds in all_bounds)
                    min_lat = min(bounds[1] for bounds in all_bounds)
                    max_lat = max(bounds[3] for bounds in all_bounds)
                    print(f"🔍 Debug: Water data bounds: lng({min_lng:.2f} to {max_lng:.2f}), lat({min_lat:.2f} to {max_lat:.2f})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading water data: {e}")
            return False

    def detect_water_crossing(self, from_lat, from_lng, to_lat, to_lng, sample_distance_km=2.0):
        """
        Detect if a transmission line crosses water bodies
        
        Args:
            from_lat, from_lng: Starting coordinates
            to_lat, to_lng: Ending coordinates  
            sample_distance_km: Distance between sample points along line
            
        Returns:
            dict: Water crossing information
        """
        if self.water_data is None or self.water_index is None:
            print(f"⚠️ Water data not loaded: data={self.water_data is not None}, index={self.water_index is not None}")
            return {
                'length': 0,
                'water_distance_km': 0,
                'water_share': 0.0,
                'crosses_water': False,
                'water_types': []
            }
        
        try:
            # Calculate total distance
            total_distance = self._haversine_distance(from_lat, from_lng, to_lat, to_lng)
            
            # Create line geometry
            line = LineString([(from_lng, from_lat), (to_lng, to_lat)])
            
            # Sample points along the line
            num_samples = max(2, int(total_distance / sample_distance_km))
            sample_points = []
            
            for i in range(num_samples):
                fraction = i / (num_samples - 1) if num_samples > 1 else 0
                lat = from_lat + (to_lat - from_lat) * fraction
                lng = from_lng + (to_lng - from_lng) * fraction
                sample_points.append(Point(lng, lat))
            
            # Check which points are in water
            water_points = 0
            water_types = set()
            
            for i, point in enumerate(sample_points):
                # Use spatial index to find candidate water polygons
                candidates = list(self.water_index.intersection(point.bounds))
                
                for candidate_idx in candidates:
                    if candidate_idx < len(self.water_data):
                        water_polygon = self.water_data[candidate_idx]
                        if water_polygon.contains(point):
                            water_points += 1
                            # Determine water type based on polygon size
                            area_km2 = water_polygon.area * (111.32 ** 2)  # Rough conversion
                            if area_km2 > 10000:  # Large water body
                                water_types.add('ocean')
                            elif area_km2 > 100:  # Medium water body
                                water_types.add('lake')
                            else:  # Small water body
                                water_types.add('water')
                            break  # Point is in water, no need to check other polygons
            
            # Calculate water share
            water_share = water_points / len(sample_points) if sample_points else 0
            water_distance = total_distance * water_share
            
            return {
                'length': total_distance,
                'water_distance_km': water_distance,
                'water_share': water_share,
                'crosses_water': water_share > self.water_threshold,
                'water_types': list(water_types)
            }
            
        except Exception as e:
            print(f"❌ Error detecting water crossing: {e}")
            return {
                'length': 0,
                'water_distance_km': 0,
                'water_share': 0.0,
                'crosses_water': False,
                'water_types': []
            }

    def add_water_detection_to_ntc(self):
        """
        Add water crossing detection to NEW connections only (disconnected bus links)
        """
        if not WATER_DETECTION_AVAILABLE:
            print("⚠️ Skipping water detection - dependencies not available")
            return False
            
        if self.ntc_matrix is None:
            print("❌ No NTC matrix available for water detection")
            return False
        
        try:
            print("🌊 Adding water crossing detection to NEW connections only...")
            
            # Load water data if not already loaded
            if self.water_data is None:
                if not self.load_water_data():
                    print("⚠️ Skipping water detection - no water data available")
                    return False
            
            # Initialize water detection columns with default values
            water_info = []
            new_connection_count = 0
            
            for _, connection in self.ntc_matrix.iterrows():
                # Only detect water for NEW connections (capacity = 0)
                if connection['s_nom'] == 0:
                    new_connection_count += 1
                    # print(f"🔍 Debug: Processing new connection #{new_connection_count}: {connection['from_cluster_type']}{connection['from_cluster_id']} → {connection['to_cluster_type']}{connection['to_cluster_id']}")
                    
                    # This is a new connection for disconnected buses
                    from_cluster = self._get_cluster_by_id(
                        connection['from_cluster_id'], 
                        connection['from_cluster_type']
                    )
                    to_cluster = self._get_cluster_by_id(
                        connection['to_cluster_id'], 
                        connection['to_cluster_type']
                    )
                    
                    if from_cluster and to_cluster:
                        # print(f"🔍 Debug: Cluster locations - From: ({from_cluster['lat']:.3f}, {from_cluster['lng']:.3f}), To: ({to_cluster['lat']:.3f}, {to_cluster['lng']:.3f})")
                        # Detect water crossing for new connection
                        water_data = self.detect_water_crossing(
                            from_cluster['lat'], from_cluster['lng'],
                            to_cluster['lat'], to_cluster['lng']
                        )
                        water_info.append(water_data)
                    else:
                        print(f"⚠️ Debug: Could not find cluster locations for connection")
                        # Default values if clusters not found
                        water_info.append({
                            'length': 0,
                            'water_distance_km': 0,
                            'water_share': 0.0,
                            'crosses_water': False,
                            'water_types': []
                        })
                else:
                    # Existing connection - no water detection needed
                    water_info.append({
                        'length': connection.get('length', 0),  # Use calculated cluster distance
                        'water_distance_km': 0,
                        'water_share': 0.0,
                        'crosses_water': False,
                        'water_types': []
                    })
            
            # Add water columns to NTC matrix
            water_df = pd.DataFrame(water_info)
            self.ntc_matrix = pd.concat([self.ntc_matrix, water_df], axis=1)
            
            # Summary statistics
            total_connections = len(self.ntc_matrix)
            new_connections = (self.ntc_matrix['s_nom'] == 0).sum()
            water_crossings = self.ntc_matrix['crosses_water'].sum()
            
            print(f"✅ Water detection complete:")
            print(f"   📊 Total connections: {total_connections}")
            print(f"   🆕 New connections analyzed: {new_connections}")
            print(f"   🌊 Water crossings detected: {water_crossings}")
            if new_connections > 0:
                print(f"   📈 Water crossing rate: {water_crossings/new_connections*100:.1f}% of new connections")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding water detection: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_cluster_by_id(self, cluster_id, cluster_type):
        """Helper method to get cluster by ID and type"""
        all_clusters = self._get_all_cluster_centers()
        
        # Convert cluster_id to integer if it's a string
        try:
            cluster_id_int = int(cluster_id)
        except (ValueError, TypeError):
            cluster_id_int = cluster_id
        
        for cluster in all_clusters:
            if (cluster['cluster_id'] == cluster_id_int and 
                cluster['cluster_type'] == cluster_type):
                return cluster
        return None


def main():
    parser = argparse.ArgumentParser(description='Map substations to clusters and calculate NTC')
    parser.add_argument('--country', required=True, help='Country code (should match grid data)')
    parser.add_argument('--output-dir', required=True, help='Directory containing cluster CSV files')
    parser.add_argument('--grid-data-dir', default=None, 
                       help='Directory containing grid infrastructure data (auto-detected if not specified)')
    
    args = parser.parse_args()
    
    # Create mapper
    mapper = SubstationGridMapper(
        country_code=args.country,
        output_dir=args.output_dir,
        grid_data_dir=args.grid_data_dir
    )
    
    # Run complete pipeline
    success = mapper.create_full_pipeline()
    
    if success:
        print(f"\n🚀 Ready for synthetic grid modeling!")
        print(f"📊 Check output files in: {args.output_dir}")
    else:
        print(f"\n💥 Pipeline failed - check logs above")


if __name__ == "__main__":
    main()
