"""
Comprehensive Test Configuration for Milestone System

Centralized pytest configuration with fixtures, utilities, and test setup
for all milestone system tests including unit, integration, and performance tests.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List, Optional
import logging

# Database imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Model imports
from backend.src.models.milestone import (
    Base, Milestone, MilestoneDependency, UserMilestone,
    MilestoneStatus, MilestoneType, MilestoneProgressLog,
    UserMilestoneArtifact, MilestoneArtifact, MilestoneCache
)
from backend.src.models.user import User, SubscriptionTier

# Service imports
from backend.src.services.milestone_service import MilestoneService
from backend.src.services.milestone_cache import MilestoneCacheService
from backend.src.services.dependency_manager import DependencyManager


# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestConfig:
    """Test configuration constants and settings."""
    
    # Database settings
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    TEST_DATABASE_ECHO = False
    
    # Performance test settings
    PERFORMANCE_TEST_TIMEOUT = 300  # 5 minutes
    PERFORMANCE_BASELINE_DB_OPS_PER_SEC = 1000
    PERFORMANCE_BASELINE_CACHE_OPS_PER_SEC = 10000
    
    # Test data settings
    DEFAULT_USER_COUNT = 10
    DEFAULT_MILESTONE_COUNT = 5
    DEFAULT_DEPENDENCY_COUNT = 3
    
    # Feature flags for test environments
    ENABLE_CACHE_TESTS = True
    ENABLE_PERFORMANCE_TESTS = True
    ENABLE_INTEGRATION_TESTS = True


class MockRedisClient:
    """Advanced Mock Redis client for comprehensive testing."""
    
    def __init__(self):
        self._cache = {}
        self._pub_sub_channels = {}
        self._locks = {}
        self._sorted_sets = {}
        self._operation_log = []
        self._error_mode = False
        self._latency_simulation = 0
        self._memory_usage = 0
    
    async def get_cache(self, key: str):
        """Get value from cache with optional latency simulation."""
        self._log_operation("GET", key)
        await self._simulate_latency()
        
        if self._error_mode:
            raise Exception("Simulated Redis error")
        
        return self._cache.get(key)
    
    async def set_cache(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with optional latency simulation."""
        self._log_operation("SET", key, value, ttl)
        await self._simulate_latency()
        
        if self._error_mode:
            raise Exception("Simulated Redis error")
        
        self._cache[key] = {
            'value': value,
            'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
        }
        
        # Simulate memory usage
        import sys
        self._memory_usage += sys.getsizeof(value)
        
        return True
    
    async def delete_cache(self, key: str):
        """Delete value from cache."""
        self._log_operation("DEL", key)
        await self._simulate_latency()
        
        if self._error_mode:
            raise Exception("Simulated Redis error")
        
        deleted_item = self._cache.pop(key, None)
        if deleted_item:
            import sys
            self._memory_usage -= sys.getsizeof(deleted_item['value'])
        
        return deleted_item is not None
    
    async def publish(self, channel: str, message: Any):
        """Publish message to channel."""
        self._log_operation("PUB", channel, message)
        await self._simulate_latency()
        
        if channel not in self._pub_sub_channels:
            self._pub_sub_channels[channel] = []
        
        self._pub_sub_channels[channel].append({
            'message': message,
            'timestamp': datetime.utcnow()
        })
        
        return len(self._pub_sub_channels.get(channel, []))
    
    async def lock(self, key: str, ttl: int = 300):
        """Acquire distributed lock."""
        self._log_operation("LOCK", key, ttl)
        await self._simulate_latency()
        
        if key not in self._locks:
            lock_token = f"lock_{uuid4().hex[:8]}"
            self._locks[key] = {
                'token': lock_token,
                'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
            }
            return lock_token
        
        return None
    
    async def unlock(self, key: str, token: str):
        """Release distributed lock."""
        self._log_operation("UNLOCK", key, token)
        await self._simulate_latency()
        
        if key in self._locks and self._locks[key]['token'] == token:
            del self._locks[key]
            return True
        
        return False
    
    # Configuration methods for testing
    def set_error_mode(self, enabled: bool):
        """Enable/disable error simulation."""
        self._error_mode = enabled
    
    def set_latency_simulation(self, milliseconds: int):
        """Set artificial latency for operations."""
        self._latency_simulation = milliseconds
    
    def get_operation_log(self):
        """Get log of all operations."""
        return self._operation_log.copy()
    
    def clear_operation_log(self):
        """Clear operation log."""
        self._operation_log.clear()
    
    def get_memory_usage(self):
        """Get simulated memory usage."""
        return self._memory_usage
    
    def get_pub_sub_messages(self, channel: str):
        """Get published messages for channel."""
        return self._pub_sub_channels.get(channel, [])
    
    def clear_all_data(self):
        """Clear all cached data and logs."""
        self._cache.clear()
        self._pub_sub_channels.clear()
        self._locks.clear()
        self._sorted_sets.clear()
        self._operation_log.clear()
        self._memory_usage = 0
    
    # Internal methods
    def _log_operation(self, operation: str, *args):
        """Log operation for analysis."""
        self._operation_log.append({
            'operation': operation,
            'args': args,
            'timestamp': datetime.utcnow()
        })
    
    async def _simulate_latency(self):
        """Simulate network latency."""
        if self._latency_simulation > 0:
            await asyncio.sleep(self._latency_simulation / 1000.0)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db_engine():
    """Create test database engine with optimized settings."""
    engine = create_async_engine(
        TestConfig.TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=TestConfig.TEST_DATABASE_ECHO,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    """Create isolated database session for each test."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()  # Rollback any uncommitted changes


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client with full functionality."""
    return MockRedisClient()


@pytest.fixture
async def cache_service(mock_redis_client):
    """Create milestone cache service with mock Redis."""
    return MilestoneCacheService(mock_redis_client)


@pytest.fixture
async def milestone_service(test_db_session, cache_service):
    """Create milestone service with database and cache."""
    return MilestoneService(test_db_session, cache_service)


@pytest.fixture
async def dependency_manager(test_db_session, cache_service, mock_redis_client):
    """Create dependency manager with full dependencies."""
    return DependencyManager(test_db_session, cache_service, mock_redis_client)


# User fixtures
@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": uuid4(),
        "email": "test@example.com",
        "username": "testuser",
        "subscription_tier": SubscriptionTier.PREMIUM,
        "is_active": True,
        "created_at": datetime.utcnow()
    }


