import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from db.models import Base, Genre
from sqlalchemy import select


def get_normalized_database_url(raw_url: str | None) -> str:
    """Render yoki lokal muhitga mos holda async database URL ni shakllantiradi."""
    if not raw_url:
        return "sqlite+aiosqlite:///./bookstore.db"

    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

    return url


# Engine va sessionmaker yaratish
database_url = get_normalized_database_url(os.getenv("DATABASE_URL"))
engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


DEFAULT_GENRES = [
    "Badiiy adabiyot",
    "Biznes va psixologiya",
    "Diniy va ma'rifiy",
    "Bolalar adabiyoti",
    "Tarix va falsafa",
    "Ilmiy-ommabop",
    "Dasturlash va IT",
    "Chet tillari",
    "O'quv qurollari",
    "Bloknot va daftarlar",
    "Kantselyariya tovarlari",
    "Sovg'alar va aksessuarlar",
    "Boshqa",
]



async def init_db():
    """Jadvallarni yaratish va boshlang'ich janrlarni qo'shish."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Boshlang'ich janrlar borligini tekshirish
    async with async_session_maker() as session:
        result = await session.execute(select(Genre))
        existing_genres = {g.name for g in result.scalars().all()}
        for genre_name in DEFAULT_GENRES:
            if genre_name not in existing_genres:
                session.add(Genre(name=genre_name))
        await session.commit()
