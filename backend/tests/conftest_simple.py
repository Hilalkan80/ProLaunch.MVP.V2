import pytest
import asyncio
import uuid
import os
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

# Set test environment variables
os.environ["TESTING"] = "true"
os.environ["OPENAI_API_KEY"] = "test_key_for_testing"
os.environ["ANTHROPIC_API_KEY"] = "test_key_for_testing"
os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_testing_only"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ENVIRONMENT"] = "test"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing"""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetch = AsyncMock()
    mock_conn.fetchrow = AsyncMock()
    return mock_conn

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    mock_client = Mock()
    mock_client.get = Mock(return_value=None)
    mock_client.set = Mock(return_value=True)
    mock_client.delete = Mock(return_value=True)
    mock_client.flushdb = Mock(return_value=True)
    return mock_client

@pytest.fixture
def sample_user():
    return {
        'id': str(uuid.uuid4()),
        'username': 'test_user',
        'email': 'test@example.com'
    }

@pytest.fixture
def sample_milestone():
    return {
        'id': str(uuid.uuid4()),
        'name': 'M0: Core Infrastructure',
        'description': 'Test milestone for M0 implementation',
        'status': 'in_progress',
        'target_completion_time': 60,  # seconds
        'created_at': datetime.now().isoformat()
    }

@pytest.fixture
def sample_task():
    return {
        'id': str(uuid.uuid4()),
        'title': 'Test Task',
        'description': 'Test task description',
        'status': 'pending',
        'milestone_id': str(uuid.uuid4()),
        'estimated_duration': 30  # seconds
    }

@pytest.fixture
def mock_mcp_adapters():
    """Mock MCP adapters for testing"""
    return {
        'memory_bank': Mock(),
        'redis': Mock(),
        'ref': Mock(),
        'puppeteer': Mock()
    }