import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.models import Article, ArticleAnalysis, Feed
from app.services.ai_processor import AIProcessor
from app.services.feed_manager import FeedManager


async def process_feeds(session, feed_manager):
    result = await session.execute(select(Feed))
    feeds = result.scalars().all()

    # For testing
    if not feeds:
        print("[*] No feeds found in database. Using test RSS feed - Hacker News")
        hn_feed = Feed(title="Hacker News", url="https://news.ycombinator.com/rss")
        session.add(hn_feed)
        await session.commit()
        feeds = [hn_feed]

    for feed in feeds:
        print(f"Fetching: {feed.title} ({feed.url})")
        articles = await feed_manager.fetch_feed_data(feed.url)

        if not articles:
            print(f"No articles found or error fetching {feed.url}")
            continue

        print(f"Retrieved {len(articles)} articles")
        await feed_manager.save_articles_to_db(session, feed.id, articles)
        print(f"Processed {feed.title}")


async def process_ai_analysis(session, ai_processor):
    query = (
        select(Article)
        .options(selectinload(Article.analysis))
        .filter(~Article.analysis.has())
    )

    result = await session.execute(query)
    unprocessed_articles = result.scalars().all()

    if not unprocessed_articles:
        print("All articles have been analyzed")
        return

    print(f"{len(unprocessed_articles)} articles needs to be analyzed by AI")

    for article in unprocessed_articles:
        print(f"Prossesing {article.title[:50]}")

        text = await ai_processor.extract_text_from_url(article.link)
        if not text:
            print(f"Error extracting text from {article.link}. Skipping this article")
            continue

        ai_result = await ai_processor.analyze_article(article.title, text)
        if not ai_result:
            print("No JSON received. Skipping analyzing")
            continue

        new_analysis = ArticleAnalysis(
            article_id=article.id,
            summary=ai_result.summary,
            category=ai_result.category,
            score=ai_result.score,
            language=ai_result.language,
            model_used=ai_processor.model_name,
        )

        session.add(new_analysis)

        await session.commit()

        await asyncio.sleep(2)


async def main():
    feed_manager = FeedManager()
    ai_processor = AIProcessor()

    async with AsyncSessionLocal() as session:
        try:
            await process_feeds(session, feed_manager)

            await process_ai_analysis(session, ai_processor)

        except SQLAlchemyError as e:
            print(f"Database Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
