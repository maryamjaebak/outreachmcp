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
