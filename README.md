# Higgsfield Backend API

Production-ready chat-based assistant backend with Higgsfield generation integration. This system provides a robust API for managing chats, generating media (images/videos) via Higgsfield's models, and handling async job polling with proper idempotency and reliability guarantees.

## 🏗️ Architecture

```
┌─────────────┐
│   Frontend  │
│   (Browser) │
└──────┬──────┘
       │ HTTP/SSE
       ▼
┌─────────────────────────────────────────────┐
│            FastAPI Backend (API)             │
│  ┌────────────┐  ┌──────────────┐          │
│  │   Routes   │  │   Services   │          │
│  │  (REST)    │──│ (Business    │          │
│  │            │  │  Logic)      │          │
│  └────────────┘  └──────┬───────┘          │
│                         │                   │
│  ┌─────────────────────┴────────────────┐  │
│  │    PostgreSQL (Async SQLAlchemy)     │  │
│  └──────────────────────────────────────┘  │
└───────────────┬─────────────────────────────┘
                │
                │ Celery Tasks
                ▼
┌───────────────────────────────────────────┐
│        Celery Worker (Background)         │
│  ┌──────────────────────────────────┐    │
│  │     Polling Task (Exponential    │    │
│  │     Backoff + Jitter)            │    │
│  └──────────┬───────────────────────┘    │
│             │                             │
│             ▼                             │
│    ┌────────────────────┐                │
│    │  Higgsfield API    │                │
│    │  (Provider)        │                │
│    └────────────────────┘                │
└───────────────────────────────────────────┘
       │
       │ S3 Operations
       ▼
┌────────────────────────┐
│  LocalStack (S3)       │
│  - Development S3      │
│  - CORS configured     │
│  - Public URL rewrite  │
└────────────────────────┘

Supporting Services:
- Redis (Celery broker + SSE pub/sub)
- PostgreSQL (Primary data store)
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Higgsfield API credentials

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Higgsfield credentials
# HIGGSFIELD_API_KEY=your_key_here
# HIGGSFIELD_SECRET=your_secret_here
```

### 2. Start Services

```bash
# Start all services (postgres, redis, localstack, api, worker)
make dev-up

# This will:
# - Start Docker Compose services
# - Run database migrations
# - Initialize LocalStack S3 bucket with CORS
```

### 3. Verify

```bash
# Check health
curl http://localhost:8000/healthz

# View API docs
open http://localhost:8000/docs

# Check metrics
curl http://localhost:8000/metrics
```

### 4. Stop Services

```bash
make dev-down
```

## 📦 Project Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/
│   │   └── 001_initial_schema.py
│   └── env.py
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── chats.py        # Chat CRUD
│   │   │   ├── messages.py     # Messages + option generation
│   │   │   ├── options.py      # List options
│   │   │   ├── jobs.py         # Job creation + polling
│   │   │   ├── attachments.py  # S3 presigned URLs
│   │   │   ├── sse.py          # Server-Sent Events
│   │   │   └── health.py       # Health checks + metrics
│   │   ├── deps.py             # FastAPI dependencies
│   │   └── errors.py           # Error handling
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── logging.py          # Structured logging (structlog)
│   │   └── security.py         # Auth stubs
│   ├── domain/
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── schemas.py          # Pydantic schemas
│   │   ├── states.py           # Enums (JobStatus, etc.)
│   │   └── pagination.py       # Keyset pagination utils
│   ├── services/
│   │   ├── chat_service.py     # Chat operations
│   │   ├── recommender.py      # Option recommendation
│   │   ├── prompt_enhance.py   # Prompt enhancement
│   │   ├── model_catalog.py    # Model metadata
│   │   ├── orchestrator.py     # Job lifecycle
│   │   ├── provider_higgsfield.py  # Provider adapter
│   │   ├── attachments.py      # S3 presigned URL generation
│   │   └── sse_broker.py       # In-memory SSE pub/sub
│   ├── workers/
│   │   ├── celery_app.py       # Celery configuration
│   │   └── tasks.py            # Background tasks (polling)
│   ├── infra/
│   │   ├── db.py               # Async DB session
│   │   ├── redis.py            # Redis client
│   │   ├── s3.py               # S3 client + URL rewrite
│   │   ├── metrics.py          # Prometheus metrics
│   │   └── idempotency.py      # Idempotency key validation
│   └── main.py                 # FastAPI app
tests/
├── conftest.py
├── test_api_messages.py
├── test_api_generate.py
├── test_poller.py
├── test_presign_localstack.py
└── fixtures/
    ├── jobset_completed.json
    └── jobset_failed.json
```

## 🔑 Key Features

### 1. **Idempotent Job Creation**

Generation requests require an `Idempotency-Key` header. Repeated requests with the same key return the same job ID:

```bash
curl -X POST http://localhost:8000/options/{option_id}/generate \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json"
```

### 2. **Polling with Exponential Backoff**

The worker polls Higgsfield's API with exponential backoff + jitter to avoid thundering herd:

- Min interval: 1s
- Max interval: 30s
- Jitter: ±20%

### 3. **LocalStack S3 for Development**

S3 operations use LocalStack in development:

- **Internal endpoint** (`http://localstack:4566`): Used by backend/worker
- **Public endpoint** (`http://localhost:4566`): Returned to browser in presigned URLs

