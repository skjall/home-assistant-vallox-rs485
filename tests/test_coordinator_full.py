"""Comprehensive tests for ValloxCoordinator covering all methods and branches."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import serial
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from vallox_rs485_protocol import ValloxState, ValloxTelegram

from custom_components.vallox_rs485.const import (
    ADDR_MAINBOARD,
    BIT_CO2_ADJUST,
    BIT_HEATING_STATE,
    BIT_POWER_STATE,
    BIT_RH_ADJUST,
    REG_BASIC_HUMIDITY_LEVEL,
    REG_BYPASS_SETPOINT,
    REG_CELL_DEFROST_SETPOINT,
    REG_CO2_HIGH,
    REG_CO2_LOW,
    REG_CO2_SETPOINT_LOWER,
    REG_CO2_SETPOINT_UPPER,
    REG_DC_FAN_INPUT_ADJ,
    REG_DC_FAN_OUTPUT_ADJ,
    REG_FAN_SPEED,
    REG_FAN_SPEED_MAX,
    REG_FAN_SPEED_MIN,
    REG_FIREPLACE_COUNTDOWN,
    REG_HUMIDITY_SENSOR1,
    REG_HUMIDITY_SENSOR2,
    REG_INPUT_FAN_STOP_THRESHOLD,
    REG_LAST_FAULT,
    REG_MULTI_PURPOSE_2,
    REG_POST_HEATING_OFF_TIME,
    REG_POST_HEATING_ON_CNT,
    REG_POST_HEATING_TARGET,
    REG_PREHEATING_SETPOINT,
    REG_SELECT,
    REG_SERVICE_REMINDER,
    REG_TEMP_EXHAUST_LEGACY,
    REG_TEMP_INCOMING_LEGACY,
    REG_TEMP_INSIDE_LEGACY,
    REG_TEMP_OUTSIDE_LEGACY,
)
from custom_components.vallox_rs485.coordinator import (
    POLL_REGISTERS,
    ValloxCoordinator,
    get_serial_ports,
)


class TestGetSerialPorts:
    """Tests for get_serial_ports module function."""

    def test_get_serial_ports_returns_list(self) -> None:
        """Test that get_serial_ports returns a list."""
        mock_port = MagicMock()
        mock_port.device = "/dev/ttyUSB0"

        with patch("serial.tools.list_ports.comports", return_value=[mock_port]):
            result = get_serial_ports()
            assert isinstance(result, list)
            assert "/dev/ttyUSB0" in result

    def test_get_serial_ports_empty(self) -> None:
        """Test get_serial_ports with no ports available."""
        with patch("serial.tools.list_ports.comports", return_value=[]):
            result = get_serial_ports()
            assert result == []


class TestCoordinatorAsyncUpdateData:
    """Tests for _async_update_data method."""

    @pytest.mark.asyncio
    async def test_async_update_data_serial_exception(
        self, hass: HomeAssistant
    ) -> None:
        """Test _async_update_data handles SerialException."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._ensure_connected = AsyncMock(
                side_effect=serial.SerialException("Port error")
            )

            with pytest.raises(UpdateFailed) as exc_info:
                await coordinator._async_update_data()

            assert "Serial communication error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_update_data_timeout_error(self, hass: HomeAssistant) -> None:
        """Test _async_update_data handles TimeoutError."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._ensure_connected = AsyncMock(
                side_effect=TimeoutError("Connection timeout")
            )

            with pytest.raises(UpdateFailed) as exc_info:
                await coordinator._async_update_data()

            assert "Communication timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_update_data_success(self, hass: HomeAssistant) -> None:
        """Test successful _async_update_data."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._ensure_connected = AsyncMock()
            coordinator._poll_missing_registers = AsyncMock()

            result = await coordinator._async_update_data()

            assert isinstance(result, ValloxState)
            coordinator._ensure_connected.assert_called_once()
            coordinator._poll_missing_registers.assert_called_once()


