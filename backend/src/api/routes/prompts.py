"""
API routes for prompt management using PromptLoader
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

from ...ai import (
    get_prompt_loader,
    PromptType,
    TokenBudgetStrategy
)
from ...core.auth import get_current_user
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/prompts",
    tags=["prompts"],
    responses={404: {"description": "Not found"}},
)


class PromptLoadRequest(BaseModel):
    """Request model for loading a prompt"""
    prompt_name: str = Field(..., description="Name of the prompt to load")
    prompt_type: Optional[str] = Field(None, description="Type of prompt (system, chat, milestones, style)")
    variables: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Variables to interpolate")
    inject_context: bool = Field(True, description="Whether to inject context from Memory Bank")
    optimize: bool = Field(True, description="Whether to optimize with Ref MCP")
    max_tokens: Optional[int] = Field(None, description="Maximum token budget", ge=100, le=32000)


class PromptChainRequest(BaseModel):
    """Request model for loading a prompt chain"""
    prompt_names: List[str] = Field(..., description="List of prompt names to load in sequence")
    shared_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Shared context for all prompts")
    optimize_chain: bool = Field(True, description="Whether to optimize the entire chain")
    max_tokens: Optional[int] = Field(None, description="Maximum token budget for the chain", ge=100, le=32000)


class PromptValidateRequest(BaseModel):
    """Request model for validating a prompt"""
    prompt_name: str = Field(..., description="Name of the prompt to validate")
    prompt_type: Optional[str] = Field(None, description="Type of prompt")


class TokenBudgetRequest(BaseModel):
    """Request model for token budget optimization"""
    prompts: List[str] = Field(..., description="List of prompt names")
    total_budget: int = Field(..., description="Total token budget", ge=100, le=32000)
    strategy: str = Field("adaptive", description="Budget allocation strategy")


class PromptExportRequest(BaseModel):
    """Request model for exporting prompts"""
    output_format: str = Field("json", description="Export format (json, yaml, markdown)")
    include_metadata: bool = Field(True, description="Whether to include metadata")


@router.post("/load", response_model=Dict[str, Any])
async def load_prompt(
    request: PromptLoadRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Load a prompt template with optional context injection and optimization
    
    This endpoint allows loading prompt templates from the /prolaunch_prompts/ directory
    with support for:
    - Variable interpolation
    - Context injection from Memory Bank MCP
    - Content optimization using Ref MCP
    - Token budget management
    """
    try:
        prompt_loader = get_prompt_loader()
        
        # Convert string prompt_type to enum if provided
        prompt_type = None
        if request.prompt_type:
            try:
                prompt_type = PromptType(request.prompt_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid prompt type: {request.prompt_type}"
                )
        
        # Load the prompt
        result = await prompt_loader.load_prompt(
            prompt_name=request.prompt_name,
            prompt_type=prompt_type,
            variables=request.variables,
            inject_context=request.inject_context,
            optimize=request.optimize,
            max_tokens=request.max_tokens
        )
        
        # Log usage for analytics
        logger.info(
            f"User {current_user.id} loaded prompt '{request.prompt_name}' "
            f"with {result['token_count']} tokens"
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error loading prompt: {e}")
        raise HTTPException(status_code=500, detail="Failed to load prompt")


@router.post("/load-chain", response_model=List[Dict[str, Any]])
async def load_prompt_chain(
    request: PromptChainRequest,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Load a chain of prompts with shared context
    
    This endpoint loads multiple prompts in sequence with:
    - Shared context across all prompts
    - Chain-level optimization
    - Token budget management across the chain
    """
    try:
        prompt_loader = get_prompt_loader()
        
        results = await prompt_loader.load_prompt_chain(
            prompt_names=request.prompt_names,
            shared_context=request.shared_context,
            optimize_chain=request.optimize_chain,
            max_tokens=request.max_tokens
        )
        
        # Log chain usage
        total_tokens = sum(r["token_count"] for r in results)
        logger.info(
            f"User {current_user.id} loaded prompt chain with {len(request.prompt_names)} prompts "
            f"using {total_tokens} total tokens"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error loading prompt chain: {e}")
        raise HTTPException(status_code=500, detail="Failed to load prompt chain")


@router.post("/validate", response_model=Dict[str, Any])
async def validate_prompt(
    request: PromptValidateRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Validate a prompt template
    
    This endpoint validates a prompt template and returns:
    - Validation status
    - Any errors or warnings
    - Required variables
    - Token count estimates
    """
    try:
        prompt_loader = get_prompt_loader()
        
        # Convert string prompt_type to enum if provided
        prompt_type = None
        if request.prompt_type:
            try:
                prompt_type = PromptType(request.prompt_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid prompt type: {request.prompt_type}"
                )
        
        result = await prompt_loader.validate_prompt(
            prompt_name=request.prompt_name,
            prompt_type=prompt_type
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error validating prompt: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate prompt")


@router.post("/optimize-budget", response_model=Dict[str, int])
async def optimize_token_budget(
    request: TokenBudgetRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, int]:
    """
    Optimize token budget allocation across multiple prompts
    
    This endpoint calculates optimal token allocation using various strategies:
    - proportional: Based on estimated token counts
    - priority_based: Based on priority scores
    - adaptive: Dynamic adjustment based on usage patterns
    - fixed: Equal allocation
    """
    try:
        prompt_loader = get_prompt_loader()
        
        # Convert string strategy to enum
        try:
            strategy = TokenBudgetStrategy(request.strategy)
        except ValueError:
            strategy = TokenBudgetStrategy.ADAPTIVE
        
        allocations = await prompt_loader.optimize_token_budget(
            prompts=request.prompts,
            total_budget=request.total_budget,
            strategy=strategy
        )
        
        return allocations
        
    except Exception as e:
        logger.error(f"Error optimizing token budget: {e}")
        raise HTTPException(status_code=500, detail="Failed to optimize token budget")


@router.get("/list", response_model=Dict[str, List[str]])
async def list_prompts(
    current_user: User = Depends(get_current_user)
) -> Dict[str, List[str]]:
    """
    List all available prompts organized by type
    
    Returns a dictionary with prompt types as keys and lists of prompt names as values
    """
    try:
        prompt_loader = get_prompt_loader()
        
        # Organize prompts by type
        prompts_by_type = {}
        for prompt_key in prompt_loader._prompt_registry.keys():
            prompt_type, prompt_name = prompt_key.split("/", 1)
            
            if prompt_type not in prompts_by_type:
                prompts_by_type[prompt_type] = []
            
            prompts_by_type[prompt_type].append(prompt_name)
        
        # Sort prompt names within each type
        for prompt_type in prompts_by_type:
            prompts_by_type[prompt_type].sort()
        
        return prompts_by_type
        
    except Exception as e:
        logger.error(f"Error listing prompts: {e}")
        raise HTTPException(status_code=500, detail="Failed to list prompts")


@router.get("/metadata/{prompt_type}/{prompt_name}", response_model=Dict[str, Any])
async def get_prompt_metadata(
    prompt_type: str,
    prompt_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get metadata for a specific prompt
    
    Returns detailed metadata including version, priority, tags, and token estimates
    """
    try:
        prompt_loader = get_prompt_loader()
        
        prompt_key = f"{prompt_type}/{prompt_name}"
        
        if prompt_key not in prompt_loader._prompt_registry:
            raise HTTPException(
                status_code=404,
                detail=f"Prompt '{prompt_key}' not found"
            )
        
        metadata = prompt_loader._prompt_registry[prompt_key]
        return metadata.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to get prompt metadata")


@router.post("/export")
async def export_prompts(
    request: PromptExportRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Export all prompts to a specified format
    
    Supports export formats:
    - json: JSON format with full structure
    - yaml: YAML format for easy editing
    - markdown: Human-readable markdown documentation
    """
    try:
        prompt_loader = get_prompt_loader()
        
        result = await prompt_loader.export_prompts(
            output_format=request.output_format,
            include_metadata=request.include_metadata
        )
        
        # Return appropriate content type based on format
        if request.output_format == "json":
            return {"format": "json", "data": result}
        elif request.output_format == "yaml":
            return {"format": "yaml", "data": result}
        elif request.output_format == "markdown":
            return {"format": "markdown", "data": result}
        else:
            return {"format": "dict", "data": result}
        
    except Exception as e:
        logger.error(f"Error exporting prompts: {e}")
        raise HTTPException(status_code=500, detail="Failed to export prompts")


@router.get("/types", response_model=List[str])
async def get_prompt_types(
    current_user: User = Depends(get_current_user)
) -> List[str]:
    """
    Get all available prompt types
    
    Returns a list of prompt type values (system, chat, milestones, style, custom)
    """
    return [pt.value for pt in PromptType]


@router.get("/strategies", response_model=List[str])
async def get_budget_strategies(
    current_user: User = Depends(get_current_user)
) -> List[str]:
    """
    Get all available token budget strategies
    
    Returns a list of strategy values (proportional, priority_based, adaptive, fixed)
    """
    return [s.value for s in TokenBudgetStrategy]


@router.get("/health", response_model=Dict[str, Any])
async def prompt_system_health() -> Dict[str, Any]:
    """
    Check the health of the prompt system
    
    Returns system status including:
    - Total prompts loaded
    - MCP integration status
    - Cache status
    """
    try:
        prompt_loader = get_prompt_loader()
        
        health = {
            "status": "healthy",
            "total_prompts": len(prompt_loader._prompt_registry),
            "cache_enabled": prompt_loader.cache_enabled,
            "cache_entries": len(prompt_loader._cache),
            "mcp_integrations": {
                "ref_mcp": prompt_loader.ref_mcp is not None,
                "memory_bank": prompt_loader.memory_bank is not None
            },
            "token_budget": {
                "total": prompt_loader.token_budget.total_budget,
                "available": prompt_loader.token_budget.available_tokens()
            }
        }
        
        return health
        
    except Exception as e:
        logger.error(f"Error checking prompt system health: {e}")
        return {
            "status": "error",
            "error": str(e)
        }