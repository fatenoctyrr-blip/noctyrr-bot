from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, MessageReactionUpdated
from sqlalchemy import select

from app.db import SessionLocal
from app.models import BattleContest, ContestStatus, PointContest, User
from app.services.contests import (
    add_points,
    add_requirement,
    create_battle,
    create_point_contest,
    finish_contest,
    join_battle,
    leaderboard,
    requirements_for,
)
from app.services.permissions import is_chat_admin
from app.services.subscriptions import check_requirements
from app.services.users import ensure_channel, ensure_user

router = Router(name="contests")


def options(text: str) -> dict[str, str]:
    return {
        match.group(1).lower(): match.group(2).strip()
        for match in re.finditer(r"(target|minutes|requirements|weights)\s*=\s*([^|]+)", text)
    }


def contest_text(contest: BattleContest | PointContest) -> str:
    if isinstance(contest, BattleContest):
        target = f"\nMaqsad: {contest.target_count}" if contest.target_count else ""
        end = f"\nTugash: {contest.end_time:%Y-%m-%d %H:%M} UTC" if contest.end_time else ""
        return f"🎁 Battle konkurs #{contest.id}\n\n{contest.task}{target}{end}\n\nQatnashing:"
    end = f"\nTugash: {contest.end_time:%Y-%m-%d %H:%M} UTC" if contest.end_time else ""
    return f"🏆 Ballik konkurs #{contest.id}\n\nSovg'a: {contest.gift}{end}\n\nQatnashing:"


async def post_battle(message: Message, contest_id: int) -> None:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    sent = await message.answer(
        contest_text(await _get_contest(contest_id)),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Qatnashish", callback_data=f"battle:join:{contest_id}")]
            ]
        ),
    )
    async with SessionLocal() as session:
        contest = await session.get(BattleContest, contest_id)
        contest.post_chat_id = sent.chat.id
        contest.post_message_id = sent.message_id
        await session.commit()


async def _get_contest(contest_id: int) -> BattleContest | PointContest:
    async with SessionLocal() as session:
        contest = await session.get(BattleContest, contest_id)
        if contest:
            return contest
        contest = await session.get(PointContest, contest_id)
        if contest:
            return contest
    raise ValueError("Contest not found")


@router.message(Command("contest"))
async def create_battle_command(message: Message) -> None:
    if not message.from_user or not await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("Battle konkursini faqat chat admini yaratishi mumkin.")
        return
    raw = (message.text or "").removeprefix("/contest").strip()
    if not raw or "|" not in raw:
        await message.answer(
            "Format:\n/contest Vazifa matni | target=100 | minutes=60 | requirements=-1001,-1002"
        )
        return
    task, *tail = [part.strip() for part in raw.split("|")]
    config = options("|".join(tail))
    target = int(config["target"]) if config.get("target", "").isdigit() else None
    minutes = int(config["minutes"]) if config.get("minutes", "").isdigit() else None
    async with SessionLocal() as session:
        owner = await ensure_user(session, message.from_user)
        channel = await ensure_channel(session, message.chat.id, owner, message.chat.title)
        contest = await create_battle(session, channel, task, owner.id, target, minutes)
        for resource in config.get("requirements", "").split(","):
            if resource.strip():
                await add_requirement(session, contest.id, int(resource.strip()), resource.strip())
        await session.commit()
        contest_id = contest.id
    await post_battle(message, contest_id)


@router.message(Command("point_contest"))
async def create_point_command(message: Message) -> None:
    if not message.from_user or not await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("Ballik konkursni faqat chat admini yaratishi mumkin.")
        return
    raw = (message.text or "").removeprefix("/point_contest").strip()
    if not raw or "|" not in raw:
        await message.answer(
            "Format:\n/point_contest Sovg'a | minutes=60 | "
            "weights=reaction:1,stars:5,boost:1,comment:1,purchased:1"
        )
        return
    gift, *tail = [part.strip() for part in raw.split("|")]
    config = options("|".join(tail))
    weights = {"reaction": 1, "stars": 5, "boost": 1, "comment": 1, "purchased": 1}
    for item in config.get("weights", "").split(","):
        if ":" in item:
            key, value = item.split(":", 1)
            if key.strip() in weights and value.strip().isdigit():
                weights[key.strip()] = int(value.strip())
    minutes = int(config["minutes"]) if config.get("minutes", "").isdigit() else None
    async with SessionLocal() as session:
        owner = await ensure_user(session, message.from_user)
        channel = await ensure_channel(session, message.chat.id, owner, message.chat.title)
        contest = await create_point_contest(session, channel, gift, owner.id, weights, minutes)
        await session.commit()
        contest_id = contest.id
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    sent = await message.answer(
        contest_text(await _get_contest(contest_id)),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Qatnashish", callback_data=f"point:join:{contest_id}")],
                [InlineKeyboardButton(text="📊 Reyting", callback_data=f"point:rank:{contest_id}")],
            ]
        ),
    )
    async with SessionLocal() as session:
        contest = await session.get(PointContest, contest_id)
        contest.post_chat_id = sent.chat.id
        contest.post_message_id = sent.message_id
        await session.commit()


