from sqlalchemy import select, text

from app import run_worker
from app.models.models import Article, ArticleAnalysis, ArticleCategory, Feed
from app.services.ai_processor import AIAnalysisResult


async def _seed_article(db_session, link="https://w.test/a") -> Article:
    feed = Feed(title="W", url="https://w.test/rss")
    db_session.add(feed)
    await db_session.flush()
    article = Article(title="Worker article", link=link, feed_id=feed.id)
    db_session.add(article)
    await db_session.commit()
    return article


async def _analysis_for(db_session, article_id):
    return (
        await db_session.execute(
            select(ArticleAnalysis).where(ArticleAnalysis.article_id == article_id)
        )
    ).scalar_one_or_none()


async def test_extraction_failure_writes_sentinel(db_session, monkeypatch):
    article = await _seed_article(db_session)

    async def no_text(url):
        return None

    monkeypatch.setattr(run_worker.ai_processor, "extract_text_from_url", no_text)
    await run_worker.analyze_pending_articles(db_session)

    sentinel = await _analysis_for(db_session, article.id)
    assert sentinel is not None
    assert sentinel.summary == "Content extraction failed."
    assert sentinel.model_used == "none"


async def test_successful_analysis_saved(db_session, monkeypatch):
    article = await _seed_article(db_session)

    async def some_text(url):
        return "Extracted article body"

    async def fake_analyze(items):
        assert [item_id for item_id, _, _ in items] == [article.id]
        return {
            article.id: AIAnalysisResult(
                summary="A fine summary",
                category=ArticleCategory.SCIENCE,
                language="English",
            )
        }

    monkeypatch.setattr(run_worker.ai_processor, "extract_text_from_url", some_text)
    monkeypatch.setattr(run_worker.ai_processor, "analyze_articles", fake_analyze)
    await run_worker.analyze_pending_articles(db_session)

    analysis = await _analysis_for(db_session, article.id)
    assert analysis is not None
    assert analysis.summary == "A fine summary"
    assert analysis.category == ArticleCategory.SCIENCE
    assert analysis.model_used == run_worker.ai_processor.model_name


async def test_failed_analysis_stays_pending(db_session, monkeypatch):
    article = await _seed_article(db_session)

    async def some_text(url):
        return "Extracted article body"

    async def fake_analyze(items):
        return {}  # CLI failure / unparseable reply

    monkeypatch.setattr(run_worker.ai_processor, "extract_text_from_url", some_text)
    monkeypatch.setattr(run_worker.ai_processor, "analyze_articles", fake_analyze)
    await run_worker.analyze_pending_articles(db_session)

    # no row: the article is retried on the next cycle
    assert await _analysis_for(db_session, article.id) is None


async def test_analysis_failure_gives_up_after_retry_window(db_session, monkeypatch):
    from datetime import datetime, timedelta, timezone

    feed = Feed(title="Old", url="https://old.test/rss")
    db_session.add(feed)
    await db_session.flush()

    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    old = Article(
        title="Ancient failing article",
        link="https://old.test/ancient",
        feed_id=feed.id,
        created_at=now_naive - run_worker.ANALYSIS_RETRY_WINDOW - timedelta(hours=1),
    )
    fresh = Article(
        title="Fresh failing article",
        link="https://old.test/fresh",
        feed_id=feed.id,
        created_at=now_naive,
    )
    db_session.add_all([old, fresh])
    await db_session.commit()

    async def some_text(url):
        return "body"

    async def fake_analyze(items):
        return {}  # analysis fails for everything

    monkeypatch.setattr(run_worker.ai_processor, "extract_text_from_url", some_text)
    monkeypatch.setattr(run_worker.ai_processor, "analyze_articles", fake_analyze)
    await run_worker.analyze_pending_articles(db_session)

    # past the window: sentinel; within the window: still pending (retried)
    old_analysis = await _analysis_for(db_session, old.id)
    assert old_analysis is not None and old_analysis.summary == "Analysis failed."
    assert await _analysis_for(db_session, fresh.id) is None


async def test_pending_query_prefers_newest(db_session, monkeypatch):
    feed = Feed(title="Order", url="https://order.test/rss")
    db_session.add(feed)
    await db_session.flush()
    for i in range(3):
        db_session.add(
            Article(title=f"n{i}", link=f"https://order.test/{i}", feed_id=feed.id)
        )
    await db_session.commit()

    seen_order = []

    async def tracking_extract(url):
        seen_order.append(url)
        return None  # extraction failure path, no AI involved

    monkeypatch.setattr(
        run_worker.ai_processor, "extract_text_from_url", tracking_extract
    )
    await run_worker.analyze_pending_articles(db_session)

    # highest id (newest) first
    assert seen_order == [
        "https://order.test/2",
        "https://order.test/1",
        "https://order.test/0",
    ]


async def test_worker_run_skips_when_lock_held(engine, monkeypatch):
    """A second cycle started while one runs must be a no-op (advisory lock)."""
    called = False

    async def fake_sync(session):
        nonlocal called
        called = True

    monkeypatch.setattr(run_worker, "sync_all_feeds", fake_sync)

    # Hold the lock from an unrelated connection, as a running cycle would
    async with engine.connect() as holder:
        got = (
            await holder.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": run_worker.WORKER_LOCK_KEY},
            )
        ).scalar()
        assert got is True
        await holder.commit()
        try:
            await run_worker.worker_run()
        finally:
            await holder.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": run_worker.WORKER_LOCK_KEY},
            )
            await holder.commit()

    assert called is False


async def test_worker_run_executes_and_releases_lock(engine, monkeypatch):
    calls = []

    async def fake_sync(session):
        calls.append("sync")

    async def fake_analyze(session):
        calls.append("analyze")

    monkeypatch.setattr(run_worker, "sync_all_feeds", fake_sync)
    monkeypatch.setattr(run_worker, "analyze_pending_articles", fake_analyze)

    await run_worker.worker_run()
    assert calls == ["sync", "analyze"]

    # the lock must be free again afterwards
    async with engine.connect() as conn:
        got = (
            await conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": run_worker.WORKER_LOCK_KEY},
            )
        ).scalar()
        assert got is True
        await conn.execute(
            text("SELECT pg_advisory_unlock(:key)"),
            {"key": run_worker.WORKER_LOCK_KEY},
        )
        await conn.commit()
