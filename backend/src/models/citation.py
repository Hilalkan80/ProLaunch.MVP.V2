"""
Citation system database models.

This module defines the database schema for the citation tracking system,
including citations, usage tracking, and accuracy metrics.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
from enum import Enum

from sqlalchemy import (
    Column, String, Text, DateTime, Float, Integer, Boolean,
    ForeignKey, JSON, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from .base import Base


class SourceType(str, Enum):
    """Types of citation sources."""
    WEB = "web"
    ACADEMIC = "academic"
    API = "api"
    DATABASE = "database"
    DOCUMENT = "document"
    SOCIAL_MEDIA = "social_media"
    NEWS = "news"
    GOVERNMENT = "government"
    BOOK = "book"
    VIDEO = "video"


class VerificationStatus(str, Enum):
    """Citation verification statuses."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    STALE = "stale"
    PARTIAL = "partial"


class ContentType(str, Enum):
    """Types of content using citations."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"
    SUMMARY = "summary"
    REPORT = "report"
    ARTICLE = "article"


class FeedbackType(str, Enum):
    """Types of accuracy feedback."""
    USER = "user"
    AUTOMATED = "automated"
    EXPERT = "expert"
    COMMUNITY = "community"


class MetricType(str, Enum):
    """Types of accuracy metrics."""
    RELEVANCE = "relevance"
    ACCURACY = "accuracy"
    AVAILABILITY = "availability"
    COMPLETENESS = "completeness"
    TIMELINESS = "timeliness"


class Citation(Base):
    """
    Core citation model for tracking sources.
    
    Stores comprehensive information about each citation including
    metadata, verification status, and usage statistics.
    """
    
    __tablename__ = "citations"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    reference_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Source information
    source_type = Column(String(20), nullable=False, default=SourceType.WEB)
    url = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    authors = Column(ARRAY(String), default=list)
    publication_date = Column(DateTime, nullable=True)
    access_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Content tracking
    content_hash = Column(String(64), nullable=True)
    excerpt = Column(Text, nullable=True)
    context = Column(Text, nullable=True)
    full_text = Column(Text, nullable=True)  # For caching verified content
    
    # Metadata (flexible schema for different source types)
    citation_metadata = Column("metadata", JSONB, default=dict)
    # Expected metadata fields:
    # - doi: Digital Object Identifier for academic papers
    # - isbn: International Standard Book Number
    # - journal: Journal name for academic articles
    # - volume: Volume number
    # - issue: Issue number
    # - pages: Page range
    # - publisher: Publisher name
    # - language: Content language
    # - keywords: List of keywords
    # - abstract: Abstract for academic papers
    
    # Verification tracking
    verification_status = Column(
        String(20), 
        nullable=False, 
        default=VerificationStatus.PENDING
    )
    last_verified = Column(DateTime, nullable=True)
    verification_attempts = Column(Integer, default=0)
    verification_errors = Column(JSONB, default=list)
    screenshot_url = Column(Text, nullable=True)
    
    # Quality metrics
    accuracy_score = Column(Float, default=0.0)
    relevance_score = Column(Float, default=0.0)
    availability_score = Column(Float, default=1.0)
    overall_quality_score = Column(Float, default=0.0)
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    
    # Flags and status
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    requires_reverification = Column(Boolean, default=False)
    
    # Relationships
    usages = relationship("CitationUsage", back_populates="citation", cascade="all, delete-orphan")
    accuracy_metrics = relationship("AccuracyTracking", back_populates="citation", cascade="all, delete-orphan")
    verification_logs = relationship("VerificationLog", back_populates="citation", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_citation_reference", "reference_id"),
        Index("idx_citation_url", "url"),
        Index("idx_citation_verification", "verification_status", "last_verified"),
        Index("idx_citation_quality", "overall_quality_score"),
        Index("idx_citation_usage", "usage_count", "last_used"),
        CheckConstraint("accuracy_score >= 0 AND accuracy_score <= 1", name="check_accuracy_range"),
        CheckConstraint("relevance_score >= 0 AND relevance_score <= 1", name="check_relevance_range"),
        CheckConstraint("availability_score >= 0 AND availability_score <= 1", name="check_availability_range"),
    )
    
    @validates("reference_id")
    def validate_reference_id(self, key, value):
        """Validate reference ID format."""
        if not value or not value.startswith("ref_"):
            raise ValueError("Reference ID must start with 'ref_'")
        return value
    
    @validates("url")
    def validate_url(self, key, value):
        """Validate URL format if provided."""
        if value and not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return value
    
    @hybrid_property
    def needs_verification(self) -> bool:
        """Check if citation needs verification."""
        if self.verification_status == VerificationStatus.PENDING:
            return True
        if self.verification_status == VerificationStatus.STALE:
            return True
        if self.requires_reverification:
            return True
        # Check if verification is older than 30 days
        if self.last_verified:
            days_since_verification = (datetime.utcnow() - self.last_verified).days
            if days_since_verification > 30:
                return True
        return False
    
    @hybrid_property
    def formatted_citation(self) -> str:
        """Return formatted citation string."""
        return f"[[{self.reference_id} - {self.access_date.strftime('%Y-%m-%d')}]]"
    
    def calculate_overall_quality(self) -> float:
        """Calculate overall quality score based on weighted metrics."""
        return (
            0.4 * self.relevance_score +
            0.4 * self.accuracy_score +
            0.2 * self.availability_score
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert citation to dictionary representation."""
        return {
            "id": str(self.id),
            "reference_id": self.reference_id,
            "source_type": self.source_type,
            "url": self.url,
            "title": self.title,
            "authors": self.authors,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "access_date": self.access_date.isoformat(),
            "excerpt": self.excerpt,
            "metadata": self.metadata,
            "verification_status": self.verification_status,
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
            "accuracy_score": self.accuracy_score,
            "usage_count": self.usage_count,
            "formatted": self.formatted_citation
        }


