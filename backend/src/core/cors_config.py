from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import re

class CORSConfig(BaseModel):
    allowed_origins: List[str]
    allow_credentials: bool = True
    allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    allowed_headers: List[str] = ["*"]
    expose_headers: List[str] = [
        "Content-Length",
        "Content-Type",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset"
    ]
    max_age: int = 600  # 10 minutes

class CORSConfigManager:
    def __init__(self, config: CORSConfig):
        self.config = config
        self._validate_origins()

    def _validate_origins(self) -> None:
        """Validate and normalize origin patterns."""
        validated_origins = []
        for origin in self.config.allowed_origins:
            # Convert pattern to regex if it contains wildcards
            if "*" in origin:
                pattern = origin.replace(".", "\\.").replace("*", ".*")
                try:
                    re.compile(pattern)
                    validated_origins.append(origin)
                except re.error as e:
                    raise ValueError(f"Invalid origin pattern: {origin}") from e
            else:
                # Validate non-wildcard origins
                try:
                    if origin != "null":  # Allow "null" origin for local development
                        HttpUrl.validate(origin)
                    validated_origins.append(origin)
                except Exception as e:
                    raise ValueError(f"Invalid origin URL: {origin}") from e
        
        self.config.allowed_origins = validated_origins

    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """
        Check if an origin is allowed based on the configuration.
        
        Args:
            origin: The origin to check
            
        Returns:
            bool: True if the origin is allowed, False otherwise
        """
        if not origin:
            return False

        # Check exact matches first
        if origin in self.config.allowed_origins:
            return True

        # Check pattern matches
        for allowed_origin in self.config.allowed_origins:
            if "*" in allowed_origin:
                pattern = allowed_origin.replace(".", "\\.").replace("*", ".*")
                if re.match(f"^{pattern}$", origin):
                    return True

        return False

def setup_cors(
    app: FastAPI,
    config: Optional[CORSConfig] = None
) -> None:
    """
    Configure CORS middleware for a FastAPI application.
    
    Args:
        app: The FastAPI application instance
        config: Optional CORS configuration. If not provided, uses restrictive defaults
    """
    if config is None:
        config = CORSConfig(
            allowed_origins=["http://localhost:3000"],  # Default to local development
            allow_credentials=True,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allowed_headers=["*"],
            expose_headers=[
                "Content-Length",
                "Content-Type",
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset"
            ],
            max_age=600
        )

    # Create CORS manager
    cors_manager = CORSConfigManager(config)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=config.allow_credentials,
        allow_methods=config.allowed_methods,
        allow_headers=config.allowed_headers,
        expose_headers=config.expose_headers,
        max_age=config.max_age
    )

    # Add CORS manager to app state for runtime checks
    app.state.cors_manager = cors_manager