import shutil
import os
import pandas as pd
import duckdb
import xlwings as xw
from pathlib import Path
import subprocess
import logging
import sys
from datetime import datetime
from time_slice_processor import process_time_slices
from shared_data_loader import get_shared_loader
from excel_manager import excel_manager

from spatial_utils import bus_id_to_commodity, cluster_id_to_commodity

# Add scenario_drivers to path for ReadmeGenerator import
scenario_drivers_path = Path(__file__).parent / "scenario_drivers"
if str(scenario_drivers_path) not in sys.path:
    sys.path.insert(0, str(scenario_drivers_path))

from scenario_drivers.readme_generator import ReadmeGenerator

models_dir = Path("C:/Veda/Veda/Veda_models/vervestacks_models")

def run_git_command(command, cwd):
    """Run a git command and return the result."""
    try:
        # Try with shell=True first (works with PATH)
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace', 
            check=True
        )
        return result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        # Git not found in PATH, try common Windows Git locations
        git_paths = [
            "C:\\Program Files\\Git\\bin\\git.exe",
            "C:\\Program Files (x86)\\Git\\bin\\git.exe",
            "C:\\Git\\bin\\git.exe"
        ]
        
        for git_path in git_paths:
            if Path(git_path).exists():
                try:
                    git_command = command.replace("git ", f'"{git_path}" ', 1)
                    result = subprocess.run(
                        git_command, 
                        shell=True, 
                        cwd=cwd, 
                        capture_output=True, 
                        text=True,
                        encoding='utf-8',
                        errors='replace', 
                        check=True
                    )
                    return result.stdout.strip(), result.stderr.strip()
                except subprocess.CalledProcessError as e:
                    continue
        
        # If no Git found, raise the original error
        raise FileNotFoundError("Git command not found in PATH or common locations")
    except subprocess.CalledProcessError as e:
        logging.warning(f"Git command failed: {e}")
        raise e


def clean_create_iso_branch(iso_code, repo_path, commit_message=None, grid_modeling=False, data_source=None):
    """Clean approach: Create/switch to ISO branch and empty the folder completely."""
    # Create branch name with _grids_<data_source> suffix if grid modeling is enabled
    if grid_modeling and data_source:
        branch_name = f"{iso_code}_grids_{data_source}"
    elif grid_modeling:
        branch_name = f"{iso_code}_grids"
    else:
        branch_name = iso_code
    
    if not commit_message:
        commit_message = f"Updated {branch_name} model - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    print(f"🔄 Setting up clean branch '{branch_name}'...")
    
    try:
        # 1. Create/switch to ISO branch
        stdout, stderr = run_git_command(f"git branch --list {branch_name}", repo_path)
        if not stdout or branch_name not in stdout:
            # Create branch from main/master
            print(f"  → Creating new branch '{branch_name}' from main")
            run_git_command(f"git checkout main", repo_path)
            run_git_command(f"git checkout -b {branch_name}", repo_path)
        else:
            print(f"  → Switching to existing branch '{branch_name}'")
            run_git_command(f"git checkout {branch_name}", repo_path)
        
        # 2. Empty the destination folder completely (except .git)
        print(f"  → Emptying destination folder...")
        files_to_delete = []
        dirs_to_delete = []
        
        for item in repo_path.iterdir():
            if item.name != ".git" and item.name != ".gitattributes":
                if item.is_dir():
                    dirs_to_delete.append(item)
                else:
                    files_to_delete.append(item)
        
        # Delete files first
        for file_path in files_to_delete:
            try:
                file_path.unlink()
            except PermissionError as e:
                print(f"    ⚠️  Could not delete {file_path.name}: {e}")
                print(f"    File may be locked by Excel or another process")
                # Try to continue anyway
        
        # Delete directories
        for dir_path in dirs_to_delete:
            try:
                shutil.rmtree(dir_path)
            except (PermissionError, OSError) as e:
                print(f"    ⚠️  Could not delete directory {dir_path.name}: {e}")
                print(f"    Directory may contain locked files")
                # Try to continue anyway
        
        print(f"✅ Created clean model folder: {repo_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to setup clean branch: {e}")
        print(f"    Git error: {e.stderr if hasattr(e, 'stderr') else 'Unknown git error'}")
        return False
    except Exception as e:
        print(f"❌ Failed to setup clean branch: {e}")
        return False


def commit_iso_model(iso_code, repo_path, commit_message=None, grid_modeling=False, data_source=None):
    """Commit the ISO model to its branch and push to remote."""
    # Create branch name with _grids_<data_source> suffix if grid modeling is enabled
    if grid_modeling and data_source:
        branch_name = f"{iso_code}_grids_{data_source}"
    elif grid_modeling:
        branch_name = f"{iso_code}_grids"
    else:
        branch_name = iso_code
    
    if not commit_message:
        commit_message = f"Updated {branch_name} model - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    try:
        print(f"  → Committing {branch_name} model...")
        
        # Add everything in the repo (should only be the one model + .gitattributes)
        run_git_command("git add .", repo_path)
        
        # Commit if there are changes
        stdout, stderr = run_git_command("git status --porcelain", repo_path)
        if stdout:
            # Commit the changes
            run_git_command(f'git commit -m "{commit_message}"', repo_path)
            print(f"✅ Committed {branch_name} model to branch '{branch_name}'")
            
            # Try to push to remote
            print(f"  → Publishing {branch_name} branch to remote...")
            try:
                # First try standard push
                run_git_command(f"git push -u origin {branch_name}", repo_path)
                print(f"🚀 Published {branch_name} branch to remote repository!")
                return True
            except:
                # If standard push fails, try with explicit remote setup
                try:
                    run_git_command(f"git push --set-upstream origin {branch_name}", repo_path)
                    print(f"🚀 Published {branch_name} branch to remote repository!")
                    return True
                except:
                    print(f"⚠️  Branch committed locally but push to remote failed.")
                    print(f"   You can manually push with: git push -u origin {iso_code}")
                    return True  # Still return True since local commit succeeded
        else:
            print(f"  → No changes to commit for {iso_code}")
            return True
    except Exception as e:
        print(f"❌ Commit failed: {e}")
        return False


def copy_vs_iso_template(input_iso, output_dir, auto_commit=True, processing_params=None, grid_modeling=False, data_source=None):
    """
    Copy the VerveStacks ISO template to create a new model folder.
    
    Args:
        input_iso: ISO country code (e.g., 'CHE', 'USA')
        output_dir: Output directory path
        auto_commit: Whether to perform git operations
        processing_params: Processing parameters for documentation
        grid_modeling: If True, appends '_grids_<data_source>' to the model folder name
        data_source: Data source identifier (e.g., 'kan', 'eur', 'cit')
        
    Returns:
        Path to the created model folder
    """
    src_folder = "assumptions/VerveStacks_ISO_template"
    
    # Create vervestacks_models subdirectory in Veda models directory
    # models_dir = Path("C:/Veda/Veda/Veda_models/vervestacks_models")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if this is a git repository
    is_git_repo = (models_dir / ".git").exists()
    
    # Create model folder path with data_source suffix
    if grid_modeling and data_source:
        folder_suffix = f"_grids_{data_source}"
    elif grid_modeling:
        folder_suffix = "_grids"
    else:
        folder_suffix = ""
    dest_folder = models_dir / f"VerveStacks_{input_iso}{folder_suffix}"
    
    if auto_commit and is_git_repo:
        # CLEAN APPROACH: Setup clean ISO branch first
        if clean_create_iso_branch(input_iso, models_dir, grid_modeling=grid_modeling, data_source=data_source):
            # 3. Copy template fresh into the clean branch
            shutil.copytree(src_folder, dest_folder)
            print(f"✅ Created clean model folder: {dest_folder}")
            
            
        else:
            print("❌ Failed to setup clean branch, falling back to regular copy")
            # Fallback to regular copy
            if dest_folder.exists():
                shutil.rmtree(dest_folder)
            shutil.copytree(src_folder, dest_folder)
    else:
        # Regular copy (no git or auto_commit=False)
        if dest_folder.exists():
            shutil.rmtree(dest_folder)
        shutil.copytree(src_folder, dest_folder)
        print(f"Created model folder: {dest_folder}")
    
    # Create source_data subfolder and copy VerveStacks_{ISO}.xlsx
    create_source_data_folder(dest_folder, input_iso, output_dir)
    
    return dest_folder


def create_source_data_folder(dest_folder, input_iso, output_dir):
    """Create source_data subfolder and copy VerveStacks_{ISO}.xlsx file."""
    # Create source_data subfolder
    source_data_folder = dest_folder / "source_data"
    source_data_folder.mkdir(exist_ok=True)
    
    # Source file path (from output directory)
    source_file = Path(output_dir) / f"VerveStacks_{input_iso}.xlsx"
    
    # Destination file path
    dest_file = source_data_folder / f"VerveStacks_{input_iso}.xlsx"
    
    # Copy the file if it exists
    if source_file.exists():
        shutil.copy2(source_file, dest_file)
        print(f"✅ Copied source data file to: {dest_file}")
    else:
        print(f"⚠️  Warning: Source data file not found: {source_file}")


def calculate_ccs_retrofit_capacity(ccs_retrofits_df, df_grouped_gem):
    """Calculate total CCS retrofit capacity by fuel type."""
    if ccs_retrofits_df is None or ccs_retrofits_df.empty:
        print("Info: No CCS retrofits found - returning 0.0 GW for both coal and gas")
        return {
            'coal_ccs_retrofit_capacity_gw': '0.0 GW',
            'gas_ccs_retrofit_capacity_gw': '0.0 GW'
        }
    
    try:
        print(f"Info: CCS retrofits DataFrame has {len(ccs_retrofits_df)} rows")
        print(f"Info: CCS retrofits columns: {list(ccs_retrofits_df.columns)}")
        
        # Check if required columns exist
        if 'model_fuel' not in ccs_retrofits_df.columns:
            print(f"Warning: CCS retrofits DataFrame missing 'model_fuel' column. Available columns: {list(ccs_retrofits_df.columns)}")
            return {
                'coal_ccs_retrofit_capacity_gw': '0.0 GW',
                'gas_ccs_retrofit_capacity_gw': '0.0 GW'
            }
        
        if 'plant_old' not in ccs_retrofits_df.columns:
            print(f"Warning: CCS retrofits DataFrame missing 'plant_old' column. Available columns: {list(ccs_retrofits_df.columns)}")
            return {
                'coal_ccs_retrofit_capacity_gw': '0.0 GW',
                'gas_ccs_retrofit_capacity_gw': '0.0 GW'
            }
        
        # Check what fuels are available in CCS retrofits
        available_fuels = ccs_retrofits_df['model_fuel'].unique()
        print(f"Info: CCS retrofits available fuels: {available_fuels}")
        
        # Merge CCS retrofits with original plant data to get capacities
        ccs_with_capacity = pd.merge(
            ccs_retrofits_df, 
            df_grouped_gem[['model_name', 'Capacity_GW', 'model_fuel']], 
            left_on='plant_old', 
            right_on='model_name', 
            how='left'
        )
        
        # print(f"Info: After merge, CCS with capacity has {len(ccs_with_capacity)} rows")
        # print(f"Info: Columns after merge: {list(ccs_with_capacity.columns)}")
        
        # Check if AF (capacity factor) column exists
        if 'AF' not in ccs_with_capacity.columns:
            print(f"Warning: CCS retrofits DataFrame missing 'AF' (capacity factor) column. Available columns: {list(ccs_with_capacity.columns)}")
            return {
                'coal_ccs_retrofit_capacity_gw': 'TBD',
                'gas_ccs_retrofit_capacity_gw': 'TBD'
            }
        
        # Calculate available capacity after capacity penalty: host_plant_capacity * capacity_factor
        ccs_with_capacity['available_capacity_gw'] = ccs_with_capacity['Capacity_GW'] * ccs_with_capacity['AF']
        
        # Sum both original and available capacity by fuel type (use model_fuel from CCS retrofits)
        # Handle potential column name conflicts from merge
        fuel_col = 'model_fuel_x' if 'model_fuel_x' in ccs_with_capacity.columns else 'model_fuel'
        coal_original_capacity = ccs_with_capacity[ccs_with_capacity[fuel_col] == 'coal']['Capacity_GW'].sum()
        coal_available_capacity = ccs_with_capacity[ccs_with_capacity[fuel_col] == 'coal']['available_capacity_gw'].sum()
        gas_original_capacity = ccs_with_capacity[ccs_with_capacity[fuel_col] == 'gas']['Capacity_GW'].sum()
        gas_available_capacity = ccs_with_capacity[ccs_with_capacity[fuel_col] == 'gas']['available_capacity_gw'].sum()
        
        print(f"Info: Coal CCS - Original: {coal_original_capacity} GW, After penalty: {coal_available_capacity} GW")
        print(f"Info: Gas CCS - Original: {gas_original_capacity} GW, After penalty: {gas_available_capacity} GW")
        
        # Import smart formatting function
        from data_utils import smart_format_number
        
        return {
            'coal_ccs_retrofit_capacity_gw': f"{smart_format_number(coal_original_capacity)} GW",
            'coal_ccs_retrofit_capacity_after_penalty_gw': f"{smart_format_number(coal_available_capacity)} GW",
            'gas_ccs_retrofit_capacity_gw': f"{smart_format_number(gas_original_capacity)} GW",
            'gas_ccs_retrofit_capacity_after_penalty_gw': f"{smart_format_number(gas_available_capacity)} GW"
        }
    except Exception as e:
        print(f"Warning: Could not calculate CCS retrofit capacity: {e}")
        return {
            'coal_ccs_retrofit_capacity_gw': 'TBD',
            'coal_ccs_retrofit_capacity_after_penalty_gw': 'TBD',
            'gas_ccs_retrofit_capacity_gw': 'TBD',
            'gas_ccs_retrofit_capacity_after_penalty_gw': 'TBD'
        }


