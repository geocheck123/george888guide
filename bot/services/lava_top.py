import hashlib
import hmac
import json
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


def _sign(payload: dict) -> str:
    """HMAC-SHA256 signature for Lava.top requests."""
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return hmac.new(
        settings.lava_secret_key.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()


async def create_invoice(user_id: int, plan_key: str) -> InvoiceResult:
    plan = settings.plans[plan_key]
    order_id = f"{user_id}_{plan_key}_{uuid.uuid4().hex[:8]}"

    payload = {
        "shopId": settings.lava_shop_id,
        "sum": plan["price"],
        "orderId": order_id,
        "comment": f"Подписка {plan['label']} — user {user_id}",
        "hookUrl": f"{settings.webhook_host}{settings.lava_webhook_path}",
        "successUrl": f"https://t.me/{(await _bot_username())}",
        "failUrl": f"https://t.me/{(await _bot_username())}",
        "expire": 30,
    }

    signature = _sign(payload)
    headers = {"Signature": signature, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(settings.lava_api_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    logger.info("Lava invoice created: %s", data)
    return InvoiceResult(invoice_id=data["data"]["id"], pay_url=data["data"]["url"])


async def _bot_username() -> str:
    # Cached lazily; imported here to avoid circular imports
    from bot.main import bot  # noqa: PLC0415

    me = await bot.get_me()
    return me.username or ""


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify that a Lava.top webhook payload is authentic."""
    expected = hmac.new(
        settings.lava_secret_key.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
