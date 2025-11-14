# VerveStacks Methodology Documentation

## Overview
This document explains the data sources, assumptions, and processing methodology used to generate the country-specific energy system models in your VerveStacks package. Each model contains calibrated technology parameters, existing power plant inventories, and future scenario projections derived from multiple authoritative global datasets.

---

## Data Sources

### Primary Global Datasets
- **IRENA**: Renewable energy capacity and generation statistics (2000-2022)
- **EMBER**: Global electricity generation and capacity data (2000-2022)  
- **Global Energy Monitor (GEM)**: Individual power plant database with technical specifications
- **NGFS**: Climate scenario projections and carbon pricing trajectories
- **UNSD**: UN energy statistics and demand projections
- **World Energy Outlook (WEO)**: Technology cost and performance assumptions
- **EPA**: Carbon capture and storage retrofit potential

### Geographic Coverage
All models cover **100+ countries** using consistent methodology and harmonized technology classifications.

---

## Technology Parameter Derivation

### 1. Capital Costs (CAPEX)
**Methodology**: Multi-factor cost estimation combining global benchmarks with local adjustments

**Base Formula**:
```
CAPEX = Base_Technology_Cost × Size_Factor × Regional_Multiplier × Vintage_Adjustment
```

**Data Sources and Files**:
- **Base Technology Cost**: `assumptions/weo_technology_assumptions.xlsx`, Sheet: `Investment_Costs_by_Region`
- **Size Factor**: `assumptions/costs_size_multipliers.xlsx`, Sheet: `Size_Multipliers`
- **Regional Multiplier**: `assumptions/regional_multipliers.xlsx`, Sheet: `Labor_Cost_Adjustments`
- **Vintage Adjustment**: `assumptions/thermal_efficiency.xlsx`, Sheet: `Efficiency_by_Vintage`

**Calculation Steps**:
1. **Base Cost Lookup**: Technology and region matched in `weo_technology_assumptions.xlsx`
2. **Size Adjustment**: Plant size from GEM matched to multiplier in `costs_size_multipliers.xlsx`
3. **Regional Scaling**: ISO code matched to labor multiplier in `regional_multipliers.xlsx`
4. **Vintage Factor**: Commissioning year matched to efficiency curve in `thermal_efficiency.xlsx`

**Example for Solar PV in Japan (JPN)**:
- Base cost: $1,200/kW (`weo_technology_assumptions.xlsx`, Sheet: `Investment_Costs_by_Region`, Technology: `Solar_PV`, Region: `Asia_Pacific`)
- Size factor: 0.95 (`costs_size_multipliers.xlsx`, Sheet: `Size_Multipliers`, Technology: `Solar_PV`, Size_Range: `50-100MW`)
- Regional multiplier: 1.15 (`regional_multipliers.xlsx`, Sheet: `Labor_Cost_Adjustments`, ISO: `JPN`)
- Vintage adjustment: 0.90 (`thermal_efficiency.xlsx`, Sheet: `Efficiency_by_Vintage`, Technology: `Solar_PV`, Year: `2020`)
- **Final CAPEX**: $1,175/kW

### 2. Capacity Factors / Utilization Rates
**Methodology**: Intelligent source selection based on data quality assessment

**Source Priority Logic**:
1. **Data Completeness**: Preference for sources with full time series
2. **Realistic Range**: Utilization factors between 5-95% (excludes outliers)
3. **Cross-Source Consistency**: Agreement between IRENA and EMBER data
4. **Recent Data**: Priority to 2018-2022 observations

**Technology-Specific Adjustments**:
- **Solar PV**: Resource-weighted by GIS solar irradiation data
- **Wind**: Adjusted for local wind resource potential
- **Hydro**: Separate treatment for run-of-river vs. reservoir plants
- **Thermal**: Efficiency degradation based on fleet vintage

### 3. Operating & Maintenance Costs
**Fixed O&M**: Regional labor cost adjustments applied to WEO base assumptions
**Variable O&M**: Technology-specific fuel and maintenance costs
**Regional Scaling**: Based on GDP per capita and energy sector wage premiums

### 4. Thermal Efficiency
**Base Efficiency**: From WEO technology assumptions by vintage
**Vintage Degradation**: Annual efficiency decline of 0.1-0.3% based on technology type
**Size Scaling**: Larger plants have higher efficiency (economies of scale)
**Regional Factors**: Ambient temperature and altitude adjustments where applicable

---

## Existing Power Plant Inventory

### Plant Characterization Process
1. **Individual Plant Data**: All operating plants from GEM database
2. **Technology Mapping**: Harmonized fuel and technology classifications
3. **Vintage Analysis**: Age-based performance and efficiency assignments
4. **Aggregation**: Grouped by technology with weighted-average characteristics

### Key Parameters Derived
- **Total Installed Capacity**: Sum of individual plant capacities by technology
- **Average Plant Size**: Typical unit size for new capacity additions
- **Fleet Age**: Capacity-weighted average commissioning year
- **Geographic Distribution**: Regional clustering for transmission planning
- **Retirement Schedule**: Based on technical lifetime assumptions

### Quality Control
- **Cross-Validation**: IRENA/EMBER totals compared to GEM plant-level sums
- **Outlier Detection**: Plants with unrealistic specifications flagged for review
- **Completeness Check**: Missing data supplemented with regional averages

---

## Future Scenario Development

