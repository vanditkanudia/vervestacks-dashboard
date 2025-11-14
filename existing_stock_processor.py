import pandas as pd
import numpy as np
import duckdb
import os
import shutil
import xlwings as xw
from pathlib import Path
from shared_data_loader import get_shared_loader
from spatial_utils import bus_id_to_commodity, grid_cell_to_commodity, cluster_id_to_commodity, calculate_rez_weights, distribute_capacity_by_weights, calculate_capacity_distribution, calculate_thermal_bus_weights


def add_missing_irena_capacity(df_gem_iso, fuel_type, iso_processor=None, existing_plants_with_spatial=None, buses_data=None, zones_data=None):
    """
    Compare IRENA 2022 renewable capacity with cumulative GEM capacity (years ≤ 2022).
    If IRENA > GEM, distribute the difference spatially across REZ zones based on resource quality.
    """
    df_irena_c = iso_processor.main.df_irena_c
    input_iso = iso_processor.input_iso
    grid_modeling = iso_processor.grid_modeling
    
    # Technology mapping for different fuel types
    tech_mapping = {
        'solar': {'Technology': 'PV', 'Type': 'solar', 'description': 'Solar'},
        'windon': {'Technology': 'Onshore', 'Type': 'wind', 'description': 'Onshore wind energy'},
        'windoff': {'Technology': 'Offshore', 'Type': 'wind', 'description': 'Offshore wind energy'},
        'hydro': {'Technology': 'conventional storage', 'Type': 'hydropower', 'description': 'Hydro'}
    }
    
    if fuel_type not in tech_mapping:
        print(f"Warning: Unknown fuel type '{fuel_type}'. Skipping.")
        return df_gem_iso
    
    # Get IRENA capacity for 2022
    irena_capacity_2022 = df_irena_c[
        (df_irena_c['iso_code'] == input_iso) & 
        (df_irena_c['model_fuel'] == fuel_type) & 
        (df_irena_c['Year'] == 2022)
    ]['Electricity statistics (MW/GWh)'].sum() / 1000  # Convert MW to GW
    
    # Get cumulative GEM capacity for years <= 2022
    gem_capacity_cumulative = df_gem_iso[
        (df_gem_iso['model_fuel'] == fuel_type) & 
        (df_gem_iso['Start year'] <= 2022)
    ]['Capacity (MW)'].sum() / 1000  # Convert MW to GW
    
    # Calculate the difference
    capacity_difference_gw = irena_capacity_2022 - gem_capacity_cumulative
    
    print(f"IRENA {fuel_type} capacity 2022: {irena_capacity_2022:.2f} GW")
    print(f"GEM cumulative {fuel_type} capacity (≤2022): {gem_capacity_cumulative:.2f} GW")
    print(f"Difference: {capacity_difference_gw:.2f} GW")
    
    # If difference > 0, add missing capacity with spatial distribution
    if capacity_difference_gw > 0:
        print(f"Adding {capacity_difference_gw:.2f} GW of missing {fuel_type} capacity to df_gem_iso")
        
        # Only use spatial distribution if grid modeling is active
        distribution = {}
        if grid_modeling or fuel_type in ['solar', 'windon', 'windoff']:
            
            # Use unified distribution function
            distribution = calculate_capacity_distribution(
                fuel_type=fuel_type,
                capacity_gw=capacity_difference_gw,
                input_iso=input_iso,
                buses_data=buses_data,
                zones_data=zones_data,
                existing_plants_df=existing_plants_with_spatial
            )
            print(f"Grid modeling enabled or solar/wind case: using spatial distribution for {fuel_type}")
        else:
            print(f"Grid modeling disabled: creating single aggregated {fuel_type} record")
        
        # Create records based on distribution
        spatial_records = []
        tech_info = tech_mapping[fuel_type]
        
        if distribution:
            print(f"Distributing {fuel_type} gap capacity across {len(distribution)} locations:")
            for location_id, allocated_gw in distribution.items():
                # print(f"  - {location_id}: {allocated_gw:.3f} GW")
                
                # Calculate spatial field before pd.Series
                if fuel_type in ['solar', 'windon', 'windoff']:
                    spatial_field = {'cluster_id': location_id}
                else:
                    spatial_field = {'bus_id': location_id}
                
                new_row = pd.Series({
                    'iso_code': input_iso,
                    'model_fuel': fuel_type,
                    'Capacity (MW)': allocated_gw * 1000,  # Convert back to MW
                    'Plant / Project name': f'Aggregated Plant - IRENA Gap - {location_id}',
                    'Unit / Phase name': f'Missing {tech_info["description"]} Capacity',
                    'GEM unit/phase ID': None,
                    'Status': 'operating',
                    'Start year': 2022,
                    'Technology': tech_info['Technology'],
                    'Type': tech_info['Type'],
                    **spatial_field  # Add spatial fields to the series
                })
                
                spatial_records.append(new_row)
        else:
            # Fallback: single aggregated record
            print(f"No spatial distribution available for {fuel_type}, creating single aggregated record")
            new_row = pd.Series({
                'iso_code': input_iso,
                'model_fuel': fuel_type,
                'Capacity (MW)': capacity_difference_gw * 1000,  # Convert back to MW
                'Plant / Project name': f'Aggregated Plant - IRENA Gap',
                'Unit / Phase name': f'Missing {tech_info["description"]} Capacity',
                'GEM unit/phase ID': None,
                'Status': 'operating',
                'Start year': 2022,
                'Technology': tech_info['Technology'],
                'Type': tech_info['Type']
            })
            spatial_records = [new_row]
        
        # Add all records to df_gem_iso
        for record in spatial_records:
            df_gem_iso = pd.concat([df_gem_iso, record.to_frame().T], ignore_index=True)
        
        print(f"Added {len(spatial_records)} new {fuel_type} record(s) for year 2022 with {capacity_difference_gw:.2f} GW total")
    else:
        print(f"No missing {fuel_type} capacity to add")
    
    return df_gem_iso


def add_missing_ember_capacity(df_gem_iso, fuel_type, iso_processor=None, existing_plants_with_spatial=None, buses_data=None):
    """
    Compare EMBER 2022 thermal capacity with cumulative GEM capacity (years ≤ 2022).
    If EMBER > GEM, add the difference as a new record for 2022.
    """
    df_ember = iso_processor.main.df_ember
    input_iso = iso_processor.input_iso
    grid_modeling = iso_processor.grid_modeling
    
    # Technology mapping for different fuel types
    tech_mapping = {
        'bioenergy': {'Technology': 'bioenergy', 'Type': 'bioenergy', 'description': 'Bioenergy'},
        'coal': {'Technology': 'subcritical', 'Type': 'coal', 'description': 'Coal'},
        'gas': {'Technology': 'combined cycle', 'Type': 'gas', 'description': 'Gas'},
        'oil': {'Technology': 'gas turbine', 'Type': 'oil', 'description': 'Oil'}
    }
    
    if fuel_type not in tech_mapping:
        print(f"Warning: Unknown fuel type '{fuel_type}'. Skipping.")
        return df_gem_iso
    
    # Get EMBER capacity for 2022
    ember_capacity_2022 = df_ember[
        (df_ember['iso_code'] == input_iso) & 
        (df_ember['model_fuel'] == fuel_type) & 
        (df_ember['Year'] == 2022) &
        (df_ember['Unit'] == 'GW')
    ]['Value'].sum()  # Already in GW
    
    # Get cumulative GEM capacity for years <= 2022
    gem_capacity_cumulative = df_gem_iso[
        (df_gem_iso['model_fuel'] == fuel_type) & 
        (df_gem_iso['Start year'] <= 2022)
    ]['Capacity (MW)'].sum() / 1000  # Convert MW to GW
    
    # Calculate the difference
    capacity_difference_gw = ember_capacity_2022 - gem_capacity_cumulative
    
    print(f"EMBER {fuel_type} capacity 2022: {ember_capacity_2022:.2f} GW")
    print(f"GEM cumulative {fuel_type} capacity (≤2022): {gem_capacity_cumulative:.2f} GW")
    print(f"Difference: {capacity_difference_gw:.2f} GW")
    
    # If difference > 0, add missing capacity
    if capacity_difference_gw > 0:
        print(f"Adding {capacity_difference_gw:.2f} GW of missing {fuel_type} capacity to df_gem_iso")
        
        # Only use spatial distribution if grid modeling is active
        distribution = {}
        if grid_modeling:
            # Use unified distribution function for thermal plants
            distribution = calculate_capacity_distribution(
                fuel_type=fuel_type,
                capacity_gw=capacity_difference_gw,
                input_iso=input_iso,
                buses_data=buses_data,
                zones_data=pd.DataFrame(),  # Ember is thermal, doesn't use REZ data
                existing_plants_df=existing_plants_with_spatial
            )
            print(f"Grid modeling enabled: using thermal distribution for {fuel_type}")
        else:
            print(f"Grid modeling disabled: creating single aggregated {fuel_type} record")
        
        # Create records based on distribution
        spatial_records = []
        tech_info = tech_mapping[fuel_type]
        
        if distribution:
            print(f"Distributing {fuel_type} gap capacity across {len(distribution)} buses:")
            for bus_id, allocated_gw in distribution.items():
                # Convert numpy float to regular float to avoid data type issues
                allocated_gw = float(allocated_gw)
                # print(f"  - {bus_id}: {allocated_gw:.3f} GW")
                
                new_row = pd.Series({
                    'iso_code': input_iso,
                    'model_fuel': fuel_type,
                    'Capacity (MW)': allocated_gw * 1000,  # Convert back to MW
                    'Plant / Project name': f'Aggregated Plant - EMBER Gap - {bus_id}',
                    'Unit / Phase name': f'Missing {tech_info["description"]} Capacity',
                    'GEM unit/phase ID': None,
                    'Status': 'operating',
                    'Start year': 2022,
                    'Technology': tech_info['Technology'],
                    'Type': tech_info['Type'],
                    'bus_id': bus_id  # Add spatial information
                })

                spatial_records.append(new_row)
        else:
            # Fallback: single aggregated record
            print(f"No thermal distribution available for {fuel_type}, creating single aggregated record")
            new_row = pd.Series({
                'iso_code': input_iso,
                'model_fuel': fuel_type,
                'Capacity (MW)': capacity_difference_gw * 1000,  # Convert back to MW
                'Plant / Project name': f'Aggregated Plant - EMBER Gap',
                'Unit / Phase name': f'Missing {tech_info["description"]} Capacity',
                'GEM unit/phase ID': None,
                'Status': 'operating',
                'Start year': 2022,
                'Technology': tech_info['Technology'],
                'Type': tech_info['Type']
            })
            spatial_records = [new_row]
        
        # Add all records to df_gem_iso
        for record in spatial_records:
            df_gem_iso = pd.concat([df_gem_iso, record.to_frame().T], ignore_index=True)
        
        print(f"Added {len(spatial_records)} new {fuel_type} record(s) for year 2022 with {capacity_difference_gw:.2f} GW total")
    else:
        print(f"No missing {fuel_type} capacity to add")
    
    return df_gem_iso


