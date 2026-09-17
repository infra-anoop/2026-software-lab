"""Direct HTTP(S) fetch with SSRF-oriented controls (plan P7)."""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES = 2_000_000
TIMEOUT_SEC = 15.0
MAX_REDIRECTS = 5


@dataclass(frozen=True)
class FetchBudget:
    """Size, time, and redirect caps for one URL fetch."""

    max_bytes: int = MAX_BYTES
    timeout_sec: float = TIMEOUT_SEC
    max_redirects: int = MAX_REDIRECTS
    allow_http: bool = False


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def resolved_hosts_are_public(hostname: str) -> bool:
    """Reject hostnames that resolve to any non-public address."""
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if not _is_public_ip(ip):
            return False
    return True


def _extract_title(html: str) -> str:
    match = re.search(r"<title[^>]*>([^<]{1,200})", html, re.IGNORECASE | re.DOTALL)
    if match:
        return " ".join(match.group(1).split())
    return ""


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return " ".join(text.split())


def _content_type(resp: httpx.Response) -> str:
    raw = resp.headers.get("content-type") or ""
    if ";" in raw:
        raw = raw.split(";", 1)[0]
    return raw.strip().lower()


async def fetch_url_text(url: str, *, budget: FetchBudget | None = None) -> tuple[str, str, str] | None:
    """Fetch URL → ``(final_url, title, plain_text)`` or None if blocked/failed."""
    cap = budget or FetchBudget()
    current = url.strip()
    if not current.startswith(("http://", "https://")):
        return None
    if current.startswith("http://") and not cap.allow_http:
        return None

    headers = {
        "User-Agent": "SmartWriterV2Bot/0.1",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
    }
    redirects = 0
    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=False,
        timeout=cap.timeout_sec,
        limits=httpx.Limits(max_connections=4),
    ) as client:
        while redirects <= cap.max_redirects:
            parsed = urlparse(current)
            if parsed.scheme not in {"http", "https"}:
                return None
            if parsed.scheme == "http" and not cap.allow_http:
                return None
            host = parsed.hostname
            if not host:
                return None
            if host.lower() in {"localhost"} or host.endswith(".localhost"):
                return None
            if not resolved_hosts_are_public(host):
                return None

            try:
                resp = await client.get(current)
            except httpx.HTTPError:
                return None

            if resp.status_code in {301, 302, 303, 307, 308}:
                loc = resp.headers.get("location")
                if not loc:
                    return None
                current = urljoin(current, loc)
                redirects += 1
                continue

            if resp.status_code != 200:
                return None
            body = resp.content
            if len(body) > cap.max_bytes:
                return None

            ctype = _content_type(resp)
            final_url = str(resp.url)
            if ctype.startswith("text/html") or "html" in ctype:
                html = body.decode(resp.encoding or "utf-8", errors="replace")
                title = _extract_title(html) or host
                return final_url, title, _html_to_text(html)
            if ctype.startswith("text/"):
                text = body.decode(resp.encoding or "utf-8", errors="replace")
                return final_url, host, text.strip()
            return None
    return None
