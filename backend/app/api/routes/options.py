"""Option routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id_dep, get_db_dep
from app.domain.models import Option
from app.domain.schemas import OptionOut

router = APIRouter(prefix="/messages", tags=["options"])


@router.get("/{message_id}/options", response_model=list[OptionOut])
async def get_message_options(
    message_id: UUID,
    user_id: UUID = Depends(get_current_user_id_dep),
    db: AsyncSession = Depends(get_db_dep),
) -> list[OptionOut]:
    """Get all options for a message."""
    stmt = select(Option).where(Option.message_id == message_id).order_by(Option.created_at)
    result = await db.execute(stmt)
    options = result.scalars().all()

    if not options:
        raise HTTPException(status_code=404, detail="No options found for this message")

    return [OptionOut.model_validate(opt) for opt in options]

