#!/usr/bin/env python3
"""
Enhanced Calendar Heatmap Visualizer for VerveStacks
Creates professional, beautiful calendar heatmaps showing daily renewable energy coverage
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime, timedelta
import seaborn as sns
from pathlib import Path

class EnhancedCalendarHeatmapVisualizer:
    def __init__(self):
        # Professional color scheme
        self.colors = {
            'extreme_shortage': '#d62728',    # Dark red
            'shortage': '#ff7f0e',            # Orange
            'moderate': '#ffd700',            # Gold
            'adequate': '#2ca02c',            # Green
            'good': '#1f77b4',               # Blue
            'surplus': '#9467bd',            # Purple
            'extreme_surplus': '#8c564b'     # Brown
        }
        
    def load_daily_coverage(self, json_file_path):
        """Load daily coverage data from JSON file"""
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        return data
    
    def create_calendar_heatmap(self, daily_coverage_data, output_path=None):
        """Create a professional GitHub-style calendar heatmap"""
        
        iso_code = daily_coverage_data['iso']
        coverage_values = daily_coverage_data['daily_coverage']
        weather_year = daily_coverage_data.get('weather_year', 2013)
        
        # Set style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Create figure with better proportions
        fig, ax = plt.subplots(figsize=(20, 12))
        
        # Set up calendar grid (7 days x 53 weeks)
        weeks = 53
        days_per_week = 7
        
        # Create coverage matrix
        coverage_matrix = np.full((weeks, days_per_week), np.nan)
        
        # Fill in the coverage values
        for day_idx, coverage in enumerate(coverage_values):
            week = day_idx // 7
            day_of_week = day_idx % 7
            if week < weeks:
                coverage_matrix[week, day_of_week] = coverage
        
        # Create enhanced colormap with beautiful teal gradient
        colors_list = [
            '#ebedf0',      # No data (light gray)
            '#e0f2f1',      # Extreme shortage (very light teal)
            '#b2dfdb',      # Shortage (light teal)
            '#80cbc4',      # Moderate shortage (teal)
            '#4db6ac',      # Low coverage (medium teal)
            '#26a69a',      # Moderate coverage (teal)
            '#00897b',      # Adequate coverage (dark teal)
            '#00796b',      # Good coverage (darker teal)
            '#00695c',      # High coverage (very dark teal)
            '#004d40',      # Surplus (deep teal)
            '#00251a'       # Extreme surplus (darkest teal)
        ]
        
        # Create custom colormap
        cmap = plt.cm.colors.ListedColormap(colors_list)
        
        # Normalize coverage values for better color distribution
        normalized_values = np.copy(coverage_matrix)
        
        for i in range(weeks):
            for j in range(days_per_week):
                if not np.isnan(coverage_matrix[i, j]):
                    coverage = coverage_matrix[i, j]
                    if coverage < 50:
                        normalized_values[i, j] = 1      # Extreme shortage
                    elif coverage < 60:
                        normalized_values[i, j] = 2      # Shortage
                    elif coverage < 70:
                        normalized_values[i, j] = 3      # Moderate shortage
                    elif coverage < 80:
                        normalized_values[i, j] = 4      # Low coverage
                    elif coverage < 90:
                        normalized_values[i, j] = 5      # Moderate coverage
                    elif coverage < 100:
                        normalized_values[i, j] = 6      # Adequate coverage
                    elif coverage < 110:
                        normalized_values[i, j] = 7      # Good coverage
                    elif coverage < 120:
                        normalized_values[i, j] = 8      # High coverage
                    elif coverage < 130:
                        normalized_values[i, j] = 9      # Surplus
                    else:
                        normalized_values[i, j] = 10     # Extreme surplus
        
        # Create heatmap with perfect square cells
        im = ax.imshow(normalized_values, cmap=cmap, aspect='equal', interpolation='nearest')
        
        # Customize appearance with professional styling
        ax.set_xticks(range(7))
        ax.set_xticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], 
                          fontsize=10, fontweight='bold', rotation=45, ha='right')
        ax.set_yticks(range(0, weeks, 4))
        ax.set_yticklabels([f'Week {i+1}' for i in range(0, weeks, 4)], fontsize=10)
        
        # Add month labels with better positioning
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        month_positions = [0, 4, 9, 13, 17, 22, 26, 30, 35, 39, 43, 48]
        
        for month_idx, (month_name, week_pos) in enumerate(zip(month_names, month_positions)):
            if week_pos < weeks:
                ax.text(-0.8, week_pos, month_name, ha='right', va='center', 
                       fontweight='bold', fontsize=12, color='#2c3e50')
        
        # Enhanced title and labels
        ax.set_title(f'Renewable Energy Coverage Calendar - {iso_code} ({weather_year})', 
                    fontsize=20, fontweight='bold', pad=30, color='#2c3e50')
        ax.set_xlabel('Day of Week', fontsize=14, fontweight='bold', color='#34495e')
        ax.set_ylabel('Week of Year', fontsize=14, fontweight='bold', color='#34495e')
        
        # Enhanced legend with teal gradient colors and descriptions
        legend_elements = [
            patches.Patch(color='#ebedf0', label='No Data'),
            patches.Patch(color='#e0f2f1', label='Extreme Shortage (<50%)'),
            patches.Patch(color='#b2dfdb', label='Shortage (50-60%)'),
            patches.Patch(color='#80cbc4', label='Moderate Shortage (60-70%)'),
            patches.Patch(color='#4db6ac', label='Low Coverage (70-80%)'),
            patches.Patch(color='#26a69a', label='Moderate Coverage (80-90%)'),
            patches.Patch(color='#00897b', label='Adequate Coverage (90-100%)'),
            patches.Patch(color='#00796b', label='Good Coverage (100-110%)'),
            patches.Patch(color='#00695c', label='High Coverage (110-120%)'),
            patches.Patch(color='#004d40', label='Surplus (120-130%)'),
            patches.Patch(color='#00251a', label='Extreme Surplus (>130%)')
        ]
        
        # Better legend positioning - move it outside the chart area
        legend = ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.02, 0.5),
                          fontsize=9, frameon=True, fancybox=True, shadow=True)
        legend.get_frame().set_facecolor('#f8f9fa')
        legend.get_frame().set_edgecolor('#dee2e6')
        
        # Enhanced statistics with better formatting
        shortage_days = sum(1 for x in coverage_values if x < 70)
        adequate_days = sum(1 for x in coverage_values if 70 <= x < 110)
        surplus_days = sum(1 for x in coverage_values if x >= 110)
        extreme_shortage = sum(1 for x in coverage_values if x < 50)
        extreme_surplus = sum(1 for x in coverage_values if x > 130)
        
        # Create statistics box
        stats_text = f'📊 Coverage Statistics:\n'
        stats_text += f'🔴 Extreme Shortage: {extreme_shortage} days\n'
        stats_text += f'🟠 Shortage: {shortage_days} days\n'
        stats_text += f'🟢 Adequate: {adequate_days} days\n'
        stats_text += f'🔵 Surplus: {surplus_days} days\n'
        stats_text += f'🟣 Extreme Surplus: {extreme_surplus} days'
        
        # Position statistics box below the legend
        ax.text(0.98, 0.75, stats_text, transform=ax.transAxes, 
               fontsize=10, bbox=dict(boxstyle='round,pad=0.5', 
                                     facecolor='#f8f9fa', 
                                     edgecolor='#dee2e6',
                                     alpha=0.9),
               verticalalignment='top', horizontalalignment='right', fontfamily='monospace')
        
        # Add grid lines for better readability
        ax.grid(True, which='major', color='#dee2e6', linewidth=0.5, alpha=0.7)
        
        # Remove axis spines for cleaner look
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        # Adjust layout to prevent overlap
        plt.subplots_adjust(right=0.85, bottom=0.15)
        
        # Save with high quality
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"📅 Enhanced calendar heatmap saved to: {output_path}")
        else:
            plt.show()
        
        plt.close()
        
        return fig
    
    def create_monthly_summary_heatmap(self, daily_coverage_data, output_path=None):
        """Create an enhanced monthly summary heatmap"""
        
        iso_code = daily_coverage_data['iso']
        coverage_values = daily_coverage_data['daily_coverage']
        weather_year = daily_coverage_data.get('weather_year', 2013)
        
        # Set style
        plt.style.use('default')
        
        # Create figure
        fig, ax = plt.subplots(figsize=(16, 10))
        
        # Group by month with proper month boundaries
        monthly_data = []
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        
        # Use actual month lengths
        month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        current_day = 0
        for month, days_in_month in enumerate(month_lengths):
            month_coverage = coverage_values[current_day:current_day + days_in_month]
            avg_coverage = np.mean(month_coverage)
            monthly_data.append(avg_coverage)
            current_day += days_in_month
        
        # Reshape for 3x4 grid
        monthly_matrix = np.array(monthly_data).reshape(3, 4)
        
        # Create enhanced colormap
        monthly_cmap = plt.cm.RdYlBu_r  # Red (shortage) to Blue (surplus)
        
        # Create heatmap
        im = ax.imshow(monthly_matrix, cmap=monthly_cmap, aspect='auto', 
                      vmin=0, vmax=150)
        
        # Add enhanced text annotations
        for i in range(3):
            for j in range(4):
                month_idx = i * 4 + j
                if month_idx < 12:
                    value = monthly_matrix[i, j]
                    # Better color contrast for text
                    color = 'white' if value > 80 else 'black'
                    ax.text(j, i, f'{value:.1f}%', ha='center', va='center', 
                           color=color, fontweight='bold', fontsize=14,
                                                       bbox=dict(boxstyle='round,pad=0.3', 
                                     facecolor='white', 
                                     edgecolor='none',
                                     alpha=0.7))
        
        # Enhanced appearance
        ax.set_xticks(range(4))
        ax.set_xticklabels(['Q1 (Winter)', 'Q2 (Spring)', 'Q3 (Summer)', 'Q4 (Fall)'], 
                          fontsize=12, fontweight='bold')
        ax.set_yticks(range(3))
        ax.set_yticklabels(['Winter Months', 'Spring/Summer Months', 'Fall Months'], 
                          fontsize=12, fontweight='bold')
        
        # Add month labels with better positioning
        for month_idx, month_name in enumerate(month_names):
            row = month_idx // 4
            col = month_idx % 4
            ax.text(col, row + 0.3, month_name, ha='center', va='center', 
                   fontsize=10, fontweight='bold', color='#2c3e50')
        
        # Enhanced title and colorbar
        ax.set_title(f'Monthly Renewable Energy Coverage - {iso_code} ({weather_year})', 
                    fontsize=18, fontweight='bold', pad=25, color='#2c3e50')
        
        cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label('Coverage (%)', fontsize=14, fontweight='bold')
        cbar.ax.tick_params(labelsize=12)
        
        # Enhanced statistics
        annual_avg = np.mean(coverage_values)
        best_month = month_names[np.argmax(monthly_data)]
        worst_month = month_names[np.argmin(monthly_data)]
        best_value = np.max(monthly_data)
        worst_value = np.min(monthly_data)
        
        stats_text = f'📈 Annual Average: {annual_avg:.1f}%\n'
        stats_text += f'🏆 Best Month: {best_month} ({best_value:.1f}%)\n'
        stats_text += f'⚠️  Worst Month: {worst_month} ({worst_value:.1f}%)'
        
        # Position statistics box
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
               fontsize=12, bbox=dict(boxstyle='round,pad=0.5', 
                                     facecolor='#f8f9fa', 
                                     edgecolor='#dee2e6',
                                     alpha=0.9),
               verticalalignment='top', fontfamily='monospace')
        
        # Add grid for better readability
        ax.grid(True, which='major', color='#dee2e6', linewidth=0.5, alpha=0.7)
        
        # Remove axis spines
        for spine in ax.spines.values():
            spine.set_visible(False)
        
        plt.tight_layout()
        
        # Save with high quality
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"📊 Enhanced monthly heatmap saved to: {output_path}")
        else:
            plt.show()
        
        plt.close()
        
        return fig

def main():
    """Main function to demonstrate the enhanced calendar heatmap visualizer"""
    
    # Find available daily coverage JSON files
    output_dir = Path("2_ts_design/outputs")
    json_files = list(output_dir.glob("*/daily_coverage_*.json"))
    
    if not json_files:
        print("❌ No daily coverage JSON files found!")
        print("   Run the stress period analyzer first to generate daily coverage data.")
        return
    
    print(f"🎯 Found {len(json_files)} daily coverage files:")
    for json_file in json_files:
        print(f"   📁 {json_file}")
    
    # Create enhanced visualizer
    visualizer = EnhancedCalendarHeatmapVisualizer()
    
    # Process each file
    for json_file in json_files:
        print(f"\n📅 Processing {json_file.name}...")
        
        try:
            # Load data
            coverage_data = visualizer.load_daily_coverage(json_file)
            iso_code = coverage_data['iso']
            
            # Create output directory
            output_dir = json_file.parent
            calendar_output = output_dir / f"enhanced_calendar_heatmap_{iso_code}.png"
            monthly_output = output_dir / f"enhanced_monthly_heatmap_{iso_code}.png"
            
            # Generate enhanced visualizations
            print(f"   🎨 Creating enhanced calendar heatmap...")
            visualizer.create_calendar_heatmap(coverage_data, str(calendar_output))
            
            print(f"   📊 Creating enhanced monthly summary...")
            visualizer.create_monthly_summary_heatmap(coverage_data, str(monthly_output))
            
            print(f"   ✅ Completed {iso_code}")
            
        except Exception as e:
            print(f"   ❌ Error processing {json_file.name}: {e}")
    
    print(f"\n🎉 All enhanced visualizations completed!")
    print(f"   Check the output directories for high-quality PNG files.")

if __name__ == "__main__":
    main()
