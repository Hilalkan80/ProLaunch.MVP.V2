"""
Redis MCP Integration

Extends the existing Redis MCP client with context-specific functionality.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging

from ...infrastructure.redis.redis_mcp import RedisMCPClient

logger = logging.getLogger(__name__)


class RedisMCP(RedisMCPClient):
    """
    Extended Redis MCP integration for context management.
    
    Provides:
    - Fast context caching
    - Real-time updates via pub/sub
    - Session state management
    - Rate limiting and throttling
    """
    
    def __init__(self):
        super().__init__()
        self.context_prefix = "context"
        self.pubsub_channels = {
            "updates": "context:updates",
            "events": "context:events",
            "notifications": "context:notifications"
        }
        
    async def cache_context_layer(
        self,
        user_id: str,
        layer_type: str,
        content: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """
        Cache a context layer.
        
        Args:
            user_id: User identifier
            layer_type: Type of context layer
            content: Layer content
            ttl: Time to live in seconds
            
        Returns:
            Success status
        """
        try:
            key = f"{self.context_prefix}:{user_id}:{layer_type}"
            return await self.set_cache(key, content, expiry=ttl)
            
        except Exception as e:
            logger.error(f"Error caching context layer: {e}")
            return False
    
    async def get_cached_context_layer(
        self,
        user_id: str,
        layer_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached context layer.
        
        Args:
            user_id: User identifier
            layer_type: Type of context layer
            
        Returns:
            Cached content or None
        """
        try:
            key = f"{self.context_prefix}:{user_id}:{layer_type}"
            return await self.get_cache(key)
            
        except Exception as e:
            logger.error(f"Error getting cached context layer: {e}")
            return None
    
    async def publish_context_update(
        self,
        user_id: str,
        update_type: str,
        data: Dict[str, Any]
    ) -> int:
        """
        Publish context update event.
        
        Args:
            user_id: User identifier
            update_type: Type of update
            data: Update data
            
        Returns:
            Number of subscribers that received the message
        """
        try:
            message = {
                "user_id": user_id,
                "type": update_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            channel = self.pubsub_channels["updates"]
            return await self.publish(channel, message)
            
        except Exception as e:
            logger.error(f"Error publishing context update: {e}")
            return 0
    
    async def track_context_access(
        self,
        user_id: str,
        layer_type: str,
        operation: str
    ) -> bool:
        """
        Track context access for analytics.
        
        Args:
            user_id: User identifier
            layer_type: Context layer type
            operation: Operation performed
            
        Returns:
            Success status
        """
        try:
            # Create tracking key
            timestamp = int(datetime.utcnow().timestamp())
            key = f"tracking:{user_id}:{layer_type}"
            
            # Add to sorted set with timestamp as score
            pipe = self.client.pipeline()
            pipe.zadd(key, {f"{operation}:{timestamp}": timestamp})
            
            # Keep only last 1000 entries
            pipe.zremrangebyrank(key, 0, -1001)
            
            # Set expiry
            pipe.expire(key, 86400 * 7)  # 7 days
            
            results = pipe.execute()
            return all(results)
            
        except Exception as e:
            logger.error(f"Error tracking context access: {e}")
            return False
    
    async def get_context_metrics(
        self,
        user_id: str,
        time_window: int = 3600
    ) -> Dict[str, Any]:
        """
        Get context usage metrics.
        
        Args:
            user_id: User identifier
            time_window: Time window in seconds
            
        Returns:
            Metrics dictionary
        """
        try:
            metrics = {
                "user_id": user_id,
                "time_window": time_window,
                "layers": {}
            }
            
            # Get metrics for each layer
            for layer in ["session", "journey", "knowledge"]:
                key = f"tracking:{user_id}:{layer}"
                
                # Get recent operations
                min_score = datetime.utcnow().timestamp() - time_window
                operations = self.client.zrangebyscore(
                    key,
                    min_score,
                    "+inf",
                    withscores=True
                )
                
                # Count operations by type
                op_counts = {}
                for op_data, score in operations:
                    op_type = op_data.split(":")[0]
                    op_counts[op_type] = op_counts.get(op_type, 0) + 1
                
                metrics["layers"][layer] = {
                    "total_operations": len(operations),
                    "operation_counts": op_counts
                }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting context metrics: {e}")
            return {}
    
    async def manage_context_locks(
        self,
        user_id: str,
        layer_type: str,
        operation: str = "acquire",
        ttl: int = 10
    ) -> Optional[str]:
        """
        Manage distributed locks for context operations.
        
        Args:
            user_id: User identifier
            layer_type: Context layer type
            operation: "acquire" or "release"
            ttl: Lock TTL in seconds
            
        Returns:
            Lock token if acquired, None otherwise
        """
        try:
            lock_name = f"context_lock:{user_id}:{layer_type}"
            
            if operation == "acquire":
                return await self.lock(lock_name, expiry=ttl)
            elif operation == "release" and hasattr(self, "_lock_value"):
                success = await self.unlock(lock_name, self._lock_value)
                if success:
                    del self._lock_value
                return "released" if success else None
            
            return None
            
        except Exception as e:
            logger.error(f"Error managing context lock: {e}")
            return None
    
    async def cache_embedding(
        self,
        text_hash: str,
        embedding: List[float],
        ttl: int = 86400
    ) -> bool:
        """
        Cache text embedding.
        
        Args:
            text_hash: Hash of the text
            embedding: Vector embedding
            ttl: Cache TTL in seconds
            
        Returns:
            Success status
        """
        try:
            key = f"embedding:{text_hash}"
            return await self.set_cache(key, embedding, expiry=ttl)
            
        except Exception as e:
            logger.error(f"Error caching embedding: {e}")
            return False
    
    async def get_cached_embedding(
        self,
        text_hash: str
    ) -> Optional[List[float]]:
        """
        Get cached embedding.
        
        Args:
            text_hash: Hash of the text
            
        Returns:
            Cached embedding or None
        """
        try:
            key = f"embedding:{text_hash}"
            return await self.get_cache(key)
            
        except Exception as e:
            logger.error(f"Error getting cached embedding: {e}")
            return None
    
    async def maintain_context_queue(
        self,
        user_id: str,
        operation: str,
        data: Optional[Dict[str, Any]] = None,
        max_size: int = 100
    ) -> Any:
        """
        Maintain a context processing queue.
        
        Args:
            user_id: User identifier
            operation: "push", "pop", "peek", or "size"
            data: Data to push (for push operation)
            max_size: Maximum queue size
            
        Returns:
            Operation result
        """
        try:
            queue_key = f"context_queue:{user_id}"
            
            if operation == "push" and data:
                # Push to queue
                serialized = json.dumps(data)
                self.client.lpush(queue_key, serialized)
                
                # Trim to max size
                self.client.ltrim(queue_key, 0, max_size - 1)
                
                # Set expiry
                self.client.expire(queue_key, 3600)
                
                return True
                
            elif operation == "pop":
                # Pop from queue
                value = self.client.rpop(queue_key)
                return json.loads(value) if value else None
                
            elif operation == "peek":
                # Peek at queue
                values = self.client.lrange(queue_key, 0, -1)
                return [json.loads(v) for v in values]
                
            elif operation == "size":
                # Get queue size
                return self.client.llen(queue_key)
            
            return None
            
        except Exception as e:
            logger.error(f"Error maintaining context queue: {e}")
            return None
    
    async def aggregate_context_stats(
        self,
        time_bucket: str = "hour"
    ) -> Dict[str, Any]:
        """
        Aggregate context statistics.
        
        Args:
            time_bucket: Time bucket for aggregation
            
        Returns:
            Aggregated statistics
        """
        try:
            stats = {
                "time_bucket": time_bucket,
                "timestamp": datetime.utcnow().isoformat(),
                "users": {},
                "totals": {
                    "operations": 0,
                    "cache_hits": 0,
                    "cache_misses": 0
                }
            }
            
            # Get all tracking keys
            pattern = "tracking:*"
            cursor = 0
            
            while True:
                cursor, keys = self.client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                for key in keys:
                    parts = key.split(":")
                    if len(parts) >= 3:
                        user_id = parts[1]
                        layer_type = parts[2]
                        
                        if user_id not in stats["users"]:
                            stats["users"][user_id] = {}
                        
                        # Get operation count
                        count = self.client.zcard(key)
                        stats["users"][user_id][layer_type] = count
                        stats["totals"]["operations"] += count
                
                if cursor == 0:
                    break
            
            return stats
            
        except Exception as e:
            logger.error(f"Error aggregating context stats: {e}")
            return {}