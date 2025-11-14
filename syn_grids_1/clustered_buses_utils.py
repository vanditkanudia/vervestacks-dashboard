#!/usr/bin/env python3
"""
Clustered Buses Utility Functions
=================================

Utility functions for preparing clustered buses data that can be used
by both advanced renewable clustering and final export processes.

Author: VerveStacks Team
"""

import pandas as pd
import os
from typing import Dict, List, Optional, Any


def get_iso2_from_iso3(iso3_code):
    """Convert ISO3 code to ISO2 code using the same logic as the reference function"""
    try:
        # Try pycountry first if available
        import pycountry
        country = pycountry.countries.get(alpha_3=iso3_code)
        if country:
            return country.alpha_2
    except ImportError:
        pass
    except Exception:
        pass
    
    # Fallback dictionary for common cases
    iso3_to_iso2 = {
        'CHE': 'CH', 'DEU': 'DE', 'FRA': 'FR', 'GBR': 'GB', 'ITA': 'IT',
        'ESP': 'ES', 'POL': 'PL', 'NLD': 'NL', 'BEL': 'BE', 'AUT': 'AT',
        'CZE': 'CZ', 'DNK': 'DK', 'NOR': 'NO', 'SWE': 'SE', 'FIN': 'FI',
        'XKX': 'XK', 'USA': 'US', 'CAN': 'CA', 'BRA': 'BR', 'ARG': 'AR',
        'MEX': 'MX', 'IND': 'IN', 'CHN': 'CN', 'JPN': 'JP', 'KOR': 'KR',
        'RUS': 'RU', 'AUS': 'AU', 'NZL': 'NZ', 'ZAF': 'ZA', 'EGY': 'EG',
        'TUR': 'TR', 'SAU': 'SA', 'IRN': 'IR', 'IRQ': 'IQ', 'ISR': 'IL',
        'JOR': 'JO', 'LBN': 'LB', 'SYR': 'SY', 'YEM': 'YE', 'OMN': 'OM',
        'ARE': 'AE', 'QAT': 'QA', 'KWT': 'KW', 'BHR': 'BH', 'AFG': 'AF',
        'PAK': 'PK', 'BGD': 'BD', 'LKA': 'LK', 'NPL': 'NP', 'BTN': 'BT',
        'MMR': 'MM', 'THA': 'TH', 'LAO': 'LA', 'VNM': 'VN', 'KHM': 'KH',
        'MYS': 'MY', 'SGP': 'SG', 'IDN': 'ID', 'BRN': 'BN', 'PHL': 'PH',
        'TWN': 'TW', 'MNG': 'MN', 'PRK': 'KP', 'KAZ': 'KZ', 'UZB': 'UZ',
        'TKM': 'TM', 'KGZ': 'KG', 'TJK': 'TJ', 'GEO': 'GE', 'ARM': 'AM',
        'AZE': 'AZ', 'UKR': 'UA', 'BLR': 'BY', 'MDA': 'MD', 'LTU': 'LT',
        'LVA': 'LV', 'EST': 'EE', 'HRV': 'HR', 'SVN': 'SI', 'SVK': 'SK',
        'HUN': 'HU', 'ROU': 'RO', 'BGR': 'BG', 'SRB': 'RS', 'MNE': 'ME',
        'BIH': 'BA', 'MKD': 'MK', 'ALB': 'AL', 'GRC': 'GR', 'CYP': 'CY',
        'MLT': 'MT', 'PRT': 'PT', 'IRL': 'IE', 'ISL': 'IS', 'LUX': 'LU',
        'MCO': 'MC', 'SMR': 'SM', 'VAT': 'VA', 'AND': 'AD', 'LIE': 'LI'
    }
    
    return iso3_to_iso2.get(iso3_code, iso3_code[:2])


def get_osm_data_source(country_code):
    """
    Determine which OSM dataset to use for the given country.
    Priority: Eur-prebuilt -> kan-prebuilt (Kanors in-house dataset)
    
    Args:
        country_code: ISO3 country code (e.g., 'CAN', 'DEU')
        
    Returns:
        str: Dataset name ('eur' or 'kan') or None if country not found
    """
    # Convert ISO3 to ISO2 for matching with OSM data
    iso2_country = get_iso2_from_iso3(country_code)
    
    # Priority order: Eur first, then Kanors in-house dataset
    data_sources = {
        'eur': 'data/OSM-Eur-prebuilt',
        'kan': 'data/OSM-kan-prebuilt'  # Kanors in-house dataset
    }
    
    for source_name, source_path in data_sources.items():
        buses_file = f'{source_path}/buses.csv'
        try:
            if os.path.exists(buses_file):
                buses_df = pd.read_csv(buses_file)
                if 'country' in buses_df.columns:
                    country_buses = buses_df[buses_df['country'] == iso2_country]
                    if not country_buses.empty:
                        print(f"✓ Using {source_name} dataset for {country_code} (ISO2: {iso2_country}) ({len(country_buses)} buses)")
                        return source_name
        except Exception as e:
            print(f"✗ Error checking {source_name} dataset: {e}")
    
    print(f"✗ Country '{country_code}' (ISO2: {iso2_country}) not found in any OSM dataset")
    return None


