"""
Unit tests for the Prompt Loader system.

Tests the prompt loading, template management, token budget optimization,
and MCP integration functionality.
"""

import pytest
import os
import tempfile
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from src.ai.prompt_loader import (
    PromptLoader, PromptType, TokenBudgetStrategy, PromptMetadata,
    TokenBudget, get_prompt_loader
)


class TestPromptMetadata:
    """Test PromptMetadata dataclass."""
    
    def test_metadata_creation_with_defaults(self):
        """Test creating metadata with default values."""
        metadata = PromptMetadata(
            name="test_prompt",
            type=PromptType.SYSTEM
        )
        
        assert metadata.name == "test_prompt"
        assert metadata.type == PromptType.SYSTEM
        assert metadata.version == "1.0.0"
        assert metadata.priority == 5
        assert metadata.token_estimate == 0
        assert metadata.tags == []
        assert metadata.dependencies == []
        assert metadata.cache_ttl == 3600
    
    def test_metadata_creation_with_custom_values(self):
        """Test creating metadata with custom values."""
        test_date = datetime(2024, 1, 15, 10, 30, 0)
        
        metadata = PromptMetadata(
            name="custom_prompt",
            type=PromptType.MILESTONE,
            version="2.1.0",
            last_updated=test_date,
            author="Test Author",
            description="Custom test prompt",
            token_estimate=1200,
            priority=8,
            tags=["ai", "business"],
            dependencies=["base_prompt"],
            cache_ttl=7200
        )
        
        assert metadata.name == "custom_prompt"
        assert metadata.type == PromptType.MILESTONE
        assert metadata.version == "2.1.0"
        assert metadata.last_updated == test_date
        assert metadata.author == "Test Author"
        assert metadata.description == "Custom test prompt"
        assert metadata.token_estimate == 1200
        assert metadata.priority == 8
        assert metadata.tags == ["ai", "business"]
        assert metadata.dependencies == ["base_prompt"]
        assert metadata.cache_ttl == 7200
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        test_date = datetime(2024, 1, 15, 10, 30, 0)
        
        metadata = PromptMetadata(
            name="dict_test",
            type=PromptType.CHAT,
            version="1.5.0",
            last_updated=test_date,
            author="Dict Author",
            priority=7
        )
        
        result = metadata.to_dict()
        
        expected = {
            "name": "dict_test",
            "type": "chat",
            "version": "1.5.0",
            "last_updated": "2024-01-15T10:30:00",
            "author": "Dict Author",
            "description": None,
            "token_estimate": 0,
            "priority": 7,
            "tags": [],
            "dependencies": [],
            "cache_ttl": 3600
        }
        
        assert result == expected


class TestTokenBudget:
    """Test TokenBudget management."""
    
    def test_default_token_budget(self):
        """Test default token budget configuration."""
        budget = TokenBudget()
        
        assert budget.total_budget == 8192
        assert budget.system_reserve == 1000
        assert budget.context_allocation == 3000
        assert budget.prompt_allocation == 2000
        assert budget.response_reserve == 2192
        assert budget.current_usage == {}
    
    def test_available_tokens_calculation(self):
        """Test available tokens calculation."""
        budget = TokenBudget(total_budget=10000, response_reserve=2000)
        
        # Initially, should have total - response_reserve available
        assert budget.available_tokens() == 8000
        
        # After some allocation
        budget.current_usage = {"system": 500, "context": 1500}
        assert budget.available_tokens() == 6000  # 10000 - 2000 - 2000
    
    def test_token_allocation(self):
        """Test token allocation to categories."""
        budget = TokenBudget(total_budget=5000, response_reserve=1000)
        
        # Successful allocation
        result1 = budget.allocate("system", 500)
        assert result1 is True
        assert budget.current_usage["system"] == 500
        
        # Another allocation
        result2 = budget.allocate("context", 1000)
        assert result2 is True
        assert budget.current_usage["context"] == 1000
        
        # Add to existing category
        result3 = budget.allocate("system", 200)
        assert result3 is True
        assert budget.current_usage["system"] == 700
        
        # Allocation that would exceed budget
        result4 = budget.allocate("prompt", 4000)  # Would exceed available (3300)
        assert result4 is False
        assert "prompt" not in budget.current_usage
    
    def test_budget_reset(self):
        """Test resetting budget usage."""
        budget = TokenBudget()
        budget.current_usage = {"system": 500, "context": 1000}
        
        budget.reset()
        
        assert budget.current_usage == {}
        assert budget.available_tokens() == budget.total_budget - budget.response_reserve
    
    def test_get_allocation_for_category(self):
        """Test getting budget allocation for specific categories."""
        budget = TokenBudget(
            system_reserve=1500,
            context_allocation=3500,
            prompt_allocation=2500,
            response_reserve=2000
        )
        
        assert budget.get_allocation_for("system") == 1500
        assert budget.get_allocation_for("context") == 3500
        assert budget.get_allocation_for("prompt") == 2500
        assert budget.get_allocation_for("response") == 2000
        assert budget.get_allocation_for("unknown") == 0


class TestPromptLoaderInitialization:
    """Test PromptLoader initialization and setup."""
    
    def test_default_initialization(self):
        """Test default initialization parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.ai.prompt_loader.RefMCP'), \
                 patch('src.ai.prompt_loader.MemoryBankMCP'), \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(prompts_dir=temp_dir)
                
                assert loader.prompts_dir == Path(temp_dir)
                assert loader.cache_enabled is True
                assert loader.cache_ttl == 3600
                assert isinstance(loader.token_budget, TokenBudget)
                assert loader._cache == {}
                assert loader._prompt_registry == {}
    
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_budget = TokenBudget(total_budget=16384, system_reserve=2000)
            
            with patch('src.ai.prompt_loader.RefMCP'), \
                 patch('src.ai.prompt_loader.MemoryBankMCP'), \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(
                    prompts_dir=temp_dir,
                    cache_enabled=False,
                    cache_ttl=7200,
                    token_budget=custom_budget
                )
                
                assert loader.cache_enabled is False
                assert loader.cache_ttl == 7200
                assert loader.token_budget == custom_budget
    
    def test_mcp_initialization(self):
        """Test MCP components initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.ai.prompt_loader.RefMCP') as mock_ref, \
                 patch('src.ai.prompt_loader.MemoryBankMCP') as mock_memory, \
                 patch('src.ai.prompt_loader.TokenOptimizer') as mock_optimizer:
                
                loader = PromptLoader(prompts_dir=temp_dir)
                
                mock_ref.assert_called_once()
                mock_memory.assert_called_once()
                mock_optimizer.assert_called_once()
                
                assert loader.ref_mcp is not None
                assert loader.memory_bank is not None
                assert loader.token_optimizer is not None


