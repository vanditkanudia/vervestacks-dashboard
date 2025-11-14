#!/usr/bin/env python3
"""
FACETS Hourly Profile Explorer
Detailed visualization of all hourly profiles used in the FACETS validation analysis
"""

import pandas as pd
import numpy as np
import h5py
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import warnings
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os
warnings.filterwarnings('ignore')

class FACETSHourlyProfileExplorer:
    """Explore and visualize all hourly profiles in FACETS validation"""
    
    def __init__(self):
        # Set up paths relative to the script location
        self.model_outputs_path = "../data/model_outputs/"
        self.hourly_data_path = "../data/hourly_data/"
        self.vs_profiles_path = "../../../vs_native_profiles/"
        self.scenario = "gp-I.re-L.Pol-IRA.Cp-95.ncs-I.smr-I"
        self.year = 2045
        self.region = "p063"  # CSV format
        self.region_hdf5 = "p63"  # HDF5 format
        self.timeslice = "W1AM2"  # Winter late morning for detailed analysis
        
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
                              box_alignment=(1, 1))  # Align right-top
            
            fig.add_artist(ab)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not add logo watermark: {e}")
        
    def load_and_process_all_profiles(self):
        """Load all hourly profiles used in the analysis"""
        print("📈 Loading and Processing All Hourly Profiles...")
        
        # Step 1: Get FACETS capacity data
        print("   🏗️  Loading FACETS capacity planning...")
        capacity_file = f"{self.model_outputs_path}VSInput_capacity by tech and region.csv"
        
        # Read capacity data
        capacity_data = []
        chunk_size = 50000
        for chunk in pd.read_csv(capacity_file, chunksize=chunk_size):
            filtered = chunk[
                (chunk['scen'] == self.scenario) &
                (chunk['year'] == self.year) &
                (chunk['region'] == self.region)
            ]
            if not filtered.empty:
                capacity_data.append(filtered)
        
        if capacity_data:
            capacity_df = pd.concat(capacity_data, ignore_index=True)
            tech_capacity = capacity_df.groupby('tech')['value'].sum()
            
            # Categorize technologies
            renewable_techs = ['Solar PV', 'RTPV', 'Solar Thermal', 'Onshore Wind', 'Offshore Wind', 'Hydro', 'Geothermal', 'Biomass']
            storage_techs = ['Storage']
            dispatchable_techs = ['Coal Steam', 'Combined Cycle', 'Combustion Turbine', 'Nuclear', 'O/G Steam', 
                                'Combined Cycle CCS', 'Coal Steam CCS', 'IGCC', 'Fossil Waste']
            
            renewable_capacity = tech_capacity[tech_capacity.index.isin(renewable_techs)].sum()
            storage_capacity = tech_capacity[tech_capacity.index.isin(storage_techs)].sum()
            dispatchable_capacity = tech_capacity[tech_capacity.index.isin(dispatchable_techs)].sum()
            
            print(f"      Renewable: {renewable_capacity:.1f} GW, Storage: {storage_capacity:.1f} GW, Dispatchable: {dispatchable_capacity:.1f} GW")
        else:
            print("      ❌ No capacity data found")
            return None
        
        # Step 2: Map timeslice to hours
        print("   📅 Mapping timeslice to hours...")
        mapping_file = f"{self.model_outputs_path}FACETS_aggtimeslices.csv"
        mapping = pd.read_csv(mapping_file)
        
        season_code = self.timeslice[0]  # W
        day_period = self.timeslice[2:]  # AM2
        
        season_months = mapping[mapping['timeslice'] == season_code]['sourcevalue'].tolist()
        period_hours = mapping[mapping['timeslice'] == day_period]['sourcevalue'].tolist()
        
        # Convert to hour indices and create COMPACT datetime mapping
        hour_indices = []
        datetime_indices = []
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        print(f"      Season '{season_code}' includes months: {[month_names[int(m)-1] for m in season_months]}")
        print(f"      Period '{day_period}' includes hours: {period_hours}")
        
        # Create a compact datetime sequence instead of spanning the full year
        compact_day_counter = 0
        
        for month_str in season_months:
            month = int(month_str)
            start_day = sum(days_in_month[:month-1])
            days_this_month = days_in_month[month-1]
            
            for day in range(days_this_month):
                day_start_hour = (start_day + day) * 24
                for hour_str in period_hours:
                    hour = int(hour_str) - 1
                    hour_indices.append(day_start_hour + hour)
                    
                    # Create COMPACT datetime - sequential days starting from Jan 1
                    compact_date = datetime(self.year, 1, 1) + timedelta(days=compact_day_counter, hours=hour)
                    datetime_indices.append(compact_date)
                
                compact_day_counter += 1
        
        print(f"      Mapped to {len(hour_indices)} hours across {len(season_months)} months")
        print(f"      Compact date range: {min(datetime_indices).strftime('%b %d')} to {max(datetime_indices).strftime('%b %d')}")
        
        # Step 3: Load hourly demand profile
        print("   ⚡ Loading hourly demand profile...")
        with h5py.File(f"{self.hourly_data_path}EER_100by2050_load_hourly.h5", 'r') as f:
            index_0 = f['index_0'][:]
            data = f['data'][:]
            columns = f['columns'][:]
            column_names = [col.decode('utf-8') if isinstance(col, bytes) else col for col in columns]
            region_idx = column_names.index(self.region_hdf5)
            
            year_2045_mask = index_0 == 2045
            demand_2045 = data[year_2045_mask, region_idx]
            hourly_demand = demand_2045[hour_indices]
        
        print(f"      Demand range: {hourly_demand.min():,.0f} - {hourly_demand.max():,.0f} MW")
        
        # Step 4: Load hourly solar profile
        print("   ☀️ Loading hourly solar profile...")
        with h5py.File(f"{self.hourly_data_path}upv-reference_ba.h5", 'r') as f:
            data = f['data'][:]
            columns = f['columns'][:]
            column_names = [col.decode('utf-8') if isinstance(col, bytes) else col for col in columns]
            region_cols = [i for i, col in enumerate(column_names) if col.endswith(f'|{self.region_hdf5}')]
            
            if region_cols:
                solar_profiles = data[:, region_cols]
                solar_avg = np.mean(solar_profiles, axis=1)
                year_hours = len(solar_avg)
                mapped_indices = [idx % year_hours for idx in hour_indices]
                hourly_solar_cf = solar_avg[mapped_indices]
            else:
                hourly_solar_cf = np.zeros(len(hour_indices))
        
        print(f"      Solar CF range: {hourly_solar_cf.min():.3f} - {hourly_solar_cf.max():.3f}")
        
        # Step 5: Load hourly wind profile
        print("   💨 Loading hourly wind profile...")
        with h5py.File(f"{self.hourly_data_path}wind-ons-reference_ba.h5", 'r') as f:
            data = f['data'][:]
            columns = f['columns'][:]
            column_names = [col.decode('utf-8') if isinstance(col, bytes) else col for col in columns]
            region_cols = [i for i, col in enumerate(column_names) if col.endswith(f'|{self.region_hdf5}')]
            
            if region_cols:
                wind_profiles = data[:, region_cols]
                wind_avg = np.mean(wind_profiles, axis=1)
                year_hours = len(wind_avg)
                mapped_indices = [idx % year_hours for idx in hour_indices]
                hourly_wind_cf = wind_avg[mapped_indices]
            else:
                hourly_wind_cf = np.zeros(len(hour_indices))
        
        print(f"      Wind CF range: {hourly_wind_cf.min():.3f} - {hourly_wind_cf.max():.3f}")
        
        # Step 6: Calculate derived profiles
        print("   🔧 Calculating derived profiles...")
        
        # Scale renewable generation (simplified: 40% solar, 60% wind+hydro)
        renewable_capacity_mw = renewable_capacity * 1000  # GW to MW
        solar_share = 0.4
        wind_share = 0.6
        
        hourly_solar_gen = hourly_solar_cf * (renewable_capacity_mw * solar_share)
        hourly_wind_gen = hourly_wind_cf * (renewable_capacity_mw * wind_share)
        hourly_renewable_gen = hourly_solar_gen + hourly_wind_gen
        
        # Calculate dispatchable needs
        hourly_dispatchable_need = hourly_demand - hourly_renewable_gen
        
        # Use the datetime indices we created during mapping
        datetime_index = datetime_indices
        
        print(f"      Renewable generation: {hourly_renewable_gen.min():,.0f} - {hourly_renewable_gen.max():,.0f} MW")
        print(f"      Dispatchable need: {hourly_dispatchable_need.min():,.0f} - {hourly_dispatchable_need.max():,.0f} MW")
        
        return {
            'datetime_index': datetime_index,
            'hour_indices': hour_indices,
            'season_months': season_months,
            'period_hours': period_hours,
            'hourly_demand': hourly_demand,
            'hourly_solar_cf': hourly_solar_cf,
            'hourly_wind_cf': hourly_wind_cf,
            'hourly_solar_gen': hourly_solar_gen,
            'hourly_wind_gen': hourly_wind_gen,
            'hourly_renewable_gen': hourly_renewable_gen,
            'hourly_dispatchable_need': hourly_dispatchable_need,
            'capacity_info': {
                'renewable_capacity': renewable_capacity,
                'storage_capacity': storage_capacity,
                'dispatchable_capacity': dispatchable_capacity,
                'tech_capacity': tech_capacity
            }
        }
    
    def create_comprehensive_hourly_plots(self, profiles):
        """Create detailed hourly plots of all profiles"""
        print("\n📊 Creating Comprehensive Hourly Profile Plots...")
        
        datetime_index = profiles['datetime_index']
        
        # Get month names for title
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        season_month_names = [month_names[int(m)-1] for m in profiles['season_months']]
        
        # Create a large figure with multiple subplots
        from datetime import datetime as dt
        timestamp = dt.now().strftime("%H:%M:%S")
        
        fig, axes = plt.subplots(3, 2, figsize=(20, 16))
        fig.suptitle(f'FACETS Hourly Profile Analysis - {self.region} {self.timeslice} | UPDATED {timestamp}\n'
                     f'{self.scenario}, {self.year} | {", ".join(season_month_names)} | Hours {"-".join(map(str, profiles["period_hours"]))} | {len(profiles["hour_indices"])} hours analyzed', 
                     fontsize=16, fontweight='bold')
        
        # Plot 1: Raw Demand Profile
        axes[0,0].plot(datetime_index, profiles['hourly_demand']/1000, 'b-', linewidth=1.5, alpha=0.8)
        axes[0,0].set_title('Hourly Electricity Demand', fontsize=14, fontweight='bold')
        axes[0,0].set_ylabel('Demand (GW)')
        axes[0,0].grid(True, alpha=0.3)
        axes[0,0].tick_params(axis='x', rotation=45)
        
        # Add statistics
        demand_stats = f"Min: {profiles['hourly_demand'].min()/1000:.1f} GW\nMax: {profiles['hourly_demand'].max()/1000:.1f} GW\nAvg: {profiles['hourly_demand'].mean()/1000:.1f} GW"
        axes[0,0].text(0.02, 0.98, demand_stats, transform=axes[0,0].transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        # Plot 2: Renewable Capacity Factors
        axes[0,1].plot(datetime_index, profiles['hourly_solar_cf'], 'gold', linewidth=1.5, alpha=0.8, label='Solar CF')
        axes[0,1].plot(datetime_index, profiles['hourly_wind_cf'], 'skyblue', linewidth=1.5, alpha=0.8, label='Wind CF')
        axes[0,1].set_title('Renewable Resource Capacity Factors', fontsize=14, fontweight='bold')
        axes[0,1].set_ylabel('Capacity Factor')
        axes[0,1].legend()
        axes[0,1].grid(True, alpha=0.3)
        axes[0,1].tick_params(axis='x', rotation=45)
        
        # Plot 3: Renewable Generation (MW)
        axes[1,0].plot(datetime_index, profiles['hourly_solar_gen']/1000, 'gold', linewidth=1.5, alpha=0.8, label='Solar Generation')
        axes[1,0].plot(datetime_index, profiles['hourly_wind_gen']/1000, 'skyblue', linewidth=1.5, alpha=0.8, label='Wind Generation')
        axes[1,0].plot(datetime_index, profiles['hourly_renewable_gen']/1000, 'green', linewidth=2, alpha=0.9, label='Total Renewables')
        axes[1,0].set_title('Renewable Generation (Scaled by FACETS Capacity)', fontsize=14, fontweight='bold')
        axes[1,0].set_ylabel('Generation (GW)')
        axes[1,0].legend()
        axes[1,0].grid(True, alpha=0.3)
        axes[1,0].tick_params(axis='x', rotation=45)
        
        # Plot 4: Demand vs Renewable Generation
        axes[1,1].plot(datetime_index, profiles['hourly_demand']/1000, 'b-', linewidth=2, alpha=0.8, label='Demand')
        axes[1,1].plot(datetime_index, profiles['hourly_renewable_gen']/1000, 'g-', linewidth=2, alpha=0.8, label='Renewable Generation')
        axes[1,1].fill_between(datetime_index, profiles['hourly_renewable_gen']/1000, profiles['hourly_demand']/1000,
                              where=(profiles['hourly_demand'] > profiles['hourly_renewable_gen']),
                              alpha=0.3, color='red', label='Dispatchable Need')
        axes[1,1].fill_between(datetime_index, profiles['hourly_renewable_gen']/1000, profiles['hourly_demand']/1000,
                              where=(profiles['hourly_demand'] <= profiles['hourly_renewable_gen']),
                              alpha=0.3, color='green', label='Renewable Surplus')
        axes[1,1].set_title('Supply-Demand Balance', fontsize=14, fontweight='bold')
        axes[1,1].set_ylabel('Power (GW)')
        axes[1,1].legend()
        axes[1,1].grid(True, alpha=0.3)
        axes[1,1].tick_params(axis='x', rotation=45)
        
        # Plot 5: Dispatchable Generation Requirements
        positive_dispatch = np.maximum(profiles['hourly_dispatchable_need'], 0)
        negative_dispatch = np.minimum(profiles['hourly_dispatchable_need'], 0)
        
        axes[2,0].fill_between(datetime_index, 0, positive_dispatch/1000, alpha=0.6, color='red', label='Dispatchable Need')
        axes[2,0].fill_between(datetime_index, 0, negative_dispatch/1000, alpha=0.6, color='green', label='Renewable Surplus')
        axes[2,0].axhline(y=profiles['capacity_info']['dispatchable_capacity'], color='orange', 
                         linestyle='--', linewidth=3, label=f'FACETS Dispatchable: {profiles["capacity_info"]["dispatchable_capacity"]:.1f} GW')
        axes[2,0].set_title('Dispatchable Generation Requirements', fontsize=14, fontweight='bold')
        axes[2,0].set_ylabel('Power (GW)')
        axes[2,0].legend()
        axes[2,0].grid(True, alpha=0.3)
        axes[2,0].tick_params(axis='x', rotation=45)
        
        # Plot 6: Key Statistics and Insights
        axes[2,1].axis('off')
        
        # Calculate key statistics
        peak_demand = profiles['hourly_demand'].max() / 1000
        min_demand = profiles['hourly_demand'].min() / 1000
        peak_renewable = profiles['hourly_renewable_gen'].max() / 1000
        min_renewable = profiles['hourly_renewable_gen'].min() / 1000
        peak_dispatchable = positive_dispatch.max() / 1000
        surplus_hours = (profiles['hourly_dispatchable_need'] < 0).sum()
        total_hours = len(profiles['hourly_dispatchable_need'])
        max_surplus = abs(negative_dispatch.min()) / 1000
        
        stats_text = f"""
📊 HOURLY PROFILE STATISTICS

DEMAND PATTERNS:
• Peak Demand: {peak_demand:.1f} GW
• Min Demand: {min_demand:.1f} GW  
• Demand Range: {peak_demand - min_demand:.1f} GW

RENEWABLE GENERATION:
• Peak RE Output: {peak_renewable:.1f} GW
• Min RE Output: {min_renewable:.1f} GW
• RE Variability: {peak_renewable - min_renewable:.1f} GW

OPERATIONAL CHALLENGES:
• Peak Dispatchable Need: {peak_dispatchable:.1f} GW
• FACETS Planned Capacity: {profiles['capacity_info']['dispatchable_capacity']:.1f} GW
• Capacity Shortfall: {peak_dispatchable - profiles['capacity_info']['dispatchable_capacity']:.1f} GW

SURPLUS MANAGEMENT:
• Hours with RE Surplus: {surplus_hours}/{total_hours} ({surplus_hours/total_hours*100:.1f}%)
• Max Surplus Power: {max_surplus:.1f} GW
• Storage Opportunity: {surplus_hours * max_surplus / 4:.0f} GWh

⚠️  FACETS underestimates dispatchable needs by {(peak_dispatchable / profiles['capacity_info']['dispatchable_capacity'] - 1) * 100:.0f}%
        """
        
        axes[2,1].text(0.05, 0.95, stats_text, transform=axes[2,1].transAxes, fontsize=11,
                       verticalalignment='top', fontfamily='monospace',
                       bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
        
        # Format x-axes for all plots with dates - force compact view
        for i in range(3):
            for j in range(2):
                if i < 2 or j == 0:  # Skip the statistics panel
                    # Set strict x-axis limits and simple formatting
                    axes[i,j].set_xlim(min(datetime_index), max(datetime_index))
                    axes[i,j].xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                    # Use fixed interval instead of trying to be smart about months
                    axes[i,j].xaxis.set_major_locator(mdates.DayLocator(interval=15))  # Every 15 days
                    axes[i,j].tick_params(axis='x', rotation=45)
                    # Force the axis to not expand beyond our data
                    axes[i,j].margins(x=0.01)
        
        plt.tight_layout()
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Save plot
        output_file = f'../outputs/plots/facets_hourly_profiles_{self.region}_{self.timeslice}.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"   ✅ Hourly profiles visualization saved: {output_file}")
        
        return output_file
    
    def run_profile_exploration(self):
        """Run complete hourly profile exploration"""
        print("🔍 FACETS Hourly Profile Explorer")
        print("="*60)
        
        # Load all profiles
        profiles = self.load_and_process_all_profiles()
        if not profiles:
            return None
        
        # Create comprehensive plots
        plot_file = self.create_comprehensive_hourly_plots(profiles)
        
        print(f"\n🎯 Profile exploration complete!")
        print(f"📊 Key insight: Hourly variability reveals massive operational challenges invisible to FACETS timeslice aggregation")
        
        return {
            'profiles': profiles,
            'plot_file': plot_file
        }

# Run the profile exploration
if __name__ == "__main__":
    explorer = FACETSHourlyProfileExplorer()
    results = explorer.run_profile_exploration()