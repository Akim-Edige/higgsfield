"""SSE (Server-Sent Events) routes for real-time updates."""
import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user_id_dep
from app.services.sse_broker import get_sse_broker

router = APIRouter(prefix="/sse", tags=["sse"])


@router.get("/{chat_id}")
async def sse_chat_events(
    chat_id: UUID,
    user_id: UUID = Depends(get_current_user_id_dep),
):
    """
    SSE endpoint for chat events.
    
    Events:
    - message.created: New message in chat
    - option.created: New option generated
    - job.updated: Generation job status update
    """
    broker = get_sse_broker()
    channel = f"chat:{user_id}"

    async def event_generator():
        queue = await broker.subscribe(channel)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": event.get("type", "message"),
                        "data": event,
                    }
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    yield {
                        "event": "ping",
                        "data": {"type": "ping"},
                    }
        except asyncio.CancelledError:
            await broker.unsubscribe(channel, queue)
            raise

    return EventSourceResponse(event_generator())

