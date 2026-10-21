from __future__ import annotations

import json
import os
import pickle
import sqlite3
import time
from pathlib import Path

from sklearn.linear_model import LogisticRegression

from outreach_mcp.leads import LEADS_SCHEMA
from outreach_mcp.scoring import FEATURE_NAMES

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./outreach.db")
MODEL_PATH = os.environ.get("MODEL_PATH", "./preference_model.pkl")
MIN_DECISIONS_TO_TRAIN = 40

DECISIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    event_id TEXT NOT NULL,
    company TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT,
    features TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (event_id, company)
)
"""

_VALID_ACTIONS = {"approve", "skip", "dnc"}


class DecisionValidationError(Exception):
    pass


def log_decision(event_id: str, company: str, action: str, reason: str = "") -> None:
    """Record an approve/skip/dnc decision on a previously `save_lead`'d lead.

    Snapshots the lead's current feature vector into the decision row, since
    training must always use the vector that was actually judged, even if
    the lead gets re-saved with different features later. A "dnc" decision
    also flips the lead's own `dnc` flag, so `rank_leads` stops surfacing it.
    Retrains the preference model once enough approve/skip decisions exist.
    """
    if action not in _VALID_ACTIONS:
        raise DecisionValidationError(
            f"invalid action: {action!r}, must be one of {_VALID_ACTIONS}"
        )

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(DECISIONS_SCHEMA)
        conn.execute(LEADS_SCHEMA)
        row = conn.execute(
            "SELECT features FROM leads WHERE event_id = ? AND company = ?",
            (event_id, company),
        ).fetchone()
        if row is None:
            raise DecisionValidationError(
                f"no saved lead for event_id={event_id!r}, company={company!r}; "
                "call save_lead first"
            )
        features_json = row[0]

        conn.execute(
            """
            INSERT INTO decisions (event_id, company, action, reason, features, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (event_id, company) DO UPDATE SET
                action = excluded.action,
                reason = excluded.reason,
                features = excluded.features,
                created_at = excluded.created_at
            """,
            (event_id, company, action, reason, features_json, time.time()),
        )

        if action == "dnc":
            conn.execute(
                "UPDATE leads SET dnc = 1 WHERE event_id = ? AND company = ?",
                (event_id, company),
            )

        conn.commit()
    finally:
        conn.close()

    _maybe_retrain()


def _training_data() -> tuple[list[list[float]], list[int]]:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(DECISIONS_SCHEMA)
        rows = conn.execute(
            "SELECT features, action FROM decisions WHERE action IN ('approve', 'skip')"
        ).fetchall()
    finally:
        conn.close()

    x: list[list[float]] = []
    y: list[int] = []
    for features_json, action in rows:
        features = json.loads(features_json)
        x.append([features[name] for name in FEATURE_NAMES])
        y.append(1 if action == "approve" else 0)
    return x, y


def count_trainable_decisions() -> int:
    """Count logged approve/skip decisions (global, not per-event) — `dnc` excluded."""
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(DECISIONS_SCHEMA)
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM decisions WHERE action IN ('approve', 'skip')"
        ).fetchone()
    finally:
        conn.close()
    return int(count)


def _maybe_retrain() -> None:
    x, y = _training_data()
    if len(x) < MIN_DECISIONS_TO_TRAIN or len(set(y)) < 2:
        return  # not enough data yet, or only one class seen so far
    model = LogisticRegression(C=0.5)
    model.fit(x, y)
    Path(MODEL_PATH).write_bytes(pickle.dumps(model))


def load_model() -> LogisticRegression | None:
    path = Path(MODEL_PATH)
    if not path.exists():
        return None
    model: LogisticRegression = pickle.loads(path.read_bytes())
    return model


def predict_approval_probability(features: dict[str, float]) -> float | None:
    """P(approve) for a feature vector, or None if no model has been trained yet."""
    model = load_model()
    if model is None:
        return None
    x = [[features[name] for name in FEATURE_NAMES]]
    return float(model.predict_proba(x)[0][1])
