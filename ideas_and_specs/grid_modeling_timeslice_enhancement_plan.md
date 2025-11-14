# Grid Modeling Timeslice Enhancement Plan
**Date**: August 31, 2025  
**Status**: Ready for implementation  
**Context**: Simple batch processing and grid modeling timeslice optimization

## 🎯 Problem Statement

Currently, the `make_models.py` script for grid modeling needs to process multiple timeslice options (`ts12_clu`, `ts24_clu`, `s1d`), but:

1. **`main.py` doesn't accept multiple `--tsopt` values** (only single tsopt)
2. **Calling `main.py` in a loop is inefficient** and architecturally poor
3. **`--process-all-tsopts` processes too many options** (11 total) when we only need 3-4 for grid modeling

## 🚀 Agreed Solution

**Modify `TimeSliceProcessor` to interpret `--process-all-tsopts` differently when `grid_modeling=True`**

### Key Components:

#### 1. **Configuration-Driven Filtering**
- Use existing `stress_periods_config` sheet in `VS_mappings.xlsx`
- Filter timeslice options by `grid_modeling='y'` column
- Current grid modeling tsopts: `['ts12_clu', 'ts24_clu', 'ts48_clu', 's1_d']`

#### 2. **TimeSliceProcessor Enhancement**
- Add `get_grid_modeling_tsopts()` method to read from VS_mappings
- Modify `get_available_tsopts()` to check if `grid_modeling=True` in iso_processor
- When grid modeling: return filtered list instead of all available options

#### 3. **make_models.py Integration**
- Grid mode will use: `python main.py --iso {iso} --grid-modeling --process-all-tsopts`
- No loop needed - single call processes only grid-relevant tsopts

## 📋 Implementation Plan

### **Step 1: Add Grid Modeling Filter Method**
```python
def get_grid_modeling_tsopts(self):
    """Get timeslice options marked for grid modeling from VS_mappings."""
    try:
        shared_loader = get_shared_loader("data/")
        stress_config_df = shared_loader.get_vs_mappings_sheet('stress_periods_config')
        
        # Filter for grid modeling options
        grid_tsopts = stress_config_df[stress_config_df['grid_modeling'] == 'y']['name'].tolist()
        
        self.logger.info(f"Found {len(grid_tsopts)} grid modeling tsopts: {grid_tsopts}")
        return grid_tsopts
        
    except Exception as e:
        self.logger.error(f"Failed to get grid modeling tsopts: {e}")
        # Fallback to hardcoded list
        return ['ts12_clu', 'ts24_clu', 'ts48_clu', 's1_d']
```

### **Step 2: Modify get_available_tsopts Method**
```python
def get_available_tsopts(self):
    """Get all available time-slice options, filtered for grid modeling if applicable."""
    
    # Check if this is grid modeling mode
    if hasattr(self.iso_processor, 'grid_modeling') and self.iso_processor.grid_modeling:
        self.logger.info("Grid modeling mode detected - filtering to grid-specific tsopts")
        return self.get_grid_modeling_tsopts()
    
    # Original logic for regular models
    # ... (existing code)
```

### **Step 3: Update make_models.py Grid Mode**
```python
def process_grid_mode(self, iso):
    """Process ISO in grid mode with filtered timeslice processing."""
    
    # Step 1: Stress period analysis
    success = self.run_command(f"python scripts/stress_period_analyzer.py {iso}", working_dir="2_ts_design")
    if not success: return False
    
    # Step 2: Grid network extraction
    success = self.run_command(f"python extract_country_pypsa_network_clustered.py --country {iso} --visualize", working_dir="1_grids")
    if not success: return False
    
    # Step 3: Grid modeling with filtered timeslice processing
    success = self.run_command(f"python main.py --iso {iso} --grid-modeling --process-all-tsopts")
    if not success: return False
    
    return True
```

## 📊 Current Status

### **Completed:**
- ✅ `make_models.py` script created with nogrid/grid modes
- ✅ Identified VS_mappings `stress_periods_config` sheet structure
- ✅ Confirmed grid modeling tsopts: `['ts12_clu', 'ts24_clu', 'ts48_clu', 's1_d']`
- ✅ Architecture decision made (configuration-driven filtering)

### **Ready for Implementation:**
- 🔄 Add `get_grid_modeling_tsopts()` method to `TimeSliceProcessor`
- 🔄 Modify `get_available_tsopts()` to check `grid_modeling` flag
- 🔄 Update `make_models.py` grid mode to use `--process-all-tsopts`
- 🔄 Test with sample ISO

## 🔍 Technical Details

### **VS_mappings Configuration:**
```
Sheet: stress_periods_config
Columns: ['name', 'days_scarcity', 'days_surplus', ..., 'grid_modeling', ...]

Grid modeling tsopts (grid_modeling='y'):
- ts12_clu
- ts24_clu  
- ts48_clu
- s1_d
```

### **Current Behavior:**
- **Regular models**: `--process-all-tsopts` processes 11 options (CSV + VS_mappings)
- **Grid models**: Will process only 4 options (filtered by `grid_modeling='y'`)

### **Benefits:**
1. **Clean Architecture**: No loops in `make_models.py`
2. **Configuration-Driven**: Easy to modify grid tsopts via Excel
3. **Efficient**: Only processes needed timeslice options
4. **Consistent**: Uses existing `--process-all-tsopts` flag

## 🎯 Next Session Tasks

1. **Implement the filtering logic** in `TimeSliceProcessor`
2. **Update `make_models.py`** grid mode command
3. **Test with sample ISO** (e.g., CHE)
4. **Verify output** contains only grid modeling tsopts
5. **Update documentation** if needed

## 📝 Notes

- **No breaking changes** to existing functionality
- **Backward compatible** - regular models work unchanged  
- **Extensible** - easy to add/remove grid tsopts via Excel
- **Performance improvement** - fewer unnecessary timeslice calculations

---

## ✅ IMPLEMENTATION COMPLETED + ENHANCED

### Recent Enhancement (Current Session)
**Issue**: The original implementation only included stress-based tsopts from `stress_periods_config`, but missed the base timeslice definitions from `base_ts_design` sheet (like `ts_annual`, `ts_16`).

**Solution**: Enhanced `get_grid_modeling_tsopts()` to:
1. Load stress-based tsopts from `stress_periods_config` sheet (filtered by `grid_modeling='y'`)
2. Load base tsopts from `base_ts_design` sheet (column headers excluding description/sourcevalue)  
3. Combine both sources for complete grid modeling tsopt list
4. Updated fallback list to include both types: `['ts12_clu', 'ts24_clu', 'ts48_clu', 's1_d', 'ts_annual', 'ts_16']`

### Status Summary:
- ✅ `get_grid_modeling_tsopts()` method implemented with dual-source support
- ✅ `get_available_tsopts()` modified to filter for grid modeling
- ✅ Grid modeling timeslice filtering now includes both stress-based and base definitions
- ⏳ Testing and integration with `make_models.py` pending

The enhancement ensures that `--process-all-tsopts` in grid mode includes the complete set of timeslice definitions, maintaining compatibility with the two-part tsopt system (standard + VS_mappings).
