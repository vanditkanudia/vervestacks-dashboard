"""
VerveStacks Model Library Table Updater
=======================================

Updates the RTD model library table incrementally - one model at a time.
Called after each model is generated to add/update its entry in the table.

Usage:
    python update_model_library_table.py --iso GRC --total-gw 23.3 --total-twh 52 --co2-mt 18.8 --calibration-pct 97
"""

import argparse
import re
from datetime import datetime
from pathlib import Path


class ModelLibraryTableUpdater:
    def __init__(self, rst_file_path="docs-rtd/model-library/coverage-map.rst", json_file_path="docs-rtd/model-library/models.json"):
        self.rst_file_path = Path(rst_file_path)
        self.json_file_path = Path(json_file_path)
        self.trigger_line = "**Models Available:**"
        
    
    def get_country_name(self, iso_code):
        """Convert ISO code to country name using data_utils function"""
        try:
            from data_utils import get_country_name_from_iso
            return get_country_name_from_iso(iso_code)
        except Exception as e:
            print(f"Warning: Could not get country name for {iso_code}: {e}")
            return iso_code.upper()
    
    def load_models_from_json(self):
        """Load existing models from JSON file"""
        if not self.json_file_path.exists():
            return {}
        
        try:
            import json
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load models from JSON: {e}")
            return {}
    
    def save_models_to_json(self, models_dict):
        """Save models dictionary to JSON file"""
        try:
            import json
            # Ensure directory exists
            self.json_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(models_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error: Could not save models to JSON: {e}")
            raise
    
    def generate_table_rst(self, models_dict):
        """Generate RST table from models dictionary"""
        if not models_dict:
            return "\n*No models available yet.*\n"
        
        # Sort models by country name
        sorted_models = sorted(models_dict.items(), key=lambda x: x[1]['country_name'])
        
        table_lines = [
            "",
            ".. list-table::",
            "   :header-rows: 1", 
            "   :widths: 15 12 12 12 12 15",
            "   :class: model-library-table",
            "",
            "   * - Model",
            "     - Total GW",
            "     - Total TWh", 
            "     - Mt CO2",
            "     - Calibration %",
            "     - Last Updated"
        ]
        
        for iso_key, model_info in sorted_models:
            country_name = model_info['country_name']
            total_gw = model_info['total_gw']
            total_twh = model_info['total_twh']
            co2_mt = model_info['co2_mt']
            calibration_pct = model_info['calibration_pct']
            last_updated = model_info['last_updated']
            # Use iso_code from model_info for correct case in URLs
            iso_code = model_info['iso_code']
            
            table_lines.extend([
                f"   * - `{country_name} <https://github.com/akanudia/vervestacks_models/tree/{iso_code}>`__",
                f"     - {total_gw}",
                f"     - {total_twh}",
                f"     - {co2_mt}",
                f"     - {calibration_pct}%",
                f"     - {last_updated}"
            ])
        
        return "\n".join(table_lines) + "\n"
    
    def update_model_entry(self, iso_code, total_gw, total_twh, co2_mt, calibration_pct):
        """Update or add a model entry in the table"""
        
        if not self.rst_file_path.exists():
            print(f"RST file not found: {self.rst_file_path}")
            return False
        
        # Load existing models from JSON
        existing_models = self.load_models_from_json()
        
        # Add/update this model
        # Handle grid branches (e.g., DEU_grids -> DEU for country name lookup)
        base_iso = iso_code.replace('_grids', '').replace('_grid', '')
        is_grid_model = '_grid' in iso_code.lower()
        
        country_name = self.get_country_name(base_iso)
        if is_grid_model:
            country_name += " (Grids)"
        
        current_date = datetime.now().strftime("%d %b %y")
        
        existing_models[iso_code.upper()] = {
            'country_name': country_name,
            'iso_code': iso_code,  # Keep original case for GitHub URLs
            'total_gw': str(total_gw),
            'total_twh': str(total_twh), 
            'co2_mt': str(co2_mt),
            'calibration_pct': str(calibration_pct),
            'last_updated': current_date
        }
        
        # Save updated models to JSON
        self.save_models_to_json(existing_models)
        
        # Read current RST file
        with open(self.rst_file_path, 'r', encoding='utf-8') as f:
            content_lines = f.readlines()
        
        # Find trigger line
        trigger_idx = None
        for i, line in enumerate(content_lines):
            if self.trigger_line in line:
                trigger_idx = i
                break
        
        if trigger_idx is None:
            print(f"Trigger line '{self.trigger_line}' not found in RST file")
            return False
        
        # Generate new table
        new_table = self.generate_table_rst(existing_models)
        
        # Reconstruct file content (everything before trigger + trigger + new table)
        new_content = ''.join(content_lines[:trigger_idx + 1]) + new_table
        
        # Write back to file
        with open(self.rst_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Updated model library table with {country_name} ({iso_code})")
        print(f"   {total_gw} GW, {total_twh} TWh, {co2_mt} Mt CO2, {calibration_pct}% calibration")
        
        return True


def main():
    parser = argparse.ArgumentParser(description='Update VerveStacks model library table')
    parser.add_argument('--iso', required=True, help='ISO country code (e.g., GRC)')
    parser.add_argument('--total-gw', required=True, help='Total capacity in GW')
    parser.add_argument('--total-twh', required=True, help='Total generation in TWh')
    parser.add_argument('--co2-mt', required=True, help='CO2 emissions in Mt')
    parser.add_argument('--calibration-pct', required=True, help='Calibration percentage (without % sign)')
    parser.add_argument('--rst-file', default='docs-rtd/model-library/coverage-map.rst', 
                       help='Path to RST file to update')
    
    args = parser.parse_args()
    
    updater = ModelLibraryTableUpdater(args.rst_file)
    success = updater.update_model_entry(
        args.iso,
        args.total_gw,
        args.total_twh, 
        args.co2_mt,
        args.calibration_pct
    )
    
    if success:
        print("Model library table updated successfully!")
    else:
        print("Failed to update model library table")
        exit(1)


if __name__ == "__main__":
    main()
