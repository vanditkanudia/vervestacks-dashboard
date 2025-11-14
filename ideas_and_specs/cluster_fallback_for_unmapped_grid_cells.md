# Cluster Fallback for Unmapped Grid Cells

## Context

**Date**: January 2025  
**Issue**: Existing solar/wind plants in some grid cells couldn't pick up cluster_id assignments, preventing them from producing commodities with resource shapes.

## Problem

In synthetic grid cases (and potentially other grid types), some REZoning grid cells exist in the source data but are not included in the renewable clustering output. This causes plants in those grid cells to fail cluster_id assignment.

**Example from IND synthetic grid (syn_5)**:
- REZoning has **1489 solar grid cells** for India
- Clustering output has only **1431 mapped grid cells**
- Missing cells correspond to **island regions** (Andaman & Nicobar, Lakshadweep)
- Result: **12 solar plants** couldn't get cluster assignments

## Root Cause

Grid cells may be excluded from clustering for various reasons:
- Low resource quality below clustering thresholds
- Remote/island locations with connectivity constraints
- Insufficient data quality in certain regions
- Strategic clustering that focuses on mainland areas

## Solution: Nearest Cluster Fallback

Implemented in `existing_stock_processor.py::assign_single_commodity()` (lines 1374-1435)

### Logic Flow

1. **Primary Assignment**: Try to map `grid_cell → cluster_id` from clustering output files
2. **Fallback Detection**: Identify plants with `grid_cell` but no `cluster_id`
3. **Coordinate Lookup**: Get lat/lon for unmapped grid_cells from REZoning data
4. **Distance Calculation**: Compute distance to all cluster centroids
5. **Nearest Assignment**: Assign plant to the closest cluster

### Implementation Details

**Data Sources**:
- `cluster_summary_{technology}.csv` - provides cluster centroids (centroid_lat, centroid_lon)
- REZoning data - provides grid_cell coordinates (x, y)
- Uses scipy's cdist for efficient distance calculation

**Technologies Covered**:
- Solar (spv)
- Wind Onshore (won)  
- Wind Offshore (wof)

**Output**:
```
   🔍 Using nearest cluster fallback for 12 solar plants
      - IND_1470 → cluster 23 (distance: 0.1234 degrees)
      - IND_1497 → cluster 45 (distance: 0.5678 degrees)
      ...
```

## Benefits

1. **No Data Loss**: All plants get valid cluster assignments
2. **Reasonable Approximation**: Nearby clusters have similar resource characteristics
3. **Graceful Degradation**: System handles incomplete clustering without crashing
4. **Transparent**: Logs which plants use fallback logic

## Trade-offs

**Pros**:
- Simple, robust solution
- Minimal code changes
- Works for all grid types
- Preserves all plant capacity data

**Cons**:
- Plants may be assigned to clusters with slightly different resource profiles
- Island plants might be assigned to mainland clusters (could have transmission implications)
- Distance is calculated in degrees (not geodesic), which is less accurate for large distances

## Alternative Approaches Considered

**Option 1**: Fix clustering to include all grid cells
- More comprehensive but requires changes to clustering algorithm
- May introduce very small/low-quality clusters
- Could be pursued as a longer-term improvement

**Option 3**: Filter out unmappable plants
- Loses valuable capacity data
- Not acceptable for energy modeling accuracy

## Future Improvements

1. **Distance Metric**: Use geodesic distance (haversine) instead of Euclidean for better accuracy
2. **Island Detection**: Flag island/remote assignments for special handling
3. **Clustering Enhancement**: Ensure all REZoning cells are included in future clustering runs
4. **Quality Checks**: Add validation to compare assigned cluster CF vs original grid_cell CF

---

**Status**: ✅ Implemented and tested with IND synthetic grid case

