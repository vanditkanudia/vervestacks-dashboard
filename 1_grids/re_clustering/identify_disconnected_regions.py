import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
import sys
from pathlib import Path

# sys.path.append(str(Path(__file__).parent.parent.parent / 'syn_grids_1' ))

# from create_gem_units_clusters import GEMUnitsClusterer
# from create_regions_simple import PopulationDemandRegionMapper

def identify_disconnected_regions_core(
    data, 
    iso3_code,
    lat_col,
    lon_col, 
    id_col,
    eps=1.5,
    min_samples=5,
    plot=True,
    plot_title_suffix="zones"
):
    """
    Core function to automatically identify disconnected regions (like Alaska/Hawaii) using DBSCAN clustering.
    This is a flexible implementation that works with different data types by accepting column names as parameters.
    
    Args:
        data: DataFrame already filtered to the specific country
        iso3_code: ISO3 country code (for display purposes)
        lat_col: Name of the latitude column
        lon_col: Name of the longitude column
        id_col: Name of the identifier column (e.g., grid_cell, gem_unit_id, bus_id)
        eps: DBSCAN eps parameter - maximum distance between points in same cluster (in degrees)
        min_samples: DBSCAN min_samples parameter - minimum points to form a cluster
        plot: Whether to create visualization plots
        plot_title_suffix: Suffix for plot title (e.g., "REZoning zones", "Generation Units")
    
    Returns:
        Dictionary with 'main_bounds' and 'main_continental_ids' keys, or None if no data
    """
    if data.empty:
        print(f"No data found for {iso3_code}")
        return None
    
    # Make a copy to avoid modifying original data
    country_data = data.copy()
    
    print(f"\n=== Analyzing {iso3_code} ===")
    
    # Get coordinates
    coords = country_data[[lat_col, lon_col]].values
    
    # Use DBSCAN to find geographic clusters
    # eps = maximum distance between points in same cluster (in degrees)
    # For continental regions, 1.5-2 degrees is reasonable; islands will be separate
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    country_data['region_cluster'] = clustering.labels_
    
    # Analyze each cluster
    clusters = country_data.groupby('region_cluster').agg({
        lat_col: ['min', 'max', 'mean'],
        lon_col: ['min', 'max', 'mean'],
        id_col: 'count'
    })
    
    clusters.columns = ['lat_min', 'lat_max', 'lat_mean', 'lon_min', 'lon_max', 'lon_mean', 'n_items']
    clusters = clusters.sort_values('n_items', ascending=False)
    
    print(f"\nFound {len(clusters)} disconnected regions:")
    print(clusters)
    
    # Identify main continental region (largest cluster)
    if -1 not in clusters.index:
        main_cluster = clusters.index[0]
    else:
        # Exclude noise points (-1) when finding main cluster
        main_cluster = clusters[clusters.index != -1].index[0]
    
    main_bounds = {
        'lat_min': clusters.loc[main_cluster, 'lat_min'],
        'lat_max': clusters.loc[main_cluster, 'lat_max'],
        'lon_min': clusters.loc[main_cluster, 'lon_min'],
        'lon_max': clusters.loc[main_cluster, 'lon_max']
    }
    
    print(f"\nMain continental region (cluster {main_cluster}):")
    print(f"  Latitude:  {main_bounds['lat_min']:.2f} to {main_bounds['lat_max']:.2f}")
    print(f"  Longitude: {main_bounds['lon_min']:.2f} to {main_bounds['lon_max']:.2f}")
    print(f"  Items: {clusters.loc[main_cluster, 'n_items']:.0f}")
    
    # Identify disconnected regions
    disconnected = []
    for idx in clusters.index:
        if idx != main_cluster and idx != -1:  # Exclude main cluster and noise
            region_info = {
                'cluster_id': idx,
                'n_items': clusters.loc[idx, 'n_items'],
                'lat_center': clusters.loc[idx, 'lat_mean'],
                'lon_center': clusters.loc[idx, 'lon_mean'],
                'lat_range': (clusters.loc[idx, 'lat_min'], clusters.loc[idx, 'lat_max']),
                'lon_range': (clusters.loc[idx, 'lon_min'], clusters.loc[idx, 'lon_max'])
            }
            disconnected.append(region_info)

    
    if disconnected:
        print(f"\nDisconnected regions to potentially exclude:")
        for region in disconnected:
            print(f"  Cluster {region['cluster_id']}: {region['n_items']} items")
            print(f"    Center: ({region['lat_center']:.1f}, {region['lon_center']:.1f})")
    
    # Plot if requested
    if plot:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot each cluster with different colors
        for cluster_id in country_data['region_cluster'].unique():
            cluster_data = country_data[country_data['region_cluster'] == cluster_id]
            if cluster_id == -1:
                ax.scatter(cluster_data[lon_col], cluster_data[lat_col], 
                          c='gray', s=10, alpha=0.5, label='Noise')
            elif cluster_id == main_cluster:
                ax.scatter(cluster_data[lon_col], cluster_data[lat_col], 
                          c='blue', s=20, alpha=0.7, label=f'Main continent ({len(cluster_data)} items)')
            else:
                ax.scatter(cluster_data[lon_col], cluster_data[lat_col], 
                          s=20, alpha=0.7, label=f'Cluster {cluster_id} ({len(cluster_data)} items)')
        
        # Draw bounding box for main region
        rect = plt.Rectangle((main_bounds['lon_min'], main_bounds['lat_min']),
                            main_bounds['lon_max'] - main_bounds['lon_min'],
                            main_bounds['lat_max'] - main_bounds['lat_min'],
                            fill=False, edgecolor='blue', linewidth=2, linestyle='--',
                            label='Suggested bounds')
        ax.add_patch(rect)
        
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title(f'{iso3_code} - Geographic Clusters ({plot_title_suffix})')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
    
    # Get IDs in main continental cluster
    main_continental_ids = country_data[
        country_data['region_cluster'] == main_cluster
    ][id_col].tolist()
    
    return {
        'main_bounds': main_bounds,
        'main_continental_ids': main_continental_ids
    }


def identify_disconnected_regions(country_data, iso3_code, plot=True):
    """
    Identify disconnected regions for renewable zones data (REZoning).
    Wrapper function that maintains backward compatibility with existing code.
    
    Args:
        country_data: DataFrame already filtered to the specific country
        iso3_code: ISO3 country code (for display purposes)
        plot: Whether to create visualization plots
    
    Returns:
        Dictionary with 'main_bounds' and 'main_continental_grid_cells' keys
    """
    result = identify_disconnected_regions_core(
        data=country_data,
        iso3_code=iso3_code,
        lat_col='centroid_lat',
        lon_col='centroid_lon',
        id_col='grid_cell',
        eps=1.5,
        min_samples=5,
        plot=plot,
        plot_title_suffix='REZoning zones'
    )
    
    # Rename key for backward compatibility
    if result:
        result['main_continental_grid_cells'] = result.pop('main_continental_ids')
    
    return result


def identify_disconnected_regions_generation(country_data, iso3_code, plot=True):
    """
    Identify disconnected regions for generation units (GEM data).
    Uses lat/lng columns and gem_unit_id identifier.
    
    Power plants tend to be sparser than renewable zones, so uses:
    - Larger eps (2.0 degrees) to connect nearby plants
    - Smaller min_samples (3) to avoid marking sparse regions as noise
    
    Args:
        country_data: DataFrame with generation units, already filtered to country
        iso3_code: ISO3 country code
        plot: Whether to create visualization
    
    Returns:
        Dictionary with 'main_bounds' and 'main_continental_units' keys
    """
    result = identify_disconnected_regions_core(
        data=country_data,
        iso3_code=iso3_code,
        lat_col='lat',
        lon_col='lng',
        id_col='gem_unit_id',
        eps=3.0,          # Larger: power plants are more sparse than RE zones
        min_samples=3,    # Lower: fewer plants than zones typically
        plot=plot,
        plot_title_suffix='Generation Units'
    )
    
    # Rename key for clarity
    if result:
        result['main_continental_units'] = result.pop('main_continental_ids')
    
    return result


def identify_disconnected_regions_demand(country_data, iso3_code, plot=True):
    """
    Identify disconnected regions for demand/load data.
    
    PLACEHOLDER: To be implemented when demand data structure is finalized.
    
    Args:
        country_data: DataFrame with demand nodes, already filtered to country
        iso3_code: ISO3 country code
        plot: Whether to create visualization
    
    Returns:
        Dictionary with 'main_bounds' and 'main_continental_nodes' keys
    """
    
    result = identify_disconnected_regions_core(
        data=country_data,
        iso3_code=iso3_code,
        lat_col='lat',      # UPDATE with actual column name
        lon_col='lng',      # UPDATE with actual column name
        id_col='name',        # UPDATE with actual column name
        eps=3.0,                # May need adjustment based on data density
        min_samples=3,          # May need adjustment based on data density
        plot=plot,
        plot_title_suffix='Demand Nodes'
    )
    
    if result:
        result['main_continental_nodes'] = result.pop('main_continental_ids')
    
    return result

# Run the analysis
def analyze_all_countries(rezoning_df):
    """Analyze multiple countries and generate filtering code"""
    
    countries_to_analyze = ['USA', 'FRA', 'RUS', 'CAN', 'AUS', 'CHN', 'BRA']
    grid_cells_dict = {}
    
    for iso3 in countries_to_analyze:
        # Filter to country first
        country_data = rezoning_df[rezoning_df['ISO'] == iso3].copy()
        result = identify_disconnected_regions(country_data, iso3, plot=False)
        if result:
            grid_cells_dict[iso3] = result['main_continental_grid_cells']
    
    # Generate Python code for the grid cells
    print("\n=== Copy this code for your filtering function ===\n")
    print("CONTINENTAL_GRID_CELLS = {")
    for iso3, grid_cells in grid_cells_dict.items():
        print(f"    '{iso3}': {grid_cells},")
    print("}")
    
    return grid_cells_dict


# if __name__ == "__main__":
#     # Usage:

#     # gem_clusterer = GEMUnitsClusterer('USA')
#     population_demand_region_mapper = PopulationDemandRegionMapper('IND')
#     demand_data = population_demand_region_mapper.load_city_data()
#     demand_data = population_demand_region_mapper.create_demand_points()
#     result = identify_disconnected_regions_demand(demand_data, 'IND', plot=True)
    
#     print(demand_data.columns)
#     # gem_data = gem_clusterer.load_gem_data()
#     # result = identify_disconnected_regions_generation(gem_data, 'USA', plot=True)
#     # print(result)
#     # Load your REZoning data
#     # rezoning_onshore = pd.read_parquet('../../data/REZoning/consolidated_onshore_zones_with_geometry.parquet')

#     # # Analyze specific country
#     # idn_data = rezoning_onshore[rezoning_onshore['ISO'] == 'JPN'].copy()
#     # usa_result = identify_disconnected_regions(idn_data, 'JPN', plot=True)

#     # Or analyze all major countries
#     # all_grid_cells = analyze_all_countries(rezoning_onshore)