from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

class CORSConfig:
    def __init__(self, allowed_origins: list, allow_credentials: bool = True,
                 allowed_methods: list = ["*"], allowed_headers: list = ["*"],
                 expose_headers: list = None):
        self.allowed_origins = allowed_origins
        self.allow_credentials = allow_credentials
        self.allowed_methods = allowed_methods
        self.allowed_headers = allowed_headers
        self.expose_headers = expose_headers or []

def setup_cors(app: FastAPI, config: CORSConfig):
    """Set up CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=config.allow_credentials,
        allow_methods=config.allowed_methods,
        allow_headers=config.allowed_headers,
        expose_headers=config.expose_headers,
    )