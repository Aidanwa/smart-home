###  Setting up Spotify API Access (Refresh Token Guide)

Your Smart Home Assistant can control Spotify playback using your personal account.  
To enable this, you’ll need to create a Spotify Developer App and generate a **refresh token** that allows the agent to authenticate securely.

---

#### 1️ Create a Spotify Developer App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications).  
2. Click **“Create App.”**  
3. Fill in the details:
   - **App Name:** SmartHomeAssistant (or any name you like)
   - **Redirect URI:** Use one of the following:
     - If you are running locally (recommended for testing):
       ```
       http://127.0.0.1:8888/callback
       ```
       **Note:** `localhost` is not allowed — you must use an explicit loopback IP (`127.0.0.1` or `[::1]`).
     - If deploying remotely, you may use an HTTPS callback, e.g.:
       ```
       https://example.com/callback
       ```
4. Save your app.  
5. Copy your **Client ID** and **Client Secret** — you’ll need these later.

---

#### Run a Local Auth Script (One-Time Setup)

Run the following Python script to complete the OAuth flow and obtain your **refresh token**.

```
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
```

This script will:
- Launch a browser window for Spotify login and authorization.
- Output your **Access Token** and **Refresh Token** in the console.

---

#### Add Credentials to `.env`

After running the script, copy the tokens into your `.env` file:

```
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REFRESH_TOKEN=your_refresh_token_here
```

---

#### Test the Integration

Once your environment is configured, you can test Spotify connectivity:

```
python -m smart_home.agentic.tools.spotify_tools
```

If authentication succeeds, your Smart Home Assistant will be able to query available devices and control playback.

---

#### Security and Compliance Notes

- **Redirect URI Rules (required by Spotify):**
  - Always use **HTTPS**, unless using a loopback IP (`127.0.0.1` or `[::1]`).
  - **Do not** use `localhost` — it is explicitly disallowed.
  - If the port number may vary dynamically, you can register the redirect URI **without** the port and append it during authorization (supported only for loopback IPs).

- **Examples of valid redirect URIs:**
  - ```
    https://example.com/callback
    ```
  - ```
    http://127.0.0.1:8000/callback
    ```
  - ```
    http://[::1]:8000/callback
    ```

