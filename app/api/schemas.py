from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.models import ArticleCategory


class AnalysisResponse(BaseModel):
    summary: str
    category: ArticleCategory
    score: int
    language: str

    # Pydantic setting to allow mapping from SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True)


class ArticleResponse(BaseModel):
    id: int
    title: str
    link: str
    published_at: Optional[datetime]
    analysis: Optional[AnalysisResponse]

    # Pydantic setting to allow mapping from SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True)


class PaginatedArticlesResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[ArticleResponse]


class FeedCreate(BaseModel):
    title: str
    url: str


class FeedResponse(BaseModel):
    id: int
    title: str
    url: str

    # Pydantic setting to allow mapping from SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True)
