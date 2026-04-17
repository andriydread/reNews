import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.models import Article, ArticleAnalysis, Feed
from app.services.ai_processor import AIProcessor
from app.services.feed_manager import FeedManager

feed_manager = FeedManager()
ai_processor = AIProcessor()


async def sync_all_feeds(session):
    """Fetches new links for all feeds in the database, saves only ones that are not in db"""
    result = await session.execute(select(Feed))
    feeds = result.scalars().all()

    for feed in feeds:
        articles_data = await feed_manager.fetch_feed_data(feed.url)

        if articles_data:
            await feed_manager.save_articles_to_db(
                session, feed.id, articles_data
            )


async def analyze_pending_articles(session):
    """Finds articles without analysis and runs them through Gemini"""
    query = (
        select(Article)
        .options(selectinload(Article.analysis))
        .filter(~Article.analysis.has())
        .limit(20)
    )

    result = await session.execute(query)
    pending = result.scalars().all()

    if not pending:
        return

    for article in pending:
        text = await ai_processor.extract_text_from_url(article.link)

        if not text:
            # If we can't scrape or text not awailable, 'failed' status is appended so app don't try again forever.
            failed = ArticleAnalysis(
                article_id=article.id,
                summary="Content extraction failed.",
                category="Other",
                score=0,
                language="unknown",
                model_used="none",
            )
            session.add(failed)
            await session.commit()
            continue

        ai_data = await ai_processor.analyze_article(article.title, text)

        if ai_data:
            analysis = ArticleAnalysis(
                article_id=article.id,
                summary=ai_data.summary,
                category=ai_data.category,
                score=ai_data.score,
                language=ai_data.language,
                model_used="gemini-3.1-flash-lite",
            )
            session.add(analysis)
            await session.commit()

        # temp limit
        await asyncio.sleep(1)


async def worker_run():
    """Main entry point for the worker cycle."""
    async with AsyncSessionLocal() as session:
        try:
            # Get new links
            await sync_all_feeds(session)
            # Process them with AI
            await analyze_pending_articles(session)
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(worker_run())
