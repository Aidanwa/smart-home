# MCP Integration Guide

## Overview

The MCP (Model Context Protocol) integration enables agents to use external tools from MCP servers. This implementation uses **FastMCP Client** to manage connections locally, making MCP tools work with **any LLM provider** (OpenAI, Ollama, Claude, etc.).

**Key Features:**
- ✅ Provider-agnostic (works with OpenAI, Ollama, and other providers)
- ✅ Local tool execution via FastMCP Client
- ✅ Automatic tool discovery and schema conversion
- ✅ Support for stdio and HTTP transports
- ✅ Tool namespacing to avoid conflicts

## How It Works: Complete Workflow

### Step 1: Configuration (`mcp_config.py`)

You define an MCP server configuration that specifies how to connect to the server:

```python
FETCH_SERVER = MCPServerConfig(
    name="fetch",                      # Server identifier
    env_var="MCP_FETCH",              # Environment variable to enable/disable
    command="uvx",                     # Command to run
    args=["mcp-server-fetch"],        # Arguments to command
    transport="stdio",                 # Transport type (stdio or http)
    env=None,                          # Optional environment variables
    url=None,                          # URL for HTTP transport
    allowed_tools=None,                # Optional tool whitelist
)
```

**What this does:**
- Defines connection parameters for the MCP server
- Maps to an environment variable (`MCP_FETCH`) for enable/disable control
- Specifies the command that will spawn the MCP server process (`uvx mcp-server-fetch`)

### Step 2: Registration (`mcp_config.py`)

The server config is registered in the global registry:

```python
ALL_SERVERS = [FETCH_SERVER, ZIGBEE_SERVER]

def get_enabled_mcp_servers() -> list[MCPServerConfig]:
    """Returns only servers where env_var is set to 'True'."""
    return [server for server in ALL_SERVERS if server.is_enabled()]
```

**What this does:**
- Maintains a list of all available MCP servers
- Filters based on environment variables (only returns enabled servers)

### Step 3: Tool Creation (`mcp_tools.py`)

When you call `create_mcp_tools()`, here's what happens:

```python
# In your agent
mcp_tools = create_mcp_tools(server_names=["fetch"])
```

**Internal workflow:**

1. **Get enabled servers** - Filters `ALL_SERVERS` by `server_names` parameter
2. **Initialize client manager** - Creates singleton `MCPClientManager` instance
3. **For each server:**
   ```python
   # a. Start the server and discover tools
   client_manager.start_client(
       name=config.name,
       transport=config.transport,
       command=config.command,
       args=config.args,
       env=config.env,
       url=config.url,
   )
   ```

   This does:
   - Stores the server configuration in `_server_configs` dict
   - Creates a temporary `StdioTransport` instance
   - Spawns the MCP server subprocess
   - Calls `client.list_tools()` to discover available tools
   - Converts FastMCP Tool objects to dictionaries
   - Caches discovered tools in `_discovered_tools` dict

4. **Get cached tools:**
   ```python
   mcp_tools = client_manager.get_discovered_tools(config.name)
   ```
   Returns the list of tool schemas that were discovered

5. **Apply filtering** (if configured):
   ```python
   if config.allowed_tools:
       mcp_tools = [t for t in mcp_tools if t["name"] in config.allowed_tools]
   ```

6. **Wrap each tool:**
   ```python
   for mcp_tool in mcp_tools:
       wrapper = MCPToolWrapper(
           server_name=config.name,
           tool_name=mcp_tool["name"],
           tool_schema=mcp_tool,
           client_manager=client_manager,
       )
       tools.append(wrapper)
   ```

### Step 4: Tool Wrapping (`MCPToolWrapper`)

Each MCP tool is wrapped in an `MCPToolWrapper` instance:

```python
class MCPToolWrapper(Tool):
    def __init__(self, server_name, tool_name, tool_schema, client_manager):
        # 1. Create namespaced name to avoid conflicts
        namespaced_name = f"{server_name}__{tool_name}"  # e.g., "fetch__fetch"

        # 2. Convert MCP schema to standard Tool parameters
        converter = MCPSchemaConverter()
        tool_info = converter.extract_tool_info(tool_schema)

        # 3. Initialize base Tool class
        super().__init__(
            name=namespaced_name,
            description=tool_info["description"],
            params=tool_info["parameters"],
        )

        # 4. Store references for execution
        self.server_name = server_name
        self.original_tool_name = tool_name
        self.client_manager = client_manager
```

