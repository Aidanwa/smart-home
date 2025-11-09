from smart_home.core.agent import Tool
from smart_home.tools.spotify.utils import _spotify

class SpotifyDeviceSwitchTool(Tool):
    def __init__(self):
        name = "spotify_switch_device"
        description = "Transfer playback to a device by name or id."
        params = {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Target device name substring or device_id."
                },
                "force_play": {
                    "type": "boolean",
                    "description": "Whether to start playback on the new device.",
                    "default": True
                }
            },
            "required": ["device", "force_play"]
        }
        super().__init__(name, description, params)

    def call(self, device: str, force_play: bool = True):
        try:
            device_id = _spotify.resolve_device_id(device)
            if not device_id:
                return "Error: device not found."
            _spotify.transfer(device_id=device_id, force_play=force_play)
            return "OK: device switched."
        except Exception as e:
            return f"Error: {e}"