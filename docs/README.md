# VerveStacks Energy Model Processor

A comprehensive Python project for processing global energy data, creating country-specific Veda/TIMES energy system models, and managing them with Git version control.

## 🌟 **New Features (Latest Release)**

### 🚀 **Git Integration & Branch Management**
- **Automatic branch creation** for each country (e.g., `JPN`, `DEU`, `USA`)
- **Clean branch isolation** - each branch contains ONLY one country's model
- **Automatic commit and push** to remote repository
- **Professional version control** for energy modeling workflows

### 📊 **GDX File Reading & Analysis**
- **GAMS GDX file support** using `gdxpds` library
- **Pattern-based data extraction** (e.g., `EN_ZGas*` processes)
- **Excel export capabilities** for GDX data analysis
- **Interactive Jupyter notebook** for GDX exploration

### 🏭 **Enhanced VEDA Model Creation**
- **Complete model folder structure** with all required files
- **Country-specific mappings** (e.g., `KOR → Asia_east`, `DEU → Germany`)
- **Automatic system settings** with formula refresh
- **Scenario file generation** (NGFS, Base VS, Time Series)

### 📋 **Model Transparency & Documentation**
- **Source data inclusion** (`source_data/VerveStacks_{ISO}.xlsx`) with full data reconciliation
- **Automated model notes** (`MODEL_NOTES.md`) with processing parameters and methodology
- **Curated information** on capacity thresholds, efficiency adjustments, missing capacity handling
- **Data source coverage** statistics and quality assurance metrics

## Overview

This project converts the original Jupyter notebook workflow into a structured Python application that:

- **Loads global datasets once** - IRENA, EMBER, GEM, NGFS, UNSD, WEO data
- **Processes multiple countries efficiently** - Reuses loaded data across different ISOs
- **Creates complete Veda models** - Generates ready-to-use energy system model files
- **Manages models with Git** - Automatic branch creation and version control
- **Reads and analyzes GDX files** - GAMS data format support
- **Caches processed data** - Avoids reloading large datasets on subsequent runs

## Project Structure

```
VerveStacks/
├── main.py                     # Main runner script with Git integration
├── verve_stacks_processor.py   # Main processor class (loads global data)
├── iso_processing_functions.py # ISO-specific processing functions
├── existing_stock_processor.py # Existing power plant data processing
├── veda_model_creator.py      # Veda model creation with Git integration
├── gdxdiff.ipynb              # GDX file reading and analysis notebook
├── requirements.txt           # Python dependencies (includes gdxpds)
├── data/                      # Input data files
├── assumptions/               # Mapping files and templates
├── output/                    # Generated model files
└── cache/                     # Cached processed data
```

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Git** (for version control features):
   - Windows: Download from https://git-scm.com/
   - Mac: `brew install git`
   - Linux: `sudo apt-get install git`

3. **Ensure Excel is available** (required for xlwings):
   - Windows: Microsoft Excel installed
   - Mac: Microsoft Excel installed
   - Linux: LibreOffice Calc (limited support)

## Usage

### 🚀 **Quick Start - Complete Workflow**

**Process a country with automatic Git integration:**
```bash
python main.py --iso JPN
```

**This single command:**
1. ✅ Processes all energy data (existing stock, calibration, CCS, renewables, WEO, IAMC)
2. ✅ Creates clean Git branch `JPN`
3. ✅ Generates complete VEDA model
4. ✅ Includes source data (`source_data/VerveStacks_JPN.xlsx`) with full reconciliation
5. ✅ Creates model documentation (`README.md`) with processing parameters
6. ✅ Commits to Git with timestamp
7. ✅ Pushes to remote repository

### 📊 **GDX File Analysis**

**Read and analyze GAMS GDX files:**
```python
# Open gdxdiff.ipynb for interactive analysis
# Or use the functions programmatically:

from gdxdiff import read_gdx_symbol, search_gdx_for_pattern

# Read specific symbol
data = read_gdx_symbol('your_file.gdx', 'ACT_COST')

# Search for patterns
results = search_gdx_for_pattern(gdx_data, 'EN_ZGas*')
```

### 🔍 **Advanced GDX Search**

**Search for specific processes:**
```python
# Search for gas processes
results = search_gdx_for_pattern(gdx_data, 'EN_ZGas*', search_in_data=True)

# Search for specific technology
results = search_gdx_for_pattern(gdx_data, 'EN_111_ZGasCCS_2032_AZ')
```

### 📋 **List Available Countries**
```bash
python main.py --list-isos
```

### 🔄 **Process Multiple Countries**
```bash
# Process all countries
python main.py

# Process specific countries
python main.py --iso JPN,DEU,USA
```

### 📋 **Model Documentation Features**

**Each generated model now includes:**

