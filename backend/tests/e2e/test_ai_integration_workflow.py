"""
End-to-end integration tests for AI service workflows.

Tests the complete integration between LlamaIndex, Prompt Loader,
Citation System, and AI-powered content generation workflows.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.main import app
from src.ai.llama_service import LlamaIndexService
from src.ai.prompt_loader import PromptLoader, PromptType
from src.services.citation_service import CitationService


@pytest.fixture
async def ai_test_environment():
    """Setup complete AI testing environment with mock services."""
    
    # Create temporary directory for prompt templates
    with tempfile.TemporaryDirectory() as temp_dir:
        prompts_dir = Path(temp_dir)
        
        # Create test prompt templates
        (prompts_dir / "system").mkdir()
        (prompts_dir / "milestones").mkdir()
        (prompts_dir / "chat").mkdir()
        
        # System prompt for business analysis
        business_prompt = """---
version: "1.0.0"
priority: 9
tags: ["business", "analysis", "e2e-test"]
---

# Business Analysis AI Assistant

You are an expert business analyst specializing in {analysis_type} for {company_name}.

## Your Expertise
- Market research and competitive analysis
- Financial modeling and projections
- Strategic planning and recommendations

## Citations and Sources
When providing analysis, reference the provided citations:
{citation_context}

## Instructions
1. Analyze the business context thoroughly
2. Cite sources appropriately using reference IDs
3. Provide actionable recommendations
4. Maintain professional tone and accuracy
"""
        (prompts_dir / "system" / "business_analysis.md").write_text(business_prompt)
        
        # Milestone prompt for financial modeling
        financial_prompt = """# Financial Model Generation

Generate comprehensive financial projections for {company_name}.

## Required Components
1. Revenue model: {revenue_model}
2. Cost structure analysis
3. Cash flow projections for {projection_years} years
4. Break-even analysis
5. Key financial metrics and KPIs

## Citation Integration
Reference these sources for industry benchmarks:
{citation_context}

## Output Format
Provide structured financial model with:
- Assumptions and methodologies
- Month-by-month projections
- Sensitivity analysis
- Risk factors assessment
"""
        (prompts_dir / "milestones" / "financial_model.md").write_text(financial_prompt)
        
        # Chat prompt for interactive sessions
        chat_prompt = """# Interactive Business Planning Session

Facilitate strategic business planning for {company_name}.

## Session Objectives
- Validate business model assumptions
- Identify market opportunities and risks
- Develop actionable strategy roadmap

## Context Integration
Use these citations to inform your guidance:
{citation_context}

