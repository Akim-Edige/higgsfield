"""Attachment routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user_id_dep
from app.domain.schemas import PresignIn, PresignOut
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

