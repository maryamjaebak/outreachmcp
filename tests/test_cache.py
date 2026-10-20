import time
from pathlib import Path

from outreach_mcp.cache import Cache


def test_set_and_get(tmp_path: Path) -> None:
    cache = Cache(tmp_path / "test.db")
    cache.set("key", {"a": 1}, ttl_seconds=60)
    assert cache.get("key") == {"a": 1}


def test_missing_key_returns_none(tmp_path: Path) -> None:
    cache = Cache(tmp_path / "test.db")
    assert cache.get("missing") is None


def test_expired_key_returns_none(tmp_path: Path) -> None:
    cache = Cache(tmp_path / "test.db")
    cache.set("key", {"a": 1}, ttl_seconds=0.01)
    time.sleep(0.05)
    assert cache.get("key") is None
