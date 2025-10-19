"""Health check routes."""
from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz():
    """Basic health check."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz():
    """Readiness check (could check DB, Redis, etc.)."""
    # TODO: Add actual readiness checks
    return {"status": "ready"}
