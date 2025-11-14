#!/usr/bin/env python3
"""
Quick Batch Processing Script for VerveStacks

A simplified script for common batch processing scenarios.
For advanced options, use batch_process_models.py

Usage Examples:
    # Process EU countries
    python quick_batch.py eu
    
    # Process G7 countries
    python quick_batch.py g7
    
    # Process specific countries
    python quick_batch.py custom JPN,DEU,USA,CHN
    
    # Process sample set (for testing)
    python quick_batch.py sample
"""

import sys
import subprocess
from pathlib import Path

def run_batch_command(args):
    """Run the main batch processing script with given arguments."""
    script_path = Path(__file__).parent / "batch_process_models.py"
    cmd = [sys.executable, str(script_path)] + args
    
    print(f"🚀 Running: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user")
        return 1

def main():
    if len(sys.argv) < 2:
        print("""
🚀 VerveStacks Quick Batch Processing

Usage: python quick_batch.py <scenario> [options]

Available scenarios:
  sample       - Process sample countries (JPN, DEU, USA, CHN, IND)
  eu           - Process EU countries  
  g7           - Process G7 countries
  g20          - Process G20 countries
  brics        - Process BRICS countries
  asean        - Process ASEAN countries
  custom       - Process custom list: python quick_batch.py custom JPN,DEU,USA

Options (add after scenario):
  --no-git         - Skip git operations
  --parallel       - Enable parallel processing
  --overwrite      - Overwrite existing files
  --force-reload   - Force reload of cached data
  --skip-re-shapes - Skip RE Shapes Analysis v5

Examples:
  python quick_batch.py sample
  python quick_batch.py eu --no-git
  python quick_batch.py g7 --parallel --overwrite
  python quick_batch.py custom JPN,DEU,USA --no-git --skip-re-shapes
        """)
        return 1
    
    scenario = sys.argv[1].lower()
    extra_args = sys.argv[2:]
    
    # Map scenarios to batch script arguments
    scenario_map = {
        'sample': ['--group', 'SAMPLE'],
        'eu': ['--group', 'EU'],
        'g7': ['--group', 'G7'],
        'g20': ['--group', 'G20'],
        'brics': ['--group', 'BRICS'],
        'asean': ['--group', 'ASEAN']
    }
    
    if scenario == 'custom':
        if len(extra_args) < 1:
            print("❌ Custom scenario requires ISO list: python quick_batch.py custom JPN,DEU,USA")
            return 1
        
        iso_list = extra_args[0]
        batch_args = ['--isos', iso_list] + extra_args[1:]
        
    elif scenario in scenario_map:
        batch_args = scenario_map[scenario] + extra_args
        
    elif scenario in ['list', 'help', '--help', '-h']:
        batch_args = ['--list-groups']
        
    else:
        print(f"❌ Unknown scenario: {scenario}")
        print("Available scenarios: sample, eu, g7, g20, brics, asean, custom")
        return 1
    
    # Run the batch processing
    return run_batch_command(batch_args)

if __name__ == "__main__":
    sys.exit(main())
