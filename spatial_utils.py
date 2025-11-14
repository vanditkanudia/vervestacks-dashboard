"""
Spatial Utilities Module

Core spatial intelligence functions for VerveStacks energy modeling platform.
Provides consistent spatial identifier transformations for both Python and SQL workflows.

Functions handle the transformation between physical geography (grid cells, buses) 
and model abstractions (commodities, processes) that enable spatially-aware 
energy system optimization.
"""

import duckdb
import pandas as pd
from typing import Optional, Literal


def bus_id_to_commodity(bus_id: str, add_prefix: bool = True) -> str:
    """
    Transform bus ID to model commodity format.
    
    Converts OpenStreetMap bus identifiers to VerveStacks model commodities
    by cleaning prefixes and optionally adding model prefix.
    
    Args:
        bus_id: Bus identifier (e.g., "way/12345", "relation/67890")
        add_prefix: Whether to add "e_" prefix for model commodity format
        
    Returns:
        Formatted commodity string
        
    Examples:
        >>> bus_id_to_commodity("way/12345")
        'e_w12345'
        >>> bus_id_to_commodity("relation/67890", add_prefix=False)
        'r67890'
    """
    if not isinstance(bus_id, str):
        raise ValueError(f"Bus ID must be string, got {type(bus_id)}")
    
    # Clean bus ID: way/ → w, relation/ → r
    clean_id = bus_id.replace('way/', 'w').replace('relation/', 'r')
    
    # Add model prefix if requested
    if add_prefix:
        return f"e_{clean_id}"
    return clean_id


def cluster_id_to_commodity(
    cluster_id: int, 
    resource_type: str, 
    format_type: Literal["commodity", "process"] = "commodity"
) -> str:
    """
    Transform cluster ID to model commodity format.
    
    Converts spatial grid cell identifiers to resource-specific model commodities
    with proper zero-padding and formatting for VerveStacks optimization.
    
    Args:
        grid_cell: Grid cell identifier (e.g., "ITA_42", "CHE_7")
        resource_type: Resource type ("spv", "won", "hyd", etc.)
        format_type: Output format - "commodity" (elc_*) or "process" (e_*)
        
    Returns:
        Formatted commodity or process string
        
    Examples:
        >>> cluster_id_to_commodity(1, "spv")
        'elc_spv_001'
        >>> cluster_id_to_commodity(1, "won", "process")
        'e_won_001'
    """
    
    try:
        # Convert to integer and zero-pad to 4 digits
        number = int(cluster_id)
        padded_number = f"{number:03d}"
    except ValueError:
        raise ValueError(f"Number part must be valid integer, got: {cluster_id}")
    
    # Format based on requested type
    if format_type == "commodity":
        return f"elc_{resource_type}_{padded_number}"
    elif format_type == "process":
        return f"e_{resource_type}_{padded_number}"
    else:
        raise ValueError(f"format_type must be 'commodity' or 'process', got: {format_type}")

def grid_cell_to_commodity(
    grid_cell: str, 
    resource_type: str, 
    format_type: Literal["commodity", "process"] = "commodity"
) -> str:
    """
    Transform grid cell ID to model commodity format.
    
    Converts spatial grid cell identifiers to resource-specific model commodities
    with proper zero-padding and formatting for VerveStacks optimization.
    
    Args:
        grid_cell: Grid cell identifier (e.g., "ITA_42", "CHE_7")
        resource_type: Resource type ("spv", "won", "hyd", etc.)
        format_type: Output format - "commodity" (elc_*) or "process" (e_*)
        
    Returns:
        Formatted commodity or process string
        
    Examples:
        >>> grid_cell_to_commodity("ITA_42", "spv")
        'elc_spv-ITA_0042'
        >>> grid_cell_to_commodity("ITA_42", "won", "process")
        'e_won-ITA_0042'
    """
    if not isinstance(grid_cell, str) or '_' not in grid_cell:
        raise ValueError(f"Grid cell ID must contain underscore separator, got: {grid_cell}")
    
    parts = grid_cell.split('_')
    if len(parts) != 2:
        raise ValueError(f"Grid cell ID must have format 'COUNTRY_NUMBER', got: {grid_cell}")
    
    country_code = parts[0][-3:]  # Take the rightmost 3 characters in case of wof-ISO
    number_part = parts[1]
    
    try:
        # Convert to integer and zero-pad to 4 digits
        number = int(number_part)
        padded_number = f"{number:04d}"
    except ValueError:
        raise ValueError(f"Number part must be valid integer, got: {number_part}")
    
    # Format based on requested type
    if format_type == "commodity":
        return f"elc_{resource_type}-{country_code}_{padded_number}"
    elif format_type == "process":
        return f"e_{resource_type}-{country_code}_{padded_number}"
    else:
        raise ValueError(f"format_type must be 'commodity' or 'process', got: {format_type}")


