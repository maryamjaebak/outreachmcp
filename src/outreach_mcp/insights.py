from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from outreach_mcp.emails import EMAILS_SCHEMA
from outreach_mcp.preference_model import DECISIONS_SCHEMA, MIN_DECISIONS_TO_TRAIN, load_model
from outreach_mcp.scoring import FEATURE_NAMES, load_config

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./outreach.db")
STYLE_REVIEW_INTERVAL = 10


@dataclass(frozen=True)
class StyleTrend:
    count: int
    overall_avg: float | None
    recent_avg: float | None
    due_for_style_review: bool


@dataclass(frozen=True)
class Insights:
    rubric_weights: dict[str, float]
    learned_weights: dict[str, float] | None
    decisions: dict[str, int]
    approval_rate: float | None
    decisions_until_model_trains: int
    style: StyleTrend


def _decision_counts() -> dict[str, int]:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(DECISIONS_SCHEMA)
        rows = conn.execute("SELECT action, COUNT(*) FROM decisions GROUP BY action").fetchall()
    finally:
        conn.close()
    counts = {"approve": 0, "skip": 0, "dnc": 0}
    counts.update(dict(rows))
    return counts


def _learned_weights() -> dict[str, float] | None:
    model = load_model()
    if model is None:
        return None
    coefs = model.coef_[0]
    return dict(zip(FEATURE_NAMES, (float(c) for c in coefs), strict=True))


def _style_similarity_trend() -> StyleTrend:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(EMAILS_SCHEMA)
        rows = conn.execute("SELECT similarity FROM emails ORDER BY created_at ASC").fetchall()
    finally:
        conn.close()

    similarities = [row[0] for row in rows]
    count = len(similarities)
    if count == 0:
        return StyleTrend(count=0, overall_avg=None, recent_avg=None, due_for_style_review=False)

    recent = similarities[-STYLE_REVIEW_INTERVAL:]
    return StyleTrend(
        count=count,
        overall_avg=sum(similarities) / count,
        recent_avg=sum(recent) / len(recent),
        due_for_style_review=count % STYLE_REVIEW_INTERVAL == 0,
    )


def insights() -> Insights:
    """Learned vs rubric weights, approval rates, and the style-similarity trend.

    `due_for_style_review` flags every `STYLE_REVIEW_INTERVAL` (10) logged
    emails — not automated pattern-mining over the text (out of scope for
    now), just a nudge to review recent drafts and add anything recurring to
    society://style.
    """
    decisions = _decision_counts()
    judged = decisions["approve"] + decisions["skip"]
    approval_rate = decisions["approve"] / judged if judged else None

    return Insights(
        rubric_weights=load_config().weights,
        learned_weights=_learned_weights(),
        decisions=decisions,
        approval_rate=approval_rate,
        decisions_until_model_trains=max(0, MIN_DECISIONS_TO_TRAIN - judged),
        style=_style_similarity_trend(),
    )
