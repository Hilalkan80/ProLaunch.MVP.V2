import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import uuid
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from src.ai.context.manager import ContextManager
from src.ai.context.token_optimizer import TokenOptimizer
from src.ai.context.layers import SessionContext, JourneyContext, KnowledgeContext
from src.ai.context.mcp_adapters import MemoryBankMCP, PostgreSQLMCP, RedisMCP, RefMCP

@pytest_asyncio.fixture
async def context_manager(context_manager_with_mocks):
    return context_manager_with_mocks

@pytest.fixture
def token_optimizer():
    return TokenOptimizer()

async def test_session_context_add_and_get(context_manager):
    user_id = str(uuid.uuid4())
    test_message = {
        'role': 'user',
        'content': 'Test message'
    }
    
    # Add message
    success = await context_manager.add_message(
        test_message,
        metadata={'user_id': user_id}
    )
    assert success
    
    # Get context
    contexts = await context_manager.get_context(user_id=user_id)
    assert contexts['session']
    assert len(contexts['session']) > 0
    assert contexts['session'][0]['content'] == 'Test message'

async def test_journey_context_milestone(context_manager):
    milestone = 'test_milestone'
    content = {
        'task': 'Test task',
        'status': 'completed'
    }
    
    # Add milestone
    success = await context_manager.add_milestone(
        content,
        milestone=milestone
    )
    assert success
    
    # Get context with milestone
    contexts = await context_manager.get_context(milestone=milestone)
    assert contexts['journey']
    assert len(contexts['journey']) > 0
    found = False
    for item in contexts['journey']:
        if item.get('task') == 'Test task':
            found = True
    assert found

async def test_knowledge_context_add_and_query(context_manager):
    test_knowledge = "Important test knowledge that should be retrievable"
    
    # Add knowledge
    success = await context_manager.add_knowledge(test_knowledge)
    assert success
    
    # Query knowledge
    contexts = await context_manager.get_context(
        query="test knowledge"
    )
    assert contexts['knowledge']
    assert len(contexts['knowledge']) > 0
    assert any(
        test_knowledge in str(item)
        for item in contexts['knowledge']
    )

def test_token_optimization(token_optimizer):
    # Test token counting
    text = "This is a test message"
    tokens = token_optimizer.count_tokens(text)
    assert tokens > 0
    
    # Test message optimization
    messages = [
        {'role': 'user', 'content': 'A' * 1000},
        {'role': 'assistant', 'content': 'B' * 1000}
    ]
    optimized = token_optimizer.optimize_messages(messages, 100)
    assert len(optimized) > 0
    for msg in optimized:
        assert token_optimizer.count_tokens(msg['content']) <= 100

async def test_context_token_limits(context_manager, token_optimizer):
    # Get token usage
    usage = context_manager.get_token_usage()
    assert usage['session'] == 800
    assert usage['journey'] == 2000
    assert usage['knowledge'] == 1200
    assert usage['total'] == 4000
    
    # Test session context limit
    large_message = {
        'role': 'user',
        'content': 'A' * 5000  # Should be truncated
    }
    await context_manager.add_message(large_message)
    
    contexts = await context_manager.get_context()
    session_tokens = sum(
        token_optimizer.count_tokens(str(msg))
        for msg in contexts['session']
    )
    assert session_tokens <= 800


# Enhanced Unit Tests

async def test_token_counting_accuracy(token_optimizer):
    """Test token counting accuracy with various content types."""
    # Test empty content
    assert token_optimizer.count_tokens("") == 0
    
    # Test simple text
    simple_text = "Hello world"
    tokens = token_optimizer.count_tokens(simple_text)
    assert tokens > 0
    assert tokens < 10  # Should be reasonable for simple text
    
    # Test complex text with special characters
    complex_text = "Hello! How are you? I'm doing great! 😊 #hashtag @mention"
    complex_tokens = token_optimizer.count_tokens(complex_text)
    assert complex_tokens > tokens
    
    # Test code
    code_text = "def function(param): return param * 2"
    code_tokens = token_optimizer.count_tokens(code_text)
    assert code_tokens > 0
    
    # Test very long text
    long_text = "word " * 1000
    long_tokens = token_optimizer.count_tokens(long_text)
    assert long_tokens > 1000


async def test_token_optimization_strategies(token_optimizer, sample_messages):
    """Test different token optimization strategies."""
    # Test with budget larger than content
    large_budget = 10000
    optimized_large = token_optimizer.optimize_messages(sample_messages, large_budget)
    assert len(optimized_large) == len(sample_messages)
    
    # Test with very small budget
    small_budget = 50
    optimized_small = token_optimizer.optimize_messages(sample_messages, small_budget)
    assert len(optimized_small) <= len(sample_messages)
    
    total_tokens = sum(
        token_optimizer.count_tokens(msg['content']) 
        for msg in optimized_small
    )
    assert total_tokens <= small_budget
    
    # Test with zero budget
    optimized_zero = token_optimizer.optimize_messages(sample_messages, 0)
    assert len(optimized_zero) == 0
    
    # Test message priority (most recent first)
    medium_budget = 200
    optimized_medium = token_optimizer.optimize_messages(sample_messages, medium_budget)
    if optimized_medium:
        # Should contain the most recent messages
        last_original = sample_messages[-1]['content']
        found_last = any(msg['content'] == last_original for msg in optimized_medium)
        assert found_last


