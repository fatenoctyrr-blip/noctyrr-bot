import asyncio
import logging

from aiogram import Bot
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import BattleContest, ContestStatus, PointContest
from app.services.contests import finish_contest

logger = logging.getLogger(__name__)


async def finish_expired_contests(bot: Bot) -> None:
    async with SessionLocal() as session:
        contests = list(
            await session.scalars(
                select(BattleContest).where(
                    BattleContest.status == ContestStatus.ACTIVE,
                    BattleContest.end_time.is_not(None),
                )
            )
        )
        point_contests = list(
            await session.scalars(
                select(PointContest).where(
                    PointContest.status == ContestStatus.ACTIVE,
                    PointContest.end_time.is_not(None),
                )
            )
        )
        for contest in [*contests, *point_contests]:
            from datetime import UTC, datetime

            if contest.end_time and contest.end_time <= datetime.now(UTC):
                winner_id = await finish_contest(session, contest.id)
                if contest.post_chat_id:
                    try:
                        await bot.send_message(
                            contest.post_chat_id,
                            f"⏰ Konkurs #{contest.id} yakunlandi.\n"
                            f"G'olib: {winner_id or 'aniqlanmadi'}",
                        )
                    except Exception:
                        logger.exception("Unable to announce contest %s", contest.id)


async def contest_watcher(bot: Bot) -> None:
    while True:
        try:
            await finish_expired_contests(bot)
        except Exception:
            logger.exception("Contest watcher failed")
        await asyncio.sleep(get_settings().contest_poll_seconds)