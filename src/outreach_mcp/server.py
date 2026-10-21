from mcp.server.mcpserver import MCPServer

from outreach_mcp.emails import log_email as _log_email
from outreach_mcp.emails import style_examples as _style_examples
from outreach_mcp.fetch import fetch_page as _fetch_page
from outreach_mcp.leads import LeadProfile
from outreach_mcp.leads import save_lead as _save_lead
from outreach_mcp.preference_model import log_decision as _log_decision
from outreach_mcp.prompts import find_sponsors_prompt
from outreach_mcp.ranking import rank_leads as _rank_leads
from outreach_mcp.search import search_web as _search_web
from outreach_mcp.society import read_section as _read_section
from outreach_mcp.society import update_society_info as _update_society_info

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


@mcp.tool()
def log_decision(event_id: str, company: str, action: str, reason: str = "") -> str:
    """Log an approve/skip/dnc decision on a lead already saved via save_lead.

    Retrains the preference model once enough approve/skip decisions exist
    (40+), which rank_leads then blends into its scores. A "dnc" decision
    also marks the lead itself do-not-contact.
    """
    _log_decision(event_id, company, action, reason)
    return f"logged {action} for {company}"


@mcp.tool()
def log_email(event_id: str, company: str, draft: str, final: str) -> float:
    """Store a draft/final email pair and return their similarity (0-1)."""
    return _log_email(event_id, company, draft, final)


@mcp.tool()
def style_examples(event_id: str, company: str, k: int = 3) -> list[dict[str, object]]:
    """Return up to k past final emails as few-shot style examples, replied-to first."""
    examples = _style_examples(event_id, company, k)
    return [{"company": ex.company, "final": ex.final, "replied": ex.replied} for ex in examples]


@mcp.tool()
def rank_leads(event_id: str, limit: int = 15) -> list[dict[str, object]]:
    """Rank saved (non-DNC) leads for an event by score, with ~20% explore slots.

    Blends the rubric with the learned preference model once enough
    decisions exist (see log_decision); falls back to the rubric score
    alone until then.
    """
    ranked = _rank_leads(event_id, limit)
    return [
        {
            "company": lead.company,
            "score": lead.score,
            "features": lead.features,
            "contact_name": lead.contact_name,
            "contact_email": lead.contact_email,
            "email_verified": lead.email_verified,
            "contact_type": lead.contact_type,
            "geography": lead.geography,
            "evidence_urls": lead.evidence_urls,
            "explore": lead.explore,
        }
        for lead in ranked
    ]


@mcp.resource("society://profile")
def society_profile() -> str:
    """Who the society is: what it does, member count, past achievements."""
    return _read_section("profile")


@mcp.resource("society://past-events")
def society_past_events() -> str:
    """Past events: name, date, attendance, notable outcomes."""
    return _read_section("past-events")


@mcp.resource("society://past-sponsors")
def society_past_sponsors() -> str:
    """Past sponsors: company, tier, year, what they got in return."""
    return _read_section("past-sponsors")


@mcp.resource("society://sponsorship-pack")
def society_sponsorship_pack() -> str:
    """Sponsorship pack: tiers, pricing, benefits."""
    return _read_section("sponsorship-pack")


@mcp.resource("society://style")
def society_style() -> str:
    """Style guide for outreach emails."""
    return _read_section("style")


@mcp.tool()
def update_society_info(section: str, text: str) -> str:
    """Append a fact to a society knowledge section.

    `section` must be one of: profile, past-events, past-sponsors,
    sponsorship-pack, style.
    """
    _update_society_info(section, text)
    return f"appended to society/{section}.md"


@mcp.prompt()
def find_sponsors(event: str) -> str:
    """Guide the sponsorship-outreach workflow for one event, start to finish."""
    return find_sponsors_prompt(event)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
