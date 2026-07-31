import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models.models import Base, Feed

logger = logging.getLogger(__name__)


async def init_models():
    """Initializes the PostgreSQL database schema and seeds default data"""
    logger.info("Initializing database")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema created")

    # Seed default feeds
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
    logger.info("Initialization complete")

if __name__ == "__main__":
    from app.core.logging_config import setup_logging

    setup_logging()
    asyncio.run(init_models())
