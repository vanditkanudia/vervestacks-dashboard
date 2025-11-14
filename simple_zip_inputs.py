#!/usr/bin/env python3
"""Simple script to zip git-ignored files that are referenced by tracked Python scripts"""

import subprocess
import zipfile
from pathlib import Path
from datetime import datetime
import json
import hashlib
import argparse

def get_untracked_files(size_limit_mb=None):
    """Get all git-ignored and untracked files with optional size filter"""
    try:
        # Get untracked files (without exclude-standard to catch everything)
        result_untracked = subprocess.run(
            ["git", "ls-files", "--others"],
            capture_output=True, text=True, check=True
        )
        
        # Get ignored files (with exclude-standard to get .gitignore matches)
        result_ignored = subprocess.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard"],
            capture_output=True, text=True, check=True
        )
        
        # Combine both lists and remove duplicates
        all_lines = set()
        for line in result_untracked.stdout.strip().split('\n'):
            if line:
                all_lines.add(line)
        for line in result_ignored.stdout.strip().split('\n'):
            if line:
                all_lines.add(line)
        
        result = type('Result', (), {'stdout': '\n'.join(all_lines)})()
    except subprocess.CalledProcessError:
        return []
    
    try:
        
        files = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            file_path = Path(line)
            
            # Skip common non-data directories and cache directories
            exclude_dirs = {
                '.venv', 'venv', '__pycache__', '.git', '.idea', '.vscode',
                'cache', 'Cache', '.cache', 'temp', 'tmp', '.tmp'
            }
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            
            # Skip files with cache-like patterns and generated files
            exclude_patterns = ['cache', '.pkl', '.pickle', '.log', '.tmp', '.temp']
            if any(pattern in file_path.name.lower() for pattern in exclude_patterns):
                continue
                
            # Include files with optional size filter
            try:
                if file_path.exists() and file_path.is_file():
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    # Apply size limit if specified
                    if size_limit_mb is None or size_mb <= size_limit_mb:
                        files.append((file_path, size_mb))
            except (OSError, PermissionError):
                continue
                
        return files
        
    except subprocess.CalledProcessError:
        return []

def get_tracked_python_files():
    """Get all git-tracked Python files"""
    try:
        result = subprocess.run(
            ["git", "ls-files", "*.py"],
            capture_output=True, text=True, check=True
        )
        
        py_files = []
        for line in result.stdout.strip().split('\n'):
            if line and line.endswith('.py'):
                py_file = Path(line)
                if py_file.exists():
                    py_files.append(py_file)
        
        return py_files
        
    except subprocess.CalledProcessError:
        print("Warning: Could not get tracked Python files, falling back to all .py files")
        # Fallback to scanning all Python files (original behavior)
        py_files = []
        for py_file in Path('.').rglob('*.py'):
            # Skip .venv and other non-project directories
            if any(part in {'.venv', 'venv', '__pycache__', '.git'} for part in py_file.parts):
                continue
            py_files.append(py_file)
        return py_files

def find_files_in_python_scripts(files_to_check):
    """Search for file references in tracked Python scripts"""
    referenced_files = []
    
    # Get only git-tracked Python files
    py_files = get_tracked_python_files()
    
    print(f"Scanning {len(py_files)} tracked Python files...")
    
    for file_path, size_mb in files_to_check:
        filename = file_path.name
        file_path_str = str(file_path)
        referencing_scripts = []
        
        # Search in each Python file
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                # Check for filename, full path, or path with forward slashes
                file_path_unix = file_path_str.replace('\\', '/')
                if (filename in content or 
                    file_path_str in content or 
                    file_path_unix in content or
                    str(file_path.relative_to(Path.cwd())) in content):
                    referencing_scripts.append(str(py_file))
            except (OSError, PermissionError, ValueError):
                continue
        
        if referencing_scripts:
            referenced_files.append((file_path, size_mb, referencing_scripts))
            
    return referenced_files

