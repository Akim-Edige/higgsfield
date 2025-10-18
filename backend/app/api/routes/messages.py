"""Message routes."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id_dep, get_db_dep
from app.domain.models import Chat, Message, Option
from app.domain.pagination import encode_cursor
from app.domain.schemas import (
    ButtonChunk,
    MessageCreate,
    MessageOut,
    MessageWithOptions,
    PaginatedResponse,
    TextChunk,
)
from app.domain.states import AuthorType
from app.services.chat_service import ChatService
from app.services.recommender import Recommender

router = APIRouter(tags=["messages"])


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
    stmt = select(Message).where(Message.chat_id == chat_id)

    # TODO: Implement cursor decoding and keyset filtering
    # For now, simple limit-based query
    stmt = stmt.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    has_more = len(messages) > limit
    items = list(reversed(messages[:limit]))  # Reverse to show oldest first

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor({"created_at": last.created_at, "id": str(last.id)})

    return PaginatedResponse(
        items=[MessageOut.model_validate(m) for m in items],
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

    # Create user message (if text provided)
    if data.text:
        user_msg = await ChatService.create_message(
            db, chat_id, AuthorType.USER.value, content_text=data.text
        )

    # Generate options
    has_attachment = bool(data.attachments)
    options = Recommender.generate_options(data.text, has_attachment=has_attachment)

    # Create assistant message first (without render_payload)
    assistant_msg = await ChatService.create_message(
        db, chat_id, AuthorType.ASSISTANT.value
    )

    # Build render chunks and persist options
    render_chunks = []
    render_payload = []

    for i, opt in enumerate(options):
        # Create and persist option first
        option_model = Option(
            id=uuid.uuid4(),
            message_id=assistant_msg.id,
            rank=opt.rank,
            tool_type=opt.tool_type,
            model_key=opt.model_key,
            parameters=opt.parameters,
            enhanced_prompt=opt.enhanced_prompt,
            reason=opt.reason,
            confidence=opt.confidence,
            est_cost=opt.est_cost,
            est_latency_ms=opt.est_latency_ms,
            requires_attachment=opt.requires_attachment,
        )
        db.add(option_model)
        await db.flush()

        # Add descriptive text
        text_chunk = TextChunk(text=f"{opt.reason}")
        render_chunks.append(text_chunk)
        render_payload.append(text_chunk.model_dump())

        # Add button with actual option_id
        button_chunk = ButtonChunk(
            label=f"Generate ({opt.tool_type.replace('_', ' ').title()})",
            option_id=option_model.id,
        )
        render_chunks.append(button_chunk)
        # Convert UUID to string for JSON serialization
        button_dict = button_chunk.model_dump()
        button_dict["option_id"] = str(button_dict["option_id"])
        render_payload.append(button_dict)

    # Update assistant message with final render_payload
    assistant_msg.render_payload = render_payload

    await db.commit()

    return MessageWithOptions(
        message=MessageOut.model_validate(assistant_msg),
        render_chunks=render_chunks,
    )

