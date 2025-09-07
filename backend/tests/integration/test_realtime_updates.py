"""
Integration Tests for Real-Time Update Functionality

Tests for real-time milestone progress updates, WebSocket communications,
event broadcasting, and live synchronization between clients.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock

from backend.src.services.milestone_service import MilestoneService
from backend.src.services.milestone_cache import MilestoneCacheService
from backend.src.models.milestone import MilestoneStatus, MilestoneType
from backend.tests.conftest_milestone import MockRedisClient


class MockWebSocketConnection:
    """Mock WebSocket connection for testing real-time updates."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.messages_received = []
        self.is_connected = True
        self.subscribed_channels = set()
    
    async def send(self, message: Any):
        """Send message to WebSocket client."""
        if self.is_connected:
            self.messages_received.append({
                'message': message,
                'timestamp': datetime.utcnow(),
                'connection_id': self.connection_id
            })
    
    async def subscribe(self, channel: str):
        """Subscribe to a channel for updates."""
        self.subscribed_channels.add(channel)
    
    async def unsubscribe(self, channel: str):
        """Unsubscribe from a channel."""
        self.subscribed_channels.discard(channel)
    
    def disconnect(self):
        """Simulate disconnection."""
        self.is_connected = False
    
    def get_messages_for_type(self, message_type: str) -> List[Dict[str, Any]]:
        """Get messages of specific type."""
        return [
            msg for msg in self.messages_received
            if isinstance(msg['message'], dict) and msg['message'].get('type') == message_type
        ]


class MockWebSocketManager:
    """Mock WebSocket manager for testing real-time functionality."""
    
    def __init__(self):
        self.connections = {}
        self.channels = {}
        self.broadcast_history = []
    
    def add_connection(self, user_id: str, connection_id: str) -> MockWebSocketConnection:
        """Add a WebSocket connection."""
        connection = MockWebSocketConnection(user_id, connection_id)
        if user_id not in self.connections:
            self.connections[user_id] = {}
        self.connections[user_id][connection_id] = connection
        return connection
    
    def remove_connection(self, user_id: str, connection_id: str):
        """Remove a WebSocket connection."""
        if user_id in self.connections and connection_id in self.connections[user_id]:
            del self.connections[user_id][connection_id]
            if not self.connections[user_id]:
                del self.connections[user_id]
    
    async def broadcast_to_user(self, user_id: str, message: Any):
        """Broadcast message to all connections for a user."""
        self.broadcast_history.append({
            'user_id': user_id,
            'message': message,
            'timestamp': datetime.utcnow()
        })
        
        if user_id in self.connections:
            for connection in self.connections[user_id].values():
                await connection.send(message)
    
    async def broadcast_to_channel(self, channel: str, message: Any):
        """Broadcast message to all subscribers of a channel."""
        self.broadcast_history.append({
            'channel': channel,
            'message': message,
            'timestamp': datetime.utcnow()
        })
        
        for user_connections in self.connections.values():
            for connection in user_connections.values():
                if channel in connection.subscribed_channels:
                    await connection.send(message)
    
    def get_user_connections(self, user_id: str) -> List[MockWebSocketConnection]:
        """Get all connections for a user."""
        return list(self.connections.get(user_id, {}).values())


class EnhancedMockRedisClient(MockRedisClient):
    """Enhanced mock Redis client with pub/sub simulation."""
    
    def __init__(self):
        super().__init__()
        self._subscribers = {}
        self._published_messages = {}
    
    async def publish(self, channel: str, message: Any):
        """Publish message with subscriber simulation."""
        await super().publish(channel, message)
        
        # Simulate message delivery to subscribers
        if channel in self._subscribers:
            for subscriber_callback in self._subscribers[channel]:
                try:
                    await subscriber_callback(channel, message)
                except Exception as e:
                    # Log error but don't break other subscribers
                    print(f"Error delivering message to subscriber: {e}")
        
        return len(self._subscribers.get(channel, []))
    
    def add_subscriber(self, channel: str, callback):
        """Add subscriber callback for testing."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)
    
    def remove_subscriber(self, channel: str, callback):
        """Remove subscriber callback."""
        if channel in self._subscribers:
            try:
                self._subscribers[channel].remove(callback)
            except ValueError:
                pass


@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager."""
    return MockWebSocketManager()


