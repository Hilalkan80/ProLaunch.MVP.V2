"""
Milestone Redis Caching Service

Implements efficient caching strategies for milestone data and progress updates
using Redis for real-time performance optimization.
"""

import json
from typing import Optional, Dict, Any, List, Set
from datetime import datetime, timedelta
import asyncio
from functools import wraps
import hashlib

from ..infrastructure.redis.redis_mcp import RedisMCPClient
from ..models.milestone import MilestoneStatus


class MilestoneCacheService:
    """
    Service for managing milestone-related caching in Redis.
    Provides high-performance access to frequently accessed milestone data.
    """
    
    # Cache key prefixes
    KEY_PREFIX_USER_PROGRESS = "milestone:progress:user:"
    KEY_PREFIX_MILESTONE_TREE = "milestone:tree:user:"
    KEY_PREFIX_MILESTONE_DATA = "milestone:data:"
    KEY_PREFIX_DEPENDENCY_CHECK = "milestone:deps:check:"
    KEY_PREFIX_ARTIFACT = "milestone:artifact:"
    KEY_PREFIX_STATISTICS = "milestone:stats:"
    KEY_PREFIX_LEADERBOARD = "milestone:leaderboard:"
    KEY_PREFIX_SESSION = "milestone:session:"
    KEY_PREFIX_LOCK = "milestone:lock:"
    
    # Cache TTL settings (in seconds)
    TTL_USER_PROGRESS = 3600  # 1 hour
    TTL_MILESTONE_TREE = 1800  # 30 minutes
    TTL_MILESTONE_DATA = 7200  # 2 hours
    TTL_DEPENDENCY_CHECK = 900  # 15 minutes
    TTL_ARTIFACT = 3600  # 1 hour
    TTL_STATISTICS = 300  # 5 minutes
    TTL_SESSION = 86400  # 24 hours
    
    def __init__(self, redis_client: RedisMCPClient):
        """Initialize the milestone cache service."""
        self.redis = redis_client
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }
    
    # User Progress Caching
    
    async def get_user_progress(
        self,
        user_id: str,
        milestone_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached user progress for all milestones or a specific milestone.
        """
        if milestone_id:
            key = f"{self.KEY_PREFIX_USER_PROGRESS}{user_id}:{milestone_id}"
        else:
            key = f"{self.KEY_PREFIX_USER_PROGRESS}{user_id}:all"
        
        data = await self.redis.get_cache(key)
        if data:
            self._cache_stats["hits"] += 1
        else:
            self._cache_stats["misses"] += 1
        
        return data
    
    async def set_user_progress(
        self,
        user_id: str,
        progress_data: Dict[str, Any],
        milestone_id: Optional[str] = None
    ) -> bool:
        """
        Cache user progress data with automatic expiry.
        """
        if milestone_id:
            key = f"{self.KEY_PREFIX_USER_PROGRESS}{user_id}:{milestone_id}"
        else:
            key = f"{self.KEY_PREFIX_USER_PROGRESS}{user_id}:all"
        
        # Add timestamp for cache freshness tracking
        progress_data["cached_at"] = datetime.utcnow().isoformat()
        
        return await self.redis.set_cache(
            key,
            progress_data,
            self.TTL_USER_PROGRESS
        )
    
    async def update_milestone_progress(
        self,
        user_id: str,
        milestone_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update specific fields in cached milestone progress.
        """
        key = f"{self.KEY_PREFIX_USER_PROGRESS}{user_id}:{milestone_id}"
        
        # Get existing data
        existing = await self.redis.get_cache(key)
        if existing:
            existing.update(updates)
            existing["updated_at"] = datetime.utcnow().isoformat()
            return await self.redis.set_cache(key, existing, self.TTL_USER_PROGRESS)
        
        return False
    
    # Milestone Tree Caching
    
    async def get_milestone_tree(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached milestone tree with dependency structure for a user.
        """
        key = f"{self.KEY_PREFIX_MILESTONE_TREE}{user_id}"
        tree = await self.redis.get_cache(key)
        
        if tree:
            self._cache_stats["hits"] += 1
            # Check if cache is stale
            cached_time = datetime.fromisoformat(tree.get("cached_at", datetime.utcnow().isoformat()))
            if (datetime.utcnow() - cached_time).seconds > self.TTL_MILESTONE_TREE:
                await self.redis.delete_cache(key)
                return None
        else:
            self._cache_stats["misses"] += 1
        
        return tree
    
    async def set_milestone_tree(
        self,
        user_id: str,
        tree_data: Dict[str, Any]
    ) -> bool:
        """
        Cache the complete milestone tree for a user.
        """
        key = f"{self.KEY_PREFIX_MILESTONE_TREE}{user_id}"
        tree_data["cached_at"] = datetime.utcnow().isoformat()
        
        return await self.redis.set_cache(
            key,
            tree_data,
            self.TTL_MILESTONE_TREE
        )
    
    # Dependency Checking Cache
    
    async def get_dependency_check(
        self,
        user_id: str,
        milestone_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached dependency check results.
        """
        key = f"{self.KEY_PREFIX_DEPENDENCY_CHECK}{user_id}:{milestone_id}"
        return await self.redis.get_cache(key)
    
    async def set_dependency_check(
        self,
        user_id: str,
        milestone_id: str,
        can_start: bool,
        missing_deps: List[str]
    ) -> bool:
        """
        Cache dependency check results.
        """
        key = f"{self.KEY_PREFIX_DEPENDENCY_CHECK}{user_id}:{milestone_id}"
        data = {
            "can_start": can_start,
            "missing_dependencies": missing_deps,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        return await self.redis.set_cache(
            key,
            data,
            self.TTL_DEPENDENCY_CHECK
        )
    
    # Real-time Progress Updates
    
    async def publish_progress_update(
        self,
        user_id: str,
        milestone_id: str,
        progress_data: Dict[str, Any]
    ) -> int:
        """
        Publish real-time progress updates to subscribed clients.
        """
        channel = f"milestone:updates:{user_id}"
        message = {
            "milestone_id": milestone_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": progress_data
        }
        
        return await self.redis.publish(channel, message)
    
    async def track_active_session(
        self,
        user_id: str,
        milestone_id: str,
        session_data: Dict[str, Any]
    ) -> bool:
        """
        Track active milestone work sessions for real-time monitoring.
        """
        key = f"{self.KEY_PREFIX_SESSION}{user_id}:{milestone_id}"
        session_data.update({
            "user_id": user_id,
            "milestone_id": milestone_id,
            "started_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        })
        
        return await self.redis.set_cache(
            key,
            session_data,
            self.TTL_SESSION
        )
    
    async def update_session_activity(
        self,
        user_id: str,
        milestone_id: str
    ) -> bool:
        """
        Update last activity time for a session.
        """
        key = f"{self.KEY_PREFIX_SESSION}{user_id}:{milestone_id}"
        session = await self.redis.get_cache(key)
        
        if session:
            session["last_activity"] = datetime.utcnow().isoformat()
            return await self.redis.set_cache(key, session, self.TTL_SESSION)
        
        return False
    
    # Artifact Caching
    
    async def cache_artifact(
        self,
        artifact_id: str,
        artifact_data: Dict[str, Any]
    ) -> bool:
        """
        Cache generated artifact data for quick retrieval.
        """
        key = f"{self.KEY_PREFIX_ARTIFACT}{artifact_id}"
        return await self.redis.set_cache(
            key,
            artifact_data,
            self.TTL_ARTIFACT
        )
    
    async def get_cached_artifact(
        self,
        artifact_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached artifact data.
        """
        key = f"{self.KEY_PREFIX_ARTIFACT}{artifact_id}"
        return await self.redis.get_cache(key)
    
    # Statistics and Analytics
    
    async def increment_milestone_stats(
        self,
        milestone_code: str,
        stat_type: str  # started, completed, failed, skipped
    ) -> bool:
        """
        Increment milestone statistics counters.
        """
        key = f"{self.KEY_PREFIX_STATISTICS}{milestone_code}:{stat_type}"
        
        try:
            # Get current value
            current = await self.redis.get_cache(key)
            if current is None:
                current = {"count": 0, "last_updated": None}
            
            # Increment
            current["count"] += 1
            current["last_updated"] = datetime.utcnow().isoformat()
            
            return await self.redis.set_cache(key, current, self.TTL_STATISTICS)
        except Exception as e:
            self._cache_stats["errors"] += 1
            print(f"Error incrementing stats: {e}")
            return False
    
    async def get_milestone_stats(
        self,
        milestone_code: str
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for a milestone.
        """
        stats = {}
        stat_types = ["started", "completed", "failed", "skipped"]
        
        for stat_type in stat_types:
            key = f"{self.KEY_PREFIX_STATISTICS}{milestone_code}:{stat_type}"
            data = await self.redis.get_cache(key)
            stats[stat_type] = data.get("count", 0) if data else 0
        
        # Calculate completion rate
        total_started = stats.get("started", 0)
        if total_started > 0:
            stats["completion_rate"] = (stats.get("completed", 0) / total_started) * 100
        else:
            stats["completion_rate"] = 0
        
        return stats
    
    # Leaderboard and Gamification
    
    async def update_leaderboard(
        self,
        user_id: str,
        score: int,
        leaderboard_type: str = "weekly"
    ) -> bool:
        """
        Update user position in milestone completion leaderboard.
        """
        key = f"{self.KEY_PREFIX_LEADERBOARD}{leaderboard_type}"
        
        try:
            # Redis sorted set for leaderboard
            await self.redis.client.zadd(key, {user_id: score})
            
            # Set expiry for weekly/monthly leaderboards
            if leaderboard_type == "weekly":
                await self.redis.client.expire(key, 604800)  # 7 days
            elif leaderboard_type == "monthly":
                await self.redis.client.expire(key, 2592000)  # 30 days
            
            return True
        except Exception as e:
            print(f"Error updating leaderboard: {e}")
            return False
    
    async def get_leaderboard(
        self,
        leaderboard_type: str = "weekly",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top users from leaderboard.
        """
        key = f"{self.KEY_PREFIX_LEADERBOARD}{leaderboard_type}"
        
        try:
            # Get top scores with users
            results = await asyncio.to_thread(
                self.redis.client.zrevrange,
                key,
                0,
                limit - 1,
                withscores=True
            )
            
            leaderboard = []
            for rank, (user_id, score) in enumerate(results, 1):
                leaderboard.append({
                    "rank": rank,
                    "user_id": user_id,
                    "score": int(score)
                })
            
            return leaderboard
        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []
    
    # Cache Management
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """
        Invalidate all cached data for a specific user.
        """
        patterns = [
            f"{self.KEY_PREFIX_USER_PROGRESS}{user_id}:*",
            f"{self.KEY_PREFIX_MILESTONE_TREE}{user_id}",
            f"{self.KEY_PREFIX_DEPENDENCY_CHECK}{user_id}:*",
            f"{self.KEY_PREFIX_SESSION}{user_id}:*"
        ]
        
        try:
            for pattern in patterns:
                keys = await asyncio.to_thread(
                    self.redis.client.keys,
                    pattern
                )
                if keys:
                    await asyncio.to_thread(
                        self.redis.client.delete,
                        *keys
                    )
            return True
        except Exception as e:
            print(f"Error invalidating user cache: {e}")
            return False
    
    async def invalidate_milestone_cache(self, milestone_id: str) -> bool:
        """
        Invalidate all cached data for a specific milestone.
        """
        patterns = [
            f"{self.KEY_PREFIX_MILESTONE_DATA}{milestone_id}",
            f"{self.KEY_PREFIX_DEPENDENCY_CHECK}*:{milestone_id}",
            f"{self.KEY_PREFIX_USER_PROGRESS}*:{milestone_id}"
        ]
        
        try:
            for pattern in patterns:
                keys = await asyncio.to_thread(
                    self.redis.client.keys,
                    pattern
                )
                if keys:
                    await asyncio.to_thread(
                        self.redis.client.delete,
                        *keys
                    )
            return True
        except Exception as e:
            print(f"Error invalidating milestone cache: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        """
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "errors": self._cache_stats["errors"],
            "hit_rate": round(hit_rate, 2),
            "total_requests": total
        }
    
    # Distributed Locking
    
    async def acquire_milestone_lock(
        self,
        user_id: str,
        milestone_id: str,
        ttl: int = 300
    ) -> Optional[str]:
        """
        Acquire a distributed lock for milestone processing.
        Prevents concurrent processing of the same milestone.
        """
        lock_key = f"{self.KEY_PREFIX_LOCK}{user_id}:{milestone_id}"
        return await self.redis.lock(lock_key, ttl)
    
    async def release_milestone_lock(
        self,
        user_id: str,
        milestone_id: str,
        lock_value: str
    ) -> bool:
        """
        Release a milestone processing lock.
        """
        lock_key = f"{self.KEY_PREFIX_LOCK}{user_id}:{milestone_id}"
        return await self.redis.unlock(lock_key, lock_value)
    
    # Batch Operations
    
    async def batch_get_progress(
        self,
        user_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get progress for multiple users in batch.
        """
        results = {}
        
        # Use Redis pipeline for batch operations
        tasks = []
        for user_id in user_ids:
            key = f"{self.KEY_PREFIX_USER_PROGRESS}{user_id}:all"
            tasks.append(self.redis.get_cache(key))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for user_id, response in zip(user_ids, responses):
            if not isinstance(response, Exception) and response:
                results[user_id] = response
            else:
                results[user_id] = None
        
        return results
    
    # Cache Warming
    
    async def warm_cache_for_user(
        self,
        user_id: str,
        milestone_data: Dict[str, Any]
    ) -> bool:
        """
        Pre-populate cache with user milestone data.
        Used after significant updates or for VIP users.
        """
        tasks = []
        
        # Cache overall progress
        if "progress" in milestone_data:
            tasks.append(
                self.set_user_progress(user_id, milestone_data["progress"])
            )
        
        # Cache milestone tree
        if "tree" in milestone_data:
            tasks.append(
                self.set_milestone_tree(user_id, milestone_data["tree"])
            )
        
        # Cache individual milestone progress
        if "milestones" in milestone_data:
            for milestone in milestone_data["milestones"]:
                tasks.append(
                    self.set_user_progress(
                        user_id,
                        milestone["progress"],
                        milestone["id"]
                    )
                )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if all operations succeeded
        return all(
            result is True
            for result in results
            if not isinstance(result, Exception)
        )


def cache_decorator(ttl: int = 3600):
    """
    Decorator for caching function results in Redis.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"func:{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()}"
            
            # Try to get from cache
            if hasattr(self, 'cache_service'):
                cached = await self.cache_service.redis.get_cache(cache_key)
                if cached:
                    return cached
            
            # Execute function
            result = await func(self, *args, **kwargs)
            
            # Cache result
            if hasattr(self, 'cache_service') and result is not None:
                await self.cache_service.redis.set_cache(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator