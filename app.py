#!/usr/bin/env python3
"""
CleanSlate MVP - Privacy-First Desktop File Cleaner
A local, offline tool to help users find and delete unneeded files.
"""

import os
import sys
import sqlite3
import hashlib
import csv
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import PySimpleGUI as sg
from send2trash import send2trash

# Prevent Tk icon crashes on macOS
sg.set_options(icon=None, window_icon=None)

# Constants
DB_PATH = Path.home() / ".cleanslate_mvp.sqlite3"
SCAN_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB for partial hash
LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50 MB
OLD_FILE_THRESHOLD = 180  # days
MAX_SIZE_SCORE = 10
MAX_AGE_SCORE = 10
MAX_EXTENSION_BIAS = 10


class CleanSlateDB:
    """SQLite database for learning and persistence."""
    
    def __init__(self, db_path: Path):
        """Initialize database connection and create tables."""
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Actions table - records user actions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                path TEXT PRIMARY KEY,
                ext TEXT NOT NULL,
                action TEXT NOT NULL,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Extension stats table - tracks bias per extension
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ext_stats (
                ext TEXT PRIMARY KEY,
                deletes INTEGER DEFAULT 0,
                keeps INTEGER DEFAULT 0
            )
        """)
        
        self.conn.commit()
    
    def record_action(self, file_path: str, action: str):
        """Record a user action (delete or keep) for a file."""
        ext = Path(file_path).suffix.lower()
        cursor = self.conn.cursor()
        
        # Insert or update action
        cursor.execute("""
            INSERT OR REPLACE INTO actions (path, ext, action, ts)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (file_path, ext, action))
        
        # Update extension stats
        if action == 'delete':
            cursor.execute("""
                INSERT OR REPLACE INTO ext_stats (ext, deletes, keeps)
                VALUES (?, 
                    COALESCE((SELECT deletes FROM ext_stats WHERE ext = ?), 0) + 1,
                    COALESCE((SELECT keeps FROM ext_stats WHERE ext = ?), 0)
                )
            """, (ext, ext, ext))
        else:  # keep
            cursor.execute("""
                INSERT OR REPLACE INTO ext_stats (ext, deletes, keeps)
                VALUES (?, 
                    COALESCE((SELECT deletes FROM ext_stats WHERE ext = ?), 0),
                    COALESCE((SELECT keeps FROM ext_stats WHERE ext = ?), 0) + 1
                )
            """, (ext, ext, ext))
        
        self.conn.commit()
    
    def get_extension_bias(self, ext: str) -> float:
        """Get the bias score for an extension (-10 to +10)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT deletes, keeps FROM ext_stats WHERE ext = ?
        """, (ext,))
        
        row = cursor.fetchone()
        if not row:
            return 0.0
        
        deletes = row['deletes']
        keeps = row['keeps']
        total = deletes + keeps
        
        if total == 0:
            return 0.0
        
        # Calculate bias: (deletes - keeps) / total, scaled to ±10
        ratio = (deletes - keeps) / total
        return ratio * MAX_EXTENSION_BIAS
    
    def close(self):
        """Close database connection."""
        self.conn.close()


