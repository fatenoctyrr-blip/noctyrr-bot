from __future__ import annotations

import random
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from redis.asyncio import Redis

from app.config import get_settings
from app.games.bunker import BunkerState
from app.games.mafia import MafiaPhase, MafiaState
from app.games.redis_store import GameStore

router = Router(name="games")
store = GameStore(Redis.from_url(get_settings().redis_url, decode_responses=True))


def lobby_keyboard(chat_id: int, game_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🙋 Qo'shilish", callback_data=f"game:join:{chat_id}")],
            [InlineKeyboardButton(text="▶️ Boshlash", callback_data=f"game:start:{chat_id}")],
        ]
    )


def player_keyboard(chat_id: int, players: dict[str, Any], prefix: str = "game:vote") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=str(player["display_name"])[:24],
                    callback_data=f"{prefix}:{chat_id}:{user_id}",
                )
            ]
            for user_id, player in players.items()
            if player.get("alive", player.get("active", True))
        ]
    )


async def create_lobby(message: Message, game_type: str) -> None:
    if game_type == "mafia":
        state = MafiaState(chat_id=message.chat.id).to_dict()
        title = "🔪 Mafia lobby ochildi. Kamida 5 o'yinchi kerak."
    else:
        state = BunkerState(chat_id=message.chat.id).to_dict()
        title = "🏚 Bunker lobby ochildi. O'yinchilar qo'shilsin."
    state["type"] = game_type
    await store.save(message.chat.id, state)
    await message.answer(title, reply_markup=lobby_keyboard(message.chat.id, game_type))


@router.message(Command("game"))
async def start_game(message: Message) -> None:
    args = (message.text or "").split()
    game_type = args[1].lower() if len(args) > 1 else ""
    if game_type in {"mafia", "bunker"}:
        await create_lobby(message, game_type)
    elif game_type == "jackpot":
        target = args[2] if len(args) > 2 else "777"
        if len(target) != 3 or not target.isdigit() or int(target) > 999:
            await message.answer("Jackpot kodi 000 dan 999 gacha bo'lgan 3 xonali raqam bo'lishi kerak.")
            return
        gift = "Admin sovg'asi"
        await store.save(
            message.chat.id,
            {"type": "jackpot", "chat_id": message.chat.id, "target": target, "gift": gift},
        )
        await message.answer(
            "🎰 777 Jackpot boshlandi. G'olib kombinatsiya yashirin.\n"
            "Spin tugmasini bosib urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Spin", callback_data=f"game:slot:{message.chat.id}")]
                ]
            ),
        )
    elif game_type == "guess":
        low = int(args[2]) if len(args) > 2 and args[2].isdigit() else 1
        high = int(args[3]) if len(args) > 3 and args[3].isdigit() else 100
        if low >= high:
            await message.answer("Diapazon noto'g'ri.")
            return
        await store.save(
            message.chat.id,
            {
                "type": "guess_number",
                "chat_id": message.chat.id,
                "low": low,
                "high": high,
                "secret": random.randint(low, high),
                "winner": None,
            },
        )
        await message.answer(f"🔢 Raqamni topish boshlandi! {low} dan {high} gacha. /guess <raqam>")
    elif game_type == "lottery":
        gift = "Admin sovg'asi"
        chance = 0.07
        if len(args) > 2:
            gift = args[2].replace("_", " ")
        if len(args) > 3:
            try:
                chance = float(args[3])
            except ValueError:
                await message.answer("Lotereya ehtimoli raqam bo'lishi kerak.")
                return
        if not 0 <= chance <= 100:
            await message.answer("Lotereya ehtimoli 0 dan 100 gacha bo'lishi kerak.")
            return
        await store.save(
            message.chat.id,
            {"type": "message_lottery", "chat_id": message.chat.id, "gift": gift, "chance": chance},
        )
        await message.answer(f"🎟 Xabar lotereyasi boshlandi. Ehtimol: {chance}%")
    else:
        await message.answer(
            "/game mafia\n/game bunker\n/game jackpot [777]\n/game guess [min] [max]\n/game lottery [gift] [chance_percent]"
        )


