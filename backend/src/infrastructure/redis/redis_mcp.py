from typing import Optional, Any, Dict
import redis
from redis.client import Redis
from redis.connection import ConnectionPool
from functools import wraps
import json
import time
import asyncio
from datetime import datetime, timedelta

class RedisMCPClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        ssl: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.pool = ConnectionPool(
            host=host,
            port=port,
            password=password,
            db=db,
            ssl=ssl,
            decode_responses=True,
            max_connections=50
        )
        self.client: Redis = redis.Redis(connection_pool=self.pool)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    async def get_cache(self, key: str) -> Optional[Any]:
        try:
            value = await asyncio.to_thread(self.client.get, key)
            return json.loads(value) if value else None
        except redis.RedisError as e:
            print(f"Redis error in get_cache: {e}")
            return None

    async def set_cache(
        self, 
        key: str, 
        value: Any, 
        expiry: Optional[int] = None
    ) -> bool:
        try:
            serialized = json.dumps(value)
            if expiry:
                return await asyncio.to_thread(
                    self.client.setex, 
                    key, 
                    expiry, 
                    serialized
                )
            return await asyncio.to_thread(
                self.client.set,
                key,
                serialized
            )
        except redis.RedisError as e:
            print(f"Redis error in set_cache: {e}")
            return False

    async def delete_cache(self, key: str) -> bool:
        try:
            return await asyncio.to_thread(self.client.delete, key)
        except redis.RedisError as e:
            print(f"Redis error in delete_cache: {e}")
            return False

    async def publish(self, channel: str, message: Any) -> int:
        try:
            serialized = json.dumps(message)
            return await asyncio.to_thread(
                self.client.publish,
                channel,
                serialized
            )
        except redis.RedisError as e:
            print(f"Redis error in publish: {e}")
            return 0

    async def rate_limit(
        self, 
        key: str, 
        limit: int, 
        window: int
    ) -> bool:
        try:
            current = int(time.time())
            window_start = current - window
            
            pipe = self.client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(current): current})
            pipe.zcard(key)
            pipe.expire(key, window)
            results = pipe.execute()
            
            return results[2] <= limit
        except redis.RedisError as e:
            print(f"Redis error in rate_limit: {e}")
            return False

    def circuit_breaker(self, failure_threshold: int = 5, reset_timeout: int = 60):
        def decorator(func):
            failure_count = 0
            last_failure_time = None

            @wraps(func)
            async def wrapper(*args, **kwargs):
                nonlocal failure_count, last_failure_time

                if (
                    last_failure_time and 
                    failure_count >= failure_threshold and 
                    (datetime.now() - last_failure_time).seconds < reset_timeout
                ):
                    raise Exception("Circuit breaker is open")

                try:
                    result = await func(*args, **kwargs)
                    failure_count = 0
                    last_failure_time = None
                    return result
                except Exception as e:
                    failure_count += 1
                    last_failure_time = datetime.now()
                    raise e

            return wrapper
        return decorator

    async def lock(
        self, 
        lock_name: str, 
        expiry: int = 10
    ) -> Optional[str]:
        try:
            lock_value = str(time.time())
            acquired = await asyncio.to_thread(
                self.client.set,
                f"lock:{lock_name}",
                lock_value,
                ex=expiry,
                nx=True
            )
            return lock_value if acquired else None
        except redis.RedisError as e:
            print(f"Redis error in lock: {e}")
            return None

    async def unlock(
        self, 
        lock_name: str, 
        lock_value: str
    ) -> bool:
        try:
            current_value = await asyncio.to_thread(
                self.client.get,
                f"lock:{lock_name}"
            )
            if current_value == lock_value:
                return await asyncio.to_thread(
                    self.client.delete,
                    f"lock:{lock_name}"
                )
            return False
        except redis.RedisError as e:
            print(f"Redis error in unlock: {e}")
            return False

    async def session_manager(
        self,
        session_id: str,
        data: Optional[Dict] = None,
        expiry: int = 3600
    ) -> Optional[Dict]:
        try:
            if data:
                return await self.set_cache(
                    f"session:{session_id}",
                    data,
                    expiry
                )
            return await self.get_cache(f"session:{session_id}")
        except redis.RedisError as e:
            print(f"Redis error in session_manager: {e}")
            return None

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis"""
        try:
            return await asyncio.to_thread(self.client.exists, key) > 0
        except redis.RedisError as e:
            print(f"Redis error in exists: {e}")
            return False
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a string value with optional TTL"""
        try:
            if ttl:
                return await asyncio.to_thread(
                    self.client.setex,
                    key,
                    ttl,
                    value
                )
            return await asyncio.to_thread(
                self.client.set,
                key,
                value
            )
        except redis.RedisError as e:
            print(f"Redis error in set: {e}")
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """Get a string value from Redis"""
        try:
            return await asyncio.to_thread(self.client.get, key)
        except redis.RedisError as e:
            print(f"Redis error in get: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        try:
            return await asyncio.to_thread(self.client.delete, key) > 0
        except redis.RedisError as e:
            print(f"Redis error in delete: {e}")
            return False
    
    async def close(self):
        try:
            self.pool.disconnect()
        except redis.RedisError as e:
            print(f"Redis error in close: {e}")


# Create singleton instance with environment configuration
import os

redis_mcp_client = RedisMCPClient(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    password=os.getenv("REDIS_PASSWORD"),
    db=int(os.getenv("REDIS_DB", "0")),
    ssl=os.getenv("REDIS_SSL", "false").lower() == "true"
)