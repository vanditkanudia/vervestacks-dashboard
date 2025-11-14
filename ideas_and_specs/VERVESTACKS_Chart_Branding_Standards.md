# 🔒 VERVESTACKS Chart Branding Standards & Implementation Guide

**Date Created:** December 19, 2024  
**Scope:** All VERVESTACKS visual outputs (2_ts_design, model, grids)  
**Status:** ACTIVE STANDARDS - Apply consistently across all modules  
**Purpose:** Comprehensive guide for AI agents and developers to implement consistent branding

---

## 🎯 QUICK START FOR AI AGENTS

### **What This Document Provides:**
1. **Complete branding rules** - All values, colors, fonts, sizes
2. **Implementation patterns** - Step-by-step code templates
3. **Common issues & solutions** - Debugging guide
4. **Quality assurance checklist** - Verification steps

### **When to Use This Document:**
- Creating new charts in any VERVESTACKS module
- Modifying existing chart styling
- Debugging branding inconsistencies
- Training AI agents on VERVESTACKS standards

---

## 📋 BRANDING SYSTEM ARCHITECTURE

### **Core Files (Single Source of Truth):**
- **`config/branding_config.yaml`** - ALL branding values and rules
- **`branding_manager.py`** - Python class that applies branding
- **`assets/logos/`** - Logo assets directory

### **Key Principle:**
**NEVER hardcode styling values in individual scripts. Everything comes from `branding_config.yaml`.**

---

## 🎨 COMPLETE BRANDING VALUES

### **Typography System:**
```yaml
fonts:
  primary: "Verdana"
  weights: ALL set to "normal" (NO bold anywhere)
  sizes:
    title: 16          # Main chart title (in header)
    subtitle: 12       # Figure suptitle
    heading: 12        # Subplot titles
    body: 12           # General text
    labels: 5.5        # Axis labels
    axis: 7            # Tick labels
    legend: 10         # Legend text
    numbers: 10        # Number formatting
```

### **Color Palette:**
```yaml
colors:
  primary: "#FD275E"      # Bright pink/fuchsia (main brand)
  secondary: "#FD626B"    # Coral/salmon pink
  accent: "#FD994C"       # Bright orange
  
  neutral:
    text: "#212529"       # Default text color
    light_gray: "#F8F9FA" # Header background
    gray: "#E9ECEF"       # Grid lines
    dark_gray: "#6C757D"  # Secondary text
  
  coverage_gradients:
    extreme_shortage: "#FD275E"    # Red
    shortage: "#FD626B"            # Pink
    moderate: "#FD994C"            # Orange
    adequate: "#00D8A2"            # Green
    surplus: "#02A9F4"             # Blue
    no_data: "#F8F9FA"            # Light gray
```

### **Chart Dimensions & Layout:**
```yaml
chart_styling:
  standard_figsize: [11, 7]       # Default for most charts
  header_band:
    height_frac: 0.08             # Header height as fraction
    background: "#F8F9FA"         # Light gray
    title_color: "#FD275E"        # Brand primary
    title_size: 20                # Header title size
  
  logos:
    target_height_px: 22          # Fixed logo height
    left_logo_pos: [0.08, 0.96]  # Left logo coordinates
    right_logo_pos: [0.92, 0.96] # Right logo coordinates
```

---

## 🚀 IMPLEMENTATION PATTERNS

### **Standard Chart Creation Template:**
```python
# 1. Import and initialize
from branding_manager import VerveStacksBrandingManager
branding_manager = VerveStacksBrandingManager()

# 2. Create figure with standard size
fig, axes = plt.subplots(rows, cols, figsize=(11, 7))

# 3. Apply initial branding to all subplots
for ax in axes.flatten():
    branding_manager.apply_chart_style(ax, "chart_type")

# 4. Apply figure-level styling
branding_manager.apply_figure_style(fig)

# 5. CREATE ALL CHART ELEMENTS (this may override font sizes)
ax.set_xlabel('Label Text')
ax.set_ylabel('Label Text') 
ax.tick_params(axis='x', rotation=45, labelsize=7)  # Include labelsize!
# ... all other chart elements ...

# 6. CRITICAL: Finalize styling after all elements are set
for ax in axes.flatten():
    branding_manager.finalize_chart_style(ax)  # Re-applies font sizes

# 7. Add logos and main title
branding_manager.add_logos_to_chart(fig, "small", f"Chart Title - {country_name}")

# 8. Save with proper padding and close
plt.savefig(path, dpi=300, bbox_inches=None, pad_inches=0.2)
plt.close()  # Prevent auto-opening
```

