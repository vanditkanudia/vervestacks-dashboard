"""
Cluster Shapes Validator - 4-Panel Visualization
Creates a comprehensive 4-subplot visualization showing:
1. Solar hulls only
2. Wind hulls only (onshore + offshore)  
3. Generation hulls only
4. Resulting network view with demand background
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Polygon
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from shapely.geometry import Point, Polygon as ShapelyPolygon
from scipy.spatial import ConvexHull
import warnings
warnings.filterwarnings('ignore')

# Try to import boundary function
try:
    from syn_grids_1.create_summary_map_visual import get_country_boundaries
    BOUNDARY_FUNCTION_AVAILABLE = True
except ImportError:
    BOUNDARY_FUNCTION_AVAILABLE = False
    print("⚠️ Boundary function not available")

# Alternative boundary loading function
def load_country_boundaries_from_shapefile(country_code, bounds=None):
    """Load country boundaries from Natural Earth shapefile"""
    try:
        import geopandas as gpd
        import numpy as np
        
        # Load the shapefile
        countries_file = 'data/country_data/naturalearth/ne_10m_admin_0_countries_lakes.shp'
        countries_gdf = gpd.read_file(countries_file)
        
        # Filter for the specific country
        if 'ISO_A3' in countries_gdf.columns:
            country_data = countries_gdf[countries_gdf['ISO_A3'] == country_code]
        elif 'ADM0_A3' in countries_gdf.columns:
            country_data = countries_gdf[countries_gdf['ADM0_A3'] == country_code]
        elif 'NAME' in countries_gdf.columns:
            # Try to match by name as fallback
            country_data = countries_gdf[countries_gdf['NAME'].str.contains(country_code, case=False, na=False)]
        else:
            print(f"⚠️ No suitable country identifier column found in shapefile")
            return None
        
        if country_data.empty:
            print(f"⚠️ No country data found for {country_code}")
            return None
        
        # Extract boundary coordinates
        boundaries = []
        for _, row in country_data.iterrows():
            if hasattr(row.geometry, 'exterior'):
                coords = np.array(row.geometry.exterior.coords)
                boundaries.append(coords)
            elif hasattr(row.geometry, 'geoms'):
                # MultiPolygon
                for geom in row.geometry.geoms:
                    if hasattr(geom, 'exterior'):
                        coords = np.array(geom.exterior.coords)
                        boundaries.append(coords)
        
        # Filter by bounds if provided
        if bounds and boundaries:
            filtered_boundaries = []
            for boundary in boundaries:
                if (boundary[:, 0].min() <= bounds['max_lng'] and 
                    boundary[:, 0].max() >= bounds['min_lng'] and
                    boundary[:, 1].min() <= bounds['max_lat'] and 
                    boundary[:, 1].max() >= bounds['min_lat']):
                    filtered_boundaries.append(boundary)
            boundaries = filtered_boundaries
        
        return boundaries if boundaries else None
        
    except Exception as e:
        print(f"⚠️ Error loading country boundaries from shapefile: {e}")
        return None

class ClusterShapesValidator4Panel:
    """
    Creates a 4-panel visualization of cluster shapes for synthetic grid validation
    """
    
    def __init__(self, country_code: str, output_dir: str, 
                 demand_results=None, generation_results=None, renewable_results=None):
        """
        Initialize the 4-panel cluster shapes validator
        
        Args:
            country_code: ISO3 country code (e.g., 'USA', 'IND', 'DEU')
            output_dir: Base directory for output files
            demand_results: Demand clustering results dict
            generation_results: Generation clustering results dict  
            renewable_results: Renewable clustering results dict
        """
        self.country = country_code.upper()
        # Ensure output_dir is a Path object and create country-specific subdirectory
        self.output_dir = Path(output_dir) / self.country
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store passed results
        self.demand_results = demand_results
        self.generation_results = generation_results
        self.renewable_results = renewable_results
        
        # Data containers
        self.demand_centers = None
        self.demand_points = None
        self.generation_centers = None
        self.generation_mapping = None
        self.renewable_centers = None
        self.renewable_mapping = None
        self.data_bounds = None
        
        print(f"🎨 Initialized 4-Panel Cluster Shapes Validator for {self.country}")
        print(f"📁 Output directory: {self.output_dir}")

    def load_cluster_data(self):
        """Load all cluster data from passed results"""
        # First try to use passed data
        if hasattr(self, 'demand_results') and self.demand_results is not None:
            if self.demand_results['centers'] is not None:
                self.demand_centers = pd.DataFrame(self.demand_results['centers'])
                print(f"📍 Using passed demand centers: {len(self.demand_centers)}")
            if self.demand_results['points'] is not None:
                self.demand_points = pd.DataFrame(self.demand_results['points'])
                print(f"📍 Using passed demand points: {len(self.demand_points)}")
        
        # Handle generation data
        if hasattr(self, 'generation_results') and self.generation_results is not None:
            if self.generation_results['centers'] is not None:
                self.generation_centers = pd.DataFrame(self.generation_results['centers'])
                print(f"🏭 Using passed generation centers: {len(self.generation_centers)}")
            if self.generation_results['mapping'] is not None:
                self.generation_mapping = pd.DataFrame(self.generation_results['mapping'])
                print(f"⚡ Using passed generation mapping: {len(self.generation_mapping)}")
        
        # Handle renewable data
        if hasattr(self, 'renewable_results') and self.renewable_results is not None:
            if self.renewable_results['centers'] is not None:
                self.renewable_centers = pd.DataFrame(self.renewable_results['centers'])
                print(f"🌞 Using passed renewable centers: {len(self.renewable_centers)}")
            if self.renewable_results['mapping'] is not None:
                self.renewable_mapping = pd.DataFrame(self.renewable_results['mapping'])
                print(f"🌞 Using passed renewable mapping: {len(self.renewable_mapping)}")
        
        # Calculate data bounds for country boundary filtering
        self._calculate_data_bounds()

    def _calculate_data_bounds(self):
        """Calculate bounds of all data points for country boundary filtering"""
        all_lngs = []
        all_lats = []
        
        if self.demand_centers is not None:
            all_lngs.extend(self.demand_centers['center_lng'])
            all_lats.extend(self.demand_centers['center_lat'])
        if self.generation_centers is not None:
            all_lngs.extend(self.generation_centers['center_lng'])
            all_lats.extend(self.generation_centers['center_lat'])
        if self.renewable_centers is not None:
            all_lngs.extend(self.renewable_centers['center_lng'])
            all_lats.extend(self.renewable_centers['center_lat'])
        
        if all_lngs and all_lats:
            self.data_bounds = {
                'min_lng': min(all_lngs), 'max_lng': max(all_lngs),
                'min_lat': min(all_lats), 'max_lat': max(all_lats)
            }
            print(f"📐 Data bounds: {self.data_bounds}")

    def create_cluster_shapes_from_points(self, centers_df, points_df):
        """
        Create convex hull shapes for each cluster from its data points
        
        Args:
            centers_df: DataFrame with cluster centers
            points_df: DataFrame with all data points and their cluster assignments
            
        Returns:
            Dict mapping cluster_id to shape object (Polygon or Circle)
        """
        if centers_df is None or points_df is None or centers_df.empty or points_df.empty:
            return {}
        
        shapes = {}
        
        # Determine the cluster column name
        if 'cluster' in points_df.columns:
            cluster_col = 'cluster'
        elif 'cluster_id' in points_df.columns:
            cluster_col = 'cluster_id'
        else:
            print("⚠️ No cluster column found in points data")
            return {}
        
        # Determine coordinate columns
        if 'lng' in points_df.columns and 'lat' in points_df.columns:
            lng_col, lat_col = 'lng', 'lat'
        elif 'lon' in points_df.columns and 'lat' in points_df.columns:
            lng_col, lat_col = 'lon', 'lat'
        elif 'center_lng' in points_df.columns and 'center_lat' in points_df.columns:
            lng_col, lat_col = 'center_lng', 'center_lat'
        else:
            print("⚠️ No coordinate columns found in points data")
            return {}
        
        for _, center in centers_df.iterrows():
            cluster_id = center.get('cluster_id', center.name)
            
            # Get all points for this cluster
            cluster_points = points_df[points_df[cluster_col] == cluster_id]
            
            if len(cluster_points) < 3:
                # Too few points for convex hull, create a small circle (same as NTC calculation)
                center_lng = center.get('center_lng', center.get('lng', 0))
                center_lat = center.get('center_lat', center.get('lat', 0))
                
                # Use same small radius as NTC calculation (0.1 degree)
                radius = 0.1
                
                shapes[cluster_id] = Circle((center_lng, center_lat), radius)
            else:
                # Create convex hull
                try:
                    points = cluster_points[[lng_col, lat_col]].values
                    
                    # Check for valid coordinates
                    valid_points = points[~np.isnan(points).any(axis=1)]
                    if len(valid_points) < 3:
                        print(f"⚠️ Cluster {cluster_id}: Not enough valid points for hull")
                        center_lng = center.get('center_lng', center.get('lng', 0))
                        center_lat = center.get('center_lat', center.get('lat', 0))
                        shapes[cluster_id] = Circle((center_lng, center_lat), 0.1)
                        continue
                    
                    hull = ConvexHull(valid_points)
                    hull_points = valid_points[hull.vertices]
                    
                    # Create shapely polygon
                    polygon = ShapelyPolygon(hull_points)
                    shapes[cluster_id] = polygon
                    
                except Exception as e:
                    print(f"⚠️ Could not create convex hull for cluster {cluster_id}: {e}")
                    # Fallback to circle
                    center_lng = center.get('center_lng', center.get('lng', 0))
                    center_lat = center.get('center_lat', center.get('lat', 0))
                    shapes[cluster_id] = Circle((center_lng, center_lat), 0.1)
        
        return shapes

    def visualize_cluster_shapes(self, save_file=None):
        """
        Create comprehensive cluster shapes visualization in 4 subplots:
        1. Solar hulls only
        2. Wind hulls only (onshore + offshore)
        3. Generation hulls only
        4. Resulting network view with demand background
        """
        if save_file is None:
            save_file = self.output_dir / f"{self.country}_cluster_shapes_4panel.png"
        
        print(f"🎨 Creating 4-subplot cluster shapes validation visualization...")
        
        # Load cluster data
        self.load_cluster_data()
        
        # Create 4 subplots
        fig, axes = plt.subplots(2, 2, figsize=(20, 16))
        # Reorder panels: Network (1st), Generation (2nd), Solar (3rd), Wind (4th)
        # Original: ax1=Solar, ax2=Wind, ax3=Generation, ax4=Network
        # Desired:  ax1=Network, ax2=Generation, ax3=Solar, ax4=Wind
        # Swap: ax1↔ax4 (Solar↔Network), ax2↔ax3 (Wind↔Generation)
        ax1, ax2, ax3, ax4 = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]
        ax1, ax2, ax3, ax4 = ax4, ax3, ax1, ax2
        
        # Set main title
        fig.suptitle(f'{self.country} Synthetic Grid Cluster Validation', 
                     fontsize=18, fontweight='bold', y=0.95)
        
        # Colors for different cluster types
        demand_color = '#FF4444'      # Red
        generation_color = '#4444FF'  # Blue  
        renewable_color = '#44AA44'   # Green
        
        # Get country boundaries once for all subplots
        boundaries = None
        if self.data_bounds:
            try:
                # Try the original function first
                if BOUNDARY_FUNCTION_AVAILABLE:
                    boundaries = get_country_boundaries(self.country, self.data_bounds)
                
                # If that fails or is not available, try the shapefile method
                if boundaries is None:
                    boundaries = load_country_boundaries_from_shapefile(self.country, self.data_bounds)
                    
                if boundaries:
                    print(f"✅ Loaded {len(boundaries)} country boundary segments for {self.country}")
                else:
                    print(f"⚠️ No country boundaries found for {self.country}")
                    
            except Exception as e:
                print(f"⚠️ Could not load country boundaries: {e}")
        
        # Calculate common axis limits for all subplots
        all_lngs = []
        all_lats = []
        
        if self.demand_centers is not None:
            all_lngs.extend(self.demand_centers['center_lng'])
            all_lats.extend(self.demand_centers['center_lat'])
        if self.generation_centers is not None:
            all_lngs.extend(self.generation_centers['center_lng'])
            all_lats.extend(self.generation_centers['center_lat'])
        if self.renewable_centers is not None:
            all_lngs.extend(self.renewable_centers['center_lng'])
            all_lats.extend(self.renewable_centers['center_lat'])
        
        if all_lngs and all_lats:
            lng_margin = (max(all_lngs) - min(all_lngs)) * 0.1
            lat_margin = (max(all_lats) - min(all_lats)) * 0.1
            xlim = [min(all_lngs) - lng_margin, max(all_lngs) + lng_margin]
            ylim = [min(all_lats) - lat_margin, max(all_lats) + lat_margin]
        else:
            xlim = ylim = None
        
        # Helper function to plot country boundaries
        def plot_boundaries(ax):
            if boundaries:
                for boundary in boundaries:
                    ax.plot(boundary[:, 0], boundary[:, 1], 'k-', 
                           linewidth=1.5, alpha=0.7)
        
        # Helper function to set common axis properties
        def setup_subplot(ax, title, xlim, ylim):
            ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
            if xlim and ylim:
                ax.set_xlim(xlim)
                ax.set_ylim(ylim)
            ax.set_xlabel('Longitude', fontsize=10)
            ax.set_ylabel('Latitude', fontsize=10)
            ax.grid(True, alpha=0.3)
            plot_boundaries(ax)
        
        # SUBPLOT 1: Network (moved from 4th)
        setup_subplot(ax1, "Resulting Synthetic Network with NTC", xlim, ylim)
        
        if (self.renewable_centers is not None and 
            hasattr(self, 'renewable_results') and 
            self.renewable_results and 
            'technologies' in self.renewable_results and 
            'solar' in self.renewable_results['technologies']):
            
            solar_data = self.renewable_results['technologies']['solar']
            if 'cell_mapping' in solar_data and solar_data['cell_mapping'] is not None:
                solar_points = solar_data['cell_mapping']
                
                # Create and plot solar hulls with CF-based coloring
                solar_shapes = self.create_cluster_shapes_from_points(
                    pd.DataFrame(solar_data['stats']), solar_points
                )
                if solar_shapes and 'stats' in solar_data and solar_data['stats'] is not None:
                    solar_centers = solar_data['stats']
                    
                    # Create CF-based color mapping for polygons
                    cf_values = solar_centers['avg_re_cf'].values
                    if len(cf_values) > 0:
                        cf_normalized = (cf_values - cf_values.min()) / (cf_values.max() - cf_values.min()) if cf_values.max() != cf_values.min() else np.ones_like(cf_values)
                        # Use viridis colormap: high CF = yellow/green, low CF = purple/blue
                        cf_colors = plt.cm.viridis(cf_normalized)
                        
                        # Create CF color mapping by cluster_id
                        cf_color_map = {}
                        for _, center in solar_centers.iterrows():
                            cluster_id = center['cluster_id']
                            cf_color_map[cluster_id] = cf_colors[solar_centers.index.get_loc(center.name)]
                    else:
                        cf_color_map = {cluster_id: renewable_color for cluster_id in solar_shapes.keys()}
                    
                    for cluster_id, shape in solar_shapes.items():
                        polygon_color = cf_color_map.get(cluster_id, renewable_color)
                        if isinstance(shape, ShapelyPolygon):
                            # Convert shapely polygon to matplotlib patch
                            coords = np.array(shape.exterior.coords)
                            ax3.fill(coords[:, 0], coords[:, 1], 
                                   color=polygon_color, alpha=0.15, 
                                   edgecolor=polygon_color, linewidth=1.5)
                        elif isinstance(shape, Circle):
                            # Plot circle
                            ax3.add_patch(patches.Circle(shape.center, shape.radius,
                                                       color=polygon_color, alpha=0.3,
                                                       edgecolor=polygon_color, linewidth=2))
                
                # Plot solar centers (keep original green color)
                if 'stats' in solar_data and solar_data['stats'] is not None:
                    solar_centers = solar_data['stats']
                    ax3.scatter(solar_centers['centroid_lon'], solar_centers['centroid_lat'],
                              c=renewable_color, s=120, marker='^', alpha=0.9, 
                              edgecolors='white', linewidth=2, label=f'Solar ({len(solar_centers)})')
                    
                    # Add CF-based labels
                    for _, center in solar_centers.iterrows():
                        cf_value = center['avg_re_cf']
                        cf_label = f"{cf_value:.3f}"  # 3 decimal places
                        ax3.annotate(cf_label, 
                                   (center['centroid_lon'], center['centroid_lat']),
                                   xytext=(5, 5), textcoords='offset points', fontsize=8,
                                   fontweight='bold', color='white',
                                   bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))
        
        ax3.legend(loc='upper right', fontsize=9)
        
        # SUBPLOT 2: Generation Hulls Only
        setup_subplot(ax2, "Generation Clusters", xlim, ylim)
        
        wind_technologies = ['wind_onshore', 'wind_offshore']
        wind_colors = {'wind_onshore': '#32CD32', 'wind_offshore': '#006400'}  # Bright green vs dark green
        
        for tech in wind_technologies:
            if (self.renewable_results and 
                'technologies' in self.renewable_results and 
                tech in self.renewable_results['technologies']):
                
                wind_data = self.renewable_results['technologies'][tech]
                if 'cell_mapping' in wind_data and wind_data['cell_mapping'] is not None:
                    wind_points = wind_data['cell_mapping']
                    
                    # Create and plot wind hulls with CF-based coloring
                    wind_shapes = self.create_cluster_shapes_from_points(
                        pd.DataFrame(wind_data['stats']), wind_points
                    )
                    if wind_shapes and 'stats' in wind_data and wind_data['stats'] is not None:
                        wind_centers = wind_data['stats']
                        
                        # Create CF-based color mapping for polygons (separate normalization per technology)
                        cf_values = wind_centers['avg_re_cf'].values
                        if len(cf_values) > 0:
                            cf_normalized = (cf_values - cf_values.min()) / (cf_values.max() - cf_values.min()) if cf_values.max() != cf_values.min() else np.ones_like(cf_values)
                            # Use viridis colormap: high CF = yellow/green, low CF = purple/blue
                            cf_colors = plt.cm.viridis(cf_normalized)
                            
                            # Create CF color mapping by cluster_id
                            cf_color_map = {}
                            for _, center in wind_centers.iterrows():
                                cluster_id = center['cluster_id']
                                cf_color_map[cluster_id] = cf_colors[wind_centers.index.get_loc(center.name)]
                        else:
                            cf_color_map = {cluster_id: wind_colors[tech] for cluster_id in wind_shapes.keys()}
                        
                        for cluster_id, shape in wind_shapes.items():
                            polygon_color = cf_color_map.get(cluster_id, wind_colors[tech])
                            # Slightly higher alpha for onshore wind visibility
                            alpha_value = 0.12 if tech == 'wind_onshore' else 0.08
                            
                            if isinstance(shape, ShapelyPolygon):
                                # Convert shapely polygon to matplotlib patch
                                coords = np.array(shape.exterior.coords)
                                ax4.fill(coords[:, 0], coords[:, 1], 
                                       color=polygon_color, alpha=alpha_value, 
                                       edgecolor=polygon_color, linewidth=1.0)
                            elif isinstance(shape, Circle):
                                # Plot circle
                                ax4.add_patch(patches.Circle(shape.center, shape.radius,
                                                           color=polygon_color, alpha=0.15,
                                                           edgecolor=polygon_color, linewidth=1.5))
                    
                    # Plot wind centers (keep original colors to distinguish onshore/offshore)
                    if 'stats' in wind_data and wind_data['stats'] is not None:
                        wind_centers = wind_data['stats']
                        ax4.scatter(wind_centers['centroid_lon'], wind_centers['centroid_lat'],
                                  c=wind_colors[tech], s=120, marker='v', alpha=0.9, 
                                  edgecolors='white', linewidth=2,
                                  label=f'{tech.replace("_", " ").title()} ({len(wind_centers)})')
                        
                        # Add CF-based labels
                        for _, center in wind_centers.iterrows():
                            cf_value = center['avg_re_cf']
                            cf_label = f"{cf_value:.3f}"  # 3 decimal places
                            ax4.annotate(cf_label, 
                                       (center['centroid_lon'], center['centroid_lat']),
                                       xytext=(5, 5), textcoords='offset points', fontsize=8,
                                       fontweight='bold', color='white',
                                       bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))
        
        ax4.legend(loc='upper right', fontsize=9)
        
        # SUBPLOT 3: Generation Clusters Only
        setup_subplot(ax3, "Solar Clusters", xlim, ylim)
        
        # Plot generation clusters
        if self.generation_centers is not None and self.generation_mapping is not None:
            generation_shapes = self.create_cluster_shapes_from_points(
                self.generation_centers, self.generation_mapping
            )
            
            if generation_shapes:
                for cluster_id, shape in generation_shapes.items():
                    if isinstance(shape, ShapelyPolygon):
                        # Convert shapely polygon to matplotlib patch
                        coords = np.array(shape.exterior.coords)
                        ax2.fill(coords[:, 0], coords[:, 1], 
                               color=generation_color, alpha=0.3, 
                               edgecolor=generation_color, linewidth=2)
                    elif isinstance(shape, Circle):
                        ax2.add_patch(patches.Circle(shape.center, shape.radius,
                                                  color=generation_color, alpha=0.3,
                                                  edgecolor=generation_color, linewidth=2))
            
            # Plot generation centers
            ax2.scatter(self.generation_centers['center_lng'], self.generation_centers['center_lat'],
                      c=generation_color, s=100, marker='s', alpha=0.8, 
                      label=f'Generation Clusters ({len(self.generation_centers)})', 
                      edgecolors='white', linewidth=1)
            
            # Add cluster labels
            for _, center in self.generation_centers.iterrows():
                ax2.annotate(f"G{center.get('cluster_id', center.name)}", 
                           (center['center_lng'], center['center_lat']),
                           xytext=(5, 5), textcoords='offset points', fontsize=8,
                           fontweight='bold', color='white',
                           bbox=dict(boxstyle='round,pad=0.2', facecolor=generation_color, alpha=0.8))
        
        ax2.legend(loc='upper right', fontsize=9)
        
        # SUBPLOT 4: Resulting Network View with NTC connections and demand background
        setup_subplot(ax4, "Wind Clusters (Onshore + Offshore)", xlim, ylim)
        
        # Plot demand cluster shapes as background (light fills for visual clarity)
        if self.demand_centers is not None and self.demand_points is not None:
            demand_shapes = self.create_cluster_shapes_from_points(
                self.demand_centers, self.demand_points
            )
            
            if demand_shapes:
                for cluster_id, shape in demand_shapes.items():
                    if isinstance(shape, ShapelyPolygon):
                        # Convert shapely polygon to matplotlib patch
                        coords = np.array(shape.exterior.coords)
                        ax1.fill(coords[:, 0], coords[:, 1], 
                               color=demand_color, alpha=0.15,  # Light fill for background
                               edgecolor=demand_color, linewidth=1)
                    elif isinstance(shape, Circle):
                        ax1.add_patch(patches.Circle(shape.center, shape.radius,
                                                  color=demand_color, alpha=0.15,  # Light fill
                                                  edgecolor=demand_color, linewidth=1))
        
        # Get cluster centers for positioning (same logic as existing network visualization)
        all_clusters = []
        if self.demand_centers is not None:
            for _, center in self.demand_centers.iterrows():
                all_clusters.append({
                    'cluster_type': 'demand',
                    'cluster_id': center.get('cluster_id', center.name),
                    'lng': center['center_lng'],
                    'lat': center['center_lat']
                })
        
        if self.generation_centers is not None:
            for _, center in self.generation_centers.iterrows():
                all_clusters.append({
                    'cluster_type': 'generation',
                    'cluster_id': center.get('cluster_id', center.name),
                    'lng': center['center_lng'],
                    'lat': center['center_lat']
                })
        
        if self.renewable_centers is not None:
            for _, center in self.renewable_centers.iterrows():
                all_clusters.append({
                    'cluster_type': 'renewable',
                    'cluster_id': center.get('cluster_id', center.name),
                    'lng': center['center_lng'],
                    'lat': center['center_lat']
                })
        
        cluster_positions = {}
        for cluster in all_clusters:
            cluster_key = f"{cluster['cluster_type']}{int(cluster['cluster_id'])}"
            cluster_positions[cluster_key] = (cluster['lng'], cluster['lat'])
        
        # Plot cluster centers with capacity/population-based scaling
        colors = {'demand': demand_color, 'generation': generation_color, 'renewable': renewable_color}
        
        # Scaling ranges (Option B - More Dramatic)
        scaling_ranges = {
            'demand': {'min_size': 60, 'max_size': 250, 'data_col': 'population_demand'},
            'generation': {'min_size': 80, 'max_size': 400, 'data_col': 'total_capacity_mw'},
            'renewable': {'min_size': 20, 'max_size': 100, 'data_col': 'total_capacity_mw'}
        }
        
        def scale_marker_size(values, min_size, max_size):
            """Scale marker sizes using logarithmic scaling"""
            if len(values) == 0:
                return []
            # Add 1 to handle zero values and use log scaling
            log_values = np.log(np.array(values) + 1)
            log_min, log_max = log_values.min(), log_values.max()
            if log_max == log_min:  # All values are the same
                return [min_size + (max_size - min_size) // 2] * len(values)
            normalized = (log_values - log_min) / (log_max - log_min)
            return min_size + normalized * (max_size - min_size)
        
        for cluster_type, color in colors.items():
            type_clusters = [c for c in all_clusters if c['cluster_type'] == cluster_type]
            if type_clusters:
                lngs = [c['lng'] for c in type_clusters]
                lats = [c['lat'] for c in type_clusters]
                
                # Get scaling data for this cluster type
                range_config = scaling_ranges[cluster_type]
                data_col = range_config['data_col']
                min_size = range_config['min_size']
                max_size = range_config['max_size']
                
                # Extract scaling values from cluster data
                if cluster_type == 'demand' and self.demand_centers is not None:
                    # Match clusters to demand centers data
                    scaling_values = []
                    for cluster in type_clusters:
                        cluster_id = cluster['cluster_id']
                        matching_center = self.demand_centers[self.demand_centers['cluster_id'] == cluster_id]
                        if not matching_center.empty and data_col in matching_center.columns:
                            scaling_values.append(matching_center.iloc[0][data_col])
                        else:
                            scaling_values.append(1000)  # Default fallback
                elif cluster_type == 'generation' and self.generation_centers is not None:
                    # Match clusters to generation centers data
                    scaling_values = []
                    for cluster in type_clusters:
                        cluster_id = cluster['cluster_id']
                        matching_center = self.generation_centers[self.generation_centers['cluster_id'] == cluster_id]
                        if not matching_center.empty and data_col in matching_center.columns:
                            scaling_values.append(matching_center.iloc[0][data_col])
                        else:
                            scaling_values.append(1000)  # Default fallback
                elif cluster_type == 'renewable' and self.renewable_centers is not None:
                    # Match clusters to renewable centers data
                    scaling_values = []
                    for cluster in type_clusters:
                        cluster_id = cluster['cluster_id']
                        matching_center = self.renewable_centers[self.renewable_centers['cluster_id'] == cluster_id]
                        if not matching_center.empty and data_col in matching_center.columns:
                            scaling_values.append(matching_center.iloc[0][data_col])
                        else:
                            scaling_values.append(100)  # Default fallback
                else:
                    # Fallback to uniform sizes if data not available
                    scaling_values = [min_size + (max_size - min_size) // 2] * len(type_clusters)
                
                # Scale marker sizes
                marker_sizes = scale_marker_size(scaling_values, min_size, max_size)
                
                ax1.scatter(lngs, lats, c=color, s=marker_sizes, 
                           alpha=0.7, label=f'{cluster_type.capitalize()} Clusters', 
                           edgecolors='black', linewidth=1)
        
        # Plot NTC connections (same logic as existing network visualization)
        ntc_connections = 0
        water_crossings = 0
        if hasattr(self, 'ntc_matrix') and self.ntc_matrix is not None:
            ntc_matrix = self.ntc_matrix
            max_capacity = ntc_matrix['s_nom'].max()
            
            for _, connection in ntc_matrix.iterrows():
                # Convert cluster IDs to int to avoid float formatting issues
                try:
                    from_id = int(float(connection['from_cluster_id'])) if pd.notna(connection['from_cluster_id']) else 0
                    to_id = int(float(connection['to_cluster_id'])) if pd.notna(connection['to_cluster_id']) else 0
                except (ValueError, TypeError):
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
                        line_color = renewable_color
                    elif connection['from_cluster_type'] == 'generation':
                        line_color = generation_color
                    else:
                        line_color = demand_color
                    
                    # Style based on water crossing
                    if crosses_water:
                        line_style = '--'
                        line_alpha = 0.8
                        water_crossings += 1
                    else:
                        line_style = '-'
                        line_alpha = 0.6
                        ntc_connections += 1
                    
                    ax1.plot([from_pos[0], to_pos[0]], [from_pos[1], to_pos[1]], 
                           color=line_color, linewidth=line_width, alpha=line_alpha,
                           linestyle=line_style)
        
        # Create custom legend for line styles (same as existing network visualization)
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color=demand_color, lw=2, label='Demand Connections'),
            Line2D([0], [0], color=generation_color, lw=2, label='Generation Connections'),
            Line2D([0], [0], color=renewable_color, lw=2, label='Renewable Connections'),
            Line2D([0], [0], color='black', lw=2, linestyle='-', label='Regular Lines'),
            Line2D([0], [0], color='black', lw=2, linestyle='--', label='Water Crossings')
        ]
        ax1.legend(handles=legend_elements, loc='upper right', fontsize=8)
        
        # Add explanatory text
        explanation = (
            "SYNTHETIC GRID OVERVIEW\n\n"
            "• Top panels show individual cluster shapes\n"
            "• Bottom left: Demand & Generation clusters\n"
            "• Bottom right: Final network bus centers\n"
            "• Each center becomes a synthetic bus\n"
            "• Connections shown in separate network plot"
        )
        ax1.text(0.02, 0.02, explanation, transform=ax1.transAxes, fontsize=9,
                verticalalignment='bottom', 
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout()
        
        # Save or show
        if save_file:
            plt.savefig(save_file, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"💾 4-panel cluster shapes validation saved: {save_file}")
        
        return fig

    def generate_shape_statistics(self):
        """Generate statistics about cluster shapes for validation"""
        if not any([self.demand_centers, self.generation_centers, self.renewable_centers]):
            print("❌ No cluster data available for statistics")
            return None
        
        stats = {
            'demand_clusters': len(self.demand_centers) if self.demand_centers is not None else 0,
            'generation_clusters': len(self.generation_centers) if self.generation_centers is not None else 0,
            'renewable_clusters': len(self.renewable_centers) if self.renewable_centers is not None else 0,
            'total_clusters': 0
        }
        
        stats['total_clusters'] = (stats['demand_clusters'] + 
                                 stats['generation_clusters'] + 
                                 stats['renewable_clusters'])
        
        print(f"📊 Cluster Statistics:")
        print(f"   • Demand clusters: {stats['demand_clusters']}")
        print(f"   • Generation clusters: {stats['generation_clusters']}")
        print(f"   • Renewable clusters: {stats['renewable_clusters']}")
        print(f"   • Total clusters: {stats['total_clusters']}")
        
        return stats
