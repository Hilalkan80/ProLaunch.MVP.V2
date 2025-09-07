"""
Persistence Layer Configuration

Centralized configuration for database connections, pooling, and optimization settings.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class IsolationLevel(str, Enum):
    """Database transaction isolation levels."""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


class PoolStrategy(str, Enum):
    """Connection pool strategies."""
    QUEUE = "queue"  # QueuePool - Default, good for most cases
    NULL = "null"    # NullPool - No pooling, creates new connections
    STATIC = "static" # StaticPool - Fixed pool size, no overflow


@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration."""
    
    # Pool sizing
    pool_size: int = 20
    max_overflow: int = 40
    pool_timeout: float = 30.0
    pool_recycle: int = 3600  # Recycle connections after 1 hour
    
    # Pool behavior
    pool_pre_ping: bool = True  # Test connections before use
    pool_strategy: PoolStrategy = PoolStrategy.QUEUE
    echo_pool: bool = False  # Log pool checkouts/checkins
    
    # Connection settings
    connect_timeout: int = 10
    command_timeout: int = 60
    prepared_statement_cache_size: int = 0  # Disable for better pooling
    
    # Application identification
    application_name: str = "prolaunch_milestone_service"
    
    def to_connect_args(self) -> Dict[str, Any]:
        """Convert to SQLAlchemy connect_args."""
        return {
            "server_settings": {
                "application_name": self.application_name,
                "jit": "off",  # Disable JIT for consistent performance
            },
            "command_timeout": self.command_timeout,
            "prepared_statement_cache_size": self.prepared_statement_cache_size,
            "connect_timeout": self.connect_timeout,
        }


@dataclass
class TransactionConfig:
    """Transaction management configuration."""
    
    # Default isolation level
    default_isolation_level: IsolationLevel = IsolationLevel.READ_COMMITTED
    
    # Retry configuration
    max_retry_attempts: int = 3
    retry_backoff_base: float = 0.5  # Base delay in seconds
    retry_backoff_max: float = 10.0  # Max delay in seconds
    
    # Deadlock handling
    deadlock_retry_enabled: bool = True
    deadlock_max_retries: int = 5
    
    # Transaction timeout
    default_timeout_seconds: Optional[int] = 300  # 5 minutes
    
    # Savepoint configuration
    enable_savepoints: bool = True
    savepoint_prefix: str = "sp"


@dataclass
class QueryOptimizationConfig:
    """Query optimization settings."""
    
    # Query cache
    enable_query_cache: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    max_cache_entries: int = 1000
    cache_eviction_policy: str = "lru"  # least recently used
    
    # Query batching
    batch_size: int = 100
    enable_bulk_operations: bool = True
    
    # Read-ahead optimization
    enable_read_ahead: bool = True
    read_ahead_limit: int = 3  # Pre-fetch next 3 items
    
    # Query timeouts
    default_query_timeout: Optional[int] = 60  # seconds
    analytics_query_timeout: Optional[int] = 120  # seconds for heavy queries
    
    # Eager loading
    default_load_strategy: str = "selectinload"  # or "joinedload", "subqueryload"
    max_eager_load_depth: int = 3


@dataclass
class MonitoringConfig:
    """Performance monitoring configuration."""
    
    # Metrics collection
    enable_metrics: bool = True
    metrics_interval_seconds: int = 60
    
    # Slow query logging
    enable_slow_query_log: bool = True
    slow_query_threshold_ms: float = 1000.0  # 1 second
    
    # Connection pool monitoring
    monitor_pool_usage: bool = True
    pool_usage_warning_threshold: float = 0.8  # Warn at 80% usage
    
    # Transaction monitoring
    track_transaction_duration: bool = True
    long_transaction_threshold_seconds: int = 30
    
    # Health checks
    health_check_interval_seconds: int = 30
    health_check_timeout_seconds: int = 5


@dataclass
class MaintenanceConfig:
    """Database maintenance configuration."""
    
    # Stale session cleanup
    enable_stale_session_cleanup: bool = True
    stale_session_threshold_hours: int = 24
    cleanup_interval_hours: int = 6
    
    # Cache maintenance
    cache_cleanup_interval_minutes: int = 30
    
    # Connection pool maintenance
    pool_recycle_check_interval_minutes: int = 15
    
    # Vacuum settings (PostgreSQL specific)
    auto_vacuum_enabled: bool = True
    vacuum_schedule: str = "0 3 * * *"  # Daily at 3 AM
    
    # Archive settings
    enable_archiving: bool = True
    archive_completed_after_days: int = 90
    archive_table_suffix: str = "_archive"


