"""Redis-backed cache helpers used by the Telegram bot."""
import json
import logging
from typing import Optional

from redis.asyncio import Redis

from config import config

logger = logging.getLogger(__name__)
SUBSCRIPTION_TTL = 60
VIDEO_TTL = 300
BAN_TTL = 120
_redis: Optional[Redis] = None


async def init_redis() -> Redis:
    """Create and verify the shared Redis connection."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(config.REDIS_URL, decode_responses=True)
    await _redis.ping()
    return _redis


def get_redis() -> Redis:
    """Return the initialized Redis connection."""
    if _redis is None:
        raise RuntimeError("Redis has not been initialized. Call init_redis() first.")
    return _redis


async def close_redis() -> None:
    """Close the shared Redis connection during application shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def cache_subscription(user_id: int, result: bool):
    await get_redis().setex(f"sub:{user_id}", SUBSCRIPTION_TTL, json.dumps(result))


async def get_cached_subscription(user_id: int) -> Optional[bool]:
    value = await get_redis().get(f"sub:{user_id}")
    return None if value is None else json.loads(value)


async def invalidate_subscription(user_id: int):
    await get_redis().delete(f"sub:{user_id}")


async def cache_video(code: str, data: dict):
    await get_redis().setex(f"video:{code}", VIDEO_TTL, json.dumps(data, default=str))


async def get_cached_video(code: str) -> Optional[dict]:
    value = await get_redis().get(f"video:{code}")
    return None if value is None else json.loads(value)


async def invalidate_video(code: str):
    await get_redis().delete(f"video:{code}")


async def cache_ban_status(user_id: int, banned: bool):
    await get_redis().setex(f"ban:{user_id}", BAN_TTL, json.dumps(banned))


async def get_cached_ban(user_id: int) -> Optional[bool]:
    value = await get_redis().get(f"ban:{user_id}")
    return None if value is None else json.loads(value)


async def invalidate_ban(user_id: int):
    await get_redis().delete(f"ban:{user_id}")


async def set_broadcast_progress(sent: int, failed: int, total: int):
    await get_redis().hset("broadcast:progress", mapping={"sent": sent, "failed": failed, "total": total})


async def get_broadcast_progress() -> Optional[dict]:
    value = await get_redis().hgetall("broadcast:progress")
    return None if not value else {key: int(item) for key, item in value.items()}


async def clear_broadcast_progress():
    await get_redis().delete("broadcast:progress")
