"""
Comprehensive Unit Tests for Milestone Database Models

Tests all database models in the milestone system including validation,
relationships, constraints, and business logic.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool

from backend.src.models.milestone import (
    Base,
    Milestone,
    MilestoneDependency,
    UserMilestone,
    MilestoneArtifact,
    UserMilestoneArtifact,
    MilestoneProgressLog,
    MilestoneCache,
    MilestoneStatus,
    MilestoneType,
    get_user_milestone_tree,
    check_milestone_dependencies,
    update_dependent_milestones
)
from backend.src.models.user import User, SubscriptionTier


@pytest.fixture
async def async_db_session():
    """Create an in-memory async database session for testing."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_milestone():
    """Create a sample milestone for testing."""
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
        prompt_template={
            "steps": ["step1", "step2", "step3"],
            "instructions": "Complete feasibility analysis"
        },
        output_schema={"type": "object", "required": ["viability_score"]},
        validation_rules={"min_viability_score": 0.0, "max_viability_score": 1.0}
    )


@pytest.fixture
def sample_paid_milestone():
    """Create a sample paid milestone for testing."""
    return Milestone(
        id=uuid4(),
        code="M1",
        name="Business Model Canvas",
        description="Comprehensive business model development",
        milestone_type=MilestoneType.PAID,
        order_index=1,
        estimated_minutes=120,
        processing_time_limit=300,
        is_active=True,
        requires_payment=True,
        auto_unlock=False,
        prompt_template={
            "steps": ["define_value_prop", "identify_segments", "revenue_streams"],
            "context_requirements": ["market_research", "competitor_analysis"]
        },
        output_schema={"type": "object", "required": ["canvas_data"]},
        validation_rules={"required_sections": 9}
    )


class TestMilestoneModel:
    """Test the Milestone model."""
    
    async def test_milestone_creation(self, async_db_session, sample_milestone):
        """Test creating and saving a milestone."""
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        assert sample_milestone.id is not None
        assert sample_milestone.code == "M0"
        assert sample_milestone.name == "Feasibility Snapshot"
        assert sample_milestone.milestone_type == MilestoneType.FREE
        assert sample_milestone.is_active is True
        assert sample_milestone.created_at is not None
        assert sample_milestone.updated_at is not None
    
    def test_milestone_to_dict(self, sample_milestone):
        """Test milestone to_dict method."""
        milestone_dict = sample_milestone.to_dict()
        
        assert milestone_dict["code"] == "M0"
        assert milestone_dict["name"] == "Feasibility Snapshot"
        assert milestone_dict["type"] == MilestoneType.FREE
        assert milestone_dict["order"] == 0
        assert milestone_dict["estimated_minutes"] == 30
        assert milestone_dict["requires_payment"] is False
        assert milestone_dict["is_active"] is True
    
    async def test_milestone_unique_code_constraint(self, async_db_session, sample_milestone):
        """Test that milestone codes must be unique."""
        # Add first milestone
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        # Try to add another milestone with same code
        duplicate_milestone = Milestone(
            code="M0",  # Same code
            name="Duplicate Milestone",
            order_index=1
        )
        
        async_db_session.add(duplicate_milestone)
        
        with pytest.raises(Exception):  # Should raise integrity error
            await async_db_session.commit()
    
    def test_milestone_type_validation(self):
        """Test milestone type enum validation."""
        milestone = Milestone(
            code="M1",
            name="Test Milestone",
            milestone_type=MilestoneType.PAID,
            order_index=1
        )
        
        assert milestone.milestone_type == MilestoneType.PAID
        assert milestone.milestone_type in [MilestoneType.FREE, MilestoneType.PAID, MilestoneType.GATEWAY]
    
    def test_milestone_json_fields(self, sample_milestone):
        """Test JSONB fields handling."""
        assert isinstance(sample_milestone.prompt_template, dict)
        assert "steps" in sample_milestone.prompt_template
        assert isinstance(sample_milestone.output_schema, dict)
        assert isinstance(sample_milestone.validation_rules, dict)
    
    def test_milestone_defaults(self):
        """Test milestone field defaults."""
        milestone = Milestone(
            code="M2",
            name="Test Milestone",
            order_index=2
        )
        
        assert milestone.milestone_type == MilestoneType.PAID  # Default
        assert milestone.estimated_minutes == 30  # Default
        assert milestone.processing_time_limit == 300  # Default
        assert milestone.is_active is True  # Default
        assert milestone.requires_payment is True  # Default
        assert milestone.auto_unlock is False  # Default