class FileScanner:
    """Scans directories and analyzes files."""
    
    def __init__(self, db: CleanSlateDB):
        """Initialize scanner with database for learning."""
        self.db = db
        self.files = []
        self.duplicate_groups = {}
        self.group_counter = 1
    
    def scan_directory(self, directory: Path, progress_callback=None) -> List[Dict]:
        """Scan directory and return file information."""
        self.files = []
        self.duplicate_groups = {}
        self.group_counter = 1
        
        if not directory.exists():
            return []
        
        # Collect all files
        files_to_scan = []
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                files_to_scan.append(file_path)
        
        total_files = len(files_to_scan)
        
        # Process files with progress updates
        for i, file_path in enumerate(files_to_scan):
            try:
                file_info = self._analyze_file(file_path)
                if file_info:
                    self.files.append(file_info)
                
                if progress_callback and i % 10 == 0:
                    progress = (i + 1) / total_files * 100
                    progress_callback(f"Scanning... {i + 1}/{total_files} files ({progress:.1f}%)")
                    
            except (PermissionError, OSError) as e:
                # Skip files we can't access
                continue
        
        # Find duplicate groups
        self._find_duplicates()
        
        if progress_callback:
            progress_callback(f"Scan complete! Found {len(self.files)} files")
        
        return self.files
    
    def _analyze_file(self, file_path: Path) -> Optional[Dict]:
        """Analyze a single file and return metadata."""
        try:
            stat = file_path.stat()
            
            # Calculate partial hash for duplicate detection
            partial_hash = self._calculate_partial_hash(file_path)
            
            # Calculate scores
            size_score = self._calculate_size_score(stat.st_size)
            age_score = self._calculate_age_score(stat.st_mtime)
            ext_bias = self.db.get_extension_bias(file_path.suffix.lower())
            
            total_score = size_score + age_score + ext_bias
            
            return {
                'name': file_path.name,
                'path': str(file_path),
                'size': stat.st_size,
                'size_human': self._format_size(stat.st_size),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'modified_str': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'partial_hash': partial_hash,
                'size_score': size_score,
                'age_score': age_score,
                'ext_bias': ext_bias,
                'total_score': total_score,
                'group': None  # Will be set by _find_duplicates
            }
            
        except (PermissionError, OSError):
            return None
    
    def _calculate_partial_hash(self, file_path: Path) -> str:
        """Calculate partial SHA-256 hash of first 4MB + file size."""
        try:
            with open(file_path, 'rb') as f:
                # Read first 4MB
                data = f.read(SCAN_CHUNK_SIZE)
                # Include file size in hash
                size_bytes = str(file_path.stat().st_size).encode()
                hash_input = data + size_bytes
                return hashlib.sha256(hash_input).hexdigest()
        except (PermissionError, OSError):
            return ""
    
    def _calculate_size_score(self, size_bytes: int) -> float:
        """Calculate size-based score (0-10)."""
        if size_bytes >= LARGE_FILE_THRESHOLD:
            return MAX_SIZE_SCORE
        elif size_bytes == 0:
            return 0.0
        else:
            # Linear interpolation from 0 to threshold
            return (size_bytes / LARGE_FILE_THRESHOLD) * MAX_SIZE_SCORE
    
    def _calculate_age_score(self, mtime: float) -> float:
        """Calculate age-based score (0-10)."""
        age_days = (datetime.now() - datetime.fromtimestamp(mtime)).days
        if age_days >= OLD_FILE_THRESHOLD:
            return MAX_AGE_SCORE
        elif age_days <= 0:
            return 0.0
        else:
            # Linear interpolation from 0 to threshold
            return (age_days / OLD_FILE_THRESHOLD) * MAX_AGE_SCORE
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in human-readable format."""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"
    
    def _find_duplicates(self):
        """Group files by partial hash to identify duplicates."""
        hash_groups = {}
        
        for file_info in self.files:
            partial_hash = file_info['partial_hash']
            if partial_hash:
                if partial_hash not in hash_groups:
                    hash_groups[partial_hash] = []
                hash_groups[partial_hash].append(file_info)
        
        # Assign group numbers to files with duplicates
        for partial_hash, group_files in hash_groups.items():
            if len(group_files) > 1:
                group_id = f"Group {self.group_counter}"
                for file_info in group_files:
                    file_info['group'] = group_id
                self.group_counter += 1


class CleanSlateGUI:
    """Main GUI application."""
    
    def __init__(self):
        """Initialize the GUI."""
        self.db = CleanSlateDB(DB_PATH)
        self.scanner = FileScanner(self.db)
        self.current_files = []
        self.filtered_files = []
        self.selected_folder = ""
        
        # Set theme
        sg.theme('LightGrey1')
        
        # Create window
        self.window = self._create_window()
    
    def _create_window(self) -> sg.Window:
        """Create the main window layout."""
        # Header section
        header_layout = [
            [
                sg.Button("Choose Folder", key="-CHOOSE-", size=(12, 1)),
                sg.Button("Scan", key="-SCAN-", size=(8, 1)),
                sg.Text("No folder selected", key="-FOLDER-", size=(50, 1))
            ]
        ]
        
        # Filters section
        filters_layout = [
            [sg.Text("Filters:", font=("Helvetica", 10, "bold"))],
            [
                sg.Checkbox("Only duplicates", key="-DUPLICATES-"),
                sg.Checkbox("Only old files (180+ days)", key="-OLD-"),
                sg.Checkbox("Only large files (50+ MB)", key="-LARGE-")
            ],
            [
                sg.Text("Min score:"),
                sg.Slider(range=(0, 20), default_value=0, orientation='h', 
                         key="-MIN_SCORE-", size=(20, 15))
            ]
        ]
        
        # Table section
        table_layout = [
            [sg.Text("Files:", font=("Helvetica", 10, "bold"))],
            [
                sg.Table(
                    values=[],
                    headings=["Name", "Path", "Size", "Modified", "Score", "Group"],
                    auto_size_columns=True,
                    justification='left',
                    num_rows=15,
                    key="-TABLE-",
                    enable_events=True,
                    select_mode=sg.TABLE_SELECT_MODE_EXTENDED
                )
            ]
        ]
        
        # Actions section
        actions_layout = [
            [
                sg.Button("Mark Keep", key="-KEEP-", size=(10, 1)),
                sg.Button("Delete Selected", key="-DELETE-", size=(12, 1)),
                sg.Button("Export CSV", key="-EXPORT-", size=(10, 1))
            ]
        ]
        
        # Status section
        status_layout = [
            [sg.Text("Ready", key="-STATUS-", size=(80, 1))]
        ]
        
        # Combine all sections
        layout = [
            header_layout,
            [sg.HSeparator()],
            [
                sg.Column(filters_layout, vertical_alignment='top'),
                sg.VSeparator(),
                sg.Column(table_layout, expand_x=True, expand_y=True)
            ],
            [sg.HSeparator()],
            actions_layout,
            status_layout
        ]
        
        return sg.Window(
            "CleanSlate MVP",
            layout,
            resizable=True,
            finalize=True
        )
    
    def run(self):
        """Run the main event loop."""
        while True:
            event, values = self.window.read()
            
            if event in (sg.WIN_CLOSED, "Exit"):
                break
            
            elif event == "-CHOOSE-":
                folder = sg.popup_get_folder("Choose folder to scan")
                if folder:
                    self.selected_folder = folder
                    self.window["-FOLDER-"].update(f"Selected: {folder}")
            
            elif event == "-SCAN-":
                if not self.selected_folder:
                    sg.popup_error("Please choose a folder first!")
                    continue
                
                self._run_scan()
            
            elif event in ["-DUPLICATES-", "-OLD-", "-LARGE-", "-MIN_SCORE-"]:
                self._apply_filters()
            
            elif event == "-KEEP-":
                self._mark_keep()
            
            elif event == "-DELETE-":
                self._delete_selected()
            
            elif event == "-EXPORT-":
                self._export_csv()
        
        self.db.close()
        self.window.close()
    
    def _run_scan(self):
        """Run file scan in background thread."""
        def scan_worker():
            try:
                self.window["-STATUS-"].update("Starting scan...")
                self.window["-SCAN-"].update(disabled=True)
                
                def progress_callback(message):
                    self.window["-STATUS-"].update(message)
                    self.window.refresh()
                
                # Run scan
                self.current_files = self.scanner.scan_directory(
                    Path(self.selected_folder), 
                    progress_callback
                )
                
                # Update table
                self._update_table()
                self.window["-STATUS-"].update(f"Scan complete! Found {len(self.current_files)} files")
                
            except Exception as e:
                sg.popup_error(f"Scan error: {str(e)}")
                self.window["-STATUS-"].update("Scan failed!")
            finally:
                self.window["-SCAN-"].update(disabled=False)
        
        # Run in background thread
        thread = threading.Thread(target=scan_worker, daemon=True)
        thread.start()
    
    def _update_table(self):
        """Update the table with current files."""
        table_data = []
        for file_info in self.current_files:
            table_data.append([
                file_info['name'],
                file_info['path'],
                file_info['size_human'],
                file_info['modified_str'],
                f"{file_info['total_score']:.2f}",
                file_info['group'] or ""
            ])
        
        self.window["-TABLE-"].update(table_data)
        self.filtered_files = self.current_files.copy()
    
    def _apply_filters(self):
        """Apply current filters to the table."""
        values = self.window.read(timeout=100)[1]
        
        filtered = self.current_files.copy()
        
        # Only duplicates filter
        if values.get("-DUPLICATES-", False):
            filtered = [f for f in filtered if f['group'] is not None]
        
        # Only old files filter
        if values.get("-OLD-", False):
            cutoff_date = datetime.now() - timedelta(days=OLD_FILE_THRESHOLD)
            filtered = [f for f in filtered if f['modified'] < cutoff_date]
        
        # Only large files filter
        if values.get("-LARGE-", False):
            filtered = [f for f in filtered if f['size'] >= LARGE_FILE_THRESHOLD]
        
        # Min score filter
        min_score = values.get("-MIN_SCORE-", 0)
        filtered = [f for f in filtered if f['total_score'] >= min_score]
        
        # Update table
        table_data = []
        for file_info in filtered:
            table_data.append([
                file_info['name'],
                file_info['path'],
                file_info['size_human'],
                file_info['modified_str'],
                f"{file_info['total_score']:.2f}",
                file_info['group'] or ""
            ])
        
        self.window["-TABLE-"].update(table_data)
        self.filtered_files = filtered
    
    def _mark_keep(self):
        """Mark selected files as keep."""
        selected_rows = self.window["-TABLE-"].get_selected_rows()
        if not selected_rows:
            sg.popup_error("Please select files to mark as keep!")
            return
        
        kept_files = []
        for row_index in selected_rows:
            if row_index < len(self.filtered_files):
                file_info = self.filtered_files[row_index]
                self.db.record_action(file_info['path'], 'keep')
                kept_files.append(file_info['name'])
        
        if kept_files:
            sg.popup(f"Marked {len(kept_files)} files as keep:\n" + "\n".join(kept_files[:5]))
            if len(kept_files) > 5:
                sg.popup(f"... and {len(kept_files) - 5} more files")
    
    def _delete_selected(self):
        """Delete selected files (send to trash)."""
        selected_rows = self.window["-TABLE-"].get_selected_rows()
        if not selected_rows:
            sg.popup_error("Please select files to delete!")
            return
        
        # Confirm deletion
        file_count = len(selected_rows)
        response = sg.popup_yes_no(
            f"Send {file_count} file(s) to Trash?\n\n"
            "This will move the files to your system Trash.\n"
            "You can recover them later if needed.",
            title="Confirm Deletion"
        )
        
        if response != "Yes":
            return
        
        # Delete files
        deleted_files = []
        failed_files = []
        
        for row_index in selected_rows:
            if row_index < len(self.filtered_files):
                file_info = self.filtered_files[row_index]
                try:
                    send2trash(file_info['path'])
                    self.db.record_action(file_info['path'], 'delete')
                    deleted_files.append(file_info['name'])
                except Exception as e:
                    failed_files.append(f"{file_info['name']}: {str(e)}")
        
        # Show results
        if deleted_files:
            sg.popup(f"Successfully moved {len(deleted_files)} files to Trash!")
        
        if failed_files:
            sg.popup_error("Failed to delete some files:\n" + "\n".join(failed_files))
        
        # Remove deleted files from current view
        if deleted_files:
            self._remove_deleted_files(deleted_files)
    
    def _remove_deleted_files(self, deleted_names: List[str]):
        """Remove deleted files from the current view."""
        deleted_paths = set()
        for file_info in self.current_files:
            if file_info['name'] in deleted_names:
                deleted_paths.add(file_info['path'])
        
        # Remove from current files
        self.current_files = [f for f in self.current_files if f['path'] not in deleted_paths]
        
        # Remove from filtered files
        self.filtered_files = [f for f in self.filtered_files if f['path'] not in deleted_paths]
        
        # Update table
        self._update_table()
    
    def _export_csv(self):
        """Export current filtered results to CSV."""
        if not self.filtered_files:
            sg.popup_error("No files to export!")
            return
        
        filename = sg.popup_get_file(
            "Save CSV file",
            save_as=True,
            file_types=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([
                    "Name", "Path", "Size (bytes)", "Size (human)", 
                    "Modified", "Size Score", "Age Score", "Extension Bias", 
                    "Total Score", "Group"
                ])
                
                # Write data
                for file_info in self.filtered_files:
                    writer.writerow([
                        file_info['name'],
                        file_info['path'],
                        file_info['size'],
                        file_info['size_human'],
                        file_info['modified'].isoformat(),
                        f"{file_info['size_score']:.2f}",
                        f"{file_info['age_score']:.2f}",
                        f"{file_info['ext_bias']:.2f}",
                        f"{file_info['total_score']:.2f}",
                        file_info['group'] or ""
                    ])
            
            sg.popup(f"Exported {len(self.filtered_files)} files to {filename}")
            
        except Exception as e:
            sg.popup_error(f"Export failed: {str(e)}")


def main():
    """Main entry point."""
    try:
        app = CleanSlateGUI()
        app.run()
    except Exception as e:
        sg.popup_error(f"Application error: {str(e)}")


if __name__ == "__main__":
    main()



