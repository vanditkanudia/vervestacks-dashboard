# Hourly Operational Simulator - Technical Documentation

## Overview

The FACETS validation suite consists of multiple interconnected scripts for comprehensive energy system analysis:

- **`hourly_operational_simulator.py`**: Core single-region operational simulation
- **`facets_hourly_simulator.py`**: Multi-regional transmission group analysis  
- **`batch_processor.py`**: Automated batch processing across scenarios and regions
- **`scenario_selector.py`**: Intelligent scenario selection for focused analysis
- **`hourly_profile_explorer.py`**: Detailed visualization of hourly profiles

This document details the data flows, transformations, and function execution logic across all components.

## Class Architecture

### `HourlyOperationalSimulator`
**Purpose**: Main orchestration class for hourly operational simulation and capacity adequacy validation (single-region analysis)

**Key Attributes**:
- `weather_year`: Weather pattern year for renewable profiles (default: 2018)
- `scenario`: FACETS scenario identifier 
- `year`: Demand projection year (default: 2045)
- `region`: Target region (default: "p063")
- `tech_categories`: Technology classification mappings
- `storage_parameters`: Storage technology specifications
- `temporal_mapping`: FACETS timeslice-to-hour mappings

### `HourlySupplyCreator`
**Purpose**: Multi-regional transmission group analysis and validation (from `facets_hourly_simulator.py`)

**Key Attributes**:
- `transmission_group`: Target transmission group (e.g., 'MISO_North', 'ERCOT')
- `weather_year`: Weather pattern year (default: 2012)
- `scenario`: FACETS scenario identifier
- `year`: Analysis year (default: 2045)
- `region`: Optional single region for backward compatibility
- `regions`: List of FACETS regions in transmission group
- `demand_regions`: Corresponding demand format regions

### `FACETSBatchProcessor`
**Purpose**: Automated batch processing across multiple scenarios and regions (from `batch_processor.py`)

**Key Features**:
- Smart caching to skip existing results
- Progress tracking with ETA estimation
- Resume capability after interruptions
- Error handling with graceful continuation
- Professional Excel outputs with FACETS branding

### `ScenarioSelector`
**Purpose**: Intelligent scenario selection for focused analysis (from `scenario_selector.py`)

**Key Features**:
- Technology penetration analysis (SMR, Gas CCS, Solar, Wind, Storage)
- Multi-criteria selection algorithm (6-step process)
- Scenario diversity optimization across 108 FACETS scenarios
- MISO region analysis (12 regions across 3 transmission groups)
- Professional visualization and reporting

**📖 Complete User Guide**: See `scenario_selector_user_guide.md` for detailed methodology, parameters, and usage instructions.

## Data Loading & Transformation Pipeline

### 1. Configuration & Initialization

#### `__init__(weather_year, config_file=None)`
**Purpose**: Initialize simulator with configuration parameters

**Data Sources**:
- Optional JSON config file for parameters
- Fallback to hardcoded defaults

**Key Transformations**:
```python
# Path resolution (relative to script location)
self.model_outputs_path = "../data/model_outputs/"
self.hourly_data_path = "../data/hourly_data/" 
self.vs_profiles_path = "../../../vs_native_profiles/"

# Parameter loading hierarchy: config_file → defaults
config = json.load(config_file) if config_file else {}
self.scenario = config.get('scenario', "gp-I.re-L.Pol-IRA.Cp-95.ncs-I.smr-I")
```

### 2. Technology Classification Loading

#### `load_technology_categories()`
**Purpose**: Load technology-to-category mappings for capacity analysis

**Data Sources**:
1. **Primary**: `{model_outputs_path}technology_categories.csv`
2. **Fallback**: Hardcoded technology categories

**Expected CSV Format**:
```csv
technology,category
Solar PV,renewable
Storage,storage
Combined Cycle,dispatchable
```

**Transformation Logic**:
```python
categories = {}
for _, row in tech_df.iterrows():
    category = row['category']
    if category not in categories:
        categories[category] = []
    categories[category].append(row['technology'])
```

**Output**: Dictionary mapping categories to technology lists

### 3. Storage Parameters Loading

#### `load_storage_parameters()`
**Purpose**: Extract storage technology specifications from FACETS data

**Data Sources** (Priority Order):
1. `{model_outputs_path}storage_characteristics.csv` (FACETS-specific)
2. Industry standard fallback parameters

**Filter Criteria**:
```python
filtered = storage_df[
    (storage_df['scen'] == self.scenario) &
    (storage_df['year'] == self.year) &
    (storage_df['region'] == self.region)
]
```

