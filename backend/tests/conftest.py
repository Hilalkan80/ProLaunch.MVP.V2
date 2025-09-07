import pytest
import asyncio
import uuid
from datetime import datetime
import redis
import asyncpg
from typing import Dict, Any

from src.ai.context.manager import ContextManager
from src.ai.context.token_optimizer import TokenOptimizer
from src.ai.context.mcp_adapters import (
    initialize_mcp_adapters,
    memory_bank_mcp,
    postgresql_mcp,
    redis_mcp,
    ref_mcp
)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_connection():
    conn = await asyncpg.connect(
        user='test_user',
        password='test_password',
        database='test_db',
        host='localhost'
    )
    
    # Create test tables
    await conn.execute('''
        CREATE EXTENSION IF NOT EXISTS vector;
        
        CREATE TABLE IF NOT EXISTS memory_bank (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            context_type VARCHAR(50),
            data JSONB,
            timestamp TIMESTAMP,
            relevance_score FLOAT DEFAULT 1.0
        );
        
        CREATE TABLE IF NOT EXISTS knowledge_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            content TEXT,
            embedding vector(1536),
            metadata JSONB,
            created_at TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS session_contexts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID,
            session_id VARCHAR(100),
            messages JSONB,
            token_count INTEGER,
            updated_at TIMESTAMP
        );
    ''')
    
    yield conn
    
    # Cleanup
    await conn.execute('''
        DROP TABLE IF EXISTS memory_bank;
        DROP TABLE IF EXISTS knowledge_embeddings;
        DROP TABLE IF EXISTS session_contexts;
    ''')
    await conn.close()

@pytest.fixture
def redis_client():
    client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )
    yield client
    client.flushdb()
    client.close()

@pytest.fixture
async def context_manager(db_connection, redis_client):
    config = {
        'database_url': str(db_connection.dsn),
        'redis_url': 'redis://localhost:6379/0'
    }
    
    initialize_mcp_adapters(config)
    manager = ContextManager()
    yield manager
    
    # Cleanup
    await manager.clear_session()

@pytest.fixture
def token_optimizer():
    return TokenOptimizer()

@pytest.fixture
def sample_user():
    return {
        'id': str(uuid.uuid4()),
        'username': 'test_user'
    }

@pytest.fixture
def sample_message():
    return {
        'role': 'user',
        'content': 'Test message content',
        'timestamp': datetime.now().isoformat()
    }

@pytest.fixture
def sample_milestone():
    return {
        'id': str(uuid.uuid4()),
        'name': 'test_milestone',
        'description': 'Test milestone description',
        'status': 'active'
    }

@pytest.fixture
def sample_knowledge():
    return {
        'content': 'Test knowledge content that should be vectorized and stored',
        'metadata': {
            'source': 'test',
            'category': 'general',
            'timestamp': datetime.now().isoformat()
        }
    }