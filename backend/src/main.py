from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from core.security_headers import setup_security_headers
from core.rate_limiter import setup_rate_limiter
from core.data_encryption import setup_encryption
from core.gdpr_compliance import setup_gdpr_compliance
from core.cors_config import setup_cors, CORSConfig
from services.chat import connection_manager
from models.base import init_db, close_db
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events.
    Initialize resources on startup and cleanup on shutdown.
    """
    # Startup
    await init_db()  # Initialize database tables
    await connection_manager.initialize()  # Initialize WebSocket manager
    
    yield
    
    # Shutdown
    await connection_manager.shutdown()  # Cleanup WebSocket connections
    await close_db()  # Close database connections


app = FastAPI(
    title="ProLaunch API",
    version="2.0.0",
    description="ProLaunch MVP API with real-time chat support",
    lifespan=lifespan
)

# Load configuration from environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # Generate and set this in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# Set up security components
setup_security_headers(
    app,
    csp_report_uri="/security/csp-report",
    hsts_max_age=31536000  # 1 year
)

setup_rate_limiter(
    app,
    redis_url=REDIS_URL,
    auth_limits={
        "auth": (5, 60),        # 5 requests per minute
        "default": (100, 60),   # 100 requests per minute
        "websocket": (10, 60),  # 10 connections per minute
        "export": (10, 3600)    # 10 requests per hour
    }
)

# Set up CORS
cors_config = CORSConfig(
    allowed_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allowed_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allowed_headers=["*"],
    expose_headers=[
        "Content-Length",
        "Content-Type",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset"
    ]
)
setup_cors(app, cors_config)

# Initialize encryption
encryption = setup_encryption(ENCRYPTION_KEY)

# Set up GDPR compliance (requires your storage backend)
# gdpr = setup_gdpr_compliance(encryption, your_storage_backend)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/security/csp-report")
async def csp_report(request: Request):
    """Endpoint for CSP violation reports."""
    report = await request.json()
    # TODO: Log CSP violation
    return {"status": "received"}

# Import and include routers
from api.v1 import websocket_chat, citations, m0_feasibility
from api import context
from api import llama_index

# Include WebSocket chat router
app.include_router(websocket_chat.router, prefix="/api/v1")

# Include Context Management router
app.include_router(context.router)

# Include LlamaIndex router
app.include_router(llama_index.router)

# Include Citation System router
app.include_router(citations.router)

# Include M0 Feasibility router
app.include_router(m0_feasibility.router)

# Example protected endpoint
@app.get("/api/protected")
async def protected_route(request: Request):
    """Example of a protected endpoint with security headers and rate limiting."""
    return {
        "message": "This is a protected endpoint",
        "client": request.client.host,
        "protocol": request.headers.get("x-forwarded-proto", request.url.scheme)
    }

# Chat health check endpoint
@app.get("/api/v1/chat/health")
async def chat_health():
    """Check chat system health."""
    active_connections = sum(
        len(conns) for conns in connection_manager.active_connections.values()
    )
    return {
        "status": "healthy",
        "active_connections": active_connections,
        "redis_connected": connection_manager.redis_client is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        ssl_keyfile=os.getenv("SSL_KEYFILE"),
        ssl_certfile=os.getenv("SSL_CERTFILE")
    )