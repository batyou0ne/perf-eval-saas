from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# Neon requires SSL; asyncpg's connect() takes ssl=, not the libpq-style
# sslmode= query param, so this is passed as connect_args instead of being
# part of DATABASE_URL.
connect_args = {"ssl": "require"} if settings.environment != "development" else {}

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Shared declarative base — every SQLAlchemy model inherits from this."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
