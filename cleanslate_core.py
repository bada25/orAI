#!/usr/bin/env python3
"""
LocalMind Core - Privacy-first, offline file scanning engine
Advanced file analysis with AI-powered content detection and media optimization.
"""

import os
import sys
import json
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import imagehash
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
import jieba
import re

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Constants
REPORT_FILE = "LocalMind_Report.txt"
REPORT_HTML_FILE = "LocalMind_Report.html"

# Default configuration
DEFAULT_CONFIG = {
    "directories_to_scan": ["demo_data"],
    "large_file_threshold_mb": 100,
    "old_file_threshold_days": 365,
    "excluded_folders": [".git", "node_modules"],
    "excluded_file_types": [".tmp", ".log"]
}


def load_config() -> Dict:
    """Load configuration from config.json file."""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        # Return the original config structure for Phase 2 compatibility
        return config
    except FileNotFoundError:
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


def scan_files(paths: List[str], exclusions: Dict) -> List[str]:
    """Scan files from given paths, excluding specified folders and file types."""
    all_files = []
    
    for path in paths:
        if not os.path.exists(path):
            print(f"Warning: Path does not exist: {path}")
            continue
            
        for root, dirs, files in os.walk(path):
            # Skip excluded folders
            dirs[:] = [d for d in dirs if d not in exclusions.get("folders", [])]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip excluded file types
                if any(file.endswith(ext) for ext in exclusions.get("extensions", [])):
                    continue
                
                all_files.append(file_path)
    
    return all_files


def find_duplicates(paths: List[str]) -> List[List[str]]:
    """Find duplicate files using MD5 hash."""
    config = load_config()
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    
    # Group files by size first (files with different sizes can't be duplicates)
    size_groups = {}
    for file_path in files:
        try:
            size = os.path.getsize(file_path)
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(file_path)
        except (OSError, PermissionError):
            continue
    
    # Find duplicates within each size group
    duplicates = []
    for size, file_list in size_groups.items():
        if len(file_list) < 2:
            continue
        
        # Calculate MD5 hash for files with same size
        hash_groups = {}
        for file_path in file_list:
            try:
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append(file_path)
            except (OSError, PermissionError):
                continue
        
        # Add groups with multiple files (duplicates)
        for file_hash, duplicate_files in hash_groups.items():
            if len(duplicate_files) > 1:
                duplicates.append(duplicate_files)
    
    return duplicates


def find_large_files(paths: List[str], threshold_mb: int) -> List[str]:
    """Find files larger than the specified threshold."""
    config = load_config()
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    
    large_files = []
    threshold_bytes = threshold_mb * 1024 * 1024
    
    for file_path in files:
        try:
            if os.path.getsize(file_path) > threshold_bytes:
                large_files.append(file_path)
        except (OSError, PermissionError):
            continue
    
    return large_files


def find_old_files(paths: List[str], threshold_days: int) -> List[str]:
    """Find files older than the specified threshold."""
    config = load_config()
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    
    old_files = []
    cutoff_time = datetime.now() - timedelta(days=threshold_days)
    
    for file_path in files:
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if mtime < cutoff_time:
                old_files.append(file_path)
        except (OSError, PermissionError):
            continue
    
    return old_files


def find_empty_files(paths: List[str]) -> List[str]:
    """Find empty files."""
    config = load_config()
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    
    empty_files = []
    
    for file_path in files:
        try:
            if os.path.getsize(file_path) == 0:
                empty_files.append(file_path)
        except (OSError, PermissionError):
            continue
    
    return empty_files


