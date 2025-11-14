# Stress Period Identification Methodology
*VerveStacks Intelligent Timeslice Generation Framework*

## 🎯 **Vision and Purpose**

### **Core Objective**
Transform the complex 8760-hour energy modeling problem into intelligent, stress-based timeslice structures that capture the most critical operational periods for grid planning and analysis. The methodology identifies when and where storage systems and dispatchable generation will face the greatest operational stress due to extreme mismatches between renewable supply and electricity demand.

### **Strategic Context**
Traditional energy models use fixed timeslice structures that may miss critical operational periods. VerveStacks' stress period identification methodology ensures that the most challenging grid conditions—periods requiring maximum ramping, storage cycling, and dispatchable generation—are explicitly captured in the model's temporal resolution.

## 📊 **Methodology Overview**

### **Three-Stage Process**
1. **Supply-Demand Envelope Construction**: Build realistic 8760-hour supply and demand profiles
2. **Coverage Analysis**: Calculate hourly renewable supply adequacy vs. demand
3. **Stress Period Selection**: Identify and rank critical periods for timeslice definition

### **Key Innovation: Coverage-Based Stress Identification**
**Coverage Ratio** = (Renewable Supply) / (Electricity Demand) × 100%

- **Coverage < 100%**: Scarcity periods requiring storage discharge or dispatchable generation
- **Coverage > 100%**: Surplus periods requiring storage charging or curtailment
- **High Coverage Variability**: Volatile periods requiring rapid ramping and flexibility

## 🏗️ **Stage 1: Supply-Demand Envelope Construction**

### **Demand Profile Assembly**
**Data Source**: ERA5 combined hourly demand profiles (2030 projections)
**Processing**: 
- Load ISO-specific 8760-hour demand profiles
- Scale to match country's annual electricity consumption from EMBER data
- Preserve unique demand patterns (industrial vs. residential dominant countries)

**Key Assumption**: Current demand patterns represent future temporal characteristics, scaled for projected consumption growth.

### **Renewable Supply Portfolio Construction**

#### **Technology Mix Determination**
**Data Sources**: 
- Historical deployment ratios from IRENASTAT-G.xlsx (IRENA generation data)
- Country-specific solar/wind ratios based on recent deployment patterns
- Avoids unrealistic technology monopolization (e.g., Germany 100% wind, Italy 100% solar)

**Methodology**:
1. Calculate residual demand after accounting for existing hydro generation
2. Apply historical solar/wind deployment ratios for realistic technology mix
3. Select renewable resources using "balanced relevant resource selection" approach

#### **Resource Selection Logic**
**Relevant Resources Concept**: Only evaluate the cheapest grid cells within each technology up to total residual demand requirement.

**Scoring Formula**: `Technology Score = (Relevant Potential TWh) / (Weighted Average LCOE $/MWh)`

**Allocation Process**:
1. Identify relevant resources by technology (cheapest cells up to demand requirement)
2. Calculate technology scores based on cost-effectiveness of relevant resources
3. Allocate residual demand proportionally based on technology scores
4. Select cheapest grid cells within each technology to meet allocated targets

#### **Hourly Profile Generation**
**Solar Generation**: 
- Capacity factors from REZoning/Atlite weather data (50×50km resolution)
- Hourly profiles reflect local weather patterns and seasonal variations

**Wind Generation**:
- Onshore wind capacity factors from REZoning/Atlite data
- Preserves regional wind resource diversity and temporal complementarity

**Hydro Generation**:
- Monthly generation patterns from EMBER historical data
- Distributed hourly using demand-following dispatch within monthly constraints
- Represents existing baseload renewable contribution

### **Supply Envelope Assumptions**
1. **Nuclear**: Flat baseload dispatch (existing capacity from EMBER)
2. **Hydro**: Load-following within monthly energy constraints
3. **Solar/Wind**: Weather-dependent variable generation
4. **No Storage**: Initial analysis excludes storage to identify raw supply-demand mismatches
5. **No Dispatchable**: Focus on renewable supply adequacy before conventional backup

