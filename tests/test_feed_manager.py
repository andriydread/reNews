from datetime import datetime
from pathlib import Path

import respx
from httpx import Response
from sqlalchemy import select

from app.models.models import Article, Feed
from app.services.feed_manager import FeedManager

FIXTURE = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_text()
FEED_URL = "https://feeds.test/rss"


@respx.mock
async def test_fetch_feed_data_parses_entries():
    respx.get(FEED_URL).mock(return_value=Response(200, text=FIXTURE))

    articles = await FeedManager().fetch_feed_data(FEED_URL)

    assert articles is not None and len(articles) == 3
    first, second, bare = articles
    assert first["title"] == "First article"  # stripped
    assert first["link"] == "https://feeds.test/first"
    assert isinstance(first["published_date"], datetime)
    assert second["published_date"] > first["published_date"]
    # entry without title/date degrades instead of raising
    assert bare["title"] == "No Title"
    assert bare["published_date"] is None


@respx.mock
async def test_fetch_feed_http_error_returns_none():
    respx.get(FEED_URL).mock(return_value=Response(500))
    assert await FeedManager().fetch_feed_data(FEED_URL) is None


async def test_save_articles_dedupes_on_link(db_session):
    feed = Feed(title="F", url=FEED_URL)
    db_session.add(feed)
    await db_session.flush()

    batch = [
        {"title": "A", "link": "https://feeds.test/a", "published_date": None},
        {"title": "B", "link": "https://feeds.test/b", "published_date": None},
    ]
    fm = FeedManager()

    assert await fm.save_articles_to_db(db_session, feed.id, batch) == 2
    # same batch again: on_conflict_do_nothing on link, nothing new
    assert await fm.save_articles_to_db(db_session, feed.id, batch) == 0

    count = len(
        (await db_session.execute(select(Article).where(Article.feed_id == feed.id)))
        .scalars()
        .all()
    )
    assert count == 2

    # the core UPDATE bypasses the identity map — reload from the DB
    await db_session.refresh(feed)
    assert feed.last_fetched_at is not None
