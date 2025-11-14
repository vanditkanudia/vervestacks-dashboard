#!/usr/bin/env python3
"""
Country-Specific PyPSA Network Extraction with DBSCAN Bus Clustering
This script extracts country-specific network data, applies DBSCAN clustering to reduce bus count,
and maps REZoning zones to clustered buses. The clustering distance can be specified as a parameter.
"""

import argparse
import sys
import subprocess
import os
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')
from typing import Optional, List, Union
import requests
from shapely.geometry import MultiPolygon, Polygon, box, Point
from shapely.prepared import prep
import country_converter as coco
import unicodedata

cc = coco.CountryConverter()

# Constants from PyPSA-Eur
GEO_CRS = "EPSG:4326"
DISTANCE_CRS = "EPSG:3035"

# Resolve important directories regardless of current working directory
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

try:
    import pycountry
    PYCOUNTRY_AVAILABLE = True
except ImportError:
    PYCOUNTRY_AVAILABLE = False
    print("Warning: pycountry not available. Using fallback method for ISO3 codes.")

try:
    from sklearn.neighbors import BallTree
    from sklearn.cluster import DBSCAN
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Bus clustering and power plant assignment will be disabled.")

# Import renewable energy clustering functions
try:
    from re_clustering.re_clustering_1 import (
        load_and_reshape_atlite,
        extract_cell_profiles,
        process_grid_infrastructure as re_process_grid_infrastructure,
        smart_clustering_pipeline,
        visualize_and_export as re_visualize_and_export
    )
    RE_CLUSTERING_AVAILABLE = True
except ImportError:
    RE_CLUSTERING_AVAILABLE = False
    print("Warning: re_clustering functions not available. Renewable clustering will be disabled.")

from re_clustering.identify_disconnected_regions import identify_disconnected_regions

# =============================================================================
# INPUT FILE PATHS CONFIGURATION
# =============================================================================
# OSM Data Sources
OSM_DATA_SOURCES = {
    'eur': '../data/OSM-Eur-prebuilt',
    'kan': '../data/OSM-kan-prebuilt'
}

# Base file paths (non-OSM data)
BASE_INPUT_FILES = {
    # Atlite renewable energy profiles - handle both main project and 1_grids directory execution
    'atlite_profiles': 'data/hourly_profiles/atlite_grid_cell_2013.parquet' if Path('data/hourly_profiles/atlite_grid_cell_2013.parquet').exists() else '../data/hourly_profiles/atlite_grid_cell_2013.parquet',
    # 'atlite_profiles': 'data/hourly_profiles/atlite_grid_cell_2013_ITA_only.parquet' if Path('data/hourly_profiles/atlite_grid_cell_2013_ITA_only.parquet').exists() else '../data/hourly_profiles/atlite_grid_cell_2013_ITA_only.parquet',
    
    # REZoning data (consolidated parquet file) - handle both main project and 1_grids directory execution
    'zones_parquet_onshore': 'data/REZoning/consolidated_onshore_zones_with_geometry.parquet' if Path('data/REZoning/consolidated_onshore_zones_with_geometry.parquet').exists() else '../data/REZoning/consolidated_onshore_zones_with_geometry.parquet',
    'zones_parquet_offshore': 'data/REZoning/consolidated_offshore_zones_with_geometry.parquet' if Path('data/REZoning/consolidated_offshore_zones_with_geometry.parquet').exists() else '../data/REZoning/consolidated_offshore_zones_with_geometry.parquet',
    
    # Power plant data (GEM)
    'power_plants': '../data/existing_stock/Global-Integrated-Power-April-2025.xlsx',
    
    # Cities data for load share estimation
    'worldcities': '../data/country_data/worldcities.csv',
    
    # Country boundaries for Voronoi clipping
    'countries': '../data/country_data/nuts/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp',
    
    # Natural Earth data for visualization background
    'naturalearth_countries': '../data/country_data/naturalearth/ne_10m_admin_0_countries_lakes',

    'nuts_geojson': '../data/country_data/nuts/NUTS_RG_01M_2021_4326_LEVL_3.geojson',

    # GDP data from JRC ARDECO database
    'gdp_data': '../data/country_data/jrc-ardeco/ARDECO-SUVGDP.2021.table.csv',
  
    # Population data from JRC ARDECO database  
    'pop_data': '../data/country_data/jrc-ardeco/ARDECO-SNPTD.2021.table.csv',
    
}

def get_input_files(data_source):
    """Get input file paths for a specific OSM data source"""
    if data_source not in OSM_DATA_SOURCES:
        raise ValueError(f"Unknown data source: {data_source}. Available sources: {list(OSM_DATA_SOURCES.keys())}")
    
    base_path = OSM_DATA_SOURCES[data_source]
    input_files = BASE_INPUT_FILES.copy()
    input_files.update({
        'buses': f'{base_path}/buses.csv',
        'lines': f'{base_path}/lines.csv',
        'links': f'{base_path}/links.csv',
    })
    return input_files

def detect_available_data_sources(country_code):
    """Detect which OSM data sources contain the requested country"""
    available_sources = []
    
    for source_name, source_path in OSM_DATA_SOURCES.items():
        buses_file = f'{source_path}/buses.csv'
        try:
            if os.path.exists(buses_file):
                # Load buses data to check country availability
                buses_df = pd.read_csv(buses_file)
                if 'country' in buses_df.columns:
                    country_buses = buses_df[buses_df['country'] == country_code]
                    if not country_buses.empty:
                        available_sources.append(source_name)
                        print(f"  + Country '{country_code}' found in {source_name} dataset ({len(country_buses)} buses)")
                    else:
                        print(f"  - Country '{country_code}' not found in {source_name} dataset")
                else:
                    print(f"  ! No 'country' column found in {source_name} dataset")
            else:
                print(f"  - Buses file not found: {buses_file}")
        except Exception as e:
            print(f"  - Error checking {source_name} dataset: {e}")
    
    # Cities data is available but only when explicitly requested
    # available_sources.append('cit')  # Removed from automatic detection
    
    return available_sources

# GEM Excel sheet name
GEM_SHEET_NAME = "Power facilities"
# =============================================================================

def get_iso3_code(iso2_code):
    """
    Convert ISO2 country code to ISO3 using pycountry library.
    Falls back to pattern matching for exceptional cases.
    """
    if PYCOUNTRY_AVAILABLE:
        try:
            # First try direct lookup
            country = pycountry.countries.get(alpha_2=iso2_code.upper())
            if country:
                return country.alpha_3
        except:
            pass
    
    # Fallback: Manual exceptions for countries that need special handling
    exceptions = {
        'GB': 'GBR',  # United Kingdom  
        'GR': 'GRC',  # Greece
        'HR': 'HRV',  # Croatia
        'SI': 'SVN',  # Slovenia
        'EE': 'EST',  # Estonia
        'LV': 'LVA',  # Latvia
        'LT': 'LTU',  # Lithuania
        'FI': 'FIN',  # Finland
        'SE': 'SWE',  # Sweden
        'NO': 'NOR',  # Norway
        'DK': 'DNK',  # Denmark
        'IE': 'IRL',  # Ireland
        'PT': 'PRT',  # Portugal
        'CZ': 'CZE',  # Czech Republic
        'SK': 'SVK',  # Slovakia
        'HU': 'HUN',  # Hungary
        'RO': 'ROU',  # Romania
        'BG': 'BGR',  # Bulgaria
        'XK': 'XKX',  # Kosovo (unofficial)
    }
    
    if iso2_code.upper() in exceptions:
        return exceptions[iso2_code.upper()]
    
    # Final fallback: Standard pattern (add 'E' to ISO2)
    # Works for: CH->CHE, DE->DEU, FR->FRA, IT->ITA, ES->ESP, NL->NLD, BE->BEL, AT->AUT, PL->POL
    return iso2_code.upper() + 'E'

def load_cities_for_country(country_code: str, mainland_bounds: dict = None):
    """Load cities data for country as spatial anchors"""
    try:
        # Handle both main project and 1_grids directory execution
        cities_file = "data/country_data/worldcities.csv" if Path("data/country_data/worldcities.csv").exists() else "../data/country_data/worldcities.csv"
        cities_df = pd.read_csv(cities_file)
        
        # Get ISO3 code for filtering
        iso3_code = get_iso3_code(country_code)
        
        # Filter by country (try both iso2 and iso3)
        country_cities = cities_df[
            (cities_df['iso2'] == country_code) | 
            (cities_df['iso3'] == iso3_code)
        ]
        
        if country_cities.empty:
            print(f"  - No cities found for {country_code} ({iso3_code})")
            return pd.DataFrame()
        
        # Select cities that account for 75% of total population
        cities_with_pop = country_cities.dropna(subset=['population'])
        
        if cities_with_pop.empty:
            # Fallback: take any cities without population filter
            major_cities = country_cities.head(min(10, len(country_cities)))
            print(f"  + No population data available, using first {len(major_cities)} cities")
        else:
            # Sort cities by population (descending) and calculate cumulative percentage
            cities_sorted = cities_with_pop.sort_values('population', ascending=False)
            total_population = cities_sorted['population'].sum()
            
            if total_population > 0:
                cities_sorted['cumulative_pop'] = cities_sorted['population'].cumsum()
                cities_sorted['cumulative_pct'] = cities_sorted['cumulative_pop'] / total_population
                
                # Select cities that account for 75% of population
                major_cities = cities_sorted[cities_sorted['cumulative_pct'] <= 0.75]
                
                # Ensure we have at least a few cities (minimum 3) but NO maximum limit
                if len(major_cities) < 3:
                    major_cities = cities_sorted.head(min(3, len(cities_sorted)))
                
                coverage_pct = major_cities['population'].sum() / total_population * 100
                print(f"  + Selected {len(major_cities)} cities covering {coverage_pct:.1f}% of population")
            else:
                # Fallback if population data is invalid
                major_cities = cities_sorted.head(min(10, len(cities_sorted)))
                print(f"  + Invalid population data, using top {len(major_cities)} cities")
        
        print(f"  + Final selection: {len(major_cities)} cities for {country_code}")
        
        # Create geometry column for compatibility
        major_cities = major_cities.copy()
        major_cities['geometry'] = gpd.points_from_xy(major_cities['lng'], major_cities['lat'])

        if mainland_bounds is not None:
            major_cities = major_cities[
                (major_cities['lng'] >= mainland_bounds['lon_min']) &
                (major_cities['lng'] <= mainland_bounds['lon_max']) &
                (major_cities['lat'] >= mainland_bounds['lat_min']) &
                (major_cities['lat'] <= mainland_bounds['lat_max'])
            ]
        
        return major_cities
        
    except Exception as e:
        print(f"  - Error loading cities for {country_code}: {e}")
        return pd.DataFrame()

def load_network_components(country_code: str, data_source: str = 'eur', mainland_bounds: dict = None):
    """Load and filter network components for the specified country from the specified data source"""
    print(f"Loading network components for country: {country_code} from {data_source} dataset")
    
    # Handle cities data source
    if data_source == 'cit':
        cities_df = load_cities_for_country(country_code, mainland_bounds)
        if cities_df.empty:
            return {'buses': pd.DataFrame(), 'lines': pd.DataFrame()}
        
        # Convert cities to "buses" format
        cities_buses = pd.DataFrame({
            'bus_id': cities_df['city'],
            'x': cities_df['lng'],
            'y': cities_df['lat'],
            'voltage': cities_df['population'].fillna(50000),  # Use population as "voltage", default 50k
            'country': country_code
        })
        
        print(f"  + Converted {len(cities_buses)} cities to bus format")
        
        return {
            'buses': cities_buses,
            'lines': pd.DataFrame()  # No transmission lines for cities
        }
    
    # Get input files for the specified data source (existing OSM logic)
    input_files = get_input_files(data_source)
    
    # Essential columns for lines and links (used for connectivity analysis and clustering)
    lines_essential_columns = ['bus0', 'bus1', 'length', 'r', 'x', 'g', 'b', 's_nom', 'p_nom', 'type','voltage', 'geometry', 'HVDC']
    
    components = {}
    
    # Load buses
    try:
        df = pd.read_csv(input_files['buses'])
        if 'country' in df.columns:
            country_buses = df[df['country'] == country_code]
        else:
            country_buses = df[df['bus_id'].astype(str).str.contains(country_code, case=False, na=False)]

        if country_buses.empty:
            # Attempt to hint available countries
            try:
                df = pd.read_csv(input_files['buses'])
                available_countries = df['country'].unique() if 'country' in df.columns else df['bus_id'].astype(str).str[:2].unique()
            except Exception:
                available_countries = []
            raise ValueError(f"No buses found for country '{country_code}' in {data_source} dataset. Available countries: {available_countries}")

        components['buses'] = country_buses
        print(f"  - Loaded {len(country_buses)} buses from {data_source} dataset")

    except Exception as e:
        print(f"  - Error loading buses from {data_source} dataset: {e}")
        components['buses'] = pd.DataFrame()
    
    # Load lines (used for connectivity analysis and later network topology updates)
    try:
        file_path = input_files['lines']
        if Path(file_path).exists():
            # First, check what columns are available
            df_sample = pd.read_csv(file_path, nrows=1)
            available_columns = df_sample.columns.tolist()
            
            # Filter essential columns to only those that exist
            existing_columns = [col for col in lines_essential_columns if col in available_columns]
            
            if len(existing_columns) >= 2:  # Need at least bus0 and bus1
                # Load only existing essential columns
                df_lines = pd.read_csv(file_path, usecols=existing_columns)
                
                # Filter for country-specific lines
                if 'bus0' in df_lines.columns and 'bus1' in df_lines.columns:
                    # Get all bus IDs for this country
                    country_bus_ids = set(country_buses['bus_id'].astype(str))
                    
                    # Filter lines where both buses are in the country
                    df_filtered = df_lines[
                        df_lines['bus0'].astype(str).isin(country_bus_ids) & 
                        df_lines['bus1'].astype(str).isin(country_bus_ids)
                    ]
                    
                    components['lines'] = df_filtered
                    print(f"  - Loaded {len(df_filtered)} lines from {data_source} dataset")
                else:
                    print(f"  - Skipping lines (no bus connection columns)")
                    components['lines'] = pd.DataFrame()
            else:
                print(f"  - Skipping lines (insufficient columns: {existing_columns})")
                components['lines'] = pd.DataFrame()
        else:
            print(f"  - lines.csv not found in {data_source} dataset")
            components['lines'] = pd.DataFrame()
    except Exception as e:
        print(f"  - Error loading lines from {data_source} dataset: {e}")
        components['lines'] = pd.DataFrame()
    
    # Load links (HVDC transmission lines) and combine with lines
    try:
        file_path = input_files['links']
        if Path(file_path).exists():
            # First, check what columns are available
            df_sample = pd.read_csv(file_path, nrows=1)
            available_columns = df_sample.columns.tolist()
            
            # Filter essential columns to only those that exist
            existing_columns = [col for col in lines_essential_columns if col in available_columns]
            
            if len(existing_columns) >= 2:  # Need at least bus0 and bus1
                # Load only existing essential columns
                df_links = pd.read_csv(file_path, usecols=existing_columns)
                
                # Filter for country-specific links
                if 'bus0' in df_links.columns and 'bus1' in df_links.columns:
                    # Get all bus IDs for this country
                    country_bus_ids = set(country_buses['bus_id'].astype(str))
                    
                    # Filter links where both buses are in the country
                    df_links_filtered = df_links[
                        df_links['bus0'].astype(str).isin(country_bus_ids) & 
                        df_links['bus1'].astype(str).isin(country_bus_ids)
                    ]
                    
                    if not df_links_filtered.empty:
                        # Rename link_id to line_id if it exists
                        if 'link_id' in df_links_filtered.columns:
                            df_links_filtered = df_links_filtered.rename(columns={
                                'link_id': 'line_id'
                            })
                        if 'p_nom' in df_links_filtered.columns:
                            df_links_filtered = df_links_filtered.rename(columns={
                                'p_nom': 's_nom'
                            })
                        # Add HVDC flag (True for all links)
                        df_links_filtered['HVDC'] = True
                        df_links_filtered['type'] = 'HVDC link'
                        
                        # Add HVDC flag to existing lines (False for all lines)
                        if not components['lines'].empty:
                            components['lines']['HVDC'] = False
                        
                        # Combine lines and links
                        components['lines'] = pd.concat([components['lines'], df_links_filtered], ignore_index=True)
                        print(f"  - Loaded {len(df_links_filtered)} links from {data_source} dataset")
                    else:
                        print(f"  - No links found for country {country_code} in {data_source} dataset")
                else:
                    print(f"  - Skipping links (no bus connection columns)")
            else:
                print(f"  - Skipping links (insufficient columns: {existing_columns})")
        else:
            print(f"  - links.csv not found in {data_source} dataset")
    except Exception as e:
        print(f"  - Error loading links from {data_source} dataset: {e}")
    
    return components

def load_zones_for_country(country_code: str, filter_type: str = 'onshore'):
    """Load and filter zones for the specified country from consolidated parquet file"""
    print(f"Loading zones for country: {country_code}")
    
    try:

        zones_src = None
        if filter_type == 'onshore':
            zones_src = Path(BASE_INPUT_FILES['zones_parquet_onshore'])
        elif filter_type == 'offshore':
            zones_src = Path(BASE_INPUT_FILES['zones_parquet_offshore'])
        else:
            print(f"  - Invalid filter type: {filter_type}")
            return gpd.GeoDataFrame()

        # zones_src = Path(BASE_INPUT_FILES['zones_parquet'])
        gdf = gpd.read_parquet(zones_src)
        print(f"  - Loaded {len(gdf)} {filter_type} zones from consolidated file")
        
        # Get ISO3 code for filtering
        if len(country_code) == 2:
            iso3_code = get_iso3_code(country_code)
        else:
            iso3_code = country_code
        print(f"  - Using ISO3 code '{iso3_code}' for filtering")
        
        # Filter zones by country ISO
        country_zones = gdf[gdf['ISO'] == iso3_code]

        
        print(f"  - Found {len(country_zones)} {filter_type} zones for {iso3_code}")
        if not country_zones.empty and 'id' in country_zones.columns:
            try:
                print(f"  - Zone IDs range from {country_zones['id'].min()} to {country_zones['id'].max()}")
            except Exception:
                pass
        return country_zones
        
    except Exception as e:
        print(f"  - Error loading zones: {e}")
        return gpd.GeoDataFrame()

# def calculate_weighted_cluster_profiles(clusters, profiles, iso3_code):
#     """
#     Calculate weighted cluster profiles based on REZoning generation potential data
    
#     Args:
#         clusters: Array of cluster assignments for each cell
#         profiles: Dictionary containing wind/solar profiles and cell info
#         rezoning_data: Dictionary containing REZoning data (solar, wind, windoff)
#         iso3_code: ISO3 country code
    
#     Returns:
#         dict: Weighted cluster profiles with generation potential weights
#     """
#     print("Calculating weighted cluster profiles based on generation potential...")
    
 
#     # Create mapping from grid_cell to capacity (MW)
#     generation_potential = {}
    
#     # Map solar generation potential
#     if not df_solar_country.empty and 'grid_cell' in df_solar_country.columns:
#         for _, row in df_solar_country.iterrows():
#             cell_id = row['grid_cell']
#             if 'Installed Capacity Potential (MW)' in row:
#                 capacity_mw = row['Installed Capacity Potential (MW)']
#                 generation_potential[f"{cell_id}_solar"] = capacity_mw  # Use capacity only (avoid double counting CF)
#             else:
#                 generation_potential[f"{cell_id}_solar"] = 0
    
#     # Calculate weighted cluster profiles
#     weighted_cluster_profiles = {}
#     unique_clusters = np.unique(clusters)
    
#     for cluster_id in unique_clusters:
#         mask = clusters == cluster_id
#         cluster_cells = profiles['cells'][mask]
        
#         # Calculate weights based on generation potential
#         solar_weights = []
#         wind_weights = []
        
#         for cell in cluster_cells:
#             solar_key = f"{cell}_solar"
#             wind_key = f"{cell}_wind"
            
#             solar_weight = generation_potential.get(solar_key, 1.0)  # Default weight of 1.0
#             wind_weight = generation_potential.get(wind_key, 1.0)    # Default weight of 1.0
            
#             solar_weights.append(solar_weight)
#             wind_weights.append(wind_weight)
        
#         solar_weights = np.array(solar_weights)
#         wind_weights = np.array(wind_weights)
        
#         # Normalize weights
#         if solar_weights.sum() > 0:
#             solar_weights = solar_weights / solar_weights.sum()
#         else:
#             solar_weights = np.ones_like(solar_weights) / len(solar_weights)
            
#         if wind_weights.sum() > 0:
#             wind_weights = wind_weights / wind_weights.sum()
#         else:
#             wind_weights = np.ones_like(wind_weights) / len(wind_weights)
        
#         # Calculate weighted profiles
#         if profiles['wind'] is not None and len(profiles['wind']) > 0:
#             weighted_wind_profile = np.average(profiles['wind'][mask], axis=0, weights=wind_weights)
#         else:
#             weighted_wind_profile = np.zeros(8760)
            