**Key Parameters Extracted**:
- `duration_hours`: Storage energy duration
- `round_trip_efficiency`: Charge/discharge efficiency (%)  
- `min_soc`: Minimum state of charge (%)
- `max_soc`: Maximum state of charge (%)

**Fallback Values**:
```python
{
    'duration_hours': 8.0,
    'round_trip_efficiency': 85.0,
    'min_soc': 5.0,
    'max_soc': 95.0
}
```

### 4. Temporal Mapping Loading

#### `load_temporal_mapping()`
**Purpose**: Map FACETS timeslices to calendar hours for temporal alignment

**Data Source**: `{model_outputs_path}FACETS_aggtimeslices.csv`

**Key Transformations**:
```python
# Extract month mappings
month_mapping = {}
for month in range(1, 13):
    month_data = df[df['month'] == month]
    month_mapping[month] = {
        'month_name': month_data['month_name'].iloc[0],
        'timeslices': month_data['timeslice'].unique().tolist()
    }

# Extract hour mappings  
hour_mapping = {}
for hour in range(24):
    hour_data = df[df['hour'] == hour]
    hour_mapping[hour] = {
        'timeslices': hour_data['timeslice'].unique().tolist()
    }
```

**Output**: Two-level mapping structure for month→timeslice and hour→timeslice

### 5. FACETS Capacity Data Loading

#### `load_facets_capacity_data()`
**Purpose**: Load planned capacity mix from FACETS optimization results

**Data Source**: `{model_outputs_path}VSInput_capacity by tech and region.csv`

**Filter & Aggregation Logic**:
```python
# Filter for target scenario/year/region
filtered_capacity = df[
    (df['scen'] == self.scenario) & 
    (df['year'] == self.year) & 
    (df['region'] == self.region)
]

# Aggregate by technology categories
for tech in filtered_capacity['technology'].unique():
    capacity_value = filtered_capacity[
        filtered_capacity['technology'] == tech
    ]['new_capacity'].sum()
    
    # Categorize using tech_categories mapping
    if tech in self.tech_categories['renewable']:
        renewable_capacity += capacity_value
    elif tech in self.tech_categories['storage']:
        storage_capacity += capacity_value
    # ... etc
```

**Key Outputs**:
- `renewable_capacity`: Total renewable capacity (GW)
- `storage_capacity`: Total storage power capacity (GW)  
- `dispatchable_capacity`: Total dispatchable capacity (GW)
- `wind_capacity`: Wind-specific capacity (GW)
- `solar_capacity`: Solar-specific capacity (GW)

### 6. Hourly Profile Data Loading

#### `load_annual_hourly_data()`
**Purpose**: Load 8,760-hour time series for demand and renewable capacity factors

**Data Sources**:
1. **Demand**: `{hourly_data_path}EER_100by2050_load_hourly.h5`
2. **Solar**: `{hourly_data_path}upv-reference_ba.h5`  
3. **Wind**: `{hourly_data_path}wind-ons-reference_ba.h5`

**HDF5 Data Extraction**:
```python
def load_renewable_profile(filename, tech_name):
    with h5py.File(f"{self.hourly_data_path}{filename}", 'r') as f:
        # Navigate HDF5 structure
        region_data = f[self.region_hdf5]  # e.g., 'p63'
        weather_group = region_data[str(self.weather_year)]  # e.g., '2018'
        hourly_data = weather_group[:]  # Extract 8760 values
        return hourly_data
```

**Demand Profile Scaling**:
```python
# Scale 2012 base demand to target year
# Uses economic growth projections embedded in FACETS
scaled_demand = base_hourly_demand * demand_growth_factor
```

**Validation Checks**:
- Verify 8,760 hours (annual coverage)
- Check reasonable value ranges
- Ensure no missing data gaps

## Core Analysis Functions

### 7. Stress Period Identification

#### `identify_stress_periods(hourly_demand, hourly_solar_cf, hourly_wind_cf)`
**Purpose**: Identify periods of maximum operational stress using rolling window analysis

**Algorithm**:
```python
# Calculate hourly renewable generation
hourly_renewable_gen = (
    hourly_solar_cf * facets_solar_capacity +
    hourly_wind_cf * facets_wind_capacity
) * 1000  # Convert GW to MW

# Calculate net load (demand minus renewables)
hourly_net_load = hourly_demand - hourly_renewable_gen

# Rolling window analysis (168 hours = 1 week)
rolling_window_size = 168
for start_hour in range(0, 8760 - rolling_window_size):
    window_net_load = hourly_net_load[start_hour:start_hour + rolling_window_size]
    
    # Stress metrics
    max_net_load = window_net_load.max()
    total_ramp = (window_net_load.diff().abs()).sum()
    min_renewable = hourly_renewable_gen[start_hour:start_hour + rolling_window_size].min()
```

**Stress Period Types**:
- **Worst Net Load Week**: Highest peak net load requirement
- **Worst Ramp Week**: Maximum ramping requirements
- **Worst Renewable Week**: Lowest renewable generation

### 8. Hourly Dispatch Simulation

#### `simulate_hourly_dispatch(annual_net_load, dispatchable_capacity_mw, storage_capacity_gw)`
**Purpose**: Simulate hour-by-hour system operation with storage and dispatchable resources

**Core Algorithm**:
```python
# Initialize storage state
storage_energy_gwh = np.zeros(8760)  
current_soc = max_energy_gwh * 0.5  # Start at 50% SOC

for hour in range(8760):
    net_load_mw = annual_net_load[hour]
    
    if net_load_mw > 0:  # Generation shortage
        # Dispatch order: 1) Storage, 2) Dispatchable
        available_storage = min(
            current_soc - min_energy_gwh,  # Available energy
            max_discharge_power_gw * 1000  # Power limit
        )
        
        storage_dispatch = min(available_storage, net_load_mw)
        remaining_need = net_load_mw - storage_dispatch
        
        dispatchable_dispatch = min(remaining_need, dispatchable_capacity_mw)
        unserved_energy = remaining_need - dispatchable_dispatch
        
    else:  # Generation surplus  
        # Charge storage, curtail excess
        available_storage_space = max_energy_gwh - current_soc
        max_charge = min(
            available_storage_space,
            max_charge_power_gw * 1000
        )
        
        storage_charge = min(max_charge, abs(net_load_mw))
        curtailed_energy = abs(net_load_mw) - storage_charge
```

**Key Constraints**:
- Storage power limits (charge/discharge)
- Storage energy limits (SOC bounds)
- Storage efficiency losses
- Dispatchable capacity limits

### 9. Storage Adequacy Assessment

#### `assess_storage_adequacy(energy_analysis, facets_capacity)`
**Purpose**: Compare planned storage capacity against operational requirements

**Analysis Dimensions**:
```python
# Energy adequacy
planned_energy_gwh = facets_storage_gw * storage_duration_hours
required_energy_gwh = max(storage_energy_levels)

# Power adequacy  
planned_power_gw = facets_storage_gw
required_power_gw = max(max_charge_rates, max_discharge_rates)

# Duration adequacy
planned_duration = planned_energy_gwh / planned_power_gw
required_duration = required_energy_gwh / required_power_gw
```

### 10. Stress Week Analysis

#### `analyze_stress_week(stress_start_hour, hourly_demand, hourly_solar_cf, hourly_wind_cf, stress_info)`
**Purpose**: Detailed operational analysis of the most challenging week

**Daily Breakdown Analysis**:
```python
for day in range(7):  # 7 days in stress week
    day_start = stress_start_hour + (day * 24)
    day_end = day_start + 24
    
    daily_demand = hourly_demand[day_start:day_end]
    daily_renewable = hourly_renewable_gen[day_start:day_end]
    daily_net_load = daily_demand - daily_renewable
    
    # Calculate daily operational metrics
    daily_peak_need = daily_net_load.max()
    daily_ramp_range = daily_net_load.max() - daily_net_load.min()
    
    # Map to FACETS timeslices for comparison
    daily_timeslices = []
    for hour_in_day in range(24):
        calendar_hour = (day_start + hour_in_day) % 8760
        month, hour_of_day = self.hour_to_calendar(calendar_hour)
        timeslice = self.map_to_facets_timeslice(month, hour_of_day)
        daily_timeslices.append(timeslice)
```

## Visualization Generation

### 11. Stress Week Visualization

#### `create_stress_week_visualization(stress_analysis, stress_type, facets_capacity)`
**Purpose**: Generate detailed plots of operational stress patterns

**Plot Components**:
- **Primary Plot**: Hourly demand, renewable generation, net load
- **Secondary Plot**: FACETS timeslice mapping overlay
- **Annotations**: Peak requirements, ramp rates, capacity gaps

### 12. Storage Operation Visualizations

#### `create_annual_storage_visualization(energy_analysis, storage_adequacy)`
**Purpose**: Annual overview of storage operation patterns

#### `create_quarterly_storage_visualizations(energy_analysis, storage_adequacy)`
**Purpose**: Seasonal breakdown of storage operation

**Plot Elements**:
- Storage energy levels (SOC over time)
- Charge/discharge patterns
- Planned vs required capacity overlays
- Unserved energy and curtailment periods

