from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text

from app.core.config import settings
from app.core.logger import configure_logging, get_logger
from app.core.error_handlers import register_error_handlers
from app.db.session import Base, engine
from app.routers import (
    attendance,
    auth,
    batches,
    evaluations,
    notifications,
    profiles,
    submissions,
    tasks,
    roadmaps,
    dashboard,
    weekly_plans,
)

import app.models  # noqa: F401


configure_logging()
logger = get_logger(__name__)


def run_startup_checks() -> None:
    if settings.JWT_SECRET == "change-me":
        logger.warning("JWT_SECRET is default. Change it.")

    if settings.ADMIN_PASSWORD == "admin123":
        logger.warning("ADMIN_PASSWORD is default. Change it.")

    logger.info("Auth system ready.")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("🚀 Starting Knowledge Factory API")

    run_startup_checks()

    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=connection)

    logger.info("✅ DB connected")

    yield

    logger.info("🛑 Shutting down API")


app = FastAPI(
    title="Knowledge Factory API",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure JSON serialization to ensure UUIDs are strings
from fastapi.responses import JSONResponse
from typing import Any
import json

class UUIDJSONResponse(JSONResponse):
    """Custom JSON response that ensures UUIDs are serialized as strings"""
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=str,  # Convert UUIDs and other non-serializable types to strings
        ).encode("utf-8")

# Set as default response class
app.router.default_response_class = UUIDJSONResponse

# =========================
# ERROR HANDLERS
# =========================

register_error_handlers(app)


# =========================
# CORS CONFIGURATION
# =========================

# Build CORS origins list from environment variable + defaults
origins = []

# Add production frontend
origins.append("https://kf-frontend-azure.vercel.app")

# Add local development origins
origins.extend([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
])

# Add custom origins from environment variable (comma-separated)
if settings.CORS_ORIGINS:
    custom_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
    origins.extend(custom_origins)
    logger.info(f"📝 Added custom CORS origins from env: {custom_origins}")

# Remove duplicates while preserving order
origins = list(dict.fromkeys(origins))

# Also ensure we are including all potential frontends in production
if settings.ENVIRONMENT == "production":
    # Make sure production frontend is explicitly included
    if "https://kf-frontend-rho.vercel.app" not in origins:
        origins.append("https://kf-frontend-rho.vercel.app")

logger.info(f"🌍 Allowed CORS origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# =========================
# ROUTES
# =========================

@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}

for router in (
    auth.router,
    profiles.router,
    batches.router,
    tasks.router,
    attendance.router,
    submissions.router,
    evaluations.router,
    notifications.router,
    roadmaps.router,
    dashboard.router,
    weekly_plans.router,
    ):
    app.include_router(router, prefix="/api")