import logging
from typing import Dict, List, Optional, Set, Union, Tuple
from fastapi import WebSocket, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
from redis.asyncio import Redis

from .rate_limiter import RedisRateLimiter as RateLimiter
from .content_security import ContentSecurity

logger = logging.getLogger(__name__)

class WebSocketSecurity:
    def __init__(
        self,
        redis: Redis,
        secret_key: str,
        rate_limiter: Optional[RateLimiter] = None,
        content_security: Optional[ContentSecurity] = None
    ):
        self.redis = redis
        self.secret_key = secret_key
        self.rate_limiter = rate_limiter or RateLimiter(redis)
        self.content_security = content_security or ContentSecurity()
        
        # Security settings
        self.MAX_CONNECTIONS_PER_USER = 5
        self.MAX_CONNECTIONS_PER_IP = 20
        self.MESSAGE_RATE_LIMIT = (30, 60)  # 30 messages per minute
        self.ROOM_JOIN_RATE_LIMIT = (10, 300)  # 10 room joins per 5 minutes
        
        # Connection tracking
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        self.ip_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_details: Dict[WebSocket, Dict] = {}

    async def authenticate_connection(
        self,
        websocket: WebSocket,
        token: str
    ) -> Dict:
        """
        Authenticate WebSocket connection using JWT
        """
        try:
            # Verify token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=['HS256']
            )
            
            # Check token expiration
            if datetime.fromtimestamp(payload['exp']) < datetime.utcnow():
                raise HTTPException(
                    status_code=401,
                    detail='Token has expired'
                )
            
            # Check token blacklist
            if await self.is_token_blacklisted(token):
                raise HTTPException(
                    status_code=401,
                    detail='Token has been revoked'
                )
            
            return payload

        except JWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=401,
                detail='Invalid authentication token'
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=401,
                detail='Authentication failed'
            )

    async def validate_connection(
        self,
        websocket: WebSocket,
        client_ip: str,
        user_id: str
    ) -> None:
        """
        Validate new WebSocket connection against limits
        """
        try:
            # Check IP blocking
            if await self.rate_limiter.ip_is_blocked(client_ip):
                raise HTTPException(
                    status_code=403,
                    detail='IP address is blocked'
                )
            
            # Check connection limits
            user_conn_count = len(self.user_connections.get(user_id, set()))
            if user_conn_count >= self.MAX_CONNECTIONS_PER_USER:
                raise HTTPException(
                    status_code=429,
                    detail='Too many connections for user'
                )
            
            ip_conn_count = len(self.ip_connections.get(client_ip, set()))
            if ip_conn_count >= self.MAX_CONNECTIONS_PER_IP:
                raise HTTPException(
                    status_code=429,
                    detail='Too many connections from IP'
                )
            
            # Check rate limits
            is_allowed, retry_after = await self.rate_limiter.check_rate_limit(
                'websocket',
                client_ip,
                'ws_connect'
            )
            if not is_allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        'error': 'Rate limit exceeded',
                        'retry_after': retry_after
                    }
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Connection validation error: {e}")
            raise HTTPException(
                status_code=500,
                detail='Connection validation failed'
            )

    async def track_connection(
        self,
        websocket: WebSocket,
        user_id: str,
        client_ip: str
    ) -> None:
        """
        Track new WebSocket connection
        """
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        # Track IP connections
        if client_ip not in self.ip_connections:
            self.ip_connections[client_ip] = set()
        self.ip_connections[client_ip].add(websocket)
        
        # Store connection details
        self.connection_details[websocket] = {
            'user_id': user_id,
            'client_ip': client_ip,
            'connected_at': datetime.utcnow(),
            'message_count': 0,
            'warning_count': 0
        }

    async def untrack_connection(
        self,
        websocket: WebSocket
    ) -> None:
        """
        Remove tracking for closed connection
        """
        try:
            details = self.connection_details.get(websocket)
            if details:
                user_id = details['user_id']
                client_ip = details['client_ip']
                
                # Remove from user connections
                if user_id in self.user_connections:
                    self.user_connections[user_id].discard(websocket)
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]
                
                # Remove from IP connections
                if client_ip in self.ip_connections:
                    self.ip_connections[client_ip].discard(websocket)
                    if not self.ip_connections[client_ip]:
                        del self.ip_connections[client_ip]
                
                # Remove connection details
                del self.connection_details[websocket]

        except Exception as e:
            logger.error(f"Error untracking connection: {e}")

    async def validate_message(
        self,
        websocket: WebSocket,
        message: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Validate WebSocket message
        """
        warnings = []
        details = self.connection_details.get(websocket)
        
        try:
            if not details:
                return False, ['Connection not tracked']
            
            user_id = details['user_id']
            client_ip = details['client_ip']
            
            # Check rate limits
            is_allowed, retry_after = await self.rate_limiter.check_rate_limit(
                'websocket',
                client_ip,
                'message'
            )
            if not is_allowed:
                return False, [
                    f'Rate limit exceeded. Retry after {retry_after} seconds'
                ]
            
            # Validate message structure
            if not isinstance(message, dict):
                return False, ['Invalid message format']
            
            if 'type' not in message:
                return False, ['Message type required']
            
            # Validate content if present
            if 'content' in message:
                content, content_warnings = await self.content_security.validate_and_sanitize_message(
                    message['content'],
                    message.get('metadata')
                )
                warnings.extend(content_warnings)
                
                if not content:
                    return False, ['Invalid message content']
                
                message['content'] = content
            
            # Track message count
            details['message_count'] += 1
            
            # Track warnings
            if warnings:
                details['warning_count'] += 1
            
            # Check for abuse
            if self.detect_abuse(details):
                await self.handle_abuse(websocket, details)
                return False, ['Connection terminated due to abuse']
            
            return True, warnings

        except Exception as e:
            logger.error(f"Message validation error: {e}")
            return False, ['Message validation failed']

    def detect_abuse(self, details: Dict) -> bool:
        """
        Detect potential abuse based on connection stats
        """
        try:
            connected_duration = datetime.utcnow() - details['connected_at']
            
            # Check message rate
            if connected_duration < timedelta(minutes=1):
                if details['message_count'] > 60:  # More than 1 message per second
                    return True
            
            # Check warning ratio
            if details['message_count'] > 10:
                warning_ratio = details['warning_count'] / details['message_count']
                if warning_ratio > 0.3:  # More than 30% messages triggered warnings
                    return True
            
            return False

        except Exception as e:
            logger.error(f"Abuse detection error: {e}")
            return False

    async def handle_abuse(
        self,
        websocket: WebSocket,
        details: Dict
    ) -> None:
        """
        Handle detected abuse
        """
        try:
            client_ip = details['client_ip']
            user_id = details['user_id']
            
            # Block IP
            await self.rate_limiter.block_ip(
                client_ip,
                'WebSocket abuse detected'
            )
            
            # Record incident
            incident = {
                'type': 'websocket_abuse',
                'user_id': user_id,
                'client_ip': client_ip,
                'message_count': details['message_count'],
                'warning_count': details['warning_count'],
                'connection_duration': str(
                    datetime.utcnow() - details['connected_at']
                ),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await self.redis.lpush(
                'security_incidents',
                json.dumps(incident)
            )
            
            # Close connection
            await websocket.close(code=1008)  # Policy violation
            
            # Clean up tracking
            await self.untrack_connection(websocket)

        except Exception as e:
            logger.error(f"Error handling abuse: {e}")

    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted
        """
        try:
            return bool(
                await self.redis.exists(f'blacklisted_token:{token}')
            )
        except Exception as e:
            logger.error(f"Token blacklist check error: {e}")
            return False

    async def blacklist_token(
        self,
        token: str,
        reason: str = 'User logout'
    ) -> None:
        """
        Add a token to the blacklist
        """
        try:
            # Decode token to get expiration
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=['HS256']
            )
            exp = datetime.fromtimestamp(payload['exp'])
            
            # Store in Redis with expiration
            ttl = int((exp - datetime.utcnow()).total_seconds())
            if ttl > 0:
                await self.redis.setex(
                    f'blacklisted_token:{token}',
                    ttl,
                    reason
                )
        except Exception as e:
            logger.error(f"Token blacklisting error: {e}")

    async def close_user_connections(self, user_id: str) -> None:
        """
        Close all connections for a user
        """
        if user_id in self.user_connections:
            for websocket in self.user_connections[user_id].copy():
                try:
                    await websocket.close(code=1000)
                    await self.untrack_connection(websocket)
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")

class WebSocketAuth(HTTPBearer):
    """
    FastAPI security scheme for WebSocket authentication
    """
    async def __call__(
        self,
        websocket: WebSocket
    ) -> Optional[HTTPAuthorizationCredentials]:
        try:
            token = websocket.headers.get('authorization')
            if token and token.startswith('Bearer '):
                return HTTPAuthorizationCredentials(
                    scheme='Bearer',
                    credentials=token[7:]
                )
        except Exception as e:
            logger.error(f"WebSocket auth error: {e}")
        
        return None