"""Chat routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id_dep, get_db_dep
from app.domain.models import Chat
from app.domain.pagination import encode_cursor
from app.domain.schemas import ChatCreate, ChatOut, PaginatedResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatOut, status_code=201)
async def create_chat(
    data: ChatCreate,
    user_id: UUID = Depends(get_current_user_id_dep),
    db: AsyncSession = Depends(get_db_dep),
) -> ChatOut:
    """Create a new chat."""
    chat = await ChatService.create_chat(db, user_id, data.title)
    await db.commit()
    return ChatOut.model_validate(chat)


@router.get("", response_model=PaginatedResponse)
async def list_chats(
    cursor: str | None = None,
    limit: int = 20,
    user_id: UUID = Depends(get_current_user_id_dep),
    db: AsyncSession = Depends(get_db_dep),
) -> PaginatedResponse:
    """List chats with keyset pagination."""
    # Keyset pagination by (created_at desc, id desc)
    stmt = select(Chat).where(Chat.user_id == user_id)

    # For now, simple limit-based query
    stmt = stmt.order_by(Chat.created_at.desc(), Chat.id.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    chats = result.scalars().all()

    has_more = len(chats) > limit
    items = chats[:limit]

    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor({"created_at": last.created_at, "id": str(last.id)})

    return PaginatedResponse(
        items=[ChatOut.model_validate(c) for c in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )

