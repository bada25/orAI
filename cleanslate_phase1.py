#!/usr/bin/env python3
"""
CleanSlate Phase 2 - Privacy-first, offline file scanning tool
Scans directories for files that match specific criteria without modifying files.
Now includes configuration file support and report generation.
"""

import os
import hashlib
import datetime
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


# =============================================================================
# CONFIGURATION MANAGEMENT
# =============================================================================

CONFIG_FILE = "config.json"
REPORT_FILE = "CleanSlate_Report.txt"

# Default configuration values
DEFAULT_CONFIG = {
    "directories_to_scan": [
        "/Users/obsa/Documents",
        "/Users/obsa/Downloads", 
        "/Users/obsa/Desktop"
    ],
    "large_file_threshold_mb": 100,
    "old_file_threshold_days": 365,
    "excluded_folders": [],
    "excluded_file_types": []
}

def load_config() -> Dict:
    """
    Load configuration from config.json file.
    Creates the file with default values if it doesn't exist.
    
    Returns:
        Dictionary containing configuration settings
    """
    config_path = Path(CONFIG_FILE)
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Ensure all required keys exist
            for key, default_value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = default_value
                    print(f"Added missing config key: {key}")
            
            return config
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Error reading config file: {e}")
            print("Creating new config file with default values...")
            return save_config(DEFAULT_CONFIG)
    else:
        print(f"Config file '{CONFIG_FILE}' not found. Creating with default values...")
        return save_config(DEFAULT_CONFIG)


