# Data Sources and Citations

## Formal Citation List for VerveStacks Project

### Core VerveStacks Model

**EMBER Climate Data**
- EMBER (2025). *Global Electricity Review 2025 - Yearly Full Release*. Retrieved from https://ember-climate.org/data/
- EMBER (2025). *Global Electricity Review 2025 - Monthly Full Release*. Retrieved from https://ember-climate.org/data/
- EMBER (2025). *Electricity Targets Database*. July 2025 release.

*Usage in VerveStacks*: EMBER data provides historical electricity generation by technology and country, used for calibrating existing capacity, validating renewable energy profiles, and creating hourly demand patterns for timeslice analysis and stress period identification.

**International Renewable Energy Agency (IRENA)**
- IRENA (2025). *Renewable Energy Statistics 2025 - Capacity Statistics (IRENASTAT-C)*. International Renewable Energy Agency, Abu Dhabi.
- IRENA (2025). *Renewable Energy Statistics 2025 - Generation Statistics (IRENASTAT-G)*. International Renewable Energy Agency, Abu Dhabi.

*Usage in VerveStacks*: IRENA statistics serve as the primary source for renewable energy capacity and generation data by country and technology, used for cross-validation with EMBER data and establishing baseline renewable energy potentials in VEDA models.

**International Energy Agency (IEA)**
- IEA (2024). *World Energy Outlook 2024 - Annex A Free Dataset (World)*. International Energy Agency, Paris.
- IEA (2024). *World Energy Outlook 2024 - Annex A Free Dataset (Regions)*. International Energy Agency, Paris.
- IEA (2024). *World Energy Outlook 2024 - Power Generation Assumptions (STEPS and NZE Scenarios)*.

*Usage in VerveStacks*: IEA WEO data provides energy demand projections, technology cost assumptions, and policy scenario parameters that inform future energy system modeling and techno-economic assumptions for power generation technologies in VEDA models.

**Global Energy Monitor (GEM)**
- Global Energy Monitor (2025). *Global Integrated Power Database*. April 2025 release. Retrieved from https://globalenergymonitor.org/

*Usage in VerveStacks*: GEM provides detailed plant-level data for existing power generation facilities worldwide, including capacity, technology type, location, and operational status, used for creating accurate existing stock representations and spatial grid modeling assignments.

**Network for Greening the Financial System (NGFS)**
- NGFS (2024). *NGFS Climate Scenarios Database v4.2*:
  - MESSAGEix-GLOBIOM 1.1-M-R12 downscaled data
  - REMIND-MAgPIE 3.2-4.6 downscaled data  
  - GCAM 6.0 NGFS downscaled data
- Retrieved from https://www.ngfs.net/ngfs-scenarios-portal/

*Usage in VerveStacks*: NGFS climate scenarios provide country-level projections for energy system transformation pathways, used to create scenario-based parameter files and inform long-term energy transition modeling in VEDA with multiple climate policy trajectories.

**United Nations Statistics Division (UNSD)**
- UNSD (2025). *Energy Statistics Database*. July 2025 release. United Nations Statistics Division, New York.

*Usage in VerveStacks*: UNSD energy statistics provide standardized energy balance data by country and fuel type, used for demand calibration, energy flow mapping, and creating consistent regional and product classifications across different data sources.

**Environmental Protection Agency (EPA)**
- U.S. Environmental Protection Agency (2025). *Coal and Gas Carbon Capture and Storage Retrofit Database*. Washington, DC.

*Usage in VerveStacks*: EPA CCS retrofit data provides technical and economic parameters for carbon capture and storage retrofits on existing coal and gas power plants, used to model decarbonization pathways and CCS technology deployment options in fossil fuel transition scenarios.

### The "WHERE" of Electricity

*This section covers data sources used in the `1_grids/` folder for spatial analysis and grid modeling.*

**OpenStreetMap**
- OpenStreetMap contributors (2025). *OpenStreetMap European Power Grid Data*. © OpenStreetMap contributors. Available under the Open Database License. https://www.openstreetmap.org/

