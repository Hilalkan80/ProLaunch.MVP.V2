"""
Unit tests for Security Module

This module provides unit tests for password management, JWT token operations,
and security utilities.
"""

import pytest
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4
import jwt as pyjwt

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from core.security import (
    password_manager,
    jwt_manager,
    security_utils,
    PasswordManager,
    JWTManager,
    SecurityUtils
)


class TestPasswordManager:
    """Test suite for password management"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "TestPassword123!"
        hashed = password_manager.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are typically 60 chars
        assert hashed.startswith("$2b$")  # Bcrypt prefix
    
    def test_verify_password_correct(self):
        """Test verifying correct password"""
        password = "TestPassword123!"
        hashed = password_manager.hash_password(password)
        
        assert password_manager.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verifying incorrect password"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = password_manager.hash_password(password)
        
        assert password_manager.verify_password(wrong_password, hashed) is False
    
    def test_hash_uniqueness(self):
        """Test that same password produces different hashes (salt)"""
        password = "TestPassword123!"
        hash1 = password_manager.hash_password(password)
        hash2 = password_manager.hash_password(password)
        
        assert hash1 != hash2
        # But both should verify correctly
        assert password_manager.verify_password(password, hash1) is True
        assert password_manager.verify_password(password, hash2) is True
    
    @pytest.mark.parametrize("password,expected_valid,expected_error", [
        ("TestPass123!", True, ""),
        ("short", False, "at least 8 characters"),
        ("nouppercase123!", False, "uppercase"),
        ("NOLOWERCASE123!", False, "lowercase"),
        ("NoNumbers!", False, "number"),
        ("NoSpecialChar123", False, "special character"),
        ("ValidP@ssw0rd", True, ""),
        ("Complex!Pass123", True, ""),
    ])
    def test_validate_password_strength(self, password, expected_valid, expected_error):
        """Test password strength validation"""
        is_valid, error_msg = password_manager.validate_password_strength(password)
        
        assert is_valid == expected_valid
        if not expected_valid:
            assert expected_error in error_msg.lower()


class TestJWTManager:
    """Test suite for JWT token management"""
    
    def setup_method(self):
        """Set up test JWT manager"""
        self.jwt_manager = JWTManager()
        self.test_user_id = str(uuid4())
        self.test_email = "test@example.com"
        self.test_tier = "free"
    
    def test_generate_jti(self):
        """Test JTI generation"""
        jti1 = self.jwt_manager.generate_jti()
        jti2 = self.jwt_manager.generate_jti()
        
        assert jti1 is not None
        assert jti2 is not None
        assert jti1 != jti2
        assert len(jti1) == 36  # UUID v4 format
    
    def test_create_access_token(self):
        """Test access token creation"""
        token, expires_at = self.jwt_manager.create_access_token(
            self.test_user_id,
            self.test_email,
            self.test_tier,
            additional_claims={"is_verified": True}
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 100
        assert expires_at > datetime.utcnow()
        
        # Decode and verify payload
        payload = pyjwt.decode(
            token,
            self.jwt_manager.secret_key,
            algorithms=[self.jwt_manager.algorithm]
        )
        
        assert payload["sub"] == self.test_user_id
        assert payload["email"] == self.test_email
        assert payload["subscription_tier"] == self.test_tier
        assert payload["type"] == "access"
        assert payload["is_verified"] is True
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        token, expires_at, family_id = self.jwt_manager.create_refresh_token(
            self.test_user_id,
            device_id="test-device"
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 100
        assert expires_at > datetime.utcnow()
        assert family_id is not None
        
        # Decode and verify payload
        payload = pyjwt.decode(
            token,
            self.jwt_manager.secret_key,
            algorithms=[self.jwt_manager.algorithm]
        )
        
        assert payload["sub"] == self.test_user_id
        assert payload["type"] == "refresh"
        assert payload["family_id"] == family_id
        assert payload["device_id"] == "test-device"
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload
    
    def test_refresh_token_family_rotation(self):
        """Test refresh token family ID for rotation"""
        token1, _, family_id1 = self.jwt_manager.create_refresh_token(
            self.test_user_id
        )
        
        # Create another token with same family
        token2, _, family_id2 = self.jwt_manager.create_refresh_token(
            self.test_user_id,
            family_id=family_id1
        )
        
        assert family_id1 == family_id2
        
        # Create token without family (new family)
        token3, _, family_id3 = self.jwt_manager.create_refresh_token(
            self.test_user_id
        )
        
        assert family_id3 != family_id1
    
    def test_decode_valid_token(self):
        """Test decoding valid token"""
        token, _ = self.jwt_manager.create_access_token(
            self.test_user_id,
            self.test_email,
            self.test_tier
        )
        
        payload = self.jwt_manager.decode_token(token)
        
        assert payload["sub"] == self.test_user_id
        assert payload["email"] == self.test_email
        assert payload["subscription_tier"] == self.test_tier
    
    def test_decode_expired_token(self):
        """Test decoding expired token"""
        # Create token that's already expired
        expired_time = datetime.utcnow() - timedelta(minutes=1)
        payload = {
            "sub": self.test_user_id,
            "exp": expired_time,
            "iat": datetime.utcnow()
        }
        
        expired_token = pyjwt.encode(
            payload,
            self.jwt_manager.secret_key,
            algorithm=self.jwt_manager.algorithm
        )
        
        with pytest.raises(Exception) as exc_info:
            self.jwt_manager.decode_token(expired_token)
        
        assert "expired" in str(exc_info.value).lower()
    
    def test_decode_token_without_exp_verification(self):
        """Test decoding token without expiration verification"""
        # Create expired token
        expired_time = datetime.utcnow() - timedelta(minutes=1)
        payload = {
            "sub": self.test_user_id,
            "exp": expired_time,
            "iat": datetime.utcnow()
        }
        
        expired_token = pyjwt.encode(
            payload,
            self.jwt_manager.secret_key,
            algorithm=self.jwt_manager.algorithm
        )
        
        # Should not raise exception when verify_exp=False
        decoded = self.jwt_manager.decode_token(expired_token, verify_exp=False)
        assert decoded["sub"] == self.test_user_id
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception) as exc_info:
            self.jwt_manager.decode_token(invalid_token)
        
        assert "invalid" in str(exc_info.value).lower()
    
    def test_decode_token_wrong_secret(self):
        """Test decoding token with wrong secret"""
        token, _ = self.jwt_manager.create_access_token(
            self.test_user_id,
            self.test_email,
            self.test_tier
        )
        
        # Try to decode with wrong secret
        wrong_manager = JWTManager()
        wrong_manager.secret_key = "wrong-secret"
        
        with pytest.raises(Exception) as exc_info:
            wrong_manager.decode_token(token)
        
        assert "invalid" in str(exc_info.value).lower()
    
    def test_verify_token_type_correct(self):
        """Test verifying correct token type"""
        token, _ = self.jwt_manager.create_access_token(
            self.test_user_id,
            self.test_email,
            self.test_tier
        )
        
        payload = self.jwt_manager.decode_token(token)
        
        # Should not raise exception
        self.jwt_manager.verify_token_type(payload, "access")
    
    def test_verify_token_type_incorrect(self):
        """Test verifying incorrect token type"""
        token, _ = self.jwt_manager.create_access_token(
            self.test_user_id,
            self.test_email,
            self.test_tier
        )
        
        payload = self.jwt_manager.decode_token(token)
        
        with pytest.raises(Exception) as exc_info:
            self.jwt_manager.verify_token_type(payload, "refresh")
        
        assert "invalid token type" in str(exc_info.value).lower()
    
    def test_extract_token_from_header(self):
        """Test extracting token from Authorization header"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        auth_header = f"Bearer {token}"
        
        extracted = self.jwt_manager.extract_token_from_header(auth_header)
        
        assert extracted == token
    
    def test_extract_token_missing_header(self):
        """Test extracting token from missing header"""
        with pytest.raises(Exception) as exc_info:
            self.jwt_manager.extract_token_from_header("")
        
        assert "missing" in str(exc_info.value).lower()
    
    def test_extract_token_invalid_format(self):
        """Test extracting token from invalid header format"""
        with pytest.raises(Exception) as exc_info:
            self.jwt_manager.extract_token_from_header("InvalidFormat token")
        
        assert "invalid" in str(exc_info.value).lower()


