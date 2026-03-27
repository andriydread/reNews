import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ArticleCategory(str, enum.Enum):
    AI = "AI & Machine Learning"
    DEV = "Software Engineering"
    SEC = "Cybersecurity"
    CLOUD = "DevOps & Cloud"
    HARDWARE = "Hardware & Electronics"
    BUSINESS = "Business & Startups"
    SCIENCE = "Science & Research"
    OTHER = "Other"


class Feed(Base):
    __tablename__ = "feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    title: Mapped[str] = mapped_column(String(500))

    articles: Mapped[list["Article"]] = relationship(back_populates="feed")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(1000), unique=True)
    content: Mapped[Optional[str]] = mapped_column(Text)

    is_ai_processed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    feed_id: Mapped[int] = mapped_column(ForeignKey("feeds.id"))
    feed: Mapped["Feed"] = relationship(back_populates="articles")

    analysis: Mapped[Optional["ArticleAnalysis"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class ArticleAnalysis(Base):
    __tablename__ = "article_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)

    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), unique=True)

    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[ArticleCategory]
    score: Mapped[int] = mapped_column(Integer)

    language: Mapped[str] = mapped_column(String(50))
    model_used: Mapped[str] = mapped_column(String(100))

    article: Mapped["Article"] = relationship(back_populates="analysis")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
