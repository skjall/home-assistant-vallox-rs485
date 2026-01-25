# Vallox RS485 Protocol Reference

This document describes the RS485 protocol used by Vallox "Digit SE" series ventilation systems.

Based on the [FHEM Vallox module](https://wiki.fhem.de/wiki/Vallox) and [Vallox Digit Protocol PDF](https://wiki.fhem.de/wiki/Datei:Digit_protocol_english_RS485.pdf).

## Overview

The Vallox RS485 bus allows communication between the main ventilation unit and control panels. This integration acts as a virtual control panel on the bus.

**Compatible Systems:**
- Vallox Digit SE series
- Helios KWL EC/ET series

## Serial Settings

| Parameter | Value |
|-----------|-------|
| Baud rate | 9600 |
| Data bits | 8 |
| Parity | None |
| Stop bits | 1 |

## Telegram Format

All communication uses 6-byte telegrams:

```
┌────────┬────────┬──────────┬──────────┬───────┬──────────┐
│ Domain │ Sender │ Receiver │ Register │ Value │ Checksum │
│  1 byte│ 1 byte │  1 byte  │  1 byte  │1 byte │  1 byte  │
└────────┴────────┴──────────┴──────────┴───────┴──────────┘
```

**Checksum calculation:**
```
Checksum = (Domain + Sender + Receiver + Register + Value) mod 256
```

## Device Addresses

### Address Ranges

| Device Type | Address Range | Broadcast |
|-------------|---------------|-----------|
| Ventilation units | 0x11 - 0x1F | 0x10 |
| Control panels | 0x21 - 0x2F | 0x20 |

### Default Addresses

| Device | Address | Description |
|--------|---------|-------------|
| 0x01 | Domain | Default domain (system ID) |
| 0x11 | Main unit | Primary ventilation unit |
| 0x21 | Panel | Built-in control panel |
| 0x22 | Integration | This Home Assistant integration |

**Domain:** Used to separate multiple systems on the same bus (e.g., multi-unit buildings). Default is 0x01.

## Registers

### Temperature Sensors (Read-only)

| Register | Name | Description | Conversion |
|----------|------|-------------|------------|
| 0x32 | TempOutside | Outdoor air temperature | NTC Table |
| 0x33 | TempExhaust | Exhaust air (after heat exchanger) | NTC Table |
| 0x34 | TempInside | Indoor extract air | NTC Table |
| 0x35 | TempIncoming | Supply air (after heat exchanger) | NTC Table |

### Fan Control

| Register | Name | Description | Range | Conversion |
|----------|------|-------------|-------|------------|
| 0x29 | FanSpeed | Current fan speed | 1-8 | Fan Speed Map |
| 0xA5 | FanSpeedMax | Maximum allowed speed | 1-8 | Fan Speed Map |
| 0xA9 | FanSpeedMin | Minimum allowed speed | 1-8 | Fan Speed Map |

### Humidity

| Register | Name | Description | Conversion |
|----------|------|-------------|------------|
| 0x2A | Humidity | Main humidity sensor | Humidity Formula |
| 0xAE | BasicHumidityLevel | Manual humidity threshold | Percent Map |

### CO2

| Register | Name | Description | Conversion |
|----------|------|-------------|------------|
| 0x2B | CO2High | CO2 value high byte | Combined |
| 0x2C | CO2Low | CO2 value low byte | Combined |
| 0xB3 | CO2SetPointUpper | CO2 threshold high byte | Combined |
| 0xB4 | CO2SetPointLower | CO2 threshold low byte | Combined |

**CO2 calculation:** `CO2_ppm = (CO2High << 8) | CO2Low`

### System Control

| Register | Name | Description | Range |
|----------|------|-------------|-------|
| 0xA3 | Select | Multi-purpose control register | Bitmask |
| 0xA4 | HeatingSetPoint | Heating temperature target | 10-30°C |
| 0xA6 | ServiceReminderMonths | Service interval | 1-15 months |
| 0xA7 | PreheatingSetPoint | Pre-heater setpoint | -6 to 15°C |
| 0xA8 | InputFanStopTemp | Frost protection threshold | -6 to 15°C |
| 0xAF | BypassSetPoint | Bypass activation temp | 0-20°C |

### Status Registers (Read-only)

| Register | Name | Description |
|----------|------|-------------|
| 0x36 | LastSystemFault | Last stored error code |
| 0x6C | MultiPurpose1 | Status flags (post-heating, etc.) |
| 0x6D | MultiPurpose2 | Status flags (bypass position, etc.) |

### DC Fan Adjustment

| Register | Name | Description | Range |
|----------|------|-------------|-------|
| 0xB0 | DCFanInputAdjustment | DC supply fan scaling | 0-100% |
| 0xB1 | DCFanOutputAdjustment | DC exhaust fan scaling | 0-100% |

### Heat Recovery

| Register | Name | Description | Range |
|----------|------|-------------|-------|
| 0xAF | HeatRecoveryCellBypassSetPoint | Bypass activation temperature | 0-20°C |
| 0xB2 | CellDefrostingSetPoint | Defrost hysteresis | 0-10°C |

## Value Conversion Methods

### NTC Temperature Table (TM)

Temperature values use a 256-entry NTC lookup table. The bus value (0x00-0xFF) maps to temperatures from -74°C to +100°C.

**Key values:**
| Bus Value | Temperature |
|-----------|-------------|
| 0x00 | -74°C |
| 0x33 | 0°C |
| 0x6D | 20°C |
| 0xFF | +100°C |

### Fan Speed Map (FSM)

Fan speed uses bit-encoded values:

| Speed | Bus Value | Binary |
|-------|-----------|--------|
| 1 | 0x01 | 00000001 |
| 2 | 0x03 | 00000011 |
| 3 | 0x07 | 00000111 |
| 4 | 0x0F | 00001111 |
| 5 | 0x1F | 00011111 |
| 6 | 0x3F | 00111111 |
| 7 | 0x7F | 01111111 |
| 8 | 0xFF | 11111111 |

**Formula:** `bus_value = (1 << speed) - 1`

### Humidity Formula (HF)

```
humidity_percent = (bus_value - 51) / 2.04
bus_value = (humidity_percent * 2.04) + 51
```

### Decimal Function (DF)

Direct decimal to hex conversion without transformation.

### Binary Mapping (BM)

Single bit values: 0 = Off, 1 = On

### Percent Mapping (PCTM)

Percentage values mapped to bus range.

### Cell Defrosting Function (CDSTF)

```
bus_value = temperature_celsius * 3
```

## Select Register (0xA3) Bitmask

The Select register contains multiple control flags:

| Bit | Name | Description |
|-----|------|-------------|
| 0 | PowerState | 0=Off, 1=On |
| 1 | CO2AdjustState | CO2-based speed adjustment |
| 2 | RHAdjustState | Humidity-based speed adjustment |
| 3 | HeatingState | Post-heating enabled |
| 4 | FilterGuardIndicator | Filter needs cleaning |
| 5 | HeatingIndicator | Heating currently active |
| 6 | FaultIndicator | Fault present |
| 7 | ServiceReminderIndicator | Service due |

## Fault Codes

| Code | Description |
|------|-------------|
| 0x00 | No fault |
| 0x01 | Supply fan fault |
| 0x02 | Exhaust fan fault |
| 0x03 | Supply/exhaust fault |
| 0x04 | Water radiator frost alarm |
| 0x05 | Electric heater frost alarm |
| 0x06 | CO2 sensor fault |
| 0x07 | Outdoor temp sensor fault |
| 0x08 | Exhaust temp sensor fault |
| 0x09 | Water radiator sensor fault |

## Example Telegrams

### Read fan speed from main unit
```
Request:  01 22 11 29 00 5D
          │  │  │  │  │  └─ Checksum
          │  │  │  │  └──── Value (ignored for read)
          │  │  │  └─────── Register (FanSpeed)
          │  │  └────────── Receiver (Main unit)
          │  └───────────── Sender (Integration)
          └──────────────── Domain

Response: 01 11 22 29 07 64
          │  │  │  │  │  └─ Checksum
          │  │  │  │  └──── Value (0x07 = Speed 3)
          │  │  │  └─────── Register (FanSpeed)
          │  │  └────────── Receiver (Integration)
          │  └───────────── Sender (Main unit)
          └──────────────── Domain
```

### Set fan speed to level 5
```
Command:  01 22 11 29 1F 7C
          │  │  │  │  │  └─ Checksum
          │  │  │  │  └──── Value (0x1F = Speed 5)
          │  │  │  └─────── Register (FanSpeed)
          │  │  └────────── Receiver (Main unit)
          │  └───────────── Sender (Integration)
          └──────────────── Domain
```

### Broadcast temperature reading (passive)
```
Telegram: 01 11 20 58 6D 07
          │  │  │  │  │  └─ Checksum
          │  │  │  │  └──── Value (NTC: ~20°C)
          │  │  │  └─────── Register (TempOutside)
          │  │  └────────── Receiver (Panel broadcast)
          │  └───────────── Sender (Main unit)
          └──────────────── Domain
```

## Bus Behavior

### Passive Monitoring

The main unit periodically broadcasts sensor values to all panels. This integration primarily listens to these broadcasts to avoid bus congestion.

**Broadcast interval:** ~1-5 seconds per register

### Active Requests

For values not regularly broadcast, the integration can send read requests. However, excessive polling should be avoided.

### Write Commands

Write operations are sent directly to the main unit (0x11). The main unit does not acknowledge writes, so verification must be done by reading back the value.

## References

- [FHEM Vallox Wiki](https://wiki.fhem.de/wiki/Vallox)
- [Vallox Digit Protocol PDF](https://wiki.fhem.de/wiki/Datei:Digit_protocol_english_RS485.pdf)
