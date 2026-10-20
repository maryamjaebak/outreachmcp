from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass, field

from outreach_mcp.fetch import get_full_text, was_seen
from outreach_mcp.scoring import ScoreResult, compute_score, load_config

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./outreach.db")

_VALID_CONTACT_TYPES = {"named", "inbox", "form", "none"}
_VALID_GEOGRAPHIES = {"london", "uk", "intl_uk_ops", "intl"}

_LEADS_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    event_id TEXT NOT NULL,
    company TEXT NOT NULL,
    score REAL NOT NULL,
    features TEXT NOT NULL,
    contact_name TEXT,
    contact_email TEXT,
    email_verified INTEGER NOT NULL,
    contact_type TEXT NOT NULL,
    geography TEXT NOT NULL,
    evidence_urls TEXT NOT NULL,
    dnc INTEGER NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (event_id, company)
)
"""


class LeadValidationError(Exception):
    pass


@dataclass
class LeadProfile:
    company: str
    contact_type: str
    geography: str
    event_fit: float
    ask_realism: float
    n_channels: int
    contact_name: str | None = None
    contact_email: str | None = None
    email_source_url: str | None = None
    evidence_urls: list[str] = field(default_factory=list)
    warm_connection: bool = False
    propensity: float = 0.25
    propensity_signal: bool = False
    dnc: bool = False


@dataclass(frozen=True)
class SaveLeadResult:
    company: str
    score: float
    features: dict[str, float]
    dropped_evidence_urls: list[str]
    email_verified: bool


def _validate(profile: LeadProfile) -> None:
    if not profile.company.strip():
        raise LeadValidationError("company is required")
    if profile.contact_type not in _VALID_CONTACT_TYPES:
        raise LeadValidationError(f"invalid contact_type: {profile.contact_type!r}")
    if profile.geography not in _VALID_GEOGRAPHIES:
        raise LeadValidationError(f"invalid geography: {profile.geography!r}")
    if not 0 <= profile.event_fit <= 5:
        raise LeadValidationError("event_fit must be between 0 and 5")
    if not 0 <= profile.ask_realism <= 5:
        raise LeadValidationError("ask_realism must be between 0 and 5")
    if profile.n_channels < 0:
        raise LeadValidationError("n_channels cannot be negative")
    if not 0 <= profile.propensity <= 1:
        raise LeadValidationError("propensity must be between 0 and 1")
    if profile.contact_email and not profile.email_source_url:
        raise LeadValidationError("contact_email requires email_source_url")


def _verify_email(profile: LeadProfile) -> bool:
    if not profile.contact_email or not profile.email_source_url:
        return False
    if not was_seen(DATABASE_PATH, profile.email_source_url):
        return False
    page_text = get_full_text(profile.email_source_url)
    if page_text is None:
        return False
    return profile.contact_email in page_text


def _upsert(
    event_id: str,
    profile: LeadProfile,
    result: ScoreResult,
    kept_urls: list[str],
    email_verified: bool,
) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(_LEADS_SCHEMA)
        conn.execute(
            """
            INSERT INTO leads (
                event_id, company, score, features, contact_name, contact_email,
                email_verified, contact_type, geography, evidence_urls, dnc, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (event_id, company) DO UPDATE SET
                score = excluded.score,
                features = excluded.features,
                contact_name = excluded.contact_name,
                contact_email = excluded.contact_email,
                email_verified = excluded.email_verified,
                contact_type = excluded.contact_type,
                geography = excluded.geography,
                evidence_urls = excluded.evidence_urls,
                dnc = excluded.dnc,
                updated_at = excluded.updated_at
            """,
            (
                event_id,
                profile.company,
                result.total,
                json.dumps(result.features),
                profile.contact_name,
                profile.contact_email,
                int(email_verified),
                profile.contact_type,
                profile.geography,
                json.dumps(kept_urls),
                int(profile.dnc),
                time.time(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def save_lead(event_id: str, profile: LeadProfile) -> SaveLeadResult:
    """Validate, score, and upsert a lead profile for an event.

    Evidence URLs that were never fetched via `fetch_page` are dropped. An
    email is only trusted if its source page was fetched and the email
    string appears verbatim in that page's (still-cached) extracted text.
    """
    _validate(profile)

    kept_urls = [url for url in profile.evidence_urls if was_seen(DATABASE_PATH, url)]
    dropped_urls = [url for url in profile.evidence_urls if url not in kept_urls]

    email_verified = _verify_email(profile)

    config = load_config()
    result = compute_score(
        event_fit=profile.event_fit,
        propensity=profile.propensity,
        propensity_signal=profile.propensity_signal,
        warm_connection=profile.warm_connection,
        contact_type=profile.contact_type,
        email_verified=email_verified,
        geography=profile.geography,
        ask_realism=profile.ask_realism,
        n_channels=profile.n_channels,
        dnc=profile.dnc,
        config=config,
    )

    _upsert(event_id, profile, result, kept_urls, email_verified)

    return SaveLeadResult(
        company=profile.company,
        score=result.total,
        features=result.features,
        dropped_evidence_urls=dropped_urls,
        email_verified=email_verified,
    )