### Scenario Framework
Based on **NGFS (Network for Greening the Financial System)** climate scenarios:
- **Current Policies**: Continuation of existing policy frameworks
- **Nationally Determined Contributions (NDCs)**: Countries meet stated climate commitments
- **Below 2°C**: Policies consistent with Paris Agreement temperature goals
- **Net Zero 2050**: Pathways to achieve carbon neutrality by mid-century

### Technology Deployment Projections
**Capacity Expansion Logic**:
1. **Demand Growth**: Based on economic and population projections
2. **Retirement Schedule**: Existing plants retired at end of technical lifetime
3. **Technology Competition**: Least-cost optimization considering carbon pricing
4. **Policy Constraints**: Renewable energy targets and fossil fuel phase-out timelines

**Carbon Price Trajectories**:
- Sector-specific CO2 pricing from NGFS scenarios
- Regional variation in carbon policy implementation
- Technology-neutral carbon pricing in optimization

---

## Regional and Country-Specific Adjustments

### Economic Context
- **Labor Costs**: Adjusted using World Bank wage and productivity data
- **Material Costs**: Globally traded components (steel, silicon) at world prices
- **Local Content**: Country-specific local sourcing requirements where applicable

### Resource Endowment
- **Renewable Resources**: GIS-based solar and wind resource assessments
- **Fossil Fuel Availability**: Domestic resource base and import dependencies
- **Grid Integration**: Transmission capacity and grid stability constraints

### Policy Environment
- **Renewable Targets**: Nationally announced renewable energy goals
- **Carbon Policies**: Existing and planned carbon pricing mechanisms
- **Technology Bans**: Phase-out schedules for specific technologies (e.g., coal)

---

## Data Quality and Uncertainty

### Quality Indicators
Each parameter includes quality flags indicating data reliability:

- **🟢 HIGH**: Multiple consistent sources, complete data, recent observations
- **🟡 MEDIUM**: Some data gaps or inconsistencies, reasonable estimates available
- **🔴 LOW**: Limited data availability, significant uncertainty in estimates
- **⚪ UNAVAILABLE**: Insufficient data for reliable parameter estimation

### Uncertainty Quantification
**Typical Uncertainty Ranges**:
- **Capacity Factors**: ±5-15% depending on technology and data availability
- **Capital Costs**: ±10-25% reflecting regional cost variations
- **Fuel Costs**: ±20-40% due to price volatility and long-term projections
- **Demand Projections**: ±15-30% reflecting economic and demographic uncertainties

### Validation Methodology
- **Cross-Source Comparison**: IRENA vs. EMBER vs. GEM consistency checks
- **Historical Benchmarking**: Model results compared to observed capacity additions
- **Expert Review**: Technology parameters validated by sectoral specialists

---

## Model Structure and Usage Notes

### Technology Representation
- **Discrete Technologies**: Each fuel/technology combination modeled separately
- **Vintage Tracking**: Multiple vintages for technologies with changing costs/performance
- **Capacity Credit**: Firm capacity contributions for intermittent renewables
- **Operational Constraints**: Minimum load factors, ramp rates, seasonal availability

### Temporal Resolution
- **Planning Horizon**: 2020-2050 in 5-year intervals
- **Operational Modeling**: Annual energy balance with seasonal variations
- **Peak Demand**: Capacity adequacy requirements based on historical load patterns

### Geographic Scope
- **National Models**: Country-level aggregation with regional detail where data permits
- **Cross-Border Trade**: Electricity import/export capabilities and costs
- **Resource Sharing**: Renewable energy potential accessible across regions

---

## Limitations and Caveats

### Data Limitations
1. **Developing Countries**: Limited plant-level data may reduce parameter accuracy
2. **Emerging Technologies**: Hydrogen, CCS, and storage costs based on early deployments
3. **Sub-National Variation**: Country-level averages may not reflect regional differences
4. **Dynamic Policies**: Rapid policy changes not captured in annual data updates

### Modeling Assumptions
1. **Perfect Competition**: Technology selection based on least-cost optimization
2. **Perfect Foresight**: Future costs and policies assumed known with certainty
3. **No Behavioral Factors**: Consumer preferences and acceptance not explicitly modeled
4. **Grid Stability**: Transmission and distribution constraints simplified

### Recommended Usage
- **Strategic Planning**: Long-term capacity expansion and policy analysis
- **Technology Assessment**: Comparative evaluation of energy technologies
- **Scenario Analysis**: Impact of policy and technology changes
- **Investment Analysis**: High-level economic evaluation of energy projects

**Not Recommended For**:
- Detailed grid operations and stability analysis
- Sub-annual or hourly operational optimization
- Site-specific project feasibility studies
- Short-term market price forecasting

---

## Citation and Data Lineage

### Primary Sources
When using VerveStacks models, please cite the original data sources:
- IRENA Global Energy Transformation datasets
- EMBER Global Electricity Review
- Global Energy Monitor Power Plant Tracker
- NGFS Climate Scenarios for Central Banks and Supervisors
- IEA World Energy Outlook Technology Annexes

### Methodology Citation
**Suggested Citation**: 
"Energy system parameters derived using VerveStacks methodology, integrating data from IRENA, EMBER, Global Energy Monitor, NGFS, and IEA World Energy Outlook. Technology costs adjusted for regional economic conditions and plant vintage characteristics."

### Version Control
- **Model Version**: Included in SysSettings file of each country model
- **Data Vintage**: Source data collection dates documented in model metadata
- **Processing Date**: Timestamp of model generation included in documentation
- **Parameter Lineage**: Traceability of each parameter to original data source

---

This methodology ensures transparent, reproducible, and high-quality energy system models while maintaining the flexibility needed for diverse analytical applications. 