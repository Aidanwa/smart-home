from smart_home.core.agent import Tool
from smart_home.tools.spotify.utils import _spotify
import os

class SpotifyPlayTool(Tool):
    def __init__(self):
        name = "spotify_play"
        description = "Start/resume playback. Provide a URI/context_uri or a simple search query. You must provide a device"
        params = {
            "type": "object",
            "properties": {
                "uris": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "List of track URIs to play (e.g., 'spotify:track:...')."
                },
                "context_uri": {
                    "type": ["string", "null"],
                    "description": "Album/playlist/artist URI to play (e.g., 'spotify:album:...')."
                },
                "query": {
                    "type": ["string", "null"],
                    "description": "Fallback search query if no URIs provided (e.g., 'lofi beats')."
                },
                "query_type": {
                    "type": "string",
                    "enum": ["track", "album", "playlist", "artist"],
                    "description": "Type for search-based playback.",
                    "default": "track"
                },
                "device": {
                    "type": "string",
                    "description": "Device name substring or device_id."
                },
                "position_ms": {
                    "type": "integer",
                    "description": "Start position in ms.",
                    "default": 0
                },
                "market": {
                    "type": ["string", "null"],
                    "description": "Market for search.",
                    "default": os.getenv("SPOTIFY_MARKET", "US")
                },
            },
            "required": ["market", "device", "position_ms", "query_type", "query", "context_uri", "uris"]
        }
        super().__init__(name, description, params)

    def call(self, uris=None, context_uri=None, query=None, query_type="track", device=None, position_ms=0, market="US"):
        try:
            device_id = _spotify.resolve_device_id(device)
            if not uris and not context_uri and query:
                item = _spotify.search_one(query, query_type, market)
                if not item:
                    return "Error: No search results."
                if query_type == "track":
                    uris = [item["uri"]]
                else:
                    context_uri = item["uri"]
            _spotify.play(uris=uris, context_uri=context_uri, device_id=device_id, position_ms=position_ms)
            return "OK: playing."
        except Exception as e:
            return f"Error: {e}"