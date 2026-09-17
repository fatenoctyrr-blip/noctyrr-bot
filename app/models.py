from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ContestStatus(StrEnum):
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class GameType(StrEnum):
    MAFIA = "mafia"
    BUNKER = "bunker"
    JACKPOT = "jackpot"
    GUESS_NUMBER = "guess_number"
    MESSAGE_LOTTERY = "message_lottery"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Channel(Base):
    __tablename__ = "channels"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    owner: Mapped["User"] = relationship()


class BattleContest(Base):
    __tablename__ = "battle_contests"
    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    task: Mapped[str] = mapped_column(Text)
    target_count: Mapped[int | None] = mapped_column(Integer)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default=ContestStatus.ACTIVE)
    post_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    post_message_id: Mapped[int | None] = mapped_column(BigInteger)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BattleParticipant(Base):
    __tablename__ = "battle_contest_participants"
    __table_args__ = (UniqueConstraint("contest_id", "user_id", name="uq_battle_participant"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    contest_id: Mapped[int] = mapped_column(ForeignKey("battle_contests.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PointContest(Base):
    __tablename__ = "point_contests"
    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    gift: Mapped[str] = mapped_column(Text)
    media_file_id: Mapped[str | None] = mapped_column(String(255))
    weights_json: Mapped[dict[str, int]] = mapped_column(
        JSON, default=lambda: {
            "reaction": 1,
            "stars": 5,
            "boost": 1,
            "comment": 1,
            "purchased": 1,
        }
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default=ContestStatus.ACTIVE)
    post_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    post_message_id: Mapped[int | None] = mapped_column(BigInteger)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PointEntry(Base):
    __tablename__ = "point_entries"
    __table_args__ = (UniqueConstraint("contest_id", "user_id", name="uq_point_entry"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    contest_id: Mapped[int] = mapped_column(ForeignKey("point_contests.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reaction_points: Mapped[int] = mapped_column(Integer, default=0)
    stars_points: Mapped[int] = mapped_column(Integer, default=0)
    boost_points: Mapped[int] = mapped_column(Integer, default=0)
    comment_points: Mapped[int] = mapped_column(Integer, default=0)
    purchased_points: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def total(self) -> int:
        return (
            self.reaction_points
            + self.stars_points
            + self.boost_points
            + self.comment_points
            + self.purchased_points
        )


class GroupGame(Base):
    __tablename__ = "group_games"
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    type: Mapped[str] = mapped_column(String(32))
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default=ContestStatus.ACTIVE)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SubscriptionRequirement(Base):
    __tablename__ = "subscription_requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    contest_id: Mapped[int] = mapped_column(index=True)
    resource_chat_id: Mapped[int] = mapped_column(BigInteger)
    resource_title: Mapped[str | None] = mapped_column(String(255))
    required_referrals: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AdminOverride(Base):
    __tablename__ = "admin_overrides"
    id: Mapped[int] = mapped_column(primary_key=True)
    contest_id: Mapped[int] = mapped_column(Integer, index=True)
    grand_admin_id: Mapped[int] = mapped_column(BigInteger)
    chosen_winner_id: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    referred_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)