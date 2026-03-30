from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import PaginatedArticlesResponse
from app.core.database import get_db
from app.models.models import Article, ArticleAnalysis, ArticleCategory

app = FastAPI(
    title="reNews API",
    description="AI-powered technical news aggregator",
    version="1.0.0",
)

templates = Jinja2Templates(directory="templates")


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
    """Serves the main HTML dashboard when users visit the root URL."""

    return templates.TemplateResponse("index.html", {"request": request})
