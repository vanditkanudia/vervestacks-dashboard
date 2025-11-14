#!/usr/bin/env python3
"""
Simple Python Files Zipper for VerveStacks
==========================================

Creates a zip file containing all tracked Python files in the project.
Useful for sharing the codebase or creating backups of the Python scripts.

Usage:
    python zip_python_files.py [--dry-run]

Author: VerveStacks Team
"""

import subprocess
import zipfile
import argparse
from pathlib import Path
from datetime import datetime


def get_tracked_python_files():
    """Get all tracked Python files using git ls-files."""
    try:
        result = subprocess.run(
            ['git', 'ls-files', '*.py'],
            capture_output=True,
            text=True,
            check=True
        )
        
        files = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                file_path = Path(line.strip())
                if file_path.exists():
                    files.append(file_path)
                else:
                    print(f"Warning: File not found: {file_path}")
        
        return files
    
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}")
        return []
    except FileNotFoundError:
        print("Error: git command not found. Make sure Git is installed and in PATH.")
        return []


def create_python_zip(files, dry_run=False):
    """Create zip file with all Python files."""
    if not files:
        print("No Python files found to zip.")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"vervestacks_python_files_{timestamp}.zip"
    
    print(f"\n{'DRY RUN: Would create' if dry_run else 'Creating'} Python files backup: {zip_filename}")
    print(f"Found {len(files)} tracked Python files:")
    
    total_size = 0
    for file_path in sorted(files):
        size_mb = file_path.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  {file_path} ({size_mb:.1f} MB)")
    
    print(f"\nTotal size: {total_size:.1f} MB")
    
    if dry_run:
        print(f"\nDRY RUN: Would create {zip_filename} with {len(files)} Python files")
        return
    
    # Create the zip file
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                # Add file to zip, preserving directory structure
                zipf.write(file_path, file_path)
                print(f"  Added: {file_path}")
        
        # Create a _latest.zip copy for convenience
        latest_filename = "vervestacks_python_files_latest.zip"
        Path(zip_filename).replace(latest_filename)
        print(f"\n✅ Created: {latest_filename}")
        print(f"   Also available as: {zip_filename}")
        
        # Show final stats
        zip_size = Path(latest_filename).stat().st_size / (1024 * 1024)
        print(f"   Compressed size: {zip_size:.1f} MB")
        print(f"   Compression ratio: {(1 - zip_size/total_size)*100:.1f}%")
        
    except Exception as e:
        print(f"Error creating zip file: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Create a zip file of all tracked Python files in VerveStacks"
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be zipped without creating the file'
    )
    
    args = parser.parse_args()
    
    print("VerveStacks Python Files Zipper")
    print("=" * 40)
    
    # Get all tracked Python files
    python_files = get_tracked_python_files()
    
    if not python_files:
        print("No tracked Python files found.")
        return
    
    # Create the zip
    create_python_zip(python_files, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
