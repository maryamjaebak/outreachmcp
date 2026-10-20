import urllib.robotparser
from pathlib import Path

import pytest
import responses

from outreach_mcp import fetch

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "kclelectronics_home.html").read_text()
URL = "https://kclelectronics.co.uk/"
DOMAIN_ROOT = "https://kclelectronics.co.uk"


def _allowing_parser() -> urllib.robotparser.RobotFileParser:
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(["User-agent: *", "Allow: /"])
    return rp


def _blocking_parser() -> urllib.robotparser.RobotFileParser:
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(["User-agent: *", "Disallow: /"])
    return rp


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(fetch, "_robots_cache", {DOMAIN_ROOT: _allowing_parser()})
    monkeypatch.setattr(
        fetch, "_rate_limiter", fetch.PerDomainRateLimiter(min_interval_seconds=0.0)
    )


@responses.activate
def test_fetch_page_extracts_main_text() -> None:
    responses.get(URL, body=FIXTURE_HTML, status=200)

    text = fetch.fetch_page(URL, max_chars=4000)

    assert "KCL" in text
    assert "Empowering the next generation of engineers" in text


@responses.activate
def test_fetch_page_respects_max_chars() -> None:
    responses.get(URL, body=FIXTURE_HTML, status=200)

    text = fetch.fetch_page(URL, max_chars=50)

    assert len(text) <= 50


@responses.activate
def test_fetch_page_caches_result() -> None:
    responses.get(URL, body=FIXTURE_HTML, status=200)

    first = fetch.fetch_page(URL, max_chars=4000)
    responses.reset()  # a second network call would now fail
    second = fetch.fetch_page(URL, max_chars=4000)

    assert first == second


@responses.activate
def test_fetch_page_marks_url_as_seen() -> None:
    responses.get(URL, body=FIXTURE_HTML, status=200)

    fetch.fetch_page(URL, max_chars=4000)

    assert fetch.was_seen(fetch.DATABASE_PATH, URL)


def test_fetch_page_raises_when_robots_disallows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "_robots_cache", {DOMAIN_ROOT: _blocking_parser()})

    with pytest.raises(fetch.RobotsDisallowedError):
        fetch.fetch_page(URL)


@responses.activate
def test_get_full_text_returns_untruncated_text_after_fetch() -> None:
    responses.get(URL, body=FIXTURE_HTML, status=200)

    fetch.fetch_page(URL, max_chars=50)  # truncated return value, full text still cached

    full_text = fetch.get_full_text(URL)

    assert full_text is not None
    assert len(full_text) > 50
    assert "Empowering the next generation of engineers" in full_text


def test_get_full_text_returns_none_when_never_fetched() -> None:
    assert fetch.get_full_text(URL) is None
