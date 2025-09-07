"""
Integration tests for the Citation system.

Tests the complete integration between citation service, database,
external verification services, and API endpoints.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.citation import (
    Citation, CitationUsage, AccuracyTracking, VerificationLog,
    SourceType, VerificationStatus, ContentType, FeedbackType, MetricType
)
from src.services.citation_service import CitationService, CitationCreate
from src.api.v1.citations import router
from src.core.exceptions import ServiceUnavailableError


@pytest.fixture(scope="session")
def integration_db():
    """Create in-memory database for integration tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Import and create all tables
    from src.models.base import Base
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


@pytest.fixture
async def mock_external_services():
    """Mock external services for integration testing."""
    # Mock Puppeteer MCP
    puppeteer_mcp = Mock()
    puppeteer_mcp.verify_url = AsyncMock()
    
    # Mock Postgres MCP
    postgres_mcp = Mock()
    postgres_mcp.execute_query = AsyncMock()
    postgres_mcp.store_data = AsyncMock()
    
    # Mock Cache Manager
    cache_manager = Mock()
    cache_manager.get = Mock(return_value=None)
    cache_manager.set = Mock(return_value=True)
    cache_manager.delete = Mock(return_value=True)
    
    return {
        "puppeteer_mcp": puppeteer_mcp,
        "postgres_mcp": postgres_mcp,
        "cache_manager": cache_manager
    }


@pytest.fixture
async def citation_service(integration_db, mock_external_services):
    """Create citation service with mocked external dependencies."""
    service = CitationService(
        db=integration_db,
        cache_manager=mock_external_services["cache_manager"],
        postgres_mcp=mock_external_services["postgres_mcp"],
        puppeteer_mcp=mock_external_services["puppeteer_mcp"]
    )
    
    # Store mock references for test access
    service._test_mocks = mock_external_services
    
    return service


