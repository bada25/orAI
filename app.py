#!/usr/bin/env python3
"""
LocalMind - Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.
A privacy-first, local desktop application that helps you find and delete unneeded files.
"""

import os
import sys
import sqlite3
import hashlib
import csv
import threading
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from send2trash import send2trash

# Prevent Tkinter deprecation warnings
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# Constants
APP_NAME = "LocalMind"
DB_PATH = Path.home() / ".localmind_mvp.sqlite3"
LICENSE_PATH = Path.home() / ".localmind_license.json"
SCAN_CHUNK_SIZE = 4 * 1024 * 1024  # 4 MB for partial hash
LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50 MB
OLD_FILE_THRESHOLD = 180  # days
MAX_SIZE_SCORE = 10
MAX_AGE_SCORE = 10
MAX_EXTENSION_BIAS = 10

# Public key for license verification (placeholder - replace with actual key)
LICENSE_PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----
"""

class LicenseManager:
    """Manages license validation and storage."""
    
    def __init__(self):
        self.license_data = None
        self.is_valid = False
    
    def check_license(self) -> bool:
        """Check if a valid license exists."""
        try:
            if not LICENSE_PATH.exists():
                return False
            
            with open(LICENSE_PATH, 'r') as f:
                self.license_data = json.load(f)
            
            if self._validate_license_data(self.license_data):
                self.is_valid = True
                return True
        except Exception:
            pass
        return False
    
    def _validate_license_data(self, data: dict) -> bool:
        """Validate license data structure."""
        required_fields = ['license_key', 'email', 'expires']
        return all(field in data for field in required_fields)
    
    def activate_license(self, license_key: str) -> bool:
        """Activate a license with the given key."""
        try:
            if not license_key.strip():
                return False
            
            license_data = {
                'license_key': license_key,
                'email': 'user@example.com',
                'expires': (datetime.now() + timedelta(days=365)).isoformat(),
                'activated': datetime.now().isoformat()
            }
            
            with open(LICENSE_PATH, 'w') as f:
                json.dump(license_data, f, indent=2)
            
            self.license_data = license_data
            self.is_valid = True
            return True
        except Exception:
            return False
    
    def load_license_file(self, file_path: str) -> bool:
        """Load license from a file."""
        try:
            with open(file_path, 'r') as f:
                license_data = json.load(f)
            
            if self._validate_license_data(license_data):
                with open(LICENSE_PATH, 'w') as f:
                    json.dump(license_data, f, indent=2)
                
                self.license_data = license_data
                self.is_valid = True
                return True
        except Exception:
            pass
        return False

class LicenseActivationWindow:
    """License activation window."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} - License Activation")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        self.result = False
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the license activation widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text=APP_NAME, font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 5))
        
        # Tagline
        tagline_label = ttk.Label(main_frame, 
                                text="Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.",
                                font=("Helvetica", 10), foreground="gray")
        tagline_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # License key label
        key_label = ttk.Label(main_frame, text="License Key:")
        key_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        # License key entry
        self.key_entry = ttk.Entry(main_frame, width=50)
        self.key_entry.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Paste button
        paste_btn = ttk.Button(button_frame, text="Paste Key", command=self._paste_key)
        paste_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Load file button
        load_btn = ttk.Button(button_frame, text="Load License File", command=self._load_file)
        load_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Buttons frame 2
        button_frame2 = ttk.Frame(main_frame)
        button_frame2.grid(row=5, column=0, columnspan=2, pady=10)
        
        # Activate button
        activate_btn = ttk.Button(button_frame2, text="Activate", command=self._activate_license)
        activate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Exit button
        exit_btn = ttk.Button(button_frame2, text="Exit", command=self._exit)
        exit_btn.pack(side=tk.LEFT)
        
        # Instructions
        instructions = ttk.Label(main_frame, 
                               text="You can purchase LocalMind at localmindit.com",
                               font=("Helvetica", 9), foreground="gray")
        instructions.grid(row=6, column=0, columnspan=2, pady=(20, 0))
        
        # Focus on entry
        self.key_entry.focus()
    
    def _paste_key(self):
        """Paste license key from clipboard."""
        try:
            clipboard_text = self.root.clipboard_get()
            self.key_entry.delete(0, tk.END)
            self.key_entry.insert(0, clipboard_text)
        except tk.TclError:
            pass
    
    def _load_file(self):
        """Load license from file."""
        file_path = filedialog.askopenfilename(
            title="Select License File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            license_manager = LicenseManager()
            if license_manager.load_license_file(file_path):
                messagebox.showinfo("Success", "License loaded successfully!")
                self.result = True
                self.root.destroy()
            else:
                messagebox.showerror("Error", "Failed to load license file.")
    
    def _activate_license(self):
        """Activate the license."""
        license_key = self.key_entry.get().strip()
        if not license_key:
            messagebox.showerror("Error", "Please enter a license key.")
            return
        
        license_manager = LicenseManager()
        if license_manager.activate_license(license_key):
            messagebox.showinfo("Success", "License activated successfully!")
            self.result = True
            self.root.destroy()
        else:
            messagebox.showerror("Error", "Failed to activate license. Please check your key.")
    
    def _exit(self):
        """Exit the application."""
        self.result = False
        self.root.destroy()
    
    def show(self) -> bool:
        """Show the license activation window."""
        self.root.mainloop()
        return self.result

class CleanSlateDB:
    """SQLite database for learning and persistence."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER,
                    file_extension TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ext_stats (
                    extension TEXT PRIMARY KEY,
                    total_deleted INTEGER DEFAULT 0,
                    total_kept INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def record_action(self, file_path: str, action: str, file_size: int = None, file_extension: str = None):
        """Record a user action."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO actions (file_path, action, file_size, file_extension)
                VALUES (?, ?, ?, ?)
            """, (file_path, action, file_size, file_extension))
    
    def get_extension_bias(self, extension: str) -> float:
        """Get the bias score for an extension based on past actions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT total_deleted, total_kept FROM ext_stats WHERE extension = ?
            """, (extension,))
            row = cursor.fetchone()
            
            if row and row[0] + row[1] > 0:
                deleted, kept = row
                total = deleted + kept
                return min(MAX_EXTENSION_BIAS, (deleted / total) * MAX_EXTENSION_BIAS)
        
        return 0.0

class FileScanner:
    """Scans directories and analyzes files."""
    
    def __init__(self, db: CleanSlateDB):
        self.db = db
    
    def scan_directory(self, directory: str, exclusions: List[str] = None) -> List[Dict]:
        """Scan a directory and return file information."""
        if exclusions is None:
            exclusions = []
        
        files = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            return files
        
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                # Check exclusions
                if any(exclusion in str(file_path) for exclusion in exclusions):
                    continue
                
                try:
                    stat = file_path.stat()
                    files.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'extension': file_path.suffix.lower()
                    })
                except OSError:
                    continue
        
        return files
    
    def analyze_files(self, files: List[Dict]) -> Dict:
        """Analyze files and return results."""
        results = {
            'large_files': [],
            'old_files': [],
            'empty_files': [],
            'duplicates': {},
            'total_size': 0,
            'file_count': len(files)
        }
        
        # Calculate total size
        for file_info in files:
            results['total_size'] += file_info['size']
        
        # Find large files
        for file_info in files:
            if file_info['size'] > LARGE_FILE_THRESHOLD:
                results['large_files'].append(file_info)
        
        # Find old files
        cutoff_time = datetime.now() - timedelta(days=OLD_FILE_THRESHOLD)
        for file_info in files:
            if datetime.fromtimestamp(file_info['modified']) < cutoff_time:
                results['old_files'].append(file_info)
        
        # Find empty files
        for file_info in files:
            if file_info['size'] == 0:
                results['empty_files'].append(file_info)
        
        # Find duplicates (by size first, then hash)
        size_groups = {}
        for file_info in files:
            size = file_info['size']
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(file_info)
        
        # Hash files with same size
        for size, group in size_groups.items():
            if len(group) > 1:
                hash_groups = {}
                for file_info in group:
                    file_hash = self._get_file_hash(file_info['path'])
                    if file_hash not in hash_groups:
                        hash_groups[file_hash] = []
                    hash_groups[file_hash].append(file_info)
                
                # Add groups with multiple files
                for file_hash, hash_group in hash_groups.items():
                    if len(hash_group) > 1:
                        results['duplicates'][file_hash] = hash_group
        
        return results
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(SCAN_CHUNK_SIZE), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

class LocalMindGUI:
    """Main LocalMind GUI application."""
    
    def __init__(self):
        self.license_manager = LicenseManager()
        
        # Check license first
        if not self.license_manager.check_license():
            activation_window = LicenseActivationWindow()
            if not activation_window.show():
                sys.exit(0)
        
        self.db = CleanSlateDB(DB_PATH)
        self.scanner = FileScanner(self.db)
        self.current_files = []
        self.filtered_files = []
        self.selected_folder = ""
        
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1000x700")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the main GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text=APP_NAME, font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 5))
        
        # Tagline
        tagline_label = ttk.Label(main_frame, 
                                text="Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.",
                                font=("Helvetica", 10), foreground="gray")
        tagline_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # Folder selection
        folder_label = ttk.Label(main_frame, text="Folder to scan:")
        folder_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        folder_frame.columnconfigure(0, weight=1)
        
        self.folder_var = tk.StringVar()
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, state="readonly")
        folder_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        browse_btn = ttk.Button(folder_frame, text="Browse", command=self._browse_folder)
        browse_btn.grid(row=0, column=1)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Large file threshold
        ttk.Label(settings_frame, text="Large file threshold (MB):").grid(row=0, column=0, sticky=tk.W)
        self.large_threshold_var = tk.StringVar(value="50")
        ttk.Entry(settings_frame, textvariable=self.large_threshold_var, width=10).grid(row=0, column=1, padx=(5, 0))
        
        # Old file threshold
        ttk.Label(settings_frame, text="Old file threshold (days):").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.old_threshold_var = tk.StringVar(value="180")
        ttk.Entry(settings_frame, textvariable=self.old_threshold_var, width=10).grid(row=1, column=1, padx=(5, 0), pady=(5, 0))
        
        # Exclusions
        ttk.Label(settings_frame, text="Exclusions (one per line):").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        self.exclusions_text = tk.Text(settings_frame, height=3, width=40)
        self.exclusions_text.grid(row=2, column=1, padx=(5, 0), pady=(5, 0))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        scan_btn = ttk.Button(button_frame, text="Run Scan", command=self._run_scan)
        scan_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        report_btn = ttk.Button(button_frame, text="Generate Report", command=self._generate_report)
        report_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        save_btn = ttk.Button(button_frame, text="Save Settings", command=self._save_settings)
        save_btn.pack(side=tk.LEFT)
        
        # Results area
        results_label = ttk.Label(main_frame, text="Results:")
        results_label.grid(row=6, column=0, sticky=tk.W, pady=(10, 5))
        
        # Results text area
        self.results_text = tk.Text(main_frame, height=20, width=100)
        results_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_text.grid(row=7, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_scrollbar.grid(row=7, column=1, sticky=(tk.N, tk.S))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
    
    def _browse_folder(self):
        """Browse for a folder to scan."""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            self.selected_folder = folder
    
    def _run_scan(self):
        """Run the file scan."""
        folder = self.folder_var.get()
        if not folder:
            messagebox.showerror("Error", "Please select a folder to scan.")
            return
        
        self.status_var.set("Scanning...")
        self.results_text.delete(1.0, tk.END)
        
        # Run scan in thread to avoid blocking GUI
        def scan_thread():
            try:
                # Get exclusions
                exclusions_text = self.exclusions_text.get(1.0, tk.END).strip()
                exclusions = [line.strip() for line in exclusions_text.split('\n') if line.strip()]
                
                # Scan files
                files = self.scanner.scan_directory(folder, exclusions)
                
                # Analyze files
                results = self.scanner.analyze_files(files)
                
                # Update GUI in main thread
                self.root.after(0, lambda: self._update_results(results))
                
            except Exception as e:
                self.root.after(0, lambda: self._show_error(f"Scan failed: {str(e)}"))
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def _update_results(self, results):
        """Update the results display."""
        self.results_text.delete(1.0, tk.END)
        
        # Display results
        self.results_text.insert(tk.END, f"Scan complete!\n")
        self.results_text.insert(tk.END, f"Total files: {results['file_count']}\n")
        self.results_text.insert(tk.END, f"Total size: {results['total_size'] / (1024*1024):.2f} MB\n\n")
        
        # Large files
        if results['large_files']:
            self.results_text.insert(tk.END, f"Large files ({len(results['large_files'])}):\n")
            for file_info in results['large_files'][:5]:  # Show first 5
                size_mb = file_info['size'] / (1024 * 1024)
                self.results_text.insert(tk.END, f"  - {file_info['name']} ({size_mb:.2f} MB)\n")
            if len(results['large_files']) > 5:
                self.results_text.insert(tk.END, f"  ... and {len(results['large_files']) - 5} more\n")
            self.results_text.insert(tk.END, "\n")
        
        # Old files
        if results['old_files']:
            self.results_text.insert(tk.END, f"Old files ({len(results['old_files'])}):\n")
            for file_info in results['old_files'][:5]:  # Show first 5
                modified_date = datetime.fromtimestamp(file_info['modified']).strftime('%Y-%m-%d')
                self.results_text.insert(tk.END, f"  - {file_info['name']} (modified: {modified_date})\n")
            if len(results['old_files']) > 5:
                self.results_text.insert(tk.END, f"  ... and {len(results['old_files']) - 5} more\n")
            self.results_text.insert(tk.END, "\n")
        
        # Empty files
        if results['empty_files']:
            self.results_text.insert(tk.END, f"Empty files ({len(results['empty_files'])}):\n")
            for file_info in results['empty_files'][:5]:  # Show first 5
                self.results_text.insert(tk.END, f"  - {file_info['name']}\n")
            if len(results['empty_files']) > 5:
                self.results_text.insert(tk.END, f"  ... and {len(results['empty_files']) - 5} more\n")
            self.results_text.insert(tk.END, "\n")
        
        # Duplicates
        if results['duplicates']:
            total_duplicates = sum(len(group) for group in results['duplicates'].values())
            self.results_text.insert(tk.END, f"Duplicate files ({total_duplicates} total):\n")
            for i, (file_hash, group) in enumerate(list(results['duplicates'].items())[:3]):  # Show first 3 groups
                self.results_text.insert(tk.END, f"  Group {i+1} ({len(group)} files):\n")
                for file_info in group[:3]:  # Show first 3 files in group
                    size_mb = file_info['size'] / (1024 * 1024)
                    self.results_text.insert(tk.END, f"    - {file_info['name']} ({size_mb:.2f} MB)\n")
                if len(group) > 3:
                    self.results_text.insert(tk.END, f"    ... and {len(group) - 3} more\n")
            if len(results['duplicates']) > 3:
                self.results_text.insert(tk.END, f"  ... and {len(results['duplicates']) - 3} more groups\n")
        
        self.status_var.set(f"Scan complete! Found {results['file_count']} files.")
    
    def _show_error(self, message):
        """Show an error message."""
        messagebox.showerror("Error", message)
        self.status_var.set("Scan failed!")
    
    def _generate_report(self):
        """Generate a report."""
        # This would integrate with the existing report generation
        messagebox.showinfo("Info", "Report generation would be implemented here.")
    
    def _save_settings(self):
        """Save current settings."""
        try:
            large_threshold = int(self.large_threshold_var.get())
            old_threshold = int(self.old_threshold_var.get())
            
            # Save to config file
            config = {
                "large_file_threshold_mb": large_threshold,
                "old_file_threshold_days": old_threshold,
                "exclude_paths": self.exclusions_text.get(1.0, tk.END).strip().split('\n')
            }
            
            with open("config.json", "w") as f:
                json.dump(config, f, indent=2)
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for thresholds.")
    
    def run(self):
        """Run the GUI."""
        self.root.mainloop()

def main():
    """Main entry point."""
    try:
        app = LocalMindGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Error", f"Application error: {str(e)}")

if __name__ == "__main__":
    main()



