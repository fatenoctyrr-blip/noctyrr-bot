from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_api_token: str = Field(alias="BOT_API_TOKEN")
    grand_admin_id: int = Field(alias="GRAND_ADMIN_ID")
    default_channel_id: int | None = Field(default=None, alias="DEFAULT_CHANNEL_ID")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    timezone: str = Field(default="Asia/Samarkand", alias="TIMEZONE")
    auto_create_schema: bool = Field(default=True, alias="AUTO_CREATE_SCHEMA")
    contest_poll_seconds: int = Field(default=30, alias="CONTEST_POLL_SECONDS")
    db_connect_retries: int = Field(default=12, alias="DB_CONNECT_RETRIES")
    db_retry_seconds: int = Field(default=5, alias="DB_RETRY_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1].strip()
            if value.startswith("postgres://"):
                return "postgresql+asyncpg://" + value.removeprefix("postgres://")
            if value.startswith("postgresql://"):
                return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
        return value

    @field_validator("redis_url", mode="before")
    @classmethod
    def normalize_redis_url(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1].strip()
            if value.startswith("redis+tls://"):
                return "rediss://" + value.removeprefix("redis+tls://")
            return value
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()