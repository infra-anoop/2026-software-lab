"""Direct HTTP(S) fetch with SSRF-oriented controls (design §5.4)."""

from __future__ import annotations

import ipaddress
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin

import httpx

# Optional HTML → text (design §14.1).
try:
    import trafilatura

    _HAS_TRAFILATURA = True
except ImportError:
    _HAS_TRAFILATURA = False


@dataclass(frozen=True)
class FetchBudget:
    max_bytes: int = 2_000_000
    timeout_sec: float = 15.0
    max_redirects: int = 5
    allow_http: bool = False


def _parse_blocklist(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return []
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def _host_blocked(host: str, blocklist: list[str]) -> bool:
    h = host.lower().rstrip(".")
    for entry in blocklist:
        if h == entry or h.endswith("." + entry):
            return True
    return False


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
    )


def _resolved_hosts_are_public(hostname: str) -> bool:
    """Reject hostnames that resolve only to non-public addresses."""
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if not _is_public_ip(ip):
            return False
    return True


def _extract_title(html: str) -> str:
    import re

    m = re.search(r"<title[^>]*>([^<]{1,200})", html, re.IGNORECASE | re.DOTALL)
    if m:
        return " ".join(m.group(1).split())
    return ""


def _html_to_text(html: str) -> str:
    if _HAS_TRAFILATURA:
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
        if extracted and extracted.strip():
            return extracted.strip()
    import re

    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return " ".join(text.split())


def _response_content_type(resp: httpx.Response) -> str:
    raw = resp.headers.get("content-type") or ""
    if ";" in raw:
        raw = raw.split(";", 1)[0]
    return raw.strip().lower()


async def fetch_url_text(
    url: str,
    *,
    budget: FetchBudget | None = None,
) -> tuple[str, str, str] | None:
    """Fetch URL and return ``(final_url, title_or_host, plain_text)`` or ``None``.

    Enforces: scheme allowlist, blocklist env, DNS → public IPs only, redirect cap,
    response size cap. HTML is stripped to text; ``text/*`` returned as decoded body.
    """
    b = budget or FetchBudget()
    blocklist = _parse_blocklist(os.getenv("SMART_WRITER_FETCH_DOMAIN_BLOCKLIST"))

    current = url.strip()
    if not current.startswith(("http://", "https://")):
        return None
    if current.startswith("http://") and not b.allow_http:
        return None

    headers = {
        "User-Agent": "SmartWriterBot/1.0 (+https://github.com/)",
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
    }

    redirects = 0
    total_read = 0
    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=False,
        timeout=b.timeout_sec,
        limits=httpx.Limits(max_connections=4),
    ) as client:
        while redirects <= b.max_redirects:
            parsed = urlparse(current)
            if parsed.scheme not in ("http", "https"):
                return None
            if parsed.scheme == "http" and not b.allow_http:
                return None
            host = parsed.hostname
            if not host:
                return None
            if _host_blocked(host, blocklist):
                return None
            if not _resolved_hosts_are_public(host):
                return None

            try:
                resp = await client.get(current)
            except httpx.HTTPError:
                return None

            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location")
                if not loc:
                    return None
                next_url = urljoin(current, loc)
                current = next_url
                redirects += 1
                continue

            if resp.status_code != 200:
                return None

            ctype = _response_content_type(resp)
            body = resp.content
            if len(body) > b.max_bytes:
                return None
            total_read += len(body)
            if total_read > b.max_bytes:
                return None

            final_url = str(resp.url)
            if ctype.startswith("text/html") or "html" in ctype:
                html = body.decode(resp.encoding or "utf-8", errors="replace")
                title = _extract_title(html) or host
                text = _html_to_text(html)
                return final_url, title, text
            if ctype.startswith("text/"):
                text = body.decode(resp.encoding or "utf-8", errors="replace")
                return final_url, host, text.strip()

            # Non-text types: skip in v1 (PDF etc. deferred).
            return None

    return None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
