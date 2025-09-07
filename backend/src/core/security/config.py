"""
Security configuration and initialization module.
Sets up and configures all security components for the chat system.
"""
import os
import logging
from typing import Optional
from datetime import datetime
from redis.asyncio import Redis

from .sentry_security import initialize_security_monitoring, SentrySecurityMonitor
from .rate_limiter import RedisRateLimiter
from .websocket_security import WebSocketAuthenticator, IPWhitelist
from ..config import settings

logger = logging.getLogger(__name__)

class SecurityConfig:
    """Security configuration settings"""
    
    # Sentry Configuration
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    SENTRY_SAMPLE_RATE = float(os.getenv("SENTRY_SAMPLE_RATE", "1.0"))
    
    # Rate Limiting Configuration
    ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
    RATE_LIMIT_STRICT_MODE = os.getenv("RATE_LIMIT_STRICT_MODE", "false").lower() == "true"
    
    # Content Security Configuration
    ENABLE_CONTENT_VALIDATION = os.getenv("ENABLE_CONTENT_VALIDATION", "true").lower() == "true"
    CONTENT_SECURITY_STRICT_MODE = os.getenv("CONTENT_SECURITY_STRICT_MODE", "true").lower() == "true"
    MAX_MESSAGE_SIZE = int(os.getenv("MAX_MESSAGE_SIZE", "4000"))
    
    # File Upload Security
    ENABLE_FILE_UPLOADS = os.getenv("ENABLE_FILE_UPLOADS", "true").lower() == "true"
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    UPLOAD_SCAN_ENABLED = os.getenv("UPLOAD_SCAN_ENABLED", "true").lower() == "true"
    
    # WebSocket Security
    WS_CONNECTION_TIMEOUT = int(os.getenv("WS_CONNECTION_TIMEOUT", "3600"))  # 1 hour
    MAX_CONNECTIONS_PER_USER = int(os.getenv("MAX_CONNECTIONS_PER_USER", "5"))
    MAX_CONNECTIONS_PER_IP = int(os.getenv("MAX_CONNECTIONS_PER_IP", "20"))
    
    # IP Security
    ENABLE_IP_WHITELIST = os.getenv("ENABLE_IP_WHITELIST", "false").lower() == "true"
    ENABLE_IP_BLACKLIST = os.getenv("ENABLE_IP_BLACKLIST", "true").lower() == "true"
    
    # Security Monitoring
    ENABLE_SECURITY_MONITORING = os.getenv("ENABLE_SECURITY_MONITORING", "true").lower() == "true"
    SECURITY_ALERT_THRESHOLD = os.getenv("SECURITY_ALERT_THRESHOLD", "warning").lower()

