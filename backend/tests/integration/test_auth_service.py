"""
Integration tests for Authentication Service

This module provides comprehensive integration tests for the authentication service
including user registration, login, token management, and security features.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from models.base import Base, get_db_context
from models.user import User, SubscriptionTier, ExperienceLevel
from models.token import RefreshToken, TokenBlacklist
from services.auth_service import auth_service
from core.security import jwt_manager, password_manager


# Test database configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://prolaunch:prolaunch123@localhost:5432/prolaunch_test"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Create a database session for testing"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_user_data():
    """Generate test user data"""
    return {
        "email": f"test_{uuid4().hex[:8]}@example.com",
        "password": "TestPassword123!",
        "business_idea": "An innovative SaaS platform for small businesses",
        "target_market": "Small to medium-sized businesses",
        "experience_level": "some-experience",
        "full_name": "Test User",
        "company_name": "Test Company Inc."
    }


class TestAuthenticationService:
    """Test suite for authentication service"""
    
    @pytest.mark.asyncio
    async def test_user_registration_success(self, db_session, test_user_data):
        """Test successful user registration"""
        user, tokens = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        # Verify user was created
        assert user is not None
        assert user.email == test_user_data["email"].lower()
        assert user.business_idea == test_user_data["business_idea"]
        assert user.subscription_tier == SubscriptionTier.FREE
        assert user.is_active is True
        assert user.is_verified is False
        
        # Verify tokens were generated
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert "expires_in" in tokens
        assert "user_profile" in tokens
        
        # Verify password was hashed
        assert user.password_hash != test_user_data["password"]
        assert password_manager.verify_password(
            test_user_data["password"],
            user.password_hash
        )
    
    @pytest.mark.asyncio
    async def test_user_registration_duplicate_email(self, db_session, test_user_data):
        """Test registration with duplicate email fails"""
        # Register first user
        await auth_service.register_user(db_session, **test_user_data)
        
        # Try to register with same email
        with pytest.raises(Exception) as exc_info:
            await auth_service.register_user(db_session, **test_user_data)
        
        assert "already registered" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_user_registration_weak_password(self, db_session, test_user_data):
        """Test registration with weak password fails"""
        test_user_data["password"] = "weak"
        
        with pytest.raises(Exception) as exc_info:
            await auth_service.register_user(db_session, **test_user_data)
        
        assert "password" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_user_login_success(self, db_session, test_user_data):
        """Test successful user login"""
        # Register user
        registered_user, _ = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        # Login
        user, tokens = await auth_service.login(
            db_session,
            email=test_user_data["email"],
            password=test_user_data["password"],
            device_info={"device_id": "test-device", "device_name": "Test Browser"},
            ip_address="127.0.0.1"
        )
        
        # Verify login was successful
        assert user.id == registered_user.id
        assert user.last_login_at is not None
        assert user.last_login_ip == "127.0.0.1"
        assert user.login_count == 1
        
        # Verify tokens
        assert "access_token" in tokens
        assert "refresh_token" in tokens
    
    @pytest.mark.asyncio
    async def test_user_login_wrong_password(self, db_session, test_user_data):
        """Test login with wrong password fails"""
        # Register user
        await auth_service.register_user(db_session, **test_user_data)
        
        # Try login with wrong password
        with pytest.raises(Exception) as exc_info:
            await auth_service.login(
                db_session,
                email=test_user_data["email"],
                password="WrongPassword123!",
                ip_address="127.0.0.1"
            )
        
        assert "invalid" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_user_login_nonexistent_email(self, db_session):
        """Test login with non-existent email fails"""
        with pytest.raises(Exception) as exc_info:
            await auth_service.login(
                db_session,
                email="nonexistent@example.com",
                password="AnyPassword123!",
                ip_address="127.0.0.1"
            )
        
        assert "invalid" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_account_lockout_after_failed_attempts(self, db_session, test_user_data):
        """Test account lockout after multiple failed login attempts"""
        # Register user
        await auth_service.register_user(db_session, **test_user_data)
        
        # Make multiple failed login attempts
        for _ in range(5):
            try:
                await auth_service.login(
                    db_session,
                    email=test_user_data["email"],
                    password="WrongPassword123!",
                    ip_address="127.0.0.1"
                )
            except:
                pass
        
        # Next attempt should result in lockout
        with pytest.raises(Exception) as exc_info:
            await auth_service.login(
                db_session,
                email=test_user_data["email"],
                password=test_user_data["password"],
                ip_address="127.0.0.1"
            )
        
        assert "locked" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_token_refresh_success(self, db_session, test_user_data):
        """Test successful token refresh"""
        # Register and login
        user, initial_tokens = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        # Wait a moment to ensure different token generation time
        await asyncio.sleep(0.1)
        
        # Refresh tokens
        new_tokens = await auth_service.refresh_tokens(
            db_session,
            refresh_token=initial_tokens["refresh_token"],
            ip_address="127.0.0.1"
        )
        
        # Verify new tokens were generated
        assert new_tokens["access_token"] != initial_tokens["access_token"]
        assert new_tokens["refresh_token"] != initial_tokens["refresh_token"]
        assert "user_profile" in new_tokens
    
    @pytest.mark.asyncio
    async def test_token_refresh_with_used_token_fails(self, db_session, test_user_data):
        """Test that reusing a refresh token fails and revokes token family"""
        # Register and login
        user, initial_tokens = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        # Use refresh token once
        new_tokens = await auth_service.refresh_tokens(
            db_session,
            refresh_token=initial_tokens["refresh_token"],
            ip_address="127.0.0.1"
        )
        
        # Try to use the same refresh token again
        with pytest.raises(Exception) as exc_info:
            await auth_service.refresh_tokens(
                db_session,
                refresh_token=initial_tokens["refresh_token"],
                ip_address="127.0.0.1"
            )
        
        assert "reuse" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_logout_success(self, db_session, test_user_data):
        """Test successful logout"""
        # Register and login
        user, tokens = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        # Logout
        await auth_service.logout(
            db_session,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"]
        )
        
        # Verify tokens are blacklisted
        payload = jwt_manager.decode_token(tokens["access_token"], verify_exp=False)
        jti = payload.get("jti")
        
        stmt = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
        result = await db_session.execute(stmt)
        blacklist_entry = result.scalar_one_or_none()
        
        assert blacklist_entry is not None
        assert blacklist_entry.reason == "User logout"
    
    @pytest.mark.asyncio
    async def test_logout_all_devices(self, db_session, test_user_data):
        """Test logout from all devices"""
        # Register user
        user, tokens1 = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        # Login from another device
        user, tokens2 = await auth_service.login(
            db_session,
            email=test_user_data["email"],
            password=test_user_data["password"],
            device_info={"device_id": "device2", "device_name": "Mobile"},
            ip_address="192.168.1.1"
        )
        
        # Logout from all devices
        await auth_service.logout_all_devices(db_session, str(user.id))
        
        # Verify all refresh tokens are revoked
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user.id
        )
        result = await db_session.execute(stmt)
        refresh_tokens = result.scalars().all()
        
        for token in refresh_tokens:
            assert token.revoked_at is not None
            assert token.revoke_reason == "Logout from all devices"
    
    @pytest.mark.asyncio
    async def test_verify_access_token_success(self, db_session, test_user_data):
        """Test successful access token verification"""
        # Register user
        user, tokens = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        # Verify access token
        payload = await auth_service.verify_access_token(
            tokens["access_token"]
        )
        
        assert payload["sub"] == str(user.id)
        assert payload["email"] == user.email
        assert payload["subscription_tier"] == "free"
    
    @pytest.mark.asyncio
    async def test_verify_access_token_with_required_tier(self, db_session, test_user_data):
        """Test access token verification with subscription tier requirement"""
        # Register user (defaults to FREE tier)
        user, tokens = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        # Verify with FREE tier requirement (should succeed)
        payload = await auth_service.verify_access_token(
            tokens["access_token"],
            required_tier=SubscriptionTier.FREE
        )
        assert payload is not None
        
        # Verify with higher tier requirement (should fail)
        with pytest.raises(Exception) as exc_info:
            await auth_service.verify_access_token(
                tokens["access_token"],
                required_tier=SubscriptionTier.GROWTH
            )
        
        assert "tier" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_inactive_user_cannot_login(self, db_session, test_user_data):
        """Test that inactive users cannot login"""
        # Register user
        user, _ = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        # Deactivate user
        stmt = select(User).where(User.id == user.id)
        result = await db_session.execute(stmt)
        db_user = result.scalar_one()
        db_user.is_active = False
        await db_session.commit()
        
        # Try to login
        with pytest.raises(Exception) as exc_info:
            await auth_service.login(
                db_session,
                email=test_user_data["email"],
                password=test_user_data["password"],
                ip_address="127.0.0.1"
            )
        
        assert "disabled" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_email_normalization(self, db_session, test_user_data):
        """Test that emails are normalized (lowercase)"""
        # Register with mixed case email
        test_user_data["email"] = "TeSt@ExAmPlE.cOm"
        user, _ = await auth_service.register_user(
            db_session,
            **test_user_data
        )
        
        assert user.email == "test@example.com"
        
        # Login with different case
        user, tokens = await auth_service.login(
            db_session,
            email="TEST@EXAMPLE.COM",
            password=test_user_data["password"],
            ip_address="127.0.0.1"
        )
        
        assert user.email == "test@example.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])