#         if profiles['solar'] is not None and len(profiles['solar']) > 0:
#             weighted_solar_profile = np.average(profiles['solar'][mask], axis=0, weights=solar_weights)
#         else:
#             weighted_solar_profile = np.zeros(8760)
        
#         # Calculate total capacity for this cluster
#         total_solar_capacity = sum(generation_potential.get(f"{cell}_solar", 0) for cell in cluster_cells)
#         total_wind_capacity = sum(generation_potential.get(f"{cell}_wind", 0) for cell in cluster_cells)
        
#         weighted_cluster_profiles[cluster_id] = {
#             'wind_profile': weighted_wind_profile,
#             'solar_profile': weighted_solar_profile,
#             'n_cells': mask.sum(),
#             'centroid_lat': profiles['coords'][mask, 0].mean(),
#             'centroid_lon': profiles['coords'][mask, 1].mean(),
#             'total_solar_capacity_mw': total_solar_capacity,
#             'total_wind_capacity_mw': total_wind_capacity,
#             'avg_solar_weight': solar_weights.mean(),
#             'avg_wind_weight': wind_weights.mean()
#         }
    
#     print(f"  - Calculated weighted profiles for {len(weighted_cluster_profiles)} clusters")
#     return weighted_cluster_profiles

def calculate_weighted_cluster_profiles_2(clusters, profiles, technology):
    """
    Calculate capacity-weighted cluster profiles for any technology (using existing mw_wt data)
    
    Args:
        clusters: Array of cluster assignments for each cell (from technology-specific clustering)
        profiles: Dictionary containing profiles, cells, coords, and mw_wt capacity data
        technology: Technology name (e.g., 'solar', 'wind_onshore', 'wind_offshore')
    
    Returns:
        dict: Weighted cluster profiles for the specified technology only
    """
    print(f"Calculating weighted cluster profiles for {technology}...")
    
    # Generic technology mapping
    tech_map = {
        'solar': {'profile_key': 'solar', 'suffix': 'solar', 'capacity_col': 'solar_capacity_mw'},
        'wind_onshore': {'profile_key': 'wind', 'suffix': 'wind', 'capacity_col': 'wind_capacity_mw'},
        'wind_offshore': {'profile_key': 'offwind', 'suffix': 'offwind', 'capacity_col': 'offwind_capacity_mw'}
    }
    
    if technology not in tech_map:
        raise ValueError(f"Unsupported technology: {technology}. Supported: {list(tech_map.keys())}")
    
    profile_key = tech_map[technology]['profile_key']
    tech_suffix = tech_map[technology]['suffix']
    capacity_col = tech_map[technology]['capacity_col']
    
    # Use existing mw_wt data for capacity weights
    mw_wt = profiles.get('mw_wt', pd.DataFrame())
    
    # Check if 'cells' key exists
    if 'cells' not in profiles:
        raise KeyError("'cells' key not found in profiles dictionary")
    
    # Check if we have the expected profile data structure
    if 're_profile_df' in profiles:
        # Extract the appropriate technology profile from re_profile_df
        re_profile_df = profiles['re_profile_df']
        
        # For solar technology, the re_profile_df should contain the solar profiles
        # The data is already in the right format - each row is a cell, columns are hours
        if technology == 'solar':
            # For solar profiles, use the entire re_profile_df as it contains solar data
            profile_data = re_profile_df.values  # Shape should be (n_cells, 8760)
        elif technology == 'wind_onshore':
            # For wind profiles, use the entire re_profile_df as it contains wind data  
            profile_data = re_profile_df.values  # Shape should be (n_cells, 8760)
        elif technology == 'wind_offshore':
            # For offshore wind profiles, use the entire re_profile_df as it contains offwind data
            profile_data = re_profile_df.values  # Shape should be (n_cells, 8760)
        else:
            raise KeyError(f"Profile data for {technology} not found")
    elif profile_key in profiles:
        profile_data = profiles[profile_key]
    else:
        raise KeyError(f"Profile data not found for {technology}")
    
    # Calculate weighted cluster profiles
    weighted_cluster_profiles = {}
    unique_clusters = np.unique(clusters)
    
    for cluster_id in unique_clusters:
        mask = clusters == cluster_id
        cluster_cells = profiles['cells'][mask]
        
        # Get capacity weights from mw_wt DataFrame
        tech_weights = []
        total_tech_capacity = 0
        
        for cell in cluster_cells:
            if not mw_wt.empty and cell in mw_wt['grid_cell'].values:
                cell_row = mw_wt[mw_wt['grid_cell'] == cell]
                if not cell_row.empty and capacity_col in cell_row.columns:
                    capacity = cell_row[capacity_col].iloc[0]
                else:
                    capacity = 1.0  # Default weight
            else:
                capacity = 1.0
            
            tech_weights.append(capacity)
            total_tech_capacity += capacity
        
        tech_weights = np.array(tech_weights)
        
        # Normalize weights
        if tech_weights.sum() > 0:
            tech_weights = tech_weights / tech_weights.sum()
        else:
            tech_weights = np.ones_like(tech_weights) / len(tech_weights)
        
        # Calculate weighted profile for the specific technology
        if profile_data is not None and len(profile_data) > 0:
            weighted_tech_profile = np.average(profile_data[mask], axis=0, weights=tech_weights)
        else:
            weighted_tech_profile = np.zeros(8760)
        
        weighted_cluster_profiles[cluster_id] = {
            f'{tech_suffix}_profile': weighted_tech_profile,
            'n_cells': mask.sum(),
            'centroid_lat': profiles['coords'][mask, 0].mean(),
            'centroid_lon': profiles['coords'][mask, 1].mean(),
            f'total_{tech_suffix}_capacity_mw': total_tech_capacity,
            f'avg_{tech_suffix}_weight': tech_weights.mean()
        }
    
    print(f"  - Calculated {technology} weighted profiles for {len(weighted_cluster_profiles)} clusters")
    return weighted_cluster_profiles

def export_technology_timeseries(weighted_profiles, technology, iso3_code, output_dir):
    """
    Export technology-specific timeseries in atlite format
    
    Args:
        weighted_profiles: Dict from calculate_weighted_cluster_profiles_2
        technology: 'solar' or 'wind_onshore'
        iso3_code: Country code
        output_dir: Output directory path
    """
    tech_suffix = 'solar' if technology == 'solar' else 'wind'
    profile_key = f'{tech_suffix}_profile'
    
    print(f"Exporting {technology} timeseries...")
    
    timeseries_data = []
    
    for cluster_id, data in weighted_profiles.items():
        cluster_name = cluster_id  # e.g., 'cluster_1'
        tech_profile = data[profile_key]  # 8760 values
        
        # Calculate annual sum for commodity fractions
        annual_sum = sum(tech_profile)
        
        # Create hourly records matching atlite format exactly
        for hour in range(8760):
            # Convert hour index to month, day, hour (assuming 2013 leap year)
            from datetime import datetime, timedelta
            start_date = datetime(2013, 1, 1)
            current_date = start_date + timedelta(hours=hour)
            
            # Get hourly capacity factor
            tech_cf = tech_profile[hour]
            
            # Calculate commodity fraction (fraction of annual generation at this hour)
            com_fr = tech_cf / annual_sum if annual_sum > 0 else 0.0
            
            # Create record
            record = {
                'grid_cell': cluster_name,
                'month': current_date.month,
                'day': current_date.day,
                'hour': current_date.hour,
                f'{tech_suffix}_capacity_factor': tech_cf,
                f'com_fr_{tech_suffix}': com_fr
            }
            
            timeseries_data.append(record)
    
    # Convert to DataFrame and save
    timeseries_df = pd.DataFrame(timeseries_data)
    
    # Save as CSV
    csv_file = f'{output_dir}/{iso3_code}_{tech_suffix}_cluster_atlite_timeseries.csv'
    timeseries_df.to_csv(csv_file, index=False)
    print(f"  - Saved {technology} timeseries: {csv_file}")
    
    # Save as Parquet for efficiency
    parquet_file = f'{output_dir}/{iso3_code}_{tech_suffix}_cluster_atlite_timeseries.parquet'
    timeseries_df.to_parquet(parquet_file, index=False)
    print(f"  - Saved {technology} timeseries: {parquet_file}")
    
    return timeseries_df

def export_cluster_timeseries(weighted_profiles, technology, output_path):
    """
    Export cluster timeseries data in atlite format for any technology
    
    Args:
        weighted_profiles: Dict from calculate_weighted_cluster_profiles_2
        technology: 'solar', 'wind_onshore', or 'wind_offshore'
        output_path: Output directory path (pathlib.Path object)
    """
    from datetime import datetime, timedelta
    import pandas as pd
    
    # Technology mapping for profile keys and file naming
    tech_map = {
        'solar': {'profile_key': 'solar_profile', 'suffix': 'solar', 'com_fr_key': 'com_fr_solar', 'cf_key': 'solar_capacity_factor'},
        'wind_onshore': {'profile_key': 'wind_profile', 'suffix': 'wind', 'com_fr_key': 'com_fr_wind', 'cf_key': 'wind_capacity_factor'},
        'wind_offshore': {'profile_key': 'offwind_profile', 'suffix': 'offwind', 'com_fr_key': 'com_fr_offwind', 'cf_key': 'offwind_capacity_factor'}
    }
    
    if technology not in tech_map:
        raise ValueError(f"Unsupported technology: {technology}. Supported: {list(tech_map.keys())}")
    
    tech_info = tech_map[technology]
    profile_key = tech_info['profile_key']
    suffix = tech_info['suffix']
    com_fr_key = tech_info['com_fr_key']
    cf_key = tech_info['cf_key']
    
    print(f"Exporting {technology} cluster timeseries...")
    
    cluster_timeseries_data = []
    
    for cluster_id, data in weighted_profiles.items():
        cluster_name = cluster_id  # e.g., 'cluster_1'
        tech_profile = data[profile_key]  # 8760 values
        
        # Calculate annual sums for commodity fractions
        annual_sum = sum(tech_profile)  # Sum of all 8760 CF values
                        
        # Create hourly records matching atlite format exactly
        for hour in range(8760):
            # Convert hour index to month, day, hour (assuming 2013 leap year)
            start_date = datetime(2013, 1, 1)
            current_date = start_date + timedelta(hours=hour)
            
            # Get hourly capacity factors
            cf = tech_profile[hour]
            
            # Calculate commodity fractions (fraction of annual generation at this hour)
            com_fr = cf / annual_sum if annual_sum > 0 else 0.0
            
            cluster_timeseries_data.append({
                'cluster_id': cluster_name,
                'month': current_date.month,
                'day': current_date.day,
                'hour': current_date.hour + 1,  # Convert 0-23 to 1-24
                com_fr_key: com_fr,
                cf_key: cf,
            })
        
    # Create DataFrame in exact atlite format
    cluster_timeseries_df = pd.DataFrame(cluster_timeseries_data)
    
    # Export full timeseries data
    timeseries_file = output_path / f'cluster_{suffix}_atlite_timeseries.csv'
    cluster_timeseries_df.to_csv(timeseries_file, index=False)
    print(f"  - Saved cluster timeseries (8760h x {len(weighted_profiles)} clusters): {timeseries_file}")
    
    # Also save as parquet for efficiency
    parquet_file = output_path / f'cluster_{suffix}_atlite_timeseries.parquet'
    cluster_timeseries_df.to_parquet(parquet_file, index=False)
    print(f"  - Saved cluster timeseries (parquet): {parquet_file}")

def load_atlite_data_for_country(country_code: str, iso3_code: str, iso_processor=None):
    """Load atlite capacity factor data for the specified country"""
    
    # Check cache first if iso_processor is provided
    if iso_processor and hasattr(iso_processor, 'atlite_data_cache'):
        if iso3_code in iso_processor.atlite_data_cache:
            print(f"Loading atlite profiles for {country_code} ({iso3_code}) from cache...")
            return iso_processor.atlite_data_cache[iso3_code]
    
    print(f"Loading atlite profiles for {country_code} ({iso3_code}) from file...")
    
    try:
        atlite_src = Path(BASE_INPUT_FILES['atlite_profiles'])
        if not atlite_src.exists():
            print(f"  - Atlite data file not found: {atlite_src}")
            return pd.DataFrame()
        
        # Load only country-specific data using column selection to save memory
        # try:
        # First, read just the grid_cell column to identify relevant rows
        grid_cells = pd.read_parquet(atlite_src, columns=['grid_cell'])
        country_cells = grid_cells[grid_cells['grid_cell'].str.startswith(f'{iso3_code}_')]['grid_cell'].unique()
        
        if len(country_cells) == 0:
            print(f"  - No atlite data found for {iso3_code}")
            return pd.DataFrame()
        
        print(f"  - Found {len(country_cells)} grid cells for {iso3_code}")
        
        # Now load only the data for these specific cells
        atlite_country = pd.read_parquet(
            atlite_src,
            filters=[('grid_cell', 'in', country_cells.tolist())]
        )
                    
        if atlite_country.empty:
            print(f"  - No atlite data found for {iso3_code}")
            return pd.DataFrame()
        
        print(f"  - Found {len(atlite_country):,} atlite profile rows for {country_code}")
        print(f"  - Grid cells: {atlite_country['grid_cell'].nunique():,} unique cells")
        
        # Cache the result if iso_processor is provided
        if iso_processor and hasattr(iso_processor, 'atlite_data_cache'):
            iso_processor.atlite_data_cache[iso3_code] = atlite_country
            print(f"  - Cached atlite data for {iso3_code} (cache size: {len(iso_processor.atlite_data_cache)} countries)")
        
        return atlite_country
        
    except Exception as e:
        print(f"  - Error loading atlite data: {e}")
        return pd.DataFrame()

def cluster_buses_dbscan(buses_gdf, eps_km=1.0, min_samples=2, voltage_threshold=None):
    """
    Cluster buses using DBSCAN based on geographic distance
    
    Parameters:
    ----------
    buses_gdf : GeoDataFrame
        DataFrame containing bus information with geometry (lat/lon)
    eps_km : float, default=1.0
        Maximum distance in kilometers for neighborhood
    min_samples : int, default=2
        Minimum samples in neighborhood for core point
    voltage_threshold : float, optional
        If provided, only cluster buses within this voltage difference (kV)
    
    Returns:
    -------
    cluster_representatives : GeoDataFrame
        Representative buses for each cluster
    cluster_mapping : dict
        Mapping from original bus IDs to cluster representatives
    """
    
    if not SKLEARN_AVAILABLE:
        print("Warning: scikit-learn not available. Skipping bus clustering.")
        # Return original buses with identity mapping
        cluster_mapping = {bus_id: bus_id for bus_id in buses_gdf['bus_id']}
        return buses_gdf, cluster_mapping
    
    print(f"Clustering {len(buses_gdf)} buses with DBSCAN")
    print(f"   - Distance threshold: {eps_km} km")
    print(f"   - Minimum samples: {min_samples}")
    
    # Extract coordinates and convert to radians for haversine distance
    coordinates = np.array([[geom.y, geom.x] for geom in buses_gdf.geometry])
    coordinates_rad = np.radians(coordinates)
    
    # Calculate epsilon in radians (earth radius = 6371 km)
    eps_rad = eps_km / 6371.0
    
    # If voltage threshold is specified, pre-group by similar voltage levels
    if voltage_threshold and 'voltage' in buses_gdf.columns:
        print(f"   - Voltage-aware clustering (threshold: {voltage_threshold} kV)")
        buses_copy = buses_gdf.copy()
        buses_copy['cluster_id'] = -1
        cluster_id_counter = 0
        
        # Group by similar voltage levels
        for voltage in buses_copy['voltage'].unique():
            voltage_mask = abs(buses_copy['voltage'] - voltage) <= voltage_threshold
            voltage_group = buses_copy[voltage_mask]
            
            if len(voltage_group) < min_samples:
                # Assign individual cluster IDs to small groups
                for idx in voltage_group.index:
                    buses_copy.loc[idx, 'cluster_id'] = cluster_id_counter
                    cluster_id_counter += 1
                continue
            
            # Extract coordinates for this voltage group
            group_coords = np.array([[geom.y, geom.x] for geom in voltage_group.geometry])
            group_coords_rad = np.radians(group_coords)
            
            # Apply DBSCAN clustering
            clustering = DBSCAN(eps=eps_rad, min_samples=min_samples, metric='haversine')
            labels = clustering.fit_predict(group_coords_rad)
            
            # Assign cluster IDs
            for i, idx in enumerate(voltage_group.index):
                if labels[i] == -1:
                    # Noise point gets its own cluster
                    buses_copy.loc[idx, 'cluster_id'] = cluster_id_counter
                    cluster_id_counter += 1
                else:
                    buses_copy.loc[idx, 'cluster_id'] = cluster_id_counter + labels[i]
            
            if len(labels) > 0 and max(labels) >= 0:
                cluster_id_counter += max(labels) + 1
    else:
        # Standard geographic clustering without voltage consideration
        clustering = DBSCAN(eps=eps_rad, min_samples=min_samples, metric='haversine')
        labels = clustering.fit_predict(coordinates_rad)
        
        buses_copy = buses_gdf.copy()
        buses_copy['cluster_id'] = labels
        
        # Reassign noise points (-1) to individual cluster IDs
        max_cluster = max(labels) if len(labels) > 0 and max(labels) >= 0 else -1
        noise_counter = max_cluster + 1
        for idx in buses_copy.index:
            if buses_copy.loc[idx, 'cluster_id'] == -1:
                buses_copy.loc[idx, 'cluster_id'] = noise_counter
                noise_counter += 1

    # Create cluster representatives
    representatives = []
    cluster_mapping = {}
    
    for cluster_id in buses_copy['cluster_id'].unique():
        cluster_buses = buses_copy[buses_copy['cluster_id'] == cluster_id]
        
        if len(cluster_buses) == 1:
            # Single bus cluster - use as is
            rep = cluster_buses.iloc[0].copy()
            rep['original_bus_count'] = 1
            rep['aggregated_buses'] = cluster_buses['bus_id'].iloc[0]
            rep_name = f"cluster_{cluster_id}"
        else:
            # Multi-bus cluster - aggregate properties
            rep = aggregate_cluster_properties(cluster_buses, cluster_id)
            rep_name = f"cluster_{cluster_id}"
        
        representatives.append(rep)
        
        # Map all original buses to this representative
        for orig_bus_id in cluster_buses['bus_id']:
            cluster_mapping[orig_bus_id] = rep_name
    
    # Create GeoDataFrame of representatives
    representatives_gdf = gpd.GeoDataFrame(representatives, crs=buses_gdf.crs)
    representatives_gdf.reset_index(drop=True, inplace=True)
    representatives_gdf.index = [f"cluster_{i}" for i in range(len(representatives_gdf))]
    
    n_original = len(buses_gdf)
    n_clustered = len(representatives_gdf)
    reduction_pct = 100 * (1 - n_clustered / n_original)
    
    print(f"   + Clustered {n_original} -> {n_clustered} buses ({reduction_pct:.1f}% reduction)")
    
    return representatives_gdf, cluster_mapping

def aggregate_cluster_properties(cluster_buses, cluster_id):
    """
    Aggregate electrical and geographical properties of buses in a cluster
    """
    # Geographic center (centroid)
    centroid = cluster_buses.geometry.centroid.iloc[0]
    
    # Representative properties
    rep = cluster_buses.iloc[0].copy()  # Start with first bus properties
    rep['cluster_id'] = cluster_id
    rep['geometry'] = centroid
    rep['x'] = centroid.x
    rep['y'] = centroid.y
    
    # Aggregate electrical properties
    if 'voltage' in cluster_buses.columns:
        # Use the most common voltage level
        voltage_counts = cluster_buses['voltage'].value_counts()
        rep['voltage'] = voltage_counts.index[0]
    
    # Keep track of original buses
    rep['original_bus_count'] = len(cluster_buses)
    rep['aggregated_buses'] = ','.join(cluster_buses['bus_id'].astype(str))
    
    # Handle other columns
    for col in cluster_buses.columns:
        if col not in ['geometry', 'x', 'y', 'cluster_id', 'voltage', 'bus_id']:
            if cluster_buses[col].dtype in ['object']:
                # For object columns, use the most common value
                rep[col] = cluster_buses[col].mode().iloc[0] if not cluster_buses[col].mode().empty else cluster_buses[col].iloc[0]
            elif cluster_buses[col].dtype in ['int64', 'float64']:
                # For numerical columns, use mean or sum as appropriate
                if col.startswith('p_') or col.startswith('q_') or 'power' in col.lower():
                    rep[col] = cluster_buses[col].sum()  # Sum power values
                else:
                    rep[col] = cluster_buses[col].mean()  # Average other values
    
    return rep

