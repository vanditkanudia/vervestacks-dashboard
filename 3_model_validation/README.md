# Model Validation Framework

## Overview

The Model Validation framework compares energy model outputs against operational reality to identify gaps in capacity planning, operational flexibility, and infrastructure requirements.

## Structure

```
3_model_validation/
├── FACETS/                 # FACETS model validation
├── KiNESYS_kapsarc/       # Future: KiNESYS validation
└── other_model_xyz/       # Template for additional models
```

## Validation Methodology

### Required Model Inputs
Each model validation requires three core inputs:
1. **Generation by tech and timeslice** - Model's generation dispatch
2. **Capacity by tech** - Model's capacity planning decisions  
3. **Timeslice definition** - Model's temporal aggregation scheme

### Hourly Reality Data
For operational comparison, we use:
- **Model-specific hourly data** (if available)
- **VS native profiles** (fallback from `../vs_native_profiles/`)
- **Global defaults** (last resort)

## Key Analyses

### Capacity Adequacy
- Compare planned capacity vs peak operational requirements
- Identify dispatchable capacity shortfalls
- Assess storage capacity needs vs surplus energy management

### Operational Flexibility  
- Analyze ramping requirements vs model assumptions
- Evaluate sub-timeslice operational challenges
- Quantify curtailment risks and storage opportunities

### Technology Mix
- Validate renewable vs dispatchable balance
- Assess technology-specific capacity factors
- Compare economic assumptions vs operational reality

## Adding New Models

1. Create `new_model_name/` folder
2. Implement model-specific data parsers
3. Adapt validation metrics for model characteristics
4. Document model-specific validation methodology

## Usage

Each model folder is self-contained and can be run independently.
See individual model README files for specific usage instructions.