"""
MCP Tool Wrapper - Wraps MCP tools as standard Tool instances.

Uses FastMCP Client to discover and execute tools from MCP servers.
Works with all LLM providers (OpenAI, Ollama, etc.).
"""

import logging
from typing import Dict, Any, List, Optional

from smart_home.core.agent import Tool
from smart_home.mcp_integration.mcp_config import MCPServerConfig, get_enabled_mcp_servers
from smart_home.mcp_integration.client_manager import MCPClientManager
from smart_home.mcp_integration.schema_converter import MCPSchemaConverter

logger = logging.getLogger(__name__)


class MCPToolWrapper(Tool):
    """
    Wraps a single MCP tool as a standard Tool.

    This class bridges the gap between MCP servers and the agent framework,
    making MCP tools work seamlessly with any LLM provider.
    """

    def __init__(
        self,
        server_name: str,
        tool_name: str,
        tool_schema: Dict[str, Any],
        client_manager: MCPClientManager,
    ):
        """
        Initialize MCP tool wrapper.

        Args:
            server_name: Name of the MCP server this tool belongs to
            tool_name: Original tool name from the MCP server
            tool_schema: MCP tool schema (from list_tools response)
            client_manager: MCPClientManager instance for execution
        """
        # Create namespaced tool name to avoid conflicts
        # Format: {server_name}__{tool_name}
        namespaced_name = f"{server_name}__{tool_name}"

        # Extract tool information
        converter = MCPSchemaConverter()
        tool_info = converter.extract_tool_info(tool_schema)

        # Initialize base Tool
        super().__init__(
            name=namespaced_name,
            description=tool_info["description"],
            params=tool_info["parameters"],
        )

        # Store MCP-specific info
        self.server_name = server_name
        self.original_tool_name = tool_name
        self.client_manager = client_manager

        logger.debug(f"Created MCP tool wrapper: {namespaced_name}")

    def call(self, **kwargs) -> str:
        """
        Execute the MCP tool.

        This method:
        1. Gets the FastMCP client for this server
        2. Calls the tool via client.call_tool()
        3. Converts the result to a string

        Args:
            **kwargs: Tool arguments (validated against parameters schema)

        Returns:
            Tool execution result as string
        """
        try:
            logger.debug(
                f"Calling MCP tool: {self.original_tool_name} "
                f"on server: {self.server_name} "
                f"with args: {kwargs}"
            )

            # Execute tool via client manager
            result = self.client_manager.call_tool(
                server_name=self.server_name,
                tool_name=self.original_tool_name,
                arguments=kwargs,
            )

            # Convert result to string
            converter = MCPSchemaConverter()
            result_str = converter.convert_tool_result(result)

            logger.debug(
                f"MCP tool {self.name} returned {len(result_str)} characters"
            )

            return result_str

        except Exception as e:
            error_msg = f"Error executing MCP tool '{self.name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"


def create_mcp_tools(server_names: Optional[List[str]] = None) -> List[MCPToolWrapper]:
    """
    Create MCPToolWrapper instances for enabled MCP servers.

    This function:
    1. Gets enabled servers from config
    2. Starts FastMCP clients for each server
    3. Discovers tools via client.list_tools()
    4. Wraps each tool in MCPToolWrapper
    5. Returns list of standard Tool instances

    Args:
        server_names: Optional list of server names to include.
                     If None, includes all enabled servers.
                     Example: ["fetch", "zigbee"]

    Returns:
        List of MCPToolWrapper instances ready to use with agents

    Example:
        # Get all MCP tools
        all_tools = create_mcp_tools()

        # Get only fetch tools
        fetch_tools = create_mcp_tools(server_names=["fetch"])

        # Use in an agent
        agent = Agent(tools=create_mcp_tools())
    """
    enabled_servers = get_enabled_mcp_servers()

    if not enabled_servers:
        logger.debug("No MCP servers enabled in configuration")
        return []

    # Filter by server_names if provided
    if server_names is not None:
        server_names_set = set(server_names)
        enabled_servers = [
            server for server in enabled_servers
            if server.name in server_names_set
        ]

        # Warn about requested servers that aren't enabled
        enabled_names = {server.name for server in enabled_servers}
        missing = server_names_set - enabled_names
        if missing:
            logger.warning(
                f"Requested MCP servers not enabled: {missing}. "
                f"Set corresponding env vars to True (e.g., MCP_FETCH=True)"
            )

    if not enabled_servers:
        logger.debug("No matching MCP servers found after filtering")
        return []

    # Create client manager (singleton)
    client_manager = MCPClientManager()
    tools = []

    for config in enabled_servers:
        try:
            logger.info(f"Initializing MCP server: {config.name}")

            # Start FastMCP client (also discovers tools)
            client = client_manager.start_client(
                name=config.name,
                transport=config.transport,
                command=config.command,
                args=config.args,
                env=config.env,
                url=config.url,
            )

            # Get cached discovered tools
            mcp_tools = client_manager.get_discovered_tools(config.name)
            logger.info(
                f"Discovered {len(mcp_tools)} tools from MCP server '{config.name}'"
            )

            # Filter by allowed_tools if specified in config
            if config.allowed_tools:
                mcp_tools = [
                    tool for tool in mcp_tools
                    if tool.get("name") in config.allowed_tools
                ]
                logger.debug(
                    f"Filtered to {len(mcp_tools)} allowed tools for '{config.name}'"
                )

            # Wrap each MCP tool
            for mcp_tool in mcp_tools:
                try:
                    wrapper = MCPToolWrapper(
                        server_name=config.name,
                        tool_name=mcp_tool["name"],
                        tool_schema=mcp_tool,
                        client_manager=client_manager,
                    )
                    tools.append(wrapper)

                except Exception as e:
                    logger.error(
                        f"Failed to wrap tool '{mcp_tool.get('name')}' "
                        f"from server '{config.name}': {e}"
                    )
                    # Continue with other tools
                    continue

            logger.info(
                f"Created {len([t for t in tools if t.server_name == config.name])} "
                f"tool wrappers from MCP server '{config.name}'"
            )

        except Exception as e:
            logger.error(
                f"Failed to initialize MCP server '{config.name}': {e}",
                exc_info=True
            )
            # Continue with other servers
            continue

    logger.info(f"Created {len(tools)} total MCP tools from {len(enabled_servers)} server(s)")
    return tools