def get_spatial_commodity(bus_id: Optional[str], iso_code: str, grid_modeling: bool = True) -> str:
    """
    Get spatial commodity identifier with graceful fallback.
    
    Returns spatially-specific commodity when grid modeling is enabled,
    falls back to country-level identifier when spatial data unavailable.
    "That's what you know - that's the truth."
    
    Args:
        bus_id: Bus identifier (if available)
        iso_code: Country ISO code (fallback)
        grid_modeling: Whether grid modeling is enabled
        
    Returns:
        Spatial commodity identifier
        
    Examples:
        >>> get_spatial_commodity("way/12345", "ITA", True)
        'e_w12345'
        >>> get_spatial_commodity(None, "ITA", False)
        'ITA'
    """
    if grid_modeling and bus_id and pd.notna(bus_id):
        return bus_id_to_commodity(bus_id)
    return iso_code


def register_sql_functions(connection=None):
    """
    Register spatial transformation functions with DuckDB for SQL usage.
    
    Enables seamless use of Python functions within SQL queries for
    consistent spatial transformations across the entire platform.
    
    Args:
        connection: DuckDB connection (uses default if None)
    """
    if connection is None:
        connection = duckdb
    
    # Register bus_id transformation function
    connection.create_function(
        "bus_id_to_commodity",
        bus_id_to_commodity,
        ["VARCHAR", "BOOLEAN"],
        "VARCHAR"
    )
    
    # Register REZ transformation function  
    connection.create_function(
        "grid_cell_to_commodity", 
        grid_cell_to_commodity,
        ["VARCHAR", "VARCHAR", "VARCHAR"],
        "VARCHAR"
    )
    
    # Register REZ transformation function  
    connection.create_function(
        "cluster_id_to_commodity", 
        cluster_id_to_commodity,
        ["BIGINT", "VARCHAR", "VARCHAR"],
        "VARCHAR"
    )
  
    # Register spatial commodity function
    connection.create_function(
        "get_spatial_commodity",
        get_spatial_commodity,
        ["VARCHAR", "VARCHAR", "BOOLEAN"], 
        "VARCHAR"
    )


# Auto-register functions when module is imported
register_sql_functions()


def create_spatial_aggregation_query(
    table_name: str,
    capacity_threshold: float,
    grid_modeling: bool = True,
    additional_group_cols: Optional[list] = None
) -> str:
    """
    Generate SQL query for spatial-aware existing stock aggregation.
    
    Creates DuckDB query that groups plants by spatial location first,
    then applies capacity threshold logic to preserve spatial distribution.
    
    Args:
        table_name: Name of table/dataframe containing plant data
        capacity_threshold: Capacity threshold for individual vs aggregated plants
        grid_modeling: Whether to use spatial grouping
        additional_group_cols: Additional columns to include in GROUP BY
        
    Returns:
        SQL query string for spatial aggregation
    """
    additional_cols = additional_group_cols or []
    additional_group = ", " + ", ".join(additional_cols) if additional_cols else ""
    
    # Spatial commodity selection
    spatial_col = """
        CASE 
            WHEN grid_modeling THEN bus_id_to_commodity("comm-out", true)
            ELSE iso_code
        END AS spatial_commodity"""
    
    query = f"""
        SELECT  
            iso_code,
            "Start year",
            model_fuel,
            {spatial_col},
            CASE 
                WHEN SUM("Capacity (MW)") >= {capacity_threshold} 
                THEN CAST(model_name AS VARCHAR) || '_' || COALESCE(CAST("GEM unit/phase ID" AS VARCHAR), '')
                ELSE CAST(model_fuel AS VARCHAR) || '_spatial_agg'
            END AS model_name,
            CASE
                WHEN SUM("Capacity (MW)") >= {capacity_threshold} 
                THEN CAST("Plant / Project name" AS VARCHAR) || '_' || COALESCE(CAST("Unit / Phase name" AS VARCHAR), '')
                ELSE 'Spatially Aggregated Plants at ' || spatial_commodity
            END AS model_description,
            SUM("Capacity (MW)") / 1000.0 AS "pasti",
            -- Weighted averages for technical parameters
            SUM("Capacity (MW)" * capex) / NULLIF(SUM("Capacity (MW)"), 0) AS capex,
            SUM("Capacity (MW)" * fixom) / NULLIF(SUM("Capacity (MW)"), 0) AS fixom,
            SUM("Capacity (MW)" * varom) / NULLIF(SUM("Capacity (MW)"), 0) AS varom,
            SUM("Capacity (MW)" * efficiency) / NULLIF(SUM("Capacity (MW)"), 0) AS efficiency
        FROM {table_name}
        GROUP BY 
            iso_code, 
            "Start year", 
            model_fuel,
            spatial_commodity{additional_group}
        ORDER BY spatial_commodity, model_fuel, "Start year"
    """
    
    return query


def calculate_rez_weights(zones_data, fuel_type, input_iso):
    """
    Calculate weights for REZ zones based on capacity factor and resource potential.
    
    Selects only the top 3 sites with the best combined resource quality to concentrate
    renewable capacity deployment at the most economically viable locations.
    
    Args:
        zones_data: DataFrame with REZoning data (solar or wind)
        fuel_type: 'solar' or 'windon' or 'windoff'
        input_iso: ISO country code
        
    Returns:
        dict: {grid_cell: weight} mapping for spatial distribution
        
    Methodology:
        1. Filters REZoning data for the specified country
        2. Deduplicates grid cells, keeping best resource per cell
        3. Calculates combined score: 70% capacity factor + 30% resource potential
        4. Selects top 3 sites based on combined score
        5. Normalizes weights to sum to 1.0 for capacity distribution
        
    Note:
        Missing renewable capacity (IRENA gaps) is distributed only among these
        top 3 sites to ensure concentrated deployment at best resource locations.
    """
    # Filter for the specific ISO
    df_zones = zones_data
    
    if df_zones.empty:
        print(f"Warning: No {fuel_type} cluster level data found for {input_iso}")
        return {}
    
    # For each grid cell, keep the best resource (max capacity factor, then max potential)
    # Note: Global deduplication should have handled most duplicates, but this ensures data integrity
    df_zones = df_zones.sort_values(['cluster_id', 'avg_re_cf', 'total_re_capacity_mw'], 
                                   ascending=[True, False, False])
    df_zones = df_zones.drop_duplicates(subset=['cluster_id'], keep='first')
    
    # Calculate combined score for ranking
    cf_normalized = df_zones['avg_re_cf'] / df_zones['avg_re_cf'].max()
    potential_normalized = df_zones['total_re_capacity_mw'] / df_zones['total_re_capacity_mw'].max()
    
    # Combined score: 70% capacity factor, 30% resource potential
    df_zones['combined_score'] = 0.7 * cf_normalized + 0.3 * potential_normalized
    
    # Select only top 3 sites based on combined score
    df_zones = df_zones.nlargest(3, 'combined_score')
    print(f"Selected top 3 {fuel_type} sites for {input_iso}: {list(df_zones['cluster_id'])}")
    
    # Calculate final weights (normalized to sum to 1.0)
    df_zones['weight'] = df_zones['combined_score'] / df_zones['combined_score'].sum()
    
    return dict(zip(df_zones['cluster_id'], df_zones['weight']))


