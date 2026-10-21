from __future__ import annotations

import json
import os
import sqlite3
import time

from outreach_mcp.bandit import OUTCOME_REWARDS
from outreach_mcp.bandit import adjust_reward as _adjust_reward
from outreach_mcp.bandit import update as _bandit_update
from outreach_mcp.leads import LEADS_SCHEMA

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./outreach.db")

OUTCOMES_SCHEMA = """
CREATE TABLE IF NOT EXISTS outcomes (
    event_id TEXT NOT NULL,
    company TEXT NOT NULL,
    outcome TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (event_id, company)
)
"""

_VALID_OUTCOMES = set(OUTCOME_REWARDS)


class OutcomeValidationError(Exception):
    pass


def log_outcome(event_id: str, company: str, outcome: str) -> None:
    """Record an outcome (replied/meeting/sponsored/declined) and update the bandit.

    Needs a previously `save_lead`'d lead to pull its feature vector from —
    the bandit learns which *feature regions* tend to convert, not which
    specific companies. Re-logging an outcome for the same lead (e.g.
    "replied" later becomes "sponsored") adjusts the bandit's reward for
    that observation instead of double-counting its context.
    """
    if outcome not in _VALID_OUTCOMES:
        raise OutcomeValidationError(
            f"invalid outcome: {outcome!r}, must be one of {_VALID_OUTCOMES}"
        )

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(OUTCOMES_SCHEMA)
        conn.execute(LEADS_SCHEMA)
        lead_row = conn.execute(
            "SELECT features FROM leads WHERE event_id = ? AND company = ?",
            (event_id, company),
        ).fetchone()
        if lead_row is None:
            raise OutcomeValidationError(
                f"no saved lead for event_id={event_id!r}, company={company!r}; "
                "call save_lead first"
            )
        features = json.loads(lead_row[0])

        existing = conn.execute(
            "SELECT outcome FROM outcomes WHERE event_id = ? AND company = ?",
            (event_id, company),
        ).fetchone()

        conn.execute(
            """
            INSERT INTO outcomes (event_id, company, outcome, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (event_id, company) DO UPDATE SET
                outcome = excluded.outcome,
                created_at = excluded.created_at
            """,
            (event_id, company, outcome, time.time()),
        )
        conn.commit()
    finally:
        conn.close()

    if existing is not None:
        _adjust_reward(features, OUTCOME_REWARDS[existing[0]], OUTCOME_REWARDS[outcome])
    else:
        _bandit_update(features, OUTCOME_REWARDS[outcome])
