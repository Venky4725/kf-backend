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

# =========================
# ✅ HARD FIX FOR CORS
# =========================

origins = [
    "https://kf-frontend-rho.vercel.app",  # production frontend
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

logger.info(f"🌍 Allowed CORS origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ROUTES
# =========================

@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"422 Unprocessable Entity: {exc.errors()}")
    logger.error(f"Body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(await request.body())},
    )

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