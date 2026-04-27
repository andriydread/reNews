from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.run_worker import worker_run
from app.web.views import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    """
    scheduler = AsyncIOScheduler()
    # Schedule the worker to run at regular intervals
    scheduler.add_job(
        worker_run,
        "interval",
        minutes=settings.WORKER_INTERVAL_MINUTES,
        id="rss_worker_job",
    )
    # Trigger initial run on startup to ensure we have fresh data
    scheduler.add_job(worker_run, id="startup_sync")

    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered technical news aggregator",
    lifespan=lifespan,
    # Hide docs in production for security
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
)

# Rate limiting configuration
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Please try again later."
        },
    )


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(api_router, prefix="/api")
app.include_router(web_router)


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc)}
