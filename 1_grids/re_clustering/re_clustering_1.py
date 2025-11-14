import pandas as pd
import numpy as np
import geopandas as gpd
from scipy.spatial import cKDTree
from scipy.cluster.hierarchy import linkage, fcluster
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import os
from shapely.geometry import Point, Polygon
from scipy.spatial import ConvexHull

def get_iso3_from_iso2(iso2_code):
    """Convert ISO2 to ISO3 country code"""
    try:
        import pycountry
        country = pycountry.countries.get(alpha_2=iso2_code)
        if country:
            return country.alpha_3
    except:
        pass
    
    # Fallback dictionary for common cases
    iso2_to_iso3 = {
        'IT': 'ITA', 'BR': 'BRA', 'DE': 'DEU', 'FR': 'FRA',
        'CH': 'CHE', 'ES': 'ESP', 'GB': 'GBR', 'NL': 'NLD',
        'AT': 'AUT', 'BE': 'BEL', 'PL': 'POL', 'CZ': 'CZE',
        'DK': 'DNK', 'NO': 'NOR', 'SE': 'SWE', 'FI': 'FIN',
        'PT': 'PRT', 'GR': 'GRC', 'HU': 'HUN', 'SK': 'SVK'
    }
    return iso2_to_iso3.get(iso2_code, iso2_code)

def normalize_country_code(country_code):
    """Normalize country code to ISO3 format"""
    if len(country_code) == 2:
        # ISO2 code, convert to ISO3
        return get_iso3_from_iso2(country_code.upper())
    elif len(country_code) == 3:
        # Already ISO3
        return country_code.upper()
    else:
        raise ValueError(f"Invalid country code: {country_code}. Use ISO2 (e.g., 'IT') or ISO3 (e.g., 'ITA')")

def load_land_mask(country_code=None):
    """
    Load land mask data for validating centroids are on land
    Uses existing Natural Earth countries data, filtered to target country
    """
    try:
        # Use existing Natural Earth countries data
        land_file = '../data/country_data/naturalearth/ne_10m_admin_0_countries_lakes.shp'
        
        if not os.path.exists(land_file):
            # Try alternative path
            land_file = 'data/country_data/naturalearth/ne_10m_admin_0_countries_lakes.shp'
        
        if not os.path.exists(land_file):
            raise FileNotFoundError(f"Natural Earth countries file not found at {land_file}")
        
        print("Loading land mask from existing Natural Earth data...")
        land_gdf = gpd.read_file(land_file)
        
        # Filter to target country if specified
        if country_code:
            print(f"Filtering land mask to country: {country_code}")
            
            # Try different country code columns that might exist
            country_columns = ['ISO_A3', 'ISO_A3_EH', 'ADM0_A3', 'ISO3', 'ISO_A3_EH']
            country_found = False
            
            for col in country_columns:
                if col in land_gdf.columns:
                    # Filter to target country
                    country_mask = land_gdf[col].str.upper() == country_code.upper()
                    if country_mask.any():
                        land_gdf = land_gdf[country_mask].copy()
                        country_found = True
                        print(f"   ✅ Found country using column '{col}': {len(land_gdf)} polygons")
                        break
            
            if not country_found:
                print(f"   ⚠️  Country {country_code} not found in land data")
                print(f"   Available country codes: {land_gdf[country_columns[0]].unique()[:10] if country_columns[0] in land_gdf.columns else 'Unknown'}")
                print("   Using full land mask (all countries)")
        else:
            print("   No country specified, using full land mask (all countries)")
        
        print(f"✅ Land mask loaded: {len(land_gdf)} country polygons")
        return land_gdf
        
    except Exception as e:
        print(f"⚠️  Warning: Could not load land mask: {e}")
        print("   Centroids will not be validated against land boundaries")
        return None

def is_point_on_land(lat, lon, land_gdf):
    """
    Check if a point (lat, lon) is on land using the land mask
    """
    if land_gdf is None:
        return True  # Assume on land if no mask available
    
    try:
        point = Point(lon, lat)  # Note: Point takes (x, y) = (lon, lat)
        
        # Check if point intersects with any land polygon
        return land_gdf.geometry.intersects(point).any()
    except Exception as e:
        print(f"⚠️  Error checking land status: {e}")
        return True  # Assume on land if error

def validate_and_correct_centroid(lat, lon, land_gdf, cluster_coords=None, technology=None):
    """
    Validate centroid is in correct location and correct if necessary using zone-based fallback
    For onshore: ensures centroid is on land
    For offshore: ensures centroid is offshore (not on land)
    """
    # Check if centroid is on land
    is_on_land = is_point_on_land(lat, lon, land_gdf)
    
    # Determine target location based on technology
    is_offshore_tech = technology and 'offshore' in technology.lower()
    
    if is_offshore_tech:
        # For offshore: we want the centroid to be offshore (NOT on land)
        if not is_on_land:
            return lat, lon  # Already offshore, good!
    else:
        # For onshore: we want the centroid to be on land
        if is_on_land:
            return lat, lon  # Already on land, good!
    
    # Check if we have cluster coordinates for fallback
    if cluster_coords is None or len(cluster_coords) == 0:
        return lat, lon
    
    # Find zones in cluster that match the target location
    target_zones = []
    for i, (zone_lat, zone_lon) in enumerate(cluster_coords):
        zone_is_on_land = is_point_on_land(zone_lat, zone_lon, land_gdf)
        
        if is_offshore_tech:
            # For offshore: look for zones that are offshore (NOT on land)
            if not zone_is_on_land:
                target_zones.append((zone_lat, zone_lon, i))
        else:
            # For onshore: look for zones that are on land
            if zone_is_on_land:
                target_zones.append((zone_lat, zone_lon, i))
    
    if not target_zones:
        return lat, lon
    
    # Find the target zone closest to the calculated centroid
    min_distance = float('inf')
    best_lat, best_lon, best_idx = lat, lon, -1
    
    for zone_lat, zone_lon, idx in target_zones:
        distance = ((zone_lat - lat)**2 + (zone_lon - lon)**2)**0.5
        if distance < min_distance:
            min_distance = distance
            best_lat, best_lon, best_idx = zone_lat, zone_lon, idx
    
    return best_lat, best_lon

