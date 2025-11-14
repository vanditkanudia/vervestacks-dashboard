"""
Update README with AR6 scenarios section
Third pass README integration for AR6 climate scenarios
"""

from pathlib import Path
from .readme_generator import ReadmeGenerator


def update_readme_with_ar6_scenarios(iso_code, ar6_insights, veda_models_dir="C:/Veda/Veda/Veda_models/vervestacks_models", grid_modeling=False, data_source=None):
    """
    Update existing README.md with AR6 scenarios section (third pass)
    
    Args:
        iso_code: Country ISO code
        ar6_insights: Dictionary with AR6 statistics and insights
        veda_models_dir: Path to VEDA models directory
        grid_modeling: If True, looks for VerveStacks_{ISO}_grids_<data_source> folder
        data_source: Data source identifier (e.g., 'kan', 'eur', 'syn_5')
    """
    try:
        # Find the model folder and README
        models_path = Path(veda_models_dir)
        
        # Create folder suffix with data_source
        if grid_modeling and data_source:
            folder_suffix = f"_grids_{data_source}"
        elif grid_modeling:
            folder_suffix = "_grids"
        else:
            folder_suffix = ""
        model_folder = models_path / f"VerveStacks_{iso_code}{folder_suffix}"
        readme_path = models_path / "README.md"
        
        if not readme_path.exists():
            print(f"   ⚠️  README.md not found: {readme_path}")
            return False
        
        # Read existing README content
        readme_content = readme_path.read_text(encoding='utf-8')
        
        # Check if AR6 section already exists
        if "## AR6 Climate Scenarios" in readme_content:
            print(f"   ℹ️  AR6 section already exists in README")
            return True
        
        # Generate AR6 section using README generator
        readme_gen = ReadmeGenerator()
        
        # Generate just the AR6 sections
        ar6_content = readme_gen.generate_readme_content(
            iso_code, 
            processing_params=ar6_insights,
            ar6_scenarios=True
        )
        
        # Extract just the AR6 parts (remove core sections that already exist)
        ar6_lines = ar6_content.split('\n')
        ar6_section_start = -1
        
        for i, line in enumerate(ar6_lines):
            if line.startswith("## AR6 Climate Scenarios"):
                ar6_section_start = i
                break
        
        if ar6_section_start >= 0:
            ar6_section_content = '\n'.join(ar6_lines[ar6_section_start:])
            
            # Find insertion point in existing README
            # Insert after Model Structure, before Temporal Modeling
            insertion_markers = [
                "## Temporal Modeling & Timeslice Analysis",
                "## Quality Assurance",
                "## Usage Notes"
            ]
            
            insertion_pos = len(readme_content)  # Default to end
            
            for marker in insertion_markers:
                marker_pos = readme_content.find(marker)
                if marker_pos != -1:
                    insertion_pos = marker_pos
                    break
            
            # Insert AR6 section
            updated_content = (
                readme_content[:insertion_pos] + 
                "\n" + ar6_section_content + "\n\n" + 
                readme_content[insertion_pos:]
            )
            
            # Write updated README
            readme_path.write_text(updated_content, encoding='utf-8')
            
            print(f"   ✅ Added AR6 climate scenarios section to README")
            print(f"   📊 Region: {ar6_insights.get('r10_region', 'Unknown')}")
            print(f"   🎭 Categories: C1, C2, C3, C4, C7")
            
            return True
        else:
            print(f"   ⚠️  Could not generate AR6 section content")
            return False
            
    except Exception as e:
        print(f"   ❌ Error updating README with AR6 scenarios: {e}")
        return False


def main():
    """Test the AR6 README update function"""
    
    # Test AR6 insights (would normally come from create_ar6_r10_scenario)
    test_insights = {
        'iso_code': 'CHE',
        'r10_region': 'R10EUROPE',
        'country_count': 49,
        'scenario_model_count': 25,
        'total_scenario_models': 25,
        'co2_2030_c1_median': 120,
        'co2_2030_c7_median': 25,
        'co2_2050_c1_median': 350,
        'co2_2050_c7_median': 60,
        'elec_growth_2050_c1': 2.8,
        'elec_growth_2050_c7': 1.6,
        'hydrogen_2050_c1_median': 18,
        'hydrogen_2050_c7_median': 4,
        'transport_2020_median': 2.5,
        'transport_2050_c1_median': 28,
        'transport_growth_factor': 11.2,
        'co2_cv': 42,
        'elec_cv': 28,
        'hydrogen_cv': 78,
        'transport_cv': 52,
        'price_volatility_description': 'high price sensitivity to climate ambition',
        'uncertainty_range_description': 'wide uncertainty bands',
        'model_agreement_level': 'moderate consensus',
        'electrification_pattern': 'aggressive electrification under ambitious scenarios',
        'demand_uncertainty': 'significant variation',
        'hydrogen_volatility': 'moderate deployment uncertainty',
        'hydrogen_regional_pattern': 'emerging hydrogen applications',
        'transport_uncertainty': 'moderate transformation uncertainty',
        'transport_divergence_description': 'significant differences',
        'regional_convergence_pattern': 'higher model consensus',
        'regional_specific_insights': 'aggressive renewable deployment and electrification targets',
        'regional_context_factors': 'strong climate policies and renewable resource availability'
    }
    
    print("🧪 Testing AR6 README update...")
    
    # Test update (would normally be called from create_ar6_r10_scenario)
    success = update_readme_with_ar6_scenarios('CHE', test_insights)
    
    if success:
        print("✅ AR6 README update test completed successfully")
    else:
        print("❌ AR6 README update test failed")


if __name__ == "__main__":
    main()
