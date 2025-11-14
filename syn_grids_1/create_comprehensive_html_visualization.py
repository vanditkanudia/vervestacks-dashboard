import pandas as pd
import numpy as np
import folium
from folium import plugins
import argparse
import os
import glob

def detect_available_layers(country_code, output_dir='output'):
    """
    Detect what clustering layers are available for a country
    """
    layers = {}
    
    # Check for demand regions
    demand_points_file = f'{output_dir}/{country_code}_demand_points.csv'
    region_centers_file = f'{output_dir}/{country_code}_region_centers.csv'
    if os.path.exists(demand_points_file) and os.path.exists(region_centers_file):
        layers['demand'] = {
            'points': demand_points_file,
            'centers': region_centers_file,
            'available': True
        }
    
    # Check for renewable clusters (combined solar+wind)
    renewable_centers_file = f'{output_dir}/{country_code}_renewable_cluster_centers.csv'
    renewable_mapping_file = f'{output_dir}/{country_code}_renewable_cluster_mapping.csv'
    if os.path.exists(renewable_centers_file):
        layers['renewable'] = {
            'centers': renewable_centers_file,
            'mapping': renewable_mapping_file if os.path.exists(renewable_mapping_file) else None,
            'available': True
        }
    
    # Check for solar-only clusters
    solar_centers_file = f'{output_dir}/{country_code}_solar_cluster_centers.csv'
    solar_mapping_file = f'{output_dir}/{country_code}_solar_cluster_mapping.csv'
    if os.path.exists(solar_centers_file):
        layers['solar'] = {
            'centers': solar_centers_file,
            'mapping': solar_mapping_file if os.path.exists(solar_mapping_file) else None,
            'available': True
        }
    
    # Check for GEM generation clusters
    gem_centers_file = f'{output_dir}/{country_code}_gem_cluster_centers.csv'
    gem_mapping_file = f'{output_dir}/{country_code}_gem_cluster_mapping.csv'
    if os.path.exists(gem_centers_file):
        layers['gem'] = {
            'centers': gem_centers_file,
            'mapping': gem_mapping_file if os.path.exists(gem_mapping_file) else None,
            'available': True
        }
    
    return layers

