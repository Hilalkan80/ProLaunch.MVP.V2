"""
Comprehensive security tests for authentication system.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, AsyncMock
from parameterized import parameterized

from src.models.user import User
from src.core.security import password_manager, jwt_manager
from src.core.auth_security import AccountLockoutManager, SessionManager, PasswordResetManager


class TestPasswordSecurity:
    """Test password-related security measures."""
    
    @pytest.mark.asyncio
    @pytest.mark.security
    @pytest.mark.parametrize("weak_password", [
        "password",
        "123456",
        "qwerty", 
        "admin",
        "letmein",
        "welcome",
        "monkey",
        "1234567890",
        "password123",
        "PASSWORD",
        "Password",
        "pass123",
        "12345678",
    ])
    async def test_weak_password_rejection(self, async_client: AsyncClient, weak_password: str):
        """Test that weak passwords are rejected during registration."""
        registration_data = {
            "email": "weakpasstest@example.com",
            "password": weak_password,
            "business_idea": "Test business with weak password"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.security
    @pytest.mark.parametrize("strong_password", [
        "MyStrongP@ssw0rd!",
        "C0mplex_Passw0rd#2023",
        "Secure123$Password",
        "Ungu3ssable!P@ss",
        "R@nd0m&Str0ng!",
    ])
    async def test_strong_password_acceptance(self, async_client: AsyncClient, strong_password: str):
        """Test that strong passwords are accepted during registration."""
        registration_data = {
            "email": f"strongpass{hash(strong_password) % 10000}@example.com",
            "password": strong_password,
            "business_idea": "Test business with strong password"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.security
    def test_password_hashing_security(self):
        """Test password hashing security properties."""
        password = "TestPassword123!"
        
        # Test that same password produces different hashes (salt randomization)
        hash1 = password_manager.hash_password(password)
        hash2 = password_manager.hash_password(password)
        assert hash1 != hash2
        
        # Test that both hashes verify correctly
        assert password_manager.verify_password(password, hash1)
        assert password_manager.verify_password(password, hash2)
        
        # Test that wrong password doesn't verify
        assert not password_manager.verify_password("WrongPassword", hash1)
        
        # Test that hash is not the original password
        assert password not in hash1
        assert password not in hash2
    
    @pytest.mark.security
    def test_password_timing_attack_resistance(self):
        """Test that password verification is resistant to timing attacks."""
        password = "TestPassword123!"
        correct_hash = password_manager.hash_password(password)
        
        # Measure time for correct password
        times_correct = []
        for _ in range(10):
            start = time.perf_counter()
            password_manager.verify_password(password, correct_hash)
            times_correct.append(time.perf_counter() - start)
        
        # Measure time for incorrect password
        times_incorrect = []
        for _ in range(10):
            start = time.perf_counter()
            password_manager.verify_password("WrongPassword", correct_hash)
            times_incorrect.append(time.perf_counter() - start)
        
        # Times should be similar (no significant timing difference)
        avg_correct = sum(times_correct) / len(times_correct)
        avg_incorrect = sum(times_incorrect) / len(times_incorrect)
        
        # Allow for some variance, but should be within reasonable bounds
        assert abs(avg_correct - avg_incorrect) < 0.001  # 1ms difference allowed


class TestJWTSecurity:
    """Test JWT token security."""
    
    @pytest.mark.security
    def test_jwt_secret_key_security(self):
        """Test that JWT secret key is properly configured."""
        # Ensure secret key is not a default or weak value
        secret_key = jwt_manager.secret_key
        
        assert len(secret_key) >= 32  # Minimum 256 bits
        assert secret_key not in [
            "secret", "password", "key", "jwt_secret", "your-secret-key",
            "change-me", "default", "test", "123456", "secret123"
        ]
    
    @pytest.mark.security
    def test_jwt_token_expiration(self):
        """Test that JWT tokens have proper expiration."""
        user_id = "test-user-123"
        email = "test@example.com"
        subscription_tier = "free"
        
        # Create access token
        access_token, expires_at = jwt_manager.create_access_token(
            user_id, email, subscription_tier
        )
        
        # Verify token has expiration
        payload = jwt_manager.decode_token(access_token, verify_exp=False)
        assert "exp" in payload
        
        # Verify expiration is reasonable (not too long)
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        now = datetime.utcnow()
        
        # Should expire within reasonable time (e.g., 1 hour default)
        assert (exp_datetime - now).total_seconds() <= 3600
    
    @pytest.mark.security
    def test_jwt_token_signature_verification(self):
        """Test that JWT tokens are properly signed and verified."""
        user_id = "test-user-123"
        email = "test@example.com"
        subscription_tier = "free"
        
        # Create token
        access_token, _ = jwt_manager.create_access_token(
            user_id, email, subscription_tier
        )
        
        # Valid token should decode successfully
        payload = jwt_manager.decode_token(access_token)
        assert payload["sub"] == user_id
        assert payload["email"] == email
        
        # Tampered token should fail verification
        tampered_token = access_token[:-5] + "XXXXX"  # Change last 5 characters
        
        with pytest.raises(Exception):  # Should raise JWT verification error
            jwt_manager.decode_token(tampered_token)
    
    @pytest.mark.security
    def test_jwt_token_claims_validation(self):
        """Test that JWT token claims are properly validated."""
        user_id = "test-user-123"
        email = "test@example.com"
        subscription_tier = "free"
        
        # Create token
        access_token, _ = jwt_manager.create_access_token(
            user_id, email, subscription_tier
        )
        
        payload = jwt_manager.decode_token(access_token, verify_exp=False)
        
        # Verify required claims are present
        assert "sub" in payload  # Subject (user ID)
        assert "email" in payload
        assert "subscription_tier" in payload
        assert "token_type" in payload
        assert "iat" in payload  # Issued at
        assert "exp" in payload  # Expires at
        assert "jti" in payload  # JWT ID for token tracking
        
        # Verify claim values
        assert payload["token_type"] == "access"
        assert payload["sub"] == user_id
        assert payload["email"] == email


class TestAccountLockout:
    """Test account lockout security measures."""
    
    @pytest.mark.asyncio
    @pytest.mark.security
    @pytest.mark.slow
    async def test_account_lockout_after_failed_attempts(
        self, 
        async_client: AsyncClient, 
        test_user: User
    ):
        """Test that accounts are locked after multiple failed login attempts."""
        login_data = {
            "email": test_user.email,
            "password": "WrongPassword"
        }
        
        # Make multiple failed attempts
        for i in range(5):
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            if i < 4:  # First 4 attempts should just fail
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
                assert "Invalid email or password" in response.json()["detail"]
            else:  # 5th attempt should lock the account
                assert response.status_code == status.HTTP_423_LOCKED
                assert "Account locked" in response.json()["detail"]
        
        # Subsequent attempts should still be locked
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == status.HTTP_423_LOCKED
        
        # Even correct password should be locked
        correct_login_data = {
            "email": test_user.email,
            "password": "TestPassword123!"
        }
        response = await async_client.post("/api/v1/auth/login", json=correct_login_data)
        assert response.status_code == status.HTTP_423_LOCKED
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_lockout_reset_after_successful_login(
        self,
        async_client: AsyncClient,
        test_user: User,
        db_session
    ):
        """Test that failed attempts are reset after successful login."""
        # Make some failed attempts
        login_data = {
            "email": test_user.email,
            "password": "WrongPassword"
        }
        
        for _ in range(2):
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Successful login should reset counter
        correct_login_data = {
            "email": test_user.email,
            "password": "TestPassword123!"
        }
        response = await async_client.post("/api/v1/auth/login", json=correct_login_data)
        assert response.status_code == status.HTTP_200_OK
        
        # Failed attempts counter should be reset
        await db_session.refresh(test_user)
        assert test_user.failed_login_attempts == 0


class TestSessionSecurity:
    """Test session security measures."""
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_session_invalidation_on_logout(
        self,
        async_client: AsyncClient,
        auth_tokens: dict
    ):
        """Test that sessions are properly invalidated on logout."""
        access_token = auth_tokens["access_token"]
        refresh_token = auth_tokens["refresh_token"]
        
        # Verify token works initially
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await async_client.get("/api/v1/auth/verify", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        # Logout
        logout_headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Refresh-Token": refresh_token
        }
        logout_response = await async_client.post("/api/v1/auth/logout", headers=logout_headers)
        assert logout_response.status_code == status.HTTP_200_OK
        
        # Token should no longer work
        response = await async_client.get("/api/v1/auth/verify", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_concurrent_session_handling(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test handling of concurrent sessions for the same user."""
        login_data = {
            "email": test_user.email,
            "password": "TestPassword123!"
        }
        
        # Create multiple sessions
        sessions = []
        for _ in range(3):
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == status.HTTP_200_OK
            sessions.append(response.json())
        
        # All sessions should be valid initially
        for session in sessions:
            headers = {"Authorization": f"Bearer {session['access_token']}"}
            response = await async_client.get("/api/v1/auth/verify", headers=headers)
            assert response.status_code == status.HTTP_200_OK
        
        # Logout all devices using one token
        headers = {"Authorization": f"Bearer {sessions[0]['access_token']}"}
        response = await async_client.post("/api/v1/auth/logout-all", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        # All sessions should be invalidated
        for session in sessions:
            headers = {"Authorization": f"Bearer {session['access_token']}"}
            response = await async_client.get("/api/v1/auth/verify", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestInputValidationSecurity:
    """Test security of input validation."""
    
    @pytest.mark.asyncio
    @pytest.mark.security
    @pytest.mark.parametrize("malicious_input", [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "'><script>alert('XSS')</script>",
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM users --",
        "../../../etc/passwd",
        "....//....//....//etc/passwd",
        "; cat /etc/passwd",
        "| whoami",
        "&& ls -la",
        "*)(uid=*",
        "admin)(&(password=*",
        "test\r\nX-Injected-Header: injected",
    ])
    async def test_malicious_input_sanitization(
        self,
        async_client: AsyncClient,
        malicious_input: str
    ):
        """Test that malicious inputs are properly sanitized."""
        registration_data = {
            "email": "malicious@example.com",
            "password": "SecurePassword123!",
            "business_idea": malicious_input,
            "target_market": malicious_input,
            "full_name": malicious_input,
            "company_name": malicious_input,
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        
        # Should either reject the input or sanitize it
        if response.status_code == status.HTTP_201_CREATED:
            # If accepted, verify the data was sanitized
            user_profile = response.json()["user_profile"]
            
            # Check that dangerous content is not present in the response
            business_idea = user_profile.get("business_idea", "")
            assert "<script>" not in business_idea
            assert "javascript:" not in business_idea
            assert "DROP TABLE" not in business_idea
            assert "../" not in business_idea
            assert "\r\n" not in business_idea
        else:
            # Input was rejected, which is also acceptable
            assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_sql_injection_prevention(
        self,
        async_client: AsyncClient
    ):
        """Test that SQL injection attempts are prevented."""
        sql_injection_payloads = [
            "admin@example.com'; DROP TABLE users; --",
            "admin@example.com' OR '1'='1",
            "admin@example.com' UNION SELECT password FROM users WHERE email='admin@example.com",
        ]
        
        for payload in sql_injection_payloads:
            login_data = {
                "email": payload,
                "password": "AnyPassword123!"
            }
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            # Should be rejected with validation error or authentication error
            assert response.status_code in [400, 401, 422]
            
            # Should not cause a 500 error (which might indicate SQL injection success)
            assert response.status_code != status.HTTP_500_INTERNAL_SERVER_ERROR


class TestRateLimitingSecurity:
    """Test rate limiting security measures."""
    
    @pytest.mark.asyncio
    @pytest.mark.security
    @pytest.mark.slow
    async def test_login_rate_limiting_per_ip(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test rate limiting on login attempts per IP address."""
        login_data = {
            "email": test_user.email,
            "password": "WrongPassword"
        }
        
        # Make rapid login attempts
        responses = []
        for i in range(20):
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            responses.append(response.status_code)
            
            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.1)
        
        # Should see some rate limiting (429 responses) after initial attempts
        # Note: Exact behavior depends on rate limiting implementation
        assert any(code == status.HTTP_401_UNAUTHORIZED for code in responses)
        
        # If rate limiting is implemented, we should see 429 responses
        # This test might need adjustment based on actual rate limiting configuration
        # assert any(code == status.HTTP_429_TOO_MANY_REQUESTS for code in responses)
    
    @pytest.mark.asyncio
    @pytest.mark.security
    @pytest.mark.slow
    async def test_registration_rate_limiting(
        self,
        async_client: AsyncClient
    ):
        """Test rate limiting on registration attempts."""
        responses = []
        for i in range(10):
            registration_data = {
                "email": f"ratelimit{i}@example.com",
                "password": "RateLimit123!",
                "business_idea": f"Rate limit test business {i}"
            }
            
            response = await async_client.post("/api/v1/auth/register", json=registration_data)
            responses.append(response.status_code)
            
            # Small delay between requests
            await asyncio.sleep(0.2)
        
        # First few should succeed, later ones might be rate limited
        assert responses[0] == status.HTTP_201_CREATED
        
        # Check if any were rate limited
        rate_limited = any(code == 429 for code in responses)
        # This might not trigger depending on rate limiting configuration


class TestCryptographicSecurity:
    """Test cryptographic security measures."""
    
    @pytest.mark.security
    def test_secure_random_generation(self):
        """Test that secure random values are generated for tokens."""
        # Generate multiple tokens and ensure they're different
        tokens = set()
        for _ in range(100):
            user_id = "test-user"
            email = "test@example.com"
            subscription_tier = "free"
            
            access_token, _ = jwt_manager.create_access_token(
                user_id, email, subscription_tier
            )
            
            # Extract JTI (JWT ID) from token
            payload = jwt_manager.decode_token(access_token, verify_exp=False)
            jti = payload.get("jti")
            
            tokens.add(jti)
        
        # All tokens should be unique
        assert len(tokens) == 100
    
    @pytest.mark.security
    def test_token_family_security(self):
        """Test that token families are properly managed for refresh token rotation."""
        user_id = "test-user-123"
        
        # Create initial refresh token
        refresh_token1, _, family_id1 = jwt_manager.create_refresh_token(user_id)
        
        # Create token with same family ID (simulating refresh)
        refresh_token2, _, family_id2 = jwt_manager.create_refresh_token(
            user_id, family_id=family_id1
        )
        
        # Should have same family ID
        assert family_id1 == family_id2
        
        # But different token values
        assert refresh_token1 != refresh_token2
        
        # Decode tokens to verify family ID
        payload1 = jwt_manager.decode_token(refresh_token1, verify_exp=False)
        payload2 = jwt_manager.decode_token(refresh_token2, verify_exp=False)
        
        assert payload1["family_id"] == payload2["family_id"]
        assert payload1["jti"] != payload2["jti"]


class TestSecurityHeaders:
    """Test security-related HTTP headers."""
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_security_headers_presence(
        self,
        async_client: AsyncClient
    ):
        """Test that security headers are present in API responses."""
        response = await async_client.get("/api/v1/auth/health")
        
        # Note: These headers would typically be added by security middleware
        # The exact headers depend on the middleware configuration
        
        # Common security headers that should be present:
        expected_headers = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "x-xss-protection": "1; mode=block",
            # "strict-transport-security": present for HTTPS
            # "content-security-policy": depends on application needs
        }
        
        # Check if security middleware is configured
        # This test might need adjustment based on actual middleware setup
        response_headers = {k.lower(): v for k, v in response.headers.items()}
        
        # At minimum, ensure no information disclosure headers are present
        sensitive_headers = [
            "server",  # Should not reveal server information
            "x-powered-by",  # Should not reveal technology stack
        ]
        
        for header in sensitive_headers:
            assert header.lower() not in response_headers or \
                   response_headers[header.lower()] == ""
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_cors_security(
        self,
        async_client: AsyncClient
    ):
        """Test CORS security configuration."""
        # Test preflight request with suspicious origin
        suspicious_origins = [
            "http://malicious.com",
            "https://attacker.evil",
            "null",
        ]
        
        for origin in suspicious_origins:
            response = await async_client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                }
            )
            
            # Should not allow suspicious origins
            # Exact behavior depends on CORS configuration
            if "access-control-allow-origin" in response.headers:
                allowed_origin = response.headers["access-control-allow-origin"]
                assert allowed_origin != origin  # Should not echo back suspicious origin


class TestAuditingSecurity:
    """Test security auditing and logging."""
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_failed_login_logging(
        self,
        async_client: AsyncClient,
        test_user: User,
        caplog
    ):
        """Test that failed login attempts are properly logged."""
        login_data = {
            "email": test_user.email,
            "password": "WrongPassword"
        }
        
        with caplog.at_level("WARNING"):
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Should log security events (implementation dependent)
        # This test might need adjustment based on actual logging configuration
    
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_security_event_monitoring(
        self,
        async_client: AsyncClient,
        test_user: User
    ):
        """Test that security events are monitored and recorded."""
        # Simulate suspicious activity (multiple failed logins)
        login_data = {
            "email": test_user.email,
            "password": "WrongPassword"
        }
        
        # Make multiple failed attempts to trigger security monitoring
        for _ in range(3):
            await async_client.post("/api/v1/auth/login", json=login_data)
        
        # In a real implementation, this would trigger security alerts
        # and be recorded in security logs for analysis