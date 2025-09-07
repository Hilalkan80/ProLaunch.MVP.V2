"""
Authentication Dependencies

This module provides FastAPI dependencies for authentication and authorization,
including middleware for protecting routes and checking permissions.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from ..models.base import get_db
from ..models.user import User, SubscriptionTier
from ..services.auth_service import auth_service
from ..core.security import jwt_manager


logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class AuthUser:
    """
    Container for authenticated user information.
    Used as dependency injection result.
    """
    
    def __init__(self, user_id: str, email: str, subscription_tier: str, payload: Dict[str, Any]):
        self.id = user_id
        self.email = email
        self.subscription_tier = subscription_tier
        self.is_verified = payload.get("is_verified", False)
        self.full_name = payload.get("full_name")
        self.token_payload = payload
    
    def has_tier(self, required_tier: SubscriptionTier) -> bool:
        """Check if user has required subscription tier or higher"""
        tier_hierarchy = {
            "free": 0,
            "starter": 1,
            "growth": 2,
            "scale": 3,
            "enterprise": 4
        }
        
        user_level = tier_hierarchy.get(self.subscription_tier, 0)
        required_level = tier_hierarchy.get(required_tier.value, 0)
        
        return user_level >= required_level
    
    def __str__(self):
        return f"AuthUser(id={self.id}, email={self.email}, tier={self.subscription_tier})"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthUser:
    """
    Get current authenticated user from JWT token.
    
    This is the main authentication dependency for protected routes.
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        AuthUser object with user information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        token = credentials.credentials
        
        # Verify token and get payload
        payload = await auth_service.verify_access_token(token)
        
        # Create AuthUser object
        return AuthUser(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            subscription_tier=payload.get("subscription_tier", "free"),
            payload=payload
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from database and verify they are active.
    
    This dependency fetches the full user object from database
    and ensures the account is active.
    
    Args:
        current_user: Authenticated user from token
        db: Database session
        
    Returns:
        User model instance
        
    Raises:
        HTTPException: If user not found or inactive
    """
    # Get user from database
    stmt = select(User).where(User.id == current_user.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    if user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account has been deleted"
        )
    
    return user


async def get_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Ensure user has verified their email.
    
    Args:
        current_user: Active user from database
        
    Returns:
        Verified user
        
    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email."
        )
    
    return current_user


def require_subscription_tier(minimum_tier: SubscriptionTier):
    """
    Factory function to create a dependency that requires a minimum subscription tier.
    
    Usage:
        @router.get("/premium-feature")
        async def premium_feature(
            user: User = Depends(require_subscription_tier(SubscriptionTier.GROWTH))
        ):
            # This route requires at least GROWTH tier
            pass
    
    Args:
        minimum_tier: Minimum required subscription tier
        
    Returns:
        Dependency function
    """
    async def tier_checker(
        current_user: AuthUser = Depends(get_current_user)
    ) -> AuthUser:
        if not current_user.has_tier(minimum_tier):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires {minimum_tier.value} subscription or higher"
            )
        return current_user
    
    return tier_checker


def require_milestone_access(milestone_id: str):
    """
    Factory function to create a dependency that checks milestone access.
    
    Usage:
        @router.post("/milestone/{milestone_id}/complete")
        async def complete_milestone(
            milestone_id: str,
            user: User = Depends(require_milestone_access("M1"))
        ):
            # This route requires access to milestone M1
            pass
    
    Args:
        milestone_id: Milestone identifier (M0, M1, etc.)
        
    Returns:
        Dependency function
    """
    async def milestone_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # M0 is free for everyone
        if milestone_id == "M0":
            return current_user
        
        # Other milestones require paid subscription
        milestone_tiers = {
            "M1": SubscriptionTier.STARTER,
            "M2": SubscriptionTier.GROWTH,
            "M3": SubscriptionTier.GROWTH,
            "M4": SubscriptionTier.SCALE,
        }
        
        required_tier = milestone_tiers.get(milestone_id)
        if not required_tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown milestone: {milestone_id}"
            )
        
        user_tier = current_user.subscription_tier
        if not user_tier:
            user_tier = SubscriptionTier.FREE
        
        tier_hierarchy = {
            SubscriptionTier.FREE: 0,
            SubscriptionTier.STARTER: 1,
            SubscriptionTier.GROWTH: 2,
            SubscriptionTier.SCALE: 3,
            SubscriptionTier.ENTERPRISE: 4
        }
        
        user_level = tier_hierarchy.get(user_tier, 0)
        required_level = tier_hierarchy.get(required_tier, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Milestone {milestone_id} requires {required_tier.value} subscription or higher"
            )
        
        return current_user
    
    return milestone_checker


class RateLimiter:
    """
    Rate limiting dependency for API endpoints.
    Uses Redis for distributed rate limiting.
    """
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
    
    async def __call__(
        self,
        current_user: AuthUser = Depends(get_current_user)
    ):
        """
        Check and update rate limit for user.
        
        Args:
            current_user: Authenticated user
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        from ..infrastructure.redis.redis_mcp import redis_mcp_client
        
        # Rate limit key
        key = f"rate_limit:{current_user.id}"
        
        # Get current count
        count = await redis_mcp_client.get(key)
        
        if count:
            count = int(count)
            if count >= self.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute."
                )
            
            # Increment counter
            await redis_mcp_client.increment(key)
        else:
            # Set initial counter with 60 second expiry
            await redis_mcp_client.set(key, "1", ttl=60)
        
        return current_user


# Pre-configured rate limiters for different tiers
rate_limit_free = RateLimiter(requests_per_minute=60)
rate_limit_starter = RateLimiter(requests_per_minute=120)
rate_limit_growth = RateLimiter(requests_per_minute=300)
rate_limit_scale = RateLimiter(requests_per_minute=600)
rate_limit_enterprise = RateLimiter(requests_per_minute=1200)


async def get_rate_limiter(
    current_user: AuthUser = Depends(get_current_user)
) -> RateLimiter:
    """
    Get appropriate rate limiter based on user's subscription tier.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        RateLimiter instance for user's tier
    """
    tier_limiters = {
        "free": rate_limit_free,
        "starter": rate_limit_starter,
        "growth": rate_limit_growth,
        "scale": rate_limit_scale,
        "enterprise": rate_limit_enterprise
    }
    
    limiter = tier_limiters.get(current_user.subscription_tier, rate_limit_free)
    
    # Apply the rate limit check
    await limiter(current_user)
    
    return limiter


# Optional user dependency (for endpoints that work with or without auth)
async def get_optional_user(
    authorization: Optional[str] = None
) -> Optional[AuthUser]:
    """
    Get current user if authenticated, otherwise return None.
    
    Useful for endpoints that have different behavior for authenticated users.
    
    Args:
        authorization: Optional Authorization header
        
    Returns:
        AuthUser if authenticated, None otherwise
    """
    if not authorization:
        return None
    
    try:
        # Extract token from header
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        token = parts[1]
        
        # Verify token
        payload = await auth_service.verify_access_token(token)
        
        return AuthUser(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            subscription_tier=payload.get("subscription_tier", "free"),
            payload=payload
        )
    
    except Exception:
        # If token is invalid, return None instead of raising
        return None