from __future__ import annotations

import os
import urllib.robotparser
from typing import cast
from urllib.parse import urlparse

import requests
import trafilatura

from outreach_mcp.cache import Cache
from outreach_mcp.ratelimit import PerDomainRateLimiter
from outreach_mcp.seen import mark_seen, was_seen

__all__ = ["fetch_page", "was_seen", "RobotsDisallowedError", "PerDomainRateLimiter"]

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./outreach.db")
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
USER_AGENT = "outreach-mcp/0.1 (+https://github.com/maryamjaebak/outreachmcp)"

_rate_limiter = PerDomainRateLimiter(min_interval_seconds=1.0)
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


class RobotsDisallowedError(Exception):
    pass


def _get_robot_parser(domain_root: str) -> urllib.robotparser.RobotFileParser:
    if domain_root not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        # fetched with our own User-Agent, not urllib's default, since some
        # sites 403 the default one (robotparser treats 401/403 as disallow-all)
        try:
            response = requests.get(
                f"{domain_root}/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=5
            )
            if response.status_code == 200:
                rp.parse(response.text.splitlines())
            elif response.status_code in (401, 403):
                rp.parse(["User-agent: *", "Disallow: /"])
            # any other status (404 included): no rules loaded, default allow
        except requests.RequestException:
            pass  # unreachable robots.txt: default to allow
        _robots_cache[domain_root] = rp
    return _robots_cache[domain_root]


def fetch_page(url: str, max_chars: int = 4000) -> str:
    """Fetch a page, extract its main text, respecting robots.txt and rate limits."""
    parsed = urlparse(url)
    domain_root = f"{parsed.scheme}://{parsed.netloc}"

    rp = _get_robot_parser(domain_root)
    if not rp.can_fetch(USER_AGENT, url):
        raise RobotsDisallowedError(f"robots.txt disallows fetching {url}")

    cache = Cache(DATABASE_PATH)
    key = f"page:{url}:{max_chars}"
    cached = cache.get(key)
    if cached is not None:
        mark_seen(DATABASE_PATH, url)
        return cast(str, cached)

    _rate_limiter.wait(parsed.netloc)

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
    response.raise_for_status()

    text = trafilatura.extract(response.text) or ""
    text = text[:max_chars]

    cache.set(key, text, CACHE_TTL_SECONDS)
    mark_seen(DATABASE_PATH, url)
    return text
