from __future__ import annotations

import json
import random
import sqlite3
from dataclasses import dataclass, replace

from outreach_mcp.leads import DATABASE_PATH, LEADS_SCHEMA

EXPLORE_FRACTION = 0.2


@dataclass(frozen=True)
class RankedLead:
    company: str
    score: float
    features: dict[str, float]
    contact_name: str | None
    contact_email: str | None
    email_verified: bool
    contact_type: str
    geography: str
    evidence_urls: list[str]
    explore: bool


def _fetch_candidates(event_id: str) -> list[RankedLead]:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(LEADS_SCHEMA)
        rows = conn.execute(
            """
            SELECT company, score, features, contact_name, contact_email,
                   email_verified, contact_type, geography, evidence_urls
            FROM leads
            WHERE event_id = ? AND dnc = 0
            """,
            (event_id,),
        ).fetchall()
    finally:
        conn.close()

    return [
        RankedLead(
            company=row[0],
            score=row[1],
            features=json.loads(row[2]),
            contact_name=row[3],
            contact_email=row[4],
            email_verified=bool(row[5]),
            contact_type=row[6],
            geography=row[7],
            evidence_urls=json.loads(row[8]),
            explore=False,
        )
        for row in rows
    ]


def rank_leads(
    event_id: str, limit: int = 15, rng: random.Random | None = None
) -> list[RankedLead]:
    """Rank saved leads for an event by score, with ~20% explore slots.

    No learned preference model exists yet (that needs `log_decision` data to
    train one), so this is rubric-only for now: ranks purely by the score
    `save_lead` already computed. DNC leads are excluded
    entirely, not just scored to zero. Once enough decisions exist, blend in
    `(1-alpha)*rubric + alpha*P(approve)*100` here instead of sorting by
    `score` directly.
    """
    rng = rng or random.Random()
    candidates = _fetch_candidates(event_id)
    ranked_by_score = sorted(candidates, key=lambda c: c.score, reverse=True)

    if len(ranked_by_score) <= limit:
        return ranked_by_score

    explore_count = round(limit * EXPLORE_FRACTION)
    exploit_count = limit - explore_count

    exploit = ranked_by_score[:exploit_count]
    tail = ranked_by_score[exploit_count:]
    explore = [replace(c, explore=True) for c in rng.sample(tail, min(explore_count, len(tail)))]

    return sorted(exploit + explore, key=lambda c: c.score, reverse=True)
