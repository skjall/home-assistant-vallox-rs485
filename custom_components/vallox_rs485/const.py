"""What this integration adds on top of the wire protocol.

The protocol itself lives in the vallox-rs485-protocol package, pinned in
manifest.json. Its names are re-exported here so the platforms keep one
place to import from, and so a package version is swapped in one file
rather than twenty.
"""

from typing import Final

from vallox_rs485_protocol import (
    ADDR_MAINBOARD,
    ADDR_MAINBOARDS_BROADCAST,
    ADDR_PANEL,
    ADDR_PANELS_BROADCAST,
    ADDR_THIS_DEVICE,
    BIT_CO2_ADJUST,
    BIT_DAMPER_MOTOR,
    BIT_EXHAUST_FAN,
    BIT_FAULT_INDICATOR,
    BIT_FAULT_SIGNAL,
    BIT_FILTER_GUARD,
    BIT_FIREPLACE_BOOST_ACTIVE,
    BIT_FIREPLACE_BOOSTER,
    BIT_FIREPLACE_SWITCH_ACTIVATE,
    BIT_HEATING_INDICATOR,
    BIT_HEATING_STATE,
    BIT_POWER_STATE,
    BIT_PRE_HEATING,
    BIT_REMOTE_CONTROL_WORKING,
    BIT_RH_ADJUST,
    BIT_SERVICE_REMINDER,
    BIT_SUPPLY_FAN,
    CELSIUS_TO_NTC,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    FAN_SPEED_TO_HEX,
    FAULT_CODES,
    HEX_TO_FAN_SPEED,
    NTC_TO_CELSIUS,
    REG_BASIC_HUMIDITY_LEVEL,
    REG_BYPASS_SETPOINT,
    REG_CELL_DEFROST_SETPOINT,
    REG_CO2_HIGH,
    REG_CO2_LOW,
    REG_CO2_SENSORS_INSTALLED,
    REG_CO2_SETPOINT_LOWER,
    REG_CO2_SETPOINT_UPPER,
    REG_CURRENT_VOLTAGE,
    REG_DC_FAN_INPUT_ADJ,
    REG_DC_FAN_OUTPUT_ADJ,
    REG_FAN_SPEED,
    REG_FAN_SPEED_MAX,
    REG_FAN_SPEED_MIN,
    REG_FAN_SPEED_RELAYS,
    REG_FIREPLACE_COUNTDOWN,
    REG_FLAGS_2,
    REG_FLAGS_4,
    REG_FLAGS_5,
    REG_FLAGS_6,
    REG_HEATING_SETPOINT,
    REG_HUMIDITY,
    REG_HUMIDITY_SENSOR1,
    REG_HUMIDITY_SENSOR2,
    REG_INPUT_FAN_STOP_THRESHOLD,
    REG_LAST_FAULT,
    REG_MULTI_PURPOSE_1,
    REG_MULTI_PURPOSE_2,
    REG_POST_HEATING_OFF_TIME,
    REG_POST_HEATING_ON_CNT,
    REG_POST_HEATING_TARGET,
    REG_PREHEATING_SETPOINT,
    REG_PROGRAM,
    REG_PROGRAM_2,
    REG_SELECT,
    REG_SERVICE_REMINDER,
    REG_TEMP_EXHAUST,
    REG_TEMP_EXHAUST_LEGACY,
    REG_TEMP_INCOMING,
    REG_TEMP_INCOMING_LEGACY,
    REG_TEMP_INSIDE,
    REG_TEMP_INSIDE_LEGACY,
    REG_TEMP_OUTSIDE,
    REG_TEMP_OUTSIDE_LEGACY,
    TELEGRAM_LENGTH,
    VALID_CO2_RANGE,
    VALID_FAN_SPEED_RANGE,
    VALID_HUMIDITY_RANGE,
    VALID_SERVICE_MONTHS_RANGE,
    VALID_TEMPERATURE_SETPOINT_RANGE,
    VALLOX_DOMAIN,
    ValloxState,
    ValloxTelegram,
    celsius_to_ntc,
    create_read_request,
    create_write_request,
    decode_cell_defrost,
    decode_co2_setpoint,
    decode_fan_speed,
    decode_fault,
    decode_humidity,
    encode_cell_defrost,
    encode_co2_setpoint,
    encode_fan_speed,
    encode_humidity,
    ntc_to_celsius,
    validate_co2_setpoint,
    validate_fan_speed,
    validate_humidity,
    validate_service_months,
    validate_temperature_setpoint,
)