def calculate_processing_statistics(df_grouped_gem, iso_processor, ccs_retrofits_df=None):
    """Calculate processing statistics from the GEM data for documentation."""
    try:
        # Get fuel-specific capacity thresholds
        df_fuel_thresholds = getattr(iso_processor, 'df_fuel_thresholds', pd.DataFrame())
        
        # Initialize capacity_threshold for use in calculations
        capacity_threshold = getattr(iso_processor, 'capacity_threshold', 100)
        
        if not df_fuel_thresholds.empty:
            # Separate hydro power from pumped storage before splitting by time
            # Create a copy to avoid modifying the original dataframe
            df_processed = df_grouped_gem.copy()
            
            # Identify pumped storage plants (those with 'hydro_ps' in model_name)
            pumped_storage_mask = df_processed['model_name'].str.contains('_hydro_ps', na=False)
            
            # Create new fuel category for pumped storage
            df_processed.loc[pumped_storage_mask, 'model_fuel'] = 'hydro_ps'
            
            # Split data by existing (ep_) vs future projects (en_)
            df_existing = df_processed[df_processed['model_name'].str.startswith('ep_')]
            df_future = df_processed[df_processed['model_name'].str.startswith('en_')]
            
            # Check if there's any mothballed capacity to determine table structure
            has_mothballed = (df_existing['model_name'].str.startswith('ep_m_')).any()
            
            # Create existing capacity table
            if has_mothballed:
                # Create fuel-specific threshold table with mothballed capacity column
                existing_capacity_table = "| **Fuel Type** | **Threshold** | **Plants Above Threshold** | **Active Capacity** | **Mothballed Capacity** | **Wtd Avg Efficiency** |\n"
                existing_capacity_table += "|---------------|---------------|----------------------------|--------------------|--------------------------|-----------------|\n"
            else:
                # Create fuel-specific threshold table without mothballed capacity column
                existing_capacity_table = "| **Fuel Type** | **Threshold** | **Plants Above Threshold** | **Active Capacity** | **Wtd Avg Efficiency** |\n"
                existing_capacity_table += "|---------------|---------------|----------------------------|--------------------|-----------------|\n"
            
            # Create future projects table (no mothballed capacity expected)
            future_projects_table = "| **Fuel Type** | **Threshold** | **Plants Above Threshold** | **Total Capacity** | **Wtd Avg Efficiency** |\n"
            future_projects_table += "|---------------|---------------|----------------------------|--------------------|-----------------|\n"
            
            # Import smart formatting function
            from data_utils import smart_format_number
            
            # Add hydro_ps to the fuel thresholds if hydro exists and there are pumped storage plants
            df_fuel_thresholds_extended = df_fuel_thresholds.copy()
            if 'hydro' in df_fuel_thresholds_extended['model_fuel'].values:
                # Check if there are any pumped storage plants
                pumped_storage_plants = df_processed[df_processed['model_fuel'] == 'hydro_ps']
                if not pumped_storage_plants.empty:
                    # Add hydro_ps with the same threshold as hydro
                    hydro_threshold = df_fuel_thresholds_extended[df_fuel_thresholds_extended['model_fuel'] == 'hydro']['capacity_threshold'].iloc[0]
                    new_row = pd.DataFrame({'model_fuel': ['hydro_ps'], 'capacity_threshold': [hydro_threshold]})
                    df_fuel_thresholds_extended = pd.concat([df_fuel_thresholds_extended, new_row], ignore_index=True)
                    print(f"   🔋 Added pumped storage threshold: {hydro_threshold} MW")
            
            for _, row in df_fuel_thresholds_extended.iterrows():
                fuel = row['model_fuel']
                threshold = row['capacity_threshold']
                
                # Add emoji for visual appeal
                fuel_emoji = {
                    'coal': '⚫',
                    'gas': '🔥', 
                    'oil': '🛢️',
                    'nuclear': '⚛️',
                    'hydro': '💧',
                    'hydro_ps': '🔋',  # Pumped storage gets battery emoji
                    'solar': '☀️',
                    'windon': '💨',
                    'windoff': '🌊',
                    'bioenergy': '🌱',
                    'geothermal': '🌋'
                }.get(fuel, '⚡')
                
                # Format threshold display (use "—" for zero thresholds)
                threshold_text = "—" if threshold == 0 else f"{smart_format_number(threshold)} MW"
                
                # Calculate separate weighted average efficiencies for existing vs future plants
                def calculate_weighted_avg_efficiency(plants_df):
                    if plants_df.empty or 'efficiency' not in plants_df.columns:
                        return "—"
                    # Filter out plants with missing or zero efficiency
                    valid_plants = plants_df[(plants_df['efficiency'].notna()) & (plants_df['efficiency'] > 0)]
                    if valid_plants.empty:
                        return "—"
                    # Calculate capacity-weighted average efficiency
                    total_capacity = valid_plants['Capacity_GW'].sum()
                    if total_capacity == 0:
                        return "—"
                    weighted_eff = (valid_plants['efficiency'] * valid_plants['Capacity_GW']).sum() / total_capacity
                    return f"{smart_format_number(weighted_eff * 100)}%"
                
                # Map fuel names for display (separate hydro power from pumped storage)
                fuel_display_name = {
                    'hydro': 'Hydro Power',
                    'hydro_ps': 'Pumped Storage'
                }.get(fuel, fuel.title())
                
                # === EXISTING CAPACITY TABLE ===
                existing_fuel_plants = df_existing[df_existing['model_fuel'] == fuel]
                existing_plants_above = len(existing_fuel_plants[existing_fuel_plants['Capacity_GW'] * 1000 >= threshold])
                total_existing_plants = len(existing_fuel_plants)
                
                if total_existing_plants > 0:
                    # Calculate active capacity (exclude mothballed plants)
                    active_fuel_plants = existing_fuel_plants[~existing_fuel_plants['model_name'].str.startswith('ep_m_')]
                    active_fuel_capacity_gw = active_fuel_plants['Capacity_GW'].sum()
                    
                    # Calculate mothballed capacity for this fuel type
                    mothballed_plants = existing_fuel_plants[existing_fuel_plants['model_name'].str.startswith('ep_m_')]
                    mothballed_capacity_gw = mothballed_plants['Capacity_GW'].sum() if not mothballed_plants.empty else 0
                    
                    # Calculate weighted average efficiency for existing plants only
                    existing_fuel_efficiency = calculate_weighted_avg_efficiency(existing_fuel_plants)
                    
                    if has_mothballed:
                        mothballed_text = f"{smart_format_number(mothballed_capacity_gw)} GW" if mothballed_capacity_gw > 0 else "—"
                        existing_capacity_table += f"| {fuel_emoji} **{fuel_display_name}** | {threshold_text} | {existing_plants_above}/{total_existing_plants} plants | {smart_format_number(active_fuel_capacity_gw)} GW | {mothballed_text} | {existing_fuel_efficiency} |\n"
                    else:
                        existing_capacity_table += f"| {fuel_emoji} **{fuel_display_name}** | {threshold_text} | {existing_plants_above}/{total_existing_plants} plants | {smart_format_number(active_fuel_capacity_gw)} GW | {existing_fuel_efficiency} |\n"
                
                # === FUTURE PROJECTS TABLE ===
                future_fuel_plants = df_future[df_future['model_fuel'] == fuel]
                future_plants_above = len(future_fuel_plants[future_fuel_plants['Capacity_GW'] * 1000 >= threshold])
                total_future_plants = len(future_fuel_plants)
                
                if total_future_plants > 0:
                    total_future_capacity_gw = future_fuel_plants['Capacity_GW'].sum()
                    # Calculate weighted average efficiency for future plants only
                    future_fuel_efficiency = calculate_weighted_avg_efficiency(future_fuel_plants)
                    future_projects_table += f"| {fuel_emoji} **{fuel_display_name}** | {threshold_text} | {future_plants_above}/{total_future_plants} plants | {smart_format_number(total_future_capacity_gw)} GW | {future_fuel_efficiency} |\n"
            
            # Combine both tables with headers
            capacity_threshold_summary = f"### Existing Capacity\n\n{existing_capacity_table}\n\n### Future Projects (offered for endogenous selection)\n\n{future_projects_table}"
        else:
            # Fallback to global threshold
            has_mothballed = (df_grouped_gem['model_name'].str.startswith('ep_m_')).any()
            plants_above_global = len(df_grouped_gem[df_grouped_gem['Capacity_GW'] * 1000 >= capacity_threshold])
            total_plants = len(df_grouped_gem)
            total_capacity_all = df_grouped_gem['Capacity_GW'].sum()
            
            # Format threshold display for fallback case
            from data_utils import smart_format_number
            threshold_text = "—" if capacity_threshold == 0 else f"{smart_format_number(capacity_threshold)} MW"
            
            if has_mothballed:
                # Calculate active and mothballed capacity across all fuels
                mothballed_plants_all = df_grouped_gem[df_grouped_gem['model_name'].str.startswith('ep_m_')]
                total_mothballed_capacity = mothballed_plants_all['Capacity_GW'].sum()
                active_plants_all = df_grouped_gem[~df_grouped_gem['model_name'].str.startswith('ep_m_')]
                total_active_capacity = active_plants_all['Capacity_GW'].sum()
                # Import smart formatting function for fallback case
                from data_utils import smart_format_number
                mothballed_text = f"{smart_format_number(total_mothballed_capacity)} GW" if total_mothballed_capacity > 0 else "—"
                capacity_threshold_summary = f"| **Fuel Type** | **Threshold** | **Plants Above Threshold** | **Active Capacity** | **Mothballed Capacity** | **Wtd Avg Eff** |\n|---------------|---------------|----------------------------|--------------------|--------------------------|-----------------|\n| ⚡ **All Fuels** | {threshold_text} | {plants_above_global}/{total_plants} plants | {smart_format_number(total_active_capacity)} GW | {mothballed_text} | — |"
            else:
                # When no mothballed plants exist, calculate active capacity (same as total)
                from data_utils import smart_format_number
                active_plants_all = df_grouped_gem[~df_grouped_gem['model_name'].str.startswith('ep_m_')]
                total_active_capacity = active_plants_all['Capacity_GW'].sum()
                capacity_threshold_summary = f"| **Fuel Type** | **Threshold** | **Plants Above Threshold** | **Active Capacity** | **Wtd Avg Eff** |\n|---------------|---------------|----------------------------|--------------------|-----------------|\n| ⚡ **All Fuels** | {threshold_text} | {plants_above_global}/{total_plants} plants | {smart_format_number(total_active_capacity)} GW | — |"
        
        # Calculate total capacity from GEM data (note: column is 'Capacity_GW')
        total_capacity_gw = df_grouped_gem['Capacity_GW'].sum()
        
        # Count plants above threshold using fuel-specific thresholds
        if not df_fuel_thresholds.empty:
            # Merge with fuel thresholds to get threshold for each plant
            df_with_thresholds = df_grouped_gem.merge(
                df_fuel_thresholds, 
                on='model_fuel', 
                how='left'
            )
            # Use fuel-specific threshold, fallback to global if not available
            df_with_thresholds['effective_threshold'] = df_with_thresholds['capacity_threshold'].fillna(
                getattr(iso_processor, 'capacity_threshold', 100)
            )
            # Count plants above their fuel-specific threshold
            plants_above_threshold = len(df_with_thresholds[
                df_with_thresholds['Capacity_GW'] >= df_with_thresholds['effective_threshold'] / 1000
            ])
        # Calculate capacity above threshold
            capacity_above_threshold = df_with_thresholds[
                df_with_thresholds['Capacity_GW'] >= df_with_thresholds['effective_threshold'] / 1000
            ]['Capacity_GW'].sum()
        else:
            # Fallback to global threshold
            capacity_threshold = getattr(iso_processor, 'capacity_threshold', 100)
            plants_above_threshold = len(df_grouped_gem[df_grouped_gem['Capacity_GW'] >= capacity_threshold / 1000])
        capacity_above_threshold = df_grouped_gem[df_grouped_gem['Capacity_GW'] >= capacity_threshold / 1000]['Capacity_GW'].sum()
        
        # Calculate GEM coverage percentage
        if total_capacity_gw > 0:
            gem_coverage_pct = round((capacity_above_threshold / total_capacity_gw) * 100, 1)
        else:
            gem_coverage_pct = 0.0
        
        # Estimate missing capacity (capacity below threshold)
        missing_capacity_gw = round(total_capacity_gw - capacity_above_threshold, 1)
        
        # Count total tracked plants
        tracked_plants_count = len(df_grouped_gem)
        
        # Count plants that are individually tracked (above threshold)
        individual_plants = len(df_grouped_gem[df_grouped_gem['Capacity_GW'] >= capacity_threshold / 1000])
        
        # Calculate missing capacity by technology and source
        missing_capacity_details = calculate_missing_capacity_details(df_grouped_gem)
        missing_capacity_summary = format_missing_capacity_details(missing_capacity_details)
        
        # Calculate CCS retrofit capacity by fuel type
        ccs_capacity_stats = calculate_ccs_retrofit_capacity(ccs_retrofits_df, df_grouped_gem)
        
        # Create summary metrics table if available
        summary_metrics_table = ""
        if hasattr(iso_processor, 'summary_metrics'):
            metrics = iso_processor.summary_metrics
            summary_metrics_table = f"""| **Total Capacity** | **Total Generation** | **CO2 Emissions** | **Calibration to EMBER** |
|--------------|---------------|------------|--------------------------|
| {metrics['total_capacity_gw']} GW | {metrics['total_generation_twh']} TWh | {metrics['model_co2_mt']} Mt | {metrics['calibration_pct']}% |"""
        
        # Calculate hydro dependency percentage from summary metrics
        hydro_share_percent = 0.0
        if hasattr(iso_processor, 'summary_metrics') and iso_processor.summary_metrics:
            metrics = iso_processor.summary_metrics
            total_gen = float(metrics.get('total_generation_twh', '0').replace(' TWh', ''))
            
            # Try to get hydro generation from calibration data
            try:
                from existing_stock_processor import calculate_irena_utilization
                df_irena_util = calculate_irena_utilization(iso_processor)
                hydro_gen = df_irena_util[
                    (df_irena_util['model_fuel'] == 'hydro') & 
                    (df_irena_util['year'] == 2022)
                ]['Generation_TWh'].sum()
                
                if total_gen > 0 and hydro_gen > 0:
                    hydro_share_percent = (hydro_gen / total_gen) * 100
            except Exception as e:
                print(f"⚠️  Could not calculate hydro dependency: {e}")
                hydro_share_percent = 0.0
        
        # Apply smart formatting to data processing notes
        from data_utils import smart_format_number
        
        return {
            'capacity_threshold_table': capacity_threshold_summary,
            'summary_metrics_table': summary_metrics_table,
            'gem_coverage_pct': f"{smart_format_number(gem_coverage_pct)}%",
            'missing_capacity_gw': f"{smart_format_number(missing_capacity_gw)} GW",
            'tracked_plants_count': smart_format_number(tracked_plants_count),
            'total_capacity_gw': f"{smart_format_number(total_capacity_gw)} GW",
            'plants_above_threshold': smart_format_number(individual_plants),
            'missing_capacity_summary': missing_capacity_summary,
            'hydro_share_percent': f"{smart_format_number(hydro_share_percent)}",
            **ccs_capacity_stats
        }
    except Exception as e:
        print(f"Warning: Could not calculate processing statistics: {e}")
        print(f"Available columns: {list(df_grouped_gem.columns) if hasattr(df_grouped_gem, 'columns') else 'No columns'}")
        return {
            'capacity_threshold_table': 'TBD',
            'summary_metrics_table': '',
            'gem_coverage_pct': 'TBD',
            'missing_capacity_gw': 'TBD',
            'tracked_plants_count': 'TBD',
            'total_capacity_gw': 'TBD',
            'plants_above_threshold': 'TBD',
            'missing_capacity_summary': 'TBD',
            'hydro_share_percent': '0',
            'coal_ccs_retrofit_capacity_gw': 'TBD',
            'gas_ccs_retrofit_capacity_gw': 'TBD'
        }


