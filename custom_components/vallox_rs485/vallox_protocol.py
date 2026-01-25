"""Vallox RS485 protocol implementation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .const import (
    VALLOX_DOMAIN,
    ADDR_MAINBOARD,
    ADDR_THIS_DEVICE,
    NTC_TO_CELSIUS,
    CELSIUS_TO_NTC,
    FAN_SPEED_TO_HEX,
    HEX_TO_FAN_SPEED,
    FAULT_CODES,
)

_LOGGER = logging.getLogger(__name__)

TELEGRAM_LENGTH = 6

# Validation ranges
VALID_FAN_SPEED_RANGE = (1, 8)
VALID_TEMPERATURE_SETPOINT_RANGE = (-6, 30)
VALID_HUMIDITY_RANGE = (0, 100)
VALID_CO2_RANGE = (0, 2550)
VALID_SERVICE_MONTHS_RANGE = (1, 15)


@dataclass
class ValloxTelegram:
    """Representation of a Vallox RS485 telegram."""

    domain: int = VALLOX_DOMAIN
    sender: int = 0
    receiver: int = 0
    register: int = 0
    value: int = 0
    checksum: int = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> ValloxTelegram | None:
        """Parse telegram from bytes."""
        if len(data) != TELEGRAM_LENGTH:
            _LOGGER.debug("Invalid telegram length: %d", len(data))
            return None

        telegram = cls(
            domain=data[0],
            sender=data[1],
            receiver=data[2],
            register=data[3],
            value=data[4],
            checksum=data[5],
        )

        if not telegram.verify_checksum():
            _LOGGER.debug("Checksum mismatch: expected %02x, got %02x",
                         telegram.calculate_checksum(), telegram.checksum)
            return None

        return telegram

    def to_bytes(self) -> bytes:
        """Convert telegram to bytes."""
        self.checksum = self.calculate_checksum()
        return bytes([
            self.domain,
            self.sender,
            self.receiver,
            self.register,
            self.value,
            self.checksum,
        ])

    def calculate_checksum(self) -> int:
        """Calculate telegram checksum."""
        return (self.domain + self.sender + self.receiver +
                self.register + self.value) & 0xFF

    def verify_checksum(self) -> bool:
        """Verify telegram checksum."""
        return self.checksum == self.calculate_checksum()


@dataclass
class ValloxState:
    """Current state of the Vallox device."""

    # Temperatures (°C)
    temp_outside: int | None = None
    temp_exhaust: int | None = None
    temp_inside: int | None = None
    temp_incoming: int | None = None

    # Fan
    fan_speed: int | None = None  # 1-8
    fan_speed_min: int | None = None
    fan_speed_max: int | None = None

    # Humidity
    humidity: int | None = None  # %
    humidity_sensor1: int | None = None
    humidity_sensor2: int | None = None
    basic_humidity_level: int | None = None  # Manual threshold %

    # CO2
    co2_high: int | None = None
    co2_low: int | None = None
    co2_ppm: int | None = None  # Combined value
    co2_setpoint: int | None = None  # ppm threshold

    # Control states
    power_state: bool | None = None
    co2_adjust: bool | None = None
    rh_adjust: bool | None = None
    heating_state: bool | None = None
    filter_guard: bool | None = None
    heating_indicator: bool | None = None
    fault_indicator: bool | None = None

    # Status
    supply_fan_on: bool | None = None
    exhaust_fan_on: bool | None = None
    pre_heating_on: bool | None = None
    fireplace_booster_on: bool | None = None
    damper_motor_position: bool | None = None  # True = bypass active

    # Setpoints (°C)
    heating_setpoint: int | None = None
    preheating_setpoint: int | None = None
    bypass_setpoint: int | None = None
    cell_defrost_setpoint: int | None = None
    input_fan_stop_threshold: int | None = None

    # Fault
    last_fault: str | None = None
    fault_signal: bool | None = None

    # Service
    service_reminder_months: int | None = None
    service_reminder_active: bool | None = None

    # Post heating
    post_heating_on_counter: int | None = None
    post_heating_off_time: int | None = None
    post_heating_target: int | None = None

    # Fireplace
    fireplace_countdown_minutes: int | None = None

    # DC Fan adjustment (%)
    dc_fan_input_adjustment: int | None = None
    dc_fan_output_adjustment: int | None = None

    # Raw register values for debugging
    _raw_values: dict[int, int] = field(default_factory=dict)

    def update_co2_ppm(self) -> None:
        """Calculate CO2 ppm from high and low bytes."""
        if self.co2_high is not None and self.co2_low is not None:
            self.co2_ppm = (self.co2_high << 8) | self.co2_low


def ntc_to_celsius(value: int) -> int:
    """Convert NTC sensor value to Celsius."""
    if 0 <= value <= 255:
        return NTC_TO_CELSIUS[value]
    return 0


def celsius_to_ntc(temp: int) -> int:
    """Convert Celsius to NTC sensor value."""
    temp = max(-74, min(100, temp))
    return CELSIUS_TO_NTC.get(temp, 100)


def decode_fan_speed(value: int) -> int:
    """Decode fan speed byte to level 1-8."""
    if value in HEX_TO_FAN_SPEED:
        return HEX_TO_FAN_SPEED[value]
    for level in range(8, 0, -1):
        if value & (1 << (level - 1)):
            return level
    return 1


def encode_fan_speed(level: int) -> int:
    """Encode fan speed level 1-8 to byte value."""
    level = max(1, min(8, level))
    return FAN_SPEED_TO_HEX[level]


def decode_humidity(value: int) -> int:
    """Decode humidity sensor value to percentage."""
    if value <= 51:
        return 0
    result = (value - 51) / 2.04
    return max(0, min(100, int(round(result))))


def encode_humidity(percent: int) -> int:
    """Encode humidity percentage to bus value."""
    percent = max(0, min(100, percent))
    return int(round(percent * 2.04 + 51))


def decode_fault(value: int) -> str:
    """Decode fault code to string."""
    return FAULT_CODES.get(value, f"unknown_fault_{value:02x}")


def decode_cell_defrost(value: int) -> int:
    """Decode cell defrost setpoint (value * 3 = °C)."""
    return value // 3


def encode_cell_defrost(temp: int) -> int:
    """Encode cell defrost setpoint (°C * 3 = value)."""
    temp = max(0, min(10, temp))
    return temp * 3


def decode_co2_setpoint(upper: int, lower: int) -> int:
    """Decode CO2 setpoint from two bytes to ppm."""
    return (upper << 8) | lower


def encode_co2_setpoint(ppm: int) -> tuple[int, int]:
    """Encode CO2 setpoint ppm to two bytes (upper, lower)."""
    ppm = max(500, min(2000, ppm))
    return (ppm >> 8) & 0xFF, ppm & 0xFF


def validate_fan_speed(speed: int) -> int:
    """Validate and clamp fan speed to valid range."""
    return max(VALID_FAN_SPEED_RANGE[0], min(VALID_FAN_SPEED_RANGE[1], speed))


def validate_temperature_setpoint(temp: int) -> int:
    """Validate and clamp temperature setpoint to valid range."""
    return max(VALID_TEMPERATURE_SETPOINT_RANGE[0],
               min(VALID_TEMPERATURE_SETPOINT_RANGE[1], temp))


def validate_humidity(humidity: int) -> int:
    """Validate and clamp humidity to valid range."""
    return max(VALID_HUMIDITY_RANGE[0], min(VALID_HUMIDITY_RANGE[1], humidity))


def validate_co2_setpoint(ppm: int) -> int:
    """Validate and clamp CO2 setpoint to valid range (500-2000)."""
    return max(500, min(2000, ppm))


def validate_service_months(months: int) -> int:
    """Validate and clamp service reminder months."""
    return max(VALID_SERVICE_MONTHS_RANGE[0],
               min(VALID_SERVICE_MONTHS_RANGE[1], months))


def create_read_request(register: int) -> ValloxTelegram:
    """Create a read request telegram."""
    return ValloxTelegram(
        domain=VALLOX_DOMAIN,
        sender=ADDR_THIS_DEVICE,
        receiver=ADDR_MAINBOARD,
        register=register,
        value=0x00,
    )


def create_write_request(
    register: int, value: int, sender: int = ADDR_THIS_DEVICE
) -> ValloxTelegram:
    """Create a write request telegram."""
    return ValloxTelegram(
        domain=VALLOX_DOMAIN,
        sender=sender,
        receiver=ADDR_MAINBOARD,
        register=register,
        value=value & 0xFF,
    )