class TestCitationWorkflowIntegration:
    """Integration tests for complete citation workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_citation_lifecycle(self, citation_service, integration_db):
        """Test complete citation lifecycle from creation to analysis."""
        service = citation_service
        db = integration_db
        mocks = service._test_mocks
        
        # Setup verification mock
        mocks["puppeteer_mcp"].verify_url.return_value = {
            'status': 'verified',
            'content': 'This is the verified content of the research paper on AI applications in healthcare.',
            'title': 'AI Applications in Healthcare: A Comprehensive Review',
            'screenshot_url': 'https://screenshots.example.com/healthcare-ai.png',
            'metadata': {
                'author': 'Dr. Jane Smith',
                'publication_date': '2024-01-15',
                'journal': 'Journal of Medical AI'
            }
        }
        
        user_id = uuid4()
        
        # Step 1: Create citation
        citation_data = CitationCreate(
            source_type=SourceType.ACADEMIC,
            url="https://journal.medai.com/papers/healthcare-ai-2024",
            title="AI in Healthcare Research",
            authors=["Dr. Jane Smith", "Dr. Bob Johnson"],
            publication_date=datetime(2024, 1, 15),
            excerpt="This paper explores the current applications of AI in healthcare...",
            metadata={
                "journal": "Journal of Medical AI",
                "doi": "10.1234/jmai.2024.001",
                "peer_reviewed": True
            }
        )
        
        citation = await service.create_citation(
            citation_data=citation_data,
            user_id=user_id,
            auto_verify=True
        )
        
        # Verify citation was created
        assert citation.id is not None
        assert citation.reference_id.startswith("ref_")
        assert citation.title == "AI in Healthcare Research"
        assert citation.verification_status == VerificationStatus.VERIFIED
        assert citation.availability_score == 1.0
        
        # Step 2: Track usage in multiple content pieces
        content_ids = [uuid4() for _ in range(3)]
        
        # Usage in research paper
        await service.track_usage(
            citation_id=citation.id,
            content_id=content_ids[0],
            user_id=user_id,
            content_type=ContentType.RESEARCH,
            position=1,
            context="In the introduction, we reference Smith's comprehensive review...",
            section="Introduction"
        )
        
        # Usage in analysis report
        await service.track_usage(
            citation_id=citation.id,
            content_id=content_ids[1],
            user_id=user_id,
            content_type=ContentType.ANALYSIS,
            position=3,
            context="The methodology described by Smith et al. provides a framework...",
            section="Methodology"
        )
        
        # Usage in summary document
        await service.track_usage(
            citation_id=citation.id,
            content_id=content_ids[2],
            user_id=user_id,
            content_type=ContentType.SUMMARY,
            position=2,
            context="Key findings from the healthcare AI review include...",
            section="Key Findings"
        )
        
        # Step 3: Submit accuracy feedback from multiple evaluators
        evaluators = [uuid4() for _ in range(4)]
        
        # Expert review - high accuracy
        from src.services.citation_service import AccuracyFeedback
        expert_feedback = AccuracyFeedback(
            metric_type=MetricType.ACCURACY,
            score=0.95,
            feedback_type=FeedbackType.EXPERT,
            comment="Highly accurate and well-referenced academic paper",
            verified_facts=[
                "AI applications in diagnostic imaging",
                "Machine learning for drug discovery",
                "Natural language processing in clinical notes"
            ]
        )
        await service.submit_accuracy_feedback(citation.id, expert_feedback, evaluators[0])
        
        # User review - good relevance
        user_feedback = AccuracyFeedback(
            metric_type=MetricType.RELEVANCE,
            score=0.88,
            feedback_type=FeedbackType.USER,
            comment="Very relevant to my healthcare AI research project"
        )
        await service.submit_accuracy_feedback(citation.id, user_feedback, evaluators[1])
        
        # Automated check - excellent availability
        automated_feedback = AccuracyFeedback(
            metric_type=MetricType.AVAILABILITY,
            score=0.98,
            feedback_type=FeedbackType.AUTOMATED,
            comment="Source consistently accessible, no downtime detected"
        )
        await service.submit_accuracy_feedback(citation.id, automated_feedback, evaluators[2])
        
        # Community review - good completeness
        community_feedback = AccuracyFeedback(
            metric_type=MetricType.COMPLETENESS,
            score=0.82,
            feedback_type=FeedbackType.COMMUNITY,
            comment="Comprehensive coverage of the topic with minor gaps"
        )
        await service.submit_accuracy_feedback(citation.id, community_feedback, evaluators[3])
        
        # Step 4: Verify integrated state
        db.refresh(citation)
        
        # Check citation scores were updated
        assert citation.accuracy_score == 0.95
        assert citation.relevance_score == 0.88
        assert citation.availability_score == 0.98
        
        # Check overall quality calculation
        expected_quality = (0.4 * 0.88) + (0.4 * 0.95) + (0.2 * 0.98)
        assert abs(citation.overall_quality_score - expected_quality) < 0.01
        
        # Check usage tracking
        assert citation.usage_count == 3
        assert citation.last_used is not None
        
        # Step 5: Verify verification log was created
        verification_logs = db.query(VerificationLog).filter(
            VerificationLog.citation_id == citation.id
        ).all()
        assert len(verification_logs) == 1
        assert verification_logs[0].status == "success"
        assert verification_logs[0].content_matched is True
        
        # Step 6: Verify all usage records
        usage_records = db.query(CitationUsage).filter(
            CitationUsage.citation_id == citation.id
        ).all()
        assert len(usage_records) == 3
        
        content_types = {usage.content_type for usage in usage_records}
        assert content_types == {ContentType.RESEARCH, ContentType.ANALYSIS, ContentType.SUMMARY}
        
        # Step 7: Verify accuracy tracking records
        accuracy_records = db.query(AccuracyTracking).filter(
            AccuracyTracking.citation_id == citation.id
        ).all()
        assert len(accuracy_records) == 4
        
        feedback_types = {record.feedback_type for record in accuracy_records}
        assert feedback_types == {
            FeedbackType.EXPERT, FeedbackType.USER, 
            FeedbackType.AUTOMATED, FeedbackType.COMMUNITY
        }
    
    @pytest.mark.asyncio
    async def test_citation_verification_failure_recovery(self, citation_service):
        """Test recovery from citation verification failures."""
        service = citation_service
        mocks = service._test_mocks
        
        # Create citation
        user_id = uuid4()
        citation_data = CitationCreate(
            source_type=SourceType.WEB,
            url="https://unreliable-website.com/article",
            title="Unreliable Web Article",
            excerpt="This article might not be accessible"
        )
        
        citation = await service.create_citation(
            citation_data=citation_data,
            user_id=user_id,
            auto_verify=False  # Don't auto-verify to control the process
        )
        
        # First verification attempt - failure
        mocks["puppeteer_mcp"].verify_url.side_effect = Exception("Network timeout")
        
        with pytest.raises(ServiceUnavailableError):
            await service.verify_citation(citation.id, user_id)
        
        # Check citation status after failure
        service.db.refresh(citation)
        assert citation.verification_status == VerificationStatus.FAILED
        assert citation.verification_attempts == 1
        assert citation.availability_score == 0.0
        
        # Second verification attempt - still failing
        mocks["puppeteer_mcp"].verify_url.side_effect = Exception("Service unavailable")
        
        with pytest.raises(ServiceUnavailableError):
            await service.verify_citation(citation.id, user_id)
        
        service.db.refresh(citation)
        assert citation.verification_attempts == 2
        
        # Third verification attempt - success (site is back up)
        mocks["puppeteer_mcp"].verify_url.side_effect = None
        mocks["puppeteer_mcp"].verify_url.return_value = {
            'status': 'verified',
            'content': 'Article content is now accessible',
            'title': 'Reliable Web Article (Updated)',
            'screenshot_url': 'https://screenshots.example.com/recovered.png'
        }
        
        verification_result = await service.verify_citation(citation.id, user_id)
        
        # Check recovery
        assert verification_result.status == "success"
        service.db.refresh(citation)
        assert citation.verification_status == VerificationStatus.VERIFIED
        assert citation.verification_attempts == 3
        assert citation.availability_score == 1.0
        assert citation.title == "Reliable Web Article (Updated)"
    
    @pytest.mark.asyncio
    async def test_batch_citation_processing(self, citation_service):
        """Test processing of multiple citations in batch operations."""
        service = citation_service
        mocks = service._test_mocks
        
        # Setup batch verification mock
        def mock_verify_url(url, **kwargs):
            # Simulate different verification outcomes based on URL
            if "reliable" in url:
                return {
                    'status': 'verified',
                    'content': f'Verified content for {url}',
                    'title': f'Verified: {url.split("/")[-1].title()}',
                    'screenshot_url': f'https://screenshots.example.com/{hash(url) % 1000}.png'
                }
            elif "slow" in url:
                raise asyncio.TimeoutError("Slow response")
            else:
                raise Exception("Verification failed")
        
        mocks["puppeteer_mcp"].verify_url.side_effect = mock_verify_url
        
        # Create batch of citations
        user_id = uuid4()
        citations_data = [
            {
                "url": "https://reliable-source-1.com/article",
                "title": "Reliable Article 1",
                "source_type": SourceType.WEB
            },
            {
                "url": "https://reliable-source-2.com/research",
                "title": "Reliable Research 2",
                "source_type": SourceType.ACADEMIC
            },
            {
                "url": "https://slow-website.com/content",
                "title": "Slow Website Article",
                "source_type": SourceType.WEB
            },
            {
                "url": "https://broken-link.com/missing",
                "title": "Broken Link Article",
                "source_type": SourceType.WEB
            },
            {
                "url": "https://reliable-source-3.com/news",
                "title": "Reliable News 3",
                "source_type": SourceType.NEWS
            }
        ]
        
        # Create citations using batch_create_citations
        citation_creates = [
            CitationCreate(
                source_type=data["source_type"],
                url=data["url"],
                title=data["title"],
                excerpt=f"Test excerpt for {data['title']}"
            )
            for data in citations_data
        ]
        
        created_citations = await service.batch_create_citations(citation_creates, user_id)
        assert len(created_citations) == 5
        
        # Manually verify each citation (simulate batch verification)
        verification_results = []
        for citation in created_citations:
            try:
                result = await service.verify_citation(citation.id, user_id)
                verification_results.append((citation, result, "success"))
            except Exception as e:
                verification_results.append((citation, None, str(e)))
        
        # Analyze batch results
        successful_verifications = [r for r in verification_results if r[2] == "success"]
        failed_verifications = [r for r in verification_results if r[2] != "success"]
        
        # Should have 3 successful (reliable sources) and 2 failed (slow + broken)
        assert len(successful_verifications) == 3
        assert len(failed_verifications) == 2
        
        # Verify successful citations
        for citation, result, status in successful_verifications:
            service.db.refresh(citation)
            assert citation.verification_status == VerificationStatus.VERIFIED
            assert citation.availability_score == 1.0
            assert "Verified:" in citation.title
        
        # Verify failed citations
        for citation, result, status in failed_verifications:
            service.db.refresh(citation)
            assert citation.verification_status == VerificationStatus.FAILED
            assert citation.availability_score == 0.0
    
    @pytest.mark.asyncio
    async def test_citation_search_integration(self, citation_service):
        """Test integrated citation search functionality."""
        service = citation_service
        
        # Create diverse citations for comprehensive search testing
        user_id = uuid4()
        base_date = datetime.utcnow()
        
        citations_data = [
            {
                "title": "Machine Learning in Healthcare: Advanced Applications",
                "source_type": SourceType.ACADEMIC,
                "quality_score": 0.95,
                "verification_status": VerificationStatus.VERIFIED,
                "age_days": 10,
                "excerpt": "This research explores machine learning applications in medical diagnosis",
                "tags": ["healthcare", "AI", "machine learning"]
            },
            {
                "title": "Business Strategy for AI Startups",
                "source_type": SourceType.WEB,
                "quality_score": 0.80,
                "verification_status": VerificationStatus.VERIFIED,
                "age_days": 25,
                "excerpt": "Comprehensive guide to building successful AI-focused startups",
                "tags": ["business", "startup", "AI"]
            },
            {
                "title": "Government AI Ethics Guidelines",
                "source_type": SourceType.GOVERNMENT,
                "quality_score": 0.92,
                "verification_status": VerificationStatus.VERIFIED,
                "age_days": 5,
                "excerpt": "Official guidelines for ethical AI development and deployment",
                "tags": ["ethics", "government", "AI policy"]
            },
            {
                "title": "Unverified AI Blog Post",
                "source_type": SourceType.WEB,
                "quality_score": 0.45,
                "verification_status": VerificationStatus.FAILED,
                "age_days": 40,
                "excerpt": "Questionable claims about AI capabilities without proper citations",
                "tags": ["blog", "opinion"]
            },
            {
                "title": "Breaking: Latest AI Breakthrough",
                "source_type": SourceType.NEWS,
                "quality_score": 0.75,
                "verification_status": VerificationStatus.VERIFIED,
                "age_days": 2,
                "excerpt": "Recent news about major AI research breakthrough",
                "tags": ["news", "breakthrough", "AI"]
            }
        ]
        
        created_citations = []
        for i, data in enumerate(citations_data):
            citation_create = CitationCreate(
                source_type=data["source_type"],
                url=f"https://example-{i}.com/article",
                title=data["title"],
                excerpt=data["excerpt"],
                metadata={"tags": data["tags"]}
            )
            
            citation = await service.create_citation(citation_create, user_id, auto_verify=False)
            
            # Manually set properties for testing
            citation.overall_quality_score = data["quality_score"]
            citation.verification_status = data["verification_status"]
            citation.access_date = base_date - timedelta(days=data["age_days"])
            service.db.commit()
            
            created_citations.append(citation)
        
        # Test various search scenarios
        from src.services.citation_service import CitationSearchParams
        
        # Search by keyword
        ai_search = CitationSearchParams(
            query="AI artificial intelligence",
            limit=10
        )
        ai_results, ai_count = await service.search_citations(ai_search)
        assert ai_count >= 4  # Most citations mention AI
        
        # Search by source type
        academic_search = CitationSearchParams(
            source_types=[SourceType.ACADEMIC],
            limit=10
        )
        academic_results, academic_count = await service.search_citations(academic_search)
        assert academic_count == 1
        assert academic_results[0].title == "Machine Learning in Healthcare: Advanced Applications"
        
        # Search by quality score
        high_quality_search = CitationSearchParams(
            min_quality_score=0.85,
            limit=10
        )
        hq_results, hq_count = await service.search_citations(high_quality_search)
        assert hq_count == 2  # Healthcare (0.95) and Government (0.92)
        
        # Search by verification status
        verified_search = CitationSearchParams(
            verification_status=VerificationStatus.VERIFIED,
            limit=10
        )
        verified_results, verified_count = await service.search_citations(verified_search)
        assert verified_count == 4  # All except the failed blog post
        
        # Search by age
        recent_search = CitationSearchParams(
            max_age_days=20,
            limit=10
        )
        recent_results, recent_count = await service.search_citations(recent_search)
        assert recent_count == 3  # Healthcare (10 days), Government (5 days), News (2 days)
        
        # Complex combined search
        complex_search = CitationSearchParams(
            query="healthcare",
            source_types=[SourceType.ACADEMIC, SourceType.GOVERNMENT],
            min_quality_score=0.90,
            verification_status=VerificationStatus.VERIFIED,
            max_age_days=30,
            limit=5
        )
        complex_results, complex_count = await service.search_citations(complex_search)
        
        # Should find Healthcare article (matches all criteria) but not Government (no "healthcare" in title/excerpt)
        assert complex_count >= 1
        healthcare_found = any("Healthcare" in result.title for result in complex_results)
        assert healthcare_found
    
    @pytest.mark.asyncio
    async def test_citation_accuracy_reporting_integration(self, citation_service):
        """Test integrated accuracy reporting functionality."""
        service = citation_service
        user_id = uuid4()
        
        # Create citations with varying accuracy levels
        citations_data = [
            ("High Accuracy Citation", SourceType.ACADEMIC, [(MetricType.ACCURACY, 0.95, FeedbackType.EXPERT)]),
            ("Medium Accuracy Citation", SourceType.WEB, [(MetricType.ACCURACY, 0.75, FeedbackType.USER)]),
            ("Low Accuracy Citation", SourceType.WEB, [(MetricType.ACCURACY, 0.40, FeedbackType.AUTOMATED)]),
            ("Mixed Reviews Citation", SourceType.NEWS, [
                (MetricType.ACCURACY, 0.90, FeedbackType.EXPERT),
                (MetricType.RELEVANCE, 0.60, FeedbackType.USER),
                (MetricType.AVAILABILITY, 0.95, FeedbackType.AUTOMATED)
            ])
        ]
        
        created_citations = []
        for title, source_type, feedback_list in citations_data:
            # Create citation
            citation_create = CitationCreate(
                source_type=source_type,
                url=f"https://example.com/{title.lower().replace(' ', '-')}",
                title=title,
                excerpt=f"Test excerpt for {title}"
            )
            
            citation = await service.create_citation(citation_create, user_id, auto_verify=False)
            citation.verification_status = VerificationStatus.VERIFIED
            service.db.commit()
            
            # Submit feedback
            for metric_type, score, feedback_type in feedback_list:
                from src.services.citation_service import AccuracyFeedback
                feedback = AccuracyFeedback(
                    metric_type=metric_type,
                    score=score,
                    feedback_type=feedback_type,
                    comment=f"Test feedback for {title}"
                )
                evaluator_id = uuid4()
                await service.submit_accuracy_feedback(citation.id, feedback, evaluator_id)
            
            created_citations.append(citation)
        
        # Generate accuracy report
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow() + timedelta(days=1)
        
        report = await service.get_accuracy_report(start_date, end_date)
        
        # Verify report structure
        assert 'overall_accuracy' in report
        assert 'accuracy_status' in report
        assert 'accuracy_by_source' in report
        assert 'verification_statistics' in report
        assert 'citations_needing_attention' in report
        assert 'feedback_statistics' in report
        
        # Check overall accuracy calculation
        # Should reflect the average of all accuracy scores
        assert 0 <= report['overall_accuracy'] <= 100
        
        # Check accuracy by source type
        source_accuracy = {item['source_type']: item['average_score'] 
                          for item in report['accuracy_by_source']}
        
        # Academic should have highest score (95%)
        assert source_accuracy.get('academic', 0) >= 90
        
        # Check verification statistics
        verified_stats = next(
            (item for item in report['verification_statistics'] 
             if item['status'] == 'verified'), 
            None
        )
        assert verified_stats is not None
        assert verified_stats['count'] == 4  # All citations are verified
        
        # Check citations needing attention (low accuracy)
        low_accuracy_citations = report['citations_needing_attention']
        low_accuracy_titles = [c['title'] for c in low_accuracy_citations]
        assert "Low Accuracy Citation" in low_accuracy_titles
        
        # Check feedback statistics
        feedback_stats = {item['feedback_type']: item['count'] 
                         for item in report['feedback_statistics']}
        
        # Should have feedback from all types
        assert feedback_stats.get('expert', 0) >= 1
        assert feedback_stats.get('user', 0) >= 1
        assert feedback_stats.get('automated', 0) >= 1
    
    @pytest.mark.asyncio
    async def test_stale_citation_management_workflow(self, citation_service):
        """Test complete workflow for managing stale citations."""
        service = citation_service
        mocks = service._test_mocks
        user_id = uuid4()
        
        # Create citations with different verification states
        base_date = datetime.utcnow()
        
        citations_data = [
            ("Fresh Citation", base_date - timedelta(days=5), VerificationStatus.VERIFIED),
            ("Aging Citation", base_date - timedelta(days=35), VerificationStatus.VERIFIED),
            ("Stale Citation", base_date - timedelta(days=60), VerificationStatus.VERIFIED),
            ("Failed Citation", base_date - timedelta(days=20), VerificationStatus.FAILED),
            ("Pending Citation", None, VerificationStatus.PENDING),
        ]
        
        created_citations = []
        for title, last_verified, status in citations_data:
            citation_create = CitationCreate(
                source_type=SourceType.WEB,
                url=f"https://example.com/{title.lower().replace(' ', '-')}",
                title=title,
                excerpt=f"Test excerpt for {title}"
            )
            
            citation = await service.create_citation(citation_create, user_id, auto_verify=False)
            citation.last_verified = last_verified
            citation.verification_status = status
            service.db.commit()
            
            created_citations.append(citation)
        
        # Identify stale citations
        stale_citations = await service.get_stale_citations(
            days_threshold=30,  # 30 days threshold
            limit=10
        )
        
        # Should find aging and stale citations
        assert len(stale_citations) >= 2
        stale_titles = [c.title for c in stale_citations]
        assert "Aging Citation" in stale_titles
        assert "Stale Citation" in stale_titles
        
        # Setup re-verification
        def mock_reverify(url, **kwargs):
            if "aging" in url:
                return {
                    'status': 'verified',
                    'content': 'Content still available and updated',
                    'title': 'Aging Citation (Reverified)',
                    'screenshot_url': 'https://screenshots.example.com/reverified.png'
                }
            else:  # stale citation
                raise Exception("Source no longer available")
        
        mocks["puppeteer_mcp"].verify_url.side_effect = mock_reverify
        
        # Re-verify stale citations
        reverification_results = []
        for citation in stale_citations:
            try:
                result = await service.verify_citation(citation.id, user_id)
                reverification_results.append((citation, True, "success"))
                
                # Mark as no longer requiring reverification
                citation.requires_reverification = False
                service.db.commit()
                
            except Exception as e:
                reverification_results.append((citation, False, str(e)))
                
                # Mark as requiring manual review
                citation.verification_status = VerificationStatus.FAILED
                citation.requires_reverification = True
                service.db.commit()
        
        # Analyze reverification results
        successful_reverifications = [r for r in reverification_results if r[1]]
        failed_reverifications = [r for r in reverification_results if not r[1]]
        
        # Should have one success (aging) and one failure (stale)
        assert len(successful_reverifications) >= 1
        assert len(failed_reverifications) >= 1
        
        # Check updated states
        for citation, success, message in reverification_results:
            service.db.refresh(citation)
            if success:
                assert citation.verification_status == VerificationStatus.VERIFIED
                assert not citation.requires_reverification
            else:
                assert citation.verification_status == VerificationStatus.FAILED
                assert citation.requires_reverification


if __name__ == "__main__":
    pytest.main([__file__, "-v"])