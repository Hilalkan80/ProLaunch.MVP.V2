from typing import Dict, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
from starlette.types import ASGIApp
import secrets

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        csp_report_uri: Optional[str] = None,
        hsts_max_age: int = 31536000,  # 1 year
    ):
        super().__init__(app)
        self.csp_report_uri = csp_report_uri
        self.hsts_max_age = hsts_max_age

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Generate nonce for CSP
        nonce = secrets.token_urlsafe(16)
        
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}'",
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles for now
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "block-all-mixed-content",
            "upgrade-insecure-requests"
        ]
        
        if self.csp_report_uri:
            csp_directives.append(f"report-uri {self.csp_report_uri}")

        headers: Dict[str, str] = {
            # Content Security Policy
            "Content-Security-Policy": "; ".join(csp_directives),
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable browser XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # HSTS (HTTP Strict Transport Security)
            "Strict-Transport-Security": f"max-age={self.hsts_max_age}; includeSubDomains; preload",
            
            # Control referrer information
            "Referrer-Policy": "same-origin",
            
            # Permissions Policy (formerly Feature Policy)
            "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
        }

        # Add headers to response
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value

        # Add nonce to response headers for use in templates
        response.headers["X-CSP-Nonce"] = nonce

        return response

def setup_security_headers(
    app: FastAPI,
    csp_report_uri: Optional[str] = None,
    hsts_max_age: int = 31536000
) -> None:
    """
    Configure security headers middleware for a FastAPI application.
    
    Args:
        app: The FastAPI application instance
        csp_report_uri: Optional URI for CSP violation reporting
        hsts_max_age: Max age for HSTS in seconds (default 1 year)
    """
    app.add_middleware(
        SecurityHeadersMiddleware,
        csp_report_uri=csp_report_uri,
        hsts_max_age=hsts_max_age
    )