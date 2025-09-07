from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import redis
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json

class RateLimitExceeded(HTTPException):
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=429,
            detail=f"Rate limit exceeded. Please try again in {retry_after} seconds."
        )
        self.headers = {"Retry-After": str(retry_after)}

class RateLimiter:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    def _get_window_key(self, key: str, window_size: int) -> str:
        """Get the current window key based on timestamp."""
        timestamp = int(datetime.now().timestamp())
        window = timestamp - (timestamp % window_size)
        return f"ratelimit:{key}:{window}"

    def _cleanup_old_windows(self, key: str, window_size: int):
        """Remove expired window keys."""
        current_time = int(datetime.now().timestamp())
        pattern = f"ratelimit:{key}:*"
        for old_key in self.redis.keys(pattern):
            window_time = int(old_key.decode().split(":")[-1])
            if current_time - window_time > window_size:
                self.redis.delete(old_key)

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_size: int
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if the rate limit has been exceeded.
        Returns (allowed: bool, retry_after: Optional[int])
        """
        window_key = self._get_window_key(key, window_size)
        
        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window_size)
        current_requests = pipe.execute()[0]

        if current_requests > max_requests:
            # Calculate retry-after
            window_end = (int(datetime.now().timestamp()) // window_size + 1) * window_size
            retry_after = window_end - int(datetime.now().timestamp())
            return False, retry_after

        return True, None

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        redis_url: str,
        auth_limits: Optional[Dict[str, Tuple[int, int]]] = None
    ):
        super().__init__(app)
        self.limiter = RateLimiter(redis_url)
        
        # Default rate limits if none provided
        self.limits = {
            "default": (100, 60),  # 100 requests per minute
            "auth": (5, 60),       # 5 requests per minute
            "websocket": (10, 60), # 10 connections per minute
            "export": (10, 3600)   # 10 requests per hour
        }
        if auth_limits:
            self.limits.update(auth_limits)

    def _get_client_identifier(self, request: Request) -> str:
        """Get a unique identifier for the client."""
        # Prefer authenticated user ID if available
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host
        return f"ip:{ip}"

    def _get_endpoint_type(self, request: Request) -> str:
        """Determine the type of endpoint being accessed."""
        path = request.url.path.lower()
        
        if path.startswith("/auth"):
            return "auth"
        elif path.startswith("/ws"):
            return "websocket"
        elif path.startswith("/export"):
            return "export"
        return "default"

    async def dispatch(self, request: Request, call_next):
        # Determine rate limit based on endpoint
        endpoint_type = self._get_endpoint_type(request)
        max_requests, window_size = self.limits[endpoint_type]
        
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Check rate limit
        allowed, retry_after = self.limiter.check_rate_limit(
            f"{endpoint_type}:{client_id}",
            max_requests,
            window_size
        )
        
        if not allowed:
            raise RateLimitExceeded(retry_after)
        
        # If allowed, process the request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max_requests - 1  # Approximate remaining requests
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(window_size)
        
        return response

def setup_rate_limiter(
    app: FastAPI,
    redis_url: str,
    auth_limits: Optional[Dict[str, Tuple[int, int]]] = None
) -> None:
    """
    Configure rate limiting middleware for a FastAPI application.
    
    Args:
        app: The FastAPI application instance
        redis_url: Redis connection URL
        auth_limits: Optional custom rate limits for different endpoint types
    """
    app.add_middleware(
        RateLimitMiddleware,
        redis_url=redis_url,
        auth_limits=auth_limits
    )