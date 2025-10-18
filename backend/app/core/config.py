"""Application configuration using pydantic-settings."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DB_DSN: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/app",
        description="Database connection string",
    )

    # Redis
    REDIS_URL: str = Field(default="redis://redis:6379/0", description="Redis URL")

    # Higgsfield API
    HIGGSFIELD_API_KEY: str = Field(default="", description="Higgsfield API key")
    HIGGSFIELD_SECRET: str = Field(default="", description="Higgsfield secret")
    HIGGSFIELD_BASE: str = Field(
        default="https://platform.higgsfield.ai", description="Higgsfield base URL"
    )

    # Application
    APP_DEBUG: bool = Field(default=False, description="Debug mode")
    POLL_MIN_INTERVAL_MS: int = Field(
        default=1000, description="Minimum polling interval in milliseconds"
    )
    POLL_MAX_INTERVAL_MS: int = Field(
        default=30000, description="Maximum polling interval in milliseconds"
    )
    POLL_JITTER: float = Field(default=0.2, description="Polling jitter factor")
    T2I_TIMEOUT_S: int = Field(default=180, description="Text-to-image timeout in seconds")
    I2V_TIMEOUT_S: int = Field(default=1200, description="Image-to-video timeout in seconds")
    T2V_TIMEOUT_S: int = Field(default=1200, description="Text-to-video timeout in seconds")

    # S3 / LocalStack
    S3_BUCKET: str = Field(default="media", description="S3 bucket name")
    S3_REGION: str = Field(default="us-east-1", description="S3 region")
    S3_USE_PATH_STYLE: bool = Field(default=True, description="Use path-style S3 URLs")
    S3_ENDPOINT_INTERNAL: str = Field(
        default="http://localstack:4566", description="S3 endpoint for backend/worker"
    )
    S3_PUBLIC_ENDPOINT: str = Field(
        default="http://localhost:4566", description="S3 endpoint for browser"
    )
    AWS_ACCESS_KEY_ID: str = Field(default="test", description="AWS access key")
    AWS_SECRET_ACCESS_KEY: str = Field(default="test", description="AWS secret key")

    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://redis:6379/0", description="Celery broker")
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://redis:6379/0", description="Celery result backend"
    )


# Global settings instance
settings = Settings()

