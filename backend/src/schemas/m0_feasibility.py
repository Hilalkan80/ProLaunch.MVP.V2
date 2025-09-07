"""
M0 Feasibility Snapshot Schemas

Pydantic schemas for M0 feasibility API requests and responses.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator
from enum import Enum


class UserExperience(str, Enum):
    """User experience levels."""
    NONE = "none"
    SOME = "some"
    EXPERIENCED = "experienced"


class BudgetBand(str, Enum):
    """Budget bands for business launch."""
    UNDER_5K = "<5k"
    BAND_5K_25K = "5k-25k"
    BAND_25K_100K = "25k-100k"
    OVER_100K = "100k+"


class M0GenerateRequest(BaseModel):
    """Request schema for M0 generation."""
    
    idea_summary: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Business idea summary"
    )
    
    project_id: Optional[str] = Field(
        None,
        description="Optional project ID to associate with"
    )
    
    user_experience: Optional[UserExperience] = Field(
        UserExperience.NONE,
        description="User's business experience level"
    )
    
    budget_band: Optional[BudgetBand] = Field(
        BudgetBand.UNDER_5K,
        description="Available budget for launch"
    )
    
    timeline_months: Optional[int] = Field(
        6,
        ge=1,
        le=36,
        description="Timeline for launch in months"
    )
    
    use_cache: bool = Field(
        True,
        description="Whether to use cached results if available"
    )
    
    allow_similar_match: bool = Field(
        True,
        description="Allow returning similar cached ideas (85%+ similarity)"
    )
    
    enable_preloading: bool = Field(
        False,
        description="Enable predictive preloading of related ideas"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "idea_summary": "An online marketplace for handmade crafts connecting local artisans with customers",
                "user_experience": "some",
                "budget_band": "5k-25k",
                "timeline_months": 6,
                "use_cache": True
            }
        }


class LeanTile(BaseModel):
    """Lean canvas tile data."""
    problem: str
    solution: str
    audience: str
    channels: List[str]
    differentiators: List[str]
    risks: List[str]
    assumptions: List[str]


class Competitor(BaseModel):
    """Competitor information."""
    name: str
    angle: str
    evidence_refs: List[str]
    dates: List[str]


class PriceBand(BaseModel):
    """Price band information."""
    min: Optional[float]
    max: Optional[float]
    currency: str = "USD"
    is_assumption: bool


class Evidence(BaseModel):
    """Evidence/citation data."""
    id: str
    title: str
    date: str
    snippet: str
    url: str
    source_type: Optional[str] = "web"


class M0Snapshot(BaseModel):
    """M0 feasibility snapshot data."""
    id: str
    idea_name: str
    idea_summary: str
    viability_score: int = Field(ge=0, le=100)
    score_range: str
    score_rationale: str
    lean_tiles: LeanTile
    competitors: List[Competitor]
    price_band: PriceBand
    next_steps: List[str]
    evidence: List[Evidence]
    signals: Dict[str, str]
    generation_time_ms: int
    status: str
    created_at: datetime


class M0GenerateResponse(BaseModel):
    """Response schema for M0 generation."""
    success: bool
    snapshot_id: str
    snapshot: Dict[str, Any]
    from_cache: bool
    generation_time_ms: int
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "snapshot_id": "123e4567-e89b-12d3-a456-426614174000",
                "snapshot": {
                    "viability_score": 72,
                    "score_rationale": "Strong market demand with moderate competition"
                },
                "from_cache": False,
                "generation_time_ms": 45000,
                "message": "M0 snapshot generated successfully"
            }
        }


class M0SnapshotResponse(BaseModel):
    """Response schema for single M0 snapshot retrieval."""
    snapshot: Dict[str, Any]
    markdown_output: str
    performance: Optional[Dict[str, Any]] = None


class M0ListResponse(BaseModel):
    """Response schema for listing M0 snapshots."""
    snapshots: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class M0PerformanceMetrics(BaseModel):
    """M0 system performance metrics."""
    total_generations: int
    avg_time_ms: float
    min_time_ms: int
    max_time_ms: int
    within_target_rate: float = Field(
        ...,
        ge=0,
        le=1,
        description="Percentage within 60s target"
    )
    cache_hit_rate: float = Field(
        ...,
        ge=0,
        le=1,
        description="Cache hit rate"
    )
    success_rate: float = Field(
        ...,
        ge=0,
        le=1,
        description="Success rate"
    )
    time_range: str
    breakdown: Optional[Dict[str, float]] = None
    service_metrics: Optional[Dict[str, Any]] = None
    cache_metrics: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_generations": 150,
                "avg_time_ms": 52000,
                "min_time_ms": 15000,
                "max_time_ms": 89000,
                "within_target_rate": 0.87,
                "cache_hit_rate": 0.35,
                "success_rate": 0.96,
                "time_range": "24h",
                "breakdown": {
                    "avg_research_ms": 25000,
                    "avg_analysis_ms": 20000,
                    "avg_cache_lookup_ms": 500
                }
            }
        }


class M0CacheInvalidateRequest(BaseModel):
    """Request schema for cache invalidation."""
    idea_summary: Optional[str] = None
    invalidate_all: bool = False


class M0ExportFormat(str, Enum):
    """Export format options."""
    MARKDOWN = "markdown"
    JSON = "json"
    PDF = "pdf"


class M0BulkGenerateRequest(BaseModel):
    """Request schema for bulk M0 generation."""
    ideas: List[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="List of ideas to analyze"
    )
    user_experience: Optional[UserExperience] = UserExperience.NONE
    budget_band: Optional[BudgetBand] = BudgetBand.UNDER_5K
    timeline_months: Optional[int] = 6
    parallel: bool = Field(
        True,
        description="Process ideas in parallel"
    )
    
    @validator("ideas")
    def validate_ideas(cls, v):
        """Validate each idea has minimum length."""
        for idea in v:
            if len(idea) < 10:
                raise ValueError(f"Each idea must be at least 10 characters: {idea}")
        return v


class M0ComparisonRequest(BaseModel):
    """Request schema for comparing multiple M0 snapshots."""
    snapshot_ids: List[str] = Field(
        ...,
        min_items=2,
        max_items=5,
        description="Snapshot IDs to compare"
    )
    comparison_criteria: Optional[List[str]] = Field(
        None,
        description="Specific criteria to compare"
    )


class M0ComparisonResponse(BaseModel):
    """Response schema for M0 comparison."""
    comparison: Dict[str, Any]
    winner: Optional[str] = None
    recommendation: str
    detailed_analysis: Dict[str, Any]