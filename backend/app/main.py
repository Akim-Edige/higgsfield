"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import attachments, chats, health, messages, options
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.infra.db import engine

from app.api.higgsfield import text2image, text2video, misc, image2video, generate

# Configure logging
configure_logging(debug=settings.APP_DEBUG)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("starting_application", debug=settings.APP_DEBUG)
    yield
    logger.info("shutting_down_application")
    # Close connections
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Higgsfield Backend API",
    description="Production chat-based assistant with Higgsfield generation integration",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chats.router)
app.include_router(messages.router)
app.include_router(options.router)
app.include_router(attachments.router)
app.include_router(text2image.router)
app.include_router(text2video.router)
app.include_router(image2video.router)
app.include_router(misc.router)
app.include_router(generate.router)  # Универсальный эндпоинт генерации


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Higgsfield API",
        "version": "0.1.0",
        "docs": "/docs",
    }
