import logging
from typing import List
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.models import Order, Book, User

logger = logging.getLogger(__name__)


def get_admin_order_keyboard(order_id: int, current_status: str) -> InlineKeyboardMarkup:
    """Admin uchun buyurtmani boshqarish tugmalari."""
    buttons = []
    
    if current_status == "new":
        buttons.append([
            InlineKeyboardButton(text="⏳ Tayyorlashga olish", callback_data=f"adm_ord:ready:{order_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"adm_ord:cancel:{order_id}")
        ])
    elif current_status == "ready":
        buttons.append([
            InlineKeyboardButton(text="✅ Topshirildi / Yetkazildi", callback_data=f"adm_ord:delivered:{order_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"adm_ord:cancel:{order_id}")
        ])
    elif current_status in ["delivered", "cancelled"]:
        buttons.append([
            InlineKeyboardButton(text="🔄 Yangi holatga qaytarish", callback_data=f"adm_ord:new:{order_id}")
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def notify_admins_new_order(bot: Bot, order: Order, admin_ids: List[int]):
    """Yangi buyurtma haqida barcha adminlarga bildirishnoma yuboradi."""
    items_text = []
    for item in order.items:
        book_title = item.book.title if item.book else "Noma'lum kitob"
        subtotal = item.quantity * item.price_at_order
        items_text.append(
            f"  • <b>{book_title}</b> x {item.quantity} ta = {subtotal:,} so'm".replace(",", " ")
        )
    
    items_block = "\n".join(items_text)
    delivery_label = "🏪 Do'kondan olib ketish" if order.delivery_type == "pickup" else "🚚 Yetkazib berish"
    address_line = f"📍 <b>Manzil:</b> {order.address}\n" if order.address else ""
    notes_line = f"📝 <b>Izoh:</b> {order.notes}\n" if order.notes else ""
    total_formatted = f"{order.total_price:,}".replace(",", " ")

    user_tg_id = order.user.telegram_id if order.user else None
    username_str = f"@{order.customer_username}" if order.customer_username else "Mavjud emas"
    profile_link = f"<a href='tg://user?id={user_tg_id}'>Profilni ko'rish ↗️</a>" if user_tg_id else ""

    msg_text = (
        f"🚨 <b>YANGI BUYURTMA! #ORD-{order.id}</b>\n\n"
        f"👤 <b>Xaridor:</b> {order.customer_name} ({profile_link})\n"
        f"🔗 <b>Username:</b> {username_str}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_tg_id}</code>\n"
        f"📞 <b>Telefon:</b> <code>{order.customer_phone}</code>\n"
        f"🚚 <b>Olish usuli:</b> {delivery_label}\n"
        f"{address_line}"
        f"{notes_line}"
        f"\n📦 <b>Buyurtma tarkibi:</b>\n{items_block}\n\n"
        f"💵 <b>Jami summa:</b> <b>{total_formatted} so'm</b>\n"
        f"📊 <b>Holat:</b> 🟡 Yangi"
    )


    keyboard = get_admin_order_keyboard(order.id, order.status)

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=msg_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.error(f"Admin {admin_id} ga bildirishnoma yuborilmadi: {e}")


async def notify_customer_order_status(bot: Bot, order: Order):
    """Buyurtma holati o'zgarganda xaridorga xabar beradi."""
    if not order.user or not order.user.telegram_id:
        return

    status_messages = {
        "ready": (
            f"✅ <b>Buyurtmangiz tayyorlandi!</b>\n\n"
            f"Buyurtma raqami: <b>#ORD-{order.id}</b>\n"
            f"Siz buyurtmangizni do'kondan olib ketishingiz yoki kuryer yetkazishini kutishingiz mumkin."
        ),
        "delivered": (
            f"🎉 <b>Buyurtmangiz topshirildi!</b>\n\n"
            f"Buyurtma raqami: <b>#ORD-{order.id}</b>\n"
            f"Xaridingiz uchun rahmat! Kitob mutolaasi maroqli bo'lsin 📖"
        ),
        "cancelled": (
            f"❌ <b>Buyurtmangiz bekor qilindi.</b>\n\n"
            f"Buyurtma raqami: <b>#ORD-{order.id}</b>\n"
            f"Savollaringiz bo'lsa, do'konimiz bilan bog'lanishingiz mumkin."
        ),
        "new": (
            f"ℹ️ <b>Buyurtmangiz holati yangilandi:</b> Qayta ko'rib chiqilmoqda.\n"
            f"Buyurtma raqami: <b>#ORD-{order.id}</b>"
        ),
    }

    text = status_messages.get(order.status)
    if text:
        try:
            await bot.send_message(
                chat_id=order.user.telegram_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Xaridor {order.user.telegram_id} ga status xabari yuborilmadi: {e}")


async def notify_subscribers_book_available(bot: Bot, book: Book, users: List[User]):
    """Kitob zaxirasi to'ldirilganda obuna bo'lgan foydalanuvchilarga xabar yuboradi."""
    me = await bot.get_me()
    bot_username = me.username or "kitob_bot"

    text = (
        f"🔔 <b>Xushxabar! Siz kutgan kitob sotuvda mavjud:</b>\n\n"
        f"📚 <b>{book.title}</b>\n"
        f"✍️ <b>Muallif:</b> {book.author}\n"
        f"💰 <b>Narxi:</b> {book.price:,} so'm\n"
        f"📦 <b>Zaxirada:</b> {book.quantity} ta qoldi!\n\n"
        f"Hoziroq buyurtma berishingiz mumkin:"
    ).replace(",", " ")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Buyurtma berish", url=f"https://t.me/{bot_username}?start=book_{book.id}")]
        ]
    )

    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.warning(f"Obunachi {user.telegram_id} ga bildirishnoma yuborilmadi: {e}")