def save_config(config: Dict) -> Dict:
    """
    Save configuration to config.json file.
    
    Args:
        config: Configuration dictionary to save
        
    Returns:
        The saved configuration dictionary
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Configuration saved to '{CONFIG_FILE}'")
        return config
    except IOError as e:
        print(f"Warning: Could not save config file: {e}")
        return config


# =============================================================================
# FILE SCANNING FUNCTIONS
# =============================================================================

def should_skip_directory(dir_path: Path, excluded_folders: List[str]) -> bool:
    """
    Check if a directory should be skipped based on exclusion rules.
    
    Args:
        dir_path: Path to the directory
        excluded_folders: List of folder names to exclude
        
    Returns:
        True if directory should be skipped, False otherwise
    """
    dir_name = dir_path.name.lower()
    return dir_name in [folder.lower() for folder in excluded_folders]


def should_skip_file(file_path: Path, excluded_file_types: List[str]) -> bool:
    """
    Check if a file should be skipped based on exclusion rules.
    
    Args:
        file_path: Path to the file
        excluded_file_types: List of file extensions to exclude
        
    Returns:
        True if file should be skipped, False otherwise
    """
    file_extension = file_path.suffix.lower()
    return file_extension in [ext.lower() for ext in excluded_file_types]


def scan_directories(directories: List[str], excluded_folders: List[str], excluded_file_types: List[str]) -> List[Path]:
    """
    Recursively scan directories and collect all file paths.
    Skips excluded folders and file types.
    
    Args:
        directories: List of directory paths to scan
        excluded_folders: List of folder names to exclude
        excluded_file_types: List of file extensions to exclude
        
    Returns:
        List of Path objects for all files found
    """
    all_files = []
    
    for directory in directories:
        dir_path = Path(directory)
        
        if not dir_path.exists():
            print(f"Warning: Directory does not exist: {directory}")
            continue
            
        if not dir_path.is_dir():
            print(f"Warning: Path is not a directory: {directory}")
            continue
    
        try:
            # Walk through all subdirectories
            for root, dirs, files in os.walk(directory):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not should_skip_directory(Path(root) / d, excluded_folders)]
                
                for file in files:
                    file_path = Path(root) / file
                    
                    # Skip excluded file types
                    if should_skip_file(file_path, excluded_file_types):
                        continue
                    
                    try:
                        # Check if file is accessible
                        if file_path.is_file() and os.access(file_path, os.R_OK):
                            all_files.append(file_path)
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Cannot access file {file_path}: {e}")
                        
        except (PermissionError, OSError) as e:
            print(f"Warning: Cannot scan directory {directory}: {e}")
    
    return all_files


def collect_file_metadata(file_path: Path) -> Dict:
    """
    Collect metadata for a single file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary containing file metadata
    """
    try:
        stat = file_path.stat()
        
        # Convert timestamps to datetime objects
        modified_time = datetime.datetime.fromtimestamp(stat.st_mtime)
        accessed_time = datetime.datetime.fromtimestamp(stat.st_atime)
        
        # Calculate file size in MB
        size_mb = round(stat.st_size / (1024 * 1024), 2)
        
        return {
            'path': file_path,
            'size_mb': size_mb,
            'modified_date': modified_time,
            'accessed_date': accessed_time,
            'absolute_path': str(file_path.absolute())
        }
        
    except (OSError, PermissionError) as e:
        print(f"Warning: Cannot read metadata for {file_path}: {e}")
        return None


# =============================================================================
# DETECTION RULES
# =============================================================================

def detect_duplicates(files_metadata: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Detect duplicate files based on MD5 hash of file contents.
    
    Args:
        files_metadata: List of file metadata dictionaries
        
    Returns:
        Dictionary mapping hash to list of duplicate files
    """
    hash_to_files = defaultdict(list)
    
    for file_info in files_metadata:
        if file_info is None:
            continue
            
        try:
            # Calculate MD5 hash of file contents
            with open(file_info['path'], 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            hash_to_files[file_hash].append(file_info)
            
        except (OSError, PermissionError) as e:
            print(f"Warning: Cannot read file for hash calculation {file_info['path']}: {e}")
    
    # Return only hashes with multiple files (duplicates)
    return {hash_val: files for hash_val, files in hash_to_files.items() 
            if len(files) > 1}


def detect_large_files(files_metadata: List[Dict], threshold_mb: float) -> List[Dict]:
    """
    Detect files larger than the threshold.
    
    Args:
        files_metadata: List of file metadata dictionaries
        threshold_mb: Size threshold in MB
        
    Returns:
        List of large file metadata dictionaries
    """
    large_files = []
    
    for file_info in files_metadata:
        if file_info is None:
            continue
            
        if file_info['size_mb'] > threshold_mb:
            large_files.append(file_info)
    
    return large_files


def detect_old_files(files_metadata: List[Dict], threshold_days: int) -> List[Dict]:
    """
    Detect files not accessed within the threshold period.
    
    Args:
        files_metadata: List of file metadata dictionaries
        threshold_days: Age threshold in days
        
    Returns:
        List of old file metadata dictionaries
    """
    old_files = []
    current_date = datetime.datetime.now()
    threshold_date = current_date - datetime.timedelta(days=threshold_days)
    
    for file_info in files_metadata:
        if file_info is None:
            continue
            
        if file_info['accessed_date'] < threshold_date:
            old_files.append(file_info)
    
    return old_files


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(scan_start_time: datetime.datetime, total_files: int, 
                   duplicates: Dict, large_files: List, old_files: List,
                   config: Dict) -> None:
    """
    Generate a comprehensive report and save it to file.
    
    Args:
        scan_start_time: When the scan started
        total_files: Total number of files scanned
        duplicates: Dictionary of duplicate file groups
        large_files: List of large files
        old_files: List of old files
        config: Configuration dictionary
    """
    report_lines = []
    
    # Header
    report_lines.append("🧹 CleanSlate Phase 2 - File Scanner Report")
    report_lines.append("=" * 80)
    report_lines.append(f"Scan Date: {scan_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Configuration: {CONFIG_FILE}")
    report_lines.append("=" * 80)
    
    # Configuration summary
    report_lines.append("\n📋 CONFIGURATION SUMMARY")
    report_lines.append("-" * 40)
    report_lines.append(f"Directories scanned: {len(config['directories_to_scan'])}")
    for dir_path in config['directories_to_scan']:
        report_lines.append(f"  - {dir_path}")
    report_lines.append(f"Large file threshold: {config['large_file_threshold_mb']} MB")
    report_lines.append(f"Old file threshold: {config['old_file_threshold_days']} days")
    report_lines.append(f"Excluded folders: {config['excluded_folders']}")
    report_lines.append(f"Excluded file types: {config['excluded_file_types']}")
    
    # Scan summary
    report_lines.append("\n📊 SCAN SUMMARY")
    report_lines.append("-" * 40)
    report_lines.append(f"Total files scanned: {total_files}")
    report_lines.append(f"Duplicate groups found: {len(duplicates)}")
    report_lines.append(f"Large files found: {len(large_files)}")
    report_lines.append(f"Old files found: {len(old_files)}")
    
    total_flagged = len(large_files) + len(old_files)
    for duplicate_group in duplicates.values():
        total_flagged += len(duplicate_group) - 1  # Count duplicates (excluding original)
    
    report_lines.append(f"Total flagged files: {total_flagged}")
    
    # Duplicate files section
    if duplicates:
        report_lines.append(f"\n🔍 DUPLICATE FILES ({len(duplicates)} groups)")
        report_lines.append("=" * 80)
        
        for hash_val, files in duplicates.items():
            report_lines.append(f"\n📁 Duplicate Group (Hash: {hash_val[:8]}...):")
            for i, file_info in enumerate(files, 1):
                report_lines.append(f"  {i}. {file_info['absolute_path']}")
                report_lines.append(f"     Size: {file_info['size_mb']} MB")
                report_lines.append(f"     Last accessed: {file_info['accessed_date'].strftime('%Y-%m-%d %H:%M')}")
                report_lines.append(f"     Last modified: {file_info['modified_date'].strftime('%Y-%m-%d %H:%M')}")
    else:
        report_lines.append("\n✅ No duplicate files found.")
    
    # Large files section
    if large_files:
        report_lines.append(f"\n📏 LARGE FILES (> {config['large_file_threshold_mb']} MB)")
        report_lines.append("=" * 80)
        
        for file_info in large_files:
            report_lines.append(f"\n📄 {file_info['absolute_path']}")
            report_lines.append(f"   Size: {file_info['size_mb']} MB")
            report_lines.append(f"   Last accessed: {file_info['accessed_date'].strftime('%Y-%m-%d %H:%M')}")
            report_lines.append(f"   Last modified: {file_info['modified_date'].strftime('%Y-%m-%d %H:%M')}")
    else:
        report_lines.append(f"\n✅ No files larger than {config['large_file_threshold_mb']} MB found.")
    
    # Old files section
    if old_files:
        report_lines.append(f"\n⏰ OLD FILES (> {config['old_file_threshold_days']} days since last access)")
        report_lines.append("=" * 80)
        
        current_date = datetime.datetime.now()
        for file_info in old_files:
            days_old = (current_date - file_info['accessed_date']).days
            report_lines.append(f"\n📄 {file_info['absolute_path']}")
            report_lines.append(f"   Size: {file_info['size_mb']} MB")
            report_lines.append(f"   Last accessed: {file_info['accessed_date'].strftime('%Y-%m-%d %H:%M')} ({days_old} days ago)")
            report_lines.append(f"   Last modified: {file_info['modified_date'].strftime('%Y-%m-%d %H:%M')}")
    else:
        report_lines.append(f"\n✅ No files older than {config['old_file_threshold_days']} days found.")
    
    # Footer
    report_lines.append("\n" + "=" * 80)
    report_lines.append("✅ Scan complete! No files were modified or deleted.")
    report_lines.append("💡 This is Phase 2 - scanning, flagging, and reporting.")
    
    # Write report to file
    try:
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        print(f"\n📄 Report saved to '{REPORT_FILE}'")
    except IOError as e:
        print(f"Warning: Could not save report file: {e}")


# =============================================================================
# OUTPUT FUNCTIONS (Console Display)
# =============================================================================

def print_duplicates(duplicates: Dict[str, List[Dict]]):
    """Print duplicate files grouped by hash."""
    if not duplicates:
        print("\n✅ No duplicate files found.")
        return
    
    print(f"\n🔍 DUPLICATE FILES ({len(duplicates)} groups):")
    print("=" * 80)
    
    for hash_val, files in duplicates.items():
        print(f"\n📁 Duplicate Group (Hash: {hash_val[:8]}...):")
        for i, file_info in enumerate(files, 1):
            print(f"  {i}. {file_info['absolute_path']}")
            print(f"     Size: {file_info['size_mb']} MB")
            print(f"     Last accessed: {file_info['accessed_date'].strftime('%Y-%m-%d %H:%M')}")
            print(f"     Last modified: {file_info['modified_date'].strftime('%Y-%m-%d %H:%M')}")


def print_large_files(large_files: List[Dict], threshold_mb: float):
    """Print large files."""
    if not large_files:
        print(f"\n✅ No files larger than {threshold_mb} MB found.")
        return
    
    print(f"\n📏 LARGE FILES (> {threshold_mb} MB):")
    print("=" * 80)
    
    for file_info in large_files:
        print(f"\n📄 {file_info['absolute_path']}")
        print(f"   Size: {file_info['size_mb']} MB")
        print(f"   Last accessed: {file_info['accessed_date'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Last modified: {file_info['modified_date'].strftime('%Y-%m-%d %H:%M')}")


def print_old_files(old_files: List[Dict], threshold_days: int):
    """Print old files."""
    if not old_files:
        print(f"\n✅ No files older than {threshold_days} days found.")
        return
    
    print(f"\n⏰ OLD FILES (> {threshold_days} days since last access):")
    print("=" * 80)
    
    current_date = datetime.datetime.now()
    for file_info in old_files:
        days_old = (current_date - file_info['accessed_date']).days
        print(f"\n📄 {file_info['absolute_path']}")
        print(f"   Size: {file_info['size_mb']} MB")
        print(f"   Last accessed: {file_info['accessed_date'].strftime('%Y-%m-%d %H:%M')} ({days_old} days ago)")
        print(f"   Last modified: {file_info['modified_date'].strftime('%Y-%m-%d %H:%M')}")


def print_summary(total_files: int, duplicates: Dict, large_files: List, old_files: List):
    """Print summary statistics."""
    print("\n" + "=" * 80)
    print("📊 SCAN SUMMARY")
    print("=" * 80)
    print(f"Total files scanned: {total_files}")
    print(f"Duplicate groups found: {len(duplicates)}")
    print(f"Large files found: {len(large_files)}")
    print(f"Old files found: {len(old_files)}")
    
    total_flagged = len(large_files) + len(old_files)
    for duplicate_group in duplicates.values():
        total_flagged += len(duplicate_group) - 1  # Count duplicates (excluding original)
    
    print(f"Total flagged files: {total_flagged}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function."""
    print("🧹 CleanSlate Phase 2 - File Scanner")
    print("=" * 80)
    
    # Load configuration
    config = load_config()
    
    print(f"Configuration loaded from '{CONFIG_FILE}'")
    print(f"Directories to scan: {len(config['directories_to_scan'])}")
    print(f"Large file threshold: {config['large_file_threshold_mb']} MB")
    print(f"Old file threshold: {config['old_file_threshold_days']} days")
    print(f"Excluded folders: {config['excluded_folders']}")
    print(f"Excluded file types: {config['excluded_file_types']}")
    print("=" * 80)
    
    # Record scan start time
    scan_start_time = datetime.datetime.now()
    
    # Step 1: Scan directories
    print("\n🔍 Scanning directories...")
    all_files = scan_directories(
        config['directories_to_scan'],
        config['excluded_folders'],
        config['excluded_file_types']
    )
    print(f"Found {len(all_files)} files to analyze")
    
    # Step 2: Collect metadata
    print("📊 Collecting file metadata...")
    files_metadata = []
    for file_path in all_files:
        metadata = collect_file_metadata(file_path)
        if metadata:
            files_metadata.append(metadata)
    
    print(f"Successfully collected metadata for {len(files_metadata)} files")
    
    # Step 3: Apply detection rules
    print("🔍 Applying detection rules...")
    duplicates = detect_duplicates(files_metadata)
    large_files = detect_large_files(files_metadata, config['large_file_threshold_mb'])
    old_files = detect_old_files(files_metadata, config['old_file_threshold_days'])
    
    # Step 4: Display results to console
    print_duplicates(duplicates)
    print_large_files(large_files, config['large_file_threshold_mb'])
    print_old_files(old_files, config['old_file_threshold_days'])
    print_summary(len(files_metadata), duplicates, large_files, old_files)
    
    # Step 5: Generate report
    generate_report(scan_start_time, len(files_metadata), duplicates, large_files, old_files, config)
    
    print("\n✅ Scan complete! No files were modified or deleted.")
    print("💡 This is Phase 2 - scanning, flagging, and reporting.")


if __name__ == "__main__":
    main() 