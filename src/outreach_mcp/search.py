from __future__ import annotations

import hashlib
import os
from typing import cast

import requests

from outreach_mcp.cache import Cache

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "./outreach.db")
CACHE_TTL_SECONDS = 24 * 60 * 60


def _cache_key(query: str, max_results: int) -> str:
    return hashlib.sha256(f"{query}:{max_results}".encode()).hexdigest()


def search_web(query: str, max_results: int = 8) -> list[dict[str, str]]:
    """Search the web via a local SearXNG instance, cached in SQLite."""
    cache = Cache(DATABASE_PATH)
    key = _cache_key(query, max_results)
    cached = cache.get(key)
    if cached is not None:
        return cast(list[dict[str, str]], cached)

    response = requests.get(
        f"{SEARXNG_URL}/search",
        params={"q": query, "format": "json"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    results = [
        {"title": r["title"], "url": r["url"], "content": r["content"]}
        for r in data.get("results", [])[:max_results]
    ]
    cache.set(key, results, CACHE_TTL_SECONDS)
    return results
