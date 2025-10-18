# 🚀 Quick Start Guide

Get the Higgsfield backend running in **5 minutes**.

## Prerequisites

- Docker & Docker Compose installed
- Higgsfield API credentials ([Get them here](https://platform.higgsfield.ai))

## Step 1: Clone & Configure

```bash
cd /path/to/higgsfield

# Create .env file
cat > .env << 'EOF'
# Higgsfield API (REQUIRED - get from platform.higgsfield.ai)
HIGGSFIELD_API_KEY=your_api_key_here
HIGGSFIELD_SECRET=your_secret_here

# Database
DB_DSN=postgresql+asyncpg://postgres:postgres@postgres:5432/app

# Redis
REDIS_URL=redis://redis:6379/0

# LocalStack S3
S3_BUCKET=media
S3_REGION=us-east-1
S3_ENDPOINT_INTERNAL=http://localstack:4566
S3_PUBLIC_ENDPOINT=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
EOF

# ⚠️ IMPORTANT: Edit .env and add your real Higgsfield credentials!
nano .env  # or use your favorite editor
```

## Step 2: Start Services

```bash
make dev-up
```

This command:
- Starts PostgreSQL, Redis, LocalStack (S3), API, and Worker
- Runs database migrations
- Sets up S3 bucket with CORS

**Wait ~10 seconds for all services to be healthy.**

## Step 3: Verify

```bash
# Check health
curl http://localhost:8000/healthz
# Expected: {"status":"ok"}

# View API documentation
open http://localhost:8000/docs

# Check that LocalStack S3 is ready
aws --endpoint-url http://localhost:4566 s3 ls
# Expected: 2025-10-18 10:00:00 media
```

## Step 4: Test the API

### Create a chat

```bash
curl -X POST http://localhost:8000/chats \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Chat"}'
```

Copy the `id` from the response (we'll use it as `CHAT_ID` below).

### Send a message & get generation options

```bash
CHAT_ID="<paste-chat-id-here>"

curl -X POST "http://localhost:8000/chats/${CHAT_ID}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "cinematic sunset over mountains",
    "attachments": []
  }'
```

You'll receive:
- An assistant message
- Multiple **render_chunks** with buttons
- Each button has an `option_id`

### Start a generation

Copy an `option_id` from the previous response:

```bash
OPTION_ID="<paste-option-id-here>"

curl -X POST "http://localhost:8000/options/${OPTION_ID}/generate" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "job_id": "abcd-1234-5678-..."
}
```

### Poll the job

```bash
JOB_ID="<paste-job-id-here>"

curl "http://localhost:8000/options/jobs/${JOB_ID}"
```

Poll this endpoint every few seconds. Status will progress:
1. `PENDING` → Job queued
2. `RUNNING` → Generating
3. `SUCCEEDED` → Done! Check `result.raw_url`

Example success response:
```json
{
  "job_id": "abcd-1234-...",
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

## Useful Commands

```bash
# View logs
docker compose logs -f api      # API logs
docker compose logs -f worker   # Worker logs

# Stop services
make dev-down

# Restart services
make dev-down && make dev-up

# Run tests
make test

# Format & lint code
make fmt
make lint

# Access database
docker compose exec postgres psql -U postgres -d app

# Check S3 contents
aws --endpoint-url http://localhost:4566 s3 ls s3://media --recursive
```

## Troubleshooting

### Services won't start

```bash
# Check if ports are in use
lsof -i :8000  # API
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :4566  # LocalStack

# Clean up and restart
docker compose down -v
make dev-up
```

### Worker not processing jobs

```bash
# Check worker logs
docker compose logs -f worker

# Restart worker
docker compose restart worker
```

### LocalStack S3 issues

```bash
# Recreate bucket
aws --endpoint-url http://localhost:4566 s3 rb s3://media --force
aws --endpoint-url http://localhost:4566 s3 mb s3://media

# Re-run init script
docker compose exec localstack bash /etc/localstack/init/ready.d/10-setup-s3.sh
```

### "Higgsfield credentials invalid"

Make sure you've set the correct values in `.env`:
- `HIGGSFIELD_API_KEY`
- `HIGGSFIELD_SECRET`

Get them from: https://platform.higgsfield.ai/settings/api

## Next Steps

- Read the full [README.md](./README.md) for architecture details
- Explore the API at http://localhost:8000/docs
- Check metrics at http://localhost:8000/metrics
- Implement frontend integration using SSE at `/sse/{chat_id}`

## Production Deployment

This setup is for **development only**. For production:

1. Use AWS S3 (not LocalStack)
2. Set up proper authentication (JWT/OAuth2)
3. Use managed PostgreSQL (AWS RDS, etc.)
4. Use managed Redis (ElastiCache, etc.)
5. Deploy with Kubernetes or ECS
6. Add monitoring (Prometheus + Grafana)
7. Enable HTTPS with a reverse proxy

See [README.md](./README.md) for production deployment guidance.

---

**Happy Coding! 🎉**

