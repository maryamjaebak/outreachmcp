# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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
