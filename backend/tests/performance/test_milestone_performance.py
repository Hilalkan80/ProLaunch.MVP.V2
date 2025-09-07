"""
Performance Benchmark Tests for Milestone System

Comprehensive performance tests to measure and validate milestone system
performance under various load conditions, including database operations,
cache performance, and API response times.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from uuid import uuid4
from typing import List, Dict, Any
import statistics
from concurrent.futures import ThreadPoolExecutor
import psutil
import gc

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select, func

from backend.src.models.milestone import (
    Base, Milestone, UserMilestone, MilestoneDependency,
    MilestoneStatus, MilestoneType, MilestoneProgressLog
)
from backend.src.models.user import User, SubscriptionTier
from backend.src.services.milestone_service import MilestoneService
from backend.src.services.milestone_cache import MilestoneCacheService
from backend.src.services.dependency_manager import DependencyManager


class PerformanceMetrics:
    """Class to track and analyze performance metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
        self.memory_usage = []
    
    def start_timer(self, operation: str):
        """Start timing an operation."""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str):
        """End timing an operation and record the duration."""
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)
            del self.start_times[operation]
            return duration
        return None
    
    def record_memory(self):
        """Record current memory usage."""
        process = psutil.Process()
        memory_info = process.memory_info()
        self.memory_usage.append({
            'timestamp': datetime.utcnow(),
            'rss': memory_info.rss,  # Resident Set Size
            'vms': memory_info.vms   # Virtual Memory Size
        })
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation."""
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        times = self.metrics[operation]
        return {
            'count': len(times),
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'min': min(times),
            'max': max(times),
            'stddev': statistics.stdev(times) if len(times) > 1 else 0,
            'p95': self._percentile(times, 95),
            'p99': self._percentile(times, 99)
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (percentile / 100)
        f = int(k)
        c = k - f
        if f == len(sorted_data) - 1:
            return sorted_data[f]
        return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
    
    def print_summary(self):
        """Print performance summary."""
        print("\n=== Performance Test Summary ===")
        for operation, times in self.metrics.items():
            stats = self.get_stats(operation)
            print(f"\n{operation}:")
            print(f"  Count: {stats['count']}")
            print(f"  Mean: {stats['mean']:.3f}s")
            print(f"  Median: {stats['median']:.3f}s")
            print(f"  Min: {stats['min']:.3f}s")
            print(f"  Max: {stats['max']:.3f}s")
            print(f"  P95: {stats['p95']:.3f}s")
            print(f"  P99: {stats['p99']:.3f}s")
            print(f"  StdDev: {stats['stddev']:.3f}s")


class MockHighPerformanceRedis:
    """High-performance mock Redis client for benchmarking."""
    
    def __init__(self):
        self._cache = {}
        self._operation_count = 0
        self._total_time = 0
    
    async def get_cache(self, key: str):
        start = time.time()
        result = self._cache.get(key)
        self._total_time += time.time() - start
        self._operation_count += 1
        return result
    
    async def set_cache(self, key: str, value: Any, ttl: int = 3600):
        start = time.time()
        self._cache[key] = value
        self._total_time += time.time() - start
        self._operation_count += 1
        return True
    
    async def delete_cache(self, key: str):
        start = time.time()
        self._cache.pop(key, None)
        self._total_time += time.time() - start
        self._operation_count += 1
        return True
    
    async def publish(self, channel: str, message: Any):
        self._operation_count += 1
        return 1
    
    def get_performance_stats(self):
        """Get Redis operation performance stats."""
        return {
            'operation_count': self._operation_count,
            'total_time': self._total_time,
            'avg_time_per_op': self._total_time / max(self._operation_count, 1)
        }


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def perf_db_engine():
    """Create database engine optimized for performance testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def perf_db_session(perf_db_engine):
    """Create database session for performance testing."""
    async_session = sessionmaker(
        perf_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def perf_redis_client():
    """Create high-performance mock Redis client."""
    return MockHighPerformanceRedis()


@pytest.fixture
async def perf_cache_service(perf_redis_client):
    """Create cache service for performance testing."""
    return MilestoneCacheService(perf_redis_client)


@pytest.fixture
async def perf_milestone_service(perf_db_session, perf_cache_service):
    """Create milestone service for performance testing."""
    return MilestoneService(perf_db_session, perf_cache_service)


@pytest.fixture
def performance_metrics():
    """Create performance metrics tracker."""
    return PerformanceMetrics()


class TestDatabasePerformance:
    """Test database operation performance."""
    
    @pytest.mark.asyncio
    async def test_milestone_creation_performance(
        self,
        perf_db_session,
        performance_metrics
    ):
        """Test performance of creating multiple milestones."""
        num_milestones = 100
        milestones = []
        
        performance_metrics.start_timer("milestone_creation_batch")
        
        # Create milestones in batch
        for i in range(num_milestones):
            milestone = Milestone(
                id=uuid4(),
                code=f"PERF_{i:03d}",
                name=f"Performance Test Milestone {i}",
                milestone_type=MilestoneType.PAID,
                order_index=i,
                estimated_minutes=60,
                is_active=True,
                prompt_template={"steps": [f"step_{j}" for j in range(5)]}
            )
            milestones.append(milestone)
            perf_db_session.add(milestone)
        
        await perf_db_session.commit()
        performance_metrics.end_timer("milestone_creation_batch")
        
        # Test individual milestone creation performance
        individual_times = []
        for i in range(10):
            performance_metrics.start_timer("milestone_creation_individual")
            
            milestone = Milestone(
                id=uuid4(),
                code=f"IND_{i:03d}",
                name=f"Individual Test Milestone {i}",
                milestone_type=MilestoneType.PAID,
                order_index=1000 + i,
                is_active=True
            )
            perf_db_session.add(milestone)
            await perf_db_session.commit()
            
            duration = performance_metrics.end_timer("milestone_creation_individual")
            individual_times.append(duration)
        
        # Performance assertions
        batch_stats = performance_metrics.get_stats("milestone_creation_batch")
        individual_stats = performance_metrics.get_stats("milestone_creation_individual")
        
        assert batch_stats["mean"] < 1.0, f"Batch creation too slow: {batch_stats['mean']:.3f}s"
        assert individual_stats["mean"] < 0.1, f"Individual creation too slow: {individual_stats['mean']:.3f}s"
        assert individual_stats["p95"] < 0.2, f"95th percentile too slow: {individual_stats['p95']:.3f}s"
    
    @pytest.mark.asyncio
    async def test_user_milestone_initialization_performance(
        self,
        perf_milestone_service,
        perf_db_session,
        performance_metrics
    ):
        """Test performance of user milestone initialization."""
        # Create test milestones
        milestones = []
        for i in range(20):
            milestone = Milestone(
                id=uuid4(),
                code=f"INIT_{i:02d}",
                name=f"Init Test Milestone {i}",
                milestone_type=MilestoneType.PAID,
                order_index=i,
                is_active=True
            )
            milestones.append(milestone)
            perf_db_session.add(milestone)
        
        await perf_db_session.commit()
        
        # Create test users
        users = []
        for i in range(10):
            user = User(
                id=uuid4(),
                email=f"perf_user_{i}@test.com",
                username=f"perf_user_{i}",
                subscription_tier=SubscriptionTier.PREMIUM,
                is_active=True
            )
            users.append(user)
            perf_db_session.add(user)
        
        await perf_db_session.commit()
        
        # Test initialization performance
        initialization_times = []
        
        for user in users:
            performance_metrics.start_timer("user_initialization")
            
            await perf_milestone_service.initialize_user_milestones(str(user.id))
            
            duration = performance_metrics.end_timer("user_initialization")
            initialization_times.append(duration)
        
        stats = performance_metrics.get_stats("user_initialization")
        
        # Performance assertions
        assert stats["mean"] < 0.5, f"Initialization too slow: {stats['mean']:.3f}s"
        assert stats["max"] < 1.0, f"Worst case too slow: {stats['max']:.3f}s"
        assert stats["p95"] < 0.8, f"95th percentile too slow: {stats['p95']:.3f}s"
    
    @pytest.mark.asyncio
    async def test_milestone_query_performance(
        self,
        perf_milestone_service,
        perf_db_session,
        performance_metrics
    ):
        """Test performance of milestone queries."""
        # Setup data
        users = []
        milestones = []
        
        # Create users
        for i in range(50):
            user = User(
                id=uuid4(),
                email=f"query_user_{i}@test.com",
                username=f"query_user_{i}",
                subscription_tier=SubscriptionTier.PREMIUM,
                is_active=True
            )
            users.append(user)
            perf_db_session.add(user)
        
        # Create milestones
        for i in range(30):
            milestone = Milestone(
                id=uuid4(),
                code=f"QUERY_{i:02d}",
                name=f"Query Test Milestone {i}",
                milestone_type=MilestoneType.PAID,
                order_index=i,
                is_active=True
            )
            milestones.append(milestone)
            perf_db_session.add(milestone)
        
        await perf_db_session.commit()
        
        # Initialize user milestones
        for user in users[:10]:  # Initialize subset for realistic data
            await perf_milestone_service.initialize_user_milestones(str(user.id))
        
        # Test query performance
        query_operations = [
            ("get_all_milestones", lambda: perf_milestone_service.get_all_milestones()),
            ("get_user_progress", lambda: perf_milestone_service.get_user_milestone_progress(str(users[0].id))),
            ("get_milestone_tree", lambda: perf_milestone_service.get_user_milestone_tree_with_cache(str(users[0].id))),
            ("get_user_analytics", lambda: perf_milestone_service.get_user_analytics(str(users[0].id)))
        ]
        
        for operation_name, operation_func in query_operations:
            times = []
            
            for _ in range(20):  # Multiple iterations for statistical significance
                performance_metrics.start_timer(operation_name)
                
                await operation_func()
                
                duration = performance_metrics.end_timer(operation_name)
                times.append(duration)
            
            stats = performance_metrics.get_stats(operation_name)
            
            # Performance assertions vary by operation complexity
            if operation_name == "get_all_milestones":
                assert stats["mean"] < 0.05, f"{operation_name} too slow: {stats['mean']:.3f}s"
            elif operation_name == "get_user_progress":
                assert stats["mean"] < 0.1, f"{operation_name} too slow: {stats['mean']:.3f}s"
            else:
                assert stats["mean"] < 0.2, f"{operation_name} too slow: {stats['mean']:.3f}s"


class TestCachePerformance:
    """Test cache operation performance."""
    
    @pytest.mark.asyncio
    async def test_cache_operation_performance(
        self,
        perf_cache_service,
        perf_redis_client,
        performance_metrics
    ):
        """Test basic cache operation performance."""
        num_operations = 1000
        
        # Test cache write performance
        write_times = []
        for i in range(num_operations):
            performance_metrics.start_timer("cache_write")
            
            await perf_cache_service.set_user_progress(
                f"user_{i}",
                {"progress": i, "data": f"test_data_{i}"},
                f"milestone_{i % 10}"
            )
            
            duration = performance_metrics.end_timer("cache_write")
            write_times.append(duration)
        
        # Test cache read performance
        read_times = []
        for i in range(num_operations):
            performance_metrics.start_timer("cache_read")
            
            await perf_cache_service.get_user_progress(
                f"user_{i}",
                f"milestone_{i % 10}"
            )
            
            duration = performance_metrics.end_timer("cache_read")
            read_times.append(duration)
        
        # Performance assertions
        write_stats = performance_metrics.get_stats("cache_write")
        read_stats = performance_metrics.get_stats("cache_read")
        
        assert write_stats["mean"] < 0.001, f"Cache writes too slow: {write_stats['mean']:.6f}s"
        assert read_stats["mean"] < 0.001, f"Cache reads too slow: {read_stats['mean']:.6f}s"
        assert write_stats["p95"] < 0.002, f"Cache write P95 too slow: {write_stats['p95']:.6f}s"
        assert read_stats["p95"] < 0.002, f"Cache read P95 too slow: {read_stats['p95']:.6f}s"
        
        # Check Redis client performance
        redis_stats = perf_redis_client.get_performance_stats()
        assert redis_stats["avg_time_per_op"] < 0.0001, "Redis operations too slow"
    
    @pytest.mark.asyncio
    async def test_cache_concurrency_performance(
        self,
        perf_cache_service,
        performance_metrics
    ):
        """Test cache performance under concurrent load."""
        concurrent_users = 20
        operations_per_user = 50
        
        async def user_operations(user_id: str):
            """Simulate operations for one user."""
            user_times = []
            
            for i in range(operations_per_user):
                performance_metrics.start_timer("concurrent_cache_op")
                
                if i % 3 == 0:
                    # Write operation
                    await perf_cache_service.set_user_progress(
                        user_id,
                        {"step": i, "timestamp": datetime.utcnow().isoformat()},
                        f"milestone_{i % 5}"
                    )
                elif i % 3 == 1:
                    # Read operation
                    await perf_cache_service.get_user_progress(
                        user_id,
                        f"milestone_{i % 5}"
                    )
                else:
                    # Update operation
                    await perf_cache_service.update_milestone_progress(
                        user_id,
                        f"milestone_{i % 5}",
                        {"updated_step": i}
                    )
                
                duration = performance_metrics.end_timer("concurrent_cache_op")
                user_times.append(duration)
            
            return user_times
        
        # Execute concurrent operations
        start_time = time.time()
        
        tasks = [
            user_operations(f"concurrent_user_{i}")
            for i in range(concurrent_users)
        ]
        
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Analyze results
        all_times = [t for user_times in results for t in user_times]
        total_operations = len(all_times)
        
        stats = performance_metrics.get_stats("concurrent_cache_op")
        
        # Performance assertions
        assert total_time < 5.0, f"Concurrent operations took too long: {total_time:.3f}s"
        assert stats["mean"] < 0.01, f"Average operation too slow: {stats['mean']:.6f}s"
        assert stats["p95"] < 0.02, f"P95 too slow under concurrency: {stats['p95']:.6f}s"
        
        # Throughput assertion
        throughput = total_operations / total_time
        assert throughput > 1000, f"Throughput too low: {throughput:.1f} ops/sec"
    
    @pytest.mark.asyncio
    async def test_cache_memory_performance(
        self,
        perf_cache_service,
        performance_metrics
    ):
        """Test cache performance with large data objects."""
        # Create large objects
        large_objects = []
        for i in range(10):
            large_object = {
                "id": i,
                "large_data": "x" * 50000,  # 50KB string
                "metadata": {
                    "created": datetime.utcnow().isoformat(),
                    "items": [f"item_{j}" for j in range(1000)]
                }
            }
            large_objects.append(large_object)
        
        # Track memory usage
        performance_metrics.record_memory()
        
        # Store large objects
        storage_times = []
        for i, obj in enumerate(large_objects):
            performance_metrics.start_timer("large_object_storage")
            
            await perf_cache_service.set_user_progress(
                f"large_user_{i}",
                obj,
                f"large_milestone_{i}"
            )
            
            duration = performance_metrics.end_timer("large_object_storage")
            storage_times.append(duration)
            
            if i % 3 == 0:
                performance_metrics.record_memory()
        
        # Retrieve large objects
        retrieval_times = []
        for i in range(len(large_objects)):
            performance_metrics.start_timer("large_object_retrieval")
            
            retrieved = await perf_cache_service.get_user_progress(
                f"large_user_{i}",
                f"large_milestone_{i}"
            )
            
            duration = performance_metrics.end_timer("large_object_retrieval")
            retrieval_times.append(duration)
            
            # Verify data integrity
            assert retrieved is not None
            assert retrieved["id"] == i
            assert len(retrieved["large_data"]) == 50000
        
        performance_metrics.record_memory()
        
        # Performance assertions
        storage_stats = performance_metrics.get_stats("large_object_storage")
        retrieval_stats = performance_metrics.get_stats("large_object_retrieval")
        
        assert storage_stats["mean"] < 0.01, f"Large object storage too slow: {storage_stats['mean']:.6f}s"
        assert retrieval_stats["mean"] < 0.01, f"Large object retrieval too slow: {retrieval_stats['mean']:.6f}s"
        
        # Memory usage should be reasonable
        memory_readings = performance_metrics.memory_usage
        if len(memory_readings) > 1:
            memory_increase = memory_readings[-1]['rss'] - memory_readings[0]['rss']
            # Memory increase should be reasonable for the data stored
            assert memory_increase < 100 * 1024 * 1024, f"Memory usage too high: {memory_increase / 1024 / 1024:.1f}MB"


class TestEndToEndPerformance:
    """Test end-to-end workflow performance."""
    
    @pytest.mark.asyncio
    async def test_complete_milestone_workflow_performance(
        self,
        perf_milestone_service,
        perf_db_session,
        performance_metrics
    ):
        """Test performance of complete milestone workflow."""
        # Setup
        user = User(
            id=uuid4(),
            email="workflow_perf@test.com",
            username="workflow_perf_user",
            subscription_tier=SubscriptionTier.PREMIUM,
            is_active=True
        )
        
        milestone = Milestone(
            id=uuid4(),
            code="WORKFLOW_PERF",
            name="Workflow Performance Test",
            milestone_type=MilestoneType.PAID,
            order_index=0,
            is_active=True,
            prompt_template={"steps": ["step1", "step2", "step3"]}
        )
        
        perf_db_session.add(user)
        perf_db_session.add(milestone)
        await perf_db_session.commit()
        
        user_id = str(user.id)
        milestone_code = "WORKFLOW_PERF"
        
        # Test complete workflow performance
        performance_metrics.start_timer("complete_workflow")
        
        # 1. Initialize
        performance_metrics.start_timer("workflow_initialize")
        await perf_milestone_service.initialize_user_milestones(user_id)
        performance_metrics.end_timer("workflow_initialize")
        
        # 2. Start
        performance_metrics.start_timer("workflow_start")
        success, _, _ = await perf_milestone_service.start_milestone(user_id, milestone_code)
        performance_metrics.end_timer("workflow_start")
        assert success is True
        
        # 3. Progress updates
        performance_metrics.start_timer("workflow_progress")
        for step in range(1, 4):
            await perf_milestone_service.update_milestone_progress(
                user_id,
                milestone_code,
                step,
                {f"step_{step}": f"completed step {step}"}
            )
        performance_metrics.end_timer("workflow_progress")
        
        # 4. Complete
        performance_metrics.start_timer("workflow_complete")
        success, _, _ = await perf_milestone_service.complete_milestone(
            user_id,
            milestone_code,
            {"result": "workflow completed successfully"},
            quality_score=0.9
        )
        performance_metrics.end_timer("workflow_complete")
        assert success is True
        
        total_time = performance_metrics.end_timer("complete_workflow")
        
        # Performance assertions
        assert total_time < 0.5, f"Complete workflow too slow: {total_time:.3f}s"
        
        init_stats = performance_metrics.get_stats("workflow_initialize")
        start_stats = performance_metrics.get_stats("workflow_start")
        progress_stats = performance_metrics.get_stats("workflow_progress")
        complete_stats = performance_metrics.get_stats("workflow_complete")
        
        assert init_stats["mean"] < 0.1, f"Initialize too slow: {init_stats['mean']:.3f}s"
        assert start_stats["mean"] < 0.1, f"Start too slow: {start_stats['mean']:.3f}s"
        assert progress_stats["mean"] < 0.2, f"Progress too slow: {progress_stats['mean']:.3f}s"
        assert complete_stats["mean"] < 0.1, f"Complete too slow: {complete_stats['mean']:.3f}s"
    
    @pytest.mark.asyncio
    async def test_high_load_milestone_performance(
        self,
        perf_milestone_service,
        perf_db_session,
        performance_metrics
    ):
        """Test milestone system performance under high load."""
        num_users = 50
        num_milestones = 10
        
        # Create users
        users = []
        for i in range(num_users):
            user = User(
                id=uuid4(),
                email=f"load_user_{i}@test.com",
                username=f"load_user_{i}",
                subscription_tier=SubscriptionTier.PREMIUM,
                is_active=True
            )
            users.append(user)
            perf_db_session.add(user)
        
        # Create milestones
        milestones = []
        for i in range(num_milestones):
            milestone = Milestone(
                id=uuid4(),
                code=f"LOAD_{i:02d}",
                name=f"Load Test Milestone {i}",
                milestone_type=MilestoneType.PAID,
                order_index=i,
                is_active=True,
                prompt_template={"steps": ["step1", "step2"]}
            )
            milestones.append(milestone)
            perf_db_session.add(milestone)
        
        await perf_db_session.commit()
        
        async def user_workflow(user: User):
            """Complete workflow for one user."""
            user_id = str(user.id)
            
            # Initialize milestones
            await perf_milestone_service.initialize_user_milestones(user_id)
            
            # Process first milestone
            milestone_code = "LOAD_00"
            await perf_milestone_service.start_milestone(user_id, milestone_code)
            
            # Progress updates
            await perf_milestone_service.update_milestone_progress(
                user_id, milestone_code, 1, {"step_1": "completed"}
            )
            await perf_milestone_service.update_milestone_progress(
                user_id, milestone_code, 2, {"step_2": "completed"}
            )
            
            # Complete
            await perf_milestone_service.complete_milestone(
                user_id,
                milestone_code,
                {"result": f"completed by {user.username}"},
                quality_score=0.85
            )
        
        # Execute high load test
        performance_metrics.start_timer("high_load_test")
        
        # Process users in batches to simulate realistic load
        batch_size = 10
        batches = [users[i:i + batch_size] for i in range(0, len(users), batch_size)]
        
        for batch_num, batch in enumerate(batches):
            batch_start = time.time()
            
            tasks = [user_workflow(user) for user in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            batch_time = time.time() - batch_start
            
            # Check for errors in batch
            errors = [r for r in results if isinstance(r, Exception)]
            success_rate = (len(results) - len(errors)) / len(results)
            
            assert success_rate > 0.9, f"Batch {batch_num} success rate too low: {success_rate:.2f}"
            assert batch_time < 10.0, f"Batch {batch_num} took too long: {batch_time:.3f}s"
        
        total_time = performance_metrics.end_timer("high_load_test")
        
        # Overall performance assertions
        assert total_time < 60.0, f"High load test took too long: {total_time:.3f}s"
        
        # Throughput calculation
        total_operations = num_users * 4  # init, start, progress, complete per user
        throughput = total_operations / total_time
        assert throughput > 10, f"Throughput too low: {throughput:.1f} ops/sec"
    
    @pytest.mark.asyncio
    async def test_memory_efficiency_under_load(
        self,
        perf_milestone_service,
        perf_db_session,
        performance_metrics
    ):
        """Test memory efficiency under sustained load."""
        # Force garbage collection to get baseline
        gc.collect()
        performance_metrics.record_memory()
        
        # Create sustained load scenario
        num_iterations = 20
        users_per_iteration = 10
        
        for iteration in range(num_iterations):
            # Create users for this iteration
            users = []
            for i in range(users_per_iteration):
                user = User(
                    id=uuid4(),
                    email=f"mem_user_{iteration}_{i}@test.com",
                    username=f"mem_user_{iteration}_{i}",
                    subscription_tier=SubscriptionTier.PREMIUM,
                    is_active=True
                )
                users.append(user)
                perf_db_session.add(user)
            
            # Create milestone for this iteration
            milestone = Milestone(
                id=uuid4(),
                code=f"MEM_{iteration:02d}",
                name=f"Memory Test Milestone {iteration}",
                milestone_type=MilestoneType.PAID,
                order_index=iteration,
                is_active=True
            )
            perf_db_session.add(milestone)
            await perf_db_session.commit()
            
            # Process users
            for user in users:
                user_id = str(user.id)
                milestone_code = f"MEM_{iteration:02d}"
                
                await perf_milestone_service.initialize_user_milestones(user_id)
                await perf_milestone_service.start_milestone(user_id, milestone_code)
                await perf_milestone_service.complete_milestone(
                    user_id,
                    milestone_code,
                    {"iteration": iteration, "result": "completed"},
                    quality_score=0.8
                )
            
            # Record memory usage periodically
            if iteration % 5 == 0:
                gc.collect()  # Force cleanup
                performance_metrics.record_memory()
        
        # Final memory check
        gc.collect()
        performance_metrics.record_memory()
        
        # Analyze memory usage
        memory_readings = performance_metrics.memory_usage
        if len(memory_readings) > 1:
            initial_memory = memory_readings[0]['rss']
            final_memory = memory_readings[-1]['rss']
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable
            max_acceptable_increase = 200 * 1024 * 1024  # 200MB
            assert memory_increase < max_acceptable_increase, \
                f"Memory usage increased too much: {memory_increase / 1024 / 1024:.1f}MB"
            
            # Check for memory leaks (sustained growth)
            if len(memory_readings) > 3:
                mid_memory = memory_readings[len(memory_readings) // 2]['rss']
                late_growth = final_memory - mid_memory
                early_growth = mid_memory - initial_memory
                
                # Late growth should not be significantly higher than early growth
                growth_ratio = late_growth / max(early_growth, 1)
                assert growth_ratio < 2.0, f"Potential memory leak detected: growth ratio {growth_ratio:.2f}"


class TestScalabilityBenchmarks:
    """Test system scalability under various conditions."""
    
    @pytest.mark.asyncio
    async def test_database_scalability(
        self,
        perf_db_session,
        performance_metrics
    ):
        """Test database performance as data volume increases."""
        # Test performance with increasing data volumes
        data_volumes = [100, 500, 1000, 2000]
        
        for volume in data_volumes:
            # Create milestones
            milestones = []
            for i in range(volume):
                milestone = Milestone(
                    id=uuid4(),
                    code=f"SCALE_{volume}_{i:04d}",
                    name=f"Scalability Test Milestone {i}",
                    milestone_type=MilestoneType.PAID,
                    order_index=i,
                    is_active=True
                )
                milestones.append(milestone)
                perf_db_session.add(milestone)
            
            # Measure commit time
            performance_metrics.start_timer(f"db_commit_{volume}")
            await perf_db_session.commit()
            commit_time = performance_metrics.end_timer(f"db_commit_{volume}")
            
            # Measure query time
            performance_metrics.start_timer(f"db_query_{volume}")
            
            stmt = select(func.count(Milestone.id)).where(Milestone.is_active == True)
            result = await perf_db_session.execute(stmt)
            count = result.scalar()
            
            query_time = performance_metrics.end_timer(f"db_query_{volume}")
            
            assert count >= volume
            
            # Performance should not degrade too much with scale
            assert commit_time < volume * 0.001, f"Commit time degraded at volume {volume}: {commit_time:.3f}s"
            assert query_time < 0.1, f"Query time degraded at volume {volume}: {query_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_user_scalability(
        self,
        perf_milestone_service,
        perf_db_session,
        performance_metrics
    ):
        """Test system performance with increasing concurrent users."""
        # Create base milestone
        milestone = Milestone(
            id=uuid4(),
            code="CONCURRENT_SCALE",
            name="Concurrent Scalability Test",
            milestone_type=MilestoneType.PAID,
            order_index=0,
            is_active=True,
            prompt_template={"steps": ["step1", "step2"]}
        )
        perf_db_session.add(milestone)
        await perf_db_session.commit()
        
        concurrent_user_counts = [5, 10, 20, 50]
        
        for user_count in concurrent_user_counts:
            # Create users
            users = []
            for i in range(user_count):
                user = User(
                    id=uuid4(),
                    email=f"concurrent_{user_count}_{i}@test.com",
                    username=f"concurrent_{user_count}_{i}",
                    subscription_tier=SubscriptionTier.PREMIUM,
                    is_active=True
                )
                users.append(user)
                perf_db_session.add(user)
            
            await perf_db_session.commit()
            
            async def user_operations(user: User):
                """Perform operations for one user."""
                user_id = str(user.id)
                await perf_milestone_service.initialize_user_milestones(user_id)
                await perf_milestone_service.start_milestone(user_id, "CONCURRENT_SCALE")
                await perf_milestone_service.update_milestone_progress(
                    user_id, "CONCURRENT_SCALE", 1, {"step": 1}
                )
                await perf_milestone_service.complete_milestone(
                    user_id,
                    "CONCURRENT_SCALE",
                    {"result": "concurrent test"},
                    quality_score=0.8
                )
            
            # Test concurrent execution
            performance_metrics.start_timer(f"concurrent_{user_count}")
            
            tasks = [user_operations(user) for user in users]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            execution_time = performance_metrics.end_timer(f"concurrent_{user_count}")
            
            # Check results
            errors = [r for r in results if isinstance(r, Exception)]
            success_rate = (len(results) - len(errors)) / len(results)
            
            assert success_rate > 0.9, f"Success rate too low at {user_count} users: {success_rate:.2f}"
            
            # Performance should scale reasonably
            time_per_user = execution_time / user_count
            assert time_per_user < 1.0, f"Time per user too high at {user_count} users: {time_per_user:.3f}s"
            
            # Throughput should not degrade severely
            throughput = (user_count * 4) / execution_time  # 4 operations per user
            expected_min_throughput = max(10, 100 / user_count)  # Allowing some degradation
            assert throughput > expected_min_throughput, \
                f"Throughput too low at {user_count} users: {throughput:.1f} ops/sec"


if __name__ == "__main__":
    # Run performance tests with detailed output
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        # Run specific benchmark tests
        pytest.main([
            __file__ + "::TestDatabasePerformance",
            __file__ + "::TestCachePerformance", 
            __file__ + "::TestEndToEndPerformance",
            "-v", "-s", "--tb=short"
        ])
    else:
        print("Use 'python test_milestone_performance.py benchmark' to run benchmarks")