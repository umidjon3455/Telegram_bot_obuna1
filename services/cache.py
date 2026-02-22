"""
Cache layer without Redis.
- FSM storage and caching simulated in-memory
"""
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

_cache = {}
SUBSCRIPTION_TTL = 60  # seconds
import aioredis
from config import config

_redis = None

async def init_redis():
    global _redis
    if not config.REDIS_URL:
        _redis = None
    else:
        _redis = await aioredis.from_url(config.REDIS_URL)
    return _redis
############################

async def cache_subscription(user_id: int, result: bool):
    _cache[f"sub:{user_id}"] = {"value": result, "ttl": SUBSCRIPTION_TTL}

async def get_cached_subscription(user_id: int) -> Optional[bool]:
    entry = _cache.get(f"sub:{user_id}")
    if not entry:
        return None
    return entry["value"]

async def invalidate_subscription(user_id: int):
    _cache.pop(f"sub:{user_id}", None)

# ─── Video cache ──────────────────────────────────────────────────────────────
VIDEO_TTL = 300  # 5 minutes

async def cache_video(code: str, data: dict):
    _cache[f"video:{code}"] = {"value": json.dumps(data, default=str), "ttl": VIDEO_TTL}

async def get_cached_video(code: str) -> Optional[dict]:
    entry = _cache.get(f"video:{code}")
    if not entry:
        return None
    return json.loads(entry["value"])

async def invalidate_video(code: str):
    _cache.pop(f"video:{code}", None)

# ─── Ban cache ────────────────────────────────────────────────────────────────
BAN_TTL = 120

async def cache_ban_status(user_id: int, banned: bool):
    _cache[f"ban:{user_id}"] = {"value": banned, "ttl": BAN_TTL}

async def get_cached_ban(user_id: int) -> Optional[bool]:
    entry = _cache.get(f"ban:{user_id}")
    if not entry:
        return None
    return entry["value"]

async def invalidate_ban(user_id: int):
    _cache.pop(f"ban:{user_id}", None)

# ─── Broadcast progress ───────────────────────────────────────────────────────
async def set_broadcast_progress(sent: int, failed: int, total: int):
    _cache["broadcast:progress"] = {"sent": sent, "failed": failed, "total": total}

async def get_broadcast_progress() -> Optional[dict]:
    entry = _cache.get("broadcast:progress")
    if not entry:
        return None
    return entry

async def clear_broadcast_progress():
    _cache.pop("broadcast:progress", None)
