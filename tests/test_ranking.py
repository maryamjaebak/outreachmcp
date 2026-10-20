import random
from pathlib import Path

import pytest

from outreach_mcp import fetch, leads, ranking


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(leads, "DATABASE_PATH", db_path)
    monkeypatch.setattr(fetch, "DATABASE_PATH", db_path)
    monkeypatch.setattr(ranking, "DATABASE_PATH", db_path)


def _save(company: str, event_fit: float, dnc: bool = False) -> None:
    profile = leads.LeadProfile(
        company=company,
        contact_type="none",
        geography="london",
        event_fit=event_fit,
        ask_realism=3.0,
        n_channels=1,
        dnc=dnc,
    )
    leads.save_lead("event-1", profile)


def test_returns_empty_list_for_unknown_event() -> None:
    assert ranking.rank_leads("no-such-event") == []


def test_sorts_by_score_descending() -> None:
    _save("Low", event_fit=1.0)
    _save("High", event_fit=5.0)
    _save("Mid", event_fit=3.0)

    ranked = ranking.rank_leads("event-1")

    assert [r.company for r in ranked] == ["High", "Mid", "Low"]


def test_excludes_dnc_leads() -> None:
    _save("Keep", event_fit=3.0)
    _save("DoNotContact", event_fit=5.0, dnc=True)

    ranked = ranking.rank_leads("event-1")

    assert [r.company for r in ranked] == ["Keep"]


def test_returns_all_leads_when_under_limit_with_no_explore() -> None:
    _save("A", event_fit=1.0)
    _save("B", event_fit=2.0)

    ranked = ranking.rank_leads("event-1", limit=15)

    assert len(ranked) == 2
    assert all(not r.explore for r in ranked)


def test_respects_limit_and_marks_explore_slots() -> None:
    for i in range(10):
        _save(f"Company{i}", event_fit=float(i % 6))

    ranked = ranking.rank_leads("event-1", limit=5, rng=random.Random(0))

    assert len(ranked) == 5
    assert sum(1 for r in ranked if r.explore) == 1  # round(5 * 0.2)


def test_exploit_slots_are_not_marked_explore() -> None:
    for i in range(10):
        _save(f"Company{i}", event_fit=float(i % 6))

    ranked = ranking.rank_leads("event-1", limit=5, rng=random.Random(0))

    exploit_count = 5 - 1
    top_scores = sorted((r.score for r in ranked if not r.explore), reverse=True)
    assert len(top_scores) == exploit_count


def test_feature_breakdown_is_included_per_lead() -> None:
    _save("Acme", event_fit=4.0)

    ranked = ranking.rank_leads("event-1")

    assert "event_fit" in ranked[0].features
