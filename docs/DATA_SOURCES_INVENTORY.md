# VerveStacks Data Sources Inventory

## Complete List of Data Files by Source

### 1. EMBER Climate Data
- `data/ember/yearly_full_release_long_format.csv` (40.3 MB)
- `data/ember/monthly_full_release_long_format.csv` (51.8 MB) 
- `data/ember/ember_targets_download2025jul.xlsx` (0.1 MB)
- `data/timeslices/monthly_full_release_long_format.csv` (51.8 MB) [duplicate]

### 2. IRENA Renewable Energy Statistics
- `data/irena/IRENASTAT-C.xlsx` (0.8 MB) - Capacity statistics
- `data/irena/IRENASTAT-G.xlsx` (0.8 MB) - Generation statistics

### 3. Weather and Climate Data (ERA5/SARAH)
- `data/hourly_profiles/era5_combined_data_2030.csv` (342.5 MB)
- `data/hourly_profiles/sarah_era5_iso_grid_cell_2013.csv` (1389.6 MB)
- `data/hourly_profiles/sarah_era5_iso_2013.csv` (52.2 MB)
- `data/hourly_profiles/sarah_era5_iso_2015.csv`
- `data/hourly_profiles/sarah_era5_iso_valid_solar_wind_grid_cell.csv`

### 4. REZoning (Renewable Energy Zones)
- `data/REZoning/REZoning_Solar.csv` (7.7 MB)
- `data/REZoning/REZoning_WindOnshore.csv` (7.3 MB)
- `data/REZoning/REZoning_WindOffshore.csv`
- `data/REZoning/REZoning_costs_per_kw.csv` (0.0 MB)
- `data/REZoning/zones_centroids.csv`

### 5. OpenStreetMap Grid Infrastructure
- `data/OSM-Eur-prebuilt/buses.csv` (0.8 MB)
- `data/OSM-Eur-prebuilt/lines.csv` (10.6 MB)
- `data/OSM-Eur-prebuilt/links.csv`
- `data/OSM-Eur-prebuilt/converters.csv`
- `data/OSM-Eur-prebuilt/transformers.csv`
- `data/OSM-Eur-prebuilt/map.html`
- `data/OSM-Eur-prebuilt/rez_grid_to_bus.csv`
- `data/OSM-Eur-prebuilt/CH_power_plants_assigned_to_buses.csv`

### 6. Global Energy Monitor (GEM) Power Plant Data
- `data/existing_stock/Global-Integrated-Power-April-2025.xlsx`

### 7. World Energy Outlook (IEA/WEO)
- `data/demand/WEO2024_AnnexA_Free_Dataset_World.csv`
- `data/demand/WEO2024_AnnexA_Free_Dataset_Regions.csv`
- `data/IEAData.csv` (3.2 MB)

### 8. NGFS Climate Scenarios
- `data/NGFS4.2/Downscaled_MESSAGEix-GLOBIOM 1.1-M-R12_data.xlsx`
- `data/NGFS4.2/Downscaled_REMIND-MAgPIE 3.2-4.6_data.xlsx`
- `data/NGFS4.2/Downscaled_GCAM 6.0 NGFS_data.xlsx`

### 9. UN Statistics Division (UNSD)
- `data/unsd/unsd_july_2025.csv`

### 10. Technology and Economic Assumptions
- `data/technologies/re_potentials.xlsx`
- `data/technologies/ep_technoeconomic_assumptions.xlsx`
- `data/technologies/advanced_parameters.xlsx`
- `data/technologies/WEO_2024_PG_Assumptions_STEPSandNZE_Scenario.xlsb`
- `data/timeslices/re_potentials.xlsx` [duplicate]

### 11. Time Slice and Regional Mappings
- `data/timeslices/region_map.xlsx` (0.0 MB)

### 12. Environmental Protection Agency (EPA)
- `data/existing_stock/epa_coal+gas ccs retrofit data.xlsx`

### 13. Geographic and Administrative Data
#### Natural Earth Data
- `1_grids/_data/ne_10m_admin_0_countries/` (country boundaries shapefile)
  - `ne_10m_admin_0_countries.shp` (8.4 MB)
  - `ne_10m_admin_0_countries.dbf`
  - `ne_10m_admin_0_countries.shx`
  - `ne_10m_admin_0_countries.prj`
  - `ne_10m_admin_0_countries.cpg`
  - `ne_10m_admin_0_countries.VERSION.txt`
  - `ne_10m_admin_0_countries.README.html`

#### NUTS (Nomenclature of Territorial Units for Statistics)
- `1_grids/_data/nuts/NUTS_RG_01M_2021_4326_LEVL_0.geojson`
- `1_grids/_data/nuts/NUTS_RG_01M_2021_4326_LEVL_1.geojson`
- `1_grids/_data/nuts/NUTS_RG_01M_2021_4326_LEVL_2.geojson`
- `1_grids/_data/nuts/NUTS_RG_01M_2021_4326_LEVL_3.geojson` (26.6 MB)
- `1_grids/_data/nuts/NUTS_RG_03M_2013_4326_LEVL_2.geojson`
- `1_grids/_data/nuts/NUTS_RG_03M_2013_4326_LEVL_3.geojson`

#### JRC ARDECO Economic Data
- `1_grids/_data/jrc-ardeco/ARDECO-SUVGDP.2021.table.csv` (1.4 MB)
- `1_grids/_data/jrc-ardeco/ARDECO-SNPTD.2021.table.csv` (1.5 MB)

#### Other Geographic Data
- `1_grids/_data/worldcities.csv` (4.9 MB)
- `1_grids/_data/Industrial_Database.csv` (1.0 MB)

### 14. FACETS Model Validation Data
#### Model Outputs
- `3_model_validation/FACETS/data/model_outputs/VSInput_generation by tech, region, and timeslice.csv` (1129.6 MB)
- `3_model_validation/FACETS/data/model_outputs/VSInput_capacity by tech and region.csv` (127.3 MB)
- `3_model_validation/FACETS/data/model_outputs/FACETS_aggtimeslices.csv`
- `3_model_validation/FACETS/data/model_outputs/technology_categories.csv`
- `3_model_validation/FACETS/data/model_outputs/transmission_region_groups.csv`
- `3_model_validation/FACETS/data/model_outputs/transmission_links_not in use.csv`
- `3_model_validation/FACETS/data/model_outputs/MPSC Phase 2 second run matrix.xlsx`

#### Hourly Operational Data
- `3_model_validation/FACETS/data/hourly_data/EER_100by2050_load_hourly.h5` (716.7 MB)
- `3_model_validation/FACETS/data/hourly_data/wind-ons-reference_ba.h5` (290.0 MB)
- `3_model_validation/FACETS/data/hourly_data/upv-reference_ba.h5` (59.9 MB)

## Summary Statistics
- **Total Files**: 66 data files
- **Major Sources**: 14 distinct data providers/organizations
- **Largest Files**: 
  - SARAH/ERA5 weather data: ~1.4 GB
  - FACETS generation data: ~1.1 GB
  - FACETS load data: ~717 MB
  - ERA5 combined data: ~343 MB
- **Total Data Volume**: Approximately 4.5+ GB
