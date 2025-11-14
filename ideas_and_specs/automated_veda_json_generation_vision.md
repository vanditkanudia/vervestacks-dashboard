# Automated VEDA JSON Generation Vision

## Overview
This document outlines the approach to automatically generate and update VEDA's `groups.json` and `cases.json` files as part of the VerveStacks model creation pipeline, ensuring seamless integration between our parameterized timeslice system and VEDA's interface.

## Current Manual Process vs. Automated Vision

### Current State (Manual)
1. VerveStacks generates timeslice parameter files in `SuppXLS/` folder
2. User manually updates `groups.json` to reflect available timeslice configurations
3. User manually updates `cases.json` to create runnable cases for each configuration
4. Potential for inconsistencies and missing configurations

### Automated Vision
1. VerveStacks generates timeslice parameter files
2. **Automatic detection** of created timeslice files
3. **Dynamic generation** of `groups.json` with proper scenario groups
4. **Dynamic generation** of `cases.json` with ready-to-run cases
5. **Consistent naming** and descriptions across all configurations

## Implementation Strategy

### 1. Integration Point in Model Creation Pipeline

**Location**: `veda_model_creator.py` - after timeslice parameter files are written

```python
def create_veda_model(input_iso, tsopt, grid_modeling=False, no_git=False):
    # ... existing model creation logic ...
    
    # After timeslice files are created
    if success:
        # Generate VEDA interface files
        veda_json_generator = VedaJsonGenerator(dest_folder, input_iso)
        veda_json_generator.generate_groups_and_cases()
    
    return success
```

### 2. New VedaJsonGenerator Class

**File**: `veda_json_generator.py` (new utility module)

#### Core Responsibilities:
- **Scan SuppXLS folder** for existing timeslice parameter files
- **Generate groups.json** with scenario groups for each configuration
- **Generate cases.json** with runnable cases for each configuration
- **Maintain consistent naming** and ID assignment
- **Preserve existing non-timeslice groups** (FACETS, NGFS, etc.)

#### Key Methods:

```python
class VedaJsonGenerator:
    def __init__(self, model_folder, iso_code):
        self.model_folder = Path(model_folder)
        self.iso_code = iso_code
        self.appdata_folder = self.model_folder / "AppData"
        
    def generate_groups_and_cases(self):
        """Main orchestrator method"""
        timeslice_files = self._scan_timeslice_files()
        self._generate_groups_json(timeslice_files)
        self._generate_cases_json(timeslice_files)
        
    def _scan_timeslice_files(self):
        """Scan SuppXLS folder for timeslice parameter files"""
        # Return list of detected files with metadata
        
    def _generate_groups_json(self, timeslice_files):
        """Generate complete groups.json"""
        # Preserve existing non-timeslice groups
        # Generate scenario groups for each timeslice configuration
        
    def _generate_cases_json(self, timeslice_files):
        """Generate complete cases.json"""
        # Create runnable cases for each timeslice configuration
```

### 3. Timeslice File Detection Logic

#### Pattern Recognition:
```python
def _classify_timeslice_file(self, filename):
    """Classify timeslice files by type and extract metadata"""
    
    patterns = {
        'stress_daily': r'scen_tsparameters_s(\d+)p(\d+)v(\d+)_d\.xlsx',
        'stress_weekly': r'scen_tsparameters_s(\d+)_w\.xlsx', 
        'stress_mixed': r'scen_tsparameters_s(\d+)_w_p(\d+)_d\.xlsx',
        'clustering': r'scen_tsparameters_ts(\d+)_clu\.xlsx',
        'vs_mappings': r'scen_tsparameters_ts_(\d+|annual)\.xlsx'
    }
    
    # Return classification and parameters for naming/description
```

#### Metadata Extraction:
- **File type** (stress-based, clustering, VS mappings)
- **Configuration parameters** (scarcity/surplus/volatile counts, slice counts)
- **Complexity level** (for ordering and grouping)

### 4. Dynamic Groups.json Generation

#### Template Structure:
```python
def _create_scenario_group(self, timeslice_config):
    """Create scenario group for a timeslice configuration"""
    
    base_scenarios = [
        {"Name": "BASE", "Checked": True, "RowOrder": 0, "ShortName": "B"},
        {"Name": "New_RE_and_Conventional", "Checked": True, "RowOrder": 2, "ShortName": "SR"},
        {"Name": "SysSettings", "Checked": True, "RowOrder": 3, "ShortName": "SS"},
        {"Name": "Base_VS", "Checked": True, "RowOrder": 4, "ShortName": "RS"},
        {"Name": "advanced_features", "Checked": True, "RowOrder": 5, "ShortName": "RS"}
    ]
    
    # Add all timeslice scenarios with only target one checked
    timeslice_scenarios = self._generate_timeslice_scenario_list(timeslice_config)
    
    return {
        "SavedGroupId": self._get_next_group_id(),
        "GroupName": f"ref_{timeslice_config.name}",
        "GroupType": "Scenario",
        "Settings": json.dumps(base_scenarios + timeslice_scenarios),
        "CreatedOn": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "DisplayCreatedOn": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "UserName": "vervestacks_auto"
    }
```

#### AllScenario Group Management:
- **Preserve existing base scenarios** (BASE, New_RE_and_Conventional, etc.)
- **Dynamically add all detected timeslice scenarios**
- **Maintain proper RowOrder** and metadata

