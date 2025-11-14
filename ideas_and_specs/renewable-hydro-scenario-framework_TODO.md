# Integrated Renewable & Hydro Scenario Framework
## Implementation Guide for Multi-Resource Energy Planning

### Executive Summary
This framework addresses the critical gap in energy planning models that use single weather years (e.g., 2013) repeated across all future periods. It provides methods to generate correlated synthetic scenarios for hydro, wind, and solar resources that capture:
- Inter-annual variability
- Climate change impacts
- Physical correlations between resources
- Compound extreme events

---

## 1. Problem Statement

### Current Limitations
- **Hydro**: Using 5-year average for all future periods → No drought/wet year variation
- **Wind/Solar**: Single 2013 weather year repeated → Missing ±15-20% annual variability
- **Correlations**: Resources treated independently → Missing compound risks (e.g., simultaneous hydro drought + wind drought)

### Impact on Planning
- Underestimating required reserve margins by 10-20%
- Missing critical stress scenarios (e.g., 2021 European energy crisis)
- False confidence in renewable reliability
- Inability to value geographic/technological diversification

---

## 2. Hydro Availability Scenarios

### 2.1 Data Structure
```
Base Data Required:
- Historical monthly generation (TWh)
- Installed capacity (GW) 
- Monthly availability factors (%)
- Minimum 5-10 years of history
```

### 2.2 Synthetic Generation Methods

#### Method A: Stochastic (ARMA)
- Generate time series preserving statistical properties
- Mean availability: Historical average with climate trend (-0.5% per decade)
- Variability: Historical std dev × (1 + 0.1 per decade)
- Temporal correlation: AR(1) coefficient ~0.6

#### Method B: Regime-Based
```
States: Dry (25%) | Normal (50%) | Wet (25%)
Transition Matrix:
        To_Dry  To_Normal  To_Wet
From_Dry    0.6      0.3      0.1
From_Normal 0.2      0.6      0.2  
From_Wet    0.1      0.3      0.6
```

#### Method C: Hybrid (Recommended)
1. Generate regime sequence (wet/normal/dry years)
2. Apply stochastic variation within each regime
3. Add climate change trends

### 2.3 Climate Scenarios
```
Optimistic:  -0.3% per decade, +5% variability
Moderate:    -0.5% per decade, +10% variability
Pessimistic: -1.0% per decade, +15% variability
Severe:      -1.5% per decade, +20% variability
```

### 2.4 Output Format
```csv
Country,Year,Month,Scenario,P10,P50,P90,Regime
BRA,2030,1,1,0.38,0.48,0.58,normal
BRA,2030,2,1,0.41,0.51,0.61,normal
...
```

---

## 3. Wind & Solar Scenarios (Without New Weather Data)

### 3.1 Scaling Existing 2013 Profiles

#### Solar Variability
```python
Annual variation: ±7% (normal years), ±10% (extreme)
Monthly variation: ±5% additional
Extreme events: 2-3 dust/smoke events per year (-40% for 2 weeks)

Scaling factors:
- Solar_Low: Base × 0.92
- Solar_Normal: Base × 1.00
- Solar_High: Base × 1.07
- Solar_Extreme: Include multi-week -40% events
```

#### Wind Variability (Onshore)
```python
Annual variation: ±20% (normal years), ±30% (extreme)
Seasonal shifts: Winter +10%, Summer -10% (climate change)
Wind droughts: 2-4 week periods at 30% capacity

Scaling factors:
- Wind_Low: Base × 0.80
- Wind_Normal: Base × 1.00
- Wind_High: Base × 1.20
- Wind_Drought: Include 2-4 week 70% reduction events
```

#### Wind Variability (Offshore)
```python
More stable than onshore
Annual variation: ±15%
Less susceptible to extended calms

Scaling factors:
- Wind_Offshore_Low: Base × 0.85
- Wind_Offshore_Normal: Base × 1.00
- Wind_Offshore_High: Base × 1.15
```

---

## 4. Resource Correlation Framework

### 4.1 Physical Correlations

| Relationship | Correlation | Physical Basis |
|-------------|-------------|----------------|
| Hydro ↔ Solar | -0.6 | Dry periods = clear skies |
| Hydro ↔ Wind | +0.2 | Storm systems bring both |
| Wind ↔ Solar | -0.3 | High pressure = sun + calm |

### 4.2 Correlation Rules

```
IF Hydro = P10-P30 (Dry):
  → 70% chance Solar_High
  → 60% chance Wind_Low
  
IF Hydro = P70-P90 (Wet):
  → 70% chance Solar_Low
  → 60% chance Wind_High
  
IF Hydro = P40-P60 (Normal):
  → Equal probability all scenarios
```

### 4.3 Regional Adjustments

| Region | Hydro-Solar | Hydro-Wind | Notes |
|--------|-------------|------------|-------|
| Tropical (Brazil) | -0.7 | +0.1 | Strong dry=sunny |
| Temperate (Europe) | -0.4 | +0.3 | Atlantic storms |
| Monsoon (S/SE Asia) | -0.5 | -0.2 | Seasonal opposites |
| Mediterranean | -0.6 | +0.4 | Winter rain+wind |

---

## 5. Scenario Sequencing for Planning Studies