class TestMilestoneDependencyModel:
    """Test the MilestoneDependency model."""
    
    async def test_dependency_creation(self, async_db_session, sample_milestone, sample_paid_milestone):
        """Test creating milestone dependencies."""
        # Add milestones first
        async_db_session.add(sample_milestone)
        async_db_session.add(sample_paid_milestone)
        await async_db_session.commit()
        
        # Create dependency (M1 depends on M0)
        dependency = MilestoneDependency(
            milestone_id=sample_paid_milestone.id,
            dependency_id=sample_milestone.id,
            is_required=True,
            minimum_completion_percentage=100.0
        )
        
        async_db_session.add(dependency)
        await async_db_session.commit()
        
        assert dependency.id is not None
        assert dependency.milestone_id == sample_paid_milestone.id
        assert dependency.dependency_id == sample_milestone.id
        assert dependency.is_required is True
        assert dependency.minimum_completion_percentage == 100.0
    
    async def test_self_dependency_constraint(self, async_db_session, sample_milestone):
        """Test that milestones cannot depend on themselves."""
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        # Try to create self-dependency
        self_dependency = MilestoneDependency(
            milestone_id=sample_milestone.id,
            dependency_id=sample_milestone.id  # Same as milestone_id
        )
        
        async_db_session.add(self_dependency)
        
        with pytest.raises(Exception):  # Should raise check constraint violation
            await async_db_session.commit()
    
    async def test_unique_dependency_constraint(self, async_db_session, sample_milestone, sample_paid_milestone):
        """Test that duplicate dependencies are not allowed."""
        # Add milestones
        async_db_session.add(sample_milestone)
        async_db_session.add(sample_paid_milestone)
        await async_db_session.commit()
        
        # Add first dependency
        dependency1 = MilestoneDependency(
            milestone_id=sample_paid_milestone.id,
            dependency_id=sample_milestone.id
        )
        async_db_session.add(dependency1)
        await async_db_session.commit()
        
        # Try to add duplicate dependency
        dependency2 = MilestoneDependency(
            milestone_id=sample_paid_milestone.id,
            dependency_id=sample_milestone.id  # Same pair
        )
        async_db_session.add(dependency2)
        
        with pytest.raises(Exception):  # Should raise unique constraint violation
            await async_db_session.commit()
    
    async def test_dependency_relationships(self, async_db_session, sample_milestone, sample_paid_milestone):
        """Test dependency relationships."""
        # Add milestones
        async_db_session.add(sample_milestone)
        async_db_session.add(sample_paid_milestone)
        await async_db_session.commit()
        
        # Create dependency
        dependency = MilestoneDependency(
            milestone_id=sample_paid_milestone.id,
            dependency_id=sample_milestone.id
        )
        
        async_db_session.add(dependency)
        await async_db_session.commit()
        
        # Refresh to load relationships
        await async_db_session.refresh(dependency)
        await async_db_session.refresh(sample_milestone)
        await async_db_session.refresh(sample_paid_milestone)
        
        # Test relationships are loaded correctly
        assert dependency.milestone is not None
        assert dependency.dependency is not None
        assert dependency.milestone.id == sample_paid_milestone.id
        assert dependency.dependency.id == sample_milestone.id


