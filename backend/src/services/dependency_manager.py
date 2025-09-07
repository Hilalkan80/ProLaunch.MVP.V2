"""
Milestone Dependency Manager

Comprehensive dependency management system for milestone tracking.
Handles validation, circular dependency detection, auto-unlocking,
and conditional dependencies with efficient caching.
"""

from typing import Optional, List, Dict, Any, Tuple, Set
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
from collections import deque, defaultdict
from enum import Enum
import json
import logging

from sqlalchemy import select, and_, or_, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError

from ..models.milestone import (
    Milestone, MilestoneDependency, UserMilestone,
    MilestoneStatus, MilestoneType, MilestoneProgressLog
)
from ..models.user import User, SubscriptionTier
from .milestone_cache import MilestoneCacheService
from ..infrastructure.redis.redis_mcp import RedisMCPClient
from ..core.exceptions import (
    CircularDependencyError,
    DependencyValidationError,
    MilestoneNotFoundError
)

logger = logging.getLogger(__name__)


class DependencyType(str, Enum):
    """Types of milestone dependencies"""
    REQUIRED = "required"  # Must be completed
    OPTIONAL = "optional"  # Nice to have but not blocking
    CONDITIONAL = "conditional"  # Required under certain conditions
    PARALLEL = "parallel"  # Can be done in parallel


class DependencyCondition(str, Enum):
    """Conditional dependency evaluation conditions"""
    USER_TIER = "user_tier"  # Based on subscription tier
    COMPLETION_SCORE = "completion_score"  # Based on quality score
    TIME_CONSTRAINT = "time_constraint"  # Time-based conditions
    FEATURE_FLAG = "feature_flag"  # Feature flag based


