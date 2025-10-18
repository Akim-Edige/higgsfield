"""Database infrastructure: async SQLAlchemy engine and session management."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DB_DSN,
    echo=settings.APP_DEBUG,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Only commit if transaction is still active
            if session.in_transaction():
                await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

