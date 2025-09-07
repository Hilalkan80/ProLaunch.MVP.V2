"""
Performance and concurrency tests for context management system.
Tests system behavior under load, concurrent access, and performance constraints.
"""

import pytest
import pytest_asyncio
import asyncio
import time
import uuid
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from src.ai.context.manager import ContextManager
from src.ai.context.token_optimizer import TokenOptimizer
from src.ai.context.layers import SessionContext, JourneyContext, KnowledgeContext


class TestPerformanceBenchmarks:
    """Performance benchmarks for context management operations."""

    @pytest_asyncio.fixture
    async def test_token_counting_performance(self, token_optimizer):
        """Test token counting performance with various content sizes."""
        content_sizes = [100, 500, 1000, 5000, 10000]
        
        performance_results = {}
        
        for size in content_sizes:
            content = "word " * size
            
            # Measure token counting performance
            start_time = time.time()
            for _ in range(100):  # Run 100 iterations
                token_count = token_optimizer.count_tokens(content)
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 100
            performance_results[size] = {
                'avg_time_ms': avg_time * 1000,
                'tokens': token_count,
                'tokens_per_ms': token_count / (avg_time * 1000) if avg_time > 0 else 0
            }
        
        # Performance assertions
        for size, result in performance_results.items():
            # Token counting should be reasonably fast
            assert result['avg_time_ms'] < 10.0  # Less than 10ms on average
            assert result['tokens'] > 0
            
            # Larger content should have proportionally more tokens
            if size > 100:
                smaller_result = performance_results[100]
                assert result['tokens'] > smaller_result['tokens']

    @pytest_asyncio.fixture
    async def test_message_optimization_performance(self, token_optimizer, sample_messages):
        """Test message optimization performance."""
        # Create messages of varying sizes
        test_messages = []
        for i in range(100):
            message = {
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': f'Message {i}: ' + ('content ' * (i % 50 + 1))
            }
            test_messages.append(message)
        
        budgets = [500, 1000, 2000, 5000]
        performance_results = []
        
        for budget in budgets:
            start_time = time.time()
            
            # Run optimization multiple times
            for _ in range(10):
                optimized = token_optimizer.optimize_messages(test_messages, budget)
                
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 10
            
            # Final optimization for result analysis
            final_optimized = token_optimizer.optimize_messages(test_messages, budget)
            
            performance_results.append({
                'budget': budget,
                'avg_time_ms': avg_time * 1000,
                'original_count': len(test_messages),
                'optimized_count': len(final_optimized),
                'reduction_percent': (1 - len(final_optimized) / len(test_messages)) * 100
            })
        
        # Performance assertions
        for result in performance_results:
            # Optimization should be reasonably fast
            assert result['avg_time_ms'] < 100.0  # Less than 100ms
            
            # Should reduce message count for smaller budgets
            if result['budget'] < 2000:
                assert result['optimized_count'] <= result['original_count']

    @pytest_asyncio.fixture
    async def test_context_retrieval_performance(self, context_manager_with_mocks):
        """Test context retrieval performance."""
        context_manager = context_manager_with_mocks
        user_ids = [str(uuid.uuid4()) for _ in range(10)]
        
        # Pre-populate contexts
        for user_id in user_ids:
            for i in range(20):
                message = {
                    'role': 'user' if i % 2 == 0 else 'assistant',
                    'content': f'Performance test message {i}'
                }
                await context_manager.add_message(
                    message,
                    metadata={'user_id': user_id}
                )
        
        # Measure retrieval performance
        retrieval_times = []
        
        for _ in range(50):  # 50 retrieval operations
            user_id = user_ids[len(retrieval_times) % len(user_ids)]
            
            start_time = time.time()
            contexts = await context_manager.get_context(user_id=user_id)
            end_time = time.time()
            
            retrieval_time = (end_time - start_time) * 1000  # Convert to ms
            retrieval_times.append(retrieval_time)
            
            # Verify retrieval success
            assert 'session' in contexts
        
        # Performance analysis
        avg_retrieval_time = statistics.mean(retrieval_times)
        max_retrieval_time = max(retrieval_times)
        p95_retrieval_time = statistics.quantiles(retrieval_times, n=20)[18]  # 95th percentile
        
        # Performance assertions
        assert avg_retrieval_time < 50.0  # Average under 50ms
        assert max_retrieval_time < 200.0  # Max under 200ms
        assert p95_retrieval_time < 100.0  # 95th percentile under 100ms

    @pytest_asyncio.fixture
    async def test_memory_usage_optimization(self, context_manager_with_mocks):
        """Test memory usage optimization during heavy operations."""
        context_manager = context_manager_with_mocks
        user_id = str(uuid.uuid4())
        
        # Add progressively larger amounts of context
        memory_stages = []
        
        for stage in range(5):
            # Add content in stages
            for i in range(50):  # 50 messages per stage
                message = {
                    'role': 'user' if i % 2 == 0 else 'assistant',
                    'content': f'Stage {stage} message {i}: ' + ('A' * (stage * 100 + 100))
                }
                
                await context_manager.add_message(
                    message,
                    metadata={'user_id': user_id, 'stage': stage}
                )
            
            # Measure context retrieval after each stage
            start_time = time.time()
            contexts = await context_manager.get_context(user_id=user_id)
            end_time = time.time()
            
            memory_stages.append({
                'stage': stage,
                'messages_added': (stage + 1) * 50,
                'retrieval_time_ms': (end_time - start_time) * 1000,
                'retrieved_count': len(contexts.get('session', []))
            })
        
        # Memory optimization assertions
        for i, stage_data in enumerate(memory_stages):
            # Retrieval time should not grow linearly with data size
            if i > 0:
                previous_stage = memory_stages[i-1]
                time_ratio = stage_data['retrieval_time_ms'] / previous_stage['retrieval_time_ms']
                
                # Time growth should be sub-linear (less than 2x)
                assert time_ratio < 2.0
            
            # Context optimization should limit retrieved messages
            assert stage_data['retrieved_count'] <= stage_data['messages_added']


