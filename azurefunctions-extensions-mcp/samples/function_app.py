from azurefunctions.extensions.mcp import McpApp, MCPToolContext
from typing import Annotated

app = McpApp()

@app.mcp_tool()
def add_numbers(
    a: Annotated[int, "First number"],
    b: Annotated[int, "Second number"]
) -> str:
    """Add two integers."""
    return str(a + b)

@app.mcp_tool()
def greet_user(name: Annotated[str, "User's name"], context: MCPToolContext) -> str:
    """Greet the user."""
    return f"Hello, {name}! You called with context: {context}"
