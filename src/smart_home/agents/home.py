from smart_home.core.agent import Agent
from smart_home.tools.weather.weather_tool import WeatherTool
from smart_home.tools.spotify.spotify_agent import CallSpotifyAgentTool
from smart_home.mcp_integration import create_mcp_tools

HOME_SYSTEM_PROMPT = """
You are a home assistant with access to a weather tool and a Spotify music tool. Be as concise as possible, because your responses are to be read aloud. 
Don't include any extraneous information, and don't be verbose.
"""

class HomeAgent(Agent):

    def __init__(self, session=None):

        mcp_tools = create_mcp_tools(server_names=["fetch"])
        
        tools = [
            WeatherTool(),
            CallSpotifyAgentTool(),
        ] + mcp_tools

        super().__init__(
            system_prompt=HOME_SYSTEM_PROMPT,
            tools=tools,
            include_time=True,
            agent_type="home",
            session=session,
        )

