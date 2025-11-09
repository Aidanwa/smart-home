from smart_home.core.agent import Tool
from smart_home.tools.spotify.utils import _spotify

class SpotifyVolumeTool(Tool):
    def __init__(self):
        name = "spotify_set_volume"
        description = "Set playback volume (0-100)."
        params = {
            "type": "object",
            "properties": {
                "percent": {
                    "type": "integer",
                    "description": "Volume percent-100."
                },
                "device": {
                    "type": "string",
                    "description": "Device name substring or device_id (optional)."
                }
            },
            "required": ["percent", "device"]
        }
        super().__init__(name, description, params)

    def call(self, percent: int, device=None):
        try:
            device_id = _spotify.resolve_device_id(device)
            _spotify.set_volume(percent=percent, device_id=device_id)
            return f"OK: volume {max(0, min(100, int(percent)))}%."
        except Exception as e:
            return f"Error: {e}"