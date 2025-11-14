#!/usr/bin/env python3
"""
One-time OSM Industrial Facilities Extraction Script

Extracts industrial facilities from raw OSM .pbf files and caches results as CSV.
Run this script whenever OSM data is updated to refresh the industrial facilities cache.

Usage:
    python extract_osm_industrial.py --country ITA
    python extract_osm_industrial.py --country DEU
    python extract_osm_industrial.py --country CHE
"""

import osmium
import pandas as pd
import os
import argparse
from pathlib import Path

class IndustrialFacilityExtractor(osmium.SimpleHandler):
    """
    OSM handler to extract industrial facilities and energy infrastructure
    """
    
    def __init__(self):
        osmium.SimpleHandler.__init__(self)
        self.facilities = []
        self.grid_infrastructure = []
        self.coal_infrastructure = []
        self.transport_corridors = []
        
        # Progress tracking
        self.processed_nodes = 0
        self.processed_ways = 0
        self.processed_relations = 0
        self.progress_interval = 100000  # Report every 100k objects
        
        # Define industrial facility types we're interested in
        self.industrial_types = {
            # Heavy industry
            'steel_mill': {'demand_estimate': 150, 'category': 'heavy_industry'},
            'aluminium_smelter': {'demand_estimate': 200, 'category': 'heavy_industry'},
            'cement_plant': {'demand_estimate': 80, 'category': 'heavy_industry'},
            'chemical': {'demand_estimate': 100, 'category': 'chemical'},
            'petrochemical': {'demand_estimate': 120, 'category': 'chemical'},
            'paper_mill': {'demand_estimate': 60, 'category': 'manufacturing'},
            
            # Manufacturing
            'automotive': {'demand_estimate': 40, 'category': 'manufacturing'},
            'electronics': {'demand_estimate': 30, 'category': 'manufacturing'},
            'food_processing': {'demand_estimate': 20, 'category': 'manufacturing'},
            'textile': {'demand_estimate': 15, 'category': 'manufacturing'},
            'machinery': {'demand_estimate': 25, 'category': 'manufacturing'},
            
            # Energy & utilities
            'refinery': {'demand_estimate': 100, 'category': 'energy'},
            'power_plant': {'demand_estimate': 0, 'category': 'energy'},  # Generator, not consumer
            'wastewater_plant': {'demand_estimate': 10, 'category': 'utilities'},
            'water_treatment': {'demand_estimate': 8, 'category': 'utilities'},
            
            # Data & tech
            'data_center': {'demand_estimate': 50, 'category': 'technology'},
            'server_farm': {'demand_estimate': 40, 'category': 'technology'},
        }
    
    def node(self, n):
        """Process OSM nodes (point facilities)"""
        self.processed_nodes += 1
        if self.processed_nodes % self.progress_interval == 0:
            print(f"  Processed {self.processed_nodes:,} nodes, found {len(self.facilities)} facilities so far...")
        
        # Quick filter: only process nodes with relevant tags
        if self._has_relevant_tags(dict(n.tags)):
            self._process_facility(n, 'node')
    
    def way(self, w):
        """Process OSM ways (area facilities)"""
        self.processed_ways += 1
        if self.processed_ways % (self.progress_interval // 10) == 0:  # Report ways more frequently
            print(f"  Processed {self.processed_ways:,} ways, found {len(self.facilities)} facilities, {len(self.grid_infrastructure)} grid elements...")
        
        # Quick filter: only process ways with relevant tags
        if self._has_relevant_tags(dict(w.tags)):
            self._process_facility(w, 'way')
    
    def relation(self, r):
        """Process OSM relations (complex facilities) - SKIP for performance"""
        self.processed_relations += 1
        # Skip relations for now - they're complex and slow to process
        return
    
    def _has_relevant_tags(self, tags):
        """Quick filter to check if object has potentially relevant tags"""
        # Check for key tags that indicate industrial/energy facilities
        relevant_keys = {
            'industrial', 'landuse', 'man_made', 'amenity', 'power', 
            'railway', 'cargo', 'plant:source', 'resource'
        }
        
        # Quick check: does this object have any relevant keys?
        if not any(key in tags for key in relevant_keys):
            return False
        
        # Additional quick filters
        landuse = tags.get('landuse', '')
        if landuse in ['industrial', 'quarry']:
            return True
            
        power = tags.get('power', '')
        if power in ['plant', 'substation', 'line', 'converter']:
            return True
            
        industrial = tags.get('industrial', '')
        if industrial:
            return True
            
        man_made = tags.get('man_made', '')
        if man_made in ['works', 'wastewater_plant']:
            return True
            
        railway = tags.get('railway', '')
        if railway in ['rail', 'narrow_gauge']:
            return True
            
        # Check for coal-related terms in name
        name = tags.get('name', '').lower()
        if 'coal' in name or tags.get('cargo') == 'coal':
            return True
            
        return False
    
    def _process_facility(self, obj, obj_type):
        """Extract facility information from OSM object"""
        tags = dict(obj.tags)
        
        # Check for grid infrastructure first
        self._extract_grid_infrastructure(obj, obj_type, tags)
        
        # Check for coal transport infrastructure
        self._process_coal_transport(obj, obj_type, tags)
        
        # Check for industrial facilities
        facility_info = self._identify_facility_type(tags)
        if not facility_info:
            return
        
        # Get coordinates (optimized)
        if obj_type == 'node':
            lat, lng = obj.location.lat, obj.location.lon
        elif obj_type == 'way':
            # Use simple centroid calculation - faster than full geometry
            try:
                nodes = list(obj.nodes)
                if not nodes:
                    return
                
                # For performance: use first, middle, and last nodes for approximation
                if len(nodes) <= 3:
                    coords = [(node.lat, node.lon) for node in nodes]
                else:
                    # Sample key nodes for faster processing
                    sample_nodes = [nodes[0], nodes[len(nodes)//2], nodes[-1]]
                    coords = [(node.lat, node.lon) for node in sample_nodes]
                
                if coords:
                    lat = sum(c[0] for c in coords) / len(coords)
                    lng = sum(c[1] for c in coords) / len(coords)
                else:
                    return
            except:
                return
        else:
            # Skip relations for now (complex geometries)
            return
        
        # Extract facility details
        facility = {
            'osm_id': f"{obj_type}/{obj.id}",
            'name': tags.get('name', f"Unnamed {facility_info['type']}"),
            'lat': lat,
            'lng': lng,
            'facility_type': facility_info['type'],
            'category': facility_info['category'],
            'estimated_demand_mw': facility_info['demand_estimate'],
            'employees': self._extract_numeric_tag(tags, 'employees'),
            'operator': tags.get('operator', ''),
            'industrial_tag': tags.get('industrial', ''),
            'landuse_tag': tags.get('landuse', ''),
            'man_made_tag': tags.get('man_made', ''),
            'amenity_tag': tags.get('amenity', ''),
            'power_tag': tags.get('power', ''),
            'all_tags': str(tags)
        }
        
        self.facilities.append(facility)
    
    def _identify_facility_type(self, tags):
        """Identify if this is an industrial facility and what type"""
        
        # Check specific industrial types
        if 'industrial' in tags:
            industrial_type = tags['industrial']
            if industrial_type in self.industrial_types:
                return {
                    'type': industrial_type,
                    'category': self.industrial_types[industrial_type]['category'],
                    'demand_estimate': self.industrial_types[industrial_type]['demand_estimate']
                }
        
        # Check man_made facilities
        if 'man_made' in tags:
            man_made = tags['man_made']
            if man_made == 'works':
                # Generic industrial works - try to classify further
                return {
                    'type': 'industrial_works',
                    'category': 'manufacturing',
                    'demand_estimate': 30
                }
            elif man_made == 'wastewater_plant':
                return {
                    'type': 'wastewater_plant',
                    'category': 'utilities',
                    'demand_estimate': 10
                }
        
        # Check amenity facilities
        if 'amenity' in tags:
            amenity = tags['amenity']
            if amenity == 'fuel':
                return {
                    'type': 'refinery',
                    'category': 'energy',
                    'demand_estimate': 100
                }
        
        # Check power facilities
        if 'power' in tags:
            power_type = tags['power']
            if power_type == 'plant':
                return {
                    'type': 'power_plant',
                    'category': 'energy',
                    'demand_estimate': 0  # Generator, not consumer
                }
        
        # Check general industrial landuse
        if tags.get('landuse') == 'industrial':
            # Large industrial area - estimate based on size or default
            return {
                'type': 'industrial_area',
                'category': 'mixed_industrial',
                'demand_estimate': 50
            }
        
        return None
    
    def _extract_numeric_tag(self, tags, key):
        """Extract numeric value from tag, handling various formats"""
        if key not in tags:
            return None
        
        value = tags[key]
        try:
            # Handle ranges like "100-200"
            if '-' in value:
                parts = value.split('-')
                return int(parts[0])
            # Handle approximate values like "~500"
            if value.startswith('~'):
                return int(value[1:])
            # Handle direct numbers
            return int(value)
        except:
            return None
    
    def _extract_grid_infrastructure(self, obj, obj_type, tags):
        """Extract electrical grid infrastructure"""
        
        # Get coordinates
        if obj_type == 'node':
            lat, lng = obj.location.lat, obj.location.lon
        elif obj_type == 'way':
            # Use centroid of way
            try:
                coords = [(node.lat, node.lon) for node in obj.nodes]
                if coords:
                    lat = sum(c[0] for c in coords) / len(coords)
                    lng = sum(c[1] for c in coords) / len(coords)
                    # Store geometry for transmission lines
                    way_geometry = coords
                else:
                    return
            except:
                return
        else:
            # Skip relations for now
            return
        
        # 1. SUBSTATIONS
        if tags.get('power') == 'substation':
            self.grid_infrastructure.append({
                'type': 'substation',
                'name': tags.get('name'),
                'lat': lat,
                'lng': lng,
                'voltage_kv': self._extract_voltage(tags),
                'operator': tags.get('operator'),
                'osm_id': f"{obj_type}/{obj.id}",
            })
        
        # 2. POWER PLANTS
        elif tags.get('power') == 'plant':
            self.grid_infrastructure.append({
                'type': 'power_plant',
                'name': tags.get('name'),
                'lat': lat,
                'lng': lng,
                'capacity_mw': self._extract_capacity(tags),
                'source': tags.get('plant:source'),
                'operator': tags.get('operator'),
                'osm_id': f"{obj_type}/{obj.id}",
            })
        
        # 3. TRANSMISSION LINES
        elif tags.get('power') == 'line':
            self.grid_infrastructure.append({
                'type': 'transmission_line',
                'name': tags.get('name'),
                'voltage_kv': self._extract_voltage(tags),
                'capacity_mw': tags.get('capacity'),
                'countries': tags.get('countries'),  # Connected countries
                'operator': tags.get('operator'),
                'osm_id': f"{obj_type}/{obj.id}",
                'geometry': str(way_geometry) if obj_type == 'way' else None,
            })
        
        # 4. CONVERTER STATIONS (AC/DC)
        elif tags.get('power') == 'converter':
            self.grid_infrastructure.append({
                'type': 'converter_station',
                'name': tags.get('name'),
                'lat': lat,
                'lng': lng,
                'voltage_kv': self._extract_voltage(tags),
                'converter': tags.get('converter'),  # Type of converter
                'capacity_mw': tags.get('rating'),
                'osm_id': f"{obj_type}/{obj.id}",
            })
    
    def _extract_voltage(self, tags):
        """Extract voltage in kV from various tag formats"""
        voltage_str = tags.get('voltage', '')
        if not voltage_str:
            return None
        
        # Handle multiple voltages (e.g., "380000;220000")
        if ';' in voltage_str:
            voltages = voltage_str.split(';')
            voltage_str = voltages[0]  # Take highest
        
        try:
            voltage = float(voltage_str)
            if voltage > 1000:  # Convert from V to kV
                voltage = voltage / 1000
            return voltage
        except:
            return None
    
    def _extract_capacity(self, tags):
        """Extract power plant capacity in MW"""
        # Try different tag formats
        capacity_tags = [
            'plant:output:electricity',
            'generator:output:electricity',
            'capacity'
        ]
        
        for tag in capacity_tags:
            if tag in tags:
                value = tags[tag]
                # Parse values like "1000 MW" or "1000"
                if 'MW' in value:
                    return float(value.replace('MW', '').strip())
                elif 'GW' in value:
                    return float(value.replace('GW', '').strip()) * 1000
                else:
                    try:
                        return float(value)
                    except:
                        continue
        return None
    
    def _process_coal_transport(self, obj, obj_type, tags):
        """Extract coal transport infrastructure"""
        
        # Get coordinates
        if obj_type == 'node':
            lat, lng = obj.location.lat, obj.location.lon
        elif obj_type == 'way':
            # Use centroid of way
            try:
                coords = [(node.lat, node.lon) for node in obj.nodes]
                if coords:
                    lat = sum(c[0] for c in coords) / len(coords)
                    lng = sum(c[1] for c in coords) / len(coords)
                    # Store geometry for transport corridors
                    way_geometry = coords
                else:
                    return
            except:
                return
        else:
            # Skip relations for now
            return
        
        # 1. COAL TERMINALS & PORTS
        if tags.get('cargo') == 'coal' or 'coal' in tags.get('name', '').lower():
            self.coal_infrastructure.append({
                'type': 'coal_terminal',
                'subtype': tags.get('harbour') or tags.get('landuse'),
                'name': tags.get('name'),
                'lat': lat,
                'lng': lng,
                'capacity': tags.get('capacity'),
                'operator': tags.get('operator'),
                'railway': tags.get('railway'),  # Rail connected?
                'osm_id': f"{obj_type}/{obj.id}",
            })
        
        # 2. RAILWAY LINES (for coal transport)
        if tags.get('railway') in ['rail', 'narrow_gauge']:
            # Check if it's freight/industrial
            if tags.get('usage') in ['freight', 'industrial', 'military']:
                self.transport_corridors.append({
                    'type': 'freight_rail',
                    'name': tags.get('name'),
                    'usage': tags.get('usage'),
                    'electrified': tags.get('electrified'),
                    'tracks': tags.get('tracks', 'single'),
                    'maxspeed': tags.get('maxspeed:freight'),
                    'operator': tags.get('operator'),
                    'osm_id': f"{obj_type}/{obj.id}",
                    'geometry': str(way_geometry) if obj_type == 'way' else None,
                })
        
        # 3. COAL MINES/SOURCES
        if tags.get('landuse') == 'quarry' and tags.get('resource') == 'coal':
            self.coal_infrastructure.append({
                'type': 'coal_mine',
                'name': tags.get('name'),
                'lat': lat,
                'lng': lng,
                'operator': tags.get('operator'),
                'status': tags.get('disused') or 'active',
                'osm_id': f"{obj_type}/{obj.id}",
            })
        
        # 4. COAL POWER PLANTS (major consumers)
        if tags.get('power') == 'plant':
            source = tags.get('plant:source', '').lower()
            if 'coal' in source:
                self.coal_infrastructure.append({
                    'type': 'coal_power_plant',
                    'name': tags.get('name'),
                    'lat': lat,
                    'lng': lng,
                    'capacity_mw': self._extract_capacity(tags),
                    'operator': tags.get('operator'),
                    'osm_id': f"{obj_type}/{obj.id}",
                })

def extract_industrial_facilities(country_code, osm_file_path, output_dir):
    """
    Extract industrial facilities from OSM file and save to CSV
    """
    print(f"Extracting industrial facilities for {country_code}...")
    print(f"Processing OSM file: {osm_file_path}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize extractor
    extractor = IndustrialFacilityExtractor()
    
    # Process OSM file
    print("Parsing OSM data with optimized streaming...")
    print("Progress will be reported every 100k nodes and 10k ways")
    
    import time
    start_time = time.time()
    
    extractor.apply_file(osm_file_path)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"\n📊 Processing completed in {processing_time:.1f} seconds")
    print(f"📈 Processed {extractor.processed_nodes:,} nodes, {extractor.processed_ways:,} ways, {extractor.processed_relations:,} relations")
    
    # Convert to DataFrames
    facilities_df = pd.DataFrame(extractor.facilities)
    grid_df = pd.DataFrame(extractor.grid_infrastructure)
    coal_df = pd.DataFrame(extractor.coal_infrastructure)
    transport_df = pd.DataFrame(extractor.transport_corridors)
    
    print(f"Found {len(facilities_df)} industrial facilities")
    print(f"Found {len(grid_df)} grid infrastructure elements")
    print(f"Found {len(coal_df)} coal infrastructure elements")
    print(f"Found {len(transport_df)} transport corridors")
    
    if len(facilities_df) == 0 and len(grid_df) == 0:
        print("No facilities or infrastructure found!")
        return
    
    # Process industrial facilities
    if len(facilities_df) > 0:
        # Add country code and facility IDs
        facilities_df['country'] = country_code
        facilities_df['facility_id'] = [f"{country_code}_IND_{i:04d}" for i in range(len(facilities_df))]
        
        # Reorder columns
        facilities_columns = [
            'country', 'facility_id', 'name', 'lat', 'lng', 'facility_type', 
            'category', 'estimated_demand_mw', 'employees', 'operator',
            'osm_id', 'industrial_tag', 'landuse_tag', 'man_made_tag', 
            'amenity_tag', 'power_tag', 'all_tags'
        ]
        facilities_df = facilities_df[facilities_columns]
        
        # Save industrial facilities
        facilities_file = os.path.join(output_dir, f"{country_code.lower()}_industrial.csv")
        facilities_df.to_csv(facilities_file, index=False)
    
    # Process grid infrastructure
    if len(grid_df) > 0:
        # Add country code and infrastructure IDs
        grid_df['country'] = country_code
        grid_df['infrastructure_id'] = [f"{country_code}_GRID_{i:04d}" for i in range(len(grid_df))]
        
        # Save grid infrastructure
        grid_file = os.path.join(output_dir, f"{country_code.lower()}_grid_infrastructure.csv")
        grid_df.to_csv(grid_file, index=False)
    
    # Process coal infrastructure
    if len(coal_df) > 0:
        # Add country code and infrastructure IDs
        coal_df['country'] = country_code
        coal_df['coal_id'] = [f"{country_code}_COAL_{i:04d}" for i in range(len(coal_df))]
        
        # Save coal infrastructure
        coal_file = os.path.join(output_dir, f"{country_code.lower()}_coal_infrastructure.csv")
        coal_df.to_csv(coal_file, index=False)
    
    # Process transport corridors
    if len(transport_df) > 0:
        # Add country code and transport IDs
        transport_df['country'] = country_code
        transport_df['transport_id'] = [f"{country_code}_TRANS_{i:04d}" for i in range(len(transport_df))]
        
        # Save transport corridors
        transport_file = os.path.join(output_dir, f"{country_code.lower()}_transport_corridors.csv")
        transport_df.to_csv(transport_file, index=False)
    
    # Print summary
    print(f"\n✅ Extraction complete!")
    
    if len(facilities_df) > 0:
        print(f"Industrial facilities: {len(facilities_df)}")
        print(f"Saved to: {facilities_file}")
        
        # Print breakdown by category
        print(f"\nFacility breakdown:")
        category_counts = facilities_df['category'].value_counts()
        for category, count in category_counts.items():
            print(f"  {category}: {count} facilities")
        
        # Print breakdown by type (top 10)
        print(f"\nTop facility types:")
        type_counts = facilities_df['facility_type'].value_counts().head(10)
        for facility_type, count in type_counts.items():
            print(f"  {facility_type}: {count}")
        
        # Estimate total demand
        total_demand = facilities_df['estimated_demand_mw'].sum()
        print(f"\nEstimated total industrial demand: {total_demand:,.0f} MW")
    
    if len(grid_df) > 0:
        print(f"\nGrid infrastructure: {len(grid_df)}")
        print(f"Saved to: {grid_file}")
        
        # Print breakdown by infrastructure type
        print(f"\nInfrastructure breakdown:")
        infra_counts = grid_df['type'].value_counts()
        for infra_type, count in infra_counts.items():
            print(f"  {infra_type}: {count}")
    
    if len(coal_df) > 0:
        print(f"\nCoal infrastructure: {len(coal_df)}")
        print(f"Saved to: {coal_file}")
        
        # Print breakdown by coal infrastructure type
        print(f"\nCoal infrastructure breakdown:")
        coal_counts = coal_df['type'].value_counts()
        for coal_type, count in coal_counts.items():
            print(f"  {coal_type}: {count}")
    
    if len(transport_df) > 0:
        print(f"\nTransport corridors: {len(transport_df)}")
        print(f"Saved to: {transport_file}")
        
        # Print breakdown by transport type
        print(f"\nTransport breakdown:")
        transport_counts = transport_df['type'].value_counts()
        for transport_type, count in transport_counts.items():
            print(f"  {transport_type}: {count}")
    
    return facilities_df, grid_df, coal_df, transport_df

def main():
    parser = argparse.ArgumentParser(description='Extract industrial facilities from OSM data')
    parser.add_argument('--country', required=True, 
                       choices=['ITA', 'DEU', 'CHE', 'USA', 'AUS', 'CHN', 'IND', 'JPN', 'ZAF', 'NZL', 'BRA'],
                       help='Country code (ITA, DEU, CHE, USA, AUS, CHN, IND, JPN, ZAF, NZL, BRA)')
    parser.add_argument('--output-dir', default='cache/industrial',
                       help='Output directory for cached results')
    
    args = parser.parse_args()
    
    # Map country codes to OSM files
    osm_files = {
        'ITA': '../data/OSM/italy-latest.osm.pbf',
        'DEU': '../data/OSM/germany-latest.osm.pbf', 
        'CHE': '../data/OSM/switzerland-latest.osm.pbf',
        'USA': '../data/OSM/us-latest.osm.pbf',
        'AUS': '../data/OSM/australia-latest.osm.pbf',
        'CHN': '../data/OSM/china-latest.osm.pbf',
        'IND': '../data/OSM/india-latest.osm.pbf',
        'JPN': '../data/OSM/japan-latest.osm.pbf',
        'ZAF': '../data/OSM/south-africa-latest.osm.pbf',
        'NZL': '../data/OSM/new-zealand-latest.osm.pbf',
        'BRA': '../data/OSM/brazil-latest.osm.pbf'
    }
    
    osm_file = osm_files[args.country]
    
    # Check if OSM file exists
    if not os.path.exists(osm_file):
        print(f"❌ OSM file not found: {osm_file}")
        print("Please ensure the OSM .pbf file is downloaded to the data/OSM/ directory")
        return
    
    # Extract facilities
    print(f"\n🚀 Starting OSM data extraction for {args.country}...")
    results = extract_industrial_facilities(args.country, osm_file, args.output_dir)
    
    # Final completion summary
    if results:
        facilities_df, grid_df, coal_df, transport_df = results
        
        print(f"\n" + "="*60)
        print(f"🎉 OSM EXTRACTION COMPLETED SUCCESSFULLY FOR {args.country}")
        print(f"="*60)
        
        print(f"\n📊 FINAL SUMMARY:")
        print(f"  ✅ Industrial facilities: {len(facilities_df) if len(facilities_df) > 0 else 0}")
        print(f"  ✅ Grid infrastructure: {len(grid_df) if len(grid_df) > 0 else 0}")
        print(f"  ✅ Coal infrastructure: {len(coal_df) if len(coal_df) > 0 else 0}")
        print(f"  ✅ Transport corridors: {len(transport_df) if len(transport_df) > 0 else 0}")
        
        print(f"\n📁 All data cached to: {args.output_dir}")
        print(f"🔄 Ready for multi-region analysis!")
        print(f"\n💡 Next step: python create_regions.py --country {args.country}")
        print(f"="*60)
    else:
        print(f"\n❌ Extraction failed or no data found for {args.country}")

if __name__ == "__main__":
    main()