**What this does:**
- **Namespacing**: Prefixes tool name with server name (`fetch__fetch`) to avoid conflicts
- **Schema conversion**: Converts MCP's `inputSchema` to standard Tool `parameters` format
- **OpenAI compatibility**: Normalizes schema (removes invalid formats, handles optional params)
- **Execution context**: Stores server name and client manager for later execution

### Step 5: Schema Conversion (`schema_converter.py`)

The schema converter normalizes MCP schemas for LLM compatibility:

```python
def convert_input_schema(mcp_input_schema: Dict[str, Any]) -> Dict[str, Any]:
    # Input: MCP tool's inputSchema
    {
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri", "title": "URL"},
            "max_length": {"type": "integer", "default": 5000, "exclusiveMaximum": 1000000}
        },
        "required": ["url"]
    }

    # Processing:
    # 1. Detect optional parameters (those with "default" values)
    # 2. Normalize properties:
    #    - Remove invalid formats ("uri" → removed, only date-time/email/uuid allowed)
    #    - Remove exclusive bounds (exclusiveMaximum → removed)
    #    - Remove title fields (not needed)
    # 3. Decide strict mode:
    #    - If all params required → add "additionalProperties": false
    #    - If optional params exist → leave unset (non-strict mode)

    # Output: Tool-compatible parameters
    {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "..."},
            "max_length": {"type": "integer", "default": 5000, "description": "..."}
        },
        "required": ["url"]
        # Note: NO "additionalProperties" because max_length has a default
    }
```

**Why this matters:**
- OpenAI's strict mode requires ALL properties in `required` array
- Tools with optional parameters (defaults) must use non-strict mode
- Invalid JSON Schema features cause API errors and must be removed

### Step 6: Tool Registration (`core/agent.py`)

The wrapped tools are passed to the Agent:

```python
class SearchAgent(Agent):
    def __init__(self):
        mcp_tools = create_mcp_tools(server_names=["fetch"])
        super().__init__(tools=mcp_tools, ...)
```

Each tool's `construct_schema()` method is called:

```python
def construct_schema(self) -> dict:
    if PROVIDER == "openai":
        # Check if strict mode is configured
        use_strict = self.parameters.get('additionalProperties') is False

        if use_strict:
            return {
                "type": "function",
                "name": "fetch__fetch",
                "description": "Fetches a URL...",
                "parameters": {...},
                "strict": True,  # OpenAI strict mode
            }
        else:
            return {
                "type": "function",
                "name": "fetch__fetch",
                "description": "Fetches a URL...",
                "parameters": {...},
                # No "strict" field = non-strict mode
            }
```

**What this does:**
- Generates provider-specific tool schemas
- Respects the `additionalProperties` setting from schema converter
- Allows MCP tools with optional params to use non-strict mode

### Step 7: Tool Execution

When the LLM calls a tool, the agent invokes `MCPToolWrapper.call()`:

```python
def call(self, **kwargs) -> str:
    # 1. Call client manager
    result = self.client_manager.call_tool(
        server_name=self.server_name,      # "fetch"
        tool_name=self.original_tool_name, # "fetch" (un-namespaced)
        arguments=kwargs,                   # {"url": "https://example.com"}
    )

    # 2. Convert result to string
    converter = MCPSchemaConverter()
    return converter.convert_tool_result(result)
```

**Client manager workflow:**

```python
def call_tool(self, server_name, tool_name, arguments):
    # 1. Create fresh transport from stored config
    transport = self._create_transport(server_name)

    # 2. Create fresh client
    client = Client(transport=transport)

    # 3. Use async with for proper lifecycle
    async with client:
        response = await client.call_tool(name=tool_name, arguments=arguments)
        return response.content
```

**Why fresh transports?**
- Each `asyncio.run()` creates a new event loop
- Cannot reuse transport/client across different event loops
- Fresh transport ensures clean connection for each call
- FastMCP's `keep_alive=True` makes reconnection efficient

### Step 8: Result Conversion

The result is converted to a string for the LLM:

