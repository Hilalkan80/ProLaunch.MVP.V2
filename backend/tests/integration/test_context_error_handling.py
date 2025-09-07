import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime
import uuid

pytestmark = pytest.mark.asyncio

async def test_database_connection_failure(
    context_manager,
    sample_user,
    sample_message
):
    """Test handling of database connection failures"""
    
    with patch('asyncpg.connect', side_effect=Exception("Connection failed")):
        # Should handle DB failure gracefully
        result = await context_manager.add_message(
            sample_message,
            metadata={'user_id': sample_user['id']}
        )
        assert not result  # Should return False on failure
        
        # Should still be able to get cached data
        contexts = await context_manager.get_context(
            user_id=sample_user['id']
        )
        assert isinstance(contexts, dict)

async def test_redis_connection_failure(
    context_manager,
    sample_user,
    sample_message
):
    """Test handling of Redis connection failures"""
    
    with patch('redis.Redis.setex', side_effect=Exception("Redis error")):
        # Should still store in database even if cache fails
        result = await context_manager.add_message(
            sample_message,
            metadata={'user_id': sample_user['id']}
        )
        assert result  # Should succeed using DB fallback
        
        contexts = await context_manager.get_context(
            user_id=sample_user['id']
        )
        assert contexts['session']

async def test_invalid_data_handling(
    context_manager,
    sample_user
):
    """Test handling of invalid data inputs"""
    
    # Test null message
    result = await context_manager.add_message(
        None,
        metadata={'user_id': sample_user['id']}
    )
    assert not result
    
    # Test empty message
    result = await context_manager.add_message(
        {},
        metadata={'user_id': sample_user['id']}
    )
    assert not result
    
    # Test invalid JSON
    result = await context_manager.add_message(
        object(),  # Non-serializable object
        metadata={'user_id': sample_user['id']}
    )
    assert not result

async def test_concurrent_error_handling(
    context_manager,
    sample_user
):
    """Test error handling during concurrent operations"""
    
    async def faulty_operation():
        await context_manager.add_message(
            {'role': 'user', 'content': str(uuid.uuid4())},
            metadata={'user_id': sample_user['id']}
        )
        if random.random() < 0.5:  # Simulate random failures
            raise Exception("Random failure")
    
    # Run multiple operations concurrently
    tasks = [faulty_operation() for _ in range(10)]
    
    # Some should fail, but it shouldn't crash
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify we can still use the context manager
    contexts = await context_manager.get_context(
        user_id=sample_user['id']
    )
    assert isinstance(contexts, dict)

async def test_token_limit_violation_handling(
    context_manager,
    sample_user
):
    """Test handling of content exceeding token limits"""
    
    # Generate content way over the limit
    huge_content = "test " * 10000  # Way over any layer's limit
    
    # Session context (800 token limit)
    result = await context_manager.add_message(
        {'role': 'user', 'content': huge_content},
        metadata={'user_id': sample_user['id']}
    )
    assert result  # Should succeed but truncate
    
    contexts = await context_manager.get_context(
        user_id=sample_user['id']
    )
    
    # Verify content was truncated, not rejected
    session_content = contexts['session'][0]['content']
    assert len(session_content) < len(huge_content)

async def test_vector_store_failure_handling(
    context_manager,
    sample_user,
    sample_knowledge
):
    """Test handling of vector store operation failures"""
    
    with patch('src.ai.context.mcp_adapters.PostgreSQLMCP.execute', 
               side_effect=Exception("Vector store error")):
        # Should handle vector store failure gracefully
        result = await context_manager.add_knowledge(
            sample_knowledge['content'],
            metadata={'user_id': sample_user['id']}
        )
        assert not result  # Should indicate failure
        
        # Should still be able to get other contexts
        contexts = await context_manager.get_context(
            user_id=sample_user['id']
        )
        assert isinstance(contexts, dict)

async def test_data_corruption_handling(
    context_manager,
    sample_user
):
    """Test handling of corrupted data in storage"""
    
    # Simulate corrupted JSON in database
    corrupted_data = "}{invalid json}{"
    
    with patch('src.ai.context.mcp_adapters.MemoryBankMCP.execute',
               return_value=[{'data': corrupted_data}]):
        # Should handle corrupted data gracefully
        contexts = await context_manager.get_context(
            user_id=sample_user['id']
        )
        assert isinstance(contexts, dict)
        assert isinstance(contexts['session'], list)  # Should return empty list

async def test_mcp_timeout_handling(
    context_manager,
    sample_user,
    sample_message
):
    """Test handling of MCP timeouts"""
    
    async def slow_operation(*args, **kwargs):
        await asyncio.sleep(2)  # Simulate slow operation
        return {}
    
    with patch('src.ai.context.mcp_adapters.RedisMCP.execute',
               side_effect=slow_operation):
        # Should timeout and fallback to database
        result = await context_manager.add_message(
            sample_message,
            metadata={'user_id': sample_user['id']}
        )
        assert result  # Should succeed using DB fallback