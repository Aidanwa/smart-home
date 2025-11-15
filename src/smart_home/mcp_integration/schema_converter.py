"""
MCP Schema Converter - Converts between MCP and Tool schema formats.

Handles bidirectional conversion between MCP's InputSchema format
and the standard Tool parameters format.
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MCPSchemaConverter:
    """
    Converter for MCP schemas and results.

    Provides methods to convert MCP InputSchemas to Tool parameters
    and MCP results to strings suitable for LLM consumption.
    """

    @staticmethod
    def _normalize_property(prop: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single property schema for OpenAI compatibility.

        Removes invalid formats and ensures compatibility.
        """
        prop = prop.copy()

        # Remove invalid formats for OpenAI
        # OpenAI only supports a limited set of formats
        if "format" in prop:
            valid_formats = {"date-time", "date", "time", "email", "uuid"}
            if prop["format"] not in valid_formats:
                del prop["format"]

        # Remove min/max values that use exclusive bounds (OpenAI doesn't support these)
        if "exclusiveMinimum" in prop:
            del prop["exclusiveMinimum"]
        if "exclusiveMaximum" in prop:
            del prop["exclusiveMaximum"]

        # Remove minLength constraint if it's 1 (redundant with required)
        if prop.get("minLength") == 1:
            del prop["minLength"]

        # Remove title field (not needed for function calling)
        if "title" in prop:
            del prop["title"]

        return prop

    @staticmethod
    def convert_input_schema(mcp_input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert MCP InputSchema to Tool parameters format.

        MCP InputSchema format (JSON Schema):
        {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch"
                }
            },
            "required": ["url"]
        }

        Tool parameters format (same, but validated and normalized):
        {
            "type": "object",
            "properties": {...},
            "required": [...],
            "additionalProperties": False  # Added for OpenAI strict mode
        }

        Args:
            mcp_input_schema: MCP tool's inputSchema field

        Returns:
            Tool parameters dict
        """
        # MCP schemas are already JSON Schema, so mostly pass-through
        params = mcp_input_schema.copy() if mcp_input_schema else {}

        # Ensure type is object
        if not params.get("type"):
            params["type"] = "object"

        # Ensure properties exist
        if "properties" not in params:
            params["properties"] = {}

        # Check if we have properties with defaults BEFORE normalizing
        has_optional_params = False
        for prop_name, prop_schema in params.get("properties", {}).items():
            if "default" in prop_schema:
                logger.debug(f"Property '{prop_name}' has default value, using non-strict mode")
                has_optional_params = True
                break

        # Normalize all properties for OpenAI compatibility
        normalized_properties = {}
        for prop_name, prop_schema in params.get("properties", {}).items():
            normalized_properties[prop_name] = MCPSchemaConverter._normalize_property(prop_schema)
        params["properties"] = normalized_properties

        # Remove top-level title and description fields from schema (keep them in properties)
        if "title" in params:
            del params["title"]
        if "description" in params:
            del params["description"]

        # For OpenAI strict mode: either all properties are required, or don't use strict mode
        # If we have optional params with defaults, don't use strict mode
        if not has_optional_params:
            # Only use strict mode if all params are required
            logger.debug("No optional params found, using strict mode (additionalProperties: false)")
            params["additionalProperties"] = False
        else:
            logger.debug("Optional params found, NOT using strict mode")
        # Otherwise, leave additionalProperties unset (non-strict mode)

        return params

    @staticmethod
    def convert_tool_result(result: Any) -> str:
        """
        Convert MCP tool result to string for LLM consumption.

        MCP results can be:
        - String (pass-through)
        - List of ContentBlock objects (extract text)
        - Dict with content/text field
        - Other types (JSON serialize)

        Args:
            result: Result from MCP tool execution

        Returns:
            String representation suitable for LLM
        """
        # Handle None
        if result is None:
            return ""

        # Handle string (most common)
        if isinstance(result, str):
            return result

        # Handle list of ContentBlocks
        if isinstance(result, list):
            text_parts = []
            for block in result:
                if isinstance(block, dict):
                    # Dict with type and text
                    if block.get("type") == "text" and "text" in block:
                        text_parts.append(block["text"])
                    elif "text" in block:
                        text_parts.append(block["text"])
                    elif "content" in block:
                        # Recursively convert content
                        text_parts.append(
                            MCPSchemaConverter.convert_tool_result(block["content"])
                        )
                elif hasattr(block, "text"):
                    # Object with text attribute
                    text_parts.append(str(block.text))
                elif hasattr(block, "content"):
                    # Object with content attribute
                    text_parts.append(
                        MCPSchemaConverter.convert_tool_result(block.content)
                    )
                else:
                    # Fallback: str conversion
                    text_parts.append(str(block))

            return "\n".join(text_parts)

        # Handle dict
        if isinstance(result, dict):
            # Check for common content fields
            if "content" in result:
                return MCPSchemaConverter.convert_tool_result(result["content"])
            if "text" in result:
                return result["text"]
            if "message" in result:
                return result["message"]

            # Fallback: JSON serialize dict
            try:
                return json.dumps(result, indent=2)
            except (TypeError, ValueError):
                return str(result)

        # Handle objects with text attribute
        if hasattr(result, "text"):
            return str(result.text)

        if hasattr(result, "content"):
            return MCPSchemaConverter.convert_tool_result(result.content)

        # Final fallback: str conversion
        return str(result)

    @staticmethod
    def validate_tool_schema(tool_schema: Dict[str, Any]) -> bool:
        """
        Validate that a tool schema has required fields.

        Args:
            tool_schema: MCP tool schema

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["name"]

        for field in required_fields:
            if field not in tool_schema:
                logger.warning(f"Tool schema missing required field: {field}")
                return False

        return True

    @staticmethod
    def extract_tool_info(tool_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant information from MCP tool schema.

        Args:
            tool_schema: MCP tool schema from list_tools()

        Returns:
            Dict with name, description, and parameters
        """
        return {
            "name": tool_schema.get("name", "unknown"),
            "description": tool_schema.get("description", ""),
            "parameters": MCPSchemaConverter.convert_input_schema(
                tool_schema.get("inputSchema", {})
            ),
        }
