"""
Performance tests for AI services.

Tests the performance characteristics of LlamaIndex, Prompt Loader,
and Citation services under various load conditions and data volumes.
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime, timedelta
from uuid import uuid4
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
from pathlib import Path

from src.ai.llama_service import LlamaIndexService
from src.ai.prompt_loader import PromptLoader, PromptType
from src.services.citation_service import CitationService, CitationCreate
from src.models.citation import Citation, SourceType, VerificationStatus


class PerformanceMetrics:
    """Helper class to collect and analyze performance metrics."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.operation_times = []
        self.memory_usage = []
        self.errors = []
    
    def start_timing(self):
        """Start timing the operation."""
        self.start_time = time.perf_counter()
    
    def end_timing(self):
        """End timing the operation."""
        self.end_time = time.perf_counter()
        return self.total_time()
    
    def total_time(self) -> float:
        """Get total elapsed time."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    def add_operation_time(self, duration: float):
        """Add individual operation time."""
        self.operation_times.append(duration)
    
    def add_error(self, error: Exception):
        """Add error to tracking."""
        self.errors.append(str(error))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.operation_times:
            return {"error": "No operation times recorded"}
        
        return {
            "test_name": self.test_name,
            "total_operations": len(self.operation_times),
            "total_time": self.total_time(),
            "average_time": statistics.mean(self.operation_times),
            "median_time": statistics.median(self.operation_times),
            "min_time": min(self.operation_times),
            "max_time": max(self.operation_times),
            "std_deviation": statistics.stdev(self.operation_times) if len(self.operation_times) > 1 else 0,
            "throughput_ops_per_sec": len(self.operation_times) / self.total_time() if self.total_time() > 0 else 0,
            "error_count": len(self.errors),
            "error_rate": len(self.errors) / len(self.operation_times) if self.operation_times else 0
        }


@pytest.fixture
def performance_prompt_loader():
    """Create PromptLoader for performance testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        prompts_dir = Path(temp_dir)
        
        # Create test prompt structure
        (prompts_dir / "system").mkdir()
        (prompts_dir / "milestones").mkdir()
        (prompts_dir / "chat").mkdir()
        
        # Create various sized prompts for performance testing
        prompt_sizes = {
            "small": "This is a small prompt with minimal content for {variable}.",
            "medium": "This is a medium-sized prompt " * 50 + " with variable {variable} and more content.",
            "large": "This is a large prompt " * 500 + " with extensive content for {variable} " * 100,
            "xlarge": "This is an extra-large prompt " * 2000 + " for comprehensive testing with {variable}."
        }
        
        for size, content in prompt_sizes.items():
            for category in ["system", "milestones", "chat"]:
                prompt_file = prompts_dir / category / f"{size}_prompt.md"
                prompt_file.write_text(f"""---
version: "1.0.0"
priority: 5
tags: ["performance", "{size}"]
---

# {size.title()} Performance Test Prompt

{content}
""")
        
        # Mock MCP services
        with patch('src.ai.prompt_loader.RefMCP'), \
             patch('src.ai.prompt_loader.MemoryBankMCP'), \
             patch('src.ai.prompt_loader.TokenOptimizer'):
            
            loader = PromptLoader(prompts_dir=str(prompts_dir))
            yield loader


@pytest.fixture
def performance_citation_service():
    """Create CitationService for performance testing."""
    # Create in-memory database for performance testing
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.models.base import Base
    
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    service = CitationService(db=db)
    
    yield service
    
    db.close()


