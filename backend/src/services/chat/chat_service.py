from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
from redis.asyncio import Redis
from fastapi import HTTPException
import re
import logging

from ...database import AsyncSession
from ...models.chat import ChatRoom, ChatMessage, ChatRoomParticipant
from ...models.tenant import Tenant
from ...core.security.sentry_security import get_security_monitor, SecurityEventType

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.security_monitor = get_security_monitor()

    async def create_room(
        self,
        tenant_id: UUID,
        creator_id: UUID,
        type: str,
        name: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> ChatRoom:
        room = ChatRoom(
            tenant_id=tenant_id,
            type=type,
            name=name,
            metadata=metadata or {}
        )
        self.db.add(room)
        
        creator_participant = ChatRoomParticipant(
            room_id=room.id,
            user_id=creator_id,
            role="admin"
        )
        self.db.add(creator_participant)
        
        await self.db.commit()
        await self.db.refresh(room)
        return room

    async def add_participant(
        self,
        room_id: UUID,
        user_id: UUID,
        role: str = "member"
    ) -> ChatRoomParticipant:
        participant = ChatRoomParticipant(
            room_id=room_id,
            user_id=user_id,
            role=role
        )
        self.db.add(participant)
        await self.db.commit()
        await self.db.refresh(participant)
        return participant

    async def remove_participant(self, room_id: UUID, user_id: UUID):
        stmt = select(ChatRoomParticipant).where(
            and_(
                ChatRoomParticipant.room_id == room_id,
                ChatRoomParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        participant = result.scalar_one_or_none()
        
        if participant:
            await self.db.delete(participant)
            await self.db.commit()

    async def create_message(
        self,
        room_id: UUID,
        user_id: UUID,
        content: str,
        content_type: str = "text",
        metadata: Optional[dict] = None,
        parent_id: Optional[UUID] = None
    ) -> ChatMessage:
        message = ChatMessage(
            room_id=room_id,
            user_id=user_id,
            content=content,
            content_type=content_type,
            metadata=metadata or {},
            parent_id=parent_id
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_messages(
        self,
        room_id: UUID,
        limit: int = 50,
        before_id: Optional[UUID] = None
    ) -> List[ChatMessage]:
        query = (
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .options(
                selectinload(ChatMessage.user),
                selectinload(ChatMessage.reactions),
                selectinload(ChatMessage.receipts)
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        
        if before_id:
            message = await self.db.get(ChatMessage, before_id)
            if message:
                query = query.where(ChatMessage.created_at < message.created_at)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def validate_room_access(self, room_id: UUID, user_id: UUID):
        stmt = select(ChatRoomParticipant).where(
            and_(
                ChatRoomParticipant.room_id == room_id,
                ChatRoomParticipant.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise HTTPException(status_code=403, detail="Access to chat room denied")
        return participant

    async def get_user_rooms(self, user_id: UUID) -> List[ChatRoom]:
        stmt = (
            select(ChatRoom)
            .join(ChatRoomParticipant)
            .where(ChatRoomParticipant.user_id == user_id)
            .options(selectinload(ChatRoom.participants))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def search_messages(
        self,
        room_id: UUID,
        query: str,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[UUID] = None
    ) -> List[ChatMessage]:
        # Validate and sanitize search query
        sanitized_query = self._sanitize_search_query(query, user_id)
        
        # Limit result size
        safe_limit = min(limit, 100)
        safe_offset = max(0, offset)
        
        # Use parameterized query to prevent SQL injection
        stmt = (
            select(ChatMessage)
            .where(
                and_(
                    ChatMessage.room_id == room_id,
                    ChatMessage.content.ilike(f"%{sanitized_query}%"),
                    ChatMessage.deleted_at.is_(None)  # Only search non-deleted messages
                )
            )
            .order_by(ChatMessage.created_at.desc())
            .offset(safe_offset)
            .limit(safe_limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    def _sanitize_search_query(self, query: str, user_id: Optional[UUID] = None) -> str:
        """Sanitize search query to prevent SQL injection and other attacks"""
        if not query or not isinstance(query, str):
            return ""
        
        # Remove or escape potentially dangerous characters
        # Keep only alphanumeric, spaces, and basic punctuation
        sanitized = re.sub(r'[^\w\s\-_.,!?@#]', '', query)
        
        # Limit length
        sanitized = sanitized[:200]
        
        # Check for SQL injection patterns
        sql_patterns = [
            r'\bunion\b', r'\bselect\b', r'\binsert\b', r'\bupdate\b', r'\bdelete\b',
            r'\bdrop\b', r'\bcreate\b', r'\balter\b', r'\bexec\b', r'\bexecute\b',
            r'--', r'/\*', r'\*/', r';', r'\|\|', r'&&'
        ]
        
        query_lower = sanitized.lower()
        for pattern in sql_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                if self.security_monitor and user_id:
                    self.security_monitor.track_security_event(
                        SecurityEventType.SQL_INJECTION_ATTEMPT,
                        user_id=user_id,
                        details={
                            "query": query[:100],  # First 100 chars only
                            "pattern_matched": pattern,
                            "sanitized_query": sanitized
                        }
                    )
                logger.warning(f"Potential SQL injection attempt detected: {pattern} in query: {query[:50]}")
                # Return empty string to prevent injection
                return ""
        
        return sanitized.strip()

    async def validate_tenant_access(self, tenant_id: UUID, user_id: UUID):
        stmt = select(Tenant).where(
            and_(
                Tenant.id == tenant_id,
                or_(
                    Tenant.owner_id == user_id,
                    Tenant.members.any(id=user_id)
                )
            )
        )
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(status_code=403, detail="Access to tenant denied")
        return tenant