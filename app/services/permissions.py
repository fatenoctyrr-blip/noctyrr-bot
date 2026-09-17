from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError

from app.config import get_settings


async def is_chat_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    if user_id == get_settings().grand_admin_id:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramAPIError:
        return False
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


def is_grand_admin(user_id: int) -> bool:
    return user_id == get_settings().grand_admin_id