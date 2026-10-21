# ADR-0003: Plain dataclasses for schemas, not pydantic

## Context
`save_lead` needs a validated profile schema. pydantic is the obvious library for this, but it
isn't in the project's approved stack (`mcp`, SQLite, SearXNG, requests + trafilatura,
scikit-learn + NumPy — no pydantic or pydantic-settings, unlike other, larger projects this
author also builds).

## Decision
`LeadProfile` (and every other internal record type — `ScoreResult`, `RankedLead`,
`EmailExample`, `Insights`) is a plain stdlib `@dataclass`, with validation written by hand as a
small function (`leads._validate`) that raises a project-specific exception
(`LeadValidationError`) on the first problem found.

## Alternatives considered
- Add pydantic anyway: more ergonomic validation and JSON schema generation for free, but it's a
  new dependency not called for in the approved stack, and the validation surface here (a
  handful of range/membership checks) doesn't need it.

## Consequences
Validation errors are plain exceptions with hand-written messages, not pydantic's structured
`ValidationError`. Adding a new validated field means writing one more `if`, not editing a type
annotation — more boilerplate per field, but zero new dependency and no schema-evolution
surprises.
