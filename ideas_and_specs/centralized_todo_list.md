# Centralized Todo List - VerveStacks
**Date**: December 19, 2024  
**Status**: Active  
**Purpose**: Centralized task tracking for VerveStacks development

## 🚨 **High Priority Tasks**

### **Data Source Validation System**
- [ ] **Create ISO validation function** to check presence in all key data sources
  - **Scope**: Check REZoning (Solar + Wind), EMBER, ERA5 demand, IRENA capacity/generation
  - **Implementation**: Function should return clear list of missing data sources
  - **Integration**: Add to main pipeline (`main.py`) and batch processing (`batch_process_models.py`)
  - **Error Handling**: Bypass all processing with clear error message if any key data missing
  - **User Experience**: Show which specific data sources are missing for the ISO
  - **Priority**: HIGH - Prevents silent failures like NZL case

## 📋 **Active Development Tasks**

### **Grid Modeling Enhancement**
- [x] Implement `get_grid_modeling_tsopts()` method with dual-source support
- [x] Modify `get_available_tsopts()` to filter for grid modeling
- [ ] Test grid modeling timeslice filtering with sample ISO (e.g., CHE)
- [ ] Verify output contains only grid modeling tsopts
- [ ] Update documentation if needed

### **YAML-Based README System**
- [x] Create YAML configuration structure for all 4 components
- [x] Implement AR6 integration documentation system
- [x] Build core README generator with template rendering
- [ ] Implement data flow integration (Call 1 and Call 2)
- [ ] Add incremental build logic
- [ ] Create file-based data readers for each module
- [ ] Migrate existing hardcoded README content to YAML templates

## 🔄 **In Progress**

### **Stress Period Analyser Issues**
- [x] Identify NZL missing data root cause (REZoning data absence)
- [ ] Implement fallback logic for countries missing from REZoning data
- [ ] Add alternative renewable data sources for unsupported countries
- [ ] Fix PNG generation failures for countries with missing REZoning data

### **Data Column Naming Issues**
- [x] Fix 'lng' vs 'long' column naming inconsistency in REZoning data
- [x] Update generate_geographic_data function to handle both column names

### **Grid Modeling README Enhancement**
- [x] Create comprehensive YAML templates for grid modeling documentation
- [x] Implement data extraction functions for grid metrics
- [x] Add HTML visualization embedding with iframe
- [x] Create grid_analysis subfolder for visualization files
- [x] Update README generator to handle grid modeling flag
- [x] Remove all fallback logic - code crashes loud and fast if data missing
- [x] Fix column name from 'load_gw' to 'load_share' and use only voronoi CSV
- [x] Correct zone analysis - solar zones are actually solar/wind onshore combined zones
- [x] Fix variable population - add missing template parameters to prevent KeyError

## 📝 **Parked Ideas**

### **Context Management System**
- [x] Create `ideas_and_specs/` folder as external memory system
- [ ] Develop consistent documentation patterns
- [ ] Test effectiveness across multiple sessions

### **Enhanced Calendar Visualization**
- [x] Design coverage heatmap concept
- [x] Identify data requirements (daily coverage JSON)
- [ ] Modify stress period analyser to export daily coverage data
- [ ] Update calendar visualizer with heatmap functionality
- [ ] Integrate enhanced calendar into VEDA model READMEs

## ✅ **Completed Tasks**

### **Grid Modeling Timeslice Enhancement**
- [x] Design configuration-driven filtering approach
- [x] Implement `get_grid_modeling_tsopts()` method
- [x] Add dual-source support (stress_periods_config + base_ts_design)
- [x] Modify `get_available_tsopts()` for grid modeling filtering

### **Context Management**
- [x] Create centralized todo list
- [x] Document NZL data source validation issue

## 🎯 **Next Session Priorities**

1. **Implement ISO validation function** - Critical for preventing silent failures
2. **Test grid modeling enhancement** - Verify complete implementation
3. **Continue YAML README system** - Complete data flow integration

## 📊 **Task Status Summary**

- **Total Tasks**: 15
- **Completed**: 6 (40%)
- **In Progress**: 4 (27%)
- **Pending**: 5 (33%)

---

**Last Updated**: December 19, 2024  
**Next Review**: Next development session
