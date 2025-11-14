"""
VerveStacks README Generator
Unified system for generating README documentation from YAML templates
Supports: core processing, timeslice analysis, grid modeling, AR6 scenarios
"""

import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import re


class ReadmeGenerator:
    """Generate README content from YAML templates and processing data"""
    
    def __init__(self, config_file="../config/readme_documentation.yaml"):
        """Initialize with YAML configuration"""
        self.config_file = Path(config_file)
        self.config = self.load_config()
    
    def load_config(self):
        """Load YAML configuration"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading README config: {e}")
            return {}
    
    def calculate_ar6_insights(self, r10_region, ar6_data, iso_code):
        """Calculate key statistics for AR6 README content"""
        
        insights = {
            'r10_region': r10_region,
            'iso_code': iso_code,
            'country_count': 'multiple',  # Could be calculated from mapping
            'scenario_model_count': len(ar6_data) // 35 if len(ar6_data) > 0 else 0,  # Rough estimate
            'total_scenario_models': len(ar6_data) // 35 if len(ar6_data) > 0 else 0
        }
        
        try:
            # CO2 price analysis
            co2_data = ar6_data[ar6_data['attribute'] == 'CO2 price']
            if len(co2_data) > 0:
                insights['co2_2030_c1_median'] = self.get_stat(co2_data, 'C1', 2030, 'median', 0)
                insights['co2_2030_c7_median'] = self.get_stat(co2_data, 'C7', 2030, 'median', 0)
                insights['co2_2050_c1_median'] = self.get_stat(co2_data, 'C1', 2050, 'median', 0)
                insights['co2_2050_c7_median'] = self.get_stat(co2_data, 'C7', 2050, 'median', 0)
                insights['co2_cv'] = self.calculate_cv(co2_data)
            
            # Electricity growth analysis  
            elec_data = ar6_data[ar6_data['attribute'] == 'Electricity growth relative to 2020']
            if len(elec_data) > 0:
                insights['elec_growth_2050_c1'] = self.get_stat(elec_data, 'C1', 2050, 'median', 1.0)
                insights['elec_growth_2050_c7'] = self.get_stat(elec_data, 'C7', 2050, 'median', 1.0)
                insights['elec_cv'] = self.calculate_cv(elec_data)
            
            # Hydrogen analysis
            hydrogen_data = ar6_data[ar6_data['attribute'] == 'Hydrogen as a share of electricity']
            if len(hydrogen_data) > 0:
                insights['hydrogen_2050_c1_median'] = self.get_stat(hydrogen_data, 'C1', 2050, 'median', 0) * 100
                insights['hydrogen_2050_c7_median'] = self.get_stat(hydrogen_data, 'C7', 2050, 'median', 0) * 100
                insights['hydrogen_cv'] = self.calculate_cv(hydrogen_data)
            
            # Transport electrification analysis
            transport_data = ar6_data[ar6_data['attribute'] == 'Transportation electricity share']
            if len(transport_data) > 0:
                insights['transport_2020_median'] = self.get_stat(transport_data, 'C1', 2020, 'median', 0) * 100
                insights['transport_2050_c1_median'] = self.get_stat(transport_data, 'C1', 2050, 'median', 0) * 100
                insights['transport_growth_factor'] = insights['transport_2050_c1_median'] / max(insights['transport_2020_median'], 0.1)
                insights['transport_cv'] = self.calculate_cv(transport_data)
            
            # Add descriptive text based on statistics
            insights.update(self.generate_descriptive_text(insights, r10_region))
            
        except Exception as e:
            print(f"⚠️  Error calculating AR6 insights: {e}")
            # Provide defaults
            insights.update({
                'co2_2030_c1_median': 100, 'co2_2030_c7_median': 20,
                'co2_2050_c1_median': 300, 'co2_2050_c7_median': 50,
                'elec_growth_2050_c1': 2.5, 'elec_growth_2050_c7': 1.5,
                'hydrogen_2050_c1_median': 15, 'hydrogen_2050_c7_median': 3,
                'transport_2020_median': 2, 'transport_2050_c1_median': 25,
                'transport_growth_factor': 12.5,
                'co2_cv': 45, 'elec_cv': 25, 'hydrogen_cv': 85, 'transport_cv': 55
            })
            insights.update(self.generate_descriptive_text(insights, r10_region))
        
        return insights
    
    def get_stat(self, data, category, year, stat_col, default=0):
        """Get a specific statistic from AR6 data"""
        try:
            filtered = data[(data['Category'] == category) & (data['Year'] == year)]
            if len(filtered) > 0:
                return float(filtered[stat_col].iloc[0])
            return default
        except:
            return default
    
    def calculate_cv(self, data):
        """Calculate coefficient of variation (CV) for uncertainty measure"""
        try:
            if 'std' in data.columns and 'median' in data.columns:
                cv_values = (data['std'] / data['median'].replace(0, np.nan)) * 100
                return float(cv_values.median())
            return 50.0  # Default moderate uncertainty
        except:
            return 50.0
    
    def generate_descriptive_text(self, insights, r10_region):
        """Generate descriptive text based on calculated statistics"""
        
        descriptions = {}
        
        # CO2 price descriptions
        price_ratio = insights.get('co2_2050_c1_median', 300) / max(insights.get('co2_2050_c7_median', 50), 1)
        if price_ratio > 5:
            descriptions['price_volatility_description'] = "high price sensitivity to climate ambition"
            descriptions['uncertainty_range_description'] = "wide uncertainty bands"
            descriptions['model_agreement_level'] = "moderate consensus"
        else:
            descriptions['price_volatility_description'] = "moderate price sensitivity"
            descriptions['uncertainty_range_description'] = "narrow uncertainty bands"
            descriptions['model_agreement_level'] = "strong consensus"
        
        # Electrification descriptions
        elec_ratio = insights.get('elec_growth_2050_c1', 2.5) / max(insights.get('elec_growth_2050_c7', 1.5), 1)
        if elec_ratio > 1.5:
            descriptions['electrification_pattern'] = "aggressive electrification under ambitious scenarios"
            descriptions['demand_uncertainty'] = "significant variation"
        else:
            descriptions['electrification_pattern'] = "steady electrification across all scenarios"
            descriptions['demand_uncertainty'] = "moderate variation"
        
        # Hydrogen descriptions
        h2_level = insights.get('hydrogen_2050_c1_median', 15)
        if h2_level > 20:
            descriptions['hydrogen_volatility'] = "high deployment uncertainty"
            descriptions['hydrogen_regional_pattern'] = "strong hydrogen economy potential"
        elif h2_level > 10:
            descriptions['hydrogen_volatility'] = "moderate deployment uncertainty"
            descriptions['hydrogen_regional_pattern'] = "emerging hydrogen applications"
        else:
            descriptions['hydrogen_volatility'] = "limited deployment consensus"
            descriptions['hydrogen_regional_pattern'] = "niche hydrogen applications"
        
        # Transport descriptions
        transport_growth = insights.get('transport_growth_factor', 10)
        if transport_growth > 15:
            descriptions['transport_uncertainty'] = "high transformation uncertainty"
            descriptions['transport_divergence_description'] = "dramatic differences"
        elif transport_growth > 8:
            descriptions['transport_uncertainty'] = "moderate transformation uncertainty"
            descriptions['transport_divergence_description'] = "significant differences"
        else:
            descriptions['transport_uncertainty'] = "low transformation uncertainty"
            descriptions['transport_divergence_description'] = "modest differences"
        
        # Regional characteristics
        region_patterns = {
            'R10EUROPE': {
                'regional_convergence_pattern': 'higher model consensus',
                'regional_specific_insights': 'aggressive renewable deployment and electrification targets',
                'regional_context_factors': 'strong climate policies and renewable resource availability'
            },
            'R10NORTH_AM': {
                'regional_convergence_pattern': 'moderate model consensus',
                'regional_specific_insights': 'technology-driven transformation with market mechanisms',
                'regional_context_factors': 'diverse energy resources and federal-state policy dynamics'
            },
            'R10CHINA+': {
                'regional_convergence_pattern': 'lower model consensus',
                'regional_specific_insights': 'rapid industrial electrification and hydrogen development',
                'regional_context_factors': 'centralized planning and manufacturing scale advantages'
            }
        }
        
        regional_info = region_patterns.get(r10_region, {
            'regional_convergence_pattern': 'moderate model consensus',
            'regional_specific_insights': 'balanced transformation across sectors',
            'regional_context_factors': 'diverse economic and policy conditions'
        })
        
        descriptions.update(regional_info)
        
        return descriptions
    
    def extract_clustering_metrics(self, iso_code, data_source):
        """Extract renewable energy clustering statistics from cluster_summary CSV files"""
        clustering_metrics = {}
        
        # Define the clustering output directory based on data_source
        cluster_output_dir = Path(f"1_grids/output_{data_source}/{iso_code}")
        if not cluster_output_dir.exists():
            print(f"⚠️  Clustering output directory not found: {cluster_output_dir}")
            return clustering_metrics
        
        # Try to find cluster summary files for different technologies
        technologies = ['solar', 'wind_onshore', 'wind_offshore']
        tech_data = {}
        
        for tech in technologies:
            # Look for technology-specific cluster summary files - try multiple naming patterns
            cluster_file_patterns = [
                cluster_output_dir / f"cluster_summary_{iso_code}_{tech}.csv",  # cluster_summary_CHN_solar.csv
                cluster_output_dir / f"cluster_summary_{tech}.csv",             # cluster_summary_solar.csv
                cluster_output_dir / f"cluster_summary_{iso_code}.csv"          # cluster_summary_CHN.csv (generic)
            ]
            
            cluster_file = None
            for pattern in cluster_file_patterns:
                if pattern.exists():
                    cluster_file = pattern
                    break
            
            if cluster_file is not None:
                try:
                    df_clusters = pd.read_csv(cluster_file)
                    
                    # Extract key statistics
                    n_clusters = len(df_clusters)
                    total_cells = df_clusters['n_cells'].sum()
                    avg_cluster_size = df_clusters['n_cells'].mean()
                    min_cluster_size = df_clusters['n_cells'].min()
                    max_cluster_size = df_clusters['n_cells'].max()
                    
                    # Extract capacity factor statistics
                    if 'avg_solar_cf' in df_clusters.columns:
                        solar_cf_min = df_clusters['avg_solar_cf'].min() * 100
                        solar_cf_max = df_clusters['avg_solar_cf'].max() * 100
                        solar_cf_avg = df_clusters['avg_solar_cf'].mean() * 100
                        tech_data['solar'] = {
                            'cf_min': solar_cf_min, 'cf_max': solar_cf_max, 'cf_avg': solar_cf_avg
                        }
                    
                    if 'avg_wind_cf' in df_clusters.columns:
                        wind_cf_min = df_clusters['avg_wind_cf'].min() * 100
                        wind_cf_max = df_clusters['avg_wind_cf'].max() * 100
                        wind_cf_avg = df_clusters['avg_wind_cf'].mean() * 100
                        tech_data['wind'] = {
                            'cf_min': wind_cf_min, 'cf_max': wind_cf_max, 'cf_avg': wind_cf_avg
                        }
                    
                    # Store general clustering metrics (use first file found)
                    if not clustering_metrics:
                        clustering_metrics.update({
                            'n_clusters': n_clusters,
                            'total_grid_cells': total_cells,
                            'avg_cluster_size': round(avg_cluster_size, 1),
                            'min_cluster_size': min_cluster_size,
                            'max_cluster_size': max_cluster_size,
                            'cluster_size_range': f"{min_cluster_size} to {max_cluster_size}",
                            'data_source': data_source,
                            'data_source_description': self._get_data_source_description(data_source)
                        })
                    
                    print(f"✅ Loaded clustering data for {tech}: {n_clusters} clusters, {total_cells} grid cells")
                    break  # Use first successful file
                    
                except Exception as e:
                    print(f"⚠️  Error reading cluster file {cluster_file}: {e}")
                    continue
        
        # Add technology-specific capacity factor data
        clustering_metrics.update(tech_data)
        
        # Copy clustering visualization to source_data folder if it exists
        # Note: Actual copying happens later in the model creation workflow
        # This just logs what files are available for copying
        self._log_available_clustering_files(iso_code, data_source)
        
        return clustering_metrics
    
    def _log_available_clustering_files(self, iso_code, data_source):
        """Log available clustering visualization files for later copying"""
        
        # Define technologies to check
        technologies = [
            ('solar', 'solar_resources'),
            ('wind_onshore', 'wind_onshore'), 
            ('wind_offshore', 'wind_offshore')
        ]
        
        available_count = 0
        
        for tech_name, folder_name in technologies:
            # Define potential source locations for each technology
            source_locations = [
                f"output_{data_source}/{iso_code}/clustering_results_{iso_code}_{tech_name}.png",
                f"1_grids/output_{data_source}/{iso_code}/clustering_results_{iso_code}_{tech_name}.png",
                f"vervestacks_visual_atlas/images/{folder_name}/{iso_code}/clustering_results_{iso_code}_{tech_name}.png",
                f"vervestacks_sector_atlas/images/grid_infrastructure/{iso_code}/clustering_results_{iso_code}_{tech_name}.png"
            ]
            
            # Check if any source file exists
            for source_path in source_locations:
                source_file = Path(source_path)
                if source_file.exists():
                    print(f"📋 Found {tech_name} clustering visualization: {source_file}")
                    available_count += 1
                    break
            else:
                print(f"⚠️  No {tech_name} clustering visualization found for {iso_code} with data_source {data_source}")
        
        if available_count == 0:
            print(f"⚠️  No clustering visualizations found for {iso_code} with data_source {data_source}")
        else:
            print(f"📋 Found {available_count} clustering visualizations for {iso_code} (will be copied to model folder later)")
    
    def copy_clustering_visualizations_to_model_folder(self, iso_code, data_source, dest_folder):
        """Copy technology-specific clustering visualization PNGs to model folder's source_data"""
        import shutil
        
        # Define technologies to copy
        technologies = [
            ('solar', 'solar_resources'),
            ('wind_onshore', 'wind_onshore'), 
            ('wind_offshore', 'wind_offshore')
        ]
        
        copied_count = 0
        
        # Create source_data directory in the model folder
        model_source_data = Path(dest_folder) / "source_data"
        model_source_data.mkdir(parents=True, exist_ok=True)
        
        for tech_name, folder_name in technologies:
            # Define potential source locations for each technology
            source_locations = [
                f"output_{data_source}/{iso_code}/clustering_results_{iso_code}_{tech_name}.png",
                f"1_grids/output_{data_source}/{iso_code}/clustering_results_{iso_code}_{tech_name}.png",
                f"vervestacks_visual_atlas/images/{folder_name}/{iso_code}/clustering_results_{iso_code}_{tech_name}.png",
                f"vervestacks_sector_atlas/images/grid_infrastructure/{iso_code}/clustering_results_{iso_code}_{tech_name}.png"
            ]
            
            # Define destination in model folder
            dest_file = model_source_data / f"clustering_results_{iso_code}_{tech_name}.png"
            
            # Try to find and copy the clustering image for this technology
            for source_path in source_locations:
                source_file = Path(source_path)
                if source_file.exists():
                    try:
                        # Copy the file to model folder
                        shutil.copy2(source_file, dest_file)
                        print(f"✅ Copied {tech_name} clustering visualization to model folder: {source_file} → {dest_file}")
                        copied_count += 1
                        break
                    except Exception as e:
                        print(f"⚠️  Error copying {tech_name} clustering image from {source_file}: {e}")
                        continue
            else:
                print(f"⚠️  No {tech_name} clustering visualization found for {iso_code} with data_source {data_source}")
        
        if copied_count == 0:
            print(f"⚠️  No clustering visualizations copied to model folder for {iso_code}")
        else:
            print(f"✅ Successfully copied {copied_count} clustering visualizations to model folder for {iso_code}")
        
        return copied_count > 0
    
    def _get_data_source_description(self, data_source):
        """Get human-readable description of data source"""
        descriptions = {
            'eur': 'European transmission infrastructure (OSM-Eur)',
            'kan': 'Infrastructure-based transmission buses', 
            'cit': 'Cities as transmission bus proxies'
        }
        return descriptions.get(data_source, f'Grid definition: {data_source}')

    def extract_grid_modeling_metrics(self, iso_code, data_source='kan'):
        """Extract comprehensive grid modeling statistics from output files"""
        grid_output_dir = Path(f"1_grids/output_{data_source}/{iso_code}")
        if not grid_output_dir.exists():
            raise FileNotFoundError(f"Grid output directory not found: {grid_output_dir}")
        
        metrics = {}
        
        # Set visualization path based on data source type
        if data_source.startswith('syn'):
            metrics['grid_viz_image_path'] = f"VerveStacks_{iso_code}_grids_{data_source}/grid_analysis/{iso_code}_cluster_shapes_4panel.png"
        else:
            metrics['grid_viz_image_path'] = f"VerveStacks_{iso_code}_grids_{data_source}/grid_analysis/{iso_code}_network_visualization.svg"
        
        # Read clustered buses data
        buses_file = grid_output_dir / f"{iso_code}_clustered_buses.csv"
        if not buses_file.exists():
            raise FileNotFoundError(f"Clustered buses file not found: {buses_file}")
        buses_df = pd.read_csv(buses_file)
        metrics.update({
            'total_buses': len(buses_df),
            'voltage_levels': ', '.join(sorted(buses_df['voltage'].unique().astype(str))),
            'grid_coverage_area': self._calculate_grid_coverage_area(buses_df)
        })
        
        # Read transmission lines data
        lines_file = grid_output_dir / f"{iso_code}_clustered_lines.csv"
        if not lines_file.exists():
            raise FileNotFoundError(f"Clustered lines file not found: {lines_file}")
        lines_df = pd.read_csv(lines_file)
        metrics.update({
            'total_lines': len(lines_df),
            'avg_line_length': self._calculate_avg_line_length(lines_df)
        })
        
        # Read power plant assignment data
        plants_file = grid_output_dir / f"{iso_code}_power_plants_assigned_to_buses.csv"
        if not plants_file.exists():
            raise FileNotFoundError(f"Power plants file not found: {plants_file}")
        plants_df = pd.read_csv(plants_file)
        metrics.update({
            'plants_mapped': len(plants_df),
            'plants_capacity_gw': self._calculate_plants_capacity(plants_df, iso_code)
        })
        
        # Read zone-bus mapping data (skip for synthetic grids where clusters ARE buses)
        if data_source.startswith('syn'):
            print(f"   Synthetic grid mode: skipping zone_bus_mapping analysis")
            zones_df = pd.DataFrame()
            # Add placeholder metrics for renewable zones
            metrics.update({
                'total_grid_cells': 0,
                'solar_wind_onshore_zones': 0,
                'wind_offshore_zones': 0,
                'zone_bus_mappings': 0
            })
        else:
            zones_file = grid_output_dir / f"{iso_code}_zone_bus_mapping.csv"
            if not zones_file.exists():
                raise FileNotFoundError(f"Zone-bus mapping file not found: {zones_file}")
            zones_df = pd.read_csv(zones_file)
            metrics.update(self._analyze_renewable_zones(zones_df))
        
        # Read load distribution data (voronoi only)
        if data_source.startswith('syn'):
            load_file = grid_output_dir / f"{iso_code}_bus_load_share.csv"
        else:
            load_file = grid_output_dir / f"{iso_code}_bus_load_share_voronoi.csv"
        if not load_file.exists():
            raise FileNotFoundError(f"Load distribution file not found: {load_file}")
        load_df = pd.read_csv(load_file)
        metrics.update(self._analyze_load_distribution(load_df, 'voronoi'))
        
        # Calculate clustering efficiency
        original_buses_file = grid_output_dir / f"{iso_code}_clustered_buses.csv"
        if not original_buses_file.exists():
            raise FileNotFoundError(f"Bus clustering mapping file not found: {original_buses_file}")
        original_df = pd.read_csv(original_buses_file)
        metrics['clustering_ratio'] = round((1 - len(buses_df) / len(original_df)) * 100, 1)
        
        return metrics
    
    def _calculate_grid_coverage_area(self, buses_df):
        """Calculate approximate grid coverage area from bus coordinates"""
        if len(buses_df) < 2:
            raise ValueError("Need at least 2 buses to calculate coverage area")
        
        # Calculate bounding box
        min_lat, max_lat = buses_df['y'].min(), buses_df['y'].max()
        min_lon, max_lon = buses_df['x'].min(), buses_df['x'].max()
        
        # Rough area calculation (not precise but good for display)
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        # Approximate km² (rough conversion)
        area = lat_range * lon_range * 111 * 111 * np.cos(np.radians((min_lat + max_lat) / 2))
        return int(area)
    
    def _calculate_avg_line_length(self, lines_df):
        """Calculate average transmission line length"""
        if 'length' not in lines_df.columns:
            raise KeyError("'length' column not found in lines data")
        return round(lines_df['length'].mean(), 1)
    
    def _calculate_plants_capacity(self, plants_df, iso_code):
        """Calculate total capacity of mapped power plants"""
        # This would need to be enhanced to read actual capacity data
        # For now, return count as placeholder
        return len(plants_df)
    
    def _analyze_renewable_zones(self, zones_df):
        """Analyze renewable energy zones from zone-bus mapping"""
        metrics = {}
        
        # Count different zone types
        # Solar/wind onshore zones: contain underscore but don't start with wof-
        solar_wind_onshore_zones = len(zones_df[
            zones_df['grid_cell'].str.contains('_', na=False) & 
            ~zones_df['grid_cell'].str.startswith('wof-', na=False)
        ])
        wind_offshore_zones = len(zones_df[zones_df['grid_cell'].str.startswith('wof-', na=False)])
        
        metrics.update({
            'total_grid_cells': len(zones_df),
            'solar_wind_onshore_zones': solar_wind_onshore_zones,
            'wind_offshore_zones': wind_offshore_zones,
            'zone_bus_mappings': len(zones_df),
            'spatial_coverage_area': solar_wind_onshore_zones * 2500,  # 50x50km = 2500 km² per cell
            # Add missing parameters for template
            'renewable_plants': 0,  # Placeholder - would need actual plant data
            'renewable_capacity_gw': 0,  # Placeholder - would need actual capacity data
            'conventional_plants': 0,  # Placeholder - would need actual plant data
            'conventional_capacity_gw': 0,  # Placeholder - would need actual capacity data
            'max_solar_id': solar_wind_onshore_zones,  # Use zone count as max ID
            'max_wind_id': solar_wind_onshore_zones,  # Same as solar since they're combined
            'max_offshore_id': wind_offshore_zones,
            'load_cv': 0,  # Placeholder - would need actual load distribution analysis
            'load_balance_description': 'Balanced distribution across transmission buses'
        })
        
        return metrics
    
    def extract_hydro_availability_content(self, iso_code, processing_params):
        """Extract hydro availability scenarios content for README integration"""
        try:
            # Import hydro enhancer (late import to avoid dependency issues)
            import sys
            from pathlib import Path
            
            # Add hydro scenarios path
            hydro_path = Path(__file__).parent.parent / "hydro_availability_scenarios"
            if str(hydro_path) not in sys.path:
                sys.path.insert(0, str(hydro_path))
            
            from hydro_readme_enhancer import HydroReadmeEnhancer
            
            print(f"   🔍 Checking hydro availability data for {iso_code}...")
            
            # Initialize hydro enhancer
            enhancer = HydroReadmeEnhancer(iso_code)
            
            # Check if country has hydro data
            if not enhancer.has_hydro_data():
                print(f"   ⚠️  No hydro scenario data available for {iso_code}")
                return None
            
            print(f"   ✅ Generating hydro content for {iso_code}...")
            
            # Determine output directory (same as other charts)
            output_dir = "source_data"  # Standard location for README charts
            
            # Generate hydro content (charts + statistics)
            hydro_content = enhancer.generate_hydro_content_for_readme(output_dir)
            
            if hydro_content:
                print(f"   📊 Hydro enhancement complete: {hydro_content['hydro_p10_avg']}/{hydro_content['hydro_p50_avg']}/{hydro_content['hydro_p90_avg']}")
                return hydro_content
            else:
                print(f"   ❌ Failed to generate hydro content for {iso_code}")
                return None
                
        except Exception as e:
            print(f"   ⚠️  Hydro enhancement failed for {iso_code}: {e}")
            return None
    
    def extract_ar6_scenario_metrics(self, iso_code):
        """Extract AR6 scenario statistics from the created scenario file"""
        try:
            # AR6 is independent of grid modeling - search for any matching folder
            models_base = Path("C:/Veda/Veda/Veda_models/vervestacks_models")
            
            # Search for any folder matching VerveStacks_{iso_code}* pattern
            # This includes: VerveStacks_{iso_code}, VerveStacks_{iso_code}_grids, VerveStacks_{iso_code}_grids_kan, etc.
            matching_folders = list(models_base.glob(f"VerveStacks_{iso_code}*"))
            
            ar6_file = None
            model_folder = None
            
            # Prioritize grid models (longer folder names = more specific)
            for folder in sorted(matching_folders, key=lambda x: len(x.name), reverse=True):
                candidate_file = folder / "SuppXLS" / "Scen_Par-AR6_R10.xlsx"
                if candidate_file.exists():
                    ar6_file = candidate_file
                    model_folder = folder.name
                    break
            
            # Check if file was found
            if not ar6_file:
                raise FileNotFoundError(f"AR6 scenario file not found for {iso_code} in any VerveStacks_{iso_code}* folder")
            
            # Load AR6 data from the Excel file
            # The data starts from row 10, so we need to skip the header rows
            ar6_data = pd.read_excel(ar6_file, sheet_name='ar6_r10', skiprows=9)
            
            # Load IEA data for baseline context
            iea_data = pd.read_excel(ar6_file, sheet_name='iea_data')
            
            # Extract basic statistics
            # Get the correct R10 region for this specific ISO
            r10_region = self._get_r10_region_for_iso(iso_code, ar6_data)
            metrics = {
                'r10_region': r10_region,
                'iea_records': len(iea_data),
                'ar6_records': len(ar6_data),
                'scenario_categories': sorted(ar6_data['Category'].unique()) if 'Category' in ar6_data.columns else [],
                'scenario_attributes': sorted(ar6_data['attribute'].unique()) if 'attribute' in ar6_data.columns else [],
                'years_covered': sorted(ar6_data['Year'].unique()) if 'Year' in ar6_data.columns else [],
            # Add template-friendly versions
            'len(scenario_categories)': len(ar6_data['Category'].unique()) if 'Category' in ar6_data.columns else 0,
            'len(scenario_attributes)': len(ar6_data['attribute'].unique()) if 'attribute' in ar6_data.columns else 0,
            'len(years_covered)': len(ar6_data['Year'].unique()) if 'Year' in ar6_data.columns else 0,
            'min(years_covered)': min(ar6_data['Year'].unique()) if 'Year' in ar6_data.columns and len(ar6_data['Year'].unique()) > 0 else 2020,
            'max(years_covered)': max(ar6_data['Year'].unique()) if 'Year' in ar6_data.columns and len(ar6_data['Year'].unique()) > 0 else 2050,
            # Add missing template variables
            'total_scenario_models': len(ar6_data),
            'co2_cv': 0.0,  # Will be calculated in _analyze_ar6_uncertainty
            'elec_cv': 0.0,  # Will be calculated in _analyze_ar6_uncertainty
            'transport_cv': 0.0,  # Will be calculated in _analyze_ar6_uncertainty
            'hydrogen_cv': 0.0,  # Will be calculated in _analyze_ar6_uncertainty
            'model_folder_name': model_folder  # Use the actual model folder name found
            }
            
            # Calculate detailed transformation metrics
            if 'Category' in ar6_data.columns and 'attribute' in ar6_data.columns:
                metrics.update(self._analyze_ar6_transformations(ar6_data))
            
            # Calculate uncertainty metrics
            if 'median' in ar6_data.columns and 'std' in ar6_data.columns:
                metrics.update(self._analyze_ar6_uncertainty(ar6_data))
            
            return metrics
            
        except Exception as e:
            print(f"⚠️  Error extracting AR6 scenario metrics: {e}")
            return {}
    
    def _get_r10_region_for_iso(self, iso_code, ar6_data):
        """Get the correct R10 region name for a specific ISO code"""
        try:
            # Import the mapping function from create_ar6_r10_scenario
            import sys
            sys.path.append('.')
            from create_ar6_r10_scenario import map_iso_to_r10
            
            # Get the R10 region for this specific ISO
            r10_region, _ = map_iso_to_r10(iso_code)
            return r10_region
            
        except Exception as e:
            print(f"⚠️  Could not map {iso_code} to R10 region: {e}")
            # Fallback to first region in data
            if 'Region' in ar6_data.columns and len(ar6_data) > 0:
                return ar6_data['Region'].iloc[0]
            return 'Unknown'
    
    def _check_grid_modeling_enabled(self, iso_code):
        """Check if grid modeling is enabled for this ISO"""
        # This would need to be passed as a parameter or checked from processing context
        # Check if any _grids folder exists (including data_source suffix variants)
        models_base = Path("C:/Veda/Veda/Veda_models/vervestacks_models")
        grids_folders = list(models_base.glob(f"VerveStacks_{iso_code}_grids*"))
        return len(grids_folders) > 0
    
    def _analyze_ar6_transformations(self, ar6_data):
        """Analyze AR6 transformation pathways and extract key metrics"""
        metrics = {}
        
        try:
            # CO2 Price analysis
            co2_data = ar6_data[ar6_data['attribute'] == 'CO2 price']
            if not co2_data.empty and 'median' in co2_data.columns:
                for category in co2_data['Category'].unique():
                    cat_data = co2_data[co2_data['Category'] == category]
                    # Get 2030 and 2050 values
                    co2_2030 = cat_data[cat_data['Year'] == 2030]['median'].iloc[0] if len(cat_data[cat_data['Year'] == 2030]) > 0 else 0
                    co2_2050 = cat_data[cat_data['Year'] == 2050]['median'].iloc[0] if len(cat_data[cat_data['Year'] == 2050]) > 0 else 0
                    metrics[f'co2_2030_{category.lower()}_median'] = co2_2030
                    metrics[f'co2_2050_{category.lower()}_median'] = co2_2050
            
            # Electricity growth analysis
            elec_data = ar6_data[ar6_data['attribute'] == 'Electricity growth relative to 2020']
            if not elec_data.empty and 'median' in elec_data.columns:
                for category in elec_data['Category'].unique():
                    cat_data = elec_data[elec_data['Category'] == category]
                    elec_2050 = cat_data[cat_data['Year'] == 2050]['median'].iloc[0] if len(cat_data[cat_data['Year'] == 2050]) > 0 else 1.0
                    metrics[f'elec_growth_2050_{category.lower()}'] = elec_2050
            
            # Hydrogen analysis
            hydrogen_data = ar6_data[ar6_data['attribute'] == 'Hydrogen as a share of electricity']
            if not hydrogen_data.empty and 'median' in hydrogen_data.columns:
                for category in hydrogen_data['Category'].unique():
                    cat_data = hydrogen_data[hydrogen_data['Category'] == category]
                    hydrogen_2050 = cat_data[cat_data['Year'] == 2050]['median'].iloc[0] if len(cat_data[cat_data['Year'] == 2050]) > 0 else 0.0
                    metrics[f'hydrogen_2050_{category.lower()}_median'] = hydrogen_2050
            
            # Add descriptive text placeholders
            metrics.update({
                'price_volatility_description': 'moderate price volatility',
                'uncertainty_range_description': 'significant uncertainty ranges',
                'model_agreement_level': 'moderate agreement',
                'electrification_pattern': 'strong electrification trends',
                'demand_uncertainty': 'moderate demand uncertainty',
                'hydrogen_volatility': 'high volatility',
                'hydrogen_regional_pattern': 'emerging hydrogen economy patterns',
                'transport_2020_median': 2.0,  # Placeholder
                'transport_2050_c1_median': 15.0,  # Placeholder
                'transport_growth_factor': 7.5,  # Placeholder
                'transport_uncertainty': 'moderate uncertainty',
                'transport_divergence_description': 'significant divergence'
            })
            
        except Exception as e:
            print(f"⚠️  Error analyzing AR6 transformations: {e}")
        
        return metrics
    
    def _analyze_ar6_uncertainty(self, ar6_data):
        """Analyze AR6 uncertainty and model divergence"""
        metrics = {}
        
        try:
            # Calculate coefficient of variation for different attributes
            attributes = ar6_data['attribute'].unique()
            
            for attr in attributes:
                attr_data = ar6_data[ar6_data['attribute'] == attr]
                if 'median' in attr_data.columns and 'std' in attr_data.columns:
                    # Calculate CV for 2050 values
                    data_2050 = attr_data[attr_data['Year'] == 2050]
                    if not data_2050.empty:
                        cv = (data_2050['std'] / data_2050['median']).mean() * 100
                        attr_key = attr.lower().replace(' ', '_').replace('|', '_')
                        metrics[f'{attr_key}_cv'] = cv
            
            # Add descriptive placeholders
            metrics.update({
                'total_scenario_models': len(ar6_data),
                'regional_convergence_pattern': 'moderate convergence',
                'regional_specific_insights': 'region-specific climate policy patterns',
                'regional_context_factors': 'economic and policy context',
                # Update CV values with proper names
                'co2_cv': metrics.get('co2_price_cv', 0.0),
                'elec_cv': metrics.get('electricity_growth_relative_to_2020_cv', 0.0),
                'transport_cv': metrics.get('transportation_electricity_share_cv', 0.0),
                'hydrogen_cv': metrics.get('hydrogen_as_a_share_of_electricity_cv', 0.0)
            })
            
        except Exception as e:
            print(f"⚠️  Error analyzing AR6 uncertainty: {e}")
        
        return metrics
    
    def _analyze_load_distribution(self, load_df, method):
        """Analyze load distribution for a specific method"""
        if 'load_share' not in load_df.columns:
            raise KeyError(f"'load_share' column not found in {method} load data")
        
        total_load = load_df['load_share'].sum()
        buses_with_load = len(load_df[load_df['load_share'] > 0])
        max_load = load_df['load_share'].max()
        max_load_bus = load_df.loc[load_df['load_share'].idxmax(), 'bus_id'] if max_load > 0 else 'N/A'
        
        return {
            f'{method}_buses': buses_with_load,
            f'{method}_load_gw': round(total_load, 2),
            f'max_load_gw': round(max_load, 2),
            f'max_load_bus': max_load_bus
        }

    def generate_readme_content(self, iso_code, processing_params=None, **section_flags):
        """
        Generate complete README content based on enabled sections
        
        Args:
            iso_code: Country ISO code
            processing_params: Dictionary of processing parameters
            **section_flags: Boolean flags for sections (timeslice_analysis=True, ar6_scenarios=True, etc.)
        """
        
        if processing_params is None:
            processing_params = {}
        
        # Add basic parameters
        processing_params.update({
            'iso_code': iso_code,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'model_folder_name': f"VerveStacks_{iso_code}"  # Default model folder name
        })
        
        # Extract clustering metrics if supply curves exist (clustering is part of renewable characterization)
        if section_flags.get('supply_curves_exist', False):
            processing_params['supply_curves_exist'] = True
            # Get data_source from iso_processor if available
            data_source = section_flags.get('data_source', 'kan')  # Default to 'kan' if not specified
            clustering_metrics = self.extract_clustering_metrics(iso_code, data_source)
            processing_params.update(clustering_metrics)
        
        # Extract grid modeling metrics if grid modeling is enabled
        if section_flags.get('grid_modeling', False):
            data_source = section_flags.get('data_source', 'kan')  # Default to 'kan' if not specified
            grid_metrics = self.extract_grid_modeling_metrics(iso_code, data_source)
            processing_params.update(grid_metrics)
        
        # Extract AR6 scenario metrics if enabled
        if section_flags.get('ar6_scenarios', False):
            ar6_metrics = self.extract_ar6_scenario_metrics(iso_code)
            processing_params.update(ar6_metrics)
        
        # Extract hydro availability scenarios if applicable
        hydro_capacity_gw = processing_params.get('hydro_capacity_gw', 0)
        if hydro_capacity_gw > 1.0:
            hydro_content = self.extract_hydro_availability_content(iso_code, processing_params)
            if hydro_content:
                processing_params.update(hydro_content)
        
        # Generate content sections
        content_sections = []
        
        # Get section order from config
        section_order = self.config.get('section_order', [])
        readme_sections = self.config.get('readme_sections', {})
        
        for section_path in section_order:
            section_parts = section_path.split('.')
            section_name = section_parts[0]
            subsection_name = section_parts[1] if len(section_parts) > 1 else None
            
            # Check if section should be included
            section_config = readme_sections.get(section_name, {})
            
            # Check enabled conditions
            enabled = section_config.get('enabled_by_default', False)
            enabled_when = section_config.get('enabled_when')
            
            if enabled_when:
                # Parse condition - support both boolean and numeric comparisons
                if '=' in enabled_when and '>' not in enabled_when and '<' not in enabled_when:
                    # Boolean condition (e.g., "ar6_scenarios=True")
                    condition_parts = enabled_when.split('=')
                    if len(condition_parts) == 2:
                        flag_name = condition_parts[0].strip()
                        flag_value = condition_parts[1].strip().lower() == 'true'
                        enabled = section_flags.get(flag_name, False) == flag_value
                elif '>' in enabled_when:
                    # Numeric comparison (e.g., "hydro_capacity_gw > 1.0")
                    condition_parts = enabled_when.split('>')
                    if len(condition_parts) == 2:
                        param_name = condition_parts[0].strip()
                        threshold_value = float(condition_parts[1].strip())
                        param_value = processing_params.get(param_name, 0)
                        enabled = param_value > threshold_value
                elif '<' in enabled_when:
                    # Less than comparison (e.g., "hydro_capacity_gw < 1.0")
                    condition_parts = enabled_when.split('<')
                    if len(condition_parts) == 2:
                        param_name = condition_parts[0].strip()
                        threshold_value = float(condition_parts[1].strip())
                        param_value = processing_params.get(param_name, 0)
                        enabled = param_value < threshold_value
            
            if not enabled:
                continue
            
            # Generate section content
            try:
                section_content = self.render_section(section_name, subsection_name, processing_params)
                if section_content:
                    content_sections.append(section_content)
            except Exception as e:
                print(f"⚠️  Error rendering section {section_path}: {e}")
        
        return '\n\n'.join(content_sections)
    
    def render_section(self, section_name, subsection_name, params):
        """Render a specific section from YAML template"""
        
        readme_sections = self.config.get('readme_sections', {})
        section_config = readme_sections.get(section_name, {})
        
        if subsection_name:
            subsection_config = section_config.get(subsection_name, {})
        else:
            subsection_config = section_config
        
        # Get template
        template = subsection_config.get('template', '')
        title = subsection_config.get('title', '')
        
        if not template:
            return ''
        
        # Handle special sections that need subsection rendering
        if section_name == 'ar6_scenarios' and subsection_name == 'transformation_insights':
            return self.render_transformation_insights(section_config, params)
        
        # Render template
        try:
            content = template.format(**params)
            if title:
                # Format the title as well
                formatted_title = title.format(**params)
                return f"{formatted_title}\n\n{content}"
            return content
        except KeyError as e:
            print(f"⚠️  Missing parameter for template: {e}")
            return f"{title}\n\n{template}"  # Return unformatted if parameters missing
    
    def render_transformation_insights(self, section_config, params):
        """Render the transformation insights subsection with all components"""
        
        insights_config = section_config.get('transformation_insights', {})
        title = insights_config.get('title', '### Key Transformation Pathways')
        
        content_parts = [title, '']
        
        # Render each insight component
        for insight_name in ['co2_prices', 'electricity_growth', 'hydrogen_economy', 'transport_electrification']:
            insight_config = insights_config.get(insight_name, {})
            template = insight_config.get('template', '')
            
            if template:
                try:
                    rendered = template.format(**params)
                    content_parts.append(rendered)
                    content_parts.append('')  # Add spacing
                except KeyError as e:
                    print(f"⚠️  Missing parameter for {insight_name}: {e}")
        
        return '\n'.join(content_parts)


