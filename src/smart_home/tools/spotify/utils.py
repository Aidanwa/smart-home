import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

# ---------- Minimal shared Spotify client ----------

class _SpotifyClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": os.getenv("SPOTIFY_USER_AGENT", "SmartHomeAssistant/1.0")
        })
        self.base = "https://api.spotify.com/v1"
        self.token_url = "https://accounts.spotify.com/api/token"
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
        self.refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN", "").strip()
        self._access_token = None
        self._expiry_ts = 0

    def _ensure_token(self):
        if self._access_token and time.time() < self._expiry_ts - 30:
            return
        if not (self.client_id and self.client_secret and self.refresh_token):
            raise RuntimeError("Spotify OAuth env vars missing.")
        resp = self.session.post(
            self.token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            },
            auth=(self.client_id, self.client_secret),
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._expiry_ts = time.time() + int(data.get("expires_in", 3600))
        self.session.headers["Authorization"] = f"Bearer {self._access_token}"

    def _request(self, method, path, *, params=None, json=None):
        self._ensure_token()
        r = self.session.request(method, f"{self.base}{path}", params=params, json=json, timeout=8.0)
        if r.status_code == 204:
            return {}
        r.raise_for_status()
        return r.json()

    # Helpers kept minimal for small models:
    def list_devices(self):
        return self._request("GET", "/me/player/devices").get("devices", [])

    def resolve_device_id(self, device_or_id: str | None):
        if not device_or_id:
            return None
        # If looks like an id, just use it
        if len(device_or_id) > 10 and " " not in device_or_id:
            return device_or_id
        # Else try name contains match
        for d in self.list_devices():
            logger.debug(f"Spotify device found: {d.get('name', 'Unknown')}", extra={"device": d})
            if device_or_id.lower() in (d.get("name") or "").lower():
                return d.get("id")
        return None

    def search_one(self, q: str, typ: str, market: str = "US"):
        data = self._request("GET", "/search", params={"q": q, "type": typ, "limit": 1, "market": market})
        bucket = data.get(f"{typ}s", {}).get("items", [])
        return bucket[0] if bucket else None

    # Thin wrappers:
    def play(self, *, uris=None, context_uri=None, device_id=None, position_ms=None):
        body = {}
        if uris: body["uris"] = uris
        if context_uri: body["context_uri"] = context_uri
        if position_ms is not None: body["position_ms"] = int(position_ms)
        return self._request("PUT", "/me/player/play", params={"device_id": device_id} if device_id else None, json=body or {})

    def pause(self, *, device_id=None):
        return self._request("PUT", "/me/player/pause", params={"device_id": device_id} if device_id else None)

    def transfer(self, *, device_id: str, force_play: bool = True):
        return self._request("PUT", "/me/player", json={"device_ids": [device_id], "play": force_play})

    def set_volume(self, *, percent: int, device_id=None):
        percent = max(0, min(100, int(percent)))
        return self._request("PUT", "/me/player/volume", params={"volume_percent": percent, **({"device_id": device_id} if device_id else {})})


_spotify = _SpotifyClient()