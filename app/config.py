from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_api_token: str = Field(alias="BOT_API_TOKEN")
    grand_admin_id: int = Field(default=8126409678, alias="GRAND_ADMIN_ID")
    default_channel_id: int | None = Field(default=4354232618, alias="DEFAULT_CHANNEL_ID")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/oyunlar",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timezone: str = Field(default="Asia/Samarkand", alias="TIMEZONE")
    auto_create_schema: bool = Field(default=True, alias="AUTO_CREATE_SCHEMA")
    contest_poll_seconds: int = Field(default=30, alias="CONTEST_POLL_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()