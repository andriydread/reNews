from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import PaginatedArticlesResponse
from app.core.database import get_db
from app.models.models import Article, ArticleAnalysis, ArticleCategory

router = APIRouter()


@router.get("", response_model=PaginatedArticlesResponse)
async def get_articles(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: ArticleCategory | None = None,
    min_score: int | None = Query(None, ge=1, le=10),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of articles with their AI analysis
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
