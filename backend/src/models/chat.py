from datetime import datetime
from uuid import UUID
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import Base

# Enums for chat system
class RoomType(str, PyEnum):
    DIRECT = "direct"
    GROUP = "group"
    SUPPORT = "support"
    BROADCAST = "broadcast"

class MessageType(str, PyEnum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

class MessageStatus(str, PyEnum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    DELETED = "deleted"

class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(PGUUID, primary_key=True)
    # TODO: Enable when tenants table is created
    # tenant_id = Column(PGUUID, ForeignKey("tenants.id"), nullable=False)
    type = Column(Enum("direct", "group", "support", "broadcast", name="chat_room_type"), nullable=False)
    name = Column(String(100))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    room_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    participants = relationship("ChatRoomParticipant", back_populates="room")
    messages = relationship("ChatMessage", back_populates="room")

class ChatRoomParticipant(Base):
    __tablename__ = "chat_room_participants"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_participant"),
    )

    id = Column(PGUUID, primary_key=True)
    room_id = Column(PGUUID, ForeignKey("chat_rooms.id"), nullable=False)
    user_id = Column(PGUUID, ForeignKey("users.id"), nullable=False)
    role = Column(Enum("admin", "moderator", "member", name="chat_participant_role"), nullable=False)
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_read_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_muted = Column(Boolean, nullable=False, default=False)
    settings = Column(JSONB, nullable=False, default=dict)

    room = relationship("ChatRoom", back_populates="participants")
    user = relationship("User", back_populates="chat_participations")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(PGUUID, primary_key=True)
    room_id = Column(PGUUID, ForeignKey("chat_rooms.id"), nullable=False)
    user_id = Column(PGUUID, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(Enum("text", "image", "file", "system", name="chat_message_type"), nullable=False)
    message_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    parent_id = Column(PGUUID, ForeignKey("chat_messages.id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime)

    room = relationship("ChatRoom", back_populates="messages")
    user = relationship("User", back_populates="chat_messages")
    parent = relationship("ChatMessage", remote_side=[id], back_populates="replies")
    replies = relationship("ChatMessage", back_populates="parent")
    reactions = relationship("ChatMessageReaction", back_populates="message")
    receipts = relationship("ChatMessageReceipt", back_populates="message")

    __table_args__ = (
        Index("ix_chat_messages_room_created", "room_id", "created_at"),
    )

class ChatMessageReaction(Base):
    __tablename__ = "chat_message_reactions"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", "emoji", name="uq_message_user_emoji"),
    )

    id = Column(PGUUID, primary_key=True)
    message_id = Column(PGUUID, ForeignKey("chat_messages.id"), nullable=False)
    user_id = Column(PGUUID, ForeignKey("users.id"), nullable=False)
    emoji = Column(String(32), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    message = relationship("ChatMessage", back_populates="reactions")
    user = relationship("User", back_populates="chat_reactions")

class ChatMessageReceipt(Base):
    __tablename__ = "chat_message_receipts"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_message_receipt"),
    )

    id = Column(PGUUID, primary_key=True)
    message_id = Column(PGUUID, ForeignKey("chat_messages.id"), nullable=False)
    user_id = Column(PGUUID, ForeignKey("users.id"), nullable=False)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    read_at = Column(DateTime)

    message = relationship("ChatMessage", back_populates="receipts")
    user = relationship("User", back_populates="chat_receipts")