"""
Milestone PostgreSQL Persistence Layer with MCP Integration

This module implements a robust persistence layer for milestone management
with advanced connection pooling, transaction management, and error handling.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple, Type, TypeVar
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from uuid import UUID
import json
from functools import wraps
import backoff

from sqlalchemy import select, update, delete, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine
from sqlalchemy.orm import selectinload, joinedload, subqueryload
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.dialects.postgresql import insert

from ...models.milestone import (
    Milestone, MilestoneDependency, UserMilestone, MilestoneArtifact,
    UserMilestoneArtifact, MilestoneProgressLog, MilestoneCache,
    MilestoneStatus, MilestoneType
)
from ...models.user import User

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConnectionPoolManager:
    """
    Manages database connection pooling with advanced monitoring and optimization.
    """
    
    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 40,
        pool_timeout: float = 30.0,
        pool_recycle: int = 3600,
        echo_pool: bool = False
    ):
        """Initialize connection pool manager."""
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo_pool = echo_pool
        
        self._engine: Optional[AsyncEngine] = None
        self._pool_stats = {
            "connections_created": 0,
            "connections_recycled": 0,
            "overflow_created": 0,
            "pool_timeouts": 0
        }
    
    async def initialize(self) -> AsyncEngine:
        """Initialize the connection pool."""
        if self._engine:
            return self._engine
        
        self._engine = create_async_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_timeout=self.pool_timeout,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=True,  # Verify connections before use
            echo_pool=self.echo_pool,
            connect_args={
                "server_settings": {
                    "application_name": "prolaunch_milestone_service",
                    "jit": "off"  # Disable JIT for consistent performance
                },
                "command_timeout": 60,
                "prepared_statement_cache_size": 0,  # Disable for better connection pooling
            }
        )
        
        # Test connection
        async with self._engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info(f"Database connection pool initialized with size={self.pool_size}")
        return self._engine
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status and statistics."""
        if not self._engine:
            return {"status": "not_initialized"}
        
        pool = self._engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.total(),
            "stats": self._pool_stats
        }
    
    async def close(self):
        """Close all connections in the pool."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            logger.info("Database connection pool closed")


class TransactionManager:
    """
    Manages database transactions with proper isolation and error handling.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize transaction manager."""
        self.session = session
        self._savepoint_counter = 0
    
    @asynccontextmanager
    async def transaction(self, isolation_level: Optional[str] = None):
        """
        Create a transaction context with optional isolation level.
        
        Isolation levels:
        - READ COMMITTED (default)
        - REPEATABLE READ
        - SERIALIZABLE
        """
        if isolation_level:
            await self.session.execute(
                text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
            )
        
        try:
            yield self.session
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
    
    @asynccontextmanager
    async def savepoint(self, name: Optional[str] = None):
        """Create a savepoint for nested transactions."""
        if not name:
            self._savepoint_counter += 1
            name = f"sp_{self._savepoint_counter}"
        
        await self.session.execute(text(f"SAVEPOINT {name}"))
        
        try:
            yield
        except Exception as e:
            await self.session.execute(text(f"ROLLBACK TO SAVEPOINT {name}"))
            logger.error(f"Rolled back to savepoint {name}: {e}")
            raise
        else:
            await self.session.execute(text(f"RELEASE SAVEPOINT {name}"))


class MilestonePersistence:
    """
    PostgreSQL persistence layer for milestone management with MCP integration.
    Provides CRUD operations, dependency tracking, and optimized queries.
    """
    
    def __init__(
        self,
        pool_manager: ConnectionPoolManager,
        enable_query_cache: bool = True,
        cache_ttl: int = 300
    ):
        """Initialize milestone persistence layer."""
        self.pool_manager = pool_manager
        self.enable_query_cache = enable_query_cache
        self.cache_ttl = cache_ttl
        self._query_cache: Dict[str, Tuple[Any, datetime]] = {}
    
    # Decorator for retry logic
    def with_retry(
        max_tries: int = 3,
        max_time: int = 10,
        on_exception: Type[Exception] = OperationalError
    ):
        """Decorator for automatic retry with exponential backoff."""
        def decorator(func):
            @wraps(func)
            @backoff.on_exception(
                backoff.expo,
                on_exception,
                max_tries=max_tries,
                max_time=max_time,
                on_backoff=lambda details: logger.warning(
                    f"Retrying {func.__name__} after {details['wait']}s (attempt {details['tries']})"
                )
            )
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    # Connection Management
    
    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """Get a database session from the pool."""
        engine = await self.pool_manager.initialize()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session
    
    # Milestone CRUD Operations
    
    @with_retry(max_tries=3)
    async def create_milestone(
        self,
        milestone_data: Dict[str, Any]
    ) -> Milestone:
        """Create a new milestone with error handling."""
        async with self.get_session() as session:
            tm = TransactionManager(session)
            
            async with tm.transaction():
                milestone = Milestone(**milestone_data)
                session.add(milestone)
                await session.flush()
                
                # Log creation
                logger.info(f"Created milestone: {milestone.code}")
                
                return milestone
    
    @with_retry(max_tries=3)
    async def get_milestone(
        self,
        milestone_id: Optional[UUID] = None,
        code: Optional[str] = None,
        load_relationships: bool = True
    ) -> Optional[Milestone]:
        """
        Retrieve a milestone by ID or code with optimized loading.
        """
        # Check cache first
        cache_key = f"milestone:{milestone_id or code}"
        if self.enable_query_cache and cache_key in self._query_cache:
            cached, timestamp = self._query_cache[cache_key]
            if (datetime.utcnow() - timestamp).seconds < self.cache_ttl:
                return cached
        
        async with self.get_session() as session:
            query = select(Milestone)
            
            # Add filters
            if milestone_id:
                query = query.where(Milestone.id == milestone_id)
            elif code:
                query = query.where(Milestone.code == code)
            else:
                return None
            
            # Optimize loading strategy
            if load_relationships:
                query = query.options(
                    selectinload(Milestone.dependencies).selectinload(
                        MilestoneDependency.dependency
                    ),
                    selectinload(Milestone.artifacts),
                    selectinload(Milestone.user_milestones)
                )
            
            result = await session.execute(query)
            milestone = result.scalar_one_or_none()
            
            # Cache result
            if milestone and self.enable_query_cache:
                self._query_cache[cache_key] = (milestone, datetime.utcnow())
            
            return milestone
    
    @with_retry(max_tries=3)
    async def update_milestone(
        self,
        milestone_id: UUID,
        updates: Dict[str, Any]
    ) -> bool:
        """Update a milestone with optimistic locking."""
        async with self.get_session() as session:
            tm = TransactionManager(session)
            
            async with tm.transaction():
                # Use UPDATE with RETURNING for atomicity
                stmt = (
                    update(Milestone)
                    .where(Milestone.id == milestone_id)
                    .values(**updates, updated_at=datetime.utcnow())
                    .returning(Milestone.id)
                )
                
                result = await session.execute(stmt)
                updated_id = result.scalar_one_or_none()
                
                if updated_id:
                    # Invalidate cache
                    self._invalidate_cache(f"milestone:{milestone_id}")
                    logger.info(f"Updated milestone: {milestone_id}")
                    return True
                
                return False
    
    @with_retry(max_tries=3)
    async def delete_milestone(
        self,
        milestone_id: UUID,
        cascade: bool = True
    ) -> bool:
        """Delete a milestone with optional cascade."""
        async with self.get_session() as session:
            tm = TransactionManager(session)
            
            async with tm.transaction():
                if cascade:
                    # Delete in order to respect foreign keys
                    await session.execute(
                        delete(MilestoneProgressLog)
                        .where(MilestoneProgressLog.user_milestone_id.in_(
                            select(UserMilestone.id)
                            .where(UserMilestone.milestone_id == milestone_id)
                        ))
                    )
                    
                    await session.execute(
                        delete(UserMilestoneArtifact)
                        .where(UserMilestoneArtifact.user_milestone_id.in_(
                            select(UserMilestone.id)
                            .where(UserMilestone.milestone_id == milestone_id)
                        ))
                    )
                    
                    await session.execute(
                        delete(UserMilestone)
                        .where(UserMilestone.milestone_id == milestone_id)
                    )
                    
                    await session.execute(
                        delete(MilestoneDependency)
                        .where(or_(
                            MilestoneDependency.milestone_id == milestone_id,
                            MilestoneDependency.dependency_id == milestone_id
                        ))
                    )
                    
                    await session.execute(
                        delete(MilestoneArtifact)
                        .where(MilestoneArtifact.milestone_id == milestone_id)
                    )
                
                # Delete the milestone
                result = await session.execute(
                    delete(Milestone)
                    .where(Milestone.id == milestone_id)
                    .returning(Milestone.id)
                )
                
                deleted_id = result.scalar_one_or_none()
                
                if deleted_id:
                    self._invalidate_cache(f"milestone:{milestone_id}")
                    logger.info(f"Deleted milestone: {milestone_id}")
                    return True
                
                return False
    
    # Bulk Operations
    
    @with_retry(max_tries=3)
    async def bulk_create_milestones(
        self,
        milestones_data: List[Dict[str, Any]]
    ) -> List[Milestone]:
        """Bulk create milestones with optimal performance."""
        async with self.get_session() as session:
            tm = TransactionManager(session)
            
            async with tm.transaction():
                milestones = []
                
                # Use bulk insert for better performance
                for data in milestones_data:
                    milestone = Milestone(**data)
                    session.add(milestone)
                    milestones.append(milestone)
                
                await session.flush()
                
                logger.info(f"Bulk created {len(milestones)} milestones")
                return milestones
    
    @with_retry(max_tries=3)
    async def bulk_update_user_milestones(
        self,
        updates: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk update user milestones with optimal batching.
        
        Each update dict should contain:
        - user_id: UUID
        - milestone_id: UUID
        - fields to update
        """
        async with self.get_session() as session:
            tm = TransactionManager(session)
            
            async with tm.transaction():
                updated_count = 0
                
                # Batch updates for performance
                for update_data in updates:
                    user_id = update_data.pop('user_id')
                    milestone_id = update_data.pop('milestone_id')
                    
                    stmt = (
                        update(UserMilestone)
                        .where(and_(
                            UserMilestone.user_id == user_id,
                            UserMilestone.milestone_id == milestone_id
                        ))
                        .values(**update_data, updated_at=datetime.utcnow())
                    )
                    
                    result = await session.execute(stmt)
                    updated_count += result.rowcount
                
                logger.info(f"Bulk updated {updated_count} user milestones")
                return updated_count
    
    # Dependency Management
    
    @with_retry(max_tries=3)
    async def create_dependency(
        self,
        milestone_id: UUID,
        dependency_id: UUID,
        is_required: bool = True,
        minimum_completion: float = 100.0
    ) -> MilestoneDependency:
        """Create a milestone dependency with cycle detection."""
        async with self.get_session() as session:
            tm = TransactionManager(session)
            
            async with tm.transaction():
                # Check for circular dependencies
                if await self._would_create_cycle(
                    session, milestone_id, dependency_id
                ):
                    raise ValueError(
                        f"Creating dependency would create a cycle: "
                        f"{milestone_id} -> {dependency_id}"
                    )
                
                # Create dependency
                dependency = MilestoneDependency(
                    milestone_id=milestone_id,
                    dependency_id=dependency_id,
                    is_required=is_required,
                    minimum_completion_percentage=minimum_completion
                )
                
                session.add(dependency)
                await session.flush()
                
                logger.info(
                    f"Created dependency: {milestone_id} depends on {dependency_id}"
                )
                return dependency
    
    async def _would_create_cycle(
        self,
        session: AsyncSession,
        milestone_id: UUID,
        dependency_id: UUID
    ) -> bool:
        """Check if adding a dependency would create a cycle."""
        # Use recursive CTE to check for cycles
        cte_query = text("""
            WITH RECURSIVE dependency_chain AS (
                SELECT milestone_id, dependency_id
                FROM milestone_dependencies
                WHERE milestone_id = :start_id
                
                UNION
                
                SELECT md.milestone_id, md.dependency_id
                FROM milestone_dependencies md
                JOIN dependency_chain dc ON md.milestone_id = dc.dependency_id
            )
            SELECT 1
            FROM dependency_chain
            WHERE dependency_id = :check_id
            LIMIT 1
        """)
        
        result = await session.execute(
            cte_query,
            {"start_id": dependency_id, "check_id": milestone_id}
        )
        
        return result.scalar() is not None
    
    @with_retry(max_tries=3)
    async def get_dependency_graph(
        self,
        milestone_id: Optional[UUID] = None
    ) -> Dict[str, List[str]]:
        """
        Get the complete dependency graph.
        Returns a dictionary mapping milestone IDs to their dependencies.
        """
        async with self.get_session() as session:
            query = select(MilestoneDependency)
            
            if milestone_id:
                # Get dependencies for specific milestone and its tree
                query = text("""
                    WITH RECURSIVE dependency_tree AS (
                        SELECT milestone_id, dependency_id
                        FROM milestone_dependencies
                        WHERE milestone_id = :milestone_id
                        
                        UNION
                        
                        SELECT md.milestone_id, md.dependency_id
                        FROM milestone_dependencies md
                        JOIN dependency_tree dt ON md.milestone_id = dt.dependency_id
                    )
                    SELECT * FROM dependency_tree
                """)
                result = await session.execute(
                    query, {"milestone_id": milestone_id}
                )
            else:
                result = await session.execute(query)
            
            graph = {}
            for row in result:
                if milestone_id:
                    milestone_id_str = str(row[0])
                    dependency_id_str = str(row[1])
                else:
                    milestone_id_str = str(row.milestone_id)
                    dependency_id_str = str(row.dependency_id)
                
                if milestone_id_str not in graph:
                    graph[milestone_id_str] = []
                graph[milestone_id_str].append(dependency_id_str)
            
            return graph
    
    # User Progress Tracking
    
    @with_retry(max_tries=3)
    async def create_user_milestone(
        self,
        user_id: UUID,
        milestone_id: UUID,
        initial_status: MilestoneStatus = MilestoneStatus.LOCKED
    ) -> UserMilestone:
        """Create a user milestone record."""
        async with self.get_session() as session:
            tm = TransactionManager(session)
            
            async with tm.transaction():
                # Use INSERT ... ON CONFLICT for idempotency
                stmt = insert(UserMilestone).values(
                    user_id=user_id,
                    milestone_id=milestone_id,
                    status=initial_status,
                    created_at=datetime.utcnow()
                )
                
                stmt = stmt.on_conflict_do_update(
                    index_elements=['user_id', 'milestone_id'],
                    set_=dict(
                        updated_at=datetime.utcnow(),
                        last_accessed_at=datetime.utcnow()
                    )
                )
                
                await session.execute(stmt)
                
                # Retrieve the created/updated record
                result = await session.execute(
                    select(UserMilestone).where(and_(
                        UserMilestone.user_id == user_id,
                        UserMilestone.milestone_id == milestone_id
                    ))
                )
                
                user_milestone = result.scalar_one()
                
                logger.info(
                    f"Created user milestone: user={user_id}, milestone={milestone_id}"
                )
                return user_milestone
    
    @with_retry(max_tries=3)
    async def update_user_progress(
        self,
        user_id: UUID,
        milestone_id: UUID,
        progress_data: Dict[str, Any],
        log_event: bool = True
    ) -> bool:
        """
        Update user milestone progress with atomic operations.
        """
        async with self.get_session() as session:
            tm = TransactionManager(session)
            
            async with tm.transaction():
                # Update progress
                stmt = (
                    update(UserMilestone)
                    .where(and_(
                        UserMilestone.user_id == user_id,
                        UserMilestone.milestone_id == milestone_id
                    ))
                    .values(**progress_data, updated_at=datetime.utcnow())
                    .returning(UserMilestone.id)
                )
                
                result = await session.execute(stmt)
                user_milestone_id = result.scalar_one_or_none()
                
                if not user_milestone_id:
                    return False
                
                # Log progress event if requested
                if log_event:
                    event_type = progress_data.get('status', 'progress_update')
                    log = MilestoneProgressLog(
                        user_milestone_id=user_milestone_id,
                        event_type=event_type,
                        event_data=progress_data,
                        completion_percentage=progress_data.get(
                            'completion_percentage', 0
                        ),
                        created_at=datetime.utcnow()
                    )
                    session.add(log)
                
                logger.info(
                    f"Updated progress: user={user_id}, milestone={milestone_id}"
                )
                return True
    
    @with_retry(max_tries=3)
    async def get_user_progress_summary(
        self,
        user_id: UUID
    ) -> Dict[str, Any]:
        """Get comprehensive user progress summary with optimized queries."""
        async with self.get_session() as session:
            # Use single query with aggregations
            stmt = text("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    COUNT(*) FILTER (WHERE status = 'locked') as locked,
                    COUNT(*) FILTER (WHERE status = 'available') as available,
                    COUNT(*) as total,
                    AVG(completion_percentage) as avg_completion,
                    SUM(time_spent_seconds) as total_time_seconds,
                    AVG(quality_score) FILTER (WHERE quality_score IS NOT NULL) as avg_quality
                FROM user_milestones
                WHERE user_id = :user_id
            """)
            
            result = await session.execute(stmt, {"user_id": user_id})
            row = result.fetchone()
            
            return {
                "completed": row[0] or 0,
                "in_progress": row[1] or 0,
                "locked": row[2] or 0,
                "available": row[3] or 0,
                "total": row[4] or 0,
                "average_completion": float(row[5] or 0),
                "total_time_hours": (row[6] or 0) / 3600,
                "average_quality_score": float(row[7] or 0)
            }
    
    # Artifact Management
    
    @with_retry(max_tries=3)
    async def create_artifact(
        self,
        user_milestone_id: UUID,
        artifact_data: Dict[str, Any]
    ) -> UserMilestoneArtifact:
        """Create a user milestone artifact."""
        async with self.get_session() as session:
            tm = TransactionManager(session)
            
            async with tm.transaction():
                artifact = UserMilestoneArtifact(
                    user_milestone_id=user_milestone_id,
                    **artifact_data
                )
                
                session.add(artifact)
                await session.flush()
                
                logger.info(f"Created artifact: {artifact.name}")
                return artifact
    
    @with_retry(max_tries=3)
    async def get_user_artifacts(
        self,
        user_id: UUID,
        milestone_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserMilestoneArtifact]:
        """Get user artifacts with pagination."""
        async with self.get_session() as session:
            query = (
                select(UserMilestoneArtifact)
                .join(UserMilestone)
                .where(UserMilestone.user_id == user_id)
            )
            
            if milestone_id:
                query = query.where(UserMilestone.milestone_id == milestone_id)
            
            query = query.order_by(
                UserMilestoneArtifact.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    # Analytics and Reporting
    
    @with_retry(max_tries=3)
    async def get_milestone_analytics(
        self,
        milestone_id: UUID,
        time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get detailed analytics for a milestone."""
        async with self.get_session() as session:
            # Base query with time filter
            base_filter = [UserMilestone.milestone_id == milestone_id]
            if time_range:
                cutoff = datetime.utcnow() - time_range
                base_filter.append(UserMilestone.created_at >= cutoff)
            
            # Get aggregated statistics
            stmt = text("""
                SELECT 
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(*) FILTER (WHERE status = 'completed') as completions,
                    AVG(time_spent_seconds) FILTER (WHERE status = 'completed') as avg_time,
                    MIN(time_spent_seconds) FILTER (WHERE status = 'completed') as min_time,
                    MAX(time_spent_seconds) FILTER (WHERE status = 'completed') as max_time,
                    AVG(quality_score) FILTER (WHERE quality_score IS NOT NULL) as avg_quality,
                    AVG(completion_percentage) as avg_progress,
                    COUNT(*) FILTER (WHERE status = 'failed') as failures
                FROM user_milestones
                WHERE milestone_id = :milestone_id
                    AND (:has_time_filter = false OR created_at >= :cutoff)
            """)
            
            params = {
                "milestone_id": milestone_id,
                "has_time_filter": time_range is not None,
                "cutoff": datetime.utcnow() - time_range if time_range else None
            }
            
            result = await session.execute(stmt, params)
            row = result.fetchone()
            
            return {
                "unique_users": row[0] or 0,
                "completions": row[1] or 0,
                "average_completion_time_minutes": (row[2] or 0) / 60,
                "min_completion_time_minutes": (row[3] or 0) / 60,
                "max_completion_time_minutes": (row[4] or 0) / 60,
                "average_quality_score": float(row[5] or 0),
                "average_progress_percentage": float(row[6] or 0),
                "failure_count": row[7] or 0,
                "success_rate": (row[1] / row[0] * 100) if row[0] > 0 else 0
            }
    
    @with_retry(max_tries=3)
    async def get_leaderboard(
        self,
        time_period: str = "all",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get leaderboard data based on milestone completions.
        
        time_period: 'day', 'week', 'month', 'all'
        """
        async with self.get_session() as session:
            # Calculate time cutoff
            cutoff = None
            if time_period == "day":
                cutoff = datetime.utcnow() - timedelta(days=1)
            elif time_period == "week":
                cutoff = datetime.utcnow() - timedelta(days=7)
            elif time_period == "month":
                cutoff = datetime.utcnow() - timedelta(days=30)
            
            # Query with window functions for ranking
            stmt = text("""
                WITH user_scores AS (
                    SELECT 
                        um.user_id,
                        u.username,
                        COUNT(*) FILTER (WHERE um.status = 'completed') as completed_count,
                        AVG(um.quality_score) FILTER (WHERE um.quality_score IS NOT NULL) as avg_quality,
                        SUM(um.time_spent_seconds) as total_time,
                        -- Calculate score: completions * 100 + quality bonus
                        COUNT(*) FILTER (WHERE um.status = 'completed') * 100 +
                        COALESCE(AVG(um.quality_score) * 10, 0) as score
                    FROM user_milestones um
                    JOIN users u ON um.user_id = u.id
                    WHERE (:has_cutoff = false OR um.completed_at >= :cutoff)
                    GROUP BY um.user_id, u.username
                )
                SELECT 
                    user_id,
                    username,
                    completed_count,
                    avg_quality,
                    total_time,
                    score,
                    RANK() OVER (ORDER BY score DESC) as rank
                FROM user_scores
                ORDER BY rank
                LIMIT :limit
            """)
            
            params = {
                "has_cutoff": cutoff is not None,
                "cutoff": cutoff,
                "limit": limit
            }
            
            result = await session.execute(stmt, params)
            
            leaderboard = []
            for row in result:
                leaderboard.append({
                    "rank": row[6],
                    "user_id": str(row[0]),
                    "username": row[1],
                    "completed_milestones": row[2],
                    "average_quality": float(row[3] or 0),
                    "total_time_hours": (row[4] or 0) / 3600,
                    "score": int(row[5])
                })
            
            return leaderboard
    
    # Cache Management
    
    def _invalidate_cache(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        if not self.enable_query_cache:
            return
        
        keys_to_remove = [
            key for key in self._query_cache
            if pattern in key or key.startswith(pattern)
        ]
        
        for key in keys_to_remove:
            del self._query_cache[key]
        
        if keys_to_remove:
            logger.debug(f"Invalidated {len(keys_to_remove)} cache entries")
    
    async def clear_cache(self):
        """Clear all cached queries."""
        self._query_cache.clear()
        logger.info("Query cache cleared")
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on persistence layer."""
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        try:
            # Check database connection
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                health["checks"]["database"] = "ok"
            
            # Check pool status
            pool_status = await self.pool_manager.get_pool_status()
            health["checks"]["connection_pool"] = pool_status
            
            # Check cache
            if self.enable_query_cache:
                health["checks"]["cache_entries"] = len(self._query_cache)
            
        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health


# Factory function for creating persistence layer
async def create_milestone_persistence(
    database_url: str,
    pool_size: int = 20,
    max_overflow: int = 40,
    enable_cache: bool = True
) -> MilestonePersistence:
    """
    Factory function to create and initialize milestone persistence layer.
    """
    pool_manager = ConnectionPoolManager(
        database_url=database_url,
        pool_size=pool_size,
        max_overflow=max_overflow
    )
    
    # Initialize pool
    await pool_manager.initialize()
    
    persistence = MilestonePersistence(
        pool_manager=pool_manager,
        enable_query_cache=enable_cache
    )
    
    logger.info("Milestone persistence layer initialized")
    return persistence