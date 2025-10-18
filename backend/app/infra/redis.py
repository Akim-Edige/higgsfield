"""Redis infrastructure for caching and pub/sub."""
import redis.asyncio as redis

from app.core.config import settings

# Redis client
_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    """Close Redis client."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None

