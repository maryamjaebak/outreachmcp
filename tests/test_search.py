import json
from pathlib import Path

import pytest
import responses

from outreach_mcp import search

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "searxng_kcl_electronics.json").read_text()
)


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search, "DATABASE_PATH", str(tmp_path / "test.db"))


@responses.activate
def test_search_web_queries_searxng_and_parses_results() -> None:
    responses.get(
        f"{search.SEARXNG_URL}/search",
        json=FIXTURE,
        status=200,
    )

    results = search.search_web("KCL Electronics Society", max_results=3)

    assert len(results) == 3
    assert results[0]["title"] == "KCL Electronics Society"
    assert results[0]["url"] == "https://kclelectronics.co.uk/"
    assert "KCL" in results[0]["content"]


@responses.activate
def test_search_web_caches_result(monkeypatch: pytest.MonkeyPatch) -> None:
    responses.get(
        f"{search.SEARXNG_URL}/search",
        json=FIXTURE,
        status=200,
    )

    first = search.search_web("KCL Electronics Society", max_results=5)
    responses.reset()  # a second network call would now fail
    second = search.search_web("KCL Electronics Society", max_results=5)

    assert first == second