class TestPromptRegistration:
    """Test prompt file registration and metadata extraction."""
    
    def create_test_prompt_files(self, temp_dir: Path):
        """Create test prompt files for testing."""
        # Create directory structure
        (temp_dir / "system").mkdir(exist_ok=True)
        (temp_dir / "milestones").mkdir(exist_ok=True)
        (temp_dir / "chat").mkdir(exist_ok=True)
        
        # System prompt with YAML metadata
        system_prompt = """---
version: "1.2.0"
author: "Test Author"
description: "System prompt for testing"
priority: 9
tags: ["system", "core"]
cache_ttl: 1800
---

# System Prompt

You are an AI assistant specialized in business strategy and planning.
Your role is to provide comprehensive guidance for startup development.
"""
        (temp_dir / "system" / "00_global_system_prompt.md").write_text(system_prompt)
        
        # Milestone prompt without metadata
        milestone_prompt = """# Financial Model Generator

## Purpose
Generate comprehensive financial models for startups

Generate a detailed financial model including:
- Revenue projections
- Cost structure analysis  
- Cash flow statements
- Break-even analysis

_Last updated: 2024-01-10_
"""
        (temp_dir / "milestones" / "M4_Financial_Model_Generator_Prompt.md").write_text(milestone_prompt)
        
        # Chat prompt as JSON
        chat_prompt = {
            "metadata": {
                "version": "2.0.0",
                "priority": 6,
                "tags": ["chat", "interactive"]
            },
            "prompt": "You are helping with interactive business planning sessions. Engage users in structured conversations to gather requirements."
        }
        (temp_dir / "chat" / "interactive_session.json").write_text(json.dumps(chat_prompt))
        
        # Invalid file (should be skipped)
        (temp_dir / "system" / "invalid.py").write_text("# Not a prompt file")
    
    def test_prompt_registry_loading(self):
        """Test loading prompts into registry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_prompt_files(temp_path)
            
            with patch('src.ai.prompt_loader.RefMCP'), \
                 patch('src.ai.prompt_loader.MemoryBankMCP'), \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(prompts_dir=temp_dir)
                
                # Should have registered 3 valid prompts
                assert len(loader._prompt_registry) == 3
                
                # Check specific registrations
                assert "system/00_global_system_prompt" in loader._prompt_registry
                assert "milestones/M4_Financial_Model_Generator_Prompt" in loader._prompt_registry
                assert "chat/interactive_session" in loader._prompt_registry
    
    def test_metadata_extraction_yaml(self):
        """Test metadata extraction from YAML front matter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_prompt_files(temp_path)
            
            with patch('src.ai.prompt_loader.RefMCP'), \
                 patch('src.ai.prompt_loader.MemoryBankMCP'), \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(prompts_dir=temp_dir)
                
                metadata = loader._prompt_registry["system/00_global_system_prompt"]
                
                assert metadata.name == "00_global_system_prompt"
                assert metadata.type == PromptType.SYSTEM
                assert metadata.version == "1.2.0"
                assert metadata.author == "Test Author"
                assert metadata.description == "System prompt for testing"
                assert metadata.priority == 9
                assert metadata.tags == ["system", "core"]
                assert metadata.cache_ttl == 1800
    
    def test_metadata_extraction_markdown(self):
        """Test metadata extraction from markdown comments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_prompt_files(temp_path)
            
            with patch('src.ai.prompt_loader.RefMCP'), \
                 patch('src.ai.prompt_loader.MemoryBankMCP'), \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(prompts_dir=temp_dir)
                
                metadata = loader._prompt_registry["milestones/M4_Financial_Model_Generator_Prompt"]
                
                assert metadata.name == "M4_Financial_Model_Generator_Prompt"
                assert metadata.type == PromptType.MILESTONE
                assert metadata.description == "Generate comprehensive financial models for startups"
                assert metadata.last_updated == datetime(2024, 1, 10)
    
    def test_token_estimation(self):
        """Test token count estimation during registration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.create_test_prompt_files(temp_path)
            
            with patch('src.ai.prompt_loader.RefMCP'), \
                 patch('src.ai.prompt_loader.MemoryBankMCP'), \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(prompts_dir=temp_dir)
                
                for prompt_key, metadata in loader._prompt_registry.items():
                    # Token estimate should be roughly content length / 4
                    assert metadata.token_estimate > 0
                    assert isinstance(metadata.token_estimate, int)


class TestPromptLoading:
    """Test prompt loading functionality."""
    
    @pytest.fixture
    def setup_loader(self):
        """Setup prompt loader with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test prompt files
            (temp_path / "system").mkdir(exist_ok=True)
            
            test_prompt = """# Test System Prompt

You are a test assistant for {company_name}.
Your primary function is {primary_function}.

