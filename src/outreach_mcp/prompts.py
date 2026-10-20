from __future__ import annotations

CHANNELS = (
    "the event's own technical/product stack",
    "recruiters hiring in this space",
    "ecosystem (adjacent tooling/platform companies)",
    "education programmes (university/student outreach or grants)",
    "momentum (recent funding, launches, or news)",
    "peer benchmark (who sponsors similar societies/events elsewhere)",
    "lateral (adjacent industries with a plausible reason to sponsor)",
    "non-company funding (grants, foundations, alumni funds)",
)


def find_sponsors_prompt(event: str) -> str:
    channels = "\n".join(f"   - {channel}" for channel in CHANNELS)
    return f"""\
You are running sponsorship outreach for the event "{event}" on behalf of a \
student society.

1. Read the event (via the Notion connector) and the society's own knowledge:
   society://profile, society://past-events, society://past-sponsors,
   society://sponsorship-pack, and society://style.

2. Plan searches across these channels before searching:
{channels}

3. For each candidate: search_web, fetch_page any page you plan to cite, then
   save_lead. Only cite URLs you've actually fetched. Never guess an email —
   contact_email must appear verbatim on its source page, or leave it unset.

4. rank_leads, present the ranked list to the user, and log_decision for each
   one they approve, skip, or mark do-not-contact.

5. For approved leads, draft an outreach email using style_examples and
   society://style. Let the user edit it, log_email the draft/final pair,
   then create the draft via the email connector — never send anything
   yourself.

Hard rules, always:
- every factual claim needs a fetched source URL
- never guess or invent an email address
- no LinkedIn as a channel or citation source
- emails are under 150 words
- exactly one sourced hook per email (one concrete, cited reason this
  company specifically)
- every email includes an opt-out line
- nothing is sent without the user's explicit approval
"""
