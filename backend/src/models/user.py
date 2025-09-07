"""
User Model

This module defines the User model with comprehensive fields for authentication
and profile management.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, Text, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum
from .base import Base


class SubscriptionTier(enum.Enum):
    """User subscription tiers"""
    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"
    SCALE = "scale"
    ENTERPRISE = "enterprise"


class ExperienceLevel(enum.Enum):
    """User experience levels"""
    FIRST_TIME = "first-time"
    SOME_EXPERIENCE = "some-experience"
    EXPERIENCED = "experienced"


class User(Base):
    """
    User model for authentication and profile management.
    Stores core user data with security and business fields.
    """
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile fields
    full_name = Column(String(255))
    phone_number = Column(String(50))
    company_name = Column(String(255))
    
    # Business fields
    business_idea = Column(Text, nullable=False)
    target_market = Column(String(500))
    experience_level = Column(
        SQLEnum(ExperienceLevel),
        default=ExperienceLevel.FIRST_TIME,
        nullable=False
    )
    
    # Subscription fields
    subscription_tier = Column(
        SQLEnum(SubscriptionTier),
        default=SubscriptionTier.FREE,
        nullable=False,
        index=True
    )
    subscription_expires_at = Column(DateTime(timezone=True))
    stripe_customer_id = Column(String(255), unique=True)
    
    # Security fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True))
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255))
    
    # Login tracking
    last_login_at = Column(DateTime(timezone=True))
    last_login_ip = Column(String(45))  # Support IPv6
    login_count = Column(Integer, default=0, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True))
    
    # Password reset
    password_reset_token = Column(String(255))
    password_reset_expires_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    milestones = relationship(
        "UserMilestone",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    chat_participations = relationship(
        "ChatRoomParticipant",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    chat_messages = relationship(
        "ChatMessage",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_subscription', 'subscription_tier', 'subscription_expires_at'),
        Index('idx_users_created_at', 'created_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert user to dictionary for API responses"""
        return {
            'id': str(self.id),
            'email': self.email,
            'full_name': self.full_name,
            'company_name': self.company_name,
            'business_idea': self.business_idea,
            'target_market': self.target_market,
            'experience_level': self.experience_level.value if self.experience_level else None,
            'subscription_tier': self.subscription_tier.value if self.subscription_tier else None,
            'is_verified': self.is_verified,
            'mfa_enabled': self.mfa_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def to_profile(self) -> dict:
        """Convert user to profile dictionary for JWT tokens"""
        return {
            'user_id': str(self.id),
            'email': self.email,
            'full_name': self.full_name,
            'subscription_tier': self.subscription_tier.value if self.subscription_tier else None,
            'is_verified': self.is_verified,
        }


class UserProfile(Base):
    """
    Extended user profile information.
    Stores additional user data that doesn't belong in the main user table.
    """
    __tablename__ = "user_profiles"
    
    # Primary key and foreign key to users
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    
    # Additional profile information
    bio = Column(Text)
    avatar_url = Column(String(500))
    timezone = Column(String(50), default='UTC')
    locale = Column(String(10), default='en-US')
    
    # Preferences
    notification_preferences = Column(Text)  # JSON string
    theme_preference = Column(String(20), default='light')
    
    # Business details
    industry = Column(String(100))
    business_stage = Column(String(100))
    funding_status = Column(String(100))
    team_size = Column(Integer)
    
    # Social links
    linkedin_url = Column(String(500))
    twitter_url = Column(String(500))
    website_url = Column(String(500))
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )