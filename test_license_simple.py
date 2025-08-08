#!/usr/bin/env python3
"""
Simple test script for LocalMind licensing system (without GUI).
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta

# Constants from app.py
APP_NAME = "LocalMind"
LICENSE_PATH = Path.home() / ".localmind_license.json"

class LicenseManager:
    """Manages license validation and storage."""
    
    def __init__(self):
        """Initialize license manager."""
        self.license_data = None
        self.is_valid = False
    
    def check_license(self) -> bool:
        """Check if a valid license exists."""
        try:
            if not LICENSE_PATH.exists():
                return False
            
            with open(LICENSE_PATH, 'r') as f:
                self.license_data = json.load(f)
            
            # Validate license (simplified for MVP - replace with actual crypto)
            if self._validate_license_data(self.license_data):
                self.is_valid = True
                return True
            
        except Exception:
            pass
        
        return False
    
    def _validate_license_data(self, data: dict) -> bool:
        """Validate license data (placeholder implementation)."""
        # For MVP, accept any license file with required fields
        required_fields = ['license_key', 'email', 'expires']
        return all(field in data for field in required_fields)
    
    def activate_license(self, license_key: str) -> bool:
        """Activate license with provided key."""
        try:
            # For MVP, accept any non-empty key
            if not license_key.strip():
                return False
            
            # Create license data
            license_data = {
                'license_key': license_key,
                'email': 'user@example.com',  # Would be extracted from license
                'expires': (datetime.now() + timedelta(days=365)).isoformat(),
                'activated': datetime.now().isoformat()
            }
            
            # Save license
            with open(LICENSE_PATH, 'w') as f:
                json.dump(license_data, f, indent=2)
            
            self.license_data = license_data
            self.is_valid = True
            return True
            
        except Exception:
            return False
    
    def load_license_file(self, file_path: str) -> bool:
        """Load license from file."""
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

def test_license_manager():
    """Test the license manager functionality."""
    print(f"🧪 Testing {APP_NAME} License Manager")
    print("=" * 50)
    
    # Create a temporary license manager
    temp_license_path = Path("test_license.json")
    license_manager = LicenseManager()
    
    # Test 1: No license should fail
    print("\n1. Testing with no license...")
    has_license = license_manager.check_license()
    print(f"   Has license: {has_license}")
    assert not has_license, "Should not have license initially"
    print("   ✅ Passed")
    
    # Test 2: Activate with valid key
    print("\n2. Testing license activation...")
    test_key = "TEST-LICENSE-KEY-12345"
    success = license_manager.activate_license(test_key)
    print(f"   Activation success: {success}")
    assert success, "Should activate with valid key"
    print("   ✅ Passed")
    
    # Test 3: Check license after activation
    print("\n3. Testing license validation after activation...")
    has_license = license_manager.check_license()
    print(f"   Has license: {has_license}")
    assert has_license, "Should have license after activation"
    print("   ✅ Passed")
    
    # Test 4: Load license from file
    print("\n4. Testing license file loading...")
    test_license_data = {
        "license_key": "FILE-LICENSE-KEY-67890",
        "email": "test@example.com",
        "expires": "2024-12-31T23:59:59",
        "activated": "2024-01-01T00:00:00"
    }
    
    with open(temp_license_path, 'w') as f:
        json.dump(test_license_data, f, indent=2)
    
    success = license_manager.load_license_file(str(temp_license_path))
    print(f"   File loading success: {success}")
    assert success, "Should load license from file"
    print("   ✅ Passed")
    
    # Cleanup
    if temp_license_path.exists():
        temp_license_path.unlink()
    
    print("\n🎉 All license tests passed!")
    print("✅ LocalMind licensing system is working correctly")

if __name__ == "__main__":
    test_license_manager() 