class TestLlamaIndexPerformance:
    """Performance tests for LlamaIndex service."""
    
    @pytest.mark.asyncio
    async def test_document_indexing_performance(self):
        """Test document indexing performance with varying document sizes."""
        
        # Mock LlamaIndex components
        with patch('src.ai.llama_service.llama_config_manager') as mock_config, \
             patch('src.ai.llama_service.Anthropic') as mock_anthropic, \
             patch('src.ai.llama_service.OpenAIEmbedding') as mock_embedding, \
             patch('src.ai.llama_service.PGVectorStore') as mock_vector:
            
            # Setup mock configuration
            from src.ai.llama_config import LlamaIndexConfig
            mock_config.get_config.return_value = LlamaIndexConfig(
                anthropic_api_key="test_key",
                openai_api_key="test_openai_key"
            )
            mock_config.get_llm_config.return_value = {"model": "claude-3", "api_key": "test"}
            mock_config.get_embedding_config.return_value = {"model_name": "embedding", "api_key": "test"}
            mock_config.get_vector_store_config.return_value = {"database": "test"}
            mock_config.get_service_context_config.return_value = {"chunk_size": 512}
            
            service = LlamaIndexService()
            
            # Test document indexing performance with different document sizes
            document_sizes = [100, 500, 1000, 5000, 10000]  # Characters
            metrics = PerformanceMetrics("document_indexing")
            
            metrics.start_timing()
            
            for size in document_sizes:
                doc_content = "Performance test document content. " * (size // 40)
                documents = [{"text": doc_content, "metadata": {"size": size}}]
                
                start_time = time.perf_counter()
                try:
                    # Mock the document indexing process
                    with patch.object(service, 'create_index') as mock_create:
                        mock_create.return_value = Mock()
                        await service.add_documents(documents)
                    
                    duration = time.perf_counter() - start_time
                    metrics.add_operation_time(duration)
                    
                except Exception as e:
                    metrics.add_error(e)
            
            metrics.end_timing()
            stats = metrics.get_statistics()
            
            # Performance assertions
            assert stats["average_time"] < 1.0  # Should average under 1 second
            assert stats["error_rate"] == 0  # No errors should occur
            assert stats["throughput_ops_per_sec"] > 1  # At least 1 operation per second
            
            print(f"Document Indexing Performance: {stats}")
    
    @pytest.mark.asyncio
    async def test_query_performance_under_load(self):
        """Test query performance under concurrent load."""
        
        with patch('src.ai.llama_service.llama_config_manager') as mock_config, \
             patch('src.ai.llama_service.Anthropic'), \
             patch('src.ai.llama_service.OpenAIEmbedding'), \
             patch('src.ai.llama_service.PGVectorStore'):
            
            from src.ai.llama_config import LlamaIndexConfig
            mock_config.get_config.return_value = LlamaIndexConfig(
                anthropic_api_key="test_key",
                openai_api_key="test_openai_key"
            )
            mock_config.get_llm_config.return_value = {"model": "claude-3", "api_key": "test"}
            mock_config.get_embedding_config.return_value = {"model_name": "embedding", "api_key": "test"}
            mock_config.get_vector_store_config.return_value = {"database": "test"}
            mock_config.get_service_context_config.return_value = {"chunk_size": 512}
            
            service = LlamaIndexService()
            
            # Setup mock index
            service.index = Mock()
            service.index.as_query_engine.return_value = Mock()
            
            # Mock query response
            mock_response = Mock()
            mock_response.source_nodes = []
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_event_loop = AsyncMock()
                mock_loop.return_value = mock_event_loop
                mock_event_loop.run_in_executor.return_value = mock_response
                
                # Test concurrent queries
                queries = [
                    "What is artificial intelligence?",
                    "How does machine learning work?",
                    "Explain deep learning concepts.",
                    "What are the benefits of AI in business?",
                    "How to implement AI solutions?"
                ] * 4  # 20 total queries
                
                metrics = PerformanceMetrics("concurrent_queries")
                metrics.start_timing()
                
                # Execute queries concurrently
                async def execute_query(query):
                    start_time = time.perf_counter()
                    try:
                        await service.query(query)
                        duration = time.perf_counter() - start_time
                        metrics.add_operation_time(duration)
                    except Exception as e:
                        metrics.add_error(e)
                
                await asyncio.gather(*[execute_query(q) for q in queries])
                
                metrics.end_timing()
                stats = metrics.get_statistics()
                
                # Performance assertions
                assert stats["average_time"] < 2.0  # Average query under 2 seconds
                assert stats["error_rate"] < 0.1  # Less than 10% error rate
                assert stats["throughput_ops_per_sec"] > 5  # At least 5 queries per second
                
                print(f"Concurrent Query Performance: {stats}")
    
    @pytest.mark.asyncio
    async def test_embedding_generation_performance(self):
        """Test embedding generation performance with batch processing."""
        
        with patch('src.ai.llama_service.llama_config_manager') as mock_config, \
             patch('src.ai.llama_service.OpenAIEmbedding') as mock_embedding_class:
            
            from src.ai.llama_config import LlamaIndexConfig
            mock_config.get_config.return_value = LlamaIndexConfig(
                anthropic_api_key="test_key",
                openai_api_key="test_openai_key"
            )
            mock_config.get_embedding_config.return_value = {"model_name": "embedding", "api_key": "test"}
            
            # Mock embedding model
            mock_embedding_model = Mock()
            mock_embedding_class.return_value = mock_embedding_model
            
            service = LlamaIndexService()
            service.embed_model = mock_embedding_model
            
            # Test batch embedding generation
            batch_sizes = [1, 5, 10, 20, 50, 100]
            metrics = PerformanceMetrics("embedding_generation")
            
            metrics.start_timing()
            
            for batch_size in batch_sizes:
                texts = [f"Test text {i} for embedding generation." for i in range(batch_size)]
                mock_embeddings = [[0.1] * 1536] * batch_size  # Mock embeddings
                
                with patch('asyncio.get_event_loop') as mock_loop:
                    mock_event_loop = AsyncMock()
                    mock_loop.return_value = mock_event_loop
                    mock_event_loop.run_in_executor.return_value = mock_embeddings
                    
                    start_time = time.perf_counter()
                    try:
                        result = await service.get_embeddings(texts)
                        assert len(result) == batch_size
                        
                        duration = time.perf_counter() - start_time
                        metrics.add_operation_time(duration)
                        
                    except Exception as e:
                        metrics.add_error(e)
            
            metrics.end_timing()
            stats = metrics.get_statistics()
            
            # Performance assertions
            assert stats["average_time"] < 3.0  # Average batch processing under 3 seconds
            assert stats["error_rate"] == 0  # No errors
            
            print(f"Embedding Generation Performance: {stats}")


class TestPromptLoaderPerformance:
    """Performance tests for Prompt Loader."""
    
    @pytest.mark.asyncio
    async def test_prompt_loading_performance(self, performance_prompt_loader):
        """Test prompt loading performance with different prompt sizes."""
        
        loader = performance_prompt_loader
        
        # Mock MCP services
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        prompt_sizes = ["small", "medium", "large", "xlarge"]
        metrics = PerformanceMetrics("prompt_loading")
        
        metrics.start_timing()
        
        for size in prompt_sizes:
            start_time = time.perf_counter()
            try:
                result = await loader.load_prompt(
                    prompt_name=f"{size}_prompt",
                    prompt_type=PromptType.SYSTEM,
                    variables={"variable": "test_value"},
                    inject_context=False,
                    optimize=False
                )
                
                assert "prompt" in result
                duration = time.perf_counter() - start_time
                metrics.add_operation_time(duration)
                
            except Exception as e:
                metrics.add_error(e)
        
        metrics.end_timing()
        stats = metrics.get_statistics()
        
        # Performance assertions
        assert stats["average_time"] < 0.5  # Average loading under 0.5 seconds
        assert stats["error_rate"] == 0  # No errors
        
        print(f"Prompt Loading Performance: {stats}")
    
    @pytest.mark.asyncio
    async def test_prompt_chain_performance(self, performance_prompt_loader):
        """Test prompt chain loading performance."""
        
        loader = performance_prompt_loader
        
        # Mock MCP services
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.memory_bank.store_memory = AsyncMock(return_value=True)
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        loader.ref_mcp.deduplicate_content = AsyncMock(return_value=["optimized"] * 3)
        
        # Test different chain lengths
        chain_lengths = [2, 3, 5, 7, 10]
        metrics = PerformanceMetrics("prompt_chain_loading")
        
        metrics.start_timing()
        
        for chain_length in chain_lengths:
            prompt_names = [f"medium_prompt"] * chain_length
            
            start_time = time.perf_counter()
            try:
                results = await loader.load_prompt_chain(
                    prompt_names=prompt_names,
                    shared_context={"variable": "chain_test"},
                    optimize_chain=True,
                    max_tokens=2000
                )
                
                assert len(results) == chain_length
                duration = time.perf_counter() - start_time
                metrics.add_operation_time(duration)
                
            except Exception as e:
                metrics.add_error(e)
        
        metrics.end_timing()
        stats = metrics.get_statistics()
        
        # Performance assertions
        assert stats["average_time"] < 5.0  # Chain loading under 5 seconds
        assert stats["error_rate"] == 0  # No errors
        
        print(f"Prompt Chain Loading Performance: {stats}")
    
    @pytest.mark.asyncio
    async def test_concurrent_prompt_loading(self, performance_prompt_loader):
        """Test concurrent prompt loading performance."""
        
        loader = performance_prompt_loader
        
        # Mock MCP services
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        # Test concurrent loading
        concurrent_loads = 20
        metrics = PerformanceMetrics("concurrent_prompt_loading")
        
        async def load_prompt_with_timing(prompt_name, index):
            start_time = time.perf_counter()
            try:
                result = await loader.load_prompt(
                    prompt_name=prompt_name,
                    variables={"variable": f"concurrent_test_{index}"},
                    inject_context=True,
                    optimize=False
                )
                duration = time.perf_counter() - start_time
                metrics.add_operation_time(duration)
                return result
            except Exception as e:
                metrics.add_error(e)
                return None
        
        metrics.start_timing()
        
        # Execute concurrent loads
        tasks = [
            load_prompt_with_timing("medium_prompt", i)
            for i in range(concurrent_loads)
        ]
        
        results = await asyncio.gather(*tasks)
        successful_results = [r for r in results if r is not None]
        
        metrics.end_timing()
        stats = metrics.get_statistics()
        
        # Performance assertions
        assert len(successful_results) >= concurrent_loads * 0.9  # 90% success rate
        assert stats["average_time"] < 2.0  # Average load time under 2 seconds
        assert stats["throughput_ops_per_sec"] > 5  # At least 5 loads per second
        
        print(f"Concurrent Prompt Loading Performance: {stats}")
    
    @pytest.mark.asyncio
    async def test_cache_performance_impact(self, performance_prompt_loader):
        """Test cache performance impact on prompt loading."""
        
        loader = performance_prompt_loader
        loader.cache_enabled = True
        
        # Mock MCP services
        loader.memory_bank.search_memories = AsyncMock(return_value=[])
        loader.ref_mcp.extract_references = AsyncMock(return_value={})
        
        prompt_name = "medium_prompt"
        variables = {"variable": "cache_test"}
        
        metrics_no_cache = PerformanceMetrics("no_cache")
        metrics_with_cache = PerformanceMetrics("with_cache")
        
        # Test without cache (first load)
        metrics_no_cache.start_timing()
        
        for i in range(10):
            start_time = time.perf_counter()
            result = await loader.load_prompt(
                prompt_name=prompt_name,
                variables={**variables, "index": i},  # Different variables to prevent caching
                inject_context=False,
                optimize=False
            )
            duration = time.perf_counter() - start_time
            metrics_no_cache.add_operation_time(duration)
        
        metrics_no_cache.end_timing()
        
        # Test with cache (repeated loads with same parameters)
        metrics_with_cache.start_timing()
        
        for i in range(10):
            start_time = time.perf_counter()
            result = await loader.load_prompt(
                prompt_name=prompt_name,
                variables=variables,  # Same variables for caching
                inject_context=False,
                optimize=False
            )
            duration = time.perf_counter() - start_time
            metrics_with_cache.add_operation_time(duration)
        
        metrics_with_cache.end_timing()
        
        no_cache_stats = metrics_no_cache.get_statistics()
        cache_stats = metrics_with_cache.get_statistics()
        
        # Cache should provide significant performance improvement
        cache_improvement = (no_cache_stats["average_time"] - cache_stats["average_time"]) / no_cache_stats["average_time"]
        
        assert cache_improvement > 0.2  # At least 20% improvement with caching
        assert cache_stats["average_time"] < no_cache_stats["average_time"]
        
        print(f"No Cache Performance: {no_cache_stats}")
        print(f"With Cache Performance: {cache_stats}")
        print(f"Cache Improvement: {cache_improvement:.2%}")


class TestCitationServicePerformance:
    """Performance tests for Citation Service."""
    
    @pytest.mark.asyncio
    async def test_citation_creation_performance(self, performance_citation_service):
        """Test citation creation performance with varying data sizes."""
        
        service = performance_citation_service
        user_id = uuid4()
        
        # Test different citation data sizes
        citation_templates = [
            {
                "size": "minimal",
                "data": {
                    "title": "Minimal Citation",
                    "sourceType": SourceType.WEB
                }
            },
            {
                "size": "standard",
                "data": {
                    "title": "Standard Citation with Authors and URL",
                    "url": "https://example.com/standard",
                    "authors": ["Author One", "Author Two"],
                    "sourceType": SourceType.ACADEMIC,
                    "excerpt": "This is a standard citation with moderate metadata."
                }
            },
            {
                "size": "comprehensive",
                "data": {
                    "title": "Comprehensive Citation with Extensive Metadata",
                    "url": "https://example.com/comprehensive",
                    "authors": ["Dr. First Author", "Prof. Second Author", "Dr. Third Author"],
                    "sourceType": SourceType.ACADEMIC,
                    "excerpt": "This is a comprehensive citation " * 20,
                    "metadata": {
                        "journal": "Performance Testing Journal",
                        "volume": "42",
                        "issue": "3",
                        "pages": "123-145",
                        "doi": "10.1234/ptj.2024.performance",
                        "keywords": ["performance", "testing", "citations", "metadata", "research"]
                    }
                }
            }
        ]
        
        metrics = PerformanceMetrics("citation_creation")
        metrics.start_timing()
        
        # Test citation creation performance
        for template in citation_templates * 5:  # 15 total citations
            citation_data = CitationCreate(**template["data"])
            
            start_time = time.perf_counter()
            try:
                citation = await service.create_citation(
                    citation_data=citation_data,
                    user_id=user_id,
                    auto_verify=False
                )
                
                assert citation.id is not None
                duration = time.perf_counter() - start_time
                metrics.add_operation_time(duration)
                
            except Exception as e:
                metrics.add_error(e)
        
        metrics.end_timing()
        stats = metrics.get_statistics()
        
        # Performance assertions
        assert stats["average_time"] < 0.1  # Average creation under 100ms
        assert stats["error_rate"] == 0  # No errors
        assert stats["throughput_ops_per_sec"] > 20  # At least 20 citations per second
        
        print(f"Citation Creation Performance: {stats}")
    
    @pytest.mark.asyncio
    async def test_citation_search_performance(self, performance_citation_service):
        """Test citation search performance with large datasets."""
        
        service = performance_citation_service
        user_id = uuid4()
        
        # Create large dataset for search testing
        dataset_size = 1000
        citations = []
        
        # Batch create citations for performance testing
        creation_start = time.perf_counter()
        
        for i in range(dataset_size):
            citation_data = CitationCreate(
                title=f"Performance Test Citation {i}",
                url=f"https://perf-test-{i}.example.com",
                authors=[f"Author {i}", f"Co-Author {i}"],
                sourceType=SourceType.WEB if i % 2 == 0 else SourceType.ACADEMIC,
                excerpt=f"Performance testing citation number {i} with searchable content and keywords.",
                metadata={
                    "category": f"category_{i % 10}",
                    "year": 2020 + (i % 5),
                    "keywords": [f"keyword_{i % 20}", "performance", "testing"]
                }
            )
            
            citation = await service.create_citation(
                citation_data=citation_data,
                user_id=user_id,
                auto_verify=False
            )
            citations.append(citation)
        
        creation_time = time.perf_counter() - creation_start
        print(f"Created {dataset_size} citations in {creation_time:.2f} seconds")
        
        # Test search performance
        from src.services.citation_service import CitationSearchParams
        
        search_scenarios = [
            CitationSearchParams(query="performance testing", limit=50),
            CitationSearchParams(source_types=[SourceType.ACADEMIC], limit=100),
            CitationSearchParams(query="keyword_5", limit=25),
            CitationSearchParams(min_quality_score=0.5, limit=200),
            CitationSearchParams(query="Citation", source_types=[SourceType.WEB], limit=75)
        ]
        
        metrics = PerformanceMetrics("citation_search")
        metrics.start_timing()
        
        for search_params in search_scenarios * 4:  # 20 total searches
            start_time = time.perf_counter()
            try:
                results, total_count = await service.search_citations(search_params)
                
                assert isinstance(results, list)
                assert total_count >= 0
                duration = time.perf_counter() - start_time
                metrics.add_operation_time(duration)
                
            except Exception as e:
                metrics.add_error(e)
        
        metrics.end_timing()
        stats = metrics.get_statistics()
        
        # Performance assertions
        assert stats["average_time"] < 2.0  # Average search under 2 seconds
        assert stats["error_rate"] == 0  # No search errors
        assert stats["throughput_ops_per_sec"] > 2  # At least 2 searches per second
        
        print(f"Citation Search Performance: {stats}")
    
    @pytest.mark.asyncio
    async def test_concurrent_citation_operations(self, performance_citation_service):
        """Test concurrent citation operations performance."""
        
        service = performance_citation_service
        user_ids = [uuid4() for _ in range(5)]  # Multiple users
        
        # Create base citations for operations
        base_citations = []
        for i in range(10):
            citation_data = CitationCreate(
                title=f"Concurrent Test Citation {i}",
                url=f"https://concurrent-{i}.example.com",
                sourceType=SourceType.WEB,
                excerpt=f"Citation for concurrent testing {i}"
            )
            
            citation = await service.create_citation(
                citation_data=citation_data,
                user_id=user_ids[0],
                auto_verify=False
            )
            base_citations.append(citation)
        
        # Define concurrent operations
        async def create_citation_operation(index):
            citation_data = CitationCreate(
                title=f"Concurrent Creation {index}",
                sourceType=SourceType.WEB,
                excerpt=f"Concurrently created citation {index}"
            )
            return await service.create_citation(
                citation_data=citation_data,
                user_id=user_ids[index % len(user_ids)],
                auto_verify=False
            )
        
        async def track_usage_operation(citation_id, index):
            return await service.track_usage(
                citation_id=citation_id,
                content_id=uuid4(),
                user_id=user_ids[index % len(user_ids)],
                content_type="research",
                position=1,
                context=f"Concurrent usage tracking {index}"
            )
        
        async def submit_feedback_operation(citation_id, index):
            from src.services.citation_service import AccuracyFeedback, MetricType, FeedbackType
            
            feedback = AccuracyFeedback(
                metric_type=MetricType.RELEVANCE,
                score=0.8 + (index * 0.01),
                feedback_type=FeedbackType.USER,
                comment=f"Concurrent feedback {index}"
            )
            
            return await service.submit_accuracy_feedback(
                citation_id=citation_id,
                feedback=feedback,
                user_id=user_ids[index % len(user_ids)]
            )
        
        # Execute concurrent operations
        metrics = PerformanceMetrics("concurrent_operations")
        metrics.start_timing()
        
        # Create mixed concurrent operations
        tasks = []
        
        # Creation tasks
        tasks.extend([create_citation_operation(i) for i in range(10)])
        
        # Usage tracking tasks
        for i in range(15):
            citation = base_citations[i % len(base_citations)]
            tasks.append(track_usage_operation(citation.id, i))
        
        # Feedback tasks
        for i in range(10):
            citation = base_citations[i % len(base_citations)]
            tasks.append(submit_feedback_operation(citation.id, i))
        
        # Execute all tasks concurrently
        start_time = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.perf_counter() - start_time
        
        # Analyze results
        successful_operations = [r for r in results if not isinstance(r, Exception)]
        failed_operations = [r for r in results if isinstance(r, Exception)]
        
        metrics.add_operation_time(total_duration)
        for error in failed_operations:
            metrics.add_error(error)
        
        metrics.end_timing()
        stats = metrics.get_statistics()
        
        # Performance assertions
        success_rate = len(successful_operations) / len(results)
        assert success_rate > 0.9  # At least 90% success rate
        assert total_duration < 20.0  # Complete within 20 seconds
        
        print(f"Concurrent Operations Performance: {stats}")
        print(f"Success Rate: {success_rate:.2%}")
        print(f"Total Operations: {len(results)}")
        print(f"Successful: {len(successful_operations)}")
        print(f"Failed: {len(failed_operations)}")
    
    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self, performance_citation_service):
        """Test bulk operations performance."""
        
        service = performance_citation_service
        user_id = uuid4()
        
        # Create citations for bulk operations
        citations = []
        batch_size = 50
        
        for i in range(batch_size):
            citation_data = CitationCreate(
                title=f"Bulk Test Citation {i}",
                url=f"https://bulk-{i}.example.com",
                sourceType=SourceType.WEB,
                excerpt=f"Citation for bulk testing {i}"
            )
            
            citation = await service.create_citation(
                citation_data=citation_data,
                user_id=user_id,
                auto_verify=False
            )
            citations.append(citation)
        
        citation_ids = [c.id for c in citations]
        
        # Test bulk verification performance
        metrics = PerformanceMetrics("bulk_verification")
        metrics.start_timing()
        
        # Mock successful verification
        with patch.object(service, 'verify_citation') as mock_verify:
            mock_verify.return_value = Mock(status="success")
            
            start_time = time.perf_counter()
            try:
                results = await service.batch_verify(citation_ids, user_id)
                duration = time.perf_counter() - start_time
                metrics.add_operation_time(duration)
                
                assert len(results) == batch_size
                
            except Exception as e:
                metrics.add_error(e)
        
        metrics.end_timing()
        stats = metrics.get_statistics()
        
        # Performance assertions
        assert stats["average_time"] < 10.0  # Bulk verification under 10 seconds
        assert stats["error_rate"] == 0  # No errors
        
        throughput = batch_size / stats["average_time"] if stats["average_time"] > 0 else 0
        assert throughput > 10  # At least 10 citations per second
        
        print(f"Bulk Operations Performance: {stats}")
        print(f"Bulk Verification Throughput: {throughput:.2f} citations/sec")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])