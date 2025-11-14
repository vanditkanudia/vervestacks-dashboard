#!/usr/bin/env python3
"""
Simple VerveStacks Model Batch Processor

A streamlined script to process multiple ISOs sequentially with two processing modes:
- nogrid (default): Standard timeslice processing only
- grid: Full processing including grid modeling

Usage Examples:
    python make_models.py CHE,DEU,ITA,FRA,ESP                    # Default: nogrid mode
    python make_models.py --mode nogrid CHE,DEU,ITA,FRA,ESP      # Explicit nogrid mode  
    python make_models.py --mode grid CHE,DEU,ITA,FRA,ESP        # Grid modeling mode

Author: VerveStacks Team
Date: August 31, 2025
"""

import sys
import os
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path
import traceback


class SimpleModelProcessor:
    """Simple sequential processor for VerveStacks models."""
    
    def __init__(self, log_dir="batch_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Processing statistics
        self.stats = {
            'total': 0,
            'successful': [],
            'failed': [],
            'start_time': None,
            'end_time': None
        }
    
    def setup_logging(self):
        """Setup comprehensive logging with timestamps."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"make_models_{timestamp}.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.log_file = log_file
    
    def run_command(self, command, working_dir=None):
        """
        Run a command with full output logging and proper directory handling.
        
        Args:
            command: Command string to execute
            working_dir: Directory to run command from (None = current dir)
            
        Returns:
            bool: True if successful, False if failed
        """
        original_dir = Path.cwd()
        
        try:
            if working_dir:
                working_dir = Path(working_dir)
                self.logger.info(f"📂 Changing to directory: {working_dir}")
                os.chdir(working_dir)
            
            self.logger.info(f"🔄 Executing: {command}")
            
            # Set environment for Unicode support
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Run command with full output capture
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
                env=env
            )
            
            # Log full output
            if result.stdout:
                self.logger.info(f"📤 STDOUT:\n{result.stdout}")
            
            if result.stderr:
                if result.returncode == 0:
                    self.logger.info(f"📤 STDERR (non-fatal):\n{result.stderr}")
                else:
                    self.logger.error(f"📤 STDERR:\n{result.stderr}")
            
            if result.returncode == 0:
                self.logger.info(f"✅ Command completed successfully")
                return True
            else:
                self.logger.error(f"❌ Command failed with return code: {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ Command timed out after 30 minutes")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error executing command: {e}")
            return False
        finally:
            # Always restore original directory
            os.chdir(original_dir)
    
    def process_nogrid_mode(self, iso, s3_only=False):
        """
        Process ISO in nogrid mode (Option 2).
        
        Steps:
        1. Stress period analysis (from ts_design folder)
        2. Grid network extraction (cit) - for RE clustering
        3. Process all timeslice options (from root)
        """
        self.logger.info(f"🔧 Processing {iso} in NOGRID mode")
        
        if not s3_only:
            # Step 1: Stress period analysis
            self.logger.info(f"📊 Step 1/3: Running stress period analysis for {iso}")
            success = self.run_command(
                f"python scripts/stress_period_analyzer.py {iso}",
                working_dir="2_ts_design"
            )
            if not success:
                return False
            
            # Step 2: Grid network extraction with visualization - KanORS version
            self.logger.info(f"🔌 Step 2/3: Extracting grid network for {iso} for RE clustering")
            success = self.run_command(
                f"python extract_country_pypsa_network_clustered.py {iso} cit --visualize",
                working_dir="1_grids"
            )
            if not success:
                return False
        else:
            self.logger.info(f"⚡ Step 3 ONLY mode: Skipping steps 1-2 for {iso}")
            
        # Step 3: Process all timeslice options (always runs)
        step_label = "Step 3/3" if not s3_only else "Step 3 ONLY"
        self.logger.info(f"⚙️ {step_label}: Processing all timeslice options for {iso}")
        success = self.run_command(f"python main.py --iso {iso} --process-all-tsopts")
        if not success:
            return False
        
        return True
    
    def process_grid_mode(self, iso, s3_only=False):
        """
        Process ISO in grid mode (Option 1).
        
        Steps:
        1. Stress period analysis (from ts_design folder)
        2. Grid network extraction (from grids folder)
        3. Grid modeling with multiple timeslice options (from root)
        """
        self.logger.info(f"🌐 Processing {iso} in GRID mode")
        
        if not s3_only:
            # Step 1: Stress period analysis
            self.logger.info(f"📊 Step 1/3: Running stress period analysis for {iso}")
            success = self.run_command(
                f"python scripts/stress_period_analyzer.py {iso}",
                working_dir="2_ts_design"
            )
            if not success:
                return False
            
            # Step 2: Grid network extraction with visualization - KanORS version
            self.logger.info(f"🔌 Step 2/3: Extracting grid network for {iso}")
            success = self.run_command(
                f"python extract_country_pypsa_network_clustered.py {iso} kan --visualize",
                working_dir="1_grids"
            )
            if not success:
                return False
        else:
            self.logger.info(f"⚡ Step 3 ONLY mode: Skipping steps 1-2 for {iso}")
        
        # Step 3: Grid modeling with multiple timeslice options (always runs)
        step_label = "Step 3/3" if not s3_only else "Step 3 ONLY"
        self.logger.info(f"🌐 {step_label}: Running grid modeling for {iso}")
        success = self.run_command(f"python main.py --iso {iso} --grid-modeling --process-all-tsopts")
        if not success:
            return False
        
        return True
    
    def process_single_iso(self, iso, mode, s3_only=False):
        """Process a single ISO with the specified mode."""
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🚀 Starting {mode.upper()} processing for {iso}")
            
            if mode == "nogrid":
                success = self.process_nogrid_mode(iso, s3_only)
            elif mode == "grid":
                success = self.process_grid_mode(iso, s3_only)
            else:
                self.logger.error(f"❌ Unknown mode: {mode}")
                return False
            
            elapsed = datetime.now() - start_time
            
            if success:
                message = f"✅ {iso}: Successfully processed in {elapsed}"
                self.logger.info(message)
                self.stats['successful'].append(iso)
                return True
            else:
                message = f"❌ {iso}: Processing failed after {elapsed}"
                self.logger.error(message)
                self.stats['failed'].append((iso, "Processing step failed"))
                return False
                
        except Exception as e:
            elapsed = datetime.now() - start_time
            error_msg = f"❌ {iso}: Unexpected error after {elapsed} - {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"Full traceback for {iso}:\n{traceback.format_exc()}")
            self.stats['failed'].append((iso, str(e)))
            return False
    
    def process_iso_list(self, iso_list, mode, s3_only=False):
        """Process list of ISOs sequentially."""
        self.stats['total'] = len(iso_list)
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"🎯 BATCH PROCESSING STARTED")
        self.logger.info(f"📋 Mode: {mode.upper()}")
        if s3_only:
            self.logger.info(f"⚡ Step 3 ONLY mode enabled")
        self.logger.info(f"📋 ISOs to process: {iso_list}")
        self.logger.info(f"📁 Log file: {self.log_file}")
        
        for i, iso in enumerate(iso_list, 1):
            self.logger.info(f"📍 Progress: {i}/{len(iso_list)} - Processing {iso}")
            
            # Process ISO (continue on error)
            self.process_single_iso(iso, mode, s3_only)
            
            # Progress update
            completed = len(self.stats['successful']) + len(self.stats['failed'])
            self.logger.info(f"📊 Progress Update: {completed}/{len(iso_list)} completed "
                           f"({len(self.stats['successful'])} successful, "
                           f"{len(self.stats['failed'])} failed)")
        
        self.stats['end_time'] = datetime.now()
        self.print_final_summary()
    
    def print_final_summary(self):
        """Print final processing summary."""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        self.logger.info("\n" + "="*80)
        self.logger.info("🎯 BATCH PROCESSING SUMMARY")
        self.logger.info("="*80)
        
        self.logger.info(f"⏱️  Total Duration: {duration}")
        self.logger.info(f"📊 Total Requested: {self.stats['total']}")
        self.logger.info(f"✅ Successful: {len(self.stats['successful'])}")
        self.logger.info(f"❌ Failed: {len(self.stats['failed'])}")
        
        if self.stats['successful']:
            self.logger.info(f"\n✅ SUCCESSFUL COUNTRIES ({len(self.stats['successful'])}):")
            for iso in self.stats['successful']:
                self.logger.info(f"   • {iso}")
        
        if self.stats['failed']:
            self.logger.info(f"\n❌ FAILED COUNTRIES ({len(self.stats['failed'])}):")
            for iso, error in self.stats['failed']:
                self.logger.info(f"   • {iso}: {error}")
        
        success_rate = len(self.stats['successful']) / max(1, self.stats['total']) * 100
        self.logger.info(f"\n🎯 SUCCESS RATE: {success_rate:.1f}%")
        self.logger.info(f"📁 Full log: {self.log_file}")
        self.logger.info("="*80)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Simple VerveStacks Model Batch Processor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s CHE,DEU,ITA,FRA,ESP                    # Default: nogrid mode (all 3 steps)
  %(prog)s --mode nogrid CHE,DEU,ITA,FRA,ESP      # Explicit nogrid mode (all 3 steps)
  %(prog)s --mode grid CHE,DEU,ITA,FRA,ESP        # Grid modeling mode (all 3 steps)
  %(prog)s --s3 CHE,DEU                           # Step 3 only: nogrid mode
  %(prog)s --mode grid --s3 CHE,DEU               # Step 3 only: grid mode
        """
    )
    
    parser.add_argument('isos', type=str,
                       help='Comma-separated list of ISO codes (e.g., CHE,DEU,ITA,FRA,ESP)')
    parser.add_argument('--mode', type=str, choices=['nogrid', 'grid'], default='nogrid',
                       help='Processing mode: nogrid (default) or grid')
    parser.add_argument('--s3', action='store_true',
                       help='Skip steps 1-2 and run only step 3 (main processing)')
    
    args = parser.parse_args()
    
    # Parse ISO list
    iso_list = [iso.strip().upper() for iso in args.isos.split(',')]
    
    # Validate ISOs
    if not iso_list or not all(len(iso) == 3 for iso in iso_list):
        print("❌ Error: Please provide valid 3-letter ISO codes separated by commas")
        sys.exit(1)
    
    try:
        # Initialize processor and run
        processor = SimpleModelProcessor()
        processor.process_iso_list(iso_list, args.mode, args.s3)
        
        # Exit with appropriate code
        if processor.stats['failed']:
            sys.exit(1)  # Some failures occurred
        else:
            sys.exit(0)  # All successful
            
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
