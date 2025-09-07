"""
Unit Tests for Milestone Service

Comprehensive test coverage for milestone service functionality including
progress tracking, dependency management, and caching.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
import json

from backend.src.services.milestone_service import MilestoneService
from backend.src.services.milestone_cache import MilestoneCacheService
from backend.src.models.milestone import (
    Milestone, UserMilestone, MilestoneDependency,
    MilestoneStatus, MilestoneType, MilestoneProgressLog,
    UserMilestoneArtifact
)
from backend.src.models.user import User, SubscriptionTier


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.get_cache = AsyncMock(return_value=None)
    client.set_cache = AsyncMock(return_value=True)
    client.delete_cache = AsyncMock(return_value=True)
    client.publish = AsyncMock(return_value=1)
    client.lock = AsyncMock(return_value="lock_value")
    client.unlock = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_cache_service(mock_redis_client):
    """Create a mock cache service."""
    service = MilestoneCacheService(mock_redis_client)
    service.get_user_progress = AsyncMock(return_value=None)
    service.set_user_progress = AsyncMock(return_value=True)
    service.get_milestone_tree = AsyncMock(return_value=None)
    service.set_milestone_tree = AsyncMock(return_value=True)
    service.invalidate_user_cache = AsyncMock(return_value=True)
    service.invalidate_milestone_cache = AsyncMock(return_value=True)
    service.publish_progress_update = AsyncMock(return_value=1)
    service.increment_milestone_stats = AsyncMock(return_value=True)
    service.update_leaderboard = AsyncMock(return_value=True)
    return service


@pytest.fixture
def milestone_service(mock_db_session, mock_cache_service):
    """Create a milestone service instance."""
    return MilestoneService(mock_db_session, mock_cache_service)


@pytest.fixture
def sample_milestone():
    """Create a sample milestone."""
    return Milestone(
        id=uuid4(),
        code="M0",
        name="Feasibility Snapshot",
        description="Initial feasibility assessment",
        milestone_type=MilestoneType.FREE,
        order_index=0,
        estimated_minutes=30,
        processing_time_limit=60,
        is_active=True,
        requires_payment=False,
        auto_unlock=True,
        prompt_template={"steps": ["step1", "step2", "step3"]},
        output_schema={"type": "object"},
        validation_rules={"required": ["viability_score"]}
    )


@pytest.fixture
def sample_user():
    """Create a sample user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True
    )


@pytest.fixture
def sample_user_milestone(sample_milestone, sample_user):
    """Create a sample user milestone."""
    return UserMilestone(
        id=uuid4(),
        user_id=sample_user.id,
        milestone_id=sample_milestone.id,
        status=MilestoneStatus.AVAILABLE,
        completion_percentage=0.0,
        current_step=0,
        total_steps=3,
        milestone=sample_milestone
    )


class TestMilestoneRetrieval:
    """Test milestone retrieval methods."""
    
    @pytest.mark.asyncio
    async def test_get_milestone_by_code_cached(
        self,
        milestone_service,
        mock_cache_service,
        sample_milestone
    ):
        """Test getting milestone by code when cached."""
        # Setup
        mock_cache_service.redis.get_cache.return_value = sample_milestone.to_dict()
        
        # Execute
        result = await milestone_service.get_milestone_by_code("M0")
        
        # Assert
        assert result == sample_milestone.to_dict()
        mock_cache_service.redis.get_cache.assert_called_once_with("milestone:code:M0")
    
    @pytest.mark.asyncio
    async def test_get_milestone_by_code_from_db(
        self,
        milestone_service,
        mock_db_session,
        mock_cache_service,
        sample_milestone
    ):
        """Test getting milestone by code from database."""
        # Setup
        mock_cache_service.redis.get_cache.return_value = None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_milestone
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await milestone_service.get_milestone_by_code("M0")
        
        # Assert
        assert result == sample_milestone
        mock_cache_service.redis.set_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_all_milestones(
        self,
        milestone_service,
        mock_db_session,
        sample_milestone
    ):
        """Test getting all active milestones."""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_milestone]
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await milestone_service.get_all_milestones()
        
        # Assert
        assert len(result) == 1
        assert result[0] == sample_milestone
    
    @pytest.mark.asyncio
    async def test_get_user_milestone_progress_cached(
        self,
        milestone_service,
        mock_cache_service
    ):
        """Test getting user milestone progress when cached."""
        # Setup
        user_id = str(uuid4())
        cached_data = {"status": "in_progress", "completion_percentage": 50}
        mock_cache_service.get_user_progress.return_value = cached_data
        
        # Execute
        result = await milestone_service.get_user_milestone_progress(user_id)
        
        # Assert
        assert result == cached_data
        mock_cache_service.get_user_progress.assert_called_once_with(user_id, None)


class TestMilestoneInitialization:
    """Test milestone initialization for new users."""
    
    @pytest.mark.asyncio
    async def test_initialize_user_milestones(
        self,
        milestone_service,
        mock_db_session,
        mock_cache_service,
        sample_milestone,
        sample_user
    ):
        """Test initializing milestones for a new user."""
        # Setup
        user_id = str(sample_user.id)
        
        # Mock getting all milestones
        mock_result_milestones = AsyncMock()
        mock_result_milestones.scalars.return_value.all.return_value = [sample_milestone]
        
        # Mock getting user
        mock_result_user = AsyncMock()
        mock_result_user.scalar_one_or_none.return_value = sample_user
        
        mock_db_session.execute.side_effect = [mock_result_milestones, mock_result_user]
        
        # Execute
        result = await milestone_service.initialize_user_milestones(user_id)
        
        # Assert
        assert len(result) == 1
        assert mock_db_session.add.called
        assert mock_db_session.commit.called
        mock_cache_service.invalidate_user_cache.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_initialize_user_milestones_user_not_found(
        self,
        milestone_service,
        mock_db_session
    ):
        """Test initializing milestones when user not found."""
        # Setup
        user_id = str(uuid4())
        
        # Mock getting all milestones
        mock_result_milestones = AsyncMock()
        mock_result_milestones.scalars.return_value.all.return_value = []
        
        # Mock getting user (not found)
        mock_result_user = AsyncMock()
        mock_result_user.scalar_one_or_none.return_value = None
        
        mock_db_session.execute.side_effect = [mock_result_milestones, mock_result_user]
        
        # Execute and assert
        with pytest.raises(ValueError, match=f"User {user_id} not found"):
            await milestone_service.initialize_user_milestones(user_id)


class TestMilestoneStatusManagement:
    """Test milestone status management operations."""
    
    @pytest.mark.asyncio
    async def test_start_milestone_success(
        self,
        milestone_service,
        mock_db_session,
        mock_cache_service,
        sample_milestone,
        sample_user,
        sample_user_milestone
    ):
        """Test successfully starting a milestone."""
        # Setup
        user_id = str(sample_user.id)
        milestone_code = "M0"
        
        # Mock getting milestone
        milestone_service.get_milestone_by_code = AsyncMock(return_value=sample_milestone)
        
        # Mock access check
        milestone_service._check_milestone_access = AsyncMock(
            return_value=(True, "Access granted")
        )
        
        # Mock getting user milestone
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_milestone
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        success, message, user_milestone = await milestone_service.start_milestone(
            user_id, milestone_code
        )
        
        # Assert
        assert success is True
        assert "in progress" in message.lower()
        assert user_milestone == sample_user_milestone
        assert sample_user_milestone.status == MilestoneStatus.IN_PROGRESS
        mock_cache_service.publish_progress_update.assert_called_once()
        mock_cache_service.increment_milestone_stats.assert_called_once_with(
            milestone_code, "started"
        )
    
    @pytest.mark.asyncio
    async def test_start_milestone_no_access(
        self,
        milestone_service,
        sample_milestone
    ):
        """Test starting a milestone without access."""
        # Setup
        user_id = str(uuid4())
        milestone_code = "M1"
        
        # Mock getting milestone
        milestone_service.get_milestone_by_code = AsyncMock(return_value=sample_milestone)
        
        # Mock access check (no access)
        milestone_service._check_milestone_access = AsyncMock(
            return_value=(False, "This milestone requires a paid subscription")
        )
        
        # Execute
        success, message, user_milestone = await milestone_service.start_milestone(
            user_id, milestone_code
        )
        
        # Assert
        assert success is False
        assert "requires a paid subscription" in message
        assert user_milestone is None
    
    @pytest.mark.asyncio
    async def test_update_milestone_progress(
        self,
        milestone_service,
        mock_db_session,
        mock_cache_service,
        sample_milestone,
        sample_user_milestone
    ):
        """Test updating milestone progress."""
        # Setup
        user_id = str(sample_user_milestone.user_id)
        milestone_code = "M0"
        step_completed = 2
        checkpoint_data = {"key": "value"}
        
        sample_user_milestone.status = MilestoneStatus.IN_PROGRESS
        sample_user_milestone.started_at = datetime.utcnow()
        
        # Mock getting milestone
        milestone_service.get_milestone_by_code = AsyncMock(return_value=sample_milestone)
        
        # Mock getting user milestone
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_milestone
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        success, message = await milestone_service.update_milestone_progress(
            user_id, milestone_code, step_completed, checkpoint_data
        )
        
        # Assert
        assert success is True
        assert "updated successfully" in message
        assert sample_user_milestone.current_step == step_completed
        assert sample_user_milestone.completion_percentage == (2/3) * 100
        assert sample_user_milestone.checkpoint_data == checkpoint_data
        mock_cache_service.update_milestone_progress.assert_called_once()
        mock_cache_service.publish_progress_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_milestone(
        self,
        milestone_service,
        mock_db_session,
        mock_cache_service,
        sample_milestone,
        sample_user_milestone
    ):
        """Test completing a milestone."""
        # Setup
        user_id = str(sample_user_milestone.user_id)
        milestone_code = "M0"
        generated_output = {"result": "success"}
        quality_score = 0.95
        
        sample_user_milestone.status = MilestoneStatus.IN_PROGRESS
        sample_user_milestone.started_at = datetime.utcnow() - timedelta(hours=1)
        
        # Mock getting milestone
        milestone_service.get_milestone_by_code = AsyncMock(return_value=sample_milestone)
        
        # Mock getting user milestone
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_milestone
        mock_db_session.execute.return_value = mock_result
        
        # Mock update_dependent_milestones
        with patch(
            'backend.src.models.milestone.update_dependent_milestones',
            AsyncMock(return_value=["M1"])
        ):
            # Execute
            success, message, newly_unlocked = await milestone_service.complete_milestone(
                user_id, milestone_code, generated_output, quality_score
            )
        
        # Assert
        assert success is True
        assert "completed successfully" in message
        assert newly_unlocked == ["M1"]
        assert sample_user_milestone.status == MilestoneStatus.COMPLETED
        assert sample_user_milestone.completion_percentage == 100.0
        assert sample_user_milestone.generated_output == generated_output
        assert sample_user_milestone.quality_score == quality_score
        mock_cache_service.invalidate_user_cache.assert_called_once_with(user_id)
        mock_cache_service.increment_milestone_stats.assert_called_once_with(
            milestone_code, "completed"
        )
    
    @pytest.mark.asyncio
    async def test_fail_milestone(
        self,
        milestone_service,
        mock_db_session,
        mock_cache_service,
        sample_milestone,
        sample_user_milestone
    ):
        """Test failing a milestone."""
        # Setup
        user_id = str(sample_user_milestone.user_id)
        milestone_code = "M0"
        error_message = "Processing failed due to timeout"
        
        sample_user_milestone.status = MilestoneStatus.IN_PROGRESS
        
        # Mock getting milestone
        milestone_service.get_milestone_by_code = AsyncMock(return_value=sample_milestone)
        
        # Mock getting user milestone
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_milestone
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        success, message = await milestone_service.fail_milestone(
            user_id, milestone_code, error_message
        )
        
        # Assert
        assert success is True
        assert "marked as failed" in message
        assert sample_user_milestone.status == MilestoneStatus.FAILED
        assert sample_user_milestone.last_error == error_message
        mock_cache_service.increment_milestone_stats.assert_called_once_with(
            milestone_code, "failed"
        )