def create_cluster_validation_plot(clusters, profiles, cluster_stats, land_gdf=None, country_code='TEST'):
    """
    Create a temporary visualization to validate cluster centroids and shapes
    DEBUGGING ONLY - Comment out in production
    """
    print(f"\n=== Creating Cluster Validation Plot for {country_code} ===")
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    fig.suptitle(f'Cluster Validation - {country_code}', fontsize=16, fontweight='bold')
    
    # Plot 1: Original zones with cluster colors
    ax1 = axes[0, 0]
    scatter1 = ax1.scatter(
        profiles['coords'][:, 1],  # longitude
        profiles['coords'][:, 0],  # latitude
        c=clusters,
        cmap='tab20',
        s=30,
        alpha=0.7,
        edgecolors='black',
        linewidth=0.3
    )
    ax1.set_title('Original Zones by Cluster')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.grid(True, alpha=0.3)
    plt.colorbar(scatter1, ax=ax1, label='Cluster ID')
    
    # Plot 2: Cluster centroids (original vs corrected)
    ax2 = axes[0, 1]
    
    # Plot original centroids (arithmetic mean)
    original_centroids = []
    for c in np.unique(clusters):
        mask = clusters == c
        orig_lat = float(profiles['coords'][mask, 0].mean())
        orig_lon = float(profiles['coords'][mask, 1].mean())
        original_centroids.append([orig_lat, orig_lon])
    
    original_centroids = np.array(original_centroids)
    
    # Plot zones
    ax2.scatter(
        profiles['coords'][:, 1], profiles['coords'][:, 0],
        c='lightblue', s=10, alpha=0.3, label='Zones'
    )
    
    # Plot original centroids
    ax2.scatter(
        original_centroids[:, 1], original_centroids[:, 0],
        c='red', s=100, marker='x', linewidth=3, label='Original Centroids'
    )
    
    # Plot corrected centroids
    ax2.scatter(
        cluster_stats['centroid_lon'], cluster_stats['centroid_lat'],
        c='green', s=100, marker='o', edgecolors='darkgreen', linewidth=2, label='Corrected Centroids'
    )
    
    # Draw lines from original to corrected centroids
    for i, (orig, corr) in enumerate(zip(original_centroids, cluster_stats[['centroid_lat', 'centroid_lon']].values)):
        ax2.plot([orig[1], corr[1]], [orig[0], corr[0]], 
                'k--', alpha=0.5, linewidth=1)
        # Add cluster ID labels
        ax2.annotate(f'C{i}', (corr[1], corr[0]), xytext=(5, 5), 
                    textcoords='offset points', fontsize=8, fontweight='bold')
    
    ax2.set_title('Centroid Correction')
    ax2.set_xlabel('Longitude')
    ax2.set_ylabel('Latitude')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Cluster shapes (convex hulls)
    ax3 = axes[1, 0]
    
    # Plot zones
    ax3.scatter(
        profiles['coords'][:, 1], profiles['coords'][:, 0],
        c='lightgray', s=8, alpha=0.4, label='Zones'
    )
    
    # Create and plot cluster shapes
    colors = plt.cm.tab20(np.linspace(0, 1, len(np.unique(clusters))))
    
    for i, c in enumerate(np.unique(clusters)):
        mask = clusters == c
        cluster_coords = profiles['coords'][mask]
        
        if len(cluster_coords) >= 3:  # Need at least 3 points for convex hull
            try:
                # Create convex hull
                hull = ConvexHull(cluster_coords)
                hull_points = cluster_coords[hull.vertices]
                
                # Create polygon
                hull_polygon = Polygon(hull_points)
                
                # Plot convex hull
                x, y = hull_polygon.exterior.xy
                ax3.plot(x, y, color=colors[i], linewidth=2, alpha=0.8)
                ax3.fill(x, y, color=colors[i], alpha=0.2)
                
                # Plot centroid
                centroid = cluster_stats[cluster_stats['cluster_id'] == c].iloc[0]
                ax3.scatter(centroid['centroid_lon'], centroid['centroid_lat'],
                           c=colors[i], s=150, marker='*', edgecolors='black', linewidth=1)
                
                # Add cluster ID
                ax3.annotate(f'C{c}', (centroid['centroid_lon'], centroid['centroid_lat']),
                            xytext=(5, 5), textcoords='offset points', 
                            fontsize=10, fontweight='bold', color='white',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor=colors[i], alpha=0.8))
                
            except Exception as e:
                print(f"   ⚠️  Could not create convex hull for cluster {c}: {e}")
                # Just plot the points
                ax3.scatter(cluster_coords[:, 1], cluster_coords[:, 0],
                           c=[colors[i]], s=20, alpha=0.6)
    
    ax3.set_title('Cluster Shapes (Convex Hulls)')
    ax3.set_xlabel('Longitude')
    ax3.set_ylabel('Latitude')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Land mask validation
    ax4 = axes[1, 1]
    
    # Plot land mask if available
    if land_gdf is not None:
        land_gdf.plot(ax=ax4, color='lightgreen', alpha=0.3, edgecolor='darkgreen', linewidth=0.5)
        ax4.set_title('Land Mask Validation')
    else:
        ax4.set_title('Land Mask Validation (No Land Data)')
    
    # Plot zones
    ax4.scatter(
        profiles['coords'][:, 1], profiles['coords'][:, 0],
        c='lightblue', s=8, alpha=0.4, label='Zones'
    )
    
    # Plot centroids with land validation status
    for _, centroid in cluster_stats.iterrows():
        # Check if centroid is on land
        is_land = is_point_on_land(centroid['centroid_lat'], centroid['centroid_lon'], land_gdf)
        color = 'green' if is_land else 'red'
        marker = 'o' if is_land else 'X'
        
        ax4.scatter(centroid['centroid_lon'], centroid['centroid_lat'],
                   c=color, s=100, marker=marker, edgecolors='black', linewidth=1,
                   label='On Land' if is_land and centroid.name == 0 else None)
    
    # Remove duplicate labels
    handles, labels = ax4.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax4.legend(by_label.values(), by_label.keys())
    
    ax4.set_xlabel('Longitude')
    ax4.set_ylabel('Latitude')
    ax4.grid(True, alpha=0.3)
    
    # Adjust layout and save
    plt.tight_layout()
    
    # Save the plot
    output_file = f'cluster_validation_{country_code.lower()}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"   ✅ Validation plot saved: {output_file}")
    
    # Show the plot
    plt.show()
    
    # Print summary statistics
    print(f"\n=== Cluster Validation Summary ===")
    print(f"Total clusters: {len(cluster_stats)}")
    print(f"Total zones: {len(profiles['coords'])}")
    
    if land_gdf is not None:
        on_land_count = 0
        for _, centroid in cluster_stats.iterrows():
            if is_point_on_land(centroid['centroid_lat'], centroid['centroid_lon'], land_gdf):
                on_land_count += 1
        
        print(f"Centroids on land: {on_land_count}/{len(cluster_stats)} ({on_land_count/len(cluster_stats)*100:.1f}%)")
        print(f"Centroids corrected: {len(cluster_stats) - on_land_count}")
    
    return fig

