from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import json
from .token_optimizer import TokenOptimizer
from .mcp_adapters import memory_bank_mcp, postgresql_mcp, redis_mcp, ref_mcp

class ContextLayer(ABC):
    def __init__(self, token_limit: int):
        self.token_limit = token_limit
        self.optimizer = TokenOptimizer()
        
    @abstractmethod
    async def add(self, content: Any, metadata: Optional[Dict] = None) -> bool:
        pass
        
    @abstractmethod
    async def get(self, **kwargs) -> Any:
        pass
        
    @abstractmethod
    async def clear(self) -> None:
        pass

class SessionContext(ContextLayer):
    """Session context with 800 token limit"""
    
    def __init__(self):
        super().__init__(800)
        self.session_id = str(uuid.uuid4())
        
    async def add(self, content: Dict[str, str], metadata: Optional[Dict] = None) -> bool:
        # First try to cache in Redis for quick access
        await redis_mcp.execute(
            "cache_set",
            key=f"session:{self.session_id}:latest",
            data=content,
            ttl_seconds=7200  # 2 hours
        )
        
        # Store in database
        await memory_bank_mcp.execute(
            "store",
            user_id=metadata.get('user_id'),
            context_type='session',
            data={
                'content': content,
                'session_id': self.session_id,
                'metadata': metadata
            }
        )
        
        return True
        
    async def get(self, **kwargs) -> List[Dict]:
        # Try Redis cache first
        cached = await redis_mcp.execute(
            "cache_get",
            key=f"session:{self.session_id}:latest"
        )
        
        if cached:
            return [cached]
            
        # Fall back to database
        contexts = await memory_bank_mcp.execute(
            "retrieve",
            user_id=kwargs.get('user_id'),
            context_type='session'
        )
        
        # Filter for this session
        session_contexts = [
            ctx for ctx in contexts
            if ctx.get('session_id') == self.session_id
        ]
        
        # Optimize to fit token limit
        if session_contexts:
            return self.optimizer.optimize_messages(session_contexts, self.token_limit)
        return []
        
    async def clear(self) -> None:
        await redis_mcp.execute(
            "cache_set",
            key=f"session:{self.session_id}:latest",
            data={},
            ttl_seconds=1  # Expire immediately
        )

class JourneyContext(ContextLayer):
    """Journey context with 2000 token limit"""
    
    def __init__(self):
        super().__init__(2000)
        
    async def add(self, content: Dict[str, Any], metadata: Optional[Dict] = None) -> bool:
        milestone = metadata.get('milestone')
        if not milestone:
            return False
            
        # Store with vector embedding for semantic search
        embedding = await ref_mcp.execute(
            "optimize_prompt",
            prompt=json.dumps(content)
        )
        
        await postgresql_mcp.execute(
            "store_embedding",
            content=json.dumps(content),
            embedding=embedding.get('optimized_prompt'),
            metadata={
                'milestone': milestone,
                'timestamp': datetime.now().isoformat(),
                **metadata
            }
        )
        
        return True
        
    async def get(self, **kwargs) -> List[Dict]:
        milestone = kwargs.get('milestone')
        
        results = await postgresql_mcp.execute(
            "vector_search",
            query_embedding=kwargs.get('query_embedding'),
            filter={'milestone': milestone},
            limit=10
        )
        
        # Optimize to fit token limit
        total_content = [
            json.loads(result['content'])
            for result in results
        ]
        
        return self.optimizer.optimize_messages(total_content, self.token_limit)
        
    async def clear(self) -> None:
        pass  # Journey context is persistent

class KnowledgeContext(ContextLayer):
    """Knowledge context with 1200 token limit"""
    
    def __init__(self):
        super().__init__(1200)
        
    async def add(self, content: str, metadata: Optional[Dict] = None) -> bool:
        # Optimize content
        optimized = await ref_mcp.execute(
            "optimize_prompt",
            prompt=content,
            max_tokens=self.token_limit
        )
        
        # Store with vector embedding
        await postgresql_mcp.execute(
            "store_embedding",
            content=optimized['optimized_prompt'],
            embedding=optimized['optimized_prompt'],  # Using same content as embedding for now
            metadata={
                'timestamp': datetime.now().isoformat(),
                **metadata
            }
        )
        
        return True
        
    async def get(self, **kwargs) -> List[Dict]:
        results = await postgresql_mcp.execute(
            "vector_search",
            query_embedding=kwargs.get('query_embedding'),
            limit=5  # Fewer results since knowledge chunks are larger
        )
        
        # Combine and optimize to fit token limit
        total_content = [
            result['content']
            for result in sorted(
                results,
                key=lambda x: x['distance']
            )
        ]
        
        return self.optimizer.optimize_messages(total_content, self.token_limit)
        
    async def clear(self) -> None:
        pass  # Knowledge context is persistent