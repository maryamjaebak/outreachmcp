from __future__ import annotations

import sqlite3
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_urls (
    url TEXT PRIMARY KEY,
    seen_at REAL NOT NULL
)
"""


def mark_seen(db_path: str | Path, url: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_SCHEMA)
        conn.execute(
            "INSERT OR REPLACE INTO seen_urls (url, seen_at) VALUES (?, ?)",
            (url, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def was_seen(db_path: str | Path, url: str) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_SCHEMA)
        row = conn.execute("SELECT 1 FROM seen_urls WHERE url = ?", (url,)).fetchone()
        return row is not None
    finally:
        conn.close()
