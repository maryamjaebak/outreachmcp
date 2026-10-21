from pathlib import Path

import numpy as np
import pytest

from outreach_mcp import bandit, fetch, leads, outcomes


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(leads, "DATABASE_PATH", db_path)
    monkeypatch.setattr(fetch, "DATABASE_PATH", db_path)
    monkeypatch.setattr(outcomes, "DATABASE_PATH", db_path)
    monkeypatch.setattr(bandit, "BANDIT_PATH", str(tmp_path / "bandit.pkl"))


def _save(company: str) -> None:
    profile = leads.LeadProfile(
        company=company,
        contact_type="none",
        geography="london",
        event_fit=3.0,
        ask_realism=3.0,
        n_channels=1,
    )
    leads.save_lead("event-1", profile)


def test_rejects_invalid_outcome() -> None:
    _save("Acme")
    with pytest.raises(outcomes.OutcomeValidationError):
        outcomes.log_outcome("event-1", "Acme", "ghosted")


def test_rejects_outcome_on_unsaved_lead() -> None:
    with pytest.raises(outcomes.OutcomeValidationError):
        outcomes.log_outcome("event-1", "NeverSaved", "replied")


def test_log_outcome_marks_bandit_as_having_outcomes() -> None:
    _save("Acme")
    assert bandit.has_outcomes() is False

    outcomes.log_outcome("event-1", "Acme", "replied")

    assert bandit.has_outcomes() is True


def test_relogging_outcome_adjusts_reward_without_double_counting() -> None:
    _save("Acme")
    outcomes.log_outcome("event-1", "Acme", "replied")
    a_after_first, _ = bandit._load_state()

    outcomes.log_outcome("event-1", "Acme", "sponsored")
    a_after_second, _ = bandit._load_state()

    # the context (feature vector) was only observed once, so the
    # uncertainty matrix shouldn't change on a re-log, only the reward
    assert np.allclose(a_after_first, a_after_second)


def test_sponsored_contributes_more_reward_than_declined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _save("Sponsor")
    outcomes.log_outcome("event-1", "Sponsor", "sponsored")
    _, b_after_sponsored = bandit._load_state()

    monkeypatch.setattr(bandit, "BANDIT_PATH", str(tmp_path / "bandit2.pkl"))  # fresh bandit
    _save("Decliner")
    outcomes.log_outcome("event-1", "Decliner", "declined")
    _, b_after_declined = bandit._load_state()

    assert np.sum(b_after_sponsored) > np.sum(b_after_declined)
