# Frontend repository link
https://github.com/AlikhanNasa7/Higgsfield-SWE-Hackaton

# Higgsfield Backend API

Production-ready chat-based assistant backend with Higgsfield AI generation integration. Provides a robust API for managing chats, generating media (images/videos) using Claude 3.5 Haiku recommendations, and real-time streaming responses.

## Architecture Overview

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────────────────────┐
│         FastAPI Backend (API)                │
│  ┌──────────────────────────────────────┐  │
│  │  Routes                               │  │
│  │  - /chats (CRUD)                      │  │
│  │  - /messages (Create with AI recs)    │  │
│  │  - /higgsfield/generate (Media gen)   │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│  ┌──────────────▼───────────────────────┐  │
│  │  Services                             │  │
│  │  - Claude Recommender (227 tools)    │  │
│  │  - Response Parser                    │  │
│  │  - S3 Attachments                     │  │
│  └──────────────┬───────────────────────┘  │
│                 │                           │
│  ┌──────────────▼───────────────────────┐  │
│  │  PostgreSQL (Async SQLAlchemy 2.0)   │  │
│  │  - Users, Chats, Messages             │  │
│  │  - Options (AI recommendations)       │  │
│  │  - Attachments                        │  │
│  └──────────────────────────────────────┘  │
└─────────────────┬───────────────────────────┘
                  │
                  │ API Calls
                  ▼
         ┌────────────────────┐
         │  Higgsfield API    │
         │  - Text-to-Image   │
         │  - Image-to-Video  │
         │  - Text-to-Video   │
         └────────────────────┘
```

**Key Components:**
- **FastAPI Backend**: Async REST API with streaming responses
- **Claude 3.5 Haiku**: AI agent generating personalized recommendations (227 dynamic tools)
- **PostgreSQL**: Primary data store with foreign key constraints
- **Higgsfield Integration**: Direct API polling for image/video generation
- **S3 Storage**: File uploads and media storage

## Quick Start

**Prerequisites:**
- Docker & Docker Compose
- Python 3.11+
- Higgsfield API credentials
- Anthropic API key (Claude 3.5 Haiku)

**Setup:**

```bash
# 1. Clone repository
git clone https://github.com/Akim-Edige/higgsfield.git
cd higgsfield

# 2. Configure environment
cd backend
cp .env.example .env
# Edit .env with your credentials:
# - HIGGSFIELD_API_KEY
# - HIGGSFIELD_SECRET
# - ANTHROPIC_API_KEY

# 3. Start services
cd ..
make dev-up
# Starts: postgres, api containers
# Runs: database migrations

# 4. Verify
curl http://localhost:8000/health
open http://localhost:8000/docs
```

**Stop Services:**
```bash
make dev-down
```

## Project Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   └── f91128f49771_v2.py
│   └── env.py
├── app/
│   ├── api/
│   │   ├── higgsfield/
│   │   │   ├── generate.py     # Universal generation endpoint
│   │   │   ├── text2image.py   # Text-to-Image API
│   │   │   ├── image2video.py  # Image-to-Video API
│   │   │   ├── text2video.py   # Text-to-Video API
│   │   │   └── misc.py         # Styles & motions
│   │   └── routes/
│   │       ├── chats.py        # Chat CRUD
│   │       ├── messages.py     # Messages + Claude recommendations
│   │       ├── options.py      # Options CRUD
│   │       ├── attachments.py  # File uploads (S3)
│   │       └── health.py       # Health checks
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── logging.py          # Structured logging
│   │   └── security.py         # Authentication
│   ├── domain/
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── schemas.py          # Pydantic schemas
│   │   └── pagination.py       # Pagination utilities
│   ├── services/
│   │   ├── claude_recommender.py  # Claude 3.5 Haiku agent (227 tools)
│   │   ├── response_parser.py     # Parse AI responses to UI chunks
│   │   ├── chat_service.py        # Chat business logic
│   │   └── attachments.py         # S3 file operations
│   ├── infra/
│   │   ├── db.py               # Async database session
│   │   └── s3.py               # S3 client
│   ├── image_styles.json       # 106 image styles for text2image
│   ├── motions.json            # 121 motion presets for video
│   └── main.py                 # FastAPI application
└── docker-compose.yml          # Docker services
```

## Key Features

### Claude 3.5 Haiku AI Agent

**227 Dynamic Tools:**
- 106 image generation styles (cinematic, anime, photorealistic, etc.)
- 121 video motion presets (camera movements, effects, etc.)

**Capabilities:**
- Multi-round tool calling (up to 10 rounds)
- Automatic prompt enhancement (150-300 words, cinematographer style)
- Context-aware recommendations with explanations
- Style/motion selection with reasoning

### Database Schema

