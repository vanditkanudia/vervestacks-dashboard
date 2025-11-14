# VerveStacks Energy Model - Technical Data Assumptions Documentation

**Version:** 1.0  
**Date:** January 2025  
**Purpose:** Comprehensive technical reference for all data assumptions, lookup tables, and key data sources

---

## 1. Data Assumptions Documentation

### 1.1 Hardcoded Constants and Default Values

#### **Core Processing Thresholds**
```python
# Plant Size Thresholds
capacity_threshold = 100 MW          # Minimum plant size for individual tracking
plants_above_threshold / 1000        # Convert MW to GW for threshold comparison

# Efficiency Adjustment Factors
efficiency_adjustment_gas = 1.0      # Default multiplier for gas plant efficiencies  
efficiency_adjustment_coal = 1.0     # Default multiplier for coal plant efficiencies
```

#### **Unit Conversion Factors**
```python
# Energy Conversions
8.76 = 8760 / 1000                  # Hours per year / 1000 (capacity factor to generation)
8760                                 # Hours per year (annual calculations)
3.6                                  # MJ to kWh conversion factor
1000                                 # MW to GW conversion
365                                  # Days per year
24                                   # Hours per day

# UNSD Energy Conversion Formula
twh_UNSD = (OBS_VALUE * CONVERSION_FACTOR / 1000 / 3.6)
```

#### **Time-related Constants**
```python
# Hour Classification (Day/Night)
day_hours = 7 <= hour <= 18         # Day period definition
night_hours = hour < 7 OR hour > 18 # Night period definition

# Seasonal Factors (RE Supply)
seasonal_pattern = 50000 + 10000 * sin(2π * hours / (365 * 24) - π/2)
daily_pattern = 15000 * sin(2π * (hours % 24) / 24 - π/3)
```

### 1.2 Technology Cost Assumptions

#### **Default Technology Costs ($/kW)**
| Technology | Cost | Source | Notes |
|------------|------|---------|-------|
| Wind | $1,500/kW | `default_settings.json` | Used in LCOE calculations |
| Solar | $700/kW | `default_settings.json` | Used in LCOE calculations |
| Default Fallback | $1,000/kW | `re_supply_capacity_calculator.py` | For unmapped technologies |

### 1.3 Time Slice Configuration

#### **Time Slice Limits**
```json
{
  "max_timeslices": 500,
  "base_aggregates": 12,
  "scenario_types": {
    "short_spans": {"max_timeslices": 300},
    "medium_spans": {"max_timeslices": 500}, 
    "long_spans": {"max_timeslices": 100}
  }
}
```

---

## 2. Key Data Sources Analysis

### 2.1 Primary Input Datasets

#### **Global Energy Monitor (GEM) - Power Facilities**
- **File:** `data/existing_stock/Global-Integrated-Power-April-2025.xlsx`
- **Sheet:** "Power facilities"
- **Key Columns Used:**
  ```
  Country/area, Type, Technology, Fuel, Status, Capacity (MW), 
  Start year, Efficiency, Owner, Project name
  ```
- **Data Processing:**
  - Remove cancelled/shelved/retired plants: `~Status.str.startswith(('cancelled', 'shelved', 'retired'))`
  - Technology fallback: `Technology = Type if Technology is null`
  - Filter: `Start year <= 2022` (base year)

**Sample Data (First 5 Rows):**
```
| Country/area | Type     | Technology | Capacity (MW) | Start year | Status    |
|--------------|----------|------------|---------------|------------|-----------|
| Germany      | coal     | hard coal  | 400.0        | 2015       | operating |
| Germany      | gas      | ccgt       | 800.0        | 2018       | operating |
| USA          | solar    | solar pv   | 250.0        | 2020       | operating |
| China        | wind     | onshore    | 150.0        | 2019       | operating |
| Japan        | nuclear  | pwr        | 1100.0       | 2010       | operating |
```

#### **IRENA Capacity and Generation Data**
- **Files:** 
  - `data/irena/IRENASTAT-C.xlsx` (Capacity)
  - `data/irena/IRENASTAT-G.xlsx` (Generation)
- **Key Columns Used:**
  ```
  Country/area, Type, 2022 (capacity/generation values)
  ```

#### **EMBER Electricity Data**
- **File:** `data/ember/yearly_full_release_long_format.csv`
- **Key Columns Used:**
  ```
  Country code, Variable (=Type), Category, Subcategory, 
  Unit, 2022 (values)
  ```
