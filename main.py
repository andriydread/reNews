import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import (
    Depends,
    FastAPI,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import FeedCreate, FeedResponse, PaginatedArticlesResponse
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Article, ArticleAnalysis, ArticleCategory, Feed
from app.run_worker import worker_run


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
    # Trigger an initial run on startup to ensure we have fresh data
    scheduler.add_job(worker_run, id="startup_sync")

    scheduler.start()

    yield

    scheduler.shutdown()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered technical news aggregator",
    version=settings.VERSION,
    lifespan=lifespan,
    # Hide docs in production for security
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Please try again later."
        },
    )


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Auth logic
def create_access_token(data: dict):
    """Generates a JWT token for admin access"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def verify_admin(request: Request):
    """
    Dependency to protect routes
    Checks for a valid JWT in the 'admin_access_token' cookie
    """
    token = request.cookies.get("admin_access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM]
        )
        if payload.get("sub") != settings.ADMIN_USER:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        return payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )


# ENDPOINTS


@app.get("/health")
async def health_check():
    """Simple health check endpoint for monitoring health status"""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc)}


@app.post("/api/auth/login")
async def login(
    response: Response, username: str = Form(...), password: str = Form(...)
):
    """Authenticates the admin and sets an HttpOnly, Secure cookie"""
    if not secrets.compare_digest(
        username, settings.ADMIN_USER
    ) or not secrets.compare_digest(password, settings.ADMIN_PASS):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(data={"sub": username})

    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=True if settings.ENVIRONMENT == "production" else False,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    return {"message": "Login successful"}


@app.post("/api/auth/logout")
async def logout(response: Response):
    """Clears the admin session cookie"""
    response.delete_cookie("admin_access_token")
    return {"message": "Logged out"}


@app.get("/api/articles", response_model=PaginatedArticlesResponse)
async def get_articles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: ArticleCategory | None = None,
    min_score: int | None = Query(None, ge=1, le=10),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of articles with their AI analysis.
    """
    query = select(Article).options(selectinload(Article.analysis))
    count_query = select(func.count()).select_from(Article)

    if category or min_score is not None:
        query = query.join(Article.analysis)
        count_query = count_query.join(Article.analysis)

        if category:
            query = query.filter(ArticleAnalysis.category == category)
            count_query = count_query.filter(ArticleAnalysis.category == category)
        if min_score is not None:
            query = query.filter(ArticleAnalysis.score >= min_score)
            count_query = count_query.filter(ArticleAnalysis.score >= min_score)

    # Order by publication date (newest first)
    query = query.order_by(Article.published_at.desc().nulls_last())

    # Pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    # Execute queries
    total_result = await session.execute(count_query)
    total_items = total_result.scalar_one()

    articles_result = await session.execute(query)
    articles = articles_result.scalars().all()

    return {"total": total_items, "page": page, "size": size, "items": articles}


@app.get("/api/feeds", response_model=list[FeedResponse])
async def get_feeds(
    session: AsyncSession = Depends(get_db), admin: str = Depends(verify_admin)
):
    """Returns a list of all managed RSS feeds."""
    result = await session.execute(select(Feed).order_by(Feed.title))
    return result.scalars().all()


@app.post("/api/feeds", response_model=FeedResponse)
async def add_feed(
    feed: FeedCreate,
    session: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Adds a new RSS feed source."""
    new_feed = Feed(title=feed.title.strip(), url=feed.url.strip())
    session.add(new_feed)
    try:
        await session.commit()
        await session.refresh(new_feed)
        return new_feed
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A feed with this URL already exists.",
        )


@app.delete("/api/feeds/{feed_id}")
async def delete_feed(
    feed_id: int,
    session: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Removes a feed and all its associated articles."""
    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    await session.delete(feed)
    await session.commit()
    return {"message": "Feed deleted successfully"}


# Frontend routes (to change)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse(name="index.html", context={"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page for admins"""
    return templates.TemplateResponse(name="login.html", context={"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """
    Admin dashboard
    """
    token = request.cookies.get("admin_access_token")
    authenticated = False
    if token:
        try:
            jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
            authenticated = True
        except jwt.PyJWTError:
            pass

    if not authenticated:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(name="admin.html", context={"request": request})