class TestConcurrencyStress:
    """Concurrency stress tests for context management system."""

    @pytest_asyncio.fixture
    async def test_concurrent_user_sessions(self, context_manager_with_mocks):
        """Test concurrent user sessions with realistic load."""
        context_manager = context_manager_with_mocks
        
        # Simulate 20 concurrent users
        user_count = 20
        messages_per_user = 10
        user_ids = [str(uuid.uuid4()) for _ in range(user_count)]
        
        async def simulate_user_session(user_id: str, user_index: int) -> Dict[str, Any]:
            """Simulate a user session with multiple messages."""
            session_results = {
                'user_id': user_id,
                'user_index': user_index,
                'messages_sent': 0,
                'successful_operations': 0,
                'errors': [],
                'session_duration_ms': 0
            }
            
            start_time = time.time()
            
            try:
                for i in range(messages_per_user):
                    message = {
                        'role': 'user' if i % 2 == 0 else 'assistant',
                        'content': f'User {user_index} message {i}: Concurrent testing content'
                    }
                    
                    success = await context_manager.add_message(
                        message,
                        metadata={'user_id': user_id, 'message_index': i}
                    )
                    
                    if success:
                        session_results['successful_operations'] += 1
                    
                    session_results['messages_sent'] += 1
                    
                    # Small delay to simulate realistic usage
                    await asyncio.sleep(0.01)
                
                # Retrieve final context
                contexts = await context_manager.get_context(user_id=user_id)
                if contexts and 'session' in contexts:
                    session_results['successful_operations'] += 1
                    
            except Exception as e:
                session_results['errors'].append(str(e))
            
            end_time = time.time()
            session_results['session_duration_ms'] = (end_time - start_time) * 1000
            
            return session_results
        
        # Run concurrent user sessions
        start_time = time.time()
        
        tasks = [
            simulate_user_session(user_id, i) 
            for i, user_id in enumerate(user_ids)
        ]
        
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = (end_time - start_time) * 1000
        
        # Analyze results
        successful_sessions = [
            result for result in session_results 
            if isinstance(result, dict) and not result.get('errors')
        ]
        
        total_operations = sum(
            result['successful_operations'] 
            for result in successful_sessions
        )
        
        # Concurrency performance assertions
        assert len(successful_sessions) >= user_count * 0.8  # At least 80% success rate
        assert total_operations >= user_count * messages_per_user * 0.8  # 80% operations succeed
        assert total_duration < 30000  # Complete within 30 seconds
        
        # Individual session performance
        for result in successful_sessions:
            assert result['session_duration_ms'] < 5000  # Each session under 5 seconds

    @pytest_asyncio.fixture
    async def test_high_frequency_operations(self, context_manager_with_mocks):
        """Test high-frequency operations on the context system."""
        context_manager = context_manager_with_mocks
        user_id = str(uuid.uuid4())
        
        # High-frequency message addition
        operation_count = 100
        batch_size = 10
        
        performance_metrics = []
        
        for batch in range(operation_count // batch_size):
            batch_start = time.time()
            
            # Create batch of concurrent operations
            batch_tasks = []
            for i in range(batch_size):
                message = {
                    'role': 'user' if i % 2 == 0 else 'assistant',
                    'content': f'High frequency batch {batch} message {i}'
                }
                
                task = context_manager.add_message(
                    message,
                    metadata={'user_id': user_id, 'batch': batch, 'index': i}
                )
                batch_tasks.append(task)
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            batch_end = time.time()
            batch_duration = (batch_end - batch_start) * 1000
            
            successful_operations = sum(
                1 for result in batch_results 
                if result is True
            )
            
            performance_metrics.append({
                'batch': batch,
                'duration_ms': batch_duration,
                'successful_operations': successful_operations,
                'operations_per_second': successful_operations / (batch_duration / 1000) if batch_duration > 0 else 0
            })
        
        # Performance analysis
        avg_ops_per_second = statistics.mean([m['operations_per_second'] for m in performance_metrics])
        total_successful = sum([m['successful_operations'] for m in performance_metrics])
        
        # High-frequency performance assertions
        assert avg_ops_per_second >= 50  # At least 50 operations per second
        assert total_successful >= operation_count * 0.9  # 90% success rate
        
        # Check for performance degradation over time
        first_half = performance_metrics[:len(performance_metrics)//2]
        second_half = performance_metrics[len(performance_metrics)//2:]
        
        first_half_avg = statistics.mean([m['operations_per_second'] for m in first_half])
        second_half_avg = statistics.mean([m['operations_per_second'] for m in second_half])
        
        # Performance should not degrade significantly
        degradation_ratio = first_half_avg / second_half_avg if second_half_avg > 0 else 1
        assert degradation_ratio <= 2.0  # No more than 2x degradation

    @pytest_asyncio.fixture
    async def test_memory_pressure_handling(self, context_manager_with_mocks):
        """Test system behavior under memory pressure conditions."""
        context_manager = context_manager_with_mocks
        
        # Simulate memory pressure by adding large amounts of context
        users = [str(uuid.uuid4()) for _ in range(5)]
        large_content_sizes = [1000, 2000, 5000, 10000]
        
        pressure_test_results = []
        
        for content_size in large_content_sizes:
            start_time = time.time()
            successful_additions = 0
            
            # Add large content for each user
            for user_id in users:
                for i in range(10):  # 10 large messages per user
                    large_message = {
                        'role': 'user',
                        'content': 'X' * content_size
                    }
                    
                    try:
                        success = await context_manager.add_message(
                            large_message,
                            metadata={'user_id': user_id, 'size': content_size}
                        )
                        
                        if success:
                            successful_additions += 1
                            
                    except Exception as e:
                        # Log but continue - system should handle gracefully
                        pass
            
            # Test retrieval under pressure
            retrieval_successes = 0
            for user_id in users:
                try:
                    contexts = await context_manager.get_context(user_id=user_id)
                    if contexts and 'session' in contexts:
                        retrieval_successes += 1
                except Exception:
                    pass
            
            end_time = time.time()
            
            pressure_test_results.append({
                'content_size': content_size,
                'duration_ms': (end_time - start_time) * 1000,
                'successful_additions': successful_additions,
                'successful_retrievals': retrieval_successes,
                'total_operations': len(users) * 10 + len(users)
            })
        
        # Memory pressure handling assertions
        for result in pressure_test_results:
            # System should handle operations even under pressure
            success_rate = (result['successful_additions'] + result['successful_retrievals']) / result['total_operations']
            assert success_rate >= 0.5  # At least 50% success rate under pressure
            
            # Operations should complete in reasonable time even under pressure
            assert result['duration_ms'] < 60000  # Under 1 minute


class TestScalabilityLimits:
    """Tests to identify scalability limits and thresholds."""

    @pytest_asyncio.fixture
    async def test_user_capacity_limits(self, context_manager_with_mocks):
        """Test system capacity with increasing user counts."""
        context_manager = context_manager_with_mocks
        
        user_counts = [10, 25, 50, 100]  # Progressive scaling
        capacity_results = []
        
        for user_count in user_counts:
            users = [str(uuid.uuid4()) for _ in range(user_count)]
            
            start_time = time.time()
            
            # Add one message per user concurrently
            tasks = []
            for i, user_id in enumerate(users):
                message = {
                    'role': 'user',
                    'content': f'Capacity test message from user {i}'
                }
                
                task = context_manager.add_message(
                    message,
                    metadata={'user_id': user_id}
                )
                tasks.append(task)
            
            # Execute all operations concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Measure retrieval performance
            retrieval_start = time.time()
            retrieval_tasks = [
                context_manager.get_context(user_id=user_id)
                for user_id in users[:min(10, len(users))]  # Sample 10 users for retrieval
            ]
            
            retrieval_results = await asyncio.gather(*retrieval_tasks, return_exceptions=True)
            retrieval_end = time.time()
            
            end_time = time.time()
            
            successful_additions = sum(1 for r in results if r is True)
            successful_retrievals = sum(
                1 for r in retrieval_results 
                if isinstance(r, dict) and 'session' in r
            )
            
            capacity_results.append({
                'user_count': user_count,
                'total_duration_ms': (end_time - start_time) * 1000,
                'retrieval_duration_ms': (retrieval_end - retrieval_start) * 1000,
                'successful_additions': successful_additions,
                'successful_retrievals': successful_retrievals,
                'addition_success_rate': successful_additions / user_count,
                'throughput_ops_per_second': user_count / ((end_time - start_time)) if (end_time - start_time) > 0 else 0
            })
        
        # Scalability analysis
        for result in capacity_results:
            # Success rate should remain reasonable as user count increases
            assert result['addition_success_rate'] >= 0.7  # 70% success rate minimum
            
            # Throughput should not degrade drastically
            assert result['throughput_ops_per_second'] >= 10  # At least 10 ops/sec
            
            # Individual operations should complete in reasonable time
            avg_operation_time = result['total_duration_ms'] / result['user_count']
            assert avg_operation_time < 1000  # Less than 1 second per operation

    @pytest_asyncio.fixture
    async def test_context_size_scalability(self, context_manager_with_mocks, token_optimizer):
        """Test scalability with varying context sizes."""
        context_manager = context_manager_with_mocks
        user_id = str(uuid.uuid4())
        
        # Test with increasing amounts of context per user
        message_counts = [10, 50, 100, 200]
        scalability_results = []
        
        for message_count in message_counts:
            # Reset context for clean test
            await context_manager.clear_session()
            
            start_time = time.time()
            
            # Add messages
            addition_times = []
            for i in range(message_count):
                message = {
                    'role': 'user' if i % 2 == 0 else 'assistant',
                    'content': f'Scalability test message {i} with some additional content to make it realistic'
                }
                
                msg_start = time.time()
                success = await context_manager.add_message(
                    message,
                    metadata={'user_id': user_id, 'index': i}
                )
                msg_end = time.time()
                
                if success:
                    addition_times.append((msg_end - msg_start) * 1000)
            
            # Test retrieval performance
            retrieval_start = time.time()
            contexts = await context_manager.get_context(user_id=user_id)
            retrieval_end = time.time()
            
            # Analyze token optimization effectiveness
            if contexts and 'session' in contexts:
                total_content = ' '.join(
                    str(msg.get('content', '')) for msg in contexts['session']
                )
                actual_tokens = token_optimizer.count_tokens(total_content)
            else:
                actual_tokens = 0
            
            end_time = time.time()
            
            scalability_results.append({
                'message_count': message_count,
                'total_duration_ms': (end_time - start_time) * 1000,
                'avg_addition_time_ms': statistics.mean(addition_times) if addition_times else 0,
                'retrieval_time_ms': (retrieval_end - retrieval_start) * 1000,
                'retrieved_messages': len(contexts.get('session', [])) if contexts else 0,
                'actual_tokens': actual_tokens,
                'token_efficiency': actual_tokens <= 800  # Within session limit
            })
        
        # Context size scalability assertions
        for result in scalability_results:
            # Addition time should not grow excessively
            assert result['avg_addition_time_ms'] < 100  # Under 100ms per message
            
            # Retrieval should be efficient regardless of total context size
            assert result['retrieval_time_ms'] < 500  # Under 500ms
            
            # Token optimization should be effective
            assert result['token_efficiency'] is True
            
            # Should retrieve reasonable number of messages
            assert result['retrieved_messages'] > 0

    @pytest_asyncio.fixture
    async def test_sustained_load_performance(self, context_manager_with_mocks):
        """Test performance under sustained load over time."""
        context_manager = context_manager_with_mocks
        
        # Sustained load test: 5 minutes of continuous operations
        test_duration_seconds = 30  # Reduced for testing, normally would be 300
        operations_per_second = 5
        total_operations = test_duration_seconds * operations_per_second
        
        user_pool = [str(uuid.uuid4()) for _ in range(10)]  # Rotate through users
        
        performance_samples = []
        start_time = time.time()
        
        for operation_index in range(total_operations):
            user_id = user_pool[operation_index % len(user_pool)]
            
            operation_start = time.time()
            
            # Perform operation
            message = {
                'role': 'user' if operation_index % 2 == 0 else 'assistant',
                'content': f'Sustained load test operation {operation_index}'
            }
            
            success = await context_manager.add_message(
                message,
                metadata={'user_id': user_id, 'operation': operation_index}
            )
            
            operation_end = time.time()
            operation_duration = (operation_end - operation_start) * 1000
            
            # Record performance sample every 50 operations
            if operation_index % 50 == 0:
                contexts = await context_manager.get_context(user_id=user_id)
                retrieval_success = contexts is not None and 'session' in contexts
                
                performance_samples.append({
                    'operation_index': operation_index,
                    'timestamp': operation_end,
                    'operation_duration_ms': operation_duration,
                    'operation_success': success,
                    'retrieval_success': retrieval_success,
                    'elapsed_time': operation_end - start_time
                })
            
            # Maintain target rate
            target_interval = 1.0 / operations_per_second
            elapsed = operation_end - operation_start
            if elapsed < target_interval:
                await asyncio.sleep(target_interval - elapsed)
        
        total_duration = time.time() - start_time
        
        # Sustained load analysis
        successful_operations = sum(1 for sample in performance_samples if sample['operation_success'])
        successful_retrievals = sum(1 for sample in performance_samples if sample['retrieval_success'])
        
        avg_operation_time = statistics.mean([s['operation_duration_ms'] for s in performance_samples])
        
        # Check for performance degradation over time
        first_half = performance_samples[:len(performance_samples)//2]
        second_half = performance_samples[len(performance_samples)//2:]
        
        if first_half and second_half:
            first_half_avg = statistics.mean([s['operation_duration_ms'] for s in first_half])
            second_half_avg = statistics.mean([s['operation_duration_ms'] for s in second_half])
            degradation_ratio = second_half_avg / first_half_avg if first_half_avg > 0 else 1
        else:
            degradation_ratio = 1
        
        # Sustained load assertions
        assert successful_operations >= len(performance_samples) * 0.9  # 90% success rate
        assert successful_retrievals >= len(performance_samples) * 0.8  # 80% retrieval success
        assert avg_operation_time < 200  # Average under 200ms
        assert degradation_ratio < 2.0  # No more than 2x performance degradation
        assert total_duration <= test_duration_seconds * 1.2  # Within 20% of target time