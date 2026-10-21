# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.0] - 2026-10-21

### Added
- Project scaffold: uv project with `src/` layout, FastMCP-style hello tool
  (MCP SDK v2's `MCPServer`), ruff/mypy/pytest config, pre-commit hooks,
  CI workflow, dependabot, justfile, docker-compose for SearXNG.
- `search_web(query, max_results)` tool: queries a local SearXNG instance's
  JSON API, cached in SQLite with a 24h TTL. Tests run against a fixture
  recorded from a real SearXNG response, no network access required.
- `fetch_page(url, max_chars)` tool: checks `robots.txt` (fetched with our
  own User-Agent — some sites 403 the default one, which `robotparser`
  otherwise treats as disallow-all), enforces a 1s per-domain delay,
  extracts main text with trafilatura, caches for 7 days, and records the
  URL as seen (for later evidence-URL validation). Tests run against a
  fixture recorded from a real page, no network access required.
- `save_lead(event_id, ...)` tool: validates a lead profile, drops evidence
  URLs that were never fetched via `fetch_page`, verifies a claimed email
  appears verbatim on its (previously fetched, not-yet-expired) source page,
  computes a weighted score from `config/config.yaml`'s rubric, and upserts
  into a SQLite `leads` table keyed on `(event_id, company)`.
- `rank_leads(event_id, limit)` tool: returns saved leads sorted by score
  with a feature breakdown each, excluding DNC leads entirely, with ~20%
  explore slots sampled from the tail.
- Society knowledge resources (`society://profile`, `past-events`,
  `past-sponsors`, `sponsorship-pack`, `style`): read `society/<section>.md`
  (gitignored, real data), falling back to the shipped `society.example/`
  placeholder until it's populated.
- `update_society_info(section, text)` tool: appends a fact to a society
  section, seeding it from the example file on first write.
- `find_sponsors(event)` prompt: encodes the full sponsorship-outreach
  workflow (read event + society knowledge, plan searches across 8 channels,
  search/fetch/save_lead, rank_leads + log_decision, draft + log_email) and
  its hard rules (sourced claims, no guessed emails, no LinkedIn, <150 words,
  one hook, opt-out line, nothing sent without approval).
- `log_decision(event_id, company, action, reason)` tool: records an
  approve/skip/dnc decision (snapshotting the lead's feature vector so later
  retraining always uses what was actually judged), flips the lead's own
  `dnc` flag on a "dnc" decision, and retrains a logistic-regression
  preference model (scikit-learn, `C=0.5`) once 40+ approve/skip decisions
  exist. `rank_leads` now blends the rubric with the trained model's
  `P(approve)`: `(1-alpha)*rubric + alpha*P(approve)*100`, where `alpha`
  grows with decision count up to a cap of 0.7, falling back to the pure
  rubric score until a model exists.
- `log_email(event_id, company, draft, final)` tool: stores the pair with a
  `difflib`-based similarity score (0-1).
- `style_examples(event_id, company, k)` tool: returns up to k past final
  emails as few-shot examples — same-company history first, falling back to
  the global pool, replied-to emails prioritized either way.
- `log_outcome(event_id, company, outcome)` tool: records an outcome
  (replied/meeting/sponsored/declined, reward 0.5/0.75/1.0/0.0) and updates
  a linear-Thompson-sampling contextual bandit (NumPy, `bandit.py`) keyed on
  the lead's feature vector. Re-logging an outcome for the same lead adjusts
  its reward rather than double-counting the observation. `rank_leads`'s
  explore slots now use Thompson sampling once any outcome has been logged
  (falls back to a random tail sample until then).
- `insights()` tool: rubric weights vs the trained preference model's
  coefficients (once one exists), approve/skip/dnc counts and approval
  rate, a countdown to the next retrain, and a style-similarity trend
  (overall vs recent average, flagged for review every 10 logged emails).
- ADRs for the project's real architectural decisions (`docs/adr/`): MCP
  SDK v2, single-SQLite storage, dataclasses over pydantic, the seen-URLs/
  content-cache split, and the learning architecture (logistic regression +
  linear Thompson sampling).
