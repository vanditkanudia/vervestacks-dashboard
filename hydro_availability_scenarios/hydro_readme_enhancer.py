"""
Hydro README Enhancement Module
Generates charts and content for country-specific README documentation
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class HydroReadmeEnhancer:
    """Generate hydro availability charts and content for README documentation"""
    
    def __init__(self, iso_code):
        self.iso_code = iso_code
        self.base_dir = Path(__file__).parent
        
        # Load data
        self.annual_df = self._load_annual_data()
        self.monthly_df = self._load_monthly_data()
        self.scenarios_df = self._load_scenarios_data()
        
        # Country metadata
        self.country_info = self._get_country_info()
        
    def _load_annual_data(self):
        """Load historical annual capacity factor data"""
        try:
            return pd.read_csv(self.base_dir / "annual_cf_table.csv")
        except FileNotFoundError:
            print(f"Warning: annual_cf_table.csv not found")
            return pd.DataFrame()
    
    def _load_monthly_data(self):
        """Load historical monthly capacity factor data"""
        try:
            return pd.read_csv(self.base_dir / "monthly_cf_table.csv")
        except FileNotFoundError:
            print(f"Warning: monthly_cf_table.csv not found")
            return pd.DataFrame()
    
    def _load_scenarios_data(self):
        """Load hydro availability scenarios"""
        try:
            return pd.read_csv(self.base_dir / "hydro_scenarios_full_2025_2050.csv")
        except FileNotFoundError:
            print(f"Warning: hydro_scenarios_full_2025_2050.csv not found")
            return pd.DataFrame()
    
    def _get_country_info(self):
        """Get country-specific information"""
        # Top hydro countries with metadata
        hydro_countries = {
            'NOR': {'name': 'Norway', 'hydro_share': 96},
            'BRA': {'name': 'Brazil', 'hydro_share': 65},
            'VEN': {'name': 'Venezuela', 'hydro_share': 68},
            'COL': {'name': 'Colombia', 'hydro_share': 70},
            'CAN': {'name': 'Canada', 'hydro_share': 60},
            'CHE': {'name': 'Switzerland', 'hydro_share': 60},
            'AUT': {'name': 'Austria', 'hydro_share': 55},
            'SWE': {'name': 'Sweden', 'hydro_share': 45},
            'PER': {'name': 'Peru', 'hydro_share': 55},
            'ECU': {'name': 'Ecuador', 'hydro_share': 75}
        }
        
        return hydro_countries.get(self.iso_code, {
            'name': self.iso_code,
            'hydro_share': 'N/A'
        })
    
    def has_hydro_data(self):
        """Check if country has sufficient hydro data for analysis"""
        # Check if country exists in scenarios data
        if len(self.scenarios_df) == 0:
            return False
        
        country_scenarios = self.scenarios_df[
            self.scenarios_df['Country code'] == self.iso_code
        ]
        
        return len(country_scenarios) > 0
    
    def get_hydro_statistics(self):
        """Generate key hydro statistics for the country"""
        if not self.has_hydro_data():
            return None
        
        # Get P10/P50/P90 annual averages from scenarios
        country_scenarios = self.scenarios_df[
            self.scenarios_df['Country code'] == self.iso_code
        ]
        
        # Calculate annual averages for each scenario
        annual_avgs = country_scenarios.groupby('Scenario')['Availability_Factor'].mean()
        
        stats = {
            'country_name': self.country_info['name'],
            'hydro_share': self.country_info['hydro_share'],
            'p10_avg': f"{annual_avgs.quantile(0.1) * 100:.1f}%",
            'p50_avg': f"{annual_avgs.quantile(0.5) * 100:.1f}%",
            'p90_avg': f"{annual_avgs.quantile(0.9) * 100:.1f}%",
            'scenario_count': len(annual_avgs)
        }
        
        # Add historical context if available
        historical_annual = self.annual_df[self.annual_df['iso_code'] == self.iso_code]
        if len(historical_annual) > 0:
            hist_mean = historical_annual['annual_hydro_cf'].mean()
            stats['historical_avg'] = f"{hist_mean * 100:.1f}%"
            stats['historical_years'] = f"{historical_annual['Year'].min()}-{historical_annual['Year'].max()}"
            
            # Calculate drought threshold (P20)
            if len(historical_annual) > 5:
                drought_threshold = historical_annual['annual_hydro_cf'].quantile(0.20)
                stats['drought_threshold'] = f"{drought_threshold * 100:.1f}%"
            else:
                stats['drought_threshold'] = "35.0%"  # Generic fallback
        
        return stats
    
    def generate_monthly_profile_chart(self, output_dir="source_data"):
        """Generate monthly hydro availability profile chart"""
        if not self.has_hydro_data():
            print(f"No hydro data available for {self.iso_code}")
            return None
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Set up the plot
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colors = {'P10': '#d62728', 'P50': '#2ca02c', 'P90': '#1f77b4', 'Historical': '#ff7f0e'}
        
        # Get monthly profiles using the correct method
        profiles = self.get_seasonal_profiles(self.iso_code)
        if profiles is None:
            print(f"No monthly profile data for {self.iso_code}")
            return None
        
        # Plot scenario profiles
        for percentile in ['P10', 'P50', 'P90']:
            data = profiles[profiles['Percentile'] == percentile]
            scenario_num = data['Scenario_Number'].iloc[0] if len(data) > 0 else 'N/A'
            
            ax.plot(data['Month'], data['Availability_Factor'] * 100,
                   marker='o', label=f'{percentile} Future (S{scenario_num})',
                   color=colors[percentile], linewidth=2.5, markersize=6)
        
        # Add historical monthly average if available
        hist_monthly = self.monthly_df[self.monthly_df['iso_code'] == self.iso_code]
        if len(hist_monthly) > 0:
            hist_avg_by_month = hist_monthly.groupby('month')['monthly_hydro_cf'].mean()
            months = list(range(1, 13))
            hist_values = [hist_avg_by_month.get(m, np.nan) for m in months]
            
            if not all(np.isnan(hist_values)):
                ax.plot(months, np.array(hist_values) * 100,
                       marker='s', label='Historical Average (2000-2023)',
                       color=colors['Historical'], linewidth=3, markersize=7,
                       linestyle='--', alpha=0.8)
        
        # Formatting
        country_name = self.country_info['name']
        hydro_share = self.country_info['hydro_share']
        
        ax.set_title(f'{country_name} - Monthly Hydro Availability\n'
                    f'Hydro Share: {hydro_share}% | Future Scenarios vs Historical Data',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Month', fontsize=12)
        ax.set_ylabel('Availability Factor (%)', fontsize=12)
        ax.set_xlim(0.5, 12.5)
        ax.set_ylim(0, max(80, profiles['Availability_Factor'].max() * 110))
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=10)
        
        # Month labels
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
        
        # Save chart
        chart_filename = f"{self.iso_code}_hydro_monthly_profile.png"
        chart_path = output_path / chart_filename
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Monthly profile chart saved: {chart_path}")
        return chart_filename
    
    def calculate_percentile_scenarios(self, country: str):
        """Calculate which scenarios represent P10/P50/P90 for a country"""
        country_data = self.scenarios_df[self.scenarios_df['Country code'] == country]
        
        if len(country_data) == 0:
            return None
        
        # Calculate mean availability for each scenario
        scenario_means = country_data.groupby('Scenario')['Availability_Factor'].mean()
        scenario_means = scenario_means.sort_values()
        
        n_scenarios = len(scenario_means)
        
        # Find percentile positions
        p10_idx = int(n_scenarios * 0.10)
        p50_idx = int(n_scenarios * 0.50)
        p90_idx = int(n_scenarios * 0.90) - 1
        
        # Get scenario numbers
        p10_scenario = scenario_means.index[p10_idx]
        p50_scenario = scenario_means.index[p50_idx]
        p90_scenario = scenario_means.index[p90_idx]
        
        return {
            'P10': {'scenario': p10_scenario, 'mean': scenario_means.iloc[p10_idx]},
            'P50': {'scenario': p50_scenario, 'mean': scenario_means.iloc[p50_idx]},
            'P90': {'scenario': p90_scenario, 'mean': scenario_means.iloc[p90_idx]}
        }
    
    def get_seasonal_profiles(self, country: str):
        """Get P10/P50/P90 seasonal (monthly) profiles for a country"""
        scenarios = self.calculate_percentile_scenarios(country)
        if not scenarios:
            return None
        
        country_data = self.scenarios_df[self.scenarios_df['Country code'] == country]
        
        profiles = []
        for percentile, info in scenarios.items():
            scenario_data = country_data[country_data['Scenario'] == info['scenario']]
            
            # Calculate average by month across all years for this specific scenario
            monthly_avg = scenario_data.groupby('Month')['Availability_Factor'].mean()
            
            for month in range(1, 13):
                profiles.append({
                    'Country': country,
                    'Percentile': percentile,
                    'Month': month,
                    'Availability_Factor': monthly_avg.get(month, 0.4),
                    'Scenario_Number': info['scenario']
                })
        
        return pd.DataFrame(profiles)
    
    def get_annual_profiles(self, country: str):
        """Get P10/P50/P90 annual trajectories for a country"""
        scenarios = self.calculate_percentile_scenarios(country)
        if not scenarios:
            return None
        
        country_data = self.scenarios_df[self.scenarios_df['Country code'] == country]
        
        profiles = []
        for percentile, info in scenarios.items():
            scenario_data = country_data[country_data['Scenario'] == info['scenario']]
            
            # Calculate annual averages for this specific scenario
            yearly_avg = scenario_data.groupby('Year')['Availability_Factor'].mean()
            
            for year in yearly_avg.index:
                profiles.append({
                    'Country': country,
                    'Percentile': percentile,
                    'Year': year,
                    'Availability_Factor': yearly_avg[year],
                    'Scenario_Number': info['scenario']
                })
        
        return pd.DataFrame(profiles)

    def generate_annual_trajectory_chart(self, output_dir="source_data"):
        """Generate annual hydro availability trajectory chart"""
        if not self.has_hydro_data():
            print(f"No hydro data available for {self.iso_code}")
            return None
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Set up the plot
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colors = {'P10': '#d62728', 'P50': '#2ca02c', 'P90': '#1f77b4', 'Historical': '#ff7f0e'}
        
        # Get annual profiles using the correct method
        profiles = self.get_annual_profiles(self.iso_code)
        if profiles is None:
            print(f"No annual profile data for {self.iso_code}")
            return None
        
        # Plot future scenario trajectories
        for percentile in ['P10', 'P50', 'P90']:
            data = profiles[profiles['Percentile'] == percentile]
            scenario_num = data['Scenario_Number'].iloc[0] if len(data) > 0 else 'N/A'
            
            ax.plot(data['Year'], data['Availability_Factor'] * 100,
                   marker='o', label=f'{percentile} Future (S{scenario_num})',
                   color=colors[percentile], linewidth=2.5, markersize=4)
        
        # Add historical annual data if available
        hist_annual = self.annual_df[self.annual_df['iso_code'] == self.iso_code]
        if len(hist_annual) > 0:
            # Plot historical time series
            ax.plot(hist_annual['Year'], hist_annual['annual_hydro_cf'] * 100,
                   marker='s', label='Historical Data (2000-2023)',
                   color=colors['Historical'], linewidth=2, markersize=5,
                   linestyle='-', alpha=0.8)
            
            # Add historical average line
            hist_mean = hist_annual['annual_hydro_cf'].mean() * 100
            ax.axhline(y=hist_mean, color=colors['Historical'], linestyle=':',
                      alpha=0.6, linewidth=2, label=f'Historical Avg ({hist_mean:.1f}%)')
            
            # Add drought threshold
            if len(hist_annual) > 5:
                drought_threshold = hist_annual['annual_hydro_cf'].quantile(0.20) * 100
                ax.axhline(y=drought_threshold, color='red', linestyle='--', alpha=0.7,
                          linewidth=2, label=f'Drought Threshold ({drought_threshold:.1f}%)')
        
        # Formatting
        country_name = self.country_info['name']
        hydro_share = self.country_info['hydro_share']
        
        ax.set_title(f'{country_name} - Annual Hydro Availability Trajectory\n'
                    f'Hydro Share: {hydro_share}% | Historical Data (2000-2023) → Future Scenarios (2025-2050)',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Annual Availability Factor (%)', fontsize=12)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Set reasonable y-limits
        all_values = profiles['Availability_Factor'].values
        if len(hist_annual) > 0:
            all_values = np.concatenate([all_values, hist_annual['annual_hydro_cf'].values])
        
        y_min = max(0, (min(all_values) * 100) - 5)
        y_max = (max(all_values) * 100) + 5
        ax.set_ylim(y_min, y_max)
        
        # Set x-axis to show both historical and future
        if len(hist_annual) > 0:
            ax.set_xlim(hist_annual['Year'].min() - 1, profiles['Year'].max() + 1)
        
        # Save chart
        chart_filename = f"{self.iso_code}_hydro_annual_trajectory.png"
        chart_path = output_path / chart_filename
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Annual trajectory chart saved: {chart_path}")
        return chart_filename
    
    def generate_hydro_content_for_readme(self, output_dir="source_data"):
        """Generate complete hydro content for README integration"""
        if not self.has_hydro_data():
            return None
        
        # Generate charts
        monthly_chart = self.generate_monthly_profile_chart(output_dir)
        annual_chart = self.generate_annual_trajectory_chart(output_dir)
        
        # Get statistics
        stats = self.get_hydro_statistics()
        
        if not stats:
            return None
        
        # Prepare content dictionary for YAML template
        content = {
            'hydro_country_name': stats['country_name'],
            'hydro_share_percent': stats['hydro_share'],
            'hydro_p10_avg': stats['p10_avg'],
            'hydro_p50_avg': stats['p50_avg'],
            'hydro_p90_avg': stats['p90_avg'],
            'hydro_monthly_chart_filename': monthly_chart,
            'hydro_annual_chart_filename': annual_chart,
            'hydro_scenario_count': stats['scenario_count']
        }
        
        # Add historical context if available
        if 'historical_avg' in stats:
            content.update({
                'hydro_historical_avg': stats['historical_avg'],
                'hydro_historical_years': stats['historical_years'],
                'hydro_drought_threshold': stats['drought_threshold']
            })
        
        return content

# Test function
def test_hydro_enhancer(iso_code="BRA"):
    """Test the hydro enhancer with a specific country"""
    enhancer = HydroReadmeEnhancer(iso_code)
    
    if not enhancer.has_hydro_data():
        print(f"No hydro data available for {iso_code}")
        return
    
    print(f"Testing hydro enhancement for {iso_code}...")
    
    # Generate content
    content = enhancer.generate_hydro_content_for_readme()
    
    if content:
        print("\n✅ Generated hydro content:")
        for key, value in content.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Failed to generate hydro content")

if __name__ == "__main__":
    # Test with Brazil (major hydro country)
    test_hydro_enhancer("BRA")
