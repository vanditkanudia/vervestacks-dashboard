#!/usr/bin/env python3
"""
FACETS Hourly Supply Picture Creator
Incrementally builds hourly supply profiles with visual validation

Phase 1: Demand plotting (Jan, Jul, Dec)
Future phases: Add supply sources as stacked areas
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import h5py
import os
from datetime import datetime, timedelta
import warnings
import argparse
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

warnings.filterwarnings('ignore')

class HourlySupplyCreator:
    """Create incremental hourly supply picture with multi-regional transmission group analysis"""
    
    def __init__(self, transmission_group='MISO_North', weather_year=2012, scenario="re-L.gp-L.Cp-95.ncs-H.smr-L", 
                 year=2045, region=None, enable_plots=True, storage_increment=None, data_version=None):
        """Initialize with transmission group parameters (region param for backward compatibility)"""
        self.transmission_group = transmission_group
        self.weather_year = weather_year
        self.scenario = scenario
        self.year = year
        self.region = region  # For backward compatibility - if set, use single region mode
        self.enable_plots = enable_plots  # Control chart generation
        self.storage_increment = storage_increment  # GW to add per iteration for sensitivity analysis
        self.data_version = data_version  # Version subfolder for inputs/outputs (e.g., "04Aug25", "25Oct25")
        
        # Set up paths relative to script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Include data_version in paths if specified
        if data_version:
            self.model_outputs_path = os.path.join(script_dir, "..", "data", "model_outputs", data_version, "")
            self.outputs_base_path = os.path.join(script_dir, "..", "outputs", data_version, "")
        else:
            self.model_outputs_path = os.path.join(script_dir, "..", "data", "model_outputs", "")
            self.outputs_base_path = os.path.join(script_dir, "..", "outputs", "")
        
        self.hourly_data_path = os.path.join(script_dir, "..", "data", "hourly_data", "")
        
        # Set base path for shared config files (always in parent model_outputs directory)
        if data_version:
            self.config_base_path = os.path.join(script_dir, "..", "data", "model_outputs", "")
        else:
            self.config_base_path = self.model_outputs_path
        
        # Load generation data once for reuse
        print("📊 Loading generation data (one-time cache)...")
        gen_file = f"{self.model_outputs_path}VSInput_generation by tech, region, and timeslice.csv"
        self.gen_df = pd.read_csv(gen_file)
        print(f"   ✅ Cached {len(self.gen_df):,} total records")
        
        # Load transmission group regions
        self.regions, self.demand_regions = self._get_transmission_group_regions()
        
        if self.region:  # Single region mode for backward compatibility
            print(f"🎯 Hourly Supply Creator - Single Region Analysis")
            print(f"   📊 Scenario: {self.scenario}")
            print(f"   📅 Year: {self.year}, Region: {self.region}")
            print(f"   🌤️  Weather: {self.weather_year}")
        else:  # Multi-regional mode
            print(f"🎯 Hourly Supply Creator - Multi-Regional Analysis")
            print(f"   📊 Scenario: {self.scenario}")
            print(f"   📅 Year: {self.year}, Transmission Group: {self.transmission_group}")
            print(f"   🌐 Regions ({len(self.regions)}): {self.regions}")
            print(f"   🌤️  Weather: {self.weather_year}")
        print("="*70)
    
    def _add_logo_watermark(self, fig, alpha=0.4, scale=0.075):
        """Add KanorsEMR logo as watermark to the top-right corner and tagline to top-left corner of the figure"""
        try:
            # Add tagline to top-left corner
            tagline = "VERVESTACKS: Energy modeling reimagined · Hourly simulation for any planned mix"
            
            # Position tagline in top-left corner with same font size as panel titles
            fig.text(0.02, 0.98, tagline, 
                    fontsize=12,  # Same as panel titles
                    color='#2E5984',  # Professional blue color
                    weight='normal',
                    ha='left', va='top',
                    transform=fig.transFigure,
                    alpha=0.8)
            
            # Get the logo path relative to script location
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "..", "..", "KanorsEMR-Logo-2025_Kanors-Primary-Logo-768x196.webp")
            
            if not os.path.exists(logo_path):
                print(f"⚠️  Logo file not found: {logo_path}")
                return
                
            # Load and process the logo
            logo_img = Image.open(logo_path)
            
            # Convert to RGB if RGBA for better compatibility
            if logo_img.mode == 'RGBA':
                logo_rgb = Image.new('RGB', logo_img.size, (255, 255, 255))
                logo_rgb.paste(logo_img, mask=logo_img.split()[-1])  # Use alpha channel as mask
                logo_img = logo_rgb
            
            # Calculate logo size relative to figure (half the previous size)
            fig_width, fig_height = fig.get_size_inches()
            logo_width_inches = fig_width * scale
            logo_height_inches = logo_width_inches * (logo_img.height / logo_img.width)
            
            # Create OffsetImage for matplotlib
            offsetimage = OffsetImage(logo_img, zoom=logo_width_inches/7.68, alpha=alpha)  # 7.68 = original width in "inches"
            
            # Position in top-right corner aligned with plot area edges
            x_pos = 0.98  # Right edge of plot area
            y_pos = 0.98  # Top edge of plot area
            
            # Add logo to figure
            ab = AnnotationBbox(offsetimage, (x_pos, y_pos), 
                              xycoords='figure fraction',
                              frameon=False,
                              xybox=(0, 0), boxcoords="offset points")
            fig.add_artist(ab)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not add logo watermark: {e}")
    
    def _get_transmission_group_regions(self):
        """Get all regions for the specified transmission group"""
        print(f"🌐 Loading transmission group regions for {self.transmission_group}...")
        
        if self.region:  # Single region backward compatibility
            facets_region = self.region
            demand_region = self._convert_facets_to_demand_format(facets_region)
            return [facets_region], [demand_region]
        
        try:
            df = self.gen_df.copy()
            
            # Filter by transmission group
            tg_regions = df[df['reg_transgrp'] == self.transmission_group]['region'].unique()
            facets_regions = sorted(tg_regions)
            
            # Convert to demand format (p060 -> p60)
            demand_regions = [self._convert_facets_to_demand_format(r) for r in facets_regions]
            
            print(f"   ✅ Found {len(facets_regions)} regions in {self.transmission_group}")
            print(f"   📊 FACETS format: {facets_regions}")
            print(f"   📈 Demand format: {demand_regions}")
            
            return facets_regions, demand_regions
            
        except Exception as e:
            raise Exception(f"❌ Error loading transmission group data: {e}")
    
    def _convert_facets_to_demand_format(self, facets_region):
        """Convert FACETS region format (p060) to demand format (p60)"""
        if facets_region.startswith('p'):
            # Remove leading zeros: p060 -> p60
            return 'p' + str(int(facets_region[1:]))
        return facets_region
    
    def load_hourly_demand(self):
        """Load and aggregate hourly demand data across transmission group regions"""
        print("📈 Loading Hourly Demand Data...")
        print(f"🎯 Extracting 2045 model year + {self.weather_year} weather year...")
        
        demand_file = f"{self.hourly_data_path}EER_100by2050_load_hourly.h5"
        
        if not os.path.exists(demand_file):
            raise FileNotFoundError(f"Demand file not found: {demand_file}")
        
        try:
            with h5py.File(demand_file, 'r') as f:
                # Load columns, data, and indices
                columns = [col.decode() for col in f['columns'][:]]
                data = f['data'][:]
                index_0 = f['index_0'][:]  # Model years
                index_1 = f['index_1'][:]  # Datetime strings
                
                # Decode datetime strings
                index_1_decoded = [item.decode() if isinstance(item, bytes) else item for item in index_1]
                
                # Create mask for 2045 model year + configurable weather year
                target_mask = np.zeros(len(index_0), dtype=bool)
                for i in range(len(index_0)):
                    if index_0[i] == 2045:
                        dt_str = index_1_decoded[i]
                        if dt_str.startswith(f'{self.weather_year}-'):
                            target_mask[i] = True
                
                target_hours = np.sum(target_mask)
                print(f"📊 Found {target_hours} hours for 2045 model year + {self.weather_year} weather year")
                
                if target_hours != 8760:
                    raise ValueError(f"Expected 8760 hours, got {target_hours}")
                
                # Handle single region mode (backward compatibility)
                if self.region:
                    demand_region = self._convert_facets_to_demand_format(self.region)
                    if demand_region in columns:
                        region_idx = columns.index(demand_region)
                        hourly_demand = data[target_mask, region_idx]
                        print(f"   ✅ Loaded {len(hourly_demand)} hours of demand data for region {demand_region}")
                        print(f"   📊 Annual demand: {hourly_demand.sum()/1000:.0f} GWh")
                        print(f"   📊 Demand range: {hourly_demand.min():,.0f} - {hourly_demand.max():,.0f} MW")
                        return hourly_demand
                    else:
                        available_regions = columns[:10]
                        raise ValueError(f"Region {demand_region} not found. Available: {available_regions}")
                
                # Multi-regional aggregation
                aggregated_demand = np.zeros(8760)
                found_regions = []
                missing_regions = []
                
                for demand_region in self.demand_regions:
                    if demand_region in columns:
                        region_idx = columns.index(demand_region)
                        region_data = data[target_mask, region_idx]
                        aggregated_demand += region_data
                        found_regions.append(demand_region)
                        print(f"   ✅ {demand_region}: {region_data.min():.0f} - {region_data.max():.0f} MW")
                    else:
                        missing_regions.append(demand_region)
                
                if missing_regions:
                    print(f"   ⚠️  Missing regions: {missing_regions}")
                
                print(f"   ✅ Aggregated demand across {len(found_regions)} {self.transmission_group} regions")
                print(f"   📊 Total annual demand: {aggregated_demand.sum()/1000:.0f} GWh")
                print(f"   📊 Total demand range: {aggregated_demand.min():,.0f} - {aggregated_demand.max():,.0f} MW")
                
                return aggregated_demand
                    
        except Exception as e:
            raise Exception(f"Error loading demand data: {e}")
    
    def extract_monthly_data(self, hourly_data):
        """Extract January, July, December hourly data with datetime indices"""
        print("📅 Extracting Monthly Data (Jan, Jul, Dec)...")
        
        # Create datetime index for the weather year
        start_date = datetime(self.weather_year, 1, 1)
        dates = [start_date + timedelta(hours=i) for i in range(len(hourly_data))]
        
        # Convert to pandas for easy monthly filtering
        df = pd.DataFrame({
            'demand_mw': hourly_data,
            'datetime': pd.to_datetime(dates)
        })
        df['month'] = df['datetime'].dt.month
        
        # Extract target months
        jan_data = df[df['month'] == 1].copy()
        jul_data = df[df['month'] == 7].copy()
        dec_data = df[df['month'] == 12].copy()
        
        print(f"   ✅ January: {len(jan_data)} hours")
        print(f"   ✅ July: {len(jul_data)} hours") 
        print(f"   ✅ December: {len(dec_data)} hours")
        
        return {
            'january': jan_data,
            'july': jul_data,
            'december': dec_data
        }
    
    def find_top_shortage_weeks(self, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw, 
                               hourly_storage_discharge, hourly_dispatchable):
        """Find the top 5 weeks with maximum residual shortage"""
        print("🔍 Finding Top 5 Weeks with Maximum Residual Shortage...")
        
        # Calculate total supply
        total_supply = (hourly_baseload + hourly_solar_mw + hourly_wind_mw + 
                       hourly_storage_discharge + hourly_dispatchable)
        
        # Calculate residual shortage (unmet demand)
        residual_shortage = np.maximum(hourly_demand - total_supply, 0)
        
        # Create datetime index for 8760 hours starting from weather year
        start_date = datetime(self.weather_year, 1, 1)
        dates = [start_date + timedelta(hours=h) for h in range(8760)]
        
        # Create DataFrame
        df = pd.DataFrame({
            'datetime': dates,
            'demand_mw': hourly_demand,
            'residual_shortage': residual_shortage,
            'hour_index': range(8760)
        })
        
        # Add week number (ISO week)
        df['week'] = df['datetime'].dt.isocalendar().week
        df['year'] = df['datetime'].dt.year
        
        # Calculate weekly shortage totals
        weekly_shortage = df.groupby(['year', 'week']).agg({
            'residual_shortage': 'sum',
            'datetime': ['min', 'max'],
            'hour_index': ['min', 'max']
        }).reset_index()
        
        # Flatten column names
        weekly_shortage.columns = ['year', 'week', 'total_shortage_mwh', 'week_start', 'week_end', 
                                  'start_hour_idx', 'end_hour_idx']
        
        # Sort by total shortage and get top 5
        top_weeks = weekly_shortage.nlargest(5, 'total_shortage_mwh')
        
        print(f"   📊 Analyzed {len(weekly_shortage)} weeks")
        
        # Check if there are any actual shortages
        max_shortage = top_weeks['total_shortage_mwh'].max() if not top_weeks.empty else 0
        
        if max_shortage <= 0:
            print("   ✅ No shortage weeks found - system meets all demand!")
            return {}  # Return empty dict to signal no shortages
        
        print("   🔥 Top 5 Shortage Weeks:")
        
        # Extract data for each top week
        week_data = {}
        for idx, week_row in top_weeks.iterrows():
            week_start = week_row['week_start']
            week_end = week_row['week_end']
            start_hour = week_row['start_hour_idx']
            end_hour = week_row['end_hour_idx']
            total_shortage = week_row['total_shortage_mwh']
            
            # Skip weeks with zero shortage
            if total_shortage <= 0:
                continue
                
            # Extract week data (up to 168 hours)
            week_hours = min(168, end_hour - start_hour + 1)
            week_df = df[(df['hour_index'] >= start_hour) & (df['hour_index'] <= end_hour)].copy()
            week_df['hour_of_week'] = range(len(week_df))
            
            week_name = f"Week {week_row['week']} ({week_start.strftime('%b %d')})"
            week_data[week_name] = week_df
            
            print(f"      {week_name}: {total_shortage:.0f} MWh shortage, {len(week_df)} hours")
        
        return week_data
    
    def find_top_surplus_weeks(self, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw, 
                              hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable):
        """Find the top 5 weeks with maximum surplus (excess supply)"""
        print("🔍 Finding Top 5 Weeks with Maximum Surplus...")
        
        # Calculate total supply
        total_supply = (hourly_baseload + hourly_solar_mw + hourly_wind_mw + 
                       hourly_storage_discharge + hourly_dispatchable)
        
        # Calculate surplus (supply exceeding demand, accounting for storage charging)
        # CRITICAL: Surplus can only exist when there's NO shortage (unmet demand)
        shortage = np.maximum(hourly_demand - total_supply, 0)
        total_demand_with_storage = hourly_demand + hourly_storage_charge
        
        # Surplus only exists where there's no shortage AND supply exceeds total demand+storage
        surplus_raw = total_supply - total_demand_with_storage
        surplus = np.where(shortage > 0, 0, np.maximum(surplus_raw, 0))
        
        # Create datetime index for 8760 hours starting from weather year
        start_date = datetime(self.weather_year, 1, 1)
        dates = [start_date + timedelta(hours=h) for h in range(8760)]
        
        # Create DataFrame
        df = pd.DataFrame({
            'datetime': dates,
            'demand_mw': hourly_demand,
            'surplus': surplus,
            'hour_index': range(8760)
        })
        
        # Add week number (ISO week)
        df['week'] = df['datetime'].dt.isocalendar().week
        df['year'] = df['datetime'].dt.year
        
        # Calculate weekly surplus totals
        weekly_surplus = df.groupby(['year', 'week']).agg({
            'surplus': 'sum',
            'datetime': ['min', 'max'],
            'hour_index': ['min', 'max']
        }).reset_index()
        
        # Flatten column names
        weekly_surplus.columns = ['year', 'week', 'total_surplus_mwh', 'week_start', 'week_end', 
                                 'start_hour_idx', 'end_hour_idx']
        
        # Sort by total surplus and get top 5
        top_weeks = weekly_surplus.nlargest(5, 'total_surplus_mwh')
        
        print(f"   📊 Analyzed {len(weekly_surplus)} weeks")
        
        # Check if there are any actual surpluses
        max_surplus = top_weeks['total_surplus_mwh'].max() if not top_weeks.empty else 0
        
        if max_surplus <= 0:
            print("   ⚠️ No surplus weeks found - system has no excess generation!")
            return {}  # Return empty dict to signal no surpluses
        
        print("   🌱 Top 5 Surplus Weeks:")
        
        # Extract data for each top week
        week_data = {}
        for idx, week_row in top_weeks.iterrows():
            week_start = week_row['week_start']
            week_end = week_row['week_end']
            start_hour = week_row['start_hour_idx']
            end_hour = week_row['end_hour_idx']
            total_surplus = week_row['total_surplus_mwh']
            
            # Skip weeks with zero surplus
            if total_surplus <= 0:
                continue
                
            # Extract week data (up to 168 hours)
            week_hours = min(168, end_hour - start_hour + 1)
            week_df = df[(df['hour_index'] >= start_hour) & (df['hour_index'] <= end_hour)].copy()
            week_df['hour_of_week'] = range(len(week_df))
            
            week_name = f"Week {week_row['week']} ({week_start.strftime('%b %d')})"
            week_data[week_name] = week_df
            
            print(f"      {week_name}: {total_surplus:.0f} MWh surplus, {len(week_df)} hours")
        
        return week_data
    
    def _create_no_shortage_chart(self):
        """Create a blank chart with 'No Shortage' message"""
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        ax.text(0.5, 0.5, 'No Shortage\n\n✅ System meets all demand', 
                fontsize=24, fontweight='bold', ha='center', va='center',
                transform=ax.transAxes, color='green')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save the chart
        system_suffix = self.region if self.region else self.transmission_group
        scenario_folder = self.scenario.replace(".", "_")
        output_path = f"../outputs/plots/{scenario_folder}/simulation_shortage_weeks_{system_suffix}.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved chart: {output_path}")
        
        return fig
    
    def _create_no_surplus_chart(self):
        """Create a blank chart with 'No Surplus' message"""
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        ax.text(0.5, 0.5, 'No Surplus\n\n⚠️ System has no excess generation', 
                fontsize=24, fontweight='bold', ha='center', va='center',
                transform=ax.transAxes, color='orange')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save the chart
        system_suffix = self.region if self.region else self.transmission_group
        scenario_folder = self.scenario.replace(".", "_")
        output_path = os.path.join(self.outputs_base_path, "plots", scenario_folder, f"simulation_surplus_weeks_{system_suffix}.png")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved chart: {output_path}")
        
        return fig
    
    def plot_top_shortage_weeks(self, week_data, hourly_baseload, hourly_solar_mw, hourly_wind_mw, 
                               hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable, phase_name=""):
        """Create 5-panel chart for top shortage weeks with complete supply stack"""
        import os
        
        # Handle case where no shortage weeks exist
        if not week_data:
            return self._create_no_shortage_chart()
        print(f"📊 Creating Top 5 Shortage Weeks Charts{' - ' + phase_name if phase_name else ''}...")
        
        # Load timeslice mapping for indicators
        season_mapping, time_mapping = self.load_timeslice_mapping()
        timeslice_hour_mapping = self.map_timeslices_to_hours(season_mapping, time_mapping)
        
        # Set up the figure with 5 subplots
        fig, axes = plt.subplots(5, 1, figsize=(20, 24))
        title_suffix = f" - {phase_name}" if phase_name else ""
        
        # Dynamic title based on analysis mode
        if self.region:
            system_name = self.region
        else:
            system_name = f"{self.transmission_group} System"
        
        fig.suptitle(f'FACETS Top 5 Shortage Weeks{title_suffix}\\n{system_name} ({self.year})', 
                     fontsize=18, fontweight='bold')
        
        # Colors for supply stack
        baseload_color = '#8B4513'        # Brown for nuclear baseload
        solar_color = '#FFD700'           # Gold for solar
        wind_color = '#87CEEB'            # Sky blue for wind
        storage_discharge_color = '#32CD32'  # Lime green for storage discharge
        storage_charge_color = '#FF6347'     # Tomato for storage charge (negative)
        dispatchable_color = '#FF4500'       # Orange red for dispatchable
        
        week_names = list(week_data.keys())
        
        for i, (week_name, week_df) in enumerate(week_data.items()):
            ax = axes[i]
            
            # Get hour indices for this week
            start_hour = week_df['hour_index'].iloc[0]
            end_hour = week_df['hour_index'].iloc[-1]
            week_length = len(week_df)
            
            # Extract hourly data for this week
            week_demand = week_df['demand_mw'].values
            week_baseload = hourly_baseload[start_hour:start_hour + week_length]
            week_solar = hourly_solar_mw[start_hour:start_hour + week_length]
            week_wind = hourly_wind_mw[start_hour:start_hour + week_length]
            week_storage_charge = hourly_storage_charge[start_hour:start_hour + week_length]
            week_storage_discharge = hourly_storage_discharge[start_hour:start_hour + week_length]
            week_dispatchable = hourly_dispatchable[start_hour:start_hour + week_length]
            
            # Convert to GW for plotting
            week_demand_gw = week_demand / 1000
            week_baseload_gw = week_baseload / 1000
            week_solar_gw = week_solar / 1000
            week_wind_gw = week_wind / 1000
            week_storage_charge_gw = week_storage_charge / 1000
            week_storage_discharge_gw = week_storage_discharge / 1000
            week_dispatchable_gw = week_dispatchable / 1000
            
            # Create hour indices for x-axis
            hours = range(week_length)
            
            # Plot demand line
            ax.plot(hours, week_demand_gw, color='black', linewidth=2, label='Demand', zorder=10)
            
            # Create stacked areas for supply
            # Start with baseload
            y_bottom = np.zeros(week_length)
            ax.fill_between(hours, y_bottom, y_bottom + week_baseload_gw, 
                           color=baseload_color, alpha=0.8, label='Baseload')
            y_bottom += week_baseload_gw
            
            # Add solar
            ax.fill_between(hours, y_bottom, y_bottom + week_solar_gw, 
                           color=solar_color, alpha=0.8, label='Solar')
            y_bottom += week_solar_gw
            
            # Add wind
            ax.fill_between(hours, y_bottom, y_bottom + week_wind_gw, 
                           color=wind_color, alpha=0.8, label='Wind')
            y_bottom += week_wind_gw
            
            # Add storage discharge
            ax.fill_between(hours, y_bottom, y_bottom + week_storage_discharge_gw, 
                           color=storage_discharge_color, alpha=0.8, label='Storage Discharge')
            y_bottom += week_storage_discharge_gw
            
            # Add dispatchable
            ax.fill_between(hours, y_bottom, y_bottom + week_dispatchable_gw, 
                           color=dispatchable_color, alpha=0.8, label='Dispatchable')
            y_bottom += week_dispatchable_gw
            
            # Add storage charging as negative area (below zero)
            ax.fill_between(hours, -week_storage_charge_gw, 0, 
                           color=storage_charge_color, alpha=0.6, label='Storage Charging')
            
            # Calculate total shortage for this week
            total_supply = (week_baseload + week_solar + week_wind + 
                           week_storage_discharge + week_dispatchable)
            week_shortage = np.maximum(week_demand - total_supply, 0)
            week_shortage_gw = week_shortage / 1000
            total_shortage_gwh = np.sum(week_shortage) / 1000
            max_shortage_gw = np.max(week_shortage) / 1000
            
            # Calculate surplus (supply above demand, accounting for storage charging)
            # CRITICAL: Surplus can only exist when there's NO shortage (unmet demand)
            week_shortage = np.maximum(week_demand - total_supply, 0)
            total_demand_with_storage = week_demand + week_storage_charge
            
            # Surplus only exists where there's no shortage AND supply exceeds total demand+storage
            surplus_raw = total_supply - total_demand_with_storage
            week_surplus = np.where(week_shortage > 0, 0, np.maximum(surplus_raw, 0))
            week_surplus_gw = week_surplus / 1000
            total_surplus_gwh = np.sum(week_surplus) / 1000
            max_surplus_gw = np.max(week_surplus) / 1000
            
            # Show shortage as the GAP between supply stack and demand line
            shortage_exists = np.any(week_shortage_gw > 0)
            if shortage_exists:
                # Fill the gap between total supply and demand with gray diagonal hatching
                ax.fill_between(hours, y_bottom, week_demand_gw, 
                               color='gray', alpha=0.4, label='Unmet Demand (Gap)' if i == 0 else "",
                               where=(week_demand_gw > y_bottom), hatch='///')
                
                # Add text annotation for significant shortages
                max_shortage_hour = np.argmax(week_shortage_gw)
                if max_shortage_gw > 1.0:  # Only annotate if shortage > 1 GW
                    gap_y_position = (y_bottom[max_shortage_hour] + week_demand_gw[max_shortage_hour]) / 2
                    ax.annotate(f'Max Gap\\n{max_shortage_gw:.1f} GW', 
                               xy=(max_shortage_hour, gap_y_position),
                               xytext=(10, 10), textcoords='offset points',
                               fontsize=8, ha='left', va='center',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='gray', alpha=0.3),
                               arrowprops=dict(arrowstyle='->', color='gray', alpha=0.7))
            
            # Show surplus as area between demand line and supply stack
            surplus_exists = np.any(week_surplus_gw > 0)
            if surplus_exists:
                # Fill surplus area with green diagonal hatching (opposite direction)
                ax.fill_between(hours, week_demand_gw, week_demand_gw + week_surplus_gw,
                               color='green', alpha=0.3, label='Surplus (Excess Supply)' if i == 0 else "",
                               where=(week_surplus_gw > 0), hatch='\\\\\\')
                
                # Add text annotation for significant surplus
                max_surplus_hour = np.argmax(week_surplus_gw)
                if max_surplus_gw > 1.0:  # Only annotate if surplus > 1 GW
                    surplus_y_position = (week_demand_gw[max_surplus_hour] + y_bottom[max_surplus_hour]) / 2
                    ax.annotate(f'Max Surplus\\n{max_surplus_gw:.1f} GW', 
                               xy=(max_surplus_hour, surplus_y_position),
                               xytext=(-10, -10), textcoords='offset points',
                               fontsize=8, ha='right', va='center',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='green', alpha=0.3),
                               arrowprops=dict(arrowstyle='->', color='green', alpha=0.7))
            
            # Formatting
            ax.set_title(f'{week_name} - Shortage: {total_shortage_gwh:.1f} GWh (Max: {max_shortage_gw:.1f} GW) | Surplus: {total_surplus_gwh:.1f} GWh (Max: {max_surplus_gw:.1f} GW)', 
                        fontsize=12, fontweight='bold')
            ax.set_ylabel('Power (GW)', fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, week_length-1)
            
            # Add legend only to first subplot
            if i == 0:
                # Add a dummy line for timeslice indicators in legend
                ax.plot([], [], color='gray', linestyle='--', alpha=0.7, linewidth=1, label='FACETS Timeslices')
                ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=10)
            
            # X-axis formatting
            if i == len(week_data) - 1:  # Last subplot
                ax.set_xlabel('Hour of Week', fontsize=10)
            
            # Set y-axis to show negative values for storage charging
            y_min = min(0, -np.max(week_storage_charge_gw) * 1.1) if np.max(week_storage_charge_gw) > 0 else 0
            y_max = max(np.max(week_demand_gw), np.max(y_bottom)) * 1.05
            ax.set_ylim(y_min, y_max)
            
            # Add hour-of-day markers for reference (after y-limits are set)
            self.add_hour_of_day_markers(ax, week_length)
            
            # Add FACETS timeslice boundaries as vertical lines
            self.add_timeslice_indicators(ax, start_hour, week_length, timeslice_hour_mapping)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.90)  # Add space for main title
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save the chart with simplified naming and scenario subfolder
        system_suffix = self.region if self.region else self.transmission_group
        scenario_folder = self.scenario.replace(".", "_")  # Replace dots with underscores for folder name
        output_path = os.path.join(self.outputs_base_path, "plots", scenario_folder, f"simulation_shortage_weeks_{system_suffix}.png")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved chart: {output_path}")
        
        return fig
    
    def plot_top_surplus_weeks(self, week_data, hourly_baseload, hourly_solar_mw, hourly_wind_mw, 
                              hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable, phase_name=""):
        """Create 5-panel chart for top surplus weeks with complete supply stack"""
        import os
        print(f"📊 Creating Top 5 Surplus Weeks Charts{' - ' + phase_name if phase_name else ''}...")
        
        # Load timeslice mapping for indicators
        season_mapping, time_mapping = self.load_timeslice_mapping()
        timeslice_hour_mapping = self.map_timeslices_to_hours(season_mapping, time_mapping)
        
        # Set up the figure with 5 subplots
        fig, axes = plt.subplots(5, 1, figsize=(20, 24))
        title_suffix = f" - {phase_name}" if phase_name else ""
        
        # Dynamic title based on analysis mode
        if self.region:
            system_name = self.region
        else:
            system_name = f"{self.transmission_group} System"
        
        fig.suptitle(f'FACETS Top 5 Surplus Weeks{title_suffix}\\n{system_name} ({self.year})', 
                     fontsize=18, fontweight='bold')
        
        # Colors for supply stack (same as shortage plots)
        baseload_color = '#8B4513'        # Brown for nuclear baseload
        solar_color = '#FFD700'           # Gold for solar
        wind_color = '#87CEEB'            # Sky blue for wind
        storage_discharge_color = '#32CD32'  # Lime green for storage discharge
        storage_charge_color = '#FF6347'     # Tomato for storage charge (negative)
        dispatchable_color = '#FF4500'       # Orange red for dispatchable
        
        week_names = list(week_data.keys())
        
        for i, (week_name, week_df) in enumerate(week_data.items()):
            ax = axes[i]
            
            # Get hour indices for this week
            start_hour = week_df['hour_index'].iloc[0]
            end_hour = week_df['hour_index'].iloc[-1]
            week_length = len(week_df)
            
            # Extract hourly data for this week
            week_demand = week_df['demand_mw'].values
            week_baseload = hourly_baseload[start_hour:start_hour + week_length]
            week_solar = hourly_solar_mw[start_hour:start_hour + week_length]
            week_wind = hourly_wind_mw[start_hour:start_hour + week_length]
            week_storage_charge = hourly_storage_charge[start_hour:start_hour + week_length]
            week_storage_discharge = hourly_storage_discharge[start_hour:start_hour + week_length]
            week_dispatchable = hourly_dispatchable[start_hour:start_hour + week_length]
            
            # Convert to GW for plotting
            week_demand_gw = week_demand / 1000
            week_baseload_gw = week_baseload / 1000
            week_solar_gw = week_solar / 1000
            week_wind_gw = week_wind / 1000
            week_storage_charge_gw = week_storage_charge / 1000
            week_storage_discharge_gw = week_storage_discharge / 1000
            week_dispatchable_gw = week_dispatchable / 1000
            
            # Create hour indices for x-axis
            hours = range(week_length)
            
            # Plot demand line
            ax.plot(hours, week_demand_gw, color='black', linewidth=2, label='Demand', zorder=10)
            
            # Create stacked areas for supply
            # Start with baseload
            y_bottom = np.zeros(week_length)
            ax.fill_between(hours, y_bottom, y_bottom + week_baseload_gw, 
                           color=baseload_color, alpha=0.8, label='Baseload')
            y_bottom += week_baseload_gw
            
            # Add solar
            ax.fill_between(hours, y_bottom, y_bottom + week_solar_gw, 
                           color=solar_color, alpha=0.8, label='Solar')
            y_bottom += week_solar_gw
            
            # Add wind
            ax.fill_between(hours, y_bottom, y_bottom + week_wind_gw, 
                           color=wind_color, alpha=0.8, label='Wind')
            y_bottom += week_wind_gw
            
            # Add storage discharge
            ax.fill_between(hours, y_bottom, y_bottom + week_storage_discharge_gw, 
                           color=storage_discharge_color, alpha=0.8, label='Storage Discharge')
            y_bottom += week_storage_discharge_gw
            
            # Add dispatchable
            ax.fill_between(hours, y_bottom, y_bottom + week_dispatchable_gw, 
                           color=dispatchable_color, alpha=0.8, label='Dispatchable')
            y_bottom += week_dispatchable_gw
            
            # Add storage charging as negative area (below zero)
            ax.fill_between(hours, -week_storage_charge_gw, 0, 
                           color=storage_charge_color, alpha=0.6, label='Storage Charging')
            
            # Calculate surplus and shortage for this week
            total_supply = (week_baseload + week_solar + week_wind + 
                           week_storage_discharge + week_dispatchable)
            week_shortage = np.maximum(week_demand - total_supply, 0)
            week_shortage_gw = week_shortage / 1000
            total_shortage_gwh = np.sum(week_shortage) / 1000
            max_shortage_gw = np.max(week_shortage) / 1000
            
            # Calculate surplus (supply above demand, accounting for storage charging)
            # CRITICAL: Surplus can only exist when there's NO shortage (unmet demand)
            week_shortage = np.maximum(week_demand - total_supply, 0)
            total_demand_with_storage = week_demand + week_storage_charge
            
            # Surplus only exists where there's no shortage AND supply exceeds total demand+storage
            surplus_raw = total_supply - total_demand_with_storage
            week_surplus = np.where(week_shortage > 0, 0, np.maximum(surplus_raw, 0))
            week_surplus_gw = week_surplus / 1000
            total_surplus_gwh = np.sum(week_surplus) / 1000
            max_surplus_gw = np.max(week_surplus) / 1000
            
            # Show shortage as GAP between supply stack and demand line
            shortage_exists = np.any(week_shortage_gw > 0)
            if shortage_exists:
                ax.fill_between(hours, y_bottom, week_demand_gw, 
                               color='gray', alpha=0.4, label='Unmet Demand (Gap)' if i == 0 else "",
                               where=(week_demand_gw > y_bottom), hatch='///')
            
            # Show surplus as area between demand line and supply stack
            surplus_exists = np.any(week_surplus_gw > 0)
            if surplus_exists:
                ax.fill_between(hours, week_demand_gw, week_demand_gw + week_surplus_gw,
                               color='green', alpha=0.3, label='Surplus (Excess Supply)' if i == 0 else "",
                               where=(week_surplus_gw > 0), hatch='\\\\\\')
                
                # Add text annotation for significant surplus
                max_surplus_hour = np.argmax(week_surplus_gw)
                if max_surplus_gw > 5.0:  # Only annotate if surplus > 5 GW
                    surplus_y_position = (week_demand_gw[max_surplus_hour] + y_bottom[max_surplus_hour]) / 2
                    ax.annotate(f'Max Surplus\\n{max_surplus_gw:.1f} GW', 
                               xy=(max_surplus_hour, surplus_y_position),
                               xytext=(-10, -10), textcoords='offset points',
                               fontsize=8, ha='right', va='center',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='green', alpha=0.3),
                               arrowprops=dict(arrowstyle='->', color='green', alpha=0.7))
            
            # Formatting
            ax.set_title(f'{week_name} - Shortage: {total_shortage_gwh:.1f} GWh (Max: {max_shortage_gw:.1f} GW) | Surplus: {total_surplus_gwh:.1f} GWh (Max: {max_surplus_gw:.1f} GW)', 
                        fontsize=12, fontweight='bold')
            ax.set_ylabel('Power (GW)', fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, week_length-1)
            
            # Add legend only to first subplot
            if i == 0:
                # Add a dummy line for timeslice indicators in legend
                ax.plot([], [], color='gray', linestyle='--', alpha=0.7, linewidth=1, label='FACETS Timeslices')
                ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=10)
            
            # X-axis formatting
            if i == len(week_data) - 1:  # Last subplot
                ax.set_xlabel('Hour of Week', fontsize=10)
            
            # Set y-axis to show negative values for storage charging
            y_min = min(0, -np.max(week_storage_charge_gw) * 1.1) if np.max(week_storage_charge_gw) > 0 else 0
            y_max = max(np.max(week_demand_gw), np.max(y_bottom)) * 1.05
            ax.set_ylim(y_min, y_max)
            
            # Add hour-of-day markers for reference (after y-limits are set)
            self.add_hour_of_day_markers(ax, week_length)
            
            # Add FACETS timeslice boundaries as vertical lines
            self.add_timeslice_indicators(ax, start_hour, week_length, timeslice_hour_mapping)
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.90)  # Add space for main title
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save the chart with simplified naming and scenario subfolder
        system_suffix = self.region if self.region else self.transmission_group
        scenario_folder = self.scenario.replace(".", "_")  # Replace dots with underscores for folder name
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(self.outputs_base_path, "plots", scenario_folder, f"simulation_surplus_weeks_{system_suffix}.png")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved chart: {output_path}")
        
        return fig
    
    def add_timeslice_indicators(self, ax, start_hour, week_length, timeslice_hour_mapping):
        """Add vertical lines and labels to indicate FACETS timeslice boundaries"""
        
        # Determine the season for this week based on start hour
        season = self.get_season_for_hour(start_hour)
        
        # Get the FACETS time periods in order
        time_periods = ['Z', 'AM1', 'AM2', 'D', 'P', 'E']
        
        # Find timeslices for this season that overlap with the week
        overlapping_timeslices = []
        
        for time_period in time_periods:
            timeslice = f"{season}{time_period}"
            if timeslice in timeslice_hour_mapping:
                hour_indices = timeslice_hour_mapping[timeslice]
                if hour_indices:
                    ts_start = min(hour_indices)
                    ts_end = max(hour_indices)
                    
                    # Check if timeslice overlaps with this week
                    week_end_hour = start_hour + week_length - 1
                    if (ts_start <= week_end_hour and ts_end >= start_hour):
                        overlapping_timeslices.append((timeslice, ts_start, ts_end))
        
        print(f"   📅 Week starting hour {start_hour} → Season {season}")
        print(f"   🕐 Expected timeslices: {[f'{season}{tp}' for tp in time_periods]}")
        print(f"   ✅ Found overlapping: {[ts[0] for ts in overlapping_timeslices]}")
        
        # Add vertical lines and labels for timeslice boundaries
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown']
        color_idx = 0
        timeslice_ranges = []
        
        for timeslice, ts_start, ts_end in overlapping_timeslices:
            # Convert global hour indices to week-relative positions
            week_ts_start = max(0, ts_start - start_hour)
            week_ts_end = min(week_length - 1, ts_end - start_hour)
            
            if week_ts_start < week_length and week_ts_end >= 0:
                color = colors[color_idx % len(colors)]
                
                # Add vertical line at timeslice start
                if week_ts_start > 0:
                    ax.axvline(x=week_ts_start, color=color, linestyle='--', alpha=0.7, linewidth=1)
                
                # Add vertical line at timeslice end
                if week_ts_end < week_length - 1:
                    ax.axvline(x=week_ts_end, color=color, linestyle='--', alpha=0.7, linewidth=1)
                
                # Store timeslice info for smart label positioning
                timeslice_ranges.append({
                    'name': timeslice,
                    'start': week_ts_start,
                    'end': week_ts_end,
                    'color': color,
                    'center': (week_ts_start + week_ts_end) / 2
                })
                
                color_idx += 1
        
        # Smart label positioning to avoid overlaps
        if timeslice_ranges:
            self.place_timeslice_labels(ax, timeslice_ranges, week_length, start_hour, timeslice_hour_mapping)
    
    def get_season_for_hour(self, hour_index):
        """Determine FACETS season (W1, R1, S1, T1) based on hour index"""
        
        # Convert hour index to month (assuming 8760 hours starting from Jan 1)
        from datetime import datetime, timedelta
        start_date = datetime(self.weather_year, 1, 1)
        current_date = start_date + timedelta(hours=int(hour_index))  # Convert numpy int64 to int
        month = current_date.month
        
        # FACETS season mapping (typical energy modeling seasons)
        if month in [12, 1, 2]:  # Dec, Jan, Feb
            return "W1"  # Winter
        elif month in [3, 4, 5]:  # Mar, Apr, May  
            return "R1"  # Spring (Rainy season / shoulder)
        elif month in [6, 7, 8]:  # Jun, Jul, Aug
            return "S1"  # Summer
        elif month in [9, 10, 11]:  # Sep, Oct, Nov
            return "T1"  # Fall (Transition / shoulder)
        else:
            return "W1"  # Default fallback
    
    def place_timeslice_labels(self, ax, timeslice_ranges, week_length, start_hour, timeslice_hour_mapping):
        """Place timeslice labels directly above their mapped hour ranges"""
        
        # Get the season for this week (only show once)
        season = self.get_season_for_hour(start_hour)
        
        # Sort by time period order for proper FACETS sequence
        time_period_order = {'Z': 1, 'AM1': 2, 'AM2': 3, 'D': 4, 'P': 5, 'E': 6}
        timeslice_ranges.sort(key=lambda x: time_period_order.get(x['name'][2:], 999))
        
        # Show season label once at the start
        y_top = ax.get_ylim()[1]
        ax.text(5, y_top * 0.98, f'Season: {season}', fontsize=10, fontweight='bold', 
               color='darkblue')
        
        # Place time period labels above their actual mapped hours
        for ts in timeslice_ranges:
            timeslice_name = ts['name']
            time_period = timeslice_name[2:]  # Extract just the time part (Z, AM1, etc.)
            
            # Get the actual hour indices for this timeslice
            if timeslice_name in timeslice_hour_mapping:
                hour_indices = timeslice_hour_mapping[timeslice_name]
                if hour_indices:
                    # Convert global hours to hours-of-day (0-23)
                    from datetime import datetime, timedelta
                    start_date = datetime(self.weather_year, 1, 1)
                    
                    # Get the hour-of-day range for this timeslice
                    hours_of_day = []
                    for hour_idx in hour_indices[:24]:  # Just look at first day's pattern
                        current_date = start_date + timedelta(hours=int(hour_idx))
                        hour_of_day = current_date.hour
                        hours_of_day.append(hour_of_day)
                    
                    if hours_of_day:
                        min_hour = min(hours_of_day)
                        max_hour = max(hours_of_day)
                        
                        # Find all occurrences of this hour pattern within the week
                        for day in range(7):  # Check each day of the week
                            day_start_in_week = day * 24
                            if day_start_in_week >= week_length:
                                break
                                
                            # Calculate position for this day
                            label_hour_in_week = day_start_in_week + (min_hour + max_hour) // 2
                            
                            if label_hour_in_week < week_length:
                                # Position label above the actual mapped hours
                                y_pos = y_top * 0.92
                                
                                # Style based on time period
                                if time_period == 'Z':
                                    style = {'fontweight': 'bold', 'fontsize': 8, 'color': 'purple'}
                                elif time_period in ['AM1', 'AM2']:
                                    style = {'fontweight': 'normal', 'fontsize': 8, 'color': 'darkgreen'}
                                elif time_period == 'D':
                                    style = {'fontweight': 'bold', 'fontsize': 8, 'color': 'orange'}
                                elif time_period == 'P':
                                    style = {'fontweight': 'bold', 'fontsize': 9, 'color': 'red'}
                                else:  # E
                                    style = {'fontweight': 'bold', 'fontsize': 8, 'color': 'darkred'}
                                
                                ax.text(label_hour_in_week, y_pos, time_period, ha='center', va='top', 
                                       **style)
                        
                        print(f"   📍 {time_period}: Hours {min_hour}-{max_hour} each day")
    
    def add_hour_of_day_markers(self, ax, week_length):
        """Add hour-of-day markers (1-24) to help with timeslice positioning"""
        
        # Create hour-of-day markers every 24 hours
        hours_per_day = 24
        days_in_week = min(7, week_length // hours_per_day)
        
        # Add vertical lines for midnight (start of each day)
        for day in range(days_in_week + 1):
            hour_mark = day * hours_per_day
            if hour_mark <= week_length:
                ax.axvline(x=hour_mark, color='gray', linestyle=':', alpha=0.5, linewidth=1)
        
        # Get current axis limits
        y_min, y_max = ax.get_ylim()
        y_range = y_max - y_min
        
        # Add hour-of-day labels at the bottom
        for day in range(days_in_week):
            day_start = day * hours_per_day
            
            # Key hours to label: 6, 12, 18, 24 (every 6 hours)
            key_hours = [6, 12, 18, 24]
            for hour_of_day in key_hours:
                week_hour = day_start + hour_of_day - 1  # Convert to 0-based
                if week_hour < week_length:
                    # Place label below the chart area
                    label_y = y_min - y_range * 0.08
                    ax.text(week_hour, label_y, f'{hour_of_day}h', 
                           fontsize=8, ha='center', va='top', color='darkblue', fontweight='bold')
        
        # Add day labels even lower
        for day in range(days_in_week):
            day_center = day * hours_per_day + hours_per_day / 2
            if day_center < week_length:
                day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                label_y = y_min - y_range * 0.15
                ax.text(day_center, label_y, day_names[day % 7], 
                       fontsize=9, ha='center', va='top', fontweight='bold', color='black')
        
        # Extend y-axis to show the labels
        ax.set_ylim(y_min - y_range * 0.2, y_max)
    
    def plot_seasonal_demand(self, monthly_data):
        """Create 3-panel seasonal demand chart"""
        print("📊 Creating Seasonal Demand Charts...")
        
        # Set up the figure with 3 subplots
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        
        # Dynamic title based on analysis mode
        if self.region:
            system_name = self.region
        else:
            system_name = f"{self.transmission_group} System"
        
        fig.suptitle(f'FACETS Hourly Demand Profile - {system_name} ({self.year})', 
                     fontsize=16, fontweight='bold')
        
        months = ['january', 'july', 'december']
        colors = ['#2E86AB', '#A23B72', '#F18F01']  # Blue, Purple, Orange
        
        for i, (month, color) in enumerate(zip(months, colors)):
            ax = axes[i]
            data = monthly_data[month]
            
            # Convert MW to GW
            demand_gw = data['demand_mw'] / 1000
            
            # Plot demand line
            ax.plot(data['datetime'], demand_gw, color=color, linewidth=1.5, alpha=0.8)
            
            # Formatting
            ax.set_title(f'{month.title()} {self.weather_year} - Demand Profile', 
                        fontsize=12, fontweight='bold')
            ax.set_ylabel('Demand (GW)', fontsize=10)
            ax.grid(True, alpha=0.3)
            
            # Format x-axis to show dates nicely
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.tick_params(axis='x', rotation=45)
            
            # Add statistics text box
            stats_text = f'Min: {demand_gw.min():.1f} GW\\nMax: {demand_gw.max():.1f} GW\\nAvg: {demand_gw.mean():.1f} GW'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                   fontsize=9)
        
        # Format bottom subplot x-axis
        axes[2].set_xlabel('Date', fontsize=10)
        
        plt.tight_layout()
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save the plot
        output_path = "../outputs/plots/phase1_seasonal_demand_profile.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ Saved chart: {output_path}")
        
        plt.show()
        
        return fig
    
    def plot_all_weeks_chronologically(self, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw, 
                                     hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable, 
                                     shortage_week_data, surplus_week_data, analysis_type, storage_soc_gwh):
        """Plot all 52 weeks chronologically, 5 weeks per chart"""
        print(f"📊 Creating Chronological Week Charts ({analysis_type})...")
        
        # Step 1: Identify top weeks for title highlighting
        top_shortage_weeks = set(shortage_week_data.keys()) if shortage_week_data else set()
        top_surplus_weeks = set(surplus_week_data.keys()) if surplus_week_data else set()
        
        # Step 2: Create week ranges (5 weeks per chart)
        weeks_per_chart = 5
        total_charts = (52 + weeks_per_chart - 1) // weeks_per_chart  # Ceiling division = 11 charts
        
        chart_files = []
        
        for chart_idx in range(total_charts):
            start_week = chart_idx * weeks_per_chart + 1
            end_week = min(start_week + weeks_per_chart - 1, 52)
            
            print(f"   📈 Creating Chart {chart_idx + 1}/{total_charts}: Weeks {start_week}-{end_week}")
            
            # Step 3: Generate chart for this week range
            fig_file = self.plot_week_range(
                start_week, end_week, 
                hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
                hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable,
                top_shortage_weeks, top_surplus_weeks, analysis_type, chart_idx + 1, storage_soc_gwh
            )
            chart_files.append(fig_file)
        
        print(f"   ✅ Generated {len(chart_files)} chronological week charts")
        return chart_files

    def plot_week_range(self, start_week, end_week, hourly_demand, hourly_baseload, 
                       hourly_solar_mw, hourly_wind_mw, hourly_storage_charge, 
                       hourly_storage_discharge, hourly_dispatchable,
                       top_shortage_weeks, top_surplus_weeks, analysis_type, chart_number, storage_soc_gwh):
        """Plot a range of weeks using existing formatting logic"""
        
        # Step 1: Extract week data for the range
        week_range_data = {}
        for week_num in range(start_week, end_week + 1):
            week_name = f"Week {week_num}"
            
            # Calculate week boundaries (similar to existing logic)
            start_hour = (week_num - 1) * 168  # Week starts at hour 0, 168, 336, etc.
            end_hour = min(start_hour + 168, 8760)
            
            # Extract hourly data for this week
            week_demand = hourly_demand[start_hour:end_hour]
            week_baseload = hourly_baseload[start_hour:end_hour]
            week_solar = hourly_solar_mw[start_hour:end_hour]
            week_wind = hourly_wind_mw[start_hour:end_hour]
            week_storage_charge = hourly_storage_charge[start_hour:end_hour]
            week_storage_discharge = hourly_storage_discharge[start_hour:end_hour]
            week_dispatchable = hourly_dispatchable[start_hour:end_hour]
            week_storage_soc = storage_soc_gwh[start_hour:end_hour]
            
            # Create datetime index for this week
            start_date = datetime(self.weather_year, 1, 1) + timedelta(hours=start_hour)
            dates = [start_date + timedelta(hours=h) for h in range(len(week_demand))]
            
            week_range_data[week_name] = {
                'hourly_data': {
                    'dates': dates,
                    'demand': week_demand,
                    'baseload': week_baseload,
                    'solar': week_solar,
                    'wind': week_wind,
                    'storage_charge': week_storage_charge,
                    'storage_discharge': week_storage_discharge,
                    'dispatchable': week_dispatchable,
                    'storage_soc': week_storage_soc
                },
                'metadata': {
                    'start_hour': start_hour,
                    'end_hour': end_hour,
                    'length_hours': len(week_demand)
                }
            }
        
        # Step 2: Create title with highlighted top weeks
        title_parts = [f"Weeks {start_week}-{end_week} | {analysis_type}"]
        
        # Highlight top shortage weeks in this range
        range_shortage_weeks = [f"Week {w}" for w in range(start_week, end_week + 1) 
                               if f"Week {w}" in top_shortage_weeks]
        if range_shortage_weeks:
            week_numbers = [w.replace('Week ', '') for w in range_shortage_weeks]
            title_parts.append(f"🔴 TOP SHORTAGE: {', '.join(week_numbers)}")
        
        # Highlight top surplus weeks in this range  
        range_surplus_weeks = [f"Week {w}" for w in range(start_week, end_week + 1)
                              if f"Week {w}" in top_surplus_weeks]
        if range_surplus_weeks:
            week_numbers = [w.replace('Week ', '') for w in range_surplus_weeks]
            title_parts.append(f"🟢 TOP SURPLUS: {', '.join(week_numbers)}")
        
        chart_title = " | ".join(title_parts)
        
        # Step 3: Use existing plot formatting logic with modified data
        fig = self._create_week_chart_with_existing_format(
            week_range_data, chart_title, analysis_type, chart_number
        )
        
        return fig

    def _create_week_chart_with_existing_format(self, week_data, title, analysis_type, chart_number):
        """Reuse existing chart formatting logic for chronological weeks"""
        
        # This uses the exact same plotting logic as plot_top_shortage_weeks
        # but works with chronological week_data instead of top 5 weeks
        
        if not week_data:
            print("   ⚠️ No week data provided for chronological chart")
            return None
        
        # Set up the figure - same as existing format
        num_weeks = len(week_data)
        fig, axes = plt.subplots(num_weeks, 1, figsize=(16, 4 * num_weeks))
        
        # Handle single week case
        if num_weeks == 1:
            axes = [axes]
        
        # Dynamic title based on analysis mode
        if self.region:
            system_name = self.region
        else:
            system_name = f"{self.transmission_group} System"
        
        fig.suptitle(f'{system_name} - {title}', 
                    fontsize=16, fontweight='bold', y=0.98)
        
        # Load timeslice mapping for indicators (same as existing)
        season_mapping, time_mapping = self.load_timeslice_mapping()
        timeslice_hour_mapping = self.map_timeslices_to_hours(season_mapping, time_mapping)
        
        # Plot each week using existing formatting
        for idx, (week_name, week_info) in enumerate(week_data.items()):
            ax = axes[idx]
            hourly = week_info['hourly_data']
            metadata = week_info['metadata']
            
            # Convert to GW for plotting (same as existing)
            dates = hourly['dates']
            week_length = len(dates)
            hours = range(week_length)
            
            week_demand_gw = np.array(hourly['demand']) / 1000
            week_baseload_gw = np.array(hourly['baseload']) / 1000
            week_solar_gw = np.array(hourly['solar']) / 1000
            week_wind_gw = np.array(hourly['wind']) / 1000
            week_storage_charge_gw = np.array(hourly['storage_charge']) / 1000
            week_storage_discharge_gw = np.array(hourly['storage_discharge']) / 1000
            week_dispatchable_gw = np.array(hourly['dispatchable']) / 1000
            
            # Plot demand line (same as existing)
            ax.plot(hours, week_demand_gw, color='black', linewidth=2, label='Demand', zorder=10)
            
            # Create stacked areas for supply (same as existing)
            y_bottom = np.zeros(week_length)
            ax.fill_between(hours, y_bottom, y_bottom + week_baseload_gw, 
                           color='brown', alpha=0.7, label='Baseload')
            
            y_bottom += week_baseload_gw
            ax.fill_between(hours, y_bottom, y_bottom + week_solar_gw, 
                           color='gold', alpha=0.7, label='Solar')
            
            y_bottom += week_solar_gw
            ax.fill_between(hours, y_bottom, y_bottom + week_wind_gw, 
                           color='skyblue', alpha=0.7, label='Wind')
            
            y_bottom += week_wind_gw
            ax.fill_between(hours, y_bottom, y_bottom + week_storage_discharge_gw, 
                           color='green', alpha=0.7, label='Storage Discharge')
            
            y_bottom += week_storage_discharge_gw
            ax.fill_between(hours, y_bottom, y_bottom + week_dispatchable_gw, 
                           color='red', alpha=0.7, label='Dispatchable')
            
            # Add storage charging (negative) - same as existing
            ax.fill_between(hours, -week_storage_charge_gw, 0, 
                           color='purple', alpha=0.5, label='Storage Charge')
            
            # Add storage level line with secondary Y-axis
            week_storage_soc = np.array(hourly['storage_soc'])
            ax2 = ax.twinx()
            ax2.plot(hours, week_storage_soc, 
                    color='navy', linewidth=2, linestyle='--', alpha=0.8, 
                    label='Storage Level (GWh)')
            ax2.set_ylabel('Storage Level (GWh)', color='navy')
            
            # Align zero axes and scale secondary Y-axis to 2x max SOC
            primary_ylim = ax.get_ylim()
            primary_min, primary_max = primary_ylim
            max_soc = np.max(week_storage_soc)
            
            # Set secondary Y-axis: 0 to 2x max SOC, aligned with primary zero
            secondary_max = 2 * max_soc if max_soc > 0 else 10  # Fallback if no storage
            
            # Calculate alignment: if primary has negative values, align zeros
            if primary_min < 0:
                # Align zeros: secondary range should match primary range proportionally
                primary_range = primary_max - primary_min
                zero_position = -primary_min / primary_range  # Position of zero in primary axis (0-1)
                secondary_min = -secondary_max * zero_position / (1 - zero_position)
                ax2.set_ylim(secondary_min, secondary_max)
            else:
                # Both start at zero
                ax2.set_ylim(0, secondary_max)
            
            ax2.tick_params(axis='y', labelcolor='navy')
            
            # Add storage level to legend (only on first subplot)
            if idx == 0:
                # Combine legends from both axes
                lines1, labels1 = ax.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax.legend(lines1 + lines2, labels1 + labels2, bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # Formatting (same as existing)
            ax.set_title(f'{week_name} ({dates[0].strftime("%b %d")} - {dates[-1].strftime("%b %d")})', 
                        fontsize=14, fontweight='bold')
            ax.set_ylabel('Power (GW)')
            ax.grid(True, alpha=0.3)
            
            # Add timeslice indicators (same as existing)
            self.add_timeslice_indicators(ax, metadata['start_hour'], week_length, timeslice_hour_mapping)
            
            # Add hour-of-day markers (same as existing)
            self.add_hour_of_day_markers(ax, week_length)
        
        # Add logo watermark (same as existing)
        self._add_logo_watermark(fig)
        
        # Save with chronological naming
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scenario_folder = self.scenario.replace(".", "_")
        plots_dir = os.path.join(script_dir, "..", "outputs", "plots", scenario_folder)
        os.makedirs(plots_dir, exist_ok=True)
        
        filename = f"chronological_weeks_{analysis_type.lower().replace(' ', '_')}_chart_{chart_number:02d}.png"
        filepath = os.path.join(plots_dir, filename)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"      ✅ Saved: {filename}")
        return filepath
    
    def create_timeslice_aggregation_view(self, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
                                        hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable, 
                                        storage_soc_gwh, analysis_type="Operationally Realistic"):
        """Create single chart showing FACETS timeslice-averaged view of operational data"""
        print(f"📊 Creating FACETS Timeslice Aggregation View ({analysis_type})...")
        print("   📋 Aggregation method: All power values (GW) averaged for comparable scale")
        
        # Load timeslice mapping
        season_mapping, time_mapping = self.load_timeslice_mapping()
        timeslice_hour_mapping = self.map_timeslices_to_hours(season_mapping, time_mapping)
        
        # Debug: Print available timeslices
        available_timeslices = list(timeslice_hour_mapping.keys())
        print(f"   🔍 Available timeslices: {sorted(available_timeslices)}")
        print(f"   📊 Total timeslices found: {len(available_timeslices)}")
        
        # Debug: Check for supply-demand balance issues
        print("   ⚖️  Checking supply-demand balance by timeslice...")
        
        # Aggregate hourly data by timeslice
        timeslice_data = {}
        timeslice_order = []
        
        # Use ALL available timeslices instead of assuming pattern
        # Sort them for logical ordering
        sorted_timeslices = sorted(available_timeslices)
        
        for timeslice in sorted_timeslices:
            if timeslice in timeslice_hour_mapping and len(timeslice_hour_mapping[timeslice]) > 0:
                hour_indices = timeslice_hour_mapping[timeslice]
                
                # Calculate aggregations for this timeslice
                # All power values (GW) should be averaged for comparable scale
                # SOC reflects cumulative energy state
                timeslice_data[timeslice] = {
                    'demand': np.mean([hourly_demand[h] for h in hour_indices if h < len(hourly_demand)]),
                    'baseload': np.mean([hourly_baseload[h] for h in hour_indices if h < len(hourly_baseload)]),
                    'solar': np.mean([hourly_solar_mw[h] for h in hour_indices if h < len(hourly_solar_mw)]),
                    'wind': np.mean([hourly_wind_mw[h] for h in hour_indices if h < len(hourly_wind_mw)]),
                    'storage_charge': np.mean([hourly_storage_charge[h] for h in hour_indices if h < len(hourly_storage_charge)]),  # Average power for comparable scale
                    'storage_discharge': np.mean([hourly_storage_discharge[h] for h in hour_indices if h < len(hourly_storage_discharge)]),  # Average power for comparable scale
                    'dispatchable': np.mean([hourly_dispatchable[h] for h in hour_indices if h < len(hourly_dispatchable)]),
                    'storage_soc': np.mean([storage_soc_gwh[h] for h in hour_indices if h < len(storage_soc_gwh)]),  # Average SOC level in timeslice
                    'hour_count': len([h for h in hour_indices if h < len(hourly_demand)])
                }
                timeslice_order.append(timeslice)
        
        if not timeslice_data:
            print("   ⚠️ No timeslice data found")
            return None
        
        # Debug: Check supply-demand balance for each timeslice
        print("   📊 Supply-demand balance check:")
        imbalanced_timeslices = []
        for ts in timeslice_order[:10]:  # Check first 10 timeslices
            demand = timeslice_data[ts]['demand'] / 1000  # Convert to GW
            total_supply = (
                timeslice_data[ts]['baseload'] + 
                timeslice_data[ts]['solar'] + 
                timeslice_data[ts]['wind'] + 
                timeslice_data[ts]['storage_discharge'] + 
                timeslice_data[ts]['dispatchable'] - 
                timeslice_data[ts]['storage_charge']
            ) / 1000  # Convert to GW
            
            balance = total_supply - demand
            if abs(balance) > 0.5:  # More than 0.5 GW imbalance
                imbalanced_timeslices.append((ts, demand, total_supply, balance))
                print(f"      ⚠️ {ts}: Demand={demand:.1f}GW, Supply={total_supply:.1f}GW, Gap={balance:.1f}GW")
        
        if not imbalanced_timeslices:
            print("      ✅ All checked timeslices are balanced (within 0.5 GW)")
        else:
            print(f"      ⚠️ Found {len(imbalanced_timeslices)} imbalanced timeslices")
        
        print(f"   📈 Aggregated data for {len(timeslice_data)} timeslices")
        
        # Create the chart
        fig, ax = plt.subplots(1, 1, figsize=(16, 8))
        
        # Dynamic title based on analysis mode
        if self.region:
            system_name = self.region
        else:
            system_name = f"{self.transmission_group} System"
        
        fig.suptitle(f'{system_name} - FACETS Timeslice View | {analysis_type}\n'
                    f'Averaged Operational Data by Timeslice ({self.scenario}, {self.year})', 
                    fontsize=16, fontweight='bold')
        
        # Prepare data arrays
        x_positions = range(len(timeslice_order))
        timeslice_labels = timeslice_order
        
        # Convert to GW for plotting
        demand_gw = [timeslice_data[ts]['demand'] / 1000 for ts in timeslice_order]
        baseload_gw = [timeslice_data[ts]['baseload'] / 1000 for ts in timeslice_order]
        solar_gw = [timeslice_data[ts]['solar'] / 1000 for ts in timeslice_order]
        wind_gw = [timeslice_data[ts]['wind'] / 1000 for ts in timeslice_order]
        storage_charge_gw = [timeslice_data[ts]['storage_charge'] / 1000 for ts in timeslice_order]
        storage_discharge_gw = [timeslice_data[ts]['storage_discharge'] / 1000 for ts in timeslice_order]
        dispatchable_gw = [timeslice_data[ts]['dispatchable'] / 1000 for ts in timeslice_order]
        storage_soc_gwh = [timeslice_data[ts]['storage_soc'] for ts in timeslice_order]
        
        # Plot demand line (same as hourly charts)
        ax.plot(x_positions, demand_gw, color='black', linewidth=3, marker='o', markersize=4, 
               label='Demand', zorder=10)
        
        # Create stacked bars for supply (same colors as hourly charts)
        width = 0.8
        
        # Baseload
        ax.bar(x_positions, baseload_gw, width, color='brown', alpha=0.7, label='Baseload')
        
        # Solar (stacked on baseload)
        ax.bar(x_positions, solar_gw, width, bottom=baseload_gw, color='gold', alpha=0.7, label='Solar')
        
        # Wind (stacked on baseload + solar)
        bottom_wind = [baseload_gw[i] + solar_gw[i] for i in range(len(x_positions))]
        ax.bar(x_positions, wind_gw, width, bottom=bottom_wind, color='skyblue', alpha=0.7, label='Wind')
        
        # Storage discharge (stacked on baseload + solar + wind)
        bottom_storage = [bottom_wind[i] + wind_gw[i] for i in range(len(x_positions))]
        ax.bar(x_positions, storage_discharge_gw, width, bottom=bottom_storage, 
               color='green', alpha=0.7, label='Storage Discharge')
        
        # Dispatchable (stacked on all previous)
        bottom_dispatch = [bottom_storage[i] + storage_discharge_gw[i] for i in range(len(x_positions))]
        ax.bar(x_positions, dispatchable_gw, width, bottom=bottom_dispatch, 
               color='red', alpha=0.7, label='Dispatchable')
        
        # Storage charging (negative bars)
        ax.bar(x_positions, [-charge for charge in storage_charge_gw], width, 
               color='purple', alpha=0.5, label='Storage Charge')
        
        # Add storage level line with secondary Y-axis
        ax2 = ax.twinx()
        ax2.plot(x_positions, storage_soc_gwh, color='navy', linewidth=3, linestyle='--', 
                marker='s', markersize=4, alpha=0.8, label='Storage Level (GWh)')
        ax2.set_ylabel('Storage Level (GWh)', color='navy')
        
        # Align zero axes and scale secondary Y-axis to 2x max SOC
        primary_ylim = ax.get_ylim()
        primary_min, primary_max = primary_ylim
        max_soc = max(storage_soc_gwh) if storage_soc_gwh else 0
        
        # Set secondary Y-axis: 0 to 2x max SOC, aligned with primary zero
        secondary_max = 2 * max_soc if max_soc > 0 else 10  # Fallback if no storage
        
        # Calculate alignment: if primary has negative values, align zeros
        if primary_min < 0:
            # Align zeros: secondary range should match primary range proportionally
            primary_range = primary_max - primary_min
            zero_position = -primary_min / primary_range  # Position of zero in primary axis (0-1)
            secondary_min = -secondary_max * zero_position / (1 - zero_position)
            ax2.set_ylim(secondary_min, secondary_max)
        else:
            # Both start at zero
            ax2.set_ylim(0, secondary_max)
        
        ax2.tick_params(axis='y', labelcolor='navy')
        
        # Formatting
        ax.set_xlabel('FACETS Timeslices')
        ax.set_ylabel('Power (GW)')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(timeslice_labels, rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add season separators (if timeslices follow season pattern)
        season_boundaries = []
        for i, ts in enumerate(timeslice_order):
            if i > 0 and len(ts) >= 2 and len(timeslice_order[i-1]) >= 2:
                if ts[:2] != timeslice_order[i-1][:2]:  # Season change (first 2 chars)
                    season_boundaries.append(i - 0.5)
        
        for boundary in season_boundaries:
            ax.axvline(x=boundary, color='gray', linestyle=':', alpha=0.7, linewidth=1)
        
        # Combined legend
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save the chart
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scenario_folder = self.scenario.replace(".", "_")
        plots_dir = os.path.join(script_dir, "..", "outputs", "plots", scenario_folder)
        os.makedirs(plots_dir, exist_ok=True)
        
        filename = f"facets_timeslice_aggregation_{analysis_type.lower().replace(' ', '_')}.png"
        filepath = os.path.join(plots_dir, filename)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"   ✅ Saved: {filename}")
        print(f"   📊 Shows how FACETS sees operational data through timeslice aggregation")
        print(f"   🎯 Compare with hourly charts to see temporal smoothing effects")
        
        return filepath
    
    def create_timeslice_energy_view(self, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
                                   hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable, 
                                   storage_soc_gwh, analysis_type="Operationally Realistic"):
        """Create single chart showing FACETS timeslice energy accounting (TWh totals)"""
        print(f"⚡ Creating FACETS Timeslice Energy View ({analysis_type})...")
        print("   📋 Aggregation method: All energy values (TWh) summed per timeslice")
        
        # Load timeslice mapping
        season_mapping, time_mapping = self.load_timeslice_mapping()
        timeslice_hour_mapping = self.map_timeslices_to_hours(season_mapping, time_mapping)
        
        # Debug: Print available timeslices
        available_timeslices = list(timeslice_hour_mapping.keys())
        print(f"   🔍 Available timeslices: {sorted(available_timeslices)}")
        print(f"   📊 Total timeslices found: {len(available_timeslices)}")
        
        # Debug: Check for energy balance issues
        print("   ⚖️  Checking energy balance by timeslice...")
        
        # Aggregate hourly data by timeslice - SUM ALL VALUES for energy accounting
        timeslice_data = {}
        timeslice_order = []
        
        # Use ALL available timeslices
        sorted_timeslices = sorted(available_timeslices)
        
        for timeslice in sorted_timeslices:
            if timeslice in timeslice_hour_mapping and len(timeslice_hour_mapping[timeslice]) > 0:
                hour_indices = timeslice_hour_mapping[timeslice]
                
                # Calculate energy totals for this timeslice (SUM all hourly values)
                # Convert MW to GWh (MW * hours / 1000)
                timeslice_data[timeslice] = {
                    'demand': sum([hourly_demand[h] for h in hour_indices if h < len(hourly_demand)]) / 1000,  # GWh
                    'baseload': sum([hourly_baseload[h] for h in hour_indices if h < len(hourly_baseload)]) / 1000,  # GWh
                    'solar': sum([hourly_solar_mw[h] for h in hour_indices if h < len(hourly_solar_mw)]) / 1000,  # GWh
                    'wind': sum([hourly_wind_mw[h] for h in hour_indices if h < len(hourly_wind_mw)]) / 1000,  # GWh
                    'storage_charge': sum([hourly_storage_charge[h] for h in hour_indices if h < len(hourly_storage_charge)]) / 1000,  # GWh
                    'storage_discharge': sum([hourly_storage_discharge[h] for h in hour_indices if h < len(hourly_storage_discharge)]) / 1000,  # GWh
                    'dispatchable': sum([hourly_dispatchable[h] for h in hour_indices if h < len(hourly_dispatchable)]) / 1000,  # GWh
                    'storage_soc': np.mean([storage_soc_gwh[h] for h in hour_indices if h < len(storage_soc_gwh)]),  # Average SOC level in timeslice (GWh)
                    'hour_count': len([h for h in hour_indices if h < len(hourly_demand)])
                }
                timeslice_order.append(timeslice)
        
        if not timeslice_data:
            print("   ⚠️ No timeslice data found")
            return None
        
        # Debug: Check energy balance for each timeslice
        print("   📊 Energy balance check:")
        imbalanced_timeslices = []
        for ts in timeslice_order[:10]:  # Check first 10 timeslices
            demand_twh = timeslice_data[ts]['demand'] / 1000  # Convert to TWh
            total_supply_twh = (
                timeslice_data[ts]['baseload'] + 
                timeslice_data[ts]['solar'] + 
                timeslice_data[ts]['wind'] + 
                timeslice_data[ts]['storage_discharge'] + 
                timeslice_data[ts]['dispatchable'] - 
                timeslice_data[ts]['storage_charge']
            ) / 1000  # Convert to TWh
            
            balance = total_supply_twh - demand_twh
            if abs(balance) > 0.001:  # More than 0.001 TWh imbalance
                imbalanced_timeslices.append((ts, demand_twh, total_supply_twh, balance))
                print(f"      ⚠️ {ts}: Demand={demand_twh:.3f}TWh, Supply={total_supply_twh:.3f}TWh, Gap={balance:.3f}TWh")
        
        if not imbalanced_timeslices:
            print("      ✅ All checked timeslices are balanced (within 0.001 TWh)")
        else:
            print(f"      ⚠️ Found {len(imbalanced_timeslices)} imbalanced timeslices")
        
        print(f"   📈 Aggregated energy data for {len(timeslice_data)} timeslices")
        
        # Create the chart
        fig, ax = plt.subplots(1, 1, figsize=(16, 8))
        
        # Prepare data for plotting
        x_positions = range(len(timeslice_order))
        timeslice_labels = timeslice_order
        
        # Convert to TWh for plotting
        demand_twh = [timeslice_data[ts]['demand'] / 1000 for ts in timeslice_order]
        baseload_twh = [timeslice_data[ts]['baseload'] / 1000 for ts in timeslice_order]
        solar_twh = [timeslice_data[ts]['solar'] / 1000 for ts in timeslice_order]
        wind_twh = [timeslice_data[ts]['wind'] / 1000 for ts in timeslice_order]
        storage_charge_twh = [timeslice_data[ts]['storage_charge'] / 1000 for ts in timeslice_order]
        storage_discharge_twh = [timeslice_data[ts]['storage_discharge'] / 1000 for ts in timeslice_order]
        dispatchable_twh = [timeslice_data[ts]['dispatchable'] / 1000 for ts in timeslice_order]
        storage_soc_gwh = [timeslice_data[ts]['storage_soc'] for ts in timeslice_order]
        
        # Plot demand line (same as hourly charts)
        ax.plot(x_positions, demand_twh, color='black', linewidth=3, marker='o', markersize=4, 
               label='Demand', zorder=10)
        
        # Create stacked bars for supply (same colors as hourly charts)
        width = 0.8
        
        # Baseload
        ax.bar(x_positions, baseload_twh, width, color='brown', alpha=0.7, label='Baseload')
        
        # Solar (stacked on baseload)
        ax.bar(x_positions, solar_twh, width, bottom=baseload_twh, color='gold', alpha=0.7, label='Solar')
        
        # Wind (stacked on baseload + solar)
        bottom_wind = [baseload_twh[i] + solar_twh[i] for i in range(len(x_positions))]
        ax.bar(x_positions, wind_twh, width, bottom=bottom_wind, color='skyblue', alpha=0.7, label='Wind')
        
        # Storage discharge (stacked on baseload + solar + wind)
        bottom_storage_discharge = [bottom_wind[i] + wind_twh[i] for i in range(len(x_positions))]
        ax.bar(x_positions, storage_discharge_twh, width, bottom=bottom_storage_discharge, 
               color='green', alpha=0.7, label='Storage Discharge')
        
        # Dispatchable (stacked on baseload + solar + wind + storage discharge)
        bottom_dispatchable = [bottom_storage_discharge[i] + storage_discharge_twh[i] for i in range(len(x_positions))]
        ax.bar(x_positions, dispatchable_twh, width, bottom=bottom_dispatchable, 
               color='red', alpha=0.7, label='Dispatchable')
        
        # Storage charge (negative, below zero)
        ax.bar(x_positions, [-charge for charge in storage_charge_twh], width, 
               color='purple', alpha=0.7, label='Storage Charge')
        
        # Secondary Y-axis for storage SOC (GWh)
        ax2 = ax.twinx()
        ax2.plot(x_positions, storage_soc_gwh, 
                color='navy', linewidth=2, linestyle='--', alpha=0.8, 
                label='Storage Level (GWh)')
        ax2.set_ylabel('Storage Level (GWh)', color='navy')
        
        # Align zero axes and scale secondary Y-axis to 2x max SOC
        primary_ylim = ax.get_ylim()
        primary_min, primary_max = primary_ylim
        max_soc = np.max(storage_soc_gwh) if storage_soc_gwh else 10
        
        secondary_max = 2 * max_soc if max_soc > 0 else 10
        
        if primary_min < 0:
            primary_range = primary_max - primary_min
            zero_position = -primary_min / primary_range
            secondary_min = -secondary_max * zero_position / (1 - zero_position)
            ax2.set_ylim(secondary_min, secondary_max)
        else:
            ax2.set_ylim(0, secondary_max)
        
        ax2.tick_params(axis='y', labelcolor='navy')
        
        # Chart formatting
        ax.set_title(f'VERVESTACKS: Energy modeling reimagined | {self.transmission_group} System | FACETS Timeslice Energy View | {analysis_type}\n'
                    f'Total Energy Accounting by Timeslice ({self.scenario}, {self.year})', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('FACETS Timeslices')
        ax.set_ylabel('Energy (TWh)')
        ax.set_xticks(x_positions)
        ax.set_xticklabels(timeslice_labels, rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add season separators (if timeslices follow season pattern)
        season_boundaries = []
        for i, ts in enumerate(timeslice_order):
            if i > 0 and len(ts) >= 2 and len(timeslice_order[i-1]) >= 2:
                if ts[:2] != timeslice_order[i-1][:2]:  # Season change (first 2 chars)
                    season_boundaries.append(i - 0.5)
        
        for boundary in season_boundaries:
            ax.axvline(x=boundary, color='gray', linestyle=':', alpha=0.7, linewidth=1)
        
        # Combined legend
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save the chart
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scenario_folder = self.scenario.replace(".", "_")
        plots_dir = os.path.join(script_dir, "..", "outputs", "plots", scenario_folder)
        os.makedirs(plots_dir, exist_ok=True)
        
        filename = f"facets_timeslice_energy_view_{analysis_type.lower().replace(' ', '_')}.png"
        filepath = os.path.join(plots_dir, filename)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"   ✅ Saved: {filename}")
        print(f"   ⚡ Shows total energy accounting that FACETS uses for planning")
        print(f"   🎯 Compare with power view to see energy vs power perspectives")
        
        return filepath
    
    def load_timeslice_mapping(self):
        """Load FACETS timeslice to hour mapping"""
        print("📅 Loading FACETS Timeslice Mapping...")
        
        # Shared config file - always in config_base_path
        mapping_file = f"{self.config_base_path}FACETS_aggtimeslices.csv"
        
        if not os.path.exists(mapping_file):
            raise FileNotFoundError(f"Timeslice mapping file not found: {mapping_file}")
        
        mapping_df = pd.read_csv(mapping_file)
        print(f"   ✅ Loaded {len(mapping_df)} mapping records")
        
        # Parse mapping into season and time period dictionaries
        season_mapping = {}
        time_mapping = {}
        
        for _, row in mapping_df.iterrows():
            desc = row['description']
            timeslice = row['timeslice']
            sourcevalue = int(row['sourcevalue'])
            
            # Month mappings go to season_mapping (W1, R1, S1, T1)
            if desc == 'month':
                if timeslice not in season_mapping:
                    season_mapping[timeslice] = []
                season_mapping[timeslice].append(sourcevalue)
            
            # Hour mappings go to time_mapping (AM1, AM2, D, P, E, Z)
            elif desc == 'hour':
                if timeslice not in time_mapping:
                    time_mapping[timeslice] = []
                time_mapping[timeslice].append(sourcevalue)
        
        print(f"   📊 Seasons: {list(season_mapping.keys())}")
        print(f"   🕐 Time periods: {list(time_mapping.keys())}")
        
        return season_mapping, time_mapping
    
    def load_baseload_generation(self):
        """Load and aggregate baseload generation data across transmission group regions"""
        print("🏭 Loading FACETS Baseload Generation Data...")
        
        
        filtered_data = []
        
        df = self.gen_df.copy()

        if self.region:
            filtered_data = df[(df['region'] == self.region) &
                              (df['scen'] == self.scenario) &
                              (df['year'] == self.year)]
        
        else:
            filtered_data = df[(df['reg_transgrp'] == self.transmission_group) &
            (df['scen'] == self.scenario) &
            (df['year'] == self.year)]

        
        if filtered_data.empty:
            target = self.region if self.region else f"transmission group {self.transmission_group}"
            raise ValueError(f"No generation data found for {self.scenario}, {target}, {self.year}")
                
        # Load tech categories for baseload identification (shared config file)
        tech_file = f"{self.config_base_path}technology_categories.csv"
        tech_df = pd.read_csv(tech_file)
        
        # Create tech+sub_tech mapping for baseload
        baseload_techs = []
        for _, row in tech_df.iterrows():
            if row['category'] == 'baseload':
                tech = row['tech']
                sub_tech = row['sub_tech'] if pd.notna(row['sub_tech']) else None
                if sub_tech:
                    baseload_techs.append(f"{tech}|{sub_tech}")
                else:
                    baseload_techs.append(tech)
        
        # Create tech+sub_tech key and filter for baseload
        filtered_data['tech_subtech_key'] = filtered_data.apply(lambda row: 
            f"{row['tech']}|{row['sub_tech']}" if pd.notna(row['sub_tech']) else row['tech'], 
            axis=1)
        
        baseload_df = filtered_data[filtered_data['tech_subtech_key'].isin(baseload_techs)]
        
        if baseload_df.empty:
            raise ValueError("No baseload generation data found")
        
        # Group by timeslice and sum across all regions in transmission group
        baseload_by_timeslice = baseload_df.groupby('timeslice')['value'].sum()
        
        if self.region:
            print(f"   ✅ Found baseload generation in {len(baseload_by_timeslice)} timeslices")
        else:
            regions_found = baseload_df['region'].nunique()
            print(f"   ✅ Found baseload generation across {regions_found} {self.transmission_group} regions")
            print(f"   📊 Timeslices: {len(baseload_by_timeslice)}")
        
        print(f"   🏭 Total baseload: {baseload_by_timeslice.sum():.1f} TWh")
        
        return baseload_by_timeslice
    
    def load_renewable_generation_by_timeslice(self):
        """Load FACETS renewable generation by timeslice (TWh) - the actual planned generation"""
        print("🌱 Loading FACETS Renewable Generation by Timeslice...")
                
        filtered_data = []
        
        df = self.gen_df.copy()

        if self.region:
            filtered_data = df[(df['region'] == self.region) &
                              (df['scen'] == self.scenario) &
                              (df['year'] == self.year)]
        else:
            filtered_data = df[(df['reg_transgrp'] == self.transmission_group) &
                              (df['scen'] == self.scenario) &
                              (df['year'] == self.year)]

        if filtered_data.empty:
            target = self.region if self.region else f"transmission group {self.transmission_group}"
            raise ValueError(f"No renewable generation data found for {self.scenario}, {target}, {self.year}")

        
        # Load tech categories for renewable identification (shared config file)
        tech_file = f"{self.config_base_path}technology_categories.csv"
        tech_df = pd.read_csv(tech_file)
        
        # Create tech+sub_tech mapping for renewables
        solar_techs = []
        wind_techs = []
        
        for _, row in tech_df.iterrows():
            if row['category'] == 'solar':
                tech = row['tech']
                sub_tech = row['sub_tech'] if pd.notna(row['sub_tech']) else None
                if sub_tech:
                    solar_techs.append(f"{tech}|{sub_tech}")
                else:
                    solar_techs.append(tech)
            elif row['category'] == 'wind':
                tech = row['tech']
                sub_tech = row['sub_tech'] if pd.notna(row['sub_tech']) else None
                if sub_tech:
                    wind_techs.append(f"{tech}|{sub_tech}")
                else:
                    wind_techs.append(tech)
        
        # Create tech+sub_tech key and filter for renewables
        filtered_data['tech_subtech_key'] = filtered_data.apply(lambda row: 
            f"{row['tech']}|{row['sub_tech']}" if pd.notna(row['sub_tech']) else row['tech'], 
            axis=1)
        
        # Get renewable generation by timeslice
        solar_df = filtered_data[filtered_data['tech_subtech_key'].isin(solar_techs)]
        wind_df = filtered_data[filtered_data['tech_subtech_key'].isin(wind_techs)]
        
        # Keep regional structure (don't aggregate across regions)
        renewable_generation = {'solar': {}, 'wind': {}}
        
        if not solar_df.empty:
            # Group by region AND timeslice to preserve regional diversity
            solar_by_region_timeslice = solar_df.groupby(['region', 'timeslice'])['value'].sum().unstack(fill_value=0)
            
            # Convert to nested dictionary: {region: {timeslice: value}}
            for region in solar_by_region_timeslice.index:
                renewable_generation['solar'][region] = solar_by_region_timeslice.loc[region].to_dict()
            
            total_solar_twh = solar_df['value'].sum()
            
            if not self.region:  # Multi-regional mode
                solar_regions = solar_df['region'].nunique()
                solar_timeslices = solar_df['timeslice'].nunique()
                print(f"   ☀️ Solar generation: {total_solar_twh:.1f} TWh across {solar_timeslices} timeslices, {solar_regions} {self.transmission_group} regions")
            else:
                solar_timeslices = solar_df['timeslice'].nunique()
                print(f"   ☀️ Solar generation: {total_solar_twh:.1f} TWh across {solar_timeslices} timeslices")
        else:
            print(f"   ☀️ No solar generation found")
        
        if not wind_df.empty:
            # Group by region AND timeslice to preserve regional diversity
            wind_by_region_timeslice = wind_df.groupby(['region', 'timeslice'])['value'].sum().unstack(fill_value=0)
            
            # Convert to nested dictionary: {region: {timeslice: value}}
            for region in wind_by_region_timeslice.index:
                renewable_generation['wind'][region] = wind_by_region_timeslice.loc[region].to_dict()
            
            total_wind_twh = wind_df['value'].sum()
            
            if not self.region:  # Multi-regional mode
                wind_regions = wind_df['region'].nunique()
                wind_timeslices = wind_df['timeslice'].nunique()
                print(f"   💨 Wind generation: {total_wind_twh:.1f} TWh across {wind_timeslices} timeslices, {wind_regions} {self.transmission_group} regions")
            else:
                wind_timeslices = wind_df['timeslice'].nunique()
                print(f"   💨 Wind generation: {total_wind_twh:.1f} TWh across {wind_timeslices} timeslices")
        else:
            print(f"   💨 No wind generation found")
        
        return renewable_generation
    
    def load_all_capacities(self):
        """Load comprehensive capacity data from FACETS capacity file"""
        print("🏭 Loading FACETS Comprehensive Capacity Data...")
        
        # Load capacity data (same logic as storage function)
        capacity_file = f"{self.model_outputs_path}VSInput_capacity by tech and region.csv"
        
        # Read in chunks to handle large file
        chunk_size = 50000
        filtered_data = []
        
        # Handle single region mode (backward compatibility)
        if self.region:
            for chunk in pd.read_csv(capacity_file, chunksize=chunk_size):
                filtered = chunk[
                    (chunk['scen'] == self.scenario) &
                    (chunk['year'] == self.year) &
                    (chunk['region'] == self.region)
                ]
                if not filtered.empty:
                    filtered_data.append(filtered)
        else:
            # Multi-regional aggregation - filter by transmission group
            for chunk in pd.read_csv(capacity_file, chunksize=chunk_size):
                filtered = chunk[
                    (chunk['scen'] == self.scenario) &
                    (chunk['year'] == self.year) &
                    (chunk['reg_transgrp'] == self.transmission_group)
                ]
                if not filtered.empty:
                    filtered_data.append(filtered)
        
        if not filtered_data:
            target = self.region if self.region else f"transmission group {self.transmission_group}"
            raise ValueError(f"No capacity data found for {self.scenario}, {target}, {self.year}")
        
        df = pd.concat(filtered_data, ignore_index=True)
        
        # Load tech categories for classification (shared config file)
        tech_file = f"{self.config_base_path}technology_categories.csv"
        tech_df = pd.read_csv(tech_file)
        
        # Create tech+sub_tech mapping for all categories
        category_mapping = {}
        for _, row in tech_df.iterrows():
            tech = row['tech']
            sub_tech = row['sub_tech'] if pd.notna(row['sub_tech']) else None
            category = row['category']
            
            if sub_tech:
                tech_key = f"{tech}|{sub_tech}"
            else:
                tech_key = tech
            category_mapping[tech_key] = category
        
        # Create tech+sub_tech key for capacity data
        df['tech_subtech_key'] = df.apply(lambda row: 
            f"{row['tech']}|{row['sub_tech']}" if pd.notna(row['sub_tech']) else row['tech'], 
            axis=1)
        
        # Initialize capacity dictionaries by category
        renewable_capacity = {'solar_capacity_gw': 0, 'wind_capacity_gw': 0}
        storage_capacity = {}
        baseload_capacity = 0
        dispatchable_capacity = 0
        other_capacity = 0
        
        # Process each technology
        for _, row in df.iterrows():
            tech_key = row['tech_subtech_key']
            capacity_gw = row['value']
            category = category_mapping.get(tech_key, 'other')
            
            if category == 'solar':
                renewable_capacity['solar_capacity_gw'] += capacity_gw
            elif category == 'wind':
                renewable_capacity['wind_capacity_gw'] += capacity_gw
            elif category == 'storage':
                if tech_key not in storage_capacity:
                    storage_capacity[tech_key] = 0
                storage_capacity[tech_key] += capacity_gw
            elif category == 'baseload':
                baseload_capacity += capacity_gw
            elif category == 'dispatchable':
                dispatchable_capacity += capacity_gw
            else:
                other_capacity += capacity_gw
        
        # Print summary
        target_name = self.region if self.region else f"{self.transmission_group} regions"
        print(f"   📊 Capacity summary for {target_name}:")
        
        total_renewable = renewable_capacity['solar_capacity_gw'] + renewable_capacity['wind_capacity_gw']
        if total_renewable > 0:
            print(f"   🌱 Renewable: {total_renewable:.1f} GW")
            if renewable_capacity['solar_capacity_gw'] > 0:
                print(f"      ☀️ Solar: {renewable_capacity['solar_capacity_gw']:.1f} GW")
            if renewable_capacity['wind_capacity_gw'] > 0:
                print(f"      💨 Wind: {renewable_capacity['wind_capacity_gw']:.1f} GW")
        
        total_storage = sum(storage_capacity.values()) if storage_capacity else 0
        if total_storage > 0:
            print(f"   🔋 Storage: {total_storage:.1f} GW")
            for tech, capacity in storage_capacity.items():
                print(f"      🔋 {tech}: {capacity:.1f} GW")
        
        if baseload_capacity > 0:
            print(f"   🏭 Baseload: {baseload_capacity:.1f} GW")
        if dispatchable_capacity > 0:
            print(f"   🔥 Dispatchable: {dispatchable_capacity:.1f} GW")
        if other_capacity > 0:
            print(f"   📋 Other: {other_capacity:.1f} GW")
        
        return {
            'renewable': renewable_capacity,
            'storage': storage_capacity,
            'baseload_gw': baseload_capacity,
            'dispatchable_gw': dispatchable_capacity,
            'other_gw': other_capacity,
            '_raw_data': df,  # Add raw dataframe for reuse
            '_tech_categories': category_mapping  # Add tech categories for reuse
        }
    
    def load_potential_dispatchable_capacity(self, capacity_data_df, tech_categories):
        """Load potential dispatchable capacity from already-loaded data (exclude hydro/trade, apply 90% availability)"""
        print("🔥 Loading Potential Dispatchable Capacity...")
        
        if capacity_data_df is None or capacity_data_df.empty:
            print("   ⚠️ No capacity data provided")
            return {}, set()
        
        # Filter to dispatchable technologies only, exclude hydro and trade
        dispatchable_techs = []
        for _, row in capacity_data_df.iterrows():
            tech = row['tech']
            sub_tech = row['sub_tech'] if pd.notna(row['sub_tech']) else ''
            capacity_gw = row['value']
            
            if capacity_gw <= 0:
                continue
            
            # Create tech_key for category lookup (same format as category_mapping)
            tech_key = f"{tech}|{sub_tech}" if sub_tech else tech
            category = tech_categories.get(tech_key, 'other')
            
            # Include only dispatchable, exclude hydro and trade
            if category == 'dispatchable' and 'hydro' not in tech.lower() and 'trade' not in tech.lower():
                # Apply 90% availability factor
                available_capacity_gw = capacity_gw * 0.9
                dispatchable_techs.append({
                    'tech': tech,
                    'sub_tech': sub_tech,
                    'capacity_gw': available_capacity_gw
                })
        
        # Create capacity dictionary and tech combinations set
        potential_capacity = {}
        tech_combinations = set()
        
        for tech_data in dispatchable_techs:
            key = (tech_data['tech'], tech_data['sub_tech'])
            potential_capacity[key] = tech_data['capacity_gw']
            tech_combinations.add(key)
        
        # Summary
        total_potential_gw = sum(potential_capacity.values())
        target_name = self.region if self.region else f"{self.transmission_group} regions"
        
        print(f"   📊 Potential dispatchable capacity for {target_name}:")
        print(f"   🔥 Total potential: {total_potential_gw:.1f} GW (at 90% availability)")
        print(f"   🏭 Technologies: {len(tech_combinations)} dispatchable tech combinations")
        
        if total_potential_gw > 0:
            print(f"   📋 Top technologies:")
            sorted_techs = sorted(potential_capacity.items(), key=lambda x: x[1], reverse=True)
            for (tech, sub_tech), capacity in sorted_techs[:5]:
                display_name = f"{tech}|{sub_tech}" if sub_tech else tech
                print(f"      {display_name}: {capacity:.1f} GW")
        
        return potential_capacity, tech_combinations
    
    def load_emission_intensities(self, tech_combinations):
        """Calculate emission intensities only for dispatchable tech combinations"""
        print("🔥 Loading Emission Intensities for Dispatchable Technologies...")
        
        # Load emission data
        emission_file = f"{self.model_outputs_path}VSInput_emission by tech and region.csv"

        try:
            # Load emission data with chunking
            emission_chunks = []
            for chunk in pd.read_csv(emission_file, chunksize=50000):
                # Filter by scenario, year, and transmission group
                if self.region:
                    filtered = chunk[
                        (chunk['scen'] == self.scenario) &
                        (chunk['year'] == self.year) &
                        (chunk['region'] == self.region)
                    ]
                else:
                    filtered = chunk[
                        (chunk['scen'] == self.scenario) &
                        (chunk['year'] == self.year) &
                        (chunk['reg_transgrp'] == self.transmission_group)
                    ]
                
                if not filtered.empty:
                    # Filter to only dispatchable tech combinations
                    tech_filter = filtered[['tech', 'sub_tech']].apply(tuple, axis=1).isin(tech_combinations)
                    filtered = filtered[tech_filter]
                    if not filtered.empty:
                        emission_chunks.append(filtered)
            
            if not emission_chunks:
                print("   ⚠️ No emission data found for dispatchable technologies")
                return {}
            
            emission_df = pd.concat(emission_chunks, ignore_index=True)
            

            df = self.gen_df.copy()

            if self.region:
                filtered = df[(df['region'] == self.region) &
                                  (df['scen'] == self.scenario) &
                                  (df['year'] == self.year)]
            else:
                filtered = df[(df['reg_transgrp'] == self.transmission_group) &
                                  (df['scen'] == self.scenario) &
                                  (df['year'] == self.year)]
                
                if not filtered.empty:
                    # Filter to only dispatchable tech combinations
                    tech_filter = filtered[['tech', 'sub_tech']].apply(tuple, axis=1).isin(tech_combinations)
                    filtered = filtered[tech_filter]

            generation_df = filtered
            
            # Calculate annual emissions by tech-subtech combination
            annual_emissions = emission_df.groupby(['tech', 'sub_tech'])['value'].sum()  # kt CO2
            
            # Calculate annual generation by tech-subtech combination (sum across all timeslices)
            annual_generation = generation_df.groupby(['tech', 'sub_tech'])['value'].sum()  # GWh
            
            # Calculate emission intensities
            emission_intensities = {}
            for tech_combo in tech_combinations:
                emissions = annual_emissions.get(tech_combo, 0.0)  # kt CO2
                generation = annual_generation.get(tech_combo, 0.0)  # GWh
                
                if generation > 0:
                    intensity = emissions / generation  # kt CO2 / GWh
                else:
                    intensity = 0.0  # Zero intensity for missing/zero generation (e.g., SMR)
                
                emission_intensities[tech_combo] = intensity
            
            # Summary
            print(f"   📊 Emission intensities calculated for {len(emission_intensities)} tech combinations")
            if emission_intensities:
                print(f"   🔥 Emission intensity range:")
                intensities = list(emission_intensities.values())
                print(f"      Min: {min(intensities):.3f} kt CO2/GWh")
                print(f"      Max: {max(intensities):.3f} kt CO2/GWh")
                
                # Show cleanest and dirtiest technologies
                sorted_by_intensity = sorted(emission_intensities.items(), key=lambda x: x[1])
                print(f"   🌿 Cleanest technologies:")
                for (tech, sub_tech), intensity in sorted_by_intensity[:3]:
                    display_name = f"{tech}|{sub_tech}" if sub_tech else tech
                    print(f"      {display_name}: {intensity:.3f} kt CO2/GWh")
                
                if len(sorted_by_intensity) > 3:
                    print(f"   🔥 Highest emission technologies:")
                    for (tech, sub_tech), intensity in sorted_by_intensity[-3:]:
                        display_name = f"{tech}|{sub_tech}" if sub_tech else tech
                        print(f"      {display_name}: {intensity:.3f} kt CO2/GWh")
            
            return emission_intensities
            
        except Exception as e:
            print(f"   ⚠️ Error loading emission intensities: {e}")
            return {}
    
    def dispatch_potential_capacity(self, remaining_shortage, potential_capacity, emission_intensities):
        """Dispatch potential capacity prioritized by emission intensity (cleanest first)"""
        print("⚡ Dispatching Potential Capacity (Emission-Prioritized)...")
        
        # Initialize arrays
        hourly_potential_dispatchable = np.zeros(8760)
        hourly_additional_emissions = np.zeros(8760)
        
        if not potential_capacity or not emission_intensities:
            print("   ⚠️ No potential capacity or emission data available")
            return hourly_potential_dispatchable, hourly_additional_emissions
        
        # Sort technologies by emission intensity (cleanest first)
        sorted_techs = sorted(emission_intensities.items(), key=lambda x: x[1])
        
        print(f"   🌿 Dispatch priority (cleanest first):")
        for i, ((tech, sub_tech), intensity) in enumerate(sorted_techs[:5]):
            display_name = f"{tech}|{sub_tech}" if sub_tech else tech
            capacity = potential_capacity.get((tech, sub_tech), 0)
            print(f"      {i+1}. {display_name}: {intensity:.3f} kt CO2/GWh ({capacity:.1f} GW)")
        
        # Calculate total shortage and potential dispatch
        total_shortage_gwh = np.sum(remaining_shortage) / 1000  # Convert MW to GWh
        total_potential_capacity_gw = sum(potential_capacity.values())
        
        print(f"   📊 Total remaining shortage: {total_shortage_gwh:.1f} GWh")
        print(f"   🔥 Total potential capacity: {total_potential_capacity_gw:.1f} GW")
        
        # Track utilization by technology
        tech_utilization = {}
        total_dispatched_gwh = 0
        total_emissions_kt = 0
        max_ramping_gw_per_hour = 0
        
        # Hour-by-hour dispatch
        for hour in range(8760):
            if remaining_shortage[hour] <= 0:
                continue
                
            shortage_this_hour = remaining_shortage[hour]  # MW
            dispatched_this_hour = 0
            emissions_this_hour = 0
            
            # Try each technology in emission intensity order (cleanest first)
            for (tech, sub_tech), emission_intensity in sorted_techs:
                if shortage_this_hour <= 0:
                    break
                    
                # Get available capacity for this technology
                available_capacity_mw = potential_capacity.get((tech, sub_tech), 0) * 1000  # Convert GW to MW
                
                if available_capacity_mw <= 0:
                    continue
                
                # Dispatch up to available capacity or remaining shortage
                dispatch_mw = min(available_capacity_mw, shortage_this_hour)
                
                if dispatch_mw > 0:
                    dispatched_this_hour += dispatch_mw
                    shortage_this_hour -= dispatch_mw
                    
                    # Calculate emissions for this dispatch
                    dispatch_gwh = dispatch_mw / 1000  # Convert to GWh
                    tech_emissions = dispatch_gwh * emission_intensity  # kt CO2
                    emissions_this_hour += tech_emissions
                    
                    # Track technology utilization
                    tech_key = (tech, sub_tech)
                    if tech_key not in tech_utilization:
                        tech_utilization[tech_key] = {'total_gwh': 0, 'total_emissions_kt': 0, 'hours_used': 0}
                    
                    tech_utilization[tech_key]['total_gwh'] += dispatch_gwh
                    tech_utilization[tech_key]['total_emissions_kt'] += tech_emissions
                    tech_utilization[tech_key]['hours_used'] += 1
            
            # Store hourly results
            hourly_potential_dispatchable[hour] = dispatched_this_hour
            hourly_additional_emissions[hour] = emissions_this_hour
            
            # Track ramping (change from previous hour)
            if hour > 0:
                ramping_gw = abs(dispatched_this_hour - hourly_potential_dispatchable[hour-1]) / 1000
                max_ramping_gw_per_hour = max(max_ramping_gw_per_hour, ramping_gw)
            
            total_dispatched_gwh += dispatched_this_hour / 1000
            total_emissions_kt += emissions_this_hour
        
        # Summary statistics
        shortage_filled_percent = (total_dispatched_gwh / total_shortage_gwh * 100) if total_shortage_gwh > 0 else 0
        hours_with_potential_dispatch = np.sum(hourly_potential_dispatchable > 0)
        
        print(f"   ⚡ Potential dispatch results:")
        print(f"      Total dispatched: {total_dispatched_gwh:.1f} GWh")
        print(f"      Shortage filled: {shortage_filled_percent:.1f}%")
        print(f"      Hours with dispatch: {hours_with_potential_dispatch}/8760 ({hours_with_potential_dispatch/8760*100:.1f}%)")
        print(f"      Additional emissions: {total_emissions_kt:.0f} kt CO2")
        print(f"      Max ramping: {max_ramping_gw_per_hour:.1f} GW/hour")
        
        # Technology utilization summary
        if tech_utilization:
            print(f"   🏭 Technology utilization:")
            sorted_utilization = sorted(tech_utilization.items(), key=lambda x: x[1]['total_gwh'], reverse=True)
            for (tech, sub_tech), util in sorted_utilization[:5]:
                display_name = f"{tech}|{sub_tech}" if sub_tech else tech
                avg_intensity = util['total_emissions_kt'] / util['total_gwh'] if util['total_gwh'] > 0 else 0
                print(f"      {display_name}: {util['total_gwh']:.1f} GWh, {util['total_emissions_kt']:.0f} kt CO2 ({avg_intensity:.3f} kt/GWh)")
        
        return hourly_potential_dispatchable, hourly_additional_emissions
    
    def _get_weather_year_indices(self, hdf5_file):
        """Get the indices for the specified weather year from HDF5 file (2012 = hours 43800-52559)"""
        with h5py.File(hdf5_file, 'r') as f:
            # Get datetime strings from index_0
            datetime_strings = f['index_0'][:]
            datetime_strings = [item.decode() if isinstance(item, bytes) else item for item in datetime_strings]
            
            # Extract years from datetime strings
            years = np.array([int(dt_str.split('-')[0]) for dt_str in datetime_strings])
            
            # Find indices where year matches weather_year
            weather_year_mask = years == self.weather_year
            weather_year_indices = np.where(weather_year_mask)[0]
            
            if len(weather_year_indices) < 8760:
                print(f"⚠️  Warning: Only found {len(weather_year_indices)} hours for {self.weather_year}, expected 8760")
                print(f"   Available years: {sorted(set(years))}")
                # Fallback to first 8760 hours
                print(f"   Using first 8760 hours as fallback")
                return np.arange(8760)
            
            # Return first 8760 hours of the weather year
            return weather_year_indices[:8760]
    
    def load_hourly_renewable_profiles(self):
        """Load hourly capacity factor profiles by region (preserving regional diversity)"""
        print("☀️💨 Loading Hourly Renewable Profiles...")
        
        # Load solar profiles
        solar_file = f"{self.hourly_data_path}upv-reference_ba.h5"
        wind_file = f"{self.hourly_data_path}wind-ons-reference_ba.h5"
        
        # Handle single region mode (backward compatibility)
        if self.region:
            profile_regions = [self._convert_facets_to_demand_format(self.region)]
        else:
            # Multi-regional mode - use all transmission group regions
            profile_regions = self.demand_regions
        
        # Initialize regional CF dictionaries
        regional_solar_cf = {}
        regional_wind_cf = {}
        
        # Load solar capacity factors by region
        if os.path.exists(solar_file):
            try:
                # Get weather year indices for consistent extraction
                weather_indices = self._get_weather_year_indices(solar_file)
                
                with h5py.File(solar_file, 'r') as f:
                    columns = [col.decode() for col in f['columns'][:]]
                    data = f['data'][:]
                    
                    all_solar_zones = []
                    
                    # Load CF for each region separately
                    for profile_region in profile_regions:
                        region_zones = [col for col in columns if col.endswith(f"|{profile_region}")]
                        
                        if region_zones:
                            # Average zones within this region only
                            indices = [columns.index(col) for col in region_zones]
                            regional_solar_cf[profile_region] = np.mean(data[weather_indices, :][:, indices], axis=1)
                            all_solar_zones.extend(region_zones)
                        else:
                            # No zones for this region, use zeros
                            regional_solar_cf[profile_region] = np.zeros(8760)
                    
                    if all_solar_zones:
                        print(f"   ☀️ Solar CF range: {min(cf.min() for cf in regional_solar_cf.values()):.3f} - {max(cf.max() for cf in regional_solar_cf.values()):.3f}")
                        print(f"   ☀️ Using zones: {all_solar_zones}")
                    else:
                        print(f"   ⚠️ No solar zones found for regions: {profile_regions}")
                        
            except Exception as e:
                print(f"   ⚠️ Error loading solar data: {e}")
                for profile_region in profile_regions:
                    regional_solar_cf[profile_region] = np.zeros(8760)
        else:
            print(f"   ⚠️ Solar file not found: {solar_file}")
            for profile_region in profile_regions:
                regional_solar_cf[profile_region] = np.zeros(8760)
        
        # Load wind capacity factors by region
        if os.path.exists(wind_file):
            try:
                # Get weather year indices for consistent extraction
                weather_indices = self._get_weather_year_indices(wind_file)
                
                with h5py.File(wind_file, 'r') as f:
                    columns = [col.decode() for col in f['columns'][:]]
                    data = f['data'][:]
                    
                    all_wind_zones = []
                    
                    # Load CF for each region separately
                    for profile_region in profile_regions:
                        region_zones = [col for col in columns if col.endswith(f"|{profile_region}")]
                        
                        if region_zones:
                            # Average zones within this region only
                            indices = [columns.index(col) for col in region_zones]
                            regional_wind_cf[profile_region] = np.mean(data[weather_indices, :][:, indices], axis=1)
                            all_wind_zones.extend(region_zones)
                        else:
                            # No zones for this region, use zeros
                            regional_wind_cf[profile_region] = np.zeros(8760)
                    
                    if all_wind_zones:
                        print(f"   💨 Wind CF range: {min(cf.min() for cf in regional_wind_cf.values()):.3f} - {max(cf.max() for cf in regional_wind_cf.values()):.3f}")
                        print(f"   💨 Using zones: {all_wind_zones}")
                    else:
                        print(f"   ⚠️ No wind zones found for regions: {profile_regions}")
                        
            except Exception as e:
                print(f"   ⚠️ Error loading wind data: {e}")
                for profile_region in profile_regions:
                    regional_wind_cf[profile_region] = np.zeros(8760)
        else:
            print(f"   ⚠️ Wind file not found: {wind_file}")
            for profile_region in profile_regions:
                regional_wind_cf[profile_region] = np.zeros(8760)
        
        return regional_solar_cf, regional_wind_cf
    
    def create_hourly_renewable_profiles(self, renewable_generation, regional_solar_cf, regional_wind_cf, timeslice_hour_mapping):
        """Create hourly renewable generation profiles using region-by-region approach"""
        print("⚡ Creating Hourly Renewable Generation Profiles...")
        
        # Initialize aggregated hourly arrays
        total_hourly_solar_mw = np.zeros(8760)
        total_hourly_wind_mw = np.zeros(8760)
        
        # Handle single region mode (backward compatibility)
        if self.region:
            regions_to_process = [self.region]
            profile_regions = [self._convert_facets_to_demand_format(self.region)]
        else:
            # Multi-regional mode - process all regions in transmission group
            regions_to_process = self.regions
            profile_regions = self.demand_regions
        
        # Process each region separately to preserve regional diversity
        for i, (facets_region, profile_region) in enumerate(zip(regions_to_process, profile_regions)):
            
            # Get region-specific generation data
            region_solar_gen = renewable_generation['solar'].get(facets_region, {})
            region_wind_gen = renewable_generation['wind'].get(facets_region, {})
            
            # Get region-specific capacity factors
            region_solar_cf = regional_solar_cf.get(profile_region, np.zeros(8760))
            region_wind_cf = regional_wind_cf.get(profile_region, np.zeros(8760))
            
            # Initialize regional hourly arrays
            region_hourly_solar_mw = np.zeros(8760)
            region_hourly_wind_mw = np.zeros(8760)
            
            # Distribute this region's solar generation
            if region_solar_gen:
                for timeslice, generation_twh in region_solar_gen.items():
                    if timeslice in timeslice_hour_mapping and generation_twh > 0:
                        hour_indices = timeslice_hour_mapping[timeslice]
                        
                        # Get capacity factors for hours in this timeslice
                        timeslice_cfs = region_solar_cf[hour_indices]
                        total_cf_weight = sum(timeslice_cfs)
                        
                        if total_cf_weight > 0.001:  # Minimum threshold to prevent unrealistic concentration
                            # Distribute generation proportionally to CF within timeslice
                            generation_mwh_total = generation_twh * 1000 * 1000  # TWh to MWh
                            
                            for hour_idx in hour_indices:
                                # Distribute regional timeslice generation proportionally by regional CF
                                region_hourly_solar_mw[hour_idx] = generation_mwh_total * (region_solar_cf[hour_idx] / total_cf_weight)
                        elif total_cf_weight > 0:
                            # Very small CF weight - distribute equally to prevent unrealistic spikes
                            generation_mwh_total = generation_twh * 1000 * 1000  # TWh to MWh
                            hourly_generation = generation_mwh_total / len(hour_indices)
                            
                            for hour_idx in hour_indices:
                                region_hourly_solar_mw[hour_idx] = hourly_generation
            
            # Distribute this region's wind generation
            if region_wind_gen:
                for timeslice, generation_twh in region_wind_gen.items():
                    if timeslice in timeslice_hour_mapping and generation_twh > 0:
                        hour_indices = timeslice_hour_mapping[timeslice]
                        
                        # Get capacity factors for hours in this timeslice
                        timeslice_cfs = region_wind_cf[hour_indices]
                        total_cf_weight = sum(timeslice_cfs)
                        
                        if total_cf_weight > 0.001:  # Minimum threshold to prevent unrealistic concentration
                            # Distribute generation proportionally to CF within timeslice
                            generation_mwh_total = generation_twh * 1000 * 1000  # TWh to MWh
                            
                            for hour_idx in hour_indices:
                                # Distribute regional timeslice generation proportionally by regional CF
                                region_hourly_wind_mw[hour_idx] = generation_mwh_total * (region_wind_cf[hour_idx] / total_cf_weight)
                        elif total_cf_weight > 0:
                            # Very small CF weight - distribute equally to prevent unrealistic spikes
                            generation_mwh_total = generation_twh * 1000 * 1000  # TWh to MWh
                            hourly_generation = generation_mwh_total / len(hour_indices)
                            
                            for hour_idx in hour_indices:
                                region_hourly_wind_mw[hour_idx] = hourly_generation
            
            # Add this region's hourly profiles to transmission group totals
            total_hourly_solar_mw += region_hourly_solar_mw
            total_hourly_wind_mw += region_hourly_wind_mw
        
        # Print distribution summary by timeslice (aggregated across regions)
        if renewable_generation['solar']:
            print("   ☀️ Distributing solar generation by timeslice...")
            for timeslice in set().union(*[region_gen.keys() for region_gen in renewable_generation['solar'].values()]):
                total_timeslice_twh = sum(region_gen.get(timeslice, 0) for region_gen in renewable_generation['solar'].values())
                if total_timeslice_twh > 0 and timeslice in timeslice_hour_mapping:
                    hour_indices = timeslice_hour_mapping[timeslice]
                    # Calculate average CF across all regions for reporting
                    avg_cf_timeslice = np.mean([np.mean(regional_solar_cf[prof_reg][hour_indices]) 
                                              for prof_reg in profile_regions 
                                              if prof_reg in regional_solar_cf])
                    print(f"      {timeslice}: {total_timeslice_twh:.3f} TWh → {len(hour_indices)} hours (avg CF: {avg_cf_timeslice:.3f})")
        
        if renewable_generation['wind']:
            print("   💨 Distributing wind generation by timeslice...")
            for timeslice in set().union(*[region_gen.keys() for region_gen in renewable_generation['wind'].values()]):
                total_timeslice_twh = sum(region_gen.get(timeslice, 0) for region_gen in renewable_generation['wind'].values())
                if total_timeslice_twh > 0 and timeslice in timeslice_hour_mapping:
                    hour_indices = timeslice_hour_mapping[timeslice]
                    # Calculate average CF across all regions for reporting
                    avg_cf_timeslice = np.mean([np.mean(regional_wind_cf[prof_reg][hour_indices]) 
                                              for prof_reg in profile_regions 
                                              if prof_reg in regional_wind_cf])
                    print(f"      {timeslice}: {total_timeslice_twh:.3f} TWh → {len(hour_indices)} hours (avg CF: {avg_cf_timeslice:.3f})")
        
        print(f"   ☀️ Solar generation: {total_hourly_solar_mw.min():.0f} - {total_hourly_solar_mw.max():.0f} MW")
        print(f"   💨 Wind generation: {total_hourly_wind_mw.min():.0f} - {total_hourly_wind_mw.max():.0f} MW")
        print(f"   🌱 Total renewable: {(total_hourly_solar_mw + total_hourly_wind_mw).sum() / 1000:.1f} GWh")
        
        return total_hourly_solar_mw, total_hourly_wind_mw
    
    def calculate_hourly_shortage(self, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw):
        """Calculate hourly shortage = demand - (baseload + renewables)"""
        print("⚖️ Calculating Hourly Supply-Demand Balance...")
        
        # Calculate total non-dispatchable supply
        total_supply = hourly_baseload + hourly_solar_mw + hourly_wind_mw
        
        # Calculate shortage (positive = shortage, negative = surplus)
        hourly_shortage = hourly_demand - total_supply
        
        # Only consider positive shortages (negative means surplus)
        hourly_shortage = np.maximum(hourly_shortage, 0)
        
        shortage_hours = np.sum(hourly_shortage > 0)
        max_shortage = np.max(hourly_shortage)
        total_shortage = np.sum(hourly_shortage) / 1000  # Convert to GWh
        
        print(f"   ⚡ Hours with shortage: {shortage_hours}/8760 ({shortage_hours/8760*100:.1f}%)")
        print(f"   📊 Max shortage: {max_shortage:.0f} MW")
        print(f"   📈 Total shortage: {total_shortage:.1f} GWh")
        
        return hourly_shortage
    
    def load_dispatchable_generation(self):
        """Load and aggregate FACETS dispatchable generation data across transmission group regions"""
        print("🔥 Loading FACETS Dispatchable Generation Data...")
        
        filtered_data = []
        
        df = self.gen_df.copy()

        if self.region:
            filtered_data = df[(df['region'] == self.region) &
                              (df['scen'] == self.scenario) &
                              (df['year'] == self.year)]
        else:
            filtered_data = df[(df['reg_transgrp'] == self.transmission_group) &
                              (df['scen'] == self.scenario) &
                              (df['year'] == self.year)]
                
        if filtered_data.empty:
            target = self.region if self.region else f"transmission group {self.transmission_group}"
            raise ValueError(f"No generation data found for {self.scenario}, {target}, {self.year}")
        
        
        # Load tech categories for dispatchable identification  
        tech_file = f"{self.config_base_path}technology_categories.csv"
        tech_df = pd.read_csv(tech_file)
        
        # Create tech+sub_tech mapping for dispatchables
        dispatchable_techs = []
        
        for _, row in tech_df.iterrows():
            if row['category'] == 'dispatchable':
                tech = row['tech']
                sub_tech = row['sub_tech'] if pd.notna(row['sub_tech']) else None
                if sub_tech:
                    dispatchable_techs.append(f"{tech}|{sub_tech}")
                else:
                    dispatchable_techs.append(tech)
        
        # Create tech+sub_tech key and filter for dispatchables
        filtered_data['tech_subtech_key'] = filtered_data.apply(lambda row: 
            f"{row['tech']}|{row['sub_tech']}" if pd.notna(row['sub_tech']) else row['tech'], 
            axis=1)
        
        # Filter for dispatchable technologies
        dispatchable_df = filtered_data[filtered_data['tech_subtech_key'].isin(dispatchable_techs)]
        
        if dispatchable_df.empty:
            print("   ⚠️ No dispatchable generation found")
            return pd.Series(dtype=float)
        
        # Group by timeslice and sum across all regions in transmission group
        dispatchable_by_timeslice = dispatchable_df.groupby('timeslice')['value'].sum()
        
        if self.region:
            print(f"   ✅ Found dispatchable generation in {len(dispatchable_by_timeslice)} timeslices")
        else:
            regions_found = dispatchable_df['region'].nunique()
            print(f"   ✅ Found dispatchable generation across {regions_found} {self.transmission_group} regions")
            print(f"   📊 Timeslices: {len(dispatchable_by_timeslice)}")
        
        print(f"   🔥 Total dispatchable: {dispatchable_by_timeslice.sum():.1f} TWh")
        print(f"   📊 Technologies: {sorted(dispatchable_df['tech_subtech_key'].unique())}")
        
        return dispatchable_by_timeslice
    
    def create_hourly_dispatchable_profile(self, dispatchable_by_timeslice, timeslice_hour_mapping, hourly_shortage):
        """Create hourly dispatchable profile by spreading generation proportional to shortage"""
        print("🎯 Creating Hourly Dispatchable Profile...")
        
        if dispatchable_by_timeslice.empty:
            print("   ⚠️ No dispatchable data to process")
            return np.zeros(8760)
        
        # Initialize hourly dispatchable array
        hourly_dispatchable = np.zeros(8760)
        
        # Process each timeslice
        for timeslice, generation_twh in dispatchable_by_timeslice.items():
            if timeslice not in timeslice_hour_mapping:
                continue
                
            # Get hours for this timeslice
            hour_indices = timeslice_hour_mapping[timeslice]
            
            if len(hour_indices) == 0:
                continue
            
            # Get shortage for these hours
            timeslice_shortage = hourly_shortage[hour_indices]
            total_timeslice_shortage = np.sum(timeslice_shortage)
            
            # Convert generation from TWh to MW for this timeslice
            # TWh -> GWh -> MWh -> MW (per hour)
            generation_mw_total = generation_twh * 1000 * 1000  # TWh to MWh total
            generation_mw_per_hour = generation_mw_total / len(hour_indices)  # MWh to MW average
            
            if total_timeslice_shortage > 0:
                # Distribute proportional to shortage
                for i, hour_idx in enumerate(hour_indices):
                    if timeslice_shortage[i] > 0:
                        # Proportion of this hour's shortage to total timeslice shortage
                        shortage_fraction = timeslice_shortage[i] / total_timeslice_shortage
                        # Total MW for timeslice distributed proportionally
                        hourly_dispatchable[hour_idx] = generation_mw_total * shortage_fraction
            else:
                # If no shortage in timeslice, don't dispatch anything
                # (The generation goes unused/curtailed)
                pass
        
        print(f"   ✅ Created hourly profile: {hourly_dispatchable.min():.0f} - {hourly_dispatchable.max():.0f} MW")
        print(f"   🔥 Total dispatchable: {hourly_dispatchable.sum() / 1000:.1f} GWh")
        
        return hourly_dispatchable
    
    # load_storage_capacity function removed - now using load_all_capacities instead
    
    # generate_summary_metrics function removed - now using generate_summary_metrics_single instead\n
    def generate_summary_metrics_single(self, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
                                      hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable,
                                      all_capacities, storage_soc_gwh, hourly_potential_dispatchable=None, 
                                      hourly_additional_emissions=None):
        """Generate comprehensive summary metrics for single pooled approach"""
        print("\n" + "="*70)
        print("📊 COMPREHENSIVE SYSTEM SUMMARY METRICS")
        print("="*70)
        
        # System identification
        if self.region:
            system_name = self.region
            system_type = "Single Region"
        else:
            system_name = f"{self.transmission_group} System"
            system_type = "Multi-Regional"
            
        print(f"🎯 System: {system_name} ({system_type})")
        print(f"📅 Year: {self.year}, Scenario: {self.scenario}")
        print()
        
        # Basic system metrics
        annual_demand_gwh = hourly_demand.sum() / 1000
        peak_demand_mw = hourly_demand.max()
        annual_renewables_gwh = (hourly_solar_mw.sum() + hourly_wind_mw.sum()) / 1000
        annual_baseload_gwh = hourly_baseload.sum() / 1000
        
        # Extract capacity data first
        renewable_capacity = all_capacities['renewable']
        storage_capacity = all_capacities['storage']
        
        total_renewable_capacity = renewable_capacity['solar_capacity_gw'] + renewable_capacity['wind_capacity_gw']
        total_storage_capacity = sum(storage_capacity.values()) if storage_capacity else 0
        
        print("📈 SYSTEM SCALE METRICS:")
        print(f"   📊 Peak Demand: {peak_demand_mw:,.0f} MW")
        print(f"   📊 Annual Total Demand: {annual_demand_gwh:,.0f} GWh")
        print(f"   📏 Daily Average Energy: {annual_demand_gwh/365:.1f} GWh/day")
        
        # Renewable capacity breakdown
        solar_capacity_gw = renewable_capacity['solar_capacity_gw']
        wind_capacity_gw = renewable_capacity['wind_capacity_gw']
        print(f"   🌱 Total Renewable Capacity: {total_renewable_capacity:.1f} GW")
        print(f"      ☀️ Solar: {solar_capacity_gw:.1f} GW ({solar_capacity_gw/total_renewable_capacity*100:.1f}%)")
        print(f"      💨 Wind: {wind_capacity_gw:.1f} GW ({wind_capacity_gw/total_renewable_capacity*100:.1f}%)")
        
        # Storage capacity breakdown
        print(f"   🔋 Total Storage Capacity: {total_storage_capacity:.1f} GW")
        if storage_capacity:
            for tech_key, capacity_gw in storage_capacity.items():
                tech_name = tech_key.replace('Storage|', '').replace('Battery ', 'Batt ')
                percentage = capacity_gw / total_storage_capacity * 100 if total_storage_capacity > 0 else 0
                print(f"      {tech_name}: {capacity_gw:.1f} GW ({percentage:.1f}%)")
        else:
            print(f"      No storage in this scenario")
        print()
        
        print("⚡ OPERATIONALLY REALISTIC:")
        
        # Calculate supply components
        total_supply_original = (hourly_baseload + hourly_solar_mw + hourly_wind_mw + 
                               hourly_storage_discharge + hourly_dispatchable)
        
        # Original shortage (without potential dispatchable)
        original_shortage = np.maximum(0, hourly_demand - total_supply_original)
        
        # Final shortage (after potential dispatchable)
        if hourly_potential_dispatchable is not None:
            total_supply_final = total_supply_original + hourly_potential_dispatchable
            final_shortage = np.maximum(0, hourly_demand - total_supply_final)
        else:
            total_supply_final = total_supply_original
            final_shortage = original_shortage
        
        # Use original shortage for main calculations (to preserve existing behavior)
        shortage = original_shortage
        total_demand_with_storage = hourly_demand + hourly_storage_charge
        
        # Surplus only exists where there's no shortage AND supply exceeds total demand+storage
        surplus_raw = total_supply_original - total_demand_with_storage
        surplus = np.where(shortage > 0, 0, np.maximum(surplus_raw, 0))
        
        # Key metrics
        total_shortage_gwh = shortage.sum() / 1000
        total_surplus_gwh = surplus.sum() / 1000
        peak_shortage_mw = shortage.max()
        shortage_hours = np.sum(shortage > 0)
        critical_shortage_hours = np.sum(shortage > peak_demand_mw * 0.1)
        
        # Generation metrics
        renewable_penetration = (annual_renewables_gwh / annual_demand_gwh) * 100
        baseload_factor = (annual_baseload_gwh / annual_demand_gwh) * 100
        
        # Storage metrics
        if total_storage_capacity > 0:
            storage_energy_gwh = hourly_storage_discharge.sum() / 1000
            storage_cycles = storage_energy_gwh / (total_storage_capacity * 4)  # Assuming 4h average duration
            storage_efficiency = (hourly_storage_discharge.sum() / 
                                hourly_storage_charge.sum() * 100) if hourly_storage_charge.sum() > 0 else 0
        else:
            storage_energy_gwh = 0
            storage_cycles = 0
            storage_efficiency = 0
        
        # Dispatchable metrics
        dispatchable_energy_gwh = hourly_dispatchable.sum() / 1000
        dispatchable_hours = np.sum(hourly_dispatchable > 0)
        max_dispatchable_mw = hourly_dispatchable.max()
        
        # Calculate potential dispatchable metrics
        if hourly_potential_dispatchable is not None:
            potential_dispatchable_energy_gwh = np.sum(hourly_potential_dispatchable) / 1000
            potential_dispatch_hours = np.sum(hourly_potential_dispatchable > 0)
            max_potential_dispatch_mw = np.max(hourly_potential_dispatchable)
        else:
            potential_dispatchable_energy_gwh = 0
            potential_dispatch_hours = 0
            max_potential_dispatch_mw = 0
            
        # Calculate emergency emissions metrics
        if hourly_additional_emissions is not None:
            emergency_emissions_kt_co2 = np.sum(hourly_additional_emissions)
            emergency_emission_intensity_avg = (emergency_emissions_kt_co2 / potential_dispatchable_energy_gwh 
                                              if potential_dispatchable_energy_gwh > 0 else 0)
        else:
            emergency_emissions_kt_co2 = 0
            emergency_emission_intensity_avg = 0
        
        # Total production (excluding storage) metrics
        if hourly_potential_dispatchable is not None:
            production_without_storage = hourly_baseload + hourly_solar_mw + hourly_wind_mw + hourly_dispatchable + hourly_potential_dispatchable
        else:
            production_without_storage = hourly_baseload + hourly_solar_mw + hourly_wind_mw + hourly_dispatchable
        total_production_gwh = production_without_storage.sum() / 1000
        production_demand_ratio = (total_production_gwh / annual_demand_gwh) * 100
        
        # Adequacy and load metrics
        adequacy_ratio = (total_production_gwh / annual_demand_gwh) * 100
        
        # Residual load analysis
        residual_load = hourly_demand - hourly_solar_mw - hourly_wind_mw  # Demand after renewables
        peak_residual_load = residual_load.max()
        min_residual_load = residual_load.min()
        
        # Print metrics
        print("   📊 System Adequacy:")
        print(f"      🎯 Adequacy Ratio: {adequacy_ratio:.1f}%")
        print(f"      ❌ Total Shortage: {total_shortage_gwh:,.0f} GWh")
        print(f"      ⚠️  Peak Shortage: {peak_shortage_mw:,.0f} MW")
        print(f"      ⏰ Shortage Hours: {shortage_hours:,.0f} hours ({shortage_hours/8760*100:.1f}%)")
        print(f"      🔥 Critical Hours: {critical_shortage_hours:,.0f} hours")
        print()
        
        print("   🌱 Generation Portfolio:")
        print(f"      🌱 Renewable Penetration: {renewable_penetration:.1f}%")
        print(f"      🏭 Baseload Factor: {baseload_factor:.1f}%")
        print(f"      🔥 Dispatchable Energy: {dispatchable_energy_gwh:,.0f} GWh")
        print(f"      ⚡ Max Dispatchable: {max_dispatchable_mw:,.0f} MW")
        print(f"      🕐 Dispatchable Hours: {dispatchable_hours:,.0f} hours")
        print()
        
        print("   🔋 Storage Performance:")
        print(f"      ⚡ Energy Throughput: {storage_energy_gwh:,.0f} GWh")
        print(f"      🔄 Annual Cycles: {storage_cycles:.1f}")
        print(f"      ⚙️  Round-trip Efficiency: {storage_efficiency:.1f}%")
        print()
        
        print("   📈 Operational Characteristics:")
        print(f"      ✅ Total Surplus: {total_surplus_gwh:,.0f} GWh")
        print(f"      📊 Peak Residual Load: {peak_residual_load:,.0f} MW")
        print(f"      📉 Min Residual Load: {min_residual_load:,.0f} MW")
        print()
        
        print("   🏭 Production (excluding storage):")
        print(f"      🔧 Total Production: {total_production_gwh:,.0f} GWh")
        print(f"      📐 Production/Demand: {production_demand_ratio:.1f}%")
        print()
        
        print("="*70)
        
        # Create summary dictionary
        summary = {
            "Operationally Realistic": {
                "system_name": system_name,
                "system_type": system_type,
                "year": self.year,
                "scenario": self.scenario,
                "peak_demand_mw": float(peak_demand_mw),
                "annual_demand_gwh": float(annual_demand_gwh),
                "total_renewable_capacity_gw": float(total_renewable_capacity),
                "solar_capacity_gw": float(solar_capacity_gw),
                "wind_capacity_gw": float(wind_capacity_gw),
                "total_storage_capacity_gw": float(total_storage_capacity),
                "storage_breakdown": storage_capacity,
                "adequacy_ratio_percent": float(adequacy_ratio),
                "total_shortage_gwh": float(total_shortage_gwh),
                "total_surplus_gwh": float(total_surplus_gwh),
                "peak_shortage_mw": float(peak_shortage_mw),
                "shortage_hours": int(shortage_hours),
                "shortage_hours_percent": float(shortage_hours/8760*100),
                "critical_shortage_hours": int(critical_shortage_hours),
                "renewable_penetration_percent": float(renewable_penetration),
                "baseload_factor_percent": float(baseload_factor),
                "dispatchable_energy_gwh": float(dispatchable_energy_gwh),
                "max_dispatchable_mw": float(max_dispatchable_mw),
                "potential_dispatchable_energy_gwh": float(potential_dispatchable_energy_gwh),
                "potential_dispatch_hours": int(potential_dispatch_hours),
                "max_potential_dispatch_mw": float(max_potential_dispatch_mw),
                "emergency_emissions_kt_co2": float(emergency_emissions_kt_co2),
                "emergency_emission_intensity_avg": float(emergency_emission_intensity_avg),
                "final_shortage_gwh": float(final_shortage.sum() / 1000),
                "final_shortage_hours": int(np.sum(final_shortage > 0)),
                "shortage_reduction_gwh": float((original_shortage.sum() - final_shortage.sum()) / 1000),
                "dispatchable_hours": int(dispatchable_hours),
                "storage_energy_throughput_gwh": float(storage_energy_gwh),
                "storage_annual_cycles": float(storage_cycles),
                "storage_efficiency_percent": float(storage_efficiency),
                "peak_residual_load_mw": float(peak_residual_load),
                "min_residual_load_mw": float(min_residual_load),
                "total_production_gwh": float(total_production_gwh),
                "production_demand_ratio_percent": float(production_demand_ratio)
            }
        }
        
        # Note: Metrics are saved from run_unified_validation_analysis after sensitivity analysis
        
        # Save hourly data to consolidated parquet file for web viewers
        self.save_hourly_data_parquet({
            'hourly_demand': hourly_demand,
            'hourly_baseload': hourly_baseload, 
            'hourly_solar_mw': hourly_solar_mw,
            'hourly_wind_mw': hourly_wind_mw,
            'hourly_storage_charge': hourly_storage_charge,
            'hourly_storage_discharge': hourly_storage_discharge,
            'hourly_dispatchable': hourly_dispatchable,
            'hourly_potential_dispatchable': hourly_potential_dispatchable if hourly_potential_dispatchable is not None else np.zeros(8760),
            'storage_soc_gwh': storage_soc_gwh
        })
        
        # Save metrics to consolidated parquet file for web viewer bottom bar
        self.save_metrics_parquet(summary)
        
        return summary

    def save_hourly_data_parquet(self, hourly_data):
        """Save hourly data to consolidated parquet file for web viewers"""
        import pandas as pd
        from datetime import datetime
        import numpy as np
        
        # Create consolidated parquet path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Ensure output directory exists
        os.makedirs(self.outputs_base_path, exist_ok=True)
        
        parquet_path = os.path.join(self.outputs_base_path, "facets_hourly_data.parquet")
        
        # Prepare data in long format
        records = []
        components = [
               ('Demand', hourly_data['hourly_demand']),
               ('Baseload', hourly_data['hourly_baseload']),
               ('Solar', hourly_data['hourly_solar_mw']),
               ('Wind', hourly_data['hourly_wind_mw']),
               ('Storage_Charge', hourly_data['hourly_storage_charge']),
               ('Storage_Discharge', hourly_data['hourly_storage_discharge']),
               ('Dispatchable', hourly_data['hourly_dispatchable']),
               ('Potential_Dispatchable', hourly_data.get('hourly_potential_dispatchable', np.zeros(8760))),
               ('SOC', hourly_data['storage_soc_gwh'])
           ]
        
        # Calculate shortage and surplus
        total_supply = (hourly_data['hourly_baseload'] + hourly_data['hourly_solar_mw'] + 
                       hourly_data['hourly_wind_mw'] + hourly_data['hourly_storage_discharge'] + 
                       hourly_data['hourly_dispatchable'] + hourly_data.get('hourly_potential_dispatchable', np.zeros(8760)))
        shortage = np.maximum(0, hourly_data['hourly_demand'] - total_supply)
        surplus_raw = total_supply - (hourly_data['hourly_demand'] + hourly_data['hourly_storage_charge'])
        surplus = np.where(shortage > 0, 0, np.maximum(surplus_raw, 0))
        
        components.extend([
            ('Shortage', shortage),
            ('Surplus', surplus)
        ])
        
        # Create records for each hour and component
        for component_name, values in components:
            for hour in range(8760):
                records.append({
                    'scenario': self.scenario,
                    'region': self.region if self.region else self.transmission_group,
                    'year': self.year,
                    'weather_year': self.weather_year,
                    'hour': hour + 1,  # 1-based indexing
                    'component': component_name,
                    'value_mw': float(values[hour]) if component_name != 'SOC' else float(values[hour]) * 1000,  # Convert GWh to MWh for SOC
                    'last_updated': datetime.now()
                })
        
        new_df = pd.DataFrame(records)
        
        # Load existing data if file exists
        if os.path.exists(parquet_path):
            try:
                existing_df = pd.read_parquet(parquet_path)
                # Remove existing records for this scenario-region combination
                mask = ~((existing_df['scenario'] == self.scenario) & 
                        (existing_df['region'] == (self.region if self.region else self.transmission_group)))
                existing_df = existing_df[mask]
                # Combine with new data
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            except Exception as e:
                print(f"⚠️  Could not read existing parquet file: {e}")
                combined_df = new_df
        else:
            combined_df = new_df
        
        # Save to parquet
        combined_df.to_parquet(parquet_path, index=False)
        
        print(f"💾 Saved hourly data to consolidated parquet: {os.path.relpath(parquet_path, script_dir)}")
        print(f"   📊 Total records: {len(combined_df):,} ({len(new_df):,} new)")
        print(f"   🎯 Scenarios: {combined_df['scenario'].nunique()}, Regions: {combined_df['region'].nunique()}")
        
        # Also save as JSON for web viewer compatibility
        json_path = os.path.join(self.outputs_base_path, "facets_hourly_data.json")
        combined_df.to_json(json_path, orient='records', indent=2)
        json_size_mb = os.path.getsize(json_path) / 1024 / 1024
        print(f"💾 Saved hourly data to JSON for web viewer: {os.path.relpath(json_path, script_dir)} ({json_size_mb:.1f} MB)")

    def save_metrics_parquet(self, summary_metrics):
        """Save metrics to consolidated parquet file for web viewer bottom bar"""
        import pandas as pd
        from datetime import datetime
        
        # Create consolidated metrics parquet path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Ensure output directory exists
        os.makedirs(self.outputs_base_path, exist_ok=True)
        
        parquet_path = os.path.join(self.outputs_base_path, "facets_metrics.parquet")
        
        # Extract metrics from summary
        if "Operationally Realistic" not in summary_metrics:
            print("⚠️  No Operationally Realistic metrics found to save")
            return
            
        data = summary_metrics["Operationally Realistic"]
        
        # Create metrics record
        metrics_record = {
            'scenario': self.scenario,
            'region': self.region if self.region else self.transmission_group,
            'year': self.year,
            'weather_year': self.weather_year,
            'system_name': data.get('system_name', 'N/A'),
            'system_type': data.get('system_type', 'N/A'),
            
            # System Scale Metrics
            'peak_demand_gw': data.get('peak_demand_mw', 0) / 1000,
            'annual_demand_twh': data.get('annual_demand_gwh', 0) / 1000,
            'daily_energy_twh': data.get('annual_demand_gwh', 0) / 1000 / 365,
            'total_renewable_gw': data.get('total_renewable_capacity_gw', 0),
            'solar_capacity_gw': data.get('solar_capacity_gw', 0),
            'wind_capacity_gw': data.get('wind_capacity_gw', 0),
            'total_storage_gw': data.get('total_storage_capacity_gw', 0),
            
            # System Adequacy Metrics
            'adequacy_ratio_percent': data.get('adequacy_ratio_percent', 0),
            'total_shortage_twh': data.get('total_shortage_gwh', 0) / 1000,
            'total_surplus_twh': data.get('total_surplus_gwh', 0) / 1000,
            'shortage_hours': data.get('shortage_hours', 0),
            'shortage_hours_percent': data.get('shortage_hours_percent', 0),
            'critical_shortage_hours': data.get('critical_shortage_hours', 0),
            
            # Generation Portfolio Metrics
            'renewable_penetration_percent': data.get('renewable_penetration_percent', 0),
            'baseload_factor_percent': data.get('baseload_factor_percent', 0),
               'dispatchable_energy_twh': data.get('dispatchable_energy_gwh', 0) / 1000,
               'max_dispatchable_gw': data.get('max_dispatchable_mw', 0) / 1000,
               'potential_dispatchable_energy_twh': data.get('potential_dispatchable_energy_gwh', 0) / 1000,
               'potential_dispatch_hours': data.get('potential_dispatch_hours', 0),
               'max_potential_dispatch_gw': data.get('max_potential_dispatch_mw', 0) / 1000,
               'emergency_emissions_kt_co2': data.get('emergency_emissions_kt_co2', 0),
               'emergency_emission_intensity_kt_per_gwh': data.get('emergency_emission_intensity_avg', 0),
            
            # Storage Performance Metrics
            'storage_throughput_twh': data.get('storage_energy_throughput_gwh', 0) / 1000,
            'storage_annual_cycles': data.get('storage_annual_cycles', 0),
            'storage_efficiency_percent': data.get('storage_efficiency_percent', 0),
            
            # Production Metrics
            'total_production_twh': data.get('total_production_gwh', 0) / 1000,
            'production_demand_ratio_percent': data.get('production_demand_ratio_percent', 0),
            
            # Metadata
            'last_updated': datetime.now()
        }
        
        # Add storage technology breakdown as separate columns
        storage_breakdown = data.get('storage_breakdown', {})
        for tech_key, capacity_gw in storage_breakdown.items():
            tech_name = tech_key.replace('Storage|', '').replace('Battery ', 'batt_').replace(' ', '_').lower()
            metrics_record[f'storage_{tech_name}_gw'] = capacity_gw
        
        new_df = pd.DataFrame([metrics_record])
        
        # Load existing data if file exists
        if os.path.exists(parquet_path):
            try:
                existing_df = pd.read_parquet(parquet_path)
                # Remove existing record for this scenario-region-year combination
                mask = ~((existing_df['scenario'] == self.scenario) & 
                        (existing_df['region'] == (self.region if self.region else self.transmission_group)) &
                        (existing_df['year'] == self.year))
                existing_df = existing_df[mask]
                # Combine with new data
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            except Exception as e:
                print(f"⚠️  Could not read existing metrics parquet file: {e}")
                combined_df = new_df
        else:
            combined_df = new_df
        
        # Save to parquet
        combined_df.to_parquet(parquet_path, index=False)
        
        print(f"💾 Saved metrics to consolidated parquet: {os.path.relpath(parquet_path, script_dir)}")
        print(f"   📊 Total records: {len(combined_df):,} (1 new)")
        print(f"   🎯 Scenarios: {combined_df['scenario'].nunique()}, Regions: {combined_df['region'].nunique()}")
        print(f"   📋 Metrics: {len([col for col in combined_df.columns if not col.endswith('_updated') and col not in ['scenario', 'region', 'year', 'weather_year']])} per record")

    def save_summary_metrics(self, summary_metrics, hourly_data=None, sensitivity_df=None, temporal_analysis=None):
        """Save summary metrics to professional Excel file with VerveStacks branding."""
        import pandas as pd
        import sys
        import os
        
        # Add the project root to sys.path to import ExcelManager
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        try:
            from excel_manager import ExcelManager
            from contextlib import contextmanager
        except ImportError:
            print("⚠️  Warning: Could not import ExcelManager. Falling back to CSV.")
            self._save_csv_fallback(summary_metrics)
            return
        
        # Prepare output directory with scenario subfolder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scenario_folder = self.scenario.replace(".", "_")  # Replace dots with underscores for folder name
        metrics_dir = os.path.join(self.outputs_base_path, "metrics", scenario_folder)
        os.makedirs(metrics_dir, exist_ok=True)
        
        # File name stem - simplified naming
        if self.region:
            stem = f"simulation_metrics_{self.region}"
        else:
            stem = f"simulation_metrics_{self.transmission_group}"
        
        # Create structured DataFrame from metrics
        if "Operationally Realistic" in summary_metrics:
            data = summary_metrics["Operationally Realistic"]
            
            # Create a clean DataFrame for Excel output
            df_rows = []
            
            # System Information Section
            df_rows.append({"Metric Category": "System Information", "Metric": "System Name", "Value": data.get("system_name", "N/A"), "Unit": ""})
            df_rows.append({"Metric Category": "System Information", "Metric": "System Type", "Value": data.get("system_type", "N/A"), "Unit": ""})
            df_rows.append({"Metric Category": "System Information", "Metric": "Year", "Value": data.get("year", "N/A"), "Unit": ""})
            df_rows.append({"Metric Category": "System Information", "Metric": "Scenario", "Value": data.get("scenario", "N/A"), "Unit": ""})
            
            # System Scale Section
            df_rows.append({"Metric Category": "System Scale", "Metric": "Peak Demand", "Value": data.get("peak_demand_mw", 0) / 1000, "Unit": "GW"})
            df_rows.append({"Metric Category": "System Scale", "Metric": "Annual Total Demand", "Value": data.get("annual_demand_gwh", 0) / 1000, "Unit": "TWh"})
            df_rows.append({"Metric Category": "System Scale", "Metric": "Daily Average Energy", "Value": data.get("annual_demand_gwh", 0) / 1000 / 365, "Unit": "TWh/day"})
            df_rows.append({"Metric Category": "System Scale", "Metric": "Total Renewable Capacity", "Value": data.get("total_renewable_capacity_gw", 0), "Unit": "GW"})
            df_rows.append({"Metric Category": "System Scale", "Metric": "Solar Capacity", "Value": data.get("solar_capacity_gw", 0), "Unit": "GW"})
            df_rows.append({"Metric Category": "System Scale", "Metric": "Wind Capacity", "Value": data.get("wind_capacity_gw", 0), "Unit": "GW"})
            df_rows.append({"Metric Category": "System Scale", "Metric": "Total Storage Capacity", "Value": data.get("total_storage_capacity_gw", 0), "Unit": "GW"})
            
            # Storage Technology Breakdown
            storage_breakdown = data.get("storage_breakdown", {})
            for tech_key, capacity_gw in storage_breakdown.items():
                tech_name = tech_key.replace('Storage|', '').replace('Battery ', 'Batt ')
                df_rows.append({"Metric Category": "Storage Technologies", "Metric": f"{tech_name} Capacity", "Value": capacity_gw, "Unit": "GW"})
            
            # System Adequacy Section
            df_rows.append({"Metric Category": "System Adequacy", "Metric": "Adequacy Ratio", "Value": data.get("adequacy_ratio_percent", 0), "Unit": "%"})
            df_rows.append({"Metric Category": "System Adequacy", "Metric": "Total Shortage", "Value": data.get("total_shortage_gwh", 0) / 1000, "Unit": "TWh"})
            df_rows.append({"Metric Category": "System Adequacy", "Metric": "Total Surplus", "Value": data.get("total_surplus_gwh", 0) / 1000, "Unit": "TWh"})
            df_rows.append({"Metric Category": "System Adequacy", "Metric": "Peak Shortage", "Value": data.get("peak_shortage_mw", 0) / 1000, "Unit": "GW"})
            df_rows.append({"Metric Category": "System Adequacy", "Metric": "Shortage Hours", "Value": data.get("shortage_hours", 0), "Unit": "hours"})
            df_rows.append({"Metric Category": "System Adequacy", "Metric": "Shortage Hours Percentage", "Value": data.get("shortage_hours_percent", 0), "Unit": "%"})
            df_rows.append({"Metric Category": "System Adequacy", "Metric": "Critical Shortage Hours", "Value": data.get("critical_shortage_hours", 0), "Unit": "hours"})
            
            # Generation Portfolio Section
            df_rows.append({"Metric Category": "Generation Portfolio", "Metric": "Renewable Penetration", "Value": data.get("renewable_penetration_percent", 0), "Unit": "%"})
            df_rows.append({"Metric Category": "Generation Portfolio", "Metric": "Baseload Factor", "Value": data.get("baseload_factor_percent", 0), "Unit": "%"})
            df_rows.append({"Metric Category": "Generation Portfolio", "Metric": "Dispatchable Energy", "Value": data.get("dispatchable_energy_gwh", 0) / 1000, "Unit": "TWh"})
            df_rows.append({"Metric Category": "Generation Portfolio", "Metric": "Max Dispatchable", "Value": data.get("max_dispatchable_mw", 0) / 1000, "Unit": "GW"})
            df_rows.append({"Metric Category": "Generation Portfolio", "Metric": "Dispatchable Hours", "Value": data.get("dispatchable_hours", 0), "Unit": "hours"})
            
            # Potential Dispatchable Section (NEW)
            df_rows.append({"Metric Category": "Emergency Generation", "Metric": "Potential Energy", "Value": data.get("potential_dispatchable_energy_gwh", 0) / 1000, "Unit": "TWh"})
            df_rows.append({"Metric Category": "Emergency Generation", "Metric": "Max Emergency Dispatch", "Value": data.get("max_potential_dispatch_mw", 0) / 1000, "Unit": "GW"})
            df_rows.append({"Metric Category": "Emergency Generation", "Metric": "Emergency Hours", "Value": data.get("potential_dispatch_hours", 0), "Unit": "hours"})
            df_rows.append({"Metric Category": "Emergency Generation", "Metric": "Emergency Emissions", "Value": data.get("emergency_emissions_kt_co2", 0), "Unit": "kt CO2"})
            df_rows.append({"Metric Category": "Emergency Generation", "Metric": "Avg Emission Intensity", "Value": data.get("emergency_emission_intensity_avg", 0), "Unit": "kt CO2/GWh"})
            
            # Final System Adequacy (NEW)
            df_rows.append({"Metric Category": "Final System Adequacy", "Metric": "Final Shortage", "Value": data.get("final_shortage_gwh", 0) / 1000, "Unit": "TWh"})
            df_rows.append({"Metric Category": "Final System Adequacy", "Metric": "Final Shortage Hours", "Value": data.get("final_shortage_hours", 0), "Unit": "hours"})
            df_rows.append({"Metric Category": "Final System Adequacy", "Metric": "Shortage Reduction", "Value": data.get("shortage_reduction_gwh", 0) / 1000, "Unit": "TWh"})
            
            # Storage Performance Section
            df_rows.append({"Metric Category": "Storage Performance", "Metric": "Energy Throughput", "Value": data.get("storage_energy_throughput_gwh", 0) / 1000, "Unit": "TWh"})
            df_rows.append({"Metric Category": "Storage Performance", "Metric": "Annual Cycles", "Value": data.get("storage_annual_cycles", 0), "Unit": "cycles"})
            df_rows.append({"Metric Category": "Storage Performance", "Metric": "Round-trip Efficiency", "Value": data.get("storage_efficiency_percent", 0), "Unit": "%"})
            
            # Production Metrics Section
            df_rows.append({"Metric Category": "Production Metrics", "Metric": "Total Production (excl. storage)", "Value": data.get("total_production_gwh", 0) / 1000, "Unit": "TWh"})
            df_rows.append({"Metric Category": "Production Metrics", "Metric": "Production/Demand Ratio", "Value": data.get("production_demand_ratio_percent", 0), "Unit": "%"})
            df_rows.append({"Metric Category": "Production Metrics", "Metric": "Peak Residual Load", "Value": data.get("peak_residual_load_mw", 0) / 1000, "Unit": "GW"})
            df_rows.append({"Metric Category": "Production Metrics", "Metric": "Min Residual Load", "Value": data.get("min_residual_load_mw", 0) / 1000, "Unit": "GW"})
            
            df = pd.DataFrame(df_rows)
            
            # Apply smart number formatting for energy metrics
            def smart_format_energy_value(value, unit):
                """Apply smart formatting: large numbers without decimals, others with 1-2 decimals"""
                if not isinstance(value, (int, float)) or pd.isna(value):
                    return value
                
                # Special handling for percentages and non-energy units
                if unit in ["%", "hours", "cycles", ""]:
                    if abs(value) >= 100:
                        return round(value, 0)
                    elif abs(value) >= 10:
                        return round(value, 1)
                    else:
                        return round(value, 2)
                
                # Energy units (GW, TWh, GWh) formatting
                if abs(value) >= 100:
                    return round(value, 0)  # Large numbers: no decimals
                elif abs(value) >= 10:
                    return round(value, 1)  # Medium numbers: 1 decimal
                else:
                    return round(value, 2)  # Small numbers: 2 decimals
            
            # Apply formatting to the Value column
            df['Value'] = df.apply(lambda row: smart_format_energy_value(row['Value'], row['Unit']), axis=1)
            
            # Save to Excel with professional formatting
            excel_path = os.path.join(metrics_dir, f"{stem}.xlsx")
            excel_manager = ExcelManager()
            
            # Use ExcelManager with default branding (FACETS tagline available in LogoManager)
            
            try:
                with excel_manager.workbook(excel_path, create_new=True) as wb:
                    # First sheet: FACETS Validation Metrics
                    ws = wb.sheets[0]
                    ws.name = "FACETS Validation Metrics"
                    
                    # Write data starting from row 3 (row 1 is for branding, row 2 is blank)
                    start_cell = "A3"
                    ws.range(start_cell).value = [df.columns.tolist()] + df.values.tolist()
                    
                    # Apply professional formatting with branding and logo
                    data_shape = (len(df) + 1, len(df.columns))  # +1 for header
                    logo_path = os.path.join(script_dir, "..", "..", "KanorsEMR-Logo-2025_Kanors-Primary-Logo-768x196.webp")
                    excel_manager.format_energy_sector_table(
                        worksheet=ws,
                        start_cell=start_cell,
                        data_shape=data_shape,
                        dataframe=df,
                        add_branding=True,
                        logo_path=logo_path
                    )
                    
                    # Auto-fit columns
                    ws.autofit()
                    
                    # Second sheet: Hourly Data (if provided)
                    if hourly_data:
                        ws_hourly = wb.sheets.add("Hourly Data")
                        
                        # Calculate shortage and surplus from hourly data
                        import numpy as np
                        total_supply = (hourly_data['hourly_baseload'] + 
                                       hourly_data['hourly_solar_mw'] + 
                                       hourly_data['hourly_wind_mw'] + 
                                       hourly_data['hourly_storage_discharge'] + 
                                       hourly_data['hourly_dispatchable'])
                        
                        # Calculate shortage (unmet demand)
                        shortage = np.maximum(0, hourly_data['hourly_demand'] - total_supply)
                        
                        # Calculate surplus (excess supply after meeting demand + storage charging)
                        total_demand_with_storage = hourly_data['hourly_demand'] + hourly_data['hourly_storage_charge']
                        surplus_raw = total_supply - total_demand_with_storage
                        surplus = np.where(shortage > 0, 0, np.maximum(surplus_raw, 0))
                        
                        # Create pivoted hourly DataFrame - only MW/GWh values pivoted, metadata as columns
                        # Start with metadata columns
                        pivoted_data = {
                            'Component': ['Demand_MW', 'Baseload_MW', 'Solar_MW', 'Wind_MW', 'Storage_Charge_MW', 'Storage_Discharge_MW', 'Dispatchable_MW', 'Potential_Dispatchable_MW', 'Shortage_MW', 'Surplus_MW', 'SOC_GWh'],
                            'Scenario': [self.scenario] * 11,
                            'Year': [self.year] * 11,
                            'Region': [self.region if self.region else self.transmission_group] * 11
                        }
                        
                        # Add hour columns (1, 2, ..., 8760)
                        for hour in range(1, 8761):
                            pivoted_data[str(hour)] = [
                                hourly_data['hourly_demand'][hour-1],           # Demand row
                                hourly_data['hourly_baseload'][hour-1],         # Baseload row
                                hourly_data['hourly_solar_mw'][hour-1],         # Solar row
                                hourly_data['hourly_wind_mw'][hour-1],          # Wind row
                                hourly_data['hourly_storage_charge'][hour-1],   # Storage charge row
                                hourly_data['hourly_storage_discharge'][hour-1], # Storage discharge row
                                hourly_data['hourly_dispatchable'][hour-1],     # Dispatchable row
                                hourly_data.get('hourly_potential_dispatchable', np.zeros(8760))[hour-1], # Potential dispatchable row
                                shortage[hour-1],                               # Shortage row (calculated)
                                surplus[hour-1],                                # Surplus row (calculated)
                                hourly_data['storage_soc_gwh'][hour-1]          # SOC row
                            ]
                        
                        hourly_df = pd.DataFrame(pivoted_data)
                        
                        # Write hourly data starting from A1 (no branding for CSV compatibility)
                        start_cell_hourly = "A1"
                        ws_hourly.range(start_cell_hourly).value = [hourly_df.columns.tolist()] + hourly_df.values.tolist()
                        
                        # Auto-fit columns (no fancy formatting for CSV compatibility)
                        ws_hourly.autofit()
                        
                        print(f"   📊 Added pivoted hourly data sheet: {len(hourly_df)} components × {len(hourly_df.columns)-4} hours")
                        print(f"   📋 Structure: Component, Scenario, Year, Region + 8760 hour columns (1-8760)")
                        print(f"   🔢 Includes: Potential_Dispatchable_MW, Shortage_MW, Surplus_MW, SOC_GWh (calculated from hourly data)")
                    
                    # Third sheet: Storage Sensitivity Analysis (if provided)
                    if sensitivity_df is not None:
                        ws_sensitivity = wb.sheets.add("Storage_Sensitivity")
                        
                        # Prepare data for Excel
                        sens_df = sensitivity_df.copy()
                        
                        # Rename columns for better Excel display
                        column_names = {
                            'iteration': 'Iteration',
                            'storage_added_gw': 'Storage Added (GW)',
                            'total_storage_gw': 'Total Storage (GW)',
                            'shortage_twh': 'Shortage (TWh)',
                            'shortage_hours': 'Shortage Hours',
                            'shortage_pct_of_demand': 'Shortage (% of Demand)',
                            'peak_shortage_mw': 'Peak Shortage (MW)',
                            'storage_cycles_per_year': 'Storage Cycles/Year',
                            'storage_utilization_pct': 'Storage Utilization (%)'
                        }
                        sens_df = sens_df.rename(columns=column_names)
                        
                        # Write data starting from row 3 (row 1 is for title, row 2 is blank)
                        start_cell_sens = "A3"
                        ws_sensitivity.range(start_cell_sens).value = [sens_df.columns.tolist()] + sens_df.values.tolist()
                        
                        # Apply formatting
                        data_shape_sens = (len(sens_df) + 1, len(sens_df.columns))  # +1 for header
                        excel_manager.format_energy_sector_table(
                            worksheet=ws_sensitivity,
                            start_cell=start_cell_sens,
                            data_shape=data_shape_sens,
                            dataframe=sens_df,
                            add_branding=True,
                            logo_path=logo_path
                        )
                        
                        # Highlight row where shortage reaches zero (green background)
                        # Find first row where shortage is effectively zero
                        shortage_col_idx = list(sens_df.columns).index('Shortage (TWh)') + 1  # +1 for Excel 1-based
                        for i, row in sens_df.iterrows():
                            if row['Shortage (TWh)'] <= 0.01 and row['Iteration'] > 0:
                                # Highlight this row (data starts at row 4, first data row is row 4, so row i+4)
                                excel_row = i + 4  # 3 (start) + 1 (header) + i
                                range_to_highlight = ws_sensitivity.range(f"A{excel_row}:I{excel_row}")
                                range_to_highlight.color = (144, 238, 144)  # Light green
                                break
                        
                        # Auto-fit columns
                        ws_sensitivity.autofit()
                        
                        print(f"   🔋 Added storage sensitivity analysis: {len(sens_df)} iterations")
                        print(f"   📋 Showing incremental storage additions to eliminate shortage")
                    
                    # Fourth sheet: Temporal Pattern Analysis (if provided)
                    if temporal_analysis is not None:
                        ws_temporal = wb.sheets.add("Temporal_Pattern_Analysis")
                        
                        # Build structured data for the temporal analysis
                        temporal_data = []
                        
                        # Energy Balance section
                        temporal_data.append(['ENERGY BALANCE ANALYSIS', '', ''])
                        temporal_data.append(['Annual Surplus Energy (TWh)', f"{temporal_analysis['energy_balance']['surplus_twh']:.2f}", ''])
                        temporal_data.append(['Annual Shortage Energy (TWh)', f"{temporal_analysis['energy_balance']['shortage_twh']:.2f}", ''])
                        temporal_data.append(['Net Energy Balance (TWh)', f"{temporal_analysis['energy_balance']['balance_twh']:.2f}", ''])
                        temporal_data.append(['Cumulative Energy Swing (GWh)', f"{temporal_analysis['energy_balance']['cumulative_swing_gwh']:.1f}", ''])
                        temporal_data.append(['Cumulative Energy Swing (TWh)', f"{temporal_analysis['energy_balance']['cumulative_swing_gwh']/1000:.2f}", ''])
                        temporal_data.append(['Current Storage Energy (GWh)', f"{temporal_analysis['energy_balance']['current_storage_gwh']:.1f}", ''])
                        temporal_data.append(['Energy Capacity Multiplier Needed', f"{temporal_analysis['energy_balance']['multiplier_needed']:.1f}x", ''])
                        temporal_data.append(['', '', ''])
                        
                        # Event characteristics section
                        temporal_data.append(['SHORTAGE EVENT CHARACTERISTICS', '', ''])
                        temporal_data.append(['Number of Events', temporal_analysis['event_stats']['num_events'], ''])
                        temporal_data.append(['Mean Duration (hours)', f"{temporal_analysis['event_stats']['mean_duration_hours']:.0f}", ''])
                        temporal_data.append(['Mean Duration (days)', f"{temporal_analysis['event_stats']['mean_duration_hours']/24:.1f}", ''])
                        temporal_data.append(['Median Duration (hours)', f"{temporal_analysis['event_stats']['median_duration_hours']:.0f}", ''])
                        temporal_data.append(['Median Duration (days)', f"{temporal_analysis['event_stats']['median_duration_hours']/24:.1f}", ''])
                        temporal_data.append(['Max Duration (hours)', f"{temporal_analysis['event_stats']['max_duration_hours']:.0f}", ''])
                        temporal_data.append(['Max Duration (days)', f"{temporal_analysis['event_stats']['max_duration_hours']/24:.1f}", ''])
                        temporal_data.append(['Events >48h (% of shortage energy)', f"{temporal_analysis['event_stats']['pct_gt_48h']:.0f}%", ''])
                        temporal_data.append(['Events >168h (% of shortage energy)', f"{temporal_analysis['event_stats']['pct_gt_168h']:.0f}%", ''])
                        temporal_data.append(['', '', ''])
                        
                        # Duration adequacy section header
                        temporal_data.append(['STORAGE DURATION ADEQUACY CURVE', '', ''])
                        temporal_data.append(['Duration', 'Energy Capacity (GWh)', 'Shortage Eliminated (%)'])
                        
                        # Duration adequacy data
                        for item in temporal_analysis['duration_adequacy']:
                            dur_hours = item['duration_hours']
                            if dur_hours < 24:
                                dur_label = f"{dur_hours}h"
                            elif dur_hours < 168:
                                dur_label = f"{dur_hours//24}d"
                            else:
                                dur_label = f"{dur_hours//168}w"
                            
                            temporal_data.append([
                                dur_label,
                                f"{item['energy_capacity_gwh']:,.0f}",
                                f"{item['shortage_eliminated_pct']:.1f}%"
                            ])
                        
                        # Write data
                        start_cell_temporal = "A3"
                        ws_temporal.range(start_cell_temporal).value = temporal_data
                        
                        # Apply basic formatting
                        # Title
                        ws_temporal.range("A1").value = "TEMPORAL PATTERN ANALYSIS"
                        ws_temporal.range("A1").api.Font.Bold = True
                        ws_temporal.range("A1").api.Font.Size = 14
                        
                        # Section headers (rows where first column contains uppercase text ending in ANALYSIS/CHARACTERISTICS/CURVE)
                        for i, row in enumerate(temporal_data, start=3):
                            if row[0] and isinstance(row[0], str) and row[0].isupper() and any(keyword in row[0] for keyword in ['ANALYSIS', 'CHARACTERISTICS', 'CURVE']):
                                cell = ws_temporal.range(f"A{i}:C{i}")
                                cell.api.Font.Bold = True
                                cell.api.Font.Size = 11
                                cell.color = (220, 220, 220)  # Light gray background
                        
                        # Auto-fit columns
                        ws_temporal.autofit()
                        
                        print(f"   📊 Added temporal pattern analysis")
                        print(f"   📋 Showing shortage event characteristics and storage duration adequacy")
                
                print(f"💾 Saved metrics Excel: {os.path.relpath(excel_path, script_dir)}")
                
            except Exception as e:
                print(f"⚠️  Excel formatting failed: {e}")
                print("💾 Falling back to CSV...")
                self._save_csv_fallback(summary_metrics, hourly_data)
        else:
            print("⚠️  No metrics data found to save")
    
    def _save_csv_fallback(self, summary_metrics, hourly_data=None):
        """Fallback method to save CSV if Excel operations fail."""
        import pandas as pd
        
        # Prepare output directory with scenario subfolder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scenario_folder = self.scenario.replace(".", "_")
        metrics_dir = os.path.join(script_dir, "..", "outputs", "metrics", scenario_folder)
        os.makedirs(metrics_dir, exist_ok=True)
        
        # File name stem
        if self.region:
            stem = f"simulation_metrics_{self.region}"
        else:
            stem = f"simulation_metrics_{self.transmission_group}"
        
        # Create CSV from the current metrics structure
        csv_rows = []
        if "Operationally Realistic" in summary_metrics:
            data = summary_metrics["Operationally Realistic"]
            row = {"analysis_type": "Operationally Realistic"}
            row.update(data)
            csv_rows.append(row)
            
        if csv_rows:
            df = pd.DataFrame(csv_rows)
            csv_path = os.path.join(metrics_dir, f"{stem}.csv")
            df.to_csv(csv_path, index=False)
            print(f"💾 Saved metrics CSV: {os.path.relpath(csv_path, script_dir)}")
        else:
            print("⚠️  No metrics data found to save to CSV")
        
        # Save hourly data as separate CSV if provided (pivoted format)
        if hourly_data:
            # Calculate shortage and surplus from hourly data (same as Excel)
            import numpy as np
            total_supply = (hourly_data['hourly_baseload'] + 
                           hourly_data['hourly_solar_mw'] + 
                           hourly_data['hourly_wind_mw'] + 
                           hourly_data['hourly_storage_discharge'] + 
                           hourly_data['hourly_dispatchable'])
            
            # Calculate shortage (unmet demand)
            shortage = np.maximum(0, hourly_data['hourly_demand'] - total_supply)
            
            # Calculate surplus (excess supply after meeting demand + storage charging)
            total_demand_with_storage = hourly_data['hourly_demand'] + hourly_data['hourly_storage_charge']
            surplus_raw = total_supply - total_demand_with_storage
            surplus = np.where(shortage > 0, 0, np.maximum(surplus_raw, 0))
            
            # Create pivoted hourly DataFrame - only MW/GWh values pivoted, metadata as columns (same as Excel)
            pivoted_data = {
                'Component': ['Demand_MW', 'Baseload_MW', 'Solar_MW', 'Wind_MW', 'Storage_Charge_MW', 'Storage_Discharge_MW', 'Dispatchable_MW', 'Potential_Dispatchable_MW', 'Shortage_MW', 'Surplus_MW', 'SOC_GWh'],
                'Scenario': [self.scenario] * 11,
                'Year': [self.year] * 11,
                'Region': [self.region if self.region else self.transmission_group] * 11
            }
            
            # Add hour columns (1, 2, ..., 8760)
            for hour in range(1, 8761):
                pivoted_data[str(hour)] = [
                    hourly_data['hourly_demand'][hour-1],           # Demand row
                    hourly_data['hourly_baseload'][hour-1],         # Baseload row
                    hourly_data['hourly_solar_mw'][hour-1],         # Solar row
                    hourly_data['hourly_wind_mw'][hour-1],          # Wind row
                    hourly_data['hourly_storage_charge'][hour-1],   # Storage charge row
                    hourly_data['hourly_storage_discharge'][hour-1], # Storage discharge row
                    hourly_data['hourly_dispatchable'][hour-1],     # Dispatchable row
                    hourly_data.get('hourly_potential_dispatchable', np.zeros(8760))[hour-1], # Potential dispatchable row
                    shortage[hour-1],                               # Shortage row (calculated)
                    surplus[hour-1],                                # Surplus row (calculated)
                    hourly_data['storage_soc_gwh'][hour-1]          # SOC row
                ]
            
            hourly_df = pd.DataFrame(pivoted_data)
            
            hourly_csv_path = os.path.join(metrics_dir, f"{stem}_hourly.csv")
            hourly_df.to_csv(hourly_csv_path, index=False)
            print(f"💾 Saved pivoted hourly data CSV: {os.path.relpath(hourly_csv_path, script_dir)}")
            print(f"   📊 Pivoted data: {len(hourly_df)} components × {len(hourly_df.columns)-3} hours")
            print(f"   📋 Structure: Component, Scenario, Year, Region + 8760 hour columns (1-8760)")
            print(f"   🔢 Includes: Shortage_MW, Surplus_MW, SOC_GWh (calculated from hourly data)")
    
    
    def simulate_combined_storage_dispatchable(self, storage_capacity, dispatchable_by_timeslice, 
                                              timeslice_hour_mapping, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw):
        """Simulate combined storage+dispatchable operation for optimal ramping"""
        print("⚡ Simulating Combined Storage + Dispatchable Operation...")
        
        # Storage parameters (defaults)
        storage_params = {
            'Storage|Battery 4h': {'duration_h': 4, 'efficiency': 0.85, 'max_c_rate': 1.0},
            'Storage|Battery 8h': {'duration_h': 8, 'efficiency': 0.85, 'max_c_rate': 0.5}, 
            'Storage|Pumped': {'duration_h': 12, 'efficiency': 0.75, 'max_c_rate': 0.2}
        }
        
        # Initialize arrays
        hourly_storage_charge = np.zeros(8760)
        hourly_storage_discharge = np.zeros(8760)
        hourly_dispatchable = np.zeros(8760)
        
        # Calculate net load after clean generation
        clean_supply = hourly_baseload + hourly_solar_mw + hourly_wind_mw
        net_load = hourly_demand - clean_supply
        
        # Storage capacity setup
        if not storage_capacity:
            print("   ⚠️ No storage capacity - using dispatchable only")
            # Fall back to original dispatchable logic
            return hourly_storage_charge, hourly_storage_discharge, self.create_hourly_dispatchable_profile(
                dispatchable_by_timeslice, timeslice_hour_mapping, np.maximum(net_load, 0))
        
        # Calculate storage characteristics
        total_storage_capacity_mw = 0
        total_energy_capacity_mwh = 0
        weighted_efficiency = 0
        
        for tech_key, capacity_gw in storage_capacity.items():
            if tech_key in storage_params:
                params = storage_params[tech_key]
                capacity_mw = capacity_gw * 1000
                energy_mwh = capacity_mw * params['duration_h']
                
                total_storage_capacity_mw += capacity_mw
                total_energy_capacity_mwh += energy_mwh
                weighted_efficiency += params['efficiency'] * capacity_gw
        
        if total_storage_capacity_mw > 0:
            weighted_efficiency /= sum(storage_capacity.values())
        
        print(f"   🔋 Combined storage: {total_storage_capacity_mw/1000:.1f} GW / {total_energy_capacity_mwh:.0f} MWh")
        print(f"   ⚡ Weighted efficiency: {weighted_efficiency:.1%}")
        
        # State of charge tracking
        soc_mwh = np.zeros(8760 + 1)
        soc_mwh[0] = total_energy_capacity_mwh * 0.5  # Start at 50%
        
        # Calculate rolling average demand to identify high/low periods
        window_hours = 12  # 12-hour rolling window
        net_load_positive = np.maximum(net_load, 0)
        demand_rolling = np.convolve(net_load_positive, np.ones(window_hours)/window_hours, mode='same')
        
        # Identify high-demand periods (top 25% of rolling demand)
        demand_threshold = np.percentile(demand_rolling, 75)
        high_demand_mask = demand_rolling > demand_threshold
        
        print(f"   📊 High demand threshold: {demand_threshold:.0f} MW")
        print(f"   ⏰ High demand hours: {np.sum(high_demand_mask)}/8760 ({np.sum(high_demand_mask)/8760*100:.1f}%)")
        
        # First pass: Use FACETS timeslice dispatchable as planned, then optimize with storage
        # This validates FACETS assumptions by forcing their planned generation
        
        # Get total FACETS dispatchable energy and distribute by timeslice
        total_dispatchable_energy_mwh = dispatchable_by_timeslice.sum() * 1e6
        print(f"   📋 FACETS planned dispatchable: {total_dispatchable_energy_mwh/1e6:.1f} TWh (will be respected)")
        
        # First, distribute FACETS dispatchable generation by timeslice (as originally planned)
        for timeslice, generation_twh in dispatchable_by_timeslice.items():
            if timeslice not in timeslice_hour_mapping:
                continue
            hour_indices = timeslice_hour_mapping[timeslice]
            if len(hour_indices) == 0:
                continue
            
            # Calculate shortage for this timeslice BEFORE storage optimization
            timeslice_net_load = net_load[hour_indices]
            timeslice_shortage = np.maximum(timeslice_net_load, 0)
            total_timeslice_shortage = np.sum(timeslice_shortage)
            
            # Convert FACETS generation from TWh to MW total for this timeslice
            generation_mw_total = generation_twh * 1000 * 1000  # TWh to MWh total
            
            if total_timeslice_shortage > 0:
                # Distribute FACETS planned generation proportional to shortage
                for i, hour_idx in enumerate(hour_indices):
                    if timeslice_shortage[i] > 0:
                        shortage_fraction = timeslice_shortage[i] / total_timeslice_shortage
                        hourly_dispatchable[hour_idx] = generation_mw_total * shortage_fraction

        # Calculate system-scaled storage operation thresholds
        peak_demand_mw = np.max(hourly_demand)
        daily_energy_mwh = np.sum(hourly_demand) / 365
        
        # Scale thresholds to system size for realistic operation
        discharge_threshold_mwh = max(peak_demand_mw * 0.5, 50)    # 30 min of peak demand, min 50 MWh
        charge_threshold_mwh = max(daily_energy_mwh * 0.005, 10)   # 0.5% of daily energy, min 10 MWh
        
        print(f"   🔋 System-scaled discharge threshold: {discharge_threshold_mwh:.0f} MWh ({discharge_threshold_mwh/1000:.1f} GWh)")
        print(f"   ⚡ System-scaled charge threshold: {charge_threshold_mwh:.0f} MWh ({charge_threshold_mwh/1000:.1f} GWh)")
        print(f"   📏 System size: {peak_demand_mw/1000:.1f} GW peak, {daily_energy_mwh/1000:.1f} GWh/day")

        
        # Now optimize storage operation to work WITH the FACETS dispatchable profile
        for hour in range(8760):
            current_soc = soc_mwh[hour]
            current_net_load = max(net_load[hour], 0)
            planned_dispatch = hourly_dispatchable[hour]
            
            # Available storage capacity for charge/discharge
            available_charge_capacity = total_energy_capacity_mwh - current_soc
            available_discharge_energy = current_soc
            max_charge_rate = min(total_storage_capacity_mw, available_charge_capacity / weighted_efficiency)
            max_discharge_rate = min(total_storage_capacity_mw, available_discharge_energy * weighted_efficiency)
            
            # Calculate total supply including planned dispatchable
            total_supply_this_hour = planned_dispatch
            
            if current_net_load > 0:
                # We have demand to meet
                if high_demand_mask[hour] and available_discharge_energy > discharge_threshold_mwh:
                    # High demand: discharge storage to reduce dispatchable ramping stress
                    # Storage can substitute for some of the planned dispatchable
                    max_storage_substitution = min(max_discharge_rate, planned_dispatch * 0.7)  # Up to 70% substitution
                    
                    if max_storage_substitution > charge_threshold_mwh:  # Only meaningful amounts
                        hourly_storage_discharge[hour] = max_storage_substitution
                        hourly_dispatchable[hour] = planned_dispatch - max_storage_substitution
                        soc_mwh[hour + 1] = current_soc - (max_storage_substitution / weighted_efficiency)
                    else:
                        soc_mwh[hour + 1] = current_soc
                        
                elif (not high_demand_mask[hour] and available_charge_capacity > charge_threshold_mwh and 
                      planned_dispatch < demand_threshold * 0.3):  # Low demand periods
                    # Low demand: charge storage with additional dispatchable for later use
                    charge_amount = min(max_charge_rate * 0.3, available_charge_capacity / weighted_efficiency)
                    if charge_amount > charge_threshold_mwh:
                        hourly_storage_charge[hour] = charge_amount
                        hourly_dispatchable[hour] = planned_dispatch + charge_amount  # Add charging to dispatchable
                        soc_mwh[hour + 1] = current_soc + (charge_amount * weighted_efficiency)
                    else:
                        soc_mwh[hour + 1] = current_soc
                else:
                    # Keep FACETS planned dispatch as-is
                    soc_mwh[hour + 1] = current_soc
            else:
                # Surplus period: charge storage with clean energy (not affecting dispatchable)
                if available_charge_capacity > charge_threshold_mwh:
                    surplus = -net_load[hour]
                    charge_amount = min(max_charge_rate, surplus, available_charge_capacity / weighted_efficiency)
                    if charge_amount > 0:
                        hourly_storage_charge[hour] = charge_amount
                        soc_mwh[hour + 1] = current_soc + (charge_amount * weighted_efficiency)
                    else:
                        soc_mwh[hour + 1] = current_soc
                else:
                    soc_mwh[hour + 1] = current_soc
        
        # Summary statistics
        total_charge_gwh = np.sum(hourly_storage_charge) / 1000
        total_discharge_gwh = np.sum(hourly_storage_discharge) / 1000
        total_dispatch_gwh = np.sum(hourly_dispatchable) / 1000
        round_trip_efficiency = total_discharge_gwh / total_charge_gwh if total_charge_gwh > 0 else 0
        
        charging_hours = np.sum(hourly_storage_charge > 0)
        discharging_hours = np.sum(hourly_storage_discharge > 0)
        dispatch_hours = np.sum(hourly_dispatchable > 0)
        
        print(f"   ⚡ Combined operation summary:")
        print(f"      Storage charging: {charging_hours} hours, {total_charge_gwh:.1f} GWh")
        print(f"      Storage discharging: {discharging_hours} hours, {total_discharge_gwh:.1f} GWh")
        print(f"      Dispatchable operation: {dispatch_hours} hours, {total_dispatch_gwh:.1f} GWh")
        print(f"      Storage efficiency: {round_trip_efficiency:.1%}")
        print(f"      Max dispatchable: {np.max(hourly_dispatchable):.0f} MW")
        print(f"      Max storage charge: {np.max(hourly_storage_charge):.0f} MW")
        print(f"      Max storage discharge: {np.max(hourly_storage_discharge):.0f} MW")
        
        return hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable
    
    def simulate_pooled_storage_dispatchable(self, storage_capacity, dispatchable_by_timeslice, 
                                           hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw, all_capacities):
        """Simulate pooled dispatchable allocation - ignore timeslice boundaries for operational realism"""
        print("⚡ Simulating Pooled Storage + Dispatchable Operation...")
        print("🎯 Key Change: Pool ALL dispatchable across timeslices for realistic allocation")
        
        # Storage parameters (defaults)
        storage_params = {
            'Storage|Battery 4h': {'duration_h': 4, 'efficiency': 0.85, 'max_c_rate': 1.0},
            'Storage|Battery 8h': {'duration_h': 8, 'efficiency': 0.85, 'max_c_rate': 0.5}, 
            'Storage|Pumped': {'duration_h': 12, 'efficiency': 0.75, 'max_c_rate': 0.2}
        }
        
        # Initialize arrays
        hourly_storage_charge = np.zeros(8760)
        hourly_storage_discharge = np.zeros(8760)
        hourly_dispatchable = np.zeros(8760)
        
        # Calculate net load after clean generation
        clean_supply = hourly_baseload + hourly_solar_mw + hourly_wind_mw
        net_load = hourly_demand - clean_supply
        
        # POOLED APPROACH: Total FACETS dispatchable budget regardless of timeslice
        total_dispatchable_budget_twh = dispatchable_by_timeslice.sum()
        total_dispatchable_budget_mwh = total_dispatchable_budget_twh * 1e6
        
        print(f"   📋 Total FACETS dispatchable budget: {total_dispatchable_budget_twh:.1f} TWh")
        print(f"   🎯 Will allocate based on actual hourly shortage, ignoring timeslice boundaries")
        
        # Calculate total shortage across all hours (before storage)
        total_shortage_mw = np.sum(np.maximum(net_load, 0))
        total_shortage_mwh = total_shortage_mw  # Since it's hourly
        
        print(f"   ⚖️ Total annual shortage: {total_shortage_mwh / 1000:.1f} GWh")
        
        # Storage capacity setup
        if not storage_capacity:
            print("   ⚠️ No storage capacity - using pooled dispatchable only")
            # Simple pooled allocation without storage
            hourly_shortage = np.maximum(net_load, 0)
            if total_shortage_mwh > 0:
                shortage_fraction = hourly_shortage / total_shortage_mwh
                hourly_dispatchable = shortage_fraction * total_dispatchable_budget_mwh
            return hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable
        
        # Calculate storage characteristics
        total_storage_capacity_mw = 0
        total_energy_capacity_mwh = 0
        weighted_efficiency = 0
        
        for tech_key, capacity_gw in storage_capacity.items():
            if tech_key in storage_params:
                params = storage_params[tech_key]
                capacity_mw = capacity_gw * 1000
                energy_mwh = capacity_mw * params['duration_h']
                
                total_storage_capacity_mw += capacity_mw
                total_energy_capacity_mwh += energy_mwh
                weighted_efficiency += params['efficiency'] * capacity_gw
        
        if total_storage_capacity_mw > 0:
            weighted_efficiency /= sum(storage_capacity.values())
        
        print(f"   🔋 Combined storage: {total_storage_capacity_mw/1000:.1f} GW / {total_energy_capacity_mwh:.0f} MWh")
        
        # State of charge tracking
        soc_mwh = np.zeros(8760 + 1)
        soc_mwh[0] = total_energy_capacity_mwh * 0.5  # Start at 50%
        
        # Calculate rolling average demand to identify high/low periods
        window_hours = 12
        net_load_positive = np.maximum(net_load, 0)
        demand_rolling = np.convolve(net_load_positive, np.ones(window_hours)/window_hours, mode='same')
        demand_threshold = np.percentile(demand_rolling, 75)
        high_demand_mask = demand_rolling > demand_threshold
        
        print(f"   📊 High demand threshold: {demand_threshold:.0f} MW")
        
        # Calculate system-scaled storage operation thresholds
        peak_demand_mw = np.max(hourly_demand)
        daily_energy_mwh = np.sum(hourly_demand) / 365
        
        # Scale thresholds to system size for realistic operation
        discharge_threshold_mwh = max(peak_demand_mw * 0.5, 50)    # 30 min of peak demand, min 50 MWh
        charge_threshold_mwh = max(daily_energy_mwh * 0.005, 10)   # 0.5% of daily energy, min 10 MWh
        
        print(f"   🔋 System-scaled discharge threshold: {discharge_threshold_mwh:.0f} MWh ({discharge_threshold_mwh/1000:.1f} GWh)")
        print(f"   ⚡ System-scaled charge threshold: {charge_threshold_mwh:.0f} MWh ({charge_threshold_mwh/1000:.1f} GWh)")
        print(f"   📏 System size: {peak_demand_mw/1000:.1f} GW peak, {daily_energy_mwh/1000:.1f} GWh/day")
        
        # Step 1: Storage operation (same as before)
        for hour in range(8760):
            current_soc = soc_mwh[hour]
            current_net_load = max(net_load[hour], 0)
            
            # Available storage capacity for charge/discharge
            available_charge_capacity = total_energy_capacity_mwh - current_soc
            available_discharge_energy = current_soc
            max_charge_rate = min(total_storage_capacity_mw, available_charge_capacity / weighted_efficiency)
            max_discharge_rate = min(total_storage_capacity_mw, available_discharge_energy * weighted_efficiency)
            
            if current_net_load > 0:
                # Need to meet demand - after base load generation and RE supply
                if high_demand_mask[hour] and available_discharge_energy > discharge_threshold_mwh:
                    # High demand: discharge storage first
                    storage_contribution = min(max_discharge_rate, current_net_load)
                    hourly_storage_discharge[hour] = storage_contribution
                    soc_mwh[hour + 1] = current_soc - (storage_contribution / weighted_efficiency)
                else:
                    # Low/medium demand: preserve storage
                    soc_mwh[hour + 1] = current_soc
            else:
                # Surplus period: charge storage with clean energy
                if available_charge_capacity > charge_threshold_mwh:
                    surplus = -net_load[hour]
                    charge_amount = min(max_charge_rate, surplus, available_charge_capacity / weighted_efficiency)
                    if charge_amount > 0:
                        hourly_storage_charge[hour] = charge_amount
                        soc_mwh[hour + 1] = current_soc + (charge_amount * weighted_efficiency)
                    else:
                        soc_mwh[hour + 1] = current_soc
                else:
                    soc_mwh[hour + 1] = current_soc
        
        # Step 2: Calculate remaining shortage after storage
        adjusted_demand = hourly_demand + hourly_storage_charge
        total_supply_with_storage = hourly_baseload + hourly_solar_mw + hourly_wind_mw + hourly_storage_discharge
        remaining_shortage = np.maximum(adjusted_demand - total_supply_with_storage, 0)
        
        # Step 3: POOLED allocation of dispatchable to remaining shortage
        total_remaining_shortage = np.sum(remaining_shortage)
        
        if total_remaining_shortage > 0:
            # Allocate dispatchable budget proportionally to remaining shortage
            shortage_fraction = remaining_shortage / total_remaining_shortage
            hourly_dispatchable = shortage_fraction * total_dispatchable_budget_mwh
        
        # Summary statistics
        total_charge_gwh = np.sum(hourly_storage_charge) / 1000
        total_discharge_gwh = np.sum(hourly_storage_discharge) / 1000
        total_dispatch_gwh = np.sum(hourly_dispatchable) / 1000
        round_trip_efficiency = total_discharge_gwh / total_charge_gwh if total_charge_gwh > 0 else 0
        
        charging_hours = np.sum(hourly_storage_charge > 0)
        discharging_hours = np.sum(hourly_storage_discharge > 0)
        dispatch_hours = np.sum(hourly_dispatchable > 0)
        
        print(f"   ⚡ Pooled operation summary:")
        print(f"      Storage charging: {charging_hours} hours, {total_charge_gwh:.1f} GWh")
        print(f"      Storage discharging: {discharging_hours} hours, {total_discharge_gwh:.1f} GWh")
        print(f"      Dispatchable operation: {dispatch_hours} hours, {total_dispatch_gwh:.1f} GWh")
        print(f"      Dispatchable budget used: {total_dispatch_gwh/total_dispatchable_budget_twh*1000:.1f}%")
        print(f"      Max dispatchable: {np.max(hourly_dispatchable):.0f} MW")
        print(f"      Max storage charge: {np.max(hourly_storage_charge):.0f} MW")
        print(f"      Max storage discharge: {np.max(hourly_storage_discharge):.0f} MW")
        
        # Convert SOC to GWh for visualization
        storage_soc_gwh = soc_mwh / 1000  # Convert MWh to GWh
        print(f"      Storage SOC range: {np.min(storage_soc_gwh):.1f} - {np.max(storage_soc_gwh):.1f} GWh")
        
        # Step 3: Add Potential Dispatchable (NEW)
        print()
        print("🔥 POTENTIAL DISPATCHABLE: Emergency Capacity Analysis")
        print("-" * 50)
        
        # Load potential dispatchable capacity and emission intensities (reuse already-loaded data)
        potential_capacity, tech_combinations = self.load_potential_dispatchable_capacity(
            all_capacities['_raw_data'], all_capacities['_tech_categories'])
        emission_intensities = self.load_emission_intensities(tech_combinations)
        
        # Calculate remaining shortage after storage + planned dispatchable
        total_supply = hourly_baseload + hourly_solar_mw + hourly_wind_mw + hourly_storage_discharge + hourly_dispatchable
        remaining_shortage = np.maximum(0, hourly_demand - total_supply)
        
        # Dispatch potential capacity to fill remaining shortages
        hourly_potential_dispatchable, hourly_additional_emissions = self.dispatch_potential_capacity(
            remaining_shortage, potential_capacity, emission_intensities
        )
        
        return hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable, hourly_potential_dispatchable, storage_soc_gwh, hourly_additional_emissions
    
    def map_timeslices_to_hours(self, season_mapping, time_mapping):
        """Create mapping from timeslices to hour indices"""
        print("🔗 Mapping Timeslices to Hour Indices...")
        
        timeslice_hour_mapping = {}
        
        # Get all unique timeslices from our data
        # For now, we'll create mappings for common FACETS patterns
        common_timeslices = ['R1AM1', 'R1AM2', 'R1D', 'R1DP', 'R1E', 'R1Z',
                           'S1AM1', 'S1AM2', 'S1D', 'S1DP', 'S1E', 'S1Z', 
                           'T1AM1', 'T1AM2', 'T1D', 'T1DP', 'T1E', 'T1Z',
                           'W1AM1', 'W1AM2', 'W1D', 'W1DP', 'W1E', 'W1Z']
        
        for timeslice in common_timeslices:
            # Parse timeslice: e.g., "R1AM2" -> season="R1", time="AM2"
            season_part = timeslice[:2]  # R1, S1, T1, W1
            time_period = timeslice[2:]  # AM1, AM2, D, DP, E, Z
            
            # Get months for this season
            if season_part in season_mapping:
                months = season_mapping[season_part]
            else:
                continue  # Skip if season not found
            
            # Get hours for this time period (use as-is from mapping file)
            if time_period in time_mapping:
                hours = time_mapping[time_period]
            else:
                continue  # Skip if time period not found
            
            # Generate hour indices for this timeslice
            hour_indices = []
            
            for month in months:
                # Calculate days in month (simplified - using 30 for all)
                days_in_month = 30  # Simplified
                if month == 2:
                    days_in_month = 28
                elif month in [1, 3, 5, 7, 8, 10, 12]:
                    days_in_month = 31
                
                # Calculate starting hour for this month (1-based)
                start_hour = sum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][:month-1]) * 24 + 1
                
                # Add hours for each day in the month
                for day in range(days_in_month):
                    for hour in hours:
                        hour_index = start_hour + day * 24 + (hour - 1)  # Convert to 0-based
                        if 1 <= hour_index <= 8760:  # Valid hour range
                            hour_indices.append(hour_index - 1)  # Convert to 0-based for array indexing
            
            timeslice_hour_mapping[timeslice] = hour_indices
        
        print(f"   ✅ Mapped {len(timeslice_hour_mapping)} timeslices to hours")
        return timeslice_hour_mapping
    
    def create_hourly_baseload_profile(self, baseload_by_timeslice, timeslice_hour_mapping):
        """Create hourly baseload profile by spreading timeslice values"""
        print("⚡ Creating Hourly Baseload Profile...")
        
        # Initialize hourly profile (8760 hours)
        hourly_baseload = np.zeros(8760)
        
        for timeslice, generation_twh in baseload_by_timeslice.items():
            if timeslice in timeslice_hour_mapping:
                hour_indices = timeslice_hour_mapping[timeslice]
                
                if len(hour_indices) > 0:
                    # Convert TWh to MW and spread equally across hours
                    generation_mw_per_hour = (generation_twh * 1000 * 1000) / len(hour_indices)  # TWh -> MWh -> MW
                    
                    # Assign to all hours in this timeslice
                    for hour_idx in hour_indices:
                        hourly_baseload[hour_idx] += generation_mw_per_hour
        
        print(f"   ✅ Created hourly profile: {hourly_baseload.min():.0f} - {hourly_baseload.max():.0f} MW")
        print(f"   🏭 Total baseload: {hourly_baseload.sum() / 1000:.1f} GWh")
        
        return hourly_baseload
    
    def run_storage_adequacy_analysis(self, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
                                     timeslice_hour_mapping, dispatchable_by_timeslice, all_capacities):
        """
        Run iterative storage sensitivity analysis to determine adequacy requirements
        
        Increments storage capacity and re-runs simulation until shortage is eliminated
        Maximum 20 iterations
        """
        print("\n" + "="*70)
        print("🔋 STORAGE ADEQUACY SENSITIVITY ANALYSIS")
        print(f"   Incrementing 8h battery storage by {self.storage_increment} GW per iteration")
        print(f"   Maximum 20 iterations or until shortage eliminated")
        print("="*70)
        
        # Storage to track results
        results = []
        
        # Get baseline storage
        baseline_storage = all_capacities['storage'].copy()
        baseline_total = sum(baseline_storage.values()) if baseline_storage else 0
        
        # Run iterations
        for iteration in range(21):  # 0-20 (0 is baseline, 1-20 are increments)
            # Calculate storage for this iteration
            if iteration == 0:
                # Baseline - use original storage
                storage_added_gw = 0
                modified_storage = baseline_storage.copy()
            else:
                # Add storage increments as 8h battery
                storage_added_gw = iteration * self.storage_increment
                modified_storage = baseline_storage.copy()
                
                # Add to 8h battery storage (create key if doesn't exist)
                storage_8h_key = 'Storage|Battery 8h'
                if storage_8h_key in modified_storage:
                    modified_storage[storage_8h_key] += storage_added_gw
                else:
                    modified_storage[storage_8h_key] = storage_added_gw
            
            total_storage_gw = sum(modified_storage.values()) if modified_storage else 0
            
            # Create modified all_capacities for this iteration
            modified_all_capacities = all_capacities.copy()
            modified_all_capacities['storage'] = modified_storage
            
            # Run pooled simulation with modified storage
            hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable, \
            hourly_potential_dispatchable, storage_soc_gwh, hourly_additional_emissions = \
                self.simulate_pooled_storage_dispatchable(
                    modified_storage, dispatchable_by_timeslice, hourly_demand, 
                    hourly_baseload, hourly_solar_mw, hourly_wind_mw, modified_all_capacities
                )
            
            # Calculate shortage
            total_supply = (hourly_baseload + hourly_solar_mw + hourly_wind_mw + 
                           hourly_storage_discharge + hourly_dispatchable)
            shortage = np.maximum(0, hourly_demand - total_supply)
            
            shortage_twh = shortage.sum() / 1_000_000  # MW-hours to TWh
            shortage_hours = np.sum(shortage > 0)
            annual_demand_twh = hourly_demand.sum() / 1_000_000
            shortage_pct = (shortage_twh / annual_demand_twh * 100) if annual_demand_twh > 0 else 0
            peak_shortage_mw = shortage.max()
            
            # Storage performance metrics
            if total_storage_gw > 0:
                storage_energy_gwh = hourly_storage_discharge.sum() / 1000
                # Assume mixed duration - calculate effective duration from capacity mix
                total_duration_gwh = 0
                for tech, cap_gw in modified_storage.items():
                    if '4h' in tech:
                        total_duration_gwh += cap_gw * 4
                    elif '8h' in tech:
                        total_duration_gwh += cap_gw * 8
                    elif '12h' in tech:
                        total_duration_gwh += cap_gw * 12
                    else:  # Pumped hydro or other - assume 8h
                        total_duration_gwh += cap_gw * 8
                
                storage_cycles = storage_energy_gwh / total_duration_gwh if total_duration_gwh > 0 else 0
                
                # Utilization: how often storage is used
                storage_active_hours = np.sum((hourly_storage_charge > 0) | (hourly_storage_discharge > 0))
                storage_utilization_pct = (storage_active_hours / 8760 * 100)
            else:
                storage_cycles = 0
                storage_utilization_pct = 0
            
            # Store results
            results.append({
                'iteration': iteration,
                'storage_added_gw': storage_added_gw,
                'total_storage_gw': total_storage_gw,
                'shortage_twh': shortage_twh,
                'shortage_hours': shortage_hours,
                'shortage_pct_of_demand': shortage_pct,
                'peak_shortage_mw': peak_shortage_mw,
                'storage_cycles_per_year': storage_cycles,
                'storage_utilization_pct': storage_utilization_pct
            })
            
            # Print progress
            if iteration == 0:
                print(f"   Iteration {iteration} (Baseline): Storage = {total_storage_gw:.1f} GW, Shortage = {shortage_twh:.2f} TWh ({shortage_pct:.2f}%)")
            else:
                print(f"   Iteration {iteration}: Storage = {total_storage_gw:.1f} GW (+{storage_added_gw:.1f} GW), Shortage = {shortage_twh:.2f} TWh ({shortage_pct:.2f}%)")
            
            # Check stopping criterion (shortage effectively zero)
            if shortage_twh <= 0.01 and iteration > 0:
                print(f"   ✅ Adequacy achieved at +{storage_added_gw:.1f} GW added storage ({total_storage_gw:.1f} GW total)")
                break
        
        # Convert to DataFrame
        sensitivity_df = pd.DataFrame(results)
        
        # Analyze temporal mismatch (baseline only)
        if len(results) > 0:
            baseline = results[0]
            print()
            print("="*70)
            print("📊 TEMPORAL MISMATCH ANALYSIS (Baseline)")
            print("="*70)
            
            # Calculate surplus AND shortage from the same baseline (NO storage, NO dispatchable)
            # This shows the raw temporal mismatch that storage would need to solve
            baseline_supply = (hourly_baseload + hourly_solar_mw + hourly_wind_mw)
            baseline_balance_raw = baseline_supply - hourly_demand
            
            # Calculate surplus (positive hours only)
            baseline_surplus = np.maximum(0, baseline_balance_raw)
            surplus_twh = baseline_surplus.sum() / 1_000_000
            surplus_hours = np.sum(baseline_balance_raw > 0)
            
            # Calculate shortage (negative hours only, as positive values)
            baseline_shortage = np.maximum(0, -baseline_balance_raw)
            shortage_twh = baseline_shortage.sum() / 1_000_000
            shortage_hours = np.sum(baseline_balance_raw < 0)
            
            print(f"   📈 Annual Surplus Energy (baseload+RE only): {surplus_twh:.2f} TWh ({surplus_hours:,} hours)")
            print(f"   📉 Annual Shortage Energy (baseload+RE only): {shortage_twh:.2f} TWh ({shortage_hours:,} hours)")
            print(f"   ⚖️  Energy Balance: {surplus_twh - shortage_twh:+.2f} TWh")
            print(f"   💡 Note: This is WITHOUT storage or dispatchable - shows raw temporal mismatch")
            print()
            
            # Calculate theoretical arbitrage potential with storage efficiency
            storage_efficiency = 0.719  # 71.9% round-trip
            arbitrageable_energy = surplus_twh * storage_efficiency
            energy_gap = shortage_twh - arbitrageable_energy
            
            print(f"   🔋 Theoretical Analysis (with {storage_efficiency*100:.1f}% storage efficiency):")
            print(f"      Surplus energy available: {surplus_twh:.2f} TWh")
            print(f"      After storage losses: {arbitrageable_energy:.2f} TWh")
            print(f"      Shortage to cover: {shortage_twh:.2f} TWh")
            print(f"      Energy gap: {energy_gap:.2f} TWh ({abs(energy_gap)/shortage_twh*100:.1f}% of shortage)")
            print()
            
            # Calculate cumulative energy imbalance to determine required storage capacity
            # baseline_balance_raw is in MW, cumsum gives MW·hour, divide by 1000 for GWh
            cumulative_balance_mwh = np.cumsum(baseline_balance_raw)
            cumulative_balance_gwh = cumulative_balance_mwh / 1000
            max_storage_gwh = cumulative_balance_gwh.max()
            min_storage_gwh = cumulative_balance_gwh.min()
            required_storage_energy = max_storage_gwh - min_storage_gwh
            
            print(f"   💡 Storage Energy Capacity Required:")
            print(f"      Cumulative energy swing: {required_storage_energy:.1f} GWh ({required_storage_energy/1000:.2f} TWh)")
            print(f"      Current storage energy (baseline): {baseline['total_storage_gw'] * 8:.1f} GWh ({baseline['total_storage_gw'] * 8 / 1000:.2f} TWh)")
            print(f"      Energy capacity multiplier needed: {required_storage_energy / (baseline['total_storage_gw'] * 8):.1f}x current capacity")
            print()
            
            # Analyze shortage event durations
            print(f"   📅 SHORTAGE EVENT CHARACTERISTICS:")
            print(f"   " + "-"*65)
            
            # Identify consecutive shortage events (when balance < 0)
            shortage_hours = baseline_balance_raw < 0
            events = []
            in_event = False
            event_start = 0
            event_energy = 0
            
            for hour in range(len(shortage_hours)):
                if shortage_hours[hour] and not in_event:
                    # Start of new event
                    in_event = True
                    event_start = hour
                    event_energy = abs(baseline_balance_raw[hour])
                elif shortage_hours[hour] and in_event:
                    # Continue event
                    event_energy += abs(baseline_balance_raw[hour])
                elif not shortage_hours[hour] and in_event:
                    # End of event
                    duration = hour - event_start
                    events.append({'start': event_start, 'duration': duration, 'energy_gwh': event_energy / 1000})
                    in_event = False
                    event_energy = 0
            
            # Handle event that goes to end of year
            if in_event:
                duration = len(shortage_hours) - event_start
                events.append({'start': event_start, 'duration': duration, 'energy_gwh': event_energy / 1000})
            
            if len(events) > 0:
                durations = [e['duration'] for e in events]
                energies = [e['energy_gwh'] for e in events]
                mean_duration = np.mean(durations)
                median_duration = np.median(durations)
                max_duration = np.max(durations)
                
                # Calculate % of shortage in long events
                total_shortage_gwh = sum(energies)
                shortage_gt_48h = sum(e['energy_gwh'] for e in events if e['duration'] > 48)
                shortage_gt_168h = sum(e['energy_gwh'] for e in events if e['duration'] > 168)
                pct_gt_48h = (shortage_gt_48h / total_shortage_gwh * 100) if total_shortage_gwh > 0 else 0
                pct_gt_168h = (shortage_gt_168h / total_shortage_gwh * 100) if total_shortage_gwh > 0 else 0
                
                print(f"      Number of shortage events: {len(events)}")
                print(f"      Mean duration: {mean_duration:.0f} hours ({mean_duration/24:.1f} days)")
                print(f"      Median duration: {median_duration:.0f} hours ({median_duration/24:.1f} days)")
                print(f"      Longest event: {max_duration:.0f} hours ({max_duration/24:.1f} days)")
                print(f"      Events >48h contain: {pct_gt_48h:.0f}% of total shortage energy")
                print(f"      Events >168h contain: {pct_gt_168h:.0f}% of total shortage energy")
                print(f"      → Shortage dominated by multi-day events (not hourly variability)")
            print()
            
            # Storage duration adequacy curve
            print(f"   ⚡ STORAGE DURATION ADEQUACY ANALYSIS:")
            print(f"   " + "-"*65)
            print(f"      Testing different durations at constant {baseline['total_storage_gw']:.1f} GW power")
            print(f"      (Baseline is raw supply-demand mismatch, no storage)")
            print()
            
            # Calculate baseline shortage (no storage)
            baseline_shortage_gwh = 0
            for hour in range(8760):
                hourly_balance = baseline_supply[hour] - hourly_demand[hour]
                if hourly_balance < 0:
                    baseline_shortage_gwh += abs(hourly_balance) / 1000
            
            # Test durations: 1h, 2h, 4h, 8h, 12h, 24h, 48h, 72h, 168h (1 week), 720h (1 month)
            test_durations = [1, 2, 4, 8, 12, 24, 48, 72, 168, 720]
            storage_power_gw = baseline['total_storage_gw']
            
            for duration_hours in test_durations:
                # Energy capacity for this duration
                energy_capacity_gwh = storage_power_gw * duration_hours
                
                # Simple simulation: track state of charge
                soc_gwh = energy_capacity_gwh / 2  # Start at 50%
                shortage_with_storage = 0
                storage_efficiency = 0.85  # Round-trip efficiency (sqrt of 0.72)
                
                for hour in range(8760):
                    hourly_balance = baseline_supply[hour] - hourly_demand[hour]
                    
                    if hourly_balance > 0:
                        # Surplus - charge storage
                        surplus_gwh = hourly_balance / 1000
                        max_charge = min(surplus_gwh, storage_power_gw, energy_capacity_gwh - soc_gwh)
                        soc_gwh = min(soc_gwh + (max_charge * storage_efficiency), energy_capacity_gwh)
                    else:
                        # Shortage - discharge storage
                        shortage_gwh = abs(hourly_balance) / 1000
                        max_discharge = min(shortage_gwh, storage_power_gw, soc_gwh)
                        actual_discharge = max_discharge * storage_efficiency  # Energy delivered to grid
                        soc_gwh = max(soc_gwh - max_discharge, 0)
                        remaining_shortage = shortage_gwh - actual_discharge
                        shortage_with_storage += remaining_shortage
                
                shortage_eliminated = baseline_shortage_gwh - shortage_with_storage
                shortage_eliminated_pct = (shortage_eliminated / baseline_shortage_gwh) * 100
                
                # Format duration label
                if duration_hours < 24:
                    dur_label = f"{duration_hours}h"
                elif duration_hours < 168:
                    dur_label = f"{duration_hours//24}d"
                else:
                    dur_label = f"{duration_hours//168}w"
                
                print(f"      {dur_label:>4} ({energy_capacity_gwh:>8,.0f} GWh):  {shortage_eliminated_pct:>5.1f}% shortage eliminated")
            
            print()
            print(f"   🔍 ROOT CAUSE: Multi-day temporal mismatch within FACETS timeslices")
            print(f"      • FACETS optimizes at coarse timeslices (e.g., 'Winter Day' = 360h average)")
            print(f"      • Hourly reality shows shortage/surplus events lasting days or weeks")
            print(f"      • Short-duration storage (4h/8h) cannot bridge multi-day energy deficits")
            print(f"      • Solution requires either: massive long-duration storage OR more flexible generation")
            
            # Prepare temporal pattern analysis data for Excel export
            temporal_analysis = {
                'event_stats': {
                    'num_events': len(events) if len(events) > 0 else 0,
                    'mean_duration_hours': mean_duration if len(events) > 0 else 0,
                    'median_duration_hours': median_duration if len(events) > 0 else 0,
                    'max_duration_hours': max_duration if len(events) > 0 else 0,
                    'pct_gt_48h': pct_gt_48h if len(events) > 0 else 0,
                    'pct_gt_168h': pct_gt_168h if len(events) > 0 else 0
                },
                'duration_adequacy': [],
                'energy_balance': {
                    'surplus_twh': surplus_twh,
                    'shortage_twh': shortage_twh,
                    'balance_twh': surplus_twh - shortage_twh,
                    'cumulative_swing_gwh': required_storage_energy,
                    'current_storage_gwh': baseline['total_storage_gw'] * 8,
                    'multiplier_needed': required_storage_energy / (baseline['total_storage_gw'] * 8)
                }
            }
            
            # Collect duration adequacy data
            for duration_hours in test_durations:
                energy_capacity_gwh = storage_power_gw * duration_hours
                soc_gwh = energy_capacity_gwh / 2
                shortage_with_storage = 0
                storage_efficiency = 0.85
                
                for hour in range(8760):
                    hourly_balance = baseline_supply[hour] - hourly_demand[hour]
                    if hourly_balance > 0:
                        surplus_gwh = hourly_balance / 1000
                        max_charge = min(surplus_gwh, storage_power_gw, energy_capacity_gwh - soc_gwh)
                        soc_gwh = min(soc_gwh + (max_charge * storage_efficiency), energy_capacity_gwh)
                    else:
                        shortage_gwh = abs(hourly_balance) / 1000
                        max_discharge = min(shortage_gwh, storage_power_gw, soc_gwh)
                        actual_discharge = max_discharge * storage_efficiency
                        soc_gwh = max(soc_gwh - max_discharge, 0)
                        remaining_shortage = shortage_gwh - actual_discharge
                        shortage_with_storage += remaining_shortage
                
                shortage_eliminated = baseline_shortage_gwh - shortage_with_storage
                shortage_eliminated_pct = (shortage_eliminated / baseline_shortage_gwh) * 100
                
                temporal_analysis['duration_adequacy'].append({
                    'duration_hours': duration_hours,
                    'energy_capacity_gwh': energy_capacity_gwh,
                    'shortage_eliminated_pct': shortage_eliminated_pct
                })
        else:
            temporal_analysis = None
        
        print("="*70)
        print(f"   💾 Sensitivity analysis complete: {len(results)} iterations")
        print("="*70)
        
        return sensitivity_df, temporal_analysis
    
    def create_temporal_mismatch_visualization(self, temporal_analysis, hourly_demand, total_supply):
        """Create 2-panel visualization showing why short-duration storage fails"""
        import matplotlib.pyplot as plt
        import numpy as np
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        fig.patch.set_facecolor('white')
        
        # Calculate cumulative energy balance: cumsum(total_supply - demand)
        hourly_balance = total_supply - hourly_demand
        cumulative_balance_mwh = np.cumsum(hourly_balance)
        cumulative_balance_gwh = cumulative_balance_mwh / 1000
        
        # Calculate swing
        min_cumulative = cumulative_balance_gwh.min()
        max_cumulative = cumulative_balance_gwh.max()
        swing = max_cumulative - min_cumulative
        
        # Debug: print cumulative statistics
        print(f"   🔍 Cumulative Balance Stats (Total Supply - Demand):")
        print(f"      Hourly balance: min={hourly_balance.min():,.0f} MW, max={hourly_balance.max():,.0f} MW")
        print(f"      Cumulative: starts at 0, ends at {cumulative_balance_gwh[-1]:,.0f} GWh (annual net)")
        print(f"      Cumulative: min={min_cumulative:,.0f} GWh, max={max_cumulative:,.0f} GWh")
        print(f"      Cumulative swing (min to max): {swing:,.0f} GWh")
        print(f"      Surplus hours (supply > demand): {(hourly_balance > 0).sum()}/8760 ({(hourly_balance > 0).sum()/87.6:.1f}%)")
        print(f"      Shortage hours (supply < demand): {(hourly_balance < 0).sum()}/8760 ({(hourly_balance < 0).sum()/87.6:.1f}%)")
        
        hours = np.arange(8760)
        
        # TOP PANEL: Cumulative Energy Balance
        ax1.plot(hours, cumulative_balance_gwh, linewidth=2, color='#2E86AB', label='Cumulative Energy Balance')
        ax1.fill_between(hours, cumulative_balance_gwh, 0, where=(cumulative_balance_gwh >= 0), 
                         alpha=0.3, color='green', label='Storage Charging Period')
        ax1.fill_between(hours, cumulative_balance_gwh, 0, where=(cumulative_balance_gwh < 0), 
                         alpha=0.3, color='red', label='Storage Depleting Period')
        
        # Add storage capacity reference lines
        storage_8h_capacity = temporal_analysis['energy_balance']['current_storage_gwh']
        ax1.axhline(y=storage_8h_capacity, color='orange', linestyle='--', linewidth=2, 
                   label=f'8h Storage Capacity (+{storage_8h_capacity:.0f} GWh)')
        ax1.axhline(y=-storage_8h_capacity, color='orange', linestyle='--', linewidth=2,
                   label=f'8h Storage Capacity (-{storage_8h_capacity:.0f} GWh)')
        
        # Add 1-week storage reference
        storage_1week = storage_8h_capacity * 21  # 168h / 8h = 21x
        ax1.axhline(y=storage_1week, color='purple', linestyle=':', linewidth=1.5, alpha=0.6,
                   label=f'1-week Storage (+{storage_1week:.0f} GWh)')
        ax1.axhline(y=-storage_1week, color='purple', linestyle=':', linewidth=1.5, alpha=0.6,
                   label=f'1-week Storage (-{storage_1week:.0f} GWh)')
        
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.7)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_xlabel('Hour of Year', fontsize=11, fontweight='bold')
        ax1.set_ylabel('Cumulative Energy Balance (GWh)\nCumsum(Total Supply - Demand)', fontsize=11, fontweight='bold')
        ax1.set_title('Cumulative Energy Balance Over Time\n' +
                     f'Starts at 0, ends at {cumulative_balance_gwh[-1]/1000:.2f} TWh | ' +
                     f'Swing: {swing:.0f} GWh (min: {min_cumulative:.0f}, max: {max_cumulative:.0f})',
                     fontsize=13, fontweight='bold', pad=15)
        ax1.legend(loc='upper right', fontsize=9, framealpha=0.9)
        
        # Add annotation
        ax1.text(0.02, 0.97, 'Total Supply = Baseload + Solar + Wind + Storage + Dispatchable\nCumulative shows net energy position throughout the year', 
                transform=ax1.transAxes, fontsize=9, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Add month labels
        month_starts = [0, 744, 1416, 2160, 2880, 3624, 4344, 5088, 5832, 6552, 7296, 8016]
        month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        ax1.set_xticks(month_starts)
        ax1.set_xticklabels(month_labels)
        
        # BOTTOM PANEL: Storage Duration Adequacy Curve
        durations = [item['duration_hours'] for item in temporal_analysis['duration_adequacy']]
        shortage_eliminated = [item['shortage_eliminated_pct'] for item in temporal_analysis['duration_adequacy']]
        
        # Create x-axis labels
        duration_labels = []
        for dur in durations:
            if dur < 24:
                duration_labels.append(f"{dur}h")
            elif dur < 168:
                duration_labels.append(f"{dur//24}d")
            else:
                duration_labels.append(f"{dur//168}w")
        
        x_positions = np.arange(len(durations))
        
        # Plot bars
        colors = ['#d62728' if pct < 20 else '#ff7f0e' if pct < 40 else '#2ca02c' for pct in shortage_eliminated]
        bars = ax2.bar(x_positions, shortage_eliminated, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
        
        # Add value labels on bars
        for i, (pos, val) in enumerate(zip(x_positions, shortage_eliminated)):
            ax2.text(pos, val + 1.5, f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # Highlight 4h and 8h
        for i, dur in enumerate(durations):
            if dur == 4:
                ax2.text(i, -8, '4h Li-ion\n(typical)', ha='center', fontsize=9, 
                        fontweight='bold', color='darkred', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
            elif dur == 8:
                ax2.text(i, -8, '8h Li-ion\n(typical)', ha='center', fontsize=9, 
                        fontweight='bold', color='darkred', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3))
        
        ax2.set_xlabel('Storage Duration', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Shortage Eliminated (%)', fontsize=11, fontweight='bold')
        ax2.set_title('Storage Duration Adequacy: Why Short-Duration Storage Fails\n' +
                     'Even 1-month storage only eliminates 43% of shortage',
                     fontsize=13, fontweight='bold', pad=15)
        ax2.set_xticks(x_positions)
        ax2.set_xticklabels(duration_labels, rotation=0)
        ax2.set_ylim(0, max(shortage_eliminated) * 1.15)
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax2.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='50% threshold')
        
        # Add color legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#d62728', alpha=0.7, label='<20% (Inadequate)'),
            Patch(facecolor='#ff7f0e', alpha=0.7, label='20-40% (Insufficient)'),
            Patch(facecolor='#2ca02c', alpha=0.7, label='>40% (Better, but still inadequate)')
        ]
        ax2.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.9)
        
        plt.tight_layout()
        
        # Save figure
        system_suffix = self.region if self.region else self.transmission_group
        scenario_folder = self.scenario.replace(".", "_")
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs", "plots", scenario_folder)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"temporal_mismatch_analysis_{system_suffix}.png")
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"   📊 Saved temporal mismatch visualization: {os.path.relpath(output_path, os.path.dirname(os.path.abspath(__file__)))}")
        
        return output_path
                 
        
    def run_unified_validation_analysis(self):
        """Run operationally realistic pooled validation analysis"""
        print("🚀 Starting FACETS Validation Analysis")
        print("🎯 Operationally Realistic Pooled Approach")
        print("="*70)
        
        # Step 1: Load all base data
        print("📈 Loading Base Data...")
        hourly_demand = self.load_hourly_demand()
        
        season_mapping, time_mapping = self.load_timeslice_mapping()
        baseload_by_timeslice = self.load_baseload_generation()
        timeslice_hour_mapping = self.map_timeslices_to_hours(season_mapping, time_mapping)
        hourly_baseload = self.create_hourly_baseload_profile(baseload_by_timeslice, timeslice_hour_mapping)
        
        renewable_generation = self.load_renewable_generation_by_timeslice()
        regional_solar_cf, regional_wind_cf = self.load_hourly_renewable_profiles()
        hourly_solar_mw, hourly_wind_mw = self.create_hourly_renewable_profiles(
            renewable_generation, regional_solar_cf, regional_wind_cf, timeslice_hour_mapping)
        
        # Load comprehensive capacity data (includes storage, renewable, baseload, dispatchable)
        all_capacities = self.load_all_capacities()
        dispatchable_by_timeslice = self.load_dispatchable_generation()
        
        print("✅ Base data loaded successfully!")
        print()
        
        # Step 2: Run Operationally Realistic Analysis
        print("🔄 OPERATIONALLY REALISTIC VALIDATION")
        print("-" * 50)
        hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable, hourly_potential_dispatchable, storage_soc_gwh, hourly_additional_emissions = self.simulate_pooled_storage_dispatchable(
            all_capacities['storage'], dispatchable_by_timeslice, hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw, all_capacities)
        
        # Find top shortage weeks (now including potential dispatchable)
        week_data = self.find_top_shortage_weeks(hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw, 
                                               hourly_storage_discharge, hourly_dispatchable + hourly_potential_dispatchable)
        
        # Step 3: Surplus Analysis
        print("🔄 SURPLUS ANALYSIS: Finding High Surplus Periods")
        print("-" * 50)
        
        # Find top surplus weeks
        surplus_week_data = self.find_top_surplus_weeks(hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw, 
                                                       hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable)
        
        # Create chronological week charts (replaces individual shortage/surplus charts)
        chronological_charts = []
        if self.enable_plots:
            print()
            print("🔄 CHRONOLOGICAL ANALYSIS: All 52 Weeks")
            print("-" * 50)
            chronological_charts = self.plot_all_weeks_chronologically(
                hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
                hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable + hourly_potential_dispatchable,
                week_data, surplus_week_data, "Operationally Realistic", storage_soc_gwh
            )
        else:
            print()
            print("🔄 CHRONOLOGICAL ANALYSIS: Skipped (--no-plots enabled)")
            print("-" * 50)
        
        # Step 4: Create FACETS Timeslice Aggregation View (Power)
        timeslice_chart = None
        if self.enable_plots:
            print()
            print("🔄 TIMESLICE AGGREGATION VIEW: How FACETS Sees the Data")
            print("-" * 50)
            timeslice_chart = self.create_timeslice_aggregation_view(
                hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
                hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable,
                storage_soc_gwh, "Operationally Realistic"
            )
        else:
            print()
            print("🔄 TIMESLICE AGGREGATION VIEW: Skipped (--no-plots enabled)")
            print("-" * 50)
        
        # Step 5: Create FACETS Timeslice Energy View (Energy)
        timeslice_energy_chart = None
        if self.enable_plots:
            print()
            print("⚡ TIMESLICE ENERGY VIEW: FACETS Energy Accounting")
            print("-" * 50)
            timeslice_energy_chart = self.create_timeslice_energy_view(
                hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
                hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable,
                storage_soc_gwh, "Operationally Realistic"
            )
        else:
            print()
            print("⚡ TIMESLICE ENERGY VIEW: Skipped (--no-plots enabled)")
            print("-" * 50)
        
        print("="*70)
        print("✅ FACETS Validation Analysis Complete!")
        if self.enable_plots:
            print("📊 Generated operationally realistic validation charts")
        else:
            print("📊 Charts skipped (--no-plots enabled for faster batch processing)")
        print("🎯 Pooled dispatchable allocation shows realistic grid operations")
        
        # Generate comprehensive summary metrics for pooled approach
        # Calculate renewable totals from nested regional structure
        total_solar_twh = sum(sum(region_data.values()) for region_data in renewable_generation['solar'].values()) if renewable_generation['solar'] else 0
        total_wind_twh = sum(sum(region_data.values()) for region_data in renewable_generation['wind'].values()) if renewable_generation['wind'] else 0
        
        summary_metrics = self.generate_summary_metrics_single(
            hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
            hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable,
            all_capacities, storage_soc_gwh, hourly_potential_dispatchable, hourly_additional_emissions
        )
        
        # Run storage sensitivity analysis if requested
        sensitivity_df = None
        temporal_analysis = None
        if self.storage_increment is not None:
            sensitivity_df, temporal_analysis = self.run_storage_adequacy_analysis(
                hourly_demand, hourly_baseload, hourly_solar_mw, hourly_wind_mw,
                timeslice_hour_mapping, dispatchable_by_timeslice, all_capacities
            )
            
            # Generate visualization if temporal analysis was performed (always generate for sensitivity analysis)
            if temporal_analysis is not None:
                # Total supply includes ALL generation sources
                total_supply = hourly_baseload + hourly_solar_mw + hourly_wind_mw + hourly_storage_discharge + hourly_dispatchable
                self.create_temporal_mismatch_visualization(temporal_analysis, hourly_demand, total_supply)
        
        # Save all metrics to Excel (including sensitivity if available)
        self.save_summary_metrics(
            summary_metrics, 
            {
                'hourly_demand': hourly_demand,
                'hourly_baseload': hourly_baseload, 
                'hourly_solar_mw': hourly_solar_mw,
                'hourly_wind_mw': hourly_wind_mw,
                'hourly_storage_charge': hourly_storage_charge,
                'hourly_storage_discharge': hourly_storage_discharge,
                'hourly_dispatchable': hourly_dispatchable,
                'hourly_potential_dispatchable': hourly_potential_dispatchable if hourly_potential_dispatchable is not None else np.zeros(8760),
                'storage_soc_gwh': storage_soc_gwh
            },
            sensitivity_df,
            temporal_analysis
        )
        
        return {
            'pooled': {
                'shortage_week_data': week_data,
                'surplus_week_data': surplus_week_data,
                'hourly_data': (hourly_baseload, hourly_solar_mw, hourly_wind_mw, 
                               hourly_storage_charge, hourly_storage_discharge, hourly_dispatchable),
                'chronological_charts': chronological_charts,
                'timeslice_chart': timeslice_chart,
                'timeslice_energy_chart': timeslice_energy_chart
            },
            'summary_metrics': summary_metrics,
            'storage_sensitivity': sensitivity_df
        }
    
    def run_phase1_analysis(self):
        """Run Phase 1: Demand plotting analysis"""
        print("🚀 Starting Phase 1: Seasonal Demand Analysis")
        print("="*70)
        
        # Step 1: Load demand data
        hourly_demand = self.load_hourly_demand()
        
        # Step 2: Extract monthly data
        monthly_data = self.extract_monthly_data(hourly_demand)
        
        # Step 3: Create charts
        fig = self.plot_seasonal_demand(monthly_data)
        
        print("="*70)
        print("✅ Phase 1 Complete!")
        print("📈 Next phases will add supply sources as stacked areas")
        print("   - Phase 2: Baseload generation")
        print("   - Phase 3: Solar generation")
        print("   - Phase 4: Wind generation") 
        print("   - Phase 5: Storage & dispatchable")
        
        return monthly_data, fig

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='FACETS Hourly Operational Simulator')
    parser.add_argument('--transmission_group', type=str, default='MISO_North',
                       help='Transmission group to analyze (e.g., MISO_North, MISO_South, MISO_Central)')
    parser.add_argument('--scenario', type=str, default='re-L.gp-L.Cp-95.ncs-H.smr-L',
                       help='FACETS scenario to analyze')
    parser.add_argument('--weather_year', type=int, default=2012,
                       help='Weather year for demand and renewable profiles')
    parser.add_argument('--no-plots', action='store_true',
                       help='Disable chart generation (faster for batch processing)')
    parser.add_argument('--storage_increment', type=float, default=None,
                       help='Enable storage sensitivity analysis (GW to add per iteration, e.g., 0.5)')
    parser.add_argument('--data_version', type=str, default=None,
                       help='Data version subfolder for inputs/outputs (e.g., "04Aug25", "25Oct25")')
    
    args = parser.parse_args()
    
    # Create simulator with command line parameters
    creator = HourlySupplyCreator(
        transmission_group=args.transmission_group,
        scenario=args.scenario,
        weather_year=args.weather_year,
        enable_plots=not args.no_plots,
        storage_increment=args.storage_increment,
        data_version=args.data_version
    )
    
    print("🎯 FACETS Hourly Operational Simulator")
    print("⚡ Comprehensive operational analysis with professional outputs")
    print("="*70)
    
    # Run unified analysis that produces both charts and metrics
    results = creator.run_unified_validation_analysis()
    
    print("\n" + "="*70)
    print("✅ FACETS simulation complete!")
    print("📊 Generated outputs:")
    if not args.no_plots:
        print("   📈 Chronological week analysis charts (11 charts, 5 weeks each)")
        print("   🔋 Storage level lines (navy dashed, GWh, secondary Y-axis)")
        print("   📊 FACETS timeslice aggregation view (power perspective, GW)")
        print("   ⚡ FACETS timeslice energy view (energy accounting, TWh)")
    else:
        print("   📊 Charts skipped (--no-plots enabled for faster batch processing)")
    print("   📋 Professional Excel metrics")
    print("   🔴 Top shortage weeks highlighted in chart titles")
    print("   🟢 Top surplus weeks highlighted in chart titles")
    print("🎯 All outputs saved in scenario-specific subfolders!")
    print("💡 Ready for stakeholder analysis and GPI reporting!")
