from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_refresh_token
from app.models.models import RefreshToken


async def _refresh_row(db_session, raw_token):
    return (
        await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.token == hash_refresh_token(raw_token)
            )
        )
    ).scalar_one_or_none()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def test_login_wrong_password_rejected(client):
    resp = await client.post(
        "/api/auth/login", data={"username": "testadmin", "password": "wrong"}
    )
    assert resp.status_code == 401
    assert "admin_access_token" not in client.cookies


async def test_login_wrong_username_rejected(client):
    resp = await client.post(
        "/api/auth/login", data={"username": "nobody", "password": "testpass"}
    )
    assert resp.status_code == 401


async def test_login_non_ascii_credentials_rejected_not_500(client):
    # str-based compare_digest raises TypeError on non-ASCII; must be a
    # clean 401, not an internal error
    resp = await client.post(
        "/api/auth/login", data={"username": "ädmin", "password": "pässwörd"}
    )
    assert resp.status_code == 401


async def test_login_sets_cookies_and_stores_refresh_token(client, db_session):
    resp = await client.post(
        "/api/auth/login", data={"username": "testadmin", "password": "testpass"}
    )
    assert resp.status_code == 200
    assert client.cookies.get("admin_access_token")
    refresh = client.cookies.get("admin_refresh_token")
    assert refresh

    row = await _refresh_row(db_session, refresh)
    assert row is not None
    assert row.username == "testadmin"
    assert row.expires_at > _now_utc()
    # stored hashed, never raw
    assert row.token != refresh


async def test_refresh_issues_new_access_token(admin_client):
    # Simulate an expired/lost access token; the refresh cookie remains.
    # (Can't assert inequality with the old token: sub+exp have whole-second
    # resolution, so a refresh within the same second is byte-identical.)
    del admin_client.cookies["admin_access_token"]

    resp = await admin_client.post("/api/auth/refresh")
    assert resp.status_code == 200
    new_access = admin_client.cookies.get("admin_access_token")
    assert new_access

    import jwt

    from app.core.config import settings

    payload = jwt.decode(new_access, settings.JWT_SECRET, algorithms=["HS256"])
    assert payload["sub"] == "testadmin"


async def test_refresh_rotates_token(admin_client, db_session):
    old_refresh = admin_client.cookies.get("admin_refresh_token")

    resp = await admin_client.post("/api/auth/refresh")
    assert resp.status_code == 200
    new_refresh = admin_client.cookies.get("admin_refresh_token")
    assert new_refresh and new_refresh != old_refresh

    # old row consumed, new row present
    assert await _refresh_row(db_session, old_refresh) is None
    assert await _refresh_row(db_session, new_refresh) is not None

    # replaying the consumed token must fail
    admin_client.cookies.set("admin_refresh_token", old_refresh)
    resp = await admin_client.post("/api/auth/refresh")
    assert resp.status_code == 401


async def test_refresh_without_cookie_rejected(client):
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


async def test_refresh_expired_token_rejected_and_deleted(client, db_session):
    db_session.add(
        RefreshToken(
            token=hash_refresh_token("expired-token"),
            username="testadmin",
            expires_at=_now_utc() - timedelta(days=1),
        )
    )
    await db_session.commit()

    client.cookies.set("admin_refresh_token", "expired-token")
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401
    # the 401 must actually clear the stale cookie (HTTPException used to
    # discard the delete_cookie header)
    set_cookies = ";".join(resp.headers.get_list("set-cookie"))
    assert "admin_refresh_token" in set_cookies

    assert await _refresh_row(db_session, "expired-token") is None


async def test_logout_deletes_refresh_token(admin_client, db_session):
    refresh = admin_client.cookies.get("admin_refresh_token")

    resp = await admin_client.post("/api/auth/logout")
    assert resp.status_code == 200

    assert await _refresh_row(db_session, refresh) is None


async def test_admin_page_redirects_without_token(client):
    resp = await client.get("/admin", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"


async def test_admin_page_renders_when_logged_in(admin_client):
    resp = await admin_client.get("/admin")
    assert resp.status_code == 200


async def test_admin_page_rejects_token_with_wrong_subject(client):
    # Signed with the right secret but wrong sub — the old inline check in
    # views.py accepted this; the shared path must not
    import jwt as pyjwt

    from app.core.config import settings

    forged = pyjwt.encode(
        {"sub": "not-the-admin", "exp": 4102444800},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    client.cookies.set("admin_access_token", forged)
    resp = await client.get("/admin", follow_redirects=False)
    assert resp.status_code == 302
