# Comprehensive Versioning System for VerveStacks Energy Models

## Vision

VerveStacks energy models will be hosted on a public GitHub repository and updated periodically. Users need complete transparency about what has changed between versions. This document outlines a comprehensive versioning system that serves both technical developers and end users of the energy models.

## Core Principles

1. **Complete Transparency**: Users should know exactly what has changed in each version
2. **Multi-Audience**: Serve both technical developers and energy model users
3. **Automated Where Possible**: Reduce manual overhead while maintaining quality
4. **Public Accountability**: Changes are documented for peer review and validation
5. **Model Traceability**: Track data sources, methodology changes, and feature evolution

## Three-Tier Versioning System

### Tier 1: Git Commit Messages (Developer-Focused)
**Purpose**: Technical change tracking for development team
**Audience**: Developers, contributors, technical reviewers

**Format**:
```
Remove hasattr() defensive programming across codebase

- Remove hasattr() checks for grid_modeling attribute in excel_manager.py
- Remove hasattr() checks for data availability in iso_processing_functions.py  
- Remove hasattr() checks in veda_model_creator.py, time_slice_processor.py
- Code now fails fast and loud instead of silent fallbacks
- Critical for energy model generation reliability

Files changed: 5
Impact: All models - improved error detection
```

**Standards**:
- Imperative mood ("Add", "Fix", "Remove")
- Detailed technical context
- File-level change tracking
- Impact assessment

### Tier 2: VERSION_LOG.md (User-Focused)
**Purpose**: User-facing changelog for model consumers
**Audience**: Energy analysts, researchers, policy makers, model users

**Location**: Included in every model folder distributed to users
**Format**:
```markdown
# VerveStacks Model Version Log

## Version 2.1.0 (2025-01-21)

### Data Updates
- **NGFS Scenarios**: Added REMIND-MAgPIE 3.2-4.6 model data alongside MESSAGEix-GLOBIOM
- **Median Calculations**: New median values across models for each scenario/variable combination
- **Electricity Trade Data**: Updated interconnection capacity data from EMBER 2024 release

### Model Features  
- **Grid Modeling**: Enhanced electricity trade constraints with import/export specific limits
- **Renewable Energy Zones**: Improved spatial distribution for solar and wind resources
- **Time Slice Design**: New stress-period identification for high VRE scenarios

### Methodology Changes
- **Data Quality**: Models now fail immediately on configuration issues (no silent errors)
- **Aggregation Logic**: Automatic exclusion of incomplete data columns from cross-model analysis
- **Capacity Factors**: Updated calculation methodology for offshore wind

### Regional Coverage
- **New Countries**: Added support for 15 additional countries in Eastern Europe
- **Enhanced Data**: Improved existing stock data for Nordic countries
- **Grid Integration**: Extended grid modeling to MISO and ERCOT regions

### Files Affected
- All country models now include NGFS median scenarios in SuppXLS/Scen_Par-NGFS.xlsx
- Enhanced grid modeling capabilities for 23 supported regions
- Updated renewable energy potential data for all models

### Known Issues
- Grid-cell level renewable data temporarily disabled (using ISO-level fallback)
- Some countries may have limited historical validation data

### Data Sources Updated
- NGFS Phase 4.2 scenarios (January 2025)
- EMBER European Electricity Review 2024
- IRENA Global Energy Transformation 2024
- GEM Global Integrated Power Database April 2025
```

**Categories**:
- **Data Updates**: New datasets, data source changes, coverage improvements
- **Model Features**: New capabilities, enhanced functionality
- **Methodology Changes**: Algorithm updates, calculation improvements
- **Regional Coverage**: Geographic expansion, country-specific improvements
- **Files Affected**: What users will see changed in their model folders
- **Known Issues**: Transparent reporting of limitations
- **Data Sources Updated**: Provenance and version tracking

### Tier 3: Model Documentation Website
**Purpose**: Public-facing version comparison and evolution tracking
**Audience**: Broader energy modeling community, academic researchers, policy institutions

**Features**:
- **Version Comparison Tables**: Side-by-side feature comparison across versions
- **Data Source Evolution**: Timeline of data source updates and improvements
- **Model Capability Matrix**: What features are available for which countries/regions
- **Methodology Documentation**: Detailed technical documentation with version history
- **Impact Assessment**: Real-world applications and validation studies per version

## Implementation Strategy

### Version Numbering: Semantic Versioning
**Format**: MAJOR.MINOR.PATCH (e.g., 2.1.0)

- **MAJOR**: Breaking changes, fundamental methodology shifts
- **MINOR**: New features, data updates, regional expansion
- **PATCH**: Bug fixes, minor corrections, documentation updates

### Automation Approach: Hybrid
1. **Git commits**: Fully manual for quality control
2. **VERSION_LOG.md**: Semi-automated
   - Template generation from tagged commits
   - Manual curation for user-friendly language
   - Quality review before release
3. **Website documentation**: Automated from VERSION_LOG.md

### Release Process
1. **Development Phase**: Regular commits with detailed technical messages
2. **Pre-Release**: Curate VERSION_LOG.md from commit history
3. **Release**: Tag version, generate model folders with VERSION_LOG.md
4. **Post-Release**: Update documentation website automatically

### Model Folder Structure
```
VerveStacks_BGR_v2.1.0/
├── VERSION_LOG.md              # User-facing changelog
├── MODEL_METADATA.json         # Machine-readable version info
├── DATA_SOURCES_MANIFEST.md    # Complete data provenance
├── SuppXLS/
│   ├── Scen_Par-NGFS.xlsx     # Enhanced with median scenarios
│   └── ...
├── SubRES_Tmpl/
└── ...
```

### Quality Assurance
- **Peer Review**: All VERSION_LOG.md entries reviewed before release
- **User Testing**: Beta releases with select user community
- **Validation Studies**: Impact assessment for major changes
- **Rollback Capability**: Clear process for reverting problematic changes

## Benefits

### For Users
- **Confidence**: Know exactly what changed and why
- **Reproducibility**: Can reference specific model versions in research
- **Planning**: Understand when to upgrade vs. maintain current version
- **Transparency**: Full visibility into data sources and methodology

### For Developers
- **Accountability**: Clear change tracking and impact assessment
- **Collaboration**: Structured approach to team development
- **Quality Control**: Systematic review process
- **Community Building**: Public development process builds trust

### For the Energy Modeling Community
- **Open Science**: Transparent model evolution
- **Best Practices**: Example of comprehensive model versioning
- **Reproducible Research**: Citable, versioned model releases
- **Collaborative Development**: Community can contribute and track improvements

## Success Metrics

1. **User Adoption**: Download and usage statistics per version
2. **Community Engagement**: GitHub issues, discussions, contributions
3. **Academic Citations**: Research papers citing specific model versions
4. **Transparency Index**: User feedback on clarity and completeness of change documentation
5. **Development Velocity**: Time from feature development to user deployment

## Future Enhancements

- **Automated Testing**: Version-to-version validation suites
- **Impact Visualization**: Graphical representation of model evolution
- **User Feedback Integration**: Systematic collection and response to user needs
- **API Versioning**: Programmatic access to version history and metadata
- **Collaborative Validation**: Community-driven model validation and improvement

---

*This versioning system ensures that VerveStacks maintains the highest standards of transparency and accountability while enabling rapid development and deployment of critical energy system models for global decarbonization efforts.*
