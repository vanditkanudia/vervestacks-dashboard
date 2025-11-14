# FACETS Simulation Methodology: Breakthrough Session Summary

**Date**: November 8, 2025  
**Session Focus**: Complete transformation from basic validation to comprehensive multi-regional analysis framework  
**Status**: Production-ready with professional outputs

---

## 🎯 Core Breakthrough: From Visual Indicators to System Simulation

### Initial Request vs. Final Achievement
- **Started with**: Adding FACETS timeslice boundaries to existing charts
- **Evolved into**: Universal multi-regional energy system simulation framework
- **Key insight**: Timeslice indicators revealed deeper planning biases that required comprehensive analysis

---

## 🌐 Multi-Regional Simulation Philosophy

### Universal Transmission Group Methodology
The breakthrough was developing a **universal methodology** that works for all 18 transmission groups identified in the FACETS data:

#### Core Principle: "Copper Plate" Aggregation
- **Demand**: Sum hourly demand across all regions within transmission group
- **Generation**: Aggregate timeslice-level generation across regions
- **Storage**: Pool all storage capacity and simulate at group level
- **Dispatch**: Pool all dispatchable generation for realistic allocation

#### Regional Diversity Preservation
**Critical insight**: Initial averaging of capacity factors across regions was **too optimistic** and lost regional diversity. The breakthrough solution:

1. **Load timeslice generation BY REGION** (not aggregated)
2. **Load capacity factors BY REGION** (preserve local weather patterns)
3. **Distribute each region's generation using its OWN regional CFs**
4. **Sum resulting hourly profiles** to get transmission group total

This preserves regional weather diversity while enabling system-wide analysis.

### Edge Case Handling: The CF Weight Threshold
**Problem discovered**: When total CF weight for a timeslice was very small (but non-zero), it created massive multipliers leading to unrealistic generation spikes.

**Solution**: Threshold logic at 0.001
- If `total_cf_weight > 0.001`: Use proportional distribution
- If `0 < total_cf_weight ≤ 0.001`: Use equal distribution across timeslice hours
- This prevents near-division-by-zero scenarios while maintaining energy conservation

---

## ⚡ Operational Simulation Philosophy

### Two Simulation Approaches (Simplified to One)
Initially developed two approaches:
1. **Phase 5a (FACETS As-Planned)**: Respects timeslice boundaries for dispatch
2. **Phase 5b (Operationally Realistic)**: Pools dispatch across timeslices

**Key decision**: Streamlined to focus on **Operationally Realistic** approach as it better represents actual grid operations and reveals planning inadequacies.

### Pooled Dispatch Logic
**Core insight**: Real grids don't respect model timeslice boundaries when dispatching resources.

**Implementation**:
- Pool ALL dispatchable generation across ALL timeslices
- Pool ALL storage capacity across regions
- Allocate based on actual hourly shortage, ignoring timeslice constraints
- This reveals whether the planned capacity mix can actually meet demand operationally

### Storage Operation Philosophy
**Charging Strategy**: 
- Charge during surplus periods OR low demand periods (below high demand threshold)
- High demand threshold = demand at 90th percentile

**Discharging Strategy**:
- Discharge during shortage periods OR high demand periods
- Prioritize shortage mitigation over peak shaving

**Efficiency**: 71.9% round-trip efficiency (industry standard)

---

## 📊 Data Handling Breakthrough: The Demand Year Fix

### Critical Bug Discovery
**Issue**: Initial analysis showed generation 2x higher than demand  
**Root cause**: Extracting 2010 demand data instead of 2045 demand data from HDF5 files  
**Solution**: Correct indexing by both model year (2045) and weather year (2007)

**HDF5 Structure Understanding**:
- `index_0`: Model year data (2045)
- `index_1`: Weather year for that model year (2007 for renewable profiles)
- Must extract both correctly for valid analysis

### Region Name Format Handling
**Discovery**: Inconsistent region naming between datasets
- FACETS data: `p060`, `p061`, etc.
- Demand data: `p60`, `p61`, etc.
- **Solution**: Automatic conversion function `_convert_facets_to_demand_format()`

---

## 🎨 Visualization Philosophy

### Surplus vs. Shortage Representation
**Key insight**: Surplus and shortage are mutually exclusive and must be visualized correctly.

**Shortage**: Gray diagonal hatching - gap between supply and demand  
**Surplus**: Green diagonal hatching - excess above demand + storage charging  
**Critical rule**: `surplus = 0` when `shortage > 0`

### FACETS Timeslice Indicators
**Purpose**: Visually show how timeslice boundaries influence generation patterns
**Implementation**: 
- Vertical lines at timeslice boundaries
- Labels spread across timeslice duration (not clustered)
- Season-aware labeling based on hour index
- Hour-of-day markers (1-24) for precise positioning

**Visual insight**: Clearly shows how generation is artificially constrained by model timeslices vs. actual renewable availability.

---

## 📋 Professional Output Standards

