import random
from pathlib import Path

import pytest

from outreach_mcp import fetch, leads, preference_model, ranking


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(leads, "DATABASE_PATH", db_path)
    monkeypatch.setattr(fetch, "DATABASE_PATH", db_path)
    monkeypatch.setattr(ranking, "DATABASE_PATH", db_path)
    monkeypatch.setattr(preference_model, "DATABASE_PATH", db_path)
    monkeypatch.setattr(preference_model, "MODEL_PATH", str(tmp_path / "model.pkl"))


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


def test_score_unblended_without_a_trained_model() -> None:
    _save("Acme", event_fit=4.0)

    rubric_score = leads.save_lead(
        "event-1",
        leads.LeadProfile(
            company="Acme",
            contact_type="none",
            geography="london",
            event_fit=4.0,
            ask_realism=3.0,
            n_channels=1,
        ),
    ).score

    ranked_score = ranking.rank_leads("event-1")[0].score

    assert preference_model.load_model() is None
    assert ranked_score == rubric_score


def test_score_blends_toward_learned_model_once_trained() -> None:
    _save("Acme", event_fit=3.0)
    acme_rubric_score = ranking.rank_leads("event-1")[0].score

    for i in range(preference_model.MIN_DECISIONS_TO_TRAIN):
        company = f"Company{i}"
        profile = leads.LeadProfile(
            company=company,
            contact_type="none",
            geography="london",
            event_fit=5.0 if i % 2 == 0 else 1.0,
            ask_realism=3.0,
            n_channels=1,
        )
        leads.save_lead("event-1", profile)
        preference_model.log_decision("event-1", company, "approve" if i % 2 == 0 else "skip")
    n_decisions = preference_model.count_trainable_decisions()
    assert preference_model.load_model() is not None

    acme = next(r for r in ranking.rank_leads("event-1", limit=1000) if r.company == "Acme")
    p_approve = preference_model.predict_approval_probability(acme.features)
    assert p_approve is not None

    alpha = min(ranking.MAX_LEARNED_WEIGHT, n_decisions / ranking.DECISIONS_FOR_MAX_WEIGHT)
    expected = (1 - alpha) * acme_rubric_score + alpha * p_approve * 100
    assert acme.score == pytest.approx(expected)
    assert alpha > 0  # otherwise this test isn't exercising the blend at all


def test_dnc_via_log_decision_removes_lead_from_ranking() -> None:
    _save("Acme", event_fit=4.0)
    preference_model.log_decision("event-1", "Acme", "dnc")

    ranked = ranking.rank_leads("event-1")

    assert ranked == []
