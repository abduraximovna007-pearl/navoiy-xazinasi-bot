from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from db.models import Book, Genre


def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Admin boshqaruv paneli menyusi (faqat admin funksiyalari)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Yangi kitob qo'shish"),
                KeyboardButton(text="✏️ O'quv quroli / Mahsulot qo'shish"),
            ],
            [
                KeyboardButton(text="📚 Barcha mahsulotlar"),
                KeyboardButton(text="📋 Buyurtmalar"),
            ],
            [KeyboardButton(text="📢 Kanalga e'lon yuborish")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🔍 Topilmagan so'rovlar")],
        ],
        resize_keyboard=True,
    )





def get_genre_select_keyboard(genres: List[Genre]) -> InlineKeyboardMarkup:
    """Kitob qo'shishda janr tanlash tugmalari."""
    buttons = []
    row = []
    for g in genres:
        row.append(InlineKeyboardButton(text=g.name, callback_data=f"sel_genre:{g.id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="➕ Yangi janr kiritish", callback_data="sel_genre:new")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="add_book_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_skip_inline_keyboard() -> InlineKeyboardMarkup:
    """Tavsifni o'tkazib yuborish tugmasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data="skip_desc")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="add_book_cancel")],
        ]
    )


def get_photo_done_keyboard() -> InlineKeyboardMarkup:
    """Rasm yuklash tugagach bosiladigan tugma."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Rasmlar yetarli (Davom etish)", callback_data="photos_done")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="add_book_cancel")],
        ]
    )


def get_book_preview_keyboard() -> InlineKeyboardMarkup:
    """Kitob kanalga chiqishidan oldin ko'rish va tasdiqlash tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga joylash", callback_data="book_publish:channel")],
            [InlineKeyboardButton(text="💾 Faqat bazaga saqlash", callback_data="book_publish:db_only")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="add_book_cancel")],
        ]
    )


def get_admin_books_keyboard(books: List[Book], page: int, total_count: int, limit: int = 6) -> InlineKeyboardMarkup:
    """Admin uchun kitoblarni ko'rish va tahrirlash ro'yxati."""
    buttons = []
    for b in books:
        status = f"({b.quantity} dona)" if b.quantity > 0 else "(Sotildi ❌)"
        buttons.append([
            InlineKeyboardButton(
                text=f"{b.title} {status}", callback_data=f"adm_book:{b.id}"
            )
        ])

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm_bpage:{page-1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm_bpage:{page+1}"))
    if nav:
        buttons.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_book_actions_keyboard(book: Book) -> InlineKeyboardMarkup:
    """Bitta kitobni boshqarish (zaxira +1/-1, narx, o'chirish, kanal)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➖ 1 dona", callback_data=f"adm_stock:{book.id}:-1"),
                InlineKeyboardButton(text=f"📦 {book.quantity} dona", callback_data="noop"),
                InlineKeyboardButton(text="➕ 1 dona", callback_data=f"adm_stock:{book.id}:1"),
            ],
            [
                InlineKeyboardButton(text="💰 Narxni o'zgartirish", callback_data=f"adm_edit_price:{book.id}"),
                InlineKeyboardButton(text="🔢 Yangi son kiritish", callback_data=f"adm_edit_qty:{book.id}"),
            ],
            [
                InlineKeyboardButton(text="📢 Kanal postini yangilash", callback_data=f"adm_sync_channel:{book.id}"),
                InlineKeyboardButton(text="🗑 Kitobni o'chirish", callback_data=f"adm_del_book:{book.id}"),
            ],
            [InlineKeyboardButton(text="◀️ Kitoblar ro'yxati", callback_data="adm_bpage:0")],
        ]
    )


def get_orders_filter_keyboard(current_filter: str = "new") -> InlineKeyboardMarkup:
    """Buyurtmalarni holat bo'yicha filtrlash tugmalari."""
    filters = [
        ("new", "🟡 Yangi"),
        ("ready", "⏳ Tayyor"),
        ("delivered", "✅ Topshirildi"),
        ("cancelled", "❌ Bekor"),
        ("all", "📋 Barchasi"),
    ]
    row = []
    for f_key, f_label in filters:
        label = f"• {f_label} •" if f_key == current_filter else f_label
        row.append(InlineKeyboardButton(text=label, callback_data=f"adm_ord_flt:{f_key}:0"))
        if len(row) == 3:
            pass  # split nicely
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row[:2],
            row[2:],
        ]
    )
