#!/usr/bin/env python3
"""
VerveStacks GeoJSON to CSV Converter
Converts GeoJSON files to CSV format for database import.
"""

import json
import csv
import os
import sys
from pathlib import Path

def geojson_to_csv(geojson_path, csv_path, is_onshore=True):
    """Convert GeoJSON to CSV format expected by the database."""
    
    print(f"Converting {geojson_path} to {csv_path}")
    
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to read {geojson_path}: {e}")
        return False
    
    # Define CSV headers based on database schema
    if is_onshore:
        headers = [
            'iso', 'country_name', 'grid_cell', 'centroid_lat', 'centroid_lon',
            'zone_score', 'capacity_factor', 'lcoe_usd_mwh', 'generation_potential_gwh',
            'installed_capacity_potential_mw', 'suitable_area_km2', 'area_km2',
            'perimeter_km', 'file_source', 'geometry_json'
        ]
    else:
        headers = [
            'iso', 'grid_cell', 'centroid_lat', 'centroid_lon', 'zone_score',
            'capacity_factor', 'lcoe_usd_mwh', 'generation_potential_gwh',
            'installed_capacity_potential_mw', 'suitable_area_km2', 'area_km2',
            'perimeter_km', 'file_source', 'geometry_json'
        ]
    
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            features = data.get('features', [])
            converted_count = 0
            
            for feature in features:
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                # Extract coordinates for centroid calculation
                coords = geom.get('coordinates', [])
                centroid_lat = None
                centroid_lon = None
                
                if coords and len(coords) > 0:
                    # For MultiPolygon, get first polygon's first ring
                    if geom.get('type') == 'MultiPolygon':
                        if coords and len(coords[0]) > 0 and len(coords[0][0]) > 0:
                            # Calculate centroid from first ring
                            ring_coords = coords[0][0]
                            lats = [coord[1] for coord in ring_coords]
                            lons = [coord[0] for coord in ring_coords]
                            centroid_lat = sum(lats) / len(lats)
                            centroid_lon = sum(lons) / len(lons)
                    elif geom.get('type') == 'Polygon':
                        if coords and len(coords[0]) > 0:
                            ring_coords = coords[0]
                            lats = [coord[1] for coord in ring_coords]
                            lons = [coord[0] for coord in ring_coords]
                            centroid_lat = sum(lats) / len(lats)
                            centroid_lon = sum(lons) / len(lons)
                
                # Build row data - handle both uppercase and lowercase ISO
                iso_value = props.get('ISO', props.get('iso', ''))
                
                if is_onshore:
                    row = [
                        iso_value,
                        props.get('country_name', ''),
                        props.get('grid_cell', ''),
                        centroid_lat,
                        centroid_lon,
                        props.get('zone_score'),
                        props.get('capacity_factor'),
                        props.get('lcoe_usd_mwh'),
                        props.get('generation_potential_gwh'),
                        props.get('installed_capacity_potential_mw'),
                        props.get('suitable_area_km2'),
                        props.get('area_km2'),
                        props.get('perimeter_km'),
                        os.path.basename(geojson_path),
                        json.dumps(geom)  # Store full geometry as JSON
                    ]
                else:
                    row = [
                        iso_value,
                        props.get('grid_cell', ''),
                        centroid_lat,
                        centroid_lon,
                        props.get('zone_score'),
                        props.get('capacity_factor'),
                        props.get('lcoe_usd_mwh'),
                        props.get('generation_potential_gwh'),
                        props.get('installed_capacity_potential_mw'),
                        props.get('suitable_area_km2'),
                        props.get('area_km2'),
                        props.get('perimeter_km'),
                        os.path.basename(geojson_path),
                        json.dumps(geom)  # Store full geometry as JSON
                    ]
                
                writer.writerow(row)
                converted_count += 1
            
            print(f"Successfully converted {converted_count} features to {csv_path}")
            return True
            
    except Exception as e:
        print(f"ERROR: Failed to write {csv_path}: {e}")
        return False

def main():
    """Convert both GeoJSON files to CSV."""
    print("VerveStacks GeoJSON to CSV Converter")
    print("====================================")
    
    data_dir = Path('data')
    
    # Check if data directory exists
    if not data_dir.exists():
        print(f"ERROR: Data directory '{data_dir}' not found")
        print("Please run this script from the database directory")
        return False
    
    success = True
    
    # Convert onshore zones
    onshore_geojson = data_dir / 'consolidated_onshore_zones.geojson'
    onshore_csv = data_dir / 'onshore_zones.csv'
    
    if onshore_geojson.exists():
        if not geojson_to_csv(onshore_geojson, onshore_csv, is_onshore=True):
            success = False
    else:
        print(f"WARNING: {onshore_geojson} not found - skipping onshore zones")
    
    # Convert offshore zones
    offshore_geojson = data_dir / 'consolidated_offshore_zones.geojson'
    offshore_csv = data_dir / 'offshore_zones.csv'
    
    if offshore_geojson.exists():
        if not geojson_to_csv(offshore_geojson, offshore_csv, is_onshore=False):
            success = False
    else:
        print(f"WARNING: {offshore_geojson} not found - skipping offshore zones")
    
    if success:
        print("\nConversion completed successfully!")
        print("You can now run setup_database.bat to import all data")
    else:
        print("\nConversion completed with errors")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
