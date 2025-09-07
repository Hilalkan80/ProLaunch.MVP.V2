"""
Unit Tests for Milestone Dependency Manager

Comprehensive test suite for dependency validation, circular
dependency detection, and auto-unlock functionality.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from src.services.dependency_manager import (
    DependencyManager,
    DependencyType,
    DependencyCondition
)
from src.models.milestone import (
    Milestone,
    MilestoneDependency,
    UserMilestone,
    MilestoneStatus,
    MilestoneType
)
from src.models.user import User, SubscriptionTier
from src.core.exceptions import (
    CircularDependencyError,
    DependencyValidationError,
    MilestoneNotFoundError
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    cache = AsyncMock()
    cache.invalidate_user_cache = AsyncMock()
    cache.invalidate_milestone_cache = AsyncMock()
    cache.publish_progress_update = AsyncMock()
    cache.get_user_progress = AsyncMock(return_value=None)
    cache.set_user_progress = AsyncMock()
    return cache


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.get_cache = AsyncMock(return_value=None)
    redis.set_cache = AsyncMock()
    redis.delete_cache = AsyncMock()
    return redis


@pytest.fixture
def dependency_manager(mock_db_session, mock_cache_service, mock_redis_client):
    """Create a DependencyManager instance with mocked dependencies."""
    return DependencyManager(mock_db_session, mock_cache_service, mock_redis_client)


@pytest.fixture
def sample_milestones():
    """Create sample milestone objects."""
    milestones = []
    for i in range(5):
        milestone = Mock(spec=Milestone)
        milestone.id = uuid4()
        milestone.code = f"M{i}"
        milestone.name = f"Milestone {i}"
        milestone.milestone_type = MilestoneType.PAID
        milestone.requires_payment = i > 0  # M0 is free
        milestone.auto_unlock = i > 1  # M2+ auto-unlock
        milestone.is_active = True
        milestone.prompt_template = {"steps": ["step1", "step2"]}
        milestone.to_dict = Mock(return_value={
            "id": str(milestone.id),
            "code": milestone.code,
            "name": milestone.name
        })
        milestones.append(milestone)
    return milestones


@pytest.fixture
def sample_user():
    """Create a sample user."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.subscription_tier = SubscriptionTier.PREMIUM
    return user


class TestDependencyCreation:
    """Test dependency creation and validation."""
    
    @pytest.mark.asyncio
    async def test_add_dependency_success(self, dependency_manager, sample_milestones, mock_db_session):
        """Test successful dependency addition."""
        m1, m2 = sample_milestones[1], sample_milestones[2]
        
        # Mock database queries
        mock_db_session.execute.side_effect = [
            # First call: get milestone
            Mock(scalar_one_or_none=Mock(return_value=m2)),
            # Second call: get dependency
            Mock(scalar_one_or_none=Mock(return_value=m1)),
            # Third call: check existing dependency
            Mock(scalar_one_or_none=Mock(return_value=None)),
            # Fourth call: get all dependencies for cycle check
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))
        ]
        
        success, message = await dependency_manager.add_dependency(
            str(m2.id),
            str(m1.id),
            is_required=True,
            minimum_completion=100.0
        )
        
        assert success is True
        assert "successfully" in message.lower()
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_dependency_self_reference(self, dependency_manager, sample_milestones, mock_db_session):
        """Test that self-dependencies are rejected."""
        m1 = sample_milestones[1]
        
        # Mock database queries
        mock_db_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=m1)),
            Mock(scalar_one_or_none=Mock(return_value=m1))
        ]
        
        success, message = await dependency_manager.add_dependency(
            str(m1.id),
            str(m1.id)
        )
        
        assert success is False
        assert "cannot depend on itself" in message.lower()
        mock_db_session.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_add_dependency_already_exists(self, dependency_manager, sample_milestones, mock_db_session):
        """Test that duplicate dependencies are rejected."""
        m1, m2 = sample_milestones[1], sample_milestones[2]
        
        existing_dep = Mock(spec=MilestoneDependency)
        existing_dep.milestone_id = m2.id
        existing_dep.dependency_id = m1.id
        
        mock_db_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=m2)),
            Mock(scalar_one_or_none=Mock(return_value=m1)),
            Mock(scalar_one_or_none=Mock(return_value=existing_dep))
        ]
        
        success, message = await dependency_manager.add_dependency(
            str(m2.id),
            str(m1.id)
        )
        
        assert success is False
        assert "already exists" in message.lower()
        mock_db_session.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_add_dependency_would_create_cycle(self, dependency_manager, sample_milestones, mock_db_session):
        """Test that circular dependencies are detected."""
        m1, m2, m3 = sample_milestones[1], sample_milestones[2], sample_milestones[3]
        
        # Create existing dependencies: M2 -> M3 -> M1
        existing_deps = [
            Mock(milestone_id=m3.id, dependency_id=m2.id),
            Mock(milestone_id=m1.id, dependency_id=m3.id)
        ]
        
        mock_db_session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=m2)),
            Mock(scalar_one_or_none=Mock(return_value=m1)),
            Mock(scalar_one_or_none=Mock(return_value=None)),
            # Dependencies for cycle check
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=existing_deps))))
        ]
        
        # Trying to add M1 -> M2 would create cycle
        success, message = await dependency_manager.add_dependency(
            str(m2.id),
            str(m1.id)
        )
        
        assert success is False
        assert "circular" in message.lower()
        mock_db_session.add.assert_not_called()