def prepare_clustered_buses_data(demand_results: Optional[Dict] = None,
                                generation_results: Optional[Dict] = None,
                                renewable_results: Optional[Dict] = None) -> pd.DataFrame:
    """
    Prepare clustered buses data from clustering results
    
    Args:
        demand_results: Demand clustering results with 'centers' key
        generation_results: Generation clustering results with 'centers' key  
        renewable_results: Renewable clustering results with 'centers' key
        
    Returns:
        DataFrame with columns: bus_id, station_id, x, y, tags, voltage
    """
    clustered_buses = []
    
    # Add demand clusters
    if demand_results and demand_results.get('centers') is not None:
        centers_df = pd.DataFrame(demand_results['centers'])
        for _, center in centers_df.iterrows():
            cluster_id = int(center.get('cluster_id', center.name))
            clustered_buses.append({
                'bus_id': f"dem{cluster_id}",
                'station_id': f"dem{cluster_id}",  # Identical to bus_id for compatibility
                'x': center['center_lng'],  # x = longitude
                'y': center['center_lat'],  # y = latitude
                'tags': f"demand{cluster_id}",
                'voltage': 300  # Dummy voltage value
            })
    
    # Add generation clusters
    if generation_results and generation_results.get('centers') is not None:
        centers_df = pd.DataFrame(generation_results['centers'])
        for _, center in centers_df.iterrows():
            cluster_id = int(center.get('cluster_id', center.name))
            clustered_buses.append({
                'bus_id': f"gen{cluster_id}",
                'station_id': f"gen{cluster_id}",  # Identical to bus_id for compatibility
                'x': center['center_lng'],  # x = longitude
                'y': center['center_lat'],  # y = latitude
                'tags': f"generation{cluster_id}",
                'voltage': 300  # Dummy voltage value
            })
    
    # Add renewable clusters (if provided)
    if renewable_results and renewable_results.get('centers') is not None:
        renewable_centers = renewable_results['centers']
        
        # Handle both DataFrame and list formats
        if isinstance(renewable_centers, list):
            # If it's a list, iterate directly
            for center in renewable_centers:
                cluster_id = int(center.get('cluster_id', 0))
                technology = center.get('technology', 'renewable')
                
                # Create bus_id based on technology
                if technology == 'solar':
                    bus_id = f"sol{cluster_id}"
                    tags = f"solar{cluster_id}"
                elif technology == 'wind_onshore':
                    bus_id = f"won{cluster_id}"
                    tags = f"wind_onshore{cluster_id}"
                elif technology == 'wind_offshore':
                    bus_id = f"wof{cluster_id}"
                    tags = f"wind_offshore{cluster_id}"
                else:
                    bus_id = f"ren{cluster_id}"
                    tags = f"renewable{cluster_id}"
                
                clustered_buses.append({
                    'bus_id': bus_id,
                    'station_id': bus_id,  # Identical to bus_id for compatibility
                    'x': center['center_lng'],  # x = longitude
                    'y': center['center_lat'],  # y = latitude
                    'tags': tags,
                    'voltage': 300  # Dummy voltage value
                })
        else:
            # If it's a DataFrame, use iterrows
            for _, center in renewable_centers.iterrows():
                cluster_id = int(center.get('cluster_id', center.name))
                technology = center.get('technology', 'renewable')
                
                # Create bus_id based on technology
                if technology == 'solar':
                    bus_id = f"sol{cluster_id}"
                    tags = f"solar{cluster_id}"
                elif technology == 'wind_onshore':
                    bus_id = f"won{cluster_id}"
                    tags = f"wind_onshore{cluster_id}"
                elif technology == 'wind_offshore':
                    bus_id = f"wof{cluster_id}"
                    tags = f"wind_offshore{cluster_id}"
                else:
                    bus_id = f"ren{cluster_id}"
                    tags = f"renewable{cluster_id}"
                
                clustered_buses.append({
                    'bus_id': bus_id,
                    'station_id': bus_id,  # Identical to bus_id for compatibility
                    'x': center['center_lng'],  # x = longitude
                    'y': center['center_lat'],  # y = latitude
                    'tags': tags,
                    'voltage': 300  # Dummy voltage value
                })
    
    # Create DataFrame
    if clustered_buses:
        return pd.DataFrame(clustered_buses)
    else:
        return pd.DataFrame(columns=['bus_id', 'station_id', 'x', 'y', 'tags', 'voltage'])


def save_clustered_buses_csv(clustered_buses_df: pd.DataFrame, 
                           output_path, 
                           country: str) -> bool:
    """
    Save clustered buses data to CSV file
    
    Args:
        clustered_buses_df: DataFrame with clustered buses data
        output_path: Path object for output directory
        country: Country code for filename
        
    Returns:
        bool: True if saved successfully
    """
    try:
        if not clustered_buses_df.empty:
            buses_file = output_path / f'{country}_clustered_buses.csv'
            clustered_buses_df.to_csv(buses_file, index=False)
            print(f"💾 Saved clustered buses data: {buses_file}")
            print(f"   📊 Total buses: {len(clustered_buses_df)}")
            return True
        else:
            print("⚠️ No clustered buses data to save")
            return False
            
    except Exception as e:
        print(f"❌ Error saving clustered buses data: {e}")
        return False
