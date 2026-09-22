"""Tests for Vallox RS485 entities."""
from __future__ import annotations

import pytest

from custom_components.vallox_rs485.vallox_protocol import ValloxState


@pytest.fixture
def mock_state() -> ValloxState:
    """Create a mock Vallox state."""
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
    return state


class TestSensorDescriptions:
    """Tests for sensor entity descriptions."""

    def test_sensor_descriptions_exist(self) -> None:
        """Test that sensor descriptions are defined."""
        from custom_components.vallox_rs485.sensor import SENSOR_DESCRIPTIONS

        assert len(SENSOR_DESCRIPTIONS) > 0

    def test_sensor_value_functions(self, mock_state: ValloxState) -> None:
        """Test sensor value functions return expected values."""
        from custom_components.vallox_rs485.sensor import SENSOR_DESCRIPTIONS

        for desc in SENSOR_DESCRIPTIONS:
            value = desc.value_fn(mock_state)
            if desc.key == "temp_outside":
                assert value == 10
            elif desc.key == "fan_speed":
                assert value == 4

    def test_sensor_required_registers(self) -> None:
        """Test sensors have required registers defined."""
        from custom_components.vallox_rs485.sensor import SENSOR_DESCRIPTIONS

        for desc in SENSOR_DESCRIPTIONS:
            assert desc.required_registers is not None, f"Missing required_registers for {desc.key}"


class TestBinarySensorDescriptions:
    """Tests for binary sensor entity descriptions."""

    def test_binary_sensor_descriptions_exist(self) -> None:
        """Test that binary sensor descriptions are defined."""
        from custom_components.vallox_rs485.binary_sensor import (
            BINARY_SENSOR_DESCRIPTIONS,
        )

        assert len(BINARY_SENSOR_DESCRIPTIONS) > 0

    def test_binary_sensor_value_functions(self, mock_state: ValloxState) -> None:
        """Test binary sensor value functions."""
        from custom_components.vallox_rs485.binary_sensor import (
            BINARY_SENSOR_DESCRIPTIONS,
        )

        mock_state.supply_fan_on = True
        mock_state.exhaust_fan_on = False
        mock_state.fault_signal = False

        for desc in BINARY_SENSOR_DESCRIPTIONS:
            value = desc.value_fn(mock_state)
            if desc.key == "supply_fan":
                assert value is True
            elif desc.key == "exhaust_fan":
                assert value is False


class TestSwitchDescriptions:
    """Tests for switch entity descriptions."""

    def test_switch_descriptions_exist(self) -> None:
        """Test that switch descriptions are defined."""
        from custom_components.vallox_rs485.switch import SWITCH_DESCRIPTIONS

        assert len(SWITCH_DESCRIPTIONS) > 0

    def test_switch_value_functions(self, mock_state: ValloxState) -> None:
        """Test switch value functions return expected values."""
        from custom_components.vallox_rs485.switch import SWITCH_DESCRIPTIONS

        for desc in SWITCH_DESCRIPTIONS:
            value = desc.value_fn(mock_state)
            if desc.key == "power_state":
                assert value is True
            elif desc.key == "heating_state":
                assert value is True

    def test_switch_has_turn_functions(self) -> None:
        """Test switches have turn on/off functions."""
        from custom_components.vallox_rs485.switch import SWITCH_DESCRIPTIONS

        for desc in SWITCH_DESCRIPTIONS:
            assert desc.turn_on_fn, f"Missing turn_on_fn for {desc.key}"
            assert desc.turn_off_fn, f"Missing turn_off_fn for {desc.key}"


