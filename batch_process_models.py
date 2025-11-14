#!/usr/bin/env python3
"""
VerveStacks Batch Model Processing Script

A comprehensive script to process multiple ISO countries and create full energy system models
with customizable settings, parallel processing options, and robust error handling.

Usage Examples:
    # Process specific countries
    python batch_process_models.py --isos JPN,DEU,USA
    
    # Process all available countries (be careful!)
    python batch_process_models.py --process-all
    
    # Process EU countries only
    python batch_process_models.py --group EU
    
    # Process with custom settings
    python batch_process_models.py --isos CHN,IND --capacity-threshold 50 --no-git
    
    # Resume failed processing from a previous run
    python batch_process_models.py --resume-from-log

Author: VerveStacks Team
"""

import sys
import os
import argparse
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
import traceback

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

from verve_stacks_processor import VerveStacksProcessor


class BatchModelProcessor:
    """Handles batch processing of multiple ISO countries with comprehensive logging and error handling."""
    
    def __init__(self, 
                 cache_dir: str = "cache",
                 output_dir: str = "output", 
                 log_dir: str = "batch_logs",
                 force_reload: bool = False):
        """Initialize the batch processor."""
        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.force_reload = force_reload
        
        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize processor
        self.processor = None
        
        # Processing statistics
        self.stats = {
            'total_requested': 0,
            'successful': [],
            'failed': [],
            'skipped': [],
            'start_time': None,
            'end_time': None
        }
        
        # Predefined country groups
        self.country_groups = {
            'EU': ['DEU', 'FRA', 'ITA', 'ESP', 'POL', 'ROU', 'NLD', 'BEL', 'GRC', 'PRT', 
                   'CZE', 'HUN', 'SWE', 'AUT', 'BGR', 'DNK', 'FIN', 'SVK', 'IRL', 'HRV',
                   'LTU', 'SVN', 'LVA', 'EST', 'CYP', 'LUX', 'MLT'],
            'G7': ['USA', 'JPN', 'DEU', 'GBR', 'FRA', 'ITA', 'CAN'],
            'G20': ['USA', 'CHN', 'JPN', 'DEU', 'IND', 'GBR', 'FRA', 'ITA', 'BRA', 'CAN',
                    'RUS', 'KOR', 'AUS', 'MEX', 'IDN', 'SAU', 'TUR', 'ARG', 'ZAF'],
            'BRICS': ['BRA', 'RUS', 'IND', 'CHN', 'ZAF'],
            'ASEAN': ['IDN', 'THA', 'SGP', 'PHL', 'VNM', 'MYS', 'MMR', 'KHM', 'LAO', 'BRN'],
            'SAMPLE': ['JPN', 'DEU', 'USA', 'CHN', 'IND']  # Quick test sample
        }

    def setup_logging(self):
        """Setup comprehensive logging for batch processing."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create log files
        main_log = self.log_dir / f"batch_process_{timestamp}.log"
        error_log = self.log_dir / f"batch_errors_{timestamp}.log"
        success_log = self.log_dir / f"batch_success_{timestamp}.log"
        
        # Configure main logger
        main_handler = logging.FileHandler(main_log, encoding='utf-8')
        error_handler = logging.FileHandler(error_log, encoding='utf-8')
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Set formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        main_handler.setFormatter(detailed_formatter)
        error_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(simple_formatter)
        
        # Configure logging levels
        main_handler.setLevel(logging.INFO)
        error_handler.setLevel(logging.ERROR)
        console_handler.setLevel(logging.INFO)
        
        # Setup root logger
        logging.basicConfig(
            level=logging.INFO,
            handlers=[main_handler, error_handler, console_handler]
        )
        
        # Store log file paths for summary
        self.log_files = {
            'main': main_log,
            'error': error_log,
            'success': success_log
        }

    def initialize_processor(self):
        """Initialize the VerveStacks processor."""
        if self.processor is None:
            self.logger.info("Initializing VerveStacks processor...")
            try:
                self.processor = VerveStacksProcessor(
                    cache_dir=self.cache_dir,
                    force_reload=self.force_reload
                )
                self.logger.info("✅ Processor initialized successfully")
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize processor: {e}")
                raise

    def get_available_isos(self) -> List[str]:
        """Get list of available ISO codes."""
        self.initialize_processor()
        return self.processor.get_available_isos()

    def get_iso_list(self, isos: Optional[str] = None, 
                     group: Optional[str] = None, 
                     process_all: bool = False) -> List[str]:
        """Get the list of ISOs to process based on input parameters."""
        
        if process_all:
            self.logger.warning("🚨 Processing ALL available countries - this may take a very long time!")
            available = self.get_available_isos()
            self.logger.info(f"Found {len(available)} available ISO codes")
            return available
        
        elif group:
            if group.upper() not in self.country_groups:
                available_groups = ', '.join(self.country_groups.keys())
                raise ValueError(f"Unknown group '{group}'. Available groups: {available_groups}")
            
            iso_list = self.country_groups[group.upper()]
            self.logger.info(f"Processing {group.upper()} group: {len(iso_list)} countries")
            return iso_list
        
        elif isos:
            iso_list = [iso.strip().upper() for iso in isos.split(',')]
            self.logger.info(f"Processing specified ISOs: {iso_list}")
            return iso_list
        
        else:
            # Default to sample
            iso_list = self.country_groups['SAMPLE']
            self.logger.info(f"No ISOs specified, using SAMPLE group: {iso_list}")
            return iso_list

    def run_re_shapes_analysis(self, iso: str) -> bool:
        """
        Run RE Shapes Analysis v5 for the specified ISO.
        This is a prerequisite that generates files needed by the main processing.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"📊 Running RE Shapes Analysis v5 for {iso}...")
            
            # Import and run the RE Shapes Analysis
            import subprocess
            import sys
            
            # Path to the RE Shapes Analysis v5 script
            re_shapes_script = Path("2_ts_design/scripts/RE_Shapes_Analysis_v5.py")
            
            if not re_shapes_script.exists():
                self.logger.error(f"❌ RE Shapes Analysis script not found: {re_shapes_script}")
                return False
            
            # Check if input file exists
            input_file = Path(self.output_dir) / f"VerveStacks_{iso}.xlsx"
            if not input_file.exists():
                self.logger.error(f"❌ Input file for RE Shapes Analysis not found: {input_file}")
                self.logger.error("💡 RE Shapes Analysis requires VerveStacks_{ISO}.xlsx to be generated first")
                return False
            
            # Run the RE Shapes Analysis script
            # The v5 script expects ISO codes as positional arguments, comma-separated
            cmd = [
                sys.executable, 
                str(re_shapes_script),
                iso  # ISO code as positional argument
            ]
            
            self.logger.info(f"🔄 Executing: {' '.join(cmd)}")
            
            # Change to the script directory since it uses relative paths
            original_dir = Path.cwd()
            script_dir = re_shapes_script.parent
            
            try:
                os.chdir(script_dir)
                self.logger.debug(f"Changed working directory to: {script_dir}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
            finally:
                os.chdir(original_dir)
                self.logger.debug(f"Restored working directory to: {original_dir}")
            
            if result.returncode == 0:
                self.logger.info(f"✅ RE Shapes Analysis completed successfully for {iso}")
                if result.stdout:
                    self.logger.debug(f"RE Shapes output: {result.stdout}")
                return True
            else:
                self.logger.error(f"❌ RE Shapes Analysis failed for {iso}")
                self.logger.error(f"Return code: {result.returncode}")
                if result.stderr:
                    self.logger.error(f"Error output: {result.stderr}")
                if result.stdout:
                    self.logger.error(f"Standard output: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ RE Shapes Analysis timed out for {iso}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error running RE Shapes Analysis for {iso}: {e}")
            return False

    def process_single_iso(self, 
                          iso: str, 
                          config: Dict) -> Tuple[str, bool, str]:
        """
        Process a single ISO country with RE Shapes Analysis prerequisite.
        
        Returns:
            Tuple of (iso, success, message)
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"🚀 Starting processing for {iso}...")
            
            # Check if already processed (unless force reload)
            output_path = Path(self.output_dir) / f"VerveStacks_{iso}.xlsx"
            if output_path.exists() and not config.get('force_reload', False):
                if not config.get('overwrite', False):
                    message = f"⏭️  {iso}: Output already exists, skipping (use --overwrite to force)"
                    self.logger.info(message)
                    return iso, False, message
            
            # Step 1: Run main ISO processing to generate VerveStacks_{ISO}.xlsx
            self.logger.info(f"📋 Step 1/2: Running main ISO processing for {iso}...")
            self.processor.process_iso(
                iso,
                capacity_threshold=config.get('capacity_threshold', 100),
                efficiency_adjustment_gas=config.get('efficiency_gas', 1.0),
                efficiency_adjustment_coal=config.get('efficiency_coal', 1.0),
                output_dir=config.get('output_dir', 'output'),
                tsopt=config.get('tsopt', 'ts12_clu'),
                skip_timeslices=config.get('skip_timeslices', False),
                process_all_tsopts=config.get('process_all_tsopts', False),
                grid_modeling=config.get('grid_modeling', False),
                auto_commit=config.get('auto_commit', True)
            )
            
            # Step 2: Run RE Shapes Analysis v5 (prerequisite for future steps)
            if not config.get('skip_re_shapes', False):
                self.logger.info(f"📊 Step 2/2: Running RE Shapes Analysis v5 for {iso}...")
                re_shapes_success = self.run_re_shapes_analysis(iso)
                
                if not re_shapes_success:
                    self.logger.warning(f"⚠️  RE Shapes Analysis failed for {iso}, but main processing succeeded")
                    # Don't fail the entire process - RE Shapes is for future enhancement
                else:
                    self.logger.info(f"✅ RE Shapes Analysis completed for {iso}")
            else:
                self.logger.info(f"⏭️  Skipping RE Shapes Analysis for {iso} (disabled in config)")
            
            elapsed = time.time() - start_time
            message = f"✅ {iso}: Successfully processed in {elapsed:.1f}s"
            self.logger.info(message)
            
            # Log to success file
            with open(self.log_files['success'], 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()} - {message}\n")
            
            return iso, True, message
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"❌ {iso}: Failed after {elapsed:.1f}s - {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"Full traceback for {iso}:\n{traceback.format_exc()}")
            
            return iso, False, error_msg

    def process_isos_sequential(self, 
                               iso_list: List[str], 
                               config: Dict) -> Dict:
        """Process ISOs sequentially (safer, easier to debug)."""
        
        self.logger.info(f"🔄 Processing {len(iso_list)} ISOs sequentially...")
        
        for i, iso in enumerate(iso_list, 1):
            self.logger.info(f"📍 Progress: {i}/{len(iso_list)} - Processing {iso}")
            
            iso_code, success, message = self.process_single_iso(iso, config)
            
            if success:
                self.stats['successful'].append(iso_code)
            else:
                self.stats['failed'].append((iso_code, message))
            
            # Progress update
            if i % 5 == 0 or i == len(iso_list):
                self.logger.info(f"📊 Progress Update: {i}/{len(iso_list)} completed "
                               f"({len(self.stats['successful'])} successful, "
                               f"{len(self.stats['failed'])} failed)")

    def process_isos_parallel(self, 
                             iso_list: List[str], 
                             config: Dict, 
                             max_workers: int = 3) -> Dict:
        """Process ISOs in parallel (faster but more resource intensive)."""
        
        self.logger.info(f"⚡ Processing {len(iso_list)} ISOs in parallel with {max_workers} workers...")
        self.logger.warning("⚠️  Parallel processing uses more system resources and may cause issues with Excel/xlwings")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_iso = {
                executor.submit(self.process_single_iso, iso, config): iso 
                for iso in iso_list
            }
            
            # Process completed tasks
            for future in as_completed(future_to_iso):
                iso = future_to_iso[future]
                try:
                    iso_code, success, message = future.result()
                    
                    if success:
                        self.stats['successful'].append(iso_code)
                    else:
                        self.stats['failed'].append((iso_code, message))
                        
                except Exception as e:
                    error_msg = f"❌ {iso}: Unexpected error in parallel processing - {str(e)}"
                    self.logger.error(error_msg)
                    self.stats['failed'].append((iso, error_msg))
                
                # Progress update
                completed = len(self.stats['successful']) + len(self.stats['failed'])
                self.logger.info(f"📊 Progress: {completed}/{len(iso_list)} completed")

    def run_batch_processing(self, 
                           iso_list: List[str], 
                           config: Dict) -> Dict:
        """Run the complete batch processing workflow."""
        
        self.stats['total_requested'] = len(iso_list)
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"🎯 BATCH PROCESSING STARTED")
        self.logger.info(f"📋 ISOs to process: {iso_list}")
        self.logger.info(f"⚙️  Configuration: {json.dumps(config, indent=2)}")
        
        # Initialize processor
        self.initialize_processor()
        
        # Validate ISOs
        available_isos = self.get_available_isos()
        invalid_isos = [iso for iso in iso_list if iso not in available_isos]
        
        if invalid_isos:
            self.logger.warning(f"⚠️  Invalid ISOs will be skipped: {invalid_isos}")
            self.stats['skipped'] = invalid_isos
            iso_list = [iso for iso in iso_list if iso in available_isos]
        
        if not iso_list:
            self.logger.error("❌ No valid ISOs to process!")
            return self.stats
        
        # Process ISOs
        try:
            if config.get('parallel', False):
                self.process_isos_parallel(iso_list, config, config.get('max_workers', 3))
            else:
                self.process_isos_sequential(iso_list, config)
                
        except KeyboardInterrupt:
            self.logger.info("⏹️  Processing interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Fatal error in batch processing: {e}")
            self.logger.error(traceback.format_exc())
        
        self.stats['end_time'] = datetime.now()
        self.print_final_summary()
        
        return self.stats

    def print_final_summary(self):
        """Print comprehensive summary of batch processing results."""
        
        duration = self.stats['end_time'] - self.stats['start_time']
        
        self.logger.info("\n" + "="*80)
        self.logger.info("🎯 BATCH PROCESSING SUMMARY")
        self.logger.info("="*80)
        
        self.logger.info(f"⏱️  Total Duration: {duration}")
        self.logger.info(f"📊 Total Requested: {self.stats['total_requested']}")
        self.logger.info(f"✅ Successful: {len(self.stats['successful'])}")
        self.logger.info(f"❌ Failed: {len(self.stats['failed'])}")
        self.logger.info(f"⏭️  Skipped: {len(self.stats['skipped'])}")
        
        if self.stats['successful']:
            self.logger.info(f"\n✅ SUCCESSFUL COUNTRIES ({len(self.stats['successful'])}):")
            for iso in self.stats['successful']:
                self.logger.info(f"   • {iso}")
        
        if self.stats['failed']:
            self.logger.info(f"\n❌ FAILED COUNTRIES ({len(self.stats['failed'])}):")
            for iso, error in self.stats['failed']:
                self.logger.info(f"   • {iso}: {error}")
        
        if self.stats['skipped']:
            self.logger.info(f"\n⏭️  SKIPPED COUNTRIES ({len(self.stats['skipped'])}):")
            for iso in self.stats['skipped']:
                self.logger.info(f"   • {iso}")
        
        # Log file locations
        self.logger.info(f"\n📁 LOG FILES:")
        self.logger.info(f"   • Main log: {self.log_files['main']}")
        self.logger.info(f"   • Error log: {self.log_files['error']}")
        self.logger.info(f"   • Success log: {self.log_files['success']}")
        
        success_rate = len(self.stats['successful']) / max(1, self.stats['total_requested'] - len(self.stats['skipped'])) * 100
        self.logger.info(f"\n🎯 SUCCESS RATE: {success_rate:.1f}%")
        
        self.logger.info("="*80)


def main():
    """Main execution function with comprehensive argument parsing."""
    
    parser = argparse.ArgumentParser(
        description='VerveStacks Batch Model Processing Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --isos JPN,DEU,USA                    # Process specific countries
  %(prog)s --group EU --capacity-threshold 50   # Process EU with custom threshold
  %(prog)s --process-all --parallel             # Process all countries in parallel (dangerous!)
  %(prog)s --list-groups                        # Show available country groups
  %(prog)s --list-available                     # Show all available ISO codes
        """
    )
    
    # ISO selection arguments
    iso_group = parser.add_mutually_exclusive_group()
    iso_group.add_argument('--isos', type=str, 
                          help='Comma-separated list of ISO codes (e.g., JPN,DEU,USA)')
    iso_group.add_argument('--group', type=str,
                          help='Process predefined country group (EU, G7, G20, BRICS, ASEAN, SAMPLE)')
    iso_group.add_argument('--process-all', action='store_true',
                          help='Process ALL available countries (use with caution!)')
    
    # Processing configuration
    parser.add_argument('--capacity-threshold', type=int, default=100,
                       help='MW threshold for individual plant tracking (default: 100)')
    parser.add_argument('--efficiency-gas', type=float, default=1.0,
                       help='Efficiency adjustment factor for gas plants (default: 1.0)')
    parser.add_argument('--efficiency-coal', type=float, default=1.0,
                       help='Efficiency adjustment factor for coal plants (default: 1.0)')
    parser.add_argument('--tsopt', type=str, default='ts12_clu',
                       help='Time slice option (default: ts12_clu)')
    
    # Processing options
    parser.add_argument('--parallel', action='store_true',
                       help='Enable parallel processing (faster but more resource intensive)')
    parser.add_argument('--max-workers', type=int, default=3,
                       help='Maximum parallel workers (default: 3)')
    parser.add_argument('--skip-timeslices', action='store_true',
                       help='Skip time-slice processing')
    parser.add_argument('--process-all-tsopts', action='store_true',
                       help='Process all available time-slice options')
    parser.add_argument('--grid-modeling', action='store_true',
                       help='Enable grid modeling')
    parser.add_argument('--skip-re-shapes', action='store_true',
                       help='Skip RE Shapes Analysis v5 (normally runs after main processing)')
    parser.add_argument('--no-git', action='store_true',
                       help='Skip all git operations (branch creation, commits, pushes)')
    
    # File system options
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory (default: output)')
    parser.add_argument('--cache-dir', type=str, default='cache',
                       help='Cache directory (default: cache)')
    parser.add_argument('--log-dir', type=str, default='batch_logs',
                       help='Log directory (default: batch_logs)')
    parser.add_argument('--force-reload', action='store_true',
                       help='Force reload of global data even if cache exists')
    parser.add_argument('--overwrite', action='store_true',
                       help='Overwrite existing output files')
    
    # Information options
    parser.add_argument('--list-groups', action='store_true',
                       help='List available country groups and exit')
    parser.add_argument('--list-available', action='store_true',
                       help='List all available ISO codes and exit')
    
    args = parser.parse_args()
    
    # Initialize processor
    try:
        processor = BatchModelProcessor(
            cache_dir=args.cache_dir,
            output_dir=args.output_dir,
            log_dir=args.log_dir,
            force_reload=args.force_reload
        )
        
        # Handle information requests
        if args.list_groups:
            print("\n🌍 Available Country Groups:")
            for group, countries in processor.country_groups.items():
                print(f"\n{group} ({len(countries)} countries):")
                print(f"  {', '.join(countries)}")
            return
        
        if args.list_available:
            available = processor.get_available_isos()
            print(f"\n📋 Available ISO Codes ({len(available)}):")
            for i, iso in enumerate(available, 1):
                print(f"{i:3d}. {iso}")
            return
        
        # Get ISO list to process
        iso_list = processor.get_iso_list(
            isos=args.isos,
            group=args.group,
            process_all=args.process_all
        )
        
        # Prepare configuration
        config = {
            'capacity_threshold': args.capacity_threshold,
            'efficiency_gas': args.efficiency_gas,
            'efficiency_coal': args.efficiency_coal,
            'output_dir': args.output_dir,
            'tsopt': args.tsopt,
            'skip_timeslices': args.skip_timeslices,
            'process_all_tsopts': args.process_all_tsopts,
            'grid_modeling': args.grid_modeling,
            'skip_re_shapes': args.skip_re_shapes,
            'auto_commit': not args.no_git,
            'force_reload': args.force_reload,
            'overwrite': args.overwrite,
            'parallel': args.parallel,
            'max_workers': args.max_workers
        }
        
        # Confirmation for large batches
        if len(iso_list) > 10 and not args.process_all:
            print(f"\n⚠️  You are about to process {len(iso_list)} countries: {', '.join(iso_list)}")
            response = input("Continue? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Processing cancelled.")
                return
        
        # Run batch processing
        stats = processor.run_batch_processing(iso_list, config)
        
        # Exit with appropriate code
        if stats['failed']:
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