def update_network_topology_after_clustering(cluster_mapping, lines_df, clustered_buses_gdf):
    """
    Update network topology after bus clustering by mapping lines to cluster representatives
    """
    if lines_df.empty:
        return pd.DataFrame()
    
    print("Updating network topology after clustering...")
    
    # Create mapping from cluster names to original bus IDs
    # cluster_mapping: original_bus -> cluster_name (e.g., 'CH1-220' -> 'cluster_0')
    # We need: cluster_name -> representative_original_bus (e.g., 'cluster_0' -> 'CH1-220')
    cluster_to_original_bus = {}
    for cluster_name in clustered_buses_gdf.index:
        original_bus_id = clustered_buses_gdf.loc[cluster_name, 'bus_id']
        cluster_to_original_bus[cluster_name] = original_bus_id
    
    # Map lines to clustered buses first (using cluster names)
    lines_updated = lines_df.copy()
    lines_updated['bus0'] = lines_updated['bus0'].astype(str).map(cluster_mapping).fillna(lines_updated['bus0'])
    lines_updated['bus1'] = lines_updated['bus1'].astype(str).map(cluster_mapping).fillna(lines_updated['bus1'])
    
    # Remove self-loops (lines connecting a cluster to itself)
    original_count = len(lines_updated)
    lines_updated = lines_updated[lines_updated['bus0'] != lines_updated['bus1']]
    self_loops_removed = original_count - len(lines_updated)
    
    # Aggregate parallel lines between same bus pairs
    lines_updated = aggregate_parallel_lines(lines_updated)
    
    # Map cluster names back to original bus IDs (representative buses)
    lines_updated['bus0'] = lines_updated['bus0'].map(cluster_to_original_bus).fillna(lines_updated['bus0'])
    lines_updated['bus1'] = lines_updated['bus1'].map(cluster_to_original_bus).fillna(lines_updated['bus1'])
    
    print(f"   - Lines: {len(lines_df)} -> {len(lines_updated)} (removed {self_loops_removed} self-loops, {len(lines_df) - self_loops_removed - len(lines_updated)} parallel)")
    
    return lines_updated

def identify_critical_infrastructure(lines_df, buses_df, country_code):
    """Identify critical transmission infrastructure that should be preserved"""
    print("Identifying critical transmission infrastructure...")
    
    critical_lines = set()
    
    # 1. High voltage backbone (380kV and above)
    if 'voltage' in lines_df.columns:
        hv_lines = lines_df[lines_df['voltage'] >= 380].index
        critical_lines.update(hv_lines)
        print(f"  - Found {len(hv_lines)} high-voltage lines (>=380kV)")
    
    # 2. Major capacity lines (top 20% by s_nom)
    if 's_nom' in lines_df.columns:
        capacity_threshold = lines_df['s_nom'].quantile(0.8)
        major_capacity = lines_df[lines_df['s_nom'] >= capacity_threshold].index
        critical_lines.update(major_capacity)
        print(f"  - Found {len(major_capacity)} high-capacity lines (>={capacity_threshold:.0f} MVA)")
    
    # 3. Detect potential submarine/international connections
    # Lines that are unusually long compared to typical transmission distances
    if 'length' in lines_df.columns:
        length_threshold = lines_df['length'].quantile(0.95)  # Top 5% longest lines
        long_lines = lines_df[lines_df['length'] >= length_threshold].index
        critical_lines.update(long_lines)
        print(f"  - Found {len(long_lines)} unusually long lines (>={length_threshold:.0f} km) - potential submarine/international")
    
    # 4. Single corridor detection - lines with no parallel alternatives
    corridor_counts = lines_df.groupby(['bus0', 'bus1']).size()
    single_corridors = corridor_counts[corridor_counts == 1].index
    for bus0, bus1 in single_corridors:
        line_idx = lines_df[(lines_df['bus0'] == bus0) & (lines_df['bus1'] == bus1)].index
        critical_lines.update(line_idx)
    
    print(f"  - Found {len(single_corridors)} single transmission corridors")
    print(f"  - Total critical lines: {len(critical_lines)}")
    
    return list(critical_lines)

def detect_geographic_constraints(buses_df, country_code):
    """Detect geographic constraints using available data"""
    constraints = {
        'coastal_buses': set(),
        'inland_buses': set(),
        'major_cities': set(),
        'industrial_centers': set()
    }
    
    try:
        # Load major cities data
        cities_df = pd.read_csv(SCRIPT_DIR / '../data/country_data/' / 'worldcities.csv')
        country_cities = cities_df[cities_df['iso2'] == country_code.upper()]
        
        # Identify major cities (population > 100k)
        major_cities = country_cities[country_cities['population'] > 100000]
        if not major_cities.empty:
            print(f"  - Found {len(major_cities)} major cities in {country_code}")
            
            # Find buses near major cities (within 50km)
            for _, city in major_cities.iterrows():
                city_point = Point(city['lng'], city['lat'])
                nearby_buses = buses_df[
                    buses_df.geometry.distance(city_point) < 0.5  # ~50km in degrees
                ].index
                constraints['major_cities'].update(nearby_buses)
        
        # Load industrial facilities
        industrial_df = pd.read_csv(SCRIPT_DIR / '../data' / 'Industrial_Database.csv', sep=';')
        country_industrial = industrial_df[industrial_df['Country'] == get_country_name_from_iso2(country_code)]
        
        if not country_industrial.empty:
            print(f"  - Found {len(country_industrial)} industrial facilities in {country_code}")
            # Parse geometry and find nearby buses
            # This would need more detailed implementation based on the geometry format
        
    except Exception as e:
        print(f"  - Warning: Could not load geographic constraint data: {e}")
    
    return constraints

def cluster_buses_realistically(buses_gdf, lines_df, country_code, eps_km=5.0, min_samples=2):
    """Cluster buses while preserving transmission corridor structure"""
    print(f"Applying realistic bus clustering (eps={eps_km}km, min_samples={min_samples})...")
    
    if not SKLEARN_AVAILABLE:
        print("Warning: scikit-learn not available. Skipping clustering.")
        return buses_gdf, {}
    
    # Identify critical infrastructure first
    critical_lines = identify_critical_infrastructure(lines_df, buses_gdf, country_code)
    critical_buses = set()
    
    # Extract buses that are endpoints of critical lines
    for line_idx in critical_lines:
        line = lines_df.loc[line_idx]
        critical_buses.add(line['bus0'])
        critical_buses.add(line['bus1'])
    
    print(f"  - {len(critical_buses)} buses are endpoints of critical infrastructure")
    
    # Get geographic constraints
    geo_constraints = detect_geographic_constraints(buses_gdf, country_code)
    
    # Prepare coordinates for clustering
    coords = np.column_stack([buses_gdf.geometry.x, buses_gdf.geometry.y])
    
    # Convert to projected coordinates for distance-based clustering
    buses_projected = buses_gdf.to_crs(DISTANCE_CRS)
    coords_projected = np.column_stack([buses_projected.geometry.x, buses_projected.geometry.y])
    
    # Apply DBSCAN clustering
    eps_meters = eps_km * 1000
    clustering = DBSCAN(eps=eps_meters, min_samples=min_samples).fit(coords_projected)
    
    # Create cluster mapping with special handling for critical buses
    cluster_mapping = {}
    cluster_representatives = {}
    
    for i, (bus_id, cluster_id) in enumerate(zip(buses_gdf.index, clustering.labels_)):
        if cluster_id == -1:  # Noise points become their own clusters
            cluster_name = f"cluster_{bus_id}"
            cluster_mapping[str(bus_id)] = cluster_name
            cluster_representatives[cluster_name] = bus_id
        else:
            cluster_name = f"cluster_{cluster_id}"
            
            # For critical buses, prefer them as cluster representatives
            if str(bus_id) in critical_buses:
                if cluster_name not in cluster_representatives:
                    cluster_representatives[cluster_name] = bus_id
                cluster_mapping[str(bus_id)] = cluster_name
            else:
                cluster_mapping[str(bus_id)] = cluster_name
                if cluster_name not in cluster_representatives:
                    cluster_representatives[cluster_name] = bus_id
                else:
                    # Prefer simplified format buses as representatives (like original algorithm)
                    current_rep_id = cluster_representatives[cluster_name]
                    current_rep_bus_id = str(buses_gdf.loc[current_rep_id, 'bus_id'])
                    new_bus_id = str(buses_gdf.loc[bus_id, 'bus_id'])
                    
                    # If current rep has way/ format but new bus has simplified format, switch
                    if (current_rep_bus_id.startswith('way/') or current_rep_bus_id.startswith('relation/')) and \
                       not (new_bus_id.startswith('way/') or new_bus_id.startswith('relation/')):
                        cluster_representatives[cluster_name] = bus_id
    
    # Create clustered buses dataframe
    clustered_buses_data = []
    for cluster_name, rep_bus_id in cluster_representatives.items():
        rep_bus = buses_gdf.loc[rep_bus_id].copy()
        # KEEP ORIGINAL bus_id - don't overwrite with cluster_name
        # The cluster_name is used in the index and mapping, but bus_id stays original
        
        # Add cluster metadata
        cluster_bus_ids = [bid for bid, cname in cluster_mapping.items() if cname == cluster_name]
        rep_bus['cluster_id'] = cluster_name
        rep_bus['original_bus_count'] = len(cluster_bus_ids)
        rep_bus['aggregated_buses'] = ','.join(cluster_bus_ids)
        
        # Calculate cluster centroid for better positioning if multiple buses
        if len(cluster_bus_ids) > 1:
            try:
                cluster_buses = buses_gdf.loc[[int(bid) if bid.isdigit() else buses_gdf[buses_gdf['bus_id'] == bid].index[0] for bid in cluster_bus_ids]]
                if not cluster_buses.empty:
                    centroid = cluster_buses.geometry.centroid.iloc[0]
                    rep_bus.geometry = centroid
            except:
                pass  # Keep original position if centroid calculation fails
        
        clustered_buses_data.append(rep_bus)
    
    clustered_buses = gpd.GeoDataFrame(clustered_buses_data, crs=buses_gdf.crs)
    
    # Set cluster names as index (like original function)
    cluster_names = [rep_bus['cluster_id'] for rep_bus in clustered_buses_data]
    clustered_buses.index = cluster_names
    
    print(f"  - Clustered {len(buses_gdf)} buses into {len(clustered_buses)} clusters")
    print(f"  - Preserved {len(critical_buses)} critical infrastructure endpoints")
    
    return clustered_buses, cluster_mapping

def aggregate_lines_realistically(lines_df, cluster_mapping, critical_lines):
    """Aggregate lines while preserving critical infrastructure and realistic topology"""
    if lines_df.empty:
        return lines_df
    
    print("Aggregating transmission lines realistically...")
    
    # Separate critical and non-critical lines
    critical_set = set(critical_lines)
    critical_lines_df = lines_df.loc[critical_lines].copy()
    non_critical_df = lines_df.drop(critical_lines).copy()
    
    print(f"  - Preserving {len(critical_lines_df)} critical lines unchanged")
    print(f"  - Aggregating {len(non_critical_df)} non-critical lines")
    
    # Map critical lines to clustered buses
    critical_lines_df['bus0'] = critical_lines_df['bus0'].astype(str).map(cluster_mapping).fillna(critical_lines_df['bus0'])
    critical_lines_df['bus1'] = critical_lines_df['bus1'].astype(str).map(cluster_mapping).fillna(critical_lines_df['bus1'])
    
    # Remove self-loops in critical lines
    critical_lines_df = critical_lines_df[critical_lines_df['bus0'] != critical_lines_df['bus1']]
    
    # Aggregate non-critical lines using improved parallel combination
    if not non_critical_df.empty:
        non_critical_df['bus0'] = non_critical_df['bus0'].astype(str).map(cluster_mapping).fillna(non_critical_df['bus0'])
        non_critical_df['bus1'] = non_critical_df['bus1'].astype(str).map(cluster_mapping).fillna(non_critical_df['bus1'])
        
        # Remove self-loops
        non_critical_df = non_critical_df[non_critical_df['bus0'] != non_critical_df['bus1']]
        
        # Group by bus pairs and aggregate
        aggregated_non_critical = []
        grouped = non_critical_df.groupby(['bus0', 'bus1'])
        
        for (bus0, bus1), group in grouped:
            if len(group) == 1:
                aggregated_non_critical.append(group.iloc[0])
            else:
                # Realistic parallel line aggregation
                agg_line = group.iloc[0].copy()
                
                # Parallel impedance combination
                if 'r' in group.columns and 'x' in group.columns:
                    z_values = group['r'] + 1j * group['x']
                    z_nonzero = z_values[np.abs(z_values) > 1e-10]
                    if len(z_nonzero) > 0:
                        z_total = 1 / (1 / z_nonzero).sum()
                        agg_line['r'] = z_total.real
                        agg_line['x'] = z_total.imag
                    else:
                        agg_line['r'] = 0
                        agg_line['x'] = 0
                
                # Capacities and admittances add in parallel
                for col in ['g', 'b', 's_nom']:
                    if col in group.columns:
                        agg_line[col] = group[col].sum()
                
                # Use minimum length (shortest path)
                if 'length' in group.columns:
                    agg_line['length'] = group['length'].min()
                
                # Keep highest voltage level
                if 'voltage' in group.columns:
                    agg_line['voltage'] = group['voltage'].max()
                
                aggregated_non_critical.append(agg_line)
        
        non_critical_aggregated = pd.DataFrame(aggregated_non_critical)
    else:
        non_critical_aggregated = pd.DataFrame()
    
    # Combine critical and aggregated non-critical lines
    if not critical_lines_df.empty and not non_critical_aggregated.empty:
        final_lines = pd.concat([critical_lines_df, non_critical_aggregated], ignore_index=True)
    elif not critical_lines_df.empty:
        final_lines = critical_lines_df
    elif not non_critical_aggregated.empty:
        final_lines = non_critical_aggregated
    else:
        final_lines = pd.DataFrame()
    
    print(f"  - Final network: {len(final_lines)} transmission lines")
    print(f"    * {len(critical_lines_df)} critical lines preserved")
    print(f"    * {len(non_critical_aggregated)} aggregated corridors")
    
    return final_lines

def get_iso_code(country_name):
    """Convert country name to ISO3 code using pycountry with special cases handling"""
    if not isinstance(country_name, str):
        return None
    name = country_name.strip().lower()
    special_cases = {
        'kosovo': 'XKX',
        'kosovo (under unscr 1244/99)': 'XKX',
        'chinese taipei': 'TWN',
        'republic of korea': 'KOR',
        'china, hong kong special administrative region': 'HKG',
        'democratic republic of the congo': 'COD',
        'russia': 'RUS',
        'dr congo': 'COD',
    }
    if name in special_cases:
        return special_cases[name]
    try:
        import pycountry
        return pycountry.countries.lookup(country_name).alpha_3
    except (LookupError, AttributeError, ImportError):
        return None

