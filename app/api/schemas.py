from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.models import ArticleCategory


class AnalysisResponse(BaseModel):
    """Schema for the AI Analysis data"""

    summary: str
    category: ArticleCategory
    score: int
    language: str

    model_config = ConfigDict(from_attributes=True)


class ArticleResponse(BaseModel):
    """Schema for the Article, including its nested AI Analysis"""

    id: int
    title: str
    link: str
    published_at: Optional[datetime]

    analysis: Optional[AnalysisResponse]
    model_config = ConfigDict(from_attributes=True)


class PaginatedArticlesResponse(BaseModel):
    """Schema for returning a paginated list of articles"""

    total: int
    page: int
    size: int
    items: list[ArticleResponse]


class FeedCreate(BaseModel):
    """Schema for creating feeds"""

    title: str
    url: str


class FeedResponse(BaseModel):
    """Schema for returning list of feeds"""

    id: int
    title: str
    url: str
    model_config = ConfigDict(from_attributes=True)
