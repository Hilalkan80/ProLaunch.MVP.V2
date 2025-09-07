"""
PromptLoader System with MCP Integration and Token Budget Management

This module provides a robust prompt loading and management system with:
- Dynamic prompt loading from /prolaunch_prompts/ directory
- Integration with Ref MCP for optimization
- Memory Bank MCP integration for context injection
- Token budget management and compliance
- Caching and performance optimization
"""

import os
import re
import json
import yaml
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from functools import lru_cache

from ..services.mcp_integrations.ref_optimization import RefMCP
from ..services.mcp_integrations.memory_bank import MemoryBankMCP
from .context.token_optimizer import TokenOptimizer

logger = logging.getLogger(__name__)


class PromptType(Enum):
    """Enumeration of prompt types"""
    SYSTEM = "system"
    CHAT = "chat"
    MILESTONE = "milestones"
    STYLE = "style"
    CUSTOM = "custom"


class TokenBudgetStrategy(Enum):
    """Token budget allocation strategies"""
    PROPORTIONAL = "proportional"  # Allocate proportionally to content size
    PRIORITY_BASED = "priority_based"  # Allocate based on priority scores
    ADAPTIVE = "adaptive"  # Dynamically adjust based on usage patterns
    FIXED = "fixed"  # Fixed allocation per component


@dataclass
class PromptMetadata:
    """Metadata for a prompt template"""
    name: str
    type: PromptType
    version: str = "1.0.0"
    last_updated: Optional[datetime] = None
    author: Optional[str] = None
    description: Optional[str] = None
    token_estimate: int = 0
    priority: int = 5  # 1-10 scale, 10 being highest
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    cache_ttl: int = 3600  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            "name": self.name,
            "type": self.type.value,
            "version": self.version,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "author": self.author,
            "description": self.description,
            "token_estimate": self.token_estimate,
            "priority": self.priority,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "cache_ttl": self.cache_ttl
        }


@dataclass
class TokenBudget:
    """Token budget configuration and tracking"""
    total_budget: int = 8192  # Default token budget
    system_reserve: int = 1000  # Reserved for system prompts
    context_allocation: int = 3000  # For context injection
    prompt_allocation: int = 2000  # For prompt templates
    response_reserve: int = 2192  # Reserved for response
    
    current_usage: Dict[str, int] = field(default_factory=dict)
    
    def available_tokens(self) -> int:
        """Calculate available tokens"""
        used = sum(self.current_usage.values())
        return self.total_budget - used - self.response_reserve
    
    def allocate(self, category: str, tokens: int) -> bool:
        """Allocate tokens to a category"""
        available = self.available_tokens()
        if tokens <= available:
            self.current_usage[category] = self.current_usage.get(category, 0) + tokens
            return True
        return False
    
    def reset(self):
        """Reset current usage"""
        self.current_usage.clear()
    
    def get_allocation_for(self, category: str) -> int:
        """Get allocated budget for a category"""
        allocations = {
            "system": self.system_reserve,
            "context": self.context_allocation,
            "prompt": self.prompt_allocation,
            "response": self.response_reserve
        }
        return allocations.get(category, 0)


