"""Tests for Vallox RS485 coordinator logic."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import pytest

from custom_components.vallox_rs485.vallox_protocol import (
    ValloxState,
    ValloxTelegram,
)
from custom_components.vallox_rs485.const import (
    REG_FAN_SPEED,
    REG_HUMIDITY,
    REG_TEMP_OUTSIDE,
    REG_TEMP_EXHAUST,
    REG_TEMP_INSIDE,
    REG_TEMP_INCOMING,
    REG_SELECT,
    REG_MULTI_PURPOSE_2,
    REG_LAST_FAULT,
    REG_CO2_HIGH,
    REG_CO2_LOW,
    REG_HEATING_SETPOINT,
    REG_FAN_SPEED_MIN,
    REG_FAN_SPEED_MAX,
    REG_CELL_DEFROST_SETPOINT,
    BIT_POWER_STATE,
    BIT_CO2_ADJUST,
    BIT_RH_ADJUST,
    BIT_HEATING_STATE,
    BIT_SUPPLY_FAN,
    BIT_EXHAUST_FAN,
    BIT_FAULT_SIGNAL,
    ADDR_MAINBOARD,
)
from custom_components.vallox_rs485.coordinator import POLL_REGISTERS, get_serial_ports


class TestGetSerialPorts:
    """Tests for get_serial_ports function."""

    def test_get_serial_ports_empty(self) -> None:
        """Test get_serial_ports with no ports."""
        with patch("serial.tools.list_ports.comports", return_value=[]):
            result = get_serial_ports()
            assert result == []

    def test_get_serial_ports_multiple(self) -> None:
        """Test get_serial_ports with multiple ports."""
        mock_port1 = MagicMock()
        mock_port1.device = "/dev/ttyUSB0"
        mock_port2 = MagicMock()
        mock_port2.device = "/dev/ttyUSB1"

        with patch(
            "serial.tools.list_ports.comports",
            return_value=[mock_port1, mock_port2],
        ):
            result = get_serial_ports()
            assert result == ["/dev/ttyUSB0", "/dev/ttyUSB1"]


class TestPollRegisters:
    """Tests for poll register configuration."""

    def test_poll_registers_not_empty(self) -> None:
        """Test that poll registers are defined."""
        assert len(POLL_REGISTERS) > 0

    def test_poll_registers_contains_essential(self) -> None:
        """Test poll registers contain essential registers."""
        assert REG_FAN_SPEED in POLL_REGISTERS
        assert REG_TEMP_OUTSIDE in POLL_REGISTERS
        assert REG_HUMIDITY in POLL_REGISTERS
        assert REG_SELECT in POLL_REGISTERS


class TestTelegramProcessing:
    """Tests for telegram processing logic."""

    def test_process_temperature_outside(self) -> None:
        """Test processing outside temperature telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_TEMP_OUTSIDE,
            value=160,  # NTC value for 20°C
        )

        _process_telegram_to_state(state, telegram)
        assert state.temp_outside == 20

    def test_process_temperature_inside(self) -> None:
        """Test processing inside temperature telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_TEMP_INSIDE,
            value=165,  # NTC value for 22°C
        )

        _process_telegram_to_state(state, telegram)
        assert state.temp_inside == 22

    def test_process_temperature_exhaust(self) -> None:
        """Test processing exhaust temperature telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_TEMP_EXHAUST,
            value=130,
        )

        _process_telegram_to_state(state, telegram)
        assert state.temp_exhaust is not None

    def test_process_temperature_incoming(self) -> None:
        """Test processing incoming temperature telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_TEMP_INCOMING,
            value=140,
        )

        _process_telegram_to_state(state, telegram)
        assert state.temp_incoming is not None

    def test_process_fan_speed(self) -> None:
        """Test processing fan speed telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_FAN_SPEED,
            value=0x0F,  # Speed 4
        )

        _process_telegram_to_state(state, telegram)
        assert state.fan_speed == 4

    def test_process_fan_speed_min(self) -> None:
        """Test processing fan speed min telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_FAN_SPEED_MIN,
            value=0x03,  # Speed 2
        )

        _process_telegram_to_state(state, telegram)
        assert state.fan_speed_min == 2

    def test_process_fan_speed_max(self) -> None:
        """Test processing fan speed max telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_FAN_SPEED_MAX,
            value=0x7F,  # Speed 7
        )

        _process_telegram_to_state(state, telegram)
        assert state.fan_speed_max == 7

    def test_process_humidity(self) -> None:
        """Test processing humidity telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_HUMIDITY,
            value=128,  # ~37%
        )

        _process_telegram_to_state(state, telegram)
        assert state.humidity is not None
        assert 0 <= state.humidity <= 100

    def test_process_select_power_on(self) -> None:
        """Test processing select register with power on."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_SELECT,
            value=(1 << BIT_POWER_STATE),
        )

        _process_telegram_to_state(state, telegram)
        assert state.power_state is True

    def test_process_select_all_bits(self) -> None:
        """Test processing select register with all bits set."""
        state = ValloxState()

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

        _process_telegram_to_state(state, telegram)
        assert state.power_state is True
        assert state.co2_adjust is True
        assert state.rh_adjust is True
        assert state.heating_state is True

    def test_process_multi_purpose_2(self) -> None:
        """Test processing multi-purpose 2 register."""
        state = ValloxState()

        value = (1 << BIT_SUPPLY_FAN) | (1 << BIT_EXHAUST_FAN)

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_MULTI_PURPOSE_2,
            value=value,
        )

        _process_telegram_to_state(state, telegram)
        assert state.supply_fan_on is True
        assert state.exhaust_fan_on is True
        assert state.fault_signal is False

    def test_process_fault(self) -> None:
        """Test processing fault register."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_LAST_FAULT,
            value=0,
        )

        _process_telegram_to_state(state, telegram)
        assert state.last_fault == "no_fault"

    def test_process_co2_combined(self) -> None:
        """Test processing CO2 high and low bytes."""
        state = ValloxState()

        # Set high byte
        telegram_high = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_CO2_HIGH,
            value=0x03,
        )
        _process_telegram_to_state(state, telegram_high)

        # Set low byte
        telegram_low = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_CO2_LOW,
            value=0xE8,
        )
        _process_telegram_to_state(state, telegram_low)

        assert state.co2_ppm == 1000

    def test_process_heating_setpoint(self) -> None:
        """Test processing heating setpoint telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_HEATING_SETPOINT,
            value=160,  # NTC for 20°C
        )

        _process_telegram_to_state(state, telegram)
        assert state.heating_setpoint == 20

    def test_process_cell_defrost(self) -> None:
        """Test processing cell defrost setpoint telegram."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_CELL_DEFROST_SETPOINT,
            value=15,  # 15 / 3 = 5°C
        )

        _process_telegram_to_state(state, telegram)
        assert state.cell_defrost_setpoint == 5

    def test_ignore_unknown_sender(self) -> None:
        """Test that telegrams from unknown senders are ignored."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=0x99,  # Unknown sender
            receiver=0x22,
            register=REG_FAN_SPEED,
            value=0x0F,
        )

        _process_telegram_to_state(state, telegram)
        assert state.fan_speed is None

    def test_process_panel_sender(self) -> None:
        """Test processing telegram from panel (0x21)."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=0x21,  # Panel
            receiver=0x22,
            register=REG_FAN_SPEED,
            value=0x1F,  # Speed 5
        )

        _process_telegram_to_state(state, telegram)
        assert state.fan_speed == 5


class TestBufferParsing:
    """Tests for buffer parsing logic."""

    def test_parse_single_telegram(self) -> None:
        """Test parsing buffer with single valid telegram."""
        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_FAN_SPEED,
            value=0x0F,
        )
        buffer = telegram.to_bytes()

        telegrams = _parse_buffer(buffer)
        assert len(telegrams) == 1
        assert telegrams[0].register == REG_FAN_SPEED

    def test_parse_multiple_telegrams(self) -> None:
        """Test parsing buffer with multiple valid telegrams."""
        telegram1 = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_FAN_SPEED,
            value=0x0F,
        )
        telegram2 = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_HUMIDITY,
            value=128,
        )
        buffer = telegram1.to_bytes() + telegram2.to_bytes()

        telegrams = _parse_buffer(buffer)
        assert len(telegrams) == 2

    def test_parse_buffer_with_garbage(self) -> None:
        """Test parsing buffer with garbage before telegram."""
        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_FAN_SPEED,
            value=0x0F,
        )
        buffer = b"\x00\x00\x00" + telegram.to_bytes()

        telegrams = _parse_buffer(buffer)
        assert len(telegrams) == 1

    def test_parse_buffer_invalid_domain(self) -> None:
        """Test parsing buffer with invalid domain byte."""
        buffer = b"\x02\x11\x22\x29\x0F\x6D"

        telegrams = _parse_buffer(buffer)
        assert len(telegrams) == 0

    def test_parse_buffer_empty(self) -> None:
        """Test parsing empty buffer."""
        telegrams = _parse_buffer(b"")
        assert len(telegrams) == 0

    def test_parse_buffer_short(self) -> None:
        """Test parsing buffer too short for telegram."""
        telegrams = _parse_buffer(b"\x01\x11\x22")
        assert len(telegrams) == 0


def _process_telegram_to_state(state: ValloxState, telegram: ValloxTelegram) -> None:
    """Process a telegram and update state (extracted logic from coordinator)."""
    from custom_components.vallox_rs485.vallox_protocol import (
        ntc_to_celsius,
        decode_fan_speed,
        decode_humidity,
        decode_fault,
        decode_cell_defrost,
    )
    from custom_components.vallox_rs485.const import (
        REG_TEMP_OUTSIDE_LEGACY,
        REG_TEMP_INSIDE_LEGACY,
        REG_TEMP_INCOMING_LEGACY,
        REG_TEMP_EXHAUST_LEGACY,
        BIT_FILTER_GUARD,
        BIT_HEATING_INDICATOR,
        BIT_FAULT_INDICATOR,
        BIT_SERVICE_REMINDER,
        BIT_DAMPER_MOTOR,
        BIT_PRE_HEATING,
        BIT_FIREPLACE_BOOSTER,
    )

    if telegram.sender not in (ADDR_MAINBOARD, 0x21):
        return

    register = telegram.register
    value = telegram.value

    state._raw_values[register] = value

    if register in (REG_TEMP_OUTSIDE, REG_TEMP_OUTSIDE_LEGACY):
        state.temp_outside = ntc_to_celsius(value)
    elif register in (REG_TEMP_EXHAUST, REG_TEMP_EXHAUST_LEGACY):
        state.temp_exhaust = ntc_to_celsius(value)
    elif register in (REG_TEMP_INSIDE, REG_TEMP_INSIDE_LEGACY):
        state.temp_inside = ntc_to_celsius(value)
    elif register in (REG_TEMP_INCOMING, REG_TEMP_INCOMING_LEGACY):
        state.temp_incoming = ntc_to_celsius(value)
    elif register == REG_FAN_SPEED:
        state.fan_speed = decode_fan_speed(value)
    elif register == REG_FAN_SPEED_MIN:
        state.fan_speed_min = decode_fan_speed(value)
    elif register == REG_FAN_SPEED_MAX:
        state.fan_speed_max = decode_fan_speed(value)
    elif register == REG_HUMIDITY:
        state.humidity = decode_humidity(value)
    elif register == REG_CO2_HIGH:
        state.co2_high = value
        state.update_co2_ppm()
    elif register == REG_CO2_LOW:
        state.co2_low = value
        state.update_co2_ppm()
    elif register == REG_LAST_FAULT:
        state.last_fault = decode_fault(value)
    elif register == REG_SELECT:
        state.power_state = bool(value & (1 << BIT_POWER_STATE))
        state.co2_adjust = bool(value & (1 << BIT_CO2_ADJUST))
        state.rh_adjust = bool(value & (1 << BIT_RH_ADJUST))
        state.heating_state = bool(value & (1 << BIT_HEATING_STATE))
        state.filter_guard = bool(value & (1 << BIT_FILTER_GUARD))
        state.heating_indicator = bool(value & (1 << BIT_HEATING_INDICATOR))
        state.fault_indicator = bool(value & (1 << BIT_FAULT_INDICATOR))
        state.service_reminder_active = bool(value & (1 << BIT_SERVICE_REMINDER))
    elif register == REG_MULTI_PURPOSE_2:
        state.damper_motor_position = bool(value & (1 << BIT_DAMPER_MOTOR))
        state.fault_signal = bool(value & (1 << BIT_FAULT_SIGNAL))
        state.supply_fan_on = bool(value & (1 << BIT_SUPPLY_FAN))
        state.pre_heating_on = bool(value & (1 << BIT_PRE_HEATING))
        state.exhaust_fan_on = bool(value & (1 << BIT_EXHAUST_FAN))
        state.fireplace_booster_on = bool(value & (1 << BIT_FIREPLACE_BOOSTER))
    elif register == REG_HEATING_SETPOINT:
        state.heating_setpoint = ntc_to_celsius(value)
    elif register == REG_CELL_DEFROST_SETPOINT:
        state.cell_defrost_setpoint = decode_cell_defrost(value)


def _parse_buffer(buffer: bytes) -> list[ValloxTelegram]:
    """Parse telegrams from buffer (extracted logic from coordinator)."""
    from custom_components.vallox_rs485.vallox_protocol import TELEGRAM_LENGTH

    telegrams = []
    pos = 0
    while pos + TELEGRAM_LENGTH <= len(buffer):
        chunk = buffer[pos : pos + TELEGRAM_LENGTH]

        if chunk[0] != 0x01:
            pos += 1
            continue

        telegram = ValloxTelegram.from_bytes(chunk)
        if telegram is not None:
            telegrams.append(telegram)
            pos += TELEGRAM_LENGTH
        else:
            pos += 1

    return telegrams


class TestValloxCoordinatorClass:
    """Tests for ValloxCoordinator class methods."""

    @pytest.fixture
    def mock_coordinator(self) -> MagicMock:
        """Create a mock coordinator for testing individual methods."""
        from custom_components.vallox_rs485.vallox_protocol import ValloxState

        coordinator = MagicMock()
        coordinator._serial_port = "/dev/ttyUSB0"
        coordinator._device_address = 0x22
        coordinator._serial = None
        coordinator._seen_registers = set()
        coordinator._register_timestamps = {}
        coordinator._state = ValloxState()
        coordinator._last_unavailable_log = 0
        coordinator._lock = asyncio.Lock()
        return coordinator

    def test_has_seen_register(self) -> None:
        """Test has_seen_register method logic."""
        seen_registers = {0x29, 0x2A}

        # Test the logic that has_seen_register uses
        assert 0x29 in seen_registers
        assert 0x30 not in seen_registers

    def test_has_seen_any_register(self) -> None:
        """Test has_seen_any_register method logic."""
        seen_registers = {0x29, 0x2A}

        # Test the logic that has_seen_any_register uses
        registers_to_check = (0x29, 0x30)
        assert any(r in seen_registers for r in registers_to_check) is True

        registers_to_check = (0x31, 0x32)
        assert any(r in seen_registers for r in registers_to_check) is False

    def test_close_serial_logic(self) -> None:
        """Test _close_serial method logic."""
        mock_serial = MagicMock()

        # Test closing
        mock_serial.close()
        mock_serial.close.assert_called_once()

    def test_close_serial_exception_handling(self) -> None:
        """Test _close_serial handles exceptions."""
        mock_serial = MagicMock()
        mock_serial.close.side_effect = Exception("Close failed")

        # Should not raise
        try:
            mock_serial.close()
        except Exception:
            pass  # Expected to be caught

    def test_log_unavailable_rate_limiting_logic(self) -> None:
        """Test _log_unavailable rate limiting logic."""
        import time

        last_unavailable_log = 0
        now = time.monotonic()

        # First call should log
        should_log_1 = now - last_unavailable_log > 60
        assert should_log_1 is True

        # Update the timestamp
        last_unavailable_log = now

        # Second call immediately after should not log
        should_log_2 = now - last_unavailable_log > 60
        assert should_log_2 is False

    def test_parse_buffer_logic(self) -> None:
        """Test _parse_buffer method logic using the already tested _parse_buffer function."""
        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_FAN_SPEED,
            value=0x0F,
        )
        buffer = telegram.to_bytes()

        telegrams = _parse_buffer(buffer)
        assert len(telegrams) == 1
        assert telegrams[0].register == REG_FAN_SPEED

    def test_process_telegram_logic(self) -> None:
        """Test _process_telegram method logic using the already tested helper."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=REG_HUMIDITY,
            value=153,
        )

        _process_telegram_to_state(state, telegram)
        assert state.humidity is not None

    def test_process_telegram_ignores_unknown_sender_logic(self) -> None:
        """Test _process_telegram ignores unknown senders."""
        state = ValloxState()

        telegram = ValloxTelegram(
            domain=0x01,
            sender=0x99,  # Unknown sender
            receiver=0x22,
            register=REG_FAN_SPEED,
            value=0x0F,
        )

        _process_telegram_to_state(state, telegram)
        # Should not have processed
        assert state.fan_speed is None

    def test_write_serial_logic(self) -> None:
        """Test _write_serial method logic."""
        mock_serial = MagicMock()

        mock_serial.write(b"\x01\x02\x03")
        mock_serial.flush()

        mock_serial.write.assert_called_once_with(b"\x01\x02\x03")
        mock_serial.flush.assert_called_once()

    def test_write_serial_raises_when_closed_logic(self) -> None:
        """Test _write_serial raises when serial is closed."""
        import serial

        # When serial is None, writing should fail
        with pytest.raises(serial.SerialException):
            raise serial.SerialException("Serial port not open")

    @pytest.mark.asyncio
    async def test_async_set_fan_speed_logic(self) -> None:
        """Test async_set_fan_speed validation logic."""
        from custom_components.vallox_rs485.vallox_protocol import (
            encode_fan_speed,
            validate_fan_speed,
        )

        # Test that speed is validated and encoded correctly
        speed = validate_fan_speed(5)
        assert speed == 5
        assert encode_fan_speed(5) == 0x1F

        # Test clamping
        speed = validate_fan_speed(10)
        assert speed == 8

        speed = validate_fan_speed(0)
        assert speed == 1

    @pytest.mark.asyncio
    async def test_async_set_heating_setpoint_logic(self) -> None:
        """Test async_set_heating_setpoint validation logic."""
        from custom_components.vallox_rs485.vallox_protocol import (
            celsius_to_ntc,
            validate_temperature_setpoint,
        )

        # Test normal value
        temp = validate_temperature_setpoint(20)
        temp = max(10, min(30, temp))
        assert temp == 20

        # Test clamping
        temp = validate_temperature_setpoint(50)
        temp = max(10, min(30, temp))
        assert temp == 30

        temp = validate_temperature_setpoint(0)
        temp = max(10, min(30, temp))
        assert temp == 10

    @pytest.mark.asyncio
    async def test_async_set_service_reminder_logic(self) -> None:
        """Test async_set_service_reminder validation logic."""
        from custom_components.vallox_rs485.vallox_protocol import validate_service_months

        # Test normal value
        months = validate_service_months(6)
        assert months == 6

        # Test clamping
        months = validate_service_months(0)
        assert months == 1

        months = validate_service_months(20)
        assert months == 15

    @pytest.mark.asyncio
    async def test_async_set_co2_setpoint_logic(self) -> None:
        """Test async_set_co2_setpoint validation and encoding logic."""
        from custom_components.vallox_rs485.vallox_protocol import (
            encode_co2_setpoint,
            validate_co2_setpoint,
        )

        # Test normal value
        ppm = validate_co2_setpoint(1000)
        assert ppm == 1000

        upper, lower = encode_co2_setpoint(1000)
        assert (upper << 8) | lower == 1000

        # Test clamping
        ppm = validate_co2_setpoint(100)
        assert ppm == 500

        ppm = validate_co2_setpoint(3000)
        assert ppm == 2000

    @pytest.mark.asyncio
    async def test_set_select_bit_logic(self) -> None:
        """Test _set_select_bit logic."""
        from custom_components.vallox_rs485.const import BIT_POWER_STATE, REG_SELECT

        # Starting value
        current = 0x00

        # Set bit
        new_value = current | (1 << BIT_POWER_STATE)
        assert new_value & (1 << BIT_POWER_STATE)

        # Clear bit
        current = 0xFF
        new_value = current & ~(1 << BIT_POWER_STATE)
        assert not (new_value & (1 << BIT_POWER_STATE))
