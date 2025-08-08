#!/usr/bin/env python3
"""
CleanSlate Phase 3 - GUI Interface
Cross-platform GUI wrapper for the CleanSlate file scanning engine.
"""

import os
import json
from pathlib import Path
import PySimpleGUI as sg
from typing import Dict, List, Optional, Tuple

# Suppress Tkinter deprecation warnings on macOS
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# 1) Clear any global default icon PySimpleGUI might try to use
try:
    sg.set_global_icon(None)  # Works on newer PySimpleGUI
except Exception:
    pass

try:
    sg.set_options(icon=None)  # Older helper that sometimes does not clear the default
except Exception:
    pass

# 2) Hard-stop any attempt to set an icon on the window
def _no_icon(self, *args, **kwargs):
    return

try:
    sg.Window._set_icon = _no_icon  # Monkey-patch the internal setter
    sg.Window.set_icon = _no_icon   # Also patch the public method
except Exception:
    pass

# 3) Belt and suspenders for older versions that store a baked-in base64 icon
try:
    sg.DEFAULT_BASE64_ICON = None  # Prevent fallback base64 icon usage
except Exception:
    pass

# 4) Nuclear option - patch tkinter.PhotoImage to prevent crashes
import tkinter
original_PhotoImage = tkinter.PhotoImage

def safe_PhotoImage(*args, **kwargs):
    """Safe PhotoImage that doesn't crash on malformed data."""
    try:
        return original_PhotoImage(*args, **kwargs)
    except Exception:
        # Return a dummy image that won't crash
        return original_PhotoImage(width=1, height=1)

tkinter.PhotoImage = safe_PhotoImage

# 5) Clear any window icon attributes
try:
    sg.Window.WindowIcon = None
except Exception:
    pass

from cleanslate_core import (
    load_config, save_config, run_scan,
    REPORT_FILE, REPORT_HTML_FILE
)

# Constants
DEFAULT_CONFIG = {
    "directories_to_scan": [],
    "large_file_threshold_mb": 100,
    "old_file_threshold_days": 365,
    "excluded_folders": [".git", "node_modules"],
    "excluded_file_types": [".tmp", ".log"],
    "exclude_paths": []
}

