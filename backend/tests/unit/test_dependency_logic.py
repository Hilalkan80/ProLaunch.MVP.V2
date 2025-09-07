"""
Unit Tests for Dependency Logic and Validation

Comprehensive test coverage for milestone dependency management including
validation, dependency resolution, circular dependency detection, and
complex dependency scenarios.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from typing import List, Dict, Any

from backend.src.services.dependency_manager import DependencyManager
from backend.src.services.milestone_cache import MilestoneCacheService
from backend.src.models.milestone import (
    Milestone, MilestoneDependency, UserMilestone,
    MilestoneStatus, MilestoneType,
    check_milestone_dependencies,
    update_dependent_milestones
)
from backend.src.models.user import User, SubscriptionTier


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    service = AsyncMock(spec=MilestoneCacheService)
    service.get_dependency_check = AsyncMock(return_value=None)
    service.set_dependency_check = AsyncMock(return_value=True)
    service.invalidate_user_cache = AsyncMock(return_value=True)
    service.publish_progress_update = AsyncMock(return_value=1)
    return service


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.publish = AsyncMock(return_value=1)
    return client


@pytest.fixture
def dependency_manager(mock_db_session, mock_cache_service, mock_redis_client):
    """Create a dependency manager instance."""
    return DependencyManager(mock_db_session, mock_cache_service, mock_redis_client)


@pytest.fixture
def sample_milestones():
    """Create a set of sample milestones with dependencies."""
    milestones = {
        "M0": Milestone(
            id=uuid4(),
            code="M0",
            name="Feasibility Snapshot",
            milestone_type=MilestoneType.FREE,
            order_index=0,
            requires_payment=False
        ),
        "M1": Milestone(
            id=uuid4(),
            code="M1", 
            name="Market Analysis",
            milestone_type=MilestoneType.PAID,
            order_index=1,
            requires_payment=True
        ),
        "M2": Milestone(
            id=uuid4(),
            code="M2",
            name="Business Model Canvas",
            milestone_type=MilestoneType.PAID,
            order_index=2,
            requires_payment=True
        ),
        "M3": Milestone(
            id=uuid4(),
            code="M3",
            name="Financial Projections",
            milestone_type=MilestoneType.PAID,
            order_index=3,
            requires_payment=True
        ),
        "M4": Milestone(
            id=uuid4(),
            code="M4",
            name="Go-to-Market Strategy",
            milestone_type=MilestoneType.PAID,
            order_index=4,
            requires_payment=True
        )
    }
    return milestones


@pytest.fixture
def sample_dependencies(sample_milestones):
    """Create sample milestone dependencies."""
    # Dependency structure:
    # M1 depends on M0
    # M2 depends on M0
    # M3 depends on M1, M2
    # M4 depends on M3
    
    dependencies = [
        MilestoneDependency(
            id=uuid4(),
            milestone_id=sample_milestones["M1"].id,
            dependency_id=sample_milestones["M0"].id,
            is_required=True,
            minimum_completion_percentage=100.0
        ),
        MilestoneDependency(
            id=uuid4(),
            milestone_id=sample_milestones["M2"].id,
            dependency_id=sample_milestones["M0"].id,
            is_required=True,
            minimum_completion_percentage=100.0
        ),
        MilestoneDependency(
            id=uuid4(),
            milestone_id=sample_milestones["M3"].id,
            dependency_id=sample_milestones["M1"].id,
            is_required=True,
            minimum_completion_percentage=80.0
        ),
        MilestoneDependency(
            id=uuid4(),
            milestone_id=sample_milestones["M3"].id,
            dependency_id=sample_milestones["M2"].id,
            is_required=True,
            minimum_completion_percentage=80.0
        ),
        MilestoneDependency(
            id=uuid4(),
            milestone_id=sample_milestones["M4"].id,
            dependency_id=sample_milestones["M3"].id,
            is_required=True,
            minimum_completion_percentage=100.0
        )
    ]
    
    return dependencies


class TestBasicDependencyValidation:
    """Test basic dependency validation logic."""
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_no_dependencies(
        self,
        dependency_manager,
        mock_db_session
    ):
        """Test validating milestone with no dependencies."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock empty dependencies query
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id
        )
        
        # Assert
        assert all_met is True
        assert unmet == []
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_all_met(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones,
        sample_dependencies
    ):
        """Test validating milestone when all dependencies are met."""
        user_id = str(uuid4())
        milestone_id = str(sample_milestones["M3"].id)  # M3 depends on M1 and M2
        
        # Mock dependencies query
        relevant_deps = [dep for dep in sample_dependencies 
                        if dep.milestone_id == sample_milestones["M3"].id]
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = relevant_deps
        
        # Mock user progress queries - both M1 and M2 are completed with sufficient percentage
        m1_progress = UserMilestone(
            user_id=user_id,
            milestone_id=sample_milestones["M1"].id,
            status=MilestoneStatus.COMPLETED,
            completion_percentage=100.0
        )
        
        m2_progress = UserMilestone(
            user_id=user_id,
            milestone_id=sample_milestones["M2"].id,
            status=MilestoneStatus.COMPLETED,
            completion_percentage=90.0  # Above 80% threshold
        )
        
        # Setup sequential query results
        mock_progress_results = [
            AsyncMock(scalar_one_or_none=AsyncMock(return_value=m1_progress)),
            AsyncMock(scalar_one_or_none=AsyncMock(return_value=m2_progress))
        ]
        
        mock_db_session.execute.side_effect = [mock_deps_result] + mock_progress_results
        
        # Execute
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id
        )
        
        # Assert
        assert all_met is True
        assert unmet == []
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_some_unmet(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones,
        sample_dependencies
    ):
        """Test validating milestone when some dependencies are unmet."""
        user_id = str(uuid4())
        milestone_id = str(sample_milestones["M3"].id)
        
        # Mock dependencies
        relevant_deps = [dep for dep in sample_dependencies 
                        if dep.milestone_id == sample_milestones["M3"].id]
        
        # Set up dependency milestone references
        for dep in relevant_deps:
            if dep.dependency_id == sample_milestones["M1"].id:
                dep.dependency = sample_milestones["M1"]
            elif dep.dependency_id == sample_milestones["M2"].id:
                dep.dependency = sample_milestones["M2"]
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = relevant_deps
        
        # Mock user progress - M1 completed, M2 incomplete
        m1_progress = UserMilestone(
            user_id=user_id,
            milestone_id=sample_milestones["M1"].id,
            status=MilestoneStatus.COMPLETED,
            completion_percentage=100.0
        )
        
        # M2 is in progress but below threshold
        m2_progress = UserMilestone(
            user_id=user_id,
            milestone_id=sample_milestones["M2"].id,
            status=MilestoneStatus.IN_PROGRESS,
            completion_percentage=70.0  # Below 80% threshold
        )
        
        mock_progress_results = [
            AsyncMock(scalar_one_or_none=AsyncMock(return_value=m1_progress)),
            AsyncMock(scalar_one_or_none=AsyncMock(return_value=m2_progress))
        ]
        
        mock_db_session.execute.side_effect = [mock_deps_result] + mock_progress_results
        
        # Execute
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id
        )
        
        # Assert
        assert all_met is False
        assert len(unmet) == 1
        assert unmet[0]["milestone_code"] == "M2"
        assert unmet[0]["current_percentage"] == 70.0
        assert unmet[0]["required_percentage"] == 80.0
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_optional_dependencies(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones
    ):
        """Test validating milestone with optional dependencies."""
        user_id = str(uuid4())
        milestone_id = str(sample_milestones["M2"].id)
        
        # Create optional dependency
        optional_dep = MilestoneDependency(
            milestone_id=sample_milestones["M2"].id,
            dependency_id=sample_milestones["M1"].id,
            is_required=False,  # Optional
            minimum_completion_percentage=100.0
        )
        optional_dep.dependency = sample_milestones["M1"]
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = [optional_dep]
        
        # Mock no progress on optional dependency
        mock_progress_result = AsyncMock()
        mock_progress_result.scalar_one_or_none.return_value = None
        
        mock_db_session.execute.side_effect = [mock_deps_result, mock_progress_result]
        
        # Execute
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id
        )
        
        # Assert - optional dependencies should not block
        assert all_met is True
        assert unmet == []
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_with_cache_hit(
        self,
        dependency_manager,
        mock_cache_service
    ):
        """Test dependency validation with cached result."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock cached result
        cached_result = {
            "can_start": True,
            "missing_dependencies": [],
            "checked_at": datetime.utcnow().isoformat()
        }
        mock_cache_service.get_dependency_check.return_value = cached_result
        
        # Execute
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id
        )
        
        # Assert
        assert all_met is True
        assert unmet == []
        mock_cache_service.get_dependency_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_dependencies_with_conditions(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones
    ):
        """Test dependency validation with conditional logic."""
        user_id = str(uuid4())
        milestone_id = str(sample_milestones["M3"].id)
        
        # Create conditional dependency
        conditional_dep = MilestoneDependency(
            milestone_id=sample_milestones["M3"].id,
            dependency_id=sample_milestones["M1"].id,
            is_required=True,
            minimum_completion_percentage=50.0  # Lower threshold for conditional
        )
        conditional_dep.dependency = sample_milestones["M1"]
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = [conditional_dep]
        
        # Mock partial progress that meets conditional requirement
        partial_progress = UserMilestone(
            user_id=user_id,
            milestone_id=sample_milestones["M1"].id,
            status=MilestoneStatus.IN_PROGRESS,
            completion_percentage=60.0  # Above 50% threshold
        )
        
        mock_progress_result = AsyncMock()
        mock_progress_result.scalar_one_or_none.return_value = partial_progress
        
        mock_db_session.execute.side_effect = [mock_deps_result, mock_progress_result]
        
        # Execute with conditions check
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id, check_conditions=True
        )
        
        # Assert
        assert all_met is True
        assert unmet == []


class TestComplexDependencyScenarios:
    """Test complex dependency scenarios."""
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones
    ):
        """Test detection of circular dependencies."""
        # Create circular dependency: M1 -> M2 -> M3 -> M1
        circular_deps = [
            MilestoneDependency(
                milestone_id=sample_milestones["M1"].id,
                dependency_id=sample_milestones["M3"].id  # M1 depends on M3
            ),
            MilestoneDependency(
                milestone_id=sample_milestones["M2"].id,
                dependency_id=sample_milestones["M1"].id  # M2 depends on M1
            ),
            MilestoneDependency(
                milestone_id=sample_milestones["M3"].id,
                dependency_id=sample_milestones["M2"].id  # M3 depends on M2
            )
        ]
        
        # Mock database to return circular dependencies
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = circular_deps
        mock_db_session.execute.return_value = mock_result
        
        # Execute circular dependency check
        has_cycle = await dependency_manager.detect_circular_dependencies()
        
        # Assert
        assert has_cycle is True
    
    @pytest.mark.asyncio
    async def test_dependency_chain_validation(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones,
        sample_dependencies
    ):
        """Test validation of entire dependency chain."""
        user_id = str(uuid4())
        
        # Mock all milestones and dependencies
        mock_milestones_result = AsyncMock()
        mock_milestones_result.scalars.return_value.all.return_value = list(sample_milestones.values())
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = sample_dependencies
        
        # Mock user progress - only M0 completed
        user_progress = [
            UserMilestone(
                user_id=user_id,
                milestone_id=sample_milestones["M0"].id,
                status=MilestoneStatus.COMPLETED,
                completion_percentage=100.0
            )
        ]
        
        mock_progress_result = AsyncMock()
        mock_progress_result.scalars.return_value.all.return_value = user_progress
        
        mock_db_session.execute.side_effect = [
            mock_milestones_result,
            mock_deps_result,
            mock_progress_result
        ]
        
        # Execute dependency chain validation
        chain_status = await dependency_manager.validate_dependency_chain(user_id)
        
        # Assert
        assert "M0" in chain_status
        assert chain_status["M0"]["can_start"] is True
        assert "M1" in chain_status
        assert chain_status["M1"]["can_start"] is True  # M1 depends only on completed M0
        assert "M2" in chain_status
        assert chain_status["M2"]["can_start"] is True  # M2 depends only on completed M0
        assert "M3" in chain_status
        assert chain_status["M3"]["can_start"] is False  # M3 depends on M1 and M2 which aren't completed
        assert "M4" in chain_status
        assert chain_status["M4"]["can_start"] is False  # M4 depends on M3 which can't start
    
    @pytest.mark.asyncio
    async def test_bulk_dependency_validation(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones
    ):
        """Test bulk validation of multiple milestones."""
        user_id = str(uuid4())
        milestone_ids = [str(m.id) for m in sample_milestones.values()]
        
        # Mock dependencies for multiple milestones
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = []  # No dependencies for simplicity
        
        mock_db_session.execute.return_value = mock_deps_result
        
        # Execute bulk validation
        results = await dependency_manager.bulk_validate_dependencies(
            user_id, milestone_ids
        )
        
        # Assert
        assert len(results) == len(milestone_ids)
        for milestone_id in milestone_ids:
            assert milestone_id in results
            assert results[milestone_id]["all_met"] is True
    
    @pytest.mark.asyncio
    async def test_dependency_graph_construction(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones,
        sample_dependencies
    ):
        """Test construction of dependency graph."""
        # Mock database queries
        mock_milestones_result = AsyncMock()
        mock_milestones_result.scalars.return_value.all.return_value = list(sample_milestones.values())
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = sample_dependencies
        
        mock_db_session.execute.side_effect = [mock_milestones_result, mock_deps_result]
        
        # Execute graph construction
        graph = await dependency_manager.build_dependency_graph()
        
        # Assert graph structure
        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) == len(sample_milestones)
        assert len(graph["edges"]) == len(sample_dependencies)
        
        # Check specific relationships
        m3_edges = [edge for edge in graph["edges"] if edge["target"] == "M3"]
        assert len(m3_edges) == 2  # M3 depends on M1 and M2
    
    @pytest.mark.asyncio
    async def test_dependency_resolution_with_partial_completion(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones
    ):
        """Test dependency resolution with partial milestone completion."""
        user_id = str(uuid4())
        milestone_id = str(sample_milestones["M3"].id)
        
        # Create dependency with partial completion threshold
        partial_dep = MilestoneDependency(
            milestone_id=sample_milestones["M3"].id,
            dependency_id=sample_milestones["M1"].id,
            is_required=True,
            minimum_completion_percentage=60.0  # Allow partial completion
        )
        partial_dep.dependency = sample_milestones["M1"]
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = [partial_dep]
        
        # Mock partial progress that meets threshold
        partial_progress = UserMilestone(
            user_id=user_id,
            milestone_id=sample_milestones["M1"].id,
            status=MilestoneStatus.IN_PROGRESS,
            completion_percentage=70.0  # Above 60% threshold
        )
        
        mock_progress_result = AsyncMock()
        mock_progress_result.scalar_one_or_none.return_value = partial_progress
        
        mock_db_session.execute.side_effect = [mock_deps_result, mock_progress_result]
        
        # Execute
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id
        )
        
        # Assert
        assert all_met is True
        assert unmet == []


class TestDependencyUpdatesAndNotifications:
    """Test dependency updates and notifications."""
    
    @pytest.mark.asyncio
    async def test_process_milestone_completion_unlocks(
        self,
        dependency_manager,
        mock_db_session,
        mock_cache_service,
        sample_milestones,
        sample_dependencies
    ):
        """Test processing milestone completion to unlock dependents."""
        user_id = str(uuid4())
        completed_milestone_id = str(sample_milestones["M0"].id)  # M0 completed
        
        # Mock finding dependents (M1 and M2 depend on M0)
        dependents = [dep for dep in sample_dependencies 
                     if dep.dependency_id == sample_milestones["M0"].id]
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = dependents
        
        # Mock existing user milestones (locked)
        existing_milestones = [
            UserMilestone(
                user_id=user_id,
                milestone_id=sample_milestones["M1"].id,
                status=MilestoneStatus.LOCKED
            ),
            UserMilestone(
                user_id=user_id,
                milestone_id=sample_milestones["M2"].id,
                status=MilestoneStatus.LOCKED
            )
        ]
        
        mock_user_milestone_results = [
            AsyncMock(scalar_one_or_none=AsyncMock(return_value=existing_milestones[0])),
            AsyncMock(scalar_one_or_none=AsyncMock(return_value=existing_milestones[1]))
        ]
        
        # Mock dependency validation (both can start after M0 completion)
        with patch.object(dependency_manager, 'validate_dependencies', 
                         AsyncMock(return_value=(True, []))):
            
            mock_db_session.execute.side_effect = [mock_deps_result] + mock_user_milestone_results
            
            # Execute
            unlocked = await dependency_manager.process_milestone_completion(
                user_id, completed_milestone_id
            )
        
        # Assert
        assert len(unlocked) == 2
        assert any(u["milestone_code"] == "M1" for u in unlocked)
        assert any(u["milestone_code"] == "M2" for u in unlocked)
        
        # Check that milestones were updated to available
        for milestone in existing_milestones:
            assert milestone.status == MilestoneStatus.AVAILABLE
    
    @pytest.mark.asyncio
    async def test_real_time_dependency_notifications(
        self,
        dependency_manager,
        mock_redis_client,
        mock_cache_service
    ):
        """Test real-time notifications for dependency changes."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock publishing dependency update
        update_data = {
            "type": "dependency_unlocked",
            "milestone_id": milestone_id,
            "dependencies_met": True,
            "newly_available": ["M2", "M3"]
        }
        
        # Execute notification
        result = await dependency_manager.publish_dependency_update(
            user_id, update_data
        )
        
        # Assert
        assert result > 0  # Redis publish returns number of subscribers
        mock_redis_client.publish.assert_called_once()
        
        # Verify published data structure
        call_args = mock_redis_client.publish.call_args
        channel = call_args[0][0]
        message = call_args[0][1]
        
        assert f"dependencies:{user_id}" in channel
        assert "dependency_unlocked" in str(message)
    
    @pytest.mark.asyncio
    async def test_dependency_invalidation_cascade(
        self,
        dependency_manager,
        mock_cache_service,
        sample_milestones
    ):
        """Test cascading cache invalidation when dependencies change."""
        user_id = str(uuid4())
        changed_milestone_id = str(sample_milestones["M1"].id)
        
        # Execute dependency change
        await dependency_manager.invalidate_dependency_cache(
            user_id, changed_milestone_id
        )
        
        # Assert cache invalidation was called
        mock_cache_service.invalidate_user_cache.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_dependency_health_check(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones,
        sample_dependencies
    ):
        """Test dependency system health check."""
        # Mock database queries
        mock_milestones_result = AsyncMock()
        mock_milestones_result.scalars.return_value.all.return_value = list(sample_milestones.values())
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = sample_dependencies
        
        mock_db_session.execute.side_effect = [mock_milestones_result, mock_deps_result]
        
        # Execute health check
        health_report = await dependency_manager.health_check()
        
        # Assert health metrics
        assert "total_milestones" in health_report
        assert "total_dependencies" in health_report
        assert "circular_dependencies" in health_report
        assert "orphaned_milestones" in health_report
        assert "dependency_depth" in health_report
        
        assert health_report["total_milestones"] == len(sample_milestones)
        assert health_report["total_dependencies"] == len(sample_dependencies)
        assert health_report["circular_dependencies"] is False


