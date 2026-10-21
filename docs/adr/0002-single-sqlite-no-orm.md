# ADR-0002: Single SQLite file, no ORM

## Context
The server needs persistent storage for: the search/page cache, seen-URLs, leads, decisions,
emails, and outcomes. The approved stack names SQLite but doesn't mandate a specific access
pattern.

## Decision
One SQLite file (`DATABASE_PATH`, default `./outreach.db`), accessed via stdlib `sqlite3`
directly — no ORM, no migration framework. Each module (`cache.py`, `seen.py`, `leads.py`,
`preference_model.py`, `emails.py`, `outcomes.py`) owns its own table(s) and runs
`CREATE TABLE IF NOT EXISTS` idempotently on every connection, rather than a central schema
migration step.

## Alternatives considered
- An ORM (SQLAlchemy, peewee): unnecessary abstraction for a handful of simple tables with no
  relational query complexity beyond basic joins already written by hand in `ranking.py`.
- Separate SQLite files per concern: would complicate the `(event_id, company)` joins that
  `ranking.py`, `preference_model.py`, and `outcomes.py` all need against the `leads` table.

## Consequences
No formal migration story exists yet — a schema change means editing the `CREATE TABLE`
statement and accepting that existing local databases won't pick up the change on old rows. Fine
for a single-user local tool at this stage; would need revisiting before any multi-deployment or
shared-database use case.
