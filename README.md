# CleanSlate MVP

A privacy-first, local desktop application that helps you find and delete unneeded files on your computer.

## Features

- **Privacy-First**: Runs completely offline with no network access or telemetry
- **Smart Scanning**: Identifies large files, old files, and probable duplicates
- **Learning System**: Adapts to your preferences by learning from your actions
- **Safe Deletion**: Only sends files to Trash - never permanently deletes
- **Cross-Platform**: Works on macOS, Windows, and Linux

## Quick Start

### Prerequisites

- Python 3.9 or newer

### Installation

1. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python3 app.py
   ```

3. Use the application:
   - Click "Choose Folder" to select a directory to scan
   - Click "Scan" to analyze files
   - Use filters to narrow down results
   - Select files and click "Delete Selected" to move them to Trash
   - Use "Mark Keep" to teach the app about files you want to keep

## How It Works

### File Analysis
- **Size Score**: Files over 50 MB get higher scores (0-10 points)
- **Age Score**: Files older than 180 days get higher scores (0-10 points)
- **Extension Bias**: Learned preference based on your actions (-10 to +10 points)

### Duplicate Detection
- Uses partial SHA-256 hash of first 4 MB + file size
- Groups identical files together for easy identification

### Learning System
The app learns from your actions:
- When you delete files, it increases bias against that file type
- When you mark files as "keep", it decreases bias against that file type
- This affects future suggestion scores for similar files

## Data Storage

The application stores learning data in:
```
~/.cleanslate_mvp.sqlite3
```

### Database Schema
- **actions**: Records of user actions (delete/keep) with timestamps
- **ext_stats**: Extension-based statistics for learning bias

### Reset Learning Data
To reset all learning data and start fresh:
```bash
rm ~/.cleanslate_mvp.sqlite3
```

## Safety Features

- **No Permanent Deletion**: Files are only moved to system Trash
- **Confirmation Required**: Always asks for confirmation before deleting
- **Permission Handling**: Gracefully handles files you can't access
- **Error Recovery**: Continues operation even if some files fail

## Filters

- **Only duplicates**: Show only files that have duplicates
- **Only old files**: Show files older than 180 days
- **Only large files**: Show files larger than 50 MB
- **Min score**: Show files with suggestion score above threshold

## Export

Use "Export CSV" to save current filtered results to a CSV file with all raw data for further analysis.

## Privacy

- **No Network Access**: App works completely offline
- **No Telemetry**: No data is sent anywhere
- **Local Storage**: All data stored locally in SQLite
- **User Control**: You have full control over all actions

## Troubleshooting

### macOS Icon Issues
The app is configured to avoid Tk icon crashes on macOS. If you experience issues, ensure no custom icons are being loaded.

### Permission Errors
The app will skip files it can't access and show a summary of any failures.

### Large Directories
For very large directories, scanning may take some time. The app shows progress updates during scanning.

## Development

This is an MVP (Minimum Viable Product) focused on core functionality:
- File scanning and analysis
- Duplicate detection
- Learning system
- Safe deletion
- Cross-platform compatibility

The code is designed to be easily extensible for future features while maintaining the privacy-first approach.
