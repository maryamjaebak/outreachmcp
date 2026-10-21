from __future__ import annotations

import json
import random
import sqlite3
from dataclasses import dataclass, replace

import numpy as np

from outreach_mcp.bandit import has_outcomes, sample_score
from outreach_mcp.leads import DATABASE_PATH, LEADS_SCHEMA
from outreach_mcp.preference_model import count_trainable_decisions, predict_approval_probability

EXPLORE_FRACTION = 0.2
MAX_LEARNED_WEIGHT = 0.7
DECISIONS_FOR_MAX_WEIGHT = 200


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


def _blend_with_learned_model(lead: RankedLead, n_decisions: int) -> RankedLead:
    alpha = min(MAX_LEARNED_WEIGHT, n_decisions / DECISIONS_FOR_MAX_WEIGHT)
    if alpha <= 0:
        return lead
    p_approve = predict_approval_probability(lead.features)
    if p_approve is None:
        return lead
    blended = (1 - alpha) * lead.score + alpha * p_approve * 100
    return replace(lead, score=blended)


def _select_explore(
    tail: list[RankedLead],
    explore_count: int,
    rng: random.Random,
    np_rng: np.random.Generator | None,
) -> list[RankedLead]:
    if explore_count <= 0 or not tail:
        return []
    explore_count = min(explore_count, len(tail))
    if has_outcomes():
        # Thompson sampling: favors under-explored feature regions, not
        # just whatever currently scores highest.
        return sorted(tail, key=lambda c: sample_score(c.features, np_rng), reverse=True)[
            :explore_count
        ]
    return rng.sample(tail, explore_count)


def rank_leads(
    event_id: str,
    limit: int = 15,
    rng: random.Random | None = None,
    np_rng: np.random.Generator | None = None,
) -> list[RankedLead]:
    """Rank saved leads for an event by score, with ~20% explore slots.

    Final score blends the rubric with the learned preference model:
    `(1-alpha)*rubric + alpha*P(approve)*100`, where `alpha` grows with the
    number of logged approve/skip decisions (capped at
    `MAX_LEARNED_WEIGHT`) and `P(approve)` needs a trained model (see
    `preference_model.py` — untrained until 40+ decisions exist, in which
    case this falls back to the rubric score untouched). DNC leads are
    excluded entirely, not just scored to zero.

    Explore slots are chosen via Thompson sampling on the contextual bandit
    (see `bandit.py`) once any outcome has been logged; before that, there's
    nothing for the bandit to have learned yet, so they're a plain random
    sample of the tail instead.
    """
    rng = rng or random.Random()
    candidates = _fetch_candidates(event_id)
    n_decisions = count_trainable_decisions()
    blended = [_blend_with_learned_model(c, n_decisions) for c in candidates]
    ranked_by_score = sorted(blended, key=lambda c: c.score, reverse=True)

    if len(ranked_by_score) <= limit:
        return ranked_by_score

    explore_count = round(limit * EXPLORE_FRACTION)
    exploit_count = limit - explore_count

    exploit = ranked_by_score[:exploit_count]
    tail = ranked_by_score[exploit_count:]
    explore = [replace(c, explore=True) for c in _select_explore(tail, explore_count, rng, np_rng)]

    return sorted(exploit + explore, key=lambda c: c.score, reverse=True)
