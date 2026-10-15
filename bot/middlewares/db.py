from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from db.session import async_session_maker
from db.crud import get_or_create_user
from bot.config import config


class DatabaseMiddleware(BaseMiddleware):
    """
    Har bir kelgan xabar/callback uchun SQLAlchemy async session ochadi
    va avtomatik tarzda bazadagi foydalanuvchi ma'lumotlarini taqdim etadi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session

            # Foydalanuvchini bazada tekshirish va yaratish
            event_user: TgUser = data.get("event_from_user")
            if event_user and not event_user.is_bot:
                role = "admin" if event_user.id in config.ADMIN_IDS else "customer"
                user = await get_or_create_user(
                    session=session,
                    telegram_id=event_user.id,
                    full_name=event_user.full_name or "Foydalanuvchi",
                    username=event_user.username,
                    role=role,
                )
                data["current_user"] = user

            return await handler(event, data)
