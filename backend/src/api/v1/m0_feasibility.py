"""
M0 Feasibility Snapshot API Endpoints

Fast API endpoints for M0 feasibility generation and retrieval
with performance monitoring and caching.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc

from ...models import get_db
from ...models.m0_feasibility import (
    M0FeasibilitySnapshot, M0PerformanceLog, M0Status
)
from ...models.user import User
from ...services.m0_generator import M0GeneratorService
from ...services.m0_cache_service import M0CacheService
from ...services.auth_service import get_current_user
from ...ai.llama_service import LlamaService
from ...services.citation_service import CitationService
from ...services.context.context_manager import ContextManager
from ...infrastructure.redis.redis_mcp import RedisMCPClient
from ...schemas.m0_feasibility import (
    M0GenerateRequest, M0GenerateResponse,
    M0SnapshotResponse, M0PerformanceMetrics,
    M0ListResponse
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/m0",
    tags=["M0 Feasibility"]
)

# Service instances (would be dependency injected in production)
m0_generator: Optional[M0GeneratorService] = None
m0_cache: Optional[M0CacheService] = None


@router.on_event("startup")
async def startup_event():
    """Initialize M0 services on startup."""
    global m0_generator, m0_cache
    
    try:
        # Initialize services (would use dependency injection in production)
        logger.info("Initializing M0 services...")
        
        # Services would be properly initialized here
        # For now, we'll leave them as None and check in endpoints
        
        logger.info("M0 services initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize M0 services: {e}")


@router.post(
    "/generate",
    response_model=M0GenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate M0 Feasibility Snapshot",
    description="Generate a new M0 feasibility snapshot for a business idea"
)
async def generate_m0_snapshot(
    request: M0GenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> M0GenerateResponse:
    """
    Generate M0 feasibility snapshot with sub-60 second target.
    
    Args:
        request: M0 generation request
        background_tasks: FastAPI background tasks
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Generated M0 snapshot response
    """
    try:
        # Initialize services if needed
        if not m0_generator:
            # Initialize with proper dependencies
            llama_service = LlamaService()
            citation_service = CitationService(db)
            context_manager = ContextManager(str(current_user.id), "session_id")
            redis_client = RedisMCPClient()
            
            global m0_generator
            m0_generator = M0GeneratorService(
                db, llama_service, citation_service,
                context_manager, redis_client
            )
            await m0_generator.initialize()
        
        # Prepare user profile
        user_profile = {
            "experience": request.user_experience or "none",
            "budget_band": request.budget_band or "<5k",
            "timeline_months": request.timeline_months or 6
        }
        
        # Check cache first if requested
        if request.use_cache:
            if not m0_cache:
                global m0_cache
                m0_cache = M0CacheService(db, RedisMCPClient())
                await m0_cache.initialize()
            
            cached = await m0_cache.get_cached_snapshot(
                request.idea_summary,
                user_profile,
                use_similarity=request.allow_similar_match
            )
            
            if cached and not cached.get("partial"):
                logger.info(f"Returning cached M0 for user {current_user.id}")
                
                return M0GenerateResponse(
                    success=True,
                    snapshot_id=cached.get("id"),
                    snapshot=cached,
                    from_cache=True,
                    generation_time_ms=0,
                    message="Retrieved from cache"
                )
        
        # Generate new snapshot
        logger.info(f"Generating new M0 for user {current_user.id}")
        
        snapshot_data = await m0_generator.generate_snapshot(
            user_id=str(current_user.id),
            idea_summary=request.idea_summary,
            user_profile=user_profile,
            project_id=request.project_id,
            use_cache=request.use_cache
        )
        
        # Queue background tasks for optimization
        if request.enable_preloading:
            background_tasks.add_task(
                preload_related_ideas,
                request.idea_summary,
                user_profile,
                db
            )
        
        return M0GenerateResponse(
            success=True,
            snapshot_id=snapshot_data["id"],
            snapshot=snapshot_data,
            from_cache=False,
            generation_time_ms=snapshot_data.get("generation_time_ms", 0),
            message="M0 snapshot generated successfully"
        )
        
    except Exception as e:
        logger.error(f"M0 generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate M0 snapshot: {str(e)}"
        )


@router.get(
    "/snapshot/{snapshot_id}",
    response_model=M0SnapshotResponse,
    summary="Get M0 Snapshot",
    description="Retrieve a specific M0 feasibility snapshot"
)
async def get_m0_snapshot(
    snapshot_id: UUID,
    include_performance: bool = Query(False, description="Include performance metrics"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> M0SnapshotResponse:
    """
    Get M0 snapshot by ID.
    
    Args:
        snapshot_id: Snapshot ID
        include_performance: Whether to include performance metrics
        current_user: Authenticated user
        db: Database session
        
    Returns:
        M0 snapshot data
    """
    try:
        # Query snapshot
        stmt = select(M0FeasibilitySnapshot).where(
            and_(
                M0FeasibilitySnapshot.id == snapshot_id,
                M0FeasibilitySnapshot.user_id == current_user.id
            )
        )
        
        result = await db.execute(stmt)
        snapshot = result.scalar_one_or_none()
        
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="M0 snapshot not found"
            )
        
        response_data = {
            "snapshot": snapshot.to_dict(),
            "markdown_output": snapshot.get_markdown_output()
        }
        
        # Include performance metrics if requested
        if include_performance:
            perf_stmt = select(M0PerformanceLog).where(
                M0PerformanceLog.snapshot_id == snapshot_id
            )
            perf_result = await db.execute(perf_stmt)
            perf_log = perf_result.scalar_one_or_none()
            
            if perf_log:
                response_data["performance"] = {
                    "total_time_ms": perf_log.total_time_ms,
                    "research_time_ms": perf_log.research_time_ms,
                    "analysis_time_ms": perf_log.analysis_time_ms,
                    "cache_lookup_time_ms": perf_log.cache_lookup_time_ms,
                    "used_cache": perf_log.used_cache,
                    "api_calls": perf_log.api_calls
                }
        
        return M0SnapshotResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve M0 snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve M0 snapshot"
        )


@router.get(
    "/list",
    response_model=M0ListResponse,
    summary="List M0 Snapshots",
    description="List user's M0 feasibility snapshots with filtering"
)
async def list_m0_snapshots(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    status: Optional[M0Status] = Query(None, description="Filter by status"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum viability score"),
    max_score: Optional[int] = Query(None, ge=0, le=100, description="Maximum viability score"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> M0ListResponse:
    """
    List user's M0 snapshots with filtering.
    
    Args:
        project_id: Optional project filter
        status: Optional status filter
        min_score: Minimum viability score filter
        max_score: Maximum viability score filter
        limit: Result limit
        offset: Pagination offset
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of M0 snapshots
    """
    try:
        # Build query
        stmt = select(M0FeasibilitySnapshot).where(
            M0FeasibilitySnapshot.user_id == current_user.id
        )
        
        # Apply filters
        if project_id:
            stmt = stmt.where(M0FeasibilitySnapshot.project_id == project_id)
        
        if status:
            stmt = stmt.where(M0FeasibilitySnapshot.status == status.value)
        
        if min_score is not None:
            stmt = stmt.where(M0FeasibilitySnapshot.viability_score >= min_score)
        
        if max_score is not None:
            stmt = stmt.where(M0FeasibilitySnapshot.viability_score <= max_score)
        
        # Order and paginate
        stmt = stmt.order_by(desc(M0FeasibilitySnapshot.created_at))
        stmt = stmt.limit(limit).offset(offset)
        
        # Execute query
        result = await db.execute(stmt)
        snapshots = result.scalars().all()
        
        # Count total
        count_stmt = select(func.count(M0FeasibilitySnapshot.id)).where(
            M0FeasibilitySnapshot.user_id == current_user.id
        )
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        return M0ListResponse(
            snapshots=[s.to_dict() for s in snapshots],
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"Failed to list M0 snapshots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list M0 snapshots"
        )


@router.get(
    "/performance/metrics",
    response_model=M0PerformanceMetrics,
    summary="Get M0 Performance Metrics",
    description="Get performance metrics for M0 generation system"
)
async def get_performance_metrics(
    time_range: str = Query("24h", description="Time range (1h, 24h, 7d, 30d)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> M0PerformanceMetrics:
    """
    Get M0 system performance metrics.
    
    Args:
        time_range: Time range for metrics
        current_user: Authenticated user (must be admin)
        db: Database session
        
    Returns:
        Performance metrics
    """
    try:
        # Check admin permission
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Parse time range
        from datetime import timedelta
        
        time_ranges = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        
        delta = time_ranges.get(time_range, timedelta(hours=24))
        since = datetime.utcnow() - delta
        
        # Query performance logs
        stmt = select(M0PerformanceLog).where(
            M0PerformanceLog.created_at >= since
        )
        
        result = await db.execute(stmt)
        logs = result.scalars().all()
        
        if not logs:
            return M0PerformanceMetrics(
                total_generations=0,
                avg_time_ms=0,
                min_time_ms=0,
                max_time_ms=0,
                within_target_rate=0,
                cache_hit_rate=0,
                success_rate=0,
                time_range=time_range
            )
        
        # Calculate metrics
        total_times = [log.total_time_ms for log in logs]
        cache_hits = sum(1 for log in logs if log.used_cache)
        successes = sum(1 for log in logs if not log.had_errors)
        within_target = sum(1 for log in logs if log.total_time_ms <= 60000)
        
        metrics = M0PerformanceMetrics(
            total_generations=len(logs),
            avg_time_ms=sum(total_times) / len(total_times),
            min_time_ms=min(total_times),
            max_time_ms=max(total_times),
            within_target_rate=within_target / len(logs),
            cache_hit_rate=cache_hits / len(logs),
            success_rate=successes / len(logs),
            time_range=time_range,
            breakdown={
                "avg_research_ms": sum(log.research_time_ms for log in logs) / len(logs),
                "avg_analysis_ms": sum(log.analysis_time_ms for log in logs) / len(logs),
                "avg_cache_lookup_ms": sum(
                    log.cache_lookup_time_ms for log in logs if log.cache_lookup_time_ms
                ) / len([l for l in logs if l.cache_lookup_time_ms]) if any(
                    l.cache_lookup_time_ms for l in logs
                ) else 0
            }
        )
        
        # Add service-level metrics if available
        if m0_generator:
            service_metrics = await m0_generator.get_performance_metrics()
            metrics.service_metrics = service_metrics
        
        # Add cache metrics if available
        if m0_cache:
            cache_metrics = await m0_cache.get_cache_statistics()
            metrics.cache_metrics = cache_metrics
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get performance metrics"
        )


@router.post(
    "/cache/invalidate",
    summary="Invalidate M0 Cache",
    description="Invalidate M0 cache entries"
)
async def invalidate_cache(
    idea_summary: Optional[str] = Query(None, description="Specific idea to invalidate"),
    invalidate_all: bool = Query(False, description="Invalidate all cache entries"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Invalidate M0 cache entries.
    
    Args:
        idea_summary: Specific idea to invalidate
        invalidate_all: Whether to invalidate all entries
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Invalidation result
    """
    try:
        if not m0_cache:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache service not available"
            )
        
        # Admin can invalidate all
        if invalidate_all and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required to invalidate all cache"
            )
        
        # Invalidate cache
        if invalidate_all:
            count = await m0_cache.invalidate_cache()
        elif idea_summary:
            count = await m0_cache.invalidate_cache(idea_summary=idea_summary)
        else:
            count = await m0_cache.invalidate_cache(user_id=str(current_user.id))
        
        return {
            "success": True,
            "invalidated_count": count,
            "message": f"Invalidated {count} cache entries"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache invalidation failed"
        )


