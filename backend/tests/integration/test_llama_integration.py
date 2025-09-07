"""
Integration tests for LlamaIndex service components.

Tests the complete integration between LlamaIndex components including
LLM, embeddings, vector store, and document management in realistic scenarios.
"""

import pytest
import asyncio
import os
import tempfile
from typing import List, Dict, Any
from datetime import datetime
from unittest.mock import patch, Mock, AsyncMock

from llama_index.core import Document
import numpy as np

from src.ai.llama_service import LlamaIndexService
from src.ai.llama_config import LlamaIndexConfig, LlamaIndexConfigManager


@pytest.fixture(scope="session")
def integration_config():
    """Configuration for integration testing."""
    return {
        'anthropic_api_key': 'test_anthropic_key_integration',
        'openai_api_key': 'test_openai_key_integration',
        'anthropic_model': 'claude-3-5-sonnet-20241022',
        'anthropic_max_tokens': 4096,
        'anthropic_temperature': 0.7,
        'openai_embedding_model': 'text-embedding-3-small',
        'openai_embedding_dimensions': 1536,
        'vector_store_host': 'localhost',
        'vector_store_port': 5432,
        'vector_store_database': 'test_prolaunch',
        'vector_store_user': 'test_user',
        'vector_store_password': 'test_password',
        'vector_store_table_name': 'test_embeddings',
        'chunk_size': 512,
        'chunk_overlap': 50,
        'context_window': 100000,
        'max_workers': 3
    }


@pytest.fixture
async def mock_llama_service(integration_config):
    """Create a LlamaIndex service with mocked external dependencies."""
    
    # Mock the config manager to return test config
    with patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': integration_config['anthropic_api_key'],
        'OPENAI_API_KEY': integration_config['openai_api_key'],
        'ANTHROPIC_MODEL_CHAT': integration_config['anthropic_model'],
        'OPENAI_EMBEDDING_MODEL': integration_config['openai_embedding_model'],
        'VECTOR_STORE_HOST': integration_config['vector_store_host'],
        'VECTOR_STORE_DATABASE': integration_config['vector_store_database'],
        'LLAMA_CHUNK_SIZE': str(integration_config['chunk_size'])
    }):
        
        # Mock external services
        with patch('src.ai.llama_service.Anthropic') as mock_anthropic, \
             patch('src.ai.llama_service.OpenAIEmbedding') as mock_openai_embed, \
             patch('src.ai.llama_service.PGVectorStore') as mock_pg_vector:
            
            # Setup mock LLM
            mock_llm = Mock()
            mock_llm.chat = AsyncMock()
            mock_llm.complete = AsyncMock()
            mock_anthropic.return_value = mock_llm
            
            # Setup mock embedding model
            mock_embed_model = Mock()
            mock_embed_model.get_text_embedding_batch = Mock()
            mock_openai_embed.return_value = mock_embed_model
            
            # Setup mock vector store
            mock_vector_store = Mock()
            mock_pg_vector.from_params.return_value = mock_vector_store
            
            # Create service
            service = LlamaIndexService()
            
            # Store references to mocks for test access
            service._mock_llm = mock_llm
            service._mock_embed_model = mock_embed_model
            service._mock_vector_store = mock_vector_store
            
            yield service


