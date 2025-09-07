"""
Milestone System Database Models

This module implements the milestone tracking system with dependency management,
progress tracking, and efficient caching strategies for the ProLaunch MVP.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, 
    ForeignKey, Text, JSON, UniqueConstraint, CheckConstraint,
    Index, select, and_, or_, func
)
from sqlalchemy.orm import relationship, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
import uuid

from .base import Base


class MilestoneStatus(str, Enum):
    """Milestone completion status enumeration"""
    LOCKED = "locked"  # Not yet available
    AVAILABLE = "available"  # Can be started
    IN_PROGRESS = "in_progress"  # Currently being worked on
    COMPLETED = "completed"  # Successfully completed
    SKIPPED = "skipped"  # Skipped by user choice
    FAILED = "failed"  # Failed due to error


class MilestoneType(str, Enum):
    """Types of milestones in the system"""
    FREE = "free"  # Free tier milestone (M0, M9)
    PAID = "paid"  # Paid tier milestone (M1-M8)
    GATEWAY = "gateway"  # Gateway milestone (triggers payment)


class Milestone(Base):
    """
    Core milestone definition model.
    Stores the template/definition of each milestone in the system.
    """
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(10), unique=True, nullable=False)  # M0, M1, etc.
    name = Column(String(100), nullable=False)
    description = Column(Text)
    milestone_type = Column(String(20), default=MilestoneType.PAID)
    
    # Milestone metadata
    order_index = Column(Integer, nullable=False)  # Display order
    estimated_minutes = Column(Integer, default=30)  # Estimated completion time
    processing_time_limit = Column(Integer, default=300)  # Max processing time in seconds
    
    # Feature flags
    is_active = Column(Boolean, default=True)
    requires_payment = Column(Boolean, default=True)
    auto_unlock = Column(Boolean, default=False)  # Automatically unlock when dependencies met
    
    # Content and prompts
    prompt_template = Column(JSONB)  # LLM prompt template configuration
    output_schema = Column(JSONB)  # Expected output structure
    validation_rules = Column(JSONB)  # Validation rules for completion
    
    # Relationships
    dependencies = relationship(
        "MilestoneDependency",
        foreign_keys="MilestoneDependency.milestone_id",
        back_populates="milestone",
        cascade="all, delete-orphan"
    )
    
    dependents = relationship(
        "MilestoneDependency",
        foreign_keys="MilestoneDependency.dependency_id",
        back_populates="dependency",
        cascade="all, delete-orphan"
    )
    
    user_milestones = relationship(
        "UserMilestone",
        back_populates="milestone",
        cascade="all, delete-orphan"
    )
    
    artifacts = relationship(
        "MilestoneArtifact",
        back_populates="milestone",
        cascade="all, delete-orphan"
    )
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_milestone_code", "code"),
        Index("idx_milestone_order", "order_index"),
        Index("idx_milestone_active", "is_active"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert milestone to dictionary representation"""
        return {
            "id": str(self.id),
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "type": self.milestone_type,
            "order": self.order_index,
            "estimated_minutes": self.estimated_minutes,
            "requires_payment": self.requires_payment,
            "is_active": self.is_active
        }


class MilestoneDependency(Base):
    """
    Defines dependencies between milestones.
    Implements a directed acyclic graph (DAG) for milestone dependencies.
    """
    __tablename__ = "milestone_dependencies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=False)
    dependency_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=False)
    
    # Dependency metadata
    is_required = Column(Boolean, default=True)  # Required vs optional dependency
    minimum_completion_percentage = Column(Float, default=100.0)  # Min completion % needed
    
    # Relationships
    milestone = relationship(
        "Milestone",
        foreign_keys=[milestone_id],
        back_populates="dependencies"
    )
    
    dependency = relationship(
        "Milestone",
        foreign_keys=[dependency_id],
        back_populates="dependents"
    )
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("milestone_id", "dependency_id", name="uq_milestone_dependency"),
        CheckConstraint("milestone_id != dependency_id", name="check_no_self_dependency"),
        Index("idx_dependency_milestone", "milestone_id"),
        Index("idx_dependency_dep", "dependency_id"),
    )


