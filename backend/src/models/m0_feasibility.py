"""
M0 Feasibility Snapshot Models

Database models for storing and managing M0 feasibility analysis data,
optimized for sub-60 second generation and efficient caching.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, JSON,
    DateTime, ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from .base import Base, TimestampMixin


class ViabilityScoreRange(str, Enum):
    """Viability score ranges for quick categorization."""
    VERY_LOW = "very_low"      # 0-20
    LOW = "low"                # 21-40
    MODERATE = "moderate"      # 41-60
    HIGH = "high"              # 61-80
    VERY_HIGH = "very_high"    # 81-100


class M0Status(str, Enum):
    """Status of M0 feasibility analysis."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


class M0FeasibilitySnapshot(Base, TimestampMixin):
    """
    Main M0 feasibility snapshot model.
    Stores the complete analysis result with optimized indexing for fast retrieval.
    """
    __tablename__ = "m0_feasibility_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    
    # Core idea information
    idea_name = Column(String(255), nullable=False)
    idea_summary = Column(Text, nullable=False)
    
    # User profile snapshot at time of analysis
    user_profile = Column(JSONB, nullable=False)  # experience, budget_band, timeline_months
    
    # Viability scoring
    viability_score = Column(Integer, nullable=False)
    score_range = Column(String(20), nullable=False)  # Enum value
    score_rationale = Column(Text, nullable=False)
    
    # Lean plan tiles (stored as structured JSON)
    lean_tiles = Column(JSONB, nullable=False)
    """
    Structure:
    {
        "problem": "...",
        "solution": "...",
        "audience": "...",
        "channels": ["..."],
        "price_band": {"min": X, "max": Y, "currency": "USD"},
        "differentiators": ["..."],
        "risks": ["..."],
        "assumptions": ["..."]
    }
    """
    
    # Competitive analysis
    competitors = Column(JSONB, nullable=False)
    """
    Structure:
    [
        {
            "name": "...",
            "angle": "...",
            "evidence_refs": ["ref_001", "ref_002"],
            "dates": ["2025-01-15", "2025-01-20"]
        }
    ]
    """
    
    # Price band
    price_band_min = Column(Float, nullable=True)
    price_band_max = Column(Float, nullable=True)
    price_band_currency = Column(String(3), default="USD")
    price_band_is_assumption = Column(Boolean, default=False)
    
    # Next steps
    next_steps = Column(JSONB, nullable=False)  # Array of step objects
    
    # Evidence and citations
    evidence_data = Column(JSONB, nullable=False)
    """
    Structure:
    [
        {
            "id": "ref_001",
            "title": "...",
            "date": "YYYY-MM-DD",
            "snippet": "...",
            "url": "...",
            "source_type": "web|academic|industry"
        }
    ]
    """
    
    # Analysis metadata
    signals = Column(JSONB, nullable=False)  # demand, trend, risk signals
    generation_time_ms = Column(Integer, nullable=False)  # Time taken to generate
    word_count = Column(Integer, nullable=False)
    max_words = Column(Integer, default=500)
    
    # Status and caching
    status = Column(String(20), nullable=False, default=M0Status.PENDING.value)
    is_cached = Column(Boolean, default=False)
    cache_key = Column(String(255), nullable=True, unique=True)
    cached_until = Column(DateTime, nullable=True)
    
    # Performance metrics
    research_time_ms = Column(Integer, nullable=True)
    analysis_time_ms = Column(Integer, nullable=True)
    total_api_calls = Column(Integer, default=0)
    
    # Version tracking for prompt evolution
    prompt_version = Column(String(20), default="1.0.0")
    
    # Relationships
    user = relationship("User", back_populates="m0_snapshots")
    research_cache = relationship("M0ResearchCache", back_populates="snapshot", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_m0_user_created", "user_id", "created_at"),
        Index("idx_m0_viability_score", "viability_score"),
        Index("idx_m0_status_cached", "status", "is_cached"),
        Index("idx_m0_cache_key", "cache_key"),
        CheckConstraint("viability_score >= 0 AND viability_score <= 100", name="check_viability_score_range"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "idea_name": self.idea_name,
            "idea_summary": self.idea_summary,
            "viability_score": self.viability_score,
            "score_range": self.score_range,
            "score_rationale": self.score_rationale,
            "lean_tiles": self.lean_tiles,
            "competitors": self.competitors,
            "price_band": {
                "min": self.price_band_min,
                "max": self.price_band_max,
                "currency": self.price_band_currency,
                "is_assumption": self.price_band_is_assumption
            },
            "next_steps": self.next_steps,
            "evidence": self.evidence_data,
            "signals": self.signals,
            "generation_time_ms": self.generation_time_ms,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def get_markdown_output(self) -> str:
        """Generate the markdown formatted output."""
        output = []
        
        # Header
        output.append(f"# {self.idea_name}")
        output.append("")
        
        # Viability Score
        output.append(f"**Viability Score:** {self.viability_score}/100 - {self.score_rationale}")
        output.append("")
        
        # Lean Plan Tiles
        output.append("## Lean Plan Tiles")
        tiles = self.lean_tiles
        output.append(f"- **Problem:** {tiles.get('problem', 'N/A')}")
        output.append(f"- **Solution:** {tiles.get('solution', 'N/A')}")
        output.append(f"- **Target Audience:** {tiles.get('audience', 'N/A')}")
        output.append(f"- **Channels:** {', '.join(tiles.get('channels', []))}")
        output.append(f"- **Differentiators:** {', '.join(tiles.get('differentiators', []))}")
        output.append(f"- **Key Risks:** {', '.join(tiles.get('risks', []))}")
        output.append(f"- **Key Assumptions:** {', '.join(tiles.get('assumptions', []))}")
        output.append("")
        
        # Top Competitors
        output.append("## Top Competitors")
        for comp in self.competitors:
            refs = ' '.join([f"[[{ref}]]" for ref in comp.get('evidence_refs', [])])
            output.append(f"- **{comp['name']}:** {comp['angle']} {refs}")
        output.append("")
        
        # Price Band
        output.append("## Likely Price Band")
        if self.price_band_is_assumption:
            output.append(f"${self.price_band_min:.0f}-${self.price_band_max:.0f} (Assumption - limited evidence)")
        else:
            output.append(f"${self.price_band_min:.0f}-${self.price_band_max:.0f}")
        output.append("")
        
        # Next 5 Steps
        output.append("## Next 5 Steps")
        for i, step in enumerate(self.next_steps, 1):
            output.append(f"{i}. {step}")
        output.append("")
        
        return "\n".join(output)


class M0ResearchCache(Base, TimestampMixin):
    """
    Cache for research data to speed up repeated M0 analyses.
    Stores pre-fetched and processed research data.
    """
    __tablename__ = "m0_research_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("m0_feasibility_snapshots.id"), nullable=True)
    
    # Cache key components
    idea_hash = Column(String(64), nullable=False, index=True)  # SHA256 of normalized idea
    research_query = Column(Text, nullable=False)
    
    # Cached data
    search_results = Column(JSONB, nullable=False)
    processed_evidence = Column(JSONB, nullable=False)
    competitor_data = Column(JSONB, nullable=False)
    market_signals = Column(JSONB, nullable=False)
    
    # Cache metadata
    fetch_time_ms = Column(Integer, nullable=False)
    is_valid = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    hit_count = Column(Integer, default=0)
    
    # Relationships
    snapshot = relationship("M0FeasibilitySnapshot", back_populates="research_cache")
    
    __table_args__ = (
        Index("idx_m0_research_hash_expires", "idea_hash", "expires_at"),
        UniqueConstraint("idea_hash", "research_query", name="uq_m0_research_cache"),
    )


class M0PerformanceLog(Base, TimestampMixin):
    """
    Performance logging for M0 generation to track and optimize sub-60s goal.
    """
    __tablename__ = "m0_performance_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey("m0_feasibility_snapshots.id"), nullable=False)
    
    # Timing breakdown (all in milliseconds)
    total_time_ms = Column(Integer, nullable=False)
    research_time_ms = Column(Integer, nullable=False)
    analysis_time_ms = Column(Integer, nullable=False)
    cache_lookup_time_ms = Column(Integer, nullable=True)
    db_time_ms = Column(Integer, nullable=True)
    
    # Resource usage
    api_calls = Column(JSONB, nullable=False)  # {service: count}
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    
    # Optimization flags
    used_cache = Column(Boolean, default=False)
    parallel_research = Column(Boolean, default=True)
    batch_processing = Column(Boolean, default=True)
    
    # Error tracking
    had_errors = Column(Boolean, default=False)
    error_details = Column(JSONB, nullable=True)
    
    __table_args__ = (
        Index("idx_m0_perf_total_time", "total_time_ms"),
        Index("idx_m0_perf_snapshot", "snapshot_id"),
    )