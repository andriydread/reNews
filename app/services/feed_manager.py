import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import feedparser
import httpx
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.safe_fetch import fetch_url_safely
from app.models.models import Article, Feed

logger = logging.getLogger(__name__)


class FeedManager:
    def __init__(self):
        self.headers = {"User-Agent": settings.USER_AGENT}

    async def fetch_feed_data(self, url: str) -> List[Dict[str, Any]] | None:
        try:
            # httpx (async) instead of requests for speed; redirects are
            # followed by fetch_url_safely with an SSRF check per hop
            async with httpx.AsyncClient(
                headers=self.headers, follow_redirects=False, timeout=15.0
            ) as client:
                response = await fetch_url_safely(client, url)
                response.raise_for_status()

            parsed_data = feedparser.parse(response.text)

            articles = []
            for entry in parsed_data.entries:
                # feedparser normalizes dates to UTC struct_time; build the
                # datetime as UTC directly (time.mktime would misread it as
                # local time and skew by the server's UTC offset)
                published = None
                parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if parsed:
                    published = datetime(*parsed[:6], tzinfo=timezone.utc)

                articles.append(
                    {
                        "title": entry.get("title", "No Title").strip(),
                        "link": entry.get("link"),
                        "published_date": published,
                    }
                )

            return articles

        except Exception as exc:
            logger.warning("failed to fetch feed %s: %s", url, exc)
            return None

    async def save_articles_to_db(
        self, session: AsyncSession, feed_id: int, articles: List[Dict[str, Any]]
    ) -> int:

        if not articles:
            return 0

        # Dedupe within the batch (feeds occasionally repeat a link) and
        # insert everything in one round-trip; rowcount is the new-item count
        # since conflicting links are skipped, not updated.
        seen: set[str] = set()
        rows = []
        for article in articles:
            if not article["link"] or article["link"] in seen:
                continue
            seen.add(article["link"])
            rows.append(
                {
                    "title": article["title"],
                    "link": article["link"],
                    "published_at": article["published_date"],
                    "feed_id": feed_id,
                    # rest of fields use defaults from models.py
                }
            )

        if not rows:
            return 0

        result = await session.execute(
            insert(Article).values(rows).on_conflict_do_nothing(index_elements=["link"])
        )
        new_items_count = result.rowcount

        await session.execute(
            update(Feed)
            .where(Feed.id == feed_id)
            .values(last_fetched_at=datetime.now(timezone.utc))
        )

        await session.commit()
        return new_items_count