def format_missing_capacity_details(missing_capacity_details):
    """Format missing capacity details for display in README.md."""
    if not missing_capacity_details:
        return "- **No missing capacity added** - All capacity covered by plant-level data"
    
    # Filter to only include IRENA and EMBER data
    filtered_details = [detail for detail in missing_capacity_details if detail['source'] in ['IRENA', 'EMBER']]
    
    if not filtered_details:
        return "- **No missing capacity added** - All capacity covered by plant-level data"
    
    # Group by source
    by_source = {}
    for detail in filtered_details:
        source = detail['source']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(detail)
    
    # Format the output
    lines = []
    for source, details in by_source.items():
        source_lines = []
        for detail in details:
            tech = detail['technology']
            capacity = detail['capacity_gw']
            source_lines.append(f"  - **{tech}**: {capacity} GW")
        
        if source_lines:
            lines.append(f"- **{source} data**:")
            lines.extend(source_lines)
    
    return "\n".join(lines)


def calculate_missing_capacity_details(df_grouped_gem):
    """Calculate detailed missing capacity by technology and source."""
    try:
        # Filter for missing capacity records (those with "Aggregated Plant" in name)
        # Check multiple possible column names
        description_col = None
        for col in ['model_description', 'Plant / Project name', 'Unit / Phase name']:
            if col in df_grouped_gem.columns:
                description_col = col
                break
        
        if description_col is None:
            return []
        
        # Look for missing capacity records with multiple patterns
        missing_capacity_records = df_grouped_gem[
            (df_grouped_gem[description_col].str.contains('Aggregated Plant', na=False)) |
            (df_grouped_gem[description_col].str.contains('Missing', na=False)) |
            (df_grouped_gem[description_col].str.contains('Gap', na=False))
        ]
        
        # Also check if any records have "Aggregated Plant" in model_name
        if 'model_name' in df_grouped_gem.columns:
            aggregated_records = df_grouped_gem[
                df_grouped_gem['model_name'].str.contains('Aggregated Plant', na=False)
            ]
            
            # Combine the records
            import pandas as pd
            missing_capacity_records = pd.concat([missing_capacity_records, aggregated_records]).drop_duplicates()
        
        # Aggregate by technology and source to show totals instead of distributed values
        aggregated_data = {}
        
        # Group by model_fuel and source
        for _, record in missing_capacity_records.iterrows():
            capacity_gw = record['Capacity_GW']
            fuel_type = record['model_fuel']
            
            # Determine source from the description
            description = str(record.get(description_col, ''))
            model_name = str(record.get('model_name', ''))
            
            if 'IRENA Gap' in description or 'IRENA Gap' in model_name:
                source = 'IRENA'
            elif 'EMBER Gap' in description or 'EMBER Gap' in model_name:
                source = 'EMBER'
            else:
                source = 'Unknown'
            
            if capacity_gw > 0:
                # Create aggregation key
                key = (fuel_type, source)
                if key not in aggregated_data:
                    aggregated_data[key] = 0
                aggregated_data[key] += capacity_gw
        
        # Convert aggregated data to details list
        details = []
        for (fuel_type, source), total_capacity in aggregated_data.items():
            details.append({
                'technology': fuel_type,
                'capacity_gw': round(total_capacity, 2),
                'source': source
            })
        
        return details
    except Exception as e:
        print(f"Warning: Could not calculate missing capacity details: {e}")
        return []


def extract_periods_from_timeslice_outputs(timeslice_output_dir, input_iso):
    """Extract periods data from timeslice analysis outputs for calendar visualization"""
    periods_data = {
        'scarcity': [],
        'surplus': [], 
        'volatile': [],
        's1d': []
    }
    weather_year = 2013  # Default weather year
    
    try:
        import pandas as pd
        
        # Look for segment summary file
        segment_file = timeslice_output_dir / f"segment_summary_{input_iso}.csv"
        if segment_file.exists():
            df = pd.read_csv(segment_file)
            
            # Extract period information from the summary
            for _, row in df.iterrows():
                if 'start_date' in row and pd.notna(row['start_date']):
                    # Parse date format (MM-DD or similar)
                    start_date = str(row['start_date'])
                    if '-' in start_date:
                        month, day = map(int, start_date.split('-'))
                    else:
                        continue
                    
                    # Determine category from scenario or period type
                    scenario = str(row.get('scenario', '')).lower()
                    period_type = str(row.get('period', '')).lower()
                    
                    if 'scarcity' in scenario or 'scarcity' in period_type:
                        category = 'scarcity'
                    elif 'surplus' in scenario or 'surplus' in period_type:
                        category = 'surplus'  
                    elif 'volatile' in scenario or 'volatile' in period_type:
                        category = 'volatile'
                    elif 'weekly' in scenario or 'stress' in scenario:
                        category = 's1d'
                    else:
                        category = 'scarcity'  # Default
                    
                    period_info = {
                        'start_month': month,
                        'start_day': day,
                        'category': category,
                        'avg_coverage': row.get('avg_score', 0)
                    }
                    
                    # Add end date if duration is available
                    if 'duration_days' in row and pd.notna(row['duration_days']):
                        duration = int(row['duration_days'])
                        if duration > 1:
                            # Calculate end date
                            from datetime import datetime, timedelta
                            start_dt = datetime(2030, month, day)
                            end_dt = start_dt + timedelta(days=duration - 1)
                            period_info['end_month'] = end_dt.month
                            period_info['end_day'] = end_dt.day
                    
                    periods_data[category].append(period_info)
        
        # Also look for individual scenario files
        for scenario_type in ['ts12_clu', 'ts24_clu', 's1_d']:
            scenario_file = timeslice_output_dir / f"timeslices_{input_iso}_{scenario_type}.csv"
            if scenario_file.exists():
                # Additional parsing could be added here
                pass
                
    except Exception as e:
        print(f"   ⚠️  Error parsing timeslice data: {e}")
        return None
    
    # Return data if any periods were found
    total_periods = sum(len(periods) for periods in periods_data.values())
    if total_periods > 0:
        return {'periods': periods_data, 'weather_year': weather_year}
    else:
        return None


