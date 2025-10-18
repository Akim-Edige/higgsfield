"""S3 infrastructure with Yandex Cloud / AWS S3 support and URL rewriting."""
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


def get_public_url(bucket: str, key: str) -> str:
    """
    Generate permanent public URL for an object in a public bucket.
    
    For Yandex Cloud Object Storage:
    - Virtual-hosted style: https://{bucket}.storage.yandexcloud.net/{key}
    - Path style: https://storage.yandexcloud.net/{bucket}/{key}
    
    Args:
        bucket: S3 bucket name
        key: Object key
        
    Returns:
        Public URL (no signature, no expiration)
    """
    endpoint = settings.S3_PUBLIC_ENDPOINT.rstrip('/')
    
    # Parse endpoint to get scheme and host
    parsed = urlparse(endpoint)
    
    if settings.S3_USE_PATH_STYLE:
        # Path style: https://storage.yandexcloud.net/{bucket}/{key}
        return f"{endpoint}/{bucket}/{key}"
    else:
        # Virtual-hosted style: https://{bucket}.storage.yandexcloud.net/{key}
        # Replace the host with bucket.host
        host = parsed.netloc
        return f"{parsed.scheme}://{bucket}.{host}/{key}"


def rewrite_to_public(url: str) -> str:
    """
    Rewrite S3 URL from internal endpoint to public endpoint.
    
    This allows the backend to generate presigned URLs using the internal
    endpoint but return URLs that work from the browser.
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

