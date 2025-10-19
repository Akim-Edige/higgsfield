"""Chat service for managing chats and messages."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Chat, Message, Attachment
from app.domain.states import AttachmentKind
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

    @staticmethod
    async def create_attachment(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        chat_id: uuid.UUID,
        message_id: uuid.UUID | None,
        storage_url: str,
        option_id: uuid.UUID | None = None,
        kind: str | None = None,
        mime: str | None = None,
        size_bytes: int | None = None,
        width: int | None = None,
        height: int | None = None,
        duration_ms: int | None = None,
        provider_url: str | None = None,
        meta: dict | None = None,
    ) -> Attachment:
        """Create an attachment row for a message/chat.

        The frontend currently sends a list of URLs; we'll infer kind from MIME if provided,
        otherwise default to image when URL looks like an image, else other.
        """
        detected_kind = kind
        if detected_kind is None:
            if mime and mime.startswith("image/"):
                detected_kind = AttachmentKind.IMAGE.value
            elif mime and mime.startswith("video/"):
                detected_kind = AttachmentKind.VIDEO.value
            else:
                # naive inference from URL
                lower = storage_url.lower()
                if lower.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                    detected_kind = AttachmentKind.IMAGE.value
                elif lower.endswith((".mp4", ".mov", ".webm", ".mkv")):
                    detected_kind = AttachmentKind.VIDEO.value
                else:
                    detected_kind = AttachmentKind.OTHER.value

        attachment = Attachment(
            id=uuid.uuid4(),
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            kind=detected_kind,
            mime=mime or "application/octet-stream",
            size_bytes=size_bytes or 0,
            storage_url=storage_url,
            option_id=option_id,
            provider_url=provider_url,
            width=width,
            height=height,
            duration_ms=duration_ms,
            meta=meta or {},
        )
        db.add(attachment)
        await db.flush()
        return attachment

