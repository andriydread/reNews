import time
from datetime import datetime

import feedparser
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Article


class FeedManager:
    """Service responsible for downloading RSS/Atom feeds and saving them to the database"""

    def __init__(self):
        # App identification fo servers to not block us right away
        self.headers = {"User-Agent": "reNews-Aggregator/1.0"}

    async def fetch_feed_data(self, url: str):
        """Downloads and parses an RSS or Atom feed, extracting the article metadata"""

        try:
            async with httpx.AsyncClient(headers=self.headers) as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()

            parsed_data = feedparser.parse(response.text)

            # Check for a broken or malformed XML feed
            if parsed_data.bozo:
                print(f"Malformed feed detected at {url}")
                return None

            articles = []

            for entry in parsed_data.entries:
                published = None

                # Convert time format into a standard Python datetime object
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
            print(f"Unexpected error while parsing {url}: {e}")
            return None

    async def save_articles_to_db(
        self, session: AsyncSession, feed_id: int, articles: list[dict]
    ):
        """Inserts fetched articles into the database, safely ignoring duplicates"""

        for article in articles:
            to_insert = insert(Article).values(
                title=article["title"],
                link=article["link"],
                published_at=article["published_date"],
                feed_id=feed_id,
            )

            # If an article with this exact link already exists PostgreSQL will ignore it
            to_insert = to_insert.on_conflict_do_nothing(index_elements=["link"])

            await session.execute(to_insert)

        await session.commit()
