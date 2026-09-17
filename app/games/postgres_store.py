from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import GroupGame, User


class GameStore:
    """Persistent game state backed by PostgreSQL instead of Redis."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def save(self, chat_id: int, state: dict[str, Any], ttl: int = 28800) -> None:
        async with self.session_factory() as session:
            game = await session.scalar(
                select(GroupGame).where(
                    GroupGame.chat_id == chat_id,
                    GroupGame.status == "active",
                )
            )
            state = dict(state)

            if game:
                previous_state = game.config_json or {}
                for key in ("_creator_telegram_id", "_expires_at"):
                    if key in previous_state:
                        state.setdefault(key, previous_state[key])
                game.type = str(state.get("type", game.type))
                game.config_json = state
            else:
                state.setdefault(
                    "_expires_at",
                    (datetime.now(UTC) + timedelta(seconds=ttl)).isoformat(),
                )
                creator_id = await self._ensure_creator(session, chat_id, state)
                game = GroupGame(
                    chat_id=chat_id,
                    type=str(state.get("type", "unknown")),
                    config_json=state,
                    created_by=creator_id,
                )
                session.add(game)

            await session.commit()

    async def load(self, chat_id: int) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            game = await session.scalar(
                select(GroupGame).where(
                    GroupGame.chat_id == chat_id,
                    GroupGame.status == "active",
                )
            )
            if not game:
                return None

            state = dict(game.config_json or {})
            expires_at = state.get("_expires_at")
            if expires_at:
                try:
                    if datetime.fromisoformat(expires_at) <= datetime.now(UTC):
                        await session.delete(game)
                        await session.commit()
                        return None
                except (TypeError, ValueError):
                    pass
            return state

    async def delete(self, chat_id: int) -> None:
        async with self.session_factory() as session:
            game = await session.scalar(
                select(GroupGame).where(
                    GroupGame.chat_id == chat_id,
                    GroupGame.status == "active",
                )
            )
            if game:
                await session.delete(game)
                await session.commit()

    @staticmethod
    async def _ensure_creator(session: Any, chat_id: int, state: dict[str, Any]) -> int:
        telegram_id = state.get("_creator_telegram_id")
        user = None
        if telegram_id is not None:
            user = await session.scalar(select(User).where(User.telegram_id == int(telegram_id)))
        if not user:
            user = await session.scalar(select(User).order_by(User.id).limit(1))
        if not user:
            user = User(
                telegram_id=int(telegram_id if telegram_id is not None else chat_id),
                first_name="Game creator",
            )
            session.add(user)
            await session.flush()
        return user.id