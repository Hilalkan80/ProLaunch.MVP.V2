"""
Context Layer Implementations

Implements the three-layer context system:
- Session Context (800 tokens): Immediate conversation context
- Journey Context (2000 tokens): Current task/milestone context  
- Knowledge Context (1200 tokens): Long-term user knowledge
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from .base import (
    BaseContextLayer,
    ContextLayerType,
    ContextLayerConfig,
    ContextEntry
)
from ..mcp_integrations import (
    MemoryBankMCP,
    PostgreSQLMCP,
    RedisMCP,
    RefMCP
)

logger = logging.getLogger(__name__)


class SessionContext(BaseContextLayer):
    """
    Session Context Layer (800 tokens)
    
    Manages immediate conversation context including:
    - Recent messages and responses
    - Current user intent
    - Active tool interactions
    - Temporary state
    """
    
    def __init__(self, user_id: str, session_id: str):
        config = ContextLayerConfig(
            max_tokens=800,
            retention_period=timedelta(hours=2),
            compression_threshold=0.75,
            auto_summarize=False,  # Keep raw for immediate context
            vector_enabled=False,  # No vectors for ephemeral data
            cache_enabled=True,
            cache_ttl=300  # 5 minutes
        )
        super().__init__(
            ContextLayerType.SESSION,
            config,
            user_id,
            session_id
        )
        self.redis_mcp = RedisMCP()
        self.message_buffer: List[Dict[str, str]] = []
        
    async def add_entry(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add new entry to session context"""
        try:
            # Calculate tokens
            token_count = self.calculate_tokens(content)
            
            # Check if we need to make room
            if self.current_tokens + token_count > self.config.max_tokens:
                await self.optimize()
            
            # Create entry
            entry = ContextEntry(
                content=content,
                timestamp=datetime.utcnow(),
                token_count=token_count,
                metadata=metadata or {}
            )
            
            # Add to entries
            self.entries.append(entry)
            self.current_tokens += token_count
            
            # Add to message buffer for quick access
            if metadata and metadata.get("type") == "message":
                self.message_buffer.append({
                    "role": metadata.get("role", "user"),
                    "content": content,
                    "timestamp": entry.timestamp.isoformat()
                })
                
                # Keep only last 10 messages in buffer
                if len(self.message_buffer) > 10:
                    self.message_buffer = self.message_buffer[-10:]
            
            # Cache in Redis
            if self.config.cache_enabled:
                cache_key = f"session:{self.session_id}:latest"
                await self.redis_mcp.set_cache(
                    cache_key,
                    {
                        "entries": self.export_entries()[-5:],  # Last 5 entries
                        "buffer": self.message_buffer
                    },
                    expiry=self.config.cache_ttl
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding session entry: {e}")
            return False
    
    async def get_context(
        self,
        max_tokens: Optional[int] = None,
        query: Optional[str] = None
    ) -> str:
        """Get formatted session context"""
        try:
            # Use configured max if not specified
            max_tokens = max_tokens or self.config.max_tokens
            
            # Remove expired entries
            self.remove_expired_entries()
            
            # For session, prioritize recent entries
            self.entries.sort(key=lambda e: e.timestamp, reverse=True)
            
            # Get entries within budget
            selected_entries = self.truncate_to_budget(max_tokens)
            
            # Reverse to chronological order for context
            selected_entries.reverse()
            
            # Format as conversation
            if self.message_buffer:
                # Use message buffer for cleaner format
                messages = []
                for msg in self.message_buffer[-5:]:  # Last 5 messages
                    role = msg["role"].upper()
                    messages.append(f"{role}: {msg['content']}")
                return "\n".join(messages)
            
            # Fallback to standard format
            return self.format_entries(selected_entries)
            
        except Exception as e:
            logger.error(f"Error getting session context: {e}")
            return ""
    
    async def optimize(self) -> None:
        """Optimize session context by removing old entries"""
        try:
            # Remove expired entries
            self.remove_expired_entries()
            
            # Remove oldest entries if still over budget
            while self.current_tokens > self.config.max_tokens * 0.7:
                if self.entries:
                    removed = self.entries.pop(0)
                    self.current_tokens -= removed.token_count
                else:
                    break
            
            self.last_optimization = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error optimizing session context: {e}")
    
    async def persist(self) -> None:
        """Persist session context to Redis"""
        try:
            key = f"session_context:{self.user_id}:{self.session_id}"
            data = {
                "entries": self.export_entries(),
                "message_buffer": self.message_buffer,
                "metadata": self.metadata,
                "last_optimization": self.last_optimization.isoformat()
            }
            
            await self.redis_mcp.set_cache(
                key,
                data,
                expiry=int(self.config.retention_period.total_seconds())
            )
            
        except Exception as e:
            logger.error(f"Error persisting session context: {e}")
    
    async def load(self) -> None:
        """Load session context from Redis"""
        try:
            key = f"session_context:{self.user_id}:{self.session_id}"
            data = await self.redis_mcp.get_cache(key)
            
            if data:
                self.import_entries(data.get("entries", []))
                self.message_buffer = data.get("message_buffer", [])
                self.metadata = data.get("metadata", {})
                if data.get("last_optimization"):
                    self.last_optimization = datetime.fromisoformat(
                        data["last_optimization"]
                    )
                    
        except Exception as e:
            logger.error(f"Error loading session context: {e}")


class JourneyContext(BaseContextLayer):
    """
    Journey Context Layer (2000 tokens)
    
    Manages current task/milestone context including:
    - Active milestone objectives
    - Task progress and history
    - Recent accomplishments
    - Current roadblocks
    """
    
    def __init__(self, user_id: str, session_id: str):
        config = ContextLayerConfig(
            max_tokens=2000,
            retention_period=timedelta(days=7),
            compression_threshold=0.8,
            auto_summarize=True,
            vector_enabled=True,
            cache_enabled=True,
            cache_ttl=1800  # 30 minutes
        )
        super().__init__(
            ContextLayerType.JOURNEY,
            config,
            user_id,
            session_id
        )
        self.memory_mcp = MemoryBankMCP()
        self.postgres_mcp = PostgreSQLMCP()
        self.redis_mcp = RedisMCP()
        self.current_milestone: Optional[str] = None
        self.task_history: List[Dict[str, Any]] = []
        
    async def add_entry(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add new entry to journey context"""
        try:
            # Calculate tokens
            token_count = self.calculate_tokens(content)
            
            # Check if optimization needed
            if self.current_tokens + token_count > self.config.max_tokens:
                await self.optimize()
            
            # Create entry
            entry = ContextEntry(
                content=content,
                timestamp=datetime.utcnow(),
                token_count=token_count,
                metadata=metadata or {}
            )
            
            # Generate vector if enabled
            if self.config.vector_enabled and metadata and metadata.get("important"):
                vector_id = await self.postgres_mcp.store_vector(
                    content=content,
                    metadata={
                        "user_id": self.user_id,
                        "type": "journey",
                        "milestone": self.current_milestone,
                        **metadata
                    }
                )
                entry.vector_id = vector_id
            
            # Add to entries
            self.entries.append(entry)
            self.current_tokens += token_count
            
            # Track task history
            if metadata and metadata.get("type") == "task":
                self.task_history.append({
                    "task": content,
                    "status": metadata.get("status", "in_progress"),
                    "timestamp": entry.timestamp.isoformat(),
                    "milestone": self.current_milestone
                })
            
            # Persist to Memory Bank for long-term storage
            if metadata and metadata.get("persist", False):
                await self.memory_mcp.store_memory(
                    key=f"journey:{self.user_id}:{entry.timestamp.timestamp()}",
                    content=content,
                    metadata=metadata
                )
            
            # Update cache
            await self._update_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding journey entry: {e}")
            return False
    
    async def get_context(
        self,
        max_tokens: Optional[int] = None,
        query: Optional[str] = None
    ) -> str:
        """Get formatted journey context"""
        try:
            max_tokens = max_tokens or self.config.max_tokens
            
            # Remove expired entries
            self.remove_expired_entries()
            
            # If query provided, use vector search
            if query and self.config.vector_enabled:
                relevant_entries = await self._get_relevant_entries(query)
            else:
                relevant_entries = self.entries
            
            # Sort by relevance and recency
            self.sort_by_relevance(query)
            
            # Get entries within budget
            selected_entries = self.truncate_to_budget(max_tokens)
            
            # Format with milestone context
            context_parts = []
            
            if self.current_milestone:
                context_parts.append(f"CURRENT MILESTONE: {self.current_milestone}")
            
            # Add recent tasks
            recent_tasks = self.task_history[-5:]
            if recent_tasks:
                context_parts.append("\nRECENT TASKS:")
                for task in recent_tasks:
                    status_icon = "✓" if task["status"] == "completed" else "→"
                    context_parts.append(f"  {status_icon} {task['task']}")
            
            # Add journey entries
            if selected_entries:
                context_parts.append("\nJOURNEY CONTEXT:")
                context_parts.append(self.format_entries(selected_entries))
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting journey context: {e}")
            return ""
    
    async def optimize(self) -> None:
        """Optimize journey context through summarization"""
        try:
            # Group entries by day
            entries_by_day: Dict[str, List[ContextEntry]] = {}
            
            for entry in self.entries:
                day_key = entry.timestamp.date().isoformat()
                if day_key not in entries_by_day:
                    entries_by_day[day_key] = []
                entries_by_day[day_key].append(entry)
            
            # Summarize old days
            cutoff_date = (datetime.utcnow() - timedelta(days=2)).date()
            optimized_entries = []
            
            for day_key, day_entries in entries_by_day.items():
                day_date = datetime.fromisoformat(day_key).date()
                
                if day_date < cutoff_date and len(day_entries) > 3:
                    # Summarize this day's entries
                    summary = await self._summarize_entries(day_entries)
                    if summary:
                        optimized_entries.append(summary)
                else:
                    # Keep original entries
                    optimized_entries.extend(day_entries)
            
            self.entries = optimized_entries
            self.current_tokens = self.get_total_tokens()
            self.last_optimization = datetime.utcnow()
            
            # Deduplicate
            self.deduplicate_entries()
            
        except Exception as e:
            logger.error(f"Error optimizing journey context: {e}")
    
    async def persist(self) -> None:
        """Persist journey context to Memory Bank and PostgreSQL"""
        try:
            # Store in Memory Bank
            key = f"journey_context:{self.user_id}"
            await self.memory_mcp.store_memory(
                key=key,
                content={
                    "entries": self.export_entries(),
                    "current_milestone": self.current_milestone,
                    "task_history": self.task_history,
                    "metadata": self.metadata
                },
                metadata={
                    "user_id": self.user_id,
                    "session_id": self.session_id,
                    "type": "journey_context"
                }
            )
            
            # Store important entries as vectors
            for entry in self.entries:
                if entry.metadata.get("important") and not entry.vector_id:
                    vector_id = await self.postgres_mcp.store_vector(
                        content=entry.content,
                        metadata={
                            "user_id": self.user_id,
                            "type": "journey",
                            **entry.metadata
                        }
                    )
                    entry.vector_id = vector_id
                    
        except Exception as e:
            logger.error(f"Error persisting journey context: {e}")
    
    async def load(self) -> None:
        """Load journey context from storage"""
        try:
            key = f"journey_context:{self.user_id}"
            data = await self.memory_mcp.retrieve_memory(key)
            
            if data and isinstance(data, dict):
                content = data.get("content", {})
                if isinstance(content, dict):
                    self.import_entries(content.get("entries", []))
                    self.current_milestone = content.get("current_milestone")
                    self.task_history = content.get("task_history", [])
                    self.metadata = content.get("metadata", {})
                    
        except Exception as e:
            logger.error(f"Error loading journey context: {e}")
    
    async def _get_relevant_entries(self, query: str) -> List[ContextEntry]:
        """Get relevant entries using vector search"""
        try:
            # Search vectors
            results = await self.postgres_mcp.search_vectors(
                query=query,
                filters={"user_id": self.user_id, "type": "journey"},
                limit=10
            )
            
            # Map results to entries
            relevant_entries = []
            for result in results:
                for entry in self.entries:
                    if entry.vector_id == result.get("id"):
                        entry.relevance_score = result.get("score", 0.5)
                        relevant_entries.append(entry)
                        break
            
            return relevant_entries
            
        except Exception as e:
            logger.error(f"Error getting relevant entries: {e}")
            return self.entries
    
    async def _summarize_entries(
        self,
        entries: List[ContextEntry]
    ) -> Optional[ContextEntry]:
        """Summarize multiple entries into one"""
        try:
            # Combine content
            combined_content = "\n".join(e.content for e in entries)
            
            # Use RefMCP for optimization
            ref_mcp = RefMCP()
            summary = await ref_mcp.optimize_content(
                content=combined_content,
                max_tokens=200
            )
            
            if summary:
                return ContextEntry(
                    content=summary,
                    timestamp=entries[0].timestamp,  # Use earliest timestamp
                    token_count=self.calculate_tokens(summary),
                    metadata={
                        "type": "summary",
                        "original_count": len(entries),
                        "date": entries[0].timestamp.date().isoformat()
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error summarizing entries: {e}")
            return None
    
    async def _update_cache(self) -> None:
        """Update Redis cache"""
        try:
            cache_key = f"journey:{self.user_id}:cache"
            await self.redis_mcp.set_cache(
                cache_key,
                {
                    "current_milestone": self.current_milestone,
                    "recent_tasks": self.task_history[-10:],
                    "entry_count": len(self.entries),
                    "token_usage": self.current_tokens
                },
                expiry=self.config.cache_ttl
            )
        except Exception as e:
            logger.error(f"Error updating journey cache: {e}")


class KnowledgeContext(BaseContextLayer):
    """
    Knowledge Context Layer (1200 tokens)
    
    Manages long-term user knowledge including:
    - User preferences and patterns
    - Domain expertise
    - Historical decisions
    - Learned optimizations
    """
    
    def __init__(self, user_id: str, session_id: str):
        config = ContextLayerConfig(
            max_tokens=1200,
            retention_period=timedelta(days=90),
            compression_threshold=0.85,
            auto_summarize=True,
            vector_enabled=True,
            cache_enabled=True,
            cache_ttl=3600  # 1 hour
        )
        super().__init__(
            ContextLayerType.KNOWLEDGE,
            config,
            user_id,
            session_id
        )
        self.memory_mcp = MemoryBankMCP()
        self.postgres_mcp = PostgreSQLMCP()
        self.redis_mcp = RedisMCP()
        self.knowledge_graph: Dict[str, List[str]] = {}
        self.user_profile: Dict[str, Any] = {}
        
    async def add_entry(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add new entry to knowledge context"""
        try:
            # Calculate tokens
            token_count = self.calculate_tokens(content)
            
            # Check if optimization needed
            if self.current_tokens + token_count > self.config.max_tokens:
                await self.optimize()
            
            # Create entry
            entry = ContextEntry(
                content=content,
                timestamp=datetime.utcnow(),
                token_count=token_count,
                metadata=metadata or {}
            )
            
            # Always store knowledge as vectors
            if self.config.vector_enabled:
                vector_id = await self.postgres_mcp.store_vector(
                    content=content,
                    metadata={
                        "user_id": self.user_id,
                        "type": "knowledge",
                        "category": metadata.get("category", "general"),
                        **metadata
                    }
                )
                entry.vector_id = vector_id
            
            # Add to entries
            self.entries.append(entry)
            self.current_tokens += token_count
            
            # Update knowledge graph
            if metadata and metadata.get("category"):
                category = metadata["category"]
                if category not in self.knowledge_graph:
                    self.knowledge_graph[category] = []
                self.knowledge_graph[category].append(content[:100])  # Store snippet
            
            # Update user profile
            if metadata and metadata.get("profile_update"):
                self.user_profile.update(metadata["profile_update"])
            
            # Persist to Memory Bank
            await self.memory_mcp.store_memory(
                key=f"knowledge:{self.user_id}:{entry.get_hash()}",
                content=content,
                metadata={
                    "permanent": True,
                    **metadata
                }
            )
            
            # Update cache
            await self._update_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding knowledge entry: {e}")
            return False
    
    async def get_context(
        self,
        max_tokens: Optional[int] = None,
        query: Optional[str] = None
    ) -> str:
        """Get formatted knowledge context"""
        try:
            max_tokens = max_tokens or self.config.max_tokens
            
            # Always use vector search for knowledge
            if query:
                relevant_entries = await self._get_relevant_knowledge(query)
            else:
                # Get most important/recent knowledge
                relevant_entries = sorted(
                    self.entries,
                    key=lambda e: (
                        e.metadata.get("importance", 0),
                        e.relevance_score,
                        e.timestamp
                    ),
                    reverse=True
                )
            
            # Get entries within budget
            selected_entries = []
            current_count = 0
            
            for entry in relevant_entries:
                if current_count + entry.token_count <= max_tokens:
                    selected_entries.append(entry)
                    current_count += entry.token_count
                else:
                    break
            
            # Format knowledge context
            context_parts = []
            
            # Add user profile if available
            if self.user_profile:
                profile_items = []
                for key, value in self.user_profile.items():
                    profile_items.append(f"  - {key}: {value}")
                if profile_items:
                    context_parts.append("USER PROFILE:")
                    context_parts.extend(profile_items)
            
            # Add knowledge categories
            if self.knowledge_graph:
                context_parts.append("\nKNOWLEDGE AREAS:")
                for category, items in list(self.knowledge_graph.items())[:5]:
                    context_parts.append(f"  • {category}: {len(items)} items")
            
            # Add selected knowledge entries
            if selected_entries:
                context_parts.append("\nRELEVANT KNOWLEDGE:")
                for entry in selected_entries:
                    category = entry.metadata.get("category", "general")
                    context_parts.append(f"  [{category}] {entry.content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting knowledge context: {e}")
            return ""
    
    async def optimize(self) -> None:
        """Optimize knowledge through consolidation and summarization"""
        try:
            # Group by category
            entries_by_category: Dict[str, List[ContextEntry]] = {}
            
            for entry in self.entries:
                category = entry.metadata.get("category", "general")
                if category not in entries_by_category:
                    entries_by_category[category] = []
                entries_by_category[category].append(entry)
            
            # Consolidate each category
            optimized_entries = []
            
            for category, category_entries in entries_by_category.items():
                if len(category_entries) > 5:
                    # Consolidate this category
                    consolidated = await self._consolidate_knowledge(
                        category,
                        category_entries
                    )
                    if consolidated:
                        optimized_entries.append(consolidated)
                else:
                    # Keep original entries
                    optimized_entries.extend(category_entries)
            
            self.entries = optimized_entries
            self.current_tokens = self.get_total_tokens()
            self.last_optimization = datetime.utcnow()
            
            # Remove duplicates
            self.deduplicate_entries()
            
        except Exception as e:
            logger.error(f"Error optimizing knowledge context: {e}")
    
    async def persist(self) -> None:
        """Persist knowledge context to all storage layers"""
        try:
            # Store complete knowledge base
            key = f"knowledge_context:{self.user_id}"
            await self.memory_mcp.store_memory(
                key=key,
                content={
                    "entries": self.export_entries(),
                    "knowledge_graph": self.knowledge_graph,
                    "user_profile": self.user_profile,
                    "metadata": self.metadata
                },
                metadata={
                    "user_id": self.user_id,
                    "type": "knowledge_context",
                    "permanent": True
                }
            )
            
            # Ensure all entries have vectors
            for entry in self.entries:
                if not entry.vector_id:
                    vector_id = await self.postgres_mcp.store_vector(
                        content=entry.content,
                        metadata={
                            "user_id": self.user_id,
                            "type": "knowledge",
                            **entry.metadata
                        }
                    )
                    entry.vector_id = vector_id
                    
        except Exception as e:
            logger.error(f"Error persisting knowledge context: {e}")
    
    async def load(self) -> None:
        """Load knowledge context from storage"""
        try:
            key = f"knowledge_context:{self.user_id}"
            data = await self.memory_mcp.retrieve_memory(key)
            
            if data and isinstance(data, dict):
                content = data.get("content", {})
                if isinstance(content, dict):
                    self.import_entries(content.get("entries", []))
                    self.knowledge_graph = content.get("knowledge_graph", {})
                    self.user_profile = content.get("user_profile", {})
                    self.metadata = content.get("metadata", {})
                    
        except Exception as e:
            logger.error(f"Error loading knowledge context: {e}")
    
    async def _get_relevant_knowledge(self, query: str) -> List[ContextEntry]:
        """Get relevant knowledge using vector search"""
        try:
            # Search vectors with knowledge filter
            results = await self.postgres_mcp.search_vectors(
                query=query,
                filters={"user_id": self.user_id, "type": "knowledge"},
                limit=15
            )
            
            # Map results to entries
            relevant_entries = []
            for result in results:
                for entry in self.entries:
                    if entry.vector_id == result.get("id"):
                        entry.relevance_score = result.get("score", 0.5)
                        relevant_entries.append(entry)
                        break
            
            # Also search Memory Bank for historical knowledge
            historical = await self.memory_mcp.search_memories(
                query=query,
                filters={"user_id": self.user_id, "type": "knowledge"}
            )
            
            # Merge historical if not already present
            for hist in historical:
                if not any(e.get_hash() == hist.get("hash") for e in relevant_entries):
                    # Create entry from historical
                    entry = ContextEntry(
                        content=hist.get("content", ""),
                        timestamp=datetime.fromisoformat(
                            hist.get("timestamp", datetime.utcnow().isoformat())
                        ),
                        token_count=self.calculate_tokens(hist.get("content", "")),
                        metadata=hist.get("metadata", {}),
                        relevance_score=hist.get("score", 0.3)
                    )
                    relevant_entries.append(entry)
            
            return sorted(
                relevant_entries,
                key=lambda e: e.relevance_score,
                reverse=True
            )
            
        except Exception as e:
            logger.error(f"Error getting relevant knowledge: {e}")
            return self.entries
    
    async def _consolidate_knowledge(
        self,
        category: str,
        entries: List[ContextEntry]
    ) -> Optional[ContextEntry]:
        """Consolidate multiple knowledge entries"""
        try:
            # Extract key points
            key_points = []
            for entry in entries:
                # Use first 100 chars as key point
                key_points.append(entry.content[:100])
            
            # Create consolidated entry
            consolidated_content = f"Consolidated {category} knowledge:\n"
            consolidated_content += "\n".join(f"• {point}" for point in key_points[:10])
            
            # Use RefMCP for final optimization
            ref_mcp = RefMCP()
            optimized = await ref_mcp.optimize_content(
                content=consolidated_content,
                max_tokens=300
            )
            
            if optimized:
                return ContextEntry(
                    content=optimized,
                    timestamp=datetime.utcnow(),
                    token_count=self.calculate_tokens(optimized),
                    metadata={
                        "type": "consolidated",
                        "category": category,
                        "original_count": len(entries),
                        "importance": max(
                            e.metadata.get("importance", 0) for e in entries
                        )
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error consolidating knowledge: {e}")
            return None
    
    async def _update_cache(self) -> None:
        """Update Redis cache with knowledge summary"""
        try:
            cache_key = f"knowledge:{self.user_id}:summary"
            await self.redis_mcp.set_cache(
                cache_key,
                {
                    "user_profile": self.user_profile,
                    "knowledge_categories": list(self.knowledge_graph.keys()),
                    "total_entries": len(self.entries),
                    "token_usage": self.current_tokens
                },
                expiry=self.config.cache_ttl
            )
        except Exception as e:
            logger.error(f"Error updating knowledge cache: {e}")