**Source Data File:**
- `source_data/VerveStacks_{ISO}.xlsx` - Complete data reconciliation from all sources
- Contains capacity, generation, and efficiency data from IRENA, EMBER, GEM, UNSD
- Technology mappings and data quality assessments
- Base year calibration tables

**Model Documentation:**
- `README.md` - Curated processing information (displays automatically on GitHub)
- Processing parameters (capacity thresholds, efficiency adjustments)
- Data source coverage statistics
- Methodology explanations and quality assurance notes
- Usage guidance and contact information

**Example README.md Content (displays on GitHub):**
```markdown
# VerveStacks Model Generation Notes - JPN
Generated: 2025-01-31 15:30:25

## Processing Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| Capacity Threshold | 100 MW | Minimum plant size for individual tracking |
| Gas Efficiency Adjustment | 1.0 | Multiplier applied to gas plant efficiencies |
| Time Slice Option | ts_336 | Time slice configuration used |

## Data Sources & Coverage
- Individual Plant Coverage: 85% of total capacity from plant-level GEM data
- Missing Capacity Added: 12.5 GW estimated from statistical sources
- Technology Mapping: Automated mapping using VerveStacks classifications
```

### ⚙️ **Advanced Usage**

**Custom processing with parameters:**
```bash
python main.py --iso USA --capacity-threshold 200 --efficiency-gas 1.1 --efficiency-coal 0.95
```

**Force reload of global data:**
```bash
python main.py --force-reload --iso JPN
```

**Disable Git integration (fallback mode):**
```bash
python main.py --iso JPN --no-git
```

## Git Workflow Features

### 🌿 **Branch Management**

**Automatic Branch Creation:**
- Each country gets its own branch: `JPN`, `DEU`, `USA`, etc.
- Clean isolation - only one country's model per branch
- Automatic branch switching and cleanup

**Example Branch Structure:**
```
main (or master)
├── JPN (contains only VerveStacks_JPN/)
├── DEU (contains only VerveStacks_DEU/)
├── USA (contains only VerveStacks_USA/)
└── KOR (contains only VerveStacks_KOR/)
```

### 📤 **Commit & Push Process**

**Automatic Workflow:**
1. **Create/switch to ISO branch**
2. **Empty working directory** (except `.git` and `.gitattributes`)
3. **Copy fresh model** to clean directory
4. **Commit with timestamp** (e.g., "Updated JPN model - 2025-07-28 15:30")
5. **Push to remote** with upstream tracking

**Manual Git Operations:**
```bash
# Check current branch
git branch

# Switch to specific country branch
git checkout JPN

# View commit history
git log --oneline

# Push manually if needed
git push -u origin JPN
```

## GDX File Analysis

### 📊 **Reading GDX Files**

**List all symbols:**
```python
import gdxpds
symbols = gdxpds.list_symbols('your_file.gdx')
print(f"Found {len(symbols)} symbols")
```

**Read specific symbol:**
```python
data = gdxpds.to_dataframe('your_file.gdx', 'ACT_COST')
print(data.head())
```

**Export to Excel:**
```python
from gdxdiff import export_gdx_to_excel
export_gdx_to_excel(gdx_data, 'analysis_output.xlsx')
```

### 🔍 **Pattern Search**

**Search in symbol names:**
```python
results = search_gdx_for_pattern(gdx_data, 'EN_ZGas*')
```

**Search in data content:**
```python
results = search_gdx_for_pattern(gdx_data, 'EN_111_ZGasCCS_2032_AZ', search_in_data=True)
```

## Output Files

For each processed country (e.g., JPN), the following are generated:

```
C:/Veda/Veda/Veda_models/vervestacks_models/
├── VerveStacks_JPN/               # Complete Veda model folder
│   ├── SysSettings.xlsx           # System configuration (345KB)
│   ├── vt_vervestacks_JPN_v1.xlsx # Variable table (47KB)
│   ├── ReportDefs_vervestacks.xlsx # Report definitions (29KB)
│   ├── Sets-vervestacks.xlsx      # Set definitions (12KB)
│   ├── BY_Trans.xlsx              # Base year transitions (11KB)
│   ├── README.md                  # 🆕 Processing parameters and methodology notes (displays on GitHub)
│   ├── AppData/                   # Application data
│   ├── SubRES_Tmpl/               # Resource templates
│   ├── source_data/               # 🆕 Source data and reconciliation
│   │   └── VerveStacks_JPN.xlsx   # Raw data from all sources with reconciliation
│   └── SuppXLS/                   # Scenario files
│       ├── Scen_TSParameters_108.xlsx  # Time series (2.1MB)
│       ├── Scen_TSParameters_12.xlsx   # Monthly parameters (359KB)
│       ├── Scen_Base_VS.xlsx           # Base scenario (19KB)
│       ├── Scen_Par-NGFS.xlsx          # NGFS scenarios (19KB)
│       └── Scen_UnitComm.xlsx          # Unit commitment (17KB)
```

