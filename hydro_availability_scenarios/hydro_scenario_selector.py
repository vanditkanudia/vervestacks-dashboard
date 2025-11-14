import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
import warnings

class ScenarioSelector:
    """
    Select representative hydro scenarios (P10/P50/P90) for any country
    from synthetic hydro availability data.
    """
    
    def __init__(self, csv_path: str,auto_calculate_metrics=False):
        """
        Initialize with path to the full scenarios CSV file.
        
        Parameters:
        -----------
        csv_path : str
            Path to the CSV file with all scenarios (not the summary file!)
        """
        print(f"Loading data from {csv_path}...")
        self.df = pd.read_csv(csv_path)
        self.validate_data()
        if auto_calculate_metrics:
            self.calculate_scenario_metrics()
        
    def validate_data(self):
        """Validate that the loaded data has the expected structure."""
        required_cols = ['Country code', 'Year', 'Month', 'Scenario', 'Availability_Factor']
        missing_cols = [col for col in required_cols if col not in self.df.columns]
        
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        print(f"Data loaded successfully:")
        print(f"  - Countries: {self.df['Country code'].nunique()}")
        print(f"  - Scenarios: {self.df['Scenario'].nunique()}")
        print(f"  - Years: {self.df['Year'].min()} to {self.df['Year'].max()}")
        print(f"  - Total rows: {len(self.df):,}")
        
    def calculate_scenario_metrics(self, iso_filter=None):
        """Pre-calculate metrics for all scenarios and countries."""
        self.scenario_metrics = {}
        
        countries = [iso_filter] if iso_filter else self.df['Country code'].unique()
        for country in countries:
            country_data = self.df[self.df['Country code'] == country]
            if country_data.empty:
                continue
            metrics = []
            
            for scenario_id in country_data['Scenario'].unique():
                scenario_data = country_data[country_data['Scenario'] == scenario_id]
                
                # Calculate various metrics
                yearly_avg = scenario_data.groupby('Year')['Availability_Factor'].mean()
                
                metrics.append({
                    'scenario': scenario_id,
                    'mean_af': scenario_data['Availability_Factor'].mean(),
                    'median_af': scenario_data['Availability_Factor'].median(),
                    'std_af': scenario_data['Availability_Factor'].std(),
                    'min_af': scenario_data['Availability_Factor'].min(),
                    'max_af': scenario_data['Availability_Factor'].max(),
                    'worst_year': yearly_avg.min(),
                    'best_year': yearly_avg.max(),
                    'drought_years': (yearly_avg < 0.35).sum(),
                    'severe_drought_years': (yearly_avg < 0.30).sum(),
                    'wet_years': (yearly_avg > 0.45).sum(),
                    'cumulative_deficit': ((0.40 - yearly_avg).clip(lower=0)).sum(),
                    'volatility': yearly_avg.std()
                })
            
            self.scenario_metrics[country] = pd.DataFrame(metrics)
        
        print(f"Metrics calculated for {len(self.scenario_metrics)} countries")
    
    def get_scenario(self, country_code: str, percentile: str, 
                    ranking_method: str = 'cumulative_deficit') -> Dict:
        """
        Get the scenario number for a given country and percentile.
        
        Parameters:
        -----------
        country_code : str
            ISO 3-letter country code (e.g., 'BRA', 'USA', 'CHN')
        percentile : str
            One of 'P10', 'P50', 'P90' (or just '10', '50', '90')
        ranking_method : str
            Method to rank scenarios:
            - 'cumulative_deficit': Total deficit below normal (default)
            - 'mean_af': Simple mean availability factor
            - 'drought_years': Number of drought years
            - 'worst_year': Severity of worst year
            
        Returns:
        --------
        dict with scenario information
        """
        # Validate inputs
        if country_code not in self.scenario_metrics:
            available = sorted(self.scenario_metrics.keys())
            raise ValueError(f"Country '{country_code}' not found. Available: {available}")
        
        # Parse percentile
        percentile = percentile.upper().replace('P', '')
        if percentile not in ['10', '50', '90']:
            raise ValueError(f"Percentile must be P10, P50, or P90, got: P{percentile}")
        
        # Get country metrics
        country_metrics = self.scenario_metrics[country_code].copy()
        
        # Sort by chosen method (higher deficit = drier = lower percentile)
        if ranking_method in ['cumulative_deficit', 'drought_years', 'severe_drought_years']:
            ascending = False  # Higher values = drier
        else:
            ascending = True   # Lower values = drier
            
        country_metrics = country_metrics.sort_values(ranking_method, ascending=ascending)
        
        # Select percentile
        n_scenarios = len(country_metrics)
        if percentile == '10':
            idx = int(n_scenarios * 0.10) - 1  # 10th percentile (dry)
        elif percentile == '50':
            idx = int(n_scenarios * 0.50) - 1  # 50th percentile (median)
        else:  # P90
            idx = int(n_scenarios * 0.90) - 1  # 90th percentile (wet)
        
        idx = max(0, min(idx, n_scenarios - 1))  # Bounds check
        
        selected = country_metrics.iloc[idx]
        
        return {
            'country': country_code,
            'percentile': f'P{percentile}',
            'scenario_number': int(selected['scenario']),
            'mean_availability': round(selected['mean_af'], 3),
            'worst_year': round(selected['worst_year'], 3),
            'best_year': round(selected['best_year'], 3),
            'drought_years': int(selected['drought_years']),
            'volatility': round(selected['volatility'], 3),
            'ranking_method': ranking_method
        }
    
    def get_all_percentiles(self, country_code: str, 
                           ranking_method: str = 'cumulative_deficit') -> Dict:
        """
        Get P10, P50, and P90 scenarios for a country at once.
        
        Parameters:
        -----------
        country_code : str
            ISO 3-letter country code
        ranking_method : str
            Method to rank scenarios
            
        Returns:
        --------
        dict with P10, P50, P90 scenario information
        """
        return {
            'P10': self.get_scenario(country_code, 'P10', ranking_method),
            'P50': self.get_scenario(country_code, 'P50', ranking_method),
            'P90': self.get_scenario(country_code, 'P90', ranking_method)
        }
    
    def extract_scenario_data(self, country_code: str, scenario_number: int) -> pd.DataFrame:
        """
        Extract the actual time series data for a specific scenario.
        
        Parameters:
        -----------
        country_code : str
            ISO 3-letter country code
        scenario_number : int
            Scenario number to extract
            
        Returns:
        --------
        DataFrame with the scenario data
        """
        return self.df[(self.df['Country code'] == country_code) & 
                      (self.df['Scenario'] == str(scenario_number))].copy()
    
    def compare_percentiles(self, country_code: str) -> pd.DataFrame:
        """
        Create a comparison table of P10/P50/P90 scenarios for a country.
        
        Parameters:
        -----------
        country_code : str
            ISO 3-letter country code
            
        Returns:
        --------
        DataFrame comparing the three scenarios
        """
        percentiles = self.get_all_percentiles(country_code)
        
        comparison = []
        for p_level, info in percentiles.items():
            scenario_data = self.extract_scenario_data(country_code, info['scenario_number'])
            yearly = scenario_data.groupby('Year')['Availability_Factor'].mean()
            
            comparison.append({
                'Percentile': p_level,
                'Scenario #': info['scenario_number'],
                'Mean AF': f"{info['mean_availability']:.1%}",
                'Worst Year': f"{info['worst_year']:.1%}",
                'Best Year': f"{info['best_year']:.1%}",
                'Drought Years': info['drought_years'],
                'Years <30%': (yearly < 0.30).sum(),
                'Years >45%': (yearly > 0.45).sum(),
                'Volatility': f"{info['volatility']:.1%}"
            })
        
        return pd.DataFrame(comparison)
    
    def plot_scenarios(self, country_code: str, save_path: Optional[str] = None):
        """
        Plot P10/P50/P90 scenarios for visual comparison.
        
        Parameters:
        -----------
        country_code : str
            ISO 3-letter country code
        save_path : str, optional
            Path to save the plot
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not installed. Install with: pip install matplotlib")
            return
        
        percentiles = self.get_all_percentiles(country_code)
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        colors = {'P10': 'orangered', 'P50': 'steelblue', 'P90': 'forestgreen'}
        
        for idx, (p_level, info) in enumerate(percentiles.items()):
            scenario_data = self.extract_scenario_data(country_code, info['scenario_number'])
            
            # Calculate monthly and annual averages
            monthly = scenario_data.pivot_table(
                index=['Year', 'Month'], 
                values='Availability_Factor', 
                aggfunc='mean'
            ).reset_index()
            monthly['Date'] = pd.to_datetime(monthly[['Year', 'Month']].assign(day=1))
            
            yearly = scenario_data.groupby('Year')['Availability_Factor'].mean()
            
            # Plot monthly as thin line
            axes[idx].plot(monthly['Date'], monthly['Availability_Factor'], 
                          alpha=0.3, color=colors[p_level], linewidth=0.5)
            
            # Plot annual average as thick line
            yearly_dates = pd.to_datetime(yearly.index.astype(str) + '-07-01')
            axes[idx].plot(yearly_dates, yearly.values, 
                          color=colors[p_level], linewidth=2, 
                          label=f'Annual Average')
            
            # Add reference lines
            axes[idx].axhline(y=0.35, color='red', linestyle='--', 
                             alpha=0.5, label='Drought Threshold')
            axes[idx].axhline(y=0.40, color='gray', linestyle=':', 
                             alpha=0.5, label='Normal')
            
            # Formatting
            axes[idx].set_title(
                f'{p_level} Scenario #{info["scenario_number"]} - '
                f'{country_code} (Mean: {info["mean_availability"]:.1%})',
                fontsize=12, fontweight='bold'
            )
            axes[idx].set_ylabel('Availability Factor')
            axes[idx].set_ylim(0.15, 0.65)
            axes[idx].grid(True, alpha=0.3)
            axes[idx].legend(loc='upper right')
            
            if idx == 2:
                axes[idx].set_xlabel('Year')
        
        plt.suptitle(f'Hydro Availability Scenarios for {country_code}', 
                    fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        
        plt.show()
    
    def get_available_countries(self) -> List[str]:
        """Get list of all available country codes."""
        # Filter out any NaN values and sort
        countries = [k for k in self.scenario_metrics.keys() if pd.notna(k)]
        return sorted(countries)
    
    def get_hydro_capacity_factors(self, iso_code: str, scenario_type: str = 'P50',
                                  ranking_method: str = 'cumulative_deficit') -> pd.DataFrame:
        """
        Get hydro capacity factors using sophisticated scenario selection.
        
        Parameters:
        -----------
        iso_code : str
            3-letter ISO country code
        scenario_type : str
            Scenario type: 'P10' (driest), 'P50' (median), 'P90' (wettest)
        ranking_method : str
            Method to rank scenarios: 'cumulative_deficit', 'mean_af', 'drought_years', 'worst_year'
        
        Returns:
        --------
        pd.DataFrame
            Columns: ['Year', 'Month', 'Capacity_Factor']
        """
        try:
            # Get the selected scenario
            scenario_info = self.get_scenario(iso_code, scenario_type, ranking_method)
            scenario_number = scenario_info['scenario_number']
            
            # Extract the scenario data
            scenario_data = self.extract_scenario_data(iso_code, scenario_number)
            
            # Return the data in the expected format
            result_df = scenario_data[['Year', 'Month', 'Availability_Factor']].copy()
            result_df.rename(columns={'Availability_Factor': 'Capacity_Factor'}, inplace=True)
            
            # Sort by year and month for consistency
            result_df = result_df.sort_values(['Year', 'Month']).reset_index(drop=True)
            
            return result_df
            
        except ValueError as e:
            # If country not found, return empty DataFrame
            print(f"Warning: {e}")
            return pd.DataFrame(columns=['Year', 'Month', 'Capacity_Factor'])
        except Exception as e:
            print(f"Error getting hydro capacity factors for {iso_code}: {e}")
            return pd.DataFrame(columns=['Year', 'Month', 'Capacity_Factor'])


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def main():
    """Example usage of the ScenarioSelector class."""
    
    # Initialize with your CSV file
    selector = ScenarioSelector('hydro_scenarios_full_2025_2050.csv',auto_calculate_metrics=False)
    
    # Example 1: Get a single scenario
    print("\n" + "="*60)
    print("EXAMPLE 1: Get P50 scenario for Brazil")
    print("="*60)
    result = selector.get_scenario('BRA', 'P50')
    print(f"Brazil P50 Scenario: #{result['scenario_number']}")
    print(f"  Mean availability: {result['mean_availability']:.1%}")
    print(f"  Worst year: {result['worst_year']:.1%}")
    print(f"  Drought years: {result['drought_years']}")
    
    # Example 2: Get all percentiles for a country
    print("\n" + "="*60)
    print("EXAMPLE 2: Get all percentiles for China")
    print("="*60)
    china_scenarios = selector.get_all_percentiles('CHN')
    for p_level, info in china_scenarios.items():
        print(f"{p_level}: Scenario #{info['scenario_number']} "
              f"(mean: {info['mean_availability']:.1%})")
    
    # Example 3: Compare scenarios in a table
    print("\n" + "="*60)
    print("EXAMPLE 3: Comparison table for Canada")
    print("="*60)
    comparison = selector.compare_percentiles('CAN')
    print(comparison.to_string(index=False))
    
    # Example 4: Extract actual data for planning
    print("\n" + "="*60)
    print("EXAMPLE 4: Extract P10 scenario data for USA")
    print("="*60)
    usa_p10 = selector.get_scenario('USA', 'P10')
    usa_p10_data = selector.extract_scenario_data('USA', usa_p10['scenario_number'])
    print(f"USA P10 Scenario #{usa_p10['scenario_number']} - First 12 months:")
    print(usa_p10_data[['Year', 'Month', 'Availability_Factor']].head(12))
    
    # Example 5: Try different ranking methods
    print("\n" + "="*60)
    print("EXAMPLE 5: Different ranking methods for Norway")
    print("="*60)
    methods = ['cumulative_deficit', 'mean_af', 'drought_years', 'worst_year']
    for method in methods:
        result = selector.get_scenario('NOR', 'P10', ranking_method=method)
        print(f"P10 by {method:20s}: Scenario #{result['scenario_number']:3d} "
              f"(mean: {result['mean_availability']:.1%})")
    
    # Example 6: List all available countries
    print("\n" + "="*60)
    print("EXAMPLE 6: Available countries")
    print("="*60)
    countries = selector.get_available_countries()
    print(f"Total countries available: {len(countries)}")
    print(f"Countries: {', '.join(countries[:10])}...")
    
    # Example 7: Plot scenarios (if matplotlib is installed)
    print("\n" + "="*60)
    print("EXAMPLE 7: Plotting scenarios")
    print("="*60)
    try:
        selector.plot_scenarios('BRA','/output/hydro_availability_scenarios/brazil_scenarios.png')
    except:
        print("Plotting skipped (matplotlib may not be installed)")


# ============================================================================
# STANDALONE FUNCTION FOR VERVESTACKS INTEGRATION
# ============================================================================

def get_hydro_capacity_factors(iso_code: str, ranking_method: str = 'cumulative_deficit',
                              scenario_file: str = 'hydro_availability_scenarios/hydro_scenarios_full_2025_2050.csv') -> pd.DataFrame:
    """
    Standalone function to get hydro capacity factors for VerveStacks integration.
    
    This function can be imported and used directly from time_slice_processor.py
    
    Parameters:
    -----------
    iso_code : str
        3-letter ISO country code
    ranking_method : str
        Method to rank scenarios: 'cumulative_deficit', 'mean_af', 'drought_years', 'worst_year'
    scenario_file : str
        Path to the hydro scenarios CSV file
    
    Returns:
    --------
    pd.DataFrame
        Columns: ['Year', 'Month', 'P10', 'P50', 'P90']
    """
    try:
        # Initialize the scenario selector with ISO filter for faster metrics calculation
        selector = ScenarioSelector(scenario_file)
        selector.calculate_scenario_metrics(iso_filter=iso_code)
        
        # Get all three scenarios using original logic
        p10_df = selector.get_hydro_capacity_factors(iso_code, 'P10', ranking_method)
        p50_df = selector.get_hydro_capacity_factors(iso_code, 'P50', ranking_method)
        p90_df = selector.get_hydro_capacity_factors(iso_code, 'P90', ranking_method)
        
        # Merge all scenarios into one DataFrame
        scenario_df = p50_df[['Year', 'Month']].copy()
        scenario_df['P10'] = p10_df['Capacity_Factor']
        scenario_df['P50'] = p50_df['Capacity_Factor']
        scenario_df['P90'] = p90_df['Capacity_Factor']
        
        # Add historical data from scenario 'Historical' (years 2020-2022)
        historical_data = selector.df[
            (selector.df['Country code'] == iso_code) & 
            (selector.df['Scenario'] == 'Historical') & 
            (selector.df['Year'].isin([2020, 2021, 2022]))
        ].copy()
        
        if not historical_data.empty:
            # Create historical DataFrame with same structure
            historical_df = historical_data[['Year', 'Month']].copy()
            historical_df['P10'] = historical_data['Availability_Factor'].values
            historical_df['P50'] = historical_data['Availability_Factor'].values
            historical_df['P90'] = historical_data['Availability_Factor'].values
            
            # Combine scenario data with historical data
            result_df = pd.concat([historical_df, scenario_df], ignore_index=True)
            result_df = result_df.sort_values(['Year', 'Month']).reset_index(drop=True)
        else:
            result_df = scenario_df
        
        print(f"Data loaded for {iso_code}: {len(result_df)} records (including historical)")
        return result_df
        
    except Exception as e:
        print(f"Error in get_hydro_capacity_factors: {e}")
        return pd.DataFrame(columns=['Year', 'Month', 'P10', 'P50', 'P90'])


if __name__ == "__main__":
    # Interactive mode - show Brazil data
    print("="*60)
    print("HYDRO CAPACITY FACTORS - BRAZIL EXAMPLE")
    print("="*60)
    
    # Get Brazil data
    print("Loading Brazil hydro capacity factors...")
    brazil_df = get_hydro_capacity_factors('BRA', scenario_file='hydro_scenarios_full_2025_2050.csv',auto_calculate_metrics=False)
    
    print(f"\nBrazil Data Summary:")
    print(f"Shape: {brazil_df.shape}")
    print(f"Columns: {brazil_df.columns.tolist()}")
    print(f"Year range: {brazil_df['Year'].min()} to {brazil_df['Year'].max()}")
    
    print(f"\nFirst 15 rows (Historical + Early Future):")
    print(brazil_df.head(15))
    
    print(f"\nLast 10 rows (Recent Future):")
    print(brazil_df.tail(10))
    
    # Check if P10/P50/P90 are different
    historical_data = brazil_df[brazil_df['Year'] <= 2022]
    future_data = brazil_df[brazil_df['Year'] > 2022]
    
    print(f"\nData Analysis:")
    print(f"Historical records (2020-2022): {len(historical_data)}")
    print(f"Future scenario records: {len(future_data)}")
    
    if not historical_data.empty:
        hist_identical = (historical_data['P10'] == historical_data['P50']).all() and (historical_data['P50'] == historical_data['P90']).all()
        print(f"Historical P10/P50/P90 identical: {hist_identical}")
    
    if not future_data.empty:
        future_identical = (future_data['P10'] == future_data['P50']).all() and (future_data['P50'] == future_data['P90']).all()
        print(f"Future P10/P50/P90 identical: {future_identical}")
        
        if not future_identical:
            print(f"\nFuture scenario sample (showing different P10/P50/P90):")
            sample_future = future_data.head(5)
            print(sample_future)
    
    print("\n" + "="*60)
    print("INTERACTIVE MODE")
    print("="*60)
    print("\nYou can now use the function interactively:")
    print("  result = get_hydro_capacity_factors('BRA')")
    print("  result = get_hydro_capacity_factors('USA')")
    print("  result = get_hydro_capacity_factors('CHN')")
    print("\nOr use the selector class directly:")
    print("  selector = ScenarioSelector('hydro_scenarios_full_2025_2050.csv')")
    print("  scenario = selector.get_scenario('BRA', 'P50')")
    print("  print(scenario['scenario_number'])")
