import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database import queries
from bot.database.queries import create_payment
from bot.keyboards.inline import join_channel_button, pay_button, check_button
from bot.services import lava_top

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    await queries.upsert_user(session, user.id, user.username, user.full_name)

    active = await queries.get_active_subscription(session, user.id)
    if active:
        await message.answer(
            f"✅ У вас активная подписка!\n"
            f"📅 Действует до: <b>{active.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
            f"Вступайте в канал по вашей персональной ссылке:",
            reply_markup=join_channel_button(active.invite_link),
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"👋 Добро пожаловать!\n\n"
        f"📦 Подписка: <b>{settings.plan_label}</b>\n"
        f"💰 Стоимость: <b>{settings.plan_price} ₽</b>\n\n"
        f"Нажмите кнопку ниже, чтобы оплатить доступ к приватному каналу:",
        reply_markup=check_button(),
        parse_mode="HTML",
    )


@router.callback_query(lambda c: c.data == "buy")
async def handle_buy(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.message.edit_text("⏳ Создаём счёт для оплаты...")

    try:
        result = await lava_top.create_invoice(callback.from_user.id)
    except Exception as exc:
        logger.exception("Failed to create invoice: %s", exc)
        await callback.message.edit_text("❌ Не удалось создать счёт. Попробуйте позже.")
        return

    await create_payment(
        session,
        user_id=callback.from_user.id,
        invoice_id=result.invoice_id,
        plan="main",
        amount=settings.plan_price,
    )

    await callback.message.edit_text(
        f"💳 Счёт на оплату создан!\n\n"
        f"📦 Подписка: <b>{settings.plan_label}</b>\n"
        f"💰 Сумма: <b>{settings.plan_price} ₽</b>\n\n"
        f"Нажмите кнопку ниже для оплаты. После оплаты нажмите «Я оплатил».",
        reply_markup=pay_button(result.pay_url),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "check_payment")
async def check_payment(callback: CallbackQuery, session: AsyncSession) -> None:
    active = await queries.get_active_subscription(session, callback.from_user.id)
    if active:
        await callback.message.edit_text(
            f"✅ Подписка активирована!\n"
            f"📅 Действует до: <b>{active.expires_at.strftime('%d.%m.%Y')}</b>\n\n"
            f"Вступайте в канал:",
            reply_markup=join_channel_button(active.invite_link),
            parse_mode="HTML",
        )
    else:
        await callback.answer(
            "⏳ Оплата ещё не поступила. Попробуйте через минуту.",
            show_alert=True,
        )
