# Geolocation to Administrative Regions Mapper

A clean, direct geolocation lookup script that maps coordinates to administrative regions using Natural Earth and NUTS data.

## Input
- Latitude, Longitude coordinates (single or batch)

## Output
- ISO3 country code
- admin_0: Country name (global coverage)
- admin_1: First-level administrative division - states/provinces (global coverage via Natural Earth, enhanced for EU via NUTS)
- admin_2: Second-level administrative division (EU only via NUTS)
- admin_3: Third-level administrative division (EU only via NUTS)

## Data Sources
- Natural Earth country boundaries (`naturalearth/ne_10m_admin_0_countries_lakes.shp`) - global coverage
- Natural Earth admin_1 states/provinces (`naturalearth/ne_10m_admin_1_states_provinces*.shp`) - global coverage
- NUTS administrative regions (`nuts/NUTS_RG_01M_2021_4326_LEVL_*.geojson`) - EU only

## Coverage
- **Global**: ISO codes, country names, basic admin_1 (if Natural Earth admin_1 data available)
- **EU Enhanced**: Additional admin_2 and admin_3 levels via NUTS data

## Usage

### Single Coordinate Lookup
```bash
python geolocation_to_admin_regions.py --lat 52.5200 --lng 13.4050
```

### Batch Processing from CSV
```bash
python geolocation_to_admin_regions.py --csv coordinates.csv --output results.csv
```

### Custom Column Names
```bash
python geolocation_to_admin_regions.py --csv data.csv --lat-col "lat" --lng-col "lon" --output output.csv
```

## Example Output
```json
{
  "latitude": 52.52,
  "longitude": 13.405,
  "iso_code": "DEU",
  "admin_0": "Germany",
  "admin_1": "Berlin",
  "admin_2": "Berlin",
  "admin_3": "Berlin, Kreisfreie Stadt"
}
```

## Requirements
- geopandas
- pandas
- shapely

No fallback mechanisms - direct spatial lookup only.