def create_model_notes(dest_folder, input_iso, processing_params, section_flags):
    """Generate README.md using YAML-based documentation system."""
    # Create README.md in the parent folder (where the model folder is)
    notes_file = dest_folder.parent / "README.md"
    
    # Initialize README generator with correct config path
    config_path = Path(__file__).parent / "config" / "readme_documentation.yaml"
    readme_gen = ReadmeGenerator(str(config_path))
    
    # Generate README content using YAML templates
    readme_content = readme_gen.generate_readme_content(
        iso_code=input_iso,
        processing_params=processing_params,
        **section_flags
    )
    
    # Write the README file
    with open(notes_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ Generated README.md using YAML templates: {notes_file}")


def update_readme_with_charts(input_iso, veda_models_dir="C:/Veda/Veda/Veda_models/vervestacks_models", grid_modeling=False, data_source=None):
    """
    Update existing README.md with timeslice analysis charts after they are generated.
    
    Args:
        input_iso: Country ISO code
        veda_models_dir: Path to VEDA models directory
        grid_modeling: If True, looks for VerveStacks_{ISO}_grids_<data_source> folder
        data_source: Data source identifier (e.g., 'kan', 'eur', 'syn_5')
    """
    try:
        from pathlib import Path
        
        # Find the model folder
        models_path = Path(veda_models_dir)
        
        # Create folder suffix with data_source
        if grid_modeling and data_source:
            folder_suffix = f"_grids_{data_source}"
        elif grid_modeling:
            folder_suffix = "_grids"
        else:
            folder_suffix = ""
        model_folder = models_path / f"VerveStacks_{input_iso}{folder_suffix}"
        readme_path = models_path / "README.md"
        
        if not model_folder.exists():
            print(f"   ⚠️  Model folder not found: {model_folder}")
            return False
            
        if not readme_path.exists():
            print(f"   ⚠️  README.md not found: {readme_path}")
            return False
        
        # Read existing README content
        readme_content = readme_path.read_text(encoding='utf-8')
        
        # Check if calendar already exists
        if "Interactive Timeslice Calendar" in readme_content:
            print(f"   ℹ️  Calendar already exists in README")
            return True
        
        # Look for SVG files in timeslice output directory
        timeslice_output_dir = Path("2_ts_design/outputs") / input_iso
        svg_files = []
        
        if timeslice_output_dir.exists():
            svg_files = list(timeslice_output_dir.glob("*.svg"))
            svg_files.sort()
        
        if not svg_files:
            print(f"   ℹ️  No SVG files found for {input_iso}")
            return False
        
        # Create source_data directory in model folder if it doesn't exist
        source_data_dir = model_folder / "source_data"
        source_data_dir.mkdir(exist_ok=True)
        
        # Generate calendar visualizations (both HTML and SVG)
        calendar_html_path = None
        calendar_svg_path = None
        try:
            from calendar_visualizer import create_calendar_visualization, create_github_calendar_svg
            
            timeslice_data = extract_periods_from_timeslice_outputs(timeslice_output_dir, input_iso)
            
            if timeslice_data:
                periods_data = timeslice_data['periods']
                weather_year = timeslice_data['weather_year']
                
                # Generate interactive HTML calendar
                calendar_html_path = create_calendar_visualization(periods_data, input_iso, source_data_dir, weather_year)
                
                # Generate GitHub-compatible SVG calendar
                calendar_svg_path = create_github_calendar_svg(periods_data, input_iso, source_data_dir, weather_year)
                
                print(f"   📅 Generated calendar visualizations (Weather Year: {weather_year})")
        except Exception as e:
            print(f"   ⚠️  Could not generate calendar visualization: {e}")
        
        # Generate calendar content if available
        calendar_content = ""
        if calendar_svg_path:
            svg_filename = calendar_svg_path.name
            html_filename = calendar_html_path.name if calendar_html_path else None
            svg_relative_path = f"VerveStacks_{input_iso}/source_data/{svg_filename}"
            html_relative_path = f"VerveStacks_{input_iso}/source_data/{html_filename}" if html_filename else None
            
            calendar_content = f"\n\n#### 📅 **Interactive Timeslice Calendar** - Visual overview of all critical periods throughout the year\n\n"
            
            # Embed SVG directly for GitHub compatibility
            calendar_content += f'<div align="center">\n'
            calendar_content += f'  <img src="{svg_relative_path}" alt="Timeslice Calendar - {input_iso}" width="800" />\n'
            calendar_content += f'</div>\n\n'
            
            # Add links to both versions
            if html_filename:
                calendar_content += f'📱 **Interactive Version**: [Open full interactive calendar]({html_relative_path}) (local viewing)\n\n'
            
            calendar_content += f'*Calendar shows critical periods: Scarcity 🔥, Surplus ⚡, Volatile 🌪️, and Weekly Stress 📅*\n\n'
        
        # Check if charts section exists and handle accordingly
        if "Generated Analysis Charts" in readme_content:
            # Charts section exists, just add calendar after the intro
            if calendar_content:
                # Find the position after the charts intro
                charts_intro_end = readme_content.find("*Interactive visualizations from the timeslice analysis process. Click any chart to view full resolution.*")
                if charts_intro_end != -1:
                    # Find the end of that line
                    insert_pos = readme_content.find("\n", charts_intro_end) + 1
                    # Insert calendar content
                    updated_content = readme_content[:insert_pos] + calendar_content + readme_content[insert_pos:]
                    readme_path.write_text(updated_content, encoding='utf-8')
                    print(f"   ✅ Added interactive calendar to existing charts section")
                    return True
                else:
                    # Fallback: append to end
                    updated_content = readme_content + calendar_content
                    readme_path.write_text(updated_content, encoding='utf-8')
                    print(f"   ✅ Added interactive calendar at end of README")
                    return True
            else:
                print(f"   ℹ️  Charts section exists but no calendar to add")
                return True
        else:
            # No charts section exists, create full section
            charts_content = "\n\n### 📊 Generated Analysis Charts\n\n"
            charts_content += "*Interactive visualizations from the timeslice analysis process. Click any chart to view full resolution.*\n\n"
            
            # Add calendar first if available
            if calendar_content:
                charts_content += calendar_content
            
            # Copy SVG files and add to README
            copied_files = []
            for svg_file in svg_files:
                # Copy SVG file to source_data folder
                dest_svg = source_data_dir / svg_file.name
                try:
                    import shutil
                    shutil.copy2(svg_file, dest_svg)
                    copied_files.append(svg_file.name)
                    print(f"   📊 Copied chart: {svg_file.name}")
                except Exception as e:
                    print(f"   ⚠️  Failed to copy {svg_file.name}: {e}")
                    continue
                
                # Create descriptive names based on filename patterns
                filename = svg_file.name
                model_folder_name = f"VerveStacks_{input_iso}"
                relative_path = f"{model_folder_name}/source_data/{filename}"
                
                if "supply_curves" in filename:
                    description = "**Renewable Supply Curves** - Cost-ordered renewable resource potential showing solar and wind capacity vs. LCOE"
                elif "plan2_triple5" in filename:
                    description = "**Critical Days Analysis (Triple-5)** - Detailed view of 15 critical days: 5 scarcity + 5 surplus + 5 volatile periods"
                elif "plan3_weekly" in filename:
                    description = "**Weekly Stress Analysis** - Sustained stress periods showing 2 worst weeks for renewable coverage"
                elif "aggregation_justification" in filename:
                    description = "**Timeslice Aggregation Justification** - Statistical analysis supporting the selected temporal resolution structure"
                elif "8760_quarterly" in filename:
                    description = "**Quarterly Energy Profiles** - Complete year breakdown showing seasonal demand and supply patterns"
                else:
                    description = f"**{filename.replace('_', ' ').replace('.svg', '').title()}** - Timeslice analysis visualization"
                
                charts_content += f"#### {description}\n"
                charts_content += f'<a href="{relative_path}" target="_blank">\n'
                charts_content += f'  <img src="{relative_path}" alt="{filename}" width="600" style="border: 2px solid #ddd; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 10px 0; cursor: pointer;" />\n'
                charts_content += f'</a>\n\n'
                charts_content += f'*Click image to view full size*\n\n'
            
            if copied_files:
                print(f"   ✅ Copied {len(copied_files)} timeslice analysis charts to source_data/")
            
            # Append charts section to README
            updated_content = readme_content + charts_content
            readme_path.write_text(updated_content, encoding='utf-8')
            
            print(f"   ✅ Updated README.md with {len(copied_files)} charts and calendar visualization")
            return True
        
    except Exception as e:
        print(f"   ❌ Error updating README with charts: {e}")
        return False


def update_system_settings(dest_folder, input_iso, grid_data=None, solar_wind_data=None):
    """
    Update the system settings file with the ISO code using xlwings (primary) for formula refresh.
    If grid_data is provided, also writes:
    - Grid commodity definitions to SysSettings.xlsx (grids sheet)
    - Grid trade links to separate file suppxls/trades/scentrade__trade_links.xlsx
    """
    syssettings_path = dest_folder / "SysSettings.xlsx"
    
    # Use df_fi_comm_sol_win from solar_wind_data for RE potentials
    commodities_df = solar_wind_data.get('df_fi_comm_sol_win') if solar_wind_data else None
    

    # Use xlwings primary for formula refresh capability
    try:
        app = xw.App(visible=False)
        app.display_alerts = False
        app.screen_updating = False
        try:
            wb_sys = xw.Book(str(syssettings_path))
            ws_sys = wb_sys.sheets["system_settings"]
            ws_sys.range("C4").value = input_iso

            # write SubRES commodies on the fuels sheet - so that they are accessble to VT files
            ws_fuels = wb_sys.sheets["fuels"]
            ws_fuels.range("M4").options(index=False).value = commodities_df

            # write fi_comm_grids on a new sheet - grids - so that they are accessible to VT files
            fi_comm_grids = grid_data.get('fi_comm_grids') if grid_data else None
            if fi_comm_grids is not None:
                try:
                    ws_grids = wb_sys.sheets["grids"]
                    ws_grids.clear()
                except:
                    ws_grids = wb_sys.sheets.add("grids")
                
                # Use excel_manager for consistent formatting
                from excel_manager import excel_manager
                excel_manager.write_formatted_table(ws_grids, "B4", fi_comm_grids, "~fi_comm")
                
            # Write grid trade links to separate file if grid modeling enabled
            if grid_data is not None:
                from excel_manager import excel_manager
                excel_manager.write_grid_trade_links(dest_folder, grid_data)

            # Refresh formulas
            wb_sys.app.calculate()
            wb_sys.save()
            wb_sys.close()
            print(f"System settings updated successfully with formulas refreshed for {input_iso}")
            return
        finally:
            app.quit()
    except Exception as e:
        print(f"Warning: xlwings failed, trying openpyxl fallback: {e}")
    


def create_veda_tables_for_vt_file(iso_processor, df_grouped_gem, ccs_retrofits_df):
    """Create the Veda model tables from existing stock and other data."""
    
    # Load required data
    output_path = iso_processor.output_dir / f"VerveStacks_{iso_processor.input_iso}.xlsx"
    # existing_stock_df = pd.read_excel(output_path, sheet_name="existing_stock", skiprows=5, usecols=lambda x: x != 'Unnamed: 0')
    # ccs_retrofits_df = pd.read_excel(output_path, sheet_name="ccs_retrofits", skiprows=2, usecols=lambda x: x != 'Unnamed: 0')
    # ngfs_data_df = pd.read_excel(output_path, sheet_name="ngfs_scenarios")

    ngfs_data_df = pd.DataFrame()
    
    # Try to read historical_data sheet, create empty DataFrame if missing
    try:
        base_year_data_df = pd.read_excel(output_path, sheet_name="historical_data")
        print("✅ Historical data loaded successfully")
    except Exception as e:
        print(f"⚠️  Could not read historical_data sheet: {e}")
        print("📊 Creating empty base_year_data_df")
        base_year_data_df = pd.DataFrame()
    
    life_df = pd.read_excel("data/technologies/ep_technoeconomic_assumptions.xlsx", sheet_name="life")

    # Register DataFrames with DuckDB
    duckdb.register('existing_stock_df', df_grouped_gem)
    duckdb.register('ccs_retrofits_df', ccs_retrofits_df)
    # duckdb.register('weo_pg_df', weo_pg_df)
    duckdb.register('life_df', life_df)

    # Create fi_t table (existing stock technology parameters)
    fi_t = duckdb.sql(f"""
        select T1.model_name AS process,T1.model_fuel AS "comm-in",
        "comm-out",
        T1."Start year" AS year,T1.capacity_gw AS ncap_pasti,
        T1.efficiency AS efficiency,T1.capex AS ncap_cost,T1.fixom AS ncap_fom,T1.varom AS act_cost,
        case
            when
            coalesce(CASE WHEN T1.retirement_year = '' THEN NULL ELSE CAST(T1.retirement_year AS INTEGER) END, 2055) - CAST(T1."Start year" AS INTEGER) > T2.life
            then
            coalesce(CASE WHEN T1.retirement_year = '' THEN NULL ELSE CAST(T1.retirement_year AS INTEGER) END, 2055) - CAST(T1."Start year" AS INTEGER) 
            else
            T2.life
        end AS ncap_tlife,
        T1.capacity_factor AS "ncap_af~fx"
        from existing_stock_df T1
        left join life_df T2 on T1.model_name ilike '%' || T2.model_name || '%'
        WHERE T1.model_name like 'ep_%'
        order by T1.model_name,T1."Start year"
    """).df()

    # Special handling for pumped storage
    fi_t.loc[fi_t['process'].str.contains('_hydro_ps'), 'comm-in'] = ''

    # Create fi_p table (process definitions)
    fi_p = duckdb.sql("""
        select 
        'ele' AS set,
        T1.model_name AS process,T1.model_description AS description,
        'GW' AS capacity_unit,
        'TWh' AS activity_unit,
        CASE when model_fuel IN ('solar','windon','windoff') then 'annual' else 'daynite' end AS timeslicelevel,
        CASE when model_description ilike 'aggregated%' then 'yes' else 'no' end AS vintage

        from existing_stock_df T1
        WHERE T1.model_name like 'ep_%'
        group by T1.model_name,T1.model_description,T1.model_fuel
        order by T1.model_name
    """).df()

    # Special handling for storage
    fi_p.loc[fi_p['process'].str.contains('_hydro_ps'), 'set'] = 'STG'

    # Create fi_t table (existing stock technology parameters)
    fi_t_new = duckdb.sql(f"""
        select T1.model_name AS process,T1.model_fuel AS "comm-in",
        "comm-out",
        T1."Start year" AS START,T1.capacity_gw AS cap_bnd,
        T1.efficiency AS efficiency,T1.capex AS ncap_cost,T1.fixom AS ncap_fom,T1.varom AS act_cost,
        case
            when
            coalesce(CASE WHEN T1.retirement_year = '' THEN NULL ELSE CAST(T1.retirement_year AS INTEGER) END, 2055) - CAST(T1."Start year" AS INTEGER) > T2.life
            then
            coalesce(CASE WHEN T1.retirement_year = '' THEN NULL ELSE CAST(T1.retirement_year AS INTEGER) END, 2055) - CAST(T1."Start year" AS INTEGER) 
            else
            T2.life
        end AS ncap_tlife,
        T1.capacity_factor AS "ncap_af~fx"
        from existing_stock_df T1
        left join life_df T2 on T1.model_name ilike '%' || T2.model_name || '%'
        WHERE not T1.model_name like 'ep_%'
        order by T1.model_name,T1."Start year"
    """).df()

    # Special handling for pumped storage
    fi_t_new.loc[fi_t_new['process'].str.contains('_hydro_ps'), 'comm-in'] = ''

    # Create fi_p table (process definitions)
    fi_p_new = duckdb.sql("""
        select 
        'ele' AS set,
        T1.model_name AS process,T1.model_description AS description,
        'GW' AS capacity_unit,
        'TWh' AS activity_unit,
        CASE when model_fuel IN ('solar','windon','windoff') then 'annual' else 'daynite' end AS timeslicelevel,
        CASE when model_description ilike 'aggregated%' then 'yes' else 'no' end AS vintage

        from existing_stock_df T1
        WHERE not T1.model_name like 'ep_%'
        group by T1.model_name,T1.model_description,T1.model_fuel
        order by T1.model_name
    """).df()

    # Special handling for storage
    fi_p_new.loc[fi_p_new['process'].str.contains('_hydro_ps'), 'set'] = 'STG'

    # Create CCS retrofit tables with inherited spatial commodities
    fi_t_ccs = duckdb.sql("""
        select T1.model_name AS process,T1.model_fuel AS "comm-in",
        COALESCE(T2."comm-out", 'ELC') as "comm-out",
        T1.efficiency AS efficiency,T1.capex AS ncap_cost,T1.fixom AS ncap_fom,T1.varom AS act_cost,
        T1.AF AS AF,
        T1.plant_old AS other_indexes, 1 AS prc_refit,
        20 AS ncap_tlife
        from ccs_retrofits_df T1
        LEFT JOIN (select model_name, "comm-out" from existing_stock_df group by model_name, "comm-out") T2 ON T1.plant_old = T2.model_name
        order by T1.model_name
    """).df()

    duckdb.register('fi_p', fi_p)
    
    fi_p_ccs = duckdb.sql("""
        select 
        'ele' AS set,
        T1.model_name AS process,'ccs retrofit of -- ' || cast(T2.model_description as varchar) AS description,
        'GW' AS capacity_unit,
        'TWh' AS activity_unit,
        'daynite' AS timeslicelevel,
        'no' AS vintage

        from ccs_retrofits_df T1
        inner join existing_stock_df T2 ON T1.plant_old = T2.model_name
        group by T1.model_name,T2.model_description
        order by T1.model_name
    """).df()

    return fi_t, fi_p, fi_t_new, fi_p_new, fi_t_ccs, fi_p_ccs, ngfs_data_df, base_year_data_df


def write_veda_excel_files(dest_folder, input_iso, tables, iso_processor):
    """Write the Veda Excel files with professional Energy Sector formatting."""
    
    fi_t, fi_p, fi_t_new, fi_p_new, fi_t_ccs, fi_p_ccs, ngfs_data_df, base_year_data_df = tables

    # Create main VT file with professional formatting
    vt_output_path = dest_folder / f"vt_vervestacks_{input_iso}_v1.xlsx"
    if vt_output_path.exists():
        vt_output_path.unlink()

    # Organize tables for VT workbook
    tables_dict = {
        'existing_stock': (fi_t, fi_p),
        'new_options': (fi_t_new, fi_p_new),
        'ccs_retrofits': (fi_t_ccs, fi_p_ccs)
    }
    
    # get additional hydro potential
    from new_hydro_potential import HydroPotentialVisualizer

    # Initialize visualizer
    viz = HydroPotentialVisualizer()

    # Generate VEDA tables for China with cit data source
    print(f'Generating VEDA Tables for {input_iso} (data_source: {iso_processor.data_source})')
    print('=' * 60)

    fi_process_df, fi_t_df = viz.generate_hydro_tables(input_iso, iso_processor.data_source, iso_processor.grid_modeling)

    if not fi_t_df.empty:
        print(f'✅ Additional hydro potential found for {input_iso}')
        tables_dict['additional_hydro_pot'] = (fi_t_df, fi_process_df)

    # Create VT workbook with professional formatting
    print("🎨 Creating VT workbook with Energy Sector styling...")
    excel_manager.write_vt_workbook(vt_output_path, tables_dict)
    
    # Update scenario files with IAMC and historical data
    print("📊 Updating scenario files with professional formatting...")
    success = excel_manager.update_scenario_files(dest_folder, input_iso, ngfs_data_df, base_year_data_df, iso_processor)
    
    if success:
        print("✅ All Excel files created with professional formatting!")
    else:
        print("⚠️  VT file created successfully, scenario file updates had warnings.")
    
    print("📋 Continuing with resource file updates...")


def update_re_subres_file(dest_folder, input_iso, iso_processor, solar_wind_data = None):
    """Update SubRES files with ISO-specific data including hydro and solar/wind from grid modeling."""

    RE_SubRES_file = dest_folder / "SubRES_Tmpl" / "SubRES_New_RE_and_Conventional.xlsx"

    # # Load and filter hydro renewable energy potential data for this ISO
    # process_df = pd.read_excel("data/technologies/re_potentials.xlsx", sheet_name="process")
    # process_df = process_df[process_df['process'].str.contains(f"_{input_iso}", na=False)]

    # fi_t_df = pd.read_excel("data/technologies/re_potentials.xlsx", sheet_name="fi_t")
    # fi_t_df = fi_t_df[fi_t_df['process'].str.contains(f"_{input_iso}", na=False)]

    # Use ExcelManager for consistent Excel operations and formatting
    from excel_manager import ExcelManager
    excel_manager = ExcelManager()
    excel_manager.write_re_subres_data(RE_SubRES_file, solar_wind_data, input_iso, iso_processor)
    


def create_utilization_summary_table(df_ember_util, df_irena_util, input_iso, base_vs_path):
    """Create a summary table of min/max utilization factors for each fuel type."""
    try:
        # Filter for the specific ISO
        df_ember_util_iso = df_ember_util[df_ember_util['iso_code'] == input_iso]
        df_irena_util_iso = df_irena_util[df_irena_util['iso_code'] == input_iso]
        
        # Get unique fuels from both datasets
        ember_fuels = set(df_ember_util_iso['model_fuel'].unique()) if not df_ember_util_iso.empty else set()
        irena_fuels = set(df_irena_util_iso['model_fuel'].unique()) if not df_irena_util_iso.empty else set()
        all_fuels = sorted(list(ember_fuels | irena_fuels))
        
        if not all_fuels:
            print("No utilization factor data found for summary table")
            return
        
        # Calculate min/max for each fuel
        summary_data = []
        for fuel in all_fuels:
            row = {'model_fuel': fuel}
            
            # EMBER min/max
            ember_fuel_data = df_ember_util_iso[df_ember_util_iso['model_fuel'] == fuel]
            if not ember_fuel_data.empty:
                row['ember_min'] = ember_fuel_data['utilization_factor'].min()
                row['ember_max'] = ember_fuel_data['utilization_factor'].max()
            else:
                row['ember_min'] = None
                row['ember_max'] = None
            
            # IRENA min/max
            irena_fuel_data = df_irena_util_iso[df_irena_util_iso['model_fuel'] == fuel]
            if not irena_fuel_data.empty:
                row['irena_min'] = irena_fuel_data['utilization_factor'].min()
                row['irena_max'] = irena_fuel_data['utilization_factor'].max()
            else:
                row['irena_min'] = None
                row['irena_max'] = None
            
            summary_data.append(row)
        
        # Create DataFrame
        summary_df = pd.DataFrame(summary_data)
        
        # Open the Base VS file and add table to Veda sheet at F2 using xlwings
        app = xw.App(visible=False)
        app.display_alerts = False
        app.screen_updating = False
        try:
            wb = app.books.open(base_vs_path)
            ws_veda = wb.sheets['Veda']
            
            # Starting position F2
            start_col = 6  # Column F
            start_row = 2
            
            # Headers
            headers = ['model_fuel', 'ember_min', 'ember_max', 'irena_min', 'irena_max']
            ws_veda.range(f'F{start_row}').value = [headers]
            
            # Format header row: bold font and light blue background
            header_range = ws_veda.range(f'F{start_row}:J{start_row}')
            header_range.font.bold = True
            header_range.color = (220, 230, 241)  # Light blue background
            
            # Data rows
            data_rows = []
            for _, row in summary_df.iterrows():
                data_row = [
                    row['model_fuel'],
                    'N/A' if row['ember_min'] is None else row['ember_min'],
                    'N/A' if row['ember_max'] is None else row['ember_max'],
                    'N/A' if row['irena_min'] is None else row['irena_min'],
                    'N/A' if row['irena_max'] is None else row['irena_max']
                ]
                data_rows.append(data_row)
            
            # Write data
            if data_rows:
                ws_veda.range(f'F{start_row + 1}').value = data_rows
                
                # Format percentage columns (skip fuel name column)
                for col_offset in range(1, 5):  # Columns G, H, I, J
                    col_letter = chr(ord('F') + col_offset)
                    data_range = ws_veda.range(f'{col_letter}{start_row + 1}:{col_letter}{start_row + len(data_rows)}')
                    # Only format non-N/A cells as percentages
                    for cell in data_range:
                        if cell.value != 'N/A' and cell.value is not None:
                            cell.number_format = '0.0%'
            
            wb.save()
            wb.close()
        finally:
            app.quit()
        
        print(f"Utilization factor summary table created at F2 in Veda sheet with {len(all_fuels)} fuel types")
        
    except Exception as e:
        print(f"Warning: Could not create utilization summary table: {e}")

def copy_supply_curve_charts(dest_folder, input_iso):
    """Copy supply curve charts to renewable_energy subfolder for README embedding"""
    # Create renewable_energy subfolder
    renewable_energy_dir = dest_folder / "renewable_energy"
    renewable_energy_dir.mkdir(exist_ok=True)
    
    # Source files from timeslice design output
    ts_output_dir = Path(f"2_ts_design/outputs/{input_iso}")
    
    # Copy SVG supply curve chart (if exists)
    svg_source = ts_output_dir / f"supply_curves_{input_iso}.svg"
    if svg_source.exists():
        svg_dest = renewable_energy_dir / f"supply_curves_{input_iso}.svg"
        shutil.copy2(svg_source, svg_dest)
        print(f"✅ Copied supply curve chart: {svg_dest}")
    else:
        print(f"ℹ️ Supply curve chart not found (timeslice analysis not run): {svg_source}")
    
    # Copy PNG supply curve chart (if exists)
    png_source = ts_output_dir / f"supply_curves_{input_iso}.png"
    if png_source.exists():
        png_dest = renewable_energy_dir / f"supply_curves_{input_iso}.png"
        shutil.copy2(png_source, png_dest)
        print(f"✅ Copied supply curve chart (PNG): {png_dest}")

def copy_timeslice_charts(dest_folder, input_iso):
    """Copy timeslice analysis charts to timeslice_analysis subfolder for README embedding"""
    # Create timeslice_analysis subfolder
    timeslice_dir = dest_folder / "timeslice_analysis"
    timeslice_dir.mkdir(exist_ok=True)
    
    # Source directory for timeslice outputs
    ts_output_dir = Path(f"2_ts_design/outputs/{input_iso}")
    
    # Define the 4 key timeslice charts to copy
    chart_files = [
        f"re_analysis_summary_{input_iso}.svg",
        f"aggregation_justification_{input_iso}_ts_048.svg", 
        f"stress_periods_s2_w_p2_d_weekly_{input_iso}.svg",
        f"stress_periods_s5p5v5_d_{input_iso}.svg"
    ]
    
    copied_count = 0
    for chart_file in chart_files:
        source_path = ts_output_dir / chart_file
        if source_path.exists():
            dest_path = timeslice_dir / chart_file
            shutil.copy2(source_path, dest_path)
            print(f"✅ Copied timeslice chart: {dest_path}")
            copied_count += 1
        else:
            print(f"ℹ️ Timeslice chart not found: {source_path}")
    
    return copied_count > 0

def copy_hydro_charts(dest_folder, input_iso):
    """Copy hydro availability charts to source_data subfolder for README embedding"""
    import shutil
    
    # Source directory where hydro charts are generated
    source_data_dir = Path("source_data")
    
    # Check if hydro charts exist
    monthly_chart = source_data_dir / f"{input_iso}_hydro_monthly_profile.png"
    annual_chart = source_data_dir / f"{input_iso}_hydro_annual_trajectory.png"
    
    charts_copied = 0
    
    if monthly_chart.exists():
        # Copy to model's source_data directory (same level as other charts)
        dest_monthly = dest_folder / "source_data" / f"{input_iso}_hydro_monthly_profile.png"
        dest_folder_source_data = dest_folder / "source_data"
        dest_folder_source_data.mkdir(exist_ok=True)
        
        shutil.copy2(monthly_chart, dest_monthly)
        print(f"✅ Copied hydro monthly chart: {dest_monthly}")
        charts_copied += 1
    
    if annual_chart.exists():
        # Copy to model's source_data directory
        dest_annual = dest_folder / "source_data" / f"{input_iso}_hydro_annual_trajectory.png"
        dest_folder_source_data = dest_folder / "source_data"
        dest_folder_source_data.mkdir(exist_ok=True)
        
        shutil.copy2(annual_chart, dest_annual)
        print(f"✅ Copied hydro annual chart: {dest_annual}")
        charts_copied += 1
    
    if charts_copied == 0:
        print(f"ℹ️ No hydro charts found for {input_iso}")
    
    return charts_copied > 0

def copy_grid_visualization_files(dest_folder, input_iso, data_source):
    """Copy grid visualization files to grid_analysis subfolder for README embedding"""
    # Create grid_analysis subfolder
    grid_analysis_dir = dest_folder / "grid_analysis"
    grid_analysis_dir.mkdir(exist_ok=True)
    
    # Source files from grid modeling output
    grid_output_dir = Path(f"1_grids/output_{data_source}/{input_iso}")
    
    # Copy visualization file - different for synthetic vs real grids
    if data_source.startswith('syn'):
        # For synthetic grids, use cluster_shapes_4panel.png
        viz_source = grid_output_dir / f"{input_iso}_cluster_shapes_4panel.png"
        if not viz_source.exists():
            raise FileNotFoundError(f"Cluster shapes visualization not found: {viz_source}")
        viz_dest = grid_analysis_dir / f"{input_iso}_cluster_shapes_4panel.png"
        shutil.copy2(viz_source, viz_dest)
        print(f"✅ Copied cluster shapes visualization: {viz_dest}")
    else:
        # For real grids, use network_visualization.html
        html_source = grid_output_dir / f"{input_iso}_network_visualization.html"
        if not html_source.exists():
            raise FileNotFoundError(f"Grid visualization file not found: {html_source}")
        html_dest = grid_analysis_dir / f"{input_iso}_network_visualization.html"
        shutil.copy2(html_source, html_dest)
        print(f"✅ Copied grid visualization: {html_dest}")
  
    
    # Copy other relevant grid analysis files
    grid_files = [
        f"{input_iso}_clustered_buses.csv",
        f"{input_iso}_clustered_lines.csv", 
        f"{input_iso}_zone_bus_mapping.csv",
        f"{input_iso}_power_plants_assigned_to_buses.csv"
    ]
    
    # For synthetic grids, zone_bus_mapping is not needed (clusters ARE buses)
    optional_for_syn = [f"{input_iso}_zone_bus_mapping.csv"]
    
    for filename in grid_files:
        source_file = grid_output_dir / filename
        if not source_file.exists():
            # Skip optional files for synthetic grids
            if data_source.startswith('syn') and filename in optional_for_syn:
                print(f"⊘  Skipped (not needed for synthetic grids): {filename}")
                continue
            raise FileNotFoundError(f"Grid data file not found: {source_file}")
        dest_file = grid_analysis_dir / filename
        shutil.copy2(source_file, dest_file)
        print(f"✅ Copied grid data: {filename}")
    
    print(f"✅ Grid analysis files copied to: {grid_analysis_dir}")

def create_region_com_dimension(buses_df,solar_df,wind_df,windoff_df,input_iso):
    """
    Create region_com dimension for commodity_map and region-grid_commodity geolocation
    """
    
    # Step 1: Create dimension-name-description DataFrame
    # Extract unique bus_ids from buses_df
    unique_bus_ids = buses_df['bus_id'].unique()
    
    # Create the dimension DataFrame using bus_id_to_commodity function
    df_region_com_dimension = pd.DataFrame({
        'dimension': 'region_com',
        'name': [bus_id_to_commodity(bus_id, add_prefix=True) for bus_id in unique_bus_ids],
        'description': [bus_id_to_commodity(bus_id, add_prefix=True) for bus_id in unique_bus_ids]
    })

    # Step 2: Add solar cluster commodities to the dimension DataFrame
    if not solar_df.empty:
        # Create solar dimension entries using cluster_id_to_commodity function
        df_solar_dimension = pd.DataFrame({
            'dimension': 'region_com',
            'name': [cluster_id_to_commodity(cluster_id, "spv", "commodity") for cluster_id in solar_df['cluster_id']],
            'description': [cluster_id_to_commodity(cluster_id, "spv", "commodity") for cluster_id in solar_df['cluster_id']]
        })
        
        # Combine bus and solar dimensions
        df_region_com_dimension = pd.concat([df_region_com_dimension, df_solar_dimension], ignore_index=True)
    
    # Step 3: Add wind onshore cluster commodities to the dimension DataFrame
    if not wind_df.empty:
        # Create wind onshore dimension entries using cluster_id_to_commodity function
        df_wind_dimension = pd.DataFrame({
            'dimension': 'region_com',
            'name': [cluster_id_to_commodity(cluster_id, "won", "commodity") for cluster_id in wind_df['cluster_id']],
            'description': [cluster_id_to_commodity(cluster_id, "won", "commodity") for cluster_id in wind_df['cluster_id']]
        })
        
        # Combine with existing dimensions
        df_region_com_dimension = pd.concat([df_region_com_dimension, df_wind_dimension], ignore_index=True)
    
    # Step 4: Add wind offshore cluster commodities to the dimension DataFrame
    if not windoff_df.empty:
        # Create wind offshore dimension entries using cluster_id_to_commodity function
        df_windoff_dimension = pd.DataFrame({
            'dimension': 'region_com',
            'name': [cluster_id_to_commodity(cluster_id, "wof", "commodity") for cluster_id in windoff_df['cluster_id']],
            'description': [cluster_id_to_commodity(cluster_id, "wof", "commodity") for cluster_id in windoff_df['cluster_id']]
        })
        
        # Combine with existing dimensions
        df_region_com_dimension = pd.concat([df_region_com_dimension, df_windoff_dimension], ignore_index=True)
    
    
    # Step 5: Create geolocation DataFrame with region-lat-lng structure
    geolocation_data = []
    
    # Add bus geolocations
    if not buses_df.empty and 'x' in buses_df.columns and 'y' in buses_df.columns:
        for _, row in buses_df.iterrows():
            commodity = bus_id_to_commodity(row['bus_id'], add_prefix=True)
            geolocation_data.append({
                'region': f"{input_iso}-{commodity}",
                'lat': row['y'],
                'lng': row['x']
            })
    
    # Add solar cluster geolocations
    if not solar_df.empty and 'centroid_lat' in solar_df.columns and 'centroid_lon' in solar_df.columns:
        for _, row in solar_df.iterrows():
            commodity = cluster_id_to_commodity(row['cluster_id'], "spv", "commodity")
            geolocation_data.append({
                'region': f"{input_iso}-{commodity}",
                'lat': row['centroid_lat'],
                'lng': row['centroid_lon']
            })
    
    # Add wind onshore cluster geolocations
    if not wind_df.empty and 'centroid_lat' in wind_df.columns and 'centroid_lon' in wind_df.columns:
        for _, row in wind_df.iterrows():
            commodity = cluster_id_to_commodity(row['cluster_id'], "won", "commodity")
            geolocation_data.append({
                'region': f"{input_iso}-{commodity}",
                'lat': row['centroid_lat'],
                'lng': row['centroid_lon']
            })
    
    # Add wind offshore cluster geolocations
    if not windoff_df.empty and 'centroid_lat' in windoff_df.columns and 'centroid_lon' in windoff_df.columns:
        for _, row in windoff_df.iterrows():
            commodity = cluster_id_to_commodity(row['cluster_id'], "wof", "commodity")
            geolocation_data.append({
                'region': f"{input_iso}-{commodity}",
                'lat': row['centroid_lat'],
                'lng': row['centroid_lon']
            })
    
    # Create the geolocation DataFrame
    df_region_com_geolocation = pd.DataFrame(geolocation_data)
    
    return df_region_com_dimension, df_region_com_geolocation


def generate_geographic_data(iso_processor):
    """
    Generate geographic data from clustered buses and REZoning data for grid modeling.
    
    Args:
        iso_processor: ISOProcessor instance with REZoning data
        
    Returns:
        tuple: (df_geolocation, df_set_psetco) DataFrames
    """
    
    try:
        input_iso = iso_processor.input_iso
        
        # Load clustered buses data
        buses_file = Path(f"1_grids/output_{iso_processor.data_source}/{input_iso}/{input_iso}_clustered_buses.csv")
        
        if not buses_file.exists():
            print(f"⚠️  Clustered buses file not found: {buses_file}")
            return pd.DataFrame(), pd.DataFrame()
        
        buses_df = pd.read_csv(buses_file)

        # Load solar clusters
        solar_file = Path(f"1_grids/output_{iso_processor.data_source}/{input_iso}/cluster_summary_solar.csv")
        solar_df = pd.read_csv(solar_file)
        # Load wind clusters
        wind_file = Path(f"1_grids/output_{iso_processor.data_source}/{input_iso}/cluster_summary_wind_onshore.csv")
        wind_df = pd.read_csv(wind_file)
        # Load wind off clusters
        windoff_file = Path(f"1_grids/output_{iso_processor.data_source}/{input_iso}/cluster_summary_wind_offshore.csv")
        if windoff_file.exists():
            windoff_df = pd.read_csv(windoff_file)
        else:
            windoff_df = pd.DataFrame()

        # create region_com dimension for commodity_map and region-grid_commodity geolocation
        df_region_com_dimension, df_region_com_geolocation = create_region_com_dimension(buses_df,solar_df,wind_df,windoff_df,input_iso)


        # Function to strip voltage from bus_id
        def strip_voltage_from_bus_id(bus_id):
            """Remove voltage suffix from bus_id (e.g., 'bus123-380' -> 'bus123')"""
            if isinstance(bus_id, str) and '-' in bus_id:
                # Split by '-' and take all parts except the last one if it's numeric (voltage)
                parts = bus_id.split('-')
                if len(parts) > 1 and parts[-1].isdigit():
                    return '-'.join(parts[:-1])
            return bus_id
        
        # Apply voltage stripping to bus_id column
        buses_df['clean_bus_id'] = buses_df['bus_id'].apply(strip_voltage_from_bus_id)
        
        # Get distinct clean_bus_id with coordinates (keep first occurrence for each clean_bus_id)
        buses_distinct = buses_df.drop_duplicates(subset=['clean_bus_id'], keep='first')
        
        # Create geolocation DataFrame from buses
        df_geolocation_buses = pd.DataFrame({
            'region': buses_distinct['clean_bus_id'].apply(lambda x: f"p_{bus_id_to_commodity(x, add_prefix=False)}"),
            'lat': buses_distinct['y'],
            'lng': buses_distinct['x']
        })
        
        # Add REZoning solar grid cells to geolocation
        df_geolocation_solar = pd.DataFrame({
            'region': solar_df['cluster_id'].apply(lambda x: f"rez_spv_{int(x):03d}"),
            'lat': solar_df['centroid_lat'],
            'lng': solar_df['centroid_lon']
        })
        
        # Add REZoning wind on grid cells to geolocation
        df_geolocation_windon = pd.DataFrame({
            'region': wind_df['cluster_id'].apply(lambda x: f"rez_won_{int(x):03d}"),
            'lat': wind_df['centroid_lat'],
            'lng': wind_df['centroid_lon']
        })
        
        # Add REZoning wind off grid cells to geolocation
        if not windoff_df.empty:
            df_geolocation_windoff = pd.DataFrame({
                'region': windoff_df['cluster_id'].apply(lambda x: f"rez_wof_{int(x):03d}"),
                'lat': windoff_df['centroid_lat'],
                'lng': windoff_df['centroid_lon']
            })
        else:
            df_geolocation_windoff = pd.DataFrame()


        # Combine geolocation sources (only non-empty ones)
        geolocation_dfs = []
        if not df_geolocation_buses.empty:
            geolocation_dfs.append(df_geolocation_buses)
        if not df_geolocation_solar.empty:
            geolocation_dfs.append(df_geolocation_solar)
        if not df_geolocation_windon.empty:
            geolocation_dfs.append(df_geolocation_windon)
        if not df_geolocation_windoff.empty:
            geolocation_dfs.append(df_geolocation_windoff)
        
        # Concatenate only if we have DataFrames to concat
        if geolocation_dfs:
            df_geolocation = pd.concat(geolocation_dfs, ignore_index=True)
            # Remove duplicates based on region (keep first occurrence)
            df_geolocation = df_geolocation.drop_duplicates(subset=['region'], keep='first')
        else:
            # Create empty DataFrame with correct structure if all are empty
            df_geolocation = pd.DataFrame(columns=['region', 'lat', 'lng'])

        # Create admin_1 mapping DataFrame using geolocation mapper
        df_admin_mapping = pd.DataFrame()
        if not df_geolocation.empty:
            try:
                # Import the geolocation mapper
                import sys
                import os
                misc_path = os.path.join(os.path.dirname(__file__), "Miscellaneous")
                if misc_path not in sys.path:
                    sys.path.insert(0, misc_path)
                
                from geolocation_to_admin_regions import GeolocationMapper
                
                # Initialize the mapper with correct data path
                data_path = os.path.join(os.path.dirname(__file__), "data", "country_data")
                mapper = GeolocationMapper(data_path)
                mapper.load_data()
                
                # Map each coordinate to admin_1
                admin_mappings = []
                for _, row in df_geolocation.iterrows():
                    try:
                        result = mapper.lookup_coordinates(row['lat'], row['lng'])
                        admin_1_name = result.get('admin_1') or 'Unknown'  # Handle None values
                        admin_mappings.append({
                            'pset_set': row['region'],
                            'dimension': 'admin_1',
                            'description': admin_1_name
                        })
                    except Exception as e:
                        # Fallback for failed lookups
                        print(f"Warning: Failed to lookup admin_1 for {row['region']}: {e}")
                        admin_mappings.append({
                            'pset_set': row['region'],
                            'dimension': 'admin_1',
                            'description': 'Unknown'
                        })
                
                df_admin_mapping = pd.DataFrame(admin_mappings)
                print(f"Generated admin_1 mappings: {len(df_admin_mapping)} regions")
                
            except Exception as e:
                print(f"Warning: Could not generate admin_1 mappings: {e}")
                df_admin_mapping = pd.DataFrame(columns=['pset_set', 'dimension', 'description'])
        else:
            df_admin_mapping = pd.DataFrame(columns=['pset_set', 'dimension', 'description'])
        
        # Create geographic sets DataFrame
        df_set_psetco = pd.DataFrame({
            'setname': buses_distinct['clean_bus_id'].apply(lambda x: f"p_{bus_id_to_commodity(x, add_prefix=False)}"),
            'pset_co': buses_distinct['clean_bus_id'].apply(lambda x: f"{bus_id_to_commodity(x, add_prefix=True)}*")
        })
        
        df_solar_set_psetco = pd.DataFrame({
            'setname': solar_df['cluster_id'].apply(lambda x: f"rez_spv_{int(x):03d}"),
            'pset_co': solar_df['cluster_id'].apply(lambda x: f"elc_spv_{int(x):03d}")
        })

        df_windon_set_psetco = pd.DataFrame({
            'setname': wind_df['cluster_id'].apply(lambda x: f"rez_won_{int(x):03d}"),
            'pset_co': wind_df['cluster_id'].apply(lambda x: f"elc_won_{int(x):03d}")
        })

        if not windoff_df.empty:
            df_windoff_set_psetco = pd.DataFrame({
                'setname': windoff_df['cluster_id'].apply(lambda x: f"rez_wof_{int(x):03d}"),
                'pset_co': windoff_df['cluster_id'].apply(lambda x: f"elc_wof_{int(x):03d}")
        })        
        else:
            df_windoff_set_psetco = pd.DataFrame()
        
        # Collect non-empty DataFrames for concatenation
        dfs_to_concat = []
        if not df_set_psetco.empty:
            dfs_to_concat.append(df_set_psetco)
        if not df_solar_set_psetco.empty:
            dfs_to_concat.append(df_solar_set_psetco)
        if not df_windon_set_psetco.empty:
            dfs_to_concat.append(df_windon_set_psetco)
        if not df_windoff_set_psetco.empty:
            dfs_to_concat.append(df_windoff_set_psetco)
        
        # Concatenate only if we have DataFrames to concat
        if dfs_to_concat:
            df_set_psetco = pd.concat(dfs_to_concat, ignore_index=True)
        else:
            # Create empty DataFrame with correct structure if all are empty
            df_set_psetco = pd.DataFrame(columns=['setname', 'pset_co'])
        
        # Add additional columns only if we have data
        if not df_set_psetco.empty:
            df_set_psetco['pset_ci'] = df_set_psetco['pset_co']
            df_set_psetco['t_pos_andor'] = 'OR'

        print(f"Generated geographic data: {len(df_geolocation)} locations, {len(df_set_psetco)} sets, {len(df_admin_mapping)} admin mappings")
        return df_geolocation, df_set_psetco, df_admin_mapping, df_region_com_dimension, df_region_com_geolocation
        
    except Exception as e:
        print(f"Error generating geographic data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def _write_buildrate_assumptions(base_vs_path, input_iso):
    """Write buildrate accumulations for the active iso from vs_mappings file"""
    from excel_manager import ExcelManager
    excel_manager = ExcelManager()
    
    import pandas as pd

    # Read the 'builrates' sheet from the vs_mappings Excel file
    vs_mappings_path = "Assumptions/VS_mappings.xlsx"
    try:
        buildrates_df = pd.read_excel(vs_mappings_path, sheet_name="buildrates")
    except Exception as e:
        print(f"Warning: Could not read 'builrates' sheet from {vs_mappings_path}: {e}")
        buildrates_df = pd.DataFrame()

    # Get the buildrate assumptions for the active iso
    buildrate_assumptions = buildrates_df[buildrates_df['iso'] == input_iso]

    # Write the buildrate assumptions to the base vs file
    excel_manager.write_buildrate_assumptions(base_vs_path, buildrate_assumptions,)
    


def create_veda_model(iso_processor, df_grouped_gem, df_irena_util, df_ember_util, tsopt='ts012', process_all_tsopts=False, skip_timeslices=False, auto_commit=True, ccs_retrofits_df=None, re_targets_ember_df=None):
    """
    Create the complete Veda model for the given ISO.
    
    Args:
        iso_processor: ISOProcessor instance with configuration and data
        df_grouped_gem: GEM data for existing power plants
        df_irena_util: IRENA utilization factor data  
        df_ember_util: EMBER utilization factor data
        tsopt: Time slice option (default: 'ts12_clu') - used when process_all_tsopts=False
        process_all_tsopts: If True, process all available ts_* options (ignores tsopt parameter)
        skip_timeslices: If True, skip time-slice processing entirely
        auto_commit: If True, perform git operations (branch creation, commits, pushes)
        
    Returns:
        dest_folder: Path to the created model directory
    """
    
    # Copy template and set up folder structure
    # Calculate actual statistics from the data
    stats = calculate_processing_statistics(df_grouped_gem, iso_processor, ccs_retrofits_df)
    
    # Collect processing parameters for documentation
    processing_params = {
        'capacity_threshold': getattr(iso_processor, 'capacity_threshold', 'Not specified'),
        'efficiency_adjustment_gas': getattr(iso_processor, 'efficiency_adjustment_gas', 'Not specified'),
        'efficiency_adjustment_coal': getattr(iso_processor, 'efficiency_adjustment_coal', 'Not specified'),
        'tsopt': tsopt,
        'output_dir': str(iso_processor.output_dir),
        'process_all_tsopts': process_all_tsopts,
        'skip_timeslices': skip_timeslices
    }
    
    # Add all statistics to processing_params
    processing_params.update(stats)
    
    # Calculate hydro capacity for hydro availability scenarios (exclude pumped storage)
    try:
        # Only count regular hydro power plants, not pumped storage
        hydro_plants = df_grouped_gem[df_grouped_gem['model_fuel'] == 'hydro']
        # Exclude pumped storage plants from hydro capacity calculation
        pumped_storage_mask = hydro_plants['model_name'].str.contains('_hydro_ps', na=False)
        regular_hydro_plants = hydro_plants[~pumped_storage_mask]
        hydro_capacity_gw = regular_hydro_plants['Capacity_GW'].sum()
        processing_params['hydro_capacity_gw'] = hydro_capacity_gw
        print(f"   💧 Hydro power capacity (excluding pumped storage): {hydro_capacity_gw:.1f} GW")
    except Exception as e:
        print(f"   ⚠️  Could not calculate hydro capacity: {e}")
        processing_params['hydro_capacity_gw'] = 0
    
    # Template already copied in process_existing_stock(), just get the path
    from pathlib import Path
    models_dir = Path("C:/Veda/Veda/Veda_models/vervestacks_models")
    
    # Create model folder path with data_source suffix
    grid_modeling = getattr(iso_processor, 'grid_modeling', False)
    data_source = getattr(iso_processor, 'data_source', None)
    
    if grid_modeling and data_source:
        folder_suffix = f"_grids_{data_source}"
    elif grid_modeling:
        folder_suffix = "_grids"
    else:
        folder_suffix = ""
    dest_folder = models_dir / f"VerveStacks_{iso_processor.input_iso}{folder_suffix}"
    
    # README generation moved to after supply curve copying

    # Process grid modeling data if enabled
    grid_data = None
    if iso_processor.grid_modeling:
        try:
            print("Processing grid modeling data...")
            from grid_modeling import process_grid_data
            grid_data = process_grid_data(iso_processor)
            print("Grid modeling data processed successfully.")
        except Exception as e:
            print(f"Warning: Grid modeling failed: {e}")
            print("Continuing with model creation...")
            grid_data = None

    # Compile solar/wind data
    # Use data_source from iso_processor for consistent grid/solar/wind data compilation
    from grid_modeling import compile_solar_wind_data_grid
    solar_wind_data = compile_solar_wind_data_grid(iso_processor)

    # Grids or ISO - we have all tables related to solar/wind in solar_wind_data at this point
    print("Solar/wind data compiled successfully.")

    # Update system settings, passing grid_data if available (from grid modeling)
    update_system_settings(dest_folder, iso_processor.input_iso, grid_data=grid_data, solar_wind_data=solar_wind_data)
    
    # Create Veda tables from processed data
    tables = create_veda_tables_for_vt_file(iso_processor, df_grouped_gem,ccs_retrofits_df)
    
    # Write Excel files  
    print("Writing Excel files...")
    print("Using xlwings for Excel file creation with formula refresh...")

    write_veda_excel_files(dest_folder, iso_processor.input_iso, tables, iso_processor)

    print("Excel files written successfully using xlwings.")
    
    # Update SubRES files
    try:
        print("Updating SubRES files...")
        update_re_subres_file(dest_folder, iso_processor.input_iso, iso_processor, solar_wind_data=solar_wind_data)
        print("SubRES file updates completed.")
    except Exception as e:
        print(f"Warning: Error during SubRES file updates: {e}")
        print(f"Error details: {type(e).__name__}: {str(e)}")
        print("Continuing with model creation...")
    
    # Create utilization factor summary table on the Base VS file
    try:
        base_vs_path = dest_folder / "SuppXLS" / "Scen_Base_VS.xlsx"
        if base_vs_path.exists():
            create_utilization_summary_table(df_ember_util, df_irena_util, iso_processor.input_iso, str(base_vs_path))
    except Exception as e:
        print(f"Warning: Could not create utilization summary table: {e}")

    # Copy historical_data sheet to Base VS file and write ATS_Final table to ReportDefs_vervestacks.xlsx
    try:
        base_vs_path = dest_folder / "SuppXLS" / "Scen_Base_VS.xlsx"
        source_iso_path = iso_processor.output_dir / f"VerveStacks_{iso_processor.input_iso}.xlsx"
        if base_vs_path.exists() and source_iso_path.exists():
            from excel_manager import excel_manager
            excel_manager.copy_historical_data(str(source_iso_path), str(base_vs_path),iso_processor.input_iso)
    except Exception as e:
        print(f"Warning: Could not copy historical data to Base VS: {e}")

    # Write RE targets to Base VS file
    try:
        if re_targets_ember_df is not None and not re_targets_ember_df.empty:
            base_vs_path = dest_folder / "SuppXLS" / "Scen_Base_VS.xlsx"
            if base_vs_path.exists():
                from excel_manager import excel_manager
                with excel_manager.workbook(base_vs_path) as wb:
                    if 're_targets' in [ws.name for ws in wb.sheets]:
                        ws = wb.sheets['re_targets']
                        ws.clear()
                    else:
                        ws = wb.sheets.add('re_targets')
                    excel_manager.write_formatted_table(ws, 'B10', re_targets_ember_df,"RE Targets from EMBER")
    except Exception as e:
        print(f"Warning: Could not write RE targets to Base VS: {e}")

    # Write buildrate accumptions for the active iso from vs_mappings file

    _write_buildrate_assumptions(base_vs_path, iso_processor.input_iso)    

    # Write grid capacity data to Base VS file if grid modeling enabled
    if grid_data is not None:
        try:
            base_vs_path = dest_folder / "SuppXLS" / "Scen_Base_VS.xlsx"
            if base_vs_path.exists():
                from excel_manager import excel_manager
                # Merge topology data from solar_wind_data into grid_data
                if solar_wind_data and 'topology_data' in solar_wind_data:
                    grid_data['topology_data'] = solar_wind_data['topology_data']
                excel_manager.write_grid_capacity_to_base_vs(str(base_vs_path), grid_data, iso_processor.input_iso, iso_processor.data_source)
        except Exception as e:
            print(f"Warning: Could not write grid capacity table: {e}")

    # Write geographic data for grid modeling (geolocation and geo_sets)
    if iso_processor.grid_modeling:
        try:
            print("Writing geographic data for grid modeling...")
            from excel_manager import excel_manager
            
            # Generate geographic data from clustered buses
            df_geolocation, df_set_psetco, df_admin_mapping, df_region_com_dimension, df_region_com_geolocation = generate_geographic_data(iso_processor)
            
            if not df_geolocation.empty and not df_set_psetco.empty:
                
                # Write geographic sets to Sets-vervestacks.xlsx
                sets_path = dest_folder / "Sets-vervestacks.xlsx"
                if sets_path.exists():
                    excel_manager.write_grid_geo_sets(str(sets_path), df_set_psetco)
                
                # Write process mapping to ReportDefs_vervestacks.xlsx
                reportdefs_path = dest_folder / "ReportDefs_vervestacks.xlsx"
                if reportdefs_path.exists():
                    excel_manager.write_grid_process_map_geo(str(reportdefs_path), df_set_psetco, df_admin_mapping, df_region_com_dimension)
                    excel_manager.write_grid_geolocation_data(str(reportdefs_path), df_geolocation, df_region_com_geolocation)
                
                print("Geographic data written successfully.")
            else:
                print("No geographic data found to write.")
            
            # Copy grid visualization files to grid_analysis subfolder
            copy_grid_visualization_files(dest_folder, iso_processor.input_iso,iso_processor.data_source)
                
        except Exception as e:
            print(f"Warning: Could not write geographic data: {e}")

    # Initialize section flags for README generation
    section_flags = {
        'timeslice_analysis': False,
        'grid_modeling': getattr(iso_processor, 'grid_modeling', False),
        'ar6_scenarios': True,
        'supply_curves_exist': False,
        'data_source': getattr(iso_processor, 'data_source', 'kan')  # Default to 'kan' if not set
    }
    
    # Copy supply curve charts to renewable_energy subfolder (available for all models)
    try:
        copy_supply_curve_charts(dest_folder, iso_processor.input_iso)
        # Check if supply curve charts exist
        timeslice_output_dir = Path("2_ts_design/outputs") / iso_processor.input_iso
        supply_curve_svg = timeslice_output_dir / f"supply_curves_{iso_processor.input_iso}.svg"
        supply_curve_png = timeslice_output_dir / f"supply_curves_{iso_processor.input_iso}.png"
        if supply_curve_svg.exists() or supply_curve_png.exists():
            section_flags['supply_curves_exist'] = True
    except Exception as e:
        print(f"Warning: Could not copy supply curve charts: {e}")
    
    # Copy clustering visualization charts to source_data subfolder (when supply curves exist)
    if section_flags.get('supply_curves_exist', False):
        try:
            from scenario_drivers.readme_generator import ReadmeGenerator
            readme_gen = ReadmeGenerator(str(Path(__file__).parent / "config" / "readme_documentation.yaml"))
            clustering_copied = readme_gen.copy_clustering_visualizations_to_model_folder(
                iso_processor.input_iso, 
                getattr(iso_processor, 'data_source', 'kan'),
                dest_folder
            )
            if clustering_copied:
                print(f"✅ Clustering visualizations copied for README integration")
            else:
                print(f"ℹ️ No clustering visualizations found for {iso_processor.input_iso}")
        except Exception as e:
            print(f"Warning: Could not copy clustering visualizations: {e}")
    
    # Copy timeslice analysis charts (available when timeslice analysis was run)
    try:
        timeslice_charts_copied = copy_timeslice_charts(dest_folder, iso_processor.input_iso)
        if timeslice_charts_copied:
            section_flags['timeslice_analysis'] = True
            print(f"✅ Timeslice analysis charts found, enabling timeslice section")
        else:
            print(f"ℹ️ No timeslice analysis charts found, skipping timeslice section")
    except Exception as e:
        print(f"Warning: Could not copy timeslice charts: {e}")
    
    # Note: Hydro chart copying moved to after README generation (where charts are created)

    # Create AR6 climate scenarios (if available)
    try:
        print("Creating AR6 climate scenarios...")
        from create_ar6_r10_scenario import create_ar6_r10_scenario
        
        ar6_stats = create_ar6_r10_scenario(
            iso_code=iso_processor.input_iso,
            grid_modeling=getattr(iso_processor, 'grid_modeling', False),
            data_source=getattr(iso_processor, 'data_source', None),
            output_dir=str(dest_folder)  # This will put it in SuppXLS folder
        )
        
        if ar6_stats:
            print(f"✅ AR6 scenarios created for {ar6_stats['r10_region']}")
            print(f"   📊 IEA records: {ar6_stats['iea_records']}")
            print(f"   📈 AR6 records: {ar6_stats['ar6_records']}")
            print(f"   🎭 Categories: {', '.join(ar6_stats['scenario_categories'])}")
        else:
            print("⚠️  AR6 scenarios not available for this region")
            
    except Exception as e:
        print(f"Warning: Could not create AR6 scenarios: {e}")
        print("Continuing with model creation...")

    # Process time-slice data 
    # This must happen AFTER Veda model creation but BEFORE commit
    # so that the time-slice files are included in the git commit
    if not skip_timeslices:
        try:
            print("Processing time-slice data...")
            process_time_slices(iso_processor, tsopt, process_all_tsopts, dest_folder)
            print("Time-slice processing completed successfully.")
        except Exception as e:
            print(f"Warning: Error during time-slice processing: {e}")
            print(f"Error details: {type(e).__name__}: {str(e)}")
            print("Continuing with model creation...")
    else:
        print("Skipping time-slice processing as requested")

    # Generate README.md with complete processing parameters and statistics (after supply curve copying)
    create_model_notes(dest_folder, iso_processor.input_iso, processing_params, section_flags)
    
    # Copy hydro availability charts AFTER README generation (where charts are created)
    try:
        hydro_charts_copied = copy_hydro_charts(dest_folder, iso_processor.input_iso)
        if hydro_charts_copied:
            print(f"✅ Hydro charts copied for README integration")
        else:
            print(f"ℹ️ No hydro charts found (likely no significant hydro capacity)")
    except Exception as e:
        print(f"Warning: Could not copy hydro charts: {e}")


    # Commit the model to git repository (including time-slice files)
    if auto_commit:
        commit_iso_model(
            iso_processor.input_iso, 
            dest_folder.parent, 
            grid_modeling=getattr(iso_processor, 'grid_modeling', False),
            data_source=getattr(iso_processor, 'data_source', None)
        )
    else:
        print("Skipping git operations")

    print(f"Veda model created successfully at: {dest_folder}")
    return dest_folder 