import pytest
import asyncio
from datetime import datetime, timedelta
import uuid
import json

pytestmark = pytest.mark.asyncio

async def test_full_context_workflow(
    context_manager,
    sample_user,
    sample_message,
    sample_milestone,
    sample_knowledge
):
    """Test complete workflow across all context layers"""
    
    # 1. Add session message
    await context_manager.add_message(
        sample_message,
        metadata={'user_id': sample_user['id']}
    )
    
    # 2. Add milestone
    await context_manager.add_milestone(
        {
            'task': 'Test task',
            'result': 'Success'
        },
        milestone=sample_milestone['name'],
        metadata={'user_id': sample_user['id']}
    )
    
    # 3. Add knowledge
    await context_manager.add_knowledge(
        sample_knowledge['content'],
        metadata=sample_knowledge['metadata']
    )
    
    # 4. Get all context
    contexts = await context_manager.get_context(
        query="test content",
        milestone=sample_milestone['name'],
        user_id=sample_user['id']
    )
    
    # Verify all layers have content
    assert contexts['session']
    assert contexts['journey']
    assert contexts['knowledge']
    
    # Verify content matches
    assert any(
        msg['content'] == sample_message['content']
        for msg in contexts['session']
    )
    assert any(
        'Test task' in str(item)
        for item in contexts['journey']
    )
    assert any(
        sample_knowledge['content'] in str(item)
        for item in contexts['knowledge']
    )

async def test_token_limits_across_layers(
    context_manager,
    sample_user
):
    """Test token limits are enforced across all layers"""
    
    # Generate large content for each layer
    large_text = "Large content " * 1000
    
    # Session context (800 tokens)
    await context_manager.add_message(
        {'role': 'user', 'content': large_text},
        metadata={'user_id': sample_user['id']}
    )
    
    # Journey context (2000 tokens)
    await context_manager.add_milestone(
        {'description': large_text},
        milestone='test_milestone',
        metadata={'user_id': sample_user['id']}
    )
    
    # Knowledge context (1200 tokens)
    await context_manager.add_knowledge(
        large_text,
        metadata={'user_id': sample_user['id']}
    )
    
    # Get contexts and verify token limits
    contexts = await context_manager.get_context(
        user_id=sample_user['id']
    )
    
    token_usage = context_manager.get_token_usage()
    
    # Verify each layer respects its limit
    session_tokens = sum(
        len(str(msg)) // 4  # Rough estimate
        for msg in contexts['session']
    )
    assert session_tokens <= token_usage['session']
    
    journey_tokens = sum(
        len(str(item)) // 4
        for item in contexts['journey']
    )
    assert journey_tokens <= token_usage['journey']
    
    knowledge_tokens = sum(
        len(str(item)) // 4
        for item in contexts['knowledge']
    )
    assert knowledge_tokens <= token_usage['knowledge']

async def test_concurrent_context_access(
    context_manager,
    sample_user
):
    """Test concurrent access to context manager"""
    
    async def add_messages(count: int):
        for i in range(count):
            await context_manager.add_message(
                {
                    'role': 'user',
                    'content': f'Concurrent message {i}'
                },
                metadata={'user_id': sample_user['id']}
            )
            await asyncio.sleep(0.01)  # Simulate work
    
    # Run 5 concurrent tasks adding 10 messages each
    tasks = [
        add_messages(10)
        for _ in range(5)
    ]
    
    await asyncio.gather(*tasks)
    
    # Verify all messages were added
    contexts = await context_manager.get_context(
        user_id=sample_user['id']
    )
    
    # Count messages containing 'Concurrent message'
    concurrent_messages = sum(
        1 for msg in contexts['session']
        if 'Concurrent message' in str(msg)
    )
    
    # Should have at least some messages (considering token limits)
    assert concurrent_messages > 0

async def test_cross_context_interactions(
    context_manager,
    sample_user,
    sample_milestone
):
    """Test interactions between different context layers"""
    
    # 1. Add related content to all layers
    topic = "cross context test"
    
    await context_manager.add_message(
        {
            'role': 'user',
            'content': f'Question about {topic}'
        },
        metadata={'user_id': sample_user['id']}
    )
    
    await context_manager.add_milestone(
        {
            'topic': topic,
            'status': 'discussed'
        },
        milestone=sample_milestone['name'],
        metadata={'user_id': sample_user['id']}
    )
    
    await context_manager.add_knowledge(
        f'Knowledge about {topic}',
        metadata={
            'topic': topic,
            'user_id': sample_user['id']
        }
    )
    
    # 2. Query with related terms
    contexts = await context_manager.get_context(
        query=topic,
        milestone=sample_milestone['name'],
        user_id=sample_user['id']
    )
    
    # 3. Verify cross-context relevance
    assert any(topic in str(msg) for msg in contexts['session'])
    assert any(topic in str(item) for item in contexts['journey'])
    assert any(topic in str(item) for item in contexts['knowledge'])

async def test_context_persistence(
    context_manager,
    sample_user,
    redis_client
):
    """Test context persistence across sessions"""
    
    test_content = str(uuid.uuid4())  # Unique content
    
    # 1. Add content
    await context_manager.add_message(
        {
            'role': 'user',
            'content': test_content
        },
        metadata={'user_id': sample_user['id']}
    )
    
    # 2. Clear session
    await context_manager.clear_session()
    
    # 3. Create new context manager
    new_manager = context_manager.__class__()
    
    # 4. Try to retrieve content
    contexts = await new_manager.get_context(
        user_id=sample_user['id']
    )
    
    # 5. Verify content persisted
    assert any(
        test_content in str(msg)
        for msg in contexts['session']
    )