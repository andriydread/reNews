import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import jwt
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import FeedCreate, FeedResponse, PaginatedArticlesResponse
from app.core.database import get_db
from app.models.models import Article, ArticleAnalysis, ArticleCategory, Feed
from run_worker import worker_run


# Scheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI"""

    scheduler = AsyncIOScheduler()
    # Run worker every 30 minutes
    scheduler.add_job(worker_run, "interval", minutes=30)
    # Run worker at startup
    scheduler.add_job(worker_run)

    scheduler.start()
    print("Scheduler Started")

    yield

    scheduler.shutdown()
    print("Scheduler stopprd")


ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

app = FastAPI(
    title="reNews API",
    description="AI-powered technical news aggregator",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


load_dotenv()


SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Expires in 30 minutes


def create_access_token(data: dict):
    """Generates a JWT token"""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_admin(request: Request):
    """Dependency to protect API routes (Throws 401 if unauthorized)"""

    token = request.cookies.get("admin_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != os.getenv("ADMIN_USER"):
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload.get("sub")


@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    """Serves login page"""

    return templates.TemplateResponse(request=request, name="login.html")


@app.post("/api/auth/login")
async def login(
    response: Response, username: str = Form(...), password: str = Form(...)
):
    """Validates credentials and sets an HttpOnly cookie"""

    real_user = str(os.getenv("ADMIN_USER"))
    real_pass = str(os.getenv("ADMIN_PASS"))

    if not secrets.compare_digest(username, real_user) or not secrets.compare_digest(
        password, real_pass
    ):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": username})

    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=IS_PRODUCTION,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"message": "Login successful"}


@app.post("/api/auth/logout")
async def logout(response: Response):
    """Clears the authentication cookie"""

    response.delete_cookie("admin_access_token")
    return {"message": "Logged out"}


@app.get("/api/articles", response_model=PaginatedArticlesResponse)
async def get_articles(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: ArticleCategory | None = Query(None, description="Filter by AI category"),
    min_score: int | None = Query(None, ge=1, le=10, description="Minimum AI score"),
    session: AsyncSession = Depends(get_db),
):
    """Fetch a paginated list of articles"""

    query = select(Article).options(selectinload(Article.analysis))

    # County all articles for pagination
    count_query = select(func.count()).select_from(Article)

    # Filters
    if category or min_score is not None:
        query = query.join(Article.analysis)
        count_query = count_query.join(Article.analysis)

        if category:
            query = query.filter(ArticleAnalysis.category == category)
            count_query = count_query.filter(ArticleAnalysis.category == category)
        if min_score is not None:
            query = query.filter(ArticleAnalysis.score >= min_score)
            count_query = count_query.filter(ArticleAnalysis.score >= min_score)

    # Newest article first
    query = query.order_by(Article.published_at.desc().nulls_last())

    # Pagination
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    total_result = await session.execute(count_query)
    total_items = total_result.scalar_one()

    articles_result = await session.execute(query)
    articles = articles_result.scalars().all()

    return {"total": total_items, "page": page, "size": size, "items": articles}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    """Serves the main HTML news dashboard"""

    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Serves the admin panel. Redirects to /login if not authenticated."""

    token = request.cookies.get("admin_access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=302)

    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(request=request, name="admin.html")


@app.get("/api/feeds", response_model=list[FeedResponse])
async def get_feeds(session: AsyncSession = Depends(get_db)):
    """Returns a list of all tracked RSS feeds"""

    result = await session.execute(select(Feed))
    return result.scalars().all()


@app.post("/api/feeds", response_model=FeedResponse)
async def add_feed(
    feed: FeedCreate,
    session: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Adds a new RSS feed to the database. Protected by verify_admin"""

    new_feed = Feed(title=feed.title, url=feed.url)
    session.add(new_feed)
    try:
        await session.commit()
        await session.refresh(new_feed)
        return new_feed
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Feed URL already exists.")


@app.delete("/api/feeds/{feed_id}")
async def delete_feed(
    feed_id: int,
    session: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Deletes a feed. Protected by verify_admin"""

    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    await session.delete(feed)
    await session.commit()

    return {"message": "Feed and all related articles deleted successfully"}
