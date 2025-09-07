"""
Integration Tests for Milestone End-to-End Workflows

Comprehensive integration tests that verify complete milestone workflows
from initialization through completion, including database persistence,
cache synchronization, and real-time updates.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List
import json

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.src.models.milestone import (
    Base, Milestone, MilestoneDependency, UserMilestone,
    MilestoneStatus, MilestoneType, MilestoneProgressLog,
    UserMilestoneArtifact
)
from backend.src.models.user import User, SubscriptionTier
from backend.src.services.milestone_service import MilestoneService
from backend.src.services.milestone_cache import MilestoneCacheService
from backend.src.services.dependency_manager import DependencyManager
from backend.src.infrastructure.redis.redis_mcp import RedisMCPClient
from backend.src.api.v1.milestones import (
    get_all_milestones, get_milestone_tree, start_milestone,
    update_progress, complete_milestone
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create test database session."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
async def mock_redis_client():
    """Create a functional mock Redis client for integration tests."""
    class MockRedisClient(RedisMCPClient):
        def __init__(self):
            self._cache = {}
            self._pub_sub_channels = {}
            self._locks = {}
            self._sorted_sets = {}
        
        async def get_cache(self, key: str):
            return self._cache.get(key)
        
        async def set_cache(self, key: str, value: Any, ttl: int = 3600):
            self._cache[key] = value
            return True
        
        async def delete_cache(self, key: str):
            self._cache.pop(key, None)
            return True
        
        async def publish(self, channel: str, message: Any):
            if channel not in self._pub_sub_channels:
                self._pub_sub_channels[channel] = []
            self._pub_sub_channels[channel].append(message)
            return 1
        
        async def lock(self, key: str, ttl: int = 300):
            if key not in self._locks:
                lock_token = f"lock_{uuid4().hex[:8]}"
                self._locks[key] = lock_token
                return lock_token
            return None
        
        async def unlock(self, key: str, token: str):
            if key in self._locks and self._locks[key] == token:
                del self._locks[key]
                return True
            return False
    
    return MockRedisClient()


@pytest.fixture
async def milestone_cache_service(mock_redis_client):
    """Create milestone cache service."""
    return MilestoneCacheService(mock_redis_client)


@pytest.fixture
async def milestone_service(test_db_session, milestone_cache_service):
    """Create milestone service with real database and mock cache."""
    return MilestoneService(test_db_session, milestone_cache_service)


@pytest.fixture
async def dependency_manager(test_db_session, milestone_cache_service, mock_redis_client):
    """Create dependency manager."""
    return DependencyManager(test_db_session, milestone_cache_service, mock_redis_client)


@pytest.fixture
async def test_user(test_db_session):
    """Create test user in database."""
    user = User(
        id=uuid4(),
        email="integration@test.com",
        username="integration_user",
        subscription_tier=SubscriptionTier.PREMIUM,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    
    return user


@pytest.fixture
async def test_milestones(test_db_session):
    """Create test milestone chain in database."""
    milestones = {
        "M0": Milestone(
            id=uuid4(),
            code="M0",
            name="Feasibility Snapshot",
            description="Initial feasibility assessment",
            milestone_type=MilestoneType.FREE,
            order_index=0,
            estimated_minutes=30,
            requires_payment=False,
            is_active=True,
            prompt_template={
                "steps": [
                    {"id": "idea_description", "name": "Describe Your Idea"},
                    {"id": "market_validation", "name": "Initial Market Check"}
                ]
            },
            output_schema={"type": "object", "required": ["viability_score"]},
            created_at=datetime.utcnow()
        ),
        "M1": Milestone(
            id=uuid4(),
            code="M1",
            name="Market Analysis",
            description="Comprehensive market research",
            milestone_type=MilestoneType.PAID,
            order_index=1,
            estimated_minutes=120,
            requires_payment=True,
            is_active=True,
            prompt_template={
                "steps": [
                    {"id": "market_sizing", "name": "Market Size Analysis"},
                    {"id": "competitor_research", "name": "Competitive Analysis"},
                    {"id": "customer_segments", "name": "Target Segments"}
                ]
            },
            output_schema={"type": "object", "required": ["market_size", "competitors"]},
            created_at=datetime.utcnow()
        ),
        "M2": Milestone(
            id=uuid4(),
            code="M2",
            name="Business Model Canvas",
            description="Business model development",
            milestone_type=MilestoneType.PAID,
            order_index=2,
            estimated_minutes=90,
            requires_payment=True,
            is_active=True,
            prompt_template={
                "steps": [
                    {"id": "value_proposition", "name": "Value Proposition"},
                    {"id": "revenue_streams", "name": "Revenue Model"}
                ]
            },
            output_schema={"type": "object", "required": ["canvas_data"]},
            created_at=datetime.utcnow()
        )
    }
    
    # Add milestones to database
    for milestone in milestones.values():
        test_db_session.add(milestone)
    
    await test_db_session.commit()
    
    # Create dependencies: M1 depends on M0, M2 depends on M0
    dependencies = [
        MilestoneDependency(
            milestone_id=milestones["M1"].id,
            dependency_id=milestones["M0"].id,
            is_required=True,
            minimum_completion_percentage=100.0
        ),
        MilestoneDependency(
            milestone_id=milestones["M2"].id,
            dependency_id=milestones["M0"].id,
            is_required=True,
            minimum_completion_percentage=100.0
        )
    ]
    
    for dep in dependencies:
        test_db_session.add(dep)
    
    await test_db_session.commit()
    
    # Refresh all objects
    for milestone in milestones.values():
        await test_db_session.refresh(milestone)
    
    return milestones


class TestCompleteUserJourney:
    """Test complete user journey through milestone system."""
    
    @pytest.mark.asyncio
    async def test_full_milestone_journey(
        self,
        milestone_service,
        dependency_manager,
        milestone_cache_service,
        test_user,
        test_milestones,
        test_db_session
    ):
        """Test complete user journey from initialization to completion."""
        user_id = str(test_user.id)
        
        # Step 1: Initialize user milestones
        initialized = await milestone_service.initialize_user_milestones(user_id)
        
        assert len(initialized) == 3
        assert any(um.milestone_id == test_milestones["M0"].id for um in initialized)
        
        # Verify M0 is available (free milestone)
        m0_milestone = next(um for um in initialized if um.milestone_id == test_milestones["M0"].id)
        assert m0_milestone.status == MilestoneStatus.AVAILABLE
        
        # Verify M1 and M2 are locked (depend on M0)
        m1_milestone = next(um for um in initialized if um.milestone_id == test_milestones["M1"].id)
        m2_milestone = next(um for um in initialized if um.milestone_id == test_milestones["M2"].id)
        assert m1_milestone.status == MilestoneStatus.LOCKED
        assert m2_milestone.status == MilestoneStatus.LOCKED
        
        # Step 2: Start M0 milestone
        success, message, started_milestone = await milestone_service.start_milestone(user_id, "M0")
        
        assert success is True
        assert "Started milestone M0" in message
        assert started_milestone.status == MilestoneStatus.IN_PROGRESS
        assert started_milestone.started_at is not None
        assert started_milestone.total_steps == 2  # From prompt template
        
        # Step 3: Update progress on M0
        progress_success, progress_message = await milestone_service.update_milestone_progress(
            user_id,
            "M0",
            1,
            {"idea_description": "AI-powered productivity tool for remote teams"}
        )
        
        assert progress_success is True
        assert "updated successfully" in progress_message
        
        # Refresh milestone to check updates
        await test_db_session.refresh(started_milestone)
        assert started_milestone.current_step == 1
        assert started_milestone.completion_percentage == 50.0  # 1/2 steps
        
        # Complete step 2
        await milestone_service.update_milestone_progress(
            user_id,
            "M0",
            2,
            {
                "market_validation": {
                    "target_market": "Remote teams 50-200 employees",
                    "problem_validation": "High demand for better productivity tools"
                }
            }
        )
        
        # Step 4: Complete M0 milestone
        completion_output = {
            "viability_score": 0.85,
            "key_insights": [
                "Strong market demand identified",
                "Clear value proposition for remote teams",
                "Competitive but differentiated space"
            ],
            "next_steps": ["Detailed market analysis", "Business model development"]
        }
        
        complete_success, complete_message, unlocked = await milestone_service.complete_milestone(
            user_id,
            "M0",
            completion_output,
            quality_score=0.9
        )
        
        assert complete_success is True
        assert "completed successfully" in complete_message
        assert len(unlocked) >= 2  # Should unlock M1 and M2
        
        # Verify M0 completion in database
        await test_db_session.refresh(started_milestone)
        assert started_milestone.status == MilestoneStatus.COMPLETED
        assert started_milestone.completion_percentage == 100.0
        assert started_milestone.completed_at is not None
        assert started_milestone.generated_output == completion_output
        assert started_milestone.quality_score == 0.9
        
        # Step 5: Verify dependent milestones are unlocked
        await test_db_session.refresh(m1_milestone)
        await test_db_session.refresh(m2_milestone)
        
        assert m1_milestone.status == MilestoneStatus.AVAILABLE
        assert m2_milestone.status == MilestoneStatus.AVAILABLE
        
        # Step 6: Start and complete M1 milestone
        m1_success, m1_message, m1_started = await milestone_service.start_milestone(user_id, "M1")
        assert m1_success is True
        
        # Simulate completing all steps of M1
        for step in range(1, 4):  # 3 steps
            await milestone_service.update_milestone_progress(
                user_id,
                "M1",
                step,
                {f"step_{step}_data": f"Completed step {step}"}
            )
        
        # Complete M1
        m1_output = {
            "market_size": {"tam": 5000000000, "sam": 500000000, "som": 50000000},
            "competitors": [
                {"name": "Competitor A", "market_share": 0.3},
                {"name": "Competitor B", "market_share": 0.2}
            ],
            "target_segments": ["SMB remote teams", "Enterprise distributed teams"]
        }
        
        m1_complete_success, _, _ = await milestone_service.complete_milestone(
            user_id,
            "M1",
            m1_output,
            quality_score=0.88
        )
        
        assert m1_complete_success is True
        
        # Step 7: Verify analytics and progress tracking
        user_analytics = await milestone_service.get_user_analytics(user_id)
        
        assert user_analytics["total_milestones"] == 3
        assert user_analytics["completed"] == 2  # M0 and M1
        assert user_analytics["available_count"] == 1  # M2
        assert user_analytics["completion_rate"] > 60.0
        assert user_analytics["total_time_spent_hours"] > 0
        
        # Step 8: Get milestone tree and verify structure
        tree = await milestone_service.get_user_milestone_tree_with_cache(user_id)
        
        assert len(tree["milestones"]) == 3
        assert tree["completed_count"] == 2
        assert tree["available_count"] == 1
        assert tree["total_progress"] > 65.0  # (100 + 100 + 0) / 3
    
    @pytest.mark.asyncio
    async def test_milestone_journey_with_artifacts(
        self,
        milestone_service,
        test_user,
        test_milestones,
        test_db_session
    ):
        """Test milestone journey with artifact creation."""
        user_id = str(test_user.id)
        
        # Initialize and complete M0 to get to M1
        await milestone_service.initialize_user_milestones(user_id)
        
        # Start and complete M0 quickly
        await milestone_service.start_milestone(user_id, "M0")
        await milestone_service.complete_milestone(
            user_id, "M0", {"viability_score": 0.8}, quality_score=0.85
        )
        
        # Start M1
        await milestone_service.start_milestone(user_id, "M1")
        
        # Complete M1 with artifacts
        m1_output = {
            "market_analysis_report": "Comprehensive analysis...",
            "competitive_landscape": {"competitors": ["A", "B", "C"]},
            "customer_segments": ["Segment 1", "Segment 2"]
        }
        
        await milestone_service.complete_milestone(
            user_id, "M1", m1_output, quality_score=0.92
        )
        
        # Create artifacts
        market_report_artifact = await milestone_service.create_milestone_artifact(
            user_id,
            "M1",
            "Market Analysis Report",
            "pdf",
            {
                "title": "Comprehensive Market Analysis",
                "sections": ["Executive Summary", "Market Sizing", "Competitive Analysis"],
                "page_count": 25,
                "content": m1_output
            },
            storage_path="/artifacts/market_analysis_report.pdf"
        )
        
        assert market_report_artifact is not None
        assert market_report_artifact.name == "Market Analysis Report"
        assert market_report_artifact.artifact_type == "pdf"
        
        # Create data artifact
        competitive_data_artifact = await milestone_service.create_milestone_artifact(
            user_id,
            "M1",
            "Competitive Analysis Data",
            "xlsx",
            {
                "competitor_data": m1_output["competitive_landscape"],
                "analysis_date": datetime.utcnow().isoformat(),
                "methodology": "Porter's Five Forces"
            },
            storage_path="/artifacts/competitive_analysis.xlsx"
        )
        
        assert competitive_data_artifact is not None
        
        # Verify artifacts can be retrieved
        user_artifacts = await milestone_service.get_user_artifacts(user_id, "M1")
        
        assert len(user_artifacts) == 2
        artifact_names = {a.name for a in user_artifacts}
        assert "Market Analysis Report" in artifact_names
        assert "Competitive Analysis Data" in artifact_names
        
        # Verify artifacts are associated with correct milestone
        for artifact in user_artifacts:
            assert artifact.user_milestone_id is not None
    
    @pytest.mark.asyncio
    async def test_milestone_journey_failure_and_recovery(
        self,
        milestone_service,
        test_user,
        test_milestones,
        test_db_session
    ):
        """Test milestone journey with failure and recovery."""
        user_id = str(test_user.id)
        
        # Initialize milestones
        await milestone_service.initialize_user_milestones(user_id)
        
        # Start M0
        await milestone_service.start_milestone(user_id, "M0")
        
        # Make some progress
        await milestone_service.update_milestone_progress(
            user_id, "M0", 1, {"partial_work": "Started but not complete"}
        )
        
        # Simulate failure
        failure_message = json.dumps({
            "error_type": "processing_timeout",
            "step_failed": 2,
            "partial_results": {"step_1": "completed"},
            "error_details": "Analysis took too long to process"
        })
        
        fail_success, fail_message = await milestone_service.fail_milestone(
            user_id, "M0", failure_message
        )
        
        assert fail_success is True
        assert "marked as failed" in fail_message
        
        # Verify failure is recorded
        from sqlalchemy import select
        stmt = select(UserMilestone).where(
            UserMilestone.user_id == test_user.id,
            UserMilestone.milestone_id == test_milestones["M0"].id
        )
        result = await test_db_session.execute(stmt)
        failed_milestone = result.scalar_one()
        
        assert failed_milestone.status == MilestoneStatus.FAILED
        assert failed_milestone.last_error == failure_message
        
        # Verify progress logs capture failure
        from sqlalchemy import select
        log_stmt = select(MilestoneProgressLog).where(
            MilestoneProgressLog.user_milestone_id == failed_milestone.id
        ).order_by(MilestoneProgressLog.created_at.desc())
        log_result = await test_db_session.execute(log_stmt)
        logs = log_result.scalars().all()
        
        assert len(logs) >= 3  # started, step_completed, failed
        latest_log = logs[0]
        assert latest_log.event_type == "failed"
        
        # Recovery: Restart the milestone
        restart_success, restart_message, restarted = await milestone_service.start_milestone(
            user_id, "M0"
        )
        
        assert restart_success is True
        assert restarted.status == MilestoneStatus.IN_PROGRESS
        assert restarted.processing_attempts == 2  # Second attempt
        
        # Complete successfully this time
        success, _, _ = await milestone_service.complete_milestone(
            user_id,
            "M0",
            {"viability_score": 0.82, "recovery": True},
            quality_score=0.87
        )
        
        assert success is True
        await test_db_session.refresh(restarted)
        assert restarted.status == MilestoneStatus.COMPLETED


class TestMilestoneWorkflowEdgeCases:
    """Test edge cases in milestone workflows."""
    
    @pytest.mark.asyncio
    async def test_concurrent_milestone_operations(
        self,
        milestone_service,
        test_user,
        test_milestones,
        test_db_session
    ):
        """Test concurrent operations on the same milestone."""
        user_id = str(test_user.id)
        
        # Initialize milestones
        await milestone_service.initialize_user_milestones(user_id)
        
        # Try to start the same milestone concurrently
        tasks = [
            milestone_service.start_milestone(user_id, "M0"),
            milestone_service.start_milestone(user_id, "M0"),
            milestone_service.start_milestone(user_id, "M0")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # At least one should succeed, others should handle gracefully
        successful_starts = sum(1 for r in results if isinstance(r, tuple) and r[0] is True)
        assert successful_starts >= 1
        
        # Verify only one milestone is actually in progress
        from sqlalchemy import select
        stmt = select(UserMilestone).where(
            UserMilestone.user_id == test_user.id,
            UserMilestone.milestone_id == test_milestones["M0"].id
        )
        result = await test_db_session.execute(stmt)
        user_milestone = result.scalar_one()
        
        assert user_milestone.status == MilestoneStatus.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_milestone_timeout_handling(
        self,
        milestone_service,
        test_user,
        test_milestones,
        test_db_session
    ):
        """Test handling of milestone processing timeouts."""
        user_id = str(test_user.id)
        
        # Initialize and start milestone
        await milestone_service.initialize_user_milestones(user_id)
        success, _, started = await milestone_service.start_milestone(user_id, "M0")
        assert success is True
        
        # Simulate long-running process by manually setting old start time
        started.started_at = datetime.utcnow() - timedelta(hours=2)
        test_db_session.add(started)
        await test_db_session.commit()
        
        # The milestone should be considered for timeout
        # In a real system, a background task would handle this
        time_spent = datetime.utcnow() - started.started_at
        assert time_spent.total_seconds() > 3600  # More than 1 hour
        
        # Simulate timeout handling
        timeout_error = {
            "error_type": "timeout",
            "time_elapsed": time_spent.total_seconds(),
            "max_allowed": 3600
        }
        
        await milestone_service.fail_milestone(
            user_id, "M0", json.dumps(timeout_error)
        )
        
        await test_db_session.refresh(started)
        assert started.status == MilestoneStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_milestone_data_integrity(
        self,
        milestone_service,
        test_user,
        test_milestones,
        test_db_session
    ):
        """Test data integrity during milestone operations."""
        user_id = str(test_user.id)
        
        # Initialize milestones
        await milestone_service.initialize_user_milestones(user_id)
        
        # Start milestone
        await milestone_service.start_milestone(user_id, "M0")
        
        # Make multiple progress updates
        progress_updates = [
            (1, {"step_1": "data_1"}),
            (2, {"step_2": "data_2", "combined": "data_1_and_2"})
        ]
        
        for step, data in progress_updates:
            await milestone_service.update_milestone_progress(user_id, "M0", step, data)
        
        # Verify all progress is recorded
        from sqlalchemy import select
        stmt = select(UserMilestone).where(
            UserMilestone.user_id == test_user.id,
            UserMilestone.milestone_id == test_milestones["M0"].id
        )
        result = await test_db_session.execute(stmt)
        milestone = result.scalar_one()
        
        assert milestone.current_step == 2
        assert milestone.checkpoint_data["step_1"] == "data_1"
        assert milestone.checkpoint_data["step_2"] == "data_2"
        assert milestone.checkpoint_data["combined"] == "data_1_and_2"
        
        # Verify progress logs
        log_stmt = select(MilestoneProgressLog).where(
            MilestoneProgressLog.user_milestone_id == milestone.id
        ).order_by(MilestoneProgressLog.created_at)
        log_result = await test_db_session.execute(log_stmt)
        logs = log_result.scalars().all()
        
        assert len(logs) >= 3  # started + 2 progress updates
        assert logs[0].event_type == "started"
        assert logs[1].event_type == "step_completed"
        assert logs[1].step_number == 1
        assert logs[2].event_type == "step_completed"
        assert logs[2].step_number == 2


class TestMilestoneDependencyWorkflows:
    """Test complex dependency workflows."""
    
    @pytest.mark.asyncio
    async def test_complex_dependency_chain_workflow(
        self,
        milestone_service,
        dependency_manager,
        test_user,
        test_db_session
    ):
        """Test workflow with complex dependency chain."""
        user_id = str(test_user.id)
        
        # Create extended milestone chain: M0 -> M1 -> M3 -> M4
        #                                        -> M2 -> M4
        milestones = {}
        
        for i, (code, name) in enumerate([
            ("M0", "Foundation"),
            ("M1", "Market Analysis"), 
            ("M2", "Business Model"),
            ("M3", "Financial Planning"),
            ("M4", "Launch Strategy")
        ]):
            milestone = Milestone(
                id=uuid4(),
                code=code,
                name=name,
                milestone_type=MilestoneType.PAID if i > 0 else MilestoneType.FREE,
                order_index=i,
                estimated_minutes=60,
                requires_payment=i > 0,
                is_active=True,
                prompt_template={"steps": [f"step_{i}_1", f"step_{i}_2"]}
            )
            milestones[code] = milestone
            test_db_session.add(milestone)
        
        await test_db_session.commit()
        
        # Create complex dependencies
        dependencies = [
            (milestones["M1"], milestones["M0"]),  # M1 depends on M0
            (milestones["M2"], milestones["M0"]),  # M2 depends on M0
            (milestones["M3"], milestones["M1"]),  # M3 depends on M1
            (milestones["M4"], milestones["M2"]),  # M4 depends on M2
            (milestones["M4"], milestones["M3"])   # M4 also depends on M3
        ]
        
        for milestone, dependency in dependencies:
            dep = MilestoneDependency(
                milestone_id=milestone.id,
                dependency_id=dependency.id,
                is_required=True,
                minimum_completion_percentage=100.0
            )
            test_db_session.add(dep)
        
        await test_db_session.commit()
        
        # Initialize user milestones
        await milestone_service.initialize_user_milestones(user_id)
        
        # Complete milestones in dependency order
        completion_order = ["M0", "M1", "M2", "M3", "M4"]
        
        for code in completion_order:
            # Start milestone
            success, message, _ = await milestone_service.start_milestone(user_id, code)
            
            if code == "M4":
                # M4 should only be available after M2 AND M3 are complete
                # At this point M3 should be completed, so M4 should start successfully
                assert success is True, f"M4 should start after M2 and M3 completion"
            else:
                assert success is True, f"Failed to start {code}: {message}"
            
            # Complete milestone
            output = {f"{code}_result": "completed", "timestamp": datetime.utcnow().isoformat()}
            complete_success, _, unlocked = await milestone_service.complete_milestone(
                user_id, code, output, quality_score=0.85
            )
            
            assert complete_success is True
            
            # Verify expected unlocking behavior
            if code == "M0":
                # Should unlock M1 and M2
                assert len(unlocked) >= 2
            elif code == "M3":
                # Should unlock M4 (since M2 is already complete)
                assert any(milestone_id for milestone_id in unlocked 
                          if milestones["M4"].id == milestone_id)
        
        # Verify final state
        user_analytics = await milestone_service.get_user_analytics(user_id)
        assert user_analytics["completed"] == 5
        assert user_analytics["completion_rate"] == 100.0
    
    @pytest.mark.asyncio
    async def test_dependency_validation_workflow(
        self,
        dependency_manager,
        milestone_service,
        test_user,
        test_milestones,
        test_db_session
    ):
        """Test dependency validation throughout workflow."""
        user_id = str(test_user.id)
        
        await milestone_service.initialize_user_milestones(user_id)
        
        # Test dependency validation at each stage
        
        # Stage 1: Initial state - only M0 should be available
        m0_valid, m0_unmet = await dependency_manager.validate_dependencies(
            user_id, str(test_milestones["M0"].id)
        )
        m1_valid, m1_unmet = await dependency_manager.validate_dependencies(
            user_id, str(test_milestones["M1"].id)
        )
        
        assert m0_valid is True
        assert m0_unmet == []
        assert m1_valid is False
        assert len(m1_unmet) > 0
        
        # Stage 2: After M0 completion - M1 and M2 should be available
        await milestone_service.start_milestone(user_id, "M0")
        await milestone_service.complete_milestone(
            user_id, "M0", {"viability_score": 0.8}
        )
        
        m1_valid_after, m1_unmet_after = await dependency_manager.validate_dependencies(
            user_id, str(test_milestones["M1"].id)
        )
        m2_valid_after, m2_unmet_after = await dependency_manager.validate_dependencies(
            user_id, str(test_milestones["M2"].id)
        )
        
        assert m1_valid_after is True
        assert m1_unmet_after == []
        assert m2_valid_after is True
        assert m2_unmet_after == []
        
        # Stage 3: Test bulk dependency validation
        all_milestone_ids = [str(m.id) for m in test_milestones.values()]
        bulk_results = await dependency_manager.bulk_validate_dependencies(
            user_id, all_milestone_ids
        )
        
        assert len(bulk_results) == 3
        assert bulk_results[str(test_milestones["M0"].id)]["all_met"] is True
        assert bulk_results[str(test_milestones["M1"].id)]["all_met"] is True
        assert bulk_results[str(test_milestones["M2"].id)]["all_met"] is True


class TestMilestoneCacheIntegration:
    """Test cache integration in workflows."""
    
    @pytest.mark.asyncio
    async def test_cache_consistency_during_workflow(
        self,
        milestone_service,
        milestone_cache_service,
        mock_redis_client,
        test_user,
        test_milestones
    ):
        """Test cache consistency throughout milestone workflow."""
        user_id = str(test_user.id)
        
        # Initialize milestones
        await milestone_service.initialize_user_milestones(user_id)
        
        # Verify cache is empty initially
        cached_progress = await milestone_cache_service.get_user_progress(user_id)
        assert cached_progress is None
        
        # Start milestone - should update cache
        success, _, started = await milestone_service.start_milestone(user_id, "M0")
        assert success is True
        
        # Check that progress update was published
        assert len(mock_redis_client._pub_sub_channels) > 0
        
        # Update progress - should update cache
        await milestone_service.update_milestone_progress(
            user_id, "M0", 1, {"step_1": "completed"}
        )
        
        # Complete milestone - should update cache and publish
        await milestone_service.complete_milestone(
            user_id, "M0", {"viability_score": 0.9}
        )
        
        # Verify cache invalidation was triggered
        # In the mock, cache operations should have been called
        cache_operations = [
            call for call in mock_redis_client._cache.keys()
            if user_id in call
        ]
        assert len(cache_operations) > 0
    
    @pytest.mark.asyncio
    async def test_milestone_tree_cache_updates(
        self,
        milestone_service,
        milestone_cache_service,
        test_user,
        test_milestones
    ):
        """Test milestone tree cache updates during workflow."""
        user_id = str(test_user.id)
        
        # Initialize milestones
        await milestone_service.initialize_user_milestones(user_id)
        
        # Get initial tree (should cache it)
        initial_tree = await milestone_service.get_user_milestone_tree_with_cache(user_id)
        
        assert initial_tree is not None
        assert initial_tree["completed_count"] == 0
        assert initial_tree["available_count"] == 1  # M0
        
        # Complete M0 - should invalidate tree cache
        await milestone_service.start_milestone(user_id, "M0")
        await milestone_service.complete_milestone(
            user_id, "M0", {"viability_score": 0.85}
        )
        
        # Get updated tree (should reflect changes)
        updated_tree = await milestone_service.get_user_milestone_tree_with_cache(user_id)
        
        assert updated_tree["completed_count"] == 1
        assert updated_tree["available_count"] >= 2  # M1 and M2 should be available
        assert updated_tree["total_progress"] > initial_tree["total_progress"]
    
    @pytest.mark.asyncio
    async def test_session_tracking_integration(
        self,
        milestone_service,
        milestone_cache_service,
        test_user,
        test_milestones
    ):
        """Test session tracking integration."""
        user_id = str(test_user.id)
        milestone_id = str(test_milestones["M0"].id)
        
        # Initialize and start milestone
        await milestone_service.initialize_user_milestones(user_id)
        await milestone_service.start_milestone(user_id, "M0")
        
        # Update progress multiple times (should track session activity)
        for step in [1, 2]:
            await milestone_service.update_milestone_progress(
                user_id, "M0", step, {f"step_{step}": "data"}
            )
            
            # Small delay to simulate user activity
            await asyncio.sleep(0.1)
        
        # Session activity should be tracked
        session_key = f"{milestone_cache_service.KEY_PREFIX_SESSION}{user_id}:{milestone_id}"
        # In integration test, we can't directly verify Redis operations,
        # but the session tracking calls should have been made


class TestMilestonePerformanceWorkflows:
    """Test performance aspects of milestone workflows."""
    
    @pytest.mark.asyncio
    async def test_high_volume_milestone_operations(
        self,
        milestone_service,
        test_db_session
    ):
        """Test milestone operations under high volume."""
        # Create multiple users
        users = []
        for i in range(10):
            user = User(
                id=uuid4(),
                email=f"user{i}@test.com",
                username=f"user_{i}",
                subscription_tier=SubscriptionTier.PREMIUM,
                is_active=True
            )
            users.append(user)
            test_db_session.add(user)
        
        await test_db_session.commit()
        
        # Create a milestone
        milestone = Milestone(
            id=uuid4(),
            code="PERF_TEST",
            name="Performance Test Milestone",
            milestone_type=MilestoneType.PAID,
            order_index=0,
            is_active=True,
            prompt_template={"steps": ["step1", "step2"]}
        )
        test_db_session.add(milestone)
        await test_db_session.commit()
        
        # Initialize milestones for all users concurrently
        init_tasks = [
            milestone_service.initialize_user_milestones(str(user.id))
            for user in users
        ]
        
        start_time = datetime.utcnow()
        init_results = await asyncio.gather(*init_tasks, return_exceptions=True)
        init_duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Verify all initializations succeeded
        successful_inits = sum(
            1 for result in init_results 
            if not isinstance(result, Exception)
        )
        assert successful_inits == len(users)
        assert init_duration < 5.0  # Should complete within 5 seconds
        
        # Start milestones for all users concurrently
        start_tasks = [
            milestone_service.start_milestone(str(user.id), "PERF_TEST")
            for user in users
        ]
        
        start_time = datetime.utcnow()
        start_results = await asyncio.gather(*start_tasks, return_exceptions=True)
        start_duration = (datetime.utcnow() - start_time).total_seconds()
        
        successful_starts = sum(
            1 for result in start_results 
            if not isinstance(result, Exception) and result[0] is True
        )
        assert successful_starts == len(users)
        assert start_duration < 10.0  # Should complete within 10 seconds
    
    @pytest.mark.asyncio
    async def test_concurrent_progress_updates(
        self,
        milestone_service,
        test_user,
        test_db_session
    ):
        """Test concurrent progress updates on the same milestone."""
        user_id = str(test_user.id)
        
        # Create milestone with multiple steps
        milestone = Milestone(
            id=uuid4(),
            code="CONCURRENT_TEST",
            name="Concurrent Test Milestone",
            milestone_type=MilestoneType.PAID,
            order_index=0,
            is_active=True,
            prompt_template={"steps": [f"step_{i}" for i in range(1, 11)]}  # 10 steps
        )
        test_db_session.add(milestone)
        await test_db_session.commit()
        
        # Initialize and start milestone
        await milestone_service.initialize_user_milestones(user_id)
        await milestone_service.start_milestone(user_id, "CONCURRENT_TEST")
        
        # Update progress concurrently (this tests race conditions)
        update_tasks = [
            milestone_service.update_milestone_progress(
                user_id, "CONCURRENT_TEST", i, {f"step_{i}": f"data_{i}"}
            )
            for i in range(1, 6)  # Update to step 1-5
        ]
        
        results = await asyncio.gather(*update_tasks, return_exceptions=True)
        
        # At least some updates should succeed (depending on race conditions)
        successful_updates = sum(
            1 for result in results
            if not isinstance(result, Exception) and result[0] is True
        )
        assert successful_updates > 0
        
        # Verify final state is consistent
        from sqlalchemy import select
        stmt = select(UserMilestone).where(
            UserMilestone.user_id == test_user.id,
            UserMilestone.milestone_id == milestone.id
        )
        result = await test_db_session.execute(stmt)
        final_milestone = result.scalar_one()
        
        # Should have some valid progress
        assert final_milestone.current_step > 0
        assert final_milestone.completion_percentage > 0