#!/usr/bin/env python3
"""
VerveStacks Main Runner Script

This script demonstrates how to use the VerveStacks processor to create energy system models
for different countries efficiently by loading global data once and processing multiple ISOs.

Usage:
    python main.py
    
For custom processing:
    from verve_stacks_processor import VerveStacksProcessor
    processor = VerveStacksProcessor()
    processor.process_iso('JPN')
"""

import sys
import argparse
import logging
from pathlib import Path
from verve_stacks_processor import VerveStacksProcessor


def update_excel_formatting_config(mode):
    """Update the Excel formatting configuration file."""
    import yaml
    import sys
    from datetime import datetime
    from pathlib import Path
    
    config_path = Path("config/excel_formatting.yaml")
    
    # Load existing config or create new
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    
    # Ensure structure exists
    if 'formatting' not in config:
        config['formatting'] = {}
    
    # Update mode and metadata
    config['formatting']['mode'] = mode
    config['last_updated'] = datetime.now().isoformat()
    config['command_used'] = ' '.join(sys.argv)
    
    # Write back
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    print(f"📝 Excel formatting mode set to: {mode}")


def setup_logging():
    """Set up logging configuration."""
    # Create handlers with proper encoding
    file_handler = logging.FileHandler('vervestacks.log', encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )


def main():
    """Main execution function."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description='VerveStacks Energy Model Processor')
    parser.add_argument('--iso', type=str, help='ISO country code to process (e.g., JPN, USA)')
    parser.add_argument('--capacity-threshold', type=int, default=100, 
                       help='MW threshold for individual plant tracking (default: 100)')
    parser.add_argument('--efficiency-gas', type=float, default=1.0,
                       help='Efficiency adjustment factor for gas plants (default: 1.0)')
    parser.add_argument('--efficiency-coal', type=float, default=1.0,
                       help='Efficiency adjustment factor for coal plants (default: 1.0)')
    parser.add_argument('--output-dir', type=str, default='output',
                       help='Output directory (default: output)')
    parser.add_argument('--force-reload', action='store_true',
                       help='Force reload of global data even if cache exists')
    parser.add_argument('--list-isos', action='store_true',
                       help='List available ISO codes and exit')
    parser.add_argument('--tsopt', type=str, default='ts12_clu',
                       help='Time slice option (default: ts12_clu)')
    parser.add_argument('--skip-timeslices', action='store_true',
                       help='Skip time-slice processing')
    parser.add_argument('--process-all-tsopts', action='store_true',
                       help='Process all available time-slice options (ts24_clu, ts12_clu, s1_d, etc.)')
    parser.add_argument('--grid-modeling', action='store_true',
                       help='Grid modeling')
    parser.add_argument('--grids', type=str, 
                       help='Override data source for grid infrastructure (eur, kan, cit, or syn_N where N is cluster count)')
    parser.add_argument('--no-git', action='store_true',
                       help='Skip all git operations (branch creation, commits, pushes)')
    parser.add_argument('--add-documentation', type=str, default='True',
                       help='Add documentation to Excel files (True/False, default: True)')
    
    # Excel formatting control (mutually exclusive)
    formatting_group = parser.add_mutually_exclusive_group()
    formatting_group.add_argument('--fast-excel', 
                                 action='store_true',
                                 help='Set fast Excel mode (minimal formatting, maximum speed)')
    formatting_group.add_argument('--full-formatting', 
                                 action='store_true', 
                                 help='Set full Excel formatting (beautiful but slower)')
    
    args = parser.parse_args()
    
    # Validate grids parameter if provided
    if args.grids:
        valid_prefixes = ['eur', 'kan', 'cit', 'syn_']
        if not any(args.grids.startswith(prefix) if prefix.endswith('_') else args.grids == prefix 
                   for prefix in valid_prefixes):
            parser.error(f"--grids must be 'eur', 'kan', 'cit', or 'syn_N' (e.g., syn_5, syn_10), got '{args.grids}'")
    
    # Update Excel formatting config based on CLI flags
    if args.fast_excel:
        update_excel_formatting_config("fast")
    elif args.full_formatting:
        update_excel_formatting_config("full")
    # If neither flag provided, use existing config (defaults to fast)
    
    try:
        # Initialize processor (loads global data once)
        logger.info("Initializing VerveStacks processor...")
        processor = VerveStacksProcessor(
            cache_dir="cache",
            force_reload=args.force_reload
        )
        
        # List available ISOs if requested
        if args.list_isos:
            available_isos = processor.get_available_isos()
            print(f"\nAvailable ISO codes ({len(available_isos)}):")
            for i, iso in enumerate(available_isos, 1):
                print(f"{i:3d}. {iso}")
            return
        
        # args.iso = 'BGR'

        # Process specific ISO or default examples
        if args.iso:
            # Process single ISO
            logger.info(f"Processing single ISO: {args.iso}")
            

            # Convert string to boolean
            add_docs = args.add_documentation.lower() in ('true', '1', 'yes', 'on')
            
            processor.process_iso(
                args.iso,
                capacity_threshold=args.capacity_threshold,
                efficiency_adjustment_gas=args.efficiency_gas,
                efficiency_adjustment_coal=args.efficiency_coal,
                output_dir=args.output_dir,
                tsopt=args.tsopt,
                skip_timeslices=args.skip_timeslices,
                process_all_tsopts=args.process_all_tsopts,
                grid_modeling=args.grid_modeling,
                auto_commit=not args.no_git,
                add_documentation=add_docs,
                grids_override=args.grids
            )
        else:
            # Run example workflow with multiple countries
            logger.info("Running example workflow with multiple countries...")
            example_countries = ['JPN', 'DEU', 'USA']
            
            # Convert string to boolean
            add_docs = args.add_documentation.lower() in ('true', '1', 'yes', 'on')
            
            for iso in example_countries:
                logger.info(f"Processing {iso}...")
                try:
                    processor.process_iso(
                        iso,
                        capacity_threshold=args.capacity_threshold,
                        efficiency_adjustment_gas=args.efficiency_gas,
                        efficiency_adjustment_coal=args.efficiency_coal,
                        output_dir=args.output_dir,
                        tsopt=args.tsopt,
                        skip_timeslices=args.skip_timeslices,
                        process_all_tsopts=args.process_all_tsopts,
                        grid_modeling=args.grid_modeling,
                        auto_commit=not args.no_git,
                        add_documentation=add_docs,
                        grids_override=args.grids
                    )
                    logger.info(f"SUCCESS: Successfully processed {iso}")
                except Exception as e:
                    logger.error(f"ERROR: Failed to process {iso}: {e}")
                    continue
        
        logger.info("COMPLETE: Processing completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 