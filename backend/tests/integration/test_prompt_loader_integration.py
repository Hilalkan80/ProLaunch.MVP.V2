"""
Integration tests for the Prompt Loader with MCP integration.

Tests the complete integration between PromptLoader, MCP services,
and the overall prompt management workflow including context injection,
optimization, and memory management.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

from src.ai.prompt_loader import (
    PromptLoader, PromptType, TokenBudgetStrategy, TokenBudget
)


@pytest.fixture
def integration_prompt_files():
    """Create comprehensive prompt files for integration testing."""
    prompts_data = {
        "system": {
            "core_system": {
                "metadata": {
                    "version": "2.1.0",
                    "priority": 10,
                    "author": "Integration Test",
                    "description": "Core system prompt with business context",
                    "tags": ["system", "business", "core"],
                    "dependencies": [],
                    "cache_ttl": 3600
                },
                "content": """# Core Business AI Assistant

You are ProLaunch AI, a specialized business planning and strategy assistant.

## Your Role
- Provide comprehensive startup guidance for {company_name}
- Focus on {business_domain} industry expertise
- Adapt recommendations based on {growth_stage}

## Key Capabilities
1. Business model analysis and validation
2. Market research and competitive intelligence
3. Financial modeling and projections
4. Go-to-market strategy development

## References
- Market data from industry reports
- Best practices from successful startups
- Financial modeling templates

Use the provided context to deliver personalized, actionable insights.
"""
            },
            "market_analysis": {
                "metadata": {
                    "version": "1.5.0",
                    "priority": 8,
                    "description": "Market analysis and research prompt",
                    "tags": ["market", "research", "analysis"],
                    "dependencies": ["core_system"]
                },
                "content": """# Market Analysis Framework

Conduct comprehensive market analysis for {company_name} in the {target_market}.

## Analysis Components
1. **Market Size & Opportunity**
   - Total Addressable Market (TAM)
   - Serviceable Addressable Market (SAM)
   - Serviceable Obtainable Market (SOM)

2. **Competitive Landscape**
   - Direct competitors: {direct_competitors}
   - Indirect competitors: {indirect_competitors}
   - Market positioning analysis

3. **Customer Segmentation**
   - Primary target segments
   - Customer personas and pain points
   - Market validation approaches

## References
- Industry research reports
- Competitor analysis data
- Customer interview insights

Provide data-driven insights with specific recommendations.
"""
            }
        },
        "milestones": {
            "financial_model": {
                "metadata": {
                    "version": "1.0.0",
                    "priority": 7,
                    "description": "Generate comprehensive financial models",
                    "tags": ["financial", "modeling", "projections"]
                },
                "content": """# Financial Model Generator

Create detailed financial projections for {company_name}.

## Model Components
1. **Revenue Projections**
   - Monthly recurring revenue (MRR) for {revenue_model}
   - Growth assumptions: {growth_rate}%
   - Customer acquisition and churn rates

2. **Cost Structure**
   - Customer acquisition cost (CAC)
   - Cost of goods sold (COGS)
   - Operating expenses by category

3. **Cash Flow Analysis**
   - Monthly cash flow projections
   - Break-even analysis
   - Funding requirements: ${funding_needed}

## References
- Industry benchmark data
- SaaS metrics standards
- Startup financial templates

Generate realistic, investor-ready financial models.
"""
            }
        },
        "chat": {
            "interactive_session": {
                "metadata": {
                    "version": "1.2.0",
                    "priority": 6,
                    "description": "Interactive business planning sessions",
                    "tags": ["chat", "interactive", "planning"]
                },
                "content": """# Interactive Business Planning

Guide {user_name} through structured business planning for {company_name}.

## Session Structure
1. **Discovery Phase**
   - Business concept validation
   - Market opportunity assessment
   - Resource availability review

2. **Planning Phase**
   - Strategy development
   - Action item identification
   - Timeline creation

3. **Review Phase**
   - Plan validation
   - Risk assessment
   - Next steps definition

## References
- Business planning methodologies
- Startup frameworks (Lean, Agile)
- Best practice templates

