# Changelog

## [Latest] - 2024-12-19

### 🚀 **New Features**

#### **Gap-filling Functionality**
- ✅ **Automatic capacity gap-filling** from IRENA and EMBER reference datasets
- ✅ **IRENA integration** for solar and wind capacity validation
- ✅ **EMBER integration** for coal, gas, and bioenergy capacity validation
- ✅ **Smart comparison logic** compares 2022 reference data vs cumulative GEM capacity (≤2022)
- ✅ **Automated record creation** adds missing capacity as aggregated plant records for year 2022
- ✅ **Traceability features** - new records tagged with "IRENA Gap" or "EMBER Gap" identifiers

### 🔧 **Bug Fixes**

#### **Case Sensitivity in Cost Lookups**
- ✅ **Fixed cost/efficiency matching** - now case-insensitive in `get_costs_and_eff()` function
- ✅ **Improved SQL queries** using `lower()` comparisons for model_name matching
- ✅ **Enhanced gap-filling support** - resolves issues where new records couldn't get cost/efficiency data

#### **Data Preservation Improvements**
- ✅ **Left join implementation** preserves gap-filling records during model_name mapping
- ✅ **Fallback model_name generation** creates `ep_{fuel_type}` names for unmapped records
- ✅ **Comprehensive data flow** ensures all records proceed through cost/efficiency calculations

### 📊 **Technical Enhancements**
- Detailed capacity comparison logging for transparency
- Enhanced error handling and validation
- Improved data integrity throughout the processing pipeline

## [2.0.0] - 2025-07-28

### 🚀 **Major New Features**

#### **Git Integration & Version Control**
- ✅ **Automatic branch creation** for each country (JPN, DEU, USA, etc.)
- ✅ **Clean branch isolation** - each branch contains ONLY one country's model
- ✅ **Automatic commit and push** to remote repository
- ✅ **Professional version control** workflow for energy modeling
- ✅ **Enhanced error handling** for Git operations with fallback modes

#### **GDX File Reading & Analysis**
- ✅ **GAMS GDX file support** using `gdxpds` library
- ✅ **Pattern-based data extraction** (e.g., `EN_ZGas*` processes)
- ✅ **Excel export capabilities** for GDX data analysis
- ✅ **Interactive Jupyter notebook** (`gdxdiff.ipynb`) for GDX exploration
- ✅ **Advanced search functions** for symbol names and data content

#### **Enhanced VEDA Model Creation**
- ✅ **Complete model folder structure** with all required files
- ✅ **Country-specific mappings** (KOR → Asia_east, DEU → Germany, etc.)
- ✅ **Automatic system settings** with formula refresh
- ✅ **Scenario file generation** (NGFS, Base VS, Time Series Parameters)
- ✅ **Resource file updates** with regional mappings

### 🔧 **Technical Improvements**

#### **Code Structure**
- ✅ **Enhanced `veda_model_creator.py`** with Git integration
- ✅ **Robust Git command handling** with PATH fallback
- ✅ **Improved error handling** and logging
- ✅ **Modular function design** for easy maintenance

#### **Performance**
- ✅ **Faster Git operations** with optimized branch management
- ✅ **Efficient file handling** with proper cleanup
- ✅ **Reduced memory usage** through better data structures

### 📊 **New Workflows**

#### **Complete End-to-End Pipeline**
```bash
python main.py --iso JPN
```
**Single command now:**
1. ✅ Processes all energy data (existing stock, calibration, CCS, renewables, WEO, IAMC)
2. ✅ Creates clean Git branch `JPN`
3. ✅ Generates complete VEDA model
4. ✅ Commits to Git with timestamp
5. ✅ Pushes to remote repository

#### **GDX Analysis Workflow**
```python
# Interactive analysis
# Open gdxdiff.ipynb

# Programmatic analysis
from gdxdiff import search_gdx_for_pattern
results = search_gdx_for_pattern(gdx_data, 'EN_ZGas*')
```

### 🎯 **Key Benefits**

#### **Professional Workflow**
- ✅ **Version control** for all energy models
- ✅ **Branch isolation** prevents conflicts
- ✅ **Automatic backup** to remote repository
- ✅ **Collaborative development** ready

#### **Enhanced Analysis**
- ✅ **GDX file support** for GAMS integration
- ✅ **Pattern search** for specific technologies
- ✅ **Excel export** for further analysis
- ✅ **Interactive exploration** capabilities

#### **Improved Reliability**
- ✅ **Robust error handling** with fallback modes
- ✅ **Git PATH detection** for different environments
- ✅ **Clean branch management** prevents corruption
- ✅ **Comprehensive logging** for debugging

### 📁 **File Structure Updates**

#### **New Files**
- ✅ `gdxdiff.ipynb` - GDX analysis notebook
- ✅ `CHANGELOG.md` - This changelog
- ✅ Enhanced `requirements.txt` with `gdxpds`

#### **Updated Files**
- ✅ `veda_model_creator.py` - Git integration
- ✅ `README.md` - Comprehensive documentation
- ✅ `main.py` - Enhanced workflow

### 🔄 **Migration from v1.0**

#### **Backward Compatibility**
- ✅ **All existing functionality** preserved
- ✅ **Fallback modes** when Git unavailable
- ✅ **Same command interface** with new options

#### **New Commands**
```bash
# New Git-enabled workflow
python main.py --iso JPN

# Disable Git (fallback to v1.0 behavior)
python main.py --iso JPN --no-git

# GDX analysis
python -c "from gdxdiff import read_gdx_symbol; print(read_gdx_symbol('file.gdx', 'ACT_COST'))"
```

### 🎉 **Success Metrics**

#### **Tested Countries**
- ✅ **JPN** (Japan) - Complete workflow
- ✅ **DEU** (Germany) - Complete workflow  
- ✅ **KOR** (Korea) - Complete workflow
- ✅ **GBR** (Great Britain) - Complete workflow
- ✅ **RUS** (Russia) - Model creation verified

#### **Git Operations**
- ✅ **Branch creation** - Working
- ✅ **Commit operations** - Working
- ✅ **Push to remote** - Working
- ✅ **Branch isolation** - Verified

#### **GDX Operations**
- ✅ **File reading** - Working
- ✅ **Pattern search** - Working
- ✅ **Excel export** - Working
- ✅ **Interactive analysis** - Working

---

## [1.0.0] - 2025-07-27

### **Initial Release**
- ✅ Basic VEDA model creation
- ✅ Global data processing
- ✅ Multi-country support
- ✅ Excel file generation
- ✅ Caching system 