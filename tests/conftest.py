"""Fixtures for Vallox RS485 tests."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain="vallox_rs485",
        data={
            "serial_port": "/dev/ttyUSB0",
            "scan_interval": 30,
            "device_address": 0x22,
        },
        title="Vallox Test",
        entry_id="test_entry_id",
    )


@pytest.fixture
def mock_serial():
    """Create a mock serial port."""
    with patch("serial.Serial") as mock:
        mock_instance = MagicMock()
        mock_instance.is_open = True
        mock_instance.in_waiting = 0
        mock_instance.read.return_value = b""
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_vallox_state():
    """Create a mock ValloxState with sample data."""
    from vallox_rs485_protocol import ValloxState

    state = ValloxState()
    state.temp_outside = 10
    state.temp_exhaust = 18
    state.temp_inside = 22
    state.temp_incoming = 20
    state.humidity = 45
    state.fan_speed = 4
    state.power_state = True
    state.heating_state = True
    state.co2_adjust = False
    state.rh_adjust = True
    state.supply_fan_on = True
    state.exhaust_fan_on = True
    state.heating_setpoint = 20
    state.fan_speed_min = 2
    state.fan_speed_max = 7
    return state


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_vallox_state):
    """Create a mock coordinator."""
    from custom_components.vallox_rs485.coordinator import ValloxCoordinator

    with patch.object(ValloxCoordinator, "__init__", lambda *args, **kwargs: None):
        coordinator = ValloxCoordinator.__new__(ValloxCoordinator)
        coordinator.hass = hass
        coordinator.data = mock_vallox_state
        coordinator._seen_registers = {0x29, 0x2A, 0x32, 0x33, 0x34, 0x35, 0xA3, 0x08}
        coordinator.last_update_success = True
        coordinator._serial = None
        coordinator._serial_port = "/dev/ttyUSB0"
        coordinator._device_address = 0x22
        coordinator._state = mock_vallox_state
        coordinator._lock = asyncio.Lock()
        coordinator._register_timestamps = {}
        # Long enough ago to be past the rate limit. A literal 0 is not, on a
        # machine whose monotonic clock started seconds ago.
        coordinator._last_unavailable_log = time.monotonic() - 61
        coordinator.async_request_refresh = AsyncMock()
        coordinator.async_set_power_state = AsyncMock()
        coordinator.async_set_fan_speed = AsyncMock()
        coordinator.async_set_heating_state = AsyncMock()
        coordinator.async_set_co2_adjust = AsyncMock()
        coordinator.async_set_rh_adjust = AsyncMock()
        coordinator.async_set_heating_setpoint = AsyncMock()
        return coordinator
