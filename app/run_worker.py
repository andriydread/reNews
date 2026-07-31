import asyncio

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.models.models import Article, ArticleAnalysis, Feed
from app.services.ai_processor import AIProcessor
from app.services.feed_manager import FeedManager

# Arbitrary but stable app-wide id for the Postgres advisory lock that keeps
# two worker cycles (timer firing while a slow cycle still runs, or a manual
# `systemctl start renews-worker`) from processing the same articles twice.
WORKER_LOCK_KEY = 815_001

feed_manager = FeedManager()
ai_processor = AIProcessor()


async def sync_all_feeds(session):
    """Fetches new links for all feeds in the database, saves only ones that are not in db"""
    result = await session.execute(select(Feed))
    feeds = result.scalars().all()

    for feed in feeds:
        articles_data = await feed_manager.fetch_feed_data(feed.url)

        if articles_data:
            await feed_manager.save_articles_to_db(session, feed.id, articles_data)


async def analyze_pending_articles(session):
    """Finds articles without analysis and runs them through the AI processor"""
    query = (
        select(Article)
        .options(selectinload(Article.analysis))
        .filter(~Article.analysis.has())
        .limit(50)
    )

    result = await session.execute(query)
    pending = result.scalars().all()

    if not pending:
        return

    # Scrape phase: collect article text, sentinel-mark pages we can't extract
    to_analyze: list[tuple[Article, str]] = []
    for article in pending:
        text = await ai_processor.extract_text_from_url(article.link)

        if not text:
            # If we can't scrape or text not awailable, 'failed' status is appended so app don't try again forever
            failed = ArticleAnalysis(
                article_id=article.id,
                summary="Content extraction failed.",
                category="Other",
                language="unknown",
                model_used="none",
            )
            session.add(failed)
            await session.commit()
            continue

        to_analyze.append((article, text))
        # temp limit
        await asyncio.sleep(1)

    # Analysis phase: one claude CLI call per batch. Articles missing from a
    # batch result stay pending and are retried on the next cycle.
    batch_size = settings.AI_BATCH_SIZE
    for i in range(0, len(to_analyze), batch_size):
        batch = to_analyze[i : i + batch_size]
        results = await ai_processor.analyze_articles(
            [(article.id, article.title, text) for article, text in batch]
        )

        for article, _ in batch:
            ai_data = results.get(article.id)
            if ai_data:
                session.add(
                    ArticleAnalysis(
                        article_id=article.id,
                        summary=ai_data.summary,
                        category=ai_data.category,
                        language=ai_data.language,
                        model_used=ai_processor.model_name,
                    )
                )
        await session.commit()


async def worker_run():
    """Main entry point for the worker cycle."""
    print("Worker started...")
    # The advisory lock lives on its own connection: session-level commits
    # release the session's connection back to the pool, which would strand
    # the lock on a pooled connection if it were taken through the session.
    async with engine.connect() as lock_conn:
        locked = (
            await lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": WORKER_LOCK_KEY}
            )
        ).scalar()
        # Advisory locks are session-scoped, not transaction-scoped: commit so
        # the connection doesn't sit idle-in-transaction for the whole cycle.
        await lock_conn.commit()

        if not locked:
            print("Another worker cycle is already running; skipping.")
            return

        try:
            async with AsyncSessionLocal() as session:
                try:
                    # Get new links
                    print("Syncing feeds...")
                    await sync_all_feeds(session)
                    # Process them with AI
                    print("Analyzing pending articles...")
                    await analyze_pending_articles(session)
                    print("Worker cycle complete.")
                except Exception as e:
                    print(f"Worker failed with error: {e}")
                    import traceback

                    traceback.print_exc()
        finally:
            await lock_conn.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": WORKER_LOCK_KEY}
            )
            await lock_conn.commit()


if __name__ == "__main__":
    asyncio.run(worker_run())
