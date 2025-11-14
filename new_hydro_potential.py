"""
VerveStacks New Hydro Potential Visualization
============================================

Visualizes future hydro development potential by country using detailed project data.
Size indicates GW capacity, color indicates estimated cost per kW.

Author: VerveStacks
Date: September 2025
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.spatial.distance import cdist
import warnings
warnings.filterwarnings('ignore')

class HydroPotentialVisualizer:
    """
    Visualize hydro development potential from detailed project database.
    """
    
    def __init__(self, json_path="data/country_data/hydro_beyond_gem.json"):
        """
        Initialize with path to the hydro potential JSON file.
        
        Parameters:
        -----------
        json_path : str
            Path to the JSON file with detailed hydro project data
        """
        self.json_path = Path(json_path)
        self.data = None
        self.load_data()
        
    def load_data(self):
        """Load and parse the hydro potential JSON data."""
        try:
            print(f"Loading hydro potential data from {self.json_path}...")
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"✅ Data loaded successfully")
            print(f"   Countries available: {len(self.data['additional_potential'])}")
            
            # List available countries
            available_countries = list(self.data['additional_potential'].keys())
            iso_codes = [self.data['additional_potential'][country]['iso3'] for country in available_countries]
            print(f"   ISO codes: {', '.join(iso_codes)}")
            
        except FileNotFoundError:
            print(f"❌ Error: Could not find {self.json_path}")
            raise
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            raise
    
    def extract_country_projects(self, input_iso):
        """
        Extract all hydro projects for a specific country.
        
        Parameters:
        -----------
        input_iso : str
            ISO 3-letter country code (e.g., 'CHN', 'BRA', 'IND')
            
        Returns:
        --------
        list of dict : Project data with coordinates, capacity, and costs
        """
        # Find country by ISO code
        target_country = None
        for country_key, country_data in self.data['additional_potential'].items():
            if country_data['iso3'] == input_iso:
                target_country = country_data
                break
        
        if not target_country:
            available_isos = [self.data['additional_potential'][c]['iso3'] for c in self.data['additional_potential']]
            raise ValueError(f"Country {input_iso} not found. Available: {available_isos}")
        
        print(f"\n🏗️  Processing hydro potential for {target_country['country_name']} ({input_iso})")
        print(f"   Additional potential: {target_country['additional_potential_gw']} GW")
        
        # Extract all projects from missing_projects list
        all_projects = []
        missing_projects = target_country.get('missing_projects', [])
        
        print(f"   📍 Found {len(missing_projects)} missing projects")
        
        for project in missing_projects:
            # Handle both single values and ranges for capacity and cost
            capacity_gw = project.get('capacity_gw', 1.0)  # Default 1 GW if missing
            capacity_mw = capacity_gw * 1000  # Convert GW to MW
            
            # Read investment cost from JSON (estimated_cost_usd_per_kw)
            cost_per_kw = project.get('estimated_cost_usd_per_kw', 2000)  # Default 2000 if missing
            
            # Read AFA (Annual Availability Factor) from JSON (estimated_cf)
            estimated_cf = project.get('estimated_cf', 0.45)  # Default 45% if missing
            cf_percentage = estimated_cf * 100 if estimated_cf <= 1.0 else estimated_cf  # Handle both decimal and percentage
            cf_range = [cf_percentage * 0.9, cf_percentage * 1.1]  # Create range around the estimate
            
            project_data = {
                'name': project['name'],
                'region': project.get('basin', 'Unknown'),
                'priority': project.get('priority', 'medium'),  # Read priority from JSON
                'latitude': project.get('lat', 0.0),
                'longitude': project.get('lng', 0.0),
                'river_basin': project.get('basin', 'Unknown'),
                'capacity_mw': capacity_mw,
                'capacity_gw': capacity_mw / 1000,  # Convert to GW
                'cost_per_kw': cost_per_kw,  # Now using actual JSON value
                'cf_min': cf_range[0],
                'cf_max': cf_range[1],
                'cf_avg': cf_percentage,  # Use actual estimated CF from JSON
                'status': project.get('status', 'planned'),  # Read status from JSON
                'timeframe': project.get('timeframe', 'TBD'),  # Read timeframe from JSON
                'flow_regime': 'Seasonal',  # Default flow regime
                'notes': project.get('technical_notes', project.get('environmental_notes', ''))
            }
            all_projects.append(project_data)
        
        print(f"   ✅ Extracted {len(all_projects)} projects totaling {sum(p['capacity_gw'] for p in all_projects):.1f} GW")
        return all_projects
    
    def _extract_numeric_value(self, value):
        """Extract numeric value from various formats (single number, range, string)."""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, list) and len(value) == 2:
            # Take midpoint of range
            return np.mean(value)
        elif isinstance(value, str):
            # Try to extract number from string
            import re
            numbers = re.findall(r'\d+', value)
            if numbers:
                return float(numbers[0])
            else:
                return 1000  # Default 1 GW if can't parse
        else:
            return 1000  # Default 1 GW
    
    def _extract_cost_range(self, cost_data):
        """Extract cost estimate, handling ranges and single values."""
        if isinstance(cost_data, (int, float)):
            return float(cost_data)
        elif isinstance(cost_data, list) and len(cost_data) == 2:
            # Take midpoint of cost range
            return np.mean(cost_data)
        else:
            return 3000  # Default $3000/kW if can't parse
    
    def plot_hydro_potential(self, input_iso, save_plot=True, output_dir="source_data"):
        """
        Create visualization of hydro potential for a country.
        
        Parameters:
        -----------
        input_iso : str
            ISO 3-letter country code
        save_plot : bool
            Whether to save the plot to file
        output_dir : str
            Directory to save plots
            
        Returns:
        --------
        matplotlib.figure.Figure : The created figure
        """
        # Extract project data
        projects = self.extract_country_projects(input_iso)
        if not projects:
            print(f"❌ No projects found for {input_iso}")
            return None
        
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(projects)
        
        # Create the visualization
        plt.style.use('default')
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Plot 1: Geographic scatter plot
        scatter = ax1.scatter(
            df['longitude'], 
            df['latitude'],
            s=df['capacity_gw'] * 50,  # Size proportional to GW capacity
            c=df['cost_per_kw'],       # Color by cost per kW
            cmap='RdYlBu_r',           # Red = expensive, Blue = cheap
            alpha=0.7,
            edgecolors='black',
            linewidth=0.5
        )
        
        ax1.set_xlabel('Longitude', fontsize=12)
        ax1.set_ylabel('Latitude', fontsize=12)
        ax1.set_title(f'{input_iso} Hydro Development Potential\nGeographic Distribution', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Add colorbar for cost
        cbar = plt.colorbar(scatter, ax=ax1, shrink=0.8)
        cbar.set_label('Cost Estimate ($/kW)', fontsize=11)
        
        # Add size legend
        sizes = [1, 5, 10, 20]  # GW
        size_legend = []
        for size in sizes:
            if size <= df['capacity_gw'].max():
                size_legend.append(plt.scatter([], [], s=size*50, c='gray', alpha=0.7, edgecolors='black'))
        
        if size_legend:
            ax1.legend(size_legend, [f'{s} GW' for s in sizes[:len(size_legend)]], 
                      title='Capacity', loc='upper right', bbox_to_anchor=(1, 1))
        
        # Plot 2: Cost vs Capacity scatter
        scatter2 = ax2.scatter(
            df['capacity_gw'],
            df['cost_per_kw'],
            s=100,
            c=df['cf_avg'],  # Color by capacity factor
            cmap='viridis',
            alpha=0.7,
            edgecolors='black',
            linewidth=0.5
        )
        
        ax2.set_xlabel('Capacity (GW)', fontsize=12)
        ax2.set_ylabel('Cost Estimate ($/kW)', fontsize=12)
        ax2.set_title(f'{input_iso} Hydro Projects\nCost vs Capacity', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # Add colorbar for capacity factor
        cbar2 = plt.colorbar(scatter2, ax=ax2, shrink=0.8)
        cbar2.set_label('Avg Capacity Factor (%)', fontsize=11)
        
        # Add project labels for largest projects
        df_sorted = df.sort_values('capacity_gw', ascending=False)
        for i, row in df_sorted.head(5).iterrows():  # Label top 5 projects
            ax2.annotate(
                f"{row['name']}\n({row['capacity_gw']:.1f} GW)",
                (row['capacity_gw'], row['cost_per_kw']),
                xytext=(5, 5), textcoords='offset points',
                fontsize=8, alpha=0.8,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
            )
        
        # Add summary statistics
        total_capacity = df['capacity_gw'].sum()
        avg_cost = df['cost_per_kw'].mean()
        weighted_avg_cost = np.average(df['cost_per_kw'], weights=df['capacity_gw'])
        
        summary_text = f"""Summary for {input_iso}:
