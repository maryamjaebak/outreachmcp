from __future__ import annotations

import difflib
import os
import sqlite3
import time
from dataclasses import dataclass

DATABASE_PATH = os.environ.get("DATABASE_PATH", "./outreach.db")

EMAILS_SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    company TEXT NOT NULL,
    draft TEXT NOT NULL,
    final TEXT NOT NULL,
    similarity REAL NOT NULL,
    replied INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
)
"""


@dataclass(frozen=True)
class EmailExample:
    company: str
    final: str
    replied: bool


def log_email(event_id: str, company: str, draft: str, final: str) -> float:
    """Store a draft/final email pair and return their similarity (0-1).

    Similarity uses stdlib `difflib` (no embedding model needed for this) —
    it's used later to track how much the user edits drafts over time.
    """
    similarity = difflib.SequenceMatcher(None, draft, final).ratio()

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(EMAILS_SCHEMA)
        conn.execute(
            """
            INSERT INTO emails (event_id, company, draft, final, similarity, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, company, draft, final, similarity, time.time()),
        )
        conn.commit()
    finally:
        conn.close()

    return similarity


def style_examples(event_id: str, company: str, k: int = 3) -> list[EmailExample]:
    """Return up to k past final emails as few-shot style examples.

    Prefers past emails to this same `company` (any event — if we've
    emailed them before, that's the most relevant style reference), then
    fills any remaining slots from the global pool. Either way, replied-to
    emails are prioritized, since those are the ones that actually worked.
    `event_id` isn't filtered on — there's rarely a prior email for the
    exact (event, company) pair on a first outreach.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(EMAILS_SCHEMA)
        company_rows = conn.execute(
            """
            SELECT id, company, final, replied FROM emails
            WHERE company = ?
            ORDER BY replied DESC, created_at DESC
            LIMIT ?
            """,
            (company, k),
        ).fetchall()

        remaining = k - len(company_rows)
        global_rows = []
        if remaining > 0:
            exclude_ids = [row[0] for row in company_rows] or [-1]
            placeholders = ",".join("?" for _ in exclude_ids)
            global_rows = conn.execute(
                f"""
                SELECT id, company, final, replied FROM emails
                WHERE id NOT IN ({placeholders})
                ORDER BY replied DESC, created_at DESC
                LIMIT ?
                """,
                (*exclude_ids, remaining),
            ).fetchall()
    finally:
        conn.close()

    return [
        EmailExample(company=row[1], final=row[2], replied=bool(row[3]))
        for row in company_rows + global_rows
    ]
