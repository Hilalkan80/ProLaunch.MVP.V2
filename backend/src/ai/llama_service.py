"""
LlamaIndex Service Layer

Core service implementation for LlamaIndex integration with Claude 3.7 Sonnet
and OpenAI embeddings.
"""

import os
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from llama_index.core import (
    VectorStoreIndex,
    Document,
    ServiceContext,
    StorageContext,
    Settings,
    SimpleDirectoryReader,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.response.schema import Response
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.core.indices.query.query_transform import HyDEQueryTransform
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from .llama_config import llama_config_manager

logger = logging.getLogger(__name__)


class LlamaIndexService:
    """Main service class for LlamaIndex operations"""
    
    def __init__(self):
        self.config = llama_config_manager.get_config()
        self.llm = None
        self.embed_model = None
        self.vector_store = None
        self.index = None
        self.service_context = None
        self.storage_context = None
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize LlamaIndex components"""
        try:
            # Initialize Claude LLM
            self._initialize_llm()
            
            # Initialize OpenAI Embeddings
            self._initialize_embeddings()
            
            # Initialize Vector Store
            self._initialize_vector_store()
            
            # Set up service context
            self._initialize_service_context()
            
            # Initialize storage context
            self._initialize_storage_context()
            
            logger.info("LlamaIndex components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LlamaIndex components: {str(e)}")
            raise
    
    def _initialize_llm(self):
        """Initialize Claude 3.7 Sonnet as the LLM"""
        try:
            llm_config = llama_config_manager.get_llm_config()
            
            self.llm = Anthropic(
                model=llm_config["model"],
                api_key=llm_config["api_key"],
                max_tokens=llm_config["max_tokens"],
                temperature=llm_config["temperature"],
                timeout=llm_config["timeout"],
            )
            
            # Set as default in Settings
            Settings.llm = self.llm
            
            logger.info(f"Initialized Claude LLM with model: {llm_config['model']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Claude LLM: {str(e)}")
            raise
    
    def _initialize_embeddings(self):
        """Initialize OpenAI text-embedding-3-small"""
        try:
            embed_config = llama_config_manager.get_embedding_config()
            
            self.embed_model = OpenAIEmbedding(
                model=embed_config["model_name"],
                api_key=embed_config["api_key"],
                dimensions=embed_config["dimensions"],
                max_retries=embed_config["max_retries"],
                timeout=embed_config["timeout"],
            )
            
            # Set as default in Settings
            Settings.embed_model = self.embed_model
            
            logger.info(f"Initialized OpenAI embeddings with model: {embed_config['model_name']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {str(e)}")
            raise
    
    def _initialize_vector_store(self):
        """Initialize PostgreSQL vector store with pgvector"""
        try:
            vector_config = llama_config_manager.get_vector_store_config()
            
            # Create connection string
            connection_string = (
                f"postgresql://{vector_config['user']}"
                f":{vector_config['password']}" if vector_config['password'] else ""
                f"@{vector_config['host']}:{vector_config['port']}"
                f"/{vector_config['database']}"
            )
            
            self.vector_store = PGVectorStore.from_params(
                database=vector_config['database'],
                host=vector_config['host'],
                password=vector_config['password'],
                port=vector_config['port'],
                user=vector_config['user'],
                table_name=vector_config['table_name'],
                embed_dim=vector_config['embed_dim'],
                hybrid_search=True,
                text_search_config="english",
            )
            
            logger.info(f"Initialized PostgreSQL vector store with table: {vector_config['table_name']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    def _initialize_service_context(self):
        """Initialize service context with configured settings"""
        try:
            context_config = llama_config_manager.get_service_context_config()
            
            # Create node parser
            node_parser = SentenceSplitter(
                chunk_size=context_config["chunk_size"],
                chunk_overlap=context_config["chunk_overlap"],
            )
            
            # Update Settings with configurations
            Settings.chunk_size = context_config["chunk_size"]
            Settings.chunk_overlap = context_config["chunk_overlap"]
            Settings.context_window = context_config["context_window"]
            Settings.num_output = context_config["num_output"]
            Settings.node_parser = node_parser
            
            logger.info("Service context initialized with custom settings")
            
        except Exception as e:
            logger.error(f"Failed to initialize service context: {str(e)}")
            raise
    
    def _initialize_storage_context(self):
        """Initialize storage context with vector store"""
        try:
            self.storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )
            
            logger.info("Storage context initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize storage context: {str(e)}")
            raise
    
    async def create_index(self, documents: List[Document]) -> VectorStoreIndex:
        """Create or update vector index from documents"""
        try:
            # Create index from documents
            self.index = VectorStoreIndex.from_documents(
                documents=documents,
                storage_context=self.storage_context,
                show_progress=True,
            )
            
            logger.info(f"Created index with {len(documents)} documents")
            return self.index
            
        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            raise
    
    async def add_documents(self, documents: List[Union[Document, Dict[str, Any]]]) -> bool:
        """Add documents to existing index"""
        try:
            if not self.index:
                # Create new index if it doesn't exist
                doc_objects = self._prepare_documents(documents)
                await self.create_index(doc_objects)
            else:
                # Add to existing index
                doc_objects = self._prepare_documents(documents)
                for doc in doc_objects:
                    self.index.insert(doc)
            
            logger.info(f"Added {len(documents)} documents to index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            return False
    
    def _prepare_documents(self, documents: List[Union[Document, Dict[str, Any]]]) -> List[Document]:
        """Prepare documents for indexing"""
        doc_objects = []
        
        for doc in documents:
            if isinstance(doc, Document):
                doc_objects.append(doc)
            elif isinstance(doc, dict):
                # Convert dict to Document
                doc_obj = Document(
                    text=doc.get("text", ""),
                    metadata=doc.get("metadata", {}),
                    doc_id=doc.get("doc_id"),
                )
                doc_objects.append(doc_obj)
            else:
                logger.warning(f"Skipping invalid document type: {type(doc)}")
        
        return doc_objects
    
    async def query(
        self,
        query_text: str,
        similarity_top_k: int = 5,
        use_hyde: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Query the index with advanced options"""
        try:
            if not self.index:
                logger.warning("No index available for querying")
                return {"response": None, "source_nodes": []}
            
            # Create query engine
            query_engine = self.index.as_query_engine(
                similarity_top_k=similarity_top_k,
                node_postprocessors=[
                    SimilarityPostprocessor(similarity_cutoff=0.7)
                ],
                **kwargs
            )
            
            # Apply HyDE if requested
            if use_hyde:
                hyde = HyDEQueryTransform(include_original=True)
                query_engine = hyde.transform(query_engine)
            
            # Execute query
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                query_engine.query,
                query_text
            )
            
            # Format response
            result = {
                "response": str(response),
                "source_nodes": self._format_source_nodes(response.source_nodes),
                "metadata": {
                    "query": query_text,
                    "timestamp": datetime.utcnow().isoformat(),
                    "similarity_top_k": similarity_top_k,
                    "use_hyde": use_hyde,
                }
            }
            
            logger.info(f"Query executed successfully: {query_text[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a list of texts"""
        try:
            embeddings = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.embed_model.get_text_embedding_batch,
                texts
            )
            
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise
    
    async def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[NodeWithScore]:
        """Perform similarity search with query embedding"""
        try:
            if not self.vector_store:
                logger.warning("Vector store not initialized")
                return []
            
            # Perform similarity search
            results = self.vector_store.query(
                query_embedding=query_embedding,
                similarity_top_k=top_k,
                filters=filters,
            )
            
            logger.info(f"Similarity search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise
    
    def _format_source_nodes(self, source_nodes: List[NodeWithScore]) -> List[Dict[str, Any]]:
        """Format source nodes for response"""
        formatted_nodes = []
        
        for node in source_nodes:
            formatted_nodes.append({
                "text": node.node.text,
                "score": node.score,
                "metadata": node.node.metadata,
                "node_id": node.node.node_id,
            })
        
        return formatted_nodes
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        context: Optional[str] = None,
        **kwargs
    ) -> str:
        """Chat interface with conversation history"""
        try:
            # Prepare chat prompt with context
            if context:
                system_message = f"Context: {context}\n\nPlease answer based on the provided context."
                messages = [{"role": "system", "content": system_message}] + messages
            
            # Get response from Claude
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.llm.chat,
                messages
            )
            
            logger.info("Chat response generated successfully")
            return response.message.content
            
        except Exception as e:
            logger.error(f"Chat failed: {str(e)}")
            raise
    
    async def summarize(self, text: str, max_length: Optional[int] = None) -> str:
        """Summarize text using Claude"""
        try:
            prompt = f"Please provide a concise summary of the following text"
            if max_length:
                prompt += f" in approximately {max_length} words"
            prompt += f":\n\n{text}"
            
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.llm.complete,
                prompt
            )
            
            logger.info("Text summarized successfully")
            return response.text
            
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = {
            "llm_model": self.config.anthropic_model,
            "embedding_model": self.config.openai_embedding_model,
            "vector_store_type": self.config.vector_store_type,
            "index_initialized": self.index is not None,
            "chunk_size": self.config.chunk_size,
            "context_window": self.config.context_window,
        }
        
        if self.index:
            stats["num_documents"] = len(self.index.docstore.docs)
        
        return stats
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


# Singleton instance
llama_service = LlamaIndexService()