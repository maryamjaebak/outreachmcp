from mcp.server.mcpserver import MCPServer

from outreach_mcp.fetch import fetch_page as _fetch_page
from outreach_mcp.search import search_web as _search_web

mcp = MCPServer("outreach")


@mcp.tool()
def hello(name: str = "world") -> str:
    """Sanity-check tool: confirms the server is wired up and callable."""
    return f"Hello, {name}! The outreach MCP server is running."


@mcp.tool()
def search_web(query: str, max_results: int = 8) -> list[dict[str, str]]:
    """Search the web via a local SearXNG instance, cached in SQLite."""
    return _search_web(query, max_results)


@mcp.tool()
def fetch_page(url: str, max_chars: int = 4000) -> str:
    """Fetch a page, extract its main text, respecting robots.txt and rate limits."""
    return _fetch_page(url, max_chars)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
