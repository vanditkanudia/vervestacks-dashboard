"""
Geolocation to Administrative Regions Mapper

Input: Latitude, Longitude coordinates
Output: ISO code, admin_0 (country), admin_1 (states/provinces) regions

Uses Natural Earth data from the project's data/country_data/ folder.
For European countries, also uses NUTS data for additional admin levels.
No fallbacks - direct spatial lookup only.
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
import argparse
import json
from typing import Dict, List, Tuple, Optional


class GeolocationMapper:
    """Maps geographic coordinates to administrative regions."""
    
    def __init__(self, data_dir: str = "../data/country_data"):
        self.data_dir = Path(data_dir)
        self.country_gdf = None
        self.admin1_gdf = None
        self.nuts_gdfs = {}
        
    def load_data(self):
        """Load all required geospatial datasets."""
        print("Loading geospatial datasets...")
        
        # Load Natural Earth country boundaries (global)
        ne_shapefile = self.data_dir / "naturalearth" / "ne_10m_admin_0_countries_lakes.shp"
        if ne_shapefile.exists():
            self.country_gdf = gpd.read_file(ne_shapefile)
            print(f"Loaded {len(self.country_gdf)} country boundaries")
        else:
            raise FileNotFoundError(f"Natural Earth shapefile not found: {ne_shapefile}")
        
        # Load Natural Earth admin_1 (states/provinces) - global coverage
        # Try different admin_1 variants in order of preference
        ne_admin1_files = [
            self.data_dir / "naturalearth" / "ne_10m_admin_1_states_provinces.shp",  # Standard version
            self.data_dir / "naturalearth" / "ne_10m_admin_1_states_provinces_lakes.shp",  # With lakes
            self.data_dir / "naturalearth" / "ne_10m_admin_1_states_provinces_scale_rank.shp",  # Scale ranked
            self.data_dir / "naturalearth" / "ne_10m_admin_1_states_provinces_lines.shp"  # Lines version
        ]
        
        for admin1_file in ne_admin1_files:
            if admin1_file.exists():
                self.admin1_gdf = gpd.read_file(admin1_file)
                print(f"Loaded {len(self.admin1_gdf)} admin_1 regions (global) from {admin1_file.name}")
                break
        
        # Load NUTS administrative levels (EU only) for additional detail
        nuts_files = {
            'nuts_1': 'NUTS_RG_01M_2021_4326_LEVL_1.geojson',
            'nuts_2': 'NUTS_RG_01M_2021_4326_LEVL_2.geojson', 
            'nuts_3': 'NUTS_RG_01M_2021_4326_LEVL_3.geojson'
        }
        
        nuts_dir = self.data_dir / "nuts"
        for level, filename in nuts_files.items():
            nuts_file = nuts_dir / filename
            if nuts_file.exists():
                self.nuts_gdfs[level] = gpd.read_file(nuts_file)
                print(f"Loaded {len(self.nuts_gdfs[level])} {level} regions (EU)")
    
    def lookup_coordinates(self, lat: float, lng: float) -> Dict[str, Optional[str]]:
        """
        Look up administrative regions for given coordinates.
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            Dictionary with ISO code and administrative levels
        """
        point = Point(lng, lat)  # Note: Point takes (x, y) = (lng, lat)
        
        result = {
            'latitude': lat,
            'longitude': lng,
            'iso_code': None,
            'admin_0': None,
            'admin_1': None,
            'admin_2': None,
            'admin_3': None
        }
        
        # Find country (admin_0) - global coverage
        country_match = self.country_gdf[self.country_gdf.contains(point)]
        if not country_match.empty:
            country_row = country_match.iloc[0]
            result['iso_code'] = country_row.get('ADM0_A3', None)
            result['admin_0'] = country_row.get('NAME', None)
        
        # Find admin_1 (states/provinces) - global coverage if available
        if self.admin1_gdf is not None:
            admin1_match = self.admin1_gdf[self.admin1_gdf.contains(point)]
            if not admin1_match.empty:
                admin1_row = admin1_match.iloc[0]
                result['admin_1'] = admin1_row.get('NAME', admin1_row.get('name', None))
        
        # Find NUTS administrative levels (EU only) - additional detail for European countries
        nuts_mapping = {'nuts_1': 'admin_1', 'nuts_2': 'admin_2', 'nuts_3': 'admin_3'}
        for nuts_level, admin_level in nuts_mapping.items():
            if nuts_level in self.nuts_gdfs:
                nuts_match = self.nuts_gdfs[nuts_level][self.nuts_gdfs[nuts_level].contains(point)]
                if not nuts_match.empty:
                    nuts_row = nuts_match.iloc[0]
                    nuts_name = nuts_row.get('NAME_LATN', nuts_row.get('NUTS_NAME', None))
                    # For EU countries, NUTS provides more detailed admin levels
                    # If we already have admin_1 from Natural Earth, NUTS_1 can override it for EU
                    if nuts_name:
                        result[admin_level] = nuts_name
        
        return result
    
    def lookup_batch(self, coordinates: List[Tuple[float, float]]) -> List[Dict[str, Optional[str]]]:
        """
        Look up administrative regions for multiple coordinates.
        
        Args:
            coordinates: List of (lat, lng) tuples
            
        Returns:
            List of result dictionaries
        """
        results = []
        total = len(coordinates)
        
        for i, (lat, lng) in enumerate(coordinates):
            if i % 100 == 0:
                print(f"Processing {i+1}/{total} coordinates...")
            
            result = self.lookup_coordinates(lat, lng)
            results.append(result)
        
        return results
    
    def process_csv(self, input_file: str, lat_col: str = 'latitude', lng_col: str = 'longitude') -> pd.DataFrame:
        """
        Process CSV file with coordinates.
        
        Args:
            input_file: Path to input CSV file
            lat_col: Name of latitude column
            lng_col: Name of longitude column
            
        Returns:
            DataFrame with original data plus administrative regions
        """
        df = pd.read_csv(input_file)
        
        if lat_col not in df.columns or lng_col not in df.columns:
            raise ValueError(f"Required columns {lat_col}, {lng_col} not found in CSV")
        
        coordinates = list(zip(df[lat_col], df[lng_col]))
        results = self.lookup_batch(coordinates)
        
        # Convert results to DataFrame and merge with original
        results_df = pd.DataFrame(results)
        
        # Remove duplicate lat/lng columns from results
        results_df = results_df.drop(['latitude', 'longitude'], axis=1)
        
        # Merge with original data
        output_df = pd.concat([df, results_df], axis=1)
        
        return output_df


def main():
    parser = argparse.ArgumentParser(description='Map coordinates to administrative regions')
    parser.add_argument('--lat', type=float, help='Latitude for single coordinate lookup')
    parser.add_argument('--lng', type=float, help='Longitude for single coordinate lookup')
    parser.add_argument('--csv', type=str, help='CSV file with coordinates to process')
    parser.add_argument('--lat-col', type=str, default='latitude', help='Latitude column name in CSV')
    parser.add_argument('--lng-col', type=str, default='longitude', help='Longitude column name in CSV')
    parser.add_argument('--output', type=str, help='Output file path (CSV or JSON)')
    parser.add_argument('--data-dir', type=str, default='../data/country_data', help='Data directory path')
    
    args = parser.parse_args()
    
    # Initialize mapper and load data
    mapper = GeolocationMapper(args.data_dir)
    mapper.load_data()
    
    if args.lat is not None and args.lng is not None:
        # Single coordinate lookup
        result = mapper.lookup_coordinates(args.lat, args.lng)
        
        if args.output:
            if args.output.endswith('.json'):
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
            else:
                pd.DataFrame([result]).to_csv(args.output, index=False)
        else:
            print(json.dumps(result, indent=2))
    
    elif args.csv:
        # Batch processing from CSV
        print(f"Processing CSV file: {args.csv}")
        result_df = mapper.process_csv(args.csv, args.lat_col, args.lng_col)
        
        if args.output:
            result_df.to_csv(args.output, index=False)
            print(f"Results saved to: {args.output}")
        else:
            print(result_df.to_string())
    
    else:
        print("Please provide either --lat/--lng for single lookup or --csv for batch processing")
        parser.print_help()


if __name__ == "__main__":
    main()
