# Veda2.0 Reports Processing Documentation

## Overview

Veda2.0's reports processing system is a sophisticated data transformation pipeline that converts raw TIMES/VEDA model results (VD files) into structured, analyzed reports through tag-based configuration. The system uses PostgreSQL stored procedures to process data through multiple stages, applying aggregations, transformations, and enrichments based on user-defined report definitions.

## Architecture Components

### 1. Core Database Schemas
- **`veda_front_end`**: Contains stored procedures and metadata tables
- **Report Schemas**: Individual schemas created for each report (format: `report_<study>_<user>`)
- **`veda_front_end_data`**: Contains master tables for reports management

### 2. Key Data Structures

#### Report Definition Files (LMADefs)
Excel files containing tag-based configurations that define:
- **TS_Defs**: Variable definitions with show/discard logic
- **TS_Ratios**: Ratio calculations between variables
- **Process_Map/Commodity_Map**: Dimension classifications
- **ScenG/ScenMap**: Scenario groupings and mappings
- **Geolocation**: Geographic coordinates for spatial analysis

#### Core Data Tables
- **`lma_dts`**: Main results table containing processed data
- **`lma_rpca`**: Report Process-Commodity-Attribute definitions
- **`scenario_master`**: Scenario metadata and file references
- **Dimension mapping tables**: Process_map, commodity_map, region, etc.

## Processing Pipeline

### Phase 1: Schema and Table Creation
**Stored Procedure**: `usp_reports_create_new_schema`

Creates a new report schema with:
- Core tables (scenario_master, gdx_master, lma_dts)
- Dimension mapping tables (process_map, commodity_map, region, topology)
- Staging tables for data processing
- Views for data access and validation

### Phase 2: Tag Import and Processing
**Stored Procedure**: `usp_dts_import_set_rules_and_lmadefs_tags`

- Imports LMADefs tags from source model
- Creates tag-specific tables based on definitions
- Processes SetRules and SysSettings configurations
- Sets up sankey_attribute mappings in lma_rpca for flow visualization

### Phase 3: Scenario Table Creation
**Stored Procedure**: `usp_lma_dts_create_and_get_scenario_tables`

- Creates temporary scenario-specific tables
- Generates processing queries for each scenario
- Sets up dimension change tracking tables
- Prepares trade flow processing queries

### Phase 4: Individual Scenario Processing
**Stored Procedure**: `usp_lma_dts_process_scenario`

For each scenario:
1. **Data Extraction**: Joins VD file data with report definitions (lma_rpca)
2. **Dimension Processing**: Applies show_me/discard logic from TS_Defs
3. **Aggregation**: Groups data according to specified dimensions
4. **Downscaling**: Applies geographic downscaling if configured
5. **Unit Substitution**: Replaces `<unit>`, `<region>` placeholders in variable names
6. **Weighted Averages**: Calculates weighted averages for linked attributes

Key features:
- Supports three downscaling modes (-1: none, 0: standard, 1: inherit)
- Handles dynamic variable name transformations
- Processes both regular and weighted average calculations

### Phase 5: Specialized Processing

#### Sankey Diagram Processing
**Stored Procedures**:
- `usp_dts_sankey_data_preparation_auto`
- `usp_dts_sankey_validation_cycle_detection`

**Sankey Data Preparation** (`usp_dts_sankey_data_preparation_auto`):
- Automatically processes variables with `_src_` and `_snk_` patterns
- Extracts source, target, and source_use information from variable names
- Creates flow relationships for Sankey diagram visualization
- Updates dimension mappings to include Sankey-specific columns (source, target, source_use, attribute)
- Links variables to their sankey_attribute from lma_rpca definitions

**Sankey Cycle Detection** (`usp_dts_sankey_validation_cycle_detection`):
- Validates Sankey flow networks for circular dependencies
- Uses recursive algorithms to detect cycles in source-target relationships
- Builds temporary tables to map node relationships and paths
- Returns paths that contain cycles for validation and correction
- Ensures data integrity for flow visualization

Key Sankey Features:
- **Automatic Pattern Recognition**: Identifies `_src_` and `_snk_` variables automatically
- **Flow Relationship Mapping**: Extracts source-target relationships from variable names
- **Cycle Detection**: Prevents infinite loops in flow diagrams
- **Attribute Linking**: Connects flow variables to their sankey_attribute definitions

