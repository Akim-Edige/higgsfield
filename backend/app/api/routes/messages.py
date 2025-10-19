"""Message routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.api.deps import get_current_user_id_dep, get_db_dep
from app.core.logging import get_logger
from app.domain.models import Chat, Message, Option
from app.domain.pagination import encode_cursor
from app.domain.schemas import (
    AttachmentOut,
    ButtonChunk,
    MessageCreate,
    MessageOut,
    MessageWithOptions,
    PaginatedResponse,
    TextChunk,
)
from app.domain.states import AuthorType
from app.services.chat_service import ChatService
from app.services.claude_recommender import ClaudeRecommender
from app.services.response_parser import parse_claude_options_list

router = APIRouter(tags=["messages"])
logger = get_logger(__name__)


@router.get("/chats/{chat_id}/messages", response_model=PaginatedResponse)
async def list_messages(
    chat_id: UUID,
    after: str | None = None,
    limit: int = 50,
    user_id: UUID = Depends(get_current_user_id_dep),
    db: AsyncSession = Depends(get_db_dep),
) -> PaginatedResponse:
    """List messages in a chat with keyset pagination."""
    # Verify chat belongs to user
    chat_stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
    chat_result = await db.execute(chat_stmt)
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Keyset pagination by (created_at desc, id desc)
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .options(selectinload(Message.attachments))
    )

    # TODO: Implement cursor decoding and keyset filtering
    # For now, simple limit-based query
    stmt = stmt.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    messages = result.scalars().unique().all()
    
    logger.info(
        "list_messages_query",
        chat_id=str(chat_id),
        found_count=len(messages),
        message_ids=[str(m.id) for m in messages],
    )

    has_more = len(messages) > limit
    items = list(reversed(messages[:limit]))  # Reverse to show oldest first

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor({"created_at": last.created_at, "id": str(last.id)})

    # Map attachments into schema
    items_out: list[MessageOut] = []
    for m in items:
        msg = MessageOut.model_validate(m)
        msg.attachments = [
            AttachmentOut.model_validate(a) for a in getattr(m, "attachments", [])
        ]
        items_out.append(msg)

    return PaginatedResponse(
        items=items_out,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.post("/chats/{chat_id}/messages", response_model=MessageWithOptions, status_code=201)
async def create_message(
    chat_id: UUID,
    data: MessageCreate,
    user_id: UUID = Depends(get_current_user_id_dep),
    db: AsyncSession = Depends(get_db_dep),
) -> MessageWithOptions:
    """
    Create a user message and generate assistant response with options.
    """
    # Verify chat belongs to user
    chat_stmt = select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
    chat_result = await db.execute(chat_stmt)
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Create user message if text or attachments are provided
    user_msg = None
    if data.text or (data.attachments and len(data.attachments) > 0):
        user_msg = await ChatService.create_message(
            db, chat_id, AuthorType.USER.value, content_text=data.text
        )
        await db.flush()
        logger.info("user_message_created", message_id=str(user_msg.id), chat_id=str(chat_id))

        # If there are attachment URLs, create attachment rows
        if data.attachments:
            for url in data.attachments:
                await ChatService.create_attachment(
                    db,
                    user_id=user_id,
                    chat_id=chat_id,
                    message_id=user_msg.id,
                    storage_url=url,
                )

    # Create assistant message first (will be updated with render_payload)
    # Ensure assistant message is slightly later to avoid identical timestamps
    assistant_msg = await ChatService.create_message(
        db, chat_id, AuthorType.ASSISTANT.value, created_at=datetime.utcnow()
    )
    await db.flush()
    logger.info("assistant_message_created", message_id=str(assistant_msg.id), chat_id=str(chat_id))

    # Generate options using Claude LLM
    has_attachment = bool(data.attachments)
    
    # Use Claude-powered recommender for intelligent style selection
    claude_results = await ClaudeRecommender.generate_options_with_claude(
        text=data.text or "Create something creative",
        message_id=assistant_msg.id,
        db=db,
        has_attachment=has_attachment
    )

    # Parse Claude results into render chunks using dedicated parser
    render_chunks = parse_claude_options_list(claude_results)
    
    # Convert render chunks to serializable format for render_payload
    render_payload = []
    for chunk in render_chunks:
        chunk_dict = chunk.model_dump()
        # Convert UUID to string for JSON serialization
        if isinstance(chunk, ButtonChunk):
            chunk_dict["option_id"] = str(chunk_dict["option_id"])
        render_payload.append(chunk_dict)

    # Update assistant message with final render_payload
    assistant_msg.render_payload = render_payload
    
    # Flush to ensure data is in transaction
    await db.flush()
    
    # IMPORTANT: Explicit commit to ensure data is persisted
    await db.commit()
    
    logger.info(
        "messages_committed_to_db", 
        chat_id=str(chat_id), 
        user_msg_id=str(user_msg.id) if user_msg else None,
        assistant_msg_id=str(assistant_msg.id)
    )

    # Build response without triggering lazy relationship loads
    message_dict = {
        "id": assistant_msg.id,
        "chat_id": assistant_msg.chat_id,
        "author_type": assistant_msg.author_type,
        "content_text": assistant_msg.content_text,
        "render_payload": assistant_msg.render_payload,
        "created_at": assistant_msg.created_at,
        "attachments": [],
    }

    return MessageWithOptions(
        message=MessageOut.model_validate(message_dict)
    )

