from mcp.server.mcpserver import MCPServer

mcp = MCPServer("outreach")


@mcp.tool()
def hello(name: str = "world") -> str:
    """Sanity-check tool: confirms the server is wired up and callable."""
    return f"Hello, {name}! The outreach MCP server is running."


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
