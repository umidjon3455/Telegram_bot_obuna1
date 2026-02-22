"""
Broadcast service — sends a message to all active users.
Uses asyncio.sleep between sends to respect Telegram rate limits.
Reports progress in real-time by editing the admin's message.
"""
import asyncio
import logging
from typing import Union

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.types import Message

import database as db
from services.cache import set_broadcast_progress, clear_broadcast_progress
from config import config

logger = logging.getLogger(__name__)


async def broadcast(
    bot: Bot,
    source_message: Message,
    status_message: Message,
) -> dict:
    """
    Forward source_message to all non-banned users.
    Updates status_message with live progress.
    Returns {sent, failed, total}.
    """
    user_ids = await db.get_all_user_ids(include_banned=False)
    total = len(user_ids)
    sent = 0
    failed = 0

    await clear_broadcast_progress()

    for i, uid in enumerate(user_ids):
        try:
            await source_message.copy_to(uid)
            sent += 1
        except TelegramForbiddenError:
            # user blocked the bot
            failed += 1
        except TelegramBadRequest as e:
            logger.warning("Broadcast to %s failed: %s", uid, e)
            failed += 1
        except Exception as e:
            logger.error("Unexpected error broadcasting to %s: %s", uid, e)
            failed += 1

        # Update progress every 20 users
        if (i + 1) % 20 == 0 or i + 1 == total:
            await set_broadcast_progress(sent, failed, total)
            try:
                await status_message.edit_text(
                    f"📨 <b>Broadcast davom etmoqda...</b>\n\n"
                    f"✅ Yuborildi: <b>{sent}</b>\n"
                    f"❌ Xatolik: <b>{failed}</b>\n"
                    f"📊 Jami: <b>{total}</b>\n"
                    f"⏳ Progress: <b>{i+1}/{total}</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        await asyncio.sleep(config.BROADCAST_DELAY)

    await clear_broadcast_progress()
    return {"sent": sent, "failed": failed, "total": total}
