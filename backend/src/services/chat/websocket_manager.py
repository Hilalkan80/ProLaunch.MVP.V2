from typing import Dict, Set
from uuid import UUID
from fastapi import WebSocket
from redis.asyncio import Redis
import json
import logging
from datetime import datetime

from ...models.chat import ChatRoom, ChatMessage, ChatMessageReceipt
from ...database import AsyncSession
from ...core.config import settings

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self, redis: Redis):
        self.active_connections: Dict[UUID, Dict[str, WebSocket]] = {}
        self.room_participants: Dict[UUID, Set[UUID]] = {}
        self.redis = redis
        self.pubsub = self.redis.pubsub()

    async def connect(self, websocket: WebSocket, user_id: UUID, connection_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][connection_id] = websocket

    async def disconnect(self, user_id: UUID, connection_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].pop(connection_id, None)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            await self._notify_user_offline(user_id)

    async def join_room(self, room_id: UUID, user_id: UUID):
        if room_id not in self.room_participants:
            self.room_participants[room_id] = set()
        self.room_participants[room_id].add(user_id)
        await self.redis.sadd(f"chat:room:{room_id}:participants", str(user_id))
        await self._notify_room(room_id, {
            "type": "user_joined",
            "room_id": str(room_id),
            "user_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat()
        })

    async def leave_room(self, room_id: UUID, user_id: UUID):
        if room_id in self.room_participants:
            self.room_participants[room_id].discard(user_id)
            if not self.room_participants[room_id]:
                del self.room_participants[room_id]
        await self.redis.srem(f"chat:room:{room_id}:participants", str(user_id))
        await self._notify_room(room_id, {
            "type": "user_left",
            "room_id": str(room_id),
            "user_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat()
        })

    async def broadcast_message(self, room_id: UUID, message: ChatMessage, db: AsyncSession):
        message_data = {
            "type": "new_message",
            "room_id": str(room_id),
            "message": {
                "id": str(message.id),
                "content": message.content,
                "content_type": message.content_type,
                "user_id": str(message.user_id),
                "created_at": message.created_at.isoformat(),
                "metadata": message.metadata,
                "parent_id": str(message.parent_id) if message.parent_id else None
            }
        }
        
        await self._notify_room(room_id, message_data)
        await self._store_message_receipts(message, room_id, db)

    async def notify_typing(self, room_id: UUID, user_id: UUID, is_typing: bool):
        notification = {
            "type": "typing_indicator",
            "room_id": str(room_id),
            "user_id": str(user_id),
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self._notify_room(room_id, notification)
        if is_typing:
            await self.redis.setex(
                f"chat:typing:{room_id}:{user_id}",
                10,  # Expire after 10 seconds
                "1"
            )

    async def mark_messages_read(self, room_id: UUID, user_id: UUID, message_ids: list[UUID], db: AsyncSession):
        now = datetime.utcnow()
        for message_id in message_ids:
            receipt = ChatMessageReceipt(
                message_id=message_id,
                user_id=user_id,
                read_at=now
            )
            db.add(receipt)
        await db.commit()

        notification = {
            "type": "messages_read",
            "room_id": str(room_id),
            "user_id": str(user_id),
            "message_ids": [str(mid) for mid in message_ids],
            "timestamp": now.isoformat()
        }
        await self._notify_room(room_id, notification)

    async def _notify_room(self, room_id: UUID, data: dict):
        channel = f"chat:room:{room_id}"
        await self.redis.publish(channel, json.dumps(data))
        
        if room_id in self.room_participants:
            message = json.dumps(data)
            for user_id in self.room_participants[room_id]:
                if user_id in self.active_connections:
                    for websocket in self.active_connections[user_id].values():
                        try:
                            await websocket.send_text(message)
                        except Exception as e:
                            logger.error(f"Failed to send message to user {user_id}: {e}")

    async def _notify_user_offline(self, user_id: UUID):
        rooms = await self._get_user_rooms(user_id)
        for room_id in rooms:
            await self._notify_room(room_id, {
                "type": "user_offline",
                "room_id": str(room_id),
                "user_id": str(user_id),
                "timestamp": datetime.utcnow().isoformat()
            })

    async def _store_message_receipts(self, message: ChatMessage, room_id: UUID, db: AsyncSession):
        now = datetime.utcnow()
        online_participants = await self.redis.smembers(f"chat:room:{room_id}:participants")
        
        receipts = []
        for participant_id in online_participants:
            receipt = ChatMessageReceipt(
                message_id=message.id,
                user_id=UUID(participant_id.decode()),
                received_at=now
            )
            receipts.append(receipt)
        
        db.add_all(receipts)
        await db.commit()

    async def _get_user_rooms(self, user_id: UUID) -> Set[UUID]:
        return {
            room_id 
            for room_id, participants in self.room_participants.items() 
            if user_id in participants
        }