def load_all_data_properly(country_code='BRA'):
    """
    Load all data sources with proper geographic information
    """
    # Normalize country code to ISO3
    country_code = normalize_country_code(country_code)
    print(f"\n=== Loading all data for {country_code} ===")
    
    # 1. Load Rezoning data with geometries
    print("Loading rezoning data with geometries...")
    onshore_zones = pd.read_parquet('../data/REZoning/consolidated_onshore_zones_with_geometry.parquet')
    offshore_zones = pd.read_parquet('../data/REZoning/consolidated_offshore_zones_with_geometry.parquet')
    
    print(f"Onshore zones shape: {onshore_zones.shape}")
    print(f"Onshore columns: {onshore_zones.columns.tolist()}")
    print(f"\nOffshore zones shape: {offshore_zones.shape}")
    print(f"Offshore columns: {offshore_zones.columns.tolist()}")
    
    # 2. Filter to country
    if 'country' in onshore_zones.columns:
        onshore_country = onshore_zones[onshore_zones['country'] == country_code]
    elif 'grid_cell' in onshore_zones.columns:
        onshore_country = onshore_zones[onshore_zones['grid_cell'].str.startswith(f'{country_code}_')]
    else:
        onshore_country = onshore_zones  # Assume all data is for one country
    
    print(f"\nFiltered to {len(onshore_country)} onshore zones for {country_code}")
    
    # 3. Extract coordinates from geometry
    if 'geometry' in onshore_country.columns:
        # Convert geometry column from binary WKB to proper geometry
        from shapely import wkb, wkt
        if onshore_country['geometry'].dtype == 'object':
            # Check if it's binary (WKB) or text (WKT)
            sample_geom = onshore_country['geometry'].iloc[0]
            if isinstance(sample_geom, bytes):
                print("Converting WKB geometry to shapely objects...")
                onshore_country['geometry'] = onshore_country['geometry'].apply(wkb.loads)
            elif isinstance(sample_geom, str):
                print("Converting WKT geometry to shapely objects...")
                onshore_country['geometry'] = onshore_country['geometry'].apply(wkt.loads)
            else:
                print("Geometry column already in proper format")
        
        # Convert to GeoDataFrame
        onshore_country = gpd.GeoDataFrame(onshore_country, geometry='geometry')
        
        # Get centroids for clustering
        onshore_country['centroid'] = onshore_country.geometry.centroid
        onshore_country['lon'] = onshore_country.centroid.x
        onshore_country['lat'] = onshore_country.centroid.y
    elif 'centroid_lat' in onshore_country.columns and 'centroid_lon' in onshore_country.columns:
        # Use existing centroid coordinates
        onshore_country['lat'] = onshore_country['centroid_lat']
        onshore_country['lon'] = onshore_country['centroid_lon']
    
    # 4. Load Atlite data for these specific cells
    print("\nLoading Atlite profiles...")
    grid_cells = onshore_country['grid_cell'].unique() if 'grid_cell' in onshore_country.columns else None
    
    if grid_cells is not None:
        # Load only data for these cells
        atlite_df = pd.read_parquet(
            '../data/hourly_profiles/atlite_grid_cell_2013_ITA_only.parquet',
            filters=[('grid_cell', 'in', grid_cells)]
        )
    else:
        # Load all country data
        atlite_df = pd.read_parquet('../data/hourly_profiles/atlite_grid_cell_2013_ITA_only.parquet')
        atlite_df = atlite_df[atlite_df['grid_cell'].str.startswith(f'{country_code}_')]
    
    print(f"Loaded {len(atlite_df):,} profile rows")
    
    # 5. Load grid infrastructure
    print("\nLoading grid infrastructure...")
    buses = pd.read_csv('../data/OSM-Eur-prebuilt/buses.csv')
    lines = pd.read_csv('../data/OSM-Eur-prebuilt/lines.csv')
    
    buses['iso'] = buses['country'].apply(get_iso3_from_iso2)

    
    # Filter buses to country if possible
    if 'country' in buses.columns:
        buses_country = buses[buses['iso'] == country_code]
    else:
        buses_country = buses  # Will filter by proximity later
    
    print(f"Found {len(buses_country)} buses in {country_code}")
    
    return {
        'onshore': onshore_country,
        'offshore': offshore_zones,
        'atlite': atlite_df,
        'buses': buses_country,
        'lines': lines
    }

# Load everything - now supports both ISO2 and ISO3
# data = load_all_data_properly('DE')  # Will be converted to 'DEU'

# Show what we have
# print("\n=== Data Summary ===")
# print(f"Onshore zones: {data['onshore'].shape}")
# print(f"Atlite profiles: {data['atlite']['grid_cell'].nunique()} unique cells")
# print(f"Grid infrastructure: {len(data['buses'])} buses")

# ============================================================================
# STEP 1: Load and reshape Atlite data efficiently
# ============================================================================
def load_and_reshape_atlite(atlite_df, year=2013):
    """
    Reshape the atlite dataset efficiently with proper datetime indexing
    """
    print(f"\n=== STEP 1: Reshaping Atlite Data ===")
    
    # Create datetime column
    print("Creating datetime index...")
    atlite_df = atlite_df.copy()
    atlite_df['datetime'] = pd.to_datetime(
        atlite_df[['month', 'day', 'hour']].assign(year=year)
    )
    
    # Create hour index (0-8759 for full year)
    # More accurate calculation than the original
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    def get_hour_idx(row):
        # Calculate cumulative days up to current month
        cumulative_days = sum(days_in_month[:row['month']-1])
        # Add current day and hour
        return (cumulative_days + row['day'] - 1) * 24 + row['hour']
    
    print("Calculating hour indices...")
    atlite_df['hour_idx'] = atlite_df.apply(get_hour_idx, axis=1)
    
    unique_cells = atlite_df['grid_cell'].unique()
    n_cells = len(unique_cells)
    n_hours = atlite_df['hour_idx'].nunique()
    
    print(f"Found {n_cells:,} unique grid cells")
    print(f"Found {n_hours:,} unique hours")
    print(f"Total data points: {len(atlite_df):,}")
    
    return atlite_df, unique_cells


def prepare_profiles(re_profile, cells, zones_gdf, is_offwind=False):
    coords = []
    valid_cells = []
    for cell in cells:
        if is_offwind:
            cell_to_match = 'wof-' + cell
        else:
            cell_to_match = cell
        zone_match = zones_gdf[zones_gdf['grid_cell'] == cell_to_match]
        if not zone_match.empty:
            lat = zone_match.iloc[0]['lat']
            lon = zone_match.iloc[0]['lon']
        
            coords.append([lat, lon])
            valid_cells.append(cell)

    coords = np.array(coords)

    # Filter profiles to only valid cells
    re_profile_filtered = re_profile.loc[valid_cells] if len(valid_cells) > 0 else re_profile
    
    return {
        'cells': np.array(valid_cells),
        'coords': coords,
        're_profile_df': re_profile_filtered
    }

# Apply Step 1
# atlite_reshaped, unique_cells = load_and_reshape_atlite(data['atlite'])
# print(f"✅ Step 1 complete: {len(unique_cells)} cells with hourly profiles")

# ============================================================================
# STEP 2: Extract cell profiles and create pivot tables
# ============================================================================
def extract_cell_profiles(atlite_df_iso, zones_gdf,iso_processor):
    """
    Extract profiles for cells and create pivot tables for clustering
    """

    print(f"\n=== STEP 2: Extracting Cell Profiles ===")
    
    print(f"Processing {len(zones_gdf)} cells...")
    
    # Create pivot tables for each technology
    print("Creating pivot tables...")
    
    # filter grid cells to only those with resonable resource quality
    good_solar_cells = atlite_df_iso.groupby('grid_cell')['solar_capacity_factor'].mean().reset_index()
    if (good_solar_cells['solar_capacity_factor'] > 0.05).sum() > 5:
        good_solar_cells = good_solar_cells[good_solar_cells['solar_capacity_factor'] >= 0.05]
    good_wind_cells = atlite_df_iso.groupby('grid_cell')['wind_capacity_factor'].mean().reset_index()
    if (good_wind_cells['wind_capacity_factor'] > 0.08).sum() > 5:
        good_wind_cells = good_wind_cells[good_wind_cells['wind_capacity_factor'] >= 0.08]
    good_offwind_cells = atlite_df_iso.groupby('grid_cell')['offwind_capacity_factor'].mean().reset_index()
    if (good_offwind_cells['offwind_capacity_factor'] > 0.2).sum() > 5:
        good_offwind_cells = good_offwind_cells[good_offwind_cells['offwind_capacity_factor'] >= 0.2]

    print("Number of cells after CF filtering:")
    print(f"Number of solar cells: {len(good_solar_cells)}")
    print(f"Number of wind (onshore) cells: {len(good_wind_cells)}")
    print(f"Number of wind (offshore) cells: {len(good_offwind_cells)}")

    # remove grid cells that have <1MW capacity
    df_solar_iso = iso_processor.df_solar_rezoning
    df_windon_iso = iso_processor.df_windon_rezoning
    df_windoff_iso = iso_processor.df_windoff_rezoning
    df_windoff_iso['grid_cell'] = df_windoff_iso['grid_cell'].str.replace('wof-', '')

    available_solar_cells = df_solar_iso.merge(good_solar_cells, 
    on='grid_cell', how='inner')[['grid_cell','Installed Capacity Potential (MW)','solar_capacity_factor']]
    available_wind_cells = df_windon_iso.merge(good_wind_cells, 
    on='grid_cell', how='inner')[['grid_cell','Installed Capacity Potential (MW)','wind_capacity_factor']]
    available_offwind_cells = df_windoff_iso.merge(good_offwind_cells, 
    on='grid_cell', how='inner')[['grid_cell','Installed Capacity Potential (MW)','offwind_capacity_factor']]

    if (available_solar_cells['Installed Capacity Potential (MW)'] > 1).sum() > 5:
        available_solar_cells = available_solar_cells[available_solar_cells['Installed Capacity Potential (MW)'] > 1]
    available_solar_cells = available_solar_cells.rename(columns={'solar_capacity_factor': 'Capacity Factor'})

    if (available_wind_cells['Installed Capacity Potential (MW)'] > 1).sum() > 5:
        available_wind_cells = available_wind_cells[available_wind_cells['Installed Capacity Potential (MW)'] > 1]
    available_wind_cells = available_wind_cells.rename(columns={'wind_capacity_factor': 'Capacity Factor'})

    if (available_offwind_cells['Installed Capacity Potential (MW)'] > 1).sum() > 5:
        available_offwind_cells = available_offwind_cells[available_offwind_cells['Installed Capacity Potential (MW)'] > 1]
    available_offwind_cells = available_offwind_cells.rename(columns={'offwind_capacity_factor': 'Capacity Factor'})

    print("Number of cells after capacity filtering:")
    print(f"Number of solar cells: {len(available_solar_cells)}")
    print(f"Number of wind (onshore) cells: {len(available_wind_cells)}")
    print(f"Number of wind (offshore) cells: {len(available_offwind_cells)}")

    # Wind profiles (cells x hours)
    wind_profiles = atlite_df_iso[atlite_df_iso['grid_cell'].isin(available_wind_cells['grid_cell'])].pivot_table(
        index='grid_cell',
        columns='hour_idx',
        values='wind_capacity_factor',
        aggfunc='mean'
    )
    
    # Solar profiles (cells x hours)
    solar_profiles = atlite_df_iso[atlite_df_iso['grid_cell'].isin(available_solar_cells['grid_cell'])].pivot_table(
        index='grid_cell',
        columns='hour_idx',
        values='solar_capacity_factor',
        aggfunc='mean'
    )
    
    # Offwind profiles (cells x hours)
    offwind_profiles = atlite_df_iso[atlite_df_iso['grid_cell'].isin(available_offwind_cells['grid_cell'])].pivot_table(
        index='grid_cell',
        columns='hour_idx',
        values='offwind_capacity_factor',
        aggfunc='mean'
    )
    
    print(f"Wind profiles shape: {wind_profiles.shape}")
    print(f"Solar profiles shape: {solar_profiles.shape}")
    print(f"Offwind profiles shape: {offwind_profiles.shape}")
    
    if not available_wind_cells.empty:
        profiles_won = prepare_profiles(wind_profiles, available_wind_cells['grid_cell'], zones_gdf)
        profiles_won['mw_wt'] = available_wind_cells
    else:
        profiles_won = {}
    if not available_solar_cells.empty:
        profiles_solar = prepare_profiles(solar_profiles, available_solar_cells['grid_cell'], zones_gdf)
        profiles_solar['mw_wt'] = available_solar_cells
    else:
        profiles_solar = {}

    if not available_offwind_cells.empty:
        profiles_offwind = prepare_profiles(offwind_profiles, available_offwind_cells['grid_cell'], zones_gdf, is_offwind=True)
        profiles_offwind['mw_wt'] = available_offwind_cells
    else:
        profiles_offwind = {}

    return {
        'profiles_won': profiles_won,
        'profiles_solar': profiles_solar,
        'profiles_offwind': profiles_offwind,
    }


# Apply Step 2
# profiles = extract_cell_profiles(atlite_reshaped, data['onshore'])
# print(f"✅ Step 2 complete: Extracted profiles for {len(profiles['cells'])} cells")

# ============================================================================
# STEP 3: Process grid infrastructure with coordinate conversion
# ============================================================================
def process_grid_infrastructure(buses_df, lines_df):
    """
    Process the OSM grid data with proper coordinate handling and voltage classification
    """
    print(f"\n=== STEP 3: Processing Grid Infrastructure ===")
    
    print(f"Processing {len(buses_df)} buses and {len(lines_df)} lines...")
    
    # Check coordinate system
    print(f"X range: {buses_df['x'].min():.2f} to {buses_df['x'].max():.2f}")
    print(f"Y range: {buses_df['y'].min():.2f} to {buses_df['y'].max():.2f}")
    
    # The coordinates are already in lat/lon format for European data
    if buses_df['x'].min() > -180 and buses_df['x'].max() < 180:
        # Already lat/lon, just assign properly
        buses_df = buses_df.copy()
        buses_df['lat'] = buses_df['y']
        buses_df['lon'] = buses_df['x']
        print("Coordinates are already in lat/lon format")
    else:
        # Would need coordinate transformation, but European data should be lat/lon
        print("Warning: Coordinates may need transformation")
        buses_df = buses_df.copy()
        buses_df['lat'] = buses_df['y']
        buses_df['lon'] = buses_df['x']
    
    # Clean and classify voltage data
    print("Processing voltage data...")
    
    # Handle voltage conversion (some data in V, some in kV)
    buses_df['voltage_kv'] = buses_df['voltage'].copy()
    
    # Convert from V to kV if needed
    high_voltage_mask = buses_df['voltage'] > 10000
    if high_voltage_mask.any():
        buses_df.loc[high_voltage_mask, 'voltage_kv'] = buses_df.loc[high_voltage_mask, 'voltage'] / 1000
        print(f"Converted {high_voltage_mask.sum()} voltage values from V to kV")
    
    # Categorize by voltage level (European grid standards)
    voltage_bins = [0, 50, 150, 300, 500, 1000]
    voltage_labels = ['distribution', 'sub_transmission', 'transmission_low', 
                     'transmission_high', 'extra_high']
    
    buses_df['voltage_class'] = pd.cut(
        buses_df['voltage_kv'],
        bins=voltage_bins,
        labels=voltage_labels,
        include_lowest=True
    )
    
    print("\nVoltage distribution:")
    voltage_counts = buses_df['voltage_class'].value_counts()
    print(voltage_counts)
    
    # Calculate some grid statistics
    print(f"\nGrid statistics:")
    print(f"  - Latitude range: {buses_df['lat'].min():.2f} to {buses_df['lat'].max():.2f}")
    print(f"  - Longitude range: {buses_df['lon'].min():.2f} to {buses_df['lon'].max():.2f}")
    print(f"  - Voltage range: {buses_df['voltage_kv'].min():.1f} to {buses_df['voltage_kv'].max():.1f} kV")
    
    # Filter to transmission level and above (>=150kV) for clustering
    transmission_buses = buses_df[buses_df['voltage_kv'] >= 150].copy()
    print(f"  - Transmission buses (>=150kV): {len(transmission_buses)}")
    
    return buses_df, transmission_buses

# Apply Step 3
# buses_processed, transmission_buses = process_grid_infrastructure(data['buses'], data['lines'])
# print(f"✅ Step 3 complete: Processed {len(buses_processed)} buses, {len(transmission_buses)} transmission-level")