Additional context: {additional_context}
"""
            (temp_path / "system" / "test_prompt.md").write_text(test_prompt)
            
            with patch('src.ai.prompt_loader.RefMCP') as mock_ref, \
                 patch('src.ai.prompt_loader.MemoryBankMCP') as mock_memory, \
                 patch('src.ai.prompt_loader.TokenOptimizer') as mock_optimizer:
                
                loader = PromptLoader(prompts_dir=temp_dir)
                
                # Mock MCP instances
                loader.ref_mcp = mock_ref.return_value
                loader.memory_bank = mock_memory.return_value
                
                yield loader
    
    @pytest.mark.asyncio
    async def test_load_prompt_basic(self, setup_loader):
        """Test basic prompt loading."""
        loader = setup_loader
        
        # Mock MCP methods
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        result = await loader.load_prompt(
            prompt_name="test_prompt",
            prompt_type=PromptType.SYSTEM,
            inject_context=False,
            optimize=False
        )
        
        assert "prompt" in result
        assert "metadata" in result
        assert "token_count" in result
        assert "token_budget" in result
        assert result["optimized"] is False
        assert result["context_injected"] is False
        
        # Check prompt content
        assert "You are a test assistant" in result["prompt"]
        assert "{company_name}" in result["prompt"]  # Variables not interpolated
    
    @pytest.mark.asyncio
    async def test_load_prompt_with_variables(self, setup_loader):
        """Test prompt loading with variable interpolation."""
        loader = setup_loader
        
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        variables = {
            "company_name": "TestCorp",
            "primary_function": "provide business guidance",
            "additional_context": "Focus on startup strategies"
        }
        
        result = await loader.load_prompt(
            prompt_name="test_prompt",
            variables=variables,
            inject_context=False,
            optimize=False
        )
        
        prompt_content = result["prompt"]
        assert "TestCorp" in prompt_content
        assert "provide business guidance" in prompt_content
        assert "Focus on startup strategies" in prompt_content
        assert "{company_name}" not in prompt_content  # Should be replaced
    
    @pytest.mark.asyncio
    async def test_load_prompt_with_context_injection(self, setup_loader):
        """Test prompt loading with context injection."""
        loader = setup_loader
        
        # Mock memory search results
        mock_memories = [
            {"content": "Previous conversation about business strategy"},
            {"content": "User preferences for detailed analysis"}
        ]
        loader.memory_bank.search_memories = AsyncMock(return_value=mock_memories)
        
        # Mock reference extraction
        mock_references = {
            "business": ["business_strategy", "market_analysis"],
            "strategy": ["competitive_analysis"]
        }
        loader.ref_mcp.extract_references = AsyncMock(return_value=mock_references)
        
        result = await loader.load_prompt(
            prompt_name="test_prompt",
            inject_context=True,
            optimize=False
        )
        
        assert result["context_injected"] is True
        
        # Context should be merged into prompt
        prompt_content = result["prompt"]
        assert "Relevant Context:" in prompt_content
        assert "business strategy" in prompt_content
    
    @pytest.mark.asyncio
    async def test_load_prompt_with_optimization(self, setup_loader):
        """Test prompt loading with optimization."""
        loader = setup_loader
        
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        # Mock optimization
        optimized_content = "Optimized version of the prompt with reduced tokens."
        loader.ref_mcp.optimize_content = AsyncMock(return_value=optimized_content)
        
        result = await loader.load_prompt(
            prompt_name="test_prompt",
            optimize=True,
            max_tokens=100
        )
        
        assert result["optimized"] is True
        assert result["prompt"] == optimized_content
        
        # Verify optimization was called with correct parameters
        loader.ref_mcp.optimize_content.assert_called_once()
        call_args = loader.ref_mcp.optimize_content.call_args
        assert call_args[1]["max_tokens"] == 100
        assert call_args[1]["strategy"] == "auto"
    
    @pytest.mark.asyncio
    async def test_load_prompt_not_found(self, setup_loader):
        """Test loading non-existent prompt."""
        loader = setup_loader
        
        with pytest.raises(ValueError) as exc_info:
            await loader.load_prompt("non_existent_prompt")
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_load_prompt_caching(self, setup_loader):
        """Test prompt result caching."""
        loader = setup_loader
        loader.cache_enabled = True
        
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        # First load
        result1 = await loader.load_prompt("test_prompt", inject_context=False, optimize=False)
        
        # Second load should use cache
        result2 = await loader.load_prompt("test_prompt", inject_context=False, optimize=False)
        
        assert result1["prompt"] == result2["prompt"]
        # Only one call to memory bank despite two load attempts
        assert loader.memory_bank.search_memories.call_count == 1


class TestPromptChainLoading:
    """Test prompt chain loading functionality."""
    
    @pytest.fixture
    def chain_loader(self):
        """Setup loader with multiple prompt files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create system directory and prompts
            (temp_path / "system").mkdir(exist_ok=True)
            
            system_prompt = "You are an AI assistant for {company_name}."
            (temp_path / "system" / "base_prompt.md").write_text(system_prompt)
            
            analysis_prompt = "Analyze the business context for {business_type}."
            (temp_path / "system" / "analysis_prompt.md").write_text(analysis_prompt)
            
            summary_prompt = "Provide a summary of findings from previous analysis."
            (temp_path / "system" / "summary_prompt.md").write_text(summary_prompt)
            
            with patch('src.ai.prompt_loader.RefMCP') as mock_ref, \
                 patch('src.ai.prompt_loader.MemoryBankMCP') as mock_memory, \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(prompts_dir=temp_dir)
                loader.ref_mcp = mock_ref.return_value
                loader.memory_bank = mock_memory.return_value
                
                yield loader
    
    @pytest.mark.asyncio
    async def test_load_prompt_chain_basic(self, chain_loader):
        """Test basic prompt chain loading."""
        loader = chain_loader
        
        # Mock MCP methods
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.memory_bank.store_memory = AsyncMock()
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        prompt_names = ["base_prompt", "analysis_prompt", "summary_prompt"]
        shared_context = {"company_name": "TestCorp", "business_type": "SaaS startup"}
        
        results = await loader.load_prompt_chain(
            prompt_names=prompt_names,
            shared_context=shared_context,
            optimize_chain=False,
            max_tokens=2000
        )
        
        assert len(results) == 3
        
        # Each result should have expected structure
        for result in results:
            assert "prompt" in result
            assert "metadata" in result
            assert "token_count" in result
        
        # Variables should be interpolated in each prompt
        assert "TestCorp" in results[0]["prompt"]
        assert "SaaS startup" in results[1]["prompt"]
        
        # Shared context should be stored in memory bank
        loader.memory_bank.store_memory.assert_called()
    
    @pytest.mark.asyncio
    async def test_load_prompt_chain_with_optimization(self, chain_loader):
        """Test prompt chain loading with optimization."""
        loader = chain_loader
        
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.memory_bank.store_memory = AsyncMock()
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        # Mock chain optimization
        optimized_prompts = [
            "Optimized base prompt for TestCorp",
            "Optimized analysis for SaaS",
            "Optimized summary prompt"
        ]
        loader.ref_mcp.deduplicate_content = AsyncMock(return_value=optimized_prompts)
        loader.ref_mcp.merge_contexts = AsyncMock(return_value=optimized_prompts)
        
        prompt_names = ["base_prompt", "analysis_prompt", "summary_prompt"]
        
        results = await loader.load_prompt_chain(
            prompt_names=prompt_names,
            optimize_chain=True,
            max_tokens=1500
        )
        
        assert len(results) == 3
        
        # Should have called optimization methods
        loader.ref_mcp.deduplicate_content.assert_called_once()
        
        # Results should be marked as chain optimized
        for result in results:
            assert result.get("chain_optimized") is True
    
    @pytest.mark.asyncio
    async def test_prompt_chain_token_budget_distribution(self, chain_loader):
        """Test token budget distribution across chain."""
        loader = chain_loader
        
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.memory_bank.store_memory = AsyncMock()
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        prompt_names = ["base_prompt", "analysis_prompt"]
        total_budget = 1000
        
        results = await loader.load_prompt_chain(
            prompt_names=prompt_names,
            max_tokens=total_budget
        )
        
        # Budget should be distributed across prompts
        total_used = sum(result["token_count"] for result in results)
        assert total_used <= total_budget
        
        # Each prompt should have gotten roughly equal allocation initially
        budget_per_prompt = total_budget // len(prompt_names)
        for result in results[:-1]:  # All but last
            # Token budget info should be available
            assert "token_budget" in result


