"""
Citation service for managing citations, verification, and accuracy tracking.

This service provides comprehensive citation management including creation,
verification, accuracy tracking, and search capabilities.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import redis
from pydantic import BaseModel, HttpUrl, Field, validator

from ..models.citation import (
    Citation, CitationUsage, AccuracyTracking,
    VerificationLog, CitationCollection,
    SourceType, VerificationStatus, ContentType,
    FeedbackType, MetricType
)
from ..core.exceptions import (
    NotFoundError, ValidationError, ConflictError,
    ServiceUnavailableError
)
from ..utils.cache import CacheManager
from ..infrastructure.mcp import PostgresMCP, PuppeteerMCP

logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
class CitationCreate(BaseModel):
    """Model for creating a new citation."""
    source_type: SourceType
    url: Optional[HttpUrl] = None
    title: str
    authors: List[str] = []
    publication_date: Optional[datetime] = None
    excerpt: Optional[str] = None
    context: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    @validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()


class CitationUpdate(BaseModel):
    """Model for updating a citation."""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    publication_date: Optional[datetime] = None
    excerpt: Optional[str] = None
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CitationVerifyRequest(BaseModel):
    """Model for verification request."""
    force: bool = False
    capture_screenshot: bool = True
    archive_content: bool = False


class AccuracyFeedback(BaseModel):
    """Model for accuracy feedback."""
    metric_type: MetricType
    score: float = Field(ge=0, le=1)
    feedback_type: FeedbackType
    comment: Optional[str] = None
    issues: List[str] = []
    suggestions: List[str] = []
    verified_facts: List[str] = []
    conflicting_sources: List[str] = []


class CitationSearchParams(BaseModel):
    """Model for citation search parameters."""
    query: Optional[str] = None
    source_types: List[SourceType] = []
    verification_status: Optional[VerificationStatus] = None
    min_quality_score: float = 0.0
    max_age_days: Optional[int] = None
    tags: List[str] = []
    limit: int = 20
    offset: int = 0


class CitationService:
    """
    Service for managing citations with verification and accuracy tracking.
    
    Provides comprehensive citation management including CRUD operations,
    verification through Puppeteer MCP, accuracy tracking, and search.
    """
    
    def __init__(
        self,
        db: Session,
        cache_manager: Optional[CacheManager] = None,
        postgres_mcp: Optional[PostgresMCP] = None,
        puppeteer_mcp: Optional[PuppeteerMCP] = None
    ):
        """Initialize citation service with dependencies."""
        self.db = db
        self.cache = cache_manager or CacheManager()
        self.postgres_mcp = postgres_mcp
        self.puppeteer_mcp = puppeteer_mcp
        self._reference_counter = 0
    
    def generate_reference_id(self) -> str:
        """Generate a unique reference ID for citations."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        self._reference_counter += 1
        return f"ref_{timestamp}_{self._reference_counter:04d}"
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA256 hash of content for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    async def create_citation(
        self,
        citation_data: CitationCreate,
        user_id: UUID,
        auto_verify: bool = True
    ) -> Citation:
        """
        Create a new citation with optional auto-verification.
        
        Args:
            citation_data: Citation creation data
            user_id: ID of user creating the citation
            auto_verify: Whether to automatically verify the citation
            
        Returns:
            Created citation object
            
        Raises:
            ValidationError: If citation data is invalid
            ConflictError: If similar citation already exists
        """
        try:
            # Check for duplicate citations by URL
            if citation_data.url:
                existing = self.db.query(Citation).filter(
                    Citation.url == str(citation_data.url)
                ).first()
                if existing:
                    logger.info(f"Citation with URL {citation_data.url} already exists")
                    return existing
            
            # Create citation object
            citation = Citation(
                reference_id=self.generate_reference_id(),
                source_type=citation_data.source_type,
                url=str(citation_data.url) if citation_data.url else None,
                title=citation_data.title,
                authors=citation_data.authors,
                publication_date=citation_data.publication_date,
                access_date=datetime.utcnow(),
                excerpt=citation_data.excerpt,
                context=citation_data.context,
                metadata=citation_data.metadata
            )
            
            # Add to database
            self.db.add(citation)
            self.db.commit()
            self.db.refresh(citation)
            
            # Auto-verify if requested and URL is provided
            if auto_verify and citation.url:
                try:
                    await self.verify_citation(citation.id, user_id)
                except Exception as e:
                    logger.error(f"Auto-verification failed for citation {citation.id}: {e}")
                    # Don't fail the creation if verification fails
            
            # Cache the citation
            cache_key = f"citation:{citation.id}"
            self.cache.set(cache_key, citation.to_dict(), ttl=3600)
            
            logger.info(f"Created citation {citation.reference_id} for user {user_id}")
            return citation
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error creating citation: {e}")
            raise ConflictError("Citation creation failed due to data conflict")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating citation: {e}")
            raise
    
    async def get_citation(
        self,
        citation_id: UUID,
        include_usage: bool = False
    ) -> Citation:
        """
        Get a citation by ID.
        
        Args:
            citation_id: Citation ID
            include_usage: Whether to include usage statistics
            
        Returns:
            Citation object
            
        Raises:
            NotFoundError: If citation not found
        """
        # Check cache first
        cache_key = f"citation:{citation_id}"
        cached = self.cache.get(cache_key)
        if cached and not include_usage:
            return Citation(**cached)
        
        # Query database
        query = select(Citation).where(Citation.id == citation_id)
        citation = self.db.execute(query).scalar_one_or_none()
        
        if not citation:
            raise NotFoundError(f"Citation {citation_id} not found")
        
        # Cache the result
        self.cache.set(cache_key, citation.to_dict(), ttl=3600)
        
        return citation
    
    async def update_citation(
        self,
        citation_id: UUID,
        update_data: CitationUpdate,
        user_id: UUID
    ) -> Citation:
        """
        Update a citation.
        
        Args:
            citation_id: Citation ID
            update_data: Update data
            user_id: ID of user updating the citation
            
        Returns:
            Updated citation object
            
        Raises:
            NotFoundError: If citation not found
            ValidationError: If update data is invalid
        """
        citation = await self.get_citation(citation_id)
        
        # Apply updates
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(citation, field, value)
        
        citation.updated_at = datetime.utcnow()
        
        try:
            self.db.commit()
            self.db.refresh(citation)
            
            # Invalidate cache
            cache_key = f"citation:{citation_id}"
            self.cache.delete(cache_key)
            
            logger.info(f"Updated citation {citation_id} by user {user_id}")
            return citation
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error updating citation: {e}")
            raise ValidationError("Citation update failed due to data conflict")
    
    async def verify_citation(
        self,
        citation_id: UUID,
        user_id: UUID,
        request: Optional[CitationVerifyRequest] = None
    ) -> VerificationLog:
        """
        Verify a citation using Puppeteer MCP.
        
        Args:
            citation_id: Citation ID
            user_id: ID of user requesting verification
            request: Verification request parameters
            
        Returns:
            Verification log entry
            
        Raises:
            NotFoundError: If citation not found
            ServiceUnavailableError: If Puppeteer MCP is unavailable
        """
        citation = await self.get_citation(citation_id)
        request = request or CitationVerifyRequest()
        
        if not citation.url:
            raise ValidationError("Cannot verify citation without URL")
        
        if not self.puppeteer_mcp:
            raise ServiceUnavailableError("Puppeteer MCP not configured")
        
        # Check if verification is needed
        if not request.force and citation.verification_status == VerificationStatus.VERIFIED:
            if citation.last_verified:
                days_since = (datetime.utcnow() - citation.last_verified).days
                if days_since < 7:  # Don't re-verify if verified within a week
                    logger.info(f"Citation {citation_id} recently verified, skipping")
                    return None
        
        # Create verification log entry
        verification_log = VerificationLog(
            citation_id=citation_id,
            attempt_number=citation.verification_attempts + 1,
            status="in_progress",
            started_at=datetime.utcnow()
        )
        self.db.add(verification_log)
        self.db.commit()
        
        try:
            # Perform verification using Puppeteer MCP
            verification_result = await self.puppeteer_mcp.verify_url(
                url=citation.url,
                capture_screenshot=request.capture_screenshot,
                extract_metadata=True
            )
            
            # Update citation with verification results
            citation.verification_status = VerificationStatus.VERIFIED
            citation.last_verified = datetime.utcnow()
            citation.verification_attempts += 1
            
            if verification_result.get('content'):
                new_hash = self.calculate_content_hash(verification_result['content'])
                if citation.content_hash and citation.content_hash != new_hash:
                    verification_log.content_matched = False
                    verification_log.changes_detected = {
                        'old_hash': citation.content_hash,
                        'new_hash': new_hash
                    }
                else:
                    verification_log.content_matched = True
                citation.content_hash = new_hash
            
            if verification_result.get('title'):
                citation.title = verification_result['title']
            
            if verification_result.get('screenshot_url'):
                citation.screenshot_url = verification_result['screenshot_url']
                verification_log.screenshot_url = verification_result['screenshot_url']
            
            # Update availability score based on verification success
            citation.availability_score = 1.0
            
            # Update verification log
            verification_log.status = "success"
            verification_log.completed_at = datetime.utcnow()
            verification_log.duration_ms = int(
                (verification_log.completed_at - verification_log.started_at).total_seconds() * 1000
            )
            
            self.db.commit()
            
            # Invalidate cache
            cache_key = f"citation:{citation_id}"
            self.cache.delete(cache_key)
            
            logger.info(f"Successfully verified citation {citation_id}")
            return verification_log
            
        except Exception as e:
            # Update verification log with error
            verification_log.status = "failed"
            verification_log.completed_at = datetime.utcnow()
            verification_log.error_type = type(e).__name__
            verification_log.error_message = str(e)
            
            # Update citation status
            citation.verification_status = VerificationStatus.FAILED
            citation.verification_attempts += 1
            citation.availability_score = 0.0
            
            if citation.verification_attempts >= 3:
                citation.requires_reverification = False  # Stop retrying after 3 attempts
            
            self.db.commit()
            
            logger.error(f"Failed to verify citation {citation_id}: {e}")
            raise ServiceUnavailableError(f"Verification failed: {e}")
    
    async def track_usage(
        self,
        citation_id: UUID,
        content_id: UUID,
        user_id: UUID,
        content_type: ContentType,
        position: int,
        context: Optional[str] = None,
        section: Optional[str] = None
    ) -> CitationUsage:
        """
        Track usage of a citation in content.
        
        Args:
            citation_id: Citation ID
            content_id: ID of content using the citation
            user_id: ID of user creating the content
            content_type: Type of content
            position: Position of citation in content
            context: Surrounding text context
            section: Section of content
            
        Returns:
            Citation usage record
        """
        # Check if citation exists
        citation = await self.get_citation(citation_id)
        
        # Create usage record
        usage = CitationUsage(
            citation_id=citation_id,
            content_id=content_id,
            user_id=user_id,
            content_type=content_type,
            position=position,
            context=context,
            section=section
        )
        
        try:
            self.db.add(usage)
            self.db.commit()
            self.db.refresh(usage)
            
            logger.info(f"Tracked usage of citation {citation_id} in content {content_id}")
            return usage
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error tracking citation usage: {e}")
            raise ConflictError("Citation usage already tracked for this position")
    
    async def submit_accuracy_feedback(
        self,
        citation_id: UUID,
        feedback: AccuracyFeedback,
        evaluator_id: UUID
    ) -> AccuracyTracking:
        """
        Submit accuracy feedback for a citation.
        
        Args:
            citation_id: Citation ID
            feedback: Accuracy feedback data
            evaluator_id: ID of user providing feedback
            
        Returns:
            Accuracy tracking record
        """
        # Check if citation exists
        citation = await self.get_citation(citation_id)
        
        # Create accuracy tracking record
        tracking = AccuracyTracking(
            citation_id=citation_id,
            evaluator_id=evaluator_id,
            metric_type=feedback.metric_type,
            score=feedback.score,
            feedback_type=feedback.feedback_type,
            feedback_data={
                'comment': feedback.comment,
                'issues': feedback.issues,
                'suggestions': feedback.suggestions,
                'verified_facts': feedback.verified_facts,
                'conflicting_sources': feedback.conflicting_sources
            },
            evaluated_at=datetime.utcnow()
        )
        
        self.db.add(tracking)
        
        # Update citation scores based on feedback
        await self._update_citation_scores(citation_id)
        
        self.db.commit()
        self.db.refresh(tracking)
        
        logger.info(f"Submitted accuracy feedback for citation {citation_id}")
        return tracking
    
    async def _update_citation_scores(self, citation_id: UUID):
        """
        Update citation scores based on accumulated feedback.
        
        Args:
            citation_id: Citation ID
        """
        # Calculate average scores from feedback
        result = self.db.execute(
            select(
                func.avg(AccuracyTracking.score).filter(
                    AccuracyTracking.metric_type == MetricType.ACCURACY
                ).label('accuracy'),
                func.avg(AccuracyTracking.score).filter(
                    AccuracyTracking.metric_type == MetricType.RELEVANCE
                ).label('relevance'),
                func.avg(AccuracyTracking.score).filter(
                    AccuracyTracking.metric_type == MetricType.AVAILABILITY
                ).label('availability')
            ).where(AccuracyTracking.citation_id == citation_id)
        ).first()
        
        if result:
            citation = self.db.get(Citation, citation_id)
            if result.accuracy is not None:
                citation.accuracy_score = float(result.accuracy)
            if result.relevance is not None:
                citation.relevance_score = float(result.relevance)
            if result.availability is not None:
                citation.availability_score = float(result.availability)
            
            # Overall quality score is calculated by trigger in database
            self.db.commit()
    
    async def search_citations(
        self,
        params: CitationSearchParams
    ) -> Tuple[List[Citation], int]:
        """
        Search citations with filters.
        
        Args:
            params: Search parameters
            
        Returns:
            Tuple of (citations list, total count)
        """
        query = select(Citation).where(Citation.is_active == True)
        
        # Apply filters
        if params.query:
            search_filter = or_(
                Citation.title.ilike(f"%{params.query}%"),
                Citation.excerpt.ilike(f"%{params.query}%"),
                Citation.url.ilike(f"%{params.query}%")
            )
            query = query.where(search_filter)
        
        if params.source_types:
            query = query.where(Citation.source_type.in_(params.source_types))
        
        if params.verification_status:
            query = query.where(Citation.verification_status == params.verification_status)
        
        if params.min_quality_score > 0:
            query = query.where(Citation.overall_quality_score >= params.min_quality_score)
        
        if params.max_age_days:
            cutoff_date = datetime.utcnow() - timedelta(days=params.max_age_days)
            query = query.where(Citation.access_date >= cutoff_date)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = self.db.execute(count_query).scalar()
        
        # Apply pagination and ordering
        query = query.order_by(Citation.overall_quality_score.desc())
        query = query.limit(params.limit).offset(params.offset)
        
        # Execute query
        results = self.db.execute(query).scalars().all()
        
        return results, total_count
    
    async def get_accuracy_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate system-wide accuracy report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Accuracy report with metrics and statistics
        """
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get overall system accuracy
        overall_accuracy = self.db.execute(
            select(func.avg(Citation.overall_quality_score))
            .where(Citation.is_active == True)
        ).scalar() or 0.0
        
        # Get accuracy by source type
        accuracy_by_source = self.db.execute(
            select(
                Citation.source_type,
                func.avg(Citation.overall_quality_score).label('avg_score'),
                func.count(Citation.id).label('count')
            )
            .where(Citation.is_active == True)
            .group_by(Citation.source_type)
        ).all()
        
        # Get verification statistics
        verification_stats = self.db.execute(
            select(
                Citation.verification_status,
                func.count(Citation.id).label('count')
            )
            .where(Citation.is_active == True)
            .group_by(Citation.verification_status)
        ).all()
        
        # Get citations needing attention (low accuracy)
        low_accuracy_citations = self.db.execute(
            select(Citation)
            .where(
                and_(
                    Citation.is_active == True,
                    Citation.overall_quality_score < 0.95
                )
            )
            .order_by(Citation.overall_quality_score.asc())
            .limit(10)
        ).scalars().all()
        
        # Get feedback statistics
        feedback_stats = self.db.execute(
            select(
                AccuracyTracking.feedback_type,
                func.count(AccuracyTracking.id).label('count'),
                func.avg(AccuracyTracking.score).label('avg_score')
            )
            .where(
                and_(
                    AccuracyTracking.evaluated_at >= start_date,
                    AccuracyTracking.evaluated_at <= end_date
                )
            )
            .group_by(AccuracyTracking.feedback_type)
        ).all()
        
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'overall_accuracy': float(overall_accuracy) * 100,
            'accuracy_status': 'green' if overall_accuracy >= 0.95 else 'yellow' if overall_accuracy >= 0.90 else 'red',
            'accuracy_by_source': [
                {
                    'source_type': row.source_type,
                    'average_score': float(row.avg_score) * 100,
                    'citation_count': row.count
                }
                for row in accuracy_by_source
            ],
            'verification_statistics': [
                {
                    'status': row.verification_status,
                    'count': row.count
                }
                for row in verification_stats
            ],
            'citations_needing_attention': [
                {
                    'id': str(c.id),
                    'reference_id': c.reference_id,
                    'title': c.title,
                    'quality_score': float(c.overall_quality_score) * 100
                }
                for c in low_accuracy_citations
            ],
            'feedback_statistics': [
                {
                    'feedback_type': row.feedback_type,
                    'count': row.count,
                    'average_score': float(row.avg_score) * 100
                }
                for row in feedback_stats
            ]
        }
        
        return report
    
    async def batch_create_citations(
        self,
        citations_data: List[CitationCreate],
        user_id: UUID
    ) -> List[Citation]:
        """
        Create multiple citations in batch.
        
        Args:
            citations_data: List of citation creation data
            user_id: ID of user creating citations
            
        Returns:
            List of created citations
        """
        created_citations = []
        
        for citation_data in citations_data:
            try:
                citation = await self.create_citation(
                    citation_data,
                    user_id,
                    auto_verify=False  # Don't auto-verify in batch to avoid overwhelming the system
                )
                created_citations.append(citation)
            except Exception as e:
                logger.error(f"Failed to create citation in batch: {e}")
                # Continue with other citations even if one fails
        
        logger.info(f"Created {len(created_citations)} citations in batch for user {user_id}")
        return created_citations
    
    async def get_stale_citations(
        self,
        days_threshold: int = 30,
        limit: int = 100
    ) -> List[Citation]:
        """
        Get citations that need reverification.
        
        Args:
            days_threshold: Days since last verification
            limit: Maximum number of citations to return
            
        Returns:
            List of stale citations
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        query = select(Citation).where(
            or_(
                Citation.verification_status == VerificationStatus.STALE,
                Citation.requires_reverification == True,
                and_(
                    Citation.last_verified != None,
                    Citation.last_verified < cutoff_date
                )
            )
        ).limit(limit)
        
        results = self.db.execute(query).scalars().all()
        return results