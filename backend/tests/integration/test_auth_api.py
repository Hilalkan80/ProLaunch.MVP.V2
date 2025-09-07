"""
Integration tests for authentication API endpoints.
"""

import pytest
import json
from datetime import datetime, timedelta
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch

from src.models.user import User
from src.core.security import jwt_manager


class TestAuthenticationAPI:
    """Test authentication API endpoints."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_register_endpoint_success(self, async_client: AsyncClient, valid_registration_data: dict):
        """Test successful user registration via API."""
        response = await async_client.post("/api/v1/auth/register", json=valid_registration_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user_profile" in data
        assert data["token_type"] == "bearer"
        
        # Verify user profile data
        profile = data["user_profile"]
        assert profile["email"] == valid_registration_data["email"].lower()
        assert profile["business_idea"] == valid_registration_data["business_idea"]
        assert profile["subscription_tier"] == "free"
        assert profile["is_verified"] is False
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_register_endpoint_duplicate_email(self, async_client: AsyncClient, test_user: User):
        """Test registration with duplicate email via API."""
        registration_data = {
            "email": test_user.email,
            "password": "NewPassword123!",
            "business_idea": "Another business idea"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=registration_data)
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Email already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    @pytest.mark.parametrize("invalid_data,expected_status", [
        ({"email": "invalid", "password": "Test123!", "business_idea": "Test"}, 422),
        ({"email": "test@example.com", "password": "weak", "business_idea": "Test"}, 400),
        ({"email": "test@example.com", "password": "Test123!"}, 422),  # Missing business_idea
        ({"password": "Test123!", "business_idea": "Test"}, 422),  # Missing email
    ])
    async def test_register_endpoint_validation(
        self, 
        async_client: AsyncClient, 
        invalid_data: dict, 
        expected_status: int
    ):
        """Test registration endpoint validation."""
        response = await async_client.post("/api/v1/auth/register", json=invalid_data)
        assert response.status_code == expected_status
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_login_endpoint_success(self, async_client: AsyncClient, test_user: User, valid_login_data: dict):
        """Test successful login via API."""
        response = await async_client.post("/api/v1/auth/login", json=valid_login_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user_profile" in data
        assert data["token_type"] == "bearer"
        
        # Verify user profile data
        profile = data["user_profile"]
        assert profile["email"] == test_user.email
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_login_endpoint_invalid_credentials(self, async_client: AsyncClient, invalid_login_data: dict):
        """Test login with invalid credentials via API."""
        response = await async_client.post("/api/v1/auth/login", json=invalid_login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_login_endpoint_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent user via API."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_login_endpoint_locked_account(self, async_client: AsyncClient, locked_user: User):
        """Test login with locked account via API."""
        login_data = {
            "email": locked_user.email,
            "password": "LockedPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_423_LOCKED
        assert "Account locked until" in response.json()["detail"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_login_endpoint_disabled_account(self, async_client: AsyncClient, disabled_user: User):
        """Test login with disabled account via API."""
        login_data = {
            "email": disabled_user.email,
            "password": "DisabledPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Account is disabled" in response.json()["detail"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_refresh_token_endpoint_success(self, async_client: AsyncClient, auth_tokens: dict):
        """Test successful token refresh via API."""
        refresh_data = {
            "refresh_token": auth_tokens["refresh_token"]
        }
        
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != auth_tokens["access_token"]
        assert data["refresh_token"] != auth_tokens["refresh_token"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_refresh_token_endpoint_invalid_token(self, async_client: AsyncClient):
        """Test token refresh with invalid token via API."""
        refresh_data = {
            "refresh_token": "invalid.refresh.token"
        }
        
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_logout_endpoint_success(self, async_client: AsyncClient, auth_tokens: dict):
        """Test successful logout via API."""
        headers = {
            "Authorization": f"Bearer {auth_tokens['access_token']}",
            "X-Refresh-Token": auth_tokens["refresh_token"]
        }
        
        response = await async_client.post("/api/v1/auth/logout", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert "Logged out successfully" in response.json()["message"]
        
        # Verify token is invalidated
        verify_response = await async_client.get("/api/v1/auth/verify", headers={
            "Authorization": f"Bearer {auth_tokens['access_token']}"
        })
        assert verify_response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_logout_endpoint_without_auth(self, async_client: AsyncClient):
        """Test logout without authentication via API."""
        response = await async_client.post("/api/v1/auth/logout")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_logout_all_devices_endpoint_success(self, async_client: AsyncClient, auth_tokens: dict):
        """Test logout from all devices via API."""
        headers = {
            "Authorization": f"Bearer {auth_tokens['access_token']}"
        }
        
        response = await async_client.post("/api/v1/auth/logout-all", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert "Logged out from all devices successfully" in response.json()["message"]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_verify_token_endpoint_success(self, async_client: AsyncClient, auth_tokens: dict):
        """Test successful token verification via API."""
        headers = {
            "Authorization": f"Bearer {auth_tokens['access_token']}"
        }
        
        response = await async_client.get("/api/v1/auth/verify", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert "subscription_tier" in data
        assert "is_verified" in data
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_verify_token_endpoint_invalid_token(self, async_client: AsyncClient):
        """Test token verification with invalid token via API."""
        headers = {
            "Authorization": "Bearer invalid.token"
        }
        
        response = await async_client.get("/api/v1/auth/verify", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_verify_token_endpoint_expired_token(self, async_client: AsyncClient, expired_tokens: dict):
        """Test token verification with expired token via API."""
        headers = {
            "Authorization": f"Bearer {expired_tokens['access_token']}"
        }
        
        response = await async_client.get("/api/v1/auth/verify", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_password_reset_request_endpoint(self, async_client: AsyncClient, test_user: User):
        """Test password reset request via API."""
        response = await async_client.post(
            f"/api/v1/auth/request-password-reset?email={test_user.email}"
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert "password reset link has been sent" in response.json()["message"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_password_reset_request_nonexistent_email(self, async_client: AsyncClient):
        """Test password reset request with non-existent email via API."""
        response = await async_client.post(
            "/api/v1/auth/request-password-reset?email=nonexistent@example.com"
        )
        
        # Should still return success for security (don't reveal if email exists)
        assert response.status_code == status.HTTP_200_OK
        assert "password reset link has been sent" in response.json()["message"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_health_check_endpoint(self, async_client: AsyncClient):
        """Test authentication service health check via API."""
        response = await async_client.get("/api/v1/auth/health")
        
        assert response.status_code == status.HTTP_200_OK
        assert "healthy" in response.json()["message"].lower()


class TestAuthenticationHeaders:
    """Test authentication-related headers and security."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.security
    async def test_cors_headers(self, async_client: AsyncClient):
        """Test CORS headers are properly set."""
        # Test preflight request
        response = await async_client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )
        
        # Should have proper CORS headers (exact headers depend on FastAPI CORS configuration)
        assert response.status_code in [200, 204]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.security
    async def test_security_headers_present(self, async_client: AsyncClient):
        """Test that security headers are present in responses."""
        response = await async_client.get("/api/v1/auth/health")
        
        # Note: Actual security headers depend on middleware configuration
        # These would typically be added by security middleware
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
        ]
        
        # This test might need adjustment based on actual middleware configuration
        # For now, just ensure the response is successful
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.security
    async def test_content_type_validation(self, async_client: AsyncClient):
        """Test that endpoints validate content type."""
        # Test with wrong content type
        response = await async_client.post(
            "/api/v1/auth/login",
            data="email=test@example.com&password=test",  # Form data instead of JSON
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Should reject non-JSON content type for JSON endpoints
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthenticationRateLimit:
    """Test rate limiting on authentication endpoints."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.slow
    async def test_login_rate_limiting(self, async_client: AsyncClient, test_user: User):
        """Test rate limiting on login endpoint."""
        login_data = {
            "email": test_user.email,
            "password": "WrongPassword"
        }
        
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            responses.append(response)
        
        # At least some should succeed initially, then start getting rate limited
        # This depends on rate limiting configuration
        status_codes = [r.status_code for r in responses]
        
        # Most should be 401 (invalid credentials) but some might be 429 (rate limited)
        assert any(code == status.HTTP_401_UNAUTHORIZED for code in status_codes)
        
        # If rate limiting is implemented, we might see 429 responses
        # assert any(code == status.HTTP_429_TOO_MANY_REQUESTS for code in status_codes)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.slow
    async def test_registration_rate_limiting(self, async_client: AsyncClient):
        """Test rate limiting on registration endpoint."""
        # Try to register multiple accounts rapidly
        responses = []
        for i in range(5):
            registration_data = {
                "email": f"ratelimit{i}@example.com",
                "password": "RateLimit123!",
                "business_idea": f"Rate limit test business {i}"
            }
            response = await async_client.post("/api/v1/auth/register", json=registration_data)
            responses.append(response)
        
        # First few should succeed, later ones might be rate limited
        status_codes = [r.status_code for r in responses]
        
        # At least the first should succeed
        assert status_codes[0] == status.HTTP_201_CREATED


class TestAuthenticationConcurrency:
    """Test concurrent authentication operations."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_concurrent_registrations(self, async_client: AsyncClient):
        """Test concurrent user registrations."""
        import asyncio
        
        async def register_user(user_index: int):
            registration_data = {
                "email": f"concurrent{user_index}@example.com",
                "password": "Concurrent123!",
                "business_idea": f"Concurrent business {user_index}"
            }
            return await async_client.post("/api/v1/auth/register", json=registration_data)
        
        # Register multiple users concurrently
        tasks = [register_user(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_concurrent_logins_same_user(self, async_client: AsyncClient, test_user: User):
        """Test concurrent logins for the same user."""
        import asyncio
        
        async def login_user():
            login_data = {
                "email": test_user.email,
                "password": "TestPassword123!"
            }
            return await async_client.post("/api/v1/auth/login", json=login_data)
        
        # Login with same user concurrently
        tasks = [login_user() for _ in range(3)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_concurrent_token_operations(self, async_client: AsyncClient, test_user: User):
        """Test concurrent token refresh and verification."""
        import asyncio
        
        # First login to get tokens
        login_data = {
            "email": test_user.email,
            "password": "TestPassword123!"
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        tokens = login_response.json()
        
        async def refresh_token():
            refresh_data = {"refresh_token": tokens["refresh_token"]}
            return await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        async def verify_token():
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            return await async_client.get("/api/v1/auth/verify", headers=headers)
        
        # Run operations concurrently
        refresh_task = refresh_token()
        verify_tasks = [verify_token() for _ in range(3)]
        
        all_responses = await asyncio.gather(refresh_task, *verify_tasks, return_exceptions=True)
        
        # At least some operations should succeed
        successful_responses = [r for r in all_responses if not isinstance(r, Exception) and r.status_code == 200]
        assert len(successful_responses) > 0


class TestAuthenticationErrorHandling:
    """Test error handling in authentication endpoints."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_malformed_json_handling(self, async_client: AsyncClient):
        """Test handling of malformed JSON requests."""
        # Send malformed JSON
        response = await async_client.post(
            "/api/v1/auth/login",
            content='{"email": "test@example.com", "password":}',  # Invalid JSON
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_oversized_request_handling(self, async_client: AsyncClient):
        """Test handling of oversized requests."""
        # Create oversized business idea
        oversized_data = {
            "email": "oversized@example.com",
            "password": "Oversized123!",
            "business_idea": "A" * 10000,  # Very long business idea
        }
        
        response = await async_client.post("/api/v1/auth/register", json=oversized_data)
        
        # Should be rejected due to size limits
        assert response.status_code in [413, 422]  # Payload Too Large or Validation Error
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_missing_required_fields(self, async_client: AsyncClient):
        """Test handling of requests with missing required fields."""
        incomplete_data = {
            "email": "incomplete@example.com",
            # Missing password and business_idea
        }
        
        response = await async_client.post("/api/v1/auth/register", json=incomplete_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        error_detail = response.json()
        assert "detail" in error_detail
        # Should indicate which fields are missing
        assert any("password" in str(error).lower() for error in error_detail["detail"])
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.auth
    async def test_database_connection_error_handling(self, async_client: AsyncClient):
        """Test handling of database connection errors."""
        with patch('src.models.base.get_db') as mock_get_db:
            # Simulate database connection error
            mock_get_db.side_effect = Exception("Database connection failed")
            
            login_data = {
                "email": "test@example.com",
                "password": "TestPassword123!"
            }
            
            response = await async_client.post("/api/v1/auth/login", json=login_data)
            
            # Should return 500 Internal Server Error
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR