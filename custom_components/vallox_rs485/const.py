"""Constants for Vallox RS485 integration."""
from typing import Any, Final

from homeassistant.helpers.device_registry import DeviceInfo

DOMAIN: Final = "vallox_rs485"

# Serial settings
DEFAULT_BAUDRATE: Final = 9600
DEFAULT_BYTESIZE: Final = 8
DEFAULT_PARITY: Final = "N"
DEFAULT_STOPBITS: Final = 1

# Protocol constants
VALLOX_DOMAIN: Final = 0x01
ADDR_MAINBOARD: Final = 0x11
ADDR_MAINBOARDS_BROADCAST: Final = 0x10
ADDR_PANEL: Final = 0x21
ADDR_PANELS_BROADCAST: Final = 0x20
ADDR_THIS_DEVICE: Final = 0x22

# Polling
DEFAULT_SCAN_INTERVAL: Final = 30

# Default device address for this integration (configurable)
# 0x2E chosen to avoid conflicts with panel addresses (0x21-0x2F range)
DEFAULT_DEVICE_ADDRESS: Final = 0x2E

# Register addresses (from FHEM 36_Vallox.pm)
REG_FAN_SPEED: Final = 0x29
REG_HUMIDITY: Final = 0x2A
REG_CO2_HIGH: Final = 0x2B
REG_CO2_LOW: Final = 0x2C
REG_CO2_SENSORS_INSTALLED: Final = 0x2D
REG_CURRENT_VOLTAGE: Final = 0x2E
REG_HUMIDITY_SENSOR1: Final = 0x2F
REG_HUMIDITY_SENSOR2: Final = 0x30

# Temperature registers (new protocol)
REG_TEMP_OUTSIDE: Final = 0x32
REG_TEMP_EXHAUST: Final = 0x33
REG_TEMP_INSIDE: Final = 0x34
REG_TEMP_INCOMING: Final = 0x35

# Temperature registers (legacy protocol)
REG_TEMP_OUTSIDE_LEGACY: Final = 0x58
REG_TEMP_INSIDE_LEGACY: Final = 0x5A
REG_TEMP_INCOMING_LEGACY: Final = 0x5B
REG_TEMP_EXHAUST_LEGACY: Final = 0x5C

REG_LAST_FAULT: Final = 0x36
REG_POST_HEATING_ON_CNT: Final = 0x55
REG_POST_HEATING_OFF_TIME: Final = 0x56
REG_POST_HEATING_TARGET: Final = 0x57
REG_FIREPLACE_COUNTDOWN: Final = 0x79

# Multi-purpose registers
REG_FAN_SPEED_RELAYS: Final = 0x06
REG_MULTI_PURPOSE_1: Final = 0x07
REG_MULTI_PURPOSE_2: Final = 0x08

# Flags registers
REG_FLAGS_2: Final = 0x6D
REG_FLAGS_4: Final = 0x6F
REG_FLAGS_5: Final = 0x70
REG_FLAGS_6: Final = 0x71

# Control registers
REG_SELECT: Final = 0xA3
REG_HEATING_SETPOINT: Final = 0xA4
REG_FAN_SPEED_MAX: Final = 0xA5
REG_SERVICE_REMINDER: Final = 0xA6
REG_PREHEATING_SETPOINT: Final = 0xA7
REG_INPUT_FAN_STOP_THRESHOLD: Final = 0xA8
REG_FAN_SPEED_MIN: Final = 0xA9
REG_PROGRAM: Final = 0xAA
REG_BASIC_HUMIDITY_LEVEL: Final = 0xAE
REG_BYPASS_SETPOINT: Final = 0xAF
REG_DC_FAN_INPUT_ADJ: Final = 0xB0
REG_DC_FAN_OUTPUT_ADJ: Final = 0xB1
REG_CELL_DEFROST_SETPOINT: Final = 0xB2
REG_CO2_SETPOINT_UPPER: Final = 0xB3
REG_CO2_SETPOINT_LOWER: Final = 0xB4
REG_PROGRAM_2: Final = 0xB5

# Select register (0xA3) bit positions
BIT_POWER_STATE: Final = 0
BIT_CO2_ADJUST: Final = 1
BIT_RH_ADJUST: Final = 2
BIT_HEATING_STATE: Final = 3
BIT_FILTER_GUARD: Final = 4
BIT_HEATING_INDICATOR: Final = 5
BIT_FAULT_INDICATOR: Final = 6
BIT_SERVICE_REMINDER: Final = 7

# Multi-purpose 2 (0x08) bit positions
BIT_DAMPER_MOTOR: Final = 1
BIT_FAULT_SIGNAL: Final = 2
BIT_SUPPLY_FAN: Final = 3
BIT_PRE_HEATING: Final = 4
BIT_EXHAUST_FAN: Final = 5
BIT_FIREPLACE_BOOSTER: Final = 6

# FLAGS 6 (0x71) bit positions
BIT_REMOTE_CONTROL_WORKING: Final = 4  # read-only
BIT_FIREPLACE_SWITCH_ACTIVATE: Final = 5  # read, then set to 1 to activate
BIT_FIREPLACE_BOOST_ACTIVE: Final = 6  # read-only

# Fan speed encoding (level 1-8 -> hex value)
FAN_SPEED_TO_HEX: Final = {
    1: 0x01,
    2: 0x03,
    3: 0x07,
    4: 0x0F,
    5: 0x1F,
    6: 0x3F,
    7: 0x7F,
    8: 0xFF,
}

# Fan speed decoding (hex value -> level 1-8)
HEX_TO_FAN_SPEED: Final = {v: k for k, v in FAN_SPEED_TO_HEX.items()}

