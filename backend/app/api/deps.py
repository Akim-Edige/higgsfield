"""API dependencies."""
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.infra.db import get_db


async def get_current_user_id_dep() -> UUID:
    """Get current user ID (stub for demo)."""
    return get_current_user_id()


async def get_db_dep() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_db():
        yield session

