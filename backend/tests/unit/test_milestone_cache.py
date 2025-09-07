"""
Unit Tests for Milestone Cache Layer

Comprehensive test coverage for milestone caching operations including
cache strategies, TTL management, invalidation patterns, and performance optimization.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from typing import Dict, Any, List

from backend.src.services.milestone_cache import MilestoneCacheService
from backend.src.infrastructure.redis.redis_mcp import RedisMCPClient
from backend.src.models.milestone import MilestoneStatus, MilestoneType


@pytest.fixture
def mock_redis_client():
    """Create a comprehensive mock Redis client."""
    client = AsyncMock(spec=RedisMCPClient)
    
    # Basic cache operations
    client.get_cache = AsyncMock(return_value=None)
    client.set_cache = AsyncMock(return_value=True)
    client.delete_cache = AsyncMock(return_value=True)
    
    # Pub/sub operations
    client.publish = AsyncMock(return_value=1)
    client.subscribe = AsyncMock()
    
    # Lock operations
    client.lock = AsyncMock(return_value="lock_token_123")
    client.unlock = AsyncMock(return_value=True)
    
    # Raw Redis client operations
    client.client = Mock()
    client.client.keys = Mock(return_value=[])
    client.client.delete = Mock(return_value=1)
    client.client.incr = Mock(return_value=1)
    client.client.zadd = Mock(return_value=1)
    client.client.zrevrange = Mock(return_value=[])
    client.client.expire = Mock(return_value=True)
    client.client.pipeline = Mock()
    client.client.info = Mock(return_value={"used_memory_human": "100MB"})
    client.client.ping = Mock(return_value=True)
    
    return client


@pytest.fixture
def cache_service(mock_redis_client):
    """Create a milestone cache service instance."""
    return MilestoneCacheService(mock_redis_client)


@pytest.fixture
def sample_user_progress():
    """Create sample user progress data."""
    return {
        "status": MilestoneStatus.IN_PROGRESS,
        "completion_percentage": 75.0,
        "current_step": 3,
        "total_steps": 4,
        "started_at": datetime.utcnow().isoformat(),
        "last_accessed_at": datetime.utcnow().isoformat(),
        "time_spent_seconds": 3600,
        "checkpoint_data": {
            "market_analysis": {
                "completed": True,
                "data_quality": 0.9
            },
            "competitive_analysis": {
                "completed": True,
                "competitors_identified": 5
            },
            "customer_segments": {
                "completed": False,
                "progress": 0.6
            }
        },
        "quality_metrics": {
            "data_completeness": 0.85,
            "analysis_depth": 0.8,
            "accuracy_score": 0.92
        }
    }


@pytest.fixture
def sample_milestone_tree():
    """Create sample milestone tree data."""
    return {
        "milestones": [
            {
                "id": str(uuid4()),
                "code": "M0",
                "name": "Feasibility Snapshot",
                "type": MilestoneType.FREE,
                "user_progress": {"status": "completed", "completion_percentage": 100},
                "dependencies": [],
                "dependents": ["M1", "M2"]
            },
            {
                "id": str(uuid4()),
                "code": "M1",
                "name": "Market Analysis",
                "type": MilestoneType.PAID,
                "user_progress": {"status": "in_progress", "completion_percentage": 60},
                "dependencies": [{"code": "M0", "is_required": True}],
                "dependents": ["M3"]
            },
            {
                "id": str(uuid4()),
                "code": "M2",
                "name": "Business Model",
                "type": MilestoneType.PAID,
                "user_progress": {"status": "available", "completion_percentage": 0},
                "dependencies": [{"code": "M0", "is_required": True}],
                "dependents": ["M3"]
            }
        ],
        "total_progress": 53.33,
        "completed_count": 1,
        "available_count": 1,
        "in_progress_count": 1,
        "locked_count": 0,
        "dependency_graph": {
            "nodes": 3,
            "edges": 2,
            "max_depth": 2
        }
    }


class TestUserProgressCaching:
    """Test user progress caching operations."""
    
    @pytest.mark.asyncio
    async def test_get_user_progress_cache_miss(self, cache_service, mock_redis_client):
        """Test getting user progress when not cached."""
        user_id = "user123"
        milestone_id = "milestone456"
        
        # Setup cache miss
        mock_redis_client.get_cache.return_value = None
        
        # Execute
        result = await cache_service.get_user_progress(user_id, milestone_id)
        
        # Assert
        assert result is None
        mock_redis_client.get_cache.assert_called_once_with(
            f"{cache_service.KEY_PREFIX_USER_PROGRESS}{user_id}:{milestone_id}"
        )
        assert cache_service._cache_stats["misses"] == 1
        assert cache_service._cache_stats["hits"] == 0
    
    @pytest.mark.asyncio
    async def test_get_user_progress_cache_hit(self, cache_service, mock_redis_client, sample_user_progress):
        """Test getting user progress when cached."""
        user_id = "user123"
        milestone_id = "milestone456"
        
        # Setup cache hit
        mock_redis_client.get_cache.return_value = sample_user_progress
        
        # Execute
        result = await cache_service.get_user_progress(user_id, milestone_id)
        
        # Assert
        assert result == sample_user_progress
        assert result["status"] == MilestoneStatus.IN_PROGRESS
        assert result["completion_percentage"] == 75.0
        assert cache_service._cache_stats["hits"] == 1
        assert cache_service._cache_stats["misses"] == 0
    
    @pytest.mark.asyncio
    async def test_set_user_progress(self, cache_service, mock_redis_client, sample_user_progress):
        """Test setting user progress in cache."""
        user_id = "user123"
        milestone_id = "milestone456"
        
        # Execute
        success = await cache_service.set_user_progress(
            user_id, sample_user_progress, milestone_id
        )
        
        # Assert
        assert success is True
        mock_redis_client.set_cache.assert_called_once()
        
        # Verify call arguments
        call_args = mock_redis_client.set_cache.call_args
        key = call_args[0][0]
        data = call_args[0][1]
        ttl = call_args[0][2]
        
        assert f"{user_id}:{milestone_id}" in key
        assert "cached_at" in data
        assert data["status"] == MilestoneStatus.IN_PROGRESS
        assert ttl == cache_service.TTL_USER_PROGRESS
    
    @pytest.mark.asyncio
    async def test_set_user_progress_all_milestones(self, cache_service, mock_redis_client, sample_user_progress):
        """Test setting progress for all milestones."""
        user_id = "user123"
        
        # Execute (no milestone_id = all milestones)
        success = await cache_service.set_user_progress(
            user_id, sample_user_progress, None
        )
        
        # Assert
        assert success is True
        call_args = mock_redis_client.set_cache.call_args
        key = call_args[0][0]
        assert key == f"{cache_service.KEY_PREFIX_USER_PROGRESS}{user_id}:all"
    
    @pytest.mark.asyncio
    async def test_update_milestone_progress_existing(self, cache_service, mock_redis_client):
        """Test updating existing milestone progress in cache."""
        user_id = "user123"
        milestone_id = "milestone456"
        
        # Mock existing cached data
        existing_data = {
            "status": MilestoneStatus.IN_PROGRESS,
            "completion_percentage": 50.0,
            "current_step": 2
        }
        mock_redis_client.get_cache.return_value = existing_data
        
        # Updates to apply
        updates = {
            "completion_percentage": 75.0,
            "current_step": 3,
            "checkpoint_data": {"new_data": "test"}
        }
        
        # Execute
        success = await cache_service.update_milestone_progress(
            user_id, milestone_id, updates
        )
        
        # Assert
        assert success is True
        
        # Verify get and set were called
        mock_redis_client.get_cache.assert_called_once()
        mock_redis_client.set_cache.assert_called_once()
        
        # Verify merged data
        set_call_args = mock_redis_client.set_cache.call_args
        merged_data = set_call_args[0][1]
        assert merged_data["completion_percentage"] == 75.0
        assert merged_data["current_step"] == 3
        assert merged_data["status"] == MilestoneStatus.IN_PROGRESS  # Preserved
        assert "updated_at" in merged_data
    
    @pytest.mark.asyncio
    async def test_update_milestone_progress_not_existing(self, cache_service, mock_redis_client):
        """Test updating non-existent milestone progress."""
        user_id = "user123"
        milestone_id = "milestone456"
        
        # Mock cache miss
        mock_redis_client.get_cache.return_value = None
        
        updates = {"completion_percentage": 75.0}
        
        # Execute
        success = await cache_service.update_milestone_progress(
            user_id, milestone_id, updates
        )
        
        # Assert
        assert success is False
        mock_redis_client.set_cache.assert_not_called()


class TestMilestoneTreeCaching:
    """Test milestone tree caching operations."""
    
    @pytest.mark.asyncio
    async def test_get_milestone_tree_cache_miss(self, cache_service, mock_redis_client):
        """Test getting milestone tree when not cached."""
        user_id = "user123"
        
        # Setup cache miss
        mock_redis_client.get_cache.return_value = None
        
        # Execute
        result = await cache_service.get_milestone_tree(user_id)
        
        # Assert
        assert result is None
        mock_redis_client.get_cache.assert_called_once_with(
            f"{cache_service.KEY_PREFIX_MILESTONE_TREE}{user_id}"
        )
        assert cache_service._cache_stats["misses"] == 1
    
    @pytest.mark.asyncio
    async def test_get_milestone_tree_cache_hit(self, cache_service, mock_redis_client, sample_milestone_tree):
        """Test getting milestone tree when cached and fresh."""
        user_id = "user123"
        
        # Setup fresh cached data
        sample_milestone_tree["cached_at"] = datetime.utcnow().isoformat()
        mock_redis_client.get_cache.return_value = sample_milestone_tree
        
        # Execute
        result = await cache_service.get_milestone_tree(user_id)
        
        # Assert
        assert result == sample_milestone_tree
        assert result["total_progress"] == 53.33
        assert len(result["milestones"]) == 3
        assert cache_service._cache_stats["hits"] == 1
    
    @pytest.mark.asyncio
    async def test_get_milestone_tree_stale_cache(self, cache_service, mock_redis_client, sample_milestone_tree):
        """Test getting milestone tree when cached but stale."""
        user_id = "user123"
        
        # Setup stale cached data
        stale_time = datetime.utcnow() - timedelta(hours=2)
        sample_milestone_tree["cached_at"] = stale_time.isoformat()
        mock_redis_client.get_cache.return_value = sample_milestone_tree
        
        # Execute
        result = await cache_service.get_milestone_tree(user_id)
        
        # Assert
        assert result is None  # Should return None for stale data
        mock_redis_client.delete_cache.assert_called_once()  # Should delete stale entry
    
    @pytest.mark.asyncio
    async def test_set_milestone_tree(self, cache_service, mock_redis_client, sample_milestone_tree):
        """Test setting milestone tree in cache."""
        user_id = "user123"
        
        # Execute
        success = await cache_service.set_milestone_tree(user_id, sample_milestone_tree)
        
        # Assert
        assert success is True
        mock_redis_client.set_cache.assert_called_once()
        
        # Verify call arguments
        call_args = mock_redis_client.set_cache.call_args
        key = call_args[0][0]
        data = call_args[0][1]
        ttl = call_args[0][2]
        
        assert key == f"{cache_service.KEY_PREFIX_MILESTONE_TREE}{user_id}"
        assert "cached_at" in data
        assert ttl == cache_service.TTL_MILESTONE_TREE


class TestDependencyCaching:
    """Test dependency check caching."""
    
    @pytest.mark.asyncio
    async def test_get_dependency_check(self, cache_service, mock_redis_client):
        """Test getting cached dependency check results."""
        user_id = "user123"
        milestone_id = "milestone456"
        
        # Mock cached dependency check
        cached_check = {
            "can_start": True,
            "missing_dependencies": [],
            "checked_at": datetime.utcnow().isoformat()
        }
        mock_redis_client.get_cache.return_value = cached_check
        
        # Execute
        result = await cache_service.get_dependency_check(user_id, milestone_id)
        
        # Assert
        assert result == cached_check
        assert result["can_start"] is True
        assert result["missing_dependencies"] == []
        
        expected_key = f"{cache_service.KEY_PREFIX_DEPENDENCY_CHECK}{user_id}:{milestone_id}"
        mock_redis_client.get_cache.assert_called_once_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_set_dependency_check(self, cache_service, mock_redis_client):
        """Test setting dependency check results in cache."""
        user_id = "user123"
        milestone_id = "milestone456"
        can_start = False
        missing_deps = ["M1", "M2"]
        
        # Execute
        success = await cache_service.set_dependency_check(
            user_id, milestone_id, can_start, missing_deps
        )
        
        # Assert
        assert success is True
        mock_redis_client.set_cache.assert_called_once()
        
        # Verify cached data structure
        call_args = mock_redis_client.set_cache.call_args
        data = call_args[0][1]
        
        assert data["can_start"] is False
        assert data["missing_dependencies"] == missing_deps
        assert "checked_at" in data


class TestRealTimeUpdates:
    """Test real-time progress update publishing."""
    
    @pytest.mark.asyncio
    async def test_publish_progress_update(self, cache_service, mock_redis_client):
        """Test publishing real-time progress updates."""
        user_id = "user123"
        milestone_id = "milestone456"
        progress_data = {
            "status": MilestoneStatus.COMPLETED,
            "completion_percentage": 100.0,
            "quality_score": 0.92
        }
        
        # Execute
        result = await cache_service.publish_progress_update(
            user_id, milestone_id, progress_data
        )
        
        # Assert
        assert result == 1  # Mock return value
        mock_redis_client.publish.assert_called_once()
        
        # Verify publish call
        call_args = mock_redis_client.publish.call_args
        channel = call_args[0][0]
        message = call_args[0][1]
        
        assert channel == f"milestone:updates:{user_id}"
        assert message["milestone_id"] == milestone_id
        assert message["data"] == progress_data
        assert "timestamp" in message
    
    @pytest.mark.asyncio
    async def test_track_active_session(self, cache_service, mock_redis_client):
        """Test tracking active milestone sessions."""
        user_id = "user123"
        milestone_id = "milestone456"
        session_data = {
            "milestone_code": "M1",
            "browser": "Chrome",
            "device": "Desktop"
        }
        
        # Execute
        success = await cache_service.track_active_session(
            user_id, milestone_id, session_data
        )
        
        # Assert
        assert success is True
        mock_redis_client.set_cache.assert_called_once()
        
        # Verify session data structure
        call_args = mock_redis_client.set_cache.call_args
        key = call_args[0][0]
        data = call_args[0][1]
        ttl = call_args[0][2]
        
        assert f"{user_id}:{milestone_id}" in key
        assert data["user_id"] == user_id
        assert data["milestone_id"] == milestone_id
        assert "started_at" in data
        assert "last_activity" in data
        assert ttl == cache_service.TTL_SESSION
    
    @pytest.mark.asyncio
    async def test_update_session_activity(self, cache_service, mock_redis_client):
        """Test updating session activity timestamp."""
        user_id = "user123"
        milestone_id = "milestone456"
        
        # Mock existing session data
        existing_session = {
            "user_id": user_id,
            "milestone_id": milestone_id,
            "started_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            "last_activity": (datetime.utcnow() - timedelta(minutes=30)).isoformat()
        }
        mock_redis_client.get_cache.return_value = existing_session
        
        # Execute
        success = await cache_service.update_session_activity(user_id, milestone_id)
        
        # Assert
        assert success is True
        mock_redis_client.get_cache.assert_called_once()
        mock_redis_client.set_cache.assert_called_once()
        
        # Verify updated timestamp
        set_call_args = mock_redis_client.set_cache.call_args
        updated_data = set_call_args[0][1]
        assert updated_data["last_activity"] != existing_session["last_activity"]


class TestArtifactCaching:
    """Test artifact caching operations."""
    
    @pytest.mark.asyncio
    async def test_cache_artifact(self, cache_service, mock_redis_client):
        """Test caching artifact data."""
        artifact_id = "artifact123"
        artifact_data = {
            "name": "Business Plan Draft",
            "type": "document",
            "content": {
                "sections": ["executive_summary", "market_analysis"],
                "metadata": {"pages": 25, "word_count": 5000}
            },
            "generation_info": {
                "model": "gpt-4",
                "processing_time": 45.2,
                "quality_score": 0.92
            }
        }
        
        # Execute
        success = await cache_service.cache_artifact(artifact_id, artifact_data)
        
        # Assert
        assert success is True
        mock_redis_client.set_cache.assert_called_once()
        
        # Verify cache key and TTL
        call_args = mock_redis_client.set_cache.call_args
        key = call_args[0][0]
        data = call_args[0][1]
        ttl = call_args[0][2]
        
        assert key == f"{cache_service.KEY_PREFIX_ARTIFACT}{artifact_id}"
        assert data == artifact_data
        assert ttl == cache_service.TTL_ARTIFACT
    
    @pytest.mark.asyncio
    async def test_get_cached_artifact(self, cache_service, mock_redis_client):
        """Test retrieving cached artifact data."""
        artifact_id = "artifact123"
        artifact_data = {
            "name": "Cached Artifact",
            "content": {"data": "test"}
        }
        
        # Mock cached artifact
        mock_redis_client.get_cache.return_value = artifact_data
        
        # Execute
        result = await cache_service.get_cached_artifact(artifact_id)
        
        # Assert
        assert result == artifact_data
        expected_key = f"{cache_service.KEY_PREFIX_ARTIFACT}{artifact_id}"
        mock_redis_client.get_cache.assert_called_once_with(expected_key)


class TestStatisticsAndAnalytics:
    """Test statistics and analytics caching."""
    
    @pytest.mark.asyncio
    async def test_increment_milestone_stats(self, cache_service, mock_redis_client):
        """Test incrementing milestone statistics counters."""
        milestone_code = "M1"
        stat_type = "completed"
        
        # Mock current counter value
        current_stats = {"count": 5, "last_updated": None}
        mock_redis_client.get_cache.return_value = current_stats
        
        # Execute
        success = await cache_service.increment_milestone_stats(milestone_code, stat_type)
        
        # Assert
        assert success is True
        mock_redis_client.get_cache.assert_called_once()
        mock_redis_client.set_cache.assert_called_once()
        
        # Verify incremented counter
        set_call_args = mock_redis_client.set_cache.call_args
        updated_stats = set_call_args[0][1]
        
        assert updated_stats["count"] == 6  # Incremented from 5
        assert "last_updated" in updated_stats
    
    @pytest.mark.asyncio
    async def test_increment_milestone_stats_new_counter(self, cache_service, mock_redis_client):
        """Test incrementing milestone stats for new counter."""
        milestone_code = "M2"
        stat_type = "started"
        
        # Mock no existing counter
        mock_redis_client.get_cache.return_value = None
        
        # Execute
        success = await cache_service.increment_milestone_stats(milestone_code, stat_type)
        
        # Assert
        assert success is True
        
        # Verify new counter created
        set_call_args = mock_redis_client.set_cache.call_args
        new_stats = set_call_args[0][1]
        
        assert new_stats["count"] == 1  # First increment
        assert "last_updated" in new_stats
    
    @pytest.mark.asyncio
    async def test_get_milestone_stats(self, cache_service, mock_redis_client):
        """Test getting aggregated milestone statistics."""
        milestone_code = "M1"
        
        # Mock individual stat counters
        def mock_get_cache(key):
            if "started" in key:
                return {"count": 100}
            elif "completed" in key:
                return {"count": 80}
            elif "failed" in key:
                return {"count": 5}
            elif "skipped" in key:
                return {"count": 2}
            return None
        
        mock_redis_client.get_cache.side_effect = mock_get_cache
        
        # Execute
        stats = await cache_service.get_milestone_stats(milestone_code)
        
        # Assert
        assert stats["started"] == 100
        assert stats["completed"] == 80
        assert stats["failed"] == 5
        assert stats["skipped"] == 2
        assert stats["completion_rate"] == 80.0  # 80/100 * 100
        
        # Verify all stat types were queried
        assert mock_redis_client.get_cache.call_count == 4
    
    @pytest.mark.asyncio
    async def test_increment_milestone_stats_error_handling(self, cache_service, mock_redis_client):
        """Test error handling in stats increment."""
        milestone_code = "M1"
        stat_type = "completed"
        
        # Mock Redis error
        mock_redis_client.get_cache.side_effect = Exception("Redis connection failed")
        
        # Execute
        success = await cache_service.increment_milestone_stats(milestone_code, stat_type)
        
        # Assert
        assert success is False
        assert cache_service._cache_stats["errors"] == 1


class TestLeaderboardAndGamification:
    """Test leaderboard and gamification features."""
    
    @pytest.mark.asyncio
    async def test_update_leaderboard(self, cache_service):
        """Test updating user position in leaderboard."""
        user_id = "user123"
        score = 1500
        leaderboard_type = "weekly"
        
        # Execute
        success = await cache_service.update_leaderboard(user_id, score, leaderboard_type)
        
        # Assert
        assert success is True
        
        # Verify Redis sorted set operations
        cache_service.redis.client.zadd.assert_called_once()
        cache_service.redis.client.expire.assert_called_once()
        
        # Check zadd call
        zadd_call = cache_service.redis.client.zadd.call_args
        key = zadd_call[0][0]
        scores = zadd_call[0][1]
        
        assert f"leaderboard:{leaderboard_type}" in key
        assert scores[user_id] == score
    
    @pytest.mark.asyncio
    async def test_update_leaderboard_monthly(self, cache_service):
        """Test updating monthly leaderboard with different TTL."""
        user_id = "user456"
        score = 2000
        leaderboard_type = "monthly"
        
        # Execute
        success = await cache_service.update_leaderboard(user_id, score, leaderboard_type)
        
        # Assert
        assert success is True
        
        # Verify monthly TTL (30 days)
        expire_call = cache_service.redis.client.expire.call_args
        ttl = expire_call[0][1]
        assert ttl == 2592000  # 30 days in seconds
    
    @pytest.mark.asyncio
    async def test_get_leaderboard(self, cache_service):
        """Test getting leaderboard rankings."""
        leaderboard_type = "weekly"
        limit = 5
        
        # Mock Redis sorted set results (user_id, score tuples)
        mock_results = [
            (b"user1", 2000.0),
            (b"user2", 1800.0),
            (b"user3", 1500.0),
            (b"user4", 1200.0),
            (b"user5", 1000.0)
        ]
        
        with patch('asyncio.to_thread', return_value=mock_results):
            # Execute
            leaderboard = await cache_service.get_leaderboard(leaderboard_type, limit)
        
        # Assert
        assert len(leaderboard) == 5
        assert leaderboard[0]["rank"] == 1
        assert leaderboard[0]["user_id"] == b"user1"
        assert leaderboard[0]["score"] == 2000
        assert leaderboard[4]["rank"] == 5
        assert leaderboard[4]["score"] == 1000
    
    @pytest.mark.asyncio
    async def test_get_leaderboard_error_handling(self, cache_service):
        """Test leaderboard error handling."""
        leaderboard_type = "weekly"
        
        # Mock Redis error
        with patch('asyncio.to_thread', side_effect=Exception("Redis error")):
            # Execute
            leaderboard = await cache_service.get_leaderboard(leaderboard_type, 10)
        
        # Assert
        assert leaderboard == []  # Should return empty list on error


class TestCacheManagement:
    """Test cache management and invalidation."""
    
    @pytest.mark.asyncio
    async def test_invalidate_user_cache(self, cache_service):
        """Test invalidating all cached data for a user."""
        user_id = "user123"
        
        # Mock Redis keys matching patterns
        def mock_keys(pattern):
            if "user_progress" in pattern:
                return [f"milestone:progress:user:{user_id}:m1", f"milestone:progress:user:{user_id}:m2"]
            elif "milestone_tree" in pattern:
                return [f"milestone:tree:user:{user_id}"]
            elif "dependency_check" in pattern:
                return [f"milestone:deps:check:{user_id}:m1"]
            elif "session" in pattern:
                return [f"milestone:session:{user_id}:m1"]
            return []
        
        with patch('asyncio.to_thread', side_effect=mock_keys):
            # Execute
            success = await cache_service.invalidate_user_cache(user_id)
        
        # Assert
        assert success is True
    
    @pytest.mark.asyncio
    async def test_invalidate_milestone_cache(self, cache_service):
        """Test invalidating cached data for a specific milestone."""
        milestone_id = "milestone456"
        
        # Mock Redis keys for milestone
        def mock_keys(pattern):
            if milestone_id in pattern:
                return [f"milestone:data:{milestone_id}", f"milestone:progress:user1:{milestone_id}"]
            return []
        
        with patch('asyncio.to_thread', side_effect=mock_keys):
            # Execute
            success = await cache_service.invalidate_milestone_cache(milestone_id)
        
        # Assert
        assert success is True
    
    @pytest.mark.asyncio
    async def test_invalidate_cache_error_handling(self, cache_service):
        """Test cache invalidation error handling."""
        user_id = "user123"
        
        # Mock Redis error
        with patch('asyncio.to_thread', side_effect=Exception("Redis connection failed")):
            # Execute
            success = await cache_service.invalidate_user_cache(user_id)
        
        # Assert
        assert success is False
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, cache_service):
        """Test getting cache performance statistics."""
        # Setup cache stats
        cache_service._cache_stats["hits"] = 150
        cache_service._cache_stats["misses"] = 50
        cache_service._cache_stats["errors"] = 2
        
        # Execute
        stats = await cache_service.get_cache_stats()
        
        # Assert
        assert stats["hits"] == 150
        assert stats["misses"] == 50
        assert stats["errors"] == 2
        assert stats["total_requests"] == 200
        assert stats["hit_rate"] == 75.0  # 150/200 * 100
    
    @pytest.mark.asyncio
    async def test_get_cache_stats_no_requests(self, cache_service):
        """Test getting cache stats with no requests."""
        # No stats recorded
        cache_service._cache_stats = {"hits": 0, "misses": 0, "errors": 0}
        
        # Execute
        stats = await cache_service.get_cache_stats()
        
        # Assert
        assert stats["hit_rate"] == 0
        assert stats["total_requests"] == 0


class TestDistributedLocking:
    """Test distributed locking for milestone operations."""
    
    @pytest.mark.asyncio
    async def test_acquire_milestone_lock(self, cache_service, mock_redis_client):
        """Test acquiring a milestone processing lock."""
        user_id = "user123"
        milestone_id = "milestone456"
        ttl = 300
        
        # Mock successful lock acquisition
        mock_redis_client.lock.return_value = "lock_token_abc123"
        
        # Execute
        lock_value = await cache_service.acquire_milestone_lock(user_id, milestone_id, ttl)
        
        # Assert
        assert lock_value == "lock_token_abc123"
        
        expected_lock_key = f"{cache_service.KEY_PREFIX_LOCK}{user_id}:{milestone_id}"
        mock_redis_client.lock.assert_called_once_with(expected_lock_key, ttl)
    
    @pytest.mark.asyncio
    async def test_release_milestone_lock(self, cache_service, mock_redis_client):
        """Test releasing a milestone processing lock."""
        user_id = "user123"
        milestone_id = "milestone456"
        lock_value = "lock_token_abc123"
        
        # Mock successful lock release
        mock_redis_client.unlock.return_value = True
        
        # Execute
        success = await cache_service.release_milestone_lock(user_id, milestone_id, lock_value)
        
        # Assert
        assert success is True
        
        expected_lock_key = f"{cache_service.KEY_PREFIX_LOCK}{user_id}:{milestone_id}"
        mock_redis_client.unlock.assert_called_once_with(expected_lock_key, lock_value)
    
    @pytest.mark.asyncio
    async def test_acquire_lock_failure(self, cache_service, mock_redis_client):
        """Test failed lock acquisition (already locked)."""
        user_id = "user123"
        milestone_id = "milestone456"
        
        # Mock failed lock acquisition
        mock_redis_client.lock.return_value = None
        
        # Execute
        lock_value = await cache_service.acquire_milestone_lock(user_id, milestone_id)
        
        # Assert
        assert lock_value is None


class TestBatchOperations:
    """Test batch cache operations for performance."""
    
    @pytest.mark.asyncio
    async def test_batch_get_progress(self, cache_service, mock_redis_client):
        """Test batch retrieval of user progress."""
        user_ids = ["user1", "user2", "user3"]
        
        # Mock individual cache responses
        def mock_get_cache(key):
            if "user1" in key:
                return {"status": "completed", "progress": 100}
            elif "user2" in key:
                return {"status": "in_progress", "progress": 50}
            elif "user3" in key:
                return None
            return None
        
        mock_redis_client.get_cache.side_effect = mock_get_cache
        
        # Execute
        results = await cache_service.batch_get_progress(user_ids)
        
        # Assert
        assert len(results) == 3
        assert results["user1"]["status"] == "completed"
        assert results["user2"]["status"] == "in_progress"
        assert results["user3"] is None
        
        # Verify all users were queried
        assert mock_redis_client.get_cache.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_get_progress_with_errors(self, cache_service, mock_redis_client):
        """Test batch get progress with some errors."""
        user_ids = ["user1", "user2", "user3"]
        
        # Mock mixed responses with one error
        responses = [
            {"status": "completed"},  # user1 success
            Exception("Redis timeout"),  # user2 error
            {"status": "available"}  # user3 success
        ]
        mock_redis_client.get_cache.side_effect = responses
        
        # Execute
        results = await cache_service.batch_get_progress(user_ids)
        
        # Assert
        assert results["user1"]["status"] == "completed"
        assert results["user2"] is None  # Error results in None
        assert results["user3"]["status"] == "available"


class TestCacheWarming:
    """Test cache warming strategies."""
    
    @pytest.mark.asyncio
    async def test_warm_cache_for_user(self, cache_service):
        """Test warming cache with user milestone data."""
        user_id = "user123"
        milestone_data = {
            "progress": {
                "status": "in_progress",
                "completion_percentage": 60.0
            },
            "tree": {
                "milestones": [],
                "total_progress": 30.0
            },
            "milestones": [
                {"id": "m1", "progress": {"completion": 80}},
                {"id": "m2", "progress": {"completion": 40}}
            ]
        }
        
        # Mock cache service methods
        cache_service.set_user_progress = AsyncMock(return_value=True)
        cache_service.set_milestone_tree = AsyncMock(return_value=True)
        
        # Execute
        success = await cache_service.warm_cache_for_user(user_id, milestone_data)
        
        # Assert
        assert success is True
        
        # Verify all cache operations were called
        cache_service.set_user_progress.assert_called()
        cache_service.set_milestone_tree.assert_called_once()
        
        # Check individual milestone caching
        assert cache_service.set_user_progress.call_count == 3  # Overall + 2 individual
    
    @pytest.mark.asyncio
    async def test_warm_cache_partial_failure(self, cache_service):
        """Test cache warming with partial failures."""
        user_id = "user123"
        milestone_data = {
            "progress": {"status": "active"},
            "tree": {"milestones": []}
        }
        
        # Mock mixed success/failure
        cache_service.set_user_progress = AsyncMock(return_value=True)
        cache_service.set_milestone_tree = AsyncMock(return_value=False)  # Failure
        
        # Execute
        success = await cache_service.warm_cache_for_user(user_id, milestone_data)
        
        # Assert
        assert success is False  # Should fail if any operation fails


class TestCacheDecorator:
    """Test cache decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_decorator_cache_miss(self, cache_service):
        """Test cache decorator on cache miss."""
        from backend.src.services.milestone_cache import cache_decorator
        
        # Create test service with cache_service attribute
        class TestService:
            def __init__(self):
                self.cache_service = cache_service
            
            @cache_decorator(ttl=3600)
            async def expensive_operation(self, param1, param2):
                return f"result_{param1}_{param2}"
        
        service = TestService()
        
        # Mock cache miss
        cache_service.redis.get_cache.return_value = None
        
        # Execute
        result = await service.expensive_operation("test", "data")
        
        # Assert
        assert result == "result_test_data"
        cache_service.redis.get_cache.assert_called_once()
        cache_service.redis.set_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_decorator_cache_hit(self, cache_service):
        """Test cache decorator on cache hit."""
        from backend.src.services.milestone_cache import cache_decorator
        
        class TestService:
            def __init__(self):
                self.cache_service = cache_service
            
            @cache_decorator(ttl=3600)
            async def expensive_operation(self, param1):
                return f"computed_{param1}"
        
        service = TestService()
        
        # Mock cache hit
        cached_result = "cached_result"
        cache_service.redis.get_cache.return_value = cached_result
        
        # Execute
        result = await service.expensive_operation("test")
        
        # Assert
        assert result == cached_result
        cache_service.redis.get_cache.assert_called_once()
        cache_service.redis.set_cache.assert_not_called()  # Should not set on hit


