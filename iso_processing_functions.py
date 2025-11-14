import pandas as pd
import duckdb
import numpy as np
import os
import shutil
import xlwings as xw
import openpyxl
from pathlib import Path
import matplotlib.pyplot as plt
import math
import io
import tempfile
from shared_data_loader import get_shared_loader


def calibration_data(iso_processor, df_irena_util, df_ember_util, df_grouped_gem):
    """Collect information to choose between EMBER and IRENA for utilization factors and efficiency tuning."""
    
    # Import smart formatting function
    from data_utils import smart_format_number
    
    duckdb.register('df_irena_util', df_irena_util)
    duckdb.register('df_ember_util', df_ember_util)
    duckdb.register('df_grouped_gem', df_grouped_gem)
    
    # Register UNSD data
    iso_processor.register_unsd_data()
    
    # Main calibration query
    result = duckdb.sql("""
        SELECT T1.iso_code, T1.model_fuel,
        round(SUM(T1.capacity_gw),1) as capacity_gw_gem,
        round(T2.capacity_gw,1) as capacity_gw_irena,
        round(T3.capacity_gw,1) as capacity_gw_ember,
        
        round(SUM(T1.capacity_gw * T2.utilization_factor * 8.76),1) AS generation_twh_gem_irena,
        round(SUM(T1.capacity_gw * T3.utilization_factor * 8.76),1) AS generation_twh_gem_ember,
        round(T3.generation_twh,1) as generation_twh_ember,round(T2.generation_twh,1) as generation_twh_irena,
        
        round(T2.utilization_factor,2) as utilization_factor_irena,
        round(T3.utilization_factor,2) as utilization_factor_ember,
        round(SUM(T1.capacity_gw * coalesce(T1.efficiency, 1)) / SUM(T1.capacity_gw),2) AS avg_efficiency,
        round(SUM(T1.capacity_gw * T2.utilization_factor * 8.76 / coalesce(T1.efficiency, 1)),1) AS fuel_consumed_twh_irena,
        round(SUM(T1.capacity_gw * T3.utilization_factor * 8.76 / coalesce(T1.efficiency, 1)),1) AS fuel_consumed_twh_ember
        
        FROM df_grouped_gem T1
        LEFT join df_irena_util T2 ON T1.model_fuel = T2.model_fuel AND T2.year = '2022'
        LEFT join df_ember_util T3 ON T1.model_fuel = T3.model_fuel AND T3.year = '2022'
        where "Start year" <= '2022'
        GROUP BY T1.iso_code, T1.model_fuel,T2.utilization_factor,T3.utilization_factor,T2.capacity_gw,T3.capacity_gw,T2.generation_twh,T3.generation_twh
        order by T1.iso_code, T1.model_fuel
    """).df()

    # Get UNSD data
    df_unsd_iso = duckdb.sql(f"""
        SELECT T1.TIME_PERIOD AS year,T2.model_fuel,round(SUM(cast(T1.OBS_VALUE as float) * T1.CONVERSION_FACTOR / 1000 / 3.6),1) as fuel_consumed_unsd_twh
        from 
        df_unsd T1
        inner join df_unsd_prodmap T2 ON cast(T2.Code as varchar) = cast(T1.COMMODITY as varchar)
        inner join df_unsd_flowmap T3 ON cast(T3.Code as varchar) = cast(T1.TRANSACTION as varchar)
        where 
        REF_AREA IN (select code from df_unsd_regmap where ISO = '{iso_processor.input_iso}')
        AND T3.attribute.lower() = 'transformation'
        AND T3.sector.lower() = 'power'
        group by T1.TIME_PERIOD,T2.model_fuel
    """).df()

    # Prepare tables for export
    gw_cols = result.columns[:2].tolist() + [col for col in result.columns if '_gw' in col]
    twh_cols = result.columns[:2].tolist() + [col for col in result.columns if 'generation_twh' in col]
    other_cols = result.columns[:2].tolist() + [col for col in result.columns if col not in gw_cols + twh_cols]
    base_year_cols = result.columns[:2].tolist() + [col for col in result.columns if 'generation_twh' in col or 'utilization' in col]

    df_gw = result[gw_cols]
    df_twh = result[twh_cols]
    df_other = result[other_cols]
    df_base_year = result[base_year_cols]
    
    output_path = iso_processor.output_dir / f"VerveStacks_{iso_processor.input_iso}.xlsx"
    
    # Filter UNSD for 2022
    df_unsd_iso = df_unsd_iso[df_unsd_iso['year'] == 2022]
    df_unsd_iso = df_unsd_iso.drop(columns=['year'])

    # Merge with other columns
    if 'model_fuel' in df_other.columns and 'model_fuel' in df_unsd_iso.columns:
        df_combined = pd.merge(df_other, df_unsd_iso, on='model_fuel', how='left')
    else:
        df_combined = pd.concat([df_other.reset_index(drop=True), df_unsd_iso.reset_index(drop=True)], axis=1)

    # Calculate summary metrics for README
    total_capacity_gw = result['capacity_gw_gem'].sum()
    total_generation_twh = result['generation_twh_ember'].sum()  # Use EMBER baseline
    
    # Calculate model CO2 using emission factors and fuel consumption
    EMISSION_FACTORS = {
        'coal': 338.4,  # Mt CO2/TWh (from user's table)
        'gas': 198,     # Mt CO2/TWh  
        'oil': 252      # Mt CO2/TWh
    }
    
    model_co2_mt = 0
    for _, row in result.iterrows():
        fuel = row['model_fuel']
        if fuel in EMISSION_FACTORS:
            fuel_consumed_twh = row['fuel_consumed_twh_ember']
            if pd.notna(fuel_consumed_twh):
                model_co2_mt += fuel_consumed_twh * EMISSION_FACTORS[fuel] / 1000  # Convert to Mt CO2
    
    # Get EMBER's actual CO2 for calibration % (bypass filtered df_ember)
    ember_co2_mt = 0
    try:
        # Create shared_loader instance to access raw EMBER data
        shared_loader = get_shared_loader(iso_processor.main.data_dir)
        raw_ember = shared_loader.get_ember_data()
        
        ember_emissions = raw_ember[
            (raw_ember['Unit'].str.lower() == 'mtco2') & 
            (raw_ember['Country code'] == iso_processor.input_iso) &
            (raw_ember['Variable'] == 'Total emissions') &
            (raw_ember['Year'] == 2022)
        ]
        
        if not ember_emissions.empty:
            ember_co2_mt = ember_emissions['Value'].iloc[0]
            
    except Exception as e:
        print(f"Warning: Could not get EMBER emissions data: {e}")
        ember_co2_mt = 0
    
    calibration_pct = (model_co2_mt / ember_co2_mt * 100) if ember_co2_mt > 0 else 0
    
    # Store summary metrics for README generation
    summary_metrics = {
        'total_capacity_gw': smart_format_number(total_capacity_gw),
        'total_generation_twh': smart_format_number(total_generation_twh), 
        'model_co2_mt': smart_format_number(model_co2_mt),
        'ember_co2_mt': smart_format_number(ember_co2_mt),
        'calibration_pct': smart_format_number(calibration_pct)
    }
    
    # Store efficiency data by fuel for capacity threshold table
    efficiency_by_fuel = {}
    for _, row in result.iterrows():
        fuel = row['model_fuel']
        avg_eff = row['avg_efficiency']
        # Convert to percentage and format
        efficiency_by_fuel[fuel] = f"{smart_format_number(avg_eff * 100)}%"
    
    # Store in iso_processor for access by README generation
    iso_processor.summary_metrics = summary_metrics
    iso_processor.efficiency_by_fuel = efficiency_by_fuel
    
    # Write to Excel using ExcelManager
    from excel_manager import ExcelManager
    excel_mgr = ExcelManager()
    
    try:
        with excel_mgr.workbook(output_path) as wb:
            # Create or replace calibration sheet
            if 'Calibration' in [ws.name for ws in wb.sheets]:
                wb.sheets['Calibration'].delete()
            
            ws = wb.sheets.add('Calibration')
            
            # Add VerveStacks branding first
            excel_mgr.add_vervestacks_branding(ws, start_col='A', merge_cols=10)
            
            # Add sheet documentation (conditional based on iso_processor setting)
            add_docs = getattr(iso_processor, 'add_documentation', True)
            excel_mgr.add_sheet_documentation(ws, 'vervestacks_ISO', 'calibration', add_docs)
            
            # Table 1: Capacity Data (GW)
            current_row = 6
            excel_mgr.write_formatted_table(
                worksheet=ws,
                start_cell=f'A{current_row}',
                dataframe=df_gw,
                veda_marker='Table 1: Capacity Comparison (GW)'
            )
            current_row += len(df_gw) + 4
            
            # Table 2: Generation Data (TWh)
            excel_mgr.write_formatted_table(
                worksheet=ws,
                start_cell=f'A{current_row}',
                dataframe=df_twh,
                veda_marker='Table 2: Generation Analysis (TWh)'
            )
            current_row += len(df_twh) + 4
            
            # Table 3: Combined Analysis
            excel_mgr.write_formatted_table(
                worksheet=ws,
                start_cell=f'A{current_row}',
                dataframe=df_combined,
                veda_marker='Table 3: Detailed Metrics & Validation'
            )
            
            # Add column comments to all tables (conditional)
            if add_docs:
                # Table 1: Add comments to capacity table headers
                table1_header_row = 7  # After VEDA marker
                excel_mgr.add_column_comments(ws, 'vervestacks_ISO', 'calibration', data_start_row=table1_header_row, add_comments=True)
                
                # Table 2: Add comments to generation table headers
                table2_header_row = table1_header_row + len(df_gw) + 5  # After table 1 + spacing + VEDA marker
                excel_mgr.add_column_comments(ws, 'vervestacks_ISO', 'calibration', data_start_row=table2_header_row, add_comments=True)
                
                # Table 3: Add comments to combined table headers  
                table3_header_row = table2_header_row + len(df_twh) + 5  # After table 2 + spacing + VEDA marker
                excel_mgr.add_column_comments(ws, 'vervestacks_ISO', 'calibration', data_start_row=table3_header_row, add_comments=True)
    
    except Exception as e:
        print(f"Error in calibration_data: {e}")
    
    # Use ExcelManager for professional historical data formatting (after xlwings context is closed)
    from excel_manager import excel_manager
    excel_manager.create_historical_data_sheet(output_path, df_ember_util, df_irena_util, iso_processor)


