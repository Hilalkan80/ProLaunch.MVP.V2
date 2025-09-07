"""
Milestone Dependencies API Endpoints

RESTful API for managing milestone dependencies, validation,
and dependency graph operations.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.auth import get_current_user, require_admin
from ...models.user import User
from ...services.dependency_manager import DependencyManager, DependencyType
from ...services.milestone_cache import MilestoneCacheService
from ...infrastructure.redis.redis_mcp import RedisMCPClient
from ...core.exceptions import (
    CircularDependencyError,
    DependencyValidationError,
    MilestoneNotFoundError,
    InsufficientPermissionsError
)
from ...schemas.milestone import (
    DependencyCreate,
    DependencyResponse,
    DependencyValidationResponse,
    DependencyChainResponse,
    DependencyGraphResponse,
    UnlockedMilestonesResponse
)

router = APIRouter(prefix="/dependencies", tags=["dependencies"])


async def get_dependency_manager(
    db: AsyncSession = Depends(get_db)
) -> DependencyManager:
    """Dependency injection for DependencyManager."""
    cache_service = MilestoneCacheService(db, RedisMCPClient())
    return DependencyManager(db, cache_service)


# Admin endpoints for managing dependencies

@router.post(
    "/add",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)]
)
async def add_dependency(
    milestone_code: str = Body(..., description="Milestone that has the dependency"),
    dependency_code: str = Body(..., description="Milestone that must be completed first"),
    is_required: bool = Body(True, description="Whether dependency is mandatory"),
    minimum_completion: float = Body(100.0, ge=0, le=100, description="Minimum completion percentage"),
    dependency_type: str = Body(DependencyType.REQUIRED, description="Type of dependency"),
    conditions: Optional[Dict[str, Any]] = Body(None, description="Conditional requirements"),
    manager: DependencyManager = Depends(get_dependency_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a dependency between milestones.
    
    Admin only endpoint for creating milestone dependencies with validation.
    """
    # Get milestone IDs from codes
    from ...models.milestone import Milestone
    from sqlalchemy import select
    
    # Get milestone by code
    stmt = select(Milestone).where(Milestone.code == milestone_code)
    result = await db.execute(stmt)
    milestone = result.scalar_one_or_none()
    
    if not milestone:
        raise MilestoneNotFoundError(milestone_code)
    
    # Get dependency by code
    stmt = select(Milestone).where(Milestone.code == dependency_code)
    result = await db.execute(stmt)
    dependency = result.scalar_one_or_none()
    
    if not dependency:
        raise MilestoneNotFoundError(dependency_code)
    
    # Add the dependency
    success, message = await manager.add_dependency(
        str(milestone.id),
        str(dependency.id),
        is_required,
        minimum_completion,
        dependency_type,
        conditions
    )
    
    if not success:
        if "circular" in message.lower():
            raise CircularDependencyError()
        raise DependencyValidationError(message)
    
    return {
        "success": success,
        "message": message,
        "dependency": {
            "milestone": milestone_code,
            "depends_on": dependency_code,
            "is_required": is_required,
            "minimum_completion": minimum_completion,
            "type": dependency_type
        }
    }