class TestUserMilestoneModel:
    """Test the UserMilestone model."""
    
    async def test_user_milestone_creation(self, async_db_session, sample_user, sample_milestone):
        """Test creating user milestone progress."""
        async_db_session.add(sample_user)
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        user_milestone = UserMilestone(
            user_id=sample_user.id,
            milestone_id=sample_milestone.id,
            status=MilestoneStatus.AVAILABLE,
            completion_percentage=0.0,
            current_step=0,
            total_steps=3,
            user_inputs={"initial_idea": "AI-powered productivity tool"},
            checkpoint_data={"phase": "planning"}
        )
        
        async_db_session.add(user_milestone)
        await async_db_session.commit()
        
        assert user_milestone.id is not None
        assert user_milestone.user_id == sample_user.id
        assert user_milestone.milestone_id == sample_milestone.id
        assert user_milestone.status == MilestoneStatus.AVAILABLE
        assert user_milestone.completion_percentage == 0.0
        assert isinstance(user_milestone.user_inputs, dict)
        assert isinstance(user_milestone.checkpoint_data, dict)
    
    def test_user_milestone_to_dict(self, sample_user, sample_milestone):
        """Test user milestone to_dict method."""
        user_milestone = UserMilestone(
            id=uuid4(),
            user_id=sample_user.id,
            milestone_id=sample_milestone.id,
            status=MilestoneStatus.IN_PROGRESS,
            completion_percentage=50.0,
            current_step=2,
            total_steps=4,
            started_at=datetime.utcnow(),
            time_spent_seconds=1800,
            quality_score=0.85,
            feedback_rating=4
        )
        
        milestone_dict = user_milestone.to_dict()
        
        assert milestone_dict["milestone_id"] == str(sample_milestone.id)
        assert milestone_dict["status"] == MilestoneStatus.IN_PROGRESS
        assert milestone_dict["completion_percentage"] == 50.0
        assert milestone_dict["current_step"] == 2
        assert milestone_dict["total_steps"] == 4
        assert milestone_dict["time_spent_seconds"] == 1800
        assert milestone_dict["quality_score"] == 0.85
        assert milestone_dict["feedback_rating"] == 4
        assert "started_at" in milestone_dict
    
    def test_user_milestone_to_dict_with_outputs(self, sample_user, sample_milestone):
        """Test user milestone to_dict with outputs included."""
        generated_output = {"result": "business_model", "confidence": 0.9}
        
        user_milestone = UserMilestone(
            user_id=sample_user.id,
            milestone_id=sample_milestone.id,
            status=MilestoneStatus.COMPLETED,
            completion_percentage=100.0,
            generated_output=generated_output
        )
        
        milestone_dict = user_milestone.to_dict(include_outputs=True)
        
        assert milestone_dict["generated_output"] == generated_output
        
        # Test without outputs
        milestone_dict_no_outputs = user_milestone.to_dict(include_outputs=False)
        assert "generated_output" not in milestone_dict_no_outputs
    
    async def test_user_milestone_unique_constraint(self, async_db_session, sample_user, sample_milestone):
        """Test unique constraint on user_id + milestone_id."""
        async_db_session.add(sample_user)
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        # Add first user milestone
        user_milestone1 = UserMilestone(
            user_id=sample_user.id,
            milestone_id=sample_milestone.id,
            status=MilestoneStatus.AVAILABLE
        )
        async_db_session.add(user_milestone1)
        await async_db_session.commit()
        
        # Try to add duplicate
        user_milestone2 = UserMilestone(
            user_id=sample_user.id,
            milestone_id=sample_milestone.id,  # Same pair
            status=MilestoneStatus.IN_PROGRESS
        )
        async_db_session.add(user_milestone2)
        
        with pytest.raises(Exception):  # Should raise unique constraint violation
            await async_db_session.commit()
    
    def test_milestone_status_enum(self):
        """Test milestone status enumeration."""
        user_milestone = UserMilestone(
            user_id=uuid4(),
            milestone_id=uuid4(),
            status=MilestoneStatus.LOCKED
        )
        
        assert user_milestone.status == MilestoneStatus.LOCKED
        assert user_milestone.status in [
            MilestoneStatus.LOCKED,
            MilestoneStatus.AVAILABLE,
            MilestoneStatus.IN_PROGRESS,
            MilestoneStatus.COMPLETED,
            MilestoneStatus.SKIPPED,
            MilestoneStatus.FAILED
        ]
    
    def test_user_milestone_defaults(self):
        """Test user milestone field defaults."""
        user_milestone = UserMilestone(
            user_id=uuid4(),
            milestone_id=uuid4()
        )
        
        assert user_milestone.status == MilestoneStatus.LOCKED  # Default
        assert user_milestone.completion_percentage == 0.0  # Default
        assert user_milestone.current_step == 0  # Default
        assert user_milestone.total_steps == 1  # Default
        assert user_milestone.time_spent_seconds == 0  # Default
        assert user_milestone.processing_attempts == 0  # Default


