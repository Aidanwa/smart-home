import os
import requests
from smart_home.core.agent import Tool
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

class SetDevicesTool(Tool):
    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url or os.getenv("ZIGBEE_API_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("ZIGBEE_API_KEY")

        name = "set_zigbee_devices"
        description = (
            "Control Zigbee smart home devices by setting their state (ON/OFF/TOGGLE), "
            "brightness level (0-254), and/or color temperature (153-500 mireds). "
            "IMPORTANT: This tool accepts MULTIPLE devices in a SINGLE call via the device_names array parameter. "
            "When controlling multiple devices with the same settings, pass ALL device names in one array - "
            "do NOT call this tool multiple times. For example, to turn on both 'Bedroom1' and 'Bedroom2', "
            "use device_names=['Bedroom1', 'Bedroom2'] in ONE tool call, not two separate calls. "
            "All specified settings will be applied to each device in the list."
        )
        params = {
            "type": "object",
            "properties": {
                "device_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of device names/IDs to control with the same settings. Pass ALL devices you want to control in this single array (e.g., ['Bedroom1', 'Bedroom2', 'Kitchen']). For a single device, still use an array format: ['DeviceName']."
                },
                "state": {
                    "type": "string",
                    "enum": ["ON", "OFF", "TOGGLE"],
                    "description": "Power state: ON (turn on), OFF (turn off), or TOGGLE (switch between on/off). Optional."
                },
                "brightness": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 254,
                    "description": "Brightness level from 0 (minimum) to 254 (maximum). Optional."
                },
                "color_temp": {
                    "type": "integer",
                    "minimum": 153,
                    "maximum": 500,
                    "description": "Color temperature in mireds. Lower values (153) are cooler/bluer, higher values (500) are warmer/yellower. Optional."
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

    def _set_single_device(self, device_name, payload):
        """Set a single device's state. Returns (device_name, success, message)."""
        try:
            resp = self._request(
                "POST",
                f"/api/devices/{device_name}/set",
                json=payload,
            )

            if resp.status_code == 200:
                return (device_name, True, "updated successfully")
            else:
                return (device_name, False, f"API returned {resp.status_code} - {resp.text}")
        except Exception as e:
            return (device_name, False, f"request failed - {e}")

    def call(self, device_names, state=None, brightness=None, color_temp=None):
        # Build payload
        payload = {}
        if state is not None:
            payload["state"] = state
        if brightness is not None:
            payload["brightness"] = brightness
        if color_temp is not None:
            payload["color_temp"] = color_temp

        if not payload:
            return "Error: No fields to update. Provide at least one of state, brightness, color_temp."

        # Ensure device_names is a list
        if isinstance(device_names, str):
            device_names = [device_names]

        results = []
        errors = []

        # Apply settings to all devices in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all device update tasks
            future_to_device = {
                executor.submit(self._set_single_device, device_name, payload): device_name
                for device_name in device_names
            }

            # Collect results as they complete
            for future in as_completed(future_to_device):
                device_name, success, message = future.result()
                if success:
                    results.append(f"{device_name}: {message}")
                else:
                    errors.append(f"{device_name}: {message}")

        # Format response
        summary = []
        if results:
            settings_applied = []
            if state:
                settings_applied.append(f"state={state}")
            if brightness is not None:
                settings_applied.append(f"brightness={brightness}")
            if color_temp is not None:
                settings_applied.append(f"color_temp={color_temp}")

            summary.append(f"Applied settings ({', '.join(settings_applied)}) to {len(results)} device(s):")
            summary.extend(results)

        if errors:
            if results:
                summary.append("\nErrors:")
            summary.extend(errors)

        return "\n".join(summary)
