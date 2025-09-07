"""
LlamaIndex Configuration Module

This module manages the configuration for LlamaIndex with Claude 3.7 Sonnet as the primary LLM
and OpenAI text-embedding-3-small for embeddings.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LlamaIndexConfig:
    """Configuration for LlamaIndex integration"""
    
    # Required Configuration (no defaults)
    anthropic_api_key: str
    openai_api_key: str
    
    # Claude Configuration
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_max_tokens: int = 4096
    anthropic_temperature: float = 0.7
    anthropic_timeout: int = 60
    
    # OpenAI Configuration
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    openai_max_retries: int = 3
    openai_timeout: int = 30
    
    # Vector Store Configuration
    vector_store_type: str = "postgres"
    vector_store_host: str = "localhost"
    vector_store_port: int = 5432
    vector_store_database: str = "prolaunch"
    vector_store_user: str = "postgres"
    vector_store_password: Optional[str] = None
    vector_store_table_name: str = "embeddings"
    vector_store_dimension: int = 1536
    
    # Context Configuration
    chunk_size: int = 512
    chunk_overlap: int = 50
    context_window: int = 100000  # Claude 3 supports up to 100k tokens
    num_output: int = 4096
    
    # Performance Configuration
    enable_caching: bool = True
    cache_ttl: int = 3600
    batch_size: int = 10
    max_workers: int = 5
    
    # Retry Configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    
    # Logging Configuration
    enable_debug_logging: bool = False
    log_level: str = "INFO"


class LlamaIndexConfigManager:
    """Manager for LlamaIndex configuration"""
    
    def __init__(self):
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> LlamaIndexConfig:
        """Load configuration from environment variables"""
        return LlamaIndexConfig(
            # Claude Configuration
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            anthropic_model=os.getenv("ANTHROPIC_MODEL_CHAT", "claude-3-5-sonnet-20241022"),
            anthropic_max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "4096")),
            anthropic_temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
            anthropic_timeout=int(os.getenv("ANTHROPIC_TIMEOUT", "60")),
            
            # OpenAI Configuration
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            openai_embedding_dimensions=int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536")),
            openai_max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
            openai_timeout=int(os.getenv("OPENAI_TIMEOUT", "30")),
            
            # Vector Store Configuration
            vector_store_type=os.getenv("VECTOR_STORE_TYPE", "postgres"),
            vector_store_host=os.getenv("VECTOR_STORE_HOST", "localhost"),
            vector_store_port=int(os.getenv("VECTOR_STORE_PORT", "5432")),
            vector_store_database=os.getenv("VECTOR_STORE_DATABASE", "prolaunch"),
            vector_store_user=os.getenv("VECTOR_STORE_USER", "postgres"),
            vector_store_password=os.getenv("VECTOR_STORE_PASSWORD"),
            vector_store_table_name=os.getenv("VECTOR_STORE_TABLE_NAME", "embeddings"),
            vector_store_dimension=int(os.getenv("VECTOR_STORE_DIMENSION", "1536")),
            
            # Context Configuration
            chunk_size=int(os.getenv("LLAMA_CHUNK_SIZE", "512")),
            chunk_overlap=int(os.getenv("LLAMA_CHUNK_OVERLAP", "50")),
            context_window=int(os.getenv("LLAMA_CONTEXT_WINDOW", "100000")),
            num_output=int(os.getenv("LLAMA_NUM_OUTPUT", "4096")),
            
            # Performance Configuration
            enable_caching=os.getenv("LLAMA_ENABLE_CACHING", "true").lower() == "true",
            cache_ttl=int(os.getenv("LLAMA_CACHE_TTL", "3600")),
            batch_size=int(os.getenv("LLAMA_BATCH_SIZE", "10")),
            max_workers=int(os.getenv("LLAMA_MAX_WORKERS", "5")),
            
            # Retry Configuration
            max_retries=int(os.getenv("LLAMA_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("LLAMA_RETRY_DELAY", "1.0")),
            retry_backoff_factor=float(os.getenv("LLAMA_RETRY_BACKOFF_FACTOR", "2.0")),
            
            # Logging Configuration
            enable_debug_logging=os.getenv("LLAMA_DEBUG_LOGGING", "false").lower() == "true",
            log_level=os.getenv("LLAMA_LOG_LEVEL", "INFO"),
        )
    
    def _validate_config(self) -> None:
        """Validate the configuration"""
        errors = []
        
        if not self.config.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required")
        
        if not self.config.openai_api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if self.config.chunk_size <= 0:
            errors.append("Chunk size must be positive")
        
        if self.config.chunk_overlap >= self.config.chunk_size:
            errors.append("Chunk overlap must be less than chunk size")
        
        if self.config.vector_store_dimension <= 0:
            errors.append("Vector store dimension must be positive")
        
        if errors:
            error_msg = "Configuration validation failed: " + "; ".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("LlamaIndex configuration validated successfully")
    
    def get_config(self) -> LlamaIndexConfig:
        """Get the current configuration"""
        return self.config
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM-specific configuration"""
        return {
            "model": self.config.anthropic_model,
            "api_key": self.config.anthropic_api_key,
            "max_tokens": self.config.anthropic_max_tokens,
            "temperature": self.config.anthropic_temperature,
            "timeout": self.config.anthropic_timeout,
        }
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """Get embedding-specific configuration"""
        return {
            "model_name": self.config.openai_embedding_model,
            "api_key": self.config.openai_api_key,
            "dimensions": self.config.openai_embedding_dimensions,
            "max_retries": self.config.openai_max_retries,
            "timeout": self.config.openai_timeout,
        }
    
    def get_vector_store_config(self) -> Dict[str, Any]:
        """Get vector store configuration"""
        return {
            "host": self.config.vector_store_host,
            "port": self.config.vector_store_port,
            "database": self.config.vector_store_database,
            "user": self.config.vector_store_user,
            "password": self.config.vector_store_password,
            "table_name": self.config.vector_store_table_name,
            "embed_dim": self.config.vector_store_dimension,
        }
    
    def get_service_context_config(self) -> Dict[str, Any]:
        """Get service context configuration"""
        return {
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "context_window": self.config.context_window,
            "num_output": self.config.num_output,
        }


# Singleton instance
llama_config_manager = LlamaIndexConfigManager()