class TestDependencyValidation:
    """Test dependency validation logic."""
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_all_met(self, dependency_manager, sample_milestones, sample_user, mock_db_session):
        """Test validation when all dependencies are met."""
        m1, m2 = sample_milestones[1], sample_milestones[2]
        
        # Create dependency: M2 depends on M1
        dep = Mock(spec=MilestoneDependency)
        dep.milestone_id = m2.id
        dep.dependency_id = m1.id
        dep.is_required = True
        dep.minimum_completion_percentage = 100.0
        
        # Create user milestone showing M1 is completed
        user_milestone = Mock(spec=UserMilestone)
        user_milestone.milestone_id = m1.id
        user_milestone.status = MilestoneStatus.COMPLETED
        user_milestone.completion_percentage = 100.0
        
        mock_db_session.execute.side_effect = [
            # Get dependencies for M2
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[dep])))),
            # Get user progress for M1
            Mock(scalar_one_or_none=Mock(return_value=user_milestone))
        ]
        
        all_met, unmet = await dependency_manager.validate_dependencies(
            str(sample_user.id),
            str(m2.id)
        )
        
        assert all_met is True
        assert len(unmet) == 0
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_unmet(self, dependency_manager, sample_milestones, sample_user, mock_db_session, mock_redis_client):
        """Test validation when dependencies are not met."""
        m1, m2 = sample_milestones[1], sample_milestones[2]
        
        # Create dependency: M2 depends on M1
        dep = Mock(spec=MilestoneDependency)
        dep.milestone_id = m2.id
        dep.dependency_id = m1.id
        dep.is_required = True
        dep.minimum_completion_percentage = 100.0
        dep.dependency = m1
        
        # No user milestone for M1 (not started)
        mock_db_session.execute.side_effect = [
            # Get dependencies for M2
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[dep])))),
            # Get user progress for M1 - none found
            Mock(scalar_one_or_none=Mock(return_value=None)),
            # Get milestone M1 for details
            Mock(scalar_one_or_none=Mock(return_value=m1))
        ]
        
        mock_redis_client.get_cache.return_value = None
        
        all_met, unmet = await dependency_manager.validate_dependencies(
            str(sample_user.id),
            str(m2.id)
        )
        
        assert all_met is False
        assert len(unmet) == 1
        assert unmet[0]["milestone_code"] == "M1"
    
    @pytest.mark.asyncio
    async def test_validate_optional_dependencies(self, dependency_manager, sample_milestones, sample_user, mock_db_session):
        """Test that optional dependencies don't block progress."""
        m1, m2, m3 = sample_milestones[1], sample_milestones[2], sample_milestones[3]
        
        # Create dependencies: M3 requires M1, optionally depends on M2
        required_dep = Mock(spec=MilestoneDependency)
        required_dep.milestone_id = m3.id
        required_dep.dependency_id = m1.id
        required_dep.is_required = True
        required_dep.minimum_completion_percentage = 100.0
        required_dep.dependency = m1
        
        optional_dep = Mock(spec=MilestoneDependency)
        optional_dep.milestone_id = m3.id
        optional_dep.dependency_id = m2.id
        optional_dep.is_required = False
        optional_dep.minimum_completion_percentage = 100.0
        optional_dep.dependency = m2
        
        # M1 is completed, M2 is not
        m1_progress = Mock(spec=UserMilestone)
        m1_progress.completion_percentage = 100.0
        
        mock_db_session.execute.side_effect = [
            # Get dependencies for M3
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[required_dep, optional_dep])))),
            # Get user progress for M1
            Mock(scalar_one_or_none=Mock(return_value=m1_progress)),
            # Get user progress for M2 - not started
            Mock(scalar_one_or_none=Mock(return_value=None))
        ]
        
        all_met, unmet = await dependency_manager.validate_dependencies(
            str(sample_user.id),
            str(m3.id)
        )
        
        assert all_met is True  # Optional dependency doesn't block
        assert len(unmet) == 0