def create_comprehensive_html_map(country_code='IND', output_dir='output'):
    """
    Create comprehensive interactive HTML map showing all available clustering layers
    """
    
    # Detect available layers
    layers = detect_available_layers(country_code, output_dir)
    
    if not layers:
        print(f"No clustering results found for {country_code}.")
        print("Run the clustering scripts first (create_regions.py, create_renewable_clusters.py, create_gem_units_clusters.py)")
        return None
    
    print(f"Available layers for {country_code}:")
    for layer_name, layer_info in layers.items():
        if layer_info.get('available'):
            print(f"  + {layer_name.upper()}")
    
    # Country-specific scaling factors
    country_scaling = {
        'CHE': {'divisor': 3, 'base': 5, 'zoom': 8},
        'ITA': {'divisor': 5, 'base': 4, 'zoom': 7},
        'DEU': {'divisor': 6, 'base': 4, 'zoom': 7},
        'USA': {'divisor': 10, 'base': 3, 'zoom': 5},
        'IND': {'divisor': 20, 'base': 3, 'zoom': 6},
        'CHN': {'divisor': 20, 'base': 3, 'zoom': 5},
        'JPN': {'divisor': 8, 'base': 3, 'zoom': 7},
        'AUS': {'divisor': 7, 'base': 4, 'zoom': 5},
        'ZAF': {'divisor': 8, 'base': 4, 'zoom': 6},
        'NZL': {'divisor': 4, 'base': 4, 'zoom': 7},
        'BRA': {'divisor': 12, 'base': 3, 'zoom': 5},
    }
    
    scaling = country_scaling.get(country_code, {'divisor': 5, 'base': 4, 'zoom': 6})
    
    # Determine map center from available data
    center_lat, center_lng = None, None
    
    if 'demand' in layers:
        demand_points = pd.read_csv(layers['demand']['points'])
        center_lat = demand_points['lat'].mean()
        center_lng = demand_points['lng'].mean()
    elif 'renewable' in layers:
        renewable_centers = pd.read_csv(layers['renewable']['centers'])
        center_lat = renewable_centers['center_lat'].mean()
        center_lng = renewable_centers['center_lng'].mean()
    elif 'gem' in layers:
        gem_centers = pd.read_csv(layers['gem']['centers'])
        center_lat = gem_centers['center_lat'].mean()
        center_lng = gem_centers['center_lng'].mean()
    
    if center_lat is None:
        print("Could not determine map center")
        return None
    
    # Create base map with layer control
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=scaling['zoom'],
        tiles='OpenStreetMap'
    )
    
    # Color schemes for different layer types
    demand_colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred',
                    'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
                    'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen',
                    'gray', 'black', 'lightgray', 'yellow']
    
    renewable_colors = ['green', 'darkgreen', 'lightgreen', 'blue', 'purple',
                       'orange', 'darkblue', 'cadetblue']
    
    gem_colors = ['red', 'darkred', 'orange', 'purple', 'darkblue',
                 'darkgreen', 'gray', 'black']
    
    # Layer groups for organization
    demand_layer = folium.FeatureGroup(name="Demand Regions")
    renewable_layer = folium.FeatureGroup(name="Renewable Zones")
    solar_layer = folium.FeatureGroup(name="Solar Zones")
    gem_layer = folium.FeatureGroup(name="Generation Plants")
    
    layer_stats = {}
    
    # Add demand regions layer
    if 'demand' in layers:
        try:
            demand_points = pd.read_csv(layers['demand']['points'])
            region_centers = pd.read_csv(layers['demand']['centers'])
            
            # Add population centers
            pop_points = demand_points[demand_points['type'] == 'population']
            for _, point in pop_points.iterrows():
                cluster_id = int(point['cluster'])
                color = demand_colors[cluster_id % len(demand_colors)]
                
                folium.CircleMarker(
                    location=[point['lat'], point['lng']],
                    radius=np.sqrt(point['raw_weight']/scaling['divisor']) + scaling['base'],
                    popup=folium.Popup(
                        f"<b>{point['name']}</b><br>"
                        f"Population: {point['raw_weight']*1000:,.0f}<br>"
                        f"Type: Population Center<br>"
                        f"Demand Weight: {point['scaled_weight']:.1f}<br>"
                        f"Demand Cluster: {cluster_id}",
                        max_width=300
                    ),
                    color=color,
                    fillColor=color,
                    fillOpacity=0.6,
                    weight=0
                ).add_to(demand_layer)
            
            # Add industrial facilities
            ind_points = demand_points[demand_points['type'] == 'industrial']
            for _, point in ind_points.iterrows():
                cluster_id = int(point['cluster'])
                color = demand_colors[cluster_id % len(demand_colors)]
                
                folium.RegularPolygonMarker(
                    location=[point['lat'], point['lng']],
                    number_of_sides=3,
                    radius=6,
                    popup=folium.Popup(
                        f"<b>{point['name']}</b><br>"
                        f"Type: {point.get('subtype', 'Industrial')}<br>"
                        f"Demand Weight: {point['raw_weight']:.1f}<br>"
                        f"Demand Cluster: {cluster_id}",
                        max_width=300
                    ),
                    color=color,
                    fillColor=color,
                    fillOpacity=0.6,
                    weight=0
                ).add_to(demand_layer)
            
            # Add demand region centers
            for _, center in region_centers.iterrows():
                cluster_id = int(center['cluster_id'])
                color = demand_colors[cluster_id % len(demand_colors)]
                
                folium.Marker(
                    location=[center['center_lat'], center['center_lng']],
                    popup=folium.Popup(
                        f"<b>{center['name']}</b><br>"
                        f"<hr><b>Demand Composition:</b><br>"
                        f"• Population: {center['population_demand']:.1f}<br>"
                        f"• Industrial: {center['industrial_demand']:.1f}<br>"
                        f"• Total: {center['total_demand']:.1f}<br>"
                        f"• Share: {center['demand_share']:.1%}<br>"
                        f"<hr><b>Components:</b><br>"
                        f"• Cities: {center['n_cities']}<br>"
                        f"• Industrial: {center['n_industrial']}<br>"
                        f"<hr><b>Major City:</b> {center['major_city']}",
                        max_width=400
                    ),
                    icon=folium.Icon(color=color, icon='home', prefix='fa')
                ).add_to(demand_layer)
            
            layer_stats['demand'] = {
                'regions': len(region_centers),
                'cities': len(pop_points),
                'industrial': len(ind_points)
            }
            
        except Exception as e:
            print(f"Error loading demand layer: {e}")
    
    # Add renewable zones layer
    if 'renewable' in layers:
        try:
            renewable_centers = pd.read_csv(layers['renewable']['centers'])
            
            for _, center in renewable_centers.iterrows():
                cluster_id = int(center['cluster_id'])
                color = renewable_colors[cluster_id % len(renewable_colors)]
                
                # Determine icon based on generation mix
                solar_gen = center.get('solar_generation_gwh', 0)
                wind_gen = center.get('wind_generation_gwh', 0)
                
                if solar_gen > wind_gen:
                    icon = 'sun-o'
                    dominant_tech = 'Solar'
                elif wind_gen > solar_gen:
                    icon = 'leaf' 
                    dominant_tech = 'Wind'
                else:
                    icon = 'bolt'
                    dominant_tech = 'Mixed'
                
                folium.Marker(
                    location=[center['center_lat'], center['center_lng']],
                    popup=folium.Popup(
                        f"<b>{center['name']}</b><br>"
                        f"<hr><b>Renewable Generation:</b><br>"
                        f"• Total: {center.get('total_generation_gwh', 0):.0f} GWh<br>"
                        f"• Solar: {center.get('solar_generation_gwh', 0):.0f} GWh<br>"
                        f"• Wind: {center.get('wind_generation_gwh', 0):.0f} GWh<br>"
                        f"• Dominant: {dominant_tech}<br>"
                        f"• Share: {center.get('generation_share', 0):.1%}<br>"
                        f"<hr><b>Grid Cells:</b> {center['n_grid_cells']}<br>"
                        f"<b>Distance-based clustering</b><br>"
                        f"<b>Transmission accessibility tier</b>",
                        max_width=400
                    ),
                    icon=folium.Icon(color=color, icon=icon, prefix='fa')
                ).add_to(renewable_layer)
                
                # Add capacity circle
                folium.Circle(
                    location=[center['center_lat'], center['center_lng']],
                    radius=np.sqrt(center.get('total_generation_gwh', 0)) * 10,  # Scale by generation
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.2,
                    weight=2,
                    opacity=0.6,
                    popup=f"RE Zone: {center['name']} ({center.get('total_generation_gwh', 0):.0f} GWh)"
                ).add_to(renewable_layer)
            
            layer_stats['renewable'] = {
                'zones': len(renewable_centers),
                'total_generation': renewable_centers['total_generation_gwh'].sum()
            }
            
        except Exception as e:
            print(f"Error loading renewable layer: {e}")
    
    # Add solar-only zones layer (if no combined renewable layer)
    if 'solar' in layers and 'renewable' not in layers:
        try:
            solar_centers = pd.read_csv(layers['solar']['centers'])
            
            for _, center in solar_centers.iterrows():
                cluster_id = int(center['cluster_id'])
                color = 'gold'
                
                folium.Marker(
                    location=[center['center_lat'], center['center_lng']],
                    popup=folium.Popup(
                        f"<b>{center['name']}</b><br>"
                        f"<hr><b>Solar Capacity:</b><br>"
                        f"• Total: {center['total_capacity_mw']:.0f} MW<br>"
                        f"• Share: {center['capacity_share']:.1%}<br>"
                        f"<hr><b>Grid Cells:</b> {center['n_grid_cells']}<br>"
                        f"<b>Avg CF:</b> {center.get('weighted_avg_cf', 0):.1%}<br>"
                        f"<b>Avg LCOE:</b> ${center.get('weighted_avg_lcoe', 0):.1f}/MWh",
                        max_width=400
                    ),
                    icon=folium.Icon(color='orange', icon='sun-o', prefix='fa')
                ).add_to(solar_layer)
            
            layer_stats['solar'] = {
                'zones': len(solar_centers),
                'total_capacity': solar_centers['total_capacity_mw'].sum()
            }
            
        except Exception as e:
            print(f"Error loading solar layer: {e}")
    
    # Add GEM generation clusters layer
    if 'gem' in layers:
        try:
            gem_centers = pd.read_csv(layers['gem']['centers'])
            
            for _, center in gem_centers.iterrows():
                cluster_id = int(center['cluster_id'])
                color = gem_colors[cluster_id % len(gem_colors)]
                
                # Determine icon based on dominant technology
                dominant_tech = center.get('dominant_tech', 'other').lower()
                if 'coal' in dominant_tech or 'subcritical' in dominant_tech or 'supercritical' in dominant_tech:
                    icon = 'industry'
                elif 'gas' in dominant_tech or 'combined cycle' in dominant_tech:
                    icon = 'fire'
                elif 'nuclear' in dominant_tech:
                    icon = 'atom'
                elif 'hydro' in dominant_tech:
                    icon = 'tint'
                elif 'wind' in dominant_tech:
                    icon = 'leaf'
                elif 'solar' in dominant_tech:
                    icon = 'sun-o'
                else:
                    icon = 'plug'
                
                folium.Marker(
                    location=[center['center_lat'], center['center_lng']],
                    popup=folium.Popup(
                        f"<b>{center['name']}</b><br>"
                        f"<hr><b>Generation Capacity:</b><br>"
                        f"• Total: {center['total_capacity_mw']:.0f} MW<br>"
                        f"• Dominant Tech: {center.get('dominant_tech', 'Mixed')}<br>"
                        f"• Share: {center['capacity_share']:.1%}<br>"
                        f"<hr><b>Plants:</b> {center['n_plants']}<br>"
                        f"<b>Avg Plant Size:</b> {center['avg_plant_size_mw']:.0f} MW<br>"
                        f"<b>Largest Plant:</b> {center['largest_plant_mw']:.0f} MW<br>"
                        f"<b>Tech Diversity:</b> {center['tech_diversity']} types" +
                        (f"<br><b>Avg Age:</b> {center['avg_age_years']:.0f} years" if pd.notna(center.get('avg_age_years')) else ""),
                        max_width=400
                    ),
                    icon=folium.Icon(color=color, icon=icon, prefix='fa')
                ).add_to(gem_layer)
                
                # Add capacity circle
                folium.Circle(
                    location=[center['center_lat'], center['center_lng']],
                    radius=np.sqrt(center['total_capacity_mw']) * 80,  # Scale by capacity
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.3,
                    weight=2,
                    opacity=0.7,
                    popup=f"Gen Cluster: {center['name']} ({center['total_capacity_mw']:.0f} MW)"
                ).add_to(gem_layer)
            
            layer_stats['gem'] = {
                'clusters': len(gem_centers),
                'total_capacity': gem_centers['total_capacity_mw'].sum(),
                'total_plants': gem_centers['n_plants'].sum()
            }
            
        except Exception as e:
            print(f"Error loading GEM layer: {e}")
    
    # Add layers to map
    if 'demand' in layer_stats:
        demand_layer.add_to(m)
    if 'renewable' in layer_stats:
        renewable_layer.add_to(m)
    if 'solar' in layer_stats and 'renewable' not in layer_stats:
        solar_layer.add_to(m)
    if 'gem' in layer_stats:
        gem_layer.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Create comprehensive legend
    legend_html = f'''
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 380px; height: auto; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:13px; padding: 12px; border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
    <h3 style="margin-top:0; color: #2E86AB;">{country_code} Multi-Layered Energy System</h3>
    '''
    
    # Add layer statistics
    if 'demand' in layer_stats:
        stats = layer_stats['demand']
        legend_html += f'''
        <div style="margin: 8px 0; padding: 6px; background-color: #f8f9fa; border-radius: 4px;">
        <b>Demand Regions:</b> {stats['regions']}<br>
        <small>• Cities: {stats['cities']} • Industrial: {stats['industrial']}</small>
        </div>
        '''
    
    if 'renewable' in layer_stats:
        stats = layer_stats['renewable']
        legend_html += f'''
        <div style="margin: 8px 0; padding: 6px; background-color: #e8f5e8; border-radius: 4px;">
        <b>🌞 Renewable Zones:</b> {stats['zones']}<br>
        <small>• Total Generation: {stats.get('total_generation', stats.get('total_capacity', 0)):,.0f} GWh</small>
        </div>
        '''
    
    if 'solar' in layer_stats and 'renewable' not in layer_stats:
        stats = layer_stats['solar']
        legend_html += f'''
        <div style="margin: 8px 0; padding: 6px; background-color: #fff3cd; border-radius: 4px;">
        <b>Solar Zones:</b> {stats['zones']}<br>
        <small>• Total Generation: {stats.get('total_generation', stats.get('total_capacity', 0)):,.0f} GWh</small>
        </div>
        '''
    
    if 'gem' in layer_stats:
        stats = layer_stats['gem']
        legend_html += f'''
        <div style="margin: 8px 0; padding: 6px; background-color: #f4e4bc; border-radius: 4px;">
        <b>🏭 Generation Clusters:</b> {stats['clusters']}<br>
        <small>• Plants: {stats['total_plants']:,} • Capacity: {stats['total_capacity']:,.0f} MW</small>
        </div>
        '''
    
    legend_html += '''
    <hr style="margin:10px 0;">
    <div style="font-size:11px; color: #666;">
    <b>Data Sources:</b> GEM, REZoning, OSM, WorldCities<br>
    <b>Clustering:</b> DBSCAN + K-means adjustment<br>
    <b>Transmission:</b> OSM-enhanced NTC estimation
    </div>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m, layer_stats

def main():
    parser = argparse.ArgumentParser(description='Create comprehensive interactive HTML visualization for all energy system layers')
    parser.add_argument('--country', required=True, 
                       help='Country code')
    parser.add_argument('--output-dir', default='.',
                       help='Output directory for HTML file (default: current directory)')
    
    args = parser.parse_args()
    country = args.country
    
    print(f"Creating comprehensive energy system map for {country}...")
    
    result = create_comprehensive_html_map(country, args.output_dir)
    
    if result:
        map_obj, layer_stats = result
        
        # Create output directory if it doesn't exist
        import os
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Save HTML file in the specified output directory
        html_filename = f'{country}_comprehensive_energy_system.html'
        html_path = os.path.join(args.output_dir, html_filename)
        map_obj.save(html_path)
        
        print(f"\nSaved comprehensive map to {html_path}")
        print(f"Open the file in your browser to view the visualization!")
        
        print(f"\nLayer Summary:")
        for layer, stats in layer_stats.items():
            print(f"  {layer.upper()}: {stats}")
    else:
        print("Failed to create map. Make sure clustering scripts have been run first.")

if __name__ == "__main__":
    main()