@pytest.fixture
def enhanced_redis_client():
    """Create enhanced Redis client with pub/sub."""
    return EnhancedMockRedisClient()


@pytest.fixture
async def realtime_cache_service(enhanced_redis_client):
    """Create cache service with real-time capabilities."""
    return MilestoneCacheService(enhanced_redis_client)


@pytest.fixture
async def realtime_milestone_service(test_db_session, realtime_cache_service):
    """Create milestone service with real-time updates."""
    return MilestoneService(test_db_session, realtime_cache_service)


class TestRealtimeProgressUpdates:
    """Test real-time progress update functionality."""
    
    @pytest.mark.asyncio
    async def test_progress_update_broadcast(
        self,
        realtime_milestone_service,
        realtime_cache_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_user,
        test_milestone
    ):
        """Test that progress updates are broadcast in real-time."""
        user_id = str(test_user.id)
        milestone_code = test_milestone.code
        
        # Set up WebSocket connections for user
        connection1 = mock_websocket_manager.add_connection(user_id, "conn1")
        connection2 = mock_websocket_manager.add_connection(user_id, "conn2")
        
        # Subscribe connections to milestone updates
        channel = f"milestone:updates:{user_id}"
        await connection1.subscribe(channel)
        await connection2.subscribe(channel)
        
        # Set up Redis subscriber to forward to WebSocket
        async def forward_to_websocket(channel, message):
            await mock_websocket_manager.broadcast_to_channel(channel, message)
        
        enhanced_redis_client.add_subscriber(channel, forward_to_websocket)
        
        # Initialize and start milestone
        await realtime_milestone_service.initialize_user_milestones(user_id)
        
        # Start milestone - should trigger real-time update
        success, _, _ = await realtime_milestone_service.start_milestone(user_id, milestone_code)
        assert success is True
        
        # Give time for async operations
        await asyncio.sleep(0.1)
        
        # Verify WebSocket connections received start notification
        start_messages = connection1.get_messages_for_type("milestone_started")
        assert len(start_messages) >= 1
        
        start_message = start_messages[0]['message']
        assert start_message['milestone_code'] == milestone_code
        assert start_message['status'] == MilestoneStatus.IN_PROGRESS
        
        # Update progress - should trigger another real-time update
        await realtime_milestone_service.update_milestone_progress(
            user_id, milestone_code, 1, {"step_1": "completed"}
        )
        
        await asyncio.sleep(0.1)
        
        # Verify progress update was broadcast
        progress_messages = connection1.get_messages_for_type("progress_update")
        assert len(progress_messages) >= 1
        
        progress_message = progress_messages[0]['message']
        assert progress_message['current_step'] == 1
        assert progress_message['milestone_code'] == milestone_code
        
        # Both connections should have received the same updates
        assert len(connection1.messages_received) == len(connection2.messages_received)
    
    @pytest.mark.asyncio
    async def test_milestone_completion_notification(
        self,
        realtime_milestone_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_user,
        test_milestone
    ):
        """Test real-time notifications when milestone is completed."""
        user_id = str(test_user.id)
        milestone_code = test_milestone.code
        
        # Set up connection and subscription
        connection = mock_websocket_manager.add_connection(user_id, "completion_test")
        channel = f"milestone:updates:{user_id}"
        await connection.subscribe(channel)
        
        async def forward_to_websocket(channel, message):
            await mock_websocket_manager.broadcast_to_channel(channel, message)
        
        enhanced_redis_client.add_subscriber(channel, forward_to_websocket)
        
        # Complete milestone workflow
        await realtime_milestone_service.initialize_user_milestones(user_id)
        await realtime_milestone_service.start_milestone(user_id, milestone_code)
        
        # Complete milestone
        completion_data = {
            "analysis_result": {"score": 0.9, "insights": ["insight1", "insight2"]},
            "recommendations": ["rec1", "rec2", "rec3"]
        }
        
        success, _, unlocked = await realtime_milestone_service.complete_milestone(
            user_id, milestone_code, completion_data, quality_score=0.92
        )
        assert success is True
        
        await asyncio.sleep(0.1)
        
        # Verify completion notification
        completion_messages = connection.get_messages_for_type("milestone_completed")
        assert len(completion_messages) >= 1
        
        completion_message = completion_messages[0]['message']
        assert completion_message['milestone_code'] == milestone_code
        assert completion_message['status'] == MilestoneStatus.COMPLETED
        assert completion_message['quality_score'] == 0.92
        assert 'newly_unlocked' in completion_message
        
        # Should also include achievement/celebration data
        assert 'achievement' in completion_message
        assert completion_message['achievement']['type'] == 'milestone_completed'
    
    @pytest.mark.asyncio
    async def test_dependency_unlock_notifications(
        self,
        realtime_milestone_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_user,
        test_milestone_chain
    ):
        """Test notifications when milestones are unlocked due to dependency completion."""
        user_id = str(test_user.id)
        
        # Set up connection
        connection = mock_websocket_manager.add_connection(user_id, "dependency_test")
        channel = f"milestone:updates:{user_id}"
        await connection.subscribe(channel)
        
        async def forward_to_websocket(channel, message):
            await mock_websocket_manager.broadcast_to_channel(channel, message)
        
        enhanced_redis_client.add_subscriber(channel, forward_to_websocket)
        
        # Initialize milestones
        await realtime_milestone_service.initialize_user_milestones(user_id)
        
        # Complete M0, which should unlock M1
        await realtime_milestone_service.start_milestone(user_id, "M0")
        await realtime_milestone_service.complete_milestone(
            user_id, "M0", {"foundation_result": "completed"}, quality_score=0.85
        )
        
        await asyncio.sleep(0.1)
        
        # Verify unlock notification
        unlock_messages = connection.get_messages_for_type("milestones_unlocked")
        assert len(unlock_messages) >= 1
        
        unlock_message = unlock_messages[0]['message']
        assert 'newly_available' in unlock_message
        assert any(m['code'] == 'M1' for m in unlock_message['newly_available'])
        
        # Should include celebration for unlocking new content
        assert 'celebration' in unlock_message
        assert unlock_message['celebration']['type'] == 'new_content_unlocked'
    
    @pytest.mark.asyncio
    async def test_session_activity_tracking(
        self,
        realtime_milestone_service,
        realtime_cache_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_user,
        test_milestone
    ):
        """Test real-time session activity tracking."""
        user_id = str(test_user.id)
        milestone_code = test_milestone.code
        
        # Set up connection
        connection = mock_websocket_manager.add_connection(user_id, "session_test")
        activity_channel = f"milestone:activity:{user_id}"
        await connection.subscribe(activity_channel)
        
        async def forward_activity(channel, message):
            await mock_websocket_manager.broadcast_to_channel(channel, message)
        
        enhanced_redis_client.add_subscriber(activity_channel, forward_activity)
        
        # Start milestone and track session
        await realtime_milestone_service.initialize_user_milestones(user_id)
        await realtime_milestone_service.start_milestone(user_id, milestone_code)
        
        # Simulate periodic activity updates
        for i in range(3):
            await realtime_milestone_service.update_milestone_progress(
                user_id, milestone_code, i + 1, {f"activity_{i}": f"step_{i}_data"}
            )
            await asyncio.sleep(0.05)  # Small delay to simulate real user activity
        
        await asyncio.sleep(0.1)
        
        # Verify activity tracking
        activity_messages = connection.get_messages_for_type("session_activity")
        assert len(activity_messages) >= 1
        
        # Should track engagement metrics
        latest_activity = activity_messages[-1]['message']
        assert 'session_duration' in latest_activity
        assert 'activity_count' in latest_activity
        assert latest_activity['activity_count'] >= 3