def find_near_duplicate_images(paths: List[str]) -> Dict[str, List[str]]:
    """Find near-duplicate images using perceptual hashing."""
    config = load_config()
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    
    # Filter for image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    image_files = [f for f in files if Path(f).suffix.lower() in image_extensions]
    
    if not image_files:
        return {}
    
    # Calculate perceptual hashes
    hash_data = []
    for file_path in image_files:
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculate perceptual hash
                phash = imagehash.phash(img)
                hash_data.append((file_path, phash))
        except Exception:
            continue
    
    # Group similar images
    near_duplicates = {}
    processed = set()
    
    for i, (file1, hash1) in enumerate(hash_data):
        if file1 in processed:
            continue
        
        similar_files = [file1]
        processed.add(file1)
        
        for j, (file2, hash2) in enumerate(hash_data[i+1:], i+1):
            if file2 in processed:
                continue
            
            # Calculate hash difference
            hash_diff = hash1 - hash2
            
            # Consider images similar if hash difference is small
            if hash_diff <= 10:  # Threshold for similarity
                similar_files.append(file2)
                processed.add(file2)
        
        if len(similar_files) > 1:
            group_key = f"near_duplicate_group_{len(near_duplicates) + 1}"
            near_duplicates[group_key] = similar_files
    
    return near_duplicates


def find_blurry_images(paths: List[str]) -> List[str]:
    """Find blurry images using Laplacian variance."""
    config = load_config()
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    files = scan_files(paths, exclusions)
    
    # Filter for image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    image_files = [f for f in files if Path(f).suffix.lower() in image_extensions]
    
    blurry_files = []
    
    for file_path in image_files:
        try:
            # Read image with OpenCV
            img = cv2.imread(file_path)
            if img is None:
                continue
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Calculate Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Consider image blurry if variance is low
            if laplacian_var < 100:  # Threshold for blur detection
                blurry_files.append(file_path)
                
        except Exception:
            continue
    
    return blurry_files


