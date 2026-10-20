from outreach_mcp.server import hello


def test_hello_default() -> None:
    assert hello() == "Hello, world! The outreach MCP server is running."


def test_hello_with_name() -> None:
    assert "Hello, Maryam!" in hello("Maryam")
