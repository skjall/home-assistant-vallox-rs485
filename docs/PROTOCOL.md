# Vallox RS485 Protocol Reference

Based on the official Vallox DIGIT bus protocol documentation (Vallox/Petteri Kähärä, 27.06.2011).

## Overview

The Vallox RS485 bus uses a twisted pair for communication between modules. RS485 allows up to 32 modules, each with transmitter and receiver.

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
┌────────┬────────┬───────────┬──────────┬───────┬──────────┐
│ SYSTEM │ SENDER │ RECIPIENT │ VARIABLE │ DATA  │ CHECKSUM │
│ 1 byte │ 1 byte │  1 byte   │  1 byte  │1 byte │  1 byte  │
└────────┴────────┴───────────┴──────────┴───────┴──────────┘
```

**Fields:**
- **SYSTEM**: System isolation for multiple systems on same bus. Always 0x01.
- **SENDER**: Source module address
- **RECIPIENT**: Destination module address
- **VARIABLE**: Register address (or 0x00 for read requests)
- **DATA**: Register value (or register to read for read requests)
- **CHECKSUM**: `(SYSTEM + SENDER + RECIPIENT + VARIABLE + DATA) & 0xFF`

## Device Addresses

| Device Type | Address Range | Broadcast |
|-------------|---------------|-----------|
| Mainboards | 0x11 - 0x1F | 0x10 |
| Remote controls | 0x21 - 0x2F | 0x20 |

**Common Addresses:**
| Address | Description |
|---------|-------------|
| 0x01 | System/Domain (always 0x01) |
| 0x10 | Broadcast to all mainboards |
| 0x11 | Master mainboard |
| 0x20 | Broadcast to all panels |
| 0x21 | Built-in control panel |
| 0x22 | This integration (default) |

## Communication Principles

### Read Request (Request/Response)

To read a register, send `VARIABLE=0x00` with `DATA=<register to read>`:

```
Request:  01 22 11 00 A3 D7
          │  │  │  │  │  └─ Checksum
          │  │  │  │  └──── DATA: Register to read (0xA3 = SELECT)
          │  │  │  └─────── VARIABLE: 0x00 = Read request
          │  │  └────────── RECIPIENT: 0x11 (Mainboard)
          │  └───────────── SENDER: 0x22 (Integration)
          └──────────────── SYSTEM: 0x01

Response: 01 11 22 A3 01 D8
          │  │  │  │  │  └─ Checksum
          │  │  │  │  └──── DATA: Value (0x01)
          │  │  │  └─────── VARIABLE: Register (0xA3)
          │  │  └────────── RECIPIENT: 0x22 (Integration)
          │  └───────────── SENDER: 0x11 (Mainboard)
          └──────────────── SYSTEM: 0x01
```

Timeout: 10ms. Retry up to 10 times before fault mode.

### Write Request (Send/Acknowledge)

To write a register, send `VARIABLE=<register>` with `DATA=<value>`:

```
Command:  01 22 11 29 1F 7C
          │  │  │  │  │  └─ Checksum
          │  │  │  │  └──── DATA: Value (0x1F = Speed 5)
          │  │  │  └─────── VARIABLE: Register (0x29 = FanSpeed)
          │  │  └────────── RECIPIENT: 0x11 (Mainboard)
          │  └───────────── SENDER: 0x22 (Integration)
          └──────────────── SYSTEM: 0x01

Acknowledge: Recipient sends back the checksum
```

### Broadcast (Unacknowledged)

The mainboard broadcasts sensor values to all panels (0x20) every ~12 seconds:

```
Broadcast: 01 11 20 35 A7 0E
           │  │  │  │  │  └─ Checksum
           │  │  │  │  └──── DATA: Value (NTC: ~22°C)
           │  │  │  └─────── VARIABLE: Register (0x35 = TempIncoming)
           │  │  └────────── RECIPIENT: 0x20 (All panels)
           │  └───────────── SENDER: 0x11 (Mainboard)
           └──────────────── SYSTEM: 0x01