### **Country Name Mapping (Required for All Charts):**
```python
def _get_country_name(self, iso_code):
    country_names = {
        'CHE': 'Switzerland', 'JPN': 'Japan', 'USA': 'United States',
        'DEU': 'Germany', 'FRA': 'France', 'GBR': 'United Kingdom',
        'ITA': 'Italy', 'ESP': 'Spain', 'CAN': 'Canada',
        'AUS': 'Australia', 'BRA': 'Brazil', 'IND': 'India',
        'CHN': 'China', 'RUS': 'Russia', 'ZAF': 'South Africa'
    }
    return country_names.get(iso_code, iso_code)

# Use in all chart titles:
title = f"Chart Title - {self._get_country_name(iso_code)}"
```

---

## 🚨 CRITICAL IMPLEMENTATION RULES

### **🚫 NEVER DO THESE:**
1. **Hardcode font sizes:** `fontsize=12`, `labelsize=10`
2. **Use bold text:** `fontweight='bold'`
3. **Add dark edges:** `edgecolor='black'`, `linewidth=0.5`
4. **Override branding:** Any manual styling that conflicts with config
5. **Use ISO codes in titles:** Always use country names

### **✅ ALWAYS DO THESE:**
1. **Import branding_manager:** `from branding_manager import VerveStacksBrandingManager`
2. **Apply to all subplots:** Loop through `axes.flatten()`
3. **Call finalize_chart_style:** AFTER setting all chart elements
4. **Use country names:** In all user-facing titles
5. **Include labelsize:** When using `tick_params()`
6. **Close plots:** `plt.close()` after saving

---

## 🔧 COMMON ISSUES & SOLUTIONS

### **Issue 1: Font Sizes Reset to Defaults**
**Problem:** Manual `set_xlabel()`, `set_ylabel()`, `tick_params()` override branding
**Solution:** Call `finalize_chart_style()` AFTER all chart elements are set

### **Issue 2: Charts Auto-Open in Viewer**
**Problem:** Missing `plt.close()` after saving
**Solution:** Always add `plt.close()` after `plt.savefig()`

### **Issue 3: Tick Parameters Override Font Sizes**
**Problem:** `tick_params(axis='x', rotation=45)` resets fonts
**Solution:** Always include `labelsize`: `tick_params(axis='x', rotation=45, labelsize=7)`

### **Issue 4: Logo Positioning Issues**
**Problem:** Logos too close to edges or overlapping
**Solution:** Adjust `left_logo_pos` and `right_logo_pos` in config

### **Issue 5: Header Band Too Small**
**Problem:** Title text overlapping with chart content
**Solution:** Increase `header_band.height_frac` in config

---

## 📊 CHART TYPE SPECIFIC GUIDELINES

### **Calendar Heatmap:**
```python
# Special considerations:
- Use `create_coverage_colormap()` from branding manager
- Implement scale buster (cap values > 125% at 125%)
- Position statistics box above legend
- Use `aspect='equal'` for square cells
```

### **Multi-Subplot Charts (like aggregation_justification):**
```python
# Layout considerations:
- Use `gridspec_kw={'height_ratios': [0.4, 0.6]}` for row control
- Position legends below rows with `bbox_to_anchor`
- Rotate x-axis labels: `rotation=45, ha='right'`
- Unified legends for related subplots
```

### **Line/Bar Charts:**
```python
# Standard styling:
- Figure size: (11, 7)
- Grid lines: light gray, alpha=0.3
- Borders: removed for clean look
- Legend positioning: avoid overlapping with data
```

---

## 🧪 TESTING & VERIFICATION

### **Test Checklist for New Charts:**
- [ ] Chart opens without errors
- [ ] All text uses correct font sizes from config
- [ ] No bold text anywhere
- [ ] Logos appear in correct positions
- [ ] Header band displays properly
- [ ] Country name shows (not ISO code)
- [ ] Chart saves without cropping
- [ ] No auto-opening in viewer
- [ ] Colors match branding palette
- [ ] Figure size is (11, 7) or appropriate

### **Test with Sample Country:**
```python
# Always test with CHE (Switzerland) first
python script.py --iso CHE
# Verify output files are generated correctly
```

---

## 🔄 MAINTENANCE & UPDATES

### **Making Branding Changes:**
1. **Edit `config/branding_config.yaml`** - Change values here
2. **Test with sample chart** - Verify changes apply correctly
3. **Update this document** - Keep implementation guide current
4. **Deploy to all modules** - Apply consistently across platform