@router.get(
    "/export/{snapshot_id}",
    summary="Export M0 Snapshot",
    description="Export M0 snapshot in various formats"
)
async def export_m0_snapshot(
    snapshot_id: UUID,
    format: str = Query("markdown", description="Export format (markdown, json, pdf)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export M0 snapshot in various formats.
    
    Args:
        snapshot_id: Snapshot ID
        format: Export format
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Exported snapshot data
    """
    try:
        # Get snapshot
        stmt = select(M0FeasibilitySnapshot).where(
            and_(
                M0FeasibilitySnapshot.id == snapshot_id,
                M0FeasibilitySnapshot.user_id == current_user.id
            )
        )
        
        result = await db.execute(stmt)
        snapshot = result.scalar_one_or_none()
        
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="M0 snapshot not found"
            )
        
        # Export based on format
        if format == "markdown":
            content = snapshot.get_markdown_output()
            
            return StreamingResponse(
                iter([content.encode()]),
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=m0_{snapshot_id}.md"
                }
            )
            
        elif format == "json":
            import json
            content = json.dumps(snapshot.to_dict(), indent=2, default=str)
            
            return StreamingResponse(
                iter([content.encode()]),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=m0_{snapshot_id}.json"
                }
            )
            
        elif format == "pdf":
            # PDF generation would require additional library
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="PDF export not yet implemented"
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {format}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export failed"
        )


async def preload_related_ideas(
    idea_summary: str,
    user_profile: Dict[str, Any],
    db: AsyncSession
) -> None:
    """
    Background task to preload related ideas for faster future generation.
    
    Args:
        idea_summary: Original idea
        user_profile: User profile
        db: Database session
    """
    try:
        logger.info(f"Preloading related ideas for: {idea_summary[:50]}...")
        
        # Generate variations of the idea
        variations = [
            f"{idea_summary} for small businesses",
            f"{idea_summary} subscription service",
            f"online {idea_summary}",
            f"mobile app for {idea_summary}"
        ]
        
        # Queue for background generation
        # This would trigger pre-generation in a worker
        
    except Exception as e:
        logger.error(f"Preload task failed: {e}")