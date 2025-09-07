"""
AI Module - LlamaIndex Integration with Claude and OpenAI

This module provides AI capabilities through LlamaIndex with:
- Claude 3.7 Sonnet as the primary LLM
- OpenAI text-embedding-3-small for embeddings
- PostgreSQL with pgvector for vector storage
- Context management system integration
- PromptLoader with MCP integrations for dynamic prompt management
"""

from .llama_config import llama_config_manager, LlamaIndexConfig
from .llama_service import llama_service, LlamaIndexService
from .embedding_service import EmbeddingService
from .context.manager import ContextManager
from .prompt_loader import (
    PromptLoader,
    PromptType,
    PromptMetadata,
    TokenBudget,
    TokenBudgetStrategy,
    get_prompt_loader
)

__all__ = [
    'llama_config_manager',
    'LlamaIndexConfig',
    'llama_service',
    'LlamaIndexService',
    'EmbeddingService',
    'ContextManager',
    'PromptLoader',
    'PromptType',
    'PromptMetadata',
    'TokenBudget',
    'TokenBudgetStrategy',
    'get_prompt_loader',
]

# Module version
__version__ = '1.1.0'