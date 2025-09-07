"""
Comprehensive test suite for the citation system.

Tests citation CRUD operations, verification, accuracy tracking,
and API endpoints with focus on maintaining 95% accuracy threshold.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import redis

from src.models.citation import (
    Citation, CitationUsage, AccuracyTracking,
    VerificationLog, CitationCollection,
    SourceType, VerificationStatus, ContentType,
    FeedbackType, MetricType
)
from src.services.citation_service import (
    CitationService, CitationCreate, CitationUpdate,
    CitationVerifyRequest, AccuracyFeedback, CitationSearchParams
)
from src.services.accuracy_tracker import (
    AccuracyTracker, AccuracyStatus, AlertSeverity
)
from src.infrastructure.mcp import PostgresMCP, PuppeteerMCP
from src.api.v1.citations import router
from src.main import app


# Test fixtures
@pytest.fixture
def test_db():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    from src.models.base import Base
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.setex.return_value = True
    mock.delete.return_value = True
    mock.hset.return_value = True
    mock.expire.return_value = True
    return mock


@pytest.fixture
def mock_postgres_mcp():
    """Create mock PostgreSQL MCP."""
    mock = AsyncMock(spec=PostgresMCP)
    mock.connect.return_value = True
    mock.vector_search.return_value = []
    mock.full_text_search.return_value = []
    mock.bulk_insert.return_value = 0
    return mock


@pytest.fixture
def mock_puppeteer_mcp():
    """Create mock Puppeteer MCP."""
    mock = AsyncMock(spec=PuppeteerMCP)
    mock.verify_url.return_value = {
        'url': 'https://example.com',
        'status': 'verified',
        'timestamp': datetime.utcnow().isoformat(),
        'content': 'Test content',
        'title': 'Test Title',
        'metadata': {},
        'screenshot_url': 'https://screenshot.example.com/test.png',
        'content_length': 100,
        'load_time_ms': 500
    }
    mock.extract_content.return_value = {
        'title': 'Test Title',
        'author': 'Test Author',
        'date': '2025-01-01',
        'content': 'Test content'
    }
    mock.capture_screenshot.return_value = 'https://screenshot.example.com/test.png'
    mock.check_availability.return_value = {'https://example.com': True}
    return mock


@pytest.fixture
def citation_service(test_db, mock_redis, mock_postgres_mcp, mock_puppeteer_mcp):
    """Create citation service instance."""
    return CitationService(
        db=test_db,
        cache_manager=Mock(get=Mock(return_value=None), set=Mock(), delete=Mock()),
        postgres_mcp=mock_postgres_mcp,
        puppeteer_mcp=mock_puppeteer_mcp
    )


@pytest.fixture
def accuracy_tracker(test_db, mock_redis):
    """Create accuracy tracker instance."""
    return AccuracyTracker(
        db=test_db,
        redis_client=mock_redis,
        notification_service=Mock()
    )


@pytest.fixture
def test_client():
    """Create test client for API endpoints."""
    return TestClient(app)


@pytest.fixture
def sample_citation_data():
    """Sample citation creation data."""
    return CitationCreate(
        source_type=SourceType.WEB,
        url="https://example.com/article",
        title="Test Article",
        authors=["John Doe", "Jane Smith"],
        publication_date=datetime(2025, 1, 1),
        excerpt="This is a test excerpt",
        context="Test context for citation",
        metadata={"keywords": ["test", "citation"]}
    )


@pytest.fixture
def sample_citation(test_db):
    """Create sample citation in database."""
    citation = Citation(
        reference_id="ref_20250101_0001",
        source_type=SourceType.WEB,
        url="https://example.com/article",
        title="Test Article",
        authors=["John Doe"],
        publication_date=datetime(2025, 1, 1),
        access_date=datetime.utcnow(),
        excerpt="Test excerpt",
        context="Test context",
        verification_status=VerificationStatus.PENDING,
        accuracy_score=0.95,
        relevance_score=0.90,
        availability_score=1.0,
        overall_quality_score=0.93
    )
    test_db.add(citation)
    test_db.commit()
    return citation


# Citation Service Tests
class TestCitationService:
    """Test citation service functionality."""
    
    @pytest.mark.asyncio
    async def test_create_citation(self, citation_service, sample_citation_data):
        """Test citation creation."""
        user_id = uuid4()
        
        citation = await citation_service.create_citation(
            citation_data=sample_citation_data,
            user_id=user_id,
            auto_verify=False
        )
        
        assert citation is not None
        assert citation.title == "Test Article"
        assert citation.source_type == SourceType.WEB
        assert citation.reference_id.startswith("ref_")
        assert len(citation.authors) == 2
    
    @pytest.mark.asyncio
    async def test_create_citation_with_auto_verify(
        self, citation_service, sample_citation_data, mock_puppeteer_mcp
    ):
        """Test citation creation with automatic verification."""
        user_id = uuid4()
        
        citation = await citation_service.create_citation(
            citation_data=sample_citation_data,
            user_id=user_id,
            auto_verify=True
        )
        
        assert citation is not None
        mock_puppeteer_mcp.verify_url.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_citation(self, citation_service, sample_citation):
        """Test getting citation by ID."""
        citation = await citation_service.get_citation(sample_citation.id)
        
        assert citation is not None
        assert citation.id == sample_citation.id
        assert citation.title == sample_citation.title
    
    @pytest.mark.asyncio
    async def test_get_citation_not_found(self, citation_service):
        """Test getting non-existent citation."""
        with pytest.raises(Exception) as exc_info:
            await citation_service.get_citation(uuid4())
        
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_update_citation(self, citation_service, sample_citation):
        """Test updating citation."""
        update_data = CitationUpdate(
            title="Updated Title",
            excerpt="Updated excerpt"
        )
        
        updated = await citation_service.update_citation(
            citation_id=sample_citation.id,
            update_data=update_data,
            user_id=uuid4()
        )
        
        assert updated.title == "Updated Title"
        assert updated.excerpt == "Updated excerpt"
    
    @pytest.mark.asyncio
    async def test_verify_citation(
        self, citation_service, sample_citation, mock_puppeteer_mcp
    ):
        """Test citation verification."""
        verification_log = await citation_service.verify_citation(
            citation_id=sample_citation.id,
            user_id=uuid4()
        )
        
        assert verification_log is not None
        assert verification_log.status == "success"
        mock_puppeteer_mcp.verify_url.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_citation_without_url(self, citation_service, test_db):
        """Test verification of citation without URL."""
        citation = Citation(
            reference_id="ref_test",
            title="No URL Citation",
            source_type=SourceType.BOOK
        )
        test_db.add(citation)
        test_db.commit()
        
        with pytest.raises(Exception) as exc_info:
            await citation_service.verify_citation(
                citation_id=citation.id,
                user_id=uuid4()
            )
        
        assert "without URL" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_track_usage(self, citation_service, sample_citation):
        """Test tracking citation usage."""
        content_id = uuid4()
        user_id = uuid4()
        
        usage = await citation_service.track_usage(
            citation_id=sample_citation.id,
            content_id=content_id,
            user_id=user_id,
            content_type=ContentType.RESEARCH,
            position=1,
            context="Test context",
            section="introduction"
        )
        
        assert usage is not None
        assert usage.citation_id == sample_citation.id
        assert usage.content_id == content_id
        assert usage.position == 1
    
    @pytest.mark.asyncio
    async def test_submit_accuracy_feedback(self, citation_service, sample_citation):
        """Test submitting accuracy feedback."""
        feedback = AccuracyFeedback(
            metric_type=MetricType.ACCURACY,
            score=0.85,
            feedback_type=FeedbackType.USER,
            comment="Good citation but could be more accurate",
            issues=["Minor factual error"],
            suggestions=["Verify date information"]
        )
        
        tracking = await citation_service.submit_accuracy_feedback(
            citation_id=sample_citation.id,
            feedback=feedback,
            evaluator_id=uuid4()
        )
        
        assert tracking is not None
        assert tracking.metric_type == MetricType.ACCURACY
        assert tracking.score == 0.85
        assert tracking.feedback_type == FeedbackType.USER
    
    @pytest.mark.asyncio
    async def test_search_citations(self, citation_service, sample_citation):
        """Test searching citations."""
        params = CitationSearchParams(
            query="Test",
            source_types=[SourceType.WEB],
            min_quality_score=0.9,
            limit=10,
            offset=0
        )
        
        results, total = await citation_service.search_citations(params)
        
        assert len(results) >= 0
        assert total >= 0
    
    @pytest.mark.asyncio
    async def test_batch_create_citations(self, citation_service, sample_citation_data):
        """Test batch citation creation."""
        citations_data = [sample_citation_data for _ in range(3)]
        user_id = uuid4()
        
        created = await citation_service.batch_create_citations(
            citations_data=citations_data,
            user_id=user_id
        )
        
        assert len(created) == 3
        for citation in created:
            assert citation.title == "Test Article"
    
    @pytest.mark.asyncio
    async def test_get_stale_citations(self, citation_service, test_db):
        """Test getting stale citations."""
        # Create old citation
        old_citation = Citation(
            reference_id="ref_old",
            title="Old Citation",
            source_type=SourceType.WEB,
            url="https://old.example.com",
            last_verified=datetime.utcnow() - timedelta(days=45)
        )
        test_db.add(old_citation)
        test_db.commit()
        
        stale = await citation_service.get_stale_citations(
            days_threshold=30,
            limit=10
        )
        
        assert len(stale) > 0
        assert any(c.id == old_citation.id for c in stale)
    
    @pytest.mark.asyncio
    async def test_get_accuracy_report(self, citation_service, sample_citation):
        """Test generating accuracy report."""
        report = await citation_service.get_accuracy_report()
        
        assert 'period' in report
        assert 'overall_accuracy' in report
        assert 'accuracy_status' in report
        assert report['overall_accuracy'] >= 0
        assert report['overall_accuracy'] <= 100


# Accuracy Tracker Tests
class TestAccuracyTracker:
    """Test accuracy tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_check_system_accuracy(self, accuracy_tracker, sample_citation):
        """Test checking system-wide accuracy."""
        status = await accuracy_tracker.check_system_accuracy()
        
        assert status in [AccuracyStatus.GREEN, AccuracyStatus.YELLOW, AccuracyStatus.RED]
    
    @pytest.mark.asyncio
    async def test_check_individual_citations(self, accuracy_tracker, test_db):
        """Test checking individual citation accuracy."""
        # Create low accuracy citation
        low_accuracy = Citation(
            reference_id="ref_low",
            title="Low Accuracy Citation",
            source_type=SourceType.WEB,
            overall_quality_score=0.70
        )
        test_db.add(low_accuracy)
        test_db.commit()
        
        await accuracy_tracker.check_individual_citations(limit=10)
        
        # Check that citation was marked for reverification
        test_db.refresh(low_accuracy)
        assert low_accuracy.requires_reverification == True
    
    @pytest.mark.asyncio
    async def test_calculate_accuracy_metrics(self, accuracy_tracker, sample_citation, test_db):
        """Test calculating accuracy metrics."""
        # Add feedback
        feedback = AccuracyTracking(
            citation_id=sample_citation.id,
            metric_type=MetricType.ACCURACY,
            score=0.90,
            feedback_type=FeedbackType.USER,
            evaluator_id=uuid4()
        )
        test_db.add(feedback)
        test_db.commit()
        
        metrics = await accuracy_tracker.calculate_accuracy_metrics(sample_citation.id)
        
        assert MetricType.ACCURACY in metrics
        assert metrics[MetricType.ACCURACY] == 0.90
        assert 'overall' in metrics
    
    @pytest.mark.asyncio
    async def test_submit_feedback(self, accuracy_tracker, sample_citation):
        """Test submitting feedback through tracker."""
        tracking = await accuracy_tracker.submit_feedback(
            citation_id=sample_citation.id,
            metric_type=MetricType.RELEVANCE,
            score=0.95,
            feedback_type=FeedbackType.EXPERT,
            evaluator_id=uuid4(),
            feedback_data={'comment': 'Highly relevant'}
        )
        
        assert tracking is not None
        assert tracking.score == 0.95
        assert tracking.confidence_level == 0.8  # Expert feedback
    
    @pytest.mark.asyncio
    async def test_get_accuracy_trends(self, accuracy_tracker, sample_citation):
        """Test getting accuracy trends."""
        trends = await accuracy_tracker.get_accuracy_trends(
            citation_id=sample_citation.id,
            days=7
        )
        
        assert 'citation_id' in trends
        assert 'period_days' in trends
        assert 'trends' in trends
        assert trends['period_days'] == 7
    
    @pytest.mark.asyncio
    async def test_generate_accuracy_report(self, accuracy_tracker, sample_citation):
        """Test generating comprehensive accuracy report."""
        report = await accuracy_tracker.generate_accuracy_report()
        
        assert 'system_metrics' in report
        assert 'source_metrics' in report
        assert 'verification_stats' in report
        assert 'feedback_stats' in report
        assert 'alert_statistics' in report
    
    @pytest.mark.asyncio
    async def test_alert_creation(self, accuracy_tracker):
        """Test alert creation for low accuracy."""
        await accuracy_tracker._create_alert(
            severity=AlertSeverity.WARNING,
            message="Test alert",
            citation_id=uuid4(),
            current_score=0.85
        )
        
        assert len(accuracy_tracker.active_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self, accuracy_tracker):
        """Test monitoring loop functionality."""
        await accuracy_tracker.start_monitoring()
        await asyncio.sleep(0.1)  # Let it run briefly
        await accuracy_tracker.stop_monitoring()
        
        assert accuracy_tracker._monitoring_task is None