class UserMilestone(Base):
    """
    Tracks individual user progress through milestones.
    Stores user-specific milestone data and completion status.
    """
    __tablename__ = "user_milestones"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=False)
    
    # Status tracking
    status = Column(String(20), default=MilestoneStatus.LOCKED)
    completion_percentage = Column(Float, default=0.0)
    
    # Timing information
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_accessed_at = Column(DateTime)
    time_spent_seconds = Column(Integer, default=0)
    
    # Progress data
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=1)
    checkpoint_data = Column(JSONB)  # Store intermediate progress
    
    # User inputs and outputs
    user_inputs = Column(JSONB)  # User-provided data for this milestone
    generated_output = Column(JSONB)  # AI-generated content
    
    # Quality metrics
    quality_score = Column(Float)  # Quality assessment score
    feedback_rating = Column(Integer)  # User satisfaction rating (1-5)
    feedback_text = Column(Text)
    
    # Processing metadata
    processing_attempts = Column(Integer, default=0)
    last_error = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="milestones")
    milestone = relationship("Milestone", back_populates="user_milestones")
    
    artifacts = relationship(
        "UserMilestoneArtifact",
        back_populates="user_milestone",
        cascade="all, delete-orphan"
    )
    
    progress_logs = relationship(
        "MilestoneProgressLog",
        back_populates="user_milestone",
        cascade="all, delete-orphan",
        order_by="MilestoneProgressLog.created_at.desc()"
    )
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("user_id", "milestone_id", name="uq_user_milestone"),
        Index("idx_user_milestone_user", "user_id"),
        Index("idx_user_milestone_status", "status"),
        Index("idx_user_milestone_completed", "completed_at"),
    )
    
    def to_dict(self, include_outputs: bool = False) -> Dict[str, Any]:
        """Convert user milestone to dictionary"""
        data = {
            "id": str(self.id),
            "milestone_id": str(self.milestone_id),
            "status": self.status,
            "completion_percentage": self.completion_percentage,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "time_spent_seconds": self.time_spent_seconds,
            "quality_score": self.quality_score,
            "feedback_rating": self.feedback_rating
        }
        
        if include_outputs and self.generated_output:
            data["generated_output"] = self.generated_output
            
        return data


class MilestoneArtifact(Base):
    """
    Template artifacts associated with milestones.
    These are the expected deliverables for each milestone.
    """
    __tablename__ = "milestone_artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    artifact_type = Column(String(50))  # document, spreadsheet, template, etc.
    description = Column(Text)
    
    # Template information
    template_path = Column(String(500))  # Path to template file
    output_format = Column(String(50))  # pdf, xlsx, json, etc.
    
    # Metadata
    is_required = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    
    # Relationships
    milestone = relationship("Milestone", back_populates="artifacts")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_artifact_milestone", "milestone_id"),
    )


class UserMilestoneArtifact(Base):
    """
    User-specific generated artifacts from milestone completion.
    Stores the actual files/content generated for each user.
    """
    __tablename__ = "user_milestone_artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_milestone_id = Column(UUID(as_uuid=True), ForeignKey("user_milestones.id"), nullable=False)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("milestone_artifacts.id"))
    
    # Artifact details
    name = Column(String(200), nullable=False)
    artifact_type = Column(String(50))
    mime_type = Column(String(100))
    
    # Storage information
    storage_path = Column(String(500))  # S3 or filesystem path
    file_size = Column(Integer)  # Size in bytes
    checksum = Column(String(64))  # SHA-256 hash for integrity
    
    # Content
    content = Column(JSONB)  # For JSON-based artifacts
    preview_text = Column(Text)  # Preview for UI display
    
    # Metadata
    generation_metadata = Column(JSONB)  # LLM generation details
    citations_used = Column(ARRAY(String))  # Citation IDs used
    
    # Access control
    is_public = Column(Boolean, default=False)
    share_token = Column(String(100), unique=True)
    access_count = Column(Integer, default=0)
    
    # Relationships
    user_milestone = relationship("UserMilestone", back_populates="artifacts")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed_at = Column(DateTime)
    
    __table_args__ = (
        Index("idx_user_artifact_milestone", "user_milestone_id"),
        Index("idx_user_artifact_share", "share_token"),
    )


class MilestoneProgressLog(Base):
    """
    Detailed progress tracking for milestone completion.
    Captures every significant event in the milestone journey.
    """
    __tablename__ = "milestone_progress_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_milestone_id = Column(UUID(as_uuid=True), ForeignKey("user_milestones.id"), nullable=False)
    
    # Event information
    event_type = Column(String(50), nullable=False)  # started, step_completed, paused, resumed, completed, failed
    event_data = Column(JSONB)
    
    # Progress snapshot
    step_number = Column(Integer)
    completion_percentage = Column(Float)
    time_elapsed_seconds = Column(Integer)
    
    # Context
    session_id = Column(String(100))  # Track within session
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Relationships
    user_milestone = relationship("UserMilestone", back_populates="progress_logs")
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_progress_log_milestone", "user_milestone_id"),
        Index("idx_progress_log_event", "event_type"),
        Index("idx_progress_log_created", "created_at"),
    )


class MilestoneCache(Base):
    """
    Cache table for frequently accessed milestone data.
    Used for optimizing read-heavy operations.
    """
    __tablename__ = "milestone_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key = Column(String(200), unique=True, nullable=False)
    cache_type = Column(String(50))  # user_progress, milestone_tree, statistics
    
    # Cached data
    data = Column(JSONB, nullable=False)
    
    # Cache metadata
    ttl_seconds = Column(Integer, default=3600)  # Time to live
    hit_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_accessed_at = Column(DateTime)
    
    __table_args__ = (
        Index("idx_cache_key", "cache_key"),
        Index("idx_cache_expires", "expires_at"),
        Index("idx_cache_type", "cache_type"),
    )


