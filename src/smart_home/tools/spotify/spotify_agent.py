from smart_home.agents.spotify import SpotifyAgent
from smart_home.core.agent import Tool

class CallSpotifyAgentTool(Tool):
    def __init__(self):
        name = "call_spotify_agent"
        description = "Calls a Spotify agent to handle music tasks"
        params = {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user's music-related request or command."
                },
            },
            "required": ["query"]
        }
        super().__init__(name, description, params)

    def call(self, query: str):
        try:
            spotify_agent = SpotifyAgent()

            def response_stream():
                for chunk in spotify_agent.stream(query):
                    print(chunk, end="", flush=True)
                    yield chunk
                    
            response = "".join(response_stream())
            return response
        except Exception as e:
            return f"Error: {e}"