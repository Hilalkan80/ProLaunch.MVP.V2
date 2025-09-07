"""
Persistence Service Integration

This module provides high-level persistence operations that integrate
with the milestone service and handle complex business logic.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, select, func

from .milestone_persistence import (
    MilestonePersistence,
    ConnectionPoolManager,
    create_milestone_persistence
)
from ...models.milestone import (
    Milestone, UserMilestone, MilestoneStatus, MilestoneType,
    MilestoneDependency, UserMilestoneArtifact, MilestoneProgressLog
)
from ...models.user import User, SubscriptionTier

logger = logging.getLogger(__name__)


class PersistenceService:
    """
    High-level persistence service that coordinates database operations
    for the milestone system with advanced features.
    """
    
    def __init__(
        self,
        persistence: MilestonePersistence,
        enable_write_through_cache: bool = True,
        enable_read_ahead: bool = True
    ):
        """Initialize persistence service."""
        self.persistence = persistence
        self.enable_write_through_cache = enable_write_through_cache
        self.enable_read_ahead = enable_read_ahead
        
        # Track active transactions for monitoring
        self._active_transactions = 0
        self._transaction_metrics = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "avg_duration_ms": 0
        }
    
    # Transaction Management
    
    @asynccontextmanager
    async def transaction_scope(self):
        """
        Create a transaction scope for complex operations.
        Provides automatic retry and monitoring.
        """
        start_time = datetime.utcnow()
        self._active_transactions += 1
        self._transaction_metrics["total"] += 1
        
        try:
            async with self.persistence.get_session() as session:
                yield session
                await session.commit()
                self._transaction_metrics["successful"] += 1
        except Exception as e:
            self._transaction_metrics["failed"] += 1
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            self._active_transactions -= 1
            
            # Update metrics
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_avg_duration(duration)
    
    def _update_avg_duration(self, duration_ms: float):
        """Update average transaction duration."""
        current_avg = self._transaction_metrics["avg_duration_ms"]
        total_count = self._transaction_metrics["successful"]
        
        if total_count > 0:
            self._transaction_metrics["avg_duration_ms"] = (
                (current_avg * (total_count - 1) + duration_ms) / total_count
            )
    
    # Milestone Lifecycle Management
    
    async def initialize_user_journey(
        self,
        user_id: UUID,
        subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    ) -> Dict[str, Any]:
        """
        Initialize complete milestone journey for a new user.
        Sets up all milestones based on subscription tier.
        """
        try:
            # Get all active milestones
            async with self.persistence.get_session() as session:
                result = await session.execute(
                    select(Milestone)
                    .where(Milestone.is_active == True)
                    .order_by(Milestone.order_index)
                )
                milestones = result.scalars().all()
            
            # Initialize user milestones
            initialized = []
            for milestone in milestones:
                # Determine initial status based on tier and type
                if milestone.code == "M0":
                    status = MilestoneStatus.AVAILABLE
                elif milestone.milestone_type == MilestoneType.FREE:
                    status = MilestoneStatus.AVAILABLE
                elif subscription_tier != SubscriptionTier.FREE and not milestone.requires_payment:
                    status = MilestoneStatus.AVAILABLE
                else:
                    status = MilestoneStatus.LOCKED
                
                # Create user milestone
                user_milestone = await self.persistence.create_user_milestone(
                    user_id=user_id,
                    milestone_id=milestone.id,
                    initial_status=status
                )
                
                initialized.append({
                    "milestone_code": milestone.code,
                    "milestone_name": milestone.name,
                    "status": status,
                    "milestone_type": milestone.milestone_type
                })
            
            logger.info(f"Initialized journey for user {user_id}: {len(initialized)} milestones")
            
            return {
                "user_id": str(user_id),
                "milestones_initialized": len(initialized),
                "available_milestones": sum(
                    1 for m in initialized 
                    if m["status"] == MilestoneStatus.AVAILABLE
                ),
                "milestones": initialized
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize user journey: {e}")
            raise
    
    async def start_milestone_with_validation(
        self,
        user_id: UUID,
        milestone_code: str,
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Start a milestone with full validation and dependency checking.
        Returns (success, message, milestone_data).
        """
        try:
            # Get milestone
            milestone = await self.persistence.get_milestone(code=milestone_code)
            if not milestone:
                return False, f"Milestone {milestone_code} not found", None
            
            # Check dependencies
            dependencies_met = await self.check_dependencies_met(
                user_id, milestone.id
            )
            
            if not dependencies_met["all_met"]:
                missing = ", ".join(dependencies_met["missing"])
                return False, f"Missing dependencies: {missing}", None
            
            # Check subscription access
            if milestone.requires_payment:
                has_access = await self.check_subscription_access(
                    user_id, milestone.milestone_type
                )
                if not has_access:
                    return False, "This milestone requires a paid subscription", None
            
            # Start the milestone
            progress_data = {
                "status": MilestoneStatus.IN_PROGRESS,
                "started_at": datetime.utcnow(),
                "current_step": 1,
                "processing_attempts": 1
            }
            
            if session_metadata:
                progress_data["checkpoint_data"] = session_metadata
            
            success = await self.persistence.update_user_progress(
                user_id=user_id,
                milestone_id=milestone.id,
                progress_data=progress_data,
                log_event=True
            )
            
            if success:
                # Pre-fetch related data if read-ahead is enabled
                if self.enable_read_ahead:
                    await self._prefetch_milestone_data(user_id, milestone.id)
                
                return True, f"Started milestone {milestone_code}", {
                    "milestone_id": str(milestone.id),
                    "milestone_code": milestone_code,
                    "milestone_name": milestone.name,
                    "total_steps": len(milestone.prompt_template.get("steps", [])) 
                        if milestone.prompt_template else 1,
                    "estimated_minutes": milestone.estimated_minutes
                }
            
            return False, "Failed to start milestone", None
            
        except Exception as e:
            logger.error(f"Error starting milestone: {e}")
            return False, str(e), None
    
    async def complete_milestone_with_artifacts(
        self,
        user_id: UUID,
        milestone_code: str,
        generated_output: Dict[str, Any],
        artifacts: List[Dict[str, Any]],
        quality_score: Optional[float] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Complete a milestone and create associated artifacts.
        Returns (success, message, completion_data).
        """
        try:
            async with self.transaction_scope() as session:
                # Get milestone
                result = await session.execute(
                    select(Milestone).where(Milestone.code == milestone_code)
                )
                milestone = result.scalar_one_or_none()
                
                if not milestone:
                    return False, f"Milestone {milestone_code} not found", {}
                
                # Update milestone completion
                progress_data = {
                    "status": MilestoneStatus.COMPLETED,
                    "completed_at": datetime.utcnow(),
                    "completion_percentage": 100.0,
                    "generated_output": generated_output,
                    "quality_score": quality_score
                }
                
                success = await self.persistence.update_user_progress(
                    user_id=user_id,
                    milestone_id=milestone.id,
                    progress_data=progress_data,
                    log_event=True
                )
                
                if not success:
                    return False, "Failed to complete milestone", {}
                
                # Get user milestone ID for artifacts
                result = await session.execute(
                    select(UserMilestone.id).where(and_(
                        UserMilestone.user_id == user_id,
                        UserMilestone.milestone_id == milestone.id
                    ))
                )
                user_milestone_id = result.scalar_one()
                
                # Create artifacts
                created_artifacts = []
                for artifact_data in artifacts:
                    artifact = await self.persistence.create_artifact(
                        user_milestone_id=user_milestone_id,
                        artifact_data=artifact_data
                    )
                    created_artifacts.append({
                        "id": str(artifact.id),
                        "name": artifact.name,
                        "type": artifact.artifact_type
                    })
                
                # Unlock dependent milestones
                unlocked = await self.unlock_dependent_milestones(
                    user_id, milestone.id
                )
                
                completion_data = {
                    "milestone_id": str(milestone.id),
                    "milestone_code": milestone_code,
                    "completed_at": datetime.utcnow().isoformat(),
                    "quality_score": quality_score,
                    "artifacts_created": len(created_artifacts),
                    "artifacts": created_artifacts,
                    "unlocked_milestones": unlocked
                }
                
                logger.info(
                    f"Completed milestone {milestone_code} for user {user_id} "
                    f"with {len(created_artifacts)} artifacts"
                )
                
                return True, f"Milestone {milestone_code} completed successfully", completion_data
                
        except Exception as e:
            logger.error(f"Error completing milestone: {e}")
            return False, str(e), {}
    
    # Dependency Management
    
    async def check_dependencies_met(
        self,
        user_id: UUID,
        milestone_id: UUID
    ) -> Dict[str, Any]:
        """
        Check if all dependencies for a milestone are met.
        Returns detailed dependency status.
        """
        try:
            async with self.persistence.get_session() as session:
                # Get dependencies
                result = await session.execute(
                    select(MilestoneDependency)
                    .options(selectinload(MilestoneDependency.dependency))
                    .where(MilestoneDependency.milestone_id == milestone_id)
                )
                dependencies = result.scalars().all()
                
                if not dependencies:
                    return {"all_met": True, "missing": [], "partial": []}
                
                missing = []
                partial = []
                
                for dep in dependencies:
                    # Check user progress on dependency
                    result = await session.execute(
                        select(UserMilestone)
                        .where(and_(
                            UserMilestone.user_id == user_id,
                            UserMilestone.milestone_id == dep.dependency_id
                        ))
                    )
                    user_progress = result.scalar_one_or_none()
                    
                    if not user_progress:
                        if dep.is_required:
                            missing.append(dep.dependency.code)
                    elif user_progress.completion_percentage < dep.minimum_completion_percentage:
                        if dep.is_required:
                            partial.append({
                                "code": dep.dependency.code,
                                "required": dep.minimum_completion_percentage,
                                "current": user_progress.completion_percentage
                            })
                
                return {
                    "all_met": len(missing) == 0 and len(partial) == 0,
                    "missing": missing,
                    "partial": partial
                }
                
        except Exception as e:
            logger.error(f"Error checking dependencies: {e}")
            return {"all_met": False, "missing": [], "partial": [], "error": str(e)}
    
    async def unlock_dependent_milestones(
        self,
        user_id: UUID,
        completed_milestone_id: UUID
    ) -> List[str]:
        """
        Unlock milestones that depend on the completed milestone.
        Returns list of newly unlocked milestone codes.
        """
        try:
            unlocked = []
            
            async with self.persistence.get_session() as session:
                # Find dependent milestones
                result = await session.execute(
                    select(MilestoneDependency)
                    .options(selectinload(MilestoneDependency.milestone))
                    .where(MilestoneDependency.dependency_id == completed_milestone_id)
                )
                dependent_deps = result.scalars().all()
                
                for dep in dependent_deps:
                    # Check if all dependencies are now met
                    deps_met = await self.check_dependencies_met(
                        user_id, dep.milestone_id
                    )
                    
                    if deps_met["all_met"]:
                        # Update milestone status to available
                        progress_data = {
                            "status": MilestoneStatus.AVAILABLE,
                            "updated_at": datetime.utcnow()
                        }
                        
                        success = await self.persistence.update_user_progress(
                            user_id=user_id,
                            milestone_id=dep.milestone_id,
                            progress_data=progress_data,
                            log_event=False
                        )
                        
                        if success:
                            unlocked.append(dep.milestone.code)
                            logger.info(
                                f"Unlocked milestone {dep.milestone.code} for user {user_id}"
                            )
            
            return unlocked
            
        except Exception as e:
            logger.error(f"Error unlocking dependent milestones: {e}")
            return []
    
    # Subscription and Access Control
    
    async def check_subscription_access(
        self,
        user_id: UUID,
        milestone_type: MilestoneType
    ) -> bool:
        """Check if user has subscription access to milestone type."""
        try:
            async with self.persistence.get_session() as session:
                result = await session.execute(
                    select(User.subscription_tier)
                    .where(User.id == user_id)
                )
                tier = result.scalar_one_or_none()
                
                if not tier:
                    return False
                
                # Free tier only has access to free milestones
                if tier == SubscriptionTier.FREE:
                    return milestone_type == MilestoneType.FREE
                
                # Paid tiers have access to all milestones
                return True
                
        except Exception as e:
            logger.error(f"Error checking subscription access: {e}")
            return False
    
    async def upgrade_user_access(
        self,
        user_id: UUID,
        new_tier: SubscriptionTier
    ) -> Dict[str, Any]:
        """
        Upgrade user subscription and unlock appropriate milestones.
        """
        try:
            unlocked_milestones = []
            
            async with self.transaction_scope() as session:
                # Update user subscription
                await session.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(
                        subscription_tier=new_tier,
                        subscription_updated_at=datetime.utcnow()
                    )
                )
                
                # Unlock paid milestones if upgrading from free
                if new_tier != SubscriptionTier.FREE:
                    result = await session.execute(
                        select(Milestone)
                        .where(and_(
                            Milestone.milestone_type == MilestoneType.PAID,
                            Milestone.is_active == True
                        ))
                    )
                    paid_milestones = result.scalars().all()
                    
                    for milestone in paid_milestones:
                        # Check if dependencies are met
                        deps_met = await self.check_dependencies_met(
                            user_id, milestone.id
                        )
                        
                        if deps_met["all_met"]:
                            # Create or update user milestone
                            await self.persistence.create_user_milestone(
                                user_id=user_id,
                                milestone_id=milestone.id,
                                initial_status=MilestoneStatus.AVAILABLE
                            )
                            unlocked_milestones.append(milestone.code)
            
            logger.info(
                f"Upgraded user {user_id} to {new_tier}, "
                f"unlocked {len(unlocked_milestones)} milestones"
            )
            
            return {
                "user_id": str(user_id),
                "new_tier": new_tier,
                "unlocked_milestones": unlocked_milestones,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error upgrading user access: {e}")
            raise
    
    # Analytics and Monitoring
    
    async def get_system_analytics(self) -> Dict[str, Any]:
        """Get comprehensive system-wide analytics."""
        try:
            analytics = {
                "timestamp": datetime.utcnow().isoformat(),
                "persistence_metrics": self._transaction_metrics,
                "active_transactions": self._active_transactions
            }
            
            async with self.persistence.get_session() as session:
                # Get user statistics
                user_stats = await session.execute(
                    text("""
                        SELECT 
                            COUNT(DISTINCT user_id) as total_users,
                            COUNT(*) FILTER (WHERE status = 'in_progress') as active_sessions,
                            COUNT(*) FILTER (WHERE status = 'completed') as total_completions,
                            AVG(completion_percentage) as avg_progress
                        FROM user_milestones
                    """)
                )
                row = user_stats.fetchone()
                
                analytics["user_statistics"] = {
                    "total_users": row[0] or 0,
                    "active_sessions": row[1] or 0,
                    "total_completions": row[2] or 0,
                    "average_progress": float(row[3] or 0)
                }
                
                # Get milestone statistics
                milestone_stats = await session.execute(
                    text("""
                        SELECT 
                            m.code,
                            COUNT(um.id) as attempts,
                            COUNT(*) FILTER (WHERE um.status = 'completed') as completions,
                            AVG(um.time_spent_seconds) FILTER (WHERE um.status = 'completed') as avg_time,
                            AVG(um.quality_score) as avg_quality
                        FROM milestones m
                        LEFT JOIN user_milestones um ON m.id = um.milestone_id
                        WHERE m.is_active = true
                        GROUP BY m.code, m.order_index
                        ORDER BY m.order_index
                    """)
                )
                
                milestone_data = []
                for row in milestone_stats:
                    milestone_data.append({
                        "code": row[0],
                        "attempts": row[1] or 0,
                        "completions": row[2] or 0,
                        "completion_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
                        "avg_completion_time_minutes": (row[3] or 0) / 60,
                        "avg_quality_score": float(row[4] or 0)
                    })
                
                analytics["milestone_statistics"] = milestone_data
            
            # Get connection pool status
            analytics["connection_pool"] = await self.persistence.pool_manager.get_pool_status()
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting system analytics: {e}")
            return {"error": str(e)}
    
    # Helper Methods
    
    async def _prefetch_milestone_data(
        self,
        user_id: UUID,
        milestone_id: UUID
    ):
        """Pre-fetch related data for better performance."""
        try:
            # Pre-fetch next milestones in sequence
            async with self.persistence.get_session() as session:
                # Get current milestone order
                result = await session.execute(
                    select(Milestone.order_index)
                    .where(Milestone.id == milestone_id)
                )
                current_order = result.scalar_one()
                
                # Pre-fetch next 3 milestones
                result = await session.execute(
                    select(Milestone)
                    .where(Milestone.order_index > current_order)
                    .order_by(Milestone.order_index)
                    .limit(3)
                )
                next_milestones = result.scalars().all()
                
                # Cache them
                for milestone in next_milestones:
                    if self.persistence.enable_query_cache:
                        cache_key = f"milestone:{milestone.code}"
                        self.persistence._query_cache[cache_key] = (
                            milestone,
                            datetime.utcnow()
                        )
                
                logger.debug(f"Pre-fetched {len(next_milestones)} upcoming milestones")
                
        except Exception as e:
            logger.error(f"Error pre-fetching data: {e}")
    
    # Cleanup and Maintenance
    
    async def cleanup_stale_sessions(
        self,
        stale_threshold_hours: int = 24
    ) -> int:
        """
        Clean up stale in-progress sessions.
        Returns number of sessions cleaned.
        """
        try:
            threshold = datetime.utcnow() - timedelta(hours=stale_threshold_hours)
            
            async with self.transaction_scope() as session:
                # Find stale sessions
                result = await session.execute(
                    select(UserMilestone.id)
                    .where(and_(
                        UserMilestone.status == MilestoneStatus.IN_PROGRESS,
                        UserMilestone.last_accessed_at < threshold
                    ))
                )
                stale_ids = [row[0] for row in result]
                
                if stale_ids:
                    # Update status to failed
                    await session.execute(
                        update(UserMilestone)
                        .where(UserMilestone.id.in_(stale_ids))
                        .values(
                            status=MilestoneStatus.FAILED,
                            last_error="Session timed out due to inactivity",
                            updated_at=datetime.utcnow()
                        )
                    )
                    
                    # Log cleanup
                    for milestone_id in stale_ids:
                        log = MilestoneProgressLog(
                            user_milestone_id=milestone_id,
                            event_type="timeout",
                            event_data={"reason": "inactivity", "threshold_hours": stale_threshold_hours},
                            created_at=datetime.utcnow()
                        )
                        session.add(log)
                
                logger.info(f"Cleaned up {len(stale_ids)} stale sessions")
                return len(stale_ids)
                
        except Exception as e:
            logger.error(f"Error cleaning up stale sessions: {e}")
            return 0
    
    async def close(self):
        """Clean up resources."""
        await self.persistence.pool_manager.close()
        logger.info("Persistence service closed")


# Factory function
async def create_persistence_service(
    database_url: str,
    pool_size: int = 20,
    enable_cache: bool = True
) -> PersistenceService:
    """Create and initialize persistence service."""
    persistence = await create_milestone_persistence(
        database_url=database_url,
        pool_size=pool_size,
        enable_cache=enable_cache
    )
    
    service = PersistenceService(
        persistence=persistence,
        enable_write_through_cache=True,
        enable_read_ahead=True
    )
    
    logger.info("Persistence service initialized")
    return service