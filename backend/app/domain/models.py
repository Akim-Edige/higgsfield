"""SQLAlchemy models for all database tables."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    handle: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    role: Mapped[str] = mapped_column(String, default="user")
    credit_balance: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    flags: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=datetime.utcnow
    )

    # Relationships
    chats: Mapped[list["Chat"]] = relationship("Chat", back_populates="user")
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="user")

class Chat(Base):
    """Chat model."""

    __tablename__ = "chats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chats")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="chat")
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="chat")

    __table_args__ = (
        Index("ix_chats_user_created", "user_id", "created_at", "id"),
        Index("ix_chats_user_last_message", "user_id", "last_message_at", "id"),
    )


class Message(Base):
    """Message model."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False, index=True
    )
    author_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # 'user', 'assistant', 'system'
    role: Mapped[Optional[str]] = mapped_column(String)
    content_text: Mapped[Optional[str]] = mapped_column(Text)
    render_payload: Mapped[Optional[list]] = mapped_column(JSONB)  # Array of UI chunks
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")
    options: Mapped[list["Option"]] = relationship("Option", back_populates="message")
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="message")

    __table_args__ = (Index("ix_messages_chat_created", "chat_id", "created_at", "id"),)


class Attachment(Base):
    """Attachment model."""

    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    chat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False, index=True)
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)  # 'image', 'video', 'other'
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=True)
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    provider_url: Mapped[Optional[str]] = mapped_column(Text)
    option_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("options.id"), nullable=True, index=True
    )
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    meta: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="attachments")
    chat: Mapped["Chat"] = relationship("Chat", back_populates="attachments")
    message: Mapped["Message"] = relationship("Message", back_populates="attachments")

    __table_args__ = (
        Index("ix_attachments_message", "message_id"),
        Index("ix_attachments_chat_created", "chat_id", "created_at")
    )


class Option(Base):
    """Option model - generation options presented to user."""

    __tablename__ = "options"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False, index=True
    )
    tool_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # 'text_to_image', 'image_to_video', etc.
    style_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)  # Style or motion ID
    model_key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    enhanced_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    result_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="options")
