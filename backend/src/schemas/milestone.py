"""
Milestone and Dependency Pydantic Schemas

Data validation and serialization schemas for milestone
and dependency management endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import UUID
from enum import Enum


class MilestoneStatus(str, Enum):
    """Milestone completion status"""
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class MilestoneType(str, Enum):
    """Types of milestones"""
    FREE = "free"
    PAID = "paid"
    GATEWAY = "gateway"


class DependencyType(str, Enum):
    """Types of dependencies"""
    REQUIRED = "required"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"


# Base schemas

class MilestoneBase(BaseModel):
    """Base milestone schema"""
    code: str = Field(..., min_length=2, max_length=10, description="Milestone code (M0, M1, etc.)")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    milestone_type: MilestoneType = MilestoneType.PAID
    order_index: int = Field(..., ge=0)
    estimated_minutes: int = Field(30, ge=1)
    requires_payment: bool = True
    auto_unlock: bool = False
    is_active: bool = True


class DependencyBase(BaseModel):
    """Base dependency schema"""
    is_required: bool = True
    minimum_completion_percentage: float = Field(100.0, ge=0, le=100)


# Request schemas

class MilestoneCreate(MilestoneBase):
    """Schema for creating a milestone"""
    prompt_template: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    processing_time_limit: int = Field(300, ge=60, le=3600)


class MilestoneUpdate(BaseModel):
    """Schema for updating a milestone"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    estimated_minutes: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    prompt_template: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None


class DependencyCreate(DependencyBase):
    """Schema for creating a dependency"""
    milestone_code: str = Field(..., description="Milestone that has the dependency")
    dependency_code: str = Field(..., description="Milestone that must be completed first")
    dependency_type: DependencyType = DependencyType.REQUIRED
    conditions: Optional[Dict[str, Any]] = None
    
    @validator('milestone_code')
    def validate_not_self_dependency(cls, v, values):
        if 'dependency_code' in values and v == values['dependency_code']:
            raise ValueError("A milestone cannot depend on itself")
        return v


class MilestoneProgressUpdate(BaseModel):
    """Schema for updating milestone progress"""
    step_completed: int = Field(..., ge=1)
    checkpoint_data: Optional[Dict[str, Any]] = None
    time_spent_seconds: Optional[int] = Field(None, ge=0)


class MilestoneCompletion(BaseModel):
    """Schema for completing a milestone"""
    generated_output: Dict[str, Any]
    quality_score: Optional[float] = Field(None, ge=0, le=5)
    feedback_rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_text: Optional[str] = None


# Response schemas

class MilestoneResponse(MilestoneBase):
    """Schema for milestone response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    prompt_template: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True


class DependencyResponse(DependencyBase):
    """Schema for dependency response"""
    id: UUID
    milestone_id: UUID
    dependency_id: UUID
    milestone_code: str
    dependency_code: str
    dependency_name: str
    created_at: datetime
    
    class Config:
        orm_mode = True


class UserMilestoneResponse(BaseModel):
    """Schema for user milestone progress response"""
    id: UUID
    milestone_id: UUID
    milestone_code: str
    milestone_name: str
    status: MilestoneStatus
    completion_percentage: float = Field(..., ge=0, le=100)
    current_step: int = Field(..., ge=0)
    total_steps: int = Field(..., ge=1)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    time_spent_seconds: int = 0
    quality_score: Optional[float] = None
    feedback_rating: Optional[int] = None
    
    class Config:
        orm_mode = True


class MilestoneTreeResponse(BaseModel):
    """Schema for complete milestone tree response"""
    milestones: List[Dict[str, Any]]
    total_progress: float = Field(..., ge=0, le=100)
    completed_count: int = Field(..., ge=0)
    available_count: int = Field(..., ge=0)
    locked_count: int = Field(..., ge=0)


class DependencyValidationResponse(BaseModel):
    """Schema for dependency validation response"""
    milestone_code: str
    all_dependencies_met: bool
    unmet_dependencies: List[Dict[str, Any]]
    can_start: bool


class DependencyChainResponse(BaseModel):
    """Schema for dependency chain response"""
    milestone_code: str
    total_dependencies: int = Field(..., ge=0)
    dependency_chain: List[Dict[str, Any]]


class UnlockedMilestonesResponse(BaseModel):
    """Schema for newly unlocked milestones response"""
    completed_milestone: str
    newly_unlocked_count: int = Field(..., ge=0)
    newly_unlocked: List[Dict[str, Any]]


class DependencyGraphResponse(BaseModel):
    """Schema for dependency graph visualization response"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    statistics: Dict[str, Any]


class MilestoneArtifactResponse(BaseModel):
    """Schema for milestone artifact response"""
    id: UUID
    name: str
    artifact_type: str
    mime_type: Optional[str] = None
    storage_path: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime
    share_token: Optional[str] = None
    is_public: bool = False
    
    class Config:
        orm_mode = True


class MilestoneAnalyticsResponse(BaseModel):
    """Schema for milestone analytics response"""
    total_milestones: int
    completed: int
    in_progress: int
    locked: int
    failed: int
    total_time_spent_hours: float
    average_completion_time_hours: float
    completion_rate: float
    average_quality_score: Optional[float] = None
    milestones_by_status: Dict[str, int]
    time_by_milestone: Dict[str, float]


class MilestoneStatisticsResponse(BaseModel):
    """Schema for milestone statistics response"""
    milestone_code: str
    total_started: int
    total_completed: int
    total_failed: int
    average_completion_time_minutes: Optional[float] = None
    average_quality_score: Optional[float] = None
    completion_rate: float
    
    
class BulkDependencyValidationRequest(BaseModel):
    """Schema for bulk dependency validation request"""
    milestone_codes: List[str] = Field(..., min_items=1, max_items=50)


class BulkDependencyValidationResponse(BaseModel):
    """Schema for bulk dependency validation response"""
    validations: Dict[str, Dict[str, Any]]
    total_validated: int