def filter_gem_data_by_status(df_gem, include_announced=True, include_preconstruction=True):
    """
    Centralized GEM data status filtering to eliminate redundant filtering operations.
    Consistent with main pipeline filtering logic.
    
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

def get_country_name_from_iso2(iso2_code):
    """Convert ISO2 code to country name for data matching using VS_mappings kinesys_region_map"""
    try:
        # Use shared data loader to get kinesys region mapping
        # Standard approach: add parent directory to Python path
        
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        
        from shared_data_loader import get_shared_loader
        shared_loader = get_shared_loader("../data/")
        region_map = shared_loader.get_vs_mappings_sheet('kinesys_region_map')
        
        # Look up the country name using the 2-alpha code
        iso2_upper = iso2_code.upper()
        matching_row = region_map[region_map['2-alpha code'] == iso2_upper]
        
        if not matching_row.empty:
            # Use the 'kinesys' column which contains the country name
            country_name = matching_row['kinesys'].iloc[0]
            print(f"  - Found country mapping: {iso2_code} -> {country_name}")
            return country_name
        else:
            print(f"  - No mapping found for {iso2_code} in kinesys_region_map, using fallback")
            # Fallback to static mapping for common cases
            fallback_mapping = {
                'DE': 'Germany', 'FR': 'France', 'IT': 'Italy', 'ES': 'Spain',
                'CH': 'Switzerland', 'AT': 'Austria', 'NL': 'Netherlands',
                'BE': 'Belgium', 'PL': 'Poland', 'CZ': 'Czech Republic',
                'FI': 'Finland', 'SE': 'Sweden', 'NO': 'Norway', 'DK': 'Denmark'
            }
            return fallback_mapping.get(iso2_upper, iso2_code)
            
    except Exception as e:
        print(f"  - Error loading kinesys_region_map: {e}")
        print(f"  - Using fallback mapping for {iso2_code}")
        # Fallback to static mapping
        fallback_mapping = {
            'DE': 'Germany', 'FR': 'France', 'IT': 'Italy', 'ES': 'Spain',
            'CH': 'Switzerland', 'AT': 'Austria', 'NL': 'Netherlands',
            'BE': 'Belgium', 'PL': 'Poland', 'CZ': 'Czech Republic',
            'FI': 'Finland', 'SE': 'Sweden', 'NO': 'Norway', 'DK': 'Denmark'
        }
        return fallback_mapping.get(iso2_code.upper(), iso2_code)

def aggregate_parallel_lines(lines_df):
    """Legacy function - now replaced by aggregate_lines_realistically"""
    print("Warning: Using legacy line aggregation. Consider using realistic aggregation instead.")
    
    if lines_df.empty:
        return lines_df
    
    # Group by bus pairs
    grouped = lines_df.groupby(['bus0', 'bus1'])
    
    aggregated_lines = []
    for (bus0, bus1), group in grouped:
        if len(group) == 1:
            aggregated_lines.append(group.iloc[0])
        else:
            # Aggregate multiple lines - parallel combination for impedances
            agg_line = group.iloc[0].copy()
            
            # For parallel lines: 1/Z_total = 1/Z1 + 1/Z2 + ...
            if 'r' in group.columns and 'x' in group.columns:
                # Handle zero impedances carefully
                z_values = group['r'] + 1j * group['x']
                z_nonzero = z_values[np.abs(z_values) > 1e-10]
                if len(z_nonzero) > 0:
                    z_total = 1 / (1 / z_nonzero).sum()
                    agg_line['r'] = z_total.real
                    agg_line['x'] = z_total.imag
                else:
                    agg_line['r'] = 0
                    agg_line['x'] = 0
            
            # Capacitance and conductance add in parallel
            for col in ['g', 'b', 's_nom']:
                if col in group.columns:
                    agg_line[col] = group[col].sum()
            
            # Length is average
            if 'length' in group.columns:
                agg_line['length'] = group['length'].mean()
            
            aggregated_lines.append(agg_line)
    
    return pd.DataFrame(aggregated_lines).reset_index(drop=True)



def perform_zone_to_bus_mapping(buses_gdf, zones_gdf):
    """Map zones to buses - each zone gets assigned to its buses or nearest bus"""
    print("Performing zone-to-bus mapping...")
    
    # Spatial join: buses within zones
    bus_zones = gpd.sjoin(buses_gdf, zones_gdf, how='left', predicate='within')
    print(f"  - {len(bus_zones)} bus-zone combinations found")
    
    # Group by zone to see which zones have buses
    zone_bus_counts = bus_zones.groupby('index_right').size()
    zones_with_buses = zone_bus_counts[zone_bus_counts > 0].index
    zones_without_buses = set(zones_gdf.index) - set(zones_with_buses)
    
    print(f"  - {len(zones_with_buses)} zones have buses")
    print(f"  - {len(zones_without_buses)} zones have no buses")
    
    # For zones without buses, find nearest bus
    if zones_without_buses:
        print("  - Mapping zones without buses to nearest bus...")
        for zone_idx in zones_without_buses:
            zone_geom = zones_gdf.loc[zone_idx].geometry
            zone_centroid = zone_geom.centroid
            
            # Find nearest bus
            distances = buses_gdf.geometry.distance(zone_centroid)
            nearest_bus_idx = distances.idxmin()
            nearest_bus = buses_gdf.loc[nearest_bus_idx]
            
            # Add this zone-bus mapping
            zone_row = zones_gdf.loc[zone_idx].copy()
            zone_row['index_right'] = zone_idx
            for col in nearest_bus.index:
                if col not in zone_row.index:
                    zone_row[col] = nearest_bus[col]
            
            bus_zones = pd.concat([bus_zones, pd.DataFrame([zone_row])], ignore_index=True)
    
    return bus_zones

def create_zone_bus_mapping(bus_zones, lines_df, country_code, cluster_mapping=None, clustered_lines_df=None):
    """Create zone-to-bus mapping, optionally using clustered buses"""
    print("Creating zone-to-bus mapping...")
    
    # Get valid bus IDs (based on connectivity)
    unique_buses = bus_zones[['bus_id']].drop_duplicates()
    
    # Use all buses (validity filtering removed)
    valid_cluster_buses = set(unique_buses['bus_id'])
    print(f"  - Using all {len(valid_cluster_buses)} buses")
    
    # Create mapping data
    mapping_data = []
    for _, row in bus_zones.iterrows():
        bus_id = row['bus_id']
        
        # Check if bus is valid (for both clustered and non-clustered cases)
        if bus_id not in valid_cluster_buses:
            continue
            
        # Get zone information from the spatial join
        zone_index = row.get('index_right', '')
        if zone_index != '' and not pd.isna(zone_index):
            # Get the actual zone ID and grid_cell from the zones data
            zone_id = row.get('id', zone_index)  # Use 'id' column if available, fallback to index
            grid_cell = row.get('grid_cell', f"{get_iso3_code(country_code)}_{zone_id}")  # Use grid_cell if available
        else:
            zone_id = ''
            grid_cell = f"{get_iso3_code(country_code)}_unknown"
        
        mapping_info = {
            'zone_id': zone_id,
            'bus_id': bus_id,
            'grid_cell': grid_cell
        }
        
        mapping_data.append(mapping_info)
    
    mapping_df = pd.DataFrame(mapping_data)
    
    # DEDUPLICATION: Keep unique buses only (first zone encountered)
    initial_count = len(mapping_df)
    mapping_df = mapping_df.drop_duplicates(subset=['bus_id'], keep='first')
    final_count = len(mapping_df)
    
    if initial_count != final_count:
        print(f"  - Removed {initial_count - final_count} duplicate bus entries (kept unique bus_ids)")
    
    print(f"  - Created zone-bus mapping with {final_count} unique buses")
    
    return mapping_df

def get_country_iso_code(country_name):
    """Convert country name to ISO3 code for power plant filtering"""
    if not isinstance(country_name, str):
        return None
    name = country_name.strip().lower()
    # Manual mappings for special cases
    special_cases = {
        'kosovo': 'XKX',
        'kosovo (under unscr 1244/99)': 'XKX',
        'chinese taipei': 'TWN',
        'republic of korea': 'KOR',
        'china, hong kong special administrative region': 'HKG',
        'democratic republic of the congo': 'COD',
        'russia': 'RUS',
        'dr congo': 'COD',
    }
    if name in special_cases:
        return special_cases[name]
    try:
        if PYCOUNTRY_AVAILABLE:
            return pycountry.countries.lookup(country_name).alpha_3
    except (LookupError, AttributeError):
        pass
    return None

def assign_power_plants_to_buses(df_plants, df_buses):
    """
    Assign each power plant to its nearest bus based on geographic distance
    """
    if not SKLEARN_AVAILABLE:
        print("Warning: scikit-learn not available. Skipping power plant assignment.")
        return pd.DataFrame()
    
    # Remove rows with missing coordinates
    df_plants_clean = df_plants.dropna(subset=['Latitude', 'Longitude']).copy()
    df_buses_clean = df_buses.dropna(subset=['latitude', 'longitude']).copy()
    
    if df_plants_clean.empty:
        print("Warning: No power plants with valid coordinates found")
        return df_plants_clean
    
    if df_buses_clean.empty:
        print("Warning: No buses with valid coordinates found")
        return df_plants_clean
    
    # Convert coordinates to radians for BallTree
    bus_coords_rad = np.radians(df_buses_clean[['latitude', 'longitude']].values)
    plant_coords_rad = np.radians(df_plants_clean[['Latitude', 'Longitude']].values)
    
    # Create BallTree for efficient nearest neighbor search
    tree = BallTree(bus_coords_rad, metric='haversine')
    
    # Find nearest bus for each power plant
    distances, indices = tree.query(plant_coords_rad, k=1)
    
    # Convert distances from radians to kilometers
    distances_km = distances.flatten() * 6371  # Earth's radius in km
    nearest_bus_indices = indices.flatten()
    
    # Add nearest bus information to power plants dataframe
    df_result = df_plants_clean.copy()
    df_result['bus_id'] = df_buses_clean.iloc[nearest_bus_indices]['bus_id'].values
    df_result['nearest_bus_latitude'] = df_buses_clean.iloc[nearest_bus_indices]['latitude'].values
    df_result['nearest_bus_longitude'] = df_buses_clean.iloc[nearest_bus_indices]['longitude'].values
    df_result['distance_to_bus_km'] = distances_km
    df_result['nearest_bus_voltage_kv'] = df_buses_clean.iloc[nearest_bus_indices]['voltage_kv'].values
    
    # Add grid_cell if available
    if 'grid_cell' in df_buses_clean.columns:
        df_result['grid_cell'] = df_buses_clean.iloc[nearest_bus_indices]['grid_cell'].values
    
    return df_result

def map_plants_to_clustered_buses(country_code: str, iso3_code: str, iso_processor=None):
    """
    Create simple mapping: GEM location ID -> clustered bus_id
    
    Parameters:
    ----------
    country_code : str
        ISO2 country code (e.g., 'IT', 'DE', 'CH')
    iso3_code : str
        ISO3 country code (e.g., 'ITA', 'DEU', 'CHE')
    iso_processor : object, optional
        ISO processor instance with cached GEM data
    
    Returns:
    -------
    pd.DataFrame
        Two-column DataFrame with ['GEM location ID', 'bus_id']
    """
    if not SKLEARN_AVAILABLE:
        print("Warning: scikit-learn not available. Skipping power plant mapping.")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    print(f"Mapping power plants to clustered buses for {iso3_code}...")
    
    # Use cached GEM data from iso_processor if available
    if iso_processor is not None and hasattr(iso_processor, 'main') and hasattr(iso_processor.main, 'df_gem'):
        print(f"  - Using cached GEM data from iso_processor")
        df_gem_country = iso_processor.main.df_gem[iso_processor.main.df_gem['iso_code'] == iso_processor.input_iso]
        df_gem_country = filter_gem_data_by_status(df_gem_country, include_announced=True, include_preconstruction=True)
        print(f"  - Found {len(df_gem_country)} active power plants in {iso3_code}")
    else:
        # Fallback to direct file loading
        gem_src = Path(BASE_INPUT_FILES['power_plants'])
        if not gem_src.exists():
            print(f"Warning: GEM data file not found at {gem_src}")
            return pd.DataFrame(columns=['GEM location ID', 'bus_id'])

        try:
            # Load and filter GEM data
            df_gem = pd.read_excel(gem_src, sheet_name=GEM_SHEET_NAME)
            print(f"  - Loaded {len(df_gem)} power plants from GEM data")
            
            # Filter out inactive plants using centralized function
            df_gem = filter_gem_data_by_status(df_gem, include_announced=True, include_preconstruction=True)
            
            # Add iso_code column using the get_iso_code function
            print(f"  - Adding ISO codes to power plants data...")
            df_gem['iso_code'] = df_gem['Country/area'].apply(get_iso_code)
            
            # Filter by country
            df_gem_country = df_gem[df_gem['iso_code'] == iso3_code]
            print(f"  - Found {len(df_gem_country)} active power plants in {iso3_code}")

        except Exception as e:
            print(f"  - Error loading GEM data: {e}")
            return pd.DataFrame(columns=['GEM location ID', 'bus_id'])

    if df_gem_country.empty:
        print(f"  - No power plants found for {iso3_code}")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])

    df_plants_clean = df_gem_country.dropna(subset=['Latitude', 'Longitude', 'GEM location ID']).copy()
    print(f"  - {len(df_plants_clean)} plants have valid coordinates and GEM location ID")

    if df_plants_clean.empty:
        print("  - No plants with valid coordinates found")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    # Load clustered buses data
    clustered_buses_file = Path(f'output_eur/{iso3_code}/{iso3_code}_clustered_buses.csv')
    if not clustered_buses_file.exists():
        print(f"Warning: Clustered buses file not found at {clustered_buses_file}")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    try:
        # Load clustered buses (index contains cluster names like 'cluster_0')
        clustered_buses_df = pd.read_csv(clustered_buses_file, index_col=0)
        print(f"  - Loaded {len(clustered_buses_df)} clustered buses")
        
        # Check for required coordinate columns
        if 'x' not in clustered_buses_df.columns or 'y' not in clustered_buses_df.columns:
            print("  - Error: Clustered buses missing coordinate columns (x, y)")
            return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
        
        # Remove buses with missing coordinates
        clustered_buses_clean = clustered_buses_df.dropna(subset=['x', 'y']).copy()
        print(f"  - {len(clustered_buses_clean)} clustered buses have valid coordinates")
        
        if clustered_buses_clean.empty:
            print("  - No clustered buses with valid coordinates found")
            return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
        
    except Exception as e:
        print(f"Error loading clustered buses: {e}")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    # Perform spatial assignment using BallTree
    try:
        # Convert coordinates to radians for BallTree (longitude=x, latitude=y)
        bus_coords_rad = np.radians(clustered_buses_clean[['y', 'x']].values)  # lat, lon order for BallTree
        plant_coords_rad = np.radians(df_plants_clean[['Latitude', 'Longitude']].values)
        
        # Create BallTree for efficient nearest neighbor search
        tree = BallTree(bus_coords_rad, metric='haversine')
        
        # Find nearest clustered bus for each power plant
        distances, indices = tree.query(plant_coords_rad, k=1)
        
        # Convert distances from radians to kilometers
        distances_km = distances.flatten() * 6371  # Earth's radius in km
        nearest_bus_indices = indices.flatten()
        nearest_bus_ids = clustered_buses_clean.iloc[nearest_bus_indices]['bus_id'].values
        
        # Create mapping dataframe
        plant_bus_mapping = pd.DataFrame({
            'GEM location ID': df_plants_clean['GEM location ID'].values,
            'bus_id': nearest_bus_ids
        })
        
        # DEDUPLICATION: Keep unique power plants only (first occurrence)
        initial_count = len(plant_bus_mapping)
        plant_bus_mapping = plant_bus_mapping.drop_duplicates(subset=['GEM location ID'], keep='first')
        final_count = len(plant_bus_mapping)
        
        if initial_count != final_count:
            print(f"  - Removed {initial_count - final_count} duplicate power plants (kept unique GEM location IDs)")
        
        print(f"  - Successfully mapped {final_count} unique power plants to clustered buses")
        print(f"  - Average distance to nearest bus: {distances_km.mean():.2f} km")
        print(f"  - Maximum distance to nearest bus: {distances_km.max():.2f} km")
        
        return plant_bus_mapping
        
    except Exception as e:
        print(f"Error during spatial assignment: {e}")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])



def compute_and_save_bus_load_share(buses_gdf, iso2_code, iso3_code, pop_min=10000, output_dir='output'):
    """Compute simple bus load share (0-1) per bus using cities >= pop_min via hard-nearest assignment.

    Saves: output/<ISO3>/<ISO3>_bus_load_share.csv with columns ['bus_id', 'load_share'].
    """
    print("Computing bus load share from cities...")

    # Validate buses input
    if buses_gdf is None or buses_gdf.empty:
        print("  - No buses provided; skipping load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"]) 

    # Ensure we have coordinates
    buses = buses_gdf.copy()
    if 'y' in buses.columns and 'x' in buses.columns:
        buses_lat = buses['y']
        buses_lon = buses['x']
    elif 'latitude' in buses.columns and 'longitude' in buses.columns:
        buses_lat = buses['latitude']
        buses_lon = buses['longitude']
    elif 'geometry' in buses.columns:
        buses_lat = buses.geometry.y
        buses_lon = buses.geometry.x
    else:
        print("  - Missing coordinates on buses; skipping load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"]) 

    # Read worldcities
    cities_src = Path(BASE_INPUT_FILES['worldcities'])
    if not cities_src.exists():
        print(f"  - Cities file not found at {cities_src}; skipping load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"]) 

    try:
        cities_df = pd.read_csv(cities_src)
    except Exception as e:
        print(f"  - Error reading cities file: {e}")
        return pd.DataFrame(columns=["bus_id", "load_share"]) 

    # Flexible column names
    lat_col = 'lat' if 'lat' in cities_df.columns else 'latitude'
    lon_col = 'lng' if 'lng' in cities_df.columns else ('lon' if 'lon' in cities_df.columns else 'longitude')
    pop_col = 'population'
    iso3_col = 'iso3' if 'iso3' in cities_df.columns else ('iso3_code' if 'iso3_code' in cities_df.columns else None)

    if iso3_col is None or pop_col not in cities_df.columns or lat_col not in cities_df.columns or lon_col not in cities_df.columns:
        print("  - Cities file missing required columns; skipping load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"]) 

    # Filter to country and pop threshold
    cities_country = cities_df[cities_df[iso3_col] == iso3_code]
    cities_country = cities_country.dropna(subset=[lat_col, lon_col, pop_col]).copy()
    cities_country = cities_country[cities_country[pop_col] >= pop_min]

    if cities_country.empty:
        print(f"  - No cities >= {pop_min} pop for {iso3_code}; falling back to equal shares")
        # Equal shares across buses
        num_buses = len(buses)
        if num_buses == 0:
            return pd.DataFrame(columns=["bus_id", "load_share"]) 
        load_share_df = pd.DataFrame({
            'bus_id': buses['bus_id'].values,
            'load_share': np.full(num_buses, 1.0 / num_buses)
        })
        output_path = Path(output_dir) / iso3_code
        output_path.mkdir(parents=True, exist_ok=True)
        load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share.csv', index=False)
        print(f"  - Saved bus load share (equal split) for {num_buses} buses")
        return load_share_df

    if not SKLEARN_AVAILABLE:
        print("  - scikit-learn unavailable; cannot perform nearest assignment. Falling back to equal shares")
        num_buses = len(buses)
        load_share_df = pd.DataFrame({
            'bus_id': buses['bus_id'].values,
            'load_share': np.full(num_buses, 1.0 / num_buses)
        })
        output_path = Path(output_dir) / iso3_code
        output_path.mkdir(parents=True, exist_ok=True)
        load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share.csv', index=False)
        print(f"  - Saved bus load share (equal split) for {num_buses} buses")
        return load_share_df

    # Build BallTree and assign each city to nearest bus
    bus_coords_rad = np.radians(np.column_stack([buses_lat.values, buses_lon.values]))
    city_coords_rad = np.radians(cities_country[[lat_col, lon_col]].values)
    tree = BallTree(bus_coords_rad, metric='haversine')
    _, indices = tree.query(city_coords_rad, k=1)
    nearest_bus_idx = indices.flatten()

    # Vectorized aggregation of population per bus
    assigned_pop = pd.Series(0.0, index=buses.index)
    counts = pd.Series(0, index=buses.index)
    # Group by nearest bus index and sum populations
    pop_by_bus = pd.Series(cities_country[pop_col].values).groupby(nearest_bus_idx).sum()
    cnt_by_bus = pd.Series(1, index=nearest_bus_idx).groupby(level=0).sum()
    assigned_pop.iloc[pop_by_bus.index] = pop_by_bus.values
    counts.iloc[cnt_by_bus.index] = cnt_by_bus.values

    total_pop = assigned_pop.sum()
    if total_pop <= 0:
        print("  - Assigned population is zero; falling back to equal shares")
        num_buses = len(buses)
        load_share = np.full(num_buses, 1.0 / num_buses)
    else:
        load_share = (assigned_pop / total_pop).values

    # Assemble output
    load_share_df = pd.DataFrame({
        'bus_id': buses['bus_id'].values,
        'load_share': load_share
    })

    # Normalize to ensure exact sum = 1 due to potential rounding
    load_share_df['load_share'] = load_share_df['load_share'] / load_share_df['load_share'].sum()

    # Save
    output_path = Path(output_dir) / iso3_code
    output_path.mkdir(parents=True, exist_ok=True)
    load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share.csv', index=False)
    print(f"  - Saved bus load share for {len(load_share_df)} buses")

    return load_share_df

def sparsify_by_demand_coverage(load_share_df, coverage_target=0.75, min_nodes=10, max_nodes=500):
    """
    Keep only enough buses to cover X% of total demand.
    Naturally finds the sweet spot between sparsity and accuracy.
    
    Parameters:
    -----------
    coverage_target : float
        Target demand coverage (0.80 = 80% of total demand)
    min_nodes : int
        Minimum nodes to keep even if coverage is met earlier
    max_nodes : int
        Maximum nodes even if coverage target not met
    """
    df = load_share_df.copy()
    
    # Sort by load share (descending)
    df_sorted = df.sort_values('load_share', ascending=False).reset_index(drop=True)
    
    # Calculate cumulative coverage
    df_sorted['cumulative_share'] = df_sorted['load_share'].cumsum()
    
    # Find cutoff point for target coverage
    coverage_mask = df_sorted['cumulative_share'] >= coverage_target
    
    if coverage_mask.any():
        # Number of nodes needed for target coverage
        nodes_for_coverage = coverage_mask.idxmax() + 1
    else:
        nodes_for_coverage = len(df_sorted)
    
    # Apply min/max constraints
    n_keep = max(min_nodes, min(nodes_for_coverage, max_nodes))
    
    # Get bus IDs to keep
    buses_to_keep = df_sorted.iloc[:n_keep]['bus_id'].values
    
    # Create sparse allocation
    df['sparse_load_share'] = 0.0
    mask = df['bus_id'].isin(buses_to_keep)
    df.loc[mask, 'sparse_load_share'] = df.loc[mask, 'load_share']
    
    # Renormalize to sum to 1
    total = df['sparse_load_share'].sum()
    if total > 0:
        df['sparse_load_share'] = df['sparse_load_share'] / total
    
    # Calculate statistics
    actual_coverage = df_sorted.iloc[:n_keep]['load_share'].sum()
    nonzero = (df['sparse_load_share'] > 0).sum()
    sparsity = 100 * (1 - nonzero/len(df))
    
    print(f"\n  Sparsification Results:")
    print(f"  - Target coverage: {coverage_target*100:.0f}%")
    print(f"  - Actual original demand covered: {actual_coverage*100:.1f}%")
    print(f"  - Nodes with demand: {nonzero}/{len(df)} ({100-sparsity:.1f}%)")
    print(f"  - Sparsity achieved: {sparsity:.1f}%")
    print(f"  - Top node share: {df_sorted.iloc[0]['load_share']*100:.1f}%")
    print(f"  - Smallest included node: {df_sorted.iloc[n_keep-1]['load_share']*100:.2f}%")
    
    # Show coverage progression
    print(f"\n  Coverage progression:")
    milestones = [1, 5, 10, 20, 30, 50, 100]
    for n in milestones:
        if n <= len(df_sorted):
            coverage = df_sorted.iloc[:n]['load_share'].sum()
            print(f"    Top {n:3d} nodes: {coverage*100:5.1f}% coverage")
    
    # Replace original load_share with sparse version
    df['load_share'] = df['sparse_load_share']
    df = df.drop('sparse_load_share', axis=1)
    
    return df, {
        'nodes_kept': nonzero,
        'sparsity_pct': sparsity,
        'coverage_pct': actual_coverage * 100,
        'buses_to_keep': buses_to_keep
    }

def compute_and_save_bus_load_share_voronoi(buses_gdf, iso2_code, iso3_code, pop_min=1000000, output_dir='output'):
    """Compute bus load share (0-1) per bus using Voronoi tessellation with country boundary clipping.
    
    Creates Voronoi cells around each bus, clips to country boundaries, and assigns cities
    to their respective cells based on spatial containment.
    
    Saves: output/<ISO3>/<ISO3>_bus_load_share_voronoi.csv with columns ['bus_id', 'load_share'].
    """
    print("Computing bus load share using Voronoi tessellation...")
    
    # Validate buses input
    if buses_gdf is None or buses_gdf.empty:
        print("  - No buses provided; skipping Voronoi load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    # Ensure we have coordinates
    buses = buses_gdf.copy()
    if 'y' in buses.columns and 'x' in buses.columns:
        buses_lat = buses['y']
        buses_lon = buses['x']
    elif 'latitude' in buses.columns and 'longitude' in buses.columns:
        buses_lat = buses['latitude']
        buses_lon = buses['longitude']
    elif 'geometry' in buses.columns:
        buses_lat = buses.geometry.y
        buses_lon = buses.geometry.x
    else:
        print("  - Missing coordinates on buses; skipping Voronoi load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    # Read worldcities
    cities_src = Path(BASE_INPUT_FILES['worldcities'])
    if not cities_src.exists():
        print(f"  - Cities file not found at {cities_src}; skipping Voronoi load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    try:
        cities_df = pd.read_csv(cities_src)
    except Exception as e:
        print(f"  - Error reading cities file: {e}")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    # Flexible column names
    lat_col = 'lat' if 'lat' in cities_df.columns else 'latitude'
    lon_col = 'lng' if 'lng' in cities_df.columns else ('lon' if 'lon' in cities_df.columns else 'longitude')
    pop_col = 'population'
    iso3_col = 'iso3' if 'iso3' in cities_df.columns else ('iso3_code' if 'iso3_code' in cities_df.columns else None)
    
    if iso3_col is None or pop_col not in cities_df.columns or lat_col not in cities_df.columns or lon_col not in cities_df.columns:
        print("  - Cities file missing required columns; skipping Voronoi load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    # Filter to country and pop threshold
    cities_country = cities_df[cities_df[iso3_col] == iso3_code]
    cities_country = cities_country.dropna(subset=[lat_col, lon_col, pop_col]).copy()
    cities_country = cities_country[cities_country[pop_col] >= pop_min]
    
    if cities_country.empty:
        print(f"  - No cities >= {pop_min} pop for {iso3_code}; falling back to equal shares")
        # Equal shares across buses
        num_buses = len(buses)
        if num_buses == 0:
            return pd.DataFrame(columns=["bus_id", "load_share"])
        load_share_df = pd.DataFrame({
            'bus_id': buses['bus_id'].values,
            'load_share': np.full(num_buses, 1.0 / num_buses)
        })
        output_path = Path(output_dir) / iso3_code
        output_path.mkdir(parents=True, exist_ok=True)
        load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share_voronoi.csv', index=False)
        print(f"  - Saved Voronoi bus load share (equal split) for {num_buses} buses")
        return load_share_df
    
    # Load country boundary
    countries_src = Path(BASE_INPUT_FILES['countries'])
    if not countries_src.exists():
        print(f"  - Countries file not found at {countries_src}; falling back to unbounded Voronoi")
        country_boundary = None
    else:
        try:
            countries_gdf = gpd.read_file(countries_src)
            # Filter to target country using ISO_A3 column
            country_mask = countries_gdf['ISO_A3'] == iso3_code
            if not country_mask.any():
                # Fallback: try ISO_A2 column
                country_mask = countries_gdf['ISO_A2'] == iso2_code
            
            if country_mask.any():
                country_boundary = countries_gdf[country_mask].geometry.iloc[0]
                print(f"  - Loaded country boundary for {iso3_code}")
            else:
                print(f"  - Country {iso3_code} not found in boundaries file; using unbounded Voronoi")
                country_boundary = None
        except Exception as e:
            print(f"  - Error loading country boundaries: {e}; using unbounded Voronoi")
            country_boundary = None
    
    # Check if scipy is available for Voronoi
    try:
        from scipy.spatial import Voronoi
        from shapely.geometry import Polygon, Point
        from shapely.ops import unary_union
    except ImportError:
        print("  - scipy or shapely unavailable; falling back to equal shares")
        num_buses = len(buses)
        load_share_df = pd.DataFrame({
            'bus_id': buses['bus_id'].values,
            'load_share': np.full(num_buses, 1.0 / num_buses)
        })
        output_path = Path(output_dir) / iso3_code
        output_path.mkdir(parents=True, exist_ok=True)
        load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share_voronoi.csv', index=False)
        print(f"  - Saved Voronoi bus load share (equal split) for {num_buses} buses")
        return load_share_df
    
    # Create Voronoi diagram
    bus_coords = np.column_stack([buses_lon.values, buses_lat.values])
    
    if len(bus_coords) < 2:
        print("  - Need at least 2 buses for Voronoi; falling back to equal shares")
        num_buses = len(buses)
        load_share_df = pd.DataFrame({
            'bus_id': buses['bus_id'].values,
            'load_share': np.full(num_buses, 1.0 / num_buses)
        })
        output_path = Path(output_dir) / iso3_code
        output_path.mkdir(parents=True, exist_ok=True)
        load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share_voronoi.csv', index=False)
        print(f"  - Saved Voronoi bus load share (equal split) for {num_buses} buses")
        return load_share_df
    
    try:
        voronoi = Voronoi(bus_coords)
    except Exception as e:
        print(f"  - Error creating Voronoi diagram: {e}; falling back to equal shares")
        num_buses = len(buses)
        load_share_df = pd.DataFrame({
            'bus_id': buses['bus_id'].values,
            'load_share': np.full(num_buses, 1.0 / num_buses)
        })
        output_path = Path(output_dir) / iso3_code
        output_path.mkdir(parents=True, exist_ok=True)
        load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share_voronoi.csv', index=False)
        print(f"  - Saved Voronoi bus load share (equal split) for {num_buses} buses")
        return load_share_df
    
    # Create Voronoi cell polygons and assign cities
    assigned_pop = pd.Series(0.0, index=buses.index)
    processed_buses = 0
    skipped_unbounded = 0
    
    for point_idx, bus_idx in enumerate(buses.index):
        # Get Voronoi cell for this bus
        region_idx = voronoi.point_region[point_idx]
        region = voronoi.regions[region_idx]
        
        if not region or -1 in region:
            # Unbounded region - skip these edge buses
            skipped_unbounded += 1
            continue
        else:
            # Bounded region - create polygon from vertices
            vertices = voronoi.vertices[region]
            if len(vertices) >= 3:
                cell_polygon = Polygon(vertices)
            else:
                continue
        
        processed_buses += 1
        
        # Clip to country boundary if available
        if country_boundary is not None:
            try:
                cell_polygon = cell_polygon.intersection(country_boundary)
                if cell_polygon.is_empty:
                    continue
            except Exception:
                # If intersection fails, use original cell
                pass
        
        # Find cities within this cell
        city_points = [Point(lon, lat) for lon, lat in 
                      zip(cities_country[lon_col], cities_country[lat_col])]
        
        cell_population = 0.0
        for i, city_point in enumerate(city_points):
            try:
                if cell_polygon.contains(city_point) or cell_polygon.touches(city_point):
                    cell_population += cities_country.iloc[i][pop_col]
            except Exception:
                # Skip problematic geometries
                continue
        
        assigned_pop.loc[bus_idx] = cell_population
    
    # Calculate load shares
    total_pop = assigned_pop.sum()
    if total_pop <= 0:
        print("  - No population assigned to any Voronoi cells; falling back to equal shares")
        num_buses = len(buses)
        load_share = np.full(num_buses, 1.0 / num_buses)
    else:
        load_share = (assigned_pop / total_pop).values
    
    # Assemble output
    load_share_df = pd.DataFrame({
        'bus_id': buses['bus_id'].values,
        'load_share': load_share
    })
    
    # Normalize to ensure exact sum = 1 due to potential rounding
    load_share_df['load_share'] = load_share_df['load_share'] / load_share_df['load_share'].sum()
    

    load_share_df, sparsity_info = sparsify_by_demand_coverage(load_share_df, coverage_target=0.80, min_nodes=10, max_nodes=500)
    print(f"  - Final Summary: {sparsity_info['nodes_kept']} nodes kept, {sparsity_info['sparsity_pct']:.1f}% sparsity, {sparsity_info['coverage_pct']:.1f}% coverage")
    
    # Save
    output_path = Path(output_dir) / iso3_code
    output_path.mkdir(parents=True, exist_ok=True)
    load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share_voronoi.csv', index=False)
    print(f"  - Saved Voronoi bus load share for {len(load_share_df)} buses")
    print(f"  - Processed {processed_buses} bounded Voronoi cells, skipped {skipped_unbounded} unbounded edge regions")
    
    return load_share_df


def compute_and_save_bus_load_share_wtddist(buses_gdf, iso2_code, iso3_code, pop_min=10000, 
                                           max_distance_km=100, decay_exponent=2.0, output_dir='output'):
    """Compute bus load share (0-1) per bus using distance-weighted assignment.
    
    Cities influence multiple buses based on inverse distance weighting. Closer buses
    receive higher weights, with influence decaying by distance^decay_exponent.
    
    Parameters:
    -----------
    max_distance_km : float, default 100
        Maximum influence distance in kilometers. Cities beyond this distance 
        from a bus have zero influence on that bus.
    decay_exponent : float, default 2.0
        Distance decay exponent. Higher values create steeper decay.
        - 1.0 = linear decay (1/distance)
        - 2.0 = quadratic decay (1/distance^2) - default
        - Higher values = more localized influence
    
    Saves: output/<ISO3>/<ISO3>_bus_load_share_wtddist.csv with columns ['bus_id', 'load_share'].
    """
    print(f"Computing bus load share using distance-weighted assignment (max_dist={max_distance_km}km, decay={decay_exponent})...")
    
    # Validate buses input
    if buses_gdf is None or buses_gdf.empty:
        print("  - No buses provided; skipping distance-weighted load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    # Ensure we have coordinates
    buses = buses_gdf.copy()
    if 'y' in buses.columns and 'x' in buses.columns:
        buses_lat = buses['y']
        buses_lon = buses['x']
    elif 'latitude' in buses.columns and 'longitude' in buses.columns:
        buses_lat = buses['latitude']
        buses_lon = buses['longitude']
    elif 'geometry' in buses.columns:
        buses_lat = buses.geometry.y
        buses_lon = buses.geometry.x
    else:
        print("  - Missing coordinates on buses; skipping distance-weighted load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    # Read worldcities
    cities_src = Path(BASE_INPUT_FILES['worldcities'])
    if not cities_src.exists():
        print(f"  - Cities file not found at {cities_src}; skipping distance-weighted load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    try:
        cities_df = pd.read_csv(cities_src)
    except Exception as e:
        print(f"  - Error reading cities file: {e}")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    # Flexible column names
    lat_col = 'lat' if 'lat' in cities_df.columns else 'latitude'
    lon_col = 'lng' if 'lng' in cities_df.columns else ('lon' if 'lon' in cities_df.columns else 'longitude')
    pop_col = 'population'
    iso3_col = 'iso3' if 'iso3' in cities_df.columns else ('iso3_code' if 'iso3_code' in cities_df.columns else None)
    
    if iso3_col is None or pop_col not in cities_df.columns or lat_col not in cities_df.columns or lon_col not in cities_df.columns:
        print("  - Cities file missing required columns; skipping distance-weighted load share computation")
        return pd.DataFrame(columns=["bus_id", "load_share"])
    
    # Filter to country and pop threshold
    cities_country = cities_df[cities_df[iso3_col] == iso3_code]
    cities_country = cities_country.dropna(subset=[lat_col, lon_col, pop_col]).copy()
    cities_country = cities_country[cities_country[pop_col] >= pop_min]
    
    if cities_country.empty:
        print(f"  - No cities >= {pop_min} pop for {iso3_code}; falling back to equal shares")
        # Equal shares across buses
        num_buses = len(buses)
        if num_buses == 0:
            return pd.DataFrame(columns=["bus_id", "load_share"])
        load_share_df = pd.DataFrame({
            'bus_id': buses['bus_id'].values,
            'load_share': np.full(num_buses, 1.0 / num_buses)
        })
        output_path = Path(output_dir) / iso3_code
        output_path.mkdir(parents=True, exist_ok=True)
        load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share_wtddist.csv', index=False)
        print(f"  - Saved distance-weighted bus load share (equal split) for {num_buses} buses")
        return load_share_df
    
    # Check if sklearn is available for distance calculations
    if not SKLEARN_AVAILABLE:
        print("  - scikit-learn unavailable; falling back to equal shares")
        num_buses = len(buses)
        load_share_df = pd.DataFrame({
            'bus_id': buses['bus_id'].values,
            'load_share': np.full(num_buses, 1.0 / num_buses)
        })
        output_path = Path(output_dir) / iso3_code
        output_path.mkdir(parents=True, exist_ok=True)
        load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share_wtddist.csv', index=False)
        print(f"  - Saved distance-weighted bus load share (equal split) for {num_buses} buses")
        return load_share_df
    
    # Calculate distances between all cities and buses using BallTree
    bus_coords_rad = np.radians(np.column_stack([buses_lat.values, buses_lon.values]))
    city_coords_rad = np.radians(cities_country[[lat_col, lon_col]].values)
    
    # Build BallTree for efficient distance calculation
    tree = BallTree(bus_coords_rad, metric='haversine')
    
    # Initialize weighted population assignment
    weighted_pop = pd.Series(0.0, index=buses.index)
    
    # Process each city
    for city_idx in range(len(cities_country)):
        city_pop = cities_country.iloc[city_idx][pop_col]
        city_coord = city_coords_rad[city_idx:city_idx+1]  # Single city coordinate
        
        # Get distances from this city to all buses
        distances_rad, bus_indices = tree.query(city_coord, k=len(buses))
        distances_km = distances_rad[0] * 6371  # Convert to km, get first (and only) row
        bus_indices = bus_indices[0]  # Get first (and only) row
        
        # Calculate weights based on inverse distance with cutoff
        total_weight = 0.0
        city_weights = {}  # Map from bus_index to weight
        
        for i in range(len(buses)):
            bus_tree_idx = bus_indices[i]  # Index in the BallTree (position in buses dataframe)
            distance = distances_km[i]     # Distance to this bus
            bus_idx = buses.index[bus_tree_idx]  # Actual bus index (e.g., 'cluster_0')
            
            if distance <= max_distance_km:
                if distance < 0.1:  # Avoid division by zero for very close points
                    weight = 1.0 / (0.1 ** decay_exponent)
                else:
                    weight = 1.0 / (distance ** decay_exponent)
                
                city_weights[bus_idx] = weight
                total_weight += weight
        
        # Normalize weights and distribute city population
        if total_weight > 0:
            for bus_idx, weight in city_weights.items():
                normalized_weight = weight / total_weight
                weighted_pop.loc[bus_idx] += city_pop * normalized_weight
    
    # Calculate load shares
    total_pop = weighted_pop.sum()
    if total_pop <= 0:
        print("  - No population assigned to any buses; falling back to equal shares")
        num_buses = len(buses)
        load_share = np.full(num_buses, 1.0 / num_buses)
    else:
        load_share = (weighted_pop / total_pop).values
    
    # Assemble output
    load_share_df = pd.DataFrame({
        'bus_id': buses['bus_id'].values,
        'load_share': load_share
    })
    
    # Normalize to ensure exact sum = 1 due to potential rounding
    load_share_df['load_share'] = load_share_df['load_share'] / load_share_df['load_share'].sum()
    
    # Save
    output_path = Path(output_dir) / iso3_code
    output_path.mkdir(parents=True, exist_ok=True)
    load_share_df.to_csv(output_path / f'{iso3_code}_bus_load_share_wtddist.csv', index=False)
    print(f"  - Saved distance-weighted bus load share for {len(load_share_df)} buses")
    
    return load_share_df


def compute_and_save_industry_load_share(buses_gdf, country_code, iso3_code, output_dir='output'):

    """
    Calculate industrial demand distribution factors for buses.
    
    Enhanced version with industry-specific weighting to account for
    electricity-intensive but low-emission industries like aluminum.
    Based on PyPSA-Eur's build_industrial_distribution_key.py methodology.
    
    Parameters
    ----------
    buses_gdf : gpd.GeoDataFrame
        GeoDataFrame containing bus information
    country_code : str
        Country code
    iso3_code : str
        ISO3 code
    """
    print("Calculating industrial distribution factors...")
    
    # Download industrial facility data
    hotmaps_data = download_hotmaps_database(cache_dir='../data')
    # gem_steel_data = download_gem_steel_data(cache_dir='_data')
    
    # Define industry-specific weighting factors
    # Higher weights for electricity-intensive industries that might be underweighted by emissions
    industry_weights = {
        'Non-ferrous metals': 5.0,      # High electricity (aluminum, copper, etc.)
        'Iron and steel': 3.0,          # High emissions + electricity
        'Chemical industry': 2.5,       # Mixed - some high electricity processes
        'Glass': 2.0,                   # High temperature processes
        'Cement': 2.0,                  # High emissions + electricity
        'Paper and printing': 1.5,      # Moderate electricity
        'Refineries': 1.0,              # Standard weight
        'Non-metallic mineral products': 1.0,  # Standard weight
        'Other non-classified': 1.0     # Standard weight
    }
    
    factors_by_country = {}
    
    print(f"Processing industrial factors for country: {country_code}")
    
    # Get bus regions for this country
    # country_buses = buses_gdf[buses_gdf.country == country].copy()
    country_buses = buses_gdf.copy()
    
    # Ensure CRS is set
    if country_buses.crs is None:
        country_buses = country_buses.set_crs(GEO_CRS)


    # Pick a local metric CRS (UTM) based on the buses' centroid for accurate distances
    centroid_ll = country_buses.to_crs(GEO_CRS).unary_union.centroid
    lon, lat = centroid_ll.x, centroid_ll.y
    utm_zone = int(np.floor((lon + 180.0) / 6.0) + 1)
    utm_hem = 326 if lat >= 0 else 327
    metric_crs = f"EPSG:{utm_hem}{utm_zone:02d}"

    # Project geometries used for distance calculations
    buses_proj = country_buses.to_crs(metric_crs)


    if len(country_buses) == 1:
        # Single bus per country - assign all load to it
        factors = pd.Series(1.0, index=country_buses.index)
    else:
        # Initialize factors with small epsilon
        factors = pd.Series(1e-6, index=country_buses.index)
        
        # Method 1: Use Hotmaps facility data with industry-specific weighting (EU countries)
        if not hotmaps_data.empty and country_code in hotmaps_data.country.unique():
            country_facilities = hotmaps_data[hotmaps_data.country == country_code]
            print(f"Found {len(country_facilities)} Hotmaps facilities in {country_code}")
            
            # Process each subsector separately with appropriate weighting
            for subsector in country_facilities.Subsector.unique():
                subsector_facilities = country_facilities[
                    country_facilities.Subsector == subsector
                ]
                
                if not subsector_facilities.empty:
                    # Get weight for this subsector
                    weight = industry_weights.get(subsector, 1.0)
                    # print(f"Processing {subsector} with weight {weight}")
                    
                    # Assign each facility to the nearest bus (since buses are always points)
                    # This handles cases with very few buses better than buffer intersection
                    facility_bus_assignments = {}
                    
                    for idx, facility in subsector_facilities.iterrows():
                        facility_point = facility.geometry
                        
                        # Calculate distances to all buses in metric CRS
                        distances = buses_proj.geometry.distance(gpd.GeoSeries([facility_point], crs=country_buses.crs).to_crs(buses_proj.crs).iloc[0])
                        nearest_bus_idx = distances.idxmin()
                        
                        facility_bus_assignments[idx] = nearest_bus_idx
                    
                    # Create a mapping DataFrame for aggregation
                    assignment_df = pd.DataFrame.from_dict(
                        facility_bus_assignments, 
                        orient='index', 
                        columns=['nearest_bus']
                    )
                    assignment_df.index.name = 'facility_idx'
                    
                    # Aggregate facility metrics by nearest bus
                    if 'Emissions_ETS_2014' in subsector_facilities.columns:
                        emissions_data = subsector_facilities['Emissions_ETS_2014'].fillna(0)
                        emissions_by_bus = assignment_df.join(emissions_data).groupby('nearest_bus')['Emissions_ETS_2014'].sum()
                        # Apply industry-specific weight to emissions
                        weighted_emissions = emissions_by_bus * weight
                        # Only add for indices that exist in factors
                        for bus_idx in weighted_emissions.index:
                            if bus_idx in factors.index:
                                factors.loc[bus_idx] += weighted_emissions.loc[bus_idx]
                    
                    # Add facility count with industry-specific weight
                    facility_count = assignment_df.groupby('nearest_bus').size()
                    # Only add for indices that exist in factors
                    for bus_idx in facility_count.index:
                        if bus_idx in factors.index:
                            factors.loc[bus_idx] += facility_count.loc[bus_idx] * (0.1 * weight)
        
        # Method 2: Add GEM steel data (global coverage)
        # if not gem_steel_data.empty and country in gem_steel_data.country.unique():
        #     country_steel = gem_steel_data[gem_steel_data.country == country]
        #     logger.info(f"Found {len(country_steel)} GEM steel plants in {country}")
            
        #     # Assign each steel plant to the nearest bus (consistent with facility approach)
        #     steel_bus_assignments = {}
            
        #     for idx, steel_plant in country_steel.iterrows():
        #         plant_point = steel_plant.geometry
                
        #         # Calculate distances to all buses in metric CRS
        #         distances = buses_proj.geometry.distance(gpd.GeoSeries([plant_point], crs=country_buses.crs).to_crs(buses_proj.crs).iloc[0])
        #         nearest_bus_idx = distances.idxmin()
                
        #         steel_bus_assignments[idx] = nearest_bus_idx
            
        #     # Create a mapping DataFrame for aggregation
        #     steel_assignment_df = pd.DataFrame.from_dict(
        #         steel_bus_assignments, 
        #         orient='index', 
        #         columns=['nearest_bus']
        #     )
        #     steel_assignment_df.index.name = 'plant_idx'
            
        #     # Aggregate steel plant metrics by nearest bus
        #     if 'Steel Production Capacity (ttpa)' in country_steel.columns:
        #         capacity_data = country_steel['Steel Production Capacity (ttpa)'].fillna(0)
        #         capacity_by_bus = steel_assignment_df.join(capacity_data).groupby('nearest_bus')['Steel Production Capacity (ttpa)'].sum()
        #         factors.loc[capacity_by_bus.index] += capacity_by_bus * 0.5
        #     else:
        #         # Fallback to plant count
        #         plant_count = steel_assignment_df.groupby('nearest_bus').size()
        #         factors.loc[plant_count.index] += plant_count * 0.2
        
        # Method 3: Fallback to GDP-based distribution
        if factors.sum() <= len(factors) * 1e-6:  # If no facilities found
            print(f"No industrial facilities found for {country_code}, using GDP fallback")
            nuts_geojson = Path(BASE_INPUT_FILES['nuts_geojson'])
            gdp_data = Path(BASE_INPUT_FILES['gdp_data'])
            pop_data = Path(BASE_INPUT_FILES['pop_data'])
            

            regions = process_nuts3_regions(
                country_codes=country_code,
                gdp_year=2019,
                pop_year=2019,
                nuts3_shapefile_path=nuts_geojson,
                nuts3_gdp_csv_path=gdp_data if Path(gdp_data).exists() else None,
                nuts3_pop_csv_path=pop_data if Path(pop_data).exists() else None
            )

            if regions.empty:
                print(f"No NUTS3 regions found for {country_code}, distributing equally across {len(country_buses)} buses")
                factors = pd.Series(1.0, index=country_buses.index)
            else:

                country_regions = regions[regions.country == country_code].copy()
                        
                if country_regions.crs is None:
                    country_regions = country_regions.set_crs(GEO_CRS)

                # If no regional shapes or GDP available (e.g., non-European countries),
                # distribute equally across available buses
                if country_regions.empty or ('gdp' not in country_regions.columns) or country_regions['gdp'].dropna().empty:
                    print(f"No regional GDP data for {country_code}; distributing equally across {len(country_buses)} buses")
                    factors = pd.Series(1.0, index=country_buses.index)
                else:
                    # Use regional GDP as proxy - assign each region to nearest bus (projected CRS)
                    region_bus_assignments = {}
                    regions_proj = country_regions.to_crs(metric_crs)
                    for idx, region in regions_proj.iterrows():
                        region_centroid = region.geometry.centroid
                        # Calculate distances to all buses in metric CRS
                        distances = buses_proj.geometry.distance(region_centroid)
                        nearest_bus_idx = distances.idxmin()
                        region_bus_assignments[idx] = nearest_bus_idx
                    
                    # Create a mapping DataFrame for aggregation
                    region_assignment_df = pd.DataFrame.from_dict(
                        region_bus_assignments, 
                        orient='index', 
                        columns=['nearest_bus']
                    )
                    region_assignment_df.index.name = 'region_idx'
                    
                    # Aggregate GDP by nearest bus
                    gdp_data = country_regions['gdp'].fillna(1.0)
                    gdp_by_bus = region_assignment_df.join(gdp_data).groupby('nearest_bus')['gdp'].sum()
                    factors = gdp_by_bus.reindex(country_buses.index, fill_value=0.0)
        
        # Normalize factors
        factors = factors / factors.sum()
    # Ensure output is a DataFrame with columns ['bus_id', 'load_share']
    factors_df = pd.DataFrame({
        'bus_id': country_buses['bus_id'].values,
        'load_share': factors.values
    })
    output_path = Path(output_dir) / iso3_code
    output_path.mkdir(parents=True, exist_ok=True)
    factors_df.to_csv(output_path / f'{iso3_code}_industry_load_share.csv', index=False)
    
    return factors_df



def save_network_data(zone_mapping, power_plants, country_code, iso3_code, buses_gdf, lines_df, output_dir='output'):
    """Save zone mapping, power plant assignment data, and original network data for visualization"""
    print("Saving zone mapping, power plant data, and network data...")
    
    # Create output directory with ISO3 subdirectory
    output_path = Path(output_dir) / iso3_code
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save zone mapping (always save)
    zone_mapping.to_csv(output_path / f'{iso3_code}_zone_bus_mapping.csv', index=False)
    print(f"  - Saved zone mapping: {len(zone_mapping)} entries")
    
    # Save power plant assignments if available
    if not power_plants.empty:
        power_plants.to_csv(output_path / f'{iso3_code}_power_plants_assigned_to_buses.csv', index=False)
        print(f"  - Saved power plant assignments: {len(power_plants)} plants")
    else:
        print("  - No power plant data to save")
    
    # Save original buses data for visualization (as "clustered_buses" to maintain compatibility)
    if buses_gdf is not None and not buses_gdf.empty:
        buses_df = buses_gdf.copy()
        if 'geometry' in buses_df.columns:
            buses_df = buses_df.drop('geometry', axis=1)
        # Save with index for compatibility with visualization script
        buses_df.to_csv(output_path / f'{iso3_code}_clustered_buses.csv', index=False)
        print(f"  - Saved original buses: {len(buses_df)} buses")
    
    # Save original lines data for visualization (as "clustered_lines" to maintain compatibility)
    if lines_df is not None and not lines_df.empty:
        lines_df.to_csv(output_path / f'{iso3_code}_clustered_lines.csv', index=False)
        print(f"  - Saved original lines: {len(lines_df)} lines")

def map_plants_to_original_buses(country_code, iso3_code, buses_gdf, iso_processor=None):
    """Map power plants to original buses using spatial proximity"""
    print("Mapping power plants to buses...")
    
    # Use cached GEM data from iso_processor if available
    if iso_processor is not None and hasattr(iso_processor, 'main') and hasattr(iso_processor.main, 'df_gem'):
        print(f"  - Using cached GEM data from iso_processor")
        df_plants = iso_processor.main.df_gem[iso_processor.main.df_gem['iso_code'] == iso_processor.input_iso]
        country_plants = filter_gem_data_by_status(df_plants, include_announced=True, include_preconstruction=True)
    else:
        # Fallback to direct file loading
        gem_src = REPO_ROOT / 'data/existing_stock/Global-Integrated-Power-April-2025.xlsx'
        if not gem_src.exists():
            print(f"  - GEM data file not found: {gem_src}")
            return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
        
        try:
            df_plants = pd.read_excel(gem_src, sheet_name=GEM_SHEET_NAME)
            print(f"  - Loaded {len(df_plants)} power facilities from GEM data")
            
            # Filter for active plants using centralized function
            df_plants = filter_gem_data_by_status(df_plants, include_announced=True, include_preconstruction=True)
            
            # Add iso_code column using the get_iso_code function
            print(f"  - Adding ISO codes to power plants data...")
            df_plants['iso_code'] = df_plants['Country/area'].apply(get_iso_code)
            
            # Filter by country using iso_code
            country_plants = df_plants[df_plants['iso_code'] == iso3_code]
        except Exception as e:
            print(f"  - Error loading GEM data: {e}")
            return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    
    if country_plants.empty:
        print(f"  - No plants found for country: {iso3_code}")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    print(f"  - Found {len(country_plants)} plants in {iso3_code}")
    
    # Filter to plants with valid coordinates
    plants_with_coords = country_plants[
        country_plants['Latitude'].notna() & 
        country_plants['Longitude'].notna() &
        (country_plants['Latitude'] != 0) & 
        (country_plants['Longitude'] != 0)
    ]
    
    if plants_with_coords.empty:
        print("  - No plants with valid coordinates")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    df_plants_clean = plants_with_coords.copy()
    print(f"  - {len(df_plants_clean)} plants have valid coordinates")
    
    # Use provided buses_gdf
    if buses_gdf is None or buses_gdf.empty:
        print("  - No buses provided")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    # Clean invalid coordinates from buses
    buses_clean = buses_gdf[
        buses_gdf['x'].notna() & 
        buses_gdf['y'].notna() &
        (buses_gdf['x'] != 0) & 
        (buses_gdf['y'] != 0)
    ]
    
    print(f"  - {len(buses_clean)} buses have valid coordinates")
    
    if buses_clean.empty:
        print("  - No buses with valid coordinates found")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    # Perform spatial assignment using BallTree (if available)
    if not SKLEARN_AVAILABLE:
        print("  - scikit-learn not available, returning empty mapping")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])
    
    try:
        # Convert coordinates to radians for BallTree (longitude=x, latitude=y)
        bus_coords_rad = np.radians(buses_clean[['y', 'x']].values)  # lat, lon order for BallTree
        plant_coords_rad = np.radians(df_plants_clean[['Latitude', 'Longitude']].values)
        
        # Create BallTree for efficient nearest neighbor search
        tree = BallTree(bus_coords_rad, metric='haversine')
        
        # Find nearest bus for each power plant
        distances, indices = tree.query(plant_coords_rad, k=1)
        
        # Convert distances from radians to kilometers
        distances_km = distances.flatten() * 6371  # Earth's radius in km
        nearest_bus_indices = indices.flatten()
        nearest_bus_ids = buses_clean.iloc[nearest_bus_indices]['bus_id'].values
        
        # Create mapping dataframe
        plant_bus_mapping = pd.DataFrame({
            'GEM location ID': df_plants_clean['GEM location ID'].values,
            'bus_id': nearest_bus_ids
        })
        
        # DEDUPLICATION: Keep unique power plants only (first occurrence)
        initial_count = len(plant_bus_mapping)
        plant_bus_mapping = plant_bus_mapping.drop_duplicates(subset=['GEM location ID'], keep='first')
        final_count = len(plant_bus_mapping)
        
        if initial_count != final_count:
            print(f"  - Removed {initial_count - final_count} duplicate power plants (kept unique GEM location IDs)")
        
        print(f"  - Successfully mapped {final_count} unique power plants to buses")
        print(f"  - Average distance to nearest bus: {distances_km.mean():.2f} km")
        print(f"  - Maximum distance to nearest bus: {distances_km.max():.2f} km")
        
        return plant_bus_mapping
        
    except Exception as e:
        print(f"Error during spatial assignment: {e}")
        return pd.DataFrame(columns=['GEM location ID', 'bus_id'])

def process_single_country(iso2_code, iso3_code, iso_processor=None, data_source='eur', output_dir='output'):
    """Process a single country using original network data (no clustering) from specified data source"""
    
    print(f"\n=== {iso2_code} Network Extraction from {data_source} dataset ===")

    # Load zones for the country (always use parquet files for geometry)
    print("Loading zone geometries from parquet files...")
    onshore_zones_gdf = load_zones_for_country(iso2_code, 'onshore')
    mainland_result = identify_disconnected_regions(onshore_zones_gdf, iso3_code, plot=False)
    mainland_grid_cells = mainland_result['main_continental_grid_cells']
    mainland_bounds = mainland_result['main_bounds']
    if len(mainland_grid_cells) > 0:
        onshore_zones_gdf = onshore_zones_gdf[onshore_zones_gdf['grid_cell'].isin(mainland_grid_cells)]
    
    offshore_zones_gdf = load_zones_for_country(iso2_code, 'offshore')
    zones_gdf = pd.concat([onshore_zones_gdf, offshore_zones_gdf], ignore_index=True)
    
    print(f"  - Loaded {len(onshore_zones_gdf)} onshore + {len(offshore_zones_gdf)} offshore zones with geometry")
    
    if zones_gdf.empty:
        print("- No zones found for the specified country")
        return False
    
    # Load atlite data for renewable clustering
    atlite_df_iso= load_atlite_data_for_country(iso2_code, iso3_code, iso_processor)
    
    # Initialize renewable clustering outputs
    # renewable_cell_mapping = pd.DataFrame()
    
    # Perform renewable energy clustering if data is available
    if RE_CLUSTERING_AVAILABLE and not atlite_df_iso.empty and not onshore_zones_gdf.empty:
        print("\n=== Renewable Energy Clustering ===")
        try:
            # Step 1: Reshape atlite data
            atlite_reshaped, unique_cells = load_and_reshape_atlite(atlite_df_iso, year=2013)
            
            # Step 2: Extract cell profiles
            # Prepare zones data similar to how re_clustering_1.py does it
            print("Preparing zones data for renewable clustering...")
            
            # Add required columns to zones_gdf if they don't exist
            if 'lat' not in zones_gdf.columns or 'lon' not in zones_gdf.columns:
                if 'centroid_lat' in zones_gdf.columns and 'centroid_lon' in zones_gdf.columns:
                    # Use existing centroid coordinates
                    zones_gdf['lat'] = zones_gdf['centroid_lat']
                    zones_gdf['lon'] = zones_gdf['centroid_lon']
                elif hasattr(zones_gdf, 'geometry') and not zones_gdf.geometry.empty:
                    # Calculate centroids from geometry
                    zones_gdf['centroid'] = zones_gdf.geometry.centroid
                    zones_gdf['lon'] = zones_gdf.centroid.x
                    zones_gdf['lat'] = zones_gdf.centroid.y
                else:
                    print("  - Warning: No geometry or coordinate columns found in zones data")
                    # Create dummy coordinates (this shouldn't happen in practice)
                    zones_gdf['lat'] = 0
                    zones_gdf['lon'] = 0
            
            # Add grid_cell column if it doesn't exist (needed by extract_cell_profiles)
            if 'grid_cell' not in zones_gdf.columns:
                # Create grid_cell identifiers based on zone IDs or indices
                if 'id' in zones_gdf.columns:
                    zones_gdf['grid_cell'] = zones_gdf['id'].astype(str)
                else:
                    zones_gdf['grid_cell'] = [f"zone_{i}" for i in range(len(zones_gdf))]
            
            print(f"  - Prepared {len(zones_gdf)} zones with lat/lon coordinates")
            
            profiles  = extract_cell_profiles(atlite_reshaped, zones_gdf,iso_processor)
            """
            'profiles_won','profiles_solar','profiles_offwind'
            Each of these with: 'cells','coords','re_profile_df'
            AND
            'mw_wt'
            """
            
            main_output_path = Path(output_dir) / iso3_code
            main_output_path.mkdir(parents=True, exist_ok=True)

            # Step 3: Process grid infrastructure for clustering
            # Load network components
            components = load_network_components(iso2_code, data_source, mainland_bounds)
            country_buses = components['buses']
            lines_df = components.get('lines', pd.DataFrame())

            buses_processed, transmission_buses = re_process_grid_infrastructure(country_buses, lines_df)


            # Wind onshore clustering  
            print(f"\nRunning wind onshore clustering...")
            wind_clusters, wind_cluster_stats, wind_linkage_matrix, wind_clustering_info, wind_cell_mapping = smart_clustering_pipeline(
                profiles['profiles_won'], transmission_buses,
                iso3_code=iso3_code,
                technology='wind_onshore',
                output_dir=str(main_output_path)
            )
            # Generate wind visualization
            re_visualize_and_export(
                wind_clusters, profiles['profiles_won'], wind_cluster_stats, transmission_buses, 
                zones_gdf, iso3_code, wind_clustering_info, str(main_output_path), technology='wind_onshore'
            )
            # Wind weighted profiles using wind clusters
            wind_weighted_profiles = calculate_weighted_cluster_profiles_2(
                wind_clusters, profiles['profiles_won'], 'wind_onshore'
            )
            export_cluster_timeseries(wind_weighted_profiles, 'wind_onshore', main_output_path)

            # Wind offshore clustering
            if offshore_zones_gdf.empty:
                print("! No offshore zones found, skipping wind offshore clustering")
            else:
                print(f"\nRunning wind offshore clustering...")
                wind_offshore_clusters, wind_offshore_cluster_stats, wind_offshore_linkage_matrix, wind_offshore_clustering_info, wind_offshore_cell_mapping = smart_clustering_pipeline(
                    profiles['profiles_offwind'], transmission_buses,
                    iso3_code=iso3_code,
                    technology='wind_offshore',
                    output_dir=str(main_output_path)
                )
                # Generate wind off visualization
                re_visualize_and_export(
                    wind_offshore_clusters, profiles['profiles_offwind'], wind_offshore_cluster_stats, transmission_buses, 
                    zones_gdf, iso3_code, wind_offshore_clustering_info, str(main_output_path), technology='wind_offshore'
                )
                # Wind off weighted profiles using wind off clusters
                wind_off_weighted_profiles = calculate_weighted_cluster_profiles_2(
                    wind_offshore_clusters, profiles['profiles_offwind'], 'wind_offshore'
                )
                export_cluster_timeseries(wind_off_weighted_profiles, 'wind_offshore', main_output_path)

            # clustering solar
                                        
            # Solar clustering
            print(f"\nRunning solar clustering...")
            solar_clusters, solar_cluster_stats, solar_linkage_matrix, solar_clustering_info, solar_cell_mapping = smart_clustering_pipeline(
                profiles['profiles_solar'], transmission_buses,
                iso3_code=iso3_code,
                technology='solar',
                output_dir=str(main_output_path)
            )
            # Generate solar visualization
            re_visualize_and_export(
                solar_clusters, profiles['profiles_solar'], solar_cluster_stats, transmission_buses, 
                zones_gdf, iso3_code, solar_clustering_info, str(main_output_path), technology='solar'
            )
            
            # wtd avg profiles
            # Step 5: Create and export renewable clustering results
            # Output directory already created above
            
            # Calculate separate weighted cluster profiles for each technology
            
            # Solar weighted profiles using solar clusters
            solar_weighted_profiles = calculate_weighted_cluster_profiles_2(
                solar_clusters, profiles['profiles_solar'], 'solar'
            )
            # Export solar timeseries using the new tech-neutral function
            export_cluster_timeseries(solar_weighted_profiles, 'solar', main_output_path)

            
            # print(f"✅ Renewable clustering complete: {len(np.unique(clusters))} clusters created")
            print(f"   - Cell mapping includes nearest_bus_id for zone-to-bus integration")
            
            # For cities-based clustering, return early after RE clustering is complete
            if data_source == 'cit':
                # Save city-buses data as clustered_buses.csv for downstream tools
                try:
                    output_path = Path(output_dir) / iso3_code
                    output_path.mkdir(parents=True, exist_ok=True)
                    
                    # Save transmission_buses (city-buses) as clustered_buses.csv
                    if transmission_buses is not None and not transmission_buses.empty:
                        buses_df = transmission_buses.copy()
                        if 'geometry' in buses_df.columns:
                            buses_df = buses_df.drop('geometry', axis=1)
                        buses_df.to_csv(output_path / f'{iso3_code}_clustered_buses.csv', index=False)
                        print(f"  - Saved city-buses data: {len(buses_df)} cities as clustered_buses.csv")
                    
                    # Create empty lines file for consistency
                    empty_lines = pd.DataFrame(columns=['bus0', 'bus1', 'voltage', 'length'])
                    empty_lines.to_csv(output_path / f'{iso3_code}_clustered_lines.csv', index=False)
                    print(f"  - Created empty clustered_lines.csv (no transmission lines for cities)")
                    
                except Exception as save_error:
                    print(f"  ⚠️ Could not save city-buses data: {save_error}")
                
                print(f"+ Cities-based RE clustering completed for {iso2_code}!")
                print(f"Output files saved in: {output_dir}/{iso3_code}/")
                return True
        except Exception as e:
            print(f"! Renewable clustering failed: {e}")
            print("   Continuing with standard zone-to-bus mapping...")
    else:
        if not RE_CLUSTERING_AVAILABLE:
            print("! Renewable clustering functions not available")
        elif atlite_df_iso.empty:
            print("! No atlite data available for renewable clustering")
        elif onshore_zones_gdf.empty:
            print("! No onshore zones available for renewable clustering")
        print("   Using standard zone-to-bus mapping only...")
    


    # Convert buses to GeoDataFrame for spatial operations
    buses_gdf = gpd.GeoDataFrame(
        country_buses,
        geometry=gpd.points_from_xy(country_buses['x'], country_buses['y']),
        crs='EPSG:4326'
    )
    
    print(f"Using original network data: {len(buses_gdf)} buses, {len(lines_df)} lines")
    
    # Perform zone-to-bus mapping using original buses
    bus_zones = perform_zone_to_bus_mapping(buses_gdf, zones_gdf)
    
    # Select only the needed columns
    bus_zones = bus_zones[['bus_id', 'grid_cell']]
    
    # DEDUPLICATION: Keep unique buses only (first zone encountered)
    initial_count = len(bus_zones)
    bus_zones = bus_zones.drop_duplicates(subset=['bus_id', 'grid_cell'], keep='first')
    final_count = len(bus_zones)
    
    if initial_count != final_count:
        print(f"  - Removed {initial_count - final_count} duplicate bus entries in zone mapping (kept unique bus_ids)")
    
    print(f"  - Final zone mapping: {final_count} unique buses")
    
    
    # Compute and save bus load share using original buses (population >=10k, hard nearest)
    compute_and_save_bus_load_share(buses_gdf, iso2_code, iso3_code, pop_min=10000, output_dir=output_dir)
    compute_and_save_bus_load_share_voronoi(buses_gdf, iso2_code, iso3_code, pop_min=10000, output_dir=output_dir)
    compute_and_save_bus_load_share_wtddist(buses_gdf, iso2_code, iso3_code, pop_min=10000, output_dir=output_dir)
    compute_and_save_industry_load_share(buses_gdf, iso2_code, iso3_code, output_dir=output_dir)

    # Process power plants and assign to buses
    power_plants = map_plants_to_original_buses(iso2_code, iso3_code, buses_gdf, iso_processor=iso_processor)
    
    # Save original network data for visualization
    save_network_data(bus_zones, power_plants, iso2_code, iso3_code, buses_gdf, lines_df, output_dir)
    
    # Renewable clustering data is now saved by the re_visualize_and_export function
    # in the main output directory alongside other script outputs
    
    # Save the power plants assignments

    # power_plants.to_csv(f'output/{iso3_code}/{iso3_code}_power_plants_assigned_to_buses.csv', index=False)
    
    print(f"\nSuccessfully processed {iso2_code}!")
    # print(f"Zone mappings: {len(bus_zones)} entries")
    print(f"Network buses: {len(buses_gdf)} buses")
    print(f"Transmission lines: {len(lines_df)} lines")
    if not power_plants.empty:
        print(f"Power plants: {len(power_plants)} plants")
    
    # Generate enhanced SVG with actual GEM power plant data
    try:
        print("Generating enhanced SVG with GEM power plant data...")
        generate_enhanced_grid_svg(iso3_code, buses_gdf, lines_df, power_plants, pd.DataFrame(), iso_processor, output_dir)
        print("Enhanced SVG generated successfully")
    except Exception as e:
        print(f"Could not generate enhanced SVG: {e}")
    
    return True

def get_iso2_from_iso3(iso3_code):
    """Convert ISO3 code to ISO2 code"""
    try:
        if PYCOUNTRY_AVAILABLE:
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


def download_hotmaps_database(cache_dir: str = "../data") -> gpd.GeoDataFrame:
    """
    Download and process Hotmaps Industrial Database.
    
    Based on PyPSA-Eur's build_industrial_distribution_key.py
    
    Parameters
    ----------
    cache_dir : str
        Directory to cache downloaded data
        
    Returns
    -------
    gpd.GeoDataFrame
        Hotmaps facility data with geometry
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    hotmaps_file = cache_path / "Industrial_Database.csv"
    
    if not hotmaps_file.exists():
        print("Downloading Hotmaps Industrial Database...")
        hotmaps_url = "https://gitlab.com/hotmaps/industrial_sites/industrial_sites_Industrial_Database/-/raw/master/data/Industrial_Database.csv"
        
        try:
            response = requests.get(hotmaps_url, timeout=30)
            response.raise_for_status()
            
            with open(hotmaps_file, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded Hotmaps database to {hotmaps_file}")
            
        except Exception as e:
            print(f"Failed to download Hotmaps database: {e}")
            return gpd.GeoDataFrame()
    
    # Load and process Hotmaps data
    try:
        # Use semicolon separator like PyPSA-Eur
        hotmaps = pd.read_csv(hotmaps_file, sep=";", index_col=0)
        # print(f"Loaded {len(hotmaps)} facilities from Hotmaps database")
        
        # Process geometry column like PyPSA-Eur
        if 'geom' in hotmaps.columns:
            hotmaps[["srid", "coordinates"]] = hotmaps.geom.str.split(";", expand=True)
            
            # Remove facilities without valid coordinates
            hotmaps = hotmaps.dropna(subset=['coordinates'])
            
            # Parse coordinates (format: "POINT(longitude latitude)")
            coords_clean = hotmaps['coordinates'].str.replace('POINT(', '').str.replace(')', '')
            coords_split = coords_clean.str.split(' ', expand=True)
            
            if len(coords_split.columns) >= 2:
                hotmaps['Longitude'] = pd.to_numeric(coords_split[0], errors='coerce')
                hotmaps['Latitude'] = pd.to_numeric(coords_split[1], errors='coerce')
            else:
                print("Could not parse coordinates from geom column")
                return gpd.GeoDataFrame()
        
        # Filter valid coordinates
        valid_coords = (
            hotmaps['Longitude'].notna() & 
            hotmaps['Latitude'].notna() &
            (hotmaps['Longitude'] != 0) & 
            (hotmaps['Latitude'] != 0)
        )
        hotmaps = hotmaps[valid_coords].copy()
        
        # Create geometries
        hotmaps['geometry'] = [
            Point(lon, lat) for lon, lat in 
            zip(hotmaps['Longitude'], hotmaps['Latitude'])
        ]
        
        # Convert to GeoDataFrame
        hotmaps_gdf = gpd.GeoDataFrame(hotmaps, geometry='geometry', crs="EPSG:4326")
        
        # Standardize country codes
        if 'Country' in hotmaps_gdf.columns:
            hotmaps_gdf['country'] = hotmaps_gdf['Country'].apply(
                lambda x: cc.convert(names=x, to='ISO2') if pd.notna(x) else None
            )
        
        # print(f"Processed {len(hotmaps_gdf)} facilities with valid coordinates")
        return hotmaps_gdf
        
    except Exception as e:
        print(f"Error processing Hotmaps data: {e}")
        return gpd.GeoDataFrame()

    
def process_nuts3_regions(country_codes: Union[str, List[str]],
                            gdp_year: int,
                            pop_year: int,
                            nuts3_shapefile_path: str,
                            nuts3_gdp_csv_path: Optional[str] = None,
                            nuts3_pop_csv_path: Optional[str] = None) -> gpd.GeoDataFrame:
    """
    Process NUTS3 regions for specified country codes.
    
    Parameters
    ----------
    country_codes : str or list of str
        ISO country code(s) to process
    nuts3_shapefile_path : str
        Path to NUTS3 shapefile
    nuts3_gdp_csv_path : str, optional
        Path to NUTS3 GDP CSV file
    nuts3_pop_csv_path : str, optional
        Path to NUTS3 population CSV file
        
    Returns
    -------
    gpd.GeoDataFrame
        Processed NUTS3 regions with GDP and population data
    """
    # Ensure country_codes is a list
    if isinstance(country_codes, str):
        country_codes = [country_codes]
        
    # Normalize country codes to 2-letter ISO format
    country_codes = [cc.convert(names=code, to="ISO2") for code in country_codes]
    print(f"Processing NUTS3 regions for countries: {country_codes}")
    
    # Load NUTS3 shapefile
    print("Loading NUTS3 shapefile...")
    regions = gpd.read_file(nuts3_shapefile_path)
    
    # Standardize country codes in shapefile
    regions.loc[regions.CNTR_CODE == "EL", "CNTR_CODE"] = "GR"  # Greece
    regions["NUTS_ID"] = regions["NUTS_ID"].str.replace("EL", "GR")
    regions.loc[regions.CNTR_CODE == "UK", "CNTR_CODE"] = "GB"  # United Kingdom
    regions["NUTS_ID"] = regions["NUTS_ID"].str.replace("UK", "GB")
    
    # Filter for specified countries
    regions = regions[regions.CNTR_CODE.isin(country_codes)]
    
    if regions.empty:
        print(f"No NUTS3 regions found for countries: {country_codes}")
        return gpd.GeoDataFrame()
    
    # Create standardized dataframe
    regions = regions[["NUTS_ID", "CNTR_CODE", "NAME_LATN", "geometry"]]
    regions = regions.rename(
        columns={"NUTS_ID": "id", "CNTR_CODE": "country", "NAME_LATN": "name"}
    )
    
    # Normalize text
    regions["id"] = regions["id"].apply(normalise_text)
    regions["name"] = regions["name"].apply(normalise_text)
    
    # Add hierarchical level columns
    regions["level1"] = regions["id"].str[:3]
    regions["level2"] = regions["id"].str[:4]
    regions["level3"] = regions["id"]
    
    # Set index
    regions.set_index("id", inplace=True)
    
    # Process GDP data if provided
    if nuts3_gdp_csv_path and Path(nuts3_gdp_csv_path).exists():
        print(f"Loading GDP data for year {gdp_year}...")
        gdp_data = load_gdp_data(nuts3_gdp_csv_path, country_codes, gdp_year)
        gdp_data.name = "gdp"  # Rename the series to avoid conflicts
        regions = regions.join(gdp_data, how="left")
    else:
        print("GDP data not provided or file not found")
        regions["gdp"] = 0.0
        
    # Process population data if provided
    if nuts3_pop_csv_path and Path(nuts3_pop_csv_path).exists():
        print(f"Loading population data for year {pop_year}...")
        pop_data = load_population_data(nuts3_pop_csv_path, country_codes, pop_year)
        pop_data.name = "pop"  # Rename the series to avoid conflicts
        regions = regions.join(pop_data, how="left")
    else:
        print("Population data not provided or file not found")
        regions["pop"] = 0.0
        
    # Fill missing values
    regions["gdp"] = regions["gdp"].fillna(0.0)
    regions["pop"] = regions["pop"].fillna(0.0)
    
    # Reorder columns
    regions = regions[
        ["name", "level1", "level2", "level3", "gdp", "pop", "country", "geometry"]
    ]
    regions.index.name = "index"
    
    print(f"Successfully processed {len(regions)} NUTS3 regions")
    return regions


def load_gdp_data(gdp_csv_path: str, country_codes: List[str], gdp_year: int) -> pd.Series:
    """
    Load and process GDP data from CSV file.
    
    Based on PyPSA-Eur's build_shapes.py GDP processing logic.
    
    Parameters
    ----------
    gdp_csv_path : str
        Path to GDP CSV file
    country_codes : list of str
        Country codes to filter for
        
    Returns
    -------
    pd.Series
        GDP data indexed by NUTS3 code
    """
    try:
        gdp_data = pd.read_csv(gdp_csv_path, index_col=[0])
        
        # Filter for NUTS3 level and EUR currency
        if "LEVEL_ID" in gdp_data.columns:
            gdp_data = gdp_data.query("LEVEL_ID == 3")
        if "UNIT" in gdp_data.columns and "EUR" in gdp_data["UNIT"].unique():
            gdp_data = gdp_data.query("UNIT == 'EUR'")
            
        # Standardize country codes
        gdp_data.index = gdp_data.index.str.replace("UK", "GB").str.replace("EL", "GR")
        
        # Filter for specified countries
        country_filter = gdp_data.index.str[:2].isin(country_codes)
        gdp_data = gdp_data[country_filter]
        
        # Extract data for specified year
        if str(gdp_year) in gdp_data.columns:
            return gdp_data[str(gdp_year)]
        else:
            print(f"GDP data for year {gdp_year} not found")
            return pd.Series(index=gdp_data.index, data=0.0)
            
    except Exception as e:
        print(f"Error loading GDP data: {e}")
        return pd.Series(dtype=float)


def load_population_data(pop_csv_path: str, country_codes: List[str], pop_year: int) -> pd.Series:
        """
        Load and process population data from CSV file.
        
        Based on PyPSA-Eur's build_shapes.py population processing logic.
        
        Parameters
        ----------
        pop_csv_path : str
            Path to population CSV file
        country_codes : list of str
            Country codes to filter for
            
        Returns
        -------
        pd.Series
            Population data indexed by NUTS3 code
        """
        try:
            pop_data = pd.read_csv(pop_csv_path, index_col=[0])
            
            # Filter for NUTS3 level
            if "LEVEL_ID" in pop_data.columns:
                pop_data = pop_data.query("LEVEL_ID == 3")
                
            # Standardize country codes
            pop_data.index = pop_data.index.str.replace("UK", "GB").str.replace("EL", "GR")
            
            # Filter for specified countries
            country_filter = pop_data.index.str[:2].isin(country_codes)
            pop_data = pop_data[country_filter]
            
            # Extract data for specified year
            if str(pop_year) in pop_data.columns:
                # Convert from thousands to actual count and round
                return pop_data[str(pop_year)].div(1e3).round(0)
            else:
                print(f"Population data for year {pop_year} not found")
                return pd.Series(index=pop_data.index, data=0.0)
                
        except Exception as e:
            print(f"Error loading population data: {e}")
            return pd.Series(dtype=float)


def normalise_text(text: str) -> str:
    """
    Normalize text by removing diacritics and special characters.
    
    Based on PyPSA-Eur's build_shapes.py normalise_text function.
    
    Parameters
    ----------
    text : str
        Input text to normalize
        
    Returns
    -------
    str
        Normalized text
    """
    # Normalize Unicode to decompose characters (e.g., accented chars)
    text = unicodedata.normalize("NFD", text)
    # Remove diacritical marks by filtering out characters of the 'Mn' category
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    # Remove asterisks
    text = text.replace("*", "")
    # Ensure only ASCII characters remain
    text = "".join(char for char in text if char.isascii())
    return text


# -----------------------------------------------------------------------------
# Helper: post-processing visualization
# -----------------------------------------------------------------------------
def _run_visualization_post_step(iso3_code: str,
                                 no_powerplants: bool = False,
                                 powerplants_only: bool = False,
                                 ppl_cap_filter: float = 0.0,
                                 output_dir: str = 'output') -> None:
    """Invoke the visualization script on the freshly created outputs.

    Parameters
    ----------
    iso3_code : str
        ISO3 country code (e.g., CHE, DEU)
    no_powerplants : bool
        Exclude power plants from visualization
    powerplants_only : bool
        Show only power plants (exclude network)
    ppl_cap_filter : float
        Minimum capacity (MW) threshold for power plants to visualize
    output_dir : str
        Output directory containing the processed data
    """
    try:
        viz_script = SCRIPT_DIR / 'visualize_iso_network.py'
        cmd = [sys.executable, str(viz_script), iso3_code, '--output-dir', output_dir]
        if no_powerplants:
            cmd.append('--no-powerplants')
        if powerplants_only:
            cmd.append('--powerplants-only')
        if ppl_cap_filter and ppl_cap_filter > 0:
            cmd.extend(['--ppl-cap-filter', str(ppl_cap_filter)])
        # Skip SVG generation since enhanced SVG will be generated later
        cmd.append('--no-svg')
        # But keep the capacity filter for the HTML visualization
        if ppl_cap_filter and ppl_cap_filter > 0:
            cmd.extend(['--ppl-cap-filter', str(ppl_cap_filter)])

        print("\nGenerating visualization with:")
        print("   ", ' '.join(cmd))
        subprocess.run(cmd, check=True)
        print(f"+ Visualization generated: {output_dir}/{iso3_code}/{iso3_code}_network_visualization.html")
    except Exception as e:
        print(f"!  Visualization step failed: {e}")

def main():
    parser = argparse.ArgumentParser(
        description='Extract country-specific PyPSA network data from OSM datasets',
        usage='%(prog)s COUNTRY [DATA_SOURCE] [options]'
    )
    parser.add_argument('country', help='Country code - ISO2 (e.g., CH, DE, FR) or ISO3 (e.g., CHE, DEU, FRA)')
    parser.add_argument('data_source', choices=['eur', 'kan', 'cit', 'auto'], nargs='?', default='auto',
                        help='Data source: eur (OSM-eur), kan (OSM-kan), cit (worldcities), auto (detect available) (default: auto)')
    parser.add_argument('--fresh-data-load', action='store_true',
                        help='Force loading GEM data from Excel file instead of using cached data')
    # Optional post-processing visualization
    parser.add_argument('--visualize', action='store_true',
                        help='Generate interactive visualization after extraction using consolidated outputs')
    parser.add_argument('--viz-no-powerplants', action='store_true',
                        help='Exclude power plants from visualization')
    parser.add_argument('--viz-powerplants-only', action='store_true',
                        help='Show only power plants (exclude network) in visualization')
    parser.add_argument('--viz-ppl-cap-filter', type=float, default=0.0,
                        help='Minimum power plant capacity (MW) to visualize (default: 0 = all)')
    
    args = parser.parse_args()
    
    input_code = args.country.upper()
    
    # Determine if input is ISO2 or ISO3 and get both codes
    if len(input_code) == 2:
        # Input is ISO2
        iso2_code = input_code
        iso3_code = get_iso3_code(iso2_code)
    elif len(input_code) == 3:
        # Input is ISO3
        iso3_code = input_code
        iso2_code = get_iso2_from_iso3(iso3_code)
    else:
        print(f"Error: Invalid country code '{input_code}'. Please use ISO2 (e.g., CH) or ISO3 (e.g., CHE)")
        return
    
    print(f"Processing country: {input_code} (ISO2: {iso2_code}, ISO3: {iso3_code})")
    print("Using original network data (no clustering)")
    
    # Determine data sources to process
    if args.data_source == 'auto':
        print(f"\nAuto-detecting data source availability for {iso2_code}...")
        available_sources = detect_available_data_sources(iso2_code)
        
        if not available_sources:
            print(f"- Country '{iso2_code}' not found in any OSM dataset")
            return
        
        print(f"+ Found {iso2_code} in {len(available_sources)} dataset(s): {', '.join(available_sources)}")
        sources_to_process = available_sources
    else:
        # User specified a specific data source
        print(f"\nUsing specified data source: {args.data_source}")
        sources_to_process = [args.data_source]
        
        # Validate the specified source (except for 'cit' which doesn't need validation)
        if args.data_source != 'cit':
            print(f"Checking if {iso2_code} exists in {args.data_source} dataset...")
            available_sources = detect_available_data_sources(iso2_code)
            if args.data_source not in available_sources:
                print(f"- Country '{iso2_code}' not found in {args.data_source} dataset")
                print(f"- Available datasets: {', '.join(available_sources) if available_sources else 'None'}")
                return
            print(f"+ Country '{iso2_code}' confirmed in {args.data_source} dataset")
        else:
            print(f"+ Using worldcities data source for {iso2_code}")
    
    # Initialize iso_processor unless fresh data load is requested
    iso_processor = None
    use_cache = not args.fresh_data_load  # Default to using cache unless --fresh-data-load is specified
    
    if args.fresh_data_load:
        print("Fresh data load requested - will load GEM data from Excel file")
    else:
        print("Using cached data by default - use --fresh-data-load to force Excel loading")
    
    if use_cache:
        try:
            print("Initializing VerveStacks processor for cached data access...")
            sys.path.append(str(REPO_ROOT))  # Add project root to path
            from verve_stacks_processor import VerveStacksProcessor
            
            # Create a minimal processor just for data access
            main_processor = VerveStacksProcessor(cache_dir="../cache", force_reload=False)
            
            # Create a minimal iso_processor-like object with the required attributes
            class MinimalISOProcessor:
                def __init__(self, main_proc, iso_code):
                    self.main = main_proc
                    self.input_iso = iso_code
                    self.df_solar_rezoning = None  # Initialize rezoning_data attribute
                    self.df_windon_rezoning = None  # Initialize rezoning_data attribute
                    self.df_windoff_rezoning = None  # Initialize rezoning_data attribute
                    self.atlite_data_cache = {}  # Cache for country-filtered atlite data
            
            iso_processor = MinimalISOProcessor(main_processor, iso3_code)
            from shared_data_loader import get_rezoning_data
            rezoning_data = get_rezoning_data(force_reload=iso_processor.main.force_reload)
            
            # retain only current country
            # Get REZoning data for the country
            df_solar = rezoning_data.get('df_rez_solar', pd.DataFrame())
            df_windon = rezoning_data.get('df_rez_wind', pd.DataFrame())
            df_windoff = rezoning_data.get('df_rez_windoff', pd.DataFrame())

            # Filter to country
            if not df_solar.empty:
                df_solar_iso = df_solar[df_solar['ISO'] == iso3_code].copy()
            else:
                df_solar_iso = pd.DataFrame()
                
            if not df_windon.empty:
                df_windon_iso = df_windon[df_windon['ISO'] == iso3_code].copy()
            else:
                df_windon_iso = pd.DataFrame()

            if not df_windoff.empty:
                df_windoff_iso = df_windoff[df_windoff['ISO'] == iso3_code].copy()
            else:
                df_windoff_iso = pd.DataFrame()

            # Store rezoning data in iso_processor for later access
            iso_processor.df_solar_rezoning = df_solar_iso
            iso_processor.df_windon_rezoning = df_windon_iso
            iso_processor.df_windoff_rezoning = df_windoff_iso

            print("VerveStacks processor initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize VerveStacks processor: {e}")
            print("   Falling back to direct file loading...")
            iso_processor = None
    
    # Process each selected data source
    successful_sources = []
    failed_sources = []
    
    for source in sources_to_process:
        # Use data source type for output directory naming
        output_dir = f'output_{source}'  # output_eur, output_kan
        print(f"\n{'='*60}")
        print(f"Processing {source.upper()} dataset (Output: {output_dir})")
        print(f"{'='*60}")
        
        try:
            success = process_single_country(
                iso2_code, iso3_code, 
                iso_processor=iso_processor, 
                data_source=source, 
                output_dir=output_dir
            )
            
            if success:
                successful_sources.append((source, output_dir))
                print(f"\n+ Successfully processed {input_code} from {source} dataset!")
                print(f"Output files saved in: {output_dir}/{iso3_code}/")
                
                # Optionally run visualization step for this source
                if args.visualize:
                    print(f"\nGenerating visualization for {source} dataset...")
                    _run_visualization_post_step(
                        iso3_code=iso3_code,
                        no_powerplants=args.viz_no_powerplants,
                        powerplants_only=args.viz_powerplants_only,
                        ppl_cap_filter=args.viz_ppl_cap_filter,
                        output_dir=output_dir
                    )
            else:
                failed_sources.append((source, "Processing failed"))
                print(f"\n- Failed to process {input_code} from {source} dataset")
                
        except Exception as e:
            failed_sources.append((source, str(e)))
            print(f"- Error processing {input_code} from {source} dataset: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("PROCESSING SUMMARY")
    print(f"{'='*60}")
    
    if successful_sources:
        print(f"+ Successfully processed {len(successful_sources)} dataset(s):")
        for source, output_dir in successful_sources:
            print(f"  - {source.upper()}: {output_dir}/{iso3_code}/")
    
    if failed_sources:
        print(f"- Failed to process {len(failed_sources)} dataset(s):")
        for source, error in failed_sources:
            print(f"  - {source.upper()}: {error}")
    
    # Show output files for successful sources
    if successful_sources:
        print(f"\nOutput Files (for each successful dataset):")
        print(f"  - {iso3_code}_zone_bus_mapping.csv")
        print(f"  - {iso3_code}_power_plants_assigned_to_buses.csv")
        print(f"  - {iso3_code}_clustered_buses.csv (original buses)")
        print(f"  - {iso3_code}_clustered_lines.csv (original lines)")
        print(f"  - {iso3_code}_bus_load_share.csv")
        print(f"  - {iso3_code}_bus_load_share_voronoi.csv")
        print(f"  - {iso3_code}_bus_load_share_wtddist.csv")
        print(f"  - {iso3_code}_industry_load_share.csv")
        if args.visualize:
            print(f"  - {iso3_code}_network_visualization.html")

def generate_enhanced_grid_svg(iso_code, buses_df, lines_df, plants_df, zones_df, iso_processor=None, output_dir='output', output_file=None):
    """Generate enhanced SVG with actual GEM power plant data"""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        import sys
        from pathlib import Path
        
        # Load GEM data to get full plant information
        try:
            if iso_processor is not None and hasattr(iso_processor, 'main') and hasattr(iso_processor.main, 'df_gem'):
                print(f"   Using cached GEM data from iso_processor")
                df_gem_country = iso_processor.main.df_gem[iso_processor.main.df_gem['iso_code'] == iso_processor.input_iso]
                df_gem_country = filter_gem_data_by_status(df_gem_country, include_announced=True, include_preconstruction=True)
                
                # Merge plants assignment with GEM data
                merged_plants_df = df_gem_country.merge(
                    plants_df, 
                    on='GEM location ID', 
                    how='inner'
                )
                print(f"   Found {len(merged_plants_df)} power plants with full GEM data")
            else:
                print("   No iso_processor available, using assignment data only")
                merged_plants_df = plants_df
        except Exception as e:
            print(f"   Could not load GEM data: {e}")
            import traceback
            traceback.print_exc()
            merged_plants_df = plants_df
        
        # Create figure with high DPI for crisp SVG
        fig, ax = plt.subplots(figsize=(16, 12), dpi=150)
        
        # Set up the plot
        ax.set_aspect('equal')
        ax.set_facecolor('white')  # White background for better marker visibility
        
        # Add a subtle grid for geographical reference
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5, color='lightgray')
        
        # Collect all coordinates to determine bounds
        all_lats = []
        all_lngs = []
        
        # Collect coordinates from all data sources
        if not buses_df.empty and 'x' in buses_df.columns and 'y' in buses_df.columns:
            valid_buses = buses_df.dropna(subset=['x', 'y'])
            all_lats.extend(valid_buses['y'].tolist())  # y is latitude
            all_lngs.extend(valid_buses['x'].tolist())  # x is longitude
        
        if not plants_df.empty and 'Latitude' in plants_df.columns and 'Longitude' in plants_df.columns:
            valid_plants = plants_df.dropna(subset=['Latitude', 'Longitude'])
            all_lats.extend(valid_plants['Latitude'].tolist())
            all_lngs.extend(valid_plants['Longitude'].tolist())
        
        # Lines don't have geometry, but we can get coordinates from connected buses
        if not lines_df.empty and 'bus0' in lines_df.columns and 'bus1' in lines_df.columns:
            # Get coordinates from connected buses
            bus_coords = buses_df.set_index('bus_id')[['x', 'y']].to_dict('index')
            for idx, line in lines_df.iterrows():
                bus0_id = line['bus0']
                bus1_id = line['bus1']
                if bus0_id in bus_coords and bus1_id in bus_coords:
                    all_lats.extend([bus_coords[bus0_id]['y'], bus_coords[bus1_id]['y']])
                    all_lngs.extend([bus_coords[bus0_id]['x'], bus_coords[bus1_id]['x']])
        
        # Set plot bounds based on data
        if all_lats and all_lngs:
            lat_min, lat_max = min(all_lats), max(all_lats)
            lng_min, lng_max = min(all_lngs), max(all_lngs)
            
            # Add some padding
            lat_padding = (lat_max - lat_min) * 0.1
            lng_padding = (lng_max - lng_min) * 0.1
            
            ax.set_xlim(lng_min - lng_padding, lng_max + lng_padding)
            ax.set_ylim(lat_min - lat_padding, lat_max + lat_padding)
            
            print(f"   SVG bounds: Lat {lat_min:.3f}-{lat_max:.3f}, Lng {lng_min:.3f}-{lng_max:.3f}")
        else:
            # Fallback bounds if no data
            ax.set_xlim(-180, 180)
            ax.set_ylim(-90, 90)
            print("   No coordinate data found, using world bounds")
        
        # Add background map using Natural Earth data
        ax.set_facecolor('white')  # White background for better marker visibility
        
        # Try to load Natural Earth data for proper background map
        try:
            import geopandas as gpd
            import os
            
            
            # Try both relative paths for different execution contexts
            ne_data_path = BASE_INPUT_FILES['naturalearth_countries']
            if not os.path.exists(ne_data_path + '.shp'):
                # Try from main project directory
                ne_data_path = 'data/country_data/naturalearth/ne_10m_admin_0_countries_lakes'
            
            if os.path.exists(ne_data_path + '.shp'):
                # Load Natural Earth countries data
                world = gpd.read_file(ne_data_path + '.shp')
                
                # Filter to relevant region based on data bounds
                if all_lats and all_lngs:
                    # Add some padding to the bounds
                    lat_padding = (max(all_lats) - min(all_lats)) * 0.2
                    lng_padding = (max(all_lngs) - min(all_lngs)) * 0.2
                    
                    # Create bounding box for filtering
                    bbox = {
                        'minx': min(all_lngs) - lng_padding,
                        'miny': min(all_lats) - lat_padding,
                        'maxx': max(all_lngs) + lng_padding,
                        'maxy': max(all_lats) + lat_padding
                    }
                    
                    # Filter countries that intersect with our region
                    world_filtered = world.cx[bbox['minx']:bbox['maxx'], bbox['miny']:bbox['maxy']]
                    
                    if not world_filtered.empty:
                        # Plot countries as background
                        for idx, country in world_filtered.iterrows():
                            if country.geometry is not None:
                                # Plot country boundaries
                                if hasattr(country.geometry, 'exterior'):
                                    # Single polygon
                                    x, y = country.geometry.exterior.xy
                                    ax.plot(x, y, 'k-', linewidth=0.5, alpha=0.6, zorder=0)
                                elif hasattr(country.geometry, 'geoms'):
                                    # Multi-polygon
                                    for geom in country.geometry.geoms:
                                        if hasattr(geom, 'exterior'):
                                            x, y = geom.exterior.xy
                                            ax.plot(x, y, 'k-', linewidth=0.5, alpha=0.6, zorder=0)
                        
                        print(f"   Added Natural Earth background map with {len(world_filtered)} countries")
                    else:
                        print("   No countries found in region, using simple background")
                else:
                    print("   No coordinate data for filtering, using simple background")
            else:
                print("   Natural Earth data not found, using simple background")
                
        except ImportError:
            print("   GeoPandas not available, using simple background")
        except Exception as e:
            print(f"   Error loading Natural Earth data: {e}, using simple background")
        
        # Add subtle grid
        ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.3, color='lightblue')
        
        # Plot transmission lines
        if not lines_df.empty and 'bus0' in lines_df.columns and 'bus1' in lines_df.columns:
            bus_coords = buses_df.set_index('bus_id')[['x', 'y']].to_dict('index')
            lines_plotted = 0
            for idx, line in lines_df.iterrows():
                bus0_id = line['bus0']
                bus1_id = line['bus1']
                if bus0_id in bus_coords and bus1_id in bus_coords:
                    x_coords = [bus_coords[bus0_id]['x'], bus_coords[bus1_id]['x']]
                    y_coords = [bus_coords[bus0_id]['y'], bus_coords[bus1_id]['y']]
                    ax.plot(x_coords, y_coords, 'b-', alpha=0.6, linewidth=0.8, zorder=1)
                    lines_plotted += 1
            print(f"   Plotted {lines_plotted} transmission lines")
        
        # Plot transmission buses
        if not buses_df.empty and 'x' in buses_df.columns and 'y' in buses_df.columns:
            valid_buses = buses_df.dropna(subset=['x', 'y'])
            if not valid_buses.empty:
                ax.scatter(valid_buses['x'], valid_buses['y'], 
                          c='blue', s=8, alpha=0.7, zorder=2, edgecolors='darkblue', linewidth=0.3)
                print(f"   Plotted {len(valid_buses)} transmission buses")
        
        # Plot power plants with actual GEM data (filtered by capacity like original)
        if not merged_plants_df.empty and 'Latitude' in merged_plants_df.columns and 'Longitude' in merged_plants_df.columns:
            valid_plants = merged_plants_df.dropna(subset=['Latitude', 'Longitude'])
            # Apply capacity filter (100MW threshold like original visualization)
            # if 'Capacity (MW)' in valid_plants.columns:
                # valid_plants = valid_plants[valid_plants['Capacity (MW)'] >= 100.0]
            if not valid_plants.empty:
                # Size markers based on capacity
                if 'Capacity (MW)' in valid_plants.columns:
                    sizes = np.clip(valid_plants['Capacity (MW)'] * 2, 10, 200)  # Scale capacity to marker size
                else:
                    sizes = 20  # Default size
                
                # Color by technology type using energy_colors (simpler and cleaner)
                if 'model_fuel' in valid_plants.columns:
                    # Import the energy colors
                    import sys
                    import os
                    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '2_ts_design', 'scripts'))
                    from energy_colors import get_energy_color
                    
                    # Get colors using energy_colors
                    colors = []
                    for idx, row in valid_plants.iterrows():
                        fuel_type = str(row['model_fuel']).lower()
                        # Map model_fuel to energy_colors format
                        if fuel_type in ['windon', 'windoff']:
                            fuel_type = 'wind'
                        elif fuel_type in ['gas', 'oil']:
                            fuel_type = 'gas'  # Will use default gray
                        elif fuel_type == 'coal':
                            fuel_type = 'coal'  # Will use default gray
                        elif fuel_type == 'bioenergy':
                            fuel_type = 'biomass'  # Will use default gray
                        elif fuel_type == 'geothermal':
                            fuel_type = 'geothermal'  # Will use default gray
                        
                        color = get_energy_color(fuel_type)
                        colors.append(color)
                    colors = colors
                else:
                    colors = 'red'
                
                # Check if 'is_new_tech' column exists to differentiate old vs new tech
                if 'is_new_tech' in valid_plants.columns:
                    print(f"   🔍 Found 'is_new_tech' column in plants data")
                    print(f"   📊 is_new_tech value counts: {valid_plants['is_new_tech'].value_counts().to_dict()}")
                    
                    # Create a mapping from original index to position for colors and sizes
                    original_indices = valid_plants.index.tolist()
                    colors_array = np.array(colors) if isinstance(colors, list) else colors
                    sizes_array = np.array(sizes) if hasattr(sizes, '__len__') and len(sizes) > 1 else sizes
                    
                    # Separate old tech and new tech plants
                    old_tech_plants = valid_plants[valid_plants['is_new_tech'] == False]
                    new_tech_plants = valid_plants[valid_plants['is_new_tech'] == True]
                    
                    print(f"   📍 Old tech plants: {len(old_tech_plants)}")
                    print(f"   🔆 New tech plants: {len(new_tech_plants)}")
                    
                    plants_plotted = 0
                    
                    # Plot old tech plants with filled markers (original style)
                    if not old_tech_plants.empty:
                        # Get colors and sizes for old tech plants
                        old_positions = [original_indices.index(idx) for idx in old_tech_plants.index]
                        if isinstance(colors_array, np.ndarray) and len(colors_array) > 1:
                            old_colors = colors_array[old_positions]
                        else:
                            old_colors = colors
                        
                        if isinstance(sizes_array, np.ndarray) and len(sizes_array) > 1:
                            old_sizes = sizes_array[old_positions]
                        else:
                            old_sizes = sizes
                        
                        ax.scatter(old_tech_plants['Longitude'], old_tech_plants['Latitude'], 
                                  c=old_colors, s=old_sizes, alpha=0.8, zorder=3, 
                                  edgecolors='black', linewidth=0.3)
                        plants_plotted += len(old_tech_plants)
                        print(f"   Plotted {len(old_tech_plants)} old tech power plants (filled markers)")
                    
                    # Plot new tech plants with hollow markers
                    if not new_tech_plants.empty:
                        # Get colors and sizes for new tech plants
                        new_positions = [original_indices.index(idx) for idx in new_tech_plants.index]
                        if isinstance(colors_array, np.ndarray) and len(colors_array) > 1:
                            new_edge_colors = colors_array[new_positions]
                        else:
                            new_edge_colors = colors
                        
                        if isinstance(sizes_array, np.ndarray) and len(sizes_array) > 1:
                            new_sizes = sizes_array[new_positions]
                        else:
                            new_sizes = sizes
                        
                        # Simple hollow markers with colored borders
                        ax.scatter(new_tech_plants['Longitude'], new_tech_plants['Latitude'], 
                                  facecolors='none', s=new_sizes, alpha=0.9, zorder=4,
                                  edgecolors=new_edge_colors, linewidth=1.5)
                        
                        plants_plotted += len(new_tech_plants)
                        print(f"   🟡 Plotted {len(new_tech_plants)} new tech power plants (hollow markers)")
                    
                    print(f"   Total plotted: {plants_plotted} power plants")
                    
                else:
                    # Fallback to original plotting if 'is_new_tech' column doesn't exist
                    ax.scatter(valid_plants['Longitude'], valid_plants['Latitude'], 
                              c=colors, s=sizes, alpha=0.8, zorder=3, edgecolors='black', linewidth=0.3)
                    print(f"   Plotted {len(valid_plants)} power plants (original style - no is_new_tech column)")
            else:
                print(f"   No valid power plants found (empty after dropping NaN coordinates)")
        else:
            print(f"   Power plants data missing Latitude/Longitude columns")
        
        # Plot hydro potential projects (if available)
        hydro_projects_plotted = 0
        try:
            # Try to load hydro potential data
            import json
            hydro_json_path = Path("../data/country_data/hydro_beyond_gem.json")
            if not hydro_json_path.exists():
                hydro_json_path = Path("data/country_data/hydro_beyond_gem.json")
            
            if hydro_json_path.exists():
                with open(hydro_json_path, 'r', encoding='utf-8') as f:
                    hydro_data = json.load(f)
                
                # Find country by ISO code
                target_country = None
                for country_key, country_data in hydro_data['additional_potential'].items():
                    if country_data['iso3'] == iso_code:
                        target_country = country_data
                        break
                
                if target_country:
                    print(f"   Loading hydro potential for {target_country['country_name']} ({iso_code})")
                    
                    # Extract all hydro projects from missing_projects
                    hydro_projects = []
                    missing_projects = target_country.get('missing_projects', [])
                    
                    for project in missing_projects:
                        # Handle capacity (GW in new format)
                        capacity_gw = project.get('capacity_gw', 1.0)
                        capacity_mw = capacity_gw * 1000  # Convert GW to MW
                        
                        # Default cost estimate
                        cost_per_kw = project.get('estimated_cost_usd_per_kw', 3000)
                        
                        # Priority level to border thickness mapping
                        priority_thickness = {
                            'Ultra High': 2.0,
                            'High': 1.5,
                            'Medium-High': 1.0,
                            'Medium': 0.8
                        }
                        
                        hydro_projects.append({
                            'name': project['name'],
                            'lat': project.get('lat', 0.0),
                            'lon': project.get('lng', 0.0),
                            'capacity_mw': float(capacity_mw),
                            'capacity_gw': float(capacity_gw),
                            'cost_per_kw': float(cost_per_kw),
                            'priority': 'High',  # Default priority
                            'border_width': priority_thickness.get('High', 1.5),
                            'status': 'Planned'  # Default status
                        })
                    
                    if hydro_projects:
                        # Convert to arrays for plotting
                        lats = [p['lat'] for p in hydro_projects]
                        lons = [p['lon'] for p in hydro_projects]
                        sizes = [p['capacity_gw'] * 40 for p in hydro_projects]  # Scale GW to marker size
                        costs = [p['cost_per_kw'] for p in hydro_projects]
                        border_widths = [p['border_width'] for p in hydro_projects]
                        
                        # Plot hydro potential as diamond markers
                        scatter_hydro = ax.scatter(
                            lons, lats,
                            c=costs,                    # Color by cost per kW
                            s=sizes,                    # Size by GW capacity
                            marker='D',                 # Diamond shape
                            cmap='RdYlGn_r',           # Red=expensive, Green=cheap
                            alpha=0.8,                  # Slightly transparent
                            zorder=5,                   # Above power plants
                            edgecolors='navy',          # Dark blue border
                            linewidths=border_widths,   # Border thickness by priority
                            label='Hydro Potential'
                        )
                        
                        hydro_projects_plotted = len(hydro_projects)
                        total_hydro_gw = sum(p['capacity_gw'] for p in hydro_projects)
                        print(f"   Plotted {hydro_projects_plotted} hydro potential projects ({total_hydro_gw:.1f} GW total)")
                        
                        # Add colorbar for hydro costs (small, positioned to not interfere)
                        if hydro_projects_plotted > 1:  # Only add colorbar if multiple projects with different costs
                            from mpl_toolkits.axes_grid1 import make_axes_locatable
                            divider = make_axes_locatable(ax)
                            cax = divider.append_axes("bottom", size="3%", pad=0.1)
                            cbar = plt.colorbar(scatter_hydro, cax=cax, orientation='horizontal')
                            cbar.set_label('Hydro Cost ($/kW)', fontsize=8)
                            cbar.ax.tick_params(labelsize=7)
                    else:
                        print(f"   No hydro projects found for {iso_code}")
                else:
                    print(f"   No hydro potential data available for {iso_code}")
            else:
                print(f"   Hydro potential database not found: {hydro_json_path}")
                
        except Exception as e:
            print(f"   Could not load hydro potential data for {iso_code}: {e}")
        
        # Add title and labels with statistics
        total_capacity = merged_plants_df['Capacity (MW)'].sum() if 'Capacity (MW)' in merged_plants_df.columns else 0
        ax.set_title(f'Enhanced Grid Network Visualization\n(Actual GEM Power Plant Data - {len(merged_plants_df)} plants, {total_capacity:.0f} MW total)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Longitude', fontsize=10)
        ax.set_ylabel('Latitude', fontsize=10)
        
        # Add enhanced legend with power plant types
        legend_elements = [
            plt.Line2D([0], [0], color='blue', linewidth=2, label='Transmission Lines'),
            plt.scatter([], [], c='blue', s=30, label='Transmission Buses'),
        ]
        
        # Add power plant type legend entries using energy_colors (simpler and cleaner)
        if not merged_plants_df.empty and 'model_fuel' in merged_plants_df.columns:
            # Import the energy colors
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), '2_ts_design', 'scripts'))
            from energy_colors import get_energy_color
            
            # Check if we have is_new_tech column to create separate legend entries
            if 'is_new_tech' in merged_plants_df.columns:
                # Create separate counts for old tech and new tech
                fuel_counts_old = merged_plants_df[merged_plants_df['is_new_tech'] == False]['model_fuel'].value_counts()
                fuel_counts_new = merged_plants_df[merged_plants_df['is_new_tech'] == True]['model_fuel'].value_counts()
                
                # Add old tech (filled) legend entries
                for fuel_type in fuel_counts_old.index:
                    fuel_lower = str(fuel_type).lower()
                    color = get_energy_color(fuel_lower)
                    fuel_label = fuel_type.replace('_', ' ').title()
                    count = fuel_counts_old[fuel_type]
                    legend_elements.append(plt.scatter([], [], c=color, s=30, edgecolors='black', linewidth=0.3,
                                                     label=f'{fuel_label} ({count})'))
                
                # Add new tech (hollow) legend entries
                for fuel_type in fuel_counts_new.index:
                    fuel_lower = str(fuel_type).lower()
                    color = get_energy_color(fuel_lower)
                    fuel_label = fuel_type.replace('_', ' ').title()
                    count = fuel_counts_new[fuel_type]
                    # Show hollow marker with colored border in legend
                    legend_elements.append(plt.scatter([], [], facecolors='none', s=30, 
                                                     edgecolors=color, linewidth=1.5,
                                                     label=f'{fuel_label} Potential ({count})'))
            else:
                # Fallback to original legend if no is_new_tech column
                fuel_counts = merged_plants_df['model_fuel'].value_counts()
                for fuel_type in fuel_counts.index:
                    fuel_lower = str(fuel_type).lower()
                    color = get_energy_color(fuel_lower)
                    fuel_label = fuel_type.replace('_', ' ').title()
                    count = fuel_counts[fuel_type]
                    legend_elements.append(plt.scatter([], [], c=color, s=30, label=f'{fuel_label} ({count})'))
        else:
            legend_elements.append(plt.scatter([], [], c='red', s=30, label='Power Plants'))
        
        # Add hydro potential to legend if any were plotted
        if hydro_projects_plotted > 0:
            legend_elements.append(plt.scatter([], [], c='green', s=40, marker='D', 
                                             edgecolors='navy', linewidths=1.5,
                                             label=f'Hydro Potential ({hydro_projects_plotted})'))
        
        ax.legend(handles=legend_elements, loc='upper right', fontsize=7, framealpha=0.9, ncol=1)
        
        # Remove ticks for cleaner look
        ax.tick_params(axis='both', which='major', labelsize=8)
        
        # Save as SVG - handle both full path and directory cases
        if output_file is not None:
            # Use the full output file path
            svg_file = Path(output_file)
        else:
            # Use the same folder structure as CSV files
            svg_file = Path(output_dir) / iso_code / f"{iso_code}_network_visualization.svg"
        
        # Ensure the parent directory exists for both cases
        svg_file.parent.mkdir(parents=True, exist_ok=True)
        
        plt.tight_layout()
        plt.savefig(svg_file, format='svg', bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"   Enhanced SVG generated: {svg_file}")
        
    except Exception as e:
        print(f"   Error generating enhanced SVG: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
