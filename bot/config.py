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
    lava_api_key: str
    lava_webhook_secret: str
    lava_api_url: str = "https://api.lava.top"
    lava_product_id: str        # single product ID from lava.top dashboard

    # Plan settings
    plan_months: int = 1
    plan_label: str = "1 месяц"
    plan_price: int = 299

    # Misc
    log_level: str = "INFO"

    @property
    def telegram_webhook_url(self) -> str:
        return f"{self.webhook_host}{self.webhook_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
