# Enhanced Calendar Visualization with Coverage Heatmap

## Overview
Transform the existing timeslice calendar from a simple "selected days" display into a comprehensive renewable energy stress heatmap with algorithm selections overlaid.

## Current State
- Calendar shows selected critical periods with basic category colors
- Generated from `segment_summary_CHE.csv` data
- Shows which days/weeks were chosen but no context about the full year

## Proposed Enhancement
Replace basic calendar with a **coverage heatmap** that shows:
1. **Full year context**: All 365 days colored by renewable energy coverage (shortage/surplus)
2. **Selection overlay**: Algorithm-chosen periods highlighted on top of the heatmap
3. **Continuous color scale**: Red (shortage) → Neutral → Green (surplus)

## Visual Concept
- **Background**: Each calendar day colored by daily average coverage percentage
  - <100% = Red scale (shortage severity)
  - ~100% = Neutral color (balanced)
  - >100% = Green scale (surplus intensity)
- **Overlay**: Selected days marked with borders/symbols/labels
  - "S1", "S2" for scarcity days
  - "P1", "P2" for surplus days  
  - "V1", "V2" for volatile days
  - Week selections shown as connected regions

## Data Requirements

### New Data Output from Stress Analyzer
Create `daily_coverage_CHE.json` with structure:
```json
{
  "iso": "CHE",
  "weather_year": 2013,
  "daily_coverage": [156.2, 142.8, 89.4, 234.1, ...]
}
```
- Simple array of 365 daily average coverage values
- Chronological order (Jan 1 to Dec 31)
- Values represent renewable supply vs demand ratio (%)

### Data Source in Analyzer
The stress period analyzer already calculates this data:
1. **Hourly coverage** for all 8760 hours (renewable supply vs demand)
2. **Daily aggregation** for ranking/selection algorithms
3. **Day ordering** used by triple_1, triple_5, weekly_stress selection

**Implementation point**: Capture the daily aggregated coverage data that's used for ranking and save it as JSON alongside existing outputs.

## Implementation Tasks

### 1. Modify Stress Period Analyzer
- Extract daily average coverage data (already calculated internally)
- Save as `daily_coverage_{ISO}.json` in output directory
- Add to existing save operations alongside CSV files

### 2. Update Calendar Visualizer
- Load daily coverage JSON data
- Implement continuous color scale mapping
- Overlay selection markers on heatmap background
- Maintain existing interactive features

### 3. Update README Integration
- Ensure enhanced calendar appears in VEDA model READMEs
- Update both SVG (GitHub) and HTML (interactive) versions

## Benefits
- **Full year insight**: See entire renewable energy landscape, not just selected days
- **Algorithm validation**: Visually verify selections make sense (scarcity days in red zones, surplus in green)
- **Pattern recognition**: Identify seasonal trends, weather patterns, systematic issues
- **Stakeholder communication**: Much more compelling visualization for presentations

## Technical Notes
- Data already exists in analyzer - just need to capture and export it
- JSON format for efficiency (internal consumption only)
- Maintains existing calendar functionality while adding rich context
- No performance impact - coverage calculation already happens

## Files to Modify
1. `2_ts_design/scripts/stress_period_analyzer.py` - add JSON export
2. `calendar_visualizer.py` - enhance with coverage heatmap
3. `veda_model_creator.py` - pass coverage data to calendar generator

## Expected Outcome
Transform calendar from simple selection indicator into comprehensive renewable energy stress visualization that provides both full-year context and algorithm validation in a single, intuitive view.