def get_costs_and_eff(input_iso, input_size, input_model_name, input_year, 
                     costs_df, costs_size_multipliers_df, reg_mult_df, 
                     reg_map_df, thermal_eff_df):
    """Get costs and efficiency for a specific plant configuration."""
    
    # Get all year columns from thermal_eff_df that are less than input_year
    year_cols = [col for col in thermal_eff_df.columns if str(col).isdigit() and int(col) < input_year]
    if year_cols:
        max_year = max(year_cols, key=lambda x: int(x))
    else:
        max_year = min([col for col in thermal_eff_df.columns if str(col).isdigit()], key=lambda x: int(x))

    # Check if input_model_name ends with any model_name in thermal_eff_df
    matching_base_names = thermal_eff_df[thermal_eff_df['model_name'].apply(lambda x: input_model_name.lower().endswith(x.lower()))]
    
    if matching_base_names.empty:
        # No efficiency data for this model_name: skip the efficiency join, set efficiency=1
        result = duckdb.query(f"""
            SELECT 
                T1.capex * T2.capex * T3.capex as capex, 
                T1.fixom * T2.fixom * T3.fixom as fixom, 
                T1.varom * T2.varom * T3.varom as varom, 
                1 as efficiency
            FROM
            (SELECT * from costs_df WHERE lower('{input_model_name}') LIKE '%' || lower(model_name)) T1
            CROSS JOIN
            (SELECT * from costs_size_multipliers_df WHERE size = (SELECT max(size) from costs_size_multipliers_df where size < {input_size})) T2
            CROSS JOIN
            (Select T1.* from reg_mult_df T1 INNER JOIN reg_map_df T2 ON T1.region = T2.region WHERE T2.iso = '{input_iso}') T3
        """).to_df()
    else:
        
        # Query the table for the particular model_name, including efficiency
        result = duckdb.query(f"""
            SELECT 
                T1.capex * T2.capex * T3.capex as capex, 
                T1.fixom * T2.fixom * T3.fixom as fixom, 
                T1.varom * T2.varom * T3.varom as varom, 
                T4.efficiency * T3.efficiency as efficiency
            FROM
            (SELECT * from costs_df WHERE lower('{input_model_name}') LIKE '%' || lower(model_name)) T1
            CROSS JOIN
            (SELECT * from costs_size_multipliers_df WHERE size = (SELECT max(size) from costs_size_multipliers_df where size < {input_size})) T2
            CROSS JOIN
            (Select T1.* from reg_mult_df T1 INNER JOIN reg_map_df T2 ON T1.region = T2.region WHERE T2.iso = '{input_iso}') T3
            CROSS JOIN
            (SELECT "{max_year}" as efficiency from thermal_eff_df where lower('{input_model_name}') LIKE '%' || lower(model_name) AND size = (SELECT max(size) from thermal_eff_df where size < {input_size})) T4
        """).to_df()

    return result


def load_uc_data():
    """Load unit commitment data and mappings."""
    uc_data = pd.read_excel('data/technologies/advanced_parameters.xlsx', sheet_name='uc_data')
    uc_tech_map = pd.read_excel('data/technologies/advanced_parameters.xlsx', sheet_name='uc_tech_map')
    return uc_data, uc_tech_map


def find_technology_for_model(model_name, uc_tech_map):
    """Find technology using simple startswith matching."""
    for _, row in uc_tech_map.iterrows():
        technology = row['technology']
        model_patterns = row['model_name'].split(',')
        
        for pattern in model_patterns:
            pattern = pattern.strip()
            if model_name.startswith(pattern):
                return technology
    
    return None


def determine_size_class(technology, capacity_mw):
    """Determine size class based on technology and capacity in MW."""
    size_rules = {
        'OCGT (Peaker)': [(50, '<50 MW'), (200, '50-200 MW'), (float('inf'), '>200 MW')],
        'CCGT': [(300, '<300 MW'), (float('inf'), '>300 MW')],
        'Gas/Oil Steam': [(200, '<200 MW'), (float('inf'), '>200 MW')],
        'Diesel': [(20, '<20 MW'), (float('inf'), '>20 MW')],
        'Subcritical Coal': [(300, '<300 MW'), (float('inf'), '>300 MW')],
        'Supercritical Coal': [(500, '<500 MW'), (float('inf'), '>500 MW')],
        'Nuclear': [(float('inf'), 'All')]
    }
    
    if technology in size_rules:
        for threshold, size_class in size_rules[technology]:
            if capacity_mw < threshold:
                return size_class
    return None


def get_uc_parameters(uc_data, technology, size_class):
    """Get unit commitment parameters for given technology and size class."""
    mask = (uc_data['technology'] == technology) & (uc_data['Size Class'] == size_class)
    matching_rows = uc_data[mask]
    
    if len(matching_rows) == 0:
        return None
    
    row = matching_rows.iloc[0]
    return {
        'min_stable_factor_pct': row['Min Stable Factor (%)'],
        'min_up_time_h': row['Min Up Time (h)'],
        'min_down_time_h': row['Min Down Time (h)'],
        'max_ramp_up_pct_h': row['Max Ramp Up (%/h)'],
        'max_ramp_down_pct_h': row['Max Ramp Down (%/h)'],
        'startup_time_h': row['Startup Time (h)'],
        'startup_cost_per_mw': row['Startup Cost ($/MW)'],
        'shutdown_cost_per_mw': row['Shutdown Cost ($/MW)']
    }


def add_uc_parameters_to_df(df, uc_data, uc_tech_map):
    """Add unit commitment parameters using simple startswith matching."""
    df = df.copy()
    
    # Initialize new columns
    df['uc_technology'] = ''
    df['uc_size_class'] = ''
    
    for col in ['min_stable_factor_pct', 'min_up_time_h', 'min_down_time_h', 
                'max_ramp_up_pct_h', 'max_ramp_down_pct_h', 'startup_time_h', 
                'startup_cost_per_mw', 'shutdown_cost_per_mw']:
        df[col] = np.nan
    
    # Track stats
    matched_count = 0
    total_thermal = 0
    
    # Process each plant
    for idx, row in df.iterrows():
        model_name = row['model_name']
        capacity_mw = row['Capacity_GW'] * 1000  # Convert GW to MW
        
        # Simple startswith matching - much cleaner!
        technology = find_technology_for_model(model_name, uc_tech_map)
        
        if technology is None:
            continue  # Skip non-thermal plants
        
        total_thermal += 1
        size_class = determine_size_class(technology, capacity_mw)
        
        if size_class:
            uc_params = get_uc_parameters(uc_data, technology, size_class)
            if uc_params:
                df.at[idx, 'uc_technology'] = technology
                df.at[idx, 'uc_size_class'] = size_class
                
                for param_name, param_value in uc_params.items():
                    df.at[idx, param_name] = param_value
                
                matched_count += 1
    
    return df


