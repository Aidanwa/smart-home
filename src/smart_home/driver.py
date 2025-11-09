from smart_home.utils.voice_utils import streaming_tts, speech_to_text, wait_for_wake_word
from smart_home.agents.weather import WeatherAgent
from smart_home.agents.spotify import SpotifyAgent
from smart_home.agents.home import HomeAgent
from smart_home.core.agent import Agent
import os
import json

# Load .env early
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


NAME_TO_AGENT = {
    "weather": WeatherAgent,
    "spotify": SpotifyAgent,
    "home": HomeAgent,
}

def select_agent_by_name(name: str) -> Agent|None:
    agent_class = NAME_TO_AGENT.get(name.lower())
    if agent_class:
        return agent_class()
    return None


def converse_with_agent(Agent: Agent | None = None):
    if Agent is not None:
        agent = Agent
    else:
        sysprompt = input("Enter system prompt for custom agent (or press Enter for default): ")
        agent = Agent(system_prompt=sysprompt.strip())

    wake_threshold = float(os.getenv("WAKE_THRESHOLD", "0.5").strip() or 0.5)
    wake_model_env = os.getenv("WAKE_MODEL_PATH", "").strip()
    wake_models = [p.strip() for p in wake_model_env.split(",") if p.strip()] if wake_model_env else None

    while True:
        if os.getenv("SPEECH_TO_TEXT", "False").lower() == "true":
            wait_for_wake_word(model_paths=wake_models, threshold=wake_threshold)
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
        with open("debug_messages.json", "w", encoding="utf-8") as f:
            json.dump(agent.messages, f, ensure_ascii=False, indent=2)


def main():
    agent_name = input("Enter agent name (or press Enter for custom agent): ").strip()
    if agent_name:
        agent = select_agent_by_name(agent_name)
        if agent is None:
            print(f"No agent found with the name '{agent_name}'. Exiting.")
            return
        print(f"Using '{agent_name}' agent for conversation.")
        converse_with_agent(Agent=agent)
    else:
        converse_with_agent()


if __name__ == "__main__":
    main()