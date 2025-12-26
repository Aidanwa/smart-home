# src/smart_home/agents/zigbee.py
from __future__ import annotations
from typing import Optional
import logging

from smart_home.core.agent import Agent
from smart_home.tools.zigbee.set_devices import SetDevicesTool
from smart_home.tools.zigbee.get_devices import GetDevicesTool
from smart_home.utils.home_utils import get_all_devices_summary, get_bedroom_temperature

logger = logging.getLogger(__name__)

ZIGBEE_SYSTEM_PROMPT_TEMPLATE = """
You are a Zigbee smart home assistant. You help users control their smart home devices.

You have access to the following devices:

{devices_list}

The current bedroom temperature is {bedroom_temp}.

When controlling devices:
- Use get_zigbee_devices to check current state of devices (power, brightness, temperature, etc.)
- Use set_zigbee_devices to control one or multiple devices
- You can set state (ON/OFF/TOGGLE), brightness (0-254), and/or color_temp (153-500 mireds)
- For color temperature, lower values (153) are cooler/bluer, higher values (500) are warmer/yellower
- When controlling multiple devices with the same settings, pass ALL device names in a single tool call

Be very concise in your responses. They are read aloud, so avoid unnecessary words or phrases.
"""

class ZigbeeAgent(Agent):

    def __init__(self, model: Optional[str] = None, *, include_time: bool = True, session=None):
        # Fetch device list and build system prompt
        try:
            devices_list = get_all_devices_summary()
        except Exception as e:
            logger.warning(f"Failed to fetch devices for system prompt: {e}")
            devices_list = "Unable to fetch device list. Ensure the Zigbee API server is running."
        temp = get_bedroom_temperature()
        system_prompt = ZIGBEE_SYSTEM_PROMPT_TEMPLATE.format(devices_list=devices_list, bedroom_temp=temp)

        super().__init__(
            model=model,
            system_prompt=system_prompt,
            tools=[GetDevicesTool(), SetDevicesTool()],
            include_time=include_time,
            agent_type="zigbee",
            session=session,
        )
