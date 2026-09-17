from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError


@dataclass(frozen=True)
class RequirementResult:
    ok: bool
    missing: list[str]


async def check_requirements(
    bot: Bot,
    user_id: int,
    requirements: list[tuple[int, str | None]],
) -> RequirementResult:
    """Check all required channels/groups using Telegram getChatMember."""
    missing: list[str] = []
    for chat_id, title in requirements:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            allowed = member.status in {
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR,
            }
        except TelegramAPIError:
            allowed = False
        if not allowed:
            missing.append(title or str(chat_id))
    return RequirementResult(ok=not missing, missing=missing)