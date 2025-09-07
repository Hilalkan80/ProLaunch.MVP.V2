#!/usr/bin/env python3
"""
Validation script for Authentication Service

This script validates that the authentication service is properly configured
and can perform basic operations.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from colorama import init, Fore, Style
init(autoreset=True)


async def validate_imports():
    """Validate that all required modules can be imported"""
    print(f"{Fore.CYAN}Validating module imports...{Style.RESET_ALL}")
    
    try:
        # Core imports
        from models.base import Base, get_db_context
        from models.user import User, SubscriptionTier, ExperienceLevel
        from models.token import RefreshToken, TokenBlacklist
        print(f"{Fore.GREEN}[OK] Database models imported successfully{Style.RESET_ALL}")
        
        # Service imports
        from services.auth_service import auth_service
        print(f"{Fore.GREEN}[OK] Auth service imported successfully{Style.RESET_ALL}")
        
        # Security imports
        from core.security import password_manager, jwt_manager, security_utils
        print(f"{Fore.GREEN}[OK] Security modules imported successfully{Style.RESET_ALL}")
        
        # Infrastructure imports
        from infrastructure.redis.redis_mcp import redis_mcp_client
        print(f"{Fore.GREEN}[OK] Redis client imported successfully{Style.RESET_ALL}")
        
        return True
    except ImportError as e:
        print(f"{Fore.RED}[FAIL] Import error: {e}{Style.RESET_ALL}")
        return False


async def validate_security_functions():
    """Validate core security functions"""
    print(f"\n{Fore.CYAN}Validating security functions...{Style.RESET_ALL}")
    
    try:
        from core.security import password_manager, jwt_manager, security_utils
        
        # Test password hashing
        test_password = "TestPassword123!"
        hashed = password_manager.hash_password(test_password)
        verified = password_manager.verify_password(test_password, hashed)
        
        if verified:
            print(f"{Fore.GREEN}[OK] Password hashing and verification working{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAIL] Password verification failed{Style.RESET_ALL}")
            return False
        
        # Test password validation
        is_valid, error = password_manager.validate_password_strength(test_password)
        if is_valid:
            print(f"{Fore.GREEN}[OK] Password strength validation working{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAIL] Password validation failed: {error}{Style.RESET_ALL}")
            return False
        
        # Test JWT token creation
        from uuid import uuid4
        test_user_id = str(uuid4())
        access_token, expires_at = jwt_manager.create_access_token(
            test_user_id,
            "test@example.com",
            "free"
        )
        
        if access_token:
            print(f"{Fore.GREEN}[OK] JWT access token creation working{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAIL] Failed to create access token{Style.RESET_ALL}")
            return False
        
        # Test JWT token decoding
        payload = jwt_manager.decode_token(access_token)
        if payload["sub"] == test_user_id:
            print(f"{Fore.GREEN}[OK] JWT token decoding working{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAIL] JWT token decoding failed{Style.RESET_ALL}")
            return False
        
        # Test security utilities
        secure_token = security_utils.generate_secure_token()
        verification_code = security_utils.generate_verification_code()
        
        if secure_token and verification_code:
            print(f"{Fore.GREEN}[OK] Security utilities working{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAIL] Security utilities failed{Style.RESET_ALL}")
            return False
        
        return True
    except Exception as e:
        print(f"{Fore.RED}[FAIL] Security validation error: {e}{Style.RESET_ALL}")
        return False


async def validate_database_models():
    """Validate database model structure"""
    print(f"\n{Fore.CYAN}Validating database models...{Style.RESET_ALL}")
    
    try:
        from models.user import User, SubscriptionTier, ExperienceLevel
        from models.token import RefreshToken, TokenBlacklist
        from uuid import uuid4
        from datetime import datetime
        
        # Test User model
        test_user = User(
            id=uuid4(),
            email="test@example.com",
            password_hash="hashed_password",
            business_idea="Test business idea",
            subscription_tier=SubscriptionTier.FREE,
            experience_level=ExperienceLevel.FIRST_TIME,
            is_active=True,
            is_verified=False
        )
        
        if test_user.to_dict() and test_user.to_profile():
            print(f"{Fore.GREEN}[OK] User model structure valid{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAIL] User model methods failed{Style.RESET_ALL}")
            return False
        
        # Test RefreshToken model
        test_token = RefreshToken(
            id=uuid4(),
            token="test_token",
            user_id=uuid4(),
            expires_at=datetime.utcnow()
        )
        
        if hasattr(test_token, 'is_valid'):
            print(f"{Fore.GREEN}[OK] RefreshToken model structure valid{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAIL] RefreshToken model missing methods{Style.RESET_ALL}")
            return False
        
        # Test TokenBlacklist model
        test_blacklist = TokenBlacklist(
            id=uuid4(),
            jti="test_jti",
            token_type="access",
            user_id=uuid4(),
            expires_at=datetime.utcnow(),
            reason="Test reason"
        )
        
        if hasattr(test_blacklist, 'can_be_cleaned'):
            print(f"{Fore.GREEN}[OK] TokenBlacklist model structure valid{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[FAIL] TokenBlacklist model missing methods{Style.RESET_ALL}")
            return False
        
        return True
    except Exception as e:
        print(f"{Fore.RED}[FAIL] Model validation error: {e}{Style.RESET_ALL}")
        return False


async def validate_auth_service_structure():
    """Validate auth service has all required methods"""
    print(f"\n{Fore.CYAN}Validating auth service structure...{Style.RESET_ALL}")
    
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
                print(f"{Fore.GREEN}[OK] Method '{method}' found{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[FAIL] Method '{method}' missing{Style.RESET_ALL}")
                return False
        
        return True
    except Exception as e:
        print(f"{Fore.RED}[FAIL] Auth service validation error: {e}{Style.RESET_ALL}")
        return False


async def main():
    """Main validation function"""
    print(f"{Fore.YELLOW}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Authentication Service Validation{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'='*60}{Style.RESET_ALL}")
    
    all_valid = True
    
    # Run validations
    if not await validate_imports():
        all_valid = False
    
    if not await validate_security_functions():
        all_valid = False
    
    if not await validate_database_models():
        all_valid = False
    
    if not await validate_auth_service_structure():
        all_valid = False
    
    # Summary
    print(f"\n{Fore.YELLOW}{'='*60}{Style.RESET_ALL}")
    if all_valid:
        print(f"{Fore.GREEN}[SUCCESS] All validations passed successfully!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}The authentication service is properly configured.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}[ERROR] Some validations failed.{Style.RESET_ALL}")
        print(f"{Fore.RED}Please review the errors above and fix the issues.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'='*60}{Style.RESET_ALL}")
    
    return 0 if all_valid else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)