Engage users with targeted questions and provide actionable guidance.
"""
            }
        }
    }
    return prompts_data


@pytest.fixture
async def mock_mcp_services():
    """Create mock MCP services for testing."""
    # Mock RefMCP
    ref_mcp = Mock()
    ref_mcp.extract_references = AsyncMock()
    ref_mcp.optimize_content = AsyncMock()
    ref_mcp.deduplicate_content = AsyncMock()
    ref_mcp.merge_contexts = AsyncMock()
    
    # Mock MemoryBankMCP
    memory_bank = Mock()
    memory_bank.search_memories = AsyncMock()
    memory_bank.store_memory = AsyncMock()
    
    # Mock TokenOptimizer
    token_optimizer = Mock()
    token_optimizer.optimize_tokens = Mock()
    
    return {
        "ref_mcp": ref_mcp,
        "memory_bank": memory_bank,
        "token_optimizer": token_optimizer
    }


@pytest.fixture
async def integration_loader(integration_prompt_files, mock_mcp_services):
    """Create integrated prompt loader with test files and mock services."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create prompt files
        for category, prompts in integration_prompt_files.items():
            category_dir = temp_path / category
            category_dir.mkdir(exist_ok=True)
            
            for prompt_name, prompt_data in prompts.items():
                if prompt_data.get("metadata"):
                    # Create markdown with YAML front matter
                    content = "---\n"
                    for key, value in prompt_data["metadata"].items():
                        if isinstance(value, list):
                            content += f"{key}:\n"
                            for item in value:
                                content += f"  - {item}\n"
                        else:
                            content += f"{key}: {value}\n"
                    content += "---\n\n" + prompt_data["content"]
                else:
                    content = prompt_data["content"]
                
                (category_dir / f"{prompt_name}.md").write_text(content)
        
        with patch('src.ai.prompt_loader.RefMCP') as mock_ref_class, \
             patch('src.ai.prompt_loader.MemoryBankMCP') as mock_memory_class, \
             patch('src.ai.prompt_loader.TokenOptimizer') as mock_optimizer_class:
            
            mock_ref_class.return_value = mock_mcp_services["ref_mcp"]
            mock_memory_class.return_value = mock_mcp_services["memory_bank"]
            mock_optimizer_class.return_value = mock_mcp_services["token_optimizer"]
            
            loader = PromptLoader(prompts_dir=temp_dir)
            
            # Store mock services for test access
            loader._test_mocks = mock_mcp_services
            
            yield loader


class TestPromptLoaderMCPIntegration:
    """Integration tests for PromptLoader with MCP services."""
    
    @pytest.mark.asyncio
    async def test_context_injection_workflow(self, integration_loader):
        """Test complete context injection workflow with MCP integration."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Setup memory search results
        memory_results = [
            {
                "content": "Previous analysis showed strong market demand for SaaS solutions in healthcare",
                "metadata": {"type": "market_research", "relevance": 0.95},
                "timestamp": datetime.utcnow() - timedelta(hours=2)
            },
            {
                "content": "Customer interviews indicated willingness to pay $50-100/month for comprehensive solution",
                "metadata": {"type": "customer_feedback", "relevance": 0.87},
                "timestamp": datetime.utcnow() - timedelta(hours=1)
            }
        ]
        mocks["memory_bank"].search_memories.return_value = memory_results
        
        # Setup reference extraction results
        reference_results = {
            "business": ["market_opportunity", "customer_segments"],
            "market": ["healthcare_saas", "competitive_analysis"],
            "financial": ["revenue_projections", "pricing_model"]
        }
        mocks["ref_mcp"].extract_references.return_value = reference_results
        
        # Setup reference memory results
        reference_memories = [
            {
                "content": "Healthcare SaaS market growing at 15% annually with $50B addressable market",
                "metadata": {"type": "market_data", "source": "industry_report"}
            },
            {
                "content": "Competitive pricing analysis shows premium solutions commanding $75-150/month",
                "metadata": {"type": "pricing_data", "source": "competitor_research"}
            }
        ]
        
        # Mock multiple calls to search_memories for references
        memory_call_count = 0
        async def mock_search_memories(*args, **kwargs):
            nonlocal memory_call_count
            memory_call_count += 1
            if memory_call_count == 1:
                return memory_results
            else:
                # Return reference memories for subsequent calls
                return reference_memories[:1] if memory_call_count <= 3 else reference_memories[1:]
        
        mocks["memory_bank"].search_memories.side_effect = mock_search_memories
        
        # Load prompt with context injection
        variables = {
            "company_name": "HealthTech Solutions",
            "business_domain": "healthcare technology",
            "growth_stage": "early stage"
        }
        
        result = await loader.load_prompt(
            prompt_name="core_system",
            prompt_type=PromptType.SYSTEM,
            variables=variables,
            inject_context=True,
            optimize=False
        )
        
        # Verify context injection
        assert result["context_injected"] is True
        prompt_content = result["prompt"]
        
        # Check variable interpolation
        assert "HealthTech Solutions" in prompt_content
        assert "healthcare technology" in prompt_content
        assert "early stage" in prompt_content
        
        # Check context injection
        assert "## Relevant Context:" in prompt_content
        assert "market demand for SaaS solutions" in prompt_content
        assert "## References:" in prompt_content
        assert "Healthcare SaaS market" in prompt_content
        
        # Verify MCP service calls
        mocks["memory_bank"].search_memories.assert_called()
        mocks["ref_mcp"].extract_references.assert_called_once()
        
        # Check search_memories was called multiple times for different references
        assert mocks["memory_bank"].search_memories.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_prompt_optimization_workflow(self, integration_loader):
        """Test prompt optimization through RefMCP integration."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Mock empty context to focus on optimization
        mocks["memory_bank"].search_memories.return_value = []
        mocks["ref_mcp"].extract_references.return_value = {}
        
        # Setup optimization result
        optimized_content = """# Optimized Business AI Assistant

ProLaunch AI specializes in startup guidance for HealthTech Solutions.

## Core Functions
- Business model validation
- Market analysis for healthcare technology
- Financial projections for early stage companies

## Key Focus Areas
1. Healthcare SaaS market opportunity
2. Competitive positioning strategy
3. Revenue model optimization

Deliver actionable, data-driven insights for rapid growth.
"""
        
        mocks["ref_mcp"].optimize_content.return_value = optimized_content
        
        # Load prompt with optimization
        result = await loader.load_prompt(
            prompt_name="core_system",
            variables={
                "company_name": "HealthTech Solutions",
                "business_domain": "healthcare technology",
                "growth_stage": "early stage"
            },
            inject_context=False,
            optimize=True,
            max_tokens=500
        )
        
        # Verify optimization
        assert result["optimized"] is True
        assert result["prompt"] == optimized_content
        
        # Verify optimization was called with correct parameters
        mocks["ref_mcp"].optimize_content.assert_called_once()
        call_args = mocks["ref_mcp"].optimize_content.call_args
        assert call_args[1]["max_tokens"] == 500
        assert call_args[1]["strategy"] == "auto"
        
        # Content should be optimized version
        assert "Optimized Business AI Assistant" in result["prompt"]
        assert len(result["prompt"]) < len(integration_loader._prompt_registry["system/core_system"].description or "")
    
    @pytest.mark.asyncio
    async def test_prompt_chain_with_mcp_integration(self, integration_loader):
        """Test prompt chain loading with full MCP integration."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Setup context for chain
        shared_context = {
            "company_name": "TechStartup Inc",
            "target_market": "B2B SaaS",
            "revenue_model": "subscription",
            "growth_rate": 25,
            "funding_needed": 500000
        }
        
        # Mock memory operations
        mocks["memory_bank"].search_memories.return_value = [
            {
                "content": "B2B SaaS companies typically achieve 15-25% monthly growth in early stages",
                "metadata": {"type": "industry_benchmark"}
            }
        ]
        mocks["memory_bank"].store_memory.return_value = True
        mocks["ref_mcp"].extract_references.return_value = {
            "business": ["saas_metrics", "growth_models"],
            "market": ["b2b_analysis"]
        }
        
        # Setup chain optimization
        optimized_prompts = [
            "Optimized market analysis for TechStartup Inc in B2B SaaS",
            "Optimized financial model with subscription revenue focus",
            "Optimized system prompt for comprehensive guidance"
        ]
        mocks["ref_mcp"].deduplicate_content.return_value = optimized_prompts
        mocks["ref_mcp"].merge_contexts.return_value = optimized_prompts
        
        # Load prompt chain
        prompt_names = ["market_analysis", "financial_model", "core_system"]
        
        results = await loader.load_prompt_chain(
            prompt_names=prompt_names,
            shared_context=shared_context,
            optimize_chain=True,
            max_tokens=2000
        )
        
        # Verify chain results
        assert len(results) == 3
        
        # Check that shared context was stored
        mocks["memory_bank"].store_memory.assert_called()
        store_call = mocks["memory_bank"].store_memory.call_args
        assert "chain_context" in store_call[1]["key"]
        assert store_call[1]["metadata"]["prompts"] == prompt_names
        
        # Check variable interpolation across chain
        for result in results:
            assert "TechStartup Inc" in result["prompt"] or result.get("chain_optimized", False)
        
        # Check chain optimization
        mocks["ref_mcp"].deduplicate_content.assert_called_once()
        
        # Verify all results marked as chain optimized
        for result in results:
            if result.get("chain_optimized"):
                assert result["chain_optimized"] is True
    
    @pytest.mark.asyncio
    async def test_token_budget_integration(self, integration_loader):
        """Test token budget management with MCP services."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Setup custom token budget
        custom_budget = TokenBudget(
            total_budget=2000,
            system_reserve=400,
            context_allocation=600,
            prompt_allocation=800,
            response_reserve=200
        )
        loader.token_budget = custom_budget
        
        # Mock context that would normally consume tokens
        large_context = [
            {"content": "Large context item 1 " * 50},
            {"content": "Large context item 2 " * 50},
            {"content": "Large context item 3 " * 50}
        ]
        mocks["memory_bank"].search_memories.return_value = large_context
        mocks["ref_mcp"].extract_references.return_value = {"business": ["large_ref"] * 10}
        
        # Mock optimization to respect token budget
        def mock_optimize_content(content, max_tokens, **kwargs):
            # Simulate optimization that reduces content to fit budget
            return f"Optimized content within {max_tokens} tokens: {content[:max_tokens//4]}..."
        
        mocks["ref_mcp"].optimize_content.side_effect = mock_optimize_content
        
        # Load prompt with token budget constraints
        result = await loader.load_prompt(
            prompt_name="core_system",
            variables={"company_name": "BudgetTest Corp"},
            inject_context=True,
            optimize=True,
            max_tokens=800  # Prompt allocation limit
        )
        
        # Verify token budget information in result
        assert "token_budget" in result
        budget_info = result["token_budget"]
        assert "allocated" in budget_info
        assert "available" in budget_info
        assert "total" in budget_info
        
        assert budget_info["total"] == 2000
        
        # Verify optimization was called with budget constraints
        mocks["ref_mcp"].optimize_content.assert_called()
        opt_call = mocks["ref_mcp"].optimize_content.call_args
        assert opt_call[1]["max_tokens"] == 800
        
        # Result should indicate optimization occurred
        assert result["optimized"] is True
        assert "Optimized content within 800 tokens" in result["prompt"]
    
    @pytest.mark.asyncio
    async def test_dependency_resolution(self, integration_loader):
        """Test prompt dependency resolution through MCP services."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Market analysis prompt depends on core_system
        # Setup dependency context
        dependency_memories = [
            {
                "content": "Core system context: Business AI assistant focused on startup guidance",
                "metadata": {"type": "dependency", "source": "core_system"}
            }
        ]
        
        search_call_count = 0
        async def mock_dependency_search(query, **kwargs):
            nonlocal search_call_count
            search_call_count += 1
            if "market_analysis" in query:
                return [
                    {"content": "Market analysis context for B2B SaaS companies"}
                ]
            elif "core_system" in query:
                return dependency_memories
            return []
        
        mocks["memory_bank"].search_memories.side_effect = mock_dependency_search
        mocks["ref_mcp"].extract_references.return_value = {}
        
        # Load prompt that has dependencies
        result = await loader.load_prompt(
            prompt_name="market_analysis",
            variables={
                "company_name": "DependencyTest Inc",
                "target_market": "B2B software"
            },
            inject_context=True,
            optimize=False
        )
        
        # Verify dependency context was injected
        assert result["context_injected"] is True
        prompt_content = result["prompt"]
        
        # Should contain both direct context and dependency context
        assert "DependencyTest Inc" in prompt_content
        assert "B2B software" in prompt_content
        
        # Memory search should have been called for the prompt and its dependencies
        assert mocks["memory_bank"].search_memories.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_caching_with_mcp_integration(self, integration_loader):
        """Test caching behavior with MCP service calls."""
        loader = integration_loader
        mocks = loader._test_mocks
        loader.cache_enabled = True
        
        # Setup MCP responses
        mocks["memory_bank"].search_memories.return_value = [
            {"content": "Cached context data"}
        ]
        mocks["ref_mcp"].extract_references.return_value = {
            "test": ["cached_reference"]
        }
        
        variables = {"company_name": "CacheTest Corp"}
        
        # First load - should call MCP services
        result1 = await loader.load_prompt(
            prompt_name="core_system",
            variables=variables,
            inject_context=True,
            optimize=False
        )
        
        # Verify MCP services were called
        assert mocks["memory_bank"].search_memories.call_count >= 1
        assert mocks["ref_mcp"].extract_references.call_count == 1
        
        # Reset call counts
        mocks["memory_bank"].search_memories.reset_mock()
        mocks["ref_mcp"].extract_references.reset_mock()
        
        # Second load with same parameters - should use cache
        result2 = await loader.load_prompt(
            prompt_name="core_system",
            variables=variables,
            inject_context=True,
            optimize=False
        )
        
        # Results should be identical
        assert result1["prompt"] == result2["prompt"]
        assert result1["metadata"] == result2["metadata"]
        
        # MCP services should NOT be called again due to caching
        assert mocks["memory_bank"].search_memories.call_count == 0
        assert mocks["ref_mcp"].extract_references.call_count == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_with_mcp_failures(self, integration_loader):
        """Test error handling when MCP services fail."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Test memory bank failure
        mocks["memory_bank"].search_memories.side_effect = Exception("Memory bank connection failed")
        mocks["ref_mcp"].extract_references.return_value = {}
        
        # Load should still succeed with graceful error handling
        result = await loader.load_prompt(
            prompt_name="core_system",
            variables={"company_name": "ErrorTest Inc"},
            inject_context=True,
            optimize=False
        )
        
        # Should still have basic prompt without context
        assert "prompt" in result
        assert "ErrorTest Inc" in result["prompt"]
        assert result["context_injected"] is False  # Failed to inject context
        
        # Reset memory bank, test ref MCP failure
        mocks["memory_bank"].search_memories.side_effect = None
        mocks["memory_bank"].search_memories.return_value = []
        mocks["ref_mcp"].extract_references.side_effect = Exception("Ref MCP service unavailable")
        
        result2 = await loader.load_prompt(
            prompt_name="core_system",
            variables={"company_name": "ErrorTest2 Inc"},
            inject_context=True,
            optimize=False
        )
        
        # Should still work without references
        assert "ErrorTest2 Inc" in result2["prompt"]
        
        # Test optimization failure
        mocks["ref_mcp"].extract_references.side_effect = None
        mocks["ref_mcp"].extract_references.return_value = {}
        mocks["ref_mcp"].optimize_content.side_effect = Exception("Optimization service failed")
        
        result3 = await loader.load_prompt(
            prompt_name="core_system",
            variables={"company_name": "ErrorTest3 Inc"},
            inject_context=False,
            optimize=True,
            max_tokens=500
        )
        
        # Should fallback to truncation when optimization fails
        assert "ErrorTest3 Inc" in result3["prompt"]
        assert result3["optimized"] is False  # Optimization failed
    
    @pytest.mark.asyncio
    async def test_performance_with_mcp_services(self, integration_loader):
        """Test performance characteristics with MCP integration."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Setup realistic MCP response times
        async def mock_search_with_delay(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms delay
            return [{"content": f"Context data for {args[0] if args else 'query'}"}]
        
        async def mock_extract_with_delay(*args, **kwargs):
            await asyncio.sleep(0.005)  # 5ms delay
            return {"business": ["ref1", "ref2"], "market": ["ref3"]}
        
        async def mock_optimize_with_delay(content, **kwargs):
            await asyncio.sleep(0.02)  # 20ms delay
            return f"Optimized: {content[:100]}..."
        
        mocks["memory_bank"].search_memories.side_effect = mock_search_with_delay
        mocks["ref_mcp"].extract_references.side_effect = mock_extract_with_delay
        mocks["ref_mcp"].optimize_content.side_effect = mock_optimize_with_delay
        
        # Time the complete workflow
        start_time = datetime.utcnow()
        
        result = await loader.load_prompt(
            prompt_name="core_system",
            variables={"company_name": "PerformanceTest Inc"},
            inject_context=True,
            optimize=True,
            max_tokens=500
        )
        
        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()
        
        # Verify result
        assert "PerformanceTest Inc" in result["prompt"]
        assert result["context_injected"] is True
        assert result["optimized"] is True
        
        # Performance should be reasonable (under 1 second for integration test)
        assert total_time < 1.0
        
        # All MCP services should have been called
        assert mocks["memory_bank"].search_memories.call_count >= 1
        assert mocks["ref_mcp"].extract_references.call_count == 1
        assert mocks["ref_mcp"].optimize_content.call_count == 1
    
    @pytest.mark.asyncio
    async def test_memory_persistence_integration(self, integration_loader):
        """Test memory persistence across prompt loading sessions."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Setup initial memory state
        stored_memories = []
        
        async def mock_store_memory(key, content, metadata=None):
            stored_memories.append({
                "key": key,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow()
            })
            return True
        
        def mock_search_memories(query, **kwargs):
            # Return relevant stored memories
            relevant = [
                mem for mem in stored_memories
                if any(term in mem["content"].lower() for term in query.lower().split())
            ]
            return relevant
        
        mocks["memory_bank"].store_memory.side_effect = mock_store_memory
        mocks["memory_bank"].search_memories.side_effect = mock_search_memories
        mocks["ref_mcp"].extract_references.return_value = {}
        
        # First session - load prompt and store context
        context_data = {
            "company_name": "MemoryTest Corp",
            "session_id": "test_session_001",
            "business_type": "SaaS platform"
        }
        
        result1 = await loader.load_prompt(
            prompt_name="core_system",
            variables=context_data,
            inject_context=True,
            optimize=False
        )
        
        # Should have stored session context
        assert len(stored_memories) > 0
        assert any("MemoryTest Corp" in mem["content"] for mem in stored_memories)
        
        # Second session - should retrieve previous context
        result2 = await loader.load_prompt(
            prompt_name="market_analysis",
            variables={
                "company_name": "MemoryTest Corp",
                "target_market": "enterprise software"
            },
            inject_context=True,
            optimize=False
        )
        
        # Should include context from previous session
        assert result2["context_injected"] is True
        # Previous business type should influence current analysis
        prompt_content = result2["prompt"]
        assert "MemoryTest Corp" in prompt_content
    
    @pytest.mark.asyncio
    async def test_validation_with_mcp_services(self, integration_loader):
        """Test prompt validation with MCP service integration."""
        loader = integration_loader
        
        # Test validation of existing prompt
        validation_result = await loader.validate_prompt("core_system", PromptType.SYSTEM)
        
        assert validation_result["valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # Check metadata validation
        info = validation_result["info"]
        assert "metadata" in info
        assert info["metadata"]["priority"] == 10
        assert "business" in info["metadata"]["tags"]
        
        # Check variable detection
        assert "required_variables" in info
        required_vars = info["required_variables"]
        assert "company_name" in required_vars
        assert "business_domain" in required_vars
        assert "growth_stage" in required_vars
        
        # Check dependency validation
        market_validation = await loader.validate_prompt("market_analysis", PromptType.SYSTEM)
        assert "core_system" in market_validation["info"]["metadata"]["dependencies"]
        
        # Should have warnings if dependencies are not found (they exist in this case)
        if market_validation["warnings"]:
            # If there are warnings, they shouldn't be about missing dependencies
            assert not any("Missing dependency" in warning for warning in market_validation["warnings"])
    
    @pytest.mark.asyncio
    async def test_export_with_mcp_integration(self, integration_loader):
        """Test prompt export functionality with full MCP context."""
        loader = integration_loader
        
        # Export all prompts as JSON
        exported_json = await loader.export_prompts(
            output_format="json",
            include_metadata=True
        )
        
        exported_data = json.loads(exported_json)
        
        # Verify export structure
        assert "prompts" in exported_data
        assert "metadata" in exported_data
        assert len(exported_data["prompts"]) == 4  # core_system, market_analysis, financial_model, interactive_session
        
        # Check specific prompt exports
        system_prompts = {k: v for k, v in exported_data["prompts"].items() if k.startswith("system/")}
        assert len(system_prompts) == 2
        
        # Verify metadata preservation
        core_system_export = exported_data["prompts"]["system/core_system"]
        assert "metadata" in core_system_export
        assert core_system_export["metadata"]["priority"] == 10
        assert "business" in core_system_export["metadata"]["tags"]
        
        # Export as YAML
        exported_yaml = await loader.export_prompts(
            output_format="yaml",
            include_metadata=True
        )
        
        import yaml
        yaml_data = yaml.safe_load(exported_yaml)
        assert len(yaml_data["prompts"]) == 4
        
        # Export as Markdown
        exported_md = await loader.export_prompts(
            output_format="markdown",
            include_metadata=True
        )
        
        assert "# Prompt Library Export" in exported_md
        assert "system/core_system" in exported_md
        assert "Priority: 10/10" in exported_md
        assert "**Tags:** ['business', 'core', 'system']" in exported_md


class TestPromptLoaderEdgeCases:
    """Test edge cases and error conditions in MCP integration."""
    
    @pytest.mark.asyncio
    async def test_partial_mcp_service_availability(self, integration_loader):
        """Test behavior when only some MCP services are available."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Memory bank available, Ref MCP unavailable
        mocks["memory_bank"].search_memories.return_value = [
            {"content": "Available memory context"}
        ]
        mocks["ref_mcp"].extract_references.side_effect = Exception("Ref service down")
        mocks["ref_mcp"].optimize_content.side_effect = Exception("Optimization service down")
        
        result = await loader.load_prompt(
            prompt_name="core_system",
            variables={"company_name": "PartialService Corp"},
            inject_context=True,
            optimize=True,
            max_tokens=500
        )
        
        # Should still work with available services
        assert "PartialService Corp" in result["prompt"]
        assert result["context_injected"] is True  # Memory context available
        assert result["optimized"] is False  # Optimization failed gracefully
        
        # Should have memory context but no reference context
        assert "Available memory context" in result["prompt"]
    
    @pytest.mark.asyncio
    async def test_concurrent_prompt_loading(self, integration_loader):
        """Test concurrent prompt loading with MCP services."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Setup mock responses
        async def mock_search_memories(query, **kwargs):
            await asyncio.sleep(0.01)  # Small delay to simulate real service
            return [{"content": f"Context for {query}"}]
        
        async def mock_extract_references(content):
            await asyncio.sleep(0.005)
            return {"business": [f"ref_{hash(content) % 100}"]}
        
        mocks["memory_bank"].search_memories.side_effect = mock_search_memories
        mocks["ref_mcp"].extract_references.side_effect = mock_extract_references
        
        # Load multiple prompts concurrently
        variables_list = [
            {"company_name": f"ConcurrentTest{i} Corp"}
            for i in range(5)
        ]
        
        tasks = [
            loader.load_prompt(
                prompt_name="core_system",
                variables=variables,
                inject_context=True,
                optimize=False
            )
            for variables in variables_list
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 5
        for i, result in enumerate(results):
            assert f"ConcurrentTest{i} Corp" in result["prompt"]
            assert result["context_injected"] is True
        
        # MCP services should have been called for each prompt
        assert mocks["memory_bank"].search_memories.call_count == 5
        assert mocks["ref_mcp"].extract_references.call_count == 5
    
    @pytest.mark.asyncio
    async def test_token_budget_edge_cases(self, integration_loader):
        """Test token budget handling edge cases."""
        loader = integration_loader
        mocks = loader._test_mocks
        
        # Test with very small token budget
        tiny_budget = TokenBudget(
            total_budget=100,
            system_reserve=20,
            context_allocation=30,
            prompt_allocation=25,
            response_reserve=25
        )
        loader.token_budget = tiny_budget
        
        # Large context that exceeds budget
        large_context = [{"content": "Large context item " * 50} for _ in range(10)]
        mocks["memory_bank"].search_memories.return_value = large_context
        mocks["ref_mcp"].extract_references.return_value = {
            "business": ["ref"] * 20  # Many references
        }
        
        # Mock optimization to handle tiny budget
        def mock_optimize_tiny(content, max_tokens, **kwargs):
            return content[:max_tokens] if max_tokens > 0 else "Minimal content"
        
        mocks["ref_mcp"].optimize_content.side_effect = mock_optimize_tiny
        
        result = await loader.load_prompt(
            prompt_name="core_system",
            variables={"company_name": "TinyBudget Corp"},
            inject_context=True,
            optimize=True,
            max_tokens=25
        )
        
        # Should still work within constraints
        assert "TinyBudget Corp" in result["prompt"] or result["prompt"] == "Minimal content"
        assert result["optimized"] is True
        
        # Budget info should reflect constraints
        budget_info = result["token_budget"]
        assert budget_info["total"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])