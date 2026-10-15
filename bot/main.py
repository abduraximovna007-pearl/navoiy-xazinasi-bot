import asyncio
import logging
import sys
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from db.session import init_db
from bot.middlewares.db import DatabaseMiddleware

# Handlers import
from bot.handlers import (
    start,
    admin_add,
    admin_manage,
    admin_orders,
    catalog,
    order,
    user_orders,
    search,
    support,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def start_health_server(port: int):
    """
    Render Web Service uchun port ochish va health-check javobini qaytarish.
    Bu servisning Renderda to'xtab qolmasligini ta'minlaydi.
    """
    app = web.Application()

    async def handle_ping(request):
        return web.Response(text="Bot is running! Kitob do'koni boti faol.", status=200)

    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Health-check HTTP server {port}-portda ishga tushdi.")


async def main():
    logger.info("Kitob do'koni boti ishga tushirilmoqda...")

    if not config.BOT_TOKEN or "YOUR_BOT_TOKEN" in config.BOT_TOKEN or len(config.BOT_TOKEN) < 20:
        logger.error(
            "XATOLIK: BOT_TOKEN ko'rsatilmagan yoki noto'g'ri!\n"
            "Iltimos, .env faylida yoki Render Environment Variables qismida BOT_TOKEN ni belgilang."
        )
        print("\n" + "=" * 60)
        print("DIQQAT: .env faylida BOT_TOKEN kiritilmagan!")
        print("Iltimos, BotFather dan olingan tokenni .env faylidagi BOT_TOKEN ga yozing.")
        print("=" * 60 + "\n")
        return

    # 1. Bazani initsializatsiya qilish (jadvallar va boshlang'ich janrlar)
    logger.info("Ma'lumotlar bazasi tekshirilmoqda...")
    await init_db()
    logger.info("Baza jadvallari va janrlar muvaffaqiyatli tayyorlandi.")

    # 2. Aiogram Bot va Dispatcher yaratish
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 3. Middleware ulash
    dp.update.middleware(DatabaseMiddleware())

    # 4. Handler routerlarini ro'yxatga olish (Tartibi muhim!)
    dp.include_router(start.router)
    dp.include_router(admin_add.router)
    dp.include_router(admin_manage.router)
    dp.include_router(admin_orders.router)
    dp.include_router(catalog.router)
    dp.include_router(order.router)
    dp.include_router(user_orders.router)
    dp.include_router(support.router)
    dp.include_router(search.router)


    # 5. Render yoki Web Service uchun HTTP Health Check serverini ishga tushirish
    render_port = os.getenv("PORT")
    if render_port:
        try:
            await start_health_server(int(render_port))
        except Exception as e:
            logger.warning(f"Health check serverini ishga tushirishda xatolik: {e}")

    # 6. Bot ma'lumotlarini tekshirish va polling boshlash
    try:
        me = await bot.get_me()
        logger.info(f"Bot muvaffaqiyatli ulandi: @{me.username} (ID: {me.id})")
        logger.info(f"Adminlar soni: {len(config.ADMIN_IDS)} ta")
        logger.info(f"Kanal: {config.CHANNEL_ID or 'Belgilanmagan'}")

        # Eski kutilgan yangilanishlarni tashlab yuborish
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
