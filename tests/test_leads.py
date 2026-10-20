import sqlite3
import time
from pathlib import Path

import pytest

from outreach_mcp import fetch, leads
from outreach_mcp.cache import Cache


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(leads, "DATABASE_PATH", db_path)
    monkeypatch.setattr(fetch, "DATABASE_PATH", db_path)


def _base_profile(**overrides: object) -> leads.LeadProfile:
    defaults: dict[str, object] = {
        "company": "Acme Corp",
        "contact_type": "none",
        "geography": "london",
        "event_fit": 3.0,
        "ask_realism": 3.0,
        "n_channels": 1,
    }
    defaults.update(overrides)
    return leads.LeadProfile(**defaults)  # type: ignore[arg-type]


def test_rejects_blank_company() -> None:
    with pytest.raises(leads.LeadValidationError):
        leads.save_lead("event-1", _base_profile(company="  "))


def test_rejects_invalid_contact_type() -> None:
    with pytest.raises(leads.LeadValidationError):
        leads.save_lead("event-1", _base_profile(contact_type="carrier-pigeon"))


def test_rejects_invalid_geography() -> None:
    with pytest.raises(leads.LeadValidationError):
        leads.save_lead("event-1", _base_profile(geography="moon"))


def test_rejects_email_without_source_url() -> None:
    with pytest.raises(leads.LeadValidationError):
        leads.save_lead("event-1", _base_profile(contact_email="a@acme.com"))


def test_drops_evidence_urls_never_fetched() -> None:
    profile = _base_profile(evidence_urls=["https://never-fetched.example/page"])

    result = leads.save_lead("event-1", profile)

    assert result.dropped_evidence_urls == ["https://never-fetched.example/page"]


def test_keeps_evidence_urls_that_were_fetched(monkeypatch: pytest.MonkeyPatch) -> None:
    from outreach_mcp.seen import mark_seen

    url = "https://real.example/page"
    mark_seen(leads.DATABASE_PATH, url)
    profile = _base_profile(evidence_urls=[url])

    result = leads.save_lead("event-1", profile)

    assert result.dropped_evidence_urls == []


def test_email_unverified_when_source_page_never_fetched() -> None:
    profile = _base_profile(
        contact_type="named",
        contact_email="jane@acme.com",
        email_source_url="https://acme.example/team",
    )

    result = leads.save_lead("event-1", profile)

    assert result.email_verified is False


def test_email_unverified_when_not_present_on_fetched_page() -> None:
    from outreach_mcp.seen import mark_seen

    url = "https://acme.example/team"
    mark_seen(leads.DATABASE_PATH, url)
    Cache(leads.DATABASE_PATH).set(f"page_full:{url}", "no contact info here", 3600)

    profile = _base_profile(
        contact_type="named",
        contact_email="jane@acme.com",
        email_source_url=url,
    )

    result = leads.save_lead("event-1", profile)

    assert result.email_verified is False


def test_email_verified_when_present_on_fetched_page() -> None:
    from outreach_mcp.seen import mark_seen

    url = "https://acme.example/team"
    mark_seen(leads.DATABASE_PATH, url)
    Cache(leads.DATABASE_PATH).set(f"page_full:{url}", "Contact: jane@acme.com", 3600)

    profile = _base_profile(
        contact_type="named",
        contact_email="jane@acme.com",
        email_source_url=url,
    )

    result = leads.save_lead("event-1", profile)

    assert result.email_verified is True


def test_email_unverified_when_cache_expired_even_if_seen() -> None:
    from outreach_mcp.seen import mark_seen

    url = "https://acme.example/team"
    mark_seen(leads.DATABASE_PATH, url)
    cache = Cache(leads.DATABASE_PATH)
    cache.set(f"page_full:{url}", "Contact: jane@acme.com", ttl_seconds=0.01)
    time.sleep(0.05)

    profile = _base_profile(
        contact_type="named",
        contact_email="jane@acme.com",
        email_source_url=url,
    )

    result = leads.save_lead("event-1", profile)

    assert result.email_verified is False


def test_save_lead_upserts_into_leads_table() -> None:
    leads.save_lead("event-1", _base_profile(event_fit=2.0))
    leads.save_lead("event-1", _base_profile(event_fit=5.0))

    conn = sqlite3.connect(leads.DATABASE_PATH)
    rows = conn.execute("SELECT company, score FROM leads WHERE event_id = 'event-1'").fetchall()
    conn.close()

    assert len(rows) == 1  # second save updated the row, didn't insert a new one
    assert rows[0][0] == "Acme Corp"


def test_dnc_lead_scores_zero_and_is_saved() -> None:
    result = leads.save_lead("event-1", _base_profile(dnc=True))

    assert result.score == 0.0

    conn = sqlite3.connect(leads.DATABASE_PATH)
    row = conn.execute("SELECT dnc FROM leads WHERE event_id = 'event-1'").fetchone()
    conn.close()

    assert row[0] == 1
