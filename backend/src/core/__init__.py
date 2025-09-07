"""
Core Module

This module contains core utilities, security, and dependencies.
"""

from .security import password_manager, jwt_manager, security_utils
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_verified_user,
    require_subscription_tier,
    require_milestone_access,
    get_rate_limiter,
    AuthUser
)
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    RateLimitExceededError
)

__all__ = [
    'password_manager',
    'jwt_manager',
    'security_utils',
    'get_current_user',
    'get_current_active_user',
    'get_verified_user',
    'require_subscription_tier',
    'require_milestone_access',
    'get_rate_limiter',
    'AuthUser',
    'AuthenticationError',
    'AuthorizationError',
    'ValidationError',
    'RateLimitExceededError'
]