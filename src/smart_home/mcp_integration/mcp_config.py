import os
from typing import Dict, Any, Optional


class MCPServerConfig:
    """
    Configuration for a single MCP server.

    Simplified configuration focused on FastMCP client integration.
    Works with all LLM providers (OpenAI, Ollama, etc.).
    """

    def __init__(
        self,
        name: str,
        env_var: str,
        command: str,
        args: list[str],
        transport: str = "stdio",
        env: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
        allowed_tools: Optional[list[str]] = None,
    ):
        """
        Initialize MCP server configuration.

        Args:
            name: Server name/identifier
            env_var: Environment variable to check if server should be enabled (e.g., "MCP_FETCH")
            command: Executable command (e.g., "uvx", "npx", "python")
            args: Arguments to pass to command
            transport: Transport type - "stdio" or "http" (default: "stdio")
            env: Optional environment variables for the server process
            url: Optional URL for HTTP transport (required if transport="http")
            allowed_tools: Optional whitelist of tool names to expose (None = all tools)
        """
        self.name = name
        self.env_var = env_var
        self.command = command
        self.args = args
        self.transport = transport
        self.env = env or {}
        self.url = url
        self.allowed_tools = allowed_tools

        # Validate configuration
        if self.transport == "http" and not self.url:
            raise ValueError(
                f"MCP server '{self.name}' with transport='http' requires 'url' parameter"
            )

    def is_enabled(self) -> bool:
        """Check if this server is enabled via environment variable."""
        return os.getenv(self.env_var, "False").lower() in ("true", "1", "yes")


# =========================================================
# SERVER REGISTRY - Add new servers here
# =========================================================

# Pre-configured MCP servers
FETCH_SERVER = MCPServerConfig(
    name="fetch",
    env_var="MCP_FETCH",
    command="uvx",
    args=["mcp-server-fetch"],
    transport="stdio",  # Use stdio transport with FastMCP
    allowed_tools=None,  # Allow all tools from this server
)


# Registry of all available servers
ALL_SERVERS = [
    FETCH_SERVER,
]


def get_enabled_mcp_servers() -> list[MCPServerConfig]:
    """
    Get list of enabled MCP server configurations.

    Returns:
        List of MCPServerConfig instances that are enabled via env vars
    """
    return [server for server in ALL_SERVERS if server.is_enabled()]