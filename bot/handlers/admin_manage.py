from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from bot.middlewares.admin_only import AdminFilter
from bot.keyboards.admin_kb import (
    get_admin_main_keyboard,
    get_admin_books_keyboard,
    get_admin_book_actions_keyboard,
)
from bot.keyboards.default import get_cancel_keyboard
from db.crud import (
    get_all_books_admin,
    get_book_by_id,
    update_book_stock,
    set_book_quantity,
    update_book_price,
    delete_book,
    get_admin_stats,
    get_unfound_searches,
    get_pending_subscribers,
    mark_subscribers_notified,
)
from bot.services.channel import (
    update_channel_post_if_exists,
    delete_channel_post_if_exists,
    publish_book_to_channel,
    format_channel_post_caption,
)
from bot.services.notify import notify_subscribers_book_available
from bot.config import config

router = Router(name="admin_manage_router")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


class AdminEditState(StatesGroup):
    waiting_for_new_price = State()
    waiting_for_new_qty = State()


@router.message(F.text == "⚙️ Admin panel")
async def show_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🛠 <b>Admin boshqaruv paneliga xush kelibsiz!</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=get_admin_main_keyboard(),
    )


@router.message(F.text.in_(["📚 Barcha mahsulotlar", "📚 Kitoblar ro'yxati", "📚 Kitoblar va Mahsulotlar"]))
async def show_admin_books(message: Message, session: AsyncSession):

    limit = 6
    books, total = await get_all_books_admin(session, limit=limit, offset=0)

    if not books:
        await message.answer("Bazada hali hech qanday kitob mavjud emas.")
        return

    kb = get_admin_books_keyboard(books, page=0, total_count=total, limit=limit)
    await message.answer(
        f"📚 <b>Barcha kitoblar (jami: {total} ta):</b>\n"
        "Boshqarish yoki zaxirani o'zgartirish uchun kitobni tanlang:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("adm_bpage:"))
async def handle_admin_books_page(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split(":")[1])
    limit = 6
    offset = page * limit
    books, total = await get_all_books_admin(session, limit=limit, offset=offset)

    kb = get_admin_books_keyboard(books, page=page, total_count=total, limit=limit)
    await callback.message.edit_text(
        f"📚 <b>Barcha kitoblar (jami: {total} ta):</b>\n"
        "Boshqarish uchun tanlang:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_book:"))