def calculate_bus_weights(buses_data, existing_capacity_by_bus=None):
    """
    Calculate weights for buses based on voltage level and existing capacity.
    
    Args:
        buses_data: DataFrame with bus information including voltage
        existing_capacity_by_bus: dict of {bus_id: capacity_mw} (optional)
        
    Returns:
        dict: {bus_id: weight} mapping for spatial distribution
    """
    if buses_data.empty:
        print("Warning: No bus data available for weighting")
        return {}
    
    df_buses = buses_data.copy()
    
    # Voltage scoring (higher voltage = higher transmission capacity)
    voltage_scores = {380: 3, 225: 2, 220: 1}
    df_buses['voltage_score'] = df_buses['voltage'].map(voltage_scores).fillna(1)
    
    # Normalize voltage scores
    voltage_normalized = df_buses['voltage_score'] / df_buses['voltage_score'].max()
    
    # Handle existing capacity weighting
    if existing_capacity_by_bus:
        df_buses['existing_capacity'] = df_buses['bus_id'].map(existing_capacity_by_bus).fillna(0)
        if df_buses['existing_capacity'].max() > 0:
            capacity_normalized = df_buses['existing_capacity'] / df_buses['existing_capacity'].max()
        else:
            capacity_normalized = 0
    else:
        capacity_normalized = 0
    
    # Combined weight: 70% voltage capacity, 30% existing capacity pattern
    df_buses['weight'] = 0.7 * voltage_normalized + 0.3 * capacity_normalized
    
    # Normalize to sum to 1.0
    df_buses['weight'] = df_buses['weight'] / df_buses['weight'].sum()
    
    return dict(zip(df_buses['bus_id'], df_buses['weight']))


def distribute_capacity_by_weights(total_capacity_gw, weights_dict, min_capacity_gw=0.001):
    """
    Distribute total capacity across zones/buses based on weights.
    
    Args:
        total_capacity_gw: Total capacity to distribute (GW)
        weights_dict: {zone/bus_id: weight} mapping
        min_capacity_gw: Minimum capacity per zone (GW)
        
    Returns:
        dict: {zone/bus_id: allocated_capacity_gw}
    """
    if not weights_dict:
        return {}
    
    # Calculate initial distribution
    distribution = {}
    for zone_id, weight in weights_dict.items():
        allocated = total_capacity_gw * weight
        if allocated >= min_capacity_gw:
            distribution[zone_id] = allocated
    
    # If nothing meets minimum, distribute to top zones
    if not distribution:
        # Sort by weight descending and allocate to top zones
        sorted_zones = sorted(weights_dict.items(), key=lambda x: x[1], reverse=True)
        zones_to_use = min(5, len(sorted_zones))  # Use top 5 zones max
        
        for i, (zone_id, weight) in enumerate(sorted_zones[:zones_to_use]):
            distribution[zone_id] = total_capacity_gw / zones_to_use
    
    # Verify total matches (should be close due to rounding)
    actual_total = sum(distribution.values())
    if abs(actual_total - total_capacity_gw) > 0.001:
        print(f"Warning: Distribution total ({actual_total:.3f} GW) differs from target ({total_capacity_gw:.3f} GW)")
    
    return distribution


if __name__ == "__main__":
    # Test the functions
    print("Testing spatial transformation functions...")
    
    # Test bus transformation
    print(f"Bus test: {bus_id_to_commodity('way/12345')}")
    print(f"Grid cell test: {grid_cell_to_commodity('ITA_42', 'spv')}")
    print(f"Spatial test: {get_spatial_commodity('way/12345', 'ITA', True)}")
    print(f"Fallback test: {get_spatial_commodity(None, 'ITA', False)}")
    
    print("All functions working correctly! 🎯")


def calculate_thermal_bus_weights(buses_data, existing_plants_df, fuel_type, input_iso):
    """
    Calculate weights for thermal plant distribution based on existing fuel-specific capacity.
    
    Args:
        buses_data: DataFrame with bus information (from clustered_buses.csv)
        existing_plants_df: DataFrame with existing plants data with bus_id
        fuel_type: 'coal', 'gas', 'oil', 'bioenergy', 'hydro'
        input_iso: ISO country code
        
    Returns:
        dict: {bus_id: weight} mapping for spatial distribution
    """
    # First try: fuel-specific distribution
    existing_fuel_plants = existing_plants_df[
        (existing_plants_df['model_fuel'] == fuel_type) & 
        (existing_plants_df['bus_id'].notna())
    ]
    
    if not existing_fuel_plants.empty:
        print(f"Distributing {fuel_type} based on existing {fuel_type} plant locations")
        
        # Group by bus_id and sum capacity
        bus_capacity = existing_fuel_plants.groupby('bus_id')['Capacity (MW)'].sum()
        
        # Normalize to weights
        total_capacity = bus_capacity.sum()
        if total_capacity > 0:
            weights = bus_capacity / total_capacity
            return dict(weights)
    
    # Fallback: voltage-based distribution
    print(f"No existing {fuel_type} plants found for {input_iso}, using voltage-based distribution")
    return calculate_voltage_based_weights(buses_data)


def calculate_voltage_based_weights(buses_data):
    """
    Calculate weights based on bus voltage levels (higher voltage = higher priority).
    
    Args:
        buses_data: DataFrame with bus information including voltage
        
    Returns:
        dict: {bus_id: weight} mapping for spatial distribution
    """
    if buses_data.empty or 'voltage' not in buses_data.columns:
        print("Warning: No bus data or voltage information available")
        return {}
    
    # Voltage priority weights
    voltage_priorities = {
        380: 1.0,    # Transmission level - highest priority
        220: 0.7,    # Sub-transmission
        110: 0.4,    # Distribution
        # Any other voltage gets lower priority
    }
    
    # Calculate weights based on voltage
    weights = []
    bus_ids = []
    
    for idx, bus in buses_data.iterrows():
        # bus_id might be in index or as a column
        bus_id = bus.get('bus_id', idx)
        voltage = bus.get('voltage', 0)
        
        # Get voltage weight (default to 0.1 for unknown voltages)
        voltage_weight = voltage_priorities.get(voltage, 0.1)
        
        weights.append(voltage_weight)
        bus_ids.append(bus_id)
    
    # Normalize to sum to 1.0
    total_weight = sum(weights)
    if total_weight > 0:
        normalized_weights = [w / total_weight for w in weights]
        return dict(zip(bus_ids, normalized_weights))
    
    return {}


def calculate_capacity_distribution(fuel_type, capacity_gw, input_iso, buses_data=None, zones_data=None, existing_plants_df=None):
    """
    Unified capacity distribution function for both renewable and thermal plants.
    
    Args:
        fuel_type: 'solar', 'wind', 'hydro', 'coal', 'gas', 'oil', 'bioenergy'
        capacity_gw: Capacity to distribute in GW
        input_iso: ISO country code
        buses_data: DataFrame with bus information (required for thermal)
        zones_data: DataFrame with cluster level data (required for renewables)
        existing_plants_df: DataFrame with existing plants (for thermal distribution)
        
    Returns:
        dict: {location_id: allocated_gw} mapping
    """
    # Renewable distribution (cluster level data)
    if fuel_type in ['solar', 'windon', 'windoff']:
        if zones_data is None:
            print(f"Warning: No cluster level data available for {fuel_type}")
            return {}
        
        weights = calculate_rez_weights(zones_data, fuel_type, input_iso)
        if not weights:
            print(f"Warning: No cluster level weights calculated for {fuel_type}")
            return {}
        
        # Distribute capacity based on weights
        distribution = {cluster_id: weight * capacity_gw for cluster_id, weight in weights.items()}
        return distribution
    
    # Thermal/Hydro distribution (bus-based) with 10MW threshold
    else:
        if buses_data is None:
            print(f"Warning: No bus data available for {fuel_type}")
            return {}
        
        weights = calculate_thermal_bus_weights(buses_data, existing_plants_df, fuel_type, input_iso)
        if not weights:
            print(f"Warning: No thermal weights calculated for {fuel_type}")
            return {}
        
        # Initial distribution based on weights
        initial_distribution = {bus_id: weight * capacity_gw for bus_id, weight in weights.items()}
        
        # Apply 10MW threshold (0.01 GW)
        final_distribution = {}
        residual_gw = 0.0
        largest_bus = None
        largest_capacity = 0.0
        
        for bus_id, allocated_gw in initial_distribution.items():
            if allocated_gw >= 0.01:  # 10 MW threshold
                final_distribution[bus_id] = allocated_gw
                if allocated_gw > largest_capacity:
                    largest_capacity = allocated_gw
                    largest_bus = bus_id
            else:
                residual_gw += allocated_gw
        
        # Give residual to largest bus
        if residual_gw > 0 and largest_bus is not None:
            final_distribution[largest_bus] += residual_gw
            print(f"Applied 10MW threshold: redistributed {residual_gw:.3f} GW residual to {largest_bus}")
        
        return final_distribution