#### Trade Flow Processing
**Stored Procedures**: 
- `usp_lma_dts_trades_for_gis`
- `usp_lma_dts_trades_for_gis_osemosys_only`

Generates trade flow data for GIS visualization using geolocation information.

#### Unit Conversion
**Stored Procedure**: `usp_dts_varbl_unit_conversion`

Applies unit conversions before ratio processing, supporting:
- Standard unit conversion tables
- Dynamic unit substitution in variable names

#### Ratio Processing
**Stored Procedure**: `usp_dts_ts_ratios_processing`

Processes TS_Ratios tag definitions:
- **Standard ratios**: numerator/denominator calculations
- **Scalar ratios**: Special case where denominator is scalar (process = '-')
- **Multiplication**: Direct multiplication of variables
- **Weighted averages**: Automatic calculation for both numerator and denominator

### Phase 6: Data Consolidation
**Stored Procedure**: `usp_dts_move_scenario_table_to_main_table`

- Aggregates data from scenario-specific tables
- Applies dimension classifications through joins
- Implements show_me logic for final output
- Moves processed data to main lma_dts table
- Uses temporary staging for WAL optimization

### Phase 7: Final Processing

#### Sankey Finalization
**Stored Procedures**:
- `usp_dts_sankey_data_preparation_auto`
- `usp_dts_sankey_validation_cycle_detection`

Finalizes Sankey diagram data preparation and validates flow networks for cycles.

#### ATS Final Processing
**Stored Procedure**: `usp_dts_ats_final_processing`

Applies ATS_final tag logic for additional data transformations.

#### Language and Color Support
**Stored Procedures**:
- `usp_lma_dts_language_processing`
- `usp_lma_dts_language_color_support`

Adds multilingual support and color mapping for visualization.

## Tag Definitions Reference

### TS_Defs (Time Series Definitions)
Defines which variables to extract and how to process dimensions:
- **show_me**: Dimensions to include in final output
- **discard**: Dimensions to exclude from processing
- **attribute**: TIMES attribute to extract
- **process/commodity/region filters**: Specify data scope

### TS_Ratios (Time Series Ratios)
Defines ratio calculations between variables:
- **var_num/var_den**: Numerator and denominator variables
- **scalar**: Special mode for scalar denominators
- **multiply**: Direct multiplication instead of division
- **include_dim**: Dimensions for joining data
- **unit**: Output unit with placeholder support (`<unit_num>`, `<unit_den>`)

### Dimension Maps
Define classifications for analysis dimensions:
- **Process_Map**: Technology/process classifications
- **Commodity_Map**: Energy carrier classifications  
- **Region_Map**: Geographic region groupings
- **Timeslice_Map**: Temporal period classifications

### ScenG/ScenMap
Define scenario groupings and display mappings:
- **ScenG**: Groups scenarios for analysis
- **ScenMap**: Maps scenario names to display names

## Data Flow Summary

```
VD Files → lma_rpca (Report Definitions) → Scenario Processing → 
Unit Conversion → Ratio Processing → Sankey Processing → 
Dimension Classification → Final Aggregation → lma_dts (Final Results)
```

## Key Features

### Performance Optimizations
- Unlogged temporary tables for intermediate processing
- WAL pressure reduction through staging
- Parallel scenario processing capability
- Efficient aggregation using temporary tables

### Flexibility
- Dynamic variable name transformations
- Configurable downscaling options
- Multiple ratio calculation modes
- Extensible tag system

### Data Quality
- Weighted average calculations
- Comprehensive error handling
- Dimension validation
- Data lineage tracking

## Usage Patterns

### Typical Report Creation Workflow
1. Create LMADefs Excel file with tag definitions
2. Import model and create report schema
3. Process scenarios through the pipeline
4. Access results through lma_dts table
5. Apply additional visualizations or exports

### Common Tag Combinations
- **TS_Defs + Process_Map**: Extract and classify technology data
- **TS_Ratios + TS_Defs**: Calculate efficiency ratios with proper grouping
- **Sankey Variables (_src_/_snk_)**: Automatic flow diagram generation
- **Geolocation + Trade processing**: Generate spatial trade flow maps
- **ScenG + ScenMap**: Create scenario comparison reports

This documentation provides a comprehensive overview of Veda2.0's reports processing system, covering the architecture, data flow, and key components that enable flexible and powerful energy system analysis reporting.
