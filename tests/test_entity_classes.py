"""Tests for Vallox RS485 entity classes."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.vallox_rs485.vallox_protocol import ValloxState


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = ValloxState()
    coordinator.data.temp_outside = 10
    coordinator.data.temp_exhaust = 18
    coordinator.data.temp_inside = 22
    coordinator.data.temp_incoming = 20
    coordinator.data.humidity = 45
    coordinator.data.fan_speed = 4
    coordinator.data.power_state = True
    coordinator.data.heating_state = True
    coordinator.data.co2_adjust = False
    coordinator.data.rh_adjust = True
    coordinator.data.supply_fan_on = True
    coordinator.data.exhaust_fan_on = True
    coordinator.data.heating_setpoint = 20
    coordinator.data.fan_speed_min = 2
    coordinator.data.fan_speed_max = 7
    coordinator.last_update_success = True
    coordinator.has_seen_any_register = MagicMock(return_value=True)
    coordinator.async_set_power_state = AsyncMock()
    coordinator.async_set_fan_speed = AsyncMock()
    coordinator.async_set_heating_state = AsyncMock()
    coordinator.async_set_co2_adjust = AsyncMock()
    coordinator.async_set_rh_adjust = AsyncMock()
    coordinator.async_set_heating_setpoint = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.fixture
def mock_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.title = "Vallox Test"
    entry.runtime_data = None
    return entry


class TestValloxSensorEntity:
    """Tests for ValloxSensor entity class."""

    def test_sensor_native_value(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test sensor native_value property."""
        from custom_components.vallox_rs485.sensor import (
            ValloxSensor,
            SENSOR_DESCRIPTIONS,
        )

        for desc in SENSOR_DESCRIPTIONS:
            if desc.key == "temp_outside":
                sensor = ValloxSensor(mock_coordinator, desc, mock_entry)
                assert sensor.native_value == 10
                break

    def test_sensor_unique_id(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test sensor unique_id is generated correctly."""
        from custom_components.vallox_rs485.sensor import (
            ValloxSensor,
            SENSOR_DESCRIPTIONS,
        )

        desc = SENSOR_DESCRIPTIONS[0]
        sensor = ValloxSensor(mock_coordinator, desc, mock_entry)
        assert sensor._attr_unique_id == f"test_entry_id_{desc.key}"

    def test_sensor_device_info(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test sensor device_info is set correctly."""
        from custom_components.vallox_rs485.sensor import (
            ValloxSensor,
            SENSOR_DESCRIPTIONS,
        )
        from custom_components.vallox_rs485.const import DOMAIN

        desc = SENSOR_DESCRIPTIONS[0]
        sensor = ValloxSensor(mock_coordinator, desc, mock_entry)
        assert sensor._attr_device_info["manufacturer"] == "Vallox"
        assert (DOMAIN, "test_entry_id") in sensor._attr_device_info["identifiers"]

    def test_sensor_available_with_value(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test sensor availability when value exists."""
        from custom_components.vallox_rs485.sensor import (
            ValloxSensor,
            SENSOR_DESCRIPTIONS,
        )

        for desc in SENSOR_DESCRIPTIONS:
            if desc.key == "temp_outside":
                sensor = ValloxSensor(mock_coordinator, desc, mock_entry)
                # Mock super().available to return True
                with patch.object(type(sensor).__bases__[0], 'available', new_callable=lambda: property(lambda self: True)):
                    assert sensor.available is True
                break

    def test_sensor_available_without_value(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test sensor availability when value is None."""
        from custom_components.vallox_rs485.sensor import (
            ValloxSensor,
            SENSOR_DESCRIPTIONS,
        )

        mock_coordinator.data.temp_outside = None

        for desc in SENSOR_DESCRIPTIONS:
            if desc.key == "temp_outside":
                sensor = ValloxSensor(mock_coordinator, desc, mock_entry)
                with patch.object(type(sensor).__bases__[0], 'available', new_callable=lambda: property(lambda self: True)):
                    assert sensor.available is False
                break


class TestValloxBinarySensorEntity:
    """Tests for ValloxBinarySensor entity class."""

    def test_binary_sensor_is_on(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test binary sensor is_on property."""
        from custom_components.vallox_rs485.binary_sensor import (
            ValloxBinarySensor,
            BINARY_SENSOR_DESCRIPTIONS,
        )

        for desc in BINARY_SENSOR_DESCRIPTIONS:
            if desc.key == "supply_fan":
                sensor = ValloxBinarySensor(mock_coordinator, desc, mock_entry)
                assert sensor.is_on is True
                break

    def test_binary_sensor_unique_id(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test binary sensor unique_id."""
        from custom_components.vallox_rs485.binary_sensor import (
            ValloxBinarySensor,
            BINARY_SENSOR_DESCRIPTIONS,
        )

        desc = BINARY_SENSOR_DESCRIPTIONS[0]
        sensor = ValloxBinarySensor(mock_coordinator, desc, mock_entry)
        assert sensor._attr_unique_id == f"test_entry_id_{desc.key}"

    def test_binary_sensor_available(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test binary sensor availability."""
        from custom_components.vallox_rs485.binary_sensor import (
            ValloxBinarySensor,
            BINARY_SENSOR_DESCRIPTIONS,
        )

        for desc in BINARY_SENSOR_DESCRIPTIONS:
            if desc.key == "supply_fan":
                sensor = ValloxBinarySensor(mock_coordinator, desc, mock_entry)
                with patch.object(type(sensor).__bases__[0], 'available', new_callable=lambda: property(lambda self: True)):
                    assert sensor.available is True
                break


class TestValloxSwitchEntity:
    """Tests for ValloxSwitch entity class."""

    def test_switch_is_on(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test switch is_on property."""
        from custom_components.vallox_rs485.switch import (
            ValloxSwitch,
            SWITCH_DESCRIPTIONS,
        )

        for desc in SWITCH_DESCRIPTIONS:
            if desc.key == "power_state":
                switch = ValloxSwitch(mock_coordinator, desc, mock_entry)
                assert switch.is_on is True
                break

    def test_switch_unique_id(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test switch unique_id."""
        from custom_components.vallox_rs485.switch import (
            ValloxSwitch,
            SWITCH_DESCRIPTIONS,
        )

        desc = SWITCH_DESCRIPTIONS[0]
        switch = ValloxSwitch(mock_coordinator, desc, mock_entry)
        assert switch._attr_unique_id == f"test_entry_id_{desc.key}"

    @pytest.mark.asyncio
    async def test_switch_turn_on(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test switch async_turn_on."""
        from custom_components.vallox_rs485.switch import (
            ValloxSwitch,
            SWITCH_DESCRIPTIONS,
        )

        for desc in SWITCH_DESCRIPTIONS:
            if desc.key == "power_state":
                switch = ValloxSwitch(mock_coordinator, desc, mock_entry)
                await switch.async_turn_on()
                mock_coordinator.async_set_power_state.assert_called_once_with(True)
                mock_coordinator.async_request_refresh.assert_called()
                break

    @pytest.mark.asyncio
    async def test_switch_turn_off(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test switch async_turn_off."""
        from custom_components.vallox_rs485.switch import (
            ValloxSwitch,
            SWITCH_DESCRIPTIONS,
        )

        for desc in SWITCH_DESCRIPTIONS:
            if desc.key == "power_state":
                switch = ValloxSwitch(mock_coordinator, desc, mock_entry)
                await switch.async_turn_off()
                mock_coordinator.async_set_power_state.assert_called_once_with(False)
                mock_coordinator.async_request_refresh.assert_called()
                break

    def test_switch_available(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test switch availability."""
        from custom_components.vallox_rs485.switch import (
            ValloxSwitch,
            SWITCH_DESCRIPTIONS,
        )

        for desc in SWITCH_DESCRIPTIONS:
            if desc.key == "power_state":
                switch = ValloxSwitch(mock_coordinator, desc, mock_entry)
                with patch.object(type(switch).__bases__[0], 'available', new_callable=lambda: property(lambda self: True)):
                    assert switch.available is True
                break


class TestValloxFanEntity:
    """Tests for ValloxFan entity class."""

    def test_fan_is_on(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan is_on property."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        assert fan.is_on is True

    def test_fan_is_on_when_power_none(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan is_on property when power_state is None."""
        from custom_components.vallox_rs485.fan import ValloxFan

        mock_coordinator.data.power_state = None
        fan = ValloxFan(mock_coordinator, mock_entry)
        assert fan.is_on is None

    def test_fan_percentage(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan percentage property."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        # fan_speed = 4, so percentage = 4 * 100 / 8 = 50
        assert fan.percentage == 50

    def test_fan_percentage_when_none(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan percentage property when fan_speed is None."""
        from custom_components.vallox_rs485.fan import ValloxFan

        mock_coordinator.data.fan_speed = None
        fan = ValloxFan(mock_coordinator, mock_entry)
        assert fan.percentage is None

    def test_fan_preset_mode(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan preset_mode property."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        assert fan.preset_mode == "4"

    def test_fan_preset_mode_when_none(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan preset_mode property when fan_speed is None."""
        from custom_components.vallox_rs485.fan import ValloxFan

        mock_coordinator.data.fan_speed = None
        fan = ValloxFan(mock_coordinator, mock_entry)
        assert fan.preset_mode is None

    def test_fan_unique_id(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan unique_id."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        assert fan._attr_unique_id == "test_entry_id_fan"

    @pytest.mark.asyncio
    async def test_fan_turn_on(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan async_turn_on."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        await fan.async_turn_on()
        mock_coordinator.async_set_power_state.assert_called_once_with(True)
        mock_coordinator.async_request_refresh.assert_called()

    @pytest.mark.asyncio
    async def test_fan_turn_on_with_preset_mode(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan async_turn_on with preset_mode."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        await fan.async_turn_on(preset_mode="5")
        mock_coordinator.async_set_power_state.assert_called_once_with(True)
        mock_coordinator.async_set_fan_speed.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_fan_turn_on_with_percentage(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan async_turn_on with percentage."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        await fan.async_turn_on(percentage=75)  # Should be speed 6 (75 * 8 / 100 = 6)
        mock_coordinator.async_set_power_state.assert_called_once_with(True)
        mock_coordinator.async_set_fan_speed.assert_called_once_with(6)

    @pytest.mark.asyncio
    async def test_fan_turn_off(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan async_turn_off."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        await fan.async_turn_off()
        mock_coordinator.async_set_power_state.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_fan_set_percentage(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan async_set_percentage."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        await fan.async_set_percentage(50)  # Should be speed 4
        mock_coordinator.async_set_fan_speed.assert_called_once_with(4)

    @pytest.mark.asyncio
    async def test_fan_set_percentage_zero(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan async_set_percentage with zero turns off."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        await fan.async_set_percentage(0)
        mock_coordinator.async_set_power_state.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_fan_set_preset_mode(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test fan async_set_preset_mode."""
        from custom_components.vallox_rs485.fan import ValloxFan

        fan = ValloxFan(mock_coordinator, mock_entry)
        await fan.async_set_preset_mode("7")
        mock_coordinator.async_set_fan_speed.assert_called_once_with(7)


class TestValloxNumberEntity:
    """Tests for ValloxNumber entity class."""

    def test_number_native_value(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test number native_value property."""
        from custom_components.vallox_rs485.number import (
            ValloxNumber,
            NUMBER_DESCRIPTIONS,
        )

        for desc in NUMBER_DESCRIPTIONS:
            if desc.key == "heating_setpoint":
                number = ValloxNumber(mock_coordinator, desc, mock_entry)
                assert number.native_value == 20.0
                break

    def test_number_native_value_none(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test number native_value when value is None."""
        from custom_components.vallox_rs485.number import (
            ValloxNumber,
            NUMBER_DESCRIPTIONS,
        )

        mock_coordinator.data.heating_setpoint = None

        for desc in NUMBER_DESCRIPTIONS:
            if desc.key == "heating_setpoint":
                number = ValloxNumber(mock_coordinator, desc, mock_entry)
                assert number.native_value is None
                break

    def test_number_unique_id(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test number unique_id."""
        from custom_components.vallox_rs485.number import (
            ValloxNumber,
            NUMBER_DESCRIPTIONS,
        )

        desc = NUMBER_DESCRIPTIONS[0]
        number = ValloxNumber(mock_coordinator, desc, mock_entry)
        assert number._attr_unique_id == f"test_entry_id_{desc.key}"

    @pytest.mark.asyncio
    async def test_number_set_native_value(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test number async_set_native_value."""
        from custom_components.vallox_rs485.number import (
            ValloxNumber,
            NUMBER_DESCRIPTIONS,
        )

        for desc in NUMBER_DESCRIPTIONS:
            if desc.key == "heating_setpoint":
                number = ValloxNumber(mock_coordinator, desc, mock_entry)
                await number.async_set_native_value(25.0)
                mock_coordinator.async_set_heating_setpoint.assert_called_once_with(25)
                mock_coordinator.async_request_refresh.assert_called()
                break

    def test_number_available(self, mock_coordinator: MagicMock, mock_entry: MagicMock) -> None:
        """Test number availability."""
        from custom_components.vallox_rs485.number import (
            ValloxNumber,
            NUMBER_DESCRIPTIONS,
        )

        for desc in NUMBER_DESCRIPTIONS:
            if desc.key == "heating_setpoint":
                number = ValloxNumber(mock_coordinator, desc, mock_entry)
                with patch.object(type(number).__bases__[0], 'available', new_callable=lambda: property(lambda self: True)):
                    assert number.available is True
                break
