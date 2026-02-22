"""
Production-ready entry point.
Supports polling (dev) and webhook (Railway / Render / VPS).
"""
import asyncio
import logging
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from config import config
import database as db
from services.cache import init_redis
from handlers import admin, user
from middlewares.anti_spam import AntiSpamMiddleware
from middlewares.user_tracker import UserTrackerMiddleware

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ─── Factory ──────────────────────────────────────────────────────────────────

async def create_bot_and_dp():
    await init_redis()
    redis = await get_redis()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)

    # Middlewares
    dp.message.middleware(AntiSpamMiddleware())
    dp.message.middleware(UserTrackerMiddleware())

    # Routers
    dp.include_router(admin.router)
    dp.include_router(user.router)

    return bot, dp


# ─── Startup / Shutdown ───────────────────────────────────────────────────────

async def on_startup(bot: Bot, use_webhook: bool):
    await db.init_db()
    me = await bot.get_me()
    logger.info("Bot @%s started (id=%s)", me.username, me.id)

    if use_webhook:
        url = f"{config.WEBHOOK_URL}{config.WEBHOOK_PATH}"
        await bot.set_webhook(url, drop_pending_updates=True)
        logger.info("Webhook set → %s", url)
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Polling mode")


async def on_shutdown(bot: Bot):
    logger.info("Shutting down…")
    if config.USE_WEBHOOK:
        await bot.delete_webhook()
    await db.close_db()
    await close_redis()
    await bot.session.close()


# ─── Polling ──────────────────────────────────────────────────────────────────

async def run_polling():
    bot, dp = await create_bot_and_dp()
    await on_startup(bot, use_webhook=False)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown(bot)


# ─── Webhook ──────────────────────────────────────────────────────────────────

async def run_webhook():
    bot, dp = await create_bot_and_dp()
    await on_startup(bot, use_webhook=True)

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=config.WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # Health check endpoint (Railway / Render)
    async def health(_):
        return web.Response(text="OK")
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.HOST, config.PORT)
    await site.start()

    logger.info("Webhook server: %s:%s", config.HOST, config.PORT)

    try:
        await asyncio.Event().wait()
    finally:
        await on_shutdown(bot)
        await runner.cleanup()


# ─── Entry ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        if config.USE_WEBHOOK:
            asyncio.run(run_webhook())
        else:
            asyncio.run(run_polling())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