class TestAdvancedDependencyFeatures:
    """Test advanced dependency management features."""
    
    @pytest.mark.asyncio
    async def test_conditional_dependency_evaluation(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones
    ):
        """Test conditional dependency evaluation based on user context."""
        user_id = str(uuid4())
        milestone_id = str(sample_milestones["M3"].id)
        
        # Create conditional dependency with complex conditions
        conditional_dep = MilestoneDependency(
            milestone_id=sample_milestones["M3"].id,
            dependency_id=sample_milestones["M1"].id,
            is_required=True,
            minimum_completion_percentage=80.0
        )
        conditional_dep.dependency = sample_milestones["M1"]
        
        # Mock user context that affects conditions
        user_context = {
            "subscription_tier": "premium",
            "completion_history": {"average_quality": 0.9},
            "preferences": {"skip_optional_steps": False}
        }
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = [conditional_dep]
        
        # Mock high-quality progress that meets enhanced conditions
        premium_progress = UserMilestone(
            user_id=user_id,
            milestone_id=sample_milestones["M1"].id,
            status=MilestoneStatus.COMPLETED,
            completion_percentage=100.0,
            quality_score=0.95  # High quality
        )
        
        mock_progress_result = AsyncMock()
        mock_progress_result.scalar_one_or_none.return_value = premium_progress
        
        mock_db_session.execute.side_effect = [mock_deps_result, mock_progress_result]
        
        # Execute with user context
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id, user_context=user_context
        )
        
        # Assert
        assert all_met is True
        assert unmet == []
    
    @pytest.mark.asyncio
    async def test_dynamic_dependency_adjustment(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones
    ):
        """Test dynamic dependency adjustment based on user performance."""
        user_id = str(uuid4())
        milestone_id = str(sample_milestones["M3"].id)
        
        # Mock user performance history
        user_performance = {
            "average_completion_time": 0.8,  # 20% faster than average
            "average_quality_score": 0.92,  # High quality
            "consistency_score": 0.95  # Very consistent
        }
        
        # Create adaptive dependency
        adaptive_dep = MilestoneDependency(
            milestone_id=sample_milestones["M3"].id,
            dependency_id=sample_milestones["M1"].id,
            is_required=True,
            minimum_completion_percentage=100.0  # Base requirement
        )
        adaptive_dep.dependency = sample_milestones["M1"]
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = [adaptive_dep]
        
        # Mock progress that would normally be insufficient
        partial_progress = UserMilestone(
            user_id=user_id,
            milestone_id=sample_milestones["M1"].id,
            status=MilestoneStatus.IN_PROGRESS,
            completion_percentage=85.0,  # Below 100% but high quality
            quality_score=0.95
        )
        
        mock_progress_result = AsyncMock()
        mock_progress_result.scalar_one_or_none.return_value = partial_progress
        
        mock_db_session.execute.side_effect = [mock_deps_result, mock_progress_result]
        
        # Execute with performance-based adjustment
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id, 
            adaptive_thresholds=True,
            user_performance=user_performance
        )
        
        # Assert - high-performing user gets relaxed requirements
        assert all_met is True
        assert unmet == []
    
    @pytest.mark.asyncio
    async def test_dependency_recommendation_engine(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones,
        sample_dependencies
    ):
        """Test dependency-based recommendation engine."""
        user_id = str(uuid4())
        
        # Mock user progress
        user_progress = [
            UserMilestone(
                user_id=user_id,
                milestone_id=sample_milestones["M0"].id,
                status=MilestoneStatus.COMPLETED,
                completion_percentage=100.0
            ),
            UserMilestone(
                user_id=user_id,
                milestone_id=sample_milestones["M1"].id,
                status=MilestoneStatus.IN_PROGRESS,
                completion_percentage=60.0
            )
        ]
        
        mock_progress_result = AsyncMock()
        mock_progress_result.scalars.return_value.all.return_value = user_progress
        
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = sample_dependencies
        
        mock_db_session.execute.side_effect = [mock_progress_result, mock_deps_result]
        
        # Execute recommendation engine
        recommendations = await dependency_manager.get_milestone_recommendations(user_id)
        
        # Assert recommendations
        assert "next_milestones" in recommendations
        assert "priority_order" in recommendations
        assert "blocked_milestones" in recommendations
        assert "optimization_suggestions" in recommendations
        
        # Should recommend completing M1 first
        next_milestone = recommendations["next_milestones"][0]
        assert next_milestone["milestone_code"] == "M1"
        assert next_milestone["reason"] == "in_progress"
    
    @pytest.mark.asyncio
    async def test_parallel_dependency_processing(
        self,
        dependency_manager,
        mock_db_session,
        sample_milestones
    ):
        """Test parallel processing of multiple dependency validations."""
        user_id = str(uuid4())
        milestone_ids = [str(m.id) for m in sample_milestones.values()]
        
        # Mock parallel dependency checks
        async def mock_validate_single(user_id, milestone_id):
            # Simulate different validation results
            if milestone_id == str(sample_milestones["M0"].id):
                return True, []
            elif milestone_id == str(sample_milestones["M1"].id):
                return True, []
            else:
                return False, [{"milestone_code": "M0"}]
        
        # Execute parallel validation
        with patch.object(dependency_manager, 'validate_dependencies', 
                         side_effect=mock_validate_single):
            
            results = await dependency_manager.parallel_validate_dependencies(
                user_id, milestone_ids
            )
        
        # Assert parallel results
        assert len(results) == len(milestone_ids)
        assert results[str(sample_milestones["M0"].id)]["all_met"] is True
        assert results[str(sample_milestones["M1"].id)]["all_met"] is True
        assert results[str(sample_milestones["M2"].id)]["all_met"] is False


