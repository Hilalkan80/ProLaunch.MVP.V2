from uuid import UUID
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
import json
from typing import Any, Dict, Optional
import logging
from datetime import datetime

from ...core.auth import get_current_user_ws
from ...core.deps import get_db, get_redis, get_websocket_manager
from ...core.security.rate_limiter import RedisRateLimiter, RateLimitType, RateLimitExceeded
from ...core.security.content_security import content_validator, ContentSecurityError
from ...core.security.websocket_security import (
    WebSocketAuthenticator, WebSocketConnectionManager, WebSocketSecurityError
)
from ...core.security.sentry_security import get_security_monitor, SecurityEventType
from ...models.user import User
from ...services.chat.chat_service import ChatService
from ...services.chat.websocket_manager import WebSocketManager
from ...core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize security components
ws_authenticator = WebSocketAuthenticator(settings.SECRET_KEY)
security_monitor = get_security_monitor()

@router.websocket("/ws/chat")
async def websocket_endpoint(
    websocket: WebSocket,
    db = Depends(get_db),
    redis = Depends(get_redis),
    ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    rate_limiter = RedisRateLimiter(redis)
    connection_manager = WebSocketConnectionManager(redis, rate_limiter)
    
    try:
        # Enhanced authentication
        user_info, connection_id = await ws_authenticator.authenticate_websocket(websocket, redis)
        
        # Get client IP
        client_ip = websocket.client.host if websocket.client else "unknown"
        
        # Add connection with security checks
        connection_accepted = await connection_manager.add_connection(
            websocket, connection_id, user_info, client_ip
        )
        
        if not connection_accepted:
            return
        
        # Initialize services
        chat_service = ChatService(db, redis)
        current_user = User(id=user_info['user_id'])  # Create user object from info
        
        # Add security breadcrumb
        if security_monitor:
            security_monitor.add_security_breadcrumb(
                f"WebSocket connection established for user {user_info['user_id']}",
                category="websocket",
                data={"connection_id": connection_id, "client_ip": client_ip}
            )
        
        # Connect to legacy websocket manager
        await ws_manager.connect(websocket, user_info['user_id'], connection_id)
        
        while True:
            try:
                data = await websocket.receive_text()
                
                # Validate message size
                if len(data) > 10000:  # 10KB limit
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Message too large"
                    }))
                    continue
                
                # Parse and validate JSON
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                    continue
                
                # Track message activity
                await connection_manager.track_message_activity(
                    connection_id, message.get('type', 'unknown')
                )
                
                # Validate message permissions
                if not await connection_manager.validate_message_permission(
                    connection_id, message.get('type', '')
                ):
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Insufficient permissions"
                    }))
                    continue
                
                # Handle message with enhanced security
                await handle_websocket_message_secure(
                    message,
                    user_info,
                    connection_id,
                    ws_manager,
                    chat_service,
                    db,
                    rate_limiter
                )
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except RateLimitExceeded as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Rate limit exceeded. Try again in {e.retry_after} seconds."
                }))
                # Close connection on repeated rate limit violations
                break
            except ContentSecurityError as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Content security violation: {str(e)}"
                }))
                if security_monitor:
                    security_monitor.track_security_event(
                        SecurityEventType.MALICIOUS_CONTENT,
                        user_id=user_info['user_id'],
                        details={"error": str(e), "connection_id": connection_id}
                    )
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                # Don't expose internal error details to client
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "An error occurred processing your request"
                }))
                if security_monitor:
                    security_monitor.track_security_event(
                        SecurityEventType.WEBSOCKET_ABUSE,
                        user_id=user_info['user_id'],
                        details={"error": str(e), "connection_id": connection_id}
                    )
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except WebSocketSecurityError as e:
        logger.warning(f"WebSocket security error: {e}")
        await websocket.close(code=1008, reason=str(e))
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal server error")
    
    finally:
        # Cleanup
        if 'connection_id' in locals():
            await connection_manager.remove_connection(connection_id)
            await ws_manager.disconnect(user_info['user_id'], connection_id)

