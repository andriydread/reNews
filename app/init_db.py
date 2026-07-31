import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import Feed

logger = logging.getLogger(__name__)


async def seed_defaults():
    """Seeds default data. Schema is managed by Alembic (alembic upgrade head
    runs before this in renews.service) — this only inserts missing rows."""
    async with AsyncSessionLocal() as session:
        hn_url = "https://news.ycombinator.com/rss"
        result = await session.execute(select(Feed).where(Feed.url == hn_url))
        if not result.scalar_one_or_none():
            hn_feed = Feed(
                title="Hacker News",
                url=hn_url
            )
            session.add(hn_feed)
            await session.commit()
            logger.info("Added default feed: %s", hn_feed.title)
        else:
            logger.info("Default feed already exists")


if __name__ == "__main__":
    from app.core.logging_config import setup_logging

    setup_logging()
    asyncio.run(seed_defaults())
