#!/usr/bin/env python3
"""
VerveStacks Economic Atlas Generator
===================================

Creates a comprehensive 3-panel portrait visualization showing:
1. DEMAND: Scaled circles showing absolute demand by region
2. GENERATION: Scaled pie charts showing capacity and technology mix
3. RENEWABLES: LCOE-optimized zones with TWh filtering from NGFS scenarios

This visual summary replaces text reports with an intuitive economic geography
of energy transition possibilities.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend to prevent hanging
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Wedge, Polygon
from scipy.spatial import ConvexHull
import argparse
import os
import sys
import pickle
from pathlib import Path
import json

# Import smart formatting function from main project utils
sys.path.append('..')
from data_utils import smart_format_number

# Try to import geopandas for shapefile reading
try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

def get_country_boundaries(country_code, data_bounds=None):
    """
    Get country boundary coordinates, filtering out distant territories
    
    Args:
        country_code: ISO3 country code
        data_bounds: (min_lng, max_lng, min_lat, max_lat) to filter territories
    
    Returns:
        List of coordinate arrays for country boundaries
    """
    try:
        boundaries = []
        
        # Try Natural Earth shapefile first (most reliable)
        if GEOPANDAS_AVAILABLE:
            ne_shapefile = '../data/country_data/naturalearth/ne_10m_admin_0_countries_lakes.shp'
            if os.path.exists(ne_shapefile):
                gdf = gpd.read_file(ne_shapefile)
                # Filter by ISO3 code
                country_gdf = gdf[gdf['ADM0_A3'] == country_code]
                
                if len(country_gdf) > 0:
                    for _, row in country_gdf.iterrows():
                        geom = row.geometry
                        
                        if geom.geom_type == 'Polygon':
                            coords = list(geom.exterior.coords)
                            boundaries.append(np.array(coords))
                        elif geom.geom_type == 'MultiPolygon':
                            for polygon in geom.geoms:
                                coords = list(polygon.exterior.coords)
                                coord_array = np.array(coords)
                                
                                # Filter out distant territories if data bounds provided
                                if data_bounds:
                                    min_lng, max_lng, min_lat, max_lat = data_bounds
                                    # Keep polygons that overlap with data bounds (with buffer)
                                    buffer = 3.0  # degrees
                                    poly_min_lng, poly_max_lng = coord_array[:, 0].min(), coord_array[:, 0].max()
                                    poly_min_lat, poly_max_lat = coord_array[:, 1].min(), coord_array[:, 1].max()
                                    
                                    if (poly_max_lng >= min_lng - buffer and poly_min_lng <= max_lng + buffer and
                                        poly_max_lat >= min_lat - buffer and poly_min_lat <= max_lat + buffer):
                                        boundaries.append(coord_array)
                                else:
                                    boundaries.append(coord_array)
                    
                    return boundaries if boundaries else None
        
        # Fallback: try NUTS geojson for European countries
        nuts_geojson = '../data/country_data/nuts/NUTS_RG_01M_2021_4326_LEVL_0.geojson'
        if os.path.exists(nuts_geojson):
            with open(nuts_geojson, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            if geojson_data and 'features' in geojson_data:
                for feature in geojson_data['features']:
                    # Check if this feature matches our country (NUTS uses different codes)
                    props = feature.get('properties', {})
                    cntr_code = props.get('CNTR_CODE', '')
                    
                    # Simple mapping for common countries
                    country_mapping = {'CH': 'CHE', 'DE': 'DEU', 'FR': 'FRA', 'IT': 'ITA', 'ES': 'ESP'}
                    if cntr_code in country_mapping and country_mapping[cntr_code] == country_code:
                        geom = feature['geometry']
                        if geom['type'] == 'Polygon':
                            coords = geom['coordinates'][0]
                            boundaries.append(np.array(coords))
                        elif geom['type'] == 'MultiPolygon':
                            for polygon in geom['coordinates']:
                                coords = polygon[0]
                                boundaries.append(np.array(coords))
        
        return boundaries if boundaries else None
        
    except Exception as e:
        print(f"Could not load country boundaries for {country_code}: {e}")
        return None

def draw_country_boundaries(ax, country_code, data_bounds=None):
    """
    Draw country boundaries as background
    
    Args:
        ax: Matplotlib axis
        country_code: ISO3 country code  
        data_bounds: (min_lng, max_lng, min_lat, max_lat) to filter territories
    """
    boundaries = get_country_boundaries(country_code, data_bounds)
    
    if boundaries:
        for boundary in boundaries:
            if len(boundary) > 2:  # Need at least 3 points
                polygon = Polygon(boundary, facecolor='none', edgecolor='gray', 
                                linewidth=0.8, alpha=0.4, zorder=-1)
                ax.add_patch(polygon)
    else:
        # Fallback: draw a simple bounding box
        if data_bounds:
            min_lng, max_lng, min_lat, max_lat = data_bounds
            buffer = 0.5
            rect_coords = [
                [min_lng - buffer, min_lat - buffer],
                [max_lng + buffer, min_lat - buffer], 
                [max_lng + buffer, max_lat + buffer],
                [min_lng - buffer, max_lat + buffer]
            ]
            polygon = Polygon(rect_coords, facecolor='none', edgecolor='lightgray',
                            linewidth=1, alpha=0.3, zorder=-1, linestyle='--')
            ax.add_patch(polygon)

def draw_cluster_shapes(ax, cluster_mapping, cluster_id_col='cluster_id', color='lightblue', alpha=0.2, 
                       min_generation_gwh=1000, min_capacity_mw=50, min_population=100000):
    """
    Draw convex hull shapes around cluster points with unique colors per cluster
    
    Args:
        ax: Matplotlib axis
        cluster_mapping: DataFrame with lat, lng, and cluster_id columns
        cluster_id_col: Name of cluster ID column
        color: Base color (will be overridden with unique colors)
        alpha: Transparency level
        min_generation_gwh: Minimum generation for renewable grid cells (default: 1000 GWh)
        min_capacity_mw: Minimum capacity for power plants (default: 50 MW)
        min_population: Minimum population for cities (default: 100,000)
    """
    if cluster_mapping is None or len(cluster_mapping) == 0:
        return
    
    # Define distinct colors for different clusters
    cluster_colors = [
        '#E8F5E8',  # Light green
        '#E8F0FF',  # Light blue  
        '#FFF0E8',  # Light orange
        '#F0E8FF',  # Light purple
        '#FFE8F0',  # Light pink
        '#F0FFE8',  # Light lime
        '#E8FFFF',  # Light cyan
        '#FFFFE8',  # Light yellow
        '#FFE8E8',  # Light red
        '#F5F5E8'   # Light beige
    ]
    
    cluster_ids = sorted(cluster_mapping[cluster_id_col].unique())
    
    for i, cluster_id in enumerate(cluster_ids):
        cluster_points = cluster_mapping[cluster_mapping[cluster_id_col] == cluster_id]
        
        # Apply visualization thresholds to filter out small/remote facilities
        filtered_points = cluster_points.copy()
        
        # Filter by generation (for renewable grid cells)
        if 'total_generation_gwh' in filtered_points.columns:
            filtered_points = filtered_points[filtered_points['total_generation_gwh'] >= min_generation_gwh]
        
        # Filter by capacity (for power plants)  
        elif 'total_capacity_mw' in filtered_points.columns:
            filtered_points = filtered_points[filtered_points['total_capacity_mw'] >= min_capacity_mw]
        
        # Filter by population (for cities)
        elif 'scaled_weight' in filtered_points.columns:
            # scaled_weight is population in thousands
            filtered_points = filtered_points[filtered_points['scaled_weight'] >= min_population/1000]
        
        # Use filtered points for hull calculation
        cluster_points = filtered_points
        
        if len(cluster_points) < 3:
            # Need at least 3 points for a hull, skip if too few
            continue
            
        try:
            # Get coordinates
            points = cluster_points[['lng', 'lat']].values
            
            # Create convex hull
            hull = ConvexHull(points)
            hull_points = points[hull.vertices]
            
            # Get unique color for this cluster
            fill_color = cluster_colors[i % len(cluster_colors)]
            
            # Draw polygon with thin border
            polygon = Polygon(hull_points, 
                            facecolor=fill_color, 
                            edgecolor='darkgray', 
                            linewidth=0.5,
                            alpha=alpha, 
                            zorder=0)
            ax.add_patch(polygon)
            
        except Exception as e:
            # Skip if hull calculation fails
            continue

class EconomicAtlasGenerator:
    """
    Generate comprehensive visual summary of multi-layered energy analysis
    """
    
    def __init__(self, country, output_dir):
        self.country = country
        self.output_dir = output_dir
        self.fig = None
        self.axes = None
        
        # Load all required data
        self.demand_data = None
        self.gem_data = None
        self.renewable_data = None
        self.ngfs_twh_target = None
        self.data_bounds = None
    
    def _estimate_text_width_degrees(self, text, fontsize, ax):
        """Estimate text width in map degrees for label positioning"""
        # Create temporary text to measure dimensions
        temp_text = ax.text(0, 0, text, fontsize=fontsize, alpha=0)
        
        # Get bounding box in display coordinates
        renderer = ax.figure.canvas.get_renderer()
        bbox = temp_text.get_window_extent(renderer=renderer)
        temp_text.remove()
        
        # Convert pixels to degrees based on current axis scaling
        # Get the transformation from data coordinates to display coordinates
        x_range = ax.get_xlim()
        display_range = ax.transData.transform([(x_range[0], 0), (x_range[1], 0)])
        pixels_per_degree = (display_range[1][0] - display_range[0][0]) / (x_range[1] - x_range[0])
        
        width_degrees = bbox.width / pixels_per_degree if pixels_per_degree > 0 else 0.5
        return max(0.3, width_degrees)  # Minimum reasonable width
    
    def _check_label_space_available(self, center_lng, center_lat, radius, label_text, fontsize, ax, side='left'):
        """Check if there's enough space for a label on the specified side of a shape"""
        # Estimate label dimensions
        label_width = self._estimate_text_width_degrees(label_text, fontsize, ax)
        padding = 0.2  # Degrees of padding around label
        
        # Calculate required space
        required_space = label_width + padding * 2
        
        # Check frame boundaries
        if side == 'left':
            # Position would be to the left of the shape
            label_center_lng = center_lng - radius - label_width/2 - padding
            available_space = label_center_lng - (label_width/2) - self.lng_bounds[0]
        else:  # right
            # Position would be to the right of the shape  
            label_center_lng = center_lng + radius + label_width/2 + padding
            available_space = self.lng_bounds[1] - (label_center_lng + label_width/2)
        
        # Check if we have enough space to frame boundary
        if available_space < 0:
            return False, 0, 0
            
        # Check for conflicts with other shapes (simplified heuristic)
        # For now, check if any other renewable zone centers are too close
        min_clearance = label_width + 0.5  # Minimum clearance from other pie charts
        
        for _, other_zone in self.renewable_data['centers'].iterrows():
            other_center_lng = other_zone['center_lng']
            other_center_lat = other_zone['center_lat']
            
            # Skip self
            if abs(other_center_lng - center_lng) < 0.01 and abs(other_center_lat - center_lat) < 0.01:
                continue
                
            # Check distance to proposed label position
            distance = ((label_center_lng - other_center_lng)**2 + (center_lat - other_center_lat)**2)**0.5
            if distance < min_clearance:
                return False, 0, 0
        
        return True, label_center_lng, center_lat
        
    def load_analysis_data(self):
        """Load all clustering results and NGFS data"""
        print(f"Loading analysis data for {self.country}...")
        
        try:
            # Load demand regions
            self.demand_data = {
                'centers': pd.read_csv(f'{self.output_dir}/{self.country}_region_centers.csv'),
                'points': pd.read_csv(f'{self.output_dir}/{self.country}_demand_points.csv')
            }
            
            # Load GEM clusters
            self.gem_data = {
                'centers': pd.read_csv(f'{self.output_dir}/{self.country}_gem_cluster_centers.csv'),
                'mapping': pd.read_csv(f'{self.output_dir}/{self.country}_gem_cluster_mapping.csv')
            }
            
            # Load renewable clusters (before LCOE filtering)
            self.renewable_data = {
                'centers': pd.read_csv(f'{self.output_dir}/{self.country}_renewable_cluster_centers.csv'),
                'mapping': pd.read_csv(f'{self.output_dir}/{self.country}_renewable_cluster_mapping.csv')
            }
            
            print(f"Loaded {len(self.demand_data['centers'])} demand regions")
            print(f"Loaded {len(self.gem_data['centers'])} generation clusters")
            print(f"Loaded {len(self.renewable_data['centers'])} renewable zones")
            
            # Calculate data bounds for country boundary filtering
            self._calculate_data_bounds()
            
        except Exception as e:
            print(f"Error loading analysis data: {e}")
            raise
    
    def _calculate_data_bounds(self):
        """Calculate geographic bounds of all data points"""
        all_lats, all_lngs = [], []
        
        # Collect coordinates from all data sources
        for data_source in [self.demand_data, self.gem_data, self.renewable_data]:
            if 'centers' in data_source and len(data_source['centers']) > 0:
                centers = data_source['centers']
                if 'center_lat' in centers.columns:
                    all_lats.extend(centers['center_lat'].tolist())
                    all_lngs.extend(centers['center_lng'].tolist())
            
            # Also check mapping data for more precise bounds
            for key in ['points', 'mapping']:
                if key in data_source and len(data_source[key]) > 0:
                    mapping = data_source[key]
                    if 'lat' in mapping.columns:
                        all_lats.extend(mapping['lat'].tolist())
                        all_lngs.extend(mapping['lng'].tolist())
        
        if all_lats and all_lngs:
            # Add small buffer around data
            buffer = 0.5  # degrees
            self.data_bounds = (
                min(all_lngs) - buffer, max(all_lngs) + buffer,
                min(all_lats) - buffer, max(all_lats) + buffer
            )
        else:
            self.data_bounds = None
    
    def _filter_contiguous_us_data(self, data_dict):
        """Filter data to show only contiguous US (exclude Alaska and Hawaii) for visualization"""
        if self.country != 'USA':
            return data_dict
        
        # Contiguous US bounds (roughly)
        contiguous_bounds = {
            'lat_min': 24.0,   # Southern Florida
            'lat_max': 49.5,   # Northern border
            'lng_min': -125.0, # West coast
            'lng_max': -66.0   # East coast
        }
        
        filtered_data = {}
        
        for key, data in data_dict.items():
            if key == 'centers' and isinstance(data, pd.DataFrame):
                # Filter cluster centers
                mask = (
                    (data['center_lat'] >= contiguous_bounds['lat_min']) &
                    (data['center_lat'] <= contiguous_bounds['lat_max']) &
                    (data['center_lng'] >= contiguous_bounds['lng_min']) &
                    (data['center_lng'] <= contiguous_bounds['lng_max'])
                )
                filtered_data[key] = data[mask].copy()
                
                # Log what was filtered out
                excluded = data[~mask]
                if len(excluded) > 0:
                    print(f"  Excluding {len(excluded)} clusters outside contiguous US for visualization:")
                    for _, cluster in excluded.iterrows():
                        name = cluster.get('name', f"Cluster_{cluster.get('cluster_id', 'unknown')}")
                        print(f"    {name}: ({cluster['center_lat']:.1f}, {cluster['center_lng']:.1f})")
            else:
                # Keep other data as-is
                filtered_data[key] = data
        
        return filtered_data
    
    def _set_country_bounds(self):
        """Set axis bounds to show the full country"""
        # Special handling for USA - focus on contiguous 48 states
        if self.country == 'USA':
            print("Setting bounds for contiguous US (excluding Alaska/Hawaii)")
            self.lat_bounds = (24.0, 49.5)   # Contiguous US latitude range
            self.lng_bounds = (-125.0, -66.0) # Contiguous US longitude range
            return
        
        # Try to get country boundaries to determine proper zoom level
        boundaries = get_country_boundaries(self.country, self.data_bounds)
        
        if boundaries:
            # Calculate bounds from country boundaries
            all_lats, all_lngs = [], []
            for boundary in boundaries:
                all_lats.extend(boundary[:, 1])  # latitude
                all_lngs.extend(boundary[:, 0])  # longitude
            
            if all_lats and all_lngs:
                # Add margin for better visualization
                lat_range = max(all_lats) - min(all_lats)
                lng_range = max(all_lngs) - min(all_lngs)
                margin = max(lat_range, lng_range) * 0.05  # 5% margin
                
                self.lat_bounds = (min(all_lats) - margin, max(all_lats) + margin)
                self.lng_bounds = (min(all_lngs) - margin, max(all_lngs) + margin)
                return
        
        # Fallback: use data bounds with larger buffer
        if self.data_bounds:
            min_lng, max_lng, min_lat, max_lat = self.data_bounds
            # Expand data bounds to show more context
            lat_range = max_lat - min_lat
            lng_range = max_lng - min_lng
            buffer = max(lat_range, lng_range) * 0.3  # 30% buffer
            
            self.lat_bounds = (min_lat - buffer, max_lat + buffer)
            self.lng_bounds = (min_lng - buffer, max_lng + buffer)
        else:
            # Default bounds for Switzerland
            self.lat_bounds = (45.8, 47.8)
            self.lng_bounds = (5.9, 10.5)
    
    def load_ngfs_twh_target(self):
        """Load NGFS scenarios and find max electricity generation target"""
        print(f"Loading NGFS electricity target for {self.country}...")
        
        try:
            # Load NGFS data from cache
            ngfs_data = self._load_ngfs_from_cache()
            
            if ngfs_data is None or len(ngfs_data) == 0:
                print("NGFS data not found, using default target")
                self.ngfs_twh_target = 1000  # Default 1000 TWh
                return
            
            # Filter for Secondary Energy|Electricity for this country
            electricity_data = ngfs_data[
                (ngfs_data['Variable'] == 'Secondary Energy|Electricity') &
                (ngfs_data['Region'] == self.country)
            ]
            
            if len(electricity_data) == 0:
                print(f"No electricity data found for {self.country}, using default")
                self.ngfs_twh_target = 1000
                return
            
            # Get year columns (2020-2050)
            year_columns = [col for col in electricity_data.columns 
                           if col.isdigit() and int(col) <= 2050]
            
            if year_columns:
                # Get all numeric values and find maximum across all scenarios/models/years
                all_values = []
                for col in year_columns:
                    col_values = pd.to_numeric(electricity_data[col], errors='coerce').dropna()
                    all_values.extend(col_values.tolist())
                
                if all_values:
                    max_value = max(all_values)
                    # Convert from EJ to TWh if needed (1 EJ = 277.78 TWh)
                    if max_value < 100:  # Likely in EJ
                        max_value = max_value * 277.78
                    
                    self.ngfs_twh_target = max_value
                    print(f"NGFS electricity target: {self.ngfs_twh_target:.0f} TWh (max across all scenarios ≤2050)")
                else:
                    print("No valid numeric values found, using default")
                    self.ngfs_twh_target = 1000
            else:
                print("No year columns found, using default")
                self.ngfs_twh_target = 1000
                
        except Exception as e:
            print(f"Error loading NGFS data: {e}, using default target")
            self.ngfs_twh_target = 1000
    
    def _load_ngfs_from_cache(self):
        """Load NGFS data from cache files"""
        cache_files = [
            '../cache/global_data_cache.pkl',
            '../cache/ngfs_data_cache.pkl',
            '../../cache/global_data_cache.pkl',
            '../../cache/ngfs_data_cache.pkl'
        ]
        
        for cache_file in cache_files:
            if os.path.exists(cache_file):
                print(f"Loading NGFS data from {cache_file}")
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    # Check for the correct key name
                    if 'ngfs_df' in cached_data:
                        return cached_data['ngfs_df']
                    elif 'ngfs_data' in cached_data:
                        return cached_data['ngfs_data']
                    elif isinstance(cached_data, pd.DataFrame):
                        return cached_data
        
        return None
    

    def create_atlas_figure(self):
        """Create the 3-panel portrait figure"""
        print("Creating economic atlas figure...")
        
        # Create portrait figure (taller than wide)
        self.fig, self.axes = plt.subplots(3, 1, figsize=(12, 16))
        self.fig.suptitle(f'{self.country} Energy System Economic Atlas', fontsize=20, fontweight='bold')
        
        # Set panel titles
        self.axes[0].set_title('DEMAND REGIONS\nAbsolute Demand Distribution', fontsize=14, fontweight='bold', pad=20)
        self.axes[1].set_title('GENERATION CLUSTERS\nExisting Capacity & Technology Mix', fontsize=14, fontweight='bold', pad=20)
        self.axes[2].set_title('RENEWABLE ZONES\nSolar/Wind Generation Potential', fontsize=14, fontweight='bold', pad=20)
        
        # Get geographic bounds to show full country
        self._set_country_bounds()
        
        # Set consistent bounds for all panels
        for ax in self.axes:
            ax.set_xlim(self.lng_bounds)
            ax.set_ylim(self.lat_bounds)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
    
    def plot_demand_panel(self):
        """Plot demand regions as scaled circles"""
        print("Plotting demand regions...")
        
        ax = self.axes[0]
        # Filter for contiguous US if applicable
        filtered_demand_data = self._filter_contiguous_us_data(self.demand_data)
        demand_centers = filtered_demand_data['centers']
        
        # Draw country boundaries first (deepest background)
        draw_country_boundaries(ax, self.country, self.data_bounds)
        
        # Draw cluster shapes (background) - no thresholds needed with Voronoi
        # Voronoi clustering ensures non-overlapping regions, so we can show all points
        if 'points' in filtered_demand_data and len(filtered_demand_data['points']) > 0:
            print(f"Drawing demand shapes for {len(filtered_demand_data['points'])} cities")
            draw_cluster_shapes(ax, filtered_demand_data['points'], 'cluster', 
                              color='lightblue', alpha=0.3, min_population=0)
        else:
            print("No demand points data found for shape drawing")
        
        if len(demand_centers) == 0:
            ax.text(0.5, 0.5, 'No demand data available', transform=ax.transAxes, 
                   ha='center', va='center', fontsize=12)
            return
        
        # Calculate adaptive font sizes based on country size
        country_width = self.lng_bounds[1] - self.lng_bounds[0]
        country_height = self.lat_bounds[1] - self.lat_bounds[0]
        country_span = max(country_width, country_height)
        
        # Base font size: percentage=8 for medium countries (span ~10-20)
        # Smaller countries get larger fonts, larger countries get smaller fonts
        font_scale = max(0.5, min(2.0, 15 / country_span))  # Inverse relationship
        percentage_fontsize = max(5, min(14, int(8 * font_scale)))
        
        print(f"Demand panel - Country span: {country_span:.1f}°, font scale: {font_scale:.2f}, percentage font: {percentage_fontsize}")
        
        # Add delicate share labels inside the shapes (no circles)
        for _, region in demand_centers.iterrows():
            # Calculate shape-specific font scaling
            cluster_id = region['cluster_id']
            
            # Get points for this specific cluster to calculate shape size
            if 'points' in filtered_demand_data and len(filtered_demand_data['points']) > 0:
                cluster_points = filtered_demand_data['points'][filtered_demand_data['points']['cluster'] == cluster_id]
                
                if len(cluster_points) >= 3:
                    # Calculate shape span (width and height)
                    points_lng = cluster_points['lng'].values
                    points_lat = cluster_points['lat'].values
                    shape_width = points_lng.max() - points_lng.min()
                    shape_height = points_lat.max() - points_lat.min()
                    shape_span = max(shape_width, shape_height)
                    
                    # Combine country-level and shape-level scaling
                    # Shape scale: larger shapes get smaller fonts, smaller shapes get larger fonts
                    shape_scale = max(0.3, min(3.0, 2.0 / max(0.5, shape_span)))  # Inverse relationship
                    combined_fontsize = max(4, min(18, int(percentage_fontsize * shape_scale)))
                    
                    print(f"Region {region['name']}: shape_span={shape_span:.2f}°, shape_scale={shape_scale:.2f}, font={combined_fontsize}")
                else:
                    combined_fontsize = percentage_fontsize
            else:
                combined_fontsize = percentage_fontsize
            
            # Add delicate demand share label
            demand_share = region.get('demand_share', 0) * 100
            label = f"{smart_format_number(demand_share)}%"
            ax.text(region['center_lng'], region['center_lat'], label,
                   ha='center', va='center', fontsize=combined_fontsize, fontweight='normal',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9, edgecolor='steelblue', linewidth=0.5))
    
    def plot_gem_panel(self):
        """Plot GEM clusters as scaled pie charts"""
        print("Plotting generation clusters...")
        
        ax = self.axes[1]
        # Filter for contiguous US if applicable
        filtered_gem_data = self._filter_contiguous_us_data(self.gem_data)
        gem_centers = filtered_gem_data['centers']
        
        # Draw country boundaries first (deepest background)
        draw_country_boundaries(ax, self.country, self.data_bounds)
        
        # Draw cluster shapes (background) - no thresholds needed with Voronoi
        # Voronoi clustering ensures non-overlapping regions, so we can show all power plants
        if 'mapping' in filtered_gem_data and len(filtered_gem_data['mapping']) > 0:
            draw_cluster_shapes(ax, filtered_gem_data['mapping'], 'cluster_id', 
                              color='lightcoral', alpha=0.15, min_capacity_mw=0)
        
        if len(gem_centers) == 0:
            ax.text(0.5, 0.5, 'No generation data available', transform=ax.transAxes,
                   ha='center', va='center', fontsize=12)
            return
        
        # Technology colors
        tech_colors = {
            'coal': '#8B4513',      # Brown
            'gas': '#4169E1',       # Royal Blue  
            'oil': '#FF4500',       # Orange Red
            'hydro': '#00CED1',     # Dark Turquoise
            'nuclear': '#FFD700',   # Gold
            'wind': '#87CEEB',      # Sky Blue
            'solar': '#FFA500',     # Orange
            'biomass': '#228B22',   # Forest Green
            'geothermal': '#DC143C', # Crimson
            'waste': '#9ACD32',     # Yellow Green
            'battery': '#9370DB',   # Medium Purple
            'pumped_hydro': '#20B2AA', # Light Sea Green
            'other': '#808080'      # Gray
        }
        
        # Calculate pie sizes (scale by capacity) - adaptive to country size
        max_capacity = gem_centers['total_capacity_mw'].max()
        
        # Calculate country-size-aware scaling
        country_width = self.lng_bounds[1] - self.lng_bounds[0]
        country_height = self.lat_bounds[1] - self.lat_bounds[0]
        country_span = max(country_width, country_height)
        
        # Scale pie sizes relative to country size (smaller countries = smaller pies)
        base_scale = country_span / 50  # Adjust this divisor to fine-tune overall size
        min_radius = max(0.1, base_scale * 0.8)  # Minimum size
        max_radius = max(0.2, base_scale * 2.0)  # Maximum size
        
        # Calculate adaptive font sizes based on country size
        # Base font size: GW=7 for medium countries (span ~10-20)
        # Smaller countries get larger fonts, larger countries get smaller fonts
        font_scale = max(0.5, min(2.0, 15 / country_span))  # Inverse relationship
        gw_fontsize = max(5, min(12, int(7 * font_scale)))
        
        print(f"Country span: {country_span:.1f}°, pie scale: {min_radius:.2f}-{max_radius:.2f}°, font scale: {font_scale:.2f}")
        
        print(f"GEM clusters: {len(gem_centers)}, max capacity: {max_capacity:.0f} MW")
        
        for _, cluster in gem_centers.iterrows():
            # Scale pie radius by capacity
            radius = min_radius + (cluster['total_capacity_mw'] / max_capacity) * (max_radius - min_radius)
            center_x, center_y = cluster['center_lng'], cluster['center_lat']
            
            print(f"Plotting {cluster['name']} at ({center_x:.3f}, {center_y:.3f}) with radius {radius:.3f}")
            
            # Get technology breakdown from mapping data using tech_group
            cluster_id = cluster['cluster_id']
            cluster_plants = filtered_gem_data['mapping'][filtered_gem_data['mapping']['cluster_id'] == cluster_id]
            
            # Calculate tech_group breakdown
            tech_breakdown = {}
            if len(cluster_plants) > 0:
                for tech_group in cluster_plants['tech_group'].unique():
                    tech_capacity = cluster_plants[cluster_plants['tech_group'] == tech_group]['capacity_mw'].sum()
                    tech_breakdown[tech_group] = tech_capacity
                print(f"  Tech breakdown: {tech_breakdown}")
            else:
                tech_breakdown = {'other': cluster['total_capacity_mw']}
            
            # Create pie chart
            if tech_breakdown and len(tech_breakdown) > 0:
                techs = list(tech_breakdown.keys())
                capacities = list(tech_breakdown.values())
                colors = [tech_colors.get(tech.lower(), tech_colors['other']) for tech in techs]
                
                # Calculate angles
                total_capacity = sum(capacities)
                if total_capacity > 0:
                    # Draw pie wedges
                    start_angle = 0
                    for i, (tech, capacity) in enumerate(zip(techs, capacities)):
                        angle = 360 * capacity / total_capacity
                        
                        if angle > 0:  # Only draw if there's actual capacity
                            wedge = Wedge((center_x, center_y), 
                                        radius, start_angle, start_angle + angle,
                                        facecolor=colors[i], edgecolor='white', 
                                        linewidth=0.5, alpha=0.8)
                            ax.add_patch(wedge)
                            print(f"    Added {tech} wedge: {start_angle:.1f}° to {start_angle + angle:.1f}°")
                            start_angle += angle
                else:
                    # Fallback: draw a simple circle
                    circle = Circle((center_x, center_y), radius, 
                                  facecolor=tech_colors['other'], edgecolor='white', 
                                  linewidth=0.5, alpha=0.8)
                    ax.add_patch(circle)
            
            # Add delicate GW label
            label = f"{smart_format_number(cluster['total_capacity_mw']/1000)} GW"
            ax.text(center_x, center_y - radius - 0.15, label,
                   ha='center', va='top', fontsize=gw_fontsize, fontweight='normal',
                   bbox=dict(boxstyle='round,pad=0.15', facecolor='white', alpha=0.8, edgecolor='lightgray', linewidth=0.5))
        
        # Add delicate legend - only show technologies that exist in the data
        existing_techs = set()
        for _, cluster in gem_centers.iterrows():
            cluster_id = cluster['cluster_id']
            cluster_plants = filtered_gem_data['mapping'][filtered_gem_data['mapping']['cluster_id'] == cluster_id]
            if len(cluster_plants) > 0:
                existing_techs.update(cluster_plants['tech_group'].unique())
        
        legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                    markerfacecolor=tech_colors[tech], markersize=6, label=tech.title())
                          for tech in sorted(existing_techs) if tech in tech_colors]
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.12, 1), 
                 fontsize=8, frameon=True, fancybox=True, shadow=False, 
                 framealpha=0.9, edgecolor='lightgray', facecolor='white')
    
    def plot_renewable_panel(self):
        """Plot renewable zones with clean solar/wind breakdown"""
        print("Plotting renewable zones...")
        
        ax = self.axes[2]
        # Filter for contiguous US if applicable
        filtered_renewable_data = self._filter_contiguous_us_data(self.renewable_data)
        renewable_centers = filtered_renewable_data['centers']
        
        # Draw country boundaries first (deepest background)
        draw_country_boundaries(ax, self.country, self.data_bounds)
        
        # Draw cluster shapes (background) - no thresholds needed with Voronoi
        # Voronoi clustering ensures non-overlapping regions, so we can show all renewable cells
        if 'mapping' in self.renewable_data and len(self.renewable_data['mapping']) > 0:
            draw_cluster_shapes(ax, self.renewable_data['mapping'], 'cluster_id', 
                              color='lightgreen', alpha=0.15, min_generation_gwh=0)
        
        if len(renewable_centers) == 0:
            ax.text(0.5, 0.5, 'No renewable data available', transform=ax.transAxes,
                   ha='center', va='center', fontsize=12)
            return
        
        # Plot renewable zones as simple pie charts showing solar/wind mix
        self._plot_renewable_zones_simple(ax)
        
        # Add delicate legend (same styling as GEM panel)
        rez_colors = {
            'solar': '#FFD700',  # Gold
            'wind': '#4169E1'    # Royal blue
        }
        legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                    markerfacecolor=color, markersize=6, label=tech.title())
                          for tech, color in rez_colors.items()]
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.12, 1), 
                 fontsize=8, frameon=True, fancybox=True, shadow=False, 
                 framealpha=0.9, edgecolor='lightgray', facecolor='white')
    
    def _get_lcoe_color(self, lcoe_value):
        """Get color based on LCOE competitiveness (green=cheap, yellow=moderate, red=expensive)"""
        if lcoe_value == 0:
            return '#666666'  # Gray for no data
        elif lcoe_value <= 80:
            return '#00AA00'  # Bright green (very competitive)
        elif lcoe_value <= 120:
            return '#66CC00'  # Lime green (competitive)
        elif lcoe_value <= 160:
            return '#FFAA00'  # Bright orange (moderate)
        elif lcoe_value <= 200:
            return '#FF6600'  # Red-orange (expensive)
        else:
            return '#CC0000'  # Bright red (very expensive)
    
    def _plot_renewable_zones_simple(self, ax):
        """Plot renewable zones as simple pie charts showing solar/wind mix"""
        renewable_centers = self.renewable_data['centers']
        
        # Colors for solar and wind
        solar_color = '#FFD700'  # Gold
        wind_color = '#4169E1'   # Royal blue
        
        for _, zone in renewable_centers.iterrows():
            center_lat = zone['center_lat']
            center_lng = zone['center_lng']
            
            # Get solar and wind generation
            solar_gwh = zone['solar_generation_gwh']
            wind_gwh = zone['wind_generation_gwh']
            total_gwh = zone['total_generation_gwh']
            
            if total_gwh == 0:
                continue
            
            # Calculate pie chart size based on total generation - adaptive to country size
            country_width = self.lng_bounds[1] - self.lng_bounds[0]
            country_height = self.lat_bounds[1] - self.lat_bounds[0]
            country_span = max(country_width, country_height)
            
            # Scale pie sizes relative to country size
            base_scale = country_span / 50  # Same scaling as GEM panel
            min_rez_radius = max(0.1, base_scale * 0.6)  # Slightly smaller than GEM
            max_rez_radius = max(0.2, base_scale * 1.5)  # Slightly smaller than GEM
            
            # Scale by generation with country-aware bounds
            radius = max(min_rez_radius, min(max_rez_radius, total_gwh / 3000 * base_scale))
            
            # Calculate adaptive font sizes based on country size
            # Base font sizes: TWh=7, LCOE=6, spread=5 for medium countries (span ~10-20)
            # Smaller countries get larger fonts, larger countries get smaller fonts
            font_scale = max(0.5, min(2.0, 15 / country_span))  # Inverse relationship
            twh_fontsize = max(5, min(12, int(7 * font_scale)))
            lcoe_fontsize = max(4, min(10, int(6 * font_scale)))
            spread_fontsize = max(3, min(8, int(5 * font_scale)))
            
            # Calculate overall weighted average LCOE across both technologies
            overall_lcoe = 0
            if solar_gwh > 0 and wind_gwh > 0:
                # Weighted average of both technologies
                solar_lcoe = zone.get('solar_weighted_lcoe_usd_mwh', 0)
                wind_lcoe = zone.get('wind_weighted_lcoe_usd_mwh', 0)
                overall_lcoe = (solar_lcoe * solar_gwh + wind_lcoe * wind_gwh) / total_gwh
                print(f"Zone {zone['name']}: Solar LCOE ${solar_lcoe:.0f}, Wind LCOE ${wind_lcoe:.0f}, Overall LCOE ${overall_lcoe:.0f}")
            elif solar_gwh > 0:
                overall_lcoe = zone.get('solar_weighted_lcoe_usd_mwh', 0)
                print(f"Zone {zone['name']}: Solar-only LCOE ${overall_lcoe:.0f}")
            elif wind_gwh > 0:
                overall_lcoe = zone.get('wind_weighted_lcoe_usd_mwh', 0)
                print(f"Zone {zone['name']}: Wind-only LCOE ${overall_lcoe:.0f}")
            
            lcoe_edge_color = self._get_lcoe_color(overall_lcoe)
            print(f"Zone {zone['name']}: LCOE ${overall_lcoe:.0f} -> Color {lcoe_edge_color}")
            
            # Create pie chart with thin white internal borders and prominent LCOE-colored outer edge
            if solar_gwh > 0 and wind_gwh > 0:
                # Both solar and wind - create pie chart
                solar_fraction = solar_gwh / total_gwh
                wind_fraction = wind_gwh / total_gwh
                
                # Solar wedge (starting from 0 degrees) - no edge color
                solar_wedge = Wedge((center_lng, center_lat), radius, 0, 360 * solar_fraction,
                                  facecolor=solar_color, alpha=0.8, edgecolor='none')
                ax.add_patch(solar_wedge)
                
                # Wind wedge (continuing from solar) - no edge color
                wind_wedge = Wedge((center_lng, center_lat), radius, 360 * solar_fraction, 360,
                                 facecolor=wind_color, alpha=0.8, edgecolor='none')
                ax.add_patch(wind_wedge)
                
                # Add thin white separator line between solar and wind
                import numpy as np
                angle_rad = np.radians(360 * solar_fraction)
                line_x = [center_lng, center_lng + radius * np.cos(angle_rad)]
                line_y = [center_lat, center_lat + radius * np.sin(angle_rad)]
                ax.plot(line_x, line_y, color='white', linewidth=1.5, alpha=0.9)
                
                # Add prominent LCOE-colored outer ring
                # outer_circle = Circle((center_lng, center_lat), radius,
                #                     facecolor='none', edgecolor=lcoe_edge_color, linewidth=4, alpha=1.0)
                # ax.add_patch(outer_circle)
                
            elif solar_gwh > 0:
                # Solar only - full circle with prominent LCOE edge
                solar_circle = Circle((center_lng, center_lat), radius,
                                    facecolor=solar_color, alpha=0.8, edgecolor=lcoe_edge_color, linewidth=4)
                ax.add_patch(solar_circle)
                
            elif wind_gwh > 0:
                # Wind only - full circle with prominent LCOE edge
                wind_circle = Circle((center_lng, center_lat), radius,
                                   facecolor=wind_color, alpha=0.8, edgecolor=lcoe_edge_color, linewidth=4)
                ax.add_patch(wind_circle)
            
            # Systematic label positioning: TWh on left, LCOE on right, fallback to above/below
            total_twh = total_gwh / 1000
            twh_text = f'{total_twh:.0f} TWh'
            
            # Prepare LCOE information
            lcoe_parts = []
            if solar_gwh > 0 and 'solar_weighted_lcoe_usd_mwh' in zone.index:
                solar_lcoe = zone['solar_weighted_lcoe_usd_mwh']
                if solar_lcoe > 0:
                    lcoe_parts.append(f's ${solar_lcoe:.0f}')
            
            if wind_gwh > 0 and 'wind_weighted_lcoe_usd_mwh' in zone.index:
                wind_lcoe = zone['wind_weighted_lcoe_usd_mwh']
                if wind_lcoe > 0:
                    lcoe_parts.append(f'w ${wind_lcoe:.0f}')
            
            lcoe_text = ' | '.join(lcoe_parts) + '/MWh' if lcoe_parts else ''
            
            # Check space availability for side positioning
            twh_left_available, twh_left_lng, twh_left_lat = self._check_label_space_available(
                center_lng, center_lat, radius, twh_text, twh_fontsize, ax, side='left')
            
            lcoe_right_available, lcoe_right_lng, lcoe_right_lat = self._check_label_space_available(
                center_lng, center_lat, radius, lcoe_text, lcoe_fontsize, ax, side='right') if lcoe_text else (False, 0, 0)
            
            # Position TWh label
            if twh_left_available:
                # TWh label on the left side
                ax.text(twh_left_lng, twh_left_lat, twh_text,
                       ha='right', va='center', fontsize=twh_fontsize, fontweight='normal',
                       bbox=dict(boxstyle='round,pad=0.15', facecolor='white', alpha=0.8, edgecolor='lightgray', linewidth=0.5))
                print(f"  TWh label positioned LEFT at ({twh_left_lng:.2f}, {twh_left_lat:.2f})")
            else:
                # Fallback: TWh label above the pie chart
                ax.text(center_lng, center_lat + radius + 0.15, twh_text,
                       ha='center', va='bottom', fontsize=twh_fontsize, fontweight='normal',
                       bbox=dict(boxstyle='round,pad=0.15', facecolor='white', alpha=0.8, edgecolor='lightgray', linewidth=0.5))
                print(f"  TWh label positioned ABOVE (fallback)")
            
            # Position LCOE label
            if lcoe_text:
                if lcoe_right_available:
                    # LCOE label on the right side
                    ax.text(lcoe_right_lng, lcoe_right_lat, lcoe_text,
                           ha='left', va='center', fontsize=lcoe_fontsize, fontweight='normal', style='italic',
                           color='#666666', alpha=0.9)
                    print(f"  LCOE label positioned RIGHT at ({lcoe_right_lng:.2f}, {lcoe_right_lat:.2f})")
                else:
                    # Fallback: LCOE label below the pie chart
                    ax.text(center_lng, center_lat - radius - 0.35, lcoe_text,
                           ha='center', va='top', fontsize=lcoe_fontsize, fontweight='normal', style='italic',
                           color='#666666', alpha=0.9)
                    print(f"  LCOE label positioned BELOW (fallback)")
                
                # Add cost spread indicators (always below, smaller)
                spread_parts = []
                if solar_gwh > 0 and 'solar_lcoe_min_usd_mwh' in zone.index and 'solar_lcoe_max_usd_mwh' in zone.index:
                    solar_min = zone['solar_lcoe_min_usd_mwh']
                    solar_max = zone['solar_lcoe_max_usd_mwh']
                    if solar_min > 0 and solar_max > solar_min:
                        spread_parts.append(f's±{solar_max - solar_min:.0f}')
                
                if wind_gwh > 0 and 'wind_lcoe_min_usd_mwh' in zone.index and 'wind_lcoe_max_usd_mwh' in zone.index:
                    wind_min = zone['wind_lcoe_min_usd_mwh']
                    wind_max = zone['wind_lcoe_max_usd_mwh']
                    if wind_min > 0 and wind_max > wind_min:
                        spread_parts.append(f'w±{wind_max - wind_min:.0f}')
                
                if spread_parts:
                    spread_text = ' | '.join(spread_parts)
                    ax.text(center_lng, center_lat - radius - 0.50, spread_text,
                           ha='center', va='top', fontsize=spread_fontsize, fontweight='normal', style='italic',
                           color='#999999', alpha=0.8)


    def save_atlas(self):
        """Save the economic atlas as both combined and separate panels"""
        # Save the existing combined figure (unchanged)
        output_file = f'{self.output_dir}/{self.country}_economic_atlas.png'
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Economic atlas saved: {output_file}")
        
        # Also save each panel separately from the existing axes
        panel_names = ['demand_regions', 'generation_clusters', 'renewable_zones']
        for i, (ax, name) in enumerate(zip(self.axes, panel_names)):
            # Extract just this subplot and save it
            extent = ax.get_window_extent().transformed(self.fig.dpi_scale_trans.inverted())
            separate_file = f'{self.output_dir}/{self.country}_{name}.png'
            self.fig.savefig(separate_file, bbox_inches=extent.expanded(1.1, 1.2), dpi=300)
            print(f"Panel saved: {separate_file}")
        
        return output_file
    
    def generate_atlas(self):
        """Generate complete economic atlas"""
        print(f"\nGENERATING ECONOMIC ATLAS FOR {self.country}")
        print("=" * 60)
        
        # Load all data
        self.load_analysis_data()
        self.load_ngfs_twh_target()
        # Skip LCOE filtering - just use all renewable zones
        
        # Create visualization
        self.create_atlas_figure()
        self.plot_demand_panel()
        self.plot_gem_panel() 
        self.plot_renewable_panel()
        
        # Save result
        output_file = self.save_atlas()
        
        print(f"\nECONOMIC ATLAS COMPLETE!")
        print(f"Visual summary: {output_file}")
        
        return output_file

def main():
    parser = argparse.ArgumentParser(description='Generate VerveStacks Economic Atlas')
    parser.add_argument('--country', required=True, help='ISO3 country code')
    parser.add_argument('--output-dir', required=True, help='Output directory with analysis results')
    
    args = parser.parse_args()
    
    # Generate atlas
    generator = EconomicAtlasGenerator(args.country, args.output_dir)
    output_file = generator.generate_atlas()
    
    # Auto-open the result
    try:
        abs_output_file = os.path.abspath(output_file)
        if os.name == 'nt':  # Windows
            os.startfile(abs_output_file)
        else:  # macOS/Linux
            import subprocess
            subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', abs_output_file])
        print(f"Opened atlas: {abs_output_file}")
    except Exception as e:
        print(f"Could not auto-open atlas: {e}")

if __name__ == "__main__":
    main()
