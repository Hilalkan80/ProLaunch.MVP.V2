"""
Milestone API Endpoints

RESTful API endpoints for milestone management, progress tracking,
and artifact handling.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
from uuid import UUID

from ...core.database import get_db
from ...models.user import User
from ...models.milestone import MilestoneStatus, MilestoneType
from ...services.milestone_service import MilestoneService
from ...services.milestone_cache import MilestoneCacheService
from ...services.dependency_manager import DependencyManager
from ...infrastructure.redis.redis_mcp import RedisMCPClient
from ...core.auth import get_current_user
from ...core.dependencies import get_redis_client
from ...core.exceptions import (
    MilestoneNotFoundError,
    MilestoneLockedError,
    MilestoneProcessingError
)


# Pydantic models for request/response

class MilestoneResponse(BaseModel):
    """Response model for milestone data."""
    id: str
    code: str
    name: str
    description: Optional[str]
    type: str
    order: int
    estimated_minutes: int
    requires_payment: bool
    is_active: bool
    dependencies: List[Dict[str, Any]] = []
    
    class Config:
        orm_mode = True


class UserMilestoneProgressResponse(BaseModel):
    """Response model for user milestone progress."""
    milestone_id: str
    status: str
    completion_percentage: float
    current_step: int
    total_steps: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    time_spent_seconds: int
    quality_score: Optional[float]
    feedback_rating: Optional[int]
    
    class Config:
        orm_mode = True


class MilestoneTreeResponse(BaseModel):
    """Response model for complete milestone tree."""
    milestones: List[Dict[str, Any]]
    total_progress: float
    completed_count: int
    available_count: int
    
    class Config:
        orm_mode = True


class StartMilestoneRequest(BaseModel):
    """Request model for starting a milestone."""
    milestone_code: str = Field(..., regex="^M[0-9]+$")
    session_metadata: Optional[Dict[str, Any]] = None


class UpdateProgressRequest(BaseModel):
    """Request model for updating milestone progress."""
    step_completed: int = Field(..., ge=1)
    checkpoint_data: Optional[Dict[str, Any]] = None
    time_spent_seconds: Optional[int] = Field(None, ge=0)


class CompleteMilestoneRequest(BaseModel):
    """Request model for completing a milestone."""
    generated_output: Dict[str, Any]
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    artifacts: Optional[List[Dict[str, Any]]] = []


class MilestoneFeedbackRequest(BaseModel):
    """Request model for milestone feedback."""
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = Field(None, max_length=1000)
    improvement_suggestions: Optional[List[str]] = []


class CreateArtifactRequest(BaseModel):
    """Request model for creating an artifact."""
    name: str = Field(..., max_length=200)
    artifact_type: str = Field(..., max_length=50)
    content: Dict[str, Any]
    storage_path: Optional[str] = None
    is_public: bool = False


class MilestoneAnalyticsResponse(BaseModel):
    """Response model for milestone analytics."""
    total_milestones: int
    completed: int
    in_progress: int
    locked: int
    failed: int
    total_time_spent_hours: float
    average_completion_time_hours: float
    completion_rate: float
    average_quality_score: Optional[float]
    milestones_by_status: Dict[str, int]
    time_by_milestone: Dict[str, float]


# Create router
router = APIRouter(
    prefix="/api/v1/milestones",
    tags=["milestones"]
)


# Dependency to get milestone service
async def get_milestone_service(
    db: AsyncSession = Depends(get_db),
    redis: RedisMCPClient = Depends(get_redis_client)
) -> MilestoneService:
    """Get milestone service instance."""
    cache_service = MilestoneCacheService(redis)
    return MilestoneService(db, cache_service)


# Dependency to get dependency manager
async def get_dependency_manager(
    db: AsyncSession = Depends(get_db),
    redis: RedisMCPClient = Depends(get_redis_client)
) -> DependencyManager:
    """Get dependency manager instance."""
    cache_service = MilestoneCacheService(redis)
    return DependencyManager(db, cache_service, redis)


# Milestone retrieval endpoints

@router.get("/", response_model=List[MilestoneResponse])
async def get_all_milestones(
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get all available milestones.
    
    Returns a list of all active milestones in the system.
    """
    milestones = await service.get_all_milestones()
    return [
        MilestoneResponse(
            id=str(m.id),
            code=m.code,
            name=m.name,
            description=m.description,
            type=m.milestone_type,
            order=m.order_index,
            estimated_minutes=m.estimated_minutes,
            requires_payment=m.requires_payment,
            is_active=m.is_active,
            dependencies=[]  # Populated separately if needed
        )
        for m in milestones
    ]


