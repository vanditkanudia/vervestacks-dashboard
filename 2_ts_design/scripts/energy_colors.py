"""
Energy Sector Standard Color Palette
====================================

Centralized color definitions following energy sector conventions for consistent
visualization across all VerveStacks timeslice analysis charts.

Color Rationale:
- Nuclear: Gold/bright yellow (clean, consistent baseload)
- Hydro: Dodger blue (water = blue, universally understood)
- Wind: Sky blue (air/sky colors, distinguishable from hydro)
- Solar: Orange-yellow (sun colors, warmer than pure yellow)

These colors ensure:
1. Industry standard recognition
2. Clear visual distinction between technologies
3. Accessibility for colorblind users
4. Professional appearance in stakeholder presentations
"""

# Standard energy sector color palette
ENERGY_COLORS = {
    'nuclear': '#FFD700',      # Gold/bright yellow
    'hydro': '#1E90FF',        # Dodger blue (water)
    'wind': '#87CEEB',         # Sky blue (distinguishable from hydro)
    'solar': '#FFA500',        # Orange-yellow (sun)
    'bioenergy': '#228B22',    # Forest green (biomass/organic)
    'biomass': '#228B22',      # Alias for bioenergy
    'coal': '#2F4F4F',         # Dark slate gray (coal/black)
    'gas': '#B39DDB',          # Light purple (distinct from coal/oil)
    'oil': '#FF0000',          # Red (for oil)
    'geothermal': '#8B4513',   # Saddle brown (earthy, geothermal)
    'windon': '#87CEEB',       # Teal (same as wind)
    'windoff': '#005B96'       # Deep blue (distinct, for offshore wind)
}

# Alternative names for compatibility
ENERGY_COLORS_ALT = {
    'Nuclear': '#FFD700',
    'Hydro': '#1E90FF', 
    'Wind': '#87CEEB',
    'Solar': '#FFA500',
    'Bioenergy': '#228B22',
    'Biomass': '#228B22',
    'Coal': '#2F4F4F',
    'Gas': '#B39DDB',
    'Oil': '#FF0000',
    'Geothermal': '#8B4513',
    'Wind Onshore': '#87CEEB',
    'Wind Offshore': '#005B96'
}

# Stress category colors (existing, keep consistent)
STRESS_COLORS = {
    'scarcity': '#d73027',   # Red
    'surplus': '#1a9850',    # Green
    'volatile': '#f46d43'    # Orange
}

def get_energy_color(technology):
    """
    Get standard color for energy technology.
    
    Args:
        technology (str): Technology name (case-insensitive)
        
    Returns:
        str: Hex color code
    """
    tech_lower = technology.lower()
    if tech_lower in ENERGY_COLORS:
        return ENERGY_COLORS[tech_lower]
    elif technology in ENERGY_COLORS_ALT:
        return ENERGY_COLORS_ALT[technology]
    else:
        return '#7F8C8D'  # Default gray for unknown technologies
