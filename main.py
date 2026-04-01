import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import FeedCreate, FeedResponse, PaginatedArticlesResponse
from app.core.database import get_db
from app.models.models import Article, ArticleAnalysis, ArticleCategory, Feed

app = FastAPI(
    title="reNews API",
    description="AI-powered technical news aggregator",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

security = HTTPBasic()

load_dotenv()


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Basic admin login and password. Set it inside .env file"""

    typed_user = credentials.username if credentials.username else ""
    typed_pass = credentials.password if credentials.password else ""

    real_user = str(os.getenv("ADMIN_USER"))
    real_pass = str(os.getenv("ADMIN_PASS"))

    if not real_user or not real_pass:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: Admin credentials not set in .env",
        )

    correct_username = secrets.compare_digest(typed_user, real_user)
    correct_password = secrets.compare_digest(typed_pass, real_pass)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


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
async def admin_dashboard(request: Request, username: str = Depends(verify_admin)):
    """Serves the admin panel to add feeds. Protected by verify_admin"""

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
    username: str = Depends(verify_admin),
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
    username: str = Depends(verify_admin),
):
    """Deletes a feed. Protected by verify_admin"""
    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    await session.delete(feed)
    await session.commit()

    return {"message": "Feed and all related articles deleted successfully"}
