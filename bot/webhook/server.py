import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request
from starlette.middleware.trustedhost import TrustedHostMiddleware

from bot.config import settings
from bot.database.engine import AsyncSessionLocal
from bot.database.queries import get_payment_by_invoice, mark_payment_paid
from bot.keyboards.inline import join_channel_button
from bot.services.lava_top import verify_webhook_secret
from bot.services.subscription import activate

logger = logging.getLogger(__name__)

# Event types that mean a successful payment
SUCCESS_EVENTS = {"payment.success", "subscription.recurring.payment.success"}


def create_app(bot: Bot, dp: Dispatcher) -> FastAPI:
    app = FastAPI(title="Subscription Bot", docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    @app.post(settings.webhook_path)
    async def telegram_webhook(request: Request) -> dict:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        return {"ok": True}

    @app.post(settings.lava_webhook_path)
    async def lava_webhook(
        request: Request,
        x_api_key: str = Header(default="", alias="X-Api-Key"),
    ) -> dict:
        # Verify the key Lava.top sends matches our LAVA_WEBHOOK_SECRET
        if not verify_webhook_secret(x_api_key):
            logger.warning("Invalid Lava webhook secret")
            raise HTTPException(status_code=403, detail="Bad secret")

        data = await request.json()
        logger.info("Lava webhook received: %s", data)

        event_type = data.get("type", "")
        if event_type not in SUCCESS_EVENTS:
            # Not a success event (e.g. payment.failed, subscription.cancelled)
            return {"ok": True}

        # Lava.top invoice/order ID — try common field names
        invoice_id = (
            data.get("orderId")
            or data.get("id")
            or data.get("invoiceId")
        )
        if not invoice_id:
            logger.warning("No invoice ID in webhook payload: %s", data)
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
