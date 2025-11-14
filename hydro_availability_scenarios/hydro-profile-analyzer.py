import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class HydroProfileAnalyzer:
    """
    Analyze and visualize P10/P50/P90 hydro availability profiles
    for top hydro-dependent countries from scenario data.
    """
    
    def __init__(self, csv_path: str):
        """
        Initialize with path to the full scenarios CSV file.
        
        Parameters:
        -----------
        csv_path : str
            Path to the CSV with all 100 scenarios
        """
        print(f"Loading scenario data from {csv_path}...")
        self.df = pd.read_csv(csv_path)
        
        # Filter out historical data if present
        if 'Scenario' in self.df.columns:
            # Keep only numeric scenarios (not 'Historical')
            self.df = self.df[self.df['Scenario'].apply(lambda x: str(x).isdigit())]
            self.df['Scenario'] = self.df['Scenario'].astype(int)
        
        # Remove any NaN values from Country code before sorting
        self.countries = sorted(self.df['Country code'].dropna().unique())
        print(f"Loaded data for {len(self.countries)} countries")
        
        # Define top hydro-dependent countries (% of electricity from hydro)
        self.top_hydro_countries = {
            'NOR': {'name': 'Norway', 'hydro_share': 96},
            'BRA': {'name': 'Brazil', 'hydro_share': 65},
            'VEN': {'name': 'Venezuela', 'hydro_share': 68},
            'COL': {'name': 'Colombia', 'hydro_share': 70},
            'CAN': {'name': 'Canada', 'hydro_share': 60},
            'CHE': {'name': 'Switzerland', 'hydro_share': 60},
            'AUT': {'name': 'Austria', 'hydro_share': 60},
            'SWE': {'name': 'Sweden', 'hydro_share': 45},
            'VNM': {'name': 'Vietnam', 'hydro_share': 38},
            'PER': {'name': 'Peru', 'hydro_share': 55}
        }
    
    def calculate_percentile_scenarios(self, country: str) -> Dict:
        """
        Find which scenarios best represent P10/P50/P90 for a country.
        """
        country_data = self.df[self.df['Country code'] == country]
        
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
    
    def get_monthly_profiles(self, country: str) -> pd.DataFrame:
        """
        Get P10/P50/P90 monthly profiles for a country.
        """
        scenarios = self.calculate_percentile_scenarios(country)
        if not scenarios:
            return None
        
        country_data = self.df[self.df['Country code'] == country]
        
        profiles = []
        for percentile, info in scenarios.items():
            scenario_data = country_data[country_data['Scenario'] == info['scenario']]
            
            # Calculate average by month across all years
            monthly_avg = scenario_data.groupby('Month')['Availability_Factor'].mean()
            
            for month in range(1, 13):
                profiles.append({
                    'Country': country,
                    'Percentile': percentile,
                    'Month': month,
                    'Availability_Factor': monthly_avg.get(month, 0.4)
                })
        
        return pd.DataFrame(profiles)
    
    def analyze_drought_characteristics(self, country: str) -> Dict:
        """
        Analyze drought characteristics for P10/P50/P90 scenarios.
        """
        scenarios = self.calculate_percentile_scenarios(country)
        if not scenarios:
            return None
        
        country_data = self.df[self.df['Country code'] == country]
        
        results = {}
        for percentile, info in scenarios.items():
            scenario_data = country_data[country_data['Scenario'] == info['scenario']]
            
            # Calculate yearly averages
            yearly_avg = scenario_data.groupby('Year')['Availability_Factor'].mean()
            
            # Drought metrics
            drought_threshold = 0.35  # 35% availability
            severe_drought_threshold = 0.30  # 30% availability
            
            drought_years = (yearly_avg < drought_threshold).sum()
            severe_drought_years = (yearly_avg < severe_drought_threshold).sum()
            worst_year = yearly_avg.min()
            best_year = yearly_avg.max()
            volatility = yearly_avg.std()
            
            # Find longest drought sequence
            drought_sequence = []
            current_sequence = 0
            for val in yearly_avg.values:
                if val < drought_threshold:
                    current_sequence += 1
                else:
                    if current_sequence > 0:
                        drought_sequence.append(current_sequence)
                    current_sequence = 0
            if current_sequence > 0:
                drought_sequence.append(current_sequence)
            
            max_drought_length = max(drought_sequence) if drought_sequence else 0
            
            results[percentile] = {
                'mean': info['mean'],
                'drought_years': drought_years,
                'severe_drought_years': severe_drought_years,
                'worst_year': worst_year,
                'best_year': best_year,
                'volatility': volatility,
                'max_drought_length': max_drought_length
            }
        
        return results
    
    def create_comparison_table(self) -> pd.DataFrame:
        """
        Create comparison table for top hydro countries.
        """
        results = []
        
        for iso_code, info in self.top_hydro_countries.items():
            if iso_code not in self.countries:
                continue
                
            drought_stats = self.analyze_drought_characteristics(iso_code)
            if not drought_stats:
                continue
            
            # Calculate P10-P50 gap
            p10_p50_gap = (drought_stats['P50']['mean'] - drought_stats['P10']['mean']) * 100
            
            results.append({
                'Country': info['name'],
                'ISO': iso_code,
                'Hydro Share (%)': info['hydro_share'],
                'P10 Avg (%)': round(drought_stats['P10']['mean'] * 100, 1),
                'P50 Avg (%)': round(drought_stats['P50']['mean'] * 100, 1),
                'P90 Avg (%)': round(drought_stats['P90']['mean'] * 100, 1),
                'P10-P50 Gap (%)': round(p10_p50_gap, 1),
                'P10 Drought Years': drought_stats['P10']['drought_years'],
                'P50 Drought Years': drought_stats['P50']['drought_years'],
                'P10 Worst (%)': round(drought_stats['P10']['worst_year'] * 100, 1),
                'Max Drought Length': drought_stats['P10']['max_drought_length']
            })
        
        df = pd.DataFrame(results)
        # Sort by hydro dependency
        df = df.sort_values('Hydro Share (%)', ascending=False)
        
        return df
    
    def plot_monthly_profiles(self, countries: List[str] = None, save_path: str = None):
        """
        Plot monthly P10/P50/P90 profiles for selected countries.
        """
        if countries is None:
            # Use top 6 hydro-dependent countries
            countries = ['NOR', 'BRA', 'COL', 'CAN', 'CHE', 'VNM']
        
        # Filter to available countries
        countries = [c for c in countries if c in self.countries]
        
        if len(countries) == 0:
            print("No valid countries to plot")
            return
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        colors = {'P10': '#ff7f0e', 'P50': '#2ca02c', 'P90': '#1f77b4'}
        
        for idx, country in enumerate(countries[:6]):
            ax = axes[idx]
            
            profiles = self.get_monthly_profiles(country)
            if profiles is None:
                continue
            
            country_name = self.top_hydro_countries.get(country, {}).get('name', country)
            
            for percentile in ['P10', 'P50', 'P90']:
                data = profiles[profiles['Percentile'] == percentile]
                ax.plot(data['Month'], data['Availability_Factor'] * 100, 
                       marker='o', label=percentile, color=colors[percentile], linewidth=2)
            
            ax.set_title(f'{country_name} ({country})', fontsize=12, fontweight='bold')
            ax.set_xlabel('Month')
            ax.set_ylabel('Availability Factor (%)')
            ax.set_xlim(0.5, 12.5)
            ax.set_ylim(0, 80)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            
            # Add month labels
            ax.set_xticks(range(1, 13))
            ax.set_xticklabels(['J', 'F', 'M', 'A', 'M', 'J', 
                               'J', 'A', 'S', 'O', 'N', 'D'])
        
        plt.suptitle('Monthly Hydro Availability Profiles: P10/P50/P90 Scenarios', 
                    fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()
    
    def plot_annual_trajectories(self, country: str, save_path: str = None):
        """
        Plot annual trajectories for P10/P50/P90 scenarios of a country.
        """
        scenarios = self.calculate_percentile_scenarios(country)
        if not scenarios:
            print(f"No data for {country}")
            return
        
        country_data = self.df[self.df['Country code'] == country]
        country_name = self.top_hydro_countries.get(country, {}).get('name', country)
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        colors = {'P10': '#ff7f0e', 'P50': '#2ca02c', 'P90': '#1f77b4'}
        
        for percentile, info in scenarios.items():
            scenario_data = country_data[country_data['Scenario'] == info['scenario']]
            yearly_avg = scenario_data.groupby('Year')['Availability_Factor'].mean()
            
            ax.plot(yearly_avg.index, yearly_avg.values * 100, 
                   label=f'{percentile} (Scenario {info["scenario"]})',
                   color=colors[percentile], linewidth=2, marker='o', markersize=4)
        
        # Add drought threshold line
        ax.axhline(y=35, color='red', linestyle='--', alpha=0.5, label='Drought Threshold')
        
        ax.set_title(f'{country_name} - Annual Hydro Availability Trajectories', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Annual Average Availability Factor (%)', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 80)
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()
    
    def plot_risk_comparison(self, save_path: str = None):
        """
        Plot risk comparison across top hydro countries.
        """
        df = self.create_comparison_table()
        
        if len(df) == 0:
            print("No data to plot")
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Plot 1: P10-P50 Gap vs Hydro Share
        ax1 = axes[0]
        ax1.scatter(df['Hydro Share (%)'], df['P10-P50 Gap (%)'], 
                   s=100, alpha=0.6, color='#2ca02c')
        
        for idx, row in df.iterrows():
            ax1.annotate(row['ISO'], (row['Hydro Share (%)'], row['P10-P50 Gap (%)']),
                        xytext=(5, 5), textcoords='offset points', fontsize=9)
        
        ax1.set_xlabel('Hydro Share of Electricity (%)', fontsize=12)
        ax1.set_ylabel('P10-P50 Gap (percentage points)', fontsize=12)
        ax1.set_title('Hydro Dependency vs Drought Risk', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Drought Years Comparison
        ax2 = axes[1]
        x = np.arange(len(df))
        width = 0.35
        
        bars1 = ax2.bar(x - width/2, df['P10 Drought Years'], width, 
                       label='P10', color='#ff7f0e')
        bars2 = ax2.bar(x + width/2, df['P50 Drought Years'], width,
                       label='P50', color='#2ca02c')
        
        ax2.set_xlabel('Country', fontsize=12)
        ax2.set_ylabel('Number of Drought Years (in 25 years)', fontsize=12)
        ax2.set_title('Drought Frequency: P10 vs P50 Scenarios', fontsize=12, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(df['ISO'], rotation=45)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        
        plt.suptitle('Hydro Availability Risk Analysis for Top Hydro-Dependent Countries',
                    fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.show()
    
    def generate_report(self) -> str:
        """
        Generate a text report of key findings.
        """
        df = self.create_comparison_table()
        
        if len(df) == 0:
            return "No data available for analysis"
        
        report = []
        report.append("=" * 80)
        report.append("HYDRO AVAILABILITY SCENARIO ANALYSIS REPORT")
        report.append("P10/P50/P90 Profiles for Top Hydro-Dependent Countries")
        report.append("=" * 80)
        report.append("")
        
        # Summary statistics
        report.append("SUMMARY STATISTICS")
        report.append("-" * 40)
        report.append(f"Countries analyzed: {len(df)}")
        report.append(f"Average P10-P50 gap: {df['P10-P50 Gap (%)'].mean():.1f}%")
        report.append(f"Most hydro-dependent: {df.iloc[0]['Country']} ({df.iloc[0]['Hydro Share (%)']}%)")
        report.append(f"Highest drought risk: {df.loc[df['P10-P50 Gap (%)'].idxmax(), 'Country']} "
                     f"({df['P10-P50 Gap (%)'].max():.1f}% gap)")
        report.append("")
        
        # Detailed country analysis
        report.append("COUNTRY-BY-COUNTRY ANALYSIS")
        report.append("-" * 40)
        
        for _, row in df.iterrows():
            report.append(f"\n{row['Country']} ({row['ISO']})")
            report.append(f"  Hydro dependency: {row['Hydro Share (%)']}% of electricity")
            report.append(f"  Average availability: P10={row['P10 Avg (%)']}%, "
                         f"P50={row['P50 Avg (%)']}%, P90={row['P90 Avg (%)']}")
            report.append(f"  Drought risk: {row['P10-P50 Gap (%)']}% gap between P10 and P50")
            report.append(f"  P10 scenario: {row['P10 Drought Years']} drought years, "
                         f"worst at {row['P10 Worst (%)']}%")
            report.append(f"  Max consecutive drought: {row['Max Drought Length']} years")
        
        report.append("")
        report.append("KEY INSIGHTS")
        report.append("-" * 40)
        
        # High risk countries
        high_risk = df[df['P10-P50 Gap (%)'] > 10]
        if len(high_risk) > 0:
            report.append(f"High risk countries (>10% P10-P50 gap): "
                         f"{', '.join(high_risk['Country'].tolist())}")
        
        # Countries needing most backup
        high_drought = df[df['P10 Drought Years'] > 5]
        if len(high_drought) > 0:
            report.append(f"Countries with frequent droughts in P10 (>5 years): "
                         f"{', '.join(high_drought['Country'].tolist())}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


# Example usage function
def analyze_hydro_scenarios(csv_path: str):
    """
    Main function to run the complete analysis.
    
    Parameters:
    -----------
    csv_path : str
        Path to the scenarios CSV file
    """
    # Initialize analyzer
    analyzer = HydroProfileAnalyzer(csv_path)
    
    # Generate comparison table
    print("\n" + "="*80)
    print("HYDRO AVAILABILITY COMPARISON TABLE")
    print("="*80)
    comparison_df = analyzer.create_comparison_table()
    print(comparison_df.to_string(index=False))
    
    # Generate plots
    print("\nGenerating visualizations...")
    
    # 1. Monthly profiles for top countries
    analyzer.plot_monthly_profiles()
    
    # 2. Annual trajectory for Brazil (example)
    analyzer.plot_annual_trajectories('BRA')
    
    # 3. Risk comparison
    analyzer.plot_risk_comparison()
    
    # Generate text report
    report = analyzer.generate_report()
    print("\n" + report)
    
    return analyzer, comparison_df


if __name__ == "__main__":
    # Example usage
    csv_path = "hydro_scenarios_full_2025_2050.csv"
    analyzer, results = analyze_hydro_scenarios(csv_path)
    
    # Additional country-specific analysis
    print("\n" + "="*80)
    print("DETAILED DROUGHT ANALYSIS FOR BRAZIL")
    print("="*80)
    brazil_drought = analyzer.analyze_drought_characteristics('BRA')
    for percentile, stats in brazil_drought.items():
        print(f"\n{percentile} Scenario:")
        print(f"  Mean availability: {stats['mean']*100:.1f}%")
        print(f"  Drought years: {stats['drought_years']}")
        print(f"  Worst year: {stats['worst_year']*100:.1f}%")
        print(f"  Max drought length: {stats['max_drought_length']} years")