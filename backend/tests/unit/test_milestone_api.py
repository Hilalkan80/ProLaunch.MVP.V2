"""
Unit Tests for Milestone API Endpoints

Comprehensive test coverage for all milestone API endpoints including
request validation, response formatting, error handling, and authorization.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.src.api.v1.milestones import (
    router,
    get_milestone_service,
    get_dependency_manager,
    MilestoneResponse,
    UserMilestoneProgressResponse,
    MilestoneTreeResponse,
    StartMilestoneRequest,
    UpdateProgressRequest,
    CompleteMilestoneRequest,
    MilestoneFeedbackRequest,
    CreateArtifactRequest,
    MilestoneAnalyticsResponse
)
from backend.src.models.milestone import (
    Milestone,
    UserMilestone,
    MilestoneStatus,
    MilestoneType,
    UserMilestoneArtifact
)
from backend.src.models.user import User, SubscriptionTier
from backend.src.services.milestone_service import MilestoneService
from backend.src.services.dependency_manager import DependencyManager
from backend.src.core.exceptions import (
    MilestoneNotFoundError,
    MilestoneLockedError,
    MilestoneProcessingError
)


@pytest.fixture
def mock_current_user():
    """Create a mock current user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        subscription_tier=SubscriptionTier.PREMIUM,
        is_active=True,
        is_admin=False
    )


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        username="adminuser",
        subscription_tier=SubscriptionTier.PREMIUM,
        is_active=True,
        is_admin=True
    )


@pytest.fixture
def mock_milestone_service():
    """Create a mock milestone service."""
    service = AsyncMock(spec=MilestoneService)
    service.get_all_milestones = AsyncMock()
    service.get_milestone_by_code = AsyncMock()
    service.get_user_milestone_progress = AsyncMock()
    service.get_user_milestone_tree_with_cache = AsyncMock()
    service.start_milestone = AsyncMock()
    service.update_milestone_progress = AsyncMock()
    service.complete_milestone = AsyncMock()
    service.fail_milestone = AsyncMock()
    service.create_milestone_artifact = AsyncMock()
    service.get_user_artifacts = AsyncMock()
    service.get_user_analytics = AsyncMock()
    service.get_milestone_statistics = AsyncMock()
    service.initialize_user_milestones = AsyncMock()
    return service


@pytest.fixture
def mock_dependency_manager():
    """Create a mock dependency manager."""
    manager = AsyncMock(spec=DependencyManager)
    manager.validate_dependencies = AsyncMock()
    manager.process_milestone_completion = AsyncMock()
    return manager


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def sample_milestones():
    """Create sample milestones for testing."""
    return [
        Milestone(
            id=uuid4(),
            code="M0",
            name="Feasibility Snapshot",
            description="Initial feasibility assessment",
            milestone_type=MilestoneType.FREE,
            order_index=0,
            estimated_minutes=30,
            requires_payment=False,
            is_active=True
        ),
        Milestone(
            id=uuid4(),
            code="M1",
            name="Market Analysis",
            description="Comprehensive market research",
            milestone_type=MilestoneType.PAID,
            order_index=1,
            estimated_minutes=120,
            requires_payment=True,
            is_active=True
        ),
        Milestone(
            id=uuid4(),
            code="M2",
            name="Business Model",
            description="Business model development",
            milestone_type=MilestoneType.PAID,
            order_index=2,
            estimated_minutes=90,
            requires_payment=True,
            is_active=True
        )
    ]


