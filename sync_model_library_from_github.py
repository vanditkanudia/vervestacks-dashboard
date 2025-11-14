"""
VerveStacks Model Library GitHub Sync
====================================

Syncs the local model library JSON with the actual GitHub repository state.
Use this to recover from corrupted JSON or align with GitHub changes.

Usage:
    python sync_model_library_from_github.py --reset-placeholders
    python sync_model_library_from_github.py --preserve-metrics
"""

import argparse
import json
import requests
from datetime import datetime
from pathlib import Path
import re


class GitHubModelLibrarySync:
    def __init__(self, json_file_path="docs-rtd/model-library/models.json"):
        self.json_file_path = Path(json_file_path)
        self.github_api_base = "https://api.github.com/repos/akanudia/vervestacks_models"
        self.placeholder_metrics = {
            'total_gw': 'TBD',
            'total_twh': 'TBD',
            'co2_mt': 'TBD',
            'calibration_pct': 'TBD',
            'last_updated': datetime.now().strftime("%d %b %y")
        }
    
    def get_country_name_from_iso(self, iso_code):
        """Get country name using the same logic as update script"""
        try:
            from data_utils import get_country_name_from_iso
            return get_country_name_from_iso(iso_code)
        except Exception as e:
            print(f"Warning: Could not get country name for {iso_code}: {e}")
            return iso_code.upper()
    
    def get_github_branches(self):
        """Fetch all branches from GitHub repository with actual commit dates"""
        print("🔍 Fetching branches from GitHub...")
        
        try:
            response = requests.get(f"{self.github_api_base}/branches", timeout=30)
            response.raise_for_status()
            
            branches_data = response.json()
            branches = []
            
            print(f"   📊 Processing {len(branches_data)} branches...")
            
            for branch in branches_data:
                branch_name = branch['name']
                
                # Skip non-model branches
                if branch_name in ['main', 'master', 'develop', 'gh-pages']:
                    continue
                
                # Get commit details for this branch
                commit_sha = branch['commit']['sha']
                commit_date = self.get_commit_date(commit_sha)
                
                branches.append({
                    'name': branch_name,
                    'last_updated': commit_date
                })
            
            print(f"   ✅ Found {len(branches)} model branches on GitHub")
            return branches
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching GitHub branches: {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return []
    
    def get_commit_date(self, commit_sha):
        """Get formatted commit date from commit SHA"""
        try:
            response = requests.get(f"{self.github_api_base}/commits/{commit_sha}", timeout=10)
            response.raise_for_status()
            
            commit_data = response.json()
            commit_date = commit_data['commit']['committer']['date']
            
            # Convert to our format: "13 Sep 25"
            dt = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
            formatted_date = dt.strftime("%d %b %y")
            
            return formatted_date
            
        except Exception as e:
            # Fallback to current date if commit fetch fails
            print(f"   ⚠️  Could not get commit date for {commit_sha[:8]}: {e}")
            return datetime.now().strftime("%d %b %y")
    
    def load_existing_json(self):
        """Load existing JSON file if it exists"""
        if not self.json_file_path.exists():
            print("📄 No existing JSON file found - will create new one")
            return {}
        
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
            print(f"📄 Loaded existing JSON with {len(existing)} entries")
            return existing
        except Exception as e:
            print(f"⚠️  Error loading existing JSON: {e}")
            return {}
    
    def create_model_entry(self, branch_name, branch_date, existing_entry=None, preserve_metrics=True):
        """Create a model entry for a GitHub branch"""
        
        # Handle grid branches (e.g., DEU_grids_kan -> DEU for country name lookup)
        base_iso = branch_name
        grid_suffix = ""
        is_grid_model = '_grids' in branch_name.lower()
        
        if is_grid_model:
            # Extract data source suffix if present (e.g., DEU_grids_kan -> kan)
            parts = branch_name.split('_grids_')
            base_iso = parts[0]
            if len(parts) > 1:
                grid_suffix = f" (Grids-{parts[1].upper()})"
            else:
                grid_suffix = " (Grids)"
        
        country_name = self.get_country_name_from_iso(base_iso)
        country_name += grid_suffix
        
        # Create base entry
        entry = {
            'country_name': country_name,
            'iso_code': branch_name,  # Keep original case for GitHub URLs
            'last_updated': branch_date
        }
        
        # Handle metrics
        if existing_entry and preserve_metrics:
            # Preserve existing calibration metrics if they exist and aren't placeholders
            for metric in ['total_gw', 'total_twh', 'co2_mt', 'calibration_pct']:
                existing_value = existing_entry.get(metric, 'TBD')
                if existing_value != 'TBD' and existing_value != '':
                    entry[metric] = existing_value
                else:
                    entry[metric] = self.placeholder_metrics[metric]
        else:
            # Use placeholders for new entries or when not preserving
            entry.update({
                'total_gw': self.placeholder_metrics['total_gw'],
                'total_twh': self.placeholder_metrics['total_twh'],
                'co2_mt': self.placeholder_metrics['co2_mt'],
                'calibration_pct': self.placeholder_metrics['calibration_pct']
            })
        
        return entry
    
    def sync_with_github(self, preserve_metrics=True):
        """Sync local JSON with GitHub repository state"""
        print("🚀 VerveStacks Model Library GitHub Sync")
        print("=" * 50)
        
        # Get GitHub branches
        github_branches = self.get_github_branches()
        if not github_branches:
            print("❌ Could not fetch GitHub branches. Aborting sync.")
            return False
        
        # Load existing JSON
        existing_models = self.load_existing_json()
        
        # Create new models dict
        new_models = {}
        
        print(f"\n📊 Processing {len(github_branches)} GitHub branches...")
        
        for branch in github_branches:
            branch_name = branch['name']
            branch_date = branch['last_updated']
            
            # Check if we have existing data for this branch
            existing_entry = existing_models.get(branch_name.upper())
            
            # Create entry
            entry = self.create_model_entry(
                branch_name, 
                branch_date, 
                existing_entry, 
                preserve_metrics
            )
            
            new_models[branch_name.upper()] = entry
            
            # Log what happened
            if existing_entry:
                if preserve_metrics:
                    print(f"   🔄 Updated: {entry['country_name']} (preserved metrics)")
                else:
                    print(f"   🔄 Reset: {entry['country_name']} (placeholders)")
            else:
                print(f"   ➕ Added: {entry['country_name']} (new from GitHub)")
        
        # Check for orphaned entries (in JSON but not on GitHub)
        orphaned = set(existing_models.keys()) - set(m['name'].upper() for m in github_branches)
        if orphaned:
            print(f"\n🗑️  Found {len(orphaned)} orphaned entries (not on GitHub):")
            for orphan in orphaned:
                if orphan in existing_models:
                    country_name = existing_models[orphan].get('country_name', orphan)
                    print(f"   ❌ Removed: {country_name} ({orphan})")
        
        # Save new JSON
        self.save_models_to_json(new_models)
        
        # Update RST table
        self.regenerate_rst_table(new_models)
        
        print(f"\n✅ Sync complete!")
        print(f"   📊 Total models: {len(new_models)}")
        print(f"   ➕ New from GitHub: {len(new_models) - len(existing_models) + len(orphaned)}")
        print(f"   🗑️  Removed orphaned: {len(orphaned)}")
        
        return True
    
    def save_models_to_json(self, models_dict):
        """Save models dictionary to JSON file"""
        try:
            # Ensure directory exists
            self.json_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(models_dict, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved JSON: {self.json_file_path}")
            
        except Exception as e:
            print(f"❌ Error saving JSON: {e}")
            raise
    
    def regenerate_rst_table(self, models_dict):
        """Regenerate RST table from synced models"""
        try:
            from update_model_library_table import ModelLibraryTableUpdater
            
            updater = ModelLibraryTableUpdater()
            
            # Read current RST file
            with open(updater.rst_file_path, 'r', encoding='utf-8') as f:
                content_lines = f.readlines()
            
            # Find trigger line
            trigger_idx = None
            for i, line in enumerate(content_lines):
                if updater.trigger_line in line:
                    trigger_idx = i
                    break
            
            if trigger_idx is None:
                print("⚠️  Could not find trigger line in RST file")
                return
            
            # Generate new table
            new_table = updater.generate_table_rst(models_dict)
            
            # Reconstruct file content
            new_content = ''.join(content_lines[:trigger_idx + 1]) + new_table
            
            # Write back to file
            with open(updater.rst_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"📝 Updated RST table: {updater.rst_file_path}")
            
        except Exception as e:
            print(f"⚠️  Could not update RST table: {e}")


def main():
    parser = argparse.ArgumentParser(description='Sync VerveStacks model library with GitHub')
    parser.add_argument('--reset-placeholders', action='store_true',
                       help='Reset all metrics to placeholders (lose existing calibration data)')
    parser.add_argument('--preserve-metrics', action='store_true', default=True,
                       help='Preserve existing calibration metrics (default)')
    parser.add_argument('--json-file', default='docs-rtd/model-library/models.json',
                       help='Path to JSON file to sync')
    
    args = parser.parse_args()
    
    # Determine preserve_metrics flag
    if args.reset_placeholders:
        preserve_metrics = False
        print("🔄 Mode: Reset all metrics to placeholders")
    else:
        preserve_metrics = True
        print("🔄 Mode: Preserve existing calibration metrics")
    
    # Run sync
    syncer = GitHubModelLibrarySync(args.json_file)
    success = syncer.sync_with_github(preserve_metrics=preserve_metrics)
    
    if success:
        print("🎉 GitHub sync completed successfully!")
    else:
        print("❌ GitHub sync failed")
        exit(1)


if __name__ == "__main__":
    main()
