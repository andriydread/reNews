from datetime import datetime, timedelta, timezone

import pytest

from app.models.models import Article, ArticleAnalysis, ArticleCategory, Feed


@pytest.fixture
async def seeded(db_session):
    """One feed, 5 articles (newest first by published_at), 3 analyzed."""
    feed = Feed(title="Seed Feed", url="https://seed.test/rss")
    db_session.add(feed)
    await db_session.flush()

    base = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
    articles = []
    for i in range(5):
        article = Article(
            title=f"Article {i}",
            link=f"https://seed.test/article-{i}",
            feed_id=feed.id,
            published_at=base + timedelta(days=i),
        )
        db_session.add(article)
        articles.append(article)
    await db_session.flush()

    categories = [ArticleCategory.AI, ArticleCategory.AI, ArticleCategory.SPORTS]
    for article, category in zip(articles[:3], categories, strict=True):
        db_session.add(
            ArticleAnalysis(
                article_id=article.id,
                summary=f"Summary of {article.title}",
                category=category,
                language="English",
                model_used="test",
            )
        )
    await db_session.commit()
    return articles


async def test_pagination(client, seeded):
    resp = await client.get("/api/articles?page=1&size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert len(data["items"]) == 2

    page3 = (await client.get("/api/articles?page=3&size=2")).json()
    assert len(page3["items"]) == 1


async def test_newest_first_ordering(client, seeded):
    data = (await client.get("/api/articles?page=1&size=5")).json()
    dates = [item["published_at"] for item in data["items"]]
    assert dates == sorted(dates, reverse=True)


async def test_category_filter(client, seeded):
    resp = await client.get(
        "/api/articles", params={"category": ArticleCategory.AI.value}
    )
    data = resp.json()
    assert data["total"] == 2
    assert all(
        item["analysis"]["category"] == ArticleCategory.AI.value
        for item in data["items"]
    )


async def test_unanalyzed_articles_have_null_analysis(client, seeded):
    data = (await client.get("/api/articles?page=1&size=5")).json()
    pending = [item for item in data["items"] if item["analysis"] is None]
    assert len(pending) == 2


async def test_invalid_category_rejected(client, seeded):
    resp = await client.get("/api/articles", params={"category": "Nonsense"})
    assert resp.status_code == 422
