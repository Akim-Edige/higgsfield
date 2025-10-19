"""Attachment routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user_id_dep, get_db_dep
from app.domain.models import Attachment, Chat
from app.domain.schemas import PresignIn, PresignOut, AttachmentOut, PaginatedResponse
from app.services.attachments import AttachmentsService

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post("/presign", response_model=PresignOut)
async def presign_upload(
    data: PresignIn,
    user_id: UUID = Depends(get_current_user_id_dep),
) -> PresignOut:
    """
    Generate presigned URL for file upload to S3.
    
    Returns URLs rewritten to use public endpoint (localhost:4566 for browser).
    """
    try:
        result = AttachmentsService.presign_put(
            file_name=data.file_name,
            content_type=data.content_type,
            size=data.size,
        )
        return PresignOut(
            upload_url=result["upload_url"],
            download_url=result["download_url"],
            upload_id=UUID(result["upload_id"]),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/by-chat/{chat_id}", response_model=PaginatedResponse)
async def list_chat_attachments(
    chat_id: UUID,
    after: str | None = None,
    limit: int = 50,
    user_id: UUID = Depends(get_current_user_id_dep),
    db: AsyncSession = Depends(get_db_dep),
) -> PaginatedResponse:
    """List attachments for a chat with simple pagination (newest first)."""
    # Verify chat belongs to user
    chat = await db.get(Chat, chat_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(status_code=404, detail="Chat not found")

    stmt = (
        select(Attachment)
        .where(Attachment.chat_id == chat_id)
        .order_by(Attachment.created_at.desc(), Attachment.id.desc())
        .limit(limit + 1)
    )

    result = await db.execute(stmt)
    rows = result.scalars().all()
    has_more = len(rows) > limit
    items = rows[:limit]

    # TODO: implement cursor-based 'after' pagination
    next_cursor = None

    return PaginatedResponse(
        items=[AttachmentOut.model_validate(a) for a in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )

