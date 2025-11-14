# Stress-Based Timeslice Engine Vision
*Transforming Fixed Timeslice Generation into a Configurable Stress Period Engine*

## 🎯 **Vision Statement**

Replace the current three hardcoded stress period calls (`s1p1v1_d`, `s3p3v3_d`, `s2_w`) with a single, parameterized function that generates timeslices based on configurable stress period definitions. This transformation leverages the existing rich hourly coverage analysis while providing complete flexibility in timeslice generation strategies.

## 📊 **Current State Analysis**

### **Strengths (Keep)**
- ✅ **Rich Data Generation**: Excellent hourly coverage metrics computation
- ✅ **Smart Classification**: Days/weeks binned into scarcity/surplus/volatile categories
- ✅ **Proven Methodology**: Existing stress period identification works well

### **Limitations (Transform)**
- ❌ **Rigid Execution**: Three hardcoded function calls limit experimentation
- ❌ **Fixed Aggregation**: Always ≤48 timeslices regardless of use case needs
- ❌ **Mixed Config Issues**: VS_mappings integration created conflicts due to different aggregation schemes
- ❌ **Limited Extensibility**: Adding new stress combinations requires code changes

## 🚀 **Proposed Architecture**

### **Core Function Signature**
```python
def generate_stress_based_timeslices(
    name: str,                    # Configuration identifier
    days_scarcity: int = None,    # Number of scarcity days to capture
    days_surplus: int = None,     # Number of surplus days to capture  
    days_volatility: int = None,  # Number of volatile days to capture
    weeks_scarcity: int = None,   # Number of scarcity weeks to capture
    weeks_surplus: int = None,    # Number of surplus weeks to capture
    weeks_volatility: int = None, # Number of volatile weeks to capture
    num_aggregated_ts: int = 48,  # Aggregated timeslices for remaining periods
    create_plot: bool = False     # Generate visualization for this configuration
):
```

### **Configuration-Driven Execution**
```python
# Replace three hardcoded calls with dynamic configuration processing
stress_config_df = shared_loader.get_vs_mappings_sheet('stress_periods_config')

for _, config in stress_config_df.iterrows():
    generate_stress_based_timeslices(**config.to_dict())
```

## 📋 **Configuration Schema**

### **Current Stress Periods Config Table**
| name | days_scarcity | days_surplus | days_volatility | weeks_scarcity | weeks_surplus | weeks_volatility | num_aggregated_ts | create_plot |
|------|---------------|--------------|-----------------|----------------|---------------|------------------|-------------------|-------------|
| s1p1v1_d | 1 | 1 | 1 | - | - | - | 48 | True |
| s3p3v3_d | 3 | 3 | 3 | - | - | - | 48 | True |
| s2_w | - | - | - | 2 | - | - | 48 | False |
| s2_w_p2_d | - | 2 | - | 2 | - | - | 48 | False |
| ts12_c | - | - | - | - | - | - | 12 | False |
| ts24_c | - | - | - | - | - | - | 24 | False |
| ts48_c | - | - | - | - | - | - | 48 | True |

### **Configuration Types**

1. **Stress-Based Configurations**:
   - `s{scarcity}p{surplus}v{volatility}_d`: Day-level stress periods
   - `s{scarcity}_w`: Week-level stress periods
   - `s{scarcity}_w_p{surplus}_d`: Mixed week/day stress periods

2. **Classical Configurations**:
   - `ts{N}_c`: Classical timeslice approaches with N aggregated periods

3. **Visualization Control**:
   - `create_plot`: Selective chart generation for key configurations

## 🔧 **Implementation Approach**

### **Phase 1: Function Refactoring**
1. **Extract Common Logic**: Identify shared processing steps from current three calls
2. **Parameterize Selection**: Make stress period selection configurable
3. **Unify Aggregation**: Consistent handling of `num_aggregated_ts` parameter
4. **Add Plot Control**: Conditional visualization based on `create_plot` flag

### **Phase 2: Configuration Integration**
1. **Load Config Table**: Read `stress_periods_config` from VS_mappings
2. **Dynamic Execution**: Loop through configurations instead of hardcoded calls
3. **Validation Logic**: Ensure parameter combinations are valid
4. **Error Handling**: Graceful handling of missing stress periods

### **Phase 3: Enhanced Features**
1. **Week-Level Surplus/Volatility**: Complete the classification for weeks
2. **Custom Aggregation**: Support for non-standard timeslice counts
3. **Hybrid Configurations**: Mix of day/week stress periods
4. **Performance Optimization**: Efficient processing of multiple configurations

## 🎯 **Key Benefits**

### **Research Flexibility**
- **Easy Experimentation**: Add new configurations without code changes
- **Comparative Analysis**: Run multiple stress period strategies simultaneously
- **Sensitivity Testing**: Vary aggregation levels to assess impact

### **Use Case Optimization**
- **Quick Analysis**: 12ts for rapid prototyping
- **Detailed Modeling**: 48ts for comprehensive analysis
- **Custom Requirements**: Any aggregation level for specific needs

### **Clean Architecture**
- **Single Responsibility**: One function handles all stress-based generation
- **Configuration Separation**: Logic separated from parameters
- **No Mixed Configs**: Each run uses consistent aggregation scheme

### **Operational Excellence**
- **Selective Visualization**: Generate plots only where needed
- **Consistent Output**: Standardized timeslice generation across all configurations
- **Future-Proof**: Easy extension for new stress metrics or methodologies

## 🚨 **Critical Considerations**

### **Mixed Configuration Prevention**
- **Isolated Runs**: Each configuration generates completely separate output
- **Consistent Aggregation**: All timeslices within a run use same `num_aggregated_ts`
- **Clean Separation**: No mixing of stress-based and classical approaches within single model

### **Data Dependency Management**
- **Rich Data Prerequisite**: Ensure hourly coverage analysis is complete before stress period selection
- **Classification Completeness**: Verify all stress categories (scarcity/surplus/volatility) are properly identified
- **Fallback Handling**: Graceful degradation when insufficient stress periods are available

### **Performance Optimization**
- **Shared Preprocessing**: Reuse hourly analysis across multiple configurations
- **Selective Processing**: Skip unnecessary computations based on configuration parameters
- **Memory Management**: Efficient handling of multiple timeslice outputs

## 🔮 **Future Extensions**

### **Advanced Stress Metrics**
- **Ramp Rate Periods**: Capture high generation/demand ramp events
- **Price Volatility**: Include economic stress indicators
- **Grid Stability**: Incorporate frequency/voltage stress periods

### **Dynamic Aggregation**
- **Adaptive Timeslices**: Vary aggregation based on system characteristics
- **Seasonal Adjustment**: Different aggregation levels by season
- **Load-Based Scaling**: Aggregation proportional to system size

### **Multi-Objective Optimization**
- **Pareto Configurations**: Balance detail vs computational efficiency
- **Automated Selection**: AI-driven configuration recommendation
- **Validation Metrics**: Quantitative assessment of timeslice quality

## 📈 **Success Metrics**

1. **Flexibility**: Number of new configurations easily added
2. **Performance**: Processing time per configuration
3. **Quality**: Accuracy of stress period capture vs full 8760 analysis
4. **Usability**: Ease of adding/modifying configurations
5. **Reliability**: Consistent results across different aggregation levels

---

*This vision transforms VerveStacks timeslice generation from a fixed-flavor approach into a configurable stress period engine, enabling unprecedented flexibility in energy system temporal modeling while maintaining the proven methodology for stress period identification.*
