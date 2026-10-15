from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.models import Genre, Book


def get_genres_keyboard(genres: List[Genre]) -> InlineKeyboardMarkup:
    """Janrlar ro'yxati tugmalari."""
    buttons = []
    row = []
    for genre in genres:
        row.append(
            InlineKeyboardButton(text=f"📖 {genre.name}", callback_data=f"genre:{genre.id}:0")
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="◀️ Asosiy menyu", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_books_list_keyboard(
    books: List[Book],
    page: int,
    total_count: int,
    prefix: str,  # "genre:GENRE_ID" yoki "latest" yoki "search:QUERY"
    limit: int = 6,
) -> InlineKeyboardMarkup:
    """Kitoblar ro'yxati va paginatsiya tugmalari."""
    buttons = []
    for book in books:
        status_icon = "✅" if book.quantity > 0 else "❌"
        price_str = f"{book.price:,}".replace(",", " ")
        btn_text = f"{status_icon} {book.title} — {price_str} so'm"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"book_view:{book.id}")])

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    nav_row = []

    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"page:{prefix}:{page-1}")
        )
    if total_pages > 1:
        nav_row.append(
            InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="noop")
        )
    if page + 1 < total_pages:
        nav_row.append(
            InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"page:{prefix}:{page+1}")
        )

    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_genres")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_book_card_keyboard(book: Book, is_subscribed: bool = False, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Kitob kartasi uchun inline tugmalar (admin uchun sotib olish qismi ko'rsatilmaydi)."""
    buttons = []

    if is_admin:
        # Admin uchun sotib olish o'rniga boshqarish tugmasi
        buttons.append([
            InlineKeyboardButton(text="⚙️ Kitobni boshqarish (Admin)", callback_data=f"adm_book:{book.id}")
        ])
    else:
        # Oddiy xaridor uchun
        if book.quantity > 0:
            buttons.append([
                InlineKeyboardButton(text="🛒 Buyurtma berish", callback_data=f"order_book:{book.id}")
            ])
        else:
            if is_subscribed:
                buttons.append([
                    InlineKeyboardButton(text="✅ Bildirishnomaga yozildingiz", callback_data="noop")
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(
                        text="🔔 Mavjud bo'lganda xabar berish", callback_data=f"sub_book:{book.id}"
                    )
                ])

    back_cb = "adm_bpage:0" if is_admin else "back_to_catalog"
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def get_order_quantity_keyboard(max_qty: int = 5) -> InlineKeyboardMarkup:
    """Nusxalar sonini tanlash tugmalari."""
    limit = min(5, max(1, max_qty))
    row = [
        InlineKeyboardButton(text=f"{i} dona", callback_data=f"ord_qty:{i}")
        for i in range(1, limit + 1)
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[row, [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ord_cancel")]]
    )


def get_delivery_type_keyboard() -> InlineKeyboardMarkup:
    """Yetkazib berish usulini tanlash tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏪 Do'kondan olib ketish (Toshkent)", callback_data="deliv:pickup")],
            [InlineKeyboardButton(text="🚚 Yetkazib berish (Kuryer orqali)", callback_data="deliv:delivery")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ord_cancel")],
        ]
    )


def get_order_confirm_keyboard() -> InlineKeyboardMarkup:
    """Buyurtmani tasdiqlash tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Buyurtmani tasdiqlayman", callback_data="ord_confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ord_cancel"),
            ]
        ]
    )


def get_no_search_result_keyboard(query: str) -> InlineKeyboardMarkup:
    """Qidiruv natijasi topilmaganda ko'rsatiladigan tugmalar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Taklif / Buyurtma qoldirish", callback_data=f"suggest:{query[:30]}")],
            [InlineKeyboardButton(text="🔍 Qaytadan qidirish", callback_data="search_again")],
        ]
    )
