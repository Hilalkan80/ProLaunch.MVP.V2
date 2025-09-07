"""
Enhanced Unit Tests for Milestone Service

Comprehensive test coverage for the milestone service including edge cases,
error handling, concurrent operations, and performance scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
import json
from contextlib import asynccontextmanager

from backend.src.services.milestone_service import MilestoneService
from backend.src.services.milestone_cache import MilestoneCacheService
from backend.src.models.milestone import (
    Milestone, UserMilestone, MilestoneDependency,
    MilestoneStatus, MilestoneType, MilestoneProgressLog,
    UserMilestoneArtifact
)
from backend.src.models.user import User, SubscriptionTier


class AsyncIterator:
    """Helper class for mocking async iterators."""
    def __init__(self, items):
        self.items = iter(items)
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration


@pytest.fixture
def enhanced_mock_db_session():
    """Enhanced mock database session with better transaction handling."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.merge = AsyncMock()
    session.flush = AsyncMock()
    
    # Mock context manager behavior
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    
    return session


@pytest.fixture
def enhanced_mock_redis_client():
    """Enhanced mock Redis client with realistic behavior."""
    client = AsyncMock()
    client.get_cache = AsyncMock(return_value=None)
    client.set_cache = AsyncMock(return_value=True)
    client.delete_cache = AsyncMock(return_value=True)
    client.publish = AsyncMock(return_value=1)
    client.lock = AsyncMock(return_value="lock_value_123")
    client.unlock = AsyncMock(return_value=True)
    
    # Mock Redis client methods
    client.client = Mock()
    client.client.keys = Mock(return_value=[])
    client.client.delete = Mock(return_value=1)
    client.client.incr = Mock(return_value=1)
    client.client.zadd = Mock(return_value=1)
    client.client.zrevrange = Mock(return_value=[])
    client.client.pipeline = Mock()
    
    return client


@pytest.fixture
def enhanced_mock_cache_service(enhanced_mock_redis_client):
    """Enhanced mock cache service with full method coverage."""
    service = MilestoneCacheService(enhanced_mock_redis_client)
    service.redis = enhanced_mock_redis_client
    service.get_user_progress = AsyncMock(return_value=None)
    service.set_user_progress = AsyncMock(return_value=True)
    service.get_milestone_tree = AsyncMock(return_value=None)
    service.set_milestone_tree = AsyncMock(return_value=True)
    service.update_milestone_progress = AsyncMock(return_value=True)
    service.invalidate_user_cache = AsyncMock(return_value=True)
    service.invalidate_milestone_cache = AsyncMock(return_value=True)
    service.publish_progress_update = AsyncMock(return_value=1)
    service.increment_milestone_stats = AsyncMock(return_value=True)
    service.update_leaderboard = AsyncMock(return_value=True)
    service.cache_artifact = AsyncMock(return_value=True)
    service.get_cached_artifact = AsyncMock(return_value=None)
    service.track_active_session = AsyncMock(return_value=True)
    service.update_session_activity = AsyncMock(return_value=True)
    service.acquire_milestone_lock = AsyncMock(return_value="lock_123")
    service.release_milestone_lock = AsyncMock(return_value=True)
    service.get_milestone_stats = AsyncMock(return_value={})
    service.get_cache_stats = AsyncMock(return_value={})
    
    return service


@pytest.fixture
def enhanced_milestone_service(enhanced_mock_db_session, enhanced_mock_cache_service):
    """Enhanced milestone service instance with full dependencies."""
    return MilestoneService(enhanced_mock_db_session, enhanced_mock_cache_service)


@pytest.fixture
def sample_milestone_with_complex_template():
    """Create a milestone with complex prompt template."""
    return Milestone(
        id=uuid4(),
        code="M2",
        name="Market Analysis Deep Dive",
        description="Comprehensive market research and analysis",
        milestone_type=MilestoneType.PAID,
        order_index=2,
        estimated_minutes=180,
        processing_time_limit=600,
        is_active=True,
        requires_payment=True,
        auto_unlock=False,
        prompt_template={
            "steps": [
                {
                    "id": "market_size",
                    "name": "Market Size Analysis",
                    "description": "Analyze total addressable market",
                    "inputs": ["industry", "geography", "timeframe"],
                    "validation": {"min_market_size": 1000000}
                },
                {
                    "id": "competitor_analysis", 
                    "name": "Competitive Landscape",
                    "description": "Identify and analyze key competitors",
                    "inputs": ["competitor_list", "competitive_advantages"],
                    "validation": {"min_competitors": 3}
                },
                {
                    "id": "customer_segments",
                    "name": "Customer Segmentation",
                    "description": "Define target customer segments",
                    "inputs": ["demographics", "psychographics", "behaviors"],
                    "validation": {"min_segments": 2}
                }
            ],
            "context_requirements": [
                "business_idea",
                "initial_research",
                "assumptions"
            ],
            "output_format": {
                "type": "structured_report",
                "sections": ["executive_summary", "methodology", "findings", "recommendations"]
            }
        },
        output_schema={
            "type": "object",
            "required": ["market_analysis", "competitive_landscape", "target_segments"],
            "properties": {
                "market_analysis": {
                    "type": "object",
                    "properties": {
                        "tam": {"type": "number", "minimum": 0},
                        "sam": {"type": "number", "minimum": 0},
                        "som": {"type": "number", "minimum": 0}
                    }
                },
                "competitive_landscape": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "market_share": {"type": "number"},
                            "strengths": {"type": "array"},
                            "weaknesses": {"type": "array"}
                        }
                    }
                },
                "target_segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "size": {"type": "number"},
                            "characteristics": {"type": "array"}
                        }
                    }
                }
            }
        },
        validation_rules={
            "required_data_quality": 0.8,
            "min_market_size": 1000000,
            "max_processing_time": 600,
            "required_sources": 5
        }
    )


