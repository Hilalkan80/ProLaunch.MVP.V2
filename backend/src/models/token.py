"""
Token Models

This module defines models for token management including refresh tokens
and token blacklisting for security.
"""

from sqlalchemy import Column, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from .base import Base


class RefreshToken(Base):
    """
    Refresh token storage for JWT authentication.
    Tracks active refresh tokens with metadata for security auditing.
    """
    __tablename__ = "refresh_tokens"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Token data
    token = Column(String(500), unique=True, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Token metadata
    family_id = Column(String(100), index=True)  # For refresh token rotation
    device_id = Column(String(100))  # Track device/browser
    device_name = Column(String(255))  # Human-readable device name
    
    # Security tracking
    ip_address = Column(String(45))  # Support IPv6
    user_agent = Column(Text)
    
    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Usage tracking
    used_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    revoke_reason = Column(String(255))
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Composite indexes for performance
    __table_args__ = (
        Index('idx_refresh_tokens_user_expires', 'user_id', 'expires_at'),
        Index('idx_refresh_tokens_family', 'family_id', 'expires_at'),
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_revoked(self) -> bool:
        """Check if token has been revoked"""
        return self.revoked_at is not None
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)"""
        return not self.is_expired and not self.is_revoked


class TokenBlacklist(Base):
    """
    Blacklist for invalidated JWT tokens.
    Used to immediately invalidate tokens before their natural expiration.
    """
    __tablename__ = "token_blacklist"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Token identification
    jti = Column(String(100), unique=True, nullable=False, index=True)  # JWT ID
    token_type = Column(String(20), nullable=False)  # 'access' or 'refresh'
    
    # Metadata
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Blacklist reason
    reason = Column(String(255), nullable=False)
    blacklisted_by = Column(UUID(as_uuid=True))  # Admin who blacklisted
    
    # Timestamps
    blacklisted_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Index for cleanup of expired entries
    __table_args__ = (
        Index('idx_blacklist_expires', 'expires_at'),
    )
    
    @property
    def can_be_cleaned(self) -> bool:
        """Check if entry can be removed (token would be naturally expired)"""
        return datetime.utcnow() > self.expires_at