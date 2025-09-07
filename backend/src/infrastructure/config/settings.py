"""
Infrastructure Settings Configuration

This module manages all infrastructure configuration settings including Redis MCP,
MinIO/S3, and other infrastructure components.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class RedisSettings:
    """Redis configuration settings"""
    host: str
    port: int
    password: Optional[str]
    db: int
    decode_responses: bool
    max_connections: int
    socket_timeout: int
    socket_connect_timeout: int
    socket_keepalive: bool
    socket_keepalive_options: Dict[str, int]
    connection_pool_kwargs: Dict[str, Any]
    ssl: bool
    ssl_certfile: Optional[str]
    ssl_keyfile: Optional[str]
    ssl_ca_certs: Optional[str]
    
    # MCP specific settings
    mcp_enabled: bool
    mcp_endpoint: Optional[str]
    mcp_token: Optional[str]
    
    # Cache TTL settings
    default_ttl: int
    session_ttl: int
    api_cache_ttl: int
    rate_limit_ttl: int
    
    # Performance settings
    enable_cluster: bool
    cluster_nodes: Optional[list]
    read_replicas: bool


@dataclass
class MinIOSettings:
    """MinIO/S3 configuration settings"""
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool
    region: Optional[str]
    bucket_name: str
    
    # Security settings
    enable_encryption: bool
    encryption_key: Optional[str]
    enable_versioning: bool
    enable_lifecycle: bool
    
    # Performance settings
    multipart_threshold: int
    multipart_chunksize: int
    max_concurrency: int
    num_download_attempts: int
    
    # URL settings
    presigned_url_expiry: int
    public_url_base: Optional[str]


@dataclass
class CacheSettings:
    """Cache layer configuration"""
    enable_memory_cache: bool
    memory_cache_max_size: int
    enable_redis_cache: bool
    enable_distributed_cache: bool
    
    # Cache policies by data type
    cache_policies: Dict[str, Dict[str, Any]]
    
    # Performance settings
    cache_warmup: bool
    cache_preload: bool
    cache_compression: bool
    
    # Monitoring
    enable_metrics: bool
    metrics_interval: int


class Settings:
    """Main settings class for infrastructure configuration"""
    
    def __init__(self):
        self.env = self._get_environment()
        self.redis = self._load_redis_settings()
        self.minio = self._load_minio_settings()
        self.cache = self._load_cache_settings()
        
        # Security settings
        self.enable_encryption = self._get_bool_env("ENABLE_ENCRYPTION", True)
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        self.jwt_secret = os.getenv("JWT_SECRET")
        self.api_key = os.getenv("API_KEY")
        
        # Performance settings
        self.max_workers = int(os.getenv("MAX_WORKERS", "10"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.batch_size = int(os.getenv("BATCH_SIZE", "100"))
    
    def _get_environment(self) -> Environment:
        """Get current environment"""
        env = os.getenv("ENVIRONMENT", "development").lower()
        return Environment(env)
    
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable"""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")
    
    def _load_redis_settings(self) -> RedisSettings:
        """Load Redis configuration from environment"""
        return RedisSettings(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
            db=int(os.getenv("REDIS_DB", "0")),
            decode_responses=self._get_bool_env("REDIS_DECODE_RESPONSES", True),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
            socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
            socket_connect_timeout=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),
            socket_keepalive=self._get_bool_env("REDIS_SOCKET_KEEPALIVE", True),
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 1,  # TCP_KEEPINTVL
                3: 3,  # TCP_KEEPCNT
            },
            connection_pool_kwargs={
                "max_connections": int(os.getenv("REDIS_POOL_MAX_CONNECTIONS", "50")),
                "retry_on_timeout": self._get_bool_env("REDIS_RETRY_ON_TIMEOUT", True),
                "health_check_interval": int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30")),
            },
            ssl=self._get_bool_env("REDIS_SSL", False),
            ssl_certfile=os.getenv("REDIS_SSL_CERTFILE"),
            ssl_keyfile=os.getenv("REDIS_SSL_KEYFILE"),
            ssl_ca_certs=os.getenv("REDIS_SSL_CA_CERTS"),
            
            # MCP specific
            mcp_enabled=self._get_bool_env("REDIS_MCP_ENABLED", True),
            mcp_endpoint=os.getenv("REDIS_MCP_ENDPOINT"),
            mcp_token=os.getenv("REDIS_MCP_TOKEN"),
            
            # TTL settings
            default_ttl=int(os.getenv("REDIS_DEFAULT_TTL", "3600")),
            session_ttl=int(os.getenv("REDIS_SESSION_TTL", "1800")),
            api_cache_ttl=int(os.getenv("REDIS_API_CACHE_TTL", "900")),
            rate_limit_ttl=int(os.getenv("REDIS_RATE_LIMIT_TTL", "60")),
            
            # Performance
            enable_cluster=self._get_bool_env("REDIS_ENABLE_CLUSTER", False),
            cluster_nodes=os.getenv("REDIS_CLUSTER_NODES", "").split(",") if os.getenv("REDIS_CLUSTER_NODES") else None,
            read_replicas=self._get_bool_env("REDIS_READ_REPLICAS", False),
        )
    
    def _load_minio_settings(self) -> MinIOSettings:
        """Load MinIO/S3 configuration from environment"""
        return MinIOSettings(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
            secure=self._get_bool_env("MINIO_SECURE", False),
            region=os.getenv("MINIO_REGION", "us-east-1"),
            bucket_name=os.getenv("MINIO_BUCKET_NAME", "prolaunch-documents"),
            
            # Security
            enable_encryption=self._get_bool_env("MINIO_ENABLE_ENCRYPTION", True),
            encryption_key=os.getenv("MINIO_ENCRYPTION_KEY"),
            enable_versioning=self._get_bool_env("MINIO_ENABLE_VERSIONING", True),
            enable_lifecycle=self._get_bool_env("MINIO_ENABLE_LIFECYCLE", True),
            
            # Performance
            multipart_threshold=int(os.getenv("MINIO_MULTIPART_THRESHOLD", str(8 * 1024 * 1024))),
            multipart_chunksize=int(os.getenv("MINIO_MULTIPART_CHUNKSIZE", str(8 * 1024 * 1024))),
            max_concurrency=int(os.getenv("MINIO_MAX_CONCURRENCY", "10")),
            num_download_attempts=int(os.getenv("MINIO_DOWNLOAD_ATTEMPTS", "3")),
            
            # URL settings
            presigned_url_expiry=int(os.getenv("MINIO_PRESIGNED_URL_EXPIRY", "3600")),
            public_url_base=os.getenv("MINIO_PUBLIC_URL_BASE"),
        )
    
    def _load_cache_settings(self) -> CacheSettings:
        """Load cache configuration from environment"""
        return CacheSettings(
            enable_memory_cache=self._get_bool_env("ENABLE_MEMORY_CACHE", True),
            memory_cache_max_size=int(os.getenv("MEMORY_CACHE_MAX_SIZE", "1000")),
            enable_redis_cache=self._get_bool_env("ENABLE_REDIS_CACHE", True),
            enable_distributed_cache=self._get_bool_env("ENABLE_DISTRIBUTED_CACHE", False),
            
            # Cache policies
            cache_policies={
                "user_profiles": {
                    "ttl": 3600,
                    "layer": "redis",
                    "compress": False,
                    "priority": "high"
                },
                "milestone_templates": {
                    "ttl": 86400,
                    "layer": "memory",
                    "compress": True,
                    "priority": "low"
                },
                "market_research": {
                    "ttl": 1800,
                    "layer": "redis",
                    "compress": True,
                    "priority": "medium"
                },
                "supplier_data": {
                    "ttl": 7200,
                    "layer": "redis",
                    "compress": True,
                    "priority": "medium"
                },
                "chat_context": {
                    "ttl": 1800,
                    "layer": "redis",
                    "compress": False,
                    "priority": "high"
                },
                "api_responses": {
                    "ttl": 900,
                    "layer": "redis",
                    "compress": True,
                    "priority": "low"
                },
                "documents": {
                    "ttl": 3600,
                    "layer": "redis",
                    "compress": False,
                    "priority": "medium"
                }
            },
            
            # Performance
            cache_warmup=self._get_bool_env("CACHE_WARMUP", False),
            cache_preload=self._get_bool_env("CACHE_PRELOAD", False),
            cache_compression=self._get_bool_env("CACHE_COMPRESSION", True),
            
            # Monitoring
            enable_metrics=self._get_bool_env("CACHE_ENABLE_METRICS", True),
            metrics_interval=int(os.getenv("CACHE_METRICS_INTERVAL", "60")),
        )
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis.password:
            return f"redis://:{self.redis.password}@{self.redis.host}:{self.redis.port}/{self.redis.db}"
        return f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"
    
    def get_minio_url(self) -> str:
        """Get MinIO/S3 endpoint URL"""
        protocol = "https" if self.minio.secure else "http"
        return f"{protocol}://{self.minio.endpoint}"


# Singleton instance
settings = Settings()