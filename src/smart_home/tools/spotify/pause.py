from smart_home.core.agent import Tool
from smart_home.tools.spotify.utils import _spotify

class SpotifyPauseTool(Tool):
    def __init__(self):
        name = "spotify_pause"
        description = "Pause current playback."
        params = {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Device name substring or device_id (optional)."
                }
            },
            "required": ["device"]
        }
        super().__init__(name, description, params)

    def call(self, device=None):
        try:
            device_id = _spotify.resolve_device_id(device)
            _spotify.pause(device_id=device_id)
            return "OK: paused."
        except Exception as e:
            return f"Error: {e}"