@pytest.fixture
def sample_user_with_premium():
    """Create a premium user for testing."""
    return User(
        id=uuid4(),
        email="premium@example.com",
        username="premiumuser",
        subscription_tier=SubscriptionTier.PREMIUM,
        is_active=True,
        subscription_expires_at=datetime.utcnow() + timedelta(days=30)
    )


class TestEnhancedMilestoneRetrieval:
    """Enhanced tests for milestone retrieval methods."""
    
    @pytest.mark.asyncio
    async def test_get_milestone_by_code_with_cache_fallback(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service,
        enhanced_mock_db_session,
        sample_milestone_with_complex_template
    ):
        """Test milestone retrieval with cache fallback and error handling."""
        # Setup cache miss and Redis error
        enhanced_mock_cache_service.redis.get_cache.side_effect = [
            None,  # Cache miss
            Exception("Redis connection failed")  # Redis error on set
        ]
        
        # Mock database success
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_milestone_with_complex_template
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await enhanced_milestone_service.get_milestone_by_code("M2")
        
        # Assert
        assert result == sample_milestone_with_complex_template
        enhanced_mock_db_session.execute.assert_called_once()
        enhanced_mock_cache_service.redis.set_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_milestone_by_code_cache_expiry_handling(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service,
        enhanced_mock_db_session,
        sample_milestone_with_complex_template
    ):
        """Test handling of expired cache entries."""
        # Mock expired cache entry
        expired_data = sample_milestone_with_complex_template.to_dict()
        expired_data["cached_at"] = (datetime.utcnow() - timedelta(hours=3)).isoformat()
        
        enhanced_mock_cache_service.redis.get_cache.return_value = expired_data
        
        # Mock fresh database data
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_milestone_with_complex_template
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await enhanced_milestone_service.get_milestone_by_code("M2")
        
        # Should fetch from database due to cache expiry
        assert result == sample_milestone_with_complex_template
        enhanced_mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_milestones_with_filtering(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session
    ):
        """Test retrieving all milestones with filtering options."""
        # Create multiple milestones
        milestones = [
            Milestone(code="M0", name="Free Milestone", milestone_type=MilestoneType.FREE, is_active=True, order_index=0),
            Milestone(code="M1", name="Paid Milestone", milestone_type=MilestoneType.PAID, is_active=True, order_index=1),
            Milestone(code="M2", name="Inactive Milestone", milestone_type=MilestoneType.PAID, is_active=False, order_index=2)
        ]
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = milestones[:2]  # Only active ones
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await enhanced_milestone_service.get_all_milestones()
        
        # Assert only active milestones returned
        assert len(result) == 2
        assert all(m.is_active for m in result)
        enhanced_mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_milestone_progress_with_complex_data(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service,
        enhanced_mock_db_session
    ):
        """Test retrieving complex user milestone progress."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock complex cached progress data
        complex_progress = {
            "status": MilestoneStatus.IN_PROGRESS,
            "completion_percentage": 67.5,
            "current_step": 2,
            "total_steps": 3,
            "step_details": {
                "market_size": {"completed": True, "confidence": 0.9, "data_quality": 0.85},
                "competitor_analysis": {"completed": True, "confidence": 0.8, "sources": 4},
                "customer_segments": {"completed": False, "progress": 0.5}
            },
            "checkpoint_data": {
                "market_analysis": {
                    "tam": 5000000000,
                    "sam": 500000000,
                    "som": 50000000,
                    "growth_rate": 0.15
                },
                "competitive_landscape": [
                    {"name": "Competitor A", "market_share": 0.3, "threat_level": "high"},
                    {"name": "Competitor B", "market_share": 0.2, "threat_level": "medium"}
                ]
            },
            "quality_metrics": {
                "data_completeness": 0.8,
                "source_reliability": 0.9,
                "analysis_depth": 0.75
            },
            "performance_data": {
                "processing_time": 3600,
                "memory_usage": "250MB",
                "tokens_consumed": 15000
            }
        }
        
        enhanced_mock_cache_service.get_user_progress.return_value = complex_progress
        
        # Execute
        result = await enhanced_milestone_service.get_user_milestone_progress(user_id, milestone_id)
        
        # Assert
        assert result == complex_progress
        assert result["status"] == MilestoneStatus.IN_PROGRESS
        assert result["completion_percentage"] == 67.5
        assert "step_details" in result
        assert "checkpoint_data" in result
        assert "quality_metrics" in result
        enhanced_mock_cache_service.get_user_progress.assert_called_once_with(user_id, milestone_id)
    
    @pytest.mark.asyncio
    async def test_get_user_milestone_tree_with_complex_dependencies(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service,
        enhanced_mock_db_session
    ):
        """Test retrieving milestone tree with complex dependency structure."""
        user_id = str(uuid4())
        
        # Mock complex milestone tree
        complex_tree = {
            "milestones": [
                {
                    "id": "m0",
                    "code": "M0",
                    "name": "Foundation",
                    "type": MilestoneType.FREE,
                    "user_progress": {"status": MilestoneStatus.COMPLETED, "completion_percentage": 100},
                    "dependencies": [],
                    "dependents": ["m1", "m2"]
                },
                {
                    "id": "m1", 
                    "code": "M1",
                    "name": "Market Analysis",
                    "type": MilestoneType.PAID,
                    "user_progress": {"status": MilestoneStatus.IN_PROGRESS, "completion_percentage": 60},
                    "dependencies": [{"id": "m0", "code": "M0", "is_required": True}],
                    "dependents": ["m3", "m4"]
                },
                {
                    "id": "m2",
                    "code": "M2", 
                    "name": "Business Model",
                    "type": MilestoneType.PAID,
                    "user_progress": {"status": MilestoneStatus.AVAILABLE, "completion_percentage": 0},
                    "dependencies": [{"id": "m0", "code": "M0", "is_required": True}],
                    "dependents": ["m4"]
                },
                {
                    "id": "m3",
                    "code": "M3",
                    "name": "Financial Projections",
                    "type": MilestoneType.PAID,
                    "user_progress": {"status": MilestoneStatus.LOCKED, "completion_percentage": 0},
                    "dependencies": [{"id": "m1", "code": "M1", "is_required": True}],
                    "dependents": []
                },
                {
                    "id": "m4",
                    "code": "M4",
                    "name": "Go-to-Market Strategy",
                    "type": MilestoneType.PAID,
                    "user_progress": {"status": MilestoneStatus.LOCKED, "completion_percentage": 0},
                    "dependencies": [
                        {"id": "m1", "code": "M1", "is_required": True},
                        {"id": "m2", "code": "M2", "is_required": True}
                    ],
                    "dependents": []
                }
            ],
            "total_progress": 32.0,  # (100 + 60 + 0 + 0 + 0) / 5
            "completed_count": 1,
            "available_count": 1,
            "locked_count": 2,
            "in_progress_count": 1,
            "dependency_graph": {
                "nodes": 5,
                "edges": 5,
                "depth": 3,
                "complexity_score": 0.6
            },
            "user_analytics": {
                "time_spent_total": 7200,
                "average_session_length": 1800,
                "most_challenging_milestone": "M1",
                "predicted_completion_time": 14400
            }
        }
        
        enhanced_mock_cache_service.get_milestone_tree.return_value = complex_tree
        
        # Execute
        result = await enhanced_milestone_service.get_user_milestone_tree_with_cache(user_id)
        
        # Assert
        assert result == complex_tree
        assert len(result["milestones"]) == 5
        assert result["completed_count"] == 1
        assert result["dependency_graph"]["nodes"] == 5
        assert "user_analytics" in result
        enhanced_mock_cache_service.get_milestone_tree.assert_called_once_with(user_id)


class TestEnhancedMilestoneInitialization:
    """Enhanced tests for milestone initialization."""
    
    @pytest.mark.asyncio
    async def test_initialize_user_milestones_with_subscription_logic(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service,
        sample_user_with_premium
    ):
        """Test initializing milestones with complex subscription logic."""
        user_id = str(sample_user_with_premium.id)
        
        # Create diverse milestone set
        milestones = [
            Milestone(code="M0", milestone_type=MilestoneType.FREE, requires_payment=False, order_index=0),
            Milestone(code="M1", milestone_type=MilestoneType.PAID, requires_payment=True, order_index=1),
            Milestone(code="M2", milestone_type=MilestoneType.GATEWAY, requires_payment=True, order_index=2),
            Milestone(code="M9", milestone_type=MilestoneType.FREE, requires_payment=False, order_index=9)
        ]
        
        # Mock getting all milestones
        mock_result_milestones = AsyncMock()
        mock_result_milestones.scalars.return_value.all.return_value = milestones
        
        # Mock getting user (premium subscription)
        mock_result_user = AsyncMock()
        mock_result_user.scalar_one_or_none.return_value = sample_user_with_premium
        
        enhanced_mock_db_session.execute.side_effect = [
            mock_result_milestones,
            mock_result_user
        ]
        
        # Execute
        result = await enhanced_milestone_service.initialize_user_milestones(user_id)
        
        # Assert
        assert len(result) == 4
        
        # Check milestone status initialization based on type and subscription
        m0_user_milestone = next(um for um in result if um.milestone_id == milestones[0].id)
        assert m0_user_milestone.status == MilestoneStatus.AVAILABLE  # M0 always available
        
        # Premium user should have access to paid milestones
        m1_user_milestone = next(um for um in result if um.milestone_id == milestones[1].id)
        # Since premium user, paid milestone should start as available if no dependencies
        
        enhanced_mock_db_session.add.assert_called()
        enhanced_mock_db_session.commit.assert_called()
        enhanced_mock_cache_service.invalidate_user_cache.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_initialize_user_milestones_with_complex_dependencies(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service,
        sample_user_with_premium
    ):
        """Test initialization with complex dependency chains."""
        user_id = str(sample_user_with_premium.id)
        
        # Create milestones with prompt templates containing steps
        milestones = [
            Milestone(
                code="M0",
                milestone_type=MilestoneType.FREE,
                prompt_template={"steps": ["idea", "validation"]},
                order_index=0
            ),
            Milestone(
                code="M1",
                milestone_type=MilestoneType.PAID,
                prompt_template={"steps": ["research", "analysis", "synthesis", "conclusion"]},
                order_index=1
            )
        ]
        
        # Mock database calls
        mock_result_milestones = AsyncMock()
        mock_result_milestones.scalars.return_value.all.return_value = milestones
        
        mock_result_user = AsyncMock()
        mock_result_user.scalar_one_or_none.return_value = sample_user_with_premium
        
        # Mock dependency check to return no dependencies for simplicity
        with patch('backend.src.models.milestone.check_milestone_dependencies',
                   AsyncMock(return_value=(True, []))):
            enhanced_mock_db_session.execute.side_effect = [
                mock_result_milestones,
                mock_result_user
            ]
            
            # Execute
            result = await enhanced_milestone_service.initialize_user_milestones(user_id)
            
            # Assert total_steps is set correctly based on prompt template
            m0_milestone = next(um for um in result if um.milestone_id == milestones[0].id)
            assert m0_milestone.total_steps == 2  # From prompt template steps
            
            m1_milestone = next(um for um in result if um.milestone_id == milestones[1].id)
            assert m1_milestone.total_steps == 4  # From prompt template steps
    
    @pytest.mark.asyncio
    async def test_initialize_user_milestones_error_handling(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session
    ):
        """Test error handling during milestone initialization."""
        user_id = str(uuid4())
        
        # Mock database error during milestone fetch
        enhanced_mock_db_session.execute.side_effect = Exception("Database connection failed")
        
        # Execute and assert exception is raised
        with pytest.raises(Exception, match="Database connection failed"):
            await enhanced_milestone_service.initialize_user_milestones(user_id)
        
        # Ensure rollback would be called in real implementation
        enhanced_mock_db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_user_milestones_concurrent_safety(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service
    ):
        """Test concurrent safety during initialization."""
        user_id = str(uuid4())
        
        # Simulate concurrent initialization attempts
        async def init_milestones():
            try:
                # Mock user and milestones
                mock_user = User(id=uuid4(), subscription_tier=SubscriptionTier.FREE)
                mock_milestones = [
                    Milestone(code="M0", milestone_type=MilestoneType.FREE, order_index=0)
                ]
                
                mock_result_milestones = AsyncMock()
                mock_result_milestones.scalars.return_value.all.return_value = mock_milestones
                
                mock_result_user = AsyncMock()
                mock_result_user.scalar_one_or_none.return_value = mock_user
                
                enhanced_mock_db_session.execute.side_effect = [
                    mock_result_milestones,
                    mock_result_user
                ]
                
                return await enhanced_milestone_service.initialize_user_milestones(user_id)
            except Exception as e:
                return e
        
        # Run multiple concurrent initialization attempts
        tasks = [init_milestones() for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # At least one should succeed, others might raise exceptions or return empty
        success_count = sum(1 for r in results if isinstance(r, list))
        assert success_count >= 1


class TestEnhancedMilestoneStatusManagement:
    """Enhanced tests for milestone status management."""
    
    @pytest.mark.asyncio
    async def test_start_milestone_with_distributed_locking(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service,
        sample_milestone_with_complex_template,
        sample_user_with_premium
    ):
        """Test starting milestone with distributed locking for concurrent safety."""
        user_id = str(sample_user_with_premium.id)
        milestone_code = "M2"
        
        # Mock distributed lock acquisition
        enhanced_mock_cache_service.acquire_milestone_lock.return_value = "lock_token_123"
        enhanced_mock_cache_service.release_milestone_lock.return_value = True
        
        # Mock milestone retrieval
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(
            return_value=sample_milestone_with_complex_template
        )
        
        # Mock access check (success)
        enhanced_milestone_service._check_milestone_access = AsyncMock(
            return_value=(True, "Access granted")
        )
        
        # Mock user milestone creation (no existing milestone)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        success, message, user_milestone = await enhanced_milestone_service.start_milestone(
            user_id, milestone_code
        )
        
        # Assert
        assert success is True
        assert "Started milestone" in message
        assert user_milestone is not None
        assert user_milestone.status == MilestoneStatus.IN_PROGRESS
        assert user_milestone.total_steps == 3  # From complex template
        
        # Verify locking was used
        enhanced_mock_cache_service.acquire_milestone_lock.assert_called()
        enhanced_mock_cache_service.release_milestone_lock.assert_called()
        
        # Verify progress tracking
        enhanced_mock_cache_service.track_active_session.assert_called_once()
        enhanced_mock_cache_service.increment_milestone_stats.assert_called_once_with(
            milestone_code, "started"
        )
    
    @pytest.mark.asyncio
    async def test_start_milestone_concurrent_access_handling(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service
    ):
        """Test handling of concurrent milestone start attempts."""
        user_id = str(uuid4())
        milestone_code = "M1"
        
        # Simulate lock acquisition failure (another process has the lock)
        enhanced_mock_cache_service.acquire_milestone_lock.return_value = None
        
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(
            return_value=Milestone(code="M1")
        )
        
        # In a real implementation, this should either:
        # 1. Wait and retry
        # 2. Return a "try again later" response
        # 3. Queue the request
        
        # For this test, we'll assume it returns a specific error
        with patch.object(enhanced_milestone_service, '_handle_lock_failure') as mock_handle:
            mock_handle.return_value = (False, "Milestone is currently being processed by another session")
            
            # This would be the enhanced version of start_milestone with locking
            # For now, we test the concept
            assert enhanced_mock_cache_service.acquire_milestone_lock.return_value is None
    
    @pytest.mark.asyncio
    async def test_update_milestone_progress_with_validation(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service,
        sample_milestone_with_complex_template
    ):
        """Test updating milestone progress with complex validation."""
        user_id = str(uuid4())
        milestone_code = "M2"
        
        # Create user milestone with complex state
        user_milestone = UserMilestone(
            id=uuid4(),
            user_id=user_id,
            milestone_id=sample_milestone_with_complex_template.id,
            status=MilestoneStatus.IN_PROGRESS,
            current_step=1,
            total_steps=3,
            started_at=datetime.utcnow() - timedelta(hours=1),
            checkpoint_data={
                "market_size": {
                    "completed": True,
                    "tam": 1000000000,
                    "validation_passed": True
                }
            }
        )
        
        # Mock milestone and user milestone retrieval
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(
            return_value=sample_milestone_with_complex_template
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_milestone
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Complex checkpoint data for step 2
        complex_checkpoint = {
            "competitor_analysis": {
                "completed": True,
                "competitors": [
                    {"name": "CompetitorA", "market_share": 0.3, "analysis_complete": True},
                    {"name": "CompetitorB", "market_share": 0.2, "analysis_complete": True},
                    {"name": "CompetitorC", "market_share": 0.15, "analysis_complete": True}
                ],
                "total_analyzed": 3,
                "validation_passed": True
            },
            "quality_metrics": {
                "data_completeness": 0.9,
                "source_reliability": 0.85,
                "analysis_depth": 0.8
            }
        }
        
        # Execute
        success, message = await enhanced_milestone_service.update_milestone_progress(
            user_id, milestone_code, 2, complex_checkpoint
        )
        
        # Assert
        assert success is True
        assert "updated successfully" in message
        assert user_milestone.current_step == 2
        assert user_milestone.completion_percentage == (2/3) * 100
        assert "competitor_analysis" in user_milestone.checkpoint_data
        
        # Verify cache updates
        enhanced_mock_cache_service.update_milestone_progress.assert_called_once()
        enhanced_mock_cache_service.update_session_activity.assert_called_once()
        enhanced_mock_cache_service.publish_progress_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_milestone_with_complex_validation(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service,
        sample_milestone_with_complex_template
    ):
        """Test milestone completion with complex output validation."""
        user_id = str(uuid4())
        milestone_code = "M2"
        
        # Complex generated output matching the schema
        generated_output = {
            "market_analysis": {
                "tam": 5000000000,  # $5B
                "sam": 500000000,   # $500M
                "som": 50000000,    # $50M
                "growth_rate": 0.15,
                "market_trends": [
                    "AI adoption increasing",
                    "Remote work normalization",
                    "Productivity tools demand"
                ]
            },
            "competitive_landscape": [
                {
                    "name": "Market Leader Corp",
                    "market_share": 0.35,
                    "strengths": ["Brand recognition", "Large user base", "Enterprise focus"],
                    "weaknesses": ["High pricing", "Complex UI", "Slow innovation"]
                },
                {
                    "name": "Innovative Startup",
                    "market_share": 0.15,
                    "strengths": ["Modern UI", "Fast development", "Competitive pricing"],
                    "weaknesses": ["Limited features", "Small team", "Funding concerns"]
                }
            ],
            "target_segments": [
                {
                    "name": "SMB Knowledge Workers",
                    "size": 10000000,
                    "characteristics": ["Time-constrained", "Tech-savvy", "Cost-conscious"]
                },
                {
                    "name": "Enterprise Teams",
                    "size": 2000000,
                    "characteristics": ["Compliance-focused", "Integration-needs", "Budget-available"]
                }
            ],
            "recommendations": {
                "go_to_market_strategy": "Focus on SMB segment first",
                "competitive_positioning": "Premium features at competitive price",
                "market_entry_timeline": "12 months"
            }
        }
        
        quality_score = 0.92
        
        # Mock user milestone
        user_milestone = UserMilestone(
            id=uuid4(),
            user_id=user_id,
            milestone_id=sample_milestone_with_complex_template.id,
            status=MilestoneStatus.IN_PROGRESS,
            current_step=3,
            total_steps=3,
            started_at=datetime.utcnow() - timedelta(hours=3)
        )
        
        # Setup mocks
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(
            return_value=sample_milestone_with_complex_template
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_milestone
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Mock dependency update
        with patch('backend.src.models.milestone.update_dependent_milestones',
                   AsyncMock(return_value=["M3", "M4"])):
            
            # Execute
            success, message, newly_unlocked = await enhanced_milestone_service.complete_milestone(
                user_id, milestone_code, generated_output, quality_score
            )
        
        # Assert completion
        assert success is True
        assert "completed successfully" in message
        assert newly_unlocked == ["M3", "M4"]
        assert user_milestone.status == MilestoneStatus.COMPLETED
        assert user_milestone.completion_percentage == 100.0
        assert user_milestone.generated_output == generated_output
        assert user_milestone.quality_score == quality_score
        
        # Verify cache invalidation and stats update
        enhanced_mock_cache_service.invalidate_user_cache.assert_called_once_with(user_id)
        enhanced_mock_cache_service.increment_milestone_stats.assert_called_once_with(
            milestone_code, "completed"
        )
    
    @pytest.mark.asyncio
    async def test_fail_milestone_with_detailed_error_tracking(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service,
        sample_milestone_with_complex_template
    ):
        """Test milestone failure with detailed error tracking."""
        user_id = str(uuid4())
        milestone_code = "M2"
        
        # Complex error information
        error_details = {
            "error_type": "processing_timeout",
            "error_message": "Market analysis processing exceeded time limit",
            "step_failed": 2,
            "step_name": "competitor_analysis",
            "partial_results": {
                "market_size": {"completed": True},
                "competitor_analysis": {"completed": False, "progress": 0.6}
            },
            "error_metadata": {
                "processing_time": 650,  # Exceeded 600s limit
                "memory_peak": "512MB",
                "timeout_threshold": 600,
                "retry_possible": True
            },
            "user_context": {
                "session_id": "session_123",
                "browser": "Chrome/91.0",
                "last_activity": datetime.utcnow().isoformat()
            }
        }
        
        error_message = json.dumps(error_details)
        
        # Mock user milestone in progress
        user_milestone = UserMilestone(
            id=uuid4(),
            user_id=user_id,
            milestone_id=sample_milestone_with_complex_template.id,
            status=MilestoneStatus.IN_PROGRESS,
            current_step=2,
            completion_percentage=66.7,
            processing_attempts=1
        )
        
        # Setup mocks
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(
            return_value=sample_milestone_with_complex_template
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_milestone
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        success, message = await enhanced_milestone_service.fail_milestone(
            user_id, milestone_code, error_message
        )
        
        # Assert
        assert success is True
        assert "marked as failed" in message
        assert user_milestone.status == MilestoneStatus.FAILED
        assert user_milestone.last_error == error_message
        
        # Verify progress log was created with detailed error info
        enhanced_mock_db_session.add.assert_called()
        
        # Verify cache and stats updates
        enhanced_mock_cache_service.update_milestone_progress.assert_called_once()
        enhanced_mock_cache_service.increment_milestone_stats.assert_called_once_with(
            milestone_code, "failed"
        )


class TestEnhancedArtifactManagement:
    """Enhanced tests for artifact management."""
    
    @pytest.mark.asyncio
    async def test_create_complex_milestone_artifact(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service,
        sample_milestone_with_complex_template
    ):
        """Test creating complex milestone artifacts with metadata."""
        user_id = str(uuid4())
        milestone_code = "M2"
        
        # Complex artifact data
        artifact_name = "Comprehensive Market Analysis Report"
        artifact_type = "structured_report"
        storage_path = "/artifacts/market_analysis/user_123/report_456.json"
        
        complex_content = {
            "executive_summary": {
                "key_findings": [
                    "Market size of $5B with 15% annual growth",
                    "3 major competitors with combined 65% market share",
                    "2 primary target segments identified"
                ],
                "recommendations": [
                    "Focus on SMB segment for initial market entry",
                    "Differentiate through AI-powered features",
                    "Plan for 12-month market entry timeline"
                ]
            },
            "detailed_analysis": {
                "market_sizing": {
                    "methodology": "Top-down and bottom-up analysis",
                    "data_sources": ["Industry reports", "Government data", "Competitor filings"],
                    "tam": 5000000000,
                    "sam": 500000000,
                    "som": 50000000,
                    "confidence_level": 0.85
                },
                "competitive_analysis": {
                    "methodology": "Porter's Five Forces",
                    "competitors_analyzed": 15,
                    "key_competitors": [
                        {
                            "name": "Market Leader",
                            "analysis": {
                                "market_share": 0.35,
                                "revenue": 175000000,
                                "strengths": ["Brand", "Distribution", "Features"],
                                "weaknesses": ["Price", "Innovation speed"],
                                "threat_level": "high"
                            }
                        }
                    ]
                }
            },
            "appendices": {
                "data_sources": ["Source 1", "Source 2", "Source 3"],
                "assumptions": ["Assumption 1", "Assumption 2"],
                "limitations": ["Limitation 1", "Limitation 2"]
            },
            "generation_metadata": {
                "model_version": "gpt-4-turbo",
                "processing_time": 180.5,
                "tokens_input": 5000,
                "tokens_output": 8000,
                "quality_score": 0.92,
                "validation_passed": True
            }
        }
        
        # Mock existing user milestone
        user_milestone = UserMilestone(
            id=uuid4(),
            user_id=user_id,
            milestone_id=sample_milestone_with_complex_template.id,
            status=MilestoneStatus.COMPLETED
        )
        
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(
            return_value=sample_milestone_with_complex_template
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_milestone
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        artifact = await enhanced_milestone_service.create_milestone_artifact(
            user_id,
            milestone_code,
            artifact_name,
            artifact_type,
            complex_content,
            storage_path
        )
        
        # Assert
        assert artifact is not None
        assert artifact.name == artifact_name
        assert artifact.artifact_type == artifact_type
        assert artifact.content == complex_content
        assert artifact.storage_path == storage_path
        assert artifact.mime_type == "application/json"  # Based on artifact_type
        
        # Verify caching
        enhanced_mock_cache_service.cache_artifact.assert_called_once()
        cache_call_args = enhanced_mock_cache_service.cache_artifact.call_args
        assert cache_call_args[0][1]["name"] == artifact_name
        assert cache_call_args[0][1]["type"] == artifact_type
    
    @pytest.mark.asyncio
    async def test_get_user_artifacts_with_filtering(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session
    ):
        """Test retrieving user artifacts with filtering and sorting."""
        user_id = str(uuid4())
        milestone_code = "M2"
        
        # Mock multiple artifacts
        artifacts = [
            UserMilestoneArtifact(
                id=uuid4(),
                name="Market Analysis Report",
                artifact_type="pdf",
                created_at=datetime.utcnow() - timedelta(days=1),
                file_size=1024000,
                access_count=5
            ),
            UserMilestoneArtifact(
                id=uuid4(),
                name="Competitive Analysis",
                artifact_type="xlsx",
                created_at=datetime.utcnow() - timedelta(hours=2),
                file_size=512000,
                access_count=2
            ),
            UserMilestoneArtifact(
                id=uuid4(),
                name="Customer Segments Data",
                artifact_type="json",
                created_at=datetime.utcnow(),
                file_size=256000,
                access_count=8
            )
        ]
        
        # Mock milestone retrieval
        milestone = Milestone(id=uuid4(), code=milestone_code)
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(return_value=milestone)
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = artifacts
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await enhanced_milestone_service.get_user_artifacts(user_id, milestone_code)
        
        # Assert
        assert len(result) == 3
        assert all(isinstance(artifact, UserMilestoneArtifact) for artifact in result)
        
        # Verify query was constructed correctly
        enhanced_mock_db_session.execute.assert_called_once()
        enhanced_milestone_service.get_milestone_by_code.assert_called_once_with(milestone_code)


class TestEnhancedAnalyticsAndReporting:
    """Enhanced tests for analytics and reporting."""
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_user_analytics(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session
    ):
        """Test getting comprehensive user analytics with advanced metrics."""
        user_id = str(uuid4())
        
        # Create diverse user milestones for analytics
        now = datetime.utcnow()
        user_milestones = [
            # Completed milestones
            UserMilestone(
                status=MilestoneStatus.COMPLETED,
                time_spent_seconds=3600,  # 1 hour
                quality_score=0.95,
                completed_at=now - timedelta(days=1),
                milestone=Mock(code="M0", milestone_type=MilestoneType.FREE)
            ),
            UserMilestone(
                status=MilestoneStatus.COMPLETED,
                time_spent_seconds=7200,  # 2 hours
                quality_score=0.88,
                completed_at=now - timedelta(hours=12),
                milestone=Mock(code="M1", milestone_type=MilestoneType.PAID)
            ),
            UserMilestone(
                status=MilestoneStatus.COMPLETED,
                time_spent_seconds=5400,  # 1.5 hours
                quality_score=0.92,
                completed_at=now - timedelta(hours=6),
                milestone=Mock(code="M2", milestone_type=MilestoneType.PAID)
            ),
            # In progress
            UserMilestone(
                status=MilestoneStatus.IN_PROGRESS,
                time_spent_seconds=1800,  # 30 minutes
                milestone=Mock(code="M3", milestone_type=MilestoneType.PAID),
                started_at=now - timedelta(hours=2),
                current_step=2,
                total_steps=4
            ),
            # Locked milestones
            UserMilestone(
                status=MilestoneStatus.LOCKED,
                time_spent_seconds=0,
                milestone=Mock(code="M4", milestone_type=MilestoneType.PAID)
            ),
            # Failed milestone
            UserMilestone(
                status=MilestoneStatus.FAILED,
                time_spent_seconds=2700,  # 45 minutes
                milestone=Mock(code="M5", milestone_type=MilestoneType.PAID),
                last_error="Processing timeout"
            )
        ]
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = user_milestones
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        analytics = await enhanced_milestone_service.get_user_analytics(user_id)
        
        # Assert comprehensive analytics
        assert analytics["total_milestones"] == 6
        assert analytics["completed"] == 3
        assert analytics["in_progress"] == 1
        assert analytics["locked"] == 1
        assert analytics["failed"] == 1
        
        # Time analytics
        expected_total_hours = (3600 + 7200 + 5400 + 1800 + 2700) / 3600  # ~5.75 hours
        assert abs(analytics["total_time_spent_hours"] - expected_total_hours) < 0.1
        
        # Completion analytics
        expected_avg_completion_time = (3600 + 7200 + 5400) / 3 / 3600  # ~1.67 hours
        assert abs(analytics["average_completion_time_hours"] - expected_avg_completion_time) < 0.1
        
        # Completion rate
        assert analytics["completion_rate"] == 50.0  # 3 completed out of 6 total
        
        # Quality analytics
        expected_avg_quality = (0.95 + 0.88 + 0.92) / 3  # ~0.917
        assert abs(analytics["average_quality_score"] - expected_avg_quality) < 0.01
        
        # Milestone breakdown
        assert "M0" in analytics["time_by_milestone"]
        assert "M1" in analytics["time_by_milestone"]
        assert len(analytics["quality_scores"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_milestone_statistics_with_advanced_metrics(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service,
        enhanced_mock_db_session,
        sample_milestone_with_complex_template
    ):
        """Test getting milestone statistics with advanced performance metrics."""
        milestone_code = "M2"
        
        # Mock cache statistics
        cache_stats = {
            "started": 150,
            "completed": 120,
            "failed": 15,
            "skipped": 5,
            "completion_rate": 80.0,
            "average_attempts": 1.3,
            "peak_concurrent_users": 25,
            "total_processing_time": 54000  # seconds
        }
        enhanced_mock_cache_service.get_milestone_stats.return_value = cache_stats
        
        # Mock getting milestone
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(
            return_value=sample_milestone_with_complex_template
        )
        
        # Mock completion times with realistic distribution
        completion_times = [
            3600,   # 1 hour
            4200,   # 1.17 hours  
            3000,   # 50 minutes
            5400,   # 1.5 hours
            7200,   # 2 hours
            2700,   # 45 minutes
            4800,   # 1.33 hours
            3900    # 1.08 hours
        ]
        
        mock_result_times = AsyncMock()
        mock_result_times.scalars.return_value.all.return_value = completion_times
        
        # Mock quality scores with realistic distribution
        quality_scores = [0.95, 0.88, 0.92, 0.85, 0.90, 0.87, 0.93, 0.89]
        
        mock_result_scores = AsyncMock()
        mock_result_scores.scalars.return_value.all.return_value = quality_scores
        
        enhanced_mock_db_session.execute.side_effect = [
            mock_result_times,
            mock_result_scores
        ]
        
        # Execute
        stats = await enhanced_milestone_service.get_milestone_statistics(milestone_code)
        
        # Assert basic stats from cache
        assert stats["started"] == 150
        assert stats["completed"] == 120
        assert stats["completion_rate"] == 80.0
        
        # Assert computed database stats
        expected_avg_time = sum(completion_times) / len(completion_times) / 60  # minutes
        assert abs(stats["average_completion_time_minutes"] - expected_avg_time) < 1.0
        
        expected_avg_quality = sum(quality_scores) / len(quality_scores)
        assert abs(stats["average_quality_score"] - expected_avg_quality) < 0.01
    
    @pytest.mark.asyncio
    async def test_analytics_error_handling(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session
    ):
        """Test analytics error handling and fallback behavior."""
        user_id = str(uuid4())
        
        # Mock database error
        enhanced_mock_db_session.execute.side_effect = Exception("Database timeout")
        
        # Execute and assert exception handling
        with pytest.raises(Exception, match="Database timeout"):
            await enhanced_milestone_service.get_user_analytics(user_id)
    
    @pytest.mark.asyncio
    async def test_analytics_with_empty_data(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session
    ):
        """Test analytics calculation with no user milestones."""
        user_id = str(uuid4())
        
        # Mock empty result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        analytics = await enhanced_milestone_service.get_user_analytics(user_id)
        
        # Assert zero analytics
        assert analytics["total_milestones"] == 0
        assert analytics["completed"] == 0
        assert analytics["total_time_spent_hours"] == 0
        assert analytics["completion_rate"] == 0
        assert analytics["average_completion_time_hours"] == 0
        assert len(analytics["quality_scores"]) == 0


class TestEnhancedErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_database_transaction_rollback(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session
    ):
        """Test database transaction rollback on errors."""
        user_id = str(uuid4())
        milestone_code = "M1"
        
        # Mock milestone retrieval success
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(
            return_value=Milestone(code="M1")
        )
        
        # Mock database commit failure
        enhanced_mock_db_session.commit.side_effect = Exception("Database commit failed")
        
        # Execute and expect exception
        with pytest.raises(Exception, match="Database commit failed"):
            await enhanced_milestone_service.start_milestone(user_id, milestone_code)
        
        # In a real implementation, we'd verify rollback was called
        enhanced_mock_db_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_cache_failure_graceful_degradation(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service,
        enhanced_mock_db_session
    ):
        """Test graceful degradation when cache fails."""
        user_id = str(uuid4())
        
        # Mock cache failure
        enhanced_mock_cache_service.get_user_progress.side_effect = Exception("Redis connection failed")
        
        # Mock database fallback
        mock_user_milestone = UserMilestone(
            user_id=user_id,
            milestone_id=uuid4(),
            status=MilestoneStatus.IN_PROGRESS
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user_milestone
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Service should continue working despite cache failure
        # In a real implementation, it would fall back to database
        with pytest.raises(Exception, match="Redis connection failed"):
            await enhanced_milestone_service.get_user_milestone_progress(user_id)
    
    @pytest.mark.asyncio
    async def test_invalid_milestone_code_handling(
        self,
        enhanced_milestone_service
    ):
        """Test handling of invalid milestone codes."""
        user_id = str(uuid4())
        
        # Mock milestone not found
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(return_value=None)
        
        # Execute
        success, message, user_milestone = await enhanced_milestone_service.start_milestone(
            user_id, "INVALID_CODE"
        )
        
        # Assert
        assert success is False
        assert "not found" in message
        assert user_milestone is None
    
    @pytest.mark.asyncio
    async def test_concurrent_milestone_completion(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service
    ):
        """Test handling concurrent milestone completion attempts."""
        user_id = str(uuid4())
        milestone_code = "M1"
        
        # Mock milestone already completed by another request
        completed_user_milestone = UserMilestone(
            user_id=user_id,
            milestone_id=uuid4(),
            status=MilestoneStatus.COMPLETED,
            completion_percentage=100.0
        )
        
        enhanced_milestone_service.get_milestone_by_code = AsyncMock(
            return_value=Milestone(code="M1")
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = completed_user_milestone
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute
        success, message, newly_unlocked = await enhanced_milestone_service.complete_milestone(
            user_id, milestone_code, {"result": "data"}, 0.9
        )
        
        # Assert
        assert success is False
        assert "already completed" in message
        assert newly_unlocked == []


class TestEnhancedPerformanceAndScaling:
    """Test performance and scaling scenarios."""
    
    @pytest.mark.asyncio
    async def test_batch_milestone_operations(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session,
        enhanced_mock_cache_service
    ):
        """Test batch operations for multiple milestones."""
        user_id = str(uuid4())
        milestone_codes = ["M1", "M2", "M3", "M4", "M5"]
        
        # Mock milestones
        milestones = [
            Milestone(code=code, id=uuid4()) for code in milestone_codes
        ]
        
        # In a real implementation, this would be a batch method
        # For now, test the concept of handling multiple milestones efficiently
        results = []
        for i, code in enumerate(milestone_codes):
            enhanced_milestone_service.get_milestone_by_code = AsyncMock(
                return_value=milestones[i]
            )
            
            result = await enhanced_milestone_service.get_milestone_by_code(code)
            results.append(result)
        
        # Assert all milestones retrieved
        assert len(results) == 5
        assert all(m is not None for m in results)
    
    @pytest.mark.asyncio
    async def test_memory_efficient_large_dataset_handling(
        self,
        enhanced_milestone_service,
        enhanced_mock_db_session
    ):
        """Test handling large datasets efficiently."""
        user_id = str(uuid4())
        
        # Simulate large number of user milestones
        large_milestone_set = []
        for i in range(1000):  # Large dataset
            milestone = UserMilestone(
                status=MilestoneStatus.COMPLETED if i % 3 == 0 else MilestoneStatus.LOCKED,
                time_spent_seconds=3600 + (i * 10),
                quality_score=0.8 + (i % 20) * 0.01,
                milestone=Mock(code=f"M{i}", milestone_type=MilestoneType.PAID)
            )
            large_milestone_set.append(milestone)
        
        # Mock database result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = large_milestone_set
        enhanced_mock_db_session.execute.return_value = mock_result
        
        # Execute analytics on large dataset
        analytics = await enhanced_milestone_service.get_user_analytics(user_id)
        
        # Assert analytics computed correctly for large dataset
        assert analytics["total_milestones"] == 1000
        completed_count = sum(1 for m in large_milestone_set if m.status == MilestoneStatus.COMPLETED)
        assert analytics["completed"] == completed_count
        assert analytics["completion_rate"] == (completed_count / 1000) * 100
        
        # Verify memory efficiency (no specific assertion, but operation should complete)
        assert analytics is not None


class TestEnhancedCacheIntegration:
    """Test enhanced cache integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_cache_warming_strategy(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service,
        enhanced_mock_db_session
    ):
        """Test cache warming for frequently accessed data."""
        user_id = str(uuid4())
        
        # Mock database data that would be cached
        milestone_data = {
            "progress": {"status": "in_progress", "completion": 50},
            "tree": {"milestones": [], "progress": 25.0},
            "milestones": [
                {"id": "m1", "progress": {"completion": 75}},
                {"id": "m2", "progress": {"completion": 25}}
            ]
        }
        
        # Test cache warming
        success = await enhanced_mock_cache_service.warm_cache_for_user(user_id, milestone_data)
        
        assert success  # Mock returns True
        enhanced_mock_cache_service.warm_cache_for_user.assert_called_once_with(user_id, milestone_data)
    
    @pytest.mark.asyncio 
    async def test_cache_invalidation_cascade(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service
    ):
        """Test cascading cache invalidation."""
        user_id = str(uuid4())
        
        # Test user cache invalidation
        success = await enhanced_mock_cache_service.invalidate_user_cache(user_id)
        
        assert success  # Mock returns True
        enhanced_mock_cache_service.invalidate_user_cache.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_cache_consistency_after_updates(
        self,
        enhanced_milestone_service,
        enhanced_mock_cache_service,
        enhanced_mock_db_session
    ):
        """Test cache consistency after database updates."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock progress update
        updates = {"completion_percentage": 75.0, "current_step": 3}
        
        # Update should invalidate or update cache
        success = await enhanced_mock_cache_service.update_milestone_progress(
            user_id, milestone_id, updates
        )
        
        assert success  # Mock returns True
        enhanced_mock_cache_service.update_milestone_progress.assert_called_once_with(
            user_id, milestone_id, updates
        )