"""Tests for Vallox RS485 diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from vallox_rs485_protocol import ValloxState

from custom_components.vallox_rs485.const import REG_FAN_SPEED, REG_HUMIDITY
from custom_components.vallox_rs485.coordinator import ValloxCoordinator
from custom_components.vallox_rs485.diagnostics import (
    async_get_config_entry_diagnostics,
)


@pytest.fixture
def mock_vallox_state():
    """Create a mock ValloxState with sample data."""
    state = ValloxState()
    state.temp_outside = 10
    state.temp_exhaust = 18
    state.temp_inside = 22
    state.temp_incoming = 20
    state.humidity = 45
    state.humidity_sensor1 = 44
    state.humidity_sensor2 = 46
    state.basic_humidity_level = 40
    state.co2_ppm = 800
    state.co2_high = 0x03
    state.co2_low = 0x20
    state.co2_setpoint = 1000
    state.fan_speed = 4
    state.fan_speed_min = 2
    state.fan_speed_max = 7
    state.power_state = True
    state.heating_state = True
    state.co2_adjust = False
    state.rh_adjust = True
    state.filter_guard = False
    state.heating_indicator = True
    state.fault_indicator = False
    state.service_reminder_active = False
    state.supply_fan_on = True
    state.exhaust_fan_on = True
    state.pre_heating_on = False
    state.fireplace_booster_on = False
    state.heating_setpoint = 20
    state.preheating_setpoint = 5
    state.bypass_setpoint = 15
    state.input_fan_stop_threshold = -3
    state.cell_defrost_setpoint = 4
    state.service_reminder_months = 6
    state.last_fault = "no_fault"
    state.damper_motor_position = True
    state.fault_signal = False
    state.fireplace_countdown_minutes = 0
    state._raw_values = {REG_FAN_SPEED: 0x0F, REG_HUMIDITY: 153}
    return state


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_vallox_state):
    """Create a mock coordinator."""
    coordinator = MagicMock(spec=ValloxCoordinator)
    coordinator.hass = hass
    coordinator.data = mock_vallox_state
    coordinator._writer = MagicMock()
    coordinator._seen_registers = {REG_FAN_SPEED, REG_HUMIDITY}
    coordinator.last_update_success = True
    return coordinator


class TestDiagnostics:
    """Tests for diagnostics."""

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics(
        self, hass: HomeAssistant, mock_coordinator, mock_vallox_state
    ) -> None:
        """Test diagnostics returns expected data."""
        config_entry = MockConfigEntry(
            domain="vallox_rs485",
            data={
                "serial_port": "/dev/ttyUSB0",
                "scan_interval": 30,
                "device_address": 0x22,
            },
            title="Vallox Test",
            entry_id="test_entry",
            version=1,
        )
        config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, config_entry)

        assert "config_entry" in result
        assert "coordinator" in result
        assert "state" in result
        assert "raw_register_values" in result

        # Check config entry redaction
        assert result["config_entry"]["entry_id"] == "test_entry"
        assert result["config_entry"]["domain"] == "vallox_rs485"
        # Serial port is redacted (value replaced with **REDACTED**)
        assert result["config_entry"]["data"]["serial_port"] == "**REDACTED**"

        # Check coordinator info
        assert result["coordinator"]["last_update_success"] is True
        assert result["coordinator"]["serial_connected"] is True
        assert result["coordinator"]["seen_register_count"] == 2

        # Check state data
        assert result["state"]["temperatures"]["outside"] == 10
        assert result["state"]["temperatures"]["inside"] == 22
        assert result["state"]["humidity"]["main"] == 45
        assert result["state"]["fan"]["speed"] == 4
        assert result["state"]["control_states"]["power_state"] is True

    @pytest.mark.asyncio
    async def test_async_get_config_entry_diagnostics_no_data(
        self, hass: HomeAssistant
    ) -> None:
        """Test diagnostics when coordinator has no data."""
        mock_coordinator = MagicMock(spec=ValloxCoordinator)
        mock_coordinator.data = None
        mock_coordinator._writer = None
        mock_coordinator._seen_registers = set()
        mock_coordinator.last_update_success = False

        config_entry = MockConfigEntry(
            domain="vallox_rs485",
            data={
                "serial_port": "/dev/ttyUSB0",
                "scan_interval": 30,
                "device_address": 0x22,
            },
            title="Vallox Test",
            entry_id="test_entry",
            version=1,
        )
        config_entry.runtime_data = mock_coordinator

        result = await async_get_config_entry_diagnostics(hass, config_entry)

        assert result["coordinator"]["serial_connected"] is False
        assert result["coordinator"]["seen_register_count"] == 0
        assert result["state"]["temperatures"]["outside"] is None