```python
def convert_tool_result(result: Any) -> str:
    # Handle different result types:

    # String → pass through
    if isinstance(result, str):
        return result

    # List of ContentBlocks → extract text
    if isinstance(result, list):
        text_parts = []
        for block in result:
            if block.get("type") == "text":
                text_parts.append(block["text"])
        return "\n".join(text_parts)

    # Dict with content field → recurse
    if isinstance(result, dict) and "content" in result:
        return convert_tool_result(result["content"])

    # Fallback → JSON serialize
    return json.dumps(result, indent=2)
```

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Configuration (mcp_config.py)                                   │
│    MCPServerConfig(name="fetch", command="uvx", args=[...])        │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. Tool Creation (create_mcp_tools)                                │
│    ├─ Filter enabled servers (MCP_FETCH=True)                      │
│    ├─ Initialize MCPClientManager                                  │
│    └─ For each server:                                             │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. Server Initialization (client_manager.start_client)             │
│    ├─ Store config in _server_configs                              │
│    ├─ Create temporary StdioTransport                              │
│    ├─ Spawn MCP server subprocess                                  │
│    ├─ Call client.list_tools()                                     │
│    └─ Cache tools in _discovered_tools                             │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. Tool Wrapping (MCPToolWrapper)                                  │
│    ├─ Namespace: "fetch" → "fetch__fetch"                          │
│    ├─ Convert schema via MCPSchemaConverter                        │
│    ├─ Normalize for OpenAI (remove invalid formats, etc.)          │
│    └─ Create Tool instance with references                         │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. Agent Registration                                               │
│    ├─ Tools passed to Agent.__init__()                             │
│    ├─ construct_schema() called for each tool                      │
│    └─ Schemas sent to LLM provider                                 │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. Tool Execution (when LLM calls tool)                            │
│    ├─ MCPToolWrapper.call(url="https://example.com")               │
│    ├─ client_manager.call_tool(server_name, tool_name, args)       │
│    ├─ Create fresh StdioTransport from config                      │
│    ├─ Create fresh Client with transport                           │
│    ├─ async with client: call_tool(...)                            │
│    ├─ Extract response.content                                     │
│    └─ Convert to string via convert_tool_result()                  │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. Result to LLM                                                    │
│    String result appended to conversation as tool response         │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Enable MCP Servers in `.env`

```bash
# Works with any provider!
PROVIDER=openai  # or ollama, or any other provider
OPENAI_API_KEY=sk-...

# Enable MCP servers
MCP_FETCH=True
MCP_ZIGBEE=False
```

### 2. Add MCP Tools to Your Agent

```python
from smart_home.core.agent import Agent
from smart_home.mcp import create_mcp_tools

class SearchAgent(Agent):
    """Agent with only web fetching capabilities."""
    def __init__(self):
        # Only include fetch MCP server
        mcp_tools = create_mcp_tools(server_names=["fetch"])

        super().__init__(
            tools=mcp_tools,
            system_prompt="You are a research assistant with web fetching capabilities.",
            agent_type="search"
        )
```

**See [agents/search.py](../agents/search.py) for a complete working example.**

### 3. Use the Agent

```python
agent = SearchAgent()

for chunk in agent.stream("What's on this page: https://example.com"):
    print(chunk, end="", flush=True)
```

The agent will:
1. Receive your query
2. Decide to use the `fetch__fetch` tool
3. Call `MCPToolWrapper.call(url="https://example.com")`
4. Connect to MCP server and execute fetch
5. Return the webpage content
6. Generate a response based on the content

## Adding a New MCP Server

### Step 1: Create the Server Configuration

Edit `src/smart_home/mcp/mcp_config.py`:

```python
# Add to server registry
WEATHER_API_SERVER = MCPServerConfig(
    name="weather_api",
    env_var="MCP_WEATHER_API",
    command="npx",
    args=["-y", "@myorg/mcp-server-weather"],
    transport="stdio",  # or "http"
    env=None,  # Optional: {"API_KEY": os.getenv("WEATHER_API_KEY")}
    url=None,  # Required if transport="http"
    allowed_tools=["get_forecast", "get_current"],  # Optional whitelist
)

# Register it
ALL_SERVERS = [
    FETCH_SERVER,
    ZIGBEE_SERVER,
    WEATHER_API_SERVER,  # Add here
]
```

### Step 2: Add Environment Variable

Add to `.env.example`:

```bash
MCP_WEATHER_API=False  # Enable weather API MCP server
```

### Step 3: Enable and Use

```bash
# In your .env
MCP_WEATHER_API=True
```

```python
# In your agent
mcp_tools = create_mcp_tools(server_names=["weather_api"])
```

That's it! The new MCP server will be automatically:
- Connected to when tools are created
- Tools discovered and wrapped
- Ready to use by your agent

## Configuration Options

### `MCPServerConfig` Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | Yes | Server identifier (used in tool namespacing) |
| `env_var` | str | Yes | Environment variable to enable/disable (e.g., `"MCP_FETCH"`) |
| `command` | str | Yes | Executable command (e.g., `"uvx"`, `"npx"`, `"python"`) |
| `args` | list[str] | Yes | Arguments to pass to command |
| `transport` | str | Yes | Transport type: `"stdio"` or `"http"` |
| `env` | dict | No | Environment variables for server process |
| `url` | str | No | URL for HTTP transport (required if `transport="http"`) |
| `allowed_tools` | list[str] | No | Whitelist of tool names (None = allow all) |

### Transport Types

#### stdio Transport (Recommended)

Spawns a subprocess and communicates via stdin/stdout:

```python
MCPServerConfig(
    name="fetch",
    command="uvx",
    args=["mcp-server-fetch"],
    transport="stdio",
)
```

**Best for:**
- Local MCP servers installed via npm/uvx
- Development and testing
- Maximum compatibility

#### HTTP Transport

Connects to a remote HTTP server:

```python
MCPServerConfig(
    name="remote_api",
    command=None,  # Not used for HTTP
    args=[],
    transport="http",
    url="https://api.example.com/mcp",
)
```

**Best for:**
- Production deployments
- Shared MCP servers
- Cloud-hosted tools

**Note:** HTTP transport is not fully implemented yet. See [client_manager.py](client_manager.py:147) for status.

## Provider Support

| Provider | MCP Support | Notes |
|----------|-------------|-------|
| OpenAI   | ✅ Yes      | Full support with schema normalization |
| Ollama   | ✅ Yes      | Full support, provider-agnostic |
| Claude   | ✅ Yes      | Works with any provider supporting function calling |

## Architecture Components

### File Structure

```
src/smart_home/mcp/
├── __init__.py                 # Public API exports
├── mcp_config.py              # Server configuration and registry
├── client_manager.py          # FastMCP client lifecycle management
├── schema_converter.py        # MCP ↔ Tool schema conversion
├── mcp_tools.py              # Tool wrapper and factory
└── README.md                 # This file
```

### Key Classes

#### `MCPServerConfig`
- **Purpose**: Stores configuration for one MCP server
- **Location**: `mcp_config.py`
- **Methods**: `is_enabled()` - checks if env var is "True"

#### `MCPClientManager` (Singleton)
- **Purpose**: Manages MCP server connections and tool execution
- **Location**: `client_manager.py`
- **Key Methods**:
  - `start_client()` - Initialize server, discover tools
  - `call_tool()` - Execute a tool on a server
  - `get_discovered_tools()` - Get cached tool schemas
  - `_create_transport()` - Create fresh transport for execution

#### `MCPSchemaConverter`
- **Purpose**: Convert between MCP and Tool schema formats
- **Location**: `schema_converter.py`
- **Key Methods**:
  - `convert_input_schema()` - MCP inputSchema → Tool parameters
  - `convert_tool_result()` - Tool result → string for LLM
  - `_normalize_property()` - Remove invalid JSON Schema features

#### `MCPToolWrapper`
- **Purpose**: Wraps MCP tool as standard Tool instance
- **Location**: `mcp_tools.py`
- **Inherits**: `Tool` base class
- **Key Methods**:
  - `__init__()` - Create namespaced tool with converted schema
  - `call()` - Execute tool via client manager

## Debugging

### Check Enabled Servers

```python
from smart_home.mcp import get_enabled_mcp_servers

servers = get_enabled_mcp_servers()
for server in servers:
    print(f"{server.name}: {server.command} {' '.join(server.args)}")
```

### Verify Tool Creation