class TestArtifactManagement:
    """Test artifact creation and retrieval."""
    
    @pytest.mark.asyncio
    async def test_create_milestone_artifact(
        self,
        milestone_service,
        mock_db_session,
        mock_cache_service,
        sample_milestone,
        sample_user_milestone
    ):
        """Test creating a milestone artifact."""
        # Setup
        user_id = str(sample_user_milestone.user_id)
        milestone_code = "M0"
        artifact_name = "Feasibility Report"
        artifact_type = "pdf"
        content = {"report": "data"}
        storage_path = "/artifacts/report.pdf"
        
        # Mock getting milestone
        milestone_service.get_milestone_by_code = AsyncMock(return_value=sample_milestone)
        
        # Mock getting user milestone
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user_milestone
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        artifact = await milestone_service.create_milestone_artifact(
            user_id,
            milestone_code,
            artifact_name,
            artifact_type,
            content,
            storage_path
        )
        
        # Assert
        assert artifact is not None
        assert artifact.name == artifact_name
        assert artifact.artifact_type == artifact_type
        assert artifact.content == content
        assert artifact.storage_path == storage_path
        mock_db_session.add.assert_called_once()
        mock_cache_service.cache_artifact.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_artifacts(
        self,
        milestone_service,
        mock_db_session,
        sample_milestone
    ):
        """Test getting user artifacts."""
        # Setup
        user_id = str(uuid4())
        milestone_code = "M0"
        
        # Mock artifact
        mock_artifact = UserMilestoneArtifact(
            id=uuid4(),
            name="Test Artifact",
            artifact_type="pdf"
        )
        
        # Mock getting milestone
        milestone_service.get_milestone_by_code = AsyncMock(return_value=sample_milestone)
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [mock_artifact]
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        artifacts = await milestone_service.get_user_artifacts(user_id, milestone_code)
        
        # Assert
        assert len(artifacts) == 1
        assert artifacts[0] == mock_artifact