**Core Tables:**
- `users` - User accounts
- `chats` - Conversation threads
- `messages` - Chat messages (user & assistant)
- `options` - AI-generated recommendations with enhanced prompts
- `attachments` - Uploaded files with S3 URLs

**Key Fields in Options:**
- `style_id` - Selected style/motion UUID
- `model_key` - Higgsfield model identifier
- `enhanced_prompt` - AI-improved prompt (150-300 words)
- `reason` - Explanation why this option was recommended
- `result_url` - Generated media URL (saved after generation)

### Generation Workflow

1. **User sends message** → `/chats/{chat_id}/messages`
2. **Claude analyzes** → Selects appropriate tools (styles/motions)
3. **System creates options** → Saves to database with enhanced prompts
4. **User selects option** → `/higgsfield/generate`
5. **Higgsfield generates** → Polls API until completion
6. **Result saved** → `option.result_url` updated automatically

### S3 File Storage

**Supported Operations:**
- Presigned upload URLs (secure client-side uploads)
- Direct downloads via storage URLs
- Image and video attachments
- Automatic metadata extraction (dimensions, duration, etc.)

## API Examples

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

### Create Message with AI Recommendations

```bash
curl -X POST http://localhost:8000/chats/{chat_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "text": "cinematic sunset over mountains"
  }'
```

**Response:**
```json
{
  "message": {
    "id": "msg-uuid",
    "chat_id": "chat-uuid",
    "author_type": "assistant",
    "render_payload": [
      {
        "type": "button",
        "label": "Cinematic Sunset (Text To Image)",
        "option_id": "option-uuid-1",
        "model": "nano-banana"
      },
      {
        "type": "text",
        "text": "Perfect for photorealistic landscapes with dramatic lighting..."
      },
      {
        "type": "button",
        "label": "Dynamic Mountain Video (Text To Video)",
        "option_id": "option-uuid-2",
        "model": "seedance-v1"
      },
      {
        "type": "text",
        "text": "Captures motion and atmosphere for cinematic video..."
      }
    ],
    "created_at": "2025-10-19T10:00:00Z"
  }
}
```

### Generate Media from Option

```bash
curl -X POST http://localhost:8000/higgsfield/generate \
  -H "Content-Type: application/json" \
  -d '{
    "option_id": "option-uuid-1",
    "mode": "text-to-image",
    "aspect_ratio": "16:9",
    "quality": "1080p"
  }'
```

**Response (with polling until complete):**
```json
{
  "url": "https://storage.example.com/outputs/image.jpg",
  "preview_url": "https://storage.example.com/outputs/preview.webp"
}
```

**Note:** The endpoint polls Higgsfield API internally and returns when generation is complete. The result URL is automatically saved to `option.result_url` in the database.

### Upload File (S3 Presigned URL)

```bash
# 1. Request presigned upload URL
curl -X POST http://localhost:8000/attachments/presign \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "input.jpg",
    "content_type": "image/jpeg",
    "size": 1024000
  }'
```

**Response:**
```json
{
  "upload_url": "https://storage.yandexcloud.net/bucket/uploads/uuid/input.jpg?signature=...",
  "download_url": "https://storage.yandexcloud.net/bucket/uploads/uuid/input.jpg",
  "upload_id": "upload-uuid"
}
```

```bash
# 2. Upload file directly to S3
curl -X PUT "{upload_url}" \
  -H "Content-Type: image/jpeg" \
  --data-binary @input.jpg
```

### Get Available Styles and Motions

```bash
# Image styles
curl http://localhost:8000/higgsfield/text2image/styles

# Video motions
curl http://localhost:8000/higgsfield/image2video/motions
```

## Testing

```bash
# Run tests (when test suite is available)
pytest tests/ -v

# Run specific test
pytest tests/test_api_messages.py -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

## Database Migrations

```bash
# Apply migrations
make migrate

# Create new migration
cd backend && docker compose exec -T api alembic revision --autogenerate -m "description"

# Check current version
cd backend && docker compose exec -T api alembic current

# Rollback one version
cd backend && docker compose exec -T api alembic downgrade -1
```

**Migration History:**
- `001_initial_schema` - Initial database schema (users, chats, messages, options, attachments)
- `f91128f49771_v2` - Added foreign key constraints, removed generation_jobs table

## Cloud Storage Configuration

**Yandex Cloud Object Storage (Recommended):**

1. Create bucket at [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Enable public read access (for development/hackathon)
3. Create service account and get static access keys
4. Configure `.env`:

```env
S3_BUCKET=your-bucket-name
S3_REGION=ru-central1
S3_ENDPOINT_INTERNAL=https://storage.yandexcloud.net
S3_PUBLIC_ENDPOINT=https://storage.yandexcloud.net
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
USE_PUBLIC_URLS=true
```

**AWS S3:**

```env
S3_BUCKET=your-bucket-name
S3_REGION=us-east-1
S3_ENDPOINT_INTERNAL=https://s3.amazonaws.com
S3_PUBLIC_ENDPOINT=https://s3.amazonaws.com
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
USE_PUBLIC_URLS=false
```

## Logging

**View Logs:**

```bash
# API logs
docker compose logs -f api