## Main Execution Flow

### `run_operational_simulation()`
**Purpose**: Orchestrate complete operational simulation and validation

**Execution Sequence**:
```python
# 1. Load all data-driven parameters
self.storage_parameters = self.load_storage_parameters()
self.temporal_mapping = self.load_temporal_mapping()

# 2. Load annual hourly data (demand + renewables)
hourly_demand, hourly_solar_cf, hourly_wind_cf = self.load_annual_hourly_data()

# 3. Load FACETS planned capacity
self.facets_capacity = self.load_facets_capacity_data()

# 4. Identify operational stress periods
stress_info = self.identify_stress_periods(hourly_demand, hourly_solar_cf, hourly_wind_cf)

# 5. Analyze primary stress period in detail
stress_analysis = self.analyze_stress_week(...)

# 6. Create stress period visualization
plot_file = self.create_stress_week_visualization(...)

# 7. Run annual storage energy analysis
energy_analysis = self.analyze_annual_storage_energy_needs(self.facets_capacity)

# 8. Assess storage adequacy
storage_adequacy = self.assess_storage_adequacy(energy_analysis, self.facets_capacity)

# 9. Generate visualization suite
storage_plots = self.create_quarterly_storage_visualizations(...)
```

## Data Dependencies & File Structure

### Required Input Files
```
3_model_validation/FACETS/data/
├── model_outputs/
│   ├── VSInput_capacity by tech and region.csv      # FACETS capacity results
│   ├── VSInput_generation by tech, region, and timeslice.csv  # FACETS generation results
│   ├── FACETS_aggtimeslices.csv                     # Timeslice definitions
│   ├── technology_categories.csv                    # Tech classifications
│   ├── transmission_region_groups.csv               # Transmission group mappings
│   └── storage_characteristics.csv                  # Storage parameters (optional)
├── hourly_data/
│   ├── EER_100by2050_load_hourly.h5                # Annual demand profiles
│   ├── upv-reference_ba.h5                         # Solar capacity factors
│   └── wind-ons-reference_ba.h5                    # Wind capacity factors
└── processed/                                       # Generated intermediate files
```

### Generated Output Files
```
3_model_validation/FACETS/outputs/
├── plots/
│   ├── facets_stress_week_worst_net_load_week_p063_weather2018.png
│   ├── annual_storage_operation_p063_weather2018.png
│   ├── storage_operation_Q1_p063_weather2018.png
│   ├── storage_operation_Q2_p063_weather2018.png
│   ├── storage_operation_Q3_p063_weather2018.png
│   └── storage_operation_Q4_p063_weather2018.png
├── tables/
│   ├── system_adequacy_summary_weather2018.csv
│   ├── regional_capacity_analysis_weather2018.csv
│   └── transmission_corridor_stats_weather2018.csv
└── reports/                                         # Future: Automated reports
```

## Key Algorithms & Transformations

### Storage State-of-Charge Calculation
```python
# Hour-by-hour SOC tracking with efficiency losses
if charging:
    soc_change = charge_power_gw * efficiency / 100
else:  # discharging
    soc_change = -discharge_power_gw / (efficiency / 100)

new_soc = current_soc + soc_change
new_soc = np.clip(new_soc, min_energy_gwh, max_energy_gwh)
```

### Net Load Calculation
```python
# Core energy balance equation
net_load = demand - variable_renewable_generation
# Where:
# net_load > 0: Need dispatchable generation/storage discharge
# net_load < 0: Excess generation for storage charge/curtailment
```

### Timeslice Mapping Algorithm
```python
def map_to_facets_timeslice(month, hour_of_day):
    # Map calendar time to FACETS timeslice identifier
    # Enables comparison of hourly operational reality vs model timeslices
    return timeslice_mapping[month][hour_of_day]
```

## Extension Points

### Adding New Regions
- Update `region` and `region_hdf5` parameters
- Verify HDF5 file contains target region data
- Adjust demand scaling factors if needed

### Adding New Technologies
- Extend `tech_categories` classification
- Update capacity aggregation logic
- Add technology-specific operational constraints

### Adding New Scenarios
- Update `scenario` parameter to match FACETS naming
- Verify FACETS output files contain target scenario data
- Adjust temporal/spatial parameters as needed

---

**Document Version**: 2.0  
**Last Updated**: August 2025  
**Script Version**: hourly_operational_simulator.py (formerly stress_period_analyzer_v3.py)  
**Multi-Regional Support**: Added via facets_hourly_simulator.py  
**Batch Processing**: Available via batch_processor.py
