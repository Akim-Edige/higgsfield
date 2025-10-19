"""Chat service for managing chats and messages."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Chat, Message
from app.domain.states import AuthorType


class ChatService:
    """Service for chat operations."""

    @staticmethod
    async def create_chat(db: AsyncSession, user_id: uuid.UUID, title: str | None = None) -> Chat:
        """Create a new chat."""
        chat = Chat(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title,
            message_count=0,
        )
        db.add(chat)
        await db.flush()
        return chat

    @staticmethod
    async def create_message(
        db: AsyncSession,
        chat_id: uuid.UUID,
        author_type: str,
        content_text: str | None = None,
        render_payload: list | None = None,
        created_at: datetime | None = None,
    ) -> Message:
        """Create a new message."""
        message = Message(
            id=uuid.uuid4(),
            chat_id=chat_id,
            author_type=author_type,
            content_text=content_text,
            render_payload=render_payload,
            created_at=created_at or datetime.utcnow(),
        )
        db.add(message)

        # Update chat message count and last_message_at
        chat_stmt = select(Chat).where(Chat.id == chat_id)
        result = await db.execute(chat_stmt)
        chat = result.scalar_one_or_none()
        if chat:
            chat.message_count += 1
            chat.last_message_at = datetime.utcnow()

        await db.flush()
        return message

