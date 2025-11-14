"""
Grid Modeling Module

Processes transmission grid data for VEDA model creation.
Called only when grid_modeling=True in iso_processor.
"""

import pandas as pd
import duckdb
from pathlib import Path
from spatial_utils import bus_id_to_commodity, grid_cell_to_commodity
from shared_data_loader import get_shared_loader


def process_grid_data(iso_processor):
    """
    Process transmission grid data for the given ISO.
    
    Args:
        iso_processor: ISOProcessor instance with configuration
        
    Returns:
        dict: Dictionary containing the 4 grid modeling dataframes:
            - TradeLinks_DINS: Trade links structure
            - TradeLinks_Desc: Process descriptions  
            - pasti: Capacity data
            - fi_comm: Grid node commodity definitions
    """
    input_iso = iso_processor.input_iso
    
    # Read the lines data file
    lines_df = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/{iso_processor.input_iso}_clustered_lines.csv")
    buses_df = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/{iso_processor.input_iso}_clustered_buses.csv")

    if iso_processor.data_source.startswith('syn'):
    # Convert 'length' column from km to m in lines_df to ensure consistency with other grid styles
        lines_df['length'] = lines_df['length'] * 1000  # convert km to m
    
    # Transform bus IDs to commodity format using standardized function
    lines_df['comm1'] = lines_df['bus0'].apply(lambda x: bus_id_to_commodity(x, add_prefix=False))
    lines_df['comm2'] = lines_df['bus1'].apply(lambda x: bus_id_to_commodity(x, add_prefix=False))

    buses_df['comm'] = buses_df['bus_id'].apply(lambda x: bus_id_to_commodity(x, add_prefix=False))

    duckdb.register('lines_df', lines_df)
    duckdb.register('buses_df', buses_df)
    
    # Process transmission lines data
    result = duckdb.sql(f"""
        with lines as (
        SELECT comm1, comm2, type, bus0, bus1,
               round(max(length)/1000, 0) as length_km,
               sum(s_nom)/1000 as gw
        FROM lines_df
        GROUP BY comm1, comm2, type, bus0, bus1
        )
        select '{input_iso}' as reg1, '{input_iso}' as reg2, 
        'ELC' as comm, 'e_' || comm1 AS comm1, 'e_' || comm2 AS comm2,
        'g_' || comm1 || '-' || comm2 AS tech,
        'B' AS tradelink,
        'grid link -' || length_km || ' km- ' || type AS "description",
        bus0 as bus0,
        bus1 as bus1,
        gw as cap
        from lines

    """).to_df()

    duckdb.register('result', result)

    # Generate the 4 required dataframes
    grid_links_DINS = duckdb.sql("""
        select reg1, reg2, comm, comm1, comm2, tech, tradelink
        from result
        order by reg1, reg2, comm, comm1, comm2
    """).to_df()

    grid_links_Desc = duckdb.sql("""
        select tech as process, description
        from result
        order by tech
    """).to_df()

    grids_parameters = duckdb.sql("""
    with lines as (
            SELECT comm1, comm2, type, bus0, bus1,
                round(max(length)/1000, 0) as length_km,
                sum(s_nom)/1000 as gw
            FROM lines_df
            GROUP BY comm1, comm2, type, bus0, bus1
            )
        select 'g_' || comm1 || '-' || comm2 AS process, gw AS pasti,
            1.1 * length_km as ncap_cost,
            (1 - .00006 * length_km) as efficiency
            from lines
            order by process
        """).to_df()


    fi_comm_grids = duckdb.sql("""
        select 'NRG' AS "set",'e_' || comm as commodity, 'grid node -- ' || bus_id as "description"
        ,'ELC' as commoditytype, 'daynite' as "timeslicelevel",'lo' as limtype, 'TWh' as unit
        from buses_df
        order by comm
    """).to_df()

    # Update description in fi_comm_grids to be max 250 chars + ... if len > 253
    fi_comm_grids['description'] = fi_comm_grids['description'].apply(
        lambda x: x if len(x) <= 253 else x[:250] + '...'
    )
    
    # Load bus load share data and filter for load_share > 0
    if iso_processor.data_source.startswith('syn'):
        df_bus_load_share = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{input_iso}/{input_iso}_bus_load_share.csv")
    else:
        df_bus_load_share = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{input_iso}/{input_iso}_bus_load_share_voronoi.csv")
    df_bus_load_share = df_bus_load_share[df_bus_load_share['load_share'] > 0]
    df_bus_load_share['bus_id'] = df_bus_load_share['bus_id'].apply(lambda x: bus_id_to_commodity(x, add_prefix=False))

    shared_loader = get_shared_loader("data/")
    df_dem_techs = shared_loader.get_vs_mappings_sheet('dem_techs')

    duckdb.register('df_bus_load_share', df_bus_load_share)
    duckdb.register('df_dem_techs', df_dem_techs)

    df_demtech_topins = duckdb.sql("""
        select 
        T2.tech || '_'|| T1.bus_id as process,
        'e_' || T1.bus_id as commodity,
        'IN' as "io",
        from df_bus_load_share T1
        cross join df_dem_techs T2
        """).to_df()


    df_demtech_flo_mark = duckdb.sql("""
        select 
        T2.tech || '_'|| T1.bus_id as process,
        'elc_buildings,elc_transport,elc_industry,elc_roadtransport' as commodity,
        T1.load_share * .98 as "flo_mark",
        'lo' as lim_type,
        'elc_buildings,elc_transport,elc_industry,elc_roadtransport' as pset_co,
        from df_bus_load_share T1
        cross join df_dem_techs T2
        """).to_df()


    # Return the processed grid data
    return {
        'grid_links_DINS': grid_links_DINS,
        'grid_links_Desc': grid_links_Desc,
        'grids_parameters': grids_parameters,
        'fi_comm_grids': fi_comm_grids,
        'df_demtech_topins': df_demtech_topins,
        'df_demtech_flo_mark': df_demtech_flo_mark
    }

