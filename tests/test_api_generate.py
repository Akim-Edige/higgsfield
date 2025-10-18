"""Test generation API endpoints."""
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_generate_with_idempotency(client: AsyncClient):
    """Test that generate endpoint is idempotent."""
    # Create chat and message
    response = await client.post("/chats", json={"title": "Gen Test"})
    chat = response.json()
    chat_id = chat["id"]

    response = await client.post(
        f"/chats/{chat_id}/messages",
        json={"text": "beautiful landscape"},
    )
    data = response.json()
    render_chunks = data["render_chunks"]

    # Get first button's option_id
    button = next(c for c in render_chunks if c["type"] == "button")
    option_id = button["option_id"]

    # Generate with idempotency key
    idem_key = str(uuid.uuid4())
    headers = {"Idempotency-Key": idem_key}

    response1 = await client.post(
        f"/options/{option_id}/generate",
        headers=headers,
    )
    assert response1.status_code == 202
    data1 = response1.json()
    job_id_1 = data1["job_id"]

    # Repeat with same idempotency key
    response2 = await client.post(
        f"/options/{option_id}/generate",
        headers=headers,
    )
    assert response2.status_code == 202
    data2 = response2.json()
    job_id_2 = data2["job_id"]

    # Should return the same job_id
    assert job_id_1 == job_id_2


@pytest.mark.asyncio
async def test_generate_without_idempotency_key_fails(client: AsyncClient):
    """Test that generate endpoint requires idempotency key."""
    # Create chat and message
    response = await client.post("/chats", json={"title": "Gen Test 2"})
    chat = response.json()
    chat_id = chat["id"]

    response = await client.post(
        f"/chats/{chat_id}/messages",
        json={"text": "test"},
    )
    data = response.json()
    button = next(c for c in data["render_chunks"] if c["type"] == "button")
    option_id = button["option_id"]

    # Generate without idempotency key
    response = await client.post(f"/options/{option_id}/generate")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_job_status(client: AsyncClient):
    """Test getting job status."""
    # Create chat, message, and job
    response = await client.post("/chats", json={"title": "Job Test"})
    chat = response.json()
    chat_id = chat["id"]

    response = await client.post(
        f"/chats/{chat_id}/messages",
        json={"text": "test"},
    )
    data = response.json()
    button = next(c for c in data["render_chunks"] if c["type"] == "button")
    option_id = button["option_id"]

    idem_key = str(uuid.uuid4())
    response = await client.post(
        f"/options/{option_id}/generate",
        headers={"Idempotency-Key": idem_key},
    )
    job_data = response.json()
    job_id = job_data["job_id"]

    # Get job status
    response = await client.get(f"/options/jobs/{job_id}")
    assert response.status_code == 200
    job = response.json()

    assert "job_id" in job
    assert "status" in job
    assert "retry_after_seconds" in job
    assert job["status"] in ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "TIMEOUT"]

