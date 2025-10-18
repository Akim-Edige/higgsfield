"""SSE (Server-Sent Events) broker for real-time updates."""
import asyncio
import json
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class SSEBroker:
    """
    Simple in-memory SSE broker.
    
    In production, this should use Redis pub/sub for horizontal scaling.
    """

    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = {}

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        """Publish event to channel."""
        if channel not in self._subscribers:
            return

        logger.debug("sse_publish", channel=channel, event=event)

        # Send to all subscribers
        dead_queues = []
        for queue in self._subscribers[channel]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)
            except Exception as e:
                logger.error("sse_publish_error", error=str(e))
                dead_queues.append(queue)

        # Clean up dead queues
        for queue in dead_queues:
            self._subscribers[channel].remove(queue)

    async def subscribe(self, channel: str) -> asyncio.Queue:
        """Subscribe to channel."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(queue)
        logger.debug("sse_subscribe", channel=channel, subscriber_count=len(self._subscribers[channel]))
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from channel."""
        if channel in self._subscribers and queue in self._subscribers[channel]:
            self._subscribers[channel].remove(queue)
            logger.debug("sse_unsubscribe", channel=channel, subscriber_count=len(self._subscribers[channel]))


# Global broker instance
_broker: SSEBroker | None = None


def get_sse_broker() -> SSEBroker:
    """Get global SSE broker instance."""
    global _broker
    if _broker is None:
        _broker = SSEBroker()
    return _broker