class TestCoordinatorConnection:
    """Tests for connection management methods."""

    @pytest.mark.asyncio
    async def test_ensure_connected_opens_serial(self, hass: HomeAssistant) -> None:
        """With no reader and no writer, the port is opened."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        coordinator._reader = None
        coordinator._writer = None
        coordinator._open_serial = AsyncMock()

        await coordinator._ensure_connected()

        coordinator._open_serial.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ensure_connected_leaves_an_open_port_alone(
        self, hass: HomeAssistant
    ) -> None:
        """An open port is not reopened on every update."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        coordinator._reader = MagicMock()
        coordinator._writer = MagicMock()
        coordinator._open_serial = AsyncMock()

        await coordinator._ensure_connected()

        coordinator._open_serial.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_open_serial(self, hass: HomeAssistant) -> None:
        """Opening keeps both ends and starts the listener."""
        reader, writer = MagicMock(), MagicMock()
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        coordinator._start_bus_listener = MagicMock()

        with patch(
            "custom_components.vallox_rs485.coordinator."
            "serial_asyncio_fast.open_serial_connection",
            new=AsyncMock(return_value=(reader, writer)),
        ) as opened:
            await coordinator._open_serial()

        assert opened.await_args.kwargs["url"] == "/dev/ttyUSB0"
        assert coordinator._reader is reader
        assert coordinator._writer is writer
        coordinator._start_bus_listener.assert_called_once()


class TestCoordinatorPolling:
    """Tests for polling methods."""

    @pytest.mark.asyncio
    async def test_poll_registers(self, hass: HomeAssistant) -> None:
        """An update polls whatever has not been seen yet."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._poll_missing_registers = AsyncMock()
            coordinator._ensure_connected = AsyncMock()

            if True:
                await coordinator._async_update_data()
                coordinator._poll_missing_registers.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_missing_registers_no_seen(self, hass: HomeAssistant) -> None:
        """Test _poll_missing_registers when no registers seen."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._seen_registers = set()
            coordinator._request_register = AsyncMock()

            await coordinator._poll_missing_registers()

            # Should poll all POLL_REGISTERS
            assert coordinator._request_register.call_count == len(POLL_REGISTERS)

    @pytest.mark.asyncio
    async def test_poll_missing_registers_all_seen(self, hass: HomeAssistant) -> None:
        """Test _poll_missing_registers when all registers seen recently."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            now = time.monotonic()
            coordinator._seen_registers = set(POLL_REGISTERS)
            coordinator._register_timestamps = {r: now for r in POLL_REGISTERS}
            coordinator._request_register = AsyncMock()

            await coordinator._poll_missing_registers()

            coordinator._request_register.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_missing_registers_stale(self, hass: HomeAssistant) -> None:
        """Test _poll_missing_registers polls stale registers."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._seen_registers = set(POLL_REGISTERS)
            # Set all timestamps to old value (stale)
            coordinator._register_timestamps = {r: 0 for r in POLL_REGISTERS}
            coordinator._request_register = AsyncMock()

            await coordinator._poll_missing_registers()

            assert coordinator._request_register.call_count == len(POLL_REGISTERS)

    @pytest.mark.asyncio
    async def test_poll_missing_registers_exception(self, hass: HomeAssistant) -> None:
        """Test _poll_missing_registers handles request exceptions."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._seen_registers = set()
            coordinator._request_register = AsyncMock(
                side_effect=Exception("Request failed")
            )

            # Should not raise, just log
            await coordinator._poll_missing_registers()

    @pytest.mark.asyncio
    async def test_request_register(self, hass: HomeAssistant) -> None:
        """Test _request_register sends telegram."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._ensure_connected = AsyncMock()
            coordinator._send_telegram = AsyncMock()

            with patch("asyncio.sleep", new=AsyncMock()):
                await coordinator._request_register(REG_FAN_SPEED)

            telegram = coordinator._send_telegram.await_args.args[0]
            assert telegram.register == 0x00
            assert telegram.value == REG_FAN_SPEED


