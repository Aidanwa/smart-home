"""
MCP Client Manager - Manages FastMCP client lifecycle.

Handles starting, stopping, and maintaining connections to MCP servers
using the FastMCP Client library.
"""

import os
import logging
import asyncio
import atexit
from typing import Dict, Optional, Any, List
from threading import Lock

from fastmcp import Client
from fastmcp.client import StdioTransport

logger = logging.getLogger(__name__)


class MCPClientManager:
    """
    Singleton manager for FastMCP client instances.

    Manages client lifecycle using manual async context management
    (__aenter__/__aexit__) to maintain persistent connections.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._server_configs: Dict[str, Dict[str, Any]] = {}  # Store config for each server
        self._discovered_tools: Dict[str, List[Dict[str, Any]]] = {}

        # Register cleanup on exit
        atexit.register(self.stop_all)

        logger.info("MCPClientManager initialized")

    async def _discover_tools_async(
        self,
        name: str,
        transport_obj: StdioTransport,
    ) -> List[Dict[str, Any]]:
        """
        Discover tools from an MCP server.

        Args:
            name: Server name
            transport_obj: Transport to use

        Returns:
            List of tool dictionaries
        """
        # Create temporary client for discovery
        client = Client(transport=transport_obj)

        async with client:
            # FastMCP returns a list of Tool objects directly
            tools = await client.list_tools()

            # Convert Tool objects to dicts for storage
            tool_dicts = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema or {},
                }
                tool_dicts.append(tool_dict)

            logger.info(f"Discovered {len(tool_dicts)} tools from server '{name}'")
            return tool_dicts

    def start_client(
        self,
        name: str,
        transport: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
    ) -> None:
        """
        Initialize an MCP server connection.

        Creates and stores the transport configuration, then discovers available tools.

        Args:
            name: Client identifier
            transport: Transport type ("stdio" or "http")
            command: Command for stdio transport
            args: Arguments for stdio transport
            env: Environment variables for stdio transport
            url: URL for HTTP transport
        """
        if name in self._server_configs:
            logger.debug(f"Server '{name}' already initialized")
            return

        try:
            if transport == "stdio":
                if not command:
                    raise ValueError(f"command required for stdio transport")

                logger.info(f"Initializing stdio MCP server: {name}")
                logger.debug(f"Command: {command} {' '.join(args or [])}")

                # Build environment
                import os
                process_env = os.environ.copy()
                if env:
                    process_env.update(env)

                # Store configuration for creating transports later
                config = {
                    "command": command,
                    "args": args or [],
                    "env": process_env
                }

                with self._lock:
                    self._server_configs[name] = config

                # Create temporary transport for tool discovery
                transport_obj = StdioTransport(**config)

                # Discover tools
                tools = asyncio.run(self._discover_tools_async(name, transport_obj))
                self._discovered_tools[name] = tools

                logger.info(f"Successfully initialized MCP server: {name}")

            elif transport == "http":
                raise NotImplementedError(
                    f"HTTP transport not yet implemented. "
                    f"Check FastMCP documentation for HTTP connection API."
                )
            else:
                raise ValueError(f"Unknown transport type: {transport}")

        except Exception as e:
            logger.error(f"Failed to initialize MCP server '{name}': {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize MCP server '{name}': {e}") from e

    def _create_transport(self, name: str) -> StdioTransport:
        """Create a fresh transport for a server."""
        config = self._server_configs.get(name)
        if not config:
            raise ValueError(f"Server '{name}' not initialized")
        return StdioTransport(**config)

    def get_discovered_tools(self, name: str) -> List[Dict[str, Any]]:
        """
        Get discovered tools for a server.

        Tools are discovered when the client is started, so this
        returns cached results.

        Args:
            name: Server name

        Returns:
            List of tool schemas
        """
        return self._discovered_tools.get(name, [])

    async def _call_tool_async(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool on an MCP server asynchronously.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        # Create fresh transport for this call
        transport = self._create_transport(server_name)

        # Create fresh client for this call with async with
        client = Client(transport=transport)

        async with client:
            response = await client.call_tool(name=tool_name, arguments=arguments)

            # Extract content from response
            if hasattr(response, 'content'):
                return response.content
            return response

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool on an MCP server (sync wrapper).

        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        return asyncio.run(self._call_tool_async(server_name, tool_name, arguments))

    def stop_client(self, name: str):
        """Stop a specific server."""
        if name not in self._server_configs:
            logger.warning(f"Server '{name}' not found")
            return

        try:
            logger.info(f"Stopping MCP server: {name}")
        except Exception as e:
            logger.error(f"Error stopping server '{name}': {e}")
        finally:
            with self._lock:
                if name in self._server_configs:
                    del self._server_configs[name]
                if name in self._discovered_tools:
                    del self._discovered_tools[name]

    def stop_all(self):
        """Stop all servers."""
        if not self._server_configs:
            return

        logger.info(f"Stopping all MCP servers ({len(self._server_configs)} running)")

        for name in list(self._server_configs.keys()):
            try:
                self.stop_client(name)
            except Exception as e:
                logger.error(f"Error stopping server '{name}': {e}")

        logger.info("All MCP servers stopped")

    def __del__(self):
        """Cleanup on deletion."""
        self.stop_all()
