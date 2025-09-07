"""
Authentication Service

This module provides comprehensive authentication services including user registration,
login, token refresh, and session management using PostgreSQL and Redis.
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from fastapi import HTTPException, status
import logging
import json
from uuid import UUID

# Use conditional imports to handle both module and script execution
try:
    # Try relative imports first (when used as a module)
    from ..models.user import User, SubscriptionTier, ExperienceLevel
    from ..models.token import RefreshToken, TokenBlacklist
    from ..models.base import get_db_context
    from ..core.security import password_manager, jwt_manager, security_utils
    from ..infrastructure.redis.redis_mcp import redis_mcp_client
except ImportError:
    # Fall back to absolute imports (when testing)
    from models.user import User, SubscriptionTier, ExperienceLevel
    from models.token import RefreshToken, TokenBlacklist
    from models.base import get_db_context
    from core.security import password_manager, jwt_manager, security_utils
    from infrastructure.redis.redis_mcp import redis_mcp_client


logger = logging.getLogger(__name__)


class AuthenticationService:
    """
    Comprehensive authentication service handling all auth operations.
    """
    
    def __init__(self):
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 30
        self.session_timeout_minutes = 30
    
    async def register_user(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        business_idea: str,
        target_market: Optional[str] = None,
        experience_level: Optional[str] = None,
        full_name: Optional[str] = None,
        company_name: Optional[str] = None
    ) -> Tuple[User, Dict[str, Any]]:
        """
        Register a new user with comprehensive validation.
        
        Args:
            db: Database session
            email: User's email
            password: User's password
            business_idea: User's business idea
            target_market: Target market description
            experience_level: User's experience level
            full_name: User's full name
            company_name: Company name
            
        Returns:
            Tuple of (user, tokens)
            
        Raises:
            HTTPException: If registration fails
        """
        # Validate email format
        email = email.lower().strip()
        if not self._validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Check if user already exists
        existing_user = await self._get_user_by_email(db, email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        
        # Validate password strength
        is_valid, error_msg = password_manager.validate_password_strength(password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Validate and convert experience level
        exp_level = ExperienceLevel.FIRST_TIME
        if experience_level:
            try:
                exp_level = ExperienceLevel(experience_level)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid experience level"
                )
        
        # Create new user
        user = User(
            email=email,
            password_hash=password_manager.hash_password(password),
            business_idea=security_utils.sanitize_user_input(business_idea, 500),
            target_market=security_utils.sanitize_user_input(target_market, 500) if target_market else None,
            experience_level=exp_level,
            full_name=security_utils.sanitize_user_input(full_name, 255) if full_name else None,
            company_name=security_utils.sanitize_user_input(company_name, 255) if company_name else None,
            subscription_tier=SubscriptionTier.FREE,
            is_active=True,
            is_verified=False,
            login_count=0,
            failed_login_attempts=0
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Generate tokens
        tokens = await self._generate_auth_tokens(db, user)
        
        # Store session in Redis
        await self._store_session(user, tokens)
        
        # Log registration event
        logger.info(f"New user registered: {email}")
        
        return user, tokens
    
    async def login(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        device_info: Optional[Dict[str, str]] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[User, Dict[str, Any]]:
        """
        Authenticate user and generate tokens.
        
        Args:
            db: Database session
            email: User's email
            password: User's password
            device_info: Device information for tracking
            ip_address: Client IP address
            
        Returns:
            Tuple of (user, tokens)
            
        Raises:
            HTTPException: If authentication fails
        """
        email = email.lower().strip()
        
        # Get user
        user = await self._get_user_by_email(db, email)
        if not user:
            # Don't reveal whether email exists
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is locked
        if user.locked_until and datetime.utcnow() < user.locked_until:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked until {user.locked_until.isoformat()}"
            )
        
        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Verify password
        if not password_manager.verify_password(password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account if too many failed attempts
            if user.failed_login_attempts >= self.max_failed_attempts:
                user.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)
                await db.commit()
                
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Account locked due to too many failed attempts"
                )
            
            await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Reset failed attempts and unlock
        user.failed_login_attempts = 0
        user.locked_until = None
        
        # Update login tracking
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        user.login_count += 1
        
        await db.commit()
        await db.refresh(user)
        
        # Generate tokens
        tokens = await self._generate_auth_tokens(
            db,
            user,
            device_id=device_info.get('device_id') if device_info else None,
            device_name=device_info.get('device_name') if device_info else None,
            user_agent=device_info.get('user_agent') if device_info else None,
            ip_address=ip_address
        )
        
        # Store session in Redis
        await self._store_session(user, tokens)
        
        # Log login event
        logger.info(f"User logged in: {email}")
        
        return user, tokens
    
    async def refresh_tokens(
        self,
        db: AsyncSession,
        refresh_token: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token with rotation.
        
        Args:
            db: Database session
            refresh_token: Current refresh token
            ip_address: Client IP address
            
        Returns:
            New tokens dictionary
            
        Raises:
            HTTPException: If refresh fails
        """
        # Decode refresh token
        payload = jwt_manager.decode_token(refresh_token)
        jwt_manager.verify_token_type(payload, "refresh")
        
        user_id = payload.get("sub")
        family_id = payload.get("family_id")
        jti = payload.get("jti")
        
        # Check if token is blacklisted
        if await self._is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        # Get refresh token from database
        stmt = select(RefreshToken).where(
            and_(
                RefreshToken.token == refresh_token,
                RefreshToken.user_id == UUID(user_id)
            )
        )
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()
        
        if not db_token:
            # Token doesn't exist - possible theft attempt
            await self._revoke_token_family(db, family_id, "Token reuse detected")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token - all tokens revoked for security"
            )
        
        # Check if token is valid
        if not db_token.is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or expired"
            )
        
        # Check for token reuse (already used)
        if db_token.used_at:
            # Token reuse detected - revoke entire family
            await self._revoke_token_family(db, family_id, "Token reuse detected")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token reuse detected - all tokens revoked for security"
            )
        
        # Mark token as used
        db_token.used_at = datetime.utcnow()
        
        # Get user
        stmt = select(User).where(User.id == UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new tokens with same family ID for rotation
        tokens = await self._generate_auth_tokens(
            db,
            user,
            family_id=family_id,
            device_id=payload.get("device_id"),
            ip_address=ip_address
        )
        
        await db.commit()
        
        # Update session in Redis
        await self._store_session(user, tokens)
        
        return tokens
    
    async def logout(
        self,
        db: AsyncSession,
        access_token: str,
        refresh_token: Optional[str] = None
    ) -> None:
        """
        Logout user and invalidate tokens.
        
        Args:
            db: Database session
            access_token: Current access token
            refresh_token: Optional refresh token to revoke
        """
        # Decode access token
        payload = jwt_manager.decode_token(access_token, verify_exp=False)
        user_id = payload.get("sub")
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        # Blacklist access token
        blacklist_entry = TokenBlacklist(
            jti=jti,
            token_type="access",
            user_id=UUID(user_id),
            expires_at=datetime.fromtimestamp(exp),
            reason="User logout"
        )
        db.add(blacklist_entry)
        
        # Revoke refresh token if provided
        if refresh_token:
            refresh_payload = jwt_manager.decode_token(refresh_token, verify_exp=False)
            refresh_jti = refresh_payload.get("jti")
            family_id = refresh_payload.get("family_id")
            
            # Revoke the specific refresh token
            stmt = update(RefreshToken).where(
                RefreshToken.token == refresh_token
            ).values(
                revoked_at=datetime.utcnow(),
                revoke_reason="User logout"
            )
            await db.execute(stmt)
            
            # Blacklist refresh token
            refresh_blacklist = TokenBlacklist(
                jti=refresh_jti,
                token_type="refresh",
                user_id=UUID(user_id),
                expires_at=datetime.fromtimestamp(refresh_payload.get("exp")),
                reason="User logout"
            )
            db.add(refresh_blacklist)
        
        await db.commit()
        
        # Clear Redis session
        await self._clear_session(user_id)
        
        logger.info(f"User logged out: {user_id}")
    
    async def logout_all_devices(
        self,
        db: AsyncSession,
        user_id: str
    ) -> None:
        """
        Logout user from all devices by revoking all refresh tokens.
        
        Args:
            db: Database session
            user_id: User ID
        """
        # Revoke all refresh tokens for user
        stmt = update(RefreshToken).where(
            and_(
                RefreshToken.user_id == UUID(user_id),
                RefreshToken.revoked_at.is_(None)
            )
        ).values(
            revoked_at=datetime.utcnow(),
            revoke_reason="Logout from all devices"
        )
        await db.execute(stmt)
        await db.commit()
        
        # Clear all Redis sessions
        await self._clear_all_sessions(user_id)
        
        logger.info(f"User logged out from all devices: {user_id}")
    
    async def verify_access_token(
        self,
        token: str,
        required_tier: Optional[SubscriptionTier] = None
    ) -> Dict[str, Any]:
        """
        Verify access token and check permissions.
        
        Args:
            token: Access token to verify
            required_tier: Optional required subscription tier
            
        Returns:
            Token payload if valid
            
        Raises:
            HTTPException: If token is invalid or insufficient permissions
        """
        # Decode token
        payload = jwt_manager.decode_token(token)
        jwt_manager.verify_token_type(payload, "access")
        
        # Check if token is blacklisted
        jti = payload.get("jti")
        if await self._is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        # Check session in Redis
        user_id = payload.get("sub")
        if not await self._verify_session(user_id, jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalid or expired"
            )
        
        # Check subscription tier if required
        if required_tier:
            user_tier = payload.get("subscription_tier")
            if not self._check_tier_access(user_tier, required_tier):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Subscription tier {required_tier.value} or higher required"
                )
        
        return payload
    
    # Private helper methods
    
    async def _get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _generate_auth_tokens(
        self,
        db: AsyncSession,
        user: User,
        family_id: Optional[str] = None,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate access and refresh tokens"""
        # Create access token
        access_token, access_expires = jwt_manager.create_access_token(
            str(user.id),
            user.email,
            user.subscription_tier.value if user.subscription_tier else "free",
            additional_claims={
                "is_verified": user.is_verified,
                "full_name": user.full_name
            }
        )
        
        # Create refresh token
        refresh_token, refresh_expires, family_id = jwt_manager.create_refresh_token(
            str(user.id),
            family_id=family_id,
            device_id=device_id
        )
        
        # Store refresh token in database
        db_refresh_token = RefreshToken(
            token=refresh_token,
            user_id=user.id,
            family_id=family_id,
            device_id=device_id,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=refresh_expires
        )
        db.add(db_refresh_token)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": jwt_manager.access_token_expire_minutes * 60,
            "user_profile": user.to_profile()
        }
    
    async def _revoke_token_family(
        self,
        db: AsyncSession,
        family_id: str,
        reason: str
    ) -> None:
        """Revoke all tokens in a family (for rotation security)"""
        stmt = update(RefreshToken).where(
            and_(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None)
            )
        ).values(
            revoked_at=datetime.utcnow(),
            revoke_reason=reason
        )
        await db.execute(stmt)
    
    async def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token JTI is blacklisted in Redis"""
        key = f"blacklist:{jti}"
        return await redis_mcp_client.exists(key)
    
    async def _store_session(self, user: User, tokens: Dict[str, Any]) -> None:
        """Store user session in Redis"""
        session_key = f"session:{user.id}"
        session_data = {
            "user_id": str(user.id),
            "email": user.email,
            "access_token_jti": jwt_manager.decode_token(tokens["access_token"], verify_exp=False)["jti"],
            "created_at": datetime.utcnow().isoformat(),
            "subscription_tier": user.subscription_tier.value if user.subscription_tier else "free"
        }
        
        await redis_mcp_client.set(
            session_key,
            json.dumps(session_data),
            ttl=self.session_timeout_minutes * 60
        )
    
    async def _verify_session(self, user_id: str, jti: str) -> bool:
        """Verify session exists and is valid"""
        session_key = f"session:{user_id}"
        session_data = await redis_mcp_client.get(session_key)
        
        if not session_data:
            return False
        
        try:
            session = json.loads(session_data)
            return session.get("access_token_jti") == jti
        except json.JSONDecodeError:
            return False
    
    async def _clear_session(self, user_id: str) -> None:
        """Clear user session from Redis"""
        session_key = f"session:{user_id}"
        await redis_mcp_client.delete(session_key)
    
    async def _clear_all_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user"""
        # In production, you might want to track multiple sessions
        # For now, we clear the main session
        await self._clear_session(user_id)
    
    def _validate_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _check_tier_access(self, user_tier: str, required_tier: SubscriptionTier) -> bool:
        """Check if user tier has access to required tier"""
        tier_hierarchy = {
            "free": 0,
            "starter": 1,
            "growth": 2,
            "scale": 3,
            "enterprise": 4
        }
        
        user_level = tier_hierarchy.get(user_tier, 0)
        required_level = tier_hierarchy.get(required_tier.value, 0)
        
        return user_level >= required_level


# Singleton service instance
auth_service = AuthenticationService()