## Performance

**First Run (with fresh data loading):**
- ~10-15 minutes (depending on data size)

**Subsequent Runs (using cache):**
- ~2-3 minutes per country

**Git Operations:**
- Branch creation: ~5-10 seconds
- Commit and push: ~10-30 seconds (depending on file size)

**Processing Multiple Countries:**
- Load data once, process many countries efficiently
- Linear scaling with number of countries
- Git operations add minimal overhead

## Configuration

### 🔧 **Key Parameters**

- **`capacity_threshold`**: MW threshold for individual plant tracking (default: 100)
- **`efficiency_adjustment_gas`**: Gas plant efficiency calibration factor (default: 1.0)  
- **`efficiency_adjustment_coal`**: Coal plant efficiency calibration factor (default: 1.0)
- **`cache_dir`**: Directory for caching processed data (default: "cache")
- **`force_reload`**: Force reload of global data (default: False)
- **`auto_commit`**: Enable Git integration (default: True)

### 🌍 **Country-Specific Mappings**

**Kinesys Region Mappings:**
- `JPN → Japan`
- `DEU → Germany` 
- `KOR → Asia_east`
- `GBR → UK`
- `USA → USA`

## Data Requirements

Ensure the following data files are available in the `data/` directory:

- `existing_stock/IRENASTAT-C.xlsx`
- `existing_stock/IRENASTAT-G.xlsx`
- `existing_stock/yearly_full_release_long_format.csv`
- `existing_stock/Global-Integrated-Power-April-2025.xlsx`
- `NGFS4.2/Downscaled_MESSAGEix-GLOBIOM 1.1-M-R12_data.xlsx`
- `technologies/ep_technoeconomic_assumptions.xlsx`
- `technologies/WEO_2024_PG_Assumptions_STEPSandNZE_Scenario.xlsb`

## Troubleshooting

### 🐛 **Git Issues**

**Git not found in PATH:**
```bash
# Windows: Install Git for Windows
# Mac: brew install git
# Linux: sudo apt-get install git
```

**Push to remote fails:**
```bash
# Check remote configuration
git remote -v

# Set upstream manually
git push -u origin BRANCH_NAME
```

**Branch conflicts:**
```bash
# Clean working directory
git reset --hard HEAD
git clean -fd
```

### 📊 **GDX File Issues**

**gdxpds installation:**
```bash
pip install gdxpds>=1.0.0
```

**File not found:**
- Ensure GDX file path is correct
- Check file permissions
- Verify file is not corrupted

### 🏭 **VEDA Model Issues**

**Excel/xlwings issues:**
- Ensure Excel is properly installed
- Close any open Excel files before running
- On Mac, try: `pip install xlwings --upgrade`

**Memory issues with large datasets:**
- Increase available RAM
- Use `--force-reload` if cache is corrupted
- Process countries individually rather than in batch

**Missing data files:**
- Check that all required files exist in `data/` directory
- Verify file permissions and paths

## Programmatic Usage

### 🔧 **Basic Usage**

```python
from verve_stacks_processor import VerveStacksProcessor

# Initialize processor (loads global data once)
processor = VerveStacksProcessor()

# Process multiple countries efficiently
for iso in ['JPN', 'DEU', 'USA', 'IND', 'CHN']:
    processor.process_iso(iso)

# See available countries
print(processor.get_available_isos())
```

### 🌿 **Git Integration**

```python
from veda_model_creator import copy_vs_iso_template

# Create model with Git integration
copy_vs_iso_template('JPN', 'output', auto_commit=True)

# Create model without Git
copy_vs_iso_template('JPN', 'output', auto_commit=False)
```

### 📊 **GDX Analysis**

```python
from gdxdiff import read_all_symbols, search_gdx_for_pattern

# Load all GDX data
gdx_data = read_all_symbols('your_file.gdx')

# Search for patterns
results = search_gdx_for_pattern(gdx_data, 'EN_ZGas*')
```

## Converting from Jupyter Notebook

This project structure **solves the key issues** from your original notebook:

**❌ Original Problems:**
- Cell 0 reloaded large datasets every time
- Inefficient for processing multiple countries
- Difficult to reuse across sessions
- No version control for models
- No GDX file analysis capabilities

**✅ Python Project Solutions:**
- Global data loaded once per session
- Cached for reuse across sessions  
- Clean separation of data loading vs. processing
- Easy to run for multiple countries efficiently
- **Git integration for model version control**
- **GDX file reading and analysis**
- **Professional workflow automation**

## Contributing

The modular structure makes it easy to extend:

- Add new data sources in `verve_stacks_processor.py`
- Add new processing functions in `iso_processing_functions.py`
- Modify Veda output format in `veda_model_creator.py`
- Add new GDX analysis functions in `gdxdiff.ipynb`
- Enhance Git workflow in `veda_model_creator.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details. 