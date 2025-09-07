"""
Context Manager

Main orchestrator for the three-layer context management system.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import logging

from .layers import SessionContext, JourneyContext, KnowledgeContext
from .token_manager import TokenBudgetManager
from .base import ContextLayerType
from ..mcp_integrations import RefMCP

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Orchestrates the three-layer context management system.
    
    Manages:
    - Session Context (800 tokens)
    - Journey Context (2000 tokens)  
    - Knowledge Context (1200 tokens)
    - Token budget allocation
    - Real-time updates
    - Optimization and caching
    """
    
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        
        # Initialize layers
        self.session_context = SessionContext(user_id, session_id)
        self.journey_context = JourneyContext(user_id, session_id)
        self.knowledge_context = KnowledgeContext(user_id, session_id)
        
        # Initialize token manager
        self.token_manager = TokenBudgetManager(total_budget=4000)
        
        # Initialize optimization module
        self.ref_mcp = RefMCP()
        
        # Track context state
        self.is_initialized = False
        self.last_update = datetime.utcnow()
        self.update_queue: List[Dict[str, Any]] = []
        
        # Performance metrics
        self.metrics = {
            "total_updates": 0,
            "optimization_count": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    async def initialize(self) -> bool:
        """
        Initialize context manager and load existing context.
        
        Returns:
            Success status
        """
        try:
            logger.info(f"Initializing context manager for user {self.user_id}")
            
            # Load existing context layers
            await asyncio.gather(
                self.session_context.load(),
                self.journey_context.load(),
                self.knowledge_context.load()
            )
            
            # Update token allocations based on loaded content
            self._update_token_allocations()
            
            self.is_initialized = True
            logger.info("Context manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing context manager: {e}")
            return False
    
    async def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to the appropriate context layers.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Additional metadata
            
        Returns:
            Success status
        """
        try:
            # Prepare metadata
            message_metadata = {
                "role": role,
                "type": "message",
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            # Add to session context (always)
            session_success = await self.session_context.add_entry(
                content,
                message_metadata
            )
            
            # Determine if should add to other layers
            should_add_to_journey = self._should_add_to_journey(content, metadata)
            should_add_to_knowledge = self._should_add_to_knowledge(content, metadata)
            
            # Add to journey if relevant
            journey_success = True
            if should_add_to_journey:
                journey_success = await self.journey_context.add_entry(
                    content,
                    {**message_metadata, "persist": True}
                )
            
            # Add to knowledge if contains important information
            knowledge_success = True
            if should_add_to_knowledge:
                knowledge_success = await self.knowledge_context.add_entry(
                    content,
                    {**message_metadata, "category": metadata.get("category", "general")}
                )
            
            # Update metrics
            self.metrics["total_updates"] += 1
            
            # Queue for real-time update
            self.update_queue.append({
                "type": "message",
                "role": role,
                "timestamp": datetime.utcnow(),
                "layers_updated": {
                    "session": session_success,
                    "journey": journey_success and should_add_to_journey,
                    "knowledge": knowledge_success and should_add_to_knowledge
                }
            })
            
            # Process update queue if needed
            if len(self.update_queue) >= 5:
                await self._process_update_queue()
            
            return session_success
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
    
    async def get_context(
        self,
        query: Optional[str] = None,
        query_type: str = "general",
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Get optimized context for a query.
        
        Args:
            query: Optional query for relevance filtering
            query_type: Type of query (conversation, task_execution, knowledge_query, planning)
            max_tokens: Maximum tokens (uses default budget if not specified)
            
        Returns:
            Formatted context string
        """
        try:
            # Use total budget if not specified
            max_tokens = max_tokens or self.token_manager.total_budget
            
            # Optimize token allocation for query type
            if query_type != "general":
                # Estimate requirements
                requirements = self._estimate_context_requirements(query, query_type)
                self.token_manager.optimize_for_query(query_type, requirements)
            
            # Get allocation status
            allocation_status = self.token_manager.get_allocation_status()
            
            # Gather context from each layer
            contexts = await asyncio.gather(
                self.session_context.get_context(
                    max_tokens=allocation_status["layers"]["session"]["allocated"],
                    query=query
                ),
                self.journey_context.get_context(
                    max_tokens=allocation_status["layers"]["journey"]["allocated"],
                    query=query
                ),
                self.knowledge_context.get_context(
                    max_tokens=allocation_status["layers"]["knowledge"]["allocated"],
                    query=query
                )
            )
            
            # Filter out empty contexts
            valid_contexts = [c for c in contexts if c]
            
            if not valid_contexts:
                return ""
            
            # Merge and optimize contexts
            merged_context = await self.ref_mcp.merge_contexts(
                valid_contexts,
                max_tokens
            )
            
            # Update metrics
            self.metrics["cache_hits"] += 1  # Assuming cache hit for simplicity
            
            return merged_context
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            self.metrics["cache_misses"] += 1
            return ""
    
    async def update_milestone(
        self,
        milestone_id: str,
        milestone_data: Dict[str, Any]
    ) -> bool:
        """
        Update current milestone in journey context.
        
        Args:
            milestone_id: Milestone identifier
            milestone_data: Milestone information
            
        Returns:
            Success status
        """
        try:
            # Update journey context
            self.journey_context.current_milestone = milestone_id
            
            # Add milestone entry
            milestone_content = f"Started milestone {milestone_id}: {milestone_data.get('title', '')}"
            success = await self.journey_context.add_entry(
                milestone_content,
                {
                    "type": "milestone",
                    "milestone_id": milestone_id,
                    "important": True,
                    **milestone_data
                }
            )
            
            # Queue update
            self.update_queue.append({
                "type": "milestone_update",
                "milestone_id": milestone_id,
                "timestamp": datetime.utcnow()
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating milestone: {e}")
            return False
    
    async def add_task_result(
        self,
        task: str,
        result: str,
        status: str = "completed"
    ) -> bool:
        """
        Add task result to journey context.
        
        Args:
            task: Task description
            result: Task result
            status: Task status
            
        Returns:
            Success status
        """
        try:
            # Format task result
            content = f"Task: {task}\nResult: {result}"
            
            # Add to journey context
            success = await self.journey_context.add_entry(
                content,
                {
                    "type": "task",
                    "status": status,
                    "persist": True
                }
            )
            
            # If task revealed important information, add to knowledge
            if status == "completed" and self._is_important_result(result):
                await self.knowledge_context.add_entry(
                    result,
                    {
                        "category": "task_results",
                        "task": task,
                        "importance": 0.7
                    }
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding task result: {e}")
            return False
    
    async def learn(
        self,
        knowledge: str,
        category: str = "general",
        importance: float = 0.5
    ) -> bool:
        """
        Add new knowledge to the knowledge context.
        
        Args:
            knowledge: Knowledge content
            category: Knowledge category
            importance: Importance score (0-1)
            
        Returns:
            Success status
        """
        try:
            # Add to knowledge context
            success = await self.knowledge_context.add_entry(
                knowledge,
                {
                    "category": category,
                    "importance": importance,
                    "learned_at": datetime.utcnow().isoformat()
                }
            )
            
            # Update user profile if it's about preferences
            if category == "preferences":
                self.knowledge_context.user_profile["last_preference_update"] = (
                    datetime.utcnow().isoformat()
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error learning knowledge: {e}")
            return False
    
    async def optimize_all_layers(self) -> Dict[str, bool]:
        """
        Optimize all context layers.
        
        Returns:
            Optimization results by layer
        """
        try:
            logger.info("Optimizing all context layers")
            
            # Run optimization in parallel
            results = await asyncio.gather(
                self.session_context.optimize(),
                self.journey_context.optimize(),
                self.knowledge_context.optimize(),
                return_exceptions=True
            )
            
            # Check results
            optimization_results = {
                "session": not isinstance(results[0], Exception),
                "journey": not isinstance(results[1], Exception),
                "knowledge": not isinstance(results[2], Exception)
            }
            
            # Rebalance token allocations
            self.token_manager.rebalance_allocations()
            
            # Update metrics
            self.metrics["optimization_count"] += 1
            
            logger.info(f"Optimization results: {optimization_results}")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Error optimizing layers: {e}")
            return {"session": False, "journey": False, "knowledge": False}
    
    async def persist_all(self) -> bool:
        """
        Persist all context layers to storage.
        
        Returns:
            Success status
        """
        try:
            # Persist all layers in parallel
            results = await asyncio.gather(
                self.session_context.persist(),
                self.journey_context.persist(),
                self.knowledge_context.persist(),
                return_exceptions=True
            )
            
            # Check for errors
            success = all(not isinstance(r, Exception) for r in results)
            
            if success:
                logger.info("All context layers persisted successfully")
            else:
                logger.error("Some context layers failed to persist")
            
            return success
            
        except Exception as e:
            logger.error(f"Error persisting context: {e}")
            return False
    
    async def clear_session(self) -> bool:
        """
        Clear session context while preserving journey and knowledge.
        
        Returns:
            Success status
        """
        try:
            self.session_context.clear()
            
            # Reset session token allocation
            self.token_manager.release_tokens("session", 
                                              self.session_context.current_tokens)
            
            logger.info("Session context cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive context statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            return {
                "user_id": self.user_id,
                "session_id": self.session_id,
                "is_initialized": self.is_initialized,
                "last_update": self.last_update.isoformat(),
                "layers": {
                    "session": self.session_context.get_statistics(),
                    "journey": self.journey_context.get_statistics(),
                    "knowledge": self.knowledge_context.get_statistics()
                },
                "token_allocation": self.token_manager.get_allocation_status(),
                "metrics": self.metrics,
                "update_queue_size": len(self.update_queue)
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def _should_add_to_journey(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if content should be added to journey context."""
        if not metadata:
            return False
        
        # Add if marked as important or task-related
        if metadata.get("important") or metadata.get("type") == "task":
            return True
        
        # Add if contains milestone keywords
        milestone_keywords = ["complete", "finish", "achieve", "milestone", "task", "goal"]
        content_lower = content.lower()
        
        return any(keyword in content_lower for keyword in milestone_keywords)
    
    def _should_add_to_knowledge(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if content should be added to knowledge context."""
        if not metadata:
            return False
        
        # Add if explicitly marked for knowledge
        if metadata.get("add_to_knowledge"):
            return True
        
        # Add if contains learning indicators
        learning_keywords = ["learned", "discovered", "found that", "realized", 
                           "preference", "always", "never", "usually"]
        content_lower = content.lower()
        
        return any(keyword in content_lower for keyword in learning_keywords)
    
    def _is_important_result(self, result: str) -> bool:
        """Check if a task result is important enough for knowledge context."""
        # Check for success indicators
        success_keywords = ["success", "completed", "achieved", "fixed", "resolved"]
        
        # Check for learning opportunities
        learning_keywords = ["error", "failed", "issue", "problem", "solution"]
        
        result_lower = result.lower()
        
        return any(keyword in result_lower 
                  for keyword in success_keywords + learning_keywords)
    
    def _estimate_context_requirements(
        self,
        query: Optional[str],
        query_type: str
    ) -> Dict[str, int]:
        """Estimate token requirements for each layer based on query."""
        # Base requirements
        requirements = {
            "session": 400,
            "journey": 800,
            "knowledge": 400
        }
        
        # Adjust based on query type
        if query_type == "conversation":
            requirements["session"] = 600
            requirements["journey"] = 400
            requirements["knowledge"] = 200
        elif query_type == "task_execution":
            requirements["session"] = 300
            requirements["journey"] = 1200
            requirements["knowledge"] = 400
        elif query_type == "knowledge_query":
            requirements["session"] = 200
            requirements["journey"] = 300
            requirements["knowledge"] = 800
        elif query_type == "planning":
            requirements["session"] = 300
            requirements["journey"] = 1000
            requirements["knowledge"] = 500
        
        return requirements
    
    def _update_token_allocations(self) -> None:
        """Update token allocations based on current usage."""
        # Update token manager with current usage
        self.token_manager.allocations["session"].used_tokens = (
            self.session_context.current_tokens
        )
        self.token_manager.allocations["journey"].used_tokens = (
            self.journey_context.current_tokens
        )
        self.token_manager.allocations["knowledge"].used_tokens = (
            self.knowledge_context.current_tokens
        )
    
    async def _process_update_queue(self) -> None:
        """Process queued updates for real-time notifications."""
        try:
            if not self.update_queue:
                return
            
            # Process updates (could publish to Redis pub/sub)
            for update in self.update_queue:
                # Log update for now
                logger.info(f"Processing update: {update['type']}")
            
            # Clear queue
            self.update_queue.clear()
            self.last_update = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error processing update queue: {e}")