def get_git_commit():
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()[:7]
    except subprocess.CalledProcessError:
        return "unknown"

def calculate_file_hash(file_path):
    """Calculate SHA256 hash of file"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()[:16]  # First 16 chars for brevity
    except (OSError, PermissionError):
        return "unknown"

def create_manifest(referenced_files, git_commit):
    """Create manifest with file metadata"""
    manifest = {
        "created_at": datetime.now().isoformat(),
        "git_commit": git_commit,
        "files": {}
    }
    
    for file_path, size_mb, scripts in referenced_files:
        file_hash = calculate_file_hash(file_path)
        manifest["files"][str(file_path)] = {
            "size_mb": round(size_mb, 1),
            "sha256_short": file_hash,
            "used_by": scripts
        }
    
    return manifest





def main():
    parser = argparse.ArgumentParser(description="Package data input files for collaboration")
    parser.add_argument("--dry-run", action="store_true", help="Show files without creating zip")
    parser.add_argument("--full", action="store_true", help="Force full backup (default behavior)")
    parser.add_argument("--sizelimit", type=float, help="Exclude files larger than specified size in MB (e.g., --sizelimit 50)")
    args = parser.parse_args()
    
    print("Finding untracked and ignored files...")
    if args.sizelimit:
        print(f"Excluding files larger than {args.sizelimit} MB")
    ignored_files = get_untracked_files(args.sizelimit)
    
    if not ignored_files:
        print("No untracked or ignored files found.")
        return
        
    print(f"Found {len(ignored_files)} untracked and ignored files")
    
    print("\nChecking which files are referenced in tracked Python scripts...")
    referenced = find_files_in_python_scripts(ignored_files)
    
    if not referenced:
        print("No untracked or ignored files are referenced in tracked Python scripts.")
        return
    
    if args.dry_run:
        print(f"\nDRY RUN: Would create full backup with {len(referenced)} files")
        for file_path, size_mb, scripts in referenced:
            print(f"\n{file_path} ({size_mb:.1f} MB)")
            print(f"  Referenced in: {', '.join(scripts[:3])}")
            if len(scripts) > 3:
                print(f"  ... and {len(scripts) - 3} more")
        return
    
    print(f"\n=== FULL BACKUP: {len(referenced)} FILES ===")
    total_size = 0
    for file_path, size_mb, scripts in referenced:
        print(f"\n{file_path} ({size_mb:.1f} MB)")
        print(f"  Referenced in: {', '.join(scripts[:3])}")
        if len(scripts) > 3:
            print(f"  ... and {len(scripts) - 3} more")
        total_size += size_mb
    
    print(f"\nTotal size: {total_size:.1f} MB")
    
    # Ask user confirmation
    response = input(f"\nCreate zip with these {len(referenced)} files? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        git_commit = get_git_commit()
        timestamp = datetime.now().strftime('%d%b%y_%Hh')
        zip_name = f"vervestacks_data_{git_commit}_{timestamp}.zip"
        
        # Create manifest (but don't save to repo - just include in zip)
        manifest = create_manifest(referenced, git_commit)
        
        print(f"\n📦 Creating {zip_name}...")
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add manifest to zip
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            
            for i, (file_path, size_mb, scripts) in enumerate(referenced, 1):
                print(f"Adding [{i}/{len(referenced)}] {file_path.name}")
                zf.write(file_path, str(file_path))
        
        # Create incremental copy with timestamp
        incremental_name = f"vervestacks_data_incremental_{timestamp}.zip"
        import shutil
        shutil.copy2(zip_name, incremental_name)
        
        final_size = Path(zip_name).stat().st_size / (1024*1024)
        print(f"\n✅ Created: {zip_name}")
        print(f"📊 Compressed size: {final_size:.1f} MB")
        print(f"🔄 Incremental copy: {incremental_name}")
        print(f"🏷️  Git commit: {git_commit}")
    else:
        print("Cancelled.")

if __name__ == "__main__":
    main()
