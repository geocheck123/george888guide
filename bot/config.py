from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    bot_token: str
    admin_ids: List[int] = []
    channel_id: int

    # Webhook
    webhook_host: str
    webhook_path: str = "/webhook/telegram"
    lava_webhook_path: str = "/webhook/lava"
    webhook_port: int = 8080

    # Database
    database_url: str
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "subscriptions"
    postgres_user: str = "bot"
    postgres_password: str = ""

    # Lava.top
    lava_api_key: str           # your API key from Integrations → Public API
    lava_webhook_secret: str    # key YOU define, paste into lava.top webhook settings
    lava_api_url: str = "https://api.lava.top"

    # Lava.top product IDs (create products in lava.top dashboard first)
    lava_product_1m: str = ""
    lava_product_3m: str = ""
    lava_product_12m: str = ""

    # Plans labels
    plan_1_month_price: int = 299
    plan_3_month_price: int = 799
    plan_12_month_price: int = 2499

    # Misc
    log_level: str = "INFO"

    @property
    def telegram_webhook_url(self) -> str:
        return f"{self.webhook_host}{self.webhook_path}"

    @property
    def plans(self) -> dict:
        return {
            "1m": {"months": 1, "price": self.plan_1_month_price, "label": "1 месяц", "product_id": self.lava_product_1m},
            "3m": {"months": 3, "price": self.plan_3_month_price, "label": "3 месяца", "product_id": self.lava_product_3m},
            "12m": {"months": 12, "price": self.plan_12_month_price, "label": "12 месяцев", "product_id": self.lava_product_12m},
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
