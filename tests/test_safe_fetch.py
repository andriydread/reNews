import httpx
import pytest
import respx
from httpx import Response

from app.core import safe_fetch
from app.core.safe_fetch import (
    UnsafeUrlError,
    ensure_public_http_url,
    fetch_url_safely,
)


async def test_rejects_non_http_schemes():
    for url in ["ftp://files.test/x", "file:///etc/passwd", "gopher://x.test/"]:
        with pytest.raises(UnsafeUrlError):
            await ensure_public_http_url(url)


async def test_rejects_literal_private_addresses():
    for url in [
        "http://127.0.0.1/secret",
        "http://10.0.0.5/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://0.0.0.0/",
    ]:
        with pytest.raises(UnsafeUrlError):
            await ensure_public_http_url(url)


async def test_accepts_literal_public_address():
    await ensure_public_http_url("https://93.184.216.34/feed")


async def test_rejects_host_resolving_to_private(monkeypatch):
    async def resolve_private(host):
        return ["192.168.1.10"]

    monkeypatch.setattr(safe_fetch, "_resolve_host", resolve_private)
    with pytest.raises(UnsafeUrlError):
        await ensure_public_http_url("https://internal.evil.test/")


@respx.mock
async def test_redirect_to_private_address_blocked():
    respx.get("https://feeds.test/rss").mock(
        return_value=Response(302, headers={"location": "http://127.0.0.1/secret"})
    )
    async with httpx.AsyncClient(follow_redirects=False) as client:
        with pytest.raises(UnsafeUrlError):
            await fetch_url_safely(client, "https://feeds.test/rss")


@respx.mock
async def test_redirect_loop_bounded():
    respx.get("https://feeds.test/loop").mock(
        return_value=Response(302, headers={"location": "https://feeds.test/loop"})
    )
    async with httpx.AsyncClient(follow_redirects=False) as client:
        with pytest.raises(UnsafeUrlError, match="redirects"):
            await fetch_url_safely(client, "https://feeds.test/loop")


@respx.mock
async def test_safe_redirect_followed():
    respx.get("https://feeds.test/old").mock(
        return_value=Response(301, headers={"location": "https://feeds.test/new"})
    )
    respx.get("https://feeds.test/new").mock(return_value=Response(200, text="ok"))
    async with httpx.AsyncClient(follow_redirects=False) as client:
        response = await fetch_url_safely(client, "https://feeds.test/old")
    assert response.status_code == 200 and response.text == "ok"


async def test_extractor_refuses_private_url():
    from app.services.ai_processor import AIProcessor

    # no respx mock: the URL must be rejected before any request is made
    assert await AIProcessor().extract_text_from_url("http://127.0.0.1/x") is None