def generate_report(duplicates: List[List[str]], large_files: List[str], 
                   old_files: List[str], empty_files: List[str],
                   near_duplicates: Dict[str, List[str]], blurry_files: List[str]) -> str:
    """Generate a comprehensive report of all findings."""
    
    report = []
    report.append("=" * 80)
    report.append("LocalMind - Privacy-First File Scanner Report")
    report.append("Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.")
    report.append("=" * 80)
    report.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary
    total_duplicate_files = sum(len(group) for group in duplicates)
    total_near_duplicate_files = sum(len(group) for group in near_duplicates.values())
    
    report.append("SUMMARY")
    report.append("-" * 40)
    report.append(f"Duplicate groups found: {len(duplicates)}")
    report.append(f"Total duplicate files: {total_duplicate_files}")
    report.append(f"Large files found: {len(large_files)}")
    report.append(f"Old files found: {len(old_files)}")
    report.append(f"Empty files found: {len(empty_files)}")
    report.append(f"Near-duplicate image groups: {len(near_duplicates)}")
    report.append(f"Total near-duplicate files: {total_near_duplicate_files}")
    report.append(f"Blurry images found: {len(blurry_files)}")
    report.append("")
    
    # Duplicates
    if duplicates:
        report.append("DUPLICATE FILES")
        report.append("-" * 40)
        for i, group in enumerate(duplicates, 1):
            report.append(f"Group {i}:")
            for file_path in group:
                size = os.path.getsize(file_path)
                report.append(f"  {file_path} ({size:,} bytes)")
            report.append("")
    
    # Large files
    if large_files:
        report.append("LARGE FILES")
        report.append("-" * 40)
        for file_path in large_files:
            size = os.path.getsize(file_path)
            report.append(f"{file_path} ({size:,} bytes)")
        report.append("")
    
    # Old files
    if old_files:
        report.append("OLD FILES")
        report.append("-" * 40)
        for file_path in old_files:
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            report.append(f"{file_path} (modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
        report.append("")
    
    # Empty files
    if empty_files:
        report.append("EMPTY FILES")
        report.append("-" * 40)
        for file_path in empty_files:
            report.append(file_path)
        report.append("")
    
    # Near-duplicate images
    if near_duplicates:
        report.append("NEAR-DUPLICATE IMAGES")
        report.append("-" * 40)
        for group_name, file_list in near_duplicates.items():
            report.append(f"{group_name}:")
            for file_path in file_list:
                report.append(f"  {file_path}")
            report.append("")
    
    # Blurry images
    if blurry_files:
        report.append("BLURRY IMAGES")
        report.append("-" * 40)
        for file_path in blurry_files:
            report.append(file_path)
        report.append("")
    
    report.append("=" * 80)
    report.append("End of Report")
    report.append("=" * 80)
    
    return "\n".join(report)


def generate_html_report(duplicates: List[List[str]], large_files: List[str], 
                        old_files: List[str], empty_files: List[str],
                        near_duplicates: Dict[str, List[str]], blurry_files: List[str]) -> str:
    """Generate an HTML report of all findings."""
    
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html lang='en'>")
    html.append("<head>")
    html.append("    <meta charset='UTF-8'>")
    html.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html.append("    <title>LocalMind Report</title>")
    html.append("    <style>")
    html.append("        body { font-family: Arial, sans-serif; margin: 20px; }")
    html.append("        .header { text-align: center; margin-bottom: 30px; }")
    html.append("        .section { margin: 20px 0; }")
    html.append("        .file-list { background: #f5f5f5; padding: 10px; border-radius: 5px; }")
    html.append("        .file-item { margin: 5px 0; font-family: monospace; }")
    html.append("        .summary { background: #e8f4fd; padding: 15px; border-radius: 5px; }")
    html.append("        .tagline { color: #666; font-style: italic; }")
    html.append("    </style>")
    html.append("</head>")
    html.append("<body>")
    
    # Header
    html.append("    <div class='header'>")
    html.append("        <h1>LocalMind Report</h1>")
    html.append("        <p class='tagline'>Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.</p>")
    html.append(f"        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
    html.append("    </div>")
    
    # Summary
    total_duplicate_files = sum(len(group) for group in duplicates)
    total_near_duplicate_files = sum(len(group) for group in near_duplicates.values())
    
    html.append("    <div class='summary'>")
    html.append("        <h2>Summary</h2>")
    html.append(f"        <p><strong>Duplicate groups:</strong> {len(duplicates)}</p>")
    html.append(f"        <p><strong>Total duplicate files:</strong> {total_duplicate_files}</p>")
    html.append(f"        <p><strong>Large files:</strong> {len(large_files)}</p>")
    html.append(f"        <p><strong>Old files:</strong> {len(old_files)}</p>")
    html.append(f"        <p><strong>Empty files:</strong> {len(empty_files)}</p>")
    html.append(f"        <p><strong>Near-duplicate image groups:</strong> {len(near_duplicates)}</p>")
    html.append(f"        <p><strong>Total near-duplicate files:</strong> {total_near_duplicate_files}</p>")
    html.append(f"        <p><strong>Blurry images:</strong> {len(blurry_files)}</p>")
    html.append("    </div>")
    
    # Duplicates
    if duplicates:
        html.append("    <div class='section'>")
        html.append("        <h2>Duplicate Files</h2>")
        for i, group in enumerate(duplicates, 1):
            html.append(f"        <h3>Group {i}</h3>")
            html.append("        <div class='file-list'>")
            for file_path in group:
                size = os.path.getsize(file_path)
                html.append(f"            <div class='file-item'>{file_path} ({size:,} bytes)</div>")
            html.append("        </div>")
        html.append("    </div>")
    
    # Large files
    if large_files:
        html.append("    <div class='section'>")
        html.append("        <h2>Large Files</h2>")
        html.append("        <div class='file-list'>")
        for file_path in large_files:
            size = os.path.getsize(file_path)
            html.append(f"            <div class='file-item'>{file_path} ({size:,} bytes)</div>")
        html.append("        </div>")
        html.append("    </div>")
    
    # Old files
    if old_files:
        html.append("    <div class='section'>")
        html.append("        <h2>Old Files</h2>")
        html.append("        <div class='file-list'>")
        for file_path in old_files:
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            html.append(f"            <div class='file-item'>{file_path} (modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')})</div>")
        html.append("        </div>")
        html.append("    </div>")
    
    # Empty files
    if empty_files:
        html.append("    <div class='section'>")
        html.append("        <h2>Empty Files</h2>")
        html.append("        <div class='file-list'>")
        for file_path in empty_files:
            html.append(f"            <div class='file-item'>{file_path}</div>")
        html.append("        </div>")
        html.append("    </div>")
    
    # Near-duplicate images
    if near_duplicates:
        html.append("    <div class='section'>")
        html.append("        <h2>Near-Duplicate Images</h2>")
        for group_name, file_list in near_duplicates.items():
            html.append(f"        <h3>{group_name}</h3>")
            html.append("        <div class='file-list'>")
            for file_path in file_list:
                html.append(f"            <div class='file-item'>{file_path}</div>")
            html.append("        </div>")
        html.append("    </div>")
    
    # Blurry images
    if blurry_files:
        html.append("    <div class='section'>")
        html.append("        <h2>Blurry Images</h2>")
        html.append("        <div class='file-list'>")
        for file_path in blurry_files:
            html.append(f"            <div class='file-item'>{file_path}</div>")
        html.append("        </div>")
        html.append("    </div>")
    
    html.append("</body>")
    html.append("</html>")
    
    return "\n".join(html)


def run_scan(config: Dict) -> Dict:
    """Run a complete scan with the given configuration."""
    # Convert Phase 2 exclusions to Phase 4 format for internal functions
    exclusions = {
        "folders": config.get("excluded_folders", []),
        "extensions": config.get("excluded_file_types", [])
    }
    all_files = scan_files(config['directories_to_scan'], exclusions)
    total_files = len(all_files)

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

    report = generate_report(duplicates_raw, large_files, old_files,
                            empty_files, near_duplicates, blurry_files)

    with open(REPORT_FILE, 'w') as f:
        f.write(report)

    # Generate HTML report
    html_report = generate_html_report(duplicates_raw, large_files, old_files,
                                     empty_files, near_duplicates, blurry_files)
    
    with open(REPORT_HTML_FILE, 'w') as f:
        f.write(html_report)

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
    return results


def run_demo_scan():
    """Run a demo scan with default settings."""
    config = load_config()
    print("🧹 LocalMind - Privacy-First File Scanner")
    print("Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.")
    print("=" * 80)
    
    print(f"Scanning directories: {config['directories_to_scan']}")
    print(f"Large file threshold: {config['large_file_threshold_mb']} MB")
    print(f"Old file threshold: {config['old_file_threshold_days']} days")
    print("=" * 80)
    
    results = run_scan(config)
    
    print("\n📊 SCAN RESULTS")
    print("=" * 80)
    print(f"Total files scanned: {results['total_files']}")
    print(f"Duplicate groups found: {len(results['duplicates'])}")
    print(f"Large files found: {len(results['large_files'])}")
    print(f"Old files found: {len(results['old_files'])}")
    print(f"Empty files found: {len(results['empty_files'])}")
    print(f"Near-duplicate image groups: {len(results['near_duplicates'])}")
    print(f"Blurry images found: {len(results['blurry_files'])}")
    
    print(f"\n📄 Reports saved to '{REPORT_FILE}' and '{REPORT_HTML_FILE}'")
    print("✅ Scan complete! No files were modified or deleted.")


def main():
    """Main entry point for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LocalMind - Privacy-First File Scanner")
    parser.add_argument("--demo", action="store_true", help="Run demo scan with default settings")
    parser.add_argument("--config", help="Path to config file")
    
    args = parser.parse_args()
    
    if args.demo:
        run_demo_scan()
    else:
        # Run with loaded config
        config = load_config()
        results = run_scan(config)
        print(f"Scan complete. Found {results['total_files']} files.")
        print(f"Reports saved to '{REPORT_FILE}' and '{REPORT_HTML_FILE}'")


if __name__ == "__main__":
    main() 