"""
Enhanced Authentication Security Module

Implements advanced authentication security features including
account lockout, session management, and secure password reset.
"""

from typing import Dict, Optional, Tuple, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import secrets
import hashlib
import hmac
import pyotp
import base64
from fastapi import HTTPException, status, Request
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AccountStatus(Enum):
    """Account status enumeration."""
    ACTIVE = "active"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    DISABLED = "disabled"


class LoginAttemptStatus(Enum):
    """Login attempt status enumeration."""
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    SUSPICIOUS = "suspicious"


@dataclass
class SecurityConfig:
    """Security configuration parameters."""
    max_login_attempts: int = 5
    lockout_duration: int = 1800  # 30 minutes in seconds
    password_reset_expiry: int = 3600  # 1 hour in seconds
    session_timeout: int = 3600  # 1 hour in seconds
    remember_me_duration: int = 2592000  # 30 days in seconds
    require_2fa: bool = False
    password_history_limit: int = 5
    min_password_age: int = 86400  # 1 day in seconds
    max_password_age: int = 7776000  # 90 days in seconds


class AccountLockoutManager:
    """
    Manages account lockout functionality to prevent brute force attacks.
    """
    
    def __init__(self, redis_client, config: SecurityConfig = SecurityConfig()):
        """
        Initialize account lockout manager.
        
        Args:
            redis_client: Redis client instance
            config: Security configuration
        """
        self.redis = redis_client
        self.config = config
    
    async def record_login_attempt(
        self,
        identifier: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> LoginAttemptStatus:
        """
        Record a login attempt and check if account should be locked.
        
        Args:
            identifier: User identifier (email or username)
            success: Whether login was successful
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Login attempt status
        """
        attempts_key = f"auth:attempts:{identifier}"
        lockout_key = f"auth:lockout:{identifier}"
        history_key = f"auth:history:{identifier}"
        
        # Check if account is locked
        if await self.redis.exists(lockout_key):
            logger.warning(f"Login attempt on locked account: {identifier}")
            return LoginAttemptStatus.BLOCKED
        
        if success:
            # Clear failed attempts on successful login
            await self.redis.delete(attempts_key)
            
            # Record successful login in history
            await self._record_login_history(
                history_key, True, ip_address, user_agent
            )
            
            return LoginAttemptStatus.SUCCESS
        
        # Increment failed attempts
        attempts = await self.redis.incr(attempts_key)
        await self.redis.expire(attempts_key, self.config.lockout_duration)
        
        # Record failed attempt in history
        await self._record_login_history(
            history_key, False, ip_address, user_agent
        )
        
        # Check if should lock account
        if attempts >= self.config.max_login_attempts:
            await self.lock_account(identifier)
            logger.warning(f"Account locked due to too many failed attempts: {identifier}")
            return LoginAttemptStatus.BLOCKED
        
        # Check for suspicious patterns
        if await self._detect_suspicious_activity(identifier, ip_address):
            return LoginAttemptStatus.SUSPICIOUS
        
        return LoginAttemptStatus.FAILED
    
    async def lock_account(self, identifier: str) -> None:
        """
        Lock an account for the configured duration.
        
        Args:
            identifier: User identifier
        """
        lockout_key = f"auth:lockout:{identifier}"
        await self.redis.set(
            lockout_key,
            datetime.utcnow().isoformat(),
            ex=self.config.lockout_duration
        )
        
        # Send notification (implement based on notification system)
        logger.info(f"Account locked: {identifier}")
    
    async def unlock_account(self, identifier: str) -> None:
        """
        Manually unlock an account.
        
        Args:
            identifier: User identifier
        """
        lockout_key = f"auth:lockout:{identifier}"
        attempts_key = f"auth:attempts:{identifier}"
        
        await self.redis.delete(lockout_key)
        await self.redis.delete(attempts_key)
        
        logger.info(f"Account unlocked: {identifier}")
    
    async def is_locked(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if account is locked.
        
        Args:
            identifier: User identifier
            
        Returns:
            Tuple of (is_locked, remaining_seconds)
        """
        lockout_key = f"auth:lockout:{identifier}"
        
        if await self.redis.exists(lockout_key):
            ttl = await self.redis.ttl(lockout_key)
            return True, ttl
        
        return False, None
    
    async def get_failed_attempts(self, identifier: str) -> int:
        """
        Get number of failed login attempts.
        
        Args:
            identifier: User identifier
            
        Returns:
            Number of failed attempts
        """
        attempts_key = f"auth:attempts:{identifier}"
        attempts = await self.redis.get(attempts_key)
        return int(attempts) if attempts else 0
    
    async def _record_login_history(
        self,
        history_key: str,
        success: bool,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> None:
        """
        Record login attempt in history.
        
        Args:
            history_key: Redis key for history
            success: Whether login was successful
            ip_address: Client IP address
            user_agent: Client user agent
        """
        import json
        
        history_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        # Add to sorted set with timestamp as score
        await self.redis.zadd(
            history_key,
            {json.dumps(history_entry): datetime.utcnow().timestamp()}
        )
        
        # Keep only last 100 entries
        await self.redis.zremrangebyrank(history_key, 0, -101)
        
        # Set expiry
        await self.redis.expire(history_key, 86400 * 30)  # 30 days
    
    async def _detect_suspicious_activity(
        self,
        identifier: str,
        ip_address: Optional[str]
    ) -> bool:
        """
        Detect suspicious login patterns.
        
        Args:
            identifier: User identifier
            ip_address: Client IP address
            
        Returns:
            True if suspicious activity detected
        """
        # Check for rapid-fire attempts from same IP
        if ip_address:
            ip_key = f"auth:ip_attempts:{ip_address}"
            ip_attempts = await self.redis.incr(ip_key)
            await self.redis.expire(ip_key, 300)  # 5 minutes
            
            if ip_attempts > 20:  # More than 20 attempts in 5 minutes
                logger.warning(f"Suspicious activity from IP {ip_address}")
                return True
        
        # Check for distributed attack pattern
        history_key = f"auth:history:{identifier}"
        recent_attempts = await self.redis.zrange(
            history_key, -10, -1, withscores=False
        )
        
        if len(recent_attempts) >= 10:
            # Parse attempts and check for patterns
            import json
            unique_ips = set()
            for attempt in recent_attempts:
                try:
                    data = json.loads(attempt)
                    if data.get("ip_address"):
                        unique_ips.add(data["ip_address"])
                except:
                    pass
            
            # Multiple IPs attacking same account
            if len(unique_ips) > 5:
                logger.warning(f"Possible distributed attack on {identifier}")
                return True
        
        return False


class SessionManager:
    """
    Manages secure session handling and validation.
    """
    
    def __init__(self, redis_client, config: SecurityConfig = SecurityConfig()):
        """
        Initialize session manager.
        
        Args:
            redis_client: Redis client instance
            config: Security configuration
        """
        self.redis = redis_client
        self.config = config
    
    async def create_session(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        remember_me: bool = False
    ) -> str:
        """
        Create a new session.
        
        Args:
            user_id: User identifier
            ip_address: Client IP address
            user_agent: Client user agent
            remember_me: Whether to extend session duration
            
        Returns:
            Session token
        """
        session_id = secrets.token_urlsafe(32)
        session_key = f"session:{session_id}"
        
        session_data = {
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "remember_me": remember_me
        }
        
        # Set session expiry based on remember_me
        expiry = (
            self.config.remember_me_duration
            if remember_me
            else self.config.session_timeout
        )
        
        import json
        await self.redis.set(
            session_key,
            json.dumps(session_data),
            ex=expiry
        )
        
        # Track active sessions for user
        user_sessions_key = f"user:sessions:{user_id}"
        await self.redis.sadd(user_sessions_key, session_id)
        await self.redis.expire(user_sessions_key, expiry)
        
        return session_id
    
    async def validate_session(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate a session token.
        
        Args:
            session_id: Session token
            ip_address: Current client IP address
            user_agent: Current client user agent
            
        Returns:
            Tuple of (is_valid, session_data)
        """
        session_key = f"session:{session_id}"
        session_data_raw = await self.redis.get(session_key)
        
        if not session_data_raw:
            return False, None
        
        import json
        session_data = json.loads(session_data_raw)
        
        # Validate IP address if provided (optional strict mode)
        if ip_address and session_data.get("ip_address") != ip_address:
            logger.warning(f"Session IP mismatch for {session_id}")
            # Could invalidate session or just log warning
        
        # Update last activity
        session_data["last_activity"] = datetime.utcnow().isoformat()
        
        # Extend session if not expired
        expiry = (
            self.config.remember_me_duration
            if session_data.get("remember_me")
            else self.config.session_timeout
        )
        
        await self.redis.set(
            session_key,
            json.dumps(session_data),
            ex=expiry
        )
        
        return True, session_data
    
    async def invalidate_session(self, session_id: str) -> None:
        """
        Invalidate a session.
        
        Args:
            session_id: Session token to invalidate
        """
        session_key = f"session:{session_id}"
        session_data_raw = await self.redis.get(session_key)
        
        if session_data_raw:
            import json
            session_data = json.loads(session_data_raw)
            user_id = session_data.get("user_id")
            
            # Remove from user's active sessions
            if user_id:
                user_sessions_key = f"user:sessions:{user_id}"
                await self.redis.srem(user_sessions_key, session_id)
        
        # Delete session
        await self.redis.delete(session_key)
    
    async def invalidate_all_sessions(self, user_id: str) -> None:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User identifier
        """
        user_sessions_key = f"user:sessions:{user_id}"
        session_ids = await self.redis.smembers(user_sessions_key)
        
        # Delete all sessions
        for session_id in session_ids:
            session_key = f"session:{session_id}"
            await self.redis.delete(session_key)
        
        # Clear user's session list
        await self.redis.delete(user_sessions_key)
    
    async def get_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of active sessions
        """
        user_sessions_key = f"user:sessions:{user_id}"
        session_ids = await self.redis.smembers(user_sessions_key)
        
        sessions = []
        import json
        
        for session_id in session_ids:
            session_key = f"session:{session_id}"
            session_data_raw = await self.redis.get(session_key)
            
            if session_data_raw:
                session_data = json.loads(session_data_raw)
                session_data["session_id"] = session_id
                sessions.append(session_data)
        
        return sessions


class PasswordResetManager:
    """
    Manages secure password reset functionality.
    """
    
    def __init__(self, redis_client, config: SecurityConfig = SecurityConfig()):
        """
        Initialize password reset manager.
        
        Args:
            redis_client: Redis client instance
            config: Security configuration
        """
        self.redis = redis_client
        self.config = config
    
    async def create_reset_token(
        self,
        user_id: str,
        email: str,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Create a password reset token.
        
        Args:
            user_id: User identifier
            email: User email
            ip_address: Request IP address
            
        Returns:
            Reset token
        """
        # Generate secure token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        reset_key = f"password_reset:{token_hash}"
        reset_data = {
            "user_id": user_id,
            "email": email,
            "created_at": datetime.utcnow().isoformat(),
            "ip_address": ip_address,
            "used": False
        }
        
        import json
        await self.redis.set(
            reset_key,
            json.dumps(reset_data),
            ex=self.config.password_reset_expiry
        )
        
        # Track reset attempts
        attempts_key = f"password_reset:attempts:{email}"
        await self.redis.incr(attempts_key)
        await self.redis.expire(attempts_key, 3600)  # 1 hour
        
        return token
    
    async def validate_reset_token(
        self,
        token: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate a password reset token.
        
        Args:
            token: Reset token
            
        Returns:
            Tuple of (is_valid, reset_data)
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        reset_key = f"password_reset:{token_hash}"
        
        reset_data_raw = await self.redis.get(reset_key)
        
        if not reset_data_raw:
            return False, None
        
        import json
        reset_data = json.loads(reset_data_raw)
        
        # Check if already used
        if reset_data.get("used"):
            logger.warning(f"Attempt to reuse password reset token")
            return False, None
        
        return True, reset_data
    
    async def use_reset_token(self, token: str) -> bool:
        """
        Mark a reset token as used.
        
        Args:
            token: Reset token
            
        Returns:
            Success status
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        reset_key = f"password_reset:{token_hash}"
        
        reset_data_raw = await self.redis.get(reset_key)
        
        if not reset_data_raw:
            return False
        
        import json
        reset_data = json.loads(reset_data_raw)
        reset_data["used"] = True
        reset_data["used_at"] = datetime.utcnow().isoformat()
        
        # Keep for audit trail but mark as used
        await self.redis.set(
            reset_key,
            json.dumps(reset_data),
            ex=86400  # Keep for 1 day for audit
        )
        
        return True
    
    async def check_reset_rate_limit(self, email: str) -> bool:
        """
        Check if user has exceeded password reset rate limit.
        
        Args:
            email: User email
            
        Returns:
            True if within rate limit
        """
        attempts_key = f"password_reset:attempts:{email}"
        attempts = await self.redis.get(attempts_key)
        
        if attempts and int(attempts) > 3:
            logger.warning(f"Password reset rate limit exceeded for {email}")
            return False
        
        return True


class TwoFactorAuthManager:
    """
    Manages two-factor authentication (2FA) using TOTP.
    """
    
    def __init__(self, redis_client):
        """
        Initialize 2FA manager.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.issuer = "ProLaunch"
    
    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret.
        
        Returns:
            Base32-encoded secret
        """
        return pyotp.random_base32()
    
    def generate_qr_code(self, email: str, secret: str) -> str:
        """
        Generate QR code URL for 2FA setup.
        
        Args:
            email: User email
            secret: TOTP secret
            
        Returns:
            QR code provisioning URI
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=self.issuer
        )
    
    def verify_token(self, secret: str, token: str, window: int = 1) -> bool:
        """
        Verify a TOTP token.
        
        Args:
            secret: User's TOTP secret
            token: Token to verify
            window: Time window for validity
            
        Returns:
            True if valid
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    
    async def store_backup_codes(self, user_id: str, codes: List[str]) -> None:
        """
        Store backup codes for 2FA recovery.
        
        Args:
            user_id: User identifier
            codes: List of backup codes
        """
        # Hash codes before storing
        hashed_codes = [
            hashlib.sha256(code.encode()).hexdigest()
            for code in codes
        ]
        
        backup_key = f"2fa:backup:{user_id}"
        import json
        await self.redis.set(
            backup_key,
            json.dumps(hashed_codes)
        )
    
    async def verify_backup_code(self, user_id: str, code: str) -> bool:
        """
        Verify and consume a backup code.
        
        Args:
            user_id: User identifier
            code: Backup code to verify
            
        Returns:
            True if valid
        """
        backup_key = f"2fa:backup:{user_id}"
        codes_raw = await self.redis.get(backup_key)
        
        if not codes_raw:
            return False
        
        import json
        hashed_codes = json.loads(codes_raw)
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        
        if code_hash in hashed_codes:
            # Remove used code
            hashed_codes.remove(code_hash)
            
            if hashed_codes:
                await self.redis.set(
                    backup_key,
                    json.dumps(hashed_codes)
                )
            else:
                # No more backup codes
                await self.redis.delete(backup_key)
            
            return True
        
        return False
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """
        Generate backup codes for 2FA recovery.
        
        Args:
            count: Number of codes to generate
            
        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric codes
            code = ''.join(
                secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                for _ in range(8)
            )
            # Format as XXXX-XXXX
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        
        return codes


class PasswordHistoryManager:
    """
    Manages password history to prevent reuse.
    """
    
    def __init__(self, redis_client, config: SecurityConfig = SecurityConfig()):
        """
        Initialize password history manager.
        
        Args:
            redis_client: Redis client instance
            config: Security configuration
        """
        self.redis = redis_client
        self.config = config
    
    async def add_password(self, user_id: str, password_hash: str) -> None:
        """
        Add a password to user's history.
        
        Args:
            user_id: User identifier
            password_hash: Hashed password
        """
        history_key = f"password:history:{user_id}"
        
        # Add to sorted set with timestamp as score
        await self.redis.zadd(
            history_key,
            {password_hash: datetime.utcnow().timestamp()}
        )
        
        # Keep only configured number of passwords
        if self.config.password_history_limit > 0:
            await self.redis.zremrangebyrank(
                history_key,
                0,
                -(self.config.password_history_limit + 1)
            )
    
    async def check_password_reuse(self, user_id: str, password_hash: str) -> bool:
        """
        Check if password was recently used.
        
        Args:
            user_id: User identifier
            password_hash: Hashed password to check
            
        Returns:
            True if password was recently used
        """
        history_key = f"password:history:{user_id}"
        
        # Get password history
        history = await self.redis.zrange(history_key, 0, -1)
        
        return password_hash.encode() in history
    
    async def check_password_age(self, user_id: str) -> Tuple[bool, Optional[int]]:
        """
        Check if password has expired.
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (is_expired, days_since_change)
        """
        last_change_key = f"password:last_change:{user_id}"
        last_change = await self.redis.get(last_change_key)
        
        if not last_change:
            return False, None
        
        last_change_date = datetime.fromisoformat(last_change)
        days_since_change = (datetime.utcnow() - last_change_date).days
        
        is_expired = days_since_change * 86400 > self.config.max_password_age
        
        return is_expired, days_since_change
    
    async def update_password_change_date(self, user_id: str) -> None:
        """
        Update the last password change date.
        
        Args:
            user_id: User identifier
        """
        last_change_key = f"password:last_change:{user_id}"
        await self.redis.set(
            last_change_key,
            datetime.utcnow().isoformat()
        )