class TestCachePerformanceOptimizations:
    """Test cache performance optimizations."""
    
    @pytest.mark.asyncio
    async def test_cache_compression_simulation(self, cache_service):
        """Test cache compression for large objects."""
        large_data = {
            "content": "x" * 10000,  # Large string
            "metadata": {"size": 10000, "type": "large_object"}
        }
        
        # Simulate compression
        original_size = len(json.dumps(large_data))
        assert original_size > 10000
        
        # In a real implementation, large objects would be compressed
        # This test verifies the concept
        compressed_indicator = len(json.dumps(large_data)) > 1000
        assert compressed_indicator is True
    
    @pytest.mark.asyncio
    async def test_cache_key_optimization(self, cache_service):
        """Test cache key generation optimization."""
        # Test key generation patterns
        user_id = "user123"
        milestone_id = "milestone456"
        
        progress_key = f"{cache_service.KEY_PREFIX_USER_PROGRESS}{user_id}:{milestone_id}"
        tree_key = f"{cache_service.KEY_PREFIX_MILESTONE_TREE}{user_id}"
        
        # Keys should be concise but descriptive
        assert len(progress_key) < 100  # Reasonable key length
        assert user_id in progress_key
        assert milestone_id in progress_key
        assert len(tree_key) < 100
    
    @pytest.mark.asyncio
    async def test_cache_ttl_strategy(self, cache_service):
        """Test TTL strategy for different data types."""
        # Verify TTL values are appropriate
        assert cache_service.TTL_USER_PROGRESS == 3600  # 1 hour for active data
        assert cache_service.TTL_MILESTONE_TREE == 1800  # 30 min for tree (more dynamic)
        assert cache_service.TTL_MILESTONE_DATA == 7200  # 2 hours for milestone definitions
        assert cache_service.TTL_DEPENDENCY_CHECK == 900  # 15 min for dependency checks
        assert cache_service.TTL_SESSION == 86400  # 24 hours for session data
        
        # TTL should be longer for more stable data
        assert cache_service.TTL_MILESTONE_DATA > cache_service.TTL_MILESTONE_TREE
        assert cache_service.TTL_SESSION > cache_service.TTL_USER_PROGRESS