class TestAnalyticsAndReporting:
    """Test analytics and reporting functions."""
    
    @pytest.mark.asyncio
    async def test_get_user_analytics(
        self,
        milestone_service,
        mock_db_session
    ):
        """Test getting user analytics."""
        # Setup
        user_id = str(uuid4())
        
        # Create mock user milestones with different statuses
        completed_milestone = UserMilestone(
            status=MilestoneStatus.COMPLETED,
            time_spent_seconds=3600,
            quality_score=0.9,
            milestone=Mock(code="M0")
        )
        
        in_progress_milestone = UserMilestone(
            status=MilestoneStatus.IN_PROGRESS,
            time_spent_seconds=1800,
            milestone=Mock(code="M1")
        )
        
        locked_milestone = UserMilestone(
            status=MilestoneStatus.LOCKED,
            milestone=Mock(code="M2")
        )
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [
            completed_milestone,
            in_progress_milestone,
            locked_milestone
        ]
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        analytics = await milestone_service.get_user_analytics(user_id)
        
        # Assert
        assert analytics["total_milestones"] == 3
        assert analytics["completed"] == 1
        assert analytics["in_progress"] == 1
        assert analytics["locked"] == 1
        assert analytics["total_time_spent_hours"] == 1.5  # 3600 + 1800 seconds
        assert analytics["completion_rate"] == (1/3) * 100
        assert analytics["average_quality_score"] == 0.9
    
    @pytest.mark.asyncio
    async def test_get_milestone_statistics(
        self,
        milestone_service,
        mock_db_session,
        mock_cache_service,
        sample_milestone
    ):
        """Test getting milestone statistics."""
        # Setup
        milestone_code = "M0"
        
        # Mock cache stats
        cache_stats = {
            "started": 100,
            "completed": 75,
            "failed": 5,
            "skipped": 0,
            "completion_rate": 75.0
        }
        mock_cache_service.get_milestone_stats.return_value = cache_stats
        
        # Mock getting milestone
        milestone_service.get_milestone_by_code = AsyncMock(return_value=sample_milestone)
        
        # Mock completion times query
        mock_result_times = AsyncMock()
        mock_result_times.scalars.return_value.all.return_value = [3600, 4200, 3000]
        
        # Mock quality scores query
        mock_result_scores = AsyncMock()
        mock_result_scores.scalars.return_value.all.return_value = [0.9, 0.85, 0.95]
        
        mock_db_session.execute.side_effect = [mock_result_times, mock_result_scores]
        
        # Execute
        stats = await milestone_service.get_milestone_statistics(milestone_code)
        
        # Assert
        assert stats["started"] == 100
        assert stats["completed"] == 75
        assert stats["completion_rate"] == 75.0
        assert "average_completion_time_minutes" in stats
        assert stats["average_completion_time_minutes"] == 60.0  # (3600+4200+3000)/3/60
        assert "average_quality_score" in stats
        assert stats["average_quality_score"] == 0.9  # (0.9+0.85+0.95)/3


class TestHelperMethods:
    """Test helper methods."""
    
    @pytest.mark.asyncio
    async def test_check_milestone_access_free_user_paid_milestone(
        self,
        milestone_service,
        mock_db_session,
        sample_user
    ):
        """Test access check for free user on paid milestone."""
        # Setup
        user_id = str(sample_user.id)
        milestone = Milestone(
            id=uuid4(),
            code="M1",
            requires_payment=True
        )
        
        # Mock getting user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        has_access, message = await milestone_service._check_milestone_access(
            user_id, milestone
        )
        
        # Assert
        assert has_access is False
        assert "requires a paid subscription" in message
    
    @pytest.mark.asyncio
    async def test_check_milestone_access_with_dependencies(
        self,
        milestone_service,
        mock_db_session,
        sample_user
    ):
        """Test access check with unmet dependencies."""
        # Setup
        user_id = str(sample_user.id)
        milestone = Milestone(
            id=uuid4(),
            code="M2",
            requires_payment=False
        )
        
        # Mock getting user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result
        
        # Mock dependency check
        with patch(
            'backend.src.models.milestone.check_milestone_dependencies',
            AsyncMock(return_value=(False, ["M1"]))
        ):
            # Execute
            has_access, message = await milestone_service._check_milestone_access(
                user_id, milestone
            )
        
        # Assert
        assert has_access is False
        assert "Missing dependencies: M1" in message
    
    def test_get_mime_type(self, milestone_service):
        """Test MIME type detection."""
        assert milestone_service._get_mime_type("pdf") == "application/pdf"
        assert milestone_service._get_mime_type("xlsx") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert milestone_service._get_mime_type("json") == "application/json"
        assert milestone_service._get_mime_type("unknown") == "application/octet-stream"