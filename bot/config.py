import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.reload()

    def reload(self):
        load_dotenv(override=True)
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
        self.CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
        admin_ids_raw = os.getenv("ADMIN_IDS", "")
        self.ADMIN_IDS: List[int] = []
        for x in admin_ids_raw.split(","):
            val = x.strip()
            if val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
                self.ADMIN_IDS.append(int(val))

        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bookstore.db").strip()
        self.SHOP_NAME = os.getenv("SHOP_NAME", "Navoiy Xazinasi")
        self.SHOP_PHONE = os.getenv("SHOP_PHONE", "+998 50 900 50 10")
        self.SHOP_INSTAGRAM = os.getenv(
            "SHOP_INSTAGRAM", "https://www.instagram.com/navoiy_xazinasi?exln=MWswZXB1azJyZWFpeA=="
        )
        self.SHOP_ADDRESS = os.getenv("SHOP_ADDRESS", "Navoiy shahar")
        self.SHOP_WORKING_HOURS = os.getenv("SHOP_WORKING_HOURS", "09:00 dan 20:00 gacha (Har kuni)")
        self.SHOP_MAP_URL = os.getenv("SHOP_MAP_URL", "https://maps.google.com/?q=40.1030,65.3739")
        self.SHOP_LATITUDE = float(os.getenv("SHOP_LATITUDE", "40.1030"))
        self.SHOP_LONGITUDE = float(os.getenv("SHOP_LONGITUDE", "65.3739"))
        self.PORT = int(os.getenv("PORT", "8080"))

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.ADMIN_IDS


config = Config()