*Usage in VerveStacks*: OpenStreetMap power infrastructure data provides detailed transmission line networks, substations, and grid topology for European countries, used in PyPSA-based grid modeling to create spatially-explicit transmission constraints and bus clustering for grid-aware energy system models.

**REZoning Database**
- REZoning Consortium. *Renewable Energy Zones Database*:
  - Solar potential zones with cost data
  - Onshore wind potential zones  
  - Offshore wind potential zones
  - Technology cost assumptions per kW

*Usage in VerveStacks*: REZoning data provides spatially-explicit renewable energy resource potential at high resolution (50x50km grid cells), used to create renewable energy supply curves, assign location-specific costs and capacity factors, and enable grid-aware renewable energy expansion modeling.

**Copernicus Climate Change Service (C3S) - Spatial Weather**
- Hersbach, H., Bell, B., Berrisford, P., et al. (2020). *The ERA5 global reanalysis*. Quarterly Journal of the Royal Meteorological Society, 146(730), 1999-2049. https://doi.org/10.1002/qj.3803
- Copernicus Climate Change Service (C3S) (2017). *ERA5: Fifth generation of ECMWF atmospheric reanalyses of the global climate*. Copernicus Climate Change Service Climate Data Store (CDS). https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels

*Usage in VerveStacks*: ERA5 reanalysis data provides spatially-explicit meteorological variables (wind speed, temperature, solar irradiance) used for renewable energy resource assessment at grid-cell level, creating location-specific generation profiles, and supporting spatial optimization in grid modeling.

**SARAH Solar Radiation Data**
- Pfeifroth, U., Kothe, S., Müller, R., et al. (2019). *SARAH-2.1: Solar surface radiation climate data record for Europe based on SEVIRI/Meteosat observations*. Satellite Application Facility on Climate Monitoring. https://doi.org/10.5676/EUM_SAF_CM/SARAH/V002_01

*Usage in VerveStacks*: SARAH satellite-derived solar radiation data provides high-resolution solar irradiance measurements for Europe, used to create accurate photovoltaic generation profiles and validate solar resource potential in grid-cell level renewable energy zone modeling.

**Natural Earth**
- Natural Earth (2021). *Admin 0 – Countries (1:10m)*. Version 5.1.1. Retrieved from https://www.naturalearthdata.com/

*Usage in VerveStacks*: Natural Earth country boundary data provides standardized geographic boundaries for spatial analysis, country identification in grid modeling, and ensuring consistent geographic referencing across all spatial datasets in the platform.

**European Commission - Eurostat**
- Eurostat (2021). *NUTS - Nomenclature of Territorial Units for Statistics*. Statistical regions of Europe at NUTS levels 0-3. European Commission. https://ec.europa.eu/eurostat/web/nuts

*Usage in VerveStacks*: NUTS regional classifications provide standardized European administrative boundaries at multiple scales, used for regional aggregation in grid modeling, spatial clustering of renewable energy zones, and ensuring consistency with European energy statistics and policy frameworks.

**European Commission - Joint Research Centre (JRC)**
- European Commission, Joint Research Centre (2021). *ARDECO - Annual Regional Database of the European Commission's Directorate General for Regional and Urban policy*:
  - ARDECO-SUVGDP: GDP per capita data
  - ARDECO-SNPTD: Population data

*Usage in VerveStacks*: JRC ARDECO socio-economic data provides regional GDP and population statistics used for demand allocation, economic weighting in grid clustering algorithms, and calibrating energy demand patterns to regional economic activity levels.

**SimpleMaps**
- SimpleMaps (2025). *World Cities Database*. Retrieved from https://simplemaps.com/data/world-cities

*Usage in VerveStacks*: World cities database provides urban center locations and population data used for demand node placement in grid modeling, spatial reference for power plant assignments, and urban load center identification in transmission network clustering.

**Industrial Database**
- Various sources. *Global Industrial Facilities Database*. Compiled for grid modeling applications.

