"""Celery tasks for background job processing."""
import asyncio
import random
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.models import GenerationJob, Option
from app.domain.states import TERMINAL_STATUSES, JobStatus
from app.infra.db import get_db_context
from app.infra.metrics import (
    jobs_failed_total,
    jobs_succeeded_total,
    jobs_timeout_total,
    provider_errors_total,
    provider_polls_total,
    queue_depth,
)
from app.services.provider_higgsfield import (
    ProviderError,
    RateLimitError,
    get_provider,
)
from app.services.sse_broker import get_sse_broker
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


def next_interval_ms(attempt: int, min_ms: int, max_ms: int, jitter: float) -> int:
    """
    Calculate next polling interval with exponential backoff and jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        min_ms: Minimum interval in milliseconds
        max_ms: Maximum interval in milliseconds
        jitter: Jitter factor (e.g., 0.2 for ±20%)
    
    Returns:
        Next interval in milliseconds
    """
    base = min_ms * (2**attempt)
    capped = min(base, max_ms)
    jitter_range = capped * jitter
    return int(capped + random.uniform(-jitter_range, jitter_range))


@celery_app.task(name="app.workers.tasks.poll_generation", bind=True, max_retries=None)
def poll_generation(self, job_id: str) -> None:
    """
    Poll generation job status.
    
    This is a Celery task that polls the provider for job status and
    updates the database accordingly.
    """
    asyncio.run(_poll_generation_async(job_id))


