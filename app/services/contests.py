import random
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AdminOverride,
    BattleContest,
    BattleParticipant,
    Channel,
    ContestStatus,
    PointContest,
    PointEntry,
    SubscriptionRequirement,
)

ContestKind = Literal["battle", "point"]


async def resolve_contest(
    session: AsyncSession,
    contest_id: int,
    kind: ContestKind | None = None,
    chat_id: int | None = None,
) -> tuple[ContestKind, BattleContest | PointContest] | None:
    """Resolve a contest without allowing unrelated chat admins to cross-control it."""
    channel_ids: set[int] | None = None
    if chat_id is not None:
        channel_id = await session.scalar(
            select(Channel.id).where(Channel.telegram_channel_id == chat_id)
        )
        channel_ids = {channel_id} if channel_id is not None else set()

    async def get(model: type[BattleContest] | type[PointContest]) -> BattleContest | PointContest | None:
        query = select(model).where(model.id == contest_id)
        if channel_ids is not None:
            query = query.where(model.channel_id.in_(channel_ids))
        return await session.scalar(query)

    if kind in (None, "battle"):
        battle = await get(BattleContest)
        if battle:
            return "battle", battle
    if kind in (None, "point"):
        point = await get(PointContest)
        if point:
            return "point", point
    return None


def parse_contest_ref(value: str) -> tuple[ContestKind | None, int]:
    """Accept both `12` and the unambiguous `battle:12` / `point:12` format."""
    if ":" in value:
        prefix, raw_id = value.split(":", 1)
        if prefix not in {"battle", "point"}:
            raise ValueError("Contest turi battle yoki point bo'lishi kerak")
    else:
        prefix, raw_id = None, value
    contest_id = int(raw_id)
    if contest_id <= 0:
        raise ValueError("Contest ID musbat bo'lishi kerak")
    return prefix, contest_id


async def join_battle(
    session: AsyncSession, contest_id: int, user_id: int
) -> tuple[bool, int, bool]:
    contest = await session.get(BattleContest, contest_id)
    if not contest or contest.status != ContestStatus.ACTIVE:
        return False, 0, False
    existing = await session.scalar(
        select(BattleParticipant).where(
            BattleParticipant.contest_id == contest_id,
            BattleParticipant.user_id == user_id,
        )
    )
    if existing:
        count = await session.scalar(
            select(func.count(BattleParticipant.id)).where(
                BattleParticipant.contest_id == contest_id
            )
        )
        return False, count or 0, False
    session.add(BattleParticipant(contest_id=contest_id, user_id=user_id))
    await session.flush()
    count = await session.scalar(
        select(func.count(BattleParticipant.id)).where(
            BattleParticipant.contest_id == contest_id
        )
    )
    reached = bool(contest.target_count and count and count >= contest.target_count)
    if reached:
        contest.status = ContestStatus.FINISHED
        participant_ids = list(
            await session.scalars(
                select(BattleParticipant.user_id).where(
                    BattleParticipant.contest_id == contest_id
                )
            )
        )
        contest.winner_id = choose_random_winner(participant_ids)
    await session.commit()
    return True, count or 0, reached


async def requirements_for(
    session: AsyncSession, contest_id: int
) -> list[tuple[int, str | None]]:
    rows = await session.scalars(
        select(SubscriptionRequirement).where(
            SubscriptionRequirement.contest_id == contest_id,
            SubscriptionRequirement.is_active.is_(True),
        )
    )
    return [(row.resource_chat_id, row.resource_title) for row in rows]


async def create_battle(
    session: AsyncSession,
    channel: Channel,
    task: str,
    created_by: int,
    target_count: int | None = None,
    minutes: int | None = None,
) -> BattleContest:
    end_time = datetime.now(UTC) + timedelta(minutes=minutes) if minutes else None
    contest = BattleContest(
        channel_id=channel.id,
        task=task,
        target_count=target_count,
        end_time=end_time,
        created_by=created_by,
    )
    session.add(contest)
    await session.flush()
    return contest


async def create_point_contest(
    session: AsyncSession,
    channel: Channel,
    gift: str,
    created_by: int,
    weights: dict[str, int] | None = None,
    minutes: int | None = None,
) -> PointContest:
    end_time = datetime.now(UTC) + timedelta(minutes=minutes) if minutes else None
    contest = PointContest(
        channel_id=channel.id,
        gift=gift,
        created_by=created_by,
        end_time=end_time,
        weights_json=weights
        or {"reaction": 1, "stars": 5, "boost": 1, "comment": 1, "purchased": 1},
    )
    session.add(contest)
    await session.flush()
    return contest