```python
from smart_home.mcp import create_mcp_tools

tools = create_mcp_tools()
print(f"Created {len(tools)} MCP tools")

for tool in tools:
    print(f"  {tool.name}: {tool.description[:60]}...")
```

### Run Tests

```bash
# Run FastMCP integration tests
uv run python tests/test_mcp_fastmcp.py

# Test with SearchAgent
uv run python src/smart_home/driver.py
# Select "search" agent
# Ask: "What's on this page: https://example.com"
```

### Common Issues

#### Tools not discovered
- Check `MCP_<SERVER>=True` in `.env`
- Verify server command is installed (`uvx mcp-server-fetch`)
- Check logs for connection errors

#### Schema validation errors
- Usually means OpenAI strict mode incompatibility
- Check schema_converter.py for normalization rules
- Verify tools with optional params don't have `additionalProperties: false`

#### Connection errors
- Fresh transports created for each call, so shouldn't persist
- Check MCP server is executable and available
- Verify environment variables are set correctly

## Security Considerations

- **Tool Whitelisting**: Use `allowed_tools` to limit which tools are exposed
- **Environment Variables**: Never hardcode secrets in config, use `.env`
- **Server Validation**: Verify MCP server command/URL before adding to registry
- **Transport Security**: Use HTTPS for HTTP transport in production
- **Subprocess Security**: Be careful with `env` parameter - don't expose sensitive env vars

## Examples

### Example 1: Web Fetching Agent

```python
from smart_home.core.agent import Agent
from smart_home.mcp import create_mcp_tools

class SearchAgent(Agent):
    def __init__(self):
        mcp_tools = create_mcp_tools(server_names=["fetch"])

        super().__init__(
            tools=mcp_tools,
            system_prompt="You are a research assistant. Use the fetch tool to access web pages and answer questions based on their content.",
            agent_type="search"
        )

# Usage
agent = SearchAgent()
response = agent.stream("Summarize the latest news from https://news.ycombinator.com")
for chunk in response:
    print(chunk, end="", flush=True)
```

### Example 2: Multi-Tool Agent

```python
from smart_home.core.agent import Agent
from smart_home.mcp import create_mcp_tools
from smart_home.tools.weather import WeatherTool

class HomeAgent(Agent):
    def __init__(self):
        # Mix regular tools and MCP tools
        regular_tools = [WeatherTool()]
        mcp_tools = create_mcp_tools(server_names=["fetch", "zigbee"])

        super().__init__(
            tools=regular_tools + mcp_tools,
            system_prompt="You are a smart home assistant with weather info, web access, and smart home control.",
            agent_type="home"
        )
```

### Example 3: Tool Filtering

```python
# Only allow specific Zigbee tools
ZIGBEE_SERVER = MCPServerConfig(
    name="zigbee",
    env_var="MCP_ZIGBEE",
    command="uvx",
    args=["mcp-server-zigbee"],
    transport="stdio",
    allowed_tools=[
        "list_devices",
        "turn_on_light",
        "turn_off_light",
        # Exclude dangerous tools like "factory_reset"
    ],
)
```

## Advanced Topics

### Custom Schema Normalization

If you need custom schema normalization rules, extend `MCPSchemaConverter`:

```python
class MySchemaConverter(MCPSchemaConverter):
    @staticmethod
    def _normalize_property(prop):
        prop = super()._normalize_property(prop)
        # Add custom normalization
        if prop.get("type") == "array" and "minItems" in prop:
            del prop["minItems"]  # Remove if your LLM doesn't support it
        return prop
```

### Event Loop Management

The client manager uses `asyncio.run()` for each tool call, creating fresh event loops. This is intentional to avoid event loop conflicts. If you need different behavior, modify `client_manager.py:call_tool()`.

### Persistent Connections

Currently, we create fresh transports for each call. FastMCP's `keep_alive=True` makes this efficient. If you want truly persistent connections, you'll need to:
1. Use a background thread with a persistent event loop
2. Store running client instances instead of configs
3. Handle cleanup and reconnection logic

This is not implemented due to complexity, but is possible.

## Next Steps

- [ ] Implement HTTP transport support
- [ ] Add connection pooling for better performance
- [ ] Support for MCP server discovery (auto-detect available servers)
- [ ] Rate limiting for tool execution
- [ ] Metrics and monitoring integration
