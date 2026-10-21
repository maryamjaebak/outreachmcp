from pathlib import Path

import pytest

from outreach_mcp import fetch, leads, preference_model
from outreach_mcp.scoring import FEATURE_NAMES


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = str(tmp_path / "test.db")
    model_path = str(tmp_path / "model.pkl")
    monkeypatch.setattr(leads, "DATABASE_PATH", db_path)
    monkeypatch.setattr(fetch, "DATABASE_PATH", db_path)
    monkeypatch.setattr(preference_model, "DATABASE_PATH", db_path)
    monkeypatch.setattr(preference_model, "MODEL_PATH", model_path)


def _save(company: str, event_fit: float) -> None:
    profile = leads.LeadProfile(
        company=company,
        contact_type="none",
        geography="london",
        event_fit=event_fit,
        ask_realism=3.0,
        n_channels=1,
    )
    leads.save_lead("event-1", profile)


def test_rejects_invalid_action() -> None:
    _save("Acme", 3.0)
    with pytest.raises(preference_model.DecisionValidationError):
        preference_model.log_decision("event-1", "Acme", "maybe")


def test_rejects_decision_on_unsaved_lead() -> None:
    with pytest.raises(preference_model.DecisionValidationError):
        preference_model.log_decision("event-1", "NeverSaved", "approve")


def test_logging_dnc_flips_the_leads_dnc_flag() -> None:
    import sqlite3

    _save("Acme", 3.0)
    preference_model.log_decision("event-1", "Acme", "dnc")

    conn = sqlite3.connect(leads.DATABASE_PATH)
    row = conn.execute(
        "SELECT dnc FROM leads WHERE event_id = 'event-1' AND company = 'Acme'"
    ).fetchone()
    conn.close()

    assert row[0] == 1


def test_count_trainable_decisions_excludes_dnc() -> None:
    _save("A", 1.0)
    _save("B", 2.0)
    _save("C", 3.0)
    preference_model.log_decision("event-1", "A", "approve")
    preference_model.log_decision("event-1", "B", "skip")
    preference_model.log_decision("event-1", "C", "dnc")

    assert preference_model.count_trainable_decisions() == 2


def test_no_model_trained_below_threshold() -> None:
    _save("Acme", 3.0)
    preference_model.log_decision("event-1", "Acme", "approve")

    assert preference_model.load_model() is None


def test_predict_approval_probability_none_without_trained_model() -> None:
    features = {name: 0.5 for name in FEATURE_NAMES}
    assert preference_model.predict_approval_probability(features) is None


def test_trains_model_once_threshold_reached_with_both_classes() -> None:
    for i in range(preference_model.MIN_DECISIONS_TO_TRAIN):
        company = f"Company{i}"
        _save(company, event_fit=5.0 if i % 2 == 0 else 1.0)
        action = "approve" if i % 2 == 0 else "skip"
        preference_model.log_decision("event-1", company, action)

    model = preference_model.load_model()
    assert model is not None

    features = {name: 1.0 for name in FEATURE_NAMES}
    probability = preference_model.predict_approval_probability(features)
    assert probability is not None
    assert 0.0 <= probability <= 1.0