async def view_admin_book_item(callback: CallbackQuery, session: AsyncSession):
    book_id = int(callback.data.split(":")[1])
    book = await get_book_by_id(session, book_id)

    if not book:
        await callback.answer("Kitob topilmadi.", show_alert=True)
        return

    me = await callback.bot.get_me()
    caption = format_channel_post_caption(book, me.username or "kitob_bot")
    channel_status = (
        f"\n📢 <b>Kanal posti:</b> Bog'langan (ID: {book.channel_post.channel_message_id})"
        if book.channel_post
        else "\n⚠️ <b>Kanal posti:</b> Joylanmagan"
    )

    full_text = f"⚙️ <b>KITOBNI BOSHQARISH</b>\n{caption}\n{channel_status}"
    kb = get_admin_book_actions_keyboard(book)

    await callback.message.edit_text(
        text=full_text,
        parse_mode="HTML",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_stock:"))
async def handle_stock_delta(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    book_id = int(parts[1])
    delta = int(parts[2])

    old_book = await get_book_by_id(session, book_id)
    was_zero = old_book.quantity == 0 if old_book else False

    book = await update_book_stock(session, book_id, delta)
    if not book:
        await callback.answer("Kitob topilmadi.", show_alert=True)
        return

    # Kanaldagi postni ham yangilaymiz (agar mavjud bo'lsa)
    await update_channel_post_if_exists(callback.bot, session, book, config.CHANNEL_ID)

    # Agar kitob 0 bo'lib, endi soni oshgan bo'lsa, obunachilarga xabar yuboramiz
    if was_zero and book.quantity > 0:
        subscribers = await get_pending_subscribers(session, book.id)
        if subscribers:
            await notify_subscribers_book_available(callback.bot, book, subscribers)
            await mark_subscribers_notified(session, book.id)

    # Tugmalarni yangilash
    await callback.message.edit_reply_markup(reply_markup=get_admin_book_actions_keyboard(book))
    await callback.answer(f"Zaxira: {book.quantity} dona")


@router.callback_query(F.data.startswith("adm_edit_price:"))
async def start_edit_price(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[1])
    await state.set_state(AdminEditState.waiting_for_new_price)
    await state.update_data(edit_book_id=book_id)

    await callback.message.answer(
        "💰 Yangi narxni kiriting (so'mda, faqat raqam):",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminEditState.waiting_for_new_price)
async def process_new_price(message: Message, session: AsyncSession, state: FSMContext):
    text = message.text.replace(" ", "").replace(",", "").strip()
    if text == "❌Bekorqilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return

    if not text.isdigit() or int(text) <= 0:
        await message.answer("Iltimos, musbat raqam kiriting:")
        return

    new_price = int(text)
    data = await state.get_data()
    book_id = data["edit_book_id"]

    book = await update_book_price(session, book_id, new_price)
    await state.clear()

    if book:
        await update_channel_post_if_exists(message.bot, session, book, config.CHANNEL_ID)
        await message.answer(
            f"✅ <b>«{book.title}»</b> kitobining narxi {new_price:,} so'mga yangilandi!".replace(",", " "),
            parse_mode="HTML",
            reply_markup=get_admin_main_keyboard(),
        )


@router.callback_query(F.data.startswith("adm_edit_qty:"))
async def start_edit_qty(callback: CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split(":")[1])
    await state.set_state(AdminEditState.waiting_for_new_qty)
    await state.update_data(edit_book_id=book_id)

    await callback.message.answer(
        "🔢 Yangi zaxira miqdorini kiriting (masalan: 10):",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminEditState.waiting_for_new_qty)
async def process_new_qty(message: Message, session: AsyncSession, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return

    if not text.isdigit() or int(text) < 0:
        await message.answer("Iltimos, musbat butun son kiriting:")
        return

    new_qty = int(text)
    data = await state.get_data()
    book_id = data["edit_book_id"]

    book = await set_book_quantity(session, book_id, new_qty)
    await state.clear()

    if book:
        await update_channel_post_if_exists(message.bot, session, book, config.CHANNEL_ID)
        await message.answer(
            f"✅ <b>«{book.title}»</b> kitobining zaxirasi {new_qty} dona qilib belgilandi!",
            parse_mode="HTML",
            reply_markup=get_admin_main_keyboard(),
        )


@router.callback_query(F.data.startswith("adm_del_book:"))
async def delete_book_action(callback: CallbackQuery, session: AsyncSession):
    book_id = int(callback.data.split(":")[1])
    book = await get_book_by_id(session, book_id)

    if not book:
        await callback.answer("Kitob topilmadi.", show_alert=True)
        return

    title = book.title
    # Kanaldan postni o'chirish
    await delete_channel_post_if_exists(callback.bot, session, book_id, config.CHANNEL_ID)
    # Bazadan o'chirish
    await delete_book(session, book_id)

    await callback.message.edit_text(
        f"🗑 <b>«{title}»</b> kitobi muvaffaqiyatli o'chirildi (kanaldagi post ham o'chirildi).",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_sync_channel:"))
async def sync_channel_post(callback: CallbackQuery, session: AsyncSession):
    book_id = int(callback.data.split(":")[1])
    book = await get_book_by_id(session, book_id)

    if not book:
        await callback.answer("Kitob topilmadi.", show_alert=True)
        return

    if book.channel_post:
        await update_channel_post_if_exists(callback.bot, session, book, config.CHANNEL_ID)
        await callback.answer("✅ Kanal posti yangilandi!", show_alert=True)
    else:
        msg_id = await publish_book_to_channel(callback.bot, session, book, config.CHANNEL_ID)
        if msg_id:
            await callback.answer("✅ Kanalga muvaffaqiyatli joylandi!", show_alert=True)
        else:
            await callback.answer("❌ Kanalga joylashda xatolik.", show_alert=True)


# ===================== STATISTIKA =====================

@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message, session: AsyncSession):
    stats = await get_admin_stats(session)

    revenue_str = f"{stats['total_revenue']:,} so'm".replace(",", " ")

    unfound_list = []
    for q, cnt in stats["unfound_searches"]:
        unfound_list.append(f"  • «{q}» — {cnt} marta")
    unfound_block = "\n".join(unfound_list) if unfound_list else "  (Hozircha yo'q)"

    stats_text = (
        f"📊 <b>DO'KON VA BOT STATISTIKASI:</b>\n\n"
        f"📚 <b>Kitoblar:</b>\n"
        f"  • Jami kitoblar: {stats['total_books']} ta\n"
        f"  • Sotuvda mavjud: {stats['available_books']} ta\n"
        f"  • Tugagan (sotilgan): {stats['sold_out_books']} ta\n\n"
        f"📦 <b>Buyurtmalar:</b>\n"
        f"  • Jami buyurtmalar: {stats['total_orders']} ta\n"
        f"  • Yangi (kutilayotgan): {stats['new_orders']} ta\n"
        f"  • Tayyor: {stats['ready_orders']} ta\n"
        f"  • Topshirilgan (yetkazilgan): {stats['delivered_orders']} ta\n"
        f"  • Bekor qilingan: {stats['cancelled_orders']} ta\n\n"
        f"💰 <b>Jami tushum (yetkazilgan):</b> <b>{revenue_str}</b>\n\n"
        f"🔍 <b>Eng ko'p so'ralgan topilmagan kitoblar:</b>\n{unfound_block}"
    )

    await message.answer(stats_text, parse_mode="HTML")


@router.message(F.text == "🔍 Topilmagan so'rovlar")
async def show_unfound_searches(message: Message, session: AsyncSession):
    unfound = await get_unfound_searches(session, limit=15)
    if not unfound:
        await message.answer("Bazada topilmagan so'rovlar mavjud emas.")
        return

    lines = ["🔍 <b>Xaridorlar qidirgan, ammo topilmagan kitoblar ro'yxati:</b>\n"]
    for q, cnt in unfound:
        lines.append(f"  • <b>«{q}»</b> — {cnt} marta qidirilgan")

    lines.append("\n💡 <i>Tavsiya: Ushbu kitoblarni do'konga olib kelish sotuvni oshiradi!</i>")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ===================== KANALGA E'LON YUBORISH =====================

class AdminBroadcastState(StatesGroup):
    waiting_for_content = State()
    waiting_for_confirm = State()


@router.message(F.text == "📢 Kanalga e'lon yuborish")
async def start_channel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AdminBroadcastState.waiting_for_content)

    await message.answer(
        "📢 <b>Kanalga e'lon yuborish bo'limi:</b>\n\n"
        "Do'kon ish vaqti o'zgarishi, vaqtinchalik yopilishi yoki yangiliklar haqida "
        "kanalga yubormoqchi bo'lgan xabaringizni yozing (matn yoki rasm + matn):\n\n"
        "<i>Eslatma: Xabar to'g'ridan-to'g'ri @xazinasi_navoiyy kanaliga siz yozgandek chiqadi.</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AdminBroadcastState.waiting_for_content)
async def process_broadcast_content(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("E'lon bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    confirm_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga yuborish", callback_data="confirm_broadcast")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_broadcast")],
        ]
    )

    if message.photo:
        photo_id = message.photo[-1].file_id
        caption = message.caption or ""
        await state.update_data(content_type="photo", photo_id=photo_id, caption=caption)

        await message.answer(
            "🔎 <b>E'lon ko'rinishi (Preview):</b>\nKanalga quyidagi rasm va matn yuboriladi:",
            parse_mode="HTML",
        )
        await message.answer_photo(
            photo=photo_id,
            caption=caption,
            parse_mode="HTML" if caption else None,
            reply_markup=confirm_kb,
        )
    else:
        text = message.text
        await state.update_data(content_type="text", text=text)

        await message.answer(
            f"🔎 <b>E'lon ko'rinishi (Preview):</b>\n\n{text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Ushbu xabar <b>{config.CHANNEL_ID}</b> kanaliga yuborilsinmi?",
            parse_mode="HTML",
            reply_markup=confirm_kb,
        )

    await state.set_state(AdminBroadcastState.waiting_for_confirm)


@router.callback_query(F.data == "confirm_broadcast", AdminBroadcastState.waiting_for_confirm)
async def execute_broadcast(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    content_type = data.get("content_type")

    try:
        if content_type == "photo":
            photo_id = data["photo_id"]
            caption = data.get("caption", "")
            await callback.bot.send_photo(
                chat_id=config.CHANNEL_ID,
                photo=photo_id,
                caption=caption,
                parse_mode="HTML" if caption else None,
            )
        else:
            text = data["text"]
            await callback.bot.send_message(
                chat_id=config.CHANNEL_ID,
                text=text,
                parse_mode="HTML",
            )

        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"✅ <b>E'lon muvaffaqiyatli kanalga yuborildi!</b> ({config.CHANNEL_ID})",
            parse_mode="HTML",
            reply_markup=get_admin_main_keyboard(),
        )
    except Exception as e:
        await callback.message.answer(
            f"❌ Kanalga yuborishda xatolik yuz berdi:\n<code>{e}</code>\n\n"
            f"Bot kanalda admin ekanligini va post yuborish huquqi borligini tekshiring.",
            parse_mode="HTML",
            reply_markup=get_admin_main_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "E'lon yuborish bekor qilindi.",
        reply_markup=get_admin_main_keyboard(),
    )
    await callback.answer()

