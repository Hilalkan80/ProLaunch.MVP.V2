"""
Multi-layer Cache Manager

This module implements a sophisticated multi-layer caching strategy with
memory cache (L1) and Redis cache (L2) for optimal performance.
"""

import asyncio
import json
import logging
import pickle
import zlib
from typing import Optional, Dict, Any, List, Callable, Union, TypeVar, Generic
from datetime import datetime, timedelta
from functools import wraps
import hashlib
from enum import Enum
from collections import OrderedDict
import sys

from ..redis.redis_mcp import RedisMCPClient, redis_mcp_client
from ..config.settings import settings, CacheSettings


logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheLayer(Enum):
    """Cache layer types"""
    MEMORY = "memory"
    REDIS = "redis"
    BOTH = "both"


class CachePriority(Enum):
    """Cache priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class LRUCache(Generic[T]):
    """Thread-safe LRU cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, Tuple[T, datetime, int]] = OrderedDict()
        self.lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0
    
    async def get(self, key: str) -> Optional[T]:
        """Get value from cache"""
        async with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                value, expiry, _ = self.cache.pop(key)
                
                # Check expiry
                if expiry and datetime.utcnow() > expiry:
                    self.misses += 1
                    return None
                
                self.cache[key] = (value, expiry, self.cache[key][2] + 1)
                self.hits += 1
                return value
            
            self.misses += 1
            return None
    
    async def set(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None
    ) -> None:
        """Set value in cache"""
        async with self.lock:
            # Calculate expiry
            expiry = None
            if ttl:
                expiry = datetime.utcnow() + timedelta(seconds=ttl)
            
            # Remove if exists to update position
            if key in self.cache:
                self.cache.pop(key)
            
            # Add to end
            self.cache[key] = (value, expiry, 0)
            
            # Evict if necessary
            while len(self.cache) > self.max_size:
                # Remove least recently used
                self.cache.popitem(last=False)
    
    async def delete(self, key: str) -> bool:
        """Delete from cache"""
        async with self.lock:
            if key in self.cache:
                self.cache.pop(key)
                return True
            return False
    
    async def clear(self) -> None:
        """Clear entire cache"""
        async with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "total_requests": total_requests
            }


