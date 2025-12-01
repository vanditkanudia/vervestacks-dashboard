# Generation Profile Page - Features & Controls Guide

## Overview

The Generation Profile Page is an interactive dashboard for visualizing and simulating hourly electricity generation profiles for renewable energy sources (Solar and Wind) and comparing them against total electricity demand. The page provides real-time capacity-driven profile generation, interactive charts, and geographical visualization of renewable energy zones.

---

## Page Layout

The page is divided into two main sections:

### Left Sidebar (3 columns)
- **Parameters**: Year selection
- **Capacity Inputs**: Solar and Wind capacity input fields with "Go" buttons
- **Generation Summary**: Average and peak generation values for Solar and Wind

### Main Content Area (9 columns)
- **Timeline Chart**: Combined view of Demand, Solar, and Wind generation
- **Solar Profile Chart**: Individual solar generation profile
- **Wind Profile Chart**: Individual wind generation profile
- **Simulator Maps**: Two side-by-side maps showing utilization factors for selected renewable energy zones

---

## Features

### 1. Auto-Loading Data

**Behavior:**
- When a country is selected or the year changes, the page automatically:
  1. Fetches capacity data for Solar and Wind
  2. Generates hourly profiles using the fetched capacity
  3. Loads the main Timeline chart
  4. Fetches GeoJSON zone data for maps

**What You See:**
- Loading indicators appear while data is being fetched
- Charts and maps update automatically when data arrives
- Error messages display if data is unavailable

---

### 2. Timeline Chart

**Purpose:** Compare total demand against combined renewable generation (Solar + Wind)

**Visualization:**
- **Demand**: Purple/indigo line showing total electricity demand
- **Solar Generation**: Yellow stacked bars
- **Wind Generation**: Green stacked bars (stacked on top of Solar)
- **Gap Visualization**: The space between the stacked bars and the demand line shows:
  - **Gap (Red)**: When demand exceeds renewable generation (additional capacity needed)
  - **Surplus (Green)**: When renewable generation exceeds demand

**Controls:**
- **Zoom Buttons**: 1M, 3M, 6M, 1Y, All - Change the time range view
- **Navigator**: Bottom timeline for quick navigation
- **Scrollbar**: Horizontal scroll for precise time selection
- **Reload Button** (🔄): Regenerates the timeline chart with current parameters
- **Data Grouping Toggle**: Switch between two modes:
  - **Grouping Disabled** (OFF): Shows all 8,760 hourly data points - most accurate
  - **Avg Aggregation** (ON): Groups data for better performance when viewing long time ranges
    - Bars use `sum` aggregation (adds Solar + Wind when grouped)
    - Line uses `average` aggregation (averages Demand when grouped)

**Tooltip:**
- Hover over any point to see:
  - Date and time
  - Demand value (GW)
  - Solar generation (GW)
  - Wind generation (GW)
  - Gap/Surplus calculation (GW)

---

### 3. Solar Profile Chart

**Purpose:** View detailed hourly solar generation profile

**Visualization:**
- Line chart showing solar generation in GW
- X-axis: Time (month names only, no year)
- Y-axis: Generation (GW)
- Chart title shows current capacity (e.g., "Solar Generation — 24.56 GW")

**Controls:**
- **Reload Button** (🔄): Regenerates solar profile using current capacity
- **Input Field**: Enter custom solar capacity in GW
- **Go Button**: Generate new profile with custom capacity
- **Enter Key**: Press Enter in the input field to trigger "Go" action

**Behavior:**
- Input field is pre-populated with current capacity from API
- Changing capacity updates both the chart and the simulator map
- Chart shows 8,760 hourly values (one year)

---

### 4. Wind Profile Chart

**Purpose:** View detailed hourly wind (onshore) generation profile

**Visualization:**
- Line chart showing wind generation in GW
- X-axis: Time (month names only, no year)
- Y-axis: Generation (GW)
- Chart title shows current capacity (e.g., "Wind Generation — 12.34 GW")