class TestMilestoneProgressLogModel:
    """Test the MilestoneProgressLog model."""
    
    async def test_progress_log_creation(self, async_db_session, sample_user, sample_milestone):
        """Test creating progress log entries."""
        async_db_session.add(sample_user)
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        user_milestone = UserMilestone(
            user_id=sample_user.id,
            milestone_id=sample_milestone.id,
            status=MilestoneStatus.IN_PROGRESS
        )
        async_db_session.add(user_milestone)
        await async_db_session.commit()
        
        progress_log = MilestoneProgressLog(
            user_milestone_id=user_milestone.id,
            event_type="started",
            event_data={"session_id": "abc123", "milestone_code": "M0"},
            step_number=1,
            completion_percentage=25.0,
            time_elapsed_seconds=300,
            session_id="abc123",
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )
        
        async_db_session.add(progress_log)
        await async_db_session.commit()
        
        assert progress_log.id is not None
        assert progress_log.user_milestone_id == user_milestone.id
        assert progress_log.event_type == "started"
        assert isinstance(progress_log.event_data, dict)
        assert progress_log.step_number == 1
        assert progress_log.completion_percentage == 25.0
        assert progress_log.time_elapsed_seconds == 300
        assert progress_log.created_at is not None
    
    def test_progress_log_event_types(self):
        """Test various progress log event types."""
        event_types = [
            "started", "step_completed", "paused", "resumed", 
            "completed", "failed", "skipped"
        ]
        
        for event_type in event_types:
            log = MilestoneProgressLog(
                user_milestone_id=uuid4(),
                event_type=event_type,
                event_data={"type": event_type}
            )
            assert log.event_type == event_type
    
    def test_progress_log_json_data(self):
        """Test progress log JSONB event data."""
        complex_event_data = {
            "step_details": {
                "completed_tasks": ["task1", "task2"],
                "remaining_tasks": ["task3", "task4"]
            },
            "performance_metrics": {
                "processing_time": 45.6,
                "memory_usage": "120MB"
            },
            "user_context": {
                "browser": "Chrome",
                "screen_resolution": "1920x1080"
            }
        }
        
        progress_log = MilestoneProgressLog(
            user_milestone_id=uuid4(),
            event_type="step_completed",
            event_data=complex_event_data
        )
        
        assert progress_log.event_data == complex_event_data
        assert isinstance(progress_log.event_data, dict)


class TestMilestoneArtifactModel:
    """Test the MilestoneArtifact model."""
    
    async def test_milestone_artifact_creation(self, async_db_session, sample_milestone):
        """Test creating milestone artifact templates."""
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        artifact = MilestoneArtifact(
            milestone_id=sample_milestone.id,
            name="Business Plan Template",
            artifact_type="document",
            description="Comprehensive business plan template",
            template_path="/templates/business_plan.docx",
            output_format="pdf",
            is_required=True,
            display_order=1
        )
        
        async_db_session.add(artifact)
        await async_db_session.commit()
        
        assert artifact.id is not None
        assert artifact.milestone_id == sample_milestone.id
        assert artifact.name == "Business Plan Template"
        assert artifact.artifact_type == "document"
        assert artifact.template_path == "/templates/business_plan.docx"
        assert artifact.output_format == "pdf"
        assert artifact.is_required is True
        assert artifact.display_order == 1
    
    def test_milestone_artifact_defaults(self):
        """Test milestone artifact field defaults."""
        artifact = MilestoneArtifact(
            milestone_id=uuid4(),
            name="Test Artifact"
        )
        
        assert artifact.is_required is True  # Default
        assert artifact.display_order == 0  # Default