def main():
    """Test the README generator"""
    
    generator = ReadmeGenerator()
    
    # Test parameters
    test_params = {
        'capacity_threshold': 100,
        'efficiency_adjustment_gas': 1.0,
        'efficiency_adjustment_coal': 1.0,
        'gem_coverage_pct': 85,
        'total_capacity_gw': 45.2,
        'plants_above_threshold': 156,
        'missing_capacity_summary': 'Added 2.3 GW from IRENA renewables statistics'
    }
    
    # Generate README for different configurations
    print("🧪 Testing README generation...")
    
    # Test 1: Core only
    content = generator.generate_readme_content('CHE', test_params)
    print(f"✅ Core only: {len(content)} characters")
    
    # Test 2: Core + AR6 scenarios
    content = generator.generate_readme_content('CHE', test_params, ar6_scenarios=True)
    print(f"✅ Core + AR6: {len(content)} characters")
    
    # Test 3: All sections
    content = generator.generate_readme_content('CHE', test_params, 
                                              timeslice_analysis=True, 
                                              ar6_scenarios=True, 
                                              grid_modeling=True)
    print(f"✅ All sections: {len(content)} characters")
    
    # Save test output
    with open('test_readme_output.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print("📄 Test output saved to test_readme_output.md")


if __name__ == "__main__":
    main()
