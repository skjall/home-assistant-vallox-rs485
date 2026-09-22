"""Vallox RS485 integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

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

    # The unit sends when it sees fit. Setting up entities before a single
    # register has arrived leaves the user with a device full of unknowns and
    # no reason given; Home Assistant retries with backoff instead.
    if not await coordinator.async_wait_for_initial_data(timeout=15.0):
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(translation_key="no_bus_data")

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ValloxConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()

    return unload_ok
