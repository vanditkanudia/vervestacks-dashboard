#!/usr/bin/env python3
"""
Time Slice Processor Module

This module processes time-slice and load shape data for energy system models.
It replicates the functionality of tsplay.ipynb in a structured Python module
that can be integrated into the main VerveStacks pipeline.

Usage:
    from time_slice_processor import TimeSliceProcessor
    processor = TimeSliceProcessor(iso_processor)
    processor.process_time_slices()
"""

import pandas as pd
import duckdb
import os
import shutil
import xlwings as xw
from pathlib import Path
import logging
import numpy as np
import threading
from shared_data_loader import get_shared_loader
from spatial_utils import cluster_id_to_commodity
import sys
from hydro_availability_scenarios.hydro_scenario_selector import get_hydro_capacity_factors



class TimeSliceProcessor:
    """
    Processor for time-slice and load shape data generation.
    Replicates the functionality of tsplay.ipynb in a structured module.
    """
    
    def __init__(self, iso_processor, tsopt='ts12_clu', process_all_tsopts=False, dest_folder=None):
        """
        Initialize the time slice processor.
        
        Args:
            iso_processor: ISOProcessor instance from main pipeline
            tsopt: Time slice option (default: 'ts12_clu') - processed alongside VS_mappings tsopts when process_all_tsopts=False
            process_all_tsopts: If True, process all available ts_* options (ignores tsopt parameter)
            dest_folder: Optional destination folder path. If None, uses default VerveStacks_{ISO} format
        """
        self.iso_processor = iso_processor
        self.input_iso = iso_processor.input_iso
        self.tsopt = tsopt
        self.process_all_tsopts = process_all_tsopts
        self.logger = iso_processor.logger
        
        # Setup paths
        self.models_dir = Path("C:/Veda/Veda/Veda_models/vervestacks_models")
        
        if dest_folder is not None:
            self.dest_folder = Path(dest_folder)
        else:
            # Fallback to original behavior for backward compatibility
            self.dest_folder = self.models_dir / f"VerveStacks_{self.input_iso}"
        self.source_file = "assumptions/tsparameters_scen.xlsx"
        
        # Excel path will be set dynamically based on tsopt
        self.excel_path = None
        
        # Cached data for optimization
        self.cached_weather_data = None
        self.cached_demand_data = None
        self.cached_mapping_data = None
        self.cached_hydro_capacity_factors = None
        
        # Thread lock for Excel operations
        self.excel_lock = threading.Lock()
                
        # Ensure destination directory exists
        self.dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Debug information
        self.logger.info(f"Initialized TimeSliceProcessor for {self.input_iso}")
        if self.process_all_tsopts:
            self.logger.info("Will process all available time-slice options")
        else:
            self.logger.info(f"Will process default time-slice options: {self.tsopt} + all available VS_mappings tsopts")
        
        self.logger.debug(f"Models directory: {self.models_dir}")
        self.logger.debug(f"Destination folder: {self.dest_folder}")
        self.logger.debug(f"Source file: {self.source_file}")
        
        # Validate paths
        self._validate_paths()
    
    def _validate_paths(self):
        """Validate that required paths and files exist."""
        try:
            # Check source file
            if not Path(self.source_file).exists():
                self.logger.warning(f"Source file not found: {self.source_file}")
            
            # Check models directory
            if not self.models_dir.exists():
                self.logger.warning(f"Models directory not found: {self.models_dir}")
                self.logger.info("Will attempt to create directory structure")
            
            # Check destination folder
            if not self.dest_folder.exists():
                self.logger.info(f"Destination folder will be created: {self.dest_folder}")
            
        except Exception as e:
            self.logger.error(f"Error validating paths: {e}")
    
    def get_available_tsopts(self):
        """Get all available time-slice options, filtered for grid modeling if applicable."""
        
        # Check if this is grid modeling mode
        if hasattr(self.iso_processor, 'grid_modeling') and self.iso_processor.grid_modeling and not self.iso_processor.data_source.startswith('syn'):
            self.logger.info("Grid modeling mode detected - filtering to grid-specific tsopts")
            return self.get_grid_modeling_tsopts()
        
        # Original logic for regular models
        try:
            # Load mapping data using the same method as main processing
            mapping_data = self.load_mapping_data()
            
            # Get CSV scenario columns
            csv_df = mapping_data['csv']
            vs_df = mapping_data['vs_mappings']
            
            csv_scenario_cols = [col for col in csv_df.columns if col not in ['description', 'sourcevalue']]
            vs_scenario_cols = [col for col in vs_df.columns if col not in ['description', 'sourcevalue']] if not vs_df.empty else []
            
            # Combine all available options (no duplicates expected since they're from different sources)
            all_available_options = csv_scenario_cols + vs_scenario_cols
            
            # Validate that we have some options
            if not all_available_options:
                self.logger.warning("No time-slice scenario columns found in either source")
                return ['ts_336']  # Fallback
            
            self.logger.info(f"Found {len(all_available_options)} time-slice options:")
            self.logger.info(f"  CSV options: {csv_scenario_cols}")
            self.logger.info(f"  VS_mappings options: {vs_scenario_cols}")
            return all_available_options
            
        except Exception as e:
            self.logger.error(f"Failed to get available time-slice options: {e}")
            self.logger.info("Falling back to legacy timeslice options: ['ts_336']")
            return ['ts_336']  # Fallback to legacy option
    
    def get_vs_mappings_tsopts(self):
        """Get only the VS_mappings time-slice options."""
        try:
            # Load mapping data using the same method as main processing
            mapping_data = self.load_mapping_data()
            vs_df = mapping_data['vs_mappings']
            
            # Get VS_mappings scenario columns
            vs_scenario_cols = [col for col in vs_df.columns if col not in ['description', 'sourcevalue']] if not vs_df.empty else []
            
            self.logger.debug(f"Found VS_mappings tsopts: {vs_scenario_cols}")
            return vs_scenario_cols
            
        except Exception as e:
            self.logger.warning(f"Failed to get VS_mappings tsopts: {e}")
            return ['ts_annual', 'ts_12']  # Fallback to known options
    
    def get_grid_modeling_tsopts(self):
        """Get timeslice options marked for grid modeling from VS_mappings (both stress_periods_config and base_ts_design)."""
        shared_loader = get_shared_loader("data/")
        
        # Get stress-based tsopts from stress_periods_config sheet
        stress_config_df = shared_loader.get_vs_mappings_sheet('stress_periods_config')
        stress_tsopts = stress_config_df[stress_config_df['grid_modeling'] == 'y']['name'].tolist()
        self.logger.info(f"Found {len(stress_tsopts)} stress-based grid modeling tsopts: {stress_tsopts}")
        
        # Get base tsopts from base_ts_design sheet (VS_mappings tsopts like ts_annual, ts_16)
        base_ts_df = shared_loader.get_vs_mappings_sheet('base_ts_design')
        # Get column names excluding description/sourcevalue - these are the tsopt names
        base_tsopts = [col for col in base_ts_df.columns if col not in ['description', 'sourcevalue']]
        self.logger.info(f"Found {len(base_tsopts)} base_ts_design tsopts: {base_tsopts}")
        
        # Combine both sources
        all_grid_tsopts = stress_tsopts + base_tsopts
        
        if not all_grid_tsopts:
            raise ValueError("No grid modeling tsopts found in either stress_periods_config or base_ts_design sheets")
        
        self.logger.info(f"Total grid modeling tsopts: {len(all_grid_tsopts)} = {len(stress_tsopts)} stress + {len(base_tsopts)} base")
        self.logger.info(f"Complete grid modeling tsopt list: {all_grid_tsopts}")
        return all_grid_tsopts
    
    def set_excel_path(self, tsopt):
        """Set the Excel file path for a specific time-slice option."""
        # self.excel_path = self.dest_folder / "SuppXLS" / f"scen_tsparameters_{tsopt}.xlsx"
        self.excel_path = self.dest_folder / "SuppXLS/Scen_Par-AR6_R10.xlsx"
        self.logger.debug(f"Set Excel path for {tsopt}: {self.excel_path}")
    
    def setup_excel_file(self):
        """Setup Excel file by copying template."""
        try:
            # Ensure SuppXLS directory exists
            suppxls_dir = self.dest_folder / "SuppXLS"
            suppxls_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy template file with thread safety
            with self.excel_lock:
                shutil.copy2(self.source_file, self.excel_path)
                self.logger.info(f"Copied template file to {self.excel_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Excel file: {e}")
            raise
    
    def load_weather_data(self):
        """Load clustered weather data for the specific ISO (Phase 1 - done once)."""
        try:
            # Use data_source from iso_processor for consistent path resolution
            base_path = Path(f"1_grids/output_{self.iso_processor.data_source}/{self.input_iso}")
                    
            # Construct path to country-specific clustered data
            cluster_path = base_path / "cluster_solar_atlite_timeseries.parquet"
             # Load the clustered data
            df_weather_solar = pd.read_parquet(cluster_path)
            
            cluster_path = base_path / "cluster_wind_atlite_timeseries.parquet"
            # Load the clustered data
            df_weather_wind = pd.read_parquet(cluster_path)
            
            df_weather_iso = pd.merge(
                df_weather_solar,
                df_weather_wind,
                on=["cluster_id", "month", "day", "hour"],
                how="outer"
            )
            
            cluster_path = base_path / "cluster_offwind_atlite_timeseries.parquet"
            
            if cluster_path.exists():
                # Load the clustered data
                df_weather_offwind = pd.read_parquet(cluster_path)
                df_weather_iso = pd.merge(
                    df_weather_iso,
                    df_weather_offwind,
                    on=["cluster_id", "month", "day", "hour"],
                    how="outer"
                )

            # Ensure hour column is properly formatted
            df_weather_iso['hour'] = df_weather_iso['hour'].astype(int)
            
            self.logger.info(f"✅ Successfully loaded clustered weather data for {self.input_iso}: {len(df_weather_iso)} records from {self.iso_processor.data_source} clustering")
            return df_weather_iso
            
        except Exception as e:
            self.logger.error(f"Failed to load weather data: {e}")
            return None
    
    def load_mapping_data(self):
        """Load time-slice mapping data (NO CACHING - always reloads from disk). Returns separate DataFrames."""
        try:
            # Try new CSV format first
            tsdesign_csv_path = Path(f"2_ts_design/outputs/{self.input_iso}/tsdesign_{self.input_iso}.csv")
            
            if tsdesign_csv_path.exists():
                csv_df = pd.read_csv(tsdesign_csv_path)
                self.logger.info(f"Loaded CSV time-slice mapping data (NO CACHE): {tsdesign_csv_path}")
                
                # Load VS_mappings data separately
                shared_loader = get_shared_loader("data/")
                vs_df = shared_loader.get_vs_mappings_sheet("base_ts_design")
                self.logger.info(f"Loaded VS_mappings time-slice data (NO CACHE): base_ts_design sheet")
                
                # Return both DataFrames separately
                return {
                    'csv': csv_df,
                    'vs_mappings': vs_df
                }
            else:
                # Fallback to legacy Excel format (only CSV-style data available)
                self.logger.warning(f"tsdesign CSV not found: {tsdesign_csv_path}")
                self.logger.info("Falling back to legacy Excel format: assumptions/VS_Mappings.xlsx")
                legacy_df = pd.read_excel("assumptions/VS_Mappings.xlsx", sheet_name="base_ts_design")
                self.logger.info("Loaded time-slice mapping data from Excel (legacy)")
                
                # For legacy, return empty vs_mappings since it's not available
                return {
                    'csv': legacy_df,
                    'vs_mappings': pd.DataFrame()  # Empty DataFrame
                }
            
        except Exception as e:
            self.logger.error(f"Failed to load mapping data: {e}")
            raise
    
    def load_and_process_demand_data(self):
        """Load and process demand data into sector shapes (Phase 1 - done once)."""
        try:
            # Initialize shared data loader
            shared_loader = get_shared_loader("data/")
            
            # Load IEA data
            iea_data = pd.read_csv('data/IEAData.csv')
            in_region_map = shared_loader.get_vs_mappings_sheet('kinesys_region_map')
            
            # Get IEA region for the ISO
            filtered_ieareg = in_region_map.loc[in_region_map['iso'] == self.input_iso, 'IEAReg']
            input_ieareg = filtered_ieareg.iloc[0] if not filtered_ieareg.empty else None
            
            if not input_ieareg or (isinstance(input_ieareg, float) and pd.isna(input_ieareg)):
                self.logger.warning(f"IEAReg not found for {self.input_iso}, skipping demand processing")
                return None
            
            # Load ERA5 load curves (using shared loader)
            in_era_load_curves_df = shared_loader.get_era5_demand_data()
            in_era_load_curves_df = in_era_load_curves_df.merge(
                in_region_map[['iso', '2-alpha code']], 
                left_on='Country', 
                right_on='2-alpha code', 
                how='inner'
            )
            iso_load_curves_df = in_era_load_curves_df[
                (in_era_load_curves_df['weather_year'] == 2013) & 
                (in_era_load_curves_df['iso'] == self.input_iso)
            ]

            # Increment the hour field by 1 so that it ranges from 1-24 instead of 0-23
            # Handles both integer and string (e.g., '01') values
            # Use .loc to avoid SettingWithCopyWarning
            iso_load_curves_df = iso_load_curves_df.copy()
            iso_load_curves_df.loc[:, 'Hour'] = iso_load_curves_df['Hour'].apply(lambda x: int(x) + 1 if pd.notnull(x) else x)

            
            # Calculate sector shares
            iea_max_year = iea_data['Year'].max()
            elec_flows = ['RESIDENT', 'COMMPUB', 'TOTIND']
            iea_filtered = iea_data[
                (iea_data['Product'] == 'ELECTR') & 
                (iea_data['Flow'].isin(elec_flows)) & 
                (iea_data['Country'] == input_ieareg)
            ]
            
            flows_df = (
                iea_filtered[iea_filtered['Year'] == iea_max_year]
                .copy()
                .rename(columns={'Flow': 'Sector'})
            )
            flows_df['TJ'] = flows_df['Value'].astype(float)
            
            totelec_df = (
                flows_df.groupby(['Country', 'Year'], as_index=False)['TJ']
                .sum()
                .rename(columns={'TJ': 'TotElec'})
            )
            
            # Merge and calculate shares
            merged_elc_flows_df = pd.merge(flows_df, totelec_df, on=['Country', 'Year'], how='inner')
            merged_elc_flows_df['Share'] = merged_elc_flows_df['TJ'] / merged_elc_flows_df['TotElec']
            
            # Map sectors
            merged_elc_flows_df['Sector'] = merged_elc_flows_df['Sector'].str.lower().map({
                'resident': 'RES',
                'totind': 'IND',
            }).fillna('COM')
            
            iea_shares_df = pd.merge(
                in_region_map[['IEAReg', '2-alpha code']], 
                merged_elc_flows_df,
                left_on='IEAReg', 
                right_on='Country', 
                how='inner'
            )
            iea_shares_df.rename(columns={'2-alpha code': 'CCode'}, inplace=True)
            iea_shares_df = iea_shares_df[['Country', 'CCode', 'Share', 'Sector', 'TotElec']]
            
            # Calculate granular MW data
            era_annual_mw_avg_df = iso_load_curves_df.groupby('Country', as_index=False)['MW'].mean()
            era_monthly_mw_avg_df = iso_load_curves_df.groupby(['Country', 'Month'], as_index=False)['MW'].mean()
            era_days_mw_avg_df = iso_load_curves_df.groupby(['Country', 'Month', 'Day'], as_index=False)['MW'].mean()
            era_hourly_mw_avg_df = iso_load_curves_df.groupby(['Country', 'Month', 'Day', 'Hour'], as_index=False)['MW'].mean()
            
            ann_mon_mw_merged_df = pd.merge(era_annual_mw_avg_df, era_monthly_mw_avg_df, on='Country', suffixes=('_ann', '_mon'))
            era_daily_mw_merged_df = pd.merge(ann_mon_mw_merged_df, era_days_mw_avg_df, on=['Country', 'Month'], suffixes=('', '_day'))
            era_daily_mw_merged_df.rename(columns={'MW': 'MW_day'}, inplace=True)
            era_granual_mw_df = pd.merge(era_daily_mw_merged_df, era_hourly_mw_avg_df, on=['Country', 'Month', 'Day'], suffixes=('', '_hr'))
            era_granual_mw_df.rename(columns={'MW': 'MW_hr'}, inplace=True)
            
            # Return processed demand data
            return {
                'era_granual_mw_df': era_granual_mw_df,
                'iea_shares_df': iea_shares_df,
                'iso_load_curves_df': iso_load_curves_df
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load and process demand data: {e}")
            return None
    
    def export_hourly_data_to_csv(self):
        """Export hourly weather and demand data to separate CSV files."""
        try:
            # Create output directory for CSV files
            csv_output_dir = Path(self.iso_processor.output_dir) / "source_data"
            csv_output_dir.mkdir(exist_ok=True)
            
            self.logger.info(f"Starting export of hourly data to CSV files in {csv_output_dir}")
            
            # Export hourly weather data (sorted by month-day-hour)
            if self.cached_weather_data is not None:
                try:
                    # Sort by month, day, hour
                    weather_data_sorted = self.cached_weather_data.sort_values(['month', 'day', 'hour']).reset_index(drop=True)
                    
                    # Export to CSV
                    weather_csv_path = csv_output_dir / f"{self.input_iso}_hourly_resource_shapes.csv"
                    weather_data_sorted.to_csv(weather_csv_path, index=False)
                    
                    self.logger.info(f"Exported sorted hourly weather data to {weather_csv_path}")
                    self.logger.info(f"Weather data shape: {weather_data_sorted.shape}")
                    
                except Exception as weather_error:
                    self.logger.error(f"Failed to export weather data: {weather_error}")
            
            # Export hourly demand data (iemm_sector_loads_df)
            if self.cached_demand_data is not None and 'iso_load_curves_df' in self.cached_demand_data:
                try:
                    # Create iemm_sector_loads_df from the cached data
                    iemm_sector_loads_df = self._create_iemm_sector_loads_df()
                    if iemm_sector_loads_df is not None:
                        # Export to CSV
                        demand_csv_path = csv_output_dir / f"{self.input_iso}_hourly_demand_data.csv"
                        iemm_sector_loads_df.to_csv(demand_csv_path, index=False)
                        
                        self.logger.info(f"Exported hourly demand data to {demand_csv_path}")
                        self.logger.info(f"Demand data shape: {iemm_sector_loads_df.shape}")
                    else:
                        self.logger.warning("iemm_sector_loads_df is None, skipping export")
                        
                except Exception as demand_error:
                    self.logger.error(f"Failed to export demand data: {demand_error}")
                    import traceback
                    self.logger.error(f"Demand export traceback: {traceback.format_exc()}")
            
            # Export raw iso_load_curves_df if available (additional data)
            if self.cached_demand_data is not None and 'iso_load_curves_df' in self.cached_demand_data:
                try:
                    iso_load_curves_df = self.cached_demand_data['iso_load_curves_df']
                    raw_demand_csv_path = csv_output_dir / f"{self.input_iso}_raw_load_curves.csv"
                    iso_load_curves_df.to_csv(raw_demand_csv_path, index=False)
                    
                    self.logger.info(f"Exported raw load curves data to {raw_demand_csv_path}")
                    self.logger.info(f"Raw load curves shape: {iso_load_curves_df.shape}")
                    
                except Exception as raw_error:
                    self.logger.error(f"Failed to export raw load curves: {raw_error}")
            
            self.logger.info(f"Completed hourly data export to {csv_output_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to export hourly data to CSV: {e}")
            import traceback
            self.logger.error(f"Export traceback: {traceback.format_exc()}")
    
    def _create_iemm_sector_loads_df(self):
        """Create iemm_sector_loads_df from cached demand data."""
        try:
            if self.cached_demand_data is None or 'iso_load_curves_df' not in self.cached_demand_data:
                self.logger.warning("No iso_load_curves_df in cached demand data")
                return None
            
            # Get the base load curves data
            iso_load_curves_df = self.cached_demand_data['iso_load_curves_df'].copy()
            
            # Ensure MW column is numeric and handle any string values
            iso_load_curves_df['MW'] = pd.to_numeric(iso_load_curves_df['MW'], errors='coerce')
            
            # Check for any remaining NaN values and fill them
            if iso_load_curves_df['MW'].isna().any():
                self.logger.warning(f"Found {iso_load_curves_df['MW'].isna().sum()} NaN values in MW column, filling with 0")
                iso_load_curves_df['MW'] = iso_load_curves_df['MW'].fillna(0)
            
            # Create a more realistic sector breakdown
            # For hourly export, we'll create simplified sector loads
            # Industry sector (30% of total load)
            industry_df = iso_load_curves_df[['Country', 'Month', 'Day', 'Hour', 'MW']].copy()
            industry_df['Sector'] = 'elc_industry'
            industry_df['MW'] = industry_df['MW'] * 0.3  # 30% for industry
            
            # Commercial sector (35% of total load)
            commercial_df = iso_load_curves_df[['Country', 'Month', 'Day', 'Hour', 'MW']].copy()
            commercial_df['Sector'] = 'elc_commercial'
            commercial_df['MW'] = commercial_df['MW'] * 0.35  # 35% for commercial
            
            # Residential sector (35% of total load)
            residential_df = iso_load_curves_df[['Country', 'Month', 'Day', 'Hour', 'MW']].copy()
            residential_df['Sector'] = 'elc_residential'
            residential_df['MW'] = residential_df['MW'] * 0.35  # 35% for residential
            
            # Combine all sectors
            sector_load_dfs = [industry_df, commercial_df, residential_df]
            iemm_sector_loads_df = pd.concat(sector_load_dfs, ignore_index=True)
            
            # Add normalized load column with robust error handling
            for sector in ['elc_industry', 'elc_commercial', 'elc_residential']:
                try:
                    sector_data = iemm_sector_loads_df[iemm_sector_loads_df['Sector'] == sector]
                    if len(sector_data) == 0:
                        self.logger.warning(f"No data found for sector {sector}")
                        continue
                    
                    avg_mw = sector_data['MW'].mean()
                    self.logger.debug(f"Sector {sector}: avg_mw = {avg_mw}, type = {type(avg_mw)}")
                    
                    if pd.notna(avg_mw) and avg_mw != 0:  # Check for valid average
                        iemm_sector_loads_df.loc[iemm_sector_loads_df['Sector'] == sector, 'LoadNormalized'] = (
                            iemm_sector_loads_df.loc[iemm_sector_loads_df['Sector'] == sector, 'MW'] / avg_mw
                        )
                    else:
                        self.logger.warning(f"Invalid average MW for sector {sector}: {avg_mw}")
                        iemm_sector_loads_df.loc[iemm_sector_loads_df['Sector'] == sector, 'LoadNormalized'] = 1.0
                        
                except Exception as sector_error:
                    self.logger.error(f"Error processing sector {sector}: {sector_error}")
                    iemm_sector_loads_df.loc[iemm_sector_loads_df['Sector'] == sector, 'LoadNormalized'] = 1.0
            
            # Convert column names to lowercase
            iemm_sector_loads_df.columns = [col.lower() for col in iemm_sector_loads_df.columns]
            
            # Pivot the sector column and drop loadnormalized column
            # First, drop the loadnormalized column
            if 'loadnormalized' in iemm_sector_loads_df.columns:
                iemm_sector_loads_df = iemm_sector_loads_df.drop('loadnormalized', axis=1)
            
            # Pivot the sector column to create separate columns for each sector
            if 'sector' in iemm_sector_loads_df.columns:
                # Create pivot table with country, month, day, hour as index and sector as columns
                pivot_df = iemm_sector_loads_df.pivot_table(
                    index=['country', 'month', 'day', 'hour'],
                    columns='sector',
                    values='mw',
                    aggfunc='first'  # Use first value in case of duplicates
                ).reset_index()
                
                # Flatten column names if they are multi-level
                if isinstance(pivot_df.columns, pd.MultiIndex):
                    pivot_df.columns = [col[1] if col[1] else col[0] for col in pivot_df.columns]
                
                iemm_sector_loads_df = pivot_df
            
            self.logger.info(f"Successfully created pivoted iemm_sector_loads_df with {len(iemm_sector_loads_df)} records")
            return iemm_sector_loads_df
            
        except Exception as e:
            self.logger.error(f"Failed to create iemm_sector_loads_df: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _add_charts_to_excel_with_workbook(self, wb):
        """Add line charts to the Excel file using an already open workbook."""
        try:
            # Add resource shapes chart (solar and wind only)
            if "Hourly_resource_shapes" in [s.name for s in wb.sheets]:
                ws_weather = wb.sheets["Hourly_resource_shapes"]
                
                # Get the data range for resource chart
                last_row = ws_weather.range('A' + str(ws_weather.cells.last_cell.row)).end('up').row
                if last_row > 1:
                    # Find columns for com_fr_solar and com_fr_wind
                    headers = ws_weather.range('A1').expand('right').value
                    solar_col = None
                    wind_col = None
                    
                    for i, header in enumerate(headers):
                        if header == 'com_fr_solar':
                            solar_col = chr(65 + i)  # Convert to column letter
                        elif header == 'com_fr_wind':
                            wind_col = chr(65 + i)  # Convert to column letter
                    
                    if solar_col and wind_col:
                        # Create chart for solar and wind data only
                        chart_range = f"A1:{wind_col}{min(last_row, 1000)}"  # Include time columns and wind column
                        chart = ws_weather.charts.add()
                        chart.set_source_data(ws_weather.range(chart_range))
                        chart.chart_type = 'line'
                        chart.name = "Resource_Shapes_Chart"
                        chart.top = 10
                        chart.left = 400
                        chart.width = 400
                        chart.height = 300
                        
                        # Set chart title - use a safer approach
                        try:
                            chart.api.ChartTitle.Text = f"Resource Shapes (Solar & Wind) - {self.input_iso}"
                        except:
                            # Alternative approach if ChartTitle is not available
                            pass
                    else:
                        self.logger.warning(f"Could not find com_fr_solar or com_fr_wind columns in Hourly_resource_shapes sheet")
            
            # Add demand data chart with 3 lines (sectors)
            if "Hourly_Demand_Data" in [s.name for s in wb.sheets]:
                ws_demand = wb.sheets["Hourly_Demand_Data"]
                
                # Get the data range for demand chart
                last_row = ws_demand.range('A' + str(ws_demand.cells.last_cell.row)).end('up').row
                if last_row > 1:
                    # Find columns for the 3 sectors
                    headers = ws_demand.range('A1').expand('right').value
                    sector_cols = []
                    
                    for i, header in enumerate(headers):
                        if header in ['elc_industry', 'elc_commercial', 'elc_residential']:
                            sector_cols.append(chr(65 + i))  # Convert to column letter
                    
                    if len(sector_cols) >= 3:
                        # Create chart for sector loads
                        chart_range = f"A1:{sector_cols[-1]}{min(last_row, 1000)}"  # Include time columns and last sector column
                        chart = ws_demand.charts.add()
                        chart.set_source_data(ws_demand.range(chart_range))
                        chart.chart_type = 'line'
                        chart.name = "Demand_Data_Chart"
                        chart.top = 10
                        chart.left = 400
                        chart.width = 400
                        chart.height = 300
                        
                        # Set chart title - use a safer approach
                        try:
                            chart.api.ChartTitle.Text = f"Hourly Demand by Sector - {self.input_iso}"
                        except:
                            # Alternative approach if ChartTitle is not available
                            pass
                    else:
                        self.logger.warning(f"Could not find all sector columns in Hourly_Demand_Data sheet")
            
            self.logger.info(f"Added charts to workbook")
            
        except Exception as e:
            self.logger.error(f"Failed to add charts to workbook: {e}")

    # def _add_charts_to_excel(self, excel_path):
    #     """Add line charts to the Excel file (legacy method for backward compatibility)."""
    #     try:
    #         with self.excel_lock:
    #             app = xw.App(visible=False)
    #             app.display_alerts = False  # Suppress Excel alerts and sounds
    #             try:
    #                 wb = xw.Book(excel_path)
    #                 self._add_charts_to_excel_with_workbook(wb)
    #                 wb.save()
    #                 wb.close()
    #             finally:
    #                 app.quit()
                    
    #         self.logger.info(f"Added charts to {excel_path}")
            
    #     except Exception as e:
    #         self.logger.error(f"Failed to add charts to Excel: {e}")
    
    def create_time_slice_mapping(self, df_resource_shapes, mapping_data_dict, tsopt=None):
        """Create time-slice mapping for a specific option (Phase 2)."""
        try:
            if tsopt is None:
                tsopt = self.tsopt
            
            # Dynamically choose appropriate DataFrame based on column availability
            # Try CSV first (stress-based and clustering configs), then VS_mappings (legacy configs)
            if tsopt in mapping_data_dict['csv'].columns:
                aopt_timeslice_df = mapping_data_dict['csv']
                self.logger.info(f"Using CSV mapping data for {tsopt}")
            elif tsopt in mapping_data_dict['vs_mappings'].columns:
                aopt_timeslice_df = mapping_data_dict['vs_mappings']
                self.logger.info(f"Using VS_mappings data for {tsopt}")
            else:
                raise ValueError(f"Timeslice option '{tsopt}' not found in either CSV or VS_mappings data. Available CSV options: {list(mapping_data_dict['csv'].columns)}, Available VS_mappings options: {list(mapping_data_dict['vs_mappings'].columns)}")
            
            # Get distinct times from weather data
            distinct_times = df_resource_shapes[['month', 'day', 'hour']].drop_duplicates().sort_values(['month', 'day', 'hour'])
            
            # Filter time-slice mapping data
            aopt_month = aopt_timeslice_df[aopt_timeslice_df['description'] == 'month']
            aopt_hour = aopt_timeslice_df[aopt_timeslice_df['description'] == 'hour']
            aopt_adv = aopt_timeslice_df[aopt_timeslice_df['description'] == 'adv']
            
            # Validate that the tsopt column exists in month and hour mappings
            if tsopt not in aopt_month.columns:
                raise ValueError(f"Column '{tsopt}' not found in month mappings. Available columns: {list(aopt_month.columns)}")
            if tsopt not in aopt_hour.columns:
                raise ValueError(f"Column '{tsopt}' not found in hour mappings. Available columns: {list(aopt_hour.columns)}")
            
            # Join distinct_times with month mapping
            joined_df = pd.merge(
                distinct_times.assign(month=distinct_times['month'].astype(int), hour=distinct_times['hour'].astype(int)),
                aopt_month.assign(sourcevalue=aopt_month['sourcevalue'].astype(int))[['sourcevalue', tsopt]],
                left_on='month',
                right_on='sourcevalue',
                how='left'
            )
            joined_df = joined_df.rename(columns={tsopt: "season"})
            
            # Join with hour mapping
            joined_df = pd.merge(
                joined_df,
                aopt_hour.assign(sourcevalue=aopt_hour['sourcevalue'].astype(int))[['sourcevalue', tsopt]],
                left_on=['hour'],
                right_on=['sourcevalue'],
                how='left'
            )
            joined_df = joined_df.rename(columns={tsopt: "daynite"})
            joined_df['weekly'] = 'a'
            
            # Process advanced weekly mapping
            # Group consecutive rows with same sourcevalue to create date ranges
            aopt_adv_grouped = {}
            
            # Check if tsopt column exists in advanced mappings (might not exist for all scenarios)
            if tsopt not in aopt_adv.columns:
                self.logger.warning(f"Column '{tsopt}' not found in advanced mappings. Skipping advanced period processing.")
                self.logger.warning(f"Available columns in advanced mappings: {list(aopt_adv.columns)}")
            else:
                for idx, row in aopt_adv.iterrows():
                    sourcevalue = row['sourcevalue']
                    option1_value = row[tsopt]
                    
                    # Skip empty, null, or whitespace-only values (supports clustering-only configs)
                    if pd.isna(option1_value) or str(option1_value).strip() == '':
                        continue
                    
                    if sourcevalue not in aopt_adv_grouped:
                        aopt_adv_grouped[sourcevalue] = []
                    aopt_adv_grouped[sourcevalue].append(str(option1_value))
            
            # Process each sourcevalue group
            for sourcevalue, date_list in aopt_adv_grouped.items():
                try:
                    if len(date_list) == 1:
                        # Single date - check if it contains 'to' for explicit range
                        option1_value = date_list[0]
                        if 'to' in str(option1_value):
                            # Range format: "01-21 to 02-15"
                            start_str, end_str = str(option1_value).split(' to ')
                            start_month, start_day = map(int, start_str.split('-'))
                            end_month, end_day = map(int, end_str.split('-'))
                        else:
                            # Single date format: "01-21"
                            start_month, start_day = map(int, str(option1_value).split('-'))
                            end_month, end_day = start_month, start_day
                    elif len(date_list) == 2:
                        # Two dates - interpret as range from first to second
                        start_str, end_str = date_list[0], date_list[1]
                        start_month, start_day = map(int, start_str.split('-'))
                        end_month, end_day = map(int, end_str.split('-'))
                        
                        # Check if start comes after end chronologically
                        start_date = (start_month, start_day)
                        end_date = (end_month, end_day)
                        
                        # Determine if this is a valid year wrap-around or invalid same-year case
                        if start_month > end_month:
                            # This is a year wrap-around case (e.g., 12-20 to 01-15) - always valid
                            pass  # Continue processing normally
                        elif start_month == end_month and start_day > end_day:
                            # Same month, but start day after end day (e.g., 03-15 to 03-10) - invalid
                            self.logger.info(f"Skipping sourcevalue '{sourcevalue}': start date {start_month:02d}-{start_day:02d} comes after end date {end_month:02d}-{end_day:02d} within same month (no adv records will be created)")
                            continue  # Skip this sourcevalue entirely
                        elif start_month < end_month and start_date > end_date:
                            # Different months, start after end in same year (e.g., 05-20 to 03-10) - invalid  
                            self.logger.info(f"Skipping sourcevalue '{sourcevalue}': start date {start_month:02d}-{start_day:02d} comes after end date {end_month:02d}-{end_day:02d} within same year (no adv records will be created)")
                            continue  # Skip this sourcevalue entirely
                            
                        self.logger.info(f"Processing date range for {sourcevalue}: {start_month:02d}-{start_day:02d} to {end_month:02d}-{end_day:02d}")
                    else:
                        # Multiple dates - use first and last as range
                        sorted_dates = sorted(date_list)
                        start_str, end_str = sorted_dates[0], sorted_dates[-1]
                        start_month, start_day = map(int, start_str.split('-'))
                        end_month, end_day = map(int, end_str.split('-'))
                        
                        self.logger.info(f"Processing multi-date range for {sourcevalue}: {start_month:02d}-{start_day:02d} to {end_month:02d}-{end_day:02d} (from {len(date_list)} dates)")
                        
                    # Update weekly column for matching (month, day) combinations
                    if start_month == end_month:
                        mask = (joined_df['month'] == start_month) & (joined_df['day'] >= start_day) & (joined_df['day'] <= end_day)
                    else:
                        # Handle cross-month ranges (including year wrap-around)
                        if start_month > end_month:
                            # Year wrap-around case (e.g., 12-20 to 01-15)
                            mask = (
                                ((joined_df['month'] == start_month) & (joined_df['day'] >= start_day)) |
                                ((joined_df['month'] > start_month) | (joined_df['month'] < end_month)) |
                                ((joined_df['month'] == end_month) & (joined_df['day'] <= end_day))
                            )
                        else:
                            # Normal cross-month case
                            mask = (
                                ((joined_df['month'] == start_month) & (joined_df['day'] >= start_day)) |
                                ((joined_df['month'] > start_month) & (joined_df['month'] < end_month)) |
                                ((joined_df['month'] == end_month) & (joined_df['day'] <= end_day))
                            )
                    
                    # Count how many records will be updated
                    matching_records = joined_df[mask]
                    unique_days = matching_records[['month', 'day']].drop_duplicates()
                    self.logger.info(f"Setting weekly='{sourcevalue}' for {len(unique_days)} days ({len(matching_records)} hourly records)")
                    
                    joined_df.loc[mask, 'weekly'] = sourcevalue
                    
                except Exception as e:
                    self.logger.warning(f"Error processing sourcevalue '{sourcevalue}' with dates {date_list}: {e}")
            
            # Update daynite with month-hour when weekly != 'a'
            mask = joined_df['weekly'] != 'a'
            joined_df.loc[mask, 'daynite'] = (
                joined_df.loc[mask, 'month'].astype(int).astype(str).str.zfill(2) +
                joined_df.loc[mask, 'day'].astype(int).astype(str).str.zfill(2) +
                'h' +
                joined_df.loc[mask, 'hour'].astype(int).astype(str).str.zfill(2)
            )
            
            # Return joined_df with time slice mappings (solar/wind computed later in process_resource_profiles)
            final_for_aggregations_df = joined_df[['month', 'day', 'hour', 'season', 'weekly', 'daynite']]
            
            self.logger.info(f"Created time-slice mapping for {tsopt} with {len(final_for_aggregations_df)} records")
            return final_for_aggregations_df
            
        except Exception as e:
            self.logger.error(f"Failed to create time-slice mapping: {e}")
            raise
    
    def create_time_slice_definitions(self, final_for_aggregations_df):
        """Create time-slice definitions for a specific option (Phase 2)."""
        try:
            # Get distinct combinations
            distinct_df = final_for_aggregations_df[['season', 'weekly', 'daynite']].drop_duplicates().reset_index(drop=True)
            # Get unique values for each column as separate DataFrames
            season_unique = pd.DataFrame({'season': distinct_df['season'].unique()})
            weekly_unique = pd.DataFrame({'weekly': distinct_df['weekly'].unique()})
            daynite_unique = pd.DataFrame({'daynite': distinct_df['daynite'].unique()})

            # Sort each DataFrame by its column
            season_unique_sorted = season_unique.sort_values(by='season').reset_index(drop=True)
            weekly_unique_sorted = weekly_unique.sort_values(by='weekly').reset_index(drop=True)
            daynite_unique_sorted = daynite_unique.sort_values(by='daynite').reset_index(drop=True)


            # Get unique seasons for each weekly value
            season_by_weekly = distinct_df.groupby('weekly')['season'].unique().apply(list).reset_index()

            season_by_weekly['wparent'] = season_by_weekly['season'].apply(lambda x: ','.join([str(s) for s in x if pd.notnull(s)]))
            season_by_weekly = season_by_weekly.drop(columns=['season'])


            # Get unique weekly for each daynite
            weekly_by_daynite = distinct_df.groupby('daynite')['weekly'].unique().apply(list).reset_index()
            weekly_by_daynite['dparent'] = weekly_by_daynite['weekly'].apply(lambda x: ','.join([str(w) for w in x if pd.notnull(w)]))
            weekly_by_daynite = weekly_by_daynite.drop(columns=['weekly'])


            # Merge into a single DataFrame for export
            # We'll concatenate them horizontally (side by side), aligning by index
            merged_unique = pd.concat([season_unique_sorted, weekly_unique_sorted, daynite_unique_sorted], axis=1)

            # Join season_by_weekly with merged_unique on 'weekly'
            merged_unique = pd.merge(
                merged_unique,
                season_by_weekly[['weekly','wparent']],
                on='weekly',
                how='left'
            )

            # Join weekly_by_daynite with merged_unique on 'daynite'
            merged_unique = pd.merge(
                merged_unique,
                weekly_by_daynite[['daynite','dparent']],
                on='daynite',
                how='left'
            )

            return merged_unique
            
        except Exception as e:
            self.logger.error(f"Failed to create time-slice definitions: {e}")
            raise
    
    def write_excel_sheet(self, sheet_name, data_df, label=None):
        """Write data to Excel sheet with thread safety (Phase 2)."""
        try:
            with self.excel_lock:
                app = xw.App(visible=False)
                app.display_alerts = False  # Suppress Excel alerts and sounds
                try:
                    wb = xw.Book(self.excel_path)
                    
                    # Check if sheet exists
                    if sheet_name in [s.name for s in wb.sheets]:
                        ws = wb.sheets[sheet_name]
                    else:
                        ws = wb.sheets.add(sheet_name, after=wb.sheets[-1])
                    
                    # Write data
                    ws.range("B3").options(index=False).value = data_df
                    
                    # Write label if provided
                    if label:
                        ws.range("B2").value = label
                    
                    wb.save()
                    wb.close()
                finally:
                    app.quit()
            
        except Exception as e:
            self.logger.error(f"Failed to write Excel sheet {sheet_name}: {e}")
            raise
    
    def process_resource_profiles(self, df_resource_shapes, final_for_aggregations_df, tsopt):
        """Process resource profiles for a specific option (Phase 2)."""
        try:
            # Perform the join on 'month', 'day', 'hour'
            merged_df = pd.merge(
                df_resource_shapes,
                final_for_aggregations_df,
                on=['month', 'day', 'hour'],
                how='inner'
            )
            
            # Check if com_fr_offwind column exists, fallback to com_fr_wind if missing
            if 'com_fr_offwind' not in df_resource_shapes.columns:
                df_resource_shapes['com_fr_offwind'] = df_resource_shapes['com_fr_wind']


            summed_df_solar = merged_df.groupby(['cluster_id','season', 'weekly', 'daynite'])['com_fr_solar'].sum().reset_index()
            summed_df_windon = merged_df.groupby(['cluster_id','season', 'weekly', 'daynite'])['com_fr_wind'].sum().reset_index()
            summed_df_windoff = merged_df.groupby(['cluster_id','season', 'weekly', 'daynite'])['com_fr_offwind'].sum().reset_index()

            
            # For solar
            solar_timeslice_df = summed_df_solar.copy()
            solar_timeslice_df['timeslice'] = solar_timeslice_df['season'].astype(str) + solar_timeslice_df['weekly'].astype(str) + solar_timeslice_df['daynite'].astype(str)
            
            solar_timeslice_df['commodity'] = solar_timeslice_df['cluster_id'].apply(lambda x: cluster_id_to_commodity(x, 'spv', 'commodity'))
            solar_timeslice_df = solar_timeslice_df[['commodity','timeslice', 'com_fr_solar']].rename(columns={'com_fr_solar': 'com_fr'})
            solar_timeslice_df['process'] = 'IMPNRGZ'

            # Remove solar commodity rows where com_fr sums to 0 across all timeslices
            solar_nonzero_commodities = solar_timeslice_df.groupby('commodity')['com_fr'].sum()
            nonzero_commodities = solar_nonzero_commodities[solar_nonzero_commodities != 0].index
            solar_timeslice_df = solar_timeslice_df[solar_timeslice_df['commodity'].isin(nonzero_commodities)]

            # For wind
            wind_timeslice_df = summed_df_windon.copy()
            wind_timeslice_df['timeslice'] = wind_timeslice_df['season'].astype(str) + wind_timeslice_df['weekly'].astype(str) + wind_timeslice_df['daynite'].astype(str)
            

            wind_timeslice_df['commodity'] = wind_timeslice_df['cluster_id'].apply(lambda x: cluster_id_to_commodity(x, 'won', 'commodity'))
            wind_timeslice_df = wind_timeslice_df[['commodity','timeslice', 'com_fr_wind']].rename(columns={'com_fr_wind': 'com_fr'})
            wind_timeslice_df['process'] = 'IMPNRGZ'
            
            # Remove wind commodity rows where com_fr sums to 0 across all timeslices
            wind_nonzero_commodities = wind_timeslice_df.groupby('commodity')['com_fr'].sum()
            nonzero_commodities = wind_nonzero_commodities[wind_nonzero_commodities != 0].index
            wind_timeslice_df = wind_timeslice_df[wind_timeslice_df['commodity'].isin(nonzero_commodities)]

            # For windoff
            windoff_timeslice_df = summed_df_windoff.copy()
            windoff_timeslice_df['timeslice'] = windoff_timeslice_df['season'].astype(str) + windoff_timeslice_df['weekly'].astype(str) + windoff_timeslice_df['daynite'].astype(str)
            
            windoff_timeslice_df['commodity'] = windoff_timeslice_df['cluster_id'].apply(lambda x: cluster_id_to_commodity(x, 'wof', 'commodity'))
            windoff_timeslice_df = windoff_timeslice_df[['commodity','timeslice', 'com_fr_offwind']].rename(columns={'com_fr_offwind': 'com_fr'})
            windoff_timeslice_df['process'] = 'IMPNRGZ'

            # Remove windoff commodity rows where com_fr sums to 0 across all timeslices
            windoff_nonzero_commodities = windoff_timeslice_df.groupby('commodity')['com_fr'].sum()
            nonzero_commodities = windoff_nonzero_commodities[windoff_nonzero_commodities != 0].index
            windoff_timeslice_df = windoff_timeslice_df[windoff_timeslice_df['commodity'].isin(nonzero_commodities)]


            # Write to Excel using professional formatting
            from excel_manager import ExcelManager
            excel_manager = ExcelManager()
            
            try:
                with excel_manager.workbook(self.excel_path) as wb:
                    # Get or create re_profiles sheet
                    if tsopt in [s.name for s in wb.sheets]:
                        ws = wb.sheets[tsopt]
                    else:
                        ws = wb.sheets.add(tsopt, after=wb.sheets[-1])
                    
                    # Write solar data with professional formatting
                    excel_manager.write_formatted_table(ws, "AUTO_ROW10", solar_timeslice_df, "~TFM_DINS-AT", conditional_cell="A11")
                                            
                    # Write wind data with professional formatting
                    excel_manager.write_formatted_table(ws, "AUTO_ROW10", wind_timeslice_df, "~TFM_DINS-AT", conditional_cell="A11")

                    # # Write windoff data with professional formatting
                    excel_manager.write_formatted_table(ws, "AUTO_ROW10", windoff_timeslice_df, "~TFM_DINS-AT", conditional_cell="A11")
            except Exception as e:
                self.logger.error(f"Failed to write formatted tables: {e}")
                # Fallback to original method if professional formatting fails
                self.write_excel_sheet(tsopt, solar_timeslice_df, "~TFM_DINS-AT")
            
            self.logger.info(f"Processed resource profiles: {len(solar_timeslice_df)} solar, {len(wind_timeslice_df)} wind records")
            
        except Exception as e:
            self.logger.error(f"Failed to process resource profiles: {e}")
            raise
    
    def process_load_shapes(self, final_for_aggregations_df, tsopt):
        """Process load shapes for a specific option (Phase 2)."""
        try:
            # Load transport load shape data
            # Load loadshape data (using shared loader)
            shared_loader = get_shared_loader("data/")
            loadshape_transport_df = shared_loader.get_vs_mappings_sheet("loadshape_roadtransport")
            
            # Merge with time-slice data
            merged_loadshape_df = pd.merge(final_for_aggregations_df, loadshape_transport_df, on='hour', how='inner')
            
            # Aggregate by time-slice
            g_yrfr_df = merged_loadshape_df.groupby(['season', 'weekly', 'daynite']).agg(
                g_yrfr=('com_fr', 'size'),
                com_fr=('com_fr', lambda x: x.sum() / 365)
            ).reset_index()
            
            g_yrfr_df['timeslice'] = g_yrfr_df['season'].astype(str) + g_yrfr_df['weekly'].astype(str) + g_yrfr_df['daynite'].astype(str)
            g_yrfr_df['g_yrfr'] = g_yrfr_df['g_yrfr'] / 8760
            g_yrfr_df['commodity'] = 'elc_roadtransport'
            g_yrfr_df.drop(columns=['season', 'weekly', 'daynite'], inplace=True)
            
            # Write to Excel using professional formatting with auto-positioning
            from excel_manager import ExcelManager
            excel_manager = ExcelManager()
            
            with excel_manager.workbook(self.excel_path) as wb:
                # Get or create load_shapes sheet
                if tsopt in [s.name for s in wb.sheets]:
                    ws = wb.sheets[tsopt]
                else:
                    ws = wb.sheets.add(tsopt, after=wb.sheets[-1])
                
                # Write transport load shapes with automatic positioning on row 10
                excel_manager.write_formatted_table(ws, "AUTO_ROW10", g_yrfr_df, "~TFM_DINS-AT", conditional_cell="A11")
            
            self.logger.info(f"Processed load shapes: {len(g_yrfr_df)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to process load shapes: {e}")
            raise
    
    def process_day_night_slices(self, final_for_aggregations_df, tsopt):
        """Process day/night time slices for a specific option (Phase 2)."""
        try:
            final_for_aggregations_df['day_night'] = final_for_aggregations_df['hour'].apply(lambda h: 'D' if 7 <= h <= 18 else 'N')
            
            day_night_df = final_for_aggregations_df.groupby(['day_night','season','weekly','daynite']).agg(
                count=('hour', 'size')
            ).reset_index()
            day_night_df['day_night'] = day_night_df['day_night'].astype(str)
            day_night_df['season'] = day_night_df['season'].astype(str)
            day_night_df['weekly'] = day_night_df['weekly'].astype(str)
            day_night_df['daynite'] = day_night_df['daynite'].astype(str)
            
            day_night_df['timeslice'] = day_night_df['season'].astype(str) + day_night_df['weekly'].astype(str) + day_night_df['daynite'].astype(str)
            
            result = duckdb.sql(f"""
                with day_night_agg as (
                    SELECT day_night, timeslice, sum(count) as count
                    FROM day_night_df
                    group by day_night, timeslice
                ),
                timeslice_df as (
                    select timeslice, max(count) as count 
                    from day_night_agg
                    group by timeslice
                )
                select T2.day_night,group_concat(T2.timeslice) as {tsopt}
                from timeslice_df T1
                inner join day_night_agg T2
                    on T1.timeslice = T2.timeslice AND T1.count = T2.count
                    group by T2.day_night
                    order by T2.day_night
            """).df()
            
            # Write to Excel using professional formatting with auto-positioning
            from excel_manager import ExcelManager
            excel_manager = ExcelManager()
            
            with excel_manager.workbook(self.excel_path) as wb:
                # Get or create ev_charging_uc sheet
                if "ev_charging_uc" in [s.name for s in wb.sheets]:
                    ws = wb.sheets["ev_charging_uc"]
                else:
                    ws = wb.sheets.add("ev_charging_uc", after=wb.sheets[-1])
                
                # Write day/night slices with automatic positioning on row 10
                excel_manager.write_formatted_table(ws, "AUTO_ROW10", result)

                ws.range("A10").value = f'=IFERROR(Veda!D5,"{tsopt}")'

            self.logger.info(f"Processed day/night slices: {len(result)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to process day/night slices: {e}")
            raise
    
    def process_demand_data(self, final_for_aggregations_df, tsopt):
        """Process demand data for a specific option (Phase 2)."""
        try:
            if self.cached_demand_data is None:
                self.logger.warning("No cached demand data available, skipping demand processing")
                return
            
            # Calculate sectoral loads using cached data
            self._calculate_sectoral_loads(
                self.cached_demand_data['era_granual_mw_df'], 
                self.cached_demand_data['iea_shares_df'], 
                final_for_aggregations_df,
                tsopt
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process demand data: {e}")
            raise
    
    def _calculate_sectoral_loads(self, era_granual_mw_df, iea_shares_df, final_for_aggregations_df, tsopt):
        """Calculate sectoral loads and write to Excel (Phase 2)."""
        try:
            # Industry load calculation
            iea_ind_shares_df = iea_shares_df[iea_shares_df['Sector'].str.lower() == 'ind']
            iso_mw_iea_shares_merge_df = pd.merge(era_granual_mw_df, iea_ind_shares_df, left_on='Country', right_on='CCode')
            
            iso_mw_iea_shares_merge_df['IND_S_part'] = (iso_mw_iea_shares_merge_df['MW_mon'] - iso_mw_iea_shares_merge_df['MW_ann']) * iso_mw_iea_shares_merge_df['Share'] * 0.01
            iso_mw_iea_shares_merge_df['IND_D_part'] = (iso_mw_iea_shares_merge_df['MW_day'] - iso_mw_iea_shares_merge_df['MW_mon']) * iso_mw_iea_shares_merge_df['Share'] * 0.1
            iso_mw_iea_shares_merge_df['IND_H_part'] = (iso_mw_iea_shares_merge_df['MW_hr'] - iso_mw_iea_shares_merge_df['MW_day']) * iso_mw_iea_shares_merge_df['Share'] * 0.1
            iso_mw_iea_shares_merge_df['I_Load'] = iso_mw_iea_shares_merge_df['MW_ann'] * iso_mw_iea_shares_merge_df['Share'] + iso_mw_iea_shares_merge_df['IND_S_part'] + iso_mw_iea_shares_merge_df['IND_D_part'] + iso_mw_iea_shares_merge_df['IND_H_part']
            
            ind_load_df = iso_mw_iea_shares_merge_df[['CCode', 'Month', 'Day', 'Hour', 'I_Load', 'IND_S_part', 'IND_D_part', 'IND_H_part']].copy()
            ind_load_df.rename(columns={'CCode': 'Country'}, inplace=True)
            
            # Commercial and residential shares
            shares_com = iea_shares_df[iea_shares_df['Sector'].str.lower() == 'com'][['CCode', 'Share']].rename(columns={'Share': 'Share_com'})
            shares_res = iea_shares_df[iea_shares_df['Sector'].str.lower() == 'res'][['CCode', 'Share']].rename(columns={'Share': 'Share_res'})
            
            # Merge with era_granual_mw_df
            df_ILoad_merge = pd.merge(era_granual_mw_df, ind_load_df, on=['Country', 'Month', 'Day', 'Hour'])
            df_ILoad_merge = pd.merge(df_ILoad_merge, shares_com, left_on='Country', right_on='CCode', how='left')
            df_ILoad_merge = pd.merge(df_ILoad_merge, shares_res, left_on='Country', right_on='CCode', how='left')
            
            # Compute hour factor
            def compute_hour_factor(hour):
                h = float(hour)
                if h < 6:
                    return 1
                elif 6 <= h <= 14:
                    return ((h - 6) / 8) * 0.5 + 1
                elif 14 < h <= 22:
                    return ((22 - h) / 8) * 0.5 + 1
                else:
                    return 1
            
            df_ILoad_merge['HourFactor'] = df_ILoad_merge['Hour'].astype(float).apply(compute_hour_factor)
            
            # C_Load formula
            numerator = (
                df_ILoad_merge['MW_ann'] * df_ILoad_merge['Share_com'] +
                (df_ILoad_merge['MW_mon'] - df_ILoad_merge['MW_ann'] - df_ILoad_merge['IND_S_part']) * df_ILoad_merge['Share_com'] / (df_ILoad_merge['Share_com'] + df_ILoad_merge['Share_res']) +
                (df_ILoad_merge['MW_day'] - df_ILoad_merge['MW_mon'] - df_ILoad_merge['IND_D_part']) * df_ILoad_merge['Share_com'] / (df_ILoad_merge['Share_com'] + df_ILoad_merge['Share_res']) +
                (df_ILoad_merge['MW_hr'] - df_ILoad_merge['MW_day'] - df_ILoad_merge['IND_H_part']) * df_ILoad_merge['Share_com'] / (df_ILoad_merge['Share_com'] + df_ILoad_merge['Share_res'])
            )
            
            df_ILoad_merge['C_Load'] = numerator * df_ILoad_merge['HourFactor']
            com_load_df = df_ILoad_merge[['Country', 'Month', 'Day', 'Hour', 'C_Load']].copy()
            
            # Residential and Building loads
            era_hourly_mw_avg_df = self.cached_demand_data['iso_load_curves_df'].copy()
            ind_merged_df = era_hourly_mw_avg_df.merge(ind_load_df, on=['Country', 'Month', 'Day', 'Hour'], how='inner', suffixes=('', '_ind'))
            all_sec_loads_df = ind_merged_df.merge(com_load_df, on=['Country', 'Month', 'Day', 'Hour'], how='inner', suffixes=('', '_com'))
            all_sec_loads_df['R_Load'] = all_sec_loads_df['MW'] - all_sec_loads_df['C_Load'] - all_sec_loads_df['I_Load']
            all_sec_loads_df['B_Load'] = all_sec_loads_df['C_Load'] + all_sec_loads_df['R_Load']
            
            # Format sector loads for timeslice aggregation
            sector_load_kvp = {
                'elc_industry': 'I_Load',
                'elc_buildings': 'B_Load'
            }
            
            sector_load_dfs = []
            for sector, load_col in sector_load_kvp.items():
                df = all_sec_loads_df[['Country', 'Month', 'Day', 'Hour', load_col]].copy()
                df['Sector'] = sector
                df[f'{load_col}_avg'] = df[load_col].mean()
                df['LoadNormalized'] = df[load_col] / df[f'{load_col}_avg']
                df.rename(columns={load_col: 'MW'}, inplace=True)
                df.drop(columns=[f'{load_col}_avg'], inplace=True)
                sector_load_dfs.append(df)
            
            iemm_sector_loads_df = pd.concat(sector_load_dfs, ignore_index=True)
            iemm_sector_loads_df.columns = [col.lower() for col in iemm_sector_loads_df.columns]
            
            # Adding timeslice column and calculate com_fr
            demands_ts_merged_df = pd.merge(
                iemm_sector_loads_df,
                final_for_aggregations_df,
                on=['month', 'day', 'hour'],
                how='inner'
            )
            demands_ts_merged_df['timeslice'] = demands_ts_merged_df['season'].astype(str) + demands_ts_merged_df['weekly'].astype(str) + demands_ts_merged_df['daynite'].astype(str)
            
            sector_ts_mw_df = (
                demands_ts_merged_df
                .groupby(['country', 'sector', 'timeslice'], as_index=False)
                .agg(TSMW=('mw', 'sum'), MaxMW=('mw', 'max'), AvgMW=('mw', 'mean'))
            )
            
            totmw_df = (
                demands_ts_merged_df.groupby(['country', 'sector'], as_index=False)['mw']
                .sum()
                .rename(columns={'mw': 'TotMW'})
            )
            
            # Merge for final calculation
            com_fr_df = pd.merge(sector_ts_mw_df, totmw_df, on=['country', 'sector'], how='inner')
            com_fr_df['com_fr'] = com_fr_df['TSMW'] / com_fr_df['TotMW']
            com_fr_df.rename(columns={'sector': 'commodity'}, inplace=True)
            com_fr_df = com_fr_df[['commodity', 'timeslice', 'com_fr']]
            
            # Write to Excel using professional formatting with auto-positioning
            from excel_manager import ExcelManager
            excel_manager = ExcelManager()
            
            with excel_manager.workbook(self.excel_path) as wb:
                # Get or create load_shapes sheet
                if tsopt in [s.name for s in wb.sheets]:
                    ws = wb.sheets[tsopt]
                else:
                    ws = wb.sheets.add(tsopt, after=wb.sheets[-1])
                
                # Write sector load shapes with automatic positioning on row 10
                excel_manager.write_formatted_table(ws, "AUTO_ROW10", com_fr_df, "~TFM_DINS-AT", conditional_cell="A11")
            
            self.logger.info(f"Calculated sectoral loads: {len(com_fr_df)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to calculate sectoral loads: {e}")
            raise
    
    def process_peak_factors(self, final_for_aggregations_df, tsopt):
        """Process peak factors for a specific option (Phase 2)."""
        try:
            # Calculate peak factors based on time-slice using the original logic
            era_hourly_mw_avg_df = self.cached_demand_data['iso_load_curves_df'].copy()
            era_hourly_mw_avg_df.columns = [col.lower() for col in era_hourly_mw_avg_df.columns]
            
            # Adding timeslice column
            com_pkflx_df = pd.merge(
                era_hourly_mw_avg_df,
                final_for_aggregations_df,
                on=['month', 'day', 'hour'],
                how='inner'
            )
            com_pkflx_df['timeslice'] = com_pkflx_df['season'].astype(str) + com_pkflx_df['weekly'].astype(str) + com_pkflx_df['daynite'].astype(str)
            com_pkflx_df = (
                com_pkflx_df
                .groupby(['country', 'timeslice'], as_index=False)
                .agg(MaxMW=('mw', 'max'), AvgMW=('mw', 'mean'))
            )
            
            com_pkflx_df['com_pkflx'] = com_pkflx_df['MaxMW'] / com_pkflx_df['AvgMW'] - 1
            com_pkflx_df['commodity'] = 'ELC'
            com_pkflx_df = com_pkflx_df[['commodity', 'timeslice', 'com_pkflx']]
            
            # Write to Excel using professional formatting with auto-positioning
            from excel_manager import ExcelManager
            excel_manager = ExcelManager()
            
            with excel_manager.workbook(self.excel_path) as wb:
                # Get or create load_shapes sheet
                if tsopt in [s.name for s in wb.sheets]:
                    ws = wb.sheets[tsopt]
                else:
                    ws = wb.sheets.add(tsopt, after=wb.sheets[-1])
                
                # Write peak factors with automatic positioning on row 10
                excel_manager.write_formatted_table(ws, "AUTO_ROW10", com_pkflx_df, "~TFM_DINS-AT", conditional_cell="A11")
            
            self.logger.info(f"Processed peak factors: {len(com_pkflx_df)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to process peak factors: {e}")
            raise

    def get_hydro_scenario_for_tsopt(self, tsopt):
        """
        Get the hydro_af scenario (P10/P50/P90) for a specific tsopt from the mapping data.
        
        Args:
            tsopt (str): The time-slice option name (e.g., 'triple_1', 'triple_5')
        
        Returns:
            str: The hydro scenario ('P10', 'P50', 'P90') or 'P50' as default
        """
        try:
            # Load the mapping data for this ISO
            mapping_data = self.load_mapping_data()
            
            # Check if this tsopt exists in CSV data (stress-based configs)
            if tsopt in mapping_data['csv'].columns:
                tsopt_df = mapping_data['csv']
            # Check if this tsopt exists in VS_mappings data (legacy configs)
            elif tsopt in mapping_data['vs_mappings'].columns:
                tsopt_df = mapping_data['vs_mappings']
            else:
                self.logger.warning(f"tsopt '{tsopt}' not found in mapping data, using default P50")
                return 'P50'
            
            # Look for hydro_af row
            hydro_af_row = tsopt_df[tsopt_df['description'] == 'hydro_af']
            
            if not hydro_af_row.empty and tsopt in hydro_af_row.columns:
                hydro_scenario = hydro_af_row[tsopt].iloc[0]
                self.logger.info(f"Using hydro scenario '{hydro_scenario}' for tsopt '{tsopt}'")
                return hydro_scenario
            else:
                self.logger.info(f"No hydro_af configuration found for tsopt '{tsopt}', using default P50")
                return 'P50'
                
        except Exception as e:
            self.logger.error(f"Error getting hydro scenario for tsopt '{tsopt}': {e}")
            return 'P50'  # Safe default

    def process_hydro_capacity_factors(self, final_for_aggregations_df, tsopt):
        # Prepare final_for_aggregations_df for the query

        # Get hydro_af scenario for this tsopt
        hydro_scenario = self.get_hydro_scenario_for_tsopt(tsopt)

        # Select the appropriate column from cached data
        df_monthly_hydro_cf = self.cached_hydro_capacity_factors[['Year', 'Month', hydro_scenario]].copy()
        df_monthly_hydro_cf = df_monthly_hydro_cf.rename(columns={hydro_scenario: 'Capacity_Factor'})

        duckdb.register('df_monthly_hydro_cf', df_monthly_hydro_cf)

        # Use duckdb to calculate hydro capacity factors
        result = duckdb.sql("""
            with tab1 as (
                select month,season from final_for_aggregations_df group by month,season
            )
            select T2.Year,T1.season AS timeslice, avg(T2.Capacity_Factor) as ncap_afs,
            'hydro' AS pset_ci
            from tab1 T1
            inner join df_monthly_hydro_cf T2
            on cast(T1.month as int) = cast(T2.Month as int)
            
            group by T1.season,T2.Year
            order by T2.Year,T1.season
        """).df()

        # Write to Excel using professional formatting
        from excel_manager import ExcelManager
        excel_manager = ExcelManager()

        with excel_manager.workbook(self.excel_path) as wb:
            # Get or create re_profiles sheet
            if tsopt in [s.name for s in wb.sheets]:
                ws_re = wb.sheets[tsopt]
            else:
                ws_re = wb.sheets.add(tsopt, after=wb.sheets[-1])
            
            # Write hydro capacity factors with automatic positioning on row 10
            excel_manager.write_formatted_table(ws_re, "AUTO_ROW10", result, "~TFM_INS-AT", conditional_cell="A11")
                

        self.logger.info(f"Processed hydro capacity factors: {len(result)} records")


    def process_hydro_capacity_factors_OLD(self, final_for_aggregations_df, tsopt):
        """Process hydro capacity factors for a specific option (Phase 2)."""
        try:
            # Load monthly hydro data (using shared loader)
            shared_loader = get_shared_loader("data/")
            ember_monthly_df = shared_loader.get_monthly_hydro_data()
            ember_monthly_df = ember_monthly_df[
                (ember_monthly_df['Country code'] == self.input_iso) & 
                (ember_monthly_df['Variable'] == 'Hydro') & 
                (ember_monthly_df['Unit'] == 'TWh')
            ].copy()  # Explicitly create a copy to avoid SettingWithCopyWarning
            
            # Check if hydro data is available for this ISO
            if ember_monthly_df.empty:
                self.logger.info(f"No hydro data found for {self.input_iso}. Skipping hydro capacity factor processing.")
                return
            
            ember_monthly_df['month'] = pd.to_datetime(ember_monthly_df['Date']).dt.strftime('%m')
            
            # Check if we have month-based seasons (like ts_336) or seasonal groupings (like ts_108, ts_192)
            sample_season = final_for_aggregations_df['season'].iloc[0]
            
            if sample_season.startswith('m'):  # Month-based seasons (e.g., m01, m02, etc.)
                # For month-based seasons, we need to aggregate by month first, then group by season
                # Create a mapping from month to season
                month_to_season = {}
                for _, row in final_for_aggregations_df[['month', 'season']].drop_duplicates().iterrows():
                    month_to_season[row['month']] = row['season']
                
                # Add season column to hydro data
                ember_monthly_df['season'] = ember_monthly_df['month'].astype(int).map(month_to_season)
                
                # Calculate hydro capacity factors by season
                result = duckdb.sql("""
                    with tab1 as (
                        select season,sum(value) as value from ember_monthly_df group by season
                    ),
                    tab2 as (
                        select sum(value) as value from tab1
                    )
                    select T1.season AS timeslice,T1.value/T2.value * 1.2 as ncap_afs,
                    'hydro' AS pset_ci
                    from tab1 T1
                    cross join tab2 T2
                """).df()
                
            else:  # Seasonal groupings (e.g., W, R, S, F)
                # Prepare final_for_aggregations_df for the query
                final_for_aggregations_df['month'] = final_for_aggregations_df['month'].astype(int)
                
                # Use duckdb to calculate hydro capacity factors
                result = duckdb.sql("""
                    with tab1 as (
                        select month,season from final_for_aggregations_df group by month,season
                    ),
                    tab2 as (
                        select month,sum(value) as value from ember_monthly_df group by month
                    ),
                    tab3 as (
                        select sum(value) as value from tab2
                    )
                    select T1.season AS timeslice,sum(T2.value)/T3.value * 1.2 as ncap_afs,
                    'hydro' AS pset_ci
                    from tab1 T1
                    inner join tab2 T2
                    on cast(T1.month as int) = cast(T2.month as int)
                    cross join tab3 T3
                    group by T1.season,T3.value
                """).df()
            
            # Write to Excel using professional formatting
            from excel_manager import ExcelManager
            excel_manager = ExcelManager()
            
            try:
                with excel_manager.workbook(self.excel_path) as wb:
                    # Get or create re_profiles sheet
                    if tsopt in [s.name for s in wb.sheets]:
                        ws_re = wb.sheets[tsopt]
                    else:
                        ws_re = wb.sheets.add(tsopt, after=wb.sheets[-1])
                    
                    # Write hydro capacity factors with automatic positioning on row 10
                    excel_manager.write_formatted_table(ws_re, "AUTO_ROW10", result, "~TFM_INS-AT", conditional_cell="A11")
                    
            except Exception as e:
                self.logger.error(f"Failed to write formatted hydro capacity factors: {e}")
                # Fallback to basic writing if professional formatting fails
                with self.excel_lock:
                    app = xw.App(visible=False)
                    app.display_alerts = False  # Suppress Excel alerts and sounds
                    try:
                        wb = xw.Book(self.excel_path)
                        if tsopt in [s.name for s in wb.sheets]:
                            ws_re = wb.sheets[tsopt]
                        else:
                            ws_re = wb.sheets.add(tsopt, after=wb.sheets[-1])
                        # Use ExcelManager's auto-positioning logic for fallback too
                        from excel_manager import ExcelManager
                        temp_excel_manager = ExcelManager()
                        hydro_cell = temp_excel_manager._find_next_row10_position(ws_re)
                        
                        # Calculate header cell (one row above)
                        col_letter = hydro_cell[:-2]  # Remove "10" to get column letter
                        header_cell = f"{col_letter}9"
                        
                        ws_re.range(hydro_cell).options(index=False).value = result
                        ws_re.range(header_cell).value = "~TFM_INS-AT"
                        wb.save()
                        wb.close()
                    finally:
                        app.quit()
            
            self.logger.info(f"Processed hydro capacity factors: {len(result)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to process hydro capacity factors: {e}")
            raise
    
    def process_single_time_slice_option(self, tsopt):
        """Process a single time-slice option (Phase 2)."""
        try:
            self.logger.info(f"Processing time-slice option: {tsopt}")
            
            # Set Excel path for this option
            self.set_excel_path(tsopt)
            self.logger.info(f"Excel path set to: {self.excel_path}")
            
            # Setup Excel file for this option
            # Commented out for AR6_R10
            # self.setup_excel_file()
            
            # Create time-slice mapping for this option (load fresh mapping data each time)
            fresh_mapping_data = self.load_mapping_data()
            final_for_aggregations_df = self.create_time_slice_mapping(self.cached_weather_data, fresh_mapping_data, tsopt)
            
            # Create time-slice definitions for this option
            merged_unique = self.create_time_slice_definitions(final_for_aggregations_df)
            
            # Write time-slice definitions using professional formatting with auto-positioning
            from excel_manager import ExcelManager
            excel_manager = ExcelManager()
            
            with excel_manager.workbook(self.excel_path) as wb:
                # Get or create timeslice_def sheet
                if tsopt in [s.name for s in wb.sheets]:
                    ws = wb.sheets[tsopt]
                else:
                    ws = wb.sheets.add(tsopt, after=wb.sheets[-1])
                
                # Write time-slice definitions with automatic positioning on row 10
                excel_manager.write_formatted_table(ws, "C10", merged_unique, "~TimeSlices", conditional_cell="A11")

                ws.range("A10").value = tsopt
                ws.range("A11").value = '=IFERROR(IF(Veda!D5=A10,"ok","x"),"")'
                

            # Process resource profiles
            self.process_resource_profiles(self.cached_weather_data, final_for_aggregations_df, tsopt)
            
            # Process load shapes
            self.process_load_shapes(final_for_aggregations_df, tsopt)
            
            # Process day/night slices
            self.process_day_night_slices(final_for_aggregations_df,tsopt)
            
            # Process demand data
            self.process_demand_data(final_for_aggregations_df, tsopt)
            
            # Process peak factors
            self.process_peak_factors(final_for_aggregations_df, tsopt)
            
            # Process hydro capacity factors
            self.process_hydro_capacity_factors(final_for_aggregations_df, tsopt)
            
            self.logger.info(f"Completed processing for time-slice option: {tsopt}")
            
        except Exception as e:
            self.logger.error(f"Failed to process time-slice option {tsopt}: {e}")
            raise
    
    def process_time_slices(self):
        """Main method to process all time-slice data with optimization."""
        try:
            self.logger.info(f"Starting time-slice processing for {self.input_iso}")
            
            # PHASE 1: Load and process data once
            self.logger.info("Phase 1: Loading and processing hourly data...")
            
            # Load weather data once
            self.cached_weather_data = self.load_weather_data()
            if self.cached_weather_data is None:
                self.logger.warning("No weather data available, skipping time-slice processing")
                return
            
            # Load mapping data (NO CACHING - will reload for each tsopt)
            # self.cached_mapping_data = self.load_mapping_data()  # Disabled caching
            
            # Load and process demand data once (heavy lifting)
            self.cached_demand_data = self.load_and_process_demand_data()
            
            # Export hourly data to _ISO.xlsx
            self.export_hourly_data_to_csv()
            
            self.logger.info("Phase 1 completed: Hourly data loaded and processed")
            
            # PHASE 2: Process time-slice options
            self.logger.info("Phase 2: Processing time-slice options...")
            
            # load hydro capacity factors
            self.cached_hydro_capacity_factors = get_hydro_capacity_factors(self.input_iso)

            # Determine which time-slice options to process
            if self.process_all_tsopts:
                tsopts_to_process = self.get_available_tsopts()
                self.logger.info(f"Processing {len(tsopts_to_process)} time-slice options: {tsopts_to_process}")
            else:
                # Default processing: include VS_mappings tsopts alongside the specified tsopt
                vs_mappings_tsopts = self.get_vs_mappings_tsopts()
                tsopts_to_process = [self.tsopt] + vs_mappings_tsopts
                # Remove duplicates while preserving order
                tsopts_to_process = list(dict.fromkeys(tsopts_to_process))
                self.logger.info(f"Processing default time-slice options: {tsopts_to_process} (includes {len(vs_mappings_tsopts)} VS_mappings tsopts)")
            
            # Process time-slice options sequentially (more reliable than parallel)
            if len(tsopts_to_process) > 1:
                self.logger.info("Processing time-slice options sequentially...")
                for tsopt in tsopts_to_process:
                    try:
                        self.process_single_time_slice_option(tsopt)
                    except Exception as e:
                        self.logger.error(f"Time-slice option {tsopt} failed: {e}")
                        # Continue with other options
            else:
                # Single option - no need for parallel processing
                for tsopt in tsopts_to_process:
                    self.process_single_time_slice_option(tsopt)
            
            self.logger.info(f"Completed time-slice processing for {self.input_iso}")
            
        except Exception as e:
            self.logger.error(f"Failed to process time slices: {e}")
            raise


def process_time_slices(iso_processor, tsopt='ts12_clu', process_all_tsopts=False, dest_folder=None):
    """
    Process time-slice data for a specific ISO.
    
    Args:
        iso_processor: ISOProcessor instance from main pipeline
        tsopt: Time slice option (default: 'ts12_clu') - processed alongside VS_mappings tsopts when process_all_tsopts=False
        process_all_tsopts: If True, process all available ts_* options (ignores tsopt parameter)
        dest_folder: Optional destination folder path. If None, uses default VerveStacks_{ISO} format
    """
    processor = TimeSliceProcessor(iso_processor, tsopt, process_all_tsopts, dest_folder)
    processor.process_time_slices() 


if __name__ == "__main__":
    
    processor = TimeSliceProcessor(iso_processor, tsopt='ts12_clu')
    processor.process_time_slices()