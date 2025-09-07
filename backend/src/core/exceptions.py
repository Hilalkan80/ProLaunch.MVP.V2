"""
Custom Exception Classes

This module defines custom exceptions for better error handling and debugging.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """Base authentication exception"""
    
    def __init__(
        self,
        detail: str = "Authentication failed",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        headers: Optional[Dict[str, str]] = None
    ):
        if headers is None:
            headers = {"WWW-Authenticate": "Bearer"}
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid"""
    
    def __init__(self, detail: str = "Invalid email or password"):
        super().__init__(detail=detail)


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired"""
    
    def __init__(self, detail: str = "Token has expired"):
        super().__init__(detail=detail)


class TokenInvalidError(AuthenticationError):
    """Raised when JWT token is invalid"""
    
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail=detail)


class AuthorizationError(HTTPException):
    """Base authorization exception"""
    
    def __init__(
        self,
        detail: str = "Not authorized",
        status_code: int = status.HTTP_403_FORBIDDEN
    ):
        super().__init__(status_code=status_code, detail=detail)


class InsufficientPermissionsError(AuthorizationError):
    """Raised when user lacks required permissions"""
    
    def __init__(self, detail: str = "Insufficient permissions for this operation"):
        super().__init__(detail=detail)


class SubscriptionRequiredError(AuthorizationError):
    """Raised when operation requires higher subscription tier"""
    
    def __init__(self, required_tier: str, detail: Optional[str] = None):
        if detail is None:
            detail = f"This feature requires {required_tier} subscription or higher"
        super().__init__(detail=detail)


class AccountError(HTTPException):
    """Base account-related exception"""
    
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        super().__init__(status_code=status_code, detail=detail)


class AccountLockedError(AccountError):
    """Raised when account is locked due to security reasons"""
    
    def __init__(self, locked_until: Optional[str] = None):
        detail = "Account is locked due to security reasons"
        if locked_until:
            detail = f"Account is locked until {locked_until}"
        super().__init__(detail=detail, status_code=status.HTTP_423_LOCKED)


class AccountDisabledError(AccountError):
    """Raised when account has been disabled"""
    
    def __init__(self):
        super().__init__(
            detail="Account has been disabled. Please contact support.",
            status_code=status.HTTP_403_FORBIDDEN
        )


class EmailNotVerifiedError(AccountError):
    """Raised when email verification is required"""
    
    def __init__(self):
        super().__init__(
            detail="Email verification required. Please verify your email address.",
            status_code=status.HTTP_403_FORBIDDEN
        )


class ValidationError(HTTPException):
    """Base validation exception"""
    
    def __init__(
        self,
        detail: str,
        field: Optional[str] = None,
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY
    ):
        if field:
            detail = {
                "field": field,
                "message": detail
            }
        super().__init__(status_code=status_code, detail=detail)


class EmailValidationError(ValidationError):
    """Raised when email validation fails"""
    
    def __init__(self, detail: str = "Invalid email format"):
        super().__init__(detail=detail, field="email")


class PasswordValidationError(ValidationError):
    """Raised when password validation fails"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, field="password")


class DuplicateResourceError(HTTPException):
    """Raised when trying to create a duplicate resource"""
    
    def __init__(
        self,
        resource: str = "Resource",
        detail: Optional[str] = None
    ):
        if detail is None:
            detail = f"{resource} already exists"
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class ResourceNotFoundError(HTTPException):
    """Raised when requested resource is not found"""
    
    def __init__(
        self,
        resource: str = "Resource",
        detail: Optional[str] = None
    ):
        if detail is None:
            detail = f"{resource} not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class RateLimitExceededError(HTTPException):
    """Raised when rate limit is exceeded"""
    
    def __init__(
        self,
        limit: int,
        window: str = "minute",
        detail: Optional[str] = None
    ):
        if detail is None:
            detail = f"Rate limit exceeded. Maximum {limit} requests per {window}."
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "60"}
        )


class DatabaseError(HTTPException):
    """Base database exception"""
    
    def __init__(
        self,
        detail: str = "Database operation failed",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        super().__init__(status_code=status_code, detail=detail)


class RedisConnectionError(HTTPException):
    """Raised when Redis connection fails"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service temporarily unavailable"
        )


class ExternalServiceError(HTTPException):
    """Raised when external service call fails"""
    
    def __init__(
        self,
        service: str,
        detail: Optional[str] = None
    ):
        if detail is None:
            detail = f"{service} service temporarily unavailable"
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )


class SecurityError(HTTPException):
    """Base security exception"""
    
    def __init__(
        self,
        detail: str = "Security violation detected",
        status_code: int = status.HTTP_403_FORBIDDEN
    ):
        super().__init__(status_code=status_code, detail=detail)


class TokenReuseError(SecurityError):
    """Raised when token reuse is detected"""
    
    def __init__(self):
        super().__init__(
            detail="Token reuse detected. All tokens have been revoked for security."
        )


class SuspiciousActivityError(SecurityError):
    """Raised when suspicious activity is detected"""
    
    def __init__(self, detail: str = "Suspicious activity detected"):
        super().__init__(detail=detail)


# Milestone-specific exceptions

class MilestoneError(HTTPException):
    """Base milestone exception"""
    
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        super().__init__(status_code=status_code, detail=detail)


class MilestoneNotFoundError(MilestoneError):
    """Raised when milestone is not found"""
    
    def __init__(self, milestone_code: Optional[str] = None):
        detail = "Milestone not found"
        if milestone_code:
            detail = f"Milestone {milestone_code} not found"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class MilestoneLockedError(MilestoneError):
    """Raised when trying to access a locked milestone"""
    
    def __init__(self, milestone_code: str, missing_dependencies: Optional[list] = None):
        detail = f"Milestone {milestone_code} is locked"
        if missing_dependencies:
            detail += f". Missing dependencies: {', '.join(missing_dependencies)}"
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class CircularDependencyError(MilestoneError):
    """Raised when circular dependency is detected"""
    
    def __init__(self, cycle: Optional[list] = None):
        detail = "Circular dependency detected"
        if cycle:
            detail += f": {' -> '.join(cycle)}"
        super().__init__(detail=detail, status_code=status.HTTP_409_CONFLICT)


class DependencyValidationError(MilestoneError):
    """Raised when dependency validation fails"""
    
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class MilestoneProcessingError(MilestoneError):
    """Raised when milestone processing fails"""
    
    def __init__(self, milestone_code: str, error: str):
        detail = f"Failed to process milestone {milestone_code}: {error}"
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)