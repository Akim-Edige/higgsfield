# Implementation Details

This document explains the key technical decisions, patterns, and implementation details of the Higgsfield Backend API.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Design](#database-design)
3. [Async Job Processing](#async-job-processing)
4. [Idempotency](#idempotency)
5. [Polling Strategy](#polling-strategy)
6. [S3 URL Rewriting](#s3-url-rewriting)
7. [Error Handling](#error-handling)
8. [Testing Strategy](#testing-strategy)

## Architecture Overview

### Layered Architecture

```
┌──────────────────────────────────────────┐
│          API Layer (FastAPI)             │
│  • Routes (REST endpoints)               │
│  • Request/Response validation           │
│  • OpenAPI documentation                 │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│          Service Layer                   │
│  • Business logic                        │
│  • Orchestration                         │
│  • Provider integration                  │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│          Domain Layer                    │
│  • Models (SQLAlchemy)                   │
│  • Schemas (Pydantic)                    │
│  • States & Enums                        │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│          Infrastructure Layer            │
│  • Database (async SQLAlchemy)           │
│  • Redis                                 │
│  • S3 (boto3)                            │
│  • Metrics (Prometheus)                  │
└──────────────────────────────────────────┘
```

### Key Design Patterns

1. **Repository Pattern**: Database access abstracted through service layer
2. **Dependency Injection**: FastAPI's `Depends()` for clean dependencies
3. **Factory Pattern**: Provider and broker instances via singleton factories
4. **Strategy Pattern**: Different prompt enhancement strategies per tool type
5. **Observer Pattern**: SSE broker for pub/sub notifications

## Database Design

### Entity Relationships

```
users
  ├──< chats
  │     └──< messages
  │           └──< options
  │                 └──< generation_jobs
  └──< attachments
```

### Key Design Decisions

1. **UUID Primary Keys**: Better for distributed systems, no sequential leaks
2. **Timestamptz**: All timestamps stored with timezone (UTC)
3. **JSONB Columns**: Flexible for `parameters`, `render_payload`, `output_urls`
4. **Composite Unique Indexes**: Enforce idempotency at database level
5. **Partial Indexes**: Optimize queries for active jobs only

### Index Strategy

```sql
-- Fast keyset pagination
CREATE INDEX ix_chats_user_created ON chats (user_id, created_at DESC, id DESC);
CREATE INDEX ix_messages_chat_created ON messages (chat_id, created_at DESC, id DESC);

-- Job polling optimization
CREATE INDEX ix_jobs_next_poll ON generation_jobs (next_poll_at) 
  WHERE status IN ('PENDING', 'RUNNING');

-- Idempotency enforcement
CREATE UNIQUE INDEX ix_jobs_user_option_idem ON generation_jobs 
  (user_id, option_id, idempotency_key);
```

## Async Job Processing

### Celery Task Flow

```
1. API receives POST /options/{id}/generate
   ↓
2. Orchestrator.create_job() → Returns job_id
   ↓
3. Enqueue Celery task: poll_generation(job_id)
   ↓
4. Worker picks up task
   ↓
5. Task checks if time to poll (next_poll_at)
   ↓
6. If not time: requeue with delay
   ↓
7. If time: poll provider API
   ↓
8. Based on response:
   - queued/processing → calculate backoff, requeue
   - completed → extract results, update job, publish SSE
   - failed → mark failed, publish SSE
   - error → classify, retry if retryable
```

### Task Requeuing

Instead of using Celery's built-in retry mechanism (which has limitations), we use explicit requeuing with calculated delays:

```python
# Calculate next poll time with exponential backoff
next_poll_at = now + timedelta(milliseconds=interval_ms)

# Requeue with specific countdown
poll_generation.apply_async(
    args=[job_id], 
    countdown=delay_seconds
)
```

**Benefits**:
- Fine-grained control over retry timing
- Respects provider's rate limits
- Easy to implement jitter
- Can handle timeout logic independently

## Idempotency

### Why It Matters

Without idempotency, network retries or duplicate requests could:
- Create multiple jobs for the same operation
- Charge users multiple times
- Waste provider credits
- Create data inconsistencies

### Implementation

1. **Header Requirement**: `Idempotency-Key` header required via FastAPI dependency
2. **Database Constraint**: Unique index on `(user_id, option_id, idempotency_key)`
3. **Service Logic**: Check existing job before creating new one

```python
# In orchestrator.py
stmt = select(GenerationJob).where(
    GenerationJob.user_id == user_id,
    GenerationJob.option_id == option_id,
    GenerationJob.idempotency_key == idempotency_key,
)
existing_job = await db.execute(stmt).scalar_one_or_none()

if existing_job:
    return existing_job.id  # Return existing job
```

### Best Practices

- Use UUIDs as idempotency keys
- Keys should be generated client-side
- Same key = same operation intent
- Different key = different operation (even if identical params)

## Polling Strategy

### Exponential Backoff with Jitter

```python
def next_interval_ms(attempt: int, min_ms: int, max_ms: int, jitter: float) -> int:
    base = min_ms * (2 ** attempt)
    capped = min(base, max_ms)
    jitter_range = capped * jitter
    return int(capped + random.uniform(-jitter_range, jitter_range))
```

**Example progression** (min=1000ms, max=30000ms, jitter=0.2):

| Attempt | Base | With Jitter |
|---------|------|-------------|
| 0 | 1000ms | 800-1200ms |
| 1 | 2000ms | 1600-2400ms |
| 2 | 4000ms | 3200-4800ms |
| 3 | 8000ms | 6400-9600ms |
| 4 | 16000ms | 12800-19200ms |
| 5+ | 30000ms (capped) | 24000-36000ms |

### Why Jitter?

Without jitter, all jobs started at the same time would poll at the same intervals, creating load spikes. Jitter spreads the load over time.

### Timeout Handling

Each job has a `timeout_at` timestamp calculated based on tool type:

```python
T2I_TIMEOUT_S = 180   # 3 minutes
I2V_TIMEOUT_S = 1200  # 20 minutes
T2V_TIMEOUT_S = 1200  # 20 minutes
```

The worker checks timeout on every poll attempt and marks the job as `TIMEOUT` if exceeded.

## S3 URL Rewriting

### The Problem

In Docker Compose:
- Backend/Worker use `http://localstack:4566` (internal Docker network)
- Browser uses `http://localhost:4566` (host machine)

Presigned URLs generated with internal endpoint won't work in browser.

### The Solution

```python
def rewrite_to_public(url: str) -> str:
    """Rewrite S3 URL from internal endpoint to public endpoint."""
    parsed = urlparse(url)
    internal_parsed = urlparse(settings.S3_ENDPOINT_INTERNAL)
    public_parsed = urlparse(settings.S3_PUBLIC_ENDPOINT)
    
    if parsed.netloc == internal_parsed.netloc:
        return urlunparse((
            public_parsed.scheme,
            public_parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))
    
    return url
```

### Production Considerations

In production with real AWS S3:
- Set `S3_ENDPOINT_INTERNAL=""` (use default AWS endpoints)
- Set `S3_PUBLIC_ENDPOINT=""` (or CloudFront distribution)
- URL rewriting becomes a no-op or simple CloudFront swap

## Error Handling

### Error Classification

Provider errors are classified into:

1. **Retryable**:
   - Network errors (timeout, connection refused)
   - 429 Rate Limit
   - 5xx Server errors

2. **Non-retryable**:
   - 400 Bad Request (invalid params)
   - 404 Not Found
   - Content policy violations

```python
class ProviderError(Exception):
    def __init__(self, message: str, code: str, retryable: bool):
        self.code = code
        self.retryable = retryable
```

### Retry Strategy

- **Retryable errors**: Apply exponential backoff, requeue task
- **Non-retryable errors**: Mark job as FAILED immediately
- **Rate limits**: Use more aggressive backoff (attempt + 5)

### Metrics

All errors are tracked in Prometheus:

```python
provider_errors_total.labels(error_type=e.code).inc()
jobs_failed_total.labels(
    tool_type=option.tool_type,
    model_key=option.model_key,
    error_code=e.code
).inc()
```

## Testing Strategy

### Test Pyramid

```
        /\
       /E2E\          (Integration tests - few)
      /------\
     /  API   \       (API tests - moderate)
    /----------\
   /   Unit     \     (Unit tests - many)
  /--------------\
```

### Test Categories

1. **Unit Tests**: Pure functions (e.g., `next_interval_ms()`, URL rewriting)
2. **API Tests**: HTTP endpoints with mocked dependencies
3. **Integration Tests**: Full flow with test database

### Key Test Files

- `test_api_messages.py`: Message creation generates ≥2 options
- `test_api_generate.py`: Idempotency enforcement
- `test_poller.py`: Exponential backoff, state transitions
- `test_presign_localstack.py`: URL rewriting, presigned URLs

### Fixtures

- `jobset_completed.json`: Mock successful provider response
- `jobset_failed.json`: Mock failed provider response

### Running Tests

```bash
# All tests
make test

# Specific test
pytest tests/test_api_messages.py::test_create_message_generates_options -v

# With coverage
pytest tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

## Security Considerations

### Current Implementation (Development)

- **Authentication**: Stub (always returns demo user)
- **CORS**: Allows all origins
- **S3**: Public bucket via LocalStack

### Production Requirements

1. **Authentication**: Implement JWT tokens with proper validation
2. **Authorization**: Role-based access control (RBAC)
3. **CORS**: Whitelist specific frontend domains
4. **S3**: Private buckets with signed URLs
5. **Rate Limiting**: Per-user API rate limits
6. **Input Validation**: Already handled by Pydantic
7. **SQL Injection**: Protected by SQLAlchemy ORM
8. **HTTPS**: Reverse proxy (nginx) with TLS termination

## Performance Optimization

### Database

- **Connection Pooling**: 20 connections, 10 overflow
- **Async I/O**: AsyncPG for non-blocking database calls
- **Index Coverage**: All frequent queries have indexes
- **Keyset Pagination**: No OFFSET (inefficient for large tables)

### Caching (Not Yet Implemented)

Future improvements:
- Redis cache for model catalog
- Redis cache for frequently accessed chats
- ETags for HTTP caching

### Celery

- **Prefetch Multiplier**: 1 (prevents worker starvation)
- **Acks Late**: True (requeue on worker crash)
- **Concurrency**: 4 workers per container

## Monitoring & Observability

### Metrics (Prometheus)

- Job lifecycle counters
- Provider API call counters
- Queue depth gauge
- Error counters by type

### Logs (Structlog)

- Structured JSON logs
- Trace IDs for request correlation
- Log levels: DEBUG, INFO, WARNING, ERROR

### Health Checks

- `/healthz`: Basic liveness
- `/readyz`: Readiness (could check DB/Redis)
- `/metrics`: Prometheus metrics

## Future Enhancements

1. **Distributed Tracing**: OpenTelemetry for request tracing
2. **GraphQL API**: Alternative to REST for complex queries
3. **Webhook Notifications**: Alternative to polling
4. **Priority Queue**: Premium users get faster processing
5. **Multi-region**: Deploy workers in multiple regions
6. **Advanced Caching**: Redis cache for hot paths
7. **Rate Limiting**: Per-user API throttling
8. **Admin Panel**: Job management UI

---

**Last Updated**: 2025-10-18