## 🔍 **Stage 2: Coverage Analysis**

### **Hourly Coverage Calculation**
```
Coverage[hour] = (Solar[hour] + Wind[hour] + Hydro[hour]) / Demand[hour] × 100%
```

### **Statistical Aggregation**

#### **Daily Statistics**
For each of 365 days:
- **Average Coverage**: Mean of 24 hourly values
- **Minimum Coverage**: Worst hour of the day (highest stress)
- **Maximum Coverage**: Best hour of the day (highest surplus)
- **Coverage Variance**: Measure of intraday volatility
- **Coverage Standard Deviation**: Volatility metric for ranking

#### **Weekly Statistics** 
For each of 52 weeks:
- **Weekly Average Coverage**: Mean across all 168 hours
- **Weekly Minimum Coverage**: Single worst hour in the week
- **Weekly Maximum Coverage**: Single best hour in the week
- **Weekly Standard Deviation**: Measure of sustained stress vs. volatility

### **Coverage Interpretation**
- **Scarcity Periods** (Coverage < 100%): Renewable supply insufficient, requiring dispatchable generation or storage discharge
- **Surplus Periods** (Coverage > 100%): Excess renewable generation, enabling storage charging or requiring curtailment
- **Volatile Periods**: High standard deviation indicating rapid supply-demand swings requiring flexible resources

## ⚡ **Stage 3: Stress Period Selection**

### **Daily Stress Period Identification**

#### **Scarcity Day Selection**
**Ranking Criteria**: Lowest average daily coverage (ascending sort)
**Logic**: Days with sustained renewable energy shortfalls represent critical planning periods
**Operational Impact**: These days require maximum dispatchable generation and storage discharge

#### **Surplus Day Selection**
**Ranking Criteria**: Highest average daily coverage (descending sort)
**Exclusion Logic**: Cannot overlap with already-selected scarcity days
**Operational Impact**: Days requiring maximum storage charging capacity and potential curtailment management

#### **Volatility Day Selection**
**Ranking Criteria**: Highest coverage standard deviation
**Exclusion Logic**: Cannot overlap with scarcity or surplus days
**Operational Impact**: Days requiring maximum ramping capability and flexible resource coordination

### **Weekly Stress Period Identification**

#### **Sustained Stress Week Selection**
**Ranking Criteria**: Lowest weekly average coverage
**Logic**: Extended periods of renewable inadequacy requiring sustained dispatchable operation
**Operational Impact**: Tests weekly energy storage capacity and sustained generation capability

#### **Extended Surplus Week Selection**
**Ranking Criteria**: Highest weekly average coverage
**Exclusion Logic**: Cannot overlap with stress weeks
**Operational Impact**: Tests maximum storage charging and grid absorption capacity

#### **Volatile Week Selection**
**Ranking Criteria**: Highest weekly coverage standard deviation
**Logic**: Weeks with extreme supply-demand swings
**Operational Impact**: Tests rapid cycling capability of storage and dispatchable resources

### **Configuration-Driven Selection**

#### **Stress Configuration Types**
1. **Daily Stress Configurations**: `s{scarcity}p{surplus}v{volatility}_d`
   - Example: `s3p3v3_d` = 3 scarcity days + 3 surplus days + 3 volatility days
   
2. **Weekly Stress Configurations**: `s{scarcity}_w`
   - Example: `s2_w` = 2 sustained stress weeks
   
3. **Mixed Configurations**: `s{scarcity}_w_p{surplus}_d`
   - Example: `s2_w_p2_d` = 2 stress weeks + 2 surplus days

4. **Classical Clustering**: `ts{N}_c`
   - Example: `ts48_c` = 48 aggregated timeslices (no stress periods)

#### **Timeslice Assembly Process**
1. **Stress Period Selection**: Identify critical days/weeks using coverage analysis
2. **Base Aggregation**: Create seasonal/diurnal clusters for remaining periods
3. **Mapping Generation**: Assign each of 8760 hours to appropriate timeslice
4. **Validation**: Ensure energy balance and operational feasibility

## 🎯 **Operational Stress Identification**

