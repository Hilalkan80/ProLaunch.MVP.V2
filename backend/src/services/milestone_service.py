"""
Milestone Service

Core business logic for milestone management, progress tracking,
and dependency resolution.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
from sqlalchemy import select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.milestone import (
    Milestone, MilestoneDependency, UserMilestone, MilestoneArtifact,
    UserMilestoneArtifact, MilestoneProgressLog, MilestoneCache,
    MilestoneStatus, MilestoneType,
    get_user_milestone_tree, check_milestone_dependencies,
    update_dependent_milestones
)
from ..models.user import User, SubscriptionTier
from .milestone_cache import MilestoneCacheService, cache_decorator
from ..infrastructure.redis.redis_mcp import RedisMCPClient


class MilestoneService:
    """
    Service layer for milestone operations.
    Handles all business logic related to milestones.
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        cache_service: MilestoneCacheService
    ):
        """Initialize the milestone service."""
        self.db = db_session
        self.cache_service = cache_service
    
    # Milestone Retrieval
    
    async def get_milestone_by_code(self, code: str) -> Optional[Milestone]:
        """Get a milestone by its code (M0, M1, etc.)."""
        # Try cache first
        cache_key = f"milestone:code:{code}"
        cached = await self.cache_service.redis.get_cache(cache_key)
        if cached:
            return cached
        
        # Query database
        stmt = select(Milestone).where(
            and_(
                Milestone.code == code,
                Milestone.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        milestone = result.scalar_one_or_none()
        
        # Cache result
        if milestone:
            await self.cache_service.redis.set_cache(
                cache_key,
                milestone.to_dict(),
                3600
            )
        
        return milestone
    
    async def get_all_milestones(self) -> List[Milestone]:
        """Get all active milestones ordered by index."""
        stmt = (
            select(Milestone)
            .where(Milestone.is_active == True)
            .order_by(Milestone.order_index)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_user_milestone_progress(
        self,
        user_id: str,
        milestone_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user's milestone progress.
        If milestone_id is provided, returns specific milestone progress.
        Otherwise returns all milestone progress.
        """
        # Try cache first
        cached = await self.cache_service.get_user_progress(user_id, milestone_id)
        if cached:
            return cached
        
        if milestone_id:
            # Get specific milestone progress
            stmt = (
                select(UserMilestone)
                .options(
                    selectinload(UserMilestone.milestone),
                    selectinload(UserMilestone.artifacts)
                )
                .where(
                    and_(
                        UserMilestone.user_id == user_id,
                        UserMilestone.milestone_id == milestone_id
                    )
                )
            )
            result = await self.db.execute(stmt)
            user_milestone = result.scalar_one_or_none()
            
            if user_milestone:
                progress_data = user_milestone.to_dict(include_outputs=True)
                progress_data["milestone"] = user_milestone.milestone.to_dict()
                
                # Cache the result
                await self.cache_service.set_user_progress(
                    user_id, progress_data, milestone_id
                )
                
                return progress_data
            return None
        else:
            # Get all milestone progress
            return await self.get_user_milestone_tree_with_cache(user_id)
    
    async def get_user_milestone_tree_with_cache(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get complete milestone tree with caching."""
        # Try cache first
        cached = await self.cache_service.get_milestone_tree(user_id)
        if cached:
            return cached
        
        # Get from database
        tree = await get_user_milestone_tree(self.db, user_id)
        
        # Cache the result
        await self.cache_service.set_milestone_tree(user_id, tree)
        
        return tree
    
    # Milestone Initialization
    
    async def initialize_user_milestones(self, user_id: str) -> List[UserMilestone]:
        """
        Initialize milestone tracking for a new user.
        Creates UserMilestone records for all available milestones.
        """
        # Get all active milestones
        milestones = await self.get_all_milestones()
        
        # Get user to check subscription
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user_milestones = []
        
        for milestone in milestones:
            # Determine initial status
            if milestone.code == "M0":
                # M0 is always available
                status = MilestoneStatus.AVAILABLE
            elif milestone.milestone_type == MilestoneType.FREE:
                # Free milestones start as available
                status = MilestoneStatus.AVAILABLE
            elif not milestone.requires_payment:
                # Non-payment milestones check dependencies
                can_start, _ = await check_milestone_dependencies(
                    self.db, user_id, str(milestone.id)
                )
                status = MilestoneStatus.AVAILABLE if can_start else MilestoneStatus.LOCKED
            else:
                # Paid milestones start as locked
                status = MilestoneStatus.LOCKED
            
            # Create user milestone record
            user_milestone = UserMilestone(
                user_id=user_id,
                milestone_id=milestone.id,
                status=status,
                total_steps=len(milestone.prompt_template.get("steps", [])) if milestone.prompt_template else 1
            )
            
            self.db.add(user_milestone)
            user_milestones.append(user_milestone)
        
        await self.db.commit()
        
        # Invalidate cache
        await self.cache_service.invalidate_user_cache(user_id)
        
        return user_milestones
    
    # Milestone Status Management
    
    async def start_milestone(
        self,
        user_id: str,
        milestone_code: str
    ) -> Tuple[bool, str, Optional[UserMilestone]]:
        """
        Start working on a milestone.
        Returns (success, message, user_milestone).
        """
        # Get milestone
        milestone = await self.get_milestone_by_code(milestone_code)
        if not milestone:
            return False, f"Milestone {milestone_code} not found", None
        
        # Check if user has access
        has_access, access_msg = await self._check_milestone_access(
            user_id, milestone
        )
        if not has_access:
            return False, access_msg, None
        
        # Get or create user milestone
        stmt = select(UserMilestone).where(
            and_(
                UserMilestone.user_id == user_id,
                UserMilestone.milestone_id == milestone.id
            )
        )
        result = await self.db.execute(stmt)
        user_milestone = result.scalar_one_or_none()
        
        if not user_milestone:
            # Create new user milestone
            user_milestone = UserMilestone(
                user_id=user_id,
                milestone_id=milestone.id,
                status=MilestoneStatus.IN_PROGRESS,
                started_at=datetime.utcnow(),
                current_step=1,
                total_steps=len(milestone.prompt_template.get("steps", [])) if milestone.prompt_template else 1
            )
            self.db.add(user_milestone)
        else:
            # Check current status
            if user_milestone.status == MilestoneStatus.COMPLETED:
                return False, f"Milestone {milestone_code} is already completed", user_milestone
            
            if user_milestone.status == MilestoneStatus.IN_PROGRESS:
                return True, f"Milestone {milestone_code} is already in progress", user_milestone
            
            # Update status to in progress
            user_milestone.status = MilestoneStatus.IN_PROGRESS
            user_milestone.started_at = user_milestone.started_at or datetime.utcnow()
            user_milestone.last_accessed_at = datetime.utcnow()
            user_milestone.processing_attempts += 1
        
        # Log progress
        progress_log = MilestoneProgressLog(
            user_milestone_id=user_milestone.id,
            event_type="started",
            event_data={"milestone_code": milestone_code},
            completion_percentage=0,
            time_elapsed_seconds=0
        )
        self.db.add(progress_log)
        
        await self.db.commit()
        
        # Update cache
        await self.cache_service.update_milestone_progress(
            user_id,
            str(milestone.id),
            {"status": MilestoneStatus.IN_PROGRESS}
        )
        
        # Publish real-time update
        await self.cache_service.publish_progress_update(
            user_id,
            str(milestone.id),
            {
                "status": MilestoneStatus.IN_PROGRESS,
                "message": f"Started {milestone.name}"
            }
        )
        
        # Track session
        await self.cache_service.track_active_session(
            user_id,
            str(milestone.id),
            {"milestone_code": milestone_code}
        )
        
        # Update statistics
        await self.cache_service.increment_milestone_stats(
            milestone_code,
            "started"
        )
        
        return True, f"Started milestone {milestone_code}", user_milestone
    
    async def update_milestone_progress(
        self,
        user_id: str,
        milestone_code: str,
        step_completed: int,
        checkpoint_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Update progress for a milestone in progress.
        """
        # Get milestone and user milestone
        milestone = await self.get_milestone_by_code(milestone_code)
        if not milestone:
            return False, f"Milestone {milestone_code} not found"
        
        stmt = select(UserMilestone).where(
            and_(
                UserMilestone.user_id == user_id,
                UserMilestone.milestone_id == milestone.id
            )
        )
        result = await self.db.execute(stmt)
        user_milestone = result.scalar_one_or_none()
        
        if not user_milestone:
            return False, f"User milestone not found"
        
        if user_milestone.status != MilestoneStatus.IN_PROGRESS:
            return False, f"Milestone is not in progress"
        
        # Update progress
        user_milestone.current_step = step_completed
        user_milestone.completion_percentage = (
            step_completed / user_milestone.total_steps * 100
        )
        user_milestone.last_accessed_at = datetime.utcnow()
        
        if checkpoint_data:
            if user_milestone.checkpoint_data:
                user_milestone.checkpoint_data.update(checkpoint_data)
            else:
                user_milestone.checkpoint_data = checkpoint_data
        
        # Calculate time spent
        if user_milestone.started_at:
            time_delta = datetime.utcnow() - user_milestone.started_at
            user_milestone.time_spent_seconds = int(time_delta.total_seconds())
        
        # Log progress
        progress_log = MilestoneProgressLog(
            user_milestone_id=user_milestone.id,
            event_type="step_completed",
            event_data={
                "step": step_completed,
                "total_steps": user_milestone.total_steps
            },
            step_number=step_completed,
            completion_percentage=user_milestone.completion_percentage,
            time_elapsed_seconds=user_milestone.time_spent_seconds
        )
        self.db.add(progress_log)
        
        await self.db.commit()
        
        # Update cache
        await self.cache_service.update_milestone_progress(
            user_id,
            str(milestone.id),
            {
                "current_step": step_completed,
                "completion_percentage": user_milestone.completion_percentage
            }
        )
        
        # Update session activity
        await self.cache_service.update_session_activity(
            user_id,
            str(milestone.id)
        )
        
        # Publish real-time update
        await self.cache_service.publish_progress_update(
            user_id,
            str(milestone.id),
            {
                "current_step": step_completed,
                "completion_percentage": user_milestone.completion_percentage,
                "message": f"Completed step {step_completed} of {user_milestone.total_steps}"
            }
        )
        
        return True, "Progress updated successfully"
    
    async def complete_milestone(
        self,
        user_id: str,
        milestone_code: str,
        generated_output: Dict[str, Any],
        quality_score: Optional[float] = None
    ) -> Tuple[bool, str, List[str]]:
        """
        Mark a milestone as completed.
        Returns (success, message, newly_unlocked_milestone_ids).
        """
        # Get milestone
        milestone = await self.get_milestone_by_code(milestone_code)
        if not milestone:
            return False, f"Milestone {milestone_code} not found", []
        
        # Get user milestone
        stmt = select(UserMilestone).where(
            and_(
                UserMilestone.user_id == user_id,
                UserMilestone.milestone_id == milestone.id
            )
        )
        result = await self.db.execute(stmt)
        user_milestone = result.scalar_one_or_none()
        
        if not user_milestone:
            return False, "User milestone not found", []
        
        if user_milestone.status == MilestoneStatus.COMPLETED:
            return False, "Milestone already completed", []
        
        # Update milestone status
        user_milestone.status = MilestoneStatus.COMPLETED
        user_milestone.completed_at = datetime.utcnow()
        user_milestone.completion_percentage = 100.0
        user_milestone.generated_output = generated_output
        user_milestone.quality_score = quality_score
        user_milestone.current_step = user_milestone.total_steps
        
        # Calculate final time spent
        if user_milestone.started_at:
            time_delta = user_milestone.completed_at - user_milestone.started_at
            user_milestone.time_spent_seconds = int(time_delta.total_seconds())
        
        # Log completion
        progress_log = MilestoneProgressLog(
            user_milestone_id=user_milestone.id,
            event_type="completed",
            event_data={
                "milestone_code": milestone_code,
                "quality_score": quality_score
            },
            completion_percentage=100.0,
            time_elapsed_seconds=user_milestone.time_spent_seconds
        )
        self.db.add(progress_log)
        
        await self.db.commit()
        
        # Update dependent milestones
        newly_unlocked = await update_dependent_milestones(
            self.db,
            user_id,
            str(milestone.id)
        )
        
        await self.db.commit()
        
        # Clear caches
        await self.cache_service.invalidate_user_cache(user_id)
        await self.cache_service.invalidate_milestone_cache(str(milestone.id))
        
        # Publish completion event
        await self.cache_service.publish_progress_update(
            user_id,
            str(milestone.id),
            {
                "status": MilestoneStatus.COMPLETED,
                "message": f"Completed {milestone.name}",
                "newly_unlocked": newly_unlocked
            }
        )
        
        # Update statistics
        await self.cache_service.increment_milestone_stats(
            milestone_code,
            "completed"
        )
        
        # Update leaderboard
        await self._update_user_leaderboard_score(user_id)
        
        return True, f"Milestone {milestone_code} completed successfully", newly_unlocked
    
    async def fail_milestone(
        self,
        user_id: str,
        milestone_code: str,
        error_message: str
    ) -> Tuple[bool, str]:
        """
        Mark a milestone as failed.
        """
        # Get milestone
        milestone = await self.get_milestone_by_code(milestone_code)
        if not milestone:
            return False, f"Milestone {milestone_code} not found"
        
        # Get user milestone
        stmt = select(UserMilestone).where(
            and_(
                UserMilestone.user_id == user_id,
                UserMilestone.milestone_id == milestone.id
            )
        )
        result = await self.db.execute(stmt)
        user_milestone = result.scalar_one_or_none()
        
        if not user_milestone:
            return False, "User milestone not found"
        
        # Update status
        user_milestone.status = MilestoneStatus.FAILED
        user_milestone.last_error = error_message
        
        # Log failure
        progress_log = MilestoneProgressLog(
            user_milestone_id=user_milestone.id,
            event_type="failed",
            event_data={
                "error": error_message,
                "milestone_code": milestone_code
            },
            completion_percentage=user_milestone.completion_percentage
        )
        self.db.add(progress_log)
        
        await self.db.commit()
        
        # Update cache
        await self.cache_service.update_milestone_progress(
            user_id,
            str(milestone.id),
            {"status": MilestoneStatus.FAILED, "error": error_message}
        )
        
        # Update statistics
        await self.cache_service.increment_milestone_stats(
            milestone_code,
            "failed"
        )
        
        return True, "Milestone marked as failed"
    
    # Artifact Management
    
    async def create_milestone_artifact(
        self,
        user_id: str,
        milestone_code: str,
        artifact_name: str,
        artifact_type: str,
        content: Dict[str, Any],
        storage_path: Optional[str] = None
    ) -> Optional[UserMilestoneArtifact]:
        """
        Create an artifact for a completed milestone.
        """
        # Get milestone and user milestone
        milestone = await self.get_milestone_by_code(milestone_code)
        if not milestone:
            return None
        
        stmt = select(UserMilestone).where(
            and_(
                UserMilestone.user_id == user_id,
                UserMilestone.milestone_id == milestone.id
            )
        )
        result = await self.db.execute(stmt)
        user_milestone = result.scalar_one_or_none()
        
        if not user_milestone:
            return None
        
        # Create artifact
        artifact = UserMilestoneArtifact(
            user_milestone_id=user_milestone.id,
            name=artifact_name,
            artifact_type=artifact_type,
            content=content,
            storage_path=storage_path,
            mime_type=self._get_mime_type(artifact_type)
        )
        
        self.db.add(artifact)
        await self.db.commit()
        
        # Cache artifact
        await self.cache_service.cache_artifact(
            str(artifact.id),
            {
                "name": artifact_name,
                "type": artifact_type,
                "content": content
            }
        )
        
        return artifact
    
    async def get_user_artifacts(
        self,
        user_id: str,
        milestone_code: Optional[str] = None
    ) -> List[UserMilestoneArtifact]:
        """
        Get all artifacts for a user, optionally filtered by milestone.
        """
        query = (
            select(UserMilestoneArtifact)
            .join(UserMilestone)
            .where(UserMilestone.user_id == user_id)
        )
        
        if milestone_code:
            milestone = await self.get_milestone_by_code(milestone_code)
            if milestone:
                query = query.where(
                    UserMilestone.milestone_id == milestone.id
                )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # Analytics and Reporting
    
    async def get_user_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive analytics for a user's milestone journey.
        """
        # Get all user milestones
        stmt = (
            select(UserMilestone)
            .options(selectinload(UserMilestone.milestone))
            .where(UserMilestone.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        user_milestones = result.scalars().all()
        
        analytics = {
            "total_milestones": len(user_milestones),
            "completed": 0,
            "in_progress": 0,
            "locked": 0,
            "failed": 0,
            "total_time_spent_hours": 0,
            "average_completion_time_hours": 0,
            "completion_rate": 0,
            "milestones_by_status": {},
            "time_by_milestone": {},
            "quality_scores": []
        }
        
        completed_times = []
        
        for um in user_milestones:
            # Count by status
            status = um.status
            analytics[status.lower()] = analytics.get(status.lower(), 0) + 1
            
            # Track time spent
            if um.time_spent_seconds:
                hours = um.time_spent_seconds / 3600
                analytics["total_time_spent_hours"] += hours
                analytics["time_by_milestone"][um.milestone.code] = hours
                
                if um.status == MilestoneStatus.COMPLETED:
                    completed_times.append(hours)
            
            # Track quality scores
            if um.quality_score:
                analytics["quality_scores"].append(um.quality_score)
        
        # Calculate averages
        if completed_times:
            analytics["average_completion_time_hours"] = (
                sum(completed_times) / len(completed_times)
            )
        
        if analytics["total_milestones"] > 0:
            analytics["completion_rate"] = (
                analytics["completed"] / analytics["total_milestones"] * 100
            )
        
        # Average quality score
        if analytics["quality_scores"]:
            analytics["average_quality_score"] = (
                sum(analytics["quality_scores"]) / len(analytics["quality_scores"])
            )
        
        return analytics
    
    async def get_milestone_statistics(
        self,
        milestone_code: str
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for a specific milestone.
        """
        # Get from cache
        stats = await self.cache_service.get_milestone_stats(milestone_code)
        
        # Add database statistics if needed
        milestone = await self.get_milestone_by_code(milestone_code)
        if milestone:
            # Get average completion time
            stmt = (
                select(UserMilestone.time_spent_seconds)
                .where(
                    and_(
                        UserMilestone.milestone_id == milestone.id,
                        UserMilestone.status == MilestoneStatus.COMPLETED,
                        UserMilestone.time_spent_seconds.isnot(None)
                    )
                )
            )
            result = await self.db.execute(stmt)
            completion_times = result.scalars().all()
            
            if completion_times:
                stats["average_completion_time_minutes"] = (
                    sum(completion_times) / len(completion_times) / 60
                )
            
            # Get average quality score
            stmt = (
                select(UserMilestone.quality_score)
                .where(
                    and_(
                        UserMilestone.milestone_id == milestone.id,
                        UserMilestone.quality_score.isnot(None)
                    )
                )
            )
            result = await self.db.execute(stmt)
            quality_scores = result.scalars().all()
            
            if quality_scores:
                stats["average_quality_score"] = (
                    sum(quality_scores) / len(quality_scores)
                )
        
        return stats
    
    # Helper Methods
    
    async def _check_milestone_access(
        self,
        user_id: str,
        milestone: Milestone
    ) -> Tuple[bool, str]:
        """
        Check if a user has access to start a milestone.
        """
        # Check if milestone requires payment
        if milestone.requires_payment:
            # Check user subscription
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False, "User not found"
            
            if user.subscription_tier == SubscriptionTier.FREE:
                return False, "This milestone requires a paid subscription"
        
        # Check dependencies
        can_start, missing = await check_milestone_dependencies(
            self.db,
            user_id,
            str(milestone.id)
        )
        
        if not can_start:
            return False, f"Missing dependencies: {', '.join(missing)}"
        
        return True, "Access granted"
    
    async def _update_user_leaderboard_score(self, user_id: str) -> None:
        """
        Update user's leaderboard score based on completed milestones.
        """
        # Calculate score based on completed milestones
        stmt = (
            select(UserMilestone)
            .where(
                and_(
                    UserMilestone.user_id == user_id,
                    UserMilestone.status == MilestoneStatus.COMPLETED
                )
            )
        )
        result = await self.db.execute(stmt)
        completed = result.scalars().all()
        
        # Simple scoring: 100 points per completed milestone
        # Bonus points for quality scores
        score = len(completed) * 100
        
        for um in completed:
            if um.quality_score:
                score += int(um.quality_score * 10)  # Up to 50 bonus points
        
        # Update weekly and monthly leaderboards
        await self.cache_service.update_leaderboard(user_id, score, "weekly")
        await self.cache_service.update_leaderboard(user_id, score, "monthly")
    
    def _get_mime_type(self, artifact_type: str) -> str:
        """
        Get MIME type for artifact type.
        """
        mime_types = {
            "pdf": "application/pdf",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
            "csv": "text/csv",
            "txt": "text/plain",
            "html": "text/html"
        }
        return mime_types.get(artifact_type, "application/octet-stream")