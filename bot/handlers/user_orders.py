from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from db.crud import get_user_orders

router = Router(name="user_orders_router")

STATUS_LABELS = {
    "new": "🟡 Yangi (qabul qilindi)",
    "ready": "⏳ Tayyor (olib ketishingiz mumkin)",
    "delivered": "✅ Topshirildi (Yetkazildi)",
    "cancelled": "❌ Bekor qilingan",
}


@router.message(F.text == "📦 Mening buyurtmalarim")
async def show_user_orders(message: Message, session: AsyncSession, current_user):
    if not current_user:
        await message.answer("Buyurtmalar ro'yxati topilmadi.")
        return

    orders = await get_user_orders(session, current_user.id, limit=10)

    if not orders:
        await message.answer(
            "📦 Sizda hali hech qanday buyurtma mavjud emas.\n"
            "«🔍 Kitob qidirish» yoki «📖 Janrlar» bo'limi orqali kitob tanlab buyurtma berishingiz mumkin!"
        )
        return

    lines = ["📦 <b>Sizning so'nggi buyurtmalaringiz:</b>\n"]
    for ord in orders:
        status_text = STATUS_LABELS.get(ord.status, ord.status)
        date_str = ord.created_at.strftime("%d.%m.%Y %H:%M")
        total_str = f"{ord.total_price:,} so'm".replace(",", " ")

        items_desc = []
        for it in ord.items:
            title = it.book.title if it.book else "Kitob"
            items_desc.append(f"  • {title} ({it.quantity} dona)")

        lines.append(
            f"🔹 <b>Buyurtma #ORD-{ord.id}</b>\n"
            f"📅 Sana: {date_str}\n"
            f"📊 Holati: <b>{status_text}</b>\n"
            f"Kitoblar:\n" + "\n".join(items_desc) + "\n"
            f"💵 Summa: <b>{total_str}</b>\n"
            f"--------------------------------"
        )

    await message.answer(
        text="\n".join(lines),
        parse_mode="HTML",
    )