### **Storage Stress Indicators**
- **Maximum Discharge Periods**: Hours with lowest coverage requiring storage output
- **Maximum Charge Periods**: Hours with highest coverage enabling storage input
- **Cycling Stress**: Periods with rapid coverage transitions requiring frequent charge/discharge cycles

### **Ramping Stress Indicators**
- **Steepest Coverage Gradients**: Hour-to-hour coverage changes requiring rapid dispatchable response
- **Multi-Hour Ramps**: Extended periods of increasing or decreasing coverage
- **Volatility Clustering**: Consecutive hours of high coverage variability

### **Dispatchable Generation Stress**
- **Sustained Low Coverage**: Multi-day periods requiring continuous dispatchable operation
- **Peak Shortage Events**: Single hours with minimum coverage requiring maximum dispatchable output
- **Rapid Response Events**: Coverage drops requiring fast-start generation resources

## 📈 **Methodology Validation**

### **Coverage Quality Metrics**
- **Annual Energy Balance**: Renewable supply vs. total demand
- **Seasonal Distribution**: Stress periods across all seasons
- **Operational Feasibility**: Realistic ramping rates and storage cycling

### **Stress Period Representativeness**
- **Scarcity Capture**: Selected periods represent worst-case renewable shortfalls
- **Surplus Management**: Selected periods test maximum renewable integration
- **Volatility Handling**: Selected periods challenge grid flexibility requirements

### **Model Integration Validation**
- **Timeslice Count Optimization**: Balance detail vs. computational efficiency
- **Energy Conservation**: Timeslice aggregation preserves annual energy flows
- **Operational Realism**: Selected periods reflect actual grid operational challenges

## 🔮 **Future Enhancements**

### **Advanced Stress Metrics**
- **Ramp Rate Stress**: Incorporate generation/demand ramp rate requirements
- **Frequency Response**: Include grid stability and inertia considerations
- **Economic Stress**: Integrate electricity price volatility and market stress

### **Multi-Regional Coordination**
- **Cross-Border Flows**: Account for international electricity trade
- **Regional Complementarity**: Leverage geographic diversity in renewable resources
- **Transmission Constraints**: Include grid infrastructure limitations

### **Storage Integration**
- **Storage-Aware Coverage**: Include existing storage in coverage calculations
- **Cycling Optimization**: Optimize stress periods for storage operational life
- **Multi-Technology Storage**: Account for different storage technologies and characteristics

## 📋 **Implementation Status**

### **Current Implementation** (`stress_period_analyzer.py`)
- ✅ **Configuration-Driven Processing**: JSON-based stress period configuration
- ✅ **Coverage Analysis**: Complete hourly, daily, and weekly statistics
- ✅ **Stress Period Selection**: Configurable scarcity/surplus/volatility identification
- ✅ **Professional Visualization**: Branded charts and analysis outputs
- ✅ **Enhanced Calendar Integration**: Daily coverage JSON export for heatmap visualization

### **Key Methods**
- `_build_renewable_supply()`: Constructs realistic renewable portfolio
- `_calculate_net_load()`: Computes supply-demand coverage
- `_calculate_daily_statistics_from_coverage()`: Daily stress analysis
- `_calculate_weekly_statistics_from_coverage()`: Weekly stress analysis
- `_select_daily_stress_periods()`: Configurable daily period selection
- `_select_weekly_stress_periods()`: Configurable weekly period selection

---

## 🎯 **Strategic Impact**

This methodology transforms energy system modeling from generic temporal structures to intelligent, stress-focused timeslice definitions that capture the operational reality of high-renewable electricity systems. By identifying when storage, ramping, and dispatchable resources face maximum stress, the approach ensures that energy models accurately represent the most challenging grid conditions that drive infrastructure investment and operational planning decisions.

**The result**: Energy models that focus computational resources on the periods that matter most for grid reliability, economic dispatch, and renewable energy integration success.

---

*This methodology represents the core innovation of VerveStacks' temporal modeling approach, enabling unprecedented precision in capturing operational stress periods that drive real-world energy system planning and investment decisions.*