```

**Broadcast registers:** 0x2A, 0x2B, 0x2C, 0x32, 0x33, 0x34, 0x35

## Registers

### Temperature Sensors (Read-only)

| Register | Name | Description |
|----------|------|-------------|
| 0x32 | TempOutside | Outdoor air temperature |
| 0x33 | TempExhaust | Exhaust air (after heat exchanger) |
| 0x34 | TempInside | Indoor extract air |
| 0x35 | TempIncoming | Supply air (after heat exchanger) |

Values use NTC sensor scale (see Conversion Tables).

### Fan Control

| Register | Name | Description |
|----------|------|-------------|
| 0x06 | IOPort1 | Fan speed relays (read-only) |
| 0x29 | FanSpeed | Current fan speed (1-8) |
| 0xA5 | FanSpeedMax | Maximum allowed speed |
| 0xA9 | FanSpeedBasic | Basic/minimum fan speed |

### Humidity

| Register | Name | Description |
|----------|------|-------------|
| 0x2A | Humidity | Maximum measured humidity |
| 0x2F | HumiditySensor1 | RH sensor 1 |
| 0x30 | HumiditySensor2 | RH sensor 2 |
| 0xAE | BasicHumidityLevel | Humidity threshold |

Formula: `humidity_percent = (value - 51) / 2.04`

### CO2

| Register | Name | Description |
|----------|------|-------------|
| 0x2B | CO2High | CO2 upper byte |
| 0x2C | CO2Low | CO2 lower byte |
| 0x2D | CO2SensorsInstalled | Bitmask of installed sensors |
| 0xB3 | CO2SetpointHigh | CO2 threshold upper byte |
| 0xB4 | CO2SetpointLow | CO2 threshold lower byte |

CO2 ppm: `(CO2High << 8) | CO2Low`

### I/O Ports (Read-only)

| Register | Bit | Description |
|----------|-----|-------------|
| 0x07 | 5 | Post-heating on |
| 0x08 | 1 | Damper position (0=winter, 1=summer) |
| 0x08 | 2 | Fault relay (0=open, 1=closed) |
| 0x08 | 3 | Supply fan (0=on, 1=off) |
| 0x08 | 4 | Pre-heating |
| 0x08 | 5 | Exhaust fan (0=on, 1=off) |
| 0x08 | 6 | Fireplace switch (0=open, 1=closed) |

### Select Register (0xA3)

| Bit | Name | Description |
|-----|------|-------------|
| 0 | PowerState | 0=Off, 1=On |
| 1 | CO2Adjust | CO2-based speed adjustment |
| 2 | RHAdjust | Humidity-based speed adjustment |
| 3 | HeatingState | Post-heating enabled |
| 4 | FilterGuard | Filter needs cleaning (read-only) |
| 5 | HeatingIndicator | Heating active (read-only) |
| 6 | FaultIndicator | Fault present (read-only) |
| 7 | ServiceReminder | Service due (read-only) |

### Flags Registers

**0x6D - FLAGS 2 (Read-only):**
| Bit | Description |
|-----|-------------|
| 0 | CO2 higher speed request |
| 1 | CO2 lower speed request |
| 2 | RH lower speed request |
| 3 | Switch lower speed request |
| 6 | CO2 alarm |
| 7 | Cell freeze alarm |

**0x6F - FLAGS 4 (Read-only):**
| Bit | Description |
|-----|-------------|
| 4 | Water coil freeze risk |
| 7 | Slave/Master (0=slave, 1=master) |

**0x70 - FLAGS 5:**
| Bit | Description |
|-----|-------------|
| 7 | Pre-heating status (0=on, 1=off) |

**0x71 - FLAGS 6:**
| Bit | Description |
|-----|-------------|
| 4 | Remote control working (read-only) |
| 5 | Activate fireplace switch |
| 6 | Fireplace/boost active (read-only) |

### Setpoints

| Register | Name | Range | Scale |
|----------|------|-------|-------|
| 0xA4 | HeatingSetpoint | - | NTC |
| 0xA6 | ServiceReminderMonths | 1-15 | Months |
| 0xA7 | PreheatingSetpoint | - | NTC |
| 0xA8 | SupplyFanStopTemp | - | NTC |
| 0xAF | BypassSetpoint | - | NTC |
| 0xB0 | DCFanInputAdjust | 0-100 | Percent |
| 0xB1 | DCFanOutputAdjust | 0-100 | Percent |
| 0xB2 | CellDefrostHysteresis | - | value/3 = °C |

### Post-Heating

| Register | Name | Description |
|----------|------|-------------|
| 0x55 | PostHeatingOnCounter | On-time in seconds (X/2.5 = %) |
| 0x56 | PostHeatingOffTime | Off-time in seconds |
| 0x57 | PostHeatingTarget | Target temp (NTC, read-only) |

### Fireplace/Boost

| Register | Name | Description |
|----------|------|-------------|
| 0x79 | FireplaceCountdown | Remaining time in minutes |

### Program Variables

**0xAA - Program:**
| Bits | Description |
|------|-------------|
| 0-3 | Adjustment interval |
| 4 | Auto humidity level search |
| 5 | Boost/fireplace switch (0=fireplace, 1=boost) |
| 6 | Heating model (0=electric, 1=water) |
| 7 | Cascade control |

**0xAB** - Service reminder monthly counter (countdown)

**0xB5 - Program2:**
| Bit | Description |
|-----|-------------|
| 0 | Max speed limit (0=with adjustments, 1=always) |

### Bus Control (Write-only)

| Register | Description |
|----------|-------------|
| 0x8F | Enable bus transmission (DATA=0x00) |
| 0x91 | Disable bus transmission (DATA=0x00) |

## Fault Codes

| Code | Description |
|------|-------------|
| 0x00 | No fault |
| 0x05 | Supply air sensor fault |
| 0x06 | CO2 alarm |
| 0x07 | Outdoor sensor fault |
| 0x08 | Exhaust air sensor fault |
| 0x09 | Water coil freeze risk |
| 0x0A | Exhaust air sensor fault |

## Conversion Tables

### Fan Speed

| Speed | Value | Binary |
|-------|-------|--------|
| 1 | 0x01 | 00000001 |
| 2 | 0x03 | 00000011 |
| 3 | 0x07 | 00000111 |
| 4 | 0x0F | 00001111 |
| 5 | 0x1F | 00011111 |
| 6 | 0x3F | 00111111 |
| 7 | 0x7F | 01111111 |
| 8 | 0xFF | 11111111 |

### Humidity

```
humidity_percent = (bus_value - 51) / 2.04
bus_value = (humidity_percent * 2.04) + 51
```

Where: 0x33 (51) = 0% RH, 0xFF (255) = 100% RH

### NTC Temperature Table

| Hex | °C | Hex | °C | Hex | °C | Hex | °C |
|-----|-----|-----|-----|-----|-----|-----|-----|
| 0x00 | -74 | 0x40 | -12 | 0x80 | 9 | 0xC0 | 34 |
| 0x10 | -40 | 0x50 | -7 | 0x90 | 14 | 0xD0 | 43 |
| 0x20 | -27 | 0x60 | -1 | 0xA0 | 20 | 0xE0 | 55 |
| 0x30 | -19 | 0x70 | 4 | 0xB0 | 26 | 0xF0 | 79 |
| 0x33 | -18 | 0x64 | 0 | 0xA7 | 22 | 0xFF | 100 |

Key reference points: 0x64 = 0°C, 0xA0 = 20°C

## References

- Vallox DIGIT bus protocol (Vallox/Petteri Kähärä, 27.06.2011)
- [FHEM Vallox Wiki](https://wiki.fhem.de/wiki/Vallox)
