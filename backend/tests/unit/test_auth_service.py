"""
Unit tests for authentication service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from src.services.auth_service import auth_service, AuthenticationService
from src.models.user import User, SubscriptionTier, ExperienceLevel
from src.models.token import RefreshToken
from src.core.security import password_manager, jwt_manager


class TestAuthenticationService:
    """Test cases for AuthenticationService."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_register_user_success(self, db_session: AsyncSession):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "business_idea": "Revolutionary AI-powered business tool",
            "target_market": "Small to medium businesses",
            "experience_level": "first-time",
            "full_name": "John Doe",
            "company_name": "Doe Enterprises"
        }
        
        user, tokens = await auth_service.register_user(db_session, **user_data)
        
        # Verify user creation
        assert user.email == user_data["email"].lower()
        assert user.business_idea == user_data["business_idea"]
        assert user.target_market == user_data["target_market"]
        assert user.experience_level == ExperienceLevel.FIRST_TIME
        assert user.full_name == user_data["full_name"]
        assert user.company_name == user_data["company_name"]
        assert user.subscription_tier == SubscriptionTier.FREE
        assert user.is_active is True
        assert user.is_verified is False
        assert user.login_count == 0
        assert user.failed_login_attempts == 0
        
        # Verify password is hashed
        assert user.password_hash != user_data["password"]
        assert password_manager.verify_password(user_data["password"], user.password_hash)
        
        # Verify tokens are generated
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert "user_profile" in tokens
        assert tokens["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_register_user_duplicate_email(self, db_session: AsyncSession, test_user: User):
        """Test registration with existing email."""
        user_data = {
            "email": test_user.email,
            "password": "StrongPassword123!",
            "business_idea": "Another business idea",
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register_user(db_session, **user_data)
        
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "Email already registered" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.parametrize("weak_password", [
        "weak123", "PASSWORD123", "password123", "Pass123", "12345678", "password"
    ])
    async def test_register_user_weak_password(self, db_session: AsyncSession, weak_password: str):
        """Test registration with weak passwords."""
        user_data = {
            "email": "weakpassword@example.com",
            "password": weak_password,
            "business_idea": "Test business idea",
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register_user(db_session, **user_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    @pytest.mark.parametrize("invalid_email", [
        "invalid-email", "@example.com", "user@", "user.example.com", "", "user@.com"
    ])
    async def test_register_user_invalid_email(self, db_session: AsyncSession, invalid_email: str):
        """Test registration with invalid email formats."""
        user_data = {
            "email": invalid_email,
            "password": "StrongPassword123!",
            "business_idea": "Test business idea",
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register_user(db_session, **user_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid email format" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_login_success(self, db_session: AsyncSession, test_user: User):
        """Test successful login."""
        device_info = {
            "device_id": "test-device-123",
            "device_name": "Test Device",
            "user_agent": "Test User Agent"
        }
        
        user, tokens = await auth_service.login(
            db_session,
            email=test_user.email,
            password="TestPassword123!",
            device_info=device_info,
            ip_address="127.0.0.1"
        )
        
        # Verify returned user
        assert user.id == test_user.id
        assert user.email == test_user.email
        
        # Verify login tracking updates
        await db_session.refresh(user)
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert user.last_login_at is not None
        assert user.last_login_ip == "127.0.0.1"
        assert user.login_count == 1
        
        # Verify tokens
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_login_invalid_credentials(self, db_session: AsyncSession, test_user: User):
        """Test login with invalid credentials."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(
                db_session,
                email=test_user.email,
                password="WrongPassword",
                ip_address="127.0.0.1"
            )
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in str(exc_info.value.detail)
        
        # Verify failed attempt tracking
        await db_session.refresh(test_user)
        assert test_user.failed_login_attempts == 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_login_nonexistent_user(self, db_session: AsyncSession):
        """Test login with non-existent email."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(
                db_session,
                email="nonexistent@example.com",
                password="AnyPassword123!",
                ip_address="127.0.0.1"
            )
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_login_locked_account(self, db_session: AsyncSession, locked_user: User):
        """Test login with locked account."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(
                db_session,
                email=locked_user.email,
                password="LockedPassword123!",
                ip_address="127.0.0.1"
            )
        
        assert exc_info.value.status_code == status.HTTP_423_LOCKED
        assert "Account locked until" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_login_disabled_account(self, db_session: AsyncSession, disabled_user: User):
        """Test login with disabled account."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login(
                db_session,
                email=disabled_user.email,
                password="DisabledPassword123!",
                ip_address="127.0.0.1"
            )
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Account is disabled" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_account_lockout_after_max_attempts(self, db_session: AsyncSession, test_user: User):
        """Test account lockout after maximum failed attempts."""
        # Make multiple failed login attempts
        for i in range(auth_service.max_failed_attempts):
            with pytest.raises(HTTPException):
                await auth_service.login(
                    db_session,
                    email=test_user.email,
                    password="WrongPassword",
                    ip_address="127.0.0.1"
                )
            
            await db_session.refresh(test_user)
            if i < auth_service.max_failed_attempts - 1:
                assert test_user.failed_login_attempts == i + 1
                assert test_user.locked_until is None
        
        # Verify account is locked after max attempts
        await db_session.refresh(test_user)
        assert test_user.failed_login_attempts == auth_service.max_failed_attempts
        assert test_user.locked_until is not None
        assert test_user.locked_until > datetime.utcnow()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_refresh_tokens_success(self, db_session: AsyncSession, test_user: User, auth_tokens: dict):
        """Test successful token refresh."""
        refresh_token = auth_tokens["refresh_token"]
        
        new_tokens = await auth_service.refresh_tokens(
            db_session,
            refresh_token=refresh_token,
            ip_address="127.0.0.1"
        )
        
        # Verify new tokens are different
        assert new_tokens["access_token"] != auth_tokens["access_token"]
        assert new_tokens["refresh_token"] != auth_tokens["refresh_token"]
        assert new_tokens["token_type"] == "bearer"
        assert "user_profile" in new_tokens
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_refresh_tokens_invalid_token(self, db_session: AsyncSession):
        """Test token refresh with invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_tokens(
                db_session,
                refresh_token="invalid.refresh.token",
                ip_address="127.0.0.1"
            )
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_refresh_tokens_reuse_detection(self, db_session: AsyncSession, test_user: User, auth_tokens: dict):
        """Test token reuse detection."""
        refresh_token = auth_tokens["refresh_token"]
        
        # Use token first time
        await auth_service.refresh_tokens(
            db_session,
            refresh_token=refresh_token,
            ip_address="127.0.0.1"
        )
        
        # Try to use same token again
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_tokens(
                db_session,
                refresh_token=refresh_token,
                ip_address="127.0.0.1"
            )
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token reuse detected" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_logout_success(self, db_session: AsyncSession, test_user: User, auth_tokens: dict):
        """Test successful logout."""
        access_token = auth_tokens["access_token"]
        refresh_token = auth_tokens["refresh_token"]
        
        await auth_service.logout(
            db_session,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        # Verify tokens are blacklisted by trying to use access token
        with pytest.raises(HTTPException):
            await auth_service.verify_access_token(access_token)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_logout_all_devices(self, db_session: AsyncSession, test_user: User):
        """Test logout from all devices."""
        # Create multiple refresh tokens (simulate multiple devices)
        tokens1 = await auth_service._generate_auth_tokens(db_session, test_user)
        tokens2 = await auth_service._generate_auth_tokens(db_session, test_user)
        await db_session.commit()
        
        # Logout from all devices
        await auth_service.logout_all_devices(db_session, str(test_user.id))
        
        # Verify all refresh tokens are revoked
        with pytest.raises(HTTPException):
            await auth_service.refresh_tokens(
                db_session,
                refresh_token=tokens1["refresh_token"],
                ip_address="127.0.0.1"
            )
        
        with pytest.raises(HTTPException):
            await auth_service.refresh_tokens(
                db_session,
                refresh_token=tokens2["refresh_token"],
                ip_address="127.0.0.1"
            )
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_verify_access_token_success(self, test_user: User, auth_tokens: dict):
        """Test successful access token verification."""
        access_token = auth_tokens["access_token"]
        
        with patch.object(auth_service, '_is_token_blacklisted', return_value=False), \
             patch.object(auth_service, '_verify_session', return_value=True):
            
            payload = await auth_service.verify_access_token(access_token)
            
            assert payload["sub"] == str(test_user.id)
            assert payload["email"] == test_user.email
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_verify_access_token_blacklisted(self, auth_tokens: dict):
        """Test access token verification with blacklisted token."""
        access_token = auth_tokens["access_token"]
        
        with patch.object(auth_service, '_is_token_blacklisted', return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.verify_access_token(access_token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Token has been revoked" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_verify_access_token_invalid_session(self, auth_tokens: dict):
        """Test access token verification with invalid session."""
        access_token = auth_tokens["access_token"]
        
        with patch.object(auth_service, '_is_token_blacklisted', return_value=False), \
             patch.object(auth_service, '_verify_session', return_value=False):
            
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.verify_access_token(access_token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Session invalid or expired" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_verify_access_token_subscription_tier_check(self, verified_user: User):
        """Test access token verification with subscription tier requirements."""
        # Generate tokens for verified user with STARTER tier
        tokens = await auth_service._generate_auth_tokens(None, verified_user)
        access_token = tokens["access_token"]
        
        with patch.object(auth_service, '_is_token_blacklisted', return_value=False), \
             patch.object(auth_service, '_verify_session', return_value=True):
            
            # Should succeed for FREE tier requirement
            payload = await auth_service.verify_access_token(
                access_token, 
                required_tier=SubscriptionTier.FREE
            )
            assert payload["sub"] == str(verified_user.id)
            
            # Should succeed for STARTER tier requirement
            payload = await auth_service.verify_access_token(
                access_token, 
                required_tier=SubscriptionTier.STARTER
            )
            assert payload["sub"] == str(verified_user.id)
            
            # Should fail for ENTERPRISE tier requirement
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.verify_access_token(
                    access_token, 
                    required_tier=SubscriptionTier.ENTERPRISE
                )
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Subscription tier" in str(exc_info.value.detail)


class TestAuthServiceHelpers:
    """Test helper methods in AuthenticationService."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    def test_validate_email(self):
        """Test email validation."""
        # Valid emails
        assert auth_service._validate_email("user@example.com") is True
        assert auth_service._validate_email("test.user@domain.co.uk") is True
        assert auth_service._validate_email("user.name+tag@example.com") is True
        
        # Invalid emails
        assert auth_service._validate_email("invalid-email") is False
        assert auth_service._validate_email("@example.com") is False
        assert auth_service._validate_email("user@") is False
        assert auth_service._validate_email("user.example.com") is False
        assert auth_service._validate_email("") is False
    
    @pytest.mark.unit
    def test_check_tier_access(self):
        """Test subscription tier access checking."""
        # Test FREE tier access
        assert auth_service._check_tier_access("free", SubscriptionTier.FREE) is True
        assert auth_service._check_tier_access("starter", SubscriptionTier.FREE) is True
        assert auth_service._check_tier_access("enterprise", SubscriptionTier.FREE) is True
        
        # Test STARTER tier access
        assert auth_service._check_tier_access("free", SubscriptionTier.STARTER) is False
        assert auth_service._check_tier_access("starter", SubscriptionTier.STARTER) is True
        assert auth_service._check_tier_access("enterprise", SubscriptionTier.STARTER) is True
        
        # Test ENTERPRISE tier access
        assert auth_service._check_tier_access("free", SubscriptionTier.ENTERPRISE) is False
        assert auth_service._check_tier_access("starter", SubscriptionTier.ENTERPRISE) is False
        assert auth_service._check_tier_access("enterprise", SubscriptionTier.ENTERPRISE) is True
        
        # Test unknown tier
        assert auth_service._check_tier_access("unknown", SubscriptionTier.STARTER) is False
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.auth
    async def test_generate_auth_tokens(self, db_session: AsyncSession, test_user: User):
        """Test token generation."""
        device_info = {
            "device_id": "test-device-123",
            "device_name": "Test Device",
            "user_agent": "Test User Agent"
        }
        
        tokens = await auth_service._generate_auth_tokens(
            db_session,
            test_user,
            device_id=device_info["device_id"],
            device_name=device_info["device_name"],
            user_agent=device_info["user_agent"],
            ip_address="127.0.0.1"
        )
        
        # Verify token structure
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert "user_profile" in tokens
        
        # Verify token contents
        access_payload = jwt_manager.decode_token(tokens["access_token"], verify_exp=False)
        refresh_payload = jwt_manager.decode_token(tokens["refresh_token"], verify_exp=False)
        
        assert access_payload["sub"] == str(test_user.id)
        assert access_payload["email"] == test_user.email
        assert access_payload["token_type"] == "access"
        
        assert refresh_payload["sub"] == str(test_user.id)
        assert refresh_payload["token_type"] == "refresh"
        assert refresh_payload["device_id"] == device_info["device_id"]


class TestAuthServiceSecurity:
    """Test security aspects of authentication service."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.security
    async def test_password_timing_attack_prevention(self, db_session: AsyncSession, test_user: User):
        """Test that login timing is consistent for existing vs non-existing users."""
        import time
        
        # Time login with existing user (wrong password)
        start_time = time.time()
        try:
            await auth_service.login(
                db_session,
                email=test_user.email,
                password="WrongPassword",
                ip_address="127.0.0.1"
            )
        except HTTPException:
            pass
        existing_user_time = time.time() - start_time
        
        # Time login with non-existing user
        start_time = time.time()
        try:
            await auth_service.login(
                db_session,
                email="nonexistent@example.com",
                password="AnyPassword",
                ip_address="127.0.0.1"
            )
        except HTTPException:
            pass
        nonexistent_user_time = time.time() - start_time
        
        # Times should be similar (within reasonable variance)
        # This is a basic check - in practice, you'd want more sophisticated timing analysis
        time_difference = abs(existing_user_time - nonexistent_user_time)
        assert time_difference < 0.1  # 100ms variance allowed
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.security
    async def test_input_sanitization(self, db_session: AsyncSession):
        """Test that user inputs are properly sanitized."""
        malicious_inputs = {
            "business_idea": "<script>alert('XSS')</script>",
            "target_market": "'; DROP TABLE users; --",
            "full_name": "<img src=x onerror=alert('XSS')>",
            "company_name": "javascript:alert('XSS')"
        }
        
        user_data = {
            "email": "sanitization@example.com",
            "password": "SecurePassword123!",
            **malicious_inputs
        }
        
        user, tokens = await auth_service.register_user(db_session, **user_data)
        
        # Verify inputs are sanitized (exact sanitization depends on implementation)
        assert "<script>" not in user.business_idea
        assert "DROP TABLE" not in user.target_market
        assert "<img" not in user.full_name
        assert "javascript:" not in user.company_name
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.security
    async def test_case_insensitive_email_handling(self, db_session: AsyncSession):
        """Test that email addresses are handled case-insensitively."""
        # Register with lowercase email
        user_data = {
            "email": "CaseTest@Example.Com",
            "password": "SecurePassword123!",
            "business_idea": "Test business for case sensitivity"
        }
        
        user, tokens = await auth_service.register_user(db_session, **user_data)
        
        # Verify email is stored in lowercase
        assert user.email == "casetest@example.com"
        
        # Verify login works with different casing
        login_user, login_tokens = await auth_service.login(
            db_session,
            email="CASETEST@EXAMPLE.COM",
            password="SecurePassword123!",
            ip_address="127.0.0.1"
        )
        
        assert login_user.id == user.id
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.security
    async def test_concurrent_login_attempts(self, db_session: AsyncSession, test_user: User):
        """Test handling of concurrent login attempts."""
        import asyncio
        
        async def failed_login_attempt():
            try:
                await auth_service.login(
                    db_session,
                    email=test_user.email,
                    password="WrongPassword",
                    ip_address="127.0.0.1"
                )
            except HTTPException:
                pass
        
        # Run multiple failed login attempts concurrently
        tasks = [failed_login_attempt() for _ in range(3)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify failed attempts are tracked correctly
        await db_session.refresh(test_user)
        assert test_user.failed_login_attempts >= 3