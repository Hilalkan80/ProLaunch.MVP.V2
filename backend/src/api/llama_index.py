"""
LlamaIndex API Endpoints

This module provides REST API endpoints for LlamaIndex functionality.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from ..ai import llama_service, EmbeddingService, ContextManager
from ..core.security.auth import get_current_user
from ..infrastructure.cache.redis_cache import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/llama",
    tags=["llama-index"],
)


# Request/Response Models
class EmbeddingRequest(BaseModel):
    """Request model for generating embeddings"""
    text: str = Field(..., description="Text to generate embedding for")
    use_cache: bool = Field(default=True, description="Whether to use cache")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class BatchEmbeddingRequest(BaseModel):
    """Request model for batch embedding generation"""
    texts: List[str] = Field(..., description="List of texts to generate embeddings for")
    use_cache: bool = Field(default=True, description="Whether to use cache")
    batch_size: Optional[int] = Field(default=None, description="Batch size for processing")
    metadata: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional metadata for each text")


class QueryRequest(BaseModel):
    """Request model for querying the index"""
    query: str = Field(..., description="Query text")
    similarity_top_k: int = Field(default=5, description="Number of similar documents to retrieve")
    use_hyde: bool = Field(default=False, description="Use HyDE for enhanced retrieval")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters")


class ChatRequest(BaseModel):
    """Request model for chat with context"""
    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    context: Optional[str] = Field(default=None, description="Optional context")
    use_context_manager: bool = Field(default=True, description="Use context manager for enhanced context")


class DocumentRequest(BaseModel):
    """Request model for adding documents"""
    documents: List[Dict[str, Any]] = Field(..., description="Documents to add to index")


class SimilaritySearchRequest(BaseModel):
    """Request model for similarity search"""
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=5, description="Number of similar items to return")
    threshold: float = Field(default=0.7, description="Similarity threshold")


# Initialize services
embedding_service = None
context_manager = None


@router.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global embedding_service, context_manager
    
    redis_client = await get_redis_client()
    embedding_service = EmbeddingService(redis_client=redis_client)
    context_manager = ContextManager(redis_client=redis_client)
    
    logger.info("LlamaIndex API services initialized")


# Embedding Endpoints
@router.post("/embeddings/generate")
async def generate_embedding(
    request: EmbeddingRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate embedding for a single text"""
    try:
        result = await embedding_service.generate_embedding(
            text=request.text,
            use_cache=request.use_cache,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings/batch")
async def generate_embeddings_batch(
    request: BatchEmbeddingRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate embeddings for multiple texts"""
    try:
        results = await embedding_service.generate_embeddings_batch(
            texts=request.texts,
            use_cache=request.use_cache,
            batch_size=request.batch_size,
            metadata=request.metadata
        )
        
        return {
            "success": True,
            "data": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings/estimate-cost")
async def estimate_embedding_cost(
    texts: List[str],
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Estimate cost for generating embeddings"""
    try:
        cost_estimate = embedding_service.estimate_cost(texts)
        
        return {
            "success": True,
            "data": cost_estimate
        }
        
    except Exception as e:
        logger.error(f"Failed to estimate cost: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Query and Search Endpoints
@router.post("/query")
async def query_index(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Query the LlamaIndex with advanced options"""
    try:
        result = await llama_service.query(
            query_text=request.query,
            similarity_top_k=request.similarity_top_k,
            use_hyde=request.use_hyde,
            filters=request.filters
        )
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/similar")
async def search_similar(
    request: SimilaritySearchRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Search for similar content"""
    try:
        results = await context_manager.search_similar_content(
            query=request.query,
            top_k=request.top_k,
            threshold=request.threshold
        )
        
        return {
            "success": True,
            "data": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Similarity search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Chat Endpoints
@router.post("/chat")
async def chat_with_context(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Chat with optional context enhancement"""
    try:
        if request.use_context_manager and request.messages:
            # Extract the last user message as query
            last_user_message = next(
                (msg for msg in reversed(request.messages) if msg.get('role') == 'user'),
                None
            )
            
            if last_user_message:
                # Generate response with context
                result = await context_manager.generate_response_with_context(
                    query=last_user_message['content'],
                    context_type='all'
                )
                
                return {
                    "success": True,
                    "data": result
                }
        
        # Fallback to direct chat
        response = await llama_service.chat(
            messages=request.messages,
            context=request.context
        )
        
        return {
            "success": True,
            "data": {
                "response": response,
                "messages": request.messages
            }
        }
        
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Document Management Endpoints
@router.post("/documents/add")
async def add_documents(
    request: DocumentRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Add documents to the index"""
    try:
        # Add to background task for async processing
        background_tasks.add_task(
            llama_service.add_documents,
            request.documents
        )
        
        return {
            "success": True,
            "message": f"Adding {len(request.documents)} documents to index",
            "count": len(request.documents)
        }
        
    except Exception as e:
        logger.error(f"Failed to add documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/summarize")
async def summarize_text(
    text: str,
    max_length: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Summarize text using Claude"""
    try:
        summary = await llama_service.summarize(
            text=text,
            max_length=max_length
        )
        
        return {
            "success": True,
            "data": {
                "summary": summary,
                "original_length": len(text),
                "summary_length": len(summary)
            }
        }
        
    except Exception as e:
        logger.error(f"Summarization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Statistics and Health Endpoints
@router.get("/stats")
async def get_statistics(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get service statistics"""
    try:
        stats = {
            "llama_service": llama_service.get_stats(),
            "embedding_service": embedding_service.get_stats(),
            "context_manager": context_manager.get_service_stats()
        }
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stats/reset")
async def reset_statistics(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Reset service statistics"""
    try:
        embedding_service.reset_stats()
        
        return {
            "success": True,
            "message": "Statistics reset successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to reset statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    try:
        # Check if services are initialized
        llama_ready = llama_service.llm is not None
        embedding_ready = embedding_service is not None
        context_ready = context_manager is not None
        
        return {
            "status": "healthy" if all([llama_ready, embedding_ready, context_ready]) else "degraded",
            "services": {
                "llama_service": llama_ready,
                "embedding_service": embedding_ready,
                "context_manager": context_ready
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }