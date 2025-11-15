"""
MCP (Model Context Protocol) integration module.

This module provides MCP server configuration and tool integration using FastMCP Client.
Works with all LLM providers (OpenAI, Ollama, etc.).
"""

from smart_home.mcp_integration.mcp_config import (
    MCPServerConfig,
    get_enabled_mcp_servers,
)
from smart_home.mcp_integration.mcp_tools import MCPToolWrapper, create_mcp_tools
from smart_home.mcp_integration.client_manager import MCPClientManager
from smart_home.mcp_integration.schema_converter import MCPSchemaConverter

__all__ = [
    "MCPServerConfig",
    "get_enabled_mcp_servers",
    "MCPToolWrapper",
    "create_mcp_tools",
    "MCPClientManager",
    "MCPSchemaConverter",
]