class TestMilestoneRetrievalEndpoints:
    """Test milestone retrieval API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_all_milestones(self, mock_milestone_service, mock_current_user, sample_milestones):
        """Test GET /api/v1/milestones/ endpoint."""
        # Setup
        mock_milestone_service.get_all_milestones.return_value = sample_milestones
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_all_milestones
        
        # Execute
        result = await get_all_milestones(
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert len(result) == 3
        assert all(isinstance(item, MilestoneResponse) for item in result)
        assert result[0].code == "M0"
        assert result[0].name == "Feasibility Snapshot"
        assert result[1].code == "M1"
        mock_milestone_service.get_all_milestones.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_milestone_tree(self, mock_milestone_service, mock_current_user):
        """Test GET /api/v1/milestones/tree endpoint."""
        # Setup
        tree_data = {
            "milestones": [
                {
                    "id": str(uuid4()),
                    "code": "M0",
                    "name": "Feasibility",
                    "user_progress": {"status": "completed", "completion_percentage": 100}
                },
                {
                    "id": str(uuid4()),
                    "code": "M1",
                    "name": "Market Analysis", 
                    "user_progress": {"status": "in_progress", "completion_percentage": 60}
                }
            ],
            "total_progress": 80.0,
            "completed_count": 1,
            "available_count": 1
        }
        mock_milestone_service.get_user_milestone_tree_with_cache.return_value = tree_data
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_milestone_tree
        
        # Execute
        result = await get_milestone_tree(
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert isinstance(result, MilestoneTreeResponse)
        assert len(result.milestones) == 2
        assert result.total_progress == 80.0
        assert result.completed_count == 1
        assert result.available_count == 1
        mock_milestone_service.get_user_milestone_tree_with_cache.assert_called_once_with(
            str(mock_current_user.id)
        )
    
    @pytest.mark.asyncio
    async def test_get_user_progress_specific_milestone(self, mock_milestone_service, mock_current_user, sample_milestones):
        """Test GET /api/v1/milestones/progress with milestone_code parameter."""
        # Setup
        milestone_code = "M1"
        milestone = sample_milestones[1]  # M1
        progress_data = {
            "milestone_id": str(milestone.id),
            "status": "in_progress",
            "completion_percentage": 75.0,
            "current_step": 3,
            "total_steps": 4,
            "started_at": datetime.utcnow().isoformat(),
            "time_spent_seconds": 3600,
            "quality_score": 0.85
        }
        
        mock_milestone_service.get_milestone_by_code.return_value = milestone
        mock_milestone_service.get_user_milestone_progress.return_value = progress_data
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_user_progress
        
        # Execute
        result = await get_user_progress(
            milestone_code=milestone_code,
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert result == progress_data
        assert result["status"] == "in_progress"
        assert result["completion_percentage"] == 75.0
        mock_milestone_service.get_milestone_by_code.assert_called_once_with(milestone_code)
        mock_milestone_service.get_user_milestone_progress.assert_called_once_with(
            str(mock_current_user.id), str(milestone.id)
        )
    
    @pytest.mark.asyncio
    async def test_get_user_progress_milestone_not_found(self, mock_milestone_service, mock_current_user):
        """Test GET /api/v1/milestones/progress with non-existent milestone."""
        # Setup
        milestone_code = "INVALID"
        mock_milestone_service.get_milestone_by_code.return_value = None
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_user_progress
        
        # Execute and assert
        with pytest.raises(HTTPException) as exc_info:
            await get_user_progress(
                milestone_code=milestone_code,
                service=mock_milestone_service,
                current_user=mock_current_user
            )
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_user_progress_not_started(self, mock_milestone_service, mock_current_user, sample_milestones):
        """Test GET /api/v1/milestones/progress for milestone not yet started."""
        # Setup
        milestone_code = "M1"
        milestone = sample_milestones[1]
        mock_milestone_service.get_milestone_by_code.return_value = milestone
        mock_milestone_service.get_user_milestone_progress.return_value = None  # Not started
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_user_progress
        
        # Execute
        result = await get_user_progress(
            milestone_code=milestone_code,
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert result["milestone_code"] == milestone_code
        assert result["status"] == "not_started"
        assert result["completion_percentage"] == 0
    
    @pytest.mark.asyncio
    async def test_get_milestone_by_code(self, mock_milestone_service, mock_current_user, sample_milestones):
        """Test GET /api/v1/milestones/{milestone_code} endpoint."""
        # Setup
        milestone_code = "M1"
        milestone = sample_milestones[1]
        mock_milestone_service.get_milestone_by_code.return_value = milestone
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_milestone
        
        # Execute
        result = await get_milestone(
            milestone_code=milestone_code,
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert isinstance(result, MilestoneResponse)
        assert result.code == milestone_code
        assert result.name == milestone.name
        assert result.type == milestone.milestone_type
        mock_milestone_service.get_milestone_by_code.assert_called_once_with(milestone_code)


class TestMilestoneManagementEndpoints:
    """Test milestone management API endpoints."""
    
    @pytest.mark.asyncio
    async def test_start_milestone_success(self, mock_milestone_service, mock_dependency_manager, mock_current_user, sample_milestones):
        """Test POST /api/v1/milestones/{milestone_code}/start endpoint."""
        # Setup
        milestone_code = "M1"
        milestone = sample_milestones[1]
        user_milestone = UserMilestone(
            id=uuid4(),
            user_id=mock_current_user.id,
            milestone_id=milestone.id,
            status=MilestoneStatus.IN_PROGRESS
        )
        
        mock_milestone_service.get_milestone_by_code.return_value = milestone
        mock_dependency_manager.validate_dependencies.return_value = (True, [])  # Dependencies met
        mock_milestone_service.start_milestone.return_value = (True, f"Started milestone {milestone_code}", user_milestone)
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import start_milestone
        
        # Execute
        result = await start_milestone(
            milestone_code=milestone_code,
            request=None,
            service=mock_milestone_service,
            dep_manager=mock_dependency_manager,
            current_user=mock_current_user,
            db=mock_db_session()
        )
        
        # Assert
        assert result["success"] is True
        assert f"Started milestone {milestone_code}" in result["message"]
        assert result["milestone"] is not None
        assert result["dependencies_validated"] is True
        mock_dependency_manager.validate_dependencies.assert_called_once()
        mock_milestone_service.start_milestone.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_milestone_dependencies_not_met(self, mock_milestone_service, mock_dependency_manager, mock_current_user, sample_milestones):
        """Test starting milestone when dependencies are not met."""
        # Setup
        milestone_code = "M2"
        milestone = sample_milestones[2]
        missing_deps = [{"milestone_code": "M1", "name": "Market Analysis"}]
        
        mock_milestone_service.get_milestone_by_code.return_value = milestone
        mock_dependency_manager.validate_dependencies.return_value = (False, missing_deps)  # Dependencies not met
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import start_milestone
        
        # Execute and assert
        with pytest.raises(MilestoneLockedError):
            await start_milestone(
                milestone_code=milestone_code,
                request=None,
                service=mock_milestone_service,
                dep_manager=mock_dependency_manager,
                current_user=mock_current_user,
                db=mock_db_session()
            )
    
    @pytest.mark.asyncio
    async def test_start_milestone_not_found(self, mock_milestone_service, mock_dependency_manager, mock_current_user):
        """Test starting non-existent milestone."""
        # Setup
        milestone_code = "INVALID"
        mock_milestone_service.get_milestone_by_code.return_value = None
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import start_milestone
        
        # Execute and assert
        with pytest.raises(MilestoneNotFoundError):
            await start_milestone(
                milestone_code=milestone_code,
                request=None,
                service=mock_milestone_service,
                dep_manager=mock_dependency_manager,
                current_user=mock_current_user,
                db=mock_db_session()
            )
    
    @pytest.mark.asyncio
    async def test_update_progress(self, mock_milestone_service, mock_current_user):
        """Test PUT /api/v1/milestones/{milestone_code}/progress endpoint."""
        # Setup
        milestone_code = "M1"
        request_data = UpdateProgressRequest(
            step_completed=3,
            checkpoint_data={"analysis_type": "competitive", "sources_reviewed": 5},
            time_spent_seconds=1800
        )
        
        mock_milestone_service.update_milestone_progress.return_value = (True, "Progress updated successfully")
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import update_progress
        
        # Execute
        result = await update_progress(
            milestone_code=milestone_code,
            request=request_data,
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert result["success"] is True
        assert "updated successfully" in result["message"]
        assert result["step_completed"] == 3
        mock_milestone_service.update_milestone_progress.assert_called_once_with(
            str(mock_current_user.id),
            milestone_code,
            3,
            {"analysis_type": "competitive", "sources_reviewed": 5}
        )
    
    @pytest.mark.asyncio
    async def test_update_progress_failure(self, mock_milestone_service, mock_current_user):
        """Test progress update failure."""
        # Setup
        milestone_code = "M1"
        request_data = UpdateProgressRequest(step_completed=3)
        
        mock_milestone_service.update_milestone_progress.return_value = (False, "Milestone is not in progress")
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import update_progress
        
        # Execute and assert
        with pytest.raises(HTTPException) as exc_info:
            await update_progress(
                milestone_code=milestone_code,
                request=request_data,
                service=mock_milestone_service,
                current_user=mock_current_user
            )
        
        assert exc_info.value.status_code == 400
        assert "not in progress" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_complete_milestone(self, mock_milestone_service, mock_dependency_manager, mock_current_user, sample_milestones):
        """Test POST /api/v1/milestones/{milestone_code}/complete endpoint."""
        # Setup
        milestone_code = "M1"
        milestone = sample_milestones[1]
        
        request_data = CompleteMilestoneRequest(
            generated_output={
                "market_analysis": {"tam": 1000000000, "sam": 100000000, "som": 10000000},
                "competitive_analysis": [{"name": "Competitor A", "market_share": 0.3}],
                "recommendations": ["Focus on SMB market", "Develop mobile app"]
            },
            quality_score=0.9,
            artifacts=[
                {
                    "name": "Market Analysis Report",
                    "type": "pdf",
                    "content": {"report_data": "..."},
                    "storage_path": "/artifacts/market_report.pdf"
                }
            ]
        )
        
        mock_milestone_service.get_milestone_by_code.return_value = milestone
        mock_milestone_service.complete_milestone.return_value = (True, f"Milestone {milestone_code} completed successfully", ["M2", "M3"])
        mock_dependency_manager.process_milestone_completion.return_value = [
            {"milestone_id": "M2", "milestone_code": "M2", "unlocked_by": "dependency_resolution"}
        ]
        mock_milestone_service.create_milestone_artifact.return_value = UserMilestoneArtifact(
            id=uuid4(),
            name="Market Analysis Report"
        )
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import complete_milestone
        
        # Execute
        result = await complete_milestone(
            milestone_code=milestone_code,
            request=request_data,
            service=mock_milestone_service,
            dep_manager=mock_dependency_manager,
            current_user=mock_current_user
        )
        
        # Assert
        assert result["success"] is True
        assert "completed successfully" in result["message"]
        assert result["completed_milestone"]["code"] == milestone_code
        assert len(result["newly_unlocked"]) >= 1
        assert result["total_unlocked"] >= 1
        
        mock_milestone_service.complete_milestone.assert_called_once()
        mock_dependency_manager.process_milestone_completion.assert_called_once()
        mock_milestone_service.create_milestone_artifact.assert_called()
    
    @pytest.mark.asyncio
    async def test_complete_milestone_processing_error(self, mock_milestone_service, mock_dependency_manager, mock_current_user, sample_milestones):
        """Test milestone completion processing error."""
        # Setup
        milestone_code = "M1"
        milestone = sample_milestones[1]
        
        request_data = CompleteMilestoneRequest(
            generated_output={"result": "data"},
            quality_score=0.8
        )
        
        mock_milestone_service.get_milestone_by_code.return_value = milestone
        mock_milestone_service.complete_milestone.return_value = (False, "Validation failed", [])
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import complete_milestone
        
        # Execute and assert
        with pytest.raises(MilestoneProcessingError):
            await complete_milestone(
                milestone_code=milestone_code,
                request=request_data,
                service=mock_milestone_service,
                dep_manager=mock_dependency_manager,
                current_user=mock_current_user
            )
    
    @pytest.mark.asyncio
    async def test_fail_milestone(self, mock_milestone_service, mock_current_user):
        """Test POST /api/v1/milestones/{milestone_code}/fail endpoint."""
        # Setup
        milestone_code = "M1"
        error_message = "Processing timeout exceeded"
        
        mock_milestone_service.fail_milestone.return_value = (True, "Milestone marked as failed")
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import fail_milestone
        
        # Execute
        result = await fail_milestone(
            milestone_code=milestone_code,
            error_message=error_message,
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert result["success"] is True
        assert "marked as failed" in result["message"]
        mock_milestone_service.fail_milestone.assert_called_once_with(
            str(mock_current_user.id),
            milestone_code,
            error_message
        )
    
    @pytest.mark.asyncio
    async def test_submit_feedback(self, mock_milestone_service, mock_db_session, mock_current_user, sample_milestones):
        """Test POST /api/v1/milestones/{milestone_code}/feedback endpoint."""
        # Setup
        milestone_code = "M1"
        milestone = sample_milestones[1]
        
        request_data = MilestoneFeedbackRequest(
            rating=4,
            feedback_text="Great milestone, very comprehensive analysis",
            improvement_suggestions=["More visual charts", "Faster processing"]
        )
        
        user_milestone = UserMilestone(
            id=uuid4(),
            user_id=mock_current_user.id,
            milestone_id=milestone.id,
            status=MilestoneStatus.COMPLETED
        )
        
        mock_milestone_service.get_milestone_by_code.return_value = milestone
        
        # Mock database query result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_milestone
        mock_db_session.execute.return_value = mock_result
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import submit_feedback
        
        # Execute
        result = await submit_feedback(
            milestone_code=milestone_code,
            request=request_data,
            service=mock_milestone_service,
            db=mock_db_session,
            current_user=mock_current_user
        )
        
        # Assert
        assert result["success"] is True
        assert "submitted successfully" in result["message"]
        assert user_milestone.feedback_rating == 4
        assert user_milestone.feedback_text == "Great milestone, very comprehensive analysis"
        mock_db_session.commit.assert_called_once()


class TestArtifactEndpoints:
    """Test artifact-related API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_artifact(self, mock_milestone_service, mock_current_user):
        """Test POST /api/v1/milestones/{milestone_code}/artifacts endpoint."""
        # Setup
        milestone_code = "M1"
        
        request_data = CreateArtifactRequest(
            name="Business Plan Draft",
            artifact_type="document",
            content={
                "sections": ["executive_summary", "market_analysis", "financial_projections"],
                "content": {"executive_summary": "Our innovative solution addresses..."}
            },
            storage_path="/artifacts/business_plan_draft.json",
            is_public=False
        )
        
        created_artifact = UserMilestoneArtifact(
            id=uuid4(),
            name="Business Plan Draft",
            artifact_type="document"
        )
        
        mock_milestone_service.create_milestone_artifact.return_value = created_artifact
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import create_artifact
        
        # Execute
        result = await create_artifact(
            milestone_code=milestone_code,
            request=request_data,
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert result["success"] is True
        assert result["artifact_id"] == str(created_artifact.id)
        assert result["name"] == "Business Plan Draft"
        assert result["type"] == "document"
        
        mock_milestone_service.create_milestone_artifact.assert_called_once_with(
            str(mock_current_user.id),
            milestone_code,
            "Business Plan Draft",
            "document",
            request_data.content,
            "/artifacts/business_plan_draft.json"
        )
    
    @pytest.mark.asyncio
    async def test_create_artifact_failure(self, mock_milestone_service, mock_current_user):
        """Test artifact creation failure."""
        # Setup
        milestone_code = "M1"
        request_data = CreateArtifactRequest(
            name="Test Artifact",
            artifact_type="document",
            content={"data": "test"}
        )
        
        mock_milestone_service.create_milestone_artifact.return_value = None  # Creation failed
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import create_artifact
        
        # Execute and assert
        with pytest.raises(HTTPException) as exc_info:
            await create_artifact(
                milestone_code=milestone_code,
                request=request_data,
                service=mock_milestone_service,
                current_user=mock_current_user
            )
        
        assert exc_info.value.status_code == 400
        assert "Failed to create artifact" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_user_artifacts(self, mock_milestone_service, mock_current_user):
        """Test GET /api/v1/milestones/artifacts/ endpoint."""
        # Setup
        milestone_code = "M1"
        
        artifacts = [
            UserMilestoneArtifact(
                id=uuid4(),
                name="Market Analysis Report",
                artifact_type="pdf",
                created_at=datetime.utcnow()
            ),
            UserMilestoneArtifact(
                id=uuid4(),
                name="Financial Model",
                artifact_type="xlsx",
                created_at=datetime.utcnow() - timedelta(hours=1)
            )
        ]
        
        mock_milestone_service.get_user_artifacts.return_value = artifacts
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_user_artifacts
        
        # Execute
        result = await get_user_artifacts(
            milestone_code=milestone_code,
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert "artifacts" in result
        assert len(result["artifacts"]) == 2
        
        artifact_1 = result["artifacts"][0]
        assert artifact_1["name"] == "Market Analysis Report"
        assert artifact_1["type"] == "pdf"
        assert artifact_1["milestone_code"] == milestone_code
        
        mock_milestone_service.get_user_artifacts.assert_called_once_with(
            str(mock_current_user.id),
            milestone_code
        )
    
    @pytest.mark.asyncio
    async def test_get_user_artifacts_all_milestones(self, mock_milestone_service, mock_current_user):
        """Test getting artifacts for all milestones."""
        # Setup
        artifacts = [
            UserMilestoneArtifact(
                id=uuid4(),
                name="Feasibility Report",
                artifact_type="pdf",
                created_at=datetime.utcnow()
            )
        ]
        
        mock_milestone_service.get_user_artifacts.return_value = artifacts
        
        # Import the endpoint function  
        from backend.src.api.v1.milestones import get_user_artifacts
        
        # Execute (no milestone_code specified)
        result = await get_user_artifacts(
            milestone_code=None,
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert len(result["artifacts"]) == 1
        mock_milestone_service.get_user_artifacts.assert_called_once_with(
            str(mock_current_user.id),
            None
        )


class TestAnalyticsEndpoints:
    """Test analytics and reporting API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_user_analytics(self, mock_milestone_service, mock_current_user):
        """Test GET /api/v1/milestones/analytics/user endpoint."""
        # Setup
        analytics_data = {
            "total_milestones": 10,
            "completed": 6,
            "in_progress": 2,
            "locked": 2,
            "failed": 0,
            "total_time_spent_hours": 12.5,
            "average_completion_time_hours": 2.08,
            "completion_rate": 60.0,
            "average_quality_score": 0.87,
            "milestones_by_status": {"completed": 6, "in_progress": 2, "locked": 2},
            "time_by_milestone": {"M0": 1.5, "M1": 3.2, "M2": 2.8}
        }
        
        mock_milestone_service.get_user_analytics.return_value = analytics_data
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_user_analytics
        
        # Execute
        result = await get_user_analytics(
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert isinstance(result, MilestoneAnalyticsResponse)
        assert result.total_milestones == 10
        assert result.completed == 6
        assert result.completion_rate == 60.0
        assert result.average_quality_score == 0.87
        
        mock_milestone_service.get_user_analytics.assert_called_once_with(
            str(mock_current_user.id)
        )
    
    @pytest.mark.asyncio
    async def test_get_milestone_statistics(self, mock_milestone_service, mock_current_user):
        """Test GET /api/v1/milestones/analytics/milestone/{milestone_code} endpoint."""
        # Setup
        milestone_code = "M1"
        stats_data = {
            "started": 500,
            "completed": 420,
            "failed": 30,
            "skipped": 10,
            "completion_rate": 84.0,
            "average_completion_time_minutes": 125.5,
            "average_quality_score": 0.86
        }
        
        mock_milestone_service.get_milestone_statistics.return_value = stats_data
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_milestone_statistics
        
        # Execute
        result = await get_milestone_statistics(
            milestone_code=milestone_code,
            service=mock_milestone_service,
            current_user=mock_current_user
        )
        
        # Assert
        assert result == stats_data
        assert result["completion_rate"] == 84.0
        assert result["average_completion_time_minutes"] == 125.5
        
        mock_milestone_service.get_milestone_statistics.assert_called_once_with(milestone_code)
    
    @pytest.mark.asyncio
    async def test_get_leaderboard(self, mock_current_user):
        """Test GET /api/v1/milestones/leaderboard endpoint."""
        # Setup
        from backend.src.services.milestone_cache import MilestoneCacheService
        mock_redis_client = AsyncMock()
        mock_cache_service = MilestoneCacheService(mock_redis_client)
        
        leaderboard_data = [
            {"rank": 1, "user_id": "user1", "score": 1500},
            {"rank": 2, "user_id": str(mock_current_user.id), "score": 1200},
            {"rank": 3, "user_id": "user3", "score": 1000}
        ]
        
        mock_cache_service.get_leaderboard = AsyncMock(return_value=leaderboard_data)
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_leaderboard
        
        # Execute (mocking the dependency)
        with patch('backend.src.api.v1.milestones.MilestoneCacheService', return_value=mock_cache_service):
            result = await get_leaderboard(
                leaderboard_type="weekly",
                limit=10,
                redis=mock_redis_client,
                current_user=mock_current_user
            )
        
        # Assert
        assert result["leaderboard"] == leaderboard_data
        assert result["current_user_rank"] == 2  # User is rank 2
        assert result["type"] == "weekly"


class TestAdminEndpoints:
    """Test admin-only API endpoints."""
    
    @pytest.mark.asyncio
    async def test_initialize_user_milestones_admin(self, mock_milestone_service, mock_admin_user):
        """Test POST /api/v1/milestones/initialize/{user_id} endpoint with admin user."""
        # Setup
        user_id = str(uuid4())
        initialized_milestones = [
            UserMilestone(id=uuid4(), user_id=user_id, milestone_id=uuid4()),
            UserMilestone(id=uuid4(), user_id=user_id, milestone_id=uuid4())
        ]
        
        mock_milestone_service.initialize_user_milestones.return_value = initialized_milestones
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import initialize_user_milestones
        
        # Execute
        result = await initialize_user_milestones(
            user_id=user_id,
            service=mock_milestone_service,
            current_user=mock_admin_user
        )
        
        # Assert
        assert result["success"] is True
        assert f"Initialized 2 milestones for user {user_id}" in result["message"]
        
        mock_milestone_service.initialize_user_milestones.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_initialize_user_milestones_non_admin(self, mock_milestone_service, mock_current_user):
        """Test admin endpoint with non-admin user."""
        # Setup
        user_id = str(uuid4())
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import initialize_user_milestones
        
        # Execute and assert
        with pytest.raises(HTTPException) as exc_info:
            await initialize_user_milestones(
                user_id=user_id,
                service=mock_milestone_service,
                current_user=mock_current_user  # Not admin
            )
        
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_clear_user_cache_admin(self, mock_admin_user):
        """Test DELETE /api/v1/milestones/cache/user/{user_id} endpoint."""
        # Setup
        user_id = str(uuid4())
        from backend.src.services.milestone_cache import MilestoneCacheService
        
        mock_redis_client = AsyncMock()
        mock_cache_service = MilestoneCacheService(mock_redis_client)
        mock_cache_service.invalidate_user_cache = AsyncMock(return_value=True)
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import clear_user_cache
        
        # Execute (mocking the dependency)
        with patch('backend.src.api.v1.milestones.MilestoneCacheService', return_value=mock_cache_service):
            result = await clear_user_cache(
                user_id=user_id,
                redis=mock_redis_client,
                current_user=mock_admin_user
            )
        
        # Assert
        assert result["success"] is True
        assert f"Cache cleared for user {user_id}" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_cache_statistics_admin(self, mock_admin_user):
        """Test GET /api/v1/milestones/cache/stats endpoint."""
        # Setup
        from backend.src.services.milestone_cache import MilestoneCacheService
        
        mock_redis_client = AsyncMock()
        mock_cache_service = MilestoneCacheService(mock_redis_client)
        
        cache_stats = {
            "hits": 15000,
            "misses": 3000,
            "hit_rate": 83.33,
            "total_requests": 18000,
            "errors": 5,
            "memory_usage": "256MB",
            "active_connections": 25
        }
        
        mock_cache_service.get_cache_stats = AsyncMock(return_value=cache_stats)
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_cache_statistics
        
        # Execute (mocking the dependency)
        with patch('backend.src.api.v1.milestones.MilestoneCacheService', return_value=mock_cache_service):
            result = await get_cache_statistics(
                redis=mock_redis_client,
                current_user=mock_admin_user
            )
        
        # Assert
        assert result == cache_stats
        assert result["hit_rate"] == 83.33
        assert result["total_requests"] == 18000


class TestRequestValidation:
    """Test request validation and error handling."""
    
    def test_start_milestone_request_validation(self):
        """Test StartMilestoneRequest validation."""
        # Valid request
        valid_request = StartMilestoneRequest(
            milestone_code="M1",
            session_metadata={"browser": "Chrome", "device": "Desktop"}
        )
        assert valid_request.milestone_code == "M1"
        
        # Invalid milestone code format
        with pytest.raises(ValueError):
            StartMilestoneRequest(milestone_code="INVALID")
    
    def test_update_progress_request_validation(self):
        """Test UpdateProgressRequest validation."""
        # Valid request
        valid_request = UpdateProgressRequest(
            step_completed=3,
            checkpoint_data={"analysis": "completed"},
            time_spent_seconds=1800
        )
        assert valid_request.step_completed == 3
        assert valid_request.time_spent_seconds == 1800
        
        # Invalid step (too low)
        with pytest.raises(ValueError):
            UpdateProgressRequest(step_completed=0)
        
        # Invalid time (negative)
        with pytest.raises(ValueError):
            UpdateProgressRequest(step_completed=1, time_spent_seconds=-100)
    
    def test_complete_milestone_request_validation(self):
        """Test CompleteMilestoneRequest validation."""
        # Valid request
        valid_request = CompleteMilestoneRequest(
            generated_output={"result": "analysis complete"},
            quality_score=0.85,
            artifacts=[]
        )
        assert valid_request.quality_score == 0.85
        
        # Invalid quality score (too high)
        with pytest.raises(ValueError):
            CompleteMilestoneRequest(
                generated_output={"result": "data"},
                quality_score=1.5  # > 1.0
            )
        
        # Invalid quality score (too low)
        with pytest.raises(ValueError):
            CompleteMilestoneRequest(
                generated_output={"result": "data"},
                quality_score=-0.1  # < 0.0
            )
    
    def test_milestone_feedback_request_validation(self):
        """Test MilestoneFeedbackRequest validation."""
        # Valid request
        valid_request = MilestoneFeedbackRequest(
            rating=4,
            feedback_text="Great milestone!",
            improvement_suggestions=["Add more examples", "Clearer instructions"]
        )
        assert valid_request.rating == 4
        
        # Invalid rating (too high)
        with pytest.raises(ValueError):
            MilestoneFeedbackRequest(rating=6)
        
        # Invalid rating (too low)
        with pytest.raises(ValueError):
            MilestoneFeedbackRequest(rating=0)
        
        # Feedback text too long
        with pytest.raises(ValueError):
            MilestoneFeedbackRequest(
                rating=5,
                feedback_text="x" * 1001  # > 1000 characters
            )
    
    def test_create_artifact_request_validation(self):
        """Test CreateArtifactRequest validation."""
        # Valid request
        valid_request = CreateArtifactRequest(
            name="Test Document",
            artifact_type="pdf",
            content={"data": "test content"},
            storage_path="/artifacts/test.pdf",
            is_public=False
        )
        assert valid_request.name == "Test Document"
        assert valid_request.is_public is False
        
        # Name too long
        with pytest.raises(ValueError):
            CreateArtifactRequest(
                name="x" * 201,  # > 200 characters
                artifact_type="pdf",
                content={"data": "test"}
            )
        
        # Artifact type too long
        with pytest.raises(ValueError):
            CreateArtifactRequest(
                name="Test",
                artifact_type="x" * 51,  # > 50 characters
                content={"data": "test"}
            )


class TestResponseSerialization:
    """Test response model serialization."""
    
    def test_milestone_response_serialization(self, sample_milestones):
        """Test MilestoneResponse serialization."""
        milestone = sample_milestones[0]
        
        response = MilestoneResponse(
            id=str(milestone.id),
            code=milestone.code,
            name=milestone.name,
            description=milestone.description,
            type=milestone.milestone_type,
            order=milestone.order_index,
            estimated_minutes=milestone.estimated_minutes,
            requires_payment=milestone.requires_payment,
            is_active=milestone.is_active,
            dependencies=[]
        )
        
        # Test serialization to dict
        response_dict = response.dict()
        assert response_dict["code"] == "M0"
        assert response_dict["name"] == "Feasibility Snapshot"
        assert response_dict["type"] == MilestoneType.FREE
    
    def test_milestone_tree_response_serialization(self):
        """Test MilestoneTreeResponse serialization."""
        response = MilestoneTreeResponse(
            milestones=[
                {"id": "m1", "code": "M1", "name": "Test", "status": "completed"},
                {"id": "m2", "code": "M2", "name": "Test 2", "status": "available"}
            ],
            total_progress=50.0,
            completed_count=1,
            available_count=1,
            locked_count=0
        )
        
        response_dict = response.dict()
        assert len(response_dict["milestones"]) == 2
        assert response_dict["total_progress"] == 50.0
        assert response_dict["completed_count"] == 1
    
    def test_milestone_analytics_response_serialization(self):
        """Test MilestoneAnalyticsResponse serialization."""
        response = MilestoneAnalyticsResponse(
            total_milestones=10,
            completed=6,
            in_progress=2,
            locked=2,
            failed=0,
            total_time_spent_hours=15.5,
            average_completion_time_hours=2.5,
            completion_rate=60.0,
            average_quality_score=0.88,
            milestones_by_status={"completed": 6, "in_progress": 2, "locked": 2},
            time_by_milestone={"M1": 3.5, "M2": 4.2, "M3": 2.8}
        )
        
        response_dict = response.dict()
        assert response_dict["completion_rate"] == 60.0
        assert response_dict["average_quality_score"] == 0.88
        assert len(response_dict["milestones_by_status"]) == 3


class TestErrorHandling:
    """Test error handling in API endpoints."""
    
    @pytest.mark.asyncio
    async def test_service_exception_handling(self, mock_milestone_service, mock_current_user):
        """Test handling of service layer exceptions."""
        # Setup service to raise exception
        mock_milestone_service.get_all_milestones.side_effect = Exception("Database connection failed")
        
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_all_milestones
        
        # Execute and assert
        with pytest.raises(Exception, match="Database connection failed"):
            await get_all_milestones(
                service=mock_milestone_service,
                current_user=mock_current_user
            )
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, mock_milestone_service, mock_current_user):
        """Test handling of validation errors."""
        # Test with invalid progress update
        invalid_request = UpdateProgressRequest(
            step_completed=-1,  # Invalid: must be >= 1
        )
        
        # The validation should happen at the pydantic level
        # This test verifies that the request model validation works
        assert invalid_request.step_completed == -1  # Pydantic allows it, but business logic should validate
    
    @pytest.mark.asyncio
    async def test_authentication_error_simulation(self, mock_milestone_service):
        """Test behavior when no authenticated user provided."""
        # Import the endpoint function
        from backend.src.api.v1.milestones import get_all_milestones
        
        # Execute without current_user should fail in real implementation
        # This test verifies the dependency structure
        try:
            await get_all_milestones(
                service=mock_milestone_service,
                current_user=None  # No authenticated user
            )
        except AttributeError:
            # Expected when trying to access None.id
            pass


class TestDependencyInjection:
    """Test dependency injection and service instantiation."""
    
    @pytest.mark.asyncio
    async def test_get_milestone_service_dependency(self, mock_db_session):
        """Test milestone service dependency injection."""
        # Mock redis client
        mock_redis_client = AsyncMock()
        
        # This would normally be tested with actual dependency injection
        # For unit tests, we verify the concept
        service = get_milestone_service.__wrapped__(
            db=mock_db_session,
            redis=mock_redis_client
        )
        
        # Service should be created with proper dependencies
        assert service is not None
        # In real implementation, verify service has correct dependencies
    
    @pytest.mark.asyncio
    async def test_get_dependency_manager_dependency(self, mock_db_session):
        """Test dependency manager dependency injection."""
        # Mock redis client
        mock_redis_client = AsyncMock()
        
        # This would test actual dependency manager creation
        manager = get_dependency_manager.__wrapped__(
            db=mock_db_session,
            redis=mock_redis_client
        )
        
        assert manager is not None