# ============================================================================
# STEP 4: Smart clustering pipeline with weighted features
# ============================================================================
def smart_clustering_pipeline(
    profiles, 
    buses_df,
    use_transmission_only=True,
    iso3_code=None,
    technology=None,
    output_dir=None,
    validate_land_centroids=True
):
    """
    Complete clustering pipeline combining renewable profiles, grid proximity, and spatial features
    """
    
    # Load land mask for centroid validation if requested
    land_gdf = None
    if validate_land_centroids:
        land_gdf = load_land_mask(iso3_code)
    
    # Calculate dynamic number of clusters based on cell count
    n_cells = len(profiles['cells'])
    n_clusters = int(np.clip(n_cells ** 0.6, 10, 300))

    print(f"\n=== STEP 4: Smart Clustering Pipeline ===")
    print(f"Found {n_cells} cells")
    
    # If fewer than 5 cells, return each cell as its own cluster
    if n_cells < 5:
        print(f"Too few cells ({n_cells}) for meaningful clustering. Returning individual cells as clusters.")
        clusters = np.arange(1, n_cells + 1)  # Each cell gets its own cluster ID (1, 2, 3, ...)
        
        # Create simple cluster statistics
        cluster_stats = []
        for i, cell in enumerate(profiles['cells']):
            stats = {
                'cluster_id': int(clusters[i]),
                'n_cells': 1,
                'avg_re_cf': float(profiles['re_profile_df'].iloc[i].mean()) if 're_profile_df' in profiles else 0.0,
                'std_re_cf': float(profiles['re_profile_df'].iloc[i].std()) if 're_profile_df' in profiles else 0.0,
                'avg_grid_dist_km': 0.0,  # Will be calculated if needed
                'min_grid_dist_km': 0.0,
                'max_grid_dist_km': 0.0,
                'centroid_lat': float(profiles['coords'][i, 0]),
                'centroid_lon': float(profiles['coords'][i, 1]),
                'lat_span': 0.0,
                'lon_span': 0.0,
                'total_re_capacity_mw': 0.0,
            }
            cluster_stats.append(stats)
        
        cluster_df = pd.DataFrame(cluster_stats)
        
        # Save outputs
        import os
        os.makedirs(output_dir, exist_ok=True)
        tech_suffix = f"_{technology}" if technology else ""
        
        # Save cluster summary statistics
        stats_file = f'{output_dir}/cluster_summary{tech_suffix}.csv'
        cluster_df.to_csv(stats_file, index=False)
        print(f"Saved individual cell statistics: {stats_file}")
        
        # Save cell to cluster mapping (each cell maps to itself)
        cell_mapping = pd.DataFrame({
            'grid_cell': profiles['cells'],
            'cluster_id': clusters,
            'lat': profiles['coords'][:, 0],
            'lon': profiles['coords'][:, 1],
            'grid_distance_km': np.zeros(n_cells),
            'nearest_bus_idx': np.zeros(n_cells, dtype=int)
        })
        mapping_file = f'{output_dir}/cell_to_cluster_mapping{tech_suffix}.csv'
        cell_mapping.to_csv(mapping_file, index=False)
        print(f"Saved individual cell mapping: {mapping_file}")
        
        return clusters, cluster_df, None, {
            'feature_names': [],
            'weights': [],
            'distances_km': np.zeros(n_cells),
            'nearest_bus_idx': np.zeros(n_cells, dtype=int)
        }
    
    # Proceed with normal clustering for 5+ cells
    n_clusters = int(np.clip(n_cells ** 0.6, 10, 300))
    print(f"Target clusters: {n_clusters}")
    if validate_land_centroids and land_gdf is not None:
        print(f"Land validation: Enabled (using {len(land_gdf)} land polygons)")
    elif validate_land_centroids:
        print(f"Land validation: Disabled (could not load land mask)")
    else:
        print(f"Land validation: Disabled (user preference)")
    
    # Set default values for output parameters
    if output_dir is None:
        output_dir = 'output'
    if iso3_code is None:
        iso3_code = 'UNKNOWN'
    
    # Technology filtering (if specified)
    if technology:
        print(f"Filtering for {technology} technology...")
        print(f"   -> Using {technology} profiles for {len(profiles['cells'])} cells")

    
    # Use transmission buses for better grid connectivity
    grid_buses = buses_df if not use_transmission_only else buses_df[buses_df['voltage_kv'] >= 150]
    print(f"Using {len(grid_buses)} grid buses for distance calculation")
    
    # 1. Calculate grid distances using KDTree for efficiency
    print("Calculating distances to grid infrastructure...")
    bus_tree = cKDTree(grid_buses[['lat', 'lon']].values)
    distances_deg, nearest_idx = bus_tree.query(profiles['coords'])
    distances_km = distances_deg * 111.32  # Convert degrees to km (approximate)
    
    print(f"Grid connectivity stats:")
    print(f"  - Average distance to grid: {distances_km.mean():.1f} km")
    print(f"  - Max distance to grid: {distances_km.max():.1f} km")
    print(f"  - Min distance to grid: {distances_km.min():.1f} km")
    
    # 2. Prepare and normalize features for clustering
    print("\nPreparing features for clustering...")
    features = []
    feature_names = []
    weights = []
    
    # Technology-specific feature selection
    # Solar-only clustering
    print("Processing solar profiles...")

    re_df = profiles['re_profile_df']
    re_array = re_df.values
    re_array = np.nan_to_num(re_array, nan=0.0)
        
    # Normalize profiles
    re_mean = re_array.mean(axis=1, keepdims=True)
    re_norm = re_array / (re_mean + 1e-6)
    
    # Apply PCA
    from sklearn.decomposition import PCA
    pca_re = PCA(n_components=min(50, re_norm.shape[0]-1), svd_solver='full')
    re_reduced = pca_re.fit_transform(re_norm)
    
    features.append(re_reduced)
    feature_names.append(f're_pca_{re_reduced.shape[1]}')
    weights.append(0.50)  # Higher weight for the main technology
    
    print(f"  - Solar PCA: {re_reduced.shape[1]} components, {pca_re.explained_variance_ratio_.sum():.1%} variance")
        
    
    # Grid distance feature (connectivity importance)
    grid_dist_norm = (distances_km / distances_km.max()).reshape(-1, 1)
    features.append(grid_dist_norm)
    feature_names.append('grid_distance')
    weights.append(0.40)
    
    # Spatial coordinates (for geographic contiguity)
    coords_norm = (profiles['coords'] - profiles['coords'].mean(axis=0)) / profiles['coords'].std(axis=0)
    features.append(coords_norm)
    feature_names.append('spatial_coords')
    weights.append(0.10)
    
    print(f"Feature summary:")
    for name, weight in zip(feature_names, weights):
        print(f"  - {name}: weight {weight}")
    
    # 3. Combine features with weights
    print("\nCombining weighted features...")
    weighted_features = []
    for feat, w in zip(features, weights):
        weighted_features.append(feat * np.sqrt(w))  # sqrt for better scaling
    
    X = np.hstack(weighted_features)
    print(f"Final feature matrix: {X.shape}")
    
    # 4. Hierarchical clustering with Ward's method
    print(f"\nPerforming hierarchical clustering...")
    from scipy.cluster.hierarchy import linkage, fcluster
    
    # Use Ward's method for compact, balanced clusters
    linkage_matrix = linkage(X, method='ward')
    clusters = fcluster(linkage_matrix, n_clusters, criterion='maxclust')
    
    n_clusters_actual = len(np.unique(clusters))
    print(f"Created {n_clusters_actual} clusters")
    
    # 5. Calculate cluster statistics and quality metrics
    print("Calculating cluster statistics...")
    cluster_stats = []
    
    for c in np.unique(clusters):
        mask = clusters == c
        n_cells_in_cluster = mask.sum()
        cluster_cells = profiles['cells'][mask]
        
        # Check for duplicate cells in this cluster
        if len(cluster_cells) != len(np.unique(cluster_cells)):
            print(f"    ! Cluster {c} has duplicate cells: {len(cluster_cells)} total, {len(np.unique(cluster_cells))} unique")
            duplicate_cells = pd.Series(cluster_cells).value_counts()
            duplicated_cells = duplicate_cells[duplicate_cells > 1]
            if len(duplicated_cells) > 0:
                print(f"    Duplicated cells: {duplicated_cells.head(3).to_dict()}")
        
        try:
            # Calculate REZoning capacities if data is available
            total_re_capacity_mw = 0
            re_cluster = None
            
            re_cluster = profiles['mw_wt']
            if re_cluster is not None and not re_cluster.empty:
                # Check for and report duplicates
                original_count = len(re_cluster)
                duplicates = re_cluster[re_cluster.duplicated(subset=['grid_cell'], keep=False)]
                if not duplicates.empty:
                    print(f"  ! Found {len(duplicates)} duplicate grid_cell entries in mw_wt data:")
                    duplicate_cells = duplicates['grid_cell'].value_counts()
                    for cell, count in duplicate_cells.head(5).items():
                        print(f"    - {cell}: {count} entries")
                    if len(duplicate_cells) > 5:
                        print(f"    - ... and {len(duplicate_cells) - 5} more cells with duplicates")
                
                # Remove duplicates to avoid reindexing issues
                re_cluster = re_cluster.drop_duplicates(subset=['grid_cell']).reset_index(drop=True)
                deduplicated_count = len(re_cluster)
                
                if original_count != deduplicated_count:
                    print(f"  + Deduplicated mw_wt: {original_count} -> {deduplicated_count} entries ({original_count - deduplicated_count} duplicates removed)")
                
                # Filter to only cells in this cluster
                cluster_re_subset = re_cluster[re_cluster['grid_cell'].isin(cluster_cells)]
                total_re_capacity_mw = cluster_re_subset['Installed Capacity Potential (MW)'].sum()
            else:
                total_re_capacity_mw = 0
                        
            # Calculate capacity weights for grid distance
            capacity_weights = []
            for cell in cluster_cells:
                re_cap = 0
                if re_cluster is not None and not re_cluster.empty:
                    cell_re = re_cluster[re_cluster['grid_cell'] == cell]
                    if not cell_re.empty:
                        # Handle potential duplicates by taking the first unique match
                        cell_re = cell_re.drop_duplicates(subset=['grid_cell'])
                        re_cap = cell_re['Installed Capacity Potential (MW)'].iloc[0]
                capacity_weights.append(re_cap)
            
                
                # Filter re_cluster to only cells in this cluster
                cluster_re_data = None
                if re_cluster is not None and not re_cluster.empty:
                    cluster_re_data = re_cluster[re_cluster['grid_cell'].isin(cluster_cells)]
                    # Remove any remaining duplicates within the cluster data
                    if not cluster_re_data.empty:
                        cluster_re_data = cluster_re_data.drop_duplicates(subset=['grid_cell']).reset_index(drop=True)
            
            
            # Calculate statistics for this cluster
            stats = {
                'cluster_id': int(c),
                'n_cells': int(n_cells_in_cluster),
                'avg_re_cf': float(
                    # Use capacity-weighted average CF, handling potential shape issues
                    np.average(cluster_re_data['Capacity Factor'].values.flatten(), 
                              weights=cluster_re_data['Installed Capacity Potential (MW)'].values.flatten())
                ) if cluster_re_data is not None and not cluster_re_data.empty and cluster_re_data['Installed Capacity Potential (MW)'].sum() > 0 and 'Capacity Factor' in cluster_re_data.columns else (
                    float(profiles['re_profile_df'].iloc[mask].mean().mean()) if 're_profile_df' in profiles and profiles['re_profile_df'] is not None else 0.0
                ),
                'std_re_cf': float(profiles['re_profile_df'].iloc[mask].std().mean()) if 're_profile_df' in profiles and profiles['re_profile_df'] is not None else 0.0,
                'avg_grid_dist_km': float(np.average(distances_km[mask], weights=capacity_weights)) if capacity_weights and sum(capacity_weights) > 0 else float(distances_km[mask].mean()),
                'min_grid_dist_km': float(distances_km[mask].min()),
                'max_grid_dist_km': float(distances_km[mask].max()),
                'centroid_lat': 0.0,  # Will be calculated with land validation below
                'centroid_lon': 0.0,  # Will be calculated with land validation below
                'lat_span': float(profiles['coords'][mask, 0].max() - profiles['coords'][mask, 0].min()),
                'lon_span': float(profiles['coords'][mask, 1].max() - profiles['coords'][mask, 1].min()),
                'total_re_capacity_mw': float(total_re_capacity_mw),
            }
            
            # Calculate capacity-weighted centroid
            cluster_coords = profiles['coords'][mask]
            
            # Use capacity weights if available, otherwise fall back to equal weights
            if capacity_weights and len(capacity_weights) == len(cluster_coords):
                # Capacity-weighted centroid
                # Raise capacity_weights to the power of 1.5 for weighting
                weights_array = np.array(capacity_weights) ** 1.5
                
                # Handle case where all weights are zero
                if weights_array.sum() > 0:
                    initial_lat = float(np.average(cluster_coords[:, 0], weights=weights_array))
                    initial_lon = float(np.average(cluster_coords[:, 1], weights=weights_array))
                else:
                    # Fallback to simple mean if all capacities are zero
                    initial_lat = float(cluster_coords[:, 0].mean())
                    initial_lon = float(cluster_coords[:, 1].mean())
            else:
                # Fallback to simple mean if capacity data not available
                initial_lat = float(cluster_coords[:, 0].mean())
                initial_lon = float(cluster_coords[:, 1].mean())
            
            # Validate centroid with land mask if enabled
            if validate_land_centroids and land_gdf is not None:
                # Validate and correct centroid if needed
                corrected_lat, corrected_lon = validate_and_correct_centroid(
                    initial_lat, initial_lon, land_gdf, cluster_coords, technology
                )
                
                # Update stats with corrected coordinates
                stats['centroid_lat'] = corrected_lat
                stats['centroid_lon'] = corrected_lon
            else:
                # Use calculated centroid without land validation
                stats['centroid_lat'] = initial_lat
                stats['centroid_lon'] = initial_lon
            
            cluster_stats.append(stats)
                
        except Exception as e:
            print(f"    - Error calculating statistics for cluster {c}: {e}")
            print(f"    Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise e
    
    cluster_df = pd.DataFrame(cluster_stats)
    
    print("\nCluster summary statistics:")
    print(f"  - Cluster sizes: {cluster_df['n_cells'].describe()}")
    print(f"  - Avg re CF: {cluster_df['avg_re_cf'].mean():.3f} +/- {cluster_df['avg_re_cf'].std():.3f}")
    print(f"  - Avg grid distance: {cluster_df['avg_grid_dist_km'].mean():.1f} +/- {cluster_df['avg_grid_dist_km'].std():.1f} km")
    
    # Save technology-specific files before returning
    import os
    os.makedirs(output_dir, exist_ok=True)
    tech_suffix = f"_{technology}" if technology else ""
    
    # Save cluster summary statistics
    stats_file = f'{output_dir}/cluster_summary{tech_suffix}.csv'
    cluster_df.to_csv(stats_file, index=False)
    print(f"Saved statistics: {stats_file}")
    
    # Save cell to cluster mapping
    cell_mapping = pd.DataFrame({
        'grid_cell': profiles['cells'],
        'cluster_id': clusters,
        'lat': profiles['coords'][:, 0],
        'lon': profiles['coords'][:, 1],
        'grid_distance_km': distances_km,
        'nearest_bus_idx': nearest_idx
    })
    mapping_file = f'{output_dir}/cell_to_cluster_mapping{tech_suffix}.csv'
    cell_mapping.to_csv(mapping_file, index=False)
    print(f"Saved mapping: {mapping_file}")
    
    # Create validation plot (commented out for production)
    # try:
    #     create_cluster_validation_plot(clusters, profiles, cluster_df, land_gdf, iso3_code or 'UNKNOWN')
    # except Exception as e:
    #     print(f"   ⚠️  Could not create validation plot: {e}")
    
    return clusters, cluster_df, linkage_matrix, {
        'feature_names': feature_names,
        'weights': weights,
        'distances_km': distances_km,
        'nearest_bus_idx': nearest_idx
    }, cell_mapping

# Apply Step 4 - test with 75 clusters for Germany
# clusters, cluster_stats, linkage_matrix, clustering_info = smart_clustering_pipeline(
#     profiles, 
#     transmission_buses,
#     n_clusters=50
# )
# print(f"✅ Step 4 complete: Created {len(np.unique(clusters))} renewable energy clusters")

# ============================================================================
# STEP 5: Visualize and export results
# ============================================================================
def visualize_and_export(clusters, profiles, cluster_stats, buses_df, zones_gdf=None, country_code='ITA', clustering_info=None, output_dir=None, technology=None):
    """
    Create comprehensive visualizations and export results for ESOM integration
    
    Parameters:
    -----------
    clusters : array
        Cluster assignments for each cell
    profiles : dict
        Dictionary containing cells, coords, and profile data
    cluster_stats : DataFrame
        Statistics for each cluster
    buses_df : DataFrame
        Bus infrastructure data
    zones_gdf : GeoDataFrame, optional
        GeoDataFrame with zone geometries for polygon visualization.
        If provided, will create filled polygon maps instead of scatter plots.
    country_code : str
        ISO country code
    clustering_info : dict, optional
        Additional clustering metadata
    output_dir : str, optional
        Output directory path
    technology : str, optional
        Technology type ('solar', 'wind_onshore', 'wind_offshore')
    """
    print(f"\n=== STEP 5: Visualization and Export ===")
    
    # Check if clustering_info is provided
    if clustering_info is None:
        print("Warning: clustering_info not provided, creating dummy values")
        clustering_info = {
            'distances_km': np.zeros(len(clusters)),
            'nearest_bus_idx': np.zeros(len(clusters), dtype=int)
        }
    
    # Create output directory
    import os
    if output_dir is None:
        output_dir = f'output_{country_code.lower()}'
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # 1. Create comprehensive map visualization
    print("Creating cluster map visualization...")
    
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    
    # Technology-specific main title
    if technology == 'solar':
        main_title = f'Solar Energy Clustering Results - {country_code}'
    elif technology == 'wind_onshore':
        main_title = f'Wind Onshore Clustering Results - {country_code}'
    elif technology == 'wind_offshore':
        main_title = f'Wind Offshore Clustering Results - {country_code}'
    else:
        main_title = f'Renewable Energy Clustering Results - {country_code}'
    
    fig.suptitle(main_title, fontsize=16, fontweight='bold')
    
    # Plot 1: Cluster map with colors
    ax1 = axes[0, 0]
    
    # Plot grid infrastructure first (background)
    if not buses_df.empty:
        ax1.scatter(buses_df['lon'], buses_df['lat'], 
                   c='lightgray', s=10, alpha=0.5, label='Grid buses')
    
    # Create cluster capacity factor mapping for coloring
    cluster_cf_map = {}
    if technology in ['solar', 'wind_onshore', 'wind_offshore']:
        for _, row in cluster_stats.iterrows():
            cluster_cf_map[row['cluster_id']] = row['avg_re_cf']
        
        if technology == 'solar':
            cf_label = 'Solar Capacity Factor'
            title_suffix = 'Solar'
        elif technology == 'wind_onshore':
            cf_label = 'Wind Capacity Factor'
            title_suffix = 'Wind'
        elif technology == 'wind_offshore':
            cf_label = 'Offshore Wind Capacity Factor'
            title_suffix = 'Offshore Wind'
        else:
            cf_label = 'RE Capacity Factor'
            title_suffix = 'RE'

    # Color individual grid cells by cluster average capacity factor
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors
    
    print("Coloring individual grid cells by cluster CF...")
    
    # Create colormap for CF values
    cf_values = list(cluster_cf_map.values())
    if len(cf_values) == 0:
        print("  ! No capacity factor values found, using default colors")
        cf_values = [0.0, 1.0]  # Default range
    
    norm = mcolors.Normalize(vmin=min(cf_values), vmax=max(cf_values))
    colormap = cm.get_cmap('viridis')
    
    # Color each cell by its cluster's CF
    cell_colors = []
    for i, cluster_id in enumerate(clusters):
        cluster_cf = cluster_cf_map.get(cluster_id, 0.2)  # Default CF if not found
        color = colormap(norm(cluster_cf))
        cell_colors.append(color)
    
    # Create geometry plot if zones_gdf is available, otherwise fall back to scatter
    if zones_gdf is not None and hasattr(zones_gdf, 'geometry') and not zones_gdf.empty:
        print("  - Using polygon geometries for visualization...")
        
        # Create mapping from cells to capacity factors
        actual_cf_values = [cluster_cf_map.get(cluster_id, 0.2) for cluster_id in clusters]
        
        # Create a dataframe mapping cells to CF values
        cell_cf_mapping = pd.DataFrame({
            'grid_cell': profiles['cells'],
            'cf_value': actual_cf_values
        })
        
        # Handle offshore wind prefix matching
        if technology == 'wind_offshore':
            # For offshore wind, we only need to match 'wof-' prefixed cells
            cell_cf_mapping['grid_cell'] = 'wof-' + cell_cf_mapping['grid_cell']

        
        # Merge zones with capacity factor data
        zones_with_cf = zones_gdf.merge(cell_cf_mapping, on='grid_cell', how='inner')
        
        if not zones_with_cf.empty:
            print(f"  - Successfully mapped {len(zones_with_cf)} zones to capacity factors")
            
            # Create the polygon plot using geopandas
            gdf_plot = zones_with_cf.plot(
                column='cf_value',
                ax=ax1,
                cmap='viridis',
                vmin=min(cf_values),
                vmax=max(cf_values),
                alpha=0.8,
                edgecolor='white',
                linewidth=0.3,
                legend=False  # We'll create our own colorbar
            )
            
            # Create a mappable object for the colorbar
            from matplotlib.cm import ScalarMappable
            sm = ScalarMappable(norm=mcolors.Normalize(vmin=min(cf_values), vmax=max(cf_values)), cmap='viridis')
            sm.set_array([])  # This is needed for matplotlib
            scatter = sm  # Use this for colorbar creation
            
            print(f"  - Plotted {len(zones_with_cf)} grid cell polygons by cluster CF")
        else:
            print(f"  ! No zones matched to capacity factors, falling back to scatter plot")
            # Fall back to scatter plot
            actual_cf_values = [cluster_cf_map.get(cluster_id, 0.2) for cluster_id in clusters]
            scatter = ax1.scatter(
                profiles['coords'][:, 1],  # longitude
                profiles['coords'][:, 0],  # latitude
                c=actual_cf_values,
                s=20,
                alpha=0.8,
                edgecolors='white',
                linewidth=0.3,
                cmap='viridis',
                vmin=min(cf_values),
                vmax=max(cf_values),
                label='Grid cells (colored by cluster CF)'
            )
    else:
        print("  - No geometry data available, using scatter plot...")
        # Fall back to original scatter plot
        actual_cf_values = [cluster_cf_map.get(cluster_id, 0.2) for cluster_id in clusters]
        scatter = ax1.scatter(
            profiles['coords'][:, 1],  # longitude
            profiles['coords'][:, 0],  # latitude
            c=actual_cf_values,
            s=20,
            alpha=0.8,
            edgecolors='white',
            linewidth=0.3,
            cmap='viridis',
            vmin=min(cf_values),
            vmax=max(cf_values),
            label='Grid cells (colored by cluster CF)'
        )
    
    print(f"  - Colored {len(profiles['coords'])} grid cell points by cluster CF")
    
    ax1.set_title(f'{len(np.unique(clusters))} {title_suffix} Clusters (Colored by Avg CF)')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Add colorbar with actual CF values
    # cbar1 = plt.colorbar(scatter, ax=ax1)
    # cbar1.set_label(cf_label)
    
    # Plot 2: Technology-specific capacity factors
    ax2 = axes[0, 1]
    
    scatter2 = ax2.scatter(
        cluster_stats['avg_grid_dist_km'],
        cluster_stats['avg_re_cf'],
        s=cluster_stats['n_cells'] * 20,  # Size by number of cells
        c=cluster_stats['avg_re_cf'],
        cmap='viridis',
        alpha=0.7,
        edgecolors='black',
        linewidth=0.5
    )
    ax2.set_xlabel('Average Grid Distance (km)')
    ax2.set_ylabel('Average RE Capacity Factor')
    ax2.set_title('RE Cluster Characteristics\n(Size = # cells, Color = RE CF)')
    
    ax2.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar2 = plt.colorbar(scatter2, ax=ax2)
    cbar2.set_label(cf_label)
    # if technology == 'solar':
    #     cbar2.set_label('Solar Capacity Factor')
    # elif technology == 'wind_onshore':
    #     cbar2.set_label('Wind Capacity Factor')
    # elif technology == 'wind_offshore':
    #     cbar2.set_label('Offshore Wind Capacity Factor')
    # else:
    #     raise ValueError(f"Unsupported technology for colorbar: {technology}. Use 'solar' or 'wind_onshore' or 'wind_offshore'.")
    
    # Plot 3: Cluster sizes distribution
    ax3 = axes[1, 0]
    cluster_sizes = cluster_stats['n_cells'].values
    ax3.hist(cluster_sizes, bins=max(10, len(np.unique(cluster_sizes))), 
             alpha=0.7, color='skyblue', edgecolor='black')
    ax3.set_xlabel('Cluster Size (# of cells)')
    ax3.set_ylabel('Number of Clusters')
    ax3.set_title('Cluster Size Distribution')
    ax3.grid(True, alpha=0.3)
    
    # Add statistics text
    stats_text = f'Mean: {cluster_sizes.mean():.1f}\nMedian: {np.median(cluster_sizes):.1f}\nStd: {cluster_sizes.std():.1f}'
    ax3.text(0.7, 0.8, stats_text, transform=ax3.transAxes, 
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    # Plot 4: Grid distance vs cluster quality
    ax4 = axes[1, 1]
    
    # Calculate cluster compactness (lower is better)
    cluster_compactness = cluster_stats['lat_span'] + cluster_stats['lon_span']
    
    scatter4 = ax4.scatter(
        cluster_stats['avg_grid_dist_km'],
        cluster_compactness,
        s=cluster_stats['n_cells'] * 20,
        c=cluster_stats['avg_re_cf'],
        cmap='RdYlBu_r',
        alpha=0.7,
        edgecolors='black',
        linewidth=0.5
    )
    
    ax4.set_xlabel('Average Grid Distance (km)')
    ax4.set_ylabel('Geographic Span (degrees)')
    ax4.set_title('Grid Connectivity vs Geographic Compactness\n(Size = # cells, Color = Average RE CF)')
    ax4.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar4 = plt.colorbar(scatter4, ax=ax4)
    cbar4.set_label(cf_label)
    
    plt.tight_layout()
    
    # Save the plot with technology suffix
    tech_suffix = f"_{technology}" if technology else ""
    plot_file = f'{output_dir}/clustering_results_{country_code}{tech_suffix}.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Saved plot: {plot_file}")
    # plt.show()  # Don't display, just save
    
    # 2. Export data for ESOM integration
    print("\nExporting data for ESOM integration...")
    
    # Cell to cluster mapping
    cell_mapping = pd.DataFrame({
        'grid_cell': profiles['cells'],
        'cluster_id': clusters,
        'lat': profiles['coords'][:, 0],
        'lon': profiles['coords'][:, 1],
        'grid_distance_km': clustering_info['distances_km'],
        'nearest_bus_idx': clustering_info['nearest_bus_idx'],
        'bus_id': buses_df.iloc[clustering_info['nearest_bus_idx']]['bus_id'].values
    })
    
    mapping_file = f'{output_dir}/cell_to_cluster_mapping{tech_suffix}.csv'
    cell_mapping.to_csv(mapping_file, index=False)
    print(f"Saved mapping: {mapping_file}")
    
    # Cluster summary statistics
    stats_file = f'{output_dir}/cluster_summary{tech_suffix}.csv'
    cluster_stats.to_csv(stats_file, index=False)
    print(f"Saved statistics: {stats_file}")
    
    # Skip simple averaged cluster profiles (replaced by weighted profiles in main script)
    print("Skipping simple averaged cluster profiles (using weighted profiles instead)...")
    cluster_profiles = {}  # Return empty dict for compatibility
    
    # 3. Create summary report
    print("\nGenerating summary report...")
    
    report = f"""
# Renewable Energy Clustering Results - {country_code}

## Summary Statistics
- **Total renewable zones processed**: {len(profiles['cells'])}
- **Number of clusters created**: {len(np.unique(clusters))}
- **Average cluster size**: {cluster_stats['n_cells'].mean():.1f} zones
- **Grid connectivity**: {cluster_stats['avg_grid_dist_km'].mean():.1f} +/- {cluster_stats['avg_grid_dist_km'].std():.1f} km

## Resource Characteristics

- **Solar capacity factor**: {cluster_stats['avg_re_cf'].mean():.3f} +/- {cluster_stats['avg_re_cf'].std():.3f}

## Clustering Algorithm
- **Method**: Hierarchical clustering with Ward linkage
- **Features**: Wind profiles (35%), Solar profiles (35%), Grid distance (20%), Spatial coordinates (10%)
- **Dimensionality reduction**: PCA (50 components each for wind/solar)

## Output Files
1. `clustering_results_{country_code}.png` - Comprehensive visualization
2. `cell_to_cluster_mapping_{country_code}.csv` - Zone-to-cluster assignments
3. `cluster_summary_{country_code}.csv` - Cluster statistics
4. `cluster_profiles_{country_code}.npz` - Aggregated hourly profiles for ESOM

## Quality Metrics
- **Cluster size range**: {cluster_stats['n_cells'].min()} - {cluster_stats['n_cells'].max()} zones
- **Best connected cluster**: {cluster_stats['min_grid_dist_km'].min():.1f} km to grid
- **Most remote cluster**: {cluster_stats['max_grid_dist_km'].max():.1f} km to grid

Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    report_file = f'{output_dir}/clustering_report_{country_code}.md'
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Saved report: {report_file}")
    
    print(f"\n+ All outputs saved to: {output_dir}/")
    print("Files ready for ESOM integration!")
    
    return cell_mapping, cluster_profiles

# Apply Step 5 - Create visualizations and export results
# cell_mapping, cluster_profiles = visualize_and_export(
#     clusters, profiles, cluster_stats, transmission_buses, 'FRA'
# )
# print(f"✅ Step 5 complete: Visualization and export finished!")