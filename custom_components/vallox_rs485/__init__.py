"""Vallox RS485 integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import ValloxCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.FAN,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
]

PARALLEL_UPDATES = 1

type ValloxConfigEntry = ConfigEntry[ValloxCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ValloxConfigEntry) -> bool:
    """Set up Vallox RS485 from a config entry."""
    serial_port = entry.data["serial_port"]
    scan_interval = entry.data.get("scan_interval", 30)
    device_address = entry.data.get("device_address", 0x2E)

    coordinator = ValloxCoordinator(
        hass,
        serial_port=serial_port,
        scan_interval=scan_interval,
        device_address=device_address,
        entry_id=entry.entry_id,
    )

    await coordinator.async_config_entry_first_refresh()

    # Wait for initial bus data before creating entities
    await coordinator.async_wait_for_initial_data(timeout=15.0)

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ValloxConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()

    return unload_ok