- **Filter:** `Subcategory == 'Fuel'`

#### **UNSD Energy Statistics**
- **File:** `data/unsd/unsd_july_2025.csv`
- **Key Columns Used:**
  ```
  TIME_PERIOD, REF_AREA, COMMODITY, TRANSACTION, 
  OBS_VALUE, CONVERSION_FACTOR
  ```
- **Processing:** Filtered for `attribute='transformation'` and `sector='power'`

### 2.2 Lookup Tables and Mappings

#### **VS_mappings.xlsx Sheet Structure**
| Sheet Name | Purpose | Key Columns |
|------------|---------|-------------|
| `gem_techmap` | GEM technology to model mapping | `model_fuel`, `Technology`, `model_name` |
| `irena_ember_typemap` | Fuel type harmonization | `Type`, `Source`, `model_fuel` |
| `unsd_region_map` | UNSD country code to ISO mapping | `Code`, `ISO` |
| `unsd_product_map` | UNSD commodity code mapping | `Code`, `model_fuel` |
| `unsd_flow_map` | UNSD transaction type mapping | `Code`, `attribute`, `sector` |

#### **Fuel Type Mapping Logic**
```python
def custom_fuel(row):
    """Custom fuel mapping for GEM data"""
    if row['Type'] != 'oil/gas':
        return 'hydro' if row['Type'] == 'hydropower' else row['Type']
    else:
        fuel_val = str(row['Fuel']) if pd.notna(row['Fuel']) else ''
        return 'oil' if fuel_val.lower().startswith('fossil liquids:') else 'gas'
```

### 2.3 Technology Cost Data

#### **Techno-economic Parameters**
- **File:** `data/technologies/ep_technoeconomic_assumptions.xlsx`
- **Key Columns:** `capex`, `fixom`, `varom`, `efficiency`, `life`
- **File:** `data/technologies/advanced_parameters.xlsx`
- **Purpose:** Advanced technology parameters and assumptions

#### **RE Potential Data**
- **File:** `data/technologies/re_potentials.xlsx`
- **Key Columns:** `CAP_BND`, `AF~FX`, `Comm-IN`, `technology`
- **Usage:** Renewable energy resource potential and capacity factors

---

## 3. Configuration Parameters

### 3.1 Processing Parameters

#### **Model Generation Parameters**
| Parameter | Default Value | Units | Description | Applied Where |
|-----------|---------------|-------|-------------|---------------|
| `capacity_threshold` | 100 | MW | Minimum plant size for individual tracking | Plant aggregation logic |
| `efficiency_adjustment_gas` | 1.0 | multiplier | Gas plant efficiency adjustment | Efficiency calculations |
| `efficiency_adjustment_coal` | 1.0 | multiplier | Coal plant efficiency adjustment | Efficiency calculations |

#### **Time Slice Parameters**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| `base_aggregates` | 12 | Base monthly aggregation |
| `weather_year` | 2013 | Reference weather year for profiles |
| `base_year` | 2022 | Base year for calibration |

### 3.2 Data Quality Filters

#### **Plant Status Exclusions**
```python
excluded_status = ['cancelled', 'shelved', 'retired']
df_gem = df_gem[~df_gem['Status'].str.lower().str.startswith(excluded_status)]
```

#### **Data Validation Rules**
- **UNSD Filter:** `commodity = 7000 AND TIME_PERIOD >= 2000`
- **Base Year Filter:** `Start year <= 2022`
- **Efficiency Validation:** `coalesce(efficiency, 1)` (default to 1.0 if missing)

---

## 4. Derived Assumptions

### 4.1 Generation Calculations

#### **Annual Generation Formula**
```python
# GEM + IRENA Utilization
generation_twh_gem_irena = capacity_gw * utilization_factor_irena * 8.76

# GEM + EMBER Utilization  
generation_twh_gem_ember = capacity_gw * utilization_factor_ember * 8.76

# Fuel Consumption
fuel_consumed_twh = (capacity_gw * utilization_factor * 8.76) / efficiency
```

#### **Capacity Factor Calculations**
```python
# Annual capacity factor
annual_cf = annual_generation_mwh / (capacity_mw * 8760)

# Renewable capacity factors (from resource data)
capacity_factor = AF_FX  # Availability factor from resource files
```

