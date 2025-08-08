#!/usr/bin/env python3
"""
CleanSlate Phase 4 - Core Scanning Engine
Minimal prototype for file cleanup scanning with demo mode support.
"""

import os
import hashlib
import datetime
import json
import argparse
from pathlib import Path
from typing import List, Tuple, Dict

# Optional imports for advanced detection
try:
    import cv2
    import numpy as np
    from PIL import Image
    import imagehash
    OPENCV_AVAILABLE = True
    PIL_AVAILABLE = True
    IMAGEHASH_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    PIL_AVAILABLE = False
    IMAGEHASH_AVAILABLE = False
    print("Warning: OpenCV/PIL/imagehash not available. Advanced image detection disabled.")

# Constants for Phase 2 compatibility
REPORT_FILE = "CleanSlate_Report.txt"
REPORT_HTML_FILE = "CleanSlate_Report.html"


def load_config() -> Dict:
    """Load configuration from config.json file."""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            
        # Return the original config structure for Phase 2 compatibility
        return config
            
    except FileNotFoundError:
        # Create default config if file doesn't exist
        default_config = {
            "directories_to_scan": ["demo_data"],
            "large_file_threshold_mb": 100,
            "old_file_threshold_days": 365,
            "excluded_folders": [".git", "node_modules"],
            "excluded_file_types": [".tmp", ".log"]
        }
        save_config(default_config)
        return default_config


def save_config(config: Dict) -> None:
    """Save configuration to config.json file."""
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)


def should_skip_file(file_path: Path, exclusions: Dict) -> bool:
    """Check if file should be skipped based on exclusions."""
    # Check folder exclusions
    for folder in exclusions.get("folders", []):
        if folder in file_path.parts:
            return True
    
    # Check extension exclusions
    file_ext = file_path.suffix.lower()
    if file_ext in exclusions.get("extensions", []):
        return True
    
    return False


def scan_files(paths: List[str], exclusions: Dict) -> List[Path]:
    """Scan directories and return list of accessible files."""
    all_files = []
    
    for path in paths:
        if not os.path.exists(path):
            print(f"Warning: Path does not exist: {path}")
            continue
            
        for root, dirs, files in os.walk(path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in exclusions.get("folders", [])]
            
            for file in files:
                file_path = Path(root) / file
                if not should_skip_file(file_path, exclusions):
                    try:
                        if file_path.is_file() and os.access(file_path, os.R_OK):
                            all_files.append(file_path)
                    except (PermissionError, OSError):
                        continue
    
    return all_files


def find_duplicates(paths: List[str]) -> List[List[str]]:
    """
    Find exact duplicate files using MD5 hash.
    
    Args:
        paths: List of directory paths to scan
        
    Returns:
        List of duplicate file groups (each group is a list of file paths)
    """
    config = load_config()
    # Convert Phase 2 exclusions to Phase 4 format
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    
    # Group files by hash
    hash_groups = {}
    for file_path in files:
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            if file_hash not in hash_groups:
                hash_groups[file_hash] = []
            hash_groups[file_hash].append(str(file_path))
        except (OSError, PermissionError):
            continue
    
    # Return only groups with multiple files (duplicates)
    return [group for group in hash_groups.values() if len(group) > 1]


def find_large_files(paths: List[str], threshold_mb: float) -> List[Tuple[str, float]]:
    """
    Find files larger than the threshold.
    
    Args:
        paths: List of directory paths to scan
        threshold_mb: Size threshold in MB
        
    Returns:
        List of tuples (file_path, size_mb)
    """
    config = load_config()
    # Convert Phase 2 exclusions to Phase 4 format
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    large_files = []
    
    for file_path in files:
        try:
            size_bytes = file_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            
            if size_mb > threshold_mb:
                large_files.append((str(file_path), size_mb))
        except (OSError, PermissionError):
            continue
    
    return large_files


def find_old_files(paths: List[str], threshold_days: int) -> List[Tuple[str, str]]:
    """
    Find files not modified within the threshold period.
    
    Args:
        paths: List of directory paths to scan
        threshold_days: Age threshold in days
        
    Returns:
        List of tuples (file_path, last_modified_date)
    """
    config = load_config()
    # Convert Phase 2 exclusions to Phase 4 format
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    old_files = []
    
    current_time = datetime.datetime.now()
    threshold_time = current_time - datetime.timedelta(days=threshold_days)
    
    for file_path in files:
        try:
            mtime = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if mtime < threshold_time:
                old_files.append((str(file_path), mtime.strftime('%Y-%m-%d %H:%M:%S')))
        except (OSError, PermissionError):
            continue
    
    return old_files


def find_empty_files(paths: List[str]) -> List[str]:
    """
    Find files with zero bytes.
    
    Args:
        paths: List of directory paths to scan
        
    Returns:
        List of file paths
    """
    config = load_config()
    # Convert Phase 2 exclusions to Phase 4 format
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    empty_files = []
    
    for file_path in files:
        try:
            if file_path.stat().st_size == 0:
                empty_files.append(str(file_path))
        except (OSError, PermissionError):
            continue
    
    return empty_files


