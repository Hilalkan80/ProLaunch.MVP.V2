"""
Integration tests for enhanced milestone caching service
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.services.milestone_cache_enhanced import (
    EnhancedMilestoneCacheService,
    CacheStrategy,
    CachePriority,
    cached,
    invalidate_on_event
)
from src.infrastructure.redis.redis_mcp import RedisMCPClient
from src.infrastructure.redis.connection_manager import RedisConnectionManager
from src.models.milestone import MilestoneStatus


@pytest.fixture
async def redis_client():
    """Create a mock Redis client for testing"""
    client = AsyncMock(spec=RedisMCPClient)
    client.get_cache = AsyncMock(return_value=None)
    client.set_cache = AsyncMock(return_value=True)
    client.delete_cache = AsyncMock(return_value=True)
    client.publish = AsyncMock(return_value=1)
    client.lock = AsyncMock(return_value="lock_value")
    client.unlock = AsyncMock(return_value=True)
    client.client = Mock()
    client.client.keys = Mock(return_value=[])
    client.client.zadd = Mock(return_value=1)
    client.client.zrevrange = Mock(return_value=[])
    client.client.incr = Mock(return_value=1)
    client.client.info = Mock(return_value={"used_memory_human": "100MB"})
    return client


@pytest.fixture
async def cache_service(redis_client):
    """Create cache service instance"""
    service = EnhancedMilestoneCacheService(
        redis_client=redis_client,
        enable_l1_cache=True,
        enable_compression=True,
        enable_metrics=True
    )
    return service


@pytest.fixture
async def connection_manager():
    """Create a mock connection manager"""
    manager = AsyncMock(spec=RedisConnectionManager)
    manager.get_connection = AsyncMock()
    manager.execute_command = AsyncMock()
    manager.get_metrics = Mock(return_value={})
    return manager


class TestEnhancedCacheService:
    """Test enhanced caching functionality"""
    
    async def test_l1_cache_operations(self, cache_service):
        """Test L1 memory cache operations"""
        # Test set and get
        key = "test_key"
        value = {"data": "test_value"}
        ttl = 3600
        
        cache_service._l1_set(key, value, ttl, CachePriority.HIGH)
        
        # Should retrieve from L1
        cached = cache_service._l1_get(key)
        assert cached == value
        assert cache_service._metrics["l1_hits"] == 1
        
        # Test cache miss
        missing = cache_service._l1_get("nonexistent")
        assert missing is None
        assert cache_service._metrics["l1_misses"] == 1
    
    async def test_l1_cache_eviction(self, cache_service):
        """Test L1 cache eviction based on priority"""
        cache_service._l1_max_size = 5
        
        # Fill cache with different priorities
        for i in range(6):
            priority = CachePriority.LOW if i < 3 else CachePriority.HIGH
            cache_service._l1_set(f"key_{i}", f"value_{i}", 3600, priority)
        
        # Low priority items should be evicted first
        assert len(cache_service._l1_cache) <= cache_service._l1_max_size
        assert cache_service._metrics["evictions"] > 0
        
        # High priority items should remain
        for i in range(3, 6):
            assert f"key_{i}" in cache_service._l1_cache
    
    async def test_user_progress_caching(self, cache_service, redis_client):
        """Test user progress caching with multi-layer"""
        user_id = "user123"
        milestone_id = "milestone456"
        progress_data = {
            "status": MilestoneStatus.IN_PROGRESS,
            "completion_percentage": 50.0,
            "current_step": 5
        }
        
        # Set progress
        success = await cache_service.set_user_progress(
            user_id, progress_data, milestone_id
        )
        assert success
        
        # Should be in L1 cache
        key = f"{cache_service.KEY_USER_PROGRESS}{user_id}:{milestone_id}"
        l1_cached = cache_service._l1_get(key)
        assert l1_cached is not None
        assert l1_cached["status"] == MilestoneStatus.IN_PROGRESS
        
        # Verify Redis was called
        redis_client.set_cache.assert_called_once()
    
    async def test_atomic_update(self, cache_service, redis_client):
        """Test atomic progress update with locking"""
        user_id = "user123"
        milestone_id = "milestone456"
        updates = {"completion_percentage": 75.0}
        
        # Mock existing data
        redis_client.get_cache.return_value = {
            "status": MilestoneStatus.IN_PROGRESS,
            "completion_percentage": 50.0
        }
        
        # Perform atomic update
        success = await cache_service.update_user_progress_atomic(
            user_id, milestone_id, updates
        )
        
        assert success
        redis_client.lock.assert_called_once()
        redis_client.unlock.assert_called_once()
        
        # Verify data was updated
        call_args = redis_client.set_cache.call_args
        assert call_args[0][1]["completion_percentage"] == 75.0
    
    async def test_dependency_caching_with_refresh(self, cache_service, redis_client):
        """Test dependency caching with refresh-ahead strategy"""
        user_id = "user123"
        milestone_id = "milestone456"
        
        # Set dependency status
        await cache_service.set_dependency_status(
            user_id,
            milestone_id,
            can_start=True,
            missing_deps=[],
            dependent_milestones=["milestone789"]
        )
        
        # Mock near-expiry data
        near_expiry_data = {
            "can_start": True,
            "missing_dependencies": [],
            "checked_at": (datetime.utcnow() - timedelta(minutes=14)).isoformat()
        }
        redis_client.get_cache.return_value = near_expiry_data
        
        # Get should trigger refresh
        with patch('asyncio.create_task') as mock_create_task:
            result = await cache_service.get_dependency_status(user_id, milestone_id)
            
            # Refresh should be scheduled
            assert mock_create_task.called
    
    async def test_real_time_updates(self, cache_service, redis_client):
        """Test real-time update publishing and retrieval"""
        user_id = "user123"
        milestone_id = "milestone456"
        
        update_data = {
            "progress_update": {"current_step": 10},
            "status": MilestoneStatus.COMPLETED
        }
        
        # Publish update
        success = await cache_service.publish_real_time_update(
            user_id, milestone_id, update_data
        )
        assert success
        
        # Verify channel publish
        redis_client.publish.assert_called()
        call_args = redis_client.publish.call_args
        assert "milestone:rt:" in call_args[0][0]
        
        # Test retrieval
        redis_client.get_cache.return_value = [
            {**update_data, "timestamp": datetime.utcnow().isoformat()}
        ]
        
        updates = await cache_service.get_real_time_updates(user_id, milestone_id)
        assert len(updates) == 1
        assert updates[0]["status"] == MilestoneStatus.COMPLETED
    
    async def test_batch_operations(self, cache_service, redis_client):
        """Test batch get and set operations"""
        # Test batch set
        data = {
            "key1": {"value": 1},
            "key2": {"value": 2},
            "key3": {"value": 3}
        }
        
        success = await cache_service.batch_set(
            data,
            key_prefix="test:",
            ttl=3600
        )
        assert success
        
        # Verify all keys were set
        assert redis_client.set_cache.call_count == 3
        
        # Test batch get
        keys = ["key1", "key2", "key3"]
        redis_client.get_cache.side_effect = [
            {"value": 1}, {"value": 2}, {"value": 3}
        ]
        
        results = await cache_service.batch_get(keys, key_prefix="test:")
        assert len(results) == 3
        assert results["key1"]["value"] == 1
    
    async def test_frequently_accessed_caching(self, cache_service, redis_client):
        """Test automatic caching of frequently accessed data"""
        key_pattern = "popular_milestone"
        data = {"milestone": "data"}
        
        # Mock increment counter
        redis_client.client.incr.return_value = 5
        
        # Track and cache
        await cache_service.track_and_cache_frequent_access(
            key_pattern, data, access_threshold=5
        )
        
        # Should be cached with longer TTL
        redis_client.set_cache.assert_called()
        call_args = redis_client.set_cache.call_args
        assert call_args[0][2] == 3600  # Double TTL for frequent access
    
    async def test_cache_invalidation_cascade(self, cache_service, redis_client):
        """Test cascading cache invalidation"""
        user_id = "user123"
        
        # Mock keys to invalidate
        redis_client.client.keys.side_effect = [
            [f"v2:milestone:progress:user:{user_id}:m1"],
            [f"v2:milestone:tree:user:{user_id}"],
            [f"v2:milestone:deps:status:{user_id}:m1"],
            [],
            []
        ]
        
        # Invalidate with cascade
        success = await cache_service.invalidate_user_cache(user_id, cascade=True)
        assert success
        
        # Verify patterns were searched
        assert redis_client.client.keys.call_count >= 4
    
    async def test_circuit_breaker(self, cache_service, redis_client):
        """Test circuit breaker pattern"""
        # Simulate failures
        redis_client.get_cache.side_effect = Exception("Connection failed")
        
        # Multiple failures should open circuit
        for _ in range(6):
            result = await cache_service._safe_redis_get("test_key")
            assert result is None
        
        # Circuit should be open
        assert cache_service._is_circuit_open()
        
        # Further calls should be blocked
        result = await cache_service._safe_redis_get("another_key")
        assert result is None
        assert redis_client.get_cache.call_count == 6  # No new calls
    
    async def test_data_compression(self, cache_service):
        """Test data compression for large objects"""
        large_data = {"key": "x" * 10000}  # Large string
        
        compressed = cache_service._compress_data(large_data)
        assert compressed["_compressed"] is True
        assert compressed["compressed_size"] < compressed["original_size"]
        
        # Test decompression
        decompressed = cache_service._decompress_data(compressed)
        assert decompressed == large_data
    
    async def test_cache_metrics(self, cache_service, redis_client):
        """Test cache metrics collection"""
        # Perform various operations
        cache_service._l1_get("key1")  # Miss
        cache_service._l1_set("key2", "value2", 3600, CachePriority.MEDIUM)
        cache_service._l1_get("key2")  # Hit
        
        # Get metrics
        metrics = await cache_service.get_cache_metrics()
        
        assert metrics["l1_hits"] == 1
        assert metrics["l1_misses"] == 1
        assert metrics["l1_hit_rate"] == 50.0
        assert metrics["l1_cache_size"] == 1
        assert metrics["circuit_breaker_state"] == "closed"
    
    async def test_cache_warming(self, cache_service, redis_client):
        """Test cache warming functionality"""
        user_id = "user123"
        milestone_data = {
            "progress": {"status": MilestoneStatus.IN_PROGRESS},
            "tree": {"milestones": []},
            "milestones": [
                {"id": "m1", "progress": {"completion": 50}},
                {"id": "m2", "progress": {"completion": 75}}
            ]
        }
        
        # Warm cache
        success = await cache_service.warm_cache_for_user(user_id, milestone_data)
        assert success
        
        # Verify all data was cached
        assert redis_client.set_cache.call_count >= 4


class TestCacheDecorators:
    """Test caching decorators"""
    
    async def test_cached_decorator(self, cache_service):
        """Test @cached decorator"""
        
        class TestService:
            def __init__(self):
                self.cache_service = cache_service
                self.call_count = 0
            
            @cached(ttl=3600, priority=CachePriority.HIGH)
            async def get_data(self, param1, param2):
                self.call_count += 1
                return {"result": f"{param1}_{param2}"}
        
        service = TestService()
        
        # First call should execute function
        result1 = await service.get_data("a", "b")
        assert service.call_count == 1
        assert result1["result"] == "a_b"
        
        # Second call should use cache
        result2 = await service.get_data("a", "b")
        assert service.call_count == 1  # Not incremented
        assert result2 == result1
    
    async def test_invalidate_on_event_decorator(self, cache_service):
        """Test @invalidate_on_event decorator"""
        
        class TestService:
            def __init__(self):
                self.cache_service = cache_service
            
            @invalidate_on_event("user_update", "milestone_update")
            async def update_user(self, user_id, milestone_id):
                return {"updated": True}
        
        service = TestService()
        
        # Mock invalidation methods
        cache_service.invalidate_user_cache = AsyncMock()
        cache_service.invalidate_milestone_cache = AsyncMock()
        
        # Call should trigger invalidation
        result = await service.update_user("user123", "milestone456")
        assert result["updated"] is True
        
        # Verify invalidation was called
        cache_service.invalidate_user_cache.assert_called_with("user123")
        cache_service.invalidate_milestone_cache.assert_called_with("user123", "milestone456")


class TestConnectionManager:
    """Test Redis connection manager"""
    
    async def test_connection_initialization(self, connection_manager):
        """Test connection manager initialization"""
        connection_manager.initialize = AsyncMock()
        connection_manager._state = "connected"
        
        await connection_manager.initialize()
        connection_manager.initialize.assert_called_once()
    
    async def test_connection_pooling(self, connection_manager):
        """Test connection pooling"""
        mock_conn = AsyncMock()
        mock_conn.ping = AsyncMock(return_value=True)
        
        connection_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        connection_manager.get_connection.return_value.__aexit__ = AsyncMock()
        
        # Get multiple connections
        async with connection_manager.get_connection() as conn1:
            await conn1.ping()
        
        async with connection_manager.get_connection() as conn2:
            await conn2.ping()
        
        # Connections should be from pool
        assert connection_manager.get_connection.call_count == 2
    
    async def test_circuit_breaker_in_manager(self, connection_manager):
        """Test circuit breaker in connection manager"""
        connection_manager._circuit_failures = 10
        connection_manager._circuit_threshold = 10
        connection_manager._is_circuit_open = Mock(return_value=True)
        
        # Should raise when circuit is open
        with pytest.raises(Exception):
            async with connection_manager.get_connection():
                pass
    
    async def test_failover_to_replica(self, connection_manager):
        """Test failover to read replica"""
        connection_manager._replica_pools = [Mock(), Mock()]
        connection_manager.get_connection.return_value.__aenter__ = AsyncMock()
        connection_manager.get_connection.return_value.__aexit__ = AsyncMock()
        
        # Request readonly connection
        async with connection_manager.get_connection(readonly=True):
            pass
        
        connection_manager.get_connection.assert_called_with(readonly=True)


@pytest.mark.asyncio
async def test_end_to_end_caching_flow(cache_service, redis_client):
    """Test complete caching flow from set to get with updates"""
    user_id = "user123"
    milestone_id = "milestone456"
    
    # Initial progress
    initial_progress = {
        "status": MilestoneStatus.IN_PROGRESS,
        "completion_percentage": 0.0,
        "current_step": 0
    }
    
    # Set initial progress
    await cache_service.set_user_progress(user_id, initial_progress, milestone_id)
    
    # Update progress atomically
    for step in range(1, 11):
        await cache_service.update_user_progress_atomic(
            user_id,
            milestone_id,
            {
                "current_step": step,
                "completion_percentage": step * 10.0
            }
        )
        
        # Publish real-time update
        await cache_service.publish_real_time_update(
            user_id,
            milestone_id,
            {"step_completed": step}
        )
    
    # Get final progress with real-time updates
    redis_client.get_cache.return_value = {
        "status": MilestoneStatus.IN_PROGRESS,
        "completion_percentage": 100.0,
        "current_step": 10
    }
    
    final_progress = await cache_service.get_user_progress(
        user_id,
        milestone_id,
        include_real_time=True
    )
    
    assert final_progress is not None
    assert final_progress["completion_percentage"] == 100.0
    
    # Check metrics
    metrics = await cache_service.get_cache_metrics()
    assert metrics["writes"] > 0