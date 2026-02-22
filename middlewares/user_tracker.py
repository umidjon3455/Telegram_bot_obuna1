from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
import database as db
from services.cache import get_cached_ban, cache_ban_status


class UserTrackerMiddleware(BaseMiddleware):
    """Registers user in DB and blocks banned users."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        u = event.from_user

        # Check ban (cache-first)
        banned = await get_cached_ban(u.id)
        if banned is None:
            banned = await db.is_banned(u.id)
            await cache_ban_status(u.id, banned)

        if banned:
            await event.answer("🚫 Siz botdan bloklangansiz.")
            return

        # Register/update user (referral handled in /start)
        await db.upsert_user(u.id, u.username, u.full_name)

        # Track message count
        await db.increment_message_count()

        return await handler(event, data)
