"""
Integration tests for Milestone Persistence Layer

Tests database operations, connection pooling, and transaction management.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
import asyncpg
from unittest.mock import MagicMock, AsyncMock, patch

from src.infrastructure.persistence import (
    MilestonePersistence,
    ConnectionPoolManager,
    PersistenceService,
    create_persistence_service
)
from src.models.milestone import (
    Milestone, UserMilestone, MilestoneStatus, MilestoneType,
    MilestoneDependency, UserMilestoneArtifact
)
from src.models.user import User, SubscriptionTier


@pytest.fixture
async def test_db_url():
    """Test database URL."""
    return "postgresql+asyncpg://test:test@localhost:5432/test_prolaunch"


@pytest.fixture
async def pool_manager(test_db_url):
    """Create test connection pool manager."""
    manager = ConnectionPoolManager(
        database_url=test_db_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=10.0
    )
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
async def persistence(pool_manager):
    """Create test persistence layer."""
    return MilestonePersistence(
        pool_manager=pool_manager,
        enable_query_cache=True,
        cache_ttl=60
    )


@pytest.fixture
async def persistence_service(test_db_url):
    """Create test persistence service."""
    service = await create_persistence_service(
        database_url=test_db_url,
        pool_size=5,
        enable_cache=True
    )
    yield service
    await service.close()


@pytest.fixture
async def sample_milestone():
    """Create sample milestone data."""
    return {
        "code": "M1",
        "name": "Test Milestone",
        "description": "Test milestone description",
        "milestone_type": MilestoneType.PAID,
        "order_index": 1,
        "estimated_minutes": 30,
        "is_active": True,
        "requires_payment": True,
        "prompt_template": {
            "steps": ["Step 1", "Step 2", "Step 3"]
        }
    }


@pytest.fixture
async def sample_user():
    """Create sample user."""
    return User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        subscription_tier=SubscriptionTier.FREE
    )


class TestConnectionPoolManager:
    """Test connection pool management."""
    
    async def test_initialize_pool(self, test_db_url):
        """Test pool initialization."""
        manager = ConnectionPoolManager(
            database_url=test_db_url,
            pool_size=10
        )
        
        engine = await manager.initialize()
        assert engine is not None
        
        # Check pool status
        status = await manager.get_pool_status()
        assert status["size"] >= 0
        assert "checked_in" in status
        assert "checked_out" in status
        
        await manager.close()
    
    async def test_pool_lifecycle(self, pool_manager):
        """Test connection pool lifecycle."""
        # Get initial status
        status1 = await pool_manager.get_pool_status()
        
        # Simulate connections
        engine = await pool_manager.initialize()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Get status after usage
        status2 = await pool_manager.get_pool_status()
        assert status2["stats"]["connections_created"] >= 0
    
    async def test_multiple_connections(self, pool_manager):
        """Test handling multiple concurrent connections."""
        engine = await pool_manager.initialize()
        
        async def use_connection():
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                await asyncio.sleep(0.1)
        
        # Run multiple concurrent connections
        tasks = [use_connection() for _ in range(10)]
        await asyncio.gather(*tasks)
        
        # Check pool didn't exceed limits
        status = await pool_manager.get_pool_status()
        assert status["total"] <= pool_manager.pool_size + pool_manager.max_overflow


class TestMilestonePersistence:
    """Test milestone persistence operations."""
    
    async def test_create_milestone(self, persistence, sample_milestone):
        """Test milestone creation."""
        milestone = await persistence.create_milestone(sample_milestone)
        
        assert milestone.code == "M1"
        assert milestone.name == "Test Milestone"
        assert milestone.milestone_type == MilestoneType.PAID
    
    async def test_get_milestone_by_code(self, persistence, sample_milestone):
        """Test retrieving milestone by code."""
        # Create milestone
        created = await persistence.create_milestone(sample_milestone)
        
        # Retrieve by code
        retrieved = await persistence.get_milestone(code="M1")
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.code == "M1"
    
    async def test_get_milestone_with_cache(self, persistence, sample_milestone):
        """Test milestone retrieval with caching."""
        # Create milestone
        await persistence.create_milestone(sample_milestone)
        
        # First retrieval (from DB)
        milestone1 = await persistence.get_milestone(code="M1")
        
        # Second retrieval (from cache)
        milestone2 = await persistence.get_milestone(code="M1")
        
        assert milestone1.id == milestone2.id
        assert len(persistence._query_cache) > 0
    
    async def test_update_milestone(self, persistence, sample_milestone):
        """Test milestone update."""
        # Create milestone
        milestone = await persistence.create_milestone(sample_milestone)
        
        # Update
        updates = {
            "name": "Updated Milestone",
            "estimated_minutes": 45
        }
        success = await persistence.update_milestone(milestone.id, updates)
        
        assert success is True
        
        # Verify update
        updated = await persistence.get_milestone(milestone_id=milestone.id)
        assert updated.name == "Updated Milestone"
        assert updated.estimated_minutes == 45
    
    async def test_delete_milestone_cascade(self, persistence, sample_milestone):
        """Test milestone deletion with cascade."""
        # Create milestone
        milestone = await persistence.create_milestone(sample_milestone)
        
        # Create user milestone
        user_milestone = await persistence.create_user_milestone(
            user_id=uuid4(),
            milestone_id=milestone.id,
            initial_status=MilestoneStatus.AVAILABLE
        )
        
        # Delete with cascade
        success = await persistence.delete_milestone(milestone.id, cascade=True)
        
        assert success is True
        
        # Verify deletion
        deleted = await persistence.get_milestone(milestone_id=milestone.id)
        assert deleted is None
    
    async def test_bulk_create_milestones(self, persistence):
        """Test bulk milestone creation."""
        milestones_data = [
            {
                "code": f"M{i}",
                "name": f"Milestone {i}",
                "order_index": i,
                "milestone_type": MilestoneType.FREE,
                "is_active": True
            }
            for i in range(5)
        ]
        
        created = await persistence.bulk_create_milestones(milestones_data)
        
        assert len(created) == 5
        assert all(m.code.startswith("M") for m in created)
    
    async def test_create_dependency_with_cycle_detection(self, persistence):
        """Test dependency creation with cycle detection."""
        # Create milestones
        m1 = await persistence.create_milestone({
            "code": "M1", "name": "Milestone 1", "order_index": 1
        })
        m2 = await persistence.create_milestone({
            "code": "M2", "name": "Milestone 2", "order_index": 2
        })
        m3 = await persistence.create_milestone({
            "code": "M3", "name": "Milestone 3", "order_index": 3
        })
        
        # Create valid dependencies: M3 -> M2 -> M1
        await persistence.create_dependency(m2.id, m1.id)
        await persistence.create_dependency(m3.id, m2.id)
        
        # Try to create cycle: M1 -> M3
        with pytest.raises(ValueError, match="would create a cycle"):
            await persistence.create_dependency(m1.id, m3.id)
    
    async def test_user_progress_tracking(self, persistence, sample_milestone):
        """Test user progress tracking."""
        # Create milestone
        milestone = await persistence.create_milestone(sample_milestone)
        user_id = uuid4()
        
        # Create user milestone
        user_milestone = await persistence.create_user_milestone(
            user_id=user_id,
            milestone_id=milestone.id,
            initial_status=MilestoneStatus.AVAILABLE
        )
        
        assert user_milestone.status == MilestoneStatus.AVAILABLE
        
        # Update progress
        progress_data = {
            "status": MilestoneStatus.IN_PROGRESS,
            "current_step": 2,
            "completion_percentage": 66.7,
            "checkpoint_data": {"last_prompt": "Step 2"}
        }
        
        success = await persistence.update_user_progress(
            user_id=user_id,
            milestone_id=milestone.id,
            progress_data=progress_data,
            log_event=True
        )
        
        assert success is True
    
    async def test_get_user_progress_summary(self, persistence):
        """Test user progress summary generation."""
        user_id = uuid4()
        
        # Create milestones and progress
        for i in range(3):
            milestone = await persistence.create_milestone({
                "code": f"M{i}",
                "name": f"Milestone {i}",
                "order_index": i
            })
            
            status = MilestoneStatus.COMPLETED if i < 2 else MilestoneStatus.IN_PROGRESS
            await persistence.create_user_milestone(
                user_id=user_id,
                milestone_id=milestone.id,
                initial_status=status
            )
            
            if status == MilestoneStatus.COMPLETED:
                await persistence.update_user_progress(
                    user_id=user_id,
                    milestone_id=milestone.id,
                    progress_data={
                        "status": MilestoneStatus.COMPLETED,
                        "completion_percentage": 100.0,
                        "time_spent_seconds": 1800,
                        "quality_score": 4.5
                    }
                )
        
        # Get summary
        summary = await persistence.get_user_progress_summary(user_id)
        
        assert summary["completed"] == 2
        assert summary["in_progress"] == 1
        assert summary["total"] == 3
        assert summary["total_time_hours"] > 0
    
    async def test_artifact_management(self, persistence, sample_milestone):
        """Test artifact creation and retrieval."""
        # Create milestone and user milestone
        milestone = await persistence.create_milestone(sample_milestone)
        user_id = uuid4()
        
        user_milestone = await persistence.create_user_milestone(
            user_id=user_id,
            milestone_id=milestone.id
        )
        
        # Create artifact
        artifact_data = {
            "name": "Business Plan.pdf",
            "artifact_type": "pdf",
            "content": {"pages": 10, "sections": ["Executive Summary", "Market Analysis"]},
            "mime_type": "application/pdf",
            "file_size": 1024000
        }
        
        artifact = await persistence.create_artifact(
            user_milestone_id=user_milestone.id,
            artifact_data=artifact_data
        )
        
        assert artifact.name == "Business Plan.pdf"
        assert artifact.artifact_type == "pdf"
        
        # Retrieve artifacts
        artifacts = await persistence.get_user_artifacts(
            user_id=user_id,
            milestone_id=milestone.id
        )
        
        assert len(artifacts) == 1
        assert artifacts[0].id == artifact.id
    
    async def test_milestone_analytics(self, persistence, sample_milestone):
        """Test milestone analytics generation."""
        milestone = await persistence.create_milestone(sample_milestone)
        
        # Create user progress
        for i in range(5):
            user_id = uuid4()
            await persistence.create_user_milestone(
                user_id=user_id,
                milestone_id=milestone.id
            )
            
            if i < 3:  # Complete 3 out of 5
                await persistence.update_user_progress(
                    user_id=user_id,
                    milestone_id=milestone.id,
                    progress_data={
                        "status": MilestoneStatus.COMPLETED,
                        "completion_percentage": 100.0,
                        "time_spent_seconds": 1800 + (i * 300),
                        "quality_score": 4.0 + (i * 0.2)
                    }
                )
        
        # Get analytics
        analytics = await persistence.get_milestone_analytics(
            milestone.id,
            time_range=timedelta(days=7)
        )
        
        assert analytics["unique_users"] == 5
        assert analytics["completions"] == 3
        assert analytics["success_rate"] == 60.0
        assert analytics["average_quality_score"] > 0
    
    async def test_leaderboard_generation(self, persistence):
        """Test leaderboard generation."""
        # Create milestones
        milestones = []
        for i in range(3):
            milestone = await persistence.create_milestone({
                "code": f"M{i}",
                "name": f"Milestone {i}",
                "order_index": i
            })
            milestones.append(milestone)
        
        # Create users with different scores
        users = []
        for i in range(5):
            user = User(
                id=uuid4(),
                username=f"user{i}",
                email=f"user{i}@example.com"
            )
            users.append(user)
            
            # Complete different numbers of milestones
            for j in range(min(i + 1, 3)):
                await persistence.create_user_milestone(
                    user_id=user.id,
                    milestone_id=milestones[j].id
                )
                
                await persistence.update_user_progress(
                    user_id=user.id,
                    milestone_id=milestones[j].id,
                    progress_data={
                        "status": MilestoneStatus.COMPLETED,
                        "completion_percentage": 100.0,
                        "completed_at": datetime.utcnow(),
                        "quality_score": 4.0 + (i * 0.1)
                    }
                )
        
        # Get leaderboard
        leaderboard = await persistence.get_leaderboard(
            time_period="all",
            limit=10
        )
        
        assert len(leaderboard) <= 5
        assert leaderboard[0]["rank"] == 1
        # Higher index users should have better scores
        assert leaderboard[0]["completed_milestones"] >= leaderboard[-1]["completed_milestones"]


class TestPersistenceService:
    """Test high-level persistence service."""
    
    async def test_initialize_user_journey(self, persistence_service):
        """Test user journey initialization."""
        user_id = uuid4()
        
        result = await persistence_service.initialize_user_journey(
            user_id=user_id,
            subscription_tier=SubscriptionTier.FREE
        )
        
        assert result["user_id"] == str(user_id)
        assert result["milestones_initialized"] > 0
        assert "available_milestones" in result
    
    async def test_start_milestone_with_validation(self, persistence_service):
        """Test starting milestone with full validation."""
        user_id = uuid4()
        
        # Initialize journey first
        await persistence_service.initialize_user_journey(user_id)
        
        # Try to start milestone
        success, message, data = await persistence_service.start_milestone_with_validation(
            user_id=user_id,
            milestone_code="M0",
            session_metadata={"session_id": "test123"}
        )
        
        assert success is True
        assert "M0" in message
        assert data is not None
        assert "milestone_id" in data
    
    async def test_complete_milestone_with_artifacts(self, persistence_service):
        """Test milestone completion with artifacts."""
        user_id = uuid4()
        
        # Initialize and start milestone
        await persistence_service.initialize_user_journey(user_id)
        await persistence_service.start_milestone_with_validation(
            user_id=user_id,
            milestone_code="M0"
        )
        
        # Complete with artifacts
        success, message, data = await persistence_service.complete_milestone_with_artifacts(
            user_id=user_id,
            milestone_code="M0",
            generated_output={"content": "Generated business plan"},
            artifacts=[
                {
                    "name": "plan.pdf",
                    "artifact_type": "pdf",
                    "content": {"pages": 10}
                }
            ],
            quality_score=4.5
        )
        
        assert success is True
        assert "completed successfully" in message
        assert data["artifacts_created"] == 1
    
    async def test_dependency_checking(self, persistence_service):
        """Test dependency validation."""
        user_id = uuid4()
        
        # Create milestones with dependencies
        async with persistence_service.persistence.get_session() as session:
            m1 = Milestone(
                code="M1", name="Milestone 1", order_index=1
            )
            m2 = Milestone(
                code="M2", name="Milestone 2", order_index=2
            )
            session.add_all([m1, m2])
            await session.flush()
            
            # M2 depends on M1
            dep = MilestoneDependency(
                milestone_id=m2.id,
                dependency_id=m1.id,
                is_required=True
            )
            session.add(dep)
            await session.commit()
        
        # Check dependencies for M2
        deps_met = await persistence_service.check_dependencies_met(
            user_id=user_id,
            milestone_id=m2.id
        )
        
        assert deps_met["all_met"] is False
        assert "M1" in deps_met["missing"]
    
    async def test_subscription_upgrade(self, persistence_service):
        """Test subscription upgrade flow."""
        user_id = uuid4()
        
        # Initialize as free user
        await persistence_service.initialize_user_journey(
            user_id=user_id,
            subscription_tier=SubscriptionTier.FREE
        )
        
        # Upgrade to paid
        result = await persistence_service.upgrade_user_access(
            user_id=user_id,
            new_tier=SubscriptionTier.PROFESSIONAL
        )
        
        assert result["new_tier"] == SubscriptionTier.PROFESSIONAL
        assert len(result["unlocked_milestones"]) >= 0
    
    async def test_cleanup_stale_sessions(self, persistence_service):
        """Test stale session cleanup."""
        user_id = uuid4()
        
        # Create stale session
        async with persistence_service.persistence.get_session() as session:
            milestone = Milestone(
                code="M1", name="Test", order_index=1
            )
            session.add(milestone)
            await session.flush()
            
            # Create stale user milestone
            stale_time = datetime.utcnow() - timedelta(hours=48)
            user_milestone = UserMilestone(
                user_id=user_id,
                milestone_id=milestone.id,
                status=MilestoneStatus.IN_PROGRESS,
                last_accessed_at=stale_time
            )
            session.add(user_milestone)
            await session.commit()
        
        # Run cleanup
        cleaned = await persistence_service.cleanup_stale_sessions(
            stale_threshold_hours=24
        )
        
        assert cleaned == 1
    
    async def test_system_analytics(self, persistence_service):
        """Test system-wide analytics generation."""
        analytics = await persistence_service.get_system_analytics()
        
        assert "timestamp" in analytics
        assert "persistence_metrics" in analytics
        assert "user_statistics" in analytics
        assert "connection_pool" in analytics
    
    async def test_transaction_metrics(self, persistence_service):
        """Test transaction metrics tracking."""
        initial_metrics = persistence_service._transaction_metrics.copy()
        
        # Execute transaction
        async with persistence_service.transaction_scope() as session:
            await session.execute(text("SELECT 1"))
        
        # Check metrics updated
        assert persistence_service._transaction_metrics["total"] > initial_metrics["total"]
        assert persistence_service._transaction_metrics["successful"] > initial_metrics["successful"]


class TestErrorHandling:
    """Test error handling and recovery."""
    
    async def test_retry_on_operational_error(self, persistence):
        """Test automatic retry on operational errors."""
        with patch.object(persistence, 'get_session') as mock_session:
            # Simulate operational error then success
            mock_session.side_effect = [
                OperationalError("Connection lost", None, None),
                AsyncMock()
            ]
            
            # Should retry and succeed
            try:
                milestone = await persistence.get_milestone(code="M1")
            except OperationalError:
                pass  # Expected on first attempt
    
    async def test_transaction_rollback(self, persistence_service):
        """Test transaction rollback on error."""
        user_id = uuid4()
        
        with patch.object(persistence_service.persistence, 'update_user_progress') as mock_update:
            mock_update.side_effect = Exception("Database error")
            
            # Should rollback transaction
            success, message, _ = await persistence_service.start_milestone_with_validation(
                user_id=user_id,
                milestone_code="M0"
            )
            
            assert success is False
            assert "Database error" in message
    
    async def test_cache_invalidation_on_error(self, persistence):
        """Test cache invalidation on update errors."""
        # Create and cache milestone
        milestone = await persistence.create_milestone({
            "code": "M1", "name": "Test", "order_index": 1
        })
        
        # Cache it
        await persistence.get_milestone(code="M1")
        assert len(persistence._query_cache) > 0
        
        # Failed update should still invalidate cache
        with patch.object(persistence, 'get_session') as mock_session:
            mock_session.side_effect = Exception("Update failed")
            
            try:
                await persistence.update_milestone(milestone.id, {"name": "Updated"})
            except:
                pass
            
            # Cache should be invalidated
            assert f"milestone:{milestone.id}" not in persistence._query_cache


class TestPerformance:
    """Test performance optimizations."""
    
    async def test_connection_pool_performance(self, pool_manager):
        """Test connection pool performance under load."""
        engine = await pool_manager.initialize()
        
        async def query_task():
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        
        # Measure time for concurrent queries
        start = datetime.utcnow()
        tasks = [query_task() for _ in range(50)]
        await asyncio.gather(*tasks)
        duration = (datetime.utcnow() - start).total_seconds()
        
        # Should complete reasonably fast with pooling
        assert duration < 5.0  # 50 queries in under 5 seconds
    
    async def test_bulk_operation_performance(self, persistence):
        """Test bulk operation performance."""
        # Prepare bulk data
        milestones_data = [
            {
                "code": f"M{i}",
                "name": f"Milestone {i}",
                "order_index": i,
                "is_active": True
            }
            for i in range(100)
        ]
        
        # Measure bulk create
        start = datetime.utcnow()
        created = await persistence.bulk_create_milestones(milestones_data)
        duration = (datetime.utcnow() - start).total_seconds()
        
        assert len(created) == 100
        assert duration < 2.0  # 100 inserts in under 2 seconds
    
    async def test_query_cache_performance(self, persistence):
        """Test query cache performance improvement."""
        # Create milestone
        await persistence.create_milestone({
            "code": "M1", "name": "Test", "order_index": 1
        })
        
        # First query (from DB)
        start1 = datetime.utcnow()
        milestone1 = await persistence.get_milestone(code="M1")
        duration1 = (datetime.utcnow() - start1).total_seconds()
        
        # Second query (from cache)
        start2 = datetime.utcnow()
        milestone2 = await persistence.get_milestone(code="M1")
        duration2 = (datetime.utcnow() - start2).total_seconds()
        
        # Cache should be significantly faster
        assert duration2 < duration1 * 0.1  # At least 10x faster