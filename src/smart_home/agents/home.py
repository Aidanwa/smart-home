from smart_home.core.agent import Agent
from smart_home.tools.weather.weather_tool import WeatherTool
from smart_home.tools.spotify.spotify_agent import CallSpotifyAgentTool
from smart_home.tools.zigbee.set_devices import SetDevicesTool
from smart_home.tools.zigbee.get_devices import GetDevicesTool

from smart_home.utils.home_utils import get_all_devices_summary, get_bedroom_temperature

import logging
logger = logging.getLogger(__name__)

from smart_home.mcp_integration import create_mcp_tools

HOME_SYSTEM_PROMPT_TEMPLATE = """
You are a home assistant. Be as concise as possible, because your responses are to be read aloud. 
Don't include any extraneous information, and don't be verbose. 
The current bedroom temperature is {bedroom_temp}.
You have access to the following devices:

{devices_list}
"""

class HomeAgent(Agent):

    def __init__(self, session=None):

        mcp_tools = create_mcp_tools(server_names=["fetch"])

        try:
            devices_list = get_all_devices_summary()
        except Exception as e:
            logger.warning(f"Failed to fetch devices for system prompt: {e}")
            devices_list = "Unable to fetch device list. Ensure the Zigbee API server is running."
        temp = get_bedroom_temperature()

        system_prompt = HOME_SYSTEM_PROMPT_TEMPLATE.format(devices_list=devices_list, bedroom_temp=temp)
        
        tools = [
            WeatherTool(),
            CallSpotifyAgentTool(),
            SetDevicesTool(),
            GetDevicesTool(),
        ] + mcp_tools

        super().__init__(
            system_prompt=system_prompt,
            tools=tools,
            include_time=True,
            agent_type="home",
            session=session,
        )

