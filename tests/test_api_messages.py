"""Test message API endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_message_generates_options(client: AsyncClient):
    """Test that posting a message generates ≥2 options."""
    # Create chat first
    response = await client.post("/chats", json={"title": "Test Chat"})
    assert response.status_code == 201
    chat = response.json()
    chat_id = chat["id"]

    # Create user message
    response = await client.post(
        f"/chats/{chat_id}/messages",
        json={"text": "cinematic sunset over mountains", "attachments": []},
    )
    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "message" in data
    assert "render_chunks" in data

    message = data["message"]
    assert message["author_type"] == "assistant"
    assert message["render_payload"] is not None

    # Verify we have at least 2 options (text + button pairs)
    render_chunks = data["render_chunks"]
    assert len(render_chunks) >= 4  # At least 2 text+button pairs

    # Verify structure of render chunks
    button_chunks = [c for c in render_chunks if c["type"] == "button"]
    assert len(button_chunks) >= 2

    for button in button_chunks:
        assert "label" in button
        assert "option_id" in button


@pytest.mark.asyncio
async def test_list_messages(client: AsyncClient):
    """Test listing messages in a chat."""
    # Create chat
    response = await client.post("/chats", json={"title": "Test Chat 2"})
    assert response.status_code == 201
    chat = response.json()
    chat_id = chat["id"]

    # Create message
    await client.post(
        f"/chats/{chat_id}/messages",
        json={"text": "test message"},
    )

    # List messages
    response = await client.get(f"/chats/{chat_id}/messages")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert len(data["items"]) >= 1

