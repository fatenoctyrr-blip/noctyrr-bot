from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Channel, Referral, User


async def ensure_user(session: AsyncSession, telegram_user: TelegramUser) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
    if not user:
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
        )
        session.add(user)
    else:
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name
    await session.flush()
    return user


async def ensure_channel(
    session: AsyncSession,
    telegram_channel_id: int,
    owner: User,
    title: str | None,
) -> Channel:
    channel = await session.scalar(
        select(Channel).where(Channel.telegram_channel_id == telegram_channel_id)
    )
    if not channel:
        channel = Channel(
            telegram_channel_id=telegram_channel_id,
            owner_id=owner.id,
            title=title,
        )
        session.add(channel)
        await session.flush()
    return channel


async def register_referral(
    session: AsyncSession, referred_user: User, referrer_telegram_id: int
) -> bool:
    if referred_user.telegram_id == referrer_telegram_id:
        return False
    referrer = await session.scalar(
        select(User).where(User.telegram_id == referrer_telegram_id)
    )
    if not referrer:
        return False
    existing = await session.scalar(
        select(Referral).where(Referral.referred_id == referred_user.id)
    )
    if existing:
        return False
    session.add(Referral(referrer_id=referrer.id, referred_id=referred_user.id))
    await session.flush()
    return True