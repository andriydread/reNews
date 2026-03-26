import time
from datetime import datetime

import feedparser
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article


class FeedManager:
    def __init__(self):
        self.headers = {"User-Agent": "reNews-Aggregator/1.0"}

    async def fetch_feed_data(self, url: str):
        try:
            async with httpx.AsyncClient(headers=self.headers) as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()

            parsed_data = feedparser.parse(response.text)

            if parsed_data.bozo:
                return None

            articles = []
            for entry in parsed_data.entries:
                published = None
                if entry.get("published_parsed"):
                    published = datetime.fromtimestamp(
                        time.mktime(entry.published_parsed)
                    )

                articles.append(
                    {
                        "title": entry.get("title", "No Title"),
                        "link": entry.get("link"),
                        "published_date": published,
                    }
                )

            return articles

        except httpx.HTTPStatusError as e:
            print(f"Server error {e.response.status_code} while fetching {url}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

    async def save_articles_to_db(
        self, session: AsyncSession, feed_id: int, articles: list[dict]
    ):
        for article in articles:
            to_insert = insert(Article).values(
                title=article["title"],
                link=article["link"],
                published_at=article["published_date"],
                feed_id=feed_id,
            )

            to_insert = to_insert.on_conflict_do_nothing(index_elements=["link"])

            await session.execute(to_insert)

        await session.commit()