### 4.2 Technology Mapping Derivations

#### **Model Name Generation**
```python
# Priority mapping logic:
# 1. Use gem_techmap mapping if available
# 2. Fallback to generated name: f"ep_{model_fuel}"

model_name = gem_map.get(technology, f"ep_{model_fuel}")
```

#### **Solar/Wind Resource Mapping**
```python
# Technology-specific outputs
comm_out = {
    'solar': f'ELC_Sol-{ISO}',
    'wind': f'ELC_Win-{ISO}',
    'default': 'comm-out'  # From original mapping
}
```

### 4.3 Regional Aggregations

#### **Country Name Cleaning**
```python
def clean_country_name(country_name):
    """Remove trailing bracketed information"""
    return re.sub(r'\s*\(.*\)\s*$', '', country_name).strip()

# Special case mappings
special_cases = {
    'kosovo': 'XKX',
    'chinese taipei': 'TWN', 
    'republic of korea': 'KOR',
    'china, hong kong special administrative region': 'HKG'
}
```

### 4.4 Time-based Aggregations

#### **Day/Night Classification**
```python
day_night = lambda h: 'D' if 7 <= h <= 18 else 'N'
```

#### **Seasonal Patterns**
```python
# Month to season mapping
month_to_season = {1:1, 2:1, 3:2, 4:2, 5:2, 6:3, 7:3, 8:3, 9:4, 10:4, 11:4, 12:1}
```

---

## 5. Data Quality Assumptions

### 5.1 Missing Data Handling

#### **Default Values Applied**
| Field | Default | Condition | Impact |
|-------|---------|-----------|---------|
| Technology | `Type` value | When Technology is null | Technology classification |
| Efficiency | 1.0 | When efficiency is null | Fuel consumption calculations |
| Utilization Factor | From lookup | When plant-specific data missing | Generation estimates |

### 5.2 Data Prioritization Hierarchy

#### **Capacity Data Priority**
1. **GEM plant-level data** (for plants > 100 MW)
2. **IRENA national statistics** (for validation/aggregation)
3. **EMBER national statistics** (alternative validation)

#### **Generation Data Priority**
1. **IRENA generation statistics** (primary)
2. **EMBER generation statistics** (secondary)
3. **Calculated from capacity × utilization** (derived)

---

## 6. Validation and Quality Checks

### 6.1 Data Reconciliation Formulas

#### **Capacity Coverage Calculation**
```python
gem_coverage_pct = (capacity_tracked_individually / total_national_capacity) * 100
individual_plants_count = len(plants[plants['Capacity_GW'] >= threshold/1000])
```

#### **Generation Validation**
```python
# Cross-validation between sources
generation_ratio = generation_twh_gem_irena / generation_twh_ember
fuel_consistency_check = fuel_consumed_twh_irena / fuel_consumed_twh_ember
```

### 6.2 Assumptions Impact Analysis

#### **Sensitivity Parameters**
- **Capacity Threshold:** Affects number of individually tracked plants
- **Efficiency Adjustments:** Directly impacts fuel consumption estimates  
- **Utilization Factors:** Critical for generation/capacity reconciliation

---

## 7. Grid Modeling and Transmission Infrastructure

### 7.1 Grid Data Sources

#### **Grid Infrastructure Data**
- **Files:** `grids/data/lines.csv`, `grids_1/data/gem.csv`, `grids/data/solar.csv`, `grids/data/wind.csv`
- **Purpose:** Transmission line modeling and grid connectivity analysis

#### **Lines Data Structure**
- **Key Columns:** `bus0`, `bus1`, `type`, `length`, `s_nom`
- **Processing:** 
  ```python
  # Bus name standardization
  comm1 = bus0.str.replace('way/', 'w').str.replace('relation/', 'r')
  comm2 = bus1.str.replace('way/', 'w').str.replace('relation/', 'r')
  
  # Aggregation by route
  length_km = round(max(length)/1000, 0)
  capacity_gw = sum(s_nom)/1000
  ```

### 7.2 Grid Model Generation

#### **TradeLinks Table Structure**
```sql
SELECT '{input_iso}' as reg1, '{input_iso}' as reg2, 
       'ELC' as comm, 
       'e_' || comm1 AS comm1, 
       'e_' || comm2 AS comm2,
       'g_' || comm1 || '-' || comm2 AS tech,
       'B' AS tradelink,
       'grid link -' || length_km || ' km- ' || type AS description,
       gw as cap
```