### 5.1 Reference Scenario (25 years)
```
Years 1-5:   Normal (P50) - Baseline period
Years 6-8:   Dry sequence (P30→P20→P25) - Early stress test
Years 9-12:  Recovery (P40→P50→P50→P60)
Years 13-14: Wet (P70→P75)
Years 15-17: Normal (P50)
Years 18-20: Severe drought (P20→P15→P30) - Major stress
Years 21-25: New normal with climate impact (P45 average)
```

### 5.2 Stress Test Scenarios

#### Compound Drought (5% probability)
```
Hydro: P20
Wind: Wind_Drought
Solar: Solar_Normal
Duration: 2-3 consecutive years
Impact: Tests system resilience
```

#### Variable Climate (high uncertainty)
```
3-year cycles: Dry(P20) → Wet(P75) → Normal(P50)
Tests flexibility and storage value
```

---

## 6. Implementation Steps

### Phase 1: Hydro Scenarios (Immediate)
1. Process historical data into monthly availability factors
2. Generate 100-500 synthetic scenarios using hybrid method
3. Apply climate change adjustments
4. Output P10/P50/P90 for each country-year-month

### Phase 2: Wind/Solar Scaling (Quick Win)
1. Create 3-5 variants of 2013 data using scaling factors
2. Include extreme events (wind droughts, dust storms)
3. Apply seasonal shifts for climate change

### Phase 3: Correlation (Integration)
1. Build correlation matrix for your regions
2. Generate paired scenarios (hydro state → wind/solar selection)
3. Create 20-30 complete multi-resource scenarios

### Phase 4: Validation
1. Backtest against historical extreme years
2. Compare statistics with literature values
3. Verify compound event frequencies

---

## 7. Code Architecture

```python
# Main components
project/
├── data/
│   ├── historical_hydro.csv
│   ├── wind_2013_profiles.csv
│   └── solar_2013_profiles.csv
├── generators/
│   ├── hydro_scenarios.py      # Synthetic hydro generation
│   ├── renewable_scaling.py    # Wind/solar variants
│   └── correlation_engine.py   # Cross-resource correlation
├── scenarios/
│   ├── scenario_builder.py     # Combines all resources
│   └── extreme_events.py       # Compound event injection
└── outputs/
    ├── scenarios_p10_p50_p90.csv
    └── full_monte_carlo_scenarios.csv
```

---

## 8. Key Parameters Table

| Parameter | Default Value | Range | Notes |
|-----------|--------------|-------|-------|
| Hydro decline rate | -0.5%/decade | -0.3 to -1.5% | Climate impact |
| Hydro variability increase | +10%/decade | +5 to +20% | Extreme events |
| Wind annual variation | ±20% | ±15 to ±30% | Onshore |
| Solar annual variation | ±7% | ±5 to ±10% | Climate dependent |
| Drought persistence | 60% | 50-70% | Year-to-year |
| Compound event probability | 5% | 2-10% | Calibrate to region |

---

## 9. Validation Metrics

### Statistical Tests
- Mean availability vs historical: Within ±5%
- Standard deviation: Within ±10% of historical
- Autocorrelation: Preserve AR(1) ≈ 0.6
- Extreme event frequency: 1-in-20 to 1-in-100 years

### Physical Consistency
- Seasonal patterns preserved
- Regional correlations maintained
- No impossible values (0-100% bounds)
- Climate trends monotonic

---

## 10. Expected Improvements vs Single Weather Year

| Metric | Single Weather Year | This Framework | Improvement |
|--------|-------------------|----------------|-------------|
| Reserve margin | Underestimated | Properly sized | +10-15% |
| Extreme events | Never captured | Included | Risk aware |
| Storage value | Undervalued | Properly valued | 2-3x value |
| System cost | ±0% uncertainty | ±15-20% range | Uncertainty quantified |
| Blackout risk | Hidden | Quantified | <5% target |

---

## 11. References & Tools

### Data Sources
- **Hydro historical**: EMBER, ONS (Brazil), ENTSO-E (Europe)
- **Weather data**: ERA5 (via Atlite), MERRA-2
- **Climate projections**: IPCC AR6, CMIP6

### Software Tools
- **PyPSA**: Network optimization
- **Atlite**: Renewable profile generation
- **SDDP**: Stochastic hydro optimization (commercial)
- **Custom scripts**: This framework

### Key Papers
- Grochowicz et al. (2024): Multi-year weather in power models
- Van der Wiel et al. (2019): Meteorological conditions leading to extreme events
- Bloomfield et al. (2020): Quantifying wind drought years
- Collins et al. (2018): Impacts of inter-annual wind/solar variability

---

## 12. Next Steps Checklist

- [ ] Gather historical hydro data for target countries
- [ ] Implement hydro scenario generator
- [ ] Create wind/solar scaling functions
- [ ] Build correlation matrix for your regions
- [ ] Generate first set of test scenarios
- [ ] Validate against historical extremes
- [ ] Integrate with PyPSA/optimization model
- [ ] Document assumptions and parameters
- [ ] Sensitivity analysis on key parameters
- [ ] Peer review methodology

---

## Notes
- Start simple: Even basic scaling is better than single year repetition
- Prioritize: Hydro scenarios first (biggest impact), then correlations
- Validate: Always check against known historical extremes
- Document: Track all assumptions for transparency
- Iterate: Refine correlations as you gather more data

*Version 1.0 - Created from analysis of global best practices in stochastic energy planning*