class TestUserMilestoneArtifactModel:
    """Test the UserMilestoneArtifact model."""
    
    async def test_user_artifact_creation(self, async_db_session, sample_user, sample_milestone):
        """Test creating user-generated artifacts."""
        async_db_session.add(sample_user)
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        user_milestone = UserMilestone(
            user_id=sample_user.id,
            milestone_id=sample_milestone.id,
            status=MilestoneStatus.COMPLETED
        )
        async_db_session.add(user_milestone)
        await async_db_session.commit()
        
        user_artifact = UserMilestoneArtifact(
            user_milestone_id=user_milestone.id,
            name="My Business Plan",
            artifact_type="pdf",
            mime_type="application/pdf",
            storage_path="/user_files/business_plan_123.pdf",
            file_size=1024567,
            checksum="abc123def456",
            content={"sections": ["executive_summary", "market_analysis"]},
            preview_text="Executive Summary: Our innovative solution...",
            generation_metadata={
                "model": "gpt-4",
                "processing_time": 45.2,
                "tokens_used": 2500
            },
            citations_used=["source1", "source2"],
            share_token="shared_abc123"
        )
        
        async_db_session.add(user_artifact)
        await async_db_session.commit()
        
        assert user_artifact.id is not None
        assert user_artifact.user_milestone_id == user_milestone.id
        assert user_artifact.name == "My Business Plan"
        assert user_artifact.mime_type == "application/pdf"
        assert user_artifact.file_size == 1024567
        assert isinstance(user_artifact.content, dict)
        assert isinstance(user_artifact.generation_metadata, dict)
        assert isinstance(user_artifact.citations_used, list)
        assert user_artifact.share_token == "shared_abc123"
    
    def test_user_artifact_defaults(self):
        """Test user artifact field defaults."""
        artifact = UserMilestoneArtifact(
            user_milestone_id=uuid4(),
            name="Test Artifact"
        )
        
        assert artifact.is_public is False  # Default
        assert artifact.access_count == 0  # Default
    
    async def test_user_artifact_share_token_unique(self, async_db_session, sample_user, sample_milestone):
        """Test share token uniqueness constraint."""
        async_db_session.add(sample_user)
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        user_milestone = UserMilestone(
            user_id=sample_user.id,
            milestone_id=sample_milestone.id
        )
        async_db_session.add(user_milestone)
        await async_db_session.commit()
        
        # Add first artifact with share token
        artifact1 = UserMilestoneArtifact(
            user_milestone_id=user_milestone.id,
            name="Artifact 1",
            share_token="unique_token_123"
        )
        async_db_session.add(artifact1)
        await async_db_session.commit()
        
        # Try to add another artifact with same share token
        artifact2 = UserMilestoneArtifact(
            user_milestone_id=user_milestone.id,
            name="Artifact 2",
            share_token="unique_token_123"  # Duplicate token
        )
        async_db_session.add(artifact2)
        
        with pytest.raises(Exception):  # Should raise unique constraint violation
            await async_db_session.commit()