### 5. Dynamic Cases.json Generation

#### Case Template:
```python
def _create_case(self, timeslice_config, scenario_group_id):
    """Create runnable case for a timeslice configuration"""
    
    description_map = {
        'stress_daily': f"NGFS scenarios with {config.name} stress-based timeslice definition",
        'stress_weekly': f"NGFS scenarios with {config.name} weekly stress timeslice definition", 
        'stress_mixed': f"NGFS scenarios with {config.name} mixed daily/weekly stress timeslice definition",
        'clustering': f"NGFS scenarios with {config.name} traditional clustering timeslice definition",
        'vs_mappings': f"NGFS scenarios with {config.name} timeslice definition"
    }
    
    return {
        "CaseId": self._get_next_case_id(),
        "Name": f"vstacks_{timeslice_config.name}",
        "Description": description_map[timeslice_config.type],
        "ScenarioGroup": f"ref_{timeslice_config.name}",
        "ScenarioGroupId": scenario_group_id,
        # ... standard VEDA case structure ...
    }
```

#### ID Management:
- **Scan existing cases** to determine next available CaseId
- **Scan existing groups** to determine next available SavedGroupId
- **Avoid conflicts** with manually created cases/groups

### 6. Preservation of Existing Data

#### Smart Merging Strategy:
```python
def _preserve_existing_data(self, existing_json, new_data, preserve_types):
    """Preserve non-timeslice groups/cases while updating timeslice ones"""
    
    # Keep existing non-timeslice items
    preserved_items = [
        item for item in existing_json 
        if not self._is_timeslice_related(item)
    ]
    
    # Add new timeslice items
    return preserved_items + new_data
```

#### Backup Strategy:
- **Create backup** of existing JSON files before modification
- **Rollback capability** if generation fails
- **Validation** of generated JSON structure

### 7. Configuration and Customization

#### Configuration File: `config/veda_json_config.yaml`
```yaml
veda_json_generation:
  enabled: true
  backup_existing: true
  
  case_defaults:
    ending_year: "2050"
    solver: "cplex"
    solver_option_file: "BA121-7"
    gams_source_folder: "GAMS_SrcTIMES.v4.9.0"
    periods_definition: "msy7_2050"
    
  group_defaults:
    user_name: "vervestacks_auto"
    
  naming_conventions:
    case_prefix: "vstacks_"
    group_prefix: "ref_"
```

### 8. Error Handling and Validation

#### Robust Error Management:
- **File existence validation** before processing
- **JSON structure validation** after generation
- **Graceful degradation** if VEDA files can't be updated
- **Detailed logging** of generation process

#### Validation Checks:
```python
def _validate_generated_json(self, json_data, json_type):
    """Validate generated JSON structure"""
    
    required_fields = {
        'groups': ['SavedGroupId', 'GroupName', 'GroupType', 'Settings'],
        'cases': ['CaseId', 'Name', 'ScenarioGroup', 'ScenarioGroupId']
    }
    
    # Validate structure and required fields
    # Check for duplicate IDs
    # Verify JSON serialization
```

### 9. Integration Testing Strategy

#### Test Scenarios:
1. **Fresh model creation** - Generate complete JSON files
2. **Model update** - Preserve existing, add new configurations  
3. **Partial timeslice set** - Handle missing configurations gracefully
4. **Existing manual customizations** - Preserve user modifications

#### Validation Points:
- **VEDA can load** generated JSON files without errors
- **All timeslice configurations** appear in VEDA interface
- **Cases execute successfully** with correct scenario combinations
- **No duplicate IDs** or naming conflicts

### 10. Future Enhancements

#### Advanced Features:
- **Custom case templates** for different analysis types (FACETS, validation, etc.)
- **Batch case generation** for multiple parametric combinations
- **VEDA project file generation** for complete automation
- **Integration with Git workflow** for version control of VEDA configurations

#### User Interface:
- **Command-line flags** to control JSON generation (`--update-veda`, `--no-veda`)
- **Configuration validation** before model creation
- **Status reporting** of VEDA integration success

## Benefits of Automation

### For Users:
- **Zero manual configuration** - VEDA interface ready immediately
- **Consistent experience** across all country models
- **No missing configurations** - all generated timeslices available
- **Reduced errors** from manual JSON editing

### For Development:
- **Maintainable system** - changes to timeslice system automatically reflected
- **Scalable approach** - works for any number of timeslice configurations
- **Version control friendly** - automated generation ensures consistency
- **Testing integration** - VEDA functionality can be automatically validated

## Implementation Priority

### Phase 1: Core Functionality
1. Basic file scanning and classification
2. Groups.json generation with scenario groups
3. Cases.json generation with basic cases
4. Integration into model creation pipeline

### Phase 2: Robustness
1. Existing data preservation
2. Error handling and validation
3. Configuration system
4. Backup and rollback

### Phase 3: Advanced Features
1. Custom templates and configurations
2. Batch processing capabilities
3. Enhanced user interface
4. Integration testing automation

This automated approach ensures that VerveStacks' powerful parameterized timeslice system is immediately accessible through VEDA's user-friendly interface, bridging the gap between our advanced temporal modeling capabilities and practical usability for energy system analysts.