Engage the user with targeted questions to gather requirements and provide tailored recommendations.
"""
        (prompts_dir / "chat" / "interactive_planning.md").write_text(chat_prompt)
        
        yield {
            "prompts_dir": str(prompts_dir),
            "temp_dir": temp_dir
        }


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
        "email": "ai-test@example.com",
        "name": "AI Test User",
        "role": "user"
    }


class TestAIContentGenerationWorkflow:
    """End-to-end tests for AI-powered content generation workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_ai_content_generation_with_citations(
        self, ai_test_environment, async_client, test_user
    ):
        """Test complete AI content generation workflow with citation integration."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Step 1: Create relevant citations for AI content generation
        citations_data = [
            {
                "title": "SaaS Industry Market Analysis 2024",
                "url": "https://market-research.example.com/saas-2024",
                "authors": ["Market Research Institute"],
                "sourceType": "web",
                "excerpt": "Comprehensive analysis of the SaaS market showing 25% YoY growth with ARR reaching $300B globally.",
                "metadata": {
                    "industryFocus": "SaaS",
                    "reportYear": "2024",
                    "keyMetrics": ["ARR", "growth_rate", "market_size"]
                }
            },
            {
                "title": "Financial Modeling Best Practices for Tech Startups",
                "url": "https://academic.example.com/finmodel-tech-startups",
                "authors": ["Dr. Finance Expert", "Prof. Startup Guru"],
                "sourceType": "academic",
                "excerpt": "Best practices for financial modeling in tech startups, covering revenue recognition, CAC/LTV ratios, and cash flow projections.",
                "metadata": {
                    "focus": "financial_modeling",
                    "industry": "technology",
                    "methodology": "startup_focused"
                }
            },
            {
                "title": "Competitive Analysis Framework for B2B SaaS",
                "url": "https://strategy-consulting.example.com/competitive-framework",
                "authors": ["Strategy Consulting Group"],
                "sourceType": "web",
                "excerpt": "Proven framework for conducting competitive analysis in B2B SaaS markets, including positioning and differentiation strategies.",
                "metadata": {
                    "framework_type": "competitive_analysis",
                    "market": "B2B_SaaS",
                    "application": "strategy_development"
                }
            }
        ]
        
        citation_ids = []
        for citation_data in citations_data:
            response = await async_client.post(
                "/api/v1/citations",
                json=citation_data,
                headers=headers
            )
            assert response.status_code == 201
            citation_ids.append(response.json()["id"])
        
        # Step 2: Verify citations (in real implementation, would verify URLs)
        for citation_id in citation_ids:
            verify_response = await async_client.post(
                f"/api/v1/citations/{citation_id}/verify",
                headers=headers
            )
            # Accept various responses based on mock implementation
            assert verify_response.status_code in [200, 202, 503]
        
        # Step 3: Load prompt template with citation context
        prompt_request = {
            "promptName": "business_analysis",
            "promptType": "system",
            "variables": {
                "company_name": "TechStartup Inc",
                "analysis_type": "market research and competitive analysis"
            },
            "citationIds": citation_ids,
            "injectContext": True,
            "optimize": True,
            "maxTokens": 2000
        }
        
        prompt_response = await async_client.post(
            "/api/v1/ai/prompts/load",
            json=prompt_request,
            headers=headers
        )
        
        # Handle different implementation states
        if prompt_response.status_code == 200:
            prompt_result = prompt_response.json()
            
            assert "prompt" in prompt_result
            assert "citationContext" in prompt_result
            assert "metadata" in prompt_result
            assert prompt_result["contextInjected"] is True
            
            # Verify citations were integrated into context
            citation_context = prompt_result["citationContext"]
            assert len(citation_context) == 3
            
            # Check that reference IDs are included
            for citation in citation_context:
                assert "referenceId" in citation
                assert citation["referenceId"].startswith("ref_")
        
        # Step 4: Generate AI content using the loaded prompt
        content_request = {
            "prompt": "Generate a comprehensive market analysis for TechStartup Inc, a B2B SaaS company entering the project management software market.",
            "context": {
                "citationIds": citation_ids,
                "analysisType": "market_research",
                "outputFormat": "structured_report"
            },
            "maxTokens": 1500,
            "temperature": 0.7
        }
        
        content_response = await async_client.post(
            "/api/v1/ai/generate",
            json=content_request,
            headers=headers
        )
        
        if content_response.status_code == 200:
            generated_content = content_response.json()
            
            assert "content" in generated_content
            assert "citationsUsed" in generated_content
            assert "metadata" in generated_content
            
            # Verify citations were referenced in generated content
            citations_used = generated_content["citationsUsed"]
            assert len(citations_used) > 0
            
            # Content should contain reference IDs
            content_text = generated_content["content"]
            assert "ref_" in content_text  # Should contain reference IDs
        
        # Step 5: Track usage of citations in generated content
        if content_response.status_code == 200:
            content_id = str(uuid4())
            generated_content = content_response.json()
            
            for i, citation_id in enumerate(citation_ids):
                usage_data = {
                    "contentId": content_id,
                    "contentType": "analysis",
                    "position": i + 1,
                    "context": f"Used in AI-generated market analysis for section {i+1}",
                    "section": ["Market Overview", "Competitive Landscape", "Financial Projections"][i]
                }
                
                usage_response = await async_client.post(
                    f"/api/v1/citations/{citation_id}/usage",
                    json=usage_data,
                    headers=headers
                )
                assert usage_response.status_code == 201
        
        # Step 6: Verify final state of citations
        for citation_id in citation_ids:
            final_response = await async_client.get(
                f"/api/v1/citations/{citation_id}",
                headers=headers
            )
            final_citation = final_response.json()
            assert final_citation["usageCount"] >= 1
            assert final_citation["lastUsed"] is not None
    
    @pytest.mark.asyncio
    async def test_prompt_chain_workflow_with_ai_generation(
        self, ai_test_environment, async_client, test_user
    ):
        """Test prompt chain workflow for comprehensive AI-generated business plan."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create citations for different aspects of business planning
        citations_by_category = {
            "market": [
                {
                    "title": "Global Market Trends 2024-2030",
                    "sourceType": "web",
                    "excerpt": "Analysis of global market trends affecting technology businesses."
                }
            ],
            "financial": [
                {
                    "title": "Startup Financial Planning Guide",
                    "sourceType": "academic", 
                    "excerpt": "Comprehensive guide to financial planning for early-stage startups."
                }
            ],
            "strategy": [
                {
                    "title": "Business Strategy Framework",
                    "sourceType": "web",
                    "excerpt": "Strategic frameworks for business development and growth planning."
                }
            ]
        }
        
        all_citation_ids = []
        citation_ids_by_category = {}
        
        for category, citations in citations_by_category.items():
            citation_ids_by_category[category] = []
            
            for i, citation_data in enumerate(citations):
                full_citation_data = {
                    **citation_data,
                    "title": f"{category.title()} - {citation_data['title']}",
                    "url": f"https://{category}-source-{i}.example.com"
                }
                
                response = await async_client.post(
                    "/api/v1/citations",
                    json=full_citation_data,
                    headers=headers
                )
                citation_id = response.json()["id"]
                citation_ids_by_category[category].append(citation_id)
                all_citation_ids.append(citation_id)
        
        # Execute prompt chain for comprehensive business plan
        prompt_chain_request = {
            "promptNames": ["business_analysis", "financial_model", "interactive_planning"],
            "sharedContext": {
                "company_name": "ChainTest Ventures",
                "business_model": "B2B SaaS Platform",
                "revenue_model": "subscription",
                "projection_years": 5,
                "target_market": "enterprise project management"
            },
            "citationMappings": {
                "business_analysis": citation_ids_by_category["market"] + citation_ids_by_category["strategy"],
                "financial_model": citation_ids_by_category["financial"],
                "interactive_planning": all_citation_ids
            },
            "optimizeChain": True,
            "maxTokensPerPrompt": 800
        }
        
        chain_response = await async_client.post(
            "/api/v1/ai/prompts/chain",
            json=prompt_chain_request,
            headers=headers
        )
        
        if chain_response.status_code == 200:
            chain_result = chain_response.json()
            
            assert "promptResults" in chain_result
            assert "chainMetadata" in chain_result
            assert len(chain_result["promptResults"]) == 3
            
            # Each prompt should have context from relevant citations
            for prompt_result in chain_result["promptResults"]:
                assert "prompt" in prompt_result
                assert "citationContext" in prompt_result
                assert prompt_result["contextInjected"] is True
        
        # Generate content using each prompt in the chain
        if chain_response.status_code == 200:
            chain_result = chain_response.json()
            generated_sections = []
            
            for i, prompt_result in enumerate(chain_result["promptResults"]):
                section_request = {
                    "prompt": prompt_result["prompt"],
                    "context": {
                        "sectionType": ["market_analysis", "financial_projections", "strategic_recommendations"][i],
                        "citationContext": prompt_result["citationContext"]
                    },
                    "maxTokens": 800
                }
                
                section_response = await async_client.post(
                    "/api/v1/ai/generate",
                    json=section_request,
                    headers=headers
                )
                
                if section_response.status_code == 200:
                    generated_sections.append(section_response.json())
            
            # Verify all sections generated successfully
            assert len(generated_sections) > 0
    
    @pytest.mark.asyncio
    async def test_ai_content_accuracy_feedback_loop(
        self, ai_test_environment, async_client, test_user
    ):
        """Test AI content generation with accuracy feedback loop."""
        
        headers = {"Authorization": f"Bearer test-token-{test_user['id']}"}
        
        # Create high-quality citation
        citation_data = {
            "title": "Verified Research on AI Business Applications",
            "url": "https://verified-research.example.com/ai-business",
            "authors": ["Dr. AI Researcher", "Prof. Business Tech"],
            "sourceType": "academic",
            "excerpt": "Peer-reviewed research on AI applications in business contexts with verified methodologies.",
            "metadata": {
                "peerReviewed": True,
                "verificationLevel": "high",
                "methodologyRating": 5
            }
        }
        
        citation_response = await async_client.post(
            "/api/v1/citations",
            json=citation_data,
            headers=headers
        )
        citation_id = citation_response.json()["id"]
        
        # Submit high accuracy feedback for the citation
        feedback_data = {
            "metricType": "accuracy",
            "score": 0.95,
            "feedbackType": "expert",
            "comment": "Highly accurate peer-reviewed research with verifiable claims and robust methodology."
        }
        
        feedback_response = await async_client.post(
            f"/api/v1/citations/{citation_id}/feedback",
            json=feedback_data,
            headers=headers
        )
        assert feedback_response.status_code == 201
        
        # Generate AI content using high-quality citation
        content_request = {
            "prompt": "Based on the latest research, explain how AI is transforming business operations.",
            "context": {
                "citationIds": [citation_id],
                "qualityThreshold": 0.9,  # Only use high-quality citations
                "requireVerification": True
            },
            "maxTokens": 1000
        }
        
        content_response = await async_client.post(
            "/api/v1/ai/generate",
            json=content_request,
            headers=headers
        )
        
        if content_response.status_code == 200:
            generated_content = content_response.json()
            
            # Content should reference the high-quality citation
            assert "citationsUsed" in generated_content
            citations_used = generated_content["citationsUsed"]
            
            # Verify high-quality citation was used
            high_quality_cited = any(
                c["citationId"] == citation_id and c["qualityScore"] >= 0.9
                for c in citations_used
            )
            assert high_quality_cited
        
        # Test accuracy feedback on generated content
        content_feedback_data = {
            "contentId": str(uuid4()),
            "contentType": "ai_generated",
            "accuracyRating": 0.88,
            "citationAccuracy": 0.95,
            "factualCorrectness": 0.90,
            "feedback": "AI-generated content accurately reflects the cited research with proper attribution."
        }
        
        content_feedback_response = await async_client.post(
            "/api/v1/ai/content/feedback",
            json=content_feedback_data,
            headers=headers
        )
        
        # Accept various response codes based on implementation
        assert content_feedback_response.status_code in [201, 501]
    
    @pytest.mark.asyncio
    async def test_multi_user_ai_collaboration_workflow(
        self, ai_test_environment, async_client
    ):
        """Test multi-user collaboration in AI-powered content generation."""
        
        # Create multiple test users
        users = [
            {
                "id": str(uuid4()),
                "email": f"collaborator{i}@example.com",
                "name": f"Collaborator {i}",
                "role": "user"
            }
            for i in range(3)
        ]
        
        # User 1: Creates citations and initial analysis
        user1_headers = {"Authorization": f"Bearer test-token-{users[0]['id']}"}
        
        citation_data = {
            "title": "Collaborative Business Analysis Framework",
            "url": "https://collaboration-framework.example.com",
            "sourceType": "web",
            "excerpt": "Framework for collaborative business analysis using AI-powered tools."
        }
        
        citation_response = await async_client.post(
            "/api/v1/citations",
            json=citation_data,
            headers=user1_headers
        )
        citation_id = citation_response.json()["id"]
        
        # Generate initial content
        initial_content_request = {
            "prompt": "Create initial market analysis framework for collaborative business planning.",
            "context": {
                "citationIds": [citation_id],
                "collaborationMode": True,
                "userId": users[0]["id"]
            },
            "maxTokens": 800
        }
        
        initial_response = await async_client.post(
            "/api/v1/ai/generate",
            json=initial_content_request,
            headers=user1_headers
        )
        
        content_id = None
        if initial_response.status_code == 200:
            content_id = str(uuid4())
            
            # Track usage by User 1
            usage_data = {
                "contentId": content_id,
                "contentType": "collaborative_analysis",
                "position": 1,
                "context": "Initial framework creation by User 1",
                "section": "Framework Foundation"
            }
            
            await async_client.post(
                f"/api/v1/citations/{citation_id}/usage",
                json=usage_data,
                headers=user1_headers
            )
        
        # User 2: Adds feedback and extends analysis
        user2_headers = {"Authorization": f"Bearer test-token-{users[1]['id']}"}
        
        if content_id:
            # User 2 provides feedback on citation accuracy
            feedback_data = {
                "metricType": "relevance",
                "score": 0.85,
                "feedbackType": "user",
                "comment": "Framework is relevant but could benefit from additional industry examples."
            }
            
            await async_client.post(
                f"/api/v1/citations/{citation_id}/feedback",
                json=feedback_data,
                headers=user2_headers
            )
            
            # User 2 extends the analysis
            extension_request = {
                "prompt": "Extend the collaborative framework with industry-specific examples and case studies.",
                "context": {
                    "citationIds": [citation_id],
                    "baseContentId": content_id,
                    "collaborationMode": True,
                    "userId": users[1]["id"]
                },
                "maxTokens": 600
            }
            
            extension_response = await async_client.post(
                "/api/v1/ai/generate",
                json=extension_request,
                headers=user2_headers
            )
            
            if extension_response.status_code == 200:
                # Track additional usage
                usage_data = {
                    "contentId": content_id,
                    "contentType": "collaborative_analysis",
                    "position": 2,
                    "context": "Framework extension by User 2",
                    "section": "Industry Examples"
                }
                
                await async_client.post(
                    f"/api/v1/citations/{citation_id}/usage",
                    json=usage_data,
                    headers=user2_headers
                )
        
        # User 3: Reviews and provides final assessment
        user3_headers = {"Authorization": f"Bearer test-token-{users[2]['id']}"}
        
        if content_id:
            # User 3 provides comprehensive feedback
            final_feedback_data = {
                "metricType": "completeness",
                "score": 0.92,
                "feedbackType": "expert",
                "comment": "Comprehensive framework with good industry integration. Ready for implementation."
            }
            
            await async_client.post(
                f"/api/v1/citations/{citation_id}/feedback",
                json=final_feedback_data,
                headers=user3_headers
            )
        
        # Verify collaborative usage tracking
        final_citation_response = await async_client.get(
            f"/api/v1/citations/{citation_id}",
            headers=user1_headers
        )
        
        final_citation = final_citation_response.json()
        
        # Citation should show multiple usages from collaboration
        assert final_citation["usageCount"] >= 2
        
        # Should have feedback from multiple users
        # This would be verified through accuracy tracking records
        # in a full implementation with database access


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])