**Controls:**
- **Reload Button** (🔄): Regenerates wind profile using current capacity
- **Input Field**: Enter custom wind capacity in GW
- **Go Button**: Generate new profile with custom capacity
- **Enter Key**: Press Enter in the input field to trigger "Go" action

**Behavior:**
- Input field is pre-populated with current capacity from API
- Changing capacity updates both the chart and the simulator map
- Chart shows 8,760 hourly values (one year)

---

### 5. Simulator Maps

**Purpose:** Visualize which renewable energy zones (grid cells) are selected and their utilization factors

**Two Maps:**
1. **Solar Simulator Map**: Shows selected solar grid cells
2. **Wind Simulator Map**: Shows selected wind grid cells

**Visualization:**
- **Color Coding**: Cells are colored by utilization factor:
  - **Red**: Low utilization (0.0 - 0.5)
  - **Amber**: Medium utilization (0.5 - 1.0)
  - **Green**: High utilization (1.0)
  - **Light Gray**: Unmatched cells (not selected for generation)
- **Tooltip**: Hover over any cell to see:
  - Cell ID
  - Utilization ratio/factor
  - Capacity (MW)

**Behavior:**
- Maps update automatically when:
  - Solar/Wind "Go" button is clicked
  - Solar/Wind "Reload" button is clicked
  - Country or year changes
- Maps show loading overlay while data is being fetched
- Maps automatically zoom to fit the selected cells

---

## Controls Reference

### Left Sidebar Controls

#### Parameters Section
- **Year Dropdown**: Select year (currently disabled, defaults to 2022)
  - Range: 2000-2022
  - Auto-loads data when changed

#### Capacity Inputs Section
- **Solar Capacity Input**:
  - Type: Number input field
  - Placeholder: "Enter capacity"
  - Units: GW
  - Min: 0.1
  - Step: 0.1
  - Pre-populated with API capacity
  - **Go Button**: Generates new profile with entered capacity
  - **Enter Key**: Same as clicking "Go"

- **Wind Capacity Input**:
  - Type: Number input field
  - Placeholder: "Enter capacity"
  - Units: GW
  - Min: 0.1
  - Step: 0.1
  - Pre-populated with API capacity
  - **Go Button**: Generates new profile with entered capacity
  - **Enter Key**: Same as clicking "Go"

#### Generation Summary Section
- **Solar Avg**: Average solar generation (GW) across the year
- **Solar Peak**: Peak solar generation (GW) in the year
- **Wind Avg**: Average wind generation (GW) across the year
- **Wind Peak**: Peak wind generation (GW) in the year

### Chart Controls

#### Timeline Chart
- **Data Grouping Toggle**: Switch between detailed and aggregated views
- **Reload Button** (🔄): Regenerate timeline chart
- **Zoom Buttons**: 1M, 3M, 6M, 1Y, All
- **Navigator**: Drag to navigate through time
- **Scrollbar**: Scroll horizontally through data
- **Legend**: Click to show/hide series

#### Solar/Wind Profile Charts
- **Reload Button** (🔄): Regenerate profile with current capacity
- **Input + Go**: Change capacity and regenerate

---

## Data Flow

### Initial Load Sequence
1. User selects country (from Country Dashboard)
2. Page automatically fetches:
   - Capacity data (`/api/capacity/capacity-by-fuel`)
   - Solar hourly profile (`/api/generation-profile/solar-hourly`)
   - Wind hourly profile (`/api/generation-profile/wind-hourly`)
   - Timeline chart data (`/api/generation-profile`)
   - Solar GeoJSON zones (`/api/renewable-potential/solar`)
   - Wind GeoJSON zones (`/api/renewable-potential/wind`)

### Manual Updates
- **Solar "Go"**: Fetches new solar profile → Updates chart + map
- **Wind "Go"**: Fetches new wind profile → Updates chart + map
- **Solar/Wind "Reload"**: Re-fetches profile with current capacity → Updates chart + map
- **Timeline "Reload"**: Re-fetches timeline data → Updates timeline chart

