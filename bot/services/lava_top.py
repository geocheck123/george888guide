import logging
import uuid
from dataclasses import dataclass

import httpx

from bot.config import settings

logger = logging.getLogger(__name__)


@dataclass
class InvoiceResult:
    invoice_id: str
    pay_url: str


async def create_invoice(user_id: int) -> InvoiceResult:
    order_id = f"{user_id}_{uuid.uuid4().hex[:8]}"

    headers = {
        "X-Api-Key": settings.lava_api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "email": f"{user_id}@telegram.user",
        "offerId": settings.lava_product_id,
        "orderId": order_id,
        "hookUrl": f"{settings.webhook_host}{settings.lava_webhook_path}",
        "successUrl": f"https://t.me/{(await _bot_username())}",
        "failUrl": f"https://t.me/{(await _bot_username())}",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{settings.lava_api_url}/api/v2/invoices",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    logger.info("Lava invoice created: %s", data)
    return InvoiceResult(invoice_id=data["id"], pay_url=data["url"])


async def _bot_username() -> str:
    from bot.main import bot  # noqa: PLC0415

    me = await bot.get_me()
    return me.username or ""


def verify_webhook_secret(x_api_key: str) -> bool:
    return x_api_key == settings.lava_webhook_secret
