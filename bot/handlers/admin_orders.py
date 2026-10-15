from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from bot.middlewares.admin_only import AdminFilter
from bot.keyboards.admin_kb import get_orders_filter_keyboard
from db.crud import (
    get_orders_by_status,
    get_order_by_id,
    update_order_status,
    update_book_stock,
)
from bot.services.notify import (
    notify_customer_order_status,
    get_admin_order_keyboard,
)
from bot.services.channel import update_channel_post_if_exists
from bot.config import config

router = Router(name="admin_orders_router")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(F.text == "📋 Buyurtmalar")
async def show_orders_menu(message: Message, session: AsyncSession):
    await render_orders_list(message, session, status="new", page=0)


@router.callback_query(F.data.startswith("adm_ord_flt:"))
async def handle_orders_filter(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    status = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0

    await render_orders_list(callback.message, session, status=status, page=page, is_edit=True)
    await callback.answer()


async def render_orders_list(
    message: Message,
    session: AsyncSession,
    status: str = "new",
    page: int = 0,
    is_edit: bool = False,
):
    limit = 5
    offset = page * limit
    orders, total_count = await get_orders_by_status(session, status=status, limit=limit, offset=offset)

    filter_kb = get_orders_filter_keyboard(current_filter=status)
    buttons = list(filter_kb.inline_keyboard)

    if not orders:
        text = f"📋 <b>Buyurtmalar ({status}):</b>\n\nBu bo'limda hozircha buyurtmalar yo'q."
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        if is_edit:
            await message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await message.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    text_blocks = [f"📋 <b>Buyurtmalar ({status}, jami: {total_count} ta):</b>\n"]

    for ord in orders:
        items_summary = ", ".join(
            f"{it.book.title if it.book else 'Kitob'} x {it.quantity}" for it in ord.items
        )
        total_str = f"{ord.total_price:,} so'm".replace(",", " ")
        text_blocks.append(
            f"🔹 <b>#ORD-{ord.id}</b> | {ord.customer_name} ({ord.customer_phone})\n"
            f"📦 Tarkib: {items_summary}\n"
            f"💵 Summa: <b>{total_str}</b> | Holat: <b>{ord.status}</b>\n"
        )
        # Har bir buyurtma uchun boshqarish tugmasi
        buttons.append([
            InlineKeyboardButton(
                text=f"🔍 #ORD-{ord.id} ni boshqarish",
                callback_data=f"adm_view_order:{ord.id}",
            )
        ])

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"adm_ord_flt:{status}:{page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"adm_ord_flt:{status}:{page+1}"))
    if nav:
        buttons.append(nav)

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if is_edit:
        await message.edit_text("\n".join(text_blocks), parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer("\n".join(text_blocks), parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("adm_view_order:"))
async def view_order_detail(callback: CallbackQuery, session: AsyncSession):
    order_id = int(callback.data.split(":")[1])
    order = await get_order_by_id(session, order_id)

    if not order:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return

    items_text = []
    for item in order.items:
        title = item.book.title if item.book else "Noma'lum"
        sub = item.quantity * item.price_at_order
        items_text.append(f"  • {title} x {item.quantity} dona = {sub:,} so'm".replace(",", " "))

    deliv_label = "🏪 Do'kondan olib ketish" if order.delivery_type == "pickup" else "🚚 Yetkazib berish"
    address_line = f"📍 Manzil: {order.address}\n" if order.address else ""
    date_str = order.created_at.strftime("%d.%m.%Y %H:%M")

    user_tg_id = order.user.telegram_id if order.user else None
    username_str = f"@{order.customer_username}" if order.customer_username else "Mavjud emas"
    profile_link = f"<a href='tg://user?id={user_tg_id}'>Profilni ochish ↗️</a>" if user_tg_id else ""

    detail_text = (
        f"📋 <b>BUYURTMA #ORD-{order.id}</b>\n"
        f"📅 Sana: {date_str}\n"
        f"📊 Holat: <b>{order.status.upper()}</b>\n\n"
        f"👤 Xaridor: <b>{order.customer_name}</b> ({profile_link})\n"
        f"🔗 Username: <b>{username_str}</b>\n"
        f"🆔 Telegram ID: <code>{user_tg_id}</code>\n"
        f"📞 Telefon: <code>{order.customer_phone}</code>\n"
        f"🚚 Olish usuli: {deliv_label}\n"
        f"{address_line}\n"
        f"📦 <b>Kitoblar:</b>\n" + "\n".join(items_text) + "\n\n"
        f"💵 <b>Jami summa:</b> <b>{order.total_price:,} so'm</b>"
    ).replace(",", " ")


    kb = get_admin_order_keyboard(order.id, order.status)
    await callback.message.edit_text(detail_text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_ord:"))
async def process_order_action(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    action = parts[1]  # ready | delivered | cancel | new
    order_id = int(parts[2])

    order = await get_order_by_id(session, order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return

    prev_status = order.status

    if action == "ready":
        # README 5.5: faqat admin tasdiqlagandan keyin zaxira kamayadi!
        if prev_status == "new":
            for it in order.items:
                book = await update_book_stock(session, it.book_id, -it.quantity)
                if book:
                    await update_channel_post_if_exists(callback.bot, session, book, config.CHANNEL_ID)

        await update_order_status(session, order.id, "ready")
        order.status = "ready"
        await notify_customer_order_status(callback.bot, order)
        await callback.answer("✅ Buyurtma tayyorlandi va zaxiradan kamaytirildi!", show_alert=True)

    elif action == "delivered":
        if prev_status == "new":
            # Agar birdan delivered qilinsa ham zaxira kamaytiriladi
            for it in order.items:
                book = await update_book_stock(session, it.book_id, -it.quantity)
                if book:
                    await update_channel_post_if_exists(callback.bot, session, book, config.CHANNEL_ID)

        await update_order_status(session, order.id, "delivered")
        order.status = "delivered"
        await notify_customer_order_status(callback.bot, order)
        await callback.answer("🎉 Buyurtma topshirildi deb belgilandi!", show_alert=True)

    elif action == "cancel":
        # Agar oldin tasdiqlanib zaxiradan ayirilgan bo'lsa, qaytarib qo'yamiz
        if prev_status in ["ready", "delivered"]:
            for it in order.items:
                book = await update_book_stock(session, it.book_id, it.quantity)
                if book:
                    await update_channel_post_if_exists(callback.bot, session, book, config.CHANNEL_ID)

        await update_order_status(session, order.id, "cancelled")
        order.status = "cancelled"
        await notify_customer_order_status(callback.bot, order)
        await callback.answer("❌ Buyurtma bekor qilindi.", show_alert=True)

    elif action == "new":
        await update_order_status(session, order.id, "new")
        order.status = "new"
        await callback.answer("🔄 Buyurtma yangi holatga qaytarildi.")

    # Xabarni yangilash
    updated_order = await get_order_by_id(session, order_id)
    if updated_order:
        new_kb = get_admin_order_keyboard(order_id, updated_order.status)
        await callback.message.edit_reply_markup(reply_markup=new_kb)