class CleanSlateGUI:
    """Main GUI wrapper for CleanSlate."""
    
    def __init__(self):
        """Initialize the GUI with default settings."""
        self.config = self._load_or_create_config()
        self.current_results = None
        self.window = None
        
        # Set theme
        sg.theme('LightGrey1')
    
    def _load_or_create_config(self) -> Dict:
        """Load config or create with defaults if missing."""
        try:
            cfg = load_config()
        except (FileNotFoundError, json.JSONDecodeError):
            save_config(DEFAULT_CONFIG)
            cfg = DEFAULT_CONFIG.copy()
        # Ensure optional keys exist
        if "exclude_paths" not in cfg:
            cfg["exclude_paths"] = []
        if "excluded_folders" not in cfg:
            cfg["excluded_folders"] = []
        if "excluded_file_types" not in cfg:
            cfg["excluded_file_types"] = []
        return cfg
    
    def _create_layout(self) -> List[List[sg.Element]]:
        """Create the main window layout."""
        # File Selection Section
        file_section = [
            [sg.Text("Directories to Scan:")],
            [
                sg.Listbox(
                    values=self.config["directories_to_scan"],
                    size=(50, 4),
                    key="-DIRS-",
                    enable_events=True
                ),
                sg.Column([
                    [sg.Button("Add", key="-ADD-")],
                    [sg.Button("Remove", key="-REMOVE-")]
                ])
            ],
            [sg.Checkbox("Test mode (use demo_data)", key="-TESTMODE-", default=False)]
        ]
        
        # Settings Section
        settings_section = [
            [sg.Text("Settings:")],
            [
                sg.Text("Large File Threshold (MB):"),
                sg.Input(
                    default_text=str(self.config["large_file_threshold_mb"]),
                    size=(10, 1),
                    key="-SIZE-"
                )
            ],
            [
                sg.Text("Old File Threshold (days):"),
                sg.Input(
                    default_text=str(self.config["old_file_threshold_days"]),
                    size=(10, 1),
                    key="-DAYS-"
                )
            ],
            [sg.Text("Excluded Folders:")],
            [
                sg.Listbox(
                    values=self.config["excluded_folders"],
                    size=(30, 3),
                    key="-EXCLUDE-FOLDERS-"
                ),
                sg.Column([
                    [sg.Button("Add", key="-ADD-FOLDER-")],
                    [sg.Button("Remove", key="-REMOVE-FOLDER-")]
                ])
            ],
            [sg.Text("Excluded File Types:")],
            [
                sg.Listbox(
                    values=self.config["excluded_file_types"],
                    size=(30, 3),
                    key="-EXCLUDE-TYPES-"
                ),
                sg.Column([
                    [sg.Button("Add", key="-ADD-TYPE-")],
                    [sg.Button("Remove", key="-REMOVE-TYPE-")]
                ])
            ],
            [sg.Text("Exclude Paths (one per line):")],
            [
                sg.Multiline(
                    default_text="\n".join(self.config.get("exclude_paths", [])),
                    size=(50, 4),
                    key="-EXCLUDE-PATHS-"
                )
            ]
        ]
        
        # Results Table
        results_section = [
            [sg.Text("Scan Results:")],
            [
                sg.Table(
                    values=[],
                    headings=["File Path", "Size (MB)", "Last Modified", "Type"],
                    auto_size_columns=True,
                    justification='left',
                    num_rows=18,
                    key="-RESULTS-",
                    enable_events=True,
                    expand_x=True,
                    expand_y=True
                )
            ]
        ]
        
        # Action Buttons
        button_section = [
            [
                sg.Button("Run Scan", key="-SCAN-", bind_return_key=True),
                sg.Button("Generate Report", key="-REPORT-", disabled=True),
                sg.Button("Save Settings", key="-SAVE-"),
                sg.Button("Exit")
            ]
        ]
        
        # Progress Bar
        progress_section = [
            [sg.Text("Ready", key="-STATUS-")],
            [sg.ProgressBar(100, orientation='h', size=(50, 20), key='-PROGRESS-')]
        ]
        
        # Combine all sections
        layout = [
            [sg.Text("CleanSlate – Privacy-First File Scanner", font=("Helvetica", 16))],
            [sg.HSeparator()],
            [
                sg.Column(file_section + settings_section, expand_y=True),
                sg.VSeparator(),
                sg.Column(results_section, expand_x=True, expand_y=True)
            ],
            [sg.HSeparator()],
            progress_section,
            button_section
        ]
        
        return layout
    
    def _format_results_for_table(self, results: Dict) -> List[List[str]]:
        """Format scan results for the table display."""
        table_data = []
        
        # Add duplicates
        for group_name, files in results.get('duplicates', {}).items():
            for file_path in files:
                table_data.append([file_path, "-", "-", "Duplicate"])
        
        # Add large files
        for file_path, size in results.get('large_files', []):
            table_data.append([file_path, f"{size:.2f}", "-", "Large"])
        
        # Add old files
        for file_path, date in results.get('old_files', []):
            table_data.append([file_path, "-", date, "Old"])
        
        # Add empty files
        for file_path in results.get('empty_files', []):
            table_data.append([file_path, "0", "-", "Empty"])
        
        # Near-duplicates
        for group, files in results.get('near_duplicates', {}).items():
            for file_path in files:
                table_data.append([file_path, "-", "-", "Near-duplicate image"])
        
        # Blurry images
        for file_path, score in results.get('blurry_files', []):
            table_data.append([file_path, "-", f"Blur {score:.2f}", "Blurry image"])
        
        return table_data
    
    def _update_config_from_values(self, values: Dict) -> None:
        """Update config dictionary from GUI values."""
        try:
            self.config["large_file_threshold_mb"] = float(values["-SIZE-"])
            self.config["old_file_threshold_days"] = int(values["-DAYS-"])
            self.config["directories_to_scan"] = list(values["-DIRS-"])
            self.config["excluded_folders"] = list(values["-EXCLUDE-FOLDERS-"])
            self.config["excluded_file_types"] = list(values["-EXCLUDE-TYPES-"])
            exclude_paths_text = values.get("-EXCLUDE-PATHS-", "") or ""
            exclude_paths = [line.strip() for line in exclude_paths_text.splitlines() if line.strip()]
            self.config["exclude_paths"] = exclude_paths
        except (ValueError, TypeError) as e:
            sg.popup_error(f"Invalid setting value: {str(e)}")
    
    def _generate_html_report(self, results: Dict) -> None:
        """Generate a simple HTML report from results."""
        def html_escape(s: str) -> str:
            return (s.replace("&", "&amp;")
                     .replace("<", "&lt;")
                     .replace(">", "&gt;")
                     .replace('"', "&quot;")
                     .replace("'", "&#39;"))
        
        sections = []
        sections.append("<h1>CleanSlate Report</h1>")
        sections.append("<h2>Summary</h2>")
        sections.append(f"<p>Total files scanned: {results.get('total_files', 0)}</p>")
        sections.append(f"<p>Duplicate groups: {len(results.get('duplicates', {}))}</p>")
        sections.append(f"<p>Large files: {len(results.get('large_files', []))}</p>")
        sections.append(f"<p>Old files: {len(results.get('old_files', []))}</p>")
        sections.append(f"<p>Empty files: {len(results.get('empty_files', []))}</p>")
        sections.append(f"<p>Near-duplicate image groups: {len(results.get('near_duplicates', {}))}</p>")
        sections.append(f"<p>Blurry images: {len(results.get('blurry_files', []))}</p>")
        
        def list_section(title: str, rows: List[List[str]]):
            html = [f"<h2>{html_escape(title)}</h2>"]
            if not rows:
                html.append("<p>None</p>")
            else:
                html.append("<ul>")
                for r in rows:
                    html.append(f"<li>{html_escape(' | '.join(r))}</li>")
                html.append("</ul>")
            return "\n".join(html)
        
        # Build sections
        dup_rows = []
        for group_name, files in results.get('duplicates', {}).items():
            for file_path in files:
                dup_rows.append([file_path])
        sections.append(list_section("Duplicate Files", dup_rows))
        
        large_rows = [[fp, f"{size:.2f} MB"] for fp, size in results.get('large_files', [])]
        sections.append(list_section("Large Files", large_rows))
        
        old_rows = [[fp, date] for fp, date in results.get('old_files', [])]
        sections.append(list_section("Old Files", old_rows))
        
        empty_rows = [[fp] for fp in results.get('empty_files', [])]
        sections.append(list_section("Empty Files", empty_rows))
        
        nd_rows = []
        for group, files in results.get('near_duplicates', {}).items():
            for fp in files:
                nd_rows.append([fp])
        sections.append(list_section("Near-duplicate Images", nd_rows))
        
        blurry_rows = [[fp, f"Blur {score:.2f}"] for fp, score in results.get('blurry_files', [])]
        sections.append(list_section("Blurry Images", blurry_rows))
        
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>CleanSlate Report</title>
<style>
 body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 24px; }
 h1 { margin-top: 0; }
 h2 { margin-top: 24px; }
 ul { padding-left: 20px; }
 li { margin: 4px 0; }
 .muted { color: #666; }
</style>
</head>
<body>
%s
</body>
</html>
""" % ("\n".join(sections))
        
        with open(REPORT_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
    
    def run(self):
        """Run the main GUI event loop."""
        self.window = sg.Window(
            "CleanSlate",
            self._create_layout(),
            resizable=True,
            finalize=True
        )
        
        while True:
            event, values = self.window.read()
            
            if event in (sg.WIN_CLOSED, "Exit"):
                break
                
            elif event == "-ADD-":
                folder = sg.popup_get_folder("Select Directory to Scan")
                if folder:
                    current = list(values["-DIRS-"])
                    if folder not in current:
                        current.append(folder)
                        self.window["-DIRS-"].update(current)
            
            elif event == "-REMOVE-":
                selected = values["-DIRS-"]
                if selected:
                    current = list(values["-DIRS-"])
                    for item in selected:
                        current.remove(item)
                    self.window["-DIRS-"].update(current)
            
            elif event == "-ADD-FOLDER-":
                folder = sg.popup_get_text("Enter folder name to exclude:")
                if folder:
                    current = list(values["-EXCLUDE-FOLDERS-"])
                    if folder not in current:
                        current.append(folder)
                        self.window["-EXCLUDE-FOLDERS-"].update(current)
            
            elif event == "-REMOVE-FOLDER-":
                selected = values["-EXCLUDE-FOLDERS-"]
                if selected:
                    current = list(values["-EXCLUDE-FOLDERS-"])
                    for item in selected:
                        current.remove(item)
                    self.window["-EXCLUDE-FOLDERS-"].update(current)
            
            elif event == "-ADD-TYPE-":
                file_type = sg.popup_get_text("Enter file extension to exclude (e.g. .tmp):")
                if file_type:
                    if not file_type.startswith("."):
                        file_type = "." + file_type
                    current = list(values["-EXCLUDE-TYPES-"])
                    if file_type not in current:
                        current.append(file_type)
                        self.window["-EXCLUDE-TYPES-"].update(current)
            
            elif event == "-REMOVE-TYPE-":
                selected = values["-EXCLUDE-TYPES-"]
                if selected:
                    current = list(values["-EXCLUDE-TYPES-"])
                    for item in selected:
                        current.remove(item)
                    self.window["-EXCLUDE-TYPES-"].update(current)
            
            elif event == "-SAVE-":
                self._update_config_from_values(values)
                save_config(self.config)
                sg.popup("Settings saved successfully!")
            
            elif event == "-SCAN-":
                self._update_config_from_values(values)
                
                # Handle test mode
                if values.get("-TESTMODE-", False):
                    scan_dirs_backup = self.config.get("directories_to_scan", [])
                    self.config["directories_to_scan"] = ["demo_data"]
                else:
                    scan_dirs_backup = None
                
                if not self.config["directories_to_scan"]:
                    sg.popup_error("Please select at least one directory to scan!")
                    # restore
                    if scan_dirs_backup is not None:
                        self.config["directories_to_scan"] = scan_dirs_backup
                    continue
                
                self.window["-STATUS-"].update("Scanning... Please wait")
                self.window["-PROGRESS-"].update(0)
                self.window.refresh()
                
                try:
                    # Run the scan
                    self.current_results = run_scan(self.config)
                    
                    # Update results table
                    table_data = self._format_results_for_table(self.current_results)
                    self.window["-RESULTS-"].update(table_data)
                    
                    # Enable report generation
                    self.window["-REPORT-"].update(disabled=False)
                    
                    self.window["-STATUS-"].update("Scan complete!")
                    self.window["-PROGRESS-"].update(100)
                    
                except Exception as e:
                    sg.popup_error(f"Error during scan: {str(e)}")
                    self.window["-STATUS-"].update("Scan failed!")
                finally:
                    # restore
                    if scan_dirs_backup is not None:
                        self.config["directories_to_scan"] = scan_dirs_backup
            
            elif event == "-REPORT-":
                if self.current_results:
                    try:
                        # Save HTML report using current results
                        self._generate_html_report(self.current_results)
                        sg.popup(f"Reports saved:\n{REPORT_FILE}\n{REPORT_HTML_FILE}")
                    except Exception as e:
                        sg.popup_error(f"Error generating reports: {str(e)}")
                else:
                    sg.popup_error("No scan results available. Please run a scan first.")
        
        self.window.close()


def main():
    """Main entry point for the GUI application."""
    gui = CleanSlateGUI()
    gui.run()


if __name__ == "__main__":
    main() 