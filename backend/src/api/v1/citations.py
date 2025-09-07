"""
Citation API endpoints for managing citations, verification, and accuracy tracking.

This module provides RESTful API endpoints for the citation system including
CRUD operations, verification, search, and accuracy reporting.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ...models import get_db
from ...models.citation import (
    SourceType, VerificationStatus, ContentType,
    FeedbackType, MetricType
)
from ...services.citation_service import (
    CitationService, CitationCreate, CitationUpdate,
    CitationVerifyRequest, AccuracyFeedback, CitationSearchParams
)
from ...core.auth import get_current_user, require_auth
from ...core.exceptions import (
    NotFoundError, ValidationError, ConflictError,
    ServiceUnavailableError
)
from ...infrastructure.mcp import PostgresMCP, PuppeteerMCP
from ...utils.cache import CacheManager

router = APIRouter(prefix="/api/v1/citations", tags=["citations"])


# Response models
class CitationResponse(BaseModel):
    """Citation response model."""
    id: str
    reference_id: str
    source_type: SourceType
    url: Optional[str]
    title: str
    authors: List[str]
    publication_date: Optional[datetime]
    access_date: datetime
    excerpt: Optional[str]
    metadata: Dict[str, Any]
    verification_status: VerificationStatus
    last_verified: Optional[datetime]
    accuracy_score: float
    relevance_score: float
    availability_score: float
    overall_quality_score: float
    usage_count: int
    formatted: str
    created_at: datetime
    updated_at: datetime


class CitationListResponse(BaseModel):
    """Citation list response model."""
    citations: List[CitationResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class VerificationResponse(BaseModel):
    """Verification response model."""
    citation_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    content_matched: Optional[bool]
    changes_detected: Dict[str, Any]
    screenshot_url: Optional[str]


class AccuracyReportResponse(BaseModel):
    """Accuracy report response model."""
    period: Dict[str, str]
    overall_accuracy: float
    accuracy_status: str
    accuracy_by_source: List[Dict[str, Any]]
    verification_statistics: List[Dict[str, Any]]
    citations_needing_attention: List[Dict[str, Any]]
    feedback_statistics: List[Dict[str, Any]]


class BatchCitationRequest(BaseModel):
    """Batch citation creation request."""
    citations: List[CitationCreate]


class BatchCitationResponse(BaseModel):
    """Batch citation creation response."""
    created: List[CitationResponse]
    failed: List[Dict[str, str]]
    total_created: int
    total_failed: int


# Dependency injection
def get_citation_service(
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
) -> CitationService:
    """Get citation service instance."""
    cache_manager = CacheManager()
    postgres_mcp = PostgresMCP()
    puppeteer_mcp = PuppeteerMCP()
    
    return CitationService(
        db=db,
        cache_manager=cache_manager,
        postgres_mcp=postgres_mcp,
        puppeteer_mcp=puppeteer_mcp
    )


@router.post("/", response_model=CitationResponse, status_code=status.HTTP_201_CREATED)
async def create_citation(
    citation_data: CitationCreate,
    auto_verify: bool = Query(True, description="Automatically verify citation after creation"),
    current_user: dict = Depends(get_current_user),
    service: CitationService = Depends(get_citation_service)
):
    """
    Create a new citation.
    
    Creates a new citation with optional automatic verification.
    Requires authentication.
    """
    try:
        citation = await service.create_citation(
            citation_data=citation_data,
            user_id=UUID(current_user['id']),
            auto_verify=auto_verify
        )
        
        return CitationResponse(
            id=str(citation.id),
            reference_id=citation.reference_id,
            source_type=citation.source_type,
            url=citation.url,
            title=citation.title,
            authors=citation.authors,
            publication_date=citation.publication_date,
            access_date=citation.access_date,
            excerpt=citation.excerpt,
            metadata=citation.metadata,
            verification_status=citation.verification_status,
            last_verified=citation.last_verified,
            accuracy_score=citation.accuracy_score,
            relevance_score=citation.relevance_score,
            availability_score=citation.availability_score,
            overall_quality_score=citation.overall_quality_score,
            usage_count=citation.usage_count,
            formatted=citation.formatted_citation,
            created_at=citation.created_at,
            updated_at=citation.updated_at
        )
        
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{citation_id}", response_model=CitationResponse)
async def get_citation(
    citation_id: UUID,
    include_usage: bool = Query(False, description="Include usage statistics"),
    service: CitationService = Depends(get_citation_service)
):
    """
    Get a citation by ID.
    
    Retrieves detailed information about a specific citation.
    """
    try:
        citation = await service.get_citation(
            citation_id=citation_id,
            include_usage=include_usage
        )
        
        return CitationResponse(
            id=str(citation.id),
            reference_id=citation.reference_id,
            source_type=citation.source_type,
            url=citation.url,
            title=citation.title,
            authors=citation.authors,
            publication_date=citation.publication_date,
            access_date=citation.access_date,
            excerpt=citation.excerpt,
            metadata=citation.metadata,
            verification_status=citation.verification_status,
            last_verified=citation.last_verified,
            accuracy_score=citation.accuracy_score,
            relevance_score=citation.relevance_score,
            availability_score=citation.availability_score,
            overall_quality_score=citation.overall_quality_score,
            usage_count=citation.usage_count,
            formatted=citation.formatted_citation,
            created_at=citation.created_at,
            updated_at=citation.updated_at
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{citation_id}", response_model=CitationResponse)
async def update_citation(
    citation_id: UUID,
    update_data: CitationUpdate,
    current_user: dict = Depends(get_current_user),
    service: CitationService = Depends(get_citation_service)
):
    """
    Update a citation.
    
    Updates citation information. Requires authentication.
    """
    try:
        citation = await service.update_citation(
            citation_id=citation_id,
            update_data=update_data,
            user_id=UUID(current_user['id'])
        )
        
        return CitationResponse(
            id=str(citation.id),
            reference_id=citation.reference_id,
            source_type=citation.source_type,
            url=citation.url,
            title=citation.title,
            authors=citation.authors,
            publication_date=citation.publication_date,
            access_date=citation.access_date,
            excerpt=citation.excerpt,
            metadata=citation.metadata,
            verification_status=citation.verification_status,
            last_verified=citation.last_verified,
            accuracy_score=citation.accuracy_score,
            relevance_score=citation.relevance_score,
            availability_score=citation.availability_score,
            overall_quality_score=citation.overall_quality_score,
            usage_count=citation.usage_count,
            formatted=citation.formatted_citation,
            created_at=citation.created_at,
            updated_at=citation.updated_at
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{citation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_citation(
    citation_id: UUID,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Delete a citation.
    
    Soft deletes a citation by marking it as inactive. Requires authentication.
    """
    try:
        citation = db.get(Citation, citation_id)
        if not citation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citation not found")
        
        citation.is_active = False
        citation.is_archived = True
        db.commit()
        
        return None
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{citation_id}/verify", response_model=VerificationResponse)
async def verify_citation(
    citation_id: UUID,
    request: CitationVerifyRequest = CitationVerifyRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user),
    service: CitationService = Depends(get_citation_service)
):
    """
    Verify a citation.
    
    Triggers verification of a citation using Puppeteer MCP.
    Requires authentication.
    """
    try:
        verification_log = await service.verify_citation(
            citation_id=citation_id,
            user_id=UUID(current_user['id']),
            request=request
        )
        
        if not verification_log:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "Citation recently verified, skipping"}
            )
        
        return VerificationResponse(
            citation_id=str(citation_id),
            status=verification_log.status,
            started_at=verification_log.started_at,
            completed_at=verification_log.completed_at,
            duration_ms=verification_log.duration_ms,
            content_matched=verification_log.content_matched,
            changes_detected=verification_log.changes_detected or {},
            screenshot_url=verification_log.screenshot_url
        )
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{citation_id}/verification-status")
async def get_verification_status(
    citation_id: UUID,
    service: CitationService = Depends(get_citation_service)
):
    """
    Get verification status of a citation.
    
    Returns the current verification status and last verification details.
    """
    try:
        citation = await service.get_citation(citation_id)
        
        return {
            "citation_id": str(citation_id),
            "verification_status": citation.verification_status,
            "last_verified": citation.last_verified,
            "verification_attempts": citation.verification_attempts,
            "needs_verification": citation.needs_verification,
            "screenshot_url": citation.screenshot_url
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{citation_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_accuracy_feedback(
    citation_id: UUID,
    feedback: AccuracyFeedback,
    current_user: dict = Depends(get_current_user),
    service: CitationService = Depends(get_citation_service)
):
    """
    Submit accuracy feedback for a citation.
    
    Allows users to provide feedback on citation accuracy, relevance, and availability.
    Requires authentication.
    """
    try:
        tracking = await service.submit_accuracy_feedback(
            citation_id=citation_id,
            feedback=feedback,
            evaluator_id=UUID(current_user['id'])
        )
        
        return {
            "id": str(tracking.id),
            "citation_id": str(tracking.citation_id),
            "metric_type": tracking.metric_type,
            "score": tracking.score,
            "feedback_type": tracking.feedback_type,
            "evaluated_at": tracking.evaluated_at
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{citation_id}/accuracy")
async def get_citation_accuracy(
    citation_id: UUID,
    service: CitationService = Depends(get_citation_service)
):
    """
    Get accuracy metrics for a citation.
    
    Returns detailed accuracy metrics including scores and feedback summary.
    """
    try:
        citation = await service.get_citation(citation_id)
        
        return {
            "citation_id": str(citation_id),
            "accuracy_score": citation.accuracy_score * 100,
            "relevance_score": citation.relevance_score * 100,
            "availability_score": citation.availability_score * 100,
            "overall_quality_score": citation.overall_quality_score * 100,
            "status": "green" if citation.overall_quality_score >= 0.95 else "yellow" if citation.overall_quality_score >= 0.90 else "red"
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/search", response_model=CitationListResponse)
async def search_citations(
    query: Optional[str] = Query(None, description="Search query"),
    source_types: Optional[List[SourceType]] = Query(None, description="Filter by source types"),
    verification_status: Optional[VerificationStatus] = Query(None, description="Filter by verification status"),
    min_quality_score: float = Query(0.0, ge=0.0, le=1.0, description="Minimum quality score"),
    max_age_days: Optional[int] = Query(None, gt=0, description="Maximum age in days"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    service: CitationService = Depends(get_citation_service)
):
    """
    Search citations with filters.
    
    Provides comprehensive search functionality with multiple filter options.
    """
    try:
        search_params = CitationSearchParams(
            query=query,
            source_types=source_types or [],
            verification_status=verification_status,
            min_quality_score=min_quality_score,
            max_age_days=max_age_days,
            limit=page_size,
            offset=(page - 1) * page_size
        )
        
        citations, total_count = await service.search_citations(search_params)
        
        return CitationListResponse(
            citations=[
                CitationResponse(
                    id=str(c.id),
                    reference_id=c.reference_id,
                    source_type=c.source_type,
                    url=c.url,
                    title=c.title,
                    authors=c.authors,
                    publication_date=c.publication_date,
                    access_date=c.access_date,
                    excerpt=c.excerpt,
                    metadata=c.metadata,
                    verification_status=c.verification_status,
                    last_verified=c.last_verified,
                    accuracy_score=c.accuracy_score,
                    relevance_score=c.relevance_score,
                    availability_score=c.availability_score,
                    overall_quality_score=c.overall_quality_score,
                    usage_count=c.usage_count,
                    formatted=c.formatted_citation,
                    created_at=c.created_at,
                    updated_at=c.updated_at
                )
                for c in citations
            ],
            total=total_count,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total_count,
            has_prev=page > 1
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/batch", response_model=BatchCitationResponse, status_code=status.HTTP_201_CREATED)
async def batch_create_citations(
    request: BatchCitationRequest,
    current_user: dict = Depends(get_current_user),
    service: CitationService = Depends(get_citation_service)
):
    """
    Create multiple citations in batch.
    
    Efficiently creates multiple citations in a single request.
    Requires authentication.
    """
    try:
        created_citations = await service.batch_create_citations(
            citations_data=request.citations,
            user_id=UUID(current_user['id'])
        )
        
        created_responses = [
            CitationResponse(
                id=str(c.id),
                reference_id=c.reference_id,
                source_type=c.source_type,
                url=c.url,
                title=c.title,
                authors=c.authors,
                publication_date=c.publication_date,
                access_date=c.access_date,
                excerpt=c.excerpt,
                metadata=c.metadata,
                verification_status=c.verification_status,
                last_verified=c.last_verified,
                accuracy_score=c.accuracy_score,
                relevance_score=c.relevance_score,
                availability_score=c.availability_score,
                overall_quality_score=c.overall_quality_score,
                usage_count=c.usage_count,
                formatted=c.formatted_citation,
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in created_citations
        ]
        
        return BatchCitationResponse(
            created=created_responses,
            failed=[],
            total_created=len(created_citations),
            total_failed=len(request.citations) - len(created_citations)
        )
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/verify-batch", status_code=status.HTTP_202_ACCEPTED)
async def batch_verify_citations(
    citation_ids: List[UUID],
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    service: CitationService = Depends(get_citation_service)
):
    """
    Batch verify multiple citations.
    
    Triggers verification for multiple citations in the background.
    Requires authentication.
    """
    async def verify_citations_task():
        for citation_id in citation_ids:
            try:
                await service.verify_citation(
                    citation_id=citation_id,
                    user_id=UUID(current_user['id'])
                )
            except Exception as e:
                # Log error but continue with other citations
                print(f"Failed to verify citation {citation_id}: {e}")
    
    background_tasks.add_task(verify_citations_task)
    
    return {
        "message": f"Verification started for {len(citation_ids)} citations",
        "citation_ids": [str(cid) for cid in citation_ids]
    }


@router.get("/stale")
async def get_stale_citations(
    days_threshold: int = Query(30, gt=0, description="Days since last verification"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum citations to return"),
    service: CitationService = Depends(get_citation_service)
):
    """
    Get citations that need reverification.
    
    Returns citations that are stale or require reverification.
    """
    try:
        stale_citations = await service.get_stale_citations(
            days_threshold=days_threshold,
            limit=limit
        )
        
        return {
            "total": len(stale_citations),
            "citations": [
                {
                    "id": str(c.id),
                    "reference_id": c.reference_id,
                    "url": c.url,
                    "title": c.title,
                    "verification_status": c.verification_status,
                    "last_verified": c.last_verified,
                    "days_since_verification": (datetime.utcnow() - c.last_verified).days if c.last_verified else None
                }
                for c in stale_citations
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/accuracy-report", response_model=AccuracyReportResponse)
async def get_accuracy_report(
    start_date: Optional[datetime] = Query(None, description="Report start date"),
    end_date: Optional[datetime] = Query(None, description="Report end date"),
    service: CitationService = Depends(get_citation_service)
):
    """
    Get system-wide accuracy report.
    
    Generates comprehensive accuracy report with metrics and statistics.
    """
    try:
        report = await service.get_accuracy_report(
            start_date=start_date,
            end_date=end_date
        )
        
        return AccuracyReportResponse(**report)
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/accuracy-alerts")
async def get_accuracy_alerts(
    threshold: float = Query(0.95, ge=0.0, le=1.0, description="Accuracy threshold"),
    service: CitationService = Depends(get_citation_service)
):
    """
    Get accuracy alerts.
    
    Returns citations with accuracy below the specified threshold.
    """
    try:
        search_params = CitationSearchParams(
            min_quality_score=0.0,
            limit=100,
            offset=0
        )
        
        citations, _ = await service.search_citations(search_params)
        
        alerts = [
            {
                "id": str(c.id),
                "reference_id": c.reference_id,
                "title": c.title,
                "overall_quality_score": c.overall_quality_score * 100,
                "alert_level": "critical" if c.overall_quality_score < 0.90 else "warning"
            }
            for c in citations
            if c.overall_quality_score < threshold
        ]
        
        return {
            "threshold": threshold * 100,
            "total_alerts": len(alerts),
            "alerts": alerts
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))