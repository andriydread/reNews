from sqlalchemy import select

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
