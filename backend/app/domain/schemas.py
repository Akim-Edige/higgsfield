"""Pydantic schemas for API requests and responses."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Render Chunks
# ============================================================================


class TextChunk(BaseModel):
    """Text chunk for rendering."""

    type: Literal["text"] = "text"
    text: str


class ButtonChunk(BaseModel):
    """Button chunk for rendering."""

    type: Literal["button"] = "button"
    label: str
    option_id: UUID


RenderChunk = TextChunk | ButtonChunk


# ============================================================================
# Users
# ============================================================================


class UserOut(BaseModel):
    """User output schema."""

    id: UUID
    handle: str | None
    role: str
    credit_balance: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Chats
# ============================================================================


class ChatCreate(BaseModel):
    """Chat creation schema."""

    title: str | None = None


class ChatOut(BaseModel):
    """Chat output schema."""

    id: UUID
    user_id: UUID
    title: str | None
    message_count: int
    last_message_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Messages
# ============================================================================


class MessageCreate(BaseModel):
    """Message creation schema."""

    text: str | None = None
    attachments: list[str] | None = Field(default_factory=list)


class MessageOut(BaseModel):
    """Message output schema."""

    id: UUID
    chat_id: UUID
    author_type: str
    content_text: str | None
    render_payload: list[dict[str, Any]] | None
    created_at: datetime
    attachments: list["AttachmentOut"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MessageWithOptions(BaseModel):
    """Message with options response."""

    message: MessageOut


# ============================================================================
# Options
# ============================================================================


class OptionOut(BaseModel):
    """Option output schema."""

    id: UUID
    message_id: UUID
    tool_type: str
    style_id: str
    model_key: str
    enhanced_prompt: str
    reason: str
    result_url: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Jobs
# ============================================================================


class JobCreateResponse(BaseModel):
    """Job creation response."""

    job_id: UUID


class JobResult(BaseModel):
    """Job result schema."""

    min_url: str | None = None
    raw_url: str | None = None
    mime: str | None = None
    size_bytes: int | None = None
    thumbnails: list[str] = Field(default_factory=list)


class ErrorOut(BaseModel):
    """Error output schema."""

    code: str
    message: str


class JobOut(BaseModel):
    """Job output schema."""

    job_id: UUID
    status: str
    result: JobResult | None = None
    error: ErrorOut | None = None
    retry_after_seconds: int = 10


# ============================================================================
# Attachments
# ============================================================================


class PresignIn(BaseModel):
    """Presign upload request."""

    file_name: str
    content_type: str
    size: int


class PresignOut(BaseModel):
    """Presign upload response."""

    upload_url: str
    download_url: str
    upload_id: UUID


class AttachmentOut(BaseModel):
    """Attachment output schema."""

    id: UUID
    kind: str
    mime: str
    size_bytes: int
    storage_url: str
    option_id: UUID | None = None
    width: int | None
    height: int | None
    duration_ms: int | None
    blurhash: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Pagination
# ============================================================================


class PaginatedResponse(BaseModel):
    """Generic paginated response."""

    items: list[Any]
    next_cursor: str | None = None
    has_more: bool = False

