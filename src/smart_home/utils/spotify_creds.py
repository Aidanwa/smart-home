import requests, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

client_id = input("Client ID: ").strip()
client_secret = input("Client Secret: ").strip()
redirect_uri = "http://127.0.0.1:8888/callback"
scopes = "user-read-playback-state user-modify-playback-state user-read-currently-playing"

auth_url = (
    "https://accounts.spotify.com/authorize?"
    + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scopes
    })
)

print("Opening browser for Spotify authorization...")
webbrowser.open(auth_url)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if "/callback" in self.path:
            code = urllib.parse.parse_qs(self.path.split("?", 1)[1])["code"][0]
            self.send_response(200); self.end_headers()
            self.wfile.write(b"You can close this tab now.")
            token_resp = requests.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                auth=(client_id, client_secret),
            ).json()
            print("\nAccess Token:", token_resp.get("access_token"))
            print("Refresh Token:", token_resp.get("refresh_token"))
            exit()

HTTPServer(("127.0.0.1", 8888), Handler).serve_forever()