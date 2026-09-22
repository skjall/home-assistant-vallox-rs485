"""Data update coordinator for Vallox RS485."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta

import serial
import serial.tools.list_ports
import serial_asyncio_fast
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_BAUDRATE,
    DEFAULT_SCAN_INTERVAL,
    ADDR_MAINBOARD,
    REG_FAN_SPEED,
    REG_HUMIDITY,
    REG_HUMIDITY_SENSOR1,
    REG_HUMIDITY_SENSOR2,
    REG_CO2_HIGH,
    REG_CO2_LOW,
    REG_CO2_SETPOINT_UPPER,
    REG_CO2_SETPOINT_LOWER,
    REG_TEMP_OUTSIDE,
    REG_TEMP_EXHAUST,
    REG_TEMP_INSIDE,
    REG_TEMP_INCOMING,
    REG_TEMP_OUTSIDE_LEGACY,
    REG_TEMP_INSIDE_LEGACY,
    REG_TEMP_INCOMING_LEGACY,
    REG_TEMP_EXHAUST_LEGACY,
    REG_LAST_FAULT,
    REG_SELECT,
    REG_MULTI_PURPOSE_2,
    REG_FAN_SPEED_MIN,
    REG_FAN_SPEED_MAX,
    REG_HEATING_SETPOINT,
    REG_PREHEATING_SETPOINT,
    REG_BYPASS_SETPOINT,
    REG_SERVICE_REMINDER,
    REG_INPUT_FAN_STOP_THRESHOLD,
    REG_BASIC_HUMIDITY_LEVEL,
    REG_CELL_DEFROST_SETPOINT,
    REG_DC_FAN_INPUT_ADJ,
    REG_DC_FAN_OUTPUT_ADJ,
    REG_POST_HEATING_ON_CNT,
    REG_POST_HEATING_OFF_TIME,
    REG_POST_HEATING_TARGET,
    REG_FIREPLACE_COUNTDOWN,
    REG_FLAGS_6,
    BIT_POWER_STATE,
    BIT_CO2_ADJUST,
    BIT_RH_ADJUST,
    BIT_HEATING_STATE,
    BIT_FILTER_GUARD,
    BIT_HEATING_INDICATOR,
    BIT_FAULT_INDICATOR,
    BIT_SERVICE_REMINDER,
    BIT_DAMPER_MOTOR,
    BIT_FAULT_SIGNAL,
    BIT_SUPPLY_FAN,
    BIT_PRE_HEATING,
    BIT_EXHAUST_FAN,
    BIT_FIREPLACE_BOOSTER,
    BIT_REMOTE_CONTROL_WORKING,
    BIT_FIREPLACE_BOOST_ACTIVE,
)
from .vallox_protocol import (
    ValloxTelegram,
    ValloxState,
    ntc_to_celsius,
    celsius_to_ntc,
    decode_fan_speed,
    decode_humidity,
    decode_fault,
    decode_cell_defrost,
    encode_fan_speed,
    encode_humidity,
    encode_cell_defrost,
    encode_co2_setpoint,
    validate_fan_speed,
    validate_temperature_setpoint,
    validate_humidity,
    validate_co2_setpoint,
    validate_service_months,
    create_read_request,
    create_write_request,
    TELEGRAM_LENGTH,
)

POLL_REGISTERS: tuple[int, ...] = (
    REG_FAN_SPEED,
    REG_HUMIDITY,
    REG_CO2_HIGH,
    REG_CO2_LOW,
    REG_HUMIDITY_SENSOR1,
    REG_HUMIDITY_SENSOR2,
    REG_TEMP_OUTSIDE,
    REG_TEMP_EXHAUST,
    REG_TEMP_INSIDE,
    REG_TEMP_INCOMING,
    REG_LAST_FAULT,
    REG_SELECT,
    REG_MULTI_PURPOSE_2,
    REG_HEATING_SETPOINT,
    REG_PREHEATING_SETPOINT,
    REG_BYPASS_SETPOINT,
    REG_INPUT_FAN_STOP_THRESHOLD,
    REG_CELL_DEFROST_SETPOINT,
    REG_FAN_SPEED_MIN,
    REG_FAN_SPEED_MAX,
    REG_SERVICE_REMINDER,
    REG_CO2_SETPOINT_UPPER,
    REG_CO2_SETPOINT_LOWER,
    REG_BASIC_HUMIDITY_LEVEL,
    REG_POST_HEATING_ON_CNT,
    REG_FIREPLACE_COUNTDOWN,
)

_LOGGER = logging.getLogger(__name__)


def get_serial_ports() -> list[str]:
    """Get list of available serial ports."""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]


class ValloxCoordinator(DataUpdateCoordinator[ValloxState]):
    """Coordinator for Vallox RS485 communication using async serial."""

    def __init__(
        self,
        hass: HomeAssistant,
        serial_port: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        device_address: int = 0x22,
        entry_id: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._serial_port = serial_port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        # Guards the writer. Never taken around a call that writes again:
        # asyncio.Lock is not reentrant.
        self._lock = asyncio.Lock()
        # Guards read-modify-write on SELECT, which spans two awaits.
        self._select_lock = asyncio.Lock()
        self._state = ValloxState()
        self._last_unavailable_log: float = 0
        self._device_address = device_address
        self._seen_registers: set[int] = set()
        self._register_timestamps: dict[int, float] = {}
        self._unknown_registers_warned: set[int] = set()
        self._max_register_age: float = 300.0
        self._entry_id = entry_id
        self._consecutive_errors: int = 0
        self._repair_issue_created: bool = False
        self._listener_task: asyncio.Task[None] | None = None

    async def _async_update_data(self) -> ValloxState:
        """Fetch data from the Vallox device."""
        try:
            await self._ensure_connected()
            await self._poll_missing_registers()
            self._clear_error_state()
            return self._state
        except serial.SerialException as err:
            self._log_unavailable(f"Serial communication error: {err}")
            await self._close_serial()
            self._handle_error("serial_connection_failed")
            raise UpdateFailed(f"Serial communication error: {err}") from err
        except TimeoutError as err:
            self._log_unavailable(f"Communication timeout: {err}")
            self._handle_error("communication_timeout")
            raise UpdateFailed(f"Communication timeout: {err}") from err
        except OSError as err:
            self._log_unavailable(f"OS error: {err}")
            await self._close_serial()
            self._handle_error("serial_connection_failed")
            raise UpdateFailed(f"OS error: {err}") from err

    def _handle_error(self, error_type: str) -> None:
        """Handle error and create repair issue if persistent."""
        self._consecutive_errors += 1
        if self._consecutive_errors >= 3 and not self._repair_issue_created:
            self._create_repair_issue(error_type)

    def _clear_error_state(self) -> None:
        """Clear error state after successful update."""
        if self._consecutive_errors > 0:
            self._consecutive_errors = 0
            if self._repair_issue_created:
                self._delete_repair_issue()

    def _create_repair_issue(self, error_type: str) -> None:
        """Create a repair issue for connection problems."""
        if self._entry_id is None:
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            f"{error_type}_{self._entry_id}",
            is_fixable=False,
            is_persistent=True,
            severity=ir.IssueSeverity.ERROR,
            translation_key=error_type,
            translation_placeholders={"serial_port": self._serial_port},
        )
        self._repair_issue_created = True
        _LOGGER.info("Created repair issue for %s", error_type)

    def _delete_repair_issue(self) -> None:
        """Delete repair issue when connection is restored."""
        if self._entry_id is None:
            return
        for error_type in ("serial_connection_failed", "communication_timeout"):
            ir.async_delete_issue(
                self.hass,
                DOMAIN,
                f"{error_type}_{self._entry_id}",
            )
        self._repair_issue_created = False
        _LOGGER.info("Cleared repair issues - connection restored")

    def _log_unavailable(self, message: str) -> None:
        """Log unavailable message only once per minute."""
        now = time.monotonic()
        if now - self._last_unavailable_log > 60:
            _LOGGER.warning(message)
            self._last_unavailable_log = now

    async def _ensure_connected(self) -> None:
        """Ensure async serial connection is open."""
        if self._reader is None or self._writer is None:
            await self._open_serial()

    async def _open_serial(self) -> None:
        """Open async serial connection."""
        _LOGGER.debug("Opening serial port %s", self._serial_port)
        self._reader, self._writer = await serial_asyncio_fast.open_serial_connection(
            url=self._serial_port,
            baudrate=DEFAULT_BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        self._start_bus_listener()

    async def _close_serial(self) -> None:
        """Close async serial connection."""
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None

    def _start_bus_listener(self) -> None:
        """Start background task to listen for bus traffic."""
        if self._listener_task is None or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._bus_listener())

    async def _bus_listener(self) -> None:
        """Continuously listen for telegrams on the bus."""
        buffer = b""
        while True:
            try:
                if self._reader is None:
                    await asyncio.sleep(1)
                    continue

                data = await asyncio.wait_for(self._reader.read(64), timeout=5.0)
                if not data:
                    continue

                buffer += data
                buffer = self._parse_buffer(buffer)

            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.debug("Bus listener error: %s", err)
                await asyncio.sleep(1)

    def _parse_buffer(self, buffer: bytes) -> bytes:
        """Parse telegrams from buffer, return remaining bytes."""
        while len(buffer) >= TELEGRAM_LENGTH:
            if buffer[0] != 0x01:
                buffer = buffer[1:]
                continue

            chunk = buffer[:TELEGRAM_LENGTH]
            telegram = ValloxTelegram.from_bytes(chunk)

            if telegram is not None:
                _LOGGER.debug(
                    "RX: %s (sender=0x%02X reg=0x%02X val=0x%02X)",
                    chunk.hex(' '), telegram.sender, telegram.register, telegram.value
                )
                self._process_telegram(telegram)
                buffer = buffer[TELEGRAM_LENGTH:]
            else:
                buffer = buffer[1:]

        return buffer

    async def _poll_missing_registers(self) -> None:
        """Actively poll registers we haven't seen or that are stale."""
        now = time.monotonic()
        to_poll = []

        for register in POLL_REGISTERS:
            if register not in self._seen_registers:
                to_poll.append(register)
            elif now - self._register_timestamps.get(register, 0) > self._max_register_age:
                to_poll.append(register)

        if not to_poll:
            return

        _LOGGER.debug("Polling %d missing/stale registers", len(to_poll))
        for register in to_poll:
            try:
                await self._request_register(register)
            except Exception as err:
                _LOGGER.debug("Failed to poll register 0x%02X: %s", register, err)

    async def _request_register(self, register: int) -> None:
        """Request a single register value from the device."""
        telegram = create_read_request(register, self._device_address)
        await self._send_telegram(telegram)
        await asyncio.sleep(0.3)

    async def _send_telegram(self, telegram: ValloxTelegram) -> None:
        """Send a telegram to the bus."""
        await self._ensure_connected()
        if self._writer is None:
            raise HomeAssistantError(translation_key="not_connected")

        data = telegram.to_bytes()
        _LOGGER.debug(
            "TX: %s (to=0x%02X reg=0x%02X val=0x%02X)",
            data.hex(' '), telegram.receiver, telegram.register, telegram.value
        )

        async with self._lock:
            try:
                self._writer.write(data)
                await self._writer.drain()
            except (serial.SerialException, OSError) as err:
                raise HomeAssistantError(translation_key="command_failed") from err

    def _process_telegram(self, telegram: ValloxTelegram) -> None:
        """Process a received telegram and update state."""
        if telegram.sender == self._device_address:
            return

        if telegram.sender not in (ADDR_MAINBOARD, 0x21):
            return

        register = telegram.register
        value = telegram.value

        self._state._raw_values[register] = value
        self._seen_registers.add(register)
        self._register_timestamps[register] = time.monotonic()

        if register in (REG_TEMP_OUTSIDE, REG_TEMP_OUTSIDE_LEGACY):
            self._state.temp_outside = ntc_to_celsius(value)
        elif register in (REG_TEMP_EXHAUST, REG_TEMP_EXHAUST_LEGACY):
            self._state.temp_exhaust = ntc_to_celsius(value)
        elif register in (REG_TEMP_INSIDE, REG_TEMP_INSIDE_LEGACY):
            self._state.temp_inside = ntc_to_celsius(value)
        elif register in (REG_TEMP_INCOMING, REG_TEMP_INCOMING_LEGACY):
            self._state.temp_incoming = ntc_to_celsius(value)
        elif register == REG_FAN_SPEED:
            self._state.fan_speed = decode_fan_speed(value)
        elif register == REG_FAN_SPEED_MIN:
            self._state.fan_speed_min = decode_fan_speed(value)
        elif register == REG_FAN_SPEED_MAX:
            self._state.fan_speed_max = decode_fan_speed(value)
        elif register == REG_HUMIDITY:
            self._state.humidity = decode_humidity(value)
        elif register == REG_HUMIDITY_SENSOR1:
            self._state.humidity_sensor1 = decode_humidity(value)
        elif register == REG_HUMIDITY_SENSOR2:
            self._state.humidity_sensor2 = decode_humidity(value)
        elif register == REG_BASIC_HUMIDITY_LEVEL:
            self._state.basic_humidity_level = decode_humidity(value)
        elif register == REG_CO2_HIGH:
            self._state.co2_high = value
            self._state.update_co2_ppm()
        elif register == REG_CO2_LOW:
            self._state.co2_low = value
            self._state.update_co2_ppm()
        elif register == REG_CO2_SETPOINT_UPPER:
            upper = value
            lower = self._state._raw_values.get(REG_CO2_SETPOINT_LOWER, 0)
            self._state.co2_setpoint = (upper << 8) | lower
        elif register == REG_CO2_SETPOINT_LOWER:
            upper = self._state._raw_values.get(REG_CO2_SETPOINT_UPPER, 0)
            lower = value
            self._state.co2_setpoint = (upper << 8) | lower
        elif register == REG_LAST_FAULT:
            self._state.last_fault = decode_fault(value)
        elif register == REG_SELECT:
            self._state.power_state = bool(value & (1 << BIT_POWER_STATE))
            self._state.co2_adjust = bool(value & (1 << BIT_CO2_ADJUST))
            self._state.rh_adjust = bool(value & (1 << BIT_RH_ADJUST))
            self._state.heating_state = bool(value & (1 << BIT_HEATING_STATE))
            self._state.filter_guard = bool(value & (1 << BIT_FILTER_GUARD))
            self._state.heating_indicator = bool(value & (1 << BIT_HEATING_INDICATOR))
            self._state.fault_indicator = bool(value & (1 << BIT_FAULT_INDICATOR))
            self._state.service_reminder_active = bool(value & (1 << BIT_SERVICE_REMINDER))
        elif register == REG_MULTI_PURPOSE_2:
            self._state.damper_motor_position = bool(value & (1 << BIT_DAMPER_MOTOR))
            self._state.fault_signal = bool(value & (1 << BIT_FAULT_SIGNAL))
            self._state.supply_fan_on = bool(value & (1 << BIT_SUPPLY_FAN))
            self._state.pre_heating_on = bool(value & (1 << BIT_PRE_HEATING))
            self._state.exhaust_fan_on = bool(value & (1 << BIT_EXHAUST_FAN))
            self._state.fireplace_booster_on = bool(value & (1 << BIT_FIREPLACE_BOOSTER))
        elif register == REG_HEATING_SETPOINT:
            self._state.heating_setpoint = ntc_to_celsius(value)
        elif register == REG_PREHEATING_SETPOINT:
            self._state.preheating_setpoint = ntc_to_celsius(value)
        elif register == REG_BYPASS_SETPOINT:
            self._state.bypass_setpoint = ntc_to_celsius(value)
        elif register == REG_INPUT_FAN_STOP_THRESHOLD:
            self._state.input_fan_stop_threshold = ntc_to_celsius(value)
        elif register == REG_CELL_DEFROST_SETPOINT:
            self._state.cell_defrost_setpoint = decode_cell_defrost(value)
        elif register == REG_SERVICE_REMINDER:
            self._state.service_reminder_months = value
        elif register == REG_POST_HEATING_ON_CNT:
            self._state.post_heating_on_counter = value
        elif register == REG_POST_HEATING_OFF_TIME:
            self._state.post_heating_off_time = value
        elif register == REG_POST_HEATING_TARGET:
            self._state.post_heating_target = value
        elif register == REG_FIREPLACE_COUNTDOWN:
            self._state.fireplace_countdown_minutes = value
        elif register == REG_DC_FAN_INPUT_ADJ:
            self._state.dc_fan_input_adjustment = value
        elif register == REG_DC_FAN_OUTPUT_ADJ:
            self._state.dc_fan_output_adjustment = value
        elif register == REG_FLAGS_6:
            self._state.remote_control_working = bool(value & (1 << BIT_REMOTE_CONTROL_WORKING))
            self._state.fireplace_boost_active = bool(value & (1 << BIT_FIREPLACE_BOOST_ACTIVE))
        else:
            if register not in self._unknown_registers_warned:
                self._unknown_registers_warned.add(register)
                _LOGGER.warning(
                    "Unknown register: %s (sender=0x%02X reg=0x%02X val=0x%02X)",
                    telegram.to_bytes().hex(' '), telegram.sender, register, value
                )

    async def _send_command(self, register: int, value: int) -> None:
        """Send a command to the Vallox device."""
        telegram = create_write_request(register, value, self._device_address)
        _LOGGER.debug("Sending command: register=0x%02X value=0x%02X", register, value)
        await self._send_telegram(telegram)

    async def _set_select_bit(self, bit: int, state: bool) -> None:
        """Set a single bit in the SELECT register.

        SELECT holds several independent switches, so a write has to start
        from the value currently on the bus. Until one has been seen there is
        nothing to modify, and writing a guess would silently flip whatever
        else lives in that register.
        """
        async with self._select_lock:
            if REG_SELECT not in self._state._raw_values:
                raise HomeAssistantError(translation_key="select_unknown")
            current = self._state._raw_values[REG_SELECT]
            if state:
                new_value = current | (1 << bit)
            else:
                new_value = current & ~(1 << bit)
            await self._send_command(REG_SELECT, new_value)

    async def async_set_fan_speed(self, speed: int) -> None:
        """Set fan speed (1-8)."""
        speed = validate_fan_speed(speed)
        await self._send_command(REG_FAN_SPEED, encode_fan_speed(speed))

    async def async_set_power_state(self, state: bool) -> None:
        """Set power state."""
        await self._set_select_bit(BIT_POWER_STATE, state)

    async def async_set_heating_state(self, state: bool) -> None:
        """Set heating state."""
        await self._set_select_bit(BIT_HEATING_STATE, state)

    async def async_set_co2_adjust(self, state: bool) -> None:
        """Set CO2 adjustment state."""
        await self._set_select_bit(BIT_CO2_ADJUST, state)

    async def async_set_rh_adjust(self, state: bool) -> None:
        """Set RH (humidity) adjustment state."""
        await self._set_select_bit(BIT_RH_ADJUST, state)

    async def async_set_heating_setpoint(self, temp: int) -> None:
        """Set heating setpoint temperature (10-30°C)."""
        temp = validate_temperature_setpoint(temp)
        temp = max(10, min(30, temp))
        await self._send_command(REG_HEATING_SETPOINT, celsius_to_ntc(temp))

    async def async_set_preheating_setpoint(self, temp: int) -> None:
        """Set preheating setpoint temperature (-6 to 15°C)."""
        temp = max(-6, min(15, temp))
        await self._send_command(REG_PREHEATING_SETPOINT, celsius_to_ntc(temp))

    async def async_set_bypass_setpoint(self, temp: int) -> None:
        """Set bypass setpoint temperature (0-20°C)."""
        temp = max(0, min(20, temp))
        await self._send_command(REG_BYPASS_SETPOINT, celsius_to_ntc(temp))

    async def async_set_input_fan_stop_threshold(self, temp: int) -> None:
        """Set frost protection threshold (-6 to 15°C)."""
        temp = max(-6, min(15, temp))
        await self._send_command(REG_INPUT_FAN_STOP_THRESHOLD, celsius_to_ntc(temp))

    async def async_set_cell_defrost_setpoint(self, temp: int) -> None:
        """Set cell defrost hysteresis (0-10°C)."""
        temp = max(0, min(10, temp))
        await self._send_command(REG_CELL_DEFROST_SETPOINT, encode_cell_defrost(temp))

    async def async_set_fan_speed_min(self, speed: int) -> None:
        """Set minimum fan speed (1-8)."""
        speed = validate_fan_speed(speed)
        await self._send_command(REG_FAN_SPEED_MIN, encode_fan_speed(speed))

    async def async_set_fan_speed_max(self, speed: int) -> None:
        """Set maximum fan speed (1-8)."""
        speed = validate_fan_speed(speed)
        await self._send_command(REG_FAN_SPEED_MAX, encode_fan_speed(speed))

    async def async_set_service_reminder_months(self, months: int) -> None:
        """Set service reminder interval (1-15 months)."""
        months = validate_service_months(months)
        await self._send_command(REG_SERVICE_REMINDER, months)

    async def async_set_co2_setpoint(self, ppm: int) -> None:
        """Set CO2 setpoint (500-2000 ppm)."""
        ppm = validate_co2_setpoint(ppm)
        upper, lower = encode_co2_setpoint(ppm)
        await self._send_command(REG_CO2_SETPOINT_UPPER, upper)
        await self._send_command(REG_CO2_SETPOINT_LOWER, lower)

    async def async_set_basic_humidity_level(self, percent: int) -> None:
        """Set basic humidity level threshold (0-100%)."""
        percent = validate_humidity(percent)
        await self._send_command(REG_BASIC_HUMIDITY_LEVEL, encode_humidity(percent))

    def has_seen_register(self, register: int) -> bool:
        """Check if a register has been seen on the bus."""
        return register in self._seen_registers

    def has_seen_any_register(self, registers: tuple[int, ...]) -> bool:
        """Check if any of the given registers have been seen."""
        return any(r in self._seen_registers for r in registers)

    async def async_wait_for_initial_data(self, timeout: float = 10.0) -> bool:
        """Wait for the first registers to arrive; report whether they did.

        The unit talks when it wants to, so the first telegram can be seconds
        away. Reporting the outcome rather than logging it lets setup fail
        properly instead of creating entities that will never have a value.
        """
        if self._seen_registers:
            return True

        _LOGGER.debug("Waiting for initial bus data (timeout: %.1fs)", timeout)
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            await self.async_request_refresh()
            if self._seen_registers:
                _LOGGER.debug("Initial data received: %d registers", len(self._seen_registers))
                return True
            await asyncio.sleep(1.0)
        return False

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self._close_serial()
