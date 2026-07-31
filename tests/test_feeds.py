from sqlalchemy import select

from app.models.models import Feed


async def test_feeds_endpoints_require_auth(client):
    assert (await client.get("/api/feeds")).status_code == 401
    assert (
        await client.post("/api/feeds", json={"title": "X", "url": "https://x.test/rss"})
    ).status_code == 401
    assert (await client.delete("/api/feeds/1")).status_code == 401


async def test_add_and_list_feeds(admin_client, db_session):
    resp = await admin_client.post(
        "/api/feeds", json={"title": "Test Feed", "url": "https://feed.test/rss"}
    )
    assert resp.status_code == 200
    created = resp.json()
    assert created["title"] == "Test Feed"

    listed = (await admin_client.get("/api/feeds")).json()
    assert any(f["url"] == "https://feed.test/rss" for f in listed)


async def test_duplicate_feed_url_rejected(admin_client):
    payload = {"title": "Dup", "url": "https://dup.test/rss"}
    assert (await admin_client.post("/api/feeds", json=payload)).status_code == 200

    resp = await admin_client.post("/api/feeds", json=payload)
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


async def test_delete_feed(admin_client, db_session):
    resp = await admin_client.post(
        "/api/feeds", json={"title": "Doomed", "url": "https://doomed.test/rss"}
    )
    feed_id = resp.json()["id"]

    assert (await admin_client.delete(f"/api/feeds/{feed_id}")).status_code == 200

    row = (
        await db_session.execute(select(Feed).where(Feed.id == feed_id))
    ).scalar_one_or_none()
    assert row is None


async def test_delete_missing_feed_404(admin_client):
    resp = await admin_client.delete("/api/feeds/999999")
    assert resp.status_code == 404


async def test_invalid_feed_input_rejected(admin_client):
    # non-http(s) / garbage URLs
    for url in ["not-a-url", "ftp://files.test/feed", "javascript:alert(1)"]:
        resp = await admin_client.post("/api/feeds", json={"title": "X", "url": url})
        assert resp.status_code == 422, url

    # blank and oversize titles must be 422s, not DB-level 500s
    resp = await admin_client.post(
        "/api/feeds", json={"title": "   ", "url": "https://ok.test/rss"}
    )
    assert resp.status_code == 422

    resp = await admin_client.post(
        "/api/feeds", json={"title": "x" * 501, "url": "https://ok.test/rss"}
    )
    assert resp.status_code == 422

    resp = await admin_client.post(
        "/api/feeds",
        json={"title": "X", "url": "https://ok.test/" + "a" * 1000},
    )
    assert resp.status_code == 422
