from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.games.redis_store import GameStore
from app.models import BattleContest, Channel, ContestStatus, PointContest
from app.services.contests import finish_contest, override_winner
from app.services.permissions import is_chat_admin, is_grand_admin
from app.services.users import ensure_channel, ensure_user

router = Router(name="admin")


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not message.from_user or not is_grand_admin(message.from_user.id):
        await message.answer("Bu bo'lim faqat Grand Admin uchun.")
        return
    async with SessionLocal() as session:
        channel_count = await session.scalar(select(func.count(Channel.id))) or 0
        active_battles = await session.scalar(
            select(func.count(BattleContest.id)).where(BattleContest.status == ContestStatus.ACTIVE)
        ) or 0
        active_points = await session.scalar(
            select(func.count(PointContest.id)).where(PointContest.status == ContestStatus.ACTIVE)
        ) or 0
        channels = list(await session.scalars(select(Channel).order_by(Channel.id.desc()).limit(10)))
    channel_lines = "\n".join(
        f"• {channel.id}: {channel.title or channel.telegram_channel_id}" for channel in channels
    )
    recent_channels = channel_lines or "yo'q"
    await message.answer(
        f"👑 Grand Admin paneli\n"
        f"Ulangan kanallar: {channel_count}\n"
        f"Faol Battle: {active_battles}\n"
        f"Faol ball konkurslari: {active_points}\n\n"
        f"So'nggi kanallar:\n{recent_channels}\n\n"
        "/override <contest_id> <user_id> [reason]\n"
        "/finish <contest_id>"
    )


@router.message(Command("override"))
async def override(message: Message) -> None:
    if not message.from_user or not is_grand_admin(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    args = (message.text or "").split(maxsplit=3)
    if len(args) < 3:
        await message.answer("Format: /override <contest_id> <telegram_user_id> [reason]")
        return
    contest_id, winner_id = int(args[1]), int(args[2])
    reason = args[3] if len(args) == 4 else None
    async with SessionLocal() as session:
        await override_winner(
            session, contest_id, get_settings().grand_admin_id, winner_id, reason
        )
    await message.answer(
        f"Contest #{contest_id} g'olibi {winner_id} qilib belgilandi. Audit yozildi."
    )


@router.message(Command("finish"))
async def finish(message: Message) -> None:
    if not message.from_user or not is_grand_admin(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    args = (message.text or "").split()
    if len(args) != 2:
        await message.answer("/finish <contest_id>")
        return
    async with SessionLocal() as session:
        winner_id = await finish_contest(session, int(args[1]))
    await message.answer(f"Contest yakunlandi. G'olib: {winner_id or 'aniqlanmadi'}")


@router.message(Command("connect"))
async def connect_channel(message: Message) -> None:
    if not message.from_user:
        return
    if not await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("Chatni ulash uchun chat admini bo'lishingiz kerak.")
        return
    async with SessionLocal() as session:
        owner = await ensure_user(session, message.from_user)
        await ensure_channel(session, message.chat.id, owner, message.chat.title)
        await session.commit()
    await message.answer("✅ Chat botga ulandi. Endi /contest yoki /point_contest ishlatishingiz mumkin.")


@router.message(Command("my_channel"))
async def my_channel(message: Message) -> None:
    if not message.from_user or not await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("Faqat chat admini.")
        return
    await message.answer(f"Ulangan chat ID: <code>{message.chat.id}</code>")


@router.message(Command("game_config"))
async def game_config(message: Message) -> None:
    if not message.from_user or not is_grand_admin(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    args = (message.text or "").split(maxsplit=3)
    if len(args) != 4:
        await message.answer("/game_config <chat_id> <target|secret|chance|gift> <value>")
        return
    chat_id, key, value = int(args[1]), args[2], args[3]
    store = GameStore(Redis.from_url(get_settings().redis_url, decode_responses=True))
    data = await store.load(chat_id)
    if not data:
        await message.answer("Bu chatda faol Redis o'yini yo'q.")
        return
    if key == "secret":
        data[key] = int(value)
    elif key == "chance":
        data[key] = float(value)
    elif key in {"target", "gift"}:
        data[key] = value
    else:
        await message.answer("Noto'g'ri parametr.")
        return
    await store.save(chat_id, data)
    await message.answer(f"✅ {chat_id} o'yini uchun {key} yangilandi.")