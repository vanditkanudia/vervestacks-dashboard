# FACETS Model Validation

## Overview

Validation of FACETS (Framework for Analysis of Clean Energy Transition Scenarios) model outputs against hourly operational reality.

## Key Findings

- **Dispatchable Capacity Gap**: FACETS underestimates dispatchable capacity needs by 538%
- **Storage Requirements**: FACETS underestimates storage needs by 2,324%
- **Operational Flexibility**: Massive ramping requirements (100+ GW/hour) invisible to timeslice aggregation

## Data Structure

```
FACETS/
├── scripts/
│   ├── hourly_operational_simulator.py     # Single-region operational simulation
│   ├── facets_hourly_simulator.py          # Multi-regional transmission group analysis
│   ├── batch_processor.py                  # Automated batch processing
│   ├── scenario_selector.py                # Intelligent scenario selection
│   └── hourly_profile_explorer.py          # Detailed profile visualization
├── data/
│   ├── model_outputs/             # Required FACETS inputs
│   │   ├── VSInput_capacity by tech and region.csv
│   │   ├── VSInput_generation by tech, region, and timeslice.csv
│   │   ├── FACETS_aggtimeslices.csv
│   │   ├── technology_categories.csv
│   │   └── transmission_region_groups.csv
│   ├── hourly_data/              # FACETS hourly profiles
│   │   ├── EER_100by2050_load_hourly.h5
│   │   ├── upv-reference_ba.h5
│   │   └── wind-ons-reference_ba.h5
│   └── processed/                # Analysis intermediate data
├── outputs/
│   ├── plots/                    # Validation visualizations
│   └── reports/                  # Analysis reports
└── config/                       # FACETS-specific settings
```

## Usage

### Single Region Analysis
```bash
cd 3_model_validation/FACETS/scripts/
python hourly_operational_simulator.py
```

### Multi-Regional Transmission Group Analysis
```bash
cd 3_model_validation/FACETS/scripts/
python facets_hourly_simulator.py --transmission_group MISO_North
python facets_hourly_simulator.py --transmission_group ERCOT
python facets_hourly_simulator.py --transmission_group PJM_East
```

### Batch Processing
```bash
cd 3_model_validation/FACETS/scripts/
python scenario_selector.py    # First select scenarios (see user guide)
python batch_processor.py      # Then run batch analysis
```

**📖 Detailed Documentation**: See `docs/scenario_selector_user_guide.md` for complete usage instructions, methodology, and output descriptions.

## Analysis Parameters

- **Scenario**: `gp-I.re-L.Pol-IRA.Cp-95.ncs-I.smr-I`
- **Year**: 2045
- **Region**: p063 (largest FACETS region)
- **Timeslice**: W1AM2 (Winter, late morning)

## Key Metrics

### Capacity Planning Gaps
- **Peak dispatchable need**: 42.1 GW (vs 6.6 GW planned)
- **Optimal storage capacity**: 1,068 GW (vs 44 GW planned)
- **Ramping requirements**: 115 GW range, 100 GW/hour max

### Operational Challenges
- **Surplus hours**: 51% of winter mornings
- **Curtailment potential**: 4.3 TWh surplus energy
- **Grid flexibility**: Orders of magnitude larger than modeled

## Methodology

1. **Extract FACETS Planning** - Load capacity and generation decisions
2. **Map Temporal Structure** - Convert timeslices to hourly indices
3. **Apply Hourly Reality** - Use actual demand/renewable profiles
4. **Calculate Gaps** - Compare planned vs required infrastructure
5. **Quantify Impacts** - Assess operational and economic implications

## Current Capabilities

### Multi-Regional Support
- **18 Transmission Groups**: All major US electricity markets
- **135 Total Regions**: From 2-region (NYISO) to 19-region (PJM_East) systems
- **Copper-Plate Analysis**: System-wide optimization within transmission groups

### Batch Processing
- **Smart Caching**: Skip existing results for efficiency
- **Progress Tracking**: ETA estimation and resume capability
- **Error Handling**: Graceful continuation after failures
- **Professional Outputs**: Excel files with FACETS branding

### Scenario Analysis
- **Intelligent Selection**: Technology penetration optimization
- **Comparative Analysis**: Cross-regional and cross-scenario insights
- **Visualization Suite**: Professional charts and interactive dashboards

## Future Extensions

- Inter-regional transmission modeling
- Stochastic weather analysis
- Economic dispatch optimization
- Real-time market validation