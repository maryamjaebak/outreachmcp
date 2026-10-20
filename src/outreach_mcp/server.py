from mcp.server.mcpserver import MCPServer

from outreach_mcp.fetch import fetch_page as _fetch_page
from outreach_mcp.leads import LeadProfile
from outreach_mcp.leads import save_lead as _save_lead
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


@mcp.tool()
def save_lead(
    event_id: str,
    company: str,
    contact_type: str,
    geography: str,
    event_fit: float,
    ask_realism: float,
    n_channels: int,
    contact_name: str | None = None,
    contact_email: str | None = None,
    email_source_url: str | None = None,
    evidence_urls: list[str] | None = None,
    warm_connection: bool = False,
    propensity: float = 0.25,
    propensity_signal: bool = False,
    dnc: bool = False,
) -> dict[str, object]:
    """Validate, score, and upsert a lead profile for an event.

    `contact_type` must be one of: named, inbox, form, none.
    `geography` must be one of: london, uk, intl_uk_ops, intl.
    Evidence URLs not previously fetched via fetch_page are dropped, and an
    email is only trusted if it appears verbatim on its (previously fetched)
    email_source_url page.
    """
    profile = LeadProfile(
        company=company,
        contact_type=contact_type,
        geography=geography,
        event_fit=event_fit,
        ask_realism=ask_realism,
        n_channels=n_channels,
        contact_name=contact_name,
        contact_email=contact_email,
        email_source_url=email_source_url,
        evidence_urls=evidence_urls or [],
        warm_connection=warm_connection,
        propensity=propensity,
        propensity_signal=propensity_signal,
        dnc=dnc,
    )
    result = _save_lead(event_id, profile)
    return {
        "company": result.company,
        "score": result.score,
        "features": result.features,
        "dropped_evidence_urls": result.dropped_evidence_urls,
        "email_verified": result.email_verified,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
