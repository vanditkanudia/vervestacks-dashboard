#!/usr/bin/env python3
"""
🎯 FACETS Scenario Selector for GPI MISO Analysis
=================================================

This script analyzes all 108 scenarios across MISO regions to identify
the most contrasting and interesting scenarios for hourly operational analysis.

Focus: SMR, Gas CCS, Solar, Wind, Storage penetration and hourly challenges

Author: VerveStacks AI Assistant
Date: 2024
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os
warnings.filterwarnings('ignore')

# Try to import seaborn, use fallback if not available
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
    print("⚠️  Seaborn not available, using matplotlib defaults")

class ScenarioSelector:
    """🔍 Intelligent scenario selection for maximum analytical insight"""
    
    def __init__(self, data_version=None):
        # Use versioned data folder if specified
        if data_version:
            self.data_path = Path("../data/model_outputs") / data_version
        else:
            self.data_path = Path("../data/model_outputs")
        
        self.gen_file = "VSInput_generation by tech, region, and timeslice.csv"
        self.cap_file = "VSInput_capacity by tech and region.csv"
        self.data_version = data_version
        
        # MISO region mapping
        self.miso_regions = {
            'MISO_North': ['p058', 'p060', 'p061', 'p062'],
            'MISO_South': ['p066', 'p085', 'p086', 'p087'], 
            'MISO_Central': ['p063', 'p064', 'p065', 'p067']
        }
        
        # Technology categories of interest (updated based on actual data)
        self.tech_categories = {
            'Solar': ['Solar PV', 'RTPV', 'Solar Thermal'],
            'Wind': ['Onshore Wind', 'Offshore Wind'],
            'Storage': ['Storage'],
            'SMR': ['Nuclear'],  # SMR will be identified by sub_tech containing 'SMR'
            'Gas_CCS': ['Combined Cycle', 'Combustion Turbine'],  # CCS will be identified by sub_tech containing 'CCS'
            'Baseload': ['Nuclear', 'Coal Steam', 'Combined Cycle', 'Combustion Turbine'],
            'Hydro': ['Hydro'],
            'Other': ['Biomass', 'Geothermal', 'Fossil Waste', 'O/G Steam', 'IGCC']
        }
        
        self.results = {}
        
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
        
    def load_and_process_data(self):
        """📊 Load and aggregate generation/capacity data by scenario and region group"""
        print("🔄 Loading FACETS data...")
        
        # Load generation data
        gen_df = pd.read_csv(self.data_path / self.gen_file)
        cap_df = pd.read_csv(self.data_path / self.cap_file)
        
        # Filter for 2045 only
        gen_df = gen_df[gen_df['year'] == 2045]
        cap_df = cap_df[cap_df['year'] == 2045]
        
        print(f"📈 Generation data: {len(gen_df):,} rows, {len(gen_df['scen'].unique())} scenarios")
        print(f"⚡ Capacity data: {len(cap_df):,} rows, {len(cap_df['scen'].unique())} scenarios")
        
        # Process generation data
        self.gen_summary = self._aggregate_by_tech_category(gen_df, 'generation')
        self.cap_summary = self._aggregate_by_tech_category(cap_df, 'capacity')
        
        return self
    
    def _aggregate_by_tech_category(self, df, data_type):
        """🔧 Aggregate data by technology categories and MISO region groups"""
        results = []
        
        for scenario in df['scen'].unique():
            scen_data = df[df['scen'] == scenario]
            
            for miso_group, regions in self.miso_regions.items():
                group_data = scen_data[scen_data['region'].isin(regions)]
                
                row = {
                    'scenario': scenario,
                    'miso_group': miso_group,
                    'data_type': data_type
                }
                
                # Aggregate by technology category
                for tech_cat, techs in self.tech_categories.items():
                    if tech_cat == 'SMR':
                        # SMR is in sub_tech field
                        value = group_data[group_data['sub_tech'].str.contains('SMR', na=False)]['value'].sum()
                    elif tech_cat == 'Gas_CCS':
                        # CCS is in sub_tech field  
                        value = group_data[group_data['sub_tech'].str.contains('CCS', na=False)]['value'].sum()
                    else:
                        # Regular tech field matching
                        if data_type == 'generation':
                            # Sum TWh across all timeslices
                            value = group_data[group_data['tech'].isin(techs)]['value'].sum()
                        else:
                            # Sum GW capacity
                            value = group_data[group_data['tech'].isin(techs)]['value'].sum()
                    
                    row[tech_cat] = value
                
                # Calculate total for percentages
                row['Total'] = sum(row[cat] for cat in self.tech_categories.keys())
                
                results.append(row)
        
        return pd.DataFrame(results)
    
    def analyze_scenario_diversity(self):
        """🎯 Identify scenarios with maximum diversity and interesting contrasts"""
        print("\n🔍 Analyzing scenario diversity...")
        
        # Calculate technology penetration percentages
        gen_pct = self.gen_summary.copy()
        for tech_cat in self.tech_categories.keys():
            gen_pct[f'{tech_cat}_pct'] = (gen_pct[tech_cat] / gen_pct['Total'] * 100).round(1)
        
        # Focus on key metrics for scenario selection
        key_metrics = ['Solar_pct', 'Wind_pct', 'SMR_pct', 'Gas_CCS_pct', 'Storage_pct']
        
        # Calculate scenario diversity score
        diversity_scores = []
        
        for scenario in gen_pct['scenario'].unique():
            scen_data = gen_pct[gen_pct['scenario'] == scenario]
            
            # Calculate variance across MISO groups for each tech
            tech_variances = []
            for metric in key_metrics:
                variance = scen_data[metric].var()
                tech_variances.append(variance if not pd.isna(variance) else 0)
            
            # Calculate extreme values (high/low penetration)
            extreme_scores = []
            for metric in key_metrics:
                max_val = scen_data[metric].max()
                min_val = scen_data[metric].min()
                extreme_scores.append(max_val - min_val)  # Range
            
            # Fixed: Use total generation instead of max regional percentage
            smr_total = scen_data['SMR'].sum()
            gasccs_total = scen_data['Gas_CCS'].sum()
            renewable_total = scen_data['Solar'].sum() + scen_data['Wind'].sum()
            storage_total = scen_data['Storage'].sum()
            total_generation = scen_data['Total'].sum()
            
            # Calculate penetration as percentage of total MISO generation
            smr_penetration = (smr_total / total_generation * 100) if total_generation > 0 else 0
            gasccs_penetration = (gasccs_total / total_generation * 100) if total_generation > 0 else 0
            renewable_penetration = (renewable_total / total_generation * 100) if total_generation > 0 else 0
            storage_penetration = (storage_total / total_generation * 100) if total_generation > 0 else 0
            
            diversity_scores.append({
                'scenario': scenario,
                'tech_variance': np.mean(tech_variances),
                'extreme_range': np.mean(extreme_scores),
                'smr_penetration': smr_penetration,
                'gasccs_penetration': gasccs_penetration,
                'renewable_penetration': renewable_penetration,
                'storage_penetration': storage_penetration,
                'renewable_total_twh': renewable_total,
                'smr_total_twh': smr_total,
                'gasccs_total_twh': gasccs_total
            })
        
        self.diversity_df = pd.DataFrame(diversity_scores)
        
        # Debug: Print some stats
        print(f"📊 Diversity metrics summary:")
        print(f"   SMR penetration: {self.diversity_df['smr_penetration'].describe()}")
        print(f"   Gas CCS penetration: {self.diversity_df['gasccs_penetration'].describe()}")
        print(f"   Renewable penetration: {self.diversity_df['renewable_penetration'].describe()}")
        print(f"   Renewable total (TWh): {self.diversity_df['renewable_total_twh'].describe()}")
        
        return self
    
    def select_contrasting_scenarios(self, n_scenarios=10):
        """🎪 Select the most contrasting scenarios using multiple criteria"""
        print(f"\n🎯 Selecting {n_scenarios} most contrasting scenarios...")
        
        selected_scenarios = []
        selection_reasons = []
        
        # 1. High SMR penetration scenarios
        high_smr = self.diversity_df.nlargest(2, 'smr_penetration')
        selected_scenarios.extend(high_smr['scenario'].tolist())
        selection_reasons.extend(['High SMR penetration (max)', 'High SMR penetration (2nd)'])
        
        # 2. High Gas CCS scenarios
        high_gasccs = self.diversity_df[~self.diversity_df['scenario'].isin(selected_scenarios)].nlargest(2, 'gasccs_penetration')
        selected_scenarios.extend(high_gasccs['scenario'].tolist())
        selection_reasons.extend(['High Gas CCS penetration (max)', 'High Gas CCS penetration (2nd)'])
        
        # 3. High renewable scenarios (now correctly using total penetration)
        high_renewable = self.diversity_df[~self.diversity_df['scenario'].isin(selected_scenarios)].nlargest(2, 'renewable_penetration')
        selected_scenarios.extend(high_renewable['scenario'].tolist())
        selection_reasons.extend(['High renewable penetration (max)', 'High renewable penetration (2nd)'])
        
        # 4. Low renewable scenarios (for contrast)
        low_renewable = self.diversity_df[~self.diversity_df['scenario'].isin(selected_scenarios)].nsmallest(1, 'renewable_penetration')
        if not low_renewable.empty:
            selected_scenarios.extend(low_renewable['scenario'].tolist())
            selection_reasons.extend(['Low renewable penetration (contrast)'])
        
        # 5. High storage scenarios
        high_storage = self.diversity_df[~self.diversity_df['scenario'].isin(selected_scenarios)].nlargest(1, 'storage_penetration')
        if not high_storage.empty:
            selected_scenarios.extend(high_storage['scenario'].tolist())
            selection_reasons.extend(['High storage penetration'])
        
        # 6. High diversity/variance scenarios
        high_diversity = self.diversity_df[~self.diversity_df['scenario'].isin(selected_scenarios)].nlargest(1, 'tech_variance')
        if not high_diversity.empty:
            selected_scenarios.extend(high_diversity['scenario'].tolist())
            selection_reasons.extend(['High tech diversity across regions'])
        
        # 7. Fill remaining with extreme range scenarios
        remaining = n_scenarios - len(selected_scenarios)
        if remaining > 0:
            extreme_range = self.diversity_df[~self.diversity_df['scenario'].isin(selected_scenarios)].nlargest(remaining, 'extreme_range')
            selected_scenarios.extend(extreme_range['scenario'].tolist())
            selection_reasons.extend([f'Extreme tech range (rank {i+1})' for i in range(remaining)])
        
        # Create final selection DataFrame
        self.selected_scenarios = pd.DataFrame({
            'scenario': selected_scenarios[:n_scenarios],
            'selection_reason': selection_reasons[:n_scenarios]
        })
        
        # Add scenario details
        scenario_details = []
        for scenario in self.selected_scenarios['scenario']:
            details = self._decode_scenario(scenario)
            scenario_details.append(details)
        
        self.selected_scenarios['scenario_details'] = scenario_details
        
        print(f"✅ Selected {len(self.selected_scenarios)} scenarios!")
        return self
    
    def _decode_scenario(self, scenario):
        """🔍 Decode scenario components into human-readable format"""
        parts = scenario.split('.')
        
        decode_map = {
            're-L': 'Low RE costs', 're-H': 'High RE costs',
            'gp-L': 'Low gas prices', 'gp-I': 'Intermediate gas prices',
            'Cp-00': 'No carbon policy', 'Cp-95': '95% CO2 reduction', 'Cp-98': '98% CO2 reduction',
            'ncs-L': 'Low NG CCS costs', 'ncs-I': 'Intermediate NG CCS costs', 'ncs-H': 'High NG CCS costs',
            'smr-L': 'Low SMR costs', 'smr-I': 'Intermediate SMR costs', 'smr-H': 'High SMR costs'
        }
        
        decoded = []
        for part in parts:
            if part in decode_map:
                decoded.append(decode_map[part])
            else:
                decoded.append(part)
        
        return ' | '.join(decoded)
    
    def create_scenario_analysis_charts(self):
        """📊 Create compelling visualizations of scenario diversity"""
        print("\n📊 Creating scenario analysis visualizations...")
        
        # Set up the plotting style
        plt.style.use('default')  # Use default instead of seaborn-v0_8
        if HAS_SEABORN:
            sns.set_palette("husl")
        
        # Create figure with subplots
        fig = plt.figure(figsize=(20, 16))
        
        # 1. Technology penetration heatmap for selected scenarios
        ax1 = plt.subplot(3, 2, 1)
        self._plot_tech_penetration_heatmap(ax1)
        
        # 2. Scenario diversity scores
        ax2 = plt.subplot(3, 2, 2)
        self._plot_diversity_scores(ax2)
        
        # 3. SMR vs Gas CCS scatter
        ax3 = plt.subplot(3, 2, 3)
        self._plot_smr_vs_gasccs(ax3)
        
        # 4. Renewable penetration distribution
        ax4 = plt.subplot(3, 2, 4)
        self._plot_renewable_distribution(ax4)
        
        # 5. Selected scenarios summary
        ax5 = plt.subplot(3, 1, 3)
        self._plot_selected_scenarios_summary(ax5)
        
        plt.tight_layout()
        
        # Add logo watermark
        self._add_logo_watermark(fig)
        
        # Add version suffix to chart filename if specified
        version_suffix = f"_{self.data_version}" if self.data_version else ""
        chart_path = f'scenario_analysis_dashboard{version_suffix}.png'
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        print(f"💾 Saved: {chart_path}")
        
        return self
    
    def _plot_tech_penetration_heatmap(self, ax):
        """📈 Heatmap of technology penetration across selected scenarios"""
        # Get generation percentages for selected scenarios
        selected_gen = self.gen_summary[self.gen_summary['scenario'].isin(self.selected_scenarios['scenario'])]
        
        # Calculate percentages
        for tech_cat in self.tech_categories.keys():
            selected_gen[f'{tech_cat}_pct'] = (selected_gen[tech_cat] / selected_gen['Total'] * 100).round(1)
        
        # Pivot for heatmap
        tech_cols = [f'{cat}_pct' for cat in ['Solar', 'Wind', 'SMR', 'Gas_CCS', 'Storage', 'Baseload']]
        heatmap_data = selected_gen.groupby('scenario')[tech_cols].mean()
        
        # Create heatmap
        if HAS_SEABORN:
            sns.heatmap(heatmap_data.T, annot=True, fmt='.1f', cmap='viridis', ax=ax, cbar_kws={'label': 'Generation %'})
        else:
            # Fallback using matplotlib imshow
            im = ax.imshow(heatmap_data.T.values, cmap='viridis', aspect='auto')
            ax.set_xticks(range(len(heatmap_data.index)))
            ax.set_xticklabels([s[:15] + '...' for s in heatmap_data.index], rotation=45, ha='right')
            ax.set_yticks(range(len(heatmap_data.columns)))
            ax.set_yticklabels([col.replace('_pct', '') for col in heatmap_data.columns])
            plt.colorbar(im, ax=ax, label='Generation %')
        ax.set_title('🎯 Technology Penetration Across Selected Scenarios', fontsize=14, fontweight='bold')
        ax.set_xlabel('Scenarios')
        ax.set_ylabel('Technology Categories')
        
    def _plot_diversity_scores(self, ax):
        """📊 Bar chart of diversity scores"""
        top_diverse = self.diversity_df.nlargest(15, 'tech_variance')
        
        bars = ax.bar(range(len(top_diverse)), top_diverse['tech_variance'], 
                     color=['red' if s in self.selected_scenarios['scenario'].values else 'lightblue' for s in top_diverse['scenario']])
        
        ax.set_title('🌟 Technology Diversity Scores (Selected in Red)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Scenario Rank')
        ax.set_ylabel('Tech Variance Score')
        ax.set_xticks(range(0, len(top_diverse), 2))
        ax.set_xticklabels([f'{i+1}' for i in range(0, len(top_diverse), 2)])
        
    def _plot_smr_vs_gasccs(self, ax):
        """⚡ Scatter plot of SMR vs Gas CCS penetration"""
        scenario_data = self.diversity_df.copy()
        
        # Color by selection status
        colors = ['red' if s in self.selected_scenarios['scenario'].values else 'lightblue' for s in scenario_data['scenario']]
        
        scatter = ax.scatter(scenario_data['smr_penetration'], scenario_data['gasccs_penetration'], 
                           c=colors, alpha=0.7, s=60)
        
        ax.set_title('⚡ SMR vs Gas CCS Penetration (Selected in Red)', fontsize=14, fontweight='bold')
        ax.set_xlabel('SMR Penetration (%)')
        ax.set_ylabel('Gas CCS Penetration (%)')
        ax.grid(True, alpha=0.3)
        
    def _plot_renewable_distribution(self, ax):
        """🌱 Distribution of renewable penetration"""
        renewable_pen = self.diversity_df['renewable_penetration'].dropna()
        
        if len(renewable_pen) > 0:
            ax.hist(renewable_pen, bins=20, alpha=0.7, color='green', edgecolor='black')
        else:
            ax.text(0.5, 0.5, 'No renewable data available', ha='center', va='center', transform=ax.transAxes)
        
        # Mark selected scenarios
        selected_renewable = self.diversity_df[self.diversity_df['scenario'].isin(self.selected_scenarios['scenario'])]['renewable_penetration'].dropna()
        for val in selected_renewable:
            if not pd.isna(val):
                ax.axvline(val, color='red', linestyle='--', alpha=0.8)
        
        ax.set_title('🌱 Renewable Penetration Distribution', fontsize=14, fontweight='bold')
        ax.set_xlabel('Renewable Penetration (%)')
        ax.set_ylabel('Number of Scenarios')
        
    def _plot_selected_scenarios_summary(self, ax):
        """📋 Summary table of selected scenarios"""
        # Create summary data
        summary_data = []
        for _, row in self.selected_scenarios.iterrows():
            scenario = row['scenario']
            reason = row['selection_reason']
            
            # Get tech penetration for this scenario
            scen_data = self.gen_summary[self.gen_summary['scenario'] == scenario]
            scen_data_pct = scen_data.copy()
            for tech_cat in self.tech_categories.keys():
                scen_data_pct[f'{tech_cat}_pct'] = (scen_data_pct[tech_cat] / scen_data_pct['Total'] * 100).round(1)
            
            # Get penetration values from diversity_df instead
            diversity_row = self.diversity_df[self.diversity_df['scenario'] == scenario].iloc[0]
            renewable_pct = diversity_row['renewable_penetration']
            smr_pct = diversity_row['smr_penetration']
            gasccs_pct = diversity_row['gasccs_penetration']
            storage_pct = diversity_row['storage_penetration']
            
            summary_data.append([
                scenario[:20] + '...' if len(scenario) > 20 else scenario,
                reason[:30] + '...' if len(reason) > 30 else reason,
                f'{renewable_pct:.1f}%',
                f'{smr_pct:.1f}%',
                f'{gasccs_pct:.1f}%',
                f'{storage_pct:.1f}%'
            ])
        
        # Create table
        table = ax.table(cellText=summary_data,
                        colLabels=['Scenario', 'Selection Reason', 'Renewable%', 'SMR%', 'Gas CCS%', 'Storage%'],
                        cellLoc='center',
                        loc='center')
        
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)
        
        # Style the table
        for i in range(len(summary_data) + 1):
            for j in range(len(summary_data[0])):
                cell = table[(i, j)]
                if i == 0:  # Header
                    cell.set_facecolor('#4CAF50')
                    cell.set_text_props(weight='bold', color='white')
                else:
                    cell.set_facecolor('#f0f0f0' if i % 2 == 0 else 'white')
        
        ax.set_title('🎯 Selected Scenarios for GPI MISO Analysis', fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
    
    def save_results(self):
        """💾 Save analysis results"""
        print("\n💾 Saving analysis results...")
        
        # Import Excel manager for branded Excel output
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent.parent.parent))
        from excel_manager import ExcelManager
        
        # Use ExcelManager with default branding (FACETS tagline available in LogoManager)
        excel_manager = ExcelManager()
        
        # Add version suffix to filenames if specified
        version_suffix = f"_{self.data_version}" if self.data_version else ""
        
        # Save selected scenarios as Excel
        try:
            excel_path = f'selected_scenarios_for_gpi{version_suffix}.xlsx'
            with excel_manager.workbook(excel_path, create_new=True) as wb:
                ws = wb.sheets[0]
                ws.name = "Selected Scenarios"
                
                # Write data starting from row 3 (branding in row 1)
                start_cell = "A3"
                ws.range(start_cell).value = [self.selected_scenarios.columns.tolist()] + self.selected_scenarios.values.tolist()
                
                # Apply professional formatting
                data_shape = (len(self.selected_scenarios) + 1, len(self.selected_scenarios.columns))
                excel_manager.format_energy_sector_table(
                    worksheet=ws,
                    start_cell=start_cell,
                    data_shape=data_shape,
                    dataframe=self.selected_scenarios,
                    add_branding=True
                )
                ws.autofit()
            
            print(f"📊 Saved: {excel_path}")
        except Exception as e:
            print(f"⚠️  Excel save failed, falling back to CSV: {e}")
            csv_path = f'selected_scenarios_for_gpi{version_suffix}.csv'
            self.selected_scenarios.to_csv(csv_path, index=False)
            print(f"📄 Saved: {csv_path}")
        
        # Save detailed tech penetration for selected scenarios as Excel
        selected_gen = self.gen_summary[self.gen_summary['scenario'].isin(self.selected_scenarios['scenario'])]
        
        # Add percentages
        for tech_cat in self.tech_categories.keys():
            selected_gen[f'{tech_cat}_pct'] = (selected_gen[tech_cat] / selected_gen['Total'] * 100).round(1)
        
        try:
            excel_path = f'selected_scenarios_tech_details{version_suffix}.xlsx'
            with excel_manager.workbook(excel_path, create_new=True) as wb:
                ws = wb.sheets[0]
                ws.name = "Technology Details"
                
                # Write data starting from row 3 (branding in row 1)
                start_cell = "A3"
                ws.range(start_cell).value = [selected_gen.columns.tolist()] + selected_gen.values.tolist()
                
                # Apply professional formatting
                data_shape = (len(selected_gen) + 1, len(selected_gen.columns))
                excel_manager.format_energy_sector_table(
                    worksheet=ws,
                    start_cell=start_cell,
                    data_shape=data_shape,
                    dataframe=selected_gen,
                    add_branding=True
                )
                ws.autofit()
            
            print(f"📊 Saved: {excel_path}")
        except Exception as e:
            print(f"⚠️  Excel save failed, falling back to CSV: {e}")
            csv_path = f'selected_scenarios_tech_details{version_suffix}.csv'
            selected_gen.to_csv(csv_path, index=False)
            print(f"📄 Saved: {csv_path}")
        
        # Create summary report
        report_path = f'scenario_selection_report{version_suffix}.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 🎯 GPI MISO Scenario Selection Report\n\n")
            f.write("## 📊 Analysis Summary\n")
            f.write(f"- **Total scenarios analyzed**: {len(self.diversity_df)}\n")
            f.write(f"- **Selected scenarios**: {len(self.selected_scenarios)}\n")
            f.write(f"- **MISO region groups**: {len(self.miso_regions)}\n\n")
            
            f.write("## 🎪 Selected Scenarios\n\n")
            for _, row in self.selected_scenarios.iterrows():
                f.write(f"### `{row['scenario']}`\n")
                f.write(f"**Selection Reason**: {row['selection_reason']}\n\n")
                f.write(f"**Details**: {row['scenario_details']}\n\n")
                
        print(f"📄 Saved: {report_path}")
        
        return self
    
    def print_final_summary(self):
        """🎉 Print final summary for the user"""
        print("\n" + "="*80)
        print("🎉 SCENARIO SELECTION COMPLETE!")
        print("="*80)
        
        print(f"\n🎯 **Selected {len(self.selected_scenarios)} scenarios for GPI MISO analysis:**\n")
        
        for i, (_, row) in enumerate(self.selected_scenarios.iterrows(), 1):
            print(f"{i:2d}. `{row['scenario']}`")
            print(f"    💡 {row['selection_reason']}")
            print(f"    📋 {row['scenario_details']}\n")
        
        print("🚀 **Ready to run facets_hourly_simulator.py with these scenarios!**")
        print("\n📁 **Files created:**")
        print("   📄 selected_scenarios_for_gpi.csv")
        print("   📄 selected_scenarios_tech_details.csv") 
        print("   📊 scenario_analysis_dashboard.png")
        print("   📋 scenario_selection_report.md")
        
        return self

def main():
    """🚀 Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FACETS Scenario Selector for GPI MISO Analysis')
    parser.add_argument('--data_version', type=str, default=None,
                       help='Data version subfolder (e.g., "04Aug25", "25Oct25")')
    
    args = parser.parse_args()
    
    print("🎯 FACETS Scenario Selector for GPI MISO Analysis")
    if args.data_version:
        print(f"📁 Using data version: {args.data_version}")
    print("=" * 60)
    
    selector = ScenarioSelector(data_version=args.data_version)
    
    # Run the full analysis pipeline
    (selector
     .load_and_process_data()
     .analyze_scenario_diversity()
     .select_contrasting_scenarios(n_scenarios=10)
     .create_scenario_analysis_charts()
     .save_results()
     .print_final_summary())

if __name__ == "__main__":
    main()
