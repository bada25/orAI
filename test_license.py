#!/usr/bin/env python3
"""
Test script for LocalMind licensing system.
"""

import json
from pathlib import Path
from app import LicenseManager, APP_NAME

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