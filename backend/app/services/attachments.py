"""Attachments service for S3 presigned URLs."""
import uuid
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.infra.s3 import rewrite_to_public, s3_client_internal, get_public_url
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
        Generate presigned PUT URL for upload and public/presigned URL for download.
        
        For hackathon simplicity: if USE_PUBLIC_URLS=True, returns permanent public URLs
        for downloads (requires public bucket in Yandex Cloud).
        
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

        # Generate presigned URL for PUT (always needed for upload)
        upload_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=3600,  # 1 hour
        )

        # Generate download URL
        if settings.USE_PUBLIC_URLS:
            # Simple public URL (permanent, no expiration)
            download_url = get_public_url(settings.S3_BUCKET, key)
        else:
            # Presigned URL (temporary, with expiration)
            download_url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.S3_BUCKET,
                    "Key": key,
                },
                ExpiresIn=86400,  # 24 hours
            )
            download_url = rewrite_to_public(download_url)

        # Rewrite upload URL to public endpoint
        upload_url_public = rewrite_to_public(upload_url)

        logger.info(
            "presigned_url_generated",
            upload_id=str(upload_id),
            file_name=file_name,
            content_type=content_type,
            size=size,
            use_public_urls=settings.USE_PUBLIC_URLS,
        )

        return {
            "upload_url": upload_url_public,
            "download_url": download_url,
            "upload_id": str(upload_id),
        }

