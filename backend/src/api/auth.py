"""
Authentication API Endpoints

This module provides RESTful API endpoints for user authentication including
registration, login, token refresh, and logout operations.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ..models.base import get_db
from ..services.auth_service import auth_service
from ..core.security import jwt_manager


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Security scheme for Swagger UI
security = HTTPBearer()


# Request/Response Models

class UserRegistrationRequest(BaseModel):
    """User registration request model"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    business_idea: str = Field(..., min_length=10, max_length=500)
    target_market: Optional[str] = Field(None, max_length=500)
    experience_level: Optional[str] = Field(
        "first-time",
        regex="^(first-time|some-experience|experienced)$"
    )
    full_name: Optional[str] = Field(None, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    
    @validator('email')
    def email_to_lower(cls, v):
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLoginRequest(BaseModel):
    """User login request model"""
    email: EmailStr
    password: str
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    
    @validator('email')
    def email_to_lower(cls, v):
        return v.lower()


class TokenRefreshRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_profile: Dict[str, Any]


class UserProfileResponse(BaseModel):
    """User profile response model"""
    user_id: str
    email: str
    full_name: Optional[str]
    company_name: Optional[str]
    business_idea: str
    target_market: Optional[str]
    experience_level: str
    subscription_tier: str
    is_verified: bool
    created_at: str


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    detail: Optional[str] = None


# Helper Functions

def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check for proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


def get_device_info(request: Request, body: Optional[UserLoginRequest] = None) -> Dict[str, str]:
    """Extract device information from request"""
    user_agent = request.headers.get("User-Agent", "unknown")
    
    device_info = {
        "user_agent": user_agent
    }
    
    if body:
        if body.device_id:
            device_info["device_id"] = body.device_id
        if body.device_name:
            device_info["device_name"] = body.device_name
    
    return device_info


# API Endpoints

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account and receive authentication tokens"
)
async def register(
    request: Request,
    body: UserRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    
    Returns:
        - **access_token**: JWT access token for API requests
        - **refresh_token**: JWT refresh token for token renewal
        - **expires_in**: Access token expiration time in seconds
        - **user_profile**: Basic user profile information
    """
    try:
        user, tokens = await auth_service.register_user(
            db,
            email=body.email,
            password=body.password,
            business_idea=body.business_idea,
            target_market=body.target_market,
            experience_level=body.experience_level,
            full_name=body.full_name,
            company_name=body.company_name
        )
        
        # Log registration for monitoring
        logger.info(f"User registered successfully: {body.email}")
        
        return TokenResponse(**tokens)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate user and receive tokens"
)
async def login(
    request: Request,
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user with email and password.
    
    Returns:
        - **access_token**: JWT access token for API requests
        - **refresh_token**: JWT refresh token for token renewal
        - **expires_in**: Access token expiration time in seconds
        - **user_profile**: Basic user profile information
    """
    try:
        client_ip = get_client_ip(request)
        device_info = get_device_info(request, body)
        
        user, tokens = await auth_service.login(
            db,
            email=body.email,
            password=body.password,
            device_info=device_info,
            ip_address=client_ip
        )
        
        # Set secure cookie for web clients (optional)
        # response.set_cookie(
        #     key="refresh_token",
        #     value=tokens["refresh_token"],
        #     httponly=True,
        #     secure=True,
        #     samesite="strict",
        #     max_age=7 * 24 * 60 * 60  # 7 days
        # )
        
        logger.info(f"User logged in: {body.email} from {client_ip}")
        
        return TokenResponse(**tokens)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token"
)
async def refresh_token(
    request: Request,
    body: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.
    
    This endpoint implements token rotation for enhanced security.
    The old refresh token is invalidated and a new one is issued.
    
    Returns:
        - **access_token**: New JWT access token
        - **refresh_token**: New JWT refresh token (rotation)
        - **expires_in**: Access token expiration time in seconds
        - **user_profile**: Basic user profile information
    """
    try:
        client_ip = get_client_ip(request)
        
        tokens = await auth_service.refresh_tokens(
            db,
            refresh_token=body.refresh_token,
            ip_address=client_ip
        )
        
        logger.info("Token refreshed successfully")
        
        return TokenResponse(**tokens)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed. Please login again."
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Invalidate current tokens and end session"
)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    refresh_token: Optional[str] = Header(None, alias="X-Refresh-Token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user and invalidate tokens.
    
    Requires valid access token in Authorization header.
    Optionally accepts refresh token to revoke.
    """
    try:
        access_token = credentials.credentials
        
        await auth_service.logout(
            db,
            access_token=access_token,
            refresh_token=refresh_token
        )
        
        logger.info("User logged out successfully")
        
        return MessageResponse(
            message="Logged out successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Logout from all devices",
    description="Invalidate all tokens and sessions for user"
)
async def logout_all_devices(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user from all devices by revoking all refresh tokens.
    
    Requires valid access token in Authorization header.
    """
    try:
        access_token = credentials.credentials
        
        # Decode token to get user ID
        payload = jwt_manager.decode_token(access_token)
        user_id = payload.get("sub")
        
        await auth_service.logout_all_devices(db, user_id)
        
        logger.info(f"User {user_id} logged out from all devices")
        
        return MessageResponse(
            message="Logged out from all devices successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout all devices error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get(
    "/verify",
    response_model=UserProfileResponse,
    summary="Verify access token",
    description="Verify current access token and get user profile"
)
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Verify access token and return user profile.
    
    Useful for checking if token is still valid and getting user info.
    """
    try:
        access_token = credentials.credentials
        
        payload = await auth_service.verify_access_token(access_token)
        
        return UserProfileResponse(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            full_name=payload.get("full_name"),
            company_name=None,  # Would need to fetch from DB
            business_idea="",  # Would need to fetch from DB
            target_market="",  # Would need to fetch from DB
            experience_level="first-time",  # Would need to fetch from DB
            subscription_tier=payload.get("subscription_tier", "free"),
            is_verified=payload.get("is_verified", False),
            created_at=payload.get("iat", "")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token verification failed"
        )


@router.post(
    "/request-password-reset",
    response_model=MessageResponse,
    summary="Request password reset",
    description="Send password reset email to user"
)
async def request_password_reset(
    email: EmailStr,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset email.
    
    Always returns success for security (doesn't reveal if email exists).
    """
    # TODO: Implement password reset email functionality
    # This would involve:
    # 1. Generate reset token
    # 2. Store in database with expiration
    # 3. Send email with reset link
    
    logger.info(f"Password reset requested for: {email}")
    
    return MessageResponse(
        message="If the email exists, a password reset link has been sent"
    )


@router.get(
    "/health",
    response_model=MessageResponse,
    summary="Auth service health check",
    description="Check if authentication service is running"
)
async def health_check():
    """
    Health check endpoint for authentication service.
    """
    return MessageResponse(
        message="Authentication service is healthy"
    )