# NTC Temperature conversion table (index 0-255 -> temperature in °C)
NTC_TO_CELSIUS: Final = [
    -74, -70, -66, -62, -59, -56, -54, -52, -50, -48, -47, -46, -44, -43, -42, -41,
    -40, -39, -38, -37, -36, -35, -34, -33, -33, -32, -31, -30, -30, -29, -28, -28,
    -27, -27, -26, -25, -25, -24, -24, -23, -23, -22, -22, -21, -21, -20, -20, -19,
    -19, -19, -18, -18, -17, -17, -16, -16, -16, -15, -15, -14, -14, -14, -13, -13,
    -12, -12, -12, -11, -11, -11, -10, -10, -9, -9, -9, -8, -8, -8, -7, -7,
    -7, -6, -6, -6, -5, -5, -5, -4, -4, -4, -3, -3, -3, -2, -2, -2,
    -1, -1, -1, -1, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3,
    4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8,
    9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 12, 13, 13, 13, 14,
    14, 14, 15, 15, 15, 16, 16, 16, 17, 17, 18, 18, 18, 19, 19, 19,
    20, 20, 21, 21, 21, 22, 22, 22, 23, 23, 24, 24, 24, 25, 25, 26,
    26, 27, 27, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 32, 33, 33,
    34, 34, 35, 35, 36, 36, 37, 37, 38, 38, 39, 40, 40, 41, 41, 42,
    43, 43, 44, 45, 45, 46, 47, 48, 48, 49, 50, 51, 52, 53, 53, 54,
    55, 56, 57, 59, 60, 61, 62, 63, 65, 66, 68, 69, 71, 73, 75, 77,
    79, 81, 82, 86, 90, 93, 97, 100, 100, 100, 100, 100, 100, 100, 100, 100,
]

# Reverse lookup: Celsius -> NTC value (for setpoints)
# We build this by finding the first occurrence of each temperature
CELSIUS_TO_NTC: Final = {}
for ntc_val, temp in enumerate(NTC_TO_CELSIUS):
    if temp not in CELSIUS_TO_NTC:
        CELSIUS_TO_NTC[temp] = ntc_val

# Fault codes
FAULT_CODES: Final = {
    0x00: "no_fault",
    0x05: "supply_air_sensor_fault",
    0x06: "co2_alarm",
    0x07: "outdoor_air_sensor_fault",
    0x08: "extract_air_sensor_fault",
    0x09: "water_radiator_freezing",
    0x0A: "exhaust_air_sensor_fault",
}

# Register requirements for lazy entity creation
# Entities only created when required registers are seen on the bus

# Temperature sensors (accept both new and legacy registers)
REQ_TEMP_OUTSIDE: Final = (REG_TEMP_OUTSIDE, REG_TEMP_OUTSIDE_LEGACY)
REQ_TEMP_EXHAUST: Final = (REG_TEMP_EXHAUST, REG_TEMP_EXHAUST_LEGACY)
REQ_TEMP_INSIDE: Final = (REG_TEMP_INSIDE, REG_TEMP_INSIDE_LEGACY)
REQ_TEMP_INCOMING: Final = (REG_TEMP_INCOMING, REG_TEMP_INCOMING_LEGACY)

# Humidity sensors
REQ_HUMIDITY: Final = (REG_HUMIDITY,)
REQ_HUMIDITY_SENSOR1: Final = (REG_HUMIDITY_SENSOR1,)
REQ_HUMIDITY_SENSOR2: Final = (REG_HUMIDITY_SENSOR2,)

# CO2 (requires both high and low bytes)
REQ_CO2: Final = (REG_CO2_HIGH, REG_CO2_LOW)

# Fan
REQ_FAN_SPEED: Final = (REG_FAN_SPEED,)
REQ_FAN_SPEED_MIN: Final = (REG_FAN_SPEED_MIN,)
REQ_FAN_SPEED_MAX: Final = (REG_FAN_SPEED_MAX,)

# Control register (switches, some binary sensors)
REQ_SELECT: Final = (REG_SELECT,)

# Multi-purpose 2 (binary sensors)
REQ_MULTI_PURPOSE_2: Final = (REG_MULTI_PURPOSE_2,)

# FLAGS 6 (fireplace/boost status)
REQ_FLAGS_6: Final = (REG_FLAGS_6,)

# Temperature setpoints
REQ_HEATING_SETPOINT: Final = (REG_HEATING_SETPOINT,)
REQ_PREHEATING_SETPOINT: Final = (REG_PREHEATING_SETPOINT,)
REQ_BYPASS_SETPOINT: Final = (REG_BYPASS_SETPOINT,)
REQ_INPUT_FAN_STOP: Final = (REG_INPUT_FAN_STOP_THRESHOLD,)
REQ_CELL_DEFROST: Final = (REG_CELL_DEFROST_SETPOINT,)

# Service and counters
REQ_SERVICE_REMINDER: Final = (REG_SERVICE_REMINDER,)
REQ_LAST_FAULT: Final = (REG_LAST_FAULT,)
REQ_POST_HEATING_CNT: Final = (REG_POST_HEATING_ON_CNT,)
REQ_FIREPLACE_COUNTDOWN: Final = (REG_FIREPLACE_COUNTDOWN,)

# CO2 and humidity setpoints
REQ_CO2_SETPOINT: Final = (REG_CO2_SETPOINT_UPPER, REG_CO2_SETPOINT_LOWER)
REQ_HUMIDITY_LEVEL: Final = (REG_BASIC_HUMIDITY_LEVEL,)


def get_device_info(entry_id: str, title: str) -> DeviceInfo:
    """Create device info dict for entities."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name=title,
        manufacturer="Vallox",
        model="RS485",
    )
