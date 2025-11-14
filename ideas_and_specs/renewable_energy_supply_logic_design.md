# Renewable Energy Supply Generation Logic - Design Documentation

## Overview

This document captures the background, rationale, and design decisions for the renewable energy supply generation logic implemented in the 8760-hour supply and demand constructor. The logic addresses the critical challenge of selecting realistic renewable energy portfolios that balance economic optimization with practical constraints.

## Problem Statement

### Initial Challenge: Technology Monopolization
The original implementation used pure LCOE (Levelized Cost of Energy) ranking across all renewable technologies, leading to unrealistic outcomes:

- **Germany**: Selected only wind (cheapest overall LCOE ~63.8 $/MWh), zero solar
- **Italy**: Would select only solar (cheapest overall LCOE ~78.1 $/MWh), zero wind
- **Result**: Technology monopolization that ignores real-world constraints

### Real-World Constraints Not Captured by Pure LCOE
1. **Grid Stability Requirements**: Need diverse generation profiles for system reliability
2. **Resource Complementarity**: Solar peaks during day, wind can generate at night
3. **Policy Preferences**: Countries have renewable energy portfolio standards
4. **Technical Limitations**: Transmission constraints, grid integration limits
5. **Risk Management**: Technology diversification reduces portfolio risk
6. **Supply Chain Constraints**: Cannot scale single technology infinitely

## Solution Approach: Balanced Relevant Resource Selection

### Core Principle: Economic Diversity
Instead of pure cost optimization, implement **economically-informed diversity** that:
- Respects economic competitiveness differences between technologies
- Prevents unrealistic technology monopolization
- Creates balanced portfolios while maintaining cost-effectiveness

### Key Innovation: "Relevant Resources" Concept
**Critical Design Decision**: Only evaluate resources that are actually relevant to the decision at hand.

**Definition**: "Relevant resources" are the cheapest grid cells within each technology up to the total residual demand requirement.

