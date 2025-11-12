import logging
from smart_home.agents.spotify import SpotifyAgent
from smart_home.core.agent import Tool

logger = logging.getLogger(__name__)


class CallSpotifyAgentTool(Tool):
    def __init__(self, session=None):
        name = "call_spotify_agent"
        description = "Calls a Spotify agent to handle music tasks"
        params = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user's music-related request or command."
                },
            },
            "required": ["query"]
        }
        super().__init__(name, description, params, session=session)

    def call(self, query: str):
        try:
            # Create SpotifyAgent with session reference
            spotify_agent = SpotifyAgent(session=self.state_session)

            # Register sub-agent in session for tracking
            if self.state_session:
                self.state_session.register_subagent(spotify_agent)

            def response_stream():
                for chunk in spotify_agent.stream(query):
                    yield chunk

            response = "".join(response_stream())

            # CRITICAL: If session exists, inject response into primary agent's history
            # This prevents the parent agent from making a redundant LLM call
            if self.state_session and self.state_session.primary_agent:
                self.state_session.append_to_primary_agent(
                    role="assistant",
                    content=response,
                )
                # Log tracking info separately (not in message for OpenAI compliance)
                logger.info(
                    f"Injected SpotifyAgent response into primary agent",
                    extra={
                        "session_id": self.state_session.session_id,
                        "subagent_id": spotify_agent.agent_id,
                        "query": query,
                        "source": "call_spotify_agent",
                        "response_preview": response[:100]
                    }
                )

            return response
        except Exception as e:
            logger.error(f"CallSpotifyAgentTool failed: {e}", exc_info=True)
            return f"Error: {e}"