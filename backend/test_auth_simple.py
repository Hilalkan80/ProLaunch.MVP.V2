#!/usr/bin/env python3
"""
Simple test script for Authentication Service

This script tests the core auth service functionality without complex dependencies.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set minimal environment variables
os.environ["JWT_SECRET"] = "test_secret_key_for_testing"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://prolaunch:prolaunch123@localhost:5432/prolaunch_test"


async def test_imports():
    """Test that core imports work"""
    print("Testing imports...")
    try:
        # Test core security imports
        from core.security import password_manager, jwt_manager, security_utils
        print("[OK] Core security modules imported")
        
        # Test model imports
        from models.user import User, SubscriptionTier, ExperienceLevel
        from models.token import RefreshToken, TokenBlacklist
        print("[OK] Database models imported")
        
        # Test auth service import
        from services.auth_service import auth_service
        print("[OK] Auth service imported")
        
        return True
    except Exception as e:
        print(f"[FAIL] Import error: {e}")
        return False


async def test_password_functions():
    """Test password hashing and validation"""
    print("\nTesting password functions...")
    try:
        from core.security import password_manager
        
        # Test password hashing
        test_password = "TestPassword123!"
        hashed = password_manager.hash_password(test_password)
        
        # Test password verification
        if password_manager.verify_password(test_password, hashed):
            print("[OK] Password hashing and verification working")
        else:
            print("[FAIL] Password verification failed")
            return False
        
        # Test password strength validation
        is_valid, error = password_manager.validate_password_strength(test_password)
        if is_valid:
            print("[OK] Password strength validation working")
        else:
            print(f"[FAIL] Password validation failed: {error}")
            return False
        
        # Test weak password rejection
        weak_password = "weak"
        is_valid, error = password_manager.validate_password_strength(weak_password)
        if not is_valid:
            print("[OK] Weak password correctly rejected")
        else:
            print("[FAIL] Weak password should have been rejected")
            return False
        
        return True
    except Exception as e:
        print(f"[FAIL] Password function error: {e}")
        return False


async def test_jwt_functions():
    """Test JWT token creation and validation"""
    print("\nTesting JWT functions...")
    try:
        from core.security import jwt_manager
        from uuid import uuid4
        
        # Test access token creation
        test_user_id = str(uuid4())
        test_email = "test@example.com"
        
        access_token, expires_at = jwt_manager.create_access_token(
            test_user_id,
            test_email,
            "free",
            additional_claims={"is_verified": True}
        )
        
        if access_token:
            print("[OK] Access token created successfully")
        else:
            print("[FAIL] Failed to create access token")
            return False
        
        # Test token decoding
        payload = jwt_manager.decode_token(access_token)
        if payload["sub"] == test_user_id and payload["email"] == test_email:
            print("[OK] Token decoded successfully")
        else:
            print("[FAIL] Token decoding failed")
            return False
        
        # Test refresh token creation
        refresh_token, refresh_expires, family_id = jwt_manager.create_refresh_token(
            test_user_id,
            device_id="test-device"
        )
        
        if refresh_token and family_id:
            print("[OK] Refresh token created successfully")
        else:
            print("[FAIL] Failed to create refresh token")
            return False
        
        return True
    except Exception as e:
        print(f"[FAIL] JWT function error: {e}")
        return False


async def test_auth_service_methods():
    """Test that auth service has required methods"""
    print("\nTesting auth service structure...")
    try:
        from services.auth_service import auth_service
        
        required_methods = [
            'register_user',
            'login',
            'refresh_tokens',
            'logout',
            'logout_all_devices',
            'verify_access_token'
        ]
        
        for method in required_methods:
            if hasattr(auth_service, method):
                print(f"[OK] Method '{method}' found")
            else:
                print(f"[FAIL] Method '{method}' missing")
                return False
        
        return True
    except Exception as e:
        print(f"[FAIL] Auth service error: {e}")
        return False


async def main():
    """Main test function"""
    print("=" * 50)
    print("Authentication Service Basic Test")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Run tests
    if not await test_imports():
        all_tests_passed = False
    
    if not await test_password_functions():
        all_tests_passed = False
    
    if not await test_jwt_functions():
        all_tests_passed = False
    
    if not await test_auth_service_methods():
        all_tests_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("[SUCCESS] All basic tests passed!")
        print("The authentication service core functionality is working.")
    else:
        print("[ERROR] Some tests failed.")
        print("Please review the errors above.")
    print("=" * 50)
    
    return 0 if all_tests_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)