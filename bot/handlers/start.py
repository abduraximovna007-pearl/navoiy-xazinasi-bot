from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from bot.config import config
from bot.keyboards.default import get_main_menu_keyboard
from bot.keyboards.inline import get_book_card_keyboard
from db.crud import get_book_by_id
from bot.services.channel import format_channel_post_caption

router = Router(name="start_router")


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    await state.clear()
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []

    is_admin = config.is_admin(message.from_user.id)

    # Deep linking tekshirish: /start book_123
    if args and args[0].startswith("book_"):
        try:
            book_id = int(args[0].replace("book_", ""))
            book = await get_book_by_id(session, book_id)
            if book:
                me = await message.bot.get_me()
                caption = format_channel_post_caption(book, me.username or "kitob_bot")
                kb = get_book_card_keyboard(book, is_admin=is_admin)

                if book.images and len(book.images) > 0:
                    await message.answer_photo(
                        photo=book.images[0].telegram_file_id,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                else:
                    await message.answer(
                        text=caption,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                return
        except Exception:
            pass

    # Agar foydalanuvchi ADMIN bo'lsa, xaridorlik qismi chiqmasin, faqat admin paneli chiqsin!
    if is_admin:
        admin_text = (
            f"Assalomu alaykum, Hurmatli Admin (<b>{message.from_user.first_name}</b>)! 👑\n\n"
            f"<b>«{config.SHOP_NAME}»</b> boshqaruv panelidasiz.\n"
            f"Quyidagi boshqaruv menyusidan kerakli bo'limni tanlang:"
        )
        from bot.keyboards.admin_kb import get_admin_main_keyboard
        await message.answer(
            text=admin_text,
            parse_mode="HTML",
            reply_markup=get_admin_main_keyboard(),
        )
        return

    main_kb = get_main_menu_keyboard(is_admin=False)
    welcome_text = (
        f"Assalomu alaykum, <b>{message.from_user.first_name}</b>! 👋\n\n"
        f"<b>«{config.SHOP_NAME}»</b> rasmiy botiga xush kelibsiz!\n\n"
        f"Bu yerda siz:\n"
        f"🔍 O'zingiz qidirgan kitoblarni tez va oson topishingiz;\n"
        f"📖 Janrlar va yangi kelgan kitoblar bilan tanishishingiz;\n"
        f"🛒 Qulay usulda buyurtma berishingiz mumkin.\n\n"
        f"Kerakli bo'limni tanlang:"
    )

    await message.answer(
        text=welcome_text,
        parse_mode="HTML",
        reply_markup=main_kb,
    )



@router.message(F.text == "📞 Biz haqimizda")
async def show_about(message: Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    about_text = (
        f"📚 <b>«{config.SHOP_NAME}»</b>\n\n"
        f"📍 <b>Manzil:</b> {config.SHOP_ADDRESS}\n"
        f"⏰ <b>Ish vaqti:</b> {config.SHOP_WORKING_HOURS}\n"
        f"📞 <b>Telefon:</b> <code>{config.SHOP_PHONE}</code>\n"
        f"📷 <b>Instagram:</b> <a href='{config.SHOP_INSTAGRAM}'>@navoiy_xazinasi</a>\n\n"
        f"🚚 <i>Yetkazib berish butun O'zbekiston bo'ylab amalga oshiriladi!</i>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📍 Xaritadan lokatsiyani olish", callback_data="send_location_pin"),
            ],
            [
                InlineKeyboardButton(text="📷 Instagram sahifamiz", url=config.SHOP_INSTAGRAM),
                InlineKeyboardButton(text="🌐 Google Maps da ko'rish", url=config.SHOP_MAP_URL),
            ]
        ]
    )

    await message.answer(
        text=about_text,
        parse_mode="HTML",
        reply_markup=kb,
        disable_web_page_preview=True,
    )



@router.callback_query(F.data == "send_location_pin")
async def handle_send_location_pin(callback: CallbackQuery):
    await callback.message.answer_location(
        latitude=config.SHOP_LATITUDE,
        longitude=config.SHOP_LONGITUDE,
    )
    await callback.message.answer(
        f"📍 <b>{config.SHOP_NAME} do'koni lokatsiyasi:</b>\n"
        f"Manzil: {config.SHOP_ADDRESS}\n"
        f"Ish vaqti: {config.SHOP_WORKING_HOURS}",
        parse_mode="HTML",
    )
    await callback.answer()



@router.message(F.text == "◀️ Foydalanuvchi menyusi")
async def back_to_user_menu(message: Message, state: FSMContext):
    await state.clear()
    is_admin = config.is_admin(message.from_user.id)
    await message.answer(
        "Bosh menyuga qaytdingiz.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    is_admin = config.is_admin(callback.from_user.id)
    await callback.message.answer(
        "Bosh sahifadasiz. Bo'limni tanlang:",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    await callback.answer()


@router.message(Command("id"))
async def cmd_id(message: Message):
    """Admin yoki foydalanuvchi o'z ID sini bilishi uchun yordamchi buyruq."""
    await message.answer(
        f"Sizning Telegram ID ingiz: <code>{message.from_user.id}</code>\n"
        f"Chat ID: <code>{message.chat.id}</code>",
        parse_mode="HTML",
    )