@dataclass
class PersistenceConfig:
    """Complete persistence layer configuration."""
    
    # Database URL
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://localhost/prolaunch"
        )
    )
    
    # Component configurations
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    transactions: TransactionConfig = field(default_factory=TransactionConfig)
    query_optimization: QueryOptimizationConfig = field(default_factory=QueryOptimizationConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    maintenance: MaintenanceConfig = field(default_factory=MaintenanceConfig)
    
    # Environment-specific settings
    environment: str = field(default_factory=lambda: os.getenv("ENV", "development"))
    debug_mode: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    
    @classmethod
    def from_env(cls) -> "PersistenceConfig":
        """Create configuration from environment variables."""
        config = cls()
        
        # Override with environment variables
        if pool_size := os.getenv("DB_POOL_SIZE"):
            config.connection_pool.pool_size = int(pool_size)
        
        if max_overflow := os.getenv("DB_MAX_OVERFLOW"):
            config.connection_pool.max_overflow = int(max_overflow)
        
        if pool_timeout := os.getenv("DB_POOL_TIMEOUT"):
            config.connection_pool.pool_timeout = float(pool_timeout)
        
        if cache_ttl := os.getenv("DB_CACHE_TTL"):
            config.query_optimization.cache_ttl_seconds = int(cache_ttl)
        
        if slow_query_threshold := os.getenv("DB_SLOW_QUERY_THRESHOLD"):
            config.monitoring.slow_query_threshold_ms = float(slow_query_threshold)
        
        # Environment-specific adjustments
        if config.environment == "production":
            config.connection_pool.pool_size = 50
            config.connection_pool.max_overflow = 100
            config.monitoring.enable_slow_query_log = True
            config.maintenance.enable_stale_session_cleanup = True
        elif config.environment == "development":
            config.connection_pool.pool_size = 5
            config.connection_pool.max_overflow = 10
            config.connection_pool.echo_pool = config.debug_mode
            config.monitoring.slow_query_threshold_ms = 500
        
        return config
    
    def validate(self) -> bool:
        """Validate configuration settings."""
        errors = []
        
        # Validate pool settings
        if self.connection_pool.pool_size < 1:
            errors.append("Pool size must be at least 1")
        
        if self.connection_pool.max_overflow < 0:
            errors.append("Max overflow cannot be negative")
        
        if self.connection_pool.pool_timeout <= 0:
            errors.append("Pool timeout must be positive")
        
        # Validate retry settings
        if self.transactions.max_retry_attempts < 0:
            errors.append("Max retry attempts cannot be negative")
        
        # Validate cache settings
        if self.query_optimization.cache_ttl_seconds < 0:
            errors.append("Cache TTL cannot be negative")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
        
        return True


# Preset configurations for different scenarios
class PersistenceConfigPresets:
    """Preset configurations for common scenarios."""
    
    @staticmethod
    def high_throughput() -> PersistenceConfig:
        """Configuration optimized for high throughput."""
        config = PersistenceConfig()
        config.connection_pool.pool_size = 100
        config.connection_pool.max_overflow = 200
        config.query_optimization.enable_bulk_operations = True
        config.query_optimization.batch_size = 500
        config.transactions.default_isolation_level = IsolationLevel.READ_COMMITTED
        return config
    
    @staticmethod
    def low_latency() -> PersistenceConfig:
        """Configuration optimized for low latency."""
        config = PersistenceConfig()
        config.connection_pool.pool_size = 50
        config.connection_pool.pool_pre_ping = False  # Skip pre-ping for speed
        config.query_optimization.enable_query_cache = True
        config.query_optimization.cache_ttl_seconds = 600
        config.query_optimization.enable_read_ahead = True
        return config
    
    @staticmethod
    def high_consistency() -> PersistenceConfig:
        """Configuration optimized for data consistency."""
        config = PersistenceConfig()
        config.transactions.default_isolation_level = IsolationLevel.SERIALIZABLE
        config.transactions.enable_savepoints = True
        config.query_optimization.enable_query_cache = False  # Disable cache
        config.monitoring.enable_slow_query_log = True
        return config
    
    @staticmethod
    def development() -> PersistenceConfig:
        """Configuration for development environment."""
        config = PersistenceConfig()
        config.environment = "development"
        config.debug_mode = True
        config.connection_pool.pool_size = 5
        config.connection_pool.echo_pool = True
        config.monitoring.slow_query_threshold_ms = 100
        return config
    
    @staticmethod
    def testing() -> PersistenceConfig:
        """Configuration for testing."""
        config = PersistenceConfig()
        config.environment = "testing"
        config.connection_pool.pool_size = 2
        config.connection_pool.pool_strategy = PoolStrategy.STATIC
        config.transactions.max_retry_attempts = 1
        config.query_optimization.enable_query_cache = False
        return config


# Global configuration instance
_global_config: Optional[PersistenceConfig] = None


def get_config() -> PersistenceConfig:
    """Get the global persistence configuration."""
    global _global_config
    if _global_config is None:
        _global_config = PersistenceConfig.from_env()
        _global_config.validate()
    return _global_config


def set_config(config: PersistenceConfig) -> None:
    """Set the global persistence configuration."""
    global _global_config
    config.validate()
    _global_config = config


def reset_config() -> None:
    """Reset the global configuration."""
    global _global_config
    _global_config = None