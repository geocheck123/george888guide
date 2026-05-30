from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings


def plans_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, plan in settings.plans.items():
        builder.button(
            text=f"💳 {plan['label']} — {plan['price']} ₽",
            callback_data=f"buy:{key}",
        )
    builder.adjust(1)
    return builder.as_markup()


def pay_button(url: str, plan_label: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Оплатить ({plan_label})", url=url)],
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data="check_payment")],
            [InlineKeyboardButton(text="« Назад", callback_data="back_to_plans")],
        ]
    )


def join_channel_button(invite_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Вступить в канал", url=invite_link)],
        ]
    )
