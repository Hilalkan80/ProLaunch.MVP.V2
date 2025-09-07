"""
Unit tests for LlamaIndex configuration management.

Tests the configuration loading, validation, and environment variable handling
for the LlamaIndex integration.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from dataclasses import asdict

from src.ai.llama_config import (
    LlamaIndexConfig, LlamaIndexConfigManager, llama_config_manager
)


class TestLlamaIndexConfig:
    """Test LlamaIndexConfig dataclass."""
    
    def test_default_config_values(self):
        """Test default configuration values."""
        config = LlamaIndexConfig(
            anthropic_api_key="test_key",
            openai_api_key="test_openai_key"
        )
        
        assert config.anthropic_model == "claude-3-5-sonnet-20241022"
        assert config.anthropic_max_tokens == 4096
        assert config.anthropic_temperature == 0.7
        assert config.openai_embedding_model == "text-embedding-3-small"
        assert config.openai_embedding_dimensions == 1536
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.context_window == 100000
        assert config.max_workers == 5
    
    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = LlamaIndexConfig(
            anthropic_api_key="custom_key",
            openai_api_key="custom_openai_key",
            anthropic_temperature=0.5,
            chunk_size=1024,
            max_workers=10
        )
        
        assert config.anthropic_api_key == "custom_key"
        assert config.anthropic_temperature == 0.5
        assert config.chunk_size == 1024
        assert config.max_workers == 10


class TestLlamaIndexConfigManager:
    """Test LlamaIndexConfigManager class."""
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_anthropic_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'ANTHROPIC_MODEL_CHAT': 'claude-3-opus-20240229',
        'ANTHROPIC_MAX_TOKENS': '8192',
        'ANTHROPIC_TEMPERATURE': '0.1',
        'OPENAI_EMBEDDING_MODEL': 'text-embedding-ada-002',
        'OPENAI_EMBEDDING_DIMENSIONS': '1024',
        'VECTOR_STORE_HOST': 'test_host',
        'VECTOR_STORE_PORT': '5433',
        'LLAMA_CHUNK_SIZE': '256',
        'LLAMA_CHUNK_OVERLAP': '25',
        'LLAMA_MAX_WORKERS': '8'
    })
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables."""
        manager = LlamaIndexConfigManager()
        config = manager.get_config()
        
        assert config.anthropic_api_key == 'test_anthropic_key'
        assert config.openai_api_key == 'test_openai_key'
        assert config.anthropic_model == 'claude-3-opus-20240229'
        assert config.anthropic_max_tokens == 8192
        assert config.anthropic_temperature == 0.1
        assert config.openai_embedding_model == 'text-embedding-ada-002'
        assert config.openai_embedding_dimensions == 1024
        assert config.vector_store_host == 'test_host'
        assert config.vector_store_port == 5433
        assert config.chunk_size == 256
        assert config.chunk_overlap == 25
        assert config.max_workers == 8
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key'
    }, clear=True)
    def test_load_config_defaults_when_env_missing(self):
        """Test default values when environment variables are missing."""
        manager = LlamaIndexConfigManager()
        config = manager.get_config()
        
        # Should use defaults for missing env vars
        assert config.anthropic_model == "claude-3-5-sonnet-20241022"
        assert config.anthropic_max_tokens == 4096
        assert config.openai_embedding_model == "text-embedding-3-small"
        assert config.vector_store_host == "localhost"
        assert config.vector_store_port == 5432
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validation_missing_api_keys(self):
        """Test validation fails when API keys are missing."""
        with pytest.raises(ValueError) as exc_info:
            LlamaIndexConfigManager()
        
        error_message = str(exc_info.value)
        assert "ANTHROPIC_API_KEY is required" in error_message
        assert "OPENAI_API_KEY is required" in error_message
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'LLAMA_CHUNK_SIZE': '0'  # Invalid chunk size
    })
    def test_validation_invalid_chunk_size(self):
        """Test validation fails for invalid chunk size."""
        with pytest.raises(ValueError) as exc_info:
            LlamaIndexConfigManager()
        
        assert "Chunk size must be positive" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'LLAMA_CHUNK_SIZE': '512',
        'LLAMA_CHUNK_OVERLAP': '600'  # Overlap greater than chunk size
    })
    def test_validation_invalid_chunk_overlap(self):
        """Test validation fails for invalid chunk overlap."""
        with pytest.raises(ValueError) as exc_info:
            LlamaIndexConfigManager()
        
        assert "Chunk overlap must be less than chunk size" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'VECTOR_STORE_DIMENSION': '-100'  # Invalid dimension
    })
    def test_validation_invalid_vector_dimension(self):
        """Test validation fails for invalid vector dimension."""
        with pytest.raises(ValueError) as exc_info:
            LlamaIndexConfigManager()
        
        assert "Vector store dimension must be positive" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'valid_key',
        'OPENAI_API_KEY': 'valid_openai_key'
    })
    def test_get_llm_config(self):
        """Test getting LLM-specific configuration."""
        manager = LlamaIndexConfigManager()
        llm_config = manager.get_llm_config()
        
        expected_keys = {'model', 'api_key', 'max_tokens', 'temperature', 'timeout'}
        assert set(llm_config.keys()) == expected_keys
        assert llm_config['api_key'] == 'valid_key'
        assert llm_config['model'] == "claude-3-5-sonnet-20241022"
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'valid_key',
        'OPENAI_API_KEY': 'valid_openai_key'
    })
    def test_get_embedding_config(self):
        """Test getting embedding-specific configuration."""
        manager = LlamaIndexConfigManager()
        embed_config = manager.get_embedding_config()
        
        expected_keys = {'model_name', 'api_key', 'dimensions', 'max_retries', 'timeout'}
        assert set(embed_config.keys()) == expected_keys
        assert embed_config['api_key'] == 'valid_openai_key'
        assert embed_config['model_name'] == "text-embedding-3-small"
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'valid_key',
        'OPENAI_API_KEY': 'valid_openai_key'
    })
    def test_get_vector_store_config(self):
        """Test getting vector store configuration."""
        manager = LlamaIndexConfigManager()
        vector_config = manager.get_vector_store_config()
        
        expected_keys = {'host', 'port', 'database', 'user', 'password', 'table_name', 'embed_dim'}
        assert set(vector_config.keys()) == expected_keys
        assert vector_config['host'] == 'localhost'
        assert vector_config['port'] == 5432
        assert vector_config['database'] == 'prolaunch'
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'valid_key',
        'OPENAI_API_KEY': 'valid_openai_key'
    })
    def test_get_service_context_config(self):
        """Test getting service context configuration."""
        manager = LlamaIndexConfigManager()
        context_config = manager.get_service_context_config()
        
        expected_keys = {'chunk_size', 'chunk_overlap', 'context_window', 'num_output'}
        assert set(context_config.keys()) == expected_keys
        assert context_config['chunk_size'] == 512
        assert context_config['chunk_overlap'] == 50
        assert context_config['context_window'] == 100000
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'LLAMA_ENABLE_CACHING': 'false',
        'LLAMA_DEBUG_LOGGING': 'true'
    })
    def test_boolean_env_var_parsing(self):
        """Test boolean environment variable parsing."""
        manager = LlamaIndexConfigManager()
        config = manager.get_config()
        
        assert config.enable_caching is False
        assert config.enable_debug_logging is True
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'LLAMA_RETRY_DELAY': '2.5',
        'LLAMA_RETRY_BACKOFF_FACTOR': '1.5'
    })
    def test_float_env_var_parsing(self):
        """Test float environment variable parsing."""
        manager = LlamaIndexConfigManager()
        config = manager.get_config()
        
        assert config.retry_delay == 2.5
        assert config.retry_backoff_factor == 1.5


