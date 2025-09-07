from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import redis
import asyncpg
import json
from datetime import datetime

class MCPAdapter(ABC):
    """Base adapter for MCP servers"""
    
    @abstractmethod
    async def execute(self, action: str, **kwargs) -> Any:
        pass

class MemoryBankMCP(MCPAdapter):
    """Memory Bank MCP - For now using PostgreSQL directly"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
    async def execute(self, action: str, **kwargs) -> Any:
        conn = await asyncpg.connect(self.connection_string)
        try:
            if action == "store":
                query = """
                INSERT INTO memory_bank 
                (user_id, context_type, data, timestamp) 
                VALUES ($1, $2, $3, $4)
                """
                await conn.execute(
                    query,
                    kwargs.get('user_id'),
                    kwargs.get('context_type'),
                    json.dumps(kwargs.get('data')),
                    datetime.now()
                )
                return {"success": True}
                
            elif action == "retrieve":
                query = """
                SELECT data FROM memory_bank 
                WHERE user_id = $1 AND context_type = $2 
                ORDER BY timestamp DESC LIMIT 10
                """
                rows = await conn.fetch(
                    query,
                    kwargs.get('user_id'),
                    kwargs.get('context_type')
                )
                return [json.loads(row['data']) for row in rows]
        finally:
            await conn.close()

class PostgreSQLMCP(MCPAdapter):
    """PostgreSQL MCP with pgvector support"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
    async def execute(self, action: str, **kwargs) -> Any:
        conn = await asyncpg.connect(self.connection_string)
        try:
            if action == "vector_search":
                query = """
                SELECT content, metadata, 
                       embedding <-> $1 as distance
                FROM knowledge_embeddings
                WHERE ($2::text IS NULL OR metadata->>'milestone' = $2)
                ORDER BY embedding <-> $1
                LIMIT $3
                """
                rows = await conn.fetch(
                    query,
                    kwargs.get('query_embedding'),
                    kwargs.get('filter', {}).get('milestone'),
                    kwargs.get('limit', 10)
                )
                return [
                    {
                        'content': row['content'],
                        'metadata': json.loads(row['metadata']),
                        'distance': float(row['distance'])
                    }
                    for row in rows
                ]
            elif action == "store_embedding":
                query = """
                INSERT INTO knowledge_embeddings 
                (content, embedding, metadata) 
                VALUES ($1, $2, $3)
                """
                await conn.execute(
                    query,
                    kwargs.get('content'),
                    kwargs.get('embedding'),
                    json.dumps(kwargs.get('metadata'))
                )
                return {"success": True}
        finally:
            await conn.close()

class RedisMCP(MCPAdapter):
    """Redis MCP for caching and real-time operations"""
    
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
        
    async def execute(self, action: str, **kwargs) -> Any:
        if action == "cache_set":
            key = kwargs.get('key')
            data = json.dumps(kwargs.get('data'))
            ttl = kwargs.get('ttl_seconds', 300)
            self.redis_client.setex(key, ttl, data)
            return {"success": True}
            
        elif action == "cache_get":
            key = kwargs.get('key')
            data = self.redis_client.get(key)
            return json.loads(data) if data else None
            
        elif action == "publish":
            channel = kwargs.get('channel')
            data = json.dumps(kwargs.get('data'))
            self.redis_client.publish(channel, data)
            return {"success": True}

class RefMCP(MCPAdapter):
    """Ref MCP for prompt optimization - Mock implementation"""
    
    async def execute(self, action: str, **kwargs) -> Any:
        if action == "optimize_prompt":
            # For now, return the prompt as-is
            # Real MCP would optimize token usage
            prompt = kwargs.get('prompt')
            max_tokens = kwargs.get('max_tokens', 4000)
            
            # Simple truncation for now
            if len(prompt) > max_tokens * 4:  # Rough estimate
                prompt = prompt[:max_tokens * 4]
                
            return {
                "optimized_prompt": prompt,
                "estimated_tokens": len(prompt) // 4
            }

# Singleton instances
memory_bank_mcp = None
postgresql_mcp = None
redis_mcp = None
ref_mcp = None

def initialize_mcp_adapters(config: Dict[str, str]):
    """Initialize all MCP adapters"""
    global memory_bank_mcp, postgresql_mcp, redis_mcp, ref_mcp
    
    memory_bank_mcp = MemoryBankMCP(config['database_url'])
    postgresql_mcp = PostgreSQLMCP(config['database_url'])
    redis_mcp = RedisMCP(config['redis_url'])
    ref_mcp = RefMCP()
    
    return {
        'memory_bank': memory_bank_mcp,
        'postgresql': postgresql_mcp,
        'redis': redis_mcp,
        'ref': ref_mcp
    }