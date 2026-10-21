from pathlib import Path

import pytest

from outreach_mcp import emails, insights, leads, preference_model
from outreach_mcp.insights import StyleTrend


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(leads, "DATABASE_PATH", db_path)
    monkeypatch.setattr(preference_model, "DATABASE_PATH", db_path)
    monkeypatch.setattr(preference_model, "MODEL_PATH", str(tmp_path / "model.pkl"))
    monkeypatch.setattr(emails, "DATABASE_PATH", db_path)
    monkeypatch.setattr(insights, "DATABASE_PATH", db_path)


def _save(company: str, event_fit: float = 3.0) -> None:
    leads.save_lead(
        "event-1",
        leads.LeadProfile(
            company=company,
            contact_type="none",
            geography="london",
            event_fit=event_fit,
            ask_realism=3.0,
            n_channels=1,
        ),
    )


def test_rubric_weights_always_present() -> None:
    result = insights.insights()
    assert "event_fit" in result.rubric_weights


def test_learned_weights_none_before_model_trained() -> None:
    result = insights.insights()
    assert result.learned_weights is None


def test_approval_rate_none_with_no_decisions() -> None:
    result = insights.insights()
    assert result.approval_rate is None


def test_approval_rate_reflects_logged_decisions() -> None:
    _save("A")
    _save("B")
    _save("C")
    preference_model.log_decision("event-1", "A", "approve")
    preference_model.log_decision("event-1", "B", "approve")
    preference_model.log_decision("event-1", "C", "skip")

    result = insights.insights()

    assert result.approval_rate == pytest.approx(2 / 3)
    assert result.decisions == {"approve": 2, "skip": 1, "dnc": 0}


def test_dnc_decisions_excluded_from_approval_rate() -> None:
    _save("A")
    _save("B")
    preference_model.log_decision("event-1", "A", "approve")
    preference_model.log_decision("event-1", "B", "dnc")

    result = insights.insights()

    assert result.approval_rate == 1.0


def test_decisions_until_model_trains_counts_down() -> None:
    _save("A")
    preference_model.log_decision("event-1", "A", "approve")

    result = insights.insights()

    assert result.decisions_until_model_trains == preference_model.MIN_DECISIONS_TO_TRAIN - 1


def test_learned_weights_present_once_model_trained() -> None:
    for i in range(preference_model.MIN_DECISIONS_TO_TRAIN):
        _save(f"C{i}", event_fit=5.0 if i % 2 == 0 else 1.0)
        preference_model.log_decision("event-1", f"C{i}", "approve" if i % 2 == 0 else "skip")

    result = insights.insights()

    assert result.learned_weights is not None
    assert "event_fit" in result.learned_weights


def test_style_trend_empty_with_no_emails() -> None:
    result = insights.insights()
    assert result.style == StyleTrend(
        count=0, overall_avg=None, recent_avg=None, due_for_style_review=False
    )


def test_style_trend_reflects_logged_emails() -> None:
    emails.log_email("event-1", "Acme", "draft", "draft")  # similarity 1.0
    emails.log_email("event-1", "Acme", "draft", "totally different final text")

    result = insights.insights()

    assert result.style.count == 2
    assert result.style.overall_avg is not None


def test_due_for_style_review_fires_every_ten_emails() -> None:
    for i in range(10):
        emails.log_email("event-1", f"Company{i}", "draft", "final")

    result = insights.insights()

    assert result.style.due_for_style_review is True


def test_not_due_for_style_review_between_multiples_of_ten() -> None:
    for i in range(7):
        emails.log_email("event-1", f"Company{i}", "draft", "final")

    result = insights.insights()

    assert result.style.due_for_style_review is False