@router.message(Command("join_game"))
async def join_game(message: Message) -> None:
    if not message.from_user:
        return
    data = await store.load(message.chat.id)
    if not data or data.get("type") not in {"mafia", "bunker"}:
        await message.answer("Bu chatda faol Mafia yoki Bunker yo'q.")
        return
    if data["type"] == "mafia":
        state = MafiaState.from_dict(data)
        added = state.add_player(message.from_user.id, message.from_user.full_name)
        await store.save(message.chat.id, state.to_dict() | {"type": "mafia"})
    else:
        state = BunkerState.from_dict(data)
        added = state.add_player(message.from_user.id, message.from_user.full_name)
        await store.save(message.chat.id, state.to_dict() | {"type": "bunker"})
    await message.answer("✅ O'yinga qo'shildingiz." if added else "Siz avval qo'shilgansiz yoki o'yin boshlangan.")


@router.callback_query(F.data.startswith("game:join:"))
async def join_game_callback(callback: CallbackQuery) -> None:
    if callback.message:
        await callback.message.answer("Qo'shilish uchun /join_game buyrug'ini yuboring.")
    await callback.answer()


@router.callback_query(F.data.startswith("game:start:"))
async def start_lobby_callback(callback: CallbackQuery) -> None:
    chat_id = int(callback.data.rsplit(":", 1)[1])
    data = await store.load(chat_id)
    if not data:
        await callback.answer("Lobby topilmadi.", show_alert=True)
        return
    if data["type"] == "mafia":
        state = MafiaState.from_dict(data)
        if not state.start():
            await callback.answer("Mafia uchun kamida 5 o'yinchi kerak.", show_alert=True)
            return
        state.phase = MafiaPhase.DAY
        await store.save(chat_id, state.to_dict() | {"type": "mafia"})
        for player in state.players.values():
            try:
                await callback.bot.send_message(
                    player.user_id,
                    f"🔐 Mafia o'yinidagi rolingiz: <b>{player.role}</b>\n"
                    "O'yin davomida rolingizni oshkor qilmang.",
                )
            except TelegramAPIError:
                # The user may not have opened the bot in private chat yet.
                pass
        await callback.message.answer(
            "🌞 Kun fazasi. Kimni chiqarishni tanlang:",
            reply_markup=player_keyboard(chat_id, state.to_dict()["players"]),
        )
    else:
        state = BunkerState.from_dict(data)
        if len(state.players) < 3:
            await callback.answer("Bunker uchun kamida 3 o'yinchi kerak.", show_alert=True)
            return
        state.round_no = 1
        await store.save(chat_id, state.to_dict() | {"type": "bunker"})
        for player in state.players.values():
            cards = "\n".join(f"• {key}: {value}" for key, value in player.cards.items())
            try:
                await callback.bot.send_message(
                    player.user_id,
                    f"🔐 Bunker kartalaringiz:\n{cards}",
                )
            except TelegramAPIError:
                # The user may not have opened the bot in private chat yet.
                pass
        await callback.message.answer(
            "🏚 1-raund. Ovoz berib bunkerdan chiqariladigan o'yinchini tanlang:",
            reply_markup=player_keyboard(chat_id, state.to_dict()["players"]),
        )
    await callback.answer("O'yin boshlandi.")