### VerveStacks Branding Integration
**Decision**: All outputs must meet professional standards with consistent branding
- **Branding text**: "VERVESTACKS - the open USE platform · Powered by data · Shaped by intuition · Accelerated with AI"
- **Colors**: Deep blue branding (#19375F), steel blue headers (#4F81BD)
- **Typography**: Segoe UI with size hierarchy

### Energy Units Standardization
**Key decision**: Use industry-standard large units for clarity
- **Capacity**: GW (not MW)
- **Energy**: TWh (not GWh) 
- **Power**: GW for large systems, MW for components

### Smart Number Formatting Philosophy
**Principle**: Formatting should match human comprehension patterns
- **Large numbers (≥100)**: No decimals (e.g., 780 TWh)
- **Medium numbers (10-99)**: 1 decimal (e.g., 62.5 GW)
- **Small numbers (<10)**: 2 decimals (e.g., 7.86 TWh)
- **Special handling**: Percentages, hours, cycles follow same logic

---

## 🗂️ File Organization Philosophy

### Scenario-Based Structure
**Insight**: Energy modeling involves comparing many scenarios
**Solution**: Organize by scenario first, then by system
```
outputs/
├── plots/
│   └── <scenario>/
│       ├── simulation_shortage_weeks_<system>.png
│       └── simulation_surplus_weeks_<system>.png
└── metrics/
    └── <scenario>/
        └── simulation_metrics_<system>.xlsx
```

### Simplified Naming Convention
**Old**: `phase_5b_operationally_realistic_shortage_weeks_ERCOT.png`  
**New**: `simulation_shortage_weeks_ERCOT.png`  
**Philosophy**: Descriptive but concise, emphasizing content over process

---

## 🔧 Technical Architecture Insights

### Backward Compatibility Design
**Requirement**: Tool must work for both single regions and transmission groups seamlessly
**Solution**: Constructor accepts either `region='p063'` or `transmission_group='ERCOT'`
**Implementation**: Internal logic automatically handles region vs. group analysis

### Error Handling Philosophy
**Principle**: Graceful degradation with meaningful feedback
- Excel formatting fails → Fall back to CSV
- ExcelManager unavailable → Fall back to CSV
- Data missing → Clear error messages, continue where possible

### Robust Fallback Strategy
**Excel Operations**: 
1. Try professional Excel with branding
2. If xlwings/ExcelManager fails → CSV with warning
3. If pandas fails → Print error, continue analysis

---

## 🧠 Methodological Insights

### Simulation vs. Verification
**Clarity emerged**: This is **simulation** (operational hour-by-hour modeling) not **verification** (does the code work correctly?)

**Simulation questions answered**:
- Can the planned capacity mix actually meet demand hour-by-hour?
- How do timeslice constraints distort operational reality?
- What are the true shortage/surplus patterns?
- How does aggregation affect system adequacy assessment?

### Planning Bias Revelation
**Key insight**: FACETS timeslice constraints create artificial dispatch patterns that may not reflect operational reality
**Evidence**: Significant differences between timeslice-constrained and pooled dispatch
**Implication**: Planners need to understand these biases when interpreting model results

### Scale Effects Discovery
**Single region** (p063): 48.4 TWh shortage, 85.4% renewable penetration  
**Transmission group** (ERCOT): 7.9 TWh shortage, 77.4% renewable penetration  
**Insight**: Regional aggregation can mask or reveal different adequacy challenges

---

## 🎯 Future Applications

### Universal Applicability
This methodology now works for:
- All 18 transmission groups in North America
- Any individual region within those groups  
- Any scenario generated by FACETS/VEDA models
- Any year with compatible data structure

### Scaling Considerations
**Memory optimization**: HDF5 chunked reading for large datasets  
**Performance**: Parallel processing potential for multiple scenarios  
**Storage**: Scenario-based organization prevents file conflicts

---

## 📈 Success Metrics

### Technical Achievements
- ✅ Universal multi-regional capability
- ✅ Professional Excel outputs with branding
- ✅ Robust error handling and fallbacks
- ✅ Smart energy unit formatting
- ✅ Clean file organization
- ✅ Backward compatibility maintained

### Methodological Breakthroughs
- ✅ Regional diversity preservation in aggregation
- ✅ Operational realism in dispatch simulation
- ✅ Timeslice bias visualization
- ✅ Surplus/shortage mutual exclusivity
- ✅ Edge case handling (CF weights)

### User Experience Improvements
- ✅ One command for complete analysis
- ✅ Professional publication-ready outputs
- ✅ Clear progress indicators and logging
- ✅ Intuitive file naming and organization
- ✅ Comprehensive metrics reporting

---

## 🚀 Impact and Vision

This breakthrough transforms FACETS simulation from a manual, single-region process into an automated, universal framework that can simulate any energy system model configuration operationally. The methodology preserves the rigor of detailed engineering analysis while providing the clarity and professionalism needed for policy and investment decisions.

**The framework now embodies VerveStacks' vision**: Democratizing energy modeling by making sophisticated operational simulation accessible, automated, and professionally presented.

---

*This document captures the conceptual foundations and methodological insights that emerged during the breakthrough session. The actual implementation details are preserved in the code, but the philosophical and strategic decisions documented here provide the context for future development and application.*
