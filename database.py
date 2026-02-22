"""
PostgreSQL database layer using asyncpg directly (no ORM overhead).
Connection pooling built-in for production performance.
"""
import logging
from typing import Optional, List, Tuple, Any
import asyncpg
from config import config

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return _pool


async def init_db():
    """Create connection pool and initialize schema."""
    global _pool
    # asyncpg uses its own DSN format (no +asyncpg prefix)
    dsn = config.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
    await _create_tables()
    logger.info("PostgreSQL pool initialized.")


async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def _create_tables():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          BIGSERIAL PRIMARY KEY,
                user_id     BIGINT UNIQUE NOT NULL,
                username    TEXT,
                full_name   TEXT NOT NULL DEFAULT '',
                is_banned   BOOLEAN NOT NULL DEFAULT FALSE,
                referrer_id BIGINT REFERENCES users(user_id),
                ref_count   INTEGER NOT NULL DEFAULT 0,
                joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS videos (
                id            BIGSERIAL PRIMARY KEY,
                code          TEXT UNIQUE NOT NULL,
                file_id       TEXT NOT NULL,
                title         TEXT,
                like_count    INTEGER NOT NULL DEFAULT 0,
                dislike_count INTEGER NOT NULL DEFAULT 0,
                view_count    INTEGER NOT NULL DEFAULT 0,
                added_by      BIGINT,
                added_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS reactions (
                id         BIGSERIAL PRIMARY KEY,
                user_id    BIGINT NOT NULL,
                video_id   BIGINT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
                reaction   TEXT NOT NULL CHECK(reaction IN ('like','dislike')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, video_id)
            );

            CREATE TABLE IF NOT EXISTS daily_stats (
                id         BIGSERIAL PRIMARY KEY,
                date       DATE NOT NULL DEFAULT CURRENT_DATE,
                new_users  INTEGER NOT NULL DEFAULT 0,
                messages   INTEGER NOT NULL DEFAULT 0,
                UNIQUE(date)
            );

            CREATE INDEX IF NOT EXISTS idx_users_user_id   ON users(user_id);
            CREATE INDEX IF NOT EXISTS idx_videos_code     ON videos(code);
            CREATE INDEX IF NOT EXISTS idx_reactions_uid   ON reactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);
        """)


# ─── USER ────────────────────────────────────────────────────────────────────

async def upsert_user(
    user_id: int,
    username: Optional[str],
    full_name: str,
    referrer_id: Optional[int] = None
) -> bool:
    """Returns True if it's a NEW user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchval(
                "SELECT user_id FROM users WHERE user_id = $1", user_id
            )
            if existing:
                await conn.execute("""
                    UPDATE users SET username=$1, full_name=$2 WHERE user_id=$3
                """, username, full_name, user_id)
                return False

            await conn.execute("""
                INSERT INTO users (user_id, username, full_name, referrer_id)
                VALUES ($1, $2, $3, $4)
            """, user_id, username, full_name, referrer_id)

            # credit referrer
            if referrer_id:
                await conn.execute("""
                    UPDATE users SET ref_count = ref_count + 1 WHERE user_id = $1
                """, referrer_id)

            # daily stats
            await conn.execute("""
                INSERT INTO daily_stats (date, new_users) VALUES (CURRENT_DATE, 1)
                ON CONFLICT (date) DO UPDATE SET new_users = daily_stats.new_users + 1
            """)
            return True


async def get_user(user_id: int) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    return dict(row) if row else None


async def get_user_count() -> int:
    pool = await get_pool()
    return await pool.fetchval("SELECT COUNT(*) FROM users WHERE is_banned = FALSE")


async def get_all_user_ids(include_banned: bool = False) -> List[int]:
    pool = await get_pool()
    if include_banned:
        rows = await pool.fetch("SELECT user_id FROM users")
    else:
        rows = await pool.fetch("SELECT user_id FROM users WHERE is_banned = FALSE")
    return [r["user_id"] for r in rows]


async def ban_user(user_id: int) -> bool:
    pool = await get_pool()
    result = await pool.execute(
        "UPDATE users SET is_banned = TRUE WHERE user_id = $1 AND is_banned = FALSE",
        user_id
    )
    return result.endswith("1")


async def unban_user(user_id: int) -> bool:
    pool = await get_pool()
    result = await pool.execute(
        "UPDATE users SET is_banned = FALSE WHERE user_id = $1 AND is_banned = TRUE",
        user_id
    )
    return result.endswith("1")


async def is_banned(user_id: int) -> bool:
    pool = await get_pool()
    val = await pool.fetchval("SELECT is_banned FROM users WHERE user_id = $1", user_id)
    return bool(val)


