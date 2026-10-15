from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from bot.config import config


class AdminFilter(BaseFilter):
    """Xabar faqat adminlardan kelganligini tekshiradi."""

    async def __call__(self, obj: Message | CallbackQuery) -> bool:
        if not obj.from_user:
            return False
        return obj.from_user.id in config.ADMIN_IDS
