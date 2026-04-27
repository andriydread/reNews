import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models
    All models inherit from this to be tracked by SQLAlchemy
    """

    pass


class ArticleCategory(str, enum.Enum):
    """
    Categories used by Gemini to classify news
    """

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
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(
        String(1000), unique=True, nullable=False, index=True
    )

    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    articles: Mapped[List["Article"]] = relationship(
        back_populates="feed",
        cascade="all, delete-orphan",  # If we delete a feed, delete its articles too
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Feed(title='{self.title[:30]}')>"


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    link: Mapped[str] = mapped_column(
        String(1000), unique=True, nullable=False, index=True
    )

    # Connection to the Feed this article belongs to
    feed_id: Mapped[int] = mapped_column(
        ForeignKey("feeds.id", ondelete="CASCADE"), index=True
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    is_saved: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    # 1 (Like), -1 (Dislike), 0 (None)
    user_vote: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    feed: Mapped["Feed"] = relationship(back_populates="articles")

    analysis: Mapped[Optional["ArticleAnalysis"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_articles_published_at_desc", published_at.desc().nulls_last()),
    )

    def __repr__(self) -> str:
        return f"<Article(title='{self.title[:30]}')>"


class ArticleAnalysis(Base):
    __tablename__ = "article_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)

    article_id: Mapped[int] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), unique=True, index=True
    )

    # Short text summary of the article
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ArticleCategory] = mapped_column(nullable=False, index=True)

    language: Mapped[str] = mapped_column(String(50))
    model_used: Mapped[str] = mapped_column(String(100))
    ai_processed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    article: Mapped["Article"] = relationship(back_populates="analysis")

    def __repr__(self) -> str:
        return f"<ArticleAnalysis(category='{self.category}')>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<RefreshToken(username='{self.username}', expires_at='{self.expires_at}')>"
