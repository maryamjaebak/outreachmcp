from outreach_mcp.prompts import find_sponsors_prompt


def test_includes_event_name() -> None:
    text = find_sponsors_prompt("Hack the Grid 2026")
    assert "Hack the Grid 2026" in text


def test_references_all_core_tools() -> None:
    text = find_sponsors_prompt("Demo Day")
    for tool in ["search_web", "fetch_page", "save_lead", "rank_leads", "log_decision"]:
        assert tool in text


def test_references_society_resources() -> None:
    text = find_sponsors_prompt("Demo Day")
    for resource in [
        "society://profile",
        "society://past-events",
        "society://past-sponsors",
        "society://sponsorship-pack",
        "society://style",
    ]:
        assert resource in text


def test_states_hard_rules() -> None:
    text = find_sponsors_prompt("Demo Day").lower()
    assert "linkedin" in text
    assert "150 words" in text
    assert "opt-out" in text
    assert "never guess" in text
