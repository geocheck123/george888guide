import asyncio
import logging
import sys

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.database.engine import init_db
from bot.handlers import admin, start
from bot.middlewares.database import DatabaseMiddleware
from bot.services.scheduler import build_scheduler
from bot.webhook.server import create_app

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.update.middleware(DatabaseMiddleware())
    dp.include_router(start.router)
    dp.include_router(admin.router)
    return dp


async def main() -> None:
    logger.info("Initialising database…")
    await init_db()

    dp = build_dispatcher()

    logger.info("Setting webhook: %s", settings.telegram_webhook_url)
    ok = await bot.set_webhook(
        url=settings.telegram_webhook_url,
        drop_pending_updates=True,
        allowed_updates=dp.resolve_used_update_types(),
    )
    logger.info("set_webhook returned: %s", ok)

    # Verify what Telegram actually has registered after we set it
    info = await bot.get_webhook_info()
    logger.info(
        "Webhook verify -> url=%r pending=%s last_error=%r",
        info.url,
        info.pending_update_count,
        info.last_error_message,
    )

    scheduler = build_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler started")

    app = create_app(bot, dp)

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.webhook_port,
        log_level=settings.log_level.lower(),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    server = uvicorn.Server(config)
    logger.info("Starting uvicorn on port %d…", settings.webhook_port)

    try:
        await server.serve()
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