class TestCoordinatorBusListener:
    """Tests for the background reader."""

    @pytest.mark.asyncio
    async def test_listener_waits_while_the_port_is_closed(
        self, hass: HomeAssistant
    ) -> None:
        """Without a reader the loop idles instead of spinning."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        coordinator._reader = None

        with patch("asyncio.sleep", new=AsyncMock(side_effect=asyncio.CancelledError)):
            await coordinator._bus_listener()

    @pytest.mark.asyncio
    async def test_listener_parses_what_it_reads(self, hass: HomeAssistant) -> None:
        """Bytes off the bus go to the parser."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_FAN_SPEED,
            value=0x0F,
        )
        data = telegram.to_bytes()
        reader = MagicMock()
        reader.read = AsyncMock(side_effect=[data, asyncio.CancelledError])
        coordinator._reader = reader

        with patch.object(coordinator, "_parse_buffer", return_value=b"") as parsed:
            await coordinator._bus_listener()

        parsed.assert_called_once()
        assert parsed.call_args.args[0] == data


class TestCoordinatorParseBuffer:
    """Tests for _parse_buffer method."""

    def test_parse_buffer_empty(self, hass: HomeAssistant) -> None:
        """Test _parse_buffer with empty buffer."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._parse_buffer(b"")

    def test_parse_buffer_invalid_domain(self, hass: HomeAssistant) -> None:
        """Test _parse_buffer skips bytes with invalid domain."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            # Invalid domain byte
            invalid_data = b"\x00\x11\x22\x29\x0f\x55"
            coordinator._parse_buffer(invalid_data)

            assert REG_FAN_SPEED not in coordinator._seen_registers

    def test_parse_buffer_invalid_checksum(self, hass: HomeAssistant) -> None:
        """Test _parse_buffer skips invalid checksums."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            # Valid domain but bad checksum
            invalid_data = b"\x01\x11\x22\x29\x0f\xff"
            coordinator._parse_buffer(invalid_data)

            assert REG_FAN_SPEED not in coordinator._seen_registers


class TestCoordinatorProcessTelegram:
    """Tests for _process_telegram covering all register branches."""

    def test_process_temp_outside_legacy(self, hass: HomeAssistant) -> None:
        """Test processing legacy outside temperature."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_TEMP_OUTSIDE_LEGACY,
                value=160,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.temp_outside == 20

    def test_process_temp_exhaust_legacy(self, hass: HomeAssistant) -> None:
        """Test processing legacy exhaust temperature."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_TEMP_EXHAUST_LEGACY,
                value=160,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.temp_exhaust == 20

    def test_process_temp_inside_legacy(self, hass: HomeAssistant) -> None:
        """Test processing legacy inside temperature."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_TEMP_INSIDE_LEGACY,
                value=160,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.temp_inside == 20

    def test_process_temp_incoming_legacy(self, hass: HomeAssistant) -> None:
        """Test processing legacy incoming temperature."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_TEMP_INCOMING_LEGACY,
                value=160,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.temp_incoming == 20

    def test_process_fan_speed_min(self, hass: HomeAssistant) -> None:
        """Test processing fan speed min."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_FAN_SPEED_MIN,
                value=0x03,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.fan_speed_min == 2

    def test_process_fan_speed_max(self, hass: HomeAssistant) -> None:
        """Test processing fan speed max."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_FAN_SPEED_MAX,
                value=0xFF,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.fan_speed_max == 8

    def test_process_humidity_sensor1(self, hass: HomeAssistant) -> None:
        """Test processing humidity sensor 1."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_HUMIDITY_SENSOR1,
                value=153,
            )
            coordinator._process_telegram(telegram)
            # decode_humidity(153) = round((153 - 51) / 2.04) = round(50) = 50
            assert coordinator._state.humidity_sensor1 == 50

    def test_process_humidity_sensor2(self, hass: HomeAssistant) -> None:
        """Test processing humidity sensor 2."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_HUMIDITY_SENSOR2,
                value=153,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.humidity_sensor2 == 50

    def test_process_basic_humidity_level(self, hass: HomeAssistant) -> None:
        """Test processing basic humidity level."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_BASIC_HUMIDITY_LEVEL,
                value=153,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.basic_humidity_level == 50

    def test_process_co2_high(self, hass: HomeAssistant) -> None:
        """Test processing CO2 high byte."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_CO2_HIGH,
                value=0x03,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.co2_high == 0x03

    def test_process_co2_low(self, hass: HomeAssistant) -> None:
        """Test processing CO2 low byte."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_CO2_LOW,
                value=0xE8,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.co2_low == 0xE8

    def test_process_co2_setpoint_upper(self, hass: HomeAssistant) -> None:
        """Test processing CO2 setpoint upper byte."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._state._raw_values[REG_CO2_SETPOINT_LOWER] = 0xE8
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_CO2_SETPOINT_UPPER,
                value=0x03,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.co2_setpoint == 0x03E8  # 1000 ppm

    def test_process_co2_setpoint_lower(self, hass: HomeAssistant) -> None:
        """Test processing CO2 setpoint lower byte."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._state._raw_values[REG_CO2_SETPOINT_UPPER] = 0x03
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_CO2_SETPOINT_LOWER,
                value=0xE8,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.co2_setpoint == 0x03E8

    def test_process_last_fault(self, hass: HomeAssistant) -> None:
        """Test processing last fault register."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_LAST_FAULT,
                value=0x00,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.last_fault == "no_fault"

    def test_process_select_register(self, hass: HomeAssistant) -> None:
        """Test processing SELECT register with all bits."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            value = (
                (1 << BIT_POWER_STATE)
                | (1 << BIT_CO2_ADJUST)
                | (1 << BIT_RH_ADJUST)
                | (1 << BIT_HEATING_STATE)
            )
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_SELECT,
                value=value,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.power_state is True
            assert coordinator._state.co2_adjust is True
            assert coordinator._state.rh_adjust is True
            assert coordinator._state.heating_state is True

    def test_process_multi_purpose_2(self, hass: HomeAssistant) -> None:
        """Test processing MULTI_PURPOSE_2 register."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            value = 0xFF  # All bits set
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_MULTI_PURPOSE_2,
                value=value,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.supply_fan_on is True
            assert coordinator._state.exhaust_fan_on is True

    def test_process_preheating_setpoint(self, hass: HomeAssistant) -> None:
        """Test processing preheating setpoint."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_PREHEATING_SETPOINT,
                value=196,  # NTC for ~5°C
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.preheating_setpoint is not None

    def test_process_bypass_setpoint(self, hass: HomeAssistant) -> None:
        """Test processing bypass setpoint."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_BYPASS_SETPOINT,
                value=178,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.bypass_setpoint is not None

    def test_process_input_fan_stop_threshold(self, hass: HomeAssistant) -> None:
        """Test processing input fan stop threshold."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_INPUT_FAN_STOP_THRESHOLD,
                value=215,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.input_fan_stop_threshold is not None

    def test_process_cell_defrost_setpoint(self, hass: HomeAssistant) -> None:
        """Test processing cell defrost setpoint."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_CELL_DEFROST_SETPOINT,
                value=4,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.cell_defrost_setpoint is not None

    def test_process_service_reminder(self, hass: HomeAssistant) -> None:
        """Test processing service reminder."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_SERVICE_REMINDER,
                value=6,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.service_reminder_months == 6

    def test_process_post_heating_on_cnt(self, hass: HomeAssistant) -> None:
        """Test processing post heating on counter."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_POST_HEATING_ON_CNT,
                value=10,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.post_heating_on_counter == 10

    def test_process_post_heating_off_time(self, hass: HomeAssistant) -> None:
        """Test processing post heating off time."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_POST_HEATING_OFF_TIME,
                value=5,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.post_heating_off_time == 5

    def test_process_post_heating_target(self, hass: HomeAssistant) -> None:
        """Test processing post heating target."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_POST_HEATING_TARGET,
                value=22,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.post_heating_target == 22

    def test_process_fireplace_countdown(self, hass: HomeAssistant) -> None:
        """Test processing fireplace countdown."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_FIREPLACE_COUNTDOWN,
                value=15,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.fireplace_countdown_minutes == 15

    def test_process_dc_fan_input_adj(self, hass: HomeAssistant) -> None:
        """Test processing DC fan input adjustment."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_DC_FAN_INPUT_ADJ,
                value=100,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.dc_fan_input_adjustment == 100

    def test_process_dc_fan_output_adj(self, hass: HomeAssistant) -> None:
        """Test processing DC fan output adjustment."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_DC_FAN_OUTPUT_ADJ,
                value=100,
            )
            coordinator._process_telegram(telegram)
            assert coordinator._state.dc_fan_output_adjustment == 100


class TestCoordinatorCommands:
    """Tests for command methods."""

    @pytest.mark.asyncio
    async def test_send_command(self, hass: HomeAssistant) -> None:
        """Test _send_command sends telegram."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._ensure_connected = AsyncMock()
            coordinator._send_telegram = AsyncMock()

            await coordinator._send_command(REG_FAN_SPEED, 0x0F)

            telegram = coordinator._send_telegram.await_args.args[0]
            assert telegram.register == REG_FAN_SPEED
            assert telegram.value == 0x0F

    @pytest.mark.asyncio
    async def test_set_select_bit_on(self, hass: HomeAssistant) -> None:
        """Test _set_select_bit sets bit to on."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._state._raw_values[REG_SELECT] = 0x00
            coordinator._send_command = AsyncMock()

            await coordinator._set_select_bit(BIT_POWER_STATE, True)

            coordinator._send_command.assert_called_once()
            args = coordinator._send_command.call_args[0]
            assert args[0] == REG_SELECT
            assert args[1] & (1 << BIT_POWER_STATE)

    @pytest.mark.asyncio
    async def test_set_select_bit_off(self, hass: HomeAssistant) -> None:
        """Test _set_select_bit sets bit to off."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._state._raw_values[REG_SELECT] = 0xFF
            coordinator._send_command = AsyncMock()

            await coordinator._set_select_bit(BIT_POWER_STATE, False)

            coordinator._send_command.assert_called_once()
            args = coordinator._send_command.call_args[0]
            assert args[0] == REG_SELECT
            assert not (args[1] & (1 << BIT_POWER_STATE))


class TestCoordinatorSetters:
    """Tests for async setter methods."""

    @pytest.mark.asyncio
    async def test_async_set_heating_state(self, hass: HomeAssistant) -> None:
        """Test async_set_heating_state."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._set_select_bit = AsyncMock()

            await coordinator.async_set_heating_state(True)

            coordinator._set_select_bit.assert_called_once_with(BIT_HEATING_STATE, True)

    @pytest.mark.asyncio
    async def test_async_set_co2_adjust(self, hass: HomeAssistant) -> None:
        """Test async_set_co2_adjust."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._set_select_bit = AsyncMock()

            await coordinator.async_set_co2_adjust(True)

            coordinator._set_select_bit.assert_called_once_with(BIT_CO2_ADJUST, True)

    @pytest.mark.asyncio
    async def test_async_set_rh_adjust(self, hass: HomeAssistant) -> None:
        """Test async_set_rh_adjust."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._set_select_bit = AsyncMock()

            await coordinator.async_set_rh_adjust(True)

            coordinator._set_select_bit.assert_called_once_with(BIT_RH_ADJUST, True)

    @pytest.mark.asyncio
    async def test_async_set_preheating_setpoint(self, hass: HomeAssistant) -> None:
        """Test async_set_preheating_setpoint."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._send_command = AsyncMock()

            await coordinator.async_set_preheating_setpoint(5)

            coordinator._send_command.assert_called_once()
            assert coordinator._send_command.call_args[0][0] == REG_PREHEATING_SETPOINT

    @pytest.mark.asyncio
    async def test_async_set_bypass_setpoint(self, hass: HomeAssistant) -> None:
        """Test async_set_bypass_setpoint."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._send_command = AsyncMock()

            await coordinator.async_set_bypass_setpoint(15)

            coordinator._send_command.assert_called_once()
            assert coordinator._send_command.call_args[0][0] == REG_BYPASS_SETPOINT

    @pytest.mark.asyncio
    async def test_async_set_input_fan_stop_threshold(
        self, hass: HomeAssistant
    ) -> None:
        """Test async_set_input_fan_stop_threshold."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._send_command = AsyncMock()

            await coordinator.async_set_input_fan_stop_threshold(-3)

            coordinator._send_command.assert_called_once()
            assert (
                coordinator._send_command.call_args[0][0]
                == REG_INPUT_FAN_STOP_THRESHOLD
            )

    @pytest.mark.asyncio
    async def test_async_set_cell_defrost_setpoint(self, hass: HomeAssistant) -> None:
        """Test async_set_cell_defrost_setpoint."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._send_command = AsyncMock()

            await coordinator.async_set_cell_defrost_setpoint(4)

            coordinator._send_command.assert_called_once()
            assert (
                coordinator._send_command.call_args[0][0] == REG_CELL_DEFROST_SETPOINT
            )

    @pytest.mark.asyncio
    async def test_async_set_fan_speed_min(self, hass: HomeAssistant) -> None:
        """Test async_set_fan_speed_min."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._send_command = AsyncMock()

            await coordinator.async_set_fan_speed_min(2)

            coordinator._send_command.assert_called_once()
            assert coordinator._send_command.call_args[0][0] == REG_FAN_SPEED_MIN

    @pytest.mark.asyncio
    async def test_async_set_fan_speed_max(self, hass: HomeAssistant) -> None:
        """Test async_set_fan_speed_max."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._send_command = AsyncMock()

            await coordinator.async_set_fan_speed_max(8)

            coordinator._send_command.assert_called_once()
            assert coordinator._send_command.call_args[0][0] == REG_FAN_SPEED_MAX

    @pytest.mark.asyncio
    async def test_async_set_service_reminder_months(self, hass: HomeAssistant) -> None:
        """Test async_set_service_reminder_months."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._send_command = AsyncMock()

            await coordinator.async_set_service_reminder_months(6)

            coordinator._send_command.assert_called_once()
            assert coordinator._send_command.call_args[0][0] == REG_SERVICE_REMINDER

    @pytest.mark.asyncio
    async def test_async_set_co2_setpoint(self, hass: HomeAssistant) -> None:
        """Test async_set_co2_setpoint."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._send_command = AsyncMock()

            await coordinator.async_set_co2_setpoint(1000)

            assert coordinator._send_command.call_count == 2
            calls = coordinator._send_command.call_args_list
            assert calls[0][0][0] == REG_CO2_SETPOINT_UPPER
            assert calls[1][0][0] == REG_CO2_SETPOINT_LOWER

    @pytest.mark.asyncio
    async def test_async_set_basic_humidity_level(self, hass: HomeAssistant) -> None:
        """Test async_set_basic_humidity_level."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._send_command = AsyncMock()

            await coordinator.async_set_basic_humidity_level(40)

            coordinator._send_command.assert_called_once()
            assert coordinator._send_command.call_args[0][0] == REG_BASIC_HUMIDITY_LEVEL


class TestCoordinatorWaitForData:
    """Tests for async_wait_for_initial_data."""

    @pytest.mark.asyncio
    async def test_wait_already_has_data(self, hass: HomeAssistant) -> None:
        """Test wait returns immediately when data exists."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._seen_registers = {REG_FAN_SPEED}

            await coordinator.async_wait_for_initial_data(timeout=1.0)

    @pytest.mark.asyncio
    async def test_wait_receives_data(self, hass: HomeAssistant) -> None:
        """Test wait succeeds when data arrives."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._seen_registers = set()

            async def mock_refresh():
                coordinator._seen_registers.add(REG_FAN_SPEED)

            coordinator.async_request_refresh = mock_refresh

            await coordinator.async_wait_for_initial_data(timeout=5.0)

            assert REG_FAN_SPEED in coordinator._seen_registers

    @pytest.mark.asyncio
    async def test_wait_timeout(self, hass: HomeAssistant) -> None:
        """Test wait times out gracefully."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
            coordinator._seen_registers = set()
            coordinator.async_request_refresh = AsyncMock()

            # Short timeout to speed up test
            await coordinator.async_wait_for_initial_data(timeout=0.1)
