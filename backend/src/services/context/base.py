"""
Base Context Layer

Provides the abstract base class for all context layers and common functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import hashlib
from enum import Enum


class ContextLayerType(Enum):
    """Types of context layers in the system"""
    SESSION = "session"
    JOURNEY = "journey"
    KNOWLEDGE = "knowledge"


@dataclass
class ContextEntry:
    """Represents a single context entry"""
    content: str
    timestamp: datetime
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    vector_id: Optional[str] = None
    relevance_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "token_count": self.token_count,
            "metadata": self.metadata,
            "vector_id": self.vector_id,
            "relevance_score": self.relevance_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        """Create from dictionary"""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
    
    def get_hash(self) -> str:
        """Generate hash for deduplication"""
        content_hash = hashlib.sha256(self.content.encode()).hexdigest()
        return content_hash[:16]


@dataclass
class ContextLayerConfig:
    """Configuration for a context layer"""
    max_tokens: int
    retention_period: timedelta
    compression_threshold: float = 0.8  # Compress when 80% full
    auto_summarize: bool = True
    vector_enabled: bool = True
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds


class BaseContextLayer(ABC):
    """
    Abstract base class for context layers.
    
    Each layer manages its own token budget, persistence, and optimization.
    """
    
    def __init__(
        self,
        layer_type: ContextLayerType,
        config: ContextLayerConfig,
        user_id: str,
        session_id: str
    ):
        self.layer_type = layer_type
        self.config = config
        self.user_id = user_id
        self.session_id = session_id
        self.entries: List[ContextEntry] = []
        self.current_tokens = 0
        self.last_optimization = datetime.utcnow()
        self.metadata: Dict[str, Any] = {}
        
    @abstractmethod
    async def add_entry(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add new entry to the context layer"""
        pass
    
    @abstractmethod
    async def get_context(
        self,
        max_tokens: Optional[int] = None,
        query: Optional[str] = None
    ) -> str:
        """Retrieve formatted context within token budget"""
        pass
    
    @abstractmethod
    async def optimize(self) -> None:
        """Optimize context by compression, summarization, or removal"""
        pass
    
    @abstractmethod
    async def persist(self) -> None:
        """Persist context to storage"""
        pass
    
    @abstractmethod
    async def load(self) -> None:
        """Load context from storage"""
        pass
    
    def calculate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        Uses approximation: 1 token ≈ 4 characters
        """
        return len(text) // 4
    
    def get_total_tokens(self) -> int:
        """Get total token count across all entries"""
        return sum(entry.token_count for entry in self.entries)
    
    def needs_optimization(self) -> bool:
        """Check if layer needs optimization"""
        utilization = self.current_tokens / self.config.max_tokens
        return utilization >= self.config.compression_threshold
    
    def remove_expired_entries(self) -> None:
        """Remove entries older than retention period"""
        cutoff = datetime.utcnow() - self.config.retention_period
        self.entries = [
            entry for entry in self.entries
            if entry.timestamp > cutoff
        ]
        self.current_tokens = self.get_total_tokens()
    
    def deduplicate_entries(self) -> None:
        """Remove duplicate entries based on content hash"""
        seen_hashes = set()
        unique_entries = []
        
        for entry in self.entries:
            entry_hash = entry.get_hash()
            if entry_hash not in seen_hashes:
                seen_hashes.add(entry_hash)
                unique_entries.append(entry)
        
        self.entries = unique_entries
        self.current_tokens = self.get_total_tokens()
    
    def sort_by_relevance(self, query: Optional[str] = None) -> None:
        """Sort entries by relevance score and recency"""
        if query:
            # TODO: Implement semantic relevance scoring with query
            pass
        
        # Sort by relevance score and timestamp
        self.entries.sort(
            key=lambda e: (e.relevance_score, e.timestamp),
            reverse=True
        )
    
    def truncate_to_budget(self, max_tokens: int) -> List[ContextEntry]:
        """
        Truncate entries to fit within token budget.
        Returns entries that fit within budget.
        """
        selected_entries = []
        current_count = 0
        
        for entry in self.entries:
            if current_count + entry.token_count <= max_tokens:
                selected_entries.append(entry)
                current_count += entry.token_count
            else:
                break
        
        return selected_entries
    
    def format_entries(self, entries: List[ContextEntry]) -> str:
        """Format entries into context string"""
        if not entries:
            return ""
        
        formatted_parts = []
        for entry in entries:
            timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            # Add metadata if present
            metadata_str = ""
            if entry.metadata:
                metadata_str = f" [{', '.join(f'{k}={v}' for k, v in entry.metadata.items())}]"
            
            formatted_parts.append(
                f"[{timestamp_str}]{metadata_str}: {entry.content}"
            )
        
        return "\n".join(formatted_parts)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get layer statistics"""
        return {
            "layer_type": self.layer_type.value,
            "total_entries": len(self.entries),
            "current_tokens": self.current_tokens,
            "max_tokens": self.config.max_tokens,
            "utilization_percentage": round(
                (self.current_tokens / self.config.max_tokens) * 100, 2
            ),
            "oldest_entry": min(
                (e.timestamp for e in self.entries),
                default=None
            ),
            "newest_entry": max(
                (e.timestamp for e in self.entries),
                default=None
            ),
            "last_optimization": self.last_optimization.isoformat(),
            "needs_optimization": self.needs_optimization()
        }
    
    def clear(self) -> None:
        """Clear all entries from the layer"""
        self.entries = []
        self.current_tokens = 0
        self.metadata = {}
    
    def export_entries(self) -> List[Dict[str, Any]]:
        """Export all entries as dictionaries"""
        return [entry.to_dict() for entry in self.entries]
    
    def import_entries(self, entries_data: List[Dict[str, Any]]) -> None:
        """Import entries from dictionaries"""
        self.entries = [
            ContextEntry.from_dict(data) for data in entries_data
        ]
        self.current_tokens = self.get_total_tokens()