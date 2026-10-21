import sqlite3
from pathlib import Path

import pytest

from outreach_mcp import emails


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(emails, "DATABASE_PATH", str(tmp_path / "test.db"))


def _mark_replied(company: str) -> None:
    conn = sqlite3.connect(emails.DATABASE_PATH)
    conn.execute("UPDATE emails SET replied = 1 WHERE company = ?", (company,))
    conn.commit()
    conn.close()


def test_log_email_returns_similarity_between_zero_and_one() -> None:
    similarity = emails.log_email("event-1", "Acme", "Hello there", "Hello there!")
    assert 0.0 <= similarity <= 1.0


def test_log_email_identical_draft_and_final_is_similarity_one() -> None:
    similarity = emails.log_email("event-1", "Acme", "Same text", "Same text")
    assert similarity == 1.0


def test_style_examples_prefers_same_company_first() -> None:
    emails.log_email("event-1", "Acme", "draft 1", "Acme final 1")
    emails.log_email("event-2", "Other", "draft 2", "Other final 2")

    examples = emails.style_examples("event-3", "Acme", k=1)

    assert len(examples) == 1
    assert examples[0].final == "Acme final 1"


def test_style_examples_falls_back_to_global_pool_when_company_has_none() -> None:
    emails.log_email("event-1", "Other", "draft", "Other final")

    examples = emails.style_examples("event-2", "NeverEmailed", k=3)

    assert len(examples) == 1
    assert examples[0].final == "Other final"


def test_style_examples_prioritizes_replied_over_recency() -> None:
    emails.log_email("event-1", "Acme", "d1", "final 1 (not replied)")
    emails.log_email("event-1", "Acme", "d2", "final 2 (replied)")
    _mark_replied("Acme")  # marks all Acme rows replied for this test's simplicity... see below
    conn = sqlite3.connect(emails.DATABASE_PATH)
    conn.execute("UPDATE emails SET replied = 0 WHERE final LIKE '%not replied%'")
    conn.commit()
    conn.close()

    examples = emails.style_examples("event-2", "Acme", k=1)

    assert examples[0].final == "final 2 (replied)"
    assert examples[0].replied is True


def test_style_examples_respects_k() -> None:
    for i in range(5):
        emails.log_email("event-1", "Acme", f"draft {i}", f"final {i}")

    examples = emails.style_examples("event-1", "Acme", k=2)

    assert len(examples) == 2
