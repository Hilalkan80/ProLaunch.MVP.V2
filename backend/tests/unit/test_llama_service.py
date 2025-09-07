"""
Unit tests for LlamaIndex service implementation.

Tests the core LlamaIndex service functionality including initialization,
document management, querying, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from llama_index.core import Document
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.core.response.schema import Response

from src.ai.llama_service import LlamaIndexService
from src.ai.llama_config import LlamaIndexConfig


class TestLlamaIndexService:
    """Test LlamaIndexService class."""
    
    @patch('src.ai.llama_service.llama_config_manager')
    @patch('src.ai.llama_service.Anthropic')
    @patch('src.ai.llama_service.OpenAIEmbedding')
    @patch('src.ai.llama_service.PGVectorStore')
    def test_initialization_success(self, mock_pg_vector, mock_openai_embed, mock_anthropic, mock_config_manager):
        """Test successful service initialization."""
        # Mock config manager
        mock_config = LlamaIndexConfig(
            anthropic_api_key="test_key",
            openai_api_key="test_openai_key"
        )
        mock_config_manager.get_config.return_value = mock_config
        mock_config_manager.get_llm_config.return_value = {
            'model': 'claude-3-5-sonnet-20241022',
            'api_key': 'test_key',
            'max_tokens': 4096,
            'temperature': 0.7,
            'timeout': 60
        }
        mock_config_manager.get_embedding_config.return_value = {
            'model_name': 'text-embedding-3-small',
            'api_key': 'test_openai_key',
            'dimensions': 1536,
            'max_retries': 3,
            'timeout': 30
        }
        mock_config_manager.get_vector_store_config.return_value = {
            'database': 'test_db',
            'host': 'localhost',
            'password': 'test_pass',
            'port': 5432,
            'user': 'test_user',
            'table_name': 'embeddings',
            'embed_dim': 1536
        }
        mock_config_manager.get_service_context_config.return_value = {
            'chunk_size': 512,
            'chunk_overlap': 50,
            'context_window': 100000,
            'num_output': 4096
        }
        
        # Initialize service
        service = LlamaIndexService()
        
        # Verify components were initialized
        assert service.llm is not None
        assert service.embed_model is not None
        assert service.vector_store is not None
        assert service.storage_context is not None
        mock_anthropic.assert_called_once()
        mock_openai_embed.assert_called_once()
        mock_pg_vector.from_params.assert_called_once()
    
    @patch('src.ai.llama_service.llama_config_manager')
    def test_initialization_failure_missing_api_key(self, mock_config_manager):
        """Test initialization failure when API key is missing."""
        # Mock config with missing API key
        mock_config = LlamaIndexConfig(
            anthropic_api_key="",  # Empty API key
            openai_api_key="test_openai_key"
        )
        mock_config_manager.get_config.return_value = mock_config
        
        with pytest.raises(Exception):
            LlamaIndexService()
    
    @pytest.fixture
    def mock_service(self):
        """Create a mock LlamaIndex service for testing."""
        with patch('src.ai.llama_service.llama_config_manager') as mock_config_manager:
            # Setup mock config
            mock_config = LlamaIndexConfig(
                anthropic_api_key="test_key",
                openai_api_key="test_openai_key"
            )
            mock_config_manager.get_config.return_value = mock_config
            mock_config_manager.get_llm_config.return_value = {
                'model': 'claude-3-5-sonnet-20241022',
                'api_key': 'test_key',
                'max_tokens': 4096,
                'temperature': 0.7,
                'timeout': 60
            }
            mock_config_manager.get_embedding_config.return_value = {
                'model_name': 'text-embedding-3-small',
                'api_key': 'test_openai_key',
                'dimensions': 1536,
                'max_retries': 3,
                'timeout': 30
            }
            mock_config_manager.get_vector_store_config.return_value = {
                'database': 'test_db',
                'host': 'localhost',
                'password': 'test_pass',
                'port': 5432,
                'user': 'test_user',
                'table_name': 'embeddings',
                'embed_dim': 1536
            }
            mock_config_manager.get_service_context_config.return_value = {
                'chunk_size': 512,
                'chunk_overlap': 50,
                'context_window': 100000,
                'num_output': 4096
            }
            
            with patch('src.ai.llama_service.Anthropic'), \
                 patch('src.ai.llama_service.OpenAIEmbedding'), \
                 patch('src.ai.llama_service.PGVectorStore'):
                
                service = LlamaIndexService()
                
                # Mock the index and other components
                service.index = Mock()
                service.llm = Mock()
                service.embed_model = Mock()
                service.vector_store = Mock()
                
                yield service
    
    @pytest.mark.asyncio
    async def test_create_index_success(self, mock_service):
        """Test successful index creation."""
        mock_service.index = None  # Start with no index
        
        # Mock VectorStoreIndex.from_documents
        with patch('src.ai.llama_service.VectorStoreIndex') as mock_index_class:
            mock_index = Mock()
            mock_index_class.from_documents.return_value = mock_index
            
            documents = [
                Document(text="Test document 1", metadata={"source": "test1"}),
                Document(text="Test document 2", metadata={"source": "test2"})
            ]
            
            result = await mock_service.create_index(documents)
            
            assert result == mock_index
            assert mock_service.index == mock_index
            mock_index_class.from_documents.assert_called_once_with(
                documents=documents,
                storage_context=mock_service.storage_context,
                show_progress=True
            )
    
    @pytest.mark.asyncio
    async def test_add_documents_new_index(self, mock_service):
        """Test adding documents when no index exists."""
        mock_service.index = None
        
        with patch.object(mock_service, 'create_index') as mock_create_index:
            mock_create_index.return_value = Mock()
            
            documents = [
                {"text": "New document", "metadata": {"source": "new"}}
            ]
            
            result = await mock_service.add_documents(documents)
            
            assert result is True
            mock_create_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_documents_existing_index(self, mock_service):
        """Test adding documents to existing index."""
        mock_index = Mock()
        mock_service.index = mock_index
        
        documents = [
            {"text": "Additional document", "metadata": {"source": "additional"}}
        ]
        
        result = await mock_service.add_documents(documents)
        
        assert result is True
        mock_index.insert.assert_called()
    
    def test_prepare_documents_mixed_types(self, mock_service):
        """Test document preparation with mixed input types."""
        documents = [
            Document(text="Document object", metadata={"type": "doc"}),
            {"text": "Dict document", "metadata": {"type": "dict"}, "doc_id": "doc_001"},
            "invalid_document",  # Should be skipped
            {"text": "Minimal dict"}  # Minimal valid dict
        ]
        
        prepared = mock_service._prepare_documents(documents)
        
        assert len(prepared) == 3  # Invalid document should be skipped
        assert all(isinstance(doc, Document) for doc in prepared)
        assert prepared[0].text == "Document object"
        assert prepared[1].text == "Dict document"
        assert prepared[2].text == "Minimal dict"
    
    @pytest.mark.asyncio
    async def test_query_no_index(self, mock_service):
        """Test querying when no index exists."""
        mock_service.index = None
        
        result = await mock_service.query("test query")
        
        assert result["response"] is None
        assert result["source_nodes"] == []
    
    @pytest.mark.asyncio
    async def test_query_with_index(self, mock_service):
        """Test successful querying with index."""
        # Mock query engine and response
        mock_query_engine = Mock()
        mock_response = Mock()
        mock_response.source_nodes = [
            Mock(node=Mock(text="Source text", metadata={"source": "test"}, node_id="node_1"), score=0.95)
        ]
        mock_service.index.as_query_engine.return_value = mock_query_engine
        
        # Mock asyncio.get_event_loop().run_in_executor
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_response
            
            result = await mock_service.query(
                query_text="test query",
                similarity_top_k=3,
                use_hyde=False
            )
            
            assert "response" in result
            assert "source_nodes" in result
            assert "metadata" in result
            assert result["metadata"]["query"] == "test query"
            assert result["metadata"]["similarity_top_k"] == 3
            assert result["metadata"]["use_hyde"] is False
    
    @pytest.mark.asyncio
    async def test_query_with_hyde(self, mock_service):
        """Test querying with HyDE transformation."""
        mock_query_engine = Mock()
        mock_service.index.as_query_engine.return_value = mock_query_engine
        
        with patch('src.ai.llama_service.HyDEQueryTransform') as mock_hyde:
            mock_hyde_instance = Mock()
            mock_hyde.return_value = mock_hyde_instance
            mock_hyde_instance.transform.return_value = mock_query_engine
            
            mock_response = Mock()
            mock_response.source_nodes = []
            
            with patch('asyncio.get_event_loop') as mock_get_loop:
                mock_loop = AsyncMock()
                mock_get_loop.return_value = mock_loop
                mock_loop.run_in_executor.return_value = mock_response
                
                result = await mock_service.query(
                    query_text="test query",
                    use_hyde=True
                )
                
                assert result["metadata"]["use_hyde"] is True
                mock_hyde.assert_called_once_with(include_original=True)
                mock_hyde_instance.transform.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_embeddings_success(self, mock_service):
        """Test successful embedding generation."""
        texts = ["Text 1", "Text 2", "Text 3"]
        mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
        
        mock_service.embed_model.get_text_embedding_batch.return_value = mock_embeddings
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_embeddings
            
            result = await mock_service.get_embeddings(texts)
            
            assert result == mock_embeddings
            assert len(result) == 3
    
    @pytest.mark.asyncio
    async def test_similarity_search_success(self, mock_service):
        """Test successful similarity search."""
        query_embedding = [0.1, 0.2, 0.3]
        mock_results = [
            Mock(node=Mock(text="Result 1"), score=0.95),
            Mock(node=Mock(text="Result 2"), score=0.87)
        ]
        
        mock_service.vector_store.query.return_value = mock_results
        
        result = await mock_service.similarity_search(
            query_embedding=query_embedding,
            top_k=2,
            filters={"category": "test"}
        )
        
        assert result == mock_results
        mock_service.vector_store.query.assert_called_once_with(
            query_embedding=query_embedding,
            similarity_top_k=2,
            filters={"category": "test"}
        )
    
    @pytest.mark.asyncio
    async def test_similarity_search_no_vector_store(self, mock_service):
        """Test similarity search when vector store is not available."""
        mock_service.vector_store = None
        
        result = await mock_service.similarity_search([0.1, 0.2, 0.3])
        
        assert result == []
    
    def test_format_source_nodes(self, mock_service):
        """Test source node formatting."""
        source_nodes = [
            Mock(
                node=Mock(
                    text="Node text 1",
                    metadata={"source": "test1"},
                    node_id="node_1"
                ),
                score=0.95
            ),
            Mock(
                node=Mock(
                    text="Node text 2",
                    metadata={"source": "test2"},
                    node_id="node_2"
                ),
                score=0.87
            )
        ]
        
        formatted = mock_service._format_source_nodes(source_nodes)
        
        assert len(formatted) == 2
        assert formatted[0]["text"] == "Node text 1"
        assert formatted[0]["score"] == 0.95
        assert formatted[0]["metadata"]["source"] == "test1"
        assert formatted[0]["node_id"] == "node_1"
    
    @pytest.mark.asyncio
    async def test_chat_with_context(self, mock_service):
        """Test chat functionality with context."""
        messages = [{"role": "user", "content": "Hello"}]
        context = "This is test context"
        
        mock_response = Mock()
        mock_response.message.content = "Hello! How can I help you?"
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_response
            
            result = await mock_service.chat(
                messages=messages,
                context=context
            )
            
            assert result == "Hello! How can I help you?"
    
    @pytest.mark.asyncio
    async def test_chat_without_context(self, mock_service):
        """Test chat functionality without context."""
        messages = [{"role": "user", "content": "Hello"}]
        
        mock_response = Mock()
        mock_response.message.content = "Hello!"
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_response
            
            result = await mock_service.chat(messages=messages)
            
            assert result == "Hello!"
    
    @pytest.mark.asyncio
    async def test_summarize_text(self, mock_service):
        """Test text summarization."""
        text = "This is a long text that needs to be summarized for testing purposes."
        max_length = 50
        
        mock_response = Mock()
        mock_response.text = "This is a summary of the text."
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_response
            
            result = await mock_service.summarize(text, max_length)
            
            assert result == "This is a summary of the text."
    
    def test_get_stats(self, mock_service):
        """Test getting service statistics."""
        mock_service.index = Mock()
        mock_service.index.docstore.docs = {"doc1": Mock(), "doc2": Mock(), "doc3": Mock()}
        
        stats = mock_service.get_stats()
        
        expected_keys = {
            "llm_model", "embedding_model", "vector_store_type",
            "index_initialized", "chunk_size", "context_window", "num_documents"
        }
        assert set(stats.keys()) == expected_keys
        assert stats["index_initialized"] is True
        assert stats["num_documents"] == 3
    
    def test_get_stats_no_index(self, mock_service):
        """Test getting statistics when no index exists."""
        mock_service.index = None
        
        stats = mock_service.get_stats()
        
        assert stats["index_initialized"] is False
        assert "num_documents" not in stats


class TestErrorHandling:
    """Test error handling in LlamaIndex service."""
    
    @pytest.fixture
    def error_service(self):
        """Create a service that will raise errors for testing."""
        with patch('src.ai.llama_service.llama_config_manager') as mock_config_manager:
            mock_config = LlamaIndexConfig(
                anthropic_api_key="test_key",
                openai_api_key="test_openai_key"
            )
            mock_config_manager.get_config.return_value = mock_config
            mock_config_manager.get_llm_config.return_value = {
                'model': 'claude-3-5-sonnet-20241022',
                'api_key': 'test_key',
                'max_tokens': 4096,
                'temperature': 0.7,
                'timeout': 60
            }
            mock_config_manager.get_embedding_config.return_value = {
                'model_name': 'text-embedding-3-small',
                'api_key': 'test_openai_key',
                'dimensions': 1536,
                'max_retries': 3,
                'timeout': 30
            }
            mock_config_manager.get_vector_store_config.return_value = {
                'database': 'test_db',
                'host': 'localhost',
                'password': 'test_pass',
                'port': 5432,
                'user': 'test_user',
                'table_name': 'embeddings',
                'embed_dim': 1536
            }
            mock_config_manager.get_service_context_config.return_value = {
                'chunk_size': 512,
                'chunk_overlap': 50,
                'context_window': 100000,
                'num_output': 4096
            }
            
            with patch('src.ai.llama_service.Anthropic'), \
                 patch('src.ai.llama_service.OpenAIEmbedding'), \
                 patch('src.ai.llama_service.PGVectorStore'):
                
                service = LlamaIndexService()
                service.index = Mock()
                service.llm = Mock()
                service.embed_model = Mock()
                service.vector_store = Mock()
                
                yield service
    
    @pytest.mark.asyncio
    async def test_create_index_error(self, error_service):
        """Test error handling in index creation."""
        with patch('src.ai.llama_service.VectorStoreIndex') as mock_index_class:
            mock_index_class.from_documents.side_effect = Exception("Index creation failed")
            
            documents = [Document(text="Test document")]
            
            with pytest.raises(Exception) as exc_info:
                await error_service.create_index(documents)
            
            assert "Index creation failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_add_documents_error(self, error_service):
        """Test error handling in document addition."""
        error_service.index = Mock()
        error_service.index.insert.side_effect = Exception("Document insertion failed")
        
        documents = [{"text": "Test document"}]
        
        result = await error_service.add_documents(documents)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_query_error(self, error_service):
        """Test error handling in querying."""
        error_service.index.as_query_engine.side_effect = Exception("Query failed")
        
        with pytest.raises(Exception) as exc_info:
            await error_service.query("test query")
        
        assert "Query failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_embeddings_error(self, error_service):
        """Test error handling in embedding generation."""
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.side_effect = Exception("Embedding generation failed")
            
            with pytest.raises(Exception) as exc_info:
                await error_service.get_embeddings(["test text"])
            
            assert "Embedding generation failed" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])