@router.callback_query(F.data.startswith("game:vote:"))
async def vote_callback(callback: CallbackQuery) -> None:
    _, _, chat_raw, target_raw = callback.data.split(":")
    chat_id, target_id = int(chat_raw), int(target_raw)
    if not callback.from_user:
        return
    data = await store.load(chat_id)
    if not data:
        await callback.answer("O'yin tugagan.", show_alert=True)
        return
    voter_id = callback.from_user.id
    if data["type"] == "mafia":
        state = MafiaState.from_dict(data)
        if not state.cast_vote(voter_id, target_id):
            await callback.answer("Ovoz berib bo'lmaydi.", show_alert=True)
            return
        alive_ids = {user_id for user_id, player in state.players.items() if player.alive}
        if alive_ids <= set(state.votes):
            eliminated = state.resolve_day()
            winner = state.winner()
            if winner:
                state.phase = MafiaPhase.FINISHED
                await store.delete(chat_id)
                await callback.message.answer(
                    f"⚖️ Ovoz natijasi: {eliminated} chiqarildi.\n"
                    f"🏆 G'olib: {winner}"
                )
            else:
                await store.save(chat_id, state.to_dict() | {"type": "mafia"})
                await callback.message.answer(f"⚖️ Ovoz natijasi: {eliminated} chiqarildi.")
        else:
            await store.save(chat_id, state.to_dict() | {"type": "mafia"})
            await callback.answer("Ovozingiz saqlandi.")
    else:
        state = BunkerState.from_dict(data)
        if not state.vote(voter_id, target_id):
            await callback.answer("Ovoz berib bo'lmaydi.", show_alert=True)
            return
        active_ids = {user_id for user_id, player in state.players.items() if player.active}
        if active_ids <= set(state.votes):
            removed = state.resolve_round()
            active_count = sum(player.active for player in state.players.values())
            if active_count <= 1:
                await store.delete(chat_id)
                await callback.message.answer(
                    f"🚪 {removed} bunkerdan chiqarildi.\n"
                    f"🏆 Bunker g'olibi: {next(player.display_name for player in state.players.values() if player.active)}"
                )
            else:
                await store.save(chat_id, state.to_dict() | {"type": "bunker"})
                await callback.message.answer(
                    f"🚪 {removed} bunkerdan chiqarildi. Raund: {state.round_no}"
                )
        else:
            await store.save(chat_id, state.to_dict() | {"type": "bunker"})
            await callback.answer("Ovozingiz saqlandi.")


@router.callback_query(F.data.startswith("game:slot:"))
async def jackpot_callback(callback: CallbackQuery) -> None:
    chat_id = int(callback.data.rsplit(":", 1)[1])
    data = await store.load(chat_id)
    if not data or data.get("type") != "jackpot":
        await callback.answer("Jackpot tugagan.", show_alert=True)
        return
    result = f"{random.randint(0, 999):03d}"
    if result == data["target"]:
        await store.delete(chat_id)
        await callback.message.answer(f"🎉 {result}! G'olib: {callback.from_user.full_name}")
    else:
        await callback.message.answer(f"🎰 {callback.from_user.full_name}: {result}")
    await callback.answer()


@router.message(Command("guess"))
async def guess_number(message: Message) -> None:
    args = (message.text or "").split()
    if len(args) != 2 or not args[1].lstrip("-").isdigit():
        await message.answer("/guess <raqam>")
        return
    data = await store.load(message.chat.id)
    if not data or data.get("type") != "guess_number":
        await message.answer("Faol raqam topish o'yini yo'q.")
        return
    guess = int(args[1])
    if guess == data["secret"]:
        await store.delete(message.chat.id)
        await message.answer(f"🎉 To'g'ri! G'olib: {message.from_user.full_name}")
    else:
        await message.answer("❌ Noto'g'ri.")


@router.message(F.text & ~F.text.startswith("/"))
async def message_lottery(message: Message) -> None:
    data = await store.load(message.chat.id)
    if not data or data.get("type") != "message_lottery" or not message.from_user:
        return
    if random.random() * 100 < float(data["chance"]):
        await store.delete(message.chat.id)
        await message.answer(
            f"🎉 Lotereyada g'olib: {message.from_user.full_name}\nSovg'a: {data['gift']}"
        )