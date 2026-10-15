from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from db.crud import (
    get_all_genres,
    get_genre_by_id,
    get_books_by_genre,
    get_latest_books,
    get_book_by_id,
    subscribe_to_book,
)
from bot.keyboards.inline import (
    get_genres_keyboard,
    get_books_list_keyboard,
    get_book_card_keyboard,
)
from bot.services.channel import format_channel_post_caption

router = Router(name="catalog_router")


@router.message(F.text == "📖 Janrlar")
async def show_genres(message: Message, session: AsyncSession):
    genres = await get_all_genres(session)
    if not genres:
        await message.answer("Hozircha janrlar kiritilmagan.")
        return

    await message.answer(
        "📚 Qaysi janrdagi kitoblarni ko'rmoqchisiz? Tanlang:",
        reply_markup=get_genres_keyboard(genres),
    )


@router.callback_query(F.data == "back_to_genres")
async def back_to_genres_cb(callback: CallbackQuery, session: AsyncSession):
    genres = await get_all_genres(session)
    await callback.message.edit_text(
        "📚 Qaysi janrdagi kitoblarni ko'rmoqchisiz? Tanlang:",
        reply_markup=get_genres_keyboard(genres),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("genre:"))
async def show_books_by_genre(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    genre_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0

    genre = await get_genre_by_id(session, genre_id)
    if not genre:
        await callback.answer("Janr topilmadi.", show_alert=True)
        return

    limit = 6
    offset = page * limit
    books, total_count = await get_books_by_genre(session, genre_id, limit=limit, offset=offset)

    if not books:
        await callback.message.edit_text(
            f"📖 <b>{genre.name}</b> janrida hozircha kitoblar mavjud emas.",
            parse_mode="HTML",
            reply_markup=get_genres_keyboard(await get_all_genres(session)),
        )
        await callback.answer()
        return

    kb = get_books_list_keyboard(
        books=books,
        page=page,
        total_count=total_count,
        prefix=f"genre:{genre_id}",
        limit=limit,
    )

    await callback.message.edit_text(
        f"📖 <b>{genre.name}</b> bo'limidagi kitoblar (jami: {total_count} ta):\n"
        f"Batafsil ma'lumot olish uchun kitob ustiga bosing:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await callback.answer()


@router.message(F.text == "🆕 Yangi kelganlar")
async def show_latest_books(message: Message, session: AsyncSession):
    books = await get_latest_books(session, limit=8)
    if not books:
        await message.answer("Hozircha sotuvda kitoblar mavjud emas.")
        return

    kb = get_books_list_keyboard(
        books=books,
        page=0,
        total_count=len(books),
        prefix="latest",
        limit=8,
    )

    await message.answer(
        "🆕 <b>Eng so'nggi qo'shilgan va mavjud kitoblar:</b>\n"
        "Batafsil ko'rish uchun tanlang:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("page:"))
async def handle_pagination(callback: CallbackQuery, session: AsyncSession):
    # Formats: page:genre:GENRE_ID:PAGE or page:latest:PAGE
    parts = callback.data.split(":")
    if parts[1] == "genre":
        genre_id = int(parts[2])
        page = int(parts[3])
        genre = await get_genre_by_id(session, genre_id)
        limit = 6
        offset = page * limit
        books, total_count = await get_books_by_genre(session, genre_id, limit=limit, offset=offset)
        kb = get_books_list_keyboard(books, page, total_count, f"genre:{genre_id}", limit)
        await callback.message.edit_text(
            f"📖 <b>{genre.name if genre else ''}</b> bo'limidagi kitoblar:\nTanlang:",
            parse_mode="HTML",
            reply_markup=kb,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("book_view:"))
async def view_book_details(callback: CallbackQuery, session: AsyncSession):
    book_id = int(callback.data.split(":")[1])
    book = await get_book_by_id(session, book_id)

    if not book:
        await callback.answer("Kitob topilmadi.", show_alert=True)
        return

    me = await callback.bot.get_me()
    caption = format_channel_post_caption(book, me.username or "kitob_bot")
    from bot.config import config
    is_admin = config.is_admin(callback.from_user.id)
    kb = get_book_card_keyboard(book, is_admin=is_admin)


    # Agar xabarda rasm bo'lmasa, yangi rasm bilan yuborishimiz mumkin
    try:
        await callback.message.delete()
    except Exception:
        pass

    if book.images and len(book.images) > 0:
        await callback.message.answer_photo(
            photo=book.images[0].telegram_file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb,
        )
    else:
        await callback.message.answer(
            text=caption,
            parse_mode="HTML",
            reply_markup=kb,
        )
    await callback.answer()


@router.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: CallbackQuery, session: AsyncSession):
    try:
        await callback.message.delete()
    except Exception:
        pass
    genres = await get_all_genres(session)
    await callback.message.answer(
        "📚 Qaysi janrdagi kitoblarni ko'rmoqchisiz? Tanlang:",
        reply_markup=get_genres_keyboard(genres),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sub_book:"))
async def subscribe_book(callback: CallbackQuery, session: AsyncSession, current_user):
    book_id = int(callback.data.split(":")[1])
    success = await subscribe_to_book(session, book_id, current_user.id)

    if success:
        await callback.answer(
            "✅ Siz ushbu kitobga obuna bo'ldingiz! Kitob sotuvga chiqishi bilan sizga bot orqali xabar beramiz.",
            show_alert=True,
        )
        book = await get_book_by_id(session, book_id)
        if book:
            await callback.message.edit_reply_markup(reply_markup=get_book_card_keyboard(book, is_subscribed=True))
    else:
        await callback.answer("Siz allaqachon ushbu kitob kelganda xabar olishga obuna bo'lgansiz.", show_alert=True)
