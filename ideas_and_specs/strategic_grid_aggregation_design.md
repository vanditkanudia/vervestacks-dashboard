# Strategic Grid Aggregation Design Specification

## Purpose & Context

**Date**: January 2025  
**Status**: Requirements Specification Phase  
**Objective**: Design strategic spatial aggregation for energy transition stress modeling

## Problem Statement

Current grid modeling in VerveStacks produces too many nodes for strategic energy transition analysis. We need **appropriate spatial aggregation** that captures:

1. **Fossil retirement stress** (where thermal plants are shutting down)
2. **Renewable integration stress** (where VRE is being added) 
3. **Broad transmission stress patterns** (inter-regional load balancing)

**This is NOT for transmission planning** - it's for representing the **spatial dynamics of the energy transition** in optimization models.

## Design Requirements

### Country Size Classification & Target Node Counts

**Large Countries (15 nodes max):**
- **Criteria**: >100 GW total installed capacity
- **Examples**: USA, CHN, RUS, IND, BRA, CAN, AUS
- **Rationale**: Need regional diversity in fossil retirement vs renewable buildup patterns

**Medium Countries (8-12 nodes):**
- **Criteria**: 25-100 GW total installed capacity  
- **Examples**: DEU, FRA, ITA, ESP, POL, JPN, GBR
- **Rationale**: Enough resolution for north/south or coastal/inland differences

**Small Countries (5-7 nodes):**
- **Criteria**: <25 GW total installed capacity
- **Examples**: CHE, AUT, BEL, NLD, PRT, GRC
- **Rationale**: Minimal nodes to capture basic geographic stress patterns

### Strategic Importance Weighting Algorithm

**Bus importance score calculation:**
```
bus_importance = (
    0.4 * existing_thermal_capacity_mw +     # Fossil retirement stress points
    0.3 * renewable_potential_nearby_gw +    # RE integration stress points  
    0.2 * transmission_capacity_mva +        # Grid backbone importance
    0.1 * voltage_level_weight              # System criticality (380kV=1.0, 220kV=0.7, etc.)
)
```

### Two-Stage Clustering Approach

**Stage 1: Transition-Aware Pre-Clustering**
- Weight buses by energy transition importance (fossil + renewable + transmission)
- Ensure important energy locations don't get merged inappropriately
- Preserve spatial separation of different energy functions

**Stage 2: Connectivity-Constrained Final Clustering**
- Apply target node count while preserving network connectivity
- Use transmission line data to prevent impossible topologies
- Ensure no isolated nodes after aggregation
- Maintain minimum spanning tree connectivity

### Critical Constraints

1. **Connectivity Preservation**: No isolated nodes or impossible topologies
2. **Energy Geography Awareness**: Clustering must reflect energy transition patterns
3. **Voltage Level Respect**: Higher voltage buses have aggregation priority
4. **Island/Isolation Handling**: Geographic barriers must be respected

## Data Availability Assessment (CHE Example)

### ✅ Available Data Sources

**Thermal Plant Locations:**
- GEM power plant database with bus assignments
- Plant capacities, fuel types, operational status
- Example: CHE has 10 oil/gas plants (31.3 MW each)

**Renewable Potential:**
- REZoning solar/wind data by 50x50km grid cells
- Capacity factors and potential capacity
- Example: CHE has 174 GW solar + 327 GW wind potential across 25-26 grid cells

**Transmission Infrastructure:**
- Line capacities (s_nom), impedances, lengths
- Bus voltage levels and connectivity
- Example: CHE transmission capacity ranges 492-14,345 MVA per bus

**Zone-Bus Mapping:**
- Links REZoning grid cells to network buses
- Enables renewable potential assignment to specific buses

### Data Integration Approach

1. **Merge power plant assignments with GEM database** → Get thermal capacity per bus
2. **Calculate renewable potential within X km of each bus** → Get integration stress
3. **Sum transmission line capacities per bus** → Get grid importance
4. **Apply voltage level weights** → Get system criticality

## Implementation Strategy

### Phase 1: Data Integration Module
- Create functions to calculate importance scores for all buses
- Implement distance-based renewable potential assignment
- Validate data quality and coverage

### Phase 2: Strategic Clustering Algorithm
- Implement transition-aware weighting
- Develop connectivity-constrained clustering
- Test on multiple country examples

### Phase 3: Validation & Tuning
- Verify clustering results capture energy geography correctly
- Adjust weighting factors based on real-world patterns
- Document algorithm parameters and sensitivities

## Success Criteria

1. **Appropriate Node Counts**: Countries clustered to target ranges (5-7, 8-12, 15)
2. **Energy Transition Relevance**: Clusters capture fossil retirement vs renewable integration patterns
3. **Network Connectivity**: No isolated nodes or impossible transmission topologies
4. **Computational Efficiency**: Algorithm runs efficiently for all 100+ countries
5. **Model Integration**: Clustered networks integrate seamlessly with VEDA model generation

## Edge Cases & Special Considerations

**Island Nations**: Each major island = separate cluster minimum
**Elongated Countries**: Linear distance penalty to prevent over-clustering  
**Isolated Grid Regions**: Preserve natural electrical boundaries
**Data Quality Variations**: Graceful degradation when data is incomplete

## Next Steps

1. **Finalize weighting parameters** through expert review
2. **Implement prototype algorithm** for testing
3. **Validate on diverse country sample** (large/medium/small)
4. **Integrate with existing grid modeling pipeline**
5. **Document final methodology** for production use

---

**Context Preservation Note**: This specification captures the strategic thinking behind grid aggregation before implementation begins. The goal is ensuring spatial modeling serves energy transition analysis rather than engineering detail.