async def _poll_generation_async(job_id: str) -> None:
    """Async implementation of poll_generation."""
    job_uuid = UUID(job_id)
    provider = get_provider()
    sse_broker = get_sse_broker()

    async with get_db_context() as db:
        # Load job
        stmt = select(GenerationJob).where(GenerationJob.id == job_uuid)
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            logger.error("job_not_found", job_id=job_id)
            return

        # Check if job is already terminal
        if job.status in [s.value for s in TERMINAL_STATUSES]:
            logger.info("job_already_terminal", job_id=job_id, status=job.status)
            return

        # Check timeout
        now = datetime.utcnow()
        if job.timeout_at and now >= job.timeout_at:
            logger.warning("job_timeout", job_id=job_id, timeout_at=job.timeout_at.isoformat())
            job.status = JobStatus.TIMEOUT.value
            job.finished_at = now
            job.last_error_code = "TIMEOUT"
            job.last_error_message = "Job exceeded timeout"
            await db.commit()

            # Load option for metrics
            option = await db.get(Option, job.option_id)
            if option:
                jobs_timeout_total.labels(
                    tool_type=option.tool_type, model_key=option.model_key
                ).inc()

            # Publish SSE event
            await sse_broker.publish(
                f"chat:{job.user_id}",
                {
                    "type": "job.updated",
                    "job_id": str(job.id),
                    "status": job.status,
                },
            )
            return

        # Load option
        option = await db.get(Option, job.option_id)
        if not option:
            logger.error("option_not_found", job_id=job_id, option_id=str(job.option_id))
            job.status = JobStatus.FAILED.value
            job.finished_at = now
            job.last_error_code = "OPTION_NOT_FOUND"
            job.last_error_message = "Associated option not found"
            await db.commit()
            return

        try:
            # If no provider_job_set_id, start generation
            if not job.provider_job_set_id:
                logger.info("starting_provider_job", job_id=job_id, model_key=option.model_key)
                job.status = JobStatus.RUNNING.value
                job.started_at = now
                job.attempts += 1

                # Формируем параметры из option
                parameters = {
                    "style_id": option.style_id,
                    "aspect_ratio": "16:9",  # можно добавить в Option если нужно
                    "quality": "1080p",
                }
                
                provider_job_set_id = await provider.start_generation(
                    model_key=option.model_key,
                    parameters=parameters,
                    prompt=option.enhanced_prompt,
                )

                job.provider_job_set_id = provider_job_set_id
                job.next_poll_at = now + timedelta(
                    milliseconds=next_interval_ms(
                        0,
                        settings.POLL_MIN_INTERVAL_MS,
                        settings.POLL_MAX_INTERVAL_MS,
                        settings.POLL_JITTER,
                    )
                )
                await db.commit()

                # Requeue
                delay_seconds = max(1, int((job.next_poll_at - now).total_seconds()))
                poll_generation.apply_async(args=[job_id], countdown=delay_seconds)
                return

            # Check if it's time to poll
            if job.next_poll_at and now < job.next_poll_at:
                # Not time yet, requeue with appropriate delay
                delay_seconds = max(1, int((job.next_poll_at - now).total_seconds()))
                logger.debug(
                    "job_not_ready_to_poll",
                    job_id=job_id,
                    next_poll_at=job.next_poll_at.isoformat(),
                    delay_seconds=delay_seconds,
                )
                poll_generation.apply_async(args=[job_id], countdown=delay_seconds)
                return

            # Poll provider
            logger.info(
                "polling_provider",
                job_id=job_id,
                provider_job_set_id=job.provider_job_set_id,
                attempt=job.attempts,
            )
            job_set_data = await provider.get_job_set(job.provider_job_set_id)
            job.last_polled_at = now
            job.attempts += 1

            provider_status = job_set_data["status"]
            provider_polls_total.labels(model_key=option.model_key, status=provider_status).inc()

            if provider_status == "completed":
                # Success!
                logger.info("job_completed", job_id=job_id)
                job.status = JobStatus.SUCCEEDED.value
                job.finished_at = now
                job.progress = 100

                # Extract results
                results = job_set_data.get("results", [])
                if results:
                    result = results[0]
                    job.output_urls = {
                        "min_url": result.get("min_url"),
                        "raw_url": result.get("raw_url"),
                        "type": result.get("type"),
                    }

                await db.commit()

                # Metrics
                jobs_succeeded_total.labels(
                    tool_type=option.tool_type, model_key=option.model_key
                ).inc()

                # SSE
                await sse_broker.publish(
                    f"chat:{job.user_id}",
                    {
                        "type": "job.updated",
                        "job_id": str(job.id),
                        "status": job.status,
                        "result": job.output_urls,
                    },
                )

            elif provider_status == "failed":
                # Failed
                logger.warning("job_failed", job_id=job_id)
                job.status = JobStatus.FAILED.value
                job.finished_at = now
                job.last_error_code = "PROVIDER_FAILED"
                job.last_error_message = "Provider reported failure"
                await db.commit()

                # Metrics
                jobs_failed_total.labels(
                    tool_type=option.tool_type,
                    model_key=option.model_key,
                    error_code=job.last_error_code,
                ).inc()

                # SSE
                await sse_broker.publish(
                    f"chat:{job.user_id}",
                    {
                        "type": "job.updated",
                        "job_id": str(job.id),
                        "status": job.status,
                        "error": {
                            "code": job.last_error_code,
                            "message": job.last_error_message,
                        },
                    },
                )

            else:
                # Still processing, schedule next poll
                interval_ms = next_interval_ms(
                    job.attempts,
                    settings.POLL_MIN_INTERVAL_MS,
                    settings.POLL_MAX_INTERVAL_MS,
                    settings.POLL_JITTER,
                )
                job.next_poll_at = now + timedelta(milliseconds=interval_ms)
                await db.commit()

                delay_seconds = max(1, int(interval_ms / 1000))
                logger.debug(
                    "job_still_processing",
                    job_id=job_id,
                    provider_status=provider_status,
                    next_poll_in_seconds=delay_seconds,
                )
                poll_generation.apply_async(args=[job_id], countdown=delay_seconds)

        except RateLimitError as e:
            # Rate limited - back off aggressively
            logger.warning("rate_limited", job_id=job_id)
            job.last_error_code = e.code
            job.last_error_message = str(e)
            backoff_ms = next_interval_ms(
                job.attempts + 5,  # More aggressive backoff
                settings.POLL_MIN_INTERVAL_MS,
                settings.POLL_MAX_INTERVAL_MS,
                settings.POLL_JITTER,
            )
            job.next_poll_at = now + timedelta(milliseconds=backoff_ms)
            await db.commit()

            provider_errors_total.labels(error_type="rate_limit").inc()

            delay_seconds = max(1, int(backoff_ms / 1000))
            poll_generation.apply_async(args=[job_id], countdown=delay_seconds)

        except ProviderError as e:
            logger.error("provider_error", job_id=job_id, error=str(e), code=e.code)
            job.last_error_code = e.code
            job.last_error_message = str(e)

            if e.retryable:
                # Retry with backoff
                backoff_ms = next_interval_ms(
                    job.attempts,
                    settings.POLL_MIN_INTERVAL_MS,
                    settings.POLL_MAX_INTERVAL_MS,
                    settings.POLL_JITTER,
                )
                job.next_poll_at = now + timedelta(milliseconds=backoff_ms)
                await db.commit()

                provider_errors_total.labels(error_type=e.code).inc()

                delay_seconds = max(1, int(backoff_ms / 1000))
                poll_generation.apply_async(args=[job_id], countdown=delay_seconds)
            else:
                # Non-retryable error, mark as failed
                job.status = JobStatus.FAILED.value
                job.finished_at = now
                await db.commit()

                jobs_failed_total.labels(
                    tool_type=option.tool_type, model_key=option.model_key, error_code=e.code
                ).inc()

                # SSE
                await sse_broker.publish(
                    f"chat:{job.user_id}",
                    {
                        "type": "job.updated",
                        "job_id": str(job.id),
                        "status": job.status,
                        "error": {"code": e.code, "message": str(e)},
                    },
                )

        except Exception as e:
            # Unexpected error
            logger.error("unexpected_error", job_id=job_id, error=str(e), exc_info=True)
            job.last_error_code = "INTERNAL_ERROR"
            job.last_error_message = str(e)

            # Retry with backoff
            backoff_ms = next_interval_ms(
                job.attempts,
                settings.POLL_MIN_INTERVAL_MS,
                settings.POLL_MAX_INTERVAL_MS,
                settings.POLL_JITTER,
            )
            job.next_poll_at = now + timedelta(milliseconds=backoff_ms)
            await db.commit()

            provider_errors_total.labels(error_type="internal_error").inc()

            delay_seconds = max(1, int(backoff_ms / 1000))
            poll_generation.apply_async(args=[job_id], countdown=delay_seconds)


@celery_app.task(name="app.workers.tasks.update_queue_depth")
def update_queue_depth() -> None:
    """Update queue depth metric (periodic task)."""
    asyncio.run(_update_queue_depth_async())


async def _update_queue_depth_async() -> None:
    """Async implementation of update_queue_depth."""
    async with get_db_context() as db:
        from sqlalchemy import func

        stmt = select(func.count(GenerationJob.id)).where(
            GenerationJob.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value])
        )
        result = await db.execute(stmt)
        count = result.scalar() or 0
        queue_depth.set(count)