• Total Potential: {total_capacity:.1f} GW
• Projects: {len(df)}
• Avg Cost: ${avg_cost:,.0f}/kW
• Capacity-Weighted Cost: ${weighted_avg_cost:,.0f}/kW
• Cost Range: ${df['cost_per_kw'].min():,.0f} - ${df['cost_per_kw'].max():,.0f}/kW"""
        
        fig.text(0.02, 0.02, summary_text, fontsize=10, 
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)  # Make room for summary text
        
        # Save plot if requested
        if save_plot:
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            filename = output_path / f"{input_iso}_hydro_potential_analysis.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"📊 Plot saved to: {filename}")
        
        plt.show()
        return fig
    
    def get_country_summary(self, input_iso):
        """
        Get summary statistics for a country's hydro potential.
        
        Parameters:
        -----------
        input_iso : str
            ISO 3-letter country code
            
        Returns:
        --------
        dict : Summary statistics
        """
        projects = self.extract_country_projects(input_iso)
        if not projects:
            return None
        
        df = pd.DataFrame(projects)
        
        summary = {
            'country_iso': input_iso,
            'total_projects': len(df),
            'total_capacity_gw': df['capacity_gw'].sum(),
            'avg_project_size_gw': df['capacity_gw'].mean(),
            'largest_project_gw': df['capacity_gw'].max(),
            'avg_cost_per_kw': df['cost_per_kw'].mean(),
            'weighted_avg_cost_per_kw': np.average(df['cost_per_kw'], weights=df['capacity_gw']),
            'cost_range': [df['cost_per_kw'].min(), df['cost_per_kw'].max()],
            'avg_capacity_factor': df['cf_avg'].mean(),
            'priority_breakdown': df['priority'].value_counts().to_dict(),
            'status_breakdown': df['status'].value_counts().to_dict()
        }
        
        return summary
    
    def generate_hydro_tables(self, input_iso, data_source='kan', grid_modeling=True):
        """
        Generate VEDA model tables for hydro potential projects.
        
        Parameters:
        -----------
        input_iso : str
            ISO 3-letter country code
        data_source : str
            Data source for grid info ('kan' or 'cit')
        grid_modeling : bool
            Whether to use grid modeling (affects Comm-OUT)
            
        Returns:
        --------
        tuple : (fi_process_df, fi_t_df)
            Returns empty DataFrames if country not found or no projects available
        """
        print(f"\n🏗️ Generating VEDA tables for {input_iso} (data_source: {data_source})")
        
        # Extract hydro projects (handle invalid countries gracefully)
        try:
            projects = self.extract_country_projects(input_iso)
            if not projects:
                print(f"❌ No hydro projects found for {input_iso}")
                return pd.DataFrame(), pd.DataFrame()
        except ValueError as e:
            print(f"❌ {e}")
            return pd.DataFrame(), pd.DataFrame()
        
        # Load buses data for distance calculation
        buses_df = self._load_buses_data(input_iso, data_source)
        if buses_df.empty:
            print(f"⚠️ No buses data found for {input_iso}, using default distances")
            
        # Import spatial utility function
        try:
            import sys
            sys.path.append('.')
            from spatial_utils import bus_id_to_commodity
        except ImportError:
            print("⚠️ Could not import bus_id_to_commodity, using generic commodities")
            bus_id_to_commodity = lambda x: f"BUS_{x}"
        
        # Process each project
        fi_process_rows = []
        fi_t_rows = []
        used_names = set()  # Track used process names for uniqueness
        
        for i, project in enumerate(projects, 1):
            # Create short, descriptive project name
            short_name = self._create_short_name(project)
            project_id = f"EN_Hydro_{short_name}"
            
            # Ensure uniqueness by adding suffix if needed
            original_id = project_id
            counter = 1
            while project_id in used_names:
                # Add numeric suffix, keeping within reasonable length
                suffix = f"{counter:02d}"  # 01, 02, 03, etc.
                if len(original_id) + len(suffix) <= 20:  # Keep total length reasonable
                    project_id = f"{original_id}{suffix}"
                else:
                    # Truncate base name to make room for suffix
                    truncated_base = original_id[:20-len(suffix)]
                    project_id = f"{truncated_base}{suffix}"
                counter += 1
            
            used_names.add(project_id)
            
            # Calculate distance to nearest bus and associated costs
            if not buses_df.empty:
                nearest_bus, distance_km = self._find_nearest_bus(project, buses_df)
                grid_cost = 1.1 * distance_km  # $/kW for grid connection
                
                # Determine output commodity
                if grid_modeling and data_source != 'cit':
                    # Only use bus-specific commodities for real grid buses (eur/kan)
                    comm_out = bus_id_to_commodity(nearest_bus)
                else:
                    # Use generic ELC for cities (cit) or when grid_modeling is False
                    comm_out = "ELC"
            else:
                nearest_bus = "DEFAULT_BUS"
                distance_km = 10.0  # Default 10km
                grid_cost = 11.0    # Default grid cost
                comm_out = "ELC"
            
            # Create descriptive description
            description = self._create_description(project)
            
            # FI_process table entry
            fi_process_rows.append({
                'Sets': 'ELE',
                'process': project_id,
                'description': description,
                'TAct': 'TWh',
                'TCap': 'GW',
                'timeslicelevel': 'DAYNITE'
            })
            
            # FI_t table entries (single row per project with pivoted attributes)
            base_cost = project['cost_per_kw']
            capacity_gw = project['capacity_gw']
            cf_avg = project['cf_avg']
            
            # Single row with pivoted attribute~currency columns
            fi_t_rows.append({
                'process': project_id,
                'Comm-IN': 'hydro',
                'Comm-OUT': comm_out,
                'CAP_BND': capacity_gw,
                'INVCOST~USD21': base_cost,
                'INVCOST~USD21_ALT': grid_cost,
                'AFA': cf_avg / 100  # Convert percentage to decimal
            })
            
            print(f"   ✅ {project['name']}: {capacity_gw:.1f} GW, "
                  f"${base_cost:.0f}/kW + ${grid_cost:.1f}/kW grid, "
                  f"CF: {cf_avg:.1f}%, nearest bus: {nearest_bus} ({distance_km:.1f}km)")
        
        # Create DataFrames
        fi_process_df = pd.DataFrame(fi_process_rows)
        fi_t_df = pd.DataFrame(fi_t_rows)
        
        print(f"\n📊 Generated VEDA tables:")
        print(f"   ~FI_process: {len(fi_process_df)} processes")
        print(f"   ~FI_t: {len(fi_t_df)} parameter entries")
        
        return fi_process_df, fi_t_df
    
    def _load_buses_data(self, input_iso, data_source):
        """Load buses data for distance calculations."""
        buses_file = f"1_grids/output_{data_source}/{input_iso}/{input_iso}_clustered_buses.csv"
        
        try:
            buses_df = pd.read_csv(buses_file)
            print(f"   📍 Loaded {len(buses_df)} buses from {buses_file}")
            return buses_df
        except FileNotFoundError:
            print(f"   ⚠️ Buses file not found: {buses_file}")
            return pd.DataFrame()
    
    def _find_nearest_bus(self, project, buses_df):
        """Find nearest bus to a hydro project and calculate distance."""
        project_coords = np.array([[project['longitude'], project['latitude']]])
        bus_coords = buses_df[['x', 'y']].values  # x=longitude, y=latitude
        
        # Calculate distances (in degrees, approximate)
        distances = cdist(project_coords, bus_coords, metric='euclidean')[0]
        nearest_idx = np.argmin(distances)
        
        # Convert to approximate km (rough conversion: 1 degree ≈ 111 km)
        distance_km = distances[nearest_idx] * 111
        nearest_bus = buses_df.iloc[nearest_idx]['bus_id']
        
        return nearest_bus, distance_km
    
    def _create_short_name(self, project):
        """Create a short, descriptive name for the project."""
        name = project['name']
        
        # Common abbreviations and replacements
        replacements = {
            'Complex': 'Cmplx',
            'Project': 'Proj',
            'Multipurpose': 'Multi',
            'Cascade': 'Casc',
            'System': 'Sys',
            'River': 'R',
            'Basin': 'B',
            'Upper': 'Up',
            'Lower': 'Low',
            'Dam': 'D',
            'Hydropower': 'HP',
            'Power': 'P',
            'Station': 'Stn',
            'Expansion': 'Exp',
            'Development': 'Dev',
            'Tributaries': 'Trib',
            'Headwaters': 'Head'
        }
        
        # Start with the original name
        short_name = name
        
        # Apply replacements
        for full, abbrev in replacements.items():
            short_name = short_name.replace(full, abbrev)
        
        # Remove common words and clean up
        remove_words = ['the', 'of', 'and', 'for', 'in', 'at', 'on', 'to']
        words = short_name.split()
        words = [w for w in words if w.lower() not in remove_words]
        
        # Join and limit length
        short_name = ''.join(words).replace(' ', '').replace('-', '').replace('/', '')
        
        # Ensure alphanumeric only (remove any non-alphanumeric characters)
        import re
        short_name = re.sub(r'[^a-zA-Z0-9]', '', short_name)
        
        # Limit to 12 characters and ensure it's unique-ish
        if len(short_name) > 12:
            # Keep first part and last part
            short_name = short_name[:6] + short_name[-6:]
        
        return short_name[:12]  # Max 12 characters
    
    def _create_description(self, project):
        """Create a qualitative, contextual description for the project."""
        name = project['name']
        region = project['region']
        capacity_gw = project['capacity_gw']
        river_basin = project['river_basin']
        priority = project['priority']
        status = project['status']
        
        # Create contextual descriptions based on basin and region
        basin_context = self._get_basin_context(river_basin, region)
        development_context = self._get_development_context(status, priority)
        scale_context = self._get_scale_context(capacity_gw)
        
        # Build qualitative description
        description = f"{scale_context} on {river_basin} in {region}. {basin_context} {development_context}"
        
        # If too long, create shorter version
        if len(description) > 200:
            description = f"{scale_context} on {river_basin}. {basin_context} {development_context}"
        
        # Final fallback if still too long
        if len(description) > 150:
            description = f"{scale_context} on {river_basin}. {development_context}"
        
        return description
    
    def _get_basin_context(self, river_basin, region):
        """Get contextual information about the river basin."""
        basin_contexts = {
            'Amazon Basin': 'Major tributary system with high seasonal flow variability',
            'Tapajós': 'Amazon tributary with significant untapped potential in remote areas',
            'Xingu': 'Eastern Amazon tributary with indigenous territory considerations',
            'Madeira': 'Major Amazon tributary with existing cascade development',
            'Tocantins': 'Central Brazil river system with established hydro infrastructure',
            'São Francisco': 'Northeast Brazil river facing water stress challenges',
            'Parnaíba': 'Northeast river with limited but strategic potential',
            'Yarlung Tsangpo': 'Tibetan plateau river with extreme elevation and flow',
            'Jinsha': 'Upper Yangtze with steep gradients and high altitude challenges',
            'Yalong River': 'Yangtze tributary in mountainous Sichuan province',
            'Dadu River': 'Yangtze tributary with existing hydropower development',
            'Nu/Salween': 'International river with cross-border implications',
            'Lancang/Mekong': 'International Mekong headwaters with downstream impacts',
            'Drichu': 'Yangtze headwater in Tibetan autonomous region'
        }
        
        # Try exact match first, then partial matches
        for basin_key, context in basin_contexts.items():
            if basin_key.lower() in river_basin.lower():
                return context
        
        # Generic context based on region
        if 'Amazon' in region or 'Brazil' in region:
            return 'Tropical river system with seasonal flow patterns'
        elif 'Tibet' in region or 'China' in region:
            return 'High-altitude river system with steep gradients'
        else:
            return 'River system with hydropower development potential'
    
    def _get_development_context(self, status, priority):
        """Get contextual information about development status and priority."""
        status_contexts = {
            'Under construction': 'Currently under active construction',
            'Planning phase': 'In detailed planning and design phase',
            'Construction resumed': 'Construction restarted after delays',
            'Environmental clearance': 'Awaiting environmental approvals',
            'Feasibility study': 'Undergoing technical and economic assessment',
            'Early planning': 'In preliminary development stages',
            'Planned': 'Approved for future development',
            'Long-term': 'Identified for long-term strategic development',
            'Multiple projects': 'Part of larger cascade development program',
            'Cascade potential': 'Suitable for multi-stage cascade development',
            'Suspended': 'Development currently suspended',
            'Licensing suspended': 'Regulatory approvals temporarily halted'
        }
        
        priority_contexts = {
            'Ultra High': 'Strategic national priority project',
            'High': 'High development priority',
            'Medium-High': 'Important regional development target',
            'Medium': 'Moderate development priority',
            'Low': 'Lower priority development option'
        }
        
        status_desc = status_contexts.get(status, f'Status: {status}')
        priority_desc = priority_contexts.get(priority, '')
        
        if priority_desc:
            return f"{priority_desc}. {status_desc}"
        else:
            return status_desc
    
    def _get_scale_context(self, capacity_gw):
        """Get contextual description of project scale."""
        if capacity_gw >= 20:
            return "Mega-scale hydropower complex"
        elif capacity_gw >= 10:
            return "Large-scale hydropower project"
        elif capacity_gw >= 5:
            return "Major hydropower development"
        elif capacity_gw >= 1:
            return "Medium-scale hydropower facility"
        else:
            return "Small-scale hydropower project"

    def list_available_countries(self):
        """List all available countries in the database."""
        print("\n🌍 Available Countries in Hydro Potential Database:")
        print("=" * 60)
        
        for country_key, country_data in self.data['additional_potential'].items():
            iso = country_data['iso3']
            name = country_data['country_name']
            potential = country_data['additional_potential_gw']
            projects = len(country_data.get('missing_projects', []))
            
            print(f"  {iso}: {name}")
            print(f"      Potential: {potential} GW, Projects: {projects}")
        
        print("=" * 60)


def main():
    """Example usage of the HydroPotentialVisualizer."""
    
    # Initialize visualizer
    viz = HydroPotentialVisualizer()
    
    # List available countries
    viz.list_available_countries()
    
    # Example: Generate VEDA tables for Brazil
    print("\n" + "="*60)
    print("EXAMPLE: Generating VEDA Tables for Brazil")
    print("="*60)
    
    try:
        # Generate VEDA tables with grid modeling
        fi_process_df, fi_t_df = viz.generate_hydro_tables('CAN', data_source='kan', grid_modeling=True)
        
        if not fi_process_df.empty:
            print("\n📋 ~FI_process Table:")
            print("=" * 80)
            print(fi_process_df.to_string(index=False))
            
            print("\n📋 ~FI_t Table:")
            print("=" * 80)
            print(fi_t_df.to_string(index=False))
            
            # Show summary statistics
            print(f"\n📊 Summary Statistics:")
            print(f"   Total projects: {len(fi_process_df)}")
            print(f"   Total capacity: {fi_t_df['CAP_BND'].sum():.1f} GW")
            
            # Cost breakdown by currency
            avg_base_cost = fi_t_df['INVCOST~USD21'].mean()
            avg_grid_cost = fi_t_df['INVCOST~USD21_ALT'].mean()
            avg_cf = fi_t_df['CF'].mean()
            
            print(f"   Average base cost (USD21): ${avg_base_cost:.1f}/kW")
            print(f"   Average grid cost (USD21_ALT): ${avg_grid_cost:.1f}/kW")
            print(f"   Average capacity factor: {avg_cf:.1%}")
        
    except Exception as e:
        print(f"❌ Error generating VEDA tables for Brazil: {e}")
        print("   Trying with default parameters...")
        
        try:
            # Fallback without grid modeling
            fi_process_df, fi_t_df = viz.generate_hydro_tables('BRA', data_source='kan', grid_modeling=False)
            if not fi_process_df.empty:
                print("\n📋 Fallback Tables Generated Successfully")
                print(f"   Processes: {len(fi_process_df)}")
                print(f"   Parameters: {len(fi_t_df)}")
        except Exception as e2:
            print(f"❌ Fallback also failed: {e2}")


if __name__ == "__main__":
    main()
