#!/usr/bin/env python3
"""
Quick timeslice processor testing script
Usage: python test_timeslice.py [ISO] [TSOPT] [--grid]

Examples:
    python test_timeslice.py                    # Default: DEU, ts12_clu
    python test_timeslice.py CHE                # Switzerland, ts12_clu  
    python test_timeslice.py USA ts24_clu       # USA, ts24_clu
    python test_timeslice.py ITA ts12_clu --grid # Italy with grid modeling
"""

import sys
from pathlib import Path
from time_slice_processor import TimeSliceProcessor
from verve_stacks_processor import VerveStacksProcessor

class MockISOProcessor:
    """Minimal ISO processor for timeslice testing"""
    def __init__(self, iso_code, main_processor, grid_modeling=False):
        import logging
        
        self.input_iso = iso_code
        self.main = main_processor
        self.grid_modeling = grid_modeling
        self.dest_folder = Path(f"output/{iso_code}")
        self.dest_folder.mkdir(parents=True, exist_ok=True)
        self.output_dir = self.dest_folder  # Add output_dir for compatibility
        
        # Create logger for timeslice processor
        self.logger = logging.getLogger(f"MockISO_{iso_code}")
        self.logger.setLevel(logging.INFO)
        
        # Add console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

def test_timeslice(iso_code="DEU", tsopt="ts12_clu", grid_modeling=False):
    """Quick timeslice test function"""
    print(f"🔄 Testing timeslice processor:")
    print(f"   ISO: {iso_code}")
    print(f"   TSOPT: {tsopt}")
    print(f"   Grid Modeling: {grid_modeling}")
    print(f"   Output: output/{iso_code}/tsparameters_{iso_code}.xlsx")
    print()
    
    try:
        # Load main processor (cached after first run)
        print("📊 Loading VerveStacks data...")
        main_processor = VerveStacksProcessor(data_dir="data/")
        
        # Create mock ISO processor
        mock_iso_processor = MockISOProcessor(iso_code, main_processor, grid_modeling)
        
        # Run timeslice processor
        print(f"⚡ Running timeslice processor for {iso_code}...")
        # Pass the dest_folder to override default VEDA models location
        ts_processor = TimeSliceProcessor(mock_iso_processor, tsopt, dest_folder=mock_iso_processor.dest_folder)
        ts_processor.process_time_slices()
        
        print()
        print(f"✅ SUCCESS: Timeslice processing completed!")
        print(f"📁 Output file: output/{iso_code}/tsparameters_{iso_code}.xlsx")
        print(f"📁 Supporting files: output/{iso_code}/SuppXLS/")
        
    except Exception as e:
        print(f"❌ ERROR: Timeslice processing failed: {e}")
        import traceback
        traceback.print_exc()

def test_multiple():
    """Test multiple scenarios quickly"""
    print("🔄 Running multiple timeslice tests...")
    scenarios = [
        ("DEU", "ts12_clu", False),
        ("CHE", "ts24_clu", False),
        ("USA", "s1_d", False)
    ]
    
    for iso, tsopt, grid in scenarios:
        print(f"\n{'='*50}")
        test_timeslice(iso, tsopt, grid)

def show_help():
    """Show usage help"""
    print(__doc__)
    print("\nAvailable TSOPT values:")
    print("  - ts12_clu      : 12 aggregated slices - clustered")
    print("  - ts24_clu      : 24 aggregated slices - clustered") 
    print("  - s1_d : one day hourly - remaining aggregated slices")
    print()
    print("Available ISO codes (examples):")
    print("  - DEU : Germany")
    print("  - CHE : Switzerland") 
    print("  - USA : United States")
    print("  - ITA : Italy")
    print("  - FRA : France")
    print("  - GBR : United Kingdom")

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_help()
        sys.exit(0)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--multiple":
        test_multiple()
        sys.exit(0)
    
    # Single test mode
    iso = sys.argv[1] if len(sys.argv) > 1 else "DEU"
    tsopt = sys.argv[2] if len(sys.argv) > 2 else "ts12_clu"
    grid = "--grid" in sys.argv
    
    test_timeslice(iso, tsopt, grid)
