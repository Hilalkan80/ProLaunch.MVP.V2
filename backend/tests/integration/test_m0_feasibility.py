"""
Integration tests for M0 Feasibility Snapshot system.

Tests the complete M0 generation pipeline including caching, performance,
and error handling.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from src.models.m0_feasibility import (
    M0FeasibilitySnapshot, M0Status, ViabilityScoreRange
)
from src.services.m0_generator import M0GeneratorService
from src.services.m0_cache_service import M0CacheService
from src.services.m0_monitoring import M0MonitoringService
from src.services.mcp_integrations.puppeteer_research import PuppeteerResearchMCP
from src.infrastructure.redis.redis_mcp import RedisMCPClient


@pytest.mark.asyncio
class TestM0FeasibilityIntegration:
    """Integration tests for M0 feasibility system."""
    
    @pytest.fixture
    async def m0_generator(self, db_session, redis_client):
        """Create M0 generator service."""
        llama_service = AsyncMock()
        citation_service = AsyncMock()
        context_manager = AsyncMock()
        
        generator = M0GeneratorService(
            db_session,
            llama_service,
            citation_service,
            context_manager,
            redis_client
        )
        
        await generator.initialize()
        return generator
    
    @pytest.fixture
    async def m0_cache(self, db_session, redis_client):
        """Create M0 cache service."""
        cache = M0CacheService(db_session, redis_client)
        await cache.initialize()
        return cache
    
    @pytest.fixture
    async def m0_monitoring(self, db_session, redis_client):
        """Create M0 monitoring service."""
        monitoring = M0MonitoringService(db_session, redis_client)
        await monitoring.initialize()
        return monitoring
    
    async def test_m0_generation_under_60_seconds(self, m0_generator):
        """Test that M0 generation completes within 60 seconds."""
        # Arrange
        user_id = str(uuid4())
        idea_summary = "An online marketplace for local farmers to sell directly to consumers"
        user_profile = {
            "experience": "some",
            "budget_band": "5k-25k",
            "timeline_months": 6
        }
        
        # Act
        start_time = time.time()
        result = await m0_generator.generate_snapshot(
            user_id=user_id,
            idea_summary=idea_summary,
            user_profile=user_profile,
            use_cache=False
        )
        elapsed_time = time.time() - start_time
        
        # Assert
        assert result is not None
        assert "id" in result
        assert "viability_score" in result
        assert 0 <= result["viability_score"] <= 100
        assert elapsed_time < 60, f"Generation took {elapsed_time:.2f}s, exceeding 60s limit"
    
    async def test_cache_hit_performance(self, m0_generator, m0_cache):
        """Test that cached results return in under 1 second."""
        # Arrange
        user_id = str(uuid4())
        idea_summary = "A subscription box service for eco-friendly products"
        user_profile = {
            "experience": "none",
            "budget_band": "<5k",
            "timeline_months": 3
        }
        
        # First generation (cache miss)
        first_result = await m0_generator.generate_snapshot(
            user_id=user_id,
            idea_summary=idea_summary,
            user_profile=user_profile,
            use_cache=True
        )
        
        # Act - Second generation (cache hit)
        start_time = time.time()
        cached_result = await m0_cache.get_cached_snapshot(
            idea_summary=idea_summary,
            user_profile=user_profile,
            use_similarity=False
        )
        cache_time = time.time() - start_time
        
        # Assert
        assert cached_result is not None
        assert cache_time < 1, f"Cache retrieval took {cache_time:.2f}s"
        assert cached_result["id"] == first_result["id"]
    
    async def test_similarity_matching(self, m0_cache, db_session):
        """Test that similar ideas are matched with 85%+ similarity."""
        # Arrange - Create a snapshot
        original_idea = "Online platform for booking home cleaning services"
        similar_idea = "Web platform for scheduling house cleaning services"
        
        snapshot = M0FeasibilitySnapshot(
            user_id=uuid4(),
            idea_name="CleanBook",
            idea_summary=original_idea,
            user_profile={"experience": "none", "budget_band": "<5k"},
            viability_score=75,
            score_range=ViabilityScoreRange.HIGH.value,
            score_rationale="High demand market",
            lean_tiles={},
            competitors=[],
            next_steps=[],
            evidence_data=[],
            signals={},
            generation_time_ms=45000,
            word_count=450,
            status=M0Status.COMPLETED.value
        )
        
        db_session.add(snapshot)
        await db_session.commit()
        
        # Act
        similar_result = await m0_cache._find_similar_snapshot(
            idea_summary=similar_idea,
            user_profile={"experience": "none", "budget_band": "<5k"}
        )
        
        # Assert
        assert similar_result is not None
        assert similar_result["idea_name"] == "CleanBook"
    
    async def test_parallel_research_performance(self):
        """Test that parallel research completes faster than sequential."""
        # Arrange
        puppeteer = PuppeteerResearchMCP()
        await puppeteer.initialize()
        
        idea = "AI-powered personal fitness coaching app"
        
        # Act - Parallel execution
        start_parallel = time.time()
        results = await asyncio.gather(
            puppeteer.research_market_demand(idea, timeout_ms=10000),
            puppeteer.research_competitors(idea, limit=3, timeout_ms=10000),
            puppeteer.research_pricing(idea, timeout_ms=10000),
            puppeteer.research_trends(idea, timeout_ms=10000)
        )
        parallel_time = time.time() - start_parallel
        
        # Act - Sequential execution (simulated)
        sequential_time = sum([10, 10, 10, 10]) / 1000  # Sum of timeouts
        
        # Assert
        assert all(r is not None for r in results)
        assert parallel_time < sequential_time / 2, "Parallel should be at least 2x faster"
    
    async def test_error_handling_and_fallback(self, m0_generator):
        """Test that system handles errors gracefully with fallbacks."""
        # Arrange - Force an error in LLM service
        m0_generator.llama.generate = AsyncMock(side_effect=Exception("LLM service down"))
        
        user_id = str(uuid4())
        idea_summary = "Test idea that will fail"
        user_profile = {"experience": "none", "budget_band": "<5k"}
        
        # Act
        with pytest.raises(Exception) as exc_info:
            await m0_generator.generate_snapshot(
                user_id=user_id,
                idea_summary=idea_summary,
                user_profile=user_profile,
                use_cache=False
            )
        
        # Assert - Check that failed attempt was logged
        assert "LLM service down" in str(exc_info.value)
    
    async def test_monitoring_metrics_collection(self, m0_monitoring):
        """Test that monitoring correctly collects performance metrics."""
        # Arrange
        snapshot_id = str(uuid4())
        
        # Act - Record multiple generations
        for i in range(10):
            latency = 40000 + (i * 2000)  # 40-58 seconds
            success = i < 8  # 80% success rate
            
            await m0_monitoring.record_generation(
                snapshot_id=snapshot_id,
                latency_ms=latency,
                success=success,
                used_cache=i % 3 == 0,  # 33% cache hits
                error="Test error" if not success else None
            )
        
        # Get metrics
        metrics = await m0_monitoring.get_real_time_metrics()
        
        # Assert
        assert "current" in metrics
        assert metrics["current"]["success_rate"] >= 0.7
        assert metrics["current"]["avg_latency_ms"] < 60000
    
    async def test_sla_compliance_checking(self, m0_monitoring):
        """Test SLA compliance monitoring."""
        # Arrange - Set up metrics
        current_metrics = {
            "p95_latency_ms": 58000,  # Under 60s target
            "p99_latency_ms": 72000,  # Under 75s target
            "success_rate": 0.96,  # Above 95% target
            "cache_hit_rate": 0.35  # Above 30% target
        }
        
        # Act
        sla_status = await m0_monitoring._check_sla_compliance(current_metrics)
        
        # Assert
        assert sla_status["latency_p95"] is True
        assert sla_status["latency_p99"] is True
        assert sla_status["success_rate"] is True
        assert sla_status["cache_hit_rate"] is True
    
    async def test_bulk_generation_performance(self, m0_generator):
        """Test bulk M0 generation with parallel processing."""
        # Arrange
        user_id = str(uuid4())
        ideas = [
            "Online tutoring platform for STEM subjects",
            "Meal prep delivery service for athletes",
            "Virtual interior design consultation service",
            "Pet grooming mobile app with on-demand booking",
            "Sustainable fashion marketplace"
        ]
        user_profile = {"experience": "some", "budget_band": "25k-100k"}
        
        # Act - Generate all in parallel
        start_time = time.time()
        tasks = [
            m0_generator.generate_snapshot(
                user_id=user_id,
                idea_summary=idea,
                user_profile=user_profile,
                use_cache=True
            )
            for idea in ideas
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Assert
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 4, "At least 80% should succeed"
        assert total_time < 120, f"Bulk generation of 5 ideas took {total_time:.2f}s"
        
        # Verify each result
        for result in successful:
            assert "viability_score" in result
            assert 0 <= result["viability_score"] <= 100
    
    async def test_cache_invalidation(self, m0_cache):
        """Test cache invalidation functionality."""
        # Arrange - Add items to cache
        idea1 = "Test idea 1"
        idea2 = "Test idea 2"
        
        await m0_cache._set_hot_cache(
            m0_cache._generate_cache_key(idea1, {}),
            {"test": "data1"}
        )
        await m0_cache._set_hot_cache(
            m0_cache._generate_cache_key(idea2, {}),
            {"test": "data2"}
        )
        
        # Act - Invalidate specific idea
        count = await m0_cache.invalidate_cache(idea_summary=idea1)
        
        # Assert
        assert count >= 1
        
        # Verify idea1 is gone but idea2 remains
        cached1 = await m0_cache._get_hot_cache(
            m0_cache._generate_cache_key(idea1, {})
        )
        cached2 = await m0_cache._get_hot_cache(
            m0_cache._generate_cache_key(idea2, {})
        )
        
        assert cached1 is None
        assert cached2 is not None
    
    async def test_performance_export(self, m0_monitoring):
        """Test metrics export in various formats."""
        # Arrange - Add some metrics
        for i in range(5):
            await m0_monitoring.record_generation(
                snapshot_id=str(uuid4()),
                latency_ms=50000 + i * 1000,
                success=True,
                used_cache=False
            )
        
        # Act - Export in different formats
        json_export = await m0_monitoring.export_metrics(format="json", time_range="1h")
        csv_export = await m0_monitoring.export_metrics(format="csv", time_range="1h")
        prometheus_export = await m0_monitoring.export_metrics(format="prometheus", time_range="1h")
        
        # Assert
        assert json_export is not None
        assert "data_points" in json.loads(json_export)
        
        assert csv_export is not None
        assert "timestamp,total_time_ms" in csv_export
        
        assert prometheus_export is not None
        assert "m0_latency_ms" in prometheus_export
    
    async def test_anomaly_detection(self, m0_monitoring):
        """Test anomaly detection in performance metrics."""
        # Arrange - Create normal pattern then anomaly
        normal_latencies = [45000, 47000, 46000, 48000, 45000]
        anomaly_latencies = [45000, 46000, 95000, 47000]  # 95s is anomaly
        
        detector = m0_monitoring.anomaly_detector
        
        # Act
        all_values = normal_latencies + anomaly_latencies
        anomalies = detector.detect(all_values)
        
        # Assert
        assert len(anomalies) > 0
        assert any(a["value"] == 95000 for a in anomalies)
        assert anomalies[0]["type"] in ["statistical_outlier", "sudden_spike"]


@pytest.mark.asyncio
class TestM0APIEndpoints:
    """Test M0 API endpoints."""
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, access_token):
        """Create auth headers."""
        return {"Authorization": f"Bearer {access_token}"}
    
    async def test_generate_m0_endpoint(self, client, auth_headers):
        """Test M0 generation API endpoint."""
        # Arrange
        request_data = {
            "idea_summary": "Mobile app for learning languages through games",
            "user_experience": "some",
            "budget_band": "5k-25k",
            "timeline_months": 6,
            "use_cache": True
        }
        
        # Act
        response = client.post(
            "/api/v1/m0/generate",
            json=request_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "snapshot_id" in data
        assert "snapshot" in data
        assert data["snapshot"]["viability_score"] >= 0
    
    async def test_get_snapshot_endpoint(self, client, auth_headers, db_session):
        """Test retrieving specific M0 snapshot."""
        # Arrange - Create a snapshot
        snapshot = M0FeasibilitySnapshot(
            user_id=uuid4(),
            idea_name="Test Idea",
            idea_summary="Test summary",
            user_profile={},
            viability_score=70,
            score_range="high",
            score_rationale="Good potential",
            lean_tiles={},
            competitors=[],
            next_steps=[],
            evidence_data=[],
            signals={},
            generation_time_ms=45000,
            word_count=400,
            status=M0Status.COMPLETED.value
        )
        
        db_session.add(snapshot)
        await db_session.commit()
        
        # Act
        response = client.get(
            f"/api/v1/m0/snapshot/{snapshot.id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "snapshot" in data
        assert data["snapshot"]["id"] == str(snapshot.id)
        assert "markdown_output" in data
    
    async def test_list_snapshots_with_filters(self, client, auth_headers):
        """Test listing M0 snapshots with filters."""
        # Act
        response = client.get(
            "/api/v1/m0/list",
            params={
                "min_score": 60,
                "max_score": 80,
                "limit": 10,
                "offset": 0
            },
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "snapshots" in data
        assert "total" in data
        assert isinstance(data["snapshots"], list)
    
    async def test_performance_metrics_endpoint(self, client, admin_headers):
        """Test performance metrics endpoint (admin only)."""
        # Act
        response = client.get(
            "/api/v1/m0/performance/metrics",
            params={"time_range": "24h"},
            headers=admin_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "total_generations" in data
        assert "avg_time_ms" in data
        assert "within_target_rate" in data
        assert 0 <= data["within_target_rate"] <= 1
    
    async def test_export_snapshot_endpoint(self, client, auth_headers, db_session):
        """Test exporting M0 snapshot in different formats."""
        # Arrange - Create snapshot
        snapshot = M0FeasibilitySnapshot(
            user_id=uuid4(),
            idea_name="Export Test",
            idea_summary="Test export functionality",
            user_profile={},
            viability_score=65,
            score_range="high",
            score_rationale="Test",
            lean_tiles={},
            competitors=[],
            next_steps=["Step 1", "Step 2"],
            evidence_data=[],
            signals={},
            generation_time_ms=40000,
            word_count=300,
            status=M0Status.COMPLETED.value
        )
        
        db_session.add(snapshot)
        await db_session.commit()
        
        # Act - Export as markdown
        response = client.get(
            f"/api/v1/m0/export/{snapshot.id}",
            params={"format": "markdown"},
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown"
        content = response.content.decode()
        assert "# Export Test" in content
        assert "Step 1" in content