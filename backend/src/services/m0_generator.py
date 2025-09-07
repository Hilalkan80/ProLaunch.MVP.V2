"""
M0 Feasibility Snapshot Generator Service

High-performance service for generating M0 feasibility snapshots in under 60 seconds.
Uses parallel processing, intelligent caching, and optimized research pipelines.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..models.m0_feasibility import (
    M0FeasibilitySnapshot, M0ResearchCache, M0PerformanceLog,
    ViabilityScoreRange, M0Status
)
from ..ai.llama_service import LlamaService
from ..ai.prompt_loader import PromptLoader
from .context.context_manager import ContextManager
from .mcp_integrations.memory_bank import MemoryBankMCP
from .mcp_integrations.ref_optimization import RefMCP
from .mcp_integrations.redis_integration import RedisMCPClient
from .citation_service import CitationService
from ..infrastructure.redis.redis_mcp import RedisMCPClient as RedisCache

logger = logging.getLogger(__name__)


class M0GeneratorService:
    """
    High-performance M0 feasibility snapshot generator.
    Optimized for sub-60 second generation with accuracy preservation.
    """
    
    # Performance targets (in milliseconds)
    TARGET_TOTAL_TIME_MS = 60000  # 60 seconds
    TARGET_RESEARCH_TIME_MS = 25000  # 25 seconds for research
    TARGET_ANALYSIS_TIME_MS = 20000  # 20 seconds for analysis
    TARGET_CACHE_LOOKUP_MS = 1000  # 1 second for cache lookup
    
    def __init__(
        self,
        db_session: AsyncSession,
        llama_service: LlamaService,
        citation_service: CitationService,
        context_manager: ContextManager,
        redis_cache: RedisCache
    ):
        """Initialize the M0 generator service."""
        self.db = db_session
        self.llama = llama_service
        self.citations = citation_service
        self.context = context_manager
        self.redis = redis_cache
        
        # Initialize MCP integrations
        self.memory_bank = MemoryBankMCP()
        self.ref_mcp = RefMCP()
        
        # Load prompt template
        self.prompt_loader = PromptLoader()
        self.m0_prompt_template = None
        
        # Performance tracking
        self.perf_metrics = {
            "total_generations": 0,
            "avg_time_ms": 0,
            "cache_hit_rate": 0,
            "success_rate": 0
        }
    
    async def initialize(self) -> bool:
        """Initialize the service and load prompt templates."""
        try:
            # Load M0 prompt template
            self.m0_prompt_template = await self.prompt_loader.load_prompt(
                "milestones/m0_feasibility_snapshot.md"
            )
            
            # Initialize MCP connections
            await self.memory_bank.initialize()
            await self.ref_mcp.initialize()
            
            logger.info("M0 Generator Service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize M0 Generator: {e}")
            return False
    
    async def generate_snapshot(
        self,
        user_id: str,
        idea_summary: str,
        user_profile: Dict[str, Any],
        project_id: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Generate an M0 feasibility snapshot with sub-60 second target.
        
        Args:
            user_id: User ID
            idea_summary: Business idea summary
            user_profile: User experience/budget/timeline profile
            project_id: Optional project ID
            use_cache: Whether to use cached research data
            
        Returns:
            Generated M0 snapshot data
        """
        start_time = time.time()
        perf_log = {
            "api_calls": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "used_cache": False,
            "parallel_research": True,
            "batch_processing": True,
            "had_errors": False,
            "error_details": []
        }
        
        try:
            # Step 1: Check cache for existing analysis (target: <1s)
            cache_start = time.time()
            cached_snapshot = None
            
            if use_cache:
                idea_hash = self._generate_idea_hash(idea_summary, user_profile)
                cached_snapshot = await self._get_cached_snapshot(idea_hash)
                
                if cached_snapshot:
                    perf_log["cache_hits"] += 1
                    perf_log["used_cache"] = True
                    cache_time = int((time.time() - cache_start) * 1000)
                    
                    # Log performance
                    await self._log_performance(
                        cached_snapshot.id,
                        total_time_ms=cache_time,
                        research_time_ms=0,
                        analysis_time_ms=0,
                        cache_lookup_time_ms=cache_time,
                        perf_log=perf_log
                    )
                    
                    return cached_snapshot.to_dict()
                else:
                    perf_log["cache_misses"] += 1
            
            cache_lookup_time = int((time.time() - cache_start) * 1000)
            
            # Step 2: Parallel research gathering (target: <25s)
            research_start = time.time()
            research_data = await self._gather_research_parallel(
                idea_summary,
                user_profile,
                perf_log
            )
            research_time = int((time.time() - research_start) * 1000)
            
            # Step 3: Generate analysis with LLM (target: <20s)
            analysis_start = time.time()
            analysis = await self._generate_analysis(
                idea_summary,
                user_profile,
                research_data,
                perf_log
            )
            analysis_time = int((time.time() - analysis_start) * 1000)
            
            # Step 4: Store snapshot in database
            snapshot = await self._store_snapshot(
                user_id=user_id,
                project_id=project_id,
                idea_summary=idea_summary,
                user_profile=user_profile,
                analysis=analysis,
                research_data=research_data,
                generation_time_ms=int((time.time() - start_time) * 1000),
                research_time_ms=research_time,
                analysis_time_ms=analysis_time
            )
            
            # Step 5: Cache for future use
            if use_cache:
                await self._cache_snapshot(snapshot, research_data)
            
            # Step 6: Log performance metrics
            total_time = int((time.time() - start_time) * 1000)
            await self._log_performance(
                snapshot.id,
                total_time_ms=total_time,
                research_time_ms=research_time,
                analysis_time_ms=analysis_time,
                cache_lookup_time_ms=cache_lookup_time,
                perf_log=perf_log
            )
            
            # Update service metrics
            self._update_metrics(total_time, perf_log)
            
            # Log warning if exceeded target time
            if total_time > self.TARGET_TOTAL_TIME_MS:
                logger.warning(
                    f"M0 generation exceeded target time: {total_time}ms > {self.TARGET_TOTAL_TIME_MS}ms"
                )
            
            return snapshot.to_dict()
            
        except Exception as e:
            logger.error(f"Error generating M0 snapshot: {e}")
            perf_log["had_errors"] = True
            perf_log["error_details"].append(str(e))
            
            # Store failed attempt
            total_time = int((time.time() - start_time) * 1000)
            await self._store_failed_attempt(
                user_id=user_id,
                idea_summary=idea_summary,
                error=str(e),
                perf_log=perf_log,
                total_time_ms=total_time
            )
            
            raise
    
    async def _gather_research_parallel(
        self,
        idea_summary: str,
        user_profile: Dict[str, Any],
        perf_log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Gather research data in parallel for maximum speed.
        Uses multiple data sources simultaneously.
        """
        research_tasks = []
        
        # Task 1: Market demand signals
        research_tasks.append(
            self._research_market_demand(idea_summary, perf_log)
        )
        
        # Task 2: Competitor analysis
        research_tasks.append(
            self._research_competitors(idea_summary, perf_log)
        )
        
        # Task 3: Trend analysis
        research_tasks.append(
            self._research_trends(idea_summary, perf_log)
        )
        
        # Task 4: Risk assessment
        research_tasks.append(
            self._research_risks(idea_summary, user_profile, perf_log)
        )
        
        # Task 5: Pricing research
        research_tasks.append(
            self._research_pricing(idea_summary, perf_log)
        )
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*research_tasks, return_exceptions=True)
        
        # Process results
        research_data = {
            "demand": results[0] if not isinstance(results[0], Exception) else {},
            "competitors": results[1] if not isinstance(results[1], Exception) else [],
            "trends": results[2] if not isinstance(results[2], Exception) else {},
            "risks": results[3] if not isinstance(results[3], Exception) else [],
            "pricing": results[4] if not isinstance(results[4], Exception) else {}
        }
        
        # Collect any errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                perf_log["error_details"].append(f"Research task {i} failed: {str(result)}")
        
        return research_data
    
    async def _research_market_demand(
        self,
        idea_summary: str,
        perf_log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Research market demand signals."""
        try:
            # Use citation service for verified sources
            citations = await self.citations.search_citations(
                query=f"market demand {idea_summary}",
                limit=5,
                source_types=["web", "industry"]
            )
            
            perf_log["api_calls"]["citation_search"] = perf_log.get("api_calls", {}).get("citation_search", 0) + 1
            
            return {
                "signal": self._analyze_demand_signal(citations),
                "evidence": [c.to_dict() for c in citations]
            }
            
        except Exception as e:
            logger.error(f"Market demand research failed: {e}")
            return {"signal": "unknown", "evidence": []}
    
    async def _research_competitors(
        self,
        idea_summary: str,
        perf_log: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Research competitive landscape."""
        try:
            # Search for competitors
            citations = await self.citations.search_citations(
                query=f"competitors alternatives {idea_summary}",
                limit=10,
                source_types=["web", "industry"]
            )
            
            perf_log["api_calls"]["citation_search"] = perf_log.get("api_calls", {}).get("citation_search", 0) + 1
            
            # Extract competitor information
            competitors = []
            seen_names = set()
            
            for citation in citations:
                comp_info = self._extract_competitor_info(citation)
                if comp_info and comp_info["name"] not in seen_names:
                    competitors.append(comp_info)
                    seen_names.add(comp_info["name"])
                    
                    if len(competitors) >= 3:
                        break
            
            return competitors
            
        except Exception as e:
            logger.error(f"Competitor research failed: {e}")
            return []
    
    async def _research_trends(
        self,
        idea_summary: str,
        perf_log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Research market trends."""
        try:
            # Search for trend data
            citations = await self.citations.search_citations(
                query=f"market trends growth {idea_summary}",
                limit=5,
                source_types=["web", "academic", "industry"]
            )
            
            perf_log["api_calls"]["citation_search"] = perf_log.get("api_calls", {}).get("citation_search", 0) + 1
            
            return {
                "signal": self._analyze_trend_signal(citations),
                "evidence": [c.to_dict() for c in citations]
            }
            
        except Exception as e:
            logger.error(f"Trend research failed: {e}")
            return {"signal": "neutral", "evidence": []}
    
    async def _research_risks(
        self,
        idea_summary: str,
        user_profile: Dict[str, Any],
        perf_log: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Research business risks."""
        try:
            # Search for risk factors
            citations = await self.citations.search_citations(
                query=f"risks challenges problems {idea_summary}",
                limit=5,
                source_types=["web", "industry"]
            )
            
            perf_log["api_calls"]["citation_search"] = perf_log.get("api_calls", {}).get("citation_search", 0) + 1
            
            # Extract and categorize risks
            risks = self._categorize_risks(citations, user_profile)
            
            return risks
            
        except Exception as e:
            logger.error(f"Risk research failed: {e}")
            return []
    
    async def _research_pricing(
        self,
        idea_summary: str,
        perf_log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Research pricing information."""
        try:
            # Search for pricing data
            citations = await self.citations.search_citations(
                query=f"pricing cost price range {idea_summary}",
                limit=5,
                source_types=["web", "industry"]
            )
            
            perf_log["api_calls"]["citation_search"] = perf_log.get("api_calls", {}).get("citation_search", 0) + 1
            
            # Extract pricing ranges
            pricing = self._extract_pricing_data(citations)
            
            return pricing
            
        except Exception as e:
            logger.error(f"Pricing research failed: {e}")
            return {"min": None, "max": None, "is_assumption": True}
    
    async def _generate_analysis(
        self,
        idea_summary: str,
        user_profile: Dict[str, Any],
        research_data: Dict[str, Any],
        perf_log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate the M0 analysis using LLM with optimized prompting.
        """
        try:
            # Prepare evidence array
            evidence = []
            ref_counter = 1
            
            # Collect evidence from all research
            for source in ["demand", "trends"]:
                if source in research_data and "evidence" in research_data[source]:
                    for e in research_data[source]["evidence"]:
                        evidence.append({
                            "id": f"ref_{ref_counter:03d}",
                            "title": e.get("title", ""),
                            "date": e.get("date", datetime.now().strftime("%Y-%m-%d")),
                            "snippet": e.get("snippet", ""),
                            "url": e.get("url", "")
                        })
                        ref_counter += 1
            
            # Build input for M0 prompt
            m0_input = {
                "idea_summary": idea_summary,
                "user_profile": user_profile,
                "signals": {
                    "demand": research_data.get("demand", {}).get("signal", "moderate"),
                    "trend": research_data.get("trends", {}).get("signal", "stable"),
                    "risk": self._summarize_risks(research_data.get("risks", []))
                },
                "evidence": evidence,
                "max_words": 500
            }
            
            # Generate analysis with LLM
            prompt = self._build_m0_prompt(m0_input)
            
            response = await self.llama.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.7
            )
            
            perf_log["api_calls"]["llm"] = perf_log.get("api_calls", {}).get("llm", 0) + 1
            
            # Parse LLM response
            analysis = self._parse_llm_response(response, research_data)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Analysis generation failed: {e}")
            raise
    
    def _build_m0_prompt(self, m0_input: Dict[str, Any]) -> str:
        """Build the M0 analysis prompt."""
        prompt = f"""
# M0 Feasibility Snapshot Generation

## Input Data
```json
{json.dumps(m0_input, indent=2)}
```

## Task
Generate a 1-page feasibility snapshot following this structure:

1. **Viability Score (0-100)**: Assess based on demand signals, competition, and execution complexity
2. **Lean Plan Tiles**: Extract problem, solution, audience, channels, differentiators, risks, assumptions
3. **Top 3 Competitors**: Name and positioning angle with evidence references
4. **Price Band**: Realistic pricing range based on evidence
5. **Next 5 Steps**: Actionable steps tailored to user profile

## Requirements
- Use ONLY provided evidence
- Stay under 500 words
- Include inline citations as [[ref_XXX - YYYY-MM-DD]]
- Be concise and actionable
- If evidence is thin, mark as "Assumption"

## Output Format
Provide a structured JSON response with all required fields.
"""
        return prompt
    
    def _parse_llm_response(
        self,
        response: str,
        research_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse and structure the LLM response."""
        try:
            # Try to parse as JSON first
            if response.strip().startswith("{"):
                analysis = json.loads(response)
            else:
                # Extract structured data from text response
                analysis = self._extract_structured_data(response)
            
            # Ensure all required fields
            analysis = self._ensure_complete_analysis(analysis, research_data)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Return minimal valid structure
            return self._get_fallback_analysis(research_data)
    
    def _extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from text response."""
        # Implementation for parsing text-based response
        # This is a fallback for when LLM doesn't return JSON
        return {
            "viability_score": 50,
            "score_rationale": "Analysis pending",
            "lean_tiles": {
                "problem": "To be determined",
                "solution": "To be determined",
                "audience": "To be determined",
                "channels": [],
                "differentiators": [],
                "risks": [],
                "assumptions": []
            },
            "competitors": [],
            "price_band": {"min": 0, "max": 0, "is_assumption": True},
            "next_steps": []
        }
    
    def _ensure_complete_analysis(
        self,
        analysis: Dict[str, Any],
        research_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ensure analysis has all required fields."""
        # Add competitors from research if missing
        if not analysis.get("competitors") and research_data.get("competitors"):
            analysis["competitors"] = research_data["competitors"][:3]
        
        # Add pricing from research if missing
        if not analysis.get("price_band") and research_data.get("pricing"):
            analysis["price_band"] = research_data["pricing"]
        
        # Ensure score is in valid range
        score = analysis.get("viability_score", 50)
        analysis["viability_score"] = max(0, min(100, score))
        
        # Calculate score range
        if score <= 20:
            analysis["score_range"] = ViabilityScoreRange.VERY_LOW.value
        elif score <= 40:
            analysis["score_range"] = ViabilityScoreRange.LOW.value
        elif score <= 60:
            analysis["score_range"] = ViabilityScoreRange.MODERATE.value
        elif score <= 80:
            analysis["score_range"] = ViabilityScoreRange.HIGH.value
        else:
            analysis["score_range"] = ViabilityScoreRange.VERY_HIGH.value
        
        return analysis
    
    async def _store_snapshot(
        self,
        user_id: str,
        project_id: Optional[str],
        idea_summary: str,
        user_profile: Dict[str, Any],
        analysis: Dict[str, Any],
        research_data: Dict[str, Any],
        generation_time_ms: int,
        research_time_ms: int,
        analysis_time_ms: int
    ) -> M0FeasibilitySnapshot:
        """Store the M0 snapshot in database."""
        try:
            # Extract idea name from summary or analysis
            idea_name = analysis.get("idea_name") or idea_summary.split(".")[0][:255]
            
            # Create snapshot record
            snapshot = M0FeasibilitySnapshot(
                user_id=UUID(user_id),
                project_id=UUID(project_id) if project_id else None,
                idea_name=idea_name,
                idea_summary=idea_summary,
                user_profile=user_profile,
                viability_score=analysis["viability_score"],
                score_range=analysis["score_range"],
                score_rationale=analysis.get("score_rationale", ""),
                lean_tiles=analysis.get("lean_tiles", {}),
                competitors=analysis.get("competitors", []),
                price_band_min=analysis.get("price_band", {}).get("min"),
                price_band_max=analysis.get("price_band", {}).get("max"),
                price_band_currency=analysis.get("price_band", {}).get("currency", "USD"),
                price_band_is_assumption=analysis.get("price_band", {}).get("is_assumption", True),
                next_steps=analysis.get("next_steps", []),
                evidence_data=self._collect_all_evidence(research_data),
                signals=research_data.get("signals", {}),
                generation_time_ms=generation_time_ms,
                word_count=len(idea_summary.split()),
                research_time_ms=research_time_ms,
                analysis_time_ms=analysis_time_ms,
                status=M0Status.COMPLETED.value
            )
            
            self.db.add(snapshot)
            await self.db.commit()
            await self.db.refresh(snapshot)
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to store snapshot: {e}")
            await self.db.rollback()
            raise
    
    async def _cache_snapshot(
        self,
        snapshot: M0FeasibilitySnapshot,
        research_data: Dict[str, Any]
    ) -> None:
        """Cache snapshot for fast retrieval."""
        try:
            # Generate cache key
            cache_key = f"m0:snapshot:{snapshot.id}"
            
            # Store in Redis with 1 hour TTL
            await self.redis.set_cache(
                cache_key,
                snapshot.to_dict(),
                ttl=3600
            )
            
            # Also cache by idea hash for deduplication
            idea_hash = self._generate_idea_hash(
                snapshot.idea_summary,
                snapshot.user_profile
            )
            
            await self.redis.set_cache(
                f"m0:idea_hash:{idea_hash}",
                str(snapshot.id),
                ttl=3600
            )
            
            # Store research cache for reuse
            research_cache = M0ResearchCache(
                snapshot_id=snapshot.id,
                idea_hash=idea_hash,
                research_query=snapshot.idea_summary,
                search_results=research_data.get("search_results", {}),
                processed_evidence=self._collect_all_evidence(research_data),
                competitor_data=research_data.get("competitors", []),
                market_signals=research_data.get("signals", {}),
                fetch_time_ms=snapshot.research_time_ms,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            
            self.db.add(research_cache)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to cache snapshot: {e}")
    
    async def _get_cached_snapshot(self, idea_hash: str) -> Optional[M0FeasibilitySnapshot]:
        """Retrieve cached snapshot if available."""
        try:
            # Check Redis cache first
            snapshot_id = await self.redis.get_cache(f"m0:idea_hash:{idea_hash}")
            
            if snapshot_id:
                # Get from database
                stmt = select(M0FeasibilitySnapshot).where(
                    M0FeasibilitySnapshot.id == UUID(snapshot_id)
                )
                result = await self.db.execute(stmt)
                snapshot = result.scalar_one_or_none()
                
                if snapshot and snapshot.cached_until > datetime.utcnow():
                    return snapshot
            
            # Check research cache in database
            stmt = select(M0ResearchCache).where(
                and_(
                    M0ResearchCache.idea_hash == idea_hash,
                    M0ResearchCache.expires_at > datetime.utcnow(),
                    M0ResearchCache.is_valid == True
                )
            )
            result = await self.db.execute(stmt)
            cache = result.scalar_one_or_none()
            
            if cache and cache.snapshot:
                # Update hit count
                cache.hit_count += 1
                await self.db.commit()
                
                return cache.snapshot
            
            return None
            
        except Exception as e:
            logger.error(f"Cache lookup failed: {e}")
            return None
    
    async def _log_performance(
        self,
        snapshot_id: UUID,
        total_time_ms: int,
        research_time_ms: int,
        analysis_time_ms: int,
        cache_lookup_time_ms: int,
        perf_log: Dict[str, Any]
    ) -> None:
        """Log performance metrics for analysis."""
        try:
            log_entry = M0PerformanceLog(
                snapshot_id=snapshot_id,
                total_time_ms=total_time_ms,
                research_time_ms=research_time_ms,
                analysis_time_ms=analysis_time_ms,
                cache_lookup_time_ms=cache_lookup_time_ms,
                api_calls=perf_log.get("api_calls", {}),
                cache_hits=perf_log.get("cache_hits", 0),
                cache_misses=perf_log.get("cache_misses", 0),
                used_cache=perf_log.get("used_cache", False),
                parallel_research=perf_log.get("parallel_research", True),
                batch_processing=perf_log.get("batch_processing", True),
                had_errors=perf_log.get("had_errors", False),
                error_details=perf_log.get("error_details", [])
            )
            
            self.db.add(log_entry)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log performance: {e}")
    
    def _generate_idea_hash(self, idea_summary: str, user_profile: Dict[str, Any]) -> str:
        """Generate a hash for idea deduplication."""
        # Normalize and combine inputs
        normalized = f"{idea_summary.lower().strip()}:{json.dumps(user_profile, sort_keys=True)}"
        
        # Generate SHA256 hash
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _analyze_demand_signal(self, citations: List[Any]) -> str:
        """Analyze demand signal from citations."""
        # Simple heuristic - can be enhanced with ML
        if len(citations) >= 4:
            return "high"
        elif len(citations) >= 2:
            return "moderate"
        else:
            return "low"
    
    def _analyze_trend_signal(self, citations: List[Any]) -> str:
        """Analyze trend signal from citations."""
        # Simple heuristic - can be enhanced with ML
        positive_keywords = ["growing", "increasing", "rising", "expanding", "boom"]
        negative_keywords = ["declining", "decreasing", "falling", "shrinking", "bust"]
        
        positive_count = 0
        negative_count = 0
        
        for citation in citations:
            snippet = citation.snippet.lower() if hasattr(citation, 'snippet') else ""
            
            for keyword in positive_keywords:
                if keyword in snippet:
                    positive_count += 1
                    break
            
            for keyword in negative_keywords:
                if keyword in snippet:
                    negative_count += 1
                    break
        
        if positive_count > negative_count:
            return "growing"
        elif negative_count > positive_count:
            return "declining"
        else:
            return "stable"
    
    def _extract_competitor_info(self, citation: Any) -> Optional[Dict[str, Any]]:
        """Extract competitor information from citation."""
        # Simple extraction - can be enhanced with NLP
        try:
            return {
                "name": citation.title.split("-")[0].strip() if hasattr(citation, 'title') else "Unknown",
                "angle": citation.snippet[:100] if hasattr(citation, 'snippet') else "",
                "evidence_refs": [f"ref_{citation.id[:3]}"] if hasattr(citation, 'id') else [],
                "dates": [citation.date] if hasattr(citation, 'date') else []
            }
        except:
            return None
    
    def _categorize_risks(self, citations: List[Any], user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Categorize and prioritize risks."""
        risks = []
        
        # Risk categories based on user profile
        if user_profile.get("experience") == "none":
            risks.append({"type": "execution", "description": "Limited industry experience"})
        
        if user_profile.get("budget_band") == "<5k":
            risks.append({"type": "financial", "description": "Limited initial capital"})
        
        # Extract risks from citations
        for citation in citations[:3]:
            if hasattr(citation, 'snippet'):
                risks.append({
                    "type": "market",
                    "description": citation.snippet[:100],
                    "source": citation.id if hasattr(citation, 'id') else None
                })
        
        return risks[:5]  # Top 5 risks
    
    def _extract_pricing_data(self, citations: List[Any]) -> Dict[str, Any]:
        """Extract pricing data from citations."""
        prices = []
        
        # Simple price extraction - can be enhanced with regex/NLP
        for citation in citations:
            if hasattr(citation, 'snippet'):
                # Look for price patterns
                import re
                price_pattern = r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)'
                matches = re.findall(price_pattern, citation.snippet)
                
                for match in matches:
                    try:
                        price = float(match.replace(',', ''))
                        prices.append(price)
                    except:
                        pass
        
        if prices:
            return {
                "min": min(prices),
                "max": max(prices),
                "is_assumption": False,
                "currency": "USD"
            }
        else:
            return {
                "min": None,
                "max": None,
                "is_assumption": True,
                "currency": "USD"
            }
    
    def _summarize_risks(self, risks: List[Dict[str, Any]]) -> str:
        """Summarize risks into a signal."""
        if not risks:
            return "low"
        elif len(risks) <= 2:
            return "moderate"
        else:
            return "high"
    
    def _collect_all_evidence(self, research_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect all evidence from research data."""
        evidence = []
        
        for source in ["demand", "trends"]:
            if source in research_data and "evidence" in research_data[source]:
                evidence.extend(research_data[source]["evidence"])
        
        return evidence
    
    def _get_fallback_analysis(self, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get fallback analysis when LLM fails."""
        return {
            "viability_score": 50,
            "score_range": ViabilityScoreRange.MODERATE.value,
            "score_rationale": "Analysis incomplete - manual review recommended",
            "lean_tiles": {
                "problem": "To be determined",
                "solution": "To be determined",
                "audience": "To be determined",
                "channels": [],
                "differentiators": [],
                "risks": [r.get("description", "") for r in research_data.get("risks", [])],
                "assumptions": ["Limited evidence available"]
            },
            "competitors": research_data.get("competitors", [])[:3],
            "price_band": research_data.get("pricing", {
                "min": None,
                "max": None,
                "is_assumption": True,
                "currency": "USD"
            }),
            "next_steps": [
                "Conduct deeper market research",
                "Validate assumptions with potential customers",
                "Analyze competitor offerings in detail",
                "Develop MVP specifications",
                "Create financial projections"
            ]
        }
    
    async def _store_failed_attempt(
        self,
        user_id: str,
        idea_summary: str,
        error: str,
        perf_log: Dict[str, Any],
        total_time_ms: int
    ) -> None:
        """Store failed M0 generation attempt for debugging."""
        try:
            snapshot = M0FeasibilitySnapshot(
                user_id=UUID(user_id),
                idea_name="Failed Analysis",
                idea_summary=idea_summary,
                user_profile={},
                viability_score=0,
                score_range=ViabilityScoreRange.VERY_LOW.value,
                score_rationale=f"Analysis failed: {error}",
                lean_tiles={},
                competitors=[],
                next_steps=[],
                evidence_data=[],
                signals={},
                generation_time_ms=total_time_ms,
                word_count=0,
                status=M0Status.FAILED.value
            )
            
            self.db.add(snapshot)
            await self.db.commit()
            
            # Log performance even for failed attempt
            await self._log_performance(
                snapshot.id,
                total_time_ms=total_time_ms,
                research_time_ms=0,
                analysis_time_ms=0,
                cache_lookup_time_ms=0,
                perf_log=perf_log
            )
            
        except Exception as e:
            logger.error(f"Failed to store failed attempt: {e}")
    
    def _update_metrics(self, total_time: int, perf_log: Dict[str, Any]) -> None:
        """Update service-level metrics."""
        self.perf_metrics["total_generations"] += 1
        
        # Update average time
        current_avg = self.perf_metrics["avg_time_ms"]
        total_gens = self.perf_metrics["total_generations"]
        self.perf_metrics["avg_time_ms"] = (
            (current_avg * (total_gens - 1) + total_time) / total_gens
        )
        
        # Update cache hit rate
        if perf_log.get("used_cache"):
            hits = self.perf_metrics.get("cache_hits", 0) + 1
            self.perf_metrics["cache_hits"] = hits
            self.perf_metrics["cache_hit_rate"] = hits / total_gens
        
        # Update success rate
        if not perf_log.get("had_errors"):
            successes = self.perf_metrics.get("successes", 0) + 1
            self.perf_metrics["successes"] = successes
            self.perf_metrics["success_rate"] = successes / total_gens
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            **self.perf_metrics,
            "target_time_ms": self.TARGET_TOTAL_TIME_MS,
            "within_target_rate": self._calculate_within_target_rate()
        }
    
    async def _calculate_within_target_rate(self) -> float:
        """Calculate percentage of generations within target time."""
        try:
            stmt = select(M0PerformanceLog).where(
                M0PerformanceLog.total_time_ms <= self.TARGET_TOTAL_TIME_MS
            )
            result = await self.db.execute(stmt)
            within_target = len(result.scalars().all())
            
            total = self.perf_metrics.get("total_generations", 1)
            return within_target / total if total > 0 else 0
            
        except Exception as e:
            logger.error(f"Failed to calculate target rate: {e}")
            return 0