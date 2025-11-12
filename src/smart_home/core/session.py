import json
import logging
import random
import string
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from smart_home.config.paths import SESSIONS_DIR

if TYPE_CHECKING:
    from smart_home.core.agent import Agent

logger = logging.getLogger(__name__)


def _generate_session_id(length: int = 8) -> str:
    """Generate a random session ID using alphanumeric characters."""
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choices(characters, k=length))


class Session:
    """
    Manages session state and message coordination across multi-agent interactions.

    Allows per session logging, and enables sub-agents to inject responses directly

    Example flow:
    1. User asks HomeAgent to "play jazz"
    2. HomeAgent calls call_spotify_agent tool
    3. SpotifyAgent processes request and generates response
    4. CallSpotifyAgentTool calls session.append_to_primary_agent() with response
    5. HomeAgent's tool loop sees complete message history, exits WITHOUT extra LLM call
    """

    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        self.session_id: str = _generate_session_id()
        self.created_at: datetime = datetime.now()
        self.primary_agent: Optional['Agent'] = None
        self.subagents: Dict[str, 'Agent'] = {}  # Track all sub-agents by agent_id
        self.metadata: Dict[str, Any] = metadata or {}

        logger.info(
            f"Created session {self.session_id}",
            extra={"session_id": self.session_id, "created_at": self.created_at.isoformat()}
        )

    def set_primary_agent(self, agent: 'Agent') -> None:
        """
        Register the main agent for this session.

        Args:
            agent: The primary agent (typically HomeAgent, WeatherAgent, or SpotifyAgent)
        """
        self.primary_agent = agent
        logger.info(
            f"Set primary agent for session {self.session_id}",
            extra={
                "session_id": self.session_id,
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type
            }
        )

    def register_subagent(self, agent: 'Agent') -> None:
        """
        Register a sub-agent that was created during this session.

        This tracks all sub-agents for debugging, analytics, and potential reuse.

        Args:
            agent: The sub-agent to register (e.g., SpotifyAgent called by HomeAgent)
        """
        self.subagents[agent.agent_id] = agent
        logger.info(
            f"Registered sub-agent {agent.agent_id} ({agent.agent_type}) in session {self.session_id}",
            extra={
                "session_id": self.session_id,
                "subagent_id": agent.agent_id,
                "subagent_type": agent.agent_type,
                "total_subagents": len(self.subagents)
            }
        )

    def get_subagent(self, agent_id: str) -> Optional['Agent']:
        """
        Retrieve a sub-agent by its agent_id.

        Args:
            agent_id: The agent_id to look up

        Returns:
            The Agent instance if found, None otherwise
        """
        return self.subagents.get(agent_id)

    def append_to_primary_agent(
        self,
        role: str,
        content: str,
    ) -> None:
        """
        Directly append a message to the primary agent's history.

        This is the KEY method for sub-agent result injection:
        - Sub-agent executes and generates response
        - Tool calls this method to inject response into parent's history
        - Parent agent's next loop iteration sees complete history, exits without LLM call

        Args:
            role: Message role (typically "assistant" for sub-agent responses)
            content: The message content to append

        Raises:
            RuntimeError: If no primary agent is registered

        Note:
            Messages are kept clean (no metadata field) to ensure OpenAI API compliance.
            Tracking information is logged separately for debugging.
        """
        if not self.primary_agent:
            raise RuntimeError("No primary agent registered in session")

        # Keep message format clean for OpenAI API compliance
        message = {"role": role, "content": content}
        self.primary_agent.messages.append(message)

        logger.debug(
            f"Injected message into primary agent's history",
            extra={
                "session_id": self.session_id,
                "agent_id": self.primary_agent.agent_id,
                "role": role,
                "content_preview": content[:100],
            }
        )

    def get_primary_messages(self) -> List[Dict[str, Any]]:
        """
        Access the primary agent's message history.

        Returns:
            List of message dictionaries, or empty list if no primary agent
        """
        if not self.primary_agent:
            return []
        return self.primary_agent.messages

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize session for logging/persistence.

        Returns:
            Dictionary representation of session state
        """
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "primary_agent": {
                "agent_id": self.primary_agent.agent_id if self.primary_agent else None,
                "agent_type": self.primary_agent.agent_type if self.primary_agent else None,
                "model": self.primary_agent.model if self.primary_agent else None,
                "provider": self.primary_agent.provider if self.primary_agent else None,
                "messages": self.primary_agent.messages if self.primary_agent else [],
            },
            "subagents": {
                agent_id: {
                    "agent_type": agent.agent_type,
                    "model": agent.model,
                    "provider": agent.provider,
                    "messages": agent.messages,
                }
                for agent_id, agent in self.subagents.items()
            },
            "metadata": self.metadata,
        }

    def save(self) -> None:
        """
        Save the complete session state to sessions/{session_id}.json.

        This includes:
        - Session metadata
        - Primary agent's complete message history
        - All sub-agents' message histories
        - Conversation flow and tool usage
        """
        try:
            # Create session file path
            session_file = SESSIONS_DIR / f"{self.session_id}.json"

            # Serialize session state
            session_data = self.to_dict()

            # Write to file
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            logger.debug(
                f"Saved session {self.session_id}",
                extra={
                    "session_id": self.session_id,
                    "session_file": str(session_file),
                    "message_count": len(self.primary_agent.messages) if self.primary_agent else 0,
                    "subagent_count": len(self.subagents)
                }
            )

        except Exception as e:
            logger.error(
                f"Failed to save session {self.session_id}: {e}",
                exc_info=True,
                extra={"session_id": self.session_id}
            )
