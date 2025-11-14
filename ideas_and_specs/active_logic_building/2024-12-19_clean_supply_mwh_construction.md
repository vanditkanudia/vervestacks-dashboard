# Complete 8760-Hour Supply and Demand Construction Logic

**Date:** 2024-12-19  
**Status:** Active Development  
**Type:** Core Algorithm Logic

## Context/Background
Defining how to construct a complete 8760-hour zero-emission electricity generation picture for any ISO, with hour-by-hour supply and demand profiles for timeslice analysis.

## Core Concept
Build complete hourly supply-demand view using:
- **Fixed baseline**: Hydro (demand-shaped) + Nuclear (flat) from 2022 actual generation
- **Variable addition**: Solar and wind from REZoning grid cells, selected by LCOE with grid-cell level hourly shapes

## Algorithm: Complete 8760-Hour Supply and Demand Construction

### **INPUT**
- ISO code (e.g., "DEU")

### **STEP 1: Load Demand Profile**
```python
# Use cached shared loader
shared_loader = get_shared_loader(data_path)
demand_df = shared_loader.get_era5_demand_data()  # Cached era5_combined_data_2030.csv

# Pivot by country, map to ISO, extract 8760-hour profile  
iso_demand_profile = iso_demand[iso_code].values  # MW for each hour (8760 values)
annual_demand_mwh = iso_demand_profile.sum()
```

### **STEP 2: Build Baseline Generation Profiles**

#### **Data Source Hierarchy (ISO-level fallback):**
```python
# Primary source (cached)
shared_loader = get_shared_loader(data_path)
monthly_df = shared_loader.get_monthly_hydro_data()  # Cached monthly_full_release_long_format.csv

# Fallback source (cached)
yearly_df = shared_loader.get_ember_data()  # Cached yearly_full_release_long_format.csv
```

#### **Nuclear Generation:**
- **If ISO in monthly data**: Get monthly TWh → flat profile within each month
- **If ISO missing**: Get annual TWh → flat across all 8760 hours (`annual_twh * 1,000,000 / 8760`)

#### **Hydro Generation:**
- **If ISO in monthly data**: Get monthly TWh → demand-shaped within each month
- **If ISO missing**: Get annual TWh → apply similar country monthly pattern → demand-shaped within each month
- **Similar country mapping**: Regional groups (Europe, North America, Asia Pacific, Africa, South America)
- **Demand shaping**: `month_hydro_mw = (month_demand / month_demand.sum()) * monthly_twh * 1,000,000`

### **STEP 3: Calculate Energy Budget**
```python
baseline_mwh = nuclear_hourly.sum() + hydro_hourly.sum()
residual_mwh = annual_demand_mwh - baseline_mwh
```

### **STEP 4: Select Renewable Grid Cells**
```python
# Use cached REZoning data from main processor
solar_cells = processor.df_solar_rezoning  # Cached and deduplicated REZoning_Solar.csv
wind_cells = processor.df_wind_rezoning    # Cached and deduplicated REZoning_WindOnshore.csv

# Filter by ISO and combine
iso_renewable_cells = all_cells[all_cells['ISO'] == iso_code]

# Sort by LCOE (cheapest first)
sorted_cells = iso_renewable_cells.sort_values('LCOE')

# Select grid cells until energy target met
selected_cells = []
selected_generation_mwh = 0

for cell in sorted_cells:
    if selected_generation_mwh >= residual_mwh:
        break
    selected_cells.append(cell)
    selected_generation_mwh += cell['Generation (MWh)']
```

### **STEP 5: Build Renewable Hourly Profiles**
```python
# Use cached shapes data
shared_loader = get_shared_loader(data_path)
shapes_df = shared_loader.get_sarah_grid_weather_data()  # Cached sarah_era5_iso_grid_cell_2013.csv

# Initialize hourly arrays
solar_hourly = np.zeros(8760)
wind_hourly = np.zeros(8760)

# For each selected grid cell
for cell in selected_cells:
    # Find matching shapes by grid_cell ID = grid_cell, month, day, hour
    cell_shapes = shapes_df[shapes_df['grid_cell'] == cell['grid_cell']]
    
    if not cell_shapes.empty:
        # Join on month/day/hour to get proper 8760 sequence
        if cell['Technology'] == 'solar':
            # hourly_mw = annual_mwh * hourly_fraction
            cell_hourly = cell['Generation (MWh)'] * cell_shapes['com_fr_solar'].values
            solar_hourly += cell_hourly
        elif cell['Technology'] == 'wind':
            cell_hourly = cell['Generation (MWh)'] * cell_shapes['com_fr_wind'].values  
            wind_hourly += cell_hourly
    # If no shapes data: skip grid cell
```

### **STEP 6: Final 8760-Hour Supply and Demand**
```python
# Complete supply profile (MW for each hour)
total_supply_hourly = nuclear_hourly + hydro_hourly + solar_hourly + wind_hourly

# Complete demand profile (MW for each hour)  
total_demand_hourly = iso_demand_profile

# Net load / shortage-surplus (MW for each hour)
net_load_hourly = total_demand_hourly - total_supply_hourly
```

### **OUTPUT**
- `total_demand_hourly[8760]`: MW demand for each hour
- `total_supply_hourly[8760]`: MW supply for each hour (nuclear + hydro + solar + wind)
- `net_load_hourly[8760]`: MW net load for each hour (basis for timeslice analysis)
- Selected grid cells with known generation amounts and cost characteristics

## Key Data Sources
- **Demand**: Cached via `shared_loader.get_era5_demand_data()` 
- **Baseline generation**: Cached via `shared_loader.get_monthly_hydro_data()` and `shared_loader.get_ember_data()`
- **REZoning grid cells**: Cached via `processor.df_solar_rezoning` and `processor.df_wind_rezoning`
- **Hourly shapes**: Cached via `shared_loader.get_sarah_grid_weather_data()`

## Technical Details
- **Grid-cell level resolution**: Each renewable grid cell has individual hourly shapes
- **Pure economic optimization**: LCOE-driven selection with no artificial constraints
- **Hour-by-hour joining**: Shapes data joined on month/day/hour columns for proper sequence
- **Skip missing shapes**: Grid cells without matching shapes data are excluded
- **Regional fallback**: Similar country monthly patterns for hydro when ISO data missing

## Result
Complete 8760-hour supply and demand profiles ready for:
- Net load calculation (demand - supply)
- Timeslice analysis and critical period identification  
- Supply-demand visualization and analysis

## Next Steps
- Create standalone script implementing this logic
- Generate stacked area chart (supply slices) + demand line visualization
- Test with sample ISO data