# Helper functions for milestone management
async def get_user_milestone_tree(
    db: AsyncSession,
    user_id: str
) -> Dict[str, Any]:
    """
    Retrieve complete milestone tree for a user with dependency status.
    Optimized for performance with eager loading.
    """
    # Query all milestones with user progress
    stmt = (
        select(Milestone, UserMilestone)
        .outerjoin(
            UserMilestone,
            and_(
                UserMilestone.milestone_id == Milestone.id,
                UserMilestone.user_id == user_id
            )
        )
        .options(
            selectinload(Milestone.dependencies).selectinload(MilestoneDependency.dependency),
            selectinload(Milestone.artifacts)
        )
        .where(Milestone.is_active == True)
        .order_by(Milestone.order_index)
    )
    
    result = await db.execute(stmt)
    milestone_data = result.all()
    
    # Build milestone tree
    tree = {
        "milestones": [],
        "total_progress": 0,
        "completed_count": 0,
        "available_count": 0
    }
    
    for milestone, user_milestone in milestone_data:
        milestone_info = milestone.to_dict()
        
        # Add user progress if exists
        if user_milestone:
            milestone_info["user_progress"] = user_milestone.to_dict()
            if user_milestone.status == MilestoneStatus.COMPLETED:
                tree["completed_count"] += 1
            elif user_milestone.status == MilestoneStatus.AVAILABLE:
                tree["available_count"] += 1
        else:
            milestone_info["user_progress"] = {
                "status": MilestoneStatus.LOCKED,
                "completion_percentage": 0
            }
        
        # Add dependencies
        milestone_info["dependencies"] = [
            {
                "id": str(dep.dependency.id),
                "code": dep.dependency.code,
                "is_required": dep.is_required
            }
            for dep in milestone.dependencies
        ]
        
        tree["milestones"].append(milestone_info)
    
    # Calculate total progress
    if milestone_data:
        tree["total_progress"] = (tree["completed_count"] / len(milestone_data)) * 100
    
    return tree


async def check_milestone_dependencies(
    db: AsyncSession,
    user_id: str,
    milestone_id: str
) -> tuple[bool, List[str]]:
    """
    Check if a user has met all dependencies for a milestone.
    Returns (can_start, missing_dependencies)
    """
    # Get milestone dependencies
    stmt = (
        select(MilestoneDependency)
        .options(selectinload(MilestoneDependency.dependency))
        .where(MilestoneDependency.milestone_id == milestone_id)
    )
    
    result = await db.execute(stmt)
    dependencies = result.scalars().all()
    
    if not dependencies:
        return True, []
    
    missing = []
    
    for dep in dependencies:
        if not dep.is_required:
            continue
            
        # Check user progress on dependency
        user_progress_stmt = (
            select(UserMilestone)
            .where(
                and_(
                    UserMilestone.user_id == user_id,
                    UserMilestone.milestone_id == dep.dependency_id
                )
            )
        )
        
        result = await db.execute(user_progress_stmt)
        user_progress = result.scalar_one_or_none()
        
        if not user_progress:
            missing.append(dep.dependency.code)
        elif user_progress.completion_percentage < dep.minimum_completion_percentage:
            missing.append(dep.dependency.code)
    
    return len(missing) == 0, missing


async def update_dependent_milestones(
    db: AsyncSession,
    user_id: str,
    completed_milestone_id: str
) -> List[str]:
    """
    Update the status of milestones that depend on a newly completed milestone.
    Returns list of newly unlocked milestone IDs.
    """
    # Find milestones that depend on the completed one
    stmt = (
        select(MilestoneDependency)
        .options(selectinload(MilestoneDependency.milestone))
        .where(MilestoneDependency.dependency_id == completed_milestone_id)
    )
    
    result = await db.execute(stmt)
    dependent_dependencies = result.scalars().all()
    
    newly_unlocked = []
    
    for dep in dependent_dependencies:
        # Check if all dependencies are now met
        can_start, _ = await check_milestone_dependencies(
            db, user_id, str(dep.milestone_id)
        )
        
        if can_start:
            # Check if user milestone exists
            user_milestone_stmt = (
                select(UserMilestone)
                .where(
                    and_(
                        UserMilestone.user_id == user_id,
                        UserMilestone.milestone_id == dep.milestone_id
                    )
                )
            )
            
            result = await db.execute(user_milestone_stmt)
            user_milestone = result.scalar_one_or_none()
            
            if user_milestone and user_milestone.status == MilestoneStatus.LOCKED:
                # Update to available
                user_milestone.status = MilestoneStatus.AVAILABLE
                user_milestone.updated_at = datetime.utcnow()
                newly_unlocked.append(str(dep.milestone_id))
            elif not user_milestone and dep.milestone.auto_unlock:
                # Create new user milestone as available
                new_user_milestone = UserMilestone(
                    user_id=user_id,
                    milestone_id=dep.milestone_id,
                    status=MilestoneStatus.AVAILABLE
                )
                db.add(new_user_milestone)
                newly_unlocked.append(str(dep.milestone_id))
    
    return newly_unlocked