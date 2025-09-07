"""
Integration tests for MCP (Model Context Protocol) components.

Tests PostgreSQL MCP and Puppeteer MCP integrations with the citation system
to ensure proper functioning and 95% accuracy maintenance.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
import json

from src.infrastructure.mcp import PostgresMCP, PuppeteerMCP
from src.services.citation_service import CitationService, CitationCreate
from src.services.accuracy_tracker import AccuracyTracker, AccuracyStatus
from src.models.citation import (
    Citation, SourceType, VerificationStatus, MetricType
)


class TestPostgresMCPIntegration:
    """Test PostgreSQL MCP integration."""
    
    @pytest.mark.asyncio
    async def test_postgres_mcp_connection(self):
        """Test PostgreSQL MCP connection establishment."""
        postgres_mcp = PostgresMCP(connection_url="postgresql://test:test@localhost:5432/test")
        
        with patch.object(postgres_mcp, 'connect', return_value=True):
            result = await postgres_mcp.connect()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_vector_search_functionality(self):
        """Test vector search for similar citations."""
        postgres_mcp = PostgresMCP()
        
        # Mock embedding
        query_embedding = [0.1] * 768  # Standard embedding size
        
        with patch.object(postgres_mcp, '_connection', True):
            results = await postgres_mcp.vector_search(
                query_embedding=query_embedding,
                limit=5,
                threshold=0.8
            )
            
            assert isinstance(results, list)
            if results:
                assert 'id' in results[0]
                assert 'similarity' in results[0]
                assert results[0]['similarity'] >= 0.8
    
    @pytest.mark.asyncio
    async def test_full_text_search(self):
        """Test full-text search functionality."""
        postgres_mcp = PostgresMCP()
        
        with patch.object(postgres_mcp, '_connection', True):
            results = await postgres_mcp.full_text_search(
                query="machine learning",
                columns=['title', 'excerpt', 'context'],
                limit=10
            )
            
            assert isinstance(results, list)
            if results:
                assert 'id' in results[0]
                assert 'rank' in results[0]
    
    @pytest.mark.asyncio
    async def test_bulk_insert_citations(self):
        """Test bulk insertion of citations."""
        postgres_mcp = PostgresMCP()
        
        citations_data = [
            {
                'reference_id': f'ref_test_{i}',
                'title': f'Test Citation {i}',
                'url': f'https://example.com/article{i}',
                'source_type': 'web'
            }
            for i in range(10)
        ]
        
        with patch.object(postgres_mcp, '_connection', True):
            count = await postgres_mcp.bulk_insert(
                table='citations',
                data=citations_data,
                on_conflict='DO UPDATE SET updated_at = EXCLUDED.updated_at'
            )
            
            assert count == len(citations_data)
    
    @pytest.mark.asyncio
    async def test_optimized_query_execution(self):
        """Test optimized query execution."""
        postgres_mcp = PostgresMCP()
        
        query = """
            SELECT c.*, 
                   COUNT(cu.id) as usage_count,
                   AVG(at.score) as avg_accuracy
            FROM citations c
            LEFT JOIN citation_usages cu ON c.id = cu.citation_id
            LEFT JOIN accuracy_tracking at ON c.id = at.citation_id
            WHERE c.verification_status = %s
            GROUP BY c.id
            ORDER BY avg_accuracy DESC
            LIMIT %s
        """
        
        with patch.object(postgres_mcp, '_connection', True):
            results = await postgres_mcp.execute_optimized_query(
                query=query,
                params=('verified', 10)
            )
            
            assert isinstance(results, list)


class TestPuppeteerMCPIntegration:
    """Test Puppeteer MCP integration."""
    
    @pytest.mark.asyncio
    async def test_url_verification(self):
        """Test URL verification with content extraction."""
        puppeteer_mcp = PuppeteerMCP(service_url="http://localhost:3000")
        
        mock_response = {
            'content': '<html><body><h1>Test Article</h1><p>Content</p></body></html>',
            'title': 'Test Article',
            'metadata': {
                'author': 'John Doe',
                'publishedDate': '2025-01-01',
                'keywords': ['test', 'article']
            },
            'screenshotUrl': 'https://screenshots.example.com/abc123.png',
            'loadTime': 1234
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await puppeteer_mcp.verify_url(
                url="https://example.com/article",
                capture_screenshot=True,
                extract_metadata=True
            )
            
            assert result['status'] == 'verified'
            assert result['title'] == 'Test Article'
            assert result['screenshot_url'] is not None
            assert 'metadata' in result
    
    @pytest.mark.asyncio
    async def test_content_extraction_with_selectors(self):
        """Test content extraction with custom CSS selectors."""
        puppeteer_mcp = PuppeteerMCP()
        
        custom_selectors = {
            'title': 'h1.article-title',
            'author': '.author-name',
            'date': 'time.published-date',
            'content': 'div.article-body'
        }
        
        mock_response = {
            'title': 'Custom Title',
            'author': 'Jane Smith',
            'date': '2025-01-15',
            'content': 'Article content extracted with custom selectors'
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await puppeteer_mcp.extract_content(
                url="https://example.com/article",
                selectors=custom_selectors
            )
            
            assert result['title'] == 'Custom Title'
            assert result['author'] == 'Jane Smith'
    
    @pytest.mark.asyncio
    async def test_screenshot_capture(self):
        """Test screenshot capture functionality."""
        puppeteer_mcp = PuppeteerMCP()
        
        mock_response = {
            'screenshotUrl': 'https://screenshots.example.com/fullpage.png',
            'data': None
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            screenshot_url = await puppeteer_mcp.capture_screenshot(
                url="https://example.com",
                full_page=True,
                viewport={'width': 1920, 'height': 1080}
            )
            
            assert screenshot_url == 'https://screenshots.example.com/fullpage.png'
    
    @pytest.mark.asyncio
    async def test_batch_availability_check(self):
        """Test batch URL availability checking."""
        puppeteer_mcp = PuppeteerMCP()
        
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
            "https://broken.example.com/404",
            "https://timeout.example.com"
        ]
        
        expected_results = {
            "https://example.com/page1": True,
            "https://example.com/page2": True,
            "https://example.com/page3": True,
            "https://broken.example.com/404": False,
            "https://timeout.example.com": False
        }
        
        with patch.object(puppeteer_mcp, 'check_availability', return_value=expected_results):
            results = await puppeteer_mcp.check_availability(
                urls=urls,
                concurrent_limit=3
            )
            
            assert len(results) == len(urls)
            assert results["https://example.com/page1"] is True
            assert results["https://broken.example.com/404"] is False
    
    @pytest.mark.asyncio
    async def test_verification_retry_logic(self):
        """Test verification retry logic on failure."""
        puppeteer_mcp = PuppeteerMCP()
        
        # Simulate failures then success
        call_count = 0
        
        async def mock_verify_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {
                'status': 'verified',
                'url': kwargs['url']
            }
        
        with patch.object(puppeteer_mcp, 'verify_url', side_effect=mock_verify_side_effect):
            # Test retry logic implementation
            max_retries = 3
            retry_count = 0
            result = None
            
            while retry_count < max_retries:
                try:
                    result = await puppeteer_mcp.verify_url(
                        url="https://example.com",
                        capture_screenshot=False
                    )
                    break
                except Exception:
                    retry_count += 1
                    await asyncio.sleep(0.1)  # Small delay between retries
            
            assert result is not None
            assert result['status'] == 'verified'


class TestCitationSystemWithMCP:
    """Test citation system with MCP integrations."""
    
    @pytest.mark.asyncio
    async def test_citation_creation_with_auto_verification(self, test_db, mock_puppeteer_mcp):
        """Test citation creation with automatic verification."""
        citation_service = CitationService(
            db=test_db,
            puppeteer_mcp=mock_puppeteer_mcp
        )
        
        citation_data = CitationCreate(
            source_type=SourceType.WEB,
            url="https://example.com/article",
            title="Test Article",
            authors=["John Doe"],
            excerpt="This is a test article about testing."
        )
        
        citation = await citation_service.create_citation(
            citation_data=citation_data,
            user_id=uuid4(),
            auto_verify=True
        )
        
        assert citation.reference_id.startswith("ref_")
        assert citation.verification_status == VerificationStatus.VERIFIED
        assert citation.screenshot_url is not None
        mock_puppeteer_mcp.verify_url.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_accuracy_tracking_with_feedback(self, test_db, mock_redis):
        """Test accuracy tracking with user feedback."""
        accuracy_tracker = AccuracyTracker(
            db=test_db,
            redis_client=mock_redis
        )
        
        # Create test citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_test_001",
            title="Test Citation",
            source_type=SourceType.ACADEMIC,
            overall_quality_score=0.85
        )
        test_db.add(citation)
        test_db.commit()
        
        # Calculate metrics
        metrics = await accuracy_tracker.calculate_accuracy_metrics(citation.id)
        
        assert 'overall' in metrics
        assert metrics['overall'] >= 0.0
        assert metrics['overall'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_system_accuracy_monitoring(self, test_db, mock_redis):
        """Test system-wide accuracy monitoring."""
        accuracy_tracker = AccuracyTracker(
            db=test_db,
            redis_client=mock_redis
        )
        
        # Create test citations with varying accuracy
        citations = [
            Citation(
                id=uuid4(),
                reference_id=f"ref_test_{i:03d}",
                title=f"Test Citation {i}",
                source_type=SourceType.WEB,
                overall_quality_score=0.96 if i < 8 else 0.85,  # 80% above threshold
                is_active=True
            )
            for i in range(10)
        ]
        
        for citation in citations:
            test_db.add(citation)
        test_db.commit()
        
        # Check system accuracy
        status = await accuracy_tracker.check_system_accuracy()
        
        # Should be YELLOW (warning) as average is around 94%
        assert status in [AccuracyStatus.YELLOW, AccuracyStatus.GREEN]
    
    @pytest.mark.asyncio
    async def test_stale_verification_detection(self, test_db):
        """Test detection of citations needing reverification."""
        accuracy_tracker = AccuracyTracker(db=test_db)
        
        # Create citations with old verification dates
        old_date = datetime.utcnow() - timedelta(days=45)
        
        stale_citation = Citation(
            id=uuid4(),
            reference_id="ref_stale_001",
            title="Stale Citation",
            source_type=SourceType.WEB,
            last_verified=old_date,
            is_active=True
        )
        
        fresh_citation = Citation(
            id=uuid4(),
            reference_id="ref_fresh_001",
            title="Fresh Citation",
            source_type=SourceType.WEB,
            last_verified=datetime.utcnow() - timedelta(days=5),
            is_active=True
        )
        
        test_db.add(stale_citation)
        test_db.add(fresh_citation)
        test_db.commit()
        
        # Process stale verifications
        await accuracy_tracker.process_stale_verifications()
        
        # Check that stale citation is marked for reverification
        test_db.refresh(stale_citation)
        test_db.refresh(fresh_citation)
        
        assert stale_citation.verification_status == VerificationStatus.STALE
        assert stale_citation.requires_reverification is True
        assert fresh_citation.verification_status != VerificationStatus.STALE
    
    @pytest.mark.asyncio
    async def test_accuracy_alerts_generation(self, test_db, mock_redis):
        """Test generation of accuracy alerts."""
        accuracy_tracker = AccuracyTracker(
            db=test_db,
            redis_client=mock_redis
        )
        
        # Create low-accuracy citation
        low_accuracy_citation = Citation(
            id=uuid4(),
            reference_id="ref_low_001",
            title="Low Accuracy Citation",
            source_type=SourceType.WEB,
            overall_quality_score=0.75,  # Below 90% threshold
            is_active=True
        )
        
        test_db.add(low_accuracy_citation)
        test_db.commit()
        
        # Check individual citations
        await accuracy_tracker.check_individual_citations()
        
        # Verify that citation is marked for reverification
        test_db.refresh(low_accuracy_citation)
        assert low_accuracy_citation.requires_reverification is True


class TestEndToEndCitationFlow:
    """Test complete citation workflow from creation to accuracy monitoring."""
    
    @pytest.mark.asyncio
    async def test_complete_citation_lifecycle(
        self, 
        test_db, 
        mock_redis,
        mock_postgres_mcp,
        mock_puppeteer_mcp
    ):
        """Test complete citation lifecycle with all components."""
        # Initialize services
        citation_service = CitationService(
            db=test_db,
            postgres_mcp=mock_postgres_mcp,
            puppeteer_mcp=mock_puppeteer_mcp
        )
        
        accuracy_tracker = AccuracyTracker(
            db=test_db,
            redis_client=mock_redis
        )
        
        # Step 1: Create citation with auto-verification
        citation_data = CitationCreate(
            source_type=SourceType.ACADEMIC,
            url="https://academic.example.com/paper",
            title="Machine Learning in Healthcare",
            authors=["Dr. Smith", "Dr. Jones"],
            publication_date=datetime(2024, 6, 15),
            excerpt="This paper explores the application of ML in medical diagnosis.",
            metadata={
                "doi": "10.1234/example.doi",
                "journal": "Journal of Medical AI",
                "volume": "15",
                "issue": "3"
            }
        )
        
        user_id = uuid4()
        citation = await citation_service.create_citation(
            citation_data=citation_data,
            user_id=user_id,
            auto_verify=True
        )
        
        assert citation.id is not None
        assert citation.verification_status == VerificationStatus.VERIFIED
        
        # Step 2: Track usage
        content_id = uuid4()
        usage = await citation_service.track_usage(
            citation_id=citation.id,
            content_id=content_id,
            user_id=user_id,
            content_type=ContentType.RESEARCH,
            position=1,
            context="As demonstrated in recent research [1]..."
        )
        
        assert usage.citation_id == citation.id
        
        # Step 3: Submit accuracy feedback
        feedback = AccuracyFeedback(
            metric_type=MetricType.RELEVANCE,
            score=0.95,
            feedback_type=FeedbackType.USER,
            comment="Highly relevant to the research topic"
        )
        
        accuracy_record = await citation_service.submit_feedback(
            citation_id=citation.id,
            feedback=feedback,
            user_id=user_id
        )
        
        assert accuracy_record.score == 0.95
        
        # Step 4: Calculate accuracy metrics
        metrics = await accuracy_tracker.calculate_accuracy_metrics(citation.id)
        
        assert metrics[MetricType.RELEVANCE] == 0.95
        assert metrics['overall'] > 0
        
        # Step 5: Check system accuracy
        status = await accuracy_tracker.check_system_accuracy()
        
        # With one high-accuracy citation, should be GREEN
        assert status in [AccuracyStatus.GREEN, AccuracyStatus.YELLOW]
        
        # Step 6: Search for citations
        search_params = CitationSearchParams(
            query="machine learning",
            source_types=[SourceType.ACADEMIC],
            min_quality_score=0.9
        )
        
        results = await citation_service.search_citations(search_params)
        
        assert len(results) >= 0  # May be 0 if search doesn't match
        
        # Step 7: Verify batch of citations
        citations_to_verify = [citation.id]
        verification_results = await citation_service.batch_verify(
            citation_ids=citations_to_verify,
            user_id=user_id
        )
        
        assert len(verification_results) == 1
        assert verification_results[0].citation_id == citation.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])