async def _check_subscriptions(callback: CallbackQuery, contest_id: int) -> bool:
    async with SessionLocal() as session:
        requirements = await requirements_for(session, contest_id)
    if not requirements:
        return True
    result = await check_requirements(callback.bot, callback.from_user.id, requirements)
    if not result.ok:
        await callback.answer("Avval obuna bo'ling: " + ", ".join(result.missing), show_alert=True)
    return result.ok


@router.callback_query(F.data.startswith("battle:join:"))
async def join_battle_callback(callback: CallbackQuery) -> None:
    contest_id = int(callback.data.rsplit(":", 1)[1])
    if not await _check_subscriptions(callback, contest_id):
        return
    async with SessionLocal() as session:
        user = await ensure_user(session, callback.from_user)
        joined, count, reached = await join_battle(session, contest_id, user.id)
    await callback.answer(f"Qabul qilindi. Ishtirokchilar: {count}" if joined else "Siz allaqachon qatnashgansiz yoki konkurs yopilgan.")
    if reached and callback.message:
        await callback.message.answer("🎉 Maqsadli ishtirokchi soniga yetildi. Konkurs yakunlandi.")


@router.callback_query(F.data.startswith("point:join:"))
async def join_point_callback(callback: CallbackQuery) -> None:
    contest_id = int(callback.data.rsplit(":", 1)[1])
    if not await _check_subscriptions(callback, contest_id):
        return
    async with SessionLocal() as session:
        contest = await session.get(PointContest, contest_id)
        if not contest or contest.status != ContestStatus.ACTIVE:
            await callback.answer("Konkurs yopilgan.", show_alert=True)
            return
        await ensure_user(session, callback.from_user)
        await session.commit()
    await callback.answer("Ballik konkursga qo'shildingiz!")


@router.callback_query(F.data.startswith("point:rank:"))
async def point_ranking_callback(callback: CallbackQuery) -> None:
    contest_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        rows = await leaderboard(session, contest_id)
        text = "\n".join(f"{idx}. user_id={entry.user_id}: {score} ball" for idx, (entry, score) in enumerate(rows, 1))
    await callback.answer("Reyting tayyor.")
    if callback.message:
        await callback.message.answer("📊 Reyting\n" + (text or "Hali ballar yo'q."))


@router.message(Command("add_points"))
async def add_points_command(message: Message) -> None:
    args = (message.text or "").split()
    if len(args) != 5 or not message.from_user:
        await message.answer("/add_points <contest_id> <telegram_user_id> <kind> <amount>")
        return
    if not await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("Faqat admin.")
        return
    contest_id, telegram_id, kind, amount = int(args[1]), int(args[2]), args[3], int(args[4])
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            await message.answer("Foydalanuvchi avval botdan foydalangan bo'lishi kerak.")
            return
        entry = await add_points(session, contest_id, user.id, kind, amount)
        await session.commit()
    await message.answer(f"Ball qo'shildi. Jami xom ball: {entry.total}")


@router.message(Command("stop_contest"))
async def stop_contest_command(message: Message) -> None:
    args = (message.text or "").split()
    if len(args) != 2 or not message.from_user:
        await message.answer("/stop_contest <contest_id>")
        return
    if not await is_chat_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("Faqat admin.")
        return
    async with SessionLocal() as session:
        winner_id = await finish_contest(session, int(args[1]))
    await message.answer(f"Konkurs tugadi. G'olib: {winner_id or 'aniqlanmadi'}")


@router.message(F.reply_to_message)
async def count_comment(message: Message) -> None:
    if not message.from_user or not message.reply_to_message:
        return
    async with SessionLocal() as session:
        contest = await session.scalar(
            select(PointContest).where(
                PointContest.post_chat_id == message.chat.id,
                PointContest.post_message_id == message.reply_to_message.message_id,
                PointContest.status == ContestStatus.ACTIVE,
            )
        )
        if not contest:
            return
        user = await ensure_user(session, message.from_user)
        await add_points(session, contest.id, user.id, "comment", 1)
        await session.commit()


@router.message_reaction()
async def count_reaction(event: MessageReactionUpdated) -> None:
    if not event.user:
        return
    async with SessionLocal() as session:
        contest = await session.scalar(
            select(PointContest).where(
                PointContest.post_chat_id == event.chat.id,
                PointContest.post_message_id == event.message_id,
                PointContest.status == ContestStatus.ACTIVE,
            )
        )
        if not contest:
            return
        user = await session.scalar(select(User).where(User.telegram_id == event.user.id))
        if not user:
            return
        delta = max(0, len(event.new_reaction) - len(event.old_reaction))
        if delta:
            await add_points(session, contest.id, user.id, "reaction", delta)
            await session.commit()