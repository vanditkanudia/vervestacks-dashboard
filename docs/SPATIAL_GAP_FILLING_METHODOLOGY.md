# Spatial Gap-Filling Methodology for Missing Capacity

## Overview

When VerveStacks reconciles statistical capacity data (IRENA/EMBER) with plant-level data (GEM), it often finds missing capacity that needs to be added to match national statistics. This methodology ensures that gap-filling capacity is spatially distributed based on resource quality and infrastructure capacity rather than being assigned to generic country-level commodities.

## Problem Statement

**Current Issue**: Gap-filling records are created without spatial attributes:
```python
new_row = pd.Series({
    'iso_code': input_iso,
    'model_fuel': fuel_type,
    'Capacity (MW)': capacity_difference_gw * 1000,
    'Plant / Project name': 'Aggregated Plant - IRENA Gap',
    # Missing: grid_cell, bus_id → Results in ISO-level commodities
})
```

**Impact**: These records get assigned country-level commodities (e.g., `elc_spv-CHE`) instead of spatially precise ones (e.g., `elc_spv-CHE_0042`), breaking the spatial intelligence of the model.

## Solution: Resource Quality Weighted Distribution

### Core Principle
Distribute gap-filling capacity proportionally based on **resource quality** and **infrastructure capacity** to maintain spatial realism while optimizing system performance.

### Methodology

#### 1. Solar/Wind Gap-Filling (REZ-based)
**Data Sources:**
- `df_solar_rezoning['Capacity Factor']` - Resource quality by grid cell
- `df_solar_rezoning['Installed Capacity Potential (MW)']` - Resource availability
- `df_wind_rezoning` - Equivalent data for wind

**Weighting Formula:**
```python
weight = 0.7 × normalized_capacity_factor + 0.3 × normalized_resource_potential
```

**Distribution Process:**
1. Calculate weights for all available REZ zones in the country
2. Normalize weights to sum to 1.0
3. Distribute gap-filling capacity proportionally
4. Assign appropriate `grid_cell` values to new records
5. Apply `rez_id_to_commodity()` for spatial commodities

#### 2. Conventional Gap-Filling (Bus-based)
**Data Sources:**
- `clustered_buses['voltage']` - Transmission capacity indicator (220kV, 225kV, 380kV)
- Existing capacity distribution by bus from GEM data

**Weighting Formula:**
```python
voltage_score = {380: 3, 225: 2, 220: 1}[voltage_kv]
weight = 0.7 × normalized_voltage_score + 0.3 × normalized_existing_capacity
```

**Distribution Process:**
1. Calculate weights for all buses with transmission capacity
2. Normalize weights to sum to 1.0
3. Distribute gap-filling capacity proportionally
4. Assign appropriate `bus_id` values to new records
5. Apply `bus_id_to_commodity()` for spatial commodities

### Implementation Strategy

#### Phase 1: Enhance Gap-Filling Functions
Modify `add_missing_irena_capacity()` and `add_missing_ember_capacity()` in `existing_stock_processor.py`:

```python
def distribute_gap_capacity_spatially(capacity_gw, fuel_type, iso_code, 
                                    zones_data=None, buses_data=None):
    """
    Distribute gap-filling capacity across spatial zones based on resource quality.
    
    Returns: List of records with spatial assignments
    """
```

#### Phase 2: Create Spatial Distribution Module
Add functions to `spatial_utils.py`:
- `calculate_rez_weights(solar_data, wind_data, fuel_type)`
- `calculate_bus_weights(buses_data, existing_capacity_data)`
- `distribute_capacity_by_weights(total_capacity, weights_dict)`

#### Phase 3: Integration
Update the main gap-filling workflow to call spatial distribution functions instead of creating single aggregated records.

## Expected Outcomes

### Model Improvements
1. **Spatial Consistency**: All capacity (existing + gap-filling) maintains spatial precision
2. **Resource Optimization**: Gap-filling capacity placed in high-quality resource zones
3. **Grid Realism**: Conventional capacity distributed based on transmission capacity
4. **Curtailment Accuracy**: Better representation of renewable integration constraints

### Data Quality
- **Before**: ~4.4 GW solar gap-filling → `elc_spv-CHE` (country-level)
- **After**: ~4.4 GW solar gap-filling → Multiple `elc_spv-CHE_00XX` (zone-level)

### Validation Metrics
- Sum of distributed capacity equals original gap amount
- Spatial distribution correlates with resource quality rankings
- No degradation in statistical reconciliation accuracy

## Technical Considerations

### Data Requirements
- REZoning capacity factor data (already available)
- Bus voltage level data (already available)
- Existing capacity distribution (already calculated)

### Performance Impact
- Minimal computational overhead
- One-time calculation per country per gap-filling run
- Results cached for model generation

### Fallback Strategy
If spatial data unavailable:
1. Fall back to equal distribution across available zones/buses
2. If no zones/buses available, create single ISO-level record (current behavior)
3. Log spatial distribution method used for transparency

---

*This methodology maintains VerveStacks' commitment to spatial precision while ensuring statistical accuracy and model performance optimization.*

