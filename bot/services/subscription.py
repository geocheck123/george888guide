import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database import queries

logger = logging.getLogger(__name__)


async def activate(
    bot: Bot,
    session: AsyncSession,
    user_id: int,
    plan_key: str,
) -> str:
    """Activate a subscription and return a personal invite link."""
    plan = settings.plans[plan_key]
    expires_at = datetime.now(timezone.utc) + timedelta(days=30 * plan["months"])

    invite = await bot.create_chat_invite_link(
        chat_id=settings.channel_id,
        member_limit=1,
        expire_date=expires_at,
    )

    await queries.activate_subscription(
        session,
        user_id=user_id,
        plan=plan_key,
        expires_at=expires_at,
        invite_link=invite.invite_link,
    )
    logger.info("Subscription activated for user %d until %s", user_id, expires_at)
    return invite.invite_link


async def revoke_expired(bot: Bot, session: AsyncSession) -> int:
    """Kick expired subscribers from the channel. Returns count removed."""
    expired = await queries.get_expired_subscriptions(session)
    removed = 0
    for sub in expired:
        try:
            await bot.ban_chat_member(chat_id=settings.channel_id, user_id=sub.user_id)
            await bot.unban_chat_member(chat_id=settings.channel_id, user_id=sub.user_id)
            await queries.mark_subscription_expired(session, sub.id)
            removed += 1
            logger.info("Removed expired user %d from channel", sub.user_id)

            try:
                await bot.send_message(
                    sub.user_id,
                    "⏰ Ваша подписка истекла и вы были удалены из канала.\n"
                    "Используйте /start чтобы продлить подписку.",
                )
            except Exception:
                pass  # user may have blocked the bot
        except Exception as exc:
            logger.warning("Could not remove user %d: %s", sub.user_id, exc)
    return removed
