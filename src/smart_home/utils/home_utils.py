import os
import requests
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

def get_bedroom_temperature(
    device_name: str = None,
    base_url: str = None,
    api_key: str = None,
) -> str:
    """Get the current temperature from a thermostat device.

    Args:
        device_name: Device identifier (defaults to PRIMARY_THERMOSTAT_ID env var)
        base_url: API base URL (defaults to ZIGBEE_API_BASE_URL env var or localhost:8000)
        api_key: API authentication key (defaults to ZIGBEE_API_KEY env var)

    Returns:
        Temperature string with unit symbol (e.g., "72°F")

    Raises:
        ValueError: If device_name is not configured
        requests.RequestException: If API request fails
    """
    device_name = device_name or os.getenv("PRIMARY_THERMOSTAT_ID")
    if not device_name:
        raise ValueError(
            "Device name not provided. Set PRIMARY_THERMOSTAT_ID environment variable "
            "or pass device_name parameter."
        )

    base_url = base_url or os.getenv("ZIGBEE_API_BASE_URL", "http://localhost:8000")
    api_key = api_key or os.getenv("ZIGBEE_API_KEY")

    url = f"{base_url.rstrip('/')}/api/devices/{device_name}"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.Timeout:
        raise requests.RequestException(
            f"Request to {url} timed out after 5 seconds. "
            "Check if the Zigbee API server is running."
        )
    except requests.ConnectionError:
        raise requests.RequestException(
            f"Failed to connect to {url}. "
            "Verify ZIGBEE_API_BASE_URL is correct and the server is running."
        )
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise requests.RequestException(
                "Authentication failed. Check ZIGBEE_API_KEY environment variable."
            )
        elif response.status_code == 404:
            raise requests.RequestException(
                f"Device '{device_name}' not found. Verify PRIMARY_THERMOSTAT_ID is correct."
            )
        else:
            raise requests.RequestException(
                f"API request failed with status {response.status_code}: {e}"
            )

    try:
        state = response.json()
    except requests.JSONDecodeError as e:
        raise requests.RequestException(
            f"Invalid JSON response from API: {e}"
        )

    if "temperature" not in state:
        raise ValueError(
            f"Response missing 'temperature' field. Got keys: {list(state.keys())}"
        )

    temperature_celsius = state["temperature"]
    unit = state.get("temperature_units", "fahrenheit")

    # API always returns temperature in Celsius, convert if needed
    if unit == "fahrenheit":
        temperature = (temperature_celsius * 9/5) + 32
        unit_symbol = "°F"
    else:
        temperature = temperature_celsius
        unit_symbol = "°C"

    return f"{temperature:.1f}{unit_symbol}"


def get_all_devices_summary(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Fetch all connected Zigbee devices and format them as a plain text summary.

    Args:
        base_url: API base URL (defaults to ZIGBEE_API_BASE_URL env var or localhost:8000)
        api_key: API authentication key (defaults to ZIGBEE_API_KEY env var)

    Returns:
        Formatted string containing device names for system prompts

    Raises:
        requests.RequestException: If API request fails
    """
    base_url = base_url or os.getenv("ZIGBEE_API_BASE_URL", "http://localhost:8000")
    api_key = api_key or os.getenv("ZIGBEE_API_KEY")

    url = f"{base_url.rstrip('/')}/api/devices"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.Timeout:
        raise requests.RequestException(
            f"Request to {url} timed out after 5 seconds. "
            "Check if the Zigbee API server is running."
        )
    except requests.ConnectionError:
        raise requests.RequestException(
            f"Failed to connect to {url}. "
            "Verify ZIGBEE_API_BASE_URL is correct and the server is running."
        )
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise requests.RequestException(
                "Authentication failed. Check ZIGBEE_API_KEY environment variable."
            )
        else:
            raise requests.RequestException(
                f"API request failed with status {response.status_code}: {e}"
            )

    try:
        devices = response.json()
    except requests.JSONDecodeError as e:
        raise requests.RequestException(
            f"Invalid JSON response from API: {e}"
        )

    if not devices:
        return "No Zigbee devices are currently connected."

    # Format devices into a readable summary
    lines = ["Available Zigbee Devices:"]

    for device in devices.get("devices", []):
        device_name = device.get("friendly_name", "Unknown")
        device_definition = device.get("definition", {})
        device_description = device_definition.get("description", "No description") if device_definition else "No description"

        info = f"- {device_name} ({device_description})"
        lines.append(info)

    return "\n".join(lines)