class TestSecurityUtils:
    """Test suite for security utilities"""
    
    def test_generate_secure_token(self):
        """Test secure token generation"""
        token1 = security_utils.generate_secure_token()
        token2 = security_utils.generate_secure_token()
        
        assert token1 is not None
        assert token2 is not None
        assert token1 != token2
        assert len(token1) == 64  # 32 bytes = 64 hex chars
        
        # Test custom length
        token3 = security_utils.generate_secure_token(16)
        assert len(token3) == 32  # 16 bytes = 32 hex chars
    
    def test_generate_verification_code(self):
        """Test verification code generation"""
        code1 = security_utils.generate_verification_code()
        code2 = security_utils.generate_verification_code()
        
        assert code1 is not None
        assert code2 is not None
        assert len(code1) == 6
        assert code1.isdigit()
        assert code1 != code2  # Should be random
        
        # Test custom length
        code3 = security_utils.generate_verification_code(8)
        assert len(code3) == 8
        assert code3.isdigit()
    
    def test_hash_email(self):
        """Test email hashing"""
        email = "test@example.com"
        hashed = security_utils.hash_email(email)
        
        assert hashed is not None
        assert len(hashed) == 64  # SHA-256 produces 64 hex chars
        assert hashed != email
        
        # Same email should produce same hash
        hashed2 = security_utils.hash_email(email)
        assert hashed == hashed2
        
        # Case insensitive
        hashed3 = security_utils.hash_email("TEST@EXAMPLE.COM")
        assert hashed == hashed3
    
    def test_constant_time_compare(self):
        """Test constant time string comparison"""
        # Equal strings
        assert security_utils.constant_time_compare("secret", "secret") is True
        
        # Different strings
        assert security_utils.constant_time_compare("secret", "different") is False
        
        # Edge cases
        assert security_utils.constant_time_compare("", "") is True
        assert security_utils.constant_time_compare("a", "a") is True
        assert security_utils.constant_time_compare("a", "b") is False
    
    @pytest.mark.parametrize("input_str,max_length,expected", [
        ("  test  ", 500, "test"),
        ("test\x00null", 500, "testnull"),
        ("very long string" * 100, 50, "very long stringvery long stringvery long stringv"),
        ("", 500, ""),
        (None, 500, ""),
        ("normal input", 500, "normal input"),
        ("  \n\t whitespace \n\t  ", 500, "whitespace"),
    ])
    def test_sanitize_user_input(self, input_str, max_length, expected):
        """Test user input sanitization"""
        result = security_utils.sanitize_user_input(input_str, max_length)
        assert result == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])