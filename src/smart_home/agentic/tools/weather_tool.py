import requests
import os
from smart_home.agentic.agent import Tool, Agent
from dotenv import load_dotenv

load_dotenv()

class WeatherTool(Tool):
    """Tool that fetches current weather information for a given location."""

    def __init__(self):
        schema = {
        "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the weather in a given location, or 'home' if no location is provided",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The location to get the weather for, or 'home' for the current location",
                            "default": "home"
                        }
                    },
                    "required": ["location"]
                }
            }
        }

        super().__init__(
            name="get_weather",
            schema=schema
        )

    def call(self, location: str = 'home') -> str:
        """Fetch weather info in JSON format and return a summary string."""

        url = f"http://wttr.in/{location}?format=j1" if location != 'home' else f"http://wttr.in/{os.getenv("COORDS")}?format=j1"

        try:
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            data = res.json()

            current = data["current_condition"][0]
            area = data.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", location or "your area")

            summary = (
                f"The weather in {area} is {current['weatherDesc'][0]['value'].lower()}, "
                f"with a temperature of {current['temp_F']}°F "
                f"(feels like {current['FeelsLikeF']}°F). "
                f"Humidity is {current['humidity']}%, "
            )

            return summary

        except Exception as e:
            return f"Error fetching weather: {e}"
        

if __name__ == "__main__":

    weather_agent = Agent(system_prompt="You are a helpful assistant. Use your tools to answer questions", tools=[WeatherTool()])

    while True:
        prompt = input("Prompt: ").strip()
        if prompt == "exit":
            break

        if not prompt:
            raise SystemExit("A non-empty prompt is required.")

        for chunk in weather_agent.stream(prompt):
            print(chunk, end="", flush=True)
        print()

    print(weather_agent.messages)