class CacheManager:
    """
    Multi-layer cache manager with intelligent routing and optimization.
    Implements L1 (memory) and L2 (Redis) caching with automatic promotion/demotion.
    """
    
    def __init__(
        self,
        cache_settings: Optional[CacheSettings] = None,
        redis_client: Optional[RedisMCPClient] = None
    ):
        """Initialize cache manager"""
        self.settings = cache_settings or settings.cache
        self.redis_client = redis_client or redis_mcp_client
        
        # Initialize memory cache
        self.memory_cache = LRUCache(max_size=self.settings.memory_cache_max_size)
        
        # Cache statistics
        self.stats = {
            "requests": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "misses": 0,
            "errors": 0
        }
        
        # Background tasks
        self._warmup_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize cache manager"""
        try:
            # Connect Redis client
            await self.redis_client.connect()
            
            # Start warmup if enabled
            if self.settings.cache_warmup:
                self._warmup_task = asyncio.create_task(self._warmup_cache())
            
            # Start metrics collection if enabled
            if self.settings.enable_metrics:
                self._metrics_task = asyncio.create_task(self._collect_metrics())
            
            logger.info("Cache manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            raise
    
    async def get(
        self,
        key: str,
        data_type: Optional[str] = None,
        default: Any = None
    ) -> Any:
        """
        Get value from cache with intelligent layer selection.
        Checks L1 (memory) first, then L2 (Redis).
        """
        self.stats["requests"] += 1
        
        try:
            # Determine cache policy
            policy = self._get_cache_policy(data_type)
            
            # Check L1 (memory cache)
            if self.settings.enable_memory_cache and policy.get("layer") in ["memory", "both"]:
                value = await self.memory_cache.get(key)
                if value is not None:
                    self.stats["memory_hits"] += 1
                    
                    # Decompress if needed
                    if policy.get("compress") and isinstance(value, bytes):
                        value = self._decompress_value(value)
                    
                    return value
            
            # Check L2 (Redis cache)
            if self.settings.enable_redis_cache and policy.get("layer") in ["redis", "both"]:
                value = await self.redis_client.get(key, default)
                
                if value != default:
                    self.stats["redis_hits"] += 1
                    
                    # Decompress if needed
                    if policy.get("compress") and isinstance(value, str):
                        value = self._decompress_value(value)
                    
                    # Promote to L1 if policy allows
                    if policy.get("layer") == "both" and self.settings.enable_memory_cache:
                        await self.memory_cache.set(key, value, policy.get("ttl"))
                    
                    return value
            
            self.stats["misses"] += 1
            return default
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        data_type: Optional[str] = None
    ) -> bool:
        """
        Set value in cache with intelligent layer selection.
        May set in L1, L2, or both based on policy.
        """
        try:
            # Determine cache policy
            policy = self._get_cache_policy(data_type)
            ttl = ttl or policy.get("ttl", self.settings.cache_policies.get("default", {}).get("ttl", 3600))
            
            # Compress if needed
            if policy.get("compress"):
                value = self._compress_value(value)
            
            success = True
            
            # Set in L1 (memory cache)
            if self.settings.enable_memory_cache and policy.get("layer") in ["memory", "both"]:
                await self.memory_cache.set(key, value, ttl)
            
            # Set in L2 (Redis cache)
            if self.settings.enable_redis_cache and policy.get("layer") in ["redis", "both"]:
                success = await self.redis_client.set(key, value, ttl)
            
            return success
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from all cache layers"""
        count = 0
        
        try:
            # Delete from L1
            if self.settings.enable_memory_cache:
                for key in keys:
                    if await self.memory_cache.delete(key):
                        count += 1
            
            # Delete from L2
            if self.settings.enable_redis_cache:
                redis_count = await self.redis_client.delete(*keys)
                count = max(count, redis_count)
            
            return count
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Cache delete error for keys {keys}: {e}")
            return 0
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        count = 0
        
        try:
            # Clear from memory cache (simple pattern matching)
            if self.settings.enable_memory_cache:
                async with self.memory_cache.lock:
                    keys_to_delete = [
                        key for key in self.memory_cache.cache.keys()
                        if self._matches_pattern(key, pattern)
                    ]
                    for key in keys_to_delete:
                        self.memory_cache.cache.pop(key)
                        count += 1
            
            # Clear from Redis
            if self.settings.enable_redis_cache:
                redis_count = await self.redis_client.invalidate_pattern(pattern)
                count += redis_count
            
            logger.info(f"Invalidated {count} keys matching pattern: {pattern}")
            return count
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
            return 0
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None,
        data_type: Optional[str] = None
    ) -> Any:
        """Get from cache or compute and set if missing"""
        # Try to get from cache
        value = await self.get(key, data_type)
        
        if value is not None:
            return value
        
        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        # Cache the computed value
        await self.set(key, value, ttl, data_type)
        
        return value
    
    def cache_decorator(
        self,
        ttl: Optional[int] = None,
        data_type: Optional[str] = None,
        key_prefix: Optional[str] = None,
        include_args: bool = True
    ):
        """Decorator for caching function results"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_function_key(
                    func, args if include_args else (), kwargs if include_args else {},
                    prefix=key_prefix
                )
                
                # Try to get from cache
                cached = await self.get(cache_key, data_type)
                if cached is not None:
                    return cached
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                await self.set(cache_key, result, ttl, data_type)
                
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, run in asyncio
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(async_wrapper(*args, **kwargs))
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    # Cache warmup and preloading
    
    async def warmup(self, keys: List[Tuple[str, Callable, Optional[int]]]) -> None:
        """Warmup cache with predefined keys"""
        logger.info(f"Starting cache warmup for {len(keys)} keys")
        
        for key, factory, ttl in keys:
            try:
                if asyncio.iscoroutinefunction(factory):
                    value = await factory()
                else:
                    value = factory()
                
                await self.set(key, value, ttl)
                
            except Exception as e:
                logger.error(f"Error warming up key {key}: {e}")
        
        logger.info("Cache warmup completed")
    
    async def _warmup_cache(self) -> None:
        """Background task for cache warmup"""
        while True:
            try:
                # Warmup logic here - could load from config or database
                await asyncio.sleep(3600)  # Run hourly
                
            except Exception as e:
                logger.error(f"Cache warmup task error: {e}")
                await asyncio.sleep(60)
    
    # Metrics and monitoring
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        memory_stats = await self.memory_cache.get_stats() if self.settings.enable_memory_cache else {}
        
        total_requests = self.stats["requests"]
        hit_rate = (
            (self.stats["memory_hits"] + self.stats["redis_hits"]) / total_requests
            if total_requests > 0 else 0
        )
        
        return {
            "total_requests": total_requests,
            "memory_hits": self.stats["memory_hits"],
            "redis_hits": self.stats["redis_hits"],
            "misses": self.stats["misses"],
            "errors": self.stats["errors"],
            "hit_rate": hit_rate,
            "memory_cache": memory_stats,
            "layers": {
                "memory_enabled": self.settings.enable_memory_cache,
                "redis_enabled": self.settings.enable_redis_cache,
                "distributed_enabled": self.settings.enable_distributed_cache
            }
        }
    
    async def _collect_metrics(self) -> None:
        """Background task for metrics collection"""
        while True:
            try:
                await asyncio.sleep(self.settings.metrics_interval)
                
                stats = await self.get_stats()
                logger.info(f"Cache metrics: {json.dumps(stats)}")
                
                # Could send to monitoring service here
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
    
    # Utility methods
    
    def _get_cache_policy(self, data_type: Optional[str]) -> Dict[str, Any]:
        """Get cache policy for data type"""
        if data_type and data_type in self.settings.cache_policies:
            return self.settings.cache_policies[data_type]
        
        return self.settings.cache_policies.get("default", {
            "ttl": 3600,
            "layer": "redis",
            "compress": False,
            "priority": "medium"
        })
    
    def _compress_value(self, value: Any) -> bytes:
        """Compress value for storage"""
        try:
            # Serialize if not bytes
            if not isinstance(value, bytes):
                value = pickle.dumps(value)
            
            # Compress
            return zlib.compress(value)
            
        except Exception as e:
            logger.error(f"Compression error: {e}")
            return value
    
    def _decompress_value(self, value: Union[bytes, str]) -> Any:
        """Decompress value from storage"""
        try:
            # Convert to bytes if string
            if isinstance(value, str):
                value = value.encode()
            
            # Decompress
            decompressed = zlib.decompress(value)
            
            # Try to deserialize
            try:
                return pickle.loads(decompressed)
            except:
                return decompressed
                
        except Exception as e:
            logger.error(f"Decompression error: {e}")
            return value
    
    def _generate_function_key(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        prefix: Optional[str] = None
    ) -> str:
        """Generate cache key for function call"""
        parts = [prefix or "func", func.__module__, func.__name__]
        
        # Add args hash
        if args:
            args_str = str(args)
            args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
            parts.append(args_hash)
        
        # Add kwargs hash
        if kwargs:
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
            kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
            parts.append(kwargs_hash)
        
        return ":".join(parts)
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for memory cache"""
        # Convert Redis pattern to simple Python pattern
        pattern = pattern.replace("*", ".*").replace("?", ".")
        
        import re
        return bool(re.match(pattern, key))
    
    async def cleanup(self) -> None:
        """Cleanup cache manager resources"""
        try:
            # Cancel background tasks
            if self._warmup_task:
                self._warmup_task.cancel()
            
            if self._metrics_task:
                self._metrics_task.cancel()
            
            # Clear memory cache
            await self.memory_cache.clear()
            
            # Disconnect Redis
            await self.redis_client.disconnect()
            
            logger.info("Cache manager cleaned up")
            
        except Exception as e:
            logger.error(f"Error cleaning up cache manager: {e}")


# Global cache manager instance
cache_manager = CacheManager()