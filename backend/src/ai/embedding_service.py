"""
Embedding Service for OpenAI text-embedding-3-small

This service provides embedding generation and management capabilities
using OpenAI's text-embedding-3-small model.
"""

import logging
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from openai import AsyncOpenAI, OpenAI
from redis import Redis
import tiktoken

from .llama_config import llama_config_manager

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing embeddings"""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.config = llama_config_manager.get_config()
        self.embedding_config = llama_config_manager.get_embedding_config()
        
        # Initialize OpenAI clients
        self.sync_client = OpenAI(api_key=self.embedding_config["api_key"])
        self.async_client = AsyncOpenAI(api_key=self.embedding_config["api_key"])
        
        # Initialize tokenizer for text-embedding-3-small
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Redis for caching (optional)
        self.redis_client = redis_client
        self.cache_enabled = self.config.enable_caching and redis_client is not None
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        # Embedding statistics
        self.stats = {
            "total_embeddings_generated": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_tokens_processed": 0,
            "errors": 0,
        }
    
    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate embedding for a single text"""
        try:
            # Check cache first
            if use_cache and self.cache_enabled:
                cached = await self._get_cached_embedding(text)
                if cached:
                    self.stats["cache_hits"] += 1
                    return cached
                self.stats["cache_misses"] += 1
            
            # Validate and prepare text
            prepared_text = self._prepare_text(text)
            
            # Generate embedding
            response = await self.async_client.embeddings.create(
                model=self.embedding_config["model_name"],
                input=prepared_text,
                dimensions=self.embedding_config["dimensions"],
            )
            
            embedding = response.data[0].embedding
            
            # Prepare result
            result = {
                "embedding": embedding,
                "text": text[:500],  # Store truncated text for reference
                "model": self.embedding_config["model_name"],
                "dimensions": len(embedding),
                "tokens": response.usage.total_tokens,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Cache the result
            if use_cache and self.cache_enabled:
                await self._cache_embedding(text, result)
            
            # Update statistics
            self.stats["total_embeddings_generated"] += 1
            self.stats["total_tokens_processed"] += response.usage.total_tokens
            
            logger.debug(f"Generated embedding for text of length {len(text)}")
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
        batch_size: Optional[int] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for multiple texts in batches"""
        try:
            batch_size = batch_size or self.config.batch_size
            results = []
            
            # Process metadata
            if metadata is None:
                metadata = [{}] * len(texts)
            elif len(metadata) != len(texts):
                raise ValueError("Metadata list must match texts list length")
            
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_metadata = metadata[i:i + batch_size]
                
                # Check cache for each text in batch
                batch_to_process = []
                batch_indices = []
                
                for idx, text in enumerate(batch_texts):
                    if use_cache and self.cache_enabled:
                        cached = await self._get_cached_embedding(text)
                        if cached:
                            self.stats["cache_hits"] += 1
                            results.append(cached)
                            continue
                        self.stats["cache_misses"] += 1
                    
                    batch_to_process.append(self._prepare_text(text))
                    batch_indices.append(i + idx)
                
                # Generate embeddings for uncached texts
                if batch_to_process:
                    response = await self.async_client.embeddings.create(
                        model=self.embedding_config["model_name"],
                        input=batch_to_process,
                        dimensions=self.embedding_config["dimensions"],
                    )
                    
                    # Process responses
                    for j, embedding_data in enumerate(response.data):
                        original_idx = batch_indices[j]
                        original_text = texts[original_idx]
                        
                        result = {
                            "embedding": embedding_data.embedding,
                            "text": original_text[:500],
                            "model": self.embedding_config["model_name"],
                            "dimensions": len(embedding_data.embedding),
                            "tokens": response.usage.total_tokens // len(response.data),
                            "metadata": metadata[original_idx],
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        
                        results.append(result)
                        
                        # Cache the result
                        if use_cache and self.cache_enabled:
                            await self._cache_embedding(original_text, result)
                    
                    # Update statistics
                    self.stats["total_embeddings_generated"] += len(response.data)
                    self.stats["total_tokens_processed"] += response.usage.total_tokens
                
                # Add delay to respect rate limits
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
            
            logger.info(f"Generated embeddings for {len(texts)} texts in batches")
            return results
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise
    
    def _prepare_text(self, text: str) -> str:
        """Prepare text for embedding generation"""
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Truncate if too long (max ~8000 tokens for text-embedding-3-small)
        max_tokens = 8000
        tokens = self.tokenizer.encode(text)
        
        if len(tokens) > max_tokens:
            tokens = tokens[:max_tokens]
            text = self.tokenizer.decode(tokens)
            logger.warning(f"Text truncated from {len(tokens)} to {max_tokens} tokens")
        
        return text
    
    async def _get_cached_embedding(self, text: str) -> Optional[Dict[str, Any]]:
        """Get cached embedding if available"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(text)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {str(e)}")
            return None
    
    async def _cache_embedding(self, text: str, embedding_data: Dict[str, Any]) -> None:
        """Cache embedding with TTL"""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(text)
            
            # Convert numpy arrays to lists for JSON serialization
            cache_data = embedding_data.copy()
            if isinstance(cache_data.get("embedding"), np.ndarray):
                cache_data["embedding"] = cache_data["embedding"].tolist()
            
            self.redis_client.setex(
                cache_key,
                self.config.cache_ttl,
                json.dumps(cache_data)
            )
            
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {str(e)}")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{self.embedding_config['model_name']}:{text_hash}"
    
    async def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
        metric: str = "cosine"
    ) -> float:
        """Calculate similarity between two embeddings"""
        try:
            arr1 = np.array(embedding1)
            arr2 = np.array(embedding2)
            
            if metric == "cosine":
                # Cosine similarity
                dot_product = np.dot(arr1, arr2)
                norm1 = np.linalg.norm(arr1)
                norm2 = np.linalg.norm(arr2)
                similarity = dot_product / (norm1 * norm2)
                
            elif metric == "euclidean":
                # Euclidean distance (convert to similarity)
                distance = np.linalg.norm(arr1 - arr2)
                similarity = 1 / (1 + distance)
                
            elif metric == "dot":
                # Dot product similarity
                similarity = np.dot(arr1, arr2)
                
            else:
                raise ValueError(f"Unknown similarity metric: {metric}")
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            raise
    
    async def find_similar(
        self,
        query_embedding: List[float],
        embeddings: List[Tuple[str, List[float]]],
        top_k: int = 5,
        threshold: float = 0.7,
        metric: str = "cosine"
    ) -> List[Dict[str, Any]]:
        """Find most similar embeddings to query"""
        try:
            similarities = []
            
            for text, embedding in embeddings:
                similarity = await self.calculate_similarity(
                    query_embedding,
                    embedding,
                    metric=metric
                )
                
                if similarity >= threshold:
                    similarities.append({
                        "text": text,
                        "similarity": similarity,
                    })
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            # Return top-k results
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find similar embeddings: {str(e)}")
            raise
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        return len(self.tokenizer.encode(text))
    
    def estimate_cost(self, texts: List[str]) -> Dict[str, Any]:
        """Estimate cost for embedding generation"""
        total_tokens = sum(self.estimate_tokens(text) for text in texts)
        
        # OpenAI text-embedding-3-small pricing (as of 2024)
        # $0.02 per 1M tokens
        cost_per_million = 0.02
        estimated_cost = (total_tokens / 1_000_000) * cost_per_million
        
        return {
            "total_texts": len(texts),
            "estimated_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 4),
            "model": self.embedding_config["model_name"],
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = self.stats.copy()
        stats["model"] = self.embedding_config["model_name"]
        stats["dimensions"] = self.embedding_config["dimensions"]
        stats["cache_enabled"] = self.cache_enabled
        
        if self.stats["total_embeddings_generated"] > 0:
            stats["avg_tokens_per_embedding"] = (
                self.stats["total_tokens_processed"] /
                self.stats["total_embeddings_generated"]
            )
            
            if self.cache_enabled:
                total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
                if total_requests > 0:
                    stats["cache_hit_rate"] = self.stats["cache_hits"] / total_requests
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset statistics"""
        self.stats = {
            "total_embeddings_generated": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_tokens_processed": 0,
            "errors": 0,
        }
        logger.info("Embedding service statistics reset")
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)