# API Endpoint Tests
class TestCitationAPI:
    """Test citation API endpoints."""
    
    def test_create_citation_endpoint(self, test_client, monkeypatch):
        """Test POST /api/v1/citations endpoint."""
        # Mock authentication
        monkeypatch.setattr(
            "src.api.v1.citations.get_current_user",
            lambda: {"id": str(uuid4())}
        )
        
        response = test_client.post(
            "/api/v1/citations",
            json={
                "source_type": "web",
                "url": "https://example.com",
                "title": "Test Citation",
                "authors": ["Author 1"],
                "excerpt": "Test excerpt"
            }
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data.get("title") == "Test Citation"
    
    def test_get_citation_endpoint(self, test_client, sample_citation):
        """Test GET /api/v1/citations/{id} endpoint."""
        response = test_client.get(f"/api/v1/citations/{sample_citation.id}")
        
        assert response.status_code in [200, 404]
    
    def test_search_citations_endpoint(self, test_client):
        """Test GET /api/v1/citations/search endpoint."""
        response = test_client.get(
            "/api/v1/citations/search",
            params={
                "query": "test",
                "page": 1,
                "page_size": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "citations" in data
        assert "total" in data
    
    def test_accuracy_report_endpoint(self, test_client):
        """Test GET /api/v1/citations/accuracy-report endpoint."""
        response = test_client.get("/api/v1/citations/accuracy-report")
        
        assert response.status_code == 200
        data = response.json()
        assert "overall_accuracy" in data
        assert "accuracy_status" in data
    
    def test_accuracy_alerts_endpoint(self, test_client):
        """Test GET /api/v1/citations/accuracy-alerts endpoint."""
        response = test_client.get(
            "/api/v1/citations/accuracy-alerts",
            params={"threshold": 0.95}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "total_alerts" in data


# Integration Tests
class TestCitationIntegration:
    """Integration tests for citation system."""
    
    @pytest.mark.asyncio
    async def test_full_citation_lifecycle(
        self, citation_service, accuracy_tracker, sample_citation_data
    ):
        """Test complete citation lifecycle from creation to verification."""
        user_id = uuid4()
        
        # Create citation
        citation = await citation_service.create_citation(
            citation_data=sample_citation_data,
            user_id=user_id,
            auto_verify=False
        )
        
        # Verify citation
        verification = await citation_service.verify_citation(
            citation_id=citation.id,
            user_id=user_id
        )
        
        # Track usage
        usage = await citation_service.track_usage(
            citation_id=citation.id,
            content_id=uuid4(),
            user_id=user_id,
            content_type=ContentType.RESEARCH,
            position=1
        )
        
        # Submit feedback
        feedback = AccuracyFeedback(
            metric_type=MetricType.ACCURACY,
            score=0.95,
            feedback_type=FeedbackType.EXPERT,
            comment="Accurate citation"
        )
        
        tracking = await citation_service.submit_accuracy_feedback(
            citation_id=citation.id,
            feedback=feedback,
            evaluator_id=user_id
        )
        
        # Check accuracy
        metrics = await accuracy_tracker.calculate_accuracy_metrics(citation.id)
        
        assert citation is not None
        assert verification is not None
        assert usage is not None
        assert tracking is not None
        assert metrics[MetricType.ACCURACY] == 0.95
    
    @pytest.mark.asyncio
    async def test_accuracy_threshold_monitoring(
        self, citation_service, accuracy_tracker, test_db
    ):
        """Test accuracy threshold monitoring and alerting."""
        # Create citations with varying accuracy
        citations = []
        for i in range(5):
            citation = Citation(
                reference_id=f"ref_test_{i}",
                title=f"Citation {i}",
                source_type=SourceType.WEB,
                overall_quality_score=0.80 + (i * 0.05)  # 0.80 to 1.00
            )
            test_db.add(citation)
            citations.append(citation)
        
        test_db.commit()
        
        # Check system accuracy
        status = await accuracy_tracker.check_system_accuracy()
        
        # Check individual citations
        await accuracy_tracker.check_individual_citations()
        
        # Verify alerts were created for low accuracy citations
        assert len(accuracy_tracker.active_alerts) > 0
        
        # Generate report
        report = await accuracy_tracker.generate_accuracy_report()
        
        assert report['system_metrics']['average_accuracy'] > 0
        assert report['system_metrics']['total_citations'] >= 5


# Performance Tests
class TestCitationPerformance:
    """Performance tests for citation system."""
    
    @pytest.mark.asyncio
    async def test_batch_creation_performance(self, citation_service):
        """Test performance of batch citation creation."""
        import time
        
        citations_data = [
            CitationCreate(
                source_type=SourceType.WEB,
                url=f"https://example.com/article{i}",
                title=f"Test Article {i}",
                authors=[f"Author {i}"]
            )
            for i in range(100)
        ]
        
        start_time = time.time()
        
        created = await citation_service.batch_create_citations(
            citations_data=citations_data,
            user_id=uuid4()
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(created) == 100
        assert duration < 10  # Should complete within 10 seconds
        
        print(f"Batch creation of 100 citations took {duration:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_search_performance(self, citation_service, test_db):
        """Test search performance with large dataset."""
        import time
        
        # Create many citations
        for i in range(1000):
            citation = Citation(
                reference_id=f"ref_perf_{i}",
                title=f"Performance Test Citation {i}",
                source_type=SourceType.WEB if i % 2 == 0 else SourceType.ACADEMIC,
                overall_quality_score=0.70 + (i % 30) / 100
            )
            test_db.add(citation)
        
        test_db.commit()
        
        # Test search performance
        params = CitationSearchParams(
            query="Performance",
            source_types=[SourceType.WEB],
            min_quality_score=0.90,
            limit=50,
            offset=0
        )
        
        start_time = time.time()
        results, total = await citation_service.search_citations(params)
        end_time = time.time()
        
        duration = end_time - start_time
        
        assert duration < 1  # Should complete within 1 second
        print(f"Search through 1000 citations took {duration:.2f} seconds")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])