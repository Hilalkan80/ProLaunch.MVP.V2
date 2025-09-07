"""
Extended unit tests for the Citation service.

Additional comprehensive tests covering advanced functionality, 
error scenarios, and edge cases not covered in the base test suite.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from src.services.citation_service import (
    CitationService, CitationCreate, CitationUpdate,
    CitationVerifyRequest, AccuracyFeedback, CitationSearchParams
)
from src.models.citation import (
    Citation, CitationUsage, AccuracyTracking, VerificationLog,
    CitationCollection, SourceType, VerificationStatus, 
    ContentType, FeedbackType, MetricType
)
from src.core.exceptions import (
    NotFoundError, ValidationError, ConflictError,
    ServiceUnavailableError
)


class TestAdvancedCitationOperations:
    """Test advanced citation operations and edge cases."""
    
    @pytest.mark.asyncio
    async def test_batch_citation_verification(self, test_db, mock_puppeteer_mcp):
        """Test batch verification of multiple citations."""
        service = CitationService(
            db=test_db,
            puppeteer_mcp=mock_puppeteer_mcp
        )
        
        # Create multiple citations with URLs
        citations = []
        for i in range(5):
            citation = Citation(
                id=uuid4(),
                reference_id=f"ref_batch_{i:03d}",
                title=f"Batch Citation {i}",
                source_type=SourceType.WEB,
                url=f"https://example.com/article{i}",
                verification_status=VerificationStatus.PENDING
            )
            test_db.add(citation)
            citations.append(citation)
        test_db.commit()
        
        # Mock successful verification for all citations
        mock_puppeteer_mcp.verify_url.return_value = {
            'status': 'verified',
            'content': 'Test verification content',
            'title': 'Verified Title',
            'screenshot_url': 'https://screenshot.example.com/test.png'
        }
        
        # Test batch verification
        citation_ids = [c.id for c in citations]
        user_id = uuid4()
        
        results = []
        for citation_id in citation_ids:
            result = await service.verify_citation(citation_id, user_id)
            results.append(result)
        
        # Verify all citations were processed
        assert len(results) == 5
        for result in results:
            assert result is not None
            assert result.status == "success"
        
        # Verify all citations are now verified
        for citation in citations:
            test_db.refresh(citation)
            assert citation.verification_status == VerificationStatus.VERIFIED
            assert citation.verification_attempts == 1
            assert citation.availability_score == 1.0
    
    @pytest.mark.asyncio
    async def test_citation_content_change_detection(self, test_db, mock_puppeteer_mcp):
        """Test detection of content changes during verification."""
        service = CitationService(
            db=test_db,
            puppeteer_mcp=mock_puppeteer_mcp
        )
        
        # Create citation with initial content hash
        original_content = "Original content that will change"
        original_hash = service.calculate_content_hash(original_content)
        
        citation = Citation(
            id=uuid4(),
            reference_id="ref_change_detect",
            title="Change Detection Test",
            source_type=SourceType.WEB,
            url="https://example.com/changing-content",
            content_hash=original_hash
        )
        test_db.add(citation)
        test_db.commit()
        
        # Mock verification with changed content
        new_content = "Updated content that has been modified"
        mock_puppeteer_mcp.verify_url.return_value = {
            'status': 'verified',
            'content': new_content,
            'title': 'Updated Title',
            'screenshot_url': 'https://screenshot.example.com/updated.png'
        }
        
        # Verify citation
        user_id = uuid4()
        result = await service.verify_citation(citation.id, user_id)
        
        # Verify change detection
        assert result.content_matched is False
        assert result.changes_detected is not None
        assert result.changes_detected['old_hash'] == original_hash
        assert result.changes_detected['new_hash'] != original_hash
        
        # Verify citation was updated
        test_db.refresh(citation)
        new_hash = service.calculate_content_hash(new_content)
        assert citation.content_hash == new_hash
        assert citation.title == "Updated Title"
    
    @pytest.mark.asyncio
    async def test_citation_quality_scoring(self, test_db):
        """Test citation quality scoring based on multiple feedback."""
        service = CitationService(db=test_db)
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_quality_test",
            title="Quality Test Citation",
            source_type=SourceType.ACADEMIC
        )
        test_db.add(citation)
        test_db.commit()
        
        # Submit multiple accuracy feedback entries
        evaluators = [uuid4() for _ in range(3)]
        
        # High quality feedback
        feedback1 = AccuracyFeedback(
            metric_type=MetricType.ACCURACY,
            score=0.95,
            feedback_type=FeedbackType.EXPERT,
            comment="Highly accurate and well-sourced"
        )
        await service.submit_accuracy_feedback(citation.id, feedback1, evaluators[0])
        
        # Medium relevance feedback
        feedback2 = AccuracyFeedback(
            metric_type=MetricType.RELEVANCE,
            score=0.80,
            feedback_type=FeedbackType.USER,
            comment="Somewhat relevant to the topic"
        )
        await service.submit_accuracy_feedback(citation.id, feedback2, evaluators[1])
        
        # High availability feedback
        feedback3 = AccuracyFeedback(
            metric_type=MetricType.AVAILABILITY,
            score=0.98,
            feedback_type=FeedbackType.AUTOMATED,
            comment="Source consistently available"
        )
        await service.submit_accuracy_feedback(citation.id, feedback3, evaluators[2])
        
        # Verify citation scores were updated
        test_db.refresh(citation)
        assert citation.accuracy_score == 0.95
        assert citation.relevance_score == 0.80
        assert citation.availability_score == 0.98
        
        # Calculate expected overall quality (weighted average)
        expected_quality = (0.4 * 0.80) + (0.4 * 0.95) + (0.2 * 0.98)
        assert abs(citation.overall_quality_score - expected_quality) < 0.01
    
    @pytest.mark.asyncio
    async def test_citation_usage_analytics(self, test_db):
        """Test comprehensive citation usage analytics."""
        service = CitationService(db=test_db)
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_analytics_test",
            title="Analytics Test Citation",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Track multiple usages across different content types
        users = [uuid4() for _ in range(3)]
        content_ids = [uuid4() for _ in range(4)]
        
        usage_data = [
            (content_ids[0], users[0], ContentType.RESEARCH, 1, "Introduction section"),
            (content_ids[0], users[0], ContentType.RESEARCH, 5, "Methodology section"),
            (content_ids[1], users[1], ContentType.ANALYSIS, 2, "Market analysis"),
            (content_ids[2], users[1], ContentType.REPORT, 1, "Executive summary"),
            (content_ids[3], users[2], ContentType.ARTICLE, 3, "Main content"),
        ]
        
        for content_id, user_id, content_type, position, section in usage_data:
            await service.track_usage(
                citation_id=citation.id,
                content_id=content_id,
                user_id=user_id,
                content_type=content_type,
                position=position,
                context="Test usage context",
                section=section
            )
        
        # Verify usage count updated
        test_db.refresh(citation)
        assert citation.usage_count == 5
        assert citation.last_used is not None
        
        # Verify all usage records were created
        usages = test_db.query(CitationUsage).filter(
            CitationUsage.citation_id == citation.id
        ).all()
        assert len(usages) == 5
        
        # Verify usage across different content types
        content_types = set(usage.content_type for usage in usages)
        expected_types = {ContentType.RESEARCH, ContentType.ANALYSIS, ContentType.REPORT, ContentType.ARTICLE}
        assert content_types == expected_types
    
    @pytest.mark.asyncio
    async def test_advanced_citation_search(self, test_db):
        """Test advanced citation search with multiple filters."""
        service = CitationService(db=test_db)
        
        # Create diverse citations for testing
        citations_data = [
            ("High Quality Academic", SourceType.ACADEMIC, 0.95, VerificationStatus.VERIFIED, ["ai", "research"]),
            ("Medium Web Article", SourceType.WEB, 0.75, VerificationStatus.VERIFIED, ["business", "strategy"]),
            ("Gov Document", SourceType.GOVERNMENT, 0.90, VerificationStatus.VERIFIED, ["policy", "regulation"]),
            ("Low Quality Blog", SourceType.WEB, 0.45, VerificationStatus.FAILED, ["opinion", "blog"]),
            ("Recent News", SourceType.NEWS, 0.80, VerificationStatus.VERIFIED, ["news", "current"]),
            ("Old Academic", SourceType.ACADEMIC, 0.85, VerificationStatus.STALE, ["historical", "research"]),
        ]
        
        citations = []
        base_date = datetime.utcnow()
        
        for i, (title, source_type, quality, status, tags) in enumerate(citations_data):
            citation = Citation(
                id=uuid4(),
                reference_id=f"ref_search_{i:03d}",
                title=title,
                source_type=source_type,
                overall_quality_score=quality,
                verification_status=status,
                access_date=base_date - timedelta(days=i*10),  # Varying ages
                url=f"https://example.com/{title.lower().replace(' ', '-')}",
                excerpt=f"This is an excerpt about {title.lower()}",
                metadata={"tags": tags}
            )
            test_db.add(citation)
            citations.append(citation)
        
        test_db.commit()
        
        # Test search by source type
        academic_params = CitationSearchParams(
            source_types=[SourceType.ACADEMIC],
            limit=10
        )
        academic_results, academic_count = await service.search_citations(academic_params)
        assert academic_count == 2
        assert all(c.source_type == SourceType.ACADEMIC for c in academic_results)
        
        # Test search by quality threshold
        high_quality_params = CitationSearchParams(
            min_quality_score=0.85,
            limit=10
        )
        high_quality_results, hq_count = await service.search_citations(high_quality_params)
        assert hq_count == 3  # Academic (0.95), Gov (0.90), Old Academic (0.85)
        assert all(c.overall_quality_score >= 0.85 for c in high_quality_results)
        
        # Test search by verification status
        verified_params = CitationSearchParams(
            verification_status=VerificationStatus.VERIFIED,
            limit=10
        )
        verified_results, verified_count = await service.search_citations(verified_params)
        assert verified_count == 4
        assert all(c.verification_status == VerificationStatus.VERIFIED for c in verified_results)
        
        # Test search by age
        recent_params = CitationSearchParams(
            max_age_days=25,  # Only citations from last 25 days
            limit=10
        )
        recent_results, recent_count = await service.search_citations(recent_params)
        assert recent_count == 3  # First 3 citations (0, 10, 20 days old)
        
        # Test combined filters
        combined_params = CitationSearchParams(
            query="academic",
            source_types=[SourceType.ACADEMIC, SourceType.WEB],
            min_quality_score=0.70,
            verification_status=VerificationStatus.VERIFIED,
            limit=5
        )
        combined_results, combined_count = await service.search_citations(combined_params)
        assert combined_count == 1  # Only "High Quality Academic" matches all criteria
        assert combined_results[0].title == "High Quality Academic"
    
    @pytest.mark.asyncio
    async def test_citation_collections_management(self, test_db):
        """Test citation collection creation and management."""
        service = CitationService(db=test_db)
        
        # Create citations
        citations = []
        for i in range(5):
            citation = Citation(
                id=uuid4(),
                reference_id=f"ref_collection_{i:03d}",
                title=f"Collection Citation {i}",
                source_type=SourceType.WEB,
                overall_quality_score=0.8 + (i * 0.05)
            )
            test_db.add(citation)
            citations.append(citation)
        test_db.commit()
        
        # Create collection
        owner_id = uuid4()
        collection = CitationCollection(
            id=uuid4(),
            name="Research Project Alpha",
            description="Citations for our main research project",
            owner_id=owner_id,
            tags=["research", "project-alpha"],
            citation_ids=[c.id for c in citations[:3]],  # First 3 citations
            citation_count=3,
            is_public=True
        )
        test_db.add(collection)
        test_db.commit()
        
        # Test collection properties
        assert collection.citation_count == 3
        assert len(collection.citation_ids) == 3
        assert collection.is_public is True
        
        # Calculate average quality score
        included_citations = citations[:3]
        expected_avg_quality = sum(c.overall_quality_score for c in included_citations) / 3
        collection.average_quality_score = expected_avg_quality
        test_db.commit()
        
        assert abs(collection.average_quality_score - expected_avg_quality) < 0.01
    
    @pytest.mark.asyncio
    async def test_stale_citation_identification(self, test_db):
        """Test identification of stale citations needing reverification."""
        service = CitationService(db=test_db)
        
        # Create citations with different verification states
        base_date = datetime.utcnow()
        
        citations_data = [
            ("recent_verified", VerificationStatus.VERIFIED, base_date - timedelta(days=5), False),
            ("old_verified", VerificationStatus.VERIFIED, base_date - timedelta(days=45), False),
            ("marked_stale", VerificationStatus.STALE, base_date - timedelta(days=10), False),
            ("needs_reverification", VerificationStatus.VERIFIED, base_date - timedelta(days=20), True),
            ("never_verified", VerificationStatus.PENDING, None, False),
        ]
        
        citations = []
        for name, status, last_verified, needs_reverif in citations_data:
            citation = Citation(
                id=uuid4(),
                reference_id=f"ref_{name}",
                title=f"Citation {name}",
                source_type=SourceType.WEB,
                url=f"https://example.com/{name}",
                verification_status=status,
                last_verified=last_verified,
                requires_reverification=needs_reverif
            )
            test_db.add(citation)
            citations.append(citation)
        
        test_db.commit()
        
        # Test stale citation identification
        stale_citations = await service.get_stale_citations(
            days_threshold=30,  # 30 days
            limit=10
        )
        
        # Should find: old_verified (45 days), marked_stale, needs_reverification
        assert len(stale_citations) == 3
        
        stale_ref_ids = [c.reference_id for c in stale_citations]
        assert "ref_old_verified" in stale_ref_ids
        assert "ref_marked_stale" in stale_ref_ids
        assert "ref_needs_reverification" in stale_ref_ids
        
        # Recent and never verified should not be included
        assert "ref_recent_verified" not in stale_ref_ids
        assert "ref_never_verified" not in stale_ref_ids


class TestCitationServiceErrorScenarios:
    """Test error scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_verification_timeout_handling(self, test_db, mock_puppeteer_mcp):
        """Test handling of verification timeouts."""
        service = CitationService(
            db=test_db,
            puppeteer_mcp=mock_puppeteer_mcp
        )
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_timeout_test",
            title="Timeout Test Citation",
            source_type=SourceType.WEB,
            url="https://example.com/timeout-test"
        )
        test_db.add(citation)
        test_db.commit()
        
        # Mock timeout exception
        mock_puppeteer_mcp.verify_url.side_effect = asyncio.TimeoutError("Verification timeout")
        
        # Attempt verification
        user_id = uuid4()
        
        with pytest.raises(ServiceUnavailableError):
            await service.verify_citation(citation.id, user_id)
        
        # Verify error was logged
        verification_logs = test_db.query(VerificationLog).filter(
            VerificationLog.citation_id == citation.id
        ).all()
        
        assert len(verification_logs) == 1
        log = verification_logs[0]
        assert log.status == "failed"
        assert log.error_type == "TimeoutError"
        assert "timeout" in log.error_message.lower()
        
        # Citation should be marked as failed
        test_db.refresh(citation)
        assert citation.verification_status == VerificationStatus.FAILED
        assert citation.verification_attempts == 1
        assert citation.availability_score == 0.0
    
    @pytest.mark.asyncio
    async def test_concurrent_citation_usage_tracking(self, test_db):
        """Test handling of concurrent usage tracking attempts."""
        service = CitationService(db=test_db)
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_concurrent_test",
            title="Concurrent Test Citation",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Attempt to track same usage multiple times concurrently
        content_id = uuid4()
        user_id = uuid4()
        
        async def track_same_usage():
            return await service.track_usage(
                citation_id=citation.id,
                content_id=content_id,
                user_id=user_id,
                content_type=ContentType.RESEARCH,
                position=1,
                context="Concurrent test"
            )
        
        # Execute concurrent tracking attempts
        tasks = [track_same_usage() for _ in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Only one should succeed, others should raise ConflictError
        successes = [r for r in results if not isinstance(r, Exception)]
        conflicts = [r for r in results if isinstance(r, ConflictError)]
        
        assert len(successes) == 1
        assert len(conflicts) == 2
        
        # Verify only one usage record was created
        usages = test_db.query(CitationUsage).filter(
            CitationUsage.citation_id == citation.id,
            CitationUsage.content_id == content_id,
            CitationUsage.position == 1
        ).all()
        assert len(usages) == 1
    
    @pytest.mark.asyncio
    async def test_invalid_citation_data_handling(self, test_db):
        """Test handling of invalid citation data."""
        service = CitationService(db=test_db)
        user_id = uuid4()
        
        # Test empty title
        with pytest.raises(ValueError):
            CitationCreate(
                source_type=SourceType.WEB,
                title="",
                url="https://example.com"
            )
        
        # Test whitespace-only title
        with pytest.raises(ValueError):
            CitationCreate(
                source_type=SourceType.WEB,
                title="   ",
                url="https://example.com"
            )
        
        # Test invalid URL format (should be handled by URL validation)
        invalid_citation = Citation(
            id=uuid4(),
            reference_id="ref_invalid",
            title="Invalid Citation",
            source_type=SourceType.WEB,
            url="not-a-valid-url"
        )
        
        # This should raise validation error when saved
        test_db.add(invalid_citation)
        with pytest.raises(Exception):  # Database constraint violation
            test_db.commit()
    
    @pytest.mark.asyncio
    async def test_citation_accuracy_score_edge_cases(self, test_db):
        """Test edge cases in accuracy score calculations."""
        service = CitationService(db=test_db)
        
        # Create citation
        citation = Citation(
            id=uuid4(),
            reference_id="ref_accuracy_edge",
            title="Accuracy Edge Case Citation",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Test extreme scores
        evaluators = [uuid4() for _ in range(3)]
        
        # Submit feedback with boundary scores
        extreme_feedback = [
            (MetricType.ACCURACY, 0.0, FeedbackType.USER),  # Minimum score
            (MetricType.ACCURACY, 1.0, FeedbackType.EXPERT),  # Maximum score
            (MetricType.RELEVANCE, 0.5, FeedbackType.AUTOMATED),  # Middle score
        ]
        
        for i, (metric_type, score, feedback_type) in enumerate(extreme_feedback):
            feedback = AccuracyFeedback(
                metric_type=metric_type,
                score=score,
                feedback_type=feedback_type,
                comment=f"Edge case feedback {i}"
            )
            await service.submit_accuracy_feedback(citation.id, feedback, evaluators[i])
        
        # Verify scores are properly calculated
        test_db.refresh(citation)
        
        # Accuracy should be average of 0.0 and 1.0 = 0.5
        assert abs(citation.accuracy_score - 0.5) < 0.01
        assert citation.relevance_score == 0.5
        # Availability score should remain default (1.0) as no feedback provided
        assert citation.availability_score == 1.0
    
    @pytest.mark.asyncio
    async def test_database_constraint_violations(self, test_db):
        """Test handling of database constraint violations."""
        service = CitationService(db=test_db)
        
        # Create citation with unique reference_id
        reference_id = "ref_unique_test"
        citation1 = Citation(
            id=uuid4(),
            reference_id=reference_id,
            title="First Citation",
            source_type=SourceType.WEB
        )
        test_db.add(citation1)
        test_db.commit()
        
        # Attempt to create another citation with same reference_id
        citation2 = Citation(
            id=uuid4(),
            reference_id=reference_id,  # Duplicate reference_id
            title="Second Citation",
            source_type=SourceType.WEB
        )
        test_db.add(citation2)
        
        # Should raise integrity constraint violation
        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()
    
    @pytest.mark.asyncio
    async def test_citation_search_performance(self, test_db):
        """Test citation search performance with large dataset."""
        service = CitationService(db=test_db)
        
        # Create large number of citations
        citations = []
        base_date = datetime.utcnow()
        
        for i in range(100):  # Create 100 citations
            citation = Citation(
                id=uuid4(),
                reference_id=f"ref_perf_{i:04d}",
                title=f"Performance Test Citation {i}",
                source_type=SourceType.WEB if i % 2 == 0 else SourceType.ACADEMIC,
                overall_quality_score=0.5 + (i % 50) / 100,  # Varying scores
                verification_status=VerificationStatus.VERIFIED if i % 3 == 0 else VerificationStatus.PENDING,
                access_date=base_date - timedelta(days=i),
                url=f"https://example.com/perf-test-{i}",
                excerpt=f"Performance test excerpt {i} with searchable content"
            )
            test_db.add(citation)
            citations.append(citation)
        
        test_db.commit()
        
        # Test search performance
        import time
        
        # Complex search query
        search_params = CitationSearchParams(
            query="performance test",
            source_types=[SourceType.WEB, SourceType.ACADEMIC],
            min_quality_score=0.7,
            max_age_days=50,
            limit=20
        )
        
        start_time = time.time()
        results, total_count = await service.search_citations(search_params)
        end_time = time.time()
        
        search_duration = end_time - start_time
        
        # Search should complete quickly (< 1 second for 100 records)
        assert search_duration < 1.0
        assert len(results) <= 20  # Respects limit
        assert total_count >= 0  # Valid count returned
        
        # Verify results match criteria
        for citation in results:
            assert citation.overall_quality_score >= 0.7
            assert citation.source_type in [SourceType.WEB, SourceType.ACADEMIC]
            days_old = (datetime.utcnow() - citation.access_date).days
            assert days_old <= 50


class TestCitationServiceCaching:
    """Test caching functionality in citation service."""
    
    @pytest.mark.asyncio
    async def test_citation_cache_performance(self, test_db, mock_cache):
        """Test citation caching improves performance."""
        service = CitationService(db=test_db, cache_manager=mock_cache)
        
        # Create citation
        citation_id = uuid4()
        citation = Citation(
            id=citation_id,
            reference_id="ref_cache_perf",
            title="Cache Performance Test",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Mock cache hit
        cached_data = {
            'id': str(citation_id),
            'reference_id': 'ref_cache_perf',
            'title': 'Cache Performance Test',
            'source_type': SourceType.WEB
        }
        
        # First call - cache miss
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        
        result1 = await service.get_citation(citation_id)
        
        # Should have called cache.get and cache.set
        mock_cache.get.assert_called_with(f"citation:{citation_id}")
        mock_cache.set.assert_called()
        
        # Second call - cache hit
        mock_cache.get.return_value = cached_data
        mock_cache.reset_mock()
        
        result2 = await service.get_citation(citation_id)
        
        # Should only have called cache.get, not database
        mock_cache.get.assert_called_once_with(f"citation:{citation_id}")
        mock_cache.set.assert_not_called()
        
        # Results should be equivalent
        assert result2.title == "Cache Performance Test"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_updates(self, test_db, mock_cache):
        """Test cache invalidation when citations are updated."""
        service = CitationService(db=test_db, cache_manager=mock_cache)
        
        # Create citation
        citation_id = uuid4()
        citation = Citation(
            id=citation_id,
            reference_id="ref_cache_invalid",
            title="Original Title",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Update citation
        update_data = CitationUpdate(title="Updated Title")
        user_id = uuid4()
        
        await service.update_citation(citation_id, update_data, user_id)
        
        # Should have invalidated cache
        mock_cache.delete.assert_called_with(f"citation:{citation_id}")
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, test_db, mock_cache):
        """Test cache TTL expiration handling."""
        service = CitationService(db=test_db, cache_manager=mock_cache)
        
        citation_id = uuid4()
        citation = Citation(
            id=citation_id,
            reference_id="ref_cache_ttl",
            title="TTL Test Citation",
            source_type=SourceType.WEB
        )
        test_db.add(citation)
        test_db.commit()
        
        # Mock expired cache entry (returns None)
        mock_cache.get.return_value = None
        
        result = await service.get_citation(citation_id)
        
        # Should fetch from database and update cache
        assert result.title == "TTL Test Citation"
        mock_cache.get.assert_called_with(f"citation:{citation_id}")
        mock_cache.set.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])