import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import get_settings
from app.db import engine
from app.models import Base
from app.routers import admin, contests, games, user
from app.services.lifecycle import contest_watcher


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
    if settings.auto_create_schema:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    watcher = asyncio.create_task(contest_watcher(bot))
    try:
        await dispatcher.start_polling(bot)
    finally:
        watcher.cancel()
        await engine.dispose()
        await bot.session.close()