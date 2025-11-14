import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict, Tuple
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.axis import DateAxis
import warnings
from logo_manager import logo_manager
warnings.filterwarnings('ignore')

class REDemandAnalyzer:
    """
    Renewable Energy vs Demand Analysis Tool
    Identifies extreme mismatch periods and optimal contiguous modeling periods
    """
    
    def __init__(self, excel_file_path: str):
        """Load and process the Excel data"""
        self.excel_file = excel_file_path
        self.demand_data = None
        self.supply_data = None
        self.hourly_data = None
        self.daily_stats = None
        self.load_data()
        
    def load_data(self):
        """Load data from Excel file"""
        print("Loading data from Excel file...")
        
        # Load both sheets
        self.demand_data = pd.read_excel(self.excel_file, sheet_name='Hourly_Demand_Data')
        self.supply_data = pd.read_excel(self.excel_file, sheet_name='Hourly_resource_shapes')
        
        print(f"Loaded {len(self.demand_data)} demand records")
        print(f"Loaded {len(self.supply_data)} supply records")
        
        # Process the combined dataset
        self.process_hourly_data()
        self.calculate_daily_stats()
        
    def process_hourly_data(self):
        """Process hourly data to calculate supply-demand metrics"""
        print("Processing hourly supply-demand metrics...")
        
        # Merge datasets
        hourly = []
        
        for i in range(len(self.demand_data)):
            demand_row = self.demand_data.iloc[i]
            supply_row = self.supply_data.iloc[i]
            
            total_demand = demand_row['Total load']
            solar_mw = supply_row.get('solar sup', 0) or 0
            wind_mw = supply_row.get('wind sup', 0) or 0
            total_re = solar_mw + wind_mw
            
            coverage = (total_re / total_demand) * 100 if total_demand > 0 else 0
            balance = total_re - total_demand
            
            hourly.append({
                'month': demand_row['month'],
                'day': demand_row['day'], 
                'hour': demand_row['hour'],
                'total_demand': total_demand,
                'solar_mw': solar_mw,
                'wind_mw': wind_mw,
                'total_re': total_re,
                'coverage_pct': coverage,
                'balance_mw': balance,
                'is_surplus': balance > 0,
                'is_extreme_scarcity': coverage < 5.0,
                'date_key': f"{demand_row['month']}-{demand_row['day']}",
                'date_hour': f"{demand_row['month']}/{demand_row['day']} {demand_row['hour']}:00"
            })
            
        self.hourly_data = pd.DataFrame(hourly)
        print(f"Processed {len(self.hourly_data)} hourly records")
        
    def calculate_daily_stats(self):
        """Calculate daily statistics for period selection"""
        print("Calculating daily statistics...")
        
        daily_groups = self.hourly_data.groupby('date_key')
        daily_stats = []
        
        for date_key, group in daily_groups:
            month, day = map(int, date_key.split('-'))
            
            stats = {
                'month': month,
                'day': day,
                'date_key': date_key,
                'min_coverage': group['coverage_pct'].min(),
                'max_coverage': group['coverage_pct'].max(),
                'avg_coverage': group['coverage_pct'].mean(),
                'coverage_range': group['coverage_pct'].max() - group['coverage_pct'].min(),
                'min_balance': group['balance_mw'].min(),
                'max_balance': group['balance_mw'].max(),
                'balance_range': group['balance_mw'].max() - group['balance_mw'].min(),
                'surplus_hours': group['is_surplus'].sum(),
                'extreme_scarcity_hours': group['is_extreme_scarcity'].sum(),
                'peak_demand': group['total_demand'].max(),
                'min_demand': group['total_demand'].min(),
                'demand_range': group['total_demand'].max() - group['total_demand'].min(),
                'total_re_generation': group['total_re'].sum(),
                'peak_re_generation': group['total_re'].max()
            }
            daily_stats.append(stats)
            
        self.daily_stats = pd.DataFrame(daily_stats)
        print(f"Calculated statistics for {len(self.daily_stats)} days")
        
    def analyze_extremes(self):
        """Analyze extreme abundance and scarcity periods"""
        print("\\n=== EXTREME PERIOD ANALYSIS ===")
        
        # Overall statistics
        avg_demand = self.hourly_data['total_demand'].mean()
        avg_re_supply = self.hourly_data['total_re'].mean()
        avg_coverage = self.hourly_data['coverage_pct'].mean()
        max_re_supply = self.hourly_data['total_re'].max()
        
        print(f"\\nOverall Statistics (at 50% of peak installed capacity):")
        print(f"Average demand: {avg_demand:,.0f} MW")
        print(f"Average RE supply: {avg_re_supply:,.0f} MW ({avg_re_supply/avg_demand*100:.1f}% of avg demand)")
        print(f"Maximum RE supply: {max_re_supply:,.0f} MW")
        print(f"Average coverage: {avg_coverage:.1f}% of demand met by renewables")
        
        # Surplus hours
        surplus_hours = self.hourly_data[self.hourly_data['is_surplus']]
        print(f"\\nSurplus hours: {len(surplus_hours)} ({len(surplus_hours)/len(self.hourly_data)*100:.1f}%)")
        
        # Top abundance periods
        print("\\n=== TOP 15 RENEWABLE ABUNDANCE PERIODS ===")
        top_abundance = self.hourly_data.nlargest(15, 'coverage_pct')
        for i, (_, row) in enumerate(top_abundance.iterrows(), 1):
            status = "SURPLUS" if row['is_surplus'] else "shortfall"
            print(f"{i:2d}. {row['date_hour']} - {row['coverage_pct']:5.1f}% coverage "
                  f"({row['total_re']:5.0f} MW RE vs {row['total_demand']:5.0f} MW demand) - {status}")
        
        # Top scarcity periods  
        print("\\n=== TOP 15 RENEWABLE SCARCITY PERIODS ===")
        top_scarcity = self.hourly_data.nsmallest(15, 'coverage_pct')
        for i, (_, row) in enumerate(top_scarcity.iterrows(), 1):
            print(f"{i:2d}. {row['date_hour']} - {row['coverage_pct']:5.1f}% coverage "
                  f"({row['total_re']:5.0f} MW RE vs {row['total_demand']:5.0f} MW demand)")
        
        # Monthly patterns
        print("\\n=== MONTHLY RE COVERAGE PATTERNS ===")
        monthly_stats = self.hourly_data.groupby('month').agg({
            'coverage_pct': ['mean', 'min', 'max'],
            'is_surplus': 'sum'
        }).round(1)
        
        monthly_stats.columns = ['avg_coverage', 'min_coverage', 'max_coverage', 'surplus_hours']
        
        for month in range(1, 13):
            if month in monthly_stats.index:
                stats = monthly_stats.loc[month]
                print(f"Month {month:2d}: Avg {stats['avg_coverage']:5.1f}% coverage, "
                      f"Range {stats['min_coverage']:5.1f}%-{stats['max_coverage']:5.1f}%, "
                      f"Surplus hours: {stats['surplus_hours']:2.0f}")
                      
        return {
            'top_abundance': top_abundance,
            'top_scarcity': top_scarcity,
            'monthly_stats': monthly_stats
        }
    
    def calculate_day_scores(self):
        """Calculate representativeness scores for each day"""
        print("\\nCalculating day representativeness scores...")
        
        # Normalize metrics for scoring
        max_coverage_range = self.daily_stats['coverage_range'].max()
        max_balance_range = self.daily_stats['balance_range'].max()  
        max_surplus_hours = self.daily_stats['surplus_hours'].max()
        max_scarcity_hours = self.daily_stats['extreme_scarcity_hours'].max()
        max_peak_demand = self.daily_stats['peak_demand'].max()
        min_min_coverage = self.daily_stats['min_coverage'].min()
        max_max_coverage = self.daily_stats['max_coverage'].max()
        
        def calculate_score(row):
            # Score components (0-1 scale, higher = more representative)
            variability_score = row['coverage_range'] / max_coverage_range if max_coverage_range > 0 else 0
            extreme_high_score = row['max_coverage'] / max_max_coverage if max_max_coverage > 0 else 0
            extreme_low_score = (min_min_coverage / row['min_coverage']) if row['min_coverage'] > 0 else 1
            surplus_score = row['surplus_hours'] / max_surplus_hours if max_surplus_hours > 0 else 0
            scarcity_score = row['extreme_scarcity_hours'] / max_scarcity_hours if max_scarcity_hours > 0 else 0
            demand_score = row['peak_demand'] / max_peak_demand if max_peak_demand > 0 else 0
            
            # Weighted composite score
            composite_score = (
                variability_score * 0.25 +    # Intraday variability
                extreme_high_score * 0.20 +   # Peak generation events
                extreme_low_score * 0.20 +    # Scarcity events
                surplus_score * 0.15 +        # Surplus events
                scarcity_score * 0.10 +       # Extended scarcity
                demand_score * 0.10           # High demand events
            )
            
            return composite_score
            
        self.daily_stats['composite_score'] = self.daily_stats.apply(calculate_score, axis=1)
        self.daily_stats = self.daily_stats.sort_values('composite_score', ascending=False)
        
        print("Top 10 most representative days:")
        top_days = self.daily_stats.head(10)
        for i, (_, row) in enumerate(top_days.iterrows(), 1):
            print(f"{i:2d}. {row['month']:2d}/{row['day']:2d} - Score: {row['composite_score']:.3f} "
                  f"(Coverage: {row['min_coverage']:4.1f}%-{row['max_coverage']:4.1f}%, "
                  f"Surplus: {row['surplus_hours']:2.0f}h)")
    
    def find_optimal_contiguous_periods(self, max_periods: int = 12, min_days: int = 1, max_days: int = 7):
        """Find optimal contiguous periods for modeling"""
        print(f"\\n=== FINDING OPTIMAL CONTIGUOUS PERIODS ===")
        print(f"Target: {max_periods} periods, {min_days}-{max_days} days each")
        
        if self.daily_stats is None or 'composite_score' not in self.daily_stats.columns:
            self.calculate_day_scores()
            
        periods = []
        used_days = set()
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        def get_next_day(month, day):
            """Get next day, handling month/year boundaries"""
            if day < days_in_month[month - 1]:
                return month, day + 1
            elif month < 12:
                return month + 1, 1
            else:
                return 1, 1  # Wrap to next year
                
        # Try to build periods starting from highest-scored days
        for _, start_day in self.daily_stats.iterrows():
            if start_day['date_key'] in used_days:
                continue
                
            # Try different period lengths (prefer longer periods)
            for period_length in range(max_days, min_days - 1, -1):
                period = {
                    'start_month': start_day['month'],
                    'start_day': start_day['day'],
                    'length': period_length,
                    'days': [],
                    'total_score': 0,
                    'min_coverage': float('inf'),
                    'max_coverage': float('-inf'),
                    'has_surplus': False,
                    'has_scarcity': False,
                    'total_surplus_hours': 0,
                    'total_scarcity_hours': 0
                }
                
                current_month, current_day = start_day['month'], start_day['day']
                valid_period = True
                
                # Build the period day by day
                for i in range(period_length):
                    current_key = f"{current_month}-{current_day}"
                    
                    # Find the day data
                    day_data = self.daily_stats[self.daily_stats['date_key'] == current_key]
                    
                    if day_data.empty or current_key in used_days:
                        valid_period = False
                        break
                        
                    day_row = day_data.iloc[0]
                    period['days'].append(day_row)
                    period['total_score'] += day_row['composite_score']
                    period['min_coverage'] = min(period['min_coverage'], day_row['min_coverage'])
                    period['max_coverage'] = max(period['max_coverage'], day_row['max_coverage'])
                    period['total_surplus_hours'] += day_row['surplus_hours']
                    period['total_scarcity_hours'] += day_row['extreme_scarcity_hours']
                    
                    if day_row['surplus_hours'] > 0:
                        period['has_surplus'] = True
                    if day_row['extreme_scarcity_hours'] > 0:
                        period['has_scarcity'] = True
                        
                    # Move to next day
                    current_month, current_day = get_next_day(current_month, current_day)
                
                if valid_period:
                    period['avg_score'] = period['total_score'] / period_length
                    period['coverage_range'] = period['max_coverage'] - period['min_coverage']
                    period['end_month'] = period['days'][-1]['month']
                    period['end_day'] = period['days'][-1]['day']
                    
                    periods.append(period)
                    
                    # Mark days as used
                    for day in period['days']:
                        used_days.add(day['date_key'])
                    break  # Found valid period for this start day
            
            if len(periods) >= max_periods:
                break
        
        # Sort by average score
        periods.sort(key=lambda x: x['avg_score'], reverse=True)
        
        print(f"\\nFound {len(periods)} optimal contiguous periods:")
        total_hours = 0
        
        for i, period in enumerate(periods, 1):
            hours = period['length'] * 24
            total_hours += hours
            
            print(f"\\n{i:2d}. {period['start_month']:2d}/{period['start_day']:2d} to "
                  f"{period['end_month']:2d}/{period['end_day']:2d} ({period['length']} days, {hours} hours)")
            print(f"    Avg Score: {period['avg_score']:.3f}, "
                  f"Coverage: {period['min_coverage']:4.1f}%-{period['max_coverage']:4.1f}% "
                  f"(Range: {period['coverage_range']:5.1f}%)")
            print(f"    Features: {'Surplus' if period['has_surplus'] else 'No surplus'} "
                  f"({period['total_surplus_hours']:2.0f}h), "
                  f"{'Scarcity' if period['has_scarcity'] else 'Normal'} "
                  f"({period['total_scarcity_hours']:2.0f}h <5%)")
        
        coverage_pct = (total_hours / 8760) * 100
        print(f"\\nSUMMARY:")
        print(f"Total modeling hours: {total_hours:,} ({coverage_pct:.1f}% of year)")
        print(f"Performance benefit: {8760 - total_hours:,} fewer hours ({100 - coverage_pct:.1f}% reduction)")
        
        return periods
    
    def export_to_excel_workbook(self, scenarios: Dict, output_file: str = "RE_Analysis_Complete.xlsx"):
        """Export all results to a comprehensive Excel workbook with multiple sheets"""
        print(f"\nCreating comprehensive Excel workbook: {output_file}")
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            
            # Sheet 1: Scenario Comparison Summary
            comparison_df = self.create_scenario_comparison_df(scenarios)
            comparison_df.to_excel(writer, sheet_name='Scenario_Comparison', index=False)
            print("  ✓ Scenario_Comparison sheet created")
            
            # Sheets 2-4: Period details for each scenario
            for scenario_name, periods in scenarios.items():
                sheet_name = f"Periods_{scenario_name.title().replace('_', '')}"
                periods_df = self.convert_periods_to_dataframe(periods)
                periods_df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  ✓ {sheet_name} sheet created")
            
            # Sheet 5: Extreme Events Summary
            extremes_df = self.create_extremes_summary_df()
            extremes_df.to_excel(writer, sheet_name='Extreme_Events', index=False)
            print("  ✓ Extreme_Events sheet created")
            
            # Sheet 6: Monthly Statistics
            monthly_df = self.create_monthly_stats_df()
            monthly_df.to_excel(writer, sheet_name='Monthly_Stats', index=False)
            print("  ✓ Monthly_Stats sheet created")
            
            # Sheets 7-9: Hourly data for each scenario's periods
            for scenario_name, periods in scenarios.items():
                sheet_name = f"Hourly_{scenario_name.title().replace('_', '')}"
                hourly_df = self.extract_hourly_data_for_periods(periods)
                hourly_df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  ✓ {sheet_name} sheet created ({len(hourly_df)} hours)")
        
        print(f"\n📊 Excel workbook '{output_file}' created successfully!")
        print("Sheets included:")
        print("  • Scenario_Comparison - Summary comparison of all three approaches")
        print("  • Periods_[Scenario] - Period details for each scenario (3 sheets)")
        print("  • Extreme_Events - Top abundance/scarcity periods")
        print("  • Monthly_Stats - Monthly coverage patterns")
        print("  • Hourly_[Scenario] - Complete hourly data for modeling (3 sheets)")
        
        return output_file
    
    def create_scenario_comparison_df(self, scenarios: Dict) -> pd.DataFrame:
        """Create scenario comparison as DataFrame"""
        comparison_data = []
        
        for scenario_name, periods in scenarios.items():
            total_hours = sum(p['length'] * 24 for p in periods)
            total_days = sum(p['length'] for p in periods)
            avg_period_length = total_days / len(periods) if periods else 0
            
            surplus_periods = sum(1 for p in periods if p['has_surplus'])
            scarcity_periods = sum(1 for p in periods if p['has_scarcity'])
            
            min_coverage = min(p['min_coverage'] for p in periods) if periods else 0
            max_coverage = max(p['max_coverage'] for p in periods) if periods else 0
            
            total_surplus_hours = sum(p['total_surplus_hours'] for p in periods)
            total_scarcity_hours = sum(p['total_scarcity_hours'] for p in periods)
            
            comparison_data.append({
                'Scenario': scenario_name.replace('_', ' ').title(),
                'Periods': len(periods),
                'Total_Hours': total_hours,
                'Total_Days': total_days,
                'Avg_Period_Days': round(avg_period_length, 1),
                'Min_Coverage_Pct': round(min_coverage, 1),
                'Max_Coverage_Pct': round(max_coverage, 1),
                'Coverage_Range_Pct': round(max_coverage - min_coverage, 1),
                'Surplus_Periods': surplus_periods,
                'Scarcity_Periods': scarcity_periods,
                'Total_Surplus_Hours': int(total_surplus_hours),
                'Total_Scarcity_Hours': int(total_scarcity_hours),
                'Year_Coverage_Pct': round(total_hours/8760*100, 1),
                'Performance_Benefit_Pct': round((8760-total_hours)/8760*100, 1)
            })
        
        return pd.DataFrame(comparison_data)
    
    def convert_periods_to_dataframe(self, periods: List[Dict]) -> pd.DataFrame:
        """Convert periods list to DataFrame for Excel export"""
        period_list = []
        for i, period in enumerate(periods, 1):
            period_list.append({
                'Period_ID': i,
                'Start_Month': period['start_month'],
                'Start_Day': period['start_day'],
                'End_Month': period['end_month'], 
                'End_Day': period['end_day'],
                'Length_Days': period['length'],
                'Total_Hours': period['length'] * 24,
                'Avg_Score': round(period['avg_score'], 4),
                'Min_Coverage_Pct': round(period['min_coverage'], 1),
                'Max_Coverage_Pct': round(period['max_coverage'], 1),
                'Coverage_Range_Pct': round(period['coverage_range'], 1),
                'Surplus_Hours': int(period['total_surplus_hours']),
                'Scarcity_Hours': int(period['total_scarcity_hours']),
                'Has_Surplus': period['has_surplus'],
                'Has_Scarcity': period['has_scarcity'],
                'Period_Description': f"{period['start_month']}/{period['start_day']}-{period['end_month']}/{period['end_day']}"
            })
            
        return pd.DataFrame(period_list)
    
    def create_extremes_summary_df(self) -> pd.DataFrame:
        """Create extremes summary DataFrame"""
        # Top abundance periods
        top_abundance = self.hourly_data.nlargest(20, 'coverage_pct')
        abundance_df = top_abundance[['month', 'day', 'hour', 'coverage_pct', 'total_re', 'total_demand', 'balance_mw', 'is_surplus']].copy()
        abundance_df['Event_Type'] = 'Abundance'
        abundance_df['Rank'] = range(1, len(abundance_df) + 1)
        
        # Top scarcity periods  
        top_scarcity = self.hourly_data.nsmallest(20, 'coverage_pct')
        scarcity_df = top_scarcity[['month', 'day', 'hour', 'coverage_pct', 'total_re', 'total_demand', 'balance_mw', 'is_surplus']].copy()
        scarcity_df['Event_Type'] = 'Scarcity'
        scarcity_df['Rank'] = range(1, len(scarcity_df) + 1)
        
        # Combine and clean up
        extremes_df = pd.concat([abundance_df, scarcity_df], ignore_index=True)
        extremes_df = extremes_df.round({'coverage_pct': 1, 'total_re': 0, 'total_demand': 0, 'balance_mw': 0})
        
        return extremes_df[['Event_Type', 'Rank', 'month', 'day', 'hour', 'coverage_pct', 'total_re', 'total_demand', 'balance_mw', 'is_surplus']]
    
    def create_monthly_stats_df(self) -> pd.DataFrame:
        """Create monthly statistics DataFrame"""
        monthly_stats = self.hourly_data.groupby('month').agg({
            'coverage_pct': ['mean', 'min', 'max', 'std'],
            'total_demand': ['mean', 'max'],
            'total_re': ['mean', 'max'],
            'is_surplus': 'sum',
            'is_extreme_scarcity': 'sum'
        }).round(1)
        
        # Flatten column names
        monthly_stats.columns = ['_'.join(col).strip() for col in monthly_stats.columns]
        monthly_stats = monthly_stats.reset_index()
        
        # Rename columns for clarity
        column_mapping = {
            'coverage_pct_mean': 'Avg_Coverage_Pct',
            'coverage_pct_min': 'Min_Coverage_Pct', 
            'coverage_pct_max': 'Max_Coverage_Pct',
            'coverage_pct_std': 'Coverage_StdDev',
            'total_demand_mean': 'Avg_Demand_MW',
            'total_demand_max': 'Peak_Demand_MW',
            'total_re_mean': 'Avg_RE_MW',
            'total_re_max': 'Peak_RE_MW',
            'is_surplus_sum': 'Surplus_Hours',
            'is_extreme_scarcity_sum': 'Extreme_Scarcity_Hours'
        }
        
        monthly_stats = monthly_stats.rename(columns=column_mapping)
        return monthly_stats
    
    def extract_hourly_data_for_periods(self, periods: List[Dict]) -> pd.DataFrame:
        """Extract hourly data for all periods in a scenario"""
        period_hours = []
        
        for period_id, period in enumerate(periods, 1):
            # Get all days in this period
            period_days = [day['date_key'] for day in period['days']]
            
            # Filter hourly data for these days
            period_hourly = self.hourly_data[self.hourly_data['date_key'].isin(period_days)].copy()
            period_hourly['Period_ID'] = period_id
            period_hourly['Period_Description'] = f"P{period_id}: {period['start_month']}/{period['start_day']}-{period['end_month']}/{period['end_day']}"
            
            period_hours.append(period_hourly)
        
        if period_hours:
            combined_df = pd.concat(period_hours, ignore_index=True)
            
            # Sort by period and then by time
            combined_df = combined_df.sort_values(['Period_ID', 'month', 'day', 'hour'])
            
            # Select and order columns for modeling
            model_columns = [
                'Period_ID', 'Period_Description', 'month', 'day', 'hour', 'date_hour',
                'total_demand', 'solar_mw', 'wind_mw', 'total_re', 
                'coverage_pct', 'balance_mw', 'is_surplus', 'is_extreme_scarcity'
            ]
            
            return combined_df[model_columns].round(1)
        else:
            return pd.DataFrame()
    
    def create_hourly_plots_for_scenarios(self, scenarios: Dict, save_plots: bool = True):
        """Create detailed hourly plots for each scenario"""
        print("\n📈 Creating hourly plots for all scenarios...")
        
        # Create a large figure with subplots for each scenario
        fig, axes = plt.subplots(3, 1, figsize=(20, 18))
        fig.suptitle('Hourly RE Coverage and Demand for Optimal Modeling Periods', fontsize=16, fontweight='bold')
        
        # Add VerveStacks logo watermark
        logo_manager.add_matplotlib_watermark(fig)
        
        colors = {'short_spans': 'red', 'medium_spans': 'blue', 'long_spans': 'green'}
        
        for idx, (scenario_name, periods) in enumerate(scenarios.items()):
            ax = axes[idx]
            
            # Extract hourly data for this scenario
            hourly_df = self.extract_hourly_data_for_periods(periods)
            
            if len(hourly_df) == 0:
                continue
                
            # Create date labels for x-axis
            hourly_df['date_label'] = hourly_df.apply(lambda row: f"{row['month']:02d}/{row['day']:02d}", axis=1)
            hourly_df['hour_index'] = range(len(hourly_df))
            
            # Plot demand and RE supply
            ax2 = ax.twinx()
            
            # Primary y-axis: Coverage percentage
            coverage_line = ax.plot(hourly_df['hour_index'], hourly_df['coverage_pct'], 
                                  color=colors[scenario_name], linewidth=1.5, alpha=0.8,
                                  label=f'RE Coverage %')
            
            # Fill areas for surplus and extreme scarcity
            surplus_mask = hourly_df['coverage_pct'] > 100
            scarcity_mask = hourly_df['coverage_pct'] < 5
            
            ax.fill_between(hourly_df['hour_index'], hourly_df['coverage_pct'], 100, 
                           where=surplus_mask, alpha=0.3, color='green', label='Surplus')
            ax.fill_between(hourly_df['hour_index'], hourly_df['coverage_pct'], 0, 
                           where=scarcity_mask, alpha=0.3, color='red', label='Extreme Scarcity (<5%)')
            
            # Secondary y-axis: Demand and RE supply in MW
            demand_line = ax2.plot(hourly_df['hour_index'], hourly_df['total_demand'], 
                                 color='black', linewidth=1, alpha=0.6, linestyle='--',
                                 label='Demand (MW)')
            re_line = ax2.plot(hourly_df['hour_index'], hourly_df['total_re'], 
                             color='orange', linewidth=1, alpha=0.7,
                             label='RE Supply (MW)')
            
            # Formatting
            ax.set_ylabel('RE Coverage (%)', fontweight='bold')
            ax2.set_ylabel('Power (MW)', fontweight='bold')
            ax.set_xlabel('Date (MM/DD)', fontweight='bold')
            
            ax.set_title(f'{scenario_name.replace("_", " ").title()}: {len(periods)} Periods, '
                        f'{len(hourly_df)} Hours ({len(hourly_df)/8760*100:.1f}% of year)', 
                        fontweight='bold', pad=20)
            
            # Set x-axis ticks to show dates
            # Show date labels at reasonable intervals based on data length
            n_ticks = min(15, len(hourly_df) // 24)  # Roughly one tick per day, max 15 ticks
            if n_ticks > 0:
                tick_indices = np.linspace(0, len(hourly_df)-1, n_ticks, dtype=int)
                tick_labels = [hourly_df.iloc[i]['date_label'] for i in tick_indices]
                ax.set_xticks(tick_indices)
                ax.set_xticklabels(tick_labels, rotation=45, ha='right')
            
            # Add horizontal lines for reference
            ax.axhline(y=100, color='gray', linestyle=':', alpha=0.5, label='100% Coverage')
            ax.axhline(y=50, color='gray', linestyle=':', alpha=0.3)
            ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
            
            # Legends
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)
            
            # Grid
            ax.grid(True, alpha=0.3)
            
            # Set y-axis limits
            ax.set_ylim(-5, max(150, hourly_df['coverage_pct'].max() * 1.1))
            
            # Add period separators with date labels
            current_period = None
            for i, (_, row) in enumerate(hourly_df.iterrows()):
                if row['Period_ID'] != current_period:
                    ax.axvline(x=i, color='purple', linestyle=':', alpha=0.6, linewidth=1)
                    # Add period start date label
                    if i > 0:  # Don't label the very first period
                        ax.text(i, ax.get_ylim()[1]*0.95, f"P{row['Period_ID']}\n{row['date_label']}", 
                               rotation=0, fontsize=8, alpha=0.8, ha='left', va='top',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
                    current_period = row['Period_ID']
        
        plt.tight_layout()
        
        if save_plots:
            plt.savefig('RE_scenarios_hourly_plots.png', dpi=300, bbox_inches='tight')
            print("  ✓ Saved detailed hourly plots to 'RE_scenarios_hourly_plots.png'")
        
        plt.show()
        
        # Create individual plots for each scenario for better detail
        self.create_individual_scenario_plots(scenarios, save_plots)
    
    def create_individual_scenario_plots(self, scenarios: Dict, save_plots: bool = True):
        """Create individual detailed plots for each scenario"""
        
        for scenario_name, periods in scenarios.items():
            hourly_df = self.extract_hourly_data_for_periods(periods)
            
            if len(hourly_df) == 0:
                continue
                
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
            fig.suptitle(f'{scenario_name.replace("_", " ").title()} Scenario: Detailed Hourly Analysis', 
                        fontsize=14, fontweight='bold')
            
            # Add VerveStacks logo watermark
            logo_manager.add_matplotlib_watermark(fig)
            
            hourly_df['hour_index'] = range(len(hourly_df))
            
            # Top plot: Coverage percentage with period boundaries
            ax1.plot(hourly_df['hour_index'], hourly_df['coverage_pct'], 
                    color='darkblue', linewidth=1.5, label='RE Coverage %')
            
            # Fill surplus and scarcity areas
            surplus_mask = hourly_df['coverage_pct'] > 100
            scarcity_mask = hourly_df['coverage_pct'] < 5
            
            ax1.fill_between(hourly_df['hour_index'], hourly_df['coverage_pct'], 100, 
                           where=surplus_mask, alpha=0.4, color='green', label='Surplus')
            ax1.fill_between(hourly_df['hour_index'], hourly_df['coverage_pct'], 0, 
                           where=scarcity_mask, alpha=0.4, color='red', label='Extreme Scarcity')
            
            ax1.set_ylabel('RE Coverage (%)', fontweight='bold')
            ax1.set_title('Renewable Energy Coverage Over Time')
            ax1.axhline(y=100, color='gray', linestyle='--', alpha=0.5, label='100% Coverage')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            # Bottom plot: Demand vs RE Supply
            ax2.plot(hourly_df['hour_index'], hourly_df['total_demand'], 
                    color='red', linewidth=1.5, label='Demand', alpha=0.8)
            ax2.plot(hourly_df['hour_index'], hourly_df['total_re'], 
                    color='green', linewidth=1.5, label='RE Supply', alpha=0.8)
            ax2.fill_between(hourly_df['hour_index'], hourly_df['total_demand'], hourly_df['total_re'],
                           where=(hourly_df['total_re'] >= hourly_df['total_demand']), 
                           alpha=0.3, color='green', label='RE Surplus')
            ax2.fill_between(hourly_df['hour_index'], hourly_df['total_demand'], hourly_df['total_re'],
                           where=(hourly_df['total_re'] < hourly_df['total_demand']), 
                           alpha=0.3, color='red', label='RE Shortfall')
            
            ax2.set_xlabel('Hour Index', fontweight='bold')
            ax2.set_ylabel('Power (MW)', fontweight='bold')
            ax2.set_title('Demand vs Renewable Energy Supply')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            # Add period separators to both plots
            current_period = None
            for i, period_id in enumerate(hourly_df['Period_ID']):
                if period_id != current_period:
                    ax1.axvline(x=i, color='purple', linestyle=':', alpha=0.6, linewidth=1)
                    ax2.axvline(x=i, color='purple', linestyle=':', alpha=0.6, linewidth=1)
                    # Add period labels
                    if i > 0:  # Don't label the first period start
                        period_desc = hourly_df.iloc[i]['Period_Description'].split(':')[0]
                        ax1.text(i, ax1.get_ylim()[1]*0.9, period_desc, rotation=90, 
                                fontsize=8, alpha=0.7, ha='right')
                    current_period = period_id
            
            plt.tight_layout()
            
            if save_plots:
                filename = f'RE_{scenario_name}_detailed.png'
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                print(f"  ✓ Saved {filename}")
            
            plt.show()
        
    def create_summary_visualizations(self, save_plots: bool = True):
        """Create summary visualizations"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Add VerveStacks logo watermark
        logo_manager.add_matplotlib_watermark(fig)
        
        # 1. Coverage distribution by month
        monthly_coverage = self.hourly_data.groupby('month')['coverage_pct'].mean()
        axes[0,0].bar(monthly_coverage.index, monthly_coverage.values)
        axes[0,0].set_title('Average RE Coverage by Month')
        axes[0,0].set_xlabel('Month')
        axes[0,0].set_ylabel('Coverage (%)')
        
        # 2. Daily coverage variability  
        axes[0,1].scatter(self.daily_stats['avg_coverage'], self.daily_stats['coverage_range'], 
                         alpha=0.6, c=self.daily_stats['surplus_hours'], cmap='viridis')
        axes[0,1].set_xlabel('Average Daily Coverage (%)')
        axes[0,1].set_ylabel('Daily Coverage Range (%)')
        axes[0,1].set_title('Daily Coverage: Average vs Variability')
        cbar = plt.colorbar(axes[0,1].collections[0], ax=axes[0,1])
        cbar.set_label('Surplus Hours')
        
        # 3. Hourly coverage distribution
        axes[1,0].hist(self.hourly_data['coverage_pct'], bins=50, alpha=0.7, edgecolor='black')
        axes[1,0].set_xlabel('Coverage (%)')
        axes[1,0].set_ylabel('Frequency')
        axes[1,0].set_title('Distribution of Hourly RE Coverage')
        axes[1,0].axvline(self.hourly_data['coverage_pct'].mean(), color='red', 
                         linestyle='--', label=f'Mean: {self.hourly_data["coverage_pct"].mean():.1f}%')
        axes[1,0].legend()
        
        # 4. Surplus hours by month
        surplus_by_month = self.hourly_data[self.hourly_data['is_surplus']].groupby('month').size()
        all_months = range(1, 13)
        surplus_counts = [surplus_by_month.get(m, 0) for m in all_months]
        axes[1,1].bar(all_months, surplus_counts)
        axes[1,1].set_title('Surplus Hours by Month')
        axes[1,1].set_xlabel('Month')
        axes[1,1].set_ylabel('Surplus Hours')
        
        plt.tight_layout()
        
        if save_plots:
            plt.savefig('re_analysis_summary.png', dpi=300, bbox_inches='tight')
            print("\\nSaved summary plots to 're_analysis_summary.png'")
        
        plt.show()
        
    def run_three_scenario_analysis(self, target_hours: int = 400, create_excel: bool = True, create_plots: bool = True):
        """Run analysis for three different span scenarios optimized for target hours"""
        print(f"=== RUNNING THREE-SCENARIO ANALYSIS (Target: ~{target_hours} hours each) ===")
        
        # 1. Analyze extremes (common to all scenarios)
        extremes = self.analyze_extremes()
        
        scenarios = {}
        
        # Scenario 1: Short spans (1-3 days) - Maximum granularity
        print(f"\n{'='*60}")
        print("SCENARIO 1: SHORT SPANS (1-3 days) - Maximum Event Granularity")
        print(f"{'='*60}")
        max_periods_short = target_hours // (3 * 24)  # Assume avg 3 days per period
        periods_short = self.find_optimal_contiguous_periods(
            max_periods=max_periods_short, min_days=1, max_days=3
        )
        scenarios['short_spans'] = periods_short
        
        # Scenario 2: Medium spans (1-7 days) - Balanced approach  
        print(f"\n{'='*60}")
        print("SCENARIO 2: MEDIUM SPANS (1-7 days) - Balanced Approach")
        print(f"{'='*60}")
        max_periods_medium = target_hours // (5 * 24)  # Assume avg 5 days per period
        periods_medium = self.find_optimal_contiguous_periods(
            max_periods=max_periods_medium, min_days=1, max_days=7
        )
        scenarios['medium_spans'] = periods_medium
        
        # Scenario 3: Long spans (7-15 days) - Extended phenomena capture
        print(f"\n{'='*60}")
        print("SCENARIO 3: LONG SPANS (7-15 days) - Extended Phenomena")
        print(f"{'='*60}")
        max_periods_long = target_hours // (12 * 24)  # Assume avg 12 days per period
        periods_long = self.find_optimal_contiguous_periods(
            max_periods=max_periods_long, min_days=7, max_days=15
        )
        scenarios['long_spans'] = periods_long
        
        # Create comparison summary
        self.create_scenario_comparison(scenarios)
        
        # Export to comprehensive Excel workbook
        if create_excel:
            excel_file = self.export_to_excel_workbook(scenarios)
        
        # Create detailed plots
        if create_plots:
            self.create_hourly_plots_for_scenarios(scenarios, save_plots=True)
            self.create_summary_visualizations(save_plots=True)
            
        return {
            'extremes': extremes,
            'scenarios': scenarios,
            'hourly_data': self.hourly_data,
            'daily_stats': self.daily_stats,
            'excel_file': excel_file if create_excel else None
        }
    
    def create_scenario_comparison(self, scenarios: Dict):
        """Create a comparison table of the three scenarios"""
        print(f"\n{'='*80}")
        print("SCENARIO COMPARISON SUMMARY")
        print(f"{'='*80}")
        
        comparison_data = []
        
        for scenario_name, periods in scenarios.items():
            total_hours = sum(p['length'] * 24 for p in periods)
            total_days = sum(p['length'] for p in periods)
            avg_period_length = total_days / len(periods) if periods else 0
            
            surplus_periods = sum(1 for p in periods if p['has_surplus'])
            scarcity_periods = sum(1 for p in periods if p['has_scarcity'])
            
            min_coverage = min(p['min_coverage'] for p in periods) if periods else 0
            max_coverage = max(p['max_coverage'] for p in periods) if periods else 0
            
            total_surplus_hours = sum(p['total_surplus_hours'] for p in periods)
            total_scarcity_hours = sum(p['total_scarcity_hours'] for p in periods)
            
            comparison_data.append({
                'Scenario': scenario_name.replace('_', ' ').title(),
                'Periods': len(periods),
                'Total Hours': total_hours,
                'Total Days': total_days,
                'Avg Period (days)': f"{avg_period_length:.1f}",
                'Coverage Range': f"{min_coverage:.1f}%-{max_coverage:.1f}%",
                'Surplus Periods': surplus_periods,
                'Scarcity Periods': scarcity_periods,
                'Total Surplus Hrs': total_surplus_hours,
                'Total Scarcity Hrs': total_scarcity_hours,
                'Year Coverage': f"{total_hours/8760*100:.1f}%"
            })
        
        # Print formatted comparison table
        headers = list(comparison_data[0].keys())
        
        # Calculate column widths
        col_widths = {}
        for header in headers:
            col_widths[header] = max(len(header), 
                                   max(len(str(row[header])) for row in comparison_data))
        
        # Print header
        header_row = " | ".join(header.ljust(col_widths[header]) for header in headers)
        print(header_row)
        print("-" * len(header_row))
        
        # Print data rows
        for row in comparison_data:
            data_row = " | ".join(str(row[header]).ljust(col_widths[header]) for header in headers)
            print(data_row)
            
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   • SHORT SPANS: Best for capturing individual extreme events with high precision")
        print(f"   • MEDIUM SPANS: Balanced approach capturing event transitions and daily cycles")  
        print(f"   • LONG SPANS: Best for multi-day phenomena, seasonal transitions, storage cycling")
        
    def run_full_analysis(self, max_periods: int = 12, create_excel: bool = True, create_plots: bool = True):
        """Run the complete analysis pipeline - DEPRECATED: Use run_three_scenario_analysis instead"""
        print("⚠️  DEPRECATED: Use run_three_scenario_analysis() for optimized span selection")
        return self.run_three_scenario_analysis(target_hours=400, create_excel=create_excel, create_plots=create_plots)

# Example usage
if __name__ == "__main__":
    # Initialize analyzer with your Excel file
    analyzer = REDemandAnalyzer('VerveStacks_ITA.xlsx')
    
    # Run three-scenario analysis with Excel workbook and plots
    results = analyzer.run_three_scenario_analysis(
        target_hours=400,    # Target hours per scenario (~400 hour modeling limit)
        create_excel=True,   # Create comprehensive Excel workbook
        create_plots=True    # Generate detailed hourly plots + summary plots
    )
    
    print("\\n=== THREE-SCENARIO ANALYSIS COMPLETE ===")
    print("\\n📊 OUTPUTS CREATED:")
    print("\\n1. COMPREHENSIVE EXCEL WORKBOOK: 'RE_Analysis_Complete.xlsx'")
    print("   • Scenario_Comparison - Summary of all three approaches")
    print("   • Periods_[Scenario] - Period details (3 sheets)")
    print("   • Extreme_Events - Top abundance/scarcity periods")  
    print("   • Monthly_Stats - Monthly coverage patterns")
    print("   • Hourly_[Scenario] - Complete hourly data for modeling (3 sheets)")
    print("\\n2. DETAILED PLOTS:")
    print("   • RE_scenarios_hourly_plots.png - Overview of all scenarios")
    print("   • RE_[scenario]_detailed.png - Individual detailed plots (3 files)")
    print("   • re_analysis_summary.png - Monthly/statistical summaries")
    print("\\n3. READY FOR YOUR MODEL:")
    print("   Each 'Hourly_[Scenario]' sheet contains Period_ID, dates, hours,")
    print("   demand, RE supply, coverage %, and flags - perfect for direct import!")
    print("\\n🎯 Each scenario targets ~400 hours, optimized for different modeling needs!")
    
    # Access specific results:
    # short_periods = results['scenarios']['short_spans']
    # medium_periods = results['scenarios']['medium_spans'] 
    # long_periods = results['scenarios']['long_spans']
    # excel_workbook = results['excel_file']