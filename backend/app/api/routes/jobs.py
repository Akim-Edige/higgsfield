"""Job routes."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id_dep, get_db_dep
from app.domain.models import GenerationJob, Option
from app.domain.schemas import ErrorOut, JobCreateResponse, JobOut, JobResult
from app.domain.states import JobStatus
from app.infra.idempotency import require_idempotency_key
from app.services.orchestrator import Orchestrator
from app.workers.tasks import poll_generation

router = APIRouter(prefix="/options", tags=["jobs"])


@router.post("/{option_id}/generate", response_model=JobCreateResponse, status_code=202)
async def generate_option(
    option_id: UUID,
    user_id: UUID = Depends(get_current_user_id_dep),
    idempotency_key: str = Depends(require_idempotency_key),
    db: AsyncSession = Depends(get_db_dep),
) -> JobCreateResponse:
    """
    Start generation for an option.
    
    Requires Idempotency-Key header.
    """
    # Verify option exists
    stmt = select(Option).where(Option.id == option_id)
    result = await db.execute(stmt)
    option = result.scalar_one_or_none()

    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    # Check if attachment is required but not provided
    # TODO: Implement attachment validation

    # Create job
    job_id = await Orchestrator.create_job(db, user_id, option_id, idempotency_key)
    await db.commit()

    # Enqueue Celery task
    poll_generation.delay(str(job_id))

    return JobCreateResponse(job_id=job_id)


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: UUID,
    user_id: UUID = Depends(get_current_user_id_dep),
    db: AsyncSession = Depends(get_db_dep),
) -> JobOut:
    """Get job status."""
    stmt = select(GenerationJob).where(GenerationJob.id == job_id, GenerationJob.user_id == user_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Calculate retry_after_seconds
    retry_after_seconds = 10
    if job.next_poll_at:
        delta = (job.next_poll_at - datetime.utcnow()).total_seconds()
        retry_after_seconds = max(1, min(int(delta) + 1, 10))

    # Build response
    result_data = None
    error_data = None

    if job.status == JobStatus.SUCCEEDED.value and job.output_urls:
        result_data = JobResult(
            min_url=job.output_urls.get("min_url"),
            raw_url=job.output_urls.get("raw_url"),
            mime="image/jpeg" if job.output_urls.get("type") == "image" else "video/mp4",
        )

    if job.status in [JobStatus.FAILED.value, JobStatus.TIMEOUT.value]:
        error_data = ErrorOut(
            code=job.last_error_code or "UNKNOWN",
            message=job.last_error_message or "Job failed",
        )

    return JobOut(
        job_id=job.id,
        status=job.status,
        result=result_data,
        error=error_data,
        retry_after_seconds=retry_after_seconds,
    )