class PromptLoader:
    """
    Main PromptLoader class that manages prompt templates with MCP integration
    """
    
    def __init__(
        self,
        prompts_dir: str = "prolaunch_prompts",
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
        token_budget: Optional[TokenBudget] = None
    ):
        """
        Initialize PromptLoader
        
        Args:
            prompts_dir: Directory containing prompt templates
            cache_enabled: Enable caching
            cache_ttl: Cache time-to-live in seconds
            token_budget: Token budget configuration
        """
        self.prompts_dir = Path(prompts_dir)
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.token_budget = token_budget or TokenBudget()
        
        # Initialize MCP integrations
        self.ref_mcp = RefMCP()
        self.memory_bank = MemoryBankMCP()
        self.token_optimizer = TokenOptimizer()
        
        # Cache storage
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._prompt_registry: Dict[str, PromptMetadata] = {}
        
        # Load prompts on initialization
        self._load_prompt_registry()
        
        logger.info(f"PromptLoader initialized with prompts_dir: {self.prompts_dir}")
    
    def _load_prompt_registry(self):
        """Load and register all available prompts"""
        try:
            if not self.prompts_dir.exists():
                logger.warning(f"Prompts directory {self.prompts_dir} does not exist")
                return
            
            # Scan all prompt files
            for prompt_type in PromptType:
                type_dir = self.prompts_dir / prompt_type.value
                if type_dir.exists() and type_dir.is_dir():
                    for file_path in type_dir.glob("*"):
                        if file_path.suffix in [".md", ".txt", ".json", ".yaml"]:
                            self._register_prompt(file_path, prompt_type)
            
            logger.info(f"Loaded {len(self._prompt_registry)} prompts into registry")
            
        except Exception as e:
            logger.error(f"Error loading prompt registry: {e}")
    
    def _register_prompt(self, file_path: Path, prompt_type: PromptType):
        """Register a single prompt file"""
        try:
            # Extract metadata from file
            name = file_path.stem
            
            # Parse metadata from file header if available
            metadata = self._extract_metadata(file_path)
            
            # Create PromptMetadata object
            prompt_meta = PromptMetadata(
                name=name,
                type=prompt_type,
                version=metadata.get("version", "1.0.0"),
                last_updated=metadata.get("last_updated"),
                author=metadata.get("author"),
                description=metadata.get("description"),
                token_estimate=metadata.get("token_estimate", 0),
                priority=metadata.get("priority", 5),
                tags=metadata.get("tags", []),
                dependencies=metadata.get("dependencies", []),
                cache_ttl=metadata.get("cache_ttl", self.cache_ttl)
            )
            
            # Register prompt
            registry_key = f"{prompt_type.value}/{name}"
            self._prompt_registry[registry_key] = prompt_meta
            
            logger.debug(f"Registered prompt: {registry_key}")
            
        except Exception as e:
            logger.error(f"Error registering prompt {file_path}: {e}")
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from prompt file"""
        metadata = {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Look for metadata header (YAML front matter style)
            if content.startswith("---"):
                lines = content.split("\n")
                end_index = -1
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "---":
                        end_index = i
                        break
                
                if end_index > 0:
                    yaml_content = "\n".join(lines[1:end_index])
                    metadata = yaml.safe_load(yaml_content) or {}
            
            # Extract from markdown comments
            if file_path.suffix == ".md":
                # Look for _Last updated: YYYY-MM-DD_ pattern
                updated_match = re.search(r'_Last updated:\s*(\d{4}-\d{2}-\d{2})_', content)
                if updated_match:
                    metadata["last_updated"] = datetime.strptime(updated_match.group(1), "%Y-%m-%d")
                
                # Look for ## Purpose section
                purpose_match = re.search(r'## Purpose\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
                if purpose_match:
                    metadata["description"] = purpose_match.group(1).strip()
            
            # Estimate tokens (rough approximation)
            metadata["token_estimate"] = len(content) // 4
            
        except Exception as e:
            logger.warning(f"Could not extract metadata from {file_path}: {e}")
        
        return metadata
    
    async def load_prompt(
        self,
        prompt_name: str,
        prompt_type: Optional[PromptType] = None,
        variables: Optional[Dict[str, Any]] = None,
        inject_context: bool = True,
        optimize: bool = True,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Load a prompt template with optional context injection and optimization
        
        Args:
            prompt_name: Name of the prompt to load
            prompt_type: Type of prompt (will search all types if not specified)
            variables: Variables to interpolate into the prompt
            inject_context: Whether to inject context from Memory Bank
            optimize: Whether to optimize with Ref MCP
            max_tokens: Maximum token budget for this prompt
            
        Returns:
            Dictionary containing the loaded and processed prompt
        """
        try:
            # Reset token budget for this load
            self.token_budget.reset()
            
            # Find prompt in registry
            prompt_key = self._find_prompt_key(prompt_name, prompt_type)
            if not prompt_key:
                raise ValueError(f"Prompt '{prompt_name}' not found")
            
            # Check cache
            if self.cache_enabled:
                cached = self._get_cached(prompt_key)
                if cached:
                    logger.debug(f"Using cached prompt: {prompt_key}")
                    return cached
            
            # Load prompt content
            prompt_content = await self._load_prompt_content(prompt_key)
            
            # Interpolate variables
            if variables:
                prompt_content = self._interpolate_variables(prompt_content, variables)
            
            # Inject context from Memory Bank
            if inject_context:
                context = await self._inject_context(prompt_name, prompt_content)
                prompt_content = self._merge_content_with_context(prompt_content, context)
            
            # Optimize with Ref MCP
            if optimize:
                target_tokens = max_tokens or self.token_budget.prompt_allocation
                prompt_content = await self._optimize_prompt(prompt_content, target_tokens)
            
            # Prepare result
            result = {
                "prompt": prompt_content,
                "metadata": self._prompt_registry[prompt_key].to_dict(),
                "token_count": self._estimate_tokens(prompt_content),
                "token_budget": {
                    "allocated": self.token_budget.current_usage,
                    "available": self.token_budget.available_tokens(),
                    "total": self.token_budget.total_budget
                },
                "optimized": optimize,
                "context_injected": inject_context,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache result
            if self.cache_enabled:
                self._set_cached(prompt_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading prompt '{prompt_name}': {e}")
            raise
    
    async def load_prompt_chain(
        self,
        prompt_names: List[str],
        shared_context: Optional[Dict[str, Any]] = None,
        optimize_chain: bool = True,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Load a chain of prompts with shared context
        
        Args:
            prompt_names: List of prompt names to load
            shared_context: Shared context for all prompts
            optimize_chain: Whether to optimize the entire chain
            max_tokens: Maximum token budget for the chain
            
        Returns:
            List of loaded prompts
        """
        try:
            results = []
            
            # Calculate token budget per prompt
            chain_budget = max_tokens or self.token_budget.total_budget
            budget_per_prompt = chain_budget // len(prompt_names) if prompt_names else 0
            
            # Store chain context in Memory Bank
            if shared_context:
                await self.memory_bank.store_memory(
                    key=f"chain_context_{datetime.utcnow().timestamp()}",
                    content=shared_context,
                    metadata={"type": "chain_context", "prompts": prompt_names}
                )
            
            # Load prompts in sequence
            for i, prompt_name in enumerate(prompt_names):
                # Adjust budget for last prompt to use remaining tokens
                if i == len(prompt_names) - 1:
                    prompt_budget = self.token_budget.available_tokens()
                else:
                    prompt_budget = budget_per_prompt
                
                prompt_result = await self.load_prompt(
                    prompt_name=prompt_name,
                    variables=shared_context,
                    inject_context=True,
                    optimize=optimize_chain,
                    max_tokens=prompt_budget
                )
                
                results.append(prompt_result)
                
                # Update shared context with result if needed
                if shared_context and "output" in prompt_result:
                    shared_context[f"{prompt_name}_output"] = prompt_result["output"]
            
            # Optimize entire chain if requested
            if optimize_chain and len(results) > 1:
                results = await self._optimize_prompt_chain(results, chain_budget)
            
            return results
            
        except Exception as e:
            logger.error(f"Error loading prompt chain: {e}")
            raise
    
    async def validate_prompt(
        self,
        prompt_name: str,
        prompt_type: Optional[PromptType] = None
    ) -> Dict[str, Any]:
        """
        Validate a prompt template
        
        Args:
            prompt_name: Name of the prompt to validate
            prompt_type: Type of prompt
            
        Returns:
            Validation results
        """
        try:
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "info": {}
            }
            
            # Check if prompt exists
            prompt_key = self._find_prompt_key(prompt_name, prompt_type)
            if not prompt_key:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Prompt '{prompt_name}' not found")
                return validation_result
            
            # Load prompt content
            try:
                prompt_content = await self._load_prompt_content(prompt_key)
            except Exception as e:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Failed to load prompt: {e}")
                return validation_result
            
            # Check prompt structure
            metadata = self._prompt_registry[prompt_key]
            
            # Validate token count
            token_count = self._estimate_tokens(prompt_content)
            if token_count > self.token_budget.total_budget:
                validation_result["errors"].append(
                    f"Prompt exceeds token budget: {token_count} > {self.token_budget.total_budget}"
                )
                validation_result["valid"] = False
            elif token_count > self.token_budget.prompt_allocation:
                validation_result["warnings"].append(
                    f"Prompt may need optimization: {token_count} tokens"
                )
            
            # Check for required variables
            variables = self._extract_variables(prompt_content)
            if variables:
                validation_result["info"]["required_variables"] = list(variables)
            
            # Check dependencies
            if metadata.dependencies:
                for dep in metadata.dependencies:
                    if not self._find_prompt_key(dep):
                        validation_result["warnings"].append(f"Missing dependency: {dep}")
            
            # Add metadata info
            validation_result["info"]["metadata"] = metadata.to_dict()
            validation_result["info"]["token_count"] = token_count
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating prompt '{prompt_name}': {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "info": {}
            }
    
    async def optimize_token_budget(
        self,
        prompts: List[str],
        total_budget: int,
        strategy: TokenBudgetStrategy = TokenBudgetStrategy.ADAPTIVE
    ) -> Dict[str, int]:
        """
        Optimize token budget allocation across multiple prompts
        
        Args:
            prompts: List of prompt names
            total_budget: Total token budget
            strategy: Budget allocation strategy
            
        Returns:
            Token allocation for each prompt
        """
        try:
            allocations = {}
            
            # Get metadata for all prompts
            prompt_metadata = []
            for prompt_name in prompts:
                prompt_key = self._find_prompt_key(prompt_name)
                if prompt_key:
                    metadata = self._prompt_registry[prompt_key]
                    prompt_metadata.append((prompt_name, metadata))
            
            if strategy == TokenBudgetStrategy.PROPORTIONAL:
                # Allocate based on estimated token counts
                total_estimate = sum(m.token_estimate for _, m in prompt_metadata)
                for name, metadata in prompt_metadata:
                    ratio = metadata.token_estimate / total_estimate if total_estimate > 0 else 1 / len(prompts)
                    allocations[name] = int(total_budget * ratio)
            
            elif strategy == TokenBudgetStrategy.PRIORITY_BASED:
                # Allocate based on priority scores
                total_priority = sum(m.priority for _, m in prompt_metadata)
                for name, metadata in prompt_metadata:
                    ratio = metadata.priority / total_priority if total_priority > 0 else 1 / len(prompts)
                    allocations[name] = int(total_budget * ratio)
            
            elif strategy == TokenBudgetStrategy.ADAPTIVE:
                # Use historical usage patterns and current context
                for name, metadata in prompt_metadata:
                    # Start with priority-based allocation
                    base_allocation = (metadata.priority / 10) * (total_budget / len(prompts))
                    
                    # Adjust based on token estimate
                    if metadata.token_estimate > 0:
                        adjustment = min(1.5, metadata.token_estimate / 1000)
                        base_allocation *= adjustment
                    
                    allocations[name] = int(base_allocation)
                
                # Redistribute remaining tokens
                allocated = sum(allocations.values())
                if allocated < total_budget:
                    remaining = total_budget - allocated
                    for name in allocations:
                        allocations[name] += remaining // len(allocations)
            
            elif strategy == TokenBudgetStrategy.FIXED:
                # Equal allocation
                per_prompt = total_budget // len(prompts)
                for name, _ in prompt_metadata:
                    allocations[name] = per_prompt
            
            return allocations
            
        except Exception as e:
            logger.error(f"Error optimizing token budget: {e}")
            # Fallback to equal allocation
            per_prompt = total_budget // len(prompts) if prompts else 0
            return {name: per_prompt for name in prompts}
    
    async def export_prompts(
        self,
        output_format: str = "json",
        include_metadata: bool = True
    ) -> Union[str, Dict[str, Any]]:
        """
        Export all prompts to a specified format
        
        Args:
            output_format: Export format (json, yaml, markdown)
            include_metadata: Whether to include metadata
            
        Returns:
            Exported prompts
        """
        try:
            export_data = {
                "prompts": {},
                "metadata": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "total_prompts": len(self._prompt_registry),
                    "version": "1.0.0"
                }
            }
            
            # Export each prompt
            for prompt_key, metadata in self._prompt_registry.items():
                prompt_content = await self._load_prompt_content(prompt_key)
                
                prompt_export = {
                    "content": prompt_content,
                }
                
                if include_metadata:
                    prompt_export["metadata"] = metadata.to_dict()
                
                export_data["prompts"][prompt_key] = prompt_export
            
            # Format output
            if output_format == "json":
                return json.dumps(export_data, indent=2, default=str)
            elif output_format == "yaml":
                return yaml.dump(export_data, default_flow_style=False)
            elif output_format == "markdown":
                return self._export_as_markdown(export_data)
            else:
                return export_data
                
        except Exception as e:
            logger.error(f"Error exporting prompts: {e}")
            raise
    
    # Private helper methods
    
    def _find_prompt_key(
        self,
        prompt_name: str,
        prompt_type: Optional[PromptType] = None
    ) -> Optional[str]:
        """Find prompt key in registry"""
        if prompt_type:
            key = f"{prompt_type.value}/{prompt_name}"
            if key in self._prompt_registry:
                return key
        else:
            # Search all types
            for type_enum in PromptType:
                key = f"{type_enum.value}/{prompt_name}"
                if key in self._prompt_registry:
                    return key
        return None
    
    async def _load_prompt_content(self, prompt_key: str) -> str:
        """Load prompt content from file"""
        try:
            parts = prompt_key.split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid prompt key: {prompt_key}")
            
            prompt_type, prompt_name = parts
            
            # Try different file extensions
            for ext in [".md", ".txt", ".json", ".yaml"]:
                file_path = self.prompts_dir / prompt_type / f"{prompt_name}{ext}"
                if file_path.exists():
                    content = file_path.read_text(encoding='utf-8')
                    
                    # Process based on file type
                    if ext == ".json":
                        data = json.loads(content)
                        content = data.get("prompt", str(data))
                    elif ext == ".yaml":
                        data = yaml.safe_load(content)
                        content = data.get("prompt", str(data))
                    elif ext == ".md":
                        # Remove metadata header if present
                        if content.startswith("---"):
                            parts = content.split("---", 2)
                            if len(parts) >= 3:
                                content = parts[2].strip()
                    
                    return content
            
            raise FileNotFoundError(f"Prompt file not found for: {prompt_key}")
            
        except Exception as e:
            logger.error(f"Error loading prompt content for {prompt_key}: {e}")
            raise
    
    def _interpolate_variables(
        self,
        content: str,
        variables: Dict[str, Any]
    ) -> str:
        """Interpolate variables into prompt content"""
        try:
            # Use Python string formatting
            for key, value in variables.items():
                # Handle different placeholder styles
                content = content.replace(f"{{{key}}}", str(value))
                content = content.replace(f"${{{key}}}", str(value))
                content = content.replace(f"${key}", str(value))
            
            return content
            
        except Exception as e:
            logger.error(f"Error interpolating variables: {e}")
            return content
    
    async def _inject_context(
        self,
        prompt_name: str,
        prompt_content: str
    ) -> Dict[str, Any]:
        """Inject relevant context from Memory Bank"""
        try:
            # Search for relevant memories
            memories = await self.memory_bank.search_memories(
                query=prompt_name,
                filters={"type": "prompt_context"},
                limit=5
            )
            
            # Extract references from prompt
            references = await self.ref_mcp.extract_references(prompt_content)
            
            # Get memories for references
            reference_memories = []
            for ref_type, ref_values in references.items():
                for ref_value in ref_values[:3]:  # Limit to 3 per type
                    ref_memories = await self.memory_bank.search_memories(
                        query=ref_value,
                        limit=2
                    )
                    reference_memories.extend(ref_memories)
            
            context = {
                "memories": memories,
                "references": reference_memories,
                "metadata": {
                    "injected_at": datetime.utcnow().isoformat(),
                    "prompt_name": prompt_name
                }
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error injecting context: {e}")
            return {}
    
    def _merge_content_with_context(
        self,
        content: str,
        context: Dict[str, Any]
    ) -> str:
        """Merge prompt content with injected context"""
        try:
            if not context:
                return content
            
            # Build context section
            context_parts = []
            
            # Add memories
            if context.get("memories"):
                context_parts.append("## Relevant Context:")
                for memory in context["memories"][:3]:
                    context_parts.append(f"- {memory.get('content', '')}")
                context_parts.append("")
            
            # Add references
            if context.get("references"):
                context_parts.append("## References:")
                for ref in context["references"][:3]:
                    context_parts.append(f"- {ref.get('content', '')}")
                context_parts.append("")
            
            # Merge with original content
            if context_parts:
                context_section = "\n".join(context_parts)
                # Insert context after first paragraph or at beginning
                lines = content.split("\n")
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.strip() == "" and i > 0:
                        insert_pos = i
                        break
                
                lines.insert(insert_pos, context_section)
                content = "\n".join(lines)
            
            return content
            
        except Exception as e:
            logger.error(f"Error merging content with context: {e}")
            return content
    
    async def _optimize_prompt(
        self,
        content: str,
        max_tokens: int
    ) -> str:
        """Optimize prompt using Ref MCP"""
        try:
            # Check if optimization is needed
            current_tokens = self._estimate_tokens(content)
            if current_tokens <= max_tokens:
                return content
            
            # Optimize with Ref MCP
            optimized = await self.ref_mcp.optimize_content(
                content=content,
                max_tokens=max_tokens,
                strategy="auto"
            )
            
            logger.debug(f"Optimized prompt from {current_tokens} to {self._estimate_tokens(optimized)} tokens")
            return optimized
            
        except Exception as e:
            logger.error(f"Error optimizing prompt: {e}")
            return content[:max_tokens * 4]  # Fallback to truncation
    
    async def _optimize_prompt_chain(
        self,
        results: List[Dict[str, Any]],
        total_budget: int
    ) -> List[Dict[str, Any]]:
        """Optimize an entire prompt chain"""
        try:
            # Extract all prompts
            prompts = [r["prompt"] for r in results]
            
            # Deduplicate content across chain
            unique_prompts = await self.ref_mcp.deduplicate_content(prompts, similarity_threshold=0.7)
            
            # Merge similar contexts
            if len(unique_prompts) < len(prompts):
                merged = await self.ref_mcp.merge_contexts(unique_prompts, total_budget)
                
                # Update results with optimized content
                for i, result in enumerate(results):
                    if i < len(unique_prompts):
                        result["prompt"] = unique_prompts[i]
                    result["chain_optimized"] = True
            
            return results
            
        except Exception as e:
            logger.error(f"Error optimizing prompt chain: {e}")
            return results
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Simple estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def _extract_variables(self, content: str) -> set:
        """Extract variable placeholders from content"""
        variables = set()
        
        # Find {variable} style
        variables.update(re.findall(r'\{(\w+)\}', content))
        
        # Find ${variable} style
        variables.update(re.findall(r'\$\{(\w+)\}', content))
        
        # Find $variable style
        variables.update(re.findall(r'\$(\w+)\b', content))
        
        return variables
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached item if valid"""
        if not self.cache_enabled:
            return None
        
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.cache_ttl):
                return value
            else:
                del self._cache[key]
        
        return None
    
    def _set_cached(self, key: str, value: Any):
        """Set cached item"""
        if self.cache_enabled:
            self._cache[key] = (value, datetime.utcnow())
    
    def _export_as_markdown(self, export_data: Dict[str, Any]) -> str:
        """Export prompts as markdown document"""
        lines = []
        lines.append("# Prompt Library Export")
        lines.append(f"\nExported at: {export_data['metadata']['exported_at']}")
        lines.append(f"Total prompts: {export_data['metadata']['total_prompts']}")
        lines.append("\n---\n")
        
        for prompt_key, prompt_data in export_data["prompts"].items():
            lines.append(f"## {prompt_key}")
            
            if "metadata" in prompt_data:
                meta = prompt_data["metadata"]
                lines.append(f"\n**Type:** {meta.get('type', 'Unknown')}")
                lines.append(f"**Version:** {meta.get('version', '1.0.0')}")
                lines.append(f"**Priority:** {meta.get('priority', 5)}/10")
                lines.append(f"**Token Estimate:** {meta.get('token_estimate', 0)}")
                
                if meta.get("description"):
                    lines.append(f"\n{meta['description']}")
            
            lines.append("\n### Content\n")
            lines.append("```")
            lines.append(prompt_data["content"])
            lines.append("```")
            lines.append("\n---\n")
        
        return "\n".join(lines)


# Singleton instance
prompt_loader = None


def get_prompt_loader(
    prompts_dir: str = "prolaunch_prompts",
    **kwargs
) -> PromptLoader:
    """
    Get or create PromptLoader singleton instance
    
    Args:
        prompts_dir: Directory containing prompts
        **kwargs: Additional configuration
        
    Returns:
        PromptLoader instance
    """
    global prompt_loader
    
    if prompt_loader is None:
        prompt_loader = PromptLoader(prompts_dir=prompts_dir, **kwargs)
    
    return prompt_loader