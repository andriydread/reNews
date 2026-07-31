from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models.models import ArticleCategory


class AnalysisResponse(BaseModel):
    summary: str
    category: ArticleCategory
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
    # Bounds mirror the DB columns (String(500)/String(1000)) so an oversize
    # value is a 422, not a database error surfaced as a 500.
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @field_validator("url")
    @classmethod
    def url_fits_db_column(cls, value: HttpUrl) -> HttpUrl:
        if len(str(value)) > 1000:
            raise ValueError("url must be at most 1000 characters")
        return value


class FeedResponse(BaseModel):
    id: int
    title: str
    url: str

    # Pydantic setting to allow mapping from SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True)
