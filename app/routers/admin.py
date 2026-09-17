from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.games.postgres_store import GameStore
from app.models import BattleContest, Channel, ContestStatus, PointContest, User
from app.services.contests import (
    finish_contest,
    override_winner,
    parse_contest_ref,
)
from app.services.permissions import is_chat_admin, is_grand_admin
from app.services.users import ensure_channel, ensure_user

router = Router(name="admin")


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats"),
                InlineKeyboardButton(text="🎯 Konkurslar", callback_data="admin:contests"),
            ],
            [
                InlineKeyboardButton(text="📢 Kanallar", callback_data="admin:channels"),
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin:refresh"),
            ],
        ]
    )


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Admin panel", callback_data="admin:refresh")]
        ]
    )


async def admin_summary() -> str:
    async with SessionLocal() as session:
        channel_count = await session.scalar(select(func.count(Channel.id))) or 0
        active_battles = await session.scalar(
            select(func.count(BattleContest.id)).where(BattleContest.status == ContestStatus.ACTIVE)
        ) or 0
        active_points = await session.scalar(
            select(func.count(PointContest.id)).where(PointContest.status == ContestStatus.ACTIVE)
        ) or 0
        user_count = await session.scalar(select(func.count(User.id))) or 0
    return (
        "👑 <b>Grand Admin paneli</b>\n\n"
        f"👤 Foydalanuvchilar: <b>{user_count}</b>\n"
        f"📢 Ulangan kanallar: <b>{channel_count}</b>\n"
        f"🎯 Faol Battle: <b>{active_battles}</b>\n"
        f"🏆 Faol ball konkurslari: <b>{active_points}</b>\n\n"
        "Kerakli bo'limni tanlang:"
    )


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not message.from_user or not is_grand_admin(message.from_user.id):
        await message.answer("Bu bo'lim faqat Grand Admin uchun.")
        return
    await message.answer(await admin_summary(), reply_markup=admin_keyboard())


async def require_grand_admin(callback: CallbackQuery) -> bool:
    if not callback.from_user or not is_grand_admin(callback.from_user.id):
        await callback.answer("Bu panel faqat Grand Admin uchun.", show_alert=True)
        return False
    return True


@router.callback_query(F.data == "admin:refresh")
async def refresh_admin_panel(callback: CallbackQuery) -> None:
    if not await require_grand_admin(callback):
        return
    if callback.message:
        await callback.message.edit_text(await admin_summary(), reply_markup=admin_keyboard())
    await callback.answer("Yangilandi")