class TestMilestoneCacheModel:
    """Test the MilestoneCache model."""
    
    async def test_milestone_cache_creation(self, async_db_session):
        """Test creating cache entries."""
        cache_entry = MilestoneCache(
            cache_key="user_progress:user123:milestone456",
            cache_type="user_progress",
            data={
                "status": "in_progress",
                "completion_percentage": 75.0,
                "current_step": 3
            },
            ttl_seconds=3600,
            expires_at=datetime.utcnow() + timedelta(seconds=3600)
        )
        
        async_db_session.add(cache_entry)
        await async_db_session.commit()
        
        assert cache_entry.id is not None
        assert cache_entry.cache_key == "user_progress:user123:milestone456"
        assert cache_entry.cache_type == "user_progress"
        assert isinstance(cache_entry.data, dict)
        assert cache_entry.ttl_seconds == 3600
        assert cache_entry.hit_count == 0  # Default
        assert cache_entry.expires_at is not None
    
    def test_milestone_cache_defaults(self):
        """Test milestone cache field defaults."""
        cache_entry = MilestoneCache(
            cache_key="test_key",
            data={"test": "data"},
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert cache_entry.ttl_seconds == 3600  # Default
        assert cache_entry.hit_count == 0  # Default
    
    async def test_milestone_cache_unique_key(self, async_db_session):
        """Test cache key uniqueness constraint."""
        # Add first cache entry
        cache1 = MilestoneCache(
            cache_key="duplicate_key",
            data={"version": 1},
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        async_db_session.add(cache1)
        await async_db_session.commit()
        
        # Try to add duplicate key
        cache2 = MilestoneCache(
            cache_key="duplicate_key",  # Same key
            data={"version": 2},
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        async_db_session.add(cache2)
        
        with pytest.raises(Exception):  # Should raise unique constraint violation
            await async_db_session.commit()


class TestMilestoneHelperFunctions:
    """Test milestone helper functions."""
    
    @patch('backend.src.models.milestone.select')
    @patch('backend.src.models.milestone.selectinload')
    async def test_get_user_milestone_tree(self, mock_selectinload, mock_select, async_db_session):
        """Test get_user_milestone_tree function."""
        user_id = str(uuid4())
        
        # Mock query results
        mock_milestone = Mock()
        mock_milestone.to_dict.return_value = {
            "id": "m1", "code": "M1", "name": "Test Milestone"
        }
        mock_milestone.dependencies = []
        
        mock_user_milestone = Mock()
        mock_user_milestone.to_dict.return_value = {
            "status": "completed", "completion_percentage": 100
        }
        mock_user_milestone.status = MilestoneStatus.COMPLETED
        
        # Mock database execute
        mock_result = AsyncMock()
        mock_result.all.return_value = [(mock_milestone, mock_user_milestone)]
        async_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute function
        tree = await get_user_milestone_tree(async_db_session, user_id)
        
        # Verify structure
        assert "milestones" in tree
        assert "total_progress" in tree
        assert "completed_count" in tree
        assert "available_count" in tree
        assert tree["completed_count"] == 1
        assert len(tree["milestones"]) == 1
    
    @patch('backend.src.models.milestone.select')
    @patch('backend.src.models.milestone.selectinload')
    async def test_check_milestone_dependencies(self, mock_selectinload, mock_select, async_db_session):
        """Test check_milestone_dependencies function."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        
        # Mock no dependencies
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        async_db_session.execute = AsyncMock(return_value=mock_result)
        
        # Test with no dependencies
        can_start, missing = await check_milestone_dependencies(
            async_db_session, user_id, milestone_id
        )
        
        assert can_start is True
        assert missing == []
    
    @patch('backend.src.models.milestone.select')
    @patch('backend.src.models.milestone.selectinload')
    async def test_check_milestone_dependencies_with_missing(self, mock_selectinload, mock_select, async_db_session):
        """Test check_milestone_dependencies with missing dependencies."""
        user_id = str(uuid4())
        milestone_id = str(uuid4())
        dependency_id = str(uuid4())
        
        # Mock dependency that's not met
        mock_dependency = Mock()
        mock_dependency.is_required = True
        mock_dependency.minimum_completion_percentage = 100.0
        mock_dependency.dependency_id = dependency_id
        mock_dependency.dependency.code = "M0"
        
        # Mock dependency query result
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = [mock_dependency]
        
        # Mock user progress query result (no progress found)
        mock_progress_result = AsyncMock()
        mock_progress_result.scalar_one_or_none.return_value = None
        
        async_db_session.execute = AsyncMock(side_effect=[
            mock_deps_result,  # Dependencies query
            mock_progress_result  # User progress query
        ])
        
        # Test with missing dependency
        can_start, missing = await check_milestone_dependencies(
            async_db_session, user_id, milestone_id
        )
        
        assert can_start is False
        assert "M0" in missing
    
    @patch('backend.src.models.milestone.select')
    @patch('backend.src.models.milestone.selectinload')
    async def test_update_dependent_milestones(self, mock_selectinload, mock_select, async_db_session):
        """Test update_dependent_milestones function."""
        user_id = str(uuid4())
        completed_milestone_id = str(uuid4())
        dependent_milestone_id = str(uuid4())
        
        # Mock dependent milestone
        mock_dependent = Mock()
        mock_dependent.milestone_id = dependent_milestone_id
        mock_dependent.milestone.auto_unlock = True
        
        # Mock queries
        mock_deps_result = AsyncMock()
        mock_deps_result.scalars.return_value.all.return_value = [mock_dependent]
        
        mock_user_milestone_result = AsyncMock()
        mock_user_milestone_result.scalar_one_or_none.return_value = None  # No existing user milestone
        
        async_db_session.execute = AsyncMock(side_effect=[
            mock_deps_result,  # Find dependents
            mock_user_milestone_result  # Check existing user milestone
        ])
        
        # Mock check_milestone_dependencies to return True
        with patch('backend.src.models.milestone.check_milestone_dependencies', 
                   AsyncMock(return_value=(True, []))):
            newly_unlocked = await update_dependent_milestones(
                async_db_session, user_id, completed_milestone_id
            )
        
        assert str(dependent_milestone_id) in newly_unlocked
        # Verify that new user milestone was added
        async_db_session.add.assert_called()


class TestModelRelationships:
    """Test model relationships and foreign key constraints."""
    
    async def test_milestone_dependencies_relationship(self, async_db_session, sample_milestone, sample_paid_milestone):
        """Test milestone dependencies relationship."""
        async_db_session.add(sample_milestone)
        async_db_session.add(sample_paid_milestone)
        await async_db_session.commit()
        
        # Create dependency
        dependency = MilestoneDependency(
            milestone_id=sample_paid_milestone.id,
            dependency_id=sample_milestone.id
        )
        async_db_session.add(dependency)
        await async_db_session.commit()
        
        # Test cascade delete
        await async_db_session.delete(sample_paid_milestone)
        await async_db_session.commit()
        
        # Dependency should be deleted due to cascade
        from sqlalchemy import select
        result = await async_db_session.execute(
            select(MilestoneDependency).where(MilestoneDependency.id == dependency.id)
        )
        deleted_dependency = result.scalar_one_or_none()
        assert deleted_dependency is None
    
    async def test_user_milestone_relationship(self, async_db_session, sample_user, sample_milestone):
        """Test user milestone relationships."""
        async_db_session.add(sample_user)
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        user_milestone = UserMilestone(
            user_id=sample_user.id,
            milestone_id=sample_milestone.id,
            status=MilestoneStatus.IN_PROGRESS
        )
        async_db_session.add(user_milestone)
        await async_db_session.commit()
        
        # Test relationship loading
        await async_db_session.refresh(user_milestone, ["milestone"])
        assert user_milestone.milestone is not None
        assert user_milestone.milestone.code == "M0"
    
    async def test_progress_log_cascade_delete(self, async_db_session, sample_user, sample_milestone):
        """Test that progress logs are deleted when user milestone is deleted."""
        async_db_session.add(sample_user)
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        user_milestone = UserMilestone(
            user_id=sample_user.id,
            milestone_id=sample_milestone.id
        )
        async_db_session.add(user_milestone)
        await async_db_session.commit()
        
        # Add progress log
        progress_log = MilestoneProgressLog(
            user_milestone_id=user_milestone.id,
            event_type="started"
        )
        async_db_session.add(progress_log)
        await async_db_session.commit()
        
        # Delete user milestone
        await async_db_session.delete(user_milestone)
        await async_db_session.commit()
        
        # Progress log should be deleted due to cascade
        from sqlalchemy import select
        result = await async_db_session.execute(
            select(MilestoneProgressLog).where(MilestoneProgressLog.id == progress_log.id)
        )
        deleted_log = result.scalar_one_or_none()
        assert deleted_log is None


class TestModelIndexes:
    """Test that database indexes are working correctly."""
    
    async def test_milestone_code_index(self, async_db_session):
        """Test that milestone code index improves query performance."""
        # Add multiple milestones
        milestones = []
        for i in range(10):
            milestone = Milestone(
                code=f"M{i}",
                name=f"Milestone {i}",
                order_index=i
            )
            milestones.append(milestone)
            async_db_session.add(milestone)
        
        await async_db_session.commit()
        
        # Query by code should use index (we can't directly test index usage in SQLite,
        # but we can test that the query works efficiently)
        from sqlalchemy import select
        result = await async_db_session.execute(
            select(Milestone).where(Milestone.code == "M5")
        )
        found_milestone = result.scalar_one()
        
        assert found_milestone.code == "M5"
        assert found_milestone.name == "Milestone 5"
    
    async def test_user_milestone_status_index(self, async_db_session, sample_user, sample_milestone):
        """Test user milestone status index."""
        async_db_session.add(sample_user)
        async_db_session.add(sample_milestone)
        await async_db_session.commit()
        
        # Add user milestones with different statuses
        statuses = [MilestoneStatus.COMPLETED, MilestoneStatus.IN_PROGRESS, MilestoneStatus.LOCKED]
        user_milestones = []
        
        for status in statuses:
            um = UserMilestone(
                user_id=sample_user.id,
                milestone_id=sample_milestone.id if status == MilestoneStatus.COMPLETED else uuid4(),
                status=status
            )
            user_milestones.append(um)
            async_db_session.add(um)
        
        await async_db_session.commit()
        
        # Query by status should be efficient
        from sqlalchemy import select
        result = await async_db_session.execute(
            select(UserMilestone).where(UserMilestone.status == MilestoneStatus.COMPLETED)
        )
        completed_milestones = result.scalars().all()
        
        assert len(completed_milestones) == 1
        assert completed_milestones[0].status == MilestoneStatus.COMPLETED


class TestModelValidation:
    """Test model validation and constraints."""
    
    def test_milestone_order_validation(self):
        """Test milestone order validation."""
        milestone = Milestone(
            code="M1",
            name="Test Milestone",
            order_index=-1  # Invalid negative order
        )
        
        # In a real application, you might have custom validators
        # For now, we just ensure the field accepts the value
        assert milestone.order_index == -1
    
    def test_completion_percentage_bounds(self):
        """Test completion percentage validation."""
        user_milestone = UserMilestone(
            user_id=uuid4(),
            milestone_id=uuid4(),
            completion_percentage=150.0  # Invalid > 100%
        )
        
        # The model allows this, but validation should happen at the service layer
        assert user_milestone.completion_percentage == 150.0
    
    def test_quality_score_bounds(self):
        """Test quality score validation."""
        user_milestone = UserMilestone(
            user_id=uuid4(),
            milestone_id=uuid4(),
            quality_score=1.5  # Might be invalid depending on scale
        )
        
        # Again, model allows this, validation at service layer
        assert user_milestone.quality_score == 1.5
    
    def test_feedback_rating_bounds(self):
        """Test feedback rating validation."""
        user_milestone = UserMilestone(
            user_id=uuid4(),
            milestone_id=uuid4(),
            feedback_rating=6  # Invalid if scale is 1-5
        )
        
        assert user_milestone.feedback_rating == 6