class SecurityManager:
    """Manages all security components and their initialization"""
    
    def __init__(self):
        self.config = SecurityConfig()
        self.sentry_monitor: Optional[SentrySecurityMonitor] = None
        self.rate_limiter: Optional[RedisRateLimiter] = None
        self.ws_authenticator: Optional[WebSocketAuthenticator] = None
        self.ip_whitelist: Optional[IPWhitelist] = None
        self._initialized = False
    
    async def initialize(self, redis: Redis) -> bool:
        """
        Initialize all security components.
        
        Args:
            redis: Redis instance
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Initialize Sentry monitoring if configured
            if self.config.SENTRY_DSN and self.config.ENABLE_SECURITY_MONITORING:
                self.sentry_monitor = initialize_security_monitoring(
                    dsn=self.config.SENTRY_DSN,
                    environment=self.config.SENTRY_ENVIRONMENT,
                    sample_rate=self.config.SENTRY_SAMPLE_RATE
                )
                logger.info("Sentry security monitoring initialized")
            
            # Initialize rate limiter
            if self.config.ENABLE_RATE_LIMITING:
                self.rate_limiter = RedisRateLimiter(redis)
                logger.info("Redis rate limiter initialized")
            
            # Initialize WebSocket authenticator
            if hasattr(settings, 'SECRET_KEY'):
                self.ws_authenticator = WebSocketAuthenticator(settings.SECRET_KEY)
                logger.info("WebSocket authenticator initialized")
            
            # Initialize IP security
            if self.config.ENABLE_IP_WHITELIST or self.config.ENABLE_IP_BLACKLIST:
                self.ip_whitelist = IPWhitelist(redis)
                await self._setup_default_ip_rules()
                logger.info("IP security initialized")
            
            # Validate security configuration
            await self._validate_security_config()
            
            self._initialized = True
            logger.info("Security manager initialization completed successfully")
            
            # Log security status
            if self.sentry_monitor:
                self.sentry_monitor.add_security_breadcrumb(
                    "Security manager initialized",
                    category="security",
                    data=self._get_security_status()
                )
            
            return True
            
        except Exception as e:\n            logger.error(f\"Security manager initialization failed: {str(e)}\")\n            if self.sentry_monitor:\n                self.sentry_monitor.track_security_event(\n                    \"security_init_failure\",\n                    details={\"error\": str(e)}\n                )\n            return False\n    \n    async def _setup_default_ip_rules(self):\n        \"\"\"Set up default IP whitelist/blacklist rules\"\"\"\n        if not self.ip_whitelist:\n            return\n        \n        # Add localhost to whitelist by default in development\n        if self.config.SENTRY_ENVIRONMENT == \"development\":\n            await self.ip_whitelist.add_to_whitelist(\"127.0.0.1\")\n            await self.ip_whitelist.add_to_whitelist(\"::1\")\n        \n        # Add known malicious IPs to blacklist\n        known_malicious_ips = os.getenv(\"BLACKLIST_IPS\", \"\").split(\",\")\n        for ip in known_malicious_ips:\n            if ip.strip():\n                await self.ip_whitelist.add_to_blacklist(ip.strip())\n    \n    async def _validate_security_config(self):\n        \"\"\"Validate security configuration\"\"\"\n        issues = []\n        \n        # Check critical security settings\n        if not hasattr(settings, 'SECRET_KEY') or len(settings.SECRET_KEY) < 32:\n            issues.append(\"SECRET_KEY is too short or missing\")\n        \n        if self.config.SENTRY_ENVIRONMENT == \"production\":\n            if not self.config.SENTRY_DSN:\n                issues.append(\"Sentry DSN not configured for production\")\n            \n            if not self.config.ENABLE_RATE_LIMITING:\n                issues.append(\"Rate limiting disabled in production\")\n            \n            if not self.config.ENABLE_CONTENT_VALIDATION:\n                issues.append(\"Content validation disabled in production\")\n        \n        if issues:\n            error_msg = \"Security configuration issues: \" + \"; \".join(issues)\n            logger.error(error_msg)\n            \n            if self.sentry_monitor:\n                self.sentry_monitor.track_security_event(\n                    \"security_config_issues\",\n                    details={\"issues\": issues}\n                )\n            \n            if self.config.SENTRY_ENVIRONMENT == \"production\":\n                raise ValueError(error_msg)\n        \n        logger.info(\"Security configuration validation passed\")\n    \n    def _get_security_status(self) -> dict:\n        \"\"\"Get current security status for monitoring\"\"\"\n        return {\n            \"initialized\": self._initialized,\n            \"sentry_enabled\": self.sentry_monitor is not None,\n            \"rate_limiting_enabled\": self.rate_limiter is not None,\n            \"ws_auth_enabled\": self.ws_authenticator is not None,\n            \"ip_security_enabled\": self.ip_whitelist is not None,\n            \"environment\": self.config.SENTRY_ENVIRONMENT,\n            \"strict_mode\": {\n                \"rate_limit\": self.config.RATE_LIMIT_STRICT_MODE,\n                \"content_security\": self.config.CONTENT_SECURITY_STRICT_MODE\n            }\n        }\n    \n    def get_rate_limiter(self) -> Optional[RedisRateLimiter]:\n        \"\"\"Get rate limiter instance\"\"\"\n        return self.rate_limiter\n    \n    def get_sentry_monitor(self) -> Optional[SentrySecurityMonitor]:\n        \"\"\"Get Sentry monitor instance\"\"\"\n        return self.sentry_monitor\n    \n    def get_ws_authenticator(self) -> Optional[WebSocketAuthenticator]:\n        \"\"\"Get WebSocket authenticator instance\"\"\"\n        return self.ws_authenticator\n    \n    def get_ip_whitelist(self) -> Optional[IPWhitelist]:\n        \"\"\"Get IP whitelist instance\"\"\"\n        return self.ip_whitelist\n    \n    def is_initialized(self) -> bool:\n        \"\"\"Check if security manager is initialized\"\"\"\n        return self._initialized\n    \n    async def shutdown(self):\n        \"\"\"Shutdown security manager and cleanup resources\"\"\"\n        try:\n            if self.sentry_monitor:\n                logger.info(\"Shutting down Sentry monitoring\")\n                # Sentry shutdown is handled by the SDK\n            \n            if self.rate_limiter:\n                logger.info(\"Shutting down rate limiter\")\n                # Redis connections are managed externally\n            \n            self._initialized = False\n            logger.info(\"Security manager shutdown completed\")\n            \n        except Exception as e:\n            logger.error(f\"Error during security manager shutdown: {str(e)}\")\n    \n    async def health_check(self) -> dict:\n        \"\"\"Perform security health check\"\"\"\n        health = {\n            \"status\": \"healthy\",\n            \"components\": {},\n            \"timestamp\": datetime.utcnow().isoformat()\n        }\n        \n        try:\n            # Check rate limiter\n            if self.rate_limiter:\n                # Try a simple Redis operation\n                test_key = \"health_check_test\"\n                await self.rate_limiter.redis.setex(test_key, 1, \"test\")\n                await self.rate_limiter.redis.delete(test_key)\n                health[\"components\"][\"rate_limiter\"] = \"healthy\"\n            \n            # Check Sentry\n            if self.sentry_monitor:\n                health[\"components\"][\"sentry_monitor\"] = \"healthy\"\n            \n            # Check other components\n            if self.ws_authenticator:\n                health[\"components\"][\"ws_authenticator\"] = \"healthy\"\n            \n            if self.ip_whitelist:\n                health[\"components\"][\"ip_security\"] = \"healthy\"\n            \n        except Exception as e:\n            health[\"status\"] = \"unhealthy\"\n            health[\"error\"] = str(e)\n            logger.error(f\"Security health check failed: {str(e)}\")\n        \n        return health\n\n# Global security manager instance\nsecurity_manager = SecurityManager()\n\nasync def get_security_manager() -> SecurityManager:\n    \"\"\"Get the global security manager instance\"\"\"\n    return security_manager\n\nasync def initialize_security(redis: Redis) -> bool:\n    \"\"\"Initialize security components\"\"\"\n    return await security_manager.initialize(redis)\n\nasync def shutdown_security():\n    \"\"\"Shutdown security components\"\"\"\n    await security_manager.shutdown()