@router.delete(
    "/remove",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_admin)]
)
async def remove_dependency(
    milestone_code: str = Query(..., description="Milestone that has the dependency"),
    dependency_code: str = Query(..., description="Dependency to remove"),
    manager: DependencyManager = Depends(get_dependency_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a dependency between milestones.
    
    Admin only endpoint for removing milestone dependencies.
    """
    from ...models.milestone import Milestone
    from sqlalchemy import select
    
    # Get milestone IDs from codes
    stmt = select(Milestone.id).where(Milestone.code == milestone_code)
    result = await db.execute(stmt)
    milestone_id = result.scalar_one_or_none()
    
    if not milestone_id:
        raise MilestoneNotFoundError(milestone_code)
    
    stmt = select(Milestone.id).where(Milestone.code == dependency_code)
    result = await db.execute(stmt)
    dependency_id = result.scalar_one_or_none()
    
    if not dependency_id:
        raise MilestoneNotFoundError(dependency_code)
    
    # Remove the dependency
    success, message = await manager.remove_dependency(
        str(milestone_id),
        str(dependency_id)
    )
    
    if not success:
        raise DependencyValidationError(message)
    
    return {
        "success": success,
        "message": message,
        "removed": {
            "milestone": milestone_code,
            "dependency": dependency_code
        }
    }


# User endpoints for viewing dependencies

@router.get(
    "/validate/{milestone_code}",
    response_model=DependencyValidationResponse
)
async def validate_dependencies(
    milestone_code: str,
    check_conditions: bool = Query(True, description="Check conditional dependencies"),
    current_user: User = Depends(get_current_user),
    manager: DependencyManager = Depends(get_dependency_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate if user has met all dependencies for a milestone.
    
    Returns validation status and any unmet dependencies.
    """
    from ...models.milestone import Milestone
    from sqlalchemy import select
    
    # Get milestone by code
    stmt = select(Milestone).where(Milestone.code == milestone_code)
    result = await db.execute(stmt)
    milestone = result.scalar_one_or_none()
    
    if not milestone:
        raise MilestoneNotFoundError(milestone_code)
    
    # Validate dependencies
    all_met, unmet_dependencies = await manager.validate_dependencies(
        str(current_user.id),
        str(milestone.id),
        check_conditions
    )
    
    return DependencyValidationResponse(
        milestone_code=milestone_code,
        all_dependencies_met=all_met,
        unmet_dependencies=unmet_dependencies,
        can_start=all_met
    )


@router.get(
    "/chain/{milestone_code}",
    response_model=DependencyChainResponse
)
async def get_dependency_chain(
    milestone_code: str,
    include_optional: bool = Query(False, description="Include optional dependencies"),
    current_user: User = Depends(get_current_user),
    manager: DependencyManager = Depends(get_dependency_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the complete dependency chain for a milestone.
    
    Returns ordered list of milestones that must be completed.
    """
    from ...models.milestone import Milestone
    from sqlalchemy import select
    
    # Get milestone by code
    stmt = select(Milestone).where(Milestone.code == milestone_code)
    result = await db.execute(stmt)
    milestone = result.scalar_one_or_none()
    
    if not milestone:
        raise MilestoneNotFoundError(milestone_code)
    
    # Get dependency chain
    chain = await manager.get_dependency_chain(
        str(milestone.id),
        include_optional
    )
    
    # Check completion status for each dependency
    from ...models.milestone import UserMilestone, MilestoneStatus
    
    for dep in chain:
        stmt = select(UserMilestone).where(
            UserMilestone.user_id == current_user.id,
            UserMilestone.milestone_id == UUID(dep["milestone_id"])
        )
        result = await db.execute(stmt)
        user_milestone = result.scalar_one_or_none()
        
        if user_milestone:
            dep["status"] = user_milestone.status
            dep["completion_percentage"] = user_milestone.completion_percentage
        else:
            dep["status"] = MilestoneStatus.LOCKED
            dep["completion_percentage"] = 0
    
    return DependencyChainResponse(
        milestone_code=milestone_code,
        total_dependencies=len(chain),
        dependency_chain=chain
    )


@router.post(
    "/process-completion",
    response_model=UnlockedMilestonesResponse
)
async def process_milestone_completion(
    milestone_code: str = Body(..., description="Completed milestone code"),
    current_user: User = Depends(get_current_user),
    manager: DependencyManager = Depends(get_dependency_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Process milestone completion and auto-unlock dependent milestones.
    
    Returns list of newly unlocked milestones.
    """
    from ...models.milestone import Milestone
    from sqlalchemy import select
    
    # Get milestone by code
    stmt = select(Milestone).where(Milestone.code == milestone_code)
    result = await db.execute(stmt)
    milestone = result.scalar_one_or_none()
    
    if not milestone:
        raise MilestoneNotFoundError(milestone_code)
    
    # Process completion and auto-unlock
    newly_unlocked = await manager.process_milestone_completion(
        str(current_user.id),
        str(milestone.id)
    )
    
    return UnlockedMilestonesResponse(
        completed_milestone=milestone_code,
        newly_unlocked_count=len(newly_unlocked),
        newly_unlocked=newly_unlocked
    )


@router.get(
    "/conditional/{milestone_code}",
    response_model=Dict[str, Any]
)
async def evaluate_conditional_dependencies(
    milestone_code: str,
    current_user: User = Depends(get_current_user),
    manager: DependencyManager = Depends(get_dependency_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluate conditional dependencies for a milestone.
    
    Returns evaluation results for all conditional dependencies.
    """
    from ...models.milestone import Milestone
    from sqlalchemy import select
    
    # Get milestone by code
    stmt = select(Milestone).where(Milestone.code == milestone_code)
    result = await db.execute(stmt)
    milestone = result.scalar_one_or_none()
    
    if not milestone:
        raise MilestoneNotFoundError(milestone_code)
    
    # Evaluate conditional dependencies
    evaluation = await manager.evaluate_conditional_dependencies(
        str(current_user.id),
        str(milestone.id)
    )
    
    return evaluation


# Admin endpoints for dependency analysis

@router.get(
    "/graph",
    response_model=DependencyGraphResponse,
    dependencies=[Depends(require_admin)]
)
async def get_dependency_graph(
    manager: DependencyManager = Depends(get_dependency_manager)
):
    """
    Get visualization-ready dependency graph.
    
    Admin only endpoint that returns the complete dependency graph
    structure for visualization.
    """
    graph_data = await manager.visualize_dependency_graph()
    
    return DependencyGraphResponse(
        nodes=graph_data["nodes"],
        edges=graph_data["edges"],
        statistics=graph_data["statistics"]
    )


@router.get(
    "/check-cycles",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_admin)]
)
async def check_circular_dependencies(
    manager: DependencyManager = Depends(get_dependency_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Check for circular dependencies in the system.
    
    Admin only endpoint that detects and reports any circular
    dependency chains.
    """
    cycles = await manager.check_circular_dependencies()
    
    if cycles:
        # Convert milestone IDs to codes for readability
        from ...models.milestone import Milestone
        from sqlalchemy import select
        
        readable_cycles = []
        for cycle in cycles:
            readable_cycle = []
            for milestone_id in cycle:
                stmt = select(Milestone.code).where(Milestone.id == UUID(milestone_id))
                result = await db.execute(stmt)
                code = result.scalar_one_or_none()
                readable_cycle.append(code or milestone_id)
            readable_cycles.append(readable_cycle)
        
        return {
            "has_circular_dependencies": True,
            "cycles_found": len(readable_cycles),
            "cycles": readable_cycles
        }
    
    return {
        "has_circular_dependencies": False,
        "cycles_found": 0,
        "cycles": []
    }


@router.get(
    "/statistics",
    response_model=Dict[str, Any],
    dependencies=[Depends(require_admin)]
)
async def get_dependency_statistics(
    manager: DependencyManager = Depends(get_dependency_manager)
):
    """
    Get comprehensive dependency system statistics.
    
    Admin only endpoint that provides detailed statistics about
    the dependency system.
    """
    stats = await manager.get_dependency_statistics()
    
    return stats


@router.post(
    "/bulk-validate",
    response_model=Dict[str, Any]
)
async def bulk_validate_dependencies(
    milestone_codes: List[str] = Body(..., description="List of milestone codes to validate"),
    current_user: User = Depends(get_current_user),
    manager: DependencyManager = Depends(get_dependency_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate dependencies for multiple milestones at once.
    
    Efficient bulk validation for UI performance.
    """
    from ...models.milestone import Milestone
    from sqlalchemy import select
    
    results = {}
    
    for code in milestone_codes:
        # Get milestone by code
        stmt = select(Milestone).where(Milestone.code == code)
        result = await db.execute(stmt)
        milestone = result.scalar_one_or_none()
        
        if milestone:
            all_met, unmet = await manager.validate_dependencies(
                str(current_user.id),
                str(milestone.id),
                check_conditions=True
            )
            
            results[code] = {
                "can_start": all_met,
                "unmet_count": len(unmet),
                "unmet_dependencies": [d["milestone_code"] for d in unmet]
            }
        else:
            results[code] = {
                "error": f"Milestone {code} not found"
            }
    
    return {
        "validations": results,
        "total_validated": len(milestone_codes)
    }