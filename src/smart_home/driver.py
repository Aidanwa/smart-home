from smart_home.utils.voice_utils import streaming_tts, speech_to_text  # , wait_for_wake_word
from smart_home.agents.weather import WeatherAgent
from smart_home.agents.spotify import SpotifyAgent
from smart_home.agents.home import HomeAgent
from smart_home.core.agent import Agent
from smart_home.core.session import Session
import os
import logging
from dotenv import load_dotenv
from smart_home.config import logging as logging_config
# from smart_home.config.paths import MODELS_DIR  # Unused while wake word is disabled

load_dotenv(override=True)

# Initialize logging system
logging_config.configure()
logger = logging.getLogger(__name__)

NAME_TO_AGENT = {
    "weather": WeatherAgent,
    "spotify": SpotifyAgent,
    "home": HomeAgent,
}

def select_agent_by_name(name: str, session: Session = None) -> Agent|None:
    agent_class = NAME_TO_AGENT.get(name.lower())
    if agent_class:
        return agent_class(session=session)
    return None


def converse_with_agent(Agent: Agent | None = None, session: Session | None = None):
    # Create session if not provided
    if session is None:
        session = Session()

    if Agent is not None:
        agent = Agent
        # Agent already has session from main(), just verify it's set
        if agent.session is None:
            agent.session = session
            # Pass session to tools
            for tool in agent.tools:
                if hasattr(tool, 'state_session'):
                    tool.state_session = session
    else:
        sysprompt = input("Enter system prompt for custom agent (or press Enter for default): ")
        agent = Agent(system_prompt=sysprompt.strip(), session=session)

    # Link session to primary agent bidirectionally (only if not already set)
    if session.primary_agent is None:
        session.set_primary_agent(agent)

    logger.info(
        f"Starting conversation with session {session.session_id}",
        extra={
            "session_id": session.session_id,
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type
        }
    )

    # ------------------------ WAKE WORD DISABLED ------------------------
    # Wake word detection is currently disabled due to openWakeWord incompatibility
    # See docs/WAKEWORD_INVESTIGATION.md for details
    # TODO: Implement Picovoice Porcupine as alternative
    # --------------------------------------------------------------------
    # wake_model_dir = MODELS_DIR / "openwakeword"
    # wake_model = "alexa_v0.1.onnx"
    # wake_models = [str(wake_model_dir / wake_model)]
    # --------------------------------------------------------------------

    while True:
        if os.getenv("SPEECH_TO_TEXT", "False").lower() == "true":
            # WAKE WORD DISABLED - direct STT for now
            # wait_for_wake_word(model_paths=wake_models, threshold=0.2)
            print("\nListening...")
            user_input = speech_to_text(play_sounds=True)
            print("You:", user_input)
        else:
            user_input = input("You: ")

        if not user_input:
            continue

        if user_input.lower() in ("stop", "exit"):
            print("Exiting the conversation.")
            break

        def response_stream():
            for chunk in agent.stream(user_input):
                print(chunk, end="", flush=True)
                yield chunk

        print("\nAI: ", end="")

        if os.getenv("TEXT_TO_SPEECH", "False").lower() == "true":
            streaming_tts(response_stream(), voice="Zira")
        else:
            for _ in response_stream():
                pass

        print("\n")

        session.save() # Update saved session after each interactions


def main():
    agent_name = input("Enter agent name (or press Enter for custom agent): ").strip()
    if agent_name:
        # Create session first
        session = Session()
        agent = select_agent_by_name(agent_name, session=session)
        if agent is None:
            logger.error(f"No agent found with the name '{agent_name}'")
            print(f"No agent found with the name '{agent_name}'. Exiting.")
            return
        # Set primary agent in session
        session.set_primary_agent(agent)
        logger.info(f"Selected agent: {agent_name}")
        print(f"Using '{agent_name}' agent for conversation.")
        converse_with_agent(Agent=agent, session=session)
    else:
        converse_with_agent()


if __name__ == "__main__":
    main()