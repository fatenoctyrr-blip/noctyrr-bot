from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db import SessionLocal
from app.services.users import ensure_user, register_referral

router = Router(name="user")


@router.message(Command("start"))
async def start(message: Message) -> None:
    if message.from_user:
        async with SessionLocal() as session:
            user = await ensure_user(session, message.from_user)
            args = (message.text or "").split(maxsplit=1)
            if len(args) == 2 and args[1].startswith("ref_"):
                try:
                    await register_referral(session, user, int(args[1].removeprefix("ref_")))
                except ValueError:
                    pass
            await session.commit()
    await message.answer(
        "Assalomu alaykum! 🎮\n"
        "Bu o'yinlar va konkurslar botidir.\n\n"
        "/games — o'yinlar\n"
        "/help — yordam\n"
        "/game mafia — Mafia\n"
        "/game bunker — Bunker\n"
        "/game jackpot — 777 Jackpot"
    )


@router.message(Command("games"))
async def games(message: Message) -> None:
    await message.answer(
        "🎮 O'yinlar:\n"
        "• Mafia — rollar, tun/kunduz va ovoz berish\n"
        "• Bunker — maxfiy xarakteristikalar va raundlar\n"
        "• 777 Jackpot — tasodifiy slot\n"
        "• Guess — raqamni topish\n"
        "• Lottery — xabarlar orqali ehtimolli lotereya"
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "Adminlar:\n"
        "/connect\n"
        "/contest Vazifa | target=50 | minutes=120\n"
        "/point_contest Sovg'a | minutes=60\n"
        "/stop_contest <id>\n\n"
        "O'yinchilar:\n"
        "/game mafia|bunker|jackpot\n"
        "/join_game\n"
        "/guess <number>\n"
        "/leaderboard <contest_id>"
    )


@router.message(Command("leaderboard"))
async def leaderboard_help(message: Message) -> None:
    await message.answer("Reytingni konkurs postidagi 📊 Reyting tugmasi orqali ko'ring.")