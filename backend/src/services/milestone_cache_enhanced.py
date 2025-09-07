"""
Enhanced Milestone Redis Caching Service

This module provides an optimized Redis caching layer for the milestone system
with advanced caching strategies, improved TTL management, and robust error handling.
"""

import json
import asyncio
import hashlib
import pickle
from typing import Optional, Dict, Any, List, Set, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum
import logging
from contextlib import asynccontextmanager

from ..infrastructure.redis.redis_mcp import RedisMCPClient
from ..models.milestone import MilestoneStatus, MilestoneType
from ..infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache invalidation strategies"""
    TIME_BASED = "time_based"  # Standard TTL-based expiration
    EVENT_BASED = "event_based"  # Invalidate on specific events
    WRITE_THROUGH = "write_through"  # Update cache on write
    WRITE_BEHIND = "write_behind"  # Async cache update after write
    REFRESH_AHEAD = "refresh_ahead"  # Proactive refresh before expiry


class CachePriority(Enum):
    """Cache priority levels for memory pressure handling"""
    CRITICAL = 1  # Never evict unless necessary
    HIGH = 2  # Keep as long as possible
    MEDIUM = 3  # Standard eviction policy
    LOW = 4  # First to evict under pressure


class EnhancedMilestoneCacheService:
    """
    Enhanced caching service with advanced features:
    - Multi-layer caching (L1 memory, L2 Redis)
    - Intelligent TTL management
    - Circuit breaker pattern
    - Cache warming and preloading
    - Compression for large objects
    - Atomic operations for concurrent access
    """
    
    # Enhanced cache key prefixes
    KEY_PREFIX = "v2:milestone:"
    KEY_USER_PROGRESS = f"{KEY_PREFIX}progress:user:"
    KEY_MILESTONE_TREE = f"{KEY_PREFIX}tree:user:"
    KEY_MILESTONE_DATA = f"{KEY_PREFIX}data:"
    KEY_DEPENDENCY_STATUS = f"{KEY_PREFIX}deps:status:"
    KEY_DEPENDENCY_GRAPH = f"{KEY_PREFIX}deps:graph:"
    KEY_ARTIFACT = f"{KEY_PREFIX}artifact:"
    KEY_STATISTICS = f"{KEY_PREFIX}stats:"
    KEY_LEADERBOARD = f"{KEY_PREFIX}leaderboard:"
    KEY_SESSION = f"{KEY_PREFIX}session:"
    KEY_LOCK = f"{KEY_PREFIX}lock:"
    KEY_FREQUENTLY_ACCESSED = f"{KEY_PREFIX}freq:"
    KEY_REAL_TIME_UPDATE = f"{KEY_PREFIX}rt:update:"
    KEY_BATCH_OPERATION = f"{KEY_PREFIX}batch:"
    
    # Enhanced TTL settings with dynamic adjustment
    BASE_TTL = {
        CachePriority.CRITICAL: 7200,  # 2 hours
        CachePriority.HIGH: 3600,  # 1 hour
        CachePriority.MEDIUM: 1800,  # 30 minutes
        CachePriority.LOW: 900,  # 15 minutes
    }
    
    # Specific TTLs for different data types
    TTL_CONFIG = {
        "user_progress": (3600, CachePriority.HIGH),
        "milestone_tree": (1800, CachePriority.MEDIUM),
        "milestone_data": (7200, CachePriority.LOW),
        "dependency_status": (900, CachePriority.HIGH),
        "dependency_graph": (3600, CachePriority.LOW),
        "artifact": (3600, CachePriority.MEDIUM),
        "statistics": (300, CachePriority.LOW),
        "session": (86400, CachePriority.CRITICAL),
        "real_time": (60, CachePriority.CRITICAL),
        "frequently_accessed": (1800, CachePriority.HIGH),
    }
    
    def __init__(
        self,
        redis_client: RedisMCPClient,
        enable_l1_cache: bool = True,
        enable_compression: bool = True,
        enable_metrics: bool = True
    ):
        """Initialize the enhanced cache service"""
        self.redis = redis_client
        self.enable_l1_cache = enable_l1_cache
        self.enable_compression = enable_compression
        self.enable_metrics = enable_metrics
        
        # L1 Memory cache for ultra-fast access
        self._l1_cache: Dict[str, Any] = {}
        self._l1_cache_metadata: Dict[str, Dict] = {}
        self._l1_max_size = 1000
        
        # Metrics tracking
        self._metrics = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "writes": 0,
            "errors": 0,
            "evictions": 0,
            "compression_ratio": 0.0,
        }
        
        # Circuit breaker state
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_reset_time = None
        self._circuit_breaker_timeout = 60  # seconds
        
        # Cache warming queue
        self._warm_cache_queue: asyncio.Queue = asyncio.Queue()
        
    # ==================== L1 Memory Cache Management ====================
    
    def _l1_get(self, key: str) -> Optional[Any]:
        """Get from L1 memory cache"""
        if not self.enable_l1_cache:
            return None
            
        if key in self._l1_cache:
            metadata = self._l1_cache_metadata[key]
            
            # Check if expired
            if datetime.utcnow() > metadata["expires_at"]:
                del self._l1_cache[key]
                del self._l1_cache_metadata[key]
                return None
            
            # Update access count and time
            metadata["access_count"] += 1
            metadata["last_accessed"] = datetime.utcnow()
            
            self._metrics["l1_hits"] += 1
            return self._l1_cache[key]
        
        self._metrics["l1_misses"] += 1
        return None
    
    def _l1_set(
        self,
        key: str,
        value: Any,
        ttl: int,
        priority: CachePriority = CachePriority.MEDIUM
    ) -> None:
        """Set in L1 memory cache with eviction if needed"""
        if not self.enable_l1_cache:
            return
        
        # Evict if at capacity
        if len(self._l1_cache) >= self._l1_max_size:
            self._l1_evict()
        
        self._l1_cache[key] = value
        self._l1_cache_metadata[key] = {
            "expires_at": datetime.utcnow() + timedelta(seconds=ttl),
            "priority": priority,
            "access_count": 0,
            "last_accessed": datetime.utcnow(),
            "size": len(json.dumps(value) if isinstance(value, (dict, list)) else str(value))
        }
    
    def _l1_evict(self) -> None:
        """Evict least recently used items from L1 cache based on priority"""
        if not self._l1_cache:
            return
        
        # Sort by priority and last accessed time
        items = sorted(
            self._l1_cache_metadata.items(),
            key=lambda x: (x[1]["priority"].value, x[1]["last_accessed"])
        )
        
        # Evict bottom 10%
        evict_count = max(1, len(items) // 10)
        for key, _ in items[:evict_count]:
            del self._l1_cache[key]
            del self._l1_cache_metadata[key]
            self._metrics["evictions"] += 1
    
    def _l1_invalidate(self, pattern: str) -> None:
        """Invalidate L1 cache entries matching pattern"""
        keys_to_delete = [
            key for key in self._l1_cache.keys()
            if pattern in key or key.startswith(pattern)
        ]
        
        for key in keys_to_delete:
            del self._l1_cache[key]
            del self._l1_cache_metadata[key]
    
    # ==================== User Progress Caching ====================
    
    async def get_user_progress(
        self,
        user_id: str,
        milestone_id: Optional[str] = None,
        include_real_time: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get user progress with multi-layer caching and real-time updates
        """
        key = f"{self.KEY_USER_PROGRESS}{user_id}"
        if milestone_id:
            key = f"{key}:{milestone_id}"
        
        # Check L1 cache first
        cached = self._l1_get(key)
        if cached:
            return cached
        
        # Check Redis (L2)
        cached = await self._safe_redis_get(key)
        if cached:
            # Populate L1 for next access
            ttl, priority = self.TTL_CONFIG["user_progress"]
            self._l1_set(key, cached, ttl, priority)
            self._metrics["l2_hits"] += 1
            
            # Merge real-time updates if requested
            if include_real_time:
                rt_updates = await self._get_real_time_updates(user_id, milestone_id)
                if rt_updates:
                    cached = self._merge_real_time_updates(cached, rt_updates)
            
            return cached
        
        self._metrics["l2_misses"] += 1
        return None
    
    async def set_user_progress(
        self,
        user_id: str,
        progress_data: Dict[str, Any],
        milestone_id: Optional[str] = None,
        strategy: CacheStrategy = CacheStrategy.WRITE_THROUGH
    ) -> bool:
        """
        Set user progress with configurable caching strategy
        """
        key = f"{self.KEY_USER_PROGRESS}{user_id}"
        if milestone_id:
            key = f"{key}:{milestone_id}"
        
        # Add metadata
        progress_data["cached_at"] = datetime.utcnow().isoformat()
        progress_data["cache_version"] = 2
        
        ttl, priority = self.TTL_CONFIG["user_progress"]
        
        if strategy == CacheStrategy.WRITE_THROUGH:
            # Update both layers synchronously
            success = await self._safe_redis_set(key, progress_data, ttl)
            if success:
                self._l1_set(key, progress_data, ttl, priority)
                self._metrics["writes"] += 1
            return success
            
        elif strategy == CacheStrategy.WRITE_BEHIND:
            # Update L1 immediately, Redis asynchronously
            self._l1_set(key, progress_data, ttl, priority)
            asyncio.create_task(self._async_redis_write(key, progress_data, ttl))
            return True
        
        return False
    
    async def update_user_progress_atomic(
        self,
        user_id: str,
        milestone_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Atomically update user progress to prevent race conditions
        """
        key = f"{self.KEY_USER_PROGRESS}{user_id}:{milestone_id}"
        lock_key = f"{self.KEY_LOCK}{key}"
        
        # Acquire distributed lock
        lock_value = await self.redis.lock(lock_key, expiry=5)
        if not lock_value:
            logger.warning(f"Failed to acquire lock for {key}")
            return False
        
        try:
            # Get current data
            current = await self._safe_redis_get(key)
            if not current:
                current = {}
            
            # Apply updates
            current.update(updates)
            current["updated_at"] = datetime.utcnow().isoformat()
            
            # Save atomically
            ttl, priority = self.TTL_CONFIG["user_progress"]
            success = await self._safe_redis_set(key, current, ttl)
            
            if success:
                # Update L1 cache
                self._l1_set(key, current, ttl, priority)
                
                # Publish update for real-time subscribers
                await self._publish_cache_update(user_id, milestone_id, updates)
            
            return success
            
        finally:
            # Release lock
            await self.redis.unlock(lock_key, lock_value)
    
    # ==================== Dependency Caching ====================
    
    async def get_dependency_status(
        self,
        user_id: str,
        milestone_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached dependency status with automatic refresh
        """
        key = f"{self.KEY_DEPENDENCY_STATUS}{user_id}:{milestone_id}"
        
        # Check L1 cache
        cached = self._l1_get(key)
        if cached:
            return cached
        
        # Check Redis with refresh-ahead strategy
        cached = await self._safe_redis_get(key)
        if cached:
            ttl, priority = self.TTL_CONFIG["dependency_status"]
            
            # Check if near expiry and schedule refresh
            cached_time = datetime.fromisoformat(cached.get("checked_at", datetime.utcnow().isoformat()))
            if (datetime.utcnow() - cached_time).seconds > (ttl * 0.8):
                # Schedule background refresh
                asyncio.create_task(self._refresh_dependency_status(user_id, milestone_id))
            
            self._l1_set(key, cached, ttl, priority)
            return cached
        
        return None
    
    async def set_dependency_status(
        self,
        user_id: str,
        milestone_id: str,
        can_start: bool,
        missing_deps: List[str],
        dependent_milestones: Optional[List[str]] = None
    ) -> bool:
        """
        Cache dependency status with related milestone invalidation
        """
        key = f"{self.KEY_DEPENDENCY_STATUS}{user_id}:{milestone_id}"
        
        data = {
            "can_start": can_start,
            "missing_dependencies": missing_deps,
            "dependent_milestones": dependent_milestones or [],
            "checked_at": datetime.utcnow().isoformat()
        }
        
        ttl, priority = self.TTL_CONFIG["dependency_status"]
        success = await self._safe_redis_set(key, data, ttl)
        
        if success:
            self._l1_set(key, data, ttl, priority)
            
            # Invalidate dependent milestone caches
            if dependent_milestones:
                for dep_id in dependent_milestones:
                    await self.invalidate_milestone_cache(user_id, dep_id)
        
        return success
    
    async def cache_dependency_graph(
        self,
        milestone_id: str,
        graph_data: Dict[str, Any]
    ) -> bool:
        """
        Cache the entire dependency graph for a milestone
        """
        key = f"{self.KEY_DEPENDENCY_GRAPH}{milestone_id}"
        ttl, priority = self.TTL_CONFIG["dependency_graph"]
        
        # Compress graph data if large
        if self.enable_compression and len(json.dumps(graph_data)) > 1024:
            graph_data = self._compress_data(graph_data)
        
        success = await self._safe_redis_set(key, graph_data, ttl)
        if success:
            self._l1_set(key, graph_data, ttl, priority)
        
        return success
    
    # ==================== Frequently Accessed Data ====================
    
    async def track_and_cache_frequent_access(
        self,
        key_pattern: str,
        data: Any,
        access_threshold: int = 5
    ) -> None:
        """
        Track access patterns and cache frequently accessed data
        """
        freq_key = f"{self.KEY_FREQUENTLY_ACCESSED}{key_pattern}"
        
        # Increment access counter
        access_count = await self._increment_access_counter(freq_key)
        
        # Cache if frequently accessed
        if access_count >= access_threshold:
            ttl, priority = self.TTL_CONFIG["frequently_accessed"]
            await self._safe_redis_set(f"{freq_key}:data", data, ttl * 2)  # Longer TTL
            self._l1_set(f"{freq_key}:data", data, ttl * 2, CachePriority.HIGH)
    
    async def get_frequently_accessed(self, key_pattern: str) -> Optional[Any]:
        """
        Get frequently accessed cached data
        """
        freq_key = f"{self.KEY_FREQUENTLY_ACCESSED}{key_pattern}:data"
        
        # Check L1 first
        cached = self._l1_get(freq_key)
        if cached:
            return cached
        
        # Check Redis
        return await self._safe_redis_get(freq_key)
    
    # ==================== Real-time Updates ====================
    
    async def publish_real_time_update(
        self,
        user_id: str,
        milestone_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Publish real-time progress updates with caching
        """
        # Store in short-lived cache for aggregation
        rt_key = f"{self.KEY_REAL_TIME_UPDATE}{user_id}:{milestone_id}"
        
        update_data["timestamp"] = datetime.utcnow().isoformat()
        
        # Get existing updates
        existing = await self._safe_redis_get(rt_key) or []
        existing.append(update_data)
        
        # Keep only last 100 updates
        if len(existing) > 100:
            existing = existing[-100:]
        
        ttl, _ = self.TTL_CONFIG["real_time"]
        await self._safe_redis_set(rt_key, existing, ttl)
        
        # Publish to channel
        channel = f"milestone:rt:{user_id}"
        message = {
            "milestone_id": milestone_id,
            "update": update_data
        }
        
        return await self.redis.publish(channel, message) > 0
    
    async def get_real_time_updates(
        self,
        user_id: str,
        milestone_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent real-time updates
        """
        if milestone_id:
            rt_key = f"{self.KEY_REAL_TIME_UPDATE}{user_id}:{milestone_id}"
            updates = await self._safe_redis_get(rt_key) or []
        else:
            # Get all milestone updates for user
            pattern = f"{self.KEY_REAL_TIME_UPDATE}{user_id}:*"
            keys = await self._safe_redis_keys(pattern)
            updates = []
            for key in keys:
                milestone_updates = await self._safe_redis_get(key) or []
                updates.extend(milestone_updates)
        
        # Filter by timestamp if requested
        if since:
            updates = [
                u for u in updates
                if datetime.fromisoformat(u["timestamp"]) > since
            ]
        
        return sorted(updates, key=lambda x: x["timestamp"])
    
    # ==================== Batch Operations ====================
    
    async def batch_get(
        self,
        keys: List[str],
        key_prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Efficiently get multiple cache entries
        """
        results = {}
        
        # Check L1 cache first
        l1_misses = []
        for key in keys:
            full_key = f"{key_prefix}{key}" if key_prefix else key
            cached = self._l1_get(full_key)
            if cached:
                results[key] = cached
            else:
                l1_misses.append(full_key)
        
        # Batch get from Redis for L1 misses
        if l1_misses:
            # Use pipeline for efficiency
            tasks = [self._safe_redis_get(key) for key in l1_misses]
            redis_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for key, result in zip(l1_misses, redis_results):
                if not isinstance(result, Exception) and result:
                    # Extract original key
                    original_key = key.replace(key_prefix, "") if key_prefix else key
                    results[original_key] = result
                    
                    # Populate L1 cache
                    ttl, priority = self.TTL_CONFIG.get("user_progress", (3600, CachePriority.MEDIUM))
                    self._l1_set(key, result, ttl, priority)
        
        return results
    
    async def batch_set(
        self,
        data: Dict[str, Any],
        key_prefix: str = "",
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.WRITE_THROUGH
    ) -> bool:
        """
        Efficiently set multiple cache entries
        """
        if not ttl:
            ttl, _ = self.TTL_CONFIG.get("user_progress", (3600, CachePriority.MEDIUM))
        
        tasks = []
        for key, value in data.items():
            full_key = f"{key_prefix}{key}" if key_prefix else key
            
            if strategy == CacheStrategy.WRITE_THROUGH:
                tasks.append(self._safe_redis_set(full_key, value, ttl))
                self._l1_set(full_key, value, ttl, CachePriority.MEDIUM)
            elif strategy == CacheStrategy.WRITE_BEHIND:
                self._l1_set(full_key, value, ttl, CachePriority.MEDIUM)
                tasks.append(self._async_redis_write(full_key, value, ttl))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return all(r is True for r in results if not isinstance(r, Exception))
        
        return True
    
    # ==================== Cache Invalidation ====================
    
    async def invalidate_user_cache(
        self,
        user_id: str,
        cascade: bool = True
    ) -> bool:
        """
        Invalidate all cache entries for a user with cascade option
        """
        patterns = [
            f"{self.KEY_USER_PROGRESS}{user_id}:*",
            f"{self.KEY_MILESTONE_TREE}{user_id}",
            f"{self.KEY_DEPENDENCY_STATUS}{user_id}:*",
            f"{self.KEY_SESSION}{user_id}:*",
            f"{self.KEY_REAL_TIME_UPDATE}{user_id}:*",
        ]
        
        try:
            for pattern in patterns:
                # Invalidate L1 cache
                self._l1_invalidate(pattern)
                
                # Invalidate Redis cache
                keys = await self._safe_redis_keys(pattern)
                if keys:
                    await self._safe_redis_delete(*keys)
            
            # Cascade to related caches if requested
            if cascade:
                await self._invalidate_related_caches(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating user cache: {e}")
            return False
    
    async def invalidate_milestone_cache(
        self,
        user_id: str,
        milestone_id: str
    ) -> bool:
        """
        Invalidate cache for a specific milestone
        """
        keys = [
            f"{self.KEY_USER_PROGRESS}{user_id}:{milestone_id}",
            f"{self.KEY_DEPENDENCY_STATUS}{user_id}:{milestone_id}",
            f"{self.KEY_REAL_TIME_UPDATE}{user_id}:{milestone_id}",
        ]
        
        for key in keys:
            self._l1_invalidate(key)
            await self._safe_redis_delete(key)
        
        # Also invalidate the full tree cache as it contains this milestone
        tree_key = f"{self.KEY_MILESTONE_TREE}{user_id}"
        self._l1_invalidate(tree_key)
        await self._safe_redis_delete(tree_key)
        
        return True
    
    # ==================== Connection Pooling & Error Handling ====================
    
    @asynccontextmanager
    async def connection_pool(self):
        """
        Context manager for Redis connection pooling
        """
        try:
            yield self.redis
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            self._handle_redis_error(e)
            raise
    
    async def _safe_redis_get(self, key: str) -> Optional[Any]:
        """
        Safe Redis get with circuit breaker
        """
        if self._is_circuit_open():
            return None
        
        try:
            async with self.connection_pool() as redis:
                return await redis.get_cache(key)
        except Exception as e:
            self._handle_redis_error(e)
            return None
    
    async def _safe_redis_set(
        self,
        key: str,
        value: Any,
        ttl: int
    ) -> bool:
        """
        Safe Redis set with circuit breaker
        """
        if self._is_circuit_open():
            return False
        
        try:
            async with self.connection_pool() as redis:
                return await redis.set_cache(key, value, ttl)
        except Exception as e:
            self._handle_redis_error(e)
            return False
    
    async def _safe_redis_delete(self, *keys: str) -> bool:
        """
        Safe Redis delete with circuit breaker
        """
        if self._is_circuit_open():
            return False
        
        try:
            async with self.connection_pool() as redis:
                tasks = [redis.delete_cache(key) for key in keys]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return all(r is True for r in results if not isinstance(r, Exception))
        except Exception as e:
            self._handle_redis_error(e)
            return False
    
    async def _safe_redis_keys(self, pattern: str) -> List[str]:
        """
        Safe Redis keys lookup with circuit breaker
        """
        if self._is_circuit_open():
            return []
        
        try:
            return await asyncio.to_thread(
                self.redis.client.keys,
                pattern
            )
        except Exception as e:
            self._handle_redis_error(e)
            return []
    
    # ==================== Circuit Breaker ====================
    
    def _is_circuit_open(self) -> bool:
        """
        Check if circuit breaker is open
        """
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            if self._circuit_breaker_reset_time:
                if datetime.utcnow() > self._circuit_breaker_reset_time:
                    # Reset circuit breaker
                    self._circuit_breaker_failures = 0
                    self._circuit_breaker_reset_time = None
                    return False
            else:
                # Set reset time
                self._circuit_breaker_reset_time = (
                    datetime.utcnow() + timedelta(seconds=self._circuit_breaker_timeout)
                )
            return True
        return False
    
    def _handle_redis_error(self, error: Exception) -> None:
        """
        Handle Redis errors and update circuit breaker
        """
        self._circuit_breaker_failures += 1
        self._metrics["errors"] += 1
        logger.error(f"Redis error (failures: {self._circuit_breaker_failures}): {error}")
    
    # ==================== Helper Methods ====================
    
    def _compress_data(self, data: Any) -> Dict[str, Any]:
        """
        Compress data for storage
        """
        import zlib
        
        serialized = pickle.dumps(data)
        compressed = zlib.compress(serialized)
        
        original_size = len(serialized)
        compressed_size = len(compressed)
        
        self._metrics["compression_ratio"] = compressed_size / original_size
        
        return {
            "_compressed": True,
            "data": compressed.hex(),
            "original_size": original_size,
            "compressed_size": compressed_size
        }
    
    def _decompress_data(self, compressed_data: Dict[str, Any]) -> Any:
        """
        Decompress data from storage
        """
        if not compressed_data.get("_compressed"):
            return compressed_data
        
        import zlib
        
        compressed = bytes.fromhex(compressed_data["data"])
        decompressed = zlib.decompress(compressed)
        return pickle.loads(decompressed)
    
    async def _increment_access_counter(self, key: str) -> int:
        """
        Increment and return access counter
        """
        try:
            return await asyncio.to_thread(
                self.redis.client.incr,
                f"{key}:counter"
            )
        except:
            return 0
    
    async def _async_redis_write(
        self,
        key: str,
        value: Any,
        ttl: int
    ) -> None:
        """
        Asynchronous write to Redis (fire and forget)
        """
        try:
            await self._safe_redis_set(key, value, ttl)
        except Exception as e:
            logger.error(f"Async Redis write failed: {e}")
    
    async def _refresh_dependency_status(
        self,
        user_id: str,
        milestone_id: str
    ) -> None:
        """
        Background refresh of dependency status
        """
        # This would typically call the service layer to recalculate
        # For now, just log the intent
        logger.info(f"Scheduled refresh for dependency status: {user_id}:{milestone_id}")
    
    def _merge_real_time_updates(
        self,
        cached_data: Dict[str, Any],
        rt_updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge real-time updates into cached data
        """
        if not rt_updates:
            return cached_data
        
        # Apply updates in chronological order
        for update in sorted(rt_updates, key=lambda x: x["timestamp"]):
            if "progress_update" in update:
                cached_data.update(update["progress_update"])
            if "status" in update:
                cached_data["status"] = update["status"]
        
        cached_data["has_real_time_updates"] = True
        return cached_data
    
    async def _invalidate_related_caches(self, user_id: str) -> None:
        """
        Invalidate caches related to a user
        """
        # Invalidate leaderboard entries
        leaderboard_types = ["weekly", "monthly", "all_time"]
        for lb_type in leaderboard_types:
            key = f"{self.KEY_LEADERBOARD}{lb_type}"
            try:
                await asyncio.to_thread(
                    self.redis.client.zrem,
                    key,
                    user_id
                )
            except:
                pass
    
    async def _publish_cache_update(
        self,
        user_id: str,
        milestone_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """
        Publish cache update event for subscribers
        """
        channel = f"cache:update:{user_id}"
        message = {
            "type": "cache_update",
            "milestone_id": milestone_id,
            "updates": updates,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await self.redis.publish(channel, message)
        except Exception as e:
            logger.error(f"Failed to publish cache update: {e}")
    
    # ==================== Monitoring & Metrics ====================
    
    async def get_cache_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive cache metrics
        """
        total_l1 = self._metrics["l1_hits"] + self._metrics["l1_misses"]
        total_l2 = self._metrics["l2_hits"] + self._metrics["l2_misses"]
        
        metrics = {
            **self._metrics,
            "l1_hit_rate": (self._metrics["l1_hits"] / total_l1 * 100) if total_l1 > 0 else 0,
            "l2_hit_rate": (self._metrics["l2_hits"] / total_l2 * 100) if total_l2 > 0 else 0,
            "l1_cache_size": len(self._l1_cache),
            "l1_cache_memory": sum(
                meta["size"] for meta in self._l1_cache_metadata.values()
            ),
            "circuit_breaker_state": "open" if self._is_circuit_open() else "closed",
            "circuit_breaker_failures": self._circuit_breaker_failures,
        }
        
        # Get Redis info
        try:
            redis_info = await asyncio.to_thread(self.redis.client.info, "memory")
            metrics["redis_memory_used"] = redis_info.get("used_memory_human", "N/A")
            metrics["redis_memory_peak"] = redis_info.get("used_memory_peak_human", "N/A")
        except:
            pass
        
        return metrics
    
    async def reset_metrics(self) -> None:
        """
        Reset cache metrics
        """
        self._metrics = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "writes": 0,
            "errors": 0,
            "evictions": 0,
            "compression_ratio": 0.0,
        }


# ==================== Cache Decorators ====================

def cached(
    ttl: int = 3600,
    key_prefix: str = "",
    priority: CachePriority = CachePriority.MEDIUM,
    strategy: CacheStrategy = CacheStrategy.TIME_BASED
):
    """
    Decorator for caching function results with configurable strategy
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix or func.__name__}:"
            cache_key += hashlib.md5(
                f"{str(args)}:{str(kwargs)}".encode()
            ).hexdigest()
            
            # Try to get from cache
            if hasattr(self, 'cache_service'):
                cache_service = self.cache_service
                
                # Check cache based on strategy
                if strategy in [CacheStrategy.TIME_BASED, CacheStrategy.REFRESH_AHEAD]:
                    cached_result = cache_service._l1_get(cache_key)
                    if not cached_result:
                        cached_result = await cache_service._safe_redis_get(cache_key)
                    
                    if cached_result:
                        # Check if refresh-ahead is needed
                        if strategy == CacheStrategy.REFRESH_AHEAD:
                            cached_time = datetime.fromisoformat(
                                cached_result.get("cached_at", datetime.utcnow().isoformat())
                            )
                            if (datetime.utcnow() - cached_time).seconds > (ttl * 0.8):
                                # Schedule background refresh
                                asyncio.create_task(
                                    _background_refresh(func, self, args, kwargs, cache_key, ttl, priority)
                                )
                        
                        return cached_result.get("result") if isinstance(cached_result, dict) else cached_result
            
            # Execute function
            result = await func(self, *args, **kwargs)
            
            # Cache result
            if hasattr(self, 'cache_service') and result is not None:
                cache_data = {
                    "result": result,
                    "cached_at": datetime.utcnow().isoformat()
                }
                
                await cache_service._safe_redis_set(cache_key, cache_data, ttl)
                cache_service._l1_set(cache_key, cache_data, ttl, priority)
            
            return result
        
        return wrapper
    return decorator


async def _background_refresh(func, self, args, kwargs, cache_key, ttl, priority):
    """
    Background refresh for refresh-ahead strategy
    """
    try:
        result = await func(self, *args, **kwargs)
        if result is not None:
            cache_data = {
                "result": result,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            if hasattr(self, 'cache_service'):
                cache_service = self.cache_service
                await cache_service._safe_redis_set(cache_key, cache_data, ttl)
                cache_service._l1_set(cache_key, cache_data, ttl, priority)
    except Exception as e:
        logger.error(f"Background refresh failed: {e}")


def invalidate_on_event(*event_names: str):
    """
    Decorator to invalidate cache on specific events
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            result = await func(self, *args, **kwargs)
            
            # Invalidate caches based on events
            if hasattr(self, 'cache_service'):
                for event_name in event_names:
                    if event_name == "user_update" and len(args) > 0:
                        await self.cache_service.invalidate_user_cache(args[0])
                    elif event_name == "milestone_update" and len(args) > 1:
                        await self.cache_service.invalidate_milestone_cache(args[0], args[1])
            
            return result
        
        return wrapper
    return decorator