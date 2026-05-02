from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.logger import configure_logging, get_logger
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
)

import app.models  # noqa: F401


configure_logging()
logger = get_logger(__name__)


def run_startup_checks() -> None:
    if settings.JWT_SECRET == "change-me":
        logger.warning(
            "JWT_SECRET is using the default value. "
            "Update it before production deployment."
        )

    if settings.ADMIN_PASSWORD == "admin123":
        logger.warning(
            "ADMIN_PASSWORD is using the default value. "
            "Update it before production deployment."
        )

    logger.info(
        "Authentication: Using database-based password hashing "
        "from public.profiles table."
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting Knowledge Factory API")
    run_startup_checks()

    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=connection)

    logger.info("Database connectivity verified and metadata synchronized")

    yield

    logger.info("Shutting down Knowledge Factory API")


app = FastAPI(
    title="Knowledge Factory API",
    version="1.0.0",
    description=(
        "Knowledge Factory backend for intern, batch, "
        "task, and evaluation management."
    ),
    lifespan=lifespan,
)


def _split_origins(value: str) -> list[str]:
    return [
        origin.strip()
        for origin in value.replace(",", " ").split()
        if origin.strip()
    ]


origins = [
    settings.FRONTEND_URL,
    "https://kf-frontend-rho.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    *_split_origins(settings.CORS_ORIGINS),
]

origins = list(
    dict.fromkeys(origin for origin in origins if origin)
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Health"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "env": settings.ENVIRONMENT,
    }


for router in (
    auth.router,
    profiles.router,
    batches.router,
    tasks.router,
    attendance.router,
    submissions.router,
    evaluations.router,
    notifications.router,
):
    app.include_router(router, prefix="/api")