class TestCircularDependencyDetection:
    """Test circular dependency detection."""
    
    @pytest.mark.asyncio
    async def test_check_circular_dependencies_none(self, dependency_manager, mock_db_session):
        """Test when no circular dependencies exist."""
        # Create linear dependencies: M1 -> M2 -> M3
        deps = [
            Mock(milestone_id=uuid4(), dependency_id=uuid4()),
            Mock(milestone_id=uuid4(), dependency_id=uuid4())
        ]
        
        mock_db_session.execute.return_value = Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=deps)))
        )
        
        cycles = await dependency_manager.check_circular_dependencies()
        
        assert len(cycles) == 0
    
    @pytest.mark.asyncio
    async def test_check_circular_dependencies_found(self, dependency_manager, mock_db_session):
        """Test detection of circular dependencies."""
        # Create circular dependencies: M1 -> M2 -> M3 -> M1
        m1_id, m2_id, m3_id = str(uuid4()), str(uuid4()), str(uuid4())
        
        deps = [
            Mock(milestone_id=m2_id, dependency_id=m1_id),
            Mock(milestone_id=m3_id, dependency_id=m2_id),
            Mock(milestone_id=m1_id, dependency_id=m3_id)  # Creates cycle
        ]
        
        for dep in deps:
            dep.milestone_id = UUID(dep.milestone_id)
            dep.dependency_id = UUID(dep.dependency_id)
        
        mock_db_session.execute.return_value = Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=deps)))
        )
        
        cycles = await dependency_manager.check_circular_dependencies()
        
        assert len(cycles) > 0
        # Check that the cycle contains all three milestones
        cycle = cycles[0]
        assert m1_id in cycle or str(deps[0].dependency_id) in cycle


