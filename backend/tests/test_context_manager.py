"""
Test Context Management System

Tests for the three-layer context management system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.services.context import ContextManager
from src.services.context.base import ContextEntry, ContextLayerConfig
from src.services.context.token_manager import TokenBudgetManager


@pytest.fixture
async def context_manager():
    """Create a context manager for testing."""
    manager = ContextManager(user_id="test_user", session_id="test_session")
    await manager.initialize()
    return manager


@pytest.fixture
def token_manager():
    """Create a token budget manager for testing."""
    return TokenBudgetManager(total_budget=4000)


class TestContextManager:
    """Test ContextManager functionality."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, context_manager):
        """Test context manager initialization."""
        assert context_manager.is_initialized
        assert context_manager.user_id == "test_user"
        assert context_manager.session_id == "test_session"
        assert context_manager.session_context is not None
        assert context_manager.journey_context is not None
        assert context_manager.knowledge_context is not None
    
    @pytest.mark.asyncio
    async def test_add_message(self, context_manager):
        """Test adding messages to context."""
        success = await context_manager.add_message(
            role="user",
            content="Test message content",
            metadata={"test": True}
        )
        
        assert success
        assert context_manager.metrics["total_updates"] == 1
        assert len(context_manager.update_queue) == 1
    
    @pytest.mark.asyncio
    async def test_get_context(self, context_manager):
        """Test retrieving context."""
        # Add some test messages
        await context_manager.add_message("user", "Hello, how are you?")
        await context_manager.add_message("assistant", "I'm doing well, thank you!")
        
        # Get context
        context = await context_manager.get_context(
            query="greeting",
            query_type="conversation"
        )
        
        assert context is not None
        assert len(context) > 0
    
    @pytest.mark.asyncio
    async def test_milestone_update(self, context_manager):
        """Test updating milestones."""
        success = await context_manager.update_milestone(
            milestone_id="M1",
            milestone_data={
                "title": "Test Milestone",
                "description": "Testing milestone functionality"
            }
        )
        
        assert success
        assert context_manager.journey_context.current_milestone == "M1"
    
    @pytest.mark.asyncio
    async def test_task_result(self, context_manager):
        """Test adding task results."""
        success = await context_manager.add_task_result(
            task="Implement feature X",
            result="Successfully implemented with tests",
            status="completed"
        )
        
        assert success
        assert len(context_manager.journey_context.task_history) > 0
    
    @pytest.mark.asyncio
    async def test_learning(self, context_manager):
        """Test adding knowledge."""
        success = await context_manager.learn(
            knowledge="User prefers dark mode",
            category="preferences",
            importance=0.8
        )
        
        assert success
        assert len(context_manager.knowledge_context.entries) > 0
    
    @pytest.mark.asyncio
    async def test_optimization(self, context_manager):
        """Test context optimization."""
        # Add multiple entries
        for i in range(10):
            await context_manager.add_message("user", f"Message {i}")
        
        # Optimize
        results = await context_manager.optimize_all_layers()
        
        assert results["session"] is not False
        assert results["journey"] is not False
        assert results["knowledge"] is not False
        assert context_manager.metrics["optimization_count"] == 1
    
    @pytest.mark.asyncio
    async def test_persistence(self, context_manager):
        """Test context persistence."""
        # Add some data
        await context_manager.add_message("user", "Test persistence")
        
        # Persist
        success = await context_manager.persist_all()
        
        assert success
    
    @pytest.mark.asyncio
    async def test_clear_session(self, context_manager):
        """Test clearing session context."""
        # Add session data
        await context_manager.add_message("user", "Session message")
        
        # Clear session
        success = await context_manager.clear_session()
        
        assert success
        assert len(context_manager.session_context.entries) == 0
    
    @pytest.mark.asyncio
    async def test_statistics(self, context_manager):
        """Test getting statistics."""
        stats = context_manager.get_statistics()
        
        assert "user_id" in stats
        assert "session_id" in stats
        assert "layers" in stats
        assert "token_allocation" in stats
        assert "metrics" in stats


