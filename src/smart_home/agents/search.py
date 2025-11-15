# src/smart_home/agents/search.py
from __future__ import annotations
from typing import Optional

from smart_home.core.agent import Agent
from smart_home.mcp_integration import create_mcp_tools


SEARCH_SYSTEM_PROMPT = """
You are a research assistant with access to web fetching capabilities via MCP.

Keep responses informative but concise.

You can fetch content from URLs to answer user questions:
- Use the fetch MCP server to retrieve web pages, APIs, or online resources
- Analyze and summarize the fetched content
- Provide citations and sources when applicable

Guidelines:
- Always verify information from fetched sources
- Be transparent about what you found and where
- If a URL fails or returns an error, explain what went wrong
- Prioritize authoritative and recent sources
- Be very concise in your answers, focusing on key points, because they will be spoken aloud.
"""


class SearchAgent(Agent):

    def __init__(
        self,
        model: Optional[str] = None,
        *,
        include_time: bool = True,
        session=None
    ):
        # Create MCP tools, but only include the fetch server
        mcp_tools = create_mcp_tools(server_names=["fetch"])

        super().__init__(
            model=model,
            system_prompt=SEARCH_SYSTEM_PROMPT,
            tools=mcp_tools,
            include_time=include_time,
            agent_type="search",
            session=session,
        )


