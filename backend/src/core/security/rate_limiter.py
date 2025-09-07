from typing import Optional, Tuple
from datetime import datetime, timedelta
from redis.asyncio import Redis
import json
import logging
from fastapi import HTTPException
import enum

logger = logging.getLogger(__name__)


class RateLimitType(enum.Enum):
    """Types of rate limiting"""
    WS_CONNECT = "ws_connect"
    MESSAGE = "message"
    ROOM_JOIN = "room_join"
    ROOM_CREATE = "room_create"
    FILE_UPLOAD = "file_upload"


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class RedisRateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis
        
        # Default rate limits
        self.DEFAULT_LIMITS = {
            'ws_connect': (5, 60),    # 5 connections per minute
            'message': (30, 60),      # 30 messages per minute
            'room_join': (10, 300),   # 10 room joins per 5 minutes
            'room_create': (5, 300),  # 5 room creations per 5 minutes
            'file_upload': (10, 300), # 10 file uploads per 5 minutes
        }

    async def check_rate_limit(
        self,
        key: str,
        identifier: str,
        action: str,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if a request should be rate limited.
        Returns (is_allowed, retry_after_seconds)
        """
        try:
            # Use default limits if not specified
            if max_requests is None or window_seconds is None:
                max_requests, window_seconds = self.DEFAULT_LIMITS.get(
                    action,
                    (30, 60)  # Default to 30 requests per minute
                )

            # Create a unique Redis key for this limiter
            redis_key = f"rate_limit:{action}:{key}:{identifier}"
            
            # Get the current timestamp
            now = datetime.utcnow()
            now_ts = int(now.timestamp())
            window_start_ts = now_ts - window_seconds

            # Clean up old requests and add the new one
            async with self.redis.pipeline() as pipe:
                # Remove old entries
                await pipe.zremrangebyscore(redis_key, 0, window_start_ts)
                # Add new request
                await pipe.zadd(redis_key, {json.dumps(now_ts): now_ts})
                # Get count of requests in window
                await pipe.zcount(redis_key, window_start_ts, now_ts)
                # Set expiry on the key
                await pipe.expire(redis_key, window_seconds)
                # Execute pipeline
                results = await pipe.execute()

            request_count = results[2]

            # Check if rate limit is exceeded
            if request_count > max_requests:
                # Calculate retry after
                oldest_ts = await self.redis.zrange(
                    redis_key,
                    0,
                    0,
                    withscores=True
                )
                if oldest_ts:
                    retry_after = int(oldest_ts[0][1]) + window_seconds - now_ts
                    return False, retry_after
                return False, window_seconds

            return True, None

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # On error, allow the request but log the issue
            return True, None

    async def check_concurrent_limit(
        self,
        key: str,
        identifier: str,
        action: str,
        max_concurrent: int
    ) -> bool:
        """
        Check if concurrent action limit is exceeded
        """
        try:
            redis_key = f"concurrent:{action}:{key}:{identifier}"
            
            # Get current count
            count = await self.redis.get(redis_key)
            current = int(count) if count else 0
            
            # Check if adding one more would exceed limit
            if current >= max_concurrent:
                return False
                
            # Increment count
            await self.redis.incr(redis_key)
            # Set expiry to clean up abandoned counts
            await self.redis.expire(redis_key, 300)  # 5 minute expiry
            
            return True

        except Exception as e:
            logger.error(f"Concurrent limit check error: {e}")
            return True

    async def increment_concurrent(
        self,
        key: str,
        identifier: str,
        action: str
    ) -> None:
        """
        Increment concurrent action count
        """
        try:
            redis_key = f"concurrent:{action}:{key}:{identifier}"
            await self.redis.incr(redis_key)
            await self.redis.expire(redis_key, 300)
        except Exception as e:
            logger.error(f"Failed to increment concurrent count: {e}")

    async def decrement_concurrent(
        self,
        key: str,
        identifier: str,
        action: str
    ) -> None:
        """
        Decrement concurrent action count
        """
        try:
            redis_key = f"concurrent:{action}:{key}:{identifier}"
            await self.redis.decr(redis_key)
        except Exception as e:
            logger.error(f"Failed to decrement concurrent count: {e}")

    async def ip_is_blocked(self, ip: str) -> bool:
        """
        Check if an IP is blocked due to suspicious activity
        """
        try:
            redis_key = f"blocked_ip:{ip}"
            return bool(await self.redis.exists(redis_key))
        except Exception as e:
            logger.error(f"IP block check error: {e}")
            return False

    async def block_ip(
        self,
        ip: str,
        reason: str,
        duration: int = 3600
    ) -> None:
        """
        Block an IP for suspicious activity
        """
        try:
            redis_key = f"blocked_ip:{ip}"
            await self.redis.setex(
                redis_key,
                duration,
                json.dumps({
                    "reason": reason,
                    "blocked_at": datetime.utcnow().isoformat()
                })
            )
        except Exception as e:
            logger.error(f"Failed to block IP: {e}")

    async def record_failed_attempt(
        self,
        key: str,
        identifier: str,
        action: str
    ) -> None:
        """
        Record a failed attempt (e.g. failed login)
        """
        try:
            redis_key = f"failed_attempts:{action}:{key}:{identifier}"
            async with self.redis.pipeline() as pipe:
                await pipe.incr(redis_key)
                await pipe.expire(redis_key, 300)  # 5 minute window
                count = await pipe.execute()

            # Block if too many failures
            if count[0] >= 5:  # 5 failures in 5 minutes
                await self.block_ip(
                    identifier,
                    f"Too many failed {action} attempts"
                )
        except Exception as e:
            logger.error(f"Failed to record attempt: {e}")

async def rate_limit_dependency(
    action: str,
    redis: Redis,
    identifier: str,
    max_requests: Optional[int] = None,
    window_seconds: Optional[int] = None
):
    """
    FastAPI dependency for rate limiting
    """
    limiter = RateLimiter(redis)
    is_allowed, retry_after = await limiter.check_rate_limit(
        "api",
        identifier,
        action,
        max_requests,
        window_seconds
    )

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": retry_after
            }
        )