# Re-exported on purpose: without this the names below are unused imports.
__all__ = [
    "ADDR_MAINBOARD",
    "ADDR_MAINBOARDS_BROADCAST",
    "ADDR_PANEL",
    "ADDR_PANELS_BROADCAST",
    "ADDR_THIS_DEVICE",
    "BIT_CO2_ADJUST",
    "BIT_DAMPER_MOTOR",
    "BIT_EXHAUST_FAN",
    "BIT_FAULT_INDICATOR",
    "BIT_FAULT_SIGNAL",
    "BIT_FILTER_GUARD",
    "BIT_FIREPLACE_BOOSTER",
    "BIT_FIREPLACE_BOOST_ACTIVE",
    "BIT_FIREPLACE_SWITCH_ACTIVATE",
    "BIT_HEATING_INDICATOR",
    "BIT_HEATING_STATE",
    "BIT_POWER_STATE",
    "BIT_PRE_HEATING",
    "BIT_REMOTE_CONTROL_WORKING",
    "BIT_RH_ADJUST",
    "BIT_SERVICE_REMINDER",
    "BIT_SUPPLY_FAN",
    "CELSIUS_TO_NTC",
    "DEFAULT_BAUDRATE",
    "DEFAULT_BYTESIZE",
    "DEFAULT_DEVICE_ADDRESS",
    "DEFAULT_PARITY",
    "DEFAULT_SCAN_INTERVAL",
    "DEFAULT_STOPBITS",
    "DOMAIN",
    "FAN_SPEED_TO_HEX",
    "FAULT_CODES",
    "HEX_TO_FAN_SPEED",
    "NTC_TO_CELSIUS",
    "REG_BASIC_HUMIDITY_LEVEL",
    "REG_BYPASS_SETPOINT",
    "REG_CELL_DEFROST_SETPOINT",
    "REG_CO2_HIGH",
    "REG_CO2_LOW",
    "REG_CO2_SENSORS_INSTALLED",
    "REG_CO2_SETPOINT_LOWER",
    "REG_CO2_SETPOINT_UPPER",
    "REG_CURRENT_VOLTAGE",
    "REG_DC_FAN_INPUT_ADJ",
    "REG_DC_FAN_OUTPUT_ADJ",
    "REG_FAN_SPEED",
    "REG_FAN_SPEED_MAX",
    "REG_FAN_SPEED_MIN",
    "REG_FAN_SPEED_RELAYS",
    "REG_FIREPLACE_COUNTDOWN",
    "REG_FLAGS_2",
    "REG_FLAGS_4",
    "REG_FLAGS_5",
    "REG_FLAGS_6",
    "REG_HEATING_SETPOINT",
    "REG_HUMIDITY",
    "REG_HUMIDITY_SENSOR1",
    "REG_HUMIDITY_SENSOR2",
    "REG_INPUT_FAN_STOP_THRESHOLD",
    "REG_LAST_FAULT",
    "REG_MULTI_PURPOSE_1",
    "REG_MULTI_PURPOSE_2",
    "REG_POST_HEATING_OFF_TIME",
    "REG_POST_HEATING_ON_CNT",
    "REG_POST_HEATING_TARGET",
    "REG_PREHEATING_SETPOINT",
    "REG_PROGRAM",
    "REG_PROGRAM_2",
    "REG_SELECT",
    "REG_SERVICE_REMINDER",
    "REG_TEMP_EXHAUST",
    "REG_TEMP_EXHAUST_LEGACY",
    "REG_TEMP_INCOMING",
    "REG_TEMP_INCOMING_LEGACY",
    "REG_TEMP_INSIDE",
    "REG_TEMP_INSIDE_LEGACY",
    "REG_TEMP_OUTSIDE",
    "REG_TEMP_OUTSIDE_LEGACY",
    "REQ_BYPASS_SETPOINT",
    "REQ_CELL_DEFROST",
    "REQ_CO2",
    "REQ_CO2_SETPOINT",
    "REQ_FAN_SPEED",
    "REQ_FAN_SPEED_MAX",
    "REQ_FAN_SPEED_MIN",
    "REQ_FIREPLACE_COUNTDOWN",
    "REQ_FLAGS_6",
    "REQ_HEATING_SETPOINT",
    "REQ_HUMIDITY",
    "REQ_HUMIDITY_LEVEL",
    "REQ_HUMIDITY_SENSOR1",
    "REQ_HUMIDITY_SENSOR2",
    "REQ_INPUT_FAN_STOP",
    "REQ_LAST_FAULT",
    "REQ_MULTI_PURPOSE_2",
    "REQ_POST_HEATING_CNT",
    "REQ_PREHEATING_SETPOINT",
    "REQ_SELECT",
    "REQ_SERVICE_REMINDER",
    "REQ_TEMP_EXHAUST",
    "REQ_TEMP_INCOMING",
    "REQ_TEMP_INSIDE",
    "REQ_TEMP_OUTSIDE",
    "TELEGRAM_LENGTH",
    "VALID_CO2_RANGE",
    "VALID_FAN_SPEED_RANGE",
    "VALID_HUMIDITY_RANGE",
    "VALID_SERVICE_MONTHS_RANGE",
    "VALID_TEMPERATURE_SETPOINT_RANGE",
    "VALLOX_DOMAIN",
    "ValloxState",
    "ValloxTelegram",
    "celsius_to_ntc",
    "create_read_request",
    "create_write_request",
    "decode_cell_defrost",
    "decode_co2_setpoint",
    "decode_fan_speed",
    "decode_fault",
    "decode_humidity",
    "encode_cell_defrost",
    "encode_co2_setpoint",
    "encode_fan_speed",
    "encode_humidity",
    "ntc_to_celsius",
    "validate_co2_setpoint",
    "validate_fan_speed",
    "validate_humidity",
    "validate_service_months",
    "validate_temperature_setpoint",
]

DOMAIN: Final = "vallox_rs485"
DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_DEVICE_ADDRESS: Final = 0x2E

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