async def test_context_truncation(token_optimizer):
    """Test content truncation functionality."""
    original_text = "This is a test sentence that will be truncated."
    
    # Test normal truncation
    truncated = token_optimizer.truncate_to_token_limit(original_text, 5)
    assert len(truncated) < len(original_text)
    
    # Test truncation with limit larger than content
    long_limit = 1000
    not_truncated = token_optimizer.truncate_to_token_limit(original_text, long_limit)
    assert not_truncated == original_text
    
    # Test truncation with zero limit
    empty_truncated = token_optimizer.truncate_to_token_limit(original_text, 0)
    assert empty_truncated == ""


async def test_session_context_lifecycle(context_manager):
    """Test complete session context lifecycle."""
    user_id = str(uuid.uuid4())
    session_messages = [
        {'role': 'user', 'content': 'First message'},
        {'role': 'assistant', 'content': 'First response'},
        {'role': 'user', 'content': 'Second message'},
        {'role': 'assistant', 'content': 'Second response'}
    ]
    
    # Add messages to session
    for msg in session_messages:
        success = await context_manager.add_message(
            msg, metadata={'user_id': user_id}
        )
        assert success
    
    # Retrieve session context
    contexts = await context_manager.get_context(user_id=user_id)
    assert 'session' in contexts
    assert len(contexts['session']) > 0
    
    # Clear session
    await context_manager.clear_session()
    
    # Verify session is cleared (implementation dependent)
    # This test depends on how clear_session is implemented


async def test_journey_context_milestones(context_manager, journey_milestones):
    """Test journey context with multiple milestones."""
    # Add milestones
    for milestone_data in journey_milestones:
        success = await context_manager.add_milestone(
            milestone_data['content'],
            milestone=milestone_data['milestone']
        )
        assert success
    
    # Query by specific milestone
    for milestone_data in journey_milestones:
        contexts = await context_manager.get_context(
            milestone=milestone_data['milestone']
        )
        assert 'journey' in contexts
        assert len(contexts['journey']) > 0
    
    # Query without milestone filter
    all_contexts = await context_manager.get_context()
    assert 'journey' in all_contexts


async def test_knowledge_context_semantic_search(context_manager, knowledge_base):
    """Test knowledge context semantic search functionality."""
    # Add knowledge base content
    for knowledge in knowledge_base:
        success = await context_manager.add_knowledge(knowledge)
        assert success
    
    # Test semantic search queries
    search_queries = [
        "programming language",
        "web framework",
        "database system",
        "caching solution",
        "containerization"
    ]
    
    for query in search_queries:
        contexts = await context_manager.get_context(query=query)
        assert 'knowledge' in contexts
        # Should return relevant knowledge (mocked behavior)
        assert len(contexts['knowledge']) > 0


def test_context_layer_token_limits():
    """Test individual context layer token limits."""
    # Test SessionContext
    session_context = SessionContext()
    assert session_context.token_limit == 800
    
    # Test JourneyContext
    journey_context = JourneyContext()
    assert journey_context.token_limit == 2000
    
    # Test KnowledgeContext
    knowledge_context = KnowledgeContext()
    assert knowledge_context.token_limit == 1200


def test_context_optimization(token_optimizer):
    """Test context optimization with different content types."""
    mixed_context = {
        'system': 'You are a helpful assistant.',
        'user': 'Help me with my project.',
        'assistant': 'I would be happy to help you!',
        'tool': 'Tool output: Success'
    }
    
    # Test with adequate budget
    adequate_budget = 1000
    optimized = token_optimizer.optimize_context(mixed_context, adequate_budget)
    assert len(optimized) == len(mixed_context)
    
    # Test with limited budget
    limited_budget = 50
    optimized_limited = token_optimizer.optimize_context(mixed_context, limited_budget)
    assert len(optimized_limited) <= len(mixed_context)
    
    # Verify priority order (system should be prioritized)
    if 'system' in mixed_context and optimized_limited:
        assert 'system' in optimized_limited


async def test_concurrent_context_access(context_manager, concurrent_users):
    """Test concurrent access to context management."""
    async def add_user_message(user_id: str, message_num: int):
        """Add a message for a specific user."""
        message = {
            'role': 'user',
            'content': f'Message {message_num} from user {user_id}'
        }
        return await context_manager.add_message(
            message, 
            metadata={'user_id': user_id}
        )
    
    # Create concurrent tasks
    tasks = []
    for i, user_id in enumerate(concurrent_users[:5]):  # Limit for testing
        task = add_user_message(user_id, i)
        tasks.append(task)
    
    # Execute concurrently
    results = await asyncio.gather(*tasks)
    
    # All operations should succeed
    assert all(results)
    
    # Verify each user can retrieve their context
    for user_id in concurrent_users[:5]:
        contexts = await context_manager.get_context(user_id=user_id)
        assert 'session' in contexts