URLs are automatically rewritten via `rewrite_to_public()`.

### 4. **Server-Sent Events (SSE)**

Real-time updates pushed to frontend via SSE:

```bash
curl -N http://localhost:8000/sse/{chat_id}
```

Events:
- `message.created`: New message
- `option.created`: New option
- `job.updated`: Job status change

### 5. **Prometheus Metrics**

Exposed at `/metrics`:

- `jobs_created_total`: Counter by tool_type, model_key
- `jobs_succeeded_total`: Success counter
- `jobs_failed_total`: Failure counter with error_code
- `provider_polls_total`: Provider API call counter
- `queue_depth`: Pending/running jobs gauge

## 🛠️ API Examples

### Create Chat

```bash
curl -X POST http://localhost:8000/chats \
  -H "Content-Type: application/json" \
  -d '{"title": "My Chat"}'
```

Response:
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "title": "My Chat",
  "message_count": 0,
  "last_message_at": null,
  "created_at": "2025-10-18T10:00:00Z"
}
```

### Create Message (Generate Options)

```bash
curl -X POST http://localhost:8000/chats/{chat_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "text": "cinematic sunset over mountains",
    "attachments": []
  }'
```

Response:
```json
{
  "message": {
    "id": "...",
    "chat_id": "...",
    "author_type": "assistant",
    "content_text": null,
    "render_payload": [...],
    "created_at": "2025-10-18T10:00:01Z"
  },
  "render_chunks": [
    {
      "type": "text",
      "text": "Fast & low-cost photorealistic image generation"
    },
    {
      "type": "button",
      "label": "Generate (Text To Image)",
      "option_id": "12345678-1234-1234-1234-123456789012"
    },
    {
      "type": "text",
      "text": "Cinematic video with smooth motion, higher cost & latency"
    },
    {
      "type": "button",
      "label": "Generate (Text To Video)",
      "option_id": "87654321-4321-4321-4321-210987654321"
    }
  ]
}
```

### Generate from Option

```bash
curl -X POST http://localhost:8000/options/{option_id}/generate \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json"
```

Response (202 Accepted):
```json
{
  "job_id": "abcd1234-5678-90ef-ghij-klmnopqrstuv"
}
```

### Poll Job Status

```bash
curl http://localhost:8000/options/jobs/{job_id}
```

Response (Running):
```json
{
  "job_id": "abcd1234-5678-90ef-ghij-klmnopqrstuv",
  "status": "RUNNING",
  "result": null,
  "error": null,
  "retry_after_seconds": 4
}
```

Response (Succeeded):
```json
{
  "job_id": "abcd1234-5678-90ef-ghij-klmnopqrstuv",
  "status": "SUCCEEDED",
  "result": {
    "min_url": "http://localhost:4566/media/outputs/min.webp",
    "raw_url": "http://localhost:4566/media/outputs/raw.jpg",
    "mime": "image/jpeg",
    "size_bytes": 1234567,
    "thumbnails": []
  },
  "error": null,
  "retry_after_seconds": 10
}
```

### Upload Attachment (Presigned URL)

```bash
# 1. Get presigned URL
curl -X POST http://localhost:8000/attachments/presign \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "photo.jpg",
    "content_type": "image/jpeg",
    "size": 1024000
  }'
```

Response:
```json
{
  "upload_url": "http://localhost:4566/media/uploads/{uuid}/photo.jpg?...",
  "download_url": "http://localhost:4566/media/uploads/{uuid}/photo.jpg",
  "upload_id": "0f8f1234-5678-90ab-cdef-1234567890ab"
}
```

```bash
# 2. Upload file using presigned URL
curl -X PUT "{upload_url}" \
  -H "Content-Type: image/jpeg" \
  --data-binary @photo.jpg
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_api_messages.py -v

# Run with coverage
pytest tests/ -v --cov=backend --cov-report=term-missing
```

## 🗄️ Database Migrations

```bash
# Run migrations
make migrate

# Create new migration
make migrate-create MSG="add_new_column"

# Rollback (manual)
cd backend && alembic downgrade -1
```

## 🐳 LocalStack S3 Management

```bash
# List buckets
aws --endpoint-url http://localhost:4566 s3 ls

# List objects in media bucket
aws --endpoint-url http://localhost:4566 s3 ls s3://media --recursive

# Download file
aws --endpoint-url http://localhost:4566 s3 cp s3://media/uploads/{uuid}/file.jpg ./file.jpg
```

## ☁️ Yandex Cloud Object Storage (Production)

For hackathon or production deployment, you can use **Yandex Cloud Object Storage** instead of LocalStack.

### Quick Setup

1. **Create bucket** at [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. **Enable public access** for read (hackathon mode)
3. **Get static access keys** from service account
4. **Update `.env`**:

```env
# Yandex Cloud configuration
S3_BUCKET=your-bucket-name
S3_REGION=ru-central1
S3_USE_PATH_STYLE=false
S3_ENDPOINT_INTERNAL=https://storage.yandexcloud.net
S3_PUBLIC_ENDPOINT=https://storage.yandexcloud.net
AWS_ACCESS_KEY_ID=your_yandex_access_key_id
AWS_SECRET_ACCESS_KEY=your_yandex_secret_key

# Use public URLs (simplified for hackathon)
USE_PUBLIC_URLS=true
```

### Public URLs Mode

When `USE_PUBLIC_URLS=true`:
- **Upload**: Still uses presigned URLs (required for security)
- **Download**: Returns permanent public URLs like `https://{bucket}.storage.yandexcloud.net/{key}`
- **No expiration**: Links work forever
- **Requires**: Public read access on bucket

This simplifies development and hackathons, but for production consider using `USE_PUBLIC_URLS=false` for private buckets with temporary presigned URLs.

📖 **Full guide**: See [YANDEX_CLOUD_SETUP.md](YANDEX_CLOUD_SETUP.md) for detailed instructions.

### Example Configuration Files

- `env.yandex.example` - Environment variables template for Yandex Cloud
- `YANDEX_CLOUD_SETUP.md` - Complete setup guide with troubleshooting

## 📊 Monitoring

### Prometheus Metrics

```bash
curl http://localhost:8000/metrics
```

Example metrics:
```
# HELP jobs_created_total Total number of generation jobs created
# TYPE jobs_created_total counter
jobs_created_total{tool_type="text_to_image",model_key="nano_banana"} 42.0

# HELP jobs_succeeded_total Total number of generation jobs succeeded
# TYPE jobs_succeeded_total counter
jobs_succeeded_total{tool_type="text_to_image",model_key="nano_banana"} 40.0

# HELP queue_depth Current number of pending/running jobs
# TYPE queue_depth gauge
queue_depth 3.0
```

### Logs

Structured JSON logs (via structlog):

```bash
# View API logs
docker compose logs -f api

# View worker logs
docker compose logs -f worker
```

Example log entry:
```json
{
  "event": "job_created",
  "job_id": "abcd1234-...",
  "option_id": "12345678-...",
  "user_id": "00000000-...",
  "tool_type": "text_to_image",
  "model_key": "nano_banana",
  "timeout_at": "2025-10-18T10:03:00Z",
  "timestamp": "2025-10-18T10:00:00Z",
  "level": "info"
}
```

## 🔧 Development

### Code Quality

```bash
# Format code
make fmt

# Lint code
make lint

# Clean cache
make clean
```

### Local Development (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start services
docker compose up -d postgres redis localstack

# Run migrations
cd backend && alembic upgrade head

# Start API
cd backend && uvicorn app.main:app --reload

# Start worker (separate terminal)
cd backend && celery -A app.workers.celery_app worker --loglevel=info
```

## 🔐 Security Notes

- **Authentication**: Currently uses stub authentication (demo user). Implement proper JWT/OAuth2 for production.
- **CORS**: Configured to allow all origins in development. Restrict in production.
- **S3**: LocalStack for development. Use AWS S3 with proper IAM roles in production.
- **Rate Limiting**: Not implemented. Add rate limiting middleware for production.

## 📝 Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `HIGGSFIELD_API_KEY`: Your Higgsfield API key
- `HIGGSFIELD_SECRET`: Your Higgsfield secret
- `DB_DSN`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `S3_BUCKET`: S3 bucket name
- `S3_REGION`: S3 region (e.g., `us-east-1`, `ru-central1`)
- `S3_ENDPOINT_INTERNAL`: S3 endpoint for backend/worker
- `S3_PUBLIC_ENDPOINT`: S3 endpoint for browser
- `AWS_ACCESS_KEY_ID`: AWS/Yandex access key ID
- `AWS_SECRET_ACCESS_KEY`: AWS/Yandex secret access key
- `USE_PUBLIC_URLS`: Use permanent public URLs instead of presigned (default: `true`)

## 🚀 Production Deployment

For production:

1. **Use cloud storage** instead of LocalStack
   - **AWS S3** with CloudFront CDN
   - **Yandex Cloud Object Storage** (see [YANDEX_CLOUD_SETUP.md](YANDEX_CLOUD_SETUP.md))
   - Set `USE_PUBLIC_URLS=false` for private buckets with presigned URLs
2. **Set up proper authentication** (JWT/OAuth2)
3. **Configure CORS** with specific origins
4. **Enable HTTPS** via reverse proxy (nginx/Caddy)
5. **Use managed Redis** (AWS ElastiCache, Redis Cloud, Yandex Managed Service for Redis)
6. **Use managed PostgreSQL** (AWS RDS, Google Cloud SQL, Yandex Managed Service for PostgreSQL)
7. **Set up monitoring** (Prometheus + Grafana)
8. **Configure log aggregation** (ELK, Datadog, CloudWatch, Yandex Cloud Logging)
9. **Add rate limiting** and request throttling
10. **Set up CI/CD** pipeline for automated deployments

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [Higgsfield API Documentation](https://platform.higgsfield.ai/docs)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details.

---

**Built with ❤️ for the Higgsfield platform**