class TestRealtimeCollaborationFeatures:
    """Test real-time collaboration features."""
    
    @pytest.mark.asyncio
    async def test_multiple_user_milestone_visibility(
        self,
        realtime_milestone_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_users,
        test_milestone
    ):
        """Test visibility of milestone activities across multiple users."""
        milestone_code = test_milestone.code
        
        # Set up connections for multiple users
        user_connections = {}
        for i, user in enumerate(test_users[:3]):
            user_id = str(user.id)
            connection = mock_websocket_manager.add_connection(user_id, f"user_{i}_conn")
            user_connections[user_id] = connection
            
            # Subscribe to global milestone activity channel
            global_channel = f"milestone:global:{milestone_code}"
            await connection.subscribe(global_channel)
        
        # Set up Redis forwarding for global channel
        global_channel = f"milestone:global:{milestone_code}"
        
        async def forward_global_activity(channel, message):
            await mock_websocket_manager.broadcast_to_channel(channel, message)
        
        enhanced_redis_client.add_subscriber(global_channel, forward_global_activity)
        
        # Initialize milestones for all users
        for user in test_users[:3]:
            user_id = str(user.id)
            await realtime_milestone_service.initialize_user_milestones(user_id)
        
        # First user starts milestone
        user1_id = str(test_users[0].id)
        await realtime_milestone_service.start_milestone(user1_id, milestone_code)
        
        # Publish global activity
        await enhanced_redis_client.publish(global_channel, {
            'type': 'user_started_milestone',
            'user_id': user1_id,
            'milestone_code': milestone_code,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        await asyncio.sleep(0.1)
        
        # All users should see the activity
        for user_id, connection in user_connections.items():
            activity_messages = connection.get_messages_for_type("user_started_milestone")
            if user_id != user1_id:  # Other users should see the activity
                assert len(activity_messages) >= 1
                activity = activity_messages[0]['message']
                assert activity['user_id'] == user1_id
                assert activity['milestone_code'] == milestone_code
    
    @pytest.mark.asyncio
    async def test_leaderboard_updates(
        self,
        realtime_milestone_service,
        realtime_cache_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_users,
        test_milestone
    ):
        """Test real-time leaderboard updates."""
        milestone_code = test_milestone.code
        
        # Set up leaderboard subscribers
        leaderboard_connections = []
        leaderboard_channel = "milestone:leaderboard:updates"
        
        for i, user in enumerate(test_users[:5]):
            connection = mock_websocket_manager.add_connection(
                str(user.id), f"leaderboard_{i}"
            )
            await connection.subscribe(leaderboard_channel)
            leaderboard_connections.append(connection)
        
        async def forward_leaderboard_updates(channel, message):
            await mock_websocket_manager.broadcast_to_channel(channel, message)
        
        enhanced_redis_client.add_subscriber(leaderboard_channel, forward_leaderboard_updates)
        
        # Simulate users completing milestones with different scores
        user_scores = []
        
        for i, user in enumerate(test_users[:3]):
            user_id = str(user.id)
            
            await realtime_milestone_service.initialize_user_milestones(user_id)
            await realtime_milestone_service.start_milestone(user_id, milestone_code)
            
            quality_score = 0.7 + (i * 0.1)  # Different scores: 0.7, 0.8, 0.9
            await realtime_milestone_service.complete_milestone(
                user_id, milestone_code, 
                {"completion_order": i}, 
                quality_score=quality_score
            )
            
            user_scores.append((user_id, quality_score))
            
            # Publish leaderboard update
            await enhanced_redis_client.publish(leaderboard_channel, {
                'type': 'leaderboard_update',
                'user_id': user_id,
                'new_score': quality_score * 100,  # Convert to points
                'rank_change': 'up' if i < 2 else 'none',
                'milestone_completed': milestone_code
            })
        
        await asyncio.sleep(0.1)
        
        # All leaderboard subscribers should receive updates
        for connection in leaderboard_connections:
            leaderboard_messages = connection.get_messages_for_type("leaderboard_update")
            assert len(leaderboard_messages) >= 3  # One for each completion
            
            # Should show progression in scores
            scores_received = [msg['message']['new_score'] for msg in leaderboard_messages]
            assert len(set(scores_received)) == 3  # All different scores


class TestRealtimeErrorHandling:
    """Test error handling in real-time scenarios."""
    
    @pytest.mark.asyncio
    async def test_websocket_disconnection_handling(
        self,
        realtime_milestone_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_user,
        test_milestone
    ):
        """Test handling of WebSocket disconnections during milestone progress."""
        user_id = str(test_user.id)
        milestone_code = test_milestone.code
        
        # Set up connection
        connection = mock_websocket_manager.add_connection(user_id, "disconnect_test")
        channel = f"milestone:updates:{user_id}"
        await connection.subscribe(channel)
        
        async def forward_with_error_handling(channel, message):
            try:
                await mock_websocket_manager.broadcast_to_channel(channel, message)
            except Exception:
                # Connection might be broken, but other operations should continue
                pass
        
        enhanced_redis_client.add_subscriber(channel, forward_with_error_handling)
        
        # Start milestone
        await realtime_milestone_service.initialize_user_milestones(user_id)
        await realtime_milestone_service.start_milestone(user_id, milestone_code)
        
        # Simulate disconnection
        connection.disconnect()
        
        # Continue milestone operations - should not fail
        success, _ = await realtime_milestone_service.update_milestone_progress(
            user_id, milestone_code, 1, {"step_after_disconnect": "data"}
        )
        assert success is True
        
        # Complete milestone - should not fail despite disconnection
        success, _, _ = await realtime_milestone_service.complete_milestone(
            user_id, milestone_code, {"result": "completed despite disconnect"}
        )
        assert success is True
    
    @pytest.mark.asyncio
    async def test_redis_failure_graceful_degradation(
        self,
        realtime_milestone_service,
        enhanced_redis_client,
        test_user,
        test_milestone
    ):
        """Test graceful degradation when Redis pub/sub fails."""
        user_id = str(test_user.id)
        milestone_code = test_milestone.code
        
        # Start milestone normally
        await realtime_milestone_service.initialize_user_milestones(user_id)
        await realtime_milestone_service.start_milestone(user_id, milestone_code)
        
        # Simulate Redis failure
        enhanced_redis_client.set_error_mode(True)
        
        # Operations should continue despite Redis errors
        success, _ = await realtime_milestone_service.update_milestone_progress(
            user_id, milestone_code, 1, {"progress_during_redis_failure": "data"}
        )
        assert success is True  # Core functionality should work
        
        success, _, _ = await realtime_milestone_service.complete_milestone(
            user_id, milestone_code, {"result": "completed during failure"}
        )
        assert success is True
        
        # Restore Redis
        enhanced_redis_client.set_error_mode(False)
        
        # Subsequent operations should work normally
        await realtime_milestone_service.start_milestone(user_id, milestone_code)
    
    @pytest.mark.asyncio
    async def test_high_frequency_update_throttling(
        self,
        realtime_milestone_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_user,
        test_milestone
    ):
        """Test throttling of high-frequency real-time updates."""
        user_id = str(test_user.id)
        milestone_code = test_milestone.code
        
        # Set up connection
        connection = mock_websocket_manager.add_connection(user_id, "throttle_test")
        channel = f"milestone:updates:{user_id}"
        await connection.subscribe(channel)
        
        # Track message delivery with throttling simulation
        delivered_messages = []
        last_delivery_time = None
        throttle_interval = 0.1  # 100ms throttle
        
        async def throttled_forward(channel, message):
            nonlocal last_delivery_time, delivered_messages
            current_time = datetime.utcnow()
            
            if (last_delivery_time is None or 
                (current_time - last_delivery_time).total_seconds() >= throttle_interval):
                await mock_websocket_manager.broadcast_to_channel(channel, message)
                delivered_messages.append(message)
                last_delivery_time = current_time
        
        enhanced_redis_client.add_subscriber(channel, throttled_forward)
        
        # Initialize milestone
        await realtime_milestone_service.initialize_user_milestones(user_id)
        await realtime_milestone_service.start_milestone(user_id, milestone_code)
        
        # Send rapid updates
        update_tasks = []
        for i in range(10):
            task = realtime_milestone_service.update_milestone_progress(
                user_id, milestone_code, min(i + 1, 3), {f"rapid_update_{i}": i}
            )
            update_tasks.append(task)
        
        await asyncio.gather(*update_tasks)
        await asyncio.sleep(0.5)  # Wait for throttling to settle
        
        # Should have fewer delivered messages due to throttling
        assert len(delivered_messages) < 10
        assert len(delivered_messages) >= 3  # But some should get through


class TestRealtimePerformance:
    """Test performance aspects of real-time updates."""
    
    @pytest.mark.asyncio
    async def test_broadcast_performance_with_many_connections(
        self,
        realtime_milestone_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_users,
        test_milestone
    ):
        """Test broadcast performance with many WebSocket connections."""
        milestone_code = test_milestone.code
        num_connections = 50
        
        # Create many connections
        connections = []
        channel = f"milestone:global:{milestone_code}"
        
        for i in range(num_connections):
            user_id = str(test_users[i % len(test_users)].id)
            connection = mock_websocket_manager.add_connection(user_id, f"perf_conn_{i}")
            await connection.subscribe(channel)
            connections.append(connection)
        
        async def forward_to_all(channel, message):
            await mock_websocket_manager.broadcast_to_channel(channel, message)
        
        enhanced_redis_client.add_subscriber(channel, forward_to_all)
        
        # Measure broadcast performance
        start_time = datetime.utcnow()
        
        # Publish multiple updates
        for i in range(10):
            await enhanced_redis_client.publish(channel, {
                'type': 'performance_test_message',
                'message_number': i,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        await asyncio.sleep(0.2)  # Wait for all broadcasts
        
        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()
        
        # Performance assertions
        assert total_time < 1.0, f"Broadcast took too long: {total_time:.3f}s"
        
        # Verify all connections received messages
        messages_per_connection = [len(conn.messages_received) for conn in connections]
        assert min(messages_per_connection) >= 10  # All should receive all messages
        assert max(messages_per_connection) == min(messages_per_connection)  # Consistent delivery
    
    @pytest.mark.asyncio
    async def test_realtime_update_latency(
        self,
        realtime_milestone_service,
        enhanced_redis_client,
        mock_websocket_manager,
        test_user,
        test_milestone
    ):
        """Test latency of real-time updates from trigger to delivery."""
        user_id = str(test_user.id)
        milestone_code = test_milestone.code
        
        # Set up connection with latency tracking
        connection = mock_websocket_manager.add_connection(user_id, "latency_test")
        channel = f"milestone:updates:{user_id}"
        await connection.subscribe(channel)
        
        latency_measurements = []
        
        async def measure_latency_forward(channel, message):
            if isinstance(message, dict) and 'trigger_timestamp' in message:
                trigger_time = datetime.fromisoformat(message['trigger_timestamp'])
                delivery_time = datetime.utcnow()
                latency = (delivery_time - trigger_time).total_seconds() * 1000  # ms
                latency_measurements.append(latency)
            
            await mock_websocket_manager.broadcast_to_channel(channel, message)
        
        enhanced_redis_client.add_subscriber(channel, measure_latency_forward)
        
        # Initialize milestone
        await realtime_milestone_service.initialize_user_milestones(user_id)
        await realtime_milestone_service.start_milestone(user_id, milestone_code)
        
        # Measure update latencies
        for i in range(5):
            trigger_time = datetime.utcnow()
            
            # Include trigger timestamp in the update
            await enhanced_redis_client.publish(channel, {
                'type': 'latency_test_update',
                'step': i + 1,
                'trigger_timestamp': trigger_time.isoformat()
            })
            
            await asyncio.sleep(0.1)  # Space out updates
        
        await asyncio.sleep(0.2)  # Wait for all deliveries
        
        # Analyze latency
        if latency_measurements:
            avg_latency = sum(latency_measurements) / len(latency_measurements)
            max_latency = max(latency_measurements)
            
            # Performance assertions
            assert avg_latency < 50, f"Average latency too high: {avg_latency:.1f}ms"
            assert max_latency < 100, f"Max latency too high: {max_latency:.1f}ms"
            assert len(latency_measurements) == 5  # All updates measured