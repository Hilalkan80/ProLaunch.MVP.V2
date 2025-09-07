"""
Unit tests for the citation service.

Tests individual components and methods of the citation service
to ensure proper functionality and error handling.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import hashlib

from src.services.citation_service import (
    CitationService, CitationCreate, CitationUpdate,
    CitationVerifyRequest, AccuracyFeedback, CitationSearchParams
)
from src.models.citation import (
    Citation, CitationUsage, AccuracyTracking,
    SourceType, VerificationStatus, ContentType,
    FeedbackType, MetricType
)
from src.core.exceptions import (
    NotFoundError, ValidationError, ConflictError,
    ServiceUnavailableError
)


class TestCitationService:
    """Unit tests for CitationService class."""
    
    def test_generate_reference_id(self, test_db):
        """Test reference ID generation."""
        service = CitationService(db=test_db)
        
        ref_id1 = service.generate_reference_id()
        ref_id2 = service.generate_reference_id()
        
        assert ref_id1.startswith("ref_")
        assert ref_id2.startswith("ref_")
        assert ref_id1 != ref_id2  # Should be unique
        assert len(ref_id1) > 10  # Should have timestamp and counter
    
    def test_calculate_content_hash(self, test_db):
        """Test content hash calculation."""
        service = CitationService(db=test_db)
        
        content = "This is test content for hashing"
        hash1 = service.calculate_content_hash(content)
        hash2 = service.calculate_content_hash(content)
        hash3 = service.calculate_content_hash("Different content")
        
        assert hash1 == hash2  # Same content should produce same hash
        assert hash1 != hash3  # Different content should produce different hash
        assert len(hash1) == 64  # SHA256 produces 64-character hex string
    
    @pytest.mark.asyncio
    async def test_create_citation_success(self, test_db):
        """Test successful citation creation."""
        service = CitationService(db=test_db)
        
        citation_data = CitationCreate(
            source_type=SourceType.WEB,
            url="https://example.com/article",
            title="Test Article",
            authors=["Author One"],
            excerpt="Test excerpt"
        )
        
        user_id = uuid4()
        citation = await service.create_citation(
            citation_data=citation_data,
            user_id=user_id,
            auto_verify=False
        )
        
        assert citation.id is not None
        assert citation.reference_id.startswith("ref_")
        assert citation.title == "Test Article"
        assert citation.source_type == SourceType.WEB
        assert citation.verification_status == VerificationStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_create_citation_duplicate_url(self, test_db):
        """Test citation creation with duplicate URL."""
        service = CitationService(db=test_db)
        
        # Create first citation
        citation_data = CitationCreate(
            source_type=SourceType.WEB,
            url="https://example.com/duplicate",
            title="Original Article"
        )
        
        user_id = uuid4()
        citation1 = await service.create_citation(
            citation_data=citation_data,
            user_id=user_id,
            auto_verify=False
        )
        
        # Try to create duplicate
        citation_data2 = CitationCreate(
            source_type=SourceType.WEB,
            url="https://example.com/duplicate",
            title="Duplicate Article"
        )
        
        citation2 = await service.create_citation(
            citation_data=citation_data2,
            user_id=user_id,
            auto_verify=False
        )
        
        # Should return the existing citation
        assert citation1.id == citation2.id
        assert citation2.title == "Original Article"  # Should keep original title
    
    @pytest.mark.asyncio
    async def test_get_citation_success(self, test_db):
        """Test successful citation retrieval."""
        service = CitationService(db=test_db)
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_test_001",
            title="Test Citation",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Retrieve citation
        retrieved = await service.get_citation(citation.id)
        
        assert retrieved.id == citation.id
        assert retrieved.title == "Test Citation"
    
    @pytest.mark.asyncio
    async def test_get_citation_not_found(self, test_db):
        """Test citation retrieval when not found."""
        service = CitationService(db=test_db)
        
        non_existent_id = uuid4()
        
        with pytest.raises(NotFoundError) as exc_info:
            await service.get_citation(non_existent_id)
        
        assert f"Citation {non_existent_id} not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_citation_success(self, test_db):
        """Test successful citation update."""
        service = CitationService(db=test_db)
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_test_002",
            title="Original Title",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Update citation
        update_data = CitationUpdate(
            title="Updated Title",
            authors=["New Author"]
        )
        
        updated = await service.update_citation(
            citation_id=citation.id,
            update_data=update_data,
            user_id=uuid4()
        )
        
        assert updated.title == "Updated Title"
        assert updated.authors == ["New Author"]
    
    @pytest.mark.asyncio
    async def test_verify_citation_without_url(self, test_db):
        """Test citation verification without URL."""
        service = CitationService(db=test_db)
        
        # Create citation without URL
        citation = Citation(
            id=uuid4(),
            reference_id="ref_test_003",
            title="No URL Citation",
            source_type=SourceType.DOCUMENT
        )
        test_db.add(citation)
        test_db.commit()
        
        with pytest.raises(ValidationError) as exc_info:
            await service.verify_citation(
                citation_id=citation.id,
                user_id=uuid4()
            )
        
        assert "Cannot verify citation without URL" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_verify_citation_no_puppeteer(self, test_db):
        """Test citation verification without Puppeteer MCP."""
        service = CitationService(db=test_db, puppeteer_mcp=None)
        
        # Create citation with URL
        citation = Citation(
            id=uuid4(),
            reference_id="ref_test_004",
            title="Test Citation",
            source_type=SourceType.WEB,
            url="https://example.com"
        )
        test_db.add(citation)
        test_db.commit()
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            await service.verify_citation(
                citation_id=citation.id,
                user_id=uuid4()
            )
        
        assert "Puppeteer MCP not configured" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_track_usage_success(self, test_db):
        """Test successful citation usage tracking."""
        service = CitationService(db=test_db)
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_test_005",
            title="Test Citation",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Track usage
        usage = await service.track_usage(
            citation_id=citation.id,
            content_id=uuid4(),
            user_id=uuid4(),
            content_type=ContentType.RESEARCH,
            position=1,
            context="Test context"
        )
        
        assert usage.citation_id == citation.id
        assert usage.content_type == ContentType.RESEARCH
        assert usage.position == 1
        assert usage.context == "Test context"
        
        # Check that usage count is incremented
        test_db.refresh(citation)
        assert citation.usage_count == 1
    
    @pytest.mark.asyncio
    async def test_submit_feedback_success(self, test_db):
        """Test successful feedback submission."""
        service = CitationService(db=test_db)
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_test_006",
            title="Test Citation",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Submit feedback
        feedback = AccuracyFeedback(
            metric_type=MetricType.ACCURACY,
            score=0.92,
            feedback_type=FeedbackType.USER,
            comment="Accurate information"
        )
        
        accuracy_record = await service.submit_feedback(
            citation_id=citation.id,
            feedback=feedback,
            user_id=uuid4()
        )
        
        assert accuracy_record.citation_id == citation.id
        assert accuracy_record.metric_type == MetricType.ACCURACY
        assert accuracy_record.score == 0.92
        assert accuracy_record.feedback_type == FeedbackType.USER
    
    @pytest.mark.asyncio
    async def test_search_citations_by_query(self, test_db):
        """Test citation search by query."""
        service = CitationService(db=test_db)
        
        # Create test citations
        citations = [
            Citation(
                id=uuid4(),
                reference_id=f"ref_search_{i:03d}",
                title=f"{'Machine Learning' if i % 2 == 0 else 'Data Science'} Article {i}",
                source_type=SourceType.WEB,
                overall_quality_score=0.8 + (i * 0.02)
            )
            for i in range(5)
        ]
        
        for citation in citations:
            test_db.add(citation)
        test_db.commit()
        
        # Search for "Machine Learning"
        search_params = CitationSearchParams(
            query="Machine Learning",
            limit=10
        )
        
        results = await service.search_citations(search_params)
        
        # Should find citations with "Machine Learning" in title
        ml_citations = [c for c in results if "Machine Learning" in c.title]
        assert len(ml_citations) > 0
    
    @pytest.mark.asyncio
    async def test_search_citations_by_source_type(self, test_db):
        """Test citation search by source type."""
        service = CitationService(db=test_db)
        
        # Create citations with different source types
        citations = [
            Citation(
                id=uuid4(),
                reference_id=f"ref_type_{i:03d}",
                title=f"Citation {i}",
                source_type=SourceType.ACADEMIC if i % 2 == 0 else SourceType.WEB
            )
            for i in range(4)
        ]
        
        for citation in citations:
            test_db.add(citation)
        test_db.commit()
        
        # Search for academic sources
        search_params = CitationSearchParams(
            source_types=[SourceType.ACADEMIC],
            limit=10
        )
        
        results = await service.search_citations(search_params)
        
        # All results should be academic sources
        for citation in results:
            assert citation.source_type == SourceType.ACADEMIC
    
    @pytest.mark.asyncio
    async def test_batch_verify_citations(self, test_db, mock_puppeteer_mcp):
        """Test batch citation verification."""
        service = CitationService(
            db=test_db,
            puppeteer_mcp=mock_puppeteer_mcp
        )
        
        # Create multiple citations
        citations = [
            Citation(
                id=uuid4(),
                reference_id=f"ref_batch_{i:03d}",
                title=f"Citation {i}",
                source_type=SourceType.WEB,
                url=f"https://example.com/article{i}"
            )
            for i in range(3)
        ]
        
        for citation in citations:
            test_db.add(citation)
        test_db.commit()
        
        citation_ids = [c.id for c in citations]
        
        # Batch verify
        results = await service.batch_verify(
            citation_ids=citation_ids,
            user_id=uuid4()
        )
        
        assert len(results) == 3
        # Check that all verifications were attempted
        assert mock_puppeteer_mcp.verify_url.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_accuracy_report(self, test_db):
        """Test accuracy report generation."""
        service = CitationService(db=test_db)
        
        # Create citations with varying accuracy
        citations = [
            Citation(
                id=uuid4(),
                reference_id=f"ref_report_{i:03d}",
                title=f"Citation {i}",
                source_type=SourceType.WEB if i < 3 else SourceType.ACADEMIC,
                overall_quality_score=0.95 if i < 7 else 0.85,
                verification_status=VerificationStatus.VERIFIED if i < 5 else VerificationStatus.PENDING
            )
            for i in range(10)
        ]
        
        for citation in citations:
            test_db.add(citation)
        test_db.commit()
        
        # Generate report
        report = await service.get_accuracy_report(
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow()
        )
        
        assert 'overall_accuracy' in report
        assert 'accuracy_by_source' in report
        assert 'verification_statistics' in report
        assert report['overall_accuracy'] >= 0.0
        assert report['overall_accuracy'] <= 1.0


class TestCitationValidation:
    """Test citation data validation."""
    
    def test_citation_create_validation(self):
        """Test CitationCreate model validation."""
        # Valid data
        valid_data = CitationCreate(
            source_type=SourceType.WEB,
            url="https://example.com",
            title="Valid Title",
            authors=["Author"]
        )
        assert valid_data.title == "Valid Title"
        
        # Empty title should raise error
        with pytest.raises(ValueError):
            CitationCreate(
                source_type=SourceType.WEB,
                url="https://example.com",
                title="",  # Empty title
                authors=[]
            )
        
        # Whitespace-only title should raise error
        with pytest.raises(ValueError):
            CitationCreate(
                source_type=SourceType.WEB,
                url="https://example.com",
                title="   ",  # Whitespace only
                authors=[]
            )
    
    def test_accuracy_feedback_validation(self):
        """Test AccuracyFeedback model validation."""
        # Valid feedback
        valid_feedback = AccuracyFeedback(
            metric_type=MetricType.RELEVANCE,
            score=0.95,
            feedback_type=FeedbackType.USER
        )
        assert valid_feedback.score == 0.95
        
        # Score out of range should raise error
        with pytest.raises(ValueError):
            AccuracyFeedback(
                metric_type=MetricType.RELEVANCE,
                score=1.5,  # > 1.0
                feedback_type=FeedbackType.USER
            )
        
        with pytest.raises(ValueError):
            AccuracyFeedback(
                metric_type=MetricType.RELEVANCE,
                score=-0.1,  # < 0.0
                feedback_type=FeedbackType.USER
            )
    
    def test_search_params_validation(self):
        """Test CitationSearchParams validation."""
        # Valid search params
        valid_params = CitationSearchParams(
            query="test query",
            source_types=[SourceType.WEB, SourceType.ACADEMIC],
            min_quality_score=0.8,
            limit=50
        )
        assert valid_params.limit == 50
        
        # Default values
        default_params = CitationSearchParams()
        assert default_params.limit == 20
        assert default_params.offset == 0
        assert default_params.min_quality_score == 0.0


class TestCitationCaching:
    """Test citation caching functionality."""
    
    @pytest.mark.asyncio
    async def test_citation_cache_on_create(self, test_db, mock_cache):
        """Test that citations are cached on creation."""
        service = CitationService(db=test_db, cache_manager=mock_cache)
        
        citation_data = CitationCreate(
            source_type=SourceType.WEB,
            url="https://example.com",
            title="Cached Citation"
        )
        
        citation = await service.create_citation(
            citation_data=citation_data,
            user_id=uuid4(),
            auto_verify=False
        )
        
        # Check that cache.set was called
        mock_cache.set.assert_called()
        cache_key = f"citation:{citation.id}"
        assert mock_cache.set.call_args[0][0] == cache_key
    
    @pytest.mark.asyncio
    async def test_citation_cache_on_get(self, test_db, mock_cache):
        """Test that citations are retrieved from cache."""
        service = CitationService(db=test_db, cache_manager=mock_cache)
        
        citation_id = uuid4()
        
        # Mock cache hit
        cached_data = {
            'id': str(citation_id),
            'reference_id': 'ref_cached_001',
            'title': 'Cached Citation',
            'source_type': SourceType.WEB
        }
        mock_cache.get.return_value = cached_data
        
        # Get citation (should use cache)
        citation = await service.get_citation(citation_id)
        
        # Verify cache was checked
        mock_cache.get.assert_called_with(f"citation:{citation_id}")
        assert citation.title == 'Cached Citation'
    
    @pytest.mark.asyncio
    async def test_citation_cache_invalidation_on_update(self, test_db, mock_cache):
        """Test that cache is invalidated on update."""
        service = CitationService(db=test_db, cache_manager=mock_cache)
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_update_001",
            title="Original Title",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Update citation
        update_data = CitationUpdate(title="Updated Title")
        await service.update_citation(
            citation_id=citation.id,
            update_data=update_data,
            user_id=uuid4()
        )
        
        # Verify cache was invalidated
        mock_cache.delete.assert_called_with(f"citation:{citation.id}")


# Test fixtures for this module
@pytest.fixture
def test_db():
    """Create in-memory test database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models.base import Base
    
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def mock_cache():
    """Create mock cache manager."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock


@pytest.fixture
def mock_puppeteer_mcp():
    """Create mock Puppeteer MCP."""
    mock = AsyncMock()
    mock.verify_url.return_value = {
        'status': 'verified',
        'content': 'Test content',
        'title': 'Test Title',
        'screenshot_url': 'https://screenshot.example.com/test.png'
    }
    return mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])