# ADR-0001: Target MCP SDK v2 (`MCPServer`, not `FastMCP`)

## Context
The design plan referred to the official `mcp` Python SDK's "FastMCP" tool-decorator style. By
the time the project was scaffolded, the installed SDK (`mcp>=2.3.0`) had renamed that class
from `FastMCP` to `MCPServer` (`mcp.server.mcpserver.MCPServer`) as part of a v2 API change.
Pinning to the older v1 API (`mcp<2`) was the alternative.

## Decision
Use the current v2 SDK and its `MCPServer` class. The decorator-based tool/resource/prompt
registration style (`@mcp.tool()`, `@mcp.resource(...)`, `@mcp.prompt()`) is unchanged; only the
import path and class name differ from the original plan.

## Alternatives considered
- Pin `mcp<2` to match the plan's wording exactly. Rejected: locks the project to an
  unmaintained major version for no functional benefit, since the decorator API carried over.

## Consequences
Any reference to "FastMCP" elsewhere just means "this SDK's decorator-based tool style," not the
literal class name. A real sharp edge found while integrating: `urllib.robotparser`'s `read()`
uses urllib's default User-Agent regardless of SDK version — unrelated to this decision, but
discovered in the same integration pass (see `fetch.py`).