class TestLlamaIndexIntegration:
    """Integration tests for LlamaIndex service."""
    
    @pytest.mark.asyncio
    async def test_complete_document_workflow(self, mock_llama_service):
        """Test complete document ingestion and querying workflow."""
        service = mock_llama_service
        
        # Mock vector store index creation
        with patch('src.ai.llama_service.VectorStoreIndex') as mock_index_class:
            mock_index = Mock()
            mock_query_engine = Mock()
            
            mock_index_class.from_documents.return_value = mock_index
            mock_index.as_query_engine.return_value = mock_query_engine
            mock_index.docstore.docs = {"doc1": Mock(), "doc2": Mock()}
            
            # Mock query response
            mock_response = Mock()
            mock_response.source_nodes = [
                Mock(
                    node=Mock(
                        text="AI is transforming business operations",
                        metadata={"source": "doc1"},
                        node_id="node_1"
                    ),
                    score=0.95
                )
            ]
            
            # Mock executor for async operations
            with patch('asyncio.get_event_loop') as mock_get_loop:
                mock_loop = AsyncMock()
                mock_get_loop.return_value = mock_loop
                mock_loop.run_in_executor.return_value = mock_response
                
                # Step 1: Create index with documents
                documents = [
                    Document(
                        text="Artificial Intelligence is revolutionizing business operations across industries.",
                        metadata={"source": "business_ai.pdf", "category": "technology"}
                    ),
                    Document(
                        text="Machine learning models require careful validation and monitoring.",
                        metadata={"source": "ml_validation.pdf", "category": "technology"}
                    ),
                    Document(
                        text="Digital transformation strategies must align with business objectives.",
                        metadata={"source": "digital_transform.pdf", "category": "strategy"}
                    )
                ]
                
                index = await service.create_index(documents)
                
                assert index is not None
                assert service.index == index
                mock_index_class.from_documents.assert_called_once()
                
                # Verify document processing
                call_args = mock_index_class.from_documents.call_args
                assert len(call_args[1]['documents']) == 3
                assert call_args[1]['storage_context'] == service.storage_context
                
                # Step 2: Query the index
                query_result = await service.query(
                    query_text="How is AI transforming business?",
                    similarity_top_k=3,
                    use_hyde=False
                )
                
                # Verify query results structure
                assert "response" in query_result
                assert "source_nodes" in query_result
                assert "metadata" in query_result
                assert query_result["metadata"]["query"] == "How is AI transforming business?"
                assert query_result["metadata"]["similarity_top_k"] == 3
                
                # Verify source nodes formatting
                source_nodes = query_result["source_nodes"]
                assert len(source_nodes) == 1
                assert source_nodes[0]["text"] == "AI is transforming business operations"
                assert source_nodes[0]["score"] == 0.95
                assert source_nodes[0]["node_id"] == "node_1"
    
    @pytest.mark.asyncio
    async def test_document_addition_and_incremental_indexing(self, mock_llama_service):
        """Test adding documents to an existing index."""
        service = mock_llama_service
        
        with patch('src.ai.llama_service.VectorStoreIndex') as mock_index_class:
            # Setup existing index
            mock_index = Mock()
            service.index = mock_index
            
            # Test adding new documents
            new_documents = [
                {
                    "text": "Cloud computing enables scalable AI solutions.",
                    "metadata": {"source": "cloud_ai.pdf", "category": "infrastructure"},
                    "doc_id": "cloud_001"
                },
                {
                    "text": "Data privacy regulations impact AI development.",
                    "metadata": {"source": "privacy_ai.pdf", "category": "compliance"}
                }
            ]
            
            result = await service.add_documents(new_documents)
            
            assert result is True
            
            # Verify documents were processed and inserted
            assert mock_index.insert.call_count == 2
            
            # Verify Document objects were created correctly
            insert_calls = mock_index.insert.call_args_list
            inserted_doc1 = insert_calls[0][0][0]
            inserted_doc2 = insert_calls[1][0][0]
            
            assert inserted_doc1.text == "Cloud computing enables scalable AI solutions."
            assert inserted_doc1.metadata["category"] == "infrastructure"
            assert inserted_doc2.text == "Data privacy regulations impact AI development."
            assert inserted_doc2.metadata["category"] == "compliance"
    
    @pytest.mark.asyncio
    async def test_embedding_generation_workflow(self, mock_llama_service):
        """Test embedding generation for multiple texts."""
        service = mock_llama_service
        
        # Mock embedding responses
        mock_embeddings = [
            [0.1, 0.2, 0.3, 0.4, 0.5],  # Simplified 5-dim embeddings for testing
            [0.6, 0.7, 0.8, 0.9, 1.0],
            [0.2, 0.3, 0.4, 0.5, 0.6]
        ]
        
        service._mock_embed_model.get_text_embedding_batch.return_value = mock_embeddings
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_embeddings
            
            texts = [
                "Machine learning algorithms process data efficiently.",
                "Natural language processing enables human-AI interaction.",
                "Computer vision systems analyze visual information."
            ]
            
            embeddings = await service.get_embeddings(texts)
            
            assert len(embeddings) == 3
            assert embeddings == mock_embeddings
            
            # Verify the embedding model was called correctly
            mock_loop.run_in_executor.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_similarity_search_integration(self, mock_llama_service):
        """Test similarity search functionality."""
        service = mock_llama_service
        
        # Mock vector store query results
        mock_results = [
            Mock(
                node=Mock(
                    text="Deep learning models achieve high accuracy on complex tasks.",
                    metadata={"source": "deep_learning.pdf", "category": "research"},
                    node_id="node_dl_001"
                ),
                score=0.92
            ),
            Mock(
                node=Mock(
                    text="Neural networks require extensive computational resources.",
                    metadata={"source": "neural_nets.pdf", "category": "research"},
                    node_id="node_nn_001"
                ),
                score=0.87
            )
        ]
        
        service._mock_vector_store.query.return_value = mock_results
        
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        filters = {"category": "research"}
        
        results = await service.similarity_search(
            query_embedding=query_embedding,
            top_k=2,
            filters=filters
        )
        
        assert len(results) == 2
        assert results[0].score == 0.92
        assert results[1].score == 0.87
        assert "Deep learning models" in results[0].node.text
        assert "Neural networks" in results[1].node.text
        
        # Verify vector store was called with correct parameters
        service._mock_vector_store.query.assert_called_once_with(
            query_embedding=query_embedding,
            similarity_top_k=2,
            filters=filters
        )
    
    @pytest.mark.asyncio
    async def test_chat_integration_with_context(self, mock_llama_service):
        """Test chat functionality with context integration."""
        service = mock_llama_service
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.message.content = "Based on the provided context about AI in business, I can help you understand how machine learning is transforming operations across various industries."
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_response
            
            messages = [
                {"role": "user", "content": "Explain how AI is changing business operations"}
            ]
            
            context = "AI technologies, particularly machine learning and deep learning, are revolutionizing business processes by automating tasks, improving decision-making, and enabling new service offerings."
            
            response = await service.chat(
                messages=messages,
                context=context
            )
            
            expected_response = "Based on the provided context about AI in business, I can help you understand how machine learning is transforming operations across various industries."
            assert response == expected_response
            
            # Verify the executor was called
            mock_loop.run_in_executor.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_text_summarization_workflow(self, mock_llama_service):
        """Test text summarization functionality."""
        service = mock_llama_service
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.text = "AI and ML are transforming business operations through automation, improved analytics, and enhanced customer experiences."
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = mock_response
            
            long_text = """
            Artificial Intelligence and Machine Learning technologies are fundamentally transforming 
            the way businesses operate across all industries. From automating routine tasks to 
            providing sophisticated analytics capabilities, AI enables organizations to process 
            vast amounts of data more efficiently than ever before. Customer service has been 
            revolutionized through chatbots and intelligent routing systems, while supply chain 
            management benefits from predictive analytics and demand forecasting. Financial 
            services leverage AI for fraud detection and risk assessment, and healthcare 
            organizations use machine learning for diagnostic assistance and treatment optimization.
            """
            
            summary = await service.summarize(
                text=long_text,
                max_length=100
            )
            
            expected_summary = "AI and ML are transforming business operations through automation, improved analytics, and enhanced customer experiences."
            assert summary == expected_summary
    
    @pytest.mark.asyncio
    async def test_query_with_hyde_integration(self, mock_llama_service):
        """Test querying with HyDE (Hypothetical Document Embeddings) enhancement."""
        service = mock_llama_service
        
        with patch('src.ai.llama_service.VectorStoreIndex') as mock_index_class:
            mock_index = Mock()
            service.index = mock_index
            
            mock_query_engine = Mock()
            mock_index.as_query_engine.return_value = mock_query_engine
            
            # Mock HyDE transformation
            with patch('src.ai.llama_service.HyDEQueryTransform') as mock_hyde:
                mock_hyde_instance = Mock()
                mock_hyde.return_value = mock_hyde_instance
                
                enhanced_query_engine = Mock()
                mock_hyde_instance.transform.return_value = enhanced_query_engine
                
                # Mock query response
                mock_response = Mock()
                mock_response.source_nodes = [
                    Mock(
                        node=Mock(
                            text="Advanced AI systems demonstrate superior performance on complex reasoning tasks.",
                            metadata={"source": "ai_reasoning.pdf"},
                            node_id="hyde_node_1"
                        ),
                        score=0.98
                    )
                ]
                
                with patch('asyncio.get_event_loop') as mock_get_loop:
                    mock_loop = AsyncMock()
                    mock_get_loop.return_value = mock_loop
                    mock_loop.run_in_executor.return_value = mock_response
                    
                    result = await service.query(
                        query_text="What are the latest advances in AI reasoning capabilities?",
                        similarity_top_k=5,
                        use_hyde=True
                    )
                    
                    # Verify HyDE was used
                    assert result["metadata"]["use_hyde"] is True
                    mock_hyde.assert_called_once_with(include_original=True)
                    mock_hyde_instance.transform.assert_called_once()
                    
                    # Verify enhanced results
                    assert len(result["source_nodes"]) == 1
                    assert result["source_nodes"][0]["score"] == 0.98
                    assert "Advanced AI systems" in result["source_nodes"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_service_statistics_integration(self, mock_llama_service):
        """Test service statistics gathering."""
        service = mock_llama_service
        
        # Setup mock index with documents
        mock_index = Mock()
        mock_index.docstore.docs = {
            "doc1": Mock(),
            "doc2": Mock(),
            "doc3": Mock(),
            "doc4": Mock(),
            "doc5": Mock()
        }
        service.index = mock_index
        
        stats = service.get_stats()
        
        # Verify all expected stats are present
        expected_keys = {
            "llm_model", "embedding_model", "vector_store_type",
            "index_initialized", "chunk_size", "context_window", "num_documents"
        }
        assert set(stats.keys()) == expected_keys
        
        # Verify specific values
        assert stats["index_initialized"] is True
        assert stats["num_documents"] == 5
        assert stats["llm_model"] == "claude-3-5-sonnet-20241022"
        assert stats["embedding_model"] == "text-embedding-3-small"
        assert stats["chunk_size"] == 512
        assert stats["context_window"] == 100000


class TestLlamaIndexErrorHandling:
    """Integration tests for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_llm_service_unavailable(self, mock_llama_service):
        """Test handling when LLM service is unavailable."""
        service = mock_llama_service
        
        # Mock LLM failure
        service._mock_llm.chat.side_effect = Exception("Claude API unavailable")
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.side_effect = Exception("Claude API unavailable")
            
            messages = [{"role": "user", "content": "Test message"}]
            
            with pytest.raises(Exception) as exc_info:
                await service.chat(messages=messages)
            
            assert "Claude API unavailable" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_embedding_service_failure(self, mock_llama_service):
        """Test handling when embedding service fails."""
        service = mock_llama_service
        
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = AsyncMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.side_effect = Exception("OpenAI API rate limit exceeded")
            
            texts = ["Test text for embedding"]
            
            with pytest.raises(Exception) as exc_info:
                await service.get_embeddings(texts)
            
            assert "OpenAI API rate limit exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_vector_store_connection_failure(self, mock_llama_service):
        """Test handling when vector store connection fails."""
        service = mock_llama_service
        
        service._mock_vector_store.query.side_effect = Exception("PostgreSQL connection failed")
        
        query_embedding = [0.1, 0.2, 0.3]
        
        with pytest.raises(Exception) as exc_info:
            await service.similarity_search(query_embedding)
        
        assert "PostgreSQL connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_index_creation_failure(self, mock_llama_service):
        """Test handling when index creation fails."""
        service = mock_llama_service
        
        with patch('src.ai.llama_service.VectorStoreIndex') as mock_index_class:
            mock_index_class.from_documents.side_effect = Exception("Vector index creation failed")
            
            documents = [Document(text="Test document")]
            
            with pytest.raises(Exception) as exc_info:
                await service.create_index(documents)
            
            assert "Vector index creation failed" in str(exc_info.value)


class TestLlamaIndexPerformance:
    """Integration tests for performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_batch_document_processing_performance(self, mock_llama_service):
        """Test performance with batch document processing."""
        service = mock_llama_service
        
        with patch('src.ai.llama_service.VectorStoreIndex') as mock_index_class:
            mock_index = Mock()
            mock_index_class.from_documents.return_value = mock_index
            
            # Create a large batch of documents
            documents = [
                Document(
                    text=f"This is test document number {i} with some content about AI and machine learning.",
                    metadata={"doc_id": f"doc_{i:04d}", "batch": "performance_test"}
                )
                for i in range(100)
            ]
            
            start_time = datetime.utcnow()
            index = await service.create_index(documents)
            end_time = datetime.utcnow()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # Verify index was created
            assert index is not None
            mock_index_class.from_documents.assert_called_once()
            
            # Verify all documents were processed
            call_args = mock_index_class.from_documents.call_args
            assert len(call_args[1]['documents']) == 100
            
            # Performance should be reasonable (this is a mock test, so it should be very fast)
            assert processing_time < 5.0  # Should complete within 5 seconds for mocked operations
    
    @pytest.mark.asyncio
    async def test_concurrent_query_handling(self, mock_llama_service):
        """Test concurrent query processing."""
        service = mock_llama_service
        
        with patch('src.ai.llama_service.VectorStoreIndex') as mock_index_class:
            mock_index = Mock()
            mock_query_engine = Mock()
            service.index = mock_index
            mock_index.as_query_engine.return_value = mock_query_engine
            
            # Mock responses for different queries
            responses = [
                Mock(source_nodes=[Mock(node=Mock(text=f"Response {i}", node_id=f"node_{i}"), score=0.9)])
                for i in range(5)
            ]
            
            with patch('asyncio.get_event_loop') as mock_get_loop:
                mock_loop = AsyncMock()
                mock_get_loop.return_value = mock_loop
                mock_loop.run_in_executor.side_effect = responses
                
                # Execute multiple concurrent queries
                queries = [
                    "What is artificial intelligence?",
                    "How does machine learning work?",
                    "Explain deep learning concepts.",
                    "What are neural networks?",
                    "Describe computer vision applications."
                ]
                
                start_time = datetime.utcnow()
                tasks = [service.query(query) for query in queries]
                results = await asyncio.gather(*tasks)
                end_time = datetime.utcnow()
                
                processing_time = (end_time - start_time).total_seconds()
                
                # Verify all queries completed
                assert len(results) == 5
                for result in results:
                    assert "response" in result
                    assert "source_nodes" in result
                    assert "metadata" in result
                
                # Concurrent processing should be efficient
                assert processing_time < 10.0  # Should complete within 10 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])