def compile_solar_wind_data_grid(iso_processor):

    # this function manages solar and wind generation at REZ cluster level - for both grid and non-grid models
    # it then aggregates the solar and wind generation to the bus level

    input_iso = iso_processor.input_iso
    data_source = iso_processor.data_source

    df_solar = pd.read_csv(f"1_grids/output_{data_source}/{input_iso}/cluster_summary_solar.csv")
    
    duckdb.register('df_solar', df_solar)

    df_solar_fi_t = duckdb.sql(f"""
    SELECT
        cluster_id AS "cluster_id", avg_grid_dist_km,
        cluster_id_to_commodity(cluster_id, 'spv', 'process') AS "process",
        cluster_id_to_commodity(cluster_id, 'spv', 'commodity') AS "comm-out",
        "total_re_capacity_mw"/1000 AS "cap_bnd",
        "avg_re_cf" AS "af~fx"
    FROM df_solar
    """).to_df()


    duckdb.register('df_solar_fi_t', df_solar_fi_t)

    df_solar_fi_p = duckdb.sql("""
    select 
    'ele' AS set,
    process,'solar resource in cluster ' || cluster_id AS description,
    'GW' AS capacity_unit,
    'TWh' AS activity_unit,
    'annual' AS timeslicelevel,
    'no' AS vintage
    from df_solar_fi_t T1
    """).to_df()

    # Investment cost: 1.1 M$/GW per km (typical for high-voltage AC transmission)
    # Efficiency: 0.006% losses per km (industry standard for AC transmission)

    if iso_processor.grid_modeling:
        # connect solar clusters to buses
        df_solar_to_bus = pd.read_csv(f"1_grids/output_{data_source}/{input_iso}/cell_to_cluster_mapping_solar.csv")

        df_solar_to_bus = df_solar_to_bus.drop_duplicates(subset=['cluster_id', 'bus_id'])

        df_solar_to_bus['bus_id'] = df_solar_to_bus['bus_id'].apply(lambda x: bus_id_to_commodity(x, add_prefix=False))

        duckdb.register('df_solar_to_bus', df_solar_to_bus)
        df_agg_sol_fi_t = duckdb.sql(f"""
        SELECT
            'distr_sol' || T1."comm-out" AS process,
            T1."comm-out" AS "comm-in",group_concat('e_' || bus_id) AS "comm-out",
            1 - 0.00006 * T1.avg_grid_dist_km AS efficiency,
            1.1 * T1.avg_grid_dist_km AS "ncap_cost~USD21_alt",
            T1.cluster_id,
        FROM df_solar_fi_t T1
            INNER JOIN df_solar_to_bus T2
            ON T1.cluster_id = T2.cluster_id
        group by T1."comm-out",T1.cluster_id,T1.avg_grid_dist_km
            """).to_df()

        duckdb.register('df_agg_sol_fi_t', df_agg_sol_fi_t)

        df_agg_sol_fi_p = duckdb.sql("""
        select 
        'pre' AS set,
        process,'connecting solar to buses in cluster ' || cluster_id AS description,
        'GW' AS capacity_unit,
        'TWh' AS activity_unit,
        'NRGI' AS primarycg,
        'daynite' AS timeslicelevel,
        'no' AS vintage
        from df_agg_sol_fi_t T1
        """).to_df()
    
        df_agg_sol_fi_t = df_agg_sol_fi_t.drop(columns=['cluster_id'])
    
    else:
        df_agg_sol_fi_t = pd.DataFrame()
        df_agg_sol_fi_p = pd.DataFrame()


    # now do the same for wind
    df_windon = pd.read_csv(f"1_grids/output_{data_source}/{input_iso}/cluster_summary_wind_onshore.csv")

    duckdb.register('df_windon', df_windon)

    # wind onshore
    df_won_fi_t = duckdb.sql(f"""
    SELECT
        cluster_id AS "cluster_id", avg_grid_dist_km,
        cluster_id_to_commodity(cluster_id, 'won', 'process') AS "process",
        cluster_id_to_commodity(cluster_id, 'won', 'commodity') AS "comm-out",
        "total_re_capacity_mw"/1000 AS "cap_bnd",
        "avg_re_cf" AS "af~fx"
    FROM df_windon
    """).to_df()

    duckdb.register('df_won_fi_t', df_won_fi_t)

    df_won_fi_p = duckdb.sql("""
    select 
    'ele' AS set,
    process,'wind resource in cluster ' || cluster_id AS description,
    'GW' AS capacity_unit,
    'TWh' AS activity_unit,
    'annual' AS timeslicelevel,
    'no' AS vintage
    from df_won_fi_t T1
    """).to_df()

    if iso_processor.grid_modeling:
        # connect wind clusters to buses
        df_windon_to_bus = pd.read_csv(f"1_grids/output_{data_source}/{input_iso}/cell_to_cluster_mapping_wind_onshore.csv")
        df_windon_to_bus = df_windon_to_bus.drop_duplicates(subset=['cluster_id', 'bus_id'])
        df_windon_to_bus['bus_id'] = df_windon_to_bus['bus_id'].apply(lambda x: bus_id_to_commodity(x, add_prefix=False))
        duckdb.register('df_windon_to_bus', df_windon_to_bus)

        df_agg_won_fi_t = duckdb.sql(f"""
        SELECT
            'distr_won' || T1."comm-out" AS process,
            T1."comm-out" AS "comm-in",group_concat('e_' || bus_id) AS "comm-out",
            1 - 0.00006 * T1.avg_grid_dist_km AS efficiency,
            1.1 * T1.avg_grid_dist_km AS "ncap_cost~USD21_alt",
            T1.cluster_id,
        FROM df_won_fi_t T1
            INNER JOIN df_windon_to_bus T2
            ON T1.cluster_id = T2.cluster_id
        group by T1."comm-out",T1.cluster_id,T1.avg_grid_dist_km
            """).to_df()

        duckdb.register('df_agg_won_fi_t', df_agg_won_fi_t)

        df_agg_won_fi_p = duckdb.sql("""
        select 
        'pre' AS set,
        process,'connecting wind onshore to buses in cluster ' || cluster_id AS description,
        'GW' AS capacity_unit,
        'TWh' AS activity_unit,
        'daynite' AS timeslicelevel,
        'no' AS vintage
        from df_agg_won_fi_t T1
        """).to_df()
    
        df_agg_won_fi_t = df_agg_won_fi_t.drop(columns=['cluster_id'])
    
    else:
        df_agg_won_fi_t = pd.DataFrame()
        df_agg_won_fi_p = pd.DataFrame()

    
    # now do the same for offwind
    offwind_path = f"1_grids/output_{data_source}/{input_iso}/cluster_summary_wind_offshore.csv"
    if Path(offwind_path).exists():

        df_offwind = pd.read_csv(f"1_grids/output_{data_source}/{input_iso}/cluster_summary_wind_offshore.csv")

        duckdb.register('df_offwind', df_offwind)
        
        df_wof_fi_t = duckdb.sql(f"""
        SELECT
            cluster_id AS "cluster_id", avg_grid_dist_km,
            cluster_id_to_commodity(cluster_id, 'wof', 'process') AS "process",
            cluster_id_to_commodity(cluster_id, 'wof', 'commodity') AS "comm-out",
            "total_re_capacity_mw"/1000 AS "cap_bnd",
            "avg_re_cf" AS "af~fx"
        FROM df_offwind
        """).to_df()

        duckdb.register('df_wof_fi_t', df_wof_fi_t)

        df_wof_fi_p = duckdb.sql("""
        select 
        'ele' AS set,
        process,'wind offshore resource in cluster ' || cluster_id AS description,
        'GW' AS capacity_unit,
        'TWh' AS activity_unit,
        'annual' AS timeslicelevel,
        'no' AS vintage
        from df_wof_fi_t T1
        """).to_df()

        if iso_processor.grid_modeling:
            # connect offwind clusters to buses
            df_offwind_to_bus = pd.read_csv(f"1_grids/output_{data_source}/{input_iso}/cell_to_cluster_mapping_wind_offshore.csv")
            df_offwind_to_bus = df_offwind_to_bus.drop_duplicates(subset=['cluster_id', 'bus_id'])
            df_offwind_to_bus['bus_id'] = df_offwind_to_bus['bus_id'].apply(lambda x: bus_id_to_commodity(x, add_prefix=False))
            duckdb.register('df_offwind_to_bus', df_offwind_to_bus)

            df_agg_wof_fi_t = duckdb.sql(f"""
            SELECT
                'distr_wof' || T1."comm-out" AS process,
                T1."comm-out" AS "comm-in",group_concat('e_' || bus_id) AS "comm-out",
                1 - 0.00006 * T1.avg_grid_dist_km AS efficiency,
                1.1 * T1.avg_grid_dist_km AS "ncap_cost~USD21_alt",
                T1.cluster_id,
            FROM df_wof_fi_t T1
                INNER JOIN df_offwind_to_bus T2
                ON T1.cluster_id = T2.cluster_id
            group by T1."comm-out",T1.cluster_id,T1.avg_grid_dist_km
                """).to_df()

            duckdb.register('df_agg_wof_fi_t', df_agg_wof_fi_t)

            df_agg_wof_fi_p = duckdb.sql("""
            select 
            'pre' AS set,
            process,'connecting wind offshore to buses in cluster ' || cluster_id AS description,
            'GW' AS capacity_unit,
            'TWh' AS activity_unit,
            'daynite' AS timeslicelevel,
            'no' AS vintage
            from df_agg_wof_fi_t T1
            """).to_df()

            df_agg_wof_fi_t = df_agg_wof_fi_t.drop(columns=['cluster_id'])
        else:
            df_agg_wof_fi_t = pd.DataFrame()
            df_agg_wof_fi_p = pd.DataFrame()
    else:
        df_wof_fi_t = pd.DataFrame()
        df_wof_fi_p = pd.DataFrame()
        df_agg_wof_fi_t = pd.DataFrame()
        df_agg_wof_fi_p = pd.DataFrame()


    # Build SQL query conditionally
    sql_parts = [
        """select 'NRG' AS "set","comm-out" as commodity, 'solar electricity generation in cluster -- ' || cluster_id as "description"
            ,'ELC' as commoditytype, 'daynite' as "timeslicelevel", 'TWh' as unit
            from df_solar_fi_t""",
        """select 'NRG' AS "set","comm-out" as commodity, 'onshore wind electricity generation in cluster -- ' || cluster_id as "description"
            ,'ELC' as commoditytype, 'daynite' as "timeslicelevel", 'TWh' as unit
            from df_won_fi_t"""
    ]

    # Only add offshore wind if file exists
    if Path(offwind_path).exists():
        sql_parts.append("""select 'NRG' AS "set","comm-out" as commodity, 'wind offshore electricity generation in cluster -- ' || cluster_id as "description"
            ,'ELC' as commoditytype, 'daynite' as "timeslicelevel", 'TWh' as unit
            from df_wof_fi_t""")

    sql_query = " UNION ".join(sql_parts) + " order by \"comm-out\""
    df_fi_comm_sol_win = duckdb.sql(sql_query).to_df()    

    # Load topology data from temp CSV (if exists)
    topology_data = None
    
    try:
        topology_csv_path = Path("cache") / f"topology_data_{input_iso}.csv"
        if topology_csv_path.exists():
            topology_data = pd.read_csv(topology_csv_path)
    except Exception as e:
        pass  # Silently handle topology data loading errors

    # drop cols cluster_id and avg_grid_dist_km from df_solar_fi_t and df_won_fi_t
    df_solar_fi_t = df_solar_fi_t.drop(columns=['cluster_id', 'avg_grid_dist_km'])
    df_won_fi_t = df_won_fi_t.drop(columns=['cluster_id', 'avg_grid_dist_km'])
    
    if Path(offwind_path).exists():
        df_wof_fi_t = df_wof_fi_t.drop(columns=['cluster_id', 'avg_grid_dist_km'])
    

    return {
        'df_solar_fi_p': df_solar_fi_p,
        'df_solar_fi_t': df_solar_fi_t,
        'df_won_fi_p': df_won_fi_p,
        'df_won_fi_t': df_won_fi_t,
        'df_wof_fi_t': df_wof_fi_t,
        'df_wof_fi_p': df_wof_fi_p,
        'df_agg_sol_fi_t': df_agg_sol_fi_t,
        'df_agg_sol_fi_p': df_agg_sol_fi_p,
        'df_agg_won_fi_t': df_agg_won_fi_t,
        'df_agg_won_fi_p': df_agg_won_fi_p,
        'df_agg_wof_fi_t': df_agg_wof_fi_t,
        'df_agg_wof_fi_p': df_agg_wof_fi_p,
        'df_fi_comm_sol_win': df_fi_comm_sol_win,
        'topology_data': topology_data,
        'grid_modeling_active': iso_processor.grid_modeling
    }