class TestAutoUnlock:
    """Test auto-unlock functionality."""
    
    @pytest.mark.asyncio
    async def test_process_completion_auto_unlock(self, dependency_manager, sample_milestones, sample_user, mock_db_session, mock_cache_service):
        """Test that completing a milestone auto-unlocks dependent milestones."""
        m1, m2 = sample_milestones[1], sample_milestones[2]
        
        # M2 depends on M1 and has auto-unlock enabled
        dep = Mock(spec=MilestoneDependency)
        dep.milestone_id = m2.id
        dep.dependency_id = m1.id
        dep.milestone = m2
        
        # User has M2 in locked state
        user_milestone = Mock(spec=UserMilestone)
        user_milestone.id = uuid4()
        user_milestone.milestone_id = m2.id
        user_milestone.status = MilestoneStatus.LOCKED
        user_milestone.updated_at = datetime.utcnow()
        
        mock_db_session.execute.side_effect = [
            # Get milestones that depend on M1
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[dep])))),
            # Get dependencies for M2 (to validate)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            # Get user milestone for M2
            Mock(scalar_one_or_none=Mock(return_value=user_milestone))
        ]
        
        newly_unlocked = await dependency_manager.process_milestone_completion(
            str(sample_user.id),
            str(m1.id)
        )
        
        assert len(newly_unlocked) == 1
        assert newly_unlocked[0]["milestone_code"] == "M2"
        assert newly_unlocked[0]["status"] == MilestoneStatus.AVAILABLE
        assert user_milestone.status == MilestoneStatus.AVAILABLE
        mock_db_session.commit.assert_called()
        mock_cache_service.invalidate_user_cache.assert_called_with(str(sample_user.id))
    
    @pytest.mark.asyncio
    async def test_process_completion_no_auto_unlock(self, dependency_manager, sample_milestones, sample_user, mock_db_session):
        """Test that milestones without auto-unlock stay locked."""
        m0, m1 = sample_milestones[0], sample_milestones[1]
        m1.auto_unlock = False  # Disable auto-unlock
        
        # M1 depends on M0
        dep = Mock(spec=MilestoneDependency)
        dep.milestone_id = m1.id
        dep.dependency_id = m0.id
        dep.milestone = m1
        
        mock_db_session.execute.return_value = Mock(
            scalars=Mock(return_value=Mock(all=Mock(return_value=[dep])))
        )
        
        newly_unlocked = await dependency_manager.process_milestone_completion(
            str(sample_user.id),
            str(m0.id)
        )
        
        assert len(newly_unlocked) == 0
        mock_db_session.commit.assert_not_called()


class TestConditionalDependencies:
    """Test conditional dependency evaluation."""
    
    @pytest.mark.asyncio
    async def test_evaluate_user_tier_condition(self, dependency_manager, sample_milestones, sample_user, mock_db_session, mock_redis_client):
        """Test evaluation of user tier conditions."""
        m1, m2 = sample_milestones[1], sample_milestones[2]
        
        # Create conditional dependency
        dep = Mock(spec=MilestoneDependency)
        dep.milestone_id = m2.id
        dep.dependency_id = m1.id
        dep.is_required = True
        dep.dependency = m1
        
        # Set conditional metadata
        conditions = {
            DependencyCondition.USER_TIER: SubscriptionTier.PREMIUM
        }
        
        mock_redis_client.get_cache.return_value = json.dumps({
            "type": DependencyType.CONDITIONAL,
            "conditions": conditions
        })
        
        mock_db_session.execute.side_effect = [
            # Get dependencies
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[dep])))),
            # Get user tier
            Mock(scalar_one_or_none=Mock(return_value=SubscriptionTier.PREMIUM)),
            # Get milestone for response
            Mock(scalar_one_or_none=Mock(return_value=m1))
        ]
        
        result = await dependency_manager.evaluate_conditional_dependencies(
            str(sample_user.id),
            str(m2.id)
        )
        
        assert result["all_conditions_met"] is True
        assert len(result["conditional_dependencies"]) == 1
        assert result["conditional_dependencies"][0]["is_met"] is True
    
    @pytest.mark.asyncio
    async def test_evaluate_completion_score_condition(self, dependency_manager, sample_milestones, sample_user, mock_db_session, mock_redis_client):
        """Test evaluation of completion score conditions."""
        m1, m2 = sample_milestones[1], sample_milestones[2]
        
        dep = Mock(spec=MilestoneDependency)
        dep.milestone_id = m2.id
        dep.dependency_id = m1.id
        dep.dependency = m1
        
        conditions = {
            DependencyCondition.COMPLETION_SCORE: {
                "min_score": 4.0,
                "milestone_id": str(m1.id)
            }
        }
        
        mock_redis_client.get_cache.return_value = json.dumps({
            "type": DependencyType.CONDITIONAL,
            "conditions": conditions
        })
        
        # User has completed M1 with score 4.5
        user_milestone = Mock(spec=UserMilestone)
        user_milestone.quality_score = 4.5
        
        mock_db_session.execute.side_effect = [
            # Get dependencies
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[dep])))),
            # Get user milestone for score check
            Mock(scalar_one_or_none=Mock(return_value=user_milestone)),
            # Get milestone for response
            Mock(scalar_one_or_none=Mock(return_value=m1))
        ]
        
        result = await dependency_manager.evaluate_conditional_dependencies(
            str(sample_user.id),
            str(m2.id)
        )
        
        assert result["all_conditions_met"] is True
        assert result["conditional_dependencies"][0]["evaluation"]["conditions"][DependencyCondition.COMPLETION_SCORE]["met"] is True


