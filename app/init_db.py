import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.models.models import Base, Feed

async def init_models():
    """Initializes the PostgreSQL database schema and seeds default data"""
    print("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database schema created.")

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
            print(f"Added default feed: {hn_feed.title}")
        else:
            print("Default feed already exists.")
    print("Initialization complete.")

if __name__ == "__main__":
    asyncio.run(init_models())
