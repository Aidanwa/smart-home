from smart_home.agentic.agents.agent import Agent
from smart_home.agentic.tools.weather_tool import WeatherTool


WEATHER_SYSTEM_PROMPT = """
    Keep responses short and clear. Only respond to the user in english.
"""

class WeatherAgent(Agent):
    """An agent specialized for answering weather questions."""

    def __init__(self):

        super().__init__(
            system_prompt=WEATHER_SYSTEM_PROMPT,
            tools=[WeatherTool()],
            model="llama3.1:8b",
            include_time=True
        )