class TestDependencyChain:
    """Test dependency chain retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_dependency_chain_simple(self, dependency_manager, sample_milestones, mock_db_session):
        """Test getting a simple dependency chain."""
        m1, m2, m3 = sample_milestones[1], sample_milestones[2], sample_milestones[3]
        
        # M3 -> M2 -> M1
        deps_m3 = [Mock(
            dependency_id=m2.id,
            is_required=True,
            minimum_completion_percentage=100.0,
            dependency=m2
        )]
        
        deps_m2 = [Mock(
            dependency_id=m1.id,
            is_required=True,
            minimum_completion_percentage=100.0,
            dependency=m1
        )]
        
        mock_db_session.execute.side_effect = [
            # Get dependencies for M3
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=deps_m3)))),
            # Get M2 details
            Mock(scalar_one_or_none=Mock(return_value=m2)),
            # Get dependencies for M2
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=deps_m2)))),
            # Get M1 details
            Mock(scalar_one_or_none=Mock(return_value=m1)),
            # Get dependencies for M1 (none)
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))
        ]
        
        chain = await dependency_manager.get_dependency_chain(str(m3.id))
        
        assert len(chain) == 2
        assert chain[0]["milestone_code"] == "M2"
        assert chain[1]["milestone_code"] == "M1"
    
    @pytest.mark.asyncio
    async def test_get_dependency_chain_with_optional(self, dependency_manager, sample_milestones, mock_db_session):
        """Test dependency chain with optional dependencies."""
        m1, m2, m3 = sample_milestones[1], sample_milestones[2], sample_milestones[3]
        
        # M3 requires M1, optionally depends on M2
        deps = [
            Mock(
                dependency_id=m1.id,
                is_required=True,
                minimum_completion_percentage=100.0,
                dependency=m1
            ),
            Mock(
                dependency_id=m2.id,
                is_required=False,
                minimum_completion_percentage=100.0,
                dependency=m2
            )
        ]
        
        mock_db_session.execute.side_effect = [
            # Get dependencies for M3
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=deps)))),
            # Get M1 details
            Mock(scalar_one_or_none=Mock(return_value=m1)),
            # Get dependencies for M1
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            # Get M2 details (for optional)
            Mock(scalar_one_or_none=Mock(return_value=m2)),
            # Get dependencies for M2
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))
        ]
        
        # Without optional
        chain = await dependency_manager.get_dependency_chain(str(m3.id), include_optional=False)
        assert len(chain) == 1
        assert chain[0]["milestone_code"] == "M1"
        
        # Reset mock for second call
        mock_db_session.execute.side_effect = [
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=deps)))),
            Mock(scalar_one_or_none=Mock(return_value=m1)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            Mock(scalar_one_or_none=Mock(return_value=m2)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))
        ]
        
        # With optional
        chain = await dependency_manager.get_dependency_chain(str(m3.id), include_optional=True)
        assert len(chain) == 2