@pytest.fixture
async def test_user(test_db_session, sample_user_data):
    """Create test user in database."""
    user = User(**sample_user_data)
    test_db_session.add(user)
    await test_db_session.commit()
    await test_db_session.refresh(user)
    return user


@pytest.fixture
async def test_users(test_db_session):
    """Create multiple test users."""
    users = []
    for i in range(TestConfig.DEFAULT_USER_COUNT):
        user = User(
            id=uuid4(),
            email=f"testuser{i}@example.com",
            username=f"testuser{i}",
            subscription_tier=SubscriptionTier.PREMIUM if i % 2 == 0 else SubscriptionTier.FREE,
            is_active=True
        )
        users.append(user)
        test_db_session.add(user)
    
    await test_db_session.commit()
    
    for user in users:
        await test_db_session.refresh(user)
    
    return users


# Milestone fixtures
@pytest.fixture
def sample_milestone_data():
    """Sample milestone data for testing."""
    return {
        "id": uuid4(),
        "code": "TEST_M1",
        "name": "Test Milestone",
        "description": "A milestone for testing purposes",
        "milestone_type": MilestoneType.PAID,
        "order_index": 1,
        "estimated_minutes": 60,
        "processing_time_limit": 300,
        "is_active": True,
        "requires_payment": True,
        "auto_unlock": False,
        "prompt_template": {
            "steps": [
                {"id": "step1", "name": "First Step", "description": "Complete first step"},
                {"id": "step2", "name": "Second Step", "description": "Complete second step"},
                {"id": "step3", "name": "Final Step", "description": "Complete final step"}
            ],
            "context_requirements": ["business_idea", "market_research"],
            "validation_rules": {"min_quality_score": 0.7}
        },
        "output_schema": {
            "type": "object",
            "required": ["analysis_result", "recommendations"],
            "properties": {
                "analysis_result": {"type": "object"},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        },
        "validation_rules": {
            "required_data_completeness": 0.8,
            "min_processing_time": 30,
            "max_processing_time": 3600
        }
    }


@pytest.fixture
async def test_milestone(test_db_session, sample_milestone_data):
    """Create test milestone in database."""
    milestone = Milestone(**sample_milestone_data)
    test_db_session.add(milestone)
    await test_db_session.commit()
    await test_db_session.refresh(milestone)
    return milestone


@pytest.fixture
async def test_milestone_chain(test_db_session):
    """Create chain of milestones with dependencies."""
    milestones = {}
    
    # Create milestone chain: M0 -> M1 -> M2 -> M3
    milestone_specs = [
        ("M0", "Foundation", MilestoneType.FREE, False, 0),
        ("M1", "Market Analysis", MilestoneType.PAID, True, 1),
        ("M2", "Business Model", MilestoneType.PAID, True, 2),
        ("M3", "Financial Planning", MilestoneType.PAID, True, 3),
    ]
    
    for code, name, type_, requires_payment, order in milestone_specs:
        milestone = Milestone(
            id=uuid4(),
            code=code,
            name=name,
            milestone_type=type_,
            requires_payment=requires_payment,
            order_index=order,
            is_active=True,
            estimated_minutes=60,
            prompt_template={"steps": [f"{code.lower()}_step1", f"{code.lower()}_step2"]}
        )
        milestones[code] = milestone
        test_db_session.add(milestone)
    
    await test_db_session.commit()
    
    # Create dependencies: M1->M0, M2->M1, M3->M2
    dependencies = [
        (milestones["M1"], milestones["M0"]),
        (milestones["M2"], milestones["M1"]),
        (milestones["M3"], milestones["M2"])
    ]
    
    for milestone, dependency in dependencies:
        dep = MilestoneDependency(
            milestone_id=milestone.id,
            dependency_id=dependency.id,
            is_required=True,
            minimum_completion_percentage=100.0
        )
        test_db_session.add(dep)
    
    await test_db_session.commit()
    
    # Refresh all milestones
    for milestone in milestones.values():
        await test_db_session.refresh(milestone)
    
    return milestones


@pytest.fixture
async def user_milestone_in_progress(test_db_session, test_user, test_milestone):
    """Create user milestone in progress state."""
    user_milestone = UserMilestone(
        id=uuid4(),
        user_id=test_user.id,
        milestone_id=test_milestone.id,
        status=MilestoneStatus.IN_PROGRESS,
        completion_percentage=50.0,
        current_step=2,
        total_steps=3,
        started_at=datetime.utcnow() - timedelta(hours=1),
        time_spent_seconds=3600,
        checkpoint_data={
            "step1": {"completed": True, "data": "step 1 completed"},
            "step2": {"completed": True, "data": "step 2 completed"},
            "step3": {"completed": False, "progress": 0.0}
        },
        user_inputs={
            "business_idea": "AI-powered productivity tool",
            "target_market": "Remote teams"
        }
    )
    
    test_db_session.add(user_milestone)
    await test_db_session.commit()
    await test_db_session.refresh(user_milestone)
    
    return user_milestone


# Test data generators
@pytest.fixture
def milestone_progress_factory():
    """Factory function to create milestone progress data."""
    def create_progress(
        status: MilestoneStatus = MilestoneStatus.IN_PROGRESS,
        completion_percentage: float = 50.0,
        current_step: int = 2,
        total_steps: int = 4,
        quality_score: Optional[float] = None,
        **kwargs
    ):
        return {
            "status": status,
            "completion_percentage": completion_percentage,
            "current_step": current_step,
            "total_steps": total_steps,
            "started_at": datetime.utcnow().isoformat(),
            "last_accessed_at": datetime.utcnow().isoformat(),
            "time_spent_seconds": 1800,
            "quality_score": quality_score,
            "checkpoint_data": kwargs.get("checkpoint_data", {}),
            "user_inputs": kwargs.get("user_inputs", {}),
            **kwargs
        }
    
    return create_progress


@pytest.fixture
def milestone_tree_factory():
    """Factory function to create milestone tree data."""
    def create_tree(milestone_count: int = 5, completion_ratio: float = 0.4):
        milestones = []
        completed_count = int(milestone_count * completion_ratio)
        
        for i in range(milestone_count):
            status = MilestoneStatus.COMPLETED if i < completed_count else MilestoneStatus.AVAILABLE
            completion = 100.0 if i < completed_count else 0.0
            
            milestones.append({
                "id": str(uuid4()),
                "code": f"M{i}",
                "name": f"Milestone {i}",
                "type": MilestoneType.PAID if i > 0 else MilestoneType.FREE,
                "user_progress": {
                    "status": status,
                    "completion_percentage": completion
                },
                "dependencies": [{"code": f"M{i-1}", "is_required": True}] if i > 0 else [],
                "dependents": [f"M{i+1}"] if i < milestone_count - 1 else []
            })
        
        return {
            "milestones": milestones,
            "total_progress": (completed_count / milestone_count) * 100,
            "completed_count": completed_count,
            "available_count": milestone_count - completed_count,
            "locked_count": 0
        }
    
    return create_tree


# Test utilities
class TestUtilities:
    """Utility functions for tests."""
    
    @staticmethod
    async def complete_milestone_workflow(
        milestone_service: MilestoneService,
        user_id: str,
        milestone_code: str,
        steps: Optional[List[Dict[str, Any]]] = None
    ):
        """Complete a full milestone workflow."""
        # Start milestone
        success, message, user_milestone = await milestone_service.start_milestone(
            user_id, milestone_code
        )
        assert success, f"Failed to start milestone: {message}"
        
        # Progress through steps
        if steps:
            for i, step_data in enumerate(steps, 1):
                await milestone_service.update_milestone_progress(
                    user_id, milestone_code, i, step_data
                )
        
        # Complete milestone
        completion_data = {
            "result": f"Completed {milestone_code}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        success, message, unlocked = await milestone_service.complete_milestone(
            user_id, milestone_code, completion_data, quality_score=0.85
        )
        assert success, f"Failed to complete milestone: {message}"
        
        return user_milestone, unlocked
    
    @staticmethod
    def assert_performance_within_bounds(
        actual_time: float,
        expected_max: float,
        operation_name: str
    ):
        """Assert that operation performance is within expected bounds."""
        assert actual_time <= expected_max, \
            f"{operation_name} took {actual_time:.3f}s, expected <= {expected_max:.3f}s"
    
    @staticmethod
    async def wait_for_cache_propagation(delay: float = 0.1):
        """Wait for cache operations to propagate."""
        await asyncio.sleep(delay)
    
    @staticmethod
    def generate_large_milestone_data(size_kb: int = 100) -> Dict[str, Any]:
        """Generate large milestone data for testing."""
        data_size = size_kb * 1024
        large_string = "x" * (data_size // 2)
        
        return {
            "large_analysis": large_string,
            "detailed_breakdown": {
                "section_1": "y" * (data_size // 4),
                "section_2": "z" * (data_size // 4)
            },
            "metadata": {
                "size_bytes": data_size,
                "generated_at": datetime.utcnow().isoformat()
            }
        }


@pytest.fixture
def test_utilities():
    """Provide test utilities."""
    return TestUtilities


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "cache: mark test as cache-related"
    )
    config.addinivalue_line(
        "markers", "database: mark test as database-related"
    )


# Skip conditions based on configuration
def pytest_runtest_setup(item):
    """Skip tests based on configuration."""
    if "performance" in item.keywords and not TestConfig.ENABLE_PERFORMANCE_TESTS:
        pytest.skip("Performance tests disabled")
    
    if "integration" in item.keywords and not TestConfig.ENABLE_INTEGRATION_TESTS:
        pytest.skip("Integration tests disabled")
    
    if "cache" in item.keywords and not TestConfig.ENABLE_CACHE_TESTS:
        pytest.skip("Cache tests disabled")


# Session-scoped fixtures for expensive setup
@pytest.fixture(scope="session")
async def test_data_seed():
    """Seed data for tests that require pre-existing data."""
    return {
        "users": [
            {"email": f"seed_user_{i}@test.com", "username": f"seed_user_{i}"}
            for i in range(5)
        ],
        "milestones": [
            {"code": f"SEED_M{i}", "name": f"Seed Milestone {i}"}
            for i in range(3)
        ]
    }


# Cleanup fixtures
@pytest.fixture(autouse=True)
async def cleanup_after_test(mock_redis_client):
    """Cleanup after each test."""
    yield
    # Clear all mock Redis data after each test
    mock_redis_client.clear_all_data()


@pytest.fixture(autouse=True)
def log_test_info(request):
    """Log test information."""
    logger.info(f"Starting test: {request.node.name}")
    yield
    logger.info(f"Completed test: {request.node.name}")