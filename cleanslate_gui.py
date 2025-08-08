#!/usr/bin/env python3
"""
LocalMind Phase 3 - GUI Interface
Cross-platform GUI wrapper for the LocalMind file scanning engine.
"""

import os
import json
from pathlib import Path
import PySimpleGUI as sg
from typing import Dict, List, Optional, Tuple
from datetime import datetime

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
APP_NAME = "LocalMind"
DEFAULT_CONFIG = {
    "directories_to_scan": [],
    "large_file_threshold_mb": 100,
    "old_file_threshold_days": 365,
    "excluded_folders": [".git", "node_modules"],
    "excluded_file_types": [".tmp", ".log"],
    "exclude_paths": []
}


class LocalMindGUI:
    """Main GUI wrapper for LocalMind."""

    def __init__(self):
        """Initialize the GUI with default settings."""
        self.config = self._load_or_create_config()
        self.current_results = None
        self.window = None

        # Set theme
        sg.theme('LightGrey1')

    def _load_or_create_config(self) -> Dict:
        """Load existing config or create default config."""
        try:
            cfg = load_config()
            # Ensure optional keys exist
            if "exclude_paths" not in cfg:
                cfg["exclude_paths"] = []
            return cfg
        except Exception:
            # Create default config
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

    def _create_layout(self) -> List[List[sg.Element]]:
        """Create the main window layout."""
        # Header
        header = [
            [sg.Text(f"{APP_NAME}", font=("Helvetica", 16, "bold"))],
            [sg.Text("Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.", 
                    font=("Helvetica", 10), text_color='gray')],
            [sg.HSeparator()]
        ]

        # Folder selection
        folder_section = [
            [sg.Text("Select folders to scan:", font=("Helvetica", 12, "bold"))],
            [sg.Listbox(values=self.config.get("directories_to_scan", []), 
                       size=(60, 4), key="-FOLDERS-", enable_events=True)],
            [
                sg.Button("Add Folder", key="-ADD_FOLDER-"),
                sg.Button("Remove Selected", key="-REMOVE_FOLDER-")
            ]
        ]

        # Settings
        settings_section = [
            [sg.Text("Settings:", font=("Helvetica", 12, "bold"))],
            [
                sg.Text("File size threshold (MB):"),
                sg.Input(str(self.config.get("large_file_threshold_mb", 100)), 
                        key="-SIZE_THRESHOLD-", size=(10, 1))
            ],
            [
                sg.Text("File age threshold (days):"),
                sg.Input(str(self.config.get("old_file_threshold_days", 365)), 
                        key="-AGE_THRESHOLD-", size=(10, 1))
            ],
            [sg.Text("Exclude paths (one per line):")],
            [sg.Multiline(default_text="\n".join(self.config.get("exclude_paths", [])), 
                         key="-EXCLUDE_PATHS-", size=(50, 4))]
        ]

        # Buttons
        buttons = [
            [
                sg.Button("Run Scan", key="-SCAN-", size=(12, 1)),
                sg.Button("Generate Report", key="-REPORT-", size=(12, 1), disabled=True),
                sg.Button("Save Settings", key="-SAVE_SETTINGS-", size=(12, 1))
            ]
        ]

        # Results table
        results_section = [
            [sg.Text("Scan Results:", font=("Helvetica", 12, "bold"))],
            [
                sg.Table(
                    values=[],
                    headings=["File Path", "Size", "Last Accessed", "Reason Flagged"],
                    auto_size_columns=True,
                    justification='left',
                    num_rows=15,
                    key="-RESULTS_TABLE-",
                    enable_events=True
                )
            ]
        ]

        # Status
        status = [
            [sg.Text("Ready", key="-STATUS-", size=(80, 1))]
        ]

        # Combine all sections
        layout = [
            header,
            [
                sg.Column(folder_section, vertical_alignment='top'),
                sg.VSeparator(),
                sg.Column(settings_section, vertical_alignment='top')
            ],
            [sg.HSeparator()],
            buttons,
            [sg.HSeparator()],
            results_section,
            status
        ]

        return layout

    def _format_results_for_table(self, results: Dict) -> List[List[str]]:
        """Format scan results for the table display."""
        table_data = []
        
        # Add duplicate files
        for group_name, files in results.get("duplicates", {}).items():
            for file_path in files:
                try:
                    stat = os.stat(file_path)
                    size = f"{stat.st_size:,} bytes"
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    table_data.append([file_path, size, modified, f"Duplicate ({group_name})"])
                except (OSError, PermissionError):
                    continue

        # Add large files
        for file_path in results.get("large_files", []):
            try:
                stat = os.stat(file_path)
                size = f"{stat.st_size:,} bytes"
                modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                table_data.append([file_path, size, modified, "Large file"])
            except (OSError, PermissionError):
                continue

        # Add old files
        for file_path in results.get("old_files", []):
            try:
                stat = os.stat(file_path)
                size = f"{stat.st_size:,} bytes"
                modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                table_data.append([file_path, size, modified, "Old file"])
            except (OSError, PermissionError):
                continue

        # Add empty files
        for file_path in results.get("empty_files", []):
            try:
                stat = os.stat(file_path)
                size = f"{stat.st_size:,} bytes"
                modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                table_data.append([file_path, size, modified, "Empty file"])
            except (OSError, PermissionError):
                continue

        # Add near-duplicate images
        for group_name, files in results.get("near_duplicates", {}).items():
            for file_path in files:
                try:
                    stat = os.stat(file_path)
                    size = f"{stat.st_size:,} bytes"
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                    table_data.append([file_path, size, modified, f"Near-duplicate image ({group_name})"])
                except (OSError, PermissionError):
                    continue

        # Add blurry images
        for file_path in results.get("blurry_files", []):
            try:
                stat = os.stat(file_path)
                size = f"{stat.st_size:,} bytes"
                modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                table_data.append([file_path, size, modified, "Blurry image"])
            except (OSError, PermissionError):
                continue

        return table_data

    def _update_config_from_values(self, values: Dict) -> None:
        """Update internal config from GUI values."""
        try:
            self.config["large_file_threshold_mb"] = int(values.get("-SIZE_THRESHOLD-", 100))
        except ValueError:
            pass

        try:
            self.config["old_file_threshold_days"] = int(values.get("-AGE_THRESHOLD-", 365))
        except ValueError:
            pass

        # Parse exclude paths from multiline text
        exclude_text = values.get("-EXCLUDE_PATHS-", "")
        self.config["exclude_paths"] = [line.strip() for line in exclude_text.split('\n') if line.strip()]

    def _generate_html_report(self, results: Dict) -> None:
        """Generate HTML report from current results."""
        try:
            # Import the HTML generation function from core
            from cleanslate_core import generate_html_report
            
            # Extract data for HTML report
            duplicates_raw = list(results.get("duplicates", {}).values())
            large_files = results.get("large_files", [])
            old_files = results.get("old_files", [])
            empty_files = results.get("empty_files", [])
            near_duplicates = results.get("near_duplicates", {})
            blurry_files = results.get("blurry_files", [])
            
            html_content = generate_html_report(
                duplicates_raw, large_files, old_files,
                empty_files, near_duplicates, blurry_files
            )
            
            with open(REPORT_HTML_FILE, 'w') as f:
                f.write(html_content)
                
        except Exception as e:
            sg.popup_error(f"Failed to generate HTML report: {str(e)}")

    def run(self):
        """Run the main GUI event loop."""
        self.window = sg.Window(
            f"{APP_NAME}",
            self._create_layout(),
            resizable=True,
            finalize=True
        )

        while True:
            event, values = self.window.read()

            if event in (sg.WIN_CLOSED, "Exit"):
                break

            elif event == "-ADD_FOLDER-":
                folder = sg.popup_get_folder("Choose folder to scan")
                if folder:
                    current_folders = list(values.get("-FOLDERS-", []))
                    if folder not in current_folders:
                        current_folders.append(folder)
                        self.window["-FOLDERS-"].update(current_folders)
                        self.config["directories_to_scan"] = current_folders

            elif event == "-REMOVE_FOLDER-":
                selected = values.get("-FOLDERS-")
                if selected:
                    current_folders = list(values.get("-FOLDERS-", []))
                    for folder in selected:
                        if folder in current_folders:
                            current_folders.remove(folder)
                    self.window["-FOLDERS-"].update(current_folders)
                    self.config["directories_to_scan"] = current_folders

            elif event == "-SCAN-":
                if not self.config.get("directories_to_scan"):
                    sg.popup_error("Please add at least one folder to scan!")
                    continue

                # Update config from GUI values
                self._update_config_from_values(values)
                
                # Save config
                save_config(self.config)

                # Run scan
                self.window["-STATUS-"].update("Scanning... please wait")
                self.window["-SCAN-"].update(disabled=True)
                self.window.refresh()

                try:
                    self.current_results = run_scan(self.config)
                    
                    # Update results table
                    table_data = self._format_results_for_table(self.current_results)
                    self.window["-RESULTS_TABLE-"].update(table_data)
                    
                    # Enable report generation
                    self.window["-REPORT-"].update(disabled=False)
                    
                    # Update status
                    total_files = self.current_results.get("total_files", 0)
                    total_flagged = len(table_data)
                    self.window["-STATUS-"].update(
                        f"Scan complete! Found {total_files} files, {total_flagged} flagged for review."
                    )

                except Exception as e:
                    sg.popup_error(f"Scan failed: {str(e)}")
                    self.window["-STATUS-"].update("Scan failed!")

                finally:
                    self.window["-SCAN-"].update(disabled=False)

            elif event == "-REPORT-":
                if not self.current_results:
                    sg.popup_error("No scan results to report!")
                    continue

                try:
                    # Generate HTML report
                    self._generate_html_report(self.current_results)
                    
                    sg.popup(f"Reports generated successfully!\n\n"
                            f"Text report: {REPORT_FILE}\n"
                            f"HTML report: {REPORT_HTML_FILE}")

                except Exception as e:
                    sg.popup_error(f"Failed to generate reports: {str(e)}")

            elif event == "-SAVE_SETTINGS-":
                self._update_config_from_values(values)
                save_config(self.config)
                sg.popup("Settings saved successfully!")

        self.window.close()


def main():
    """Main entry point."""
    try:
        app = LocalMindGUI()
        app.run()
    except Exception as e:
        sg.popup_error(f"Application error: {str(e)}")


if __name__ == "__main__":
    main() 