### **Adding New Chart Types:**
1. **Define styling in config** - Add new section under `chart_types`
2. **Update branding_manager** - Add specific styling methods if needed
3. **Document here** - Add implementation notes to this guide
4. **Test thoroughly** - Verify with multiple countries

---

## 📚 COMPLETE CODE EXAMPLES

### **Simple Single Chart:**
```python
import matplotlib.pyplot as plt
from branding_manager import VerveStacksBrandingManager

def create_simple_chart(iso_code, data, output_path):
    # Initialize branding
    branding_manager = VerveStacksBrandingManager()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(11, 7))
    
    # Apply branding
    branding_manager.apply_chart_style(ax, "line_chart")
    branding_manager.apply_figure_style(fig)
    
    # Create chart
    ax.plot(data)
    ax.set_xlabel('Time')
    ax.set_ylabel('Value')
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    
    # Finalize styling
    branding_manager.finalize_chart_style(ax)
    
    # Add branding elements
    country_name = branding_manager._get_country_name(iso_code)
    branding_manager.add_logos_to_chart(fig, "small", f"Simple Chart - {country_name}")
    
    # Save and close
    plt.savefig(output_path, dpi=300, bbox_inches=None, pad_inches=0.2)
    plt.close()
```

### **Multi-Subplot Chart:**
```python
def create_multi_subplot_chart(iso_code, data, output_path):
    branding_manager = VerveStacksBrandingManager()
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(11, 7))
    
    # Apply branding to all subplots
    for ax in axes.flatten():
        branding_manager.apply_chart_style(ax, "scenario_analysis")
    
    branding_manager.apply_figure_style(fig)
    
    # Create chart elements
    # ... chart creation code ...
    
    # Finalize styling
    for ax in axes.flatten():
        branding_manager.finalize_chart_style(ax)
    
    # Add branding
    country_name = branding_manager._get_country_name(iso_code)
    branding_manager.add_logos_to_chart(fig, "small", f"Multi Chart - {country_name}")
    
    # Save and close
    plt.savefig(output_path, dpi=300, bbox_inches=None, pad_inches=0.2)
    plt.close()
```

---

## 🎯 QUALITY ASSURANCE CHECKLIST

### **Before Deploying Any Chart:**
- [ ] All hardcoded `fontsize` parameters removed
- [ ] All `fontweight='bold'` parameters removed  
- [ ] All `edgecolor` parameters removed
- [ ] Country names used instead of ISO codes
- [ ] `branding_manager` imported and applied
- [ ] Figure size standardized to `(11, 7)` or appropriate
- [ ] Header band and logos properly displayed
- [ ] Save parameters use `bbox_inches=None, pad_inches=0.2`
- [ ] Chart styling applied to all subplots
- [ ] Typography hierarchy respected
- [ ] **`finalize_chart_style()` called AFTER all chart elements**
- [ ] **`plt.close()` added after `plt.savefig()`**
- [ ] **`show_chart=False` parameter used in chart generation calls**
- [ ] **`tick_params()` includes `labelsize` parameter when used**

---

## 🚀 NEXT STEPS FOR AI AGENTS

### **When Implementing New Charts:**
1. **Read this document completely** - Understand all rules
2. **Check `branding_config.yaml`** - Verify current values
3. **Use implementation templates** - Copy and modify existing patterns
4. **Test with sample data** - Verify branding applies correctly
5. **Update documentation** - Add any new patterns discovered

### **When Debugging Issues:**
1. **Check common issues section** - Look for known problems
2. **Verify config values** - Ensure YAML is correct
3. **Test step by step** - Apply branding incrementally
4. **Compare with working examples** - Use existing charts as reference

---

## 📈 IMPACT & BENEFITS

This system ensures **100% consistency** across all VERVESTACKS outputs for:
- **Clients:** Professional, branded presentations
- **Stakeholders:** Clear, readable country identification  
- **Publications:** Consistent visual standards for academic/industry papers
- **AI Agents:** Clear implementation guidelines and troubleshooting

---

**Last Updated:** December 19, 2024  
**Applied To:** 2_ts_design module (stress_period_analyzer.py, 8760_supply_demand_constructor.py, RE_Shapes_Analysis_v5.py)  
**Next Target:** model and grids modules  
**AI Agent Ready:** ✅ Comprehensive implementation guide provided

**🔧 CRITICAL UPDATES (Latest Session):**
- Complete rewrite for AI agent consumption
- Added comprehensive implementation patterns
- Included all common issues and solutions
- Provided complete code examples
- Added quality assurance checklist
- Made document single source of truth for implementation