class CitationUsage(Base):
    """
    Tracks where and how citations are used in content.
    
    Links citations to specific content pieces and tracks
    usage context and positioning.
    """
    
    __tablename__ = "citation_usages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    citation_id = Column(UUID(as_uuid=True), ForeignKey("citations.id"), nullable=False)
    content_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to content using citation
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Usage details
    content_type = Column(String(20), nullable=False, default=ContentType.RESEARCH)
    position = Column(Integer, nullable=False)  # Position in content (for ordering)
    context = Column(Text, nullable=True)  # Surrounding text context
    section = Column(String(100), nullable=True)  # Section of content (e.g., "introduction", "conclusion")
    
    # Quality tracking
    is_verified = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.5)
    
    # Relationships
    citation = relationship("Citation", back_populates="usages")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_usage_citation", "citation_id"),
        Index("idx_usage_content", "content_id"),
        Index("idx_usage_user", "user_id"),
        UniqueConstraint("citation_id", "content_id", "position", name="uq_citation_content_position"),
    )


class AccuracyTracking(Base):
    """
    Tracks accuracy metrics and feedback for citations.
    
    Stores various types of accuracy assessments including
    user feedback, automated checks, and expert reviews.
    """
    
    __tablename__ = "accuracy_tracking"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    citation_id = Column(UUID(as_uuid=True), ForeignKey("citations.id"), nullable=False)
    evaluator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Metric details
    metric_type = Column(String(20), nullable=False)
    score = Column(Float, nullable=False)
    feedback_type = Column(String(20), nullable=False, default=FeedbackType.USER)
    
    # Feedback data (flexible schema)
    feedback_data = Column(JSONB, default=dict)
    # Expected feedback_data fields:
    # - comment: Text feedback from user
    # - issues: List of identified issues
    # - suggestions: Improvement suggestions
    # - verified_facts: List of verified facts
    # - conflicting_sources: URLs of conflicting sources
    
    # Evaluation context
    evaluated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    evaluation_method = Column(String(50), nullable=True)  # e.g., "manual", "automated_factcheck"
    confidence_level = Column(Float, default=0.5)
    
    # Relationships
    citation = relationship("Citation", back_populates="accuracy_metrics")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_accuracy_citation", "citation_id"),
        Index("idx_accuracy_evaluator", "evaluator_id"),
        Index("idx_accuracy_type", "metric_type", "feedback_type"),
        CheckConstraint("score >= 0 AND score <= 1", name="check_score_range"),
        CheckConstraint("confidence_level >= 0 AND confidence_level <= 1", name="check_confidence_range"),
    )


class VerificationLog(Base):
    """
    Logs all verification attempts for citations.
    
    Maintains a history of verification attempts including
    successes, failures, and error details.
    """
    
    __tablename__ = "verification_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign key
    citation_id = Column(UUID(as_uuid=True), ForeignKey("citations.id"), nullable=False)
    
    # Verification details
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)  # success, failed, timeout, error
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Results
    content_matched = Column(Boolean, nullable=True)
    new_content_hash = Column(String(64), nullable=True)
    changes_detected = Column(JSONB, default=dict)
    
    # Error tracking
    error_type = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, default=dict)
    
    # Screenshot and artifacts
    screenshot_url = Column(Text, nullable=True)
    archived_content_url = Column(Text, nullable=True)
    
    # Relationships
    citation = relationship("Citation", back_populates="verification_logs")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_verification_citation", "citation_id"),
        Index("idx_verification_status", "status", "completed_at"),
    )


class CitationCollection(Base):
    """
    Groups related citations into collections.
    
    Useful for organizing citations by project, topic, or research area.
    """
    
    __tablename__ = "citation_collections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Collection details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Collection metadata
    tags = Column(ARRAY(String), default=list)
    is_public = Column(Boolean, default=False)
    citation_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)
    
    # Statistics
    citation_count = Column(Integer, default=0)
    average_quality_score = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_collection_owner", "owner_id"),
        Index("idx_collection_public", "is_public"),
    )