**Rationale**: 
- No point considering expensive tail-end resources that would never be selected
- Focuses evaluation on economically viable options
- Reflects real-world decision-making (countries don't evaluate infinite resources)
- Improves computational efficiency

## Algorithm Design

### Step 1: Identify Relevant Resources by Technology
For each technology (solar, wind onshore):
1. Sort grid cells by LCOE (cheapest first)
2. Accumulate generation potential until reaching total residual demand
3. These constitute the "relevant resources" for that technology

### Step 2: Calculate Technology Scores
**Scoring Formula**: `Score = (Relevant Potential in TWh) / (Weighted Average LCOE in $/MWh)`

**Interpretation**: TWh per $/MWh - measures cost-effectiveness of relevant resources

**Components**:
- **Relevant Potential**: Sum of generation from relevant grid cells only
- **Weighted Average LCOE**: Generation-weighted average cost of relevant cells
- **Higher Score**: Better cost-effectiveness (more generation per unit cost)

### Step 3: Proportional Allocation
Allocate residual demand proportionally based on technology scores:
```
Solar Target = Residual Demand × (Solar Score / Total Score)
Wind Target = Residual Demand × (Wind Score / Total Score)
```

### Step 4: Within-Technology Selection
For each technology, select the cheapest grid cells (by LCOE within technology) to meet the allocated target.

## Design Rationale

### Why Not Other Approaches?

#### Pure LCOE Ranking (Original)
- **Problem**: Technology monopolization
- **Example**: Germany selecting only wind, ignoring solar completely

#### Fixed 50/50 Split
- **Problem**: Ignores economic fundamentals
- **Example**: Would force equal solar/wind even if one is much more expensive

#### Minimum Share Constraints (e.g., 20% each)
- **Problem**: Arbitrary thresholds not based on economic reality
- **Complexity**: Requires country-specific calibration

#### Full Supply Curve Evaluation
- **Problem**: Computationally expensive and irrelevant
- **Rationale**: Why evaluate 1000 $/MWh resources that will never be selected?

### Why the Current Approach Works

1. **Economically Grounded**: Based on actual cost-effectiveness of viable resources
2. **Technology Neutral**: No arbitrary preferences, purely data-driven
3. **Scalable**: Works across different countries with different resource profiles
4. **Realistic**: Produces portfolios that align with real-world deployment patterns
5. **Efficient**: Only evaluates resources that matter for the decision

## Expected Outcomes by Country Type

### Wind-Favored Countries (e.g., Germany, Denmark)
- **Traditional Outcome**: 100% wind selection
- **New Outcome**: Wind-heavy but includes solar (e.g., 60-70% wind, 30-40% solar)
- **Rationale**: Wind gets higher allocation due to better cost-effectiveness, but solar prevents monopolization

### Solar-Favored Countries (e.g., Italy, Spain)
- **Traditional Outcome**: 100% solar selection  
- **New Outcome**: Solar-heavy but includes wind (e.g., 70-80% solar, 20-30% wind)
- **Rationale**: Solar dominates due to excellent resource, wind provides diversity

### Balanced Countries
- **Traditional Outcome**: Whatever technology has cheapest single grid cell
- **New Outcome**: More balanced mix reflecting relative competitiveness

## Implementation Details

### Technology Coverage
**Current**: Solar PV and Wind Onshore only
**Rationale**: 
- Wind offshore excluded for simplicity (limited deployment scale)
- Other technologies (hydro, nuclear) handled as baseline generation
- Focus on variable renewables that need balancing

### Grid Cell Data Consistency
**Critical Implementation Feature**: Pre-filtering for data alignment
**Problem Solved**: REZoning data contains more grid cells than weather shapes data
- **Example**: Germany has 189 wind cells in REZoning but only 177 cells with weather data
- **Solution**: Filter REZoning data to only include cells that exist in shapes dataset
- **Implementation**: Create unified list of available `grid_cell` from shapes data, filter both solar and wind REZoning tables
- **Result**: 100% matching success rate, zero failed grid cell lookups

**Benefits**:
- Eliminates matching failures completely  
- Ensures data integrity by only using cells with complete hourly profiles
- Improves performance by avoiding failed lookup attempts
- Future-proof approach that works for any ISO/country

### Fallback Behavior
**If one technology has no relevant resources**: Allocate all residual demand to the available technology
**If both technologies unavailable**: Graceful degradation (return empty selection)

### Data Quality Handling
- Uses `Generation Potential (GWh)` if available, converts to MWh
- Falls back to calculated generation from capacity and capacity factor
- Pre-filters grid cells to ensure weather data availability
- Handles missing data gracefully without crashing

## Validation and Testing

### Germany Results Validation
**Technology Balance**:
- **Before**: 0 solar + 36 wind cells (unrealistic monopolization)
- **After**: 36 solar + 18 wind cells (realistic diversified portfolio)

**Data Quality Improvement**:
- **Before**: 10 failed grid cell matches out of 62 (84% success rate)
- **After**: 54 out of 54 grid cells matched successfully (100% success rate)

**Score Calculation**: 
  - Solar: 540.5 TWh at 122.3 $/MWh → Score: 4.42
  - Wind: 542.8 TWh at 78.2 $/MWh → Score: 6.94
  - Allocation: 38% solar (210.1 TWh), 62% wind (330.0 TWh) - economically justified

**Coverage Performance**:
- **Before**: 96.8% demand coverage with data mismatches
- **After**: 101.2% demand coverage with perfect data alignment

### Cross-Country Consistency
Expected to produce different but economically logical portfolios for:
- **Germany**: Wind-heavy (good wind resources)
- **Italy**: Solar-heavy (excellent solar resources)
- **Denmark**: Balanced wind-dominated (excellent wind, limited solar)

## Future Enhancements

### Potential Improvements
1. **Seasonal Complementarity**: Weight based on generation profile correlation
2. **Grid Integration Limits**: Maximum percentage constraints per technology
3. **Policy Overlays**: Country-specific renewable energy targets
4. **Storage Integration**: Consider storage costs in technology comparison
5. **Transmission Costs**: Include grid connection costs in LCOE calculations

### Extension to Other Technologies
- **Wind Offshore**: Could be re-enabled with proper data validation
- **Hybrid Technologies**: Solar + storage, wind + storage combinations
- **Emerging Technologies**: Floating solar, agrivoltaics, etc.

## Key Design Principles

1. **Data-Driven**: No arbitrary assumptions or preferences
2. **Economically Informed**: Based on actual cost-effectiveness
3. **Practically Realistic**: Produces implementable portfolios
4. **Computationally Efficient**: Only processes relevant resources
5. **Transparent**: Clear scoring and allocation logic
6. **Extensible**: Framework supports additional technologies and constraints

## Conclusion

The balanced relevant resource selection approach represents a significant improvement over pure LCOE optimization by:
- Maintaining economic rationality while ensuring technology diversity
- Producing realistic renewable energy portfolios
- Providing transparent, data-driven allocation logic
- Supporting strategic energy planning and policy analysis

This approach enables VerveStacks to generate credible renewable energy scenarios that can inform real-world decision-making while maintaining computational efficiency and technical rigor.

---

*This document captures design decisions and rationale that cannot be inferred from code alone. For implementation details, refer to the `select_renewable_grid_cells()` method and related functions in `8760_supply_demand_constructor.py`.*