async def handle_websocket_message_secure(
    message: Dict[str, Any],
    user_info: Dict,
    connection_id: str,
    ws_manager: WebSocketManager,
    chat_service: ChatService,
    db: Any,
    rate_limiter: RedisRateLimiter
):
    """Handle WebSocket messages with enhanced security validation"""
    message_type = message.get("type")
    if not message_type:
        raise ValueError("Message type is required")
    
    user_id = user_info['user_id']
    user = User(id=user_id)  # Create user object

    if message_type == "join_room":
        # Rate limit room joins
        allowed, retry_after = await rate_limiter.is_allowed(
            str(user_id), RateLimitType.ROOM_JOIN
        )
        if not allowed:
            raise RateLimitExceeded(RateLimitType.ROOM_JOIN, retry_after)
        
        room_id = UUID(message["room_id"])
        await chat_service.validate_room_access(room_id, user.id)
        await ws_manager.join_room(room_id, user.id)
        
        # Add security breadcrumb
        if security_monitor:
            security_monitor.add_security_breadcrumb(
                f"User joined room {room_id}",
                category="chat",
                data={"user_id": str(user_id), "room_id": str(room_id)}
            )

    elif message_type == "leave_room":
        room_id = UUID(message["room_id"])
        await ws_manager.leave_room(room_id, user.id)

    elif message_type == "send_message":
        # Rate limit message sending
        allowed, retry_after = await rate_limiter.is_allowed(
            str(user_id), RateLimitType.MESSAGE_SEND
        )
        if not allowed:
            raise RateLimitExceeded(RateLimitType.MESSAGE_SEND, retry_after)
        
        room_id = UUID(message["room_id"])
        await chat_service.validate_room_access(room_id, user.id)
        
        # Validate and sanitize message content
        content = message.get("content", "")
        content_type = message.get("content_type", "text")
        metadata = message.get("metadata", {})
        
        validated_content = content_validator.validate_and_sanitize_message(
            content, content_type, metadata, user_id
        )
        
        # Create message with validated content
        new_message = await chat_service.create_message(
            room_id=room_id,
            user_id=user.id,
            content=validated_content["content"],
            content_type=content_type,
            metadata=validated_content["metadata"],
            parent_id=UUID(message["parent_id"]) if message.get("parent_id") else None
        )
        
        # Add security score to message metadata
        new_message.metadata["security_score"] = validated_content["security_score"]
        
        await ws_manager.broadcast_message(room_id, new_message, db)
        
        # Log low security score messages
        if validated_content["security_score"] < 0.8 and security_monitor:
            security_monitor.track_security_event(
                SecurityEventType.SUSPICIOUS_USER_BEHAVIOR,
                user_id=user_id,
                details={
                    "reason": "low_security_score",
                    "score": validated_content["security_score"],
                    "room_id": str(room_id)
                }
            )

    elif message_type == "typing":
        # Rate limit typing indicators
        allowed, retry_after = await rate_limiter.is_allowed(
            str(user_id), RateLimitType.TYPING_INDICATOR
        )
        if not allowed:
            raise RateLimitExceeded(RateLimitType.TYPING_INDICATOR, retry_after)
        
        room_id = UUID(message["room_id"])
        is_typing = message["is_typing"]
        await chat_service.validate_room_access(room_id, user.id)
        await ws_manager.notify_typing(room_id, user.id, is_typing)

    elif message_type == "mark_read":
        room_id = UUID(message["room_id"])
        message_ids = [UUID(mid) for mid in message["message_ids"]]
        await chat_service.validate_room_access(room_id, user.id)
        await ws_manager.mark_messages_read(room_id, user.id, message_ids, db)

    elif message_type == "get_history":
        # Rate limit history requests
        allowed, retry_after = await rate_limiter.is_allowed(
            str(user_id), RateLimitType.SEARCH_QUERY
        )
        if not allowed:
            raise RateLimitExceeded(RateLimitType.SEARCH_QUERY, retry_after)
        
        room_id = UUID(message["room_id"])
        await chat_service.validate_room_access(room_id, user.id)
        
        # Limit message history size
        limit = min(message.get("limit", 50), 100)  # Cap at 100 messages
        
        messages = await chat_service.get_messages(
            room_id=room_id,
            limit=limit,
            before_id=UUID(message["before_id"]) if message.get("before_id") else None
        )
        
        return {
            "type": "message_history",
            "room_id": str(room_id),
            "messages": [msg.dict() for msg in messages]
        }

    else:
        raise ValueError(f"Unknown message type: {message_type}")