class TestTokenBudgetOptimization:
    """Test token budget optimization strategies."""
    
    @pytest.fixture
    def budget_loader(self):
        """Setup loader for budget optimization testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "system").mkdir(exist_ok=True)
            
            # Create prompts with different priorities and sizes
            prompts_data = [
                ("high_priority", "High priority prompt with significant content", 10, 500),
                ("medium_priority", "Medium priority prompt", 5, 200),
                ("low_priority", "Low priority prompt", 2, 100),
            ]
            
            for name, content, priority, estimated_tokens in prompts_data:
                prompt_content = f"""---
priority: {priority}
token_estimate: {estimated_tokens}
---

{content}
"""
                (temp_path / "system" / f"{name}.md").write_text(prompt_content)
            
            with patch('src.ai.prompt_loader.RefMCP'), \
                 patch('src.ai.prompt_loader.MemoryBankMCP'), \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(prompts_dir=temp_dir)
                yield loader
    
    @pytest.mark.asyncio
    async def test_proportional_budget_strategy(self, budget_loader):
        """Test proportional token budget allocation."""
        loader = budget_loader
        
        prompt_names = ["high_priority", "medium_priority", "low_priority"]
        total_budget = 1000
        
        allocations = await loader.optimize_token_budget(
            prompts=prompt_names,
            total_budget=total_budget,
            strategy=TokenBudgetStrategy.PROPORTIONAL
        )
        
        assert len(allocations) == 3
        assert sum(allocations.values()) <= total_budget
        
        # Higher token estimate should get more allocation
        assert allocations["high_priority"] > allocations["medium_priority"]
        assert allocations["medium_priority"] > allocations["low_priority"]
    
    @pytest.mark.asyncio
    async def test_priority_based_budget_strategy(self, budget_loader):
        """Test priority-based token budget allocation."""
        loader = budget_loader
        
        prompt_names = ["high_priority", "medium_priority", "low_priority"]
        total_budget = 1500
        
        allocations = await loader.optimize_token_budget(
            prompts=prompt_names,
            total_budget=total_budget,
            strategy=TokenBudgetStrategy.PRIORITY_BASED
        )
        
        # Higher priority should get more allocation
        assert allocations["high_priority"] > allocations["medium_priority"]
        assert allocations["medium_priority"] > allocations["low_priority"]
        
        # Total should not exceed budget
        assert sum(allocations.values()) <= total_budget
    
    @pytest.mark.asyncio
    async def test_adaptive_budget_strategy(self, budget_loader):
        """Test adaptive token budget allocation."""
        loader = budget_loader
        
        prompt_names = ["high_priority", "medium_priority", "low_priority"]
        total_budget = 2000
        
        allocations = await loader.optimize_token_budget(
            prompts=prompt_names,
            total_budget=total_budget,
            strategy=TokenBudgetStrategy.ADAPTIVE
        )
        
        # Should consider both priority and token estimates
        assert allocations["high_priority"] > allocations["low_priority"]
        assert sum(allocations.values()) <= total_budget
        
        # All prompts should get some allocation
        for allocation in allocations.values():
            assert allocation > 0
    
    @pytest.mark.asyncio
    async def test_fixed_budget_strategy(self, budget_loader):
        """Test fixed token budget allocation."""
        loader = budget_loader
        
        prompt_names = ["high_priority", "medium_priority", "low_priority"]
        total_budget = 1200
        
        allocations = await loader.optimize_token_budget(
            prompts=prompt_names,
            total_budget=total_budget,
            strategy=TokenBudgetStrategy.FIXED
        )
        
        # All should get equal allocation
        expected_per_prompt = total_budget // 3
        for allocation in allocations.values():
            assert allocation == expected_per_prompt


class TestPromptValidation:
    """Test prompt validation functionality."""
    
    @pytest.fixture
    def validation_loader(self):
        """Setup loader for validation testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "system").mkdir(exist_ok=True)
            
            # Valid prompt
            valid_prompt = """# Valid Test Prompt

This is a valid prompt for {variable1} and {variable2}.
It has reasonable length and proper structure.
"""
            (temp_path / "system" / "valid_prompt.md").write_text(valid_prompt)
            
            # Large prompt that might exceed budget
            large_content = "This is a very large prompt. " * 1000
            large_prompt = f"# Large Prompt\n\n{large_content}"
            (temp_path / "system" / "large_prompt.md").write_text(large_prompt)
            
            with patch('src.ai.prompt_loader.RefMCP'), \
                 patch('src.ai.prompt_loader.MemoryBankMCP'), \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(prompts_dir=temp_dir)
                yield loader
    
    @pytest.mark.asyncio
    async def test_validate_valid_prompt(self, validation_loader):
        """Test validation of a valid prompt."""
        loader = validation_loader
        
        result = await loader.validate_prompt("valid_prompt", PromptType.SYSTEM)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "metadata" in result["info"]
        assert "token_count" in result["info"]
        assert "required_variables" in result["info"]
        
        # Should detect variables
        assert "variable1" in result["info"]["required_variables"]
        assert "variable2" in result["info"]["required_variables"]
    
    @pytest.mark.asyncio
    async def test_validate_large_prompt(self, validation_loader):
        """Test validation of prompt exceeding token budget."""
        loader = validation_loader
        
        result = await loader.validate_prompt("large_prompt", PromptType.SYSTEM)
        
        # Should have warnings or errors about size
        assert len(result["warnings"]) > 0 or len(result["errors"]) > 0
        
        # Should still provide info
        assert "token_count" in result["info"]
        assert result["info"]["token_count"] > loader.token_budget.prompt_allocation
    
    @pytest.mark.asyncio
    async def test_validate_nonexistent_prompt(self, validation_loader):
        """Test validation of non-existent prompt."""
        loader = validation_loader
        
        result = await loader.validate_prompt("nonexistent", PromptType.SYSTEM)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0]


