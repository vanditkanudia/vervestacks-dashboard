#!/usr/bin/env python3
"""
NTC Network Visualization
=========================

Visualizes the realistic NTC connections between cluster centroids with arrows
showing transmission corridors between demand, generation, and renewable zones.

Usage:
    python visualize_ntc_network.py --country USA --output-dir output/USA_d10g10r10
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import argparse
import os
from pathlib import Path

class NTCNetworkVisualizer:
    """Visualize NTC connections between cluster centroids"""
    
    def __init__(self, country_code, output_dir='output'):
        self.country = country_code
        self.output_dir = output_dir
        
        # Load cluster data
        self.demand_centers = None
        self.gem_centers = None
        self.renewable_centers = None
        self.ntc_connections = None
        
    def load_data(self):
        """Load all cluster centers and NTC connections"""
        base_path = Path(self.output_dir)
        
        # Load demand centers
        demand_file = base_path / f'{self.country}_region_centers.csv'
        if demand_file.exists():
            self.demand_centers = pd.read_csv(demand_file)
            print(f"Loaded {len(self.demand_centers)} demand centers")
        
        # Load GEM centers
        gem_file = base_path / f'{self.country}_gem_cluster_centers.csv'
        if gem_file.exists():
            self.gem_centers = pd.read_csv(gem_file)
            print(f"Loaded {len(self.gem_centers)} GEM centers")
        
        # Load renewable centers
        renewable_file = base_path / f'{self.country}_renewable_cluster_centers.csv'
        if renewable_file.exists():
            self.renewable_centers = pd.read_csv(renewable_file)
            print(f"Loaded {len(self.renewable_centers)} renewable centers")
        
        # Load realistic NTC connections (now includes visualization-ready format)
        ntc_file = base_path / f'{self.country}_realistic_ntc_connections.csv'
        if ntc_file.exists():
            self.ntc_connections = pd.read_csv(ntc_file)
            print(f"Loaded {len(self.ntc_connections)} realistic NTC connections")
            if 'connection_type' in self.ntc_connections.columns:
                print(f"Connection types: {self.ntc_connections['connection_type'].value_counts().to_dict()}")
        else:
            print(f"Warning: No realistic NTC connections file found")
            self.ntc_connections = None
    
    def create_ntc_visualization(self):
        """Create the main NTC network visualization"""
        if not all([self.demand_centers is not None, 
                   self.gem_centers is not None, 
                   self.renewable_centers is not None,
                   self.ntc_connections is not None]):
            print("Missing required data for visualization")
            return None
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        
        # Define colors and styles for each cluster type
        colors = {
            'DEMAND': '#2E86AB',      # Blue
            'GEM': '#A23B72',         # Purple/Magenta  
            'RENEWABLE': '#F18F01'    # Orange
        }
        
        markers = {
            'DEMAND': 'o',      # Circle
            'GEM': 's',         # Square
            'RENEWABLE': '^'    # Triangle
        }
        
        sizes = {
            'DEMAND': 200,
            'GEM': 150, 
            'RENEWABLE': 180
        }
        
        # Plot cluster centroids
        self._plot_cluster_centroids(ax, colors, markers, sizes)
        
        # Draw NTC connections as arrows
        self._draw_ntc_arrows(ax, colors)
        
        # Add legend and formatting
        self._add_legend_and_formatting(ax, colors, markers, sizes)
        
        # Save visualization
        output_file = Path(self.output_dir) / f'{self.country}_ntc_network.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"NTC network visualization saved: {output_file}")
        
        plt.show()
        return output_file
    
    def _plot_cluster_centroids(self, ax, colors, markers, sizes):
        """Plot the cluster centroids"""
        
        # Plot demand centers
        if self.demand_centers is not None:
            ax.scatter(self.demand_centers['center_lng'], self.demand_centers['center_lat'],
                      c=colors['DEMAND'], marker=markers['DEMAND'], s=sizes['DEMAND'],
                      alpha=0.8, edgecolors='white', linewidth=2, zorder=5,
                      label=f'Demand Regions ({len(self.demand_centers)})')
        
        # Plot GEM centers  
        if self.gem_centers is not None:
            ax.scatter(self.gem_centers['center_lng'], self.gem_centers['center_lat'],
                      c=colors['GEM'], marker=markers['GEM'], s=sizes['GEM'],
                      alpha=0.8, edgecolors='white', linewidth=2, zorder=5,
                      label=f'Generation Clusters ({len(self.gem_centers)})')
        
        # Plot renewable centers
        if self.renewable_centers is not None:
            ax.scatter(self.renewable_centers['center_lng'], self.renewable_centers['center_lat'],
                      c=colors['RENEWABLE'], marker=markers['RENEWABLE'], s=sizes['RENEWABLE'],
                      alpha=0.8, edgecolors='white', linewidth=2, zorder=5,
                      label=f'Renewable Zones ({len(self.renewable_centers)})')
    
    def _get_cluster_coordinates(self, cluster_name, cluster_type):
        """Get coordinates for a cluster by name and type"""
        if cluster_type == 'DEMAND' and self.demand_centers is not None:
            cluster = self.demand_centers[self.demand_centers['name'] == cluster_name]
        elif cluster_type == 'GEM' and self.gem_centers is not None:
            cluster = self.gem_centers[self.gem_centers['name'] == cluster_name]
        elif cluster_type == 'RENEWABLE' and self.renewable_centers is not None:
            cluster = self.renewable_centers[self.renewable_centers['name'] == cluster_name]
        else:
            return None, None
            
        if len(cluster) > 0:
            return cluster.iloc[0]['center_lng'], cluster.iloc[0]['center_lat']
        return None, None
    
    def _draw_ntc_arrows(self, ax, colors):
        """Draw arrows representing NTC connections"""
        if self.ntc_connections is None:
            return
        
        # Group connections by capacity for different arrow styles
        connections = self.ntc_connections.copy()
        connections['capacity_tier'] = pd.cut(connections['ntc_mw'], 
                                            bins=[0, 1000, 5000, 20000, float('inf')],
                                            labels=['Small', 'Medium', 'Large', 'Massive'])
        
        # Arrow styles by capacity
        arrow_styles = {
            'Small': {'width': 0.5, 'alpha': 0.3},
            'Medium': {'width': 1.0, 'alpha': 0.5},
            'Large': {'width': 1.5, 'alpha': 0.7},
            'Massive': {'width': 2.5, 'alpha': 0.9}
        }
        
        # Connection type colors (lighter versions of cluster colors)
        connection_colors = {
            ('GEM', 'DEMAND'): '#D4A5C7',           # Light purple
            ('RENEWABLE', 'DEMAND'): '#F8C471',     # Light orange  
            ('RENEWABLE', 'GEM'): '#85C1E9'         # Light blue
        }
        
        for _, conn in connections.iterrows():
            from_type = conn['from_type']
            to_type = conn['to_type']
            
            # Get coordinates - use direct coordinates from comprehensive file if available
            if 'from_lat' in conn and 'from_lng' in conn and pd.notna(conn['from_lat']):
                from_lat, from_lng = conn['from_lat'], conn['from_lng']
            else:
                from_lng, from_lat = self._get_cluster_coordinates(conn['from_name'], from_type)
            
            if 'to_lat' in conn and 'to_lng' in conn and pd.notna(conn['to_lat']):
                to_lat, to_lng = conn['to_lat'], conn['to_lng']
            else:
                to_lng, to_lat = self._get_cluster_coordinates(conn['to_name'], to_type)
            
            if from_lng is None or to_lng is None:
                continue
            
            # Get arrow style
            capacity_tier = conn['capacity_tier']
            style = arrow_styles.get(capacity_tier, arrow_styles['Medium'])
            
            # Get connection color
            conn_color = connection_colors.get((from_type, to_type), '#CCCCCC')
            
            # Create arrow
            arrow = FancyArrowPatch(
                (from_lng, from_lat), (to_lng, to_lat),
                arrowstyle='->', 
                mutation_scale=15,
                linewidth=style['width'],
                alpha=style['alpha'],
                color=conn_color,
                zorder=2
            )
            ax.add_patch(arrow)
    
    def _add_legend_and_formatting(self, ax, colors, markers, sizes):
        """Add legend, title, and formatting"""
        
        # Add cluster legend
        ax.legend(loc='upper right', bbox_to_anchor=(0.98, 0.98), 
                 frameon=True, fancybox=True, shadow=True, fontsize=10)
        
        # Add connection legend
        legend_elements = []
        
        # NTC capacity legend
        capacity_legend = [
            ('Massive (>20 GW)', 2.5, 0.9),
            ('Large (5-20 GW)', 1.5, 0.7),
            ('Medium (1-5 GW)', 1.0, 0.5),
            ('Small (<1 GW)', 0.5, 0.3)
        ]
        
        # Add text box with NTC capacity legend
        legend_text = "NTC Capacity:\n"
        for label, width, alpha in capacity_legend:
            legend_text += f"  {label}\n"
        
        ax.text(0.02, 0.98, legend_text, transform=ax.transAxes, 
               bbox=dict(boxstyle="round,pad=0.5", facecolor='white', alpha=0.8),
               verticalalignment='top', fontsize=9, family='monospace')
        
        # Add connection type legend
        conn_legend_text = "Connection Types:\n"
        conn_legend_text += "  Renewable → Demand\n"
        conn_legend_text += "  Generation → Demand\n" 
        conn_legend_text += "  Renewable → Generation"
        
        ax.text(0.02, 0.65, conn_legend_text, transform=ax.transAxes,
               bbox=dict(boxstyle="round,pad=0.5", facecolor='white', alpha=0.8),
               verticalalignment='top', fontsize=9, family='monospace')
        
        # Formatting
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_title(f'{self.country} - Realistic NTC Network Topology\n'
                    f'Transmission Connections Between Energy Clusters', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        
        # Add summary statistics
        if self.ntc_connections is not None:
            total_capacity = self.ntc_connections['ntc_mw'].sum()
            total_connections = len(self.ntc_connections)
            avg_distance = self.ntc_connections['distance_km'].mean()
            
            stats_text = f"Network Statistics:\n"
            stats_text += f"  Total Connections: {total_connections}\n"
            stats_text += f"  Total NTC Capacity: {total_capacity:,.0f} MW\n"
            stats_text += f"  Average Distance: {avg_distance:.0f} km"
            
            ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
                   bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.8),
                   verticalalignment='bottom', horizontalalignment='right',
                   fontsize=9, family='monospace')

def main():
    parser = argparse.ArgumentParser(description='Visualize NTC network connections')
    parser.add_argument('--country', required=True, help='Country code (e.g., USA, IND)')
    parser.add_argument('--output-dir', required=True, help='Output directory with cluster files')
    
    args = parser.parse_args()
    
    print(f"Creating NTC network visualization for {args.country}...")
    
    visualizer = NTCNetworkVisualizer(args.country, args.output_dir)
    visualizer.load_data()
    visualizer.create_ntc_visualization()
    
    print("NTC network visualization complete!")

if __name__ == '__main__':
    main()