def process_existing_stock(iso_processor, add_documentation=True):
    """
    Process existing stock data for the given ISO.
    
    Args:
        iso_processor: ISO processor instance
        add_documentation: If False, skips documentation for faster testing (default: True)
    """
    
    # EXCEL COM INITIALIZATION: Warm up COM environment at pipeline start
    import time
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            print(f"🔥 Initializing Excel COM environment (attempt {attempt + 1}/{max_attempts})...")
            test_app = xw.App(visible=False)
            test_app.display_alerts = False
            
            # Give COM time to fully initialize, especially on first attempt
            if attempt == 0:
                time.sleep(3)  # Cold start buffer
                print("   ⏳ Allowing extra time for COM initialization...")
            else:
                time.sleep(1)  # Quick retry buffer
            
            # Test basic functionality
            test_app.quit()
            print("   ✅ Excel COM environment ready")
            break
            
        except Exception as e:
            print(f"   ⚠️  Excel COM attempt {attempt + 1} failed: {e}")
            
            # Clean up failed attempt
            try:
                if 'test_app' in locals():
                    test_app.quit()
            except:
                pass
            
            # If not the last attempt, wait and retry
            if attempt < max_attempts - 1:
                wait_time = 2 * (attempt + 1)  # Progressive backoff: 2s, 4s
                print(f"   🔄 Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                # All attempts failed
                raise RuntimeError(
                    f"❌ FATAL: Excel COM failed after {max_attempts} attempts\n"
                    f"Final error: {e}\n"
                    f"Solutions: 1) Restart Excel processes, 2) Reboot system, 3) Check Office installation"
                )
    
    # Load template and set up output file
    template_path = "Assumptions/vervestacks_ISO_template.xlsx"
    output_path = iso_processor.output_dir / f"VerveStacks_{iso_processor.input_iso}.xlsx"

    def read_cell(ws, cell):
        value = ws.range(cell).value
        return value

    if output_path.exists():
        app = xw.App(visible=False)
        try:
            wb = app.books.open(output_path)
            ws = wb.sheets['system_settings']
            efficiency_adjustment_gas = ws.range('A4').value
            efficiency_adjustment_coal = ws.range('A5').value
            capacity_threshold = ws.range('A3').value
            wb.close()
        finally:
            app.quit()
    else:
        try:
            shutil.copyfile(template_path, output_path)
            app = xw.App(visible=False)
            try:
                wb = app.books.open(output_path)

                if 'system_settings' in [ws.name for ws in wb.sheets]:
                    ws = wb.sheets['system_settings']
                else:
                    ws = wb.sheets[0]

                ws.range('A1').value = iso_processor.input_iso
                ws.range('A3').value = iso_processor.capacity_threshold

                efficiency_adjustment_gas = read_cell(ws, 'A4') or iso_processor.efficiency_adjustment_gas
                efficiency_adjustment_coal = read_cell(ws, 'A5') or iso_processor.efficiency_adjustment_coal

                wb.save()
                wb.close()
            finally:
                app.quit()

        except Exception as e:
            print(f"Error setting up template: {e}")
            raise

    # Copy template folder immediately after Excel file setup
    from veda_model_creator import copy_vs_iso_template
    
    try:
        template_folder = copy_vs_iso_template(
            input_iso=iso_processor.input_iso,
            output_dir=iso_processor.output_dir,
            auto_commit=iso_processor.auto_commit,
            grid_modeling=iso_processor.grid_modeling,
            data_source=getattr(iso_processor, 'data_source', None)
        )
        print(f"✅ Template folder copied to: {template_folder}")
        
        # Store template folder path for later use
        iso_processor.template_folder = template_folder
        
    except Exception as e:
        print(f"Error copying template folder: {e}")
        raise

    # Calculate utilization factors for IRENA and EMBER
    df_irena_util = calculate_irena_utilization(iso_processor)
    df_ember_util = calculate_ember_utilization(iso_processor)
    
    # Process GEM data for existing stock
    df_grouped_gem, buses_to_attach_thermal, buses_to_attach_hydro, buses_to_attach_storage = process_gem_data(iso_processor, efficiency_adjustment_gas, efficiency_adjustment_coal, grid_modeling=iso_processor.grid_modeling)
    # Create enhanced grid SVG with 20km buffer (only if grid_modeling enabled)
    create_enhanced_grid_svg(iso_processor, df_grouped_gem, buffer_km=20.0)
    
    # Create topology data for grid modeling (if active)
    if iso_processor.grid_modeling:
        if len(buses_to_attach_thermal) > 0 or len(buses_to_attach_hydro) > 0 or len(buses_to_attach_storage) > 0:
            create_topology_data_csv(iso_processor.input_iso, buses_to_attach_thermal, buses_to_attach_hydro, buses_to_attach_storage)
    
    # Write existing stock data to Excel using excel_manager
    from excel_manager import ExcelManager
    
    excel_mgr = ExcelManager()
    df_sorted = df_grouped_gem.sort_values(by=['model_name', 'Start year'])
    
    try:
        with excel_mgr.workbook(output_path) as wb:
            # Create or replace existing_stock sheet
            if 'existing_stock' in [ws.name for ws in wb.sheets]:
                wb.sheets['existing_stock'].delete()
            
            ws = wb.sheets.add('existing_stock')
            
            # Add VerveStacks branding first (with logo and blue background)
            excel_mgr.add_vervestacks_branding(ws, start_col='A', merge_cols=len(df_sorted.columns))
            
            # Add sheet documentation (skips row 1 since branding is already there)
            excel_mgr.add_sheet_documentation(ws, 'vervestacks_ISO', 'existing_stock', add_documentation)
            
            # Write formatted table with VerveStacks branding AFTER documentation
            excel_mgr.write_formatted_table(
                worksheet=ws,
                start_cell='A6',  # Start after documentation (rows 1, 3, 4)
                dataframe=df_sorted,
                veda_marker='existing_stock'
            )
            
            # Add rich column comments to headers at row 6
            excel_mgr.add_column_comments(ws, 'vervestacks_ISO', 'existing_stock', data_start_row=6, add_comments=add_documentation)

            # Write bus attachment data to subres_trans file
            
    except Exception as e:
        print(f"Error writing existing stock data with excel_manager: {e}")
        raise
    
    return df_irena_util, df_ember_util, df_grouped_gem


def calculate_irena_utilization(iso_processor):
    """Calculate utilization factors from IRENA data."""
    
    # Filter for specific ISO and group by iso_code, model_fuel, and year
    df_irena_c_iso = (
        iso_processor.main.df_irena_c[iso_processor.main.df_irena_c['iso_code'] == iso_processor.input_iso]
        .groupby(['iso_code', 'model_fuel', 'Year'], as_index=False)
        .agg({'Electricity statistics (MW/GWh)': lambda x: x.sum() / 1000})
    )
    df_irena_g_iso = (
        iso_processor.main.df_irena_g[iso_processor.main.df_irena_g['iso_code'] == iso_processor.input_iso]
        .groupby(['iso_code', 'model_fuel', 'Year'], as_index=False)
        .agg({'Electricity statistics (MW/GWh)': lambda x: x.sum() / 1000})
    )

    # Standardize column names for merging
    df_irena_c_iso = df_irena_c_iso.rename(columns={
        'Electricity statistics (MW/GWh)': 'Capacity_GW'
    })
    df_irena_g_iso = df_irena_g_iso.rename(columns={
        'Electricity statistics (MW/GWh)': 'Generation_TWh'
    })

    # Merge on Country, Type, Year
    df_irena_util = pd.merge(
        df_irena_c_iso[['iso_code', 'model_fuel', 'Year', 'Capacity_GW']],
        df_irena_g_iso[['iso_code', 'model_fuel', 'Year', 'Generation_TWh']],
        on=['iso_code', 'model_fuel', 'Year'],
        how='inner'
    )

    # Compute utilization factor
    df_irena_util['utilization_factor'] = df_irena_util['Generation_TWh'] / (df_irena_util['Capacity_GW'] * 8.76)
    df_irena_util = df_irena_util.rename(columns={'Year': 'year'})
    
    return df_irena_util


def calculate_ember_utilization(iso_processor):
    """Calculate utilization factors from EMBER data."""
    
    # Get capacity (GW) by country code, year, Type
    df_capacity = iso_processor.main.df_ember[
        (iso_processor.main.df_ember['Unit'] == 'GW') & 
        (iso_processor.main.df_ember['iso_code'] == iso_processor.input_iso)
    ].copy()

    df_capacity = (
        df_capacity
        .groupby(['iso_code', 'Year', 'model_fuel'], as_index=False)['Value']
        .sum()
    )
    df_capacity = df_capacity.rename(columns={'Value': 'Capacity_GW'})

    df_generation = iso_processor.main.df_ember[
        (iso_processor.main.df_ember['Unit'] == 'TWh') & 
        (iso_processor.main.df_ember['iso_code'] == iso_processor.input_iso)
    ].copy()
    df_generation = (
        df_generation
        .groupby(['iso_code', 'model_fuel', 'Year'], as_index=False)['Value']
        .sum()
    )
    df_generation = df_generation.rename(columns={'Value': 'Generation_TWh'})
    
    # Merge on Country code, Year, Type
    df_ember_util = pd.merge(
        df_capacity,
        df_generation[['iso_code', 'model_fuel', 'Year', 'Generation_TWh']],
        on=['iso_code', 'model_fuel', 'Year'],
        how='inner'
    )

    
    # Compute utilization factor
    df_ember_util['utilization_factor'] = df_ember_util['Generation_TWh'] / (df_ember_util['Capacity_GW'] * 8.76)
    df_ember_util = df_ember_util.rename(columns={'Year': 'year'})

    
    return df_ember_util


def load_efficiency_adjustments(iso_code):
    """Load efficiency adjustment factors from YAML configuration file."""
    import yaml
    from pathlib import Path
    
    config_path = Path("config/efficiency_adjustments.yaml")
    
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        # Get country-specific factors or fall back to defaults
        if iso_code in config:
            country_config = config[iso_code]
            coal_factor = country_config.get('coal_factor', 1.0)
            gas_factor = country_config.get('gas_factor', 1.0)
            notes = country_config.get('notes', '')
            print(f"📊 Using efficiency adjustments for {iso_code}: Coal={coal_factor}, Gas={gas_factor}")
            if notes:
                print(f"   📝 Notes: {notes}")
        else:
            # Use defaults
            default_config = config.get('default', {})
            coal_factor = default_config.get('coal_factor', 1.0)
            gas_factor = default_config.get('gas_factor', 1.0)
            print(f"📊 Using default efficiency adjustments for {iso_code}: Coal={coal_factor}, Gas={gas_factor}")
        
        return coal_factor, gas_factor
        
    except FileNotFoundError:
        print(f"⚠️  Efficiency adjustments file not found: {config_path}")
        print("   Using default factors: Coal=1.0, Gas=1.0")
        return 1.0, 1.0
    except Exception as e:
        print(f"⚠️  Error loading efficiency adjustments: {e}")
        print("   Using default factors: Coal=1.0, Gas=1.0")
        return 1.0, 1.0


def process_gem_data(iso_processor, efficiency_adjustment_gas, efficiency_adjustment_coal,grid_modeling=False):
    """Process GEM data to create existing stock characteristics."""
    
    import pandas as pd
    from pathlib import Path
    
    # Load efficiency adjustments from YAML (override command-line parameters)
    yaml_coal_factor, yaml_gas_factor = load_efficiency_adjustments(iso_processor.input_iso)
    
    # Use YAML factors if they differ from defaults, otherwise use command-line parameters
    if yaml_coal_factor != 1.0 or yaml_gas_factor != 1.0:
        efficiency_adjustment_coal = yaml_coal_factor
        efficiency_adjustment_gas = yaml_gas_factor
        print(f"🔧 Overriding command-line efficiency adjustments with YAML config")

    # Load techno-economic data
    # Use shared loader for technoeconomic assumptions
    shared_loader = get_shared_loader("data/")
    # costs_df = shared_loader.get_technoeconomic_sheet("costs")
    costs_df = pd.read_excel("data/technologies/ep_technoeconomic_assumptions.xlsx", sheet_name="costs")
    costs_size_multipliers_df = shared_loader.get_technoeconomic_sheet("costs_size_multipliers")
    reg_mult_df = shared_loader.get_technoeconomic_sheet("regional_multipliers")
    reg_map_df = shared_loader.get_technoeconomic_sheet("ep_regionmap")
    # Load thermal_eff without caching (always fresh)
    thermal_eff_df = pd.read_excel("data/technologies/ep_technoeconomic_assumptions.xlsx", sheet_name="thermal_eff")
    re_units_cf_grid_cell_mapping = pd.read_csv("data/GlobalEnergyMonitor/re_units_cf_grid_cell_mapping.csv")

    # Register DataFrames for DuckDB
    duckdb.register('costs_df', costs_df)
    duckdb.register('costs_size_multipliers_df', costs_size_multipliers_df)
    duckdb.register('reg_mult_df', reg_mult_df)
    duckdb.register('reg_map_df', reg_map_df)
    duckdb.register('thermal_eff_df', thermal_eff_df)

    # Filter df_gem for the specific ISO
    df_gem_iso = iso_processor.main.df_gem[iso_processor.main.df_gem['iso_code'] == iso_processor.input_iso]

    # Filter for active statuses before joining
    # statuses_to_keep = ['operating', 'construction', 'mothballed']
    # df_gem_iso = df_gem_iso[df_gem_iso['Status'].isin(statuses_to_keep)]
    # 21-09-25: Only excludes retired. other statuses will be offered as potential new techs. Retired plants are already excluded in verve_stacks_processor.py


    def is_valid_year(val):
        try:
            year = int(val)
            return 1900 <= year <= 2100
        except (ValueError, TypeError):
            return False

    # Get status map once outside the function
    status_map = iso_processor.main.df_gem_status_map
    
    def get_start_year(row, status_map):
        year_val = row['Start year']
        if not is_valid_year(year_val):
            # Get default year from status map
            status_match = status_map[status_map['status'].str.lower() == str(row['Status']).lower()]
            return int(status_match['default_year'].iloc[0])
        return int(year_val)

    df_gem_iso['Start year'] = df_gem_iso.apply(lambda row: get_start_year(row, status_map), axis=1)


    # 20 Sep 2025 - replace the grid_cell capacity factors with cluster-level capacity factors
    # Load all cluster summary files and cell-to-cluster mappings
    cluster_data = {}
    cell_to_cluster_mapping = {}
    
    if Path(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/cluster_summary_solar.csv").exists():
        cluster_data['solar'] = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/cluster_summary_solar.csv")
        cell_to_cluster_mapping['solar'] = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/cell_to_cluster_mapping_solar.csv")

    if Path(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/cluster_summary_wind_onshore.csv").exists():
        cluster_data['windon'] = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/cluster_summary_wind_onshore.csv")
        cell_to_cluster_mapping['windon'] = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/cell_to_cluster_mapping_wind_onshore.csv")
        
    if Path(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/cluster_summary_wind_offshore.csv").exists():
        cluster_data['windoff'] = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/cluster_summary_wind_offshore.csv")
        cell_to_cluster_mapping['windoff'] = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/cell_to_cluster_mapping_wind_offshore.csv")

    # Update capacity factors in re_units_cf_grid_cell_mapping using grid_cell → cluster_id → avg_re_cf mapping
    for fuel_type in ['solar', 'windon', 'windoff']:
        if fuel_type in cluster_data and fuel_type in cell_to_cluster_mapping:
            # Step 1: Create grid_cell → cluster_id mapping
            cell_to_cluster = dict(zip(
                cell_to_cluster_mapping[fuel_type]['grid_cell'], 
                cell_to_cluster_mapping[fuel_type]['cluster_id']
            ))
            
            # Step 2: Create cluster_id → avg_re_cf mapping
            cluster_to_cf = dict(zip(
                cluster_data[fuel_type]['cluster_id'], 
                cluster_data[fuel_type]['avg_re_cf']
            ))
            # Step 3: Update capacity factors where model_fuel matches and grid_cell exists in mapping
            mask = (re_units_cf_grid_cell_mapping['model_fuel'] == fuel_type) & \
                   (re_units_cf_grid_cell_mapping['grid_cell'].isin(cell_to_cluster.keys()))
            
            # Map grid_cell → cluster_id → avg_re_cf
            re_units_cf_grid_cell_mapping.loc[mask, 'capacity_factor'] = \
                re_units_cf_grid_cell_mapping.loc[mask, 'grid_cell'].map(cell_to_cluster).map(cluster_to_cf)
            
            print(f"Updated {mask.sum()} {fuel_type} units with cluster-level capacity factors")        


    # 31 Aug 2025 - wind offshore loop
    # add capacity factor and grid cell to df_gem_iso
    # this will be used to determine CF of RE units regardless of grid modeling
    # and it already brings grid_cell col in the df. no need for zone-bus mapping
    df_gem_iso = df_gem_iso.merge(re_units_cf_grid_cell_mapping,
        left_on=['GEM unit/phase ID'], 
        right_on=['GEM_unit/phase_ID'], 
        how='left', 
        suffixes=('', '_mapping'))
    
    # Clean up duplicate columns from merge
    if 'model_fuel_mapping' in df_gem_iso.columns:
        df_gem_iso = df_gem_iso.drop('model_fuel_mapping', axis=1)

    # Load spatial mapping data for thermal distribution (if grid modeling enabled)
    existing_plants_with_spatial = df_gem_iso.copy()
    buses_data = None
    
    if grid_modeling:
        print("Loading spatial mapping data for thermal distribution...")
        try:
            # Load bus data for voltage-based fallback
            buses_file = f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/{iso_processor.input_iso}_clustered_buses.csv"
            if os.path.exists(buses_file):
                buses_data = pd.read_csv(buses_file, index_col=0)
                print(f"Loaded {len(buses_data)} buses for thermal distribution")
                
            # Load power plants to buses mapping
            mapping_file = f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/{iso_processor.input_iso}_power_plants_assigned_to_buses.csv"
            if os.path.exists(mapping_file):
                mapping_data = pd.read_csv(mapping_file)
                
                # Merge existing plants with spatial data for thermal distribution analysis
                existing_plants_with_spatial = df_gem_iso.merge(
                    mapping_data[['GEM location ID', 'bus_id']],
                    on='GEM location ID',
                    how='left'
                )

                bus_count = existing_plants_with_spatial['bus_id'].notna().sum()
                grid_count = existing_plants_with_spatial['grid_cell'].notna().sum()
                print(f"Spatial mapping loaded: {bus_count} plants have bus assignments, {grid_count} have grid_cell assignments")
                
        except Exception as e:
            print(f"Warning: Could not load spatial data for thermal distribution: {e}")
        
        # Use the spatially-enhanced dataframe from this point forward
        df_gem_iso = existing_plants_with_spatial.copy()
        print("Switched to using spatially-enhanced dataframe for all subsequent operations")
    else:
        print("Grid modeling disabled - using original dataframe without spatial enhancements")

    # Add missing capacity from IRENA and EMBER reference datasets with spatial distribution
    df_gem_iso = add_missing_irena_capacity(df_gem_iso, 'solar', iso_processor, existing_plants_with_spatial, buses_data, cluster_data.get('solar'))
    df_gem_iso = add_missing_irena_capacity(df_gem_iso, 'windon', iso_processor, existing_plants_with_spatial, buses_data, cluster_data.get('windon'))
    df_gem_iso = add_missing_irena_capacity(df_gem_iso, 'windoff', iso_processor, existing_plants_with_spatial, buses_data, cluster_data.get('windoff'))
    df_gem_iso = add_missing_irena_capacity(df_gem_iso, 'hydro', iso_processor, existing_plants_with_spatial, buses_data, None)
    df_gem_iso = add_missing_ember_capacity(df_gem_iso, 'bioenergy', iso_processor, existing_plants_with_spatial, buses_data)
    df_gem_iso = add_missing_ember_capacity(df_gem_iso, 'coal', iso_processor, existing_plants_with_spatial, buses_data)
    df_gem_iso = add_missing_ember_capacity(df_gem_iso, 'gas', iso_processor, existing_plants_with_spatial, buses_data)
    
    
    # 31 Aug 2025 - model_fuel/model_name are already populated upstream in verve_stacks_processor.py
    # BUT new gap-filling records still need model_name populated
    
    # Only process records where model_name is missing (new gap-filling records)
    needs_model_name = df_gem_iso['model_name'].isna()
    missing_count = needs_model_name.sum()
    
    if missing_count > 0:
        print(f"🔧 Populating model_name for {missing_count} new gap-filling records")
        
        # Create temporary dataframe for records that need model_name
        temp_df = df_gem_iso[needs_model_name][['model_fuel', 'Technology']].merge(
            iso_processor.main.df_gem_map[['model_fuel', 'Technology', 'model_name']], 
            on=['model_fuel', 'Technology'], 
            how='left'
        )
        
        # Update only the missing model_name values with ep_ prefix
        df_gem_iso.loc[needs_model_name, 'model_name'] = 'ep_' + temp_df['model_name'].fillna('').astype(str)
        
        # Verify the update worked
        remaining_missing = df_gem_iso['model_name'].isna().sum()
        print(f"✅ Updated {missing_count - remaining_missing} records, {remaining_missing} still missing")
    else:
        print("✅ All records already have model_name from upstream processing")
    
    # Fill any remaining missing model_names for gap-filling records
    df_gem_iso['model_name'] = df_gem_iso['model_name'].fillna(df_gem_iso['model_fuel'].apply(lambda x: f'ep_{x}'))

    # The new units added might have model_name + year duplication - aggregate them



    # Apply cost and efficiency functions
    def apply_get_costs_and_eff(row):
        iso = row['iso_code']
        size = row['Capacity (MW)'] if 'Capacity (MW)' in row else None
        model_name = row['model_name'].lower() if 'model_name' in row else None
        year = row['Start year'] if 'Start year' in row else None
        if None in (iso, size, model_name, year):
            return [None, None, None, None]
        try:
            res = get_costs_and_eff(iso, size, model_name, year, costs_df, 
                                   costs_size_multipliers_df, reg_mult_df, 
                                   reg_map_df, thermal_eff_df)
            return res.iloc[0].tolist()
        except Exception as e:
            return [None, None, None, None]

    new_cols = ['capex', 'fixom', 'varom', 'efficiency']
    df_gem_iso[new_cols] = df_gem_iso.apply(apply_get_costs_and_eff, axis=1, result_type='expand')

    # Fill missing efficiency values
    df_gem_iso.loc[(df_gem_iso['efficiency'].isnull()) | (df_gem_iso['efficiency'] == 0), 'efficiency'] = 0.33123

    # Apply efficiency adjustments
    df_gem_iso.loc[df_gem_iso['model_name'].str.lower().str.startswith('ep_gas'), 'efficiency'] = (
        df_gem_iso.loc[df_gem_iso['model_name'].str.lower().str.startswith('ep_gas'), 'efficiency'] * efficiency_adjustment_gas
    )

    df_gem_iso.loc[df_gem_iso['model_name'].str.lower().str.startswith('ep_oil'), 'efficiency'] = (
        df_gem_iso.loc[df_gem_iso['model_name'].str.lower().str.startswith('ep_oil'), 'efficiency'] * efficiency_adjustment_gas
    )

    df_gem_iso.loc[df_gem_iso['model_name'].str.lower().str.startswith('ep_coal'), 'efficiency'] = (
        df_gem_iso.loc[df_gem_iso['model_name'].str.lower().str.startswith('ep_coal'), 'efficiency'] * efficiency_adjustment_coal
    )

    df_gem_iso.loc[df_gem_iso['model_name'].str.lower().str.startswith('ep_bio'), 'efficiency'] = (
        df_gem_iso.loc[df_gem_iso['model_name'].str.lower().str.startswith('ep_bio'), 'efficiency'] * efficiency_adjustment_coal
    )


    # if df_gem_iso has spatial_id, add it to the model_name
    # if 'spatial_id' in df_gem_iso.columns:
    #     df_gem_iso['model_name'] = df_gem_iso['model_name'] + df_gem_iso['spatial_id'].fillna('')

    # Load fuel-specific capacity thresholds for this ISO
    
    thresholds_file = Path('assumptions/iso_fuel_capacity_thresholds.csv')
    if thresholds_file.exists():
        df_thresholds_all = pd.read_csv(thresholds_file)
        iso_thresholds = df_thresholds_all[df_thresholds_all['iso_code'] == iso_processor.input_iso]
        
        if not iso_thresholds.empty:
            # Create simple model_fuel | capacity_threshold DataFrame
            fuel_threshold_data = []
            fuel_columns = ['bioenergy', 'coal', 'gas', 'geothermal', 'hydro', 'nuclear', 'oil', 'solar', 'windoff', 'windon']
            
            for fuel in fuel_columns:
                if fuel in iso_thresholds.columns:
                    threshold = iso_thresholds[fuel].iloc[0]
                    fuel_threshold_data.append({'model_fuel': fuel, 'capacity_threshold': threshold})
            
            df_fuel_thresholds = pd.DataFrame(fuel_threshold_data)
            print(f"   📊 Loaded fuel-specific thresholds for {iso_processor.input_iso}: {len(df_fuel_thresholds)} fuels")
        else:
            print(f"   ⚠️  No thresholds found for {iso_processor.input_iso}, using global threshold")
            df_fuel_thresholds = pd.DataFrame()
    else:
        print(f"   ⚠️  Thresholds file not found, using global threshold")
        df_fuel_thresholds = pd.DataFrame()
    
    # Store fuel thresholds in ISO processor for later use in documentation
    iso_processor.df_fuel_thresholds = df_fuel_thresholds

    duckdb.register('df_fuel_thresholds', df_fuel_thresholds)

    # collect lists of buses to attach new techs with adaptive capacity threshold
    if 'bus_id' in df_gem_iso.columns:
        
        # Collect bus_ids for plants above fuel-specific thresholds
        if not df_fuel_thresholds.empty:
            # Create a merged DataFrame to apply fuel-specific thresholds
            df_with_thresholds = df_gem_iso.merge(
                df_fuel_thresholds, 
                on='model_fuel', 
                how='left'
            )
            
            # Get thermal buses (coal, gas, nuclear) above their thresholds
            buses_to_attach_thermal = df_with_thresholds[
                (df_with_thresholds['model_fuel'].notna()) &
                (df_with_thresholds['model_fuel'].isin(['coal', 'gas', 'nuclear'])) &
                (df_with_thresholds['Capacity (MW)'] > df_with_thresholds['capacity_threshold'].fillna(0)) &
                (df_with_thresholds['bus_id'].notna())
            ]['bus_id'].unique()
            
            # Get hydro buses above their thresholds
            buses_to_attach_hydro = df_with_thresholds[
                (df_with_thresholds['model_fuel'].notna()) &
                (df_with_thresholds['model_fuel'].isin(['hydro'])) &
                (df_with_thresholds['Capacity (MW)'] > df_with_thresholds['capacity_threshold'].fillna(0)) &
                (df_with_thresholds['bus_id'].notna())
            ]['bus_id'].unique()
            
            # Get storage buses (all plants above their fuel-specific thresholds)
            buses_to_attach_storage = df_with_thresholds[
                (df_with_thresholds['model_fuel'].notna()) &
                (df_with_thresholds['Capacity (MW)'] > df_with_thresholds['capacity_threshold'].fillna(0)) &
                (df_with_thresholds['bus_id'].notna())
            ]['bus_id'].unique()
            
        else:
            # Fallback to global threshold if no fuel-specific thresholds available
            buses_to_attach_thermal = df_gem_iso[
                (df_gem_iso['model_fuel'].notna()) &
                (df_gem_iso['model_fuel'].isin(['coal', 'gas', 'nuclear'])) &
                (df_gem_iso['Capacity (MW)'] > iso_processor.capacity_threshold) &
                (df_gem_iso['bus_id'].notna())
            ]['bus_id'].unique()
            
            buses_to_attach_hydro = df_gem_iso[
                (df_gem_iso['model_fuel'].notna()) &
                (df_gem_iso['model_fuel'].isin(['hydro'])) &
                (df_gem_iso['Capacity (MW)'] > iso_processor.capacity_threshold) &
                (df_gem_iso['bus_id'].notna())
            ]['bus_id'].unique()
            
            buses_to_attach_storage = df_gem_iso[
                (df_gem_iso['Capacity (MW)'] > iso_processor.capacity_threshold) &
                (df_gem_iso['bus_id'].notna())
            ]['bus_id'].unique()

        # Load the bus load share file
        if iso_processor.data_source.startswith('syn'):
            bus_load_file = Path(f"1_grids/output_{iso_processor.data_source}") / iso_processor.input_iso / f"{iso_processor.input_iso}_bus_load_share.csv"
        else:
            bus_load_file = Path(f"1_grids/output_{iso_processor.data_source}") / iso_processor.input_iso / f"{iso_processor.input_iso}_bus_load_share_voronoi.csv"

        bus_load_df = pd.read_csv(bus_load_file)
        # Filter for non-zero load share
        buses_to_attach_demand = bus_load_df[bus_load_df['load_share'] > 0]['bus_id'].unique()

    else:
        buses_to_attach_thermal = []
        buses_to_attach_hydro = []
        buses_to_attach_storage = []
        buses_to_attach_demand = []
    

    # Apply single commodity assignment for all plants
    print("Applying single commodity assignment...")
    df_gem_iso = assign_single_commodity(df_gem_iso, iso_processor=iso_processor)
    print("Commodity assignment completed.")

    df_gem_iso.to_csv(f"output/df_gem_iso_after_commodity_assignment.csv", index=False)

    if grid_modeling:
        # Write buses to replicate in regions tag of subres trans
        from excel_manager import ExcelManager
        excel_mgr = ExcelManager()
        
        # Load technology lists for replication
        shared_loader = get_shared_loader("data/")
        
        # 1. Thermal techs: from VS_mappings, weo_pg_techs sheet, filter by _include = 'y'
        weo_pg_techs_df = shared_loader.get_vs_mappings_sheet("weo_pg_techs")
        thermal_techs = weo_pg_techs_df[weo_pg_techs_df['_include'].str.lower() == 'y']['tech'].dropna().tolist()
        thermal_tech_list = ','.join(thermal_techs)
        
        # 2. Hydro techs: from re_potentials.xlsx, process sheet, filter by _ISO_
        hydro_df = pd.read_excel("data/technologies/re_potentials.xlsx", sheet_name="process")
        iso_filter = f"_{iso_processor.input_iso}-"  # e.g., "_CHE_"
        hydro_techs = hydro_df[hydro_df['process'].str.contains(iso_filter, na=False)]['process'].dropna().tolist()
        hydro_tech_list = ','.join(hydro_techs)
        
        # 3. Storage techs: from VS_mappings, storage_techs sheet
        storage_techs_df = shared_loader.get_vs_mappings_sheet("storage_techs")
        storage_tech_list = ','.join(storage_techs_df['tech'].dropna().tolist())
        
        # 4. Demand techs: from VS_mappings, storage_techs sheet, filter by _include = 'y'
        demand_techs_df = shared_loader.get_vs_mappings_sheet("dem_techs")
        demand_tech_list = ','.join(demand_techs_df['tech'].dropna().tolist())

        # Create regions DataFrames for VEDA syntax with bus_id transformation
        df_thermal_regions = pd.DataFrame({
            'region': [iso_processor.input_iso] * len(buses_to_attach_thermal),
            'incode': [bus_id_to_commodity(bus_id, False) for bus_id in buses_to_attach_thermal],
            'indesc': [f"at grid node - {bus_id_to_commodity(bus_id, False)}" for bus_id in buses_to_attach_thermal],
            'process': [thermal_tech_list] * len(buses_to_attach_thermal)
        }) if len(buses_to_attach_thermal) > 0 else pd.DataFrame(columns=['region', 'incode', 'indesc', 'process'])
        
        df_hydro_regions = pd.DataFrame({
            'region': [iso_processor.input_iso] * len(buses_to_attach_hydro),
            'incode': [bus_id_to_commodity(bus_id, False) for bus_id in buses_to_attach_hydro],
            'indesc': [f"at grid node - {bus_id_to_commodity(bus_id, False)}" for bus_id in buses_to_attach_hydro],
            'process': [hydro_tech_list] * len(buses_to_attach_hydro)
        }) if len(buses_to_attach_hydro) > 0 else pd.DataFrame(columns=['region', 'incode', 'indesc', 'process'])
        
        df_storage_regions = pd.DataFrame({
            'region': [iso_processor.input_iso] * len(buses_to_attach_storage),
            'incode': [bus_id_to_commodity(bus_id, False) for bus_id in buses_to_attach_storage],
            'indesc': [f"at grid node - {bus_id_to_commodity(bus_id, False)}" for bus_id in buses_to_attach_storage],
            'process': [storage_tech_list] * len(buses_to_attach_storage)
        }) if len(buses_to_attach_storage) > 0 else pd.DataFrame(columns=['region', 'incode', 'indesc', 'process'])

        df_demand_regions = pd.DataFrame({
            'region': [iso_processor.input_iso] * len(buses_to_attach_demand),
            'incode': [bus_id_to_commodity(bus_id, False) for bus_id in buses_to_attach_demand],
            'indesc': [f"at grid node - {bus_id_to_commodity(bus_id, False)}" for bus_id in buses_to_attach_demand],
            'process': [demand_tech_list] * len(buses_to_attach_demand)
        }) if len(buses_to_attach_demand) > 0 else pd.DataFrame(columns=['region', 'incode', 'indesc', 'process'])

        # Write to SubRES_New_RE_and_Conventional_Trans.xlsx
        # Use the same path construction as veda_model_creator.py
        models_dir = Path("C:/Veda/Veda/Veda_models/vervestacks_models")
        
        # Create model folder path with data_source suffix
        if grid_modeling and hasattr(iso_processor, 'data_source') and iso_processor.data_source:
            folder_suffix = f"_grids_{iso_processor.data_source}"
        elif grid_modeling:
            folder_suffix = "_grids"
        else:
            folder_suffix = ""
        dest_folder = models_dir / f"VerveStacks_{iso_processor.input_iso}{folder_suffix}"
        trans_file = dest_folder / "SubRES_Tmpl" / "SubRES_New_RE_and_Conventional_Trans.xlsx"
        
        with excel_mgr.workbook(trans_file, create_new=False) as wb:
            # Add or get grids sheet
            if 'AVA' in [ws.name for ws in wb.sheets]:
                ws = wb.sheets['AVA']
                # ws.clear()
            else:
                ws = wb.sheets.add('AVA')
                         
            # Write three tables side by side with ~replicateinregions markers
            excel_mgr.write_formatted_table(ws, 'B10', df_thermal_regions, '~replicateinregions')
            excel_mgr.write_formatted_table(ws, 'G10', df_hydro_regions, '~replicateinregions')
            excel_mgr.write_formatted_table(ws, 'L10', df_storage_regions, '~replicateinregions')
            excel_mgr.write_formatted_table(ws, 'Q10', df_demand_regions, '~replicateinregions')
            

        print(f"✅ Grid regions file created: {trans_file}")
        print(f"   - Thermal buses: {len(buses_to_attach_thermal)} with {len(thermal_techs)} technologies")
        print(f"   - Hydro buses: {len(buses_to_attach_hydro)} with {len(hydro_techs)} technologies") 
        print(f"   - Storage buses: {len(buses_to_attach_storage)} with {len(storage_techs_df)} technologies")

    def get_spatial_suffix(row):
        comm_out = row.get('comm-out', 'ELC')
        model_fuel = row.get('model_fuel', '')
        
        if comm_out == 'ELC':
            return ''
        
        if model_fuel in ['solar', 'windon', 'windoff']:
            return comm_out[-3:]  # Last 3 characters
        else:
            return comm_out[2:]   # Skip "e_" prefix
            
    df_gem_iso['spatial_suffix'] = df_gem_iso.apply(get_spatial_suffix, axis=1)


    duckdb.register('df_gem_iso', df_gem_iso)

    # Create query for grouped GEM data
    query = f"""
            SELECT  
                (
                    CASE 
                        WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) AND COALESCE(CAST("GEM unit/phase ID" AS VARCHAR), '') <> '' THEN CAST(model_name AS VARCHAR) || '_' || COALESCE(CAST("GEM unit/phase ID" AS VARCHAR), '')
                        WHEN upper(T1."comm-out") <> 'ELC' THEN 
                            CAST(model_name AS VARCHAR) || '_' || CAST(T1.spatial_suffix AS VARCHAR)
                        ELSE CAST(model_name AS VARCHAR)
                    END
                    ||
                    CASE 
                        WHEN lower("Plant / Project name") like '%irena gap%' THEN '__irena'
                        WHEN lower("Plant / Project name") like '%ember gap%' THEN '__ember'
                        ELSE ''
                    END
                ) AS model_name,
                CASE
                    WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) THEN CAST("Plant / Project name" AS VARCHAR) || '_' || COALESCE(CAST("Unit / Phase name" AS VARCHAR), '')
                    ELSE 'Aggregated Plant'
                END 
                ||
                ' -- ' || T1.Status
                AS model_description,
                T1.model_fuel,
                iso_code, 
                "Start year",
                CASE 
                    WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) THEN coalesce(CAST("Retired year" AS VARCHAR), '')
                    ELSE ''
                END AS "retirement_year",
                CASE 
                    WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) THEN coalesce(CAST("Subnational unit (state, province)" AS VARCHAR), '')
                    ELSE ''
                END AS "state",
                CASE 
                    WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) THEN coalesce(CAST("City" AS VARCHAR), '')
                    ELSE ''
                END AS "city",
                T1.Status,
                T1."comm-out",T1.spatial_suffix,
                SUM("Capacity (MW)") / 1000 AS Capacity_GW,
                SUM("Capacity (MW)" * capex) / NULLIF(SUM("Capacity (MW)"), 0) AS capex,
                SUM("Capacity (MW)" * fixom) / NULLIF(SUM("Capacity (MW)"), 0) AS fixom,
                SUM("Capacity (MW)" * varom) / NULLIF(SUM("Capacity (MW)"), 0) AS varom,
                SUM("Capacity (MW)" * efficiency) / NULLIF(SUM("Capacity (MW)"), 0) AS efficiency,
                SUM("Capacity (MW)" * capacity_factor) / NULLIF(SUM("Capacity (MW)"), 0) AS capacity_factor
            FROM df_gem_iso T1
            LEFT JOIN df_fuel_thresholds T2
            ON T1.model_fuel = T2.model_fuel
            GROUP BY
                (
                    CASE 
                        WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) AND COALESCE(CAST("GEM unit/phase ID" AS VARCHAR), '') <> '' THEN CAST(model_name AS VARCHAR) || '_' || COALESCE(CAST("GEM unit/phase ID" AS VARCHAR), '')
                        WHEN upper(T1."comm-out") <> 'ELC' THEN 
                            CAST(model_name AS VARCHAR) || '_' || CAST(T1.spatial_suffix AS VARCHAR)
                        ELSE CAST(model_name AS VARCHAR)
                    END
                    ||
                    CASE 
                        WHEN lower("Plant / Project name") like '%irena gap%' THEN '__irena'
                        WHEN lower("Plant / Project name") like '%ember gap%' THEN '__ember'
                        ELSE ''
                    END
                ),
                CASE
                    WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) THEN CAST("Plant / Project name" AS VARCHAR) || '_' || COALESCE(CAST("Unit / Phase name" AS VARCHAR), '')
                    ELSE 'Aggregated Plant'
                END,
                T1.model_fuel,
                iso_code, 
                "Start year",
                CASE 
                    WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) THEN coalesce(CAST("Retired year" AS VARCHAR), '')
                    ELSE ''
                END,
                CASE 
                    WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) THEN coalesce(CAST("Subnational unit (state, province)" AS VARCHAR), '')
                    ELSE ''
                END,
                CASE 
                    WHEN "Capacity (MW)" >= COALESCE(T2.capacity_threshold, {iso_processor.capacity_threshold}) THEN coalesce(CAST("City" AS VARCHAR), '')
                    ELSE ''
                END,
                T1.Status,
                T1."comm-out",T1.spatial_suffix

        """

    df_grouped_gem = duckdb.sql(query).df()

    # model_fuel solar, windon, and windoff will have capacity_factor for most records, but the missing capacity that has been added will not have it
    # assign the average capacity_factor of the records with capacity_factor for the model_fuel
    # For each model_fuel in ['solar', 'windon', 'windoff'], fill missing capacity_factor with the average for that model_fuel
    for mf in ['solar', 'windon', 'windoff']:
        mask = (df_grouped_gem['model_fuel'] == mf)
        if 'capacity_factor' in df_grouped_gem.columns:
            avg_cf = df_grouped_gem.loc[mask & df_grouped_gem['capacity_factor'].notna(), 'capacity_factor'].mean()
            # Only fill where missing
            df_grouped_gem.loc[mask & df_grouped_gem['capacity_factor'].isna(), 'capacity_factor'] = avg_cf


    # Add UC parameters
    uc_data, uc_tech_map = load_uc_data()
    df_grouped_gem_with_uc = add_uc_parameters_to_df(df_grouped_gem, uc_data, uc_tech_map)
    df_grouped_gem_with_uc = df_grouped_gem_with_uc.drop(columns=['uc_technology', 'uc_size_class'])

    return df_grouped_gem_with_uc, buses_to_attach_thermal, buses_to_attach_hydro, buses_to_attach_storage


def assign_single_commodity(df_gem_iso, iso_processor=None):
    """
    Single commodity assignment function for all plants based on fuel type and spatial data.
    
    Args:
        df_gem_iso: DataFrame with all plants (original + gap-filled)
        grid_modeling: Whether grid modeling is enabled
        input_iso: Country ISO code
        
    Returns:
        DataFrame with comm-out column assigned
    """

    print("Assigning single commodity...")
    
    input_iso = iso_processor.input_iso
    grid_modeling = iso_processor.grid_modeling

    # Check if grid_cell column is present and show some stats
    if 'grid_cell' in df_gem_iso.columns:
        grid_count = df_gem_iso['grid_cell'].notna().sum()
        total_count = len(df_gem_iso)
        print(f"✅ grid_cell column preserved: {grid_count}/{total_count} plants have grid_cell assignments")
    else:
        print("❌ grid_cell column is missing!")
    

    def assign_commodity_single(row):
        model_fuel = row.get('model_fuel', '')
        
        # Solar/Wind: use cluster_id for solar/wind regardless of grid modeling
        if model_fuel in ['solar', 'windon', 'windoff']:
            cluster_id = row.get('cluster_id', None)
            if pd.notna(cluster_id):
                if model_fuel == 'solar':
                    return cluster_id_to_commodity(cluster_id, 'spv', 'commodity')
                elif model_fuel == 'windon':
                    return cluster_id_to_commodity(cluster_id, 'won', 'commodity')
                elif model_fuel == 'windoff':
                    return cluster_id_to_commodity(cluster_id, 'wof', 'commodity')

        if grid_modeling:
            # Grid modeling mode: spatial commodities
            
            # All other plants: use bus_id for spatial commodity
            bus_id = row.get('bus_id', None)
            if pd.notna(bus_id):
                return bus_id_to_commodity(bus_id, add_prefix=True)
            
            # Fallback for grid modeling
            return 'ELC'
            
        else:
            return 'ELC'
    
    # Load mapping files using data_source from iso_processor
    # Note: This function needs iso_processor parameter to access data_source
    # For now, derive data_source from grid_modeling parameter for backward compatibility
    
    df_solar_to_bus = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{input_iso}/cell_to_cluster_mapping_solar.csv")
    df_won_to_bus = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{input_iso}/cell_to_cluster_mapping_wind_onshore.csv")

    if Path(f"1_grids/output_{iso_processor.data_source}/{input_iso}/cell_to_cluster_mapping_wind_offshore.csv").exists():
        df_wof_to_bus = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{input_iso}/cell_to_cluster_mapping_wind_offshore.csv")
        df_wof_to_bus = df_wof_to_bus.drop_duplicates(subset=['grid_cell', 'cluster_id'])
        df_wof_to_bus['grid_cell'] = 'wof-' + df_wof_to_bus['grid_cell'].astype(str)

    else:
        df_wof_to_bus = pd.DataFrame()

    df_solar_to_bus = df_solar_to_bus.drop_duplicates(subset=['grid_cell', 'cluster_id'])
    df_won_to_bus = df_won_to_bus.drop_duplicates(subset=['grid_cell', 'cluster_id'])
    
    if 'cluster_id' not in df_gem_iso.columns:
        df_gem_iso['cluster_id'] = None

    # Assign cluster_id from solar mapping only for rows where model_fuel == 'solar' and cluster_id is NULL
    solar_mask = (df_gem_iso['model_fuel'] == 'solar') & (df_gem_iso['cluster_id'].isna())
    df_gem_iso.loc[solar_mask, 'cluster_id'] = (
        df_gem_iso[solar_mask]
        .merge(df_solar_to_bus[['grid_cell', 'cluster_id']], on='grid_cell', how='left')['cluster_id_y']
        .values
    )
    # Assign cluster_id from wind onshore mapping only for rows where model_fuel == 'windon' and cluster_id is NULL
    windon_mask = (df_gem_iso['model_fuel'] == 'windon') & (df_gem_iso['cluster_id'].isna())
    df_gem_iso.loc[windon_mask, 'cluster_id'] = (
        df_gem_iso[windon_mask]
        .merge(df_won_to_bus[['grid_cell', 'cluster_id']], on='grid_cell', how='left')['cluster_id_y']
        .values
    )
    if not df_wof_to_bus.empty:
        # Assign cluster_id from wind offshore mapping only for rows where model_fuel == 'windoff' and cluster_id is NULL
        windoff_mask = (df_gem_iso['model_fuel'] == 'windoff') & (df_gem_iso['cluster_id'].isna())
        df_gem_iso.loc[windoff_mask, 'cluster_id'] = (
            df_gem_iso[windoff_mask]
            .merge(df_wof_to_bus[['grid_cell', 'cluster_id']], on='grid_cell', how='left')['cluster_id_y']
            .values
        )

    # FALLBACK: Assign nearest cluster for plants with grid_cell but no cluster_id
    # This handles grid cells that weren't included in clustering (e.g., islands, remote areas)
    for fuel_type, mapping_df, cluster_file in [
        ('solar', df_solar_to_bus, f"1_grids/output_{iso_processor.data_source}/{input_iso}/cluster_summary_solar.csv"),
        ('windon', df_won_to_bus, f"1_grids/output_{iso_processor.data_source}/{input_iso}/cluster_summary_wind_onshore.csv"),
        ('windoff', df_wof_to_bus, f"1_grids/output_{iso_processor.data_source}/{input_iso}/cluster_summary_wind_offshore.csv")
    ]:
        # Find plants that still need cluster assignment
        needs_fallback = (df_gem_iso['model_fuel'] == fuel_type) & (df_gem_iso['cluster_id'].isna()) & (df_gem_iso['grid_cell'].notna())
        
        if needs_fallback.sum() > 0 and Path(cluster_file).exists():
            print(f"   🔍 Using nearest cluster fallback for {needs_fallback.sum()} {fuel_type} plants")
            
            # Load cluster centroids
            cluster_summary = pd.read_csv(cluster_file)
            
            # Get REZoning data to look up coordinates for grid_cells
            from shared_data_loader import get_rezoning_data
            rezoning_data = get_rezoning_data(force_reload=False)
            
            if fuel_type == 'solar':
                rez_df = rezoning_data['df_rez_solar']
            elif fuel_type == 'windon':
                rez_df = rezoning_data['df_rez_wind']
            elif fuel_type == 'windoff':
                rez_df = rezoning_data['df_rez_windoff']
            
            # Filter for this country
            rez_df = rez_df[rez_df['ISO'] == input_iso].copy()
            
            # Create grid_cell → lat/lng lookup
            grid_coords = rez_df[['grid_cell', 'lat', 'lng']].drop_duplicates(subset=['grid_cell'])
            grid_coords = grid_coords.rename(columns={'lat': 'cell_lat', 'lng': 'cell_lon'})
            
            # For each plant needing fallback
            for idx in df_gem_iso[needs_fallback].index:
                grid_cell = df_gem_iso.loc[idx, 'grid_cell']
                
                # Remove wof- prefix if present
                grid_cell_clean = grid_cell.replace('wof-', '') if isinstance(grid_cell, str) else grid_cell
                
                # Look up coordinates for this grid_cell
                cell_coords = grid_coords[grid_coords['grid_cell'] == grid_cell_clean]
                
                if len(cell_coords) > 0:
                    cell_lat = cell_coords.iloc[0]['cell_lat']
                    cell_lon = cell_coords.iloc[0]['cell_lon']
                    
                    # Calculate distance to all cluster centroids
                    from scipy.spatial.distance import cdist
                    plant_coord = np.array([[cell_lat, cell_lon]])
                    cluster_coords = cluster_summary[['centroid_lat', 'centroid_lon']].values
                    distances = cdist(plant_coord, cluster_coords, metric='euclidean')[0]
                    
                    # Find nearest cluster
                    nearest_idx = np.argmin(distances)
                    nearest_cluster_id = cluster_summary.iloc[nearest_idx]['cluster_id']
                    
                    # Assign cluster_id
                    df_gem_iso.loc[idx, 'cluster_id'] = nearest_cluster_id
                    
                    print(f"      - {grid_cell} → cluster {nearest_cluster_id} (distance: {distances[nearest_idx]:.4f} degrees)")

    df_gem_iso['comm-out'] = df_gem_iso.apply(assign_commodity_single, axis=1)
    
    return df_gem_iso


def create_topology_data_csv(input_iso, buses_to_attach_thermal, buses_to_attach_hydro, buses_to_attach_storage):
    """
    Create topology data CSV for grid modeling.
    This creates the ~tfm_topins table that declares e_bus_id as output for each replicated process.
    """
    from pathlib import Path
    import pandas as pd
    from shared_data_loader import get_shared_loader
    
    topology_data = []
    
    # Load technology lists
    shared_loader = get_shared_loader("data/")
    
    # Thermal technologies
    try:
        weo_pg_techs_df = shared_loader.get_vs_mappings_sheet("weo_pg_techs")
        thermal_techs = weo_pg_techs_df[weo_pg_techs_df['_include'] == 'y']['tech'].tolist()
    except:
        thermal_techs = []
    
    # Hydro technologies  
    try:
        hydro_df = shared_loader.get_re_potentials_sheet("process")
        hydro_techs = hydro_df[hydro_df['process'].str.contains(f'_{input_iso}-', na=False)]['process'].tolist()
    except:
        hydro_techs = []
    
    # Storage technologies
    try:
        storage_techs_df = shared_loader.get_vs_mappings_sheet("storage_techs")
        storage_techs = storage_techs_df['tech'].tolist()
    except:
        storage_techs = []
    
    # Create topology entries for thermal buses
    for bus_id in buses_to_attach_thermal:
        e_bus_id = bus_id_to_commodity(bus_id, add_prefix=True)
        
        for tech in thermal_techs:
            process_name = f"{tech}_{bus_id_to_commodity(bus_id, add_prefix=False)}"
            topology_data.append({
                'region': input_iso,
                'process': process_name,
                'commodity': e_bus_id,
                'io': 'OUT'
            })
    
    # Create topology entries for hydro buses
    for bus_id in buses_to_attach_hydro:
        e_bus_id = bus_id_to_commodity(bus_id, add_prefix=True)
        
        for tech in hydro_techs:
            process_name = f"{tech}_{bus_id_to_commodity(bus_id, add_prefix=False)}"
            topology_data.append({
                'region': input_iso,
                'process': process_name,
                'commodity': e_bus_id,
                'io': 'OUT'
            })
    
    # Create topology entries for storage buses
    for bus_id in buses_to_attach_storage:
        e_bus_id = bus_id_to_commodity(bus_id, add_prefix=True)
        
        for tech in storage_techs:
            process_name = f"{tech}_{bus_id_to_commodity(bus_id, add_prefix=False)}"
            topology_data.append({
                'region': input_iso,
                'process': process_name,
                'commodity': e_bus_id,
                'io': 'OUT'
            })
    
    # Create DataFrame and save to temp CSV
    if topology_data:
        topology_df = pd.DataFrame(topology_data)
        
        # Ensure cache directory exists
        cache_dir = Path("cache")
        cache_dir.mkdir(exist_ok=True)
        
        # Save to temp CSV - for replicateinregions work
        csv_path = cache_dir / f"topology_data_{input_iso}.csv"
        topology_df.to_csv(csv_path, index=False) 

def assign_plant_coordinates(df, df_gem_country, buffer_km=1.0):
    """
    Assign latitude and longitude coordinates to plants with smart fallback logic.
    
    Args:
        df: DataFrame with plant data including gem_id, x, y columns
        df_gem_country: DataFrame with GEM data including 'GEM unit/phase ID', 'Latitude', 'Longitude'
        buffer_km: Buffer distance in kilometers for plants without GEM coordinates (default: 1.0)
    
    Returns:
        DataFrame with 'latitude' and 'longitude' columns assigned
    """
    try:
        import numpy as np
        
        # Create a copy to avoid modifying original
        df_result = df.copy()
        
        # Initialize coordinate columns
        df_result['latitude'] = None
        df_result['longitude'] = None
        
        # Try to merge with GEM country data if available
        try:
            if not df_gem_country.empty and 'GEM unit/phase ID' in df_gem_country.columns:
                df_result = pd.merge(
                    df_result,
                    df_gem_country[['GEM unit/phase ID', 'Latitude', 'Longitude']],
                    how='left',
                    left_on='gem_id',
                    right_on='GEM unit/phase ID',
                    suffixes=('', '_gem_country')
                )
                
                # Check if we have valid GEM coordinates (both latitude and longitude)
                has_gem_coords = (df_result['gem_id'].notna() & 
                                df_result['Latitude'].notna() & 
                                df_result['Longitude'].notna())
                
                # Use GEM coordinates when available
                df_result['latitude'] = df_result['Latitude'].where(has_gem_coords, df_result['y'])
                df_result['longitude'] = df_result['Longitude'].where(has_gem_coords, df_result['x'])
                
                gem_count = has_gem_coords.sum()
                print(f"   Successfully assigned {gem_count} precise GEM coordinates")
                
            else:
                print("   No GEM coordinate data available, using bus coordinates only")
                df_result['latitude'] = df_result['y']
                df_result['longitude'] = df_result['x']
                has_gem_coords = pd.Series([False] * len(df_result), index=df_result.index)
                
        except Exception as e:
            print(f"   Warning: GEM coordinate merge failed, using bus coordinates: {e}")
            df_result['latitude'] = df_result['y']
            df_result['longitude'] = df_result['x']
            has_gem_coords = pd.Series([False] * len(df_result), index=df_result.index)
        
        # For plants without GEM coordinates, distribute them around the bus location
        needs_distribution = ~has_gem_coords
        
        if needs_distribution.sum() > 0:
            try:
                # Convert buffer from km to degrees (rough approximation: 1 degree ≈ 111 km)
                buffer_degrees = buffer_km / 111.0
                
                # Group by bus_id to handle multiple plants per bus
                for bus_id, bus_group in df_result[needs_distribution].groupby('bus_id'):
                    if pd.isna(bus_id):
                        continue  # Skip plants without bus assignment
                        
                    if len(bus_group) == 1:
                        # Single plant: add random offset
                        offset_lat = np.random.uniform(-buffer_degrees, buffer_degrees)
                        offset_lon = np.random.uniform(-buffer_degrees, buffer_degrees)
                        df_result.loc[bus_group.index, 'latitude'] += offset_lat
                        df_result.loc[bus_group.index, 'longitude'] += offset_lon
                    else:
                        # Multiple plants: distribute in circle around bus
                        bus_lat = bus_group['y'].iloc[0]
                        bus_lon = bus_group['x'].iloc[0]
                        
                        if pd.isna(bus_lat) or pd.isna(bus_lon):
                            continue  # Skip if bus coordinates are invalid
                        
                        # Calculate radius based on number of plants (minimum buffer_degrees)
                        num_plants = len(bus_group)
                        radius = max(buffer_degrees, buffer_degrees * 0.5 * num_plants)  # Scale with number of plants
                        
                        # Distribute plants evenly around the circle
                        angles = np.linspace(0, 2*np.pi, num_plants, endpoint=False)
                        
                        for i, (idx, angle) in enumerate(zip(bus_group.index, angles)):
                            # Add small random variation to avoid perfect circle
                            angle_variation = np.random.uniform(-0.3, 0.3)  # ±17 degrees
                            final_angle = angle + angle_variation
                            
                            # Calculate offset from bus center
                            offset_lat = radius * np.cos(final_angle)
                            offset_lon = radius * np.sin(final_angle)
                            
                            # Apply offset
                            df_result.loc[idx, 'latitude'] = bus_lat + offset_lat
                            df_result.loc[idx, 'longitude'] = bus_lon + offset_lon
                            
                distributed_count = needs_distribution.sum()
                print(f"   Distributed {distributed_count} plants around bus locations with {buffer_km}km buffer")
                
            except Exception as e:
                print(f"   Warning: Spatial distribution failed, using direct bus coordinates: {e}")
                # Fallback to direct bus coordinates
                df_result.loc[needs_distribution, 'latitude'] = df_result.loc[needs_distribution, 'y']
                df_result.loc[needs_distribution, 'longitude'] = df_result.loc[needs_distribution, 'x']
        
        return df_result
        
    except Exception as e:
        print(f"   Error: Coordinate assignment failed completely: {e}")
        # Return original dataframe with null coordinates to prevent total failure
        df_result = df.copy()
        df_result['latitude'] = None
        df_result['longitude'] = None
        return df_result


def prepare_plants_for_visualization(df_grouped_gem, iso_processor, buses_df, df_zone_mapping, buffer_km=10.0):
    """
    Prepare plant data for grid visualization with smart coordinate assignment.
    
    Args:
        df_grouped_gem: DataFrame with grouped GEM plant data
        iso_processor: ISO processor instance
        buses_df: DataFrame with bus data (already loaded)
        df_zone_mapping: DataFrame with zone-to-bus mapping data (already loaded)
        buffer_km: Buffer distance in kilometers for plants without GEM coordinates (default: 1.0)
    
    Returns:
        DataFrame formatted for generate_enhanced_grid_svg function with Latitude, Longitude, Capacity (MW), model_fuel
    """
    
    print(f"🗺️  Preparing plant data for visualization with {buffer_km}km buffer...")
    
    # Add commodity ID to buses
    buses_df['comm_id'] = buses_df['bus_id'].apply(bus_id_to_commodity)
    
    # Prepare REZ data for visualization (add to mapping)
    def prepare_rez_comm_for_visualization(iso_processor, buses_df, df_zone_mapping):
        """
        Prepare REZ zoning data for visualization.
        Returns empty DataFrame if any errors occur to avoid breaking pipeline.
        """
        try:
            from shared_data_loader import get_rezoning_data
            rezoning_data = get_rezoning_data(force_reload=iso_processor.main.force_reload)
            df_rez_solar = rezoning_data.get('df_rez_solar')
            df_rez_wind = rezoning_data.get('df_rez_wind')
            df_rez_windoff = rezoning_data.get('df_rez_windoff')
            
            # Check if data is available
            if df_rez_solar is None or df_rez_wind is None:
                print(f"   Warning: REZ data not available for {iso_processor.input_iso}")
                return pd.DataFrame(columns=['comm_id', 'bus_id', 'x', 'y'])
            
            buses_df = buses_df.copy()
            
            # Check if zone mapping data is available
            if df_zone_mapping.empty:
                print(f"   Warning: Zone mapping data not available")
                return pd.DataFrame(columns=['comm_id', 'bus_id', 'x', 'y'])
            
            df_rez_grid_to_bus = df_zone_mapping.copy()
            
            df_rez_solar = df_rez_solar[df_rez_solar['ISO'] == iso_processor.input_iso]
            df_rez_wind = df_rez_wind[df_rez_wind['ISO'] == iso_processor.input_iso]
            if df_rez_windoff is not None:
                df_rez_windoff = df_rez_windoff[df_rez_windoff['ISO'] == iso_processor.input_iso]
            else:
                df_rez_windoff = pd.DataFrame()

            df_rez_solar = pd.merge(df_rez_solar, df_rez_grid_to_bus, how='left', on='grid_cell')
            df_rez_wind = pd.merge(df_rez_wind, df_rez_grid_to_bus, how='left', on='grid_cell')
            if not df_rez_windoff.empty:
                df_rez_windoff = pd.merge(df_rez_windoff, df_rez_grid_to_bus, how='left', on='grid_cell')
                df_rez_windoff['grid_cell'] = df_rez_windoff['grid_cell'].str.replace('wof-', '')

            df_rez_solar['comm_id'] = df_rez_solar['grid_cell'].apply(lambda x: grid_cell_to_commodity(x, 'spv','commodity'))
            df_rez_wind['comm_id'] = df_rez_wind['grid_cell'].apply(lambda x: grid_cell_to_commodity(x, 'won','commodity'))
            if not df_rez_windoff.empty:
                df_rez_windoff['comm_id'] = df_rez_windoff['grid_cell'].apply(lambda x: grid_cell_to_commodity(x, 'wof','commodity'))
            
            # Combine all REZ data with necessary columns
            rez_dataframes = [df for df in [df_rez_solar, df_rez_wind, df_rez_windoff] if not df.empty]
            if not rez_dataframes:
                print(f"   Warning: No REZ data found for {iso_processor.input_iso}")
                return pd.DataFrame(columns=['comm_id', 'bus_id', 'x', 'y'])
            
            df_rez = pd.concat(rez_dataframes)[['comm_id', 'bus_id']]
            
            # Merge with buses_df to get x, y coordinates
            df_rez = pd.merge(df_rez, buses_df[['bus_id', 'x', 'y']], how='left', on='bus_id')
            df_rez = df_rez.drop_duplicates(subset=['comm_id'], keep='first')
            return df_rez
            
        except Exception as e:
            print(f"   Warning: Could not prepare REZ data for visualization: {e}")
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=['comm_id', 'bus_id', 'x', 'y'])
    
    # Add REZ data to mapping (with error handling)
    try:
        rez_plants_df = prepare_rez_comm_for_visualization(iso_processor, buses_df, df_zone_mapping)
        mapping_df = pd.concat([buses_df, rez_plants_df])
        print(f"   REZ data added to mapping: {len(rez_plants_df)} REZ entries")
    except Exception as e:
        print(f"   Warning: REZ data preparation failed, using buses only: {e}")
        mapping_df = buses_df
    
    try:
        # Group df_grouped_gem by comm-out and model_name, sum Capacity_GW, keep only required columns
        print(f"Original df_grouped_gem length: {len(df_grouped_gem)}")
        df_gem = df_grouped_gem.groupby(['comm-out', 'model_name']).agg({
            'Capacity_GW': 'sum',
            'model_fuel': 'first'  # Take first value since it should be the same for grouped records
        }).reset_index()
        print(f"Grouped df_gem length: {len(df_gem)}")

        # Extract GEM ID from model names
        def extract_gem_id(model_name):
            try:
                import re
                match = re.search(r'(_G\d+)$', str(model_name))
                if match:
                    return match.group(1).replace('_', '').strip()
                return None
            except Exception:
                return None
        
        df_gem['gem_id'] = df_gem['model_name'].apply(extract_gem_id)
        
        # Merge with mapping data (buses + REZ) to get coordinates
        merged_df = pd.merge(
            df_gem,
            mapping_df[['comm_id', 'bus_id', 'x', 'y']],
            how='left',
            left_on='comm-out',
            right_on='comm_id',
            suffixes=('_gem', '_bus')
        )
        
        # Get GEM country data with precise coordinates
        try:
            df_gem_country = iso_processor.main.df_gem[iso_processor.main.df_gem['iso_code'] == iso_processor.input_iso]
            # df_gem_country = df_gem_country[~df_gem_country['Status'].str.lower().str.startswith(('cancelled', 'shelved', 'retired','announced'))]
            
            # Drop duplicates in GEM country data to avoid coordinate duplication issues
            df_gem_country = df_gem_country.drop_duplicates(subset=['GEM unit/phase ID'], keep='first')
            
            print(f"   GEM country data: {len(df_gem_country)} records available for coordinate lookup")
        except Exception as e:
            print(f"   Warning: Could not load GEM country data for coordinates: {e}")
            # Create empty dataframe with required columns
            df_gem_country = pd.DataFrame(columns=['GEM unit/phase ID', 'Latitude', 'Longitude'])
        
        # Apply smart coordinate assignment (with error handling inside the function)
        merged_df = assign_plant_coordinates(merged_df, df_gem_country, buffer_km)
        
    except Exception as e:
        print(f"   Warning: Data preparation failed, using simplified approach: {e}")
        # Fallback: create a simple plants dataframe
        merged_df = df_grouped_gem.copy()
        merged_df['Latitude'] = None
        merged_df['Longitude'] = None
    
    try:
        # Create plants_df in the format expected by generate_enhanced_grid_svg
        # First drop the original GEM Latitude/Longitude columns to avoid duplicates
        merged_df_clean = merged_df.drop(['Latitude', 'Longitude'], axis=1, errors='ignore')
        
        # Now rename our processed coordinates to the expected format
        plants_df = merged_df_clean.rename(columns={
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'Capacity_GW': 'Capacity (MW)'  # Convert GW to MW
        }).copy()
        
        # Convert capacity from GW to MW
        if 'Capacity (MW)' in plants_df.columns:
            plants_df['Capacity (MW)'] = plants_df['Capacity (MW)'] * 1000
        else:
            print("   Warning: No capacity data found for plants")
            plants_df['Capacity (MW)'] = 0
        
        # Remove temporary columns we don't need for visualization
        plants_df = plants_df.drop(['gem_id', 'GEM unit/phase ID', 'x', 'y'], axis=1, errors='ignore')
        plants_df['is_new_tech'] = [True if model_name.lower().startswith('en_') else False for model_name in plants_df['model_name']]
        # Ensure we have the minimum required columns
        required_columns = ['Latitude', 'Longitude', 'Capacity (MW)', 'model_fuel']
        for col in required_columns:
            if col not in plants_df.columns:
                print(f"   Warning: Missing required column '{col}', adding placeholder")
                if col in ['Latitude', 'Longitude']:
                    plants_df[col] = None
                elif col == 'Capacity (MW)':
                    plants_df[col] = 0
                elif col == 'model_fuel':
                    plants_df[col] = 'unknown'
        
        # Report statistics
        total_plants = len(plants_df)
        valid_coords = plants_df['Latitude'].notna() & plants_df['Longitude'].notna()
        valid_coord_count = valid_coords.sum()
        
        # Calculate GEM vs bus statistics if we have the merged data
        gem_coord_count = 0
        bus_coord_count = 0
        
        if 'gem_id' in merged_df.columns and 'latitude' in merged_df.columns:
            has_gem_coords = merged_df['gem_id'].notna() & merged_df['latitude'].notna() & merged_df['longitude'].notna()
            gem_coord_count = has_gem_coords.sum()
            bus_coord_count = total_plants - gem_coord_count
        else:
            bus_coord_count = valid_coord_count
        
        print(f"   Processed {total_plants} plants:")
        print(f"   {gem_coord_count} plants with precise GEM coordinates")
        print(f"   {bus_coord_count} plants with bus coordinates + {buffer_km}km buffer")
        print(f"   {valid_coord_count} plants have valid coordinates for visualization")
        
        return plants_df
        
    except Exception as e:
        print(f"   Error: Final data formatting failed: {e}")
        # Return minimal dataframe to prevent total failure
        fallback_df = pd.DataFrame({
            'Latitude': [None],
            'Longitude': [None], 
            'Capacity (MW)': [0],
            'model_fuel': ['unknown']
        })
        print(f"   Returning fallback dataframe with {len(fallback_df)} record")
        return fallback_df


def create_enhanced_grid_svg(iso_processor, df_grouped_gem, buffer_km=1.0, output_file=None):
    """
    Create enhanced grid SVG with smart plant coordinate assignment.
    Only creates visualization if grid_modeling is enabled.
    
    Args:
        iso_processor: ISO processor instance
        df_grouped_gem: DataFrame with grouped GEM plant data
        buffer_km: Buffer distance in kilometers for plants without GEM coordinates (default: 1.0)
        output_file: Optional custom output file path (if None, uses VEDA models directory structure)
    """
    # Only create visualization if grid modeling is enabled
    if not iso_processor.grid_modeling:
        print("   Grid visualization skipped (grid_modeling not enabled)")
        return
    
    try:
        # Import required modules
        import sys
        sys.path.append('1_grids')
        from extract_country_pypsa_network_clustered import generate_enhanced_grid_svg
        from veda_model_creator import models_dir
        
        # Load grid data once
        print(f"  Loading grid data for {iso_processor.input_iso}...")
        buses_df = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/{iso_processor.input_iso}_clustered_buses.csv")
        lines_df = pd.read_csv(f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/{iso_processor.input_iso}_clustered_lines.csv")
        
        # Load zone mapping data once (skip for synthetic grids where clusters ARE buses)
        if iso_processor.data_source.startswith('syn_'):
            print(f"   Synthetic grid mode: skipping zone_bus_mapping (renewable clusters are direct buses)")
            df_zone_mapping = pd.DataFrame(columns=['grid_cell', 'bus_id'])
        else:
            zone_mapping_file = f"1_grids/output_{iso_processor.data_source}/{iso_processor.input_iso}/{iso_processor.input_iso}_zone_bus_mapping.csv"
            try:
                if Path(zone_mapping_file).exists():
                    df_zone_mapping = pd.read_csv(zone_mapping_file)
                    print(f"   Loaded zone mapping: {len(df_zone_mapping)} zone-bus mappings")
                else:
                    print(f"   Warning: Zone mapping file not found: {zone_mapping_file}")
                    df_zone_mapping = pd.DataFrame(columns=['grid_cell', 'bus_id'])
            except Exception as e:
                print(f"   Warning: Could not load zone mapping file: {e}")
                df_zone_mapping = pd.DataFrame(columns=['grid_cell', 'bus_id'])
        
        # Prepare plant data with smart coordinates (passing pre-loaded DataFrames)
        plants_df = prepare_plants_for_visualization(df_grouped_gem, iso_processor, buses_df, df_zone_mapping, buffer_km)
        
        # Construct output file path using VEDA models directory structure (same as other exports)
        if output_file is None:
            # Use imported models_dir from veda_model_creator
            if iso_processor.grid_modeling and hasattr(iso_processor, 'data_source') and iso_processor.data_source:
                folder_suffix = f"_grids_{iso_processor.data_source}"
            elif iso_processor.grid_modeling:
                folder_suffix = "_grids"
            else:
                folder_suffix = ""
            dest_folder = models_dir / f"VerveStacks_{iso_processor.input_iso}{folder_suffix}"
            
            # Create grid_analysis subdirectory for visualization files
            grid_analysis_dir = dest_folder / "grid_analysis"
            grid_analysis_dir.mkdir(parents=True, exist_ok=True)
            
            # Construct filename
            output_file = grid_analysis_dir / f"{iso_processor.input_iso}_network_visualization.svg"
            
            print(f"   Exporting to VEDA models directory: {output_file}")
        
        # Generate the visualization
        generate_enhanced_grid_svg(
            iso_processor.input_iso, 
            buses_df, 
            lines_df, 
            plants_df, 
            None,  # zones_df not used
            iso_processor=None,  # Don't let function prepare data
            output_file=str(output_file)
        )
        
        print("Enhanced grid SVG generated successfully")
        
    except Exception as e:
        print(f"Could not generate enhanced grid SVG: {e}")
        import traceback
        traceback.print_exc()

    
    