from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from db.crud import get_book_by_id, create_order, update_user_phone
from bot.keyboards.inline import (
    get_order_quantity_keyboard,
    get_delivery_type_keyboard,
    get_order_confirm_keyboard,
)
from bot.keyboards.default import (
    get_phone_request_keyboard,
    get_cancel_keyboard,
    get_main_menu_keyboard,
)
from bot.services.notify import notify_admins_new_order
from bot.config import config

router = Router(name="order_router")


class OrderState(StatesGroup):
    waiting_for_quantity = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_delivery_type = State()
    waiting_for_address = State()
    waiting_for_notes = State()
    waiting_for_confirm = State()


@router.callback_query(F.data.startswith("order_book:"))
async def start_book_order(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    book_id = int(callback.data.split(":")[1])
    book = await get_book_by_id(session, book_id)

    if config.is_admin(callback.from_user.id):
        await callback.answer("Siz adminsiz! Admin hisobidan buyurtma berilmaydi.", show_alert=True)
        return

    if not book or book.quantity <= 0:
        await callback.answer("Kechirasiz, ushbu kitob hozirda tugagan.", show_alert=True)
        return


    await state.update_data(book_id=book_id, book_title=book.title, book_price=book.price)
    await state.set_state(OrderState.waiting_for_quantity)

    await callback.message.answer(
        f"📚 <b>{book.title}</b> kitobidan necha nusxa buyurtma qilmoqchisiz?\n"
        f"<i>(Mavjud: {book.quantity} dona)</i>\n\n"
        f"Tugmalardan tanlang yoki sonini yozib yuboring:",
        parse_mode="HTML",
        reply_markup=get_order_quantity_keyboard(book.quantity),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ord_qty:"), OrderState.waiting_for_quantity)
async def process_quantity_callback(callback: CallbackQuery, state: FSMContext):
    qty = int(callback.data.split(":")[1])
    await state.update_data(quantity=qty)
    await ask_name_step(callback.message, state, callback.from_user.full_name)
    await callback.answer()


@router.message(OrderState.waiting_for_quantity)
async def process_quantity_message(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Iltimos, musbat butun son kiriting (masalan: 1 yoki 2):")
        return

    qty = int(message.text)
    data = await state.get_data()
    # Zaxiradan ko'p kiritilgan bo'lsa
    await state.update_data(quantity=qty)
    await ask_name_step(message, state, message.from_user.full_name)


async def ask_name_step(message: Message, state: FSMContext, default_name: str):
    await state.set_state(OrderState.waiting_for_name)
    await message.answer(
        f"Buyurtmachi ismini tasdiqlang yoki o'zgartiring:\n"
        f"<i>(Hozirgi ismingiz: {default_name})</i>\n\n"
        f"Ismingizni yozib yuboring yoki o'zgartirishsiz qoldirish uchun «<b>{default_name}</b>» deb yozing:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(OrderState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if name == "❌ Bekor qilish":
        await cancel_order(message, state)
        return

    await state.update_data(customer_name=name)
    await state.set_state(OrderState.waiting_for_phone)

    await message.answer(
        "Iltimos, siz bilan bog'lanish uchun telefon raqamingizni yuboring:\n"
        "<i>Pastdagi tugmani bosing yoki raqamni yozing (+998901234567)</i>",
        parse_mode="HTML",
        reply_markup=get_phone_request_keyboard(),
    )


@router.message(OrderState.waiting_for_phone, F.contact)
async def process_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await handle_phone_received(message, state, phone)


@router.message(OrderState.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    if phone == "❌ Bekor qilish":
        await cancel_order(message, state)
        return

    # Raqamni oddiy formatlash
    if not any(char.isdigit() for char in phone) or len(phone) < 7:
        await message.answer("Iltimos, to'g'ri telefon raqam kiriting (masalan: +998901234567):")
        return

    await handle_phone_received(message, state, phone)


async def handle_phone_received(message: Message, state: FSMContext, phone: str):
    await state.update_data(customer_phone=phone)
    await state.set_state(OrderState.waiting_for_delivery_type)

    await message.answer(
        "Kitobni qanday qabul qilasiz?",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        "Yetkazib berish usulini tanlang:",
        reply_markup=get_delivery_type_keyboard(),
    )


@router.callback_query(F.data.startswith("deliv:"), OrderState.waiting_for_delivery_type)
async def process_delivery_type(callback: CallbackQuery, state: FSMContext):
    deliv_type = callback.data.split(":")[1]
    await state.update_data(delivery_type=deliv_type)

    if deliv_type == "pickup":
        await state.update_data(address=f"Do'kondan olib ketiladi: {config.SHOP_ADDRESS}")
        await show_order_summary(callback.message, state)
    else:
        await state.set_state(OrderState.waiting_for_address)
        await callback.message.edit_text(
            "📍 Yetkazib berish manzilini to'liq yozib yuboring:\n"
            "<i>(Shahar/tuman, ko'cha, uy raqami, mo'ljal)</i>",
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(OrderState.waiting_for_address)
async def process_address(message: Message, state: FSMContext):
    address = message.text.strip()
    if address == "❌ Bekor qilish":
        await cancel_order(message, state)
        return

    await state.update_data(address=address)
    await show_order_summary(message, state)


async def show_order_summary(message: Message, state: FSMContext):
    await state.set_state(OrderState.waiting_for_confirm)
    data = await state.get_data()

    book_title = data.get("book_title", "")
    quantity = data.get("quantity", 1)
    price = data.get("book_price", 0)
    total_price = quantity * price

    deliv_label = "🏪 Do'kondan olib ketish" if data.get("delivery_type") == "pickup" else "🚚 Yetkazib berish"
    address = data.get("address", "-")

    summary_text = (
        f"📋 <b>BUYURTMA MA'LUMOTLARI:</b>\n\n"
        f"📚 <b>Kitob:</b> {book_title}\n"
        f"🔢 <b>Soni:</b> {quantity} dona\n"
        f"💰 <b>Narxi:</b> {price:,} so'm\n"
        f"💵 <b>Jami summa:</b> <b>{total_price:,} so'm</b>\n\n"
        f"👤 <b>Xaridor:</b> {data.get('customer_name')}\n"
        f"📞 <b>Telefon:</b> {data.get('customer_phone')}\n"
        f"🚚 <b>Olish usuli:</b> {deliv_label}\n"
        f"📍 <b>Manzil:</b> {address}\n\n"
        f"Barcha ma'lumotlar to'g'rimi?"
    ).replace(",", " ")

    await message.answer(
        text=summary_text,
        parse_mode="HTML",
        reply_markup=get_order_confirm_keyboard(),
    )


@router.callback_query(F.data == "ord_confirm", OrderState.waiting_for_confirm)
async def confirm_order(callback: CallbackQuery, session: AsyncSession, state: FSMContext, current_user):
    data = await state.get_data()
    book_id = data["book_id"]
    quantity = data["quantity"]
    price = data["book_price"]
    customer_name = data["customer_name"]
    customer_phone = data["customer_phone"]
    delivery_type = data["delivery_type"]
    address = data.get("address")

    # Foydalanuvchi profiliga telefonini ham saqlab qo'yamiz
    await update_user_phone(session, current_user.id, customer_phone)

    customer_username = callback.from_user.username

    order = await create_order(
        session=session,
        user_id=current_user.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_username=customer_username,
        delivery_type=delivery_type,
        address=address,
        notes=None,
        items=[{"book_id": book_id, "quantity": quantity, "price": price}],
    )


    await state.clear()

    # Xaridorga muvaffaqiyatli xabari
    success_msg = (
        f"🎉 <b>Buyurtmangiz qabul qilindi!</b>\n\n"
        f"Buyurtma raqami: <b>#ORD-{order.id}</b>\n"
        f"Jami to'lov: <b>{order.total_price:,} so'm</b>\n\n"
        f"Tez orada menejerimiz siz bilan bog'lanadi. "
        f"Buyurtmangiz holatini «📦 Mening buyurtmalarim» bo'limida kuzatishingiz mumkin."
    ).replace(",", " ")

    is_admin = config.is_admin(callback.from_user.id)
    await callback.message.edit_text(
        text=success_msg,
        parse_mode="HTML",
    )
    await callback.message.answer(
        "Bosh sahifaga qaytdingiz:",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
    await callback.answer()

    # Barcha adminlarga bildirishnoma yuborish
    await notify_admins_new_order(callback.bot, order, config.ADMIN_IDS)


@router.callback_query(F.data == "ord_cancel")
async def cancel_order_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = config.is_admin(callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer(
        "Buyurtma bekor qilindi.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
    await callback.answer()


async def cancel_order(message: Message, state: FSMContext):
    await state.clear()
    is_admin = config.is_admin(message.from_user.id)
    await message.answer(
        "Buyurtma berish bekor qilindi.",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
    )