def get_ngfs_data(iso_processor):
    """Collect data to construct future scenarios using published IAMC results."""
    
    # Read variables mapping
    # Use shared loader for IAMC variables mapping
    shared_loader = get_shared_loader("data/")
    df_varbl = shared_loader.get_vs_mappings_sheet("iamc_variables")
    
    # Include CO2 emissions and carbon scenarios in addition to demand/fuel supply projections
    # Option 1: Include specific potential_use categories
    
    standard_categories = df_varbl['potential_use'].isin(['demand_projection', 'fuel_supply', 'scenarios - CO2 abatement', 'CCS potential','elec_co2'])
    
    # Filter df_varbl for standard categories
    df_varbl_standard = df_varbl[standard_categories]

    # Filter NGFS data for the specific ISO and standard variables
    ngfs_df_iso = iso_processor.main.ngfs_df[iso_processor.main.ngfs_df['Region'] == iso_processor.input_iso]
    ngfs_df_iso = ngfs_df_iso[ngfs_df_iso['Variable'].isin(df_varbl_standard['variable'])]
    ngfs_df_iso = ngfs_df_iso.dropna(axis=1, how='all')

    # 

    # Merge with variable info
    df_varbl_for_merge = df_varbl[['variable', 'potential_use','commodity']].drop_duplicates()
    ngfs_df_iso_with_pu = ngfs_df_iso.merge(
        df_varbl_for_merge,
        left_on='Variable',
        right_on='variable',
        how='left'
    )
    
    # Identify year columns for unpivoting
    years = [col for col in ngfs_df_iso_with_pu.columns if str(col).isdigit()]
    
    # Unpivot years in ngfs_df_iso_with_pu and ignore rows with null values. Sort on model, scenario, variable, year.
    id_vars = [col for col in ngfs_df_iso_with_pu.columns if col not in years]
    ngfs_df_iso_with_pu_long = ngfs_df_iso_with_pu.melt(
        id_vars=id_vars,
        value_vars=years,
        var_name="year",
        value_name="value"
    )
    
    # Drop rows with null values in the 'value' column
    ngfs_df_iso_with_pu_long = ngfs_df_iso_with_pu_long.dropna(subset=["value"])
    # Sort by model, scenario, variable, year
    sort_cols = [col for col in ['Model', 'Scenario', 'potential_use', 'Variable', 'year'] if col in ngfs_df_iso_with_pu_long.columns]
    ngfs_df_iso_with_pu_long = ngfs_df_iso_with_pu_long.sort_values(by=sort_cols).reset_index(drop=True)

    # convert secondary energy to emissions
    # Join with iamc_variables to get 'ej_to_mtco2' for each variable
    ngfs_df_iso_with_pu_long = ngfs_df_iso_with_pu_long.merge(
        df_varbl[['variable', 'ej_to_mtco2']],
        left_on='Variable',
        right_on='variable',
        how='left'
    )

    # If 'ej_to_mtco2' is not null, multiply 'value' by 'ej_to_mtco2' and update 'Unit'
    # Exclude REMIND models as they are extremely aggressive on emission reductions
    mask = (
        ngfs_df_iso_with_pu_long['ej_to_mtco2'].notnull() &
        (ngfs_df_iso_with_pu_long['Model'].str.lower().str.contains('remind', na=False) == False)
    )
    ngfs_df_iso_with_pu_long.loc[mask, 'value'] = (
        ngfs_df_iso_with_pu_long.loc[mask, 'value'] * ngfs_df_iso_with_pu_long.loc[mask, 'ej_to_mtco2']
    )
    # Update 'Unit' from 'EJ' to 'Mt CO2' where conversion was applied
    if 'Unit' in ngfs_df_iso_with_pu_long.columns:
        ngfs_df_iso_with_pu_long.loc[mask, 'Unit'] = "Mt CO2"
        ngfs_df_iso_with_pu_long.loc[mask, 'Variable'] = "Emissions|CO2|Power (estimated)"

        
    # Create plots
    variables_sorted = (
        ngfs_df_iso_with_pu[['Variable', 'potential_use', 'Unit']]
        .drop_duplicates()
        .sort_values(by='potential_use', na_position='last')
        .reset_index(drop=True)
    )

    years = [col for col in ngfs_df_iso.columns if str(col).isdigit()]
    years_int = [int(year) for year in years]  # Convert to integers to avoid categorical units warning

    n_vars = len(variables_sorted)
    n_cols = 2
    n_rows = math.ceil(n_vars / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 5 * n_rows), squeeze=False)
    axes = axes.flatten()

    for idx, row in variables_sorted.iterrows():
        var = row['Variable']
        unit = row['Unit'] if pd.notnull(row['Unit']) else "Value"
        ax = axes[idx]
        df_plot = ngfs_df_iso[ngfs_df_iso['Variable'] == var]
        if df_plot.empty:
            ax.set_visible(False)
            continue
        for scenario, group in df_plot.groupby('Scenario'):
            yvals = group[years].values
            if yvals.shape[0] > 1:
                yvals = yvals.mean(axis=0)
            else:
                yvals = yvals.flatten()
            ax.plot(years_int, yvals, marker='o', label=scenario)
        ax.set_title(f"{var} ({iso_processor.input_iso})")
        ax.set_xlabel("Year")
        ax.set_ylabel(unit)
        ax.legend(title="Scenario")
        ax.grid(True, linestyle='--', alpha=0.5)

    # Hide unused subplots
    for j in range(idx + 1, len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout()

    output_path = iso_processor.output_dir / f"VerveStacks_{iso_processor.input_iso}.xlsx"

    # Save chart and data to Excel
    app = xw.App(visible=False)
    try:
        if output_path.exists():
            wb = app.books.open(output_path)
        else:
            wb = app.books.add()
            if len(wb.sheets) > 0:
                for sheet in wb.sheets:
                    if sheet.name.startswith('Sheet'):
                        sheet.delete()

        if "iamc_charts" in [ws.name for ws in wb.sheets]:
            wb.sheets["iamc_charts"].delete()

        ws = wb.sheets.add("iamc_charts")

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            fig.savefig(temp_file.name, format='png', bbox_inches='tight')
            temp_file_path = temp_file.name
        
        ws.pictures.add(temp_file_path, left=ws.range('A1').left, top=ws.range('A1').top)
        os.unlink(temp_file_path)

        wb.save(output_path)
        wb.close()
    finally:
        app.quit()

    # Write IAMC data sheet
    if output_path.exists():
        app = xw.App(visible=False)
        try:
            wb = app.books.open(output_path)
            
            if 'ngfs_scenarios' in [ws.name for ws in wb.sheets]:
                wb.sheets['ngfs_scenarios'].delete()
            
            ws = wb.sheets.add('ngfs_scenarios')
            df_to_write = ngfs_df_iso_with_pu_long
            ws.range('A1').value = [df_to_write.columns.tolist()] + df_to_write.values.tolist()
            
            wb.save()
            wb.close()
        finally:
            app.quit()


def get_rezoning_data(iso_code, use_adjusted=True, technology='both', force_reload=False):
    """
    Get REZoning data for specific ISO with optional land use adjustments.
    
    This function provides access to the globally processed REZoning datasets
    with conservative land use overlap corrections. It serves as the single
    source of truth for all REZoning data access across VerveStacks.
    
    Parameters:
    -----------
    iso_code : str
        ISO country code (e.g., 'CHE', 'IND', 'USA', 'CHN')
    use_adjusted : bool, default=True
        - True: Return land-use adjusted data (recommended)
        - False: Return original REZoning data (for comparison)
    technology : str, default='both'
        - 'solar': Return only solar data
        - 'wind': Return only wind data  
        - 'both': Return both solar and wind data
        - 'all': Return solar, wind onshore, and wind offshore data
    force_reload : bool, default=False
        - True: Force reload from source data (bypass cache)
        - False: Use cached data if available
        
    Returns:
    --------
    dict: REZoning data with keys:
        - 'solar': Solar DataFrame (if requested)
        - 'wind': Wind DataFrame (if requested)
        - 'windoff': Wind Offshore DataFrame (if requested)
        - 'metadata': Processing information
        
    Example:
    --------
    # Get land-use adjusted data for Switzerland
    data = get_rezoning_data('CHE', use_adjusted=True, technology='both')
    solar_df = data['solar']
    wind_df = data['wind']
    
    # Get original data for comparison
    original = get_rezoning_data('CHE', use_adjusted=False, technology='solar')
    """
    
    # Load global processed data using shared data loader (with proper force-reload support)
    print(f"Loading REZoning data for {iso_code}...")
    
    # Use shared data loader for consistent caching behavior
    from shared_data_loader import get_rezoning_data as get_shared_rezoning_data
    
    # Pass through the force_reload parameter to the shared data loader
    global_data = get_shared_rezoning_data(force_reload=force_reload)
    
    # Select appropriate datasets based on use_adjusted flag
    if use_adjusted:
        solar_global = global_data['df_rez_solar']
        wind_global = global_data['df_rez_wind']
        data_type = "land-use adjusted"
    else:
        solar_global = global_data['df_rez_solar_original'] 
        wind_global = global_data['df_rez_wind_original']
        data_type = "original"
    
    # Load offshore wind data from centralized source
    if use_adjusted:
        windoff_global = global_data.get('df_rez_windoff', pd.DataFrame())
    else:
        windoff_global = global_data.get('df_rez_windoff_original', pd.DataFrame())
    
    # Filter by ISO
    solar_iso = solar_global[solar_global['ISO'] == iso_code].copy()
    wind_iso = wind_global[wind_global['ISO'] == iso_code].copy()
    windoff_iso = windoff_global[windoff_global['ISO'] == iso_code].copy() if not windoff_global.empty else pd.DataFrame()
    
    # Prepare result based on technology selection
    result = {}
    
    if technology in ['solar', 'both', 'all']:
        result['solar'] = solar_iso
        
    if technology in ['wind', 'both', 'all']:
        result['wind'] = wind_iso
        
    if technology in ['windoff', 'all']:
        result['windoff'] = windoff_iso
    
    # Add metadata
    result['metadata'] = {
        'iso_code': iso_code,
        'data_type': data_type,
        'technology': technology,
        'solar_cells': len(solar_iso) if technology in ['solar', 'both', 'all'] else 0,
        'wind_cells': len(wind_iso) if technology in ['wind', 'both', 'all'] else 0,
        'windoff_cells': len(windoff_iso) if technology in ['windoff', 'all'] else 0,
        'processing_timestamp': global_data['processing_metadata']['timestamp']
    }
    
    # Print summary
    if technology in ['solar', 'both', 'all']:
        solar_gen = solar_iso['Generation Potential (GWh)'].sum() / 1000
        print(f"Solar ({data_type}): {len(solar_iso)} cells, {solar_gen:.1f} TWh")
        
    if technology in ['wind', 'both', 'all']:
        wind_gen = wind_iso['Generation Potential (GWh)'].sum() / 1000  
        print(f"Wind Onshore ({data_type}): {len(wind_iso)} cells, {wind_gen:.1f} TWh")
        
    if technology in ['windoff', 'all'] and not windoff_iso.empty:
        windoff_gen = windoff_iso['Generation Potential (GWh)'].sum() / 1000
        print(f"Wind Offshore (adjusted): {len(windoff_iso)} cells, {windoff_gen:.1f} TWh")
    
    return result


def get_weo_data(iso_processor):
    """Compile new tech characteristics from WEO data for the appropriate region."""
    
    weo_path = "data/technologies/WEO_2024_PG_Assumptions_STEPSandNZE_Scenario.xlsb"
    tech_mapping_path = "data/technologies/ep_technoeconomic_assumptions.xlsx"
    
    # Load region mapping
    reg_map_df = pd.read_excel(tech_mapping_path, sheet_name="ep_regionmap")
    region_name = reg_map_df.loc[reg_map_df['iso'] == iso_processor.input_iso, 'region'].values[0]
    
    relevant_sheets = [
        "Renewables",
        "Fossil fuels equipped with CCUS", 
        "Nuclear",
        "Gas",
        "Coal"
    ]

    def process_weo_sheet(sheet_name, region_name):
        df = pd.read_excel(weo_path, sheet_name=sheet_name, engine="pyxlsb")

        # Create consistent column headers
        orig_cols = list(df.columns)
        new_header_row = []
        last_name = None
        for col in orig_cols:
            if not (str(col).startswith("Unnamed") or pd.isna(col)):
                last_name = col
            new_header_row.append(last_name)
        df1 = pd.concat([pd.DataFrame([new_header_row], columns=df.columns), df], ignore_index=True)

        # Add attribute row
        second_row = df1.iloc[1]
        filled_second_row = []
        last_val = None
        for val in second_row:
            if pd.notna(val):
                last_val = val
            filled_second_row.append(last_val)
        df2 = pd.concat([df1.iloc[[0]], pd.DataFrame([filled_second_row], columns=df.columns), df1.iloc[1:]], ignore_index=True)

        # Add Technology column
        tech_col = []
        current_tech = None
        for idx, row in df2.iterrows():
            if pd.isna(row.iloc[2]) or str(row.iloc[2]).strip() == '':
                if pd.notna(row.iloc[0]) and str(row.iloc[0]).strip() != '':
                    current_tech = row.iloc[0]
            tech_col.append(current_tech)
        df2.insert(0, "Technology", tech_col)

        # Identify row where years start
        year_row_idx = None
        for idx, val in enumerate(df2.iloc[:, 2]):
            if pd.notna(val) and str(val).isdigit() and len(str(val)) == 4:
                year_row_idx = idx
                break
        if year_row_idx is None:
            year_row_idx = 1

        # Filter by region name
        df_out = pd.concat([
            df2.iloc[:year_row_idx+1],
            df2.iloc[year_row_idx+1:][df2.iloc[year_row_idx+1:, 1] == region_name]
        ], ignore_index=True)
        return df_out

    flat_rows = []

    for sheet in relevant_sheets:
        df_sheet = process_weo_sheet(sheet, region_name)

        # Find the year row index for this sheet
        year_row_idx = None
        for idx, val in enumerate(df_sheet.iloc[:, 2]):
            if pd.notna(val) and str(val).isdigit() and len(str(val)) == 4:
                year_row_idx = idx
                break
        if year_row_idx is None:
            year_row_idx = 1

        for idx in range(year_row_idx + 1, len(df_sheet)):
            row = df_sheet.iloc[idx]
            technology = row['Technology']
            for col_idx in range(2, len(df_sheet.columns)):
                scenario = df_sheet.iloc[0, col_idx]
                attribute = df_sheet.iloc[1, col_idx]
                year = df_sheet.iloc[year_row_idx, col_idx] if year_row_idx < len(df_sheet) else None
                value = row.iloc[col_idx]
                if pd.notna(year) and pd.notna(value):
                    flat_rows.append({
                        'scenario': scenario,
                        'technology': technology,
                        'attribute': attribute,
                        'year': year,
                        'value': value
                    })

    flat_df = pd.DataFrame(flat_rows)

    # Convert to numeric and pivot
    flat_df_numeric = flat_df.copy()
    flat_df_numeric['value'] = pd.to_numeric(flat_df_numeric['value'], errors='coerce')
    flat_df_numeric = flat_df_numeric[flat_df_numeric['value'].notna()]
    weo_pg_final = flat_df_numeric.pivot_table(
        index=['scenario', 'technology', 'attribute'],
        columns='year',
        values='value',
        fill_value=''
    ).reset_index()
    
    # Fix future warning by explicitly inferring object types
    weo_pg_final = weo_pg_final.infer_objects(copy=False)

    # Add model mappings
    df_gem_map = iso_processor.main.df_gem_map
    model_fuel_keywords = (
        df_gem_map[['model_fuel']]
        .drop_duplicates()
        .model_fuel
        .dropna()
        .unique()
    )
    model_fuel_keywords = [str(fuel).lower() for fuel in model_fuel_keywords if isinstance(fuel, str)]

    tech_to_fuel = (
        df_gem_map.drop_duplicates(subset=['Technology', 'model_fuel'])
        .set_index(df_gem_map['Technology'].str.lower())['model_fuel']
        .to_dict()
    )
    
    special_cases = {
        "ccgt": "gas",
        "ccgt + ccs": "gas",
        "ccgt - chp": "gas",
        "fuel cell (distributed electricity generation)": "hydrogen",
        "igcc + ccs": "coal",
        "marine": "hydro",
        "gas turbine": "gas",
        "oxyfuel + ccs": "coal"
    }

    for tech_name, model_fuel in special_cases.items():
        tech_to_fuel[tech_name.lower()] = model_fuel

    def guess_model_fuel(tech):
        tech_l = str(tech).lower()
        if tech_l in tech_to_fuel:
            return tech_to_fuel[tech_l]
        for fuel in model_fuel_keywords:
            if fuel in tech_l:
                return fuel
        return 'unknown'

    attribute_to_model_attribute = {
        "O&M": "ncap_fom",
        "capacity factor": "ncap_af",
        "capital": "ncap_cost",
        "construction time": "ncap_iled",
        "efficiency": "efficiency"
    }

    def get_model_attribute(attr):
        if not isinstance(attr, str):
            return None
        attr_l = attr.lower()
        for key, value in attribute_to_model_attribute.items():
            if key.lower() in attr_l:
                return value
        return None

    weo_pg_final['model_attribute'] = weo_pg_final['attribute'].apply(get_model_attribute)
    weo_pg_final['model_fuel'] = weo_pg_final['technology'].apply(guess_model_fuel)


    # Filter weo_pg_final using allowed technologies from VS_mappings

    weo_pg_techs_df = get_shared_loader("data/").get_vs_mappings_sheet("weo_pg_techs")
    if weo_pg_techs_df is not None and not weo_pg_techs_df.empty:
        allowed_techs = weo_pg_techs_df.iloc[:, 0].dropna().tolist()
        weo_pg_final = weo_pg_final[weo_pg_final['technology'].isin(allowed_techs)]
        print(f"Filtered weo_pg_final to {len(allowed_techs)} allowed technologies")
    else:
        print("Warning: weo_pg_techs sheet not found, keeping all technologies")

    # Write to Excel using ExcelManager
    output_path = iso_processor.output_dir / f"VerveStacks_{iso_processor.input_iso}.xlsx"

    if output_path.exists():
        from excel_manager import excel_manager
        
        with excel_manager.workbook(output_path) as wb:
            # Remove existing weo_pg sheet if it exists
            if 'weo_pg' in [ws.name for ws in wb.sheets]:
                wb.sheets['weo_pg'].delete()
            
            # Add new weo_pg sheet and write formatted data
            ws = wb.sheets.add('weo_pg')
            excel_manager.write_formatted_table(ws, 'B3', weo_pg_final,"Conventional Technologies from WEO")


def create_ccs_retrofits_table(iso_processor, df_grouped_gem):
    """Analyze CCS retrofit potential for existing plants."""
    
    epa_ccs_rf_df = pd.read_excel("data/existing_stock/epa_coal+gas ccs retrofit data.xlsx", sheet_name="epa_ccs_rf")

    duckdb.register('epa_ccs_rf_df', epa_ccs_rf_df)
    duckdb.register('df_grouped_gem', df_grouped_gem)

    result = duckdb.sql("""
        SELECT T1.model_fuel,T1.model_name || '_ccs-rf' as model_name
        ,T2.capex,T2.fixom,T2.varom
        ,(100-T2.heatrate_penalty) * max(T1.efficiency) / 100 AS efficiency
        ,(100-T2.capacity_penalty) * .95 / 100 AS AF
        ,max(T1.efficiency) as efficiency_old
        ,T1.model_name AS plant_old
        FROM df_grouped_gem T1 
        inner join epa_ccs_rf_df T2 ON 
        T1.model_fuel=T2.model_fuel and
        T2.eff1 = 0
        and
        T2.cap1=0

        where lower(T1.model_description) like 'aggregated%' and T1.model_fuel='coal'

        group by T1.model_fuel,T1.model_name,T2.capex,T2.fixom,T2.varom,T2.heatrate_penalty,T2.capacity_penalty

        UNION
        
        SELECT T1.model_fuel,T1.model_name || '_ccs-rf' as model_name
        ,T2.capex,T2.fixom,T2.varom
        ,(100-T2.heatrate_penalty) * T1.efficiency / 100 AS efficiency
        ,(100-T2.capacity_penalty) * .95 / 100 AS AF
        ,T1.efficiency as efficiency_old
        ,T1.model_name AS plant_old
        FROM df_grouped_gem T1 
        inner join epa_ccs_rf_df T2 ON 
        T1.model_fuel=T2.model_fuel and
        T1.efficiency < T2.efficiency and T1.efficiency >= T2.eff1
        and
        T1.capacity_gw < T2.capacity/1000 and T1.capacity_gw >= T2.cap1/1000

        where not lower(T1.model_description) like 'aggregated%' and T1.model_fuel='coal'

        UNION

        SELECT T1.model_fuel,T1.model_name || '_ccs-rf' as model_name
        ,T2.capex,T2.fixom,T2.varom
        ,(100-T2.heatrate_penalty) * max(T1.efficiency) / 100 AS efficiency
        ,(100-T2.capacity_penalty) * .95 / 100 AS AF
        ,max(T1.efficiency) as efficiency_old
        ,T1.model_name AS plant_old
        FROM df_grouped_gem T1 
        inner join epa_ccs_rf_df T2 ON 
        T2.model_fuel='gas'
        
        where T1.model_fuel IN ('gas','oil')

        group by T1.model_fuel,T1.model_name,T2.capex,T2.fixom,T2.varom,T2.heatrate_penalty,T2.capacity_penalty
    """).df()

    # Write to Excel
    output_path = iso_processor.output_dir / f"VerveStacks_{iso_processor.input_iso}.xlsx"
    
    if output_path.exists():
        from excel_manager import excel_manager
        
        with excel_manager.workbook(output_path) as wb:
            # Remove existing ccs_retrofits sheet if it exists
            if 'ccs_retrofits' in [ws.name for ws in wb.sheets]:
                wb.sheets['ccs_retrofits'].delete()
            
            # Add new ccs_retrofits sheet and write formatted data
            ws = wb.sheets.add('ccs_retrofits')
            result_sorted = result.sort_values(by='model_name')
            excel_manager.write_formatted_table(ws, 'B3', result_sorted,"CCS Retrofits")
    
    return result


def re_targets_ember(iso_processor):
    """Extract renewable energy targets from Ember data."""
    
    ember_raw_data_long = pd.read_excel("data/ember/ember_targets_download2025Oct.xlsx", sheet_name="raw_data_long")
    ember_sources = pd.read_excel("data/ember/ember_targets_download2025Oct.xlsx", sheet_name="sources")

    duckdb.register('ember_raw_data_long', ember_raw_data_long)
    duckdb.register('ember_sources', ember_sources)

    result = duckdb.sql(f"""
        select T1.TARGET_YEAR,T1.FUEL_CATEGORY,T1.METRIC,T1.VALUE,
        T2.SOURCE_TYPE,T2.SOURCE_NAME,T2.PUBLISHER,T2.ANNOUNCEMENT_DATE,T2.LINK,T2.SOURCE_SUMMARY,T2.NOTES
        from ember_raw_data_long T1
        inner join ember_sources T2 on T1.SOURCE_ID=T2.SOURCE_ID
        where T1.COUNTRY_CODE='{iso_processor.input_iso}'
        order by T2.SOURCE_TYPE,T1.METRIC,T1.FUEL_CATEGORY
    """).df()

    # Write to Excel
    output_path = iso_processor.output_dir / f"VerveStacks_{iso_processor.input_iso}.xlsx"
        
    if output_path.exists():
        from excel_manager import excel_manager
        
        with excel_manager.workbook(output_path) as wb:
            # Remove existing re_targets sheet if it exists
            if 're_targets' in [ws.name for ws in wb.sheets]:
                wb.sheets['re_targets'].delete()
            
            ws = wb.sheets.add('re_targets')
            excel_manager.write_formatted_table(ws, 'B3', result,"RE Targets from EMBER")

    # return the result dataframe
    return result


def get_electricity_trade_data(iso_processor):
    """
    Get electricity trade data for a specific ISO, using UNSD data if available,
    otherwise estimating from EMBER net imports data.
    Returns a tuple of (dataframe, source).
    """
    input_iso = iso_processor.input_iso
    
    # First, try to get UNSD data
    if iso_processor.main.df_electricity_trade is not None:
        df_unsd_trade_iso = iso_processor.main.df_electricity_trade.reset_index()
        df_unsd_trade_iso = df_unsd_trade_iso[df_unsd_trade_iso['ISO'] == input_iso]
        
        if not df_unsd_trade_iso.empty:
            return df_unsd_trade_iso, "UNSD"
    
    # If UNSD data not available, estimate from EMBER net imports
    if iso_processor.main.df_ember_trade is not None:
        df_ember_trade_iso = iso_processor.main.df_ember_trade[iso_processor.main.df_ember_trade['ISO'] == input_iso]
        
        if not df_ember_trade_iso.empty:
            # Get the net imports data
            net_imports_row = df_ember_trade_iso.iloc[0]
            
            # Get all year columns (excluding 'ISO')
            years = [col for col in net_imports_row.index if str(col).isdigit()]
            
            # Create estimated import/export data based on net imports
            result_data = []
            
            # Create Import row
            import_row = {'ISO': input_iso, 'attribute': 'Import'}
            export_row = {'ISO': input_iso, 'attribute': 'Export'}
            
            for year in years:
                net_imports = net_imports_row[year]
                if pd.notna(net_imports):
                    if net_imports > 0:
                        # Net importer: imports = net_imports, exports = 0
                        import_row[year] = net_imports
                        export_row[year] = 0.0
                    else:
                        # Net exporter: imports = 0, exports = abs(net_imports)
                        import_row[year] = 0.0
                        export_row[year] = abs(net_imports)
                else:
                    import_row[year] = 0.0
                    export_row[year] = 0.0
            
            result_data.append(import_row)
            result_data.append(export_row)
            
            df_result = pd.DataFrame(result_data)
            return df_result, "EMBER (estimated)"
    
    # If no data available, return empty DataFrame and no source
    return pd.DataFrame(), None 