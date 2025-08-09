#!/usr/bin/env python3
"""
LocalMind Build Script
Builds LocalMind for macOS and Windows using PyInstaller.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Build configuration
APP_NAME = "LocalMind"
APP_VERSION = "1.0.0"
MAIN_SCRIPT = "app.py"

# PyInstaller options
PYINSTALLER_OPTS = [
    "--onefile",
    "--windowed",  # No console window
    "--name", APP_NAME,
    "--distpath", "dist",
    "--workpath", "build",
    "--specpath", "build",
    "--clean",
    "--noconfirm"
]

# macOS specific options
MACOS_OPTS = [
    "--target-architecture", "universal2",  # Support both Intel and Apple Silicon
    "--codesign-identity", "-",  # Ad-hoc signing
]

# Windows specific options
WINDOWS_OPTS = [
    "--icon", "assets/icon.ico",  # If you have an icon
]

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def install_dependencies():
    """Install build dependencies."""
    print("📦 Installing build dependencies...")
    
    # Install PyInstaller
    if not run_command([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                      "Installing PyInstaller"):
        return False
    
    # Install application dependencies
    if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      "Installing application dependencies"):
        return False
    
    return True

def create_assets():
    """Create assets directory and placeholder icon."""
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    # Create a simple placeholder icon (you can replace this with your actual icon)
    icon_content = """
# This is a placeholder for the LocalMind icon
# Replace this with your actual icon file
# For macOS: .icns file
# For Windows: .ico file
"""
    
    with open(assets_dir / "icon.txt", "w") as f:
        f.write(icon_content)
    
    print("📁 Created assets directory")

def build_macos():
    """Build macOS application."""
    print("🍎 Building macOS application...")
    
    # macOS specific build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        *PYINSTALLER_OPTS,
        *MACOS_OPTS,
        MAIN_SCRIPT
    ]
    
    if run_command(cmd, "Building macOS app"):
        # Create macOS app bundle
        app_path = Path("dist") / f"{APP_NAME}.app"
        if app_path.exists():
            print(f"✅ macOS app created: {app_path}")
            return True
    
    return False

def build_windows():
    """Build Windows application."""
    print("🪟 Building Windows application...")
    
    # Windows specific build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        *PYINSTALLER_OPTS,
        *WINDOWS_OPTS,
        MAIN_SCRIPT
    ]
    
    if run_command(cmd, "Building Windows app"):
        # Create Windows executable
        exe_path = Path("dist") / f"{APP_NAME}.exe"
        if exe_path.exists():
            print(f"✅ Windows app created: {exe_path}")
            return True
    
    return False

def create_release_package():
    """Create release package with documentation."""
    print("📦 Creating release package...")
    
    release_dir = Path("releases")
    release_dir.mkdir(exist_ok=True)
    
    # Copy built applications
    dist_dir = Path("dist")
    if dist_dir.exists():
        for item in dist_dir.iterdir():
            target = release_dir / item.name
            if item.is_dir():
                # Copy app bundles or folders recursively
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
            elif item.is_file():
                shutil.copy2(item, target)
    
    # Copy documentation
    docs = ["README.md", "requirements.txt", "LICENSE"]
    for doc in docs:
        if Path(doc).exists():
            shutil.copy2(doc, release_dir)
    
    # Create install instructions
    install_instructions = f"""
# LocalMind {APP_VERSION} Installation Instructions

## macOS
1. Download the LocalMind.app file
2. Drag LocalMind.app to your Applications folder
3. Right-click and select "Open" the first time (to bypass Gatekeeper)
4. Launch LocalMind from Applications

## Windows
1. Download the LocalMind.exe file
2. Run LocalMind.exe
3. Windows may show a security warning - click "More info" then "Run anyway"

## License Activation
1. Launch LocalMind
2. Enter your license key when prompted
3. You can purchase LocalMind at localmindit.com

## Support
- Website: localmindit.com
- Privacy Policy: localmindit.com/privacy
- 30-day money-back guarantee

LocalMind - Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.
"""
    
    with open(release_dir / "INSTALL.txt", "w") as f:
        f.write(install_instructions)
    
    print(f"✅ Release package created in {release_dir}")

def clean_build():
    """Clean build artifacts."""
    print("🧹 Cleaning build artifacts...")
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Cleaned {dir_name}")

def main():
    """Main build function."""
    print(f"🚀 Building {APP_NAME} {APP_VERSION}")
    print("=" * 50)
    
    # Check if we're on the right platform
    platform = sys.platform
    print(f"Platform: {platform}")
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Create assets
    create_assets()
    
    # Clean previous builds
    clean_build()
    
    # Build for current platform
    success = False
    if platform == "darwin":  # macOS
        success = build_macos()
    elif platform.startswith("win"):  # Windows
        success = build_windows()
    else:
        print(f"⚠️  Unsupported platform: {platform}")
        print("Building generic executable...")
        success = run_command([
            sys.executable, "-m", "PyInstaller",
            *PYINSTALLER_OPTS,
            MAIN_SCRIPT
        ], "Building generic executable")
    
    if success:
        # Create release package
        create_release_package()
        print("\n🎉 Build completed successfully!")
        print("📁 Check the 'releases' directory for the built application")
        return True
    else:
        print("\n❌ Build failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 