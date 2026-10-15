import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, update, delete, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import (
    User,
    Genre,
    Book,
    BookImage,
    ChannelPost,
    Order,
    OrderItem,
    SearchLog,
    BookSubscription,
)


# ===================== USER CRUD =====================

async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    username: Optional[str] = None,
    role: str = "customer",
) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Ism yoki usernameni yangilab turamiz
        updated = False
        if user.full_name != full_name:
            user.full_name = full_name
            updated = True
        if user.username != username:
            user.username = username
            updated = True
        if updated:
            await session.commit()
            await session.refresh(user)

    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_user_phone(session: AsyncSession, user_id: int, phone: str):
    stmt = update(User).where(User.id == user_id).values(phone=phone)
    await session.execute(stmt)
    await session.commit()


# ===================== GENRE CRUD =====================

async def get_all_genres(session: AsyncSession) -> List[Genre]:
    stmt = select(Genre).order_by(Genre.name)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_genre_by_id(session: AsyncSession, genre_id: int) -> Optional[Genre]:
    stmt = select(Genre).where(Genre.id == genre_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_genre(session: AsyncSession, name: str) -> Genre:
    clean_name = name.strip()
    stmt = select(Genre).where(func.lower(Genre.name) == func.lower(clean_name))
    result = await session.execute(stmt)
    genre = result.scalar_one_or_none()
    if not genre:
        genre = Genre(name=clean_name)
        session.add(genre)
        await session.commit()
        await session.refresh(genre)
    return genre


# ===================== BOOK CRUD =====================

async def create_book(
    session: AsyncSession,
    title: str,
    author: str,
    price: int,
    genre_id: Optional[int],
    description: Optional[str],
    quantity: int,
    images: List[str],
) -> Book:
    book = Book(
        title=title.strip(),
        author=author.strip(),
        price=price,
        genre_id=genre_id,
        description=description.strip() if description else None,
        quantity=max(0, quantity),
        is_active=True,
    )
    session.add(book)
    await session.flush()

    for idx, file_id in enumerate(images):
        img = BookImage(
            book_id=book.id,
            telegram_file_id=file_id,
            position=idx,
        )
        session.add(img)

    await session.commit()
    await session.refresh(book)
    return await get_book_by_id(session, book.id)


async def get_book_by_id(session: AsyncSession, book_id: int) -> Optional[Book]:
    stmt = (
        select(Book)
        .options(
            selectinload(Book.genre),
            selectinload(Book.images),
            selectinload(Book.channel_post),
        )
        .where(Book.id == book_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_active_books(session: AsyncSession, limit: int = 10, offset: int = 0) -> List[Book]:
    stmt = (
        select(Book)
        .options(selectinload(Book.genre), selectinload(Book.images))
        .where(Book.is_active == True)
        .order_by(desc(Book.id))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_latest_books(session: AsyncSession, limit: int = 10) -> List[Book]:
    stmt = (
        select(Book)
        .options(selectinload(Book.genre), selectinload(Book.images))
        .where(Book.is_active == True, Book.quantity > 0)
        .order_by(desc(Book.created_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_books_by_genre(
    session: AsyncSession, genre_id: int, limit: int = 10, offset: int = 0
) -> Tuple[List[Book], int]:
    count_stmt = select(func.count(Book.id)).where(Book.genre_id == genre_id, Book.is_active == True)
    total_count = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Book)
        .options(selectinload(Book.genre), selectinload(Book.images))
        .where(Book.genre_id == genre_id, Book.is_active == True)
        .order_by(desc(Book.id))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), total_count


async def get_all_books_for_search(session: AsyncSession) -> List[Book]:
    stmt = (
        select(Book)
        .options(selectinload(Book.genre), selectinload(Book.images))
        .where(Book.is_active == True)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_book_stock(session: AsyncSession, book_id: int, delta: int) -> Optional[Book]:
    book = await get_book_by_id(session, book_id)
    if not book:
        return None
    new_qty = max(0, book.quantity + delta)
    book.quantity = new_qty
    book.updated_at = datetime.datetime.utcnow()
    await session.commit()
    return await get_book_by_id(session, book_id)


async def set_book_quantity(session: AsyncSession, book_id: int, quantity: int) -> Optional[Book]:
    book = await get_book_by_id(session, book_id)
    if not book:
        return None
    book.quantity = max(0, quantity)
    book.updated_at = datetime.datetime.utcnow()
    await session.commit()
    return await get_book_by_id(session, book_id)


async def update_book_price(session: AsyncSession, book_id: int, new_price: int) -> Optional[Book]:
    book = await get_book_by_id(session, book_id)
    if not book:
        return None
    book.price = new_price
    book.updated_at = datetime.datetime.utcnow()
    await session.commit()
    return await get_book_by_id(session, book_id)



async def delete_book(session: AsyncSession, book_id: int) -> bool:
    book = await get_book_by_id(session, book_id)
    if not book:
        return False
    await session.delete(book)
    await session.commit()
    return True


async def get_all_books_admin(session: AsyncSession, limit: int = 20, offset: int = 0) -> Tuple[List[Book], int]:
    count_stmt = select(func.count(Book.id))
    total_count = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Book)
        .options(selectinload(Book.genre), selectinload(Book.images), selectinload(Book.channel_post))
        .order_by(desc(Book.id))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), total_count


# ===================== CHANNEL POST CRUD =====================

async def save_channel_post(session: AsyncSession, book_id: int, channel_message_id: int) -> ChannelPost:
    stmt = select(ChannelPost).where(ChannelPost.book_id == book_id)
    result = await session.execute(stmt)
    post = result.scalar_one_or_none()

    if post:
        post.channel_message_id = channel_message_id
        post.posted_at = datetime.datetime.utcnow()
    else:
        post = ChannelPost(book_id=book_id, channel_message_id=channel_message_id)
        session.add(post)

    await session.commit()
    await session.refresh(post)
    return post


async def get_channel_post_by_book_id(session: AsyncSession, book_id: int) -> Optional[ChannelPost]:
    stmt = select(ChannelPost).where(ChannelPost.book_id == book_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ===================== ORDER CRUD =====================

async def create_order(
    session: AsyncSession,
    user_id: int,
    customer_name: str,
    customer_phone: str,
    delivery_type: str,
    address: Optional[str],
    notes: Optional[str],
    items: List[Dict[str, Any]],  # [{"book_id": int, "quantity": int, "price": int}]
    customer_username: Optional[str] = None,
) -> Order:
    total_price = sum(item["price"] * item["quantity"] for item in items)
    order = Order(
        user_id=user_id,
        status="new",
        delivery_type=delivery_type,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_username=customer_username,
        address=address,
        notes=notes,
        total_price=total_price,
    )

    session.add(order)
    await session.flush()

    for item in items:
        order_item = OrderItem(
            order_id=order.id,
            book_id=item["book_id"],
            quantity=item["quantity"],
            price_at_order=item["price"],
        )
        session.add(order_item)

    await session.commit()
    await session.refresh(order)
    return await get_order_by_id(session, order.id)


async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    stmt = (
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.book),
        )
        .where(Order.id == order_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_orders(session: AsyncSession, user_id: int, limit: int = 10) -> List[Order]:
    stmt = (
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.book),
        )
        .where(Order.user_id == user_id)
        .order_by(desc(Order.created_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_orders_by_status(
    session: AsyncSession, status: Optional[str] = None, limit: int = 10, offset: int = 0
) -> Tuple[List[Order], int]:
    base_query = select(Order)
    count_query = select(func.count(Order.id))

    if status and status != "all":
        base_query = base_query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)

    total_count = (await session.execute(count_query)).scalar() or 0

    stmt = (
        base_query.options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.book),
        )
        .order_by(desc(Order.created_at))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all()), total_count


async def update_order_status(session: AsyncSession, order_id: int, new_status: str) -> Optional[Order]:
    order = await get_order_by_id(session, order_id)
    if not order:
        return None
    order.status = new_status
    order.updated_at = datetime.datetime.utcnow()
    await session.commit()
    await session.refresh(order)
    return order


# ===================== SEARCH LOG CRUD =====================

async def log_search(
    session: AsyncSession, query: str, found: bool, user_id: Optional[int] = None
):
    clean_query = query.strip()
    if not clean_query:
        return
    log = SearchLog(query=clean_query, found=found, user_id=user_id)
    session.add(log)
    await session.commit()


async def get_unfound_searches(session: AsyncSession, limit: int = 15) -> List[Tuple[str, int]]:
    # Topilmagan so'rovlarni chastotasi bo'yicha guruhlash
    stmt = (
        select(func.lower(SearchLog.query).label("q"), func.count(SearchLog.id).label("cnt"))
        .where(SearchLog.found == False)
        .group_by(func.lower(SearchLog.query))
        .order_by(desc("cnt"))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


# ===================== SUBSCRIPTION CRUD =====================

async def subscribe_to_book(session: AsyncSession, book_id: int, user_id: int) -> bool:
    stmt = select(BookSubscription).where(
        BookSubscription.book_id == book_id,
        BookSubscription.user_id == user_id,
        BookSubscription.is_notified == False,
    )
    result = await session.execute(stmt)
    sub = result.scalar_one_or_none()
    if sub:
        return False  # Allaqachon obuna bo'lgan

    new_sub = BookSubscription(book_id=book_id, user_id=user_id, is_notified=False)
    session.add(new_sub)
    await session.commit()
    return True


async def get_pending_subscribers(session: AsyncSession, book_id: int) -> List[User]:
    stmt = (
        select(User)
        .join(BookSubscription, BookSubscription.user_id == User.id)
        .where(BookSubscription.book_id == book_id, BookSubscription.is_notified == False)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_subscribers_notified(session: AsyncSession, book_id: int):
    stmt = (
        update(BookSubscription)
        .where(BookSubscription.book_id == book_id, BookSubscription.is_notified == False)
        .values(is_notified=True)
    )
    await session.execute(stmt)
    await session.commit()


# ===================== STATS =====================

async def get_admin_stats(session: AsyncSession) -> Dict[str, Any]:
    total_books = (await session.execute(select(func.count(Book.id)))).scalar() or 0
    available_books = (
        await session.execute(select(func.count(Book.id)).where(Book.is_active == True, Book.quantity > 0))
    ).scalar() or 0
    sold_out_books = (
        await session.execute(select(func.count(Book.id)).where(Book.is_active == True, Book.quantity == 0))
    ).scalar() or 0

    total_orders = (await session.execute(select(func.count(Order.id)))).scalar() or 0
    new_orders = (await session.execute(select(func.count(Order.id)).where(Order.status == "new"))).scalar() or 0
    ready_orders = (await session.execute(select(func.count(Order.id)).where(Order.status == "ready"))).scalar() or 0
    delivered_orders = (
        await session.execute(select(func.count(Order.id)).where(Order.status == "delivered"))
    ).scalar() or 0
    cancelled_orders = (
        await session.execute(select(func.count(Order.id)).where(Order.status == "cancelled"))
    ).scalar() or 0

    # Yetkazilgan (sotilgan) buyurtmalar summasi
    total_revenue_stmt = select(func.sum(Order.total_price)).where(Order.status == "delivered")
    total_revenue = (await session.execute(total_revenue_stmt)).scalar() or 0

    unfound_searches = await get_unfound_searches(session, limit=5)

    return {
        "total_books": total_books,
        "available_books": available_books,
        "sold_out_books": sold_out_books,
        "total_orders": total_orders,
        "new_orders": new_orders,
        "ready_orders": ready_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,
        "total_revenue": total_revenue,
        "unfound_searches": unfound_searches,
    }
