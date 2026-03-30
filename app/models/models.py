import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """All SQLAlchemy models inherit from this Base class."""

    pass


class ArticleCategory(str, enum.Enum):
    """Categories for AI classification."""

    TECHNOLOGY = "Technology & Innovation"
    AI = "AI & Machine Learning"
    SCIENCE = "Science & Space"

    POLITICS = "Politics & Government"
    BUSINESS = "Business & Economy"
    SOCIETY = "Society & Culture"
    CRIME = "Crime & Justice"

    HEALTH = "Health & Medicine"
    ENVIRONMENT = "Environment & Nature"
    EDUCATION = "Education & Learning"

    ART = "Arts & Entertainment"
    LIFESTYLE = "Lifestyle & Leisure"
    SPORTS = "Sports & Recreation"

    OTHER = "Other"


class Feed(Base):
    """RSS/Atom feed sources"""

    __tablename__ = "feeds"

    # Database Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000), unique=True)

    # Python Relationships
    articles: Mapped[list["Article"]] = relationship(back_populates="feed")


class Article(Base):
    """Raw article fetched from an RSS feed"""

    __tablename__ = "articles"

    # Database Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(1000), unique=True)

    # Foreign Keys
    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Python Relationships
    feed: Mapped["Feed"] = relationship(back_populates="articles")
    analysis: Mapped[Optional["ArticleAnalysis"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class ArticleAnalysis(Base):
    """AI-generated summary and category for a specific article"""

    __tablename__ = "article_analyses"

    # Database Columns
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign Keys
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), unique=True)

    # AI Columns
    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[ArticleCategory]
    score: Mapped[int] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(50))
    model_used: Mapped[str] = mapped_column(String(100))

    # Timestamps
    ai_processed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Python Relationships
    article: Mapped["Article"] = relationship(back_populates="analysis")
