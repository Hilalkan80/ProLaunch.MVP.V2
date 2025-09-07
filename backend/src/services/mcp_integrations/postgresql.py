"""
PostgreSQL MCP Integration

Provides vector storage and search capabilities using PostgreSQL with pgvector.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json
import logging
import hashlib
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.base import get_db_context

logger = logging.getLogger(__name__)


class PostgreSQLMCP:
    """
    Integration with PostgreSQL MCP for vector storage and search.
    
    PostgreSQL with pgvector provides:
    - High-performance vector storage
    - Semantic similarity search
    - Hybrid search (vector + metadata)
    - Scalable vector indexing
    """
    
    def __init__(self):
        self.vector_dimension = 1536  # OpenAI embedding dimension
        self.index_type = "ivfflat"  # Index type for vector search
        self.lists = 100  # Number of lists for IVF index
        
    async def initialize_vector_extension(self) -> bool:
        """
        Initialize pgvector extension and create necessary tables.
        
        Returns:
            Success status
        """
        try:
            async with get_db_context() as db:
                # Enable pgvector extension
                await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                
                # Create vector storage table
                await db.execute(text("""
                    CREATE TABLE IF NOT EXISTS context_vectors (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        vector_id VARCHAR(255) UNIQUE NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector(:dim),
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_id (user_id),
                        INDEX idx_metadata_gin (metadata) USING gin
                    )
                """).bindparams(dim=self.vector_dimension))
                
                # Create IVF index for vector similarity search
                await db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_embedding_ivfflat 
                    ON context_vectors 
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = :lists)
                """).bindparams(lists=self.lists))
                
                await db.commit()
                logger.info("Initialized pgvector extension and tables")
                return True
                
        except Exception as e:
            logger.error(f"Error initializing vector extension: {e}")
            return False
    
    async def store_vector(
        self,
        content: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Store content with its vector embedding.
        
        Args:
            content: Text content to store
            embedding: Vector embedding (will be generated if not provided)
            metadata: Additional metadata
            
        Returns:
            Vector ID or None if failed
        """
        try:
            # Generate vector ID
            vector_id = self._generate_vector_id(content)
            
            # Generate embedding if not provided
            if embedding is None:
                embedding = await self._generate_embedding(content)
            
            # Ensure embedding is correct dimension
            if len(embedding) != self.vector_dimension:
                logger.error(f"Invalid embedding dimension: {len(embedding)}")
                return None
            
            async with get_db_context() as db:
                # Check if vector already exists
                result = await db.execute(
                    text("SELECT vector_id FROM context_vectors WHERE vector_id = :vid"),
                    {"vid": vector_id}
                )
                
                if result.scalar():
                    # Update existing vector
                    await db.execute(text("""
                        UPDATE context_vectors
                        SET content = :content,
                            embedding = :embedding,
                            metadata = :metadata,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE vector_id = :vector_id
                    """), {
                        "content": content,
                        "embedding": embedding,
                        "metadata": json.dumps(metadata or {}),
                        "vector_id": vector_id
                    })
                else:
                    # Insert new vector
                    user_id = metadata.get("user_id", "system") if metadata else "system"
                    
                    await db.execute(text("""
                        INSERT INTO context_vectors 
                        (user_id, vector_id, content, embedding, metadata)
                        VALUES (:user_id, :vector_id, :content, :embedding, :metadata)
                    """), {
                        "user_id": user_id,
                        "vector_id": vector_id,
                        "content": content,
                        "embedding": embedding,
                        "metadata": json.dumps(metadata or {})
                    })
                
                await db.commit()
                logger.info(f"Stored vector: {vector_id}")
                return vector_id
                
        except Exception as e:
            logger.error(f"Error storing vector: {e}")
            return None
    
    async def search_vectors(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query: Search query text
            query_embedding: Query vector (will be generated if not provided)
            filters: Metadata filters
            limit: Maximum results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of matching vectors with scores
        """
        try:
            # Generate query embedding if not provided
            if query_embedding is None:
                query_embedding = await self._generate_embedding(query)
            
            async with get_db_context() as db:
                # Build query with filters
                query_parts = [
                    """
                    SELECT 
                        vector_id,
                        content,
                        metadata,
                        1 - (embedding <=> :query_embedding::vector) as similarity
                    FROM context_vectors
                    WHERE 1=1
                    """
                ]
                
                params = {"query_embedding": query_embedding}
                
                # Add filters
                if filters:
                    if "user_id" in filters:
                        query_parts.append("AND user_id = :user_id")
                        params["user_id"] = filters["user_id"]
                    
                    # Add JSONB filters
                    for key, value in filters.items():
                        if key != "user_id":
                            query_parts.append(f"AND metadata @> :filter_{key}")
                            params[f"filter_{key}"] = json.dumps({key: value})
                
                # Add similarity threshold
                query_parts.append("AND 1 - (embedding <=> :query_embedding::vector) >= :threshold")
                params["threshold"] = similarity_threshold
                
                # Order and limit
                query_parts.append("ORDER BY embedding <=> :query_embedding::vector")
                query_parts.append("LIMIT :limit")
                params["limit"] = limit
                
                # Execute query
                result = await db.execute(
                    text(" ".join(query_parts)),
                    params
                )
                
                # Format results
                results = []
                for row in result:
                    results.append({
                        "id": row.vector_id,
                        "content": row.content,
                        "metadata": json.loads(row.metadata) if row.metadata else {},
                        "score": float(row.similarity)
                    })
                
                logger.info(f"Found {len(results)} similar vectors")
                return results
                
        except Exception as e:
            logger.error(f"Error searching vectors: {e}")
            return []
    
    async def get_vector(
        self,
        vector_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific vector by ID.
        
        Args:
            vector_id: Vector ID
            
        Returns:
            Vector data or None if not found
        """
        try:
            async with get_db_context() as db:
                result = await db.execute(text("""
                    SELECT 
                        vector_id,
                        content,
                        embedding,
                        metadata,
                        created_at,
                        updated_at
                    FROM context_vectors
                    WHERE vector_id = :vector_id
                """), {"vector_id": vector_id})
                
                row = result.first()
                if row:
                    return {
                        "id": row.vector_id,
                        "content": row.content,
                        "embedding": list(row.embedding) if row.embedding else None,
                        "metadata": json.loads(row.metadata) if row.metadata else {},
                        "created_at": row.created_at.isoformat(),
                        "updated_at": row.updated_at.isoformat()
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting vector: {e}")
            return None
    
    async def delete_vector(
        self,
        vector_id: str
    ) -> bool:
        """
        Delete a vector.
        
        Args:
            vector_id: Vector ID
            
        Returns:
            Success status
        """
        try:
            async with get_db_context() as db:
                result = await db.execute(text("""
                    DELETE FROM context_vectors
                    WHERE vector_id = :vector_id
                """), {"vector_id": vector_id})
                
                await db.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting vector: {e}")
            return False
    
    async def update_vector_metadata(
        self,
        vector_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update vector metadata.
        
        Args:
            vector_id: Vector ID
            metadata: New metadata (will be merged with existing)
            
        Returns:
            Success status
        """
        try:
            async with get_db_context() as db:
                # Get existing metadata
                result = await db.execute(text("""
                    SELECT metadata FROM context_vectors
                    WHERE vector_id = :vector_id
                """), {"vector_id": vector_id})
                
                row = result.first()
                if not row:
                    return False
                
                # Merge metadata
                existing_metadata = json.loads(row.metadata) if row.metadata else {}
                existing_metadata.update(metadata)
                
                # Update
                await db.execute(text("""
                    UPDATE context_vectors
                    SET metadata = :metadata,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE vector_id = :vector_id
                """), {
                    "metadata": json.dumps(existing_metadata),
                    "vector_id": vector_id
                })
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating vector metadata: {e}")
            return False
    
    async def bulk_store_vectors(
        self,
        vectors: List[Tuple[str, List[float], Dict[str, Any]]]
    ) -> int:
        """
        Store multiple vectors in bulk.
        
        Args:
            vectors: List of (content, embedding, metadata) tuples
            
        Returns:
            Number of successfully stored vectors
        """
        try:
            stored = 0
            
            async with get_db_context() as db:
                for content, embedding, metadata in vectors:
                    vector_id = self._generate_vector_id(content)
                    user_id = metadata.get("user_id", "system")
                    
                    try:
                        await db.execute(text("""
                            INSERT INTO context_vectors 
                            (user_id, vector_id, content, embedding, metadata)
                            VALUES (:user_id, :vector_id, :content, :embedding, :metadata)
                            ON CONFLICT (vector_id) DO UPDATE
                            SET content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding,
                                metadata = EXCLUDED.metadata,
                                updated_at = CURRENT_TIMESTAMP
                        """), {
                            "user_id": user_id,
                            "vector_id": vector_id,
                            "content": content,
                            "embedding": embedding,
                            "metadata": json.dumps(metadata)
                        })
                        stored += 1
                    except Exception as e:
                        logger.error(f"Error storing vector {vector_id}: {e}")
                
                await db.commit()
                logger.info(f"Bulk stored {stored} vectors")
                return stored
                
        except Exception as e:
            logger.error(f"Error in bulk store: {e}")
            return 0
    
    async def get_vector_statistics(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get vector storage statistics.
        
        Args:
            user_id: Optional user filter
            
        Returns:
            Statistics dictionary
        """
        try:
            async with get_db_context() as db:
                # Base query
                where_clause = "WHERE user_id = :user_id" if user_id else ""
                params = {"user_id": user_id} if user_id else {}
                
                # Get counts
                result = await db.execute(text(f"""
                    SELECT 
                        COUNT(*) as total_vectors,
                        COUNT(DISTINCT user_id) as unique_users,
                        MIN(created_at) as oldest_vector,
                        MAX(created_at) as newest_vector
                    FROM context_vectors
                    {where_clause}
                """), params)
                
                row = result.first()
                
                stats = {
                    "total_vectors": row.total_vectors,
                    "unique_users": row.unique_users,
                    "oldest_vector": row.oldest_vector.isoformat() if row.oldest_vector else None,
                    "newest_vector": row.newest_vector.isoformat() if row.newest_vector else None
                }
                
                # Get metadata distribution
                result = await db.execute(text(f"""
                    SELECT 
                        metadata->>'type' as vector_type,
                        COUNT(*) as count
                    FROM context_vectors
                    {where_clause}
                    GROUP BY metadata->>'type'
                """), params)
                
                type_distribution = {}
                for row in result:
                    type_distribution[row.vector_type or "unknown"] = row.count
                
                stats["type_distribution"] = type_distribution
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting vector statistics: {e}")
            return {}
    
    def _generate_vector_id(self, content: str) -> str:
        """Generate unique vector ID from content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        This is a placeholder - in production, this would call an embedding API.
        """
        # Placeholder: generate random embedding
        # In production, use OpenAI, Cohere, or local model
        np.random.seed(hash(text) % 2**32)
        return np.random.randn(self.vector_dimension).tolist()