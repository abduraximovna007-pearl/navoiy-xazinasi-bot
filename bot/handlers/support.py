import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from bot.config import config
from bot.keyboards.default import get_cancel_keyboard, get_main_menu_keyboard
from bot.keyboards.admin_kb import get_admin_main_keyboard

router = Router(name="support_router")


class CustomerQuestionState(StatesGroup):
    waiting_for_question = State()


class AdminReplyState(StatesGroup):
    waiting_for_reply = State()


# ===================== XARIDOR SAVOL YO'LLASHI =====================

@router.message(F.text == "❓ Savol yo'llash")
async def start_customer_question(message: Message, state: FSMContext):
    # Agar admin bo'lsa
    if config.is_admin(message.from_user.id):
        await message.answer("Siz adminsiz. Mijozlar savollari sizga keladi.")
        return

    await state.set_state(CustomerQuestionState.waiting_for_question)
    await message.answer(
        "❓ <b>Savolingiz yoki murojaatingiz bormi?</b>\n\n"
        "Savolingizni yozib yuboring (matn yoki rasm ko'rinishida).\n"
        "Do'kon ma'muriyati uni o'rganib, sizga bot orqali tezda javob qaytaradi:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(CustomerQuestionState.waiting_for_question)
async def process_customer_question(message: Message, state: FSMContext, current_user):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Murojaat bekor qilindi.", reply_markup=get_main_menu_keyboard(is_admin=False))
        return

    user_tg_id = message.from_user.id
    full_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    phone = current_user.phone if current_user and current_user.phone else "Kiritilmagan"
    now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    profile_link = f"<a href='tg://user?id={user_tg_id}'>Profilni ko'rish ↗️</a>"

    # Adminga boradigan chiroyli va ajralib turadigan xabar
    admin_header = (
        f"📬 ══════════════════════ 📬\n"
        f"💬 <b>YANGI SAVOL / MUROJAAT KELDI!</b>\n"
        f"📬 ══════════════════════ 📬\n\n"
        f"👤 <b>Kimdan:</b> {full_name} ({profile_link})\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_tg_id}</code>\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"⏰ <b>Vaqt:</b> {now_str}\n\n"
    )

    reply_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Xaridorga javob yozish",
                    callback_data=f"reply_cust:{user_tg_id}",
                )
            ]
        ]
    )

    # Barcha adminlarga yuboramiz
    for admin_id in config.ADMIN_IDS:
        try:
            if message.photo:
                photo_id = message.photo[-1].file_id
                caption = message.caption or "Rasm yuborildi"
                await message.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_id,
                    caption=admin_header + f"📝 <b>Savol mazmuni:</b>\n{caption}",
                    parse_mode="HTML",
                    reply_markup=reply_kb,
                )
            else:
                question_text = message.text
                full_admin_msg = (
                    admin_header +
                    f"📝 <b>Savol mazmuni:</b>\n"
                    f"<blockquote>{question_text}</blockquote>\n\n"
                    f"👉 <i>Xaridorga javob yuborish uchun pastdagi tugmani bosing:</i>"
                )
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=full_admin_msg,
                    parse_mode="HTML",
                    reply_markup=reply_kb,
                )
        except Exception:
            pass

    await state.clear()
    await message.answer(
        "✅ <b>Savolingiz do'kon ma'muriyatiga yetkazildi!</b>\n\n"
        "Tez orada sizga shu yerda javob qaytaramiz. E'tiboringiz uchun rahmat!",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(is_admin=False),
    )


# ===================== ADMIN XARIDORGA JAVOB YOZISHI =====================

@router.callback_query(F.data.startswith("reply_cust:"))
async def start_admin_reply(callback: CallbackQuery, state: FSMContext):
    if not config.is_admin(callback.from_user.id):
        await callback.answer("Ruxsat berilmagan.", show_alert=True)
        return

    target_user_id = int(callback.data.split(":")[1])
    await state.set_state(AdminReplyState.waiting_for_reply)
    await state.update_data(target_user_id=target_user_id)

    await callback.message.answer(
        f"✍️ <b>Xaridorga (ID: <code>{target_user_id}</code>) javob yozing:</b>\n\n"
        f"<i>Siz yozgan javob to'g'ridan-to'g'ri xaridorga yetkaziladi.</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminReplyState.waiting_for_reply)
async def process_admin_reply(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Javob yuborish bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return

    data = await state.get_data()
    target_user_id = data["target_user_id"]
    reply_text = message.text

    # Xaridorga yuboriladigan javob
    customer_msg = (
        f"🔔 <b>«{config.SHOP_NAME}» do'koni ma'muriyatidan javob:</b>\n\n"
        f"{reply_text}\n\n"
        f"<i>Agar boshqa savollaringiz bo'lsa, bemalol murojaat qilishingiz mumkin!</i>"
    )

    try:
        await message.bot.send_message(
            chat_id=target_user_id,
            text=customer_msg,
            parse_mode="HTML",
        )
        await state.clear()
        await message.answer(
            f"✅ <b>Javobingiz xaridorga muvaffaqiyatli yetkazildi!</b> (ID: {target_user_id})",
            parse_mode="HTML",
            reply_markup=get_admin_main_keyboard(),
        )
    except Exception as e:
        await message.answer(
            f"❌ Xaridorga xabar yetkazilmadi (u botni bloklagan bo'lishi mumkin):\n<code>{e}</code>",
            parse_mode="HTML",
            reply_markup=get_admin_main_keyboard(),
        )
