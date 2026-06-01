import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.engine import AsyncSessionLocal
from bot.services.subscription import revoke_expired

logger = logging.getLogger(__name__)


def build_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    async def _job() -> None:
        async with AsyncSessionLocal() as session:
            removed = await revoke_expired(bot, session)
            logger.info("Scheduler: removed %d expired subscribers", removed)

    scheduler.add_job(_job, trigger="cron", hour=3, minute=0, id="revoke_expired")
    return scheduler