class TestTokenBudgetManager:
    """Test TokenBudgetManager functionality."""
    
    def test_initialization(self, token_manager):
        """Test token manager initialization."""
        assert token_manager.total_budget == 4000
        assert "session" in token_manager.allocations
        assert "journey" in token_manager.allocations
        assert "knowledge" in token_manager.allocations
    
    def test_allocate_tokens(self, token_manager):
        """Test token allocation."""
        success, allocated = token_manager.allocate_tokens("session", 500)
        
        assert success
        assert allocated == 500
        assert token_manager.allocations["session"].used_tokens == 500
    
    def test_release_tokens(self, token_manager):
        """Test releasing tokens."""
        # Allocate first
        token_manager.allocate_tokens("session", 500)
        
        # Release
        success = token_manager.release_tokens("session", 200)
        
        assert success
        assert token_manager.allocations["session"].used_tokens == 300
    
    def test_rebalance_allocations(self, token_manager):
        """Test rebalancing allocations."""
        # Set some usage
        token_manager.allocate_tokens("session", 700)
        token_manager.allocate_tokens("journey", 500)
        
        # Rebalance
        new_allocations = token_manager.rebalance_allocations()
        
        assert sum(new_allocations.values()) <= token_manager.total_budget
        assert len(token_manager.optimization_history) == 1
    
    def test_optimize_for_query(self, token_manager):
        """Test query-specific optimization."""
        optimized = token_manager.optimize_for_query(
            "task_execution",
            {"session": 300, "journey": 1000, "knowledge": 400}
        )
        
        assert optimized["journey"] >= 1000
        assert sum(optimized.values()) <= token_manager.total_budget
    
    def test_set_priority(self, token_manager):
        """Test setting layer priority."""
        success = token_manager.set_priority("session", 0.9)
        
        assert success
        assert token_manager.allocations["session"].priority == 0.9
    
    def test_token_borrowing(self, token_manager):
        """Test borrowing tokens from lower priority layers."""
        # Use up session tokens
        token_manager.allocate_tokens("session", 800)
        
        # Try to allocate more (should borrow)
        success, allocated = token_manager.allocate_tokens("session", 200)
        
        # Should get partial allocation through borrowing
        assert allocated > 0
    
    def test_get_allocation_status(self, token_manager):
        """Test getting allocation status."""
        status = token_manager.get_allocation_status()
        
        assert "total_budget" in status
        assert "total_allocated" in status
        assert "total_used" in status
        assert "layers" in status
        assert len(status["layers"]) == 3
    
    def test_export_metrics(self, token_manager):
        """Test exporting metrics."""
        metrics = token_manager.export_metrics()
        
        assert "timestamp" in metrics
        assert "total_budget" in metrics
        assert "allocations" in metrics
        assert "efficiency_score" in metrics


class TestContextLayers:
    """Test individual context layer functionality."""
    
    @pytest.mark.asyncio
    async def test_session_context(self):
        """Test SessionContext layer."""
        from src.services.context.layers import SessionContext
        
        session = SessionContext("test_user", "test_session")
        
        # Add entry
        success = await session.add_entry(
            "Test session message",
            {"type": "message", "role": "user"}
        )
        
        assert success
        assert len(session.entries) == 1
        
        # Get context
        context = await session.get_context(max_tokens=400)
        assert context is not None
    
    @pytest.mark.asyncio
    async def test_journey_context(self):
        """Test JourneyContext layer."""
        from src.services.context.layers import JourneyContext
        
        journey = JourneyContext("test_user", "test_session")
        journey.current_milestone = "M1"
        
        # Add entry
        success = await journey.add_entry(
            "Completed task X",
            {"type": "task", "status": "completed"}
        )
        
        assert success
        assert len(journey.task_history) == 1
        
        # Get context
        context = await journey.get_context(max_tokens=1000)
        assert "CURRENT MILESTONE: M1" in context
    
    @pytest.mark.asyncio
    async def test_knowledge_context(self):
        """Test KnowledgeContext layer."""
        from src.services.context.layers import KnowledgeContext
        
        knowledge = KnowledgeContext("test_user", "test_session")
        
        # Add entry
        success = await knowledge.add_entry(
            "User prefers Python",
            {"category": "preferences", "importance": 0.8}
        )
        
        assert success
        assert "preferences" in knowledge.knowledge_graph
        
        # Get context
        context = await knowledge.get_context(max_tokens=600)
        assert context is not None


class TestMCPIntegrations:
    """Test MCP integration modules."""
    
    @pytest.mark.asyncio
    async def test_memory_bank_mcp(self):
        """Test MemoryBankMCP integration."""
        from src.services.mcp_integrations import MemoryBankMCP
        
        memory_bank = MemoryBankMCP()
        
        # Store memory
        success = await memory_bank.store_memory(
            key="test_memory",
            content="Test content",
            metadata={"type": "test"}
        )
        
        assert success
        
        # Retrieve memory
        memory = await memory_bank.retrieve_memory("test_memory")
        assert memory is not None
        assert memory["content"] == "Test content"
    
    @pytest.mark.asyncio
    async def test_ref_mcp(self):
        """Test RefMCP optimization."""
        from src.services.mcp_integrations import RefMCP
        
        ref_mcp = RefMCP()
        
        # Test content optimization
        long_content = "This is a very long content " * 100
        optimized = await ref_mcp.optimize_content(
            content=long_content,
            max_tokens=100
        )
        
        assert len(optimized) < len(long_content)
        
        # Test reference extraction
        content_with_refs = "Check https://example.com and function_name()"
        refs = await ref_mcp.extract_references(content_with_refs)
        
        assert len(refs["urls"]) > 0
        assert len(refs["functions"]) > 0


@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """Test complete context management workflow."""
    manager = ContextManager("test_user", "test_session")
    await manager.initialize()
    
    # Simulate a conversation
    await manager.add_message("user", "I want to work on milestone M1")
    await manager.update_milestone("M1", {"title": "Build feature X"})
    
    # Add some task progress
    await manager.add_task_result(
        "Setup development environment",
        "Environment configured successfully",
        "completed"
    )
    
    # Learn something about the user
    await manager.learn(
        "User prefers TDD approach",
        category="development_style",
        importance=0.9
    )
    
    # Get context for different query types
    conv_context = await manager.get_context(query_type="conversation")
    task_context = await manager.get_context(query_type="task_execution")
    knowledge_context = await manager.get_context(query_type="knowledge_query")
    
    assert conv_context is not None
    assert task_context is not None
    assert knowledge_context is not None
    
    # Optimize and persist
    await manager.optimize_all_layers()
    success = await manager.persist_all()
    
    assert success
    
    # Get final statistics
    stats = manager.get_statistics()
    assert stats["metrics"]["total_updates"] > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])