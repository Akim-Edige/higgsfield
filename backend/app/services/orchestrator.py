"""Orchestrator service for managing generation jobs."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.models import GenerationJob, Option
from app.domain.states import JobStatus
from app.infra.metrics import jobs_created_total

logger = get_logger(__name__)


class Orchestrator:
    """Orchestrates generation job lifecycle."""

    @staticmethod
    async def create_job(
        db: AsyncSession,
        user_id: uuid.UUID,
        option_id: uuid.UUID,
        idempotency_key: str,
    ) -> uuid.UUID:
        """
        Create a generation job (idempotent).
        
        Args:
            db: Database session
            user_id: User ID
            option_id: Option ID
            idempotency_key: Idempotency key from header
        
        Returns:
            job_id (UUID)
        """
        # Check if job already exists
        stmt = select(GenerationJob).where(
            GenerationJob.user_id == user_id,
            GenerationJob.option_id == option_id,
            GenerationJob.idempotency_key == idempotency_key,
        )
        result = await db.execute(stmt)
        existing_job = result.scalar_one_or_none()

        if existing_job:
            logger.info(
                "job_already_exists",
                job_id=str(existing_job.id),
                option_id=str(option_id),
                idempotency_key=idempotency_key,
            )
            return existing_job.id

        # Get option to determine timeout
        option_stmt = select(Option).where(Option.id == option_id)
        option_result = await db.execute(option_stmt)
        option = option_result.scalar_one_or_none()

        if not option:
            raise ValueError(f"Option {option_id} not found")

        # Determine timeout based on tool type
        timeout_seconds = Orchestrator._get_timeout_seconds(option.tool_type)
        timeout_at = datetime.utcnow() + timedelta(seconds=timeout_seconds)

        # Create job
        job = GenerationJob(
            id=uuid.uuid4(),
            option_id=option_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
            status=JobStatus.PENDING.value,
            provider="higgsfield",
            timeout_at=timeout_at,
            next_poll_at=datetime.utcnow(),  # Poll immediately
            trace_id=str(uuid.uuid4()),
        )

        db.add(job)
        await db.flush()

        # Record metrics
        jobs_created_total.labels(tool_type=option.tool_type, model_key=option.model_key).inc()

        logger.info(
            "job_created",
            job_id=str(job.id),
            option_id=str(option_id),
            user_id=str(user_id),
            tool_type=option.tool_type,
            model_key=option.model_key,
            timeout_at=timeout_at.isoformat(),
        )

        return job.id

    @staticmethod
    def _get_timeout_seconds(tool_type: str) -> int:
        """Get timeout in seconds based on tool type."""
        timeouts = {
            "text_to_image": settings.T2I_TIMEOUT_S,
            "text_to_video": settings.T2V_TIMEOUT_S,
            "image_to_video": settings.I2V_TIMEOUT_S,
            "speak": settings.T2I_TIMEOUT_S,  # Use T2I timeout for speak
        }
        return timeouts.get(tool_type, settings.T2V_TIMEOUT_S)

