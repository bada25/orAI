#!/usr/bin/env python3
"""
LocalMind Phase 2 - Backward Compatible Version
Privacy-first, offline file scanning tool with configuration and reporting.
This version maintains Phase 2 compatibility while using Phase 3 core.
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cleanslate_core import (
    load_config, run_scan, 
    REPORT_FILE, REPORT_HTML_FILE
)


def main():
    """Main execution function for Phase 2 compatibility."""
    print("🧹 LocalMind Phase 2 - File Scanner")
    print("Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.")
    print("=" * 80)
    
    # Load configuration
    config = load_config()
    
    print(f"Configuration loaded from 'config.json'")
    print(f"Directories to scan: {len(config['directories_to_scan'])}")
    print(f"Large file threshold: {config['large_file_threshold_mb']} MB")
    print(f"Old file threshold: {config['old_file_threshold_days']} days")
    print(f"Excluded folders: {config['excluded_folders']}")
    print(f"Excluded file types: {config['excluded_file_types']}")
    print("=" * 80)
    
    # Run scan without progress callback for console output
    print("\n🔍 Starting scan...")
    scan_results = run_scan(config)
    
    # Display results to console
    print("\n" + "=" * 80)
    print("📊 SCAN RESULTS")
    print("=" * 80)
    print(f"Total files scanned: {scan_results['total_files']}")
    print(f"Duplicate groups found: {len(scan_results['duplicates'])}")
    print(f"Large files found: {len(scan_results['large_files'])}")
    print(f"Old files found: {len(scan_results['old_files'])}")
    print(f"Empty files found: {len(scan_results['empty_files'])}")
    print(f"Near-duplicate image groups: {len(scan_results['near_duplicates'])}")
    print(f"Blurry images found: {len(scan_results['blurry_files'])}")
    
    # Calculate total flagged files
    total_flagged = (len(scan_results['large_files']) + 
                    len(scan_results['old_files']) + 
                    len(scan_results['empty_files']) + 
                    len(scan_results['blurry_files']))
    
    for duplicate_group in scan_results['duplicates'].values():
        total_flagged += len(duplicate_group) - 1  # Count duplicates (excluding original)
    
    for near_duplicate_group in scan_results['near_duplicates'].values():
        total_flagged += len(near_duplicate_group) - 1  # Count near-duplicates (excluding original)
    
    print(f"Total flagged files: {total_flagged}")
    
    print("\n✅ Scan complete! No files were modified or deleted.")
    print("💡 This is Phase 2 - scanning, flagging, and reporting.")
    print(f"📄 Reports saved to '{REPORT_FILE}' and '{REPORT_HTML_FILE}'")


if __name__ == "__main__":
    main() 