async def test_edge_cases(context_manager, token_optimizer):
    """Test edge cases and boundary conditions."""
    # Test with None content
    with pytest.raises((ValueError, TypeError, AttributeError)):
        await context_manager.add_message(None)
    
    # Test with empty content
    empty_message = {'role': 'user', 'content': ''}
    result = await context_manager.add_message(empty_message)
    # Should handle gracefully (implementation dependent)
    
    # Test with malformed message
    malformed_message = {'invalid_key': 'value'}
    try:
        await context_manager.add_message(malformed_message)
    except (KeyError, ValueError):
        pass  # Expected to fail
    
    # Test token optimization with empty messages
    empty_messages = []
    optimized_empty = token_optimizer.optimize_messages(empty_messages, 100)
    assert len(optimized_empty) == 0
    
    # Test with negative token budget
    negative_budget = -100
    optimized_negative = token_optimizer.optimize_messages([empty_message], negative_budget)
    assert len(optimized_negative) == 0


async def test_metadata_handling(context_manager):
    """Test metadata handling across all context layers."""
    user_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Test session metadata
    session_metadata = {
        'user_id': user_id,
        'session_start': timestamp,
        'device_info': 'test-device'
    }
    
    message = {'role': 'user', 'content': 'Test message with metadata'}
    success = await context_manager.add_message(message, metadata=session_metadata)
    assert success
    
    # Test journey metadata
    journey_metadata = {
        'milestone': 'test_milestone',
        'project_id': str(uuid.uuid4()),
        'phase': 'development'
    }
    
    milestone_content = {'task': 'Test task', 'status': 'completed'}
    success = await context_manager.add_milestone(
        milestone_content,
        milestone='test_milestone',
        metadata=journey_metadata
    )
    assert success
    
    # Test knowledge metadata
    knowledge_metadata = {
        'source': 'documentation',
        'topic': 'testing',
        'confidence': 0.95
    }
    
    knowledge = "This is test knowledge with metadata"
    success = await context_manager.add_knowledge(knowledge, metadata=knowledge_metadata)
    assert success


class TestMCPAdapters:
    """Test MCP adapter implementations."""
    
    async def test_memory_bank_mcp_operations(self, mock_memory_bank_mcp):
        """Test Memory Bank MCP store and retrieve operations."""
        # Test store operation
        store_result = await mock_memory_bank_mcp.execute(
            "store",
            user_id="test-user",
            context_type="session",
            data={"test": "data"}
        )
        assert store_result["success"] is True
        
        # Test retrieve operation
        retrieve_result = await mock_memory_bank_mcp.execute(
            "retrieve",
            user_id="test-user",
            context_type="session"
        )
        assert isinstance(retrieve_result, list)
    
    async def test_postgresql_mcp_vector_operations(self, mock_postgresql_mcp):
        """Test PostgreSQL MCP vector operations."""
        # Test store embedding
        store_result = await mock_postgresql_mcp.execute(
            "store_embedding",
            content="test content",
            embedding=[0.1, 0.2, 0.3],
            metadata={"test": "metadata"}
        )
        assert store_result["success"] is True
        
        # Test vector search
        search_result = await mock_postgresql_mcp.execute(
            "vector_search",
            query_embedding=[0.1, 0.2, 0.3],
            limit=5
        )
        assert isinstance(search_result, list)
    
    async def test_redis_mcp_cache_operations(self, mock_redis_mcp):
        """Test Redis MCP cache operations."""
        # Test cache set
        set_result = await mock_redis_mcp.execute(
            "cache_set",
            key="test:key",
            data={"test": "data"},
            ttl_seconds=300
        )
        assert set_result["success"] is True
        
        # Test cache get
        get_result = await mock_redis_mcp.execute(
            "cache_get",
            key="test:key"
        )
        assert get_result == {"test": "data"}
        
        # Test publish
        publish_result = await mock_redis_mcp.execute(
            "publish",
            channel="test:channel",
            data={"test": "message"}
        )
        assert publish_result["success"] is True
    
    async def test_ref_mcp_optimization(self, mock_ref_mcp):
        """Test Ref MCP prompt optimization."""
        # Test prompt optimization
        optimize_result = await mock_ref_mcp.execute(
            "optimize_prompt",
            prompt="This is a test prompt for optimization",
            max_tokens=100
        )
        assert "optimized_prompt" in optimize_result
        assert "estimated_tokens" in optimize_result
        assert isinstance(optimize_result["estimated_tokens"], int)