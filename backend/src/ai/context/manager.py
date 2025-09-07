from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
from .layers import SessionContext, JourneyContext, KnowledgeContext
from .token_optimizer import TokenOptimizer
from ..llama_service import llama_service
from ..embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class ContextManager:
    def __init__(self, redis_client=None):
        self.session_context = SessionContext()
        self.journey_context = JourneyContext()
        self.knowledge_context = KnowledgeContext()
        self.optimizer = TokenOptimizer()
        
        # Initialize LlamaIndex integration
        self.llama_service = llama_service
        self.embedding_service = EmbeddingService(redis_client=redis_client)
        
        # Track indexed documents
        self.indexed_documents = set()
        
        logger.info("ContextManager initialized with LlamaIndex integration")
        
    async def add_message(self, content: Dict[str, str], metadata: Optional[Dict] = None) -> bool:
        """Add a message to session context"""
        return await self.session_context.add(content, metadata)
        
    async def add_milestone(self, content: Dict[str, Any], milestone: str, metadata: Optional[Dict] = None) -> bool:
        """Add content to journey context with milestone"""
        full_metadata = {
            'milestone': milestone,
            **(metadata or {})
        }
        return await self.journey_context.add(content, full_metadata)
        
    async def add_knowledge(self, content: str, metadata: Optional[Dict] = None) -> bool:
        """Add content to knowledge context and LlamaIndex"""
        # Add to traditional knowledge context
        success = await self.knowledge_context.add(content, metadata)
        
        if success:
            # Also index in LlamaIndex for advanced retrieval
            try:
                doc_id = metadata.get('doc_id') if metadata else None
                if doc_id and doc_id not in self.indexed_documents:
                    await self.llama_service.add_documents([{
                        'text': content,
                        'metadata': metadata,
                        'doc_id': doc_id
                    }])
                    self.indexed_documents.add(doc_id)
                    logger.debug(f"Document {doc_id} indexed in LlamaIndex")
            except Exception as e:
                logger.error(f"Failed to index document in LlamaIndex: {str(e)}")
        
        return success
        
    async def get_context(self, query: Optional[str] = None, milestone: Optional[str] = None, use_llama_index: bool = True, **kwargs) -> Dict[str, Any]:
        """Get context from all layers with optional LlamaIndex enhancement"""
        query_embedding = None
        llama_response = None
        
        if query:
            # Optimize prompt
            optimized = await self.optimizer.optimize_prompt(query)
            query_embedding = optimized['optimized_prompt']
            
            # Get embedding from OpenAI if LlamaIndex is enabled
            if use_llama_index:
                try:
                    embedding_result = await self.embedding_service.generate_embedding(query)
                    query_embedding = embedding_result['embedding']
                    
                    # Query LlamaIndex for enhanced context
                    llama_response = await self.llama_service.query(
                        query_text=query,
                        similarity_top_k=5,
                        use_hyde=True  # Use HyDE for better retrieval
                    )
                except Exception as e:
                    logger.error(f"LlamaIndex query failed: {str(e)}")
        
        # Get traditional context
        results = {
            'session': await self.session_context.get(**kwargs),
            'journey': await self.journey_context.get(
                query_embedding=query_embedding,
                milestone=milestone,
                **kwargs
            ),
            'knowledge': await self.knowledge_context.get(
                query_embedding=query_embedding,
                **kwargs
            )
        }
        
        # Add LlamaIndex results if available
        if llama_response:
            results['llama_context'] = {
                'response': llama_response.get('response'),
                'source_nodes': llama_response.get('source_nodes', []),
                'metadata': llama_response.get('metadata', {})
            }
        
        return results
        
    async def clear_session(self) -> None:
        """Clear session context"""
        await self.session_context.clear()
        
    async def generate_response_with_context(
        self,
        query: str,
        context_type: str = 'all',
        milestone: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate AI response using context and Claude via LlamaIndex"""
        try:
            # Get relevant context
            context = await self.get_context(
                query=query,
                milestone=milestone,
                use_llama_index=True,
                **kwargs
            )
            
            # Prepare context for Claude
            context_text = self._prepare_context_text(context, context_type)
            
            # Generate response using Claude through LlamaIndex
            messages = [
                {"role": "user", "content": query}
            ]
            
            response = await self.llama_service.chat(
                messages=messages,
                context=context_text
            )
            
            return {
                'response': response,
                'context_used': context,
                'query': query,
                'milestone': milestone
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response with context: {str(e)}")
            raise
    
    def _prepare_context_text(self, context: Dict[str, Any], context_type: str) -> str:
        """Prepare context text for Claude"""
        context_parts = []
        
        if context_type in ['all', 'session'] and context.get('session'):
            context_parts.append("Session Context:\n" + str(context['session'][:500]))
        
        if context_type in ['all', 'journey'] and context.get('journey'):
            context_parts.append("Journey Context:\n" + str(context['journey'][:500]))
        
        if context_type in ['all', 'knowledge'] and context.get('knowledge'):
            context_parts.append("Knowledge Context:\n" + str(context['knowledge'][:500]))
        
        if context.get('llama_context') and context['llama_context'].get('response'):
            context_parts.append("Enhanced Context:\n" + context['llama_context']['response'][:1000])
        
        return "\n\n".join(context_parts)
    
    async def search_similar_content(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar content using embeddings"""
        try:
            # Generate embedding for query
            embedding_result = await self.embedding_service.generate_embedding(query)
            query_embedding = embedding_result['embedding']
            
            # Search in LlamaIndex
            similar_nodes = await self.llama_service.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k
            )
            
            # Format results
            results = []
            for node in similar_nodes:
                if node.score >= threshold:
                    results.append({
                        'text': node.node.text,
                        'score': float(node.score),
                        'metadata': node.node.metadata
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar content: {str(e)}")
            return []
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage per layer"""
        return {
            'session': self.session_context.token_limit,
            'journey': self.journey_context.token_limit,
            'knowledge': self.knowledge_context.token_limit,
            'total': 4000,  # Total budget
            'llama_context_window': 100000  # Claude's context window
        }
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get statistics from all services"""
        return {
            'token_usage': self.get_token_usage(),
            'llama_stats': self.llama_service.get_stats(),
            'embedding_stats': self.embedding_service.get_stats(),
            'indexed_documents': len(self.indexed_documents)
        }