class TestNumberDescriptions:
    """Tests for number entity descriptions."""

    def test_number_descriptions_exist(self) -> None:
        """Test that number descriptions are defined."""
        from custom_components.vallox_rs485.number import NUMBER_DESCRIPTIONS

        assert len(NUMBER_DESCRIPTIONS) > 0

    def test_number_all_have_set_fn(self) -> None:
        """Test that all number entities have set functions."""
        from custom_components.vallox_rs485.number import NUMBER_DESCRIPTIONS

        for desc in NUMBER_DESCRIPTIONS:
            assert desc.set_fn, f"Missing set_fn for {desc.key}"

    def test_number_value_functions(self, mock_state: ValloxState) -> None:
        """Test number value functions."""
        from custom_components.vallox_rs485.number import NUMBER_DESCRIPTIONS

        mock_state.heating_setpoint = 20
        mock_state.fan_speed_min = 2
        mock_state.fan_speed_max = 7

        for desc in NUMBER_DESCRIPTIONS:
            value = desc.value_fn(mock_state)
            if desc.key == "heating_setpoint":
                assert value == 20
            elif desc.key == "fan_speed_min":
                assert value == 2
            elif desc.key == "fan_speed_max":
                assert value == 7

    def test_number_ranges(self) -> None:
        """Test number entities have valid min/max values."""
        from custom_components.vallox_rs485.number import NUMBER_DESCRIPTIONS

        for desc in NUMBER_DESCRIPTIONS:
            assert desc.native_min_value < desc.native_max_value, (
                f"Invalid range for {desc.key}"
            )


class TestHeatRecoveryEfficiency:
    """Tests for heat recovery efficiency calculation."""

    def test_calculate_efficiency_normal(self) -> None:
        """Test efficiency calculation with normal values."""
        from custom_components.vallox_rs485.sensor import _calculate_efficiency

        state = ValloxState()
        state.temp_outside = 0
        state.temp_inside = 20
        state.temp_incoming = 18
        result = _calculate_efficiency(state)
        assert result == 90

    def test_calculate_efficiency_missing_values(self) -> None:
        """Test efficiency calculation with missing values."""
        from custom_components.vallox_rs485.sensor import _calculate_efficiency

        state = ValloxState()
        state.temp_outside = 0
        result = _calculate_efficiency(state)
        assert result is None

    def test_calculate_efficiency_zero_diff(self) -> None:
        """Test efficiency calculation when inside equals outside."""
        from custom_components.vallox_rs485.sensor import _calculate_efficiency

        state = ValloxState()
        state.temp_outside = 20
        state.temp_inside = 20
        state.temp_incoming = 20
        result = _calculate_efficiency(state)
        assert result == 0

    def test_calculate_efficiency_clamped(self) -> None:
        """Test efficiency calculation is clamped to 0-100."""
        from custom_components.vallox_rs485.sensor import _calculate_efficiency

        state = ValloxState()
        state.temp_outside = 0
        state.temp_inside = 20
        state.temp_incoming = 25
        result = _calculate_efficiency(state)
        assert result == 100

    def test_calculate_efficiency_low_clamped(self) -> None:
        """Test efficiency calculation is clamped to 0 for negative values."""
        from custom_components.vallox_rs485.sensor import _calculate_efficiency

        state = ValloxState()
        state.temp_outside = 10
        state.temp_inside = 20
        state.temp_incoming = 5  # Incoming colder than outside → negative efficiency
        result = _calculate_efficiency(state)
        assert result == 0


class TestDeviceInfo:
    """Tests for device info helper."""

    def test_get_device_info(self) -> None:
        """Every entity lands on the one device, keyed by the entry."""
        from unittest.mock import MagicMock

        from custom_components.vallox_rs485.const import DOMAIN
        from custom_components.vallox_rs485.entity import ValloxEntity

        entity = ValloxEntity(MagicMock(), "test_entry_id", "Vallox Test", "probe")

        result = entity.device_info
        assert result["name"] == "Vallox Test"
        assert result["manufacturer"] == "Vallox"
        assert result["model"] == "RS485"
        assert (DOMAIN, "test_entry_id") in result["identifiers"]
        assert entity.unique_id == "test_entry_id_probe"
