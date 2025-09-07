"""
Security Module

This module provides comprehensive security utilities including password hashing,
JWT token management, and security validation.
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
import secrets
import uuid
import hashlib
import hmac
from fastapi import HTTPException, status
import os


# Password hashing configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # High cost factor for security
)


class PasswordManager:
    """
    Manages password hashing and verification with security best practices.
    """
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt with salt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password meets security requirements.
        
        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        - At least one special character
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
        
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
        
        return True, ""


class JWTManager:
    """
    Manages JWT token generation, validation, and refresh operations.
    """
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    def generate_jti(self) -> str:
        """Generate a unique JWT ID"""
        return str(uuid.uuid4())
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        subscription_tier: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, datetime]:
        """
        Create a JWT access token.
        
        Args:
            user_id: User's UUID
            email: User's email
            subscription_tier: User's subscription tier
            additional_claims: Optional additional claims to include
            
        Returns:
            Tuple of (token, expiration_time)
        """
        expires_at = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "subscription_tier": subscription_tier,
            "type": "access",
            "jti": self.generate_jti(),  # Unique token ID for blacklisting
            "iat": datetime.utcnow(),
            "exp": expires_at,
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires_at
    
    def create_refresh_token(
        self,
        user_id: str,
        family_id: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Tuple[str, datetime, str]:
        """
        Create a JWT refresh token with rotation support.
        
        Args:
            user_id: User's UUID
            family_id: Token family ID for rotation tracking
            device_id: Device identifier
            
        Returns:
            Tuple of (token, expiration_time, family_id)
        """
        expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        family_id = family_id or str(uuid.uuid4())
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "family_id": family_id,
            "device_id": device_id,
            "jti": self.generate_jti(),
            "iat": datetime.utcnow(),
            "exp": expires_at,
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires_at, family_id
    
    def decode_token(self, token: str, verify_exp: bool = True) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token to decode
            verify_exp: Whether to verify expiration
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": verify_exp}
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def verify_token_type(self, payload: Dict[str, Any], expected_type: str) -> None:
        """
        Verify token is of expected type.
        
        Args:
            payload: Decoded token payload
            expected_type: Expected token type ('access' or 'refresh')
            
        Raises:
            HTTPException: If token type doesn't match
        """
        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {expected_type}"
            )
    
    def extract_token_from_header(self, authorization: str) -> str:
        """
        Extract token from Authorization header.
        
        Args:
            authorization: Authorization header value
            
        Returns:
            Extracted token
            
        Raises:
            HTTPException: If header format is invalid
        """
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing"
            )
        
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        return parts[1]


class SecurityUtils:
    """
    Additional security utilities for various operations.
    """
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.
        
        Args:
            length: Length of the token in bytes
            
        Returns:
            Hex string token
        """
        return secrets.token_hex(length)
    
    @staticmethod
    def generate_verification_code(length: int = 6) -> str:
        """
        Generate a numeric verification code.
        
        Args:
            length: Length of the code
            
        Returns:
            Numeric string code
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    @staticmethod
    def hash_email(email: str) -> str:
        """
        Hash an email for privacy-preserving storage.
        
        Args:
            email: Email to hash
            
        Returns:
            SHA-256 hash of the email
        """
        return hashlib.sha256(email.lower().encode()).hexdigest()
    
    @staticmethod
    def constant_time_compare(val1: str, val2: str) -> bool:
        """
        Perform constant-time string comparison to prevent timing attacks.
        
        Args:
            val1: First value
            val2: Second value
            
        Returns:
            True if values match
        """
        return hmac.compare_digest(val1, val2)
    
    @staticmethod
    def sanitize_user_input(input_str: str, max_length: int = 500) -> str:
        """
        Sanitize user input to prevent injection attacks.
        
        Args:
            input_str: Input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not input_str:
            return ""
        
        # Truncate to max length
        input_str = input_str[:max_length]
        
        # Remove null bytes
        input_str = input_str.replace('\x00', '')
        
        # Strip leading/trailing whitespace
        input_str = input_str.strip()
        
        return input_str


# Singleton instances
password_manager = PasswordManager()
jwt_manager = JWTManager()
security_utils = SecurityUtils()