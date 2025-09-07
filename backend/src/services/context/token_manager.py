"""
Token Budget Manager

Manages token allocation and optimization across context layers.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenAllocation:
    """Represents token allocation for a context layer"""
    layer_name: str
    allocated_tokens: int
    used_tokens: int
    priority: float
    last_updated: datetime
    
    @property
    def available_tokens(self) -> int:
        """Get available tokens"""
        return max(0, self.allocated_tokens - self.used_tokens)
    
    @property
    def utilization_rate(self) -> float:
        """Get utilization rate"""
        if self.allocated_tokens == 0:
            return 0.0
        return self.used_tokens / self.allocated_tokens
    
    def can_allocate(self, tokens: int) -> bool:
        """Check if tokens can be allocated"""
        return self.available_tokens >= tokens


class TokenBudgetManager:
    """
    Manages token budget allocation across context layers.
    
    Total budget: 4000 tokens
    - Session: 800 tokens (20%)
    - Journey: 2000 tokens (50%)
    - Knowledge: 1200 tokens (30%)
    """
    
    def __init__(self, total_budget: int = 4000):
        self.total_budget = total_budget
        self.allocations: Dict[str, TokenAllocation] = {}
        self.reserve_pool = 0  # Reserve for critical operations
        self.optimization_history: List[Dict[str, Any]] = []
        
        # Initialize default allocations
        self._initialize_default_allocations()
    
    def _initialize_default_allocations(self) -> None:
        """Initialize default token allocations"""
        now = datetime.utcnow()
        
        # Default allocation strategy
        default_allocations = {
            "session": (800, 1.0),    # 800 tokens, priority 1.0
            "journey": (2000, 0.8),   # 2000 tokens, priority 0.8
            "knowledge": (1200, 0.6),  # 1200 tokens, priority 0.6
        }
        
        for layer_name, (tokens, priority) in default_allocations.items():
            self.allocations[layer_name] = TokenAllocation(
                layer_name=layer_name,
                allocated_tokens=tokens,
                used_tokens=0,
                priority=priority,
                last_updated=now
            )
    
    def allocate_tokens(
        self,
        layer_name: str,
        requested_tokens: int
    ) -> Tuple[bool, int]:
        """
        Allocate tokens to a layer.
        
        Args:
            layer_name: Name of the context layer
            requested_tokens: Number of tokens requested
            
        Returns:
            Tuple of (success, allocated_tokens)
        """
        try:
            if layer_name not in self.allocations:
                logger.error(f"Unknown layer: {layer_name}")
                return False, 0
            
            allocation = self.allocations[layer_name]
            
            # Check if tokens available in layer
            if allocation.can_allocate(requested_tokens):
                allocation.used_tokens += requested_tokens
                allocation.last_updated = datetime.utcnow()
                return True, requested_tokens
            
            # Try to borrow from other layers
            borrowed = self._borrow_tokens(layer_name, requested_tokens)
            if borrowed > 0:
                allocation.used_tokens += borrowed
                allocation.last_updated = datetime.utcnow()
                return True, borrowed
            
            # Partial allocation
            available = allocation.available_tokens
            if available > 0:
                allocation.used_tokens += available
                allocation.last_updated = datetime.utcnow()
                return True, available
            
            return False, 0
            
        except Exception as e:
            logger.error(f"Error allocating tokens: {e}")
            return False, 0
    
    def release_tokens(
        self,
        layer_name: str,
        tokens: int
    ) -> bool:
        """
        Release tokens back to a layer.
        
        Args:
            layer_name: Name of the context layer
            tokens: Number of tokens to release
            
        Returns:
            Success status
        """
        try:
            if layer_name not in self.allocations:
                return False
            
            allocation = self.allocations[layer_name]
            allocation.used_tokens = max(0, allocation.used_tokens - tokens)
            allocation.last_updated = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"Error releasing tokens: {e}")
            return False
    
    def rebalance_allocations(
        self,
        usage_patterns: Optional[Dict[str, float]] = None
    ) -> Dict[str, int]:
        """
        Rebalance token allocations based on usage patterns.
        
        Args:
            usage_patterns: Optional usage patterns by layer
            
        Returns:
            New allocations
        """
        try:
            # Calculate current usage patterns if not provided
            if usage_patterns is None:
                usage_patterns = self._calculate_usage_patterns()
            
            # Calculate new allocations based on usage
            total_usage = sum(usage_patterns.values())
            if total_usage == 0:
                return {k: v.allocated_tokens for k, v in self.allocations.items()}
            
            new_allocations = {}
            remaining_budget = self.total_budget
            
            # Allocate proportionally with minimum guarantees
            min_allocations = {
                "session": 400,     # Minimum 400 tokens
                "journey": 800,     # Minimum 800 tokens
                "knowledge": 400,   # Minimum 400 tokens
            }
            
            for layer_name in self.allocations:
                # Calculate proportional allocation
                usage_ratio = usage_patterns.get(layer_name, 0) / total_usage
                proportional = int(self.total_budget * usage_ratio)
                
                # Apply minimum guarantee
                min_tokens = min_allocations.get(layer_name, 200)
                allocated = max(min_tokens, proportional)
                allocated = min(allocated, remaining_budget)
                
                new_allocations[layer_name] = allocated
                remaining_budget -= allocated
            
            # Distribute remaining tokens to highest priority layers
            if remaining_budget > 0:
                sorted_layers = sorted(
                    self.allocations.items(),
                    key=lambda x: x[1].priority,
                    reverse=True
                )
                
                for layer_name, allocation in sorted_layers:
                    if remaining_budget <= 0:
                        break
                    
                    bonus = min(remaining_budget, 100)
                    new_allocations[layer_name] += bonus
                    remaining_budget -= bonus
            
            # Apply new allocations
            for layer_name, new_tokens in new_allocations.items():
                if layer_name in self.allocations:
                    self.allocations[layer_name].allocated_tokens = new_tokens
            
            # Record optimization
            self.optimization_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "old_allocations": {
                    k: v.allocated_tokens for k, v in self.allocations.items()
                },
                "new_allocations": new_allocations,
                "usage_patterns": usage_patterns
            })
            
            return new_allocations
            
        except Exception as e:
            logger.error(f"Error rebalancing allocations: {e}")
            return {k: v.allocated_tokens for k, v in self.allocations.items()}
    
    def get_allocation_status(self) -> Dict[str, Any]:
        """
        Get current allocation status.
        
        Returns:
            Status dictionary
        """
        try:
            total_allocated = sum(a.allocated_tokens for a in self.allocations.values())
            total_used = sum(a.used_tokens for a in self.allocations.values())
            
            status = {
                "total_budget": self.total_budget,
                "total_allocated": total_allocated,
                "total_used": total_used,
                "total_available": self.total_budget - total_used,
                "utilization_rate": total_used / self.total_budget if self.total_budget > 0 else 0,
                "layers": {}
            }
            
            for layer_name, allocation in self.allocations.items():
                status["layers"][layer_name] = {
                    "allocated": allocation.allocated_tokens,
                    "used": allocation.used_tokens,
                    "available": allocation.available_tokens,
                    "utilization": allocation.utilization_rate,
                    "priority": allocation.priority,
                    "last_updated": allocation.last_updated.isoformat()
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting allocation status: {e}")
            return {}
    
    def optimize_for_query(
        self,
        query_type: str,
        context_requirements: Dict[str, int]
    ) -> Dict[str, int]:
        """
        Optimize allocations for a specific query type.
        
        Args:
            query_type: Type of query being processed
            context_requirements: Required tokens per layer
            
        Returns:
            Optimized allocations
        """
        try:
            # Query type profiles
            query_profiles = {
                "conversation": {"session": 0.5, "journey": 0.3, "knowledge": 0.2},
                "task_execution": {"session": 0.2, "journey": 0.6, "knowledge": 0.2},
                "knowledge_query": {"session": 0.1, "journey": 0.2, "knowledge": 0.7},
                "planning": {"session": 0.2, "journey": 0.5, "knowledge": 0.3},
            }
            
            profile = query_profiles.get(query_type, {
                "session": 0.33,
                "journey": 0.34,
                "knowledge": 0.33
            })
            
            # Calculate optimized allocations
            optimized = {}
            remaining_budget = self.total_budget
            
            for layer_name, weight in profile.items():
                required = context_requirements.get(layer_name, 0)
                weighted = int(self.total_budget * weight)
                
                # Use maximum of required and weighted
                allocated = max(required, weighted)
                allocated = min(allocated, remaining_budget)
                
                optimized[layer_name] = allocated
                remaining_budget -= allocated
            
            # Temporarily adjust allocations
            for layer_name, tokens in optimized.items():
                if layer_name in self.allocations:
                    self.allocations[layer_name].allocated_tokens = tokens
            
            return optimized
            
        except Exception as e:
            logger.error(f"Error optimizing for query: {e}")
            return context_requirements
    
    def set_priority(
        self,
        layer_name: str,
        priority: float
    ) -> bool:
        """
        Set priority for a context layer.
        
        Args:
            layer_name: Name of the context layer
            priority: Priority value (0.0 - 1.0)
            
        Returns:
            Success status
        """
        try:
            if layer_name not in self.allocations:
                return False
            
            if not 0.0 <= priority <= 1.0:
                logger.error(f"Invalid priority value: {priority}")
                return False
            
            self.allocations[layer_name].priority = priority
            return True
            
        except Exception as e:
            logger.error(f"Error setting priority: {e}")
            return False
    
    def _borrow_tokens(
        self,
        requesting_layer: str,
        tokens_needed: int
    ) -> int:
        """
        Try to borrow tokens from other layers.
        
        Args:
            requesting_layer: Layer requesting tokens
            tokens_needed: Number of tokens needed
            
        Returns:
            Number of tokens borrowed
        """
        try:
            borrowed = 0
            requester_priority = self.allocations[requesting_layer].priority
            
            # Sort layers by priority (lowest first)
            sorted_layers = sorted(
                [(k, v) for k, v in self.allocations.items() if k != requesting_layer],
                key=lambda x: x[1].priority
            )
            
            for layer_name, allocation in sorted_layers:
                # Only borrow from lower priority layers
                if allocation.priority >= requester_priority:
                    continue
                
                # Calculate how much can be borrowed
                available = allocation.available_tokens
                can_borrow = min(available // 2, tokens_needed - borrowed)  # Borrow max 50%
                
                if can_borrow > 0:
                    # Transfer tokens
                    allocation.allocated_tokens -= can_borrow
                    self.allocations[requesting_layer].allocated_tokens += can_borrow
                    borrowed += can_borrow
                    
                    logger.info(
                        f"Borrowed {can_borrow} tokens from {layer_name} to {requesting_layer}"
                    )
                
                if borrowed >= tokens_needed:
                    break
            
            return borrowed
            
        except Exception as e:
            logger.error(f"Error borrowing tokens: {e}")
            return 0
    
    def _calculate_usage_patterns(self) -> Dict[str, float]:
        """
        Calculate usage patterns from current allocations.
        
        Returns:
            Usage patterns by layer
        """
        patterns = {}
        
        for layer_name, allocation in self.allocations.items():
            # Calculate weighted usage
            usage = allocation.utilization_rate
            recency = 1.0  # Could be based on last_updated
            priority = allocation.priority
            
            # Weighted score
            patterns[layer_name] = usage * 0.5 + recency * 0.3 + priority * 0.2
        
        return patterns
    
    def export_metrics(self) -> Dict[str, Any]:
        """
        Export token management metrics.
        
        Returns:
            Metrics dictionary
        """
        try:
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_budget": self.total_budget,
                "allocations": {},
                "optimization_count": len(self.optimization_history),
                "efficiency_score": 0.0
            }
            
            total_used = 0
            total_allocated = 0
            
            for layer_name, allocation in self.allocations.items():
                metrics["allocations"][layer_name] = {
                    "allocated": allocation.allocated_tokens,
                    "used": allocation.used_tokens,
                    "utilization": allocation.utilization_rate,
                    "priority": allocation.priority
                }
                total_used += allocation.used_tokens
                total_allocated += allocation.allocated_tokens
            
            # Calculate efficiency score
            if total_allocated > 0:
                allocation_efficiency = total_allocated / self.total_budget
                usage_efficiency = total_used / total_allocated
                metrics["efficiency_score"] = (allocation_efficiency + usage_efficiency) / 2
            
            # Add recent optimizations
            if self.optimization_history:
                metrics["recent_optimizations"] = self.optimization_history[-5:]
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return {}