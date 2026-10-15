from typing import List
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from bot.middlewares.admin_only import AdminFilter
from bot.keyboards.admin_kb import (
    get_photo_done_keyboard,
    get_genre_select_keyboard,
    get_skip_inline_keyboard,
    get_book_preview_keyboard,
    get_admin_main_keyboard,
)
from bot.keyboards.default import get_cancel_keyboard
from db.crud import (
    get_all_genres,
    get_genre_by_id,
    get_or_create_genre,
    create_book,
)
from bot.services.channel import publish_book_to_channel, format_channel_post_caption
from bot.config import config

router = Router(name="admin_add_router")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


class AddBookState(StatesGroup):
    waiting_for_photos = State()
    waiting_for_title = State()
    waiting_for_author = State()
    waiting_for_price = State()
    waiting_for_genre = State()
    waiting_for_new_genre_name = State()
    waiting_for_quantity = State()
    waiting_for_description = State()
    waiting_for_preview_choice = State()


@router.message(Command("add"))
@router.message(F.text.in_(["➕ Yangi kitob qo'shish", "✏️ O'quv quroli / Mahsulot qo'shish"]))
async def start_add_book(message: Message, state: FSMContext):
    await state.clear()
    is_stationery = "o'quv" in message.text.lower() or "mahsulot" in message.text.lower()
    item_type = "stationery" if is_stationery else "book"
    await state.set_state(AddBookState.waiting_for_photos)
    await state.update_data(photos=[], item_type=item_type)

    label = "O'quv quroli / Mahsulot (bloknot, daftar, qalam...)" if is_stationery else "Kitob"
    await message.answer(
        f"📸 <b>1-qadam: {label} rasmini yuboring</b>\n\n"
        f"Mahsulot muqovasi yoki rasmini (bitta yoki bir nechta) yuboring.\n"
        f"Rasmlarni yuborib bo'lgach, «✅ Rasmlar yetarli» tugmasini bosing:",
        parse_mode="HTML",
        reply_markup=get_photo_done_keyboard(),
    )



@router.message(AddBookState.waiting_for_photos, F.photo)
async def process_book_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos: List[str] = data.get("photos", [])

    # Eng sifatli rasm o'lchamining file_id sini olamiz
    file_id = message.photo[-1].file_id
    photos.append(file_id)
    await state.update_data(photos=photos)

    await message.answer(
        f"✅ Rasm qabul qilindi (Jami rasmlar: {len(photos)} ta).\n"
        f"Yana rasm yuborishingiz yoki keyingi bosqichga o'tishingiz mumkin:",
        reply_markup=get_photo_done_keyboard(),
    )


@router.callback_query(F.data == "photos_done", AddBookState.waiting_for_photos)
async def photos_done_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])

    if not photos:
        await callback.answer("Iltimos, kamida bitta rasm yuboring!", show_alert=True)
        return

    data = await state.get_data()
    is_stationery = data.get("item_type") == "stationery"
    item_label = "Mahsulot nomini" if is_stationery else "Kitob nomini"
    example = "«Deli charm bloknot A5», «12 talik qalamlar», «A4 daftar»" if is_stationery else "«O'tkan kunlar», «Atom odatlar»"

    await state.set_state(AddBookState.waiting_for_title)
    await callback.message.answer(
        f"🏷 <b>2-qadam: {item_label} kiriting:</b>\n"
        f"<i>(Masalan: {example})</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AddBookState.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if title == "❌ Bekor qilish":
        await cancel_book_addition(message, state)
        return

    data = await state.get_data()
    is_stationery = data.get("item_type") == "stationery"
    author_prompt = (
        "🏷 <b>3-qadam: Brend yoki ishlab chiqaruvchini kiriting:</b>\n"
        "<i>(Masalan: Deli, ErichKrause, yoki «Navoiy Xazinasi»)</i>"
        if is_stationery
        else
        "✍️ <b>3-qadam: Kitob muallifini kiriting:</b>\n"
        "<i>(Masalan: Abdulla Qodiriy, Jeyms Klir)</i>"
    )

    await state.update_data(title=title)
    await state.set_state(AddBookState.waiting_for_author)

    await message.answer(
        author_prompt,
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddBookState.waiting_for_author)
async def process_author(message: Message, state: FSMContext):
    author = message.text.strip()
    if author == "❌ Bekor qilish":
        await cancel_book_addition(message, state)
        return

    data = await state.get_data()
    is_stationery = data.get("item_type") == "stationery"
    price_prompt = (
        "💰 <b>4-qadam: Mahsulot narxini kiriting (so'mda):</b>\n"
        "<i>Faqat raqam yozing (masalan: 35000 yoki 80000)</i>"
        if is_stationery
        else
        "💰 <b>4-qadam: Kitob narxini kiriting (so'mda):</b>\n"
        "<i>Faqat raqam yozing (masalan: 65000 yoki 120000)</i>"
    )

    await state.update_data(author=author)
    await state.set_state(AddBookState.waiting_for_price)

    await message.answer(
        price_prompt,
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddBookState.waiting_for_price)
async def process_price(message: Message, session: AsyncSession, state: FSMContext):
    text = message.text.replace(" ", "").replace(",", "").strip()
    if text == "❌Bekorqilish":
        await cancel_book_addition(message, state)
        return

    if not text.isdigit() or int(text) <= 0:
        await message.answer("Iltimos, faqat musbat raqam kiriting (masalan: 55000):")
        return

    price = int(text)
    await state.update_data(price=price)
    await state.set_state(AddBookState.waiting_for_genre)

    data = await state.get_data()
    is_stationery = data.get("item_type") == "stationery"
    genre_prompt = (
        "📂 <b>5-qadam: Mahsulot bo'limini / kategoriyasini tanlang:</b>\n"
        "<i>(Masalan: O'quv qurollari, Bloknot va daftarlar, Kantselyariya...)</i>"
        if is_stationery
        else
        "📂 <b>5-qadam: Kitob janrini tanlang:</b>"
    )

    genres = await get_all_genres(session)
    await message.answer(
        genre_prompt,
        parse_mode="HTML",
        reply_markup=get_genre_select_keyboard(genres),
    )



@router.callback_query(F.data.startswith("sel_genre:"), AddBookState.waiting_for_genre)
async def process_genre_choice(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split(":")[1]

    if choice == "new":
        await state.set_state(AddBookState.waiting_for_new_genre_name)
        await callback.message.edit_text(
            "Yangi janr nomini yozib yuboring:\n<i>(Masalan: Fantastika)</i>",
            parse_mode="HTML",
        )
    else:
        genre_id = int(choice)
        await state.update_data(genre_id=genre_id)
        await ask_quantity_step(callback.message, state)

    await callback.answer()


@router.message(AddBookState.waiting_for_new_genre_name)
async def process_new_genre(message: Message, session: AsyncSession, state: FSMContext):
    name = message.text.strip()
    if name == "❌ Bekor qilish":
        await cancel_book_addition(message, state)
        return

    genre = await get_or_create_genre(session, name)
    await state.update_data(genre_id=genre.id)
    await ask_quantity_step(message, state)


async def ask_quantity_step(message: Message, state: FSMContext):
    await state.set_state(AddBookState.waiting_for_quantity)
    await message.answer(
        "🔢 <b>6-qadam: Nechta nusxa (zaxira soni) bor?</b>\n"
        "<i>(Masalan: 5 yoki 10)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddBookState.waiting_for_quantity)
async def process_quantity(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "❌ Bekor qilish":
        await cancel_book_addition(message, state)
        return

    if not text.isdigit() or int(text) < 0:
        await message.answer("Iltimos, musbat butun son kiriting (masalan: 1, 5, 10):")
        return

    quantity = int(text)
    await state.update_data(quantity=quantity)
    await state.set_state(AddBookState.waiting_for_description)

    await message.answer(
        "📖 <b>7-qadam: Kitob haqida qisqacha tavsif yozing:</b>\n"
        "<i>(Ixtiyoriy, agar kerak bo'lmasa «⏭ O'tkazib yuborish» tugmasini bosing)</i>",
        parse_mode="HTML",
        reply_markup=get_skip_inline_keyboard(),
    )


@router.callback_query(F.data == "skip_desc", AddBookState.waiting_for_description)
async def skip_description_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.update_data(description=None)
    await show_book_preview(callback.message, session, state)
    await callback.answer()


@router.message(AddBookState.waiting_for_description)
async def process_description(message: Message, session: AsyncSession, state: FSMContext):
    desc = message.text.strip()
    if desc == "❌ Bekor qilish":
        await cancel_book_addition(message, state)
        return

    await state.update_data(description=desc)
    await show_book_preview(message, session, state)


async def show_book_preview(message: Message, session: AsyncSession, state: FSMContext):
    await state.set_state(AddBookState.waiting_for_preview_choice)
    data = await state.get_data()

    genre_id = data.get("genre_id")
    genre = await get_genre_by_id(session, genre_id) if genre_id else None
    genre_name = genre.name if genre else "Noma'lum"

    price = data.get("price", 0)
    price_formatted = f"{price:,}".replace(",", " ")

    is_stationery = data.get("item_type") == "stationery"
    icon = "📓" if "bloknot" in data.get('title', '').lower() or "daftar" in data.get('title', '').lower() else ("✏️" if is_stationery else "📚")
    author_label = "🏷 <b>Brend:</b>" if is_stationery else "✍️ <b>Muallif:</b>"
    genre_label = "📂 <b>Bo'lim:</b>" if is_stationery else "📂 <b>Janr:</b>"

    preview_text = (
        f"📢 <b>KANAL VA BOTDA QUYIDAGICHA KO'RINADI:</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{icon} <b>{data.get('title')}</b>\n"
        f"{author_label} {data.get('author')}\n"
        f"{genre_label} #{genre_name.replace(' ', '_')}\n"
        f"💰 <b>Narxi:</b> {price_formatted} so'm\n"
        f"✅ <b>Holati:</b> Mavjud ({data.get('quantity')} ta)\n"
    )


    if data.get("description"):
        preview_text += f"\n📖 <b>Tavsif:</b>\n<i>{data.get('description')}</i>\n"

    preview_text += "━━━━━━━━━━━━━━━━━━\nTanlang:"

    photos = data.get("photos", [])
    if photos:
        await message.answer_photo(
            photo=photos[0],
            caption=preview_text,
            parse_mode="HTML",
            reply_markup=get_book_preview_keyboard(),
        )
    else:
        await message.answer(
            text=preview_text,
            parse_mode="HTML",
            reply_markup=get_book_preview_keyboard(),
        )


@router.callback_query(F.data.startswith("book_publish:"), AddBookState.waiting_for_preview_choice)
async def publish_or_save_book(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    action = callback.data.split(":")[1]
    data = await state.get_data()

    # Bazaga kitobni saqlaymiz
    book = await create_book(
        session=session,
        title=data["title"],
        author=data["author"],
        price=data["price"],
        genre_id=data.get("genre_id"),
        description=data.get("description"),
        quantity=data.get("quantity", 1),
        images=data.get("photos", []),
    )

    channel_post_msg = ""
    if action == "channel":
        msg_id = await publish_book_to_channel(
            bot=callback.bot,
            session=session,
            book=book,
            channel_id=config.CHANNEL_ID,
        )
        if msg_id:
            channel_post_msg = f"\n📢 <b>Kanalga ham muvaffaqiyatli joylandi!</b> (Post ID: {msg_id})"
        else:
            channel_post_msg = "\n⚠️ <i>Kanalga joylash amalga oshmadi (CHANNEL_ID yoki bot huquqini tekshiring).</i>"

    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"🎉 <b>«{book.title}»</b> kitobi muvaffaqiyatli saqlandi!{channel_post_msg}",
        parse_mode="HTML",
        reply_markup=get_admin_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "add_book_cancel")
async def cancel_book_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Kitob qo'shish bekor qilindi.",
        reply_markup=get_admin_main_keyboard(),
    )
    await callback.answer()


async def cancel_book_addition(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Kitob qo'shish bekor qilindi.",
        reply_markup=get_admin_main_keyboard(),
    )