class TestSingletonBehavior:
    """Test singleton behavior of config manager."""
    
    def test_singleton_instance(self):
        """Test that llama_config_manager is a singleton."""
        # Import the singleton instance
        from src.ai.llama_config import llama_config_manager
        
        # Should always return the same instance
        manager1 = llama_config_manager
        manager2 = llama_config_manager
        
        assert manager1 is manager2
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'singleton_test_key',
        'OPENAI_API_KEY': 'singleton_openai_key'
    })
    def test_config_consistency(self):
        """Test that configuration remains consistent across calls."""
        from src.ai.llama_config import llama_config_manager
        
        config1 = llama_config_manager.get_config()
        config2 = llama_config_manager.get_config()
        
        # Should return the same config object
        assert config1 is config2
        assert config1.anthropic_api_key == config2.anthropic_api_key


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'ANTHROPIC_MAX_TOKENS': 'not_a_number'
    })
    def test_invalid_integer_env_var(self):
        """Test handling of invalid integer environment variables."""
        with pytest.raises(ValueError):
            LlamaIndexConfigManager()
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'ANTHROPIC_TEMPERATURE': 'not_a_float'
    })
    def test_invalid_float_env_var(self):
        """Test handling of invalid float environment variables."""
        with pytest.raises(ValueError):
            LlamaIndexConfigManager()
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': '   ',  # Whitespace only
        'OPENAI_API_KEY': 'test_openai_key'
    })
    def test_whitespace_api_key(self):
        """Test handling of whitespace-only API keys."""
        with pytest.raises(ValueError) as exc_info:
            LlamaIndexConfigManager()
        
        assert "ANTHROPIC_API_KEY is required" in str(exc_info.value)
    
    @patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key',
        'LLAMA_MAX_WORKERS': '0'
    })
    def test_zero_max_workers(self):
        """Test configuration with zero max workers."""
        # This should be valid, though perhaps not practical
        manager = LlamaIndexConfigManager()
        config = manager.get_config()
        
        assert config.max_workers == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])