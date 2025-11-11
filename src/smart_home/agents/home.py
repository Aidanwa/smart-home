from smart_home.core.agent import Agent
from smart_home.tools.weather.weather_tool import WeatherTool
from smart_home.tools.spotify.spotify_agent import CallSpotifyAgentTool

HOME_SYSTEM_PROMPT = """
    You are a home assistant with access to a weather tool and a Spotify music tool. Be as concise as possible, because your responses are to be read aloud.
"""

class HomeAgent(Agent):

    def __init__(self):

        super().__init__(
            system_prompt=HOME_SYSTEM_PROMPT,
            tools=[
                WeatherTool(),
                CallSpotifyAgentTool(),
            ],
            include_time=True,
            agent_type="home",
        )

