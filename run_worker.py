import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import AsyncSessionLocal
from app.models.models import Feed
from app.services.feed_manager import FeedManager


async def main():
    print("[+] Starting worker")
    manager = FeedManager()

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Feed))
            feeds = result.scalars().all()

            if not feeds:
                print("[+] No feeds in database. Adding test feed (Hacker News)")
                hn_feed = Feed(
                    title="Hacker News", url="https://news.ycombinator.com/rss"
                )
                session.add(hn_feed)
                await session.commit()
                feeds = [hn_feed]

            print(f"[!] Found {len(feeds)} feeds to process.")

            for feed in feeds:
                print(f"[+] Fetching - {feed.title} ({feed.url})")
                articles = await manager.fetch_feed_data(feed.url)

                if not articles:
                    print(f"[-] No articles found or error fetching {feed.url}")
                    continue

                print(f"[!] Fetched {len(articles)} articles")

                await manager.save_articles_to_db(session, feed.id, articles)
                print("[->] Done")

        except SQLAlchemyError as e:
            print(f"[-] Database Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[-] Unexpected Error: {e}")
            sys.exit(1)

    print("[->] Worker Done")


if __name__ == "__main__":
    asyncio.run(main())
