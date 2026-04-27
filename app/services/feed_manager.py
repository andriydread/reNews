import time
from datetime import datetime
from typing import Any, Dict, List

import feedparser
import httpx
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Article, Feed


class FeedManager:
    def __init__(self):
        self.headers = {"User-Agent": settings.USER_AGENT}

    async def fetch_feed_data(self, url: str) -> List[Dict[str, Any]] | None:
        try:
            # httpx (async) instead of requests for speed
            async with httpx.AsyncClient(
                headers=self.headers, follow_redirects=True, timeout=15.0
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

            parsed_data = feedparser.parse(response.text)

            articles = []
            for entry in parsed_data.entries:
                published = None
                if entry.get("published_parsed"):
                    published = datetime.fromtimestamp(
                        time.mktime(entry.published_parsed)
                    )
                elif entry.get("updated_parsed"):
                    published = datetime.fromtimestamp(
                        time.mktime(entry.updated_parsed)
                    )

                articles.append(
                    {
                        "title": entry.get("title", "No Title").strip(),
                        "link": entry.get("link"),
                        "published_date": published,
                    }
                )

            return articles

        except Exception:
            return None

    async def save_articles_to_db(
        self, session: AsyncSession, feed_id: int, articles: List[Dict[str, Any]]
    ) -> int:

        if not articles:
            return 0

        new_items_count = 0
        for article in articles:
            stmt = (
                insert(Article)
                .values(
                    title=article["title"],
                    link=article["link"],
                    published_at=article["published_date"],
                    feed_id=feed_id,
                    # rest of fiels use defaults from models.py
                )
                .on_conflict_do_nothing(index_elements=["link"])
            )

            result = await session.execute(stmt)
            if result.rowcount > 0:
                new_items_count += 1

        await session.execute(
            update(Feed)
            .where(Feed.id == feed_id)
            .values(last_fetched_at=datetime.now())
        )

        await session.commit()
        return new_items_count
