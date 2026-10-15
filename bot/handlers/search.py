from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from db.crud import get_all_books_for_search, log_search, get_book_by_id
from bot.services.search import search_books
from bot.keyboards.inline import get_books_list_keyboard, get_no_search_result_keyboard
from bot.keyboards.default import get_cancel_keyboard, get_main_menu_keyboard
from bot.config import config
from bot.services.channel import format_channel_post_caption

router = Router(name="search_router")


class SearchState(StatesGroup):
    waiting_for_query = State()


@router.message(F.text == "🔍 Kitob qidirish")
async def start_search_prompt(message: Message, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await message.answer(
        "🔍 <b>Kitob qidirish:</b>\n\n"
        "Kitob nomi yoki muallif ismini yozing (lotin yoki kirill alifbosida):\n"
        "<i>Masalan: «O'tkan kunlar», «Stiv Jobs», «Dasturlash»...</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.callback_query(F.data == "search_again")
async def search_again_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await callback.message.answer(
        "Qidirmoqchi bo'lgan kitob yoki muallif nomini kiriting:",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(F.text == "❌ Bekor qilish")
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    is_admin = config.is_admin(message.from_user.id)
    await message.answer(
        "Amal bekor qilindi. Bosh menyudasiz.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )


@router.message(SearchState.waiting_for_query)
async def process_search_query(message: Message, session: AsyncSession, state: FSMContext, current_user):
    query = message.text.strip()
    if not query or query == "❌ Bekor qilish":
        await cancel_action(message, state)
        return

    await state.clear()
    await execute_search(message, session, query, user_id=current_user.id if current_user else None)


# Agar foydalanuvchi menyudan emas, shunchaki chatga biror kitob nomini yozsa ham qidirsin
@router.message(F.text & ~F.text.startswith("/"))
async def handle_direct_text_search(message: Message, session: AsyncSession, state: FSMContext, current_user):

    current_state = await state.get_state()
    if current_state is not None:
        return


    # Admin bo'lsa xaridorlik qidiruviga tushmasin
    if config.is_admin(message.from_user.id):
        return


    # Asosiy menyu tugmalari bo'lsa, ularni o'tkazib yuboramiz

    menu_buttons = [
        "🔍 Kitob qidirish",
        "📖 Janrlar",
        "🆕 Yangi kelganlar",
        "📦 Mening buyurtmalarim",
        "📞 Biz haqimizda",
        "⚙️ Admin panel",
        "◀️ Foydalanuvchi menyusi",
        "➕ Yangi kitob qo'shish",
        "📚 Kitoblar ro'yxati",
        "📋 Buyurtmalar",
        "📊 Statistika",
        "🔍 Topilmagan so'rovlar",
    ]
    if message.text in menu_buttons:
        return

    query = message.text.strip()
    await execute_search(message, session, query, user_id=current_user.id if current_user else None)


async def execute_search(message: Message, session: AsyncSession, query: str, user_id: int | None = None):
    all_books = await get_all_books_for_search(session)
    results = search_books(query, all_books, threshold=60.0)

    is_admin = config.is_admin(message.from_user.id)
    menu_kb = get_main_menu_keyboard(is_admin=is_admin)

    if not results:
        # Baza uchun qidiruv tarixiga yozish (topilmadi)
        await log_search(session, query, found=False, user_id=user_id)

        await message.answer(
            f"😔 Afsuski, <b>«{query}»</b> bo'yicha hech qanday kitob topilmadi.\n\n"
            f"Siz bu kitobni buyurtma/taklif sifatida qoldirishingiz mumkin, "
            f"tez orada uni do'konimizga olib kelishga harakat qilamiz!",
            parse_mode="HTML",
            reply_markup=get_no_search_result_keyboard(query),
        )
        return

    # Muvaffaqiyatli qidiruvni qayd etish
    await log_search(session, query, found=True, user_id=user_id)

    books = [b for b, _ in results[:6]]
    kb = get_books_list_keyboard(
        books=books,
        page=0,
        total_count=len(results),
        prefix=f"srch:{query[:15]}",
        limit=6,
    )

    await message.answer(
        f"🔍 <b>«{query}»</b> bo'yicha topilgan natijalar (jami: {len(results)} ta):\n\n"
        f"Kitob haqida batafsil ma'lumot olish uchun tanlang:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("suggest:"))
async def handle_suggest(callback: CallbackQuery):
    query = callback.data.split(":")[1]
    await callback.message.edit_text(
        f"✍️ <b>Rahmat!</b> Siz qidirgan <b>«{query}»</b> kitobi e'tiborga olindi.\n"
        f"Kitob do'konga keltirilgach, yangiliklar kanalimizda e'lon qilinadi!",
        parse_mode="HTML",
    )
    await callback.answer()


# ===================== INLINE QUERY HANDLER =====================

@router.inline_query()
async def inline_search_handler(inline_query: InlineQuery, session: AsyncSession):
    query = inline_query.query.strip()
    all_books = await get_all_books_for_search(session)

    if not query:
        # Bo'sh bo'lsa so'nggi faol kitoblarni chiqaramiz
        target_books = [b for b in all_books if b.quantity > 0][:10]
    else:
        results = search_books(query, all_books, threshold=55.0)
        target_books = [b for b, _ in results[:15]]

    articles = []
    me = await inline_query.bot.get_me()
    bot_username = me.username or "kitob_bot"

    for book in target_books:
        status_text = f"Mavjud ({book.quantity} ta)" if book.quantity > 0 else "Tugagan"
        price_str = f"{book.price:,} so'm".replace(",", " ")

        caption = format_channel_post_caption(book, bot_username)

        article = InlineQueryResultArticle(
            id=str(book.id),
            title=f"{book.title} — {price_str}",
            description=f"Muallif: {book.author} | {status_text}",
            thumbnail_url=None,
            input_message_content=InputTextMessageContent(
                message_text=caption,
                parse_mode="HTML",
            ),
        )
        articles.append(article)

    await inline_query.answer(
        results=articles,
        cache_time=10,
        is_personal=True,
    )
