import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Book
from db.crud import save_channel_post, get_channel_post_by_book_id

logger = logging.getLogger(__name__)


def format_channel_post_caption(book: Book, bot_username: str) -> str:
    """Kanal posti uchun chiroyli matn shakllantiradi (kitob va boshqa mahsulotlar uchun moslashadi)."""
    genre_name = book.genre.name if book.genre else ""
    is_stationery = any(
        term in genre_name.lower()
        for term in ["o'quv", "bloknot", "daftar", "kantselyariya", "aksessuar", "qurol"]
    )

    icon = "📓" if "bloknot" in genre_name.lower() or "daftar" in genre_name.lower() else ("✏️" if is_stationery else "📚")
    author_label = "🏷 <b>Brend / Ishlab chiqaruvchi:</b>" if is_stationery else "✍️ <b>Muallif:</b>"
    genre_label = "📂 <b>Bo'lim:</b>" if is_stationery else "📂 <b>Janr:</b>"

    genre_text = f"{genre_label} #{genre_name.replace(' ', '_')}" if genre_name else ""
    
    if book.quantity > 0:
        status_text = f"✅ <b>Holati:</b> Mavjud ({book.quantity} ta)"
    else:
        status_text = "❌ <b>Holati:</b> Sotildi (Hozirda tugagan)"

    price_formatted = f"{book.price:,}".replace(",", " ")

    lines = [
        f"{icon} <b>{book.title}</b>",
        f"{author_label} {book.author}" if book.author else None,
        genre_text,
        f"💰 <b>Narxi:</b> {price_formatted} so'm",
        status_text,
    ]

    # Bo'sh qatorlarni tozalash
    lines = [line for line in lines if line]


    if book.description:
        desc = book.description.strip()
        if len(desc) > 500:
            desc = desc[:497] + "..."
        lines.append(f"\n📖 <b>Tavsif:</b>\n<i>{desc}</i>")

    lines.append(f"\n👉 Buyurtma berish uchun quyidagi tugmani bosing:")
    return "\n".join(lines)


def get_channel_post_keyboard(book: Book, bot_username: str) -> InlineKeyboardMarkup:
    """Kanal posti uchun 'Buyurtma berish' tugmasi."""
    order_url = f"https://t.me/{bot_username}?start=book_{book.id}"
    buttons = [
        [InlineKeyboardButton(text="🛒 Buyurtma berish", url=order_url)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def publish_book_to_channel(
    bot: Bot,
    session: AsyncSession,
    book: Book,
    channel_id: str,
) -> Optional[int]:
    """Kitobni kanalga joylaydi va message_id ni bazaga saqlaydi."""
    if not channel_id:
        logger.warning("CHANNEL_ID belgilanmagan, kanalga joylash o'tkazib yuborildi.")
        return None

    try:
        me = await bot.get_me()
        bot_username = me.username or "kitob_bot"
        caption = format_channel_post_caption(book, bot_username)
        keyboard = get_channel_post_keyboard(book, bot_username)

        msg = None
        if book.images and len(book.images) > 0:
            first_image = book.images[0].telegram_file_id
            msg = await bot.send_photo(
                chat_id=channel_id,
                photo=first_image,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            msg = await bot.send_message(
                chat_id=channel_id,
                text=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        if msg:
            await save_channel_post(session, book.id, msg.message_id)
            return msg.message_id
    except Exception as e:
        logger.error(f"Kanalga post yuborishda xatolik: {e}")
        return None


async def update_channel_post_if_exists(
    bot: Bot,
    session: AsyncSession,
    book: Book,
    channel_id: str,
):
    """Kitob tahrirlanganda yoki zaxira tugaganda kanaldagi postni yangilaydi."""
    if not channel_id:
        return

    try:
        channel_post = await get_channel_post_by_book_id(session, book.id)
        if not channel_post:
            return

        me = await bot.get_me()
        bot_username = me.username or "kitob_bot"
        caption = format_channel_post_caption(book, bot_username)
        keyboard = get_channel_post_keyboard(book, bot_username)

        # Agar rasm bo'lsa editCaption, aks holda editText
        if book.images and len(book.images) > 0:
            await bot.edit_message_caption(
                chat_id=channel_id,
                message_id=channel_post.channel_message_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            await bot.edit_message_text(
                chat_id=channel_id,
                message_id=channel_post.channel_message_id,
                text=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
    except Exception as e:
        logger.warning(f"Kanal postini yangilashda xatolik (xabar o'chirilgan bo'lishi mumkin): {e}")


async def delete_channel_post_if_exists(
    bot: Bot,
    session: AsyncSession,
    book_id: int,
    channel_id: str,
):
    """Kitob o'chirilganda kanaldagi postni ham o'chiradi."""
    if not channel_id:
        return

    try:
        channel_post = await get_channel_post_by_book_id(session, book_id)
        if not channel_post:
            return

        await bot.delete_message(
            chat_id=channel_id,
            message_id=channel_post.channel_message_id,
        )
    except Exception as e:
        logger.warning(f"Kanal postini o'chirishda xatolik: {e}")
