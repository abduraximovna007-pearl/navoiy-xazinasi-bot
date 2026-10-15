import asyncio
import sys
import io
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from db.models import Base, Genre
from sqlalchemy import select

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from db.crud import (
    create_book,
    get_book_by_id,
    update_book_stock,
    update_book_price,
    create_order,
    get_order_by_id,
    get_or_create_user,
    get_all_genres,
    get_all_books_for_search,
    get_admin_stats,
    subscribe_to_book,
    get_pending_subscribers,
    log_search,
    get_unfound_searches,
)
from bot.services.search import search_books
from bot.services.channel import format_channel_post_caption

TEST_DB_PATH = "./test_isolated.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_maker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def run_tests():
    # Tozalash
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Dastlabki janrlar
    default_genres = ["Badiiy adabiyot", "Biznes va psixologiya", "O'quv qurollari"]
    async with test_session_maker() as session:
        for g in default_genres:
            session.add(Genre(name=g))
        await session.commit()

        print("--- 1. Testing DB Initialization on isolated test DB ---")
        genres = await get_all_genres(session)
        assert len(genres) >= 3
        print(f"✅ Genres initialized successfully: {[g.name for g in genres]}...")

        # 2. Test User creation
        print("--- 2. Testing User CRUD ---")
        user = await get_or_create_user(session, telegram_id=999888777, full_name="Ali Valiyev", username="aliv")
        assert user.telegram_id == 999888777
        print("✅ User created successfully")

        # 3. Test Book creation
        print("--- 3. Testing Book creation ---")
        genre_id = genres[0].id
        book = await create_book(
            session=session,
            title="Ikki eshik orasida",
            author="O'tkir Hoshimov",
            price=65000,
            genre_id=genre_id,
            description="O'zbek adabiyotining durdona asari.",
            quantity=3,
            images=["file_id_mock_12345"],
        )
        assert book.id is not None
        assert book.quantity == 3
        print(f"✅ Book created: {book.title} (ID: {book.id})")

        # Test Book 2 (for search)
        book2 = await create_book(
            session=session,
            title="Atom odatlar",
            author="Jeyms Klir",
            price=75000,
            genre_id=genres[1].id,
            description="Kichik o'zgarishlar, ulkan natijalar.",
            quantity=0,  # Sold out
            images=[],
        )
        print(f"✅ Book 2 created: {book2.title} (Quantity: {book2.quantity})")

        # 4. Test Search Engine (Transliteration and fuzzy matching)
        print("--- 4. Testing Search Engine with Typos and Cyrillic/Latin ---")
        all_books = await get_all_books_for_search(session)

        # Test A: Typo tolerance: "Ikki eshik orasi" -> should match "Ikki eshik orasida"
        res_typo = search_books("Ikki eshik orasi", all_books)
        assert len(res_typo) > 0 and res_typo[0][0].title == "Ikki eshik orasida"
        print(f"✅ Typo search match: 'Ikki eshik orasi' matched '{res_typo[0][0].title}' with score {res_typo[0][1]}")

        # Test B: Cyrillic search for Latin book: "Икки эшик орасида" -> should match
        res_cyrillic = search_books("Икки эшик орасида", all_books)
        assert len(res_cyrillic) > 0 and res_cyrillic[0][0].title == "Ikki eshik orasida"
        print(f"✅ Cyrillic search match: 'Икки эшик орасида' matched '{res_cyrillic[0][0].title}' with score {res_cyrillic[0][1]}")

        # Test C: Author search: "O'tkir" or "Hoshimov"
        res_author = search_books("Hoshimov", all_books)
        assert len(res_author) > 0 and res_author[0][0].title == "Ikki eshik orasida"
        print(f"✅ Author search match: 'Hoshimov' matched '{res_author[0][0].title}'")

        # Test D: Unfound query logging
        await log_search(session, "Garri Potter", found=False, user_id=user.id)
        unfound = await get_unfound_searches(session)
        assert any(q == "garri potter" for q, _ in unfound)
        print("✅ Unfound search log successfully recorded")

        # 5. Test Stock and Channel Caption
        print("--- 5. Testing Channel Post Formatting and Stock Delta ---")
        caption = format_channel_post_caption(book, "kitob_test_bot")
        assert "Ikki eshik orasida" in caption
        assert "65 000 so'm" in caption
        assert "Mavjud (3 ta)" in caption
        print("✅ Channel caption formatted properly")

        updated_book = await update_book_stock(session, book.id, -1)
        assert updated_book.quantity == 2
        print(f"✅ Stock decremented to {updated_book.quantity}")

        # 6. Test Book Subscription for Sold Out book
        print("--- 6. Testing Book Restock Subscriptions ---")
        sub_ok = await subscribe_to_book(session, book2.id, user.id)
        assert sub_ok is True
        subs = await get_pending_subscribers(session, book2.id)
        assert len(subs) == 1 and subs[0].id == user.id
        print("✅ Restock subscription registered")

        # 7. Test Order Creation and Calculations
        print("--- 7. Testing Order Flow ---")
        order = await create_order(
            session=session,
            user_id=user.id,
            customer_name="Ali Valiyev",
            customer_phone="+998901234567",
            customer_username="ali_valiyev",
            delivery_type="delivery",
            address="Toshkent, Yunusobod 4",
            notes="Iltimos, soat 18:00 dan keyin olib keling",
            items=[{"book_id": book.id, "quantity": 2, "price": 65000}],
        )
        assert order.id is not None
        assert order.total_price == 130000
        print(f"✅ Order #ORD-{order.id} created with total price {order.total_price} so'm")

        # 8. Test Admin Stats
        print("--- 8. Testing Admin Statistics ---")
        stats = await get_admin_stats(session)
        assert stats["total_books"] == 2
        assert stats["total_orders"] == 1
        print("✅ Admin statistics calculated correctly:", stats)

    await test_engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    print("\n🎉 ALL UNIT AND INTEGRATION TESTS PASSED 100% (Isolated DB)!")


if __name__ == "__main__":
    asyncio.run(run_tests())
