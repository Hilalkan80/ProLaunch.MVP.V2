from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response
from typing import Callable, Dict, List, Optional
import logging
import time
from datetime import datetime
import re
import json

from .rate_limiter import RedisRateLimiter as RateLimiter
from .content_security import ContentSecurity
from .sentry_security import SentrySecurity, SecurityLevel, SecurityEventType

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        content_security: ContentSecurity,
        sentry: SentrySecurity
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.content_security = content_security
        self.sentry = sentry
        
        # Security settings
        self.BLOCKED_USER_AGENTS = {
            r'sqlmap',
            r'nikto',
            r'nessus',
            r'masscan',
            r'nmap',
            r'burp',
            r'python-requests'  # Block basic scripts
        }
        
        self.BLOCKED_PATHS = {
            r'\.php$',
            r'\.asp$',
            r'\.jsp$',
            r'\.env$',
            r'wp-admin',
            r'wp-login',
            r'phpinfo',
            r'admin',
            r'shell'
        }
        
        self.SUSPICIOUS_PATTERNS = {
            r'select.*from',
            r'union.*select',
            r'drop.*table',
            r'exec\(',
            r'eval\(',
            r'alert\(',
            r'document\.cookie',
            r'<script',
            r'javascript:',
            r'onload=',
            r'onerror='
        }

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Main middleware dispatch method
        """
        start_time = time.time()
        
        try:
            # Extract request info
            client_ip = request.client.host
            user_agent = request.headers.get('user-agent', '')
            path = request.url.path
            method = request.method
            
            # Basic security checks
            if not await self._is_request_allowed(request):
                return Response(
                    content=json.dumps({
                        'error': 'Request blocked for security reasons'
                    }),
                    status_code=403,
                    media_type='application/json'
                )
            
            # Add security headers to response
            response = await call_next(request)
            response = self._add_security_headers(response)
            
            # Log request timing
            process_time = time.time() - start_time
            if process_time > 1.0:  # Log slow requests
                await self.sentry.capture_suspicious_activity(
                    message=f"Slow request detected: {path}",
                    activity_type="slow_request",
                    severity=SecurityLevel.WARNING,
                    details={
                        'path': path,
                        'method': method,
                        'process_time': process_time
                    }
                )
            
            return response

        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            await self.sentry.capture_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                SecurityLevel.ERROR,
                f"Security middleware error: {str(e)}",
                {
                    'path': request.url.path,
                    'method': request.method,
                    'error': str(e)
                }
            )
            return Response(
                content=json.dumps({
                    'error': 'Internal server error'
                }),
                status_code=500,
                media_type='application/json'
            )

    async def _is_request_allowed(self, request: Request) -> bool:
        """
        Check if request should be allowed
        """
        try:
            client_ip = request.client.host
            user_agent = request.headers.get('user-agent', '')
            path = request.url.path
            method = request.method
            
            # Check IP blocking
            if await self.rate_limiter.ip_is_blocked(client_ip):
                await self.sentry.capture_suspicious_activity(
                    message=f"Request from blocked IP: {client_ip}",
                    activity_type="blocked_ip",
                    severity=SecurityLevel.WARNING,
                    ip_address=client_ip
                )
                return False
            
            # Check user agent
            if self._is_suspicious_user_agent(user_agent):
                await self.rate_limiter.block_ip(
                    client_ip,
                    'Suspicious user agent'
                )
                await self.sentry.capture_suspicious_activity(
                    message=f"Suspicious user agent detected: {user_agent}",
                    activity_type="suspicious_ua",
                    severity=SecurityLevel.WARNING,
                    ip_address=client_ip,
                    details={'user_agent': user_agent}
                )
                return False
            
            # Check path
            if self._is_blocked_path(path):
                await self.sentry.capture_suspicious_activity(
                    message=f"Request to blocked path: {path}",
                    activity_type="blocked_path",
                    severity=SecurityLevel.WARNING,
                    ip_address=client_ip
                )
                return False
            
            # Check rate limits
            is_allowed, retry_after = await self.rate_limiter.check_rate_limit(
                'http',
                client_ip,
                method.lower()
            )
            if not is_allowed:
                await self.sentry.capture_rate_limit_violation(
                    message=f"Rate limit exceeded for {method} requests",
                    limit_type=f"http_{method.lower()}",
                    ip_address=client_ip
                )
                return False
            
            # Check request body for suspicious patterns
            if request.method in ['POST', 'PUT', 'PATCH']:
                body = await request.body()
                if body:
                    body_str = body.decode()
                    if self._contains_suspicious_patterns(body_str):
                        await self.sentry.capture_suspicious_activity(
                            message="Suspicious patterns in request body",
                            activity_type="suspicious_content",
                            severity=SecurityLevel.WARNING,
                            ip_address=client_ip
                        )
                        return False
            
            return True

        except Exception as e:
            logger.error(f"Request validation error: {e}")
            return False

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """
        Check if user agent matches known malicious patterns
        """
        if not user_agent:
            return True
            
        return any(
            re.search(pattern, user_agent, re.IGNORECASE)
            for pattern in self.BLOCKED_USER_AGENTS
        )

    def _is_blocked_path(self, path: str) -> bool:
        """
        Check if path matches blocked patterns
        """
        return any(
            re.search(pattern, path, re.IGNORECASE)
            for pattern in self.BLOCKED_PATHS
        )

    def _contains_suspicious_patterns(self, content: str) -> bool:
        """
        Check content for suspicious patterns
        """
        return any(
            re.search(pattern, content, re.IGNORECASE)
            for pattern in self.SUSPICIOUS_PATTERNS
        )

    def _add_security_headers(self, response: Response) -> Response:
        """
        Add security headers to response
        """
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' wss:; "
            "frame-ancestors 'none'; "
            "form-action 'self';"
        )
        
        # Other security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Permissions-Policy'] = (
            'accelerometer=(), '
            'camera=(), '
            'geolocation=(), '
            'gyroscope=(), '
            'magnetometer=(), '
            'microphone=(), '
            'payment=(), '
            'usb=()'
        )
        
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Simplified middleware that only adds security headers
    """
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response