*Usage in VerveStacks*: Industrial facilities database provides locations and energy consumption data for major industrial loads, used to create realistic demand patterns, identify industrial demand nodes in grid modeling, and calibrate regional electricity consumption profiles.

### The "WHEN" of Electricity

*This section covers data sources used in the `2_ts_design/` folder for temporal analysis and timeslice design.*

**EMBER Climate Data (Temporal Analysis)**
- EMBER (2025). *Global Electricity Review 2025 - Monthly Full Release*. Retrieved from https://ember-climate.org/data/

*Usage in VerveStacks*: EMBER monthly data provides seasonal and temporal patterns in electricity generation, used in the stress period analyzer for identifying critical time periods, creating timeslice definitions, and designing temporal aggregation strategies for energy system modeling.

**Copernicus Climate Change Service (C3S) - Temporal Patterns**
- Hersbach, H., Bell, B., Berrisford, P., et al. (2020). *The ERA5 global reanalysis*. Quarterly Journal of the Royal Meteorological Society, 146(730), 1999-2049. https://doi.org/10.1002/qj.3803

*Usage in VerveStacks*: ERA5 hourly weather data enables stress period identification, renewable energy variability analysis, and creation of representative time slices that capture critical scarcity and surplus periods for energy system adequacy planning.

**IRENA Generation Data (Temporal Validation)**
- IRENA (2025). *Renewable Energy Statistics 2025 - Generation Statistics (IRENASTAT-G)*. International Renewable Energy Agency, Abu Dhabi.

*Usage in VerveStacks*: IRENA generation statistics provide temporal validation for renewable energy output patterns, used to calibrate seasonal generation profiles and validate timeslice aggregation accuracy in the stress period analyzer.

### Hourly Simulation (Byproduct)

*This section covers data sources used in the `3_model_validation/FACETS/` folder for hourly operational simulation and model validation.*

**EER Load Profiles**
- Eastern Electricity Reliability Council. *100% by 2050 Hourly Load Profiles*. Hourly demand data for grid simulation.

*Usage in VerveStacks*: EER hourly load profiles provide detailed electricity demand patterns for model validation, used in the FACETS hourly operational simulator to test energy system adequacy, validate capacity planning results, and assess system reliability under high renewable energy scenarios.

**Renewable Energy Profiles**
- Various sources. *Reference Renewable Energy Profiles*:
  - Utility-scale photovoltaic (UPV) hourly profiles
  - Onshore wind hourly profiles
  - Technology categorization and mapping data

*Usage in VerveStacks*: Reference renewable energy profiles provide standardized hourly generation patterns for different renewable technologies, used in FACETS validation to simulate realistic renewable energy output, test grid integration challenges, and validate renewable energy capacity expansion scenarios.

## Citation Format for Academic Use

When citing the VerveStacks platform and its integrated datasets:

> VerveStacks Team (2025). *VerveStacks: Open Energy System Modeling Platform*. Integrated analysis of global energy data from EMBER, IRENA, IEA WEO, GEM, NGFS, UNSD, ERA5/SARAH weather data, and OpenStreetMap grid infrastructure. Available at: [repository URL]

## Data Usage and Licensing

- **Open Data**: Most sources (EMBER, IRENA, IEA WEO, ERA5, OpenStreetMap, Natural Earth) provide data under open licenses
- **Attribution Required**: OpenStreetMap data requires attribution to © OpenStreetMap contributors
- **Academic Use**: All sources support academic and research applications
- **Commercial Use**: Check individual source licenses for commercial applications

## Data Quality and Validation

All datasets undergo automated quality checks and reconciliation within the VerveStacks processing pipeline:
- Cross-validation between sources (e.g., IRENA vs EMBER capacity data)
- Spatial consistency checks for grid and renewable energy zone data  
- Temporal alignment of weather and demand profiles
- Technology mapping standardization across all sources

---
*Last updated: January 2025*
*For questions about data sources or citations, contact the VerveStacks team*
