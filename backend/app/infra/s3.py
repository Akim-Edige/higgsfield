"""S3 infrastructure with LocalStack support and URL rewriting."""
from urllib.parse import urlparse, urlunparse

import boto3

from app.core.config import settings


def s3_client_internal():
    """Get S3 client for internal use (backend/worker)."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_INTERNAL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
        config=boto3.session.Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if settings.S3_USE_PATH_STYLE else "virtual"},
        ),
    )


def rewrite_to_public(url: str) -> str:
    """
    Rewrite S3 URL from internal endpoint to public endpoint.
    
    This allows the backend to generate presigned URLs using the internal
    endpoint (e.g., http://localstack:4566) but return URLs that work
    from the browser (e.g., http://localhost:4566).
    """
    if not url:
        return url

    parsed = urlparse(url)
    internal_parsed = urlparse(settings.S3_ENDPOINT_INTERNAL)
    public_parsed = urlparse(settings.S3_PUBLIC_ENDPOINT)

    # If the URL uses the internal endpoint, rewrite to public
    if parsed.netloc == internal_parsed.netloc:
        return urlunparse((
            public_parsed.scheme,
            public_parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))

    return url