**Sample Grid Links Output:**
```
| reg1 | reg2 | comm | comm1 | comm2 | tech | tradelink | description | cap |
|------|------|------|-------|-------|------|-----------|------------|-----|
| CHE  | CHE  | ELC  | e_w123| e_w456| g_w123-w456 | B | grid link -50 km- ac | 2.5 |
| CHE  | CHE  | ELC  | e_r789| e_r012| g_r789-r012 | B | grid link -120 km- dc | 1.8 |
```

#### **Grid Infrastructure Assumptions**
- **Distance Calculation:** `max(length)/1000` - Maximum route length in km
- **Capacity Aggregation:** `sum(s_nom)/1000` - Total capacity in GW
- **Technology Naming:** `g_{bus1}-{bus2}` format for grid technologies
- **Commodity Mapping:** All grid links use `ELC` (electricity) commodity

---

## 8. CCS Retrofit Computations

### 8.1 CCS Retrofit Data Sources

#### **EPA CCS Retrofit Database**
- **File:** `data/existing_stock/epa_coal+gas ccs retrofit data.xlsx`
- **Sheet:** `epa_ccs_rf`
- **Purpose:** Carbon capture and storage retrofit potential for existing fossil fuel plants

#### **CCS Processing Workflow**
```python
# Load EPA CCS retrofit data
epa_ccs_rf_df = pd.read_excel("data/existing_stock/epa_coal+gas ccs retrofit data.xlsx", 
                              sheet_name="epa_ccs_rf")

# Filter and process CCS retrofit candidates
# (Specific processing logic varies by fuel type - coal vs gas)
```

### 8.2 CCS Retrofit Assumptions

#### **Technology Targeting**
- **Coal Plants:** CCS retrofit potential based on plant age, size, and efficiency
- **Gas Plants:** Natural gas CCS retrofit analysis
- **Minimum Size Threshold:** Applied consistent with capacity_threshold (100 MW)

#### **CCS Technology Parameters**
- **Capture Rate Assumptions:** Varies by technology and fuel type
- **Retrofit Costs:** Technology-specific CAPEX and OPEX adjustments
- **Efficiency Penalties:** Reduced plant efficiency due to CCS equipment

### 8.3 CCS Data Integration

#### **Output Sheet Structure**
- **Sheet Name:** `ccs_retrofits`
- **Integration:** Combined with existing stock data for plant-level CCS potential
- **Usage:** Referenced in VEDA model creation for CCS technology options

**Sample CCS Retrofit Data:**
```
| Plant ID | Technology | Capacity_MW | CCS_Potential | Retrofit_Cost | Efficiency_Penalty |
|----------|------------|-------------|---------------|---------------|--------------------|
| USA_001  | coal       | 500         | Yes          | 1500          | 0.15               |
| USA_002  | gas_ccgt   | 800         | Yes          | 800           | 0.08               |
```

---

## 9. Reference Tables

### 9.1 Unit Conversions Summary

| Conversion | Formula | Usage |
|------------|---------|-------|
| MW to GW | `/1000` | Capacity aggregation |
| Hours to year fraction | `/8760` | Annual calculations |
| MJ to kWh | `/3.6` | UNSD energy data |
| Capacity to generation | `MW × CF × 8760 / 1000` | TWh calculation |

### 9.2 File Dependencies

| Analysis Component | Required Files | Critical Sheets/Columns |
|-------------------|----------------|------------------------|
| Technology Mapping | `VS_mappings.xlsx` | `gem_techmap`, `irena_ember_typemap` |
| Existing Stock | `Global-Integrated-Power-April-2025.xlsx` | Power facilities |
| National Statistics | `IRENASTAT-C.xlsx`, `IRENASTAT-G.xlsx` | Country/technology data |
| Energy Balances | `unsd_july_2025.csv` | TIME_PERIOD, REF_AREA, COMMODITY |
| Scenarios | `Downscaled_MESSAGEix-GLOBIOM 1.1-M-R12_data.xlsx` | IAMC scenario data |

---

**Document Control:**
- **Maintainer:** VerveStacks Development Team
- **Review Frequency:** With each major data update
- **Validation:** Cross-reference with generated `MODEL_NOTES.md` files