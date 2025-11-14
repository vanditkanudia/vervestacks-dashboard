#!/usr/bin/env python3
"""
Complete Multi-Layered Energy System Analysis Pipeline
======================================================

Runs the full VerveStacks regional modeling workflow:
1. Population-based demand regions
2. GEM existing generation clusters  
3. Combined renewable (solar+wind) zones
4. Inter-layer NTC calculations (demand ↔ generation ↔ renewables)
5. Comprehensive visualization

Usage:
    python run_complete_analysis.py --country IND --demand-regions 12 --gen-clusters 10 --renewable-zones 8
    
Features:
- OSM disabled by default (population-only, distance-based NTC)
- Optional OSM enhancement with --enable-osm flags
- Complete NTC matrix between all layers
- Comprehensive HTML visualization
- Progress tracking and error handling
"""

import subprocess
import argparse
import os
import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np
import webbrowser

class MultiLayerAnalysisPipeline:
    """
    Complete multi-layered energy system analysis pipeline
    """
    
    def __init__(self, country_code, demand_regions=None, gen_clusters=None, renewable_zones=None, 
                 enable_osm_industrial=False, enable_osm_grid=False,
                 eps_demand=100, eps_generation=30, eps_renewable=50):
        self.country = country_code.upper()
        self.demand_regions = demand_regions
        self.gen_clusters = gen_clusters  
        self.renewable_zones = renewable_zones
        self.enable_osm_industrial = enable_osm_industrial
        self.enable_osm_grid = enable_osm_grid
        self.eps_demand = eps_demand
        self.eps_generation = eps_generation
        self.eps_renewable = eps_renewable
        
        # Default cluster suggestions for known countries (optional)
        self.country_defaults = {
            'CHE': {'demand': 4, 'gen': 3, 'renewable': 3},
            'ITA': {'demand': 7, 'gen': 5, 'renewable': 4}, 
            'DEU': {'demand': 10, 'gen': 8, 'renewable': 6},
            'USA': {'demand': 15, 'gen': 12, 'renewable': 10},
            'AUS': {'demand': 8, 'gen': 6, 'renewable': 5},
            'CHN': {'demand': 20, 'gen': 15, 'renewable': 12},
            'IND': {'demand': 12, 'gen': 10, 'renewable': 8},
            'JPN': {'demand': 10, 'gen': 8, 'renewable': 6},
            'ZAF': {'demand': 6, 'gen': 4, 'renewable': 3},
            'NZL': {'demand': 4, 'gen': 3, 'renewable': 3},
            'BRA': {'demand': 12, 'gen': 8, 'renewable': 6},
            'FRA': {'demand': 8, 'gen': 6, 'renewable': 6},
            'GBR': {'demand': 8, 'gen': 6, 'renewable': 6},
            'ESP': {'demand': 6, 'gen': 5, 'renewable': 5},
            'CAN': {'demand': 12, 'gen': 10, 'renewable': 10},
            'MEX': {'demand': 8, 'gen': 6, 'renewable': 6},
            'ARG': {'demand': 6, 'gen': 4, 'renewable': 5},
            'RUS': {'demand': 15, 'gen': 12, 'renewable': 12},
            'TUR': {'demand': 6, 'gen': 5, 'renewable': 5},
            'IRN': {'demand': 8, 'gen': 6, 'renewable': 6},
            'SAU': {'demand': 4, 'gen': 3, 'renewable': 4},
            'EGY': {'demand': 6, 'gen': 4, 'renewable': 5},
            'NGA': {'demand': 8, 'gen': 6, 'renewable': 6},
            'KEN': {'demand': 4, 'gen': 3, 'renewable': 3},
            'ETH': {'demand': 6, 'gen': 4, 'renewable': 4},
            'GHA': {'demand': 4, 'gen': 3, 'renewable': 3},
            'THA': {'demand': 6, 'gen': 4, 'renewable': 4},
            'VNM': {'demand': 6, 'gen': 4, 'renewable': 4},
            'IDN': {'demand': 10, 'gen': 8, 'renewable': 8},
            'MYS': {'demand': 4, 'gen': 3, 'renewable': 3},
            'PHL': {'demand': 8, 'gen': 6, 'renewable': 6},
            'KOR': {'demand': 6, 'gen': 4, 'renewable': 4},
            'TWN': {'demand': 4, 'gen': 3, 'renewable': 3},
            'SGP': {'demand': 1, 'gen': 1, 'renewable': 1},
            'HKG': {'demand': 1, 'gen': 1, 'renewable': 1},
            'ARE': {'demand': 2, 'gen': 2, 'renewable': 2}
        }
        
        # Set defaults if not specified (fallback for any unlisted country)
        defaults = self.country_defaults.get(country_code.upper(), {'demand': 8, 'gen': 6, 'renewable': 5})
        self.demand_regions = demand_regions or defaults['demand']
        self.gen_clusters = gen_clusters or defaults['gen']
        self.renewable_zones = renewable_zones or defaults['renewable']
        
        # Create configuration-specific output directory
        config_name = f"{self.country}_d{self.demand_regions}g{self.gen_clusters}r{self.renewable_zones}"
        self.output_dir = f"output/{config_name}"
        
        # Track pipeline state
        self.completed_steps = []
        self.failed_steps = []
        self.start_time = None
        
    def run_complete_pipeline(self):
        """
        Execute the complete multi-layered analysis pipeline
        """
        self.start_time = time.time()
        
        # Create configuration-specific output directory
        import os
        os.makedirs(self.output_dir, exist_ok=True)
        
        print("🌍" + "="*80)
        print(f"🚀 VERVESTACKS MULTI-LAYERED ENERGY SYSTEM ANALYSIS")
        print("🌍" + "="*80)
        print(f"📍 Country: {self.country}")
        print(f"🏘️  Demand Regions: {self.demand_regions}")
        print(f"🏭 Generation Clusters: {self.gen_clusters}")
        print(f"🌞 Renewable Zones: {self.renewable_zones}")
        print(f"🏭 OSM Industrial: {'ENABLED' if self.enable_osm_industrial else 'DISABLED'}")
        print(f"🔌 OSM Grid: {'ENABLED' if self.enable_osm_grid else 'DISABLED'}")
        print(f"📂 Output Directory: {self.output_dir}")
        print("="*88)
        
        try:
            # Step 1: Demand Regions
            self._run_demand_analysis()
            
            # Step 2: Generation Clusters  
            self._run_generation_analysis()
            
            # Step 3: Renewable Zones
            self._run_renewable_analysis()
            
            # Step 4: Inter-layer NTC calculations
            self._calculate_interlayer_ntc()
            
            # Step 5: Comprehensive Visualization
            self._create_visualization()
            
            # Step 6: NTC Network Visualization
            self._create_ntc_visualization()
            
            # Step 7: Visual Summary (Economic Atlas)
            self._generate_visual_summary()
            
            self._print_completion_summary()
            
            # Auto-open output files
            print(f"\n🚀 OPENING OUTPUT FILES...")
            print("-" * 50)
            self._open_output_files()
            
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            self._print_failure_summary()
            return False
            
        return True
    
    def _run_demand_analysis(self):
        """Step 1: Population-based demand region clustering"""
        print(f"\n🏘️  STEP 1: DEMAND REGION ANALYSIS")
        print("-" * 50)
        
        # Use simple population-only script by default (more reliable)
        if self.enable_osm_industrial:
            cmd = [
                'python', 'create_regions.py',
                '--country', self.country,
                '--clusters', str(self.demand_regions),
                '--eps-km', str(self.eps_demand),
                '--enable-osm-industrial',
                '--output-dir', self.output_dir
            ]
        else:
            cmd = [
                'python', 'create_regions_simple.py',
                '--country', self.country,
                '--clusters', str(self.demand_regions),
                '--eps-km', str(self.eps_demand),
                '--output-dir', self.output_dir
            ]
        
        result = self._run_subprocess(cmd, "Demand region clustering")
        
        if result:
            self.completed_steps.append("demand_regions")
            print("✅ Demand regions completed successfully")
        else:
            raise Exception("Demand region analysis failed")
    
    def _run_generation_analysis(self):
        """Step 2: GEM existing generation clustering"""
        print(f"\n🏭 STEP 2: GENERATION CLUSTER ANALYSIS")
        print("-" * 50)
        
        # Use fixed main script (Unicode issues resolved)
        cmd = [
            'python', 'create_gem_units_clusters.py',
            '--country', self.country,
            '--clusters', str(self.gen_clusters),
            '--eps-km', str(self.eps_generation),
            '--min-share', '0.01',
            '--output-dir', self.output_dir
        ]
        
        if self.enable_osm_grid:
            cmd.append('--enable-osm-grid')
        
        result = self._run_subprocess(cmd, "Generation cluster analysis")
        
        if result:
            self.completed_steps.append("generation_clusters")
            print("✅ Generation clusters completed successfully")
        else:
            raise Exception("Generation cluster analysis failed")
    
    def _run_renewable_analysis(self):
        """Step 3: Combined renewable (solar+wind) zone clustering"""
        print(f"\n🌞 STEP 3: RENEWABLE ZONE ANALYSIS")
        print("-" * 50)
        
        # Use fixed main script (Unicode issues resolved)
        cmd = [
            'python', 'create_renewable_clusters.py',
            '--country', self.country,
            '--clusters', str(self.renewable_zones),
            '--eps-km', str(self.eps_renewable),

            '--output-dir', self.output_dir
        ]
        
        if self.enable_osm_grid:
            cmd.append('--enable-osm-grid')
        
        result = self._run_subprocess(cmd, "Renewable zone clustering")
        
        if result:
            self.completed_steps.append("renewable_zones")
            print("✅ Renewable zones completed successfully")
        else:
            raise Exception("Renewable zone analysis failed")
    
    def _calculate_interlayer_ntc(self):
        """Step 4: Calculate realistic NTC between overlapping clusters only"""
        print(f"\n⚡ STEP 4: REALISTIC NTC CALCULATIONS")
        print("-" * 50)
        
        try:
            # Run the realistic NTC calculator
            cmd = ['python', 'calculate_realistic_ntc.py', '--country', self.country, '--output-dir', self.output_dir]
            result = self._run_subprocess(cmd, "Realistic NTC calculation")
            
            if result:
                print("✅ Realistic NTC calculation completed successfully")
                
                # Load and display results
                ntc_file = f'{self.output_dir}/{self.country}_realistic_ntc_connections.csv'
                if os.path.exists(ntc_file):
                    ntc_data = pd.read_csv(ntc_file)
                    
                    print(f"🔗 Total connections: {len(ntc_data)}")
                    print(f"⚡ Total NTC capacity: {ntc_data['ntc_mw'].sum():.0f} MW")
                    
                    # Show connection breakdown
                    connection_types = ntc_data.groupby(['from_type', 'to_type']).size()
                    print("\n📊 Connection breakdown:")
                    for (from_type, to_type), count in connection_types.items():
                        print(f"  {from_type} -> {to_type}: {count} connections")
                    
                    # Show top connections
                    print("\n🔝 Top 5 connections by capacity:")
                    top_connections = ntc_data.nlargest(5, 'ntc_mw')
                    for _, conn in top_connections.iterrows():
                        print(f"  {conn['from_name']} -> {conn['to_name']}: "
                              f"{conn['ntc_mw']:.0f} MW ({conn['distance_km']:.0f} km)")
                
                self.completed_steps.append("realistic_ntc")
                
            else:
                print(f"❌ Realistic NTC calculation failed: {result.stderr}")
                self.failed_steps.append("realistic_ntc")
                
        except Exception as e:
            print(f"❌ Realistic NTC calculation failed: {e}")
            self.failed_steps.append("realistic_ntc")
    

    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate haversine distance between two points in km"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Earth radius in km
        
        return c * r
    
    def _create_visualization(self):
        """Step 5: Create comprehensive HTML visualization"""
        print(f"\n🗺️  STEP 5: COMPREHENSIVE VISUALIZATION")
        print("-" * 50)
        
        cmd = [
            'python', 'create_comprehensive_html_visualization.py',
            '--country', self.country,
            '--output-dir', self.output_dir
        ]
        
        result = self._run_subprocess(cmd, "Comprehensive visualization")
        
        if result:
            self.completed_steps.append("visualization")
            print("✅ Comprehensive visualization completed successfully")
            print(f"📂 Open {self.country}_comprehensive_energy_system.html in your browser!")
        else:
            print("⚠️  Visualization failed, but continuing...")
            self.failed_steps.append("visualization")
    
    def _create_ntc_visualization(self):
        """Step 6: Create NTC network visualization"""
        print(f"\n🔗 STEP 6: NTC NETWORK VISUALIZATION")
        print("-" * 50)
        
        try:
            # Create NTC network visualization (uses realistic NTC file directly)
            cmd = ['python', 'visualize_ntc_network.py', '--country', self.country, '--output-dir', self.output_dir]
            result = self._run_subprocess(cmd, "NTC network visualization")
            
            if result:
                print("✅ NTC network visualization completed successfully")
                ntc_viz_file = f'{self.output_dir}/{self.country}_ntc_network.png'
                if os.path.exists(ntc_viz_file):
                    print(f"🔗 NTC network diagram saved: {ntc_viz_file}")
                self.completed_steps.append("ntc_visualization")
            else:
                print(f"❌ NTC visualization failed: {result.stderr}")
                self.failed_steps.append("ntc_visualization")
                
        except Exception as e:
            print(f"❌ NTC visualization failed: {e}")
            self.failed_steps.append("ntc_visualization")
    
    def _generate_visual_summary(self):
        """Step 7: Generate visual economic atlas"""
        print(f"\n🎨 STEP 7: VISUAL SUMMARY (ECONOMIC ATLAS)")
        print("-" * 50)
        
        try:
            # Run the visual summary script
            cmd = [
                'python', 'create_summary_map_visual.py',
                '--country', self.country,
                '--output-dir', self.output_dir
            ]
            
            success = self._run_subprocess(cmd, "Visual economic atlas generation")
            
            if success:
                atlas_file = f'{self.output_dir}/{self.country}_economic_atlas.png'
                print(f"🖼️  Economic atlas saved: {atlas_file}")
                self.completed_steps.append("visual_summary")
            else:
                self.failed_steps.append("visual_summary")
            
        except Exception as e:
            print(f"⚠️  Visual summary generation failed: {e}")
            self.failed_steps.append("visual_summary")
    
    def _collect_summary_statistics(self):
        """Collect summary statistics from all analysis outputs"""
        summary = {}
        
        # Demand regions statistics
        try:
            demand_centers = pd.read_csv(f'{self.output_dir}/{self.country}_region_centers.csv')
            demand_points = pd.read_csv(f'{self.output_dir}/{self.country}_demand_points.csv')
            
            summary['Demand Analysis'] = {
                'Total Regions': len(demand_centers),
                'Total Demand Points': len(demand_points),
                'Population Centers': len(demand_points[demand_points['type'] == 'population']),
                'Industrial Facilities': len(demand_points[demand_points['type'] == 'industrial']),
                'Total Demand': f"{demand_centers['total_demand'].sum():,.0f} units"
            }
        except:
            summary['Demand Analysis'] = {'Status': 'Data not available'}
        
        # Generation clusters statistics  
        try:
            gen_centers = pd.read_csv(f'{self.output_dir}/{self.country}_gem_cluster_centers.csv')
            gen_mapping = pd.read_csv(f'{self.output_dir}/{self.country}_gem_cluster_mapping.csv')
            
            # Calculate technology distribution across clusters
            tech_distribution = {}
            for _, cluster in gen_centers.iterrows():
                cluster_name = cluster['name']
                cluster_id = cluster['cluster_id']
                cluster_plants = gen_mapping[gen_mapping['cluster_id'] == cluster_id]
                
                # Parse tech_breakdown from the cluster centers (it's a string representation of dict)
                tech_breakdown_str = cluster.get('tech_breakdown', '{}')
                try:
                    import ast
                    tech_breakdown = ast.literal_eval(tech_breakdown_str)
                    tech_summary = {}
                    for tech, capacity in tech_breakdown.items():
                        tech_summary[tech.title()] = f"{capacity:,.1f} MW"
                    tech_distribution[cluster_name] = tech_summary
                except:
                    # Fallback: analyze from mapping file
                    tech_summary = {}
                    for tech in ['Coal', 'Gas', 'Oil', 'Hydro', 'Nuclear', 'Other']:
                        tech_plants = cluster_plants[cluster_plants['technology'].str.contains(tech, case=False, na=False)]
                        if len(tech_plants) > 0:
                            tech_summary[tech] = f"{tech_plants['capacity_mw'].sum():,.0f} MW ({len(tech_plants)} plants)"
                    
                    if tech_summary:
                        tech_distribution[cluster_name] = tech_summary
            
            summary['Generation Analysis'] = {
                'Total Clusters': len(gen_centers),
                'Total Power Plants': len(gen_mapping),
                'Total Capacity': f"{gen_centers['total_capacity_mw'].sum():,.0f} MW",
                'Average Cluster Size': f"{gen_centers['total_capacity_mw'].mean():,.0f} MW",
                'Largest Cluster': f"{gen_centers['total_capacity_mw'].max():,.0f} MW"
            }
            
            # Add detailed distribution
            summary['Generation Distribution by Cluster'] = tech_distribution
            
        except Exception as e:
            summary['Generation Analysis'] = {'Status': f'Data not available: {e}'}
        
        # Renewable zones statistics
        try:
            re_centers = pd.read_csv(f'{self.output_dir}/{self.country}_renewable_cluster_centers.csv')
            re_mapping = pd.read_csv(f'{self.output_dir}/{self.country}_renewable_cluster_mapping.csv')
            
            # Calculate solar/wind distribution across clusters
            renewable_distribution = {}
            demand_distribution = {}
            
            for _, cluster in re_centers.iterrows():
                cluster_name = cluster['name']
                
                # Renewable technology breakdown
                solar_capacity = cluster.get('solar_capacity_mw', 0)
                wind_capacity = cluster.get('wind_capacity_mw', 0)
                total_capacity = cluster['total_capacity_mw']
                
                renewable_distribution[cluster_name] = {
                    'Total': f"{total_capacity:,.0f} MW",
                    'Solar': f"{solar_capacity:,.0f} MW ({solar_capacity/total_capacity*100:.1f}%)" if solar_capacity > 0 else "0 MW",
                    'Wind': f"{wind_capacity:,.0f} MW ({wind_capacity/total_capacity*100:.1f}%)" if wind_capacity > 0 else "0 MW",
                    'Dominant': cluster.get('dominant_tech', 'Mixed'),
                    'Avg CF': f"{cluster.get('weighted_avg_cf', 0):.1%}"
                }
            
            # Demand region distribution
            for _, region in demand_centers.iterrows():
                region_name = region['name']
                demand_distribution[region_name] = {
                    'Total Demand': f"{region['total_demand']:,.0f} units",
                    'Population': f"{region.get('total_population', 0):,.0f}",
                    'Cities': f"{region.get('n_cities', 0)} cities",
                    'Major City': region.get('major_city', 'Unknown'),
                    'Demand Share': f"{region.get('demand_share', 0)*100:.1f}%"
                }
            
            summary['Renewable Analysis'] = {
                'Total Zones': len(re_centers),
                'Total Capacity': f"{re_centers['total_capacity_mw'].sum():,.0f} MW",
                'Average Zone Size': f"{re_centers['total_capacity_mw'].mean():,.0f} MW",
                'Largest Zone': f"{re_centers['total_capacity_mw'].max():,.0f} MW",
                'Average Capacity Factor': f"{re_centers.get('weighted_avg_cf', pd.Series([0])).mean():.1%}"
            }
            
            # Add detailed distributions
            summary['Renewable Distribution by Zone'] = renewable_distribution
            summary['Demand Distribution by Region'] = demand_distribution
            
        except Exception as e:
            summary['Renewable Analysis'] = {'Status': f'Data not available: {e}'}
        
        return summary
    
    def _open_output_files(self):
        """Open the visual summary and HTML visualization"""
        try:
            # Open economic atlas
            atlas_file = f'{self.output_dir}/{self.country}_economic_atlas.png'
            atlas_abs_path = os.path.abspath(atlas_file)
            if os.path.exists(atlas_abs_path):
                if os.name == 'nt':  # Windows
                    os.startfile(atlas_abs_path)
                else:  # macOS/Linux
                    subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', atlas_abs_path])
                print(f"🖼️  Opened economic atlas: {atlas_abs_path}")
            else:
                print(f"⚠️  Atlas file not found: {atlas_abs_path}")
            
            # Open NTC network visualization
            ntc_file = f'{self.output_dir}/{self.country}_ntc_network.png'
            ntc_abs_path = os.path.abspath(ntc_file)
            if os.path.exists(ntc_abs_path):
                if os.name == 'nt':  # Windows
                    os.startfile(ntc_abs_path)
                else:  # macOS/Linux
                    subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', ntc_abs_path])
                print(f"🔗 Opened NTC network: {ntc_abs_path}")
            else:
                print(f"⚠️  NTC network file not found: {ntc_abs_path}")
            
            # Open HTML visualization in browser
            html_file = f'{self.output_dir}/{self.country}_comprehensive_energy_system.html'
            html_abs_path = os.path.abspath(html_file)
            if os.path.exists(html_abs_path):
                webbrowser.open(f'file://{html_abs_path}')
                print(f"🌐 Opened HTML visualization: {html_abs_path}")
            else:
                print(f"⚠️  HTML file not found: {html_abs_path}")
                
        except Exception as e:
            print(f"⚠️  Could not auto-open files: {e}")
            print(f"📂 Manually open files in: {os.path.abspath(self.output_dir)}")
    
    def _run_subprocess(self, cmd, description):
        """Run subprocess with error handling and progress tracking"""
        print(f"🔄 Running: {description}...")
        
        try:
            # Ensure we run from the 0_multi_region directory and use the same Python interpreter
            script_dir = Path(__file__).parent
            # Replace 'python' with the current Python executable to inherit the virtual environment
            if cmd[0] == 'python':
                cmd[0] = sys.executable
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600, cwd=script_dir)  # 10 minute timeout
            
            if result.returncode == 0:
                print(f"✅ {description} completed successfully")
                return True
            else:
                print(f"❌ {description} failed:")
                print(f"   Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {description} timed out (>10 minutes)")
            return False
        except Exception as e:
            print(f"❌ {description} failed with exception: {e}")
            return False
    
    def _print_completion_summary(self):
        """Print final completion summary"""
        runtime = time.time() - self.start_time
        
        print("\n" + "🎉" + "="*86 + "🎉")
        print("🎊 MULTI-LAYERED ANALYSIS COMPLETE! 🎊")
        print("🎉" + "="*86 + "🎉")
        print(f"⏱️  Total Runtime: {runtime:.1f} seconds ({runtime/60:.1f} minutes)")
        print(f"✅ Completed Steps: {len(self.completed_steps)}")
        print(f"❌ Failed Steps: {len(self.failed_steps)}")
        
        if self.completed_steps:
            print(f"\n🎯 Successfully Completed:")
            for step in self.completed_steps:
                print(f"   ✅ {step.replace('_', ' ').title()}")
        
        if self.failed_steps:
            print(f"\n⚠️  Failed (non-critical):")
            for step in self.failed_steps:
                print(f"   ❌ {step.replace('_', ' ').title()}")
        
        print(f"\n📂 Output Files (check '{self.output_dir}/' folder):")
        output_files = [
            f"{self.country}_region_centers.csv",
            f"{self.country}_gem_cluster_centers.csv", 
            f"{self.country}_renewable_cluster_centers.csv",
            f"{self.country}_renewable_to_generation_ntc.csv",
            f"{self.country}_comprehensive_energy_system.html",
            f"{self.country}_economic_atlas.png"
        ]
        
        for file in output_files:
            if os.path.exists(f"output/{file}"):
                print(f"   📄 {file}")
        
        print(f"\n🌟 Ready for VEDA model integration! 🌟")
    
    def _print_failure_summary(self):
        """Print failure summary"""
        runtime = time.time() - self.start_time if self.start_time else 0
        
        print("\n" + "❌" + "="*86 + "❌")
        print("💥 ANALYSIS PIPELINE FAILED 💥")
        print("❌" + "="*86 + "❌")
        print(f"⏱️  Runtime before failure: {runtime:.1f} seconds")
        print(f"✅ Completed before failure: {self.completed_steps}")
        print(f"❌ Failed step: {self.failed_steps[-1] if self.failed_steps else 'Unknown'}")


