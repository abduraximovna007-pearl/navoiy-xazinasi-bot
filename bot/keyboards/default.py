from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Asosiy menyu tugmalari."""
    buttons = [
        [KeyboardButton(text="🔍 Kitob qidirish")],
        [KeyboardButton(text="📖 Janrlar"), KeyboardButton(text="🆕 Yangi kelganlar")],
        [KeyboardButton(text="📦 Mening buyurtmalarim"), KeyboardButton(text="❓ Savol yo'llash")],
        [KeyboardButton(text="📞 Biz haqimizda")],
    ]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Quyidagi menyulardan birini tanlang...",
    )



def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqamini ulashish tugmasi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamimni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish tugmasi."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