class DependencyManager:
    """
    Manages all milestone dependency operations including validation,
    resolution, and auto-unlocking with efficient caching strategies.
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        cache_service: MilestoneCacheService,
        redis_client: Optional[RedisMCPClient] = None
    ):
        """Initialize the dependency manager."""
        self.db = db_session
        self.cache_service = cache_service
        self.redis = redis_client or RedisMCPClient()
        self._dependency_graph_cache = {}
        self._validation_cache = {}
        
    # Core Dependency Operations
    
    async def add_dependency(
        self,
        milestone_id: str,
        dependency_id: str,
        is_required: bool = True,
        minimum_completion: float = 100.0,
        dependency_type: str = DependencyType.REQUIRED,
        conditions: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Add a dependency between milestones with validation.
        
        Args:
            milestone_id: The milestone that has the dependency
            dependency_id: The milestone that must be completed first
            is_required: Whether the dependency is mandatory
            minimum_completion: Minimum completion percentage required
            dependency_type: Type of dependency relationship
            conditions: Optional conditional requirements
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate milestones exist
            milestone = await self._get_milestone(milestone_id)
            dependency = await self._get_milestone(dependency_id)
            
            if not milestone or not dependency:
                return False, "One or both milestones not found"
            
            # Check for self-dependency
            if milestone_id == dependency_id:
                return False, "A milestone cannot depend on itself"
            
            # Check if dependency already exists
            existing = await self._get_existing_dependency(milestone_id, dependency_id)
            if existing:
                return False, "Dependency already exists"
            
            # Validate no circular dependency would be created
            would_create_cycle = await self._would_create_cycle(
                milestone_id, dependency_id
            )
            if would_create_cycle:
                return False, "Adding this dependency would create a circular reference"
            
            # Create the dependency
            new_dependency = MilestoneDependency(
                milestone_id=UUID(milestone_id),
                dependency_id=UUID(dependency_id),
                is_required=is_required,
                minimum_completion_percentage=minimum_completion
            )
            
            # Store additional metadata in cache if provided
            if dependency_type != DependencyType.REQUIRED or conditions:
                await self._store_dependency_metadata(
                    milestone_id,
                    dependency_id,
                    {
                        "type": dependency_type,
                        "conditions": conditions or {}
                    }
                )
            
            self.db.add(new_dependency)
            await self.db.commit()
            
            # Invalidate caches
            await self._invalidate_dependency_caches(milestone_id)
            
            # Log the operation
            logger.info(
                f"Added dependency: {milestone.code} depends on {dependency.code}"
            )
            
            return True, "Dependency added successfully"
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database error adding dependency: {e}")
            return False, "Database constraint violation"
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding dependency: {e}")
            return False, f"Error: {str(e)}"
    
    async def remove_dependency(
        self,
        milestone_id: str,
        dependency_id: str
    ) -> Tuple[bool, str]:
        """
        Remove a dependency between milestones.
        """
        try:
            # Find the dependency
            stmt = select(MilestoneDependency).where(
                and_(
                    MilestoneDependency.milestone_id == UUID(milestone_id),
                    MilestoneDependency.dependency_id == UUID(dependency_id)
                )
            )
            result = await self.db.execute(stmt)
            dependency = result.scalar_one_or_none()
            
            if not dependency:
                return False, "Dependency not found"
            
            # Remove the dependency
            await self.db.delete(dependency)
            await self.db.commit()
            
            # Clear dependency metadata
            await self._clear_dependency_metadata(milestone_id, dependency_id)
            
            # Invalidate caches
            await self._invalidate_dependency_caches(milestone_id)
            
            # Check if any milestones should be auto-unlocked
            await self._check_auto_unlock_after_removal(milestone_id)
            
            return True, "Dependency removed successfully"
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error removing dependency: {e}")
            return False, f"Error: {str(e)}"
    
    # Dependency Validation
    
    async def validate_dependencies(
        self,
        user_id: str,
        milestone_id: str,
        check_conditions: bool = True
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate if all dependencies are met for a milestone.
        
        Returns:
            Tuple of (all_met, unmet_dependencies)
        """
        # Check cache first
        cache_key = f"dep_validation:{user_id}:{milestone_id}"
        if cache_key in self._validation_cache:
            cached = self._validation_cache[cache_key]
            if cached["expires"] > datetime.utcnow():
                return cached["result"]
        
        # Get all dependencies for the milestone
        dependencies = await self._get_milestone_dependencies(milestone_id)
        
        if not dependencies:
            result = (True, [])
            self._cache_validation_result(cache_key, result)
            return result
        
        unmet = []
        
        for dep in dependencies:
            # Get dependency metadata
            metadata = await self._get_dependency_metadata(
                milestone_id,
                str(dep.dependency_id)
            )
            
            # Check if dependency is met
            is_met = await self._check_single_dependency(
                user_id,
                dep,
                metadata,
                check_conditions
            )
            
            if not is_met:
                dep_milestone = await self._get_milestone(str(dep.dependency_id))
                unmet.append({
                    "milestone_id": str(dep.dependency_id),
                    "milestone_code": dep_milestone.code if dep_milestone else "Unknown",
                    "milestone_name": dep_milestone.name if dep_milestone else "Unknown",
                    "is_required": dep.is_required,
                    "minimum_completion": dep.minimum_completion_percentage,
                    "type": metadata.get("type", DependencyType.REQUIRED) if metadata else DependencyType.REQUIRED
                })
        
        # Filter out optional dependencies if there are required ones unmet
        required_unmet = [d for d in unmet if d["is_required"]]
        if required_unmet:
            unmet = required_unmet
        
        result = (len(unmet) == 0, unmet)
        self._cache_validation_result(cache_key, result)
        return result
    
    async def check_circular_dependencies(self) -> List[List[str]]:
        """
        Check the entire milestone system for circular dependencies.
        
        Returns:
            List of circular dependency chains found
        """
        # Build the full dependency graph
        graph = await self._build_dependency_graph()
        
        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node)
        
        # Check from each unvisited node
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    async def get_dependency_chain(
        self,
        milestone_id: str,
        include_optional: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get the complete dependency chain for a milestone.
        
        Returns:
            Ordered list of milestones that must be completed
        """
        chain = []
        visited = set()
        
        async def build_chain(mid: str, level: int = 0):
            if mid in visited:
                return
            visited.add(mid)
            
            dependencies = await self._get_milestone_dependencies(mid)
            
            for dep in dependencies:
                if not include_optional and not dep.is_required:
                    continue
                
                dep_milestone = await self._get_milestone(str(dep.dependency_id))
                if dep_milestone:
                    chain_entry = {
                        "milestone_id": str(dep.dependency_id),
                        "milestone_code": dep_milestone.code,
                        "milestone_name": dep_milestone.name,
                        "level": level,
                        "is_required": dep.is_required,
                        "minimum_completion": dep.minimum_completion_percentage
                    }
                    
                    if chain_entry not in chain:
                        chain.append(chain_entry)
                    
                    # Recursively get dependencies of dependencies
                    await build_chain(str(dep.dependency_id), level + 1)
        
        await build_chain(milestone_id)
        
        # Sort by level (depth in dependency tree)
        chain.sort(key=lambda x: (x["level"], x["milestone_code"]))
        
        return chain
    
    # Auto-unlock Operations
    
    async def process_milestone_completion(
        self,
        user_id: str,
        completed_milestone_id: str
    ) -> List[Dict[str, Any]]:
        """
        Process a milestone completion and auto-unlock dependent milestones.
        
        Returns:
            List of newly unlocked milestones
        """
        newly_unlocked = []
        
        # Find all milestones that depend on the completed one
        stmt = (
            select(MilestoneDependency)
            .options(selectinload(MilestoneDependency.milestone))
            .where(MilestoneDependency.dependency_id == UUID(completed_milestone_id))
        )
        
        result = await self.db.execute(stmt)
        dependent_dependencies = result.scalars().all()
        
        for dep in dependent_dependencies:
            milestone = dep.milestone
            
            # Skip if milestone is not configured for auto-unlock
            if not milestone.auto_unlock:
                continue
            
            # Check if all dependencies are now met
            all_met, _ = await self.validate_dependencies(
                user_id,
                str(milestone.id)
            )
            
            if all_met:
                # Check if user milestone exists
                user_milestone = await self._get_user_milestone(
                    user_id,
                    str(milestone.id)
                )
                
                if user_milestone:
                    if user_milestone.status == MilestoneStatus.LOCKED:
                        # Unlock the milestone
                        user_milestone.status = MilestoneStatus.AVAILABLE
                        user_milestone.updated_at = datetime.utcnow()
                        
                        # Log the unlock
                        unlock_log = MilestoneProgressLog(
                            user_milestone_id=user_milestone.id,
                            event_type="auto_unlocked",
                            event_data={
                                "triggered_by": completed_milestone_id,
                                "milestone_code": milestone.code
                            }
                        )
                        self.db.add(unlock_log)
                        
                        newly_unlocked.append({
                            "milestone_id": str(milestone.id),
                            "milestone_code": milestone.code,
                            "milestone_name": milestone.name,
                            "status": MilestoneStatus.AVAILABLE
                        })
                else:
                    # Create new user milestone as available
                    new_user_milestone = UserMilestone(
                        user_id=UUID(user_id),
                        milestone_id=milestone.id,
                        status=MilestoneStatus.AVAILABLE,
                        total_steps=len(milestone.prompt_template.get("steps", [])) if milestone.prompt_template else 1
                    )
                    self.db.add(new_user_milestone)
                    
                    newly_unlocked.append({
                        "milestone_id": str(milestone.id),
                        "milestone_code": milestone.code,
                        "milestone_name": milestone.name,
                        "status": MilestoneStatus.AVAILABLE
                    })
        
        if newly_unlocked:
            await self.db.commit()
            
            # Invalidate user's cache
            await self.cache_service.invalidate_user_cache(user_id)
            
            # Publish unlock events
            for unlocked in newly_unlocked:
                await self.cache_service.publish_progress_update(
                    user_id,
                    unlocked["milestone_id"],
                    {
                        "event": "auto_unlocked",
                        "message": f"{unlocked['milestone_name']} is now available"
                    }
                )
        
        return newly_unlocked
    
    async def evaluate_conditional_dependencies(
        self,
        user_id: str,
        milestone_id: str
    ) -> Dict[str, Any]:
        """
        Evaluate conditional dependencies for a milestone.
        
        Returns:
            Dictionary with evaluation results
        """
        dependencies = await self._get_milestone_dependencies(milestone_id)
        evaluations = []
        
        for dep in dependencies:
            metadata = await self._get_dependency_metadata(
                milestone_id,
                str(dep.dependency_id)
            )
            
            if metadata and metadata.get("type") == DependencyType.CONDITIONAL:
                conditions = metadata.get("conditions", {})
                evaluation = await self._evaluate_conditions(
                    user_id,
                    conditions
                )
                
                dep_milestone = await self._get_milestone(str(dep.dependency_id))
                evaluations.append({
                    "dependency_id": str(dep.dependency_id),
                    "dependency_code": dep_milestone.code if dep_milestone else "Unknown",
                    "conditions": conditions,
                    "evaluation": evaluation,
                    "is_met": evaluation.get("all_conditions_met", False)
                })
        
        return {
            "milestone_id": milestone_id,
            "conditional_dependencies": evaluations,
            "all_conditions_met": all(e["is_met"] for e in evaluations)
        }
    
    # Dependency Analysis
    
    async def get_dependency_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the dependency system.
        """
        # Get all dependencies
        stmt = select(MilestoneDependency)
        result = await self.db.execute(stmt)
        all_dependencies = result.scalars().all()
        
        # Build statistics
        stats = {
            "total_dependencies": len(all_dependencies),
            "required_dependencies": sum(1 for d in all_dependencies if d.is_required),
            "optional_dependencies": sum(1 for d in all_dependencies if not d.is_required),
            "milestones_with_dependencies": len(set(d.milestone_id for d in all_dependencies)),
            "milestones_as_dependencies": len(set(d.dependency_id for d in all_dependencies)),
            "average_dependencies_per_milestone": 0,
            "max_dependency_chain_length": 0,
            "circular_dependencies_found": []
        }
        
        # Calculate average dependencies
        if stats["milestones_with_dependencies"] > 0:
            stats["average_dependencies_per_milestone"] = (
                stats["total_dependencies"] / stats["milestones_with_dependencies"]
            )
        
        # Find longest dependency chain
        all_milestones = await self._get_all_milestone_ids()
        max_chain_length = 0
        
        for milestone_id in all_milestones:
            chain = await self.get_dependency_chain(milestone_id, include_optional=False)
            chain_length = max([d["level"] for d in chain], default=0) + 1
            max_chain_length = max(max_chain_length, chain_length)
        
        stats["max_dependency_chain_length"] = max_chain_length
        
        # Check for circular dependencies
        cycles = await self.check_circular_dependencies()
        if cycles:
            stats["circular_dependencies_found"] = [
                [await self._get_milestone_code(mid) for mid in cycle]
                for cycle in cycles
            ]
        
        return stats
    
    async def visualize_dependency_graph(self) -> Dict[str, Any]:
        """
        Generate a visualization-ready representation of the dependency graph.
        
        Returns:
            Dictionary with nodes and edges for graph visualization
        """
        # Get all milestones
        stmt = select(Milestone).where(Milestone.is_active == True)
        result = await self.db.execute(stmt)
        milestones = result.scalars().all()
        
        # Get all dependencies
        stmt = select(MilestoneDependency)
        result = await self.db.execute(stmt)
        dependencies = result.scalars().all()
        
        # Build graph structure
        nodes = []
        edges = []
        
        for milestone in milestones:
            nodes.append({
                "id": str(milestone.id),
                "label": milestone.code,
                "name": milestone.name,
                "type": milestone.milestone_type,
                "requires_payment": milestone.requires_payment,
                "auto_unlock": milestone.auto_unlock
            })
        
        for dep in dependencies:
            metadata = await self._get_dependency_metadata(
                str(dep.milestone_id),
                str(dep.dependency_id)
            )
            
            edges.append({
                "source": str(dep.dependency_id),
                "target": str(dep.milestone_id),
                "is_required": dep.is_required,
                "minimum_completion": dep.minimum_completion_percentage,
                "type": metadata.get("type", DependencyType.REQUIRED) if metadata else DependencyType.REQUIRED
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "required_edges": sum(1 for e in edges if e["is_required"]),
                "optional_edges": sum(1 for e in edges if not e["is_required"])
            }
        }
    
    # Helper Methods
    
    async def _get_milestone(self, milestone_id: str) -> Optional[Milestone]:
        """Get a milestone by ID with caching."""
        cache_key = f"milestone:{milestone_id}"
        cached = await self.redis.get_cache(cache_key)
        
        if cached:
            return Milestone(**json.loads(cached))
        
        stmt = select(Milestone).where(Milestone.id == UUID(milestone_id))
        result = await self.db.execute(stmt)
        milestone = result.scalar_one_or_none()
        
        if milestone:
            await self.redis.set_cache(
                cache_key,
                json.dumps(milestone.to_dict()),
                ttl=3600
            )
        
        return milestone
    
    async def _get_milestone_code(self, milestone_id: str) -> str:
        """Get milestone code by ID."""
        milestone = await self._get_milestone(milestone_id)
        return milestone.code if milestone else "Unknown"
    
    async def _get_all_milestone_ids(self) -> List[str]:
        """Get all active milestone IDs."""
        stmt = select(Milestone.id).where(Milestone.is_active == True)
        result = await self.db.execute(stmt)
        return [str(mid) for mid in result.scalars().all()]
    
    async def _get_user_milestone(
        self,
        user_id: str,
        milestone_id: str
    ) -> Optional[UserMilestone]:
        """Get a user's milestone progress."""
        stmt = select(UserMilestone).where(
            and_(
                UserMilestone.user_id == UUID(user_id),
                UserMilestone.milestone_id == UUID(milestone_id)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_milestone_dependencies(
        self,
        milestone_id: str
    ) -> List[MilestoneDependency]:
        """Get all dependencies for a milestone."""
        stmt = (
            select(MilestoneDependency)
            .where(MilestoneDependency.milestone_id == UUID(milestone_id))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def _get_existing_dependency(
        self,
        milestone_id: str,
        dependency_id: str
    ) -> Optional[MilestoneDependency]:
        """Check if a dependency already exists."""
        stmt = select(MilestoneDependency).where(
            and_(
                MilestoneDependency.milestone_id == UUID(milestone_id),
                MilestoneDependency.dependency_id == UUID(dependency_id)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _would_create_cycle(
        self,
        milestone_id: str,
        dependency_id: str
    ) -> bool:
        """Check if adding a dependency would create a cycle."""
        # Build current graph
        graph = await self._build_dependency_graph()
        
        # Add the proposed edge
        if milestone_id not in graph:
            graph[milestone_id] = []
        graph[milestone_id].append(dependency_id)
        
        # Check for cycle using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        # Start from the dependency_id to see if we can reach milestone_id
        return has_cycle(dependency_id) if dependency_id in graph else False
    
    async def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build the complete dependency graph."""
        if self._dependency_graph_cache:
            cache_age = self._dependency_graph_cache.get("timestamp", datetime.min)
            if datetime.utcnow() - cache_age < timedelta(minutes=5):
                return self._dependency_graph_cache.get("graph", {})
        
        stmt = select(MilestoneDependency)
        result = await self.db.execute(stmt)
        dependencies = result.scalars().all()
        
        graph = defaultdict(list)
        for dep in dependencies:
            graph[str(dep.dependency_id)].append(str(dep.milestone_id))
        
        self._dependency_graph_cache = {
            "graph": dict(graph),
            "timestamp": datetime.utcnow()
        }
        
        return dict(graph)
    
    async def _check_single_dependency(
        self,
        user_id: str,
        dependency: MilestoneDependency,
        metadata: Optional[Dict[str, Any]],
        check_conditions: bool
    ) -> bool:
        """Check if a single dependency is met."""
        # Get user's progress on the dependency
        user_milestone = await self._get_user_milestone(
            user_id,
            str(dependency.dependency_id)
        )
        
        if not user_milestone:
            return False
        
        # Check completion percentage
        if user_milestone.completion_percentage < dependency.minimum_completion_percentage:
            return False
        
        # Check conditional requirements if applicable
        if check_conditions and metadata:
            dep_type = metadata.get("type", DependencyType.REQUIRED)
            
            if dep_type == DependencyType.CONDITIONAL:
                conditions = metadata.get("conditions", {})
                evaluation = await self._evaluate_conditions(user_id, conditions)
                if not evaluation.get("all_conditions_met", False):
                    return False
            elif dep_type == DependencyType.OPTIONAL:
                # Optional dependencies don't block
                return True
        
        return True
    
    async def _evaluate_conditions(
        self,
        user_id: str,
        conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate conditional dependency requirements."""
        results = {}
        
        for condition_type, condition_value in conditions.items():
            if condition_type == DependencyCondition.USER_TIER:
                # Check user's subscription tier
                stmt = select(User.subscription_tier).where(User.id == UUID(user_id))
                result = await self.db.execute(stmt)
                user_tier = result.scalar_one_or_none()
                
                results[condition_type] = {
                    "required": condition_value,
                    "actual": user_tier,
                    "met": user_tier == condition_value if user_tier else False
                }
                
            elif condition_type == DependencyCondition.COMPLETION_SCORE:
                # Check quality score requirement
                min_score = condition_value.get("min_score", 0)
                milestone_id = condition_value.get("milestone_id")
                
                if milestone_id:
                    user_milestone = await self._get_user_milestone(
                        user_id,
                        milestone_id
                    )
                    actual_score = user_milestone.quality_score if user_milestone else 0
                    results[condition_type] = {
                        "required": min_score,
                        "actual": actual_score,
                        "met": actual_score >= min_score
                    }
                    
            elif condition_type == DependencyCondition.TIME_CONSTRAINT:
                # Check time-based conditions
                deadline = condition_value.get("complete_by")
                if deadline:
                    deadline_dt = datetime.fromisoformat(deadline)
                    results[condition_type] = {
                        "required": deadline,
                        "actual": datetime.utcnow().isoformat(),
                        "met": datetime.utcnow() <= deadline_dt
                    }
                    
            elif condition_type == DependencyCondition.FEATURE_FLAG:
                # Check feature flag
                flag_name = condition_value
                # This would check against a feature flag service
                # For now, we'll assume all flags are enabled
                results[condition_type] = {
                    "required": flag_name,
                    "actual": "enabled",
                    "met": True
                }
        
        return {
            "conditions": results,
            "all_conditions_met": all(r.get("met", False) for r in results.values())
        }
    
    async def _store_dependency_metadata(
        self,
        milestone_id: str,
        dependency_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Store additional dependency metadata in cache."""
        cache_key = f"dep_meta:{milestone_id}:{dependency_id}"
        await self.redis.set_cache(
            cache_key,
            json.dumps(metadata),
            ttl=86400  # 24 hours
        )
    
    async def _get_dependency_metadata(
        self,
        milestone_id: str,
        dependency_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve dependency metadata from cache."""
        cache_key = f"dep_meta:{milestone_id}:{dependency_id}"
        cached = await self.redis.get_cache(cache_key)
        return json.loads(cached) if cached else None
    
    async def _clear_dependency_metadata(
        self,
        milestone_id: str,
        dependency_id: str
    ) -> None:
        """Clear dependency metadata from cache."""
        cache_key = f"dep_meta:{milestone_id}:{dependency_id}"
        await self.redis.delete_cache(cache_key)
    
    async def _invalidate_dependency_caches(self, milestone_id: str) -> None:
        """Invalidate all caches related to a milestone's dependencies."""
        # Clear validation cache for all users
        pattern = f"dep_validation:*:{milestone_id}"
        self._validation_cache = {
            k: v for k, v in self._validation_cache.items()
            if not k.startswith(pattern.replace("*", ""))
        }
        
        # Clear dependency graph cache
        self._dependency_graph_cache = {}
        
        # Clear milestone cache
        await self.cache_service.invalidate_milestone_cache(milestone_id)
    
    def _cache_validation_result(
        self,
        cache_key: str,
        result: Tuple[bool, List[Dict[str, Any]]]
    ) -> None:
        """Cache validation result with expiry."""
        self._validation_cache[cache_key] = {
            "result": result,
            "expires": datetime.utcnow() + timedelta(minutes=5)
        }
    
    async def _check_auto_unlock_after_removal(self, milestone_id: str) -> None:
        """Check if any milestones should be auto-unlocked after dependency removal."""
        # Get all users who have this milestone
        stmt = select(UserMilestone.user_id).where(
            UserMilestone.milestone_id == UUID(milestone_id)
        )
        result = await self.db.execute(stmt)
        user_ids = result.scalars().all()
        
        for user_id in user_ids:
            # Check if dependencies are now met
            all_met, _ = await self.validate_dependencies(
                str(user_id),
                milestone_id,
                check_conditions=True
            )
            
            if all_met:
                user_milestone = await self._get_user_milestone(
                    str(user_id),
                    milestone_id
                )
                
                if user_milestone and user_milestone.status == MilestoneStatus.LOCKED:
                    milestone = await self._get_milestone(milestone_id)
                    if milestone and milestone.auto_unlock:
                        user_milestone.status = MilestoneStatus.AVAILABLE
                        user_milestone.updated_at = datetime.utcnow()
                        
                        # Log the unlock
                        unlock_log = MilestoneProgressLog(
                            user_milestone_id=user_milestone.id,
                            event_type="auto_unlocked",
                            event_data={
                                "reason": "dependency_removed",
                                "milestone_code": milestone.code
                            }
                        )
                        self.db.add(unlock_log)
        
        await self.db.commit()