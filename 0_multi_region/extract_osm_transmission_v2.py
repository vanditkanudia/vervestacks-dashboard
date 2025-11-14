#!/usr/bin/env python3
"""
OSM Power Transmission Infrastructure Extraction Script - Enhanced for Relations
"""

import osmium
import pandas as pd
import os
import argparse
from pathlib import Path
import re
from collections import defaultdict

class PowerTransmissionExtractor(osmium.SimpleHandler):
    """
    OSM handler with two-pass processing for route relations
    """
    
    def __init__(self, min_voltage_kv=0, debug=False):
        osmium.SimpleHandler.__init__(self)
        self.transmission_lines = []
        self.substations = []
        self.power_plants = []
        self.converters = []
        
        self.min_voltage_kv = min_voltage_kv
        self.debug = debug
        
        # Store ways and nodes for relation processing
        self.way_cache = {}  # way_id -> way_data
        self.node_cache = {}  # node_id -> (lat, lon)
        self.power_relations = []  # Store relations for second pass
        
        # Progress tracking
        self.processed_nodes = 0
        self.processed_ways = 0
        self.processed_relations = 0
        self.progress_interval = 50000
        
        # Statistics
        self.power_objects_found = 0
        self.lines_found = 0
        self.substations_found = 0
        self.plants_found = 0
        self.relations_processed = 0
        
    def node(self, n):
        """Process and cache OSM nodes"""
        self.processed_nodes += 1
        if self.processed_nodes % self.progress_interval == 0:
            print(f"  Nodes: {self.processed_nodes:,} | Power objects: {self.power_objects_found:,}")
        
        # Cache node coordinates for later use
        try:
            self.node_cache[n.id] = (n.location.lat, n.location.lon)
        except:
            pass
        
        tags = dict(n.tags)
        if self._is_power_infrastructure(tags):
            self.power_objects_found += 1
            self._process_power_infrastructure(n, 'node', tags)
    
    def way(self, w):
        """Process and cache OSM ways"""
        self.processed_ways += 1
        if self.processed_ways % (self.progress_interval // 5) == 0:
            print(f"  Ways: {self.processed_ways:,} | Lines: {self.lines_found:,} | Substations: {self.substations_found:,}")
        
        tags = dict(w.tags)
        
        # Cache way data for relation processing
        way_nodes = []
        for node in w.nodes:
            if node.ref in self.node_cache:
                way_nodes.append(self.node_cache[node.ref])
        
        if way_nodes:
            self.way_cache[w.id] = {
                'tags': tags,
                'nodes': way_nodes
            }
        
        # Process way if it's power infrastructure
        if self._is_power_infrastructure(tags):
            self.power_objects_found += 1
            self._process_power_infrastructure(w, 'way', tags)
    
    def relation(self, r):
        """Store relations for second pass processing"""
        self.processed_relations += 1
        
        tags = dict(r.tags)
        
        # Store power route relations for second pass
        if tags.get('type') == 'route' and tags.get('route') == 'power':
            # Extract member way IDs
            member_ways = []
            for member in r.members:
                if member.type == 'w':  # way member
                    member_ways.append(member.ref)
            
            self.power_relations.append({
                'id': r.id,
                'tags': tags,
                'member_ways': member_ways
            })
            
            if self.debug:
                print(f"Found power route relation {r.id} with {len(member_ways)} member ways")
        
        # Also process direct power infrastructure relations
        elif self._is_power_infrastructure(tags):
            self.power_objects_found += 1
            self._process_power_infrastructure(r, 'relation', tags)
    
    def process_relations_second_pass(self):
        """
        Second pass to process route relations using cached way data
        """
        print(f"\nProcessing {len(self.power_relations)} power route relations...")
        
        for relation in self.power_relations:
            self.relations_processed += 1
            
            # Collect all coordinates from member ways
            all_coords = []
            total_length = 0
            voltages = []
            
            for way_id in relation['member_ways']:
                if way_id in self.way_cache:
                    way_data = self.way_cache[way_id]
                    all_coords.extend(way_data['nodes'])
                    
                    # Extract voltage from way if available
                    way_voltage = self._extract_voltage(way_data['tags'])
                    if way_voltage:
                        voltages.append(way_voltage)
                    
                    # Calculate segment length
                    if len(way_data['nodes']) >= 2:
                        segment_length = self._calculate_line_length(way_data['nodes'])
                        if segment_length:
                            total_length += segment_length
            
            if not all_coords:
                if self.debug:
                    print(f"  Relation {relation['id']}: No cached ways found")
                continue
            
            # Calculate centroid from all coordinates
            lat = sum(coord[0] for coord in all_coords) / len(all_coords)
            lng = sum(coord[1] for coord in all_coords) / len(all_coords)
            
            # Use relation voltage or max way voltage
            relation_voltage = self._extract_voltage(relation['tags'])
            if not relation_voltage and voltages:
                relation_voltage = max(voltages)
            
            # Apply voltage filter
            if self.min_voltage_kv > 0 and relation_voltage:
                if relation_voltage < self.min_voltage_kv:
                    continue
            
            # Create transmission line entry
            line_data = {
                'osm_id': f"relation/{relation['id']}",
                'osm_type': 'relation',
                'name': relation['tags'].get('name', ''),
                'lat': lat,
                'lng': lng,
                'operator': relation['tags'].get('operator', ''),
                'voltage_kv': relation_voltage,
                'type': 'transmission_line',
                'power_type': 'route',
                'from_location': relation['tags'].get('from', ''),
                'to_location': relation['tags'].get('to', ''),
                'cables': self._extract_numeric_value(relation['tags'], 'cables'),
                'circuits': self._extract_numeric_value(relation['tags'], 'circuits'),
                'frequency': self._extract_numeric_value(relation['tags'], 'frequency'),
                'ref': relation['tags'].get('ref', ''),
                'countries': relation['tags'].get('countries', ''),
                'geometry_length_km': total_length if total_length > 0 else None,
                'num_member_ways': len(relation['member_ways']),
                'num_cached_ways': len([w for w in relation['member_ways'] if w in self.way_cache]),
                'route_relation': True,
                'all_tags': str(relation['tags'])
            }
            
            self.transmission_lines.append(line_data)
            self.lines_found += 1
            
            if self.debug:
                print(f"  Added relation {relation['id']}: {relation_voltage}kV, {total_length:.1f}km, "
                      f"{len(all_coords)} points from {line_data['num_cached_ways']} ways")
    
    def _is_power_infrastructure(self, tags):
        """Check if object is power transmission infrastructure"""
        # Primary power tags
        power_tag = tags.get('power', '')
        if power_tag in ['line', 'cable', 'minor_line', 'substation', 'plant', 'generator', 'converter']:
            return True
        
        # Route relations handled separately in relation() method
        
        # Voltage indicates transmission infrastructure
        if 'voltage' in tags:
            return True
        
        # Energy-related landuse
        if tags.get('landuse') == 'industrial' and 'power' in tags.get('name', '').lower():
            return True
        
        # Specific power plant indicators
        if any(key.startswith('plant:') for key in tags.keys()):
            return True
        
        if any(key.startswith('generator:') for key in tags.keys()):
            return True
        
        return False
    
    def _process_power_infrastructure(self, obj, obj_type, tags):
        """Process power infrastructure object (excluding route relations)"""
        
        if self.debug:
            print(f"Processing {obj_type} {obj.id}: power={tags.get('power', 'none')}, "
                  f"voltage={tags.get('voltage', 'none')}")
        
        # Get coordinates and geometry
        coords_data = self._extract_coordinates_and_geometry(obj, obj_type)
        if not coords_data:
            return
        
        lat, lng, geometry = coords_data
        
        # Extract common attributes
        common_attrs = {
            'osm_id': f"{obj_type}/{obj.id}",
            'osm_type': obj_type,
            'name': tags.get('name', ''),
            'lat': lat,
            'lng': lng,
            'operator': tags.get('operator', ''),
            'voltage_kv': self._extract_voltage(tags),
            'all_tags': str(tags)
        }
        
        # Apply voltage filter
        if self.min_voltage_kv > 0 and common_attrs['voltage_kv']:
            if common_attrs['voltage_kv'] < self.min_voltage_kv:
                if self.debug:
                    print(f"  Filtered out: {common_attrs['voltage_kv']}kV < {self.min_voltage_kv}kV")
                return
        
        # Process by power infrastructure type
        power_type = tags.get('power', '')
        
        if power_type in ['line', 'cable', 'minor_line']:
            self._process_transmission_line(tags, common_attrs, geometry)
        elif power_type in ['substation', 'sub_station']:
            self._process_substation(tags, common_attrs)
        elif power_type in ['plant', 'generator']:
            self._process_power_plant(tags, common_attrs)
        elif power_type == 'converter':
            self._process_converter(tags, common_attrs)
        elif 'voltage' in tags or any(key.startswith('plant:') for key in tags.keys()):
            # Catch other power infrastructure based on voltage or plant tags
            self._process_other_power_infrastructure(tags, common_attrs)
    
    def _extract_coordinates_and_geometry(self, obj, obj_type):
        """Extract coordinates and geometry from OSM object"""
        try:
            if obj_type == 'node':
                if obj.id in self.node_cache:
                    lat, lon = self.node_cache[obj.id]
                    return lat, lon, None
                return obj.location.lat, obj.location.lon, None
            
            elif obj_type == 'way':
                # Use cached nodes if available
                if obj.id in self.way_cache:
                    coords = self.way_cache[obj.id]['nodes']
                    if coords:
                        lat = sum(c[0] for c in coords) / len(coords)
                        lng = sum(c[1] for c in coords) / len(coords)
                        return lat, lng, coords
                
                # Fallback to direct processing
                nodes = list(obj.nodes)
                if not nodes:
                    return None
                
                coords = []
                for node in nodes:
                    if node.ref in self.node_cache:
                        coords.append(self.node_cache[node.ref])
                
                if not coords:
                    return None
                
                lat = sum(c[0] for c in coords) / len(coords)
                lng = sum(c[1] for c in coords) / len(coords)
                
                return lat, lng, coords
            
            elif obj_type == 'relation':
                # Relations without geometry handled in second pass
                return 0.0, 0.0, None
            
        except Exception as e:
            if self.debug:
                print(f"Error extracting coordinates from {obj_type} {obj.id}: {e}")
            return None
        
        return None
    
    def _process_transmission_line(self, tags, common_attrs, geometry):
        """Process transmission/power lines"""
        self.lines_found += 1
        
        line_data = {
            **common_attrs,
            'type': 'transmission_line',
            'power_type': tags.get('power'),
            'cables': self._extract_numeric_value(tags, 'cables'),
            'circuits': self._extract_numeric_value(tags, 'circuits'),
            'frequency': self._extract_numeric_value(tags, 'frequency'),
            'location': tags.get('location', ''),  # underground, overhead, etc.
            'material': tags.get('material', ''),
            'structure': tags.get('structure', ''),
            'countries': tags.get('countries', ''),  # For cross-border lines
            'ref': tags.get('ref', ''),  # Line reference number
            'wires': self._extract_numeric_value(tags, 'wires'),
            'geometry_coords': str(geometry) if geometry else None,
            'geometry_length_km': self._calculate_line_length(geometry) if geometry else None,
            'route_relation': False
        }
        
        self.transmission_lines.append(line_data)
        
        if self.debug:
            print(f"  Added line: {line_data['voltage_kv']}kV, {line_data['power_type']}")
    
    def _process_substation(self, tags, common_attrs):
        """Process substations and switching stations"""
        self.substations_found += 1
        
        substation_data = {
            **common_attrs,
            'type': 'substation',
            'substation_type': tags.get('substation', ''),
            'switching': tags.get('switching', ''),
            'compensation': tags.get('compensation', ''),
            'frequency': self._extract_numeric_value(tags, 'frequency'),
            'ref': tags.get('ref', ''),
            'location': tags.get('location', ''),
        }
        
        self.substations.append(substation_data)
    
    def _process_power_plant(self, tags, common_attrs):
        """Process power plants and generators"""
        self.plants_found += 1
        
        plant_data = {
            **common_attrs,
            'type': 'power_plant',
            'plant_source': tags.get('plant:source', ''),
            'plant_method': tags.get('plant:method', ''),
            'plant_output_electricity': tags.get('plant:output:electricity', ''),
            'generator_source': tags.get('generator:source', ''),
            'generator_method': tags.get('generator:method', ''),
            'generator_output_electricity': tags.get('generator:output:electricity', ''),
            'capacity_mw': self._extract_capacity(tags),
            'commissioned': tags.get('start_date', ''),
            'decommissioned': tags.get('end_date', ''),
            'status': tags.get('operational_status', ''),
        }
        
        self.power_plants.append(plant_data)
    
    def _process_converter(self, tags, common_attrs):
        """Process converter stations (AC/DC)"""
        converter_data = {
            **common_attrs,
            'type': 'converter_station',
            'converter_type': tags.get('converter', ''),
            'frequency': self._extract_numeric_value(tags, 'frequency'),
            'rating': tags.get('rating', ''),
        }
        
        self.converters.append(converter_data)
    
    def _process_other_power_infrastructure(self, tags, common_attrs):
        """Process other power infrastructure not caught by main categories"""
        # Determine type based on available tags
        if any(key.startswith('plant:') for key in tags.keys()):
            self._process_power_plant(tags, common_attrs)
        elif 'voltage' in tags:
            # Treat as generic power infrastructure
            other_data = {
                **common_attrs,
                'type': 'power_infrastructure',
                'infrastructure_type': 'unknown',
            }
            # Add to appropriate category based on context
            self.substations.append(other_data)
    
    def _extract_voltage(self, tags):
        """Extract voltage in kV from various tag formats"""
        voltage_str = tags.get('voltage', '')
        if not voltage_str:
            return None
        
        # Handle multiple voltages (e.g., "380000;220000")
        if ';' in voltage_str:
            voltages = voltage_str.split(';')
            # Take the highest voltage
            voltage_str = max(voltages, key=lambda x: self._parse_voltage(x) or 0)
        
        return self._parse_voltage(voltage_str)
    
    def _parse_voltage(self, voltage_str):
        """Parse voltage string to kV float"""
        if not voltage_str:
            return None
        
        # Remove units and extra characters
        voltage_clean = re.sub(r'[^\d.]', '', voltage_str)
        
        try:
            voltage = float(voltage_clean)
            
            # Convert to kV based on magnitude
            if voltage > 100000:  # Voltage in V
                return voltage / 1000
            elif voltage > 1000:  # Voltage in V
                return voltage / 1000
            else:  # Already in kV
                return voltage
        except:
            return None
    
    def _extract_capacity(self, tags):
        """Extract power plant capacity in MW"""
        capacity_tags = [
            'plant:output:electricity',
            'generator:output:electricity',
            'capacity',
            'rating'
        ]
        
        for tag in capacity_tags:
            if tag in tags:
                value = tags[tag]
                capacity = self._parse_capacity(value)
                if capacity:
                    return capacity
        
        return None
    
    def _parse_capacity(self, capacity_str):
        """Parse capacity string to MW float"""
        if not capacity_str:
            return None
        
        capacity_str = capacity_str.upper()
        
        # Extract number
        numbers = re.findall(r'[\d.]+', capacity_str)
        if not numbers:
            return None
        
        try:
            value = float(numbers[0])
            
            # Convert to MW based on units
            if 'GW' in capacity_str:
                return value * 1000
            elif 'KW' in capacity_str:
                return value / 1000
            else:  # Assume MW or no unit
                return value
        except:
            return None
    
    def _extract_numeric_value(self, tags, key):
        """Extract numeric value from tag"""
        if key not in tags:
            return None
        
        value = tags[key]
        numbers = re.findall(r'\d+', value)
        if numbers:
            try:
                return int(numbers[0])
            except:
                pass
        return None
    
    def _calculate_line_length(self, geometry):
        """Calculate approximate length of transmission line in km"""
        if not geometry or len(geometry) < 2:
            return None
        
        try:
            # Simple haversine distance calculation
            from math import radians, cos, sin, asin, sqrt
            
            total_length = 0
            for i in range(len(geometry) - 1):
                lat1, lon1 = geometry[i]
                lat2, lon2 = geometry[i + 1]
                
                # Convert to radians
                lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                
                # Haversine formula
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                r = 6371  # Earth radius in km
                
                segment_length = c * r
                total_length += segment_length
            
            return round(total_length, 2)
        except:
            return None

def extract_transmission_infrastructure(country_code, osm_file_path, output_dir, min_voltage_kv=0, debug=False):
    """
    Extract power transmission infrastructure from OSM file and save to CSV
    """
    print(f"Extracting power transmission infrastructure for {country_code}...")
    print(f"Processing OSM file: {osm_file_path}")
    if min_voltage_kv > 0:
        print(f"Minimum voltage filter: {min_voltage_kv} kV")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize extractor
    extractor = PowerTransmissionExtractor(min_voltage_kv=min_voltage_kv, debug=debug)
    
    # First pass: process OSM file
    print("\n🔍 FIRST PASS: Parsing OSM data for power infrastructure...")
    print("Progress will be reported every 50k nodes and 10k ways")
    
    import time
    start_time = time.time()
    
    extractor.apply_file(osm_file_path)
    
    first_pass_time = time.time() - start_time
    
    print(f"\n✅ First pass completed in {first_pass_time:.1f} seconds")
    print(f"📈 Processed {extractor.processed_nodes:,} nodes, {extractor.processed_ways:,} ways, {extractor.processed_relations:,} relations")
    print(f"🔌 Found {extractor.power_objects_found:,} direct power objects")
    print(f"📦 Cached {len(extractor.way_cache):,} ways and {len(extractor.node_cache):,} nodes")
    print(f"🔗 Found {len(extractor.power_relations):,} power route relations to process")
    
    # Second pass: process relations
    print("\n🔍 SECOND PASS: Processing power route relations...")
    second_pass_start = time.time()
    
    extractor.process_relations_second_pass()
    
    second_pass_time = time.time() - second_pass_start
    total_time = time.time() - start_time
    
    print(f"✅ Second pass completed in {second_pass_time:.1f} seconds")
    print(f"📊 Total processing time: {total_time:.1f} seconds")
    print(f"🔗 Processed {extractor.relations_processed} route relations")
    
    # Convert to DataFrames
    lines_df = pd.DataFrame(extractor.transmission_lines)
    substations_df = pd.DataFrame(extractor.substations)
    plants_df = pd.DataFrame(extractor.power_plants)
    converters_df = pd.DataFrame(extractor.converters)
    
    print(f"\n📋 EXTRACTION RESULTS:")
    print(f"  Transmission lines: {len(lines_df)}")
    if len(lines_df) > 0:
        relation_lines = lines_df[lines_df['route_relation'] == True]
        way_lines = lines_df[lines_df['route_relation'] == False]
        print(f"    - From ways: {len(way_lines)}")
        print(f"    - From route relations: {len(relation_lines)}")
    print(f"  Substations: {len(substations_df)}")
    print(f"  Power plants: {len(plants_df)}")
    print(f"  Converters: {len(converters_df)}")
    
    if len(lines_df) == 0 and len(substations_df) == 0 and len(plants_df) == 0:
        print("⚠️  No power infrastructure found!")
        return None
    
    # Save results
    results = {}
    
    if len(lines_df) > 0:
        lines_df['country'] = country_code
        lines_file = os.path.join(output_dir, f"{country_code.lower()}_transmission_lines.csv")
        lines_df.to_csv(lines_file, index=False)
        results['lines'] = lines_df
        print(f"  ✅ Transmission lines saved to: {lines_file}")
        
        # Voltage breakdown
        if 'voltage_kv' in lines_df.columns:
            voltage_counts = lines_df['voltage_kv'].value_counts().sort_index()
            print(f"     Voltage levels found: {dict(voltage_counts.head(10))}")
            
            # Show route vs way breakdown
            if 'route_relation' in lines_df.columns:
                print(f"     Route relations: {lines_df['route_relation'].sum()}")
                print(f"     Direct ways: {(~lines_df['route_relation']).sum()}")
    
    if len(substations_df) > 0:
        substations_df['country'] = country_code
        substations_file = os.path.join(output_dir, f"{country_code.lower()}_substations.csv")
        substations_df.to_csv(substations_file, index=False)
        results['substations'] = substations_df
        print(f"  ✅ Substations saved to: {substations_file}")
    
    if len(plants_df) > 0:
        plants_df['country'] = country_code
        plants_file = os.path.join(output_dir, f"{country_code.lower()}_power_plants.csv")
        plants_df.to_csv(plants_file, index=False)
        results['plants'] = plants_df
        print(f"  ✅ Power plants saved to: {plants_file}")
    
    if len(converters_df) > 0:
        converters_df['country'] = country_code
        converters_file = os.path.join(output_dir, f"{country_code.lower()}_converters.csv")
        converters_df.to_csv(converters_file, index=False)
        results['converters'] = converters_df
        print(f"  ✅ Converters saved to: {converters_file}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Extract power transmission infrastructure from OSM data')
    parser.add_argument('--country', required=True, 
                       choices=['ITA', 'DEU', 'CHE', 'USA', 'AUS', 'CHN', 'IND', 'JPN', 'ZAF', 'NZL', 'BRA'],
                       help='Country code')
    parser.add_argument('--output-dir', default='cache/transmission',
                       help='Output directory for results')
    parser.add_argument('--min-voltage', type=float, default=0,
                       help='Minimum voltage in kV to include (default: 0 = all voltages)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')
    
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
    
    # Extract transmission infrastructure
    print(f"\nStarting power transmission extraction for {args.country}...")
    results = extract_transmission_infrastructure(
        args.country, 
        osm_file, 
        args.output_dir,
        min_voltage_kv=args.min_voltage,
        debug=args.debug
    )
    
    # Final summary
    if results:
        print(f"\n" + "="*60)
        print(f"🎉 POWER TRANSMISSION EXTRACTION COMPLETED FOR {args.country}")
        print(f"="*60)
        
        print(f"\n📊 FINAL SUMMARY:")
        for category, df in results.items():
            print(f"  ✅ {category.title()}: {len(df)} items")
        
        print(f"\n📁 All data saved to: {args.output_dir}")
        print(f"🔄 Ready for transmission network analysis!")
        print(f"="*60)
    else:
        print(f"\n❌ No power transmission infrastructure found for {args.country}")
        print("This could indicate:")
        print("  - OSM data lacks power infrastructure tags")
        print("  - Voltage filter too restrictive")
        print("  - Different tagging conventions used")
        print("\nTry running with --debug flag for more details")

if __name__ == "__main__":
    main()