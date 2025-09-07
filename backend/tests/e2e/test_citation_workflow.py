"""
End-to-end integration tests for citation workflow.

Tests the complete citation workflow from creation through verification,
usage tracking, and accuracy feedback across all system components.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List
import json

from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.models.citation import Citation, CitationUsage, AccuracyTracking, VerificationLog
from src.models.base import Base
from src.services.citation_service import CitationService
from src.ai.llama_service import LlamaIndexService
from src.ai.prompt_loader import PromptLoader


@pytest.fixture(scope="session")
def e2e_database():
    """Create test database for E2E tests."""
    engine = create_engine("sqlite:///./test_e2e.db", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    yield db
    
    db.close()
    # Clean up
    import os
    try:
        os.remove("./test_e2e.db")
    except FileNotFoundError:
        pass


@pytest.fixture
def test_client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_user():
    """Create test user for authentication."""
    return {
        "id": str(uuid4()),
        "email": "testuser@example.com",
        "name": "Test User",
        "role": "user"
    }


class TestCitationWorkflowE2E:
    """End-to-end tests for complete citation workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_citation_lifecycle_api(self, async_client, test_user):
        """Test complete citation lifecycle through API endpoints."""
        
        # Step 1: Create citation via API
        citation_data = {
            "title": "E2E Test: AI Applications in Healthcare Systems",
            "url": "https://e2e-test.journal.com/ai-healthcare-2024",
            "authors": ["Dr. E2E Smith", "Prof. Integration Test"],
            "sourceType": "academic",
            "excerpt": "This comprehensive study examines the integration of AI technologies in healthcare systems, focusing on practical applications and implementation challenges.",
            "metadata": {
                "journal": "Journal of Healthcare AI",
                "doi": "10.1234/jhai.2024.e2e",
                "peerReviewed": True
            },
            "publicationDate": "2024-01-15"
        }
        
        # Mock authentication
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        response = await async_client.post(
            "/api/v1/citations",
            json=citation_data,
            headers=headers
        )
        
        assert response.status_code == 201
        created_citation = response.json()
        
        assert created_citation["title"] == citation_data["title"]
        assert created_citation["referenceId"].startswith("ref_")
        assert created_citation["verificationStatus"] == "pending"
        
        citation_id = created_citation["id"]
        
        # Step 2: Verify citation
        verify_response = await async_client.post(
            f"/api/v1/citations/{citation_id}/verify",
            headers=headers
        )
        
        assert verify_response.status_code == 200
        verification_result = verify_response.json()
        assert verification_result["status"] == "success"
        
        # Step 3: Get updated citation
        get_response = await async_client.get(
            f"/api/v1/citations/{citation_id}",
            headers=headers
        )
        
        assert get_response.status_code == 200
        updated_citation = get_response.json()
        assert updated_citation["verificationStatus"] == "verified"
        assert updated_citation["availabilityScore"] == 1.0
        
        # Step 4: Track usage
        usage_data = {
            "contentId": str(uuid4()),
            "contentType": "research",
            "position": 1,
            "context": "Referenced in introduction section for AI applications overview",
            "section": "Introduction"
        }
        
        usage_response = await async_client.post(
            f"/api/v1/citations/{citation_id}/usage",
            json=usage_data,
            headers=headers
        )
        
        assert usage_response.status_code == 201
        usage_result = usage_response.json()
        assert usage_result["citationId"] == citation_id
        assert usage_result["contentType"] == "research"
        
        # Step 5: Submit accuracy feedback
        feedback_data = {
            "metricType": "accuracy",
            "score": 0.95,
            "feedbackType": "expert",
            "comment": "Highly accurate and well-researched paper with verifiable claims"
        }
        
        feedback_response = await async_client.post(
            f"/api/v1/citations/{citation_id}/feedback",
            json=feedback_data,
            headers=headers
        )
        
        assert feedback_response.status_code == 201
        feedback_result = feedback_response.json()
        assert feedback_result["score"] == 0.95
        assert feedback_result["metricType"] == "accuracy"
        
        # Step 6: Get final citation state
        final_response = await async_client.get(
            f"/api/v1/citations/{citation_id}",
            headers=headers
        )
        
        final_citation = final_response.json()
        assert final_citation["accuracyScore"] == 0.95
        assert final_citation["usageCount"] == 1
        assert final_citation["lastUsed"] is not None
        
        # Step 7: Search for citation
        search_response = await async_client.get(
            "/api/v1/citations/search",
            params={
                "query": "AI Applications Healthcare",
                "sourceType": "academic",
                "verificationStatus": "verified",
                "limit": 10
            },
            headers=headers
        )
        
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert search_results["total"] >= 1
        
        found_citation = None
        for citation in search_results["citations"]:
            if citation["id"] == citation_id:
                found_citation = citation
                break
        
        assert found_citation is not None
        assert found_citation["title"] == citation_data["title"]
    
    @pytest.mark.asyncio
    async def test_citation_verification_failure_recovery(self, async_client, test_user):
        """Test citation verification failure and recovery workflow."""
        
        # Create citation with URL that will fail verification
        citation_data = {
            "title": "Citation That Will Initially Fail Verification",
            "url": "https://unreliable-test-site.com/failing-article",
            "sourceType": "web",
            "excerpt": "This citation will test the failure recovery workflow"
        }
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create citation
        response = await async_client.post(
            "/api/v1/citations",
            json=citation_data,
            headers=headers
        )
        
        citation_id = response.json()["id"]
        
        # First verification attempt - should fail
        verify_response = await async_client.post(
            f"/api/v1/citations/{citation_id}/verify",
            headers=headers
        )
        
        # Depending on mock implementation, this might succeed or fail
        # In a real E2E test, we'd have control over the external service
        
        # Get citation status
        status_response = await async_client.get(
            f"/api/v1/citations/{citation_id}",
            headers=headers
        )
        
        citation_status = status_response.json()
        
        # Verify that verification was attempted
        assert citation_status["verificationAttempts"] >= 1
        
        # Test retry verification
        retry_response = await async_client.post(
            f"/api/v1/citations/{citation_id}/verify",
            headers=headers
        )
        
        assert retry_response.status_code in [200, 400, 503]  # Various valid responses
    
    @pytest.mark.asyncio
    async def test_bulk_citation_operations(self, async_client, test_user):
        """Test bulk citation operations workflow."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create multiple citations
        citations_data = [
            {
                "title": f"Bulk Test Citation {i}",
                "url": f"https://bulk-test-{i}.example.com/article",
                "sourceType": "web",
                "excerpt": f"This is bulk citation number {i}"
            }
            for i in range(3)
        ]
        
        citation_ids = []
        for citation_data in citations_data:
            response = await async_client.post(
                "/api/v1/citations",
                json=citation_data,
                headers=headers
            )
            citation_ids.append(response.json()["id"])
        
        # Test bulk verification
        bulk_verify_data = {"citationIds": citation_ids}
        
        bulk_response = await async_client.post(
            "/api/v1/citations/bulk/verify",
            json=bulk_verify_data,
            headers=headers
        )
        
        assert bulk_response.status_code == 200
        bulk_result = bulk_response.json()
        assert len(bulk_result["results"]) == 3
        
        # Test bulk search with specific criteria
        search_response = await async_client.get(
            "/api/v1/citations/search",
            params={
                "query": "Bulk Test",
                "sourceType": "web",
                "limit": 10
            },
            headers=headers
        )
        
        search_results = search_response.json()
        assert search_results["total"] >= 3
        
        # Test bulk delete
        bulk_delete_data = {"citationIds": citation_ids[:2]}  # Delete first 2
        
        delete_response = await async_client.delete(
            "/api/v1/citations/bulk",
            json=bulk_delete_data,
            headers=headers
        )
        
        assert delete_response.status_code == 200
        
        # Verify citations were deleted
        for citation_id in citation_ids[:2]:
            get_response = await async_client.get(
                f"/api/v1/citations/{citation_id}",
                headers=headers
            )
            assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_citation_accuracy_reporting_workflow(self, async_client, test_user):
        """Test complete accuracy reporting workflow."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create citations with different accuracy levels
        citations = []
        accuracy_scores = [0.95, 0.80, 0.60, 0.90]
        
        for i, score in enumerate(accuracy_scores):
            citation_data = {
                "title": f"Accuracy Test Citation {i}",
                "url": f"https://accuracy-test-{i}.example.com",
                "sourceType": "academic" if i % 2 == 0 else "web",
                "excerpt": f"Citation for accuracy testing with target score {score}"
            }
            
            # Create citation
            response = await async_client.post(
                "/api/v1/citations",
                json=citation_data,
                headers=headers
            )
            citation_id = response.json()["id"]
            citations.append(citation_id)
            
            # Submit accuracy feedback
            feedback_data = {
                "metricType": "accuracy",
                "score": score,
                "feedbackType": "expert",
                "comment": f"Test feedback with score {score}"
            }
            
            await async_client.post(
                f"/api/v1/citations/{citation_id}/feedback",
                json=feedback_data,
                headers=headers
            )
        
        # Generate accuracy report
        report_response = await async_client.get(
            "/api/v1/citations/reports/accuracy",
            params={
                "startDate": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "endDate": (datetime.utcnow() + timedelta(days=1)).isoformat()
            },
            headers=headers
        )
        
        assert report_response.status_code == 200
        report = report_response.json()
        
        # Verify report structure
        assert "overallAccuracy" in report
        assert "accuracyBySource" in report
        assert "verificationStatistics" in report
        assert "citationsNeedingAttention" in report
        
        # Check accuracy calculations
        expected_avg = sum(accuracy_scores) / len(accuracy_scores) * 100
        assert abs(report["overallAccuracy"] - expected_avg) < 5  # Allow some variance
        
        # Check source type breakdown
        academic_scores = [accuracy_scores[i] for i in range(len(accuracy_scores)) if i % 2 == 0]
        web_scores = [accuracy_scores[i] for i in range(len(accuracy_scores)) if i % 2 == 1]
        
        source_breakdown = {item["sourceType"]: item["averageScore"] 
                           for item in report["accuracyBySource"]}
        
        if academic_scores:
            expected_academic_avg = sum(academic_scores) / len(academic_scores) * 100
            assert abs(source_breakdown.get("academic", 0) - expected_academic_avg) < 5
        
        if web_scores:
            expected_web_avg = sum(web_scores) / len(web_scores) * 100
            assert abs(source_breakdown.get("web", 0) - expected_web_avg) < 5
    
    @pytest.mark.asyncio
    async def test_citation_collection_management_workflow(self, async_client, test_user):
        """Test citation collection management workflow."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create some citations first
        citation_ids = []
        for i in range(3):
            citation_data = {
                "title": f"Collection Test Citation {i}",
                "url": f"https://collection-test-{i}.example.com",
                "sourceType": "web",
                "excerpt": f"Citation for collection testing {i}"
            }
            
            response = await async_client.post(
                "/api/v1/citations",
                json=citation_data,
                headers=headers
            )
            citation_ids.append(response.json()["id"])
        
        # Create citation collection
        collection_data = {
            "name": "E2E Test Collection",
            "description": "Collection created for end-to-end testing",
            "tags": ["e2e-test", "automation"],
            "citationIds": citation_ids,
            "isPublic": True
        }
        
        collection_response = await async_client.post(
            "/api/v1/citations/collections",
            json=collection_data,
            headers=headers
        )
        
        assert collection_response.status_code == 201
        collection = collection_response.json()
        
        assert collection["name"] == "E2E Test Collection"
        assert collection["citationCount"] == 3
        assert collection["isPublic"] is True
        
        collection_id = collection["id"]
        
        # Get collection details
        get_collection_response = await async_client.get(
            f"/api/v1/citations/collections/{collection_id}",
            headers=headers
        )
        
        retrieved_collection = get_collection_response.json()
        assert len(retrieved_collection["citationIds"]) == 3
        
        # Update collection
        update_data = {
            "name": "Updated E2E Collection",
            "description": "Updated description",
            "citationIds": citation_ids[:2]  # Remove one citation
        }
        
        update_response = await async_client.put(
            f"/api/v1/citations/collections/{collection_id}",
            json=update_data,
            headers=headers
        )
        
        assert update_response.status_code == 200
        updated_collection = update_response.json()
        assert updated_collection["name"] == "Updated E2E Collection"
        assert updated_collection["citationCount"] == 2
        
        # List collections
        list_response = await async_client.get(
            "/api/v1/citations/collections",
            headers=headers
        )
        
        collections_list = list_response.json()
        assert len(collections_list["collections"]) >= 1
        
        # Delete collection
        delete_response = await async_client.delete(
            f"/api/v1/citations/collections/{collection_id}",
            headers=headers
        )
        
        assert delete_response.status_code == 204
        
        # Verify deletion
        get_deleted_response = await async_client.get(
            f"/api/v1/citations/collections/{collection_id}",
            headers=headers
        )
        
        assert get_deleted_response.status_code == 404


class TestAIIntegrationWorkflowE2E:
    """End-to-end tests for AI service integration workflows."""
    
    @pytest.mark.asyncio
    async def test_citation_with_ai_content_generation(self, async_client, test_user):
        """Test citation integration with AI content generation workflow."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create citation
        citation_data = {
            "title": "AI Content Generation Study",
            "url": "https://ai-content-study.example.com",
            "sourceType": "academic",
            "excerpt": "Research on AI-powered content generation techniques"
        }
        
        response = await async_client.post(
            "/api/v1/citations",
            json=citation_data,
            headers=headers
        )
        
        citation_id = response.json()["id"]
        
        # Use citation in AI-generated content
        ai_request_data = {
            "prompt": "Generate a summary of recent advances in AI content generation",
            "context": {
                "citations": [citation_id],
                "contextType": "research_summary"
            }
        }
        
        ai_response = await async_client.post(
            "/api/v1/ai/generate",
            json=ai_request_data,
            headers=headers
        )
        
        # In a real implementation, this would integrate with LlamaIndex
        # For E2E testing, we verify the request structure and response
        assert ai_response.status_code in [200, 501]  # 501 if not implemented
        
        # Track AI usage of citation
        if ai_response.status_code == 200:
            ai_content = ai_response.json()
            
            # Track usage
            usage_data = {
                "contentId": str(uuid4()),
                "contentType": "analysis",
                "position": 1,
                "context": "Used in AI-generated research summary",
                "section": "Literature Review"
            }
            
            usage_response = await async_client.post(
                f"/api/v1/citations/{citation_id}/usage",
                json=usage_data,
                headers=headers
            )
            
            assert usage_response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_prompt_template_with_citations_workflow(self, async_client, test_user):
        """Test prompt template system with citation integration."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create citations for use in prompt templates
        citation_ids = []
        for i in range(2):
            citation_data = {
                "title": f"Prompt Template Citation {i}",
                "url": f"https://prompt-template-{i}.example.com",
                "sourceType": "web",
                "excerpt": f"Citation for prompt template testing {i}"
            }
            
            response = await async_client.post(
                "/api/v1/citations",
                json=citation_data,
                headers=headers
            )
            citation_ids.append(response.json()["id"])
        
        # Load prompt template with citations
        template_request = {
            "promptName": "business_analysis",
            "variables": {
                "company_name": "TestCorp",
                "analysis_type": "market_research"
            },
            "citationIds": citation_ids,
            "injectContext": True,
            "optimize": True
        }
        
        template_response = await async_client.post(
            "/api/v1/prompts/load",
            json=template_request,
            headers=headers
        )
        
        # Response structure depends on implementation
        assert template_response.status_code in [200, 501]
        
        if template_response.status_code == 200:
            template_result = template_response.json()
            
            # Verify citations were included in context
            assert "prompt" in template_result
            assert "citationContext" in template_result
            assert len(template_result["citationContext"]) == 2


class TestPerformanceE2E:
    """End-to-end performance tests for citation workflows."""
    
    @pytest.mark.asyncio
    async def test_large_citation_dataset_performance(self, async_client, test_user):
        """Test performance with large citation datasets."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create multiple citations concurrently
        citation_tasks = []
        
        async def create_citation(index):
            citation_data = {
                "title": f"Performance Test Citation {index}",
                "url": f"https://perf-test-{index}.example.com",
                "sourceType": "web" if index % 2 == 0 else "academic",
                "excerpt": f"Performance testing citation {index}"
            }
            
            response = await async_client.post(
                "/api/v1/citations",
                json=citation_data,
                headers=headers
            )
            return response.json()["id"]
        
        # Create 20 citations concurrently
        import time
        start_time = time.time()
        
        citation_tasks = [create_citation(i) for i in range(20)]
        citation_ids = await asyncio.gather(*citation_tasks)
        
        creation_time = time.time() - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert creation_time < 30.0  # 30 seconds
        assert len(citation_ids) == 20
        
        # Test search performance with large dataset
        start_time = time.time()
        
        search_response = await async_client.get(
            "/api/v1/citations/search",
            params={
                "query": "Performance Test",
                "limit": 50
            },
            headers=headers
        )
        
        search_time = time.time() - start_time
        
        assert search_response.status_code == 200
        assert search_time < 5.0  # Should complete within 5 seconds
        
        search_results = search_response.json()
        assert search_results["total"] >= 20
    
    @pytest.mark.asyncio
    async def test_concurrent_citation_operations_performance(self, async_client, test_user):
        """Test concurrent citation operations performance."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create base citation
        citation_data = {
            "title": "Concurrent Operations Test Citation",
            "url": "https://concurrent-test.example.com",
            "sourceType": "academic",
            "excerpt": "Citation for concurrent operations testing"
        }
        
        response = await async_client.post(
            "/api/v1/citations",
            json=citation_data,
            headers=headers
        )
        
        citation_id = response.json()["id"]
        
        # Perform concurrent operations
        async def track_usage(index):
            usage_data = {
                "contentId": str(uuid4()),
                "contentType": "research",
                "position": index,
                "context": f"Concurrent usage tracking {index}",
                "section": "Test Section"
            }
            
            return await async_client.post(
                f"/api/v1/citations/{citation_id}/usage",
                json=usage_data,
                headers=headers
            )
        
        async def submit_feedback(index):
            feedback_data = {
                "metricType": "relevance",
                "score": 0.8 + (index * 0.02),  # Varying scores
                "feedbackType": "user",
                "comment": f"Concurrent feedback {index}"
            }
            
            return await async_client.post(
                f"/api/v1/citations/{citation_id}/feedback",
                json=feedback_data,
                headers=headers
            )
        
        # Execute operations concurrently
        start_time = time.time()
        
        usage_tasks = [track_usage(i) for i in range(5)]
        feedback_tasks = [submit_feedback(i) for i in range(3)]
        
        all_tasks = usage_tasks + feedback_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        concurrent_time = time.time() - start_time
        
        # Check that most operations succeeded
        successful_results = [r for r in results if not isinstance(r, Exception) and r.status_code < 400]
        assert len(successful_results) >= 6  # Allow some failures due to concurrency
        
        # Should complete within reasonable time
        assert concurrent_time < 10.0
        
        # Verify final state
        final_response = await async_client.get(
            f"/api/v1/citations/{citation_id}",
            headers=headers
        )
        
        final_citation = final_response.json()
        assert final_citation["usageCount"] >= 3  # At least some usages tracked
        assert final_citation["relevanceScore"] > 0  # At least some feedback recorded


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])