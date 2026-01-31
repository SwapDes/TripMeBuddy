import redis.asyncio as redis
from typing import Optional
from app.core.config import settings

# Create async Redis client
redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """
    Get async Redis client instance.
    Creates connection on first call, reuses for subsequent calls.
    """
    global redis_client

    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    return redis_client


async def close_redis():
    """
    Close Redis connection.
    Should be called on application shutdown.
    """
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
