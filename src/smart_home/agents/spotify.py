# spotify_agent.py
import os
import requests

from smart_home.core.agent import Agent
from smart_home.tools.spotify.play import SpotifyPlayTool
from smart_home.tools.spotify.pause import SpotifyPauseTool
from smart_home.tools.spotify.switch import SpotifyDeviceSwitchTool
from smart_home.tools.spotify.volume import SpotifyVolumeTool


SPOTIFY_SYSTEM_PROMPT = """
Keep responses short and clear. Only respond to the user in English.

You can control Spotify using the provided tools:
- spotify_play: play a track/album/playlist/artist by URI or simple search query.
- spotify_pause: pause playback.
- spotify_switch_device: transfer playback to a named device or device_id.
- spotify_set_volume: set volume 0-100.

Guidelines:
- If user says “play <something>”, call spotify_play with query=<something>.
- If they mention a device (e.g., “on living room”), pass device="living room".
- For “pause/stop”, call spotify_pause.
- For “volume X%”, call spotify_set_volume with percent=X.
- Prefer minimal wording in responses; confirm success or report errors.
"""

def _fetch_spotify_devices_for_prompt(timeout: float = 6.0) -> list[dict]:
    """
    Fetches the current user's Spotify Connect devices using env-provided OAuth creds.
    Returns a list of {'name': str, 'id': str} items. On any error, returns [].
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN", "").strip()
    if not (client_id and client_secret and refresh_token):
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": os.getenv("SPOTIFY_USER_AGENT", "SmartHomeAssistant/1.0")})

    # Get an access token via refresh token
    try:
        token_resp = session.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(client_id, client_secret),
            timeout=timeout,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
    except Exception:
        return []

    session.headers["Authorization"] = f"Bearer {access_token}"

    # Query devices
    try:
        r = session.get("https://api.spotify.com/v1/me/player/devices", timeout=timeout)
        r.raise_for_status()
        devices = r.json().get("devices", [])
        out = []
        for d in devices:
            name = (d.get("name") or "").strip()
            dev_id = (d.get("id") or "").strip()
            if name and dev_id:
                out.append({"name": name, "id": dev_id})
        return out
    except Exception:
        return []


def _devices_prompt_fragment() -> str:
    """
    Builds a short prompt fragment with device name/id pairs.
    """
    devices = _fetch_spotify_devices_for_prompt()
    if not devices:
        return "\nKnown Spotify devices: none detected.\n"

    lines = ["\nKnown Spotify devices (name → id):"]
    for d in devices:
        # Keep it compact and unambiguous
        lines.append(f"- {d['name']} (id: {d['id']})")
    lines.append("")  # trailing newline
    return "\n".join(lines)


class SpotifyAgent(Agent):
    """An agent specialized for Spotify control. You have access to Spotify tools."""

    def __init__(self):
        # Inject devices (name/id pairs) directly into the system prompt at construction time.
        system_prompt = SPOTIFY_SYSTEM_PROMPT + _devices_prompt_fragment()

        super().__init__(
            system_prompt=system_prompt,
            tools=[
                SpotifyPlayTool(),
                SpotifyPauseTool(),
                SpotifyDeviceSwitchTool(),
                SpotifyVolumeTool(),
            ],
            include_time=True,
        )
