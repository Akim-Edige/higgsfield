"""Idempotency key validation."""
from __future__ import annotations

from fastapi import Header, HTTPException


async def require_idempotency_key(
    idempotency_key: str | None = Header(None, alias="Idempotency-Key")
) -> str:
    """
    Dependency to ensure Idempotency-Key header is present.
    
    Raises:
        HTTPException: 400 if header is missing
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_IDEMPOTENCY_KEY",
                "message": "Idempotency-Key header is required for this endpoint",
            },
        )
    return idempotency_key