---

## Understanding the Visualizations

### Timeline Chart Interpretation

**When Demand Line is Above Stacked Bars:**
- Demand exceeds renewable generation
- Gap shown in tooltip (red)
- Additional generation capacity needed from other sources

**When Stacked Bars Reach or Exceed Demand Line:**
- Renewable generation meets or exceeds demand
- Surplus shown in tooltip (green)
- Excess energy available (could be stored or exported)

**Patterns to Look For:**
- **Daily Patterns**: Solar peaks during midday, zero at night
- **Seasonal Patterns**: Solar varies by season, wind may be more consistent
- **Peak Demand Times**: Usually morning and evening (when demand line peaks)

### Simulator Maps Interpretation

**High Utilization (Green):**
- Grid cells with high capacity factors
- These cells are prioritized in merit-order selection
- Most efficient renewable energy zones

**Medium Utilization (Amber):**
- Grid cells with moderate capacity factors
- Used when higher-capacity cells are insufficient

**Low Utilization (Red):**
- Grid cells with lower capacity factors
- Used only when more capacity is needed
- Less efficient but still viable

**Unmatched Cells (Light Gray):**
- Grid cells not selected for generation
- Either insufficient capacity factor or not needed for target capacity

---

## Tips & Best Practices

1. **Start with Auto-Loaded Data**: The page automatically loads data when you select a country. Review this before making changes.

2. **Use Data Grouping Toggle**: 
   - Turn OFF for detailed hourly analysis
   - Turn ON for overview of long time periods (better performance)

3. **Compare Scenarios**: 
   - Use capacity inputs to test different renewable capacity scenarios
   - Compare how gap/surplus changes with different capacity levels

4. **Zoom for Details**: 
   - Use zoom buttons to focus on specific time periods
   - Daily/weekly views show detailed patterns

5. **Check Maps**: 
   - After changing capacity, check the maps to see which zones are selected
   - High utilization zones (green) are most efficient

6. **Tooltip Information**: 
   - Hover over charts to see exact values
   - Gap/Surplus calculation helps understand energy balance

---

## Error Handling

### Common Scenarios

**"Capacity data unavailable"**:
- Selected country/year combination has no capacity data
- Try a different year or country

**"Solar/Wind profile endpoint returned no data"**:
- No renewable energy zones available for the country
- Capacity may be zero or data not available

**"Python service not available"**:
- Python API service is not running
- Start the Python service: `cd python-service && python api_server.py`

**Loading Indicators Stuck**:
- Check browser console for errors
- Verify Python service is running
- Check network connectivity

---

## Technical Details

### Data Units
- **Capacity**: Displayed in GW (Gigawatts)
- **Generation**: Displayed in GW (Gigawatts)
- **Internal Processing**: Python API uses MW, converted to GW for display

### Data Points
- **Hourly Profiles**: 8,760 data points (365 days × 24 hours)
- **Time Range**: Full year (January 1 to December 31)
- **Time Zone**: Based on selected country's time zone

### Performance
- **Grouping Disabled**: Shows all 8,760 points (may be slower)
- **Average Aggregation**: Groups data automatically (faster, better for overview)
- **Map Rendering**: Updates when capacity changes (may take a few seconds)

---

## Keyboard Shortcuts

- **Enter** (in Solar/Wind input fields): Triggers "Go" button action
- **Shift + Drag**: Pan the chart (when enabled)
- **Mouse Wheel**: Zoom in/out on charts

---

## Notes

- Year dropdown is currently disabled (defaults to 2022)
- Offshore wind charts are not displayed (removed for now)
- All charts use the same year and time axis for consistency
- Maps show loading overlays during data fetches
- Charts reset and show waiting indicators when country changes

---

## Support

For issues or questions:
1. Check browser console for error messages
2. Verify Python service is running
3. Check network connectivity
4. Review data availability for selected country/year

