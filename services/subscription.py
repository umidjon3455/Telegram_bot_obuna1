import logging
from typing import List
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from config import config
from services.cache import cache_subscription, get_cached_subscription

logger = logging.getLogger(__name__)


async def check_user_subscriptions(bot: Bot, user_id: int) -> List[str]:
    """
    Returns channels the user is NOT subscribed to.
    Uses Redis cache (60s TTL) to avoid hammering Telegram API.
    """
    # Check cache first
    cached = await get_cached_subscription(user_id)
    if cached is True:
        return []

    not_subscribed = []
    for channel in config.REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ("left", "kicked", "banned"):
                not_subscribed.append(channel)
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.error("Cannot check %s for user %s: %s", channel, user_id, e)
            not_subscribed.append(channel)

    is_subscribed = len(not_subscribed) == 0
    await cache_subscription(user_id, is_subscribed)
    return not_subscribed
