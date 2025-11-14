#!/usr/bin/env python3
"""
Cluster Shapes Validator for Synthetic Grid Planning
===================================================

Enhances existing VerveStacks visualization to show full cluster shapes
(not just centroids) to validate how substations will be grouped.

Reuses visualization components from create_summary_map_visual.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Wedge, Polygon
from scipy.spatial import ConvexHull, Voronoi
import argparse
import os
import sys
from pathlib import Path

# Import existing boundary function from create_summary_map_visual
sys.path.append('.')
try:
    from create_summary_map_visual import get_country_boundaries
    BOUNDARY_FUNCTION_AVAILABLE = True
except ImportError:
    BOUNDARY_FUNCTION_AVAILABLE = False
    print("⚠️ Could not import boundary function, will create simplified boundaries")

class ClusterShapesValidator:
    """
    Enhanced cluster visualization showing full shapes for synthetic grid planning
    """
    
    def __init__(self, country_code, output_dir):
        self.country = country_code.upper()
        # Ensure output_dir is a Path object and create country-specific subdirectory
        self.output_dir = Path(output_dir) / self.country
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Visualization thresholds (reusing from existing code)
        self.min_generation_gwh = 100   
        self.min_capacity_mw = 10       
        self.min_population = 10000     
        
        # Load cluster data
        self.demand_centers = None
        self.demand_points = None
        self.generation_centers = None
        self.generation_mapping = None
        self.renewable_centers = None
        self.renewable_mapping = None
        
        # Data bounds for country boundary filtering
        self.data_bounds = None
        
    def load_cluster_data(self):
        """Load all cluster data from passed results or CSV files"""
        # First try to use passed data
        if hasattr(self, 'demand_results') and self.demand_results is not None:
            if self.demand_results['centers'] is not None:
                self.demand_centers = pd.DataFrame(self.demand_results['centers'])
                print(f"📍 Using passed demand centers: {len(self.demand_centers)}")
            if self.demand_results['points'] is not None:
                self.demand_points = pd.DataFrame(self.demand_results['points'])
                print(f"📍 Using passed demand points: {len(self.demand_points)}")
        else:
            # Fallback to loading from CSV files
            base_path = Path(self.output_dir)
            demand_centers_file = base_path / f'{self.country}_region_centers.csv'
            demand_points_file = base_path / f'{self.country}_demand_points.csv'
            
            if demand_centers_file.exists():
                self.demand_centers = pd.read_csv(demand_centers_file)
                print(f"📍 Loaded {len(self.demand_centers)} demand centers from CSV")
        
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
        all_lats, all_lngs = [], []
        
        # Collect all coordinates
        if self.demand_centers is not None:
            all_lats.extend(self.demand_centers['center_lat'].tolist())
            all_lngs.extend(self.demand_centers['center_lng'].tolist())
        
        if self.generation_centers is not None:
            all_lats.extend(self.generation_centers['center_lat'].tolist())
            all_lngs.extend(self.generation_centers['center_lng'].tolist())
        
        if self.renewable_centers is not None:
            all_lats.extend(self.renewable_centers['center_lat'].tolist())
            all_lngs.extend(self.renewable_centers['center_lng'].tolist())
        
        if all_lats and all_lngs:
            self.data_bounds = (min(all_lngs), max(all_lngs), min(all_lats), max(all_lats))
            print(f"📊 Data bounds: {self.data_bounds}")
    
    def create_cluster_shapes_from_points(self, cluster_centers, cluster_points, cluster_id_col='cluster_id'):
        """
        Create cluster shapes using ConvexHull from the actual clustered points
        (not just Voronoi from centers)
        """
        if cluster_centers is None or cluster_points is None:
            return None
        
        cluster_shapes = {}
        
        for _, center in cluster_centers.iterrows():
            cluster_id = center[cluster_id_col]
            
            # Get all points assigned to this cluster
            if 'cluster' in cluster_points.columns:
                cluster_data = cluster_points[cluster_points['cluster'] == cluster_id]
            elif cluster_id_col in cluster_points.columns:
                cluster_data = cluster_points[cluster_points[cluster_id_col] == cluster_id]
            else:
                continue
            
            if len(cluster_data) >= 3:  # Need at least 3 points for ConvexHull
                try:
                    # Extract coordinates
                    coords = cluster_data[['lng', 'lat']].values
                    
                    # Create ConvexHull (actual cluster shape from data points)
                    hull = ConvexHull(coords)
                    hull_coords = coords[hull.vertices]
                    
                    # Create polygon
                    cluster_shapes[cluster_id] = Polygon(hull_coords)
                    
                except Exception as e:
                    print(f"⚠️ Could not create shape for cluster {cluster_id}: {e}")
                    # Fallback to circle around center
                    cluster_shapes[cluster_id] = Circle(
                        (center['center_lng'], center['center_lat']), 
                        0.5
                    )
            else:
                # Fallback for clusters with few points
                cluster_shapes[cluster_id] = Circle(
                    (center['center_lng'], center['center_lat']), 
                    0.5
                )
        
        return cluster_shapes
    
    def create_cluster_shapes_from_voronoi(self, cluster_centers, lat_col='center_lat', lng_col='center_lng'):
        """
        Create Voronoi-based cluster shapes (backup method)
        """
        if cluster_centers is None or len(cluster_centers) == 0:
            return None
        
        # Extract coordinates
        coords = cluster_centers[[lng_col, lat_col]].values
        
        try:
            # Create Voronoi diagram
            vor = Voronoi(coords)
            
            cluster_shapes = {}
            for i, (point_idx, region_idx) in enumerate(vor.point_region):
                region = vor.regions[region_idx]
                if len(region) > 0 and -1 not in region:  # Valid finite region
                    polygon_coords = vor.vertices[region]
                    if len(polygon_coords) >= 3:  # Valid polygon
                        cluster_shapes[i] = Polygon(polygon_coords)
            
            return cluster_shapes
            
        except Exception as e:
            print(f"⚠️ Could not create Voronoi shapes: {e}")
            return None
    
    def visualize_cluster_shapes(self, save_file=None):
        """
        Create comprehensive cluster shapes visualization in 4 subplots:
        1. Solar hulls only
        2. Wind hulls only (onshore + offshore)
        3. Demand & Generation hulls
        4. Resulting network view
        """
        fig, axes = plt.subplots(2, 2, figsize=(20, 16))
        axes = axes.flatten()  # Flatten for easier indexing
        
        # Load cluster data (will use passed data if available)
        self.load_cluster_data()
        
        # Debug: Check what data we have
        print(f"🔍 Debug - demand_centers: {self.demand_centers is not None}")
        print(f"🔍 Debug - generation_centers: {self.generation_centers is not None}")
        print(f"🔍 Debug - renewable_centers: {self.renewable_centers is not None}")
        
        if self.demand_centers is not None:
            print(f"🔍 Debug - demand_centers shape: {self.demand_centers.shape}")
        if self.generation_centers is not None:
            print(f"🔍 Debug - generation_centers shape: {self.generation_centers.shape}")
        if self.renewable_centers is not None:
            print(f"🔍 Debug - renewable_centers shape: {self.renewable_centers.shape}")
        
        # Set main title
        fig.suptitle(f'{self.country} Synthetic Grid Cluster Validation - 4-Panel View', 
                     fontsize=18, fontweight='bold', y=0.95)
        
        # Colors for different cluster types
        demand_color = '#FF4444'      # Red
        generation_color = '#4444FF'  # Blue  
        renewable_color = '#44AA44'   # Green
        
        # Get country boundaries once for all subplots
        boundaries = None
        if BOUNDARY_FUNCTION_AVAILABLE and self.data_bounds:
            try:
                boundaries = get_country_boundaries(self.country, self.data_bounds)
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
        
        # SUBPLOT 1: Solar Hulls Only
        ax1 = axes[0]
        setup_subplot(ax1, "Solar Clusters", xlim, ylim)
        
        if (self.renewable_centers is not None and 
            hasattr(self, 'renewable_results') and 
            self.renewable_results and 
            'technologies' in self.renewable_results and 
            'solar' in self.renewable_results['technologies']):
            
            solar_data = self.renewable_results['technologies']['solar']
            if 'cell_mapping' in solar_data and solar_data['cell_mapping'] is not None:
                # Plot solar points
                solar_points = solar_data['cell_mapping']
                ax1.scatter(solar_points['lon'], solar_points['lat'], 
                           c=renewable_color, s=20, alpha=0.6, marker='^')
                
                # Create and plot solar hulls
                solar_shapes = self.create_cluster_shapes_from_points(
                    pd.DataFrame(solar_data['stats']), solar_points
                )
                if solar_shapes:
                    for cluster_id, shape in solar_shapes.items():
                        if isinstance(shape, Polygon):
                            coords = np.array(shape.get_xy())
                            ax1.fill(coords[:, 0], coords[:, 1], 
                                   color=renewable_color, alpha=0.2, 
                                   edgecolor=renewable_color, linewidth=2)
                
                # Plot solar centers
                if 'stats' in solar_data and solar_data['stats'] is not None:
                    solar_centers = solar_data['stats']
                    ax1.scatter(solar_centers['centroid_lon'], solar_centers['centroid_lat'],
                              c=renewable_color, s=100, marker='^', alpha=0.8, 
                              edgecolors='white', linewidth=1)
                    
                    # Add labels
                    for _, center in solar_centers.iterrows():
                        ax1.annotate(f"S{int(center['cluster_id'])}", 
                                   (center['centroid_lon'], center['centroid_lat']),
                                   xytext=(5, 5), textcoords='offset points', fontsize=8,
                                   fontweight='bold', color='white',
                                   bbox=dict(boxstyle='round,pad=0.2', facecolor=renewable_color, alpha=0.8))
        
        # SUBPLOT 2: Wind Hulls Only (Onshore + Offshore)
        ax2 = axes[1]
        setup_subplot(ax2, "Wind Clusters (Onshore + Offshore)", xlim, ylim)
        
        wind_technologies = ['wind_onshore', 'wind_offshore']
        wind_colors = {'wind_onshore': '#228B22', 'wind_offshore': '#006400'}  # Different greens
        
        for tech in wind_technologies:
            if (self.renewable_results and 
                'technologies' in self.renewable_results and 
                tech in self.renewable_results['technologies']):
                
                wind_data = self.renewable_results['technologies'][tech]
                if 'cell_mapping' in wind_data and wind_data['cell_mapping'] is not None:
                    # Plot wind points
                    wind_points = wind_data['cell_mapping']
                    ax2.scatter(wind_points['lon'], wind_points['lat'], 
                               c=wind_colors[tech], s=20, alpha=0.6, marker='v',
                               label=f'{tech.replace("_", " ").title()}')
                    
                    # Create and plot wind hulls
                    wind_shapes = self.create_cluster_shapes_from_points(
                        pd.DataFrame(wind_data['stats']), wind_points
                    )
                    if wind_shapes:
                        for cluster_id, shape in wind_shapes.items():
                            if isinstance(shape, Polygon):
                                coords = np.array(shape.get_xy())
                                ax2.fill(coords[:, 0], coords[:, 1], 
                                       color=wind_colors[tech], alpha=0.15, 
                                       edgecolor=wind_colors[tech], linewidth=1.5)
                    
                    # Plot wind centers
                    if 'stats' in wind_data and wind_data['stats'] is not None:
                        wind_centers = wind_data['stats']
                        ax2.scatter(wind_centers['centroid_lon'], wind_centers['centroid_lat'],
                                  c=wind_colors[tech], s=100, marker='v', alpha=0.8, 
                                  edgecolors='white', linewidth=1)
                        
                        # Add labels
                        for _, center in wind_centers.iterrows():
                            ax2.annotate(f"W{int(center['cluster_id'])}", 
                                       (center['centroid_lon'], center['centroid_lat']),
                                       xytext=(5, 5), textcoords='offset points', fontsize=8,
                                       fontweight='bold', color='white',
                                       bbox=dict(boxstyle='round,pad=0.2', facecolor=wind_colors[tech], alpha=0.8))
        
        ax2.legend(loc='upper right', fontsize=9)
        
        # Plot generation cluster shapes  
        if self.generation_centers is not None and self.generation_mapping is not None:
            # Use actual plant locations for cluster shapes
            generation_shapes = self.create_cluster_shapes_from_points(
                self.generation_centers, self.generation_mapping
            )
            
            if generation_shapes:
                for cluster_id, shape in generation_shapes.items():
                    if isinstance(shape, Polygon):
                        coords = np.array(shape.get_xy())
                        ax.fill(coords[:, 0], coords[:, 1], 
                               color=generation_color, alpha=0.2, 
                               edgecolor=generation_color, linewidth=2)
                    elif isinstance(shape, Circle):
                        ax.add_patch(patches.Circle(shape.center, shape.radius,
                                                  color=generation_color, alpha=0.2,
                                                  edgecolor=generation_color, linewidth=2))
            
            # Plot generation centers
            ax.scatter(self.generation_centers['center_lng'], self.generation_centers['center_lat'],
                      c=generation_color, s=120, marker='s', alpha=0.8,
                      label=f'Generation Clusters ({len(self.generation_centers)})', 
                      zorder=5, edgecolors='white', linewidth=1)
            
            # Add cluster labels
            for _, center in self.generation_centers.iterrows():
                ax.annotate(f"G{center.get('cluster_id', center.name)}", 
                           (center['center_lng'], center['center_lat']),
                           xytext=(5, 5), textcoords='offset points', fontsize=9,
                           fontweight='bold', color='white',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor=generation_color, alpha=0.8))
        
        # Plot renewable cluster shapes
        if self.renewable_centers is not None and self.renewable_mapping is not None:
            # Use actual grid cell locations for cluster shapes
            renewable_shapes = self.create_cluster_shapes_from_points(
                self.renewable_centers, self.renewable_mapping
            )
            
            if renewable_shapes:
                for cluster_id, shape in renewable_shapes.items():
                    if isinstance(shape, Polygon):
                        coords = np.array(shape.get_xy())
                        ax.fill(coords[:, 0], coords[:, 1], 
                               color=renewable_color, alpha=0.2, 
                               edgecolor=renewable_color, linewidth=2)
                    elif isinstance(shape, Circle):
                        ax.add_patch(patches.Circle(shape.center, shape.radius,
                                                  color=renewable_color, alpha=0.2,
                                                  edgecolor=renewable_color, linewidth=2))
            
            # Plot renewable centers
            ax.scatter(self.renewable_centers['center_lng'], self.renewable_centers['center_lat'],
                      c=renewable_color, s=120, marker='^', alpha=0.8,
                      label=f'Renewable Zones ({len(self.renewable_centers)})', 
                      zorder=5, edgecolors='white', linewidth=1)
            
            # Add cluster labels
            for _, center in self.renewable_centers.iterrows():
                ax.annotate(f"R{center.get('cluster_id', center.name)}", 
                           (center['center_lng'], center['center_lat']),
                           xytext=(5, 5), textcoords='offset points', fontsize=9,
                           fontweight='bold', color='white',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor=renewable_color, alpha=0.8))
        
        # Customize plot
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=11)
        
        # Set aspect ratio to be roughly equal
        ax.set_aspect('equal', adjustable='box')
        
        # Add explanation text box
        explanation = (
            "🎯 SYNTHETIC GRID VALIDATION\n"
            "• Colored areas = Actual cluster shapes (ConvexHull of data points)\n"
            "• Substations will be grouped within these cluster boundaries\n"
            "• Transmission lines crossing cluster borders = Inter-cluster NTC\n"
            "• Each cluster becomes a synthetic bus in simplified grid model\n"
            "• Shape quality indicates how well substations will be grouped"
        )
        ax.text(0.02, 0.02, explanation, transform=ax.transAxes, fontsize=10,
                verticalalignment='bottom', 
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.9))
        
        plt.tight_layout()
        
        # Save or show
        if save_file:
            plt.savefig(save_file, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"💾 Cluster shapes validation saved: {save_file}")
        
        return fig
    
    def generate_shape_statistics(self):
        """Generate statistics about cluster shapes for validation"""
        stats = {
            'country': self.country,
            'output_dir': self.output_dir,
            'validation_summary': {}
        }
        
        # Demand cluster validation
        if self.demand_centers is not None and self.demand_points is not None:
            demand_shapes = self.create_cluster_shapes_from_points(
                self.demand_centers, self.demand_points
            )
            if demand_shapes:
                stats['validation_summary']['demand'] = {
                    'clusters_with_shapes': len(demand_shapes),
                    'total_clusters': len(self.demand_centers),
                    'shape_coverage': f"{len(demand_shapes)/len(self.demand_centers)*100:.1f}%"
                }
        
        # Generation cluster validation
        if self.generation_centers is not None and self.generation_mapping is not None:
            generation_shapes = self.create_cluster_shapes_from_points(
                self.generation_centers, self.generation_mapping
            )
            if generation_shapes:
                stats['validation_summary']['generation'] = {
                    'clusters_with_shapes': len(generation_shapes),
                    'total_clusters': len(self.generation_centers),
                    'shape_coverage': f"{len(generation_shapes)/len(self.generation_centers)*100:.1f}%"
                }
        
        # Renewable cluster validation
        if self.renewable_centers is not None and self.renewable_mapping is not None:
            renewable_shapes = self.create_cluster_shapes_from_points(
                self.renewable_centers, self.renewable_mapping
            )
            if renewable_shapes:
                stats['validation_summary']['renewable'] = {
                    'clusters_with_shapes': len(renewable_shapes),
                    'total_clusters': len(self.renewable_centers),
                    'shape_coverage': f"{len(renewable_shapes)/len(self.renewable_centers)*100:.1f}%"
                }
        
        return stats


def main():
    parser = argparse.ArgumentParser(description='Validate cluster shapes for synthetic grid planning')
    parser.add_argument('--country', required=True, help='ISO3 country code')
    parser.add_argument('--output-dir', required=True, help='Directory containing cluster CSV files')
    parser.add_argument('--save-file', help='Save visualization to file (optional)')
    
    args = parser.parse_args()
    
    print(f"🎯 CLUSTER SHAPES VALIDATION FOR SYNTHETIC GRID")
    print("=" * 60)
    print(f"Country: {args.country}")
    print(f"Data source: {args.output_dir}")
    print("=" * 60)
    
    # Create validator
    validator = ClusterShapesValidator(args.country, args.output_dir)
    
    # Load data
    validator.load_cluster_data()
    
    # Create visualization
    save_file = args.save_file or f"{args.output_dir}/{args.country}_cluster_shapes_validation.png"
    validator.visualize_cluster_shapes(save_file)
    
    # Print validation statistics
    stats = validator.generate_shape_statistics()
    print(f"\n📊 VALIDATION STATISTICS:")
    for key, value in stats['validation_summary'].items():
        print(f"{key.upper()}:")
        for subkey, subvalue in value.items():
            print(f"  {subkey}: {subvalue}")


if __name__ == "__main__":
    main()
