import time
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from config import config

logger = logging.getLogger(__name__)


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self._history: Dict[int, list] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        uid = event.from_user.id if event.from_user else None
        if uid is None or uid in config.ADMIN_IDS:
            return await handler(event, data)

        now = time.monotonic()
        self._history[uid] = [t for t in self._history[uid] if now - t < config.SPAM_RATE_WINDOW]

        if len(self._history[uid]) >= config.SPAM_RATE_LIMIT:
            await event.answer(
                f"⚠️ Juda tez yuboryapsiz! {config.SPAM_RATE_WINDOW} soniya kuting."
            )
            return

        self._history[uid].append(now)
        return await handler(event, data)
