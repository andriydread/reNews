import time
from datetime import datetime

import feedparser
import httpx


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
                if entry.ger("published_parsed"):
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

            return {
                "feed_title": parsed_data.feed.get("title", "Unknown"),
                "articles": articles,
            }

        except httpx.HTTPStatusError as e:
            print(f"Server error {e.response.status_code} while fetching {url}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


# To test it (manually):
manager = FeedManager()
print(manager.fetch_feed_data("https://news.ycombinator.com/rss"))
