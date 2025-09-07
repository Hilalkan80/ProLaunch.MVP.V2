"""
Protected API Example

This module demonstrates how to use authentication middleware to protect API endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ..models.base import get_db
from ..models.user import User, SubscriptionTier
from ..core.dependencies import (
    get_current_user,
    get_current_active_user,
    get_verified_user,
    require_subscription_tier,
    require_milestone_access,
    get_rate_limiter,
    AuthUser
)


logger = logging.getLogger(__name__)

# Create router for protected endpoints
router = APIRouter(prefix="/api/v1/protected", tags=["Protected Examples"])


@router.get(
    "/profile",
    summary="Get current user profile",
    description="Get profile of the authenticated user"
)
async def get_profile(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get the profile of the currently authenticated user.
    
    This endpoint requires a valid JWT token.
    """
    return {
        "user": current_user.to_dict(),
        "message": "Profile retrieved successfully"
    }


@router.get(
    "/verified-only",
    summary="Verified users only",
    description="Endpoint that requires email verification"
)
async def verified_only_endpoint(
    current_user: User = Depends(get_verified_user)
) -> Dict[str, Any]:
    """
    Example endpoint that requires the user to have verified their email.
    """
    return {
        "message": "You have access because your email is verified",
        "user_email": current_user.email
    }


@router.get(
    "/premium-feature",
    summary="Premium feature",
    description="Endpoint that requires at least GROWTH subscription"
)
async def premium_feature(
    current_user: AuthUser = Depends(require_subscription_tier(SubscriptionTier.GROWTH))
) -> Dict[str, Any]:
    """
    Example endpoint that requires a GROWTH subscription or higher.
    """
    return {
        "message": "You have access to this premium feature",
        "subscription_tier": current_user.subscription_tier
    }


@router.get(
    "/milestone/{milestone_id}",
    summary="Access milestone",
    description="Check access to a specific milestone"
)
async def access_milestone(
    milestone_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Example endpoint for milestone access checking.
    
    - M0: Free for all users
    - M1: Requires STARTER subscription or higher
    - M2-M3: Requires GROWTH subscription or higher
    - M4: Requires SCALE subscription or higher
    """
    # Use the milestone access dependency
    milestone_access = require_milestone_access(milestone_id)
    
    try:
        # Check access
        await milestone_access(current_user)
        
        return {
            "message": f"You have access to milestone {milestone_id}",
            "milestone_id": milestone_id,
            "user_subscription": current_user.subscription_tier.value if current_user.subscription_tier else "free"
        }
    except HTTPException as e:
        raise e


@router.post(
    "/rate-limited",
    summary="Rate limited endpoint",
    description="Endpoint with rate limiting based on subscription tier"
)
async def rate_limited_endpoint(
    _: Any = Depends(get_rate_limiter),
    current_user: AuthUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Example endpoint with rate limiting.
    
    Rate limits by subscription tier:
    - FREE: 60 requests/minute
    - STARTER: 120 requests/minute
    - GROWTH: 300 requests/minute
    - SCALE: 600 requests/minute
    - ENTERPRISE: 1200 requests/minute
    """
    return {
        "message": "Request successful within rate limit",
        "user_tier": current_user.subscription_tier
    }


@router.put(
    "/update-profile",
    summary="Update user profile",
    description="Update authenticated user's profile information"
)
async def update_profile(
    profile_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Example endpoint for updating user profile.
    
    Demonstrates how to:
    - Get the authenticated user
    - Update user data in the database
    - Return updated information
    """
    # Update user fields (example)
    if "full_name" in profile_data:
        current_user.full_name = profile_data["full_name"]
    
    if "company_name" in profile_data:
        current_user.company_name = profile_data["company_name"]
    
    if "target_market" in profile_data:
        current_user.target_market = profile_data["target_market"]
    
    # Save to database
    await db.commit()
    await db.refresh(current_user)
    
    return {
        "message": "Profile updated successfully",
        "user": current_user.to_dict()
    }


@router.get(
    "/admin-only",
    summary="Admin only endpoint",
    description="Endpoint that requires ENTERPRISE subscription"
)
async def admin_only_endpoint(
    current_user: AuthUser = Depends(require_subscription_tier(SubscriptionTier.ENTERPRISE))
) -> Dict[str, Any]:
    """
    Example endpoint that requires the highest subscription tier.
    
    This could be used for admin features or advanced analytics.
    """
    return {
        "message": "Welcome to the admin area",
        "user_id": current_user.id,
        "subscription": current_user.subscription_tier
    }


@router.get(
    "/token-info",
    summary="Get token information",
    description="Debug endpoint to see JWT token contents"
)
async def get_token_info(
    current_user: AuthUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Debug endpoint that shows the contents of the JWT token.
    
    Useful for development and debugging authentication issues.
    """
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "subscription_tier": current_user.subscription_tier,
        "is_verified": current_user.is_verified,
        "full_name": current_user.full_name,
        "token_payload": current_user.token_payload
    }