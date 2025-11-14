#!/usr/bin/env python3
"""
ISO-based PyPSA network visualization using consolidated output files.
Creates interactive visualization for any ISO country using OSM-Eur-prebuilt data and consolidated mappings.
"""

import pandas as pd
import geopandas as gpd
import json
import folium
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString
from folium import plugins
import pycountry
import sys
import warnings
warnings.filterwarnings('ignore')
from typing import Optional

  

# Resolve directories independent of CWD
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

def generate_svg_preview(buses_df, lines_df, plants_df, zones_df, svg_file_path):
    """
    Generate SVG preview of grid network using matplotlib
    
    Args:
        buses_df: Buses dataframe
        lines_df: Lines dataframe  
        plants_df: Power plants dataframe
        zones_df: Renewable zones dataframe
        svg_file_path (str): Path to save SVG file
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        import numpy as np
        
        # Create figure with high DPI for crisp SVG
        fig, ax = plt.subplots(figsize=(16, 12), dpi=150)
        
        # Set up the plot
        ax.set_aspect('equal')
        ax.set_facecolor('#f8f9fa')
        
        # Collect all coordinates to determine bounds
        all_lats = []
        all_lngs = []
        
        # Collect coordinates from all data sources
        if not buses_df.empty and 'lat' in buses_df.columns and 'lng' in buses_df.columns:
            valid_buses = buses_df.dropna(subset=['lat', 'lng'])
            all_lats.extend(valid_buses['lat'].tolist())
            all_lngs.extend(valid_buses['lng'].tolist())
        
        if not plants_df.empty and 'lat' in plants_df.columns and 'lng' in plants_df.columns:
            valid_plants = plants_df.dropna(subset=['lat', 'lng'])
            all_lats.extend(valid_plants['lat'].tolist())
            all_lngs.extend(valid_plants['lng'].tolist())
        
        if not lines_df.empty and 'geometry' in lines_df.columns:
            for idx, line in lines_df.iterrows():
                if hasattr(line['geometry'], 'coords'):
                    coords = list(line['geometry'].coords)
                    if len(coords) >= 2:
                        lngs, lats = zip(*coords)
                        all_lats.extend(lats)
                        all_lngs.extend(lngs)
        
        if not zones_df.empty and 'geometry' in zones_df.columns:
            for idx, zone in zones_df.iterrows():
                if hasattr(zone['geometry'], 'exterior'):
                    coords = list(zone['geometry'].exterior.coords)
                    if len(coords) >= 3:
                        lngs, lats = zip(*coords)
                        all_lats.extend(lats)
                        all_lngs.extend(lngs)
        
        # Set plot bounds based on data
        if all_lats and all_lngs:
            lat_min, lat_max = min(all_lats), max(all_lats)
            lng_min, lng_max = min(all_lngs), max(all_lngs)
            
            # Add some padding
            lat_padding = (lat_max - lat_min) * 0.1
            lng_padding = (lng_max - lng_min) * 0.1
            
            ax.set_xlim(lng_min - lng_padding, lng_max + lng_padding)
            ax.set_ylim(lat_min - lat_padding, lat_max + lat_padding)
            
            print(f"   📊 SVG bounds: Lat {lat_min:.3f}-{lat_max:.3f}, Lng {lng_min:.3f}-{lng_max:.3f}")
        else:
            # Fallback bounds if no data
            ax.set_xlim(-180, 180)
            ax.set_ylim(-90, 90)
            print("   ⚠️  No coordinate data found, using world bounds")
        
        # Plot renewable zones first (background)
        if not zones_df.empty and 'geometry' in zones_df.columns:
            for idx, zone in zones_df.iterrows():
                if hasattr(zone['geometry'], 'exterior'):
                    coords = list(zone['geometry'].exterior.coords)
                    if len(coords) >= 3:
                        lngs, lats = zip(*coords)
                        # Color based on zone type
                        if 'wof-' in str(zone.get('grid_cell', '')):
                            color = '#87CEEB'  # Sky blue for offshore wind
                        else:
                            color = '#90EE90'  # Light green for solar/onshore
                        ax.fill(lngs, lats, color=color, alpha=0.3, zorder=0)
        
        # Plot transmission lines
        if not lines_df.empty and 'geometry' in lines_df.columns:
            for idx, line in lines_df.iterrows():
                if hasattr(line['geometry'], 'coords'):
                    coords = list(line['geometry'].coords)
                    if len(coords) >= 2:
                        lngs, lats = zip(*coords)
                        ax.plot(lngs, lats, 'b-', alpha=0.6, linewidth=0.8, zorder=1)
        
        # Plot transmission buses
        if not buses_df.empty and 'lat' in buses_df.columns and 'lng' in buses_df.columns:
            valid_buses = buses_df.dropna(subset=['lat', 'lng'])
            if not valid_buses.empty:
                ax.scatter(valid_buses['lng'], valid_buses['lat'], 
                          c='blue', s=8, alpha=0.7, zorder=2, edgecolors='darkblue', linewidth=0.3)
        
        # Plot power plants
        if not plants_df.empty and 'lat' in plants_df.columns and 'lng' in plants_df.columns:
            valid_plants = plants_df.dropna(subset=['lat', 'lng'])
            if not valid_plants.empty:
                ax.scatter(valid_plants['lng'], valid_plants['lat'], 
                          c='red', s=20, alpha=0.8, zorder=3, edgecolors='darkred', linewidth=0.5)
        
        # Add title and labels
        ax.set_title('Grid Network Visualization\n(Click to open interactive version)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Longitude', fontsize=10)
        ax.set_ylabel('Latitude', fontsize=10)
        
        # Add legend
        legend_elements = [
            plt.Line2D([0], [0], color='blue', linewidth=2, label='Transmission Lines'),
            plt.scatter([], [], c='blue', s=30, label='Transmission Buses'),
            plt.scatter([], [], c='red', s=30, label='Power Plants'),
            plt.Rectangle((0, 0), 1, 1, facecolor='#90EE90', alpha=0.3, label='Solar/Wind Zones'),
            plt.Rectangle((0, 0), 1, 1, facecolor='#87CEEB', alpha=0.3, label='Offshore Wind Zones')
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=8, framealpha=0.9)
        
        # Remove ticks for cleaner look
        ax.tick_params(axis='both', which='major', labelsize=8)
        
        # Save as SVG
        plt.tight_layout()
        plt.savefig(svg_file_path, format='svg', bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"   📸 SVG preview generated: {svg_file_path}")
        
    except Exception as e:
        print(f"   ⚠️  Error generating SVG preview: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: create a simple placeholder
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.text(0.5, 0.5, f"Grid Visualization\n(Click to open interactive version)", 
                   ha='center', va='center', fontsize=16, 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            plt.savefig(svg_file_path, format='svg', bbox_inches='tight')
            plt.close()
            print(f"   📸 Fallback SVG created: {svg_file_path}")
        except Exception as e2:
            print(f"   ❌ Could not create fallback SVG: {e2}")

def get_iso2_from_iso3(iso3_code):
    """Convert ISO3 code to ISO2 code"""
    try:
        country = pycountry.countries.get(alpha_3=iso3_code)
        if country:
            return country.alpha_2
    except:
        pass
    
    # Fallback dictionary for special cases
    iso3_to_iso2 = {
        'CHE': 'CH',
        'DEU': 'DE', 
        'FRA': 'FR',
        'GBR': 'GB',
        'ITA': 'IT',
        'ESP': 'ES',
        'POL': 'PL',
        'NLD': 'NL',
        'BEL': 'BE',
        'AUT': 'AT',
        'CZE': 'CZ',
        'DNK': 'DK',
        'NOR': 'NO',
        'SWE': 'SE',
        'FIN': 'FI',
        'XKX': 'XK'   # Kosovo
    }
    
    return iso3_to_iso2.get(iso3_code, iso3_code[:2])

def load_consolidated_data(iso_code, output_dir='output'):
    """Load consolidated data for specific ISO country"""
    print(f"Loading consolidated data for {iso_code}...")
    
    # Convert ISO3 to ISO2 for file naming
    iso2_code = get_iso2_from_iso3(iso_code)
    
    # Load power plants assignments
    plants_file = SCRIPT_DIR / output_dir / iso_code / f"{iso_code}_power_plants_assigned_to_buses.csv"
    if plants_file.exists():
        plants_assignments = pd.read_csv(plants_file)
        print(f"  - Loaded {len(plants_assignments)} power plant assignments")
    else:
        print(f"  - Power plants file not found: {plants_file}")
        plants_assignments = pd.DataFrame()
    
    # Load zone bus mapping
    zones_file = SCRIPT_DIR / output_dir / iso_code / f"{iso_code}_zone_bus_mapping.csv"
    if zones_file.exists():
        zone_bus_mapping = pd.read_csv(zones_file)
        print(f"  - Loaded {len(zone_bus_mapping)} zone-bus mappings")
    else:
        print(f"  - Zone bus mapping file not found: {zones_file}")
        zone_bus_mapping = pd.DataFrame()
    
    return plants_assignments, zone_bus_mapping

def load_clustered_buses(iso_code, output_dir='output'):
    """Load clustered buses for country"""
    print(f"Loading clustered buses for {iso_code}...")
    
    clustered_buses_file = SCRIPT_DIR / output_dir / iso_code / f"{iso_code}_clustered_buses.csv"
    if clustered_buses_file.exists():
        # Load clustered buses without expecting an index column
        buses_df = pd.read_csv(clustered_buses_file)
        print(f"  - Loaded {len(buses_df)} clustered buses for {iso_code}")
        
        # Ensure we have the required columns for visualization
        required_columns = ['bus_id', 'x', 'y']
        missing_columns = [col for col in required_columns if col not in buses_df.columns]
        
        if missing_columns:
            print(f"  - Warning: Missing required columns: {missing_columns}")
            print(f"  - Available columns: {list(buses_df.columns)}")
            return pd.DataFrame()
        
        # Rename coordinates to match expected format (x, y) if needed
        if 'x' in buses_df.columns and 'y' in buses_df.columns:
            # Already in correct format
            pass
        elif 'longitude' in buses_df.columns and 'latitude' in buses_df.columns:
            buses_df = buses_df.rename(columns={'longitude': 'x', 'latitude': 'y'})
        
        # Add country column for compatibility if not present
        if 'country' not in buses_df.columns:
            iso2_code = get_iso2_from_iso3(iso_code)
            buses_df['country'] = iso2_code
        
        return buses_df
    else:
        print(f"  - Clustered buses file not found: {clustered_buses_file}")
        return pd.DataFrame()



def load_clustered_lines(iso_code, output_dir='output'):
    """Load clustered lines for country"""
    print(f"Loading clustered lines for {iso_code}...")
    
    clustered_lines_file = SCRIPT_DIR / output_dir / iso_code / f"{iso_code}_clustered_lines.csv"
    if clustered_lines_file.exists():
        lines_df = pd.read_csv(clustered_lines_file)
        print(f"  - Loaded {len(lines_df)} clustered lines for {iso_code}")
        return lines_df
    else:
        print(f"  - Clustered lines file not found: {clustered_lines_file}")
        return pd.DataFrame()



def load_rezoning_zones(iso_code: str) -> gpd.GeoDataFrame:
    """
    Load renewable energy zoning zones from consolidated parquet files.
    
    Parameters:
    -----------
    iso_code : str
        ISO country code to filter zones
        
    Returns:
    --------
    gpd.GeoDataFrame
        Combined onshore and offshore zones for the specified country.
        Returns empty GeoDataFrame if no zones found or error occurs.
    """
    print(f"Loading REZoning zones for {iso_code}...")
    
    try:
        # Define file paths
        data_dir = Path("../data/REZoning")
        onshore_path = data_dir / "consolidated_onshore_zones_with_geometry.parquet"
        offshore_path = data_dir / "consolidated_offshore_zones_with_geometry.parquet"
        
        # Check if files exist
        if not onshore_path.exists():
            print(f"  - Warning: Onshore zones file not found: {onshore_path}")
            return gpd.GeoDataFrame()
        if not offshore_path.exists():
            print(f"  - Warning: Offshore zones file not found: {offshore_path}")
            return gpd.GeoDataFrame()
        
        # Load and filter zones
        zones_list = []
        
        # Load onshore zones
        print(f"  - Loading onshore zones from {onshore_path.name}")
        onshore_zones = gpd.read_parquet(onshore_path)
        onshore_filtered = onshore_zones[onshore_zones['ISO'] == iso_code].copy()
        if not onshore_filtered.empty:
            onshore_filtered['zone_type'] = 'onshore'  # Add zone type indicator
            zones_list.append(onshore_filtered)
            print(f"    Found {len(onshore_filtered)} onshore zones")
        
        # Load offshore zones
        print(f"  - Loading offshore zones from {offshore_path.name}")
        offshore_zones = gpd.read_parquet(offshore_path)
        offshore_filtered = offshore_zones[offshore_zones['ISO'] == iso_code].copy()
        if not offshore_filtered.empty:
            offshore_filtered['zone_type'] = 'offshore'  # Add zone type indicator
            zones_list.append(offshore_filtered)
            print(f"    Found {len(offshore_filtered)} offshore zones")
        
        # Combine zones if any were found
        if zones_list:
            zones_all = gpd.pd.concat(zones_list, ignore_index=True)
            print(f"  - Total zones loaded: {len(zones_all)}")
            return zones_all
        else:
            print(f"  - No RE zones found for {iso_code}")
            return gpd.GeoDataFrame()
            
    except Exception as e:
        print(f"  - Error loading REZoning zones: {e}")
        return gpd.GeoDataFrame()


def load_power_plants_metadata(iso_processor=None, iso_code=None):
    """Load original power plants metadata from GEM data using cache when available"""
    print("Loading power plants metadata...")
    
    # Use cached GEM data from iso_processor if available
    if iso_processor is not None and hasattr(iso_processor, 'main') and hasattr(iso_processor.main, 'df_gem'):
        print(f"  - Using cached GEM data from iso_processor")
        plants_df = iso_processor.main.df_gem.copy()
        print(f"  - Loaded metadata for {len(plants_df)} power plants from cache")
        return plants_df
    else:
        # Fallback to direct file loading
        print(f"  - Loading GEM data from Excel file...")
        gem_src = REPO_ROOT / 'data/existing_stock/Global-Integrated-Power-April-2025.xlsx'
        if not gem_src.exists():
            print(f"  - GEM data file not found: {gem_src}")
            return pd.DataFrame()

        try:
            plants_df = pd.read_excel(gem_src, sheet_name='Power facilities')
            
            if not plants_df.empty:
                print(f"  - Loaded metadata for {len(plants_df)} power plants from GEM 'Power facilities' sheet")
                return plants_df
            else:
                print("  - GEM sheet loaded but is empty")
                return pd.DataFrame()
        except Exception as e:
            print(f"  - Error loading GEM 'Power facilities' sheet: {e}")
            return pd.DataFrame()

def merge_power_plants_data(plants_assignments, plants_metadata):
    """Merge power plant assignments with metadata"""
    if plants_assignments.empty or plants_metadata.empty:
        return pd.DataFrame()
    
    # Check available columns to find the right merge key
    print(f"  - Power plants assignments columns: {list(plants_assignments.columns)}")
    print(f"  - Power plants metadata columns (first 10): {list(plants_metadata.columns)[:10]}")
    
    # Try different possible column names for GEM location ID
    possible_gem_columns = ['GEM location ID', 'Location ID', 'GEM ID', 'location_id', 'gem_location_id']
    gem_column = None
    
    for col in possible_gem_columns:
        if col in plants_metadata.columns:
            gem_column = col
            break
    
    if gem_column is None:
        print(f"  - Warning: Could not find GEM location ID column in metadata")
        print(f"  - Available metadata columns: {list(plants_metadata.columns)}")
        return pd.DataFrame()
    
    print(f"  - Using '{gem_column}' as merge key")
    
    merged_plants = plants_assignments.merge(
        plants_metadata,
        left_on='GEM location ID',
        right_on=gem_column,
        how='left'
    )
    
    print(f"  - Merged {len(merged_plants)} power plants with metadata")
    return merged_plants

def create_line_geometry_from_buses(bus0_coords, bus1_coords):
    """Create a simple straight line geometry between two bus coordinates"""
    return LineString([bus0_coords, bus1_coords])

def get_powerplant_color_and_icon(plant_type, status):
    """Get color and icon for power plant based on type and status"""
    # Technology-based colors
    type_colors = {
        'nuclear': '#8B0000',      # Dark red
        'coal': '#2F4F4F',         # Dark slate gray
        'oil/gas': '#FF8C00',      # Dark orange
        'gas': '#FFA500',          # Orange
        'oil': '#CD853F',          # Peru
        'hydro': '#4169E1',        # Royal blue
        'wind': '#87CEEB',         # Sky blue
        'solar': '#FFD700',        # Gold
        'biomass': '#228B22',      # Forest green
        'geothermal': '#A0522D',   # Sienna
        'waste': '#696969',        # Dim gray
        'unknown': '#808080'       # Gray
    }
    
    # Status-based opacity
    status_opacity = {
        'operating': 1.0,
        'construction': 0.8,
        'proposed': 0.6,
        'mothballed': 0.4,
        'retired': 0.2,
        'unknown': 0.5
    }
    
    # Get color (default to gray if type not found)
    color = type_colors.get(plant_type.lower() if isinstance(plant_type, str) else 'unknown', '#808080')
    
    # Get opacity (default to 0.5 if status not found)
    opacity = status_opacity.get(status.lower() if isinstance(status, str) else 'unknown', 0.5)
    
    # Get icon based on technology
    if 'nuclear' in str(plant_type).lower():
        icon = '☢️'
    elif 'coal' in str(plant_type).lower():
        icon = '🏭'
    elif any(fuel in str(plant_type).lower() for fuel in ['oil', 'gas']):
        icon = '🔥'
    elif 'hydro' in str(plant_type).lower():
        icon = '💧'
    elif 'wind' in str(plant_type).lower():
        icon = '💨'
    elif 'solar' in str(plant_type).lower():
        icon = '☀️'
    elif 'biomass' in str(plant_type).lower():
        icon = '🌱'
    elif 'geothermal' in str(plant_type).lower():
        icon = '🌋'
    else:
        icon = '⚡'
    
    return color, opacity, icon

def create_iso_interactive_map(buses_df, lines_df, plants_df, zones_df, zone_bus_mapping, iso_code, include_powerplants=True, powerplants_only=False, ppl_cap_filter=0.0):
    """Create interactive map for ISO country"""
    print(f"Creating interactive map for {iso_code}...")
    
    # Determine map center from buses
    if not buses_df.empty:
        center_lat = buses_df['y'].mean()
        center_lon = buses_df['x'].mean()
    else:
        # Default centers for some countries
        centers = {
            'CHE': [46.8, 8.2],   # Switzerland
            'DEU': [51.0, 10.0],  # Germany
            'FRA': [46.5, 2.0],   # France
            'ITA': [42.0, 12.5],  # Italy
        }
        center_lat, center_lon = centers.get(iso_code, [50.0, 10.0])
    
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=7, 
        # tiles='OpenStreetMap',
        tiles='cartodbpositron',
        prefer_canvas=True
    )
    
    # m = folium.Map(location=[lat, lon], zoom_start=6, tiles="cartodbpositron")
    
    # Create zone-to-buses mapping for hover interaction
    zone_bus_dict = {}
    if not zone_bus_mapping.empty:
        for _, mapping in zone_bus_mapping.iterrows():
            zone_id = mapping['grid_cell']
            bus_id = mapping['bus_id']
            if zone_id not in zone_bus_dict:
                zone_bus_dict[zone_id] = []
            zone_bus_dict[zone_id].append(bus_id)
    
    # Add rezoning zones
    if not zones_df.empty:
        print(f"  - Adding {len(zones_df)} rezoning zones...")
        for idx, zone in zones_df.iterrows():
            zone_id = zone.get('grid_cell', zone.get('id', idx))
            zone_buses = zone_bus_dict.get(zone_id, [])
            zone_type = zone.get('zone_type', 'onshore')  # Default to onshore if not specified
            
            # Define colors based on zone type
            if zone_type == 'offshore':
                fill_color = '#4169E1'  # Royal blue
                border_color = '#1E90FF'  # Dodger blue
                zone_icon = '🌊'
            else:  # onshore
                fill_color = '#98FB98'  # Pale green
                border_color = '#32CD32'  # Lime green
                zone_icon = '🌍'
            
            # Create zone layer
            zone_geojson = folium.GeoJson(
                zone.geometry,
                style_function=lambda x, fill_color=fill_color, border_color=border_color: {
                    'fillColor': fill_color,
                    'color': border_color,
                    'weight': 1,  # Thinner border
                    'fillOpacity': 0,  # Hollow cells - only show boundaries
                    'opacity': 1.0  # Make border fully opaque
                },
                popup=folium.Popup(
                    f"""
                    <div style='font-family: Arial; font-size: 12px; width: 250px;'>
                        <h4 style='margin: 5px 0; color: {border_color};'>{zone_icon} REZone {zone_id}</h4>
                        <div style='background-color: {fill_color}20; padding: 8px; margin: 5px 0; border-radius: 3px; border: 1px solid {border_color};'>
                            <b>Zone ID:</b> {zone_id}<br>
                            <b>Type:</b> {zone_type.title()}<br>
                            <b>ISO:</b> {zone.get('iso', 'N/A')}<br>
                            <b>Connected Buses:</b> {len(zone_buses)}<br>
                        </div>
                    </div>
                    """,
                    max_width=270
                ),
                tooltip=f"Zone {zone_id} - {len(zone_buses)} buses"
            )
            zone_geojson.add_to(m)
    
    # Add transmission lines (skip if powerplants_only mode)
    if not lines_df.empty and not powerplants_only:
        print(f"  - Adding {len(lines_df)} transmission lines...")
        
        bus_coords = {}
        if not buses_df.empty:
            for _, bus in buses_df.iterrows():
                bus_coords[bus['bus_id']] = (bus['x'], bus['y'])
        
        lines_added = 0
        for idx, line in lines_df.iterrows():
            try:
                # Always create straight line geometry from bus coordinates
                line_geometry = None
                
                if line.get('bus0') in bus_coords and line.get('bus1') in bus_coords:
                    bus0_coords = bus_coords[line['bus0']]
                    bus1_coords = bus_coords[line['bus1']]
                    line_geometry = create_line_geometry_from_buses(bus0_coords, bus1_coords)
                
                if line_geometry is not None:
                    s_nom = line.get('s_nom', 0)
                    if pd.isna(s_nom):
                        s_nom = 0
                    line_width = max(1.5, min(s_nom / 200, 8)) if s_nom > 0 else 2
                    
                    voltage = line.get('voltage', 0)
                    if voltage >= 380:
                        line_color = '#FF0000'
                    elif voltage >= 220:
                        line_color = '#FF8C00'
                    elif voltage >= 110:
                        line_color = '#4169E1'
                    else:
                        line_color = '#32CD32'
                    
                    if line_geometry.geom_type == 'LineString':
                        coords = [[point[1], point[0]] for point in line_geometry.coords]
                    elif line_geometry.geom_type == 'MultiLineString':
                        coords = []
                        for linestring in line_geometry.geoms:
                            coords.extend([[point[1], point[0]] for point in linestring.coords])
                    else:
                        continue
                    
                    folium.PolyLine(
                        locations=coords,
                        popup=folium.Popup(
                            f"""
                            <div style='font-family: Arial; font-size: 12px; width: 250px;'>
                                <h4 style='margin: 5px 0; color: #4169E1;'>⚡ Transmission Line</h4>
                                <b>From Bus:</b> {line.get('bus0', 'N/A')}<br>
                                <b>To Bus:</b> {line.get('bus1', 'N/A')}<br>
                                <b>Voltage:</b> {voltage} kV<br>
                                <b>Capacity (S_nom):</b> {s_nom:.1f} MVA<br>
                                <b>Length:</b> {line.get('length', 'N/A')} km<br>
                                <b>Type:</b> {line.get('type', 'N/A')}
                            </div>
                            """,
                            max_width=280
                        ),
                        color=line_color,
                        weight=line_width,
                        opacity=0.6,
                        tooltip=f"Line {line.get('bus0', 'N/A')} ↔ {line.get('bus1', 'N/A')} ({voltage}kV)"
                    ).add_to(m)
                    
                    lines_added += 1
                    
            except Exception as e:
                continue
        
        print(f"    Successfully added {lines_added} lines")
    
    # Add power plant connections and plants (only if include_powerplants is True)
    if not plants_df.empty and include_powerplants:
        print(f"  - Adding {len(plants_df)} power plants and connections...")
        
        # Get bus coordinates (even if buses_df is empty for powerplants_only mode)
        bus_coords = {}
        if not buses_df.empty:
            for _, bus in buses_df.iterrows():
                bus_coords[bus['bus_id']] = (bus['x'], bus['y'])
        elif powerplants_only:
            # In powerplants_only mode, we might not have bus coordinates
            # We'll skip the connection lines but still show power plants
            print("  - Note: No bus coordinates available in powerplants-only mode, skipping connection lines")
        
        plants_added = 0
        for _, plant in plants_df.iterrows():
            try:
                plant_lat = plant.get('Latitude')
                plant_lon = plant.get('Longitude')
                nearest_bus_id = plant.get('bus_id')
                
                plant_type = plant.get('Type', 'unknown')
                plant_status = plant.get('Status', 'unknown')
                color, opacity, icon = get_powerplant_color_and_icon(plant_type, plant_status)
                
                # Add connection line only if we have bus coordinates and not in powerplants_only mode
                if (all(pd.notna([plant_lat, plant_lon, nearest_bus_id])) and 
                    nearest_bus_id in bus_coords and not powerplants_only):
                    
                    bus_coords_tuple = bus_coords[nearest_bus_id]
                    bus_lat, bus_lon = bus_coords_tuple[1], bus_coords_tuple[0]  # x,y to lon,lat
                    
                    # Create connection line between power plant and bus
                    connection_coords = [[plant_lat, plant_lon], [bus_lat, bus_lon]]
                    
                    # Add connection line
                    folium.PolyLine(
                        locations=connection_coords,
                        color=color,
                        weight=4,
                        opacity=0.95,
                        dash_array='12, 6',
                        popup=folium.Popup(
                            f"""
                            <div style='font-family: Arial; font-size: 11px; width: 200px;'>
                                <h5 style='margin: 2px 0; color: {color};'>🔌 Power Plant Connection</h5>
                                <b>Plant:</b> {plant.get('Plant / Project name', 'N/A')}<br>
                                <b>Connected Bus:</b> {nearest_bus_id}<br>
                                <b>Distance:</b> {float(plant.get('distance_to_bus_km', 0)) if pd.notna(plant.get('distance_to_bus_km')) else 0:.1f} km
                            </div>
                            """,
                            max_width=220
                        ),
                        tooltip=f"Connection: {plant.get('Plant / Project name', 'N/A')[:20]}..."
                    ).add_to(m)
                
                # Add power plant marker (always add if we have coordinates)
                if all(pd.notna([plant_lat, plant_lon])):
                    # Add power plant marker
                    plant_name = plant.get('Plant / Project name', 'Unknown Plant')
                    
                    # Handle different possible capacity column names
                    capacity_columns = ['Capacity (MW)']
                    plant_capacity_raw = 0
                    for col in capacity_columns:
                        if col in plant.index:
                            plant_capacity_raw = plant.get(col, 0)
                            break
                    
                    # Convert capacity to float safely
                    try:
                        plant_capacity = float(plant_capacity_raw) if pd.notna(plant_capacity_raw) else 0
                    except (ValueError, TypeError):
                        plant_capacity = 0
                    
                    # Determine size based on capacity
                    if plant_capacity > 1000:
                        plant_size = 15
                    elif plant_capacity > 500:
                        plant_size = 12
                    elif plant_capacity > 100:
                        plant_size = 10
                    elif plant_capacity > 10:
                        plant_size = 8
                    else:
                        plant_size = 6
                    
                    # Make all icons except nuclear larger for better visibility
                    if 'nuclear' not in str(plant_type).lower():
                        plant_size = plant_size * 2
                    
                    # Create power plant popup
                    plant_popup_html = f"""
                    <div style='font-family: Arial; font-size: 12px; width: 280px;'>
                        <h4 style='margin: 5px 0; color: {color};'>{icon} {plant_name}</h4>
                        
                        <div style='background-color: #f5f5f5; padding: 8px; margin: 5px 0; border-radius: 3px; border: 2px solid {color};'>
                            <b>Technology:</b> {plant_type}<br>
                            <b>Status:</b> {plant_status}<br>
                            <b>Capacity:</b> {plant_capacity:.1f} MW<br>
                            <b>Country:</b> {plant.get('Country/area', 'N/A')}
                        </div>
                        
                        <div style='background-color: #f0f8ff; padding: 8px; margin: 5px 0; border-radius: 3px;'>
                            <b>📍 Location:</b><br>
                            <b>Coordinates:</b> ({plant_lat:.4f}, {plant_lon:.4f})<br>
                            <b>GEM ID:</b> {plant.get('GEM location ID', 'N/A')}
                        </div>
                        
                        <div style='background-color: #fff8dc; padding: 8px; margin: 5px 0; border-radius: 3px;'>
                            <b>🔌 Grid Connection:</b><br>
                            <b>Nearest Bus:</b> {nearest_bus_id}<br>
                            <b>Distance to Bus:</b> {float(plant.get('distance_to_bus_km', 0)) if pd.notna(plant.get('distance_to_bus_km')) else 0:.1f} km
                        </div>
                    </div>
                    """
                    
                    # Use DivIcon to create square markers
                    plant_marker = folium.Marker(
                        location=[plant_lat, plant_lon],
                        popup=folium.Popup(plant_popup_html, max_width=320),
                        tooltip=f"{icon} {plant_name} ({plant_type}, {plant_capacity:.0f}MW)",
                        icon=folium.DivIcon(
                            html=f"""
                            <div style='
                                background-color: {color}; 
                                border: 2px solid white; 
                                border-radius: 3px; 
                                width: {plant_size}px; 
                                height: {plant_size}px; 
                                opacity: {opacity};
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-size: {min(plant_size-2, 12)}px;
                                color: white;
                                font-weight: bold;
                                text-shadow: 1px 1px 1px rgba(0,0,0,0.5);
                            '>
                                {icon}
                            </div>
                            """,
                            icon_size=(plant_size, plant_size),
                            icon_anchor=(plant_size//2, plant_size//2)
                        )
                    )
                    plant_marker.add_to(m)
                    plants_added += 1
                
            except Exception as e:
                print(f"    Warning: Could not add power plant {plant.get('Plant / Project name', idx)}: {e}")
                continue
        
        print(f"    Successfully added {plants_added} power plants")
    
    # Add buses (skip if powerplants_only mode)
    if not buses_df.empty and not powerplants_only:
        print(f"  - Adding {len(buses_df)} buses...")
        
        for idx, bus in buses_df.iterrows():
            try:
                voltage = bus.get('voltage', 0)
                bus_id = bus.get('bus_id', 'N/A')
                
                # Determine bus size and color based on voltage level
                if voltage >= 380:
                    bus_size = 10
                    bus_color = '#FF0000'  # Red
                    border_color = '#8B0000'
                    fill_opacity = 0.8
                elif voltage >= 220:
                    bus_size = 8
                    bus_color = '#FF8C00'  # Orange
                    border_color = '#FF4500'
                    fill_opacity = 0.8
                elif voltage >= 110:
                    bus_size = 6
                    bus_color = '#4169E1'  # Blue
                    border_color = '#0000CD'
                    fill_opacity = 0.8
                else:
                    bus_size = 4
                    bus_color = '#32CD32'  # Green
                    border_color = '#228B22'
                    fill_opacity = 0.8
                
                # Create bus popup
                popup_html = f"""
                <div style='font-family: Arial; font-size: 12px; width: 250px;'>
                    <h4 style='margin: 5px 0; color: {bus_color};'>🏭 Bus {bus_id}</h4>
                    
                    <div style='background-color: #f0f0f0; padding: 8px; margin: 5px 0; border-radius: 3px;'>
                        <b>Bus ID:</b> {bus_id}<br>
                        <b>Voltage Level:</b> {voltage} kV<br>
                        <b>Country:</b> {bus.get('country', 'N/A')}<br>
                        <b>Symbol:</b> {bus.get('symbol', 'N/A')}
                    </div>
                    
                    <div style='background-color: #f0f8ff; padding: 8px; margin: 5px 0; border-radius: 3px;'>
                        <b>📍 Location:</b><br>
                        <b>Coordinates:</b> ({bus.get('x', 'N/A'):.4f}, {bus.get('y', 'N/A'):.4f})<br>
                        <b>Under Construction:</b> {bus.get('under_construction', 'N/A')}
                    </div>
                </div>
                """
                
                bus_marker = folium.CircleMarker(
                    location=[bus.get('y', 0), bus.get('x', 0)],
                    radius=bus_size,
                    popup=folium.Popup(popup_html, max_width=280),
                    color=border_color,
                    fillColor=bus_color,
                    fillOpacity=fill_opacity,
                    weight=2,
                    tooltip=f"Bus {bus_id} ({voltage}kV)"
                )
                bus_marker.add_to(m)
                
            except Exception as e:
                print(f"    Warning: Could not add bus {bus.get('bus_id', idx)}: {e}")
                continue
    
             # Add comprehensive legend
    capacity_filter_note = ""
    if ppl_cap_filter > 0.0:
        # Calculate the ratio for display in legend
        total_plants = len(plants_df) if not plants_df.empty else 0
        # Note: We can't easily get the pre-filter count here, so we'll show just the filter value
        capacity_filter_note = f"""
    <div style="margin: 8px 0; background-color: #fff3cd; padding: 8px; border-radius: 3px; border-left: 4px solid #ffc107;">
        <h5 style="margin: 4px 0; color: #856404;">🔍 Capacity Filter Active:</h5>
        <small>Showing only powerplants ≥ {ppl_cap_filter} MW</small><br>
        <small style="color: #856404; font-style: italic;">Filter applied to GEM metadata capacity field</small>
    </div>
    """
    
    legend_html = f'''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 300px; height: 500px; 
                background-color: white; border:2px solid #32CD32; z-index:9999; 
                font-size:11px; padding: 12px; border-radius: 5px; box-shadow: 0 0 15px rgba(50,205,50,0.3);
                overflow-y: auto;">
    <h4 style="margin-top: 0; color: #228B22;">🌍 {iso_code} Network</h4>
    {capacity_filter_note}
    <div style="margin: 8px 0;">
        <h5 style="margin: 4px 0; color: #666;">🏭 Voltage Levels:</h5>
        <i class="fa fa-circle" style="color:#FF0000"></i> 380+ kV<br>
        <i class="fa fa-circle" style="color:#FF8C00"></i> 220 kV<br>
        <i class="fa fa-circle" style="color:#4169E1"></i> 110 kV<br>
        <i class="fa fa-circle" style="color:#32CD32"></i> <110 kV<br>
        <small>Size ∝ Voltage Level</small>
    </div>
    
    <div style="margin: 8px 0;">
        <h5 style="margin: 4px 0; color: #666;">⚡ Transmission Lines:</h5>
        <i class="fa fa-minus" style="color:#FF0000; font-weight: bold;"></i> 380+ kV<br>
        <i class="fa fa-minus" style="color:#FF8C00; font-weight: bold;"></i> 220 kV<br>
        <i class="fa fa-minus" style="color:#4169E1; font-weight: bold;"></i> 110 kV<br>
        <small>Width ∝ Capacity (MVA)</small>
    </div>
    
    <div style="margin: 8px 0;">
        <h5 style="margin: 4px 0; color: #666;">🏭 Power Plants:</h5>
        <span style="background-color:#8B0000; color:white; padding:1px 3px; border-radius:2px;">☢️</span> Nuclear (normal)<br>
        <span style="background-color:#2F4F4F; color:white; padding:1px 3px; border-radius:2px;">🏭</span> Coal (2x size)<br>
        <span style="background-color:#FF8C00; color:white; padding:1px 3px; border-radius:2px;">🔥</span> Oil/Gas (2x size)<br>
        <span style="background-color:#4169E1; color:white; padding:1px 3px; border-radius:2px;">💧</span> Hydro (2x size)<br>
        <span style="background-color:#87CEEB; color:white; padding:1px 3px; border-radius:2px;">💨</span> Wind (2x size)<br>
        <span style="background-color:#FFD700; color:black; padding:1px 3px; border-radius:2px;">☀️</span> Solar (2x size)<br>
        <small>Square markers with tech icons</small>
    </div>
    
    <div style="margin: 8px 0;">
        <h5 style="margin: 4px 0; color: #666;">🔌 Connections:</h5>
        <i class="fa fa-minus" style="color:#666;"></i> Dashed lines to nearest bus<br>
        <small>Medium thickness (4px) for good visibility</small>
    </div>
    
    <div style="margin: 8px 0;">
        <h5 style="margin: 4px 0; color: #666;">🌍 REZones:</h5>
        <i class="fa fa-square" style="color:#98FB98;"></i> Renewable Energy Zones<br>
    </div>
    </div>
    '''
        # <small>Hover for bus count</small>
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add fullscreen and measure controls
    plugins.Fullscreen().add_to(m)
    plugins.MeasureControl(position='topleft').add_to(m)
    
    return m

def create_summary_statistics(buses_df, lines_df, plants_df, zones_df, iso_code, ppl_cap_filter=0.0):
    """Create comprehensive summary statistics"""
    print(f"\n=== {iso_code} NETWORK SUMMARY ===")
    
    # Bus statistics
    print(f"\n🏭 Substations/Buses: {len(buses_df)}")
    if not buses_df.empty:
        voltage_counts = buses_df['voltage'].value_counts().sort_index(ascending=False)
        print("   Voltage Levels:")
        for voltage, count in voltage_counts.items():
            print(f"     {voltage} kV: {count} buses")
    
    # Line statistics  
    print(f"\n⚡ Transmission Lines: {len(lines_df)}")
    if not lines_df.empty:
        voltage_counts = lines_df['voltage'].value_counts().sort_index(ascending=False)
        print("   Voltage Levels:")
        for voltage, count in voltage_counts.items():
            print(f"     {voltage} kV: {count} lines")
    
    # Power plant statistics
    print(f"\n🏭 Power Plants: {len(plants_df)}")
    if ppl_cap_filter > 0.0:
        print(f"   🔍 Capacity Filter: >= {ppl_cap_filter} MW")
        # Note: The ratio is shown in the main filtering message above
    
    if not plants_df.empty:
        tech_counts = plants_df['Type'].value_counts()
        print("   By Technology:")
        for tech, count in tech_counts.items():
            print(f"     {tech}: {count} plants")
        
        status_counts = plants_df['Status'].value_counts()
        print("   By Status:")
        for status, count in status_counts.items():
            print(f"     {status}: {count} plants")
        
        # Handle different possible capacity column names
        capacity_columns = ['Capacity (MW)']
        capacity_col = None
        for col in capacity_columns:
            if col in plants_df.columns:
                capacity_col = col
                break
        
        if capacity_col:
            total_capacity = plants_df[capacity_col].sum()
            print(f"   Total Capacity: {total_capacity:.0f} MW")
            if ppl_cap_filter > 0.0:
                avg_capacity = plants_df[capacity_col].mean()
                print(f"   Average Capacity: {avg_capacity:.1f} MW")
                min_capacity = plants_df[capacity_col].min()
                max_capacity = plants_df[capacity_col].max()
                print(f"   Capacity Range: {min_capacity:.1f} - {max_capacity:.1f} MW")
    
    # Zone statistics
    print(f"\n🌍 REZoning Zones: {len(zones_df)}")

def main():
    """Main function to create ISO network visualization"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Create ISO network visualization from consolidated data')
    parser.add_argument('iso_code', nargs='?', default='CHE', help='ISO country code (e.g., CHE, DEU, FRA)')
    parser.add_argument('--no-powerplants', action='store_true', help='Exclude power plants from visualization')
    parser.add_argument('--powerplants-only', action='store_true', help='Show only power plants (exclude network)')
    parser.add_argument('--ppl-cap-filter', type=float, default=100.0, help='Filter powerplants by minimum capacity in MW (default: 100.0)')
    parser.add_argument('--fresh-data-load', action='store_true',
                        help='Force loading GEM data from Excel file instead of using cached data')
    parser.add_argument('--no-svg', action='store_true',
                        help='Skip SVG generation (useful when enhanced SVG will be generated later)')
    parser.add_argument('--output-dir', default='output', 
                        help='Output directory containing the processed data (default: output)')
    
    args = parser.parse_args()
    ISO_CODE = args.iso_code.upper()
    include_powerplants = not args.no_powerplants
    powerplants_only = args.powerplants_only
    ppl_cap_filter = args.ppl_cap_filter
    use_cache = not args.fresh_data_load  # Default to using cache unless --fresh-data-load is specified
    output_dir = args.output_dir
    
    print(f"=== {ISO_CODE} NETWORK VISUALIZATION FROM CONSOLIDATED DATA ===")
    print(f"Usage: python visualize_iso_network.py [ISO_CODE] [--no-powerplants] [--powerplants-only] [--ppl-cap-filter MIN_CAPACITY_MW] [--fresh-data-load]")
    print(f"Options:")
    print(f"  --no-powerplants    Exclude power plants from visualization")
    print(f"  --powerplants-only  Show only power plants (exclude buses and lines)")
    print(f"  --ppl-cap-filter    Filter powerplants by minimum capacity in MW (default: 100.0)")
    print(f"  --fresh-data-load   Force loading GEM data from Excel file instead of using cached data")
    print(f"Current settings: Include power plants: {include_powerplants}, Power plants only: {powerplants_only}, Capacity filter: {ppl_cap_filter} MW")
    
    # Initialize iso_processor unless fresh data load is requested
    iso_processor = None
    if args.fresh_data_load:
        print("🔄 Fresh data load requested - will load GEM data from Excel file")
    else:
        print("🚀 Using cached data by default - use --fresh-data-load to force Excel loading")
    
    if use_cache:
        try:
            print("🔄 Initializing VerveStacks processor for cached data access...")
            import sys
            sys.path.append(str(REPO_ROOT))  # Add project root to path
            from verve_stacks_processor import VerveStacksProcessor
            
            # Create a minimal processor just for data access
            main_processor = VerveStacksProcessor(data_dir=str(REPO_ROOT / "data"),
                                                cache_dir=str(REPO_ROOT / "cache"), 
                                                force_reload=False)
            
            # Create a minimal iso_processor-like object with the required attributes
            class MinimalISOProcessor:
                def __init__(self, main_proc, iso_code):
                    self.main = main_proc
                    self.input_iso = iso_code
            
            # Get ISO2 code for processor
            iso2_code = get_iso2_from_iso3(ISO_CODE)
            iso_processor = MinimalISOProcessor(main_processor, iso2_code)
            print(f"✅ VerveStacks processor initialized for {ISO_CODE}")
        except Exception as e:
            print(f"⚠️  Could not initialize VerveStacks processor: {e}")
            print("   Falling back to direct file loading...")
            iso_processor = None
    
    print()
    
    try:
        # Load data based on options
        if include_powerplants:
            plants_assignments, zone_bus_mapping = load_consolidated_data(ISO_CODE, output_dir)
        else:
            # Still load zone bus mapping for valid bus determination, but not power plants
            _, zone_bus_mapping = load_consolidated_data(ISO_CODE, output_dir)
            plants_assignments = pd.DataFrame()
        
        if not powerplants_only:
            buses_df = load_clustered_buses(ISO_CODE, output_dir)
            lines_df = load_clustered_lines(ISO_CODE, output_dir)
            zones_df = load_rezoning_zones(ISO_CODE)
        else:
            buses_df = pd.DataFrame()
            lines_df = pd.DataFrame()
            zones_df = load_rezoning_zones(ISO_CODE)  # Still load zones for context
        
        if include_powerplants:
            plants_metadata = load_power_plants_metadata(iso_processor=iso_processor, iso_code=ISO_CODE)
            plants_df = merge_power_plants_data(plants_assignments, plants_metadata)
            
            # Apply capacity filtering if specified
            if ppl_cap_filter > 0.0:
                print(f"Applying capacity filter: showing only powerplants >= {ppl_cap_filter} MW")
                initial_count = len(plants_df)
                
                # Filter by capacity - handle different possible column names
                capacity_columns = ['Capacity (MW)']
                capacity_col = None
                for col in capacity_columns:
                    if col in plants_df.columns:
                        capacity_col = col
                        break
                
                if capacity_col:
                    # Convert capacity to numeric, handling any non-numeric values
                    plants_df[capacity_col] = pd.to_numeric(plants_df[capacity_col], errors='coerce')
                    plants_df = plants_df[plants_df[capacity_col] >= ppl_cap_filter]
                    filtered_count = len(plants_df)
                    print(f"  - Filtered from {initial_count} to {filtered_count} powerplants ({filtered_count}/{initial_count} = {filtered_count/initial_count*100:.1f}%)")
                else:
                    print(f"  - Warning: Could not find capacity column for filtering. Available columns: {list(plants_df.columns)}")
        else:
            plants_df = pd.DataFrame()
        
        # Create summary statistics
        create_summary_statistics(buses_df, lines_df, plants_df, zones_df, ISO_CODE, ppl_cap_filter)
        
        # Create interactive map
        map_viz = create_iso_interactive_map(
            buses_df, lines_df, plants_df, zones_df, zone_bus_mapping, ISO_CODE, 
            include_powerplants=include_powerplants, powerplants_only=powerplants_only, ppl_cap_filter=ppl_cap_filter
        )
        
        # Save map
        output_file = SCRIPT_DIR / output_dir / ISO_CODE / f"{ISO_CODE}_network_visualization.html"
        map_viz.save(str(output_file))
        print(f"\n✅ {ISO_CODE} network visualization saved to: {output_file}")
        
        # Generate SVG preview for README embedding (unless disabled)
        if not args.no_svg:
            try:
                print("📸 Generating SVG preview for README...")
                svg_file = SCRIPT_DIR / output_dir / ISO_CODE / f"{ISO_CODE}_network_visualization.svg"
                generate_svg_preview(buses_df, lines_df, plants_df, zones_df, str(svg_file))
                print(f"✅ SVG preview saved to: {svg_file}")
            except Exception as e:
                print(f"⚠️  Could not generate SVG preview: {e}")
        else:
            print("📸 Skipping SVG generation (--no-svg flag used)")
        print(f"🌐 Features:")
        print(f"   🏭 {len(buses_df)} network buses from OSM-Eur-prebuilt")
        print(f"   ⚡ {len(lines_df)} transmission lines with geometry")
        print(f"   🏭 {len(plants_df)} power plants with grid connections")
        if ppl_cap_filter > 0.0:
            # Get the total count before filtering for comparison
            if include_powerplants and not plants_assignments.empty:
                total_before_filter = len(plants_assignments)
                print(f"   🔍 Capacity filtered: >= {ppl_cap_filter} MW ({len(plants_df)}/{total_before_filter} = {len(plants_df)/total_before_filter*100:.1f}%)")
            else:
                print(f"   🔍 Capacity filtered: >= {ppl_cap_filter} MW")
        print(f"   🌍 {len(zones_df)} REZoning zones")
        print(f"   📊 Complete network topology from consolidated mappings")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()