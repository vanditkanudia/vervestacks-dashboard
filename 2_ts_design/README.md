# VerveStacks Timeslice Design Module

## Overview
The `2_ts_design` module contains the core VerveStacks timeslice processor that transforms 8760-hour annual data into intelligent, stress-based timeslice structures optimized for each ISO's unique characteristics.

## Structure
```
2_ts_design/
├── scripts/
│   ├── RE_Shapes_Analysis_v5.py          # Main timeslice processor
│   ├── 8760_supply_demand_constructor.py # 8760-hour supply/demand profiles
│   └── enhanced_lcoe_calculator.py       # LCOE calculation engine
├── outputs/                              # ISO-organized outputs
│   ├── USA/                              # United States outputs
│   ├── GER/                              # Germany outputs  
│   ├── CHN/                              # China outputs
│   └── ...                               # Other ISOs
├── config/
│   ├── default_settings.json             # Default parameters
│   └── iso_settings.json                 # ISO-specific overrides
└── README.md                             # This file
```

## Configuration System

### Default Settings (`config/default_settings.json`)
- **max_timeslices**: Default maximum timeslices (500)
- **scenario_types**: Three standard scenarios (short/medium/long spans)
- **technology_costs**: Default LCOE parameters
- **processing_options**: Output and analysis settings

### ISO-Specific Settings (`config/iso_settings.json`)
Override defaults for specific ISOs based on their characteristics:
- **USA**: 600 timeslices (complex grid)
- **CHN**: 400 timeslices (large system)
- **GER**: 350 timeslices (high renewable penetration)
- **BOL**: 200 timeslices (smaller hydro-dominated system)

## Usage

### Basic Usage
```python
from scripts.RE_Shapes_Analysis_v5 import VerveStacksTimesliceProcessor

# Initialize with configuration
processor = VerveStacksTimesliceProcessor(
    data_path="../data/",
    config_path="./config/"
)

# Process single ISO
results = processor.run_full_pipeline(
    target_isos=['USA'],
    save_results=True,
    output_dir="./outputs/"
)
```

### EMBER Electricity Generation Data Access
```python
from scripts.8760_supply_demand_constructor import Supply8760Constructor

# Initialize constructor
constructor = Supply8760Constructor()

# Get total electricity generation for Germany in 2022
germany_total = constructor.get_total_electricity_generation('DEU', 2022)
# Returns: 566.23 TWh

# Get generation breakdown by fuel for Germany in 2022
germany_fuels = constructor.get_generation_by_fuel('DEU', 2022)
# Returns DataFrame with fuel types and values

# Get generation capacity by fuel type in GW for Germany in 2022
germany_capacity_gw = constructor.get_capacity_by_fuel('DEU', 2022)
# Returns dict with fuel types and capacity in GW from multiple sources

# Create hourly generation profile using ISO-specific demand shape
germany_profile = constructor.create_hourly_generation_profile('DEU', 100.0, use_demand_shape=True)
# Returns: 8760-hour array with Germany's unique demand pattern, scaled to 100 TWh annual
```

### 8760-Hour Supply and Demand Profiles
```python
from scripts.8760_supply_demand_constructor import Supply8760Constructor

# Initialize constructor
constructor = Supply8760Constructor()

# Get total generation from EMBER data
total_gen = constructor.get_total_electricity_generation('DEU', 2022)

# Build complete 8760-hour profiles
profiles = constructor.construct_8760_profiles('DEU')
```

### Custom Configuration
```python
# Override specific parameters
processor = VerveStacksTimesliceProcessor(
    max_timeslices=400,  # Override default
    data_path="../data/",
    config_path="./config/"
)
```

## Output Files (per ISO)

### Timeslice Definitions
- `timeslices_{ISO}_short_spans.csv` - High-resolution critical periods
- `timeslices_{ISO}_medium_spans.csv` - Balanced resolution
- `timeslices_{ISO}_long_spans.csv` - Seasonal aggregation

### Analysis Files
- `segment_summary_{ISO}.csv` - Statistical summary
- `season_clusters_{ISO}.csv` - Seasonal clustering analysis
- `period_clusters_{ISO}.csv` - Diurnal period analysis

### Visualizations
- `RE_scenarios_hourly_{ISO}.svg` - Main scenario comparison
- `re_analysis_summary_{ISO}.svg` - Renewable analysis overview
- `aggregation_justification_{ISO}.svg` - Aggregation validation
- `individual_scenarios/` - Detailed scenario plots

## Data Dependencies

The module requires data files in the `../data/` directory:
- `timeslices/region_map.xlsx` - ISO to country mapping
- `hourly_profiles/era5_combined_data_2030.csv` - Hourly demand profiles
- `irena/IRENASTAT-C.xlsx` - Installed capacity data
- `irena/IRENASTAT-G.xlsx` - Generation data
- `timeslices/re_potentials.xlsx` - Renewable resource potential
- `hourly_profiles/sarah_era5_iso_2015.csv` - Renewable generation shapes
- `timeslices/monthly_full_release_long_format.csv` - Hydro patterns
- `ember/yearly_full_release_long_format.csv` - EMBER electricity generation data
- `ember/monthly_full_release_long_format.csv` - EMBER monthly hydro patterns

## Key Features

### Adaptive Timeslice Generation
- **Stress-based identification**: Focuses on periods that matter most for grid operations
- **Multi-scenario approach**: Three complementary timeslice structures
- **ISO-specific tuning**: Optimized parameters for each region's characteristics

### Enhanced Analysis
- **LCOE-based optimization**: Uses actual technology costs for realistic capacity mix
- **Historical deployment ratios**: Solar/wind mix based on recent IRENA data
- **Comprehensive validation**: Statistical analysis of timeslice adequacy

### EMBER Data Integration
- **Electricity generation data**: Access total generation and fuel breakdown by ISO and year
- **8760-hour profiles**: Complete hourly supply and demand profiles for any ISO
- **ISO-specific demand shapes**: Each country uses its own unique demand pattern for generation profiles
- **Baseline generation**: Nuclear and hydro profiles from actual EMBER data
- **Renewable integration**: Solar and wind from REZoning with hourly shapes

### Flexible Configuration
- **Default parameters**: Sensible defaults for all ISOs
- **ISO-specific overrides**: Customized settings for complex regions
- **Runtime configuration**: Easy parameter adjustment without code changes

## Technical Notes

### Memory Requirements
- Large ISOs (USA, CHN) may require 8GB+ RAM for full processing
- Consider processing in smaller batches for memory-constrained systems

### Processing Time
- Typical processing time: 5-15 minutes per ISO
- Varies with system complexity and renewable potential data size

### EMBER Data Access
- **Data coverage**: 210+ countries with electricity generation data (2000-2023)
- **Data quality**: Official national statistics and international databases
- **Performance**: Cached data loading for efficient repeated access

### Customization
- Modify `config/iso_settings.json` to add new ISOs or adjust parameters
- Update `config/default_settings.json` to change global defaults
- Add custom scenarios by modifying the scenario_types configuration