async def add_requirement(
    session: AsyncSession,
    contest_id: int,
    resource_chat_id: int,
    resource_title: str | None = None,
) -> None:
    session.add(
        SubscriptionRequirement(
            contest_id=contest_id,
            resource_chat_id=resource_chat_id,
            resource_title=resource_title,
        )
    )
    await session.flush()


async def ensure_point_entry(
    session: AsyncSession, contest_id: int, user_id: int
) -> PointEntry:
    entry = await session.scalar(
        select(PointEntry).where(
            PointEntry.contest_id == contest_id,
            PointEntry.user_id == user_id,
        )
    )
    if not entry:
        entry = PointEntry(contest_id=contest_id, user_id=user_id)
        session.add(entry)
        await session.flush()
    return entry


async def add_points(
    session: AsyncSession,
    contest_id: int,
    user_id: int,
    kind: str,
    amount: int,
) -> PointEntry:
    if kind not in {"reaction", "stars", "boost", "comment", "purchased"}:
        raise ValueError("Unknown point type")
    if amount <= 0:
        raise ValueError("Amount must be positive")
    contest = await session.get(PointContest, contest_id)
    if not contest or contest.status != ContestStatus.ACTIVE:
        raise ValueError("Point contest is not active")
    entry = await ensure_point_entry(session, contest_id, user_id)
    setattr(entry, f"{kind}_points", getattr(entry, f"{kind}_points") + amount)
    await session.flush()
    return entry


async def leaderboard(
    session: AsyncSession, contest_id: int, limit: int = 10
) -> list[tuple[PointEntry, int]]:
    contest = await session.get(PointContest, contest_id)
    if not contest:
        return []
    entries = list(
        await session.scalars(
            select(PointEntry).where(PointEntry.contest_id == contest_id)
        )
    )
    return sorted(
        [(entry, point_score(entry, contest.weights_json)) for entry in entries],
        key=lambda row: row[1],
        reverse=True,
    )[:limit]


async def finish_contest(
    session: AsyncSession,
    contest_id: int,
    forced_winner_id: int | None = None,
    kind: ContestKind | None = None,
    chat_id: int | None = None,
) -> int | None:
    resolved = await resolve_contest(session, contest_id, kind, chat_id)
    if not resolved:
        raise ValueError("Contest topilmadi yoki bu chatga tegishli emas")
    resolved_kind, contest = resolved
    if resolved_kind == "battle":
        battle = contest
        assert isinstance(battle, BattleContest)
        battle.status = ContestStatus.FINISHED
        if forced_winner_id:
            battle.winner_id = forced_winner_id
        else:
            ids = list(
                await session.scalars(
                    select(BattleParticipant.user_id).where(
                        BattleParticipant.contest_id == contest_id
                    )
                )
            )
            battle.winner_id = choose_random_winner(ids)
        await session.commit()
        return battle.winner_id
    if resolved_kind == "point":
        point = contest
        assert isinstance(point, PointContest)
        point.status = ContestStatus.FINISHED
        if forced_winner_id:
            point.winner_id = forced_winner_id
        else:
            rows = await leaderboard(session, contest_id, 1)
            point.winner_id = rows[0][0].user_id if rows else None
        await session.commit()
        return point.winner_id
    raise ValueError("Contest turi noma'lum")


def choose_random_winner(user_ids: list[int]) -> int | None:
    return random.choice(user_ids) if user_ids else None


async def override_winner(
    session: AsyncSession,
    contest_id: int,
    grand_admin_id: int,
    chosen_winner_id: int,
    reason: str | None = None,
    kind: ContestKind | None = None,
    chat_id: int | None = None,
) -> AdminOverride:
    resolved = await resolve_contest(session, contest_id, kind, chat_id)
    if not resolved:
        raise ValueError("Contest topilmadi yoki bu chatga tegishli emas")
    resolved_kind, contest = resolved
    if resolved_kind == "battle":
        assert isinstance(contest, BattleContest)
        contest.winner_id = chosen_winner_id
        contest.status = ContestStatus.FINISHED
    else:
        assert isinstance(contest, PointContest)
        contest.winner_id = chosen_winner_id
        contest.status = ContestStatus.FINISHED
    audit = AdminOverride(
        contest_id=contest_id,
        grand_admin_id=grand_admin_id,
        chosen_winner_id=chosen_winner_id,
        reason=reason,
    )
    session.add(audit)
    await session.commit()
    return audit


def contest_expired(end_time: datetime | None) -> bool:
    return bool(end_time and end_time <= datetime.now(UTC))


def point_score(entry: PointEntry, weights: dict[str, int]) -> int:
    return (
        entry.reaction_points * weights.get("reaction", 1)
        + entry.stars_points * weights.get("stars", 1)
        + entry.boost_points * weights.get("boost", 1)
        + entry.comment_points * weights.get("comment", 1)
        + entry.purchased_points * weights.get("purchased", 1)
    )