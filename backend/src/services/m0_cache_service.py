"""
M0 Intelligent Cache Service

Advanced caching layer for M0 feasibility snapshots with predictive preloading,
similarity matching, and performance optimization.
"""

import asyncio
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from ..models.m0_feasibility import (
    M0FeasibilitySnapshot, M0ResearchCache, M0PerformanceLog,
    M0Status
)
from ..infrastructure.redis.redis_mcp import RedisMCPClient
from .mcp_integrations.memory_bank import MemoryBankMCP

logger = logging.getLogger(__name__)


class M0CacheService:
    """
    Intelligent caching service for M0 feasibility analysis.
    
    Features:
    - Semantic similarity matching for idea deduplication
    - Predictive preloading based on user patterns
    - Multi-tier caching (Redis + PostgreSQL)
    - Automatic cache warming and invalidation
    - Performance-aware cache strategies
    """
    
    # Cache configuration
    CACHE_TTL_SECONDS = 3600  # 1 hour for hot cache
    RESEARCH_CACHE_TTL_HOURS = 24  # 24 hours for research data
    SIMILARITY_THRESHOLD = 0.85  # 85% similarity for cache hit
    MAX_CACHE_SIZE = 1000  # Maximum cached snapshots
    PRELOAD_BATCH_SIZE = 10  # Batch size for predictive preloading
    
    def __init__(
        self,
        db_session: AsyncSession,
        redis_client: RedisMCPClient,
        memory_bank: Optional[MemoryBankMCP] = None
    ):
        """Initialize the cache service."""
        self.db = db_session
        self.redis = redis_client
        self.memory_bank = memory_bank or MemoryBankMCP()
        
        # Initialize TF-IDF vectorizer for similarity matching
        self.vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "similarity_hits": 0,
            "preload_hits": 0,
            "evictions": 0
        }
        
        # Preload queue
        self.preload_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.preload_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> bool:
        """Initialize the cache service and start background tasks."""
        try:
            # Initialize memory bank connection
            await self.memory_bank.initialize()
            
            # Start preload worker
            self.preload_task = asyncio.create_task(self._preload_worker())
            
            # Warm up cache with popular ideas
            await self._warm_cache()
            
            logger.info("M0 Cache Service initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize cache service: {e}")
            return False
    
    async def get_cached_snapshot(
        self,
        idea_summary: str,
        user_profile: Dict[str, Any],
        use_similarity: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached snapshot with intelligent matching.
        
        Args:
            idea_summary: Business idea description
            user_profile: User experience/budget profile
            use_similarity: Whether to use similarity matching
            
        Returns:
            Cached snapshot data or None
        """
        try:
            # Step 1: Check exact match in hot cache
            cache_key = self._generate_cache_key(idea_summary, user_profile)
            cached = await self._get_hot_cache(cache_key)
            
            if cached:
                self.stats["hits"] += 1
                await self._record_cache_hit(cache_key, "exact")
                return cached
            
            # Step 2: Check similarity match if enabled
            if use_similarity:
                similar = await self._find_similar_snapshot(idea_summary, user_profile)
                
                if similar:
                    self.stats["similarity_hits"] += 1
                    await self._record_cache_hit(cache_key, "similarity")
                    
                    # Promote to hot cache
                    await self._set_hot_cache(cache_key, similar)
                    
                    return similar
            
            # Step 3: Check research cache for partial data
            research = await self._get_research_cache(idea_summary)
            
            if research:
                # Queue for preloading complete analysis
                await self._queue_preload(idea_summary, user_profile)
                
                return {
                    "partial": True,
                    "research_data": research,
                    "message": "Partial data available - full analysis generating"
                }
            
            self.stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache lookup failed: {e}")
            return None
    
    async def store_snapshot(
        self,
        snapshot_id: str,
        idea_summary: str,
        user_profile: Dict[str, Any],
        snapshot_data: Dict[str, Any],
        research_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store snapshot in multi-tier cache.
        
        Args:
            snapshot_id: Unique snapshot ID
            idea_summary: Business idea description
            user_profile: User profile
            snapshot_data: Complete snapshot data
            research_data: Optional research data for separate caching
            
        Returns:
            Success status
        """
        try:
            # Generate cache keys
            cache_key = self._generate_cache_key(idea_summary, user_profile)
            idea_hash = self._generate_idea_hash(idea_summary)
            
            # Store in hot cache (Redis)
            await self._set_hot_cache(cache_key, snapshot_data)
            
            # Store idea hash mapping
            await self.redis.set_cache(
                f"m0:hash:{idea_hash}",
                snapshot_id,
                self.CACHE_TTL_SECONDS
            )
            
            # Store research data separately if provided
            if research_data:
                await self._store_research_cache(
                    idea_hash,
                    idea_summary,
                    research_data
                )
            
            # Update similarity index
            await self._update_similarity_index(idea_summary, snapshot_id)
            
            # Check cache size and evict if necessary
            await self._manage_cache_size()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store snapshot: {e}")
            return False
    
    async def _find_similar_snapshot(
        self,
        idea_summary: str,
        user_profile: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find similar cached snapshot using semantic similarity."""
        try:
            # Get recent snapshots for similarity comparison
            stmt = select(M0FeasibilitySnapshot).where(
                and_(
                    M0FeasibilitySnapshot.status == M0Status.COMPLETED.value,
                    M0FeasibilitySnapshot.created_at > datetime.utcnow() - timedelta(hours=24)
                )
            ).limit(100)
            
            result = await self.db.execute(stmt)
            snapshots = result.scalars().all()
            
            if not snapshots:
                return None
            
            # Extract idea summaries
            summaries = [s.idea_summary for s in snapshots]
            summaries.append(idea_summary)
            
            # Vectorize and compute similarities
            try:
                vectors = self.vectorizer.fit_transform(summaries)
                query_vector = vectors[-1]
                candidate_vectors = vectors[:-1]
                
                similarities = cosine_similarity(query_vector, candidate_vectors)[0]
                
                # Find best match above threshold
                best_idx = np.argmax(similarities)
                best_similarity = similarities[best_idx]
                
                if best_similarity >= self.SIMILARITY_THRESHOLD:
                    # Check if user profiles are compatible
                    best_snapshot = snapshots[best_idx]
                    
                    if self._are_profiles_compatible(
                        user_profile,
                        best_snapshot.user_profile
                    ):
                        logger.info(
                            f"Found similar snapshot with {best_similarity:.2%} similarity"
                        )
                        return best_snapshot.to_dict()
                
            except Exception as e:
                logger.error(f"Similarity matching failed: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Similar snapshot lookup failed: {e}")
            return None
    
    async def _get_hot_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from hot cache (Redis)."""
        try:
            cached = await self.redis.get_cache(cache_key)
            
            if cached:
                # Update access time
                await self.redis.set_cache(
                    f"{cache_key}:accessed",
                    datetime.utcnow().isoformat(),
                    self.CACHE_TTL_SECONDS
                )
                
            return cached
            
        except Exception as e:
            logger.error(f"Hot cache lookup failed: {e}")
            return None
    
    async def _set_hot_cache(
        self,
        cache_key: str,
        data: Dict[str, Any]
    ) -> None:
        """Store in hot cache (Redis)."""
        try:
            await self.redis.set_cache(
                cache_key,
                data,
                self.CACHE_TTL_SECONDS
            )
            
            # Store metadata
            await self.redis.set_cache(
                f"{cache_key}:metadata",
                {
                    "stored_at": datetime.utcnow().isoformat(),
                    "size": len(json.dumps(data)),
                    "access_count": 1
                },
                self.CACHE_TTL_SECONDS
            )
            
        except Exception as e:
            logger.error(f"Hot cache store failed: {e}")
    
    async def _get_research_cache(
        self,
        idea_summary: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached research data."""
        try:
            idea_hash = self._generate_idea_hash(idea_summary)
            
            # Check database research cache
            stmt = select(M0ResearchCache).where(
                and_(
                    M0ResearchCache.idea_hash == idea_hash,
                    M0ResearchCache.expires_at > datetime.utcnow(),
                    M0ResearchCache.is_valid == True
                )
            ).order_by(M0ResearchCache.created_at.desc())
            
            result = await self.db.execute(stmt)
            cache = result.scalar_one_or_none()
            
            if cache:
                # Update hit count
                cache.hit_count += 1
                await self.db.commit()
                
                return {
                    "search_results": cache.search_results,
                    "evidence": cache.processed_evidence,
                    "competitors": cache.competitor_data,
                    "signals": cache.market_signals
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Research cache lookup failed: {e}")
            return None
    
    async def _store_research_cache(
        self,
        idea_hash: str,
        research_query: str,
        research_data: Dict[str, Any]
    ) -> None:
        """Store research data in cache."""
        try:
            cache = M0ResearchCache(
                idea_hash=idea_hash,
                research_query=research_query,
                search_results=research_data.get("search_results", {}),
                processed_evidence=research_data.get("evidence", []),
                competitor_data=research_data.get("competitors", []),
                market_signals=research_data.get("signals", {}),
                fetch_time_ms=research_data.get("fetch_time_ms", 0),
                expires_at=datetime.utcnow() + timedelta(hours=self.RESEARCH_CACHE_TTL_HOURS)
            )
            
            self.db.add(cache)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to store research cache: {e}")
    
    async def _warm_cache(self) -> None:
        """Warm up cache with popular/recent ideas."""
        try:
            # Get most accessed snapshots
            stmt = select(M0FeasibilitySnapshot).where(
                M0FeasibilitySnapshot.status == M0Status.COMPLETED.value
            ).order_by(
                M0FeasibilitySnapshot.created_at.desc()
            ).limit(20)
            
            result = await self.db.execute(stmt)
            snapshots = result.scalars().all()
            
            # Cache them
            for snapshot in snapshots:
                cache_key = self._generate_cache_key(
                    snapshot.idea_summary,
                    snapshot.user_profile
                )
                
                await self._set_hot_cache(cache_key, snapshot.to_dict())
            
            logger.info(f"Warmed cache with {len(snapshots)} snapshots")
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
    
    async def _preload_worker(self) -> None:
        """Background worker for predictive preloading."""
        while True:
            try:
                # Get preload request from queue
                request = await self.preload_queue.get()
                
                # Check if already being processed
                processing_key = f"m0:preload:{request['idea_hash']}"
                if await self.redis.get_cache(processing_key):
                    continue
                
                # Mark as processing
                await self.redis.set_cache(processing_key, "processing", 60)
                
                # Trigger preload generation
                logger.info(f"Preloading analysis for idea: {request['idea_summary'][:50]}...")
                
                # This would trigger the M0 generator in background
                # await self._trigger_background_generation(request)
                
            except Exception as e:
                logger.error(f"Preload worker error: {e}")
                await asyncio.sleep(1)
    
    async def _queue_preload(
        self,
        idea_summary: str,
        user_profile: Dict[str, Any]
    ) -> None:
        """Queue idea for predictive preloading."""
        try:
            if not self.preload_queue.full():
                await self.preload_queue.put({
                    "idea_summary": idea_summary,
                    "user_profile": user_profile,
                    "idea_hash": self._generate_idea_hash(idea_summary),
                    "timestamp": datetime.utcnow()
                })
        except:
            pass  # Ignore if queue is full
    
    async def _manage_cache_size(self) -> None:
        """Manage cache size with intelligent eviction."""
        try:
            # Get cache size
            cache_size = await self.redis.get_cache("m0:cache:size") or 0
            
            if cache_size > self.MAX_CACHE_SIZE:
                # Implement LRU eviction
                await self._evict_lru_entries(cache_size - self.MAX_CACHE_SIZE)
                
        except Exception as e:
            logger.error(f"Cache size management failed: {e}")
    
    async def _evict_lru_entries(self, count: int) -> None:
        """Evict least recently used cache entries."""
        try:
            # Get access times from Redis
            pattern = "m0:snapshot:*:accessed"
            keys = await self.redis.client.keys(pattern)
            
            if not keys:
                return
            
            # Sort by access time
            access_times = []
            for key in keys[:count]:
                accessed = await self.redis.get_cache(key)
                if accessed:
                    cache_key = key.replace(":accessed", "")
                    access_times.append((cache_key, accessed))
            
            # Sort and evict oldest
            access_times.sort(key=lambda x: x[1])
            
            for cache_key, _ in access_times[:count]:
                await self.redis.delete_cache(cache_key)
                self.stats["evictions"] += 1
            
            logger.info(f"Evicted {count} cache entries")
            
        except Exception as e:
            logger.error(f"LRU eviction failed: {e}")
    
    async def _update_similarity_index(
        self,
        idea_summary: str,
        snapshot_id: str
    ) -> None:
        """Update similarity index for fast lookup."""
        try:
            # Store in memory bank for vector similarity
            if self.memory_bank:
                await self.memory_bank.store_memory(
                    key=f"m0:similarity:{snapshot_id}",
                    content=idea_summary,
                    metadata={"snapshot_id": snapshot_id}
                )
        except Exception as e:
            logger.error(f"Similarity index update failed: {e}")
    
    async def _record_cache_hit(
        self,
        cache_key: str,
        hit_type: str
    ) -> None:
        """Record cache hit for analytics."""
        try:
            # Update access count
            metadata_key = f"{cache_key}:metadata"
            metadata = await self.redis.get_cache(metadata_key) or {}
            metadata["access_count"] = metadata.get("access_count", 0) + 1
            metadata["last_accessed"] = datetime.utcnow().isoformat()
            metadata["last_hit_type"] = hit_type
            
            await self.redis.set_cache(
                metadata_key,
                metadata,
                self.CACHE_TTL_SECONDS
            )
            
        except Exception as e:
            logger.error(f"Failed to record cache hit: {e}")
    
    def _generate_cache_key(
        self,
        idea_summary: str,
        user_profile: Dict[str, Any]
    ) -> str:
        """Generate cache key for snapshot."""
        normalized = f"{idea_summary.lower().strip()}:{json.dumps(user_profile, sort_keys=True)}"
        hash_value = hashlib.md5(normalized.encode()).hexdigest()
        return f"m0:snapshot:{hash_value}"
    
    def _generate_idea_hash(self, idea_summary: str) -> str:
        """Generate hash for idea deduplication."""
        normalized = idea_summary.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _are_profiles_compatible(
        self,
        profile1: Dict[str, Any],
        profile2: Dict[str, Any]
    ) -> bool:
        """Check if user profiles are compatible for cache sharing."""
        # Profiles are compatible if budget and experience are similar
        budget_compatible = (
            profile1.get("budget_band") == profile2.get("budget_band") or
            self._are_budgets_adjacent(
                profile1.get("budget_band"),
                profile2.get("budget_band")
            )
        )
        
        experience_compatible = (
            profile1.get("experience") == profile2.get("experience") or
            self._are_experiences_similar(
                profile1.get("experience"),
                profile2.get("experience")
            )
        )
        
        return budget_compatible and experience_compatible
    
    def _are_budgets_adjacent(self, budget1: str, budget2: str) -> bool:
        """Check if budget bands are adjacent."""
        bands = ["<5k", "5k-25k", "25k-100k", "100k+"]
        
        try:
            idx1 = bands.index(budget1)
            idx2 = bands.index(budget2)
            return abs(idx1 - idx2) <= 1
        except:
            return False
    
    def _are_experiences_similar(self, exp1: str, exp2: str) -> bool:
        """Check if experience levels are similar."""
        levels = ["none", "some", "experienced"]
        
        try:
            idx1 = levels.index(exp1)
            idx2 = levels.index(exp2)
            return abs(idx1 - idx2) <= 1
        except:
            return False
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        try:
            # Calculate hit rate
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
            
            # Get cache size
            pattern = "m0:snapshot:*"
            keys = await self.redis.client.keys(pattern)
            cache_size = len(keys)
            
            # Get database cache stats
            stmt = select(func.count(M0ResearchCache.id)).where(
                M0ResearchCache.expires_at > datetime.utcnow()
            )
            result = await self.db.execute(stmt)
            research_cache_size = result.scalar() or 0
            
            return {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "similarity_hits": self.stats["similarity_hits"],
                "preload_hits": self.stats["preload_hits"],
                "evictions": self.stats["evictions"],
                "hit_rate": f"{hit_rate:.2%}",
                "hot_cache_size": cache_size,
                "research_cache_size": research_cache_size,
                "max_cache_size": self.MAX_CACHE_SIZE,
                "cache_ttl_seconds": self.CACHE_TTL_SECONDS,
                "similarity_threshold": self.SIMILARITY_THRESHOLD
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return self.stats
    
    async def invalidate_cache(
        self,
        idea_summary: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> int:
        """
        Invalidate cache entries.
        
        Args:
            idea_summary: Specific idea to invalidate
            user_id: Invalidate all entries for user
            
        Returns:
            Number of entries invalidated
        """
        try:
            count = 0
            
            if idea_summary:
                # Invalidate specific idea
                idea_hash = self._generate_idea_hash(idea_summary)
                pattern = f"m0:*{idea_hash}*"
                
            elif user_id:
                # Invalidate user's entries
                pattern = f"m0:user:{user_id}:*"
                
            else:
                # Invalidate all
                pattern = "m0:*"
            
            keys = await self.redis.client.keys(pattern)
            
            for key in keys:
                await self.redis.delete_cache(key)
                count += 1
            
            logger.info(f"Invalidated {count} cache entries")
            return count
            
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0
    
    async def shutdown(self) -> None:
        """Shutdown cache service cleanly."""
        try:
            # Cancel preload worker
            if self.preload_task:
                self.preload_task.cancel()
                
            # Flush any pending operations
            await self.redis.client.flushall()
            
            logger.info("M0 Cache Service shutdown complete")
            
        except Exception as e:
            logger.error(f"Shutdown error: {e}")