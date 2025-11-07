import requests
import os
from smart_home.agentic.agents.agent import Tool, Agent
from dotenv import load_dotenv

load_dotenv()

class WeatherTool(Tool):
    """Tool that fetches current weather information for a given location."""

    def __init__(self):
        name = "get_weather"
        description = "Fetch current weather for a location, or 'home' if none is given"
        params = {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City, region, or 'home' for default location",
                    "default": "home"
                }
            },
            "required": ["location"] # Must have all params required, allow null as valid type if param is optional
        }

        super().__init__(name, description, params)


    def call(self, location: str = 'home') -> str:
        """Fetch weather info in JSON format and return a summary string."""

        url = f"http://wttr.in/{location}?format=j1" if location != 'home' else f"http://wttr.in/{os.getenv('COORDS')}?format=j1"

        try:
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            data = res.json()

            current = data["current_condition"][0]

            summary = (
                f"The weather in {location} is {current['weatherDesc'][0]['value'].lower()}, "
                f"with a temperature of {current['temp_F']}°F "
                f"(feels like {current['FeelsLikeF']}°F). "
                f"Humidity is {current['humidity']}%. Tell this to the user."
            )

            return summary

        except Exception as e:
            return f"Error fetching weather: {e}"
        
