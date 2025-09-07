from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

def setup_security_headers(app: FastAPI, csp_report_uri: str, hsts_max_age: int = 31536000):
    """Set up security headers middleware."""
    return app