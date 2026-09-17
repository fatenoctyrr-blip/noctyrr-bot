import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import engine
from app.models import Base
from app.redis import close_redis, initialize_redis
from app.routers import admin, contests, games, user
from app.services.lifecycle import contest_watcher


async def initialize_database() -> None:
    settings = get_settings()
    retries = max(1, settings.db_connect_retries)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as connection:
                await connection.execute(text("SELECT 1"))
                if settings.auto_create_schema:
                    await connection.run_sync(Base.metadata.create_all)
            logging.getLogger(__name__).info("PostgreSQL connection is ready")
            return
        except (OSError, SQLAlchemyError) as exc:
            last_error = exc
            if attempt == retries:
                break
            logging.getLogger(__name__).warning(
                "PostgreSQL unavailable (attempt %s/%s); retrying in %ss",
                attempt,
                retries,
                settings.db_retry_seconds,
            )
            await asyncio.sleep(max(1, settings.db_retry_seconds))
    raise RuntimeError(
        "PostgreSQLga ulanib bo'lmadi. DATABASE_URL ni tekshiring: "
        "Docker Compose ichida host 'postgres', alohida serverda esa "
        "PostgreSQL serverining haqiqiy hosti bo'lishi kerak."
    ) from last_error


async def run() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    bot = Bot(
        token=settings.bot_api_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_routers(admin.router, contests.router, games.router, user.router)
    await initialize_database()
    await initialize_redis()
    watcher = asyncio.create_task(contest_watcher(bot))
    try:
        await dispatcher.start_polling(bot)
    finally:
        watcher.cancel()
        await engine.dispose()
        await close_redis()
        await bot.session.close()