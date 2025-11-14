# YAML-Based README Documentation Approach

**Date**: August 26, 2025  
**Status**: Design Complete - Ready for Implementation  
**Priority**: High - Core Infrastructure

## 🎯 **Vision**

Transform VerveStacks README generation from hardcoded strings to a flexible, maintainable YAML-based system that supports incremental builds and modular documentation.

## 📋 **Two-Call Architecture**

### **Call 1: After Core Processing**
```python
# Location: existing_stock_processor.py or main processing workflow
readme_gen.generate_readme_content(
    iso_code, 
    processing_params=core_metrics,  # In-memory data only
    core_processing=True             # Only core sections
)
```

**Rationale**: Core processing metrics (capacity thresholds, plant counts, efficiency adjustments, coverage percentages) are calculated **in-memory** and not persisted to CSV files. Must capture immediately or data is lost.

### **Call 2: At Very End (After All Modules)**
```python
# Location: After timeslice design, grid modeling (optional), and AR6 scenarios
readme_gen.generate_readme_content(
    iso_code,
    processing_params=final_params,
    timeslice_analysis=True,           # Always - reads from 2_ts_design/outputs/
    grid_modeling=grid_modeling_flag,  # Conditional - reads from 1_grids/output_kan/
    ar6_scenarios=True                 # Always - reads from Excel template
)
```

**Rationale**: These three modules write their data to **persistent files** (CSVs, Excel, output folders), so README generator can read them at the end when all processing is complete.

## 🔄 **Data Flow & Dependencies**

| Module | Data Source | Availability | Read Method |
|--------|-------------|--------------|-------------|
| **Core Processing** | In-memory metrics | ✅ During processing | Parameter passing |
| **Timeslice Analysis** | `2_ts_design/outputs/{iso}/` | ✅ After ts_design | File system read |
| **Grid Modeling** | `1_grids/output_kan/{iso}/` | ✅ After grid processing | File system read |
| **AR6 Scenarios** | `SuppXLS/Scen_Par-AR6_R10.xlsx` + CSV | ✅ After scenario creation | Excel + CSV read |

## 📚 **YAML Configuration Structure**

### **Unified Config**: `config/readme_documentation.yaml`
```yaml
readme_sections:
  core_processing:
    enabled_by_default: true    # Always included in Call 1
    data_source: "parameters"   # Passed as function parameters
    
  timeslice_analysis:
    enabled_when: "timeslice_analysis=True"
    data_source: "file_system"  # Read from 2_ts_design/outputs/
    
  grid_modeling:
    enabled_when: "grid_modeling=True"  
    data_source: "file_system"  # Read from 1_grids/output_kan/
    
  ar6_scenarios:
    enabled_when: "ar6_scenarios=True"
    data_source: "file_system"  # Read from Excel + CSV files
```

## 🏗️ **Implementation Requirements**

### **1. README Generator Enhancements**
- **Incremental build support**: Merge new content with existing README
- **File-based data readers**: Functions to extract metrics from output files
- **Smart insertion logic**: Place new sections in correct order without disrupting existing content

### **2. Data Extraction Functions**
```python
def extract_timeslice_metrics(iso_code):
    """Read timeslice analysis results from 2_ts_design/outputs/{iso}/"""
    
def extract_grid_modeling_metrics(iso_code):
    """Read grid modeling results from 1_grids/output_kan/{iso}/"""
    
def extract_ar6_scenario_metrics(iso_code):
    """Read AR6 scenario data from Excel template and CSV drivers"""
```

### **3. Integration Points**
- **Call 1**: Integrate into existing core processing workflow (likely in `existing_stock_processor.py` or `veda_model_creator.py`)
- **Call 2**: Add to final model assembly stage after all modules complete

## ✅ **Benefits of This Approach**

1. **No Data Loss**: Core metrics captured when available (in-memory)
2. **Efficient**: File-based modules read once at the end
3. **Flexible**: Grid modeling optional, others always included  
4. **Non-Disruptive**: Fits existing workflow without major changes
5. **Maintainable**: YAML templates easy to modify and extend
6. **Modular**: Each documentation component independent
7. **Incremental**: Can migrate existing hardcoded sections gradually

## 🎯 **Next Steps for Implementation**

1. **Enhance README Generator**: Add incremental build and file reading capabilities
2. **Create Data Extractors**: Functions to read metrics from each module's output files
3. **Identify Integration Points**: Find exact locations for Call 1 and Call 2 in existing workflow
4. **Test Incremental Builds**: Ensure new content merges properly with existing README
5. **Migrate Existing Sections**: Gradually move hardcoded README content to YAML templates

## 📝 **Current Status**

- ✅ **YAML Configuration**: Complete unified structure for all 4 components
- ✅ **AR6 Integration**: Full AR6 scenario documentation system ready
- ✅ **README Generator**: Core engine with template rendering
- 🔄 **Data Flow Integration**: Needs implementation (tomorrow's priority)
- 🔄 **Incremental Build Logic**: Needs implementation
- 🔄 **File-Based Data Readers**: Needs implementation

---

**Note**: This approach transforms README generation from a maintenance burden into a flexible, data-driven system that can evolve with VerveStacks capabilities while preserving all existing functionality.