async def get_top_referrers(limit: int = 10) -> List[dict]:
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT user_id, username, full_name, ref_count
        FROM users WHERE ref_count > 0
        ORDER BY ref_count DESC LIMIT $1
    """, limit)
    return [dict(r) for r in rows]


# ─── VIDEO ───────────────────────────────────────────────────────────────────

async def add_video(code: str, file_id: str, title: Optional[str], added_by: int) -> bool:
    pool = await get_pool()
    try:
        await pool.execute("""
            INSERT INTO videos (code, file_id, title, added_by)
            VALUES ($1, $2, $3, $4)
        """, code, file_id, title, added_by)
        return True
    except asyncpg.UniqueViolationError:
        return False


async def get_video(code: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM videos WHERE code = $1", code)
    if row:
        # increment view count
        await pool.execute("UPDATE videos SET view_count = view_count + 1 WHERE code = $1", code)
    return dict(row) if row else None


async def get_video_by_id(video_id: int) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM videos WHERE id = $1", video_id)
    return dict(row) if row else None


async def get_video_count() -> int:
    pool = await get_pool()
    return await pool.fetchval("SELECT COUNT(*) FROM videos")


async def list_all_video_codes() -> List[dict]:
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT code, title, like_count, dislike_count, view_count
        FROM videos ORDER BY CAST(code AS INTEGER)
    """)
    return [dict(r) for r in rows]


async def delete_video(code: str) -> bool:
    pool = await get_pool()
    result = await pool.execute("DELETE FROM videos WHERE code = $1", code)
    return result.endswith("1")


# ─── REACTIONS ───────────────────────────────────────────────────────────────

async def get_user_reaction(user_id: int, video_id: int) -> Optional[str]:
    pool = await get_pool()
    return await pool.fetchval(
        "SELECT reaction FROM reactions WHERE user_id = $1 AND video_id = $2",
        user_id, video_id
    )


async def set_reaction(user_id: int, video_id: int, reaction: str) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchval(
                "SELECT reaction FROM reactions WHERE user_id=$1 AND video_id=$2",
                user_id, video_id
            )
            if existing == reaction:
                pass  # no change
            elif existing is None:
                await conn.execute(
                    "INSERT INTO reactions (user_id, video_id, reaction) VALUES ($1,$2,$3)",
                    user_id, video_id, reaction
                )
                col = "like_count" if reaction == "like" else "dislike_count"
                await conn.execute(f"UPDATE videos SET {col}={col}+1 WHERE id=$1", video_id)
            else:
                old = "like_count" if existing == "like" else "dislike_count"
                new = "like_count" if reaction == "like" else "dislike_count"
                await conn.execute(
                    "UPDATE reactions SET reaction=$1 WHERE user_id=$2 AND video_id=$3",
                    reaction, user_id, video_id
                )
                await conn.execute(f"UPDATE videos SET {old}={old}-1 WHERE id=$1", video_id)
                await conn.execute(f"UPDATE videos SET {new}={new}+1 WHERE id=$1", video_id)

            row = await conn.fetchrow(
                "SELECT like_count, dislike_count FROM videos WHERE id=$1", video_id
            )
            return {
                "like_count": row["like_count"],
                "dislike_count": row["dislike_count"],
                "user_reaction": reaction,
                "changed": existing != reaction
            }


# ─── STATS ───────────────────────────────────────────────────────────────────

async def get_daily_stats(days: int = 7) -> List[dict]:
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT date, new_users, messages
        FROM daily_stats
        WHERE date >= CURRENT_DATE - $1
        ORDER BY date ASC
    """, days)
    return [dict(r) for r in rows]


async def increment_message_count():
    pool = await get_pool()
    await pool.execute("""
        INSERT INTO daily_stats (date, messages) VALUES (CURRENT_DATE, 1)
        ON CONFLICT (date) DO UPDATE SET messages = daily_stats.messages + 1
    """)


async def get_full_stats() -> dict:
    pool = await get_pool()
    users_total = await pool.fetchval("SELECT COUNT(*) FROM users")
    users_active = await pool.fetchval("SELECT COUNT(*) FROM users WHERE is_banned=FALSE")
    users_banned = await pool.fetchval("SELECT COUNT(*) FROM users WHERE is_banned=TRUE")
    videos_total = await pool.fetchval("SELECT COUNT(*) FROM videos")
    total_views  = await pool.fetchval("SELECT COALESCE(SUM(view_count),0) FROM videos")
    total_likes  = await pool.fetchval("SELECT COALESCE(SUM(like_count),0) FROM videos")
    total_dislikes = await pool.fetchval("SELECT COALESCE(SUM(dislike_count),0) FROM videos")
    new_today    = await pool.fetchval(
        "SELECT COALESCE(new_users,0) FROM daily_stats WHERE date=CURRENT_DATE"
    )
    return {
        "users_total": users_total,
        "users_active": users_active,
        "users_banned": users_banned,
        "videos_total": videos_total,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_dislikes": total_dislikes,
        "new_today": new_today or 0,
    }