@router.get("/tree", response_model=MilestoneTreeResponse)
async def get_milestone_tree(
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete milestone tree with user progress.
    
    Returns the entire milestone structure with dependency relationships
    and the current user's progress through each milestone.
    """
    tree = await service.get_user_milestone_tree_with_cache(str(current_user.id))
    return MilestoneTreeResponse(**tree)


@router.get("/progress", response_model=Dict[str, Any])
async def get_user_progress(
    milestone_code: Optional[str] = Query(None, regex="^M[0-9]+$"),
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's milestone progress.
    
    If milestone_code is provided, returns progress for that specific milestone.
    Otherwise, returns progress for all milestones.
    """
    if milestone_code:
        milestone = await service.get_milestone_by_code(milestone_code)
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")
        
        progress = await service.get_user_milestone_progress(
            str(current_user.id),
            str(milestone.id)
        )
        
        if not progress:
            return {
                "milestone_code": milestone_code,
                "status": "not_started",
                "completion_percentage": 0
            }
        
        return progress
    else:
        return await service.get_user_milestone_progress(str(current_user.id))


@router.get("/{milestone_code}", response_model=MilestoneResponse)
async def get_milestone(
    milestone_code: str = Path(..., regex="^M[0-9]+$"),
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get details for a specific milestone.
    """
    milestone = await service.get_milestone_by_code(milestone_code)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    return MilestoneResponse(
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


# Milestone management endpoints

@router.post("/{milestone_code}/start")
async def start_milestone(
    milestone_code: str = Path(..., regex="^M[0-9]+$"),
    request: Optional[StartMilestoneRequest] = None,
    service: MilestoneService = Depends(get_milestone_service),
    dep_manager: DependencyManager = Depends(get_dependency_manager),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start working on a milestone.
    
    Validates dependencies and user access before starting.
    Returns the milestone progress object with dependency validation.
    """
    # First check dependencies
    milestone = await service.get_milestone_by_code(milestone_code)
    if not milestone:
        raise MilestoneNotFoundError(milestone_code)
    
    # Validate dependencies
    all_met, unmet = await dep_manager.validate_dependencies(
        str(current_user.id),
        str(milestone.id),
        check_conditions=True
    )
    
    if not all_met:
        missing_codes = [d["milestone_code"] for d in unmet]
        raise MilestoneLockedError(milestone_code, missing_codes)
    
    # Now start the milestone
    success, message, user_milestone = await service.start_milestone(
        str(current_user.id),
        milestone_code
    )
    
    if not success:
        if "locked" in message.lower() or "dependencies" in message.lower():
            # Extract dependency info from message if available
            raise MilestoneLockedError(milestone_code)
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message,
        "milestone": user_milestone.to_dict() if user_milestone else None,
        "dependencies_validated": True
    }


@router.put("/{milestone_code}/progress")
async def update_progress(
    milestone_code: str = Path(..., regex="^M[0-9]+$"),
    request: UpdateProgressRequest = Body(...),
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Update progress for a milestone in progress.
    
    Updates the current step and optional checkpoint data.
    """
    success, message = await service.update_milestone_progress(
        str(current_user.id),
        milestone_code,
        request.step_completed,
        request.checkpoint_data
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message,
        "step_completed": request.step_completed
    }


@router.post("/{milestone_code}/complete")
async def complete_milestone(
    milestone_code: str = Path(..., regex="^M[0-9]+$"),
    request: CompleteMilestoneRequest = Body(...),
    service: MilestoneService = Depends(get_milestone_service),
    dep_manager: DependencyManager = Depends(get_dependency_manager),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a milestone as completed.
    
    Saves generated output and triggers auto-unlock of dependent milestones.
    """
    # Get milestone
    milestone = await service.get_milestone_by_code(milestone_code)
    if not milestone:
        raise MilestoneNotFoundError(milestone_code)
    
    # Complete the milestone
    success, message, newly_unlocked_ids = await service.complete_milestone(
        str(current_user.id),
        milestone_code,
        request.generated_output,
        request.quality_score
    )
    
    if not success:
        raise MilestoneProcessingError(milestone_code, message)
    
    # Process dependency auto-unlocks
    auto_unlocked = await dep_manager.process_milestone_completion(
        str(current_user.id),
        str(milestone.id)
    )
    
    # Combine unlocked milestones from both sources
    all_unlocked = []
    unlocked_ids = set()
    
    # Add from service
    for mid in newly_unlocked_ids:
        if mid not in unlocked_ids:
            unlocked_ids.add(mid)
            all_unlocked.append({"milestone_id": mid})
    
    # Add from dependency manager with more details
    for unlocked in auto_unlocked:
        if unlocked["milestone_id"] not in unlocked_ids:
            all_unlocked.append(unlocked)
    
    # Create artifacts if provided
    if request.artifacts:
        for artifact_data in request.artifacts:
            await service.create_milestone_artifact(
                str(current_user.id),
                milestone_code,
                artifact_data.get("name"),
                artifact_data.get("type"),
                artifact_data.get("content"),
                artifact_data.get("storage_path")
            )
    
    return {
        "success": True,
        "message": message,
        "completed_milestone": {
            "code": milestone_code,
            "name": milestone.name
        },
        "newly_unlocked": all_unlocked,
        "total_unlocked": len(all_unlocked)
    }


@router.post("/{milestone_code}/fail")
async def fail_milestone(
    milestone_code: str = Path(..., regex="^M[0-9]+$"),
    error_message: str = Body(..., embed=True),
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a milestone as failed.
    
    Records the error and allows retry.
    """
    success, message = await service.fail_milestone(
        str(current_user.id),
        milestone_code,
        error_message
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "message": message
    }


@router.post("/{milestone_code}/feedback")
async def submit_feedback(
    milestone_code: str = Path(..., regex="^M[0-9]+$"),
    request: MilestoneFeedbackRequest = Body(...),
    service: MilestoneService = Depends(get_milestone_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit feedback for a completed milestone.
    """
    # Get milestone
    milestone = await service.get_milestone_by_code(milestone_code)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    # Update user milestone with feedback
    from sqlalchemy import select, and_
    from ...models.milestone import UserMilestone
    
    stmt = select(UserMilestone).where(
        and_(
            UserMilestone.user_id == current_user.id,
            UserMilestone.milestone_id == milestone.id
        )
    )
    result = await db.execute(stmt)
    user_milestone = result.scalar_one_or_none()
    
    if not user_milestone:
        raise HTTPException(status_code=404, detail="User milestone not found")
    
    user_milestone.feedback_rating = request.rating
    user_milestone.feedback_text = request.feedback_text
    user_milestone.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Feedback submitted successfully"
    }


# Artifact endpoints

@router.post("/{milestone_code}/artifacts")
async def create_artifact(
    milestone_code: str = Path(..., regex="^M[0-9]+$"),
    request: CreateArtifactRequest = Body(...),
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Create an artifact for a milestone.
    """
    artifact = await service.create_milestone_artifact(
        str(current_user.id),
        milestone_code,
        request.name,
        request.artifact_type,
        request.content,
        request.storage_path
    )
    
    if not artifact:
        raise HTTPException(status_code=400, detail="Failed to create artifact")
    
    return {
        "success": True,
        "artifact_id": str(artifact.id),
        "name": artifact.name,
        "type": artifact.artifact_type
    }


@router.get("/artifacts/")
async def get_user_artifacts(
    milestone_code: Optional[str] = Query(None, regex="^M[0-9]+$"),
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get all artifacts for the current user.
    
    Optionally filter by milestone code.
    """
    artifacts = await service.get_user_artifacts(
        str(current_user.id),
        milestone_code
    )
    
    return {
        "artifacts": [
            {
                "id": str(a.id),
                "name": a.name,
                "type": a.artifact_type,
                "created_at": a.created_at.isoformat(),
                "milestone_code": milestone_code
            }
            for a in artifacts
        ]
    }


# Analytics endpoints

@router.get("/analytics/user", response_model=MilestoneAnalyticsResponse)
async def get_user_analytics(
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive analytics for the current user's milestone journey.
    """
    analytics = await service.get_user_analytics(str(current_user.id))
    return MilestoneAnalyticsResponse(**analytics)


@router.get("/analytics/milestone/{milestone_code}")
async def get_milestone_statistics(
    milestone_code: str = Path(..., regex="^M[0-9]+$"),
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated statistics for a specific milestone.
    """
    stats = await service.get_milestone_statistics(milestone_code)
    return stats


@router.get("/leaderboard")
async def get_leaderboard(
    leaderboard_type: str = Query("weekly", regex="^(weekly|monthly|all_time)$"),
    limit: int = Query(10, ge=1, le=100),
    redis: RedisMCPClient = Depends(get_redis_client),
    current_user: User = Depends(get_current_user)
):
    """
    Get milestone completion leaderboard.
    """
    cache_service = MilestoneCacheService(redis)
    leaderboard = await cache_service.get_leaderboard(leaderboard_type, limit)
    
    # Get current user's rank
    user_rank = None
    for entry in leaderboard:
        if entry["user_id"] == str(current_user.id):
            user_rank = entry["rank"]
            break
    
    return {
        "leaderboard": leaderboard,
        "current_user_rank": user_rank,
        "type": leaderboard_type
    }


# Admin endpoints (requires admin role)

@router.post("/initialize/{user_id}")
async def initialize_user_milestones(
    user_id: str,
    service: MilestoneService = Depends(get_milestone_service),
    current_user: User = Depends(get_current_user)
):
    """
    Initialize milestones for a user (Admin only).
    """
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    milestones = await service.initialize_user_milestones(user_id)
    
    return {
        "success": True,
        "message": f"Initialized {len(milestones)} milestones for user {user_id}"
    }


@router.delete("/cache/user/{user_id}")
async def clear_user_cache(
    user_id: str,
    redis: RedisMCPClient = Depends(get_redis_client),
    current_user: User = Depends(get_current_user)
):
    """
    Clear all cached data for a user (Admin only).
    """
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cache_service = MilestoneCacheService(redis)
    success = await cache_service.invalidate_user_cache(user_id)
    
    return {
        "success": success,
        "message": f"Cache cleared for user {user_id}"
    }


@router.get("/cache/stats")
async def get_cache_statistics(
    redis: RedisMCPClient = Depends(get_redis_client),
    current_user: User = Depends(get_current_user)
):
    """
    Get cache performance statistics (Admin only).
    """
    # Check admin permission
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cache_service = MilestoneCacheService(redis)
    stats = await cache_service.get_cache_stats()
    
    return stats