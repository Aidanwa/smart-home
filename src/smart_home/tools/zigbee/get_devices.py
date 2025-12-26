import os
import requests
from smart_home.core.agent import Tool
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

class GetDevicesTool(Tool):
    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url or os.getenv("ZIGBEE_API_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("ZIGBEE_API_KEY")

        name = "get_zigbee_devices"
        description = (
            "Get detailed current state information for one or more Zigbee devices. "
            "Use this to check the current status of devices if necessary. Don't use unless you need to." \
            "Primarily for debugging or verification purposes, or answering questions."
        )
        params = {
            "type": "object",
            "properties": {
                "device_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of device friendly names to query. For a single device, still use an array format: ['DeviceName']."
                },
            },
            "required": ["device_names"],
        }
        super().__init__(name, description, params)

    def _request(self, method: str, path: str, json: dict | None = None, timeout: int = 5):
        url = self.base_url.rstrip("/") + path
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return requests.request(method, url, headers=headers, json=json, timeout=timeout)

    def _get_single_device(self, device_name):
        """Get a single device's state. Returns (device_name, success, data)."""
        try:
            resp = self._request(
                "GET",
                f"/api/devices/{device_name}",
            )

            if resp.status_code == 200:
                return (device_name, True, resp.json())
            else:
                return (device_name, False, f"API returned {resp.status_code} - {resp.text}")
        except Exception as e:
            return (device_name, False, f"request failed - {e}")

    def call(self, device_names):
        # Ensure device_names is a list
        if isinstance(device_names, str):
            device_names = [device_names]

        results = []
        errors = []

        # Get all device states in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all device query tasks
            future_to_device = {
                executor.submit(self._get_single_device, device_name): device_name
                for device_name in device_names
            }

            # Collect results as they complete
            for future in as_completed(future_to_device):
                device_name, success, data = future.result()
                if success:
                    results.append(self._format_device_state(device_name, data))
                else:
                    errors.append(f"{device_name}: {data}")

        # Format response
        summary = []
        if results:
            summary.append(f"Retrieved state for {len(results)} device(s):\n")
            summary.extend(results)

        if errors:
            if results:
                summary.append("\nErrors:")
            summary.extend(errors)

        return "\n".join(summary)

    def _format_device_state(self, device_name, data):
        """Format device state data into a readable string."""
        lines = [f"• {device_name}:"]

        if isinstance(data, dict):
            state_parts = []

            # Power state
            if "state" in data and data["state"] is not None:
                state_parts.append(f"state={data['state']}")

            # Brightness
            if "brightness" in data and data["brightness"] is not None:
                brightness = data["brightness"]
                brightness_pct = int((brightness / 254) * 100)
                state_parts.append(f"brightness={brightness_pct}% ({brightness}/254)")

            # Color temperature
            if "color_temp" in data and data["color_temp"] is not None:
                state_parts.append(f"color_temp={data['color_temp']} mireds")

            # Temperature (for sensors/thermostats)
            if "temperature" in data and data["temperature"] is not None:
                temp_celsius = data["temperature"]
                temp_units = data.get("temperature_units", "fahrenheit")

                if temp_units == "fahrenheit":
                    temp = (temp_celsius * 9/5) + 32
                    state_parts.append(f"temperature={temp:.1f}°F")
                else:
                    state_parts.append(f"temperature={temp_celsius:.1f}°C")

            # Humidity
            if "humidity" in data and data["humidity"] is not None:
                state_parts.append(f"humidity={data['humidity']}%")

            # Battery
            if "battery" in data and data["battery"] is not None:
                state_parts.append(f"battery={data['battery']}%")

            # Power metrics (for smart plugs/outlets)
            if "power" in data and data["power"] is not None:
                state_parts.append(f"power={data['power']}W")

            if "voltage" in data and data["voltage"] is not None:
                state_parts.append(f"voltage={data['voltage']}V")

            if "current" in data and data["current"] is not None:
                state_parts.append(f"current={data['current']}A")

            if "energy" in data and data["energy"] is not None:
                state_parts.append(f"energy={data['energy']}kWh")

            # Linkquality (signal strength)
            if "linkquality" in data and data["linkquality"] is not None:
                state_parts.append(f"signal={data['linkquality']}")

            if state_parts:
                lines.append(f"  {', '.join(state_parts)}")
            else:
                lines.append("  No state data available")

        return "\n".join(lines)