@router.callback_query(F.data == "admin:stats")
async def admin_stats_callback(callback: CallbackQuery) -> None:
    if not await require_grand_admin(callback):
        return
    if callback.message:
        await callback.message.edit_text(await admin_summary(), reply_markup=admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:channels")
async def admin_channels_callback(callback: CallbackQuery) -> None:
    if not await require_grand_admin(callback):
        return
    async with SessionLocal() as session:
        channels = list(await session.scalars(select(Channel).order_by(Channel.id.desc()).limit(20)))
    lines = [
        "📢 <b>Ulangan kanallar</b>\n",
        *[
            f"• #{channel.id} — {channel.title or channel.telegram_channel_id}"
            for channel in channels
        ],
    ]
    if not channels:
        lines.append("Hali kanal ulanmagan.")
    if callback.message:
        await callback.message.edit_text("\n".join(lines), reply_markup=back_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:contests")
async def admin_contests_callback(callback: CallbackQuery) -> None:
    if not await require_grand_admin(callback):
        return
    async with SessionLocal() as session:
        battles = list(
            await session.scalars(
                select(BattleContest)
                .where(BattleContest.status == ContestStatus.ACTIVE)
                .order_by(BattleContest.id.desc())
                .limit(10)
            )
        )
        points = list(
            await session.scalars(
                select(PointContest)
                .where(PointContest.status == ContestStatus.ACTIVE)
                .order_by(PointContest.id.desc())
                .limit(10)
            )
        )
    buttons: list[list[InlineKeyboardButton]] = []
    lines = ["🎯 <b>Faol konkurslar</b>\n"]
    for contest in battles:
        lines.append(f"• Battle #{contest.id}: {contest.task[:50]}")
        buttons.append(
            [InlineKeyboardButton(
                text=f"⛔ Battle #{contest.id}ni tugatish",
                callback_data=f"admin:finish:battle:{contest.id}",
            )]
        )
    for contest in points:
        lines.append(f"• Ball #{contest.id}: {contest.gift[:50]}")
        buttons.append(
            [InlineKeyboardButton(
                text=f"⛔ Ball #{contest.id}ni tugatish",
                callback_data=f"admin:finish:point:{contest.id}",
            )]
        )
    if not battles and not points:
        lines.append("Faol konkurs yo'q.")
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:refresh")])
    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:finish:"))
async def confirm_finish_callback(callback: CallbackQuery) -> None:
    if not await require_grand_admin(callback):
        return
    _, _, kind, contest_id = callback.data.split(":")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, tugatish",
                    callback_data=f"admin:confirm:{kind}:{contest_id}",
                ),
                InlineKeyboardButton(text="❌ Bekor", callback_data="admin:contests"),
            ]
        ]
    )
    if callback.message:
        await callback.message.edit_text(
            f"{kind.title()} #{contest_id} konkursini yakunlashni tasdiqlaysizmi?",
            reply_markup=keyboard,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:confirm:"))
async def finish_from_panel_callback(callback: CallbackQuery) -> None:
    if not await require_grand_admin(callback):
        return
    _, _, kind, raw_id = callback.data.split(":")
    try:
        async with SessionLocal() as session:
            winner_id = await finish_contest(session, int(raw_id), kind=kind)
        text = f"✅ {kind.title()} #{raw_id} yakunlandi.\nG'olib: {winner_id or 'aniqlanmadi'}"
    except (ValueError, TypeError) as exc:
        text = f"❌ Yakunlab bo'lmadi: {exc}"
    if callback.message:
        await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()


@router.message(Command("override"))
async def override(message: Message) -> None:
    if not message.from_user or not is_grand_admin(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    args = (message.text or "").split(maxsplit=3)
    if len(args) < 3:
        await message.answer(
            "Format: /override <battle:contest_id|point:contest_id> "
            "<telegram_user_id> [reason]"
        )
        return
    try:
        kind, contest_id = parse_contest_ref(args[1])
        if kind is None:
            await message.answer("Contest turini aniq yozing: battle:12 yoki point:12")
            return
        telegram_winner_id = int(args[2])
    except ValueError:
        await message.answer("Contest ID va Telegram user ID raqam bo'lishi kerak.")
        return
    reason = args[3] if len(args) == 4 else None
    async with SessionLocal() as session:
        winner = await session.scalar(select(User).where(User.telegram_id == telegram_winner_id))
        if not winner:
            await message.answer("Bu foydalanuvchi botda hali ro'yxatdan o'tmagan.")
            return
        try:
            await override_winner(
                session,
                contest_id,
                get_settings().grand_admin_id,
                winner.id,
                reason,
                kind=kind,
            )
        except ValueError as exc:
            await message.answer(str(exc))
            return
    await message.answer(
        f"{kind.title()} #{contest_id} g'olibi {telegram_winner_id} qilib belgilandi. "
        "Audit yozildi."
    )


@router.message(Command("finish"))
async def finish(message: Message) -> None:
    if not message.from_user or not is_grand_admin(message.from_user.id):
        await message.answer("Ruxsat yo'q.")
        return
    args = (message.text or "").split()
    if len(args) != 2:
        await message.answer("/finish <battle:contest_id|point:contest_id>")
        return
    try:
        kind, contest_id = parse_contest_ref(args[1])
        if kind is None:
            await message.answer("Contest turini aniq yozing: battle:12 yoki point:12")
            return
    except ValueError:
        await message.answer("Contest reference noto'g'ri.")
        return
    async with SessionLocal() as session:
        try:
            winner_id = await finish_contest(session, contest_id, kind=kind)
        except ValueError as exc:
            await message.answer(str(exc))
            return
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
    store = GameStore(SessionLocal)
    data = await store.load(chat_id)
    if not data:
        await message.answer("Bu chatda faol o'yin yo'q.")
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