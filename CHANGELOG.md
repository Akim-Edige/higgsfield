# Changelog

All notable changes to the Higgsfield Backend API will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-18

### Added
- Initial production-ready implementation
- FastAPI backend with async SQLAlchemy 2.x
- Chat and message management with keyset pagination
- AI-powered generation option recommendation system
- Idempotent job creation with header validation
- Background worker with Celery for async job processing
- Exponential backoff polling with jitter for provider API
- Higgsfield provider adapter with error classification
- LocalStack S3 integration for development
- Presigned URL generation with internal/public endpoint rewriting
- Server-Sent Events (SSE) for real-time updates
- Prometheus metrics for monitoring
- Structured JSON logging with structlog
- Comprehensive test suite
- Docker Compose setup for local development
- Alembic migrations for database schema
- Health check and readiness endpoints
- Complete API documentation with OpenAPI/Swagger
- Model catalog with T2I, T2V, I2V, and Speak models
- Prompt enhancement for different generation types
- Rate limit handling with automatic retry
- Job timeout management per tool type
- CORS middleware for frontend integration

### Models Supported
- **Text-to-Image**: nano_banana, seedream_4
- **Text-to-Video**: kling_21_master, minimax_hailuo_02, seedance_1_lite
- **Image-to-Video**: kling_25_turbo, wan_25_fast, veo3
- **Speak**: veo3_speak

### Infrastructure
- PostgreSQL for primary data storage
- Redis for Celery broker and SSE pub/sub
- LocalStack for S3 emulation in development
- Celery for distributed task processing
- Alembic for database migrations

### Developer Experience
- Makefile with common commands
- Comprehensive README with examples
- Quick start guide
- GitHub Actions CI/CD workflow
- Code formatting with Black
- Linting with Ruff
- Type checking with MyPy
- Test coverage reporting

## [Unreleased]

### Planned
- Frontend authentication (JWT/OAuth2)
- Advanced keyset pagination implementation
- Credit/billing system implementation
- Redis-based SSE broker for horizontal scaling
- Attachment validation and virus scanning
- Webhook notifications for job completion
- API rate limiting middleware
- Advanced metrics and alerting
- Distributed tracing with OpenTelemetry
- GraphQL API alongside REST
- Admin panel for job management
- Multi-region support
- Advanced caching strategies
- Batch job processing
- Priority queue for premium users

