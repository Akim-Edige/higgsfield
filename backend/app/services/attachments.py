"""Attachments service for S3 presigned URLs."""
import uuid
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.infra.s3 import rewrite_to_public, s3_client_internal
from app.core.config import settings

logger = get_logger(__name__)


class AttachmentsService:
    """Handles attachment uploads via presigned URLs."""

    @staticmethod
    def presign_put(
        file_name: str,
        content_type: str,
        size: int,
    ) -> dict[str, str]:
        """
        Generate presigned PUT URL for upload.
        
        Args:
            file_name: Original file name
            content_type: MIME type
            size: File size in bytes
        
        Returns:
            {
                "upload_url": "...",
                "download_url": "...",
                "upload_id": "..."
            }
        """
        # Validate size (100 MB max)
        max_size = 100 * 1024 * 1024
        if size > max_size:
            raise ValueError(f"File size {size} exceeds maximum {max_size}")

        # Generate unique key
        upload_id = uuid.uuid4()
        key = f"uploads/{upload_id}/{file_name}"

        # Get S3 client
        s3 = s3_client_internal()

        # Generate presigned URL for PUT
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=3600,  # 1 hour
        )

        # Generate download URL (not presigned, public bucket)
        download_url = f"{settings.S3_ENDPOINT_INTERNAL}/{settings.S3_BUCKET}/{key}"

        # Rewrite to public endpoint
        upload_url_public = rewrite_to_public(upload_url)
        download_url_public = rewrite_to_public(download_url)

        logger.info(
            "presigned_url_generated",
            upload_id=str(upload_id),
            file_name=file_name,
            content_type=content_type,
            size=size,
        )

        return {
            "upload_url": upload_url_public,
            "download_url": download_url_public,
            "upload_id": str(upload_id),
        }

