from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def check_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="buy")],
        ]
    )


def pay_button(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=url)],
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data="check_payment")],
        ]
    )


def join_channel_button(invite_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Вступить в канал", url=invite_link)],
        ]
    )
