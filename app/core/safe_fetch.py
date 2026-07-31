import asyncio
import ipaddress
from urllib.parse import urlparse

import httpx

# Feed URLs are admin-supplied but article links come from third-party feed
# content, so every worker fetch is treated as untrusted: http(s) only, no
# private/internal targets, safety re-checked on every redirect hop, and a
# cap on response size.

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5


class UnsafeUrlError(Exception):
    """The URL points somewhere the worker must not fetch."""


def _ip_is_private(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _resolve_host(host: str) -> list[str]:
    """All addresses a hostname resolves to (patchable in tests)."""
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, None)
    except OSError as exc:
        raise UnsafeUrlError(f"cannot resolve host {host!r}") from exc
    return [info[4][0] for info in infos]


async def ensure_public_http_url(url: str) -> None:
    """Raise UnsafeUrlError unless url is http(s) to a public address."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"scheme {parsed.scheme!r} not allowed")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL has no host")

    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        addresses = [ipaddress.ip_address(a) for a in await _resolve_host(host)]

    for ip in addresses:
        if _ip_is_private(ip):
            raise UnsafeUrlError(f"{host!r} resolves to non-public address {ip}")


async def fetch_url_safely(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """
    GET with SSRF protection. The client must NOT follow redirects itself —
    each hop is validated here before it is requested.
    """
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        await ensure_public_http_url(current)
        response = await client.get(current)

        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                raise UnsafeUrlError("redirect without Location header")
            current = str(httpx.URL(current).join(location))
            continue

        if len(response.content) > MAX_RESPONSE_BYTES:
            raise UnsafeUrlError(f"response larger than {MAX_RESPONSE_BYTES} bytes")
        return response

    raise UnsafeUrlError(f"more than {MAX_REDIRECTS} redirects")