def find_near_duplicate_images(paths: List[str], similarity_threshold: int = 5) -> Dict[str, List[str]]:
    """
    Find near-duplicate images using perceptual hashing.
    
    Args:
        paths: List of directory paths to scan
        similarity_threshold: Threshold for similarity (0-64)
        
    Returns:
        Dictionary of image groups
    """
    if not (PIL_AVAILABLE and IMAGEHASH_AVAILABLE):
        return {}
    
    config = load_config()
    # Convert Phase 2 exclusions to Phase 4 format
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    image_files = [f for f in files if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']]
    
    # Group images by hash
    hash_groups = {}
    for file_path in image_files:
        try:
            with Image.open(file_path) as img:
                img_hash = imagehash.average_hash(img)
                hash_str = str(img_hash)
                
                if hash_str not in hash_groups:
                    hash_groups[hash_str] = []
                hash_groups[hash_str].append(str(file_path))
        except Exception:
            continue
    
    # Find similar images
    similar_groups = {}
    processed_hashes = set()
    
    for hash1, files1 in hash_groups.items():
        if hash1 in processed_hashes:
            continue
            
        similar_files = files1.copy()
        processed_hashes.add(hash1)
        
        for hash2, files2 in hash_groups.items():
            if hash2 in processed_hashes:
                continue
                
            # Calculate hash difference
            hash_diff = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
            
            if hash_diff <= similarity_threshold:
                similar_files.extend(files2)
                processed_hashes.add(hash2)
        
        if len(similar_files) > 1:
            similar_groups[f"group_{len(similar_groups) + 1}"] = similar_files
    
    return similar_groups


def find_blurry_images(paths: List[str], blur_threshold: float = 100.0) -> List[Tuple[str, float]]:
    """
    Find blurry images using Laplacian variance.
    
    Args:
        paths: List of directory paths to scan
        blur_threshold: Threshold for blur detection
        
    Returns:
        List of tuples (file_path, blur_score)
    """
    if not OPENCV_AVAILABLE:
        return []
    
    config = load_config()
    # Convert Phase 2 exclusions to Phase 4 format
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    image_files = [f for f in files if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']]
    
    blurry_files = []
    
    for file_path in image_files:
        try:
            # Read image with OpenCV
            img = cv2.imread(str(file_path))
            if img is None:
                continue
                
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Calculate Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            if laplacian_var < blur_threshold:
                blurry_files.append((str(file_path), laplacian_var))
        except Exception:
            continue
    
    return blurry_files


def generate_report(duplicates: List[List[str]], 
                   large_files: List[Tuple[str, float]], 
                   old_files: List[Tuple[str, str]],
                   empty_files: List[str] = None,
                   near_duplicates: Dict[str, List[str]] = None,
                   blurry_files: List[Tuple[str, float]] = None,
                   demo_mode: bool = False) -> str:
    """Generate a plain text report."""
    if empty_files is None:
        empty_files = []
    if near_duplicates is None:
        near_duplicates = {}
    if blurry_files is None:
        blurry_files = []
    
    report_lines = []
    report_lines.append("CleanSlate Phase 4 - File Scan Report")
    if demo_mode:
        report_lines.append("🎯 DEMO MODE - Sample Data Scan")
    report_lines.append("=" * 50)
    report_lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # Duplicates section
    report_lines.append("DUPLICATE FILES")
    report_lines.append("-" * 20)
    if duplicates:
        for i, group in enumerate(duplicates, 1):
            report_lines.append(f"Group {i}:")
            for file_path in group:
                report_lines.append(f"  {file_path}")
            report_lines.append("")
    else:
        report_lines.append("No duplicate files found.")
    report_lines.append("")
    
    # Large files section
    report_lines.append("LARGE FILES")
    report_lines.append("-" * 20)
    if large_files:
        for file_path, size_mb in large_files:
            report_lines.append(f"{file_path} ({size_mb:.2f} MB)")
    else:
        report_lines.append("No large files found.")
    report_lines.append("")
    
    # Old files section
    report_lines.append("OLD FILES")
    report_lines.append("-" * 20)
    if old_files:
        for file_path, date in old_files:
            report_lines.append(f"{file_path} (Last modified: {date})")
    else:
        report_lines.append("No old files found.")
    report_lines.append("")
    
    # Empty files section
    report_lines.append("EMPTY FILES")
    report_lines.append("-" * 20)
    if empty_files:
        for file_path in empty_files:
            report_lines.append(f"{file_path}")
    else:
        report_lines.append("No empty files found.")
    report_lines.append("")
    
    # Near-duplicate images section
    if near_duplicates:
        report_lines.append("NEAR-DUPLICATE IMAGES")
        report_lines.append("-" * 20)
        for group_name, files in near_duplicates.items():
            report_lines.append(f"{group_name}:")
            for file_path in files:
                report_lines.append(f"  {file_path}")
            report_lines.append("")
    else:
        report_lines.append("NEAR-DUPLICATE IMAGES")
        report_lines.append("-" * 20)
        report_lines.append("No near-duplicate images found.")
        report_lines.append("")
    
    # Blurry images section
    report_lines.append("BLURRY IMAGES")
    report_lines.append("-" * 20)
    if blurry_files:
        for file_path, blur_score in blurry_files:
            report_lines.append(f"{file_path} (Blur score: {blur_score:.2f})")
    else:
        report_lines.append("No blurry images found.")
    report_lines.append("")
    
    # Summary
    report_lines.append("SUMMARY")
    report_lines.append("-" * 20)
    report_lines.append(f"Duplicate groups: {len(duplicates)}")
    report_lines.append(f"Large files: {len(large_files)}")
    report_lines.append(f"Old files: {len(old_files)}")
    report_lines.append(f"Empty files: {len(empty_files)}")
    report_lines.append(f"Near-duplicate image groups: {len(near_duplicates)}")
    report_lines.append(f"Blurry images: {len(blurry_files)}")
    
    if demo_mode:
        report_lines.append("")
        report_lines.append("🎯 This is a demo scan using sample data.")
        report_lines.append("Switch to real mode to scan your own folders!")
    
    return "\n".join(report_lines)


def run_demo_scan() -> Dict:
    """Run a complete demo scan with all detection rules."""
    config = load_config()
    config["directories_to_scan"] = ["demo_data"]
    config["demo_mode"] = True
    
    print("🎯 CleanSlate Phase 4 - Demo Mode")
    print("Scanning demo data...")
    print("-" * 50)
    
    # Run all detection rules
    duplicates = find_duplicates(config['directories_to_scan'])
    large_files = find_large_files(config['directories_to_scan'], config['large_file_threshold_mb'])
    old_files = find_old_files(config['directories_to_scan'], config['old_file_threshold_days'])
    empty_files = find_empty_files(config['directories_to_scan'])
    near_duplicates = find_near_duplicate_images(config['directories_to_scan'])
    blurry_files = find_blurry_images(config['directories_to_scan'])
    
    # Generate report
    report = generate_report(duplicates, large_files, old_files, 
                           empty_files, near_duplicates, blurry_files, demo_mode=True)
    
    # Save report
    with open('demo_report.txt', 'w') as f:
        f.write(report)
    
    results = {
        'duplicates': duplicates,
        'large_files': large_files,
        'old_files': old_files,
        'empty_files': empty_files,
        'near_duplicates': near_duplicates,
        'blurry_files': blurry_files,
        'report': report
    }
    
    print("Demo scan complete!")
    print(f"Found: {len(duplicates)} duplicate groups, {len(large_files)} large files, {len(old_files)} old files")
    print(f"Empty files: {len(empty_files)}, Near-duplicates: {len(near_duplicates)}, Blurry: {len(blurry_files)}")
    print("Report saved to demo_report.txt")
    
    return results


def run_scan(config: Dict) -> Dict:
    """
    Run a complete scan with all detection rules.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dictionary containing scan results in Phase 2 format
    """
    print("CleanSlate Phase 4 - Scanning...")
    print(f"Scanning paths: {config['directories_to_scan']}")
    print(f"Size threshold: {config['large_file_threshold_mb']} MB")
    print(f"Age threshold: {config['old_file_threshold_days']} days")
    print("-" * 50)
    
    # Convert Phase 2 exclusions to Phase 4 format
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    
    # Count total files scanned
    all_files = scan_files(config['directories_to_scan'], exclusions)
    total_files = len(all_files)
    
    # Run all detection rules
    duplicates_raw = find_duplicates(config['directories_to_scan'])
    large_files = find_large_files(config['directories_to_scan'], config['large_file_threshold_mb'])
    old_files = find_old_files(config['directories_to_scan'], config['old_file_threshold_days'])
    empty_files = find_empty_files(config['directories_to_scan'])
    near_duplicates = find_near_duplicate_images(config['directories_to_scan'])
    blurry_files = find_blurry_images(config['directories_to_scan'])
    
    # Convert duplicates to Phase 2 format (dict with group keys)
    duplicates = {}
    for i, group in enumerate(duplicates_raw):
        duplicates[f"group_{i+1}"] = group
    
    # Generate report
    report = generate_report(duplicates_raw, large_files, old_files, 
                           empty_files, near_duplicates, blurry_files)
    
    # Save report
    with open(REPORT_FILE, 'w') as f:
        f.write(report)
    
    # Return results in Phase 2 format
    results = {
        'total_files': total_files,
        'duplicates': duplicates,
        'large_files': large_files,
        'old_files': old_files,
        'empty_files': empty_files,
        'near_duplicates': near_duplicates,
        'blurry_files': blurry_files,
        'report': report
    }
    
    print("Scan complete! Report saved to report.txt")
    print(f"Found: {len(duplicates)} duplicate groups, {len(large_files)} large files, {len(old_files)} old files")
    
    return results


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='CleanSlate Phase 4 - File Scanner')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode')
    args = parser.parse_args()
    
    if args.demo:
        run_demo_scan()
    else:
        config = load_config()
        run_scan(config)


if __name__ == "__main__":
    main() 