class TestPromptExport:
    """Test prompt export functionality."""
    
    @pytest.fixture
    def export_loader(self):
        """Setup loader for export testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "system").mkdir(exist_ok=True)
            (temp_path / "chat").mkdir(exist_ok=True)
            
            # System prompt
            system_prompt = """---
version: "1.0.0"
author: "Export Test"
---

# System Export Test

This is a test system prompt.
"""
            (temp_path / "system" / "export_system.md").write_text(system_prompt)
            
            # Chat prompt
            chat_prompt = "You are a helpful chat assistant."
            (temp_path / "chat" / "export_chat.md").write_text(chat_prompt)
            
            with patch('src.ai.prompt_loader.RefMCP'), \
                 patch('src.ai.prompt_loader.MemoryBankMCP'), \
                 patch('src.ai.prompt_loader.TokenOptimizer'):
                
                loader = PromptLoader(prompts_dir=temp_dir)
                yield loader
    
    @pytest.mark.asyncio
    async def test_export_prompts_json(self, export_loader):
        """Test exporting prompts as JSON."""
        loader = export_loader
        
        result = await loader.export_prompts(
            output_format="json",
            include_metadata=True
        )
        
        assert isinstance(result, str)
        exported_data = json.loads(result)
        
        assert "prompts" in exported_data
        assert "metadata" in exported_data
        assert len(exported_data["prompts"]) == 2
        
        # Check structure
        for prompt_key, prompt_data in exported_data["prompts"].items():
            assert "content" in prompt_data
            assert "metadata" in prompt_data
    
    @pytest.mark.asyncio
    async def test_export_prompts_yaml(self, export_loader):
        """Test exporting prompts as YAML."""
        loader = export_loader
        
        result = await loader.export_prompts(
            output_format="yaml",
            include_metadata=True
        )
        
        assert isinstance(result, str)
        exported_data = yaml.safe_load(result)
        
        assert "prompts" in exported_data
        assert "metadata" in exported_data
        assert len(exported_data["prompts"]) == 2
    
    @pytest.mark.asyncio
    async def test_export_prompts_markdown(self, export_loader):
        """Test exporting prompts as Markdown."""
        loader = export_loader
        
        result = await loader.export_prompts(
            output_format="markdown",
            include_metadata=True
        )
        
        assert isinstance(result, str)
        assert "# Prompt Library Export" in result
        assert "system/export_system" in result
        assert "chat/export_chat" in result
        assert "**Type:**" in result
        assert "**Version:**" in result


class TestSingletonBehavior:
    """Test singleton behavior of prompt loader."""
    
    def test_get_prompt_loader_singleton(self):
        """Test that get_prompt_loader returns singleton instance."""
        with patch('src.ai.prompt_loader.RefMCP'), \
             patch('src.ai.prompt_loader.MemoryBankMCP'), \
             patch('src.ai.prompt_loader.TokenOptimizer'):
            
            loader1 = get_prompt_loader()
            loader2 = get_prompt_loader()
            
            assert loader1 is loader2
    
    def test_get_prompt_loader_with_params(self):
        """Test singleton creation with custom parameters."""
        with patch('src.ai.prompt_loader.RefMCP'), \
             patch('src.ai.prompt_loader.MemoryBankMCP'), \
             patch('src.ai.prompt_loader.TokenOptimizer'):
            
            # Clear singleton
            import src.ai.prompt_loader
            src.ai.prompt_loader.prompt_loader = None
            
            loader = get_prompt_loader(
                prompts_dir="custom_prompts",
                cache_enabled=False
            )
            
            assert loader.prompts_dir == Path("custom_prompts")
            assert loader.cache_enabled is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])