class TestDependencyPerformanceOptimization:
    """Test performance optimization in dependency operations."""
    
    @pytest.mark.asyncio
    async def test_cached_dependency_validation(
        self,
        dependency_manager,
        mock_cache_service
    ):
        """Test that dependency validation uses caching effectively."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # First call - cache miss
        mock_cache_service.get_dependency_check.return_value = None
        
        # Mock database validation (expensive operation)
        with patch.object(dependency_manager, '_validate_dependencies_from_db',
                         AsyncMock(return_value=(True, []))):
            
            all_met, unmet = await dependency_manager.validate_dependencies(
                user_id, milestone_id
            )
        
        # Verify result was cached
        mock_cache_service.set_dependency_check.assert_called_once()
        
        # Second call - cache hit
        cached_result = {
            "can_start": True,
            "missing_dependencies": [],
            "checked_at": datetime.utcnow().isoformat()
        }
        mock_cache_service.get_dependency_check.return_value = cached_result
        
        all_met_cached, unmet_cached = await dependency_manager.validate_dependencies(
            user_id, milestone_id
        )
        
        # Assert cached result used
        assert all_met_cached is True
        assert unmet_cached == []
    
    @pytest.mark.asyncio
    async def test_bulk_dependency_optimization(
        self,
        dependency_manager,
        mock_db_session
    ):
        """Test bulk dependency operations optimization."""
        user_id = str(uuid4())
        milestone_ids = [str(uuid4()) for _ in range(10)]  # Large batch
        
        # Mock single query for all dependencies (optimized)
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        # Execute bulk validation
        start_time = datetime.utcnow()
        results = await dependency_manager.bulk_validate_dependencies(
            user_id, milestone_ids
        )
        end_time = datetime.utcnow()
        
        # Assert optimization - single query instead of N queries
        assert mock_db_session.execute.call_count == 1
        assert len(results) == len(milestone_ids)
        
        # Performance check - should be fast
        execution_time = (end_time - start_time).total_seconds()
        assert execution_time < 1.0  # Should complete quickly
    
    @pytest.mark.asyncio
    async def test_dependency_graph_caching(
        self,
        dependency_manager,
        mock_cache_service,
        mock_db_session
    ):
        """Test caching of dependency graph for performance."""
        # Mock cached graph
        cached_graph = {
            "nodes": ["M0", "M1", "M2"],
            "edges": [{"source": "M0", "target": "M1"}],
            "cached_at": datetime.utcnow().isoformat()
        }
        
        mock_cache_service.get_dependency_graph = AsyncMock(return_value=cached_graph)
        
        # Execute graph retrieval
        graph = await dependency_manager.get_dependency_graph()
        
        # Assert cached graph used
        assert graph == cached_graph
        mock_cache_service.get_dependency_graph.assert_called_once()
        
        # Verify database not queried when cache hit
        mock_db_session.execute.assert_not_called()


class TestDependencyErrorHandling:
    """Test error handling in dependency operations."""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(
        self,
        dependency_manager,
        mock_db_session
    ):
        """Test handling database errors during dependency validation."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock database error
        mock_db_session.execute.side_effect = Exception("Database connection failed")
        
        # Execute with error handling
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id, fallback_to_cache=True
        )
        
        # Assert graceful degradation
        assert all_met is False  # Fail-safe approach
        assert "error" in str(unmet).lower()
    
    @pytest.mark.asyncio
    async def test_cache_error_handling(
        self,
        dependency_manager,
        mock_cache_service,
        mock_db_session
    ):
        """Test handling cache errors during dependency validation."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock cache error but database success
        mock_cache_service.get_dependency_check.side_effect = Exception("Redis connection failed")
        
        # Mock database fallback
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        # Execute with cache error
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id
        )
        
        # Assert fallback to database
        assert all_met is True  # Should work despite cache error
        assert unmet == []
        mock_db_session.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_corrupted_dependency_data_handling(
        self,
        dependency_manager,
        mock_db_session
    ):
        """Test handling of corrupted dependency data."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock corrupted dependency (missing required fields)
        corrupted_dep = Mock()
        corrupted_dep.dependency_id = None  # Corrupted
        corrupted_dep.is_required = True
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [corrupted_dep]
        mock_db_session.execute.return_value = mock_result
        
        # Execute with error handling
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id, skip_corrupted=True
        )
        
        # Assert corrupted data handled gracefully
        assert all_met is True  # Should skip corrupted entries
        assert unmet == []
    
    @pytest.mark.asyncio
    async def test_timeout_handling(
        self,
        dependency_manager,
        mock_db_session
    ):
        """Test handling of validation timeouts."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock slow database operation
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow query
            return AsyncMock(scalars=AsyncMock(return_value=AsyncMock(all=AsyncMock(return_value=[]))))
        
        mock_db_session.execute.side_effect = slow_execute
        
        # Execute with timeout
        all_met, unmet = await dependency_manager.validate_dependencies(
            user_id, milestone_id, timeout_seconds=1
        )
        
        # Assert timeout handling
        assert all_met is False  # Should fail safely on timeout
        assert any("timeout" in str(item).lower() for item in unmet)