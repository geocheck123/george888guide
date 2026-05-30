import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request

from bot.config import settings
from bot.database.engine import AsyncSessionLocal
from bot.database.queries import get_payment_by_invoice, mark_payment_paid
from bot.keyboards.inline import join_channel_button
from bot.services.lava_top import verify_webhook_signature
from bot.services.subscription import activate

logger = logging.getLogger(__name__)


def create_app(bot: Bot, dp: Dispatcher) -> FastAPI:
    app = FastAPI(title="Subscription Bot", docs_url=None, redoc_url=None)

    @app.post(settings.webhook_path)
    async def telegram_webhook(request: Request) -> dict:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        return {"ok": True}

    @app.post(settings.lava_webhook_path)
    async def lava_webhook(
        request: Request,
        x_signature: str = Header(default="", alias="X-Signature"),
    ) -> dict:
        body = await request.body()

        if not verify_webhook_signature(body, x_signature):
            logger.warning("Invalid Lava webhook signature")
            raise HTTPException(status_code=403, detail="Bad signature")

        data = await request.json()
        logger.info("Lava webhook received: %s", data)

        status = data.get("status")
        invoice_id = data.get("id") or data.get("orderId")

        if status != "success" or not invoice_id:
            return {"ok": True}

        async with AsyncSessionLocal() as session:
            payment = await get_payment_by_invoice(session, invoice_id)
            if payment is None or payment.status == "paid":
                return {"ok": True}

            payment = await mark_payment_paid(session, invoice_id)
            invite_link = await activate(bot, session, payment.user_id, payment.plan)

        from bot.config import settings as cfg  # noqa: PLC0415
        plan = cfg.plans[payment.plan]
        try:
            await bot.send_message(
                payment.user_id,
                f"🎉 <b>Оплата получена!</b>\n\n"
                f"📦 Тариф: <b>{plan['label']}</b>\n\n"
                f"Нажмите кнопку ниже, чтобы вступить в закрытый канал:",
                reply_markup=join_channel_button(invite_link),
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Could not notify user %d: %s", payment.user_id, exc)

        return {"ok": True}

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app