# All services
docker compose logs -f
```

**Structured Logging:**
- Uses `structlog` for JSON-formatted logs
- Request/response logging
- Error tracking with stack traces
- Performance metrics

## Local Development

**Without Docker:**

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Start PostgreSQL
docker compose up -d postgres

# Run migrations
cd backend && alembic upgrade head

# Start API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Code Quality:**

```bash
# Format code (when configured)
black backend/
isort backend/

# Type checking
mypy backend/

# Linting
ruff check backend/
```

## Security Notes

**Current Implementation:**
- Stub authentication (demo user ID)
- CORS enabled for all origins (development)
- No rate limiting

**Production Recommendations:**
- Implement JWT/OAuth2 authentication
- Restrict CORS to specific origins
- Add rate limiting middleware (slowapi, fastapi-limiter)
- Use HTTPS with reverse proxy (nginx/Caddy)
- Enable SQL injection protection (SQLAlchemy ORM provides this)
- Add request validation and sanitization
- Implement API key rotation
- Use secrets manager for credentials (Yandex Lockbox, AWS Secrets Manager)

## Environment Variables

**Required Variables:**

```env
# Higgsfield API
HIGGSFIELD_API_KEY=your_higgsfield_api_key
HIGGSFIELD_SECRET=your_higgsfield_secret

# Claude AI
ANTHROPIC_API_KEY=your_anthropic_api_key

# Database
DB_DSN=postgresql+asyncpg://user:password@postgres:5432/higgsfield

# S3 Storage
S3_BUCKET=your-bucket-name
S3_REGION=ru-central1
S3_ENDPOINT_INTERNAL=https://storage.yandexcloud.net
S3_PUBLIC_ENDPOINT=https://storage.yandexcloud.net
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
USE_PUBLIC_URLS=true
```

**Optional Variables:**

```env
# Server
PORT=8000
WORKERS=1

# Logging
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS=*
```

## Production Deployment

**Infrastructure:**

1. **Database**: Use managed PostgreSQL
   - AWS RDS
   - Google Cloud SQL
   - Yandex Managed Service for PostgreSQL
   - Enable automated backups
   - Configure connection pooling

2. **Storage**: Use cloud object storage
   - AWS S3 with CloudFront CDN
   - Yandex Cloud Object Storage
   - Configure lifecycle policies
   - Enable versioning for critical data

3. **Compute**: Deploy API service
   - Docker container on cloud VMs
   - Kubernetes cluster
   - Yandex Cloud Container Registry
   - Configure auto-scaling

4. **Security**:
   - Enable HTTPS (Let's Encrypt, cloud certificates)
   - Implement JWT authentication
   - Configure firewall rules
   - Use secrets management
   - Enable request rate limiting

5. **Monitoring**:
   - Application logs (structured JSON)
   - Error tracking (Sentry)
   - Performance monitoring
   - Database query performance

6. **CI/CD**:
   - Automated testing on pull requests
   - Docker image building
   - Automated deployment to staging/production
   - Database migration automation

**Example Docker Compose for Production:**

```yaml
version: '3.8'
services:
  api:
    image: registry.example.com/higgsfield-api:latest
    environment:
      - DB_DSN=${DB_DSN}
      - HIGGSFIELD_API_KEY=${HIGGSFIELD_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    ports:
      - "8000:8000"
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Technology Stack

**Backend:**
- FastAPI 0.119.0 - Modern async web framework
- SQLAlchemy 2.0.44 - Async ORM
- Alembic 1.13.1 - Database migrations
- Pydantic 2.12.3 - Data validation
- asyncpg 0.29.0 - Async PostgreSQL driver

**AI Integration:**
- anthropic 0.71.0 - Claude 3.5 Haiku API client
- 227 dynamic tools (106 styles + 121 motions)

**Infrastructure:**
- PostgreSQL 16 - Primary database
- boto3 1.34.27 - S3 operations
- httpx - Async HTTP client for Higgsfield API

**Development:**
- uvicorn 0.27.0 - ASGI server
- pytest - Testing framework
- Docker & Docker Compose - Containerization

## Resources

- [Higgsfield Platform](https://platform.higgsfield.ai/)
- [Claude API Documentation](https://docs.anthropic.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - See LICENSE file for details.

---

**Authors: Alikhan Nashtay, Adilet Shildebayev, Edige Akimali, Dinmukhamed Albek**


Built for the Higgsfield AI platform
