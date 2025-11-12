# src/smart_home/agents/weather.py
from __future__ import annotations
from typing import Optional

from smart_home.core.agent import Agent
from smart_home.tools.weather.weather_tool import WeatherTool


WEATHER_SYSTEM_PROMPT = """
Keep responses short and clear.

You can call tools to fetch weather data:
- get_weather: Get forecast from weather.gov with optional time/granularity.

Guidelines:
- If user asks about a specific time (e.g., "6pm today"), call get_weather with an ISO-8601 timestamp (check the tool description for timezone requirements).
- For current weather, use "now" instead of a timestamp.
- Be concise in responses.
"""

class WeatherAgent(Agent):

    def __init__(self, model: Optional[str] = None, *, include_time: bool = True, session=None):
        super().__init__(
            model=model,
            system_prompt=WEATHER_SYSTEM_PROMPT,
            tools=[WeatherTool()],
            include_time=include_time,
            agent_type="weather",
            session=session,
        )

if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What's the weather around 6pm today at home?"
    agent = WeatherAgent()
    for chunk in agent.stream(q):
        print(chunk, end="", flush=True)
    print()