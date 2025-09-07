"""
Redis Connection Manager

Provides robust Redis connection management with connection pooling,
health checks, and automatic failover capabilities.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from enum import Enum
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
from redis.asyncio.sentinel import Sentinel
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from ..config.settings import settings, RedisSettings

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Redis connection states"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class RedisConnectionManager:
    """
    Manages Redis connections with advanced features:
    - Connection pooling with automatic scaling
    - Health monitoring and auto-recovery
    - Read/write splitting for replicas
    - Sentinel support for high availability
    - Circuit breaker pattern
    - Connection warming
    """
    
    def __init__(
        self,
        config: Optional[RedisSettings] = None,
        enable_sentinel: bool = False,
        enable_cluster: bool = False,
        enable_read_replicas: bool = False
    ):
        """Initialize the connection manager"""
        self.config = config or settings.redis
        self.enable_sentinel = enable_sentinel
        self.enable_cluster = enable_cluster
        self.enable_read_replicas = enable_read_replicas
        
        # Connection pools
        self._master_pool: Optional[ConnectionPool] = None
        self._replica_pools: List[ConnectionPool] = []
        self._current_replica_index = 0
        
        # Connection state
        self._state = ConnectionState.DISCONNECTED
        self._last_health_check = datetime.utcnow()
        self._health_check_interval = 30  # seconds
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        
        # Circuit breaker
        self._circuit_failures = 0
        self._circuit_threshold = 10
        self._circuit_reset_time: Optional[datetime] = None
        self._circuit_timeout = 60  # seconds
        
        # Metrics
        self._metrics = {
            "connections_created": 0,
            "connections_closed": 0,
            "connection_errors": 0,
            "commands_executed": 0,
            "commands_failed": 0,
            "pool_size": 0,
            "active_connections": 0,
        }
        
        # Sentinel configuration
        self._sentinel: Optional[Sentinel] = None
        self._sentinel_masters: List[str] = []
        
        # Callbacks
        self._connection_callbacks: List[Callable] = []
        self._disconnection_callbacks: List[Callable] = []
    
    async def initialize(self) -> None:
        """
        Initialize connection pools and establish connections
        """
        try:
            if self.enable_sentinel:
                await self._initialize_sentinel()
            elif self.enable_cluster:
                await self._initialize_cluster()
            else:
                await self._initialize_standalone()
            
            # Start health monitoring
            asyncio.create_task(self._health_monitor())
            
            # Warm connections
            await self._warm_connections()
            
            self._state = ConnectionState.CONNECTED
            logger.info("Redis connection manager initialized successfully")
            
            # Execute connection callbacks
            for callback in self._connection_callbacks:
                asyncio.create_task(callback())
                
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection manager: {e}")
            self._state = ConnectionState.FAILED
            raise
    
    async def _initialize_standalone(self) -> None:
        """
        Initialize standalone Redis connection
        """
        # Create master pool
        self._master_pool = ConnectionPool(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password,
            db=self.config.db,
            decode_responses=self.config.decode_responses,
            max_connections=self.config.max_connections,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_keepalive=self.config.socket_keepalive,
            socket_keepalive_options=self.config.socket_keepalive_options,
            **self.config.connection_pool_kwargs
        )
        
        # Test connection
        async with self.get_connection() as conn:
            await conn.ping()
        
        self._metrics["connections_created"] += 1
        
        # Initialize read replicas if enabled
        if self.enable_read_replicas and self.config.read_replicas:
            await self._initialize_replicas()
    
    async def _initialize_replicas(self) -> None:
        """
        Initialize read replica connections
        """
        # This would typically read replica configurations from settings
        # For now, we'll use a simple approach
        replica_configs = [
            {"host": "replica1", "port": 6379},
            {"host": "replica2", "port": 6379},
        ]
        
        for replica_config in replica_configs:
            try:
                pool = ConnectionPool(
                    host=replica_config["host"],
                    port=replica_config["port"],
                    password=self.config.password,
                    db=self.config.db,
                    decode_responses=self.config.decode_responses,
                    max_connections=self.config.max_connections // 2,  # Half for replicas
                    **self.config.connection_pool_kwargs
                )
                
                # Test connection
                conn = redis.Redis(connection_pool=pool)
                await conn.ping()
                await conn.close()
                
                self._replica_pools.append(pool)
                logger.info(f"Initialized replica connection: {replica_config}")
                
            except Exception as e:
                logger.warning(f"Failed to initialize replica {replica_config}: {e}")
    
    async def _initialize_sentinel(self) -> None:
        """
        Initialize Redis Sentinel for high availability
        """
        sentinels = [
            ("sentinel1", 26379),
            ("sentinel2", 26379),
            ("sentinel3", 26379),
        ]
        
        self._sentinel = Sentinel(
            sentinels,
            socket_timeout=self.config.socket_timeout,
            decode_responses=self.config.decode_responses,
            password=self.config.password,
        )
        
        # Discover masters
        masters = await asyncio.to_thread(self._sentinel.discover_master, "mymaster")
        logger.info(f"Discovered Redis masters: {masters}")
        
        # Get master connection
        master = self._sentinel.master_for(
            "mymaster",
            socket_timeout=self.config.socket_timeout,
            password=self.config.password,
            db=self.config.db
        )
        
        # Test connection
        await master.ping()
        
        self._state = ConnectionState.CONNECTED
    
    async def _initialize_cluster(self) -> None:
        """
        Initialize Redis Cluster connection
        """
        from redis.asyncio.cluster import RedisCluster
        
        startup_nodes = [
            {"host": node.split(":")[0], "port": int(node.split(":")[1])}
            for node in self.config.cluster_nodes or []
        ]
        
        if not startup_nodes:
            startup_nodes = [
                {"host": self.config.host, "port": self.config.port}
            ]
        
        cluster = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=self.config.decode_responses,
            skip_full_coverage_check=True,
            password=self.config.password,
            max_connections_per_node=self.config.max_connections // len(startup_nodes),
        )
        
        # Test connection
        await cluster.ping()
        
        # Store as master pool (cluster handles routing internally)
        self._master_pool = cluster
        self._state = ConnectionState.CONNECTED
    
    @asynccontextmanager
    async def get_connection(self, readonly: bool = False):
        """
        Get a Redis connection from the pool
        
        Args:
            readonly: If True, attempts to use a read replica
        """
        if self._is_circuit_open():
            raise ConnectionError("Circuit breaker is open")
        
        conn = None
        try:
            if readonly and self._replica_pools:
                # Round-robin through replicas
                pool = self._get_next_replica_pool()
                conn = redis.Redis(connection_pool=pool)
            else:
                # Use master connection
                if not self._master_pool:
                    await self.initialize()
                
                if self.enable_cluster:
                    conn = self._master_pool  # Cluster client
                else:
                    conn = redis.Redis(connection_pool=self._master_pool)
            
            # Update metrics
            self._metrics["active_connections"] += 1
            
            yield conn
            
            # Reset circuit breaker on success
            self._circuit_failures = 0
            
        except (ConnectionError, TimeoutError) as e:
            self._handle_connection_error(e)
            raise
            
        except Exception as e:
            self._metrics["commands_failed"] += 1
            raise
            
        finally:
            if conn and not self.enable_cluster:
                await conn.close()
            self._metrics["active_connections"] -= 1
    
    def _get_next_replica_pool(self) -> ConnectionPool:
        """
        Get next replica pool using round-robin
        """
        pool = self._replica_pools[self._current_replica_index]
        self._current_replica_index = (self._current_replica_index + 1) % len(self._replica_pools)
        return pool
    
    async def execute_command(
        self,
        command: str,
        *args,
        readonly: bool = False,
        **kwargs
    ) -> Any:
        """
        Execute a Redis command with automatic retry and failover
        """
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with self.get_connection(readonly=readonly) as conn:
                    result = await getattr(conn, command)(*args, **kwargs)
                    self._metrics["commands_executed"] += 1
                    return result
                    
            except (ConnectionError, TimeoutError) as e:
                if attempt == max_retries - 1:
                    raise
                
                logger.warning(f"Command failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(retry_delay * (attempt + 1))
                
                # Try to reconnect
                if self._state == ConnectionState.DISCONNECTED:
                    await self._reconnect()
        
        raise ConnectionError(f"Failed to execute command after {max_retries} attempts")
    
    async def pipeline(self, transaction: bool = True):
        """
        Create a pipeline for batch operations
        """
        async with self.get_connection() as conn:
            return conn.pipeline(transaction=transaction)
    
    async def _warm_connections(self) -> None:
        """
        Pre-establish connections to reduce latency
        """
        warm_count = min(5, self.config.max_connections // 2)
        
        tasks = []
        for _ in range(warm_count):
            tasks.append(self._warm_single_connection())
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Warmed {warm_count} connections")
    
    async def _warm_single_connection(self) -> None:
        """
        Warm a single connection
        """
        try:
            async with self.get_connection() as conn:
                await conn.ping()
        except Exception as e:
            logger.warning(f"Failed to warm connection: {e}")
    
    async def _health_monitor(self) -> None:
        """
        Monitor connection health and auto-recover
        """
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if self._state == ConnectionState.CONNECTED:
                    # Perform health check
                    async with self.get_connection() as conn:
                        await conn.ping()
                    
                    self._last_health_check = datetime.utcnow()
                    
                    # Check pool statistics
                    if self._master_pool and hasattr(self._master_pool, 'connection_kwargs'):
                        pool_stats = self._get_pool_stats()
                        self._metrics["pool_size"] = pool_stats.get("created_connections", 0)
                
                elif self._state == ConnectionState.DISCONNECTED:
                    # Attempt reconnection
                    await self._reconnect()
                    
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                self._state = ConnectionState.DISCONNECTED
    
    async def _reconnect(self) -> None:
        """
        Attempt to reconnect to Redis
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self._state = ConnectionState.FAILED
            logger.error("Max reconnection attempts reached")
            return
        
        self._state = ConnectionState.RECONNECTING
        self._reconnect_attempts += 1
        
        try:
            logger.info(f"Attempting reconnection (attempt {self._reconnect_attempts})")
            
            # Close existing pools
            await self.close()
            
            # Re-initialize
            await self.initialize()
            
            self._state = ConnectionState.CONNECTED
            self._reconnect_attempts = 0
            logger.info("Successfully reconnected to Redis")
            
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            self._state = ConnectionState.DISCONNECTED
            
            # Exponential backoff
            await asyncio.sleep(2 ** self._reconnect_attempts)
    
    def _handle_connection_error(self, error: Exception) -> None:
        """
        Handle connection errors and update circuit breaker
        """
        self._metrics["connection_errors"] += 1
        self._circuit_failures += 1
        
        if self._circuit_failures >= self._circuit_threshold:
            self._circuit_reset_time = datetime.utcnow() + timedelta(seconds=self._circuit_timeout)
            logger.error(f"Circuit breaker opened due to {self._circuit_failures} failures")
        
        # Update connection state
        if isinstance(error, ConnectionError):
            self._state = ConnectionState.DISCONNECTED
            
            # Execute disconnection callbacks
            for callback in self._disconnection_callbacks:
                asyncio.create_task(callback())
    
    def _is_circuit_open(self) -> bool:
        """
        Check if circuit breaker is open
        """
        if self._circuit_failures < self._circuit_threshold:
            return False
        
        if self._circuit_reset_time and datetime.utcnow() > self._circuit_reset_time:
            # Reset circuit breaker
            self._circuit_failures = 0
            self._circuit_reset_time = None
            logger.info("Circuit breaker reset")
            return False
        
        return True
    
    def _get_pool_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics
        """
        if not self._master_pool:
            return {}
        
        stats = {
            "created_connections": getattr(self._master_pool, "created_connections", 0),
            "available_connections": len(getattr(self._master_pool, "_available_connections", [])),
            "in_use_connections": len(getattr(self._master_pool, "_in_use_connections", set())),
        }
        
        return stats
    
    def register_connection_callback(self, callback: Callable) -> None:
        """
        Register callback for connection events
        """
        self._connection_callbacks.append(callback)
    
    def register_disconnection_callback(self, callback: Callable) -> None:
        """
        Register callback for disconnection events
        """
        self._disconnection_callbacks.append(callback)
    
    async def close(self) -> None:
        """
        Close all connections and clean up resources
        """
        try:
            # Close master pool
            if self._master_pool:
                if self.enable_cluster:
                    await self._master_pool.close()
                else:
                    await self._master_pool.disconnect()
                self._master_pool = None
            
            # Close replica pools
            for pool in self._replica_pools:
                await pool.disconnect()
            self._replica_pools.clear()
            
            # Close sentinel
            if self._sentinel:
                # Sentinel cleanup
                pass
            
            self._state = ConnectionState.DISCONNECTED
            self._metrics["connections_closed"] += 1
            
            logger.info("Redis connection manager closed")
            
        except Exception as e:
            logger.error(f"Error closing connections: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get connection manager metrics
        """
        pool_stats = self._get_pool_stats() if self._master_pool else {}
        
        return {
            **self._metrics,
            **pool_stats,
            "state": self._state.value,
            "circuit_breaker_failures": self._circuit_failures,
            "circuit_breaker_open": self._is_circuit_open(),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "reconnect_attempts": self._reconnect_attempts,
            "replica_pools": len(self._replica_pools),
        }
    
    async def flush_db(self, db: Optional[int] = None) -> None:
        """
        Flush database (use with caution)
        """
        async with self.get_connection() as conn:
            if db is not None:
                await conn.select(db)
            await conn.flushdb()
            logger.warning(f"Flushed database {db or self.config.db}")
    
    async def get_info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Redis server information
        """
        async with self.get_connection() as conn:
            info = await conn.info(section or "all")
            return info


# Singleton instance
_connection_manager: Optional[RedisConnectionManager] = None


async def get_redis_connection_manager() -> RedisConnectionManager:
    """
    Get or create the Redis connection manager singleton
    """
    global _connection_manager
    
    if _connection_manager is None:
        _connection_manager = RedisConnectionManager(
            enable_sentinel=settings.redis.enable_cluster,
            enable_cluster=settings.redis.enable_cluster,
            enable_read_replicas=settings.redis.read_replicas
        )
        await _connection_manager.initialize()
    
    return _connection_manager


async def close_redis_connection_manager() -> None:
    """
    Close the Redis connection manager
    """
    global _connection_manager
    
    if _connection_manager:
        await _connection_manager.close()
        _connection_manager = None