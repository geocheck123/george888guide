import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database import queries

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return

    total = await queries.count_total_users(session)
    active = await queries.count_active(session)
    expired = await queries.count_expired(session)

    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👤 Всего пользователей: <b>{total}</b>\n"
        f"✅ Активных подписок: <b>{active}</b>\n"
        f"❌ Истёкших подписок: <b>{expired}</b>",
        parse_mode="HTML",
    )


@router.message(Command("active"))
async def cmd_active(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return

    subs = await queries.list_active_subscriptions(session)
    if not subs:
        await message.answer("Нет активных подписок.")
        return

    lines = [f"✅ <b>Активные подписки ({len(subs)})</b>\n"]
    for s in subs:
        exp = s.expires_at.strftime("%d.%m.%Y") if s.expires_at else "—"
        lines.append(f"• <code>{s.user_id}</code> | {s.plan} | до {exp}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("expired"))
async def cmd_expired(message: Message, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return

    subs = await queries.list_expired_subscriptions(session)
    if not subs:
        await message.answer("Нет истёкших подписок.")
        return

    lines = [f"❌ <b>Истёкшие подписки (последние {len(subs)})</b>\n"]
    for s in subs:
        exp = s.expires_at.strftime("%d.%m.%Y") if s.expires_at else "—"
        lines.append(f"• <code>{s.user_id}</code> | {s.plan} | истёк {exp}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot, session: AsyncSession) -> None:
    if not _is_admin(message.from_user.id):
        return

    text = message.text.partition(" ")[2].strip()
    if not text:
        await message.answer("Использование: /broadcast <текст сообщения>")
        return

    subs = await queries.list_active_subscriptions(session)
    sent = failed = 0
    for sub in subs:
        try:
            await bot.send_message(sub.user_id, text)
            sent += 1
        except Exception:
            failed += 1

    await message.answer(f"📣 Рассылка завершена.\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")
