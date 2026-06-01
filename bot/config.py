from functools import lru_cache
from typing import List

from pydantic import field_validator
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

    # Database — Railway provides DATABASE_URL automatically
    database_url: str = ""
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "subscriptions"
    postgres_user: str = "bot"
    postgres_password: str = ""

    # Lava.top
    lava_api_key: str
    lava_webhook_secret: str
    lava_api_url: str = "https://api.lava.top"
    lava_product_id: str

    # How many months this product grants
    plan_months: int = 1

    # Misc
    log_level: str = "INFO"

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

    @field_validator("database_url", mode="before")
    @classmethod
    def build_database_url(cls, v, info):
        # If DATABASE_URL is provided, convert postgres:// to postgresql+asyncpg://
        if v:
            return v.replace("postgres://", "postgresql+asyncpg://").replace(
                "postgresql://", "postgresql+asyncpg://"
            )
        # Fall back to building from individual parts
        data = info.data
        host = data.get("postgres_host", "db")
        port = data.get("postgres_port", 5432)
        db = data.get("postgres_db", "subscriptions")
        user = data.get("postgres_user", "bot")
        password = data.get("postgres_password", "")
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    @property
    def telegram_webhook_url(self) -> str:
        return f"{self.webhook_host}{self.webhook_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