def main():
    """Main execution function"""
    

    
    parser = argparse.ArgumentParser(
        description='Complete Multi-Layered Energy System Analysis Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis with defaults
  python run_complete_analysis.py --country IND
  
  # Custom cluster counts (short aliases)
  python run_complete_analysis.py --country USA --cd 15 --cg 12 --cr 10
  
  # Custom spatial granularity (clusters + epsilon)
  python run_complete_analysis.py --country DEU --cd 8 --cg 6 --cr 4 --ekd 80 --ekg 25 --ekr 40
  
  # Structural sensitivity analysis - coarse spatial resolution
  python run_complete_analysis.py --country FRA --cd 4 --cg 3 --cr 3 --ekd 150 --ekg 50 --ekr 80
  
  # Structural sensitivity analysis - fine spatial resolution  
  python run_complete_analysis.py --country FRA --cd 16 --cg 12 --cr 8 --ekd 50 --ekg 15 --ekr 25
  
  # Enable OSM enhancements (if available)
  python run_complete_analysis.py --country DEU --enable-osm-industrial --enable-osm-grid
        """
    )
    
    parser.add_argument('--country', required=True,
                       help='ISO3 country code for analysis (e.g., USA, DEU, IND, FRA, GBR, etc.)')
    # Cluster count parameters (with short aliases for rapid iteration)
    parser.add_argument('--demand-regions', '--cd', type=int,
                       help='Number of demand regions (default: country-specific)')
    parser.add_argument('--gen-clusters', '--cg', type=int,
                       help='Number of generation clusters (default: country-specific)')
    parser.add_argument('--renewable-zones', '--cr', type=int,
                       help='Number of renewable zones (default: country-specific)')
    
    # Epsilon parameters for DBSCAN clustering (with short aliases)
    parser.add_argument('--eps-demand', '--ekd', type=float, default=100,
                       help='DBSCAN epsilon for demand clustering in km (default: 100)')
    parser.add_argument('--eps-generation', '--ekg', type=float, default=30,
                       help='DBSCAN epsilon for generation clustering in km (default: 30)')
    parser.add_argument('--eps-renewable', '--ekr', type=float, default=50,
                       help='DBSCAN epsilon for renewable clustering in km (default: 50)')
    
    # OSM enhancement options
    parser.add_argument('--enable-osm-industrial', action='store_true',
                       help='Enable OSM industrial facilities (disabled by default)')
    parser.add_argument('--enable-osm-grid', action='store_true',
                       help='Enable OSM grid infrastructure for NTC (disabled by default)')
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = MultiLayerAnalysisPipeline(
        country_code=args.country,
        demand_regions=args.demand_regions,
        gen_clusters=args.gen_clusters,
        renewable_zones=args.renewable_zones,
        enable_osm_industrial=args.enable_osm_industrial,
        enable_osm_grid=args.enable_osm_grid,
        eps_demand=args.eps_demand,
        eps_generation=args.eps_generation,
        eps_renewable=args.eps_renewable
    )
    
    success = pipeline.run_complete_pipeline()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
