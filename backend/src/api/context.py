"""
Context Management API

Provides API endpoints for the context management system.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime

from ..services.context import ContextManager
from ..core.dependencies import get_current_user, AuthUser
from ..models.base import get_db
from sqlalchemy.ext.asyncio import AsyncSession

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/context",
    tags=["context"],
    responses={404: {"description": "Not found"}},
)

# Store context managers per session
context_managers: Dict[str, ContextManager] = {}


class MessageInput(BaseModel):
    """Input model for adding messages"""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ContextQuery(BaseModel):
    """Input model for context queries"""
    query: Optional[str] = Field(default=None, description="Optional query for relevance filtering")
    query_type: str = Field(default="general", description="Type of query")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens")


class MilestoneUpdate(BaseModel):
    """Input model for milestone updates"""
    milestone_id: str = Field(..., description="Milestone identifier")
    milestone_data: Dict[str, Any] = Field(..., description="Milestone information")


class TaskResult(BaseModel):
    """Input model for task results"""
    task: str = Field(..., description="Task description")
    result: str = Field(..., description="Task result")
    status: str = Field(default="completed", description="Task status")


class KnowledgeInput(BaseModel):
    """Input model for adding knowledge"""
    knowledge: str = Field(..., description="Knowledge content")
    category: str = Field(default="general", description="Knowledge category")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Importance score")


async def get_context_manager(
    current_user: AuthUser = Depends(get_current_user)
) -> ContextManager:
    """
    Get or create context manager for the current user session.
    """
    session_key = f"{current_user.id}:{current_user.token_payload.get('session_id', 'default')}"
    
    if session_key not in context_managers:
        manager = ContextManager(
            user_id=current_user.id,
            session_id=current_user.token_payload.get('session_id', 'default')
        )
        await manager.initialize()
        context_managers[session_key] = manager
    
    return context_managers[session_key]


@router.post("/initialize")
async def initialize_context(
    current_user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Initialize context management for the current session.
    """
    try:
        manager = await get_context_manager(current_user)
        
        if not manager.is_initialized:
            success = await manager.initialize()
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize context manager"
                )
        
        return {
            "status": "initialized",
            "user_id": current_user.id,
            "session_id": manager.session_id,
            "statistics": manager.get_statistics()
        }
        
    except Exception as e:
        logger.error(f"Error initializing context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/message")
async def add_message(
    message: MessageInput,
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Add a message to the context system.
    """
    try:
        success = await manager.add_message(
            role=message.role,
            content=message.content,
            metadata=message.metadata
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add message to context"
            )
        
        return {
            "status": "success",
            "message": "Message added to context",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error adding message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/query")
async def query_context(
    query: ContextQuery,
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Query the context system.
    """
    try:
        context = await manager.get_context(
            query=query.query,
            query_type=query.query_type,
            max_tokens=query.max_tokens
        )
        
        return {
            "status": "success",
            "context": context,
            "token_count": len(context) // 4,  # Rough estimate
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error querying context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/milestone")
async def update_milestone(
    milestone: MilestoneUpdate,
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Update current milestone in journey context.
    """
    try:
        success = await manager.update_milestone(
            milestone_id=milestone.milestone_id,
            milestone_data=milestone.milestone_data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update milestone"
            )
        
        return {
            "status": "success",
            "milestone_id": milestone.milestone_id,
            "message": "Milestone updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating milestone: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/task")
async def add_task_result(
    task: TaskResult,
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Add task result to journey context.
    """
    try:
        success = await manager.add_task_result(
            task=task.task,
            result=task.result,
            status=task.status
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add task result"
            )
        
        return {
            "status": "success",
            "task": task.task,
            "message": "Task result added successfully"
        }
        
    except Exception as e:
        logger.error(f"Error adding task result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/learn")
async def add_knowledge(
    knowledge: KnowledgeInput,
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Add new knowledge to the knowledge context.
    """
    try:
        success = await manager.learn(
            knowledge=knowledge.knowledge,
            category=knowledge.category,
            importance=knowledge.importance
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add knowledge"
            )
        
        return {
            "status": "success",
            "category": knowledge.category,
            "message": "Knowledge added successfully"
        }
        
    except Exception as e:
        logger.error(f"Error adding knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/optimize")
async def optimize_context(
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Optimize all context layers.
    """
    try:
        results = await manager.optimize_all_layers()
        
        return {
            "status": "success",
            "optimization_results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/persist")
async def persist_context(
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Persist all context layers to storage.
    """
    try:
        success = await manager.persist_all()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist context"
            )
        
        return {
            "status": "success",
            "message": "Context persisted successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error persisting context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/clear-session")
async def clear_session_context(
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Clear session context while preserving journey and knowledge.
    """
    try:
        success = await manager.clear_session()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear session"
            )
        
        return {
            "status": "success",
            "message": "Session context cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/statistics")
async def get_context_statistics(
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Get comprehensive context statistics.
    """
    try:
        statistics = manager.get_statistics()
        
        return {
            "status": "success",
            "statistics": statistics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/token-status")
async def get_token_status(
    manager: ContextManager = Depends(get_context_manager)
) -> Dict[str, Any]:
    """
    Get current token allocation status.
    """
    try:
        token_status = manager.token_manager.get_allocation_status()
        
        return {
            "status": "success",
            "token_status": token_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting token status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )