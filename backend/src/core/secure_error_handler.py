"""
Secure Error Handling and Logging Module

Implements secure error handling with sanitized responses
and comprehensive security logging.
"""

from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
import hashlib
import json
from datetime import datetime
from enum import Enum
import re
import sys

logger = logging.getLogger(__name__)


class SecurityEventType(Enum):
    """Types of security events to log."""
    AUTH_FAILED = "authentication_failed"
    AUTH_SUCCESS = "authentication_success"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_REQUEST = "suspicious_request"
    INJECTION_ATTEMPT = "injection_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    ACCOUNT_LOCKED = "account_locked"
    PASSWORD_CHANGED = "password_changed"
    SESSION_HIJACK_ATTEMPT = "session_hijack_attempt"


class ErrorResponse:
    """
    Standardized error response structure.
    """
    
    @staticmethod
    def create(
        error_code: str,
        message: str,
        status_code: int,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create standardized error response.
        
        Args:
            error_code: Application-specific error code
            message: User-friendly error message
            status_code: HTTP status code
            details: Additional error details (sanitized)
            request_id: Request tracking ID
            
        Returns:
            Error response dictionary
        """
        response = {
            "error": {
                "code": error_code,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        if request_id:
            response["error"]["request_id"] = request_id
        
        if details and not self._contains_sensitive_data(details):
            response["error"]["details"] = details
        
        return response
    
    @staticmethod
    def _contains_sensitive_data(data: Any) -> bool:
        """
        Check if data contains sensitive information.
        
        Args:
            data: Data to check
            
        Returns:
            True if sensitive data detected
        """
        sensitive_patterns = [
            r"password",
            r"secret",
            r"token",
            r"api[_-]?key",
            r"auth",
            r"credential",
            r"private[_-]?key",
            r"ssn",
            r"social[_-]?security"
        ]
        
        data_str = str(data).lower()
        
        for pattern in sensitive_patterns:
            if re.search(pattern, data_str, re.IGNORECASE):
                return True
        
        return False


class SecureErrorHandler:
    """
    Handles application errors securely without exposing sensitive information.
    """
    
    def __init__(self, environment: str = "production"):
        """
        Initialize error handler.
        
        Args:
            environment: Current environment
        """
        self.environment = environment
        self.show_details = environment == "development"
    
    async def handle_exception(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """
        Handle general exceptions securely.
        
        Args:
            request: Request that caused the exception
            exc: Exception instance
            
        Returns:
            Sanitized error response
        """
        # Generate request ID for tracking
        request_id = self._generate_request_id(request)
        
        # Log the full error securely
        self._log_error(request, exc, request_id)
        
        # Determine error details based on exception type
        if isinstance(exc, HTTPException):
            return await self.handle_http_exception(request, exc, request_id)
        
        elif isinstance(exc, ValueError):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse.create(
                    error_code="VALIDATION_ERROR",
                    message="Invalid input provided",
                    status_code=400,
                    request_id=request_id
                )
            )
        
        elif isinstance(exc, PermissionError):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=ErrorResponse.create(
                    error_code="PERMISSION_DENIED",
                    message="You don't have permission to perform this action",
                    status_code=403,
                    request_id=request_id
                )
            )
        
        else:
            # Generic error response for production
            if self.show_details:
                # Show stack trace in development
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content=ErrorResponse.create(
                        error_code="INTERNAL_ERROR",
                        message="An internal error occurred",
                        status_code=500,
                        details={"traceback": traceback.format_exc()},
                        request_id=request_id
                    )
                )
            else:
                # Hide details in production
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content=ErrorResponse.create(
                        error_code="INTERNAL_ERROR",
                        message="An internal error occurred. Please try again later.",
                        status_code=500,
                        request_id=request_id
                    )
                )
    
    async def handle_http_exception(
        self,
        request: Request,
        exc: HTTPException,
        request_id: str
    ) -> JSONResponse:
        """
        Handle HTTP exceptions with sanitized responses.
        
        Args:
            request: Request that caused the exception
            exc: HTTP exception instance
            request_id: Request tracking ID
            
        Returns:
            Sanitized error response
        """
        # Map status codes to error codes
        error_code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE"
        }
        
        error_code = error_code_map.get(exc.status_code, "ERROR")
        
        # Sanitize error detail
        detail = self._sanitize_error_detail(exc.detail)
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse.create(
                error_code=error_code,
                message=detail,
                status_code=exc.status_code,
                request_id=request_id
            ),
            headers=exc.headers if hasattr(exc, 'headers') else None
        )
    
    def _generate_request_id(self, request: Request) -> str:
        """
        Generate unique request ID for tracking.
        
        Args:
            request: HTTP request
            
        Returns:
            Request ID
        """
        # Check if request ID already exists in headers
        request_id = request.headers.get("X-Request-ID")
        
        if not request_id:
            # Generate new ID
            timestamp = datetime.utcnow().isoformat()
            path = request.url.path
            request_id = hashlib.sha256(
                f"{timestamp}{path}".encode()
            ).hexdigest()[:16]
        
        return request_id
    
    def _sanitize_error_detail(self, detail: Any) -> str:
        """
        Sanitize error detail to remove sensitive information.
        
        Args:
            detail: Error detail
            
        Returns:
            Sanitized detail string
        """
        if not detail:
            return "An error occurred"
        
        detail_str = str(detail)
        
        # Remove file paths
        detail_str = re.sub(r'(/[^\s]+)+', '[PATH]', detail_str)
        
        # Remove potential SQL
        detail_str = re.sub(
            r'(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE).*',
            '[QUERY]',
            detail_str,
            flags=re.IGNORECASE
        )
        
        # Remove stack traces
        detail_str = re.sub(
            r'File ".*", line \d+.*',
            '[STACK_TRACE]',
            detail_str
        )
        
        # Remove potential passwords or tokens
        detail_str = re.sub(
            r'(password|token|secret|key)[\s:=]+\S+',
            '[REDACTED]',
            detail_str,
            flags=re.IGNORECASE
        )
        
        return detail_str
    
    def _log_error(self, request: Request, exc: Exception, request_id: str) -> None:
        """
        Log error details securely.
        
        Args:
            request: HTTP request
            exc: Exception instance
            request_id: Request tracking ID
        """
        error_data = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent"),
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        }
        
        # Add stack trace in development
        if self.show_details:
            error_data["traceback"] = traceback.format_exc()
        
        # Log at appropriate level
        if isinstance(exc, HTTPException):
            if exc.status_code >= 500:
                logger.error(f"Server error: {json.dumps(error_data)}")
            elif exc.status_code >= 400:
                logger.warning(f"Client error: {json.dumps(error_data)}")
        else:
            logger.error(f"Unhandled exception: {json.dumps(error_data)}")


class SecurityLogger:
    """
    Specialized logger for security events.
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize security logger.
        
        Args:
            redis_client: Optional Redis client for storing events
        """
        self.redis = redis_client
        self.logger = logging.getLogger("security")
        
        # Set up security log handler
        handler = logging.FileHandler("security.log")
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    async def log_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "INFO"
    ) -> None:
        """
        Log security event.
        
        Args:
            event_type: Type of security event
            user_id: User involved (if applicable)
            ip_address: Client IP address
            details: Additional event details
            severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "severity": severity,
            "details": details or {}
        }
        
        # Log to file
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        log_method(json.dumps(event))
        
        # Store in Redis for real-time monitoring
        if self.redis:
            await self._store_event(event)
        
        # Trigger alerts for critical events
        if severity == "CRITICAL":
            await self._trigger_alert(event)
    
    async def _store_event(self, event: Dict[str, Any]) -> None:
        """
        Store security event in Redis.
        
        Args:
            event: Event data
        """
        try:
            # Store in time-series
            key = f"security:events:{event['event_type']}"
            await self.redis.zadd(
                key,
                {json.dumps(event): datetime.utcnow().timestamp()}
            )
            
            # Keep only last 1000 events per type
            await self.redis.zremrangebyrank(key, 0, -1001)
            
            # Set expiry
            await self.redis.expire(key, 86400 * 30)  # 30 days
            
        except Exception as e:
            logger.error(f"Failed to store security event: {e}")
    
    async def _trigger_alert(self, event: Dict[str, Any]) -> None:
        """
        Trigger alert for critical security events.
        
        Args:
            event: Critical event data
        """
        # Implement alert mechanism (email, Slack, etc.)
        logger.critical(f"SECURITY ALERT: {json.dumps(event)}")
    
    async def get_recent_events(
        self,
        event_type: Optional[SecurityEventType] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent security events.
        
        Args:
            event_type: Filter by event type
            user_id: Filter by user
            limit: Maximum number of events
            
        Returns:
            List of security events
        """
        if not self.redis:
            return []
        
        events = []
        
        if event_type:
            # Get events of specific type
            key = f"security:events:{event_type.value}"
            raw_events = await self.redis.zrange(key, -limit, -1)
            
            for raw_event in raw_events:
                event = json.loads(raw_event)
                if not user_id or event.get("user_id") == user_id:
                    events.append(event)
        
        else:
            # Get all event types
            for et in SecurityEventType:
                key = f"security:events:{et.value}"
                raw_events = await self.redis.zrange(key, -limit // 10, -1)
                
                for raw_event in raw_events:
                    event = json.loads(raw_event)
                    if not user_id or event.get("user_id") == user_id:
                        events.append(event)
        
        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return events[:limit]
    
    async def analyze_patterns(self) -> Dict[str, Any]:
        """
        Analyze security event patterns for anomalies.
        
        Returns:
            Analysis results
        """
        analysis = {
            "timestamp": datetime.utcnow().isoformat(),
            "anomalies": [],
            "statistics": {}
        }
        
        # Count events by type
        for event_type in SecurityEventType:
            key = f"security:events:{event_type.value}"
            count = await self.redis.zcard(key) if self.redis else 0
            analysis["statistics"][event_type.value] = count
            
            # Check for anomalies
            if event_type == SecurityEventType.AUTH_FAILED:
                if count > 100:  # Threshold for failed auth attempts
                    analysis["anomalies"].append({
                        "type": "high_failed_auth",
                        "count": count,
                        "severity": "HIGH"
                    })
            
            elif event_type == SecurityEventType.INJECTION_ATTEMPT:
                if count > 10:  # Even small numbers are concerning
                    analysis["anomalies"].append({
                        "type": "injection_attempts",
                        "count": count,
                        "severity": "CRITICAL"
                    })
        
        return analysis


class AuditLogger:
    """
    Audit logging for compliance and security monitoring.
    """
    
    def __init__(self, storage_backend=None):
        """
        Initialize audit logger.
        
        Args:
            storage_backend: Backend for storing audit logs
        """
        self.storage = storage_backend
        self.logger = logging.getLogger("audit")
    
    async def log_data_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: Optional[str] = None,
        success: bool = True
    ) -> None:
        """
        Log data access for audit trail.
        
        Args:
            user_id: User accessing data
            resource_type: Type of resource accessed
            resource_id: ID of resource accessed
            action: Action performed (read, write, delete)
            ip_address: Client IP address
            success: Whether action was successful
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "ip_address": ip_address,
            "success": success
        }
        
        # Log to file
        self.logger.info(json.dumps(audit_entry))
        
        # Store in backend if available
        if self.storage:
            await self.storage.store_audit_log(audit_entry)
    
    async def log_configuration_change(
        self,
        user_id: str,
        setting: str,
        old_value: Any,
        new_value: Any,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Log configuration changes.
        
        Args:
            user_id: User making change
            setting: Setting that was changed
            old_value: Previous value
            new_value: New value
            ip_address: Client IP address
        """
        # Sanitize sensitive values
        if "password" in setting.lower() or "key" in setting.lower():
            old_value = "[REDACTED]"
            new_value = "[REDACTED]"
        
        change_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "setting": setting,
            "old_value": str(old_value),
            "new_value": str(new_value),
            "ip_address": ip_address
        }
        
        self.logger.info(f"Configuration change: {json.dumps(change_entry)}")


def setup_error_handling(app, environment: str = "production"):
    """
    Setup error handling for FastAPI application.
    
    Args:
        app: FastAPI application instance
        environment: Current environment
    """
    error_handler = SecureErrorHandler(environment)
    
    # Register exception handlers
    app.add_exception_handler(Exception, error_handler.handle_exception)
    app.add_exception_handler(HTTPException, error_handler.handle_http_exception)
    
    # Add request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = hashlib.sha256(
                f"{datetime.utcnow().isoformat()}{request.url.path}".encode()
            ).hexdigest()[:16]
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response