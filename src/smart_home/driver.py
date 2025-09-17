from smart_home.utils.voice_utils import streaming_tts, speech_to_text, text_to_speech
from smart_home.agentic.agents.weather_agent import WeatherAgent
from smart_home.agentic.agents.agent import Agent


# Can pass in prebuilt agent or will create a default one
def converse_with_agent_stream(agent:Agent|None=None):
    if agent is None:
        agent = Agent(system_prompt="You are a helpful friendly smart home assistant.")
    while True:
        user_input = speech_to_text(play_sounds=True)
        if user_input.lower() == "stop":
            print("Exiting the conversation.")
            break

        print(f"User asked: {user_input}")

        def response_stream():
            for chunk in agent.stream(user_input):
                print(chunk, end="", flush=True)
                yield chunk

        streaming_tts(response_stream())
        print()


def converse_with_weather_agent():
    agent = WeatherAgent()
    while True:
        user_input = speech_to_text(play_sounds=True)
        if user_input.lower() == "stop":
            print("Exiting the conversation.")
            break

        print(f"User asked: {user_input}")

        # Collect full response
        response_chunks = []
        for chunk in agent.stream(user_input):
            print(chunk, end="", flush=True)
            response_chunks.append(chunk)

        full_response = "".join(response_chunks)
        print("\nAgent response:", full_response)

        # Speak the response
        text_to_speech(full_response)


if __name__ == "__main__":
    agent = WeatherAgent()
    converse_with_agent_stream(agent)