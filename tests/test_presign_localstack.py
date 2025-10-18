"""Test S3 presigned URL generation with LocalStack."""
import pytest

from app.core.config import settings
from app.infra.s3 import rewrite_to_public


def test_rewrite_to_public_endpoint():
    """Test URL rewriting from internal to public endpoint."""
    # Internal URL
    internal_url = f"{settings.S3_ENDPOINT_INTERNAL}/media/uploads/123/test.jpg?signature=abc"

    # Rewrite to public
    public_url = rewrite_to_public(internal_url)

    # Should contain public endpoint
    assert settings.S3_PUBLIC_ENDPOINT.replace("http://", "").split(":")[0] in public_url
    assert "test.jpg" in public_url
    assert "signature=abc" in public_url


def test_rewrite_preserves_non_internal_urls():
    """Test that non-internal URLs are not modified."""
    external_url = "https://example.com/file.jpg"
    result = rewrite_to_public(external_url)
    assert result == external_url


@pytest.mark.asyncio
async def test_presign_upload():
    """Test presign upload endpoint."""
    from httpx import AsyncClient
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/attachments/presign",
            json={
                "file_name": "test.png",
                "content_type": "image/png",
                "size": 1024000,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "upload_url" in data
        assert "download_url" in data
        assert "upload_id" in data

        # URLs should use public endpoint
        assert "localhost:4566" in data["upload_url"] or "localstack:4566" in data["upload_url"]

